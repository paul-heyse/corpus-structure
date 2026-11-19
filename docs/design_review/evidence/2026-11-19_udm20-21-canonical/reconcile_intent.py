"""Replay the one recorded unpublished canonical intent through its exact native fence."""

import argparse
from typing import Any, cast

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.storage_target import StorageTarget, verify_target
from corpus_structure.settings import Settings

INTENT = "intent:c78f332cb8562bce5ee1ae5eadd93b0397bc11b77771a4f881ca00fe23c4460c"
REQUEST = "semantic-request:6211674a464e79a7ee932f1ebf9851880e2fca5d041169594a185bee2dc22ec8"
PROJECT = "nce-grinstead-snell-full-book"


def replay(commit: bool, timeout: int):
    if not 1 <= timeout <= 360:
        raise ValueError("intent recovery deadline must be 1 to 360 seconds")
    target = StorageTarget(
        database="corpus_structure_dev",
        database_oid=131763263,
        system_identifier="7701811359771751232",
        host="/var/run/postgresql",
        port=5434,
        purpose="write",
    )
    with (
        open_runtime_engine(Settings(), "udm-n29-intent-reconcile", purpose="write") as engine,
        engine.connect() as connection,
        connection.begin() as transaction,
    ):
        verify_target(connection, target, purpose="write")
        connection.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
        connection.exec_driver_sql(f"SET LOCAL statement_timeout = '{timeout}s'")
        storage = DataOperationStorage(connection)
        claim = storage.claim_data_requests(
            cast(
                Any,
                {
                    "holder": "udm21-exact-unpublished-intent",
                    "lease_seconds": 300,
                    "items": [{"request_id": REQUEST, "generation": 1}],
                },
            )
        )["items"][0]
        if claim["state"] != "claimed":
            raise ValueError(f"the exact request did not claim for reconciliation: {claim}")
        result = claim["result"]
        if result["action"] != "reconcile" or result["retained_intent_id"] != INTENT:
            raise ValueError("claim would do fresh work or reconcile another intent")
        fence = {
            name: result[name]
            for name in ("request_id", "generation", "task_id", "attempt", "holder")
        }
        adopted = storage.adopt_data_completion_intent(cast(Any, {**fence, "intent_id": INTENT}))
        if (adopted["intent_id"], adopted["producer_task_id"], adopted["producer_attempt"]) != (
            INTENT,
            24,
            1,
        ):
            raise ValueError("native adoption substituted another producer")
        published = storage.publish_data_derivation(cast(Any, {**fence, "intent_id": INTENT}))
        if not commit:
            transaction.rollback()
    return {
        "intent": INTENT,
        "project": PROJECT,
        "committed": commit,
        "timeout_seconds": timeout,
        "original": dict(adopted),
        "publication": dict(published),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--commit", action="store_true", help="Commit the exact native reconciliation."
    )
    parser.add_argument("--statement-timeout", type=int, default=120)
    args = parser.parse_args()
    print(json_bytes(replay(args.commit, args.statement_timeout)).decode())
