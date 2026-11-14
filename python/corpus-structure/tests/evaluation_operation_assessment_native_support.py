"""Shared controlled inputs and builders for evaluation operation assessment native support."""

from dataclasses import asdict

from semantic.reference_scenarios import expected_reading
from sqlalchemy import select

from corpus_structure.evaluate.operation_assessment import (
    PROTOCOL,
    OperationCase,
    OperationEvaluationFrame,
    create_reference_set,
)
from corpus_structure.evaluate.record_references import assign_origin, source_binding
from corpus_structure.evaluate.semantic import split_documents
from corpus_structure.evaluate.split import SplitConfig
from corpus_structure.semantic.metadata import table


def freeze(
    conn,
    case,
    partition="development",
    label="operation-source-only",
    *,
    frame_version=1,
    comparison=None,
    frame_source_state="stated",
):
    uri = conn.scalar(
        select(table("kb.document").c.source_uri).where(
            table("kb.document").c.id == case.view_row["document_id"]
        )
    )
    origins = table("eval.reference_origin_source")
    if (
        conn.scalar(
            select(origins.c.origin_group).where(
                origins.c.project_id == "private-records", origins.c.source_uri == uri
            )
        )
        is None
    ):
        assign_origin(
            conn,
            project_id="private-records",
            origin_group="operation-fixture-origin",
            partition=partition,
            source_uris=(uri,),
            provenance={"source": "independent two-cell control"},
        )
    splits = table("eval.document_split")
    if (
        conn.scalar(
            select(splits.c.id).where(
                splits.c.project_id == "private-records", splits.c.source_uri == uri
            )
        )
        is None
    ):
        split_documents(
            conn,
            "private-records",
            SplitConfig(forced_dev={uri: "controlled source"}),
            release_id=case.prepared.release_id,
        )
    logical = source_binding(
        conn, source_run_id=case.run, source_view_id=case.view, source_cut_id=case.cut
    )
    reading, old_frame = expected_reading(case, logical)
    frame = OperationEvaluationFrame(
        unit=old_frame.unit,
        release_id=old_frame.release_id,
        guideline_version="operation-guideline-1",
        rubric_version="cell-value-1",
        context_policy="native-source-only-1",
        operation_question="recover_returned_local_contributions",
        operation_version="retained-native-contributions-1",
        domain="scientific-source",
        direction="source_first",
        pin=old_frame.pin,
        anchor_ids=tuple(anchor["anchor_id"] for anchor in reading["anchors"]),
        anchor_scopes=old_frame.anchor_scopes,
    )
    if frame_version == 2:
        from corpus_structure.evaluate.operation_assessment import (
            OperationEvaluationFrameV2,
            OperationSourceOpportunity,
        )

        frame = OperationEvaluationFrameV2(
            **asdict(frame),
            source_group="operation-fixture-origin",
            partition=partition,
            inspected_scope="two-cell native source control",
            opportunities=(
                OperationSourceOpportunity(
                    "cell-value" if comparison else "cell-opportunity-without-output",
                    case.view,
                    0,
                    2,
                    "value" if comparison else "location",
                    "stated",
                ),
            ),
        )
    if frame_version == 3:
        from corpus_structure.evaluate.operation_assessment import (
            CharacterizationSourceOpportunity,
            OperationEvaluationFrameV3,
        )

        projection = case.view_row["projection"]
        piece = next(
            p for p in projection["pieces"] if p["kind"] == "native_text" and p["end"] > p["start"]
        )
        frame = OperationEvaluationFrameV3(
            **asdict(frame),
            source_group="operation-fixture-origin",
            partition=partition,
            inspected_scope="independently selected native source piece",
            opportunities=(
                CharacterizationSourceOpportunity(
                    "cell-value",
                    (
                        dict(
                            source_view_id=case.view,
                            projection=case.view_row["projection_digest"],
                            native_pointer=piece["item_ref"],
                            start=piece["start"],
                            end=piece["end"],
                        ),
                    ),
                    "value",
                    frame_source_state,
                ),
            ),
        )
    created = create_reference_set(
        conn,
        project_id="private-records",
        source_run_id=case.run,
        source_cut_id=case.cut,
        label=label,
        legacy_split="dev",
        guideline=frame.guideline_version,
        guideline_text="Transcribe only independently selected source cell.",
        partition=partition,
        frames={frame.unit: frame},
        sampling=dict(
            seed=1,
            strata={frame.unit: "body_cell"},
            inclusion_probabilities={frame.unit: 1},
            provenance={"selection": "source-only controlled cell"},
            cohort="native-controls",
            **(
                {
                    "comparison_arms": {
                        arm: {frame.unit: binding} for arm, binding in comparison.items()
                    }
                }
                if comparison
                else {}
            ),
        ),
    )
    units = table("eval.reference_unit")
    unit = conn.scalar(select(units.c.id).where(units.c.set_id == created["set_id"]))
    expected = OperationCase(
        case_id="cell-value",
        facet="value",
        anchor_ids=(frame.anchor_ids[0],),
        inspected_scope="controlled/table/cell-0",
        source_state="stated",
        judgment="supported",
        alternatives=({"value": {"kind": "text", "text": "12"}},),
        explanation="The source cell independently spells 12.",
        assessor_provenance={"assistance": "none"},
        opportunity_id="cell-value" if frame_version == 3 else None,
        required_family="native.spatial" if frame_version == 3 else None,
    )
    payload = dict(
        protocol=PROTOCOL,
        release_id=frame.release_id,
        unit_ref=frame.unit,
        guideline=frame.guideline_version,
        rubric_version=frame.rubric_version,
        context_policy=frame.context_policy,
        operation_question=frame.operation_question,
        operation_version=frame.operation_version,
        domain=frame.domain,
        direction=frame.direction,
        reason="Controlled independent source-only pass",
        cases=[asdict(expected)],
        adjudication_passes=[],
    )
    return created, unit, frame, payload
