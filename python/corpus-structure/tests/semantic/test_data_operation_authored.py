"""Authored inputs retain their own standing and never fabricate inference episodes."""

import json
from dataclasses import replace
from typing import cast as typing_cast

import pytest
from native_refusals import native_refusal
from sqlalchemy import text

from corpus_structure.semantic._data_operation_wire import (
    WireAdmitAuthoredDataRequest,
    WireReadDemandResultRequest,
)
from corpus_structure.semantic.data_operation_compilation import (
    compile_data_operations,
    project_operation_binding,
)
from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
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
    operation.update(
        id="urn:authored:consume",
        subject="document",
        subject_definition={
            "id": "document",
            "identifier_kind": "string",
            "scope": "original-source",
        },
        binding={"operator": "scan", "roles": ["authored"]},
    )
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
                "coverage": {"role": "authored", "description": "selected-scope"},
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
    context = SubjectContext(
        "ddo-test", "authored:subject", "source:authored", b"{}", subject_definition="document"
    )
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
    from corpus_structure.semantic.data_operation_service import NativeDemandRequest
    from corpus_structure.serve.interpretation_authoring import author_interpretations

    request = NativeDemandRequest.model_validate(
        {
            "project_id": context.project_id,
            "release_id": kernel.prepared.release_id,
            "runtime_id": kernel.preparation.runtime.runtime_id,
            "roots": [
                {
                    "subject": context.subject,
                    "original_source": context.original_source,
                    "analyzed_scope": {},
                }
            ],
            "targets": ["urn:authored:consume"],
            "execution_profile": "execution:test",
            "inference": "authored-test",
            "original_sources": {authored.name: authored.record()},
        }
    )
    wrong_subject = request.model_dump(mode="python")
    wrong_subject["original_sources"][authored.name]["reference"]["subject_definition"] = (
        "undeclared-subject"
    )
    with pytest.raises(ValueError, match="resolved subject definition"):
        author_interpretations(
            kernel.engine,
            kernel.prepared,
            request=NativeDemandRequest.model_validate(wrong_subject),
        )
    admitted = author_interpretations(kernel.engine, kernel.prepared, request=request)
    assert admitted["standing"] == "authored" and not admitted["selected"]
    assert "run_id" not in admitted and "cut_id" not in admitted
    with kernel.engine.begin() as connection:
        storage = DataOperationStorage(connection)
        demand = {"demand_id": admitted["demand_id"]}
        read = storage.read_demand_result(
            typing_cast(WireReadDemandResultRequest, {"demand_id": demand["demand_id"]})
        )
        assert len(read["original_source_admissions"]) == 1
        fact = read["original_source_admissions"][0]
        assert isinstance(fact["evidence"], dict)
        assert fact["evidence"]["standing"] == "authored"
        assert fact["evidence"]["author_assertion"] == "operator assertion"
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 0
    with kernel.engine.begin() as connection:
        storage = DataOperationStorage(connection)
        (ready,) = DemandPlanner(kernel.model, storage).ready(read, authorization=b"{}")
        member = ready.resolved.roles[0].members[0]
        assert member.support_episodes == ()
        assert tuple(reference.kind for reference in member.support_references) == ("authored",)
        assert json.loads(ready.binding)["support"][0]["kind"] == "authored"
        repeated = storage.admit_authored_data(
            typing_cast(
                WireAdmitAuthoredDataRequest,
                {
                    "demand_id": demand["demand_id"],
                    "selection_name": authored.name,
                    **authored.record(),
                },
            )
        )
        assert repeated["admission_id"] == fact["admission_id"]
        changed = authored.record()
        changed["reference"]["selection_id"] = "different"
        with (
            native_refusal(
                "P0001", message="original source selection differs from immutable demand"
            ),
            connection.begin_nested(),
        ):
            storage.admit_authored_data(
                typing_cast(
                    WireAdmitAuthoredDataRequest,
                    {"demand_id": demand["demand_id"], "selection_name": authored.name, **changed},
                )
            )
        wire = json.loads(ready.binding)
        support_available = text(
            "SELECT ops.ddo_bound_support_available(request,CAST(:support AS jsonb),CAST(:binding AS jsonb)) FROM ops.data_request request WHERE id=:request"
        )
        arguments = {
            "support": json.dumps(wire["support"]),
            "binding": json.dumps(wire),
            "request": json.loads(ready.native)["request_id"],
        }
        assert connection.scalar(support_available, arguments) is True
        assert connection.scalar(text("SELECT count(*) FROM ops.original_source_admission")) == 1
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 0
        wire["support"][0]["kind"] = "original-source"
        with (
            native_refusal(
                "P0001", message="original support differs from selected factual input custody"
            ),
            connection.begin_nested(),
        ):
            connection.execute(
                support_available,
                {
                    **arguments,
                    "support": json.dumps(wire["support"]),
                    "binding": json.dumps(wire),
                },
            )
        assert connection.scalar(support_available, arguments) is True


@pytest.mark.parametrize("ddo_kernel", [_recipe()], indirect=True)
def test_native_product_scoped_authored_fact_preserves_context_and_current_trust(ddo_kernel):
    from sqlalchemy import insert

    from corpus_structure.semantic._data_operation_wire import WireRevokeDataSupportRequest
    from corpus_structure.semantic.data_operation_demands import RootSubject, freeze_demand
    from corpus_structure.semantic.metadata import table

    kernel = ddo_kernel
    context = SubjectContext(
        "ddo-test",
        "authored:subject",
        "source:authored",
        b'{"section":"chosen"}',
        subject_definition="document",
    )
    input_role = kernel.model.operation("urn:authored:consume").roles[0]
    authored = authored_fact_selection(
        "scoped-policy",
        7,
        kind_contract=kernel.identities[input_role.kind, "kind"],
        context=context,
        author="scoped assertion",
        selection_id="review:scoped-seven",
    )
    roots = (
        RootSubject(context.subject, context.original_source, context.analyzed_scope),
        RootSubject("authored:other", context.original_source, context.analyzed_scope),
        RootSubject(context.subject, "source:other", context.analyzed_scope),
        RootSubject(context.subject, context.original_source, b'{"section":"other"}'),
    )
    with kernel.engine.begin() as connection:
        storage = DataOperationStorage(connection)
        planner = DemandPlanner(kernel.model, storage)
        intent = freeze_demand(
            kernel.model,
            roots=roots,
            targets=("urn:authored:consume",),
            inference="authored:scoped-original",
            execution_profile=kernel.recipe.execution_profile,
            original_sources=(authored,),
        )
        demand = planner.register(
            intent,
            project=context.project_id,
            release=kernel.prepared.release_id,
            runtime=kernel.preparation.runtime.runtime_id,
        )
    with kernel.engine.begin() as connection:
        storage = DataOperationStorage(connection)
        unscoped = storage.read_demand_result(
            typing_cast(WireReadDemandResultRequest, {"demand_id": demand["demand_id"]})
        )
        assert len(unscoped["obligations"]) == 4
        (fact,) = unscoped["original_source_admissions"]
        request = {
            "demand_id": demand["demand_id"],
            "view": "support",
            "limit": 1000,
            "scope": {"product_ids": [fact["product_id"]]},
        }
        scoped = storage.read_demand_result(typing_cast(WireReadDemandResultRequest, request))
        assert [row["admission_id"] for row in scoped["original_source_admissions"]] == [
            fact["admission_id"]
        ]
        assert [
            (row["subject"], row["original_source"], row["analyzed_scope"])
            for row in scoped["obligations"]
        ] == [(context.subject, context.original_source, {"section": "chosen"})]
        assert scoped["uses"] == []
        assert scoped["obligations"][0]["fate"] == "waiting"
        assert scoped["obligations"][0]["historical_fate"] is None
        assert scoped["obligations"][0]["request_id"] is None
        assert scoped["support_page"] is not None and scoped["support_page"]["complete"]
        records = scoped["support_page"]["records"]
        assert [
            row["record"]["id"]
            for row in records
            if row["relation"] == "ops.original_source_admission"
        ] == [fact["admission_id"]]
        assert [row["record"]["id"] for row in records if row["relation"] == "kb.data_product"] == [
            fact["product_id"]
        ]
        assert not {"ops.demand_use", "ops.data_derivation"}.intersection(
            row["relation"] for row in records
        )
        for scope in (
            {"product_ids": ["product:absent"]},
            {"product_ids": [fact["product_id"]], "subject": "authored:other"},
            {"product_ids": [fact["product_id"]], "original_source": "source:other"},
        ):
            absent = storage.read_demand_result(
                typing_cast(WireReadDemandResultRequest, {**request, "scope": scope})
            )
            assert absent["obligations"] == []
            assert absent["original_source_admissions"] == []
            assert absent["support_page"] is not None
            assert absent["support_page"]["records"] == []
    # Register unrelated demands before acquiring their independent read fences.
    for project in (context.project_id, "ddo-other"):
        with kernel.engine.begin() as connection:
            storage = DataOperationStorage(connection)
            planner = DemandPlanner(kernel.model, storage)
            if project != context.project_id:
                connection.execute(insert(table("data.project")).values(project_id=project))
            unrelated = planner.register(
                freeze_demand(
                    kernel.model,
                    roots=roots,
                    targets=("urn:authored:consume",),
                    inference="authored:other-demand",
                    execution_profile=kernel.recipe.execution_profile,
                ),
                project=project,
                release=kernel.prepared.release_id,
                runtime=kernel.preparation.runtime.runtime_id,
            )
        with kernel.engine.begin() as connection:
            storage = DataOperationStorage(connection)
            absent = storage.read_demand_result(
                typing_cast(
                    WireReadDemandResultRequest,
                    {**request, "demand_id": unrelated["demand_id"]},
                )
            )
            assert absent["obligations"] == []
            assert absent["original_source_admissions"] == []
            assert absent["support_page"] is not None
            assert absent["support_page"]["records"] == []
    with kernel.engine.begin() as connection:
        storage = DataOperationStorage(connection)
        storage.revoke_data_support(
            typing_cast(
                WireRevokeDataSupportRequest,
                {
                    "project_id": context.project_id,
                    "original_source": context.original_source,
                    "selector_kind": "original-admission",
                    "selector": fact["admission_id"],
                    "reason": "authored assertion withdrawn",
                },
            )
        )
    with (
        native_refusal("23514", message="read trust changed; reacquire demand read"),
        kernel.engine.begin() as connection,
    ):
        DataOperationStorage(connection).read_demand_result(
            typing_cast(WireReadDemandResultRequest, {**request, "read_id": scoped["read_id"]})
        )
    with kernel.engine.begin() as connection:
        storage = DataOperationStorage(connection)
        current = storage.read_demand_result(typing_cast(WireReadDemandResultRequest, request))
        assert current["original_source_admissions"] == []
        assert len(current["obligations"]) == 1
        assert current["uses"] == []
        assert current["support_page"] is not None
        assert [
            row["record"]["id"]
            for row in current["support_page"]["records"]
            if row["relation"] == "ops.original_source_admission"
        ] == [fact["admission_id"]]
        assert connection.scalar(text("SELECT count(*) FROM ops.data_request")) == 0
        assert connection.scalar(text("SELECT count(*) FROM ops.demand_use")) == 0
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 0
