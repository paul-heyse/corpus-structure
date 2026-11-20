"""Inspect acknowledged local custody and native standing without recomputing its SQL digest."""

import json
from hashlib import sha256
from pathlib import Path

from corpus_structure.semantic.completion_drafts import CompletionDraftStore
from corpus_structure.semantic.data_operation_json import json_bytes, wire_json_loads
from corpus_structure.semantic.metadata import table
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import URL

ROOT = Path("/home/paul/corpus-structure")
FOLDER = Path(__file__).resolve().parent
namespace = (
    ROOT
    / "build/data/completion-drafts/7942cfc2a5f7ebb8fbe2048e7d068f3bf5f45c90c6ec738f58d53ccd130945ac"
)
identity = "531b190420630bdd3146514bf9d97f6b1edf3193ce0ce97a8291e77d314cc7a0"
store = CompletionDraftStore(namespace, max_bytes=201326592)
draft = store.open(identity)
producer = draft.native_request()
basis = wire_json_loads(draft.basis)
r = table("ops.data_request")
t = table("ops.task")
i = table("ops.data_completion_intent")
o = table("ops.data_execution_origin")
f = table("ops.data_attempt_failure")
used = table("ops.data_draft_consumption")
engine = create_engine(
    URL.create(
        "postgresql+psycopg",
        username="paul",
        database="corpus_structure_ddo_stage",
        query={"host": "/var/run/postgresql", "port": "5434"},
    )
)
try:
    with engine.connect() as c:
        request = dict(
            c.execute(select(r).where(r.c.id == producer["request_id"]))
            .mappings()
            .one()
        )
        task = dict(
            c.execute(select(t).where(t.c.id == request["live_task_id"]))
            .mappings()
            .one()
        )
        origin = dict(
            c.execute(select(o).where(o.c.id == basis["execution_origin"]))
            .mappings()
            .one()
        )
        fence_names = (
            "request_id",
            "generation",
            "task_id",
            "attempt",
            "holder",
            "runtime_id",
        )
        assert all(origin[key] == producer[key] for key in fence_names)
        assert request["generation"] == producer["generation"]
        assert request["runtime_id"] == producer["runtime_id"]
        assert task["status"] == "pending" and task["lease_until"] is None
        intents = c.execute(
            select(func.count())
            .select_from(i)
            .where(
                i.c.request_id == request["id"], i.c.generation == request["generation"]
            )
        ).scalar_one()
        consumption = c.execute(
            select(func.count())
            .select_from(used)
            .where(used.c.origin_id == origin["id"])
        ).scalar_one()
        failures = [
            dict(row)
            for row in c.execute(
                select(f).where(
                    f.c.request_id == request["id"],
                    f.c.generation == request["generation"],
                )
            ).mappings()
        ]
        assert intents == 0 and consumption == 0 and failures
        result = {
            "outcome": "passed",
            "scope": "local acknowledged file custody and independent bounded native reads; no native recovery/adoption claim",
            "draft_id": identity,
            "request_bytes": len(draft.request),
            "request_sha256": sha256(draft.request).hexdigest(),
            "completion_bytes": len(json_bytes(producer["completion"])),
            "release": draft.release_id,
            "operation": draft.operation,
            "producer_fence": {key: producer[key] for key in fence_names},
            "basis": {
                key: basis[key]
                for key in (
                    "execution_origin",
                    "runtime_manifest_sha256",
                    "runtime_archive_sha256",
                )
            },
            "native_request": {
                key: request[key]
                for key in (
                    "id",
                    "project_id",
                    "release_id",
                    "runtime_id",
                    "recipe",
                    "generation",
                    "live_task_id",
                )
            },
            "task": {
                key: task[key]
                for key in (
                    "id",
                    "status",
                    "attempt",
                    "claimed_by",
                    "lease_until",
                    "started_at",
                    "finished_at",
                )
            },
            "native_intents": intents,
            "native_draft_consumptions": consumption,
            "attempt_failures": failures,
            "producer_task_released": True,
            "retained_provider_answer_available": True,
            "native_recovery": "not_run; exact applicability and adoption must still succeed under the enforcing native API",
        }
    (FOLDER / "raw/largest-failed-private-draft.json").write_text(
        json.dumps(result, indent=2, default=str) + "\n"
    )
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "attempt_failures"},
            default=str,
        )
    )
finally:
    engine.dispose()
