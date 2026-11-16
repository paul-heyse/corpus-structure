"""Batch correspondence protocol examples; no native execution evidence is invented."""

from copy import deepcopy
from decimal import Decimal

import pytest

from corpus_structure.semantic.data_operation_cpu_basis import (
    cpu_authority_batch_reply,
    cpu_authority_batch_values,
    cpu_authority_reply,
    cpu_authority_value,
    cpu_input_basis,
)
from corpus_structure.semantic.data_operation_identity import decode_semantic_value, semantic_value
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.identity import canonical_bytes


def members():
    return tuple(
        dict(
            member="logical:" + name,
            producer=dict(
                request_id="request:" + name,
                generation=2,
                task_id=task,
                attempt=3,
                holder="original-holder",
            ),
            input_basis=cpu_input_basis(
                "same-recipe",
                SubjectContext(
                    "project", name, None, b"{}", subject_definition="knowledge-universe"
                ),
                (),
                parameters=canonical_bytes(semantic_value({"selection": name})),
                replicate=None,
            ),
        )
        for name, task in (("one", 11), ("two", 12))
    )


def test_batch_reply_retains_order_original_fences_and_exact_values():
    population = members()
    outputs = ({"value": -0.0}, {"value": Decimal("0.1234567890123456789")})
    reply = cpu_authority_batch_reply(population, outputs)
    assert [row["member"] for row in reply["members"]] == ["logical:one", "logical:two"]
    assert [row["producer"]["task_id"] for row in reply["members"]] == [11, 12]
    values = cpu_authority_batch_values(canonical_bytes(reply), expected_members=population)
    assert values[0]["value"].hex() == "-0x0.0p+0"
    assert values[1]["value"] == Decimal("0.1234567890123456789")


@pytest.mark.parametrize(
    "change",
    ["swap", "omit", "duplicate", "request", "generation", "task", "attempt", "holder", "basis"],
)
def test_batch_scatter_refuses_changed_order_membership_and_original_producer_fences(change):
    population = members()
    reply = cpu_authority_batch_reply(population, ({"result": 1}, {"result": 2}))
    if change == "swap":
        reply["members"].reverse()
    elif change == "omit":
        reply["members"].pop()
    elif change == "duplicate":
        reply["members"][1] = deepcopy(reply["members"][0])
    elif change == "request":
        reply["members"][0]["producer"]["request_id"] = "request:other"
    elif change == "generation":
        reply["members"][0]["producer"]["generation"] = 3
    elif change == "task":
        reply["members"][0]["producer"]["task_id"] = 22
    elif change == "attempt":
        reply["members"][0]["producer"]["attempt"] = 4
    elif change == "holder":
        reply["members"][0]["producer"]["holder"] = "adopting-holder"
    else:
        reply["members"][0]["input_basis_digest"] = "0" * 64
    with pytest.raises(ValueError, match="CPU batch reply"):
        cpu_authority_batch_values(canonical_bytes(reply), expected_members=population)


def test_batch_refuses_repeated_original_request_generations_and_v1_basis():
    population = list(members())
    population[1]["producer"] = dict(population[0]["producer"])
    with pytest.raises(ValueError, match="repeats"):
        cpu_authority_batch_reply(population, (1, 2))
    population = members()
    old = decode_semantic_value(population[0]["input_basis"])
    old["version"] = "cpu-input-basis-1"
    with pytest.raises(ValueError, match="current exact input basis"):
        cpu_authority_reply(semantic_value(old), 1)
    scalar = cpu_authority_reply(population[0]["input_basis"], 1)
    scalar["version"] = "cpu-authority-reply-1"
    with pytest.raises(ValueError, match="input basis"):
        cpu_authority_value(canonical_bytes(scalar), expected_basis=population[0]["input_basis"])


def test_prepared_batch_uses_one_actual_owned_cpu_reply_for_all_controlled_members():
    """Controlled logical headers are inputs here, not native claim evidence."""
    from dataclasses import asdict
    from types import SimpleNamespace

    from corpus_structure.core.work import drive_prepared_work
    from corpus_structure.semantic.data_operation_admission import PreparedCapabilityIdentity
    from corpus_structure.semantic.data_operation_bindings import BindingResult
    from corpus_structure.semantic.data_operation_compilation import compile_data_operations
    from corpus_structure.semantic.data_operation_model import (
        MODEL_VERSION,
        BoundRoleMember,
        ResolvedRoleBinding,
    )
    from corpus_structure.semantic.data_operation_ports import (
        PythonBatchMember,
        PythonRoleValue,
        python_port_identity,
    )
    from semantic.data_operation_port_support import scope
    from semantic.prepared_batch_control import controlled_sources, resolve_controlled_port

    sources = controlled_sources()
    model = compile_data_operations(python_sources=sources)
    operation = model.operations[0]
    base = python_port_identity(model, sources, operation.semantic_id)
    boundaries = (
        *operation.assets,
        *(
            boundary
            for item in model.implementation_slices
            if item.root == operation.implementation_root
            for boundary in item.boundaries
        ),
    )
    identity = PreparedCapabilityIdentity(
        **asdict(base),
        runtime="controlled-source-custody",
        assets=canonical_bytes(tuple(asdict(value) for value in boundaries)),
    )

    def authorize(actual):
        assert actual == identity

    port = resolve_controlled_port(
        None,
        model,
        operation.semantic_id,
        identity=identity,
        authorize=authorize,
        custody=sources.boundary_contracts,
        sources=sources,
    )
    kind = next(
        value.key
        for value in model.identities
        if value.domain == "kind" and value.owner == operation.roles[0].kind
    )
    logical = []
    for member, value in zip(members(), (4, 8), strict=True):
        context = SubjectContext(
            "project", member["member"], None, b"{}", subject_definition="controlled-value"
        )
        selected = BoundRoleMember(
            "controlled-input:" + member["member"],
            kind,
            context.subject,
            None,
            b"{}",
            b"{}",
            (),
            b"{}",
            subject_definition=context.subject_definition,
            support_references=(),
        )
        binding = BindingResult(
            operation.semantic_id,
            context.subject,
            (ResolvedRoleBinding("index", "present", (selected,)),),
            "ready",
            (),
            b'["mapping",[]]',
            b"{}",
            MODEL_VERSION,
            identity.definition,
            identity.eligibility,
            (),
            subject_context=context,
            replicate="controlled-observation",
        )
        logical.append(
            PythonBatchMember(
                member["member"],
                (PythonRoleValue("index", kind, value),),
                binding,
                producer=canonical_bytes(member["producer"]),
            )
        )
    cpu = scope()
    try:
        result = drive_prepared_work(
            port.plan_batch_python(
                tuple(logical), execution_owner=SimpleNamespace(cpu=cpu, reservation=None)
            ),
            lambda: None,
        )
        assert [(name, value.outputs[0].value()) for name, value in result.members] == [
            ("logical:one", 5),
            ("logical:two", 9),
        ]
        assert len({value.cpu_execution_evidence for _, value in result.members}) == 1
        assert len({value.cpu_execution_reply for _, value in result.members}) == 1
        assert all(value.cpu_execution_reply is not None for _, value in result.members)
    finally:
        cpu.close()
