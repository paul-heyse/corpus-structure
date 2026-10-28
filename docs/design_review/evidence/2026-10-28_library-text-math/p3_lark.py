"""P3 (2026-10-28): Lark 1.3.1 questions for the production math grammar (spike code/mathgrammar).

    cd docs/design_review/evidence/2026-10-28_design-spikes
    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python ../2026-10-28_library-text-math/p3_lark.py

1. Parser construction time and how many distinct parsers (MacroClass keys) the 78 pages need.
2. Whether an Earley Lark instance can be saved (Lark.save) or pickled for reuse across processes.
3. Shipped %ignore literals ("\\left", "\\right") against whole-name commands (\\rightarrow, \\leftarrow ...).
4. Whether repeated builds give the same tree for an ambiguous value (ordered_sets default).
Read-only; prints JSON.
"""
import csv, io, json, pickle, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPIKE = HERE.parent / "2026-10-28_design-spikes" / "code"
sys.path.insert(0, str(SPIKE))
import lark  # noqa: E402
import lxml.html  # noqa: E402
import s1_adapter as A  # noqa: E402
from mathgrammar import api, build, printer  # noqa: E402

REPO = HERE.parents[3]
pages = [r["path"] for r in csv.DictReader((REPO / "docs/statistics_corpus/index/siegrist_sections.tsv").open(), delimiter="\t")
         if r["first_pass"] == "yes"]
keys, full = set(), set()
for p in pages:
    mc = build.classify(A.macro_table(lxml.html.document_fromstring((A.SIEGRIST / p).read_bytes())))
    keys.add(mc.key)
    full.add(mc.full_key)
res = {"distinct_parser_keys": len(keys), "distinct_full_tables": len(full)}

mc = build.classify({"\\R": {"nargs": 0, "body": "\\mathbb{R}"}, "\\var": {"nargs": 0, "body": "\\text{var}"}})
t = time.perf_counter(); p = build.parser_for(mc); res["build_s"] = round(time.perf_counter() - t, 2)
for how in ("save", "pickle"):
    try:
        buf = io.BytesIO()
        if how == "save":
            p.save(buf)
        else:
            pickle.dump(p, buf)
        res[how] = f"ok, {len(buf.getvalue())} bytes"
        if how == "pickle":
            t = time.perf_counter(); q = pickle.loads(buf.getvalue()); res["unpickle_s"] = round(time.perf_counter() - t, 3)
            res["unpickled_parses"] = str(q.parse("a + b", start="formula"))[:60]
    except Exception as e:  # noqa: BLE001
        res[how] = f"{type(e).__name__}: {str(e)[:120]}"

cases = [r"x \rightarrow 0", r"x \leftarrow y", r"A \leftrightarrow B", r"x \Rightarrow y", r"\left( a \right)",
         r"\lim_{x \rightarrow 0} f(x)", r"a \rightarrow b"]
rows = []
for c in cases:
    r = api.parse(c, "any_value", macros={})
    tree_c = printer.tree_canonical(r.tree, {}) if r.tree is not None else None
    rows.append({"latex": c, "status": r.status, "reason": (r.reason or {}).get("category"), "notes": r.notes[:2],
                 "tree_canonical": tree_c, "tokens_canonical": printer.tokens_canonical(c, {})})
res["ignore_prefix_cases"] = rows

amb = r"\frac{1}{b} g\left(\frac{x - a}{b}\right)"
trees = set()
for _ in range(3):
    build._PARSERS.clear(); api._CACHE.clear()
    r = api.parse(amb, "any_value", macros={})
    trees.add(repr(r.tree)[:4000])
res["ambiguous_value_status"] = r.status
res["distinct_trees_over_rebuilds"] = len(trees)
res["earley_ordered_sets_default"] = build.parser_for(mc).options.ordered_sets
print(json.dumps(res, indent=1, ensure_ascii=False))
