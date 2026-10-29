"""Declared identity (P0-F-2d; ADR-0023; D1 §5.2, §6.2, §10; TM §8): the key schema compiled from
qualifier specifications, canonical form by declared range, the case policy, the key scheme
recorded beside keys, the carry-over map, and the stated stability limit.

Expectations are written by hand from TM §8's table and D1 §5.2; keys are compared as relations
(equal or different), never as pinned values (D1 §10.1).
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from corpus_structure.core._model.qualifiers import MISSING, QualifierSpec
from corpus_structure.core.batch import StoredQualifiers, StoredScope
from corpus_structure.core.candidates import KeyedCandidateSet
from corpus_structure.core.evidence import (
    RenditionContent,
    Segment,
    SegmentKind,
    content_digest,
    document_key,
    rendition_key,
    segment_key,
)
from corpus_structure.core.frame import FrameFailure
from corpus_structure.core.keys import (
    Drop,
    KeyContext,
    Keys,
    KeySchema,
    LabelRules,
    Member,
    Uniform,
    ValueSpec,
    canonical_condition,
    canonical_qualifier,
    carry_over,
    key_claims,
    text_form,
)
from corpus_structure.core.values import CONDITION_ADAPTERS, VALUE_ADAPTERS
from corpus_structure.core.vocab import (
    CanonicalForm,
    CaseRule,
    DropReason,
    FrameFailureReason,
    KeyRole,
    QualifierStore,
    Relation,
)

C = CanonicalForm
PAGE = "special/Test.html"
DOC = document_key("statistics", PAGE, "0" * 64)


resolve = Uniform(lambda ref: f"key:{ref}")  # every reference alike, whatever its kind


def spec(name: str, canonical: CanonicalForm, range_: str = "string", *,
         role: KeyRole = KeyRole.IDENTITY, when: str | None = None,
         case: CaseRule = CaseRule.FOLD) -> QualifierSpec:  # fmt: skip
    return QualifierSpec(
        name=name, local_name=name.split(":")[1], range=range_, default=MISSING, key_role=role,
        key_role_when=when, canonical=canonical, case=case, store=QualifierStore.JSON,
    )  # fmt: skip


# --- Canonical form by declared range (TM §8), one row each ------------------------------------

FORMULA = {"t": "formula", "latex": "b^{2} \\, \\mu", "symbols": {"mu": {"bind": "free"}}}
MAPS = {
    "stat:Names": ValueSpec("string", C.IDENTIFIER),
    "stat:Params": ValueSpec("Formula", C.TOKEN_FORM),
}
SCHEMA = KeySchema(map_values=MAPS)


def canon(value: Any, canonical: CanonicalForm, range_: str = "x", case=CaseRule.FOLD, **kw: Any):
    return canonical_qualifier(
        value, ValueSpec(range_, canonical, case), SCHEMA, {}, resolve, "stat:q", **kw
    )


@pytest.mark.parametrize(
    ("value", "canonical", "range_", "expected"),
    [
        (FORMULA, C.TOKEN_FORM, "Formula", {"t": "formula", "latex": "b^2\\mu"}),
        ({"t": "set", "latex": "( 0 , \\infty )"}, C.TOKEN_FORM, "SetExpr",
         {"t": "set", "latex": "(0,\\infty)"}),
        ({"t": "text", "v": " Normal\n Family"}, C.TEXT_FORM, "TextValue",
         {"t": "text", "v": "normal family"}),
        ({"t": "phrase", "text": "Roughly", "start": 0, "end": 7}, C.TEXT_FORM, "PhraseValue",
         {"t": "phrase", "text": "roughly"}),
        ("  ORG-101 ", C.IDENTIFIER, "string", "org-101"),
        ({"t": "enum", "enum": "stat:Shape", "v": "Rate"}, C.ENUM, "EnumValue",
         {"t": "enum", "enum": "stat:Shape", "v": "Rate"}),
        ("supposed", C.MEMBER, "ClaimModality", "supposed"),
        ({"ref": "Smith"}, C.ENTITY_KEY, "Entity", "key:Smith"),
        ({"t": "interval", "start": {"t": "number", "v": "1"}, "end_incl": True}, C.INTERVAL,
         "IntervalValue", {"t": "interval", "start": {"t": "number", "v": "1"}, "end_incl": True}),
        ({"mean": FORMULA}, C.MAP, "stat:Params", {"mean": {"t": "formula", "latex": "b^2\\mu"}}),
        ({"t": "number", "v": "2.5", "unit": " m "}, C.NUMBER, "NumberValue",
         {"t": "number", "v": "2.5", "unit": "m"}),
        ({"t": "date", "v": "2026-01-31"}, C.VERBATIM, "DateValue",
         {"t": "date", "v": "2026-01-31"}),
        ({"t": "bool", "v": False}, C.VERBATIM, "BoolValue", {"t": "bool", "v": False}),
        ({"op": "cmp", "rel": ">", "lhs": {"t": "formula", "latex": "t"},
          "rhs": {"t": "formula", "latex": "1"}}, C.CONDITION, "Condition",
         {"op": "cmp", "rel": "<", "lhs": {"t": "formula", "latex": "1"},
          "rhs": {"t": "formula", "latex": "t"}}),
    ],
)  # fmt: skip
def test_each_range_has_its_canonical_form(value: Any, canonical, range_: str, expected) -> None:
    assert canon(value, canonical, range_) == expected


def test_a_stored_scope_enters_by_extent_and_locator() -> None:
    scope = StoredScope(extent="section", segment="seg:x")
    assert canon(scope, C.SCOPE, locate=lambda s: {"loc": s}) == {
        "extent": "section", "segment": {"loc": "seg:x"}
    }  # fmt: skip
    with pytest.raises(ValueError, match="only with its rendition"):
        canon(scope, C.SCOPE)


def test_canonical_form_follows_the_declared_range_not_the_shape() -> None:
    """DA-001's closure cases: `{"ref": "Smith"}` under a string range is a string."""
    assert canon({"ref": "Smith"}, C.MAP, "stat:Names") == {"ref": "smith"}
    assert canon("Shape-Rate", C.IDENTIFIER, case=CaseRule.PRESERVE) == "Shape-Rate"
    assert canon("Shape-Rate", C.IDENTIFIER) == "shape-rate"
    for value, canonical in [
        ({"ref": "Smith"}, C.TOKEN_FORM),  # an entity reference is no formula
        (FORMULA, C.IDENTIFIER),
        ({"t": "text", "v": "x"}, C.NUMBER),
        ({"t": "quantity", "v": "1"}, C.TOKEN_FORM),
        ("x", C.MAP),
    ]:
        with pytest.raises(Exception) as caught:
            canon(value, canonical, "stat:Params")
        assert caught.value.drop == Drop(DropReason.MALFORMED_QUALIFIER, "stat:q")  # type: ignore[attr-defined]


def test_relations_are_the_models() -> None:
    """The relation set and its rewrite are generated (Relation, its member properties)."""
    assert [r.value for r in Relation] == ["<", "<=", "=", "!=", ">", ">="]
    adapter = CONDITION_ADAPTERS["stored"]

    def cmp(rel: str, lhs: str, rhs: str) -> Any:
        return canonical_condition(adapter.validate_python({
            "op": "cmp", "rel": rel, "lhs": {"t": "formula", "latex": lhs},
            "rhs": {"t": "formula", "latex": rhs}}), {}, resolve)  # fmt: skip

    assert cmp(">=", "t", "1") == cmp("<=", "1", "t")
    assert cmp("!=", "a", "b") == cmp("!=", "b", "a") and cmp("<", "a", "b") != cmp("<", "b", "a")
    with pytest.raises(ValidationError):
        cmp("≈", "a", "b")


# --- A small rendition and a test pack ---------------------------------------------------------


def content(sentences: list[str]) -> RenditionContent:
    text, parts = "", []
    for sentence in sentences:
        if parts:
            text += " "
        parts.append(Segment(kind=SegmentKind.SENTENCE, start=len(text),
                             end=len(text) + len(sentence)))  # fmt: skip
        text += sentence
    paragraph = Segment(kind=SegmentKind.PARAGRAPH, start=0, end=len(text), children=parts)
    unit = Segment(kind=SegmentKind.UNIT, start=0, end=len(text), attrs={"id": "u1"},
                   children=(paragraph,))  # fmt: skip
    root = Segment(kind=SegmentKind.DOCUMENT, start=0, end=len(text), children=(unit,))
    return RenditionContent(canonical_text=text, document=root)


def context(sentences: list[str] | None = None) -> KeyContext:
    return KeyContext(DOC, content(sentences or ["Suppose X.", "Then Y."]), PAGE)


def seg(ctx: KeyContext, kind: SegmentKind, n: int = 0) -> str:
    segment = [s for s in ctx.content.document.walk() if s.kind is kind][n]
    ren = rendition_key(DOC, content_digest(ctx.content))
    return segment_key(ren, segment.kind, segment.start, segment.end)


PACK = KeySchema(  # a toy business pack
    predicates=frozenset({"biz:owns"}),
    qualifiers={"biz:owns": (spec("biz:share", C.IDENTIFIER),
                             spec("biz:note", C.TEXT_FORM, "TextValue", role=KeyRole.MEANING),
                             spec("biz:names", C.MAP, "stat:Names"))},
    map_values=MAPS,
    # the pack's modality `reported`, under which attribution identifies
    modality_properties={"attribution_identifying": frozenset({"cited", "reported"}),
                         "premise_forming": frozenset({"supposed"}),
                         "conflict_bearing": frozenset({"asserted", "defined"}),
                         "reserved": frozenset({"posed"})},
    label_case={"biz:Symbolic": CaseRule.PRESERVE},
    slot_case={"biz:code": CaseRule.PRESERVE},
    identity_keys={"biz:Org": ("biz:code",)},
)  # fmt: skip


def keyed(claims: list[dict], entities: list[dict] | None = None, schema: KeySchema = PACK,
          members: dict[str, Member] | None = None,
          ctx: KeyContext | None = None) -> Keys:  # fmt: skip
    ctx = ctx or context()
    base = {"predicate": "biz:owns", "subject": "A", "object": {"ref": "B"},
            "evidence": [{"start": 0, "end": 1, "role": "primary"}]}  # fmt: skip
    cands = KeyedCandidateSet.model_validate({
        "renditions": [ctx.rendition_key],
        "entities": [{"id": n, "type": "biz:Org", "label": n, "scope": "global",
                      "identity": {"biz:code": n}} for n in ("A", "B", "S", "J")]
                    + list(entities or ()),
        "claims": [{**base, **c} for c in claims],
    })  # fmt: skip
    return key_claims(cands, ctx, schema, LabelRules(), members=members)


def claim(qualifiers: dict, schema: KeySchema = PACK) -> str:
    out = keyed([{"id": "c", "qualifiers": qualifiers}], schema=schema)
    assert out.dropped == {}, out.dropped
    return out.claims["c"]


def test_attribution_identifies_under_a_pack_modality_with_the_property() -> None:
    """The F2d revealing case: a business modality given `attribution_identifying`."""
    q = StoredQualifiers.model_validate({"core:modality": "reported"})  # a pack member validates
    assert q.modality == "reported"

    def by(who: str, modality: str) -> str:
        return claim({"core:modality": modality, "core:attribution": {"ref": who}})

    assert by("S", "reported") != by("J", "reported")
    assert by("S", "cited") != by("J", "cited")
    assert by("S", "asserted") == by("J", "asserted") == claim({})  # meaning: outside the key
    attribution = PACK.spec("biz:owns", "core:attribution")
    assert attribution is not None and PACK.role(attribution, "reported") is KeyRole.IDENTITY
    assert "core:hedge" in PACK.meaning_qualifiers("biz:owns", "asserted")
    assert "biz:note" in PACK.meaning_qualifiers("biz:owns", "asserted")
    assert PACK.has_property("defined", "conflict_bearing")


def test_pack_qualifiers_enter_by_their_role_and_range() -> None:
    assert claim({"biz:share": "Half"}) == claim({"biz:share": " half "}) != claim({})
    assert claim({"biz:note": {"t": "text", "v": "x"}}) == claim({})  # meaning
    assert claim({"biz:names": {"ref": "Smith"}}) == claim({"biz:names": {"ref": "SMITH"}})
    out = keyed([{"id": "c", "qualifiers": {"biz:share": {"t": "text", "v": "half"}}}])
    assert out.dropped == {"c": Drop(DropReason.MALFORMED_QUALIFIER, "biz:share")}


def test_case_policy_keys_math_labels_apart_and_prose_alike() -> None:
    """DA-008: X/x and \\Sigma/\\sigma key apart under `preserve`, alike under `fold`."""

    def entity(label: str, type_: str, **extra: Any) -> str:
        out = keyed([], [{"id": "e", "type": type_, "label": label, "scope": "global", **extra}])
        return out.entities["e"]

    for upper, lower in (("X", "x"), ("\\Sigma", "\\sigma")):
        assert entity(upper, "biz:Symbolic") != entity(lower, "biz:Symbolic")
        assert entity(upper, "biz:Prose") == entity(lower, "biz:Prose")
    assert entity("Normal  Distribution", "biz:Prose") == entity("normal distribution", "biz:Prose")
    code = {"biz:code": "Rate"}
    assert entity("x", "biz:Org", identity=code) != entity(
        "x", "biz:Org", identity={"biz:code": "rate"}
    )
    assert text_form("\u03a3X", CaseRule.PRESERVE) == "\u03a3X"
    assert text_form("\u03a3X") == "\u03c3x"


def test_the_scheme_is_recorded_beside_keys_never_in_them() -> None:
    again = PACK.model_copy(update={"key_scheme": 2})
    one, two = keyed([{"id": "c", "qualifiers": {"biz:share": "half"}}]), keyed(
        [{"id": "c", "qualifiers": {"biz:share": "half"}}], schema=again)  # fmt: skip
    assert (one.scheme, two.scheme) == (1, 2)
    assert (one.entities, one.claims) == (two.entities, two.claims)


def test_carry_over_maps_old_keys_to_new_and_reports_missing_inputs() -> None:
    """A hand-built two-scheme pair: scheme 2 preserves the case of `biz:Symbolic` labels."""
    old = PACK
    new = PACK.model_copy(update={"key_scheme": 2, "label_case": {}})
    entities = [{"id": "e", "type": "biz:Symbolic", "label": "X", "scope": "global"}]
    ctx = context()
    cands = KeyedCandidateSet.model_validate({"renditions": [ctx.rendition_key], "entities": entities})

    def keyer(schema: KeySchema):
        return lambda c, x: key_claims(c, x, schema, LabelRules())

    before = keyer(old)(cands, ctx)
    after = keyer(new)(cands, ctx)
    assert before.entities["e"] != after.entities["e"]
    result = carry_over([before.entities["e"], "ent:" + "0" * 32], [(cands, ctx)], keyer(old),
                        keyer(new))  # fmt: skip
    assert (result.from_scheme, result.to_scheme) == (1, 2)
    assert result.mapping == {before.entities["e"]: after.entities["e"]}
    assert result.missing == frozenset({"ent:" + "0" * 32}) and result.split == {}


def test_an_earlier_sentence_inserted_in_an_anchor_shifts_only_that_anchors_later_ordinals() -> (
    None
):
    """The stated stability limit (D1 §10.3; DA-014)."""

    def statement_keys(sentences: list[str]) -> list[str]:
        ctx = KeyContext(DOC, two_units(sentences), PAGE)
        sents = [s for s in ctx.content.document.walk() if s.kind is SegmentKind.SENTENCE]
        ren = rendition_key(DOC, content_digest(ctx.content))
        statements = [{"id": f"st{i}", "kind": "theorem",
                       "anchor": [segment_key(ren, s.kind, s.start, s.end)]}
                      for i, s in enumerate(sents)]  # fmt: skip
        cands = KeyedCandidateSet.model_validate({"renditions": [ren], "statements": statements})
        out = key_claims(cands, ctx, PACK, LabelRules())
        return [out.statements[f"st{i}"] for i in range(len(sents))]

    base = statement_keys(["Alpha a.", "Alpha b.", "|", "Bravo a."])
    inserted = statement_keys(["Alpha new.", "Alpha a.", "Alpha b.", "|", "Bravo a."])
    # "Alpha a." and "Alpha b." move to the next ordinals of u1, so their keys move (the first
    # takes ordinal 2's old key, the second a key no statement had); u2's statement keeps its key
    assert inserted[1] == base[1] != base[0]
    assert inserted[2] not in base
    assert inserted[0] == base[0]  # ordinal 1's key now names the inserted sentence's statement
    assert inserted[3] == base[2]


def two_units(sentences: list[str]) -> RenditionContent:
    """Units u1 and u2 of one paragraph each, split at the "|" entry."""
    text, blocks = "", []
    groups: list[list[str]] = [[]]
    for s in sentences:
        if s == "|":
            groups.append([])
        else:
            groups[-1].append(s)
    for i, group in enumerate(groups):
        if text:
            text += "\n\n"
        start = len(text)
        current = []
        for s in group:
            if current:
                text += " "
            current.append(Segment(kind=SegmentKind.SENTENCE, start=len(text),
                                   end=len(text) + len(s)))  # fmt: skip
            text += s
        p = Segment(kind=SegmentKind.PARAGRAPH, start=start, end=len(text), children=current)
        blocks.append(Segment(kind=SegmentKind.UNIT, start=start, end=len(text),
                              attrs={"id": f"u{i + 1}"}, children=(p,)))  # fmt: skip
    root = Segment(kind=SegmentKind.DOCUMENT, start=0, end=len(text), children=blocks)
    return RenditionContent(canonical_text=text, document=root)


# --- Refusals by code, never exceptions (implementation review of 34cd2a8) ---------------------


def test_map_keys_equal_after_nfc_are_a_malformed_qualifier_for_claims_and_members() -> None:
    composed, decomposed = "é", "é"
    names = {"biz:names": {composed: "a", decomposed: "b"}}
    out = keyed([{"id": "c", "qualifiers": names}])
    assert out.dropped == {"c": Drop(DropReason.MALFORMED_QUALIFIER, "biz:names")}
    note = {"biz:note": {"t": "text", "v": "x"}, "biz:names": {"k": "v"}}
    member = Member(qualifiers=("biz:note",))
    bad_note = {**note, "biz:note": {"t": "text", "v": "lone \ud800"}}
    out = keyed([{"id": "c", "qualifiers": bad_note}], members={"c": member})
    assert "c" in out.claims  # the note is meaning: outside the claim key
    assert out.dropped_members == {"c": Drop(DropReason.MALFORMED_QUALIFIER, "biz:note", ("v",))}


def test_a_lone_surrogate_in_a_qualifier_is_a_malformed_qualifier() -> None:
    out = keyed([{"id": "c", "qualifiers": {"biz:share": "lone \ud800"}}])
    assert out.dropped == {"c": Drop(DropReason.MALFORMED_QUALIFIER, "biz:share")}


@pytest.mark.parametrize(
    ("entities", "claims", "dropped", "expected"),
    [
        ([{"id": "e", "type": "biz:P", "label": "lone \ud800", "scope": "global"}], [], "e",
         Drop(DropReason.MALFORMED_VALUE, "e", ("$.label",))),
        ([{"id": "e", "type": "biz:P", "label": "x", "scope": "local", "symbol": "\ud800"}], [],
         "e", Drop(DropReason.MALFORMED_VALUE, "e", ("$.symbol",))),
        ([], [{"id": "c", "object": {"t": "text", "v": "\ud800"}}], "c",
         Drop(DropReason.MALFORMED_VALUE, "c", ("$.object.value.v",))),
        ([], [{"id": "c", "object": {"t": "phrase", "text": "\ud800", "start": 0, "end": 1}}],
         "c", Drop(DropReason.MALFORMED_VALUE, "c", ("$.object.value.text",))),
    ],
)  # fmt: skip
def test_a_lone_surrogate_elsewhere_is_a_malformed_value(
    entities, claims, dropped, expected
) -> None:
    """The entity label, the symbol, an object text value, and a statement-free claim's phrase."""
    ctx = context()
    for e in entities:
        if e["scope"] == "local":
            e["scope_segment"] = seg(ctx, SegmentKind.UNIT)
    out = keyed(claims, entities, ctx=ctx)
    assert out.dropped[dropped] == expected
    assert "no canonical JSON" in expected.message


def test_canonically_equal_conditions_give_equal_member_keys() -> None:
    """`or(M, M)` and `M` share a claim key and, walking the canonical tree, a member key."""
    a = {"t": "formula", "latex": "a", "symbols": {"a": {"bind": "free"}}}
    m: dict[str, Any] = {"op": "member", "x": a, "set": {"t": "set", "latex": "\\R"}}
    claims: list[dict[str, Any]] = [
              {"id": "c1", "qualifiers": {"core:conditions": {"op": "or", "args": [m, m]}}},
              {"id": "c2", "qualifiers": {"core:conditions": m}},
              {"id": "c3", "qualifiers": {"core:conditions": {"op": "and", "args": [
                  m, {"op": "and", "args": [m, {"op": "or", "args": []}]}]}}},
              {"id": "c4", "qualifiers": {"core:conditions": {"op": "and", "args": [m, m]},
                                          "biz:names": {"k": "v"}}}]  # fmt: skip
    out = keyed(claims, members={c["id"]: Member(bindings=True) for c in claims})
    assert out.claims["c1"] == out.claims["c2"] == out.claims["c3"]
    assert out.members["c1"] == out.members["c2"] == out.members["c3"]


def test_the_schema_refuses_malformed_specifications() -> None:
    with pytest.raises(ValidationError, match="not a known predicate"):
        KeySchema(qualifiers={"biz:owns": (spec("biz:x", C.IDENTIFIER),)})
    with pytest.raises(ValidationError, match="condition 'search_block' is unknown"):
        KeySchema(predicates=frozenset({"biz:owns"}),
                  qualifiers={"biz:owns": (
                      spec("biz:x", C.IDENTIFIER, when="search_block"),)})  # fmt: skip
    with pytest.raises(ValidationError, match="has no value range"):
        KeySchema(predicates=frozenset({"biz:owns"}),
                  qualifiers={"biz:owns": (spec("biz:x", C.MAP, "stat:Nowhere"),)})  # fmt: skip
    with pytest.raises(ValidationError, match="drops core members"):
        KeySchema(modality_properties={"attribution_identifying": frozenset({"reported"})})
    with pytest.raises(ValidationError):
        KeySchema(key_scheme=0)  # type: ignore[bad-argument-type]


def test_every_frame_failure_reason_has_a_message() -> None:
    for code in FrameFailureReason:
        assert FrameFailure("s1", "p", code).message


def test_values_validated_in_the_value_adapters_keep_their_text_form() -> None:
    phrase = VALUE_ADAPTERS["stored"].validate_python(
        {"t": "phrase", "text": "ΣX", "start": 0, "end": 2}
    )
    assert canon(phrase, C.TEXT_FORM, case=CaseRule.PRESERVE) == {"t": "phrase", "text": "ΣX"}
