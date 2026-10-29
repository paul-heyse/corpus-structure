r"""S5-A steps 2 and 5: grammar coverage and the tree/token property over all 28,956 math spans.

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run --project <spike folder> --locked \
        python code/s5_coverage.py --variant spike|edited|edited-noovr|extended --reader spike|tokenizer [--printer spike|s5]

Every span is parsed under ``any_value`` with its rendition's effective macro table (page table
from the chosen reader over the D2 §12.1 fallback, ``instruments.values.merged_macros``), in
single-threaded worker processes (one task per page chunk; parsers cached per macro classification
in each process; ``api.PARSE_SECONDS`` timer). Failure categories are deterministic: the
exception class, the TeX token at the error position (``printer.TEX_TOKEN``) and the ``allowed`` /
``expected`` terminal set (``api._category``'s ``match_examples`` fallback is not used).

For every span the grammar reads (a tree: ``ok``, ``ambiguous``, ``partial``) the tree printer is
compared with the token form: the spike's I-R2 ``printer.tokens_canonical`` and the product's
``core/tex.py`` ``token_form`` (imported read-only). ``--printer s5`` uses ``s5grammar.printer``'s
tree printer (the fixes S5 makes on the tree side).

Writes results/s5/runs/<variant>.<reader>[.<printer>].jsonl and .summary.json.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
EVIDENCE = CODE.parent
REPO = EVIDENCE.parents[3]
OUT = EVIDENCE / "results" / "s5"
PRODUCT_SRC = REPO / "python" / "corpus-structure" / "src"

ENV_CMDS = ("\\begin", "\\end")
TEXT_CMDS = ("\\text", "\\mbox", "\\textrm")
LIMIT_CMDS = ("\\lim", "\\to")
INTEGRAL_CMDS = ("\\int", "\\iint", "\\oint")
SUM_CMDS = ("\\sum", "\\prod")
UNSUPPORTED_REL = ("\\mapsto", "\\Rightarrow", "\\iff", "\\implies", "\\Leftrightarrow", "\\Longrightarrow",
                   "\\leftarrow", "\\rightarrow", "\\longrightarrow", "\\Leftarrow", "\\leftrightarrow")

RESOLVE_SECONDS = 1.0
RESOLVE_BUDGET = 4.0
_STATE: dict = {}


def _init(variant: str, printer: str) -> None:
    import lark

    import s5grammar
    from mathgrammar import api, build, printer as P

    sys.path.insert(0, str(PRODUCT_SRC))
    from corpus_structure.core import tex
    from corpus_structure.core.evidence import MacroDef

    s5grammar.install(variant)
    if printer == "s5":
        from s5grammar import printer as S5P

        tree_printer = S5P.read_canonical  # (result, table)
    else:
        def tree_printer(result, table):
            return P.tree_canonical(result.tree, table)

    known_cache: dict = {}

    def known(word: str, mc) -> bool:
        k = (word, mc.key)
        if k not in known_cache:
            import re

            p = api.parser_for(mc)
            pats = _STATE.setdefault(("pats", mc.key), [re.compile(t.pattern.to_regexp()) for t in p.terminals])
            known_cache[k] = word in P.DROP or any(pt.fullmatch(word) for pt in pats)
        return known_cache[k]

    def reason(e, s, parse_fn):  # noqa: ARG001 - replaces api._reason
        out = {"error": type(e).__name__}
        pos = None
        allowed: list[str] = []
        if isinstance(e, lark.exceptions.UnexpectedCharacters):
            pos = e.pos_in_stream
            allowed = sorted(e.allowed or ())
        elif isinstance(e, lark.exceptions.UnexpectedToken):
            pos = e.token.start_pos
            allowed = sorted(e.expected or ())
        elif isinstance(e, lark.exceptions.UnexpectedEOF):
            pos = len(s)
            allowed = sorted(e.expected or ())
        tok = ""
        if pos is not None:
            for m in P.TEX_TOKEN.finditer(s):
                if m.start() <= pos < m.end():
                    tok = m.group(0)
                    break
        out.update(pos=pos, at=s[pos:pos + 16] if pos is not None else "", token=tok, allowed_n=len(allowed),
                   allowed=allowed[:12])
        mc = _STATE["mc"]
        if type(e).__name__ == "_Timeout":
            cat = "timeout"
        elif not isinstance(e, lark.exceptions.UnexpectedInput):
            cat = "internal"
            out["detail"] = str(e)[:160]
        elif isinstance(e, lark.exceptions.UnexpectedEOF) or (
                isinstance(e, lark.exceptions.UnexpectedToken) and e.token.type == "$END") or pos == len(s):
            cat = "incomplete"
        elif tok[:1] == "\\" and tok[1:].isalpha():
            if tok in ENV_CMDS:
                cat = "environment"
            elif tok in TEXT_CMDS:
                cat = "text-in-math"
            elif tok in LIMIT_CMDS:
                cat = "limit-arrow"
            elif tok in INTEGRAL_CMDS:
                cat = "integral-bounds"
            elif tok in SUM_CMDS:
                cat = "sum-bounds"
            elif tok in UNSUPPORTED_REL:
                cat = "unsupported-relation"
            elif not known(tok, mc):
                cat = "unknown-command"
            else:
                cat = "unexpected-command"
        elif tok in ("&", "\\\\"):
            cat = "alignment"
        elif tok in (",", ";", ".", ":"):
            cat = "punctuation-or-list"
        else:
            cat = "unexpected-token"
        out["category"] = cat
        return out

    api._reason = reason

    # The resolver merges readings by converting each to SymPy; that conversion runs outside the
    # parse timer, and SymPy's Eq can evaluate integrals numerically without bound (found on the
    # first full run: workers held >11 min in mpmath quadrature from transformer.eq). S5 bounds it:
    # RESOLVE_SECONDS per reading, RESOLVE_BUDGET per value; a reading not converted in time is not
    # comparable, so the ambiguity stays unresolved (reported ambiguous, never picked).
    orig_value = api._Resolver._value

    def bounded_value(self, alt):
        if _STATE["budget"] <= 0:
            _STATE["resolver_timeouts"] += 1
            return None
        t0 = time.perf_counter()
        try:
            with api._limit(min(RESOLVE_SECONDS, _STATE["budget"])):
                return orig_value(self, alt)  # swallows the timer's exception and returns None
        finally:
            dt = time.perf_counter() - t0
            _STATE["budget"] -= dt
            if dt >= min(RESOLVE_SECONDS, _STATE["budget"] + dt) - 0.01:
                _STATE["resolver_timeouts"] += 1

    api._Resolver._value = bounded_value
    _STATE.update(api=api, build=build, P=P, tex=tex, MacroDef=MacroDef, tree_printer=tree_printer)


def _work(task: tuple[str, dict, list[dict]]) -> list[dict]:
    page, macros, spans = task
    api, P, tex, MacroDef = _STATE["api"], _STATE["P"], _STATE["tex"], _STATE["MacroDef"]
    mc = api._macro_class(macros)
    _STATE["mc"] = mc
    table = mc.table()
    ptable = {n: MacroDef(nargs=s.get("nargs", 0), body=s["body"], default=s.get("default")) for n, s in macros.items()}
    rows = []
    for s in spans:
        latex = s["latex"]
        cached = (latex, "any_value", mc.full_key, "[]") in api._CACHE
        _STATE["budget"], _STATE["resolver_timeouts"] = RESOLVE_BUDGET, 0
        t0 = time.perf_counter()
        try:
            r = api.parse(latex, "any_value", mc=mc)
        except Exception as e:  # noqa: BLE001 - a crash outside the parser (resolver, occurrences)
            r = api.MathResult(latex=latex, requested="any_value", status="failed", mc=mc, source=latex,
                               reason={"error": type(e).__name__, "category": "internal", "detail": str(e)[:160]})
        ms = (time.perf_counter() - t0) * 1000
        tok_spike, unexp = P.token_form(latex, table)
        tok_product = tex.token_form(latex, ptable)
        tree = None
        trimmed = None
        if r.tree is not None:
            tree = _STATE["tree_printer"](r, table)
            if r.status == "partial":
                trimmed = P.tokens_canonical(r.latex.rstrip().rstrip(".,;").rstrip(), table)
        reason = r.reason or {}
        rows.append({
            "key": s["key"], "page": page, "kind": s["kind"], "start": s["start"], "end": s["end"],
            "delimiting": s["delimiting"], "delimiting_reason": s.get("reason"),
            "status": r.status, "detected": r.kind, "category": reason.get("category"),
            "error": reason.get("error"), "token": reason.get("token"), "at": reason.get("at"), "pos": reason.get("pos"),
            "allowed_n": reason.get("allowed_n"), "allowed": reason.get("allowed"),
            "notes": r.notes, "ms": round(ms, 2), "cached": cached,
            "resolver_timeouts": _STATE["resolver_timeouts"],
            "tokens_spike": tok_spike, "tokens_product": tok_product, "unexpanded": unexp,
            "tree": tree, "tokens_trimmed": trimmed,
        })
    return rows


def tasks(reader: str, chunk: int = 60) -> list[tuple[str, dict, list[dict]]]:
    from instruments.values import merged_macros

    rens = json.loads((OUT / "renditions.json").read_text())
    tbls = json.loads((OUT / "macro_tables.json").read_text())
    by_page: dict[str, list[dict]] = {}
    for line in (OUT / "spans.jsonl").read_text().splitlines():
        s = json.loads(line)
        by_page.setdefault(s["page"], []).append(s)
    out = []
    for page, spans in by_page.items():
        page_table = rens[page]["macros_spike_reader"] if reader == "spike" else tbls[page]["table"]
        eff = merged_macros(page_table)
        for k in range(0, len(spans), chunk):
            out.append((page, eff, spans[k:k + chunk]))
    # long display spans first, so the slowest chunks do not finish last
    out.sort(key=lambda t: -max(len(s["latex"]) for s in t[2]))
    return out


def summarize(rows: list[dict]) -> dict:
    read = [r for r in rows if r["tree"] is not None]
    st = Counter(r["status"] for r in rows)
    fails = [r for r in rows if r["status"] == "failed"]
    construct = Counter(f"{r['category']}:{r['token']}" if r["category"] in ("unknown-command", "unexpected-command", "environment")
                        else r["category"] for r in fails)
    amb = Counter()
    for r in rows:
        if r["status"] == "ambiguous":
            amb[ambiguity_cause(r["notes"])] += 1
    fresh = sorted(r["ms"] for r in rows if not r["cached"])
    return {
        "spans": len(rows), "status": dict(st),
        "status_by_kind": {k: dict(Counter(r["status"] for r in rows if r["kind"] == k)) for k in ("math_inline", "math_display")},
        "read": len(read),
        "failed_by_category": dict(Counter(r["category"] for r in fails).most_common()),
        "failed_by_construct": dict(construct.most_common(40)),
        "ambiguous_by_cause": dict(amb.most_common()),
        "detected": dict(Counter(r["detected"] for r in read)),
        "tree_eq_tokens_spike": sum(r["tree"] == r["tokens_spike"] for r in read),
        "tree_eq_tokens_product": sum(r["tree"] == r["tokens_product"] for r in read),
        "tokens_spike_eq_product": sum(r["tokens_spike"] == r["tokens_product"] for r in rows),
        "ms_fresh_n": len(fresh), "ms_median": fresh[len(fresh) // 2] if fresh else None,
        "ms_p99": fresh[int(len(fresh) * 0.99)] if fresh else None, "ms_max": fresh[-1] if fresh else None,
        "timeouts": sum(r["category"] == "timeout" for r in fails),
        "spans_with_resolver_timeouts": sum(1 for r in rows if r["resolver_timeouts"]),
    }


def ambiguity_cause(notes: list[str]) -> str:
    text = "; ".join(notes)
    if "application or product" in text or "product or application" in text:
        return "undeclared application or product"
    if "interval or pair" in text:
        return "bare interval or pair"
    if "unresolved ambiguity" in text:
        return "operator scope or other"
    return "other"


def run_name(variant: str, reader: str, printer: str = "spike") -> str:
    return f"{variant.replace(':', '-').replace(',', '+')}.{reader}" + ("" if printer == "spike" else f".{printer}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="edited")
    ap.add_argument("--reader", default="tokenizer", choices=("spike", "tokenizer"))
    ap.add_argument("--printer", default="spike", choices=("spike", "s5"))
    ap.add_argument("--workers", type=int, default=30)
    a = ap.parse_args()
    name = run_name(a.variant, a.reader, a.printer)
    (OUT / "runs").mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rows: list[dict] = []
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init, initargs=(a.variant, a.printer)) as ex:
        for part in ex.map(_work, tasks(a.reader)):
            rows.extend(part)
    order = {}
    for i, line in enumerate((OUT / "spans.jsonl").read_text().splitlines()):
        order[json.loads(line)["key"]] = i
    rows.sort(key=lambda r: order[r["key"]])
    with (OUT / "runs" / f"{name}.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    s = summarize(rows)
    s.update(variant=a.variant, reader=a.reader, printer=a.printer, wall_seconds=round(time.time() - t0, 1),
             workers=a.workers)
    (OUT / "runs" / f"{name}.summary.json").write_text(json.dumps(s, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(s, ensure_ascii=False)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
