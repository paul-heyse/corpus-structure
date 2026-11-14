"""Declared table/schema privileges with truthful initial normalization custody."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Literal, TypedDict

from alembic.autogenerate import renderers
from alembic.operations import MigrateOperation, Operations
from alembic.runtime.plugins import Plugin
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from .native_objects import NativeAuthoringError, native_owner

PUBLISHER = "corpus_sem_publisher"
DEFAULT_READ_ROLES = ("corpus_sem_writer", "corpus_sem_reader", "corpus_sem_admitter", "corpus_sem_evaluator")


PURPOSE_ROLES = (*DEFAULT_READ_ROLES, "corpus_sem_fitter")


class PrivilegePolicy(TypedDict):
    kind: Literal["table", "schema"]
    name: str
    owner: str | None
    acl: list[tuple[str, str, bool]]
    columns: list[tuple[str, str, str, bool]]


class LegacyPrivilegePolicy(TypedDict):
    kind: Literal["table"]
    name: str
    owner: str
    read_roles: list[str]
    unrecorded: list[Literal["acl", "columns"]]


def policy_fact(value) -> PrivilegePolicy:
    """Decode the JSON array representation to its positional typed policy facts."""
    return {"kind": value["kind"], "name": value["name"], "owner": value["owner"],
            "acl": [(role, privilege, bool(grantable)) for role, privilege, grantable in value["acl"]],
            "columns": [(column, role, privilege, bool(grantable)) for column, role, privilege, grantable in value["columns"]]}


def _deny_purpose_create(connection, schema):
    for role in PURPOSE_ROLES:
        if connection.scalar(text("SELECT has_schema_privilege(:role,:schema,'CREATE')"), {"role": role, "schema": schema}):
            raise NativeAuthoringError("purpose principal has effective schema CREATE: " + role)


def table_policy(relation) -> PrivilegePolicy:
    roles = relation.info.get("read_roles", DEFAULT_READ_ROLES)
    return {"kind": "table", "name": relation.fullname, "owner": PUBLISHER,
            "acl": [(role, "SELECT", False) for role in sorted(set(roles))], "columns": []}


def desired_policies(metadata, native) -> tuple[PrivilegePolicy, ...]:
    tables = [table_policy(table) for table in metadata.sorted_tables]
    usages = {str(table.schema): {PUBLISHER} for table in metadata.sorted_tables}
    for table in tables:
        usages[table["name"].split(".")[0]].update(row[0] for row in table["acl"])
    for obj in native:
        usages.setdefault(obj.identity.schema, {PUBLISHER}).update(
            row[0] for row in obj.catalog.get("acl", ()) if row[0].startswith("corpus_")
        )
    schemas: list[PrivilegePolicy] = [{"kind": "schema", "name": schema, "owner": None,
                "acl": sorted([(role, "USAGE", False) for role in roles] + [(PUBLISHER, "CREATE", False)]),
                "columns": []} for schema, roles in sorted(usages.items())]
    return tuple([*tables, *schemas])


def observe_policy(connection, policy) -> PrivilegePolicy | None:
    schema = policy["kind"] == "schema"
    relation = connection.execute(text(
        "SELECT n.oid, pg_get_userbyid(n.nspowner) owner FROM pg_namespace n WHERE n.nspname=:name"
        if schema else
        "SELECT c.oid, pg_get_userbyid(c.relowner) owner FROM pg_class c WHERE c.oid=to_regclass(:name)"
    ), {"name": policy["name"]}).mappings().one_or_none()
    if relation is None:
        return None
    acl = connection.execute(text(
        "SELECT CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(a.grantee) END, "
        "a.privilege_type,a.is_grantable FROM pg_namespace n CROSS JOIN LATERAL "
        "aclexplode(coalesce(n.nspacl,acldefault('n',n.nspowner))) a "
        "WHERE n.oid=:oid AND a.grantee<>n.nspowner"
        if schema else
        "SELECT CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(a.grantee) END, "
        "a.privilege_type,a.is_grantable FROM pg_class c CROSS JOIN LATERAL "
        "aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) a "
        "WHERE c.oid=:oid AND a.grantee<>c.relowner"
    ), {"oid": relation["oid"]}).all()
    # Schema owners have implicit rights and are deliberately outside the usage policy.
    acl = [(role, privilege, bool(grantable)) for role, privilege, grantable in acl]
    if schema:
        acl = [row for row in acl if row[0] != relation["owner"]]
    columns = [] if schema else [(column, role, privilege, bool(grantable)) for column, role, privilege, grantable in connection.execute(text(
        "SELECT at.attname,CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(a.grantee) END,"
        "a.privilege_type,a.is_grantable FROM pg_attribute at CROSS JOIN LATERAL aclexplode(at.attacl) a "
        "WHERE at.attrelid=:oid AND at.attnum>0 AND NOT at.attisdropped"
    ), {"oid": relation["oid"]}).all()]
    return {"kind": policy["kind"], "name": policy["name"], "owner": None if schema else relation["owner"],
            "acl": sorted(acl), "columns": sorted(columns)}


def _expected(connection, policy):
    result = policy_fact(policy)
    if policy["kind"] == "schema":
        owner = connection.scalar(text("SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname=:name"), {"name": policy["name"]})
        if owner in PURPOSE_ROLES:
            raise NativeAuthoringError("purpose principal owns governed schema")
        result["acl"] = [row for row in result["acl"] if row[0] != owner]
    return result


def _revoke_acl_edges(connection, policy, target, kind):
    """Remove observed delegation leaves first; never cascade into implicit dependents."""
    from networkx import DiGraph, NetworkXUnfeasible, lexicographical_topological_sort
    if kind == "SCHEMA":
        sql = "SELECT pg_get_userbyid(a.grantor),CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(a.grantee) END,a.privilege_type,NULL::text FROM pg_namespace n CROSS JOIN LATERAL aclexplode(coalesce(n.nspacl,acldefault('n',n.nspowner))) a WHERE n.nspname=:name AND a.grantee<>n.nspowner"
    else:
        sql = "SELECT pg_get_userbyid(a.grantor),CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(a.grantee) END,a.privilege_type,NULL::text FROM pg_class c CROSS JOIN LATERAL aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) a WHERE c.oid=to_regclass(:name) AND a.grantee<>c.relowner UNION ALL SELECT pg_get_userbyid(a.grantor),CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(a.grantee) END,a.privilege_type,at.attname FROM pg_attribute at CROSS JOIN pg_class c CROSS JOIN LATERAL aclexplode(at.attacl) a WHERE c.oid=to_regclass(:name) AND at.attrelid=c.oid AND at.attnum>0 AND NOT at.attisdropped AND a.grantee<>c.relowner"
    edges = connection.execute(text(sql), {"name": policy["name"]}).all()
    graph = DiGraph()
    graph.add_edges_from((grantor, grantee) for grantor, grantee, _, _ in edges)
    try:
        leaves = list(reversed(list(lexicographical_topological_sort(graph))))
    except NetworkXUnfeasible as error:
        raise NativeAuthoringError("cyclic privilege delegation requires explicit authoring intent") from error
    quote = connection.dialect.identifier_preparer.quote
    for recipient in leaves:
        for grantor, grantee, privilege, column in edges:
            if grantee != recipient:
                continue
            role = "PUBLIC" if grantee == "PUBLIC" else quote(grantee)
            columns = " (" + quote(column) + ")" if column is not None else ""
            try:
                with native_owner(connection, grantor):
                    connection.exec_driver_sql(f"REVOKE {privilege}{columns} ON {kind} {target} FROM {role}")
            except DBAPIError as error:
                state = getattr(error.orig, "sqlstate", None)
                failure = NativeAuthoringError("declared privilege delegation refusal for " + policy["name"] + "; SQLSTATE " + str(state))
                failure.authoring_context = {"operation_kind": "privilege", "object_kind": policy["kind"], "object_name": policy["name"], "sqlstate": state, "dependency_objects": [{"grantor": grantor, "grantee": grantee, "privilege": privilege, "column": column}]}
                raise failure from error


@Operations.register_operation("privilege_transition")
class PrivilegeTransitionOp(MigrateOperation):
    before: PrivilegePolicy | LegacyPrivilegePolicy | None
    after: PrivilegePolicy | None
    def __init__(self, before, after, *, normalization=False):
        if after is None and before is None:
            raise NativeAuthoringError("privilege transition has no declared policy")
        self.before = policy_fact(before) if before is not None and "acl" in before else before
        self.after = policy_fact(after) if after is not None else None
        self.normalization = normalization
        selected = after or before
        if selected["kind"] not in {"table", "schema"}:
            raise NativeAuthoringError("unsupported privilege object")
        if before and after and (before["name"], before["kind"]) != (after["name"], after["kind"]):
            raise NativeAuthoringError("privilege transition changes object identity")

    @classmethod
    def from_payload(cls, payload):
        if payload.get("version") != 1:
            raise NativeAuthoringError("unsupported privilege payload")
        return cls(payload["before"], payload["after"], normalization=payload["normalization"])

    @classmethod
    def privilege_transition(cls, operations, payload):
        return operations.invoke(cls.from_payload(payload))

    def payload(self):
        return {"version": 1, "before": self.before, "after": self.after, "normalization": self.normalization}

    def reverse(self):
        if self.normalization:
            raise NativeAuthoringError("unrecorded initial privilege state cannot be reversed")
        return PrivilegeTransitionOp(self.after, self.before)


@Operations.implementation_for(PrivilegeTransitionOp)
def execute_privileges(operations, operation):
    try:
        _execute_privileges(operations, operation)
    except DBAPIError as error:
        selected = operation.after or operation.before
        state = getattr(error.orig, "sqlstate", None)
        diagnostic = {"operation_kind": "privilege", "object_kind": selected["kind"], "object_name": selected["name"], "sqlstate": state}
        failure = NativeAuthoringError("privilege operation refused for " + selected["name"] + "; SQLSTATE " + str(state))
        failure.authoring_context = diagnostic
        raise failure from error


def _execute_privileges(operations, operation):
    connection = operations.get_bind()
    if operations.migration_context.as_sql:
        raise NativeAuthoringError("privilege operations require a live connection")
    policy = operation.after or operation.before
    observed = observe_policy(connection, policy)
    if observed is None and policy["kind"] == "schema":
        raise NativeAuthoringError("missing declared schema")
    if operation.normalization:
        if operation.before and observed is None:
            raise NativeAuthoringError("missing privilege predecessor")
        if operation.before and policy["kind"] == "table":
            if observed is None:
                raise NativeAuthoringError("missing privilege predecessor")
            before = operation.before
            if "read_roles" not in before:
                raise NativeAuthoringError("initial normalization requires recorded legacy read policy")
            if observed["owner"] != before["owner"]:
                raise NativeAuthoringError("stale recorded table owner")
            for role in sorted(set(DEFAULT_READ_ROLES) | set(before["read_roles"])):
                allowed = connection.scalar(text("SELECT has_table_privilege(:role,to_regclass(:name),'SELECT')"), {"role": role, "name": policy["name"]})
                column_allowed = connection.scalar(text("SELECT has_any_column_privilege(:role,to_regclass(:name),'SELECT')"), {"role": role, "name": policy["name"]})
                mutation = connection.scalar(text("SELECT has_table_privilege(:role,to_regclass(:name),'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') OR has_any_column_privilege(:role,to_regclass(:name),'INSERT,UPDATE,REFERENCES')"), {"role": role, "name": policy["name"]})
                if allowed != (role in before["read_roles"]) or column_allowed != allowed or mutation:
                    raise NativeAuthoringError("stale recorded table read/write privilege")
            if any(row[0] == "PUBLIC" for row in observed["acl"]):
                raise NativeAuthoringError("stale recorded PUBLIC table privilege")
    elif observed != (_expected(connection, operation.before) if operation.before else None):
        raise NativeAuthoringError("stale privilege before-state")
    if operation.after is None:
        return  # Ordinary physical retirement owns object removal.
    quote = connection.dialect.identifier_preparer.quote
    target = quote(policy["name"]) if policy["kind"] == "schema" else ".".join(quote(part) for part in policy["name"].split("."))
    kind = "SCHEMA" if policy["kind"] == "schema" else "TABLE"
    # Table ownership transfer is a migration-authority effect before publisher ACL work.
    if kind == "TABLE" and observed and observed["owner"] != policy["owner"]:
        connection.exec_driver_sql(f"ALTER TABLE {target} OWNER TO {quote(policy['owner'])}")
    owner = policy["owner"] if kind == "TABLE" else connection.scalar(text("SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname=:name"), {"name": policy["name"]})
    if kind == "SCHEMA" and owner in PURPOSE_ROLES:
        raise NativeAuthoringError("purpose principal owns governed schema")
    with native_owner(connection, owner):
        current = observe_policy(connection, policy)
        if current is None:
            raise NativeAuthoringError("missing declared privilege object")
        _revoke_acl_edges(connection, policy, target, kind)
        for grantee, privilege, grantable in _expected(connection, policy)["acl"]:
            connection.exec_driver_sql(f"GRANT {privilege} ON {kind} {target} TO {("PUBLIC" if grantee == "PUBLIC" else quote(grantee))}" + (" WITH GRANT OPTION" if grantable else ""))
        if kind == "SCHEMA":
            _deny_purpose_create(connection, policy["name"])
        if observe_policy(connection, policy) != _expected(connection, policy):
            raise NativeAuthoringError("privilege after-state differs")


@renderers.dispatch_for(PrivilegeTransitionOp)
def render_privileges(context, operation):
    context.imports.add("from corpus_structure.semantic import alembic_privileges")
    return f"op.privilege_transition({operation.payload()!r})"


@contextmanager
def owned_operation(connection, owner):
    """Restore the actual upgrade caller, independently of the authoring login."""
    with native_owner(connection, owner):
        yield


def privilege_operations(before, desired, legacy_tables):
    old = {(item["kind"], item["name"]): policy_fact(item) for item in before}
    legacy = {item["relation"]: item for item in legacy_tables}
    result = []
    for after in map(policy_fact, desired):
        key = (after["kind"], after["name"])
        if key in old:
            if old[key] != after:
                result.append(PrivilegeTransitionOp(old[key], after))
        else:
            prior = legacy.get(after["name"]) if after["kind"] == "table" else None
            known = None if prior is None else {"kind": "table", "name": after["name"], "owner": prior.get("owner", PUBLISHER), "read_roles": prior.get("read_roles", list(DEFAULT_READ_ROLES)), "unrecorded": ["acl", "columns"]}
            result.append(PrivilegeTransitionOp(known, after, normalization=True))
    return result

@Operations.register_operation("owned_sql")
class OwnedSQLOp(MigrateOperation):
    def __init__(self, owner, statement, references=()):
        self.owner, self.statement, self.references = owner, statement, tuple(references)

    @classmethod
    def owned_sql(cls, operations, owner, statement, references=()):
        return operations.invoke(cls(owner, statement, references))

    def reverse(self):
        raise NativeAuthoringError("frozen ordinary DDL requires explicit reverse material")


@Operations.implementation_for(OwnedSQLOp)
def execute_owned_sql(operations, operation):
    connection = operations.get_bind()
    quote = connection.dialect.identifier_preparer.quote
    introduced = []
    for relation, column, owner in operation.references:
        if not connection.scalar(text("SELECT has_column_privilege(:role,:relation,:column,'REFERENCES')"), {"role": operation.owner, "relation": relation, "column": column}):
            target = ".".join(quote(part) for part in relation.split("."))
            with native_owner(connection, owner):
                connection.exec_driver_sql(f"GRANT REFERENCES ({quote(column)}) ON TABLE {target} TO {quote(operation.owner)}")
            introduced.append((relation, column, owner))
    with native_owner(connection, operation.owner):
        connection.exec_driver_sql(operation.statement, execution_options={"no_parameters": True})
    for relation, column, owner in introduced:
        target = ".".join(quote(part) for part in relation.split("."))
        with native_owner(connection, owner):
            connection.exec_driver_sql(f"REVOKE REFERENCES ({quote(column)}) ON TABLE {target} FROM {quote(operation.owner)}")


@renderers.dispatch_for(OwnedSQLOp)
def render_owned_sql(context, operation):
    context.imports.add("from corpus_structure.semantic import alembic_privileges")
    return f"op.owned_sql({operation.owner!r}, {operation.statement!r}, {operation.references!r})"


def operation_record(operation):
    from .alembic_native import NativeTransitionOp
    if isinstance(operation, NativeTransitionOp):
        return {"kind": "native", "payload": operation.payload()}
    if isinstance(operation, PrivilegeTransitionOp):
        return {"kind": "privilege", "payload": operation.payload()}
    raise NativeAuthoringError("unsupported frozen operation record")


def native_operation_payloads(state):
    if state.get("version") == 1:
        return tuple(state.get("operations", ()))
    if state.get("version") != 2:
        raise NativeAuthoringError("unsupported frozen artifact envelope")
    result = []
    for record in state.get("operations", ()):
        if record.get("kind") == "native":
            result.append(record["payload"])
        elif record.get("kind") == "privilege":
            PrivilegeTransitionOp.from_payload(record["payload"])
        else:
            raise NativeAuthoringError("unsupported frozen operation kind")
    return tuple(result)


def admit_privileges(connection, policies):
    for policy in policies:
        if policy["kind"] == "schema":
            _deny_purpose_create(connection, policy["name"])
        if observe_policy(connection, policy) != _expected(connection, policy):
            raise NativeAuthoringError("frozen privilege admission differs: " + policy["name"])

@Operations.register_operation("owned_operations")
class OwnedOperationsOp(MigrateOperation):
    def __init__(self, owner, operations):
        self.owner, self.ops = owner, list(operations)

    @classmethod
    def owned_operations(cls, operations, owner, children):
        return operations.invoke(cls(owner, children))

    def reverse(self):
        return OwnedOperationsOp(self.owner, [operation.reverse() for operation in reversed(self.ops)])


@Operations.implementation_for(OwnedOperationsOp)
def execute_owned_operations(operations, operation):
    with native_owner(operations.get_bind(), operation.owner):
        for child in operation.ops:
            operations.invoke(child)


@renderers.dispatch_for(OwnedOperationsOp)
def render_owned_operations(context, operation):
    from alembic.autogenerate.render import render_op
    context.imports.add("from corpus_structure.semantic import alembic_privileges")
    body = [line for child in operation.ops for rendered in render_op(context, child) for line in rendered.splitlines()]
    return "with alembic_privileges.owned_operation(op.get_bind(), " + repr(operation.owner) + "):\n" + "\n".join("    " + line for line in body)


def admission_comparison_sql():
    roles_sql = ",".join("('" + role + "')" for role in PURPOSE_ROLES)
    return """
 IF EXISTS(
 SELECT FROM jsonb_array_elements(expected->'privileges') policy
 CROSS JOIN (VALUES __PURPOSE_ROLES__) principal(name)
 WHERE policy->>'kind'='schema' AND has_schema_privilege(principal.name,policy->>'name','CREATE')
 ) THEN RAISE EXCEPTION 'purpose principal has effective schema CREATE' USING ERRCODE='42501'; END IF;
 IF EXISTS(
 SELECT FROM jsonb_array_elements(expected->'privileges') policy
 WHERE (CASE WHEN policy->>'kind'='table' THEN
   (SELECT coalesce(jsonb_agg(jsonb_build_array(CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(a.grantee) END,a.privilege_type,a.is_grantable) ORDER BY (CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(a.grantee) END) COLLATE "C",a.privilege_type COLLATE "C",a.is_grantable),'[]'::jsonb)
    FROM pg_class c CROSS JOIN LATERAL aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) a WHERE c.oid=to_regclass(policy->>'name') AND a.grantee<>c.relowner)
   IS DISTINCT FROM policy->'acl'
   OR EXISTS(SELECT FROM pg_attribute at CROSS JOIN LATERAL aclexplode(at.attacl) a WHERE at.attrelid=to_regclass(policy->>'name') AND at.attnum>0 AND NOT at.attisdropped)
 ELSE
   (SELECT coalesce(jsonb_agg(jsonb_build_array(CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(a.grantee) END,a.privilege_type,a.is_grantable) ORDER BY (CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(a.grantee) END) COLLATE "C",a.privilege_type COLLATE "C",a.is_grantable),'[]'::jsonb)
    FROM pg_namespace n CROSS JOIN LATERAL aclexplode(coalesce(n.nspacl,acldefault('n',n.nspowner))) a WHERE n.nspname=policy->>'name' AND a.grantee<>n.nspowner)
   IS DISTINCT FROM (SELECT coalesce(jsonb_agg(entry ORDER BY (entry->>0) COLLATE "C",(entry->>1) COLLATE "C",(entry->>2)::boolean),'[]'::jsonb) FROM jsonb_array_elements(policy->'acl') entry WHERE entry->>0 IS DISTINCT FROM (SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname=policy->>'name')) END)
 ) THEN RAISE EXCEPTION 'declared table/schema privilege policy differs' USING ERRCODE='42501'; END IF;
""".replace("__PURPOSE_ROLES__", roles_sql)


def compare_table_policy(context, changes, schema, name, reflected, declared):
    from alembic.util import PriorityDispatchResult
    if declared is not None:
        options = context.migration_context.opts
        desired = [policy for policy in options["declared_privileges"] if policy["kind"] == "table" and policy["name"] == declared.fullname]
        options["compared_privileges"].extend(privilege_operations(options["predecessor_privileges"], desired, options["legacy_privilege_tables"]))
    return PriorityDispatchResult.CONTINUE


def compare_schema_policy(context, changes, schemas):
    from alembic.util import PriorityDispatchResult
    options = context.migration_context.opts
    desired = [policy for policy in options["declared_privileges"] if policy["kind"] == "schema" and policy["name"] in schemas]
    options["compared_privileges"].extend(privilege_operations(options["predecessor_privileges"], desired, options["legacy_privilege_tables"]))
    return PriorityDispatchResult.CONTINUE


plugin = Plugin("corpus.semantic.privileges")
plugin.add_autogenerate_comparator(compare_table_policy, "table", "privileges", qualifier="postgresql")
plugin.add_autogenerate_comparator(compare_schema_policy, "schema", "privileges", qualifier="postgresql")
