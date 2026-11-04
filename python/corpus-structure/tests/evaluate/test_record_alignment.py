"""Independent source readings/counts for the private strict record scorer.

These miniature authored source coordinates are fixtures, not an actual gold population.
Production validation checks supplied coordinates; expected readings/counts below do not
come from production assembly, alignment, validators, or family-schema enumeration.
"""

from copy import deepcopy
from dataclasses import replace
from functools import cache
from pathlib import Path
from typing import Any

import pytest
import yaml

from corpus_structure.evaluate.record_alignment import (
    RecordEvaluationFrame,
    RecordSide,
    align_records,
)
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.observations import observation_inputs
from corpus_structure.semantic.record_contracts import (
    anchor_identity,
    bind_record_candidates,
    evidence_set_identity,
    interpretation_identity,
    record_identity,
)

ROOT = Path(__file__).resolve().parents[4]
MODEL = ROOT / "python/corpus-structure/src/corpus_structure/model/semantic"
PIN = {
    "source": "source:independent-fixture",
    "native_product_task_id": 23,
    "product_key": "organized",
    "product_digest": "a" * 64,
    "projection_digest": "b" * 64,
    "recipe_digest": "c" * 64,
    "source_view_id": 7,
}


@cache
def prepared():
    return prepare_release(
        observation_inputs(
            SourceBundle(
                "statistics_semantic",
                (
                    SourceArtifact(
                        "statistics_semantic",
                        (ROOT / "domains/statistics/semantic.yaml").read_bytes(),
                    ),
                    SourceArtifact("semantic_core", (MODEL / "core.yaml").read_bytes()),
                ),
            )
        )
    )


def literal(role, text, *, meaning=True, decimal=False):
    if isinstance(text, tuple):
        value = {"kind": "text_sequence", "items": text}
    else:
        value = {"kind": "decimal", "lexical": text} if decimal else {"kind": "text", "text": text}
    return role, "literal", value, text, meaning


def native(role, pointer):
    return role, "native", {"kind": "native_location", "pointer": pointer}, None, True


def classified(role, kind, label, cue):
    return role, "classified", {"kind": kind, "label": label}, cue, True


def absent(role, *, kind="literal", meaning=True):
    return role, kind, None, None, meaning


def specifications(family):
    # Explicit expected source readings. No family shape is inferred from the release.
    return {
        "definition": (
            "DefinitionRecordFields",
            (
                literal("term", "variance"),
                literal("defining_text", "expected squared deviation"),
                native("scope", "#/sections/0"),
                absent("alias", meaning=False),
                absent("relation_type", kind="classified", meaning=False),
            ),
        ),
        "assertion": (
            "AssertionRecordFields",
            (
                literal("subject", "sample mean"),
                literal("predicate", "estimates"),
                literal("object", "population mean"),
                classified("polarity", "assertion_polarity", "positive", "does"),
                classified("modality", "assertion_modality", "asserted", "estimates"),
                absent("attribution"),
                literal("condition", "independent observations"),
                absent("quantification"),
                absent("scope"),
            ),
        ),
        "measurement": (
            "MeasurementRecordFields",
            (
                literal("referent", "bottle"),
                literal("property", "volume"),
                literal("original_value", "1.234567890123456789e-400", decimal=True),
                classified("value_role", "measurement_value_role", "mean", "average"),
                literal("unit", "litres"),
                absent("comparator"),
                absent("uncertainty"),
                absent("reference_quantity"),
                literal("condition", "at 20°C"),
                absent("normalized_value", kind="normalized", meaning=False),
            ),
        ),
        "table": (
            "TableRecordFields",
            (
                native("table", "#/tables/0"),
                native("cell", "#/tables/0/cells/3"),
                literal("row_label", "Group A"),
                literal("header_path", ("Population", "mean")),
                literal("cell_value", "12", decimal=True),
                literal("unit", "cm"),
                literal("note", "hypothetical"),
                absent("caption"),
            ),
        ),
        "formula_context": (
            "FormulaRecordFields",
            (
                literal("formula", "f(x)=x²"),
                native("scope", "#/sections/1"),
                literal("symbol", "x"),
                literal("meaning", "input value"),
                literal("domain", "real"),
                absent("assumption"),
            ),
        ),
    }[family]


def finish(row):
    for name in ("fields", "anchors", "evidence_sets"):
        row[name] = tuple(row[name])
    row["record_id"] = record_identity(prepared().release_id, row)
    row["interpretation_id"] = interpretation_identity(row)
    return row


def reading(family):
    contract, specs = specifications(family)
    anchors, sets, fields, contexts = [], [], [], []
    for role, kind, value, original, meaning in specs:
        field: dict[str, Any] = {
            "role": role,
            "kind": kind,
            "state": "present" if value is not None else "unstated",
            "meaning_changing": meaning,
            "evidence_status": "available" if value is not None else "unavailable",
            "evidence_sets": (),
        }
        if value is None:
            field["reason"] = "not stated in this independently authored source fixture"
        else:
            field["value"] = value
            parts = original if isinstance(original, tuple) else (original,)
            members = []
            for i, text in enumerate(parts):
                pointer = value["pointer"] if kind == "native" else f"#/{family}/{role}/{i}"
                space = "recognized_text" if role == "formula" else "native"
                anchor = {
                    "pin": dict(PIN),
                    "space": space,
                    "pointer": pointer,
                    "precision": "item" if text is None else "exact",
                }
                if text is not None:
                    anchor.update(start=0, end=len(text), source_piece=text)
                    contexts.append(
                        {"pin": dict(PIN), "space": space, "pointer": pointer, "text": text}
                    )
                anchor["anchor_id"] = anchor_identity(anchor)
                anchors.append(anchor)
                members.append(anchor["anchor_id"])
            evidence = {
                "role": role,
                "ordering": "ordered",
                "usage": "classification_cue" if kind == "classified" else kind,
                "anchors": tuple(members),
            }
            evidence["set_id"] = evidence_set_identity(evidence)
            sets.append(evidence)
            field["evidence_sets"] = (evidence["set_id"],)
            if kind == "literal":
                field["original_pieces" if isinstance(original, tuple) else "original"] = original
        fields.append(field)
    occurrence = anchors[1] if family == "table" else anchors[0]
    return finish(
        {
            "contract": contract,
            "family": family,
            "occurrence_recipe": "source-anchor-membership-1",
            "pin": dict(PIN),
            "occurrence_anchors": (occurrence["anchor_id"],),
            "standing": "accepted",
            "policy_version": "reference-acceptance-1",
            "fields": fields,
            "anchors": anchors,
            "evidence_sets": sets,
        }
    ), contexts


def frame(*records):
    return RecordEvaluationFrame(
        unit="chapter-1#region-2",
        release_id=prepared().release_id,
        guideline_version="independent-reading-guideline-1",
        reference_policy_version="reference-acceptance-1",
        prediction_policy_version="reference-acceptance-1",
        pin=dict(PIN),
        anchor_ids=frozenset(anchor["anchor_id"] for row in records for anchor in row["anchors"]),
    )


def score(reference, prediction, contexts, *, binding=None):
    binding = binding or frame(*reference, *prediction)
    return align_records(
        RecordSide(binding, reference),
        RecordSide(binding, prediction),
        prepared(),
        coordinate_texts=contexts,
    )


def role(row, name):
    return next(field for field in row["fields"] if field["role"] == name)


def replace_evidence(row, name, *, pointer=None, text=None, precision=None, space=None):
    """Change actual source evidence and identities, without changing the reading."""
    field = role(row, name)
    evidence = next(
        item for item in row["evidence_sets"] if item["set_id"] in field["evidence_sets"]
    )
    old = evidence["anchors"][0]
    anchor = next(item for item in row["anchors"] if item["anchor_id"] == old)
    if pointer is not None:
        anchor["pointer"] = pointer
    if text is not None:
        anchor.update(source_piece=text, start=0, end=len(text))
    if precision is not None:
        anchor["precision"] = precision
        if precision != "exact":
            anchor.pop("start", None)
            anchor.pop("end", None)
    if space is not None:
        anchor["space"] = space
    anchor["anchor_id"] = anchor_identity(anchor)
    row["occurrence_anchors"] = tuple(
        anchor["anchor_id"] if item == old else item for item in row["occurrence_anchors"]
    )
    evidence["anchors"] = (anchor["anchor_id"], *evidence["anchors"][1:])
    evidence["set_id"] = evidence_set_identity(evidence)
    field["evidence_sets"] = (evidence["set_id"],)
    finish(row)
    if anchor["precision"] != "exact":
        return None
    return {
        "pin": dict(PIN),
        "space": anchor["space"],
        "pointer": anchor["pointer"],
        "text": anchor["source_piece"],
    }


def test_independent_five_family_counts_and_empty_prediction_denominator():
    records, contexts = [], []
    for family in ("definition", "assertion", "measurement", "table", "formula_context"):
        row, texts = reading(family)
        # Exercise real production validation, not an assumed-valid test-side reading.
        assert (
            len(
                bind_record_candidates(
                    prepared(), source=PIN["source"], records=(row,), coordinate_texts=texts
                )
            )
            == 1
        )
        records.append(row)
        contexts.extend(texts)
    got = score(records, deepcopy(records), contexts)
    assert {tier: count.matched for tier, count in got.counts.items()} == {
        "core": 5,
        "full": 5,
        "evidence": 5,
    }
    assert {family: tiers["full"].matched for family, tiers in got.family_counts.items()} == {
        "definition": 1,
        "assertion": 1,
        "measurement": 1,
        "table": 1,
        "formula_context": 1,
    }
    empty = score(records, (), contexts).as_dict()
    assert empty["tiers"]["full"] == {
        "reference": 5,
        "prediction": 0,
        "matched": 0,
        "precision": None,
        "recall": 0.0,
        "f1": 0.0,
    }
    assert empty["families"]["formula_context"]["full"]["reference"] == 1
    assert empty["scope"] == "private_validated_records"
    assert empty["grain"] == "accepted_source_record_occurrence"


def test_empty_region_still_reports_every_supported_family_without_accuracy_claim():
    got = score((), (), ()).as_dict()
    assert set(got["families"]) == {
        "definition",
        "assertion",
        "measurement",
        "table",
        "formula_context",
    }
    assert got["tiers"]["full"] == {
        "reference": 0,
        "prediction": 0,
        "matched": 0,
        "precision": None,
        "recall": None,
        "f1": None,
    }


@pytest.mark.parametrize(
    "family,name,new_value",
    [
        ("measurement", "unit", {"kind": "text", "text": "gallons"}),
        ("assertion", "polarity", {"kind": "assertion_polarity", "label": "negative"}),
        ("table", "note", {"kind": "text", "text": "observed"}),
    ],
)
def test_wrong_unit_flipped_negation_and_inherited_note_are_full_record_errors(
    family, name, new_value
):
    ref, contexts = reading(family)
    pred = deepcopy(ref)
    field = role(pred, name)
    field["value"] = new_value
    if field["kind"] == "literal":
        field["original"] = new_value["text"]
        # Another independently present source phrase is a valid but wrong role choice.
        extra = replace_evidence(pred, name, pointer=f"#/wrong/{name}", text=new_value["text"])
        contexts.append(extra)
    finish(pred)
    got = score((ref,), (pred,), contexts)
    assert (
        got.counts["core"].matched,
        got.counts["full"].matched,
        got.counts["evidence"].matched,
    ) == (1, 0, 0)
    assert name in got.field_failures[0]["reading_roles"]


@pytest.mark.parametrize(
    "family,name", [("assertion", "condition"), ("table", "note"), ("measurement", "value_role")]
)
def test_valid_in_cut_wrong_required_or_meaning_changing_anchor_fails_full(family, name):
    ref, contexts = reading(family)
    pred = deepcopy(ref)
    extra = replace_evidence(pred, name, pointer=f"#/different-scope/{name}")
    contexts.append(extra)
    got = score((ref,), (pred,), contexts)
    assert (got.counts["core"].matched, got.counts["full"].matched) == (1, 0)
    assert got.field_failures[0]["reading_roles"] == ()
    assert got.field_failures[0]["evidence_roles"] == (name,)


def test_missing_parent_header_is_not_the_same_table_reading():
    ref, contexts = reading("table")
    pred = deepcopy(ref)
    header = role(pred, "header_path")
    evidence = next(item for item in pred["evidence_sets"] if item["role"] == "header_path")
    evidence["anchors"] = evidence["anchors"][1:]
    evidence["set_id"] = evidence_set_identity(evidence)
    header.update(
        value={"kind": "text_sequence", "items": ("mean",)},
        original_pieces=("mean",),
        evidence_sets=(evidence["set_id"],),
    )
    finish(pred)
    got = score((ref,), (pred,), contexts)
    assert (got.counts["core"].matched, got.counts["full"].matched) == (0, 0)
    assert got.field_failures[0]["reading_roles"] == ("header_path",)


def test_cross_scope_symbol_cannot_match_equal_formula_text():
    ref, contexts = reading("formula_context")
    pred = deepcopy(ref)
    replace_evidence(pred, "scope", pointer="#/sections/another")
    role(pred, "scope")["value"]["pointer"] = "#/sections/another"
    finish(pred)
    got = score((ref,), (pred,), contexts)
    assert (got.counts["core"].matched, got.counts["full"].matched) == (0, 0)


def test_equal_text_at_two_occurrences_is_two_records_with_one_to_one_counts():
    ref, contexts = reading("definition")
    other = deepcopy(ref)
    extra = replace_evidence(other, "term", pointer="#/definition/term/repeated")
    contexts.append(extra)
    got = score((ref, other), (deepcopy(other),), contexts)
    assert got.counts["full"].as_dict() == {
        "reference": 2,
        "prediction": 1,
        "matched": 1,
        "precision": 1.0,
        "recall": 0.5,
        "f1": 2 / 3,
    }
    assert got.matches["full"] == [other["record_id"]]


def test_duplicate_or_competing_accepted_occurrence_cannot_inflate_true_positives():
    ref, contexts = reading("assertion")
    with pytest.raises(ValueError, match="duplicate record interpretation"):
        score((ref,), (deepcopy(ref), deepcopy(ref)), contexts)
    competing = deepcopy(ref)
    role(competing, "polarity")["value"]["label"] = "negative"
    finish(competing)
    with pytest.raises(ValueError, match="multiple accepted interpretations"):
        score((ref,), (deepcopy(ref), competing), contexts)


def test_nonaccepted_predictions_remain_separate_and_cannot_satisfy_recall():
    ref, contexts = reading("measurement")
    pred = deepcopy(ref)
    pred["standing"] = "unresolved"
    role(pred, "unit").update(
        state="unresolved",
        reason="unit association unresolved",
        evidence_status="unavailable",
        evidence_sets=(),
    )
    role(pred, "unit").pop("value")
    role(pred, "unit").pop("original")
    finish(pred)
    got = score((ref,), (pred,), contexts)
    assert got.prediction_standings == {"unresolved": 1}
    assert (
        got.counts["full"].reference,
        got.counts["full"].prediction,
        got.counts["full"].matched,
    ) == (1, 0, 0)
    with pytest.raises(ValueError, match="reference denominator"):
        score((pred,), (), contexts)


@pytest.mark.parametrize(
    "attribute,value",
    [
        ("unit", "other-region"),
        ("guideline_version", "guideline-2"),
        ("release_id", "other-release"),
    ],
)
def test_mismatched_region_guideline_or_release_refuses(attribute, value):
    ref, contexts = reading("table")
    bound = frame(ref)
    with pytest.raises(ValueError, match=r"frame|release"):
        align_records(
            RecordSide(bound, (ref,)),
            RecordSide(replace(bound, **{attribute: value}), (ref,)),
            prepared(),
            coordinate_texts=contexts,
        )


def test_out_of_cut_and_stale_coordinates_refuse_without_dropping_reference():
    ref, contexts = reading("table")
    wrong = replace(frame(ref), anchor_ids=frozenset())
    with pytest.raises(ValueError, match=r"outside.*cut"):
        score((ref,), (), contexts, binding=wrong)
    pred = deepcopy(ref)
    contexts.append(replace_evidence(pred, "note", pointer="#/outside-region/note"))
    with pytest.raises(ValueError, match=r"outside.*cut"):
        score((ref,), (pred,), contexts, binding=frame(ref))
    stale = deepcopy(contexts)
    stale[0]["pin"]["projection_digest"] = "d" * 64
    with pytest.raises(ValueError, match=r"stale.*source pin"):
        score((ref,), (), stale)
    changed_pin = {**PIN, "projection_digest": "d" * 64}
    with pytest.raises(ValueError, match="same source-region/guideline frame"):
        align_records(
            RecordSide(frame(ref), (ref,)),
            RecordSide(replace(frame(ref), pin=changed_pin), ()),
            prepared(),
            coordinate_texts=contexts,
        )


def test_broken_source_anchor_and_missing_coordinate_text_refuse_whole_operation():
    ref, contexts = reading("table")
    broken = deepcopy(ref)
    next(item for item in broken["anchors"] if item.get("source_piece") == "12")["source_piece"] = (
        "13"
    )
    with pytest.raises(ValueError, match="anchor identity"):
        score((ref,), (broken,), contexts)
    with pytest.raises(ValueError, match="lacks pinned coordinate text"):
        score((ref,), (), ())


def test_unknown_family_shape_and_policy_versions_refuse():
    ref, contexts = reading("measurement")
    for key, value, error in (
        ("family", "unhandled-family", "family/occurrence recipe"),
        ("contract", "SourceObject", "released family declaration"),
        ("occurrence_recipe", "unknown-recipe", "family/occurrence recipe"),
        ("policy_version", "unknown-policy", "acceptance policy"),
    ):
        wrong = deepcopy(ref)
        wrong[key] = value
        finish(wrong)
        with pytest.raises(ValueError, match=error):
            score((ref,), (wrong,), contexts)
    with pytest.raises(ValueError, match="unsupported record comparison policy"):
        align_records(
            RecordSide(frame(ref), (ref,)),
            RecordSide(frame(ref), ()),
            prepared(),
            comparison_policy="unknown-2",
        )


def test_reference_and_prediction_acceptance_policies_are_separate_from_guideline():
    ref, contexts = reading("definition")
    pred = deepcopy(ref)
    pred["policy_version"] = "producer-acceptance-4"
    finish(pred)
    bound = replace(frame(ref), prediction_policy_version="producer-acceptance-4")
    assert score((ref,), (pred,), contexts, binding=bound).counts["full"].matched == 1


def test_original_normalized_derived_and_nonpresent_states_are_not_relabelled():
    ref, contexts = reading("measurement")
    normalized = role(ref, "normalized_value")
    normalized.update(
        state="present",
        value={"kind": "decimal", "lexical": "1234567890123456789e-418"},
        original="1.234567890123456789e-400",
        policy="decimal-1",
        reason="exact normalization; no additional source cue",
    )
    finish(ref)
    pred = deepcopy(ref)
    role(pred, "normalized_value").update(
        kind="derived", rule="convert-1", premises=("original_value",)
    )
    finish(pred)
    got = score((ref,), (pred,), contexts)
    assert (got.counts["core"].matched, got.counts["full"].matched) == (1, 0)
    assert got.field_failures[0]["reading_roles"] == ("normalized_value",)
    ref, contexts = reading("definition")
    pred = deepcopy(ref)
    role(pred, "alias").update(state="inapplicable", reason="no alias applies")
    finish(pred)
    assert score((ref,), (pred,), contexts).counts["full"].matched == 0


def test_supplemental_evidence_is_separate_from_full_and_precision_is_preserved():
    # A supplemental alias is part of the complete reading, with evidence separately graded.
    ref, contexts = reading("definition")
    alias = deepcopy(role(ref, "term"))
    alias.update(role="alias", meaning_changing=False)
    alias_set = deepcopy(ref["evidence_sets"][0])
    alias_set["role"] = "alias"
    alias_set["set_id"] = evidence_set_identity(alias_set)
    alias["evidence_sets"] = (alias_set["set_id"],)
    ref["fields"] = [alias if item["role"] == "alias" else item for item in ref["fields"]]
    ref["evidence_sets"] = (*ref["evidence_sets"], alias_set)
    finish(ref)
    pred = deepcopy(ref)
    # Change only alias evidence membership, not the shared term anchor itself.
    extra_anchor = deepcopy(ref["anchors"][0])
    extra_anchor["pointer"] = "#/alias/another-mention"
    extra_anchor["anchor_id"] = anchor_identity(extra_anchor)
    pred["anchors"] = (*pred["anchors"], extra_anchor)
    evidence = next(item for item in pred["evidence_sets"] if item["role"] == "alias")
    evidence["anchors"] = (extra_anchor["anchor_id"],)
    evidence["set_id"] = evidence_set_identity(evidence)
    role(pred, "alias")["evidence_sets"] = (evidence["set_id"],)
    contexts.append(
        {
            "pin": dict(PIN),
            "space": "native",
            "pointer": extra_anchor["pointer"],
            "text": "variance",
        }
    )
    finish(pred)
    got = score((ref,), (pred,), contexts)
    assert (
        got.counts["core"].matched,
        got.counts["full"].matched,
        got.counts["evidence"].matched,
    ) == (1, 1, 0)


def test_exact_item_and_coordinate_space_distinctions_are_not_weakened():
    ref, contexts = reading("formula_context")
    pred = deepcopy(ref)
    extra = replace_evidence(pred, "formula", space="selected_projection")
    contexts.append(extra)
    # Formula is an occurrence anchor, so changing its coordinate space changes occurrence.
    got = score((ref,), (pred,), contexts)
    assert (
        got.counts["core"].reference,
        got.counts["core"].prediction,
        got.counts["core"].matched,
    ) == (1, 1, 0)
    ref, contexts = reading("table")
    pred = deepcopy(ref)
    replace_evidence(pred, "table", precision="coarse")
    got = score((ref,), (pred,), contexts)
    assert (got.counts["core"].matched, got.counts["full"].matched) == (1, 0)


def test_explanations_and_computation_ids_do_not_replace_semantics_or_mutate_inputs():
    ref, contexts = reading("definition")
    pred = deepcopy(ref)
    role(pred, "alias")["reason"] = "independently worded source absence explanation"
    pred.update(
        computation_dependencies=("observation:other-attempt",), assertion_members=("fact:other",)
    )
    finish(pred)
    before = deepcopy((ref, pred, contexts))
    assert score((ref,), (pred,), contexts).counts["evidence"].matched == 1
    assert (ref, pred, contexts) == before


def test_actual_released_role_requiredness_drives_core_scoring():
    document = yaml.safe_load((ROOT / "domains/statistics/semantic.yaml").read_text())
    document["classes"]["MeasurementRecordFields"]["attributes"]["unit"]["range"] = (
        "RequiredLiteralRecordField"
    )
    changed = prepare_release(
        observation_inputs(
            SourceBundle(
                "statistics_semantic",
                (
                    SourceArtifact("statistics_semantic", yaml.safe_dump(document).encode()),
                    SourceArtifact("semantic_core", (MODEL / "core.yaml").read_bytes()),
                ),
            )
        )
    )
    ref, contexts = reading("measurement")
    pred = deepcopy(ref)
    role(pred, "unit").update(value={"kind": "text", "text": "gallons"}, original="gallons")
    contexts.append(replace_evidence(pred, "unit", pointer="#/other/unit", text="gallons"))
    for row in (ref, pred):
        row["record_id"] = record_identity(changed.release_id, row)
        row["interpretation_id"] = interpretation_identity(row)
    bound = replace(frame(ref, pred), release_id=changed.release_id)
    got = align_records(
        RecordSide(bound, (ref,)), RecordSide(bound, (pred,)), changed, coordinate_texts=contexts
    )
    # The same controlled error was core-correct under the original optional-unit contract.
    assert (got.counts["core"].matched, got.counts["full"].matched) == (0, 0)


def test_typed_alternatives_compare_without_local_ids_or_explanatory_prose():
    ref, contexts = reading("definition")
    role(ref, "term")["alternatives"] = (
        {
            "alternative_id": "author-a",
            "value": {"kind": "text", "text": "dispersion"},
            "reason": "source ambiguity",
        },
    )
    finish(ref)
    pred = deepcopy(ref)
    alternative = role(pred, "term")["alternatives"][0]
    alternative.update(alternative_id="producer-b", reason="independently worded ambiguity")
    finish(pred)
    assert score((ref,), (pred,), contexts).counts["evidence"].matched == 1
    alternative["value"]["text"] = "standard deviation"
    finish(pred)
    got = score((ref,), (pred,), contexts)
    assert (got.counts["core"].matched, got.counts["full"].matched) == (0, 0)


def test_evidence_set_ordering_standing_is_not_discarded():
    ref, contexts = reading("formula_context")
    pred = deepcopy(ref)
    evidence = next(item for item in pred["evidence_sets"] if item["role"] == "scope")
    evidence["ordering"] = "unordered"
    evidence["set_id"] = evidence_set_identity(evidence)
    role(pred, "scope")["evidence_sets"] = (evidence["set_id"],)
    finish(pred)
    got = score((ref,), (pred,), contexts)
    assert (got.counts["core"].matched, got.counts["full"].matched) == (1, 0)
