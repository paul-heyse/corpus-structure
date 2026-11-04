"""Independent reading identity/state expectations; controlled decoder, no provider claim."""

import json
import math
from dataclasses import replace
from types import SimpleNamespace

import pytest

from corpus_structure.methods.math.pdf import FormulaOccurrence
from corpus_structure.methods.record_assembly import (
    OCCURRENCE_POLICY,
    LiteralSpan,
    NativeRecordGroup,
    RoleInput,
    assemble_native_records,
    assemble_records,
    native_formula_group,
    native_group_identity,
)
from corpus_structure.methods.record_packs import family_pack
from corpus_structure.methods.record_readings import (
    interpret_candidate_readings,
    native_model_observations,
)
from corpus_structure.semantic import record_interpretation as ri
from corpus_structure.semantic.source_contexts import (
    ContextRelationship,
    NativeSourceContext,
    RelatedNativeSource,
    SourceSlice,
)
from methods.test_record_assembly import context, fields, release, report, source, span


def test_auxiliary_state_is_an_independent_proposal_not_decoder_absence():
    ctx = context("A mean 2")
    pack = family_pack(
        release(),
        contract="MeasurementRecordFields",
        anchor_role="original_value",
        source_inspection=True,
    )
    group = dict(
        referent=span(0, 1, "A"),
        property=span(2, 6, "mean"),
        original_value=span(7, 8, "2"),
        value_role={"text": "mean", "confidence": 0.83},
        value_role__cue=span(2, 6, "mean"),
        unit__state={"text": "unstated"},
        comparator__state={"text": "unstated"},
        uncertainty__state={"text": "unstated"},
        reference_quantity__state={"text": "unstated"},
        condition__state={"text": "unstated"},
    )
    raw = report(ctx, pack, "measurement", [group])
    result = assemble_records(
        release(),
        ctx,
        pack,
        raw,
        contract="MeasurementRecordFields",
        anchor_role="original_value",
        policy_version="m1-grouped-reading-logistic-1",
        occurrence_policy=OCCURRENCE_POLICY,
    )
    (record,) = result.records
    actual = fields(record)
    assert actual["unit"]["state"] == "unstated"
    assert actual["value_role"]["value"]["label"] == "mean"
    assert actual["value_role"]["evidence_status"] == "available"
    assert actual["normalized_value"]["state"] == "inapplicable"
    row = record.model_dump()
    assert {evidence["role"] for evidence in row["evidence_sets"]} == set(actual)
    assert len({evidence["set_id"] for evidence in row["evidence_sets"]}) == len(actual)
    unit_set = next(e for e in row["evidence_sets"] if e["role"] == "unit")
    inspected = next(a for a in row["anchors"] if a["anchor_id"] == unit_set["anchors"][0])
    assert inspected["source_piece"] == "A mean 2" and unit_set["usage"] == "context"
    assert result.raw_report is raw
    omitted = dict(group)
    omitted.pop("unit__state")
    omitted.pop("value_role__cue")
    second = assemble_records(
        release(),
        ctx,
        pack,
        report(ctx, pack, "measurement", [omitted]),
        contract="MeasurementRecordFields",
        anchor_role="original_value",
        policy_version="test",
        occurrence_policy=OCCURRENCE_POLICY,
    )
    assert fields(second.records[0])["unit"]["state"] == "unresolved"
    assert fields(second.records[0])["value_role"]["state"] == "unresolved"
    assert fields(second.records[0])["value_role"]["evidence_status"] == "available"
    conflicting = {**group, "unit": span(2, 6, "mean")}
    third = assemble_records(
        release(),
        ctx,
        pack,
        report(ctx, pack, "measurement", [conflicting]),
        contract="MeasurementRecordFields",
        anchor_role="original_value",
        policy_version="test",
    )
    assert fields(third.records[0])["unit"]["state"] == "unresolved"


def conflicting_measurement():
    return dict(
        referent={**span(0, 1, "A"), "confidence": 0.91},
        referent__state={"text": "unstated", "confidence": 0.12},
        property=span(2, 6, "mean"),
        property__state={"text": "unresolved"},
        original_value=span(7, 8, "2"),
        original_value__state={"text": "inapplicable"},
        value_role={"text": "mean", "confidence": 0.83},
        value_role__state={"text": "unstated"},
        value_role__cue=span(2, 6, "mean"),
        condition__state={"text": "unstated"},
    )


def assemble_conflicting(groups):
    ctx = context("A mean 2")
    pack = family_pack(
        release(),
        contract="MeasurementRecordFields",
        anchor_role="original_value",
        source_inspection=True,
    )
    raw = report(ctx, pack, "measurement", groups)
    result = assemble_records(
        release(),
        ctx,
        pack,
        raw,
        contract="MeasurementRecordFields",
        anchor_role="original_value",
        policy_version="m1-grouped-reading-logistic-1",
        occurrence_policy=OCCURRENCE_POLICY,
    )
    return ctx, raw, result


def test_conflicting_primary_spans_keep_located_alternatives_and_one_whole_value_hypothesis():
    group = conflicting_measurement()
    ctx, raw, result = assemble_conflicting([group])
    assert len(result.records) == 2
    inspected, valued = (record.model_dump() for record in result.records)
    assert inspected["record_id"] == valued["record_id"]
    assert inspected["interpretation_id"] != valued["interpretation_id"]
    assert inspected["standing"] == valued["standing"] == "candidate"
    assert inspected["occurrence_anchors"] == valued["occurrence_anchors"]
    by_role = {field["role"]: field for field in inspected["fields"]}
    by_value = {field["role"]: field for field in valued["fields"]}
    anchors = {anchor["anchor_id"]: anchor for anchor in inspected["anchors"]}
    evidence = {entry["set_id"]: entry for entry in inspected["evidence_sets"]}
    occurrence_spans = [
        (anchors[key]["start"], anchors[key]["end"]) for key in inspected["occurrence_anchors"]
    ]
    assert occurrence_spans == [(0, 1), (2, 6), (7, 8)]
    for role, actual in (("referent", "A"), ("property", "mean"), ("original_value", "2")):
        field = by_role[role]
        assert field["state"] == "unresolved" and "value" not in field
        (alternative,) = field["alternatives"]
        assert alternative["value"] == dict(kind="text", text=actual)
        context_set = evidence[field["evidence_sets"][0]]
        literal_set = evidence[alternative["evidence_sets"][0]]
        assert context_set["usage"] == "context" and literal_set["usage"] == "literal"
        assert context_set["set_id"] != literal_set["set_id"]
        assert "".join(anchors[key]["source_piece"] for key in literal_set["anchors"]) == actual
        assert by_value[role]["state"] == "present"
        assert by_value[role]["evidence_sets"] == alternative["evidence_sets"]
        assert "alternatives" not in by_value[role]
    assert by_value["value_role"]["value"]["label"] == "mean"
    assert evidence[by_value["value_role"]["evidence_sets"][0]]["usage"] == "classification_cue"
    assert by_value["unit"]["state"] == "unresolved"  # no emitted source absence
    assert by_value["condition"]["state"] == "unstated"  # actual state + inspected scope
    shared = native_group_identity(raw, 0, group)
    assert all(shared in record["computation_dependencies"] for record in (inspected, valued))
    assert "source-reading-branch:inspection" in inspected["computation_dependencies"]
    assert "source-reading-branch:native-group-value" in valued["computation_dependencies"]
    assert result.raw_report is raw and raw.raw["measurement"] == [group]
    assert {item.code for item in result.diagnostics} >= {
        "state_value_conflict",
        "unresolved_value_proposal",
        "unresolved_field",
    }
    observations = native_model_observations(
        raw, context=ctx, family="measurement", context_index=0
    )
    assert any(
        row["field"] == "referent__state" and row["confidence"] == 0.12 for row in observations
    )
    assert all("score" not in record for record in (inspected, valued))


@pytest.mark.parametrize("change", ["missing", "wrong_literal", "untyped", "synthetic"])
def test_unlocated_critical_raw_proposal_cannot_borrow_inspection_context(change):
    group = conflicting_measurement()
    if change == "missing":
        group.pop("referent")
    elif change == "wrong_literal":
        group["referent"] = span(0, 1, "B")
    elif change == "untyped":
        group["referent"] = dict(start=True, end=1, text="A")
    else:
        group["referent"] = span(8, 9, ".")  # outside actual source, even if provider added suffix
    _, _, result = assemble_conflicting([group])
    assert not result.records
    assert any(item.code == "unlocated_occurrence" for item in result.diagnostics)


def test_repeated_group_has_two_readings_and_cueless_classification_stays_unresolved():
    group = conflicting_measurement()
    group.pop("value_role__cue")
    _, _, result = assemble_conflicting([group, group])
    assert len(result.records) == 2
    assert len({record.model_dump()["record_id"] for record in result.records}) == 1
    assert all(fields(record)["value_role"]["state"] == "unresolved" for record in result.records)
    assert all("alternatives" not in fields(record)["value_role"] for record in result.records)


def test_ambiguous_formula_binding_cannot_become_formula_only_after_value_repair():
    ctx = context("x=2 x value")
    pack = family_pack(
        release(), contract="FormulaRecordFields", anchor_role="formula", source_inspection=True
    )
    group = dict(
        formula=span(0, 3, "x=2"),
        formula__state={"text": "unstated"},
        symbol=span(4, 5, "x"),
        symbol__state={"text": "unresolved"},
        meaning__state={"text": "unresolved"},
    )
    result = assemble_records(
        release(),
        ctx,
        pack,
        report(ctx, pack, "formula_context", [group]),
        contract="FormulaRecordFields",
        anchor_role="formula",
        policy_version="test",
        occurrence_policy=OCCURRENCE_POLICY,
    )
    assert not result.records
    assert any(item.code == "unlocated_occurrence" for item in result.diagnostics)


def test_formula_value_proposals_and_inspection_share_actual_binding_first_use():
    ctx = context("x=2 x means value")
    pack = family_pack(
        release(), contract="FormulaRecordFields", anchor_role="formula", source_inspection=True
    )
    group = dict(
        formula=span(0, 3, "x=2"),
        formula__state={"text": "unstated"},
        symbol=span(4, 5, "x"),
        symbol__state={"text": "unresolved"},
        meaning=span(12, 17, "value"),
        meaning__state={"text": "unstated"},
    )
    result = assemble_records(
        release(),
        ctx,
        pack,
        report(ctx, pack, "formula_context", [group]),
        contract="FormulaRecordFields",
        anchor_role="formula",
        policy_version="test",
        occurrence_policy=OCCURRENCE_POLICY,
    )
    assert len(result.records) == 2
    rows = [record.model_dump() for record in result.records]
    assert rows[0]["record_id"] == rows[1]["record_id"]
    assert rows[0]["interpretation_id"] != rows[1]["interpretation_id"]
    for row in rows:
        anchors = {anchor["anchor_id"]: anchor for anchor in row["anchors"]}
        membership = [
            (anchors[key]["start"], anchors[key]["end"]) for key in row["occurrence_anchors"]
        ]
        assert membership == [(0, 3), (0, 1)]


def test_related_literal_proposal_cannot_define_primary_occurrence():
    primary, related = source("A"), source("mean 2", identity=2)
    ctx = NativeSourceContext(
        primary,
        (RelatedNativeSource(related, ContextRelationship.DECLARATION, "actual context"),),
        (SourceSlice(1, 0, 1), SourceSlice(2, 0, 6)),
        "reading",
        "policy",
        "explicit",
    )
    pack = family_pack(
        release(),
        contract="MeasurementRecordFields",
        anchor_role="original_value",
        source_inspection=True,
    )
    group = dict(
        referent=span(0, 1, "A"),
        referent__state={"text": "unstated"},
        property=span(1, 5, "mean"),
        property__state={"text": "unresolved"},
        original_value=span(6, 7, "2"),
        original_value__state={"text": "unstated"},
    )
    result = assemble_records(
        release(),
        ctx,
        pack,
        report(ctx, pack, "measurement", [group]),
        contract="MeasurementRecordFields",
        anchor_role="original_value",
        policy_version="test",
        occurrence_policy=OCCURRENCE_POLICY,
    )
    assert not result.records
    assert any(item.code == "unlocated_occurrence" for item in result.diagnostics)


@pytest.mark.parametrize(
    "family,contract,roles",
    [
        ("assertion", "AssertionRecordFields", ("subject", "predicate", "object")),
        ("measurement", "MeasurementRecordFields", ("referent", "property", "original_value")),
    ],
)
def test_shared_grouping_anchor_cannot_merge_compatible_readings(family, contract, roles):
    ctx = context("A and B have 2")
    groups = tuple(
        NativeRecordGroup(
            (
                RoleInput(roles[0], spans=(LiteralSpan(start, start + 1, letter),)),
                RoleInput(roles[1], spans=(LiteralSpan(8, 12, "have"),)),
                RoleInput(roles[2], spans=(LiteralSpan(13, 14, "2"),)),
            ),
            "independently specified shared-predicate reading",
        )
        for start, letter in ((0, "A"), (6, "B"))
    )
    result = assemble_native_records(
        release(),
        ctx,
        contract=contract,
        occurrence_roles=(roles[1],),
        policy_version="test",
        occurrence_policy=OCCURRENCE_POLICY,
        groups=groups,
    )
    assert len(result.records) == 2
    assert len({record.model_dump()["record_id"] for record in result.records}) == 2
    assert all(len(record.model_dump()["occurrence_anchors"]) == 3 for record in result.records)


def test_formula_bindings_use_first_actual_primary_symbol_and_keep_conflicts_alternative():
    text = "x+x+y x means mean y means count x means median"
    ctx = context(
        text,
        pieces=[
            dict(kind="native_text", item_ref="#/texts/1", source_field="orig", start=0, end=5),
            dict(
                kind="native_text",
                item_ref="#/texts/2",
                source_field="text",
                start=5,
                end=len(text),
            ),
        ],
        items=[dict(self_ref="#/texts/1", orig="x+x+y"), dict(self_ref="#/texts/2", text=text[5:])],
    )
    occurrence = FormulaOccurrence("a" * 64, "#/texts/1", "x+x+y", "x+x+y", "succeeded")
    groups = []
    for symbol_start, symbol, meaning_start, meaning in (
        (6, "x", 14, "mean"),
        (19, "y", 27, "count"),
        (33, "x", 41, "median"),
    ):
        groups.append(
            native_formula_group(
                ctx,
                occurrence,
                scope_pointer="#/groups/1",
                declarations=(
                    RoleInput(
                        "symbol", spans=(LiteralSpan(symbol_start, symbol_start + 1, symbol),)
                    ),
                    RoleInput(
                        "meaning",
                        spans=(LiteralSpan(meaning_start, meaning_start + len(meaning), meaning),),
                    ),
                ),
            )
        )
    result = assemble_native_records(
        release(),
        ctx,
        contract="FormulaRecordFields",
        occurrence_roles=("formula",),
        policy_version="test",
        occurrence_policy=OCCURRENCE_POLICY,
        groups=tuple(groups),
    )
    assert len(result.records) == 3
    rows = [record.model_dump() for record in result.records]
    assert rows[0]["record_id"] == rows[2]["record_id"] != rows[1]["record_id"]
    assert rows[0]["interpretation_id"] != rows[2]["interpretation_id"]
    for row, expected in zip(rows, ((0, 1, "x"), (4, 5, "y"), (0, 1, "x")), strict=True):
        anchor = next(a for a in row["anchors"] if a["anchor_id"] == row["occurrence_anchors"][1])
        assert (anchor["start"], anchor["end"], anchor["source_piece"]) == expected
    unsupported = replace(
        groups[0],
        fields=tuple(
            replace(field, spans=(LiteralSpan(0, 3, "x+x"),)) if field.role == "symbol" else field
            for field in groups[0].fields
        ),
    )
    limited = assemble_native_records(
        release(),
        ctx,
        contract="FormulaRecordFields",
        occurrence_roles=("formula",),
        policy_version="test",
        occurrence_policy=OCCURRENCE_POLICY,
        groups=(unsupported,),
    )
    assert not limited.records and any(
        d.code == "unlocated_occurrence" for d in limited.diagnostics
    )


def test_native_score_projection_preserves_only_actual_uncalibrated_outputs():
    ctx = context("A mean 2")
    pack = family_pack(release(), contract="MeasurementRecordFields", anchor_role="original_value")
    raw = report(
        ctx,
        pack,
        "measurement",
        [
            {
                "referent": {**span(0, 1, "A"), "confidence": 0.91},
                "property": span(2, 6, "mean"),
                "confidence": 0.77,
            }
        ],
    )
    observations = native_model_observations(
        raw, context=ctx, family="measurement", context_index=1
    )
    assert [(row["field"], row["confidence"]) for row in observations] == [
        ("referent", 0.91),
        ("confidence", 0.77),
    ]
    assert observations[0]["raw_output"] == {**span(0, 1, "A"), "confidence": 0.91}
    assert all(row["score_standing"] == "uncalibrated_decoder_output" for row in observations)
    assert observations[0]["dependence_group"] == observations[1]["dependence_group"]


def test_unavailable_factor_policy_is_sealed_not_run_without_probabilities():
    ctx = context("A is mean")
    result = assemble_native_records(
        release(),
        ctx,
        contract="DefinitionRecordFields",
        occurrence_roles=("term",),
        policy_version="test",
        occurrence_policy=OCCURRENCE_POLICY,
        groups=(
            NativeRecordGroup(
                (
                    RoleInput("term", spans=(LiteralSpan(0, 1, "A"),)),
                    RoleInput("defining_text", spans=(LiteralSpan(5, 9, "mean"),)),
                ),
                "explicit fixture reading",
            ),
        ),
    )
    records = [record.model_dump() for record in result.records]
    (row,) = interpret_candidate_readings(records)
    assert row["outcome"] == "not_run" and row["coupling_enabled"] is False
    assert "result" not in row and "request" not in row
    assert row["seal"] and row["dependencies"] == list(result.dependencies)
    assert json.loads(json.dumps(row))["record_id"] == records[0]["record_id"]


@pytest.mark.parametrize("template_name", ["value", "mention", "table"])
def test_three_template_seam_runs_actual_pure_operation_with_retained_event_identity(template_name):
    """A supplied finite test policy; these hand-written potentials are not production fit."""

    def decision(key, value, *, identity=False):
        return ri.Decision(
            key,
            (
                ri.Candidate(
                    value, ri.CandidateKind.LOCAL_NEW if identity else ri.CandidateKind.RESOLVED
                ),
                ri.Candidate(
                    "unresolved", ri.CandidateKind.UNRESOLVED, "source interpretation unresolved"
                ),
            ),
        )

    if template_name == "value":
        decisions = (
            decision("value", "2"),
            decision("property", "mean"),
            decision("referent", "A", identity=True),
            decision("condition", "stated"),
        )
        template = ri.ValuePropertyReferentCondition(*decisions)
    elif template_name == "mention":
        decisions = (
            decision("identity", "A", identity=True),
            decision("type", "statistical-variable"),
            decision("relation", "denotes"),
        )
        template = ri.MentionIdentityTypeRelation("actual-source-mention", *decisions)
    else:
        decisions = (
            decision("header", "mean"),
            decision("row", "A", identity=True),
            decision("cell", "2"),
            decision("unit", "unstated"),
            decision("note", "unstated"),
        )
        template = ri.TableHeaderRowCellUnitNote("actual-native-table", *decisions)
    record = dict(
        record_id="actual-occurrence",
        interpretation_id="actual-reading",
        family="measurement",
        standing="candidate",
        computation_dependencies=("observed", "rejected", "retrieval"),
    )

    def supplied(group):
        assert group.readings == (record,)
        dependencies = tuple(
            ri.Dependency(key, kind, "test-policy-1")
            for key, kind in (
                ("model", ri.DependencyKind.MODEL),
                ("ontology", ri.DependencyKind.ONTOLOGY),
                ("policy", ri.DependencyKind.POLICY),
                ("observed", ri.DependencyKind.OBSERVATION),
                ("rejected", ri.DependencyKind.REJECTED_ALTERNATIVE),
                ("retrieval", ri.DependencyKind.RETRIEVAL),
            )
        )
        return ri.InterpretationRequest(
            template=template,
            potentials=tuple(
                ri.LogPotential(d.key, (d.key,), (0.7, -0.4), ("model", "observed"))
                for d in decisions
            ),
            constraints=(),
            events=(
                ri.RecordEvent(
                    "actual-reading",
                    (tuple(ri.Choice(d.key, d.candidates[0].key) for d in decisions),),
                ),
            ),
            dependencies=dependencies,
            selection=ri.CandidateSelection(
                group.record_id, ("observed", "retrieval"), exclusions=("outside retained scope",)
            ),
            model_dependency_id="model",
            ontology_dependency_id="ontology",
            policy_dependency_id="policy",
        )

    (result,) = interpret_candidate_readings((record,), request_factory=supplied)
    assert result["outcome"] == "completed"
    assert result["result"]["event_probabilities"][0]["event"] == "actual-reading"
    assert result["result"]["event_probabilities"][0]["probability"] == pytest.approx(
        (1 / (1 + math.exp(-1.1))) ** len(decisions)
    )
    assert result["coupling_enabled"] is False and record["standing"] == "candidate"
    assert result["request_digest"] and result["result_digest"] and result["seal"]
    invalid = replace(
        supplied(SimpleNamespace(readings=(record,), record_id="actual-occurrence")),
        dependencies=(),
    )
    with pytest.raises(ValueError, match="omits retained"):
        interpret_candidate_readings((record,), request_factory=lambda _: invalid)
