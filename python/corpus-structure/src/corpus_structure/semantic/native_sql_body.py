"""The PostgreSQL18 SQL-standard function body comparison profile.

Deployment statements are retained separately. PostgreSQL's decompiled definition and
symbolic dependencies compare bound objects; raw pg_node_tree/OID bytes are not identities.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace

from pglast import ast
from pglast.stream import RawStream

from .native_program import core_reference

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


def published_revision_statement(*, target_metadata=None):
    """The exact published product pin, with private build state independently checked."""
    from sqlalchemy import select

    from .metadata import table as default_table

    table = default_table if target_metadata is None else target_metadata.tables.__getitem__

    published, build = table("ops.pdf_published_revision"), table("ops.pdf_stage_build")
    return (
        select(published)
        .select_from(published.join(build, published.c.build_id == build.c.build_id))
        .where(
            published.c.task_id == core_reference("p_task", type_=published.c.task_id.type),
            published.c.product_key == core_reference("p_key", type_=published.c.product_key.type),
            published.c.logical_digest
            == core_reference("p_digest", type_=published.c.logical_digest.type),
            build.c.state == "published",
        )
    )


def published_validation_statement(*, target_metadata=None):
    """The original immutable receipt for an exact published pin, without revalidation."""
    from sqlalchemy import and_, or_, select

    from .metadata import table as default_table

    table = default_table if target_metadata is None else target_metadata.tables.__getitem__

    published = table("ops.pdf_published_revision")
    build = table("ops.pdf_stage_build")
    frozen = table("ops.pdf_frozen_build")
    product = table("ops.pdf_product")
    validation = table("ops.pdf_build_validation")
    producer = table("ops.pdf_producer_certification")
    oracle = table("ops.pdf_roundtrip_oracle")
    oracle_publication = published.alias("oracle_publication")
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
                producer,
                and_(
                    producer.c.build_id == validation.c.build_id,
                    producer.c.lowering_identity == validation.c.lowering_identity,
                    producer.c.logical_digest == validation.c.attested_logical_digest,
                    producer.c.logical_digest == published.c.logical_digest,
                    producer.c.native_document_digest == validation.c.native_document_digest,
                    producer.c.kind == published.c.kind,
                ),
            )
            .join(
                oracle,
                and_(
                    oracle.c.oracle_receipt_id == validation.c.oracle_receipt_id,
                    oracle.c.lowering_identity == validation.c.lowering_identity,
                    oracle.c.kind == published.c.kind,
                ),
            )
            .outerjoin(
                oracle_publication,
                and_(
                    oracle_publication.c.build_id == oracle.c.build_id,
                    oracle_publication.c.frozen_digest == oracle.c.frozen_digest,
                    oracle_publication.c.logical_digest == oracle.c.logical_digest,
                    oracle_publication.c.kind == oracle.c.kind,
                ),
            )
        )
        .where(
            published.c.task_id == core_reference("p_task", type_=published.c.task_id.type),
            published.c.product_key == core_reference("p_key", type_=published.c.product_key.type),
            published.c.logical_digest
            == core_reference("p_digest", type_=published.c.logical_digest.type),
            build.c.state == "published",
            validation.c.native_callbacks.is_(True),
            oracle.c.state == "passed",
            oracle.c.actual_native_digest == oracle.c.native_document_digest,
            or_(
                and_(
                    validation.c.certification_basis == "round-trip-verified",
                    oracle.c.build_id == published.c.build_id,
                    oracle.c.frozen_digest == published.c.frozen_digest,
                    oracle.c.native_document_digest == producer.c.native_document_digest,
                ),
                and_(
                    validation.c.certification_basis == "producer-certified",
                    oracle_publication.c.build_id.is_not(None),
                ),
            ),
        )
    )


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


@contextmanager
def catalog_path(connection):
    """Deparse against an explicit path and restore the caller's setting."""
    from sqlalchemy import select
    from sqlalchemy.exc import DBAPIError

    from .native_catalog import pg

    previous = connection.scalar(select(pg.current_setting("search_path")))
    connection.execute(select(pg.set_config("search_path", "pg_catalog,pg_temp", True)))
    failed = False
    try:
        yield
    except DBAPIError:
        failed = True
        raise
    finally:
        if not failed:
            connection.execute(select(pg.set_config("search_path", previous, True)))


def admission_body_comparison(item, procedure):
    """Compare stored AS bodies and server-bound SQL bodies through catalog facts."""
    from sqlalchemy import Integer, case, cast, literal, or_

    from .native_catalog import dependencies, pg

    columns = procedure.c

    def body_hash(definition):
        return pg.encode(pg.sha256(pg.convert_to(definition, "UTF8")), "hex")

    major = cast(pg.current_setting("server_version_num"), Integer()).op(
        "/", return_type=Integer()
    )(literal(10000))
    observed_dependencies = dependencies(columns.oid).correlate(procedure).scalar_subquery()
    expected_hash = item["body_sha256"].astext
    return case(
        (
            item.has_key("body_profile"),
            or_(
                item["body_profile"].astext.is_distinct_from(SQL_STANDARD_PROFILE),
                item["body_kind"].astext.is_distinct_from("sql_standard"),
                item["server_major"].astext.is_distinct_from(str(SQL_STANDARD_MAJOR)),
                major != SQL_STANDARD_MAJOR,
                columns.prosqlbody.is_(None),
                body_hash(pg.pg_get_functiondef(columns.oid)).is_distinct_from(expected_hash),
                observed_dependencies.is_distinct_from(item["dependencies"]),
            ),
        ),
        else_=or_(
            columns.prosqlbody.is_not(None),
            body_hash(columns.prosrc).is_distinct_from(expected_hash),
        ),
    )
