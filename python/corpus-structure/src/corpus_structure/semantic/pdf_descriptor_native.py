"""Compile compact PDF descriptors directly from canonical wire bytes."""

from sqlalchemy import Text, cast, column, func, literal, select
from sqlalchemy.dialects.postgresql import BYTEA, JSON, JSONB

from corpus_structure.schema.integrity import role_name

from .native_objects import (
    NativeIdentity,
    native_owner_sql,
    native_privilege_sql,
    native_sql_script,
)
from .native_program import (
    Assign,
    Block,
    ForQuery,
    If,
    Local,
    Parameter,
    Return,
    SelectInto,
    core_variable,
    function,
    pg_type,
)


def pdf_descriptor_sql() -> str:
    """Keep large record collections in JSON while retaining compact JSONB metadata."""
    payload = core_variable("p_payload", BYTEA())
    result = core_variable("result", JSONB())
    field_name = core_variable("field_name", Text())
    field_value = core_variable("field_value", JSON())
    content_metadata = core_variable("content_metadata", JSONB())
    empty = cast(literal("{}"), JSONB())
    fields = func.json_each(cast(func.convert_from(payload, "UTF8"), JSON())).table_valued(
        column("key", Text()), column("value", JSON())
    )
    content = func.json_each(field_value).table_valued(
        column("key", Text()), column("value", JSON())
    )
    identity = NativeIdentity("function", "ops", "pdf_product_descriptor", ("bytea",))
    definition = function(
        "ops",
        identity.name,
        parameters=(Parameter("p_payload", pg_type("bytea")),),
        returns=pg_type("jsonb"),
        body=Block(
            (
                ForQuery(
                    ("field_name", "field_value"),
                    select(fields.c.key, fields.c.value),
                    (
                        If(
                            field_name == "content",
                            (
                                SelectInto(
                                    select(
                                        func.coalesce(
                                            func.jsonb_object_agg(
                                                content.c.key, cast(content.c.value, JSONB())
                                            ),
                                            empty,
                                        )
                                    ).where(
                                        content.c.key.in_(
                                            ("schema_digest", "recipe_digest", "health")
                                        )
                                    ),
                                    ("content_metadata",),
                                ),
                            ),
                            (
                                If(
                                    field_name.not_in(
                                        (
                                            "occurrences",
                                            "relations",
                                            "coverage",
                                            "inputs",
                                            "mapping_reports",
                                        )
                                    ),
                                    (
                                        Assign(
                                            "result",
                                            result.op("||")(
                                                func.jsonb_build_object(
                                                    field_name, cast(field_value, JSONB())
                                                )
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
                If(
                    result["kind"].astext == "integrated",
                    (
                        Assign(
                            "result",
                            result.op("||")(
                                func.jsonb_build_object("content_metadata", content_metadata)
                            ),
                        ),
                    ),
                ),
                Return(result),
            ),
            (
                Local("result", pg_type("jsonb"), empty),
                Local("content_metadata", pg_type("jsonb"), empty),
                Local("field_name", pg_type("text")),
                Local("field_value", pg_type("json")),
            ),
        ),
        volatility="immutable",
        strict=True,
        search_path=("pg_catalog", "pg_temp"),
    )
    return native_sql_script(
        (
            definition,
            native_owner_sql(identity, role_name("publisher")),
            native_privilege_sql(identity, "PUBLIC", grant=False),
        )
    )
