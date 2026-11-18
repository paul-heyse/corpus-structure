"""Closed DATA authoring and its frozen upgrade boundary."""

from contextlib import nullcontext
from functools import partial
from io import StringIO

import pytest
from alembic.operations import Operations, ops
from alembic.runtime.migration import MigrationContext
from model_change_support import model_checkout as model_checkout
from pydantic import ValidationError
from sqlalchemy import Column, ForeignKey, Text

from corpus_structure.schema import data_steps, model
from corpus_structure.schema.model_change import ChangeRequest, check_preview, prepare_preview
from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.alembic_privileges import OwnedOperationsOp
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import (
    NativeAuthoring,
    NativeAuthoringError,
    NativeIdentity,
    NativeObject,
)

PREDECESSOR = None
prepare_data_steps = partial(
    data_steps.prepare_data_steps, target=get_metadata(), predecessor=PREDECESSOR
)
order_data_steps = partial(
    data_steps.order_data_steps, target=get_metadata(), predecessor=PREDECESSOR
)


def n1():
    return prepare_data_steps((data_steps.DataStepRequest(name="ddo_n1_relower"),))


def guarded_authoring(step):
    guards = []
    for relation in step.guarded_relations:
        schema, name = relation.split(".")
        guards.append(
            NativeObject(
                NativeIdentity("trigger", schema, "semantic_immutable", relation=name),
                "fixture: intrinsic guard",
                (
                    f"CREATE TRIGGER semantic_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON {relation} FOR EACH STATEMENT EXECUTE FUNCTION sem.refuse_immutable_mutation()",
                ),
                "{}",
            )
        )
    return NativeAuthoring(tuple(guards))


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "arbitrary.module.builder"},
        {"name": "ddo_n1_relower", "sql": "DELETE FROM sem.release"},
        {"name": "ddo_n1_relower", "parameters": {"release_id": "invented"}},
    ],
)
def test_requests_cannot_select_python_sql_or_invented_evidence(payload):
    with pytest.raises(ValidationError):
        data_steps.DataStepRequest.model_validate(payload)


def test_data_steps_require_native_custody_and_are_not_repeatable():
    request = data_steps.DataStepRequest(name="ddo_n1_relower")
    with pytest.raises(ValidationError, match="explicit native authoring"):
        ChangeRequest(data_steps=(request,))
    with pytest.raises(ValidationError, match="duplicate revision data step"):
        ChangeRequest(native_revision="n1", data_steps=(request, request))
    with pytest.raises(ValueError, match="duplicate revision data step"):
        prepare_data_steps((request, request))


def test_n1_rederives_admitted_facts_without_manufacturing_old_evidence():
    from pglast import parse_sql

    (step,) = n1()
    for statement in step.statements:
        assert parse_sql(statement)
    rederive = step.statements[0]
    assert "SELECT DISTINCT sem.data_operation_definition.release_id" in rederive
    assert "JOIN sem.release_finalization" in rederive
    assert "sem.relower_admitted_data_operation_release(" in rederive
    assert "UPDATE ops.data_population SET context_key=" in step.statements[1]
    assert "ddo_population_evidence_scope(ops.data_population.evidence)" in step.statements[1]
    frozen = "\n".join(step.statements)
    for historical in ("data_read", "data_completion_intent", "data_receipt"):
        assert historical not in frozen
    assert len(step.implementation_sha256) == 64
    assert dict(step.libraries).keys() == {"sqlalchemy", "alembic", "pglast"}


def test_nullable_ddl_precedes_native_data_and_final_guards():
    (step,) = n1()
    authoring = guarded_authoring(step)
    source = Column("execution_profile", Text, nullable=False, comment="admitted profile")
    helper = ops.ExecuteSQLOp("SELECT 'native helper installed'")
    upgrade = ops.UpgradeOps(
        [
            OwnedOperationsOp(
                "corpus_sem_publisher", [ops.AddColumnOp("runtime_binding", source, schema="sem")]
            ),
            helper,
        ]
    )
    order_data_steps(upgrade, (step,), authoring)
    first = upgrade.ops[0]
    assert isinstance(first, OwnedOperationsOp)
    staged = first.ops[0]
    assert isinstance(staged, ops.AddColumnOp)
    assert staged.column.nullable is True
    assert source.nullable is False
    assert staged.column.comment == source.comment
    data_index = next(
        index
        for index, operation in enumerate(upgrade.ops)
        if isinstance(operation, OwnedOperationsOp)
        and any(isinstance(child, ops.ExecuteSQLOp) for child in operation.ops)
    )
    assert upgrade.ops.index(helper) < data_index
    temporary_retirements = upgrade.ops[2:data_index]
    retired = set()
    for item in temporary_retirements:
        assert isinstance(item, NativeTransitionOp)
        assert item.before is not None and item.after is None
        retired.add(item.before.identity)
    assert retired == {guard.identity for guard in authoring.desired}
    final = upgrade.ops[data_index + 1]
    assert isinstance(final, OwnedOperationsOp)
    alteration = final.ops[0]
    assert isinstance(alteration, ops.AlterColumnOp)
    assert alteration.modify_nullable is False
    restores = upgrade.ops[data_index + 2 :]
    restored = set()
    for item in restores:
        assert isinstance(item, NativeTransitionOp)
        assert item.before is None
        restored.add(item.after)
    assert restored == set(authoring.desired)


def test_receipt_oracle_foreign_key_survives_nullable_staging_without_reparenting():
    (step,) = prepare_data_steps((data_steps.DataStepRequest(name="pdf_s36_retire_validation"),))
    source = Column(
        "oracle_receipt_id",
        Text,
        ForeignKey("ops.pdf_roundtrip_oracle.oracle_receipt_id"),
        nullable=False,
    )
    original_key = next(iter(source.foreign_keys))
    upgrade = ops.UpgradeOps(
        [
            OwnedOperationsOp(
                "corpus_sem_publisher",
                [ops.AddColumnOp("pdf_build_validation", source, schema="ops")],
            )
        ]
    )
    order_data_steps(upgrade, (step,), guarded_authoring(step))
    first = upgrade.ops[0]
    assert isinstance(first, OwnedOperationsOp)
    staged = first.ops[0]
    assert isinstance(staged, ops.AddColumnOp)
    assert source.nullable is False and staged.column.nullable is True
    assert next(iter(staged.column.foreign_keys)) is not original_key
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output}
    )
    Operations(context).invoke(staged)
    ddl = output.getvalue()
    assert (
        "FOREIGN KEY(oracle_receipt_id) REFERENCES ops.pdf_roundtrip_oracle (oracle_receipt_id)"
        in ddl
    )
    assert "NOT NULL" not in ddl
    assert original_key.parent is source and source.table is None
    assert any(
        isinstance(operation, OwnedOperationsOp)
        and any(
            isinstance(child, ops.AlterColumnOp)
            and child.column_name == "oracle_receipt_id"
            and child.modify_nullable is False
            for child in operation.ops
        )
        for operation in upgrade.ops
    )


def test_only_not_null_is_deferred_when_a_column_also_changes_type():
    (step,) = n1()
    change = ops.AlterColumnOp(
        "runtime_binding",
        "execution_profile",
        schema="sem",
        existing_type=Text(),
        modify_type=Text(),
        modify_nullable=False,
    )
    upgrade = ops.UpgradeOps([OwnedOperationsOp("corpus_sem_publisher", [change])])
    order_data_steps(upgrade, (step,), guarded_authoring(step))
    first = upgrade.ops[0]
    assert isinstance(first, OwnedOperationsOp)
    staged = first.ops[0]
    assert isinstance(staged, ops.AlterColumnOp)
    assert staged.modify_type is change.modify_type
    assert staged.modify_nullable is None
    assert change.modify_nullable is False
    assert any(
        isinstance(operation, OwnedOperationsOp)
        and any(
            isinstance(child, ops.AlterColumnOp) and child.modify_nullable is False
            for child in operation.ops
        )
        for operation in upgrade.ops[1:]
    )


def test_unrelated_successor_has_no_table_specific_data_work():
    operation = ops.ExecuteSQLOp("SELECT 1")
    upgrade = ops.UpgradeOps([operation])
    order_data_steps(upgrade, (), NativeAuthoring(()))
    assert upgrade.ops == [operation]


def test_data_authoring_refuses_absent_guards_and_edited_frozen_sql():
    (step,) = n1()
    with pytest.raises(NativeAuthoringError, match="exact intrinsic guard"):
        order_data_steps(ops.UpgradeOps([]), (step,), NativeAuthoring(()))
    edited = step.model_copy(update={"statements": ("DELETE FROM sem.release",)})
    with pytest.raises(NativeAuthoringError, match="closed builder custody"):
        order_data_steps(ops.UpgradeOps([]), (edited,), guarded_authoring(step))


def test_frozen_upgrade_executes_sql_without_resolving_current_builders(monkeypatch):
    from alembic import op

    from corpus_structure.cli.schema import _native_candidate_python
    from corpus_structure.semantic import alembic_privileges

    (step,) = n1()
    upgrade = ops.UpgradeOps([])
    order_data_steps(upgrade, (step,), guarded_authoring(step))
    source = _native_candidate_python(upgrade)
    assert "schema.data_steps" not in source
    namespace = {}
    exec(compile(source, "frozen_data_candidate.py", "exec"), namespace)
    executed = []
    transitions = []
    monkeypatch.setattr(op, "get_bind", lambda: None)
    monkeypatch.setattr(op, "execute", executed.append)
    monkeypatch.setattr(op, "native_transition", transitions.append, raising=False)
    monkeypatch.setattr(alembic_privileges, "owned_operation", lambda *_: nullcontext())

    def unavailable(*_):
        raise AssertionError("a frozen upgrade resolved a current builder")

    monkeypatch.setattr(data_steps, "prepare_data_steps", unavailable)
    namespace["upgrade"]()
    assert executed == list(step.statements)
    assert len(transitions) == 2 * len(step.guarded_relations)


def test_preview_captures_builder_identity_and_rejects_dependency_drift(
    model_checkout, monkeypatch
):
    root, _ = model_checkout
    preview = prepare_preview(
        root,
        ChangeRequest(
            native_revision="n1", data_steps=(data_steps.DataStepRequest(name="ddo_n1_relower"),)
        ),
        target="working-target",
        authoring_target="working-target",
    )
    assert "revision_data_steps" in preview.effects.native_basis
    assert preview.data_steps == n1()
    check_preview(root, preview)
    edited = preview.model_copy(update={"data_steps": ()})
    with pytest.raises(model.ModelError, match="data-step custody"):
        check_preview(root, edited)
    current_version = data_steps.version
    monkeypatch.setattr(
        data_steps,
        "version",
        lambda name: "changed" if name == "sqlalchemy" else current_version(name),
    )
    with pytest.raises(model.ModelError, match="data-step custody"):
        check_preview(root, preview)


def test_data_builder_uses_proposed_column_identity():
    from sqlalchemy import MetaData

    target = MetaData()
    for table in get_metadata().tables.values():
        table.to_metadata(target)
    target.tables["ops.data_population"].c.context_key.name = "proposed_context_key"

    (step,) = data_steps.prepare_data_steps(
        (data_steps.DataStepRequest(name="ddo_n1_relower"),),
        target=target,
        predecessor=None,
    )

    assert "SET proposed_context_key=" in step.statements[1]
    assert "ops.data_population.proposed_context_key IS NULL" in step.statements[-1]
