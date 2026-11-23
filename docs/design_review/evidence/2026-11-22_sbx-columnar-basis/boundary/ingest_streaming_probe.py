"""Does ADBC adbc_ingest (and pgpq + psycopg COPY) stream a RecordBatchReader batch by batch?

The producer samples pg_stat_progress_copy for the ingesting backend before yielding each
~2 MB batch. Non-zero server progress before the final batch means earlier batches reached
PostgreSQL before later ones were produced. Scratch database only.
Writes ``raw/ingest_streaming.json``. Usage: uv run python <this file>
"""

from __future__ import annotations

import json
from pathlib import Path

import adbc_driver_postgresql.dbapi as adbc
import psycopg
import pyarrow as pa
from pgpq import ArrowToPostgresBinaryEncoder

DB = "sbx_columnar_probe_scratch"
URI = f"postgresql:///{DB}?host=/var/run/postgresql&port=5434"
PG = f"dbname={DB} host=/var/run/postgresql port=5434"
OUT = Path(__file__).with_name("raw") / "ingest_streaming.json"
ROWS, BATCHES = 20_000, 6
schema = pa.schema([("k", pa.int64()), ("v", pa.string())])
res: dict[str, object] = {}


def batches(sample):
    for b in range(BATCHES):
        sample()
        yield pa.record_batch([pa.array(range(b * ROWS, (b + 1) * ROWS), pa.int64()),
                               pa.array(["x" * 100] * ROWS)], schema=schema)


with psycopg.connect(PG, autocommit=True) as obs:
    obs.execute("DROP TABLE IF EXISTS public.stream_t; CREATE TABLE public.stream_t (k bigint, v text)")

    def sampler(pid, out):
        def sample():
            out.append(obs.execute(
                "select coalesce((select array[bytes_processed, tuples_processed] from pg_stat_progress_copy "
                "where pid=%s), array[-1,-1])", (pid,)).fetchone()[0])
        return sample

    conn = adbc.connect(URI)
    cur = conn.cursor()
    cur.execute("SELECT pg_backend_pid()")
    pid = cur.fetchone()[0]
    samples: list = []
    cur.adbc_ingest("stream_t", pa.RecordBatchReader.from_batches(schema, batches(sampler(pid, samples))),
                    mode="append")
    conn.commit()
    res["adbc_ingest_progress_before_each_batch"] = samples
    cur.close()
    conn.close()

    with psycopg.connect(PG) as pc:
        pid = pc.execute("select pg_backend_pid()").fetchone()[0]
        samples = []
        enc = ArrowToPostgresBinaryEncoder(schema)
        with pc.cursor() as c, c.copy("COPY public.stream_t (k, v) FROM STDIN (FORMAT BINARY)") as cp:
            cp.write(enc.write_header())
            for batch in batches(sampler(pid, samples)):
                cp.write(enc.write_batch(batch))
            cp.write(enc.finish())
        pc.commit()
        res["pgpq_psycopg_copy_progress_before_each_batch"] = samples

print(json.dumps(res, indent=1))
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(res, indent=2))
