"""S1-C: score sentence-segmentation combinations against the adjudicated boundary gold.

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/s1c_score.py [agreement|score]

agreement: compares marker_a.json and marker_b.json (results/s1/gold/), writes gold_agreement.json
and disagreements.md for adjudication. score: reads gold.json (adjudicated), scores every
combination, writes results/s1/sentences.tsv, sentences_errors.json and proxies.json.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from s1_adapter import EVIDENCE, adapt  # noqa: E402
from s1_sentences import PIPELINES, blocks_of, split_block  # noqa: E402

GOLD = EVIDENCE / "results" / "s1" / "gold"
MATH = ["a", "b1", "b2", "bp", "d"]


def starts_from_sentences(text: str, sentences: list[str]) -> tuple[list[int], list[str]]:
    """Locate each sentence in order; return start offsets (excluding the first) and problems."""
    pos, starts, problems = 0, [], []
    for i, s in enumerate(sentences):
        j = text.find(s, pos)
        if j < 0:
            j2 = text.find(s.strip(), pos)
            if j2 < 0:
                problems.append(f"sentence {i + 1} not found: {s[:60]!r}")
                continue
            j = j2
        if i > 0:
            starts.append(j)
        pos = j + len(s)
    return starts, problems


def load_blocks() -> dict[str, dict]:
    sample = json.loads((GOLD / "sample.json").read_text())
    return {b["id"]: b for b in sample["blocks"]}


def agreement() -> int:
    blocks = load_blocks()
    a = json.loads((GOLD / "marker_a.json").read_text())
    b = json.loads((GOLD / "marker_b.json").read_text())
    same = differ = 0
    tp = fa = fb = 0
    lines = ["# Sentence gold: marker A versus marker B disagreements", ""]
    problems = {}
    for bid, blk in blocks.items():
        sa, pa = starts_from_sentences(blk["text"], a.get(bid, []))
        sb, pb = starts_from_sentences(blk["text"], b.get(bid, []))
        if pa or pb:
            problems[bid] = {"a": pa, "b": pb}
        A, B = set(sa), set(sb)
        tp += len(A & B)
        fa += len(A - B)
        fb += len(B - A)
        if A == B:
            same += 1
        else:
            differ += 1
            lines += [f"## {bid}", "", "```text", blk["text"], "```", "",
                      "Only A: " + "; ".join(repr(blk["text"][max(0, x - 30):x] + " ‖ " + blk["text"][x:x + 20]) for x in sorted(A - B)),
                      "", "Only B: " + "; ".join(repr(blk["text"][max(0, x - 30):x] + " ‖ " + blk["text"][x:x + 20]) for x in sorted(B - A)), ""]
    res = {"blocks": len(blocks), "identical_blocks": same, "differing_blocks": differ,
           "boundaries_both": tp, "only_a": fa, "only_b": fb, "location_problems": problems}
    (GOLD / "gold_agreement.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")
    (GOLD / "disagreements.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "location_problems"}), "problems:", len(problems))
    return 0


def categorize(text: str, cut: int, block: dict) -> str:
    before, after = text[:cut].rstrip(), text[cut:]
    if any(m["start"] < cut < m["end"] for m in block["math"]):
        return "inside math"
    if re.search(r"\b(i\.e|e\.g|cf|etc)\.$", before):
        return "after abbreviation"
    if any(r["start"] <= cut <= r["end"] for r in block.get("refs", [])):
        return "at reference marker"
    if re.match(r"\((?:[a-z])\)\s", text[max(0, cut - 4):cut + 1]) or re.match(r"^\([a-z]\)\s*$", before[-4:]):
        return "after list marker"
    if before.endswith("\\]"):
        return "after display math"
    if re.match(r"(Then|where|so|and)\b", after):
        return "before Then/where/so/and"
    if before and before[-1] not in ".?!":
        return "mid-clause"
    return "other"


def score() -> int:
    blocks = load_blocks()
    gold = json.loads((GOLD / "gold.json").read_text())
    renditions = {p: adapt(p) for p in {b["page"] for b in blocks.values()}}
    rblocks = {}
    for p, r in renditions.items():
        for b in blocks_of(r):
            rblocks[(p, b["key"])] = (b, r["rendition"]["parse_detail"]["macros"])
    combos = [(p, m + c) for p in PIPELINES for m in MATH for c in ("", "+c")]
    rows, errors, proxies = [], {}, {}
    for pipe, math in combos:
        tp = fp = fn = 0
        cats_fp, cats_fn = Counter(), Counter()
        lower_start = math_start = 0
        n_sent = 0
        block_err, block_proxy = [], []
        for bid, meta in blocks.items():
            b, macros = rblocks[(meta["page"], meta["key"])]
            g, _ = starts_from_sentences(b["text"], gold[bid])
            G = set(g)
            P = set(split_block(b, pipe, math, macros))
            tp += len(P & G)
            fp += len(P - G)
            fn += len(G - P)
            for x in P - G:
                cats_fp[categorize(b["text"], x, b)] += 1
            for x in G - P:
                cats_fn[categorize(b["text"], x, b)] += 1
            cuts = sorted(P)
            n_sent += len(cuts) + 1
            flagged = 0
            for x in cuts:
                nxt = b["text"][x:x + 3]
                if nxt[:1].islower():
                    lower_start += 1
                    flagged += 1
                if nxt.startswith("\\("):
                    math_start += 1
                    flagged += 1
            block_err.append(int(bool(P ^ G)))
            block_proxy.append(int(flagged > 0))
        prec = tp / (tp + fp) if tp + fp else 1.0
        rec = tp / (tp + fn) if tp + fn else 1.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        rows.append({"pipeline": pipe, "math": math, "tp": tp, "fp": fp, "fn": fn, "precision": round(prec, 3),
                     "recall": round(rec, 3), "f1": round(f1, 3), "sentences": n_sent,
                     "fp_inside_math": cats_fp["inside math"], "fp_after_abbrev": cats_fp["after abbreviation"],
                     "fp_before_then": cats_fp["before Then/where/so/and"], "fn_after_display": cats_fn["after display math"]})
        errors[f"{pipe}/{math}"] = {"fp": dict(cats_fp), "fn": dict(cats_fn)}
        both = sum(1 for e, q in zip(block_err, block_proxy, strict=True) if e and q)
        proxies[f"{pipe}/{math}"] = {"blocks_with_errors": sum(block_err), "blocks_flagged_by_proxy": sum(block_proxy),
                                     "flagged_and_erroneous": both, "lower_start": lower_start, "math_start": math_start}
        print(pipe, math, rows[-1]["f1"], rows[-1]["fp"], rows[-1]["fn"], flush=True)
    out = EVIDENCE / "results" / "s1"
    with (out / "sentences.tsv").open("w", encoding="utf-8") as f:
        f.write("\t".join(rows[0]) + "\n")
        for r in rows:
            f.write("\t".join(str(v) for v in r.values()) + "\n")
    (out / "sentences_errors.json").write_text(json.dumps(errors, indent=2) + "\n")
    (out / "sentences_proxies.json").write_text(json.dumps(proxies, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit({"agreement": agreement, "score": score}[sys.argv[1] if len(sys.argv) > 1 else "score"]())
