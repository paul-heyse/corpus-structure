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

from corpus_structure.core import keys as keys_module
from corpus_structure.core.batch import (
    AuthoredItem,
    StoredItem,
    cited_sentences,
    rewrite_citations,
)
from corpus_structure.core.candidates import KeyedCandidateSet
from corpus_structure.core.evidence import (
    MacroDef,
    RenditionContent,
    Segment,
    SegmentKind,
    content_digest,
    document_key,
    rendition_key,
    segment_key,
)
from corpus_structure.core.keys import (
    Drop,
    KeyContext,
    KeySchema,
    LabelRules,
    Member,
    Rewrite,
    canonical_condition,
    canonical_qualifier,
    canonical_value,
    claim_refs,
    condition_nodes,
    expressions,
    key_claims,
)
from corpus_structure.core.locators import LocatorIndex
from corpus_structure.core.values import (
    CONDITION_ADAPTERS,
    VALUE_ADAPTERS,
    AuthoredCondition,
    AuthoredValue,
    EntityRef,
    StoredCondition,
    StoredValue,
)
from corpus_structure.core.vocab import DropReason

MACROS = {"\\R": MacroDef(body="\\mathbb{R}")}


def resolve(ref: str) -> str:
    return f"key:{ref}"


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
    ({"t": "enum", "enum": "stat:Kind", "v": "a"}, {"t": "enum", "enum": "stat:Kind", "v": "a"}, 0),
    (FORMULA, {"t": "formula", "latex": "b^2\\mu"}, 1),
    (SET, {"t": "set", "latex": "\\mathbb R"}, 1),
    ({"t": "date", "v": "2026-01-31"}, {"t": "date", "v": "2026-01-31"}, 0),
    ({"t": "interval", "start": {"t": "formula", "latex": "a"}, "end": {"t": "number", "v": "2"},
      "end_incl": True},
     {"t": "interval", "start": {"t": "formula", "latex": "a"}, "end": {"t": "number", "v": "2"},
      "end_incl": True}, 1),
]  # fmt: skip
VALUES["authored"] = [
    *_SHARED,
    ({"t": "phrase", "text": "Roughly", "sentence": "s1"}, {"t": "phrase", "text": "roughly"}, 0),
]
VALUES["stored"] = [
    *_SHARED,
    ({"t": "phrase", "text": "Roughly", "start": 0, "end": 7},
     {"t": "phrase", "text": "roughly"}, 0),
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
        assert canonical_value(value, MACROS, resolve) == canonical, raw
        assert len(list(expressions(value))) == count, raw
        if form == "stored":
            assert canonical_qualifier(value, MACROS, resolve) == canonical, raw
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
        if form == "stored":
            assert canonical_qualifier(node, MACROS, resolve) == canonical, raw


def test_assert_never_is_reached_only_by_an_unrepresentable_member() -> None:
    stray: Any = object()
    for dispatch in (
        lambda: canonical_value(stray, MACROS, resolve),
        lambda: canonical_condition(stray, MACROS, resolve),
        lambda: list(condition_nodes(stray)),
        lambda: list(expressions(stray)),
        lambda: canonical_qualifier(stray, MACROS, resolve),
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
    with pytest.raises(ValidationError):  # nor can a stored claim carry one into keying
        KeyedCandidateSet.model_validate({"claims": [{
            "id": "c1", "predicate": "stat:p", "subject": "X", "object": {"ref": "Y"},
            "qualifiers": {"core:conditions": xor},
        }]})  # fmt: skip


# --- Items and citations -----------------------------------------------------------------------

AUTHORED_ITEMS: list[tuple[dict, list[str]]] = [  # (raw item, sentences it cites)
    ({"local_ref": "X", "type": "RandomVariable", "label": "X", "scope": "local"}, []),
    ({"local_ref": "st", "kind": "theorem", "anchor": ["s1", "s2"]}, ["s1", "s2"]),
    ({"local_ref": "st0", "kind": "theorem", "anchor": "outside"}, []),
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
    assert cited_sentences(batch) == ["s1", "s2", "s4", "s5", "s6", "s3", "c1"]


# --- Keying outcomes ---------------------------------------------------------------------------

PAGE = "special/Test.html"
DOC = document_key("statistics", PAGE, "0" * 64)
SENTENCES = ["Suppose that X is normal.", "Then Y is normal.", "Recall the gamma function."]


def content() -> RenditionContent:
    """Three units of one paragraph and one sentence each."""
    text, units = "", []
    for i, sentence in enumerate(SENTENCES):
        if text:
            text += "\n\n"
        start = len(text)
        text += sentence
        s = Segment(kind=SegmentKind.SENTENCE, start=start, end=len(text))
        p = Segment(kind=SegmentKind.PARAGRAPH, start=start, end=len(text), children=(s,))
        units.append(Segment(kind=SegmentKind.UNIT, start=start, end=len(text),
                             attrs={"id": f"u{i + 1}"}, children=(p,)))  # fmt: skip
    root = Segment(kind=SegmentKind.DOCUMENT, start=0, end=len(text), children=units)
    return RenditionContent(canonical_text=text, document=root)


def context() -> KeyContext:
    return KeyContext(DOC, content(), PAGE, MACROS)


def seg(ctx: KeyContext, kind: SegmentKind, n: int = 0) -> str:
    segment = [s for s in ctx.content.document.walk() if s.kind is kind][n]
    ren = rendition_key(DOC, content_digest(ctx.content))
    return segment_key(ren, segment.kind, segment.start, segment.end)


SCHEMA = KeySchema(
    predicates=frozenset({"stat:p"}),
    identity_qualifiers={"stat:p": ("stat:sentence", "stat:values")},
)
RULES = LabelRules()


def key(ctx: KeyContext, entities: list[dict], statements: list[dict], claims: list[dict],
        members: dict[str, Member] | None = None):  # fmt: skip
    base = {"predicate": "stat:p", "subject": "N", "object": {"ref": "N"},
            "evidence": [{"start": 0, "end": 5, "role": "primary"}]}  # fmt: skip
    cands = KeyedCandidateSet.model_validate({
        "entities": [{"id": "N", "type": "stat:T", "label": "normal", "scope": "global"},
                     *entities],
        "statements": statements,
        "claims": [{**base, **c} for c in claims],
    })  # fmt: skip
    return key_claims(cands, ctx, SCHEMA, RULES, members=members)


def test_every_drop_reason_has_a_case_producing_it() -> None:
    ctx = context()
    sentence = seg(ctx, SegmentKind.SENTENCE)
    entities = [
        {"id": "a", "type": "stat:P", "label": "a", "scope": "global",
         "identity": {"stat:of": "b"}},
        {"id": "b", "type": "stat:P", "label": "b", "scope": "global",
         "identity": {"stat:of": "a"}},
        {"id": "z", "type": "stat:P", "label": "z", "scope": "global",
         "identity": {"stat:of": "nowhere"}},
    ]  # fmt: skip
    statements = [
        {"id": "st", "kind": "theorem", "anchor": [sentence]},
        {"id": "gone", "kind": "theorem", "anchor": ["seg:" + "0" * 32]},
        {"id": "last", "kind": "theorem", "anchor": "outside"},
    ]
    claims = [
        {"id": "c_predicate", "predicate": "stat:q"},
        {"id": "c_outside", "statement": "last"},
        {"id": "c_unknown", "subject": "nobody"},
        {"id": "c_dropped", "statement": "gone"},
        {"id": "c_claim_ref", "qualifiers": {"core:conditions": {"op": "claim", "ref": "c9"}}},
        {"id": "c_cycle", "qualifiers": {"core:conditions": {"op": "claim", "ref": "c_cycle"}}},
        {"id": "c_float", "qualifiers": {"stat:values": {"mean": 1.5}}},
        {"id": "c_kind", "qualifiers": {"stat:values": {"mean": {"t": "quantity", "v": "1"}}}},
        {"id": "c_ok", "statement": "st", "qualifiers": {"stat:values": {"mean": FORMULA}}},
    ]
    identity = KeySchema(
        identity_keys={"stat:P": ("stat:of",)},
        entity_identity={"stat:P": ("stat:of",)},
        predicates=frozenset({"stat:p"}),
        identity_qualifiers={"stat:p": ("stat:values",)},
    )
    base = {"predicate": "stat:p", "subject": "N", "object": {"ref": "N"},
            "evidence": [{"start": 0, "end": 5, "role": "primary"}]}  # fmt: skip
    cands = KeyedCandidateSet.model_validate({
        "entities": [{"id": "N", "type": "stat:T", "label": "normal", "scope": "global"},
                     *entities],
        "statements": statements,
        "claims": [{**base, **c} for c in claims],
    })  # fmt: skip
    out = key_claims(cands, ctx, identity, RULES)
    assert out.dropped == {
        "a": Drop(DropReason.IDENTITY_CYCLE, "a"),
        "b": Drop(DropReason.IDENTITY_CYCLE, "b"),
        "z": Drop(DropReason.UNKNOWN_IDENTITY_ENTITY, "nowhere"),
        "gone": Drop(DropReason.SEGMENT_NOT_ON_RENDITION, "seg:" + "0" * 32),
        "c_predicate": Drop(DropReason.UNKNOWN_PREDICATE, "stat:q"),
        "c_outside": Drop(DropReason.OUTSIDE_UNRESOLVED, "last"),
        "c_unknown": Drop(DropReason.UNKNOWN_REFERENCE, "nobody"),
        "c_dropped": Drop(DropReason.DROPPED_DEPENDENCY, "gone"),
        "c_claim_ref": Drop(DropReason.UNKNOWN_CLAIM_REF, "c9"),
        "c_cycle": Drop(DropReason.CONDITION_CYCLE, "c_cycle", ("c_cycle", "c_cycle")),
        "c_float": Drop(DropReason.MALFORMED_QUALIFIER, "stat:values", ("mean",)),
        "c_kind": Drop(DropReason.MALFORMED_QUALIFIER, "stat:values", ("mean",)),
    }
    assert set(out.claims) == {"c_ok"}
    assert {d.code for d in out.dropped.values()} == set(DropReason)
    for drop in out.dropped.values():  # every code projects to a message naming its subject
        assert drop.ref in drop.message or drop.code is DropReason.CONDITION_CYCLE


def test_a_pack_qualifier_named_sentence_keys_as_written() -> None:
    """`stat:sentence` is a schema qualifier like any other: keyed by its text form, never read
    as a citation (R03, DA-004)."""
    ctx = context()

    def keys_of(value: Any) -> tuple[str, str]:
        out = key(ctx, [], [], [{"id": "c1", "qualifiers": {"stat:sentence": value}}],
                  members={"c1": Member(qualifiers=("stat:sentence",), bindings=True)})  # fmt: skip
        assert out.dropped == {} and out.dropped_members == {}
        return out.claims["c1"], out.members["c1"]

    assert keys_of("s3") == keys_of(" S3 ")  # the text form of a literal
    assert keys_of("s3") != keys_of("s4")
    assert keys_of({"sentence": "s3"}) != keys_of("s3")


def test_preparation_happens_once_per_context(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"annotation_units": 0, "content_digest": 0, "claim_parts": 0}

    def counted(name: str, function: Any) -> Any:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            calls[name] += 1
            return function(*args, **kwargs)

        return wrapper

    monkeypatch.setattr(LocatorIndex, "annotation_units",
                        counted("annotation_units", LocatorIndex.annotation_units))  # fmt: skip
    monkeypatch.setattr(keys_module, "content_digest",
                        counted("content_digest", keys_module.content_digest))  # fmt: skip
    monkeypatch.setattr(keys_module, "claim_parts",
                        counted("claim_parts", keys_module.claim_parts))  # fmt: skip
    ctx = context()
    sentences = [s for s in ctx.content.document.walk() if s.kind is SegmentKind.SENTENCE]
    # Paragraph-level statements outside any `unit`/`details`: each needs the annotation units.
    no_units = RenditionContent(
        canonical_text=ctx.content.canonical_text,
        document=Segment(kind=SegmentKind.DOCUMENT, start=0, end=len(ctx.content.canonical_text),
                         children=[u.children[0] for u in ctx.content.document.children]),
    )  # fmt: skip
    flat = KeyContext(DOC, no_units, PAGE, MACROS)
    ren = rendition_key(DOC, content_digest(no_units))
    calls["content_digest"] = 0  # the test's own digest above is not the context's
    statements = [{"id": f"st{i}", "kind": "theorem",
                   "anchor": [segment_key(ren, s.kind, s.start, s.end)]}
                  for i, s in enumerate(sentences)]  # fmt: skip
    claims = [{"id": f"c{i}", "statement": f"st{i}"} for i in range(len(sentences))]
    out = key(flat, [], statements, claims,
              members={c["id"]: Member(bindings=True) for c in claims})  # fmt: skip
    assert len(out.statements) == 3 and len(out.members) == 3 and out.dropped == {}
    assert calls == {"annotation_units": 1, "content_digest": 1, "claim_parts": 3}


def test_malformed_pack_and_schema_inputs_are_refused_at_construction() -> None:
    """Construction errors stay `ValueError`s: they are input errors, not keying outcomes."""
    with pytest.raises(ValidationError, match="does not compile"):
        LabelRules(rewrites=(Rewrite(match="(unclosed", replace=""),))
    with pytest.raises(ValidationError, match="core qualifier"):
        KeySchema(predicates=frozenset({"stat:p"}), identity_qualifiers={"stat:p": ("core:hedge",)})
