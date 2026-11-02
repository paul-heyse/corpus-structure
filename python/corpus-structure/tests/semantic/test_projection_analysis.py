"""Independent expectations for model-bound analysis; Core/PG owns execution."""

from dataclasses import replace

import pytest
from sqlalchemy import BigInteger, Text
from sqlglot.errors import SqlglotError

from corpus_structure.semantic import projection_recipe as ir
from corpus_structure.semantic.projection_analysis import analyze_recipe, recipe_expression


def run_recipe():
    return ir.ProjectionRecipe(
        family="input",
        projection_id="independent-test-1",
        parameters=(
            ir.ParameterDefinition("run_id", "p_run", "physical:ops.run.id", BigInteger(), False),
        ),
        helpers=(),
        sources=(ir.SourceDefinition("runs", "ops.run", None),),
        source=ir.SourceReference("runs", "r"),
        joins=(),
        fields=(
            ir.OutputField(
                "project",
                ir.Field("r", "project_id"),
                "physical:ops.run.project_id",
                "value",
                Text(),
                False,
            ),
        ),
        predicate=ir.Equal(ir.Field("r", "id"), ir.Parameter("run_id")),
        order=(ir.Order("project"),),
        families=("input",),
    )


def test_qualified_value_lineage_and_types_use_the_model_recipe():
    recipe = run_recipe()
    result = analyze_recipe(recipe)
    assert result.output_types == (("project", "TEXT"),)
    assert result.value_dependencies == (("project", ("physical:ops.run.project_id",)),)
    assert result.relational_sources == ("ops.run",)
    assert dict(result.relational_dependencies)["where"] == ("physical:ops.run.id",)
    assert dict(result.relational_dependencies)["order"] == ("physical:ops.run.project_id",)
    assert result.library_version == "30.27.0"
    assert result.projection_id == "independent-test-1"
    assert result.unknowns == ()
    assert analyze_recipe(recipe) is result


def test_analysis_does_not_mutate_a_previously_built_tree():
    recipe = run_recipe()
    tree = recipe_expression(recipe)
    before = tree.sql(dialect="postgres")
    analyze_recipe(recipe)
    assert tree.sql(dialect="postgres") == before


def test_unknown_column_fails_before_lineage_can_masquerade_as_valid():
    recipe = run_recipe()
    field = replace(recipe.fields[0], expression=ir.Field("r", "not_a_column"))
    with pytest.raises(SqlglotError):
        analyze_recipe(replace(recipe, fields=(field,)))


def test_unused_available_relation_is_not_claimed_as_an_answer_dependency():
    recipe = run_recipe()
    result = analyze_recipe(
        replace(
            recipe,
            sources=(
                *recipe.sources,
                ir.SourceDefinition("unused", "kb.pdf_record_endpoint", None),
            ),
        )
    )
    assert result.relational_sources == ("ops.run",)
    assert result.output_origins == (("project", "physical:ops.run.project_id"),)
