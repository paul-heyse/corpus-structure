"""Render the dedicated host's role, database and peer-authentication declarations.

The shell entrypoints own host service/file effects and execute these statements.
Rendering acquires no database connection and changes no server state.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

from pglast import ast, enums
from pglast.stream import RawStream
from sqlalchemy import Boolean, Connection, Text, column, exists, func, literal, or_, select, table
from sqlalchemy.dialects.postgresql import OID, aggregate_order_by, dialect

from corpus_structure.schema.integrity import integrity
from corpus_structure.semantic.native_objects import native_sql_script
from corpus_structure.semantic.native_program import Block, Do, If, Raise, Sql

from .extensions import expected_extensions


@dataclass(frozen=True)
class Principal:
    purpose: str
    name: str
    login: bool = True
    inherit: bool | None = None


PEER_MAP = "corpus_semantic"


def integrity_principals():
    policy = integrity()
    result = [Principal("publisher", policy.publisher, login=False)]
    for purpose, name in policy.purposes.items():
        if name is not None:
            role = policy.roles[name]
            result.append(Principal(purpose, name, login=role.login, inherit=role.inherit))
    return tuple(result)


def _catalog(name, **columns):
    return table(name, *(column(name, kind) for name, kind in columns.items()), schema="pg_catalog")


ROLES = _catalog(
    "pg_roles",
    oid=OID,
    rolname=Text,
    rolcanlogin=Boolean,
    rolinherit=Boolean,
    rolsuper=Boolean,
    rolcreatedb=Boolean,
    rolcreaterole=Boolean,
    rolreplication=Boolean,
    rolbypassrls=Boolean,
)
MEMBERS = _catalog(
    "pg_auth_members",
    member=OID,
    roleid=OID,
    grantor=OID,
    admin_option=Boolean,
    inherit_option=Boolean,
    set_option=Boolean,
)
DATABASES = _catalog("pg_database", datname=Text)
EXTENSIONS = _catalog("pg_extension", extname=Text, extversion=Text)


class RoleObservation(TypedDict):
    oid: int
    rolname: str
    rolcanlogin: bool
    rolinherit: bool
    rolsuper: bool
    rolcreatedb: bool
    rolcreaterole: bool
    rolreplication: bool
    rolbypassrls: bool


class MembershipObservation(TypedDict):
    member: int
    roleid: int
    grantor: int
    admin_option: bool
    inherit_option: bool
    set_option: bool
    member_name: str
    role_name: str
    grantor_name: str


class SemanticRolePolicy(TypedDict):
    roles: list[RoleObservation]
    memberships: list[MembershipObservation]


def observe_semantic_role_policy(
    connection: Connection, names: tuple[str, ...]
) -> SemanticRolePolicy:
    """Observe provisioned capability and membership policy in both membership directions."""
    roles = (
        connection.execute(
            select(ROLES).where(ROLES.c.rolname.in_(names)).order_by(ROLES.c.rolname)
        )
        .mappings()
        .all()
    )
    member = ROLES.alias("member_role")
    granted = ROLES.alias("granted_role")
    grantor = ROLES.alias("grantor_role")
    memberships = (
        connection.execute(
            select(
                MEMBERS,
                member.c.rolname.label("member_name"),
                granted.c.rolname.label("role_name"),
                grantor.c.rolname.label("grantor_name"),
            )
            .select_from(
                MEMBERS.join(member, MEMBERS.c.member == member.c.oid)
                .join(granted, MEMBERS.c.roleid == granted.c.oid)
                .join(grantor, MEMBERS.c.grantor == grantor.c.oid)
            )
            .where(or_(member.c.rolname.in_(names), granted.c.rolname.in_(names)))
            .order_by(MEMBERS.c.member, MEMBERS.c.roleid, MEMBERS.c.grantor)
        )
        .mappings()
        .all()
    )
    return {
        "roles": [cast(RoleObservation, dict(row)) for row in roles],
        "memberships": [cast(MembershipObservation, dict(row)) for row in memberships],
    }


def _options(values):
    return tuple(
        ast.DefElem(defname=name, arg=ast.Boolean(boolval=value)) for name, value in values.items()
    )


def _role(role, *, create, administrative=False):
    values = {"canlogin": role.login}
    if role.inherit is not None:
        values["inherit"] = role.inherit
    values.update(superuser=administrative, createdb=administrative, createrole=administrative)
    if not administrative:
        values.update(isreplication=False, bypassrls=False)
    if create:
        return ast.CreateRoleStmt(
            stmt_type=enums.RoleStmtType.ROLESTMT_ROLE, role=role.name, options=_options(values)
        )
    return ast.AlterRoleStmt(
        role=ast.RoleSpec(roletype=enums.RoleSpecType.ROLESPEC_CSTRING, rolename=role.name),
        options=_options(values),
        action=1,
    )


def _grant_role(name, grantee, *, set_only=False):
    return ast.GrantRoleStmt(
        granted_roles=(ast.AccessPriv(priv_name=name),),
        grantee_roles=(
            ast.RoleSpec(roletype=enums.RoleSpecType.ROLESPEC_CSTRING, rolename=grantee),
        ),
        is_grant=True,
        opt=_options({"inherit": False, "set": True}) if set_only else (),
        behavior=enums.DropBehavior.DROP_RESTRICT,
    )


def semantic_roles(operator: str, *, fitter_only: bool = False) -> str:
    principals = integrity_principals()
    selected = (
        tuple(role for role in principals if role.purpose == "fit") if fitter_only else principals
    )
    steps: list[If | Sql] = []
    for role in selected:
        steps.append(
            If(
                ~exists(select(1).select_from(ROLES).where(ROLES.c.rolname == role.name)),
                (Sql(_role(role, create=True)),),
            )
        )
        if not fitter_only:
            steps.append(Sql(_role(role, create=False)))
    memberships = exists(
        select(1)
        .select_from(MEMBERS.join(ROLES, MEMBERS.c.member == ROLES.c.oid))
        .where(ROLES.c.rolname.in_(tuple(role.name for role in selected)))
    )
    if fitter_only:
        role = selected[0]
        mismatch = exists(
            select(1)
            .select_from(ROLES)
            .where(
                ROLES.c.rolname == role.name,
                or_(
                    ~ROLES.c.rolcanlogin,
                    ROLES.c.rolinherit,
                    ROLES.c.rolsuper,
                    ROLES.c.rolcreatedb,
                    ROLES.c.rolcreaterole,
                    ROLES.c.rolreplication,
                    ROLES.c.rolbypassrls,
                ),
            )
        )
        steps.append(
            If(
                or_(mismatch, memberships),
                (
                    Raise(
                        "existing fitting role differs from restricted provisioning contract",
                        "P0001",
                    ),
                ),
            )
        )
    else:
        steps.append(
            If(memberships, (Raise("semantic principals must not inherit any role", "P0001"),))
        )
        publisher = next(role.name for role in principals if role.purpose == "publisher")
        steps.append(Sql(_grant_role(publisher, operator, set_only=True)))
    return Do(Block(tuple(steps)))


def base_roles(owner: str) -> str:
    administrator = Principal("operator", owner)
    readonly = Principal("legacy_read", "corpus_ro", login=False)
    return Do(
        Block(
            (
                If(
                    ~exists(select(1).select_from(ROLES).where(ROLES.c.rolname == owner)),
                    (Sql(_role(administrator, create=True, administrative=True)),),
                    (Sql(_role(administrator, create=False, administrative=True)),),
                ),
                If(
                    ~exists(select(1).select_from(ROLES).where(ROLES.c.rolname == readonly.name)),
                    (
                        Sql(
                            ast.CreateRoleStmt(
                                stmt_type=enums.RoleStmtType.ROLESTMT_ROLE,
                                role=readonly.name,
                                options=_options({"canlogin": False}),
                            )
                        ),
                    ),
                ),
                Sql(_grant_role("pg_read_all_data", readonly.name)),
                Sql(_grant_role(readonly.name, owner)),
            )
        )
    )


def peer_principals(*, fitter_only=False):
    return tuple(
        role
        for role in integrity_principals()
        if role.login and (not fitter_only or role.purpose == "fit")
    )


def peer_hba(*, fitter_only=False):
    return (
        "local all "
        + ",".join(role.name for role in peer_principals(fitter_only=fitter_only))
        + " peer map="
        + PEER_MAP
    )


def peer_ident(operator: str, *, fitter_only=False):
    # Keep the host file token contract used by the original provisioning entrypoint.
    if re.fullmatch(r"[a-z_][a-z0-9_-]*", operator) is None:
        raise ValueError("unsupported operator name")
    return "\n".join(
        PEER_MAP + " " + operator + " " + role.name
        for role in peer_principals(fitter_only=fitter_only)
    )


def _render(statement):
    if isinstance(statement, ast.Node):
        return RawStream()(statement)
    return str(
        statement.compile(
            dialect=dialect(paramstyle="named"), compile_kwargs={"literal_binds": True}
        )
    )


def sql_command(action: str, arguments: list[str]) -> str:
    if action == "database-exists":
        statement = select(1).select_from(DATABASES).where(DATABASES.c.datname == arguments[0])
    elif action == "database-create":
        statement = ast.CreatedbStmt(
            dbname=arguments[0],
            options=(ast.DefElem(defname="owner", arg=ast.String(sval=arguments[1])),),
        )
    elif action == "extension-version":
        statement = select(EXTENSIONS.c.extversion).where(EXTENSIONS.c.extname == arguments[0])
    elif action == "extension-list":
        statement = select(
            func.string_agg(
                EXTENSIONS.c.extname + " " + EXTENSIONS.c.extversion,
                aggregate_order_by(literal(", "), EXTENSIONS.c.extname),
            )
        )
    elif action == "extension-install":
        name, version = arguments
        options = (ast.DefElem(defname="new_version", arg=ast.String(sval=version)),)
        return native_sql_script(
            (
                RawStream()(
                    ast.VariableSetStmt(
                        kind=enums.VariableSetKind.VAR_SET_VALUE,
                        name="client_min_messages",
                        args=(ast.A_Const(val=ast.String(sval="warning")),),
                    )
                ),
                RawStream()(
                    ast.CreateExtensionStmt(extname=name, if_not_exists=True, options=options)
                ),
                RawStream()(ast.AlterExtensionStmt(extname=name, options=options)),
            )
        )
    elif action == "template":
        statement = ast.AlterDatabaseStmt(
            dbname=arguments[0],
            options=(
                ast.DefElem(
                    defname="is_template",
                    arg=ast.String(sval="true"),
                    defaction=enums.DefElemAction.DEFELEM_UNSPEC,
                ),
            ),
        )
    elif action == "server-version":
        statement = select(literal("version ") + func.current_setting("server_version"))
    elif action == "setting":
        statement = ast.VariableShowStmt(name=arguments[0])
    elif action == "reload":
        statement = select(func.pg_catalog.pg_reload_conf())
    elif action == "auth-check":
        errors = [
            exists(
                select(1)
                .select_from(_catalog(name, error=Text))
                .where(column("error", Text).is_not(None))
            )
            for name in ("pg_hba_file_rules", "pg_ident_file_mappings")
        ]
        return Do(
            Block((If(or_(*errors), (Raise("invalid authentication configuration", "P0001"),)),))
        )
    else:
        raise ValueError("unsupported host statement")
    return _render(statement)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "principals",
            "semantic-sql",
            "base-sql",
            "peer-hba",
            "peer-ident",
            "expected",
            "database-exists",
            "database-create",
            "extension-version",
            "extension-list",
            "extension-install",
            "template",
            "server-version",
            "setting",
            "reload",
            "auth-check",
        ),
    )
    parser.add_argument("arguments", nargs="*")
    parser.add_argument("--fitter-only", action="store_true")
    parser.add_argument("--record", type=Path)
    args = parser.parse_args()
    arities = {
        "semantic-sql": 1,
        "base-sql": 1,
        "peer-ident": 1,
        "database-exists": 1,
        "database-create": 2,
        "extension-version": 1,
        "extension-install": 2,
        "template": 1,
        "setting": 1,
    }
    if len(args.arguments) != arities.get(args.action, 0):
        parser.error("incorrect number of host declaration arguments")
    if args.action == "principals":
        result = "\n".join(role.purpose + " " + role.name for role in integrity_principals())
    elif args.action == "semantic-sql":
        result = semantic_roles(args.arguments[0], fitter_only=args.fitter_only)
    elif args.action == "base-sql":
        result = base_roles(args.arguments[0])
    elif args.action == "peer-hba":
        result = peer_hba(fitter_only=args.fitter_only)
    elif args.action == "peer-ident":
        result = peer_ident(args.arguments[0], fitter_only=args.fitter_only)
    elif args.action == "expected":
        result = "\n".join(
            name + " " + version for name, version in expected_extensions(args.record).items()
        )
    else:
        result = sql_command(args.action, args.arguments)
    print(result)


if __name__ == "__main__":
    main()
