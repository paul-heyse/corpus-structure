"""S6-E step 6: vectors at 1024 and 2048 dimensions (phase 1 input; OPEN-D3-2 waits on S7).

    uv run python code/s6e_vectors.py      # after s6b_rows.py, on cs_spike_s6

For each dimension, a table shaped like D3's ``kb.embedding`` (``kb.embedding`` itself for 1024; a
copy ``kb.embedding_2048`` with ``halfvec(2048)``), loaded by binary COPY (``Copy.set_types`` with
pgvector's registered ``halfvec``) with 10,000 random unit vectors: 7,000 ``segment`` rows (the
run-1 segments under three synthetic embedding configurations), 2,000 ``entity`` and 1,000
``alias`` rows (synthetic target ids; ``target_id`` has no foreign key).

Indexes: D3's global ``hnsw (vec halfvec_cosine_ops)``, then one partial HNSW per ``target_type``
(D3 §5, L-S6). Top-10 queries for one configuration filtered by a join on ``kb.segment.kind``
(``paragraph``), 50 query vectors: median and p95 wall time, recall@10 against the exact answer,
with ``hnsw.iterative_scan`` off, ``relaxed_order`` and ``strict_order``. Build time and size per
index. Writes ``results/s6/vectors.tsv`` and ``results/s6/vectors.md``. The vector tables are
dropped at the end (they are phase 1 tables; their sizes are recorded here).
"""

from __future__ import annotations

import re
import statistics
import time

import numpy as np
from pgvector import HalfVector
from pgvector.psycopg import register_vector

from s6_db import RESULTS, app
from s6_load import Loader  # noqa: F401  (documented dependency: rows from s6b)

N_SEG, N_ENT, N_ALIAS, N_Q = 7000, 2000, 1000, 50
RNG = np.random.default_rng(20261028)


def unit(n, d):
    v = RNG.standard_normal((n, d)).astype(np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))]


def cleanup(c):
    """Back to D3's DDL: no vector rows, the global index, no S6 embedding configurations (idempotent)."""
    with c.transaction():
        c.execute("DROP TABLE IF EXISTS kb.embedding_2048")
        c.execute("TRUNCATE kb.embedding")
        c.execute("DROP INDEX IF EXISTS kb.embedding_hnsw, kb.embedding_hnsw_segment, kb.embedding_hnsw_entity, kb.embedding_hnsw_alias")
        c.execute("CREATE INDEX embedding_hnsw ON kb.embedding USING hnsw (vec halfvec_cosine_ops)")
        c.execute("DELETE FROM ops.method_config WHERE method_id IN (SELECT id FROM ops.method WHERE name = 'embed.qwen3')")
        c.execute("DELETE FROM ops.method WHERE name = 'embed.qwen3'")


def main() -> int:
    rows_tsv = [["dim", "index", "iterative_scan", "query", "median_ms", "p95_ms", "recall_at_10", "build_ms", "index_bytes", "plan_uses"]]
    md = ["# S6 vectors (brief step 6)", "", "pgvector 0.8.7, pgvector-python 0.5.1 (`HalfVector`, binary COPY). Random unit vectors (seed 20261028); "
          "recall@10 against the exact top 10 (`enable_indexscan = off`). The query: one embedding configuration, `target_type = 'segment'`, "
          "joined to `kb.segment` with `kind = 'paragraph'` (one in four of the segment rows), `ORDER BY vec <=> $q LIMIT 10`.", ""]
    with app() as c:
        register_vector(c)
        c.execute("SET maintenance_work_mem = '1GB'")
        cleanup(c)
        meth = c.execute("INSERT INTO ops.method (name, version, family) VALUES ('embed.qwen3', 's6', 'extract') RETURNING id").fetchone()[0]
        cfgs = [c.execute("INSERT INTO ops.method_config (method_id, name, params, config_hash, tier) VALUES (%s, %s, '{}', %s, 'encoder') RETURNING id",
                          (meth, f"s6-{i}", f"cfg:s6-embed-{i}")).fetchone()[0] for i in range(3)]
        segs = [r[0] for r in c.execute("SELECT id FROM kb.segment ORDER BY id")]
        c.commit()
        targets = [("segment", segs[i % len(segs)], cfgs[i // len(segs)]) for i in range(N_SEG)]
        targets += [("entity", 10_000_000 + i, cfgs[0]) for i in range(N_ENT)] + [("alias", 20_000_000 + i, cfgs[0]) for i in range(N_ALIAS)]
        for dim in (1024, 2048):
            table = "kb.embedding" if dim == 1024 else "kb.embedding_2048"
            with c.transaction():
                if dim == 2048:
                    c.execute("CREATE TABLE kb.embedding_2048 (LIKE kb.embedding INCLUDING DEFAULTS INCLUDING IDENTITY INCLUDING CONSTRAINTS)")
                    c.execute("ALTER TABLE kb.embedding_2048 ALTER COLUMN vec TYPE halfvec(2048)")
                    c.execute("ALTER TABLE kb.embedding_2048 ADD UNIQUE (target_type, target_id, model_config_id)")
                else:
                    c.execute("DROP INDEX kb.embedding_hnsw")   # rebuilt after the load, as the loading guidance says
            vecs = unit(len(targets), dim)
            t0 = time.perf_counter()
            with c.transaction():
                with c.cursor().copy(f"COPY {table} (target_type, target_id, model_config_id, vec) FROM STDIN (FORMAT BINARY)") as cp:
                    cp.set_types(["text", "int8", "int8", "halfvec"])
                    for (tt, tid, cfg), v in zip(targets, vecs):
                        cp.write_row((tt, tid, cfg, HalfVector(v)))
            copy_ms = (time.perf_counter() - t0) * 1000
            c.execute(f"ANALYZE {table}")
            stored = np.array([np.asarray(r[0].to_list(), dtype=np.float32) for r in c.execute(f"SELECT vec FROM {table} ORDER BY id LIMIT 3")])
            md += [f"## {dim} dimensions", "", f"COPY of {len(targets)} rows: {copy_ms:.0f} ms; table {c.execute(f'SELECT pg_table_size(%s)', (table,)).fetchone()[0]} bytes. "
                   f"Half-precision round trip, max abs error over 3 rows: {np.abs(stored - vecs[:3]).max():.2e}.", ""]
            rows_tsv.append([dim, "(copy)", "", f"{len(targets)} rows", round(copy_ms, 1), "", "", "", c.execute("SELECT pg_table_size(%s)", (table,)).fetchone()[0], ""])
            qs = unit(N_Q, dim)
            sql = (f"SELECT e.target_id FROM {table} e JOIN kb.segment s ON s.id = e.target_id "
                   "WHERE e.target_type = 'segment' AND e.model_config_id = %(cfg)s AND s.kind = 'paragraph' "
                   "ORDER BY e.vec <=> %(q)s LIMIT 10")
            # exact answers
            exact = []
            with c.transaction(force_rollback=True):
                c.execute("SET LOCAL enable_indexscan = off")
                for q in qs:
                    exact.append({r[0] for r in c.execute(sql, {"cfg": cfgs[0], "q": HalfVector(q)})})
            short = f"{table.split('.')[1]}"
            for label, ddl in (("global hnsw (D3)", [f"CREATE INDEX {short}_hnsw ON {table} USING hnsw (vec halfvec_cosine_ops)"]),
                               ("partial hnsw per target_type", [f"DROP INDEX kb.{short}_hnsw"] + [
                                   f"CREATE INDEX {short}_hnsw_{t} ON {table} USING hnsw (vec halfvec_cosine_ops) WHERE target_type = '{t}'"
                                   for t in ("segment", "entity", "alias")])):
                t0 = time.perf_counter()
                with c.transaction():
                    for d in ddl:
                        c.execute(d)
                build_ms = (time.perf_counter() - t0) * 1000
                isize = c.execute("SELECT coalesce(sum(pg_relation_size(i.indexrelid)), 0) FROM pg_index i JOIN pg_class x ON x.oid = i.indexrelid "
                                  "WHERE i.indrelid = %s::regclass AND x.relname LIKE %s", (table, f"{short}_hnsw%")).fetchone()[0]
                for it, forced in [(x, f) for f in (False, True) for x in ("off", "relaxed_order", "strict_order")]:
                    ts, rec = [], []
                    with c.transaction(force_rollback=True):
                        c.execute(f"SET LOCAL hnsw.iterative_scan = {it}")
                        if forced:   # the planner prefers an exact scan at this size; force the HNSW ordered scan to measure it
                            c.execute("SET LOCAL enable_seqscan = off")
                            c.execute("SET LOCAL enable_sort = off")
                        p = [re.sub(r"'\[[^']{60,}\]'", "'[query vector]'", r[0])
                             for r in c.execute("EXPLAIN (COSTS off) " + sql, {"cfg": cfgs[0], "q": HalfVector(qs[0])})]
                        for q, ex in zip(qs, exact):
                            t0 = time.perf_counter()
                            got = {r[0] for r in c.execute(sql, {"cfg": cfgs[0], "q": HalfVector(q)})}
                            ts.append((time.perf_counter() - t0) * 1000)
                            rec.append(len(got & ex) / 10)
                    uses = next((x.strip() for x in p if "Index Scan using" in x), "no hnsw index scan")
                    rows_tsv.append([dim, label + (" (forced)" if forced else " (planner's choice)"), it, "top-10 paragraph segments, one config", round(statistics.median(ts), 3), round(pct(ts, 0.95), 3),
                                     round(statistics.mean(rec), 3), round(build_ms, 1), isize, uses])
                    md += [f"### {label}, iterative_scan {it}, {'HNSW forced (enable_seqscan, enable_sort off)' if forced else 'planner' + chr(39) + 's choice'}", "", f"build {build_ms:.0f} ms, {isize} bytes; median {statistics.median(ts):.2f} ms, "
                           f"p95 {pct(ts, 0.95):.2f} ms; recall@10 {statistics.mean(rec):.3f}; results short of 10 in "
                           f"{sum(1 for r in rec if r < 1)} of {N_Q} queries.", "", "```", *p, "```", ""]
            c.commit()
        cleanup(c)
    with (RESULTS / "vectors.tsv").open("w") as f:
        for r in rows_tsv:
            f.write("\t".join(str(x) for x in r) + "\n")
    (RESULTS / "vectors.md").write_text("\n".join(md) + "\n")
    for r in rows_tsv:
        print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
