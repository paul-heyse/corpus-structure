"""The PostgreSQL18 SQL-standard function body comparison profile.

Deployment statements are retained separately. PostgreSQL's decompiled definition and
symbolic dependencies compare bound objects; raw pg_node_tree/OID bytes are not identities.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace

from pglast import ast
from pglast.stream import RawStream

SQL_STANDARD_PROFILE = "postgresql-18-sql-standard-v1"
SQL_STANDARD_MAJOR = 18


def sql_standard_definition(definition, statement):
    """Construct one SELECT body from Core while retaining its declared envelope."""
    from sqlalchemy.dialects.postgresql import dialect

    from .prepared_sql import prepare_sql

    body = (
        prepare_sql(
            str(
                statement.compile(
                    dialect=dialect(paramstyle="named"), compile_kwargs={"literal_binds": True}
                )
            ),
            source=definition.source + ":Core body",
        )
        .private_tree()[0]
        .stmt
    )
    if not isinstance(body, ast.SelectStmt):
        raise ValueError("selected SQL-standard profile requires one Core SELECT")
    envelope = prepare_sql(definition.sql, source=definition.source).private_tree()[0].stmt
    if not isinstance(envelope, ast.CreateFunctionStmt):
        raise ValueError("SQL-standard body requires a function declaration")
    options = []
    for option in envelope.options or ():
        if option.defname == "as":
            continue
        if option.defname == "language":
            option.arg = ast.String(sval="sql")
        options.append(option)
    envelope.options = tuple(options)
    envelope.sql_body = ((body,),)
    return replace(
        definition, sql=RawStream()(envelope), source=definition.source + ":sql-standard"
    )


def published_revision_definition(definition):
    """The exact published product pin, with private build state independently checked."""
    from sqlalchemy import literal_column, select

    from .metadata import table

    published, build = table("ops.pdf_published_revision"), table("ops.pdf_stage_build")
    statement = (
        select(published)
        .select_from(published.join(build, published.c.build_id == build.c.build_id))
        .where(
            published.c.task_id == literal_column("p_task", type_=published.c.task_id.type),
            published.c.product_key == literal_column("p_key", type_=published.c.product_key.type),
            published.c.logical_digest
            == literal_column("p_digest", type_=published.c.logical_digest.type),
            build.c.state == "published",
        )
    )
    return sql_standard_definition(definition, statement)


def published_validation_statement():
    """The original immutable receipt for an exact published pin, without revalidation."""
    from sqlalchemy import and_, literal_column, select

    from .metadata import table

    published = table("ops.pdf_published_revision")
    build = table("ops.pdf_stage_build")
    frozen = table("ops.pdf_frozen_build")
    product = table("ops.pdf_product")
    validation = table("ops.pdf_build_validation")
    native = table("ops.pdf_native_validation")
    return (
        select(validation)
        .select_from(
            published.join(
                build,
                and_(
                    build.c.build_id == published.c.build_id,
                    build.c.task_id == published.c.task_id,
                    build.c.release_id == published.c.release_id,
                    build.c.source_digest == published.c.source_digest,
                    build.c.schema_digest == published.c.schema_digest,
                    build.c.recipe_digest == published.c.recipe_digest,
                ),
            )
            .join(
                frozen,
                and_(
                    frozen.c.build_id == published.c.build_id,
                    frozen.c.frozen_digest == published.c.frozen_digest,
                    frozen.c.kind == published.c.kind,
                ),
            )
            .join(
                product,
                and_(
                    product.c.task_id == published.c.task_id,
                    product.c.product_key == published.c.product_key,
                    product.c.content_digest == published.c.logical_digest,
                    product.c.release_id == published.c.release_id,
                    product.c.artifact_digest == published.c.source_digest,
                    product.c.kind == published.c.kind,
                ),
            )
            .join(
                validation,
                and_(
                    validation.c.build_id == published.c.build_id,
                    validation.c.frozen_digest == published.c.frozen_digest,
                    validation.c.logical_digest == published.c.logical_digest,
                    validation.c.contract_digest == product.c.contract_digest,
                ),
            )
            .join(
                native,
                and_(
                    native.c.build_id == validation.c.build_id,
                    native.c.frozen_digest == validation.c.frozen_digest,
                    native.c.contract_digest == validation.c.native_contract_digest,
                ),
            )
        )
        .where(
            published.c.task_id == literal_column("p_task", type_=published.c.task_id.type),
            published.c.product_key == literal_column("p_key", type_=published.c.product_key.type),
            published.c.logical_digest
            == literal_column("p_digest", type_=published.c.logical_digest.type),
            build.c.state == "published",
            validation.c.native_callbacks.is_(True),
            native.c.passed.is_(True),
        )
    )


def published_validation_definition(definition):
    return sql_standard_definition(definition, published_validation_statement())


def body_source(statement: ast.CreateFunctionStmt) -> str:
    """Declared source representation, never a claim of server-bound equivalence."""
    options = {option.defname: option.arg for option in statement.options or ()}
    if statement.sql_body is None:
        if "as" not in options or len(options["as"]) != 1:
            raise ValueError("native function requires one source body")
        return options["as"][0].sval
    if "as" in options or "language" not in options or options["language"].sval != "sql":
        raise ValueError("SQL-standard body requires LANGUAGE sql and no AS body")
    if isinstance(statement.sql_body, ast.Node):
        return RawStream()(statement.sql_body)
    return "BEGIN ATOMIC " + RawStream()(statement.sql_body[0]) + "; END"


def dependency_query(oid: str) -> str:
    """One fixed catalog expression shared by observation and native admission."""
    return f"""SELECT COALESCE(jsonb_agg(jsonb_build_object(
 'kind',d.deptype,'type',i.type,'schema',i.schema,'name',i.name,'identity',i.identity)
 ORDER BY d.deptype::text COLLATE \"C\",i.type COLLATE \"C\",i.schema COLLATE \"C\",
 i.name COLLATE \"C\",i.identity COLLATE \"C\"),'[]'::jsonb)
 FROM pg_depend d CROSS JOIN LATERAL
 pg_identify_object(d.refclassid,d.refobjid,d.refobjsubid) i
 WHERE d.classid='pg_proc'::regclass AND d.objid={oid}"""


@contextmanager
def catalog_path(connection):
    """Deparse against an explicit path and restore the caller's setting."""
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    previous = connection.scalar(text("SELECT current_setting('search_path')"))
    connection.execute(text("SELECT set_config('search_path','pg_catalog,pg_temp',true)"))
    failed = False
    try:
        yield
    except DBAPIError:
        failed = True
        raise
    finally:
        if not failed:
            connection.execute(
                text("SELECT set_config('search_path',:previous,true)"), {"previous": previous}
            )


def admission_body_comparison() -> str:
    """Compare v1 AS bodies and v2 bound SQL bodies without a permissive fallback."""
    dependencies = dependency_query("p.oid")
    return f"""CASE WHEN item.value ? 'body_profile' THEN
 item.value->>'body_profile' IS DISTINCT FROM '{SQL_STANDARD_PROFILE}'
 OR item.value->>'body_kind' IS DISTINCT FROM 'sql_standard'
 OR item.value->>'server_major' IS DISTINCT FROM '{SQL_STANDARD_MAJOR}'
 OR (current_setting('server_version_num')::integer/10000)<>({SQL_STANDARD_MAJOR})
 OR p.prosqlbody IS NULL
 OR encode(sha256(convert_to(pg_get_functiondef(p.oid),'UTF8')),'hex')
 IS DISTINCT FROM item.value->>'body_sha256'
 OR ({dependencies}) IS DISTINCT FROM item.value->'dependencies'
 ELSE p.prosqlbody IS NOT NULL OR
 encode(sha256(convert_to(p.prosrc,'UTF8')),'hex')
 IS DISTINCT FROM item.value->>'body_sha256' END"""
