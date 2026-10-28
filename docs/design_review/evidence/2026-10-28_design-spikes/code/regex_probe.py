"""regex probe (2026-10-28): two questions for the regex 2026.9.29 engine (docs/libraries/regex.md).

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/regex_probe.py

A. Quote location (D4 §4.3 tiers 3-4). Every evidence quote of passes A, B, P, H and the reference
   is located exactly (ground truth), then perturbed in seeded ways an LLM quote goes wrong
   (LaTeX re-spacing, a typo, a dropped word, a trimmed end, an added trailing period, \\R spelled
   \\mathbb{R}). Each perturbed quote is located by
     current  s0_locate.locate_quote (normalized tier 3, rapidfuzz tier 4)
     ws       regex: the quote's non-space characters joined by (?:\\s|\\[,;!])* — exact up to
              spacing, offsets in the original text, no offset map
     fuzzy    regex BESTMATCH, (?:quote){e<=k}, k = ceil(0.15 len), inside the cited sentence
     fuzzy_w  fuzzy, then the span snapped outward to word boundaries
   Scored against the unperturbed span: exact, overlap (IoU), and whether an end cuts a word.
B. Math delimiting (M01). One regex — opener, body that stops at the next delimiter, optional
   closer, (*SKIP)(*F) over "\\\\", bare display environments — against s1_adapter.scan_math
   on the spike pages' exported blocks (results/s1/blocks/).
C. Lark with regex=True: the probe's extended SymPy grammar built with the regex engine gives the
   same results as with re on the S0 values.
Writes results/regex_probe/{quotes.tsv,summary.json}.
"""

from __future__ import annotations

import json
import math
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import regex

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
from s0_check import context  # noqa: E402
from s0_locate import locate_quote  # noqa: E402
from s1_adapter import scan_math  # noqa: E402

EVIDENCE = CODE.parent
S0 = EVIDENCE / "results" / "s0"
OUT = EVIDENCE / "results" / "regex_probe"
SAMPLE = json.loads((EVIDENCE / "sample.json").read_text())
SPACING = r"(?:\s|\\[,;!])*"


def quotes() -> list[tuple[str, str, str]]:
    out = set()
    for d in [S0 / "pass_a", S0 / "pass_b", S0 / "pass_p", S0 / "pass_h", S0 / "reference_model"]:
        for f in d.glob("[TU]*.json"):
            b = json.loads(f.read_text())

            def walk(o):
                if isinstance(o, dict):
                    if isinstance(o.get("quote"), str) and isinstance(o.get("sentence"), str):
                        out.add((f.stem, o["sentence"], o["quote"]))
                    for v in o.values():
                        walk(v)
                elif isinstance(o, list):
                    for v in o:
                        walk(v)
            walk(b)
    return sorted(out)


def perturb(q: str, kind: str, rng: random.Random) -> str | None:
    words = q.split(" ")
    if kind == "respace":  # LaTeX spacing changed
        if "\\(" not in q and "\\[" not in q:
            return None
        return regex.sub(r"\s*([=+\-<>,])\s*", r" \1 ", q).replace("\\( ", "\\(").replace(" \\)", "\\)")
    if kind == "typo":
        idx = [i for i, c in enumerate(q) if c.isalpha() and (i == 0 or q[i - 1] != "\\")]
        if len(idx) < 8:
            return None
        i = rng.choice(idx[2:-2])
        return q[:i] + ("e" if q[i] != "e" else "a") + q[i + 1:]
    if kind == "drop_word":
        cand = [i for i, w in enumerate(words) if 3 <= len(w) and w.isalpha() and 0 < i < len(words) - 1]
        if len(words) < 6 or not cand:
            return None
        i = rng.choice(cand)
        return " ".join(words[:i] + words[i + 1:])
    if kind == "trim_end":
        return q[:-2] if len(q) > 20 and q[-2].isalnum() else None
    if kind == "add_period":
        return q + "." if not q.endswith(".") else None
    if kind == "macro":
        return q.replace("\\R", "\\mathbb{R}") if "\\R" in q else None
    raise ValueError(kind)


def ws_pattern(q: str) -> str:
    return SPACING.join(regex.escape(c) for c in q if not c.isspace())


def snap(text: str, a: int, b: int, lo: int, hi: int) -> tuple[int, int]:
    while a > lo and text[a - 1].isalnum() and text[a].isalnum():
        a -= 1
    while b < hi and text[b - 1].isalnum() and text[b].isalnum():
        b += 1
    return a, b


def cuts_word(text: str, a: int, b: int) -> bool:
    return (a > 0 and text[a - 1].isalnum() and text[a].isalnum()) or (b < len(text) and text[b - 1].isalnum() and text[b].isalnum())


UNIT = [""]
REN = json.loads((EVIDENCE / "results" / "s1" / "renditions.json").read_text())
MACROS = {page: {name.strip(): m["body"].strip() for name, m in (r.get("parse_detail", {}).get("macros") or {}).items()
                 if m.get("nargs", 0) == 0}
          for page, r in REN.items()}


def locate_all(text, sent, q, ctx, sid):
    res = {}
    t0 = time.perf_counter()
    r = locate_quote(q, sid, ctx)
    res["current"] = (r.start, r.end, r.tier, time.perf_counter() - t0)
    lo, hi = sent
    t0 = time.perf_counter()
    m = regex.search(ws_pattern(q), text, pos=lo, endpos=hi, timeout=1.0)
    res["ws"] = (m.start(), m.end(), "ws", time.perf_counter() - t0) if m else (None, None, None, 0)
    k = max(1, math.ceil(0.15 * len(q)))
    t0 = time.perf_counter()
    try:
        m = regex.search(r"(?b)(?:" + regex.escape(q) + "){e<=" + str(k) + "}", text, pos=lo, endpos=hi, timeout=2.0)
    except TimeoutError:
        m = None
    dt = time.perf_counter() - t0
    res["fuzzy"] = (m.start(), m.end(), m.fuzzy_counts, dt) if m else (None, None, None, dt)
    res["fuzzy_w"] = (*snap(text, m.start(), m.end(), lo, hi), m.fuzzy_counts, dt) if m else (None, None, None, dt)
    # weighted: substitutions cost 2, so an extra or missing edge character is a deletion/insertion,
    # not a substitution that drags the span one character too far; edge punctuation trimmed first
    qq = q.rstrip(".,;:")  # trailing punctuation is the commonest LLM addition; the snap restores a real one
    k2 = max(2, math.ceil(0.30 * len(qq)))
    t0 = time.perf_counter()
    try:
        m = regex.search(r"(?b)(?:" + regex.escape(qq) + "){1i+1d+2s<=" + str(k2) + "}", text, pos=lo, endpos=hi, timeout=1.0)
        timed_out = False
    except TimeoutError:
        m, timed_out = None, True
    dt = time.perf_counter() - t0
    res["fuzzy_c"] = (*snap(text, m.start(), m.end(), lo, hi), m.fuzzy_counts, dt) if m else (None, None, "timeout" if timed_out else None, dt)
    # macro-normalized: the page's \R-style macros expanded on both sides, then the ws pattern
    exp = MACROS.get(SAMPLE["units"][UNIT[0]]["page"], {})
    qx = q
    for name, body in sorted(exp.items(), key=lambda kv: -len(kv[0])):
        qx = regex.sub(regex.escape(body), lambda _m, n=name: n, qx)
    t0 = time.perf_counter()
    m = regex.search(ws_pattern(qx), text, pos=lo, endpos=hi, timeout=1.0)
    res["macro_ws"] = (m.start(), m.end(), "macro_ws", time.perf_counter() - t0) if m else (None, None, None, 0)
    # fuzzy_p: unit-cost BESTMATCH on the quote without trailing punctuation, then snapped
    k = max(1, math.ceil(0.15 * len(qq)))
    t0 = time.perf_counter()
    try:
        m = regex.search(r"(?b)(?:" + regex.escape(qq) + "){e<=" + str(k) + "}", text, pos=lo, endpos=hi, timeout=1.0)
    except TimeoutError:
        m = None
    dt = time.perf_counter() - t0
    res["fuzzy_p"] = (*snap(text, m.start(), m.end(), lo, hi), m.fuzzy_counts, dt) if m else (None, None, None, dt)
    # rf_snap: rapidfuzz alignment (cutoff 85) snapped to word boundaries
    from rapidfuzz import fuzz
    t0 = time.perf_counter()
    r = fuzz.partial_ratio_alignment(qq, text[lo:hi], score_cutoff=85)
    dt = time.perf_counter() - t0
    res["rf_snap"] = (*snap(text, lo + r.dest_start, lo + r.dest_end, lo, hi), round(r.score, 1), dt) if r else (None, None, None, dt)
    # hybrid: the rapidfuzz window (widened by 30% of the quote) bounds an ENHANCEMATCH fuzzy search
    t0 = time.perf_counter()
    m = None
    if r:
        pad = math.ceil(0.3 * len(qq))
        wlo, whi = max(lo, lo + r.dest_start - pad), min(hi, lo + r.dest_end + pad)
        try:
            m = regex.search(r"(?e)(?:" + regex.escape(qq) + "){e<=" + str(k) + "}", text, pos=wlo, endpos=whi, timeout=0.5)
        except TimeoutError:
            m = None
    dt = time.perf_counter() - t0
    res["hybrid"] = ((*snap(text, m.start(), m.end(), lo, hi), m.fuzzy_counts, dt) if m
                     else (res["rf_snap"][0], res["rf_snap"][1], "rf", dt) if r else (None, None, None, dt))
    # refine: BESTMATCH inside the rapidfuzz window (small region, short timeout); rf_snap when it fails
    t0 = time.perf_counter()
    m = None
    if r:
        try:
            m = regex.search(r"(?b)(?:" + regex.escape(qq) + "){e<=" + str(k) + "}", text, pos=wlo, endpos=whi, timeout=0.2)
        except TimeoutError:
            m = None
    dt = time.perf_counter() - t0
    res["refine"] = ((*snap(text, m.start(), m.end(), lo, hi), m.fuzzy_counts, dt) if m
                     else (res["rf_snap"][0], res["rf_snap"][1], "rf", dt) if r else (None, None, None, dt))
    # proposed cascade: exact (tiers 1-2) -> ws -> macro_ws -> refine -> coarse; every span snapped to words
    cur = res["current"] if res["current"][2] in (1, 2) else None
    for meth in ("ws", "macro_ws", "refine"):
        if cur is None and res[meth][0] is not None:
            cur = res[meth]
    if cur is None:
        cur = (None, None, "coarse", 0)
    else:
        cur = (*snap(text, cur[0], cur[1], lo, hi), cur[2], cur[3])
    res["cascade"] = cur
    return res


def part_a() -> dict:
    rng = random.Random(20261028)
    rows, ctxs = [], {}
    kinds = ["respace", "typo", "drop_word", "trim_end", "add_period", "macro"]
    for unit, sid, q in quotes():
        ctx = ctxs.setdefault(unit, context(unit))
        UNIT[0] = unit
        gt = locate_quote(q, sid, ctx)
        if gt.tier not in (1, 2) or sid not in ctx.sentences:
            continue
        sent = ctx.sentences[sid]
        for kind in kinds:
            pq = perturb(q, kind, rng)
            if pq is None or pq == q:
                continue
            res = locate_all(ctx.text, sent, pq, ctx, sid)
            for meth, (a, b, info, dt) in res.items():
                if a is None:
                    rows.append({"unit": unit, "kind": kind, "method": meth, "found": False, "exact": False, "iou": 0.0,
                                 "cut": False, "info": str(info), "ms": round(dt * 1000, 3), "quote": pq[:80]})
                    continue
                if meth == "current" and info is None or info == "coarse":  # the cited-sentence fallback
                    rows.append({"unit": unit, "kind": kind, "method": meth, "found": False, "exact": False, "iou": 0.0,
                                 "cut": False, "info": "coarse", "ms": round(dt * 1000, 3), "quote": pq[:80]})
                    continue
                inter = max(0, min(b, gt.end) - max(a, gt.start))
                union = max(b, gt.end) - min(a, gt.start)
                rows.append({"unit": unit, "kind": kind, "method": meth, "found": True,
                             "exact": (a, b) == (gt.start, gt.end), "iou": round(inter / union, 3),
                             "cut": cuts_word(ctx.text, a, b) and not cuts_word(ctx.text, gt.start, gt.end),
                             "info": str(info), "ms": round(dt * 1000, 3), "quote": pq[:80]})
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "quotes.tsv").open("w", encoding="utf-8") as fh:
        fh.write("\t".join(rows[0]) + "\n")
        for r in rows:
            fh.write("\t".join(str(v).replace("\t", " ") for v in r.values()) + "\n")
    agg = defaultdict(lambda: Counter())
    ms = defaultdict(list)
    for r in rows:
        key = (r["kind"], r["method"])
        agg[key]["n"] += 1
        agg[key]["found"] += r["found"]
        agg[key]["exact"] += r["exact"]
        agg[key]["iou>=0.9"] += r["iou"] >= 0.9
        agg[key]["cut"] += r["cut"]
        ms[r["method"]].append(r["ms"])
    table = {f"{k}|{m}": dict(v) for (k, m), v in sorted(agg.items())}
    return {"n_quotes": len({(r['unit'], r['quote']) for r in rows}), "by_kind_method": table,
            "ms_max": {m: max(v) for m, v in ms.items()}, "ms_median": {m: sorted(v)[len(v) // 2] for m, v in ms.items()}}


MATH_RE = regex.compile(r"""(?V1)
    \\\\ (*SKIP)(*F)                                   # an escaped backslash is never a delimiter
  | (?P<open>\\[(\[])                                   # \( or \[
    (?P<body>(?:\\\\ | (?!\\[()\[\]]) .)*+)             # stops at the next delimiter: resync like the scanner
    (?P<close>\\[)\]])?
  | (?P<env>\\begin\{(?P<name>align\*?)\}) .*? (?:\\end\{(?P=name)\} | \Z)
""", regex.VERBOSE | regex.DOTALL)


def part_b() -> dict:
    same = diff = 0
    examples = []
    for f in sorted((EVIDENCE / "results" / "s1" / "blocks").glob("*.jsonl")):
        for line in f.read_text().splitlines():
            b = json.loads(line)
            s = b["text"]
            ref, _ = scan_math(s, ["align", "align*"])
            ref_spans = [(x["start"], x["end"], x["status"]) for x in ref]
            got = []
            for m in MATH_RE.finditer(s, timeout=5.0):
                if m.group("open"):
                    ok = m.group("close") is not None and {"\\(": "\\)", "\\[": "\\]"}[m.group("open")] == m.group("close")
                    got.append((m.start(), m.end(), "ok" if ok else "partial"))
                else:
                    got.append((m.start(), m.end(), "ok" if m.group(0).rstrip().endswith("}") else "partial"))
            if got == ref_spans:
                same += 1
            else:
                diff += 1
                if len(examples) < 8:
                    examples.append({"block": b["segment"], "scanner": ref_spans[:4], "regex": got[:4]})
    return {"blocks_same": same, "blocks_different": diff, "examples": examples}


def part_c() -> dict:
    import lark_probe as lp
    import lark
    text = (lp.GRAMMAR_DIR / "latex.lark").read_text(encoding="utf-8") + lp.EXTENSION
    starts = ["latex_string", "set_expr", "member", "any_value"]
    p_re = lp.build(True)
    p_rx = lark.Lark(text, source_path=str(lp.GRAMMAR_DIR) + "/", parser="earley", start=starts, lexer="auto",
                     ambiguity="explicit", propagate_positions=True, maybe_placeholders=False, keep_all_tokens=True,
                     regex=True)
    same = diff = 0
    for kind, s in lp.batch_values():
        st = ["set_expr", "member", "any_value"] if kind == "set" else starts
        a, b = lp.run(p_re, s, st), lp.run(p_rx, s, st)
        same += a["status"] == b["status"]
        diff += a["status"] != b["status"]
    return {"values_same_status": same, "values_different": diff}


def main() -> int:
    summary = {"regex": regex.__version__, "A_quotes": part_a(), "B_math": part_b(), "C_lark_regex": part_c()}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "A_quotes"}, ensure_ascii=False)[:1500])
    a = summary["A_quotes"]
    print("quotes", a["n_quotes"], "ms median", a["ms_median"], "ms max", a["ms_max"])
    for k, v in a["by_kind_method"].items():
        print(f"  {k:28s} n {v.get('n',0):3d} found {v.get('found',0):3d} exact {v.get('exact',0):3d} iou>=.9 {v.get('iou>=0.9',0):3d} cut {v.get('cut',0):3d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
