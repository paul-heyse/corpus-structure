"""S6-C (brief steps 4–5): D3 §9 patterns, D8 §5.3 trace questions in SQL, and BM25 (OPEN-D3-1).

    uv run python code/s6c_queries.py      # after code/s6b_rows.py, on the same cs_spike_s6

The D3 query texts are read from ``code/s6_queries_d3.sql`` (extracted, never retyped); ``:name``
parameters become psycopg parameters, and the one correction the BM25 query needs (F1's cast in
the repeated predicate) is applied in code and listed. The D8 §5.3 queries are this spike's SQL
sketches of the typed queries over the D3 patterns; their rows are mapped back to v1 reference
local refs and to the trace's C-refs.

Every query: rows (abridged), client wall time (median of 7 runs, ms), and its
``EXPLAIN (ANALYZE, COSTS off, TIMING off)`` plan. Writes ``results/s6/queries.md``,
``results/s6/bm25.md`` and ``results/s6/queries.json``.
"""

from __future__ import annotations

import json
import re
import statistics
import time

import psycopg

from s6_db import CODE, RESULTS, app, write_json
from s6_load import CORE, S0R2, SAMPLE, key

RUN = 1
PRED = "s.kind IN ('paragraph','heading','list_item','math_display') AND s.ts_config = 'english'"
PRED_FIXED = PRED + "::regconfig"

# trace C-refs (docs/design/trace.md) -> v1 reference local refs
TRACE = {
    "T1": {"C1": "c_Z_values", "C2": "c_X_def", "C3": "c_defines", "C4": "c_constr", "C5": "c_hp_loc", "C6": "c_hp_scale", "C7": "c_dom_loc", "C8": "c_dom_scale"},
    "T2": {"C1": "c_X_normal", "C4": "c_loc_is_mean", "C5": "c_scale_is_sd"},
    "T3": {"C1": "c_X_normal", "C2": "c_aX_def", "C3": "c_aX_normal", "C4": "c_proves"},
    "T4": {f"C{i}": r for i, r in enumerate(["c_Y_normal", "c_X_def", "c_X_lognormal", "c_defines_LN", "c_hp_mu", "c_hp_sigma", "c_LN_transform",
                                              "c_role_sigma", "c_hp_scale", "c_scale_derived", "c_dom_mu", "c_dom_sigma", "c_Z_stdnormal",
                                              "c_W_def", "c_W_stdlognormal", "c_defines_SLN", "c_SLN_transform"], start=1)},
}


MARKERS = {394: "to_bm25query", 960: "s.type = 'DistributionFamily'", 971: "c.statement_id = :statement_id", 981: "qualifiers @?",
           989: "FROM kb.claim_evidence ce", 1000: "CROSS JOIN LATERAL", 1020: "LEFT JOIN ops.policy_rule pr"}


def d3_query(line: int) -> str:
    """The D3 query block, found by its content (MARKERS keys are the baseline 35ea59a line numbers, used as names)."""
    blocks = (CODE / "s6_queries_d3.sql").read_text().split("-- D3 lines ")[1:]
    (b,) = [b for b in blocks if MARKERS[line] in b]
    sql = b.split("\n", 1)[1].strip().rstrip(";")
    return re.sub(r"(?<![:\w]):([a-z_]+)\b", r"%(\1)s", sql)


def timed(c, sql, params=None, n=7):
    ts, rows = [], None
    for _ in range(n):
        t0 = time.perf_counter()
        rows = c.execute(sql, params).fetchall()
        ts.append((time.perf_counter() - t0) * 1000)
    return rows, round(statistics.median(ts), 3)


def plan(c, sql, params=None, settings=()):
    with c.transaction(force_rollback=True):
        for s in settings:
            c.execute(s)
        return [r[0] for r in c.execute(f"EXPLAIN (ANALYZE, COSTS off, TIMING off) {sql}", params).fetchall()]


def claim_map(c) -> dict[int, tuple[str, str]]:
    out = {}
    for u in CORE:
        for cl in json.loads((S0R2 / "reference_v1" / f"{u}.json").read_text())["claims"]:
            r = c.execute("SELECT id FROM kb.claim WHERE run_id = %s AND key = %s",
                          (RUN, key("clm", {"unit": u, "local_ref": cl["local_ref"], "run": "placeholder"}))).fetchone()
            if r:
                out[r[0]] = (u, cl["local_ref"])
    for (cid,) in c.execute("SELECT id FROM kb.claim WHERE run_id = %s AND establishment = 'derived'", (RUN,)):
        out[cid] = ("T3", "D1 (derived, D3 §10)")
    return out


def tref(u, lr):
    inv = {v: k for k, v in TRACE.get(u, {}).items()}
    return inv.get(lr, "")


def entity(c, label, typ):
    return c.execute("SELECT id, key FROM kb.entity WHERE run_id = %s AND label = %s AND type = %s", (RUN, label, typ)).fetchone()


def md_table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in rows:
        out.append("| " + " | ".join(str(x).replace("|", "\\|").replace("\n", " ") for x in r) + " |")
    return out


# ---- D3 §9 and D8 §5.3 -------------------------------------------------------------------------

STATEMENT_BY_LOCATOR = """
WITH u AS (
  SELECT seg.rendition_id, seg.start_offset, seg.end_offset
  FROM kb.run_rendition rr
  JOIN kb.document d ON d.id = rr.document_id
  JOIN kb.segment seg ON seg.rendition_id = rr.rendition_id
  WHERE rr.run_id = %(run)s AND d.source_uri = %(source_uri)s AND seg.kind = 'unit' AND seg.attrs ->> 'id' = %(unit_id)s),
st AS (
  SELECT DISTINCT e.id, e.kind
  FROM kb.entity e
  JOIN kb.entity_anchor a ON a.entity_id = e.id
  JOIN kb.segment s ON s.id = a.segment_id
  JOIN u ON s.rendition_id = u.rendition_id AND s.start_offset >= u.start_offset AND s.end_offset <= u.end_offset
  WHERE e.run_id = %(run)s AND e.type = 'Statement')
SELECT st.kind, c.statement_role, c.id, c.predicate, coalesce(c.qualifiers ->> 'modality', 'asserted') AS modality,
       c.qualifiers ? 'conditions' AS has_conditions,
       (SELECT count(*) FROM kb.claim_evidence ce WHERE ce.claim_id = c.id) AS evidence
FROM st JOIN kb.claim c ON c.statement_id = st.id
WHERE c.run_id = %(run)s AND c.status = 'accepted'
ORDER BY st.kind, CASE c.statement_role WHEN 'premise' THEN 0 WHEN 'definiens' THEN 1 WHEN 'restriction' THEN 2 ELSE 3 END, c.id"""

# family_profile: D3 §9's pattern (claims whose subject is the family) plus claims on the
# FamilyParameter entities whose identity names the family (D8 §5.2)
FAMILY_PROFILE = """
SELECT 'family' AS via, c.id, c.predicate, o.label AS object_label, coalesce(c.qualifiers ->> 'modality', 'asserted') AS modality
FROM kb.claim c JOIN kb.entity s ON s.id = c.subject_id LEFT JOIN kb.entity o ON o.id = c.object_entity_id
WHERE c.run_id = %(run)s AND s.key = %(family_key)s AND c.status IN ('accepted','candidate')
UNION ALL
SELECT 'parameter ' || p.label, c.id, c.predicate, o.label, coalesce(c.qualifiers ->> 'modality', 'asserted')
FROM kb.entity p JOIN kb.claim c ON c.subject_id = p.id AND c.run_id = p.run_id LEFT JOIN kb.entity o ON o.id = c.object_entity_id
WHERE p.run_id = %(run)s AND p.type = 'FamilyParameter' AND p.attrs ->> 'family' = %(family_key)s AND c.status IN ('accepted','candidate')
ORDER BY 1, 2"""

FAMILY_PARAMS = """
SELECT p.label, p.attrs ->> 'canonical_name' FROM kb.entity p
WHERE p.run_id = %(run)s AND p.type = 'FamilyParameter' AND p.attrs ->> 'family' = %(family_key)s ORDER BY 1"""

CONSTRUCTION_PROFILE = FAMILY_PROFILE  # same shape: subject the construction, or a parameter whose identity names it

TRANSFORMATIONS_OF = """
WITH thm AS (
  SELECT DISTINCT c.statement_id
  FROM kb.claim c JOIN kb.entity o ON o.id = c.object_entity_id
  WHERE c.run_id = %(run)s AND c.predicate = 'stat:has_distribution' AND c.statement_role = 'premise' AND o.key = %(family_key)s),
concl AS (   -- a conclusion giving the distribution of a variable the same statement defines
  SELECT c.statement_id, c.subject_id FROM kb.claim c JOIN thm USING (statement_id)
  WHERE c.run_id = %(run)s AND c.statement_role = 'conclusion' AND c.predicate = 'stat:has_distribution'
    AND EXISTS (SELECT 1 FROM kb.claim d WHERE d.run_id = c.run_id AND d.statement_id = c.statement_id
                AND d.subject_id = c.subject_id AND d.predicate = 'stat:defined_as'))
SELECT c.statement_role, c.id, c.predicate, c.establishment, coalesce(c.qualifiers ->> 'modality', 'asserted') AS modality,
       jsonb_path_query_array(c.qualifiers -> 'conditions', 'strict $.**.latex') AS condition_latex
FROM kb.claim c
WHERE c.run_id = %(run)s AND c.statement_id IN (SELECT statement_id FROM concl)
  AND (c.subject_id IN (SELECT subject_id FROM concl) OR c.statement_role = 'premise')
ORDER BY CASE c.statement_role WHEN 'premise' THEN 0 WHEN 'definiens' THEN 1 ELSE 2 END, c.id"""


def d3_section(c, cm) -> tuple[list[str], dict]:
    md, out = ["## D3 §9 patterns", ""], {}
    normal, lognormal = entity(c, "normal distribution", "DistributionFamily"), entity(c, "lognormal distribution", "DistributionFamily")
    st = {u: c.execute("SELECT id FROM kb.entity WHERE run_id = %s AND type = 'Statement' AND label = %s", (RUN, lbl)).fetchone()[0]
          for u, lbl in (("T3", "theorem T3:st1"), ("T4", "definition T4:st1"))}
    c3 = next(i for i, v in cm.items() if v == ("T3", "c_aX_normal"))
    u12 = next(i for i, v in cm.items() if v == ("U12", "c_X_stdgamma"))
    t3_unit = c.execute("SELECT unit_key FROM ops.task WHERE run_id = %s AND stage = 'propose' AND unit_id = (SELECT id FROM kb.segment WHERE key = %s)",
                        (RUN, SAMPLE["units"]["T3"]["parts"][-1]["segment_key"])).fetchone()[0]
    docs = [r[0] for r in c.execute("SELECT document_id FROM kb.run_rendition WHERE run_id = %s", (RUN,))]
    cases = [
        ("family_profile(normal)", 960, {"run": RUN, "family_key": normal[1]}, lambda r: (r[0], r[3], json.dumps(r[2])[:50] if r[2] else "", r[4])),
        ("family_profile(lognormal)", 960, {"run": RUN, "family_key": lognormal[1]}, lambda r: (r[0], r[3], json.dumps(r[2])[:50] if r[2] else "", r[4])),
        ("statement reconstruction (T3 theorem)", 971, {"run": RUN, "statement_id": st["T3"]}, lambda r: (r[0], r[2], "/".join(cm.get(_cid(c, r[1]), ("", "?"))), bool(r[3]))),
        ("statement reconstruction (T4 definition)", 971, {"run": RUN, "statement_id": st["T4"]}, lambda r: (r[0], r[2], "/".join(cm.get(_cid(c, r[1]), ("", "?"))), bool(r[3]))),
        ("claims with qualifier param_values.variance", 981, {"run": RUN}, lambda r: ("/".join(cm.get(_cid(c, r[0]), ("", "?"))),)),
        ("evidence for T3 C3", 989, {"claim_id": c3}, lambda r: (r[0], r[1][:60], r[2], r[3], r[4], r[5])),
        ("evidence for U12 c_X_stdgamma (context premise, c1)", 989, {"claim_id": u12}, lambda r: (r[0], r[1][:60], r[2], r[3], r[4], r[5])),
        ("coverage of the four pages", 1000, {"run": RUN, "documents": docs}, lambda r: r),
        ("why a method ran (T3's unit)", 1020, {"run": RUN, "unit_key": t3_unit}, lambda r: (r[0], r[1], r[2], json.dumps(r[3]), r[4], json.dumps(r[5]))),
    ]
    for name, line, params, fmt in cases:
        sql = d3_query(line)
        rows, ms = timed(c, sql, params)
        p = plan(c, sql, params)
        out[name] = {"rows": len(rows), "ms": ms, "plan": p}
        md += [f"### {name}", "", f"D3 §9 block (`{MARKERS[line]}`); {len(rows)} rows; median {ms} ms.", ""]
        md += md_table([f"c{i}" for i in range(len(fmt(rows[0])))] if rows else ["(no rows)"], [fmt(r) for r in rows[:20]])
        md += ["", "```", *p, "```", ""]
    # the @? qualifier query: is it carried by claim_pred? (no GIN index; D3 §5)
    sql = d3_query(981)
    p_off = plan(c, sql, {"run": RUN}, ("SET LOCAL enable_seqscan = off",))
    out["qualifier_query_index"] = {"chosen": out["claims with qualifier param_values.variance"]["plan"], "seqscan_off": p_off,
                                    "claim_pred_used": any("claim_pred" in x for x in out["claims with qualifier param_values.variance"]["plan"] + p_off)}
    md += ["### The `@?` qualifier query and `claim_pred`", "", "With `enable_seqscan = off` (tables are small, so the chosen plan may be a scan):", "",
           "```", *p_off, "```", "", f"`claim_pred` carries it: {out['qualifier_query_index']['claim_pred_used']} "
           "(index condition on `run_id, predicate`; the `@?` path test is a filter on the fetched rows).", ""]
    return md, out


def _cid(c, k):
    r = c.execute("SELECT id FROM kb.claim WHERE run_id = %s AND key = %s", (RUN, k)).fetchone()
    return r[0] if r else None


def d8_section(c, cm) -> tuple[list[str], dict]:
    md = ["## D8 §5.3 trace questions in SQL", "",
          "Each query is a SQL sketch of the typed query over the D3 patterns, run on run 1 (all twelve core units of the v1 reference). "
          "Rows are shown as `unit/local_ref` with the trace C-ref where the row is a trace unit's target claim. The default "
          "filters (status `accepted`; modality not `supposed` unless `include_suppositions`, D8 §5) are shown as a column, not applied, "
          "so the comparison is visible.", ""]
    out = {}
    normal, lognormal = entity(c, "normal distribution", "DistributionFamily"), entity(c, "lognormal distribution", "DistributionFamily")
    lsf = entity(c, "location-scale family", "FamilyConstruction")
    cases = [
        ("T1", "statement(LocationScale#dfn1)", STATEMENT_BY_LOCATOR, {"run": RUN, "source_uri": "siegrist_random/random/special/LocationScale.html", "unit_id": "dfn1"},
         2, ["C2", "C3", "C4", "C5", "C6", "C7", "C8"], "Statement S1 (definition) with C2 (definiens, conditions), C3, C4–C8; C1 only with include_suppositions"),
        ("T1", "construction_profile(location-scale family)", CONSTRUCTION_PROFILE, {"run": RUN, "family_key": lsf[1]},
         1, ["C4", "C5", "C6", "C7", "C8"], "C4 with base variable Z and parameter symbols; parameters location and scale (C5, C6) with domains (C7, C8)"),
        ("T2", "family_profile(normal)", FAMILY_PROFILE, {"run": RUN, "family_key": normal[1]},
         1, ["C4", "C5"], "Parameters location and scale (FamilyParameter entities whose identity names the family), identical to mean and sd (C4, C5); no has_parameter claim; C1 only with include_suppositions"),
        ("T3", "transformations_of(normal)", TRANSFORMATIONS_OF, {"run": RUN, "family_key": normal[1]},
         1, ["C1", "C2", "C3"], "C3 with conditions a ∈ ℝ, b ∈ ℝ∖{0} and premise C1, and C2 defining Y under the same restrictions; D1 from phase 2"),
        ("T4", "statement(LogNormal#dfn)", STATEMENT_BY_LOCATOR, {"run": RUN, "source_uri": "siegrist_random/random/special/LogNormal.html", "unit_id": "dfn"},
         2, [f"C{i}" for i in range(1, 18)], "C1–C17 in the statement (with the standard lognormal, C13–C17)"),
        ("T4", "family_profile(lognormal)", FAMILY_PROFILE, {"run": RUN, "family_key": lognormal[1]},
         1, ["C5", "C6", "C7", "C8", "C9", "C10", "C11", "C12"], "parameters mu, sigma and scale (C5, C6, C9) with domains (C11, C12), sigma's role shape (C8), scale = e^μ (C10), transformation of normal (C7)"),
    ]
    for unit, name, sql, params, id_col, expected, expected_text in cases:
        rows, ms = timed(c, sql, params)
        p = plan(c, sql, params)
        got = [cm.get(r[id_col], ("?", "?")) for r in rows]
        refs = [tref(u, lr) if u == unit else "" for u, lr in got]
        missing = [e for e in expected if e not in refs]
        extra = [f"{u}/{lr}" + (f" ({tref(u, lr)})" if tref(u, lr) else "") for (u, lr), rf in zip(got, refs) if not rf or rf not in expected]
        out[f"{unit} {name}"] = {"rows": len(rows), "ms": ms, "expected": expected, "missing": missing, "extra": extra, "plan": p}
        md += [f"### {unit} · `{name}`", "", f"Expected (D8 §5.3): {expected_text}.", "",
               f"{len(rows)} rows; median {ms} ms. Trace refs returned: {', '.join(r for r in refs if r) or 'none'}. "
               f"Missing from the expected: {', '.join(missing) or 'none'}. Rows beyond the expected: {', '.join(extra) or 'none'}.", ""]
        md += md_table(["row", "unit/local_ref", "trace"], [(", ".join(str(x) for i, x in enumerate(r) if i != id_col), f"{u}/{lr}", rf) for r, (u, lr), rf in zip(rows, got, refs)])
        if "family_key" in params:
            fp = c.execute(FAMILY_PARAMS, params).fetchall()
            md += ["", "FamilyParameter entities whose identity names it: " + "; ".join(f"{a} ({b})" for a, b in fp)]
        md += ["", "```", *p, "```", ""]
    return md, out


# ---- BM25 ------------------------------------------------------------------------------------------

QUERIES = ["affine transformation normal", "location-scale family", "lognormal shape parameter", "sum of independent gamma", "standard score"]


def bm25_section(c) -> tuple[list[str], dict]:
    out, md = {}, ["# S6 BM25 (OPEN-D3-1)", "", "pg_textsearch 1.5.1 on PostgreSQL 18.6 (project-local cluster), index `kb.segment_bm25` as created by "
                   "`code/s6_ddl_applied.sql` (F1: `'english'::regconfig` in its predicate). Run 1's renditions of the four spike pages.", ""]
    renditions = [r[0] for r in c.execute("SELECT rendition_id FROM kb.run_rendition WHERE run_id = %s ORDER BY 1", (RUN,))]
    # index rebuild on the loaded table, timed
    idx = c.execute("SELECT pg_get_indexdef('kb.segment_bm25'::regclass)").fetchone()[0]
    with c.transaction():
        c.execute("DROP INDEX kb.segment_bm25")
        t0 = time.perf_counter()
        c.execute(idx)
        out["build_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    n_idx = c.execute(f"SELECT count(*) FROM kb.segment s WHERE {PRED_FIXED}").fetchone()[0]
    out["indexed_rows"], out["segments"] = n_idx, c.execute("SELECT count(*) FROM kb.segment").fetchone()[0]
    out["index_bytes"] = c.execute("SELECT pg_relation_size('kb.segment_bm25')").fetchone()[0]
    md += ["## Index", "", "```sql", idx, "```", "",
           f"{n_idx} of {out['segments']} segment rows indexed (sentences, units, sections, details, lists, inline math and the document row excluded by the predicate); "
           f"rebuilt on the loaded table in {out['build_ms']} ms; {out['index_bytes']} bytes.", ""]
    # non-overlap and coverage of the kind list
    ov = c.execute(f"""
        SELECT r.key, a.kind, b.kind, count(*) FROM kb.segment a JOIN kb.segment b
          ON a.rendition_id = b.rendition_id AND a.id < b.id AND a.start_offset < b.end_offset AND b.start_offset < a.end_offset
        JOIN kb.rendition r ON r.id = a.rendition_id
        WHERE {PRED_FIXED.replace('s.', 'a.')} AND {PRED_FIXED.replace('s.', 'b.')}
        GROUP BY 1, 2, 3 ORDER BY 1, 2, 3""").fetchall()
    examples = c.execute(f"""
        SELECT r.key, a.kind, a.key, a.start_offset, a.end_offset, b.kind, b.key, b.start_offset, b.end_offset, left(b.text, 60)
        FROM kb.segment a JOIN kb.segment b
          ON a.rendition_id = b.rendition_id AND a.id < b.id AND a.start_offset < b.end_offset AND b.start_offset < a.end_offset
        JOIN kb.rendition r ON r.id = a.rendition_id
        WHERE {PRED_FIXED.replace('s.', 'a.')} AND {PRED_FIXED.replace('s.', 'b.')} ORDER BY 1, 4 LIMIT 8""").fetchall()
    cov = {}
    for rid, text in c.execute("SELECT id, canonical_text FROM kb.rendition WHERE id = ANY(%s)", (renditions,)).fetchall():
        hits = [0] * len(text)
        for s, e in c.execute(f"SELECT start_offset, end_offset FROM kb.segment s WHERE rendition_id = %s AND {PRED_FIXED}", (rid,)):
            for k in range(s, e):
                hits[k] += 1
        ns = [k for k, ch in enumerate(text) if not ch.isspace()]
        uncovered = [k for k in ns if hits[k] == 0]
        runs, prev = [], None
        for k in uncovered:
            if prev is None or k != prev + 1:
                runs.append([k, k])
            runs[-1][1] = k
            prev = k
        cov[rid] = {"non_space_chars": len(ns), "uncovered": len(uncovered), "covered_twice": sum(1 for k in ns if hits[k] > 1),
                    "uncovered_examples": [text[a:b + 1][:60] for a, b in sorted(runs, key=lambda x: x[0] - x[1])[:4]]}
    rkeys = dict(c.execute("SELECT id, key FROM kb.rendition").fetchall())
    out["overlap"] = [list(r) for r in ov]
    out["coverage"] = {rkeys[k]: v for k, v in cov.items()}
    md += ["## Does the kind list overlap? (no token counted twice)", "",
           (f"Overlapping pairs of indexed segments: {sum(r[3] for r in ov)}." if ov else "No two indexed segments overlap on any of the four pages."), ""]
    if ov:
        md += md_table(["rendition", "kind a", "kind b", "pairs"], ov) + ["", "Examples:", ""]
        md += md_table(["rendition", "kind a", "key a", "a.start", "a.end", "kind b", "key b", "b.start", "b.end", "b text"], examples) + [""]
    md += ["Coverage of each page's non-whitespace canonical text by the indexed segments:", ""]
    md += md_table(["rendition", "non-space chars", "not indexed", "indexed twice", "largest unindexed runs"],
                   [(rkeys[k], v["non_space_chars"], v["uncovered"], v["covered_twice"], " · ".join(repr(x) for x in v["uncovered_examples"])) for k, v in cov.items()]) + [""]

    # candidate kind lists: overlap and coverage computed the same way
    def kinds_check(kinds):
        res = {"overlapping_chars": 0, "unindexed_chars": 0, "non_space_chars": 0, "overlapping_pairs": 0}
        for rid, text in c.execute("SELECT id, canonical_text FROM kb.rendition WHERE id = ANY(%s)", (renditions,)).fetchall():
            hits = [0] * len(text)
            segs = c.execute("SELECT start_offset, end_offset FROM kb.segment WHERE rendition_id = %s AND kind = ANY(%s) ORDER BY 1", (rid, kinds)).fetchall()
            for a, (s0, e0) in enumerate(segs):
                for k in range(s0, e0):
                    hits[k] += 1
                res["overlapping_pairs"] += sum(1 for s1, e1 in segs[a + 1:] if s1 < e0)
            ns = [k for k, ch in enumerate(text) if not ch.isspace()]
            res["non_space_chars"] += len(ns)
            res["unindexed_chars"] += sum(1 for k in ns if hits[k] == 0)
            res["overlapping_chars"] += sum(1 for k in ns if hits[k] > 1)
        return res
    cands = {"D3: paragraph, heading, list_item, math_display": ["paragraph", "heading", "list_item", "math_display"],
             "paragraph, heading, list_item": ["paragraph", "heading", "list_item"],
             "paragraph, heading, list_item, caption": ["paragraph", "heading", "list_item", "caption"]}
    out["kind_lists"] = {k: kinds_check(v) for k, v in cands.items()}
    md += ["Candidate kind lists over the four pages (non-whitespace characters):", ""]
    md += md_table(["kind list", "overlapping pairs", "chars indexed twice", "chars not indexed", "non-space chars"],
                   [(k, v["overlapping_pairs"], v["overlapping_chars"], v["unindexed_chars"], v["non_space_chars"]) for k, v in out["kind_lists"].items()]) + [""]

    # syntax variants on one query
    q = "location-scale family"
    base = d3_query(394)
    fixed = base.replace("s.ts_config = 'english'", "s.ts_config = 'english'::regconfig")
    assert fixed.count("::regconfig") == 1
    lit = {"q": q, "renditions": renditions, "k": 5}
    variants = [
        ("V1 D3 §5 form with F1's cast (index named, predicate repeated, rendition filter)", fixed, lit),
        ("V2 D3 §5 form verbatim (no cast)", base, lit),
        ("V3 V1 without the rendition filter", fixed.replace("  AND s.rendition_id = ANY(%(renditions)s)          -- the run's renditions (kb.run_rendition, §8)\n", ""), lit),
        ("V4 index named, predicate omitted", "SELECT s.id, s.key, s.text <@> to_bm25query(%(q)s, 'kb.segment_bm25') AS score FROM kb.segment s "
                                             "ORDER BY s.text <@> to_bm25query(%(q)s, 'kb.segment_bm25') LIMIT %(k)s", lit),
        ("V5 implicit string form with the predicate", f"SELECT s.id, s.key, s.text <@> %(q)s AS score FROM kb.segment s WHERE {PRED_FIXED} "
                                                       "ORDER BY s.text <@> %(q)s LIMIT %(k)s", lit),
        ("V6 implicit string form, literal query text", f"SELECT s.id, s.key FROM kb.segment s WHERE {PRED_FIXED} ORDER BY s.text <@> 'location-scale family' LIMIT 5", None),
        ("V7 predicate written as ts_config::text = 'english'", fixed.replace("s.ts_config = 'english'::regconfig", "s.ts_config::text = 'english'"), lit),
        ("V8 unqualified index name 'segment_bm25'", fixed.replace("'kb.segment_bm25'", "'segment_bm25'"), lit),
        ("V9 narrower kind predicate (paragraph only), index named", fixed.replace("s.kind IN ('paragraph','heading','list_item','math_display')", "s.kind = 'paragraph'"), lit),
    ]
    out["variants"] = {}
    md += ["## Syntax variants (query \"location-scale family\")", ""]
    for name, sql, params in variants:
        try:
            p = plan(c, sql, params)
            rows = c.execute(sql, params).fetchall()
            used = any("using segment_bm25" in x for x in p)
            kinds = sorted({c.execute("SELECT kind FROM kb.segment WHERE id = %s", (r[0],)).fetchone()[0] for r in rows})
            res = {"error": None, "index_scan": used, "rows": len(rows), "kinds": kinds, "plan": p}
        except psycopg.Error as e:
            c.rollback()
            res = {"error": f"{e.sqlstate}: {e.diag.message_primary}", "index_scan": False, "rows": 0, "plan": []}
        out["variants"][name] = res
        md += [f"### {name}", "", f"Index scan on `segment_bm25`: **{res['index_scan']}**; rows {res['rows']}" + (f" (kinds: {', '.join(res['kinds'])})" if res.get("kinds") else "") + (f"; error `{res['error']}`" if res["error"] else ""), ""]
        if res["plan"]:
            md += ["```", *res["plan"], "```", ""]
    # bound parameter in a prepared statement, custom and generic plans
    with c.transaction(force_rollback=True):
        c.execute(f"PREPARE bm(text, bigint[]) AS SELECT s.id, s.key FROM kb.segment s WHERE {PRED_FIXED} AND s.rendition_id = ANY($2) "
                  "ORDER BY s.text <@> to_bm25query($1, 'kb.segment_bm25') LIMIT 5")
        lits = "'{" + ",".join(map(str, renditions)) + "}'"
        custom = [r[0] for r in c.execute(f"EXPLAIN (COSTS off) EXECUTE bm('{q}', {lits})").fetchall()]
        c.execute("SET LOCAL plan_cache_mode = force_generic_plan")
        generic = [r[0] for r in c.execute(f"EXPLAIN (COSTS off) EXECUTE bm('{q}', {lits})").fetchall()]
        grow = c.execute(f"EXECUTE bm('{q}', {lits})").fetchall()
        c.execute("DEALLOCATE bm")
    out["prepared"] = {"custom_index": any("using segment_bm25" in x for x in custom), "generic_index": any("using segment_bm25" in x for x in generic), "generic_rows": len(grow)}
    md += ["### V10 prepared statement, query text as `$1` inside `to_bm25query($1, 'kb.segment_bm25')`", "",
           f"Custom plan uses the index: **{out['prepared']['custom_index']}**; forced generic plan: **{out['prepared']['generic_index']}** ({len(grow)} rows).", "",
           "```", "-- custom", *custom, "-- generic", *generic, "```", ""]

    # the five queries, top five each (V1 form)
    md += ["## The five queries (V1 form), top five", ""]
    out["top5"] = {}
    unit_of = """SELECT u.attrs ->> 'id' FROM kb.segment u WHERE u.rendition_id = %s AND u.kind = 'unit'
                 AND u.start_offset <= %s AND %s <= u.end_offset ORDER BY u.end_offset - u.start_offset LIMIT 1"""
    for qq in QUERIES:
        params = {"q": qq, "renditions": renditions, "k": 5}
        rows, ms = timed(c, fixed, params)
        p = plan(c, fixed, params)
        det = []
        for sid, skey, score in rows:
            rid, kind, so, eo, text = c.execute("SELECT rendition_id, kind, start_offset, end_offset, text FROM kb.segment WHERE id = %s", (sid,)).fetchone()
            page = c.execute("SELECT d.source_uri FROM kb.rendition r JOIN kb.document d ON d.id = r.document_id WHERE r.id = %s", (rid,)).fetchone()[0].rsplit("/", 1)[-1]
            u = c.execute(unit_of, (rid, so, eo)).fetchone()
            det.append([page, kind, (u[0] or "(unit without id)") if u else "", skey, round(score, 4), text[:90]])
        asc = all(det[i][4] <= det[i + 1][4] for i in range(len(det) - 1))
        out["top5"][qq] = {"rows": det, "ms": ms, "index_scan": any("using segment_bm25" in x for x in p), "scores_ascending": asc}
        md += [f"### \"{qq}\"", "", f"median {ms} ms; index scan {out['top5'][qq]['index_scan']}; scores ascending (best first) {asc}.", ""]
        md += md_table(["page", "kind", "unit", "segment key", "score", "text"], det) + ["", "```", *p, "```", ""]

    # Boolean and phrase filters with ranking
    md += ["## Boolean and phrase filters with ranking", ""]
    out["filters"] = {}
    for name, tsq, qq in (("Boolean: independent & gamma", "independent & gamma", "sum of independent gamma"),
                          ("Phrase: standard <-> score", "standard <-> score", "standard score")):
        sql = fixed.replace("ORDER BY", "  AND s.text @@ to_tsquery('english', %(tsq)s)\nORDER BY")
        params = {"q": qq, "renditions": renditions, "k": 5, "tsq": tsq}
        rows, ms = timed(c, sql, params)
        p = plan(c, sql, params)
        det = [[c.execute("SELECT kind FROM kb.segment WHERE id = %s", (r[0],)).fetchone()[0], r[1], round(r[2], 4),
                c.execute("SELECT left(text, 90) FROM kb.segment WHERE id = %s", (r[0],)).fetchone()[0]] for r in rows]
        p2 = plan(c, sql, params, ("SET LOCAL enable_seqscan = off", "SET LOCAL enable_bitmapscan = off", "SET LOCAL enable_indexscan = on"))
        out["filters"][name] = {"rows": det, "ms": ms, "plan": p, "index_scan": any("using segment_bm25" in x for x in p),
                                "plan_scans_off": p2, "index_scan_scans_off": any("using segment_bm25" in x for x in p2)}
        md += [f"### {name}", "", "```sql", sql % {k: (repr(v) if isinstance(v, str) else v) for k, v in params.items()}, "```", "",
               f"{len(rows)} rows; median {ms} ms.", ""] + md_table(["kind", "segment key", "score", "text"], det) + ["", "chosen plan:", "```", *p, "```",
               "with sequential and bitmap scans disabled (can the BM25 index serve the `@@` filter?):", "```", *p2, "```", ""]
    # can the index serve @@ at all? btree alternatives dropped inside a rolled-back transaction
    probe = {}
    bare = f"SELECT s.id FROM kb.segment s WHERE {PRED_FIXED} AND s.text @@ to_tsquery('english', 'independent & gamma')"
    ranked = bare + " ORDER BY s.text <@> to_bm25query('sum of independent gamma', 'kb.segment_bm25') LIMIT 5"
    with c.transaction(force_rollback=True):
        c.execute("DROP INDEX kb.segment_kind")
        c.execute("DROP INDEX kb.segment_range")
        c.execute("SET LOCAL enable_seqscan = off")
        for name, sql in (("@@ alone", bare), ("@@ with BM25 ranking", ranked)):
            pl = [r[0] for r in c.execute(f"EXPLAIN (ANALYZE, COSTS off, TIMING off) {sql}").fetchall()]
            probe[name] = {"plan": pl, "index_scan": any("using segment_bm25" in x for x in pl)}
    out["filter_probe"] = probe
    md += ["### Can `segment_bm25` serve the `@@` filter? (probe: `segment_kind` and `segment_range` dropped in a rolled-back transaction, `enable_seqscan = off`)", ""]
    for name, v in probe.items():
        md += [f"{name}: index scan **{v['index_scan']}**", "", "```", *v["plan"], "```", ""]
    return md, out


def main() -> int:
    with app() as c:
        c.execute("ANALYZE")
        cm = claim_map(c)
        md3, o3 = d3_section(c, cm)
        md8, o8 = d8_section(c, cm)
        c.commit()
        mdb, ob = bm25_section(c)
        c.commit()
    head = ["# S6 queries (D3 §9, D8 §5.3)", "",
            "Run 1 of `cs_spike_s6` (S6-B rows: the four spike pages, twelve core units of the v1 reference). PostgreSQL 18.6, "
            "project-local cluster; times are client wall times (median of 7) on tables of tens to thousands of rows, so plans "
            "show what the planner chose at this size, not at run scale (S6-E).", "",
            "Query texts come from `code/s6_queries_d3.sql`; the only correction applied is F1's `::regconfig` cast in the BM25 "
            "query's repeated predicate (`bm25.md`).", ""]
    fp_d3 = o3["family_profile(normal)"]["rows"]
    notes = ["## Differences and observations (2026-10-28)", "",
             f"- **D8 §5.3 against the v1 rows:** every trace question returns all its expected trace claims (missing: none in all six). "
             "Rows beyond the expectation come from other core units in the same run (U6's `transformation_of` for the normal family; "
             "U5's sum theorem under `transformations_of(normal)`) and from the derived D1 the loader adds as D3 §10 describes; D8 expects D1 only from phase 2.",
             f"- **`family_profile` needs the parameter branch.** D3 §9's pattern (claims whose subject is the family) returns {fp_d3} row for the normal "
             "family; T2's answer (C4, C5) lives on `FamilyParameter` entities whose identity names the family, reached here through "
             "`kb.entity.attrs ->> 'family'` (the identity attribute stored as the family's entity key). D3 §9 should carry that branch; with no index on "
             "`attrs` it is a filter over the run's `FamilyParameter` rows (`entity_type`).",
             "- **`statement(LocationScale#dfn1)`** resolves to the unit's statements only: the T1 assumption (C1) sits in the lead-in paragraph, outside "
             "unit `dfn1`, so no option of a unit-locator query reaches it; D8's \"C1 only with include_suppositions\" needs the composite locator "
             "(lead-in paragraph + unit) the sample uses, or the premise-through-conditions rule.",
             "- **Evidence `unit_id` is null** for spans whose smallest containing segment is a `sentence` or `math_inline` (every row here): D3 §9's "
             "`seg.attrs ->> 'id' AS unit_id` reads the span's own segment; the unit needs an ancestor lookup (`kb.segment` range or `parent_id` walk).",
             "- **The `@?` qualifier query** is carried by `claim_pred` (index condition on `run_id, predicate`; the path test filters the fetched rows).",
             "- **v1 misfit:** U6's `e_last_result` (a `Statement`-typed entity without a kind) and its claim `c_follows` were not loaded "
             "(`rows.json`); OPEN-D1-5.", ""]
    (RESULTS / "queries.md").write_text("\n".join(head + md3 + md8 + notes) + "\n")
    v = ob["variants"]
    kl = ob["kind_lists"]
    d3k = kl["D3: paragraph, heading, list_item, math_display"]
    bnotes = ["## Syntax that worked, and observations (2026-10-28)", "",
              "- **Working form** (OPEN-D3-1): `ORDER BY s.text <@> to_bm25query(:q, 'kb.segment_bm25') LIMIT :k` with the index predicate repeated as "
              "`s.kind IN (…) AND s.ts_config = 'english'::regconfig`; the schema-qualified index name is required "
              f"(V8: `{v['V8 unqualified index name ' + chr(39) + 'segment_bm25' + chr(39)]['error']}`). The planner uses an ordered `Index Scan using segment_bm25`, "
              "and the rendition condition is a post-filter on it (V1). A narrower kind predicate implied by the index's (V9) also uses it.",
              f"- **D3 §5's query as written fails** (V2: `{v['V2 D3 §5 form verbatim (no cast)']['error']}`): the F1 cast is needed in the repeated predicate.",
              f"- **The implicit string form fails** on the partial index, with a bound parameter (V5: `{v['V5 implicit string form with the predicate']['error']}`) "
              f"and with a literal (V6: `{v['V6 implicit string form, literal query text']['error']}`): an error, not a silent seq scan.",
              "- **Repeating the predicate matters for results, not only for the plan.** Named index without the predicate (V4) or with a predicate the "
              "planner cannot prove (V7, `ts_config::text = 'english'`): no index scan; rows are scored standalone with the index's statistics and sorted, "
              f"and V4 returns rows the index does not hold (kinds {', '.join(v['V4 index named, predicate omitted']['kinds'])}).",
              f"- **Prepared statements** (`$1` inside `to_bm25query`): custom and forced generic plans both use the index ({ob['prepared']}).",
              "- **Boolean and phrase filters** (`@@ to_tsquery('english', …)`) return their matches; at this size the planner evaluates `@@` as a filter "
              "over `segment_kind`. The probe shows `segment_bm25` can serve `@@` alone (`Index Cond: text @@ …`), but not combined with BM25 ordering: then "
              "the filter is evaluated on scanned rows and the matches scored and sorted, as the overview (§2.3) says.",
              f"- **The kind list overlaps.** D3's list indexes `math_display` segments that are children of indexed `paragraph` and `list_item` segments: "
              f"{d3k['overlapping_pairs']} nested pairs, {d3k['overlapping_chars']} of {d3k['non_space_chars']} non-space characters indexed twice. "
              "Without `math_display` there is no overlap; adding `caption` covers the remaining "
              f"{kl['paragraph, heading, list_item']['unindexed_chars']} characters (the Gamma page's figure caption). Display formulas outside a paragraph "
              "are already `paragraph` segments (D1 §3.2 orphans), so `('paragraph','heading','list_item','caption')` covers every character once on the four pages.",
              f"- Index: {ob['indexed_rows']} rows, rebuilt in {ob['build_ms']} ms, {ob['index_bytes']} bytes on the four pages; scores negative and ascending in all five queries.", ""]
    (RESULTS / "bm25.md").write_text("\n".join(mdb + bnotes) + "\n")
    write_json(RESULTS / "queries.json", {"d3": o3, "d8": o8, "bm25": ob})
    for k, v in o8.items():
        print(k, "rows", v["rows"], "missing", v["missing"], "extra", v["extra"][:6])
    print("variants", {k[:3]: (v["index_scan"], v["error"]) for k, v in ob["variants"].items()}, ob["prepared"])
    print("overlap", ob["overlap"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
