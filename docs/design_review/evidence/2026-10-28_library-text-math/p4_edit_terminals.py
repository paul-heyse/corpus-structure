"""P4 (2026-10-28): Lark `edit_terminals` as the single whole-name rule for command terminals.

    cd docs/design_review/evidence/2026-10-28_design-spikes
    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python ../2026-10-28_library-text-math/p4_edit_terminals.py

Builds the spike grammar text unchanged (shipped latex.lark + whole-name %override lines + extension
+ generated block) and adds edit_terminals, which rewrites every string terminal that is a control
word (including the anonymous %ignore literals "\\left", "\\right", "\\quad", ...) into a regex with
(?![A-Za-z]). Compares statuses and printed forms with the spike parser on cases and on the
spike-page math spans (results/s1/segments).
"""
import json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPIKE = HERE.parent / "2026-10-28_design-spikes"
sys.path.insert(0, str(SPIKE / "code"))
import lark  # noqa: E402
import regex  # noqa: E402
from lark.lexer import PatternRE, PatternStr  # noqa: E402
from mathgrammar import api, build, printer  # noqa: E402

CW = regex.compile(r"\\[A-Za-z]+")


ALT = regex.compile(r"\(\?:((?:[^()|]+\|)*[^()|]+)\)")  # a flat (?:a|b|c) alternation, as Lark builds for "a" | "b"
RE_CW = regex.compile(r"\\\\[A-Za-z]+")  # an escaped control word inside a regex: \\left


def whole_name(t):
    """Every control-word literal matches whole names only: "\\left" never matches the start of \\leftarrow."""
    p = t.pattern
    if isinstance(p, PatternStr) and CW.fullmatch(p.value):
        t.pattern = PatternRE(regex.escape(p.value) + r"(?![A-Za-z])", p.flags)
    elif isinstance(p, PatternRE) and (m := ALT.fullmatch(p.value)):
        alts = m.group(1).split("|")
        if any(RE_CW.fullmatch(a) for a in alts):
            t.pattern = PatternRE("(?:" + "|".join(a + "(?![A-Za-z])" if RE_CW.fullmatch(a) else a for a in alts) + ")", p.flags)


def edited_parser(mc):
    return lark.Lark(build.grammar_text(mc), source_path=str(build.GRAMMAR_DIR) + "/", parser="earley",
                     start=list(build.STARTS), lexer="dynamic", ambiguity="explicit", propagate_positions=True,
                     maybe_placeholders=False, keep_all_tokens=True, edit_terminals=whole_name)


mc0 = build.classify({})
spike_p = build.parser_for(mc0)
new_p = edited_parser(mc0)
rewritten = [t.name + " " + t.pattern.value for t in new_p.terminals if t.name.startswith("__IGNORE")]
cases = [r"x \leftarrow y", r"A \leftrightarrow B", r"x \rightarrow 0", r"\left( a \right)", r"\left[ a, b \right)",
         r"a \quadrant b", r"x \to 0"]
rows = []
for c in cases:
    out = {"latex": c}
    for name, p in (("spike", spike_p), ("edited", new_p)):
        build._PARSERS[mc0.key] = p
        api._CACHE.clear()
        r = api.parse(c, "any_value", mc=mc0)
        out[name] = {"status": r.status, "tree": printer.tree_canonical(r.tree, {}) if r.tree is not None else None}
    out["tokens"] = printer.tokens_canonical(c, {})
    rows.append(out)

# spike pages: every math span, both parsers, with the page macro tables
import glob  # noqa: E402
ren = json.loads((SPIKE / "results/s1/renditions.json").read_text())
changed, n, agree = [], 0, {"spike": 0, "edited": 0}
for page, rr in ren.items():
    name = page.replace("/", "__").removesuffix(".html")
    text = (SPIKE / "results/s1/canonical" / f"{name}.txt").read_text()
    macros = rr["parse_detail"]["macros"]
    mc = api._macro_class(macros)
    sp, ep = build.parser_for(mc), edited_parser(mc)
    for line in (SPIKE / "results/s1/segments" / f"{name}.jsonl").read_text().splitlines():
        s = json.loads(line)
        if not s["kind"].startswith("math"):
            continue
        tex = text[s["start"]:s["end"]]
        n += 1
        res = {}
        for nm, p in (("spike", sp), ("edited", ep)):
            build._PARSERS[mc.key] = p
            api._CACHE.clear()
            r = api.parse(tex, "any_value", mc=mc)
            tc = printer.tree_canonical(r.tree, mc.table()) if r.tree is not None else None
            res[nm] = (r.status, tc)
            if tc is not None and tc == printer.tokens_canonical(tex, mc.table()):
                agree[nm] += 1
        if res["spike"] != res["edited"]:
            changed.append({"tex": tex[:100], "spike": res["spike"][0], "edited": res["edited"][0],
                            "tree_spike": (res["spike"][1] or "")[:60], "tree_edited": (res["edited"][1] or "")[:60]})
        build._PARSERS.pop(mc.key, None)
print(json.dumps({"rewritten_terminals": len(rewritten), "examples": rewritten[:12], "cases": rows,
                  "spike_page_spans": n, "tree_equals_tokens": agree, "spans_changed": len(changed),
                  "changed_examples": changed[:15]}, indent=1, ensure_ascii=False))
