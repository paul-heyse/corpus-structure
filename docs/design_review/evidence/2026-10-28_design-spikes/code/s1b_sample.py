"""S1-B: locators and sample.json, invariants with an independent text path, determinism,
provisional sentences (P1 parser + b′ merge + rule c).

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/s1b_sample.py

Writes sample.json (evidence folder root), results/s1/invariants.json, results/s1/locators.json,
results/s1/sentences/<page>.provisional.jsonl.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

import yaml
from lxml.cssselect import CSSSelector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from s1_adapter import (  # noqa: E402
    CODE,
    EVIDENCE,
    SIEGRIST,
    adapt,
    load_profile,
    merge,
    DEFAULT_CONFIG,
    parse_html,
    stamp,
)
from s1_sentences import sentences  # noqa: E402

OUT = EVIDENCE / "results" / "s1"
PAGES = ["special/LocationScale.html", "special/Normal.html", "special/LogNormal.html", "special/Gamma.html"]
CORE = {  # unit id -> locators (D2 §12.2 core12; T1 is the union of two locators)
    "T1": ["special/LocationScale.html@p:As usual, our starting point", "special/LocationScale.html#dfn1"],
    "T2": ["special/Normal.html@p:Suppose again that \\( X \\) has the normal distribution with location parameter"],
    "T3": ["special/Normal.html#rel1"],
    "T4": ["special/LogNormal.html#dfn"],
    "U5": ["special/Normal.html#rel2"],
    "U6": ["special/Normal.html@p:Recall that in general, if \\(X\\) is a random variable with mean"],
    "U7": ["special/Normal.html@p:In some settings, it's convenient to consider a constant"],
    "U8": ["special/Normal.html@u:A metal rod is designed"],
    "U9": ["special/LogNormal.html@u:Suppose that \\(n \\in \\N_+\\) and that"],
    "U10": ["special/Gamma.html#dfn4"],
    "U11": ["special/Gamma.html#rel2"],
    "U12": ["special/Gamma.html#mom1"],
}


def ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def ancestors(seg: dict, by_key: dict) -> list[dict]:
    out = []
    while seg["parent"]:
        seg = by_key[seg["parent"]]
        out.append(seg)
    return out


def resolve(locator: str, r: dict) -> list[dict]:
    """D2 §12.2 locator forms: page#unit-id | page@u:<prefix> | page@p:<prefix> (outside units)."""
    text, segs = r["text"], r["segments"]
    by_key = {s["key"]: s for s in segs}
    if "#" in locator:
        uid = locator.split("#", 1)[1]
        return [s for s in segs if s["kind"] == "unit" and s["attrs"].get("id") == uid]
    form, prefix = locator.split("@", 1)[1].split(":", 1)
    prefix = ws(prefix)
    kind = {"u": "unit", "p": "paragraph"}[form]
    hits = [s for s in segs if s["kind"] == kind and ws(text[s["start"]:s["end"]]).startswith(prefix)]
    if form == "p":
        hits = [s for s in hits if not any(a["kind"] == "unit" for a in ancestors(s, by_key))]
    return hits


def check_slices(renditions: dict) -> dict:
    data = yaml.safe_load((CODE / "profile" / "slices.yaml").read_text())
    out = {}
    for name in ("trace", "core12"):
        for loc in data["slices"][name]:
            if isinstance(loc, dict):
                continue
            page = loc.split("#")[0].split("@")[0]
            hits = resolve(loc, renditions[page])
            out[loc] = {"matches": len(hits), "ok": len(hits) == 1,
                        "segments": [h["key"] for h in hits]}
    return out


def strip_insertions(r: dict, start: int, end: int) -> str:
    """Canonical text of [start, end) without the rendered-only insertions (references, quote marks,
    list markers), whitespace removed: what the source element's own text should equal."""
    text = r["text"]
    cut = [(m["start"], m["end"]) for m in r["markup"] if m["markup"] in ("aref", "list_marker")
           and start <= m["start"] and m["end"] <= end]
    chars = [c for i, c in enumerate(text[start:end], start) if not any(a <= i < b for a, b in cut)]
    s = "".join(chars).replace("“", "").replace("”", "")
    return re.sub(r"\s+", "", s)


def independent_text(page: str, r: dict) -> dict:
    """Re-parse the page and compute each element's text with XPath string(.) after removing the
    profile's excluded elements found through cssselect→XPath (not the walk that built the text)."""
    config = r["rendition"]["config"]
    root = parse_html((SIEGRIST / page).read_bytes(), config["parser"])
    stamp(root)
    prof = load_profile(config["profile"], config)
    for css in prof["exclude"].values():
        for el in CSSSelector(css, translator="html")(root):
            parent = el.getparent()
            if parent is None:
                continue
            tail = el.tail or ""
            prev = el.getprevious()
            if prev is not None:
                prev.tail = (prev.tail or "") + tail
            else:
                parent.text = (parent.text or "") + tail
            parent.remove(el)
    by_sid = {el.get("data-s1id"): el for el in root.iter() if isinstance(el.tag, str) and el.get("data-s1id")}
    checked = mismatched = skipped = 0
    examples = []
    for s in r["segments"]:
        sid = s["attrs"].get("sid")
        if not sid or s["kind"] in ("section",) or sid not in by_sid:
            skipped += 1
            continue
        el = by_sid[sid]
        expected = re.sub(r"\s+", "", unicodedata.normalize(config["unicode"], el.xpath("string(.)")))
        actual = strip_insertions(r, s["start"], s["end"])
        checked += 1
        if expected != actual:
            mismatched += 1
            if len(examples) < 8:
                examples.append({"segment": s["key"], "kind": s["kind"], "tag": s["attrs"].get("tag"),
                                 "expected": expected[:120], "actual": actual[:120]})
    return {"checked": checked, "mismatched": mismatched, "skipped_no_element": skipped, "examples": examples}


def structural(r: dict) -> dict:
    segs = r["segments"]
    by_key = {s["key"]: s for s in segs}
    viol: dict[str, list] = {"start_le_end": [], "inside_parent": [], "siblings_ordered": [], "keys_unique": []}
    for s in segs:
        if s["start"] > s["end"]:
            viol["start_le_end"].append(s["key"])
        p = by_key.get(s["parent"]) if s["parent"] else None
        if p and not (p["start"] <= s["start"] and s["end"] <= p["end"]):
            viol["inside_parent"].append(s["key"])
    kids: dict = {}
    for s in segs:
        kids.setdefault(s["parent"], []).append(s)
    for ks in kids.values():
        ks = sorted(ks, key=lambda x: (x["start"], x["end"]))
        for a, b in zip(ks, ks[1:], strict=False):
            if b["start"] < a["end"]:
                viol["siblings_ordered"].append([a["key"], b["key"]])
    if len(by_key) != len(segs):
        viol["keys_unique"].append(len(segs) - len(by_key))
    return {k: {"count": len(v), "examples": v[:3]} for k, v in viol.items()}


def main() -> int:
    renditions = {p: adapt(p) for p in PAGES}
    again = {p: adapt(p) for p in PAGES}
    determinism = {p: {"text_identical": renditions[p]["text"] == again[p]["text"],
                       "keys_identical": [s["key"] for s in renditions[p]["segments"]]
                       == [s["key"] for s in again[p]["segments"]]} for p in PAGES}
    invariants = {p: {"structural": structural(r), "independent_text": independent_text(p, r)}
                  for p, r in renditions.items()}
    (OUT / "sentences").mkdir(parents=True, exist_ok=True)
    sents = {}
    for p, r in renditions.items():
        sents[p] = sentences(r, "P1", "bp+c")
        name = p.replace("/", "__").removesuffix(".html")
        with (OUT / "sentences" / f"{name}.provisional.jsonl").open("w", encoding="utf-8") as f:
            for s in sents[p]:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
    sample = {"created": "2026-10-28", "sentence_variant": "provisional: P1 parser + b′ + rule c",
              "adapter_config": DEFAULT_CONFIG, "units": {}}
    for uid, locs in CORE.items():
        page = locs[0].split("#")[0].split("@")[0]
        r = renditions[page]
        parts = []
        n_sent = 0  # sentence ids run across a unit's parts (T1 has two)
        for loc in locs:
            hits = resolve(loc, r)
            if len(hits) != 1:
                parts.append({"locator": loc, "error": f"{len(hits)} matches"})
                continue
            h = hits[0]
            unit_text = r["text"][h["start"]:h["end"]]
            sids = [s for s in sents[page] if h["start"] <= s["start"] and s["end"] <= h["end"]]
            parts.append({"locator": loc, "found_by": loc.split(page)[1][:2], "segment_key": h["key"],
                          "kind": h["kind"], "start": h["start"], "end": h["end"],
                          "sha256": hashlib.sha256(unit_text.encode("utf-8")).hexdigest(),
                          "sentences": [{"id": f"s{n_sent + i + 1}", "key": s["key"], "start": s["start"], "end": s["end"]}
                                        for i, s in enumerate(sids)],
                          "first_80": unit_text[:80]})
            n_sent += len(sids)
        sample["units"][uid] = {"page": page, "document_key": r["rendition"]["document_key"],
                                "rendition_key": r["rendition"]["rendition_key"], "parts": parts}
    (EVIDENCE / "sample.json").write_text(json.dumps(sample, indent=2, ensure_ascii=False) + "\n")
    (OUT / "invariants.json").write_text(json.dumps({"determinism": determinism, "pages": invariants},
                                                    indent=2, ensure_ascii=False) + "\n")
    (OUT / "locators.json").write_text(json.dumps(check_slices(renditions), indent=2, ensure_ascii=False) + "\n")
    for p in PAGES:
        st = invariants[p]["structural"]
        it = invariants[p]["independent_text"]
        print(p, "structural", {k: v["count"] for k, v in st.items()}, "independent",
              {k: it[k] for k in ("checked", "mismatched", "skipped_no_element")}, determinism[p])
    bad = [u for u, v in sample["units"].items() if any("error" in x for x in v["parts"])]
    print("units located:", len(CORE) - len(bad), "of", len(CORE), "errors:", bad)
    return 0


if __name__ == "__main__":
    del merge
    sys.exit(main())
