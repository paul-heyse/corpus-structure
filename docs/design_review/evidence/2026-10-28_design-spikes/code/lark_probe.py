"""Lark probe (2026-10-28): can SymPy 1.14's Lark LaTeX grammar be *extended* (Lark %extend,
extra start symbols) instead of rewriting strings around it (the instruments' shim)?

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/lark_probe.py [--sample 1500]

Inputs: every LaTeX value in the S0 stored batches (passes A, B, P, reference, trace: formula and
set objects, qualifier values, condition operands) and a seeded sample of S1 math spans (78 pages).
Parsers: "sympy" = SymPy's grammar as shipped (Earley, explicit ambiguity, as LarkLaTeXParser
builds it); "extended" = the same grammar text plus EXTENSION below. Recognition only (no SymPy
transformation). Per input: ok / ambiguous (an `_ambig` node) / failed (exception class and the
offending token), and for "extended" which start symbol accepted it. A 2 s limit per parse.
Writes results/lark_probe/{values,spans}.tsv and summary.json.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import signal
import sys
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

import lark
import sympy.parsing.latex.lark as slark

CODE = Path(__file__).resolve().parent
EVIDENCE = CODE.parent
S0 = EVIDENCE / "results" / "s0"
S1 = EVIDENCE / "results" / "s1"
OUT = EVIDENCE / "results" / "lark_probe"
GRAMMAR_DIR = Path(slark.__file__).parent / "grammar"

# Extension of SymPy's grammar, by Lark directives only (no edits to the shipped text).
EXTENSION = r"""
// ---- corpus-structure extension (probe) ----
SIGMA: "\\sigma" | "\\varsigma"
IOTA: "\\iota"
%extend GREEK_SYMBOL: SIGMA | IOTA
UPPER_GREEK: "\\Gamma" | "\\Delta" | "\\Theta" | "\\Lambda" | "\\Xi" | "\\Pi" | "\\Sigma"
    | "\\Upsilon" | "\\Phi" | "\\Psi" | "\\Omega"
CMD_PI: "\\pi"
%extend LT: "\\lt"
%extend GT: "\\gt"
%extend BAR: "\\lvert" | "\\rvert" | "\\vert" | "\\mid"
%ignore "\\," | "\\ "

// page operators (D2 §12.1 macro map; per-rendition macros, HTML-06): applied to () or []
PAGE_OP: "\\E" | "\\var" | "\\P" | "\\sd" | "\\cov" | "\\cor" | "\\skw" | "\\kur" | "\\mse" | "\\sgn"
page_op_applied: PAGE_OP (L_PAREN (_relation | list_of_expressions | conditional) R_PAREN
                        | L_BRACKET (_expression | conditional) R_BRACKET)
conditional: _expression BAR (_relation | _expression)
// named functions applied: upper-case Greek (\Phi(x), \Gamma(k)) and Greek letters (\phi(z))
greek_applied: (UPPER_GREEK | GREEK_SYMBOL) L_PAREN list_of_expressions R_PAREN
%extend _function: page_op_applied | greek_applied
upper_greek_symbol: UPPER_GREEK
pi_constant: CMD_PI
text_atom: "\\text" L_BRACE /[^{}]+/ R_BRACE
%extend _atomic_expr: upper_greek_symbol | pi_constant | text_atom

// sets (D2 §9 SetExpr) as their own start symbol
SET_CONST: "\\R" | "\\N" | "\\Z" | "\\Q" | "\\mathbb{R}" | "\\mathbb{N}" | "\\mathbb{Z}"
CMD_SETMINUS: "\\setminus"
CMD_CUP: "\\cup"
CMD_CAP: "\\cap"
CMD_LDOTS: "\\ldots" | "\\dots" | "\\cdots"
CMD_IN: "\\in"
CMD_NOTIN: "\\notin"
L_SET: "\\{"
R_SET: "\\}"
set_const: SET_CONST (UNDERSCORE ("+" | L_BRACE "+" R_BRACE))? (CARET _expression_core)?
interval: (L_PAREN | L_BRACKET) _expression "," _expression (R_PAREN | R_BRACKET)
set_list: L_SET _set_item ("," _set_item)* R_SET
_set_item: _expression | CMD_LDOTS
set_builder: L_SET _expression (COLON | BAR) _set_condition R_SET
_set_condition: _relation | member | _set_condition "," _set_condition
?set_expr: set_atom | set_expr CMD_SETMINUS set_atom -> set_minus
    | set_expr CMD_CUP set_atom -> set_union | set_expr CMD_CAP set_atom -> set_intersection
?set_atom: set_const | interval | set_list | set_builder | L_PAREN set_expr R_PAREN
member: _expression (CMD_IN | CMD_NOTIN) set_expr
// formula positions as the instruments see them: a formula, a relation, a membership, a set
any_value: _relation | _expression | member | set_expr
"""


class _Timeout(Exception):
    pass


@contextmanager
def limit(seconds: float):
    def handler(signum, frame):  # noqa: ARG001
        raise _Timeout()

    old = signal.signal(signal.SIGALRM, handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def build(extended: bool) -> lark.Lark:
    text = (GRAMMAR_DIR / "latex.lark").read_text(encoding="utf-8")
    starts = ["latex_string"]
    if extended:
        text += EXTENSION
        starts = ["latex_string", "set_expr", "member", "any_value"]
    return lark.Lark(text, source_path=str(GRAMMAR_DIR) + "/", parser="earley", start=starts,
                     lexer="auto", ambiguity="explicit", propagate_positions=True,
                     maybe_placeholders=False, keep_all_tokens=True)


def attempt(parser: lark.Lark, s: str, start: str) -> dict:
    try:
        with limit(2.0):
            tree = parser.parse(s, start=start)
    except _Timeout:
        return {"status": "timeout"}
    except lark.exceptions.UnexpectedCharacters as e:
        return {"status": "failed", "error": "UnexpectedCharacters", "at": s[e.pos_in_stream:e.pos_in_stream + 12]}
    except lark.exceptions.UnexpectedToken as e:
        return {"status": "failed", "error": "UnexpectedToken", "at": str(e.token)[:12] or "<EOF>"}
    except lark.exceptions.UnexpectedEOF:
        return {"status": "failed", "error": "UnexpectedEOF", "at": "<EOF>"}
    except Exception as e:  # noqa: BLE001 - recorded, never hidden
        return {"status": "failed", "error": type(e).__name__, "at": str(e)[:30]}
    amb = sum(1 for _ in tree.find_data("_ambig"))
    return {"status": "ambiguous" if amb else "ok", "ambig_nodes": amb}


def run(parser: lark.Lark, s: str, starts: list[str]) -> dict:
    last = None
    for st in starts:
        r = attempt(parser, s, st)
        r["start"] = st
        if r["status"] in ("ok", "ambiguous"):
            return r
        last = last or r
    return last


def strip_delims(t: str) -> str:
    t = t.strip()
    for a, b in (("\\(", "\\)"), ("\\[", "\\]")):
        if t.startswith(a) and t.endswith(b):
            return t[2:-2].strip()
    return t


def batch_values() -> list[tuple[str, str]]:
    out = set()

    def walk(o, where):
        if isinstance(o, dict):
            if o.get("t") in ("formula", "set") and isinstance(o.get("latex"), str):
                out.add((o["t"], o["latex"]))
            for k in ("x", "lhs", "rhs") if o.get("op") in ("member", "cmp") else ():
                if isinstance(o.get(k), str):
                    out.add(("cond_operand", o[k]))
            if o.get("op") == "member" and isinstance(o.get("set"), str):
                out.add(("set", o["set"]))
            for v in o.values():
                walk(v, where)
        elif isinstance(o, list):
            for v in o:
                walk(v, where)

    for d in [S0 / "reference", S0 / "trace_stored", *(S0 / "stored").glob("pass_*")]:
        for f in d.glob("[TU]*.json"):
            walk(json.loads(f.read_text()), d.name)
    return sorted(out)


def corpus_spans(n: int) -> list[tuple[str, str]]:
    spans = []
    for f in sorted((S1 / "segments").glob("*.jsonl")):
        text = (S1 / "canonical" / f"{f.stem}.txt").read_text(encoding="utf-8")
        for line in f.read_text().splitlines():
            s = json.loads(line)
            if s["kind"].startswith("math"):
                spans.append((s["kind"], strip_delims(text[s["start"]:s["end"]])))
    random.Random(20261028).shuffle(spans)
    return spans[:n]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=1500)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    base, ext = build(False), build(True)
    summary = {"lark": lark.__version__}
    for name, items in (("values", batch_values()), ("spans", corpus_spans(a.sample))):
        rows = []
        for kind, s in items:
            rb = run(base, s, ["latex_string"])
            starts = (["set_expr", "member", "any_value"] if kind == "set" else ["latex_string", "member", "set_expr", "any_value"])
            rx = run(ext, s, starts)
            rows.append({"kind": kind, "latex": s, "sympy": rb["status"], "sympy_error": rb.get("error", ""),
                         "sympy_at": rb.get("at", ""), "extended": rx["status"], "extended_start": rx.get("start", ""),
                         "extended_error": rx.get("error", ""), "extended_at": rx.get("at", ""),
                         "extended_ambig_nodes": rx.get("ambig_nodes", "")})
        with (OUT / f"{name}.tsv").open("w", encoding="utf-8") as fh:
            fh.write("\t".join(rows[0]) + "\n")
            for r in rows:
                fh.write("\t".join(str(v).replace("\t", " ").replace("\n", " ") for v in r.values()) + "\n")
        summary[name] = {
            "n": len(rows),
            "sympy": dict(Counter(r["sympy"] for r in rows)),
            "extended": dict(Counter(r["extended"] for r in rows)),
            "extended_by_start": dict(Counter(r["extended_start"] for r in rows if r["extended"] in ("ok", "ambiguous"))),
            "sympy_fail_tokens": Counter(re.sub(r"[{(\[].*", "", r["sympy_at"]) for r in rows if r["sympy"] == "failed").most_common(15),
            "extended_fail_tokens": Counter(re.sub(r"[{(\[].*", "", r["extended_at"]) for r in rows if r["extended"] == "failed").most_common(15),
        }
        print(name, json.dumps(summary[name], ensure_ascii=False))
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
