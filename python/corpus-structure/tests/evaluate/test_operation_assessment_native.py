"""Actual evaluator pass custody; controlled source, never model-quality evidence."""

import json
from copy import deepcopy
from dataclasses import asdict, replace

import pytest
from evaluate.test_record_references_native import create_case, expected_reading, native_pass
from evaluate.test_record_references_native import reference_source as reference_source
from semantic.conftest import semantic_db_engine as semantic_db_engine
from semantic.conftest import semantic_evaluator_engine as semantic_evaluator_engine
from semantic.conftest import semantic_writer_engine as semantic_writer_engine
from semantic.test_private_records import private_source as private_source
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.evaluate.operation_assessment import (
    PROTOCOL,
    OperationCase,
    OperationEvaluationFrame,
    adjudication_packet,
    author_packet,
    create_reference_set,
    project_reference_field,
    record_pass,
    review_export,
)
from corpus_structure.evaluate.record_references import assign_origin, source_binding
from corpus_structure.evaluate.semantic import split_documents
from corpus_structure.evaluate.split import SplitConfig
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.record_contracts import anchor_identity


def freeze(conn, case, partition="development"):
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
    created = create_reference_set(
        conn,
        project_id="private-records",
        source_run_id=case.run,
        source_cut_id=case.cut,
        label="operation-source-only",
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
    return created, unit, frame, json.loads(json.dumps(payload))


def test_native_source_only_passes_and_protected_inventory(
    reference_source, semantic_evaluator_engine
):
    source = reference_source
    with semantic_evaluator_engine.begin() as conn:
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
    with source.writer.begin() as conn, pytest.raises(DBAPIError):
        conn.execute(text("SELECT authored FROM eval.reference_pass LIMIT 1"))


def test_heldout_review_export_retains_sealed_inventory_only(
    reference_source, semantic_evaluator_engine
):
    source = reference_source
    with semantic_evaluator_engine.begin() as conn:
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


def test_native_exact_field_projection_authenticates_subject_map_and_alternatives(
    reference_source, semantic_evaluator_engine
):
    from corpus_structure.orchestrate.commands import finalize_bound_run

    source = reference_source
    finalize_bound_run(source.writer, source.run, "projection-completed-source")
    with semantic_evaluator_engine.begin() as conn:
        _, old_unit, old_reading, old_frame = create_case(conn, source, "development")
        a = native_pass(conn, old_unit, old_reading, old_frame, "A", "old-independent-A")
        b = native_pass(conn, old_unit, old_reading, old_frame, "B", "old-independent-B")
        c = native_pass(conn, old_unit, old_reading, old_frame, "C", "old-independent-C", (a, b))
        frames = table("eval.reference_frame")
        old_frame_id = conn.scalar(select(frames.c.id).where(frames.c.pass_id == c))
        _, unit, frame, payload = freeze(conn, source)
        projection = project_reference_field(
            conn,
            prediction_run_id=source.run,
            pass_id=c,
            frame_id=old_frame_id,
            record_id=old_reading["record_id"],
            field_index=0,
            question="value",
        )
        assert projection["source_adjudication_passes"] == [a, b]
        expected = dict(
            payload["cases"][0],
            anchor_ids=projection["correspondence"]["anchor_ids"],
            alternatives=projection["expected_alternatives"],
            reference_projection=projection,
        )
        payload["cases"] = [expected]
        record_pass(
            conn,
            unit_id=unit,
            pass_kind="A",
            actor="projected-independent-A",
            authored=json.dumps(payload).encode(),
            frame=frame,
        )
        derived_set = create_reference_set(
            conn,
            project_id="private-records",
            source_run_id=source.run,
            source_cut_id=source.cut,
            label="derived-exact-independent-fields",
            legacy_split="dev",
            guideline=frame.guideline_version,
            guideline_text="Exact independent field projection, without new authors.",
            partition="development",
            frames={frame.unit: frame},
            sampling=dict(
                seed=1,
                strata={frame.unit: "projected-independent-field"},
                inclusion_probabilities={frame.unit: 1},
                provenance={"source": "immutable independently authored original C field"},
                cohort="native-controls",
            ),
        )
        units = table("eval.reference_unit")
        derived_unit = conn.scalar(
            select(units.c.id).where(units.c.set_id == derived_set["set_id"])
        )
        derived = dict(
            payload,
            reference_derivation={
                "protocol": "exact-independent-field-projection-1",
                "source_pass_ids": [c],
            },
        )
        derived_id = record_pass(
            conn,
            unit_id=derived_unit,
            pass_kind="C",
            actor=f"derivedprojection:C{c}:fixture",
            authored=json.dumps(derived).encode(),
            frame=frame,
        )
        passes = table("eval.reference_pass")
        assert conn.execute(
            select(passes.c.pass_kind).where(passes.c.unit_id == derived_unit)
        ).scalars().all() == ["C"]
        assert derived_id is not None
        mixed = json.loads(json.dumps(derived))
        mixed["cases"].append(
            dict(payload["cases"][0], case_id="unproved-new-case", reference_projection=None)
        )
        with pytest.raises(DBAPIError, match="derived C"), conn.begin_nested():
            record_pass(
                conn,
                unit_id=derived_unit,
                pass_kind="C",
                actor=f"derivedprojection:C{c}:fixture",
                authored=json.dumps(mixed).encode(),
                frame=frame,
            )
        for defect in ("malformed_map", "substituted_field", "altered_value"):
            changed = deepcopy(payload)
            if defect == "malformed_map":
                changed["cases"][0]["reference_projection"]["correspondence"] = {"anchor_ids": []}
            elif defect == "substituted_field":
                changed["cases"][0]["reference_projection"]["source_field_index"] = 1
                changed["cases"][0]["reference_projection"]["source_field"] = old_reading["fields"][
                    1
                ]
            else:
                changed["cases"][0]["alternatives"] = [{"source_pieces": ["99"]}]
            with pytest.raises(DBAPIError), conn.begin_nested():
                record_pass(
                    conn,
                    unit_id=unit,
                    pass_kind="B",
                    actor="projected-independent-B",
                    authored=json.dumps(changed).encode(),
                    frame=frame,
                )
        # Same spelling in another source region cannot inherit this field's truth.
        views = table("kb.source_view")
        other = conn.execute(select(views).where(views.c.id == source.other_view)).mappings().one()
        pin = dict(
            frame.pin,
            source=source_binding(
                conn, source_run_id=source.run, source_view_id=other["id"], source_cut_id=source.cut
            ),
            source_view_id=other["id"],
            projection_digest=other["projection_digest"],
            recipe_digest=other["recipe_digest"],
        )
        anchor = dict(
            pin=pin,
            space="native",
            pointer=source.sibling,
            precision="exact",
            start=0,
            end=2,
            source_piece="12",
        )
        anchor["anchor_id"] = anchor_identity(anchor)
        foreign = replace(
            frame,
            unit=other["key"],
            pin=pin,
            anchor_ids=(anchor["anchor_id"],),
            anchor_scopes=(
                {
                    key: value
                    for key, value in anchor.items()
                    if key not in {"anchor_id", "source_piece"}
                },
            ),
        )
        created = create_reference_set(
            conn,
            project_id="private-records",
            source_run_id=source.run,
            source_cut_id=source.cut,
            label="foreign-source-projection-control",
            legacy_split="dev",
            guideline=foreign.guideline_version,
            guideline_text="Exact independent foreign source control.",
            partition="development",
            frames={foreign.unit: foreign},
            sampling=dict(
                seed=1,
                strata={foreign.unit: "foreign-source"},
                inclusion_probabilities={foreign.unit: 1},
                provenance={"source": "different actual native region"},
                cohort="native-controls",
            ),
        )
        units = table("eval.reference_unit")
        foreign_id = conn.scalar(select(units.c.id).where(units.c.set_id == created["set_id"]))
        changed = deepcopy(payload)
        changed["unit_ref"] = foreign.unit
        changed["cases"][0]["anchor_ids"] = [anchor["anchor_id"]]
        with pytest.raises(DBAPIError, match="projection"), conn.begin_nested():
            record_pass(
                conn,
                unit_id=foreign_id,
                pass_kind="A",
                actor="foreign-independent-A",
                authored=json.dumps(changed).encode(),
                frame=foreign,
            )
