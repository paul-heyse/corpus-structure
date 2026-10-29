"""Reviewed PostgreSQL gap companion: protected staging, semantic checks and publication.

Fixed relation and column names come from the immutable transport contract. Domain
identifiers are data, never SQL identifiers. Deploy this with the bootstrap migration.
"""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from unicodedata import unidata_version

from sqlalchemy import Connection

from .publication import STAGE_TYPES

_SQL = Path(__file__).with_name("sql")


def _transport_sql(writer: str) -> tuple[str, str, str, str]:
    create, verify, content, insert = [], [], [], []
    for name, (row_type, types) in STAGE_TYPES.items():
        columns = [f.name for f in fields(row_type)]
        definition = ",".join(
            f'"{column}" {typ}' for column, typ in zip(columns, types, strict=True)
        )
        names = ",".join(f'"{column}"' for column in columns)
        create.append(
            f"IF to_regclass('pg_temp.sp_{name}') IS NOT NULL THEN "
            "RAISE EXCEPTION 'preexisting staging relation'; END IF; "
            f"CREATE TEMP TABLE sp_{name}({definition}) ON COMMIT DROP; "
            f"GRANT INSERT ({names}) ON pg_temp.sp_{name} TO {writer};"
        )
        signatures = ",".join("'" + c + ":" + t + "'" for c, t in zip(columns, types, strict=True))
        verify.append(
            "IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE "
            f"c.relnamespace=pg_my_temp_schema() AND c.relname='sp_{name}' "
            "AND c.relkind='r' AND c.relpersistence='t' "
            "AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) "
            "AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) "
            "ORDER BY a.attnum) FROM pg_catalog.pg_attribute a "
            "WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)="
            f"ARRAY[{signatures}]) THEN "
            f"RAISE EXCEPTION 'untrusted staging relation sp_{name}'; END IF;"
        )
        expressions = [
            f'"{c}"::text'
            if name == "typed_value" and c in {"integer_value", "numeric_value"}
            else f'"{c}"'
            for c in columns
        ]
        row = "jsonb_build_array(" + ",".join(expressions) + ")"
        content.append(
            f"'{name}',COALESCE((SELECT jsonb_agg(j "
            'ORDER BY data.canonical_json(j) COLLATE "C") '
            f"FROM (SELECT {row} j FROM pg_temp.sp_{name}) q),'[]'::jsonb)"
        )
        target_columns = "release_id,realization_id," + names
        values = "r,z," + names
        if name == "occurrence":
            target_columns += ",batch_id"
            values += ",b"
        if name == "selection":
            insert.append((_SQL / "selection.sql").read_text())
            continue
        if name == "fact":
            insert.append((_SQL / "fact.sql").read_text())
            continue
        # Existing payload IDs cannot silently bind different values. Compare full row data.
        insert.append(
            f"INSERT INTO data.{name}({target_columns}) "
            f"SELECT {values} FROM pg_temp.sp_{name} ON CONFLICT DO NOTHING; "
            f"IF EXISTS(SELECT {names} FROM pg_temp.sp_{name} "
            f"EXCEPT SELECT {names} FROM data.{name} WHERE release_id=r "
            "AND realization_id=z) THEN "
            f"RAISE EXCEPTION 'conflicting existing {name}' USING ERRCODE='23505'; END IF;"
        )
    return "\n".join(create), "\n".join(verify), ",\n".join(content), "\n".join(insert)


def deploy_routines(
    connection: Connection,
    *,
    publisher_role: str = "corpus_sem_publisher",
    writer_role: str = "corpus_sem_writer",
    reader_role: str = "corpus_sem_reader",
) -> None:
    """Deploy bodies, owners and revokes in the caller's single migration transaction."""
    connection = connection.execution_options(no_parameters=True)
    quote = connection.dialect.identifier_preparer.quote
    publisher, writer, reader = map(quote, (publisher_role, writer_role, reader_role))
    if (
        unidata_version != "16.0.0"
        or connection.exec_driver_sql("SELECT pg_catalog.unicode_version()").scalar_one() != "16.0"
    ):
        raise ValueError(
            "native semantic casefold requires qualified Unicode 16 in Python and PostgreSQL"
        )
    database = quote(connection.exec_driver_sql("SELECT current_database()").scalar_one())
    for statement in (
        f"REVOKE TEMP ON DATABASE {database} FROM PUBLIC",
        f"GRANT TEMP ON DATABASE {database} TO {publisher}",
        f"GRANT USAGE,CREATE ON SCHEMA data TO {publisher}",
        f"GRANT USAGE ON SCHEMA sem TO {publisher}",
        f"GRANT SELECT ON ALL TABLES IN SCHEMA sem TO {publisher}",
        f"GRANT SELECT,INSERT,UPDATE ON ALL TABLES IN SCHEMA data TO {publisher}",
        f"REVOKE ALL ON ALL TABLES IN SCHEMA data,sem FROM {writer},{reader},PUBLIC",
        f"GRANT USAGE ON SCHEMA data,sem TO {writer},{reader}",
        f"GRANT SELECT ON ALL TABLES IN SCHEMA data,sem TO {reader}",
        f"GRANT SELECT ON data.batch TO {writer}",
        f"GRANT DELETE ON data.selection TO {publisher}",
    ):
        connection.exec_driver_sql(statement)
    connection.exec_driver_sql((_SQL / "identity.sql").read_text())
    connection.exec_driver_sql((_SQL / "validation.sql").read_text())
    create, verify, content, insert = _transport_sql(writer)
    publication = (_SQL / "publication.sql").read_text()
    for marker, source in (
        ("create", create),
        ("verify", verify),
        ("content", content),
        ("insert", insert),
    ):
        publication = publication.replace("{" + marker + "}", source)
    connection.exec_driver_sql(publication)

    signatures = (
        "canonical_json(jsonb)",
        "decimal_canonical(text)",
        "fact_identity(text,text,text,text,text,text)",
        "compare_decimal(text,text)",
        "value_meaning(text,text,text,text[],boolean)",
        "value_matches(text,text,text,text,boolean)",
        "validate_state(text,text)",
        "validate_property(text,text,text,text,jsonb)",
        "begin_stage()",
        "publish_batch(text,text,text,bytea)",
    )
    for signature in signatures:
        connection.exec_driver_sql(f"ALTER FUNCTION data.{signature} OWNER TO {publisher}")
        connection.exec_driver_sql(
            f"REVOKE ALL ON FUNCTION data.{signature} FROM PUBLIC,{writer},{reader}"
        )
    for signature in ("begin_stage()", "publish_batch(text,text,text,bytea)"):
        connection.exec_driver_sql(f"GRANT EXECUTE ON FUNCTION data.{signature} TO {writer}")
