"""Reviewed PostgreSQL gap companion: protected staging, semantic checks and publication.

Fixed relation and column names come from the immutable transport contract. Domain
identifiers are data, never SQL identifiers. Deploy this with the bootstrap migration.
"""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from .publication import STAGE_TYPES

_SQL = Path(__file__).with_name("sql")


def _transport_sql(
    writer: str, *, relation_order: tuple[str, ...] | None = None
) -> tuple[str, str, str, str]:
    create, verify, content, insert = [], [], [], []
    order = tuple(STAGE_TYPES) if relation_order is None else relation_order
    if len(order) != len(set(order)) or set(order) != set(STAGE_TYPES):
        raise ValueError("transport order must contain each declared relation exactly once")
    for name in order:
        row_type, types = STAGE_TYPES[name]
        columns = [f.name for f in fields(row_type)]
        from .metadata import table
        from .types import Diagnostic, PreparationError
        target = table("data." + name)
        unknown = set(columns) - set(target.c.keys()) - ({"selected"} if name == "selection" else set())
        if unknown:
            raise PreparationError((Diagnostic(
                "unsupported_transport_shape", name, "transport fields lack a physical target",
                contract_id=name, consumer="protected publication",
                expected=repr(tuple(target.c.keys())), actual=repr(tuple(columns)),
                remedy="add the corresponding physical model fields and forward migration before deriving transport SQL",
            ),))
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
            f'"{c}"::text' if types[columns.index(c)] == "numeric" else f'"{c}"' for c in columns
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


def stage_disposal_sql(
    *, optional: frozenset[str] = frozenset({"identity_exclusion", "identity_exclusion_evidence"})
) -> str:
    """Verify every present relation before disposal; optional absence is deliberate."""
    if not optional.issubset(STAGE_TYPES):
        raise ValueError("unknown optional transport relation")
    clauses = []
    for name, (row_type, types) in STAGE_TYPES.items():
        columns = [field.name for field in fields(row_type)]
        signatures = ",".join(
            "'" + column + ":" + kind + "'" for column, kind in zip(columns, types, strict=True)
        )
        verify = (
            "IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() "
            "AND c.relname='sp_"
            f"{name}"
            "' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=current_user::regr"
            "ole AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) "
            "ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 A"
            "ND NOT a.attisdropped)=ARRAY["
            f"{signatures}"
            "]) THEN RAISE EXCEPTION 'untrusted staging relation sp_"
            f"{name}"
            "'; END IF; DROP TABLE pg_temp.sp_"
            f"{name}"
            ";"
        )
        if name in optional:
            verify = f"IF to_regclass('pg_temp.sp_{name}') IS NOT NULL THEN " + verify + " END IF;"
        clauses.append(verify)
    return "\n".join(clauses)
