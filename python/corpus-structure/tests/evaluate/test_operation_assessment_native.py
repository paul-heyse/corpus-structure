"""Actual evaluator pass custody; controlled source, never model-quality evidence."""

import json
from copy import deepcopy
from dataclasses import replace
from typing import Any

import pytest
from evaluation_operation_assessment_native_support import freeze as freeze
from semantic.method_dimensions_native_support import current_guarded_database
from semantic.native_record_fixtures import (
    RecordSourceRecipe,
    complete_contributions,
    contribution_drafts,
)
from semantic.native_record_fixtures import private_source as private_source
from semantic.reference_scenarios import reference_source as reference_source
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.evidence import config_key
from corpus_structure.evaluate.operation_assessment import (
    adjudication_packet,
    author_packet,
    compare_assessments,
    create_reference_set,
    read_evaluation,
    record_pass,
    reference_evaluate,
    review_export,
)
from corpus_structure.evaluate.semantic import ReferenceError
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import seal_cut

_CELL_CONFIGURATION = config_key("private.records", "1", {})


@pytest.mark.parametrize(
    "private_source",
    [RecordSourceRecipe(composition="reference")],
    indirect=True,
    ids=("record-reference",),
)
def test_native_source_only_passes_and_protected_inventory(
    reference_source, record_source_evaluator
):
    source = reference_source
    with record_source_evaluator.begin() as conn:
        created, unit, frame, payload = freeze(conn, source)
        packet = author_packet(conn, unit)
        assert packet["native_contexts"]
        assert "contributions" not in packet and "authors" not in packet
        assert "contribution_ids" not in packet["source_frame"]["evaluation_frame"]
        a = record_pass(
            conn,
            unit_id=unit,
            pass_kind="A",
            actor="independent-A",
            authored=json.dumps(payload).encode(),
            frame=frame,
        )
        with pytest.raises(DBAPIError, match="independent"), conn.begin_nested():
            record_pass(
                conn,
                unit_id=unit,
                pass_kind="B",
                actor="independent-A",
                authored=json.dumps(payload).encode(),
                frame=frame,
            )
        b = record_pass(
            conn,
            unit_id=unit,
            pass_kind="B",
            actor="independent-B",
            authored=json.dumps(payload).encode(),
            frame=frame,
        )
        c_packet = adjudication_packet(conn, unit)
        assert c_packet["adjudication_passes"] == [a, b]
        payload["adjudication_passes"] = [a, b]
        record_pass(
            conn,
            unit_id=unit,
            pass_kind="C",
            actor="independent-C",
            authored=json.dumps(payload).encode(),
            frame=frame,
        )
        exported = review_export(conn, project_id="private-records", set_id=created["set_id"])
        assert exported["judgments_exposed"] and len(exported["judgments"]) == 1
    with source.writer.begin() as conn:
        final = seal_cut(conn, source.run, "operation-grade-final", final=True)
    consolidate_cut(source.writer, final, "operation-grade-output")
    with record_source_evaluator.begin() as conn:
        graded = reference_evaluate(
            conn, project_id="private-records", run_id=source.run, set_id=created["set_id"]
        )
        assert graded.result["protocol"] == "source-operation-evaluation-1"
        assert graded.result["quality_claim"] == "not_established"
        assert graded.result["population_claim"] == "declared_cases_only"
        assert graded.result["units"][0]["cases"][0]["case_id"] == "cell-value"
        assert graded.result["units"][0]["cases"][0]["judgment"] == "unsupported"
        assert "comparisons" not in graded.result["units"][0]
        stored = conn.scalar(
            select(table("eval.reference_evaluation").c.result).where(
                table("eval.reference_evaluation").c.id == graded.id
            )
        )
        assert stored == graded.result
        statement = text(
            "SELECT eval.record_operation_reference_evaluation("
            "'private-records',:r,:s,CAST(:n AS jsonb),CAST(:v AS jsonb))"
        )

        def record(result, set_id=created["set_id"]):
            return conn.scalar(
                statement,
                dict(
                    r=source.run,
                    s=set_id,
                    n=canonical_bytes(graded.reference_snapshot).decode(),
                    v=canonical_bytes(result).decode(),
                ),
            )

        for protocol in ("source-record-evaluation-1", "scientific-evaluation-1", "unknown"):
            invalid = dict(graded.result, protocol=protocol)
            with pytest.raises(DBAPIError, match="trusted set protocol"), conn.begin_nested():
                record(invalid)
        invalid = deepcopy(graded.result)
        invalid["units"][0]["cases"] = []
        with pytest.raises(DBAPIError, match="misses selected source cases"), conn.begin_nested():
            record(invalid)
        # Report-supplied protocol cannot choose operation validation for another trusted set.
        for index, sampling in enumerate(
            (
                {},
                {"record_protocol": "source-record-reference-1"},
                {"operation_protocol": "source-operation-reference-999"},
            )
        ):
            foreign = conn.scalar(
                text(
                    "SELECT eval.create_reference_set('private-records',"
                    ":release,:run,:label,'dev','independent',"
                    "CAST(:sampling AS jsonb))"
                ),
                dict(
                    release=source.prepared.release_id,
                    run=source.run,
                    label=f"foreign protocol control {index}",
                    sampling=canonical_bytes(sampling).decode(),
                ),
            )
            invalid = dict(graded.result, set_id=foreign)
            with pytest.raises(DBAPIError, match="trusted set protocol"), conn.begin_nested():
                record(invalid, foreign)
        assert (
            conn.scalar(
                select(table("eval.reference_evaluation").c.id).where(
                    table("eval.reference_evaluation").c.set_id == created["set_id"]
                )
            )
            == graded.id
        )
    with source.writer.begin() as conn, pytest.raises(DBAPIError):
        conn.execute(text("SELECT authored FROM eval.reference_pass LIMIT 1"))


@pytest.mark.parametrize(
    "private_source",
    [RecordSourceRecipe(composition="reference")],
    indirect=True,
    ids=("record-reference",),
)
def test_heldout_review_export_retains_sealed_inventory_only(
    reference_source, record_source_evaluator
):
    source = reference_source
    with record_source_evaluator.begin() as conn:
        created, unit, frame, payload = freeze(conn, source, "feature_fit")
        ids = []
        for kind in ("A", "B", "C"):
            payload["adjudication_passes"] = ids if kind == "C" else []
            identity = record_pass(
                conn,
                unit_id=unit,
                pass_kind=kind,
                actor=f"independent-{kind}",
                authored=json.dumps(payload).encode(),
                frame=frame,
            )
            if kind != "C":
                ids.append(identity)
        exported = review_export(conn, project_id="private-records", set_id=created["set_id"])
        assert exported["inventory"][0]["adjudicated"]
        assert exported["judgments"] == [] and not exported["judgments_exposed"]


@pytest.mark.parametrize(
    "private_source",
    [RecordSourceRecipe(composition="reference")],
    indirect=True,
    ids=("record-reference",),
)
def test_native_bound_pair_retains_the_actual_operation_and_does_not_credit_uncovered_scope(
    private_source, record_source_evaluator
):
    source = private_source
    with source.writer.begin() as conn:
        complete_contributions(source, conn, contribution_drafts(source))
        source = replace(source, cut=seal_cut(conn, source.run, "paired-source-frame", final=False))
    binding = dict(
        method=source.method.name,
        method_version=source.method.version,
        operation_question="inspect_cell",
        operation_version="1",
    )
    with record_source_evaluator.begin() as conn:
        created, unit, frame, payload = freeze(
            conn,
            source,
            frame_version=2,
            comparison={
                "baseline": dict(binding, operation_version="unavailable"),
                "revised": binding,
            },
        )
        expected: dict[str, Any] = payload["cases"][0]
        expected.update(
            contribution_kind="occurrence",
            alternatives=[{"semantic_type": "table.cell_value", "source_pieces": ["12"]}],
        )
        ids = []
        for kind in ("A", "B", "C"):
            payload["adjudication_passes"] = ids if kind == "C" else []
            identity = record_pass(
                conn,
                unit_id=unit,
                pass_kind=kind,
                actor=f"paired-source-{kind}",
                authored=canonical_bytes(payload),
                frame=frame,
            )
            if kind != "C":
                ids.append(identity)
    with source.writer.begin() as conn:
        final = seal_cut(conn, source.run, "paired-predictions", final=True)
    consolidate_cut(source.writer, final, "paired-operation-assessment")
    with record_source_evaluator.begin() as conn:
        args = dict(project_id="private-records", run_id=source.run, set_id=created["set_id"])
        with pytest.raises(ReferenceError, match="frozen baseline or revised"):
            reference_evaluate(conn, **args)
        baseline = reference_evaluate(conn, comparison_arm="baseline", **args)
        revised = reference_evaluate(conn, comparison_arm="revised", **args)
        assert baseline.result["units"][0]["cases"][0]["judgment"] == "unassessed"
        assert revised.result["units"][0]["cases"][0]["judgment"] == "supported"
        assert revised.result["units"][0]["producer_operations"][0]["question"] == "inspect_cell"
        assert revised.result["comparison_arm"]["cut_id"] == final
        grades = [
            read_evaluation(conn, project_id="private-records", evaluation_id=grade.id)
            for grade in (baseline, revised)
        ]
        changes = compare_assessments(*grades)["changes"]
        assert [entry["case_id"] for entry in changes["not_comparable"]] == ["cell-value"]
        assert not changes["corrected"] and not changes["newly_captured"]
        with pytest.raises(ReferenceError, match="opposite arms"):
            compare_assessments(grades[1], grades[0])


@pytest.mark.parametrize(
    "private_source",
    [RecordSourceRecipe(composition="reference", record_configuration_hash=_CELL_CONFIGURATION)],
    indirect=True,
)
def test_same_operation_comparison_authenticates_each_completed_configuration(
    private_source, record_source_admin, record_source_evaluator
):
    source = private_source
    with source.writer.begin() as conn:
        complete_contributions(source, conn, contribution_drafts(source))
        source = replace(
            source, cut=seal_cut(conn, source.run, "exact-configuration-frame", final=False)
        )
        final = seal_cut(conn, source.run, "exact-configuration-predictions", final=True)
    consolidate_cut(source.writer, final, "exact-configuration-assessment")
    current_guarded_database(record_source_admin)
    binding = dict(
        method=source.method.name,
        method_version=source.method.version,
        operation_question="inspect_cell",
        operation_version="1",
    )
    literal = dict(binding, configuration_hash=_CELL_CONFIGURATION)
    enriched = dict(
        binding,
        configuration_hash=config_key(source.method.name, source.method.version, {"context": True}),
    )
    with record_source_evaluator.begin() as conn:
        for left, right in ((binding, binding), (literal, binding), (literal, literal)):
            with pytest.raises(ReferenceError, match="distinct registered configuration"):
                freeze(
                    conn, source, frame_version=2, comparison={"baseline": left, "revised": right}
                )
        created, unit, frame, payload = freeze(
            conn, source, frame_version=2, comparison={"baseline": literal, "revised": enriched}
        )
        expected: dict[str, Any] = payload["cases"][0]
        expected.update(
            contribution_kind="occurrence",
            alternatives=[{"semantic_type": "table.cell_value", "source_pieces": ["12"]}],
        )
        ids = []
        for kind in ("A", "B", "C"):
            payload["adjudication_passes"] = ids if kind == "C" else []
            identity = record_pass(
                conn,
                unit_id=unit,
                pass_kind=kind,
                actor=f"configuration-source-{kind}",
                authored=canonical_bytes(payload),
                frame=frame,
            )
            if kind != "C":
                ids.append(identity)
    with record_source_evaluator.begin() as conn:
        args = dict(project_id="private-records", run_id=source.run, set_id=created["set_id"])
        with pytest.raises(ReferenceError, match="frozen arm configuration"):
            reference_evaluate(conn, comparison_arm="revised", **args)
        accepted = reference_evaluate(conn, comparison_arm="baseline", **args)
        stored = read_evaluation(conn, project_id="private-records", evaluation_id=accepted.id)
        assert stored["units"][0]["cases"][0]["judgment"] == "supported"
        (report,) = stored["units"][0]["producer_reports"]
        assert report["configuration_hash"] == _CELL_CONFIGURATION

        statement = text(
            "SELECT eval.record_operation_reference_evaluation('private-records',:r,:s,"
            "CAST(:snapshot AS jsonb),CAST(:result AS jsonb))"
        )

        wrong_arm = deepcopy(stored)
        wrong_arm["comparison_arm"].update(name="revised", producers={frame.unit: enriched})
        wrong_report = deepcopy(stored)
        wrong_report["units"][0]["producer_reports"][0]["configuration_hash"] = enriched[
            "configuration_hash"
        ]
        missing_report = deepcopy(stored)
        missing_report["units"][0]["producer_reports"] = []
        for changed in (wrong_arm, wrong_report, missing_report):
            with pytest.raises(DBAPIError, match="frozen arm configuration"), conn.begin_nested():
                conn.scalar(
                    statement,
                    dict(
                        r=source.run,
                        s=created["set_id"],
                        snapshot=canonical_bytes(accepted.reference_snapshot).decode(),
                        result=canonical_bytes(changed).decode(),
                    ),
                )


@pytest.mark.parametrize(
    "private_source",
    [RecordSourceRecipe(composition="reference")],
    indirect=True,
    ids=("record-reference",),
)
def test_native_conditional_proposal_endpoint_cases_preserve_kind_and_source_scope(
    reference_source, record_source_admin, record_source_evaluator
):
    current_guarded_database(record_source_admin)
    source = reference_source
    with record_source_evaluator.begin() as conn:
        _, unit, frame, payload = freeze(conn, source)
        expected: dict[str, Any] = payload["cases"][0]
        expected.update(
            facet="conditional_role",
            contribution_kind="proposal",
            anchor_endpoint_role="mention",
            candidate_selector={"semantic_type": "attribute.role"},
            alternatives=[
                {
                    "semantic_type": "attribute.role",
                    "value": {"kind": "text", "text": "defined_term"},
                    "endpoint_semantics": [
                        {
                            "role": "mention",
                            "anchor_ids": [frame.anchor_ids[0]],
                            "fields": {"source_pieces": ["12"]},
                        }
                    ],
                }
            ],
        )
        identity = record_pass(
            conn,
            unit_id=unit,
            pass_kind="A",
            actor="independent-conditional-A",
            authored=canonical_bytes(payload),
            frame=frame,
        )
        units = table("eval.reference_unit")
        frozen = conn.scalar(select(units.c.context).where(units.c.id == unit))[0]
        statement = text(
            "SELECT eval.record_operation_reference_pass("
            ":u,'B',:actor,:authored,CAST(:frame AS jsonb))"
        )
        # Bypass Python construction: the actual native boundary must reject
        # unsupported kinds and source anchors outside the independent frame.
        invalid_values: list[dict[str, Any]] = [
            dict(contribution_kind=kind) for kind in ("occurrence", "composite", "diagnostic")
        ]
        invalid_values.extend((dict(anchor_endpoint_role=""), dict(anchor_endpoint_role=True)))
        invalid_values.append(dict(anchor_ids=["not-in-frozen-source"]))
        for index, changed in enumerate(invalid_values):
            invalid = deepcopy(payload)
            invalid["cases"][0].update(changed)
            with (
                pytest.raises(DBAPIError, match="independent source/facet authority"),
                conn.begin_nested(),
            ):
                conn.scalar(
                    statement,
                    dict(
                        u=unit,
                        actor=f"invalid-conditional-{index}",
                        authored=canonical_bytes(invalid),
                        frame=canonical_bytes(frozen).decode(),
                    ),
                )
        items = table("eval.reference_item")
        stored = conn.scalar(select(items.c.payload).where(items.c.pass_id == identity))
        assert stored["contribution_kind"] == "proposal"
        assert stored["anchor_endpoint_role"] == "mention"
        assert stored["alternatives"][0]["endpoint_semantics"][0]["anchor_ids"] == [
            frame.anchor_ids[0]
        ]


@pytest.mark.parametrize(
    "private_source",
    [RecordSourceRecipe(composition="reference")],
    indirect=True,
    ids=("record-reference",),
)
@pytest.mark.parametrize("partition", ["final_event_calibration", "final_assessment"])
def test_sealed_access_control_fixture_history_has_no_labels(
    reference_source, record_source_evaluator, partition
):
    """Controlled fixture labels test access only; no valid heldout quality follows."""
    from corpus_structure.evaluate.review_assessments import iter_assessment_review_rows

    source = reference_source
    with record_source_evaluator.begin() as conn:
        created, unit, frame, payload = freeze(
            conn, source, partition, label="sealed-access-control-fixture-not-research-evidence"
        )
        ids = []
        for kind in ("A", "B", "C"):
            payload["adjudication_passes"] = ids if kind == "C" else []
            identity = record_pass(
                conn,
                unit_id=unit,
                pass_kind=kind,
                actor=f"sealed-access-control-fixture-{kind}",
                authored=json.dumps(payload).encode(),
                frame=frame,
            )
            if kind != "C":
                ids.append(identity)
        rows = list(
            iter_assessment_review_rows(
                conn, project_id="private-records", set_id=created["set_id"]
            )
        )
        assert {row["kind"] for row in rows} == {"set", "unit_inventory"}
        assert (
            next(row for row in rows if row["kind"] == "set")["value"]["judgments_exposed"] is False
        )
        assert all("authored_base64" not in row["value"] for row in rows)
    with source.writer.begin() as conn:
        with pytest.raises(DBAPIError) as refused, conn.begin_nested():
            list(
                iter_assessment_review_rows(
                    conn, project_id="private-records", set_id=created["set_id"]
                )
            )
        assert getattr(refused.value.orig, "sqlstate", None) == "42501"


@pytest.mark.parametrize(
    "private_source",
    [RecordSourceRecipe(composition="reference")],
    indirect=True,
    ids=("record-reference",),
)
def test_native_v2_source_opportunities_require_origin_group_and_partition(
    reference_source, record_source_evaluator
):
    from dataclasses import replace

    source = reference_source
    with record_source_evaluator.begin() as conn:
        created, unit, frame, _payload = freeze(conn, source, frame_version=2)
        assert created["sampling"]["source_frame_abi"] == "source-operation-frame-2"
        packet = author_packet(conn, unit)
        assert packet["source_frame"]["protocol"] == "source-operation-frame-2"
        assert (
            packet["source_frame"]["evaluation_frame"]["opportunities"][0]["opportunity_id"]
            == "cell-opportunity-without-output"
        )
        # The new source population is independent of emission IDs.
        assert not frame.contribution_ids
        with pytest.raises(ValueError, match="partition differs"):
            create_reference_set(
                conn,
                project_id="private-records",
                source_run_id=source.run,
                source_cut_id=source.cut,
                label="wrong-partition",
                legacy_split="dev",
                guideline=frame.guideline_version,
                guideline_text="Frozen independent source rubric",
                partition="feature_fit",
                sampling=created["sampling"],
                frames={frame.unit: frame},
            )
        from corpus_structure.evaluate.operation_assessment import OperationEvaluationFrameV2

        assert isinstance(frame, OperationEvaluationFrameV2)
        wrong = replace(frame, source_group="invented-origin")
        with pytest.raises(DBAPIError, match="source opportunities differ"), conn.begin_nested():
            create_reference_set(
                conn,
                project_id="private-records",
                source_run_id=source.run,
                source_cut_id=source.cut,
                label="wrong-origin",
                legacy_split="dev",
                guideline=frame.guideline_version,
                guideline_text="Frozen independent source rubric",
                partition="development",
                sampling=created["sampling"],
                frames={wrong.unit: wrong},
            )


@pytest.mark.parametrize(
    "private_source",
    [RecordSourceRecipe(composition="reference")],
    indirect=True,
    ids=("record-reference",),
)
def test_native_characterization_source_reference_is_blind_and_uses_existing_abc(
    reference_source,
    record_source_evaluator,
):
    from dataclasses import replace

    from corpus_structure.evaluate.operation_assessment import OperationEvaluationFrameV3

    source = reference_source
    with record_source_evaluator.begin() as conn:
        created, unit, frame, payload = freeze(
            conn,
            source,
            frame_version=3,
            label="characterization-source-only",
            frame_source_state="uninspected",
        )
        assert isinstance(frame, OperationEvaluationFrameV3)
        packet = author_packet(conn, unit)
        bound = packet["source_frame"]["evaluation_frame"]
        assert "characterization_view" not in bound and "selected_outputs" not in packet
        assert "outputs" not in bound and packet["native_contexts"]
        passes = []
        for kind in ("A", "B"):
            passes.append(
                record_pass(
                    conn,
                    unit_id=unit,
                    pass_kind=kind,
                    actor=f"characterization-source-{kind}",
                    authored=json.dumps(payload).encode(),
                    frame=frame,
                )
            )
        payload["adjudication_passes"] = passes
        record_pass(
            conn,
            unit_id=unit,
            pass_kind="C",
            actor="characterization-source-C",
            authored=json.dumps(payload).encode(),
            frame=frame,
        )
        assert adjudication_packet(conn, unit)["adjudication_passes"] == passes
        assert created["sampling"]["source_frame_abi"] == "source-operation-frame-3"
        assert frame.opportunities[0].source_state == "uninspected"
        adjudicated = adjudication_packet(conn, unit)
        assert (
            json.loads(adjudicated["authors"][0]["authored"])["cases"][0]["source_state"]
            == "stated"
        )
        invalid = deepcopy(payload)
        invalid["adjudication_passes"] = []
        invalid["cases"][0]["output_reference"] = {
            "layer": {"task_id": 1, "product_key": "layer", "content_digest": "a" * 64},
            "collection": "terms",
            "local_id": "invented",
        }
        frozen = conn.scalar(
            select(table("eval.reference_unit").c.context).where(
                table("eval.reference_unit").c.id == unit
            )
        )[0]
        with pytest.raises(DBAPIError, match="case changes"), conn.begin_nested():
            conn.execute(
                text(
                    "SELECT eval.record_operation_reference_pass("
                    ":unit,'A','forged-author',:authored,CAST(:frame AS jsonb))"
                ),
                dict(unit=unit, authored=json.dumps(invalid).encode(), frame=json.dumps(frozen)),
            )
        # A source opportunity cannot acquire a producer view when a source frame is replaced.
        with pytest.raises(ReferenceError):
            replace(
                frame,
                characterization_view={
                    "task_id": 1,
                    "product_key": "view",
                    "content_digest": "a" * 64,
                },
            )


@pytest.mark.parametrize(
    "private_source",
    [RecordSourceRecipe(composition="reference")],
    indirect=True,
    ids=("record-reference",),
)
def test_native_operation_inspection_pages_retained_cases_and_binds_cursor(
    reference_source,
    record_source_evaluator,
):
    from corpus_structure.evaluate.operation_assessment import inspect_evaluation

    source = reference_source
    with record_source_evaluator.begin() as conn:
        created, unit, frame, payload = freeze(conn, source, label="inspection-controls")
        payload["cases"].append(
            dict(payload["cases"][0], case_id="second-case", facet="second-facet")
        )
        passes = []
        for kind in ("A", "B"):
            passes.append(
                record_pass(
                    conn,
                    unit_id=unit,
                    pass_kind=kind,
                    actor=f"inspection-{kind}",
                    authored=json.dumps(payload).encode(),
                    frame=frame,
                )
            )
        payload["adjudication_passes"] = passes
        record_pass(
            conn,
            unit_id=unit,
            pass_kind="C",
            actor="inspection-C",
            authored=json.dumps(payload).encode(),
            frame=frame,
        )
    with source.writer.begin() as conn:
        final = seal_cut(conn, source.run, "operation-inspection-final", final=True)
    consolidate_cut(source.writer, final, "operation-inspection-output")
    with record_source_evaluator.begin() as conn:
        graded = reference_evaluate(
            conn, project_id="private-records", run_id=source.run, set_id=created["set_id"]
        )
        summary = inspect_evaluation(conn, project_id="private-records", evaluation_id=graded.id)
        assert summary["unit_count"] == 1 and "units" not in summary
        first = inspect_evaluation(
            conn, project_id="private-records", evaluation_id=graded.id, view="cases", limit=1
        )
        assert len(first["items"]) == 1 and first["next_cursor"]
        second = inspect_evaluation(
            conn,
            project_id="private-records",
            evaluation_id=graded.id,
            view="cases",
            limit=1,
            cursor=first["next_cursor"],
        )
        assert len(second["items"]) == 1 and second["next_cursor"] is None
        assert first["items"][0]["item"]["case_id"] != second["items"][0]["item"]["case_id"]
        filtered = inspect_evaluation(
            conn,
            project_id="private-records",
            evaluation_id=graded.id,
            view="cases",
            facet="second-facet",
        )
        assert len(filtered["items"]) == 1
        with pytest.raises(DBAPIError, match="another selection"), conn.begin_nested():
            inspect_evaluation(
                conn,
                project_id="private-records",
                evaluation_id=graded.id,
                view="errors",
                cursor=first["next_cursor"],
            )
