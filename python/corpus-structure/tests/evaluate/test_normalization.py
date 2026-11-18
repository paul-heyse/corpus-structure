"""Independent canonical forms and normalization expectations used by comparison."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from corpus_structure.core.evidence import (
    MacroDef,
    document_key,
)
from corpus_structure.core.tex import symbol_form
from corpus_structure.core.values import CONDITION_ADAPTERS, AuthoredObject, StoredObject
from corpus_structure.evaluate.normalization import canonical_condition, canonical_value
from corpus_structure.semantic.label_normalization import LabelRules, Rewrite, normalize_label

MACROS = {"\\R": MacroDef(body="\\mathbb{R}")}
DOC = document_key("statistics", "special/Test.html", "0" * 64)


def _ident(ref: str) -> str:
    return f"key:{ref}"


ident = _ident  # every reference alike: these canonical forms are kind-blind


# --- Label normalization (D5 §3.3 point 5) ---------------------------------------------------

RULES = LabelRules(
    articles=("the", "a", "an"),
    head_words={"stat:DistributionFamily": ("distribution", "distributions")},
    rewrites=(
        Rewrite(match=r"^(\w+)ly distributed$", replace=r"\1"),
        Rewrite(match=r"^(\w+) distributed$", replace=r"\1"),
    ),
)


@pytest.mark.parametrize(
    ("text", "type_", "label"),
    [
        ("The  Normal Distribution", "stat:DistributionFamily", "normal"),
        ("normally distributed", "stat:DistributionFamily", "normal"),
        ("gamma distributed", "stat:DistributionFamily", "gamma"),
        ("the normal distributions", "stat:DistributionFamily", "normal"),
        ("distribution", "stat:DistributionFamily", "distribution"),  # never emptied
        ("The normal distribution", "Concept", "normal distribution"),  # no head words there
        ("the", "Concept", "the"),  # a lone article stays
        ("An  exponential family", "Concept", "exponential family"),
    ],
)
def test_normalize_label(text: str, type_: str, label: str) -> None:
    assert normalize_label(text, type_, RULES) == label


def test_symbols_in_key_form() -> None:
    assert symbol_form("\\mu", MACROS) == "mu"
    assert symbol_form("a + b X", MACROS) == "a+bX"
    assert symbol_form("\\R", MACROS) == "\\mathbb R"
    assert symbol_form("X_{1}", MACROS) == "X_1"


# --- Canonical values ------------------------------------------------------------------------


def typed(raw: dict, adapters: tuple[TypeAdapter[Any], ...]) -> Any:
    """`raw` validated in the form it is written in (stored first, then authored)."""
    for adapter in adapters:
        try:
            return adapter.validate_python(raw)
        except ValidationError:
            continue
    raise AssertionError(f"{raw!r} is in neither form")


OBJECTS = (TypeAdapter(StoredObject), TypeAdapter(AuthoredObject))
CONDITIONS = (CONDITION_ADAPTERS["stored"], CONDITION_ADAPTERS["authored"])


def cv(value: dict) -> Any:
    return canonical_value(typed(value, OBJECTS), MACROS, ident)


def test_canonical_values() -> None:
    assert cv({"t": "text", "v": "  Location-Scale\nFamily "}) == {
        "t": "text", "v": "location-scale family"
    }  # fmt: skip
    assert cv({"t": "number", "v": "30", "unit": " cm "}) == {
        "t": "number",
        "v": "30",
        "unit": "cm",
    }
    assert cv({"t": "number", "v": "30", "unit": "cm"}) != cv(
        {"t": "number", "v": "0.3", "unit": "m"}
    )
    assert cv({"t": "formula", "latex": "b^{2} \\, \\sigma", "symbols": {"b": {"bind": "free"}},
               "sympy": "x", "parse": "ok"}) == {"t": "formula", "latex": "b^2\\sigma"}  # fmt: skip
    assert cv({"t": "set", "latex": "\\R"}) == {"t": "set", "latex": "\\mathbb R"}
    assert cv({"t": "date", "v": "2026-01-31"}) == {"t": "date", "v": "2026-01-31"}
    assert cv({"t": "phrase", "text": "Roughly", "start": 3, "end": 10}) == cv(
        {"t": "phrase", "text": "roughly", "sentence": "s1"}
    )
    assert cv({"t": "interval", "start": {"t": "date", "v": "2026"}, "end_incl": True}) == {
        "t": "interval", "start": {"t": "date", "v": "2026"}, "end_incl": True
    }  # fmt: skip
    assert cv({"ref": "X"}) == {"key": "key:X"}


# --- Canonical conditions --------------------------------------------------------------------


def member(x: str, s: str) -> dict:
    return {"op": "member", "x": {"t": "formula", "latex": x}, "set": {"t": "set", "latex": s}}


def cc(node: dict, symmetric: frozenset[str] = frozenset()) -> Any:
    return canonical_condition(typed(node, CONDITIONS), MACROS, ident, symmetric)


def test_and_or_flatten_collapse_drop_and_sort() -> None:
    a, b, c = member("a", "\\R"), member("b", "\\R"), {"op": "claim", "ref": "c1"}
    nested = {"op": "and", "args": [a, {"op": "and", "args": [b, {"op": "or", "args": [c]}]}]}
    flat = {"op": "and", "args": [c, b, a]}
    assert cc(nested) == cc(flat)
    assert cc(flat)["op"] == "and" and len(cc(flat)["args"]) == 3
    assert cc({"op": "and", "args": [a]}) == cc(a)
    assert cc({"op": "and", "args": []}) is None
    assert cc({"op": "and", "args": [{"op": "or", "args": []}, a]}) == cc(a)
    assert cc({"op": "not", "arg": {"op": "and", "args": []}}) is None
    # and(or(and(a, b))) collapses to and(a, b), which then flattens into its parent
    deep = {"op": "and", "args": [{"op": "or", "args": [{"op": "and", "args": [a, b]}]}, c]}
    assert cc(deep) == cc(flat)
    assert cc({"op": "or", "args": [a, b]}) != cc({"op": "and", "args": [a, b]})


def test_greater_is_written_as_less_with_sides_swapped() -> None:
    def cmp(rel: str, lhs: str, rhs: str) -> dict:
        return {"op": "cmp", "rel": rel, "lhs": {"t": "formula", "latex": lhs},
                "rhs": {"t": "formula", "latex": rhs}}  # fmt: skip

    assert cc(cmp(">", "t", "1")) == cc(cmp("<", "1", "t"))
    assert cc(cmp(">=", "t", "1")) == cc(cmp("<=", "1", "t"))
    assert cc(cmp("<", "t", "1")) != cc(cmp("<", "1", "t"))


def test_pred_arguments_sorted_only_when_symmetric() -> None:
    xy = {"op": "pred", "name": "independent", "args": [{"ref": "X"}, {"ref": "Y"}]}
    yx = {"op": "pred", "name": "independent", "args": [{"ref": "Y"}, {"ref": "X"}]}
    assert cc(xy) != cc(yx)
    assert cc(xy, frozenset({"independent"})) == cc(yx, frozenset({"independent"}))


def test_phrase_leaves_enter_by_text_alone() -> None:
    stored = {"op": "unsupported", "text": "For  ALL t", "start": 1, "end": 9, "coarse": True,
              "reason": "quantifier"}  # fmt: skip
    authored = {"op": "unsupported", "text": "for all t", "sentence": "s2", "reason": "other"}
    assert cc(stored) == cc(authored) == {"op": "unsupported", "text": "for all t"}
    assert cc({"op": "phrase", "text": "x"}) != cc({"op": "unsupported", "text": "x", "reason": ""})


def test_forall_canonicalizes_its_parts() -> None:
    node = {"op": "forall", "var": "\\mu", "set": {"t": "set", "latex": "\\R"},
            "body": {"op": "and", "args": [member("x_{i}", "\\R")]}}  # fmt: skip
    assert cc(node) == {
        "op": "forall", "var": "mu", "set": {"t": "set", "latex": "\\mathbb R"},
        "body": {"op": "member", "x": {"t": "formula", "latex": "x_i"},
                 "set": {"t": "set", "latex": "\\mathbb R"}},
    }  # fmt: skip
