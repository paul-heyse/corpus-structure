r"""S5-A step 1: macro tables of the 78 pages with a reader on the shared TeX tokenizer (V2).

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run --project <spike folder> --locked python code/s5_macros.py

``read_definitions`` reads ``\newcommand``, ``\renewcommand``, ``\providecommand`` (each with an
optional ``*``), then the name (``{\name}`` or ``\name``), an optional ``[n]``, an optional default
``[...]`` and the body, as TeX reads undelimited arguments (D4 M01), and
``\DeclareMathOperator[*]{\name}{text}`` as an operator (body ``\operatorname{text}``, with ``*``
``\operatorname*{text}``). Tokens are ``mathgrammar.printer.tex_tokens`` (TeX's rules, the token
form's tokenizer). ``\def`` / ``\let`` / ``\DeclareMathOperator`` occurrences are counted.

Inputs: results/s5/renditions.json (``latex_blocks``, ``macros_spike_reader``), results/s5/spans.jsonl.
Writes results/s5/macro_tables.json (per page: the tokenizer reader's table, what the spike reader
missed or read differently, the effective tables under both readers and whether they differ) and
results/s5/macros.tsv (every control word used in math spans: count, pages, source, expansion,
differing bodies).
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))

from mathgrammar.printer import tex_tokens  # noqa: E402

EVIDENCE = CODE.parent
OUT = EVIDENCE / "results" / "s5"
DEFINERS = ("\\newcommand", "\\renewcommand", "\\providecommand")


def _skip(t: list[str], i: int) -> int:
    while i < len(t) and t[i].isspace():
        i += 1
    return i


def _group(t: list[str], i: int) -> tuple[list[str], int]:
    """At ``{``: the group's inner tokens and the index after its ``}``; else one token."""
    i = _skip(t, i)
    if i >= len(t):
        return [], i
    if t[i] != "{":
        return [t[i]], i + 1
    depth = 0
    for k in range(i, len(t)):
        depth += t[k] == "{"
        depth -= t[k] == "}"
        if depth == 0:
            return t[i + 1:k], k + 1
    return t[i + 1:], len(t)


def _optional(t: list[str], i: int) -> tuple[list[str] | None, int]:
    """``[...]`` (brackets inside braces do not close it) at ``i``, else None."""
    j = _skip(t, i)
    if j >= len(t) or t[j] != "[":
        return None, i
    depth = 0
    for k in range(j + 1, len(t)):
        depth += t[k] == "{"
        depth -= t[k] == "}"
        if depth == 0 and t[k] == "]":
            return t[j + 1:k], k + 1
    return None, i


def read_definitions(src: str) -> tuple[list[dict], Counter]:
    """Definitions in source order: {command, name, nargs, default, body}; and counts of other
    definition commands met (\\def, \\let, \\DeclareMathOperator...)."""
    t = tex_tokens(src)
    defs, other = [], Counter()
    i = 0
    while i < len(t):
        tok = t[i]
        if tok in DEFINERS:
            j = _skip(t, i + 1)
            star = j < len(t) and t[j] == "*"
            if star:
                j += 1
            name_toks, j = _group(t, j)
            name_toks = [x for x in name_toks if not x.isspace()]
            nargs_toks, j = _optional(t, j)
            default = None
            if nargs_toks is not None:
                default_toks, j2 = _optional(t, j)
                if default_toks is not None:
                    default, j = "".join(default_toks), j2
            body, j = _group(t, j)
            nargs = int("".join(nargs_toks).strip()) if nargs_toks and "".join(nargs_toks).strip().isdigit() else 0
            if len(name_toks) == 1 and name_toks[0].startswith("\\"):
                defs.append({"command": tok + ("*" if star else ""), "name": name_toks[0], "nargs": nargs,
                             "default": default, "body": "".join(body)})
            else:
                other[f"{tok} with unreadable name"] += 1
            i = j
            continue
        if tok == "\\DeclareMathOperator":
            j = _skip(t, i + 1)
            star = j < len(t) and t[j] == "*"
            if star:
                j += 1
            name_toks, j = _group(t, j)
            body, j = _group(t, j)
            name_toks = [x for x in name_toks if not x.isspace()]
            other["\\DeclareMathOperator"] += 1
            if len(name_toks) == 1:
                defs.append({"command": tok + ("*" if star else ""), "name": name_toks[0], "nargs": 0, "default": None,
                             "body": ("\\operatorname*{" if star else "\\operatorname{") + "".join(body) + "}"})
            i = j
            continue
        if tok in ("\\def", "\\gdef", "\\edef", "\\xdef", "\\let", "\\DeclareRobustCommand"):
            other[tok] += 1
        i += 1
    return defs, other


def table_from(defs: list[dict]) -> tuple[dict, list[str]]:
    """TeX's semantics: \\newcommand of a defined name is an error (kept first, reported);
    \\renewcommand replaces; \\providecommand defines only an undefined name."""
    table, notes = {}, []
    for d in defs:
        spec = {"nargs": d["nargs"], "body": d["body"]}
        if d["default"] is not None:
            spec["default"] = d["default"]
        base = d["command"].rstrip("*")
        if base == "\\providecommand" and d["name"] in table:
            continue
        if base == "\\newcommand" and d["name"] in table:
            notes.append(f"{d['name']} redefined by \\newcommand (TeX error; first kept)")
            continue
        if base == "\\renewcommand" and d["name"] not in table:
            notes.append(f"{d['name']} \\renewcommand without a prior definition on the page")
        table[d["name"]] = spec
    return table, notes


def effective(page_table: dict) -> dict:
    from instruments.values import merged_macros

    return merged_macros(page_table)


def main() -> int:
    from mathgrammar import build

    rens = json.loads((OUT / "renditions.json").read_text())
    tables, per_page = {}, {}
    totals = Counter()
    for page, r in rens.items():
        defs, other = [], Counter()
        for blk in r["latex_blocks"]:
            d, o = read_definitions(blk)
            defs += d
            other += o
        tbl, notes = table_from(defs)
        spike = r["macros_spike_reader"]
        missed = sorted(set(tbl) - set(spike))
        differ = sorted(n for n in set(tbl) & set(spike) if {k: v for k, v in tbl[n].items()} != spike[n])
        extra = sorted(set(spike) - set(tbl))
        eff_new, eff_spike = effective(tbl), effective(spike)
        for d in defs:
            totals[d["command"]] += 1
        totals.update(other)
        tables[page] = tbl
        per_page[page] = {"definitions": len(defs), "by_command": dict(Counter(d["command"] for d in defs)),
                          "other_definers": dict(other), "notes": notes, "table": tbl,
                          "spike_missed": {n: tbl[n] for n in missed}, "spike_differs": differ, "spike_only": extra,
                          "effective_differs": eff_new != eff_spike,
                          "effective_diff": sorted(n for n in set(eff_new) | set(eff_spike) if eff_new.get(n) != eff_spike.get(n)),
                          "classification_key_new": build.classify(eff_new).key,
                          "classification_key_spike": build.classify(eff_spike).key,
                          "full_key_new": build.classify(eff_new).full_key,
                          "full_key_spike": build.classify(eff_spike).full_key}
    (OUT / "macro_tables.json").write_text(json.dumps(per_page, indent=1, ensure_ascii=False) + "\n")

    # ---- macros.tsv: every control word in math spans
    from mathgrammar.printer import tex_tokens as tt
    from instruments.values import FALLBACK_MACROS

    uses = defaultdict(Counter)  # name -> page -> count
    for line in (OUT / "spans.jsonl").read_text().splitlines():
        s = json.loads(line)
        for tok in tt(s["latex"]):
            if len(tok) > 2 and tok[0] == "\\" and tok[1:].isalpha() or (len(tok) == 2 and tok[0] == "\\" and tok[1].isalpha()):
                uses[tok][s["page"]] += 1
    known = grammar_commands()
    rows = []
    for name in sorted(uses, key=lambda n: (-sum(uses[n].values()), n)):
        pages = uses[name]
        defining = {p: tables[p][name] for p in pages if name in tables[p]}
        n_ren = sum(c for p, c in pages.items() if p in defining)
        n_fb = sum(c for p, c in pages.items() if p not in defining) if name in FALLBACK_MACROS else 0
        n_fb_spike = (sum(c for p, c in pages.items() if name not in rens[p]["macros_spike_reader"])
                      if name in FALLBACK_MACROS else 0)
        bodies = Counter(json.dumps(v, sort_keys=True) for v in defining.values())
        if defining or name in FALLBACK_MACROS:
            source = "rendition" if n_fb == 0 else ("fallback" if n_ren == 0 else "rendition+fallback")
            exp = "; ".join(f"{json.loads(b)['body']} ({c} pages)" for b, c in bodies.most_common())
            if n_fb:
                exp = (exp + "; " if exp else "") + f"fallback {FALLBACK_MACROS[name]}"
        elif name in known:
            source, exp = "grammar", "(command read by the grammar)"
        else:
            source, exp = "none", "unmapped"
        fb_body = FALLBACK_MACROS.get(name)
        all_bodies = {json.loads(b)["body"] for b in bodies} | ({fb_body} if n_fb else set())
        rows.append({"macro": name, "count": sum(pages.values()), "pages": len(pages), "count_rendition": n_ren,
                     "count_fallback": n_fb,
                     "count_fallback_spike_reader": n_fb_spike, "source": source, "expansion": exp,
                     "differing_bodies": "yes" if len(all_bodies) > 1 else ("" if all_bodies else "")})
    with (OUT / "macros.tsv").open("w", encoding="utf-8") as fh:
        fh.write("\t".join(rows[0]) + "\n")
        for r in rows:
            fh.write("\t".join(str(v) for v in r.values()) + "\n")
    summary = {
        "pages": len(rens),
        "definitions_by_command": dict(totals),
        "pages_where_spike_missed": {p: sorted(v["spike_missed"]) for p, v in per_page.items() if v["spike_missed"]},
        "pages_where_spike_differs": {p: v["spike_differs"] for p, v in per_page.items() if v["spike_differs"]},
        "pages_spike_only": {p: v["spike_only"] for p, v in per_page.items() if v["spike_only"]},
        "pages_effective_table_differs": sorted(p for p, v in per_page.items() if v["effective_differs"]),
        "pages_parser_key_differs": sorted(p for p, v in per_page.items() if v["classification_key_new"] != v["classification_key_spike"]),
        "notes": {p: v["notes"] for p, v in per_page.items() if v["notes"]},
        "uses_from_fallback_spike_reader": {r["macro"]: r["count_fallback_spike_reader"] for r in rows if r["count_fallback_spike_reader"]},
        "distinct_definitions": len({(n, json.dumps(s, sort_keys=True)) for t in tables.values() for n, s in t.items()}),
        "distinct_names": len({n for t in tables.values() for n in t}),
        "control_words_in_math": len(rows),
        "by_source": dict(Counter(r["source"] for r in rows)),
        "uses_by_source": {k: sum(r["count"] for r in rows if r["source"] == k) for k in sorted({r["source"] for r in rows})},
        "unmapped": [(r["macro"], r["count"], r["pages"]) for r in rows if r["source"] == "none"],
        "differing_bodies": [(r["macro"], r["expansion"]) for r in rows if r["differing_bodies"]],
        "with_arguments": sorted({(n, s["nargs"]) for t in tables.values() for n, s in t.items() if s["nargs"]}),
    }
    (OUT / "macros_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=1, ensure_ascii=False)[:6000])
    return 0


def grammar_commands() -> set[str]:
    """Control words some terminal of the assembled grammar (edited terminals, empty macro table)
    matches as a whole token, or that the drop list removes."""
    import re

    from mathgrammar import build
    from mathgrammar.printer import DROP
    from s5grammar import build_parser

    p = build_parser("edited", build.classify({}))
    pats = [re.compile(t.pattern.to_regexp()) for t in p.terminals]
    words = set()
    for line in (OUT / "spans.jsonl").read_text().splitlines():
        for tok in tex_tokens(json.loads(line)["latex"]):
            if tok[:1] == "\\" and tok[1:].isalpha():
                words.add(tok)
    return {w for w in words if w in DROP or any(pt.fullmatch(w) for pt in pats)}


if __name__ == "__main__":
    sys.exit(main())
