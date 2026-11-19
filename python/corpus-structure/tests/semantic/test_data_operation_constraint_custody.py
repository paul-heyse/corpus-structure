"""Current DDO JSON constraints and ordinary graph capability remain distinct."""

import json
from dataclasses import replace

import pytest
import yaml
from pglast import parse_plpgsql, parse_sql
from sqlalchemy import insert, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.execution_admission import ExecutionAdmissionError
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.native_definition_projection import read_native_definition_projection
from corpus_structure.semantic.releases import _projection_rows
from semantic.data_operation_declaration_support import source_declaration
from semantic.data_operation_kernel_support import STORAGE, prepare_kernel


def question_recipe(*, graph_pattern=False):
    schema = yaml.safe_load(STORAGE.schema_text)
    schema["classes"].update(
        Question=dict(
            attributes=dict(
                family=dict(range="string", required=True, pattern="^(table|measurement)$"),
                variant=dict(
                    range="string",
                    required=True,
                    pattern="^(standard|unresolved-value-alternative)$",
                ),
            )
        ),
        QuestionPanel=dict(
            attributes=dict(question=dict(range="Question", inlined=True, required=True))
        ),
    )
    if graph_pattern:
        schema["classes"]["GraphOnly"] = dict(
            attributes=dict(label=dict(range="string", required=True, pattern="^x$"))
        )
    operation = source_declaration()
    operation["roles"][0].update(kind="QuestionPanel", maximum=1, collection="scalar")
    return replace(
        STORAGE,
        name="question-constraint-custody" + ("-graph" if graph_pattern else ""),
        schema_text=yaml.safe_dump(schema),
        declaration_content=canonical_bytes(
            dict(version=STORAGE.model_version, operations=[operation])
        ),
    )


QUESTION = question_recipe()


def test_current_question_projection_preserves_exact_patterns_and_class_ownership():
    preparation = prepare_kernel(QUESTION)
    prepared = preparation.prepared
    projected = read_native_definition_projection(prepared)
    panel = prepared.index.definitions["QuestionPanel"].iri
    question = prepared.index.definitions["Question"].iri
    # The nested value is enforced within the panel's captured body schema; it
    # need not also be a separately published nominal kind.
    assert panel in {kind["kind"] for kind in projected["kinds"]}
    assert question not in {kind["kind"] for kind in projected["kinds"]}
    kinds = {kind["semantic_id"]: kind for kind in json.loads(preparation.model.content)["kinds"]}
    assert kinds[panel]["category"] == "class"
    rows = _projection_rows(prepared)["property_applicability"]
    assert any(
        row["class_id"] == panel
        and row["range_name"] == "Question"
        and row["constraints"]["inlined"] is True
        for row in rows
    )
    constraints = {row["property_id"]: row for row in rows if row["class_id"] == question}
    assert {row["constraint_scope"] for row in constraints.values()} == {"shape"}
    assert {
        prop.name: constraints[prop.iri]["constraints"]["pattern"]
        for prop in prepared.index.definitions["Question"].properties
    } == {
        "family": "^(table|measurement)$",
        "variant": "^(standard|unresolved-value-alternative)$",
    }
    schema = next(kind["body_schema"] for kind in projected["kinds"] if kind["kind"] == panel)
    serialized = canonical_bytes(schema)
    assert b"^(table|measurement)$" in serialized
    assert b"^(standard|unresolved-value-alternative)$" in serialized


def test_current_admission_kernel_sql_parses():
    from corpus_structure.semantic.native_products import admission_kernel

    source = admission_kernel()
    assert parse_sql(source)
    assert parse_plpgsql(source)
    # The unloaded source_record_graph.sql parser case retired with its subject.
    # Current question/constraint guards are exercised through the native journeys below.


@pytest.mark.parametrize("ddo_kernel", [QUESTION], indirect=True)
def test_native_current_question_patterns_are_enforced_after_release_admission(ddo_kernel):
    kernel = ddo_kernel
    panel = kernel.prepared.index.definitions["QuestionPanel"].iri
    context = dict(
        project_id="ddo-test",
        release_id=kernel.prepared.release_id,
        subject="question:one",
        subject_definition=kernel.model.operations[0].subject,
        original_source="source:one",
        analyzed_scope={},
    )
    statement = text(
        "SELECT ops.ddo_install_product_context(CAST(:context AS jsonb),"
        "CAST(:product AS jsonb),ops.ddo_release_subject_scopes(:release))"
    )

    def packet(family, variant):
        return json.dumps(
            dict(
                kind_contract=kernel.identities[panel, "kind"],
                members=[],
                body=semantic_value(dict(question=dict(family=family, variant=variant))),
            )
        )

    with kernel.engine.begin() as connection:
        arguments = dict(context=json.dumps(context), release=kernel.prepared.release_id)
        assert connection.scalar(
            statement, {**arguments, "product": packet("measurement", "standard")}
        )
        for family, variant in (("unrequested", "standard"), ("table", "invented-variant")):
            with (
                pytest.raises(DBAPIError, match="body violates kind contract"),
                connection.begin_nested(),
            ):
                connection.execute(statement, {**arguments, "product": packet(family, variant)})


def test_native_unprojected_graph_pattern_is_still_refused(scenario_seeds):
    # A current DDO release is essential here: the obsolete execution-model
    # refusal must not mask whether the actual graph requirement was enforced.
    with (
        pytest.raises(
            ExecutionAdmissionError, match="unsupported required native constraint scope or pattern"
        ),
        scenario_seeds.commit_clone(question_recipe(graph_pattern=True)),
    ):
        pytest.fail("unsupported ordinary graph pattern was admitted")


@pytest.mark.parametrize("ddo_kernel", [QUESTION], indirect=True)
@pytest.mark.parametrize("graph_use", ["membership", "datatype"])
def test_native_json_kind_does_not_grant_graph_pattern_support(ddo_kernel, graph_use):
    kernel = ddo_kernel
    release = kernel.prepared.release_id
    question = kernel.prepared.index.definitions["Question"].iri
    with kernel.engine.begin() as connection:
        connection.execute(
            insert(table("data.realization")).values(
                realization_id="question-graph",
                project_id="ddo-test",
                release_id=release,
            )
        )
        common = dict(realization_id="question-graph", release_id=release)
        if graph_use == "membership":
            connection.execute(
                insert(table("data.entity")).values(**common, entity_id="question:one")
            )
            connection.execute(
                insert(table("data.membership")).values(
                    **common,
                    entity_id="question:one",
                    class_id=question,
                    establishment="asserted",
                )
            )
        else:
            connection.execute(
                insert(table("data.typed_value")).values(
                    **common,
                    value_id="question:value",
                    kind="record",
                    datatype=question,
                )
            )
        with (
            pytest.raises(
                DBAPIError, match="unsupported required native graph constraint scope or pattern"
            ),
            connection.begin_nested(),
        ):
            connection.execute(
                text("SELECT data.validate_state(:r,:z)"), dict(r=release, z="question-graph")
            )
        # The transaction deliberately contains rejected graph input, never a
        # published fact or candidate. Roll it back before deferred validation.
        connection.rollback()
