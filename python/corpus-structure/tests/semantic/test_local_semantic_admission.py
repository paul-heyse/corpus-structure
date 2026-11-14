"""Independent semantic admission expectations, distinct from grade labels."""

from copy import deepcopy
from typing import Any

import pytest
from scenario_recipes import register_scenario_builder

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.local_semantic_admission import CONTEXT_POLICY, RUBRIC
from corpus_structure.semantic.observations import source_python, source_value
from pgtap_batch import (
    SqlCase,
    SqlRecipe,
    build_sql_seed,
    run_sql_batch,
    selected_sql_cases,
    sql_literal,
)

pytestmark = pytest.mark.db

register_scenario_builder(SqlRecipe, build_sql_seed)


def evidence() -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]
]:
    # Expected semantic content is fixed independently of computational lineage.
    source = dict(
        project_id="independent-source",
        native_product_key="fixture-text",
        native_content_digest="a" * 64,
        projection_digest="b" * 64,
        recipe_digest="c" * 64,
        coordinate_version=2,
    )
    statement = dict(
        target=dict(
            term=dict(
                source=source,
                start=0,
                end=7,
                text="Poisson",
                scope="selected-source-context",
            ),
            content=dict(
                source=source,
                start=8,
                end=17,
                text="count law",
                scope="selected-source-context",
            ),
            interpretation="definition",
            scope="selected-source-context",
        ),
        relation="denotes",
        scope="selected-source-context",
        effective_version=None,
    )
    value = source_value(statement)
    contribution = dict(
        standing="retained_private",
        kind="proposal",
        semantic_type="contextual.relationship",
        contribution_id="proposal:one",
        occurrence_id="physical:one",
        value=value,
        pin={"source_view_id": 23, "projection_digest": "source-projection"},
        anchors=[
            dict(
                anchor_id="anchor:one",
                space="native",
                precision="exact",
                start=0,
                end=7,
                source_piece="Poisson",
            )
        ],
    )
    question = "contextual relationship selection for located occurrence"
    operation = dict(question=question, operation_version="2", outcome="succeeded")
    frame = dict(
        direction="source_first",
        operation_question=question,
        operation_version="2",
        rubric_version=RUBRIC,
        context_policy=CONTEXT_POLICY,
        pin=contribution["pin"],
        anchor_ids=["anchor:one"],
    )
    case = dict(
        case_id="denotation-one",
        facet="relationship",
        judgment="supported",
        source_state="stated",
        expectation_mode="structure",
        contribution_kind="proposal",
        anchor_ids=["anchor:one"],
        alternatives=[dict(semantic_type="contextual.relationship", value=value)],
    )
    result = dict(
        case_id="denotation-one",
        facet="relationship",
        judgment="supported",
        source_state="stated",
        expectation_mode="structure",
        capture_outcome="captured_structure",
        error_category=None,
        contribution_id="proposal:one",
    )
    return contribution, operation, frame, case, result


def native_expression(values) -> str:
    arguments = ",".join(
        sql_literal(canonical_bytes(value).decode()) + "::jsonb" for value in values
    )
    return "data.local_semantic_case_matches(" + arguments + ")"


_APPLICABILITY = (
    (0, "semantic_type", "entity.canonical_identity"),
    (1, "outcome", "failed"),
    (1, "operation_version", "3"),
    (2, "direction", "output_first"),
    (2, "rubric_version", "other-rubric"),
    (2, "context_policy", "other-context"),
    (2, "operation_question", "different question"),
    (2, "pin", {"source_view_id": 99}),
    (3, "judgment", "ambiguous"),
    (3, "judgment", "unassessed"),
    (3, "source_state", "unstated"),
    (3, "expectation_mode", "absence_detection"),
    (3, "facet", "scientific_truth"),
    (3, "anchor_ids", ["other-anchor"]),
    (4, "contribution_id", "foreign-proposal"),
    (4, "capture_outcome", "not_captured"),
    (4, "judgment", "unsupported"),
)
_FAMILY = "local_semantic_admission"


def sql_recipe() -> SqlRecipe:
    cases = [
        SqlCase(
            "test_exact",
            ((native_expression(evidence()), "exact independent denotation qualifies"),),
        )
    ]
    for index, (position, key, value) in enumerate(_APPLICABILITY):
        values = deepcopy(evidence())
        baseline = native_expression(values)
        values[position][key] = value
        cases.append(
            SqlCase(
                f"test_applicability_{index:02d}",
                (
                    (baseline, "independent baseline qualifies"),
                    ("NOT " + native_expression(values), f"{key} cannot bypass applicability"),
                ),
            )
        )
    values = evidence()
    assertions = [(native_expression(values), "independent baseline qualifies")]
    # Mutate only independently authored fixture content, never a producer projection.
    wrong_statement = deepcopy(source_python(values[0]["value"]))
    wrong_statement["target"]["content"]["text"] = "event law"
    for expected in (
        {"semantic_type": "contextual.relationship"},
        {"value": source_value({"target": {"interpretation": "definition"}})},
        {"semantic_type": "contextual.relationship", "value": source_value(wrong_statement)},
    ):
        values = deepcopy(evidence())
        values[3]["alternatives"] = [expected]
        assertions.append(
            ("NOT " + native_expression(values), "partial or wrong full statement is rejected")
        )
    cases.append(SqlCase("test_partial_statement", tuple(assertions)))
    return SqlRecipe.create(_FAMILY, tuple(cases))


@pytest.fixture(scope="module")
def local_semantic_sql_batch(request, scenario_seeds, tmp_path_factory):
    selected = selected_sql_cases(request.session, _FAMILY)
    with scenario_seeds.commit_clone(sql_recipe()) as clone:
        yield run_sql_batch(clone, selected, tmp_path_factory.mktemp("sql-batches"))


@pytest.mark.sql_family(_FAMILY, "test_exact", assertions=1)
def test_exact_independent_denotation_can_qualify(local_semantic_sql_batch):
    local_semantic_sql_batch.require_pass("test_exact")


@pytest.mark.parametrize(
    "position,key,value",
    [
        pytest.param(
            position,
            key,
            value,
            marks=pytest.mark.sql_family(_FAMILY, f"test_applicability_{index:02d}", assertions=2),
        )
        for index, (position, key, value) in enumerate(_APPLICABILITY)
    ],
)
def test_supported_label_cannot_bypass_applicability(
    local_semantic_sql_batch, position, key, value
):
    index = _APPLICABILITY.index((position, key, value))
    local_semantic_sql_batch.require_pass(f"test_applicability_{index:02d}")


@pytest.mark.sql_family(_FAMILY, "test_partial_statement", assertions=4)
def test_partial_or_wrong_full_semantic_statement_is_not_admitted(local_semantic_sql_batch):
    local_semantic_sql_batch.require_pass("test_partial_statement")
