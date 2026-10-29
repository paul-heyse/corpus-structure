r"""S5-A step 5, generated layers of the tree/token property (KEYS-01; D1 §6.2; D9 §4).

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run --project <spike folder> --no-sync \
        --with hypothesis==6.170.12 python code/s5_keys_property.py [--variant extended] [--printer s5] [--examples N]

1. **Metamorphic, token form alone** (no grammar), over all 28,956 corpus spans: seeded rewrites
   that D1 §6.2 says leave the token form unchanged — spacing commands inserted between tokens
   (``\,`` ``\;`` ``\!`` ``\quad``), sizing commands before bare delimiters, braces around a single
   letter, digit or Greek letter, whitespace between tokens outside text-mode arguments. Checked
   for the spike's I-R2 token form and the product's ``core/tex.py``. Separation cases: ``\P`` vs
   ``\Phi``, ``\mu x`` vs ``\mux``, ``a\ b`` vs ``ab``.
2. **Metamorphic, with the grammar**: on a seeded sample of spans the grammar reads, each rewrite
   is parsed too; where it is read, the tree printer must equal the token form (of the rewrite,
   and so of the original).
3. **Generated from the grammar**: Hypothesis ``from_lark`` over the assembled grammar (start
   ``any_value``; printable ASCII; explicit strategies for the generated macro terminals GEN_SET,
   GEN_OP, GEN_STYLE drawn from the Siegrist effective table). Every generated string the grammar
   reads is checked; disagreements are collected (not fail-fast), then a strict ``@given`` test
   is run so Hypothesis shrinks any counterexample.

Writes results/s5/keys_property.json and results/s5/keys_generated.tsv (the disagreements and a
sample of agreeing generated strings).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
EVIDENCE = CODE.parent
REPO = EVIDENCE.parents[3]
OUT = EVIDENCE / "results" / "s5"
sys.path.insert(0, str(REPO / "python" / "corpus-structure" / "src"))

import s5_coverage as COV  # noqa: E402
from mathgrammar import printer as P  # noqa: E402

SEED = 20261028
SPACING = ("\\,", "\\;", "\\!", "\\quad", "\\:")
SIZING = P.SIZING_COMMANDS
BARE_DELIMS = {"(", ")", "[", "]", "|", "\\{", "\\}", "/"}
GREEK = {"\\alpha", "\\beta", "\\gamma", "\\mu", "\\sigma", "\\lambda", "\\theta", "\\pi", "\\rho", "\\tau", "\\Gamma"}


def _text_mask(toks: list[str]) -> list[bool]:
    """Tokens inside a text-mode argument (braces included), or in an environment's name group
    (``\begin{align}``: inserting there names another environment, not a rewrite of this one)."""
    out = _mask_text(toks)
    for i, t in enumerate(toks):
        if t in ("\\begin", "\\end"):
            j = i + 1
            while j < len(toks) and toks[j].isspace():
                j += 1
            if j < len(toks) and toks[j] == "{":
                k = j
                while k < len(toks) and toks[k] != "}":
                    k += 1
                for m in range(i, min(k + 1, len(toks))):
                    out[m] = True
    return out


def _mask_text(toks: list[str]) -> list[bool]:
    out, depth_stack, pending = [], [], False
    for t in toks:
        inside = bool(depth_stack) and depth_stack[-1]
        if t == "{":
            depth_stack.append(pending or inside)
            inside = inside or pending
        elif t == "}" and depth_stack:
            depth_stack.pop()
        out.append(inside)
        if not t.isspace():
            pending = t in P.TEXT_MODE
    return out


def rewrites(latex: str, rng: random.Random) -> list[tuple[str, str]]:
    """(relation, rewritten) pairs whose token form D1 §6.2 says is unchanged."""
    toks = P.tex_tokens(latex)
    mask = _text_mask(toks)
    n = len(toks)
    out = []
    # positions between two tokens, both outside text mode, the left not a control word directly
    # before a letter (inserting there is fine for spacing commands, which end in a non-letter or are
    # control words followed by a non-letter only if we add a space) and not after a control space
    gaps = [i for i in range(1, n) if not mask[i - 1] and not mask[i] and toks[i - 1] not in ("\\ ", "\\")]
    # skip the delimiters themselves: \( ... \) at the ends stay outer
    gaps = [i for i in gaps if i > 1 and i < n - 1]
    if gaps:
        i = rng.choice(gaps)
        cmd = rng.choice(SPACING)
        sep = " " if cmd[-1].isalpha() and toks[i][:1].isalpha() else ""
        out.append(("spacing", "".join(toks[:i]) + cmd + sep + "".join(toks[i:])))
        j = rng.choice(gaps)
        out.append(("whitespace", "".join(toks[:j]) + " " * rng.choice((1, 2)) + "".join(toks[j:])))
    delims = [i for i in range(1, n - 1) if toks[i] in BARE_DELIMS and not mask[i]
              and toks[i - 1] not in ("\\left", "\\right", "\\middle") and toks[i - 1] not in SIZING
              and not (toks[i - 1].startswith("\\") and toks[i - 1][1:].isalpha() and toks[i - 1] not in DROPPABLE_PREV)]
    if delims:
        i = rng.choice(delims)
        out.append(("sizing", "".join(toks[:i]) + rng.choice(SIZING) + "".join(toks[i:])))
    singles = [i for i in range(1, n - 1) if not mask[i] and (toks[i].isalnum() and len(toks[i]) == 1 or toks[i] in GREEK)
               and not (toks[i - 1].startswith("\\") and toks[i - 1][1:].isalpha() and toks[i].isalpha()
                        and toks[i - 1] not in GREEK and toks[i - 1] not in P.DROP and False)]
    if singles:
        i = rng.choice(singles)
        out.append(("braces", "".join(toks[:i]) + "{" + toks[i] + "}" + "".join(toks[i + 1:])))
    return out


# a control word before a bare delimiter may take it as an argument (\big is a sizing command; \sqrt[
# is an optional argument); only these are known to read nothing from a following delimiter
DROPPABLE_PREV = {"\\in", "\\le", "\\ge", "\\lt", "\\gt", "\\cdot", "\\times", "\\exp", "\\ln", "\\log", "\\quad"}


def token_layer(spans: list[dict], tables: dict, ptables: dict, tex) -> dict:
    rng = random.Random(SEED)
    stats = Counter()
    bad = []
    for s in spans:
        tbl, ptbl = tables[s["page"]], ptables[s["page"]]
        base_s, base_p = P.tokens_canonical(s["latex"], tbl), tex.token_form(s["latex"], ptbl)
        for rel, rw in rewrites(s["latex"], rng):
            got_s, got_p = P.tokens_canonical(rw, tbl), tex.token_form(rw, ptbl)
            stats[(rel, "spike", got_s == base_s)] += 1
            stats[(rel, "product", got_p == base_p)] += 1
            if got_s != base_s or got_p != base_p:
                bad.append({"key": s["key"], "relation": rel, "latex": s["latex"], "rewritten": rw,
                            "spike": [base_s, got_s], "product": [base_p, got_p]})
    sep_cases = [("\\P", "\\Phi"), ("\\mu x", "\\mux"), ("a\\ b", "ab"), ("a\\ b", "a\\,b"), ("\\text{a b}", "\\text{ab}"),
                 ("\\R", "\\Re")]
    seps = []
    tbl = next(iter(tables.values()))
    ptbl = next(iter(ptables.values()))
    for a, b in sep_cases:
        seps.append({"a": a, "b": b, "spike_distinct": P.tokens_canonical(a, tbl) != P.tokens_canonical(b, tbl),
                     "product_distinct": tex.token_form(a, ptbl) != tex.token_form(b, ptbl)})
    return {"rewrites": {f"{r}|{w}|{'same' if ok else 'changed'}": c for (r, w, ok), c in sorted(stats.items())},
            "changed": bad[:200], "changed_n": len(bad), "separation": seps}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="extended")
    ap.add_argument("--printer", default="s5")
    ap.add_argument("--examples", type=int, default=3000)
    ap.add_argument("--grammar-sample", type=int, default=3000)
    a = ap.parse_args()

    from corpus_structure.core import tex
    from corpus_structure.core.evidence import MacroDef
    from instruments.values import merged_macros

    tbls = json.loads((OUT / "macro_tables.json").read_text())
    spans = [json.loads(x) for x in (OUT / "spans.jsonl").read_text().splitlines()]
    eff = {p: merged_macros(v["table"]) for p, v in tbls.items()}
    tables = {p: P.macro_table(e) for p, e in eff.items()}
    ptables = {p: {n: MacroDef(nargs=s.get("nargs", 0), body=s["body"], default=s.get("default")) for n, s in e.items()}
               for p, e in eff.items()}
    result = {"seed": SEED, "variant": a.variant, "printer": a.printer}

    # ---- 1. token form alone
    result["token_layer"] = token_layer(spans, tables, ptables, tex)
    print("token layer", json.dumps({k: v for k, v in result["token_layer"].items() if k != "changed"})[:1500])

    # ---- 2. with the grammar, on a sample of spans the grammar reads
    COV._init(a.variant, a.printer)
    api, tree_printer = COV._STATE["api"], COV._STATE["tree_printer"]
    run = OUT / "runs" / f"{a.variant}.tokenizer{'' if a.printer == 'spike' else '.' + a.printer}.jsonl"
    read = [json.loads(x) for x in run.read_text().splitlines()]
    read_keys = {r["key"] for r in read if r["tree"] is not None}
    rng = random.Random(SEED + 1)
    pool = [s for s in spans if s["key"] in read_keys]
    sample = rng.sample(pool, min(a.grammar_sample, len(pool)))
    gstats, gbad = Counter(), []
    for s in sample:
        mc = api._macro_class(eff[s["page"]])
        COV._STATE["mc"] = mc
        table = mc.table()
        for rel, rw in rewrites(s["latex"], rng):
            COV._STATE["budget"], COV._STATE["resolver_timeouts"] = COV.RESOLVE_BUDGET, 0
            r = api.parse(rw, "any_value", mc=mc)
            if r.tree is None:
                gstats[(rel, "not read")] += 1
                continue
            tok = P.tokens_canonical(rw, table)
            tr = tree_printer(r, table)
            ok = tr == tok
            gstats[(rel, "agree" if ok else "disagree")] += 1
            if not ok:
                gbad.append({"key": s["key"], "relation": rel, "rewritten": rw, "tree": tr, "token": tok, "status": r.status})
    result["grammar_layer"] = {"sample": len(sample), "stats": {f"{r}|{k}": c for (r, k), c in sorted(gstats.items())},
                               "disagreements": gbad[:100], "disagreements_n": len(gbad)}
    print("grammar layer", json.dumps(result["grammar_layer"])[:1500])

    # ---- 3. generated from the grammar
    from hypothesis import HealthCheck, given, settings, strategies as st
    from hypothesis.extra.lark import from_lark

    import s5grammar
    from mathgrammar import build

    siegrist = eff["special/Normal.html"]
    mc = api._macro_class(siegrist)
    COV._STATE["mc"] = mc
    parser = s5grammar.build_parser(a.variant, mc)
    explicit = {"GEN_SET": st.sampled_from([n for n, _ in mc.sets] or ["\\R"]),
                "GEN_OP": st.sampled_from([n for n, _ in mc.ops] or ["\\E"]),
                "GEN_STYLE": st.sampled_from([n for n, _ in mc.styles] or ["\\bs"])}
    alphabet = st.characters(min_codepoint=32, max_codepoint=126)
    strat = from_lark(parser, start="any_value", explicit=explicit, alphabet=alphabet)
    table = mc.table()
    gen = Counter()
    rows: list[dict] = []

    def check(s: str) -> tuple[bool | None, dict]:
        COV._STATE["budget"], COV._STATE["resolver_timeouts"] = COV.RESOLVE_BUDGET, 0
        r = api.parse(s, "any_value", mc=mc)
        if r.tree is None:
            return None, {"status": r.status, "category": (r.reason or {}).get("category")}
        tr, tok = tree_printer(r, table), P.tokens_canonical(s, table)
        return tr == tok, {"status": r.status, "tree": tr, "token": tok}

    cfg = settings(max_examples=a.examples, deadline=None, database=None, derandomize=True,
                   suppress_health_check=list(HealthCheck))

    @cfg
    @given(strat)
    def collect(s):
        ok, info = check(s)
        gen["generated"] += 1
        gen["read" if ok is not None else "not read"] += 1
        if ok is not None:
            gen["agree" if ok else "disagree"] += 1
            if not ok or len(rows) < 60:
                rows.append({"latex": s, "agree": ok, **info})

    collect()
    strict_result = {"run": True, "counterexample": None}

    @settings(max_examples=a.examples, deadline=None, database=None, derandomize=True,
              suppress_health_check=list(HealthCheck))
    @given(strat)
    def strict(s):
        ok, info = check(s)
        assert ok is not False, info

    try:
        strict()
    except AssertionError as e:
        strict_result["counterexample"] = str(e)[:600]
    result["generated_layer"] = {"start": "any_value", "examples": a.examples, "counts": dict(gen),
                                 "disagreements": [r for r in rows if r["agree"] is False][:100],
                                 "strict": strict_result, "macro_table_page": "special/Normal.html"}
    print("generated layer", json.dumps(result["generated_layer"])[:2000])
    (OUT / "keys_property.json").write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    with (OUT / "keys_generated.tsv").open("w", encoding="utf-8") as fh:
        fh.write("latex\tstatus\tagree\ttree\ttoken\n")
        for r in rows:
            fh.write("\t".join(str(r.get(k, "")).replace("\t", " ").replace("\n", " ") for k in
                               ("latex", "status", "agree", "tree", "token")) + "\n")
    _ = build
    return 0


if __name__ == "__main__":
    sys.exit(main())
