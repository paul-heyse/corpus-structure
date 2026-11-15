"""Exact actual CPU role reconstruction, without parallel body/header copies."""

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
    )
    meaning = cpu_input_basis("recipe:actual", context, (role,))
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
