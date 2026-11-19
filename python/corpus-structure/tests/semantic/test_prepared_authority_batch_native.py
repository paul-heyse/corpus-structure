"""Genuine CPU batch replies, native claims/intents and original-producer adoption."""

from copy import deepcopy
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.orchestrate.data_operations import (
    NativeDemandExecutionError,
    NativeDemandExecutor,
)
from corpus_structure.semantic._data_operation_wire import WireAdoptDataCompletionIntentRequest
from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
    OperationSelection,
    RootSubject,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_service import execute_data_demand
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.data_operation_support import authored_fact_selection
from corpus_structure.semantic.data_operation_values import semantic_value
from semantic.data_operation_demand_support import claim, publish
from semantic.prepared_batch_control import controlled_recipe, controlled_sources

OPERATION = "urn:controlled:prepared-batch-add-one"
ROOT = Path(__file__).resolve().parents[4]


def test_controlled_batch_source_has_explicit_preparation_form_and_complete_recipe():
    from corpus_structure.semantic.data_operation_compilation import compile_data_operations

    model = compile_data_operations(python_sources=controlled_sources())
    operation = model.operation(OPERATION)
    assert operation.capabilities.forms == ("batch",)
    assert operation.capabilities.prepared_factory is not None
    assert all(value.complete for value in model.implementation_slices), [
        (value.root, value.unknowns) for value in model.implementation_slices if not value.complete
    ]


def _demand(kernel):
    contexts = tuple(
        SubjectContext("ddo-test", key, None, b"{}", subject_definition="controlled-value")
        for key in ("one", "two")
    )
    authored = tuple(
        authored_fact_selection(
            "integer:" + context.subject,
            value,
            kind_contract=kernel.identities["primitive:integer", "kind"],
            context=context,
            author="test operator",
            selection_id="selected-integral-input",
        )
        for context, value in zip(contexts, (4, 8), strict=True)
    )
    intent = freeze_demand(
        kernel.model,
        roots=tuple(RootSubject(value.subject, None, b"{}") for value in contexts),
        targets=(OPERATION,),
        selections=(OperationSelection(OPERATION, replicate="actual-batch-observation-A"),),
        inference="actual-integral-batch-control",
        execution_profile=kernel.recipe.execution_profile,
        original_sources=authored,
    )
    with kernel.purpose("write").begin() as connection:
        return DemandPlanner(kernel.model, DataOperationStorage(connection)).register(
            intent, project="ddo-test", release=kernel.prepared.release_id, runtime=kernel.runtime
        )["demand_id"]


def _native_output(connection, request_id, completion):
    return connection.scalar(
        text(
            "SELECT ops.ddo_cpu_reply_output(r,CAST(:completion AS jsonb)) FROM ops.data_request r WHERE r.id=:request"
        ),
        {"request": request_id, "completion": json_bytes(completion).decode()},
    )


@pytest.mark.parametrize("ddo_kernel", [controlled_recipe()], indirect=True)
def test_real_batch_retained_intent_keeps_original_member_after_adoption(
    ddo_kernel, monkeypatch, tmp_path
):
    kernel = ddo_kernel
    demand = _demand(kernel)

    def stop_after_actual_retention(self, claim, intent, owner):
        raise RuntimeError("controlled stop after genuine CPU reply and native retention")

    with monkeypatch.context() as patch:
        patch.setattr(NativeDemandExecutor, "_publish", stop_after_actual_retention)
        with pytest.raises(NativeDemandExecutionError):
            execute_data_demand(
                kernel.purpose("write"),
                demand,
                source_root=ROOT,
                project_id="ddo-test",
                admission_engine=kernel.purpose("admit"),
                database_capacity=6,
            )
    with kernel.engine.connect() as connection:
        intents = list(
            connection.execute(
                text("SELECT * FROM ops.data_completion_intent ORDER BY request_id")
            ).mappings()
        )
        assert len(intents) == 2
        original = dict(intents[0])
        payload = original["payload"]
        replies = {row["payload"]["execution_evidence"]["cpu_replies"][0] for row in intents}
        assert len(replies) == 1, "logical completions retain the same actual whole CPU batch reply"
        outputs = [_native_output(connection, row["request_id"], row["payload"]) for row in intents]
        assert sorted(outputs) == [semantic_value(5), semantic_value(9)]
        assert connection.scalar(text("SELECT count(*) FROM ops.data_publication_receipt")) == 0
    successor = claim(kernel, original, holder="adopting-holder")
    assert successor["attempt"] > original["producer_attempt"]
    with kernel.engine.begin() as connection:
        adopted = DataOperationStorage(connection).adopt_data_completion_intent(
            cast(WireAdoptDataCompletionIntentRequest, {**successor, "intent_id": original["id"]})
        )
        assert adopted["producer_task_id"] == original["producer_task_id"]
        assert adopted["producer_attempt"] == original["producer_attempt"]
        assert _native_output(connection, original["request_id"], payload) in (
            semantic_value(5),
            semantic_value(9),
        )
        subject = connection.scalar(
            text("SELECT subject FROM ops.data_request WHERE id=:request"),
            {"request": original["request_id"]},
        )
        forged = deepcopy(payload)
        forged["execution_evidence"].update(successor)
        # The CPU reply and physical receipt remain the actual originals. Only
        # the attempted replacement of original native attribution is corrupt.
        with (
            pytest.raises(
                DBAPIError, match=r"original intent|original retained intent|original producer"
            ),
            connection.begin_nested(),
        ):
            _native_output(connection, original["request_id"], forged)
    publish(kernel, successor, {"intent_id": original["id"]})
    with kernel.engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT d.producer_task_id,d.producer_attempt,p.publishing_attempt FROM ops.data_derivation d JOIN ops.data_publication_receipt p ON p.derivation_id=d.id WHERE d.intent_id=:intent"
            ),
            {"intent": original["id"]},
        ).one()
        assert (row.producer_task_id, row.producer_attempt, row.publishing_attempt) == (
            original["producer_task_id"],
            original["producer_attempt"],
            successor["attempt"],
        )
        assert _native_output(connection, original["request_id"], payload) in (
            semantic_value(5),
            semantic_value(9),
        )

    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.semantic.data_operation_values import decode_semantic_value
    from corpus_structure.serve.demand_export import export_demand_result, verify_demand_export

    expected_input, expected_output = {"one": (4, 5), "two": (8, 9)}[subject]
    for encoding in ("jsonl", "parquet"):
        destination = tmp_path / encoding
        with kernel.purpose("read").begin() as connection:
            manifest = export_demand_result(
                connection,
                demand,
                project_id="ddo-test",
                destination=destination,
                format=encoding,
                scope={"subject": subject},
                page_rows=1,
            )
        rows = [
            json_loads(line) for line in (destination / "closure.jsonl").read_bytes().splitlines()
        ]
        leaves = [
            row["record"] for row in rows if row["relation"] == "ops.data_execution_evidence_leaf"
        ]
        assert len(leaves) == 1
        leaf = leaves[0]
        assert leaf["intent_id"] == original["id"] and leaf["cohort_size"] == 2
        assert (
            leaf["cpu_receipt"]["result_digest"]
            == payload["execution_evidence"]["cpu_receipts"][0]["result_digest"]
        )
        assert "cpu_replies" not in leaf["selected_completion"]["execution_evidence"]
        assert not any(row["relation"] == "ops.data_completion_intent" for row in rows)
        assert (
            payload["execution_evidence"]["cpu_replies"][0]
            not in (destination / "closure.jsonl").read_text()
        )
        assert {
            decode_semantic_value(row["record"]["canonical_body"])
            for row in rows
            if row["relation"] == "kb.data_product"
        } == {expected_input, expected_output}
        verified = verify_demand_export(destination, manifest_digest=manifest["manifest_digest"])
        assert verified["support_disclosure"] == "complete"
        assert verified["execution_evidence_disclosure"] == "bounded"
        assert verified["physical_cpu_cohort"] == "undisclosed"
        assert verified["whole_cpu_reply_verification"] == "native-member-assertion-only"
