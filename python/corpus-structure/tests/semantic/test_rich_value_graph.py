"""Independent exact value and actual range expectations for current rich members."""

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, localcontext

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_member_contracts import derive_member_kinds
from corpus_structure.semantic.data_operation_version import MODEL_VERSION
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.rich_knowledge_contracts import (
    DdoRichCollectionValue,
    DdoRichEntityValue,
    DdoRichRecordValue,
    DdoRichScalarValue,
    rich_kind_declarations,
)
from corpus_structure.semantic.rich_value_graph import RichValueGraph
from corpus_structure.semantic.types import SourceArtifact, SourceBundle


@pytest.fixture(scope="module")
def source():
    bundle = SourceBundle(
        "values",
        (
            SourceArtifact(
                "values",
                b"""id: urn:rich-values
name: rich_values
prefixes: {r: 'urn:rich-values:', xsd: 'http://www.w3.org/2001/XMLSchema#'}
default_prefix: r
default_range: string
types:
  string: {base: str, uri: 'xsd:string'}
  decimal: {base: Decimal, uri: 'xsd:decimal'}
  datetime: {base: datetime, uri: 'xsd:dateTime'}
  float: {base: float, uri: 'xsd:double'}
enums:
  Establishment:
    permissible_values: {stated: {}, derived: {}, agent_asserted: {}}
classes:
  Entity:
    attributes:
      id: {identifier: true, required: true}
  Measurement:
    annotations: {cs:scope: global}
    attributes:
      amount: {range: decimal, required: true}
      at: {range: datetime, required: true}
      signed: {range: float, required: true}
      labels: {multivalued: true, required: true}
      reference: {range: Entity, inlined: false, required: true}
      note: {}
      optional_ref: {range: Entity, inlined: false}
      optional_inline: {range: Detail, inlined: true}
      optional_values: {multivalued: true}
  Detail:
    attributes:
      label: {required: true, slot_uri: r:shared}
      alias: {slot_uri: r:shared}
  KeyedEntity:
    annotations: {cs:scope: global}
    is_a: Entity
    attributes:
      code: {required: true}
    unique_keys:
      business: {unique_key_slots: [code]}
  Qualification:
    attributes:
      label: {required: true, annotations: {cs:case: casefold}}
      reporter: {annotations: {cs:key_role: provenance}}
""",
            ),
        ),
    )
    from semantic.data_operation_declaration_support import contract, declarations

    operation = contract(
        subject="knowledge-universe",
        subject_definition={
            "id": "knowledge-universe",
            "identifier_kind": "string",
            "scope": "project",
        },
    )
    kinds = SourceArtifact(
        "actual-rich-contracts.json",
        canonical_bytes({"version": MODEL_VERSION, "kinds": rich_kind_declarations()}),
    )
    return prepare_release(bundle), compile_data_operations(
        bundle, declarations=(*declarations(operation), kinds)
    )


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
    assert scalar.kind_contract == next(
        item.key
        for item in model.identities
        if item.domain == "kind" and item.owner == "type:urn:rich-values#decimal"
    )
    assert graph.lower_property("Measurement", "amount", Decimal("0.1000")) == graph.lower_property(
        "Measurement", "amount", Decimal("0.1")
    )
    assert graph.lower_property("Measurement", "signed", -0.0) != graph.lower_property(
        "Measurement", "signed", 0.0
    )


def test_rich_record_fields_retain_actual_property_owners_and_original_entity_reference(source):
    prepared, model = source
    graph = RichValueGraph(prepared, model)
    instant = datetime(2026, 11, 15, 10, 30, tzinfo=timezone(timedelta(hours=3)))
    values = {
        "amount": Decimal("12.30"),
        "at": instant,
        "signed": -0.0,
        "labels": ("first", "second"),
        "reference": "entity:original",
    }
    identifier = graph.lower_record("Measurement", values)
    rows = {value.value_id: value for value in graph.values}
    record = rows[identifier]
    assert isinstance(record, DdoRichRecordValue)
    fields = {field.property_contract: rows[field.value_id] for field in record.fields}
    definition = prepared.index.definitions["Measurement"]
    expected = {
        prop.name: next(
            item.key
            for item in model.identities
            if item.domain == "kind" and item.owner == definition.iri + "/property/" + prop.name
        )
        for prop in definition.properties
    }
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
    assert graph.lower_property("Measurement", "at", instant) == graph.lower_property(
        "Measurement", "at", instant.astimezone(UTC)
    )
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
    source = SourceArtifact(
        "rich-contracts.json",
        canonical_bytes({"version": MODEL_VERSION, "kinds": rich_kind_declarations()}),
    )
    model = compile_data_operations(declarations=(source,))
    namespace = "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/"
    expected = {
        "DdoRichScalarValue",
        "DdoRichEntityValue",
        "DdoRichRecordValue",
        "DdoRichCollectionValue",
        "DdoRichEntity",
        "DdoRichFact",
        "DdoRichOccurrence",
        "DdoRichSourceReadingAssertion",
        "DdoRichAlternative",
        "DdoRichAssessment",
        "DdoRichDiagnostic",
        "DdoRichCasefoldText",
        "DdoRichQualificationMeaning",
        "DdoRichIdentityResolution",
        "DdoRichOccurrenceDecision",
        "DdoRichIdentityExclusion",
    }
    for root in ("DdoRichConsolidation", "DdoRichAdmission"):
        assert set(derive_member_kinds(model, namespace + root)) == {
            namespace + name for name in expected
        }


def test_internal_cpu_context_pin_materializes_exact_public_json_only_against_actual_selected_context():
    from pydantic import TypeAdapter

    from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.rich_knowledge_contracts import (
        DdoRichContextPin,
        materialize_rich_context,
        rich_context_pin,
    )
    from semantic.data_operation_declaration_support import contract, declarations

    model = compile_data_operations(
        declarations=declarations(
            contract(
                subject="knowledge-universe",
                subject_definition={
                    "id": "knowledge-universe",
                    "identifier_kind": "string",
                    "scope": "project",
                },
            )
        )
    )
    original = SubjectContext(
        project_id="actual-project",
        subject="actual-universe",
        subject_definition="knowledge-universe",
        original_source=None,
        analyzed_scope=json_bytes(
            {"fraction": Decimal("0.123456789012345678901234567890123456789")}
        ),
    )
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


@pytest.mark.parametrize(
    "datatype,lexical",
    [
        ("decimal", "NaN"),
        ("decimal", "0.1000"),
        ("integer", "+01"),
        ("float", "nan"),
        ("boolean", "1"),
        ("datetime", "2026-11-15T00:00:00"),
        ("null", "unavailable"),
    ],
)
def test_rich_scalar_contract_refuses_forged_noncanonical_meaning(datatype, lexical):
    with pytest.raises(ValidationError):
        DdoRichScalarValue(
            member_type="scalar-value",
            value_id="value:untrusted",
            kind_contract="kind:untrusted",
            datatype=datatype,
            lexical=lexical,
        )


def test_actual_optional_boundaries_keep_omission_empty_and_present_values_distinct_and_refuse_null(
    source,
):
    prepared, model = source
    graph = RichValueGraph(prepared, model)
    observed = {
        "amount": Decimal("1"),
        "at": datetime(2026, 11, 15, tzinfo=UTC),
        "signed": 0.0,
        "labels": ("observed",),
        "reference": "entity:original",
    }
    omitted = graph.lower_record("Measurement", observed)
    empty = graph.lower_record("Measurement", {**observed, "optional_values": ()})
    present = graph.lower_record(
        "Measurement",
        {
            **observed,
            "note": "",
            "optional_ref": "entity:retained",
            "optional_inline": {"label": "actual"},
        },
    )
    assert len({omitted, empty, present}) == 3
    rows = {value.value_id: value for value in graph.values}
    props = {
        prop.name: next(
            item.key
            for item in model.identities
            if item.domain == "kind"
            and item.owner == "urn:rich-values:Measurement/property/" + prop.name
        )
        for prop in prepared.index.definitions["Measurement"].properties
    }
    empty_record = rows[empty]
    assert isinstance(empty_record, DdoRichRecordValue)
    empty_values = rows[
        next(
            field.value_id
            for field in empty_record.fields
            if field.property_contract == props["optional_values"]
        )
    ]
    assert isinstance(empty_values, DdoRichCollectionValue)
    assert empty_values.entries == ()
    present_record = rows[present]
    assert isinstance(present_record, DdoRichRecordValue)
    fields = {field.property_contract: rows[field.value_id] for field in present_record.fields}
    assert isinstance(fields[props["optional_inline"]], DdoRichRecordValue)
    assert isinstance(fields[props["optional_ref"]], DdoRichEntityValue)
    assert isinstance(fields[props["note"]], DdoRichScalarValue)
    for name in ("note", "optional_ref", "optional_inline", "optional_values"):
        with pytest.raises(ValidationError):
            graph.lower_record("Measurement", {**observed, name: None})
        with pytest.raises(ValidationError):
            graph.lower_property("Measurement", name, None)


def test_qualification_meaning_excludes_provenance_and_uses_explicit_casefold_projection(source):
    from corpus_structure.semantic.rich_knowledge_contracts import (
        DdoRichCasefoldText,
        DdoRichQualificationMeaning,
    )

    prepared, model = source
    graph = RichValueGraph(prepared, model)
    first = {"label": "Gaussian", "reporter": "source-A"}
    second = {"label": "GAUSSIAN", "reporter": "source-B"}
    observed_a, meaning_a = graph.lower_qualification("Qualification", first)
    observed_b, meaning_b = graph.lower_qualification("Qualification", second)
    assert observed_a != observed_b
    assert meaning_a == meaning_b
    rows = {value.value_id: value for value in graph.values}
    meaning = rows[meaning_a]
    assert isinstance(meaning, DdoRichQualificationMeaning)
    assert len(meaning.fields) == 1
    folded = rows[meaning.fields[0].value_id]
    assert isinstance(folded, DdoRichCasefoldText)
    assert folded.text == "gaussian"
    assert not hasattr(folded, "kind_contract")
    assert prepared.fact_identity(
        "realization", "entity:subject", "urn:predicate", "object", first
    ) == prepared.fact_identity("realization", "entity:subject", "urn:predicate", "object", second)
    _, changed = graph.lower_qualification(
        "Qualification", {"label": "Poisson", "reporter": "source-A"}
    )
    assert changed != meaning_a


def test_current_rich_fact_identity_uses_actual_property_and_qualification_meaning(source):
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.rich_fact_graph import RichFactGraph

    prepared, model = source
    context = SubjectContext(
        project_id="actual-project",
        subject="universe",
        subject_definition="knowledge-universe",
        original_source=None,
        analyzed_scope=json_bytes({"selection": "closed"}),
    )
    graph = RichFactGraph(
        prepared,
        model,
        context=context,
        entities={"entity:subject": frozenset({"urn:rich-values:Measurement"})},
        known_fact_ids=frozenset(),
    )
    first = graph.add_property_fact(
        subject_entity="entity:subject",
        class_name="Measurement",
        property_name="amount",
        value=Decimal("12.30"),
        qualification={"label": "Gaussian", "reporter": "source-A"},
    )
    second = graph.add_property_fact(
        subject_entity="entity:subject",
        class_name="Measurement",
        property_name="amount",
        value=Decimal("12.300"),
        qualification={"label": "GAUSSIAN", "reporter": "source-B"},
    )
    assert first.fact == second.fact
    assert first.observed_qualification_value != second.observed_qualification_value
    assert graph.facts == (first.fact,)
    assert first.fact.predicate == next(
        prop.iri
        for prop in prepared.index.definitions["Measurement"].properties
        if prop.name == "amount"
    )
    changed = graph.add_property_fact(
        subject_entity="entity:subject",
        class_name="Measurement",
        property_name="amount",
        value=Decimal("12.31"),
        qualification={"label": "Gaussian", "reporter": "source-A"},
    )
    assert changed.fact.fact_id != first.fact.fact_id
    before = graph.values
    with pytest.raises(ValueError, match="selected entity universe"):
        graph.add_property_fact(
            subject_entity="entity:subject",
            class_name="Measurement",
            property_name="reference",
            value="entity:outside",
            qualification={"label": "Gaussian"},
        )
    assert graph.values == before
    assert len(graph.facts) == 2
    with pytest.raises(ValueError, match="class membership"):
        graph.add_property_fact(
            subject_entity="entity:subject",
            class_name="Measurement",
            property_name="reference",
            value="entity:subject",
            qualification={"label": "Gaussian"},
        )
    assert graph.values == before


def test_rich_fact_subject_context_is_a_real_determinant_and_property_null_stays_refused(source):
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.rich_fact_graph import RichFactGraph

    prepared, model = source

    def graph(subject):
        return RichFactGraph(
            prepared,
            model,
            context=SubjectContext(
                project_id="actual-project",
                subject=subject,
                subject_definition="knowledge-universe",
                original_source=None,
                analyzed_scope=b"{}",
            ),
            entities={"entity:subject": frozenset({"urn:rich-values:Measurement"})},
            known_fact_ids=frozenset(),
        )

    first, second = graph("knowledge-A"), graph("knowledge-B")
    kwargs = dict(
        subject_entity="entity:subject",
        class_name="Measurement",
        property_name="note",
        value="",
        qualification={"label": "Gaussian"},
    )
    a, b = first.add_property_fact(**kwargs), second.add_property_fact(**kwargs)
    assert a.fact.fact_id != b.fact.fact_id
    with pytest.raises(ValidationError):
        first.add_property_fact(**{**kwargs, "property_name": "optional_ref", "value": None})


def actual_graph(source):
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.rich_fact_graph import RichFactGraph
    from corpus_structure.semantic.rich_knowledge_contracts import (
        DdoRichContext,
        DdoRichEntity,
        DdoRichOccurrence,
        DdoRichPacket,
        DdoRichSelectedMember,
        RichGraphAssembly,
    )

    prepared, model = source
    context = SubjectContext(
        "project:actual", "knowledge:actual", None, b"{}", subject_definition="knowledge-universe"
    )
    ids = {item.owner: item.key for item in model.identities if item.domain == "kind"}
    prefix = "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/"
    from corpus_structure.semantic.data_operation_support import ComputationalSupportReference

    selected_support = (
        ComputationalSupportReference(
            kind="computation", derivation_id="derivation:actual", admission_use_id="use:actual"
        ),
    )
    entity_ref = DdoRichSelectedMember(
        product_id="selected:known-entities",
        member_id="entity:subject",
        kind_contract=ids[prefix + "DdoRichEntity"],
        support_references=selected_support,
    )
    claim_ref = DdoRichSelectedMember(
        product_id="selected:authored-fact",
        member_id="fact:source",
        kind_contract=ids[prefix + "DdoRichFact"],
        support_references=selected_support,
    )
    values = RichFactGraph(
        prepared,
        model,
        context=context,
        entities={"entity:subject": frozenset({"urn:rich-values:Measurement"})},
        known_fact_ids=frozenset(),
    )
    result = values.add_property_fact(
        subject_entity="entity:subject",
        class_name="Measurement",
        property_name="amount",
        value=Decimal("12.3"),
        qualification={"label": "Gaussian", "reporter": "original-source"},
    )
    entity = DdoRichEntity(
        member_type="entity",
        entity_id="entity:subject",
        class_contracts=(ids["urn:rich-values:Measurement"],),
        identities=(
            {
                "class_contract": ids["urn:rich-values:Measurement"],
                "fields": (),
                "source_context": None,
                "label": None,
            },
        ),
        source_members=(entity_ref,),
    )
    occurrence = DdoRichOccurrence(
        member_type="source-occurrence",
        occurrence_id="occurrence:actual",
        fact_id=result.fact.fact_id,
        original=claim_ref,
        statement=None,
        observed_qualification_value=result.observed_qualification_value,
        dependencies=(),
        establishment="stated",
        statement_kind=None,
        statement_role=None,
        evidence_count=1,
    )
    bodies = (
        *((value.value_id, value) for value in values.values),
        (entity.entity_id, entity),
        (result.fact.fact_id, result.fact),
        (occurrence.occurrence_id, occurrence),
    )
    packets = tuple(
        DdoRichPacket(
            member_id=identifier,
            kind_contract=ids[prefix + type(body).__name__],
            context=DdoRichContext(
                subject=context.subject,
                subject_definition=context.subject_definition,
                original_source=None,
                analyzed_scope={},
            ),
            body=body,
        )
        for identifier, body in bodies
    )
    inputs = (entity_ref, claim_ref)
    return context, RichGraphAssembly(members=packets, input_population=inputs), inputs


def test_finite_rich_graph_validator_checks_real_member_property_range_and_source_links(source):
    from corpus_structure.semantic.rich_graph_validation import validate_rich_graph

    prepared, model = source
    context, graph, inputs = actual_graph(source)
    checked = validate_rich_graph(prepared, model, context=context, graph=graph, inputs=inputs)
    assert checked == graph
    from corpus_structure.semantic.rich_knowledge_contracts import RichGraphAssembly

    assert isinstance(checked, RichGraphAssembly)
    from corpus_structure.semantic.data_operation_ports import project_product_members

    projected = project_product_members(
        model,
        "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/DdoRichConsolidation",
        contract_consolidation(checked),
    )
    assert len(projected) == len(checked.members)
    assert {__import__("json").loads(item)["member_id"] for item in projected} == {
        packet.member_id for packet in checked.members
    }


@pytest.mark.parametrize(
    "defect",
    [
        "dangling-value",
        "different-range",
        "nominal-header",
        "source-possession",
        "wrong-context",
        "body-identity",
        "provenance-equality",
        "wrong-property-owner",
    ],
)
def test_finite_rich_graph_validator_refuses_lookalike_ids_and_unselected_or_wrong_typed_relations(
    source, defect
):
    from corpus_structure.semantic.rich_graph_validation import validate_rich_graph
    from corpus_structure.semantic.rich_knowledge_contracts import (
        DdoRichFact,
        DdoRichOccurrence,
        DdoRichPropertyValue,
        DdoRichQualificationMeaning,
    )

    prepared, model = source
    context, graph, inputs = actual_graph(source)
    packets = list(graph.members)
    ids = {item.owner: item.key for item in model.identities if item.domain == "kind"}
    for index, packet in enumerate(packets):
        body = packet.body
        if defect == "dangling-value" and isinstance(body, DdoRichFact):
            packets[index] = packet.model_copy(
                update={
                    "body": body.model_copy(
                        update={"object_value": "rich-value:same-looking-unselected"}
                    )
                }
            )
            break
        if (
            defect == "different-range"
            and isinstance(body, DdoRichScalarValue)
            and body.datatype == "decimal"
        ):
            packets[index] = packet.model_copy(
                update={
                    "body": body.model_copy(
                        update={"kind_contract": ids["type:urn:rich-values#string"]}
                    )
                }
            )
            break
        if defect == "nominal-header" and isinstance(body, DdoRichFact):
            packets[index] = packet.model_copy(
                update={
                    "kind_contract": ids[
                        "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/DdoRichEntity"
                    ]
                }
            )
            break
        if defect == "source-possession" and isinstance(body, DdoRichOccurrence):
            packets[index] = packet.model_copy(
                update={
                    "body": body.model_copy(
                        update={
                            "original": body.original.model_copy(
                                update={"product_id": "unselected:source"}
                            )
                        }
                    )
                }
            )
            break
        if defect == "wrong-context":
            packets[index] = packet.model_copy(
                update={
                    "context": packet.context.model_copy(update={"subject": "another-universe"})
                }
            )
            break
        if defect == "body-identity" and isinstance(body, DdoRichFact):
            packets[index] = packet.model_copy(
                update={"body": body.model_copy(update={"fact_id": "rich-fact:unowned"})}
            )
            break
        if defect == "provenance-equality" and isinstance(body, DdoRichQualificationMeaning):
            packets[index] = packet.model_copy(
                update={
                    "body": body.model_copy(
                        update={
                            "fields": (
                                DdoRichPropertyValue(
                                    property_contract=ids[
                                        "urn:rich-values:Qualification/property/reporter"
                                    ],
                                    value_id=body.fields[0].value_id,
                                ),
                            )
                        }
                    )
                }
            )
            break
        if defect == "wrong-property-owner" and isinstance(body, DdoRichQualificationMeaning):
            packets[index] = packet.model_copy(
                update={
                    "body": body.model_copy(
                        update={
                            "fields": (
                                DdoRichPropertyValue(
                                    property_contract=ids[
                                        "urn:rich-values:Measurement/property/note"
                                    ],
                                    value_id=body.fields[0].value_id,
                                ),
                            )
                        }
                    )
                }
            )
            break
    else:
        raise AssertionError("independent invalid fixture did not identify its intended member")
    invalid = graph.model_copy(update={"members": tuple(packets)})
    with pytest.raises(ValueError):
        validate_rich_graph(prepared, model, context=context, graph=invalid, inputs=inputs)


def test_record_property_contracts_preserve_distinct_alias_fields_sharing_a_predicate_iri(source):
    prepared, model = source
    graph = RichValueGraph(prepared, model)
    identifier = graph.lower_record("Detail", {"label": "first", "alias": "second"})
    props = prepared.index.definitions["Detail"].properties
    assert len(props) == 2 and props[0].iri == props[1].iri
    rows = {value.value_id: value for value in graph.values}
    record = rows[identifier]
    assert isinstance(record, DdoRichRecordValue)
    actual = {field.property_contract: rows[field.value_id] for field in record.fields}
    ids = {item.owner: item.key for item in model.identities if item.domain == "kind"}
    assert len(actual) == 2
    label = actual[ids["urn:rich-values:Detail/property/label"]]
    alias = actual[ids["urn:rich-values:Detail/property/alias"]]
    assert isinstance(label, DdoRichScalarValue) and isinstance(alias, DdoRichScalarValue)
    assert (label.lexical, alias.lexical) == ("first", "second")


def test_rich_context_pin_uses_shared_json_number_equality_without_collapsing_booleans():
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.rich_knowledge_contracts import rich_context_pin

    def pin(scope):
        return rich_context_pin(
            SubjectContext(
                "project", "knowledge", None, scope, subject_definition="knowledge-universe"
            )
        )

    assert pin(b'{"page":1}') == pin(b'{"page":1.0}')
    assert pin(b'{"page":1}') != pin(b'{"page":true}')


def test_whole_input_member_proof_uses_actual_nominal_members_and_same_support(source):
    from corpus_structure.semantic.rich_graph_validation import RichWholeInput, validate_rich_graph
    from corpus_structure.semantic.rich_knowledge_contracts import (
        DdoRichEntity,
        DdoRichOccurrence,
        DdoRichSelectedMember,
    )

    prepared, model = source
    context, graph, inputs = actual_graph(source)
    root_kind = next(
        item.key
        for item in model.identities
        if item.domain == "kind"
        and item.owner
        == "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/DdoRichConsolidation"
    )
    parent = DdoRichSelectedMember(
        product_id="selected:whole",
        member_id=None,
        kind_contract=root_kind,
        support_references=inputs[0].support_references,
    )
    by_kind = {type(packet.body).__name__: packet for packet in graph.members}

    def reference(name):
        packet = by_kind[name]
        return parent.model_copy(
            update={"member_id": packet.member_id, "kind_contract": packet.kind_contract}
        )

    packets = tuple(
        packet.model_copy(
            update={
                "body": packet.body.model_copy(
                    update={"source_members": (reference("DdoRichEntity"),)}
                )
            }
        )
        if isinstance(packet.body, DdoRichEntity)
        else packet.model_copy(
            update={"body": packet.body.model_copy(update={"original": reference("DdoRichFact")})}
        )
        if isinstance(packet.body, DdoRichOccurrence)
        else packet
        for packet in graph.members
    )
    output = graph.model_copy(update={"members": packets, "input_population": (parent,)})
    proof = (RichWholeInput(parent, contract_consolidation(graph)),)
    assert (
        validate_rich_graph(
            prepared, model, context=context, graph=output, inputs=(parent,), whole_inputs=proof
        )
        == output
    )
    with pytest.raises(ValueError, match="actual selected input"):
        validate_rich_graph(prepared, model, context=context, graph=output, inputs=(parent,))
    # Possessing another member string or a different episode does not prove membership.
    entity = next(packet for packet in output.members if isinstance(packet.body, DdoRichEntity))
    for changed in (
        reference("DdoRichEntity").model_copy(update={"member_id": "entity:unselected"}),
        reference("DdoRichEntity").model_copy(
            update={
                "support_references": (
                    inputs[0]
                    .support_references[0]
                    .model_copy(update={"derivation_id": "other-episode"}),
                )
            }
        ),
    ):
        forged = entity.model_copy(
            update={"body": entity.body.model_copy(update={"source_members": (changed,)})}
        )
        invalid = output.model_copy(
            update={
                "members": tuple(
                    forged if item.member_id == entity.member_id else item
                    for item in output.members
                )
            }
        )
        with pytest.raises(ValueError, match="actual selected input"):
            validate_rich_graph(
                prepared,
                model,
                context=context,
                graph=invalid,
                inputs=(parent,),
                whole_inputs=proof,
            )
    with pytest.raises(ValueError, match="input population"):
        validate_rich_graph(
            prepared,
            model,
            context=context,
            graph=output.model_copy(
                update={"input_population": (parent, reference("DdoRichEntity"))}
            ),
            inputs=(parent,),
            whole_inputs=proof,
        )


def test_selected_rich_reference_requires_actual_support_and_normalizes_population():
    from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
    from corpus_structure.semantic.rich_knowledge_contracts import DdoRichSelectedMember

    a = ComputationalSupportReference(
        kind="computation", derivation_id="episode:a", admission_use_id="use:a"
    )
    b = ComputationalSupportReference(
        kind="computation", derivation_id="episode:b", admission_use_id="use:b"
    )
    fields = dict(product_id="product:actual", member_id=None, kind_contract="kind:actual")
    with pytest.raises(ValidationError):
        DdoRichSelectedMember(**fields, support_references=())
    assert DdoRichSelectedMember(**fields, support_references=(a, b, a)) == DdoRichSelectedMember(
        **fields, support_references=(b, a)
    )


def test_rich_reading_decision_does_not_invent_unavailable_resolution():
    from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
    from corpus_structure.semantic.rich_knowledge_contracts import (
        DdoRichReadingDecision,
        DdoRichSelectedMember,
    )

    support = (
        ComputationalSupportReference(
            kind="computation", derivation_id="episode:actual", admission_use_id="use:actual"
        ),
    )
    raw = DdoRichSelectedMember(
        product_id="product:raw",
        member_id="member:raw",
        kind_contract="kind:record",
        support_references=support,
    )
    fields = dict(
        original=raw,
        resolution=None,
        resolved=None,
        record_id="record:actual",
        source_interpretation_id="interpretation:raw",
        interpretation_id=None,
        authorization=None,
        outcome="not-checkable",
        feature_input_digest=None,
        feature_instance_digest=None,
        event_procedure=None,
        score_hex=None,
        probability_hex=None,
        reason_code="resolution-unavailable",
        assertion_member_id=None,
    )
    assert DdoRichReadingDecision.model_validate(fields).interpretation_id is None
    for change in (
        {"outcome": "accepted"},
        {"interpretation_id": "interpretation:invented"},
        {"resolved": raw},
        {"score_hex": (0.5).hex()},
    ):
        with pytest.raises(ValidationError):
            DdoRichReadingDecision.model_validate({**fields, **change})


def test_entity_identity_bases_retain_actual_declared_key_values_and_refuse_other_fields(source):
    from corpus_structure.semantic.rich_graph_validation import validate_rich_graph
    from corpus_structure.semantic.rich_knowledge_contracts import (
        DdoRichEntity,
        DdoRichEntityIdentity,
        DdoRichPacket,
        DdoRichPropertyValue,
    )

    prepared, model = source
    context, graph, inputs = actual_graph(source)
    ids = {item.owner: item.key for item in model.identities if item.domain == "kind"}
    values = RichValueGraph(prepared, model)
    key = values.lower_property("KeyedEntity", "code", "retained-key")
    original = next(packet for packet in graph.members if isinstance(packet.body, DdoRichEntity))
    original_body = original.body
    assert isinstance(original_body, DdoRichEntity)
    basis = DdoRichEntityIdentity(
        class_contract=ids["urn:rich-values:KeyedEntity"],
        fields=(
            DdoRichPropertyValue(
                property_contract=ids["urn:rich-values:KeyedEntity/property/code"], value_id=key
            ),
        ),
        source_context=None,
        label="Observed label",
    )
    entity = original.model_copy(
        update={
            "body": original_body.model_copy(
                update={
                    "class_contracts": (*original_body.class_contracts, basis.class_contract),
                    "identities": (*original_body.identities, basis),
                }
            )
        }
    )
    added = tuple(
        DdoRichPacket(
            member_id=value.value_id,
            kind_contract=ids[
                "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/"
                + type(value).__name__
            ],
            context=original.context,
            body=value,
        )
        for value in values.values
    )
    actual = graph.model_copy(
        update={
            "members": tuple(
                entity if packet.member_id == entity.member_id else packet
                for packet in graph.members
            )
            + added
        }
    )
    assert (
        validate_rich_graph(prepared, model, context=context, graph=actual, inputs=inputs) == actual
    )
    entity_body = entity.body
    assert isinstance(entity_body, DdoRichEntity)
    for field in (
        basis.fields[0].model_copy(
            update={"property_contract": ids["urn:rich-values:Measurement/property/amount"]}
        ),
        basis.fields[0].model_copy(update={"value_id": "value:unselected"}),
    ):
        changed = entity.model_copy(
            update={
                "body": entity_body.model_copy(
                    update={
                        "identities": (
                            *original_body.identities,
                            basis.model_copy(update={"fields": (field,)}),
                        )
                    }
                )
            }
        )
        invalid = actual.model_copy(
            update={
                "members": tuple(
                    changed if packet.member_id == entity.member_id else packet
                    for packet in actual.members
                )
            }
        )
        with pytest.raises(ValueError):
            validate_rich_graph(prepared, model, context=context, graph=invalid, inputs=inputs)


def contract_consolidation(graph):
    """Controlled schema container; this fixture claims no computed/native eligibility."""
    from corpus_structure.semantic.rich_decisions import DdoRichEligibility
    from corpus_structure.semantic.rich_knowledge_contracts import DdoRichConsolidation

    return DdoRichConsolidation(
        version="rich-consolidation-1",
        standing="private-consolidated",
        members=graph.members,
        input_population=graph.input_population,
        eligibility=DdoRichEligibility(
            eligibility_policy_digest="e" * 64,
            selected_fact_ids=(),
            selected_occurrence_ids=(),
            scientific_representatives=(),
        ),
    )


def contract_selection(members):
    """Independent declared selection data for decoder tests, never native authority."""
    from corpus_structure.semantic.rich_decisions import DdoRichScientificRepresentative
    from corpus_structure.semantic.rich_knowledge_contracts import (
        DdoRichFact,
        DdoRichOccurrence,
        DdoRichSourceReadingAssertion,
    )

    facts = tuple(
        sorted(packet.member_id for packet in members if isinstance(packet.body, DdoRichFact))
    )
    return dict(
        eligibility_policy_digest="e" * 64,
        selected_fact_ids=facts,
        selected_occurrence_ids=tuple(
            sorted(
                packet.member_id for packet in members if isinstance(packet.body, DdoRichOccurrence)
            )
        ),
        selected_reading_ids=tuple(
            sorted(
                packet.member_id
                for packet in members
                if isinstance(packet.body, DdoRichSourceReadingAssertion)
            )
        ),
        scientific_representatives=tuple(
            DdoRichScientificRepresentative(
                fact_id=value,
                representative_fact_id=value,
                component_id="component:" + value,
                policy="min-fact-id-1",
            )
            for value in facts
        ),
    )
