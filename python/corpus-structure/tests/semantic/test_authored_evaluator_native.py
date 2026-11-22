"""Actual evaluator admission grant and independent ordinary-purpose refusal."""

import json
from dataclasses import replace

import pytest
from sqlalchemy import Text, bindparam, cast, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_service import NativeDemandRequest
from corpus_structure.semantic.data_operation_support import authored_fact_selection
from corpus_structure.serve.interpretation_authoring import author_interpretations
from semantic.test_data_operation_authored import _recipe


def protected_recipe():
    recipe = _recipe()
    assert recipe.declaration_content is not None
    declaration = json.loads(recipe.declaration_content)
    kind = "urn:authored-reference:evaluator-integer"
    declaration["kinds"] = [dict(id=kind, primitive="integer", universe="evaluator")]
    for role in declaration["operations"][0]["roles"]:
        role["kind"] = kind
    return replace(
        recipe, name="protected-authored-reference", declaration_content=json_bytes(declaration)
    )


@pytest.mark.parametrize("ddo_kernel", [protected_recipe()], indirect=True)
def test_evaluator_authored_reference_allowed_and_ordinary_writer_refused(ddo_kernel):
    kernel = ddo_kernel
    context = SubjectContext(
        "ddo-test",
        "reference:one",
        "source:independent-reference",
        b"{}",
        subject_definition="document",
    )
    kind = kernel.identities["urn:authored-reference:evaluator-integer", "kind"]
    authored = authored_fact_selection(
        "independent-reference",
        41,
        kind_contract=kind,
        context=context,
        author="independent operator",
        selection_id="question:one",
    )
    request = NativeDemandRequest.model_validate(
        dict(
            project_id=context.project_id,
            release_id=kernel.prepared.release_id,
            runtime_id=kernel.preparation.runtime.runtime_id,
            roots=[
                dict(
                    subject=context.subject,
                    original_source=context.original_source,
                    analyzed_scope={},
                )
            ],
            targets=["urn:authored:consume"],
            execution_profile="execution:test",
            inference="reference:no-inference",
            original_sources={authored.name: authored.record()},
        )
    )
    evaluator, writer = kernel.purpose("evaluate"), kernel.purpose("write")
    statement = select(
        cast(func.ops.admit_authored_data(cast(bindparam("payload", type_=Text), JSONB)), Text)
    )
    try:
        report = author_interpretations(evaluator, kernel.prepared, request=request)
        assert report["standing"] == "authored"
        assert len(report["authored_admissions"]) == 1
        payload = dict(
            demand_id=report["demand_id"], selection_name=authored.name, **authored.record()
        )
        with evaluator.begin() as connection:
            admitted = json.loads(
                connection.scalar(statement, {"payload": json_bytes(payload).decode()})
            )["payload"]
            assert admitted["admission_id"] == report["authored_admissions"][0]["admission_id"]
        with writer.begin() as connection, pytest.raises(DBAPIError, match="evaluator"):
            connection.scalar(statement, {"payload": json_bytes(payload).decode()})
    finally:
        evaluator.dispose()
        writer.dispose()
