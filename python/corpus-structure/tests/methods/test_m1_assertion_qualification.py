"""Assertion qualification from retained source columns with a controlled decoder."""

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.methods.assertion_qualification import AssertionQualification
from corpus_structure.methods.gliner import GlinerRefused
from corpus_structure.methods.m1_annotations import consume_annotations
from corpus_structure.methods.m1_source import M1Candidates, configured_packs
from corpus_structure.methods.record_assembly import OCCURRENCE_POLICY, assemble_records
from corpus_structure.orchestrate.m1 import registry
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext,
    SourceSlice,
    SyntheticText,
)

from .test_m1_producer import (
    ROOT,
    ControlledDecoder,
    detail_object,
    detail_objects,
    owned_reader,
    view,
)
from .test_m1_source_profile import config
from .test_record_assembly import report, span


def group(text, subject, predicate, obj, *, start=0):
    result = {}
    for role, literal in (("subject", subject), ("predicate", predicate), ("object", obj)):
        offset = text.index(literal, start)
        result[role] = span(offset, offset + len(literal), literal)
    return result


class AssertionDecoder(ControlledDecoder):
    def __init__(self, text, groups):
        super().__init__("empty")
        self.text = text
        self.groups = groups

    def extract(self, pack, inputs, *, threshold, check_active):
        (report,) = super().extract(pack, inputs, threshold=threshold, check_active=check_active)
        (item,) = inputs
        if "assertion" in report.raw and item.text == self.text:
            report = replace(report, raw_json=json.dumps({"assertion": self.groups}))
        return (report,)


def produce(monkeypatch, text, groups, *, heading=None):
    source = view(text, heading=heading)
    reader = owned_reader(source)
    producer = M1Candidates()
    decoder = AssertionDecoder(text, groups)
    monkeypatch.setattr(producer, "_resident", lambda _: decoder)
    cfg = registry(ROOT / "domains/statistics").overlay(producer.name, "default")
    unit = SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, source.ref.id, source.ref.key))
    (result,) = producer.run(
        (unit,), cfg, SimpleNamespace(reader=reader, check_active=lambda: None)
    )
    assert result.records and result.parse_detail
    assert all(r["family"] == "assertion" and r["standing"] == "candidate" for r in result.records)
    return result.records, result.parse_detail


def evidence(record, role):
    field = next(f for f in record["fields"] if f["role"] == role)
    by_id = {a["anchor_id"]: a for a in record["anchors"]}
    return [
        (a["pointer"], a["start"], a["end"], a["source_piece"])
        for e in record["evidence_sets"]
        if e["set_id"] in field["evidence_sets"]
        for a in (by_id[key] for key in e["anchors"])
    ]


def assert_classification(record, role, label, *, cue=None, start=None):
    field = next(f for f in record["fields"] if f["role"] == role)
    if label is None:
        assert field["state"] == "unresolved"
        assert field["evidence_status"] == "unavailable"
        assert "value" not in field and not field.get("evidence_sets")
        return
    assert field["state"] == "present"
    assert field["value"] == {"kind": f"assertion_{role}", "label": label}
    assert field["evidence_status"] == "available"
    assert [
        e["usage"] for e in record["evidence_sets"] if e["set_id"] in field["evidence_sets"]
    ] == ["classification_cue"]
    assert isinstance(start, int) and isinstance(cue, str)
    assert evidence(record, role) == [("#/texts/1", start, start + len(cue), cue)]


def test_repeated_predicates_qualify_only_at_their_own_source_occurrence(monkeypatch):
    positive = "The pumps drain the tanks."
    negative = "The pumps do not drain the tanks."
    possible = "The pumps might drain the tanks."
    text = " ".join((positive, negative, possible))
    starts = (0, len(positive) + 1, len(positive) + len(negative) + 2)
    groups = [group(text, "The pumps", "drain", "the tanks", start=i) for i in starts]
    records, details = produce(monkeypatch, text, groups)
    records = sorted(records, key=lambda record: evidence(record, "predicate")[0][1])
    assert len({r["record_id"] for r in records}) == 3
    assert [evidence(r, "predicate")[0][1:] for r in records] == [
        (10, 15, "drain"),
        (44, 49, "drain"),
        (77, 82, "drain"),
    ]
    first, second, third = records
    assert_classification(first, "polarity", "positive", cue=positive[:-1], start=starts[0])
    assert_classification(first, "modality", "asserted", cue=positive[:-1], start=starts[0])
    assert_classification(second, "polarity", "negative", cue="not", start=text.index("not"))
    assert_classification(second, "modality", "asserted", cue=negative[:-1], start=starts[1])
    assert_classification(third, "polarity", "positive", cue=possible[:-1], start=starts[2])
    assert_classification(third, "modality", "possible", cue="might", start=text.index("might"))
    (retained,) = [r for r in detail_objects(details["reports"]) if r["family"] == "assertion"]
    raw_json = detail_object(retained["report"])["raw_json"]
    assert isinstance(raw_json, str) and json.loads(raw_json) == {"assertion": groups}
    blocks = detail_object(details["annotation_product"])["blocks"]
    assert isinstance(blocks, list) and len(blocks) == 1 and isinstance(blocks[0], str)
    for row in records:
        assert f"annotation:{blocks[0]}" in row["computation_dependencies"]


@pytest.mark.parametrize(
    ("text", "parts", "heading", "label", "cue"),
    [
        (
            "The managers must review the forms.",
            ("The managers", "review", "the forms"),
            "Requirements",
            "required",
            "must",
        ),
        (
            "The managers must review the forms.",
            ("The managers", "review", "the forms"),
            None,
            None,
            None,
        ),
        (
            "The managers must not review the forms.",
            ("The managers", "review", "the forms"),
            "Requirements",
            None,
            None,
        ),
        (
            "The term means an average.",
            ("The term", "means", "an average"),
            None,
            "defined",
            "The term means an average",
        ),
    ],
)
def test_modality_requires_a_supported_local_reading(monkeypatch, text, parts, heading, label, cue):
    records, _ = produce(monkeypatch, text, [group(text, *parts)], heading=heading)
    (record,) = records
    block_start = len(heading) + 1 if heading else 0
    start = block_start + text.index(cue) if cue else None
    assert_classification(record, "modality", label, cue=cue, start=start)


@pytest.mark.parametrize(
    ("text", "parts"),
    [
        (
            "The workers do not heat the water and stir the mixture.",
            ("The workers", "heat", "the water"),
        ),
        (
            "The pumps might drain the tanks. The fans cool the motors.",
            ("The pumps", "drain", "the motors"),
        ),
        ("The pumps might drain the tanks.", ("The pumps", "drain the tanks", "the tanks")),
    ],
    ids=("ambiguous-negation", "cross-clause-object", "inexact-predicate"),
)
def test_unsupported_attachment_keeps_literal_candidate_and_unresolved_qualifiers(
    monkeypatch, text, parts
):
    records, _ = produce(monkeypatch, text, [group(text, *parts)])
    (record,) = records
    assert evidence(record, "predicate")[0][-1] == parts[1]
    assert_classification(record, "polarity", None)
    assert_classification(record, "modality", None)


@pytest.mark.parametrize("case", ["missing", "foreign-pin", "clipped", "synthetic"])
def test_unavailable_or_unmappable_retained_cues_stay_unresolved(tmp_path, case):
    text = "The pumps might drain the tanks."
    source_view = view(text)
    reader = owned_reader(source_view)
    source = native_source_frame(source_view, ())
    annotations, errors, _ = consume_annotations(
        reader, source_view, AnnotationProfile(config(tmp_path).sentences)
    )
    assert not errors and len(annotations) == 1
    (annotation,) = annotations
    pieces = (SourceSlice(source_view.ref.id, 0, len(text)),)
    if case == "missing":
        annotations = ()
    elif case == "foreign-pin":
        annotations = (
            replace(annotation, source=replace(annotation.source, projection_digest="0" * 64)),
        )
    else:
        middle = (
            (SyntheticText("might ", "controlled synthetic modal"),) if case == "synthetic" else ()
        )
        pieces = (
            SourceSlice(source_view.ref.id, 0, text.index("might")),
            *middle,
            SourceSlice(source_view.ref.id, text.index("drain"), len(text)),
        )
    context = NativeSourceContext(source, (), pieces, "assertion refusal control", "test", case)
    row = group(context.text, "The pumps", "drain", "the tanks")
    pack = configured_packs(reader.prepared, config(tmp_path))["assertion"]
    retained = report(context, pack, "assertion", [row])
    qualifier = AssertionQualification(source, annotations, source_view.pieces, source_view.items)
    supplement = qualifier.supplement(context, pack, retained, row)
    result = assemble_records(
        reader.prepared,
        context,
        pack,
        retained,
        contract="AssertionRecordFields",
        anchor_role="predicate",
        policy_version="test",
        occurrence_policy=OCCURRENCE_POLICY,
        supplements={0: supplement} if supplement else {},
    )
    (record,) = (record.model_dump(mode="python") for record in result.records)
    assert evidence(record, "predicate") == [("#/texts/1", 16, 21, "drain")]
    assert_classification(record, "polarity", None)
    assert_classification(record, "modality", None)


def test_literal_assertion_pack_refuses_decoder_classification(tmp_path):
    source_view = view("The pumps drain the tanks.")
    source = native_source_frame(source_view, ())
    context = NativeSourceContext(
        source,
        (),
        (SourceSlice(source_view.ref.id, 0, len(source_view.text)),),
        "classification injection control",
        "test",
        "entire native passage",
    )
    prepared = owned_reader(source_view).prepared
    pack = configured_packs(prepared, config(tmp_path))["assertion"]
    row = group(context.text, "The pumps", "drain", "the tanks")
    raw = report(context, pack, "assertion", [dict(row, polarity={"text": "positive"})])
    with pytest.raises(GlinerRefused, match="outside its released family pack"):
        assemble_records(
            prepared,
            context,
            pack,
            raw,
            contract="AssertionRecordFields",
            anchor_role="predicate",
            policy_version="test",
        )


def test_qualification_reads_primary_predication_without_recognition(tmp_path, monkeypatch):
    from corpus_structure.methods.annotation_rules import PreparedAnnotationRules
    from corpus_structure.semantic.constructions import retained_rules

    text = "The pumps might drain the tanks."
    source_view = view(text)
    reader = owned_reader(source_view)
    source = native_source_frame(source_view, ())
    annotations, errors, _ = consume_annotations(
        reader, source_view, AnnotationProfile(config(tmp_path).sentences)
    )
    assert annotations and not errors

    def unexpected(*_args, **_kwargs):
        pytest.fail("assertion consumer recognized source language")

    monkeypatch.setattr(retained_rules, "recognize_frames", unexpected)
    monkeypatch.setattr(retained_rules, "recognize_frame_result", unexpected)
    monkeypatch.setattr(PreparedAnnotationRules, "match", unexpected)
    context = NativeSourceContext(
        source,
        (),
        (SourceSlice(source_view.ref.id, 0, len(text)),),
        "assertion primary projection",
        "test",
        "complete selected source",
    )
    pack = configured_packs(reader.prepared, config(tmp_path))["assertion"]
    row = group(context.text, "The pumps", "drain", "the tanks")
    retained = report(context, pack, "assertion", [row])
    result = AssertionQualification(
        source, annotations, source_view.pieces, source_view.items
    ).supplement(context, pack, retained, row)
    assert result is not None
    assert {(field.role, field.label) for field in result.fields} == {
        ("polarity", "positive"),
        ("modality", "possible"),
    }
