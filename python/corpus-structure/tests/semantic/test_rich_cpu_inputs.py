"""Exact actual CPU role reconstruction, without parallel body/header copies."""

from corpus_structure.semantic.selected_support import ProducerOutputOccurrence

from decimal import Decimal

import pytest
from pydantic import TypeAdapter

from corpus_structure.semantic.data_operation_cpu_basis import CPUInputRole, cpu_input_basis
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
from corpus_structure.semantic.rich_cpu_inputs import RichKernelInputs


def test_actual_child_inputs_reconstruct_exact_scope_typed_body_and_support_after_cpu_json():
    context = SubjectContext(
        "project:one",
        "knowledge:one",
        None,
        json_bytes({"page": Decimal("0.123456789012345678901234567890123456789")}),
        subject_definition="knowledge-universe",
    )
    source = SubjectContext(
        "project:one",
        "source:one",
        "original:one",
        b'{"page":1}',
        subject_definition="selected-native-source",
    )
    supports = (
        ComputationalSupportReference(
            kind="computation", derivation_id="episode:one", admission_use_id="use:one"
        ),
    )
    role = CPUInputRole(
        "records",
        None,
        1,
        "product:one",
        None,
        "kind:whole",
        source,
        {"signed": -0.0, "fraction": Decimal("1e-300")},
        supports,
     producer_output=ProducerOutputOccurrence(member_id=None, role="result", position=0, multiplicity=1))
    meaning = cpu_input_basis(
        "recipe:actual", context, (role,), parameters=b'["mapping",[]]', replicate=None
    )
    adapter = TypeAdapter(list)
    returned = adapter.validate_json(adapter.dump_json(meaning))
    inputs = RichKernelInputs.from_basis(returned)
    assert inputs.context == context
    assert inputs.scalar("records").context == source
    assert inputs.scalar("records").body["fraction"] == Decimal("1e-300")
    assert inputs.scalar("records").body["signed"].hex() == "-0x0.0p+0"
    assert inputs.reference(inputs.scalar("records")).support_references == supports
    assert inputs.basis() == meaning
    with pytest.raises(ValueError, match="one actual whole"):
        inputs.scalar("unknown")
    altered = decode_semantic_value(meaning)
    altered["roles"][0]["invented"] = "ignored"
    from corpus_structure.semantic.data_operation_identity import semantic_value

    with pytest.raises(ValueError, match="finite role"):
        RichKernelInputs.from_basis(semantic_value(altered))


def test_shared_cpu_basis_distinguishes_exact_parameters_with_same_roles_and_context():
    from hashlib import sha256

    from corpus_structure.semantic.data_operation_cpu_basis import (
        cpu_authority_reply,
        cpu_authority_value,
    )
    from corpus_structure.semantic.data_operation_identity import semantic_value
    from corpus_structure.semantic.identity import canonical_bytes

    context = SubjectContext(
        "project", "knowledge", None, b"{}", subject_definition="knowledge-universe"
    )
    variants = (
        {},
        {"selected": None},
        {"selected": 1},
        {"selected": 1.0},
        {"selected": Decimal("1")},
        {"selected": Decimal("0.12345678901234567890123456789")},
    )
    bases = [
        cpu_input_basis(
            "same-recipe",
            context,
            (),
            parameters=canonical_bytes(semantic_value(value)),
            replicate=None,
        )
        for value in variants
    ]
    assert len({sha256(canonical_bytes(basis)).hexdigest() for basis in bases}) == len(variants)
    for expected, basis in zip(variants, bases, strict=True):
        actual = decode_semantic_value(basis)
        assert actual["version"] == "cpu-input-basis-3"
        assert actual["parameters"] == expected
        assert canonical_bytes(semantic_value(actual["parameters"])) == canonical_bytes(
            semantic_value(expected)
        )
    reply = canonical_bytes(cpu_authority_reply(bases[0], {"result": "actual"}))
    assert cpu_authority_value(reply, expected_basis=bases[0]) == {"result": "actual"}
    with pytest.raises(ValueError, match="input basis"):
        cpu_authority_value(reply, expected_basis=bases[1])
    replicated = cpu_input_basis(
        "same-recipe",
        context,
        (),
        parameters=b'["mapping",[]]',
        replicate="independent-observation-B",
    )
    with pytest.raises(ValueError, match="input basis"):
        cpu_authority_value(reply, expected_basis=replicated)
