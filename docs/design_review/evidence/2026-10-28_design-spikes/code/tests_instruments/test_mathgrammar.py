"""I-R1: the math grammar (code/mathgrammar, ADR-0009).

Expectations are written from the grammar's contract (api docstring), not read back from it.
"""

from __future__ import annotations

import re
import unittest

import fixtures  # noqa: F401  (code/ on sys.path)
import sympy

import mathgrammar as M
from mathgrammar.build import BASE_GRAMMAR, EXTENSION, classify, parser_for
from mathgrammar.printer import tokens_canonical
from instruments.values import merged_macros

PAGE = {"\\R": {"nargs": 0, "body": "\\mathbb{R}"}, "\\N": {"nargs": 0, "body": "\\mathbb{N}"},
        "\\P": {"nargs": 0, "body": "\\mathbb{P}"}, "\\E": {"nargs": 0, "body": "\\mathbb{E}"},
        "\\var": {"nargs": 0, "body": "\\text{var}"}, "\\sgn": {"nargs": 0, "body": "\\,\\text{sgn}"},
        "\\ms": {"nargs": 0, "body": "\\mathscr"}, "\\odd": {"nargs": 0, "body": "\\frac{1}{2}"}}


def P(latex, kind="any_value", **ctx):
    return M.parse(latex, kind, macros=PAGE, context=ctx or None)


class TestBuild(unittest.TestCase):
    def test_shipped_grammar_is_read_unedited(self):
        import sympy.parsing.latex.lark as slark

        self.assertEqual(BASE_GRAMMAR.parent.parent, __import__("pathlib").Path(slark.__file__).parent)
        self.assertIn("latex_string: _relation | _expression", BASE_GRAMMAR.read_text())

    def test_no_source_specific_names_in_the_grammar(self):
        ext = EXTENSION.read_text()
        for name in ("\\\\E", "\\\\var", "\\\\sd", "\\\\skw", "\\\\kur", "\\\\cov", "\\\\cor", "\\\\bs", "\\\\ms", "\\\\R\"", "\\\\N\""):
            self.assertNotIn(name, ext, name)

    def test_classification_from_bodies(self):
        mc = classify(PAGE)
        self.assertEqual(dict(mc.sets), {"\\N": "N", "\\R": "R"})
        self.assertEqual(dict(mc.ops), {"\\E": "E", "\\P": "P", "\\sgn": "sgn", "\\var": "var"})
        self.assertEqual(dict(mc.styles), {"\\ms": "\\mathscr"})
        self.assertEqual(dict(mc.other), {"\\odd": "\\frac{1}{2}"})

    def test_parser_cached_per_classification(self):
        self.assertIs(parser_for(classify(PAGE)), parser_for(classify(dict(PAGE))))

    def test_whole_command_names(self):
        self.assertEqual(P("\\Phi").status, "ok")  # \P is a prefix of \Phi; never matched inside it
        self.assertEqual(P("\\P(A)").kind, "formula")
        self.assertEqual(P("\\sinh x").status, "ok")
        r = P("\\phantom x")
        self.assertEqual((r.status, r.reason["category"]), ("failed", "unknown-command"))


class TestReading(unittest.TestCase):
    def test_kinds(self):
        for latex, kind in (("a + b \\mu", "formula"), ("X = e^Y", "formula"), ("x < 1", "relation"),
                            ("0 < p \\le 1", "relation"), ("x \\in \\R", "member"), ("a, b \\in \\R", "member"),
                            ("\\R \\setminus \\{0\\}", "set_expr"), ("\\{x \\in \\R: x > 0\\}", "set_expr"),
                            ("f(x) = 2 x, \\quad x \\in [0, 1]", "list"), ("X \\sim N(\\mu, \\sigma^2)", "relation")):
            with self.subTest(latex):
                r = P(latex)
                self.assertIn(r.status, ("ok",), (r.status, r.notes, r.reason))
                self.assertEqual(r.kind, kind)

    def test_structure_of_scripts(self):
        x = M.to_sympy(P("\\sigma_{X_1}^2 + X_{(n)} + \\mu_i^2 + \\sigma^2_X", "formula"))
        names = {s.name for s in x.free_symbols}
        self.assertEqual(names, {"sigma_{X_1}", "X_{(n)}", "mu_{i}", "sigma_{X}"})

    def test_sympy_values(self):
        cases = {
            "b^2 \\sigma^2": sympy.Symbol("b") ** 2 * sympy.Symbol("sigma") ** 2,
            "\\lvert b \\rvert \\sigma": sympy.Abs(sympy.Symbol("b")) * sympy.Symbol("sigma"),
            "e^{\\pi}": sympy.exp(sympy.pi),
            "\\E(X)": sympy.Function("E")(sympy.Symbol("X")),
            "\\var(X)": sympy.Function("var")(sympy.Symbol("X")),
        }
        for latex, want in cases.items():
            with self.subTest(latex):
                self.assertEqual(M.to_sympy(P(latex, "formula")), want)
        self.assertEqual(M.to_sympy(P("\\R \\setminus \\{0\\}", "set_expr")),
                         sympy.Complement(sympy.S.Reals, sympy.FiniteSet(0)))
        self.assertEqual(M.to_sympy(P("(0, \\infty)", "set_expr")), sympy.Interval.open(0, sympy.oo))
        self.assertEqual(M.to_sympy(P("\\N_+", "set_expr")), sympy.S.Naturals)
        self.assertEqual(M.to_sympy(P("x \\in \\R", "member")), sympy.Contains(sympy.Symbol("x"), sympy.S.Reals))
        self.assertEqual(M.to_sympy(P("x < 1", "relation")), sympy.Lt(sympy.Symbol("x"), 1))

    def test_not_representable(self):
        for latex, kind in (("\\mu \\pm \\sigma", "formula"), ("x_1 + \\cdots + x_n", "formula"), ("A \\cup B", "set_expr")):
            with self.subTest(latex):
                r = P(latex, kind)
                self.assertEqual(r.status, "ok")
                with self.assertRaises(M.NotRepresentable):
                    M.to_sympy(r)


class TestAmbiguity(unittest.TestCase):
    def test_application_or_product(self):
        self.assertEqual(P("\\Phi(-x)", "formula").status, "ambiguous")
        self.assertEqual(P("a(b + c)", "formula").status, "ambiguous")
        self.assertEqual(P("a(b + c)", "formula", variables={"a", "b", "c"}).status, "ok")
        self.assertEqual(M.to_sympy(P("a(b + c)", "formula", variables={"a", "b", "c"})), sympy.Symbol("a") * (sympy.Symbol("b") + sympy.Symbol("c")))
        self.assertEqual(P("\\Phi(-x)", "formula", functions={"Phi"}).status, "ok")
        self.assertEqual(P("f(x) y", "formula").status, "ambiguous")  # SymPy's grammar picked the product silently
        self.assertEqual(P("F^{-1}(p)", "formula").status, "ambiguous")

    def test_known_function_and_definitions(self):
        self.assertEqual(M.to_sympy(P("\\Gamma(k)", "formula")), sympy.gamma(sympy.Symbol("k")))
        r = P("g(x) = x^2 + g(1)")
        self.assertEqual(r.status, "ok", r.notes)
        self.assertIn("g declared a function by its definition", r.notes)

    def test_interval_only_where_a_set_is_expected(self):
        self.assertEqual(P("(0, 1)").status, "ambiguous")
        self.assertEqual(P("(0, 1)", "set_expr").status, "ok")
        self.assertEqual(P("x \\in (0, 1)").status, "ok")
        self.assertEqual(P("(0, 1)", "formula").status, "failed")

    def test_equivalent_readings_collapse(self):
        r = P("a b / c", "formula")
        self.assertEqual(r.status, "ok")
        self.assertEqual(M.to_sympy(r), sympy.Symbol("a") * sympy.Symbol("b") / sympy.Symbol("c"))

    def test_lone_symbol_is_a_formula(self):
        r = P("X")
        self.assertEqual((r.status, r.kind), ("ok", "formula"))
        self.assertEqual(P("X", "set_expr").status, "ok")


class TestCanonicalAndOccurrences(unittest.TestCase):
    def test_canonical_is_the_token_form(self):
        """ADR-0012: keys are the token form for every value, parsed or not."""
        mm = merged_macros(PAGE)
        for latex in ("b^{2} \\, \\sigma^2", "x \\text{ if } y", "\\begin{cases} x \\end{cases}"):
            with self.subTest(latex):
                r = M.parse(latex, "any_value", macros=mm)
                self.assertEqual(M.canonical(r), tokens_canonical(latex, r.mc.table()))
        self.assertEqual(M.canonical(M.parse("\\R", "set_expr", macros=mm)), "\\mathbb R")

    def test_tree_printer_agrees_with_token_form(self):
        """The tree/token property (D1 §6.2) on parsed values, including sizing commands."""
        mm = merged_macros(PAGE)
        for latex in ("b^{2} \\, \\sigma^2", "\\left( x \\right)", "\\R \\setminus \\{0\\}", "\\E(X) = \\mu",
                      "a + b \\, Z", "\\sigma_{X_1}^{2}", "e^{\\mu}", "a \\big/ b", "\\Bigl( x \\Bigr)"):
            with self.subTest(latex):
                r = M.parse(latex, "any_value", macros=mm)
                self.assertNotEqual(r.status, "failed")
                got = M.tree_token_agreement(r)
                self.assertTrue(got["agree"], got)
        self.assertIsNone(M.tree_token_agreement(M.parse("\\begin{cases} x \\end{cases}", macros=mm))["agree"])

    def test_grammar_ignores_come_from_the_drop_list(self):
        """build refuses an assembled grammar with an %ignore the drop list does not cover."""
        from mathgrammar.build import check_ignores, grammar_text

        text = grammar_text(classify(PAGE))
        check_ignores(text)
        self.assertIn("bigg", [l for l in text.splitlines() if l.startswith("%ignore /")][-1])
        with self.assertRaises(ValueError):
            check_ignores(text + '\n%ignore "\\\\hspace"\n')

    def test_occurrences(self):
        latex = "\\sigma_{X_1}^2 + \\mu_i + e^{\\pi x} + \\mathscr{F}"
        occ = P(latex, "formula").occurrences
        got = [(o.name, o.base, o.sub, o.sup, latex[o.start:o.end], o.constant, o.in_subscript_of) for o in occ]
        self.assertEqual(got, [
            ("\\sigma_{X_1}", "\\sigma", "X_1", "2", "\\sigma_{X_1}", False, None),
            ("X_1", "X", "1", None, "X_1", False, "\\sigma_{X_1}"),
            ("\\mu_i", "\\mu", "i", None, "\\mu_i", False, None),
            ("i", "i", None, None, "i", False, "\\mu_i"),
            ("e", "e", None, "\\pi x", "e", True, None),
            ("\\pi", "\\pi", None, None, "\\pi", True, None),
            ("x", "x", None, None, "x", False, None),
            ("\\mathscr F", "\\mathscr F", None, None, "\\mathscr{F}", False, None),
        ])

    def test_occurrences_in_span_of_canonical_text(self):
        from fixtures import T3_S2, TEXT

        i = TEXT.index("\\(a + b \\mu\\)")
        span_end = i + len("\\(a + b \\mu\\)")
        r, occ = M.occurrences_in_span(TEXT, i, span_end, macros=merged_macros({}))
        self.assertEqual(r.status, "ok")
        self.assertEqual([(o.name, TEXT[o.start:o.end]) for o in occ], [("a", "a"), ("b", "b"), ("\\mu", "\\mu")])
        self.assertTrue(all(i < o.start < span_end for o in occ))
        self.assertIn(TEXT[occ[2].start:occ[2].end], T3_S2)

    def test_bare_unit(self):
        self.assertEqual(M.bare_unit(P("1 cm", "formula")), "cm")
        self.assertIsNone(M.bare_unit(P("2 x + 1", "formula")))


if __name__ == "__main__":
    unittest.main()
