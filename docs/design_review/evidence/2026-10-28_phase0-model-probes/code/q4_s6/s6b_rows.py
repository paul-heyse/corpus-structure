"""Copy of S6's ``code/s6b_rows.py`` (design-spikes, 2026-10-28) for probe Q-4: unchanged; ``load`` and ``run_deletion`` are used. Original docstring follows.

S6-B (brief step 3): trace rows, golden-run rows, the constraint sweep and the run-deletion check.

    uv run python code/s6b_rows.py        # project-local cluster (just db-up); recreates cs_spike_s6

1. Recreates ``cs_spike_s6`` from ``cs_template`` and applies ``code/s6_ddl_applied.sql`` as the
   application role (S6-A).
2. Loads the rows (``code/s6_load.py``): run 1 (finished, promoted) with the four pages and the
   twelve core units of the v1 reference; the golden run with passes a/b/c and items; run 2
   (finished, not promoted) with a reused ingest/propose task, a task finished after the run, and
   materialized rows for T2 and T3 plus an alignment and a result.
3. Checks the brief's row questions (T3's C2 conditions, T4's seventeen claims, context-premise
   evidence outside its unit, golden ordering, ``kb.run_observation`` with reuse and the fate cut).
4. The constraint sweep, in one transaction rolled back at the end: the brief's named bad rows,
   then every CHECK, NOT NULL, FOREIGN KEY, UNIQUE and PRIMARY KEY constraint of the four schemas
   with one mutated copy of an existing row each, and the invariants the database does not
   express (expected: no error). Writes ``results/s6/constraints.tsv``.
5. Run deletion (D3 §8): run 2's materialized rows deleted by ``run_id``; ``EXPLAIN`` plans with and
   without ``enable_seqscan``; the run row and its tasks kept. Writes ``results/s6/run_deletion.md``.
Writes ``results/s6/rows.json``.
"""

from __future__ import annotations

import json
import re
import time
from datetime import timedelta

import psycopg
from psycopg.types.json import Jsonb

from s6_db import CODE, RESULTS, app, recreate_db, write_json
from s6_load import CORE, PAGES, S0R2, SAMPLE, T0, Loader, key, sha
from s6a_ddl import apply

SCHEMAS = ("meta", "kb", "ops", "eval")


def load(c) -> tuple[Loader, dict]:
    L = Loader(c)
    L.scaffold()
    run1 = L.run("run1", "slice")
    L.pages(run1)
    units = {}
    for u in CORE:
        units[u] = L.load_unit(run1, u, json.loads((S0R2 / "reference_v1" / f"{u}.json").read_text()))
    d1 = L.derived_link(run1, units["T3"])
    L.escalation(run1, "T3", units["T3"])
    c.execute("UPDATE meta.project SET promoted_run_id = %s WHERE id = %s", (run1, L.ids["project"]))
    gold = L.goldens(run1)
    # run 2: reuses run 1's ingest tasks and T3's propose task; T2's own propose task finishes after the run
    fin2 = T0 + timedelta(hours=8)
    run2 = L.run("run2", "slice", started=T0 + timedelta(hours=7), finished=fin2, reference=run1)
    for page in PAGES:
        t1 = L.one("SELECT id FROM ops.task WHERE run_id = %s AND stage = 'ingest' AND unit_id = %s", (run1, L.doc_id[page]))
        L.task(run2, "ingest", "document", L.doc_id[page], None, "cfg:ingest.html/default", status="reused", reused_task_id=t1,
               created=T0 + timedelta(hours=7), finished=T0 + timedelta(hours=7))
    t3_run1 = units["T3"]["task"]
    reused = L.task(run2, "propose", "segment", L.unit_segment("T3"), units["T3"]["unit_key"], "cfg:agent.opus/default", status="reused",
                    reused_task_id=t3_run1, created=T0 + timedelta(hours=7), finished=T0 + timedelta(hours=7, minutes=1))
    b2 = json.loads((S0R2 / "reference_v1" / "T2.json").read_text())
    late = L.load_unit(run2, "T2", b2, materialize=False)
    c.execute("UPDATE ops.task SET finished_at = %s, created_at = %s WHERE id = %s", (fin2 + timedelta(minutes=30), T0 + timedelta(hours=7), late["task"]))
    m2 = {u: L.materialize(run2, u, json.loads((S0R2 / "reference_v1" / f"{u}.json").read_text()), units[u]["observation"]) for u in ("T2", "T3")}
    L.derived_link(run2, m2["T3"])
    gi = L.one("SELECT id FROM eval.golden_item WHERE item_type = 'claim' ORDER BY id LIMIT 1")
    c.execute("INSERT INTO eval.alignment (run_id, golden_item_id, target_type, target_id, tier, score) VALUES (%s, %s, 'claim', %s, 'core', 1.0)",
              (run2, gi, next(iter(m2["T3"]["claims"].values()))))
    c.execute("INSERT INTO eval.result (run_id, golden_set_id, scope_type, metric, tier, value, n, golden_snapshot) "
              "VALUES (%s, %s, 'all', 'f1', 'core', 0.5, 2, %s)",
              (run2, gold["golden_set"], [r[0] for r in c.execute("SELECT id FROM eval.golden_pass WHERE pass = 'c'")]))
    c.execute("INSERT INTO ops.measurement (run_id, task_id, iteration, scope_type, scope_key, metric, value) VALUES (%s, NULL, 0, 'run', NULL, 'claims.count', 2)", (run2,))
    meta = {"units": {u: {k: v for k, v in units[u].items() if k in ("task", "observation", "merged_globals", "evidence_rows", "misfits")} for u in CORE},
            "d1": d1, "golden": {k: v for k, v in gold.items() if k != "task_order"}, "run2": run2, "reused_task": reused, "late_task": late["task"],
            "t3_run1_task": t3_run1, "late_observation": late["observation"]}
    meta["_units"] = units
    meta["_gold_order"] = gold["task_order"]
    return L, meta


def checks(c, L: Loader, meta: dict) -> dict:
    run1, run2 = L.ids["run1"], meta["run2"]
    u = meta["_units"]
    out = {}
    out["counts"] = {f"{s}.{t}": c.execute(f"SELECT count(*) FROM {s}.{t}").fetchone()[0]
                     for s, t in c.execute("SELECT schemaname, tablename FROM pg_tables WHERE schemaname = ANY(%s) ORDER BY 1, 2", (list(SCHEMAS),)).fetchall()}
    c2 = u["T3"]["claims"]["c_aX_def"]
    cond = c.execute("SELECT predicate, statement_role, qualifiers -> 'conditions' FROM kb.claim WHERE id = %s", (c2,)).fetchone()
    out["T3_C2"] = {"predicate": cond[0], "role": cond[1], "condition_op": cond[2]["op"],
                    "members": [(a["x"]["latex"], a["set"]["latex"]) for a in cond[2]["args"]],
                    "ok": cond[2]["op"] == "and" and [a["set"]["latex"] for a in cond[2]["args"]] == ["\\R", "\\R \\setminus \\{0\\}"]}
    t4 = c.execute("SELECT count(*) FROM kb.claim c JOIN kb.claim_support s ON s.claim_id = c.id WHERE c.run_id = %s AND s.observation_id = %s",
                   (run1, u["T4"]["observation"])).fetchone()[0]
    fams = [r[0] for r in c.execute("SELECT DISTINCT e.label FROM kb.claim c JOIN kb.claim_support s ON s.claim_id = c.id "
                                    "JOIN kb.entity e ON e.id IN (c.subject_id, c.object_entity_id) WHERE c.run_id = %s AND s.observation_id = %s "
                                    "AND e.type = 'DistributionFamily' ORDER BY 1", (run1, u["T4"]["observation"]))]
    out["T4"] = {"claims": t4, "ok": t4 == 17, "families": fams}
    # context-premise evidence: U12's premise cites c1, outside the unit; the D3 §9 evidence query returns it
    prem = u["U12"]["claims"]["c_X_stdgamma"]
    ev_sql = [b for b in (CODE / "s6_queries_d3.sql").read_text().split("-- D3 lines ")[1:] if "FROM kb.claim_evidence ce" in b][0].split("\n", 1)[1]
    ev_sql = ev_sql.replace(":claim_id", "%(claim_id)s")
    rows = c.execute(ev_sql, {"claim_id": prem}).fetchall()
    lo = SAMPLE["units"]["U12"]["parts"][0]["start"]
    out["context_evidence"] = {"claim": "U12 c_X_stdgamma", "rows": [list(r) for r in rows], "unit_start": lo,
                               "ok": bool(rows) and all(r[3] <= lo for r in rows)}
    # golden run
    order = meta["_gold_order"]
    bad = []
    for unit in CORE:
        ts = {p: (t, cr) for uu, p, t, cr in order if uu == unit}
        if not (ts["c"][0] > max(ts["a"][0], ts["b"][0]) and ts["c"][1] > max(ts["a"][1], ts["b"][1])):
            bad.append(unit)
    out["golden"] = {
        "passes": dict(c.execute("SELECT pass, count(*) FROM eval.golden_pass GROUP BY 1 ORDER BY 1").fetchall()),
        "models": dict(c.execute("SELECT pass, min(model) FROM eval.golden_pass GROUP BY 1 ORDER BY 1").fetchall()),
        "tasks": c.execute("SELECT count(*) FROM ops.task WHERE run_id = %s AND unit_type = 'golden_unit'", (meta["golden"]["golden_run"],)).fetchone()[0],
        "items": meta["golden"]["items"], "context_items": meta["golden"]["context_items"],
        "context_item_refs": [list(r) for r in c.execute("SELECT gu.current_locator, gi.item_type, gi.local_ref FROM eval.golden_item gi "
                                                         "JOIN eval.golden_pass gp ON gp.id = gi.golden_pass_id JOIN eval.golden_unit gu ON gu.id = gp.golden_unit_id "
                                                         "WHERE gi.context ORDER BY 1, 2, 3")],
        "pass_c_after_a_and_b": not bad, "units_out_of_order": bad,
        "splits": [list(r) for r in c.execute("SELECT d.source_uri, s.split, s.reason FROM eval.document_split s JOIN kb.document d ON d.id = s.document_id ORDER BY 2, 1")],
    }
    # run_observation with reuse and the fate cut
    ro = {r[0]: r[1] for r in c.execute("SELECT run_id, array_agg(id ORDER BY id) FROM kb.run_observation WHERE run_id IN (%s, %s) GROUP BY 1", (run1, run2))}
    rr = c.execute("SELECT count(*) FROM kb.run_rendition WHERE run_id = %s", (run2,)).fetchone()[0]
    out["run_observation"] = {
        "run2_observations": ro.get(run2, []), "t3_observation_via_reuse": u["T3"]["observation"] in ro.get(run2, []),
        "late_observation_excluded": meta["late_observation"] not in ro.get(run2, []),
        "run1_observations": len(ro.get(run1, [])), "run2_renditions": rr,
        "ok": u["T3"]["observation"] in ro.get(run2, []) and meta["late_observation"] not in ro.get(run2, []) and len(ro.get(run2, [])) == 1 and rr == 4,
    }
    return out


# ---- constraint sweep ------------------------------------------------------------------------

IN_OVERRIDES = {  # simple IN checks whose column another CHECK also reads: (sample WHERE, extra mutation)
    "entity_scope_check": ("scope = 'global'", {}),
    "segment_parse_status_check": (None, {"parse_reason": "x"}),
}

HAND = [  # (definition substring, mutation, sample WHERE)
    ("(grp = 'derive'::text) = (severity IS NULL)", {"severity": None}, "grp <> 'derive'"),
    ("(grp = 'derive'::text) = (check_expr IS NULL)", {"check_expr": None}, "grp <> 'derive'"),
    ("(parse_status = 'ok'::text) = (parse_reason IS NULL)", {"parse_reason": "x"}, "parse_status = 'ok'"),
    ("start_offset <= end_offset", "start_after_end", None),
    ("start_offset < end_offset", "empty_span", None),
    ("(scope = 'local'::text) = (scope_segment_id IS NOT NULL)", {"scope_segment_id": None}, "scope = 'local' AND type <> 'Statement'"),
    ("(type = 'Statement'::text) = (kind IS NOT NULL)", {"kind": None}, "type = 'Statement'"),
    ("(object_entity_id IS NULL) <> (object_value IS NULL)", {"object_value": {"t": "formula", "latex": "x", "symbols": {}}}, "object_entity_id IS NOT NULL"),
]


def fixtures(c, L: Loader):
    """Rows for tables S6-B leaves empty, inside the sweep transaction."""
    sv, run1 = L.ids["schema"], L.ids["run1"]
    c.execute("INSERT INTO meta.compiled_artifact (schema_version_id, compiler, compiler_version, kind, hash, body) VALUES (%s, 'json_schema', '0', 'batch.stored', 'h', '{}')", (sv,))
    c.execute("INSERT INTO meta.schema_class (schema_version_id, name, kind, scope) VALUES (%s, 'DistributionFamily', 'entity', 'global')", (sv,))
    c.execute("INSERT INTO meta.schema_slot (schema_version_id, name, role) VALUES (%s, 'stat:has_distribution', 'predicate')", (sv,))
    c.execute("INSERT INTO meta.schema_enum (schema_version_id, name, values) VALUES (%s, 'ParameterRole', '[]')", (sv,))
    c.execute("INSERT INTO meta.schema_rule (schema_version_id, rule_id, grp, applies_to, severity, when_expr, check_expr) VALUES (%s, 'r1', 'rules', '{stat:has_distribution}', 'warning', 'true', 'true')", (sv,))
    cfg = L.ids["cfg:extract.gliner_schema/default"]
    ent = L.one("SELECT id FROM kb.entity WHERE run_id = %s LIMIT 1", (run1,))
    c.execute("INSERT INTO kb.embedding (target_type, target_id, model_config_id, vec) VALUES ('entity', %s, %s, %s::halfvec)", (ent, cfg, "[" + ",".join(["0.03125"] * 1024) + "]"))
    t = L.one("SELECT id FROM ops.task WHERE run_id = %s LIMIT 1", (run1,))
    c.execute("INSERT INTO ops.measurement (run_id, task_id, iteration, scope_type, scope_key, metric, value) VALUES (%s, %s, 0, 'rule', 'r1', 'rules.evaluated', 3)", (run1, t))
    c.execute("INSERT INTO meta.schema_version (project_id, domain, label, content_hash, parent_id, source, created_by) "
              "SELECT project_id, domain, '0.1.1', content_hash || '-child', id, source, created_by FROM meta.schema_version WHERE id = %s", (sv,))
    c.execute("INSERT INTO meta.guideline_version (project_id, domain, label, content_hash, body, schema_version_id, parent_id, created_by) "
              "SELECT project_id, domain, 'v1.1', content_hash || '-child', body, schema_version_id, id, created_by FROM meta.guideline_version WHERE id = %s", (L.ids["guideline"],))
    c.execute("INSERT INTO ops.experiment (project_id, hypothesis, target_metric, baseline_run_id, candidate_run_id, candidate_change, decision) VALUES (%s, 'h', 'f1', %s, %s, '{}', 'reject')",
              (L.ids["project"], run1, L.ids["run2"]))


def catalog(c):
    cols = {}
    for s, t, a, typ, nn, ident, gen in c.execute(
            "SELECT n.nspname, cl.relname, at.attname, format_type(at.atttypid, at.atttypmod), at.attnotnull, at.attidentity, at.attgenerated "
            "FROM pg_attribute at JOIN pg_class cl ON cl.oid = at.attrelid JOIN pg_namespace n ON n.oid = cl.relnamespace "
            "WHERE n.nspname = ANY(%s) AND cl.relkind = 'r' AND at.attnum > 0 AND NOT at.attisdropped ORDER BY 1, 2, at.attnum", (list(SCHEMAS),)):
        cols.setdefault(f"{s}.{t}", []).append({"name": a, "type": typ, "notnull": nn, "identity": bool(ident), "generated": bool(gen)})
    cons = []
    for s, t, name, ct, cols_, d in c.execute(
            "SELECT n.nspname, cl.relname, co.conname, co.contype, "
            "ARRAY(SELECT attname FROM unnest(co.conkey) k JOIN pg_attribute a ON a.attrelid = co.conrelid AND a.attnum = k), pg_get_constraintdef(co.oid) "
            "FROM pg_constraint co JOIN pg_class cl ON cl.oid = co.conrelid JOIN pg_namespace n ON n.oid = cl.relnamespace "
            "WHERE n.nspname = ANY(%s) AND co.contype IN ('c','f','u','p','n') ORDER BY 1, 2, 3", (list(SCHEMAS),)):
        cons.append({"table": f"{s}.{t}", "name": name, "type": ct, "cols": list(cols_), "def": d})
    return cols, cons


class Sweep:
    def __init__(self, c, cols, cons):
        self.c, self.cols, self.cons, self.rows = c, cols, cons, []
        self.uniques = {}
        self.checked_cols = {}
        for k in cons:
            if k["type"] in ("u", "p"):
                self.uniques.setdefault(k["table"], []).append(k)
            if k["type"] == "c":
                self.checked_cols.setdefault(k["table"], set()).update(k["cols"])
        self.fk_cols = {(k["table"], col) for k in cons if k["type"] == "f" for col in k["cols"]}

    def sample(self, table, where=None):
        r = self.c.execute(f"SELECT to_jsonb(t), t.ctid::text FROM {table} t {'WHERE ' + where if where else ''} ORDER BY 1 LIMIT 1").fetchone()
        self.last_ctid = r[1] if r else None
        return dict(r[0]) if r else None

    def make_unique(self, table, row, keep: set):
        """Change one column of every unique constraint not involving `keep`, so a duplicate is unique."""
        for u in self.uniques.get(table, []):
            if set(u["cols"]) & keep:
                continue
            colinfo = {c["name"]: c for c in self.cols[table]}
            if any(colinfo[x]["identity"] for x in u["cols"]):
                continue
            text = [x for x in u["cols"] if colinfo[x]["type"] == "text" and x not in self.checked_cols.get(table, set())]
            ints = [x for x in u["cols"] if colinfo[x]["type"] in ("integer", "bigint") and (table, x) not in self.fk_cols]
            if text:
                row[text[0]] = f"{row[text[0]]}-sweep"
            elif ints:
                row[ints[-1]] = row[ints[-1]] + 1_000_000
            else:
                return False
        return True

    def insert(self, table, row, delete_ctid=None):
        names = [c["name"] for c in self.cols[table] if not c["identity"] and not c["generated"]]
        cl = ", ".join(names)
        try:
            with self.c.transaction(force_rollback=True):
                if delete_ctid:
                    self.c.execute(f"DELETE FROM {table} WHERE ctid = %s::tid", (delete_ctid,))
                self.c.execute(f"INSERT INTO {table} ({cl}) SELECT {cl} FROM jsonb_populate_record(NULL::{table}, %s)", (Jsonb(row),))
            return ("no error", "")
        except psycopg.Error as e:
            return (e.sqlstate, e.diag.constraint_name or e.diag.column_name or e.diag.message_primary)

    def case(self, table, constraint, bad, expected_state, expected_name, row, delete_ctid=None):
        if row is None:
            self.rows.append([table, constraint, bad, f"{expected_state} {expected_name}", "no sample row", "not_run"])
            return
        st, name = self.insert(table, row, delete_ctid)
        ok = st == expected_state and (expected_name in ("", None) or name == expected_name)
        self.rows.append([table, constraint, bad, f"{expected_state} {expected_name}".strip(), f"{st} {name}".strip(), "passed" if ok else "failed"])

    def run_all(self):
        for k in self.cons:
            t = k["table"]
            if k["type"] == "n":
                col = k["cols"][0]
                if next(c for c in self.cols[t] if c["name"] == col)["identity"]:
                    continue
                row = self.sample(t)
                if row is not None:
                    row[col] = None
                self.case(t, k["name"], f"{col} = NULL", "23502", col, row)
            elif k["type"] == "c":
                m = re.fullmatch(r"CHECK \(\((\w+) = ANY \(ARRAY\[.*\]\)\)\)", k["def"])
                if m:
                    where, extra = IN_OVERRIDES.get(k["name"], (None, {}))
                    row = self.sample(t, where)
                    if row is not None:
                        row[m.group(1)] = "__bad__"
                        row.update(extra)
                    self.case(t, k["name"], f"{m.group(1)} = '__bad__'", "23514", k["name"], row)
                    continue
                hand = next((h for h in HAND if h[0] in k["def"]), None)
                if hand is None:
                    self.rows.append([t, k["name"], k["def"], "", "no mutation defined", "not_run"])
                    continue
                row = self.sample(t, hand[2])
                if row is not None:
                    if hand[1] == "start_after_end":
                        row["start_offset"] = row["end_offset"] + 1
                        desc = "start_offset = end_offset + 1"
                    elif hand[1] == "empty_span":
                        row["start_offset"] = row["end_offset"]
                        desc = "start_offset = end_offset"
                    else:
                        row.update(hand[1])
                        desc = ", ".join(f"{a} = {json.dumps(b)}" for a, b in hand[1].items())
                    self.make_unique(t, row, set(k["cols"]))
                else:
                    desc = str(hand[1])
                self.case(t, k["name"], desc, "23514", k["name"], row)
            elif k["type"] == "f":
                row = self.sample(t, f"{k['cols'][0]} IS NOT NULL")
                ctid = None
                if row is not None:
                    row[k["cols"][0]] = 2_000_000_000
                    if not self.make_unique(t, row, set(k["cols"])):
                        ctid = self.last_ctid
                self.case(t, k["name"], f"{k['cols'][0]} = 2000000000 (no such row)", "23503", k["name"], row, ctid)
            elif k["type"] in ("u", "p"):
                colinfo = {c["name"]: c for c in self.cols[t]}
                if any(colinfo[x]["identity"] for x in k["cols"]):
                    continue   # identity keys regenerate; uniqueness by construction
                row = self.sample(t)
                if row is not None:
                    for u in self.uniques.get(t, []):
                        if u["name"] != k["name"] and not set(u["cols"]) <= set(k["cols"]):
                            self.make_unique_one(t, row, u, set(k["cols"]))
                self.case(t, k["name"], f"duplicate of an existing ({', '.join(k['cols'])})", "23505", k["name"], row)

    def make_unique_one(self, table, row, u, keep):
        colinfo = {c["name"]: c for c in self.cols[table]}
        if any(colinfo[x]["identity"] for x in u["cols"]):
            return
        text = [x for x in u["cols"] if x not in keep and colinfo[x]["type"] == "text" and x not in self.checked_cols.get(table, set())]
        if text:
            row[text[0]] = f"{row[text[0]]}-sweep"


def named_cases(c, sw: Sweep, L: Loader):
    """The brief's bad rows first, then invariants the database does not express (expected: no error)."""
    rows = []
    r = sw.sample("kb.claim", "object_entity_id IS NOT NULL")
    r["object_value"] = {"t": "formula", "latex": "x", "symbols": {}}
    r["key"] += "-both"
    st, name = sw.insert("kb.claim", r)
    rows.append(["kb.claim", "brief: object both entity and value", "object_entity_id and object_value both set", "23514 claim_check", f"{st} {name}", "passed" if st == "23514" else "failed"])
    r = sw.sample("kb.entity", "scope = 'local' AND type <> 'Statement'")
    r["scope_segment_id"] = None
    r["key"] += "-noscope"
    st, name = sw.insert("kb.entity", r)
    rows.append(["kb.entity", "brief: local entity without scope segment", "scope = 'local', scope_segment_id = NULL", "23514 entity_check", f"{st} {name}", "passed" if st == "23514" else "failed"])
    r = sw.sample("eval.golden_pass")
    r["model"] = None
    st, name = sw.insert("eval.golden_pass", r)
    rows.append(["eval.golden_pass", "brief: golden pass without a model", "model = NULL", "23502 model", f"{st} {name}", "passed" if st == "23502" and name == "model" else "failed"])
    # invariants the database does not express: expected to insert; the repository layer checks them
    r = sw.sample("kb.span")
    ln = L.one("SELECT length(canonical_text) FROM kb.rendition WHERE id = %s", (r["rendition_id"],))
    r["start_offset"], r["end_offset"] = ln + 10, ln + 20
    st, name = sw.insert("kb.span", r)
    rows.append(["kb.span", "INV-10 (repository): span outside its rendition's text", f"offsets {ln + 10}-{ln + 20} beyond length {ln}", "no error (repository check)", f"{st} {name}".strip(), "passed" if st == "no error" else "failed"])
    r = sw.sample("kb.span")
    r["text"] = "not the canonical substring"
    r["end_offset"] += 1_000_000
    st, name = sw.insert("kb.span", r)
    rows.append(["kb.span", "repository: span text equals canonical_text[start:end]", "text differs from the rendition substring", "no error (repository check)", f"{st} {name}".strip(), "passed" if st == "no error" else "failed"])
    other = L.one("SELECT s.id FROM kb.span s WHERE s.rendition_id <> (SELECT sp.rendition_id FROM kb.claim_evidence ce JOIN kb.span sp ON sp.id = ce.span_id ORDER BY ce.claim_id LIMIT 1) LIMIT 1")
    r = sw.sample("kb.claim_evidence")
    r["span_id"] = other
    st, name = sw.insert("kb.claim_evidence", r)
    rows.append(["kb.claim_evidence", "repository: evidence span on the claim's run rendition", "span of another page's rendition", "no error (repository check)", f"{st} {name}".strip(), "passed" if st == "no error" else "failed"])
    a = sw.sample("eval.golden_pass", "pass = 'a'")
    try:
        with c.transaction():
            n = c.execute("UPDATE eval.golden_pass SET session_ref = %s WHERE golden_unit_id = %s AND pass = 'b'", (a["session_ref"], a["golden_unit_id"])).rowcount
        st = "no error" if n == 1 else f"updated {n}"
    except psycopg.Error as e:
        st = e.sqlstate
    rows.append(["eval.golden_pass", "repository: passes a and b of a unit have different sessions", "pass b session_ref = pass a's", "no error (repository check)", st, "passed" if st == "no error" else "failed"])
    r = sw.sample("eval.golden_item")
    r["golden_pass_id"] = L.one("SELECT id FROM eval.golden_pass WHERE pass = 'a' LIMIT 1")
    st, name = sw.insert("eval.golden_item", r)
    rows.append(["eval.golden_item", "repository: items project a pass c only", "item on a pass a row", "no error (repository check)", f"{st} {name}".strip(), "passed" if st == "no error" else "failed"])
    r = sw.sample("kb.segment")
    r["text"] = "drifted"
    r["key"] += "-drift"
    st, name = sw.insert("kb.segment", r)
    rows.append(["kb.segment", "repository: segment text equals canonical_text[start:end]", "text differs from the rendition substring", "no error (repository check)", f"{st} {name}".strip(), "passed" if st == "no error" else "failed"])
    return rows


def sweep(c, L: Loader) -> dict:
    cols, cons = catalog(c)
    with c.transaction(force_rollback=True):
        fixtures(c, L)
        sw = Sweep(c, cols, cons)
        named = named_cases(c, sw, L)
        sw.run_all()
    rows = named + sw.rows
    with (RESULTS / "constraints.tsv").open("w") as f:
        f.write("table\tconstraint\tbad_row\texpected\tobserved\toutcome\n")
        for r in rows:
            f.write("\t".join(str(x).replace("\t", " ").replace("\n", " ") for x in r) + "\n")
    by = {}
    for r in rows:
        by[r[5]] = by.get(r[5], 0) + 1
    return {"cases": len(rows), "by_outcome": by, "constraints_in_catalog": {t: sum(1 for k in cons if k["type"] == t) for t in "cfunp"},
            "failed": [r for r in rows if r[5] != "passed"]}


# ---- run deletion ------------------------------------------------------------------------------

DELETES = [
    ("eval.result", "DELETE FROM eval.result WHERE run_id = %(run)s"),
    ("eval.alignment", "DELETE FROM eval.alignment WHERE run_id = %(run)s"),
    ("kb.claim_link", "DELETE FROM kb.claim_link WHERE run_id = %(run)s"),
    ("kb.claim", "DELETE FROM kb.claim WHERE run_id = %(run)s"),
    ("kb.entity", "DELETE FROM kb.entity WHERE run_id = %(run)s"),
]
RI = [  # the referential checks the cascades and NO ACTION keys run per deleted row (as PostgreSQL's RI triggers query)
    ("kb.claim_evidence (claim_id)", "SELECT 1 FROM ONLY kb.claim_evidence x WHERE claim_id = $1"),
    ("kb.claim_support (claim_id)", "SELECT 1 FROM ONLY kb.claim_support x WHERE claim_id = $1"),
    ("kb.claim_link (from_claim_id)", "SELECT 1 FROM ONLY kb.claim_link x WHERE from_claim_id = $1"),
    ("kb.claim_link (to_claim_id)", "SELECT 1 FROM ONLY kb.claim_link x WHERE to_claim_id = $1"),
    ("kb.claim (subject_id)", "SELECT 1 FROM ONLY kb.claim x WHERE subject_id = $1"),
    ("kb.claim (object_entity_id)", "SELECT 1 FROM ONLY kb.claim x WHERE object_entity_id = $1"),
    ("kb.claim (statement_id)", "SELECT 1 FROM ONLY kb.claim x WHERE statement_id = $1"),
    ("kb.entity_alias (entity_id)", "SELECT 1 FROM ONLY kb.entity_alias x WHERE entity_id = $1"),
    ("kb.entity_anchor (entity_id)", "SELECT 1 FROM ONLY kb.entity_anchor x WHERE entity_id = $1"),
    ("kb.entity_mention (entity_id)", "SELECT 1 FROM ONLY kb.entity_mention x WHERE entity_id = $1"),
    ("eval.alignment (golden_item_id)", "SELECT 1 FROM ONLY eval.alignment x WHERE golden_item_id = $1"),
]


def plan_lines(c, sql, params=None, analyze=False, seqscan=True) -> list[str]:
    with c.transaction(force_rollback=not analyze):
        if not seqscan:
            c.execute("SET LOCAL enable_seqscan = off")
        rows = c.execute(f"EXPLAIN ({'ANALYZE, ' if analyze else ''}COSTS off{', TIMING off, SUMMARY off' if analyze else ''}) {sql}", params).fetchall()
    return [r[0] for r in rows]


def generic_plan(c, sql, seqscan=True) -> list[str]:
    with c.transaction(force_rollback=True):
        if not seqscan:
            c.execute("SET LOCAL enable_seqscan = off")
        return [r[0] for r in c.execute(f"EXPLAIN (GENERIC_PLAN, COSTS off) {sql}").fetchall()]


def run_deletion(c, run: int, keep_run: int, label: str) -> tuple[dict, list[str]]:
    def counts(r):
        return {t: c.execute(f"SELECT count(*) FROM {t} WHERE run_id = %s", (r,)).fetchone()[0]
                for t in ("kb.entity", "kb.claim", "kb.claim_link", "eval.alignment", "eval.result", "ops.task", "ops.measurement")} | {
            "ops.run": c.execute("SELECT count(*) FROM ops.run WHERE id = %s", (r,)).fetchone()[0],
            "kb.claim_evidence": c.execute("SELECT count(*) FROM kb.claim_evidence ce JOIN kb.claim cl ON cl.id = ce.claim_id WHERE cl.run_id = %s", (r,)).fetchone()[0],
            "kb.entity_alias": c.execute("SELECT count(*) FROM kb.entity_alias a JOIN kb.entity e ON e.id = a.entity_id WHERE e.run_id = %s", (r,)).fetchone()[0]}
    before, keep_before = counts(run), counts(keep_run)
    md = [f"### {label}", "", f"Run {run} deleted; run {keep_run} kept. Plans are `EXPLAIN (COSTS off)`; "
          "\"index usable\" plans are taken with `SET LOCAL enable_seqscan = off`.", ""]
    for t, sql in DELETES:
        md += [f"**{t}** — `{sql % {'run': run}}`", "", "chosen plan:", "```", *plan_lines(c, sql, {"run": run}), "```",
               "index usable:", "```", *plan_lines(c, sql, {"run": run}, seqscan=False), "```", ""]
    md += ["**Referential checks** run per deleted row (generic plans, as the RI triggers prepare them):", ""]
    for name, sql in RI:
        p = generic_plan(c, sql, seqscan=False)
        md += [f"- {name}: `{' / '.join(x.strip() for x in p)}`"]
    md.append("")
    t0 = time.perf_counter()
    with c.transaction():
        trig = []
        for t, sql in DELETES:
            rows = c.execute(f"EXPLAIN (ANALYZE, COSTS off, TIMING on, SUMMARY on) {sql}", {"run": run}).fetchall()
            trig += [f"{t}: " + r[0].strip() for r in rows if r[0].lstrip().startswith(("Trigger", "Execution Time", "Delete on"))]
    ms = (time.perf_counter() - t0) * 1000
    after, keep_after = counts(run), counts(keep_run)
    md += ["Executed (`EXPLAIN ANALYZE`, one transaction), trigger and execution lines:", "```", *trig, "```", ""]
    res = {"before": before, "after": after, "kept_run_before": keep_before, "kept_run_after": keep_after, "ms": round(ms, 1),
           "ok": after["ops.run"] == 1 and after["ops.task"] == before["ops.task"] and all(after[t] == 0 for t in ("kb.entity", "kb.claim", "kb.claim_link", "eval.alignment", "eval.result", "kb.claim_evidence", "kb.entity_alias"))
           and keep_after == keep_before}
    md += ["| rows | before | after |", "|---|---|---|"] + [f"| {k} | {before[k]} | {after[k]} |" for k in before] + [
        "", f"Kept run {keep_run} unchanged: {keep_after == keep_before}. Outcome: {'passed' if res['ok'] else 'failed'}.", ""]
    return res, md


def main() -> int:
    t0 = time.perf_counter()
    recreate_db()
    a = apply(CODE / "s6_ddl_applied.sql")
    assert not a["errors"], a["errors"]
    with app() as c:
        L, meta = load(c)
        c.commit()
        out = {"load_ms": round((time.perf_counter() - t0) * 1000, 1), **{k: v for k, v in meta.items() if not k.startswith("_")}}
        out["checks"] = checks(c, L, meta)
        c.commit()
        out["constraints"] = sweep(c, L)
        c.commit()
        res, md = run_deletion(c, meta["run2"], L.ids["run1"], f"Run {meta['run2']}: the second slice run (T2 and T3 materialized, S6-B)")
        c.commit()
        out["run_deletion"] = res
        (RESULTS / "run_deletion.md").write_text("# S6 run deletion (D3 §8)\n\n" + "\n".join(md))
        c.execute("ANALYZE")
        c.commit()
    write_json(RESULTS / "rows.json", out)
    ch = out["checks"]
    print("T3_C2", ch["T3_C2"]["ok"], "T4", ch["T4"], "context", ch["context_evidence"]["ok"], "golden order", ch["golden"]["pass_c_after_a_and_b"],
          "run_obs", ch["run_observation"]["ok"], "deletion", res["ok"])
    print("constraints", out["constraints"]["by_outcome"])
    for r in out["constraints"]["failed"]:
        print("  ", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
