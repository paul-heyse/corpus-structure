"""Probe Q-4 (P0-F-Q4, record ``p0q.fk-cost``): binary COPY at run scale on ``18/corpus`` with and without
the target model's same-run composite FKs and per-version vocabulary FKs, paired with the ``s6.volume``
rerun on the dedicated cluster.

    UV_PROJECT_ENVIRONMENT=$PWD/build/probe-venv uv run --project docs/design_review/evidence/2026-10-28_phase0-model-probes \
        python docs/design_review/evidence/2026-10-28_phase0-model-probes/code/q4_fk_cost.py all

Subcommands (``all`` runs them in order, each repetition in its own process on its own database clone):

- ``base``: ``p0q_fk`` cloned from ``cs_template``; S6's applied DDL (``code/q4_s6/s6_ddl_applied.sql``) and
  S6-B's row load (``s6b_rows.load``: the four spike pages, the v1 reference, run 1 promoted, run 2, the
  golden run), then ``ANALYZE``. Every repetition clones this database (``CREATE DATABASE … TEMPLATE p0q_fk``),
  so each starts from the same state.
- ``s6rerun --rep N``: variant **(a)**, the S6 schema as tested: S6's ``s6e_volume.py`` unchanged (copy in
  ``code/q4_s6``) on a clone — 12,500 tasks, 100,000 observations, 5,000 entities, 20,000 claims, 40,000
  support and evidence rows, the D3 queries, sizes and run deletion; outputs to ``results/q4/s6_rerun/repN``.
- ``target --variant V --rep N [--claims C]``: variant **(b)**, the target model's additions
  (TM §6) as a scratch addendum over S6's DDL, in three placements:

  - ``t_none``: the columns and edge tables, no same-run or vocabulary FK (the bulk-writer placement);
    edge rows are deleted explicitly by ``run_id`` at run deletion, since nothing cascades;
  - ``t_samerun``: plus ``UNIQUE (run_id, id)`` on ``kb.claim`` and ``kb.entity`` and the same-run composite FKs
    (``kb.claim_ref`` ×2, ``kb.claim_entity_ref`` ×2, ``kb.claim.attribution_entity_id``), cascading;
  - ``t_all``: plus the per-version vocabulary FKs ``(schema_version_id, predicate) → meta.schema_slot`` (INV-03)
    and ``(schema_version_id, kind) → meta.statement_kind``.

  The writes are S6's (same tasks and observations, payload generators imported from the copy), plus
  2,500 ``Statement`` entities (one per unit, ``kind`` cycled through D1's StatementKind), the new claim columns
  (``schema_version_id``; ``attribution_entity_id`` on every tenth claim; ``statement_id`` the unit's
  statement), one ``kb.claim_ref`` row and four ``kb.claim_entity_ref`` rows per claim (so 10⁵ edges at
  2×10⁴ claims). ``--claims 100000`` is the top of D3 §11's range (25,000 entities, 5×10⁵ edges).
  Negative checks (rolled back) show which placement refuses a cross-run edge, an unknown predicate and an
  unknown statement kind; the bulk-writer equivalent (Python set membership over the same rows) is timed.
- ``dataset``: one ``t_all`` load kept as a plain-SQL dump (``results/q4/raw/p0q_fk_dataset.sql.gz``, Git LFS)
  for C2's edge-join plan inspection; the generator is this script with ``RND`` seed 20261028.

All writes are psycopg 3.3.6 binary COPY with ``Copy.set_types``, each table in its own transaction as S6
did; times are client wall clock (``time.perf_counter``). Databases ``p0q_fk*`` are dropped at the end.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path

CODE = Path(__file__).resolve().parent
EVIDENCE = CODE.parent
OUT = EVIDENCE / "results" / "q4"
BASE = "p0q_fk"
SEED = 20261028
STATEMENT_KINDS = ["definition", "theorem", "proposition", "lemma", "corollary", "proof", "example", "exercise",
                   "solution", "remark", "convention", "notation", "assumption", "narrative"]
MODALITIES = ["asserted", "supposed", "defined", "conventional", "exemplified", "posed", "cited"]
VARIANTS = ["t_none", "t_samerun", "t_all"]

ADDENDUM_COMMON = """
CREATE TABLE meta.statement_kind (            -- per-version member table (TM §6, R05)
  schema_version_id bigint NOT NULL REFERENCES meta.schema_version ON DELETE CASCADE,
  value             text   NOT NULL,
  PRIMARY KEY (schema_version_id, value)
);
INSERT INTO meta.statement_kind (schema_version_id, value)
SELECT v.id, k FROM meta.schema_version v, unnest(ARRAY['definition','theorem','proposition','lemma','corollary','proof','example','exercise',
  'solution','remark','convention','notation','assumption','narrative']) k;
ALTER TABLE kb.claim
  ADD COLUMN modality text NOT NULL DEFAULT 'asserted' CHECK (modality IN ('asserted','supposed','defined','conventional','exemplified','posed','cited')),
  ADD COLUMN polarity text NOT NULL DEFAULT 'positive' CHECK (polarity IN ('positive','negative')),
  ADD COLUMN attribution_entity_id bigint,
  ADD COLUMN schema_version_id bigint REFERENCES meta.schema_version;
UPDATE kb.claim c SET schema_version_id = r.schema_version_id FROM ops.run r WHERE r.id = c.run_id;
ALTER TABLE kb.claim ALTER COLUMN schema_version_id SET NOT NULL;
CREATE TABLE kb.claim_ref (
  run_id          bigint NOT NULL,
  claim_id        bigint NOT NULL,
  kind            text   NOT NULL CHECK (kind IN ('condition_premise', 'binding_param')),
  path            text   NOT NULL,
  target_claim_id bigint NOT NULL,
  PRIMARY KEY (claim_id, kind, path)
);
CREATE INDEX claim_ref_target ON kb.claim_ref (target_claim_id);
CREATE TABLE kb.claim_entity_ref (
  run_id    bigint NOT NULL,
  claim_id  bigint NOT NULL,
  role      text   NOT NULL,
  slot      text,
  path      text   NOT NULL,
  entity_id bigint NOT NULL,
  PRIMARY KEY (claim_id, role, path)
);
CREATE INDEX claim_entity_ref_entity ON kb.claim_entity_ref (entity_id, role);
"""

ADDENDUM_SAMERUN = """
ALTER TABLE kb.claim  ADD CONSTRAINT claim_run_id_key  UNIQUE (run_id, id);
ALTER TABLE kb.entity ADD CONSTRAINT entity_run_id_key UNIQUE (run_id, id);
ALTER TABLE kb.claim ADD CONSTRAINT claim_attribution_same_run
  FOREIGN KEY (run_id, attribution_entity_id) REFERENCES kb.entity (run_id, id);
-- not in the TM §6 sketch: without an index on the referencing columns, every deleted entity's NO ACTION check
-- scans the run's claims (trial: 9.3 s for 7,500 entities, results/q4/trial_t_all_without_attribution_index.json)
CREATE INDEX claim_attribution ON kb.claim (run_id, attribution_entity_id) WHERE attribution_entity_id IS NOT NULL;
ALTER TABLE kb.claim_ref
  ADD CONSTRAINT claim_ref_claim  FOREIGN KEY (run_id, claim_id)        REFERENCES kb.claim (run_id, id) ON DELETE CASCADE,
  ADD CONSTRAINT claim_ref_target_same_run FOREIGN KEY (run_id, target_claim_id) REFERENCES kb.claim (run_id, id) ON DELETE CASCADE;
ALTER TABLE kb.claim_entity_ref
  ADD CONSTRAINT claim_entity_ref_claim  FOREIGN KEY (run_id, claim_id)  REFERENCES kb.claim  (run_id, id) ON DELETE CASCADE,
  ADD CONSTRAINT claim_entity_ref_entity_same_run FOREIGN KEY (run_id, entity_id) REFERENCES kb.entity (run_id, id) ON DELETE CASCADE;
"""

ADDENDUM_VOCAB = """
ALTER TABLE kb.claim ADD CONSTRAINT claim_predicate_in_version
  FOREIGN KEY (schema_version_id, predicate) REFERENCES meta.schema_slot (schema_version_id, name);   -- INV-03
ALTER TABLE kb.entity ADD CONSTRAINT entity_kind_in_version
  FOREIGN KEY (schema_version_id, kind) REFERENCES meta.statement_kind (schema_version_id, value);
"""


def env_for(db: str, results: Path | None = None) -> dict:
    e = dict(os.environ, Q4_DB=db, PYTHONHASHSEED="0")
    if results:
        e["Q4_RESULTS"] = str(results)
    return e


def s6mods():
    sys.path.insert(0, str(CODE / "q4_s6"))
    import s6_db  # noqa: E402

    return s6_db


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str) + "\n")


# ---- base ------------------------------------------------------------------------------------------

def cmd_base() -> int:
    os.environ["Q4_DB"] = BASE
    s6_db = s6mods()
    import s6a_ddl
    import s6b_rows

    t0 = time.perf_counter()
    s6_db.recreate_db(BASE)
    a = s6a_ddl.apply(s6_db.CODE / "s6_ddl_applied.sql")
    assert not a["errors"], a["errors"]
    with s6_db.app(BASE) as c:
        L, meta = s6b_rows.load(c)
        c.commit()
        slots = schema_slots(c, L.ids["schema"])
        c.commit()
        c.autocommit = True
        c.execute("ANALYZE")
        ext = dict(c.execute("SELECT extname, extversion FROM pg_extension ORDER BY 1").fetchall())
    facts = s6_db.server_facts()
    facts |= {"extensions": ext, "ddl": {k: a[k] for k in ("statements", "ms", "catalog")}, "base_ms": round((time.perf_counter() - t0) * 1000, 1),
              "schema_slot_rows_added": slots, "machine": machine()}
    write_json(OUT / "base.json", facts)
    print("base", facts["base_ms"], "ms; slots", slots)
    return 0


def schema_slots(c, sv: int) -> int:
    """meta.schema_slot rows for the run's schema version (S6-B's load leaves them empty; S6-D filled 0.2.0's):
    every slot of the 0.1.0 sources, prefixed as S6 prefixes predicates, so the INV-03 FK has its target."""
    import yaml
    from s6_load import EVIDENCE as SPIKE

    rows = []
    for f, p in (("core.yaml", "core"), ("statistics.yaml", "stat")):
        y = yaml.safe_load((SPIKE / "code" / "schema" / f).read_text())
        for s in (y.get("slots") or {}):
            rows.append((sv, f"{p}:{s}", "predicate"))
    seen, uniq = set(), []
    for r in rows:
        if r[1] not in seen:
            seen.add(r[1])
            uniq.append(r)
    with c.cursor() as cur:
        cur.executemany("INSERT INTO meta.schema_slot (schema_version_id, name, role) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", uniq)
    return len(uniq)


def machine() -> dict:
    cpu = next((ln.split(":", 1)[1].strip() for ln in Path("/proc/cpuinfo").read_text().splitlines() if ln.startswith("model name")), None)
    mem = next((ln.split(":", 1)[1].strip() for ln in Path("/proc/meminfo").read_text().splitlines() if ln.startswith("MemTotal")), None)
    import psycopg

    return {"cpu": cpu, "logical_cpus": os.cpu_count(), "mem_total": mem, "kernel": platform.release(), "python": platform.python_version(),
            "psycopg": psycopg.__version__, "psycopg_impl": psycopg.pq.__impl__, "libpq": psycopg.pq.version(),
            "load_1_5_15": os.getloadavg()}


# ---- clones ----------------------------------------------------------------------------------------

def clone(name: str) -> None:
    s6_db = s6mods()
    drop(name)
    with s6_db.admin() as c:
        c.execute(f"CREATE DATABASE {name} TEMPLATE {BASE}")


def drop(name: str) -> None:
    """Plain DROP DATABASE, retried: WITH (FORCE) cannot terminate an autovacuum worker as a non-superuser
    (42501, seen on a freshly loaded clone), while a plain DROP cancels autovacuum itself."""
    import psycopg

    s6_db = s6mods()
    for attempt in range(20):
        try:
            with s6_db.admin() as c:
                c.execute(f"DROP DATABASE IF EXISTS {name}")
            return
        except psycopg.errors.ObjectInUse:
            time.sleep(0.5)
    raise RuntimeError(f"could not drop {name}")


# ---- (a) the s6.volume rerun -----------------------------------------------------------------------

def cmd_s6rerun(rep: int) -> int:
    db = f"{BASE}_a"
    res = OUT / "s6_rerun" / f"rep{rep}"
    res.mkdir(parents=True, exist_ok=True)
    clone(db)
    load0 = os.getloadavg()
    try:
        t0 = time.perf_counter()
        r = subprocess.run([sys.executable, str(CODE / "q4_s6" / "s6e_volume.py")], env=env_for(db, res), cwd=CODE / "q4_s6",
                           capture_output=True, text=True)
        (res / "stdout.txt").write_text(r.stdout + ("\n--- stderr\n" + r.stderr if r.stderr else ""))
        if r.returncode:
            print(r.stdout, r.stderr)
            return r.returncode
        write_json(res / "load.json", {"loadavg_before": load0, "loadavg_after": os.getloadavg(), "wall_s": round(time.perf_counter() - t0, 1)})
        print("s6rerun", rep, round((time.perf_counter() - t0), 1), "s")
    finally:
        drop(db)
    return 0


# ---- (b) the target-model variants -----------------------------------------------------------------

def cmd_target(variant: str, rep: int, claims_n: int, keep: bool = False, db: str | None = None) -> dict:
    db = db or f"{BASE}_{variant}"
    clone(db)
    os.environ["Q4_DB"] = db
    s6mods()
    load0 = os.getloadavg()
    try:
        out = target_volume(db, variant, claims_n)
    finally:
        if not keep:
            drop(db)
    out |= {"variant": variant, "rep": rep, "claims_n": claims_n, "loadavg_before": load0, "loadavg_after": os.getloadavg()}
    write_json(OUT / "target" / f"{variant}_c{claims_n}_rep{rep}.json", out)
    print(variant, claims_n, rep, {k: v for k, v in out["ms"].items()})
    return out


def addendum(variant: str) -> str:
    sql = ADDENDUM_COMMON
    if variant in ("t_samerun", "t_all"):
        sql += ADDENDUM_SAMERUN
    if variant == "t_all":
        sql += ADDENDUM_VOCAB
    return sql


def target_volume(db: str, variant: str, claims_n: int, delete: bool = True) -> dict:
    import random

    import psycopg
    import s6_db
    import s6e_volume as V
    from s6_load import T0, Loader, predicate_prefixes, sha

    rnd = random.Random(SEED)
    units = V.UNITS
    sents, batches, ref_claims = V.payloads()
    prefix = predicate_prefixes()
    ms: dict[str, float] = {}
    rows: dict[str, int] = {}
    with s6_db.app(db) as c:
        for stmt in s6_db.split_sql(addendum(variant)):
            c.execute(stmt)
        L = Loader(c)
        L.ids["schema"] = c.execute("SELECT id FROM meta.schema_version ORDER BY id LIMIT 1").fetchone()[0]
        for k in ("project",):
            L.ids[k] = c.execute("SELECT id FROM meta.project LIMIT 1").fetchone()[0]
        L.ids["guideline"] = c.execute("SELECT id FROM meta.guideline_version ORDER BY id LIMIT 1").fetchone()[0]
        L.ids["policy"] = c.execute("SELECT id FROM ops.policy_version LIMIT 1").fetchone()[0]
        L.ids["slice"] = c.execute("SELECT id FROM ops.debug_slice LIMIT 1").fetchone()[0]
        sv = L.ids["schema"]
        run1 = c.execute("SELECT promoted_run_id FROM meta.project").fetchone()[0]
        cfg = {}
        for name, fam in (("vol.mentions", "extract"), ("vol.relations", "extract"), ("vol.scope", "resolve"), ("vol.values", "normalize"), ("vol.propose", "llm")):
            mid = c.execute("INSERT INTO ops.method (name, version, family) VALUES (%s, '1', %s) RETURNING id", (name, fam)).fetchone()[0]
            cfg[name] = c.execute("INSERT INTO ops.method_config (method_id, params, config_hash, tier) VALUES (%s, '{}', %s, 'deterministic') RETURNING id",
                                  (mid, f"cfg:{name}")).fetchone()[0]
        run = L.run("volume", "full", started=T0 + timedelta(days=1), finished=T0 + timedelta(days=1, hours=3), reference=run1)
        segs = [r[0] for r in c.execute("SELECT id FROM kb.segment WHERE kind IN ('unit','paragraph') ORDER BY id")]
        ren = c.execute("SELECT id FROM kb.rendition ORDER BY id LIMIT 1").fetchone()[0]
        slot_names = {r[0] for r in c.execute("SELECT name FROM meta.schema_slot WHERE schema_version_id = %s", (sv,))}
        c.commit()
        c.execute("ANALYZE meta.statement_kind")
        c.commit()

        def copy(label, sql, types, gen):
            t0 = time.perf_counter()
            n = 0
            with c.transaction():
                with c.cursor().copy(sql) as cp:
                    cp.set_types(types)
                    for r in gen:
                        cp.write_row(r)
                        n += 1
            ms[label] = round((time.perf_counter() - t0) * 1000, 1)
            rows[label] = n

        stages = [("extract", "vol.mentions"), ("extract", "vol.relations"), ("scope", "vol.scope"), ("normalize", "vol.values"), ("propose", "vol.propose")]
        copy("ops.task", "COPY ops.task (run_id, stage, unit_type, unit_id, unit_key, method_config_id, input_hash, status, attempt, cost, "
             "created_at, started_at, finished_at) FROM STDIN (FORMAT BINARY)",
             ["int8", "text", "text", "int8", "text", "int8", "text", "text", "int4", "jsonb", "timestamptz", "timestamptz", "timestamptz"],
             ((run, st, "segment", segs[u % len(segs)], f"unit:vol-{u}", cfg[m], sha([m, u]), "done", 1, {"wall_ms": 40 + u % 50},
               T0 + timedelta(days=1), T0 + timedelta(days=1, minutes=1), T0 + timedelta(days=1, hours=1)) for u in range(units) for st, m in stages))
        tasks = {(m, u): tid for tid, m, u in c.execute(
            "SELECT t.id, m.name, substr(t.unit_key, 10)::int FROM ops.task t JOIN ops.method_config mc ON mc.id = t.method_config_id "
            "JOIN ops.method m ON m.id = mc.method_id WHERE t.run_id = %s", (run,))}
        kinds = [("vol.mentions", "mention", 16, V.mention), ("vol.relations", "relation", 8, V.relation), ("vol.scope", "scope", 8, V.scope), ("vol.values", "value", 7, V.value)]

        def obs():
            for u in range(units):
                for m, kind, k, f in kinds:
                    for j in range(k):
                        yield (tasks[(m, u)], j, kind, ren, segs[u % len(segs)], f(sents, u * 40 + j), 0.5 + (j % 5) / 10, "produced")
                yield (tasks[("vol.propose", u)], 0, "claim_proposal", ren, segs[u % len(segs)], {"batch": batches[u % len(batches)], "rationale": None}, None, "produced")
        copy("kb.observation", "COPY kb.observation (task_id, ordinal, kind, rendition_id, segment_id, payload, score, outcome) FROM STDIN (FORMAT BINARY)",
             ["int8", "int4", "text", "int8", "int8", "jsonb", "float4", "text"], obs())
        prop_obs = {u: oid for oid, u in c.execute(
            "SELECT o.id, substr(t.unit_key, 10)::int FROM kb.observation o JOIN ops.task t ON t.id = o.task_id "
            "WHERE t.run_id = %s AND o.kind = 'claim_proposal'", (run,))}

        n_ent = max(5000, claims_n // 4)

        def ents_gen():
            for i in range(n_ent):
                glob = i % 10 == 0
                yield (run, f"ent:vol-{i}", sv, "DistributionFamily" if glob else "RandomVariable", f"e{i}", "global" if glob else "local",
                       None if glob else segs[(i // 2) % len(segs)], {}, None)
            for u in range(units):
                yield (run, f"stm:vol-{u}", sv, "Statement", f"s{u}", "local", segs[u % len(segs)], {}, STATEMENT_KINDS[u % len(STATEMENT_KINDS)])
        copy("kb.entity", "COPY kb.entity (run_id, key, schema_version_id, type, label, scope, scope_segment_id, attrs, kind) FROM STDIN (FORMAT BINARY)",
             ["int8", "text", "int8", "text", "text", "text", "int8", "jsonb", "text"], ents_gen())
        ents, stms = [], {}
        for eid, k in c.execute("SELECT id, key FROM kb.entity WHERE run_id = %s ORDER BY id", (run,)):
            if k.startswith("stm:"):
                stms[int(k[8:])] = eid
            else:
                ents.append(eid)
        per_unit = max(1, claims_n // units)

        def claims_gen():
            for i in range(claims_n):
                rc = ref_claims[i % len(ref_claims)]
                obj = rc.get("object") or {}
                is_ref = set(obj) == {"ref"}
                q = rc.get("qualifiers") or {}
                yield (run, f"clm:vol-{i}", ents[(i * 7) % len(ents)], f"{prefix.get(rc['predicate'], 'stat')}:{rc['predicate']}",
                       ents[(i * 13 + 1) % len(ents)] if is_ref else None, None if is_ref else obj, q, stms[min(i // per_unit, units - 1)],
                       rc.get("statement_role"), "accepted", "stated", MODALITIES[i % 3], "negative" if i % 17 == 0 else "positive",
                       ents[(i * 3) % len(ents)] if i % 10 == 0 else None, sv)
        claim_rows = list(claims_gen())
        copy("kb.claim", "COPY kb.claim (run_id, key, subject_id, predicate, object_entity_id, object_value, qualifiers, statement_id, statement_role, "
             "status, establishment, modality, polarity, attribution_entity_id, schema_version_id) FROM STDIN (FORMAT BINARY)",
             ["int8", "text", "int8", "text", "int8", "jsonb", "jsonb", "int8", "text", "text", "text", "text", "text", "int8", "int8"], iter(claim_rows))
        claims = [r[0] for r in c.execute("SELECT id FROM kb.claim WHERE run_id = %s ORDER BY id", (run,))]
        spans = [r[0] for r in c.execute("SELECT id FROM kb.span ORDER BY id")]
        copy("kb.claim_support", "COPY kb.claim_support (claim_id, observation_id) FROM STDIN (FORMAT BINARY)", ["int8", "int8"],
             ((cid, prop_obs[min(i // per_unit, units - 1)]) for i, cid in enumerate(claims)))
        copy("kb.claim_evidence", "COPY kb.claim_evidence (claim_id, span_id, role) FROM STDIN (FORMAT BINARY)", ["int8", "int8", "text"],
             ((cid, spans[i % len(spans)], "primary") for i, cid in enumerate(claims)))
        nc = len(claims)
        ref_rows = [(run, cid, "condition_premise" if i % 2 else "binding_param", "/qualifiers/conditions/0/claim" if i % 2 else "/object_value/symbols/mu",
                     claims[(i + 1 + rnd.randrange(nc - 1)) % nc]) for i, cid in enumerate(claims)]
        roles = (("qualifier", "stat:param_values", "/qualifiers/param_values/variance"), ("pred_arg", None, "/qualifiers/conditions/0/args/0"),
                 ("pred_arg", None, "/qualifiers/conditions/0/args/1"), ("binding_variable", None, "/object_value/symbols/x"))
        ce_rows = [(run, cid, role, slot, path, ents[rnd.randrange(len(ents))]) for cid in claims for role, slot, path in roles]
        copy("kb.claim_ref", "COPY kb.claim_ref (run_id, claim_id, kind, path, target_claim_id) FROM STDIN (FORMAT BINARY)",
             ["int8", "int8", "text", "text", "int8"], iter(ref_rows))
        copy("kb.claim_entity_ref", "COPY kb.claim_entity_ref (run_id, claim_id, role, slot, path, entity_id) FROM STDIN (FORMAT BINARY)",
             ["int8", "int8", "text", "text", "text", "int8"], iter(ce_rows))

        # the bulk writer's equivalent check, in process over the same rows (what t_none would need)
        t0 = time.perf_counter()
        claim_set, ent_set = set(claims), set(ents) | set(stms.values())
        bad = sum(1 for r in ref_rows if r[1] not in claim_set or r[4] not in claim_set)
        bad += sum(1 for r in ce_rows if r[1] not in claim_set or r[5] not in ent_set)
        bad += sum(1 for r in claim_rows if r[3] not in slot_names or (r[13] is not None and r[13] not in ent_set))
        bad += sum(1 for u in range(units) if STATEMENT_KINDS[u % len(STATEMENT_KINDS)] not in STATEMENT_KINDS)
        py_check_ms = round((time.perf_counter() - t0) * 1000, 2)

        t0 = time.perf_counter()
        c.commit()   # the COPYs after the first ran as savepoints of one transaction, as in S6's s6e_volume
        commit_ms = round((time.perf_counter() - t0) * 1000, 1)
        c.autocommit = True
        t0 = time.perf_counter()
        c.execute("ANALYZE")
        analyze_ms = round((time.perf_counter() - t0) * 1000, 1)
        c.autocommit = False

        negatives = negative_checks(c, run, run1, sv, claims, ents)
        sizes = {t: c.execute("SELECT pg_total_relation_size(%s), pg_indexes_size(%s)", (t, t)).fetchone()
                 for t in ("kb.claim", "kb.entity", "kb.claim_ref", "kb.claim_entity_ref", "kb.observation")}
        c.commit()
        out = {"ms": ms, "rows": rows, "commit_ms": commit_ms, "py_check_ms": py_check_ms, "py_check_bad": bad, "analyze_ms": analyze_ms, "negatives": negatives, "run": run,
               "sizes_total_index_bytes": sizes, "constraints": constraints(c)}
        if delete:
            out["deletion"] = run_deletion(c, run, run1, variant)
        c.commit()
    return out


def constraints(c) -> list:
    return [list(r) for r in c.execute(
        "SELECT conrelid::regclass::text, conname, contype, pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conrelid IN ('kb.claim'::regclass, 'kb.entity'::regclass, 'kb.claim_ref'::regclass, 'kb.claim_entity_ref'::regclass) "
        "AND contype IN ('f','u') ORDER BY 1, 2")]


def negative_checks(c, run, run1, sv, claims, ents) -> dict:
    import psycopg

    other_claim = c.execute("SELECT id FROM kb.claim WHERE run_id = %s ORDER BY id LIMIT 1", (run1,)).fetchone()[0]
    other_ent = c.execute("SELECT id FROM kb.entity WHERE run_id = %s ORDER BY id LIMIT 1", (run1,)).fetchone()[0]
    seg = c.execute("SELECT id FROM kb.segment ORDER BY id LIMIT 1").fetchone()[0]
    cases = {
        "claim_ref target in another run (INV-08)": ("INSERT INTO kb.claim_ref VALUES (%s, %s, 'condition_premise', '/neg', %s)", (run, claims[0], other_claim)),
        "claim_entity_ref entity in another run": ("INSERT INTO kb.claim_entity_ref VALUES (%s, %s, 'pred_arg', NULL, '/neg', %s)", (run, claims[0], other_ent)),
        "claim predicate not in the version's slots (INV-03)": (
            "INSERT INTO kb.claim (run_id, key, subject_id, predicate, object_value, status, establishment, schema_version_id) "
            "VALUES (%s, 'clm:neg', %s, 'stat:no_such_slot', '{}', 'accepted', 'stated', %s)", (run, ents[0], sv)),
        "statement kind not in the version's members": (
            "INSERT INTO kb.entity (run_id, key, schema_version_id, type, label, scope, scope_segment_id, kind) "
            "VALUES (%s, 'stm:neg', %s, 'Statement', 'x', 'local', %s, 'no_such_kind')", (run, sv, seg)),
    }
    out = {}
    for name, (sql, params) in cases.items():
        try:
            with c.transaction(force_rollback=True):
                c.execute(sql, params)
            out[name] = "accepted"
        except psycopg.Error as e:
            out[name] = f"refused {e.sqlstate} ({e.diag.constraint_name})"
    return out


def run_deletion(c, run, keep_run, variant) -> dict:
    deletes = [("eval.result", "DELETE FROM eval.result WHERE run_id = %(run)s"),
               ("eval.alignment", "DELETE FROM eval.alignment WHERE run_id = %(run)s"),
               ("kb.claim_link", "DELETE FROM kb.claim_link WHERE run_id = %(run)s")]
    if variant == "t_none":   # nothing cascades to the edge tables: the bulk writer's delete names them
        deletes += [("kb.claim_ref", "DELETE FROM kb.claim_ref WHERE run_id = %(run)s"),
                    ("kb.claim_entity_ref", "DELETE FROM kb.claim_entity_ref WHERE run_id = %(run)s")]
    deletes += [("kb.claim", "DELETE FROM kb.claim WHERE run_id = %(run)s"), ("kb.entity", "DELETE FROM kb.entity WHERE run_id = %(run)s")]

    def counts(r):
        return {t: c.execute(f"SELECT count(*) FROM {t} WHERE run_id = %s", (r,)).fetchone()[0]
                for t in ("kb.entity", "kb.claim", "kb.claim_ref", "kb.claim_entity_ref", "ops.task")} | {
            "kb.claim_support": c.execute("SELECT count(*) FROM kb.claim_support s JOIN kb.claim cl ON cl.id = s.claim_id WHERE cl.run_id = %s", (r,)).fetchone()[0]}
    before, keep_before = counts(run), counts(keep_run)
    # trigger breakdown, rolled back, before the timed deletion
    trig = []
    with c.transaction(force_rollback=True):
        for t, sql in deletes:
            rr = c.execute(f"EXPLAIN (ANALYZE, COSTS off, TIMING on, SUMMARY on) {sql}", {"run": run}).fetchall()
            trig += [f"{t}: " + x[0].strip() for x in rr if x[0].lstrip().startswith(("Trigger", "Execution Time", "Delete on"))]
    t0 = time.perf_counter()
    with c.transaction():
        for _, sql in deletes:
            c.execute(sql, {"run": run})
    ms = round((time.perf_counter() - t0) * 1000, 1)
    after, keep_after = counts(run), counts(keep_run)
    ok = all(after[t] == 0 for t in ("kb.entity", "kb.claim", "kb.claim_ref", "kb.claim_entity_ref", "kb.claim_support")) and after["ops.task"] == before["ops.task"] and keep_after == keep_before
    return {"ms": ms, "before": before, "after": after, "kept_run_unchanged": keep_after == keep_before, "ok": ok, "explain_triggers": trig}


# ---- dataset ---------------------------------------------------------------------------------------

def cmd_dataset() -> int:
    db = f"{BASE}_dataset"
    clone(db)
    os.environ["Q4_DB"] = db
    s6mods()
    try:
        out = target_volume(db, "t_all", 20000, delete=False)
        raw = OUT / "raw"
        raw.mkdir(parents=True, exist_ok=True)
        dump = raw / "p0q_fk_dataset.sql.gz"
        with dump.open("wb") as f:
            p1 = subprocess.Popen(["pg_dump", "-h", "/var/run/postgresql", "-p", "5434", "--no-owner", "--no-privileges", db], stdout=subprocess.PIPE)
            p2 = subprocess.run(["gzip", "-9n"], stdin=p1.stdout, stdout=f)
            p1.wait()
        write_json(OUT / "dataset.json", {"db": db, "variant": "t_all", "claims_n": 20000, "seed": SEED, "run": out["run"], "rows": out["rows"],
                                          "dump": str(dump.relative_to(EVIDENCE)), "dump_bytes": dump.stat().st_size,
                                          "restore": "createdb -T cs_template <db> && gunzip -c results/q4/raw/p0q_fk_dataset.sql.gz | psql -d <db>",
                                          "pg_dump_rc": p1.returncode, "gzip_rc": p2.returncode})
        print("dataset", dump, dump.stat().st_size)
    finally:
        drop(db)
    return 0


# ---- orchestration ---------------------------------------------------------------------------------

def child(*args) -> None:
    r = subprocess.run([sys.executable, str(Path(__file__).resolve()), *args], env=dict(os.environ, PYTHONHASHSEED="0"))
    if r.returncode:
        raise SystemExit(f"child {args} failed: {r.returncode}")


def cmd_all(reps: int, high_reps: int) -> int:
    child("base")
    for rep in range(reps):
        child("s6rerun", "--rep", str(rep))
        order = VARIANTS[rep % 3:] + VARIANTS[: rep % 3]   # rotate the order between repetitions
        for v in order:
            child("target", "--variant", v, "--rep", str(rep))
    for rep in range(high_reps):
        for v in (["t_none", "t_all"] if rep % 2 == 0 else ["t_all", "t_none"]):
            child("target", "--variant", v, "--rep", str(rep), "--claims", "100000")
    child("dataset")
    drop(BASE)
    child("summary")
    return 0


# ---- summary ---------------------------------------------------------------------------------------

S6_VOLUME = {"copy ops.task": 103.4, "copy kb.observation": 1109.7, "copy kb.entity": None, "copy kb.claim": 228.6,
             "delete materialized rows (entities, claims, cascades)": 260.8,
             "query: claims with qualifier param_values.variance (`@?`, no GIN)": 1.001, "query: why a method ran (one unit)": 0.559,
             "query: observations of the run by kind (kb.run_observation)": 17.931}


def spread(xs):
    xs = sorted(xs)
    return {"median": round(statistics.median(xs), 1 if max(xs) >= 10 else 3), "min": xs[0], "max": xs[-1], "n": len(xs)}


def cmd_summary() -> int:
    out: dict = {"base": json.loads((OUT / "base.json").read_text())}
    # (a) the s6.volume rerun
    steps: dict[str, list] = {}
    notes: dict[str, str] = {}
    for f in sorted((OUT / "s6_rerun").glob("rep*/volume.tsv")):
        for ln in f.read_text().splitlines()[1:]:
            r = ln.split("\t")
            steps.setdefault(r[0], []).append(float(r[2]))
            if r[0].startswith("query") and f.parent.name == "rep0":
                notes[r[0]] = r[5]
    v0 = json.loads((OUT / "s6_rerun" / "rep0" / "volume.json").read_text())
    for name, q in v0["queries"].items():
        notes[f"query: {name}"] = "; ".join(x.strip().removeprefix("->  ") for x in q["plan"] if "Scan" in x)
    out["s6_rerun_copy_type_notes"] = v0["copy_type_notes"]
    out["s6_rerun"] = {k: spread(v) | {"s6_volume_interim_cluster": S6_VOLUME.get(k), "plan_rep0": notes.get(k)} for k, v in steps.items()}
    out["s6_rerun_loadavg"] = [json.loads(f.read_text()) for f in sorted((OUT / "s6_rerun").glob("rep*/load.json"))]
    # (b) the target variants
    tv: dict = {}
    for f in sorted((OUT / "target").glob("*.json")):
        d = json.loads(f.read_text())
        key = f"{d['variant']} @ {d['claims_n']} claims"
        e = tv.setdefault(key, {"variant": d["variant"], "claims_n": d["claims_n"], "steps": {}, "materialized_ms": [], "edges_ms": [], "load_ms": [],
                                "deletion_ms": [], "py_check_ms": [], "rows": d["rows"], "negatives": d["negatives"], "deletion_ok": [], "loadavg_1m": [],
                                "sizes_total_index_bytes": d["sizes_total_index_bytes"], "explain_triggers_rep0": None, "constraints": d["constraints"]})
        for k, v in d["ms"].items():
            e["steps"].setdefault(k, []).append(v)
        e["materialized_ms"].append(sum(d["ms"][k] for k in ("kb.entity", "kb.claim", "kb.claim_support", "kb.claim_evidence", "kb.claim_ref", "kb.claim_entity_ref")))
        e["edges_ms"].append(d["ms"]["kb.claim_ref"] + d["ms"]["kb.claim_entity_ref"])
        e["load_ms"].append(sum(d["ms"].values()))
        e["deletion_ms"].append(d["deletion"]["ms"])
        e["deletion_ok"].append(d["deletion"]["ok"])
        e["py_check_ms"].append(d["py_check_ms"])
        e["loadavg_1m"].append(round(d["loadavg_before"][0], 2))
        if d["rep"] == 0:
            e["explain_triggers_rep0"] = d["deletion"]["explain_triggers"]
    for e in tv.values():
        e["steps"] = {k: spread(v) for k, v in e["steps"].items()}
        for k in ("materialized_ms", "edges_ms", "load_ms", "deletion_ms", "py_check_ms"):
            e[k] = spread(e[k])
    out["target"] = tv
    deltas = {}
    for n in (20000, 100000):
        base = tv.get(f"t_none @ {n} claims")
        for v in ("t_samerun", "t_all"):
            o = tv.get(f"{v} @ {n} claims")
            if base and o:
                deltas[f"{v} - t_none @ {n}"] = {k: round(o[k]["median"] - base[k]["median"], 1) for k in ("materialized_ms", "edges_ms", "load_ms", "deletion_ms")} | {
                    "claim_ms": round(o["steps"]["kb.claim"]["median"] - base["steps"]["kb.claim"]["median"], 1),
                    "entity_ms": round(o["steps"]["kb.entity"]["median"] - base["steps"]["kb.entity"]["median"], 1),
                    "load_ratio": round(o["load_ms"]["median"] / base["load_ms"]["median"], 3),
                    "materialized_ratio": round(o["materialized_ms"]["median"] / base["materialized_ms"]["median"], 3)}
    out["fk_overhead_medians"] = deltas
    write_json(OUT / "summary.json", out)
    L = ["# Q-4 summary (generated by `q4_fk_cost.py summary`)", "", "Medians over repetitions (min–max); client wall ms.", "",
         "## (a) `s6.volume` rerun on 18/corpus", "", "| step | rerun median (min–max), n | s6.volume (interim cluster) | plan (rep0) |", "|---|---|---|---|"]
    for k, v in out["s6_rerun"].items():
        L.append(f"| {k} | {v['median']} ({v['min']}–{v['max']}), {v['n']} | {v['s6_volume_interim_cluster'] if v['s6_volume_interim_cluster'] is not None else '—'} | {v['plan_rep0'] or ''} |")
    L += ["", "## (b) target model: per-table COPY ms", ""]
    names = list(next(iter(tv.values()))["steps"])
    L += ["| variant | " + " | ".join(names) + " | materialized | load | deletion | py check |", "|---" * (len(names) + 5) + "|"]
    for k, e in tv.items():
        L.append(f"| {k} | " + " | ".join(f"{e['steps'][n]['median']} ({e['steps'][n]['min']}–{e['steps'][n]['max']})" for n in names)
                 + f" | {e['materialized_ms']['median']} | {e['load_ms']['median']} | {e['deletion_ms']['median']} ({e['deletion_ms']['min']}–{e['deletion_ms']['max']}) | {e['py_check_ms']['median']} |")
    L += ["", "## FK overhead (median differences against t_none)", "", "```json", json.dumps(deltas, indent=1), "```", "",
          "## Negative checks", ""]
    for k, e in tv.items():
        L.append(f"- {k}: {e['negatives']}")
    L += ["", "## Deletion trigger lines (rep 0, EXPLAIN ANALYZE, rolled back)", ""]
    for k, e in tv.items():
        L += [f"### {k}", "", "```", *(e["explain_triggers_rep0"] or []), "```", ""]
    (OUT / "summary.md").write_text("\n".join(L) + "\n")
    print(json.dumps(deltas, indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("base")
    a = sub.add_parser("s6rerun")
    a.add_argument("--rep", type=int, required=True)
    t = sub.add_parser("target")
    t.add_argument("--variant", choices=VARIANTS, required=True)
    t.add_argument("--rep", type=int, required=True)
    t.add_argument("--claims", type=int, default=20000)
    sub.add_parser("dataset")
    al = sub.add_parser("all")
    al.add_argument("--reps", type=int, default=5)
    al.add_argument("--high-reps", type=int, default=3)
    sub.add_parser("drop")
    sub.add_parser("summary")
    a = ap.parse_args()
    if a.cmd == "base":
        return cmd_base()
    if a.cmd == "s6rerun":
        return cmd_s6rerun(a.rep)
    if a.cmd == "target":
        cmd_target(a.variant, a.rep, a.claims)
        return 0
    if a.cmd == "dataset":
        return cmd_dataset()
    if a.cmd == "summary":
        return cmd_summary()
    if a.cmd == "drop":
        for d in (BASE, f"{BASE}_a", *(f"{BASE}_{v}" for v in VARIANTS), f"{BASE}_dataset"):
            drop(d)
        return 0
    return cmd_all(a.reps, a.high_reps)


if __name__ == "__main__":
    raise SystemExit(main())
