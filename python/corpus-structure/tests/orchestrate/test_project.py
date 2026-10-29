"""`ci project init` and the pack-version upsert (P0-O-1, orchestration §3.3)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import Connection, text

from corpus_structure.orchestrate import project


def setup(orch: SimpleNamespace, tmp_path: Path) -> tuple[Path, Any]:
    pack = orch.write_pack(tmp_path)
    registry = orch.MethodRegistry([orch.ingest_stub()], orch.load_methods(pack / "methods.yaml"))
    return pack, registry


def counts(db: Connection) -> dict[str, int]:
    tables = (
        "meta.project",
        "kb.document",
        "meta.schema_version",
        "meta.guideline_version",
        "ops.policy_version",
        "meta.compiled_artifact",
    )
    return {t: db.execute(text(f"SELECT count(*) FROM {t}")).scalar_one() for t in tables}


def test_init_registers_documents_and_versions_and_a_rerun_adds_nothing(
    db: Connection, orch: SimpleNamespace, tmp_path: Path
) -> None:
    pack, registry = setup(orch, tmp_path)
    report = project.init_project(
        db, domain="minimal", corpus=orch.CORPUS, registry=registry, domains=pack.parent
    )
    assert (report.name, report.documents, report.documents_added) == ("minimal", 4, 4)
    assert report.profiles == ["siegrist"]
    assert set(report.versions_added) == {"schema_version", "guideline_version", "policy_version"}
    doc = db.execute(
        text(
            "SELECT source_uri, key, meta, title FROM kb.document WHERE source_uri "
            "LIKE '%/special/Normal.html'"
        )
    ).one()
    assert doc.source_uri == "siegrist_random/random/special/Normal.html"
    assert doc.key.startswith("doc:") and doc.meta["first_pass"] == "yes"
    assert doc.title == "The Normal Distribution" and "path" not in doc.meta
    assert doc.meta["page"] == "special/Normal.html"  # the locators' page
    guideline = db.execute(
        text("SELECT label, schema_version_id, parent_id FROM meta.guideline_version")
    ).one()
    assert guideline.label == "1" and guideline.parent_id is None
    before = counts(db)
    again = project.init_project(
        db, domain="minimal", corpus=orch.CORPUS, registry=registry, domains=pack.parent
    )
    assert again.documents_added == 0 and again.versions_added == []
    assert counts(db) == before


def test_an_edited_guideline_is_a_new_version_with_its_parent(
    db: Connection, orch: SimpleNamespace, tmp_path: Path
) -> None:
    pack, registry = setup(orch, tmp_path)
    project.init_project(
        db, domain="minimal", corpus=orch.CORPUS, registry=registry, domains=pack.parent
    )
    (pack / "guideline.md").write_text(
        "# Annotation guideline v2 (test)\n\nMore.\n", encoding="utf-8"
    )
    pid = db.execute(text("SELECT id FROM meta.project")).scalar_one()
    versions = project.ensure_pack_versions(db, pid, pack, "human:test")
    assert versions.created == ("guideline_version",)
    rows = db.execute(text("SELECT id, label, parent_id FROM meta.guideline_version ORDER BY id"))
    first, second = rows.all()
    assert (second.label, second.parent_id) == ("2", first.id)


def test_two_rows_with_one_page_are_refused(
    db: Connection, orch: SimpleNamespace, tmp_path: Path
) -> None:
    pack, registry = setup(orch, tmp_path)
    corpus = tmp_path / "corpus"
    import shutil

    shutil.copytree(orch.CORPUS, corpus)
    index = tmp_path / "index" / "siegrist_sections.tsv"
    index.parent.mkdir()
    lines = (orch.CORPUS.parent / "index" / "siegrist_sections.tsv").read_text().splitlines()
    index.write_text("\n".join([*lines, lines[1]]) + "\n", encoding="utf-8")
    with pytest.raises(project.ProjectError, match="registered twice"):
        project.init_project(
            db, domain="minimal", corpus=corpus, registry=registry, domains=pack.parent
        )
