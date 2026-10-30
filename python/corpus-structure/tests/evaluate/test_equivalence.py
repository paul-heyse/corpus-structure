"""Value equivalence (evaluation §3.5, §6 P0-E-2a; D7 §5.3). Expected outcomes are written from
D7 §5.3's tiers, not read back from the comparator."""

from __future__ import annotations

import threading
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from corpus_structure.core import values as V
from corpus_structure.core.evidence import MacroDef
from corpus_structure.core.vocab import Relation
from corpus_structure.evaluate.equivalence import (
    Tier,
    TreeMatch,
    ValueComparator,
    _seed,
    trees_equivalent,
)
from corpus_structure.methods.math.grammar import OffMainThread

pytestmark = pytest.mark.filterwarnings("error::sympy.utilities.exceptions.SymPyDeprecationWarning")
MACROS = {"\\R": MacroDef(body="\\mathbb{R}")}


def f(latex: str, **symbols: str) -> V.Formula:
    return V.Formula(
        t="formula", latex=latex, symbols={k: V.SymbolBinding(bind=v) for k, v in symbols.items()}
    )


def s(latex: str) -> V.SetValue:
    return V.SetValue(t="set", latex=latex)


def cmp(a: Any, b: Any, conds: tuple[Any, ...] = ()) -> tuple[bool, Tier]:
    out = ValueComparator(MACROS, ("e", "\\pi")).compare(a, b, conds)
    return out.equal, out.tier


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (f("b^{2}"), f("b^2"), (True, Tier.CANONICAL)),  # the token form
        (f("a + b"), f("b + a"), (True, Tier.SYMBOLIC)),
        (f("\\frac{a}{2}"), f("0.5 a"), (True, Tier.SYMBOLIC)),
        (f("a + 1"), f("a + 2"), (False, Tier.SYMBOLIC)),  # a nonzero constant apart
        (f("y = 2 x"), f("2 x = y"), (True, Tier.SYMBOLIC)),  # equations up to sign
        (f("x < 1"), f("1 > x"), (True, Tier.SYMBOLIC)),  # > written as <
        (f("x \\in \\R"), f("x \\in \\R"), (True, Tier.CANONICAL)),
        (s("(0, \\infty)"), s("\\R_+"), (True, Tier.SYMBOLIC)),  # the positive reals
        (s("(0, \\infty)"), s("[0, \\infty)"), (False, Tier.SYMBOLIC)),
        (s("[0, 1] \\cup [1, 2]"), s("[0, 2]"), (True, Tier.SYMBOLIC)),
        # Unqualified source log definedness is not established over x's domain.
        # Native cancellation alone cannot prove equivalence of these partial functions.
        (f("e^{\\ln x}"), f("x"), (False, Tier.UNDECIDED)),
        (
            V.TextValue(t="text", v="Normal "),
            V.TextValue(t="text", v="normal"),
            (True, Tier.CANONICAL),
        ),
        (
            V.NumberValue(t="number", v="1.5"),
            V.NumberValue(t="number", v="1.5", unit="cm"),
            (False, Tier.CANONICAL),
        ),  # units as written
        (f("x"), V.TextValue(t="text", v="x"), (False, Tier.CANONICAL)),
    ],
)
def test_value_tiers(a: Any, b: Any, expected: tuple[bool, Tier]) -> None:
    assert cmp(a, b) == expected


def test_the_numeric_tier_uses_the_conditions() -> None:
    """|x| and x agree only where the conditions put x: a numeric decision over x > 0."""
    cond = V.CmpNode(op="cmp", rel=Relation.GT, lhs=f("x"), rhs=f("0"))
    equal, tier = cmp(f("\\sqrt{x^2}"), f("x"), (cond,))
    assert (equal, tier) in ((True, Tier.NUMERIC), (True, Tier.SYMBOLIC))
    assert cmp(f("\\sqrt{x^2}"), f("x")) == (False, Tier.NUMERIC)


def test_undecided_counts_unequal_and_is_logged() -> None:
    comparator = ValueComparator(MACROS)
    out = comparator.compare(f("\\Phi(x)"), f("\\Phi(y)"))  # application or product, undeclared
    assert (out.equal, out.tier) == (False, Tier.UNDECIDED)
    assert comparator.undecided == [out] and "ambiguous" in out.grammar


def test_a_decision_input_decides_an_undecided_pair() -> None:
    plain = ValueComparator(MACROS)
    first = plain.compare(f("\\Phi(x)"), f("\\Phi(y)"))
    decided = ValueComparator(MACROS, decisions={(first.a, first.b): True})
    out = decided.compare(f("\\Phi(x)"), f("\\Phi(y)"))
    assert (out.equal, out.tier) == (True, Tier.DECIDED)


def test_a_comparison_off_the_main_thread_raises() -> None:
    raised: list[BaseException] = []

    def call() -> None:
        try:
            ValueComparator(MACROS).compare(f("a + b"), f("b + a"))
        except BaseException as error:
            raised.append(error)

    worker = threading.Thread(target=call)
    worker.start()
    worker.join()
    assert len(raised) == 1 and isinstance(raised[0], OffMainThread)


@given(st.text(min_size=1, max_size=20), st.text(min_size=1, max_size=20), st.text(max_size=10))
def test_numeric_seeds_do_not_depend_on_argument_order(a: str, b: str, c: str) -> None:
    assert _seed(a, b, c) == _seed(b, a, c)


def test_the_cache_is_symmetric() -> None:
    comparator = ValueComparator(MACROS)
    one = comparator.compare(f("a + b"), f("b + a"))
    assert comparator.compare(f("b + a"), f("a + b")) is one


def _match(comparator: ValueComparator, claims: dict[str, str] | None = None) -> TreeMatch:
    return TreeMatch(
        value_eq=lambda x, y: comparator.compare(x, y).equal,
        claim_eq=lambda x, y: (claims or {}).get(x) == y,
        ref_eq=lambda x, y: x == y,
        span_eq=lambda x, y: x.start < y.end and y.start < x.end,
        canonical_eq=comparator.canonical_equal,
    )


def test_condition_trees_match_their_leaves_one_to_one() -> None:
    comparator = ValueComparator(MACROS)
    member = V.MemberNode(op="member", x=f("x"), set=s("\\R"))
    gt = V.CmpNode(op="cmp", rel=Relation.GT, lhs=f("x"), rhs=f("0"))
    lt = V.CmpNode(op="cmp", rel=Relation.LT, lhs=f("0"), rhs=f("x"))
    claim = V.ClaimNode(op="claim", ref="c1")
    a = V.StoredAnd(op="and", args=(member, V.StoredAnd(op="and", args=(gt, claim))))
    b = V.StoredAnd(op="and", args=(claim_b := V.ClaimNode(op="claim", ref="d1"), lt, member))
    assert trees_equivalent(a, b, _match(comparator, {"c1": "d1"}))
    assert not trees_equivalent(a, b, _match(comparator, {}))  # the premise is not matched
    assert not trees_equivalent(
        a, V.StoredAnd(op="and", args=(claim_b, lt)), _match(comparator, {"c1": "d1"})
    )
    single = V.StoredAnd(op="and", args=(member,))
    assert trees_equivalent(single, member, _match(comparator))
