"""A consumed original answer is durable native custody before publication."""

import json
from dataclasses import replace
from typing import Any, cast

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.completion_drafts import CompletionDraftStore
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.data_operation_wire import wire_contracts
from native_test_support import principal_engine
from semantic.data_operation_demand_support import attach, cancel_demand, claim, publish
from semantic.data_operation_kernel_support import STORAGE, admit_kernel, prepare_kernel


def test_consumed_original_reconciles_after_local_ack_loss_without_new_answer(
    commit_db_engine,
    native_settings,
    tmp_path,
):
    engine = commit_db_engine
    preparation = prepare_kernel(STORAGE, directory=tmp_path / "kernel")
    with engine.begin() as connection:
        kernel = admit_kernel(connection, STORAGE, preparation=preparation)
    writer = principal_engine(native_settings, "write", engine.url.database)
    kernel = replace(kernel, engine=writer)
    try:
        first_demand, _, _, attached = attach(kernel)
        original = claim(kernel, attached, holder="original-producer")
        with writer.begin() as connection:
            origin = DataOperationStorage(connection).register_data_execution_origin(
                cast(
                    Any,
                    {
                        **original,
                        "runtime_id": kernel.runtime,
                    },
                )
            )
        completion = {
            "outcome": "success",
            "inputs": [],
            "support": [],
            "implementation_revision": "native-test-source-v1",
            "outputs": [
                {
                    "role": "result",
                    "position": 0,
                    "multiplicity": 1,
                    "product": {
                        "kind_contract": kernel.kind,
                        "body": semantic_value(51),
                        "members": [],
                    },
                }
            ],
        }
        store = CompletionDraftStore(tmp_path / "private", max_bytes=65536)
        draft = store.acknowledge(
            {**original, "runtime_id": kernel.runtime, "completion": completion},
            writer_schema=json_bytes(wire_contracts()["retain_data_completion_intent"]["input"]),
            release_id=kernel.prepared.release_id,
            operation="source.pdf/capture",
            basis=json.dumps({"execution_origin": origin["origin_id"]}).encode(),
            check_active=lambda: None,
        )
        with writer.begin() as connection:
            DataOperationStorage(connection).release_data_attempt(
                cast(
                    Any,
                    {
                        **original,
                        "physical_retirement": "confirmed",
                        "failure": {
                            "code": "settlement-failed",
                            "message": "original physically retired",
                        },
                    },
                )
            )
        cancel_demand(kernel, first_demand)
        _, _, _, target = attach(kernel, targets=("urn:ddo-test:source", "urn:ddo-test:consumer"))
        first_adopter = claim(kernel, target, holder="consume-only")
        assert first_adopter["generation"] > original["generation"]
        with writer.begin() as connection:
            intent = DataOperationStorage(connection).consume_data_completion_draft(
                cast(
                    Any,
                    {
                        **first_adopter,
                        "origin_id": origin["origin_id"],
                        "draft_id": draft.identity,
                        "completion": completion,
                    },
                )
            )
        with writer.begin() as connection:
            inspect = DataOperationStorage(connection).inspect_data_completion_draft
            retained = store.retire(draft.identity, project_id="ddo-test", inspect=inspect)
            assert (retained.state, retained.reason, retained.intent_id) == (
                "retained",
                "unpublished",
                intent["intent_id"],
            )
        assert tuple(store.candidates(original["request_id"], original["generation"])) == (draft,)
        with writer.begin() as connection:
            storage = DataOperationStorage(connection)
            failure = storage.release_data_attempt(
                cast(
                    Any,
                    {
                        **first_adopter,
                        "physical_retirement": "confirmed",
                        "failure": {
                            "code": "lost-consume-reply",
                            "message": "adopter retired before publication",
                        },
                    },
                )
            )
            assert failure["state"] == "released"
            assert failure["retained_intent_id"] == intent["intent_id"]
            claimed = storage.claim_data_requests(
                cast(
                    Any,
                    {
                        "holder": "native-reconciler",
                        "lease_seconds": 300,
                        "items": [
                            {"request_id": target["request_id"], "generation": target["generation"]}
                        ],
                    },
                )
            )["items"][0]
            assert claimed["state"] == "claimed"
            current = claimed["result"]
            assert current["action"] == "reconcile"
            assert current["retained_intent_id"] == intent["intent_id"]
            fence = {
                name: current[name]
                for name in ("request_id", "generation", "task_id", "attempt", "holder")
            }
            assert fence["attempt"] > first_adopter["attempt"]
            with pytest.raises(DBAPIError, match="consumed draft"), connection.begin_nested():
                storage.retain_data_completion_intent(
                    cast(
                        Any,
                        {
                            **fence,
                            "runtime_id": kernel.runtime,
                            "completion": completion,
                        },
                    )
                )
            adopted = storage.adopt_data_completion_intent(
                cast(Any, {**fence, "intent_id": intent["intent_id"]})
            )
            assert adopted["producer_task_id"] == original["task_id"]
            assert adopted["producer_attempt"] == original["attempt"]
        receipt = publish(kernel, fence, intent)
        with writer.begin() as connection:
            inspect = DataOperationStorage(connection).inspect_data_completion_draft
            with pytest.raises(DBAPIError, match="original custody"), connection.begin_nested():
                store.retire(draft.identity, project_id="wrong-project", inspect=inspect)
            assert store.open(draft.identity) == draft
            retired = store.retire(draft.identity, project_id="ddo-test", inspect=inspect)
            assert retired.state == "retired"
            assert retired.receipt_id == receipt["receipt_id"]
            assert retired.failure_id
        assert not tuple(store.candidates(original["request_id"], original["generation"]))
        assert publish(kernel, fence, intent) == {**receipt, "replayed": True}
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT producer_task_id,producer_attempt,generation FROM ops.data_derivation WHERE id=:id"
                ),
                {"id": receipt["derivation_id"]},
            ).one()
            assert tuple(row) == (original["task_id"], original["attempt"], original["generation"])
            assert connection.scalar(text("SELECT count(*) FROM ops.data_completion_intent")) == 1
            assert connection.scalar(text("SELECT count(*) FROM ops.data_publication_receipt")) == 1
    finally:
        writer.dispose()
