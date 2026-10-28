"""I-R1: the quote cascade against the regex probe's perturbation kinds (code/regex_probe.py).

1. Synthetic: one hand-expected case per perturbation kind (re-spacing, typo, dropped word, trimmed
   end, added period, macro respelling) on the trace-T3 sentence.
2. Probe reproduction: every evidence quote of passes A, B, P, H and the model reference, located
   exactly (ground truth), perturbed with the probe's own seeded ``perturb`` and located with
   ``s0_locate.locate_quote``. The probe's cascade figures (results/regex_probe/summary.json,
   "cascade") are reproduced: no mid-word cuts; macro 16/16, respace 60/60 exact; drop_word at
   least 43/99 exact; worst case well under a second. Skipped when the S0 passes are absent.
"""

from __future__ import annotations

import random
import unittest
from collections import Counter, defaultdict

from fixtures import TEXT, ctx_t3

from s0_locate import locate_quote

S2 = ctx_t3().sentences["s2"]
CASES = [  # (kind, quote, expected substring of TEXT, step)
    ("respace", "If $a\\in\\R$ and $b \\in \\R\\setminus\\{0\\}$", "If \\(a \\in \\R\\) and \\(b \\in \\R \\setminus \\{0\\}\\)", "spacing"),
    ("macro", "If \\(a \\in \\mathbb{R}\\) and", "If \\(a \\in \\R\\) and", "macros"),
    ("typo", "then \\(a + b X\\) is normaly distributed with mean", "then \\(a + b X\\) is normally distributed with mean", "fuzzy"),
    # a dropped short word ("with")
    ("drop_word", "is normally distributed mean \\(a + b \\mu\\)", "is normally distributed with mean \\(a + b \\mu\\)", "fuzzy"),
    # a long dropped word (8 of 55 characters) falls below cutoff 85: coarse
    ("drop_long_word", "then \\(a + b X\\) is distributed with mean \\(a + b \\mu\\)", None, None),
    ("trim_end", "is normally distributed with mea", "is normally distributed with mean", "exact_sentence"),
    ("add_period", "variance \\(b^2 \\sigma^2\\).", "variance \\(b^2 \\sigma^2\\).", "exact_sentence"),
    ("add_period_absent", "is normally distributed with mean.", "is normally distributed with mean", "fuzzy"),
]


class TestKinds(unittest.TestCase):
    def test_refine_timeout_falls_back_to_window(self):
        # 95 characters: the BESTMATCH refine exceeds its 0.2 s budget; the RapidFuzz window is
        # used (step fuzzy_window), snapped to words: it overlaps the true phrase and cuts no word
        q = "then \\(a + b X\\) is normally distributed mean \\(a + b \\mu\\) and variance \\(b^2 \\sigma^2\\)"
        truth = "then \\(a + b X\\) is normally distributed with mean \\(a + b \\mu\\) and variance \\(b^2 \\sigma^2\\)"
        r = locate_quote(q, "s2", ctx_t3())
        i = TEXT.index(truth)
        if r.step == "fuzzy":  # a faster machine finishes the refine: then it is exact
            self.assertEqual((r.start, r.end), (i, i + len(truth)))
            return
        self.assertEqual(r.step, "fuzzy_window", r)
        self.assertTrue(r.start < i + len(truth) and i < r.end)
        self.assertFalse(TEXT[r.start - 1].isalnum() and TEXT[r.start].isalnum())
        self.assertFalse(TEXT[r.end - 1].isalnum() and TEXT[r.end].isalnum())

    def test_kinds(self):
        ctx = ctx_t3()
        for kind, quote, expect, step in CASES:
            with self.subTest(kind):
                r = locate_quote(quote, "s2", ctx)
                if expect is None:
                    self.assertTrue(r.coarse, r)
                    continue
                i = TEXT.index(expect, S2[0])
                self.assertEqual((r.start, r.end, r.step), (i, i + len(expect), step), (r, TEXT[r.start:r.end]))


def _probe():
    try:
        import regex_probe as rp
        from s0_check import context
    except Exception as ex:  # noqa: BLE001
        return None, str(ex)
    return (rp, context), None


PROBE, WHY = _probe()
RESULTS: dict = {}


@unittest.skipIf(PROBE is None, f"regex probe inputs unavailable: {WHY}")
class TestProbeFigures(unittest.TestCase):
    def test_reproduce(self):
        rp, context = PROBE
        rng = random.Random(20261028)
        agg = defaultdict(Counter)
        worst = 0.0
        ctxs = {}
        for unit, sid, q in rp.quotes():
            ctx = ctxs.setdefault(unit, context(unit))
            gt = locate_quote(q, sid, ctx)
            if gt.tier not in (1, 2) or sid not in ctx.sentences:
                continue
            for kind in ["respace", "typo", "drop_word", "trim_end", "add_period", "macro"]:
                pq = rp.perturb(q, kind, rng)
                if pq is None or pq == q:
                    continue
                r = locate_quote(pq, sid, ctx)
                worst = max(worst, r.ms)
                a = agg[kind]
                a["n"] += 1
                if r.tier is None:
                    continue
                a["found"] += 1
                a["exact"] += (r.start, r.end) == (gt.start, gt.end)
                a["cut"] += rp.cuts_word(ctx.text, r.start, r.end) and not rp.cuts_word(ctx.text, gt.start, gt.end)
                a[f"step:{r.step}"] += 1
        RESULTS.update({k: dict(v) for k, v in agg.items()}, worst_ms=round(worst, 1))
        self.assertEqual(sum(v["cut"] for v in agg.values()), 0, RESULTS)
        self.assertEqual((agg["macro"]["exact"], agg["macro"]["n"]), (16, 16), RESULTS)
        self.assertEqual((agg["respace"]["exact"], agg["respace"]["n"]), (60, 60), RESULTS)
        self.assertEqual(agg["drop_word"]["n"], 99)
        self.assertGreaterEqual(agg["drop_word"]["exact"], 43, RESULTS)
        self.assertLess(worst, 1000.0, RESULTS)


if __name__ == "__main__":
    unittest.main()
