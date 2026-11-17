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
