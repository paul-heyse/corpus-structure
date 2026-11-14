"""Independent compatibility controls; these are not source/model quality evidence."""

import json
from copy import deepcopy
from dataclasses import replace

import pytest
from evaluation_record_references_support import fixture, prepared
from pglast import parse_sql

from corpus_structure.evaluate.record_alignment import RecordSide, align_records, reference_contract
from corpus_structure.evaluate.record_policy import whole_reading_correct
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.record_contracts import (
    anchor_identity,
    evidence_set_identity,
    interpretation_identity,
    record_identity,
)


def successor_reading(reference, contexts, binding):
    """An independently validated prediction fixture with distinct release/alias IDs."""
    target = replace(prepared(), release_id="release:" + "9" * 64)
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
    prediction["record_id"] = record_identity(target.release_id, prediction)
    prediction["interpretation_id"] = interpretation_identity(prediction)
    # The original opaque IDs remain the cut authority, not an invented translated
    # inventory. Membership derives a counterpart ID from each actual descriptor.
    target_frame = replace(binding, release_id=target.release_id, pin=pin)
    target_contexts = [dict(value, pin=pin) for value in contexts]
    correspondence = [
        {"reference_pin": dict(binding.pin), "prediction_pin": pin, "physical_digest": "d" * 64}
    ]
    return target, prediction, target_frame, target_contexts, correspondence


@pytest.mark.parametrize(
    "family", ["definition", "assertion", "measurement", "table", "formula_context"]
)
def test_successor_compares_physical_occurrences_without_rebinding_original_ids(family):
    reference, contexts, binding = fixture(family)
    before = canonical_bytes(reference)
    target, prediction, target_frame, target_contexts, correspondence = successor_reading(
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
    )
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
    )
    assert prediction["standing"] == "candidate"


def test_cross_release_opaque_allowlist_checks_actual_descriptor_not_reference_record_coverage():
    reference, contexts, binding = fixture()
    target, prediction, target_frame, target_contexts, correspondence = successor_reading(
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
    )
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
        )


@pytest.mark.parametrize(
    "change", ["source", "scope", "guideline", "policy", "schema", "semantics", "bijection"]
)
def test_changed_source_or_consumed_contract_refuses_instead_of_false_misses(change):
    reference, contexts, binding = fixture()
    target, prediction, target_frame, target_contexts, correspondence = successor_reading(
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
    elif change == "schema":
        artifact = next(
            value for value in target.artifacts if value.kind == "json_schema/SourceRecord"
        )
        schema = json.loads(artifact.content)
        schema["required"] = [*schema["required"], "new-meaning"]
        target = replace(
            target,
            artifacts=tuple(
                replace(value, content=canonical_bytes(schema)) if value is artifact else value
                for value in target.artifacts
            ),
        )
    elif change == "semantics":
        definition = next(value for value in target.definitions if value.name == "RecordSourcePin")
        prop = definition.properties[0]
        changed = replace(
            definition,
            properties=(replace(prop, case_policy="changed"), *definition.properties[1:]),
        )
        target = replace(
            target,
            definitions=tuple(
                changed if value is definition else value for value in target.definitions
            ),
        )
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
        )


def test_report_schema_is_not_an_authored_source_premise_and_empty_units_survive():
    reference, contexts, binding = fixture()
    target, _, target_frame, target_contexts, correspondence = successor_reading(
        reference, contexts, binding
    )
    target = replace(
        target,
        artifacts=tuple(
            replace(value, content=b"{}")
            if value.kind == "json_schema/ReferenceRecordEvaluationReport"
            else value
            for value in target.artifacts
        ),
    )
    assert reference_contract(prepared()) == reference_contract(target)
    result = align_records(
        RecordSide(binding, (reference,)),
        RecordSide(target_frame),
        prepared(),
        coordinate_texts=contexts,
        prediction_prepared=target,
        prediction_coordinate_texts=target_contexts,
        correspondence=correspondence,
    )
    assert (
        result.counts["full"].reference,
        result.counts["full"].prediction,
        result.counts["full"].matched,
    ) == (1, 0, 0)


def test_native_reference_and_policy_sql_outer_syntax():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "src/corpus_structure/semantic/sql"
    for name in ("record_references.sql", "record_policy.sql"):
        assert parse_sql((root / name).read_text())


def test_successor_changed_prediction_policy_with_recomputed_identity_refuses():
    reference, contexts, binding = fixture()
    target, prediction, target_frame, target_contexts, correspondence = successor_reading(
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
        )
