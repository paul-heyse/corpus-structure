"""Independent source-reading graph and direct-custody expectations (pure scope)."""

from copy import deepcopy
from functools import cache
from pathlib import Path

import pytest
import yaml

from corpus_structure.semantic import PreparationProfile, ResolvedDependencies, SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.observations import observation_inputs
from corpus_structure.semantic.record_assertions import (
    lower_record_assertions,
    reading_identity,
    source_reading_inputs,
)
from corpus_structure.semantic.record_contracts import (
    anchor_identity,
    bind_record_candidates,
    evidence_set_identity,
    interpretation_identity,
    record_identity,
)

ROOT = Path(__file__).resolve().parents[4]
MODEL = ROOT / "python/corpus-structure/src/corpus_structure/model/semantic"
PIN = dict(source="source:reading", native_product_task_id=23, product_key="organized", product_digest="a" * 64, projection_digest="b" * 64, recipe_digest="c" * 64, source_view_id=7)


@cache
def inputs():
    original = observation_inputs(SourceBundle("statistics_semantic", (
        SourceArtifact("statistics_semantic", (ROOT / "domains/statistics/semantic.yaml").read_bytes()),
        SourceArtifact("semantic_core", (MODEL / "core.yaml").read_bytes()),
    )))
    bundle = source_reading_inputs(original)
    return original, bundle, prepare_release(bundle, composed_dependencies(ResolvedDependencies()), PreparationProfile(version="semantic-2"))


def record(contract="TableRecordFields", overrides=None):
    prepared = inputs()[2]
    fields, anchors, sets, texts = [], [], [], []
    for prop in prepared.index.definitions[contract].properties:
        if prop.name in {"family", "occurrence_recipe"}:
            continue
        field_type = prepared.index.definitions[prop.range]
        field_props = {p.name: p for p in field_type.properties}
        kind = field_props["kind"].equals_string or "normalized"
        role = prop.name
        anchor = dict(pin=dict(PIN), space="native", pointer="#/inspected/" + role, precision="item")
        value = dict(role=role, kind=kind, state="unstated", meaning_changing="MeaningChangingRecordField" in field_type.ancestors, evidence_status="available", reason="inspected role scope contains no stated value")
        usage = "context"
        if role in (overrides or {}):
            addition = deepcopy(overrides[role])
            source_pieces = addition.pop("pieces", None)
            value.update(addition)
            usage = {"literal": "literal", "classified": "classification_cue", "native": "native"}.get(value["kind"], "association")
            if source_pieces is not None:
                anchor.update(precision="exact", start=0, end=len(source_pieces), source_piece=source_pieces)
                texts.append(dict(pin=dict(PIN), space="native", pointer=anchor["pointer"], text=source_pieces))
        anchor["anchor_id"] = anchor_identity(anchor)
        anchors.append(anchor)
        evidence = dict(role=role, ordering="ordered", usage=usage, anchors=(anchor["anchor_id"],))
        evidence["set_id"] = evidence_set_identity(evidence)
        sets.append(evidence)
        value["evidence_sets"] = (evidence["set_id"],)
        fields.append(value)
    props = {p.name: p for p in prepared.index.definitions[contract].properties}
    row = dict(contract=contract, family=props["family"].equals_string, occurrence_recipe="source-anchor-membership-1", pin=dict(PIN), occurrence_anchors=(anchors[0]["anchor_id"],), standing="candidate", policy_version="reading-1", fields=tuple(fields), anchors=tuple(anchors), evidence_sets=tuple(sets))
    seal(row)
    # The independent fixture crosses the existing private semantic binder too.
    bind_record_candidates(prepared, source=PIN["source"], records=(row,), coordinate_texts=texts)
    return row


def seal(row):
    row["record_id"] = record_identity(inputs()[2].release_id, row)
    row["interpretation_id"] = interpretation_identity(row)


def report(*records):
    return dict(selected_task_id=41, origin_task_id=37, cut_id=13, source=PIN["source"], outcome="ok", records=records, source_uri="file:///retained.pdf", provider="m1-candidates", operation_version="4")


def lower(*records):
    return lower_record_assertions(inputs()[2], "realization:reading", "batch:reading", (report(*records),))


def test_derived_bundle_is_hashed_idempotent_and_has_only_ordinary_readings():
    _, bundle, prepared = inputs()
    assert source_reading_inputs(bundle) == bundle
    readings = {d.name for d in prepared.definitions if "SourceReading" in d.ancestors}
    assert readings == {"DefinitionReading", "QualifiedAssertionReading", "MeasurementReading", "TableAssertionReading", "FormulaContextReading"}
    for definition in prepared.definitions:
        if definition.name.startswith("SourceReading") or definition.name in readings:
            assert "SourceRecordProduct" not in definition.ancestors
            assert all(p.range not in {"RecordField", "RecordScalar"} for p in definition.properties)
    graph_value = prepared.index.definitions["SourceReadingLiteralValue"]
    assert not {"alternatives", "role", "evidence_sets"} & {p.name for p in graph_value.properties}
    assert prepared.index.definitions["SourceReadingDecimal"].properties[1].pattern is None


@pytest.mark.parametrize("contract,count", [("DefinitionRecordFields", 5), ("AssertionRecordFields", 9), ("MeasurementRecordFields", 10), ("TableRecordFields", 8), ("FormulaRecordFields", 6)])
def test_every_role_including_nonpresent_is_typed_and_uses_own_sealed_support(contract, count):
    row = record(contract)
    result = lower(row)
    assert result.diagnostics == ()
    assert len(result.batch.fact) == len(result.assertions) == count
    assert len(result.support) == count
    assert result.batch.selection == ()
    roles = {f["role"]: f for f in row["fields"]}
    sets = {s["set_id"]: s for s in row["evidence_sets"]}
    for support in result.support:
        assert support.origin_task_id == 37
        assert support.set_id in roles[support.role]["evidence_sets"]
        assert sets[support.set_id]["role"] == support.role
        assert support.anchor_id in sets[support.set_id]["anchors"]
    assert all(e.provider == "m1-candidates" and e.operation_version == "4" for e in result.batch.evidence)
    assert {a.reading_id for a in result.assertions} == {reading_identity(inputs()[2].release_id, row["record_id"], row["interpretation_id"])}


def test_literal_decimal_pieces_and_author_qualification_remain_reading_values():
    table = record(overrides={
        "cell_value": dict(state="present", kind="literal", value=dict(kind="decimal", lexical="+1.200e-03"), original="+1.200e-03", pieces="+1.200e-03"),
        "header_path": dict(state="present", kind="literal", value=dict(kind="text_sequence", items=("Population", "mean")), original_pieces=("Population", "mean"), pieces="Populationmean"),
    })
    assertion = record("AssertionRecordFields", overrides={
        "polarity": dict(state="present", kind="classified", value=dict(kind="assertion_polarity", label="negative")),
        "modality": dict(state="present", kind="classified", value=dict(kind="assertion_modality", label="possible")),
        "predicate": dict(state="present", kind="literal", value=dict(kind="text", text="causes"), original="causes", pieces="causes"),
    })
    result = lower(table, assertion)
    assert result.diagnostics == ()
    text_values = {value.text_value for value in result.batch.typed_value if value.kind == "string"}
    assert {"+1.200e-03", "Population", "mean", "negative", "possible", "causes", "asserted"} <= text_values
    assert len(result.batch.fact) == 17
    assert all("/QualifiedAssertionReading/" in f.property_id or "/TableAssertionReading/" in f.property_id for f in result.batch.fact)
    # Positive core qualification describes the field assertion, independent of author polarity.
    assert {v.boolean_value for v in result.batch.typed_value if v.kind == "boolean"} >= {True}
    assert result.batch.selection == ()


def test_no_half_record_on_missing_or_wrong_role_evidence_and_other_record_survives():
    damaged = record()
    fields = list(damaged["fields"])
    fields[0]["evidence_sets"] = fields[1]["evidence_sets"]
    seal(damaged)
    good = record("DefinitionRecordFields")
    result = lower(damaged, good)
    assert len(result.diagnostics) == 1
    assert "another role" in result.diagnostics[0].reason
    assert len(result.assertions) == 5
    assert {binding.record_id for binding in result.assertions} == {good["record_id"]}
    missing = record()
    missing["fields"][0].update(evidence_status="unavailable", evidence_sets=())
    seal(missing)
    result = lower(missing)
    assert len(result.diagnostics) == 1
    assert result.batch.fact == result.support == result.assertions == ()


def test_interpretations_and_occurrences_do_not_merge_by_text_and_missing_custody_refuses():
    first = record()
    alternative = deepcopy(first)
    alternative["fields"][0]["reason"] = "alternative unresolved scope"
    seal(alternative)
    result = lower(first, alternative)
    assert len({a.reading_id for a in result.assertions}) == 2
    assert len(result.batch.fact) == 16
    assert reading_identity("release:other", first["record_id"], first["interpretation_id"]) != result.assertions[0].reading_id
    incomplete_report = report(first)
    del incomplete_report["provider"]
    with pytest.raises(ValueError, match="actual producer"):
        lower_record_assertions(inputs()[2], "r", "b", (incomplete_report,))


def test_role_derivation_tracks_effective_declaration_and_refuses_tampering():
    original, _, _ = inputs()
    sources = list(original.sources)
    domain = yaml.safe_load(sources[0].content)
    domain["classes"]["DefinitionRecordFields"]["attributes"]["new_role"] = dict(range="LiteralRecordField", required=True, inlined=True)
    sources[0] = SourceArtifact(sources[0].name, yaml.safe_dump(domain).encode())
    updated = prepare_release(source_reading_inputs(SourceBundle(original.root, tuple(sources))))
    assert "new_role" in {p.name for p in updated.index.definitions["DefinitionReading"].properties}
    assert updated.release_id != inputs()[2].release_id
    bundle = inputs()[1]
    altered = tuple(SourceArtifact(s.name, s.content + b"\n# altered\n") if s.name == "source-readings" else s for s in bundle.sources)
    with pytest.raises(ValueError, match="differ"):
        source_reading_inputs(SourceBundle(bundle.root, altered))


@pytest.mark.parametrize("kind", ["normalized", "derived"])
def test_native_address_and_transformation_lineage_are_graph_values(kind):
    measurement = record("MeasurementRecordFields", overrides={
        "original_value": dict(state="present", kind="literal", value=dict(kind="decimal", lexical="12.00"), original="12.00", pieces="12.00"),
        "normalized_value": dict(state="present", kind=kind, value=dict(kind="decimal", lexical="0.1200"), original="12.00", policy="decimal-percent-1", rule="divide-by-100", premises=("original_value",)),
    })
    formula = record("FormulaRecordFields", overrides={
        "scope": dict(state="present", kind="native", value=dict(kind="native_location", pointer="#/inspected/scope")),
    })
    result = lower(measurement, formula)
    assert result.diagnostics == ()
    values = {v.text_value for v in result.batch.typed_value if v.kind == "string"}
    assert {"12.00", "0.1200", "decimal-percent-1", "divide-by-100", "original_value", "#/inspected/scope", kind} <= values
    assert result.batch.selection == ()
