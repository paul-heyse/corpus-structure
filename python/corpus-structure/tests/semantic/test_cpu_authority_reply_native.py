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
from evaluate.test_declared_record_policy import fit_basis as fit_basis
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
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import (
    MODEL_VERSION,
    BoundRoleMember,
    ResolvedRoleBinding,
    SubjectContext,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.prepared_sql import prepare_sql
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection
from semantic.test_data_operation_cpu_basis import cpu_basis_connection as cpu_basis_connection


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
    replicate=None)
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
            }
        )
    request = {
        **context.record,
        "release_id": "controlled-input-release",
        "operation_id": "record_policy.fit",
        "recipe": "recipe:controlled-cpu-fit",
        "binding": {"inputs": inputs, "support": [], "parameters": semantic_value({"parameters": {}, "replicate": None})},
    }
    return connection, request


def completion(actual, *, reply=None):
    # This is the private helper's execution-evidence fragment, not an invented
    # native task fence, publication receipt, or NativeExecutionEvidence instance.
    reply = actual.reply if reply is None else reply
    return {
        "inputs": [dict(role=role.role, position=member.position, multiplicity=member.multiplicity,
            product_id=member.product, member_id=member.member)
            for role in actual.binding.roles for member in role.members],
        "support": [],
        "execution_evidence": {
            "cpu_receipts": [reply.execution_receipt.record()],
            "cpu_replies": [reply.content.decode()],
        }
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


@pytest.mark.parametrize("parameters", [{"selected": None}, {"selected": 1},
    {"selected": 1.0}, {"selected": Decimal("1")},
    {"selected": Decimal("0.12345678901234567890123456789")}])
def test_changed_parameters_cannot_reuse_original_worker_reply_with_same_roles_context(
    authority_connection, actual_cpu_fit, parameters
):
    connection, request = authority_connection
    different = deepcopy(request)
    different["binding"]["parameters"] = semantic_value({"parameters": parameters, "replicate": None})
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
    changed = deepcopy(actual_cpu_fit.values["specification"][0])
    changed["threshold"] = 0.75
    # This is a different immutable selected fixture row, not an UPDATE of the
    # original product and never a claimed current computational producer.
    original = actual_cpu_fit.binding.roles[-1].members[0]
    connection.execute(
        table("kb.data_product")
        .insert()
        .values(
            id="product:other-controlled-spec",
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
    ] = "product:other-controlled-spec"
    with pytest.raises(DBAPIError, match="exact native input basis"):
        native_output(connection, different, completion(actual_cpu_fit))
