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


PIN = dict(project_id="project:selected", demand_id="demand:selected", read_id="read:selected",
           use_id="use:selected", product_id="product:selected", derivation_id="derivation:original")


@dataclass
class SourceRuntime:
    engine: MagicMock
    connection: MagicMock
    opened: list[tuple[str, str]]


@pytest.fixture
def source_runtime(monkeypatch):
    from corpus_structure.semantic import demand_results, runtime

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
    return controlled


def _inspect_args(*extra):
    return ("source", "inspect", PIN["demand_id"], "--project", PIN["project_id"],
            "--read", PIN["read_id"], "--use", PIN["use_id"], "--product", PIN["product_id"],
            "--derivation", PIN["derivation_id"], *extra)


@pytest.mark.parametrize("command,view", [("native-products", "publications"), ("views", "views")])
@pytest.mark.parametrize("empty", [False, True])
def test_current_catalog_cli_retains_pinned_cut_and_partial_standing(cli, source_runtime, monkeypatch, command, view, empty):
    from corpus_structure.serve import source_catalog
    from corpus_structure.semantic.data_operation_json import json_loads

    seen = []
    def catalog(connection, request):
        assert connection is source_runtime.connection
        seen.append(request)
        return source_catalog.SourceCatalogResponse(
            selection=request,
            cut={"read_id": PIN["read_id"], "scope": {"ratio": Decimal("0.123456789012345678901")}},
            rows=[] if empty else [{"selection": PIN, "member_id": "member:source-view" if view == "views" else None}],
            obligations=[{"fate": "unknown"}], uses=[], populations=[],
            next_cursor="exact-selected-continuation", page_complete=False,
        )
    monkeypatch.setattr(source_catalog, "read_source_catalog", catalog)
    result = cli("source", command, PIN["demand_id"], "--project", PIN["project_id"],
                 "--cursor", "prior-selected-continuation", "--limit", "7", "--json")
    assert result.exit_code == 0, (result.output, result.exception)
    response = json_loads(result.stdout)
    assert response["cut"]["scope"]["ratio"] == Decimal("0.123456789012345678901")
    assert response["rows"] == ([] if empty else [{"selection": PIN, "member_id": "member:source-view" if view == "views" else None}])
    assert response["obligations"] == [{"fate": "unknown"}] and not response["page_complete"]
    assert response["next_cursor"] == "exact-selected-continuation"
    assert seen[0].model_dump() == dict(project_id=PIN["project_id"], demand_id=PIN["demand_id"],
        view=view, cursor="prior-selected-continuation", limit=7, max_bytes=1048576)
    assert source_runtime.opened == [("ci-source-catalog", "read")]


def test_inspect_cli_delivers_exact_visual_selection(cli, source_runtime, monkeypatch):
    from corpus_structure.serve import native_source
    from corpus_structure.semantic.visual_evidence import VisualEvidenceRead, VisualText

    def inspect(connection, request, *, cancellation):
        assert connection is source_runtime.connection
        assert request.model_dump(include=set(PIN)) == PIN
        assert request.view == "visual_evidence" and request.page_no == 3
        assert request.pointer == "#/pictures/2" and request.region_index == 1
        assert request.visual_kind == "mermaid" and request.occurrence_id == "o1"
        assert request.evidence is not None
        assert request.evidence.model_dump() == dict(use_id="use:mapped", product_id="product:mapped", derivation_id="derivation:mapped")
        return native_source.NativeSourceResponse(
            selection=request, release_id="release:source", cut={"read_id": PIN["read_id"]}, health={}, rows=[{"text": "incumbent"}],
            visual_evidence=VisualEvidenceRead(evidence=request.evidence, raw_evidence=request.evidence,
                producer={"request_id": "request:mapped"}, raw_producer={"request_id": "request:raw"}, page_no=3, original_artifact_digest="c" * 64,
                original_regions=[], submitted_region=None, observation_release_id="release:observation",
                observation={"outcome": "partial"}, mapping_availability="available",
                items=(VisualText(occurrence_id="o1", kind="mermaid", text="graph TD; A-->B"),)),
        )
    monkeypatch.setattr(native_source, "inspect_native_source", inspect)
    result = cli(*_inspect_args("--native-view", "visual-evidence", "--evidence-use", "use:mapped",
        "--evidence-product", "product:mapped", "--evidence-derivation", "derivation:mapped",
        "--page", "3", "--pointer", "#/pictures/2", "--region-index", "1",
        "--visual-kind", "mermaid", "--occurrence", "o1", "--json"))
    assert result.exit_code == 0, (result.output, result.exception)
    data = json.loads(result.stdout)
    assert data["rows"] == [{"text": "incumbent"}]
    assert data["visual_evidence"]["items"][0]["kind"] == "mermaid"
    assert source_runtime.opened == [("ci-source", "read")]


def test_current_inspection_preserves_exact_product_and_companion_selector(cli, source_runtime, monkeypatch):
    from corpus_structure.serve import native_source
    seen = []
    def inspect(connection, request, *, cancellation):
        assert connection is source_runtime.connection
        seen.append(request)
        return native_source.NativeSourceResponse(selection=request, release_id="release:source",
            cut={"read_id": PIN["read_id"]}, health={}, rows=[{"outcome": "unknown"}])
    monkeypatch.setattr(native_source, "inspect_native_source", inspect)
    result = cli(*_inspect_args("--native-view", "manifest", "--collection", "coverage", "--json"))
    assert result.exit_code == 0, (result.output, result.exception)
    selected = seen[0]
    assert selected.version == 5 and selected.model_dump(include=set(PIN)) == PIN
    assert selected.view == "manifest" and selected.collection == "coverage"
    assert json.loads(result.stdout)["rows"] == [{"outcome": "unknown"}]
    for old in (("17", "4"), ("17", "--producing-task", "23", "--native-digest", "a" * 64)):
        rejected = cli("source", "inspect", *old, "--json")
        assert rejected.exit_code != 0
    assert len(seen) == 1, "retired physical selection reached the current source reader"


def test_source_coverage_summary_keeps_page_counts_and_continuation(cli, source_runtime, monkeypatch):
    from corpus_structure.serve import native_source
    def inspect(connection, request, *, cancellation):
        assert connection is source_runtime.connection
        return native_source.NativeSourceResponse(selection=request, release_id="release:source",
            cut={"read_id": PIN["read_id"]}, health={},
            rows=[{"rows": [{"outcome": "missing"}, {"outcome": "ready"}]}],
            next_cursor="next-coverage-page", population_complete=False)
    monkeypatch.setattr(native_source, "inspect_native_source", inspect)
    args = _inspect_args("--native-view", "manifest", "--collection", "coverage")
    full, projected, human = cli(*args, "--json"), cli(*args, "--view", "summary", "--json"), cli(*args)
    assert full.exit_code == projected.exit_code == human.exit_code == 0
    assert json.loads(projected.stdout) == dict(selection=json.loads(full.stdout)["selection"],
        release_id="release:source", outcome="source_ready", page_outcomes={"missing": 1, "ready": 1},
        page_rows=2, next_cursor="next-coverage-page")
    assert "missing: 1, ready: 1" in human.stdout
    assert PIN["product_id"] in human.stdout


def test_retired_run_catalog_options_refuse_before_opening_runtime(cli, source_runtime):
    for command in ("native-products", "views"):
        assert cli("source", command, "17", "--json").exit_code != 0
    assert cli("source", "native-products", PIN["demand_id"], "--project", PIN["project_id"], "--observations", "--task", "23").exit_code != 0
    assert not source_runtime.opened
