"""S0-E: rule-based symbol scoping (D4 M13) over the core units, compared with annotated scopes.

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/s0e_m13_probe.py STORED_DIR [--sections h3h4|h3]

Symbols come from S1's math segments through pylatexenc 3.0b2 nodes; binding sites and extents
follow D4 M13 with D2 §12.1's binder lexicon. For every local entity with a symbol in the given
stored batches (the S0 reference, or the trace), the probe's binding is compared with the
annotated extent. Writes results/s0/m13_probe[.<sections>].tsv.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from pylatexenc.latexnodes.nodes import LatexCharsNode, LatexGroupNode, LatexMacroNode, LatexSpecialsNode
from pylatexenc.latexnodes.parsers import LatexGeneralNodesParser
from pylatexenc.latexwalker import LatexWalker

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
from s0a_packets import BINDERS  # noqa: E402
from s1_adapter import adapt, prose_safe_state  # noqa: E402
from s1_sentences import sentences  # noqa: E402

EVIDENCE = CODE.parent
SAMPLE = json.loads((EVIDENCE / "sample.json").read_text())
GREEK = {"alpha", "beta", "gamma", "delta", "epsilon", "theta", "kappa", "lambda", "mu", "nu", "xi", "pi", "rho",
         "sigma", "tau", "phi", "chi", "psi", "omega", "Gamma", "Phi", "Sigma", "Omega", "Lambda"}
SKIP_ARGS = {"text", "mathbb", "mathscr", "mathrm", "operatorname", "begin", "end", "frac", "sqrt"}
CONSTANTS = {"e", "pi", "i", "d"}


def symbols(tex: str) -> list[tuple[str, int]]:
    """Identifier occurrences (name, offset in tex): single letters and Greek macros, with subscripts."""
    w = LatexWalker(tex, tolerant_parsing=True)
    nodes, _ = w.parse_content(LatexGeneralNodesParser(), parsing_state=prose_safe_state(w))
    out: list[tuple[str, int]] = []

    def visit(nodelist):
        prev = None
        for n in nodelist or []:
            if isinstance(n, LatexCharsNode):
                for k, ch in enumerate(n.chars):
                    if ch.isalpha():
                        out.append((ch, n.pos + k))
                        prev = len(out) - 1
                    else:
                        prev = None if not ch.isspace() else prev
            elif isinstance(n, LatexMacroNode):
                if n.macroname in GREEK:
                    out.append(("\\" + n.macroname, n.pos))
                    prev = len(out) - 1
                elif n.macroname in SKIP_ARGS:
                    prev = None
                else:
                    for a in (n.nodeargd.argnlist if n.nodeargd else []) or []:
                        if a is not None:
                            visit(getattr(a, "nodelist", None) or [a])
                    prev = None
            elif isinstance(n, LatexSpecialsNode) and n.specials_chars == "_" and prev is not None:
                arg = (n.nodeargd.argnlist[0] if n.nodeargd and n.nodeargd.argnlist else None)
                sub = arg.latex_verbatim().strip("{}") if arg is not None else ""
                name, pos = out[prev]
                out[prev] = (f"{name}_{sub}", pos)
            elif isinstance(n, LatexGroupNode):
                visit(n.nodelist)
                prev = None
            else:
                inner = getattr(n, "nodelist", None)
                if inner:
                    visit(inner)
    visit(nodes)
    return [(s, p) for s, p in out if s not in CONSTANTS]


def norm(sym: str) -> str:
    return sym.replace("\\", "").replace("{", "").replace("}", "").replace(" ", "")


def probe_page(page: str, sections_mode: str, clause_binders: bool = False, if_binder: bool = False,
               paragraph_statements: bool = False, sample_parts: list | None = None) -> dict:
    r = adapt(page, {"sections": sections_mode})
    text, segs = r["text"], r["segments"]
    sents = sentences(r, "P1", "bp+c")
    by_key = {s["key"]: s for s in segs}
    units = [s for s in segs if s["kind"] == "unit"]
    secs = [s for s in segs if s["kind"] == "section"]
    maths = [s for s in segs if s["kind"].startswith("math")]
    mentions = []  # (symbol, offset, sentence)
    for m in maths:
        for sym, off in symbols(text[m["start"]:m["end"]]):
            pos = m["start"] + off
            sent = next((s for s in sents if s["start"] <= pos < s["end"]), None)
            mentions.append({"symbol": norm(sym), "pos": pos, "sentence": sent, "math": m})
    def unit_of(pos):
        return next((u for u in units if u["start"] <= pos < u["end"]), None)
    def section_of(pos):
        inside = [s for s in secs if s["start"] <= pos < s["end"]]
        return min(inside, key=lambda s: s["end"] - s["start"]) if inside else None
    sites = []
    for mn in mentions:
        s = mn["sentence"]
        if not s:
            continue
        st = text[s["start"]:s["end"]]
        words = re.findall(r"[A-Za-z]+", st.lower())
        first = words[0] if words else ""
        initial = BINDERS["sentence_initial"] + (["if"] if if_binder else [])
        binder = first in initial or any(p in st.lower() for p in BINDERS["section_wide"])
        clause = re.search(r"\b(" + "|".join(BINDERS["clause"]) + r")\b", st[: mn["pos"] - s["start"]].lower())
        mtex = text[mn["math"]["start"]:mn["math"]["end"]]
        rel = mn["pos"] - mn["math"]["start"]
        left_of = any(op in mtex[rel:] for op in ("\\in", "=", "\\le", "\\lt", "\\gt", "\\ge"))
        only = len(symbols(mtex)) <= 2
        syms = symbols(mtex)
        definitional = bool(syms) and syms[0][1] == rel and re.match(r"\\[\(\[]\s*[A-Za-z\\_{}0-9]+\s*=", mtex) is not None
        if clause_binders and not binder:  # variant: a binder word anywhere before the mention in its sentence
            before = st[: mn["pos"] - s["start"]].lower()
            binder = any(re.search(rf"\b{w}\b", before) for w in BINDERS["sentence_initial"])
        if (binder and (left_of or only)) or (clause and "\\in" in mtex[rel:]) or definitional:
            u = unit_of(mn["pos"])
            section_wide = any(w in st.lower() for w in BINDERS["section_wide"]) or "again" in st.lower()
            if u is None and paragraph_statements and not section_wide:  # a standalone paragraph is a statement
                u = next((p for p in (sample_parts or []) if p["start"] <= mn["pos"] < p["end"]), None)
            if u:
                extent = ("statement", u["start"], u["end"], u["key"])
            else:
                sec = section_of(mn["pos"])
                extent = ("section", mn["pos"], sec["end"] if sec else len(text), sec["key"] if sec else None)
            again = "again" in st.lower()
            sites.append({"symbol": mn["symbol"], "pos": mn["pos"], "extent": extent, "again": again,
                          "sentence": st[:100]})
    # "Suppose again" re-opens the previous section-level binding of the symbol
    for s in sites:
        if s["again"]:
            prev = [p for p in sites if p["symbol"] == s["symbol"] and p["pos"] < s["pos"] and p["extent"][0] == "section"]
            if prev:
                s["reopens"] = prev[-1]["sentence"][:60]
    return {"text": text, "mentions": mentions, "sites": sites, "units": units}


def assign(pg: dict, symbol: str, ranges: list[tuple[int, int]]) -> dict:
    """Each mention of the symbol inside the unit goes to the innermost binding site at or before it
    whose extent contains it (D4 M13 rule 3); the unit's binding is that of its first mention."""
    mentions = sorted(m["pos"] for m in pg["mentions"] if m["symbol"] == symbol
                      and any(a <= m["pos"] < e for a, e in ranges))
    for pos in mentions:
        cands = [s for s in pg["sites"] if s["symbol"] == symbol and s["pos"] <= pos
                 and s["extent"][1] <= pos < s["extent"][2] or (s["symbol"] == symbol and s["pos"] == pos)]
        if cands:
            best = min(cands, key=lambda s: s["extent"][2] - s["extent"][1])
            return {"binding": best["extent"][0], "site": best["sentence"], "reopens": best.get("reopens"),
                    "mentions": len(mentions)}
    return {"binding": "unresolved", "mentions": len(mentions)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stored", type=Path)
    ap.add_argument("--sections", default="h3h4")
    ap.add_argument("--clause-binders", action="store_true")
    ap.add_argument("--if-binder", action="store_true", help="variant: sentence-initial \"if\" binds")
    ap.add_argument("--paragraph-statements", action="store_true",
                    help="variant: a sample paragraph outside any unit is a statement extent")
    a = ap.parse_args()
    pages: dict = {}
    rows = []
    for f in sorted(a.stored.glob("*.json")):
        if f.stem not in SAMPLE["units"]:
            continue
        b = json.loads(f.read_text())
        meta = SAMPLE["units"][f.stem]
        parts = [{"start": p["start"], "end": p["end"], "key": p["segment_key"]} for m in SAMPLE["units"].values()
                 if m["page"] == meta["page"] for p in m["parts"]]
        pg = pages.setdefault(meta["page"], probe_page(meta["page"], a.sections, a.clause_binders, a.if_binder,
                                                       a.paragraph_statements, parts))
        for e in b.get("entities", []):
            if e.get("scope") != "local" or not e.get("symbol"):
                continue
            sym = norm(e["symbol"])
            got = assign(pg, sym, [(p["start"], p["end"]) for p in meta["parts"]])
            annotated = e.get("extent") or "?"
            # an expression entity (a + b X, \prod X_i), not a symbol: outside M13's scope rules
            expression = (len(symbols(f"\\({e['symbol']}\\)")) > 1
                          or re.search(r"[+*/^-]|\\(prod|sum|frac)\b", e["symbol"]) is not None)
            rows.append({"unit": f.stem, "symbol": e["symbol"], "type": e["type"], "expression": expression,
                         "annotated_extent": annotated,
                         "probe": got["binding"], "match": got["binding"] == annotated,
                         "probe_site": (got.get("site") or "")[:90], "reopens": got.get("reopens") or ""})
    tag = (f"{a.sections}{'.clause' if a.clause_binders else ''}{'.if' if a.if_binder else ''}"
           f"{'.para' if a.paragraph_statements else ''}")
    out = EVIDENCE / "results" / "s0" / f"m13_probe.{a.stored.name}.{tag}.tsv"
    with out.open("w", encoding="utf-8") as fh:
        fh.write("\t".join(rows[0]) + "\n")
        for r in rows:
            fh.write("\t".join(str(v).replace("\t", " ").replace("\n", " ") for v in r.values()) + "\n")
    ok = sum(r["match"] for r in rows)
    sym = [r for r in rows if not r["expression"]]
    print(f"{ok}/{len(rows)} local-entity extents reproduced by the M13 rules ({tag}); "
          f"symbols only: {sum(r['match'] for r in sym)}/{len(sym)}")
    for r in rows:
        print(" ", r["unit"], r["symbol"], r["annotated_extent"], "->", r["probe"], "|", r["probe_site"][:70])
    return 0


if __name__ == "__main__":
    sys.exit(main())
