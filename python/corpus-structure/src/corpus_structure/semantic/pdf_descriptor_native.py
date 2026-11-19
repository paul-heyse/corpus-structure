"""Compile compact PDF descriptors directly from canonical wire bytes."""

from sqlalchemy import Text, cast, column, func, literal, select
from sqlalchemy.dialects.postgresql import BYTEA, JSON, JSONB

from corpus_structure.schema.integrity import role_name

from .native_objects import (
    INTERNAL_PROGRAM,
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
    NativeRoutine,
    Parameter,
    Return,
    SelectInto,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration


def pdf_descriptor_programs() -> tuple[ProgramDeclaration, ...]:
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
    routine = NativeRoutine(
        "ops",
        "pdf_product_descriptor",
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
    return (
        ProgramDeclaration(
            routine,
            source="target-current:PDF descriptor CHECK prerequisite",
            owner=role_name("publisher"),
            access=INTERNAL_PROGRAM,
        ),
    )


def pdf_descriptor_sql() -> str:
    """Render the captured descriptor statement and its existing ACL projection."""
    return native_sql_script(
        statement
        for declaration in pdf_descriptor_programs()
        for statement in (
            declaration.routine.render(),
            native_owner_sql(declaration.identity, declaration.owner),
            native_privilege_sql(declaration.identity, "PUBLIC", grant=False),
        )
    )
