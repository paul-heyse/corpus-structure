"""S1-E: profile-free baseline. trafilatura 2.3.1 XML extraction versus the S1 adapter's canonical text.

Plan: docs/plans/design-spikes-s0-s1/S1-ingest-segmentation.md §7.1 (settings §3.1).

For each of the 78 first-pass Siegrist pages, trafilatura runs three times: `plain`; `pruned`
(`prune_xpath` = the profile's exclusion XPaths); `pruned_noref` (pruned, and the empty
JS-filled `a.ref` anchors removed from the source first, isolating their effect). Its XML body is compared with our canonical
text (DEFAULT_CONFIG) by normalized character runs:

* both sides NFC, whitespace collapsed; rendered-only characters our conventions add and the
  source lacks (a.ref "[n]", ol.sub "(a) " markers, the “ ” around <q>) are masked out of ours;
* "characters" are non-whitespace characters;
* alignment: rapidfuzz Indel opcodes over whitespace tokens, refined by character-level Indel
  opcodes inside every replace block (so a token that differs by one character costs one).

Per page it reports our characters missing from trafilatura's output by segment kind
(non-exclusive), the characters trafilatura adds and which profile exclusion rule they come
from, verbatim survival of our math spans and delimiters, and a structure cross-tab
(our segment kind -> trafilatura element holding the same normalized text).

Usage (from the evidence folder):
    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/s1e_trafilatura.py
    ... code/s1e_trafilatura.py [summary.json]
Outputs: results/s1/baseline_trafilatura.tsv; optionally a summary JSON (totals, cross-tabs,
unattributed tokens) at the given path, from which results/s1/baseline_trafilatura.md was written.
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import lxml.html
import trafilatura
from rapidfuzz.distance import Indel

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s1_adapter as A  # noqa: E402

OUT = A.EVIDENCE / "results" / "s1"
INDEX = A.REPO / "docs/statistics_corpus/index/siegrist_sections.tsv"
VARIANTS = ("plain", "pruned", "pruned_noref")
SHORT_DEF = 300  # a "short definition unit": definition-hinted unit with < 300 non-space chars
TRAF_OPTS = dict(output_format="xml", include_tables=True, include_formatting=True,
                 favor_recall=True, include_comments=False)
# trafilatura's XML vocabulary plus raw HTML tags its fallback paths pass through (td, th, tr, div)
TRAF_BLOCK = {"p", "head", "item", "cell", "quote", "code", "list", "table", "row", "graphic", "lb",
              "td", "th", "tr", "div"}
CATS = ["all", "heading", "details", "details_summary", "math_display", "math_inline",
        "ol_sub_item", "list_item_other", "table", "definition_unit", "short_definition_unit",
        "unit", "outside_unit_prose", "caption"]
# exclusive attribution of missing characters (first matching class wins)
PRIMARY = ["heading", "details_summary", "table", "math_display", "ol_sub_item", "details",
           "math_inline", "caption", "list_item_other", "short_definition_unit", "unit",
           "outside_unit_prose"]


def pages() -> list[str]:
    with INDEX.open(newline="", encoding="utf-8") as f:
        return [r["path"] for r in csv.DictReader(f, delimiter="\t") if r["first_pass"] == "yes"]


def collapse(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip()


# ---------------------------------------------------------------------------- our side

def rendered_mask(r: dict) -> list[bool]:
    """True at characters our rendering conventions add (absent from the source bytes)."""
    mask = [False] * len(r["text"])
    for m in r["markup"]:
        if m["markup"] in ("aref", "list_marker"):
            for k in range(m["start"], m["end"]):
                mask[k] = True
        elif m["markup"] == "q" and r["rendition"]["config"]["render"]["q"] == "quotes":
            mask[m["start"]] = mask[m["end"] - 1] = True
    return mask


def categories(r: dict) -> list[set[str]]:
    """Per character of our text: the segment kinds (S1-E classes) containing it."""
    text, segs = r["text"], r["segments"]
    by_key = {s["key"]: s for s in segs}
    cats: list[set[str]] = [{"all"} for _ in text]

    def ancestors(s):
        p = s["parent"]
        while p:
            yield by_key[p]
            p = by_key[p]["parent"]

    def mark(s, name):
        for k in range(s["start"], s["end"]):
            cats[k].add(name)

    for s in segs:
        kind, anc = s["kind"], list(ancestors(s))
        in_details = any(a["kind"] == "details" for a in anc)
        if kind == "heading":
            mark(s, "details_summary" if in_details else "heading")
        elif kind == "details":
            mark(s, "details")
        elif kind in ("math_display", "math_inline"):
            mark(s, kind)
        elif kind == "list_item":
            parent = by_key.get(s["parent"])
            sub = parent is not None and "sub" in parent["attrs"].get("classes", [])
            mark(s, "ol_sub_item" if sub else "list_item_other")
        elif kind == "table":
            mark(s, "table")
        elif kind == "caption":
            mark(s, "caption")
        elif kind == "unit":
            mark(s, "unit")
            if s["attrs"].get("hint", {}).get("statement_kind") == "definition":
                mark(s, "definition_unit")
                if sum(not c.isspace() for c in text[s["start"]:s["end"]]) < SHORT_DEF:
                    mark(s, "short_definition_unit")
    for k in range(len(text)):
        if "unit" not in cats[k] and not cats[k] & {"heading", "details_summary"}:
            cats[k].add("outside_unit_prose")
    return cats


def our_tokens(text: str, mask: list[bool]) -> tuple[list[str], list[list[int]]]:
    """NFC-stable text (the adapter already applied NFC) -> whitespace tokens with source offsets."""
    toks, pos, cur, cpos = [], [], [], []
    for k, ch in enumerate(text):
        if mask[k]:
            continue
        if ch.isspace():
            if cur:
                toks.append("".join(cur)), pos.append(cpos)
                cur, cpos = [], []
        else:
            cur.append(ch), cpos.append(k)
    if cur:
        toks.append("".join(cur)), pos.append(cpos)
    return toks, pos


def segment_norm_text(r: dict, s: dict, mask: list[bool]) -> str:
    return collapse("".join(c for k, c in enumerate(r["text"][s["start"]:s["end"]], s["start"])
                            if not mask[k]))


# ---------------------------------------------------------------------------- trafilatura side

def traf_text(body) -> str:
    """Text of trafilatura's XML body: text and tails in document order, a space around blocks."""
    out: list[str] = []

    def walk(el):
        block = el.tag in TRAF_BLOCK
        if block:
            out.append(" ")
        if el.tag == "lb":
            out.append(" ")
        out.append(el.text or "")
        for c in el:
            walk(c)
        if block:
            out.append(" ")
        out.append(el.tail or "")

    walk(body)
    return collapse("".join(out))


def drop_empty_arefs(raw: bytes) -> bytes:
    """Source edit for the third variant: remove empty JS-filled a.ref anchors, keeping their tails
    (the adapter's `aref: empty` convention applied before trafilatura sees the page)."""
    root = lxml.html.document_fromstring(raw)
    for a in root.xpath("//a[contains(concat(' ', normalize-space(@class), ' '), ' ref ')]"):
        if not "".join(a.itertext()).strip():
            a.drop_tree()
    return lxml.html.tostring(root, encoding="utf-8", doctype="<!DOCTYPE html>")


def run_trafilatura(raw: bytes, prune: list[str] | None):
    doc = trafilatura.bare_extraction(raw, prune_xpath=prune, **TRAF_OPTS)
    return None if doc is None else doc.body


# ---------------------------------------------------------------------------- alignment

def align(ours: list[str], opos: list[list[int]], theirs: list[str]):
    """Returns (missing source offsets of ours, inserted strings of theirs)."""
    missing: list[int] = []
    inserted: list[str] = []
    for op in Indel.opcodes(ours, theirs):
        tag, i1, i2, j1, j2 = op.tag, op.src_start, op.src_end, op.dest_start, op.dest_end
        if tag == "equal":
            continue
        if tag == "delete":
            for p in opos[i1:i2]:
                missing.extend(p)
            continue
        if tag == "insert":
            inserted.append(" ".join(theirs[j1:j2]))
            continue
        # replace: character-level refinement
        a_chars, a_pos = [], []
        for t, p in zip(ours[i1:i2], opos[i1:i2], strict=True):
            if a_chars:
                a_chars.append(" "), a_pos.append(None)
            a_chars.extend(t), a_pos.extend(p)
        a = "".join(a_chars)
        b = " ".join(theirs[j1:j2])
        if len(a) * len(b) > 4e8:  # never hit on this corpus; recorded if it is
            missing.extend(p for p in a_pos if p is not None)
            inserted.append(b)
            continue
        for cop in Indel.opcodes(a, b):
            if cop.tag in ("delete", "replace"):
                missing.extend(p for p in a_pos[cop.src_start:cop.src_end] if p is not None)
            if cop.tag in ("insert", "replace"):
                s = b[cop.dest_start:cop.dest_end].strip()
                if s:
                    inserted.append(s)
    return missing, inserted


# ---------------------------------------------------------------------------- boilerplate attribution

def excluded_texts(raw: bytes, prof: dict, xpaths: dict[str, str]) -> dict[str, str]:
    root = lxml.html.document_fromstring(raw, parser=lxml.html.HTMLParser(remove_comments=True))
    out = {}
    for rule, css in prof["exclude"].items():
        out[rule] = " ".join(collapse("".join(el.itertext())) for el in root.xpath(xpaths[css]))
    return out


def attribute(inserted: list[str], excl: dict[str, str]) -> tuple[Counter, list[str]]:
    by_rule: Counter = Counter()
    other: list[str] = []
    tok_sets = {r: set(t.split()) for r, t in excl.items()}
    for s in inserted:
        n = sum(not c.isspace() for c in s)
        rule = next((r for r, t in excl.items() if t and s in t), None)
        if rule:
            by_rule[rule] += n
            continue
        for tok in s.split():
            r = next((r for r, ts in tok_sets.items() if tok in ts), None)
            if r:
                by_rule[r] += len(tok)
            else:
                by_rule["unattributed"] += len(tok)
                other.append(tok)
    return by_rule, other


# ---------------------------------------------------------------------------- structure

def traf_index(body) -> dict[str, list[str]]:
    idx: dict[str, list[str]] = defaultdict(list)
    for el in body.iter():
        if el.tag in ("p", "head", "item", "cell", "quote", "code"):
            idx[collapse("".join(el.itertext()))].append(el.tag)
    return idx


def structure_xtab(r: dict, mask, body, xt: Counter) -> None:
    """For our text-bearing segments: which trafilatura element holds exactly the same text."""
    idx = traf_index(body) if body is not None else {}
    by_key = {s["key"]: s for s in r["segments"]}
    for s in r["segments"]:
        if s["kind"] not in ("heading", "paragraph", "list_item", "table_cell", "caption"):
            continue
        kind = s["kind"]
        par = by_key.get(s["parent"])
        if kind == "heading":
            kind = "summary" if s["attrs"].get("tag") == "summary" else f"heading:{s['attrs'].get('tag')}"
        elif kind == "list_item" and par and "sub" in par["attrs"].get("classes", []):
            kind = "list_item:ol.sub"
        t = segment_norm_text(r, s, mask)
        if not t:
            continue
        tags = idx.get(t)
        xt[(kind, tags[0] if tags else "no exact element")] += 1


# ---------------------------------------------------------------------------- loss inventory

def collect_losses(r: dict, missing: set[int], mask, examples: dict, key: str) -> None:
    """Segments (details, tables, units, paragraphs, list items) at least 90% missing."""
    by_key = {s["key"]: s for s in r["segments"]}
    kids: dict[str, list[str]] = defaultdict(list)
    for s in r["segments"]:
        if s["parent"]:
            kids[s["parent"]].append(by_key[s["key"]]["kind"])
    for s in r["segments"]:
        if s["kind"] not in ("details", "table", "unit", "paragraph", "list_item", "caption"):
            continue
        ks = [k for k in range(s["start"], s["end"]) if not mask[k] and not r["text"][k].isspace()]
        if not ks:
            continue
        lost = sum(k in missing for k in ks)
        if lost / len(ks) >= 0.9:
            par = by_key.get(s["parent"])
            examples[key].append({
                "page": r["page"], "kind": s["kind"], "chars": len(ks),
                "sourceline": s["attrs"].get("sourceline"), "parent": par["kind"] if par else None,
                "child_kinds": sorted(set(kids.get(s["key"], []))),
                "head": collapse(r["text"][s["start"]:s["end"]])[:60]})


# ---------------------------------------------------------------------------- driver

def nonspace(s: str) -> int:
    return sum(not c.isspace() for c in s)


def main() -> int:
    t0 = time.time()
    plist = pages()
    prof = A.load_profile("siegrist", A.DEFAULT_CONFIG)
    rows, totals = [], {v: Counter() for v in VARIANTS}
    xtabs = {v: Counter() for v in VARIANTS}
    struct = {v: Counter() for v in VARIANTS}
    unattributed = {v: Counter() for v in VARIANTS}
    examples: dict[str, list] = defaultdict(list)
    for page in plist:
        r = A.adapt(page)
        raw = (A.SIEGRIST / page).read_bytes()
        xp = r["rendition"]["profile_xpaths"]
        prune = [xp[css] for css in prof["exclude"].values()]
        mask = rendered_mask(r)
        cats = categories(r)
        toks, pos = our_tokens(r["text"], mask)
        excl = excluded_texts(raw, prof, xp)
        cat_total = Counter()
        for k, ch in enumerate(r["text"]):
            if not mask[k] and not ch.isspace():
                for c in cats[k]:
                    cat_total[c] += 1
        maths = [s for s in r["segments"] if s["kind"] in ("math_inline", "math_display")]
        for variant, pr in (("plain", None), ("pruned", prune), ("pruned_noref", prune)):
            body = run_trafilatura(drop_empty_arefs(raw) if variant == "pruned_noref" else raw, pr)
            ttext = traf_text(body) if body is not None else ""
            ttoks = ttext.split()
            missing, inserted = align(toks, pos, ttoks)
            miss = Counter()
            prim = Counter()
            for k in missing:
                for c in cats[k]:
                    miss[c] += 1
                prim[next((c for c in PRIMARY if c in cats[k]), "outside_unit_prose")] += 1
            kept, other = attribute(inserted, excl)
            unattributed[variant].update(other)
            m_ok = sum(1 for s in maths if collapse(r["text"][s["start"]:s["end"]]) in ttext)
            # spans not found verbatim although most of their characters were aligned as present
            mset = set(missing)
            m_altered = [collapse(r["text"][s["start"]:s["end"]])[:80] for s in maths
                         if collapse(r["text"][s["start"]:s["end"]]) not in ttext
                         and sum(k in mset for k in range(s["start"], s["end"])) < 0.5 * (s["end"] - s["start"])]
            if variant == "pruned_noref":
                examples["math_altered"].extend({"page": page, "span": m} for m in m_altered)
            delim = {d: (r["text"].count(d), ttext.count(d)) for d in ("\\(", "\\)", "\\[", "\\]", "\\begin{align")}
            tags = Counter(el.tag + (f":{el.get('rend')}" if el.tag in ("list", "head") and el.get("rend") else "")
                           for el in body.iter()) if body is not None else Counter()
            structure_xtab(r, mask, body, xtabs[variant])
            struct[variant].update(tags)
            row = {"page": page, "variant": variant, "returned": body is not None,
                   "our_chars": cat_total["all"], "traf_chars": nonspace(ttext),
                   "missing_chars": miss["all"],
                   "missing_pct": round(100 * miss["all"] / max(cat_total["all"], 1), 2)}
            for c in CATS[1:]:
                row[f"miss_{c}"] = miss[c]
                row[f"tot_{c}"] = cat_total[c]
            row["inserted_chars"] = sum(kept.values())
            for rule in list(prof["exclude"]) + ["unattributed"]:
                row[f"kept_{rule}"] = kept[rule]
            row["math_spans"], row["math_verbatim"], row["math_altered"] = len(maths), m_ok, len(m_altered)
            for d, (a, b) in delim.items():
                row[f"ours_{d}"], row[f"traf_{d}"] = a, b
            for t in ("head", "p", "list", "item", "table", "row", "cell", "quote", "hi", "code", "graphic"):
                row[f"traf_{t}"] = sum(v for k, v in tags.items() if k.split(":")[0] == t)
            ours_kinds = Counter(s["kind"] for s in r["segments"])
            for k in ("heading", "paragraph", "list", "list_item", "table", "details", "unit", "math_display"):
                row[f"our_{k}"] = ours_kinds[k]
            rows.append(row)
            t = totals[variant]
            for k, v in row.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool) and k != "missing_pct":
                    t[k] += v
            for c, v in prim.items():
                t[f"primary_{c}"] += v
            t["pages"] += 1
            t["returned_none"] += body is None
            if variant != "plain":
                collect_losses(r, set(missing), mask, examples, f"whole_losses_{variant}")
        print(page, *(x["missing_pct"] for x in rows[-3:]), flush=True)
    fields = list(rows[0].keys())
    with (OUT / "baseline_trafilatura.tsv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    summary = {
        "trafilatura": trafilatura.__version__, "options": TRAF_OPTS,
        "prune_xpath": prune, "short_definition_threshold_nonspace_chars": SHORT_DEF,
        "totals": {v: dict(t) for v, t in totals.items()},
        "structure_xtab": {v: {f"{a} -> {b}": n for (a, b), n in sorted(x.items())} for v, x in xtabs.items()},
        "traf_tags": {v: dict(s) for v, s in struct.items()},
        "unattributed_top": {v: u.most_common(40) for v, u in unattributed.items()},
        "examples": examples, "wall_seconds": round(time.time() - t0, 1),
    }
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
    print("wall", summary["wall_seconds"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
