"""Actual CPU results and private PostgreSQL correspondence, not admission proofs.

The numerical frames and stored input rows are controlled scalar fixtures. They
have no invented producing episode/publication, and these helpers do not make
those values a native capability or a protected producer. Only the CPU worker's
execution receipt and original reply below are actual physical execution evidence.
"""

import inspect
import json
import os
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
from evaluate.declared_record_policy_test_support import fit_basis as fit_basis
from pglast import ast
from sqlalchemy import cast, literal, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.core.work import drive_prepared_work
from corpus_structure.evaluate.declared_record_policy import (
    execute_fit_kernel,
    record_policy_operation_sources,
)
from corpus_structure.semantic.cpu_execution import CPUExecutionScope, CPUReply
from corpus_structure.semantic.data_operation_bindings import BindingResult
from corpus_structure.semantic.data_operation_cpu import PythonCPUDescriptor, plan_cpu_call
from corpus_structure.semantic.data_operation_cpu_basis import (
    cpu_authority_value,
    cpu_input_basis_from_binding,
    cpu_input_basis_native_sql,
)
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import (
    MODEL_VERSION,
    BoundRoleMember,
    ResolvedRoleBinding,
    SubjectContext,
)
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.prepared_sql import prepare_sql
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection
from semantic.cpu_basis_support import (
    cpu_basis_connection as cpu_basis_connection,
)
from semantic.cpu_basis_support import (
    cpu_basis_engine as cpu_basis_engine,
)


@dataclass(frozen=True)
class ActualCPUFit:
    reply: CPUReply
    scalar_reply: CPUReply
    basis: list
    binding: BindingResult
    values: dict
    packet_digest: str


def exact_scalar_kernel(input_basis: list, *, check_active) -> dict:
    """Controlled codec result only; this declares no production operation."""
    from corpus_structure.semantic.data_operation_cpu_basis import cpu_authority_reply

    check_active()
    return cpu_authority_reply(
        input_basis,
        {
            "negative_zero": -0.0,
            "decimal": Decimal("0.123456789123456789"),
        },
    )


@pytest.fixture(scope="module")
def actual_cpu_fit(fit_basis):
    from evaluation_record_alignment_support import prepared

    first, second, specification = fit_basis
    values = {
        "feature_grade": (first.model_dump(mode="python"),),
        "calibration_grade": (second.model_dump(mode="python"),),
        "specification": (specification.model_dump(mode="python"),),
    }
    context = SubjectContext(
        "project:one",
        "knowledge:controlled-inputs",
        None,
        json_bytes({"fraction": Decimal("0.123456789123456789")}),
        subject_definition="knowledge-universe",
    )
    roles = tuple(
        ResolvedRoleBinding(
            name,
            "present",
            (
                BoundRoleMember(
                    product="product:controlled-" + name,
                    kind_contract="kind:controlled-" + name,
                    subject=context.subject,
                    original_source=None,
                    analyzed_scope=context.analyzed_scope,
                    coverage=b"{}",
                    subject_definition=context.subject_definition,
                    support_episodes=(),
                    support_evidence=b"{}",
                    position=0,
                    multiplicity=1,
                    support_references=(),
                ),
            ),
        )
        for name in values
    )
    binding = BindingResult(
        operation="record_policy.fit",
        subject=context.subject,
        roles=roles,
        status="ready",
        reasons=(),
        parameters=canonical_bytes(semantic_value({})),
        choices=b"{}",
        model_version=MODEL_VERSION,
        definition="controlled-input-definition",
        eligibility="controlled-input-eligibility",
        admission_evidence=(),
        subject_context=context,
        replicate=None,
    )
    basis = cpu_input_basis_from_binding("recipe:controlled-cpu-fit", binding, values)
    sources = record_policy_operation_sources()
    descriptor = PythonCPUDescriptor(
        tuple((source.module, source.filename, source.content) for source in sources.sources),
        execute_fit_kernel.__module__ + "." + execute_fit_kernel.__qualname__,
        (),
        verification="prepared-kernel",
        control_parameter="check_active",
    )
    signature = inspect.signature(execute_fit_kernel, eval_str=True)
    bound = signature.bind(input_basis=basis, check_active=lambda: None)
    packet_digest = sha256(descriptor.packet(bound.arguments, signature)).hexdigest()
    execution = CPUExecutionScope(
        prepared(),
        CharacterizationExecutionPolicy(workers=1, max_submissions=1),
        retain_schema=False,
    )
    try:
        reply = drive_prepared_work(
            plan_cpu_call(
                descriptor,
                bound,
                signature,
                verify=lambda: None,
                execution_owner=SimpleNamespace(cpu=execution, reservation=None),
                check_active=lambda: None,
            ),
            lambda: None,
        )
        path = Path(__file__).resolve()
        scalar_sources = PythonSourceCollection(
            (
                PythonSource(
                    "semantic.test_cpu_authority_reply_native",
                    path.read_bytes(),
                    str(path),
                ),
            )
        )
        scalar_descriptor = PythonCPUDescriptor(
            tuple(
                (source.module, source.filename, source.content)
                for source in scalar_sources.sources
            ),
            "semantic.test_cpu_authority_reply_native.exact_scalar_kernel",
            (),
            verification="prepared-kernel",
            control_parameter="check_active",
        )
        scalar_signature = inspect.signature(exact_scalar_kernel, eval_str=True)
        scalar_bound = scalar_signature.bind(input_basis=basis, check_active=lambda: None)
        scalar_reply = drive_prepared_work(
            plan_cpu_call(
                scalar_descriptor,
                scalar_bound,
                scalar_signature,
                verify=lambda: None,
                execution_owner=SimpleNamespace(cpu=execution, reservation=None),
                check_active=lambda: None,
            ),
            lambda: None,
        )
    finally:
        execution.close()
    assert execution.budget.used_bytes == 0
    return ActualCPUFit(reply, scalar_reply, basis, binding, values, packet_digest)


@pytest.fixture
def authority_connection(cpu_basis_connection, actual_cpu_fit):
    from corpus_structure.semantic.data_operation_storage import native_protocol_sources, native_sql

    connection = cpu_basis_connection
    for source, names in (
        (native_sql(native_protocol_sources()), {"ddo_digest", "ddo_cpu_reply_value"}),
        (cpu_input_basis_native_sql(), {"ddo_cpu_reply_output"}),
    ):
        parsed = prepare_sql(source, source="actual-cpu-reply-private-control")
        for index, statement in enumerate(parsed.statements):
            node = statement.stmt
            if (
                isinstance(node, ast.CreateFunctionStmt)
                and node.funcname
                and node.funcname[-1].sval in names
            ):
                connection.exec_driver_sql(
                    parsed.excerpt(index), execution_options={"no_parameters": True}
                )
    context = actual_cpu_fit.binding.subject_context
    assert context is not None
    connection.execute(
        table("sem.data_operation_definition")
        .insert()
        .values(
            release_id="controlled-input-release",
            operation_id="record_policy.fit",
            subject_definition=context.subject_definition,
            recipe="recipe:controlled-cpu-fit",
            profile="derivation",
            implementation_revision="controlled-input-definition",
            input_roles=[],
            output_roles=[],
            support_contract={"capabilities": {"forms": ["scalar"]}},
            binding_expression={"operator": "all", "children": []},
            definition_identity="definition:controlled",
            eligibility_identity="eligibility:controlled",
            quantified=False,
            dependencies=[],
        )
    )
    inputs = []
    for role in actual_cpu_fit.binding.roles:
        member = role.members[0]
        body = actual_cpu_fit.values[role.role][0]
        meaning = semantic_value(body)
        connection.execute(
            table("kb.data_product")
            .insert()
            .values(
                id=member.product,
                kind_contract=member.kind_contract,
                project_id=context.project_id,
                subject=member.subject,
                subject_definition=member.subject_definition,
                original_source=None,
                analyzed_scope=cast(literal(member.analyzed_scope.decode()), JSONB),
                canonical_body=meaning,
                body_digest=sha256(canonical_bytes(meaning)).hexdigest(),
            )
        )
        inputs.append(
            {
                "role": role.role,
                "product_id": member.product,
                "member_id": None,
                "position": member.position,
                "multiplicity": member.multiplicity,
                "support_derivation_ids": sorted(member.support_episodes),
                "producer_output": None,
            }
        )
    request = {
        **context.record,
        "release_id": "controlled-input-release",
        "operation_id": "record_policy.fit",
        "recipe": "recipe:controlled-cpu-fit",
        "binding": {
            "inputs": inputs,
            "support": [],
            "parameters": semantic_value({"parameters": {}, "replicate": None}),
        },
    }
    return connection, request


def completion(actual, *, reply=None):
    # This is the private helper's execution-evidence fragment, not an invented
    # native task fence, publication receipt, or NativeExecutionEvidence instance.
    reply = actual.reply if reply is None else reply
    return {
        "inputs": [
            dict(
                role=role.role,
                position=member.position,
                multiplicity=member.multiplicity,
                product_id=member.product,
                member_id=member.member,
                support_derivation_ids=sorted(member.support_episodes),
                producer_output=None,
            )
            for role in actual.binding.roles
            for member in role.members
        ],
        "support": [],
        "execution_evidence": {
            "cpu_receipts": [reply.execution_receipt.record()],
            "cpu_replies": [reply.content.decode()],
        },
    }


def native_output(connection, request, evidence):
    return connection.scalar(
        text(
            "SELECT ops.ddo_cpu_reply_output(jsonb_populate_record(NULL::ops.data_request,CAST(:request AS jsonb)),CAST(:completion AS jsonb))"
        ),
        {"request": json_bytes(request).decode(), "completion": json.dumps(evidence)},
    )


def test_actual_numerical_worker_reply_matches_original_digest_and_exact_native_basis(
    authority_connection, actual_cpu_fit
):
    connection, request = authority_connection
    receipt = actual_cpu_fit.reply.execution_receipt
    assert receipt.pid != os.getpid() and receipt.main_thread is True
    assert receipt.request_digest == actual_cpu_fit.packet_digest
    assert receipt.result_digest == sha256(actual_cpu_fit.reply.content).hexdigest()
    value = cpu_authority_value(actual_cpu_fit.reply.content, expected_basis=actual_cpu_fit.basis)
    assert value["fitted"] is not None
    assert value["fitted"]["instance"]["threshold"] == 0.99
    native = native_output(connection, request, completion(actual_cpu_fit))
    assert native == semantic_value(value)
    basis = connection.scalar(
        text(
            "SELECT ops.ddo_cpu_input_basis(jsonb_populate_record(NULL::ops.data_request,CAST(:request AS jsonb)))"
        ),
        {"request": json_bytes(request).decode()},
    )
    assert basis == actual_cpu_fit.basis
    scope = dict(dict(basis[1])["context"][1])["analyzed_scope"]
    assert scope == ["mapping", [["fraction", ["decimal", "0.123456789123456789"]]]]


@pytest.mark.parametrize(
    "parameters",
    [
        {"selected": None},
        {"selected": 1},
        {"selected": 1.0},
        {"selected": Decimal("1")},
        {"selected": Decimal("0.12345678901234567890123456789")},
    ],
)
def test_changed_parameters_cannot_reuse_original_worker_reply_with_same_roles_context(
    authority_connection, actual_cpu_fit, parameters
):
    connection, request = authority_connection
    different = deepcopy(request)
    different["binding"]["parameters"] = semantic_value(
        {"parameters": parameters, "replicate": None}
    )
    with pytest.raises(DBAPIError, match="exact native input basis"), connection.begin_nested():
        native_output(connection, different, completion(actual_cpu_fit))


def test_actual_scalar_worker_preserves_signed_zero_and_decimal_through_native_reply(
    authority_connection, actual_cpu_fit
):
    connection, request = authority_connection
    reply = actual_cpu_fit.scalar_reply
    assert reply.pid != os.getpid() and reply.main_thread is True
    assert reply.execution_receipt.result_digest == sha256(reply.content).hexdigest()
    assert native_output(connection, request, completion(actual_cpu_fit, reply=reply)) == [
        "mapping",
        [
            ["decimal", ["decimal", "0.123456789123456789"]],
            ["negative_zero", ["float", "-0x0.0p+0"]],
        ],
    ]


def test_preserved_real_receipt_refuses_substituted_raw_reply(authority_connection, actual_cpu_fit):
    connection, request = authority_connection
    changed = completion(actual_cpu_fit)
    raw = json.loads(changed["execution_evidence"]["cpu_replies"][0])
    raw["output"] = semantic_value({"fitted": None, "diagnostics": []})
    changed["execution_evidence"]["cpu_replies"][0] = canonical_bytes(raw).decode()
    with pytest.raises(DBAPIError, match="original execution receipt"):
        native_output(connection, request, changed)


def test_other_stored_input_basis_cannot_reuse_real_worker_reply(
    authority_connection, actual_cpu_fit
):
    connection, request = authority_connection
    original_specification = actual_cpu_fit.values["specification"][0]
    changed = deepcopy(original_specification)
    changed["threshold"] = 0.75
    assert original_specification["threshold"] == 0.99
    assert semantic_value(changed) != semantic_value(original_specification)
    # This is a different immutable selected fixture row, not an UPDATE of the
    # original product and never a claimed current computational producer.
    original = next(
        role.members[0] for role in actual_cpu_fit.binding.roles if role.role == "specification"
    )
    replacement_product = "product:other-controlled-spec"
    assert replacement_product != original.product
    connection.execute(
        table("kb.data_product")
        .insert()
        .values(
            id=replacement_product,
            kind_contract=original.kind_contract,
            project_id="project:one",
            subject=original.subject,
            subject_definition=original.subject_definition,
            original_source=None,
            analyzed_scope=cast(literal(original.analyzed_scope.decode()), JSONB),
            canonical_body=semantic_value(changed),
            body_digest=sha256(canonical_bytes(semantic_value(changed))).hexdigest(),
        )
    )
    different = deepcopy(request)
    next(row for row in different["binding"]["inputs"] if row["role"] == "specification")[
        "product_id"
    ] = replacement_product
    changed_completion = completion(actual_cpu_fit)
    # The helper authenticates original completion pins for historical reads,
    # rather than substituting a request's later live selection.
    next(row for row in changed_completion["inputs"] if row["role"] == "specification")[
        "product_id"
    ] = replacement_product
    with pytest.raises(DBAPIError, match="exact native input basis"):
        native_output(connection, different, changed_completion)


@pytest.fixture
def original_cpu_connection(cpu_basis_connection):
    """Private controlled runtime/decoder seams; these do not grant native admission."""
    from sqlalchemy import Column, MetaData, Table
    from sqlalchemy.schema import CreateTable

    connection = cpu_basis_connection
    scratch = MetaData()
    for name in ("ops.data_completion_intent", "ops.task", "sem.runtime_binding"):
        source = table(name)
        relation = Table(
            source.name,
            scratch,
            *(Column(c.name, c.type) for c in source.columns),
            schema=source.schema,
        )
        connection.execute(CreateTable(relation))
    connection.exec_driver_sql("""
        CREATE FUNCTION sem.require_runtime_binding(text,text) RETURNS void LANGUAGE plpgsql AS $$
        BEGIN IF $1 <> 'release:original' OR $2 <> 'runtime:submitted' THEN
          RAISE EXCEPTION 'controlled runtime admission refused' USING ERRCODE='23514';
        END IF; END $$;
        CREATE FUNCTION ops.ddo_require_provider_profile(text,text,text) RETURNS void LANGUAGE plpgsql AS $$
        BEGIN IF $1 <> 'release:original' OR $2 <> 'operation:original' OR $3 <> 'runtime:submitted' THEN
          RAISE EXCEPTION 'controlled provider admission refused' USING ERRCODE='23514';
        END IF; END $$;
        CREATE OR REPLACE FUNCTION ops.ddo_cpu_reply_value(completion jsonb)
        RETURNS jsonb LANGUAGE sql AS $$ SELECT completion->'controlled_reply' $$;
    """)
    source = prepare_sql(cpu_input_basis_native_sql(), source="private-original-producer-control")
    for index, statement in enumerate(source.statements):
        node = statement.stmt
        if (
            isinstance(node, ast.CreateFunctionStmt)
            and node.funcname
            and node.funcname[-1].sval == "ddo_cpu_original_producer"
        ):
            connection.exec_driver_sql(
                source.excerpt(index), execution_options={"no_parameters": True}
            )
    context = SubjectContext(
        "project:original", "subject:original", None, b"{}", subject_definition="subject:knowledge"
    )
    request = {
        **context.record,
        "id": "request:original",
        "generation": 2,
        "live_task_id": 42,
        "release_id": "release:original",
        "operation_id": "operation:original",
        "recipe": "recipe:original",
        "runtime_id": "runtime:creation-is-provenance",
        "replicate": None,
        "binding": {
            "inputs": [],
            "support": [],
            "execution_profile": "profile:original",
            "parameters": semantic_value({"parameters": {}, "replicate": None}),
        },
    }
    connection.execute(
        table("sem.data_operation_definition")
        .insert()
        .values(
            release_id=request["release_id"],
            operation_id=request["operation_id"],
            subject_definition=context.subject_definition,
            recipe=request["recipe"],
            profile="derivation",
            implementation_revision="implementation:original",
            input_roles=[],
            output_roles=[],
            support_contract={"capabilities": {"forms": ["batch"]}},
            binding_expression={"operator": "all", "children": []},
            definition_identity="definition:original",
            eligibility_identity="eligibility:original",
            quantified=False,
            dependencies=[],
        )
    )
    connection.execute(
        scratch.tables["ops.task"]
        .insert()
        .values(
            id=42,
            data_request_id=request["id"],
            data_generation=2,
            status="running",
            attempt=3,
            claimed_by="holder:original",
            lease_until=text("clock_timestamp()+interval '1 hour'"),
        )
    )
    connection.execute(
        scratch.tables["sem.runtime_binding"]
        .insert()
        .values(
            release_id=request["release_id"],
            runtime_id="runtime:submitted",
            manifest_bytes=b'{"execution_profile":"profile:original"}',
        )
    )
    fence = dict(
        request_id=request["id"], generation=2, task_id=42, attempt=3, holder="holder:original"
    )
    payload = {
        "inputs": [],
        "support": [],
        "execution_evidence": {**fence, "runtime_id": "runtime:submitted"},
    }
    from corpus_structure.semantic.data_operation_cpu_basis import cpu_input_basis

    recipe = request["recipe"]
    assert isinstance(recipe, str)
    basis = cpu_input_basis(
        recipe,
        context,
        (),
        parameters=canonical_bytes(semantic_value({})),
        replicate=None,
    )
    return connection, request, payload, fence, basis, scratch


def test_original_cpu_producer_keeps_live_lease_and_immutable_replay_authority(
    original_cpu_connection,
):
    connection, request, payload, fence, _, scratch = original_cpu_connection

    def producer(r, completion):
        return connection.scalar(
            text(
                "SELECT ops.ddo_cpu_original_producer(jsonb_populate_record(NULL::ops.data_request,CAST(:r AS jsonb)),CAST(:c AS jsonb))"
            ),
            {"r": json_bytes(r).decode(), "c": json_bytes(completion).decode()},
        )

    assert producer(request, payload) == fence
    changed = deepcopy(payload)
    changed["execution_evidence"]["runtime_id"] = "runtime:foreign"
    with (
        pytest.raises(DBAPIError, match="controlled runtime admission refused"),
        connection.begin_nested(),
    ):
        producer(request, changed)
    runtime = scratch.tables["sem.runtime_binding"]
    with connection.begin_nested() as savepoint:
        connection.execute(runtime.update().values(manifest_bytes=b'{"execution_profile":"other"}'))
        with (
            pytest.raises(DBAPIError, match="runtime execution profile differs"),
            connection.begin_nested(),
        ):
            producer(request, payload)
        savepoint.rollback()
    task = scratch.tables["ops.task"]
    connection.execute(
        task.update().values(lease_until=text("clock_timestamp()-interval '1 second'"))
    )
    with pytest.raises(DBAPIError) as failure, connection.begin_nested():
        producer(request, payload)
    assert getattr(failure.value.orig, "sqlstate", None) == "P0002"
    digest = connection.scalar(
        text("SELECT ops.ddo_digest(CAST(:p AS jsonb))"), {"p": json_bytes(payload).decode()}
    )
    connection.execute(
        scratch.tables["ops.data_completion_intent"]
        .insert()
        .values(
            request_id=request["id"],
            generation=2,
            payload=payload,
            payload_digest=digest,
            runtime_id="runtime:submitted",
            producer_task_id=42,
            producer_attempt=3,
            producer_holder="holder:original",
        )
    )
    # Retained evidence authenticates the original owner, independently of the current lease/runtime.
    replay_request = {**request, "generation": 3, "live_task_id": 99, "runtime_id": "runtime:later"}
    assert producer(replay_request, payload) == fence
    changed = deepcopy(payload)
    changed["execution_evidence"]["attempt"] = 4
    with (
        pytest.raises(DBAPIError, match="immutable original intent digest/payload"),
        connection.begin_nested(),
    ):
        producer(request, changed)
    changed = deepcopy(payload)
    changed["execution_evidence"]["generation"] = 1
    with (
        pytest.raises(DBAPIError, match="immutable original retained intent"),
        connection.begin_nested(),
    ):
        producer(request, changed)


def test_native_batch_scatter_keeps_exact_member_fence_basis_and_output(original_cpu_connection):
    from corpus_structure.semantic.data_operation_cpu_basis import cpu_authority_batch_reply

    connection, request, payload, fence, basis, _ = original_cpu_connection
    logical_members = (
        {
            "member": "other",
            "producer": {**fence, "request_id": "request:other", "task_id": 43},
            "input_basis": basis,
        },
        {"member": "selected", "producer": fence, "input_basis": basis},
    )
    reply = cpu_authority_batch_reply(
        logical_members, ({"value": 0}, {"value": Decimal("0.125"), "zero": -0.0})
    )
    payload = {**payload, "controlled_reply": reply}
    assert native_output(connection, request, payload) == semantic_value(
        {"value": Decimal("0.125"), "zero": -0.0}
    )
    changes = []
    duplicate_member = deepcopy(reply)
    duplicate_member["members"][0]["member"] = "selected"
    changes.append((duplicate_member, "repeats a logical member"))
    duplicate_producer = deepcopy(reply)
    duplicate_producer["members"][0]["producer"] = fence
    changes.append((duplicate_producer, "repeats a logical member"))
    different_basis = deepcopy(reply)
    different_basis["members"][1]["input_basis_digest"] = "0" * 64
    changes.append((different_basis, "original producer fence/exact input basis"))
    extra_field = deepcopy(reply)
    extra_field["members"][1]["extra"] = None
    changes.append((extra_field, "lacks its exact original producer/basis/output"))
    for changed, message in changes:
        with pytest.raises(DBAPIError, match=message) as failure, connection.begin_nested():
            native_output(connection, request, {**payload, "controlled_reply": changed})
        assert getattr(failure.value.orig, "sqlstate", None) == "23514"
