"""Independent miniature source controls; no retained answer resources are opened."""

from copy import deepcopy
from dataclasses import replace
from functools import cache
from types import SimpleNamespace
from typing import Any

import pytest
from evaluate.test_record_alignment import MODEL, PIN, ROOT, frame, reading, role

from corpus_structure.evaluate.record_alignment import RecordSide, align_records
from corpus_structure.evaluate.record_references import (
    PROTOCOL,
    ReferenceError,
    decode_authored,
    decode_frame,
    encode_frame,
    prediction_records,
    reference_inputs,
    report_payload,
)
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import observation_inputs
from corpus_structure.semantic.record_contracts import (
    anchor_identity,
    evidence_set_identity,
    interpretation_identity,
    record_identity,
)
from corpus_structure.semantic.record_projection import RECORD_ROW_TYPES


@cache
def prepared():
    return prepare_release(
        reference_inputs(
            observation_inputs(
                SourceBundle(
                    "statistics_semantic",
                    (
                        SourceArtifact(
                            "statistics_semantic",
                            (ROOT / "domains/statistics/semantic.yaml").read_bytes(),
                        ),
                        SourceArtifact("semantic_core", (MODEL / "core.yaml").read_bytes()),
                        SourceArtifact(
                            "statistics_terminology",
                            (ROOT / "domains/statistics/terminology.yaml").read_bytes(),
                        ),
                    ),
                )
            )
        )
    )


def fixture(family="measurement"):
    row, contexts = reading(family)
    row = deepcopy(row)
    row["record_id"] = record_identity(prepared().release_id, row)
    row["interpretation_id"] = interpretation_identity(row)
    return row, contexts, replace(frame(row), release_id=prepared().release_id)


def authored(row, binding, **extra):
    return canonical_bytes(
        dict(
            protocol=PROTOCOL,
            release_id=prepared().release_id,
            unit_ref=binding.unit,
            guideline=binding.guideline_version,
            reference_policy_version=binding.reference_policy_version,
            prediction_policy_version=binding.prediction_policy_version,
            reason="Independent miniature source reading, no population claim.",
            records=[row],
            **extra,
        )
    )


@pytest.mark.parametrize(
    "family", ["definition", "assertion", "measurement", "table", "formula_context"]
)
def test_independent_record_payload_is_distinct_and_empty_prediction_keeps_denominator(family):
    row, contexts, binding = fixture(family)
    payload = decode_authored(
        prepared(), authored(row, binding), binding, coordinate_texts=contexts
    )
    assert payload["protocol"] == PROTOCOL
    assert "claims" not in payload
    result = align_records(
        RecordSide(binding, payload["records"]),
        RecordSide(binding, ()),
        prepared(),
        coordinate_texts=contexts,
    )
    assert (result.counts["full"].reference, result.counts["full"].prediction) == (1, 0)
    assert decode_frame(encode_frame(binding)) == binding


@pytest.mark.parametrize("change", ["guideline", "release_id", "protocol", "unit_ref"])
def test_wrong_payload_binding_refuses_instead_of_scoring_empty(change):
    row, contexts, binding = fixture()
    raw = dict(__import__("json").loads(authored(row, binding)))
    raw[change] = "wrong"
    with pytest.raises(ValueError):
        decode_authored(prepared(), canonical_bytes(raw), binding, coordinate_texts=contexts)


def test_authored_reference_bytes_and_broken_anchor_are_not_repaired():
    row, contexts, binding = fixture()
    invalid_authored: Any = authored(row, binding).decode()
    with pytest.raises(TypeError, match="bytes"):
        decode_authored(prepared(), invalid_authored, binding, coordinate_texts=contexts)
    row["occurrence_anchors"] = ("not-an-authored-anchor",)
    with pytest.raises(ValueError):
        decode_authored(prepared(), authored(row, binding), binding, coordinate_texts=contexts)


def test_related_attributed_header_preserves_separate_pin_and_requires_explicit_closure():
    row, contexts, binding = fixture("table")
    header = role(row, "header_path")
    evidence = next(
        value for value in row["evidence_sets"] if value["set_id"] in header["evidence_sets"]
    )
    related_pin = dict(
        PIN, source="source:related-header", source_view_id=8, projection_digest="d" * 64
    )
    replacements = {}
    for anchor in row["anchors"]:
        if anchor["anchor_id"] in evidence["anchors"]:
            old = anchor["anchor_id"]
            anchor["pin"] = related_pin
            anchor["binding"] = dict(
                version=2, relationship="selected_context", policy="attributed-selected-source-2"
            )
            anchor["anchor_id"] = anchor_identity(anchor)
            replacements[old] = anchor["anchor_id"]
            for context in contexts:
                if context["pointer"] == anchor["pointer"]:
                    context["pin"] = related_pin
    old_set = evidence["set_id"]
    evidence["anchors"] = tuple(replacements.get(value, value) for value in evidence["anchors"])
    evidence["set_id"] = evidence_set_identity(evidence)
    header["evidence_sets"] = tuple(
        evidence["set_id"] if value == old_set else value for value in header["evidence_sets"]
    )
    row["interpretation_id"] = interpretation_identity(row)
    binding = replace(
        binding,
        anchor_ids=frozenset(value["anchor_id"] for value in row["anchors"]),
        related_pins=(related_pin,),
    )
    assert decode_authored(prepared(), authored(row, binding), binding, coordinate_texts=contexts)[
        "records"
    ]
    with pytest.raises(ValueError, match="source pin"):
        decode_authored(
            prepared(),
            authored(row, binding),
            replace(binding, related_pins=()),
            coordinate_texts=contexts,
        )
    stale = replace(binding, related_pins=(dict(related_pin, product_digest="e" * 64),))
    with pytest.raises(ValueError, match="same native product"):
        decode_authored(prepared(), authored(row, binding), stale, coordinate_texts=contexts)


def projection(rows, *, release_id="release", realization_id="completed"):
    return SimpleNamespace(
        rows={**dict.fromkeys(RECORD_ROW_TYPES, ()), **rows},
        release_id=release_id,
        realization_id=realization_id,
        report_source_view_ids={row["selected_task_id"]: 7 for row in rows["record_report"]},
    )


def test_prediction_adapter_keeps_failed_and_empty_units_and_binds_completed_identity():
    rows = dict(
        record_report=(
            dict(selected_task_id=4, source="unit", outcome="failed", records_present=True),
            dict(selected_task_id=5, source="unit", outcome="empty", records_present=True),
        ),
        record_report_member=(),
    )
    records, reports = prediction_records(
        projection(rows),
        source="unit",
        source_view_id=7,
        release_id="release",
        realization_id="completed",
    )
    assert records == ()
    assert [row["outcome"] for row in reports] == ["failed", "empty"]
    with pytest.raises(ReferenceError, match="completed"):
        prediction_records(
            projection(rows),
            source="unit",
            source_view_id=7,
            release_id="release",
            realization_id="moving-default",
        )


def test_duplicate_public_interpretations_are_not_silently_deduplicated():
    rows = dict(
        record_report=(dict(selected_task_id=4, source="unit"),),
        record_report_member=(
            dict(selected_task_id=4, record_id="record", interpretation_id="reading"),
        )
        * 2,
    )
    with pytest.raises(ReferenceError, match="repeats"):
        prediction_records(
            projection(rows),
            source="unit",
            source_view_id=7,
            release_id="release",
            realization_id="completed",
        )


def test_source_derived_range_scope_accepts_later_span_without_prediction_anchor_inventory():
    row, contexts, binding = fixture()
    scopes = tuple(
        {
            key: value
            for key, value in anchor.items()
            if key in {"pin", "space", "pointer", "precision", "start", "end", "recognition"}
        }
        for anchor in row["anchors"]
    )
    # Freeze source coordinate extents, independently of any output record or ID list.
    scoped = replace(binding, anchor_ids=frozenset(), anchor_scopes=scopes)
    got = align_records(
        RecordSide(scoped, (row,)),
        RecordSide(scoped, (deepcopy(row),)),
        prepared(),
        coordinate_texts=contexts,
    )
    assert got.counts["full"].matched == 1
    outside = deepcopy(scopes)
    outside[0]["start"] = 1
    with pytest.raises(ValueError, match="evaluation cut"):
        align_records(
            RecordSide(replace(scoped, anchor_scopes=outside), (row,)),
            RecordSide(replace(scoped, anchor_scopes=outside), ()),
            prepared(),
            coordinate_texts=contexts,
        )


def test_empty_authored_unit_is_explicit_and_keeps_zero_record_reference_population():
    _, _, binding = fixture()
    payload = dict(__import__("json").loads(authored(fixture()[0], binding)))
    payload["records"] = []
    assert (
        decode_authored(prepared(), canonical_bytes(payload), binding, coordinate_texts=())[
            "records"
        ]
        == ()
    )
    payload.pop("records")
    with pytest.raises(ValueError):
        decode_authored(prepared(), canonical_bytes(payload), binding, coordinate_texts=())


def test_released_record_grade_protocol_is_distinct_from_reference_and_typed():
    row, contexts, binding = fixture()
    result = align_records(
        RecordSide(binding, (row,)), RecordSide(binding, ()), prepared(), coordinate_texts=contexts
    ).as_dict()
    result.update(
        origin_group="one-original-book",
        producer_reports=[],
        gap_evidence=dict(
            unit_id=1,
            pass_id=2,
            frame_id=3,
            source_view_id=7,
            source_run_id=4,
            source_cut_id=5,
            run_id=6,
            cut_id=8,
            cohort="controlled",
            tasks=[],
            gaps=[
                dict(
                    reference_record_id=row["record_id"],
                    family=row["family"],
                    reference_anchor_ids=sorted(a["anchor_id"] for a in row["anchors"]),
                    kind="no_output",
                    earliest_failed_stage="unknown",
                    reading_roles=[],
                    evidence_roles=[],
                    predictions=[],
                )
            ],
        ),
    )
    report = dict(
        protocol="source-record-evaluation-1",
        release_id=prepared().release_id,
        output_realization_id="completed",
        family="source_records",
        comparison_policy="strict-source-occurrence-1",
        grain="accepted_source_record_occurrence",
        tiers=result["tiers"],
        families=result["families"],
        units=[result],
        reference_units_scored=1,
        partition="development",
        sampling_digest="a" * 64,
        quality_claim="not_established",
    )
    assert prepared().validate_json(
        "ReferenceRecordEvaluationReport", canonical_bytes(report_payload(report))
    )
    with pytest.raises(ValueError):
        prepared().validate_json(
            "ReferenceRecordEvaluationReport",
            canonical_bytes(report_payload(dict(report, protocol=PROTOCOL))),
        )
    with pytest.raises(ValueError):
        prepared().validate_json(
            "ReferenceRecordEvaluationReport",
            canonical_bytes(report_payload(dict(report, partition="dev"))),
        )


def test_fitting_credentials_are_separate_and_keep_the_declared_database_target():
    from sqlalchemy.engine import make_url

    from corpus_structure.semantic.runtime import connection_settings
    from corpus_structure.settings import Settings

    settings = Settings(
        database=dict(
            url="postgresql://source:producer-secret@localhost:5434/case",
            fitter_url="postgresql://corpus_sem_fitter:fit-secret@/",
        )
    )
    url = make_url(connection_settings(settings, "fit").database.url)
    assert (url.username, url.password, url.host, url.port, url.database) == (
        "corpus_sem_fitter",
        "fit-secret",
        "localhost",
        5434,
        "case",
    )
    default = settings.model_copy(
        update={"database": settings.database.model_copy(update={"fitter_url": None})}
    )
    assert make_url(connection_settings(default, "fit").database.url).password is None
    bad = settings.model_copy(
        update={
            "database": settings.database.model_copy(
                update={"fitter_url": "postgresql://corpus_sem_fitter@other-host/case"}
            )
        }
    )
    with pytest.raises(ValueError, match="target host"):
        connection_settings(bad, "fit")


def test_prediction_alias_change_refuses_instead_of_becoming_empty_output():
    rows = dict(
        record_report=(
            dict(selected_task_id=4, source="new-alias", outcome="empty", records_present=True),
        ),
        record_report_member=(),
    )
    projected = projection(rows)
    projected.report_source_view_ids = {4: 7}
    with pytest.raises(ReferenceError, match="logical source alias"):
        prediction_records(
            projected,
            source="frozen-alias",
            source_view_id=7,
            release_id="release",
            realization_id="completed",
        )


def test_shared_public_root_counts_once_and_keeps_each_producer_membership():
    from corpus_structure.semantic.record_projection import project_record_reports

    row, _, _ = fixture()
    row["standing"] = "candidate"
    row["interpretation_id"] = interpretation_identity(row)
    reports = tuple(
        dict(
            selected_task_id=task,
            origin_task_id=task,
            cut_id=1,
            source=PIN["source"],
            outcome="produced",
            records=(row,),
        )
        for task in (4, 5)
    )
    rows = project_record_reports(prepared(), reports)
    projected = SimpleNamespace(
        rows=rows,
        release_id=prepared().release_id,
        realization_id="completed",
        report_source_view_ids={4: 7, 5: 7},
    )
    records, outcomes = prediction_records(
        projected,
        source=PIN["source"],
        source_view_id=7,
        release_id=prepared().release_id,
        realization_id="completed",
    )
    assert records == (row,)
    assert len(outcomes) == 2


def test_reference_author_validation_and_agreement_keep_production_policy_distinct():
    from corpus_structure.evaluate.record_references import align_independent_references

    row, contexts, binding = fixture()
    binding = replace(binding, prediction_policy_version="independent-production-policy-2")
    original = deepcopy(row)
    payload = decode_authored(
        prepared(), authored(row, binding), binding, coordinate_texts=contexts
    )
    got = align_independent_references(
        RecordSide(binding, payload["records"]),
        RecordSide(binding, (row,)),
        prepared(),
        coordinate_texts=contexts,
    )
    assert got.counts["full"].matched == 1
    assert got.prediction_policy_version == binding.reference_policy_version
    assert (
        row == original and binding.prediction_policy_version == "independent-production-policy-2"
    )
    wrong = deepcopy(row)
    wrong["policy_version"] = binding.prediction_policy_version
    wrong["interpretation_id"] = interpretation_identity(wrong)
    with pytest.raises(ValueError, match="acceptance policy"):
        decode_authored(prepared(), authored(wrong, binding), binding, coordinate_texts=contexts)


def test_document_producer_absence_report_is_not_a_source_view_prediction():
    projected = SimpleNamespace(
        release_id="release",
        realization_id="completed",
        report_source_view_ids={4: 7},
        rows=dict(
            dict.fromkeys(RECORD_ROW_TYPES, ()),
            record_report=(
                dict(
                    selected_task_id=3,
                    source="document.pdf",
                    records_present=False,
                    outcome="produced",
                ),
                dict(
                    selected_task_id=4, source="source-view", records_present=True, outcome="empty"
                ),
            ),
            record_report_member=(),
        ),
    )
    records, reports = prediction_records(
        projected,
        source="source-view",
        source_view_id=7,
        release_id="release",
        realization_id="completed",
    )
    assert records == () and len(reports) == 1 and reports[0]["selected_task_id"] == 4


def test_prediction_adopts_native_overlay_without_mutating_private_interpretation():
    from corpus_structure.semantic.record_projection import (
        project_record_reports,
        reconstruct_record,
    )

    row, _, _ = fixture()
    row["standing"] = "candidate"
    rows = project_record_reports(
        prepared(),
        (
            dict(
                selected_task_id=4,
                origin_task_id=4,
                cut_id=1,
                source=PIN["source"],
                outcome="produced",
                records=(row,),
            ),
        ),
    )
    rows = dict(
        rows,
        record_admission=tuple(
            replace(admission, decision="accepted") for admission in rows["record_admission"]
        ),
    )
    projected = SimpleNamespace(
        rows=rows,
        release_id=prepared().release_id,
        realization_id="completed",
        report_source_view_ids={4: 7},
    )
    predictions, _ = prediction_records(
        projected,
        source=PIN["source"],
        source_view_id=7,
        release_id=prepared().release_id,
        realization_id="completed",
    )
    assert len(predictions) == 1 and predictions[0]["standing"] == "accepted"
    assert predictions[0]["interpretation_id"] == row["interpretation_id"]
    assert predictions[0]["record_id"] == row["record_id"]
    assert reconstruct_record(rows, row["record_id"], row["interpretation_id"]) == row


def test_resolver_is_prediction_authority_and_raw_report_stays_diagnostic():
    from corpus_structure.semantic.record_projection import project_record_reports

    raw, _, _ = fixture()
    raw["standing"] = "candidate"
    resolved = deepcopy(raw)
    resolved["computation_dependencies"] = ("reading-resolution:recipe",)
    resolved["interpretation_id"] = interpretation_identity(resolved)
    rows = project_record_reports(
        prepared(),
        tuple(
            dict(
                selected_task_id=task,
                origin_task_id=task,
                cut_id=1,
                source=PIN["source"],
                outcome="produced",
                records=(record,),
            )
            for task, record in ((4, raw), (5, resolved))
        ),
    )
    projected = SimpleNamespace(
        rows=rows,
        release_id=prepared().release_id,
        realization_id="completed",
        report_source_view_ids={4: 7, 5: 7},
    )
    predictions, reports = prediction_records(
        projected,
        source=PIN["source"],
        source_view_id=7,
        release_id=prepared().release_id,
        realization_id="completed",
        report_method_names={4: "extract.m1_candidates", 5: "resolve.m1_readings"},
    )
    assert predictions == (resolved,)
    assert [report["selected_task_id"] for report in reports] == [5]


def test_empty_or_absent_resolver_report_never_falls_back_to_raw_predictions():
    from corpus_structure.semantic.record_projection import project_record_reports

    row, _, _ = fixture()
    row["standing"] = "candidate"
    rows = project_record_reports(
        prepared(),
        (
            dict(
                selected_task_id=4,
                origin_task_id=4,
                cut_id=1,
                source=PIN["source"],
                outcome="produced",
                records=(row,),
            ),
            dict(
                selected_task_id=5,
                origin_task_id=5,
                cut_id=1,
                source=PIN["source"],
                outcome="empty",
                records=(),
            ),
        ),
    )
    projected = SimpleNamespace(
        rows=rows,
        release_id=prepared().release_id,
        realization_id="completed",
        report_source_view_ids={4: 7, 5: 7},
    )
    methods = {4: "extract.m1_candidates", 5: "resolve.m1_readings", 6: "resolve.m1_readings"}
    for selected in ((4, 5), (4, 6)):
        predictions, reports = prediction_records(
            projected,
            source=PIN["source"],
            source_view_id=7,
            release_id=prepared().release_id,
            realization_id="completed",
            selected_tasks=selected,
            report_method_names=methods,
        )
        assert predictions == ()
        assert [report["selected_task_id"] for report in reports] == ([5] if 5 in selected else [])
