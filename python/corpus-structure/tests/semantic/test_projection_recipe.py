"""Independent model-mutation, reference refusal and Core/native continuity controls."""

import ast
import copy
import json
from pathlib import Path

import pyarrow as pa
import pytest
from linkml_runtime.linkml_model.meta import Annotation, SlotDefinition
from linkml_runtime.utils.schemaview import SchemaView
from pglast import parse_sql
from sqlalchemy.dialects.postgresql import dialect

from corpus_structure.semantic.companion_projection import (
    MODEL,
    PROJECTION_ID,
    prepare_projection,
    projection,
    render_static_columns,
)
from corpus_structure.semantic.companion_projection_native import family_sql
from corpus_structure.semantic.metadata import PHYSICAL_MODEL_ID, metadata
from corpus_structure.semantic.projection_recipe import (
    Conditional,
    Constant,
    Equal,
    Field,
    InternalBinding,
    JsonPath,
    Parameter,
    native_statement,
)
from corpus_structure.semantic.types import PreparationError


def prepared(view, family="coverage", physical_id=PHYSICAL_MODEL_ID):
    return prepare_projection(
        view,
        family,
        projection_id="independent-mutated-recipe",
        physical=metadata,
        physical_id=physical_id,
    )


def attributes(container) -> dict[str, SlotDefinition]:
    values = container.attributes
    assert isinstance(values, dict)
    assert all(isinstance(value, SlotDefinition) for value in values.values())
    return values


def annotation(container, key) -> Annotation:
    values = container.annotations
    assert isinstance(values, dict)
    value = values[key]
    assert isinstance(value, Annotation)
    return value


def json_annotation(container, key):
    value = annotation(container, key).value
    assert isinstance(value, str)
    return json.loads(value)


@pytest.mark.parametrize(
    "family,count", [("input", 13), ("relation", 20), ("coverage", 15), ("mapping_report", 21)]
)
def test_four_families_share_resolved_core_native_and_arrow_contract(family, count):
    spec = projection(family)
    assert len(spec.columns) == count
    assert spec.arrow_schema.names == [field.name for field in spec.recipe.fields]
    assert spec.keys == tuple(order.field for order in spec.recipe.order)
    assert tuple(p.name for p in spec.recipe.parameters) == (
        "project_id",
        "run_id",
        "selection_release_id",
        "task_id",
        "product_key",
        "content_digest",
    )
    assert all(p.native_name != p.name for p in spec.recipe.parameters)
    bindings = spec.body_statement.compile(dialect=dialect()).params
    assert "_published_build_id" in bindings
    assert "_published_release_id" in bindings
    outputs = {field.name: field for field in spec.recipe.fields}
    assert outputs["selection_release_id"].expression == Parameter("selection_release_id")
    assert outputs["producer_release_id"].expression == InternalBinding("published_release_id")
    assert spec.projection_id == spec.recipe.projection_id == PROJECTION_ID
    body = str(
        native_statement(spec.body_statement, spec.recipe).compile(
            dialect=dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    sql = family_sql(family)
    if family == "input":
        assert (
            "RETURN QUERY SELECT * FROM ops.read_published_input_batch_rows("
            "p_project,p_run,p_selection_release,p_task,p_product,p_digest,"
            "published.build_id,published.release_id);"
        ) in sql
    else:
        assert "RETURN QUERY " + body + ";" in sql
    assert sql.index("published:=ops.require_published_companion_pin") < sql.index("RETURN QUERY")
    assert parse_sql(sql)
    assert "cp:sql" not in MODEL.read_text()


def test_relational_keys_roles_multiplicity_and_conditional_own_product_identity():
    relation = projection("relation").recipe
    join = relation.joins[0]
    assert (join.left_role, join.right_role, join.multiplicity) == (
        "relation",
        "endpoint",
        "one_to_many",
    )
    actual_keys = []
    for key in join.keys:
        assert isinstance(key.left, Field) and isinstance(key.right, Field)
        actual_keys.append((key.left.name, key.right.name))
    assert actual_keys == [
        ("product_id", "product_id"),
        ("revision_id", "revision_id"),
        ("local_id", "relation_id"),
    ]
    for name, parameter in (
        ("target_task_id", "task_id"),
        ("target_product_key", "product_key"),
        ("target_content_digest", "content_digest"),
    ):
        expression = next(field.expression for field in relation.fields if field.name == name)
        assert isinstance(expression, Conditional)
        assert isinstance(expression.when, Equal)
        assert isinstance(expression.when.left, Field)
        assert isinstance(expression.when.right, Constant)
        assert isinstance(expression.then, Parameter) and isinstance(expression.otherwise, Field)
        assert expression.when.left.name == "target_task_id" and expression.when.right.value == 0
        assert expression.then.name == parameter and expression.otherwise.name == name
    mapping = projection("mapping_report").recipe
    assert mapping.joins[0].multiplicity == "many_to_one"
    assert len(mapping.joins[0].keys) == 3
    assert isinstance(mapping.joins[0].keys[-1].left, JsonPath)
    assert mapping.joins[0].keys[-1].left.path == ("input_index",)
    assert isinstance(mapping.joins[0].keys[-1].right, Field)
    assert mapping.joins[0].keys[-1].right.name == "local_id"


def test_nullable_nested_json_addition_changes_all_products_without_sql_authoring():
    view = SchemaView(str(MODEL))
    source = view.get_class("PdfProductCoverage")
    assert source is not None
    source_slots = attributes(source)
    source_slots["nested_sample"] = copy.deepcopy(source_slots["supports"])
    source_slots["nested_sample"].name = "nested_sample"
    output = view.get_class("PublishedCoverageRow")
    assert output is not None
    output_slots = attributes(output)
    slot = copy.deepcopy(output_slots["supports_json"])
    slot.name = "nested_sample"
    annotation(slot, "cp:source").value = "PdfProductCoverage.nested_sample"
    annotation(slot, "cp:expr").value = json.dumps(
        {"json": {"value": {"field": ["c", "body"]}, "path": ["metadata", "sample"]}}
    )
    output_slots["nested_sample"] = slot
    spec = prepared(view)
    assert spec.arrow_schema.field("nested_sample").type == pa.json_()
    assert spec.arrow_schema.field("nested_sample").nullable
    field = next(field for field in spec.recipe.fields if field.name == "nested_sample")
    assert isinstance(field.expression, JsonPath)
    assert field.expression.path == ("metadata", "sample") and not field.expression.as_text
    assert "nested_sample" in spec.body_statement.selected_columns
    sql = str(
        native_statement(spec.body_statement, spec.recipe).compile(
            dialect=dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    assert "#>" in sql and "metadata" in sql and "sample" in sql
    # JSON extraction retains JSON null; text extraction intentionally has another contract.
    assert "#>>" not in sql
    assert spec.projection_id != projection("coverage").projection_id


@pytest.mark.parametrize(
    "expression",
    [
        {"sql": "arbitrary SQL is unsupported"},
        {"field": ["c", "absent_field"]},
        {"parameter": "undeclared_parameter"},
        {"call": {"helper": "unbound_helper", "arguments": []}},
        {"cast": {"value": {"constant": "{}"}, "type": "jsonb"}},
    ],
)
def test_invalid_expression_refuses_with_model_field_location(expression):
    view = SchemaView(str(MODEL))
    cls = view.get_class("PublishedCoverageRow")
    assert cls is not None
    annotation(attributes(cls)["detail"], "cp:expr").value = json.dumps(expression)
    with pytest.raises(PreparationError) as error:
        prepared(view)
    diagnostic = error.value.diagnostics[0]
    assert diagnostic.code == "invalid_projection_recipe"
    assert "PublishedCoverageRow.detail" in diagnostic.location


def test_cycle_wrong_alias_and_unsupported_physical_profile_refuse():
    view = SchemaView(str(MODEL))
    schema = view.schema
    assert schema is not None
    sources = json_annotation(schema, "cp:sources")
    sources[-1]["input"]["name"] = "companions"
    annotation(schema, "cp:sources").value = json.dumps(sources)
    with pytest.raises(PreparationError, match="cycles/forward references"):
        prepared(view)
    with pytest.raises(PreparationError, match="unsupported physical model"):
        prepared(SchemaView(str(MODEL)), physical_id="unsupported-archive")
    view = SchemaView(str(MODEL))
    cls = view.get_class("PublishedRelationRow")
    assert cls is not None
    body = json_annotation(cls, "cp:recipe")
    body["joins"][0]["keys"][0]["right"]["field"][0] = "unknown_alias"
    annotation(cls, "cp:recipe").value = json.dumps(body)
    with pytest.raises(PreparationError, match="join keys"):
        prepared(view, "relation")


def test_unsupported_recipe_schema_version_refuses_without_installed_fallback():
    view = SchemaView(str(MODEL))
    schema = view.schema
    assert schema is not None
    annotation(schema, "cp:version").value = "unsupported-archive"
    with pytest.raises(PreparationError, match="unsupported companion recipe version"):
        prepared(view)


def test_static_column_surface_preserved():
    target = Path(__file__).parents[2] / "src/corpus_structure/semantic/_companion_columns.py"
    assert ast.dump(ast.parse(render_static_columns())) == ast.dump(ast.parse(target.read_text()))
