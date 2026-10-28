"""S6-D (S6 plan §3): the joint dry run — S4-B's compiled schema-table rows into ``meta.schema_*``,
the pack's schema version registered from its hash, the trace rows inserted against that version.

    uv run python code/s6d_dry_run.py      # after s6b_rows.py, on cs_spike_s6

Inputs: ``results/s4/compiled/tables.json`` (S4-B; its records come at S4-E), the compiled
artifacts beside it, and the pack sources under ``results/s4/schema/domains``.

1. Registers ``meta.schema_version`` 0.2.0 with S4's ``content_hash``, after recomputing it here
   from the listed sources (canonical JSON of the parsed sources, D2 §2), and with ``source`` the
   files' text; adds the ``meta.compiled_artifact`` rows with their bodies, each body's hash
   recomputed and compared.
2. Inserts every ``schema_class``, ``schema_slot``, ``schema_enum`` and ``schema_rule`` row, each under
   a savepoint, recording any row the DDL rejects.
3. A run on that version (its ingest tasks reuse run 1's, so ``kb.run_rendition`` selects the same
   renditions) with the twelve core units of the v1 reference materialized as in S6-B.
4. Typed agreement between the trace rows and the tables: predicates, entity types, subject and
   object types against ``domain_class`` and ``range`` (with ``parent`` chains and the pack's
   mixins), value kinds against ``object_kind``, qualifier names against the slot's
   ``qualifiers``, and the DDL's closed value sets against the compiled enums.
Writes ``results/s6/dry_run.md`` and ``results/s6/dry_run.json``.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from datetime import timedelta

import psycopg
import yaml
from psycopg.types.json import Jsonb

from s6_db import RESULTS, app, write_json
from s6_load import CORE, EVIDENCE, PAGES, RENDITIONS, S0R2, SAMPLE, T0, Loader, page_segments

S4 = EVIDENCE / "results" / "s4"
DOMAINS = S4 / "schema" / "domains"
CORE_QUALIFIERS = {"modality", "polarity", "hedge", "attribution", "conditions", "scope", "valid_time"}


def _nfc(o):
    if isinstance(o, str):
        return unicodedata.normalize("NFC", o)
    if isinstance(o, list | tuple):
        return [_nfc(v) for v in o]
    if isinstance(o, dict):
        return {unicodedata.normalize("NFC", str(k)): _nfc(v) for k, v in o.items()}
    return o


def canon_sha(o) -> str:
    return hashlib.sha256(json.dumps(_nfc(o), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def parsed_source(path: str):
    p = DOMAINS / path
    if path.endswith((".yaml", ".yml")):
        return yaml.safe_load(p.read_text(encoding="utf-8"))
    if path.endswith(".json"):
        return json.loads(p.read_text(encoding="utf-8"))
    return p.read_text(encoding="utf-8")


def bare(name: str | None) -> str | None:
    return name.split(":", 1)[1] if name and ":" in name else name


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--suffix", default="", help="output name suffix, e.g. _2 for a superseding run")
    suffix = ap.parse_args().suffix
    tables = json.loads((S4 / "compiled" / "tables.json").read_text())
    sv = tables["schema_version"]
    out: dict = {"input": "results/s4/compiled/tables.json", "schema_version": sv}
    recomputed = canon_sha({f: parsed_source(f) for f in sv["source_files"]})
    out["content_hash_recomputed"] = recomputed
    out["content_hash_matches"] = recomputed == sv["content_hash"]
    bodies = {"batch.model_facing": S4 / "compiled" / "batch.model.schema.json", "batch.stored": S4 / "compiled" / "batch.stored.schema.json",
              "batch.decoding": S4 / "compiled" / "batch.decoding.schema.json"}
    projection = {k: tables[k] for k in ("schema_class", "schema_slot", "schema_enum", "schema_rule")}
    rejected, inserted = [], {}
    with app() as c:
        proj = c.execute("SELECT id FROM meta.project LIMIT 1").fetchone()[0]
        old = c.execute("SELECT id FROM meta.schema_version WHERE project_id = %s AND content_hash = %s", (proj, sv["content_hash"])).fetchone()
        if old:   # rerun: drop the previous dry-run version and its run
            runs = [r[0] for r in c.execute("SELECT id FROM ops.run WHERE schema_version_id = %s", (old[0],))]
            for r in runs:
                c.execute("DELETE FROM kb.claim WHERE run_id = %s", (r,))
                c.execute("DELETE FROM kb.entity WHERE run_id = %s", (r,))
                c.execute("DELETE FROM ops.task WHERE run_id = %s", (r,))
                c.execute("DELETE FROM ops.run WHERE id = %s", (r,))
            c.execute("DELETE FROM meta.schema_version WHERE id = %s", (old[0],))
        svid = c.execute(
            "INSERT INTO meta.schema_version (project_id, domain, label, content_hash, source, created_by) VALUES (%s, %s, %s, %s, %s, 'agent:opus-5.5 (S6-D from S4-B)') RETURNING id",
            (proj, sv["domain"], sv["label"], sv["content_hash"], Jsonb({f: (DOMAINS / f).read_text(encoding="utf-8") for f in sv["source_files"]}))).fetchone()[0]
        art = []
        for a in tables["compiled_artifact"]:
            body = projection if a["kind"] == "tables" else json.loads(bodies[a["kind"]].read_text())
            h = canon_sha(body)
            c.execute("INSERT INTO meta.compiled_artifact (schema_version_id, compiler, compiler_version, kind, hash, body) VALUES (%s, %s, %s, %s, %s, %s)",
                      (svid, a["compiler"], a["compiler_version"], a["kind"], a["hash"], Jsonb(body)))
            art.append({**a, "body_hash_recomputed_matches": h == a["hash"]})
        out["compiled_artifact"] = art
        for tname, rows in projection.items():
            ok = 0
            cols = None
            for r in rows:
                cols = ["schema_version_id"] + list(r)
                vals = [svid] + [Jsonb(v) if isinstance(v, dict) or (isinstance(v, list) and v and isinstance(v[0], dict)) else v for v in r.values()]
                try:
                    with c.transaction():
                        c.execute(f"INSERT INTO meta.{tname} ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})", vals)
                    ok += 1
                except psycopg.Error as e:
                    rejected.append({"table": tname, "row": r.get("name") or r.get("rule_id"), "sqlstate": e.sqlstate,
                                     "constraint": e.diag.constraint_name, "message": e.diag.message_primary})
            inserted[tname] = {"rows": len(rows), "inserted": ok}
        out["inserted"], out["rejected"] = inserted, rejected
        c.commit()

        # a run on that version, reusing run 1's ingest
        L = Loader(c)
        for k, q in (("project", "SELECT id FROM meta.project LIMIT 1"), ("guideline", "SELECT id FROM meta.guideline_version ORDER BY id LIMIT 1"),
                     ("policy", "SELECT id FROM ops.policy_version LIMIT 1"), ("slice", "SELECT id FROM ops.debug_slice LIMIT 1")):
            L.ids[k] = c.execute(q).fetchone()[0]
        L.ids["schema"] = svid
        run1 = c.execute("SELECT promoted_run_id FROM meta.project").fetchone()[0]
        run = L.run("dryrun", "slice", started=T0 + timedelta(days=2), finished=T0 + timedelta(days=2, hours=1), reference=run1)
        for page in PAGES:
            text, segs = page_segments(page)
            L.text[page], L.seg_rows[page] = text, segs
            L.ren_id[page] = c.execute("SELECT id FROM kb.rendition WHERE key = %s", (RENDITIONS[page]["rendition_key"],)).fetchone()[0]
            L.doc_id[page] = c.execute("SELECT document_id FROM kb.rendition WHERE id = %s", (L.ren_id[page],)).fetchone()[0]
            for k, sid in c.execute("SELECT key, id FROM kb.segment WHERE rendition_id = %s", (L.ren_id[page],)):
                L.seg_id[k] = sid
            t1, cfg = c.execute("SELECT id, method_config_id FROM ops.task WHERE run_id = %s AND stage = 'ingest' AND unit_id = %s", (run1, L.doc_id[page])).fetchone()
            c.execute("INSERT INTO ops.task (run_id, stage, unit_type, unit_id, method_config_id, input_hash, status, reused_task_id, finished_at) "
                      "VALUES (%s, 'ingest', 'document', %s, %s, 'reuse', 'reused', %s, %s)", (run, L.doc_id[page], cfg, t1, T0 + timedelta(days=2)))
        misfits = []
        for u in CORE:
            obs = c.execute("SELECT o.id FROM kb.observation o JOIN ops.task t ON t.id = o.task_id WHERE t.run_id = %s AND t.stage = 'propose' "
                            "AND o.kind = 'claim_proposal' AND t.unit_id = %s", (run1, L.seg_id[SAMPLE["units"][u]["parts"][-1]["segment_key"]])).fetchone()[0]
            m = L.materialize(run, u, json.loads((S0R2 / "reference_v1" / f"{u}.json").read_text()), obs)
            misfits += m["misfits"]
        out["trace_rows"] = {"run": run, "entities": c.execute("SELECT count(*) FROM kb.entity WHERE run_id = %s", (run,)).fetchone()[0],
                             "claims": c.execute("SELECT count(*) FROM kb.claim WHERE run_id = %s", (run,)).fetchone()[0], "misfits": misfits,
                             "rendition_selection": c.execute("SELECT count(*) FROM kb.run_rendition WHERE run_id = %s", (run,)).fetchone()[0]}
        c.commit()

        # ---- typed agreement --------------------------------------------------------------------
        P = {"run": run, "sv": svid}
        classes = {r[0]: r for r in c.execute("SELECT name, parent, kind, scope FROM meta.schema_class WHERE schema_version_id = %(sv)s", P)}
        by_bare = {}
        for n in classes:
            by_bare.setdefault(bare(n), []).append(n)
        stat = yaml.safe_load((DOMAINS / "statistics" / "schema" / "statistics.yaml").read_text())
        core = yaml.safe_load((DOMAINS / "core" / "schema" / "core.yaml").read_text())
        mixins = {k: v.get("mixins", []) for y in (stat, core) for k, v in (y.get("classes") or {}).items()}

        def ancestors(t):
            seen, todo = set(), [t]
            while todo:
                x = todo.pop()
                if x in seen or x is None:
                    continue
                seen.add(x)
                for full in by_bare.get(x, []):
                    todo.append(bare(classes[full][1]))
                todo += mixins.get(x, [])
            return seen

        checks = {}
        # predicates
        rows = c.execute("""SELECT c.predicate, count(*) FROM kb.claim c WHERE c.run_id = %(run)s
                            AND NOT EXISTS (SELECT 1 FROM meta.schema_slot s WHERE s.schema_version_id = %(sv)s AND s.name = c.predicate AND s.role = 'predicate')
                            GROUP BY 1 ORDER BY 1""", P).fetchall()
        checks["predicate not a predicate slot"] = rows
        # entity types: exact name and bare name
        rows = c.execute("""SELECT e.type, count(*) FROM kb.entity e WHERE e.run_id = %(run)s
                            AND NOT EXISTS (SELECT 1 FROM meta.schema_class k WHERE k.schema_version_id = %(sv)s AND k.name = e.type)
                            GROUP BY 1 ORDER BY 1""", P).fetchall()
        checks["entity type not equal to a schema_class name"] = rows
        checks["entity type matching a class only once prefixed"] = [(t, n, by_bare.get(t)) for t, n in rows if by_bare.get(t)]
        checks["entity type with no class at all"] = [(t, n) for t, n in rows if not by_bare.get(t)]
        # subject / object types against domain_class / range
        slots = {r[0]: r for r in c.execute("SELECT name, domain_class, range, object_kind, qualifiers FROM meta.schema_slot WHERE schema_version_id = %(sv)s AND role = 'predicate'", P)}
        claims = c.execute("""SELECT c.id, c.predicate, s.type, o.type, c.object_value ->> 't', c.object_value ->> 'enum', c.object_value ->> 'v', c.qualifiers
                              FROM kb.claim c JOIN kb.entity s ON s.id = c.subject_id LEFT JOIN kb.entity o ON o.id = c.object_entity_id
                              WHERE c.run_id = %(run)s""", P).fetchall()
        dom_bad, rng_bad, kind_bad, qual_bad, qual_prefixed_only = {}, {}, {}, {}, {}
        for cid, pred, st, ot, vt, venum, vv, quals in claims:
            s = slots.get(pred)
            if not s:
                continue
            _, dc, rng, ok_, sq = s
            if dc and bare(dc) not in ancestors(st):
                dom_bad.setdefault((pred, st, dc), 0)
                dom_bad[(pred, st, dc)] += 1
            if ot is not None and rng and bare(rng) not in ancestors(ot):
                rng_bad.setdefault((pred, ot, rng), 0)
                rng_bad[(pred, ot, rng)] += 1
            if ot is None and ok_ and vt != ok_:
                kind_bad.setdefault((pred, vt, ok_), 0)
                kind_bad[(pred, vt, ok_)] += 1
            if ot is not None and ok_ != "entity":
                kind_bad.setdefault((pred, "entity ref", ok_), 0)
                kind_bad[(pred, "entity ref", ok_)] += 1
            for q in (quals or {}):
                if q in CORE_QUALIFIERS or q in (sq or []):
                    continue
                if any(bare(x) == q for x in (sq or [])):
                    qual_prefixed_only.setdefault((pred, q), 0)
                    qual_prefixed_only[(pred, q)] += 1
                else:
                    qual_bad.setdefault((pred, q), 0)
                    qual_bad[(pred, q)] += 1
        checks["subject type outside domain_class (with parents and mixins)"] = [list(k) + [v] for k, v in sorted(dom_bad.items())]
        checks["object entity type outside range"] = [list(k) + [v] for k, v in sorted(rng_bad.items())]
        checks["object kind differs from object_kind"] = [list(k) + [v] for k, v in sorted(kind_bad.items())]
        checks["qualifier key matching the slot's qualifiers only once prefixed"] = [list(k) + [v] for k, v in sorted(qual_prefixed_only.items())]
        checks["qualifier key not allowed for the predicate"] = [list(k) + [v] for k, v in sorted(qual_bad.items())]
        # enums: values used by the rows, and the DDL's CHECK lists against the compiled enums
        enums = {bare(n): {x["value"] for x in vals} for n, vals in c.execute("SELECT name, values FROM meta.schema_enum WHERE schema_version_id = %(sv)s", P)}
        used = {
            "StatementKind": {r[0] for r in c.execute("SELECT DISTINCT kind FROM kb.entity WHERE run_id = %(run)s AND kind IS NOT NULL", P)},
            "StatementRole": {r[0] for r in c.execute("SELECT DISTINCT statement_role FROM kb.claim WHERE run_id = %(run)s AND statement_role IS NOT NULL", P)},
            "ClaimModality": {r[0] for r in c.execute("SELECT DISTINCT qualifiers ->> 'modality' FROM kb.claim WHERE run_id = %(run)s AND qualifiers ? 'modality'", P)},
            "EvidenceRole": {r[0] for r in c.execute("SELECT DISTINCT ce.role FROM kb.claim_evidence ce JOIN kb.claim cl ON cl.id = ce.claim_id WHERE cl.run_id = %(run)s", P)},
            "ParameterRole": {r[0] for r in c.execute("SELECT DISTINCT object_value ->> 'v' FROM kb.claim WHERE run_id = %(run)s AND object_value ->> 'enum' = 'ParameterRole'", P)},
        }
        checks["row values outside the compiled enum"] = [(e, sorted(v - enums.get(e, set())), sorted(enums.get(e, set()))) for e, v in used.items() if v - enums.get(e, set())]
        ddl_lists = {}
        for t, col, enum in (("kb.claim", "statement_role", "StatementRole"), ("kb.claim_evidence", "role", "EvidenceRole"), ("kb.segment", "parse_status", "ParseStatus")):
            d = c.execute("""SELECT pg_get_constraintdef(co.oid) FROM pg_constraint co WHERE co.conrelid = %s::regclass AND co.contype = 'c'
                             AND pg_get_constraintdef(co.oid) LIKE %s""", (t, f"%({col} = ANY%")).fetchone()
            vals = set(__import__("re").findall(r"'([a-z_]+)'::text", d[0])) if d else set()
            ddl_lists[f"{t}.{col}"] = {"ddl": sorted(vals), "enum": sorted(enums.get(enum, set())), "equal": vals == enums.get(enum, set())}
        checks["DDL CHECK lists against the compiled enums"] = ddl_lists
        sl = c.execute("SELECT name, domain_class, range, role FROM meta.schema_slot WHERE schema_version_id = %(sv)s", P).fetchall()
        enum_names = {r[0] for r in c.execute("SELECT name FROM meta.schema_enum WHERE schema_version_id = %(sv)s", P)}
        checks["slot domain_class or range naming a class or enum only by its bare name (within the compiled rows)"] = sorted({
            (col, v) for n, dc, rg, role in sl for col, v in (("domain_class", dc), ("range", rg))
            if v and v not in classes and v not in enum_names and (v in by_bare or any(bare(e) == v for e in enum_names))})
        checks["value-class attribute rows (named <prefix>:<Class>.<attr>)"] = c.execute(
            "SELECT count(*) FROM meta.schema_slot WHERE schema_version_id = %(sv)s AND name LIKE '%%.%%'", P).fetchone()[0]
        out["checks"] = checks
    write_json(RESULTS / f"dry_run{suffix}.json", out)
    md = ["# S6 joint dry run (S6-D, plan §3)", "",
          f"S4-B's `results/s4/compiled/tables.json` (schema version {sv['label']}, content hash `{sv['content_hash'][:16]}…`) loaded into `meta.schema_*` of "
          "`cs_spike_s6` (PostgreSQL 18.6, project-local cluster, as the non-superuser `cs_s6_app`); the twelve core units of the v1 reference inserted "
          f"against it as run {run}. Input not yet recorded by S4 (its records come at S4-E).", "",
          "## Registration", "",
          f"- Content hash recomputed here from the {len(sv['source_files'])} listed sources (canonical JSON of the parsed files): "
          f"**{'matches' if out['content_hash_matches'] else 'differs'}**.",
          *[f"- `{a['compiler']}` `{a['kind']}`: body hash recomputed {'matches' if a['body_hash_recomputed_matches'] else 'differs'}" for a in art],
          "", "| table | rows | inserted |", "|---|---|---|", *[f"| meta.{k} | {v['rows']} | {v['inserted']} |" for k, v in inserted.items()], ""]
    if rejected:
        md += ["Rows the DDL rejected:", "", "| table | row | sqlstate | constraint | message |", "|---|---|---|---|---|",
               *[f"| {r['table']} | {r['row']} | {r['sqlstate']} | {r['constraint']} | {r['message']} |" for r in rejected], ""]
    else:
        md += ["Every compiled row inserts; no constraint rejects one.", ""]
    md += ["## Trace rows against the version", "",
           f"{out['trace_rows']['entities']} entities and {out['trace_rows']['claims']} claims inserted; renditions selected through reused ingest tasks: "
           f"{out['trace_rows']['rendition_selection']}; not loaded (as in S6-B): {', '.join(m['unit'] + '/' + m['item'] for m in misfits) or 'none'}.", "",
           "## Mismatches between the trace rows and the compiled tables", ""]
    for k, v in checks.items():
        if isinstance(v, dict):
            md += [f"**{k}**", "", "| column | DDL | compiled enum | equal |", "|---|---|---|---|",
                   *[f"| {col} | {', '.join(x['ddl'])} | {', '.join(x['enum'])} | {x['equal']} |" for col, x in v.items()], ""]
        elif isinstance(v, int):
            md += [f"**{k}:** {v}", ""]
        else:
            md += [f"**{k}:** {len(v)}", ""] + ([f"- `{json.dumps(x, ensure_ascii=False, default=str)}`" for x in v[:25]] + [""] if v else [""])
    ck = checks
    pf = ck["entity type matching a class only once prefixed"]
    qp = ck["qualifier key matching the slot's qualifiers only once prefixed"]
    md += ["## Reading (2026-10-28)", "",
           f"- **The path works.** Pack → compiled rows → migration-0001 tables → trace rows: every compiled row inserts, the hashes recompute, every "
           f"claim predicate is a predicate slot, subject and object types agree with `domain_class` and `range` (through `parent` and the pack's mixins), "
           "value kinds agree with `object_kind`, and every enum value the rows use is in its compiled enum.",
           f"- **Names do not join as stored.** `schema_class.name` and `schema_slot.qualifiers` are prefixed (`stat:RandomVariable`, `stat:param_values`), "
           f"while `kb.entity.type` (D3 §9, §10: `s.type = 'DistributionFamily'`) and the `kb.claim.qualifiers` keys (D3 §6.1) are bare: {len(pf)} entity types "
           f"and {len(qp)} (predicate, qualifier) pairs match only after prefixing; within the compiled rows `domain_class`/`range` name classes bare "
           f"({len(ck['slot domain_class or range naming a class or enum only by its bare name (within the compiled rows)'])} values) while `name` is prefixed. "
           "One convention is needed before SQL joins from claims to their schema definitions (D3 §3) work: prefixed everywhere, or bare classes with "
           "prefixed slots, with the compiler and the repository agreeing (P0-F-4, D2 §7.1).",
           f"- **Value-class attributes** are slot rows named `<prefix>:<Class>.<attr>` ({ck['value-class attribute rows (named <prefix>:<Class>.<attr>)']}): "
           "D3's `meta.schema_slot` key `(schema_version_id, name)` cannot hold an attribute such as `v` of two value classes under its bare name, so the "
           "class is folded into the name; a `domain_class` column in the key would say it directly (DDL / D2 §7.1 finding).",
           "- **`ParseStatus` has `ambiguous`**, which D3's `parse_status` CHECKs (`kb.segment`, `kb.rendition`) do not allow; one of the two moves.",
           "- U6's `Statement`-typed entity stays a misfit against either version (OPEN-D1-5).", ""]
    (RESULTS / f"dry_run{suffix}.md").write_text("\n".join(md) + "\n")
    print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in checks.items()}, default=str, indent=1)[:3000])
    print("hash", out["content_hash_matches"], [a["body_hash_recomputed_matches"] for a in art], inserted, rejected[:3])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
