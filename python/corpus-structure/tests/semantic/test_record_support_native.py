"""Current native support custody, bounded diagnostics and revocation."""

from decimal import Decimal
from typing import cast

import pytest
from evaluate.declared_record_native_support import PROJECT, run_readings
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic._data_operation_wire import WireRevokeDataSupportRequest
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
from corpus_structure.semantic.rich_queries import SourceReadingsQuery
from semantic.record_publication_native_support import (
    publish_readings,
    query_publication,
)
from semantic.record_publication_native_support import (
    rich_publication as rich_publication,
)


def test_native_support_keeps_actual_raw_resolution_and_admission_producers(
    rich_publication, monkeypatch
):
    from evaluate.declared_record_native_support import complete_policy_fit
    from evaluate.declared_rich_native_journey_test_support import verify_completion_refusals
    from evaluate.declared_rich_native_support import selected_policy_authorization

    from corpus_structure.semantic.data_operation_identity import decode_semantic_value

    journey = rich_publication

    with verify_completion_refusals(journey, monkeypatch):
        fitted = complete_policy_fit(journey)
        authorization = selected_policy_authorization(fitted)
        source = next(
            source
            for source in journey.sources
            if source.pin == fitted.calibration.grade.frame.coverage[0].source
        )
        selected = publish_readings(
            journey,
            fitted.calibration_readings,
            source=source,
            authorization=authorization,
            inference="actual-record-support",
        )
    assert len(selected.admission.selected_reading_ids) == 2
    assert selected.admission.selected_fact_ids == ()
    page = query_publication(selected, SourceReadingsQuery(name="source_readings"), limit=1)
    assert len(page["rows"]) == 1 and page["cursor"] is not None
    second = query_publication(
        selected, SourceReadingsQuery(name="source_readings"), cursor=page["cursor"]
    )
    rows = [*page["rows"], *second["rows"]]
    assert len(rows) == 2 and {row["scientific_truth"] for row in rows} == {"not-established"}
    assert {
        Decimal(decode_semantic_value(row["reading"])["value"]["value"]["lexical"]) for row in rows
    } == {Decimal(12)}
    with journey.kernel.engine.begin() as connection:
        for row in rows:
            assertion = row["assertion"]
            for name, operation in (
                ("original", "fixture.record_candidates"),
                ("resolution", "resolve.m1_readings/declared"),
            ):
                (support,) = assertion[name]["support_references"]
                assert support["kind"] == "computation"
                assert (
                    connection.scalar(
                        text(
                            "SELECT request.operation_id FROM ops.data_derivation episode JOIN ops.data_request request ON request.id=episode.request_id WHERE episode.id=:id"
                        ),
                        {"id": support["derivation_id"]},
                    )
                    == operation
                )
            assert assertion["source_interpretation_id"] != assertion["interpretation_id"]
        (support,) = selected.admission.consolidation.support_references
        assert isinstance(support, ComputationalSupportReference)
        assert (
            connection.scalar(
                text("SELECT ops.ddo_node_valid('episode',:episode)"),
                {"episode": support.derivation_id},
            )
            is True
        )
        DataOperationStorage(connection).revoke_data_support(
            cast(
                WireRevokeDataSupportRequest,
                {
                    "project_id": PROJECT,
                    "original_source": source.pin.original_source,
                    "selector_kind": "product",
                    "selector": source.pin.source_product,
                    "reason": "actual source-product revocation",
                },
            )
        )
        assert (
            connection.scalar(
                text("SELECT ops.ddo_node_valid('episode',:episode)"),
                {"episode": support.derivation_id},
            )
            is False
        )
    with pytest.raises(DBAPIError, match="read trust changed; reacquire demand read") as rejected:
        query_publication(
            selected, SourceReadingsQuery(name="source_readings"), cursor=page["cursor"]
        )
    assert getattr(rejected.value.orig, "sqlstate", None) == "23514"


def test_native_large_diagnostics_remain_in_actual_support_without_forcing_public_body(
    rich_publication,
):
    from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
    from corpus_structure.semantic.demand_results import (
        SelectedGraphBudgetExceeded,
        selected_record_index,
    )

    journey = rich_publication
    source = journey.sources[0]
    readings = run_readings(
        journey,
        (source,),
        policy=None,
        diagnostic_bytes=2 * 1024**2,
        # Inspect the actual large private payload one obligation at a time;
        # the separate public read below retains its 64 KiB contract.
        page_rows=1,
        max_bytes=16 * 1024**2,
        inference="actual-large-record-diagnostic",
    )
    ((raw_product, raw),) = readings.raw
    assert json_loads(raw["diagnostics_json"])["controlled_large"] == "x" * (2 * 1024**2)
    selected = publish_readings(
        journey,
        readings,
        source=source,
        inference="bounded-record-diagnostic-support",
        # The publication's private support includes the same full diagnostic body.
        page_rows=1,
        max_bytes=16 * 1024**2,
    )
    assert selected.admission.selected_reading_ids == ()
    assert raw_product["id"] in {
        reference.product_id for reference in selected.consolidation.input_population
    }
    page = query_publication(
        selected, SourceReadingsQuery(name="source_readings"), max_bytes=64 * 1024
    )
    assert page["rows"] == [] and len(json_bytes(page)) <= 64 * 1024
    with (
        journey.kernel.purpose("read").begin() as connection,
        pytest.raises(SelectedGraphBudgetExceeded),
        selected_record_index(
            connection,
            readings.demand_id,
            project_id=PROJECT,
            scope={"product_ids": [raw_product["id"]]},
            max_total_bytes=64 * 1024,
        ),
    ):
        raise AssertionError("oversized exact support escaped its declared graph bound")
