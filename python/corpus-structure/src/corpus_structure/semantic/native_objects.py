"""Explicit PostgreSQL native authoring scope and server-normalized catalog projections.

Only an owned authoring connection may prepare definitions. Normal deployment uses frozen
payloads and never imports today's generators or prepares desired state on a reader.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace

from pglast import ast, enums
from pglast.stream import RawStream
from sqlalchemy import Connection, Integer, cast, func, literal, select, text

from . import native_catalog as catalog_queries
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.exc import DBAPIError

from .prepared_sql import prepare_sql


class NativeAuthoringError(ValueError):
    """Explicit native source, scope, catalog or transition refusal."""


def _quote(value: str) -> str:
    return dialect(paramstyle="named").identifier_preparer.quote(value)


def execute_native_sql(connection: Connection, sql: str) -> None:
    """Preserve trusted literal percent/colon content on the caller's Connection."""
    connection.exec_driver_sql(sql, execution_options={"no_parameters": True})


@contextmanager
def native_owner(connection: Connection, owner: str | None):
    """Apply object effects as their explicit owner, then restore the caller's role.

    PostgreSQL can warn instead of revoking a different grantor's ACL when a migration
    login may SET the owner role but does not inherit it. Running as the selected owner
    makes the complete privilege effects real. A database error requires caller rollback,
    which also restores SET LOCAL state; never hide it with a failed cleanup statement.
    """
    previous = connection.scalar(text("SELECT current_setting('role')"))
    changed = owner is not None and owner != connection.scalar(text("SELECT current_user"))
    if changed:
        execute_native_sql(connection, "SET LOCAL ROLE " + _quote(owner))
    failed = False
    try:
        yield
    except DBAPIError:
        failed = True
        raise
    finally:
        if changed and not failed:
            role = "NONE" if previous == "none" else _quote(previous)
            execute_native_sql(connection, "SET LOCAL ROLE " + role)


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
        if self.kind == "trigger":
            return (
                f"DROP TRIGGER {_quote(self.name)} ON "
                f"{_quote(self.schema)}.{_quote(self.relation or '')}"
            )
        if self.kind not in {"function", "view"}:
            raise NativeAuthoringError(f"unsupported native object {self.kind}")
        return f"DROP {self.kind.upper()} {self.qualified}"

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
            action = {"O": "ENABLE", "D": "DISABLE", "R": "ENABLE REPLICA", "A": "ENABLE ALWAYS"}[
                self.enabled
            ]
            relation = _quote(self.identity.schema) + "." + _quote(self.identity.relation or "")
            result.append(f"ALTER TABLE {relation} {action} TRIGGER {_quote(self.identity.name)}")
        else:
            target = self.identity.kind.upper() + " " + self.identity.qualified
            result.append(f"ALTER {target} OWNER TO {_quote(self.owner or '')}")
            target = (
                ("FUNCTION" if self.identity.kind == "function" else "TABLE")
                + " "
                + self.identity.qualified
            )
            # Fresh normalization starts from default ACLs, then sets the complete desired ACL.
            result.append(f"REVOKE ALL ON {target} FROM PUBLIC")
            for grantee, privilege, option in self.grants:
                role = "PUBLIC" if grantee == "PUBLIC" else _quote(grantee)
                result.append(
                    f"GRANT {privilege} ON {target} TO {role}"
                    + (" WITH GRANT OPTION" if option else "")
                )
        return tuple(result)


def definition_from_sql(
    connection: Connection,
    sql: str,
    *,
    source: str,
    owner: str | None = None,
    grants: tuple[tuple[str, str, bool], ...] = (),
    enabled: str = "O",
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
            canonical = connection.scalar(
                select(catalog_queries.pg.format_type(catalog_queries.pg.to_regtype(kind), None)),
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
    return NativeDefinition(identity, sql, source, owner, grants, enabled)


def observe_native(
    connection: Connection, identity: NativeIdentity, *, catalog_version: int | None = 1
) -> dict | None:
    """Read selected properties independently from catalog fields; NULL ACL uses acldefault."""
    if catalog_version not in {None, 1, 2}:
        raise NativeAuthoringError("unsupported native catalog comparison profile")
    if identity.kind == "function":
        statement = catalog_queries.function_observation(identity.qualified)
    elif identity.kind == "view":
        statement = catalog_queries.view_observation(identity.schema, identity.name)
    elif identity.kind == "trigger":
        statement = catalog_queries.trigger_observation(identity.schema, identity.name, identity.relation)
    else:
        raise NativeAuthoringError(f"unsupported native kind {identity.kind}")
    row = connection.execute(statement).mappings().one_or_none()
    if identity.kind == "trigger":
        return None if row is None else dict(row)
    if row is not None and identity.kind == "view" and row["kind"] != "v":
        raise NativeAuthoringError(
            f"{identity.qualified}: selected object is not an ordinary view"
        )
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
                select(catalog_queries.pg.pg_get_functiondef(catalog_queries.pg.to_regprocedure(identity.qualified)))
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
        catalog_queries.acl_rows(literal(result.pop("acl")), literal(aclkind), literal(result.pop("proowner")))
    ).all()
    result.pop("oid")
    result["acl"] = [list(item) for item in acl]
    if "config" in result:
        result["config"] = sorted(result["config"] or ())
    if "options" in result:
        result["options"] = sorted(result["options"] or ())
    return result


def semantic_namespace_owner(connection: Connection) -> str:
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
    target = ("FUNCTION" if identity.kind == "function" else "TABLE") + " " + identity.qualified
    for grantee in sorted({grant[0] for grant in installed["acl"]}):
        role = "PUBLIC" if grantee == "PUBLIC" else _quote(grantee)
        execute_native_sql(connection, f"REVOKE ALL ON {target} FROM {role}")
    for grantee, privilege, option in grants:
        role = "PUBLIC" if grantee == "PUBLIC" else _quote(grantee)
        execute_native_sql(
            connection,
            f"GRANT {privilege} ON {target} TO {role}" + (" WITH GRANT OPTION" if option else ""),
        )


def _declared_acl(connection: Connection, definition: NativeDefinition):
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
            raise NativeAuthoringError("duplicate managed native identity")
        if before - desired != self.retire:
            raise NativeAuthoringError(
                "native retirement must explicitly equal removed predecessor identities"
            )
        if self.recreate - (desired & before):
            raise NativeAuthoringError(
                "recreation must name a predecessor and desired native identity"
            )


def prepare_native_authoring(
    connection: Connection,
    definitions: tuple[NativeDefinition, ...],
    *,
    predecessor: tuple[NativeDefinition | NativeObject, ...] = (),
    retire: frozenset[NativeIdentity] = frozenset(),
    recreate: frozenset[NativeIdentity] = frozenset(),
    owned_authoring: bool = False,
) -> NativeAuthoring:
    """Normalize complete declared definitions in rollback-only authoring savepoints.

    Definitions are dependency ordered. The caller explicitly owns this disposable database;
    normalization refuses ordinary runtime principals. Predecessor meaning comes from supplied
    source, never adoption of live catalog state. No implicit CASCADE is used.
    """
    if not owned_authoring:
        raise NativeAuthoringError(
            "native preparation requires an explicitly owned authoring database"
        )
    principal = connection.scalar(text("SELECT current_user"))
    if principal in {
        "corpus_sem_reader",
        "corpus_sem_writer",
        "corpus_sem_admitter",
        "corpus_sem_evaluator",
    }:
        raise NativeAuthoringError("native preparation cannot use a runtime principal")
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
    scope = tuple(dict.fromkeys(item.identity for item in (*predecessor, *definitions)))

    def normalize(items):
        savepoint = connection.begin_nested()
        try:
            # Union order is explicit dependency order; dependencies absent from the scope
            # make PostgreSQL refuse, rather than silently authorizing a dependent drop.
            for identity in reversed(scope):
                installed = observe_native(connection, identity, catalog_version=None)
                if installed is not None:
                    with native_owner(connection, installed.get("owner")):
                        execute_native_sql(connection, identity.drop_sql)
            for item in items:
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
                    for statement in item.install_sql:
                        execute_native_sql(connection, statement)
                    if item.identity.kind != "trigger":
                        set_native_acl(
                            connection,
                            item.identity,
                            _declared_acl(connection, item),
                            catalog_version=item.catalog_version,
                        )
            result = []
            for item in items:
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
                        != (
                            f"GRANT EXECUTE ON FUNCTION {item.identity.qualified} "
                            f"TO {_quote(migration_owner)}"
                        )
                    )
                    if item.bind_owner:
                        owner_statement = (
                            "ALTER "
                            + item.identity.kind.upper()
                            + " "
                            + item.identity.qualified
                            + " OWNER TO "
                            + _quote(migration_owner)
                        )
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
        finally:
            savepoint.rollback()

    before = (
        tuple(item for item in predecessor if isinstance(item, NativeObject))
        if frozen_predecessor
        else normalize(tuple(item for item in predecessor if isinstance(item, NativeDefinition)))
    )
    desired = normalize(definitions)
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
