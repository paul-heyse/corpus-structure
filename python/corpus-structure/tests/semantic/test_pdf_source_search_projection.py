"""Stored database search representation and captured producer identity."""

import json
from hashlib import sha256

from pglast import ast, parse_sql
from pglast.stream import RawStream
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from corpus_structure.schema.physical import compile_physical, physical_source_closure
from corpus_structure.schema.relational import column_type_annotation
from corpus_structure.semantic.metadata import PHYSICAL_MODEL
from corpus_structure.semantic.pdf_source_search import (
    CONTRACT,
    search_projection_sources,
    search_projection_sql,
)


def test_search_projection_has_private_immutable_stored_vector_and_gin_index(
    infrastructure_rollback,
):
    sources = physical_source_closure(
        PHYSICAL_MODEL.name,
        lambda name: PHYSICAL_MODEL.with_name(name).read_bytes(),
    )
    model = compile_physical(sources)
    population = model.tables["ops.pdf_source_search_population"]
    section = model.tables["ops.pdf_source_search_section"]
    assert population.info["read_roles"] == section.info["read_roles"] == []
    assert population.info["immutability"] == section.info["immutability"] == "intrinsic"
    assert tuple(section.primary_key.columns.keys()) == (
        "population_id",
        "section_pointer",
        "membership",
    )
    ddl = str(CreateTable(section).compile(dialect=postgresql.dialect()))
    statement = parse_sql(ddl)[0].stmt
    assert isinstance(statement, ast.CreateStmt)
    column = next(
        item
        for item in statement.tableElts or ()
        if isinstance(item, ast.ColumnDef) and item.colname == "search_vector"
    )
    generated = next(item for item in column.constraints or () if item.generated_when == "a")
    assert generated.generated_kind == "s"
    expression = generated.raw_expr
    assert isinstance(expression, ast.FuncCall) and expression.args
    configuration = expression.args[0]
    assert isinstance(configuration, ast.TypeCast)
    sql = RawStream()(expression)
    connection = infrastructure_rollback
    assert (
        connection.exec_driver_sql(
            f"SELECT ({sql}) @@ websearch_to_tsquery('simple', 'run') "
            "FROM (VALUES ('running')) AS sample(text)"
        ).scalar_one()
        is True
    )
    configuration.arg = ast.A_Const(val=ast.String(sval="simple"))
    sql = RawStream()(expression)
    assert (
        connection.exec_driver_sql(
            f"SELECT ({sql}) @@ websearch_to_tsquery('simple', 'run') "
            "FROM (VALUES ('running')) AS sample(text)"
        ).scalar_one()
        is False
    )
    indexes = [
        parse_sql(str(CreateIndex(index).compile(dialect=postgresql.dialect())))[0].stmt
        for index in section.indexes
    ]
    assert any(
        isinstance(index, ast.IndexStmt)
        and index.accessMethod == "gin"
        and tuple(parameter.name for parameter in index.indexParams or ()) == ("search_vector",)
        for index in indexes
    )
    assert column_type_annotation(section.c.search_vector) == "str"


def test_native_search_installs_the_exact_captured_renderer_contract():
    sources = search_projection_sources()
    by_name = {source.name: source.content for source in sources}
    contract = json.loads(by_name[CONTRACT])
    assert (
        contract["default_policy_digest"]
        == sha256(
            by_name["native/search-renderer/model/semantic/section-text-recipe.json"]
        ).hexdigest()
    )
    assert by_name["native/search-renderer/ingest/pdf_section_views.py"]
    assert by_name["native/search-renderer/semantic/source_products.py"]
    sql = search_projection_sql(sources)
    assert "__SEARCH_" not in sql
    assert contract["renderer"] in sql and contract["default_policy_digest"] in sql


def test_generated_search_tracks_quoted_physical_fields_and_result_types():
    from pglast import ast, parse_plpgsql, parse_sql
    from sqlalchemy import MetaData, String

    from corpus_structure.semantic.metadata import get_metadata

    target = MetaData()
    for name in (
        "sem.input",
        "ops.pdf_published_revision",
        "ops.pdf_source_search_population",
        "ops.pdf_source_search_section",
    ):
        get_metadata().tables[name].to_metadata(target)
    target.tables["ops.pdf_published_revision"].c.logical_digest.name = 'publication "digest"'
    section = target.tables["ops.pdf_source_search_section"]
    section.c.text.name = 'section "text"'
    section.c.population_id.type = String(80)
    generated = search_projection_sql(search_projection_sources(target_metadata=target))
    declarations = []
    for item in parse_sql(generated):
        assert isinstance(item.stmt, ast.CreateFunctionStmt)
        declarations.append(item.stmt)
    assert len(parse_plpgsql(generated)) == 4
    keys = next(
        item
        for item in declarations
        if item.funcname and item.funcname[-1].sval == "ddo_pdf_search_keys"
    )
    assert keys.parameters is not None
    population = next(
        parameter for parameter in keys.parameters if parameter.name == "population_id"
    )
    assert population.argType is not None
    assert population.argType.names is not None
    assert population.argType.names[-1].sval == "varchar"
    assert population.argType.typmods is not None
    length = population.argType.typmods[0]
    assert isinstance(length, ast.A_Const)
    assert isinstance(length.val, ast.Integer)
    assert length.val.ival == 80
    assert '"publication ""digest"""' in generated
    assert '"section ""text"""' in generated


def test_search_configuration_changes_the_vector_program_and_wire_together():
    from pglast import enums, parse_plpgsql
    from pglast.visitors import Visitor

    from corpus_structure.schema.physical import compile_physical
    from corpus_structure.semantic.data_operation_wire import wire_contracts
    from corpus_structure.semantic.metadata import get_metadata
    from corpus_structure.semantic.native_products import capture_native_authoring_inputs

    physical = dict(get_metadata().info["physical_sources"])
    physical["physical.yaml"] = physical["physical.yaml"].replace(
        b"ph:search_configuration: english", b"ph:search_configuration: simple"
    )
    target = compile_physical(physical, linkml_types=get_metadata().info["physical_linkml_types"])
    captured = capture_native_authoring_inputs(target_metadata=target)
    wire = wire_contracts(captured.native_sources)["ensure_pdf_search_projection"]["input"]
    request = wire["definitions"]["ensure_pdf_search_projection_request"]
    assert request["properties"]["configuration"] == {"const": "simple"}
    statement = search_projection_sql(captured.native_sources)

    class Configurations(Visitor):
        def __init__(self):
            super().__init__()
            self.queries = []
            self.guards = []

        def visit_FuncCall(self, ancestors, node):
            if node.funcname[-1].sval == "websearch_to_tsquery":
                configuration = node.args[0]
                assert isinstance(configuration, ast.TypeCast)
                assert configuration.typeName is not None and configuration.typeName.names
                assert configuration.typeName.names[-1].sval == "regconfig"
                assert isinstance(configuration.arg, ast.A_Const)
                assert isinstance(configuration.arg.val, ast.String)
                self.queries.append(configuration.arg.val.sval)

        def visit_A_Expr(self, ancestors, node):
            key = node.lexpr
            if (
                node.kind == enums.A_Expr_Kind.AEXPR_DISTINCT
                and isinstance(key, ast.A_Expr)
                and isinstance(key.rexpr, ast.A_Const)
                and isinstance(key.rexpr.val, ast.String)
                and key.rexpr.val.sval == "configuration"
            ):
                assert isinstance(node.rexpr, ast.A_Const)
                assert isinstance(node.rexpr.val, ast.String)
                self.guards.append(node.rexpr.val.sval)

    configurations = Configurations()

    def inspect(value):
        if isinstance(value, dict):
            for kind, contents in value.items():
                if kind in {"PLpgSQL_stmt_assign", "PLpgSQL_stmt_if"}:
                    expression = contents["expr" if kind == "PLpgSQL_stmt_assign" else "cond"][
                        "PLpgSQL_expr"
                    ]["query"]
                    # pglast retains the assignment target in this expression field.
                    if kind == "PLpgSQL_stmt_assign":
                        _, separator, expression = expression.partition(":=")
                        assert separator
                    configurations(parse_sql("SELECT " + expression))
                inspect(contents)
        elif isinstance(value, list):
            for contents in value:
                inspect(contents)

    inspect(parse_plpgsql(statement))
    assert configurations.queries == ["simple"]
    assert configurations.guards == ["simple"]
