"""The declared forward upgrade from semantic pins to exact published addresses.

Alembic still owns ordinary DDL. This orders its generated placement additions around
an exact old-row precondition and backfill; it never creates compatibility publications.
The resulting ordinary operations are frozen by the migration author, not regenerated
by deployment. The caller retains its normal migration transaction and owning role.
"""

from __future__ import annotations

from alembic.operations import ops
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import dialect

from .metadata import table
from .native_objects import NativeAuthoringError
from .published_document import published_address_precondition_sql

_RELATIONS = ("kb.source_view", "ops.native_region_artifact")
_COLUMNS = ("native_build_id", "native_revision_id")


def _backfill_sql() -> str:
    published = table("ops.pdf_published_revision")
    statements = []
    for name in _RELATIONS:
        relation = table(name)
        key = next(
            key
            for key in relation.foreign_key_constraints
            if key.referred_table.fullname == published.fullname
        )
        matches = [
            relation.c[element.parent.name] == published.c[element.column.name]
            for element in key.elements
            if element.parent.name not in _COLUMNS
        ]
        statement = (
            update(relation)
            .where(*matches)
            .values(**{column: published.c.build_id for column in _COLUMNS})
        )
        sql = str(statement.compile(dialect=dialect(), compile_kwargs={"literal_binds": True}))
        # No other trigger is touched. An unexpected prior trigger state refuses
        # rather than silently restoring a different protection configuration.
        statements.append(f"""DO $placement$
DECLARE owner_name text; previous_role text:=current_setting('role');
BEGIN
 IF NOT EXISTS(SELECT FROM pg_trigger WHERE tgrelid='{name}'::regclass
 AND tgname='semantic_immutable' AND NOT tgisinternal AND tgenabled='O') THEN
 RAISE EXCEPTION 'published address migration requires enabled semantic_immutable on {name}'
 USING ERRCODE='55000'; END IF;
 SELECT pg_get_userbyid(relowner) INTO STRICT owner_name FROM pg_class
 WHERE oid='{name}'::regclass;
 EXECUTE format('SET LOCAL ROLE %I',owner_name);
 ALTER TABLE {name} DISABLE TRIGGER semantic_immutable;
 {sql};
 ALTER TABLE {name} ENABLE TRIGGER semantic_immutable;
 IF previous_role='none' THEN EXECUTE 'SET LOCAL ROLE NONE';
 ELSE EXECUTE format('SET LOCAL ROLE %I',previous_role); END IF;
END $placement$;""")
    return "\n".join(statements)


def order_published_address_upgrade(upgrade: ops.UpgradeOps) -> None:
    """Order this complete four-column addition, leaving unrelated diffs intact.

    Current-candidate comparison has no additions and remains empty. Partial prior
    upgrades or unexpected placement declarations need a separately owned transition.
    """
    additions = {}
    retained = []
    publication_keys = []
    for operation in upgrade.ops:
        if not isinstance(operation, ops.ModifyTableOps):
            retained.append(operation)
            continue
        relation = f"{operation.schema}.{operation.table_name}"
        remaining = []
        for child in operation.ops:
            if (
                relation in _RELATIONS
                and isinstance(child, ops.AddColumnOp)
                and child.column.name in _COLUMNS
            ):
                additions[relation, child.column.name] = child
            elif (
                relation == "ops.pdf_published_revision"
                and isinstance(child, ops.CreateUniqueConstraintOp)
                and tuple(child.columns) == ("build_id", "task_id", "product_key", "logical_digest")
            ):
                publication_keys.append(
                    ops.ModifyTableOps(
                        operation.table_name,
                        [child],
                        schema=operation.schema,
                    )
                )
            else:
                remaining.append(child)
        if remaining:
            retained.append(
                ops.ModifyTableOps(
                    operation.table_name,
                    remaining,
                    schema=operation.schema,
                )
            )
    if not additions:
        return
    expected = {(name, column) for name in _RELATIONS for column in _COLUMNS}
    if set(additions) != expected:
        raise NativeAuthoringError(
            "published address upgrade requires all four placement additions"
        )
    nullable = []
    required = []
    for name in _RELATIONS:
        schema, relation = name.split(".")
        for column_name in _COLUMNS:
            operation = additions[name, column_name]
            column = operation.column._copy()
            if column.nullable or column.server_default is not None:
                raise NativeAuthoringError(
                    "published placement addition must be required without a default"
                )
            column.nullable = True
            nullable.append(ops.AddColumnOp(relation, column, schema=schema))
            required.append(
                ops.AlterColumnOp(
                    relation,
                    column_name,
                    schema=schema,
                    existing_type=column.type,
                    existing_nullable=True,
                    modify_nullable=False,
                )
            )
    # Native dependencies and admission follow the complete ordinary placement
    # transition. Preserve their already-declared provider/dependent ordering.
    from .alembic_native import NativeTransitionOp

    native = [operation for operation in retained if isinstance(operation, NativeTransitionOp)]
    ordinary = [
        operation for operation in retained if not isinstance(operation, NativeTransitionOp)
    ]
    upgrade.ops[:] = [
        ops.ExecuteSQLOp(published_address_precondition_sql()),
        *publication_keys,
        *nullable,
        ops.ExecuteSQLOp(_backfill_sql()),
        *required,
        *ordinary,
        *native,
    ]
