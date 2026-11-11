"""Finite public record expectations; provider quality and native admission are separate."""

from collections.abc import MutableMapping
from copy import deepcopy
from dataclasses import replace
from operator import setitem
from typing import cast

import pytest

from corpus_structure.semantic.archive_reader import reconstruct_release
from corpus_structure.semantic.arrow_publication import AppendPublication
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.publication import PublicationBatch
from corpus_structure.semantic.record_contracts import interpretation_identity
from corpus_structure.semantic.record_projection import (
    ARTIFACT,
    CALIBRATION,
    RECORD_ROW_TYPES,
    index_record_projection,
    project_record_reports,
    read_record_projection,
    reconstruct_record,
)
from corpus_structure.semantic.releases import _products

from .test_record_contracts import (
    PIN,
    bind,
    finish,
    formula_record,
    measurement_record,
    record_from_fields,
    release_inputs,
    table_record,
)


def definition_record():
    return record_from_fields(
        "DefinitionRecordFields",
        "definition",
        (
            (
                "term",
                "literal",
                "#/texts/1",
                "native",
                "variable",
                {"kind": "text", "text": "variable"},
            ),
            (
                "defining_text",
                "literal",
                "#/texts/2",
                "native",
                "measurable map",
                {"kind": "text", "text": "measurable map"},
            ),
            (
                "scope",
                "native",
                "#/groups/1",
                "native",
                None,
                {"kind": "native_location", "pointer": "#/groups/1"},
            ),
        ),
        (("alias", "literal", False), ("relation_type", "classified", False)),
    )


def test_prepared_projection_reuses_rows_and_preserves_independent_records(monkeypatch):
    raw_table, table_contexts = table_record()
    raw_formula, formula_contexts = formula_record()
    for record in (raw_table, raw_formula):
        record["standing"] = "candidate"
        finish(record)
    table_model = bind(raw_table, table_contexts)
    formula_model = bind(raw_formula, formula_contexts)
    rows = project_record_reports(release_inputs()[2], (report((table_model, formula_model)),))
    index = index_record_projection(rows)

    def repeated_conversion(*args, **kwargs):
        raise AssertionError("a prepared projection must not convert detached rows again")

    monkeypatch.setattr("corpus_structure.semantic.record_projection.asdict", repeated_conversion)
    assert index_record_projection(index) is index
    for _ in range(2):
        for expected in (raw_table, raw_formula):
            actual = reconstruct_record(index, expected["record_id"], expected["interpretation_id"])
            assert canonical_bytes(actual) == canonical_bytes(expected)
    assert len(index.reports_by_task[71]) == 1
    assert len(index.members_by_task[71]) == 2
    with pytest.raises(TypeError):
        # Deliberately challenge runtime immutability beyond the read-only type interface.
        setitem(
            cast(
                MutableMapping[str, object],
                index.rows_for(
                    raw_table["record_id"], raw_table["interpretation_id"], "source_record"
                )[0],
            ),
            "standing",
            "accepted",
        )


def assertion_record():
    return record_from_fields(
        "AssertionRecordFields",
        "assertion",
        (
            ("subject", "literal", "#/texts/1", "native", "X", {"kind": "text", "text": "X"}),
            (
                "predicate",
                "literal",
                "#/texts/2",
                "native",
                "has mean",
                {"kind": "text", "text": "has mean"},
            ),
            ("object", "literal", "#/texts/3", "native", "0", {"kind": "decimal", "lexical": "0"}),
        ),
        tuple(
            (role, "classified" if role in {"polarity", "modality"} else "literal", True)
            for role in (
                "polarity",
                "modality",
                "attribution",
                "condition",
                "quantification",
                "scope",
            )
        ),
    )


def report(records, *, selected=71, origin=23):
    return dict(
        selected_task_id=selected,
        origin_task_id=origin,
        cut_id=19,
        source=PIN["source"],
        outcome="produced" if records else "empty",
        records=records,
    )


def candidate(factory):
    raw, coordinates = factory()
    raw["standing"] = "candidate"
    return bind(raw, coordinates)


@pytest.mark.parametrize(
    "factory,family",
    [
        (definition_record, "definition"),
        (assertion_record, "assertion"),
        (measurement_record, "measurement"),
        (table_record, "table"),
        (formula_record, "formula_context"),
    ],
)
def test_five_families_roundtrip_through_finite_arrow_transport(factory, family):
    prepared = release_inputs()[2]
    model = candidate(factory)
    original = model.model_dump(mode="python")
    rows = project_record_reports(prepared, (report((model,)),))
    batch = PublicationBatch(prepared.release_id, "record-result", "record-batch", **rows)
    arrow = AppendPublication.from_rows(batch)
    assert arrow.content == batch.content
    detached = {name: arrow.relations[name].to_pylist() for name in RECORD_ROW_TYPES}
    restored = reconstruct_record(
        detached,
        model.model_dump(mode="python")["record_id"],
        model.model_dump(mode="python")["interpretation_id"],
    )
    assert canonical_bytes(restored) == canonical_bytes(original)
    assert restored["family"] == family
    assert restored["record_id"] == original["record_id"]
    assert interpretation_identity(restored) == original["interpretation_id"]
    assert rows["record_report"][0].selected_task_id == 71
    assert rows["record_report"][0].origin_task_id == 23
    assert rows["record_report_member"][0].position == 0
    assert rows["record_admission"][0].decision == "candidate"
    assert rows["record_admission"][0].calibration == CALIBRATION
    assert rows["record_assertion"] == ()
    assert batch.membership == batch.typed_value == ()


def test_numeric_original_ordered_evidence_and_private_assertions_are_not_relabelled():
    prepared = release_inputs()[2]
    model = candidate(table_record)
    rows = project_record_reports(prepared, (report((model,)),))
    header = next(field for field in rows["record_field"] if field.role == "header_path")
    assert header.value_kind == "text_sequence"
    assert [
        (piece.position, piece.original_piece, piece.value_piece)
        for piece in rows["record_field_piece"]
        if piece.role == "header_path"
    ] == [(0, "Population", "Population"), (1, "mean", "mean")]
    assert (
        next(field for field in rows["record_field"] if field.role == "cell_value").decimal_lexical
        == "12"
    )
    assert [(a.position, a.assertion_ref) for a in rows["record_private_assertion"]] == [
        (0, "fact:value"),
        (1, "fact:condition"),
    ]
    assert any(
        a.precision == "item" and a.start is None and a.end is None for a in rows["record_anchor"]
    )
    assert rows["record_dependency"][0].dependency == "observation:rejected-header-alternative"
    tiny = candidate(measurement_record)
    projected = project_record_reports(prepared, (report((tiny,)),))
    value = next(field for field in projected["record_field"] if field.role == "original_value")
    assert value.decimal_lexical == "1.234567890123456789e-400"
    assert (
        next(
            field for field in projected["record_field"] if field.role == "value_role"
        ).classification
        == "mean"
    )


def test_alternatives_states_and_evidence_links_survive_without_acceptance():
    prepared = release_inputs()[2]
    raw, contexts = measurement_record()
    raw["standing"] = "unresolved"
    field = raw["fields"][2]
    field["alternatives"] = (
        {
            "alternative_id": "tiny-2",
            "value": {"kind": "decimal", "lexical": "2e-400"},
            "evidence_sets": field["evidence_sets"],
            "reason": "retained counterreading",
        },
    )
    raw["fields"][4].update(state="inapplicable", reason="dimensionless quantity")
    raw["fields"][5].update(state="unresolved", reason="countercandidate retained")
    finish(raw)
    model = bind(raw, contexts)
    rows = project_record_reports(prepared, (report((model,)),))
    restored = reconstruct_record(
        rows,
        model.model_dump(mode="python")["record_id"],
        model.model_dump(mode="python")["interpretation_id"],
    )
    assert canonical_bytes(restored) == canonical_bytes(raw)
    assert rows["record_alternative"][0].decimal_lexical == "2e-400"
    assert rows["record_alternative_evidence"][0].set_id == field["evidence_sets"][0]
    assert rows["record_admission"][0].decision == "unresolved"


def test_absent_and_completed_empty_are_distinct_and_keep_task_provenance():
    prepared = release_inputs()[2]
    rows = project_record_reports(prepared, (report(None), report((), selected=72, origin=24)))
    assert [r.records_present for r in rows["record_report"]] == [False, True]
    assert [r.selected_task_id for r in rows["record_report"]] == [71, 72]
    assert rows["source_record"] == rows["record_report_member"] == rows["record_admission"] == ()
    batch = PublicationBatch(prepared.release_id, "empty-result", "empty-batch", **rows)
    assert AppendPublication.from_rows(batch).content == batch.content


def test_reused_task_keeps_one_interpretation_and_both_selected_memberships():
    prepared = release_inputs()[2]
    model = candidate(table_record)
    rows = project_record_reports(prepared, (report((model,)), report((model,), selected=72)))
    assert len(rows["source_record"]) == 1
    assert [r.selected_task_id for r in rows["record_report_member"]] == [71, 72]
    assert len(rows["record_admission"]) == 1


def test_candidate_policy_refuses_every_accepted_record():
    prepared = release_inputs()[2]
    raw, contexts = table_record()
    accepted = bind(raw, contexts)
    with pytest.raises(ValueError, match="refuses accepted"):
        project_record_reports(prepared, (report((accepted,)),))


def test_same_identity_cannot_bind_different_fields():
    prepared = release_inputs()[2]
    model = candidate(table_record)
    forged = deepcopy(model.model_dump(mode="python"))
    forged["fields"][2]["reason"] = "changed outside identity"
    with pytest.raises(ValueError, match="conflicting immutable"):
        project_record_reports(prepared, (report((model, forged)),))


def test_explicit_iris_cross_preparation_and_archive_as_plain_text():
    from corpus_structure.semantic import (
        PreparationProfile,
        SourceArtifact,
        SourceBundle,
        prepare_release,
    )
    from corpus_structure.semantic.prepare import preview_schema

    bundle = SourceBundle(
        "explicit",
        (
            SourceArtifact(
                "explicit",
                b"""id: https://example.org/explicit
name: explicit
types:
  string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
classes:
  Explicit:
    class_uri: https://example.org/Explicit
    attributes:
      value:
        range: string
        slot_uri: https://example.org/value
""",
            ),
        ),
    )
    profile = PreparationProfile()
    prepared = prepare_release(bundle, profile=profile)
    (definition,) = prepared.definitions
    (prop,) = definition.properties
    assert type(definition.iri) is str and definition.iri == "https://example.org/Explicit"
    assert type(prop.iri) is str and prop.iri == "https://example.org/value"
    (query,) = prepared.queries
    assert type(query.class_iri) is str and query.class_iri == definition.iri
    (preview,) = preview_schema(bundle).classes
    assert type(preview.iri) is str and preview.iri == definition.iri
    assert type(preview.properties[0].iri) is str and preview.properties[0].iri == prop.iri
    reopened = reconstruct_release(
        _products(prepared), prepared.manifest, bundle, profile, prepared.artifacts
    )
    assert reopened.definitions == prepared.definitions
    assert reopened.queries == prepared.queries


def test_archive_projection_is_the_only_family_role_authority():
    bundle, profile, prepared = release_inputs()
    projection = read_record_projection(prepared)
    assert {family["family"] for family in projection["families"]} == {
        "definition",
        "assertion",
        "measurement",
        "table",
        "formula_context",
    }
    reopened = reconstruct_release(
        _products(prepared), prepared.manifest, bundle, profile, prepared.artifacts
    )
    assert read_record_projection(reopened) == projection
    absent = replace(prepared, artifacts=tuple(a for a in prepared.artifacts if a.kind != ARTIFACT))
    with pytest.raises(ValueError, match="no unique"):
        read_record_projection(absent)


@pytest.mark.parametrize("captured", [False, True])
def test_attributed_binding_and_recognition_coordinates_roundtrip(captured):
    from corpus_structure.semantic.record_contracts import anchor_identity, evidence_set_identity

    raw, contexts = table_record()
    raw["standing"] = "candidate"
    previous = next(a for a in raw["anchors"] if a["pointer"] == "#/texts/4")
    anchor = deepcopy(previous)
    anchor["binding"] = dict(
        version=2,
        relationship="primary" if captured else "selected_context",
        policy="attributed-selected-source-2",
    )
    if captured:
        import json

        anchor["space"] = "captured_recognition"
        anchor["recognition"] = dict(
            selected_occurrence_id="selected:4",
            task_id=12,
            product_key="recognition",
            content_digest="e" * 64,
            occurrence_id="provider:7",
            relation_id="decision:4",
            endpoint_role="evidence",
            relation_kind="decision",
            relation_outcome="selected",
            provider_occurrence_json=json.dumps(
                dict(
                    occurrence_id="provider:7",
                    kind="text",
                    precision="coarse",
                    address_space="submitted_pixels",
                    text="hypothetical",
                    region=dict(precision="coarse", left=0, right=80),
                )
            ),
            observation_json=json.dumps(
                dict(image=dict(precision="unknown"), raw_response_digest="f" * 64)
            ),
        )
    else:
        anchor["pin"] = dict(PIN, source="related-note", source_view_id=8, recipe_digest="d" * 64)
    anchor["anchor_id"] = anchor_identity(anchor)
    raw["anchors"] = tuple(anchor if a is previous else a for a in raw["anchors"])
    replacements = {}
    for evidence in raw["evidence_sets"]:
        old = evidence["set_id"]
        evidence["anchors"] = tuple(
            anchor["anchor_id"] if aid == previous["anchor_id"] else aid
            for aid in evidence["anchors"]
        )
        evidence["set_id"] = evidence_set_identity(evidence)
        replacements[old] = evidence["set_id"]
    for field in raw["fields"]:
        field["evidence_sets"] = tuple(replacements[sid] for sid in field["evidence_sets"])
    finish(raw)
    coordinate = dict(
        pin=anchor["pin"], space=anchor["space"], pointer=anchor["pointer"], text="hypothetical"
    )
    if captured:
        coordinate["recognition"] = anchor["recognition"]
    model = bind(raw, (*contexts, coordinate))
    rows = project_record_reports(release_inputs()[2], (report((model,)),))
    restored = reconstruct_record(
        rows,
        model.model_dump(mode="python")["record_id"],
        model.model_dump(mode="python")["interpretation_id"],
    )
    assert canonical_bytes(restored) == canonical_bytes(raw)
    projected = next(a for a in rows["record_anchor"] if a.pointer == "#/texts/4")
    assert projected.binding_relationship == anchor["binding"]["relationship"]
    if captured:
        assert projected.space == "captured_recognition"
        assert (
            projected.recognition_provider_occurrence_json
            == anchor["recognition"]["provider_occurrence_json"]
        )
        assert projected.recognition_observation_json == anchor["recognition"]["observation_json"]
    else:
        assert projected.source_view_id == 8
        assert restored["pin"]["source_view_id"] == 7


@pytest.mark.parametrize("kind", ["normalized", "derived"])
def test_transformation_policy_rule_and_premises_survive(kind):
    raw, contexts = measurement_record()
    raw["standing"] = "candidate"
    transformed = raw["fields"][-1]
    transformed.update(
        state="present",
        kind=kind,
        value=dict(kind="decimal", lexical="1.234567890123456789e-400"),
        policy="exact-unit-policy-2",
        reason="retained computation with unavailable direct evidence",
    )
    if kind == "normalized":
        transformed["original"] = "1.234567890123456789e-400"
    else:
        transformed.update(rule="dimensional-rule-1", premises=("original_value",))
    finish(raw)
    model = bind(raw, contexts)
    rows = project_record_reports(release_inputs()[2], (report((model,)),))
    restored = reconstruct_record(
        rows,
        model.model_dump(mode="python")["record_id"],
        model.model_dump(mode="python")["interpretation_id"],
    )
    assert canonical_bytes(restored) == canonical_bytes(raw)
    field = next(f for f in rows["record_field"] if f.role == "normalized_value")
    assert field.policy == "exact-unit-policy-2"
    if kind == "derived":
        assert field.rule == "dimensional-rule-1"
        assert [(p.role, p.position, p.premise_role) for p in rows["record_premise"]] == [
            ("normalized_value", 0, "original_value")
        ]
