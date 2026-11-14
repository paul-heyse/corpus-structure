"""Independent grouped-witness expectations, including cross-member forgery."""

from dataclasses import replace

import pytest

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_model import read_effective_data_operations
from corpus_structure.semantic.data_operation_output_witnesses import validate_output_witnesses
from corpus_structure.semantic.types import PreparationError, SourceArtifact, SourceBundle
from semantic.data_operation_declaration_support import contract, declarations


def group():
    fields = {
        "source_product": ("selected-input", "product", "value"),
        "source_member": ("selected-input", "member", "value"),
        "source": ("selected-input", "reference", "json"),
        "subject": ("selected-input", "subject", "value"),
        "scope": ("selected-input", "analyzed_scope", "context-meaning-json"),
        "document": ("Source", "document", "value"),
    }
    return {"output_role": "result", "records": "/records/*/pin", "input_role": "source", "comparisons": [
        {"output_field": name, "input": {"role": "source", "projection": projection, "field": field}, "encoding": encoding}
        for name, (projection, field, encoding) in fields.items()
    ]}


def compiled(witness=None):
    bundle = SourceBundle("model", (SourceArtifact("model", b'''id: urn:witness:model
name: model
prefixes:
  w: 'urn:witness:'
  xsd: 'http://www.w3.org/2001/XMLSchema#'
default_prefix: w
default_range: string
types:
  string:
    base: str
    uri: xsd:string
classes:
  Source:
    attributes:
      document: {required: true}
  Pin:
    attributes:
      source_product: {required: true}
      source_member: {}
      source: {required: true}
      subject: {required: true}
      scope: {required: true}
      document: {required: true}
  Record:
    attributes:
      pin: {range: Pin, inlined: true, required: true}
  Envelope:
    attributes:
      records: {range: Record, inlined: true, multivalued: true}
'''),))
    value = contract()
    value["roles"][0]["kind"] = "Source"
    value["roles"][1]["kind"] = "Envelope"
    if witness is not None:
        value["output_witnesses"] = [witness]
    return compile_data_operations(bundle, declarations=declarations(value))


def pin():
    return {"source_product": "p:a", "source_member": "m:a", "source": '["p:a","m:a"]', "subject": "s:a", "scope": '["mapping",[["page",["decimal","1"]]]]', "document": "doc:a"}


def selected():
    return {"source": [
        {"product": "p:a", "member": "m:a", "subject": "s:a", "analyzed_scope": {"page": 1}, "body": {"document": "doc:a"}},
        {"product": "p:b", "member": "m:b", "subject": "s:b", "analyzed_scope": {"page": 2}, "body": {"document": "doc:b"}},
    ]}


def test_group_compiles_into_recipe_and_roundtrips_without_changing_unrelated_model():
    ordinary = compiled()
    model = compiled(group())
    assert ordinary.operations[0].recipe != model.operations[0].recipe
    assert model.operations[0].output_witnesses[0].comparisons[-1].input.projection == "urn:witness:Source"
    assert read_effective_data_operations(model.content).content == model.content
    assert read_effective_data_operations(ordinary.content).content == ordinary.content
    assert b'"output_witnesses"' not in ordinary.content


def test_complete_member_satisfies_all_comparisons_with_jsonb_scope_semantics():
    operation = compiled(group()).operations[0]
    rows = selected()
    rows["source"][0]["analyzed_scope"] = {"page": 1.0}
    validate_output_witnesses(operation, {"result": [{"records": [{"pin": pin()}]}]}, rows)
    validate_output_witnesses(operation, {"result": [{"records": []}]}, rows)


@pytest.mark.parametrize("field,value", [
    ("source_product", "p:b"), ("source_member", "m:b"), ("subject", "s:b"),
    ("scope", '["mapping",[["page",["decimal","2"]]]]'), ("document", "doc:b"),
    ("source", '["p:b","m:b"]'),
])
def test_individually_valid_foreign_fields_cannot_form_a_hybrid_witness(field, value):
    operation = compiled(group()).operations[0]
    forged = {**pin(), field: value}
    with pytest.raises(ValueError, match="no complete selected input member"):
        validate_output_witnesses(operation, {"result": [{"records": [{"pin": forged}]}]}, selected())


@pytest.mark.parametrize("mutation", ["untyped-path", "missing-member-step", "wrong-role", "wrong-kind", "wrong-encoding"])
def test_compiler_refuses_untyped_or_ambiguous_witness_mapping(mutation):
    witness = group()
    if mutation == "untyped-path":
        witness["comparisons"][0]["output_field"] = "not_a_property"
    elif mutation == "missing-member-step":
        witness["records"] = "/records/pin"
    elif mutation == "wrong-role":
        witness["comparisons"][0]["input"]["role"] = "result"
    elif mutation == "wrong-kind":
        witness["comparisons"][-1]["input"]["projection"] = "Pin"
    else:
        witness["comparisons"][0]["encoding"] = "json"
    with pytest.raises(PreparationError):
        compiled(witness)


def test_historical_archive_cannot_acquire_new_witness_meaning():
    from corpus_structure.semantic.data_operation_model import PREVIOUS_MODEL_VERSION

    old = replace(compiled(), version=PREVIOUS_MODEL_VERSION)
    assert read_effective_data_operations(old.content).content == old.content
    with pytest.raises(ValueError, match="historical models cannot"):
        replace(compiled(group()), version=PREVIOUS_MODEL_VERSION).content
