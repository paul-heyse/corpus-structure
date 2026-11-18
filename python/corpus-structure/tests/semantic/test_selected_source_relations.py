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
            access_table.metadata, published=published, section=literal("#/section", Text())
        )
        query = union_all(
            select(literal("selected").label("kind"), selected.c.pointer),
            select(literal("ancestor").label("kind"), ancestors.c.pointer),
        )
        assert set(connection.execute(query).all()) == {
            ("selected", "#/section"),
            ("selected", "#/child"),
            ("selected", "#/leaf"),
            ("ancestor", "#/book"),
            ("ancestor", "#/"),
        }


def test_containment_and_metadata_keep_published_product_and_context_scope(semantic_bare_engine):
    from sqlalchemy.dialects.postgresql import JSONB

    from corpus_structure.semantic.pdf_selected_source_native import selected_content_relations

    metadata = MetaData()
    access = Table(
        "pdf_record_access",
        metadata,
        Column("product_id", Text),
        Column("revision_id", Text),
        Column("pointer", Text),
        Column("parent_pointer", Text),
        Column("ordinal", BigInteger),
        schema="kb",
    )
    native = Table(
        "pdf_record_native",
        metadata,
        Column("product_id", Text),
        Column("revision_id", Text),
        Column("record_id", Text),
        Column("native_address", Text),
        Column("structure_json", JSONB),
        schema="kb",
    )
    membership = Table(
        "pdf_record_membership",
        metadata,
        Column("product_id", Text),
        Column("revision_id", Text),
        Column("parent_id", Text),
        Column("value_kind", Text),
        Column("record_id", Text),
        schema="kb",
    )
    companions = Table(
        "pdf_record_companion",
        metadata,
        Column("product_id", Text),
        Column("revision_id", Text),
        Column("family", Text),
        Column("local_id", Text),
        Column("body", JSONB),
        schema="kb",
    )
    with semantic_bare_engine.begin() as connection:
        connection.execute(CreateSchema("kb"))
        connection.execute(CreateSchema("ops"))
        metadata.create_all(connection)
        # Independent control for the contextual body resolver isolates membership selection.
        connection.exec_driver_sql("""
            CREATE FUNCTION ops.pdf_companion_body(text,text,text,text,jsonb) RETURNS jsonb
            LANGUAGE sql IMMUTABLE AS 'SELECT $5'
        """)
        connection.execute(
            access.insert(),
            [
                {
                    "product_id": "build",
                    "revision_id": "build",
                    "pointer": pointer,
                    "parent_pointer": parent,
                    "ordinal": ordinal,
                }
                for ordinal, (pointer, parent) in enumerate(
                    [
                        ("#/book", None),
                        ("#/section", "#/book"),
                        ("#/child", "#/section"),
                        ("#/sibling", "#/book"),
                    ]
                )
            ],
        )
        connection.execute(
            native.insert(),
            [
                {
                    "product_id": product,
                    "revision_id": revision,
                    "record_id": record,
                    "native_address": address,
                    "structure_json": {"fields": fields},
                }
                for product, revision, record, address, fields in [
                    (
                        "build",
                        "build",
                        "root",
                        "#/section",
                        {
                            "object": {"kind": "object", "target": "nested"},
                            "scalar": {"kind": "scalar", "target": "excluded"},
                        },
                    ),
                    (
                        "build",
                        "build",
                        "nested",
                        None,
                        {"cycle": {"kind": "object", "target": "root"}},
                    ),
                    ("build", "build", "member", None, {}),
                    ("build", "build", "excluded", None, {}),
                    (
                        "other",
                        "other",
                        "root",
                        "#/section",
                        {"object": {"kind": "object", "target": "foreign"}},
                    ),
                ]
            ],
        )
        connection.execute(
            membership.insert(),
            [
                {
                    "product_id": "build",
                    "revision_id": revision,
                    "parent_id": "root",
                    "value_kind": kind,
                    "record_id": record,
                }
                for revision, kind, record in [
                    ("build", "record", "member"),
                    ("build", "scalar", "excluded"),
                    ("other", "record", "foreign"),
                ]
            ],
        )
        connection.execute(
            companions.insert(),
            [
                {
                    "product_id": "build",
                    "revision_id": revision,
                    "family": family,
                    "local_id": local,
                    "body": {
                        "kind": kind,
                        "pointer": pointer,
                        "value": {"section_pointer": pointer},
                    },
                }
                for local, family, kind, pointer, revision in [
                    (
                        "formula-selected",
                        "native_metadata",
                        "formula_outcomes",
                        "#/section",
                        "build",
                    ),
                    ("formula-ancestor", "native_metadata", "formula_outcomes", "#/book", "build"),
                    (
                        "coverage-ancestor",
                        "native_metadata",
                        "recognition_coverage",
                        "#/book",
                        "build",
                    ),
                    (
                        "coverage-selected",
                        "native_metadata",
                        "recognition_coverage",
                        "#/child",
                        "build",
                    ),
                    (
                        "coverage-sibling",
                        "native_metadata",
                        "recognition_coverage",
                        "#/sibling",
                        "build",
                    ),
                    ("unknown", "native_metadata", "unknown", "#/section", "build"),
                    ("other-family", "health", "formula_outcomes", "#/section", "build"),
                    ("stale", "native_metadata", "formula_outcomes", "#/section", "other"),
                ]
            ],
        )
        published = select(literal("build", Text()).label("build_id")).cte("published")
        _, _, selected, ancestors = selected_membership_relations(
            metadata, published=published, section=literal("#/section", Text())
        )
        contained, selected_metadata = selected_content_relations(
            metadata, selected, ancestors, published=published
        )
        query = union_all(
            select(literal("record").label("kind"), contained.c.record_id.label("id")),
            select(literal("metadata").label("kind"), selected_metadata.c.local_id.label("id")),
        )
        assert set(connection.execute(query).all()) == {
            ("record", "root"),
            ("record", "nested"),
            ("record", "member"),
            ("metadata", "formula-selected"),
            ("metadata", "coverage-selected"),
            ("metadata", "coverage-ancestor"),
        }
