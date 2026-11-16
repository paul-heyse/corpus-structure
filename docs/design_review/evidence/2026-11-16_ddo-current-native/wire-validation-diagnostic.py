"""Isolate installed wire-validator work from demand reads, without business effects.

Run with UV_NO_SYNC=1 uv run python PATH. CORPUS_DDO_DIAGNOSTIC_URL must name
the owned authoring stage through maintenance authentication. Invalid null values
exercise schema preparation without reading source, prediction or reference data.
"""

import hashlib
import json
import os
import re
import time
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[4]
REGISTERED = ROOT / "python/corpus-structure/target_alembic/versions/semantic_ddo_observation_split_native.json"


def main():
    catalog = json.loads(REGISTERED.read_bytes())
    wire = next(row for row in catalog["desired"] if row["identity"]["schema"] == "ops"
                and row["identity"]["name"] == "ddo_require_wire")
    body = wire["catalog"]["body"]
    literal = re.search(r"contracts constant jsonb := '((?:''|[^'])*)'::jsonb", body)
    if literal is None:
        raise ValueError("registered wire body lacks its exact trusted schema constant")
    contracts = json.loads(literal.group(1).replace("''", "'"))
    with psycopg.connect(os.environ["CORPUS_DDO_DIAGNOSTIC_URL"], options=
            "-c default_transaction_read_only=on -c statement_timeout=10000") as connection:
        database, oid, system, jit = connection.execute(
            "SELECT current_database(),(SELECT oid FROM pg_database WHERE datname=current_database()),"
            "system_identifier::text,current_setting('jit') FROM pg_control_system()"
        ).fetchone()
        if (database, oid, system) != ("corpus_structure_ddo_stage", 130661481,
                                      "7701811359771751232"):
            raise ValueError("diagnostic requires the exact owned authoring stage")
        actual = connection.execute(
            "SELECT prosrc FROM pg_proc WHERE oid='ops.ddo_require_wire(text,text,jsonb)'::regprocedure"
        ).fetchone()[0]
        if actual != body:
            raise ValueError("installed wire source differs from the registered candidate")
        version = connection.execute(
            "SELECT extversion FROM pg_extension WHERE extname='pg_jsonschema'"
        ).fetchone()[0]
        results = []
        for name, schema, expected in (
            ("tiny", {"type": "null"}, True),
            ("read_input", contracts["read_demand_result"]["input"], False),
            ("read_output", contracts["read_demand_result"]["output"], False),
        ):
            content = json.dumps(schema, separators=(",", ":"))
            elapsed = []
            for _ in range(3):
                start = time.perf_counter()
                value = connection.execute(
                    "SELECT public.json_matches_schema(%s::json,'null'::json)", (content,)
                ).fetchone()[0]
                elapsed.append(time.perf_counter() - start)
                if value is not expected:
                    raise ValueError("unexpected diagnostic validator result: " + name)
            results.append(dict(name=name, schema_bytes=len(content.encode()),
                                seconds=elapsed, result=expected))
        print(json.dumps(dict(database=database, oid=oid, system=system, jit=jit,
            pg_jsonschema=version, registered_wire_sha256=hashlib.sha256(body.encode()).hexdigest(),
            scope="pure schema preparation/invalid-null check; no demand or source reads",
            results=results), indent=2))


if __name__ == "__main__":
    main()
