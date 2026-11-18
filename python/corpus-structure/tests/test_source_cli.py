"""Current source adapters preserve exact selected semantic pins and bounded reports.

These controlled adapters establish CLI correspondence, not native publication custody.
The genuine source/publication journeys own that independent native obligation.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy import Connection, Engine

PIN = dict(
    project_id="project:selected",
    demand_id="demand:selected",
    read_id="read:selected",
    use_id="use:selected",
    product_id="product:selected",
    derivation_id="derivation:original",
)


@dataclass
class SourceRuntime:
    engine: MagicMock
    connection: MagicMock
    opened: list[tuple[str, str]]


@pytest.fixture
def source_runtime(monkeypatch):
    from corpus_structure.semantic import demand_results, pdf_source_search, runtime

    controlled = SourceRuntime(MagicMock(spec=Engine), MagicMock(spec=Connection), [])

    @contextmanager
    def open_engine(settings, *, application_name, purpose):
        controlled.opened.append((application_name, purpose))
        yield controlled.engine

    @contextmanager
    def selected_snapshot(engine, *, cancellation=None):
        assert engine is controlled.engine
        yield controlled.connection

    monkeypatch.setattr(runtime, "open_runtime_engine", open_engine)
    monkeypatch.setattr(demand_results, "selected_read_snapshot", selected_snapshot)
    monkeypatch.setattr(pdf_source_search, "search_source_snapshot", selected_snapshot)
    return controlled


def _inspect_args(*extra):
    return (
        "source",
        "inspect",
        PIN["demand_id"],
        "--project",
        PIN["project_id"],
        "--read",
        PIN["read_id"],
        "--use",
        PIN["use_id"],
        "--product",
        PIN["product_id"],
        "--derivation",
        PIN["derivation_id"],
        *extra,
    )


@pytest.mark.parametrize("command,view", [("native-products", "publications"), ("views", "views")])
@pytest.mark.parametrize("empty", [False, True])
def test_current_catalog_cli_retains_pinned_cut_and_partial_standing(
    cli, source_runtime, monkeypatch, command, view, empty
):
    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.serve import source_catalog

    seen = []

    def catalog(connection, request):
        assert connection is source_runtime.connection
        seen.append(request)
        return source_catalog.SourceCatalogResponse(
            selection=request,
            cut={"read_id": PIN["read_id"], "scope": {"ratio": Decimal("0.123456789012345678901")}},
            rows=[]
            if empty
            else [
                {"selection": PIN, "member_id": "member:source-view" if view == "views" else None}
            ],
            obligations=[{"fate": "unknown"}],
            uses=[],
            populations=[],
            next_cursor="exact-selected-continuation",
            page_complete=False,
        )

    monkeypatch.setattr(source_catalog, "read_source_catalog", catalog)
    result = cli(
        "source",
        command,
        PIN["demand_id"],
        "--project",
        PIN["project_id"],
        "--cursor",
        "prior-selected-continuation",
        "--limit",
        "7",
        "--json",
    )
    assert result.exit_code == 0, (result.output, result.exception)
    response = json_loads(result.stdout)
    assert response["cut"]["scope"]["ratio"] == Decimal("0.123456789012345678901")
    assert response["rows"] == (
        []
        if empty
        else [{"selection": PIN, "member_id": "member:source-view" if view == "views" else None}]
    )
    assert response["obligations"] == [{"fate": "unknown"}] and not response["page_complete"]
    assert response["next_cursor"] == "exact-selected-continuation"
    assert seen[0].model_dump() == dict(
        project_id=PIN["project_id"],
        demand_id=PIN["demand_id"],
        view=view,
        cursor="prior-selected-continuation",
        limit=7,
        max_bytes=1048576,
    )
    assert source_runtime.opened == [("ci-source-catalog", "read")]


def test_inspect_cli_delivers_exact_visual_selection(cli, source_runtime, monkeypatch):
    from corpus_structure.semantic.visual_evidence import VisualEvidenceRead, VisualText
    from corpus_structure.serve import native_source

    def inspect(connection, request, *, cancellation):
        assert connection is source_runtime.connection
        assert request.model_dump(include=set(PIN)) == PIN
        assert request.view == "visual_evidence" and request.page_no == 3
        assert request.pointer == "#/pictures/2" and request.region_index == 1
        assert request.visual_kind == "mermaid" and request.occurrence_id == "o1"
        assert request.evidence is not None
        assert request.evidence.model_dump() == dict(
            use_id="use:mapped", product_id="product:mapped", derivation_id="derivation:mapped"
        )
        return native_source.NativeSourceResponse(
            selection=request,
            release_id="release:source",
            cut={"read_id": PIN["read_id"]},
            health={},
            rows=[{"text": "incumbent"}],
            visual_evidence=VisualEvidenceRead(
                evidence=request.evidence,
                raw_evidence=request.evidence,
                producer={"request_id": "request:mapped"},
                raw_producer={"request_id": "request:raw"},
                page_no=3,
                original_artifact_digest="c" * 64,
                original_regions=[],
                submitted_region=None,
                observation_release_id="release:observation",
                observation={"outcome": "partial"},
                mapping_availability="available",
                items=(VisualText(occurrence_id="o1", kind="mermaid", text="graph TD; A-->B"),),
            ),
        )

    monkeypatch.setattr(native_source, "inspect_native_source", inspect)
    result = cli(
        *_inspect_args(
            "--native-view",
            "visual-evidence",
            "--evidence-use",
            "use:mapped",
            "--evidence-product",
            "product:mapped",
            "--evidence-derivation",
            "derivation:mapped",
            "--page",
            "3",
            "--pointer",
            "#/pictures/2",
            "--region-index",
            "1",
            "--visual-kind",
            "mermaid",
            "--occurrence",
            "o1",
            "--json",
        )
    )
    assert result.exit_code == 0, (result.output, result.exception)
    data = json.loads(result.stdout)
    assert data["rows"] == [{"text": "incumbent"}]
    assert data["visual_evidence"]["items"][0]["kind"] == "mermaid"
    assert source_runtime.opened == [("ci-source", "read")]


def test_current_inspection_preserves_exact_product_and_companion_selector(
    cli, source_runtime, monkeypatch
):
    from corpus_structure.serve import native_source

    seen = []

    def inspect(connection, request, *, cancellation):
        assert connection is source_runtime.connection
        seen.append(request)
        return native_source.NativeSourceResponse(
            selection=request,
            release_id="release:source",
            cut={"read_id": PIN["read_id"]},
            health={},
            rows=[{"outcome": "unknown"}],
        )

    monkeypatch.setattr(native_source, "inspect_native_source", inspect)
    result = cli(*_inspect_args("--native-view", "manifest", "--collection", "coverage", "--json"))
    assert result.exit_code == 0, (result.output, result.exception)
    selected = seen[0]
    assert selected.version == 5 and selected.model_dump(include=set(PIN)) == PIN
    assert selected.view == "manifest" and selected.collection == "coverage"
    assert json.loads(result.stdout)["rows"] == [{"outcome": "unknown"}]
    for old, reason in (
        (("17", "4"), "Got unexpected extra argument(s) (4)"),
        (
            ("17", "--producing-task", "23", "--native-digest", "a" * 64),
            "No such option: --producing-task",
        ),
    ):
        rejected = cli("source", "inspect", old[0], *_inspect_args()[3:], *old[1:], "--json")
        assert rejected.exit_code == 2
        assert reason in rejected.output
    assert len(seen) == 1, "retired physical selection reached the current source reader"


def test_source_coverage_summary_keeps_page_counts_and_continuation(
    cli, source_runtime, monkeypatch
):
    from corpus_structure.serve import native_source

    def inspect(connection, request, *, cancellation):
        assert connection is source_runtime.connection
        return native_source.NativeSourceResponse(
            selection=request,
            release_id="release:source",
            cut={"read_id": PIN["read_id"]},
            health={},
            rows=[{"rows": [{"outcome": "missing"}, {"outcome": "ready"}]}],
            next_cursor="next-coverage-page",
            population_complete=False,
        )

    monkeypatch.setattr(native_source, "inspect_native_source", inspect)
    args = _inspect_args("--native-view", "manifest", "--collection", "coverage")
    full, projected, human = (
        cli(*args, "--json"),
        cli(*args, "--view", "summary", "--json"),
        cli(*args),
    )
    assert full.exit_code == projected.exit_code == human.exit_code == 0
    assert json.loads(projected.stdout) == dict(
        selection=json.loads(full.stdout)["selection"],
        release_id="release:source",
        outcome="source_ready",
        page_outcomes={"missing": 1, "ready": 1},
        page_rows=2,
        next_cursor="next-coverage-page",
    )
    assert "missing: 1, ready: 1" in human.stdout
    assert PIN["product_id"] in human.stdout


def test_source_catalog_requires_project_and_refuses_retired_run_options(
    cli, source_runtime, monkeypatch
):
    from corpus_structure.serve import source_catalog

    def catalog(connection, request):
        assert connection is source_runtime.connection
        return source_catalog.SourceCatalogResponse(
            selection=request,
            cut={},
            rows=[],
            obligations=[],
            uses=[],
            populations=[],
            next_cursor=None,
            page_complete=True,
        )

    monkeypatch.setattr(source_catalog, "read_source_catalog", catalog)
    for command in ("native-products", "views"):
        accepted = cli(
            "source", command, PIN["demand_id"], "--project", PIN["project_id"], "--json"
        )
        assert accepted.exit_code == 0, (accepted.output, accepted.exception)
    source_runtime.opened.clear()
    for command in ("native-products", "views"):
        rejected = cli("source", command, "17", "--json")
        assert rejected.exit_code == 2
        assert "Missing option '--project'" in rejected.output
    for option, value in (("--observations", ()), ("--task", ("23",))):
        rejected = cli(
            "source",
            "native-products",
            PIN["demand_id"],
            "--project",
            PIN["project_id"],
            option,
            *value,
        )
        assert rejected.exit_code == 2
        assert f"No such option: {option}" in rejected.output
    assert not source_runtime.opened


@pytest.mark.parametrize("empty", [False, True])
def test_source_find_routes_exact_selected_request_and_preserves_current_handles(
    cli, source_runtime, tmp_path, monkeypatch, empty
):
    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.serve import source_search
    from corpus_structure.serve.native_source import NativeSourceRequest
    from corpus_structure.serve.selected_pdf import SelectedPdfSourceReference

    content = dict(
        project_id=PIN["project_id"],
        demand_id=PIN["demand_id"],
        read_id=PIN["read_id"],
        sources=[PIN],
        sections=["#/body"],
        membership="descendants",
        text="Alice",
        cursor="selected:continuation",
        limit=3,
        max_rows=500,
        max_bytes=8192,
    )
    path = tmp_path / "search.json"
    path.write_text(json.dumps(content))
    seen = []

    def search(connection, request):
        assert connection is source_runtime.connection
        seen.append(request)
        return source_search.SourceSearchResponse(
            cut={"read_id": PIN["read_id"], "scope": {"ratio": Decimal("0.123456789012345678901")}},
            rows=[]
            if empty
            else [
                source_search.SourceSearchHit(
                    source=SelectedPdfSourceReference(**PIN),
                    original_source="original:selected",
                    source_digest="a" * 64,
                    projection_digest="projection:selected",
                    selection=NativeSourceRequest(
                        **PIN, section_pointer="#/body", membership="descendants"
                    ),
                    excerpt="<b>Alice</b> was running.",
                    score=0.25,
                )
            ],
            next_cursor="next:selected",
            population_complete=False,
        )

    monkeypatch.setattr(source_search, "search_source", search)
    reply = cli("source", "find", str(path), "--json")
    assert reply.exit_code == 0, (reply.output, reply.exception)
    value = json_loads(reply.stdout)
    assert value["cut"]["scope"]["ratio"] == Decimal("0.123456789012345678901")
    assert value["next_cursor"] == "next:selected" and not value["population_complete"]
    if not empty:
        selection = value["rows"][0]["selection"]
        assert {key: selection[key] for key in PIN} == PIN
        assert selection["section_pointer"] == "#/body" and selection["membership"] == "descendants"
        assert value["rows"][0]["original_source"] == "original:selected"
    else:
        assert value["rows"] == []
    assert seen[0].model_dump(mode="json", exclude_defaults=True) == content
    assert source_runtime.opened == [("ci-source-find", "read")]


def test_source_find_refuses_unqualified_or_retired_request_before_acquisition(
    cli, source_runtime, tmp_path, monkeypatch
):
    from corpus_structure.serve import source_search

    valid = {
        "project_id": PIN["project_id"],
        "demand_id": PIN["demand_id"],
        "read_id": PIN["read_id"],
        "sources": [PIN],
        "text": "Alice",
    }

    def search(connection, request):
        assert connection is source_runtime.connection
        return source_search.SourceSearchResponse(cut={}, rows=[], population_complete=True)

    monkeypatch.setattr(source_search, "search_source", search)
    path = tmp_path / "search.json"
    path.write_text(json.dumps(valid))
    accepted = cli("source", "find", str(path), "--json")
    assert accepted.exit_code == 0, (accepted.output, accepted.exception)
    source_runtime.opened.clear()
    for value, code, pointer in (
        ({**valid, "run_id": 17}, "extra_forbidden", "/run_id"),
        ({key: value for key, value in valid.items() if key != "read_id"}, "missing", "/read_id"),
        ({key: value for key, value in valid.items() if key != "sources"}, "missing", "/sources"),
    ):
        path.write_text(json.dumps(value))
        rejected = cli("source", "find", str(path), "--json")
        assert rejected.exit_code == 1
        refusal = json.loads(rejected.stdout)["error"]
        assert refusal["code"] == "ValidationError"
        assert refusal["message"] == "invalid SourceSearchRequest input"
        assert [
            (row["code"], row["input_path"]) for row in refusal["validation"]["observations"]
        ] == [(code, pointer)]
    assert not source_runtime.opened
