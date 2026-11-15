"""Independent compatibility controls; these are not source/model quality evidence."""

from copy import deepcopy
from dataclasses import replace
from functools import cache
import yaml

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.data_operation_compilation import compile_data_operations

import pytest
from evaluation_record_references_support import fixture, prepared, model, bundle

from corpus_structure.evaluate.record_alignment import RecordSide, align_records, reference_contract
from corpus_structure.evaluate.record_alignment import whole_reading_correct
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.record_contracts import (
    anchor_identity,
    evidence_set_identity,
    interpretation_identity,
    record_identity,
    record_family_contract,
)


@cache
def successor_preparation(change="unrelated"):
    """Prepare actual closed counterfactual sources; never alias a release identity."""
    original = bundle()
    sources = list(original.sources)
    if change in {"schema", "semantics", "vocabulary"}:
        name = "observations" if change in {"schema", "vocabulary"} else "statistics_semantic"
        position = next(index for index, source in enumerate(sources) if source.name == name)
        document = yaml.safe_load(sources[position].content)
        if change == "schema":
            document["classes"]["SourceRecord"]["attributes"]["new_meaning"] = {"range": "string", "required": True}
        elif change == "vocabulary":
            document["enums"]["RecordEvidenceOrdering"]["permissible_values"]["ordered"]["description"] = "changed authored ordering meaning"
        else:
            document["classes"]["MeasurementRecordFields"]["attributes"]["unit"]["required"] = True
        sources[position] = SourceArtifact(name, yaml.safe_dump(document).encode())
    root_name = "counterfactual_record_reference_root"
    root = SourceArtifact(root_name, yaml.safe_dump({
        "id": "urn:corpus:counterfactual-record-reference", "name": root_name,
        "imports": [original.root],
        "classes": {"UnrelatedGradeDiagnostics": {"attributes": {"summary": {"range": "string"},
                     **({"review_note": {"range": "string"}} if change == "output" else {})}}},
    }).encode())
    actual = SourceBundle(root_name, (*sources, root))
    return prepare_release(actual), compile_data_operations(actual)


def successor_reading(reference, contexts, binding):
    """An independently validated prediction fixture with distinct release/alias IDs."""
    target, target_model = successor_preparation()
    pin = dict(binding.pin, source="source:actual-successor", source_view_id=73)
    prediction = deepcopy(reference)
    prediction["pin"] = pin
    anchors = {}
    for anchor in prediction["anchors"]:
        before = anchor["anchor_id"]
        anchor["pin"] = pin
        anchor["anchor_id"] = anchor_identity(anchor)
        anchors[before] = anchor["anchor_id"]
    sets = {}
    for evidence in prediction["evidence_sets"]:
        before = evidence["set_id"]
        evidence["anchors"] = tuple(anchors[value] for value in evidence["anchors"])
        evidence["set_id"] = evidence_set_identity(evidence)
        sets[before] = evidence["set_id"]
    prediction["occurrence_anchors"] = tuple(
        anchors[value] for value in prediction["occurrence_anchors"]
    )
    for value in prediction["fields"]:
        value["evidence_sets"] = tuple(sets[identity] for identity in value["evidence_sets"])
    prediction["record_id"] = record_identity(record_family_contract(target_model, prediction["contract"]), prediction)
    prediction["interpretation_id"] = interpretation_identity(prediction)
    # The original opaque IDs remain the cut authority, not an invented translated
    # inventory. Membership derives a counterpart ID from each actual descriptor.
    target_frame = replace(binding, release_id=target.release_id, pin=pin)
    target_contexts = [dict(value, pin=pin) for value in contexts]
    correspondence = [
        {"reference_pin": dict(binding.pin), "prediction_pin": pin, "physical_digest": "d" * 64}
    ]
    return target, prediction, target_frame, target_contexts, correspondence, target_model


@pytest.mark.parametrize(
    "family", ["definition", "assertion", "measurement", "table", "formula_context"]
)
def test_successor_compares_physical_occurrences_without_rebinding_original_ids(family):
    reference, contexts, binding = fixture(family)
    before = canonical_bytes(reference)
    target, prediction, target_frame, target_contexts, correspondence, target_model = successor_reading(
        reference, contexts, binding
    )
    assert prediction["record_id"] != reference["record_id"]
    result = align_records(
        RecordSide(binding, (reference,)),
        RecordSide(target_frame, (prediction,)),
        prepared(),
        coordinate_texts=contexts,
        prediction_prepared=target,
        prediction_coordinate_texts=target_contexts,
        correspondence=correspondence,
    model = model(), prediction_model = target_model)
    assert result.matches == {
        tier: [reference["record_id"]] for tier in ("core", "full", "evidence")
    }
    assert result.release_id == target.release_id
    assert result.reference_release_id == prepared().release_id
    assert result.match_bindings == [
        {
            "reference_record_id": reference["record_id"],
            "reference_interpretation_id": reference["interpretation_id"],
            "prediction_record_id": prediction["record_id"],
            "prediction_interpretation_id": prediction["interpretation_id"],
            "tiers": ["core", "full", "evidence"],
        }
    ]
    assert canonical_bytes(reference) == before
    if family == "table":
        assert next(value for value in prediction["fields"] if value["role"] == "header_path")[
            "original_pieces"
        ] == ("Population", "mean")
    prediction["standing"] = "candidate"
    assert whole_reading_correct(
        target,
        prediction,
        (reference,),
        binding,
        coordinate_texts=contexts,
        reference_prepared=prepared(),
        prediction_frame=target_frame,
        prediction_coordinate_texts=target_contexts,
        correspondence=correspondence,
    reference_model = model(), prediction_model = target_model)
    assert prediction["standing"] == "candidate"


def test_cross_release_opaque_allowlist_checks_actual_descriptor_not_reference_record_coverage():
    reference, contexts, binding = fixture()
    target, prediction, target_frame, target_contexts, correspondence, target_model = successor_reading(
        reference, contexts, binding
    )
    # A cut may permit an additional source anchor that no expected record used.
    allowed = deepcopy(reference["anchors"][0])
    allowed["pointer"] = "#/unmentioned-source-item"
    allowed["anchor_id"] = anchor_identity(allowed)
    binding = replace(binding, anchor_ids=binding.anchor_ids | {allowed["anchor_id"]})
    actual = deepcopy(allowed)
    actual["pin"] = dict(target_frame.pin)
    actual["anchor_id"] = anchor_identity(actual)
    prediction["anchors"] = (*prediction["anchors"], actual)
    prediction["interpretation_id"] = interpretation_identity(prediction)
    target_contexts.append(
        dict(
            pin=actual["pin"],
            space=actual["space"],
            pointer=actual["pointer"],
            text=actual["source_piece"],
        )
    )
    target_frame = replace(target_frame, anchor_ids=binding.anchor_ids)
    result = align_records(
        RecordSide(binding, (reference,)),
        RecordSide(target_frame, (prediction,)),
        prepared(),
        coordinate_texts=contexts,
        prediction_prepared=target,
        prediction_coordinate_texts=target_contexts,
        correspondence=correspondence,
    model = model(), prediction_model = target_model)
    assert result.counts["full"].matched == 1
    with pytest.raises(ValueError, match="outside the explicit evaluation cut"):
        align_records(
            RecordSide(
                replace(binding, anchor_ids=binding.anchor_ids - {allowed["anchor_id"]}),
                (reference,),
            ),
            RecordSide(target_frame, (prediction,)),
            prepared(),
            coordinate_texts=contexts,
            prediction_prepared=target,
            prediction_coordinate_texts=target_contexts,
            correspondence=correspondence,
        model = model(), prediction_model = target_model)


@pytest.mark.parametrize(
    "change", ["source", "scope", "guideline", "policy", "schema", "semantics", "bijection"]
)
def test_changed_source_or_consumed_contract_refuses_instead_of_false_misses(change):
    reference, contexts, binding = fixture()
    target, prediction, target_frame, target_contexts, correspondence, target_model = successor_reading(
        reference, contexts, binding
    )
    if change == "source":
        correspondence[0]["prediction_pin"] = dict(target_frame.pin, product_digest="e" * 64)
    elif change == "scope":
        target_frame = replace(
            target_frame,
            anchor_scopes=(
                {
                    "pin": dict(target_frame.pin),
                    "space": "native",
                    "pointer": "#/foreign",
                    "precision": "item",
                },
            ),
        )
    elif change == "guideline":
        target_frame = replace(target_frame, guideline_version="changed-guideline")
    elif change == "policy":
        target_frame = replace(target_frame, prediction_policy_version="changed-policy")
    elif change in {"schema", "semantics", "vocabulary"}:
        target, target_model = successor_preparation(change)
        target_frame = replace(target_frame, release_id=target.release_id)
    else:
        correspondence.append(deepcopy(correspondence[0]))
    with pytest.raises(ValueError):
        align_records(
            RecordSide(binding, (reference,)),
            RecordSide(target_frame, (prediction,)),
            prepared(),
            coordinate_texts=contexts,
            prediction_prepared=target,
            prediction_coordinate_texts=target_contexts,
            correspondence=correspondence,
        model = model(), prediction_model = target_model)


def test_report_schema_is_not_an_authored_source_premise_and_empty_units_survive():
    reference, contexts, binding = fixture()
    target, _, target_frame, target_contexts, correspondence, target_model = successor_reading(
        reference, contexts, binding
    )
    target, target_model = successor_preparation("output")
    target_frame = replace(target_frame, release_id=target.release_id)
    assert reference_contract(prepared()) == reference_contract(target)
    result = align_records(
        RecordSide(binding, (reference,)),
        RecordSide(target_frame),
        prepared(),
        coordinate_texts=contexts,
        prediction_prepared=target,
        prediction_coordinate_texts=target_contexts,
        correspondence=correspondence,
    model = model(), prediction_model = target_model)
    assert (
        result.counts["full"].reference,
        result.counts["full"].prediction,
        result.counts["full"].matched,
    ) == (1, 0, 0)


def test_successor_changed_prediction_policy_with_recomputed_identity_refuses():
    reference, contexts, binding = fixture()
    target, prediction, target_frame, target_contexts, correspondence, target_model = successor_reading(
        reference, contexts, binding
    )
    prediction["standing"] = "candidate"
    prediction["policy_version"] = "another-well-formed-policy"
    prediction["interpretation_id"] = interpretation_identity(prediction)
    with pytest.raises(ValueError, match="policy differs from its evaluation binding"):
        whole_reading_correct(
            target,
            prediction,
            (reference,),
            binding,
            coordinate_texts=contexts,
            reference_prepared=prepared(),
            prediction_frame=target_frame,
            prediction_coordinate_texts=target_contexts,
            correspondence=correspondence,
        reference_model = model(), prediction_model = target_model)


def test_unrelated_release_does_not_resalt_the_original_source_occurrence():
    reference, _, _ = fixture()
    target, target_model = successor_preparation()
    assert target.release_id != prepared().release_id
    assert record_family_contract(model(), reference["contract"]) == record_family_contract(target_model, reference["contract"])
    assert record_identity(record_family_contract(target_model, reference["contract"]), reference) == reference["record_id"]


def test_consumed_vocabulary_meaning_changes_source_reference_contract():
    reference, contexts, binding = fixture()
    target, target_model = successor_preparation("vocabulary")
    assert reference_contract(prepared()) != reference_contract(target)
    prediction_frame = replace(binding, release_id=target.release_id)
    with pytest.raises(ValueError, match="source reading declarations differ"):
        align_records(RecordSide(binding, (reference,)), RecordSide(prediction_frame), prepared(),
                      model=model(), prediction_model=target_model, prediction_prepared=target,
                      coordinate_texts=contexts, prediction_coordinate_texts=contexts,
                      correspondence=[{"reference_pin": dict(binding.pin), "prediction_pin": dict(binding.pin), "physical_digest": "d" * 64}])
