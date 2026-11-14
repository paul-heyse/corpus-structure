"""Independent native-progress projections preserve unknowns, custody and exact pins."""

from contextlib import nullcontext
from typing import Any, cast
from uuid import UUID

import pytest

from corpus_structure.orchestrate.source_lineage import SourceOperationLink
from corpus_structure.orchestrate.source_progress import (
    OperationProgressCursor,
    SettledProduct,
    project_operation_progress,
)
from corpus_structure.semantic.characterization_store import CharacterizationProductSummary
from corpus_structure.semantic.product_reference import ProductReference

OPERATION = UUID("00000000-0000-0000-0000-000000000123")
BASE = ProductReference(7, "integrated", "a" * 64)
LAYER = ProductReference(8, "layer", "b" * 64)
VIEW = ProductReference(9, "view", "c" * 64)


def summary(*, kind="view", readiness="enriched", outcome="complete", omitted=0):
    return CharacterizationProductSummary.model_validate(
        dict(
            base_document=BASE,
            profile="full_characterization" if kind == "view" else None,
            outcome=None if kind == "view" else outcome,
            readiness=readiness if kind == "view" else None,
            coverage=[dict(family="syntax", outcome=outcome, availability="available")],
            coverage_omitted=omitted,
            layer_count=1 if kind == "view" else 0,
            active_layer_count=1 if kind == "view" else 0,
            providers=[]
            if kind == "view"
            else [
                dict(
                    provider="hanlp",
                    profile="historical-cpu-profile",
                    model="original-model",
                    model_version="v1",
                    runtime_version="old-runtime",
                    configuration_digest="d" * 64,
                    availability=[dict(family="syntax", attribute="dependency", status="complete")],
                    availability_omitted=0,
                )
            ],
            providers_omitted=0,
        )
    )


def product(kind, *, region=0, summary_value=None):
    return SettledProduct(
        reference=VIEW if kind == "view" else LAYER,
        kind=kind,
        selected_run_id=11,
        producer_run_id=300,
        region=region,
        release_id="original-release",
        method="text.test",
        summary=summary_value,
        summary_availability="available" if summary_value is not None else "unavailable",
    )


def projection(
    *, products=(), link=True, region_count=1, document_count=1, region_rows=None, omissions=()
):
    primary = SourceOperationLink(operation_id=OPERATION, role="primary", capture_run_id=10)
    row = dict(
        id=11,
        project_id="project",
        release_id="current-release",
        input_realization_id="input",
        options={"physical_policy": {"workers": 2}},
    )
    run_rows: list[dict[str, Any]] = [
        dict(
            id=10,
            options={
                "source_operation": SourceOperationLink(
                    operation_id=OPERATION, role="capture"
                ).model_dump(mode="json")
            },
            status="finished",
            source_ready=True,
            supervisor="inactive",
        ),
        dict(
            id=11,
            options={
                "source_operation": primary.model_dump(mode="json"),
                "characterization_region": 0,
                "characterization_stage": ["text.test"],
            },
            status="running",
            source_ready=True,
            supervisor="active",
            has_demand=True,
        ),
    ]
    if not link:
        run_rows = [run_rows[1]]
        run_rows[0]["options"].pop("source_operation")
    return project_operation_progress(
        row=row,
        link=primary if link else None,
        anchor=11,
        run_rows=run_rows,
        run_count=len(run_rows),
        task_counts={"reused": 1, "running": 1},
        stage_rows=[
            dict(
                run_id=11,
                region=0,
                method="text.test",
                stage="extract",
                status="reused",
                reason=None,
                count=1,
                task_ids=(21,),
                task_ids_omitted=0,
            )
        ],
        region_rows=region_rows
        if region_rows is not None
        else [
            dict(
                index=0,
                base_document=BASE.values(),
                source_only=False,
                original_sources=[dict(run_id=3, source_view_id=42)],
                original_sources_omitted=0,
                declared_methods=["text.test"],
            )
        ],
        region_count=region_count,
        document_count=document_count,
        products=products,
        selected_input_views=(),
        after_region=-1,
        region_limit=8,
        next_region=None,
        next_run=None,
        omissions=omissions,
    )


def test_aggregate_keeps_actual_capture_distinct_from_original_reused_product_provenance():
    result = projection(
        products=(
            product("layer", summary_value=summary(kind="layer")),
            product("view", summary_value=summary()),
        )
    )
    assert (
        result.capture_run_id == 10
        and result.capture_run_id != result.regions[0].original_sources[0]["run_id"]
    )
    assert result.capture_readiness == "source_ready" and result.view_readiness == "enriched"
    assert result.final_views == (VIEW,) and result.regions[0].families[0].outcome == "complete"
    assert result.settled_products[0].selected_run_id == 11
    assert result.settled_products[0].producer_run_id == 300
    assert (
        result.providers[0].producing_run_id == 300 and result.providers[0].producing_task_id == 8
    )
    assert result.providers[0].provenance.profile == "historical-cpu-profile"
    assert result.providers[0].standing == "historical_native_product"
    assert result.providers[0].live_activity == "unknown"
    assert result.activity.owner_availability == "active"
    assert result.activity.physical_availability == "unavailable" and result.activity.phase is None
    assert result.task_counts == {"reused": 1, "running": 1}


def test_missing_metadata_does_not_turn_a_settled_pin_into_complete_or_absent_work():
    result = projection(products=(product("view"),))
    assert result.regions[0].views == (VIEW,)
    assert result.regions[0].readiness == result.view_readiness == "unknown"
    assert result.providers == () and result.provider_provenance_availability == "unavailable"
    assert not result.regions[0].coverage_metadata_complete


def test_historical_anchor_does_not_guess_enclosing_capture_from_original_sources():
    result = projection(products=(product("view", summary_value=summary()),), link=False)
    assert result.association == "historical_anchor" and result.operation_id is None
    assert result.capture_run_id is None and result.capture_association == "unavailable"
    assert result.capture_readiness == "unknown"


def test_regional_view_does_not_establish_combined_full_document_readiness():
    result = projection(products=(product("view", summary_value=summary()),), region_count=2)
    assert result.regions[0].readiness == "enriched"
    assert result.final_views == () and result.view_readiness == "unsettled"


def test_partial_family_outcome_survives_final_view_projection():
    result = projection(
        products=(product("view", summary_value=summary(readiness="partial", outcome="partial")),)
    )
    assert result.view_readiness == result.regions[0].readiness == "partial"
    assert result.regions[0].families[0].outcome == "partial"


def test_bounded_family_detail_does_not_change_authenticated_view_readiness():
    result = projection(products=(product("view", summary_value=summary(omitted=1)),))
    assert result.view_readiness == "enriched"
    assert not result.regions[0].coverage_metadata_complete
    assert result.detail_omissions
    minimized = result.without_details()
    assert minimized.task_counts == result.task_counts and minimized.view_readiness == "enriched"
    assert minimized.regions == () and minimized.detail_omissions


def test_typed_cursor_preserves_native_scope_and_nested_inventory_position():
    cursor = OperationProgressCursor(
        selected_run_id=11,
        scope_id=str(OPERATION),
        after_region=7,
        after_run=22,
        product_run_id=23,
        product_after=(24, "view"),
    )
    assert OperationProgressCursor.decode(cursor.encode()) == cursor
    with pytest.raises(ValueError, match="cursor"):
        OperationProgressCursor.decode("not a cursor")


def test_native_inventory_adapter_validates_bounded_summary_without_reading_payload(monkeypatch):
    from corpus_structure.semantic import _operation_calls
    from corpus_structure.semantic.characterization_store import read_inventory

    observed = []
    value = dict(
        products=[
            dict(
                reference=VIEW.values(),
                kind="view",
                producer_run_id=300,
                summary=summary().model_dump(mode="json"),
            )
        ],
        continuation=None,
    )
    monkeypatch.setattr(
        _operation_calls,
        "read_characterization_inventory",
        lambda *a, **kw: observed.append(kw) or value,
    )
    result = read_inventory(cast(Any, object()), 11, limit=8, max_bytes=262144)
    assert result["products"][0]["summary"]["readiness"] == "enriched"
    assert observed[0]["limit"] == 8 and observed[0]["max_bytes"] == 262144
    assert "annotations" not in result["products"][0]["summary"]


def test_native_progress_queries_parse_and_page_under_exact_uuid_scope(monkeypatch):
    from pglast import parse_sql
    from sqlalchemy.dialects import postgresql

    from corpus_structure.orchestrate import source_progress

    link = SourceOperationLink(operation_id=OPERATION, role="primary", capture_run_id=10)
    row = dict(
        id=11,
        project_id="project",
        release_id="release",
        input_realization_id="input",
        options={"source_operation": link.model_dump(mode="json")},
        has_characterization_demand=True,
    )
    calls = []

    class Rows:
        def __init__(self, values):
            self.values = values

        def mappings(self):
            return self

        def scalars(self):
            return iter(self.values)

        def one(self):
            assert len(self.values) == 1
            return self.values[0]

        def one_or_none(self):
            return self.values[0] if self.values else None

        def all(self):
            return self.values

        def __iter__(self):
            return iter(self.values)

    class Connection:
        def begin_nested(self):
            return nullcontext()

        def execute(self, statement, params=None):
            compiled = str(
                statement.compile(dialect=postgresql.dialect(paramstyle="numeric_dollar"))
            )
            parse_sql(compiled)
            sql = " ".join(str(statement).split())
            calls.append((sql, params))
            if "SELECT r.id FROM ops.run" in sql:
                return Rows([11])
            if " AS region_count" in sql:
                return Rows(
                    [
                        dict(
                            project_id="project",
                            release_id="release",
                            input_realization_id="input",
                            region_count=1,
                            document_count=1,
                        )
                    ]
                )
            if "ordinal-1 AS index" in sql:
                return Rows(
                    [
                        dict(
                            index=0,
                            base_document=BASE.values(),
                            source_only=False,
                            original_sources=[dict(run_id=3)],
                            original_sources_omitted=0,
                            declared_methods=["text.test"],
                        )
                    ]
                )
            if "GROUP BY t.status" in sql:
                return Rows([("done", 2)])
            if "AS has_demand" in sql:
                return Rows(
                    [
                        dict(
                            id=10,
                            project_id="project",
                            release_id="release",
                            input_realization_id="input",
                            status="finished",
                            sealed=True,
                            options={"source_operation": SourceOperationLink(
                                operation_id=OPERATION, role="capture"
                            ).model_dump(mode="json")},
                            has_demand=False,
                        ),
                        dict(
                            id=11,
                            project_id="project",
                            release_id="release",
                            input_realization_id="input",
                            status="running",
                            sealed=False,
                            options={
                                "source_operation": link.model_dump(mode="json"),
                                "characterization_region": 0,
                                "characterization_stage": ["text.test"],
                            },
                            has_demand=True,
                        ),
                    ]
                )
            if "run_supervisor_held" in sql:
                return Rows([(False, True)])
            if "WITH groups AS" in sql:
                return Rows(
                    [
                        dict(
                            run_id=11,
                            region=0,
                            method_id=1,
                            method="text.test",
                            stage="extract",
                            status="done",
                            reason=None,
                            count=2,
                            task_ids=[21, 22],
                            task_ids_omitted=0,
                            group_count=1,
                        )
                    ]
                )
            raise AssertionError(sql)

        def scalar(self, statement, params=None):
            parse_sql(
                str(statement.compile(dialect=postgresql.dialect(paramstyle="numeric_dollar")))
            )
            return 2 if "count(*)" in str(statement) else 1

    monkeypatch.setattr(
        source_progress,
        "read_inventory",
        lambda *a, **kw: dict(
            products=[
                dict(
                    reference=VIEW.values(),
                    kind="view",
                    producer_run_id=300,
                    release_id="original-release",
                    method="text.test",
                    summary=summary().model_dump(mode="json"),
                )
            ],
            continuation=None,
        ),
    )
    result = source_progress.read_source_operation_progress(Connection(), row)
    assert result is not None
    assert result.operation_id == OPERATION and result.capture_run_id == 10
    assert result.view_readiness == "enriched" and result.task_counts == {"done": 2}
    grouped = [params for sql, params in calls if "operation_id'=:operation" in sql]
    assert grouped and all(
        value is not None and value["operation"] == str(OPERATION) for value in grouped
    )


def test_protected_summary_function_and_inventory_query_have_valid_postgresql_grammar():
    from pathlib import Path

    from pglast import parse_sql

    path = Path(__file__).parents[2] / "src/corpus_structure/semantic/sql/characterization.sql"
    source = path.read_text()
    start = source.index("CREATE OR REPLACE FUNCTION ops.read_characterization_inventory(")
    stop = source.index("\nEND $$;", start) + len("\nEND $$;")
    function = source[start:stop]
    assert len(parse_sql(function)) == 1
    # The standalone PL parser cannot resolve private ops.run composite types.
    # Parse the exact added SQL projection; the forward native candidate owns
    # real PLpgSQL/catalogue/ACL qualification in PostgreSQL.
    query_start = function.index(" SELECT coalesce(jsonb_agg(body")
    query_end = function.index(" ) bounded;", query_start) + len(" ) bounded;")
    assert len(parse_sql(function[query_start:query_end])) == 1


def test_two_single_region_documents_do_not_require_synthetic_combined_stages():
    second_base = ProductReference(70, "integrated", "d" * 64)
    second_view = ProductReference(90, "view", "e" * 64)
    second = SettledProduct(
        reference=second_view,
        kind="view",
        selected_run_id=12,
        producer_run_id=400,
        region=1,
        release_id="original-release",
        method="text.test",
        summary=summary().model_copy(update={"base_document": second_base}),
        summary_availability="available",
    )
    rows = [
        dict(
            index=index,
            base_document=base.values(),
            source_only=False,
            original_sources=[],
            original_sources_omitted=0,
            declared_methods=["text.test"],
        )
        for index, base in enumerate((BASE, second_base))
    ]
    result = projection(
        products=(product("view", summary_value=summary()), second),
        region_count=2,
        document_count=2,
        region_rows=rows,
    )
    assert result.view_readiness == "enriched"
    assert set(result.final_views) == {VIEW, second_view}
