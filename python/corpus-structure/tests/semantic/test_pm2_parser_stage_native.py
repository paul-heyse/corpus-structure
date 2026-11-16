"""Current PM2 intent, eligibility and producing-attempt custody."""

import json
import os
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic._data_operation_wire import (
    WireClaimDataRequestRequest,
    WirePublishDataDerivationRequest,
)
from corpus_structure.semantic.data_operation_demands import DemandPlanner
from corpus_structure.semantic.data_operation_service import cancel_data_demand
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from semantic.current_pdf_source_support import (
    admit_current_target,
    current_consumer_request,
    selected_current_sources,
)
from semantic.current_pdf_source_support import (
    current_pdf_source_factory as current_pdf_source_factory,
)
from semantic.current_pm2_native_support import (
    execute,
    page,
    parser_recipe,
    projection_recipe,
    projection_request,
    pure_source,
    register,
    reports,
    table_source,
)
from semantic.current_pm2_native_support import projection_prepared as projection_prepared

DIPO = "text.dipo/source-native"


def test_partial_original_scope_is_ineligible_for_whole_block_inspection(projection_prepared):
    from corpus_structure.semantic.sentence_products import _blocks
    from corpus_structure.semantic.source_products import FrozenNativeSource

    source, _, _ = pure_source(projection_prepared)
    selected = source.value
    selected["selectors"] = [{"projection": selected["source"]["projection"], "start": 0, "end": 1}]
    partial = FrozenNativeSource.acquire(projection_prepared.prepared, selected)
    blocks, coverage = _blocks(partial)
    assert not blocks
    assert len(coverage) == 1 and coverage[0]["outcome"] == "unsupported"
    assert coverage[0]["reason"] == "selected scope does not contain the complete original block"
    assert (coverage[0]["start"], coverage[0]["end"]) == (0, 2)
    # This is explicit unexamined original scope, not completed-empty inference.
    assert not any(item["outcome"] in {"empty", "complete"} for item in coverage)


def test_unrequested_parser_scope_is_not_invented_as_an_empty_product(
    scenario_seeds, tmp_path, monkeypatch
):
    with table_source(scenario_seeds, tmp_path, monkeypatch) as source:
        kernel = admit_current_target(source, projection_recipe(tmp_path), tmp_path / "consumer")
        ((row, _),) = selected_current_sources(source)
        demand = register(kernel, projection_request(kernel, row, mode="literal"))
        execute(kernel, demand)
        snapshot = page(kernel, demand)
        requested = {item["operation"] for item in snapshot.record["intent"]["operations"]}
        assert (
            not {DIPO, "text.hanlp_native/source-native", "text.maverick/source-native"} & requested
        )
        assert {item["operation_id"] for item in snapshot.record["obligations"]} == {
            "fixture.pm2_projection"
        }
        assert not any(
            item["family"].startswith(("dipo", "hanlp", "maverick"))
            for member in snapshot.members()
            if member["member_id"] is None
            for item in member["body"].get("coverage", ())
        )
        assert snapshot.record["attempt_failures"] == []


def test_cancelled_current_pm2_scope_has_no_product_or_inspected_count(
    scenario_seeds, tmp_path, monkeypatch
):
    with table_source(scenario_seeds, tmp_path, monkeypatch) as source:
        kernel = admit_current_target(source, projection_recipe(tmp_path), tmp_path / "consumer")
        ((row, _),) = selected_current_sources(source)
        demand = register(kernel, projection_request(kernel, row))
        with kernel.purpose("write").begin() as connection:
            assert (
                cancel_data_demand(
                    connection, demand, reason="operator cancelled before inspection"
                )["state"]
                == "cancelled"
            )
        result = execute(kernel, demand)
        assert result.receipt_count == 0
        snapshot = page(kernel, demand)
        assert snapshot.record["state"] == "cancelled"
        assert snapshot.record["uses"] and all(
            item["fate"] == "cancelled" for item in snapshot.record["uses"]
        )
        assert snapshot.members() == ()
        assert snapshot.record["attempt_failures"] == []


@pytest.mark.gpu
@pytest.mark.provider_evidence
@pytest.mark.prerequisite("pm2_native_assets")
def test_actual_dipo_reclaim_refuses_stale_holder_before_current_publication(
    current_pdf_source_factory, tmp_path, monkeypatch
):
    from corpus_structure.orchestrate.data_operations import NativeDemandExecutor

    passage = "The sensor records each request. It writes a receipt."
    with current_pdf_source_factory((("text", passage, passage, None),)) as source:
        kernel = admit_current_target(
            source,
            parser_recipe(Path(os.environ["CORPUS_PM2_NATIVE_TEST_ASSETS"])),
            tmp_path / "consumer",
        )
        demand = register(kernel, current_consumer_request(source, kernel, (DIPO,), discover=True))
        old = None
        # Advance real discovery/sentence dependencies; stop before this real
        # DiPO request is executed so its first holder can genuinely expire.
        for _ in range(12):
            with kernel.purpose("write").begin() as connection:
                planner = DemandPlanner(kernel.model, DataOperationStorage(connection))
                ready = planner.ready(planner.resume(demand), authorization=b"{}")
                selected = next((item for item in ready if item.operation == DIPO), None)
                if selected is not None:
                    claimed = DataOperationStorage(connection).claim_data_request(
                        cast(
                            WireClaimDataRequestRequest,
                            dict(
                                request_id=json.loads(selected.native)["request_id"],
                                           generation=json.loads(selected.native)["generation"],
                                holder="old-dipo-holder",
                                lease_seconds=30,
                            ),
                        )
                    )
                    assert claimed["state"] == "claimed"
                    old = {
                        name: claimed[name]
                        for name in ("request_id", "generation", "task_id", "attempt", "holder")
                    }
            if old is not None:
                break
            execute(kernel, demand, rounds=1)
        assert old is not None, "current source/sentence dependencies never made DiPO ready"
        with source.kernel.clone.admin.begin() as connection:
            connection.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
            assert (
                connection.execute(
                    text(
                        "UPDATE ops.task SET lease_until=clock_timestamp()-interval '1 second' WHERE id=:task"
                    ),
                    {"task": old["task_id"]},
                ).rowcount
                == 1
            )
        original = NativeDemandExecutor._retain_answer
        observed = []

        def retain(executor, ready, claim, answer, port, owner, *, physical):
            intent = original(executor, ready, claim, answer, port, owner, physical=physical)
            if ready.operation == DIPO and claim.request_id == old["request_id"]:
                assert claim.task_id == old["task_id"] and claim.attempt > old["attempt"]
                # The actual provider computation and retained new intent exist.
                # Before its publication, the stale holder has no publish effect.
                with (
                    kernel.purpose("write").begin() as connection,
                    pytest.raises(DBAPIError, match="stale"),
                    connection.begin_nested(),
                ):
                    DataOperationStorage(connection).publish_data_derivation(
                        cast(WirePublishDataDerivationRequest, {**old, "intent_id": intent})
                    )
                observed.append((claim, intent))
            return intent

        with monkeypatch.context() as patch:
            patch.setattr(NativeDemandExecutor, "_retain_answer", retain)
            execute(kernel, demand)
        assert len(observed) == 1
        ((claim, intent),) = observed
        with source.kernel.clone.admin.connect() as connection:
            retained = connection.execute(
                text(
                    "SELECT producer_task_id,producer_attempt,payload->'execution_evidence' AS evidence FROM ops.data_completion_intent WHERE id=:intent"
                ),
                {"intent": intent},
            ).one()
        assert (
            retained.producer_task_id == claim.task_id
            and retained.producer_attempt == claim.attempt
        )
        assert retained.evidence["provider_receipts"]
        assert all(
            item["provider"] == "dipo"
            for receipt in retained.evidence["provider_receipts"]
            for item in receipt["physical"]
        )
        values, snapshot = reports(kernel, demand, operation=DIPO)
        assert {item["role"] for item in values} == {"result", "candidates"}
        assert any(item["body"]["members"] for item in values if item["role"] == "candidates")
        uses = {
            item["obligation_id"]
            for item in snapshot.record["obligations"]
            if item["operation_id"] == DIPO
        }
        assert all(
            item["fate"] == "fulfilled"
            for item in snapshot.record["uses"]
            if item["obligation_id"] in uses
        )
