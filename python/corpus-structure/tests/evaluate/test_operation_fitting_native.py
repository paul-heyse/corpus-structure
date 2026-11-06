"""Owned fit lifecycle over actual frozen source contributions and independent C passes."""

import json
from copy import deepcopy
from dataclasses import asdict, replace
from typing import Any

import pytest
from semantic import native_record_fixtures as sources
from semantic.conftest import semantic_db_engine as semantic_db_engine
from semantic.conftest import semantic_evaluator_engine as semantic_evaluator_engine
from semantic.conftest import semantic_reader_engine as semantic_reader_engine
from semantic.conftest import semantic_writer_engine as semantic_writer_engine
from semantic.native_record_fixtures import private_source as private_source
from semantic.reference_scenarios import private_source_options as private_source_options
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.evaluate.operation_assessment import (
    PROTOCOL,
    OperationCase,
    OperationEvaluationFrame,
    create_reference_set,
    record_pass,
    reference_evaluate,
)
from corpus_structure.evaluate.operation_fitting import (
    fit_native_operation_event,
    fit_operation_event,
    read_native_fit,
    read_native_frame,
)
from corpus_structure.evaluate.record_references import assign_origin, source_binding
from corpus_structure.evaluate.semantic import split_documents
from corpus_structure.evaluate.split import SplitConfig
from corpus_structure.semantic.contributions import contribution_identity, occurrence_identity
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.operations import seal_cut
from corpus_structure.semantic.record_contracts import anchor_identity


def _development_grade(case, evaluator):
    batch = sources.contribution_drafts(case)
    assert batch.contributions is not None and batch.contribution_operations is not None
    head: dict[str, Any] = dict(
        batch.contributions[0], semantic_type="definition.term", value=source_value("12")
    )
    head.pop("contribution_id")
    head["contribution_id"] = contribution_identity(head)
    tail_anchor: dict[str, Any] = deepcopy(head["anchors"][0])
    tail_anchor["pointer"] = case.table + "/data/table_cells/1"
    tail_anchor["anchor_id"] = anchor_identity(tail_anchor)
    tail: dict[str, Any] = dict(
        head,
        item_key="cell/1",
        anchors=(tail_anchor,),
        occurrence_id=occurrence_identity((tail_anchor,)),
    )
    tail.pop("contribution_id")
    tail["contribution_id"] = contribution_identity(tail)
    relations: list[dict[str, Any]] = []
    for i, confidence in enumerate((0.1, 0.2, 0.8, 0.9)):
        endpoints = (head, tail) if i >= 2 else (tail, head)
        relation = dict(
            head,
            kind="relation",
            semantic_type="relation.defined_by",
            item_key="relation/" + str(i),
            anchors=(),
            endpoints=tuple(
                dict(role=role, contribution_id=value["contribution_id"])
                for role, value in zip(("head", "tail"), endpoints, strict=True)
            ),
            score_state="native",
            score=source_value(confidence),
        )
        relation.pop("contribution_id")
        relation.pop("occurrence_id")
        relation["contribution_id"] = contribution_identity(relation)
        relations.append(relation)
    assert batch.contribution_coordinate_texts is not None
    coordinates = (
        *batch.contribution_coordinate_texts,
        dict(pin=tail_anchor["pin"], space="native", pointer=tail_anchor["pointer"], text="12"),
    )
    batch = replace(
        batch,
        contributions=(head, tail, *relations),
        contribution_operations=(
            dict(batch.contribution_operations[0], inspected_count=2, emitted_count=6),
        ),
        contribution_coordinate_texts=coordinates,
    )
    with case.writer.begin() as conn:
        sources.complete_contributions(case, conn, batch)
        case.cut = seal_cut(conn, case.run, "event-source-ready", final=False)
    with evaluator.begin() as conn:
        uri = conn.scalar(
            select(table("kb.document").c.source_uri).where(
                table("kb.document").c.id == case.view_row["document_id"]
            )
        )
        assign_origin(
            conn,
            project_id="private-records",
            origin_group="one-development-book",
            partition="development",
            source_uris=(uri,),
            provenance={"selection": "independent source fixture"},
        )
        split_documents(
            conn,
            "private-records",
            SplitConfig(forced_dev={uri: "shared development source"}),
            release_id=case.prepared.release_id,
        )
        reference_pin = dict(
            head["pin"],
            source=source_binding(
                conn,
                source_run_id=case.run,
                source_view_id=case.view,
                source_cut_id=case.cut,
            ),
        )
        endpoint_scopes = tuple(
            dict(
                pin=reference_pin,
                space="native",
                pointer=f"{case.table}/data/table_cells/{cell}",
                precision="exact",
                start=0,
                end=2,
            )
            for cell in (0, 1)
        )
        endpoint_ids = tuple(
            anchor_identity(dict(scope, source_piece="12")) for scope in endpoint_scopes
        )
        assert endpoint_ids == (head["anchors"][0]["anchor_id"], tail_anchor["anchor_id"])
        frame = OperationEvaluationFrame(
            unit=case.view_row["key"],
            release_id=case.prepared.release_id,
            guideline_version="defined-by-guideline-1",
            rubric_version="exact-endpoints-scope-1",
            context_policy="native-source-only-1",
            operation_question="inspect_cell",
            operation_version="1",
            domain="scientific-source",
            direction="output_first",
            pin=reference_pin,
            anchor_ids=endpoint_ids,
            anchor_scopes=endpoint_scopes,
            contribution_ids=tuple(r["contribution_id"] for r in relations),
        )
        created = create_reference_set(
            conn,
            project_id="private-records",
            source_run_id=case.run,
            source_cut_id=case.cut,
            label="event-development",
            legacy_split="dev",
            guideline=frame.guideline_version,
            guideline_text=(
                "Assess defined_by using both independently fixed native endpoint scopes."
            ),
            partition="development",
            frames={frame.unit: frame},
            sampling=dict(
                seed=1,
                strata={frame.unit: "relation"},
                inclusion_probabilities={frame.unit: 1},
                provenance={"selection": "controlled source"},
                cohort="shared-source",
            ),
        )
        unit = conn.scalar(
            select(table("eval.reference_unit").c.id).where(
                table("eval.reference_unit").c.set_id == created["set_id"]
            )
        )
        alternatives = (
            {
                "semantic_type": "relation.defined_by",
                "endpoint_semantics": [
                    {"role": "head", "anchor_ids": [head["anchors"][0]["anchor_id"]], "fields": {}},
                    {"role": "tail", "anchor_ids": [tail_anchor["anchor_id"]], "fields": {}},
                ],
            },
        )
        cases = tuple(
            OperationCase(
                case_id="defined-by-" + str(i),
                facet="defined_by_correctness",
                anchor_ids=(),
                inspected_scope="native/table/cell-0-and-cell-1",
                source_state="stated",
                judgment="supported",
                alternatives=alternatives,
                explanation="Head is independently fixed physical cell0 and tail is cell1.",
                assessor_provenance={"assistance": "none"},
                contribution_kind="relation",
                contribution_id=r["contribution_id"],
            )
            for i, r in enumerate(relations)
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
            reason="Independent exact endpoints, including reversed emitted relations.",
            cases=[asdict(c) for c in cases],
            adjudication_passes=[],
        )
        parents = []
        for kind in ("A", "B", "C"):
            payload["adjudication_passes"] = parents if kind == "C" else []
            identity = record_pass(
                conn,
                unit_id=unit,
                pass_kind=kind,
                actor="source-author-" + kind,
                authored=json.dumps(payload).encode(),
                frame=frame,
            )
            if kind != "C":
                parents.append(identity)
    with case.writer.begin() as conn:
        cut = seal_cut(conn, case.run, "event-final", final=True)
    consolidate_cut(case.writer, cut, "event-grade-output")
    with evaluator.begin() as conn:
        return reference_evaluate(
            conn, project_id="private-records", run_id=case.run, set_id=created["set_id"]
        )


def test_native_operation_event_fit_retains_exact_frame_and_blocks_forgery(
    private_source, semantic_evaluator_engine, semantic_reader_engine
):
    grade = _development_grade(private_source, semantic_evaluator_engine)
    fitted = fit_native_operation_event(
        semantic_evaluator_engine, project_id="private-records", evaluation_id=grade.id
    )
    assert fitted["result"]["status"] == "fitted"
    assert fitted["result"]["positive"] == fitted["result"]["negative"] == 2
    assert fitted["cut_id"] == fitted["frame"]["cut_id"]
    with semantic_reader_engine.begin() as conn:
        runtime = read_native_fit(conn, project_id="private-records", fit_id=fitted["id"])
        assert runtime["parameters"] is not None and "judgment" not in json.dumps(runtime)
        with pytest.raises(DBAPIError, match="protected"), conn.begin_nested():
            read_native_fit(conn, project_id="private-records", fit_id=fitted["id"], protected=True)
        with pytest.raises(DBAPIError), conn.begin_nested():
            conn.execute(select(table("eval.operation_event_fit")))
    with semantic_evaluator_engine.begin() as conn:
        native, frame = read_native_frame(
            conn, project_id="private-records", evaluation_id=grade.id
        )
        result = fit_operation_event(frame).model_dump(mode="json")
        assert [o.judgment for o in frame.observations] == [
            "unsupported",
            "unsupported",
            "supported",
            "supported",
        ]
        assert frame.observations[0].features == (0.1, 1.0, 1.0, 1.0)
        statement = text(
            "SELECT eval.record_operation_event_fit(:p,:e,CAST(:f AS jsonb),CAST(:r AS jsonb))"
        )
        mutations = [("cut", dict(native, cut_id=native["cut_id"] + 1), result)]
        wrong = deepcopy(result)
        wrong["parameters"]["coefficients"].append(1)
        mutations.append(("shape", native, wrong))
        wrong = deepcopy(result)
        wrong["parameters"]["judgment"] = "supported"
        mutations.append(("label leak", native, wrong))
        wrong = deepcopy(result)
        wrong["positive"] += 1
        mutations.append(("class counts", native, wrong))
        wrong = deepcopy(result)
        wrong["predictions"][0]["event_id"] = "foreign-event"
        mutations.append(("event identity", native, wrong))
        for field in ("regularization_c", "tolerance", "max_iterations"):
            wrong = deepcopy(result)
            wrong["parameters"]["algorithm"][field] = None
            mutations.append(("null algorithm " + field, native, wrong))
        for field, value in (
            ("prior_probability", 2),
            ("prior_probability", None),
            ("fitted_probability", -1),
            ("fitted_probability", None),
        ):
            wrong = deepcopy(result)
            wrong["predictions"][0][field] = value
            mutations.append(("prediction " + field, native, wrong))
        for _label, captured, product in mutations:
            with pytest.raises(DBAPIError), conn.begin_nested():
                conn.execute(
                    statement,
                    dict(
                        p="private-records",
                        e=grade.id,
                        f=json.dumps(captured),
                        r=json.dumps(product),
                    ),
                )
