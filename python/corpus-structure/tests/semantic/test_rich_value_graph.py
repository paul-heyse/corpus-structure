"""Independent exact value and actual range expectations for current rich members."""

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, localcontext

import pytest
from pydantic import ValidationError

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_member_contracts import derive_member_kinds
from corpus_structure.semantic.data_operation_model import MODEL_VERSION
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.rich_knowledge_contracts import (rich_kind_declarations, DdoRichScalarValue, DdoRichEntityValue, DdoRichRecordValue, DdoRichCollectionValue)
from corpus_structure.semantic.rich_value_graph import RichValueGraph


@pytest.fixture(scope="module")
def source():
    bundle = SourceBundle("values", (SourceArtifact("values", b"""id: urn:rich-values
name: rich_values
prefixes: {r: 'urn:rich-values:', xsd: 'http://www.w3.org/2001/XMLSchema#'}
default_prefix: r
default_range: string
types:
  string: {base: str, uri: 'xsd:string'}
  decimal: {base: Decimal, uri: 'xsd:decimal'}
  datetime: {base: datetime, uri: 'xsd:dateTime'}
  float: {base: float, uri: 'xsd:double'}
classes:
  Entity:
    attributes:
      id: {identifier: true, required: true}
  Measurement:
    attributes:
      amount: {range: decimal, required: true}
      at: {range: datetime, required: true}
      signed: {range: float, required: true}
      labels: {multivalued: true, required: true}
      reference: {range: Entity, inlined: false, required: true}
      note: {}
"""),))
    return prepare_release(bundle), compile_data_operations(bundle)


def test_exact_rich_value_members_keep_decimal_scale_independent_meaning_and_signed_float(source):
    prepared, model = source
    graph = RichValueGraph(prepared, model)
    with localcontext() as context:
        context.prec = 4
        original = Decimal("1.234567890123456789012345678901234567890123456789e-400")
        identifier = graph.lower_property("Measurement", "amount", original)
    scalar = next(value for value in graph.values if value.value_id == identifier)
    assert isinstance(scalar, DdoRichScalarValue)
    assert scalar.datatype == "decimal"
    assert Decimal(scalar.lexical) == original
    assert scalar.kind_contract == next(item.key for item in model.identities if item.domain == "kind" and item.owner == "type:urn:rich-values#decimal")
    assert graph.lower_property("Measurement", "amount", Decimal("0.1000")) == graph.lower_property("Measurement", "amount", Decimal("0.1"))
    assert graph.lower_property("Measurement", "signed", -0.0) != graph.lower_property("Measurement", "signed", 0.0)


def test_rich_record_fields_retain_actual_property_owners_and_original_entity_reference(source):
    prepared, model = source
    graph = RichValueGraph(prepared, model)
    instant = datetime(2026, 11, 15, 10, 30, tzinfo=timezone(timedelta(hours=3)))
    values = {"amount": Decimal("12.30"), "at": instant, "signed": -0.0,
              "labels": ("first", "second"), "reference": "entity:original"}
    identifier = graph.lower_record("Measurement", values)
    rows = {value.value_id: value for value in graph.values}
    record = rows[identifier]
    assert isinstance(record, DdoRichRecordValue)
    fields = {field.name: rows[field.value_id] for field in record.fields}
    definition = prepared.index.definitions["Measurement"]
    expected = {prop.name: prop.iri for prop in definition.properties}
    assert set(fields) == {expected[name] for name in values}
    at = fields[expected["at"]]
    reference = fields[expected["reference"]]
    assert isinstance(at, DdoRichScalarValue)
    assert isinstance(reference, DdoRichEntityValue)
    assert at.lexical == instant.astimezone(UTC).isoformat()
    assert reference.entity_id == "entity:original"
    labels = fields[expected["labels"]]
    assert isinstance(labels, DdoRichCollectionValue)
    actual = []
    for entry in labels.entries:
        text = rows[entry.value_id]
        assert isinstance(text, DdoRichScalarValue)
        actual.append((entry.position, text.lexical))
    assert actual == [(0, "first"), (1, "second")]
    assert graph.lower_property("Measurement", "at", instant) == graph.lower_property("Measurement", "at", instant.astimezone(UTC))
    assert expected["note"] not in fields


def test_rich_value_lowering_preserves_declared_scalar_refusals(source):
    prepared, model = source
    graph = RichValueGraph(prepared, model)
    with pytest.raises(ValidationError):
        graph.lower_property("Measurement", "amount", "12.3")
    with pytest.raises(ValidationError, match="timezone info"):
        graph.lower_property("Measurement", "at", datetime(2026, 11, 15))
    with pytest.raises(ValidationError):
        graph.lower_property("Measurement", "reference", {"id": "entity:invented-object"})


def test_actual_rich_consolidation_contract_has_finite_closed_nominal_member_kinds():
    source = SourceArtifact("rich-contracts.json", canonical_bytes({"version": MODEL_VERSION, "kinds": rich_kind_declarations()}))
    model = compile_data_operations(declarations=(source,))
    namespace = "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/"
    expected = {
        "DdoRichScalarValue", "DdoRichEntityValue", "DdoRichRecordValue", "DdoRichCollectionValue",
        "DdoRichEntity", "DdoRichFact", "DdoRichOccurrence", "DdoRichSourceReadingAssertion",
        "DdoRichAlternative", "DdoRichAssessment", "DdoRichDiagnostic",
    }
    for root in ("DdoRichConsolidation", "DdoRichAdmission"):
        assert set(derive_member_kinds(model, namespace + root)) == {namespace + name for name in expected}


def test_internal_cpu_context_pin_materializes_exact_public_json_only_against_actual_selected_context():
    from pydantic import TypeAdapter
    from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.rich_knowledge_contracts import DdoRichContextPin, materialize_rich_context, rich_context_pin
    from semantic.data_operation_declaration_support import contract, declarations

    model = compile_data_operations(declarations=declarations(contract(
        subject="knowledge-universe", subject_definition={"id": "knowledge-universe", "identifier_kind": "string", "scope": "project"},
    )))
    original = SubjectContext(project_id="actual-project", subject="actual-universe", subject_definition="knowledge-universe", original_source=None,
                              analyzed_scope=json_bytes({"fraction": Decimal("0.123456789012345678901234567890123456789")}))
    pin = rich_context_pin(original)
    # Exercise the real Pydantic CPU DTO round-trip. Public JSON is materialized
    # afterwards; no raw fractional number crosses its lossy JSON number parser.
    adapter = TypeAdapter(DdoRichContextPin)
    returned = adapter.validate_json(adapter.dump_json(pin), strict=True)
    result = materialize_rich_context(returned, model, expected_context=original)
    raw = json_loads(json_bytes(result.model_dump(mode="python")))
    assert raw["analyzed_scope"] == json_loads(original.analyzed_scope)
    assert "original_source" in raw and raw["original_source"] is None
    forged = returned.model_copy(update={"project_id": "another-project"})
    with pytest.raises(ValueError, match="actual selected"):
        materialize_rich_context(forged, model, expected_context=original)


@pytest.mark.parametrize("datatype,lexical", [("decimal", "NaN"), ("decimal", "0.1000"), ("integer", "+01"), ("float", "nan"), ("boolean", "1"), ("datetime", "2026-11-15T00:00:00"), ("null", "unavailable")])
def test_rich_scalar_contract_refuses_forged_noncanonical_meaning(datatype, lexical):
    with pytest.raises(ValidationError):
        DdoRichScalarValue(member_type="scalar-value", value_id="value:untrusted", kind_contract="kind:untrusted", datatype=datatype, lexical=lexical)
