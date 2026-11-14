"""Independent external protocol meaning and refusal controls; no remote agent calls."""

from copy import deepcopy

import pytest

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_external import ExternalResultPort
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import read_effective_data_operations
from corpus_structure.semantic.types import PreparationError
from semantic.data_operation_declaration_support import declarations, identity
from semantic.external_scenarios import external_declaration


def test_external_protocol_is_source_free_recipe_meaning_and_roundtrips():
    declared = external_declaration()
    model = compile_data_operations(declarations=declarations(declared))
    assert not model.implementation_slices
    external = model.operations[0].external
    assert external is not None
    assert external.instructions.startswith("Return the independently")
    assert read_effective_data_operations(model.content).content == model.content
    changed = deepcopy(declared)
    changed["external"]["requested_model"] = "actual-model-assertion"
    newer = compile_data_operations(declarations=declarations(changed))
    assert identity(model, declared["id"]) != identity(newer, declared["id"])


@pytest.mark.parametrize(
    "change", ["protected", "reference-scope", "effect-authorization", "python-factory"]
)
def test_external_protocol_refuses_unadmitted_authority(change):
    declared = external_declaration()
    kinds = []
    if change == "protected":
        kinds = [{"id": "protected", "primitive": "integer", "universe": "evaluator"}]
        declared["roles"][0]["kind"] = "protected"
    elif change == "reference-scope":
        declared["external"]["reference_scope"] = "all-data"
    elif change == "effect-authorization":
        declared["effects"][0]["authorization"] = ["operator-assumed"]
    else:
        declared["capabilities"]["prepared_factory"] = {
            "reference": "missing.Factory",
            "method": "acquire",
        }
    expected = {"protected": "protected evaluator kinds", "reference-scope": "declared-input reference scope",
                "effect-authorization": "native write authorization", "python-factory": "captured capability"}
    with pytest.raises(PreparationError, match=expected[change]):
        compile_data_operations(declarations=declarations(declared, kinds=kinds))


def test_external_result_port_preserves_integer_meaning_and_refuses_receipt_injection():
    declared = external_declaration()
    model = compile_data_operations(declarations=declarations(declared))
    packet = {
        "operation_id": declared["id"],
        "recipe": identity(model, declared["id"]),
        "outcomes": ["success", "empty", "failed"],
        "binding": {"inputs": [], "support": []},
        "implementation_revision": "external:" + identity(model, declared["id"]),
        "result_contract": [
            {
                "role": "result",
                "kind_contract": identity(model, "primitive:integer", "kind"),
                "schema": {"type": "integer"},
            }
        ],
    }
    port = ExternalResultPort(json_bytes(packet), model, 10000)
    result = {"outcome": "success", "outputs": [{"role": "result", "body": 7}]}
    completion = port.completion(result)
    assert completion["outputs"][0]["product"]["body"] == ["integer", "7"]
    assert completion["inputs"] == [] and "execution_evidence" not in completion
    with pytest.raises(ValueError):
        port.completion({**result, "execution_evidence": {"made_up": True}})
    with pytest.raises(ValueError):
        port.completion({"outcome": "success", "outputs": [{"role": "result", "body": "7"}]})
    with pytest.raises(ValueError):
        ExternalResultPort(json_bytes(packet), model, 1).completion(result)


def test_frozen_model_reuses_content_and_exact_decoding_without_caching_other_inputs():
    model = compile_data_operations(declarations=declarations(external_declaration()))
    first = model.content
    assert model.content is first
    decoded = read_effective_data_operations(first)
    assert read_effective_data_operations(first) is decoded
    class CapturedBytes(bytes):
        pass

    captured = CapturedBytes(first)
    assert read_effective_data_operations(captured) == decoded
    assert read_effective_data_operations(captured) is not decoded
    with pytest.raises(ValueError):
        read_effective_data_operations(first[:-1])
