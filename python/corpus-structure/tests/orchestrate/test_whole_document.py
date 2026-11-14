"""Explicit native source scope and membership preserve operator intent."""

import pytest
from typer.testing import CliRunner

from corpus_structure.cli.app import app
from corpus_structure.orchestrate.source_request import (
    SourceRunRequest,
    WholeDocument,
    source_selection,
)


@pytest.mark.parametrize("command", ["run", "ingest", "regenerate"])
@pytest.mark.parametrize("selection", ["--slice", "--scope"])
def test_whole_document_conflict_refuses_before_execution(command, selection, tmp_path):
    result = CliRunner().invoke(
        app,
        [
            command,
            "--source-root",
            str(tmp_path),
            "--semantic-release",
            "release",
            "--runtime",
            "runtime",
            "--whole-document",
            selection,
            "selected",
        ],
    )
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output


def test_resume_refuses_new_source_projection(tmp_path):
    for args in (["--whole-document"], ["--source-membership", "direct"]):
        result = CliRunner().invoke(
            app, ["regenerate", "--demand", "demand:one", "--source-root", str(tmp_path), *args]
        )
        assert result.exit_code == 2
        assert "owns its source and workflow selections" in result.output


def test_explicit_whole_document_is_frozen_without_default_scope_authority():
    value = SourceRunRequest(
        project_id="project",
        release_id="release",
        runtime_id="runtime",
        workflow="capture",
        selection=source_selection(whole_document=True),
        documents=("book",),
        membership="direct",
    )
    restored = SourceRunRequest.model_validate_json(value.model_dump_json())
    assert isinstance(restored.selection, WholeDocument)
    assert restored.documents == ("book",) and restored.membership == "direct"


def test_direct_membership_honors_named_scope_in_fresh_and_retained_selection():
    from types import SimpleNamespace

    from corpus_structure.ingest.pdf_methods import PdfIngestConfig, _select_sections
    from corpus_structure.ingest.pdf_section_views import select_published_sections

    names = {"#/groups/1": "Selected", "#/groups/2": "Child", "#/groups/3": "Unrelated"}
    parents = {"#/groups/1": "#/body", "#/groups/2": "#/groups/1", "#/groups/3": "#/body"}
    nodes = {"#/body": SimpleNamespace(label="body", parent=None)}
    for pointer, name in names.items():
        nodes[pointer] = SimpleNamespace(
            label="section", name=name, parent=SimpleNamespace(cref=parents[pointer])
        )
    rows = [
        dict(
            pointer=p,
            name=n,
            ancestors=[parents[p]] if p != "#/groups/2" else ["#/groups/1", "#/body"],
        )
        for p, n in names.items()
    ]
    scope = {"kind": "native_sections", "sections": ["Selected"]}
    expected = ("#/groups/1", "#/groups/2")
    assert _select_sections(nodes, PdfIngestConfig(membership="direct"), scope=scope) == expected
    assert select_published_sections(rows, (), "direct", scope) == expected
