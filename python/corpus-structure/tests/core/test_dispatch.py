"""Typed dispatch (R03; foundations §3.5, §3.6): every member of each typed union is driven through
each dispatch over it, and the outcome codes are closed.

The members come from the unions themselves (`typing.get_args`), so a member added to a union and
missing here fails `test_every_union_member_has_an_example` before any dispatch is exercised.
Expectations are hand-written per member, independent of the code under test.
"""

from __future__ import annotations

import typing
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from corpus_structure.core.batch import (
    AuthoredItem,
    StoredItem,
    cited_sentences,
    rewrite_citations,
)
from corpus_structure.core.evidence import (
    MacroDef,
)
from corpus_structure.core.values import (
    CONDITION_ADAPTERS,
    VALUE_ADAPTERS,
    AuthoredCondition,
    AuthoredValue,
    EntityRef,
    StoredCondition,
    StoredValue,
)
from corpus_structure.core.vocab import (
    CanonicalForm,
)
from corpus_structure.evaluate.normalization import (
    canonical_condition,
    canonical_value,
    claim_refs,
    condition_nodes,
    expressions,
)

# the canonical form each value tag's range takes (TM §8), written out
BY_TAG = {"text": CanonicalForm.TEXT_FORM, "number": CanonicalForm.NUMBER,
          "bool": CanonicalForm.VERBATIM, "enum": CanonicalForm.ENUM,
          "formula": CanonicalForm.TOKEN_FORM, "set": CanonicalForm.TOKEN_FORM,
          "date": CanonicalForm.VERBATIM, "interval": CanonicalForm.INTERVAL,
          "phrase": CanonicalForm.TEXT_FORM}  # fmt: skip


MACROS = {"\\R": MacroDef(body="\\mathbb{R}")}


def resolve(ref: str) -> str:
    return f"key:{ref}"  # every reference alike, whatever its kind


def members(alias: Any) -> set[type]:
    """The classes of a union alias (`type X = Annotated[A | B, …]` or a plain union)."""
    union = alias.__value__
    if typing.get_origin(union) is typing.Annotated:
        union = typing.get_args(union)[0]
    return set(typing.get_args(union))


# --- Examples, one per member ------------------------------------------------------------------

FORMULA = {"t": "formula", "latex": "b^{2} \\, \\mu", "symbols": {"mu": {"bind": "free"}}}
SET = {"t": "set", "latex": "\\R"}

VALUES: dict[str, list[tuple[dict, dict, int]]] = {}  # form -> (raw, canonical form, expressions)
_SHARED = [
    ({"t": "text", "v": " Location-Scale\nFamily"}, {"t": "text", "v": "location-scale family"}, 0),
    ({"t": "number", "v": "1.5", "unit": " m ", "basis": "per  year"},
     {"t": "number", "v": "1.5", "unit": "m", "basis": "per year"}, 0),
    ({"t": "bool", "v": True}, {"t": "bool", "v": True}, 0),
    (FORMULA, {"t": "formula", "latex": "b^2\\mu"}, 1),
    (SET, {"t": "set", "latex": "\\mathbb R"}, 1),
    ({"t": "date", "v": "2026-01-31"}, {"t": "date", "v": "2026-01-31"}, 0),
    ({"t": "interval", "start": {"t": "formula", "latex": "a"}, "end": {"t": "number", "v": "2"},
      "end_incl": True},
     {"t": "interval", "start": {"t": "formula", "latex": "a"}, "end": {"t": "number", "v": "2"},
      "end_incl": True}, 1),
]  # fmt: skip
# An authored enum value names its enum locally, so it has no key form: keys read the stored
# form, which names it prefixed (X2-01).
NO_KEY_FORM: dict = {}
VALUES["authored"] = [
    *_SHARED,
    ({"t": "enum", "enum": "Kind", "v": "a"}, NO_KEY_FORM, 0),
    ({"t": "phrase", "text": "Roughly", "sentence": "s1"}, {"t": "phrase", "text": "roughly"}, 0),
]
VALUES["stored"] = [
    *_SHARED,
    ({"t": "enum", "enum": "stat:Kind", "v": "a"}, {"t": "enum", "enum": "stat:Kind", "v": "a"}, 0),
    (
        {"t": "phrase", "text": "Roughly", "start": 0, "end": 7},
        {"t": "phrase", "text": "roughly"},
        0,
    ),
]

MEMBER = {"op": "member", "x": {"t": "formula", "latex": "a"}, "set": SET}
LEAF = {"authored": {"sentence": "s2"}, "stored": {"start": 1, "end": 4}}


def conditions(form: str) -> list[tuple[dict, dict, list[str], int]]:
    """(raw, canonical form, claim refs, expressions) for every node kind of the form."""
    canonical_member = {"op": "member", "x": {"t": "formula", "latex": "a"},
                        "set": {"t": "set", "latex": "\\mathbb R"}}  # fmt: skip
    claim = {"op": "claim", "ref": "c1"}
    return [
        ({"op": "and", "args": [MEMBER, claim]}, {"op": "and", "args": sorted_args(
            canonical_member, {"op": "claim", "ref": "key:c1"})}, ["c1"], 2),
        ({"op": "or", "args": [claim, MEMBER]}, {"op": "or", "args": sorted_args(
            canonical_member, {"op": "claim", "ref": "key:c1"})}, ["c1"], 2),
        ({"op": "not", "arg": claim}, {"op": "not", "arg": {"op": "claim", "ref": "key:c1"}},
         ["c1"], 0),
        ({"op": "forall", "var": "\\mu", "set": SET, "body": MEMBER},
         {"op": "forall", "var": "mu", "set": {"t": "set", "latex": "\\mathbb R"},
          "body": canonical_member}, [], 3),
        (claim, {"op": "claim", "ref": "key:c1"}, ["c1"], 0),
        (MEMBER, canonical_member, [], 2),
        ({"op": "cmp", "rel": ">", "lhs": {"t": "formula", "latex": "t"},
          "rhs": {"t": "formula", "latex": "1"}},
         {"op": "cmp", "rel": "<", "lhs": {"t": "formula", "latex": "1"},
          "rhs": {"t": "formula", "latex": "t"}}, [], 2),
        ({"op": "pred", "name": "owns", "args": [{"ref": "X"}, FORMULA]},
         {"op": "pred", "name": "owns", "args": [{"key": "key:X"},
                                                 {"t": "formula", "latex": "b^2\\mu"}]}, [], 1),
        ({"op": "phrase", "text": "For ALL t", **LEAF[form]},
         {"op": "phrase", "text": "for all t"}, [], 0),
        ({"op": "unsupported", "text": "For ALL t", "reason": "r", **LEAF[form]},
         {"op": "unsupported", "text": "for all t"}, [], 0),
    ]  # fmt: skip


def sorted_args(*args: dict) -> list[dict]:
    """D1 §7 orders `and`/`or` arguments by canonical JSON; written out by hand here."""
    member, claim = args
    return [claim, member]  # '{"op":"claim"…' sorts before '{"op":"member"…'


UNIONS = {
    "authored value": (AuthoredValue, VALUE_ADAPTERS["authored"], VALUES["authored"]),
    "stored value": (StoredValue, VALUE_ADAPTERS["stored"], VALUES["stored"]),
    "authored condition": (AuthoredCondition, CONDITION_ADAPTERS["authored"],
                           conditions("authored")),
    "stored condition": (StoredCondition, CONDITION_ADAPTERS["stored"], conditions("stored")),
}  # fmt: skip


@pytest.mark.parametrize("name", UNIONS)
def test_every_union_member_has_an_example(name: str) -> None:
    alias, adapter, examples = UNIONS[name]
    assert {type(adapter.validate_python(e[0])) for e in examples} == members(alias)


@pytest.mark.parametrize("form", ["authored", "stored"])
def test_every_value_member_through_every_value_dispatch(form: str) -> None:
    adapter = VALUE_ADAPTERS[form]
    for raw, canonical, count in VALUES[form]:
        value = adapter.validate_python(raw)
        if canonical is NO_KEY_FORM:
            with pytest.raises(TypeError, match="names its enum locally"):
                canonical_value(value, MACROS, resolve)
        else:
            assert canonical_value(value, MACROS, resolve) == canonical, raw
        assert len(list(expressions(value))) == count, raw
    ref = EntityRef(ref="X")
    assert canonical_value(ref, MACROS, resolve) == {"key": "key:X"}
    assert list(expressions(ref)) == []


@pytest.mark.parametrize("form", ["authored", "stored"])
def test_every_condition_member_through_every_condition_dispatch(form: str) -> None:
    adapter = CONDITION_ADAPTERS[form]
    for raw, canonical, refs, count in conditions(form):
        node = adapter.validate_python(raw)
        assert canonical_condition(node, MACROS, resolve) == canonical, raw
        visited = list(condition_nodes(node))
        assert visited[-1] is node  # children before their parent
        assert claim_refs(node) == refs, raw
        assert len(list(expressions(node))) == count, raw


def test_assert_never_is_reached_only_by_an_unrepresentable_member() -> None:
    stray: Any = object()
    for dispatch in (
        lambda: canonical_value(stray, MACROS, resolve),
        lambda: canonical_condition(stray, MACROS, resolve),
        lambda: list(condition_nodes(stray)),
        lambda: list(expressions(stray)),
    ):
        with pytest.raises(AssertionError):
            dispatch()


@pytest.mark.parametrize("form", ["authored", "stored"])
def test_a_seeded_unknown_operator_or_value_kind_is_refused_at_validation(form: str) -> None:
    xor = {"op": "xor", "args": [MEMBER]}
    with pytest.raises(ValidationError, match=r"does not match any of the expected tags"):
        CONDITION_ADAPTERS[form].validate_python({"op": "and", "args": [xor]})
    with pytest.raises(ValidationError):
        VALUE_ADAPTERS[form].validate_python({"t": "quantity", "v": "1"})


# --- Items and citations -----------------------------------------------------------------------

AUTHORED_ITEMS: list[tuple[dict, list[str]]] = [  # (raw item, sentences it cites)
    ({"local_ref": "X", "type": "RandomVariable", "label": "X", "scope": "local"}, []),
    ({"local_ref": "st", "kind": "theorem", "anchor": ["s1", "s2"]}, ["s1", "s2"]),
    ({"local_ref": "st0", "anchor": "outside",
      "descriptor": {"sentence": "s7", "quote": "the last result"}}, ["s7"]),
    ({"local_ref": "c", "predicate": "p", "subject": "X",
      "object": {"t": "phrase", "text": "x", "sentence": "s4"},
      "qualifiers": {"hedge": {"t": "phrase", "text": "h", "sentence": "s5"},
                     "conditions": {"op": "not", "arg": {"op": "phrase", "text": "y",
                                                         "sentence": "s6"}},
                     "sentence": "s9"},  # a pack qualifier named `sentence`: not a citation
      "evidence": [{"sentence": "s3", "quote": "q", "role": "primary"}]},
     ["s4", "s5", "s6", "s3"]),
    ({"refs": ["a", "b"], "reason": "r"}, []),
    ({"local_ref": "u", "sentence": "c1", "quote": "q", "reason": "r"}, ["c1"]),
]  # fmt: skip
STORED_ITEMS: list[dict] = [
    {"local_ref": "X", "type": "stat:T", "label": "X", "scope": "global"},
    {"local_ref": "st", "kind": "theorem", "anchor": ["seg:1"]},
    {"local_ref": "st0", "anchor": "outside", "descriptor": {"start": 2, "end": 9}},
    {"local_ref": "c", "predicate": "stat:p", "subject": "X", "object": {"ref": "X"},
     "qualifiers": {"stat:sentence": "s3"},
     "evidence": [{"start": 0, "end": 1, "role": "primary"}]},
    {"refs": ["a", "b"], "reason": "r"},
    {"local_ref": "u", "start": 0, "end": 1, "reason": "r"},
]  # fmt: skip
ITEM_ADAPTERS = {"authored": TypeAdapter(AuthoredItem), "stored": TypeAdapter(StoredItem)}


def test_every_item_member_through_citation_finding() -> None:
    authored = [(ITEM_ADAPTERS["authored"].validate_python(raw), cites)
                for raw, cites in AUTHORED_ITEMS]  # fmt: skip
    stored = [ITEM_ADAPTERS["stored"].validate_python(raw) for raw in STORED_ITEMS]
    assert {type(i) for i, _ in authored} == members(AuthoredItem)
    assert {type(i) for i in stored} == members(StoredItem)
    for item, cites in authored:
        seen: list[str] = []
        moved = rewrite_citations(item, lambda s, seen=seen: seen.append(s) or s.upper())
        assert seen == cites, item
        again: list[str] = []
        rewrite_citations(moved, lambda s, again=again: again.append(s) or s)
        assert again == [s.upper() for s in cites]
        assert (moved is item) == (not cites)  # an item citing nothing is returned as it is
    for item in stored:  # the stored form cites by offsets and segment keys, never by id
        assert rewrite_citations(item, lambda s: pytest.fail(f"cited {s}")) is item


def test_cited_sentences_reads_the_typed_items() -> None:
    from corpus_structure.core.batch import AuthoredBatch

    batch = AuthoredBatch.model_validate({
        "unit_ref": "p#u1",
        "entities": [AUTHORED_ITEMS[0][0]],
        "statements": [AUTHORED_ITEMS[1][0], AUTHORED_ITEMS[2][0]],
        "claims": [AUTHORED_ITEMS[3][0]],
        "alternatives": [],
        "unsupported": [AUTHORED_ITEMS[5][0]],
    })  # fmt: skip
    assert cited_sentences(batch) == ["s1", "s2", "s7", "s4", "s5", "s6", "s3", "c1"]
