"""Complete translations and typed references (F2e; foundations §3.5, §3.6; R04, DA-005 to DA-007).

- Translation completeness from the model's slot lists: every source slot of T1 and T2 is mapped
  or declared omitted, and a seeded gap on either side fails.
- The keyed candidate set carries the whole stored batch, the `outside` item included.
- References resolve by their declared kind; a reference of another kind is refused with
  `WRONG_KIND_REFERENCE`, never keyed as what it names.
- `ExternalReference`: the authored descriptor, its stored span, its `xrf` key; an unresolved one is
  kept as a typed node and its citing claim is keyed, and a resolved one stands as its statement.

Expectations are written from D1 §4.4, §10.1, D2 §7.3 and TM §7, never read back from the code.
"""

from __future__ import annotations

import dataclasses
import importlib.util
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from linkml_runtime.utils.schemaview import SchemaView

from corpus_structure.core import translations as T
from corpus_structure.core.batch import (
    AuthoredBatch,
    AuthoredClaim,
    AuthoredOutside,
    StoredBatch,
    StoredOutside,
)
from corpus_structure.core.candidates import (
    AWAITING,
    UNKEYED,
    CandidateClaim,
    CandidateReference,
    KeyedCandidateSet,
)
from corpus_structure.core.evidence import (
    RenditionContent,
    Segment,
    SegmentKind,
    document_key,
    segment_key,
)
from corpus_structure.core.keys import Drop, KeyContext, Keys, KeySchema, LabelRules, key_claims
from corpus_structure.core.values import RefKind, ref_kinds
from corpus_structure.core.vocab import DropReason
from corpus_structure.schema.model import CORE, ci_annotations

# --- Translation completeness (TM §7, DP-08) ---------------------------------------------------


def slot_lister(view: SchemaView):
    """The model's slots of a class in one form (an attribute counts in a form by its `ci:form`,
    a `consolidated` one in both)."""

    def slots(cls: str, form: str) -> Iterator[str]:
        for slot in view.class_induced_slots(cls):
            if ci_annotations(slot).get("ci:form") in (None, form, "consolidated"):
                yield str(slot.name)

    return slots


@pytest.fixture(scope="module")
def core_view() -> SchemaView:
    return SchemaView(str(CORE))


@pytest.mark.parametrize("translation", T.TRANSLATIONS, ids=lambda t: t.id)
def test_every_source_slot_is_mapped_or_declared_omitted(core_view, translation) -> None:
    assert T.completeness(translation, slot_lister(core_view)) == []


def untranslated(view: SchemaView, translation: T.Translation) -> set[str]:
    """The model's batch classes (the Batch envelope's item ranges, and the envelope) that the
    translation has no class map for."""
    batch = {"Batch"} | {str(s.range) for s in view.class_induced_slots("Batch")
                         if view.get_class(str(s.range)) is not None}  # fmt: skip
    batch |= {"OutsideItem"}  # statements[] holds it beside StatementItem (D2 §7.3)
    return batch - {m.source for m in translation.classes}


def test_the_batch_classes_of_the_model_are_all_translated(core_view) -> None:
    for translation in T.TRANSLATIONS:
        assert untranslated(core_view, translation) == set(), translation.id


def test_a_slot_the_model_gains_and_no_translation_maps_fails(core_view, tmp_path) -> None:
    data = yaml.safe_load(CORE.read_text(encoding="utf-8"))
    data["classes"]["ClaimItem"]["attributes"]["confidence"] = {"description": "seeded"}
    path = tmp_path / "core.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    slots = slot_lister(SchemaView(str(path)))
    targets = {"T1": "StoredClaim", "T2": "CandidateClaim"}
    for translation in T.TRANSLATIONS:
        found = T.completeness(translation, slots)
        assert found == [f"{translation.id} ClaimItem -> {targets[translation.id]}: 'confidence' "
                         "is neither mapped nor declared omitted"], found  # fmt: skip


def test_an_outside_item_dropped_between_stored_batch_and_candidate_set_fails(core_view) -> None:
    """The failure scenario: T2's batch map losing `references` leaves the target field filled by
    nothing, and losing the outside item's class map leaves the model's class untranslated."""
    batch, *rest = T.T2.classes
    losing = dataclasses.replace(batch, slots={**batch.slots, "statements": "statements"})
    seeded = dataclasses.replace(T.T2, classes=(losing, *rest))
    assert T.completeness(seeded, slot_lister(core_view)) == [
        "T2 Batch -> KeyedCandidateSet: target field 'references' is filled by nothing declared"
    ]
    no_outside = dataclasses.replace(
        T.T2, classes=tuple(m for m in T.T2.classes if m.source != "OutsideItem")
    )
    assert untranslated(core_view, no_outside) == {"OutsideItem"}


# --- A rendition with a corollary that cites "the last result" ---------------------------------

PAGE = "special/Test.html"
DOC = document_key("statistics", PAGE, "3" * 64)
SENTENCES = ["Let X be normal.", "A corollary of the last result is this.", "It holds."]
FRAME_TEXT = {"s1": SENTENCES[0], "s2": SENTENCES[1], "s3": SENTENCES[2]}


def rendition() -> RenditionContent:
    """One unit of one paragraph whose three sentences are s1, s2, s3."""
    text = " ".join(SENTENCES)
    sentences, start = [], 0
    for sentence in SENTENCES:
        sentences.append(Segment(kind=SegmentKind.SENTENCE, start=start, end=start + len(sentence)))
        start += len(sentence) + 1
    paragraph = Segment(kind=SegmentKind.PARAGRAPH, start=0, end=len(text), children=sentences)
    unit = Segment(kind=SegmentKind.UNIT, start=0, end=len(text), attrs={"id": "u1"},
                   children=(paragraph,))  # fmt: skip
    root = Segment(kind=SegmentKind.DOCUMENT, start=0, end=len(text), children=(unit,))
    return RenditionContent(canonical_text=text, document=root)


def context() -> KeyContext:
    return KeyContext(DOC, rendition(), PAGE)


def sentence_keys(ctx: KeyContext) -> dict[str, str]:
    """sN -> the segment key of the Nth sentence."""
    found = [s for s in ctx.content.document.walk() if s.kind is SegmentKind.SENTENCE]
    return {f"s{i + 1}": segment_key(ctx.rendition_key, s.kind, s.start, s.end)
            for i, s in enumerate(found)}  # fmt: skip


AUTHORED = {
    "unit_ref": f"{PAGE}#u1",
    "statements": [
        {"local_ref": "st_cor", "kind": "corollary", "anchor": ["s2", "s3"]},
        {"local_ref": "e_last", "anchor": "outside",
         "descriptor": {"sentence": "s2", "quote": "the last result"}},
    ],
    "claims": [
        {"local_ref": "c_follows", "predicate": "follows_from", "subject": "st_cor",
         "object": {"ref": "e_last"}, "statement": "st_cor",
         "evidence": [{"sentence": "s2", "quote": "A corollary of the last result",
                       "role": "primary"}]},
    ],
}  # fmt: skip


def locate(ctx: KeyContext, sentence: str, quote: str) -> dict[str, int]:
    """The quote cascade's exact case, as a test stand-in for T1's locator (A0's): the quote's
    offsets inside its sentence on the rendition."""
    text = ctx.content.canonical_text
    start = text.index(FRAME_TEXT[sentence]) + FRAME_TEXT[sentence].index(quote)
    return {"start": start, "end": start + len(quote)}


def stored(ctx: KeyContext, authored: dict = AUTHORED) -> StoredBatch:
    """The stored form of an authored batch on `ctx`'s rendition (what T1 derives)."""
    keys = sentence_keys(ctx)
    statements: list[dict] = []
    for st in authored["statements"]:
        if st["anchor"] == "outside":
            d = st["descriptor"]
            span = locate(ctx, d["sentence"], d["quote"])
            target = {"target": d["target"]} if "target" in d else {}
            statements.append({"local_ref": st["local_ref"], "anchor": "outside",
                               "descriptor": span | target})  # fmt: skip
        else:
            statements.append({**st, "anchor": [keys[s] for s in st["anchor"]]})
    claims = [
        {**c, "predicate": f"core:{c['predicate']}",
         "evidence": [{**locate(ctx, e["sentence"], e["quote"]), "role": e["role"]}
                      for e in c["evidence"]]}
        for c in authored["claims"]
    ]  # fmt: skip
    return StoredBatch.model_validate({"unit_ref": authored["unit_ref"],
                                       "rendition": ctx.rendition_key,
                                       "statements": statements, "claims": claims})  # fmt: skip


def _load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


candidate_set = _load("translate").candidate_set  # T2, applied from its declaration


SCHEMA = KeySchema(predicates=frozenset({"core:follows_from", "core:proves", "stat:p"}))


def keyed(cands: KeyedCandidateSet, ctx: KeyContext) -> Keys:
    return key_claims(cands, ctx, SCHEMA, LabelRules())


# --- The candidate set carries the whole batch -------------------------------------------------


def test_the_candidate_set_carries_the_whole_stored_batch() -> None:
    ctx = context()
    raw = stored(ctx).model_dump(mode="json")
    derived = {**raw["claims"][0], "local_ref": "c_derived", "establishment": "derived",
               "derived_from": ["c_follows"], "rule": "core.transitive"}  # fmt: skip
    with_more = StoredBatch.model_validate({
        **raw, "claims": [*raw["claims"], derived],
        "alternatives": [{"refs": ["c_follows", "c_derived"], "reason": "two readings"}],
        "unsupported": [{"local_ref": "u1", **locate(ctx, "s3", "It holds"), "reason": "r"}],
    })  # fmt: skip
    cands = candidate_set(with_more)
    assert cands.renditions == (ctx.rendition_key,)
    assert [s.id for s in cands.statements] == ["st_cor"]
    assert [r.id for r in cands.references] == ["e_last"]  # the outside item, not lost
    assert cands.references[0].resolved_to is AWAITING and cands.references[0].key is UNKEYED
    claim = cands.claims[1]
    assert (claim.establishment, claim.derived_from, claim.rule) == (
        "derived", ("c_follows",), "core.transitive")  # fmt: skip
    assert [a.refs for a in cands.alternatives] == [("c_follows", "c_derived")]
    assert [u.id for u in cands.unsupported] == ["u1"]
    out = keyed(cands, ctx)
    assert out.dropped == {} and set(out.claims) == {"c_follows", "c_derived"}


def test_keying_refuses_a_context_of_another_rendition() -> None:
    ctx = context()
    other = KeyContext(document_key("statistics", PAGE, "4" * 64), rendition(), PAGE)
    with pytest.raises(ValueError, match="exactly the context's rendition"):
        keyed(candidate_set(stored(ctx)), other)
    two = candidate_set(stored(ctx)).model_copy(
        update={"renditions": tuple(sorted({ctx.rendition_key, other.rendition_key}))}
    )
    with pytest.raises(ValueError, match="exactly the context's rendition"):
        keyed(two, ctx)  # a run-wide set is never keyed


# --- References typed by kind ------------------------------------------------------------------


def test_the_subject_is_typed_entity_or_statement() -> None:
    both = frozenset({RefKind.ENTITY, RefKind.STATEMENT})
    assert ref_kinds(CandidateClaim, "subject") == ref_kinds(AuthoredClaim, "subject") == both
    assert ref_kinds(CandidateClaim, "statement") == {RefKind.STATEMENT}
    assert ref_kinds(CandidateClaim, "derived_from") == {RefKind.CLAIM}
    assert ref_kinds(CandidateClaim, "predicate") == frozenset()


@pytest.mark.parametrize(
    ("claim", "ref", "expected", "named"),
    [
        # the failure scenario: a `claim` condition naming a statement is no claim reference
        ({"qualifiers": {"core:conditions": {"op": "claim", "ref": "st_cor"}}},
         "st_cor", "claim", "a statement"),
        ({"subject": "c_follows"}, "c_follows", "entity or statement", "a claim"),
        ({"statement": "c_follows"}, "c_follows", "statement", "a claim"),
        ({"statement": "e_last"}, "e_last", "statement", "a reference"),
        ({"object": {"ref": "c_follows"}}, "c_follows", "entity", "a claim"),
    ],
)  # fmt: skip
def test_a_wrong_kind_reference_is_refused_with_its_code(claim, ref, expected, named) -> None:
    ctx = context()
    cands = candidate_set(stored(ctx))
    wrong = CandidateClaim.model_validate(
        {**cands.claims[0].model_dump(mode="json"), "id": "c_wrong", **claim}
    )
    out = keyed(cands.model_copy(update={"claims": (*cands.claims, wrong)}), ctx)
    assert out.dropped == {"c_wrong": Drop(DropReason.WRONG_KIND_REFERENCE, ref, (expected, named))}
    assert "c_follows" in out.claims  # the well-typed claim keys as before
    assert ref in out.dropped["c_wrong"].message


def test_a_claim_condition_naming_an_external_reference_keys() -> None:
    """D1 §4.4: an ExternalReference stands where it is cited, a `claim` condition included."""
    ctx = context()
    cands = candidate_set(stored(ctx))
    conditional = cands.claims[0].model_copy(update={
        "id": "c_if", "qualifiers": cands.claims[0].qualifiers.model_validate(
            {"core:conditions": {"op": "claim", "ref": "e_last"}})})  # fmt: skip
    out = keyed(cands.model_copy(update={"claims": (*cands.claims, conditional)}), ctx)
    assert out.dropped == {} and out.claims["c_if"] != out.claims["c_follows"]


# --- ExternalReference: descriptor, span, key, resolution --------------------------------------


def test_an_authored_descriptor_is_stored_with_its_span_and_keyed() -> None:
    ctx = context()
    authored = AuthoredBatch.model_validate(AUTHORED)
    batch = stored(ctx)
    outside = batch.statements[1]
    assert isinstance(outside, StoredOutside)
    span = outside.descriptor
    assert ctx.content.canonical_text[span.start : span.end] == "the last result"
    assert isinstance(authored.statements[1], AuthoredOutside)
    assert authored.statements[1].descriptor.sentence == "s2"
    out = keyed(candidate_set(batch), ctx)
    assert out.references["e_last"].startswith("xrf:")
    assert out.dropped == {} and "c_follows" in out.claims  # cited, unresolved, never dropped


def reference_key(descriptor: dict, anchor: tuple[str, ...] = ("s2", "s3")) -> str:
    ctx = context()
    authored = {**AUTHORED, "statements": [
        {**AUTHORED["statements"][0], "anchor": list(anchor)},
        {**AUTHORED["statements"][1], "descriptor": descriptor},
    ]}  # fmt: skip
    return keyed(candidate_set(stored(ctx, authored)), ctx).references["e_last"]


def test_the_reference_key_is_its_citing_statement_quote_and_target() -> None:
    base = reference_key({"sentence": "s2", "quote": "the last result"})
    assert base == reference_key({"sentence": "s2", "quote": "the last result"})
    assert base != reference_key({"sentence": "s2", "quote": "last result"})
    linked = reference_key({"sentence": "s2", "quote": "the last result",
                            "target": "special/Test.html#thm3"})  # fmt: skip
    assert linked != base
    # the citing statement's key, not its anchor's extent: (s2) keys as (s2, s3) does, while a
    # statement whose first sentence is s1 is another statement
    assert base == reference_key({"sentence": "s2", "quote": "the last result"}, ("s2",))
    assert base != reference_key({"sentence": "s2", "quote": "the last result"}, ("s1", "s2"))


def test_an_unresolved_reference_stays_a_node_and_a_resolved_one_stands_as_its_statement() -> None:
    ctx = context()
    cands = candidate_set(stored(ctx))
    unresolved = keyed(cands, ctx)
    statement = "stm:" + "9" * 32  # the statement of the run consolidation resolved it to
    resolved = cands.model_copy(
        update={"references": (cands.references[0].model_copy(update={"resolved_to": statement}),)}
    )
    after = keyed(resolved, ctx)
    assert after.references == unresolved.references  # the node keeps its own key
    assert after.claims["c_follows"] != unresolved.claims["c_follows"]  # re-keyed (D1 §10.3)
    raw = cands.model_dump(mode="json")
    direct = KeyedCandidateSet.model_validate({
        **raw, "references": [],
        "statements": [*raw["statements"], {**raw["statements"][0], "id": "st_last",
                                            "key": statement}],
        "claims": [{**raw["claims"][0], "object": {"ref": "st_last"}}],
    })  # fmt: skip
    # it fuses with a claim that cites the resolved statement directly
    assert keyed(direct, ctx).claims["c_follows"] == after.claims["c_follows"]


def test_a_reference_in_no_statement_is_uncited() -> None:
    ctx = context()
    authored = {**AUTHORED, "statements": [
        {**AUTHORED["statements"][0], "anchor": ["s3"]},  # s2 is no longer the statement's
        {**AUTHORED["statements"][1]},
    ]}  # fmt: skip
    cands = candidate_set(stored(ctx, authored))
    out = keyed(cands, ctx)
    assert out.dropped["e_last"] == Drop(DropReason.UNCITED_REFERENCE, "e_last")
    assert out.dropped["c_follows"] == Drop(DropReason.DROPPED_DEPENDENCY, "e_last")


def test_a_reference_candidate_refuses_null_states() -> None:
    descriptor = {"start": 0, "end": 3}
    for bad in ({"resolved_to": None}, {"key": None}, {"resolved_to": "ent:" + "1" * 32}):
        with pytest.raises(ValueError):
            CandidateReference.model_validate({"id": "r", "descriptor": descriptor, **bad})
