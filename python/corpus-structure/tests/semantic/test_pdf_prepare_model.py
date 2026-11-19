"""Frozen preparation follows physical metadata without handwritten column SQL."""

from pglast import ast, parse_sql
from sqlalchemy import Column, MetaData, Text
from sqlalchemy.dialects.postgresql import dialect

from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.pdf_publication_native import (
    _FINAL,
    _prepare_pdf_copy_statements,
    publication_control_programs,
)
from corpus_structure.semantic.pdf_staging import STAGE_FAMILIES


def test_frozen_region_copy_tracks_quoted_columns_and_new_model_fields():
    stages = {
        **STAGE_FAMILIES,
        **{
            family: "ops.pdf_stage_" + family
            for family in ("companion", "endpoint", "companion_field", "access", "region")
        },
    }
    target_metadata = MetaData()
    for relation in (*_FINAL.values(), *stages.values()):
        get_metadata().tables[relation].to_metadata(target_metadata)
    target = target_metadata.tables[_FINAL["region"]]
    source = target_metadata.tables[stages["region"]]
    target.c.left.name = 'left "edge"'
    source.c.left.name = 'source "edge"'
    target.append_column(Column('new "domain" field', Text, key="extension"))
    source.append_column(Column('new "stage" field', Text, key="extension"))

    copies = _prepare_pdf_copy_statements(target_metadata, stages, build_parameter="p_build")
    region = next(statement for statement in copies if statement.table is target)
    sql = str(
        region.compile(dialect=dialect(paramstyle="named"), compile_kwargs={"literal_binds": True})
    )
    statement = parse_sql(sql)[0].stmt
    assert isinstance(statement, ast.InsertStmt)
    assert statement.cols is not None
    assert [column.name for column in statement.cols] == [column.name for column in target.columns]
    assert isinstance(statement.selectStmt, ast.SelectStmt)
    projection = statement.selectStmt.targetList
    assert projection is not None
    assert all(isinstance(item.val, ast.ColumnRef) for item in projection)
    assert [item.val.fields[-1].sval for item in projection] == [
        source.c[column.key].name for column in target.columns
    ]
    assert statement.onConflictClause is not None


def test_frozen_prepare_declaration_matches_its_writer_grant():
    from corpus_structure.semantic.pdf_contracts import trusted_pdf_context

    programs = publication_control_programs(get_metadata(), trusted_pdf_context().domain)
    prepare = next(item for item in programs if item.identity.name == "prepare_pdf_build")
    assert prepare.identity.arguments == ("text", "bigint", "bigint", "text", "text")
    assert prepare.access.grants(prepare.owner) == (("corpus_sem_writer", "EXECUTE", False),)
