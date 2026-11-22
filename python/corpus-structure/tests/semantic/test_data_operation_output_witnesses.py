"""Independent grouped-witness expectations, including cross-member forgery."""

from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest

from corpus_structure.semantic import data_operation_output_witnesses as witnesses
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
        "subject_definition": ("selected-input", "subject_definition", "value"),
        "scope": ("selected-input", "analyzed_scope", "context-meaning-json"),
        "document": ("Source", "document", "value"),
    }
    return {
        "output_role": "result",
        "records": "/records/*/pin",
        "input_role": "source",
        "comparisons": [
            {
                "output_field": name,
                "input": {"role": "source", "projection": projection, "field": field},
                "encoding": encoding,
            }
            for name, (projection, field, encoding) in fields.items()
        ],
    }


def compiled(witness=None):
    bundle = SourceBundle(
        "model",
        (
            SourceArtifact(
                "model",
                b"""id: urn:witness:model
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
      subject_definition: {required: true}
      scope: {required: true}
      document: {required: true}
  Record:
    attributes:
      pin: {range: Pin, inlined: true, required: true}
  Envelope:
    attributes:
      records: {range: Record, inlined: true, multivalued: true}
""",
            ),
        ),
    )
    value = contract()
    value["roles"][0]["kind"] = "Source"
    value["roles"][1]["kind"] = "Envelope"
    if witness is not None:
        value["output_witnesses"] = [witness]
    return compile_data_operations(bundle, declarations=declarations(value))


def pin():
    return {
        "source_product": "p:a",
        "source_member": "m:a",
        "source": '["p:a","m:a"]',
        "subject": "s:a",
        "subject_definition": "original-source-view",
        "scope": '["mapping",[["page",["decimal","1"]]]]',
        "document": "doc:a",
    }


def selected() -> dict[str, list[dict[str, Any]]]:
    return {
        "source": [
            {
                "product": "p:a",
                "member": "m:a",
                "subject": "s:a",
                "subject_definition": "original-source-view",
                "analyzed_scope": {"page": 1},
                "body": {"document": "doc:a"},
            },
            {
                "product": "p:b",
                "member": "m:b",
                "subject": "s:b",
                "subject_definition": "original-document",
                "analyzed_scope": {"page": 2},
                "body": {"document": "doc:b"},
            },
        ]
    }


def test_selected_witness_rows_materialize_only_declared_fields_and_roles():
    operation = compiled(group()).operations[0]
    declaration = operation.output_witnesses[0]
    # Keep only the declared reference comparison. Neither the source body nor
    # its other member metadata or the unrelated role should be inspected.
    reference = replace(declaration, comparisons=(declaration.comparisons[2],))
    operation = replace(operation, output_witnesses=(reference,))
    source = SimpleNamespace(member=SimpleNamespace(product="p:a", member="m:a"))
    selection = SimpleNamespace(values=(("source", (source,)), ("unused", (object(),))))
    assert witnesses.selected_witness_rows(operation, selection, "project") == {
        "source": ({"product": "p:a", "member": "m:a"},)
    }


def test_repeated_output_records_prepare_each_complete_input_key_once(monkeypatch):
    operation = compiled(group()).operations[0]
    prepared = []
    input_key = witnesses._input_key

    def prepare(row, comparisons):
        prepared.append(row["member"])
        return input_key(row, comparisons)

    monkeypatch.setattr(witnesses, "_input_key", prepare)
    outputs = {"result": [{"records": [{"pin": pin()} for _ in range(8)]}]}
    validate_output_witnesses(operation, outputs, selected())
    assert prepared == ["m:a", "m:b"]


def test_group_compiles_into_recipe_and_roundtrips_without_changing_unrelated_model():
    ordinary = compiled()
    model = compiled(group())
    assert ordinary.operations[0].recipe != model.operations[0].recipe
    assert (
        model.operations[0].output_witnesses[0].comparisons[-1].input.projection
        == "urn:witness:Source"
    )
    assert read_effective_data_operations(model.content).content == model.content
    assert read_effective_data_operations(ordinary.content).content == ordinary.content
    assert b'"output_witnesses"' not in ordinary.content


def test_complete_member_satisfies_all_comparisons_with_jsonb_scope_semantics():
    operation = compiled(group()).operations[0]
    rows = selected()
    rows["source"][0]["analyzed_scope"] = {"page": 1.0}
    validate_output_witnesses(operation, {"result": [{"records": [{"pin": pin()}]}]}, rows)
    validate_output_witnesses(operation, {"result": [{"records": []}]}, rows)


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_product", "p:b"),
        ("source_member", "m:b"),
        ("subject", "s:b"),
        ("subject_definition", "original-document"),
        ("scope", '["mapping",[["page",["decimal","2"]]]]'),
        ("document", "doc:b"),
        ("source", '["p:b","m:b"]'),
    ],
)
def test_individually_valid_foreign_fields_cannot_form_a_hybrid_witness(field, value):
    operation = compiled(group()).operations[0]
    forged = {**pin(), field: value}
    with pytest.raises(ValueError, match="no complete selected input member"):
        validate_output_witnesses(
            operation, {"result": [{"records": [{"pin": forged}]}]}, selected()
        )


@pytest.mark.parametrize(
    "mutation",
    ["untyped-path", "missing-member-step", "wrong-role", "wrong-kind", "wrong-encoding"],
)
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


def test_missing_body_field_is_not_an_implicit_null_witness():
    operation = compiled(group()).operations[0]
    rows = selected()
    rows["source"][0]["body"].pop("document")
    incomplete = pin()
    incomplete.pop("document")
    with pytest.raises(ValueError, match="no complete selected input member"):
        validate_output_witnesses(operation, {"result": [{"records": [{"pin": incomplete}]}]}, rows)


def test_numeric_boolean_value_witnesses_are_typed_without_becoming_subject_identifiers():
    bundle = SourceBundle(
        "model",
        (
            SourceArtifact(
                "model",
                b"""id: urn:scalar-witness:model
name: model
prefixes:
  w: 'urn:scalar-witness:'
  xsd: 'http://www.w3.org/2001/XMLSchema#'
default_prefix: w
types:
  integer: {base: int, uri: 'xsd:integer'}
  boolean: {base: bool, uri: 'xsd:boolean'}
classes:
  Record:
    attributes:
      count: {range: integer, required: true}
      flag: {range: boolean, required: true}
""",
            ),
        ),
    )
    value = contract()
    for role in value["roles"]:
        role["kind"] = "Record"
    value["output_witnesses"] = [
        {
            "output_role": "result",
            "records": "",
            "input_role": "source",
            "comparisons": [
                {
                    "output_field": field,
                    "input": {"role": "source", "projection": "Record", "field": field},
                    "encoding": "value",
                }
                for field in ("count", "flag")
            ],
        }
    ]
    operation = compile_data_operations(bundle, declarations=declarations(value)).operations[0]
    rows = {"source": [{"body": {"count": 3, "flag": False}}]}
    validate_output_witnesses(operation, {"result": [{"count": 3, "flag": False}]}, rows)
    with pytest.raises(ValueError, match="no complete selected input"):
        validate_output_witnesses(operation, {"result": [{"count": 3, "flag": 0}]}, rows)
    value["roles"][0]["subject_field"] = "count"
    with pytest.raises(PreparationError, match="scalar subject identifier"):
        compile_data_operations(bundle, declarations=declarations(value))


def test_nested_value_witness_preserves_optional_absence_and_subjects_stay_scalar():
    bundle = SourceBundle(
        "model",
        (
            SourceArtifact(
                "model",
                b"""id: urn:record-witness:model
name: model
prefixes:
  w: 'urn:record-witness:'
  xsd: 'http://www.w3.org/2001/XMLSchema#'
default_prefix: w
default_range: string
types:
  integer: {base: int, uri: 'xsd:integer'}
  string: {base: str, uri: 'xsd:string'}
classes:
  Selection:
    attributes:
      page: {range: integer, required: true}
      pointer: {}
  Record:
    attributes:
      selection: {range: Selection, inlined: true, required: true}
""",
            ),
        ),
    )
    value = contract()
    for role in value["roles"]:
        role["kind"] = "Record"
    value["output_witnesses"] = [
        {
            "output_role": "result",
            "records": "",
            "input_role": "source",
            "comparisons": [
                {
                    "output_field": "selection",
                    "input": {"role": "source", "projection": "Record", "field": "selection"},
                    "encoding": "value",
                }
            ],
        }
    ]
    operation = compile_data_operations(bundle, declarations=declarations(value)).operations[0]
    selected = {"source": [{"body": {"selection": {"page": 1}}}]}
    validate_output_witnesses(operation, {"result": [{"selection": {"page": 1}}]}, selected)
    with pytest.raises(ValueError, match="no complete selected input"):
        validate_output_witnesses(
            operation, {"result": [{"selection": {"page": 1, "pointer": None}}]}, selected
        )
    value["roles"][0]["subject_field"] = "selection"
    with pytest.raises(PreparationError, match="scalar subject identifier"):
        compile_data_operations(bundle, declarations=declarations(value))
