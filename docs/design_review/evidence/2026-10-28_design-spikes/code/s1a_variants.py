"""S1-A: adapter variants V1–V4, V6 (pylatexenc 3.0b2, default and prose-safe ParsingState), V7, R1–R5.

Each variant re-runs the adapter with one configuration change and compares it with the default
rendition. Writes results/s1/variants_s1a.json and results/s1/blocks/<page>.jsonl (block texts with scanner math).

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/s1a_variants.py [pages...]
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from pylatexenc.latexnodes.parsers import LatexGeneralNodesParser
from pylatexenc.latexwalker import (
    LatexCommentNode,
    LatexEnvironmentNode,
    LatexMathNode,
    LatexWalker,
)
from s1_adapter import EVIDENCE, adapt, prose_safe_state

SPIKE_PAGES = ["special/LocationScale.html", "special/Normal.html", "special/LogNormal.html", "special/Gamma.html"]
OUT = EVIDENCE / "results" / "s1"
TEXT_KINDS = {"paragraph", "list_item", "heading", "table_cell", "caption"}

VARIANTS = {
    "V1_html5lib": {"parser": "html5lib"},
    "V2_NFKC": {"unicode": "NFKC"},
    "V3_math_ws_collapse": {"math_whitespace": "collapse"},
    "V4_h3_only": {"sections": "h3"},
    "V7_apps_excluded": {"apps": "exclude"},
    "R1_aref_empty": {"render": {"aref": "empty"}},
    "R1_aref_placeholder": {"render": {"aref": "placeholder"}},
    "R2_q_bare": {"render": {"q": "bare"}},
    "R3_markers_none": {"render": {"list_markers": "none"}},
    "R3_markers_browser": {"render": {"list_markers": "browser"}},
    "R4_summary_drop": {"render": {"summary": "drop"}},
    "R5_figure_drop": {"render": {"figure": "drop"}},
}


def text_of(r: dict, s: dict) -> str:
    return r["text"][s["start"]:s["end"]]


def structure(r: dict) -> list[tuple[str, str]]:
    """Kind and text of every non-math segment, in order: the structural fingerprint of a rendition."""
    return [(s["kind"], text_of(r, s)) for s in r["segments"] if not s["kind"].startswith("math")]


def diff(base: dict, var: dict) -> dict:
    a, b = structure(base), structure(var)
    kinds_a, kinds_b = Counter(k for k, _ in a), Counter(k for k, _ in b)
    sa, sb = set(a), set(b)
    only_a = [x for x in a if x not in sb]
    only_b = [x for x in b if x not in sa]
    math_a = [text_of(base, s) for s in base["segments"] if s["kind"].startswith("math")]
    math_b = [text_of(var, s) for s in var["segments"] if s["kind"].startswith("math")]
    return {
        "chars": [len(base["text"]), len(var["text"])],
        "segments_by_kind_delta": {k: kinds_b[k] - kinds_a[k] for k in sorted(set(kinds_a) | set(kinds_b))
                                   if kinds_b[k] != kinds_a[k]},
        "segments_only_in_default": len(only_a),
        "segments_only_in_variant": len(only_b),
        "examples_default": [(k, t[:120]) for k, t in only_a[:4]],
        "examples_variant": [(k, t[:120]) for k, t in only_b[:4]],
        "math_spans": [len(math_a), len(math_b)],
        "math_texts_changed": sum(1 for x, y in zip(math_a, math_b, strict=False) if x != y),
        "unicode_changed": len(var["rendition"]["parse_detail"]["unicode_changed"]),
        "unicode_examples": var["rendition"]["parse_detail"]["unicode_changed"][:5],
    }


def blocks(r: dict) -> list[dict]:
    """Text-bearing blocks with their math segments (scanner results), for V6."""
    segs = r["segments"]
    kids: dict[str, list[dict]] = {}
    for s in segs:
        kids.setdefault(s["parent"], []).append(s)
    out = []
    for s in segs:
        if s["kind"] in TEXT_KINDS:
            math = [{"start": m["start"] - s["start"], "end": m["end"] - s["start"], "kind": m["kind"]}
                    for m in kids.get(s["key"], []) if m["kind"].startswith("math")]
            out.append({"segment": s["key"], "kind": s["kind"], "start": s["start"], "text": text_of(r, s),
                        "scanner_math": math})
    return out


def v6_walker(bl: list[dict], prose_safe: bool) -> dict:
    """pylatexenc 3.0b2 over whole block text, default ParsingState ($, $$ math; % comments) or the
    prose-safe one: spans versus the scanner, comment nodes, errors."""
    agree = only_scanner = only_walker = comments = errors = 0
    examples: list[dict] = []
    for b in bl:
        try:
            w = LatexWalker(b["text"], tolerant_parsing=True)
            if prose_safe:
                nodes, _ = w.parse_content(LatexGeneralNodesParser(), parsing_state=prose_safe_state(w))
            else:
                nodes, _, _ = w.get_latex_nodes()
        except Exception as exc:  # recorded per block
            errors += 1
            examples.append({"segment": b["segment"], "error": repr(exc)[:160]})
            continue
        found = set()
        stack = list(nodes)
        while stack:
            n = stack.pop()
            if isinstance(n, LatexMathNode) or (isinstance(n, LatexEnvironmentNode)
                                                and n.environmentname in ("align", "align*")):
                found.add((n.pos, n.pos_end))
                continue
            if isinstance(n, LatexCommentNode):
                comments += 1
                examples.append({"segment": b["segment"], "comment_swallowed": b["text"][n.pos:n.pos_end][:120]})
            stack.extend(getattr(n, "nodelist", None) or [])
        scan = {(m["start"], m["end"]) for m in b["scanner_math"]}
        agree += len(scan & found)
        only_scanner += len(scan - found)
        only_walker += len(found - scan)
        for s, e in sorted(found - scan)[:2]:
            examples.append({"segment": b["segment"], "walker_only": b["text"][s:e][:120]})
        for s, e in sorted(scan - found)[:2]:
            examples.append({"segment": b["segment"], "scanner_only": b["text"][s:e][:120]})
    return {"blocks": len(bl), "spans_agree": agree, "scanner_only": only_scanner, "walker_only": only_walker,
            "comment_nodes": comments, "parse_errors": errors, "examples": examples[:12]}


def main(pages: list[str]) -> int:
    report: dict = {}
    (OUT / "blocks").mkdir(parents=True, exist_ok=True)
    for page in pages:
        base = adapt(page)
        name = page.replace("/", "__").removesuffix(".html")
        bl = blocks(base)
        with (OUT / "blocks" / f"{name}.jsonl").open("w", encoding="utf-8") as f:
            for b in bl:
                f.write(json.dumps(b, ensure_ascii=False) + "\n")
        page_rep = {"default_rendition": base["rendition"]["rendition_key"],
                    "V5_profile_engines": base["rendition"]["profile_engines"],
                    "V6_pylatexenc3_default_state": v6_walker(bl, prose_safe=False),
                    "V6_pylatexenc3_prose_safe": v6_walker(bl, prose_safe=True)}
        for vname, cfg in VARIANTS.items():
            page_rep[vname] = diff(base, adapt(page, cfg))
        report[page] = page_rep
        print(page, "done")
    (OUT / "variants_s1a.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main(sys.argv[1:] or SPIKE_PAGES))
