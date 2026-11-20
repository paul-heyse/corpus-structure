"""Explicit PostgreSQL native authoring scope and server-normalized catalog projections.

Only an owned authoring connection may prepare definitions. Normal deployment uses frozen
payloads and never imports today's generators or prepares desired state on a reader.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from typing import Literal

from pglast import ast, enums
from pglast.stream import RawStream
from sqlalchemy import Connection, Integer, Table, cast, func, literal, select
from sqlalchemy.dialects.postgresql import OID, dialect
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import DBAPIError

from corpus_structure.schema.integrity import role_name

from .prepared_sql import prepare_sql


class NativeAuthoringError(ValueError):
    """Explicit native source, scope, catalog or transition refusal."""

    authoring_context: dict[str, object] | None = None


def _quote(value: str) -> str:
    return dialect(paramstyle="named").identifier_preparer.quote(value)


def execute_native_sql(connection: Connection, sql: str) -> None:
    """Preserve trusted literal percent/colon content on the caller's Connection."""
    connection.exec_driver_sql(sql, execution_options={"no_parameters": True})


def native_sql_script(statements: Iterable[str]) -> str:
    """Join separately executable native statements without rewriting their bodies."""
    return "\n".join(statement.rstrip(";\n") + ";" for statement in statements)


def native_role_sql(role: str) -> str:
    return RawStream()(
        ast.VariableSetStmt(
            kind=enums.VariableSetKind.VAR_SET_VALUE,
            name="role",
            is_local=True,
            args=(ast.A_Const(val=ast.String(sval=role)),),
        )
    )


def _native_target(identity: NativeIdentity):
    if identity.kind == "function":
        types = []
        for argument in identity.arguments:
            parsed = prepare_sql(
                "SELECT NULL::" + argument, source="native argument type"
            ).statements
            if len(parsed) != 1 or not isinstance(parsed[0].stmt, ast.SelectStmt):
                raise NativeAuthoringError("invalid native argument type")
            projection = parsed[0].stmt
            if (
                not projection.targetList
                or len(projection.targetList) != 1
                or projection.fromClause
            ):
                raise NativeAuthoringError("invalid native argument type")
            value = projection.targetList[0].val
            if not isinstance(value, ast.TypeCast):
                raise NativeAuthoringError("invalid native argument type")
            types.append(value.typeName)
        return ast.ObjectWithArgs(
            objname=(ast.String(sval=identity.schema), ast.String(sval=identity.name)),
            objargs=tuple(types),
            args_unspecified=False,
        )
    if identity.kind == "schema":
        return ast.String(sval=identity.name)
    return ast.RangeVar(schemaname=identity.schema, relname=identity.name, inh=True)


def native_privilege_sql(
    identity: NativeIdentity,
    grantee: str,
    privilege: str | None = None,
    *,
    grant: bool = True,
    grant_option: bool = False,
    column: str | None = None,
) -> str:
    kinds = {
        "function": enums.ObjectType.OBJECT_FUNCTION,
        "schema": enums.ObjectType.OBJECT_SCHEMA,
        "table": enums.ObjectType.OBJECT_TABLE,
        "view": enums.ObjectType.OBJECT_TABLE,
    }
    if identity.kind not in kinds:
        raise NativeAuthoringError("unsupported privilege object")
    role = ast.RoleSpec(
        roletype=enums.RoleSpecType.ROLESPEC_PUBLIC
        if grantee == "PUBLIC"
        else enums.RoleSpecType.ROLESPEC_CSTRING,
        rolename=None if grantee == "PUBLIC" else grantee,
    )
    return RawStream()(
        ast.GrantStmt(
            is_grant=grant,
            targtype=enums.GrantTargetType.ACL_TARGET_OBJECT,
            objtype=kinds[identity.kind],
            objects=(_native_target(identity),),
            privileges=None
            if privilege is None
            else (
                ast.AccessPriv(
                    priv_name=privilege.lower(),
                    cols=None if column is None else (ast.String(sval=column),),
                ),
            ),
            grantees=(role,),
            grant_option=grant_option,
            behavior=enums.DropBehavior.DROP_RESTRICT,
        )
    )


def native_owner_sql(identity: NativeIdentity, owner: str) -> str:
    role = ast.RoleSpec(roletype=enums.RoleSpecType.ROLESPEC_CSTRING, rolename=owner)
    if identity.kind == "function":
        statement = ast.AlterOwnerStmt(
            objectType=enums.ObjectType.OBJECT_FUNCTION,
            object=_native_target(identity),
            newowner=role,
        )
    elif identity.kind in {"table", "view"}:
        statement = ast.AlterTableStmt(
            relation=ast.RangeVar(schemaname=identity.schema, relname=identity.name, inh=True),
            objtype=enums.ObjectType.OBJECT_VIEW
            if identity.kind == "view"
            else enums.ObjectType.OBJECT_TABLE,
            cmds=(ast.AlterTableCmd(subtype=enums.AlterTableType.AT_ChangeOwner, newowner=role),),
        )
    else:
        raise NativeAuthoringError("unsupported native ownership object")
    return RawStream()(statement)


def native_before_trigger(
    relation: Table,
    name: str,
    routine: tuple[str, str],
    *,
    events: tuple[Literal["insert", "delete", "update", "truncate"], ...],
    row: bool = False,
) -> ast.CreateTrigStmt:
    """Build a PostgreSQL trigger on a captured physical relation."""
    # PostgreSQL TRIGGER_TYPE_* bits used by CreateTrigStmt.
    event_bits = {"insert": 4, "delete": 8, "update": 16, "truncate": 32}
    return ast.CreateTrigStmt(
        trigname=name,
        relation=ast.RangeVar(schemaname=relation.schema, relname=relation.name, inh=True),
        funcname=tuple(ast.String(sval=part) for part in routine),
        row=row,
        timing=2,
        events=sum(event_bits[event] for event in set(events)),
    )


@contextmanager
def native_owner(connection: Connection, owner: str | None):
    """Apply object effects as their explicit owner, then restore the caller's role.

    PostgreSQL can warn instead of revoking a different grantor's ACL when a migration
    login may SET the owner role but does not inherit it. Running as the selected owner
    makes the complete privilege effects real. A database error requires caller rollback,
    which also restores SET LOCAL state; never hide it with a failed cleanup statement.
    """
    previous = connection.scalar(select(func.current_setting("role")))
    changed = owner is not None and owner != connection.scalar(select(func.current_user()))
    if changed:
        execute_native_sql(connection, native_role_sql(owner))
    failed = False
    try:
        yield
    except DBAPIError:
        failed = True
        raise
    finally:
        if changed and not failed:
            execute_native_sql(connection, native_role_sql(previous))


def execute_native_trigger(connection: Connection, sql: str) -> None:
    """Install a declared trigger without changing its function's final EXECUTE ACL.

    Existing triggers may legitimately join a migration-owned relation to a protected
    publisher-owned trigger function. PostgreSQL checks EXECUTE when creating the
    trigger, so grant only for that statement and restore it before returning.
    """
    tree = prepare_sql(sql, source="native trigger installation").statements
    if len(tree) != 1 or not isinstance(tree[0].stmt, ast.CreateTrigStmt):
        execute_native_sql(connection, sql)
        return
    from . import native_catalog as catalog_queries

    statement = tree[0].stmt
    if not statement.funcname:
        raise NativeAuthoringError("native trigger function name is absent")
    identity = NativeIdentity("function", *(part.sval for part in statement.funcname))
    signature = identity.qualified
    principal = connection.execute(select(func.current_user())).scalar_one()
    permitted = connection.scalar(
        select(catalog_queries.pg.has_function_privilege(principal, signature, "EXECUTE"))
    )
    if permitted:
        execute_native_sql(connection, sql)
        return
    function = connection.execute(catalog_queries.function_observation(signature)).mappings().one()
    with native_owner(connection, function["owner"]):
        execute_native_sql(connection, native_privilege_sql(identity, principal, "EXECUTE"))
    try:
        execute_native_sql(connection, sql)
    except DBAPIError:
        # The caller's failed transaction/savepoint rolls back both grant and CREATE.
        raise
    else:
        with native_owner(connection, function["owner"]):
            execute_native_sql(
                connection, native_privilege_sql(identity, principal, "EXECUTE", grant=False)
            )


@dataclass(frozen=True)
class NativeIdentity:
    kind: str
    schema: str
    name: str
    arguments: tuple[str, ...] = ()
    relation: str | None = None

    @property
    def qualified(self) -> str:
        name = f"{_quote(self.schema)}.{_quote(self.name)}"
        return name + "(" + ",".join(self.arguments) + ")" if self.kind == "function" else name

    @property
    def drop_sql(self) -> str:
        kinds = {
            "function": enums.ObjectType.OBJECT_FUNCTION,
            "view": enums.ObjectType.OBJECT_VIEW,
            "trigger": enums.ObjectType.OBJECT_TRIGGER,
        }
        if self.kind not in kinds:
            raise NativeAuthoringError(f"unsupported native object {self.kind}")
        target = (
            _native_target(self)
            if self.kind == "function"
            else tuple(
                ast.String(sval=value)
                for value in (
                    (self.schema, self.relation or "", self.name)
                    if self.kind == "trigger"
                    else (self.schema, self.name)
                )
            )
        )
        return RawStream()(
            ast.DropStmt(
                objects=(target,),
                removeType=kinds[self.kind],
                behavior=enums.DropBehavior.DROP_RESTRICT,
            )
        )

    def payload(self) -> dict:
        return asdict(self)

    @classmethod
    def from_payload(cls, value: dict) -> NativeIdentity:
        return cls(
            value["kind"],
            value["schema"],
            value["name"],
            tuple(value["arguments"]),
            value["relation"],
        )


@dataclass(frozen=True)
class NativeProgramAccess:
    """Current program purpose declaration, separate from frozen ACL evidence."""

    purposes: tuple[str, ...] = ()
    internal: bool = False
    owner_execute: bool = False

    def __post_init__(self):
        if bool(self.purposes) == self.internal or len(set(self.purposes)) != len(self.purposes):
            raise NativeAuthoringError(
                "program requires distinct purposes or an explicit internal marking"
            )

    def grants(self, owner: str | None) -> tuple[tuple[str, str, bool], ...]:
        from corpus_structure.schema.integrity import integrity

        policy = integrity()
        roles = []
        for purpose in self.purposes:
            role = policy.purpose_role(purpose)
            if role is None:
                raise NativeAuthoringError(f"program purpose has no executable role: {purpose}")
            roles.append(role)
        if self.owner_execute:
            if owner is None:
                raise NativeAuthoringError("owner execute grant requires a declared owner")
            roles.append(owner)
        return tuple((role, "EXECUTE", False) for role in dict.fromkeys(roles))


INTERNAL_PROGRAM = NativeProgramAccess(internal=True)


@dataclass(frozen=True)
class NativeDefinition:
    identity: NativeIdentity
    sql: str
    source: str
    owner: str | None = None
    # (grantee, privilege, grant option). PUBLIC is a special grantee, never a role name.
    grants: tuple[tuple[str, str, bool], ...] = ()
    enabled: str = "O"
    role_bindings: tuple[tuple[str, str], ...] = ()
    bind_owner: bool = False
    program_access: NativeProgramAccess | None = None
    callees: frozenset[NativeIdentity] | None = None
    validity: tuple[tuple[str, str], ...] = ()

    @property
    def catalog_version(self) -> int:
        statement = prepare_sql(self.sql, source=self.source).statements[0].stmt
        return (
            2
            if isinstance(statement, ast.CreateFunctionStmt) and statement.sql_body is not None
            else 1
        )

    def __post_init__(self):
        if self.role_bindings not in ((), (("$migration_owner", "sem_namespace_owner"),)):
            raise NativeAuthoringError(f"{self.source}: unsupported native role binding")
        if self.bind_owner and not self.role_bindings:
            raise NativeAuthoringError(
                f"{self.source}: owner binding requires its semantic namespace"
            )
        tree = prepare_sql(self.sql, source=self.source).statements
        expected = {
            "function": ast.CreateFunctionStmt,
            "view": ast.ViewStmt,
            "trigger": ast.CreateTrigStmt,
        }
        if (
            self.identity.kind not in expected
            or len(tree) != 1
            or not isinstance(tree[0].stmt, expected[self.identity.kind])
        ):
            raise NativeAuthoringError(
                f"{self.source}: native definition requires one matching CREATE"
            )
        if self.identity.kind in {"function", "view"} and not tree[0].stmt.replace:
            raise NativeAuthoringError(
                f"{self.source}: managed declarations require CREATE OR REPLACE"
            )
        statement = tree[0].stmt
        if isinstance(statement, ast.CreateFunctionStmt) and any(
            option.defname == "set" and option.arg.kind != enums.VariableSetKind.VAR_SET_VALUE
            for option in statement.options or ()
        ):
            raise NativeAuthoringError(
                f"{self.source}: function settings require explicit frozen values"
            )
        if self.identity.kind != "trigger" and self.owner is None:
            raise NativeAuthoringError(
                f"{self.source}: native definition requires an explicit owner"
            )
        if self.enabled not in {"O", "D", "R", "A"}:
            raise NativeAuthoringError(f"{self.source}: unsupported trigger enabled state")
        allowed = (
            {"EXECUTE"}
            if self.identity.kind == "function"
            else {
                "SELECT",
                "INSERT",
                "UPDATE",
                "DELETE",
                "TRUNCATE",
                "REFERENCES",
                "TRIGGER",
                "MAINTAIN",
            }
        )
        if any(privilege not in allowed for _, privilege, _ in self.grants):
            raise NativeAuthoringError(f"{self.source}: unsupported native privilege")

    @property
    def install_sql(self) -> tuple[str, ...]:
        result = [self.sql]
        if self.identity.kind == "trigger":
            action = {
                "O": enums.AlterTableType.AT_EnableTrig,
                "D": enums.AlterTableType.AT_DisableTrig,
                "R": enums.AlterTableType.AT_EnableReplicaTrig,
                "A": enums.AlterTableType.AT_EnableAlwaysTrig,
            }[self.enabled]
            result.append(
                RawStream()(
                    ast.AlterTableStmt(
                        relation=ast.RangeVar(
                            schemaname=self.identity.schema,
                            relname=self.identity.relation,
                            inh=True,
                        ),
                        objtype=enums.ObjectType.OBJECT_TABLE,
                        cmds=(ast.AlterTableCmd(subtype=action, name=self.identity.name),),
                    )
                )
            )
        else:
            result.append(native_owner_sql(self.identity, self.owner or ""))
            result.append(native_privilege_sql(self.identity, "PUBLIC", grant=False))
            result.extend(
                native_privilege_sql(self.identity, grantee, privilege, grant_option=option)
                for grantee, privilege, option in self.grants
            )
        return tuple(result)


def definition_from_sql(
    connection: Connection | None,
    sql: str,
    *,
    source: str,
    owner: str | None = None,
    grants: tuple[tuple[str, str, bool], ...] = (),
    enabled: str = "O",
    program_access: NativeProgramAccess | None = None,
) -> NativeDefinition:
    statement = prepare_sql(sql, source=source).statements
    if len(statement) != 1:
        raise NativeAuthoringError(f"{source}: expected exactly one native declaration")
    stmt = statement[0].stmt
    if isinstance(stmt, ast.CreateFunctionStmt):
        if stmt.is_procedure:
            raise NativeAuthoringError(
                f"{source}: procedures are outside the selected native scope"
            )
        names = tuple(part.sval for part in stmt.funcname or ())
        arguments = []
        for parameter in stmt.parameters or ():
            if parameter.mode in {
                enums.FunctionParameterMode.FUNC_PARAM_OUT,
                enums.FunctionParameterMode.FUNC_PARAM_TABLE,
            }:
                continue
            kind = RawStream()(parameter.argType)
            canonical = kind
            if connection is not None:
                from . import native_catalog as catalog_queries

                type_oid = connection.scalar(select(cast(catalog_queries.pg.to_regtype(kind), OID)))
                from .native_sql_body import catalog_path

                with catalog_path(connection):
                    canonical = connection.scalar(
                        select(catalog_queries.pg.format_type(type_oid, None)),
                    )
            if canonical is None:
                raise NativeAuthoringError(f"{source}: unresolved input type {kind}")
            arguments.append(canonical)
        if len(names) != 2:
            raise NativeAuthoringError(f"{source}: function requires a qualified name")
        identity = NativeIdentity("function", *names, tuple(arguments))
    elif isinstance(stmt, ast.ViewStmt):
        if stmt.view is None or stmt.view.schemaname is None or stmt.view.relname is None:
            raise NativeAuthoringError(f"{source}: view requires a qualified name")
        identity = NativeIdentity("view", stmt.view.schemaname, stmt.view.relname)
    elif isinstance(stmt, ast.CreateTrigStmt):
        if (
            stmt.relation is None
            or stmt.relation.schemaname is None
            or stmt.relation.relname is None
            or stmt.trigname is None
        ):
            raise NativeAuthoringError(f"{source}: trigger requires a qualified relation")
        identity = NativeIdentity(
            "trigger", stmt.relation.schemaname, stmt.trigname, relation=stmt.relation.relname
        )
    else:
        raise NativeAuthoringError(
            f"{source}: unsupported native declaration {type(stmt).__name__}"
        )
    if program_access is not None:
        if grants or identity.kind != "function":
            raise NativeAuthoringError(f"{source}: program purposes must own the function grants")
        grants = program_access.grants(owner)
    return NativeDefinition(
        identity, sql, source, owner, grants, enabled, program_access=program_access
    )


def observe_native(
    connection: Connection, identity: NativeIdentity, *, catalog_version: int | None = 1
) -> dict | None:
    """Read selected properties independently from catalog fields; NULL ACL uses acldefault."""
    from . import native_catalog as catalog_queries

    if catalog_version not in {None, 1, 2}:
        raise NativeAuthoringError("unsupported native catalog comparison profile")
    if identity.kind == "function":
        statement = catalog_queries.function_observation(identity.qualified)
    elif identity.kind == "view":
        statement = catalog_queries.view_observation(identity.schema, identity.name)
    elif identity.kind == "trigger":
        statement = catalog_queries.trigger_observation(
            identity.schema, identity.name, identity.relation
        )
    else:
        raise NativeAuthoringError(f"unsupported native kind {identity.kind}")
    from .native_sql_body import catalog_path

    with catalog_path(connection):
        row = connection.execute(statement).mappings().one_or_none()
    if identity.kind == "trigger":
        return None if row is None else dict(row)
    if row is not None and identity.kind == "view" and row["kind"] != "v":
        raise NativeAuthoringError(f"{identity.qualified}: selected object is not an ordinary view")
    if row is None:
        return None
    result = dict(row)
    sql_body = result.pop("sql_body", False)
    selected_version = (2 if sql_body else 1) if catalog_version is None else catalog_version
    if sql_body and selected_version == 1:
        raise NativeAuthoringError(
            f"{identity.qualified}: SQL-standard body normalization is unsupported"
        )
    if selected_version == 2:
        from .native_sql_body import (
            SQL_STANDARD_MAJOR,
            SQL_STANDARD_PROFILE,
            catalog_path,
        )

        if identity.kind != "function" or not sql_body:
            raise NativeAuthoringError(
                "SQL-standard comparison profile requires a parsed SQL function body"
            )
        major = connection.scalar(
            select(cast(func.current_setting("server_version_num"), Integer) // 10000)
        )
        if major != SQL_STANDARD_MAJOR:
            raise NativeAuthoringError(
                "unsupported PostgreSQL major for SQL-standard body comparison"
            )
        with catalog_path(connection):
            result["body"] = connection.scalar(
                select(
                    catalog_queries.pg.pg_get_functiondef(
                        catalog_queries.pg.to_regprocedure(identity.qualified)
                    )
                )
            )
            dependencies = connection.scalar(
                catalog_queries.dependencies(catalog_queries.pg.to_regprocedure(identity.qualified))
            )
        result.update(
            body_kind="sql_standard",
            body_profile=SQL_STANDARD_PROFILE,
            server_major=major,
            dependencies=dependencies,
        )
    aclkind = "f" if identity.kind == "function" else "r"
    acl = connection.execute(
        catalog_queries.acl_rows(
            literal(result.pop("acl")), literal(aclkind), literal(result.pop("proowner"))
        )
    ).all()
    result.pop("oid")
    result["acl"] = [list(item) for item in acl]
    if "config" in result:
        result["config"] = sorted(result["config"] or ())
    if "options" in result:
        result["options"] = sorted(result["options"] or ())
    return result


def semantic_namespace_owner(connection: Connection) -> str:
    from . import native_catalog as catalog_queries

    owner = connection.scalar(catalog_queries.namespace_owner())
    if owner is None:
        raise NativeAuthoringError("migration-owner binding requires the semantic namespace owner")
    return owner


def set_native_acl(
    connection: Connection, identity: NativeIdentity, grants, *, catalog_version=1
) -> None:
    """Replace the selected function/view ACL using PostgreSQL's ACL projections."""
    installed = observe_native(connection, identity, catalog_version=catalog_version)
    if installed is None:
        raise NativeAuthoringError(f"cannot grant an absent native object: {identity.qualified}")
    for grantee in sorted({grant[0] for grant in installed["acl"]}):
        execute_native_sql(connection, native_privilege_sql(identity, grantee, grant=False))
    for grantee, privilege, option in grants:
        execute_native_sql(
            connection, native_privilege_sql(identity, grantee, privilege, grant_option=option)
        )


def _declared_acl(connection: Connection, definition: NativeDefinition):
    from . import native_catalog as catalog_queries

    # acldefault is the built-in owner baseline, unlike ALTER DEFAULT PRIVILEGES,
    # which may contain ambient grants unrelated to this explicit desired scope.
    owner = definition.owner
    if owner is None:
        raise NativeAuthoringError(f"{definition.source}: native ACL requires an explicit owner")
    rows = connection.execute(
        catalog_queries.declared_acl("f" if definition.identity.kind == "function" else "r", owner)
    ).all()
    grants: dict[tuple[str, str], bool] = {(owner, privilege): option for privilege, option in rows}
    grants.update(
        {(grantee, privilege): option for grantee, privilege, option in definition.grants}
    )
    return tuple(
        (grantee, privilege, option) for (grantee, privilege), option in sorted(grants.items())
    )


@dataclass(frozen=True)
class NativeObject:
    identity: NativeIdentity
    source: str
    statements: tuple[str, ...]
    catalog_json: str
    role_bindings: tuple[tuple[str, str], ...] = ()
    catalog_version: int = 1
    binding_version: int = 1

    def __post_init__(self):
        if self.binding_version not in {1, 2}:
            raise NativeAuthoringError("unsupported frozen native owner binding")
        if self.binding_version == 2 and (
            self.role_bindings != (("$migration_owner", "sem_namespace_owner"),)
            or self.catalog.get("owner") != "$migration_owner"
        ):
            raise NativeAuthoringError("v2 native owner requires its semantic namespace binding")
        if self.catalog_version not in {1, 2}:
            raise NativeAuthoringError("unsupported frozen native catalog profile")
        if self.catalog_version == 2:
            from .native_sql_body import SQL_STANDARD_MAJOR, SQL_STANDARD_PROFILE

            catalog = self.catalog
            if (
                self.identity.kind != "function"
                or catalog.get("body_kind") != "sql_standard"
                or catalog.get("body_profile") != SQL_STANDARD_PROFILE
                or catalog.get("server_major") != SQL_STANDARD_MAJOR
                or not isinstance(catalog.get("dependencies"), list)
            ):
                raise NativeAuthoringError("unsupported frozen SQL-standard comparison profile")
        elif "body_profile" in self.catalog:
            raise NativeAuthoringError("v1 native catalog cannot carry a SQL-standard profile")

    @property
    def catalog(self) -> dict:
        return json.loads(self.catalog_json)

    def expected_catalog(self, connection: Connection) -> dict:
        catalog = self.catalog
        if not self.role_bindings:
            return catalog
        if self.role_bindings != (("$migration_owner", "sem_namespace_owner"),):
            raise NativeAuthoringError(f"{self.source}: unsupported frozen native role binding")
        owner = semantic_namespace_owner(connection)
        if self.binding_version == 2:
            catalog["owner"] = owner
        if self.identity.kind == "trigger":
            return catalog
        acl = {}
        for grantee, privilege, option in catalog["acl"]:
            grantee = owner if grantee == "$migration_owner" else grantee
            acl[(grantee, privilege)] = acl.get((grantee, privilege), False) or option
        catalog["acl"] = [
            [grantee, privilege, option] for (grantee, privilege), option in sorted(acl.items())
        ]
        return catalog

    @property
    def payload_version(self) -> int:
        return max(self.catalog_version, self.binding_version)

    def payload(self) -> dict:
        return {
            "identity": self.identity.payload(),
            "source": self.source,
            "statements": list(self.statements),
            "catalog": self.catalog,
            "role_bindings": dict(self.role_bindings),
            **({"catalog_version": self.catalog_version} if self.catalog_version != 1 else {}),
            **({"binding_version": self.binding_version} if self.binding_version != 1 else {}),
        }

    @classmethod
    def from_payload(cls, value: dict) -> NativeObject:
        return cls(
            NativeIdentity.from_payload(value["identity"]),
            value["source"],
            tuple(value["statements"]),
            json.dumps(value["catalog"], sort_keys=True),
            tuple(value.get("role_bindings", {}).items()),
            value.get("catalog_version", 1),
            value.get("binding_version", 1),
        )


@dataclass(frozen=True)
class NativeAuthoring:
    desired: tuple[NativeObject, ...]
    predecessor: tuple[NativeObject, ...] = ()
    retire: frozenset[NativeIdentity] = frozenset()
    recreate: frozenset[NativeIdentity] = frozenset()

    def __post_init__(self):
        desired = {item.identity for item in self.desired}
        before = {item.identity for item in self.predecessor}
        if len(desired) != len(self.desired) or len(before) != len(self.predecessor):
            duplicates = [
                f"{part} {identity.kind} {identity.qualified}"
                for part, items in (("desired", self.desired), ("predecessor", self.predecessor))
                for identity, count in Counter(item.identity for item in items).items()
                if count > 1
            ]
            raise NativeAuthoringError(
                "duplicate managed native identity: " + "; ".join(duplicates[:12])
            )
        if before - desired != self.retire:
            failure = NativeAuthoringError(
                "native retirement must explicitly equal removed predecessor identities"
            )
            # The operator must name these exact identities in the next intent.
            # Reuse the managed authoring diagnostic rather than forcing a
            # second catalog acquisition or an unrecorded SQL comparison.
            failure.authoring_context = {
                "missing_retirements": [
                    identity.payload()
                    for identity in sorted(
                        before - desired - self.retire, key=lambda item: item.qualified
                    )
                ],
                "unexpected_retirements": [
                    identity.payload()
                    for identity in sorted(
                        self.retire - (before - desired), key=lambda item: item.qualified
                    )
                ],
            }
            raise failure
        if self.recreate - (desired & before):
            raise NativeAuthoringError(
                "recreation must name a predecessor and desired native identity"
            )


def _require_owned_authoring(connection: Connection, owned_authoring: bool) -> None:
    if not owned_authoring:
        raise NativeAuthoringError(
            "native preparation requires an explicitly owned authoring database"
        )
    principal = connection.execute(select(func.current_user())).scalar_one()
    if principal in {
        role_name("reader"),
        role_name("writer"),
        role_name("admitter"),
        role_name("evaluator"),
        role_name("fitter"),
    }:
        raise NativeAuthoringError("native preparation cannot use a runtime principal")


def native_dependency_graph(connection: Connection, identities):
    """A bounded observed dependency graph, with declaration-order tie breaking."""
    from .graph_runtime import nx

    identities = tuple(identities)
    graph = nx.DiGraph(backend="networkx")
    graph.add_nodes_from(identities)
    if not identities:
        return graph
    from . import native_catalog as catalog_queries

    records = [
        (
            position,
            identity.kind,
            identity.qualified if identity.kind != "trigger" else "",
            (_quote(identity.schema) + "." + _quote(identity.relation or ""))
            if identity.kind == "trigger"
            else None,
            identity.name,
        )
        for position, identity in enumerate(identities)
    ]
    dependencies = connection.execute(catalog_queries.native_scope_dependencies(records))
    for dependent, prerequisite in dependencies:
        graph.add_edge(identities[prerequisite], identities[dependent])
    return graph


def native_dependency_order(connection: Connection, identities):
    from .graph_runtime import nx
    from .graph_topology import ordered_nodes

    graph = native_dependency_graph(connection, identities)
    declared = {identity: position for position, identity in enumerate(graph)}
    try:
        return ordered_nodes(graph, key=declared.__getitem__)
    except nx.NetworkXUnfeasible as error:
        raise NativeAuthoringError("declared native dependency scope is cyclic") from error


def normalize_native_backfill(
    connection: Connection,
    definitions: tuple[NativeDefinition, ...],
    *,
    context: tuple[NativeObject, ...],
    owned_authoring: bool = False,
) -> tuple[NativeObject, ...]:
    """Normalize old source with only its authenticated dependent context removed.

    No catalog body is acquired as desired meaning. The outer savepoint restores
    original objects, OIDs, complete ACLs and owners, including on refusal.
    """
    from .graph_runtime import nx
    from .graph_topology import ordered_nodes, rooted_closure

    _require_owned_authoring(connection, owned_authoring)
    if any(not isinstance(item, NativeObject) for item in context):
        raise NativeAuthoringError("native backfill context requires exact frozen objects")
    admit_native(connection, context)
    frozen = {item.identity: item for item in context}
    selected = {item.identity for item in definitions}
    identities = tuple(dict.fromkeys((*frozen, *(item.identity for item in definitions))))
    graph = native_dependency_graph(connection, identities)
    dependents = rooted_closure(graph, selected) - selected
    declared = {identity: position for position, identity in enumerate(graph)}
    try:
        order = ordered_nodes(graph, key=declared.__getitem__)
    except nx.NetworkXUnfeasible as error:
        raise NativeAuthoringError("declared native dependency scope is cyclic") from error
    savepoint = connection.begin_nested()
    try:
        for identity in reversed(order):
            if identity in dependents:
                if identity not in frozen:
                    raise NativeAuthoringError(
                        "native dependent lacks frozen normalization custody"
                    )
                owner = frozen[identity].expected_catalog(connection).get("owner")
                with native_owner(connection, owner):
                    execute_native_sql(connection, identity.drop_sql)
        return prepare_native_authoring(
            connection, definitions, owned_authoring=owned_authoring
        ).desired
    except DBAPIError as error:
        raise NativeAuthoringError(
            "native backfill dependent scope refused an undeclared or unavailable dependent"
        ) from error
    finally:
        savepoint.rollback()


def _check_plpgsql_authoring(
    connection: Connection,
    definitions: tuple[NativeDefinition, ...],
    *,
    triggers: tuple[NativeDefinition, ...] = (),
    trigger_contexts: frozenset[NativeIdentity] = frozenset(),
) -> None:
    """Check concrete PL/pgSQL expressions against the complete installed candidate.

    The caller owns the rollback-only normalization savepoint, including any checker
    installation. This checks static SQL, not arbitrary runtime-generated SQL or
    semantic behavior. Frozen predecessors are historical inputs, not new authoring.
    """
    if not definitions:
        return
    from . import native_catalog as catalog_queries

    contexts = {}
    for trigger in triggers if trigger_contexts else ():
        context = (
            connection.execute(
                catalog_queries.trigger_check_context(
                    _quote(trigger.identity.schema) + "." + _quote(trigger.identity.relation or ""),
                    trigger.identity.name,
                ),
            )
            .mappings()
            .one()
        )
        contexts.setdefault(context["function_oid"], []).append((trigger, context))
    selected: list[tuple[NativeDefinition, RowMapping | None]] = []
    for item in definitions:
        if item.identity.kind != "function":
            continue
        metadata = (
            connection.execute(
                catalog_queries.routine_check_context(item.identity.qualified),
            )
            .mappings()
            .one()
        )
        if metadata["lanname"] != "plpgsql":
            continue
        if metadata["result_type"] == "trigger" and not metadata["pseudo_argument"]:
            applicable = contexts.get(metadata["function_oid"], ())
            if not applicable or any(
                trigger.identity not in trigger_contexts for trigger, _ in applicable
            ):
                raise NativeAuthoringError(
                    f"PL/pgSQL authoring check requires a concrete ordinary function context "
                    f"or every declared trigger relation context: {item.identity.qualified}; source={item.source}"
                )
            selected.extend((item, context) for _, context in applicable)
            continue
        if metadata["pseudo_argument"] or metadata["result_type"] in {
            "event_trigger",
            "anyelement",
            "anyarray",
            "anynonarray",
            "anyenum",
            "anyrange",
            "anymultirange",
            "anycompatible",
            "anycompatiblearray",
            "anycompatiblenonarray",
            "anycompatiblerange",
            "anycompatiblemultirange",
        }:
            raise NativeAuthoringError(
                f"PL/pgSQL authoring check requires a concrete ordinary function context: "
                f"{item.identity.qualified}; source={item.source}"
            )
        selected.append((item, None))
    if not selected:
        return
    extension = connection.execute(catalog_queries.checker_extension()).mappings().one_or_none()
    if extension is None:
        available = connection.scalar(catalog_queries.checker_available())
        if not available:
            raise NativeAuthoringError(
                "PL/pgSQL authoring requires available plpgsql_check extension version 2.10"
            )
        execute_native_sql(
            connection,
            RawStream()(
                ast.CreateExtensionStmt(
                    extname="plpgsql_check",
                    options=(
                        ast.DefElem(defname="schema", arg=ast.String(sval="public")),
                        ast.DefElem(defname="new_version", arg=ast.String(sval="2.10")),
                    ),
                )
            ),
        )
        schema = "public"
    else:
        if extension["extversion"] != "2.10":
            raise NativeAuthoringError(
                "PL/pgSQL authoring requires plpgsql_check extension version 2.10"
            )
        schema = extension["nspname"]
    diagnostics = []
    omissions = []
    error_count = 0
    for index, (item, context) in enumerate(selected):
        errors = (
            connection.execute(
                catalog_queries.checker_diagnostics(schema, item.identity.qualified, context),
            )
            .mappings()
            .all()
        )
        if errors:
            limit = min(8, 32 - error_count)
            messages = "; ".join(
                f"SQLSTATE {error['sqlstate']} line {error['lineno']}: "
                + " ".join(error["message"].split())[:500]
                for error in errors[:limit]
            )
            relation = f"; relation={context['relation']}" if context else ""
            diagnostics.append(
                f"{item.identity.qualified}: {messages}; source={item.source}{relation}"
            )
            error_count += min(len(errors), limit)
            if len(errors) > limit:
                omissions.append(f"{item.identity.qualified}: further errors omitted")
            if error_count == 32:
                remaining = len(selected) - index - 1
                if remaining:
                    omissions.append(f"{remaining} selected functions unexamined")
                break
    if diagnostics:
        suffix = "; diagnostic limit: " + "; ".join(omissions) if omissions else ""
        failure = NativeAuthoringError(
            "PL/pgSQL authoring check failed for " + "; ".join(diagnostics) + suffix
        )
        failure.authoring_context = {
            "phase": "plpgsql_check",
            "diagnostics": diagnostics,
            "omissions": omissions,
            "error_count": error_count,
        }
        raise failure


def prepare_native_authoring(
    connection: Connection,
    definitions: tuple[NativeDefinition, ...],
    *,
    predecessor: tuple[NativeDefinition | NativeObject, ...] = (),
    retire: frozenset[NativeIdentity] = frozenset(),
    recreate: frozenset[NativeIdentity] = frozenset(),
    owned_authoring: bool = False,
    check_plpgsql: frozenset[NativeIdentity] = frozenset(),
    check_plpgsql_triggers: frozenset[NativeIdentity] = frozenset(),
) -> NativeAuthoring:
    """Normalize complete declared definitions in rollback-only authoring savepoints.

    Definitions are dependency ordered. The caller explicitly owns this disposable database;
    normalization refuses ordinary runtime principals. Predecessor meaning comes from supplied
    source, never adoption of live catalog state. No implicit CASCADE is used.
    """
    from . import native_catalog as catalog_queries

    _require_owned_authoring(connection, owned_authoring)
    functions = {item.identity for item in definitions if item.identity.kind == "function"}
    if check_plpgsql - functions:
        raise NativeAuthoringError("PL/pgSQL check selection requires desired function identities")
    triggers = tuple(item for item in definitions if item.identity.kind == "trigger")
    if check_plpgsql_triggers - {item.identity for item in triggers}:
        raise NativeAuthoringError("PL/pgSQL trigger contexts require desired trigger identities")
    frozen_predecessor = bool(predecessor) and all(
        isinstance(item, NativeObject) for item in predecessor
    )
    if (
        predecessor
        and not frozen_predecessor
        and any(isinstance(item, NativeObject) for item in predecessor)
    ):
        raise NativeAuthoringError(
            "native predecessor must use one complete source or frozen snapshot contract"
        )
    scope_items = {item.identity: item for item in (*predecessor, *definitions)}
    scope = native_dependency_order(connection, tuple(scope_items))

    def normalize(items, *, check_selected=False):
        savepoint = connection.begin_nested()
        active = None
        phase = "normalization"
        try:
            # Union order is explicit dependency order; dependencies absent from the scope
            # make PostgreSQL refuse, rather than silently authorizing a dependent drop.
            for identity in reversed(scope):
                active = scope_items[identity]
                phase = "remove existing object"
                installed = observe_native(connection, identity, catalog_version=None)
                if installed is not None:
                    with native_owner(connection, installed.get("owner")):
                        execute_native_sql(connection, identity.drop_sql)
            for item in items:
                active = item
                phase = "resolve declared owner"
                owner = item.owner
                if item.identity.kind == "trigger":
                    relation = (
                        _quote(item.identity.schema) + "." + _quote(item.identity.relation or "")
                    )
                    parent_owner = connection.scalar(catalog_queries.relation_owner(relation))
                    if parent_owner is None or (owner is not None and owner != parent_owner):
                        raise NativeAuthoringError(
                            f"{item.source}: trigger requires its declared owning relation"
                        )
                    owner = parent_owner
                with native_owner(connection, owner):
                    for number, statement in enumerate(item.install_sql, start=1):
                        phase = f"install statement {number}"
                        if item.identity.kind == "trigger":
                            execute_native_trigger(connection, statement)
                        else:
                            execute_native_sql(connection, statement)
                    phase = "normalize privileges and restore owner"
                    if item.identity.kind != "trigger":
                        set_native_acl(
                            connection,
                            item.identity,
                            _declared_acl(connection, item),
                            catalog_version=item.catalog_version,
                        )
            if check_selected:
                phase = "check PL/pgSQL static SQL"
                _check_plpgsql_authoring(
                    connection,
                    tuple(item for item in items if item.identity in check_plpgsql),
                    triggers=triggers,
                    trigger_contexts=check_plpgsql_triggers,
                )
            result = []
            for item in items:
                active = item
                phase = "inspect normalized catalog"
                catalog = observe_native(
                    connection, item.identity, catalog_version=item.catalog_version
                )
                if catalog is None:
                    raise NativeAuthoringError(
                        f"{item.source}: declaration did not create {item.identity.qualified}"
                    )
                statements = item.install_sql
                if item.role_bindings:
                    migration_owner = semantic_namespace_owner(connection)
                    if item.bind_owner:
                        if item.owner != migration_owner:
                            raise NativeAuthoringError(
                                "native owner binding differs from semantic namespace"
                            )
                        catalog["owner"] = "$migration_owner"
                    # Bind only the historical ACL grantee. SQL bodies, names and other
                    # text remain exact. Complete frozen ACL execution supplies this grant.
                    if "acl" in catalog:
                        catalog["acl"] = [
                            [
                                "$migration_owner" if grantee == migration_owner else grantee,
                                privilege,
                                option,
                            ]
                            for grantee, privilege, option in catalog["acl"]
                        ]
                    if "acl" in catalog and migration_owner == item.owner and not item.bind_owner:
                        catalog["acl"].extend(
                            [
                                list(grant)
                                for grant in _declared_acl(connection, replace(item, grants=()))
                            ]
                        )
                    statements = tuple(
                        statement
                        for statement in statements
                        if statement
                        != native_privilege_sql(item.identity, migration_owner, "EXECUTE")
                    )
                    if item.bind_owner:
                        owner_statement = native_owner_sql(item.identity, migration_owner)
                        statements = tuple(s for s in statements if s != owner_statement)
                result.append(
                    NativeObject(
                        item.identity,
                        item.source,
                        statements,
                        json.dumps(catalog, sort_keys=True),
                        item.role_bindings,
                        item.catalog_version,
                        2 if item.bind_owner else 1,
                    )
                )
            return tuple(result)
        except DBAPIError as error:
            if active is None:
                raise
            # Report only authored provenance and the driver's typed SQLSTATE. SQL,
            # parameters and server message/context remain on the chained cause.
            state = getattr(error.orig, "sqlstate", None)
            state = (
                state if isinstance(state, str) and re.fullmatch(r"[0-9A-Z]{5}", state) else None
            )
            raise NativeAuthoringError(
                f"native normalization {phase} failed for {active.identity.kind} "
                f"{active.identity.qualified} (SQLSTATE {state or 'unavailable'}); "
                f"source={active.source}"
            ) from error
        finally:
            savepoint.rollback()

    before = (
        tuple(item for item in predecessor if isinstance(item, NativeObject))
        if frozen_predecessor
        else normalize(tuple(item for item in predecessor if isinstance(item, NativeDefinition)))
    )
    desired = normalize(definitions, check_selected=True)
    return NativeAuthoring(desired, before, retire, recreate)


def admit_native(connection: Connection, objects: tuple[NativeObject, ...]) -> None:
    for item in objects:
        actual = observe_native(connection, item.identity, catalog_version=item.catalog_version)
        expected = item.expected_catalog(connection)
        if actual != expected:
            changed = sorted(
                key
                for key in set(actual or {}) | set(expected)
                if (actual or {}).get(key) != expected.get(key)
            )
            raise NativeAuthoringError(
                f"{item.source}: native admission failed for {item.identity.qualified}: "
                f"{', '.join(changed) or 'missing object'}"
            )
