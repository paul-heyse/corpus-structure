"""S6-E steps 7 and 8: volume (binary COPY at run scale), index-backed queries, sizes, run deletion at volume.

    uv run python code/s6e_volume.py      # after s6b_rows.py (and s6c), on cs_spike_s6

A finished ``full`` run ("volume") over 2,500 synthetic units (D3 §11's first-pass scale), each with
five method tasks (mentions, relations, scope, values, proposal) and 40 observations:
16 ``mention``, 8 ``relation``, 8 ``scope``, 7 ``value`` and 1 ``claim_proposal``, so 12,500
tasks and 100,000 observations; then 5,000 entities and 20,000 claims (8 per unit) with one
support and one evidence row each. No S2 or S3 outputs exist yet, so payloads are synthetic in the
D3 §6.2 shapes, sized from the S0 stored batches for proposals (the v1 reference batches, cycled)
and from the S1 sentences for mention and value texts; the claims' qualifiers and values are the
v1 reference claims', cycled. All writes are binary COPY with ``Copy.set_types`` (D6 §3);
D6's two notes are checked: ``real`` needs ``float4``, and JSONB takes plain dicts once declared.

Then: the ``@?`` qualifier query (no GIN index; carried by ``claim_pred``), "why a method ran" for one
unit, coverage of the run, with plans; sizes of every table and index and the share of
``kb.segment.text`` (``results/s6/sizes.tsv``), taken before the run's materialized rows are deleted
(D3 §8) with plans and trigger times (``results/s6/run_deletion_volume.md``). Writes
``results/s6/volume.tsv`` and ``results/s6/volume.md``.
"""

from __future__ import annotations

import json
import random
import statistics
import time
from datetime import timedelta

import psycopg

from s6_db import RESULTS, app, write_json
from s6_load import CORE, S0R2, T0, Loader, predicate_prefixes, sha
from s6b_rows import run_deletion

UNITS = 2500
RND = random.Random(20261028)


def plan(c, sql, params=None):
    with c.transaction(force_rollback=True):
        return [r[0] for r in c.execute(f"EXPLAIN (ANALYZE, COSTS off, TIMING off) {sql}", params).fetchall()]


def timed(c, sql, params=None, n=7):
    ts, rows = [], None
    for _ in range(n):
        t0 = time.perf_counter()
        rows = c.execute(sql, params).fetchall()
        ts.append((time.perf_counter() - t0) * 1000)
    return rows, round(statistics.median(ts), 3)


def payloads():
    sents = []
    for f in sorted((S0R2.parent / "s1" / "sentences").glob("*.provisional.jsonl")):
        page = f.name.replace(".provisional.jsonl", "")
        text = (S0R2.parent / "s1" / "canonical" / f"{page}.txt").read_text()
        for line in f.read_text().splitlines():
            r = json.loads(line)
            sents.append((text[r["start"]:r["end"]], r["start"], r["end"]))
    batches = [json.loads((S0R2 / "reference_v1" / f"{u}.json").read_text()) for u in CORE]
    claims = [c for b in batches for c in b["claims"]]
    return sents, batches, claims


def mention(sents, i):
    t, s, e = sents[i % len(sents)]
    w = t.split()[: 1 + i % 3]
    return {"label": ["random variable", "distribution family", "parameter", "symbol"][i % 4], "text": " ".join(w), "start": s, "end": s + len(" ".join(w)),
            "attributes": {"role": {"label": "subject", "score": 0.83}}}


def relation(sents, i):
    t, s, e = sents[i % len(sents)]
    return {"label": "stat:has_distribution", "head": {"start": s, "end": s + 3, "label": "random variable"},
            "tail": {"start": s + 10, "end": s + 30, "label": "distribution family"}, "joint": True, "feasible": True}


def scope(sents, i):
    t, s, e = sents[i % len(sents)]
    return {"mention_ref": {"task": 0, "ordinal": i % 16, "start": s, "end": s + 1}, "binding_site": {"ordinal": 0, "start": s, "end": s + 1},
            "scope_segment": "seg:" + sha(str(i))[:32], "extent": "statement", "binding": "supposition"}


def value(sents, i):
    t, s, e = sents[i % len(sents)]
    return {"value": {"t": "formula", "latex": t[:80], "symbols": {"x": {"bind": "free"}, "mu": {"bind": "param_of", "claim": "clm:" + sha(str(i))[:32], "param": "mean"}}},
            "math_kind": "formula"}


def main() -> int:
    sents, batches, ref_claims = payloads()
    prefix = predicate_prefixes()
    out, tsv = {}, [["step", "rows", "ms", "rows_per_s", "mean_payload_bytes", "note"]]
    with app() as c:
        L = Loader(c)
        L.ids.update({k: v for k, v in c.execute("SELECT 'project', id FROM meta.project LIMIT 1").fetchall()})
        L.ids["schema"] = c.execute("SELECT id FROM meta.schema_version ORDER BY id LIMIT 1").fetchone()[0]
        L.ids["guideline"] = c.execute("SELECT id FROM meta.guideline_version ORDER BY id LIMIT 1").fetchone()[0]
        L.ids["policy"] = c.execute("SELECT id FROM ops.policy_version LIMIT 1").fetchone()[0]
        L.ids["slice"] = c.execute("SELECT id FROM ops.debug_slice LIMIT 1").fetchone()[0]
        run1 = c.execute("SELECT promoted_run_id FROM meta.project").fetchone()[0]
        c.execute("DELETE FROM ops.method WHERE name LIKE 'vol.%%'")
        cfg = {}
        for name, fam in (("vol.mentions", "extract"), ("vol.relations", "extract"), ("vol.scope", "resolve"), ("vol.values", "normalize"), ("vol.propose", "llm")):
            mid = c.execute("INSERT INTO ops.method (name, version, family) VALUES (%s, '1', %s) RETURNING id", (name, fam)).fetchone()[0]
            cfg[name] = c.execute("INSERT INTO ops.method_config (method_id, params, config_hash, tier) VALUES (%s, '{}', %s, 'deterministic') RETURNING id",
                                  (mid, f"cfg:{name}")).fetchone()[0]
        run = L.run("volume", "full", started=T0 + timedelta(days=1), finished=T0 + timedelta(days=1, hours=3), reference=run1)
        segs = [r[0] for r in c.execute("SELECT id FROM kb.segment WHERE kind IN ('unit','paragraph') ORDER BY id")]
        ren = c.execute("SELECT id FROM kb.rendition ORDER BY id LIMIT 1").fetchone()[0]
        c.commit()

        # D6 §3 notes: a real column needs float4 in binary COPY; jsonb takes dicts once declared
        notes = {}
        for label, types, row in (("score as float8 into real", ["int8", "int4", "text", "jsonb", "float8", "text"], (None, 999999, "mention", {"a": 1}, 0.5, "produced")),
                                  ("payload as str into jsonb (declared jsonb)", ["int8", "int4", "text", "jsonb", "float4", "text"], (None, 999999, "mention", '{"a": 1}', 0.5, "produced"))):
            try:
                with c.transaction(force_rollback=True):
                    t = c.execute("SELECT id FROM ops.task LIMIT 1").fetchone()[0]
                    with c.cursor().copy("COPY kb.observation (task_id, ordinal, kind, payload, score, outcome) FROM STDIN (FORMAT BINARY)") as cp:
                        cp.set_types(types)
                        cp.write_row((t,) + row[1:])
                notes[label] = "accepted"
            except psycopg.Error as e:
                notes[label] = f"{e.sqlstate}: {e.diag.message_primary}"
        out["copy_type_notes"] = notes

        # tasks
        t0 = time.perf_counter()
        stages = [("extract", "vol.mentions"), ("extract", "vol.relations"), ("scope", "vol.scope"), ("normalize", "vol.values"), ("propose", "vol.propose")]
        with c.transaction():
            with c.cursor().copy("COPY ops.task (run_id, stage, unit_type, unit_id, unit_key, method_config_id, input_hash, status, attempt, cost, "
                                 "created_at, started_at, finished_at) FROM STDIN (FORMAT BINARY)") as cp:
                cp.set_types(["int8", "text", "text", "int8", "text", "int8", "text", "text", "int4", "jsonb", "timestamptz", "timestamptz", "timestamptz"])
                for u in range(UNITS):
                    for st, m in stages:
                        cp.write_row((run, st, "segment", segs[u % len(segs)], f"unit:vol-{u}", cfg[m], sha([m, u]), "done", 1,
                                      {"wall_ms": 40 + u % 50}, T0 + timedelta(days=1), T0 + timedelta(days=1, minutes=1), T0 + timedelta(days=1, hours=1)))
        ms = (time.perf_counter() - t0) * 1000
        tsv.append(["copy ops.task", UNITS * 5, round(ms, 1), round(UNITS * 5 / ms * 1000), "", "binary COPY, set_types"])
        tasks = {(m, u): tid for tid, m, u in c.execute(
            "SELECT t.id, m.name, substr(t.unit_key, 10)::int FROM ops.task t JOIN ops.method_config mc ON mc.id = t.method_config_id "
            "JOIN ops.method m ON m.id = mc.method_id WHERE t.run_id = %s", (run,))}

        # observations
        kinds = [("vol.mentions", "mention", 16, mention), ("vol.relations", "relation", 8, relation), ("vol.scope", "scope", 8, scope), ("vol.values", "value", 7, value)]
        sizes, n = [], 0
        t0 = time.perf_counter()
        with c.transaction():
            with c.cursor().copy("COPY kb.observation (task_id, ordinal, kind, rendition_id, segment_id, payload, score, outcome) FROM STDIN (FORMAT BINARY)") as cp:
                cp.set_types(["int8", "int4", "text", "int8", "int8", "jsonb", "float4", "text"])
                for u in range(UNITS):
                    for m, kind, k, f in kinds:
                        for j in range(k):
                            p = f(sents, u * 40 + j)
                            if u % 50 == 0:
                                sizes.append((kind, len(json.dumps(p))))
                            cp.write_row((tasks[(m, u)], j, kind, ren, segs[u % len(segs)], p, 0.5 + (j % 5) / 10, "produced"))
                            n += 1
                    b = batches[u % len(batches)]
                    p = {"batch": b, "rationale": None}
                    if u % 50 == 0:
                        sizes.append(("claim_proposal", len(json.dumps(p))))
                    cp.write_row((tasks[("vol.propose", u)], 0, "claim_proposal", ren, segs[u % len(segs)], p, None, "produced"))
                    n += 1
        ms = (time.perf_counter() - t0) * 1000
        mean_payload = statistics.mean(s for _, s in sizes)
        by_kind = {}
        for k, s in sizes:
            by_kind.setdefault(k, []).append(s)
        tsv.append(["copy kb.observation", n, round(ms, 1), round(n / ms * 1000), round(mean_payload),
                    "; ".join(f"{k} mean {statistics.mean(v):.0f} B" for k, v in by_kind.items())])
        out["observations"] = {"rows": n, "ms": ms, "payload_bytes_by_kind": {k: round(statistics.mean(v)) for k, v in by_kind.items()}}
        prop_obs = {u: oid for oid, u in c.execute(
            "SELECT o.id, substr(t.unit_key, 10)::int FROM kb.observation o JOIN ops.task t ON t.id = o.task_id "
            "WHERE t.run_id = %s AND o.kind = 'claim_proposal'", (run,))}

        # entities and claims
        t0 = time.perf_counter()
        with c.transaction():
            with c.cursor().copy("COPY kb.entity (run_id, key, schema_version_id, type, label, scope, scope_segment_id, attrs) FROM STDIN (FORMAT BINARY)") as cp:
                cp.set_types(["int8", "text", "int8", "text", "text", "text", "int8", "jsonb"])
                for i in range(5000):
                    glob = i % 10 == 0
                    cp.write_row((run, f"ent:vol-{i}", L.ids["schema"], "DistributionFamily" if glob else "RandomVariable", f"e{i}",
                                  "global" if glob else "local", None if glob else segs[(i // 2) % len(segs)], {}))
        ems = (time.perf_counter() - t0) * 1000
        ents = [r[0] for r in c.execute("SELECT id FROM kb.entity WHERE run_id = %s ORDER BY id", (run,))]
        tsv.append(["copy kb.entity", len(ents), round(ems, 1), round(len(ents) / ems * 1000), "", ""])
        t0 = time.perf_counter()
        with c.transaction():
            with c.cursor().copy("COPY kb.claim (run_id, key, subject_id, predicate, object_entity_id, object_value, qualifiers, statement_role, status, establishment) "
                                 "FROM STDIN (FORMAT BINARY)") as cp:
                cp.set_types(["int8", "text", "int8", "text", "int8", "jsonb", "jsonb", "text", "text", "text"])
                for i in range(20000):
                    rc = ref_claims[i % len(ref_claims)]
                    obj = rc.get("object") or {}
                    is_ref = set(obj) == {"ref"}
                    cp.write_row((run, f"clm:vol-{i}", ents[(i * 7) % len(ents)], f"{prefix.get(rc['predicate'], 'stat')}:{rc['predicate']}",
                                  ents[(i * 13 + 1) % len(ents)] if is_ref else None, None if is_ref else obj, rc.get("qualifiers") or {},
                                  rc.get("statement_role"), "accepted", "stated"))
        cms = (time.perf_counter() - t0) * 1000
        tsv.append(["copy kb.claim", 20000, round(cms, 1), round(20000 / cms * 1000), "", "qualifiers and values of the v1 reference claims, cycled"])
        claims = [r[0] for r in c.execute("SELECT id FROM kb.claim WHERE run_id = %s ORDER BY id", (run,))]
        spans = [r[0] for r in c.execute("SELECT id FROM kb.span ORDER BY id")]
        t0 = time.perf_counter()
        with c.transaction():
            with c.cursor().copy("COPY kb.claim_support (claim_id, observation_id) FROM STDIN (FORMAT BINARY)") as cp:
                cp.set_types(["int8", "int8"])
                for i, cid in enumerate(claims):
                    cp.write_row((cid, prop_obs[i // 8]))
            with c.cursor().copy("COPY kb.claim_evidence (claim_id, span_id, role) FROM STDIN (FORMAT BINARY)") as cp:
                cp.set_types(["int8", "int8", "text"])
                for i, cid in enumerate(claims):
                    cp.write_row((cid, spans[i % len(spans)], "primary"))
        sms = (time.perf_counter() - t0) * 1000
        tsv.append(["copy kb.claim_support + kb.claim_evidence", 40000, round(sms, 1), round(40000 / sms * 1000), "", ""])
        c.execute("ANALYZE")
        c.commit()

        # queries at volume
        md = ["# S6 volume (brief step 7)", "", f"Run {run} (`full`, finished): {UNITS} units, {UNITS * 5} tasks, {n} observations, {len(ents)} entities, {len(claims)} claims. "
              "PostgreSQL 18.6 on the project-local cluster (shared_buffers 160 MB, work_mem 4 MB); client wall times, median of 7.", "",
              "| step | rows | ms | rows/s | mean payload B | note |", "|---|---|---|---|---|---|"]
        md += ["| " + " | ".join(str(x) for x in r) + " |" for r in tsv[1:]]
        md += ["", "D6 §3 binary COPY notes (one row each, rolled back): " + "; ".join(f"{k}: {v}" for k, v in notes.items()), ""]
        qs = [
            ("claims with qualifier param_values.variance (`@?`, no GIN)", "SELECT key FROM kb.claim WHERE run_id = %(run)s AND predicate = 'stat:has_distribution' AND qualifiers @? '$.param_values.variance'", {"run": run}),
            ("why a method ran (one unit)", "SELECT t.stage, m.name, pr.rule_key, t.trigger_metrics, t.status, t.cost FROM ops.task t JOIN ops.method_config mc ON mc.id = t.method_config_id "
             "JOIN ops.method m ON m.id = mc.method_id LEFT JOIN ops.policy_rule pr ON pr.id = t.trigger_rule_id WHERE t.run_id = %(run)s AND t.unit_key = %(unit_key)s ORDER BY t.id",
             {"run": run, "unit_key": "unit:vol-1234"}),
            ("effective observations of one task (kb.run_observation)", "SELECT count(*) FROM kb.run_observation WHERE run_id = %(run)s AND task_id = %(task)s", {"run": run, "task": tasks[("vol.mentions", 1234)]}),
            ("observations of the run by kind (kb.run_observation)", "SELECT kind, count(*) FROM kb.run_observation WHERE run_id = %(run)s GROUP BY 1 ORDER BY 1", {"run": run}),
            ("claims of one subject", "SELECT count(*) FROM kb.claim WHERE run_id = %(run)s AND subject_id = %(s)s", {"run": run, "s": ents[77]}),
        ]
        out["queries"] = {}
        for name, sql, params in qs:
            rows, ms = timed(c, sql, params)
            p = plan(c, sql, params)
            out["queries"][name] = {"rows": len(rows), "ms": ms, "plan": p}
            tsv.append([f"query: {name}", len(rows), ms, "", "", next((x.strip() for x in p if "Scan" in x), "")])
            md += [f"## {name}", "", f"{len(rows)} rows; median {ms} ms.", "", "```", *p, "```", ""]

        # sizes before deletion
        size_rows = sizes_table(c)
        # deletion at volume
        res, dmd = run_deletion(c, run, run1, f"Volume run {run} (5,000 entities, 20,000 claims)")
        c.commit()
        out["run_deletion"] = res
        (RESULTS / "run_deletion_volume.md").write_text("# S6 run deletion at volume (D3 §8)\n\n" + "\n".join(dmd))
        tsv.append(["delete materialized rows (entities, claims, cascades)", res["before"]["kb.claim"] + res["before"]["kb.entity"], res["ms"], "", "", "run row and tasks kept: " + str(res["ok"])])
    with (RESULTS / "volume.tsv").open("w") as f:
        for r in tsv:
            f.write("\t".join(str(x) for x in r) + "\n")
    (RESULTS / "volume.md").write_text("\n".join(md) + "\n")
    write_json(RESULTS / "volume.json", out | {"sizes": size_rows})
    for r in tsv:
        print(r)
    return 0


def sizes_table(c):
    rows = [["object", "kind", "rows", "table_bytes", "index_bytes", "total_bytes", "note"]]
    for s, t in c.execute("SELECT schemaname, tablename FROM pg_tables WHERE schemaname IN ('meta','kb','ops','eval') ORDER BY 1, 2").fetchall():
        q = f"{s}.{t}"
        n = c.execute(f"SELECT count(*) FROM {q}").fetchone()[0]
        tb, ib, tot = c.execute("SELECT pg_table_size(%s), pg_indexes_size(%s), pg_total_relation_size(%s)", (q, q, q)).fetchone()
        rows.append([q, "table", n, tb, ib, tot, ""])
    for s, i, t in c.execute("SELECT schemaname, indexname, tablename FROM pg_indexes WHERE schemaname IN ('meta','kb','ops','eval') ORDER BY 1, 3, 2").fetchall():
        rows.append([f"{s}.{i}", f"index on {t}", "", "", c.execute("SELECT pg_relation_size(%s)", (f"{s}.{i}",)).fetchone()[0], "", ""])
    seg_text, seg_raw, seg_n = c.execute("SELECT sum(pg_column_size(text)), sum(octet_length(text)), count(*) FROM kb.segment").fetchone()
    seg_idx = c.execute("SELECT sum(pg_column_size(text)), sum(octet_length(text)), count(*) FROM kb.segment WHERE kind IN ('paragraph','heading','list_item','math_display')").fetchone()
    canon, canon_raw = c.execute("SELECT sum(pg_column_size(canonical_text)), sum(octet_length(canonical_text)) FROM kb.rendition").fetchone()
    seg_tot = c.execute("SELECT pg_total_relation_size('kb.segment')").fetchone()[0]
    all_tot = c.execute("SELECT sum(pg_total_relation_size(c.oid)) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                        "WHERE n.nspname IN ('meta','kb','ops','eval') AND c.relkind IN ('r','m')").fetchone()[0]
    units = c.execute("SELECT count(*) FROM kb.segment WHERE kind = 'unit'").fetchone()[0]
    obs_payload, obs_n = c.execute("SELECT sum(pg_column_size(payload)), count(*) FROM kb.observation").fetchone()
    bm25 = c.execute("SELECT pg_relation_size('kb.segment_bm25')").fetchone()[0]
    rows += [["kb.segment.text", "column", seg_n, seg_text, "", "", f"stored bytes (raw {seg_raw}); {seg_text / seg_tot:.1%} of kb.segment with its indexes; {seg_text / all_tot:.2%} of the four schemas at volume"],
             ["kb.segment.text (BM25 kinds only)", "column", seg_idx[2], seg_idx[0], "", "", f"raw {seg_idx[1]}; the rows the BM25 index reads"],
             ["kb.rendition.canonical_text", "column", 4, canon, "", "", f"stored bytes, TOAST-compressed (raw {canon_raw}); raw segment text is {seg_raw / canon_raw:.1f}x the raw canonical text (every level of the tree, sentences included, repeats it)"],
             ["kb.segment_bm25", "index", "", "", bm25, "", "BM25 partial index over the four pages"],
             ["per unit", "ratio", units, round(seg_text / units), "", "", f"segment text bytes per author unit on the four pages ({units} units) vs observation payload bytes per volume unit "
              f"({round(obs_payload / obs_n * 40)} at 40 observations per unit)"],
             ["four schemas", "total", "", "", "", all_tot, "after the volume load, before its deletion"]]
    with (RESULTS / "sizes.tsv").open("w") as f:
        for r in rows:
            f.write("\t".join(str(x) for x in r) + "\n")
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
