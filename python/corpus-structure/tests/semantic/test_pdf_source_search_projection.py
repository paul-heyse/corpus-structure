"""Stored database search representation and captured producer identity."""

import json
from hashlib import sha256

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


def test_search_projection_has_private_immutable_stored_vector_and_gin_index():
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
    assert (
        "TSVECTOR GENERATED ALWAYS AS (to_tsvector(CAST('english' AS REGCONFIG), text)) STORED"
        in ddl
    )
    assert any(
        "USING gin (search_vector)" in str(CreateIndex(index).compile(dialect=postgresql.dialect()))
        for index in section.indexes
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

    from corpus_structure.semantic.metadata import metadata

    target = MetaData()
    for name in (
        "sem.input",
        "ops.pdf_published_revision",
        "ops.pdf_source_search_population",
        "ops.pdf_source_search_section",
    ):
        metadata.tables[name].to_metadata(target)
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
    from corpus_structure.schema.physical import compile_physical
    from corpus_structure.semantic.data_operation_wire import wire_contracts
    from corpus_structure.semantic.metadata import metadata
    from corpus_structure.semantic.native_products import capture_native_authoring_inputs

    physical = dict(metadata.info["physical_sources"])
    physical["physical.yaml"] = physical["physical.yaml"].replace(
        b"ph:search_configuration: english", b"ph:search_configuration: simple"
    )
    target = compile_physical(physical, linkml_types=metadata.info["physical_linkml_types"])
    captured = capture_native_authoring_inputs(target_metadata=target)
    wire = wire_contracts(captured.native_sources)["ensure_pdf_search_projection"]["input"]
    assert wire["properties"]["configuration"] == {"const": "simple"}
    statement = search_projection_sql(captured.native_sources)
    assert "websearch_to_tsquery(CAST('simple' AS REGCONFIG)" in statement
    assert "configuration') IS DISTINCT FROM 'simple'" in statement
