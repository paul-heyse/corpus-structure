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
    installed_projection_id,
    prepare_projection,
    projection,
    render_static_columns,
)
from corpus_structure.semantic.companion_projection_native import family_sql
from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.projection_recipe import (
    Conditional,
    Constant,
    Equal,
    Field,
    InternalBinding,
    JsonPath,
    native_statement,
)
from corpus_structure.semantic.types import PreparationError


def prepared(view, family="coverage"):
    return prepare_projection(
        view,
        family,
        projection_id="independent-mutated-recipe",
        physical=metadata,
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
    "family,count", [("input", 17), ("relation", 24), ("coverage", 19), ("mapping_report", 25)]
)
def test_four_families_share_resolved_core_native_and_arrow_contract(family, count):
    spec = projection(family)
    assert len(spec.columns) == count
    assert spec.arrow_schema.names == [field.name for field in spec.recipe.fields]
    assert spec.keys == tuple(order.field for order in spec.recipe.order)
    assert tuple(p.name for p in spec.recipe.parameters) == (
        "project_id",
        "demand_id",
        "read_id",
        "use_id",
        "product_id",
        "derivation_id",
    )
    assert all(p.native_name != p.name for p in spec.recipe.parameters)
    bindings = spec.body_statement.compile(dialect=dialect()).params
    assert "_published_build_id" in bindings
    assert "_published_release_id" in bindings
    outputs = {field.name: field for field in spec.recipe.fields}
    assert outputs["selection_release_id"].expression == InternalBinding("selection_release_id")
    assert outputs["producer_release_id"].expression == InternalBinding("published_release_id")
    assert spec.projection_id == spec.recipe.projection_id == installed_projection_id()
    body = str(
        native_statement(spec.body_statement, spec.recipe).compile(
            dialect=dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    sql = family_sql(family)
    from pglast.stream import RawStream
    from pglast.visitors import Visitor

    from corpus_structure.semantic.native_products import function_bodies

    function_body = function_bodies(sql)[spec.function_name]
    query = function_body.split("RETURN QUERY ", 1)[1].rsplit("END", 1)[0].strip().removesuffix(";")
    if family == "input":
        calls = []

        class Calls(Visitor):
            def visit_FuncCall(self, ancestors, node):
                calls.append(node)

        Calls()(parse_sql(query))
        (helper,) = [
            call
            for call in calls
            if tuple(part.sval for part in call.funcname)
            == ("ops", "read_published_input_batch_rows")
        ]
        assert tuple(RawStream()(argument) for argument in helper.args) == (
            "p_project",
            "p_demand",
            "p_read",
            "p_use",
            "p_product",
            "p_derivation",
            "published.build_id",
            "published.release_id",
            "published.task_id",
            "published.product_key",
            "published.logical_digest",
            "selected_release",
        )
    else:
        assert parse_sql(query)[0].stmt == parse_sql(body)[0].stmt
    assert function_body.index(
        "published := ops.require_published_companion_pin"
    ) < function_body.index("RETURN QUERY")
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
        assert isinstance(expression.then, InternalBinding) and isinstance(
            expression.otherwise, Field
        )
        assert expression.when.left.name == "target_task_id" and expression.when.right.value == 0
        assert (
            expression.then.name == "published_" + parameter and expression.otherwise.name == name
        )
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


def test_cycle_and_wrong_alias_refuse():
    view = SchemaView(str(MODEL))
    schema = view.schema
    assert schema is not None
    sources = json_annotation(schema, "cp:sources")
    sources[-1]["input"]["name"] = "companions"
    annotation(schema, "cp:sources").value = json.dumps(sources)
    with pytest.raises(PreparationError, match="cycles/forward references"):
        prepared(view)
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


def test_native_companion_authoring_consumes_captured_recipe_without_installed_model(monkeypatch):
    import yaml

    from corpus_structure.semantic import companion_projection as owner
    from corpus_structure.semantic.companion_projection import captured_projection
    from corpus_structure.semantic.companion_projection_native import pin_guard_sql
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.pdf_domain import PdfDomainContract, pdf_domain_sources
    from corpus_structure.semantic.types import SourceArtifact

    contract, *sources = pdf_domain_sources()
    original_domain = PdfDomainContract(contract.content, tuple(sources))
    original = captured_projection("coverage", original_domain, target_metadata=metadata)
    assert original.projection_id == projection("coverage").projection_id
    logical_name = "pdf-domain/logical/companion_projections"
    document = yaml.safe_load(
        next(source.content for source in sources if source.name == logical_name)
    )
    document["classes"]["PublishedCoverageRow"]["annotations"]["cp:function"] = (
        "ops.read_captured_coverage_batch"
    )
    changed_sources = tuple(
        SourceArtifact(source.name, yaml.safe_dump(document, sort_keys=False).encode())
        if source.name == logical_name
        else source
        for source in sources
    )
    changed_contract = json.loads(contract.content)
    changed_contract["inputs"] = [
        {"name": source.name, "sha256": source.digest} for source in changed_sources
    ]
    captured = PdfDomainContract(canonical_bytes(changed_contract), changed_sources)
    monkeypatch.setattr(owner, "MODEL", Path("/unavailable-installed-companion-model.yaml"))
    selected = captured_projection("coverage", captured, target_metadata=metadata)
    assert selected.function_name == "ops.read_captured_coverage_batch"
    assert selected.projection_id != original.projection_id
    assert [(item.name, type(item.type)) for item in selected.columns] == [
        (item.name, type(item.type)) for item in original.columns
    ]
    assert parse_sql(family_sql("coverage", target_metadata=metadata, domain=captured))
    assert parse_sql(pin_guard_sql(target_metadata=metadata, domain=captured))
    assert "read_captured_coverage_batch" in family_sql(
        "coverage", target_metadata=metadata, domain=captured
    )
    assert render_static_columns(captured)


def test_private_input_helper_is_sql_standard_and_retains_no_public_grants(monkeypatch):
    from pglast import ast as pg_ast
    from pglast import enums
    from pglast.stream import RawStream

    from corpus_structure.semantic import companion_projection_native as owner
    from corpus_structure.semantic.native_objects import NativeDefinition, NativeIdentity

    def unresolved_definition(connection, sql, *, source, owner, grants):
        statement = parse_sql(sql)[0].stmt
        assert isinstance(statement, pg_ast.CreateFunctionStmt)
        assert statement.parameters is not None
        arguments = tuple(
            RawStream()(parameter.argType)
            for parameter in statement.parameters
            if parameter.mode != enums.FunctionParameterMode.FUNC_PARAM_TABLE
        )
        return NativeDefinition(
            NativeIdentity("function", "ops", "read_published_input_batch_rows", arguments),
            sql,
            source,
            owner,
            grants,
        )

    monkeypatch.setattr(owner, "definition_from_sql", unresolved_definition)
    definition = owner.input_body_definition(None)
    statement = parse_sql(definition.sql)[0].stmt
    assert isinstance(statement, pg_ast.CreateFunctionStmt)
    assert statement.parameters is not None and statement.options is not None
    assert definition.catalog_version == 2
    assert definition.owner == "corpus_sem_publisher"
    assert definition.grants == ()
    assert statement.sql_body is not None
    assert statement.returnType is not None and statement.returnType.setof
    options = {option.defname: option.arg for option in statement.options}
    assert options["language"].sval == "sql"
    assert "security" not in options or not options["security"].boolval
    assert tuple(
        parameter.name
        for parameter in statement.parameters
        if parameter.mode != enums.FunctionParameterMode.FUNC_PARAM_TABLE
    ) == (
        "p_project",
        "p_demand",
        "p_read",
        "p_use",
        "p_product",
        "p_derivation",
        "p_build",
        "p_producer_release",
        "p_native_task",
        "p_native_product",
        "p_native_digest",
        "p_selection_release",
    )
    assert tuple(
        parameter.name
        for parameter in statement.parameters
        if parameter.mode == enums.FunctionParameterMode.FUNC_PARAM_TABLE
    ) == tuple(field.name for field in projection("input").recipe.fields)
