"""I-A: planted quote-location cases with hand-written expected spans (instruments §3, revisit I-R1).

Expected spans are written as the exact expected substring plus which occurrence (or the
cited sentence for coarse fallbacks); expected steps follow from the cascade in s0_locate's
docstring (exact sentence, exact unit, spacing, macros, fuzzy). Every located span is snapped to
word boundaries, so no expectation ends inside a word. Fuzzy cases were re-derived for I-R1
(cutoff 85, regex refine): the repaired a.ref gap under (b) and the short straight-quoted phrase,
coarse before, are now located; (c) (an 11-character gap) stays coarse. The "different marker"
span starts at "a)": the refine aligns "1." to "a)" by two substitutions, and "(" is not part of
a word, so the snap does not add it.
"""

from __future__ import annotations

import copy
import unittest

from fixtures import SEGMENTS, TEXT, ctx_t2, ctx_t3, t2_model, t3_model

from s0_locate import UnitContext, locate_quote, reanchor, to_stored

S1 = ("Suppose that \\(X\\) has the gamma distribution with shape parameter \\(k \\in (0, \\infty)\\) "
      "and scale parameter \\(b \\in (0, \\infty)\\).")
S3 = "The distribution is called the “standard gamma distribution” when \\(b = 1\\)."
S4 = "Hence the scale parameter is positive."
S5 = "The mean is \\(k b\\) and the scale parameter is \\(b\\)."
S6 = "(a) The parameter \\( \\sigma \\) is the shape parameter of the distribution."
S7 = "(b) The parameter \\( e^\\mu\\) is the scale parameter of the distribution."
AREF = {
    "a_nothing": "As a special case of , Stirling's approximation holds.",
    "b_placeholder": "As a special case of [ref], Stirling's approximation holds.",
    "c_target": "As a special case of Theorem 3, Stirling's approximation holds.",
}


def make_ctx(aref: str = "a_nothing") -> UnitContext:
    sents = [S1, AREF[aref], S3, S4, S5]
    para = " ".join(sents)
    text = "Gamma page\n\n" + para + "\n\n" + S6 + "\n" + S7 + "\n"
    spans, pos = {}, text.index(para)
    for i, s in enumerate(sents, 1):
        j = text.index(s, pos)
        spans[f"s{i}"] = (j, j + len(s))
        pos = j + len(s)
    for i, s in ((6, S6), (7, S7)):
        j = text.index(s)
        spans[f"s{i}"] = (j, j + len(s))
    return UnitContext(text, [(spans["s1"][0], spans["s7"][1])], spans)


def nth(text: str, sub: str, n: int = 0, start: int = 0) -> tuple[int, int]:
    i = start - 1
    for _ in range(n + 1):
        i = text.index(sub, i + 1)
    return (i, i + len(sub))


# (name, aref convention, quote, cited sentence, expected substring | "COARSE" | "DROPPED", occurrence, tier, extra checks)
CASES = [
    ("exact in cited sentence", "a_nothing", "has the gamma distribution", "s1", "has the gamma distribution", 0, 1, {}),
    ("exact in unit, wrong sentence cited", "a_nothing", "Stirling's approximation holds", "s1", "Stirling's approximation holds", 0, 2, {}),
    ("phrase twice in the cited sentence", "a_nothing", "parameter \\(", "s1", "parameter \\(", 0, 1, {"matches": 2}),
    ("phrase twice in the unit, nearest to the cited sentence", "a_nothing", "the scale parameter is", "s6", "the scale parameter is", 1, 2, {"matches": 2}),
    ("$...$ and re-spaced LaTeX", "a_nothing", "shape parameter $k\\in(0,\\infty)$", "s1", "shape parameter \\(k \\in (0, \\infty)\\)", 0, 3, {"step": "spacing"}),
    ("\\(\\) without inner spaces", "a_nothing", "\\(\\sigma\\) is the shape parameter", "s6", "\\( \\sigma \\) is the shape parameter", 0, 3, {"step": "spacing"}),
    ("macro spelled out in the quote", "a_nothing", "parameter \\(k \\in (0, \\infty)\\)", "s1", "parameter \\(k \\in (0, \\infty)\\)", 0, 1, {}),
    ("verbatim quote across an a.ref gap (a)", "a_nothing", "As a special case of , Stirling's", "s2", "As a special case of , Stirling's", 0, 1, {}),
    ("verbatim quote across an a.ref gap (b)", "b_placeholder", "As a special case of [ref], Stirling's", "s2", "As a special case of [ref], Stirling's", 0, 1, {}),
    ("verbatim quote across an a.ref gap (c)", "c_target", "As a special case of Theorem 3, Stirling's", "s2", "As a special case of Theorem 3, Stirling's", 0, 1, {}),
    # an annotator who "repairs" the gap: fuzzy step; the span covers the whole clause (no cut word)
    ("gap repaired by the annotator (a)", "a_nothing", "As a special case of Stirling's approximation holds", "s2", "As a special case of , Stirling's approximation holds", 0, 5, {"fuzzy_counts": (0, 2, 0)}),
    ("gap repaired by the annotator (b)", "b_placeholder", "As a special case of Stirling's approximation holds", "s2", "As a special case of [ref], Stirling's approximation holds", 0, 5, {"fuzzy_counts": (0, 7, 0)}),
    ("gap repaired by the annotator (c)", "c_target", "As a special case of Stirling's approximation holds", "s2", "COARSE", 0, None, {}),
    # <q> rendered as curly quotes; annotator types straight quotes (2 substitutions)
    ("straight for curly quotes, short quote", "a_nothing", "\"standard gamma distribution\"", "s3", "“standard gamma distribution”", 0, 5, {"fuzzy_counts": (2, 0, 0)}),
    ("straight for curly quotes, longer quote", "a_nothing", "is called the \"standard gamma distribution\" when", "s3", "is called the “standard gamma distribution” when", 0, 5, {"fuzzy_counts": (2, 0, 0)}),
    ("list item without its marker", "a_nothing", "The parameter \\( \\sigma \\) is the shape parameter", "s6", "The parameter \\( \\sigma \\) is the shape parameter", 0, 1, {}),
    ("list item with the marker", "a_nothing", "(a) The parameter \\( \\sigma \\) is the shape parameter", "s6", "(a) The parameter \\( \\sigma \\) is the shape parameter", 0, 1, {}),
    ("list item with a different marker", "a_nothing", "1. The parameter \\( \\sigma \\) is the shape parameter", "s6", "a) The parameter \\( \\sigma \\) is the shape parameter", 0, 5, {"fuzzy_counts": (2, 0, 0)}),
    ("long quote with one typo", "a_nothing",
     "Suppose that \\(X\\) has the gamma distrbution with shape parameter \\(k \\in (0, \\infty)\\) and scale parameter",
     "s1", "Suppose that \\(X\\) has the gamma distribution with shape parameter \\(k \\in (0, \\infty)\\) and scale parameter", 0, 5,
     {"long_quote": True, "fuzzy_counts": (0, 1, 0)}),
    ("unlocated quote", "a_nothing", "the moment generating function exists", "s4", "COARSE", 0, None, {}),
    ("unlocated quote with an unknown sentence", "a_nothing", "the moment generating function exists", "s9", "DROPPED", 0, None, {}),
]

RESULTS: list[str] = []


class TestPlanted(unittest.TestCase):
    def test_cases(self):
        for name, conv, quote, sid, expect, occ, tier, extra in CASES:
            with self.subTest(name):
                ctx = make_ctx(conv)
                res = locate_quote(quote, sid, ctx)
                RESULTS.append(f"{name}\t{tier}\t{res.tier}\t{res.matches}\t{res.score}\t{res.long_quote}\t{ctx.text[res.start:res.end] if res.start is not None else None!r}")
                self.assertEqual(res.tier, tier, res)
                if expect == "COARSE":
                    self.assertTrue(res.coarse)
                    self.assertEqual((res.start, res.end), ctx.sentences[sid])
                elif expect == "DROPPED":
                    self.assertTrue(res.dropped)
                else:
                    self.assertEqual((res.start, res.end), nth(ctx.text, expect, occ), ctx.text[res.start:res.end])
                for k, v in extra.items():
                    self.assertEqual(getattr(res, k), v)


class TestStoredConversion(unittest.TestCase):
    def test_t2_extent_section_and_scope_qualifier(self):
        st, rep = to_stored(t2_model(), ctx_t2())
        self.assertEqual(rep.problems, [])
        x = next(e for e in st["entities"] if e["local_ref"] == "X")
        self.assertEqual(x["scope_segment"], "seg:section")
        c1 = st["claims"][0]
        self.assertEqual(c1["qualifiers"]["scope"], {"extent": "section", "segment": "seg:section"})
        self.assertEqual(st["statements"][0]["anchor"], ["seg:t2para"])
        q = TEXT[c1["evidence"][1]["start"]:c1["evidence"][1]["end"]]
        self.assertEqual(q, "\\( \\mu \\in \\R \\)")
        self.assertNotIn("scope_segment", next(e for e in st["entities"] if e["local_ref"] == "N"))

    def test_t3_extent_statement(self):
        st, rep = to_stored(t3_model(), ctx_t3())
        self.assertEqual(rep.problems, [])
        segs = {e["local_ref"]: e.get("scope_segment") for e in st["entities"]}
        self.assertEqual(segs["X"], "seg:t3unit")  # S1 anchored to s1, s2; enclosing segment is the unit
        self.assertEqual(segs["Y"], "seg:t3unit")
        self.assertEqual(st["statements"][1]["anchor"], ["seg:t3s3"])
        for c in st["claims"]:
            for e in c["evidence"]:
                self.assertNotIn("coarse", e)

    def test_unresolvable_extent_reported(self):
        b = t3_model()
        b["entities"].append({"local_ref": "Z", "type": "RandomVariable", "label": "Z", "scope": "local", "extent": "statement", "symbol": "Z"})
        _, rep = to_stored(b, ctx_t3())
        self.assertTrue(any("'Z'" in p and "binding statement" in p for p in rep.problems), rep.problems)

    def test_unlocated_evidence_coarse_and_dropped(self):
        b = t3_model()
        b["claims"][1]["evidence"] = [{"sentence": "s2", "quote": "nothing like this", "role": "primary"},
                                      {"sentence": "s8", "quote": "nothing like this", "role": "supporting"}]
        st, rep = to_stored(b, ctx_t3())
        self.assertEqual(st["claims"][1]["evidence"], [{"start": SEGMENTS["seg:t3s2"][0], "end": SEGMENTS["seg:t3s2"][1], "role": "primary", "coarse": True}])
        self.assertTrue(any("dropped as malformed" in p for p in rep.problems))

    def test_phrase_leaf_located(self):
        b = t3_model()
        b["claims"][2]["qualifiers"]["conditions"]["args"].append({"op": "phrase", "text": "b \\in \\R \\setminus \\{0\\}", "sentence": "s2"})
        st, _ = to_stored(b, ctx_t3())
        leaf = st["claims"][2]["qualifiers"]["conditions"]["args"][-1]
        self.assertEqual(TEXT[leaf["start"]:leaf["end"]], "b \\in \\R \\setminus \\{0\\}")
        self.assertNotIn("sentence", leaf)


class TestReanchor(unittest.TestCase):
    def test_reanchor_moves_spans_and_lists_failures(self):
        ctx = ctx_t3()
        st, _ = to_stored(t3_model(), ctx)
        # new rendition: a sentence inserted before the unit, proof sentence reworded
        prefix = "An inserted sentence. "
        new_text = TEXT.replace("Suppose that \\(X\\)", prefix + "Suppose that \\(X\\)").replace("The MGF of", "The moment generating function of")
        shift = len(prefix)
        sent = {k: (a + shift, b + shift) for k, (a, b) in ctx.sentences.items()}
        sent["s3"] = (new_text.index("The moment"), new_text.index("The moment") + len("The moment generating function of \\(a + b X\\) is computed from the MGF of \\(X\\)."))
        new_ctx = UnitContext(new_text, [(ctx.unit_ranges[0][0], ctx.unit_ranges[0][1] + shift + 22)], sent)
        moved, failed = reanchor(st, TEXT, new_ctx)
        c1 = moved["claims"][0]["evidence"][0]
        self.assertEqual(new_text[c1["start"]:c1["end"]], TEXT[st["claims"][0]["evidence"][0]["start"]:st["claims"][0]["evidence"][0]["end"]])
        self.assertEqual(len(failed), 1, failed)
        self.assertIn("The MGF of", failed[0])


if __name__ == "__main__":
    unittest.main()
