"""Native source/role admission for the two model-question assessment tasks."""

import json
from copy import deepcopy
from dataclasses import asdict

import pytest
from evaluation_operation_assessment_native_support import freeze
from semantic.native_record_fixtures import RecordSourceRecipe
from semantic.native_record_fixtures import private_source as private_source
from semantic.reference_scenarios import reference_source as reference_source
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.evaluate.operation_assessment import OperationCase, OperationEvaluationFrameV3


@pytest.mark.parametrize(
    "private_source",
    [
        RecordSourceRecipe(
            composition="reference-characterization", additional_methods=("native-binding",)
        )
    ],
    indirect=True,
)
@pytest.mark.parametrize("task,role", [("host_choice", "host"), ("referent_choice", "referent")])
def test_native_choice_task_admits_exact_source_and_refuses_scheme_role_or_source_changes(
    reference_source, record_source_evaluator, task, role
):
    with record_source_evaluator.begin() as conn:
        _created, unit, frame, payload = freeze(
            conn, reference_source, frame_version=3, label="choice-native-" + task
        )
        assert isinstance(frame, OperationEvaluationFrameV3)
        reference = dict(
            version="characterization-task-reference-v1",
            task=task,
            role_scheme="model-question-source-v1",
            mode="complete_slots",
            focus="focus",
            entities=[
                dict(id=identity, kind=kind, extents=list(frame.opportunities[0].extents))
                for identity, kind in (("focus", "source"), ("target", "participant"))
            ],
            assertions=[dict(subject="focus", relation=role, object="target")],
            complete_slots=[dict(subject="focus", relation=role)],
        )
        case = OperationCase(
            case_id="choice-source",
            facet="value",
            anchor_ids=(),
            inspected_scope="original controlled source extent",
            source_state="stated",
            judgment="supported",
            alternatives=(),
            explanation="Controlled source-reference admission, not a model-quality assertion.",
            assessor_provenance={"actor": "native-choice-control"},
            opportunity_id="cell-value",
            required_family="character_" + task + "_v1",
            semantic_reference=reference,
        )
        payload["cases"] = [asdict(case)]
        payload["adjudication_passes"] = []
        frozen_frame = conn.scalar(
            text("SELECT context->0 FROM eval.reference_unit WHERE id=:id"), {"id": unit}
        )

        def submit(body, actor):
            return conn.scalar(
                text(
                    "SELECT eval.record_operation_reference_pass("
                    ":unit,'A',:actor,:authored,CAST(:frame AS jsonb))"
                ),
                dict(
                    unit=unit,
                    actor=actor,
                    authored=json.dumps(body).encode(),
                    frame=json.dumps(frozen_frame),
                ),
            )

        for corruption, message in (
            ("scheme", "semantic task identities or completeness"),
            ("role", "semantic assertion changes declared endpoints"),
            ("source", "task entity differs from frozen original source"),
        ):
            invalid = deepcopy(payload)
            proposed = invalid["cases"][0]["semantic_reference"]
            if corruption == "scheme":
                proposed["role_scheme"] = "construction-children-v1"
            elif corruption == "role":
                proposed["assertions"][0]["relation"] = "variable"
            else:
                proposed["entities"][0]["extents"][0]["projection"] = "f" * 64
            with pytest.raises(DBAPIError, match=message), conn.begin_nested():
                submit(invalid, task + "-invalid-" + corruption)
        assert submit(payload, task + "-valid") is not None
