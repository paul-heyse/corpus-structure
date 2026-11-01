"""Read-only PG18 casts of exact retained task86 fields; no publication or schema writes."""
import gzip
import json
from hashlib import sha256
from pathlib import Path

import psycopg

from corpus_structure.semantic.identity import canonical_bytes

ROOT = Path(__file__).with_name("raw")
payload = gzip.decompress((ROOT / "book-task86-prepared.json.gz").read_bytes())
assert sha256(payload).hexdigest() == "c8f19ca1703206e9007b416eecb7c0d286de57d7ce82b006a605335efe7da524"
product = json.loads(payload)
results = []
with psycopg.connect(
    "postgresql://corpus_sem_reader@/corpus_pdf_20261031?host=/var/run/postgresql&port=5434",
    autocommit=True,
) as connection:
    connection.execute("SET default_transaction_read_only=on")
    # Root bounded parameter logging before this diagnostic. Refuse to duplicate
    # hundreds of MB into a server query log if that operational setting changes.
    assert connection.execute("SHOW log_parameter_max_length").fetchone()[0] == "0"
    assert connection.execute("SHOW log_parameter_max_length_on_error").fetchone()[0] == "0"
    for field in ("content", "occurrences", "relations"):
        data = canonical_bytes(product[field])
        row = {"path": "/" + field, "canonical_bytes": len(data), "sha256": sha256(data).hexdigest()}
        try:
            row["jsonb_bytes"] = connection.execute(
                "SELECT pg_column_size(convert_from(%s,'UTF8')::jsonb)", (data,)
            ).fetchone()[0]
            row["outcome"] = "passed"
        except psycopg.Error as error:
            row.update(outcome="failed", sqlstate=error.sqlstate, diagnostic=str(error).splitlines()[0])
        results.append(row)
        print(json.dumps(row), flush=True)
(ROOT / "book-task86-jsonb-field-casts.json").write_bytes(canonical_bytes({
    "payload_sha256": sha256(payload).hexdigest(), "read_only": True, "fields": results,
}))
