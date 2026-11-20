"""Verify the emitted canonicalizer on the exact retained N35 body."""

import json
from dataclasses import replace
from pathlib import Path
from time import monotonic

from sqlalchemy import func, select

from corpus_structure.semantic.data_operation_value_native import canonical_identity_programs
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.storage_target import StorageTarget, verify_target
from corpus_structure.settings import Settings

folder = Path(__file__).resolve().parent
previous = json.loads((folder / "raw/canonical-json-parity.json").read_bytes())
expected = previous["observations"]["current"]
stage = StorageTarget(
    database="corpus_structure_ddo_stage",
    database_oid=130661481,
    system_identifier="7701811359771751232",
    host="/var/run/postgresql",
    port=5434,
    purpose="maintenance",
)
canonical, _ = canonical_identity_programs(decimal_digits=128)
candidate = replace(canonical.routine, schema="pg_temp", name="udm20_canonical_json")
intent = table("ops.data_completion_intent")
body = intent.c.payload["outputs"][0]["product"]["body"]
rendered = func.pg_temp.udm20_canonical_json(body)

with (
    open_runtime_engine(Settings(), "udm20-canonicalization-candidate", purpose="maintenance")
    as engine,
    engine.connect() as connection,
):
    transaction = connection.begin()
    try:
        verify_target(connection, stage, purpose="maintenance")
        connection.execute(select(func.set_config("statement_timeout", "20s", True)))
        connection.exec_driver_sql(candidate.render())
        started = monotonic()
        size, digest = connection.execute(
            select(
                func.octet_length(rendered),
                func.encode(func.sha256(func.convert_to(rendered, "UTF8")), "hex"),
            ).where(intent.c.id == previous["intent"])
        ).one()
        seconds = monotonic() - started
        if (size, digest) != (expected["bytes"], expected["sha256"]):
            raise ValueError("emitted canonicalization differs from the retained N35 result")
    finally:
        transaction.rollback()

report = {
    "outcome": "passed",
    "target": stage.model_dump(mode="json"),
    "intent": previous["intent"],
    "bytes": size,
    "sha256": digest,
    "seconds": seconds,
    "rolled_back": True,
}
(folder / "raw/candidate-canonical-json.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
