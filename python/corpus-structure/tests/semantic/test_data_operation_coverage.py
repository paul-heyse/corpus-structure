"""Actual coverage owners and selection semantics, independent of descriptive labels."""

from copy import deepcopy
from hashlib import sha256
import json
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.native_definition_projection import read_native_definition_projection
from corpus_structure.semantic.types import PreparationError
from semantic.data_operation_declaration_support import contract, declarations


def compile_contract(value=None):
    return compile_data_operations(declarations=declarations(contract() if value is None else value))


def test_checked_coverage_retains_actual_binding_role_schema_and_declaration_meaning():
    model = compile_contract()
    operation = model.operations[0]
    coverage = operation.coverage
    assert coverage.binding == operation.semantic_id + "/binding"
    selection = json.loads(coverage.selection)
    assert selection["binding"]["operator"] == "scan"
    assert selection["binding"]["roles"] == ["source"]
    role, = selection["input_roles"]
    assert (role["name"], role["minimum"], role["maximum"]) == ("source", 1, 1)
    assert role["support"]["coverage"] == {"role": "source"}
    assert {owner.kind for owner in coverage.result_owners} == {"declared-contract", "schema"}
    declared = next(owner for owner in coverage.result_owners if owner.kind == "declared-contract")
    assert json.loads(declared.semantics)["behavior"] == "integer-derive-v1"
    schema = next(owner for owner in coverage.result_owners if owner.kind == "schema")
    assert schema.reference == "primitive:integer"
    assert json.loads(schema.semantics)["kind_contract"].startswith("kind:")


def test_coverage_wording_is_descriptive_and_binding_changes_remain_semantic():
    original = contract()
    reworded = deepcopy(original)
    reworded["coverage"]["description"] = "An edited explanation of complete input coverage"
    reworded["roles"][0]["support"]["coverage"]["description"] = "An edited explanation of the input scope"
    before, after = compile_contract(original).operations[0], compile_contract(reworded).operations[0]
    assert before.recipe == after.recipe
    assert before.definition == after.definition
    assert before.coverage != after.coverage
    changed = deepcopy(original)
    changed["binding"] = {"operator": "all", "children": [changed["binding"], {"operator": "cardinality", "roles": ["source"], "minimum": 1, "maximum": 1}]}
    assert compile_contract(changed).operations[0].recipe != before.recipe


@pytest.mark.parametrize("change", ["label", "wrong-binding", "missing-owner", "schema-only", "wrong-role"])
def test_missing_or_unresolved_coverage_owners_refuse(change):
    value = contract()
    if change == "label": value["coverage"] = "coverage is merely asserted"
    elif change == "wrong-binding": value["coverage"]["binding"] = "foreign-owner"
    elif change == "missing-owner": value["coverage"]["result_owners"] = []
    elif change == "schema-only": value["coverage"]["result_owners"] = [{"kind": "schema", "reference": "integer"}]
    else: value["roles"][0]["support"]["coverage"]["role"] = "different-input"
    with pytest.raises(PreparationError): compile_contract(value)


def test_native_reader_requires_exact_checked_current_coverage_export():
    model = compile_contract()
    operation = model.operations[0]
    coverage = json.loads(model.content)["operations"][0]["coverage"]
    record = {"model_digest": sha256(model.content).hexdigest(), "native_digest": "controlled-native", "kinds": [], "operations": [{
        "operation_id": operation.semantic_id, "subject_definition": operation.subject,
        "recipe": "recipe:controlled", "profile": operation.profile, "binding": {},
        "definition": "definition:controlled", "eligibility": "eligibility:controlled", "implementation_revision": "declared", "input_roles": [], "output_roles": [],
        "support_contract": {"replicate_policy": "deterministic-single-result", "coverage": coverage},
    }]}
    def prepared(value):
        return SimpleNamespace(artifacts=(SimpleNamespace(kind="data_operation_native_definitions.json", content=canonical_bytes(value)),))
    assert read_native_definition_projection(prepared(record), model=model)["operations"][0]["support_contract"]["coverage"] == coverage
    for changed in (None, {**coverage, "binding": "foreign-owner"}):
        altered = deepcopy(record)
        altered["operations"][0]["support_contract"]["coverage"] = changed
        with pytest.raises(ValueError, match="coverage differs"):
            read_native_definition_projection(prepared(altered), model=model)
