"""Faithful original inventory registration uses the ordinary native source owner."""

import json
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import select, text
from typer.testing import CliRunner

from corpus_structure.cli import orchestrate as cli
from corpus_structure.cli.app import build_full_app
from corpus_structure.core.evidence import document_key
from corpus_structure.orchestrate.project import (
    OriginalDescriptorInventory,
    ProjectError,
    init_described_projects,
)
from corpus_structure.semantic.data_operation_admission import admit_data_operation_release
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.original_documents import (
    OriginalDocumentConflict,
    acquire_original_document_selection,
    read_original_document_bytes,
)
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.types import PreparationProfile
from semantic.original_document_support import source_admission_inputs


def inventory(tmp_path, count=29):
    descriptors = []
    for index in range(count):
        # Two project identities deliberately retain the same physical source path.
        path = tmp_path / f"original-{max(index, 1)}.pdf"
        raw = f"%PDF-1.7\nsource-{max(index, 1)}\n".encode()
        path.write_bytes(raw)
        project = f"project-{index % 9}"
        uri = f"original-{index}.pdf"
        digest = sha256(raw).hexdigest()
        descriptors.append(
            dict(
                project_id=project,
                key=document_key(project, uri, digest),
                source_uri=uri,
                content_hash=digest,
                original_path=str(path),
                mime="application/pdf",
                title=f"Original title {index} β",
                metadata={"empty": [], "null": None, "ordinal": index},
            )
        )
    return OriginalDescriptorInventory.model_validate(
        {
            "descriptors": descriptors,
            "documents": count,
            "distinct_paths": len({x["original_path"] for x in descriptors}),
        }
    )


def test_retained_inventory_has_exact_nine_project_twenty_nine_descriptor_basis():
    path = (
        Path(__file__).resolve().parents[4]
        / "docs/design_review/evidence/2026-11-16_ddo-current-native/original-descriptors.json"
    )
    selected = OriginalDescriptorInventory.model_validate_json(path.read_bytes())
    assert selected.documents == 29 and selected.distinct_paths == 28
    assert len({item.project_id for item in selected.descriptors}) == 9
    # Receipt metadata supplies provenance only and never chooses the target.
    assert "database" not in selected.model_dump()


@pytest.mark.parametrize("mutation", ["hash", "key", "missing", "duplicate", "count", "paths"])
def test_invalid_inventory_refuses_before_any_project_effect(tmp_path, mutation):
    from unittest.mock import MagicMock

    selected = inventory(tmp_path, count=2).model_dump()
    if mutation == "hash":
        selected["descriptors"][1]["content_hash"] = "0" * 64
    elif mutation == "key":
        selected["descriptors"][1]["key"] = "doc:" + "0" * 32
    elif mutation == "missing":
        Path(selected["descriptors"][1]["original_path"]).unlink()
    elif mutation == "duplicate":
        selected["descriptors"][1] = selected["descriptors"][0]
    elif mutation == "count":
        selected["documents"] = 3
    else:
        selected["distinct_paths"] = 3
    connection = MagicMock()
    with pytest.raises((ProjectError, ValidationError, FileNotFoundError)):
        init_described_projects(
            connection,
            inventory=OriginalDescriptorInventory.model_validate(selected),
            release_id="release",
        )
    assert connection.mock_calls == []


def test_native_descriptor_cli_preserves_inventory_and_exact_retry(
    commit_db_engine, commit_writer_engine, commit_reader_engine, tmp_path, monkeypatch
):
    bundle, dependencies, _ = source_admission_inputs()
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(bundle, dependencies, profile)
    with commit_db_engine.begin() as connection:
        persist_release(connection, bundle, dependencies, profile, prepared)
        admit_data_operation_release(connection, prepared)
    selected = inventory(tmp_path)
    inventory_path = tmp_path / "descriptors.json"
    inventory_path.write_text(selected.model_dump_json())

    @contextmanager
    def engine(_):
        yield commit_writer_engine

    monkeypatch.setattr(cli, "ENGINE", engine)
    app = build_full_app()
    arguments = [
        "project",
        "init",
        "--original-descriptors",
        str(inventory_path),
        "--semantic-release",
        prepared.release_id,
        "--json",
    ]
    for _ in range(2):
        response = CliRunner().invoke(app, arguments)
        assert response.exit_code == 0, (response.output, response.exception)
        assert json.loads(response.stdout) == {
            "projects": [f"project-{index}" for index in range(9)],
            "release_id": prepared.release_id,
            "documents": 29,
        }
    with commit_reader_engine.connect() as connection:
        for item in selected.descriptors:
            fact = acquire_original_document_selection(
                connection, project_id=item.project_id, document_key=item.key
            )
            assert (
                read_original_document_bytes(connection, fact.reference, prepared=prepared)
                == Path(item.original_path).read_bytes()
            )
    documents = table("kb.document")
    with commit_db_engine.connect() as connection:
        rows = connection.execute(select(documents)).mappings().all()
        assert len(rows) == 29
        assert {
            (
                row["project_id"],
                row["key"],
                row["source_uri"],
                row["content_hash"],
                row["original_path"],
                row["mime"],
                row["title"],
                json.dumps(row["meta"], sort_keys=True),
            )
            for row in rows
        } == {
            (
                item.project_id,
                item.key,
                item.source_uri,
                item.content_hash,
                item.original_path,
                item.mime,
                item.title,
                json.dumps(item.metadata, sort_keys=True),
            )
            for item in selected.descriptors
        }
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM data.project WHERE generation=0 AND active_release_id IS NULL"
                )
            )
            == 9
        )
        assert connection.scalar(text("SELECT count(*) FROM ops.data_demand")) == 0

    # A later immutable conflict rolls back a newly initialized and registered project.
    changed = selected.model_dump()
    changed["descriptors"][0]["title"] = "changed title"
    extra = dict(changed["descriptors"][1])
    extra["project_id"] = "additional-project"
    extra["key"] = document_key(extra["project_id"], extra["source_uri"], extra["content_hash"])
    changed["descriptors"].insert(0, extra)
    changed["documents"] += 1
    with (
        commit_writer_engine.begin() as connection,
        pytest.raises(OriginalDocumentConflict),
        connection.begin_nested(),
    ):
        init_described_projects(
            connection,
            inventory=OriginalDescriptorInventory.model_validate(changed),
            release_id=prepared.release_id,
        )

    with commit_db_engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM data.project WHERE project_id='additional-project'")
            )
            == 0
        )
        assert connection.scalar(text("SELECT count(*) FROM kb.document")) == 29
