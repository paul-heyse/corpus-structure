"""I-B: canonical forms (D1 §6.2) and tiered value equivalence (instruments §4)."""

from __future__ import annotations

import unittest

import fixtures  # noqa: F401

from instruments import values as V
from instruments.values import ValueComparator, canonical_latex, canonical_value


def F(latex):
    return {"t": "formula", "latex": latex, "symbols": {}}


def S(latex):
    return {"t": "set", "latex": latex, "symbols": {}}


B_NONZERO = {"op": "and", "args": [{"op": "member", "x": "a", "set": "\\R"}, {"op": "member", "x": "b", "set": "\\R \\setminus \\{0\\}"}]}


class TestCanonical(unittest.TestCase):
    def test_d1_rules(self):
        self.assertEqual(canonical_latex("b^{2}"), "b^2")
        self.assertEqual(canonical_latex("b^{2} \\sigma^2"), canonical_latex("b^2\\sigma^{2}"))
        self.assertEqual(canonical_latex("\\left( x \\right)"), "(x)")
        self.assertEqual(canonical_latex("a + b \\, Z"), "a+bZ")
        self.assertEqual(canonical_latex("a\\;+\\!b"), "a+b")
        self.assertEqual(canonical_latex("e^{\\mu}"), "e^\\mu")
        self.assertEqual(canonical_latex("\\(x\\)"), "x")
        self.assertEqual(canonical_latex("\\[ x \\]"), "x")
        # D1 §6.2: $ is not one of the delimiters removed (I-R2)
        self.assertEqual(canonical_latex("$x$"), "$x$")
        # a control word keeps the separator TeX needs, so \mu x and \mux stay distinct
        self.assertEqual(canonical_latex("\\mu  x"), "\\mu x")
        self.assertNotEqual(canonical_latex("\\mu x"), canonical_latex("\\mux"))
        # \{ \} are control symbols, not group braces
        self.assertEqual(canonical_latex("\\R \\setminus \\{0\\}"), "\\mathbb R\\setminus\\{0\\}")

    def test_token_form_rules_i_r2(self):
        """D1 §6.2 token-form rules settled by I-R2 (written from the design, not read back)."""
        # sizing commands are on the drop list
        self.assertEqual(canonical_latex("a \\big/ b"), "a/b")
        self.assertEqual(canonical_latex("\\Bigl( x \\Bigr)"), "(x)")
        self.assertEqual(canonical_latex("\\biggm| x"), "|x")
        # a sizing name is matched whole: \bigcup is not \big + cup
        self.assertEqual(canonical_latex("A \\bigcup B"), "A\\bigcup B")
        # a * is never part of a control word: \cmd* is \cmd then *
        self.assertEqual(V.MG.printer.tex_tokens("\\operatorname*{max}"), ["\\operatorname", "*", "{", "m", "a", "x", "}"])
        # text-mode arguments keep one space per whitespace run
        self.assertEqual(canonical_latex("x \\text{ for all } y"), "x\\text{ for all }y")
        self.assertEqual(canonical_latex("\\text{for   all}"), "\\text{for all}")
        self.assertEqual(canonical_latex("1 \\text{ cm}"), "1\\text{ cm}")
        self.assertNotEqual(canonical_latex("\\text{for all}"), canonical_latex("\\text{forall}"))
        self.assertEqual(canonical_latex("\\mathrm{a  b}"), "\\mathrm{a b}")
        self.assertEqual(canonical_latex("\\mbox{ }x"), "\\mbox{ }x")
        # one outer pair: an inline and a displayed formula key alike; inner delimiters stay
        self.assertEqual(canonical_latex("\\begin{align} a &= b \\end{align}"), "a&=b")
        self.assertEqual(canonical_latex("\\begin{align*} a \\end{align*}"), canonical_latex("\\(a\\)"))
        self.assertEqual(canonical_latex("\\begin{cases} a \\end{cases}"), "\\begin{cases}a\\end{cases}")
        # a \) inside: not one outer pair, so nothing is stripped (\( is on the drop list, \) is not)
        self.assertEqual(canonical_latex("\\(\\(x\\)\\)"), "x\\)\\)")
        self.assertEqual(canonical_latex("\\(a\\) + \\(b\\)"), "a\\)+b\\)")  # \( on the drop list, \) not
        # macro expansion is bounded at depth 16; the unexpanded token is kept and reported
        loop = {"\\loop": {"nargs": 0, "body": "x\\loop"}}
        V.UNEXPANDED.clear()
        self.assertEqual(canonical_latex("\\loop", loop), "x" * 16 + "\\loop")
        self.assertEqual(V.UNEXPANDED, [("\\loop", ["\\loop"])])
        chain = {f"\\m{chr(97 + i)}": {"nargs": 0, "body": f"\\m{chr(98 + i)}"} for i in range(15)}
        self.assertEqual(canonical_latex("\\ma", chain), "\\mp")  # 15 nested expansions: within the bound

    def test_token_form_metamorphic(self):
        """D1 §6.2 metamorphic layer: invariances of the token form alone (no grammar)."""
        base = "a + b X_1^2 - \\frac{c}{d} \\sigma(x) \\in \\R"
        want = canonical_latex(base)
        for variant in ("a \\, + b X_1^2 - \\frac{c}{d} \\sigma(x) \\in \\R",
                        "a + \\; b X_1^{2} - \\frac{c}{d} \\sigma(x) \\in \\R",
                        "a + b\\! X_{1}^2 - \\frac c d \\sigma(x) \\in \\R",
                        "a + b X_1^2 - \\frac{c}{d} \\sigma\\big(x\\big) \\in \\R",
                        "a+bX_1^2-\\frac{c}{d}\\sigma(x)\\in\\R",
                        "  a   +   b X_1 ^ 2 - \\frac { c } { d } \\sigma ( x ) \\in \\R  ",
                        "{a} + b {X}_1^2 - \\frac{c}{d} \\sigma(x) \\in \\R"):
            with self.subTest(variant):
                self.assertEqual(canonical_latex(variant), want)
        self.assertNotEqual(canonical_latex("\\P"), canonical_latex("\\Phi"))
        self.assertNotEqual(canonical_latex("\\Phi"), "\\mathbb Phi")  # \P never expands inside \Phi
        self.assertNotEqual(canonical_latex("\\mu x"), canonical_latex("\\mux"))

    def test_macros_page_over_fallback(self):
        self.assertEqual(canonical_latex("\\R"), "\\mathbb R")  # D2 §12.1 fallback
        self.assertEqual(canonical_latex("\\R", {"\\R": {"nargs": 0, "body": "\\mathbf{R}"}}), "\\mathbf R")
        self.assertEqual(canonical_latex("\\abs{x}", {"\\abs": {"nargs": 1, "body": "\\lvert #1 \\rvert"}}), "\\lvert x\\rvert")
        self.assertEqual(canonical_latex("\\var(X)"), "\\text{var}(X)")

    def test_numbers_and_text(self):
        self.assertEqual(canonical_value({"t": "number", "v": "1", "unit": "cm"}), canonical_value({"t": "number", "v": "0.01", "unit": "m"}))
        self.assertEqual(canonical_value({"t": "number", "v": "2.50"})["v"], "2.5")
        self.assertEqual(canonical_value({"t": "text", "v": "  Normal\n Distribution "})["v"], "normal distribution")


class TestTiers(unittest.TestCase):
    def setUp(self):
        self.c = ValueComparator()

    def tier(self, a, b, conds=()):
        e = self.c.compare(a, b, conds)
        return e.equal, e.tier

    def test_canonical(self):
        self.assertEqual(self.tier(F("b^{2} \\sigma^2"), F("b^2\\sigma^2")), (True, "canonical"))

    def test_sympy(self):
        self.assertEqual(self.tier(F("b^2 \\sigma^2"), F("\\sigma^2 b^{2}")), (True, "sympy"))
        self.assertEqual(self.tier(F("a + b \\mu"), F("\\mu b + a")), (True, "sympy"))
        self.assertEqual(self.tier(F("X = e^Y"), F("e^{Y} = X")), (True, "sympy"))
        self.assertEqual(self.tier(F("a + b \\mu"), F("a + b")), (False, "numeric"))  # simplify leaves b*mu - b
        self.assertEqual(self.tier(F("2 + 2"), F("5")), (False, "sympy"))

    def test_sets(self):
        self.assertEqual(self.tier(S("\\R \\setminus \\{0\\}"), S("(-\\infty, 0) \\cup (0, \\infty)")), (True, "sympy"))
        self.assertEqual(self.tier(S("(0, \\infty)"), S("[0, \\infty)")), (False, "sympy"))

    def test_numeric_under_conditions(self):
        self.assertEqual(self.tier(F("\\lvert b \\rvert \\sigma"), F("b \\sigma"), [B_NONZERO]), (False, "numeric"))
        self.assertEqual(self.tier(F("\\lvert b \\rvert \\sigma"), F("\\sqrt{b^2} \\sigma"), [B_NONZERO]), (True, "numeric"))
        # with b restricted to (0, inf), |b| sigma and b sigma agree at every sampled point
        pos = {"op": "member", "x": "b", "set": "(0, \\infty)"}
        self.assertEqual(self.tier(F("\\lvert b \\rvert \\sigma"), F("b \\sigma"), [pos]), (True, "numeric"))

    def test_numbers_numeric(self):
        e = self.c.compare({"t": "number", "v": "0.1"}, {"t": "number", "v": "0.1000000000001"})
        self.assertEqual((e.equal, e.tier), (True, "numeric"))

    def test_manual_pending_and_decided(self):
        e = self.c.compare(F("\\var(X)"), F("\\sigma^2"))
        self.assertEqual((e.equal, e.tier), (None, "pending"))
        self.assertEqual(len(self.c.pending), 1)
        self.assertIn("\\text{var}(X)", self.c.pending_tsv())
        c2 = ValueComparator(manual={(e.a, e.b): (True, "var(X) is sigma^2 under the premise")})
        e2 = c2.compare(F("\\var(X)"), F("\\sigma^2"))
        self.assertEqual((e2.equal, e2.tier), (True, "manual"))

    # ---- review findings (2026-10-28)
    def test_f2_subscripts_kept_in_shim(self):
        for a, b in (("\\sigma_{X_1}^2", "\\sigma_{X_2}^2"), ("\\sigma_{\\mu}", "\\sigma"), ("\\sigma_{\\mu}", "\\sigma_{\\nu}"),
                     ("\\sigma_{X_1} + \\sigma_{X_2}", "2 \\sigma"), ("\\sigma_{1,2}", "\\sigma_{2,1}"), ("\\Sigma_1", "\\Sigma_2")):
            with self.subTest(a=a, b=b):
                self.assertIsNot(self.c.compare(F(a), F(b)).equal, True)
        self.assertEqual(self.tier(F("\\sigma_{X_1} \\sigma_{X_2}"), F("\\sigma_{X_2}\\sigma_{X_1}")), (True, "sympy"))

    def test_f3_application_is_not_multiplication(self):
        # F3 through the grammar: an undeclared symbol before (...) is ambiguous (application or
        # product) and goes to manual, never multiplied silently
        for a, b in (("\\Phi(-x)", "-\\Phi(x)"), ("\\Phi(z)", "z \\Phi"), ("f(x) y", "f x y"), ("\\phi(2x)", "2\\phi(x)")):
            with self.subTest(a=a, b=b):
                e = self.c.compare(F(a), F(b))
                self.assertIsNot(e.equal, True, e)
                self.assertEqual(e.tier, "pending", e)
        # \Gamma is a declared known function (the gamma function): Gamma(2a) != 2 Gamma(a), and
        # Gamma(a + 1) = a Gamma(a) is a true identity (under the shim this pair was kept unequal
        # only because \Gamma( was not read at all)
        self.assertIsNot(self.c.compare(F("\\Gamma(2 a)"), F("2 \\Gamma(a)")).equal, True)
        self.assertEqual(self.tier(F("\\Gamma(a+1)"), F("a \\Gamma(a)")), (True, "sympy"))
        # declared variables (the binding map) make a(b + c) a product
        bound = {"t": "formula", "latex": "a(b + c)", "symbols": {k: {"bind": "free"} for k in "abc"}}
        self.assertEqual(self.tier(bound, F("a b + a c")), (True, "sympy"))
        self.assertEqual(self.c.compare(F("a(b + c)"), F("a b + a c")).tier, "pending")

    def test_f5a_relations(self):
        self.assertEqual(self.tier(F("x < 1"), F("x < 2")), (False, "sympy"))
        self.assertEqual(self.tier(F("X \\le x"), F("X \\leq x")), (True, "sympy"))
        self.assertEqual(self.tier(F("x > 1"), F("1 < x")), (True, "sympy"))
        self.assertEqual(self.tier(F("x < 1"), F("x - 1")), (False, "sympy"))
        self.assertEqual(self.c.compare(F("x < 1"), F("x \\le 1")).tier, "pending")
        self.assertEqual(self.c.compare(F("x < 1"), F("x < 2")).kind, "relation")

    def test_memberships_and_chains(self):
        self.assertEqual(self.tier(F("x \\in \\R"), F("x\\in\\mathbb{R}")), (True, "canonical"))
        self.assertEqual(self.tier(F("x \\in (0, \\infty)"), F("x \\in \\R_+")), (True, "sympy"))
        self.assertEqual(self.c.compare(F("x \\in \\R"), F("x < 1")).equal, False)
        self.assertEqual(self.c.compare(F("x \\in \\N"), F("x \\in \\Z")).tier, "pending")

    def test_f5b_distinct_points_and_range(self):
        nat = [{"op": "member", "x": "n", "set": "\\N"}, {"op": "cmp", "rel": ">", "lhs": "n", "rhs": "8"}]
        self.assertEqual(self.tier(F("n^2"), F("19 n - 90"), nat), (False, "numeric"))
        self.assertEqual(self.tier(F("\\min(x, 10)"), F("x")), (False, "numeric"))
        # only two admissible integers: too few distinct points to decide
        two = [{"op": "member", "x": "n", "set": "\\N"}, {"op": "cmp", "rel": ">", "lhs": "n", "rhs": "8"},
               {"op": "cmp", "rel": "<", "lhs": "n", "rhs": "11"}]
        self.assertEqual(self.c.compare(F("n^2"), F("19 n - 90"), two).tier, "pending")

    def test_f5f_pint_units(self):
        self.assertIsNotNone(V._UREG)
        self.assertEqual(canonical_value({"t": "number", "v": "1", "unit": "cm"}), {"t": "number", "v": "0.01", "unit": "meter"})
        self.assertEqual(canonical_value({"t": "number", "v": "7", "unit": "widgets"})["unit"], "widgets")  # unknown: kept

    def test_parse_log_records_raw_failures(self):
        # SymPy's shipped grammar rejected \tau^2 \kappa^2 (implicit product after a power); the
        # math grammar reads it, so nothing is logged
        self.assertEqual(V.parse_formula("\\tau^2 \\kappa^2").status, "ok")
        self.assertFalse([r for r in V.PARSE_LOG if r["latex"] == "\\tau^2 \\kappa^2"])
        for latex, status in (("\\begin{cases} x & y \\end{cases}", "failed"), ("\\Phi(x)", "ambiguous"), ("\\mu \\pm \\sigma", "ok")):
            r = V.parse_formula(latex)
            self.assertIsNone(r.expr)
            rec = [x for x in V.PARSE_LOG if x["latex"] == latex]
            self.assertEqual((rec[0]["status"], bool(rec[0]["error"])), (status, True), rec)


if __name__ == "__main__":
    unittest.main()
