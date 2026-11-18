"""Published membership traversals retain subtree and ancestor scope."""

from sqlalchemy import BigInteger, Column, MetaData, Table, Text, literal, select, union_all
from sqlalchemy.schema import CreateSchema

from corpus_structure.semantic.pdf_selected_source_native import selected_membership_relations


def test_membership_traversals_are_pinned_and_keep_ancestor_scope(semantic_bare_engine):
    access_table = Table(
        "pdf_record_access",
        MetaData(),
        Column("product_id", Text),
        Column("revision_id", Text),
        Column("pointer", Text),
        Column("parent_pointer", Text),
        Column("ordinal", BigInteger),
        schema="kb",
    )
    records = [
        ("#/", None),
        ("#/book", "#/"),
        ("#/section", "#/book"),
        ("#/child", "#/section"),
        ("#/leaf", "#/child"),
        ("#/sibling", "#/book"),
    ]
    rows = [
        {
            "product_id": "build",
            "revision_id": "build",
            "pointer": pointer,
            "parent_pointer": parent,
            "ordinal": position,
        }
        for position, (pointer, parent) in enumerate(records)
    ]
    rows.extend(
        [
            {
                "product_id": "other",
                "revision_id": "other",
                "pointer": "#/foreign",
                "parent_pointer": "#/section",
                "ordinal": 8,
            },
            {
                "product_id": "build",
                "revision_id": "other",
                "pointer": "#/stale",
                "parent_pointer": "#/section",
                "ordinal": 9,
            },
        ]
    )
    with semantic_bare_engine.begin() as connection:
        connection.execute(CreateSchema("kb"))
        access_table.create(connection)
        connection.execute(access_table.insert(), rows)
        published = select(literal("build", Text()).label("build_id")).cte("published")
        _, _, selected, ancestors = selected_membership_relations(
            access_table.metadata, section=literal("#/section", Text())
        )
        query = union_all(
            select(literal("selected").label("kind"), selected.c.pointer),
            select(literal("ancestor").label("kind"), ancestors.c.pointer),
        ).add_cte(published)
        assert set(connection.execute(query).all()) == {
            ("selected", "#/section"),
            ("selected", "#/child"),
            ("selected", "#/leaf"),
            ("ancestor", "#/book"),
            ("ancestor", "#/"),
        }
