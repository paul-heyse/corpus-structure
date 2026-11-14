"""Authored inputs retain their own standing and never fabricate inference episodes."""

import json
from dataclasses import replace

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_compilation import (
    compile_data_operations,
    project_operation_binding,
)
from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
    RootSubject,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_model import MODEL_VERSION, SubjectContext
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.data_operation_support import (
    AuthoredFactSupportReference,
    authored_fact_selection,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.types import PreparationError
from semantic.data_operation_declaration_support import (
    contract,
    declarations,
    resolved_binding,
    source_declaration,
)
from semantic.data_operation_kernel_support import STORAGE, KernelRecipe


def test_authored_origin_is_explicit_and_preserves_exact_fact_identity():
    declaration = contract()
    declaration["roles"][0]["support"].update(
        origins=["authored"], provenance="exact", identity_requirements=["original-source"]
    )
    model = compile_data_operations(declarations=declarations(declaration))
    binding = resolved_binding(model)
    role = binding.roles[0]
    fact = AuthoredFactSupportReference(
        admission_id="authored:one", source_reference="reference:one"
    )
    member = replace(role.members[0], support_episodes=(), support_references=(fact,))
    binding = replace(binding, roles=(replace(role, members=(member,)),))
    first, _ = project_operation_binding(model, binding)
    second, _ = project_operation_binding(
        model,
        replace(
            binding,
            roles=(
                replace(
                    role,
                    members=(
                        replace(
                            member,
                            support_references=(
                                fact.model_copy(update={"source_reference": "reference:two"}),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    assert first.identity != second.identity
    assert member.support_episodes == ()
    declaration["roles"][0]["support"].update(
        origins=["computation"], identity_requirements=["episode"]
    )
    computed = compile_data_operations(declarations=declarations(declaration))
    with pytest.raises(PreparationError, match="origin"):
        project_operation_binding(
            computed, replace(resolved_binding(computed), roles=(replace(role, members=(member,)),))
        )


def _recipe():
    operation = source_declaration()
    operation.update(id="urn:authored:consume", binding={"operator": "scan", "roles": ["authored"]})
    operation["roles"].insert(
        0,
        {
            "name": "authored",
            "kind": "integer",
            "direction": "input",
            "minimum": 1,
            "maximum": 1,
            "collection": "scalar",
            "presence": "required",
            "support": {
                "provenance": "value_substitution",
                "identity_requirements": [],
                "origins": ["authored"],
                "source": "same-original",
                "coverage": "selected-scope",
            },
        },
    )
    return KernelRecipe(
        "authored-fact",
        STORAGE.schema_text,
        canonical_bytes({"version": MODEL_VERSION, "operations": [operation]}),
        STORAGE.manifest_text,
    )


@pytest.mark.parametrize("ddo_kernel", [_recipe()], indirect=True)
def test_native_authored_fact_has_no_computation_and_cannot_be_relabelled(ddo_kernel):
    kernel = ddo_kernel
    context = SubjectContext("ddo-test", "authored:subject", "source:authored", b"{}")
    input_role = kernel.model.operation("urn:authored:consume").roles[0]
    kind = kernel.identities[input_role.kind, "kind"]
    authored = authored_fact_selection(
        "chosen-policy",
        7,
        kind_contract=kind,
        context=context,
        author="operator assertion",
        selection_id="review:seven",
    )
    intent = freeze_demand(
        kernel.model,
        roots=(RootSubject(context.subject, context.original_source, context.analyzed_scope),),
        targets=("urn:authored:consume",),
        inference="authored-test",
        execution_profile="execution:test",
        original_sources=(authored,),
    )
    with kernel.engine.begin() as connection:
        storage = DataOperationStorage(connection)
        demand = DemandPlanner(kernel.model, storage).register(
            intent,
            project=context.project_id,
            release=kernel.prepared.release_id,
            runtime=kernel.preparation.runtime.runtime_id,
        )
        read = storage.invoke("read_demand_result", {"demand_id": demand["demand_id"]})
        assert len(read["original_source_admissions"]) == 1
        fact = read["original_source_admissions"][0]
        assert fact["evidence"]["standing"] == "authored"
        assert fact["evidence"]["author_assertion"] == "operator assertion"
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 0
        (ready,) = DemandPlanner(kernel.model, storage).ready(read, authorization=b"{}")
        member = ready.resolved.roles[0].members[0]
        assert member.support_episodes == ()
        assert tuple(reference.kind for reference in member.support_references) == ("authored",)
        assert json.loads(ready.binding)["support"][0]["kind"] == "authored"
        repeated = storage.invoke(
            "admit_authored_data",
            {
                "demand_id": demand["demand_id"],
                "selection_name": authored.name,
                **authored.record(),
            },
        )
        assert repeated["admission_id"] == fact["admission_id"]
        changed = authored.record()
        changed["reference"]["selection_id"] = "different"
        with pytest.raises(DBAPIError, match="immutable demand"), connection.begin_nested():
            storage.invoke(
                "admit_authored_data",
                {"demand_id": demand["demand_id"], "selection_name": authored.name, **changed},
            )
        wire = json.loads(ready.binding)
        wire["support"][0]["kind"] = "original-source"
        with pytest.raises(DBAPIError), connection.begin_nested():
            connection.execute(
                text(
                    "SELECT ops.ddo_bound_support_available(request,CAST(:support AS jsonb),CAST(:binding AS jsonb)) FROM ops.data_request request WHERE id=:request"
                ),
                {
                    "support": json.dumps(wire["support"]),
                    "binding": json.dumps(wire),
                    "request": json.loads(ready.native)["request_id"],
                },
            )
