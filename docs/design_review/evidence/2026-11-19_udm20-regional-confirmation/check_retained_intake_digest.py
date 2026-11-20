"""Time N36's installed digest on the exact acknowledged 66-page intake."""

import json
from hashlib import sha256
from pathlib import Path
from time import monotonic

from sqlalchemy import Text, bindparam, cast, func, select, text
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.semantic.completion_drafts import completion_draft_store
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.storage_target import StorageTarget, verify_target
from corpus_structure.settings import Settings

folder = Path(__file__).resolve().parent
acknowledgment = json.loads((folder / "raw/largest-failed-private-draft.json").read_bytes())
stage = StorageTarget(
    database="corpus_structure_ddo_stage",
    database_oid=130661481,
    system_identifier="7701811359771751232",
    host="/var/run/postgresql",
    port=5434,
    purpose="maintenance",
)
settings = Settings()
store = completion_draft_store(
    settings.paths.data_dir / "completion-drafts", stage, 201326592
)
draft = store.open(acknowledgment["draft_id"])
if (
    len(draft.request) != acknowledgment["request_bytes"]
    or sha256(draft.request).hexdigest() != acknowledgment["request_sha256"]
):
    raise ValueError("acknowledged request differs from the measured draft")

decoded = (
    select(cast(bindparam("request", type_=Text()), JSONB()).label("document"))
    .cte("decoded_intake")
    .prefix_with("MATERIALIZED", dialect="postgresql")
)
document = decoded.c.document
parts = (
    "request_id",
    "generation",
    "task_id",
    "attempt",
    "holder",
    "runtime_id",
    "completion",
)
statement = select(
    func.ops.ddo_digest(func.jsonb_build_array(*(document[name] for name in parts)))
).select_from(decoded)
with (
    open_runtime_engine(settings, "udm20-retained-intake-digest", purpose="maintenance")
    as engine,
    engine.connect() as connection,
):
    transaction = connection.begin()
    try:
        connection.exec_driver_sql("SET TRANSACTION READ ONLY")
        verify_target(connection, stage, purpose="maintenance")
        revision = connection.scalar(text("SELECT version_num FROM public.semantic_alembic_version"))
        if revision != "semantic_ddo_pe_n36":
            raise ValueError("installed head differs from the planned N36 experiment")
        connection.execute(select(func.set_config("statement_timeout", "120s", True)))
        started = monotonic()
        digest = connection.execute(statement, {"request": draft.request.decode()}).scalar_one()
        seconds = monotonic() - started
    finally:
        transaction.rollback()

if not isinstance(digest, str) or len(digest) != 64:
    raise ValueError("installed digest returned an invalid identity")
report = {
    "outcome": "passed",
    "revision": revision,
    "target": stage.model_dump(mode="json"),
    "draft_id": draft.identity,
    "request_bytes": len(draft.request),
    "intent_digest": digest,
    "statement_seconds": seconds,
    "deadline_seconds": 120,
    "scope": "read-only digest assignment with the retained producer fence and completion",
}
(folder / "raw/n36-retained-intake-digest.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
