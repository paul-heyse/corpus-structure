"""S6-F (brief steps 9–10): claim-key agreement under the revised statement key, and restated facts.

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run --locked python code/s6f_keys.py

Step 9. The S0 blind passes A and B (``results/s0/stored/pass_a``, ``pass_b``) on the libxml2
renditions of ``sample.json``, aligned unit by unit with the I-R2 instruments exactly as
``code/s0d_compare.py`` does (``align_unit`` on ``side_for``, ``compute_keys``, ``key_agreement``
at the core tier). Rows:

- the four S0 variants, recomputed here as a check against ``results/s0/compare/a_vs_b*``
  (raw; ``--anchors``; ``--labels``; both; normalizations from ``code/s0d_key_variants.normalize``);
- **revised**: each statement's key part replaced by ADR-0019's (D1 §10.1): the anchor segment is the
  ``unit`` for a statement inside a unit, the ``details`` block for a proof or solution, and the
  paragraph (or list item) outside units; the part is the anchor segment's locator in key form
  (``corpus_structure.core.locators``, P0-I-0, generated on the rendition) and the ordinal of the
  statement's first sentence among that segment's sentences. A context-premise assumption whose
  sentences fall inside another statement's anchor takes that statement's part;
- **revised + labels**: the same after the label rule.

Only the keys change: alignment runs on the unnormalized (or label-normalized) batches, so every
row has the same aligned pairs. All passes are on one rendition per page, where locator and
segment identity are one-to-one, so within the rendition the figures are comparable with the S0
rows (the brief's caveat).

Step 10. Over the v1 reference (``results/s0r2/reference_v1``, twelve units), facts whose meaning
key (claim key without ``statement``; I-R2 instruments) occurs in more than one unit, raw and
under the label rule.

Writes ``results/s6/keys.tsv``, ``results/s6/key_pairs.tsv`` (pairs whose claim keys still differ,
with causes), ``results/s6/restated.tsv`` and ``results/s6/keys.json``.
"""

from __future__ import annotations

import copy
import json
import sys
from collections import defaultdict
from pathlib import Path

CODE = Path(__file__).resolve().parent
EVIDENCE = CODE.parent
REPO = EVIDENCE.parents[3]
sys.path.insert(0, str(CODE))
sys.path.insert(1, str(REPO / "python" / "corpus-structure" / "src"))

from corpus_structure.core.evidence import RenditionContent, Segment  # noqa: E402
from corpus_structure.core.locators import LocatorIndex  # noqa: E402
from instruments.align import align_unit  # noqa: E402
from instruments.conditions import canonical_json  # noqa: E402
from instruments.keys import compute_keys, mismatch_causes  # noqa: E402
from instruments.scores import key_agreement  # noqa: E402
from s0d_compare import RENDITIONS, SAMPLE, comparator, side_for  # noqa: E402
from s0d_key_variants import normalize  # noqa: E402
from s6_load import page_segments  # noqa: E402

RESULTS = EVIDENCE / "results" / "s6"
A, B = EVIDENCE / "results" / "s0" / "stored" / "pass_a", EVIDENCE / "results" / "s0" / "stored" / "pass_b"
REF = EVIDENCE / "results" / "s0r2" / "reference_v1"
UNITS = [u for u in SAMPLE["units"] if (A / f"{u}.json").exists() and (B / f"{u}.json").exists()]


class Page:
    """One rendition: segments with their tree, sentences, and generated locators."""

    def __init__(self, page: str):
        self.page = page
        self.text, segs = page_segments(page)
        self.by_key = {s["key"]: s for s in segs}
        kids = defaultdict(list)
        for s in segs:
            kids[s.get("parent")].append(s)
        made = {}

        def build(s):
            seg = Segment(kind=s["kind"], start=s["start"], end=s["end"], parse_status=s.get("parse_status", "ok"),
                          parse_reason=s.get("parse_reason"), attrs={k: v for k, v in (s.get("attrs") or {}).items() if k == "id"},
                          children=tuple(build(c) for c in kids.get(s["key"], [])))
            made[s["key"]] = seg
            return seg

        root = next(s for s in segs if s["kind"] == "document")
        self.index = LocatorIndex(RenditionContent(canonical_text=self.text, document=build(root)), page)
        self.made = made
        self.sentences = sorted((s for s in segs if s["kind"] == "sentence"), key=lambda s: s["start"])

    def ancestors(self, key):
        out, k = [], key
        while k:
            out.append(self.by_key[k])
            k = self.by_key[k].get("parent")
        return out   # innermost first

    def sentences_in(self, seg):
        return [s for s in self.sentences if seg["start"] <= s["start"] and s["end"] <= seg["end"]]

    def locator_form(self, seg):
        return self.index.generate(self.made[seg["key"]]).key_form(RENDITIONS[self.page]["document_key"])


PAGES: dict[str, Page] = {}


def page_of(unit) -> Page:
    p = SAMPLE["units"][unit]["page"]
    if p not in PAGES:
        PAGES[p] = Page(p)
    return PAGES[p]


def revised_anchor(pg: Page, st: dict) -> tuple[dict, dict]:
    """ADR-0019's statement anchor: (anchor segment, key part)."""
    firsts = []
    for k in st.get("anchor") or []:
        s = pg.by_key[k]
        firsts.append(s if s["kind"] == "sentence" else (pg.sentences_in(s) or [s])[0])
    first = min(firsts, key=lambda s: s["start"])
    chain = pg.ancestors(first["key"])
    proofish = st.get("kind") in ("proof", "solution")
    anchor = (next((s for s in chain if s["kind"] == "details"), None) if proofish else None) \
        or next((s for s in chain if s["kind"] == "unit"), None) \
        or next((s for s in chain if s["kind"] in ("paragraph", "list_item")), None) or chain[-1]
    inside = pg.sentences_in(anchor)
    ordinal = next((i for i, s in enumerate(inside, start=1) if s["key"] == first["key"]), 1)
    return anchor, {"anchor": pg.locator_form(anchor), "ordinal": ordinal}


def revise(unit: str, batch: dict) -> tuple[dict, list[dict]]:
    """A copy whose statements carry the revised key part as their only anchor (keys only)."""
    b = copy.deepcopy(batch)
    pg = page_of(unit)
    info, parts = [], {}
    for st in b.get("statements", []):
        seg, part = revised_anchor(pg, st)
        parts[st["local_ref"]] = (seg, part)
    for st in b.get("statements", []):
        seg, part = parts[st["local_ref"]]
        joined = None
        if st.get("kind") == "assumption":
            for other, (oseg, opart) in parts.items():
                if other != st["local_ref"] and oseg["key"] == seg["key"] and opart["ordinal"] < part["ordinal"]:
                    joined, part = other, opart
                    break
        st["anchor"] = [canonical_json(part)]
        info.append({"statement": st["local_ref"], "kind": st.get("kind"), "anchor_kind": seg["kind"],
                     "locator": str(pg.index.generate(pg.made[seg["key"]])), "ordinal": part["ordinal"], "joined": joined})
    return b, info


def macros(unit):
    return RENDITIONS[SAMPLE["units"][unit]["page"]]["parse_detail"]["macros"]


def agreement(variant: str):
    anchors, labels, revised = "anchors" in variant.split("+"), "labels" in variant.split("+"), "revised" in variant.split("+")
    al, kr, kp, notes = [], {}, {}, {}
    for u in UNITS:
        ra, rb = json.loads((A / f"{u}.json").read_text()), json.loads((B / f"{u}.json").read_text())
        if anchors or labels:
            ra, rb = normalize(u, ra, anchors, labels), normalize(u, rb, anchors, labels)
        al.append(align_unit(side_for(u, ra), side_for(u, rb), comparator=comparator(u)))
        if revised:
            ka_b, ia = revise(u, ra)
            kb_b, ib = revise(u, rb)
            notes[u] = {"a": ia, "b": ib}
        else:
            ka_b, kb_b = ra, rb
        kr[u], kp[u] = compute_keys(ka_b, macros=macros(u)), compute_keys(kb_b, macros=macros(u))
    return al, kr, kp, notes


def main() -> int:
    variants = [("raw (D1 §10.1 as in S0)", "raw", "a_vs_b"), ("statement keyed by covering segment (S0 --anchors)", "anchors", "a_vs_b.keys_anchors"),
                ("global label from identity (S0 --labels)", "labels", "a_vs_b.keys_labels"), ("both (S0)", "anchors+labels", "a_vs_b.keys_both"),
                ("revised statement key (ADR-0019)", "revised", None), ("revised statement key + label rule", "revised+labels", None)]
    rows, out, pairs = [["variant", "aligned_pairs", "claim_keys_equal", "meaning_keys_equal", "s0_record_claim", "s0_record_meaning", "claim_causes"]], {}, []
    for label, v, s0 in variants:
        al, kr, kp, notes = agreement(v)
        ka = key_agreement(al, kr, kp, "core")
        ref = json.loads((EVIDENCE / "results" / "s0" / "compare" / s0 / "score.json").read_text())["keys_core"] if s0 else None
        rows.append([label, ka["pairs"], ka["claim_key_equal"], ka["meaning_key_equal"], ref["claim_key_equal"] if ref else "",
                     ref["meaning_key_equal"] if ref else "", json.dumps(ka["claim_causes"], sort_keys=True)])
        out[v] = {"pairs": ka["pairs"], "claim": ka["claim_key_equal"], "meaning": ka["meaning_key_equal"], "claim_causes": ka["claim_causes"],
                  "meaning_causes": ka["meaning_causes"], "matches_s0": (ka["claim_key_equal"], ka["meaning_key_equal"]) == (ref["claim_key_equal"], ref["meaning_key_equal"]) if ref else None}
        if v.startswith("revised"):
            out[v]["statements"] = notes
            for ua in al:
                for a, b in ua.matches.get("core", []):
                    x, y = kr[ua.unit], kp[ua.unit]
                    if x.claim.get(a) is None or x.claim.get(a) != y.claim.get(b):
                        pairs.append([v, ua.unit, a, b, ",".join(mismatch_causes(x, a, y, b)), ",".join(mismatch_causes(x, a, y, b, meaning=True)) or "(meaning keys equal)"])
    with (RESULTS / "keys.tsv").open("w") as f:
        for r in rows:
            f.write("\t".join(str(x) for x in r) + "\n")
    with (RESULTS / "key_pairs.tsv").open("w") as f:
        f.write("variant\tunit\tpass_a\tpass_b\tclaim_key_causes\tmeaning_key_causes\n")
        for r in pairs:
            f.write("\t".join(r) + "\n")

    # step 10: restated facts over the v1 reference
    rest_rows = [["rule", "meaning_key", "predicate", "subject", "object", "units", "statements"]]
    restated = {}
    for rule in ("raw", "labels"):
        groups = defaultdict(list)
        for f in sorted(REF.glob("*.json")):
            u = f.stem
            if u not in SAMPLE["units"]:
                continue
            b = json.loads(f.read_text())
            if rule == "labels":
                b = normalize(u, b, False, True)
            k = compute_keys(b, macros=macros(u))
            ents = {e["local_ref"]: e for e in b.get("entities", [])} | {s["local_ref"]: {"label": f"{s['kind']} {s['local_ref']}"} for s in b.get("statements", [])}
            for c in b.get("claims", []):
                mk = k.meaning.get(c["local_ref"])
                if mk:
                    obj = c.get("object") or {}
                    o = ents.get(obj.get("ref"), {}).get("label") if set(obj) == {"ref"} else (obj.get("latex") or obj.get("v") or obj.get("t"))
                    groups[mk].append((u, c.get("statement"), c["predicate"], ents.get(c["subject"], {}).get("label"), o, c["local_ref"],
                                       ents.get(c["subject"], {}).get("scope") == "global"))
        multi = {mk: g for mk, g in groups.items() if len({x[0] for x in g}) > 1}
        within = {mk: g for mk, g in groups.items() if len({x[0] for x in g}) == 1 and len({x[1] for x in g}) > 1}
        restated[rule] = {"facts": len(groups), "facts_with_a_global_subject": len({mk for mk, g in groups.items() if g[0][6]}),
                          "restated_across_units": len(multi), "restated_within_a_unit": len(within),
                          "claims_in_restated_facts": sum(len(g) for g in multi.values())}
        if not multi:
            rest_rows.append([rule, "(none)", "", "", "", "", f"no meaning key in more than one unit among {len(groups)} facts "
                              f"({restated[rule]['facts_with_a_global_subject']} with a global subject; local subjects are scoped to their unit)"])
        for mk, g in sorted(multi.items(), key=lambda kv: kv[1][0][2]):
            rest_rows.append([rule, mk, g[0][2], g[0][3], g[0][4], ",".join(sorted({x[0] for x in g})), ",".join(f"{x[0]}:{x[1]}:{x[5]}" for x in g)])
    with (RESULTS / "restated.tsv").open("w") as f:
        for r in rest_rows:
            f.write("\t".join("" if x is None else str(x) for x in r) + "\n")
    out["restated"] = restated
    out["units"] = UNITS
    (RESULTS / "keys.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str) + "\n")
    for r in rows:
        print(r[:6])
    print(restated)
    print(len(pairs), "differing pairs (both revised variants)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
