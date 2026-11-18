"""Residual source pages use the authentic body traversal with section boundaries."""

from pglast import ast, parse_sql
from pglast.stream import RawStream
from sqlalchemy import Column, MetaData, Table, Text, column, func, select
from sqlalchemy.schema import CreateSchema

from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.published_document import (
    published_read_statements,
    published_readers_sql,
)


def test_body_direct_page_includes_unsectioned_body_and_preserves_section_boundaries(
    infrastructure_rollback,
):
    selected = MetaData()
    for name in (
        "kb.pdf_record_access",
        "kb.pdf_record_region",
        "kb.pdf_record_companion",
        "ops.pdf_published_revision",
    ):
        source = metadata.tables[name]
        Table(
            source.name,
            selected,
            *(Column(item.name, item.type, nullable=item.nullable) for item in source.columns),
            schema=source.schema,
        )
    access = selected.tables["kb.pdf_record_access"]
    rows = [
        ("#/body", None, None, "unspecified", "body"),
        ("#/texts/0", "#/body", None, "text", "body"),
        ("#/groups/0", "#/body", "#/groups/0", "section", "body"),
        ("#/texts/1", "#/groups/0", "#/groups/0", "text", "body"),
        ("#/texts/2", "#/body", None, "page_footer", "furniture"),
        ("#/texts/3", "#/body", None, "text", "body"),
    ]
    statement = published_read_statements(target_metadata=selected)["item_page"]
    with infrastructure_rollback.begin_nested():
        connection = infrastructure_rollback
        connection.execute(CreateSchema("kb"))
        access.create(connection)
        connection.execute(CreateSchema("ops"))
        private = next(
            raw.stmt
            for raw in parse_sql(published_readers_sql(target_metadata=selected))
            if isinstance(raw.stmt, ast.CreateFunctionStmt)
            and raw.stmt.funcname
            and raw.stmt.funcname[-1].sval == "read_pdf_published_item_page_rows"
        )
        connection.exec_driver_sql(RawStream()(private), execution_options={"no_parameters": True})
        connection.execute(
            access.insert(),
            [
                {
                    "product_id": "build",
                    "revision_id": "build",
                    "pointer": pointer,
                    "parent_pointer": parent,
                    "section_pointer": section,
                    "label": label,
                    "content_layer": layer,
                    "ordinal": ordinal,
                    "native_json": {"self_ref": pointer},
                    "text": pointer,
                }
                for ordinal, (pointer, parent, section, label, layer) in enumerate(rows)
            ],
        )

        def page(section, *, after=-1, limit=100, pointer=None):
            actual = [
                row.pointer
                for row in connection.execute(
                    statement,
                    {
                        "_native_build_id": "build",
                        "_native_revision_id": "build",
                        "p_section": section,
                        "p_membership": "direct",
                        "p_pointer": pointer,
                        "p_after": after,
                        "p_limit": limit,
                    },
                )
            ]
            function = func.ops.read_pdf_published_item_page_rows(
                "build",
                "build",
                section,
                "direct",
                pointer,
                after,
                limit,
            ).table_valued(column("pointer", Text()))
            assert list(connection.scalars(select(function.c.pointer))) == actual
            return actual

        assert page("#/body") == ["#/body", "#/texts/0", "#/texts/3"]
        assert page("#/groups/0") == ["#/groups/0", "#/texts/1"]
        assert page("#/body", after=0, limit=1) == ["#/texts/0"]
        assert page("#/body", pointer="#/texts/3") == ["#/texts/3"]
        assert page("#/body", pointer="#/texts/1") == []
        assert page("#/missing") == []
