"""Independent expectations for model-bound analysis; Core/PG owns execution."""

from dataclasses import replace

import pytest
from sqlalchemy import BigInteger, Text
from sqlglot import exp, parse_one
from sqlglot.errors import SqlglotError

from corpus_structure.semantic import projection_recipe as ir
from corpus_structure.semantic.projection_analysis import (
    ProjectionAnalysisUnavailable,
    analyze_recipe,
    expand_sources,
    recipe_expression,
)


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


def test_nested_pinned_queries_expand_before_qualification_and_keep_materialized_barrier():
    recipe = run_recipe()
    fields = tuple(
        ir.OutputField(
            name, ir.Field("base", name), "physical:ops.run." + name, "source", typ, False
        )
        for name, typ in (("id", BigInteger()), ("project_id", Text()))
    )
    first = ir.SourceDefinition(
        "first", None, ir.SourceReference("runs", "base"), fields, ir.Constant(True)
    )
    second = ir.SourceDefinition(
        "second", None, ir.SourceReference("first", "base"), fields, ir.Constant(True)
    )
    selected = replace(
        recipe, sources=(*recipe.sources, first, second), source=ir.SourceReference("second", "r")
    )
    result = analyze_recipe(selected)
    assert result.value_dependencies == (("project", ("physical:ops.run.project_id",)),)
    assert dict(result.relational_dependencies)["where"] == ("physical:ops.run.id",)
    assert result.logical_sources == (
        ("first", "projection:input/sources/first"),
        ("second", "projection:input/sources/second"),
    )
    assert not tuple(recipe_expression(selected).find_all(exp.CTE))
    materialized = replace(
        selected,
        sources=(*recipe.sources, replace(first, materialized=True)),
        source=ir.SourceReference("first", "r"),
    )
    tree = recipe_expression(materialized)
    assert next(tree.find_all(exp.CTE)).args["materialized"] is True
    assert analyze_recipe(materialized).value_dependencies == result.value_dependencies


def test_expansion_copies_shared_ast_and_comments_cannot_supply_authority():
    query = parse_one("SELECT project_id FROM logical")
    source = parse_one("SELECT project_id FROM ops.run /* sqlglot: authorize */")
    source.meta["model_source"] = "projection:input/sources/logical"
    before = source.dump(), query.dump()
    result = expand_sources(query, {"logical": source}, physical_sources=frozenset({"ops.run"}))
    assert (source.dump(), query.dump()) == before
    assert any(
        node.meta.get("model_source") == "projection:input/sources/logical"
        for node in result.walk()
    )
    assert "authorize" in result.sql()
    assert not result.meta.get("authorized")


@pytest.mark.parametrize(
    "query,sources,reason",
    [
        ("SELECT x FROM a", {"a": "SELECT x FROM b", "b": "SELECT x FROM a"}, "cyclic"),
        ("SELECT x FROM a", {"a": "SELECT x FROM missing"}, "missing source"),
        (
            "WITH a AS (SELECT x FROM ops.run) SELECT x FROM a",
            {"a": "SELECT x FROM ops.run"},
            "collision",
        ),
        ("SELECT x FROM a", {"a": "SELECT :unbound AS x FROM ops.run"}, "placeholder"),
        ("SELECT x FROM a", {"a": "SELECT unknown_helper(id) AS x FROM ops.run"}, "unbound helper"),
    ],
)
def test_pinned_closure_refuses_before_recursive_expansion(query, sources, reason):
    with pytest.raises(ProjectionAnalysisUnavailable, match=reason):
        expand_sources(
            parse_one(query),
            {name: parse_one(sql) for name, sql in sources.items()},
            physical_sources=frozenset({"ops.run"}),
        )


@pytest.mark.parametrize("type_name", ["ARRAY<UNKNOWN>", "ARRAY"])
def test_opaque_and_incomplete_nested_type_sources_refuse(type_name):
    with pytest.raises(ProjectionAnalysisUnavailable, match="not a supported query"):
        expand_sources(
            exp.select("x").from_("a"),
            {"a": exp.Command(this="opaque")},
            physical_sources=frozenset(),
        )
    source = exp.select(
            exp.Cast(this=exp.column("body"), to=exp.DataType.build(type_name))
    ).from_("ops.run")
    with pytest.raises(ProjectionAnalysisUnavailable, match="incomplete declared type"):
        expand_sources(
            exp.select("x").from_("a"), {"a": source}, physical_sources=frozenset({"ops.run"})
        )
