"""Execute the production selected-graph predicate on PostgreSQL JSON values."""

import pytest
from sqlalchemy import literal, select
from sqlalchemy.dialects.postgresql import JSONB


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
    from corpus_structure.semantic.demand_registration_native import dependency_selection_differs

    query = select(
        dependency_selection_differs(
            literal(declared.get("dependencies", []), type_=JSONB()),
            literal(declared.get("potential_dependencies", []), type_=JSONB()),
            literal(selected, type_=JSONB()),
        )
    )
    with semantic_bare_engine.connect() as connection:
        actual = connection.scalar(query)
    assert actual is invalid
