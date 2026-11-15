"""Actual typed current consumers with controlled native acquisition, never publication proof."""

from contextlib import contextmanager, nullcontext
from decimal import Decimal
from types import SimpleNamespace

import anyio
import pytest
from fastmcp import Client
from sqlalchemy import create_engine
from typer.testing import CliRunner

from corpus_structure.cli.app import app
from corpus_structure.semantic import prepare_release
from corpus_structure.semantic.analysis_contracts import acquire_analysis_context_profile
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.data_operation_read_index import SelectedRecordIndex
from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.semantic.record_policy_authority import record_policy_kind_declarations
from corpus_structure.semantic.refusals import InvalidContinuation
from corpus_structure.semantic.rich_invocations import rich_knowledge_operation_sources
from corpus_structure.semantic.rich_knowledge_sources import (
    rich_knowledge_declarations,
    rich_knowledge_inputs,
)
from corpus_structure.semantic.types import ResolvedDependencies
from corpus_structure.serve import contribution_facets as facets
from corpus_structure.serve import identity_exclusion_comparison as comparison
from corpus_structure.serve.selected_contributions import SelectedContributionScope
from semantic.record_contracts_support import release_inputs
from semantic.test_rich_identity_exclusions import constraint
from semantic.test_rich_queries import PREFIX, Graph
from semantic.test_selected_contribution_inputs import append


@pytest.fixture(scope="module")
def rich_source():
    bundle, deps = rich_knowledge_inputs(
        release_inputs()[0],
        ResolvedDependencies(),
        domain_rules=b"rules: []\n",
        context_profile=acquire_analysis_context_profile(),
        qualification_class="StatisticsQualification",
        statement_class="SourceStatement",
    )
    return prepare_release(bundle, deps), compile_data_operations(
        bundle,
        declarations=(*rich_knowledge_declarations(deps), record_policy_kind_declarations()),
        python_sources=rich_knowledge_operation_sources(),
    )


def scope(tmp_path, source, *, side="one", left="A"):
    graph = Graph(
        source, {"A": "DistributionFamily", "B": "DistributionFamily", "C": "DistributionFamily"}
    )
    value = constraint(graph, left=left)
    graph.bodies[value.exclusion_id] = value
    index = graph.index()
    selected = graph.root_input
    native = SelectedRecordIndex(tmp_path / (side + ".sqlite"))
    cut = CutSelection(
        json_bytes(
            dict(
                demand_id="demand:" + side,
                project_id=graph.context.project_id,
                read_id="read:" + side,
                release_id=source[0].release_id,
                runtime_id="runtime:controlled",
                selection={"targets": ["rich.admit"]},
                trust_snapshot={},
                read_snapshot="1:2:",
                frontier_at="2026-11-15T00:00:00Z",
                scope={"product_ids": [selected.reference.product_id]},
            )
        )
    )
    native.append_page(
        {
            **cut.record,
            "obligations": [dict(obligation_id="obligation:" + side, operation_id="rich.admit")],
            "uses": [
                dict(
                    use_id="use:" + side,
                    obligation_id="obligation:" + side,
                    fate="fulfilled",
                    completion_state="success",
                    derivation_id="episode:" + side,
                )
            ],
        }
    )
    append(
        native,
        "ops.data_derivation",
        "episode:" + side,
        dict(id="episode:" + side, request_id="request:" + side),
    )
    append(
        native,
        "ops.data_request",
        "request:" + side,
        dict(
            id="request:" + side,
            operation_id="rich.admit",
            recipe=next(
                item.key
                for item in source[1].identities
                if item.owner == "rich.admit" and item.domain == "recipe"
            ),
        ),
    )
    append(
        native,
        "ops.data_derivation_output",
        "output:" + side,
        dict(
            derivation_id="episode:" + side,
            product_id=selected.reference.product_id,
            member_id=None,
            role="admission",
            position=0,
            multiplicity=1,
        ),
    )
    append(
        native,
        "kb.data_product",
        selected.reference.product_id,
        dict(
            id=selected.reference.product_id,
            project_id=graph.context.project_id,
            subject=graph.context.subject,
            subject_definition=graph.context.subject_definition,
            original_source=None,
            analyzed_scope={},
            kind_contract=selected.reference.kind_contract,
            canonical_body=semantic_value(index.state.graph.model_dump(mode="python")),
        ),
    )
    append(
        native,
        "sem.data_kind_contract",
        selected.reference.kind_contract,
        dict(
            kind_contract=selected.reference.kind_contract,
            kind=PREFIX + "DdoRichAdmission",
            universe="ordinary",
        ),
    )
    return SelectedContributionScope(
        cut, native, source[0], source[1], {"product_ids": [selected.reference.product_id]}, 100000
    )


def pin(scope, side="one"):
    return comparison.ConstraintRootPin(
        demand_id="demand:" + side,
        project_id=scope.cut.record["project_id"],
        product_id="selected-knowledge",
        read_id="read:" + side,
        cut_id=scope.cut.identity,
        use_id="use:" + side,
        derivation_id="episode:" + side,
    )


def request(scope, **updates):
    return facets.ContributionFacetsRequest.model_validate(
        {
            "demand_id": scope.cut.record["demand_id"],
            "project_id": scope.cut.record["project_id"],
            "product_id": "selected-knowledge",
            **updates,
        }
    )


@contextmanager
def controlled_scope(scope, seen, request):
    seen.append(request)
    if request.read_id is not None:
        assert (
            request.read_id == scope.cut.record["read_id"]
            and request.expected_cut == scope.cut.identity
        )
    yield scope


def test_current_facet_pages_pin_native_selection_root_and_implementation(
    monkeypatch, tmp_path, rich_source
):
    selected = scope(tmp_path, rich_source)
    seen = []
    monkeypatch.setattr(
        facets,
        "selected_contribution_scope",
        lambda connection, request: controlled_scope(selected, seen, request),
    )
    try:
        first = facets.serve_contribution_facets(None, request(selected, limit=1))
        assert first["items"][0]["population"] == "operation" and first["cursor"]
        second = facets.serve_contribution_facets(
            None, request(selected, limit=1, cursor=first["cursor"])
        )
        assert second["items"] != first["items"]
        assert (
            seen[1].read_id == selected.cut.record["read_id"]
            and seen[1].expected_cut == selected.cut.identity
        )
        replay = facets.ContributionFacetsRequest.model_validate(
            facets.decode_rich_cursor(first["resource_handle"])
        )
        assert facets.serve_contribution_facets(None, replay)["items"] == first["items"]
        with pytest.raises(InvalidContinuation):
            facets.serve_contribution_facets(
                None, request(selected, cursor=first["cursor"], include_assessment=False)
            )
        with pytest.raises(InvalidContinuation):
            facets.serve_contribution_facets(None, request(selected, implementation="0" * 64))
        from corpus_structure.semantic.rich_queries import RichQueryRefused

        with pytest.raises(RichQueryRefused, match="member bound"):
            facets.serve_contribution_facets(
                None, request(selected, include_operations=False, max_members=1)
            )
        with pytest.raises(RichQueryRefused, match="max_bytes"):
            facets.serve_contribution_facets(None, request(selected, max_bytes=1024))
    finally:
        selected.index.close()


def test_current_comparison_uses_exact_two_root_use_and_cut_pins(
    monkeypatch, tmp_path, rich_source
):
    before = scope(tmp_path, rich_source, side="before")
    after = scope(tmp_path, rich_source, side="after", left="C")
    seen = []
    monkeypatch.setattr(
        comparison,
        "selected_contribution_scope",
        lambda connection, request: controlled_scope(
            before if request.demand_id == "demand:before" else after, seen, request
        ),
    )
    try:
        selected = comparison.ExclusionComparisonRequest(
            before=pin(before, "before"), after=pin(after, "after")
        )
        report = comparison.compare_selected_exclusions(None, selected)
        assert (
            report["before"]["pin"]["use_id"] == "use:before"
            and report["after"]["pin"]["derivation_id"] == "episode:after"
        )
        assert report["changes"][0]["outcome"] == "changed" and report["changes"][0]["facets"] == [
            "resolution"
        ]
        assert report["before"]["producer"]["operation_id"] == "rich.admit"
        assert report["scope"]["original_source_completeness"] == "unknown"
        replay = comparison.ExclusionComparisonRequest.model_validate(
            comparison.decode_rich_cursor(report["resource_handle"])
        )
        assert comparison.compare_selected_exclusions(None, replay)["changes"] == report["changes"]
        bad = selected.model_copy(
            update={"before": selected.before.model_copy(update={"use_id": "other-use"})}
        )
        with pytest.raises(ValueError, match="exactly one actual selected whole"):
            comparison.compare_selected_exclusions(None, bad)
    finally:
        before.index.close()
        after.index.close()


def test_comparison_mcp_and_cli_keep_two_cuts_exact_values_and_retention_after_transaction(
    monkeypatch, tmp_path
):
    from corpus_structure.cli import research
    from corpus_structure.cli.managed import ResultStore
    from corpus_structure.intervene import contribution_facet_tools as tools
    from corpus_structure.intervene.semantic_server import build_retained_reader_server

    selected = comparison.ExclusionComparisonRequest(
        before=comparison.ConstraintRootPin(
            demand_id="before",
            project_id="p",
            product_id="root:before",
            use_id="use:before",
            derivation_id="episode:before",
            read_id="read:before",
            cut_id="cut:before",
        ),
        after=comparison.ConstraintRootPin(
            demand_id="after",
            project_id="p",
            product_id="root:after",
            use_id="use:after",
            derivation_id="episode:after",
            read_id="read:after",
            cut_id="cut:after",
        ),
    )
    fraction = Decimal("0.123456789123456789123456789")
    seen = []
    committed = []

    def read(connection, request):
        seen.append(request)
        return dict(
            before={"pin": request.before.model_dump(mode="python")},
            after={"pin": request.after.model_dump(mode="python")},
            changes=[{"alignment_score": fraction}],
            resource_handle=comparison._cursor(request.model_dump(mode="python")),
        )

    engine = create_engine("sqlite://")

    @contextmanager
    def transaction(engine):
        yield None
        committed.append(True)

    store = ResultStore(tmp_path / "results")
    monkeypatch.setattr(comparison, "compare_selected_exclusions", read)
    monkeypatch.setattr(tools, "compare_selected_exclusions", read)
    monkeypatch.setattr(
        "corpus_structure.semantic.runtime.open_runtime_engine", lambda *a, **k: nullcontext(engine)
    )
    monkeypatch.setattr(research, "selected_read_snapshot", transaction)
    monkeypatch.setattr(research, "state", lambda ctx: SimpleNamespace(settings=lambda: None))
    monkeypatch.setattr("corpus_structure.cli.managed.result_store", lambda ctx: store)
    path = tmp_path / "comparison.json"
    path.write_bytes(json_bytes(selected.model_dump(mode="python")))
    result = CliRunner().invoke(
        app, ["research", "compare-exclusions", "--request", str(path), "--retain", "--json"]
    )
    assert result.exit_code == 0, result.output
    report = json_loads(result.stdout)
    assert committed == [True]
    assert report["changes"][0]["alignment_score"] == fraction
    assert store.read_artifact(report["retained"]["result_id"], "comparison") == json_bytes(
        {key: value for key, value in report.items() if key != "retained"}
    )
    assert store.show(report["retained"]["result_id"]).outcome == "passed"

    async def run():
        async with Client(build_retained_reader_server(project="p", read_engine=engine)) as client:
            response = await client.call_tool(
                "compare_identity_exclusions", {"request": selected.model_dump(mode="python")}
            )
            assert not response.is_error and response.structured_content is not None
            assert response.structured_content["cut_ids"] == ["cut:before", "cut:after"]
            assert (
                json_loads(response.structured_content["exact_json"])["changes"][0][
                    "alignment_score"
                ]
                == fraction
            )
            changed = selected.model_copy(
                update={"after": selected.after.model_copy(update={"project_id": "other-project"})}
            )
            rejected = await client.call_tool(
                "compare_identity_exclusions",
                {"request": changed.model_dump(mode="python")},
                raise_on_error=False,
            )
            assert rejected.is_error

    try:
        anyio.run(run)
    finally:
        engine.dispose()
    assert len(seen) == 2


def test_comparison_transaction_failure_retains_original_error_and_never_publishes_success(
    monkeypatch, tmp_path
):
    from corpus_structure.cli import research
    from corpus_structure.cli.managed import ResultStore

    selected = comparison.ExclusionComparisonRequest(
        before=comparison.ConstraintRootPin(
            demand_id="before",
            project_id="p",
            product_id="a",
            use_id="u:a",
            derivation_id="e:a",
            read_id="r:a",
            cut_id="c:a",
        ),
        after=comparison.ConstraintRootPin(
            demand_id="after",
            project_id="p",
            product_id="b",
            use_id="u:b",
            derivation_id="e:b",
            read_id="r:b",
            cut_id="c:b",
        ),
    )
    bug = ValueError("unexpected transaction failure")

    @contextmanager
    def transaction(engine):
        yield None
        raise bug

    store = ResultStore(tmp_path / "results")
    monkeypatch.setattr(
        comparison,
        "compare_selected_exclusions",
        lambda connection, request: {"actual_read_completed": True},
    )
    monkeypatch.setattr(
        "corpus_structure.semantic.runtime.open_runtime_engine", lambda *a, **k: nullcontext(None)
    )
    monkeypatch.setattr(research, "selected_read_snapshot", transaction)
    monkeypatch.setattr(research, "state", lambda ctx: SimpleNamespace(settings=lambda: None))
    monkeypatch.setattr("corpus_structure.cli.managed.result_store", lambda ctx: store)
    path = tmp_path / "request.json"
    path.write_bytes(json_bytes(selected.model_dump(mode="python")))
    result = CliRunner().invoke(
        app, ["research", "compare-exclusions", "--request", str(path), "--retain", "--json"]
    )
    assert result.exception is bug
    records = store.list(None, 20, None).results
    assert (
        len(records) == 1
        and records[0].outcome == "failed"
        and "comparison" not in records[0].artifacts
    )
