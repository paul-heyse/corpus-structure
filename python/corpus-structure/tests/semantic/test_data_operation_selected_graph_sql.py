"""Execute the production selected-graph predicate on PostgreSQL JSON values."""

import json
from importlib.resources import files

import pytest
from sqlalchemy import text


@pytest.mark.db
@pytest.mark.parametrize(
    "declared, selected, invalid",
    [
        ({"dependencies": ["required"]}, ["required"], False),
        ({"dependencies": ["required"]}, [], True),
        ({"potential_dependencies": ["alternative"]}, ["alternative"], False),
        (
            {"dependencies": ["required"], "potential_dependencies": ["alternative"]},
            ["required", "alternative"],
            False,
        ),
        ({"dependencies": ["required"]}, ["required", "unrelated"], True),
        ({"dependencies": ["required"]}, ["required", "required"], True),
        ({}, [], False),
    ],
)
def test_selected_dependency_guard_preserves_declared_required_and_alternative_edges(
    semantic_bare_engine,
    declared,
    selected,
    invalid,
):
    source = files("corpus_structure.semantic").joinpath("sql/data_operations.sql").read_text()
    start = source.index("AND (NOT (coalesce(operation->'dependencies'") + len("AND (")
    end = source.index(
        "\n OR EXISTS(SELECT FROM jsonb_array_elements(p->'selection'->'operations') selected"
        "\n CROSS JOIN LATERAL",
        start,
    )
    predicate = source[start:end].removesuffix("))")
    # Only the predicate is selected: no native function/table/authorization bypass
    # is installed, and the actual PostgreSQL operator parser evaluates it.
    query = text(
        "WITH arguments AS (SELECT CAST(:declared AS jsonb) AS operation, "
        "CAST(:selected AS jsonb) AS selected) SELECT " + predicate + " FROM arguments"
    )
    with semantic_bare_engine.connect() as connection:
        actual = connection.scalar(
            query,
            {
                "declared": json.dumps(declared),
                "selected": json.dumps({"dependencies": selected}),
            },
        )
    assert actual is invalid
