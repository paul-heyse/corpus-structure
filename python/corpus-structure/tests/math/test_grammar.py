"""The math grammar (ingest and math §3.7, §6 P0-I-2a; D4 M11; ADR-0012).

The spike's grammar cases, ported, with expectations written from the contract (D4 M11 and the
grammar's docstring), not read back from the code. SymPy's deprecation warning is an error here,
so a SymPy bump that sends a construct down a deprecated path fails these tests.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from collections.abc import Mapping

import pytest
import sympy

from corpus_structure.core import tex
from corpus_structure.core.evidence import MacroDef
from corpus_structure.core.vocab import ParseOutcome
from corpus_structure.methods.math import grammar as G
from corpus_structure.methods.math.transform import NotRepresentable

pytestmark = pytest.mark.filterwarnings("error::sympy.utilities.exceptions.SymPyDeprecationWarning")

PAGE: Mapping[str, MacroDef] = {
    name: MacroDef(body=body)
    for name, body in {
        "\\R": "\\mathbb{R}",
        "\\N": "\\mathbb{N}",
        "\\P": "\\mathbb{P}",
        "\\E": "\\mathbb{E}",
        "\\var": "\\text{var}",
        "\\sgn": "\\,\\text{sgn}",
        "\\ms": "\\mathscr",
        "\\odd": "\\frac{1}{2}",
    }.items()
}
OK, AMBIGUOUS, PARTIAL, FAILED = (
    ParseOutcome.OK,
    ParseOutcome.AMBIGUOUS,
    ParseOutcome.PARTIAL,
    ParseOutcome.FAILED,
)


def P(latex: str, kind: G.Kind = "any_value", **declared: set[str]) -> G.MathResult:
    from corpus_structure.semantic.analysis_contracts import prepare_interpretation_context

    declarations = tuple(
        {
            "symbol": symbol,
            "role": role,
            "authority": "source",
            "evidence": "test:declaration",
            "source_id": "test:expression",
            "scope": "test:expression",
            "start": 0,
            "end": len(latex),
        }
        for field, role in (
            ("functions", "function"),
            ("variables", "variable"),
            ("constants", "constant"),
        )
        for symbol in declared.get(field, ())
    )
    context = prepare_interpretation_context(
        macros=PAGE,
        declarations=declarations,
        kind=kind,
        source_id="test:expression",
        scope="test:expression",
        offset=0,
    )
    return G.parse(latex, kind, PAGE, context.grammar_context)


def category(result: G.MathResult) -> str | None:
    return result.failure.category if result.failure else None


# --- Assembly --------------------------------------------------------------------------------


def test_the_shipped_grammar_is_read_unedited_from_sympy() -> None:
    import sympy.parsing.latex.lark as shipped

    assert G.SHIPPED.is_relative_to(G.Path(shipped.__file__).parent)
    assert "latex_string: _relation | _expression" in G.SHIPPED.read_text(encoding="utf-8")


def test_the_extension_names_no_source_fact() -> None:
    extension = G.EXTENSION.read_text(encoding="utf-8")
    for name in (
        "\\\\E",
        "\\\\var",
        "\\\\sd",
        "\\\\skw",
        "\\\\kur",
        "\\\\cov",
        "\\\\cor",
        "\\\\bs",
        "\\\\ms",
        '\\\\R"',
        '\\\\N"',
        "Siegrist",
    ):
        assert name not in extension, name
    assert "%ignore" not in "".join(line.split("//")[0] for line in extension.splitlines())


def test_macros_classify_from_their_bodies() -> None:
    classes = G.classify(PAGE)
    assert dict(classes.sets) == {"\\N": "N", "\\R": "R"}
    assert dict(classes.ops) == {"\\E": "E", "\\P": "P", "\\sgn": "sgn", "\\var": "var"}
    assert dict(classes.styles) == {"\\ms": "\\mathscr"}  # \odd is not in the grammar


def test_one_parser_per_classification() -> None:
    assert G.parser_for(G.classify(PAGE)) is G.parser_for(G.classify(dict(PAGE)))
    other = {**PAGE, "\\odd": MacroDef(body="\\frac{1}{3}")}  # an unclassified body
    assert G.parser_for(G.classify(other)) is G.parser_for(G.classify(PAGE))
    assert G.parser_for(G.classify({})) is not G.parser_for(G.classify(PAGE))


def test_every_ignore_of_the_grammar_is_on_the_drop_list() -> None:
    text = G.grammar_text(G.classify(PAGE))
    G.check_ignores(text)
    ignores = [line for line in text.splitlines() if line.startswith("%ignore")]
    assert any("Bigg" in line and "bigl" in line for line in ignores)  # the sizing commands
    with pytest.raises(G.GrammarError):
        G.check_ignores(text + '\n%ignore "\\\\hspace"\n')
    with pytest.raises(G.GrammarError):
        G.check_ignores(text + "\n%ignore /\\\\hspace/\n")


# --- Whole command names ----------------------------------------------------------------------


def test_command_names_match_whole() -> None:
    assert P("\\Phi").status is OK  # \P is a prefix of \Phi and never matches inside it
    assert P("\\P(A)").kind == "formula"
    assert P("\\sinh x").status is OK
    unknown = P("\\phantom x")
    assert (unknown.status, category(unknown)) == (FAILED, "unknown-command")


def test_a_command_beginning_with_an_ignored_name_fails_honestly() -> None:
    """The spike read `x \\leftarrow y` as the product `x·arrow·y` under its prefix `\\left`."""
    for latex in ("x \\leftarrow y", "A \\leftrightarrow B", "a \\quadrant b"):
        result = P(latex)
        assert result.status is FAILED, latex
        assert not {o.name for o in result.occurrences} & {"a", "r", "o", "w", "n", "t"}
    assert category(P("a \\quadrant b")) == "unknown-command"
    arrow = P("x \\rightarrow 0")
    assert (arrow.status, arrow.kind) == (OK, "relation")
    assert [o.name for o in arrow.occurrences] == ["x"]


# --- Reading ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("latex", "kind"),
    [
        ("a + b \\mu", "formula"),
        ("X = e^Y", "formula"),
        ("x < 1", "relation"),
        ("0 < p \\le 1", "relation"),
        ("x \\in \\R", "member"),
        ("a, b \\in \\R", "member"),
        ("\\R \\setminus \\{0\\}", "set_expr"),
        ("\\{x \\in \\R: x > 0\\}", "set_expr"),
        ("f(x) = 2 x, \\quad x \\in [0, 1]", "list"),
        ("X \\sim N(\\mu, \\sigma^2)", "relation"),
    ],
)
def test_detected_kinds(latex: str, kind: str) -> None:
    result = P(latex)
    assert result.status is OK, (result.notes, result.failure)
    assert result.kind == kind


def test_scripts_are_structure() -> None:
    value = G.to_sympy(P("\\sigma_{X_1}^2 + X_{(n)} + \\mu_i^2 + \\sigma^2_X", "formula"))
    names = {s.name for s in value.free_symbols if isinstance(s, sympy.Symbol)}
    assert names == {"sigma_{X_1}", "X_{(n)}", "mu_{i}", "sigma_{X}"}


def test_sympy_values() -> None:
    b, sigma, x = sympy.symbols("b sigma x")
    cases = {
        "b^2 \\sigma^2": b**2 * sigma**2,
        "\\lvert b \\rvert \\sigma": sympy.Abs(b) * sigma,
        "e^{\\pi}": sympy.exp(sympy.pi),
        "\\E(X)": sympy.Function("E")(sympy.Symbol("X")),
        "\\var(X)": sympy.Function("var")(sympy.Symbol("X")),
    }
    for latex, want in cases.items():
        result = G.parse(latex, "formula", PAGE, G.MathContext(constants=frozenset({"e"})))
        assert G.to_sympy(result) == want, latex
    assert G.to_sympy(P("\\R \\setminus \\{0\\}", "set_expr")) == sympy.Complement(
        sympy.S.Reals, sympy.FiniteSet(0)
    )
    assert G.to_sympy(P("(0, \\infty)", "set_expr")) == sympy.Interval.open(0, sympy.oo)
    assert G.to_sympy(P("\\N_+", "set_expr")) == sympy.S.Naturals
    assert G.to_sympy(P("x \\in \\R", "member")) == sympy.Contains(x, sympy.S.Reals)
    assert G.to_sympy(P("x < 1", "relation")) == sympy.Lt(x, 1)


@pytest.mark.parametrize(
    ("latex", "kind"),
    [
        ("\\mu \\pm \\sigma", "formula"),
        ("x_1 + \\cdots + x_n", "formula"),
        ("A \\cup B", "set_expr"),
        ("(a, b) = (c, d)", "formula"),  # S5-02: a tuple equation parses, without a value
        ("x \\mapsto x^2", "relation"),  # S5-03
    ],
)
def test_constructs_without_a_sympy_value(latex: str, kind: G.Kind) -> None:
    result = P(latex, kind)
    assert result.status is OK
    with pytest.raises(NotRepresentable):
        G.to_sympy(result)


def test_to_sympy_refuses_what_did_not_parse_or_is_ambiguous() -> None:
    with pytest.raises(G.NotParsed):
        G.to_sympy(P("x +"))
    with pytest.raises(G.Ambiguous):
        G.to_sympy(P("a(b + c)", "formula"))


def test_a_product_with_a_non_expression_operand_is_not_a_value() -> None:
    """`dz` reads as SymPy's differential pair; multiplying by it is SymPy's deprecated non-`Expr`
    path, refused, so the two readings of `z \\phi(z)` are not merged through it (the spike read
    this span `ok`)."""
    result = P("dv = z \\phi(z) \\, dz")
    assert result.status is AMBIGUOUS
    assert any("application or product: phi" in note for note in result.notes)


# --- Trailing punctuation and failures --------------------------------------------------------


def test_trailing_sentence_punctuation_gives_partial() -> None:
    result = P("x + y,")
    assert (result.status, result.kind, result.tail) == (PARTIAL, "formula", ",")
    assert category(result) == "incomplete"  # the whole input's failure is kept
    assert P("x + y").failure is None


@pytest.mark.parametrize(
    ("latex", "expected"),
    [
        ("x +", "incomplete"),
        ("a & b", "alignment"),
        ("a ; b", "punctuation-or-list"),
        ("\\begin{matrix} x \\end{matrix}", "environment"),
        ("\\mbox{a} x", "text-in-math"),
        ("A \\leftrightarrow B", "unsupported-relation"),
        ("2 \\cdot (x \\in A)", "unexpected-command"),
    ],
)
def test_failure_categories(latex: str, expected: str) -> None:
    result = P(latex)
    assert (result.status, category(result)) == (FAILED, expected)
    assert result.failure is not None and result.failure.position is not None
    found = tex.token_at(latex, result.failure.position)
    assert result.failure.token == (found.text if found else "")


# --- Ambiguity ---------------------------------------------------------------------------------


def test_application_or_product_is_decided_by_declared_context() -> None:
    assert P("\\Phi(-x)", "formula").status is AMBIGUOUS
    assert P("a(b + c)", "formula").status is AMBIGUOUS
    declared = P("a(b + c)", "formula", variables={"a", "b", "c"})
    assert declared.status is OK
    a, b, c = sympy.symbols("a b c")
    assert G.to_sympy(declared) == a * (b + c)
    assert P("\\Phi(-x)", "formula", functions={"Phi"}).status is OK
    assert P("\\Phi(-x)", "formula", functions={"\\Phi"}).status is OK
    assert P("f(x) y", "formula").status is AMBIGUOUS  # SymPy's grammar picked the product silently
    assert P("F^{-1}(p)", "formula").status is AMBIGUOUS


def test_a_known_function_and_a_definition() -> None:
    assert G.to_sympy(P("\\Gamma(k)", "formula")) == sympy.gamma(sympy.Symbol("k"))
    result = P("g(x) = x^2 + g(1)")
    assert result.status is OK, result.notes
    assert "g declared a function by its definition" in result.notes


def test_an_interval_only_where_a_set_is_expected() -> None:
    assert P("(0, 1)").status is AMBIGUOUS  # interval or pair
    assert P("(0, 1)", "set_expr").status is OK
    assert P("x \\in (0, 1)").status is OK
    assert P("(0, 1)", "formula").kind == "formula"  # a pair (S5-02), never an interval


def test_equal_readings_collapse() -> None:
    result = P("a b / c", "formula")
    assert result.status is OK
    a, b, c = sympy.symbols("a b c")
    assert G.to_sympy(result) == a * b / c


def test_a_lone_symbol_is_a_formula() -> None:
    result = P("X")
    assert (result.status, result.kind) == (OK, "formula")
    assert any("lone symbol" in note for note in result.notes)
    assert P("X", "set_expr").status is OK


def test_a_list_before_in_is_a_membership_of_each_element() -> None:
    result = P("a, b \\in \\R")
    assert (result.status, result.kind) == (OK, "member")
    assert G.to_sympy(result) == sympy.And(
        sympy.Contains(sympy.Symbol("a"), sympy.S.Reals),
        sympy.Contains(sympy.Symbol("b"), sympy.S.Reals),
    )


def test_ordered_sets_make_a_reading_stable() -> None:
    """An unresolved ambiguity keeps its readings in one order across parser builds."""
    first = P("\\Phi(-x)", "formula")
    G._PARSERS.clear()
    G._MEMO.clear()
    again = P("\\Phi(-x)", "formula")
    assert first.tree == again.tree


# --- Occurrences --------------------------------------------------------------------------------


def test_occurrences() -> None:
    latex = "\\sigma_{X_1}^2 + \\mu_i + e^{\\pi x} + \\mathscr{F}"
    context = G.MathContext(constants=frozenset({"e", "\\pi"}))
    found = G.parse(latex, "formula", PAGE, context).occurrences
    got = [
        (o.name, o.base, o.sub, o.sup, latex[o.start : o.end], o.constant, o.in_subscript_of)
        for o in found
    ]
    assert got == [
        ("\\sigma_{X_1}", "\\sigma", "X_1", "2", "\\sigma_{X_1}", False, None),
        ("X_1", "X", "1", None, "X_1", False, "\\sigma_{X_1}"),
        ("\\mu_i", "\\mu", "i", None, "\\mu_i", False, None),
        ("i", "i", None, None, "i", False, "\\mu_i"),
        ("e", "e", None, "\\pi x", "e", True, None),
        ("\\pi", "\\pi", None, None, "\\pi", True, None),
        ("x", "x", None, None, "x", False, None),
        ("\\mathscr F", "\\mathscr F", None, None, "\\mathscr{F}", False, None),
    ]


def test_an_occurrence_is_named_by_its_token_form() -> None:
    latex = "\\bs{X}_{n} + \\ms R"
    macros = {**PAGE, "\\bs": MacroDef(body="\\boldsymbol")}
    found = G.parse(latex, "formula", macros).occurrences
    for o in found:
        assert o.name == tex.token_form(latex[o.start : o.end], macros)
    assert [o.name for o in found if o.in_subscript_of is None] == [
        "\\boldsymbol X_n",
        "\\mathscr R",
    ]


# --- Deadline, thread and memo ------------------------------------------------------------------


def test_a_call_off_the_main_thread_raises() -> None:
    raised: list[BaseException] = []

    def call() -> None:
        try:
            G.parse("x + y", "formula", PAGE)
        except BaseException as error:  # the test records what was raised
            raised.append(error)

    worker = threading.Thread(target=call)
    worker.start()
    worker.join()
    assert len(raised) == 1 and isinstance(raised[0], G.OffMainThread)


def test_integral_relation_construction_does_not_launch_equality_evaluation(monkeypatch) -> None:
    from sympy.core import relational

    evaluations = []

    def forbidden(*args, **kwargs):
        evaluations.append(1)
        raise AssertionError("formal source relation launched equality evaluation")

    monkeypatch.setattr(relational, "is_eq", forbidden)
    latex = "\\int_0^\\infty h(t) \\, dt = \\infty"
    result = P(latex, functions={"h"})
    assert result.status is OK
    value = G.to_sympy(result)
    assert isinstance(value, sympy.Equality)
    assert isinstance(value.lhs, sympy.Integral)
    assert value.rhs is sympy.oo
    assert value.lhs.limits[0].args[1:] == (0, sympy.oo)
    unqualified = G.parse(latex, "any_value", PAGE, seconds=0.3)
    assert unqualified.status in {OK, AMBIGUOUS}
    assert category(unqualified) is None
    assert evaluations == []


@pytest.mark.parametrize(
    ("latex", "constructor", "truth"),
    [
        ("1=1", sympy.Eq, sympy.true),
        ("1 \\ne 1", sympy.Ne, sympy.false),
        ("1<1", sympy.Lt, sympy.false),
        ("1 \\le 1", sympy.Le, sympy.true),
        ("1>1", sympy.Gt, sympy.false),
        ("1 \\ge 1", sympy.Ge, sympy.true),
    ],
)
def test_relations_are_formal_until_explicit_evaluation(latex, constructor, truth):
    value = G.to_sympy(P(latex))
    assert isinstance(value, constructor)
    assert value.args == (sympy.Integer(1), sympy.Integer(1))
    assert value.doit() is truth


def test_relation_chain_keeps_unevaluated_components():
    value = G.to_sympy(P("0<1<2", "relation"))
    assert isinstance(value, sympy.And)
    assert len(value.args) == 2
    assert all(isinstance(part, sympy.StrictLessThan) for part in value.args)
    assert value.doit() is sympy.true


def test_the_deadline_bounds_the_whole_read_including_the_resolver(monkeypatch) -> None:
    """An expensive resolver leaf cannot swallow one expiry and disable the whole-read budget."""
    from corpus_structure.semantic.analysis_contracts import prepare_interpretation_context

    latex = "\\int_0^\\infty h(t) \\, dt = \\infty"
    context = prepare_interpretation_context(
        macros=PAGE, kind="any_value", source_id="deadline-leaf-control"
    ).grammar_context
    assert G.syntax(latex, "any_value", PAGE).tree is not None
    memo: OrderedDict[tuple[str, str, str, str], G.MathResult] = OrderedDict()
    monkeypatch.setattr(G, "_MEMO", memo)
    calls = []

    def slow_equivalence(self, candidates):
        calls.append(1)
        try:
            time.sleep(1)
        except G.Expired:
            time.sleep(1)
        raise AssertionError("resolver escaped its whole-read budget")

    monkeypatch.setattr(G._SymbolicResolver, "equivalent", slow_equivalence)
    results = []
    for _ in range(2):
        started = time.monotonic()
        result = G.parse(latex, "any_value", PAGE, context, seconds=0.3)
        assert (result.status, category(result)) == (FAILED, "timeout")
        assert time.monotonic() - started < 0.3 + 0.5
        results.append(result)
    assert len(calls) == 2
    assert results[0] is not results[1]  # timeouts are never memoized
    assert not memo


def test_the_memo_shares_a_parse() -> None:
    first = P("x^2 + y")
    assert P("x^2 + y") is first
    assert P("x^2 + y", variables={"x"}) is not first
    assert G.parse("x^2 + y", "any_value", {}) is not first


def test_local_definition_records_rule_and_survives_worker_transport():
    import pickle

    result = P("f(x)=x+1", "formula")
    assert result.status is OK
    assert [(d.symbol, d.role, d.rule, d.start, d.end) for d in result.declarations] == [
        ("f", "function", "function-definition-1", 0, len(result.latex))
    ]
    restored = pickle.loads(pickle.dumps(result))
    assert restored.context == result.context
    assert restored.declarations == result.declarations
    assert dict(restored.macros) == dict(result.macros)
