"""P2 (2026-10-28): math-span checks over the 78 first-pass pages (S1 adapter, its default configuration).

    cd docs/design_review/evidence/2026-10-28_design-spikes
    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python ../2026-10-28_library-text-math/p2_math_checks.py

1. Which `partial` math segments come from pylatexenc's balance check rather than from delimiting.
2. Whether a brace / \\begin-\\end check over TeX tokens (the tokenizer the token canonical form
   already uses, mathgrammar.printer.tex_tokens) flags any span, and which.
3. How often the printer's dropped-command set (_DROP, read from the shipped grammar's %ignore lines)
   misses the sizing commands the extension ignores, i.e. where tokens_canonical keeps \\big etc.
4. Named-list delimiter pattern (regex \\L<...>) against s1_adapter.scan_math on every text run.
Read-only; prints a JSON summary.
"""
import csv, json, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPIKE = HERE.parent / "2026-10-28_design-spikes" / "code"
sys.path.insert(0, str(SPIKE))
import regex  # noqa: E402
import s1_adapter as A  # noqa: E402
from mathgrammar import printer  # noqa: E402

REPO = HERE.parents[3]
pages = [r["path"] for r in csv.DictReader((REPO / "docs/statistics_corpus/index/siegrist_sections.tsv").open(), delimiter="\t")
         if r["first_pass"] == "yes"]

SIZING = regex.compile(r"\\(?:big|Big|bigg|Bigg)[lrm]?(?![A-Za-z])")


def token_check(tex: str) -> str | None:
    toks = [t for t in printer.tex_tokens(tex) if not t.isspace()]
    depth, envs = 0, []
    i = 0
    while i < len(toks):
        t = toks[i]
        if t == "{":
            depth += 1
        elif t == "}":
            depth -= 1
            if depth < 0:
                return "unmatched }"
        elif t in ("\\begin", "\\end") and i + 3 < len(toks) + 1:
            j = i + 1
            name = ""
            if j < len(toks) and toks[j] == "{":
                k = j + 1
                while k < len(toks) and toks[k] != "}":
                    name += toks[k]
                    k += 1
            if t == "\\begin":
                envs.append(name)
            elif not envs or envs.pop() != name:
                return f"\\end{{{name}}} without matching \\begin"
        i += 1
    if depth:
        return "unclosed {"
    if envs:
        return f"unclosed \\begin{{{envs[-1]}}}"
    return None


# named-list version of the delimiter pattern (Siegrist profile delimiters)
NL = regex.compile(r"""(?V1)
    \\\\ (*SKIP)(*F)
  | (?P<env>\\begin\{(?P<name>\L<envs>)\}) .*? (?P<envend>\\end\{(?P=name)\} | \Z)
  | (?P<open>\L<opens>) (?P<body>(?:\\\\ | (?!\L<delims>) .)*+) (?P<close>\L<closes>)?
  | (?P<stray>\L<closes>)
""", regex.VERBOSE | regex.DOTALL, opens=["\\(", "\\["], closes=["\\)", "\\]"],
                   delims=["\\(", "\\[", "\\)", "\\]"], envs=["align", "align*"])

if "--b" in sys.argv:
    pages = []
out = Counter()
flagged, partial_reasons = [], Counter()
sizing_spans = 0
pattern_diff = []
for p in pages:
    r = A.adapt(p)
    text = r["text"]
    for s in r["segments"]:
        if not s["kind"].startswith("math"):
            continue
        out["math_spans"] += 1
        tex = text[s["start"]:s["end"]]
        if s["parse_status"] == "partial":
            partial_reasons["pylatexenc" if (s.get("reason") or "").startswith("pylatexenc") else (s.get("reason") or "")] += 1
        tc = token_check(tex)
        if tc:
            flagged.append({"page": p, "status": s["parse_status"], "reason": s.get("reason"), "token_check": tc, "tex": tex[:90]})
        if SIZING.search(tex):
            sizing_spans += 1
            if "\\big" in printer.tokens_canonical(tex, {}) or "\\Big" in printer.tokens_canonical(tex, {}):
                out["tokens_canonical_keeps_sizing"] += 1
print(json.dumps({"pages": len(pages), "counts": dict(out), "partial_reasons": dict(partial_reasons),
                  "token_check_flags": len(flagged), "flag_examples": flagged[:12], "spans_with_sizing": sizing_spans,
                  "printer_DROP_has_big": "\\big" in printer._DROP}, indent=1, ensure_ascii=False))


def part_b():
    """Named-list pattern vs scan_math on the spike pages' exported blocks; malformed-input checks."""
    same = diff = 0
    for f in sorted((SPIKE.parent / "results" / "s1" / "blocks").glob("*.jsonl")):
        for line in f.read_text().splitlines():
            s = json.loads(line)["text"]
            ref, _ = A.scan_math(s, {"inline": ["\\(", "\\)"], "display": ["\\[", "\\]"], "display_environments": ["align", "align*"]})
            got = [(m.start(), m.end()) for m in NL.finditer(s, timeout=1.0) if not m.group("stray")]
            same += got == [(x["start"], x["end"]) for x in ref]
            diff += got != [(x["start"], x["end"]) for x in ref]
    pre = regex.compile(r"\L<d>", d=["$", "$$"])
    bad = [r"\(\frac{a}{b\)", r"\(a}\)", r"\(\begin{cases} a \)", r"\(\end{cases}\)", r"\(\left( a \)",
           r"\(\frac{a}\)", r"\(x^\)", r"\(\sqrt\)", r"\(a & b\)", r"\(\begin{cases} a \end{array}\)"]
    ctx = A.latex_context({})
    rows = [{"tex": b, "pylatexenc": A.validate_span(b, ctx)[0], "token_check": token_check(b)} for b in bad]
    return {"named_list_pattern_blocks_same": same, "blocks_different": diff,
            "named_list_prefix_overlap_match_on_$$x": pre.match("$$x").group(0), "named_lists": {k: sorted(v) for k, v in NL.named_lists.items()},
            "malformed": rows}


if __name__ == "__main__" and "--b" in sys.argv:
    print(json.dumps(part_b(), indent=1, ensure_ascii=False))
