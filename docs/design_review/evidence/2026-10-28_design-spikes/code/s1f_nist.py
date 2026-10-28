"""S1-F: second-source generality probe on NIST e-Handbook section 1.3.6 HTML.

Plan: docs/plans/design-spikes-s0-s1/S1-ingest-segmentation.md §7.2.

Runs the S1 adapter's own machinery (parse, cssselect2 Matcher + cssselect XPath agreement,
Builder walk, math scanner + pylatexenc span validation, serialization, keys) on eight NIST pages
under a generic profile that holds only structural rules (no Siegrist classes). s1_adapter.py is
imported, not edited: `adapt()` hard-codes the Siegrist corpus root and the YAML profile loader,
so `adapt_generic()` below repeats its driver steps for arbitrary bytes and a profile dict.

Variants per page:
  generic       structural profile (scripts/noscript/style, button, img excluded; sections h1–h6
                requested but see `sectionize` note in the report);
  generic_alt   the same, except an <img> that has an alt attribute is replaced before the walk by
                an inline <span data-img-alt=src> holding the alt text (a probe of an
                `img_alt` rendering convention the adapter lacks);
  siegrist      the Siegrist profile's rules evaluated on the NIST tree (which rules match at all);
  trafilatura   trafilatura 2.3.1 with the S1-E options, aligned with the `generic` canonical text.

Usage (from the evidence folder):
    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/s1f_nist.py
Outputs: results/s1/nist/<page>.generic.txt, <page>.generic_alt.txt, <page>.trafilatura.xml,
results/s1/nist/probe.json (per-page measurements used by results/s1/nist_probe.md).
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

import trafilatura
from lxml import etree
from lxml.cssselect import CSSSelector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s1_adapter as A  # noqa: E402
import s1e_trafilatura as E  # noqa: E402

NIST = A.CORPUS / "nist_ehandbook/html/eda/section3"
OUT = A.EVIDENCE / "results/s1/nist"
PAGES = ["eda361.htm", "eda3652.htm", "eda3661.htm", "eda3662.htm",
         "eda367.htm", "eda3671.htm", "eda3672.htm", "eda3675.htm"]

GENERIC = {
    "applies_to": "nist_ehandbook/html/**/*.htm",
    "exclude": {"scripts": "script, noscript, style", "controls": "button", "images": "img"},
    "title": "head > title",
    "sections": ["h1", "h2", "h3", "h4", "h5", "h6"],
    "block_hints": {},
    "math": {"inline": ["\\(", "\\)"], "display": ["\\[", "\\]"],
             "display_environments": ["align", "align*"], "page_macros": False},
}
CONFIG = A.merge(A.DEFAULT_CONFIG, {"profile": "generic-structural"})


def generic_rules(prof: dict) -> list[tuple[str, tuple]]:
    """profile_rules() without the unit / details roles a generic profile does not declare."""
    rules = [(css, ("exclude", name, None)) for name, css in prof["exclude"].items()]
    rules.append((prof["title"], ("title", "title", None)))
    rules += [(css, ("block_hint", css, h)) for css, h in prof["block_hints"].items()]
    return rules


def surface_alt(root) -> list[dict]:
    """generic_alt: <img alt> -> inline span with the alt text (tail kept)."""
    out = []
    for img in root.xpath("//img[@alt]"):
        span = etree.Element("span")
        span.set("data-img-alt", img.get("src") or "")
        span.text = img.get("alt")
        span.tail = img.tail
        for k in ("data-s1id",):
            if img.get(k):
                span.set(k, img.get(k))
        img.getparent().replace(img, span)
        out.append({"src": img.get("src"), "alt": img.get("alt")})
    return out


def adapt_generic(raw: bytes, page: str, prof: dict, alt: bool = False) -> dict:
    root = A.parse_html(raw, "lxml")
    alts = surface_alt(root) if alt else []
    A.stamp(root)
    rules = generic_rules(prof)
    payloads = A.match_cssselect2(root, rules)
    xpay, xpaths = A.match_xpath(root, rules)
    agreement = A.compare_payloads(payloads, xpay)
    macros = A.macro_table(root)
    ctx = A.latex_context(macros)
    b = A.Builder(root, CONFIG, prof, payloads)
    tree = b.build(root.find("body"))
    stats = {"math_anomalies": [], "unicode_changed": [], "orphans": []}
    text, seg = A.serialize(tree, CONFIG, prof, ctx, stats)
    doc_key = A.make_key("doc", ["corpus-structure", "nist_ehandbook/html/eda/section3/" + page,
                                 hashlib.sha256(raw).hexdigest()])
    cfg_hash = hashlib.sha256(A.canonical_json([CONFIG, prof, alt]).encode()).hexdigest()[:32]
    ren_key = A.make_key("ren", [doc_key, cfg_hash])
    segments, markup = [], []
    A.flatten(seg, ren_key, text, segments, markup)
    A.add_titles(segments, text)
    title = CSSSelector(prof["title"], translator="html")(root)
    return {"text": text, "segments": segments, "markup": markup, "exclusions": b.exclusions,
            "alts": alts, "stats": stats, "agreement": agreement, "xpaths": xpaths,
            "title": re.sub(r"\s+", " ", title[0].text_content()).strip() if title else None,
            "root": root}


def siegrist_rule_hits(raw: bytes) -> dict[str, int]:
    prof = A.load_profile("siegrist", A.DEFAULT_CONFIG)
    root = A.parse_html(raw, "lxml")
    A.stamp(root)
    hits = Counter()
    for payloads in A.match_cssselect2(root, A.profile_rules(prof)).values():
        for p in payloads:
            hits[f"{p[0]}:{p[1]}"] += 1
    rules = {f"{p[0]}:{p[1]}" for _, p in A.profile_rules(prof)}
    return {r: hits.get(r, 0) for r in sorted(rules)}


def describe(r: dict) -> dict:
    segs, text = r["segments"], r["text"]
    by_key = {s["key"]: s for s in segs}
    kinds = Counter(s["kind"] for s in segs)
    heads = []
    for s in segs:
        if s["kind"] == "heading":
            chain, p = [], s["parent"]
            while p:
                chain.append(by_key[p]["kind"])
                p = by_key[p]["parent"]
            heads.append({"tag": s["attrs"]["tag"], "text": text[s["start"]:s["end"]][:60],
                          "ancestors": chain})
    math = [s for s in segs if s["kind"].startswith("math_")]
    pre = [s for s in segs if s["attrs"].get("tag") == "pre"]
    # marginal-note layout: a row whose first cell holds only <i> text and whose second cell is wide
    root = r["root"]
    notes = []
    for tr in root.iter("tr"):
        cells = [c for c in tr if isinstance(c.tag, str) and c.tag in ("td", "th")]
        if len(cells) == 2 and (cells[0].get("width") or "").startswith("15"):
            notes.append(re.sub(r"\s+", " ", cells[0].text_content()).strip())
    imgs_alt = [m for m in r["markup"] if m["markup"] == "span"]
    first_cell = next((s for s in segs if s["kind"] == "table_cell"), None)
    return {
        "title": r["title"], "chars": len(text), "segment_kinds": dict(kinds),
        "headings": heads, "sections": kinds.get("section", 0),
        "math": {"inline": sum(s["kind"] == "math_inline" for s in math),
                 "display": sum(s["kind"] == "math_display" for s in math),
                 "partial": [{"text": text[s["start"]:s["end"]][:80], "reason": s.get("reason")}
                             for s in math if s["parse_status"] != "ok"]},
        "math_anomalies": r["stats"]["math_anomalies"],
        "pre_blocks": [{"chars": s["end"] - s["start"], "newlines_kept": text[s["start"]:s["end"]].count("\n"),
                        "head": text[s["start"]:s["end"]][:70]} for s in pre],
        "marginal_notes": notes,
        "first_table_cell": text[first_cell["start"]:first_cell["end"]][:120] if first_cell else None,
        "exclusions": dict(Counter(e["rule"] for e in r["exclusions"])),
        "alt_spans": [m["text"] for m in imgs_alt],
        "img_alts_surfaced": r["alts"],
        "engines_identical": r["agreement"]["all_identical"],
        "orphans": len(r["stats"]["orphans"]),
        "html_math_markup": dict(Counter(m["markup"] for m in r["markup"] if m["markup"] in ("sub", "sup", "em"))),
    }


def traf_compare(raw: bytes, r: dict) -> tuple[dict, str]:
    body = E.run_trafilatura(raw, None)
    if body is None:
        return {"returned": False}, ""
    ttext = E.traf_text(body)
    mask = [False] * len(r["text"])
    toks, pos = E.our_tokens(r["text"], mask)
    missing, inserted = E.align(toks, pos, ttext.split())
    ours = sum(not c.isspace() for c in r["text"])
    maths = [s for s in r["segments"] if s["kind"].startswith("math_")]
    tags = Counter(el.tag + (f":{el.get('rend')}" if el.get("rend") else "") for el in body.iter())
    lost = sorted(set(missing))
    runs, cur = [], []
    for k in lost:  # contiguous lost runs -> short heads for the report
        if cur and k != cur[-1] + 1 and not r["text"][cur[-1] + 1:k].isspace():
            runs.append(cur)
            cur = []
        cur.append(k)
    if cur:
        runs.append(cur)
    runs.sort(key=len, reverse=True)
    return {
        "returned": True, "our_chars": ours, "traf_chars": sum(not c.isspace() for c in ttext),
        "missing_chars": len(missing), "missing_pct": round(100 * len(missing) / max(ours, 1), 2),
        "inserted_chars": sum(sum(not c.isspace() for c in s) for s in inserted),
        "inserted_heads": [s[:60] for s in sorted(inserted, key=len, reverse=True)[:4]],
        "largest_missing": [{"chars": len(x), "head": re.sub(r"\s+", " ", r["text"][x[0]:x[-1] + 1])[:70]}
                            for x in runs[:5]],
        "math_spans": len(maths),
        "math_verbatim": sum(E.collapse(r["text"][s["start"]:s["end"]]) in ttext for s in maths),
        "tags": dict(tags),
        "heads": [E.collapse("".join(h.itertext()))[:60] for h in body.iter("head")],
    }, etree.tostring(body, encoding="unicode", pretty_print=True)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"profile": GENERIC, "config": CONFIG, "pages": {}}
    for page in PAGES:
        raw = (NIST / page).read_bytes()
        name = page.removesuffix(".htm")
        g = adapt_generic(raw, page, copy.deepcopy(GENERIC))
        ga = adapt_generic(raw, page, copy.deepcopy(GENERIC), alt=True)
        (OUT / f"{name}.generic.txt").write_text(g["text"], encoding="utf-8")
        (OUT / f"{name}.generic_alt.txt").write_text(ga["text"], encoding="utf-8")
        traf, xml = traf_compare(raw, g)
        (OUT / f"{name}.trafilatura.xml").write_text(xml, encoding="utf-8")
        report["pages"][page] = {"generic": describe(g), "generic_alt": describe(ga),
                                 "siegrist_rule_hits": siegrist_rule_hits(raw), "trafilatura": traf}
        d = report["pages"][page]["generic"]
        print(page, d["chars"], "chars", d["segment_kinds"], "traf missing%", traf.get("missing_pct"))
    (OUT / "probe.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
