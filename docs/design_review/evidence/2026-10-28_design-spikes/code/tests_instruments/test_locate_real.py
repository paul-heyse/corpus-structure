"""I-A: locator cases on S1's real canonical text (cases in ``real_text_cases.py``)."""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

import fixtures  # noqa: F401  (puts code/ on sys.path)
from real_text_cases import REAL_CASES

from s0_locate import UnitContext, locate_quote

S1 = Path(__file__).resolve().parents[2] / "results" / "s1"
VARIANT = os.environ.get("S0_SENTENCE_VARIANT", "provisional")


def load_page(page: str):
    text = (S1 / "canonical" / f"{page}.txt").read_text(encoding="utf-8")
    segs = [json.loads(x) for x in (S1 / "segments" / f"{page}.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    sents = [json.loads(x) for x in (S1 / "sentences" / f"{page}.{VARIANT}.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    return text, segs, sents


def unit_context(page: str, prefixes: list[str]) -> UnitContext:
    text, segs, sents = load_page(page)
    ranges, keys = [], []
    for p in prefixes:
        cands = [s for s in segs if s["kind"] in ("unit", "paragraph") and text[s["start"]:s["end"]].startswith(p)]
        if not cands:
            raise LookupError(f"{page}: no unit/paragraph starting {p!r}")
        s = max(cands, key=lambda s: s["end"] - s["start"])  # the unit when a unit and its first paragraph share the start
        ranges.append((s["start"], s["end"]))
        keys.append(s["key"])
    inside = sorted((x for x in sents if any(a <= x["start"] and x["end"] <= b for a, b in ranges)), key=lambda x: x["start"])
    sentences = {f"s{i}": (x["start"], x["end"]) for i, x in enumerate(inside, 1)}
    return UnitContext(text, ranges, sentences, unit_keys=keys, sentence_keys={f"s{i}": x["key"] for i, x in enumerate(inside, 1)})


def available() -> bool:
    return all((S1 / d).exists() for d in ("canonical", "segments", "sentences")) and any((S1 / "sentences").glob(f"*.{VARIANT}.jsonl"))


RESULTS: list[str] = []


@unittest.skipUnless(available(), "S1 canonical text / sentences not present")
class TestRealText(unittest.TestCase):
    def test_cases(self):
        for case in REAL_CASES:
            page, prefixes, quote, expect, tier = case[:5]
            with self.subTest(f"{page}: {quote[:40]}"):
                ctx = unit_context(page, prefixes)
                if expect == "COARSE":
                    pre = case[5]
                    sid = next(k for k, (a, b) in ctx.sentences.items() if ctx.text[a:b].startswith(pre))
                else:
                    pos = [o for a, b in ctx.unit_ranges for o in [ctx.text.find(expect, a, b)] if o >= 0]
                    self.assertTrue(pos, f"expected substring not in the unit: {expect!r}")
                    sid = next(k for k, (a, b) in ctx.sentences.items() if a <= pos[0] < b)
                res = locate_quote(quote, sid, ctx)
                got = ctx.text[res.start:res.end] if res.start is not None else None
                RESULTS.append(f"{page}\t{quote}\t{tier}\t{res.tier}\t{res.matches}\t{res.score}\t{got!r}")
                self.assertEqual(res.tier, tier, res)
                if expect == "COARSE":
                    self.assertTrue(res.coarse)
                    self.assertEqual((res.start, res.end), ctx.sentences[sid])
                else:
                    self.assertEqual(got, expect)
                    self.assertEqual(res.start, pos[0])


if __name__ == "__main__":
    unittest.main()
