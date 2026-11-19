"""Current native candidate preparation and frozen Alembic lifecycle helpers."""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path

from alembic.autogenerate import produce_migrations
from alembic.migration import MigrationContext
from alembic.operations.ops import MigrateOperation, MigrationScript, UpgradeOps
from pglast import ast, enums
from pglast.stream import RawStream
from sqlalchemy import cast, func, literal, select
from sqlalchemy.dialects.postgresql import JSONB, dialect
from sqlalchemy.exc import DBAPIError

from corpus_structure.schema.integrity import role_name

from . import native_catalog as catalog
from .alembic_checks import plugin as checks_plugin
from .alembic_defaults import compare_default, compare_type
from .alembic_defaults import plugin as defaults_plugin
from .alembic_indexes import plugin as indexes_plugin
from .alembic_native import plugin as native_plugin
from .alembic_privileges import PrivilegePolicy, policy_fact, table_policy
from .native_objects import (
    INTERNAL_PROGRAM,
    NativeAuthoringError,
    NativeIdentity,
    NativeObject,
    NativeProgramAccess,
    definition_from_sql,
    execute_native_sql,
    native_owner_sql,
    native_role_sql,
    native_sql_script,
)
from .prepared_sql import prepare_sql


@dataclass(frozen=True)
class NativeCandidate:
    migration: MigrationScript
    privilege_policies: tuple[PrivilegePolicy, ...]

    @property
    def upgrade_ops(self) -> UpgradeOps | None:
        return self.migration.upgrade_ops


def final_native_catalog(objects, policies):
    """Project derived trigger ownership after explicit table policy transitions.

    Transition operations retain their intermediate before/after owners. The final
    admission snapshot instead describes the completed migration, where PostgreSQL
    gives each trigger its parent table's declared owner.
    """
    owners = {policy["name"]: policy["owner"] for policy in policies if policy["kind"] == "table"}
    result = []
    for item in objects:
        if item.identity.kind == "trigger" and item.identity.relation is not None:
            parent = item.identity.schema + "." + item.identity.relation
            if parent in owners:
                if owners[parent] is None:
                    raise NativeAuthoringError("declared parent table lacks its owner")
                if item.role_bindings not in ((), (("$migration_owner", "sem_namespace_owner"),)):
                    raise NativeAuthoringError("unresolved final trigger namespace binding")
                item = replace(
                    item,
                    catalog_json=json.dumps(
                        {**item.catalog, "owner": owners[parent]}, sort_keys=True
                    ),
                    role_bindings=(),
                    binding_version=1,
                )
        result.append(item)
    return tuple(result)


def _shape_definition(connection, sql, *, source):
    prepared = prepare_sql(sql, source=source)
    for index, raw in enumerate(prepared.statements):
        statement = raw.stmt
        if isinstance(statement, ast.CreateFunctionStmt) and tuple(
            part.sval for part in statement.funcname or ()
        ) == ("ops", "pdf_native_record_shape"):
            return definition_from_sql(
                connection,
                prepared.excerpt(index),
                source=source,
                owner=role_name("publisher"),
                program_access=INTERNAL_PROGRAM,
            )
    raise NativeAuthoringError(f"{source}: native record shape declaration is absent")


def _pdf_payload_definitions(connection, sql, *, source):
    from corpus_structure.schema.integrity import integrity

    from .native_function_signatures import function_signature
    from .native_inventory import update_function_inventory

    inventory = {}
    prepared = update_function_inventory(inventory, sql)
    purposes_by_role = {role: purpose for purpose, role in integrity().purposes.items() if role}
    definitions = {}
    for index, raw in enumerate(prepared.statements):
        statement = raw.stmt
        if not isinstance(statement, ast.CreateFunctionStmt):
            continue
        name = tuple(part.sval for part in statement.funcname or ())
        if len(name) != 2 or (
            name[0] != "ops" and name != ("sem", "admit_pdf_operation_contracts")
        ):
            continue
        # The compiled shape declaration has a dedicated owner.
        if name[1] == "pdf_native_record_shape":
            continue
        descriptor = inventory[function_signature(statement)]
        roles = descriptor["execute_roles"]
        owner = descriptor["owner"]
        try:
            purposes = tuple(purposes_by_role[role] for role in roles if role != owner)
        except KeyError as exc:
            raise NativeAuthoringError(
                f"{source}: undeclared PDF execute role {exc.args[0]}"
            ) from exc
        definition = definition_from_sql(
            connection,
            prepared.excerpt(index),
            source=source,
            owner=owner,
            program_access=NativeProgramAccess(
                purposes=purposes, internal=not purposes, owner_execute=owner in roles
            ),
        )
        # CREATE OR REPLACE can recur in a frozen collection; the last declaration
        # is the source authority, while the inventory carries its cumulative ACL.
        definitions[definition.identity] = definition
    return tuple(definitions.values())


def _publication_view_definitions(connection, sql, *, source):
    """Own the current published views and explicit ACLs."""
    prepared = prepare_sql(sql, source=source)
    definitions = {}
    for index, raw in enumerate(prepared.statements):
        statement = raw.stmt
        if (
            isinstance(statement, ast.ViewStmt)
            and statement.view is not None
            and statement.view.schemaname == "ops"
            and statement.view.relname
            in {
                "pdf_selected_product",
                "pdf_published_item",
                "pdf_published_region",
                "pdf_published_coverage",
            }
        ):
            roles = (role_name("writer"), role_name("reader"), role_name("evaluator"))
            if statement.view.relname == "pdf_selected_product":
                roles = (*roles, role_name("admitter"))
            definition = definition_from_sql(
                connection,
                prepared.excerpt(index),
                source=source,
                owner=role_name("publisher"),
                grants=tuple((role, "SELECT", False) for role in roles),
            )
            definitions[definition.identity] = definition
    if len(definitions) != 4:
        raise NativeAuthoringError(f"{source}: current published view declaration is absent")
    return tuple(definitions.values())


def _task_call_definition(
    connection,
    sql,
    *,
    name,
    source,
    program_access,
    schema="ops",
):
    """Require one exact declaration; overloaded owners select their complete family."""
    selected = _task_call_definitions(
        connection, sql, name=name, source=source, program_access=program_access, schema=schema
    )
    if len(selected) != 1:
        raise NativeAuthoringError("singular native function selection is ambiguous: " + name)
    return selected[0]


def _task_call_definitions(
    connection,
    sql,
    *,
    name,
    source,
    program_access,
    schema="ops",
):
    """Bind every declared overload with its own normalized ABI and ACL facts."""
    definitions = []
    prepared = prepare_sql(sql, source=source)
    for index, raw in enumerate(prepared.statements):
        statement = raw.stmt
        if isinstance(statement, ast.CreateFunctionStmt) and tuple(
            part.sval for part in statement.funcname or ()
        ) == (schema, name):
            definitions.append(
                definition_from_sql(
                    connection,
                    prepared.excerpt(index),
                    source=source,
                    owner=role_name("publisher"),
                    program_access=program_access,
                )
            )
    if definitions:
        return tuple(definitions)
    raise NativeAuthoringError(f"native task-call ABI declaration is absent: {name}")


def current_admission_definitions(connection, sql, *, source, require_descriptor=True):
    """Declare current purpose grants without historical migration-owner custody."""
    prepared = prepare_sql(sql, source=source)
    definitions = []
    for index, raw in enumerate(prepared.statements):
        statement = raw.stmt
        if not isinstance(statement, ast.CreateFunctionStmt):
            continue
        name = tuple(part.sval for part in statement.funcname or ())
        if name not in {
            ("data", "execution_contract_descriptor"),
            ("data", "require_execution_release"),
        }:
            continue
        purposes = (
            ("admit",)
            if name[1] == "execution_contract_descriptor"
            else ("write", "read", "evaluate", "admit")
        )
        definition = definition_from_sql(
            connection,
            prepared.excerpt(index),
            source=source + ":" + name[1],
            owner=role_name("publisher"),
            program_access=NativeProgramAccess(purposes=purposes),
        )
        definitions.append(definition)
    if len(definitions) != (2 if require_descriptor else 1) or (
        not require_descriptor and definitions[0].identity.name != "require_execution_release"
    ):
        raise NativeAuthoringError(
            f"{source}: admission requires its descriptor and enforcing guard"
        )
    return tuple(definitions)


def _declared_physical_catalog(connection, target_metadata):
    """Normalize declarations on empty temporary relations, independent of installed indexes."""
    from sqlalchemy.schema import CreateIndex, CreateTable

    from .native_admission import PhysicalCatalogExpectations
    from .native_program import literal as pg_literal

    postgres = dialect(paramstyle="named")
    preparer = postgres.identifier_preparer
    scratch = "semantic_candidate_catalog"
    scratch_relation = "pg_temp." + scratch
    indexes = []
    generated = {}
    defaults = {}
    attribute, default = catalog.attribute.c, catalog.attribute_default.c
    savepoint = connection.begin_nested()
    try:
        # Match the protecting guard's deparser search path.
        execute_native_sql(
            connection,
            RawStream()(
                ast.VariableSetStmt(
                    kind=enums.VariableSetKind.VAR_SET_VALUE,
                    name="search_path",
                    args=(pg_literal("pg_catalog"), pg_literal("pg_temp")),
                    is_local=True,
                )
            ),
        )
        for relation in sorted(target_metadata.tables.values(), key=lambda item: item.fullname):
            if not relation.indexes and not any(
                c.computed is not None or (c.identity is None and c.server_default is not None)
                for c in relation.columns
            ):
                continue
            target = preparer.format_table(relation)
            declaration = str(
                CreateTable(relation, include_foreign_key_constraints=[]).compile(dialect=postgres)
            )
            (table_statement,) = prepare_sql(declaration, source=relation.fullname).statements
            if not isinstance(table_statement.stmt, ast.CreateStmt):
                raise NativeAuthoringError(f"unexpected physical declaration for {target}")
            table_statement.stmt.relation = ast.RangeVar(
                schemaname="pg_temp", relname=scratch, inh=True, relpersistence="t"
            )
            execute_native_sql(connection, RawStream()(table_statement.stmt))
            # The scratch table's keys are absent from this selection. Only
            # model-declared standalone indexes enter the descriptor.
            for index in sorted(relation.indexes, key=lambda item: str(item.name)):
                ddl = str(CreateIndex(index).compile(dialect=postgres))
                (index_statement,) = prepare_sql(ddl, source=str(index.name)).statements
                if not isinstance(index_statement.stmt, ast.IndexStmt):
                    raise NativeAuthoringError(
                        f"unexpected index declaration target for {index.name}"
                    )
                index_statement.stmt.relation = ast.RangeVar(
                    schemaname="pg_temp", relname=scratch, inh=True
                )
                execute_native_sql(connection, RawStream()(index_statement.stmt))
                rendered_name = preparer.format_index(index)
                definition = connection.scalar(
                    select(
                        catalog.pg.pg_get_indexdef(
                            catalog.pg.to_regclass("pg_temp." + rendered_name)
                        )
                    )
                )
                if definition is None:
                    raise NativeAuthoringError(f"declared index was not created: {index.name}")
                header, separator, body = definition.partition(" USING ")
                scratch_targets = (" ON " + scratch, " ON " + scratch_relation)
                if not separator or not header.endswith(scratch_targets):
                    raise NativeAuthoringError(f"unexpected index catalog shape for {index.name}")
                prefix = header[: header.rindex(" ON ")]
                index_name = (
                    preparer.quote_schema(relation.schema) + "." + rendered_name
                    if relation.schema
                    else rendered_name
                )
                indexes.append(
                    dict(
                        index=index_name,
                        relation=relation.fullname,
                        definition=prefix + " ON " + target + separator + body,
                    )
                )
            normalized = connection.execute(
                select(
                    attribute.attname,
                    catalog.pg.pg_get_expr(default.adbin, default.adrelid),
                    attribute.attgenerated,
                )
                .select_from(
                    catalog.attribute.join(
                        catalog.attribute_default,
                        (default.adrelid == attribute.attrelid)
                        & (default.adnum == attribute.attnum),
                    )
                )
                .where(
                    attribute.attrelid == catalog.pg.to_regclass(scratch_relation),
                    attribute.attidentity == "",
                )
            ).all()
            generated[relation.fullname] = {
                name: expression for name, expression, kind in normalized if kind
            }
            defaults[relation.fullname] = {
                name: expression for name, expression, kind in normalized if not kind
            }
            _drop_authoring_scratch(connection, scratch)
    finally:
        savepoint.rollback()
    return PhysicalCatalogExpectations(
        tuple(sorted(indexes, key=lambda item: item["index"])), generated, defaults
    )


def _drop_authoring_scratch(connection, name):
    execute_native_sql(
        connection,
        RawStream()(
            ast.DropStmt(
                objects=((ast.String(sval="pg_temp"), ast.String(sval=name)),),
                removeType=enums.ObjectType.OBJECT_TABLE,
                behavior=enums.DropBehavior.DROP_RESTRICT,
            )
        ),
    )


def load_native_state(path: Path, *, digest: str | None = None) -> tuple[NativeObject, ...]:
    content = path.read_bytes()
    if digest is not None and sha256(content).hexdigest() != digest:
        raise NativeAuthoringError(f"{path.name}: native predecessor state digest differs")
    return _parse_native_state(content, path)[0]


def _parse_native_state(content: bytes, path: Path):
    try:
        payload = json.loads(content)
        if payload["version"] != 2 or not isinstance(payload["desired"], list):
            raise ValueError("unsupported native state format")
        from .alembic_privileges import native_operation_payloads

        native_operation_payloads(payload)
        objects = tuple(NativeObject.from_payload(value) for value in payload["desired"])
        if len({item.identity for item in objects}) != len(objects):
            raise ValueError("duplicate native identity")
        if "operations" in payload and not isinstance(payload["operations"], list):
            raise ValueError("native operations must be a list")
        return objects, payload
    except (KeyError, TypeError, ValueError) as error:
        raise NativeAuthoringError(
            f"{path.name}: invalid frozen native predecessor state: {error}"
        ) from error


def _read_revision_artifact(path: Path, digest: str) -> bytes:
    content = path.read_bytes()
    if sha256(content).hexdigest() != digest:
        raise NativeAuthoringError(f"{path.name}: frozen revision artifact digest differs")
    return content


def _current_revision_artifact(
    connection, filename_attribute: str, digest_attribute: str, *, script_location=None
):
    """Locate only declared, hash-bound predecessor source, never a live descriptor."""
    from alembic.script import ScriptDirectory

    from .migrations import alembic_config, current_revision

    revision = current_revision(connection)
    if revision is None:
        raise NativeAuthoringError("native authoring requires a declared current revision")
    script = ScriptDirectory.from_config(
        alembic_config(script_location=script_location)
    ).get_revision(revision)
    if script is None:
        raise NativeAuthoringError("native authoring requires a declared current revision")
    filename = getattr(script.module, filename_attribute, None)
    digest = getattr(script.module, digest_attribute, None)
    if (
        not isinstance(filename, str)
        or Path(filename).name != filename
        or not isinstance(digest, str)
    ):
        raise NativeAuthoringError(
            "current revision lacks frozen native artifact: " + filename_attribute
        )
    return Path(script.path).parent / filename, digest


def current_native_state(connection, *, script_location=None):
    """Read the current revision's declared immutable desired state, never live adoption."""
    source = _current_revision_artifact(
        connection, "NATIVE_STATE_FILE", "NATIVE_STATE_SHA256", script_location=script_location
    )
    return load_native_state(source[0], digest=source[1])


def _order_physical_retirement(upgrade_ops):
    """Remove FK dependencies before native replacement and stored relation retirement."""
    from alembic.operations import ops

    from .alembic_native import NativeTransitionOp

    native = [item for item in upgrade_ops.ops if isinstance(item, NativeTransitionOp)]
    drops = [item for item in upgrade_ops.ops if isinstance(item, ops.DropTableOp)]
    ordinary = [
        item
        for item in upgrade_ops.ops
        if not isinstance(item, (NativeTransitionOp, ops.DropTableOp))
    ]
    constraints = []
    for item in drops:
        # Alembic's reflected table ordering may contain cycles. These constraints
        # leave with their explicitly removed table, so retire their edges first.
        relation = item.to_table()
        constraints.extend(
            ops.DropConstraintOp.from_constraint(constraint)
            for constraint in sorted(
                relation.foreign_key_constraints, key=lambda constraint: str(constraint.name)
            )
        )
    upgrade_ops.ops[:] = [*ordinary, *constraints, *native, *drops]


def _order_row_type_evolution(connection, upgrade_ops, authoring):
    """Bracket physical row changes with exact declared dependent transitions.

    PostgreSQL refuses some table rewrites while SQL-standard bodies retain its
    composite type. The existing bounded catalog graph supplies ordering facts;
    frozen predecessors and declared targets supply every dropped/restored body.
    Unmanaged dependents remain a RESTRICT refusal, never an implicit CASCADE.
    """
    from alembic.operations import ops

    from .alembic_native import NativeTransitionOp
    from .graph_runtime import nx
    from .graph_topology import ordered_nodes, rooted_closure
    from .native_objects import native_dependency_graph

    relations = set()

    def visit(operation):
        if isinstance(operation, (ops.AddColumnOp, ops.DropColumnOp)) or (
            isinstance(operation, ops.AlterColumnOp) and operation.modify_type is not None
        ):
            relations.add(
                NativeIdentity("table", operation.schema or "public", operation.table_name)
            )
        for child in getattr(operation, "ops", ()):
            visit(child)

    visit(upgrade_ops)
    if not relations:
        return
    before = {item.identity: item for item in authoring.predecessor}
    identities = (*before, *sorted(relations, key=lambda identity: identity.qualified))
    graph = native_dependency_graph(connection, identities)
    selected = (rooted_closure(graph, relations) - relations) & before.keys()
    if not selected:
        return
    declared = {identity: position for position, identity in enumerate(graph)}
    try:
        order = ordered_nodes(graph, key=declared.__getitem__)
    except nx.NetworkXUnfeasible as error:
        raise NativeAuthoringError("physical/native row-type dependency scope is cyclic") from error
    native = [
        operation for operation in upgrade_ops.ops if isinstance(operation, NativeTransitionOp)
    ]
    physical = [
        operation
        for operation in upgrade_ops.ops
        if not isinstance(operation, (NativeTransitionOp, ops.DropTableOp))
    ]
    dropped_tables = [
        operation for operation in upgrade_ops.ops if isinstance(operation, ops.DropTableOp)
    ]
    retiring = [
        operation
        for operation in native
        if operation.after is None and operation.identity not in selected
    ]
    installing = {
        operation.identity: operation
        for operation in native
        if operation.after is not None and operation.identity not in selected
    }
    early = [
        NativeTransitionOp(before[identity], None)
        for identity in reversed(order)
        if identity in selected
    ]
    late = [
        NativeTransitionOp(None, item) if item.identity in selected else installing[item.identity]
        for item in authoring.desired
        if item.identity in selected or item.identity in installing
    ]
    upgrade_ops.ops[:] = [*early, *physical, *retiring, *late, *dropped_tables]


def _physical_check_contract(connection, target_metadata, authoring):
    """Normalize declared CHECKs through PostgreSQL, never enroll live table drift."""
    from sqlalchemy import CheckConstraint

    from corpus_structure.schema.relational import physical_expression_sql

    from .native_admission import _admission_descriptor
    from .native_program import column_type

    descriptor = next(
        item for item in authoring.desired if item.identity.name == "execution_contract_descriptor"
    )
    expected = _admission_descriptor(native_sql_script(descriptor.statements))
    contract = target_metadata.tables["sem.physical_contract"]
    present = connection.scalar(
        select(contract.c.source_digest).where(contract.c.physical_id == expected["physical_id"])
    )
    if present is not None:
        if present != expected["physical_checks_source_digest"]:
            raise NativeAuthoringError(
                "physical CHECK identity already has another source contract"
            )
        return None
    scratch = "semantic_candidate_check"
    constraint = catalog.constraint.c
    checks = []
    for relation in sorted(target_metadata.tables.values(), key=lambda item: item.fullname):
        constraints = sorted(
            (item for item in relation.constraints if isinstance(item, CheckConstraint)),
            key=lambda item: str(item.name),
        )
        if not constraints:
            continue
        table_items: list[ast.Node] = [
            ast.ColumnDef(colname=column.name, typeName=column_type(column))
            for column in relation.columns
        ]
        for item in constraints:
            (parsed,) = prepare_sql(
                "SELECT " + physical_expression_sql(item.sqltext), source=relation.fullname
            ).statements
            if not isinstance(parsed.stmt, ast.SelectStmt) or not parsed.stmt.targetList:
                raise NativeAuthoringError(f"invalid CHECK declaration for {relation.fullname}")
            (expression,) = parsed.stmt.targetList
            name = connection.dialect.identifier_preparer.format_constraint(
                item, _alembic_quote=False
            )
            if name is None:
                raise NativeAuthoringError(f"unnamed CHECK declaration for {relation.fullname}")
            table_items.append(
                ast.Constraint(
                    contype=enums.ConstrType.CONSTR_CHECK, conname=name, raw_expr=expression.val
                )
            )
        execute_native_sql(
            connection,
            RawStream()(
                ast.CreateStmt(
                    relation=ast.RangeVar(
                        schemaname="pg_temp", relname=scratch, inh=True, relpersistence="t"
                    ),
                    tableElts=tuple(table_items),
                    oncommit=enums.OnCommitAction.ONCOMMIT_DROP,
                )
            ),
        )
        for name, expression in connection.execute(
            select(
                constraint.conname, catalog.pg.pg_get_expr(constraint.conbin, constraint.conrelid)
            )
            .where(
                constraint.conrelid == catalog.pg.to_regclass("pg_temp." + scratch),
                constraint.contype == "c",
            )
            .order_by(constraint.conname)
        ):
            checks.append(dict(relation=relation.fullname, name=name, expression=expression))
        _drop_authoring_scratch(connection, scratch)

    return str(
        contract.insert()
        .inline()
        .values(
            physical_id=expected["physical_id"],
            checks=cast(literal(json.dumps(checks, sort_keys=True)), JSONB),
            source_digest=expected["physical_checks_source_digest"],
        )
        .compile(dialect=dialect(paramstyle="named"), compile_kwargs={"literal_binds": True})
    )


def physical_relations(connection) -> set[str]:
    relation, namespace = catalog.relation, catalog.namespace
    return set(
        connection.scalars(
            select(namespace.c.nspname + "." + relation.c.relname)
            .select_from(relation.join(namespace, namespace.c.oid == relation.c.relnamespace))
            .where(relation.c.relkind.in_(("r", "p")))
        )
    )


@contextmanager
def physical_row_type_context(connection, target_metadata, *, existing=None):
    """Supply declared new tables/columns for native normalization, then roll back.

    This supplies row types, never a data backfill or authorization to accept
    installed drift. Each caller authenticates its own predecessor before entry.
    """
    from sqlalchemy import inspect

    from .native_program import column_type

    existing = physical_relations(connection) if existing is None else existing
    new_tables = [item for item in target_metadata.sorted_tables if item.fullname not in existing]
    scaffolding = connection.begin_nested()
    try:
        previous = connection.execute(select(func.current_user())).scalar_one()
        inspector = inspect(connection)
        for relation in target_metadata.sorted_tables:
            if relation.fullname not in existing:
                continue
            names = {
                column["name"]
                for column in inspector.get_columns(relation.name, schema=relation.schema)
            }
            for column in relation.columns:
                if column.name not in names:
                    # Row-type resolution only: actual defaults/constraints remain migration effects.
                    execute_native_sql(
                        connection,
                        RawStream()(
                            ast.AlterTableStmt(
                                relation=ast.RangeVar(
                                    schemaname=relation.schema, relname=relation.name, inh=True
                                ),
                                objtype=enums.ObjectType.OBJECT_TABLE,
                                cmds=(
                                    ast.AlterTableCmd(
                                        subtype=enums.AlterTableType.AT_AddColumn,
                                        def_=ast.ColumnDef(
                                            colname=column.name, typeName=column_type(column)
                                        ),
                                    ),
                                ),
                            )
                        ),
                    )
        # Alembic comparison happens after rollback. Create the collection
        # together so SQLAlchemy retains its native FK/cycle ordering.
        execute_native_sql(connection, native_role_sql(previous))
        target_metadata.create_all(connection, tables=new_tables, checkfirst=False)
        for relation in new_tables:
            owner = table_policy(relation)["owner"]
            if owner is None:
                raise NativeAuthoringError("declared physical table requires its owner")
            schema = relation.schema or connection.dialect.default_schema_name
            execute_native_sql(
                connection, native_owner_sql(NativeIdentity("table", schema, relation.name), owner)
            )
        yield
    finally:
        scaffolding.rollback()


def compare_declared_candidate(
    connection,
    *,
    target_metadata,
    authoring,
    old_descriptor,
    physical_contract,
    data_steps=(),
    predecessor_revision=None,
):
    """One Alembic comparison for explicit prior/desired declarations, including fresh roots."""
    from .alembic_privileges import plugin as privileges_plugin
    from .native_admission import _admission_descriptor

    descriptor = _admission_descriptor(authored_admission_sql(authoring))
    before_policies = old_descriptor.get("privileges", ())
    target_policies = descriptor["privileges"]
    compared_privileges = []
    context = MigrationContext.configure(
        connection,
        opts={
            "include_schemas": True,
            "include_name": lambda name, kind, parents: (
                name in {table.schema for table in target_metadata.tables.values()}
                if kind == "schema"
                else True
            ),
            "compare_server_default": compare_default,
            "compare_type": compare_type,
            "autogenerate_plugins": [
                "alembic.autogenerate.*",
                "alembic.ext.checkconstraint_byname",
                checks_plugin.name,
                defaults_plugin.name,
                indexes_plugin.name,
                native_plugin.name,
                privileges_plugin.name,
            ],
            "native_authoring": authoring,
            "declared_physical_indexes": descriptor["indexes"],
            "declared_physical_columns": {
                table["relation"]: {column["name"]: column for column in table["columns"]}
                for table in descriptor["tables"]
            },
            "declared_privileges": target_policies,
            "predecessor_privileges": before_policies,
            "legacy_privilege_tables": old_descriptor["tables"],
            "compared_privileges": compared_privileges,
        },
    )
    candidate = produce_migrations(context, target_metadata)
    if candidate.upgrade_ops is not None:
        from alembic.operations.ops import CreateForeignKeyOp, CreateTableOp, ModifyTableOps
        from sqlalchemy.schema import AddConstraint

        from .alembic_privileges import OwnedOperationsOp, OwnedSQLOp
        from .native_admission import _admission_descriptor

        declared_owners = {
            row["relation"]: row.get("owner", role_name("publisher"))
            for row in old_descriptor["tables"]
        }
        target_owners = {
            row["name"]: row["owner"] for row in target_policies if row["kind"] == "table"
        }
        ordered: list[MigrateOperation] = []
        after_data: list[MigrateOperation] = []
        deferred_keys = {key for step in data_steps for key in step.deferred_foreign_keys}
        for item in candidate.upgrade_ops.ops:
            if isinstance(item, ModifyTableOps):
                relation = f"{item.schema}.{item.table_name}"
                owner = declared_owners.get(relation, role_name("publisher"))
                for change in item.ops:
                    if isinstance(change, CreateForeignKeyOp):
                        remote = (
                            change.kw.get("referent_schema", item.schema)
                            + "."
                            + change.referent_table
                        )
                        statement = str(
                            AddConstraint(change.to_constraint()).compile(
                                dialect=connection.dialect
                            )
                        )
                        destination = after_data if (relation, remote) in deferred_keys else ordered
                        destination.append(
                            OwnedSQLOp(
                                owner,
                                statement,
                                tuple(
                                    (
                                        remote,
                                        column,
                                        declared_owners.get(remote, role_name("publisher")),
                                    )
                                    for column in change.remote_cols
                                ),
                            )
                        )
                    else:
                        ordered.append(OwnedOperationsOp(owner, [change]))
            elif isinstance(item, CreateTableOp):
                relation = f"{item.schema}.{item.table_name}" if item.schema else item.table_name
                # Native triggers install as their declared table owner. Create
                # the physical table under that same authority before installing
                # its native dependents; final ACL normalization stays explicit.
                ordered.append(OwnedOperationsOp(target_owners[relation], [item]))
            else:
                ordered.append(item)
        # Native and physical dependency retirement stays explicit. Privileges follow installation.
        candidate.upgrade_ops.ops[:] = ordered
        _order_physical_retirement(candidate.upgrade_ops)
        _order_row_type_evolution(connection, candidate.upgrade_ops, authoring)
        from corpus_structure.schema.data_steps import order_data_steps

        order_data_steps(
            candidate.upgrade_ops,
            data_steps,
            authoring,
            target=target_metadata,
            predecessor=predecessor_revision,
        )
        candidate.upgrade_ops.ops.extend(after_data)
        candidate.upgrade_ops.ops.extend(compared_privileges)
        if physical_contract is not None:
            candidate.upgrade_ops.ops.append(OwnedSQLOp(role_name("publisher"), physical_contract))
    return NativeCandidate(candidate, tuple(map(policy_fact, target_policies))), replace(
        authoring, desired=final_native_catalog(authoring.desired, target_policies)
    )


def definition_sql(definitions) -> str:
    """Inspection/admission input; frozen revisions execute serialized native operations."""
    return native_sql_script(statement for item in definitions for statement in item.install_sql)


def authored_admission_sql(authoring):
    """Retain the exact descriptor/guard normalized inside physical authoring."""
    names = ("execution_contract_descriptor", "require_execution_release")
    selected = {
        item.identity.name: item
        for item in authoring.desired
        if item.identity.schema == "data" and item.identity.name in names
    }
    if set(selected) != set(names):
        raise NativeAuthoringError("native authoring lacks its exact admission descriptor/guard")
    return native_sql_script(statement for name in names for statement in selected[name].statements)


def verify_frozen_catalog(connection, admission):
    """Run the frozen guard's catalog predicates without inventing a semantic release.

    The release/authorization checks remain in require_execution_release. Authoring
    has no released application result: this checks physical/native catalog after DDL,
    using the same predicates and independently observed PostgreSQL catalog facts.
    """
    from .native_admission import frozen_catalog_verification
    from .native_products import function_bodies

    body = function_bodies(admission)["data.require_execution_release"]
    try:
        verification = frozen_catalog_verification(body)
    except ValueError as error:
        raise NativeAuthoringError("frozen guard lacks the authoring catalog boundaries") from error
    from .native_sql_body import catalog_path

    with catalog_path(connection):
        connection.exec_driver_sql(
            verification,
            execution_options={"no_parameters": True},
        )


def verify_rendered_candidate(connection, python_source, authoring, policies, admission):
    """Execute the exact generated upgrade and independent admission inside a savepoint."""
    from alembic.operations import Operations

    from .alembic_privileges import admit_privileges
    from .native_objects import admit_native

    role = connection.execute(select(func.current_user())).scalar_one()
    savepoint = connection.begin_nested()
    phase = "rendered_upgrade"
    try:
        namespace = {}
        exec(compile(python_source, "native_candidate.py", "exec"), namespace)
        with Operations.context(MigrationContext.configure(connection)):
            namespace["upgrade"]()
        if connection.execute(select(func.current_user())).scalar_one() != role:
            raise NativeAuthoringError("candidate upgrade did not restore its migration caller")
        phase = "native_after_admission"
        admit_native(connection, authoring.desired)
        phase = "privilege_after_admission"
        admit_privileges(connection, policies)
        phase = "frozen_catalog_admission"
        verify_frozen_catalog(connection, admission)
    except DBAPIError as error:
        import ast as python_ast
        import re
        import traceback

        state = getattr(error.orig, "sqlstate", None)
        sites = [
            frame.lineno
            for frame in traceback.extract_tb(error.__traceback__)
            if frame.filename == "native_candidate.py" and frame.lineno is not None
        ]
        context: dict[str, object] = {"operation_kind": phase, "sqlstate": state}
        diagnostic = getattr(error.orig, "diag", None)
        for key in ("schema_name", "table_name", "constraint_name"):
            identifier = getattr(diagnostic, key, None)
            if isinstance(identifier, str) and re.fullmatch(
                r"[a-zA-Z_][a-zA-Z0-9_]{0,62}", identifier
            ):
                context[key] = identifier
        # Retain a first-party literal refusal when PostgreSQL reports it exactly.
        # Interpolated messages and arbitrary SQL/data stay outside this safe view.
        primary = getattr(diagnostic, "message_primary", None)
        declared_refusals = {
            literal.replace("''", "'")
            for item in authoring.desired
            for statement in item.statements
            for literal in re.findall(
                r"\bRAISE\s+EXCEPTION\s+'((?:[^']|'')*)'", statement, re.IGNORECASE
            )
            if "%" not in literal
        }
        if isinstance(primary, str) and primary in declared_refusals and len(primary) <= 512:
            context["declared_refusal"] = primary
        if sites:
            line = sites[-1]
            context["source_line"] = line
            calls = [
                node
                for node in python_ast.walk(python_ast.parse(python_source))
                if isinstance(node, python_ast.Call)
                and node.lineno <= line <= (node.end_lineno or node.lineno)
                and isinstance(node.func, python_ast.Attribute)
            ]
            if calls:
                call = min(calls, key=lambda node: (node.end_lineno or node.lineno) - node.lineno)
                if not isinstance(call.func, python_ast.Attribute):
                    raise NativeAuthoringError("invalid rendered operation site") from error
                context["operation_kind"] = call.func.attr
                if call.args and call.func.attr in {"native_transition", "privilege_transition"}:
                    payload = python_ast.literal_eval(call.args[0])
                    obj = payload.get("after") or payload.get("before")
                    context["operation_identity"] = obj.get(
                        "identity", {"kind": obj.get("kind"), "name": obj.get("name")}
                    )
        failure = NativeAuthoringError(
            "rendered candidate operation refused; SQLSTATE " + str(state)
        )
        failure.authoring_context = context
        raise failure from error
    finally:
        savepoint.rollback()
