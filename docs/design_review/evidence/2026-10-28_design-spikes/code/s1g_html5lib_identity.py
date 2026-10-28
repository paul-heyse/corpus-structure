"""S1-G: do the stored libxml2 renditions of every page an S0/S0-R2 unit uses survive a switch to html5lib?

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/s1g_html5lib_identity.py

For the four spike pages (stored under results/s1/) and the three S0-R2 pages (results/s0r2/s1/), adapt
the page with parser html5lib and with parser lxml (a reproducibility check of the stored rendition), split
sentences as S1-B does (P1 + bp+c), and compare with the stored files byte for byte:

- text: the canonical text's UTF-8 bytes;
- segments: per position, canonical JSON of (kind, start, end, attrs, parse_status, reason, parent position);
  keys are rendition-scoped (make_key over the rendition key, which hashes the configuration and so the
  parser), so they are compared through the position projection and reported as a mapping instead;
- sentences: per position, canonical JSON of (kind, start, end, parent position);
- every S0/S0-R2 unit (results/s0r2/sample.json): unit text sha256 and its sentence offsets;
- the S1-B locators (profile/slices.yaml trace + core12) on the four spike pages.

Writes results/s1_html5lib/rendition_comparison.{tsv,json}; and rendition_identity.tsv only when text,
segments and sentences are identical for every page. Never writes sample.json or any stored rendition.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
from s1_adapter import EVIDENCE, adapt, canonical_json  # noqa: E402
from s1_sentences import sentences  # noqa: E402
from s1b_sample import check_slices  # noqa: E402

OUT = EVIDENCE / "results" / "s1_html5lib"
SAMPLE = json.loads((EVIDENCE / "results" / "s0r2" / "sample.json").read_text())
STORED = {  # page -> stored rendition folder (the folder holding canonical/, segments/, sentences/)
    **{p: "results/s1" for p in ("special/LocationScale.html", "special/Normal.html",
                                 "special/LogNormal.html", "special/Gamma.html")},
    **{p: "results/s0r2/s1" for p in ("special/Pareto.html", "special/ChiSquare.html", "special/Weibull.html")},
}


def name_of(page: str) -> str:
    return page.replace("/", "__").removesuffix(".html")


def jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def stored(page: str) -> dict:
    d = EVIDENCE / STORED[page]
    n = name_of(page)
    rens = json.loads((d / "renditions.json").read_text())
    return {"text": (d / "canonical" / f"{n}.txt").read_bytes().decode("utf-8"),
            "segments": jsonl(d / "segments" / f"{n}.jsonl"),
            "sentences": jsonl(d / "sentences" / f"{n}.provisional.jsonl"),
            "rendition_key": rens[page]["rendition_key"]}


def seg_proj(segs: list[dict], drop_attrs: tuple[str, ...] = ()) -> list[str]:
    pos = {s["key"]: i for i, s in enumerate(segs)}
    return [canonical_json([s["kind"], s["start"], s["end"],
                            {k: v for k, v in s["attrs"].items() if k not in drop_attrs},
                            s["parse_status"], s.get("reason"), pos.get(s["parent"])]) for s in segs]


def sent_proj(sents: list[dict], segs: list[dict]) -> list[str]:
    pos = {s["key"]: i for i, s in enumerate(segs)}
    return [canonical_json([s["kind"], s["start"], s["end"], pos.get(s["parent"])]) for s in sents]


def first_diffs(a: list[str], b: list[str], n: int = 5) -> list[dict]:
    out = [{"index": i, "libxml2": x, "html5lib": y} for i, (x, y) in enumerate(zip(a, b, strict=False)) if x != y]
    return out[:n]


def attr_diffs(a: list[dict], b: list[dict]) -> dict:
    """Per attribute name: how many positions differ, and the first examples."""
    count: Counter = Counter()
    ex: dict[str, list] = {}
    for i, (x, y) in enumerate(zip(a, b, strict=False)):
        for k in sorted(set(x["attrs"]) | set(y["attrs"])):
            if x["attrs"].get(k) != y["attrs"].get(k):
                count[k] += 1
                if len(ex.setdefault(k, [])) < 3:
                    ex[k].append({"index": i, "kind": x["kind"], "start": x["start"], "end": x["end"],
                                  "libxml2": x["attrs"].get(k), "html5lib": y["attrs"].get(k)})
    return {k: {"positions": v, "examples": ex[k]} for k, v in count.items()}


def compare(old: dict, new: dict, new_sents: list[dict]) -> dict:
    so, sn = seg_proj(old["segments"]), seg_proj(new["segments"])
    so_ns, sn_ns = seg_proj(old["segments"], ("sourceline",)), seg_proj(new["segments"], ("sourceline",))
    to, tn = sent_proj(old["sentences"], old["segments"]), sent_proj(new_sents, new["segments"])
    kse = [canonical_json([s["kind"], s["start"], s["end"]]) for s in old["segments"]] == \
          [canonical_json([s["kind"], s["start"], s["end"]]) for s in new["segments"]]
    return {
        "text_identical": old["text"].encode() == new["text"].encode(),
        "text_sha256": [hashlib.sha256(old["text"].encode()).hexdigest(), hashlib.sha256(new["text"].encode()).hexdigest()],
        "segments": [len(so), len(sn)],
        "segments_kind_start_end_identical": kse,
        "segments_identical": so == sn,
        "segments_identical_except_sourceline": so_ns == sn_ns,
        "segment_diffs": first_diffs(so, sn),
        "attr_diffs": attr_diffs(old["segments"], new["segments"]),
        "sentences": [len(to), len(tn)],
        "sentences_identical": to == tn,
        "sentence_diffs": first_diffs(to, tn),
    }


def unit_check(uid: str, meta: dict, new: dict, new_sents: list[dict]) -> dict:
    parts = []
    for p in meta["parts"]:
        seg = next((s for s in new["segments"] if (s["kind"], s["start"], s["end"]) == (p["kind"], p["start"], p["end"])), None)
        sha = hashlib.sha256(new["text"][p["start"]:p["end"]].encode()).hexdigest()
        inside = [s for s in new_sents if p["start"] <= s["start"] and s["end"] <= p["end"]]
        parts.append({"locator": p["locator"], "sha256_identical": sha == p["sha256"],
                      "segment_present": seg is not None, "old_segment_key": p["segment_key"],
                      "new_segment_key": seg["key"] if seg else None,
                      "sentence_offsets_identical": [(s["start"], s["end"]) for s in inside]
                      == [(s["start"], s["end"]) for s in p["sentences"]],
                      "sentence_keys": [[s["key"], n["key"]] for s, n in zip(p["sentences"], inside, strict=False)]})
    ctx_ok = all(any((s["start"], s["end"]) == (c["start"], c["end"]) for s in new_sents) for c in meta.get("context", []))
    return {"unit": uid, "page": meta["page"], "set": meta.get("set"), "parts": parts, "context_sentences_present": ctx_ok,
            "ok": ctx_ok and all(x["sha256_identical"] and x["segment_present"] and x["sentence_offsets_identical"]
                                 for x in parts)}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows, detail, h5_renditions = [], {}, {}
    for page in STORED:
        old = stored(page)
        lx = adapt(page, {"parser": "lxml"})
        lx_sents = sentences(lx, "P1", "bp+c")
        h5 = adapt(page, {"parser": "html5lib"})
        h5_sents = sentences(h5, "P1", "bp+c")
        h5_renditions[page] = h5
        repro = compare(old, lx, lx_sents)
        repro["rendition_key_identical"] = lx["rendition"]["rendition_key"] == old["rendition_key"]
        repro["segment_keys_identical"] = [s["key"] for s in lx["segments"]] == [s["key"] for s in old["segments"]]
        repro["sentence_keys_identical"] = [s["key"] for s in lx_sents] == [s["key"] for s in old["sentences"]]
        c = compare(old, h5, h5_sents)
        detail[page] = {"libxml2_rendition_key": old["rendition_key"],
                        "html5lib_rendition_key": h5["rendition"]["rendition_key"],
                        "stored_dir": STORED[page], "html5lib_vs_stored": c, "fresh_lxml_vs_stored": repro,
                        "orphans": [len(lx["rendition"]["parse_detail"]["orphans"]),
                                    len(h5["rendition"]["parse_detail"]["orphans"])]}
        rows.append({"page": page, "libxml2_rendition_key": old["rendition_key"],
                     "html5lib_rendition_key": h5["rendition"]["rendition_key"],
                     "text_identical": c["text_identical"],
                     "segments_kind_start_end_identical": c["segments_kind_start_end_identical"],
                     "segments_identical": c["segments_identical"],
                     "segments_identical_except_sourceline": c["segments_identical_except_sourceline"],
                     "differing_attrs": ";".join(f"{k}:{v['positions']}" for k, v in sorted(c["attr_diffs"].items())),
                     "segments": c["segments"][1], "sentences_identical": c["sentences_identical"],
                     "sentences": c["sentences"][1],
                     "stored_reproduced_by_fresh_lxml": repro["text_identical"] and repro["segments_identical"]
                     and repro["sentences_identical"] and repro["rendition_key_identical"]
                     and repro["segment_keys_identical"] and repro["sentence_keys_identical"]})
        print(page, {k: rows[-1][k] for k in ("text_identical", "segments_identical", "segments_identical_except_sourceline",
                                               "differing_attrs", "sentences_identical", "stored_reproduced_by_fresh_lxml")},
              flush=True)
    units = {}
    for uid, meta in SAMPLE["units"].items():
        page = meta["page"]
        h5 = h5_renditions[page]
        units[uid] = unit_check(uid, meta, h5, sentences(h5, "P1", "bp+c"))
    old_loc = json.loads((EVIDENCE / "results" / "s1" / "locators.json").read_text())
    new_loc = check_slices(h5_renditions)
    loc = {}
    for k, v in old_loc.items():
        page = k.split("#")[0].split("@")[0]
        old_segs = {s["key"]: s for s in stored(page)["segments"]}
        new_segs = {s["key"]: s for s in h5_renditions[page]["segments"]}
        n = new_loc.get(k, {})
        same = [(old_segs[a]["kind"], old_segs[a]["start"], old_segs[a]["end"]) for a in v["segments"]] == \
               [(new_segs[b]["kind"], new_segs[b]["start"], new_segs[b]["end"]) for b in n.get("segments", [])]
        loc[k] = {"libxml2": {"matches": v["matches"], "ok": v["ok"]},
                  "html5lib": {"matches": n.get("matches"), "ok": n.get("ok")}, "same_segment_span": same}
    pages_identical = all(r["text_identical"] and r["segments_identical"] and r["sentences_identical"] for r in rows)
    summary = {
        "pages": len(rows),
        "text_identical": sum(r["text_identical"] for r in rows),
        "segments_kind_start_end_identical": sum(r["segments_kind_start_end_identical"] for r in rows),
        "segments_identical": sum(r["segments_identical"] for r in rows),
        "segments_identical_except_sourceline": sum(r["segments_identical_except_sourceline"] for r in rows),
        "sentences_identical": sum(r["sentences_identical"] for r in rows),
        "stored_reproduced_by_fresh_lxml": sum(r["stored_reproduced_by_fresh_lxml"] for r in rows),
        "units": len(units), "units_ok": sum(u["ok"] for u in units.values()),
        "locators": len(loc), "locators_ok_html5lib": sum(bool(v["html5lib"]["ok"]) for v in loc.values()),
        "locators_same_span": sum(v["same_segment_span"] for v in loc.values()),
        "identity": pages_identical,
    }
    with (OUT / "rendition_comparison.tsv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    (OUT / "rendition_comparison.json").write_text(json.dumps(
        {"summary": summary, "pages": detail, "units": units, "locators": loc}, indent=1, ensure_ascii=False) + "\n")
    if pages_identical:
        with (OUT / "rendition_identity.tsv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["page", "libxml2_rendition_key", "html5lib_rendition_key", "text_identical",
                        "segments_identical", "sentences_identical"])
            for r in rows:
                w.writerow([r["page"], r["libxml2_rendition_key"], r["html5lib_rendition_key"], r["text_identical"],
                            r["segments_identical"], r["sentences_identical"]])
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
