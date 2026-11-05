"""Native frozen-report checks on actual completed deterministic producer output.

Mutations are deliberate negative inputs. No model or semantic quality is tested.
"""
from copy import deepcopy
import json
from pathlib import Path

from sqlalchemy import text, bindparam
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

RAW = Path(__file__).with_name("raw")
receipt = json.loads((RAW / "normal-structural-run-008.json").read_bytes())
task = next(t["task_id"] for t in receipt["tasks"] if t["product_id"].startswith("structural:9cbf39"))
statement = text("SELECT ops.validate_structural_product_report(:task,:body)").bindparams(bindparam("body", type_=JSONB))
checks = {}
with open_runtime_engine(Settings(), "structural-numeric-controls", purpose="maintenance") as engine, engine.connect() as conn:
    transaction = conn.begin()
    try:
        body = conn.execute(text("SELECT body FROM ops.task_result WHERE task_id=:t"), {"t": task}).scalar_one()
        conn.execute(statement, {"task": task, "body": body})
        checks["canonical_float_configuration_matches_actual_numeric_derivation"] = "passed"
        for name, mutate in (
            ("tampered_numeric_derivation", lambda r: r["retrieval_report"]["vectors"][0]["values"].__setitem__(0, r["retrieval_report"]["vectors"][0]["values"][0] + 0.01)),
            ("typed_raw_string_cannot_be_retyped_numeric", lambda r: r["retrieval_report"]["profiles"][0].__setitem__("model", 384)),
            ("integer_identifier_is_exact", lambda r: r["inputs"]["sources"][0].__setitem__("native_task_id", r["inputs"]["sources"][0]["native_task_id"] + 1)),
            ("integer_dimension_cannot_be_retyped_string", lambda r: r["retrieval_report"]["profiles"][0].__setitem__("dimension", str(r["retrieval_report"]["profiles"][0]["dimension"]))),
        ):
            changed = deepcopy(body)
            mutate(changed["structural_product"])
            try:
                with conn.begin_nested():
                    conn.execute(statement, {"task": task, "body": changed})
            except DBAPIError as error:
                assert getattr(error.orig, "sqlstate", None) == "23514", str(error)
                checks[name] = {"outcome": "passed", "native_refusal": "23514", "reason": str(error.orig).splitlines()[0]}
            else:
                raise AssertionError("native validation accepted " + name)
    finally:
        transaction.rollback()
result = {"outcome": "passed", "task_id": task, "native_revision": "semantic_pce_defnumeric_20261105", "scope": "native canonical configuration versus raw derivation binding; no provider or semantic assessment", "checks": checks, "transaction": "rolled_back"}
with (RAW / "structural-numeric-controls-151.json").open("xb") as out:
    out.write(canonical_bytes(result) + b"\n")
print(json.dumps(result))
