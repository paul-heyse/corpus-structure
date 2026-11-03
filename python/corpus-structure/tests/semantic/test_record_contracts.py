"""Independent private record expectations; no provider or publication qualification."""

from copy import deepcopy
from functools import cache
from pathlib import Path

import pytest
import yaml
from pydantic import BaseModel, ValidationError

from corpus_structure.core.method import ObservationDraft, UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationKind, ObservationOutcome, TaskUnitType
from corpus_structure.semantic import (
    PreparationError,
    PreparationProfile,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.archive_reader import reconstruct_release
from corpus_structure.semantic.observations import bind_result, observation_inputs
from corpus_structure.semantic.record_contracts import (
    anchor_identity,
    bind_record_candidates,
    evidence_set_identity,
    interpretation_identity,
    record_identity,
)
from corpus_structure.semantic.releases import _products

ROOT = Path(__file__).resolve().parents[4]
MODEL = ROOT / "python/corpus-structure/src/corpus_structure/model/semantic"
PIN = {
    "source": "source:table",
    "native_product_task_id": 23,
    "product_key": "organized",
    "product_digest": "a" * 64,
    "projection_digest": "b" * 64,
    "recipe_digest": "c" * 64,
    "source_view_id": 7,
}


@cache
def release_inputs():
    bundle = observation_inputs(
        SourceBundle(
            "statistics_semantic",
            (
                SourceArtifact(
                    "statistics_semantic", (ROOT / "domains/statistics/semantic.yaml").read_bytes()
                ),
                SourceArtifact("semantic_core", (MODEL / "core.yaml").read_bytes()),
            ),
        )
    )
    profile = PreparationProfile()
    return bundle, profile, prepare_release(bundle, profile=profile)


def anchor(pointer, text=None, start=None, end=None, *, space="native", precision="exact"):
    row = {"pin": dict(PIN), "space": space, "pointer": pointer, "precision": precision}
    if text is not None:
        row["source_piece"] = text
    if start is not None:
        row.update(start=start, end=end)
    row["anchor_id"] = anchor_identity(row)
    return row


def field(
    role,
    value=None,
    *,
    kind="literal",
    state="present",
    evidence=(),
    original=None,
    originals=None,
    meaning=True,
):
    row = {
        "role": role,
        "kind": kind,
        "state": state,
        "meaning_changing": meaning,
        "evidence_status": "available" if evidence else "unavailable",
        "evidence_sets": tuple(evidence),
    }
    if value is not None:
        row["value"] = value
    if original is not None:
        row["original"] = original
    if originals is not None:
        row["original_pieces"] = tuple(originals)
    if state != "present":
        row["reason"] = "not stated in the explicitly inspected source"
    return row


def finish(record):
    record["record_id"] = record_identity(release_inputs()[2].release_id, record)
    record["interpretation_id"] = interpretation_identity(record)
    return record


def table_record():
    # Two repeated numeric strings have independently specified positions/cells.
    pieces = {
        "table": anchor("#/tables/0", precision="item"),
        "cell": anchor("#/tables/0/cells/3", precision="item"),
        "row_identity": anchor("#/tables/0/cells/0", "Group A", 0, 7),
        "parent": anchor("#/tables/0/cells/1", "Population", 0, 10),
        "child": anchor("#/tables/0/cells/2", "mean", 0, 4),
        "value": anchor("#/tables/0/cells/3", "12", 0, 2),
        "note": anchor("#/texts/4", "hypothetical", 0, 12),
    }
    memberships = {
        "table": ("table",),
        "cell": ("cell",),
        "row_identity": ("row_identity",),
        "header_path": ("parent", "child"),
        "cell_value": ("value",),
        "note": ("note",),
    }
    sets = []
    by_role = {}
    for role, names in memberships.items():
        evidence = {
            "role": role,
            "ordering": "ordered",
            "usage": "native" if role in {"table", "cell"} else "literal",
            "anchors": tuple(pieces[name]["anchor_id"] for name in names),
        }
        evidence["set_id"] = evidence_set_identity(evidence)
        sets.append(evidence)
        by_role[role] = (evidence["set_id"],)
    fields = (
        field(
            "table",
            {"kind": "native_location", "pointer": "#/tables/0"},
            kind="native",
            evidence=by_role["table"],
        ),
        field(
            "cell",
            {"kind": "native_location", "pointer": "#/tables/0/cells/3"},
            kind="native",
            evidence=by_role["cell"],
        ),
        field(
            "row_identity",
            {"kind": "text", "text": "Group A"},
            original="Group A",
            evidence=by_role["row_identity"],
        ),
        field(
            "header_path",
            {"kind": "text_sequence", "items": ("Population", "mean")},
            originals=("Population", "mean"),
            evidence=by_role["header_path"],
        ),
        field(
            "cell_value",
            {"kind": "decimal", "lexical": "12"},
            original="12",
            evidence=by_role["cell_value"],
        ),
        field(
            "note",
            {"kind": "text", "text": "hypothetical"},
            original="hypothetical",
            evidence=by_role["note"],
        ),
        field("unit", state="unstated"),
        field("caption", state="inapplicable"),
    )
    record = {
        "contract": "TableRecordFields",
        "family": "table",
        "occurrence_recipe": "source-anchor-membership-1",
        "pin": dict(PIN),
        "occurrence_anchors": (pieces["cell"]["anchor_id"],),
        "standing": "accepted",
        "policy_version": "reading-1",
        "fields": fields,
        "anchors": tuple(pieces.values()),
        "evidence_sets": tuple(sets),
        "computation_dependencies": ("observation:rejected-header-alternative",),
        "assertion_members": ("fact:value", "fact:condition"),
    }
    contexts = tuple(
        {"pin": dict(PIN), "space": "native", "pointer": pointer, "text": text}
        for pointer, text in (
            ("#/tables/0/cells/0", "Group A"),
            ("#/tables/0/cells/1", "Population"),
            ("#/tables/0/cells/2", "mean"),
            ("#/tables/0/cells/3", "12"),
            ("#/texts/4", "hypothetical"),
        )
    )
    return finish(record), contexts


def bind(record, contexts=(), release=None):
    return bind_record_candidates(
        release or release_inputs()[2],
        source=PIN["source"],
        records=(record,),
        coordinate_texts=contexts,
    )[0]


def test_table_preserves_full_header_native_cell_note_and_assertion_members():
    record, contexts = table_record()
    bound = bind(record, contexts).model_dump(mode="python")
    fields = {row["role"]: row for row in bound["fields"]}
    assert fields["header_path"]["original_pieces"] == ("Population", "mean")
    assert fields["cell_value"]["value"] == {"kind": "decimal", "lexical": "12"}
    assert fields["unit"]["state"] == "unstated"
    assert fields["caption"]["state"] == "inapplicable"
    assert bound["assertion_members"] == ("fact:value", "fact:condition")
    assert [(row["pointer"], row.get("start"), row.get("end")) for row in bound["anchors"]] == [
        ("#/tables/0", None, None),
        ("#/tables/0/cells/3", None, None),
        ("#/tables/0/cells/0", 0, 7),
        ("#/tables/0/cells/1", 0, 10),
        ("#/tables/0/cells/2", 0, 4),
        ("#/tables/0/cells/3", 0, 2),
        ("#/texts/4", 0, 12),
    ]


def test_generated_five_family_boundaries_are_archived_and_reopened():
    bundle, profile, prepared = release_inputs()
    expected = {
        "DefinitionRecordFields",
        "AssertionRecordFields",
        "MeasurementRecordFields",
        "TableRecordFields",
        "FormulaRecordFields",
    }
    assert expected <= prepared.index.definitions.keys()
    reopened = reconstruct_release(
        _products(prepared), prepared.manifest, bundle, profile, prepared.artifacts
    )
    record, contexts = table_record()
    assert (
        bind(record, contexts, reopened).model_dump_json()
        == bind(record, contexts).model_dump_json()
    )


def test_binding_preserves_record_memberships_and_retry_identity():
    record, contexts = table_record()

    class RawProviderReport(BaseModel):
        source_text: str

    report = RawProviderReport(source_text="Group A mean 12")
    kwargs = dict(
        source=PIN["source"],
        method="record",
        operation_version="1",
        configuration_hash="c",
        input_hash="i",
        invocation_key="invocation:1",
        records=(record,),
        record_coordinate_texts=contexts,
        result=UnitResult(
            ref=UnitRef(TaskUnitType.SOURCE_VIEW, 7, "view"),
            outcome=ObservationOutcome.PRODUCED,
            observations=(
                ObservationDraft(
                    kind=ObservationKind.RECORD,
                    payload=report,
                    payload_class=RawProviderReport,
                    payload_version="1",
                    source_view_id=7,
                ),
            ),
        ),
    )
    prepared = release_inputs()[2]
    assert (
        bind_result(prepared, **kwargs).model_dump_json()
        == bind_result(prepared, **kwargs).model_dump_json()
    )
    assert bind_result(prepared, **kwargs).records[0].record_id == record["record_id"]
    # Operational retry/sequence positions are not source occurrence meaning.
    moved = deepcopy(record)
    moved["pin"]["source_view_id"] = 81
    for row in moved["anchors"]:
        row["pin"]["source_view_id"] = 81
    assert record_identity(prepared.release_id, moved) == record["record_id"]
    moved["pin"]["recipe_digest"] = "d" * 64
    assert record_identity(prepared.release_id, moved) != record["record_id"]
    kwargs["result"] = UnitResult(
        ref=UnitRef(TaskUnitType.SOURCE_VIEW, 7, "view"), outcome=ObservationOutcome.EMPTY
    )
    with pytest.raises(ValueError, match="produced source report"):
        bind_result(prepared, **kwargs)


def test_equal_text_at_another_cell_is_another_record_and_dependency_change_is_new_interpretation():
    record, _ = table_record()
    other = deepcopy(record)
    other["occurrence_anchors"] = (anchor("#/tables/0/cells/9", precision="item")["anchor_id"],)
    assert record_identity(release_inputs()[2].release_id, other) != record["record_id"]
    other = deepcopy(record)
    other["computation_dependencies"] = ("observation:changed-countercandidate",)
    assert interpretation_identity(other) != record["interpretation_id"]


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda row: row.update(family="measurement"), "family/occurrence recipe"),
        (lambda row: row.update(contract="SourceObject"), "released family"),
        (lambda row: row.update(occurrence_recipe="unsupported-2"), "family/occurrence recipe"),
        (lambda row: row["anchors"][2].update(end=8), "anchor identity"),
        (lambda row: row["pin"].update(product_digest="d" * 64), "source pin"),
        (lambda row: row["pin"].update(recipe_digest="not-a-digest"), "pattern"),
        (lambda row: row["pin"].update(native_product_task_id=0), "greater than or equal"),
        (lambda row: row["fields"][4].update(original="13"), "original source spelling"),
        (
            lambda row: row["fields"][4].update(value={"kind": "decimal", "lexical": "NaN"}),
            "pattern",
        ),
        (lambda row: row["fields"][4].update(value={"kind": "decimal", "lexical": 12.0}), "string"),
        (
            lambda row: row.update(fields=(*row["fields"], row["fields"][0])),
            "duplicate record role",
        ),
        (lambda row: row.update(occurrence_anchors=("missing",)), "occurrence anchor membership"),
    ],
)
def test_independent_contract_refusals(mutation, match):
    record, contexts = table_record()
    mutation(record)
    with pytest.raises((ValueError, ValidationError), match=match):
        bind(record, contexts)


def test_missing_role_unresolved_role_and_unknown_role_refuse_full_acceptance():
    record, contexts = table_record()
    record["fields"] = record["fields"][1:]
    with pytest.raises(ValidationError, match="table"):
        bind(record, contexts)
    record, contexts = table_record()
    record["fields"] = tuple(
        field("unit", state="unresolved") if row["role"] == "unit" else row
        for row in record["fields"]
    )
    finish(record)
    with pytest.raises(ValueError, match="unresolved meaning-changing"):
        bind(record, contexts)
    record["standing"] = "candidate"
    assert bind(record, contexts).standing == "candidate"


def test_synthetic_and_coarse_spans_do_not_become_exact_literals():
    record, contexts = table_record()
    with pytest.raises(ValueError, match="does not reconstruct"):
        bind(record, (*contexts[:-1], {**contexts[-1], "text": "synthetic appended punctuation"}))
    old = record["anchors"][5]
    replacement = anchor(old["pointer"], "12", precision="coarse")
    record["anchors"] = (*record["anchors"][:5], replacement, record["anchors"][6])
    evidence = record["evidence_sets"][4]
    old_set = evidence["set_id"]
    evidence["anchors"] = (replacement["anchor_id"],)
    evidence["set_id"] = evidence_set_identity(evidence)
    for row in record["fields"]:
        if row["evidence_sets"] == (old_set,):
            row["evidence_sets"] = (evidence["set_id"],)
    finish(record)
    with pytest.raises(ValueError, match="exact located evidence"):
        bind(record, contexts)


def test_source_record_requires_same_producer_pin_and_model_context_is_not_evidence():
    record, contexts = table_record()
    with pytest.raises(ValueError, match="producing source"):
        bind_record_candidates(release_inputs()[2], source="another-source", records=(record,))
    raw = record["anchors"][0]
    raw["space"] = "model_context"
    raw["anchor_id"] = anchor_identity(raw)
    with pytest.raises(ValueError, match="model context"):
        bind(record, contexts)


def record_from_fields(contract, family, specifications, absent):
    """Fixture coordinates and role expectations are authored independently below."""
    anchors, sets, fields, contexts = [], [], [], []
    for role, kind, pointer, space, text, value in specifications:
        piece = anchor(
            pointer,
            text,
            0 if text is not None else None,
            len(text) if text is not None else None,
            space=space,
            precision="exact" if text is not None else "item",
        )
        anchors.append(piece)
        evidence = {
            "role": role,
            "ordering": "ordered",
            "usage": "classification_cue" if kind == "classified" else kind,
            "anchors": (piece["anchor_id"],),
        }
        evidence["set_id"] = evidence_set_identity(evidence)
        sets.append(evidence)
        fields.append(
            field(
                role,
                value,
                kind=kind,
                evidence=(evidence["set_id"],),
                original=text if kind == "literal" else None,
            )
        )
        if text is not None:
            contexts.append({"pin": dict(PIN), "space": space, "pointer": pointer, "text": text})
    for role, kind, meaning in absent:
        fields.append(field(role, state="unstated", kind=kind, meaning=meaning))
    return finish(
        {
            "contract": contract,
            "family": family,
            "occurrence_recipe": "source-anchor-membership-1",
            "pin": dict(PIN),
            "occurrence_anchors": (anchors[0]["anchor_id"],),
            "standing": "accepted",
            "policy_version": "reading-1",
            "fields": tuple(fields),
            "anchors": tuple(anchors),
            "evidence_sets": tuple(sets),
        }
    ), tuple(contexts)


def formula_record():
    return record_from_fields(
        "FormulaRecordFields",
        "formula_context",
        (
            (
                "formula",
                "literal",
                "#/formulas/2",
                "recognized_text",
                "f(x)=x²",
                {"kind": "text", "text": "f(x)=x²"},
            ),
            (
                "scope",
                "native",
                "#/groups/3",
                "native",
                None,
                {"kind": "native_location", "pointer": "#/groups/3"},
            ),
            (
                "symbol",
                "literal",
                "#/texts/8",
                "selected_projection",
                "x",
                {"kind": "text", "text": "x"},
            ),
            (
                "meaning",
                "literal",
                "#/texts/9",
                "selected_projection",
                "input value",
                {"kind": "text", "text": "input value"},
            ),
            (
                "domain",
                "literal",
                "#/texts/10",
                "selected_projection",
                "real",
                {"kind": "text", "text": "real"},
            ),
        ),
        (("assumption", "literal", True),),
    )


def measurement_record():
    return record_from_fields(
        "MeasurementRecordFields",
        "measurement",
        (
            (
                "referent",
                "literal",
                "#/texts/1",
                "native",
                "bottle",
                {"kind": "text", "text": "bottle"},
            ),
            (
                "property",
                "literal",
                "#/texts/2",
                "native",
                "volume",
                {"kind": "text", "text": "volume"},
            ),
            (
                "original_value",
                "literal",
                "#/texts/3",
                "native",
                "1.234567890123456789e-400",
                {"kind": "decimal", "lexical": "1.234567890123456789e-400"},
            ),
            (
                "value_role",
                "classified",
                "#/texts/4",
                "native",
                "average",
                {"kind": "measurement_value_role", "label": "mean"},
            ),
        ),
        (
            ("unit", "literal", True),
            ("comparator", "literal", True),
            ("uncertainty", "literal", True),
            ("reference_quantity", "literal", True),
            ("condition", "literal", True),
            ("normalized_value", "normalized", False),
        ),
    )


def test_formula_and_declaration_keep_separate_coordinate_spaces():
    record, contexts = formula_record()
    bound = bind(record, contexts).model_dump(mode="python")
    assert [
        (row["pointer"], row["space"], row.get("start"), row.get("end")) for row in bound["anchors"]
    ] == [
        ("#/formulas/2", "recognized_text", 0, 7),
        ("#/groups/3", "native", None, None),
        ("#/texts/8", "selected_projection", 0, 1),
        ("#/texts/9", "selected_projection", 0, 11),
        ("#/texts/10", "selected_projection", 0, 4),
    ]
    assert bound["fields"][5]["state"] == "unstated"


def test_classified_enum_retains_cue_and_exact_scientific_number_without_literal_label():
    record, contexts = measurement_record()
    bound = bind(record, contexts).model_dump(mode="python")
    assert bound["fields"][2]["value"]["lexical"] == "1.234567890123456789e-400"
    assert bound["fields"][3]["value"] == {"kind": "measurement_value_role", "label": "mean"}
    assert bound["anchors"][3]["source_piece"] == "average"
    assert "original" not in bound["fields"][3]
    record["fields"][3]["value"]["label"] = "unsupported-measurement-role"
    with pytest.raises(ValidationError, match="literal"):
        bind(record, contexts)


def test_classification_record_association_and_zero_offsets_cannot_manufacture_a_cue():
    record, contexts = measurement_record()
    role = record["fields"][3]
    evidence = record["evidence_sets"][3]
    evidence["usage"] = "association"
    evidence["set_id"] = evidence_set_identity(evidence)
    role["evidence_sets"] = (evidence["set_id"],)
    finish(record)
    with pytest.raises(ValueError, match="association is not located source cue"):
        bind(record, contexts)
    role["evidence_sets"] = ()
    role["evidence_status"] = "unavailable"
    role["reason"] = "provider supplied record association offsets (0,0); no cue was located"
    record["evidence_sets"] = record["evidence_sets"][:3]
    record["anchors"] = record["anchors"][:3]
    finish(record)
    with pytest.raises(ValueError, match="required role lacks located evidence"):
        bind(record, contexts)
    record["standing"] = "candidate"
    assert bind(record, contexts).fields[3].evidence_status == "unavailable"


def test_discontinuous_definition_retains_two_real_original_pieces():
    record, contexts = record_from_fields(
        "DefinitionRecordFields",
        "definition",
        (
            (
                "term",
                "literal",
                "#/texts/1",
                "native",
                "randomvariable",
                {"kind": "text", "text": "randomvariable"},
            ),
            (
                "defining_text",
                "literal",
                "#/texts/2",
                "native",
                "a measurable map",
                {"kind": "text", "text": "a measurable map"},
            ),
            (
                "scope",
                "native",
                "#/groups/3",
                "native",
                None,
                {"kind": "native_location", "pointer": "#/groups/3"},
            ),
        ),
        (("alias", "literal", False), ("relation_type", "classified", False)),
    )
    first = anchor("#/texts/1", "random", 0, 6)
    last = anchor("#/texts/1", "variable", 11, 19)
    record["anchors"] = (first, last, *record["anchors"][1:])
    record["occurrence_anchors"] = (first["anchor_id"], last["anchor_id"])
    evidence = record["evidence_sets"][0]
    evidence["anchors"] = (first["anchor_id"], last["anchor_id"])
    evidence["set_id"] = evidence_set_identity(evidence)
    record["fields"] = (
        field(
            "term",
            {"kind": "text_sequence", "items": ("random", "variable")},
            originals=("random", "variable"),
            evidence=(evidence["set_id"],),
        ),
        *record["fields"][1:],
    )
    contexts = ({**contexts[0], "text": "random ... variable"}, *contexts[1:])
    finish(record)
    assert bind(record, contexts).fields[0].original_pieces == ("random", "variable")
    record["fields"][0]["original_pieces"] = ("random ", "variable")
    with pytest.raises(ValueError, match="original source pieces"):
        bind(record, contexts)


def test_required_state_and_released_meaning_changing_role_cannot_be_overridden():
    record, contexts = formula_record()
    record["fields"] = (field("formula", state="unresolved"), *record["fields"][1:])
    finish(record)
    with pytest.raises(ValueError, match="missing a required role"):
        bind(record, contexts)
    record, contexts = table_record()
    record["fields"][6]["state"] = "unresolved"
    record["fields"][6]["meaning_changing"] = False
    finish(record)
    with pytest.raises(ValueError, match="differs from released role"):
        bind(record, contexts)


def test_normalization_and_derivation_require_original_policy_and_real_premises():
    record, contexts = measurement_record()
    normalized = record["fields"][-1]
    normalized.update(
        state="present", value={"kind": "decimal", "lexical": "1234567890123456789e-418"}
    )
    finish(record)
    with pytest.raises(ValueError, match="requires its policy"):
        bind(record, contexts)
    normalized.update(policy="decimal-policy-1", original="1.234567890123456789e-400")
    finish(record)
    assert bind(record, contexts).fields[-1].value.lexical == "1234567890123456789e-418"
    normalized.update(kind="derived")
    finish(record)
    with pytest.raises(ValueError, match="present premises and rule"):
        bind(record, contexts)
    normalized.update(rule="unit-conversion-1", premises=("original_value",))
    finish(record)
    assert bind(record, contexts).fields[-1].premises == ("original_value",)
    normalized.update(kind="classified", value={"kind": "classification", "label": "x"})
    with pytest.raises(ValidationError, match=r"derived.*normalized"):
        bind(record, contexts)


def test_multiple_sets_cannot_duplicate_one_source_value_into_a_new_literal():
    record, contexts = table_record()
    original_set = record["evidence_sets"][4]
    second_set = {**original_set, "ordering": "unordered"}
    second_set["set_id"] = evidence_set_identity(second_set)
    record["evidence_sets"] = (*record["evidence_sets"], second_set)
    value = record["fields"][4]
    value["evidence_sets"] = (original_set["set_id"], second_set["set_id"])
    finish(record)
    assert bind(record, contexts).fields[4].original == "12"
    value.update(original="1212", value={"kind": "decimal", "lexical": "1212"})
    finish(record)
    with pytest.raises(ValueError, match="does not reconstruct"):
        bind(record, contexts)


@pytest.mark.parametrize(
    "source_text,intervals,literal",
    [
        ("12", ((0, 2), (0, 1)), "121"),
        ("1 2", ((2, 3), (0, 1)), "21"),
    ],
)
def test_one_literal_set_cannot_overlap_or_reverse_a_source_coordinate(
    source_text, intervals, literal
):
    record, contexts = table_record()
    pieces = tuple(
        anchor("#/tables/0/cells/3", source_text[start:end], start, end) for start, end in intervals
    )
    record["anchors"] = (*record["anchors"][:5], *pieces, *record["anchors"][6:])
    evidence = record["evidence_sets"][4]
    evidence["anchors"] = tuple(piece["anchor_id"] for piece in pieces)
    evidence["set_id"] = evidence_set_identity(evidence)
    record["fields"][4].update(
        original=literal,
        value={"kind": "decimal", "lexical": literal},
        evidence_sets=(evidence["set_id"],),
    )
    contexts = tuple(
        {**row, "text": source_text} if row["pointer"] == "#/tables/0/cells/3" else row
        for row in contexts
    )
    finish(record)
    with pytest.raises(ValueError, match="overlap or reverse source order"):
        bind(record, contexts)


def test_unordered_multi_piece_literal_has_no_invented_reconstruction_order():
    record, contexts = table_record()
    header = record["evidence_sets"][3]
    header["ordering"] = "unordered"
    old_identity = header["set_id"]
    header["set_id"] = evidence_set_identity(header)
    record["fields"][3]["evidence_sets"] = (header["set_id"],)
    assert old_identity != header["set_id"]
    finish(record)
    with pytest.raises(ValueError, match="requires an ordered evidence set"):
        bind(record, contexts)
    identity = header["set_id"]
    header["anchors"] = tuple(reversed(header["anchors"]))
    assert evidence_set_identity(header) == identity
    finish(record)
    with pytest.raises(ValueError, match="requires an ordered evidence set"):
        bind(record, contexts)


@pytest.mark.parametrize(
    "change,match",
    [
        (
            lambda classes: classes["MeasurementRecordFields"]["attributes"]["value_role"].update(
                range="string"
            ),
            "scalar inlined RecordField",
        ),
        (
            lambda classes: classes["MeasurementRecordFields"]["attributes"]["unit"].update(
                required=False
            ),
            "explicit states",
        ),
        (
            lambda classes: classes["MeasurementRecordFields"]["attributes"][
                "occurrence_recipe"
            ].update(equals_string="unknown-recipe-2"),
            "unsupported released record occurrence recipe",
        ),
        (
            lambda classes: classes["DefinitionRecordFields"]["attributes"]["family"].update(
                equals_string="measurement"
            ),
            "unique nonempty released family",
        ),
    ],
)
def test_unsupported_family_contract_refuses_preparation(change, match):
    bundle, profile, _ = release_inputs()
    sources = []
    for source in bundle.sources:
        if source.name == "statistics_semantic":
            document = yaml.safe_load(source.content)
            change(document["classes"])
            source = SourceArtifact(source.name, yaml.safe_dump(document).encode())
        sources.append(source)
    with pytest.raises(PreparationError, match=match):
        prepare_release(SourceBundle(bundle.root, tuple(sources)), profile=profile)
