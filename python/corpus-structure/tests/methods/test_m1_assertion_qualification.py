"""Assertion qualification from retained source columns with a controlled decoder."""

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.methods.assertion_qualification import AssertionQualification
from corpus_structure.methods.gliner import GlinerRefused
from corpus_structure.methods.m1_source import configured_packs
from corpus_structure.methods.record_assembly import OCCURRENCE_POLICY, assemble_records
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.m1_products import NativeCandidateData
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext,
    PreparedNativeSources,
    SyntheticText,
    source_slice,
)
from methods.declared_primary_fixture import selected_source, source_readings
from methods.domain_configuration import candidate_configuration
from methods.m1_producer_support import (
    ROOT,
    ControlledDecoder,
    candidate_fixture_product,
    detail_object,
    detail_objects,
)
from methods.m1_source_profile_support import config
from methods.record_assembly_support import model as record_model
from methods.record_assembly_support import release as record_release
from methods.record_assembly_support import report, span


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
    from corpus_structure.methods.source_preparation import prepare_source
    from corpus_structure.semantic.declared_contexts import DeclaredContextPopulation

    cfg = candidate_configuration(ROOT / "domains/statistics", "default")
    frame, annotations, primary, native = source_readings(
        text, AnnotationProfile(cfg.sentences), heading=heading
    )
    data = NativeCandidateData.from_frame(frame)
    population = DeclaredContextPopulation(
        (frame,),
        canonical_bytes(
            dict(
                identity="unadmitted:complete-original-context",
                complete=True,
                members=[frame.pin.values()["source_member"]],
                evidence={"literal": "pure source"},
            )
        ),
    )
    prepared_source = prepare_source(
        data,
        source_frame=frame,
        context_population=population,
        profile=AnnotationProfile(cfg.sentences, execution_profile=native.value.execution_profile),
        persisted_annotations=annotations,
        max_chars=cfg.max_context_chars,
        max_pieces=cfg.max_context_pieces,
        max_annotation_chars=cfg.max_annotation_chars,
        policy=cfg.policy,
        formula_prose=cfg.formula_prose,
        region_pointers=cfg.region_pointers,
    )
    result = candidate_fixture_product(
        dict(
            prepared=record_release(),
            model=record_model(),
            view=data,
            prepared_source=prepared_source,
            annotation_result={"semantic_product": native.semantic_id},
            primary_products=primary,
            cfg=cfg,
            check_active=lambda: None,
        ),
        AssertionDecoder(text, groups),
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
    source, annotations, primary, _native = source_readings(
        text, AnnotationProfile(config(tmp_path).sentences)
    )
    assert len(annotations) == 1
    (annotation,) = annotations
    data = NativeCandidateData.from_frame(source)
    pieces = (source_slice(source, 0, len(text)),)
    if case == "missing":
        annotations = ()
    elif case == "foreign-pin":
        annotations = (
            replace(
                annotation,
                source=replace(
                    annotation.source,
                    content=canonical_bytes(
                        {**annotation.source.values(), "projection_digest": "0" * 64}
                    ).decode(),
                ),
            ),
        )
    else:
        middle = (
            (SyntheticText("might ", "controlled synthetic modal"),) if case == "synthetic" else ()
        )
        pieces = (
            source_slice(source, 0, text.index("might")),
            *middle,
            source_slice(source, text.index("drain"), len(text)),
        )
    context = NativeSourceContext(
        source,
        (),
        pieces,
        "assertion refusal control",
        "test",
        case,
        version=2,
        preparation=PreparedNativeSources((source,)),
    )
    row = group(context.text, "The pumps", "drain", "the tanks")
    pack = configured_packs(record_release(), config(tmp_path))["assertion"]
    retained = report(context, pack, "assertion", [row])
    qualifier = AssertionQualification(
        source, annotations, data.pieces, data.items, primary_products=primary
    )
    supplement = qualifier.supplement(context, pack, retained, row)
    result = assemble_records(
        record_release(),
        context,
        pack,
        retained,
        contract="AssertionRecordFields",
        anchor_role="predicate",
        policy_version="test",
        occurrence_policy=OCCURRENCE_POLICY,
        supplements={0: supplement} if supplement else {},
        model=record_model(),
    )
    (record,) = (record.model_dump(mode="python") for record in result.records)
    assert evidence(record, "predicate") == [("#/texts/1", 16, 21, "drain")]
    assert_classification(record, "polarity", None)
    assert_classification(record, "modality", None)


def test_literal_assertion_pack_refuses_decoder_classification(tmp_path):
    _selected, source, _context = selected_source("The pumps drain the tanks.")
    context = NativeSourceContext(
        source,
        (),
        (source_slice(source, 0, len(source.text)),),
        "classification injection control",
        "test",
        "entire native passage",
        version=2,
        preparation=PreparedNativeSources((source,)),
    )
    prepared = record_release()
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
            model=record_model(),
        )


def test_qualification_reads_primary_predication_without_recognition(tmp_path, monkeypatch):
    from corpus_structure.methods.annotation_rules import PreparedAnnotationRules
    from corpus_structure.semantic.constructions import retained_rules

    text = "The pumps might drain the tanks."
    source, annotations, primary, _native = source_readings(
        text, AnnotationProfile(config(tmp_path).sentences)
    )
    data = NativeCandidateData.from_frame(source)
    assert annotations

    def unexpected(*_args, **_kwargs):
        pytest.fail("assertion consumer recognized source language")

    monkeypatch.setattr(retained_rules, "recognize_frames", unexpected)
    monkeypatch.setattr(retained_rules, "recognize_frame_result", unexpected)
    monkeypatch.setattr(PreparedAnnotationRules, "match", unexpected)
    context = NativeSourceContext(
        source,
        (),
        (source_slice(source, 0, len(text)),),
        "assertion primary projection",
        "test",
        "complete selected source",
        version=2,
        preparation=PreparedNativeSources((source,)),
    )
    pack = configured_packs(record_release(), config(tmp_path))["assertion"]
    row = group(context.text, "The pumps", "drain", "the tanks")
    retained = report(context, pack, "assertion", [row])
    result = AssertionQualification(
        source, annotations, data.pieces, data.items, primary_products=primary
    ).supplement(context, pack, retained, row)
    assert result is not None
    assert {(field.role, field.label) for field in result.fields} == {
        ("polarity", "positive"),
        ("modality", "possible"),
    }


def test_missing_primary_layout_is_unknown():
    from corpus_structure.methods.predicate_frames import source_layout

    assert source_layout(SimpleNamespace(), "arbitrary source", (), {}) == "unknown"


@pytest.mark.parametrize(
    ("missing", "text", "expected"),
    [
        ("TAG", "The pumps might drain the tanks.", {("polarity", "positive")}),
        ("MORPH", "The pumps drain the tanks.", set()),
        ("MORPH", "The pumps do not drain the tanks.", {("polarity", "negative")}),
    ],
)
def test_missing_cue_columns_withhold_only_unsupported_conclusions(
    tmp_path, missing, text, expected
):
    def withhold(product):
        return replace(
            product,
            availability=tuple(
                replace(row, status="absent") if row.attribute == missing else row
                for row in product.availability
            ),
        )

    source, annotations, primary, _native = source_readings(
        text, AnnotationProfile(config(tmp_path).sentences), change=withhold
    )
    data = NativeCandidateData.from_frame(source)
    coverage = next(
        row
        for product in primary
        for row in product.value.coverage
        if row.family == "construction.source_readings"
    )
    assert coverage.outcome == "complete"
    context = NativeSourceContext(
        source,
        (),
        (source_slice(source, 0, len(text)),),
        "partial cue examination",
        "test",
        "exact source",
        version=2,
        preparation=PreparedNativeSources((source,)),
    )
    pack = configured_packs(record_release(), config(tmp_path))["assertion"]
    row = group(context.text, "The pumps", "drain", "the tanks")
    retained = report(context, pack, "assertion", [row])
    result = AssertionQualification(
        source, annotations, data.pieces, data.items, primary_products=primary
    ).supplement(context, pack, retained, row)
    assert ({(field.role, field.label) for field in result.fields} if result else set()) == expected
