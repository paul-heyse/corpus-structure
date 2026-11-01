"""Stable frozen native-operation payload v1 and Alembic's comparison/render lifecycle."""

from __future__ import annotations

from alembic.autogenerate import renderers
from alembic.operations import MigrateOperation, Operations
from alembic.runtime.plugins import Plugin
from alembic.util import PriorityDispatchResult

from .native_objects import (
    NativeAuthoring,
    NativeAuthoringError,
    NativeObject,
    execute_native_sql,
    native_owner,
    observe_native,
    set_native_acl,
)


@Operations.register_operation("native_transition")
class NativeTransitionOp(MigrateOperation):
    def __init__(self, before: NativeObject | None, after: NativeObject | None, *, recreate=False):
        if before is None and after is None:
            raise NativeAuthoringError("native transition requires before or after material")
        if before is not None and after is not None and before.identity != after.identity:
            raise NativeAuthoringError("native transition cannot silently change an identity")
        if (
            before is not None
            and after is not None
            and before.identity.kind == "function"
            and not recreate
        ):
            if (before.catalog["result"], before.catalog["setof"]) != (
                after.catalog["result"],
                after.catalog["setof"],
            ):
                raise NativeAuthoringError(
                    f"native result change requires explicit recreation: {after.identity.qualified}"
                )
            if before.catalog["arguments"] != after.catalog["arguments"]:
                raise NativeAuthoringError(
                    "native argument change requires explicit recreation: "
                    f"{after.identity.qualified}"
                )
        self.before, self.after, self.recreate = before, after, recreate

    @classmethod
    def native_transition(cls, operations, payload):
        if payload.get("version") != 1:
            raise NativeAuthoringError("unsupported frozen native operation payload")
        operation = cls(
            NativeObject.from_payload(payload["before"]) if payload["before"] else None,
            NativeObject.from_payload(payload["after"]) if payload["after"] else None,
            recreate=payload["recreate"],
        )
        return operations.invoke(operation)

    @property
    def identity(self):
        item = self.after if self.after is not None else self.before
        if item is None:
            raise NativeAuthoringError("native transition lacks its identity material")
        return item.identity

    def payload(self):
        return {
            "version": 1,
            "before": self.before.payload() if self.before else None,
            "after": self.after.payload() if self.after else None,
            "recreate": self.recreate,
        }

    def reverse(self):
        return NativeTransitionOp(self.after, self.before, recreate=self.recreate)


@Operations.implementation_for(NativeTransitionOp)
def execute_native(operations, operation):
    if operations.migration_context.as_sql:
        raise NativeAuthoringError("native operations require an explicit live Connection")
    connection = operations.get_bind()
    expected = operation.before.expected_catalog(connection) if operation.before else None
    actual = observe_native(connection, operation.identity)
    if actual != expected:
        raise NativeAuthoringError(f"stale native before-state for {operation.identity.qualified}")
    # Validate the whole directive before any effects. Result changes need explicit
    # dependency/recreation authorization; CREATE OR REPLACE cannot perform them.
    if (
        operation.before
        and operation.after
        and operation.identity.kind == "function"
        and not operation.recreate
    ):
        before, after = operation.before.catalog, operation.after.catalog
        if (before["result"], before["setof"]) != (after["result"], after["setof"]):
            raise NativeAuthoringError(
                f"native result change requires explicit recreation: {operation.identity.qualified}"
            )
    target_catalog = operation.after.expected_catalog(connection) if operation.after else None
    owner_catalog = target_catalog if target_catalog is not None else expected
    if owner_catalog is None:
        raise NativeAuthoringError("native transition lacks its owner material")
    owner = owner_catalog.get("owner")
    with native_owner(connection, owner):
        if operation.before and (
            operation.after is None or operation.recreate or operation.identity.kind == "trigger"
        ):
            execute_native_sql(connection, operation.identity.drop_sql)
        if operation.after:
            if target_catalog is None:
                raise NativeAuthoringError("native transition lacks its desired catalog material")
            for statement in operation.after.statements:
                # SQLAlchemy no_parameters preserves archived colon/percent content.
                execute_native_sql(connection, statement)
            if operation.identity.kind != "trigger":
                # Frozen complete ACL replaces ambient default grants and prior effects.
                set_native_acl(connection, operation.identity, target_catalog["acl"])
            if observe_native(connection, operation.identity) != target_catalog:
                raise NativeAuthoringError(
                    f"native after-state differs for {operation.identity.qualified}"
                )


@renderers.dispatch_for(NativeTransitionOp)
def render_native(autogen_context, operation):
    autogen_context.imports.add("from corpus_structure.semantic import alembic_native")
    return f"op.native_transition({operation.payload()!r})"


def compare_native(autogen_context, upgrade_ops, schemas):
    authoring = autogen_context.migration_context.opts.get("native_authoring")
    if not isinstance(authoring, NativeAuthoring):
        raise NativeAuthoringError(
            "native autogeneration requires explicit native_authoring context"
        )
    before = {item.identity: item for item in authoring.predecessor}
    desired = {item.identity: item for item in authoring.desired}
    # Refuse drift before appending any operation; absent desired context never means drop.
    for identity in before.keys() | desired.keys():
        if identity.schema not in schemas:
            raise NativeAuthoringError(
                f"managed native schema excluded from comparison: {identity.schema}"
            )
        expected = (
            before[identity].expected_catalog(autogen_context.connection)
            if identity in before
            else None
        )
        actual = observe_native(autogen_context.connection, identity)
        target = (
            desired[identity].expected_catalog(autogen_context.connection)
            if identity in desired
            else None
        )
        if actual != expected and actual != target:
            raise NativeAuthoringError(
                f"unexpected catalog state for managed native object {identity.qualified}"
            )
    recreations = (
        authoring.recreate
        if any(
            observe_native(autogen_context.connection, identity)
            != desired[identity].expected_catalog(autogen_context.connection)
            for identity in authoring.recreate
        )
        else frozenset()
    )
    # Explicitly recreated dependents retire first, then their providers. Reverse() and
    # Alembic's reversed downgrade order restore the actual prior definitions in turn.
    for previous in reversed(authoring.predecessor):
        if (
            previous.identity in authoring.retire | recreations
            and observe_native(autogen_context.connection, previous.identity) is not None
        ):
            upgrade_ops.ops.append(NativeTransitionOp(previous, None))
    for item in authoring.desired:
        actual = observe_native(autogen_context.connection, item.identity)
        if item.identity in recreations:
            upgrade_ops.ops.append(NativeTransitionOp(None, item))
        elif actual != item.expected_catalog(autogen_context.connection):
            upgrade_ops.ops.append(NativeTransitionOp(before.get(item.identity), item))
    return PriorityDispatchResult.CONTINUE


plugin = Plugin("corpus.semantic.native")
plugin.add_autogenerate_comparator(compare_native, "schema", "native", qualifier="postgresql")
