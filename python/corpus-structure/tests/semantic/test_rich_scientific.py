"""Independent scientific outcomes over actual compiled current rich graphs."""

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from corpus_structure.core.evidence import MacroDef
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.analysis_contracts import acquire_analysis_context_profile
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
from corpus_structure.semantic.expression_context import bind_expression_context
from corpus_structure.semantic.rich_fact_graph import RichFactGraph
from corpus_structure.semantic.rich_graph_validation import RichWholeInput
from corpus_structure.semantic.rich_knowledge_contracts import (
    DdoRichConsolidation, RichGraphAssembly, DdoRichContext, DdoRichEntity, DdoRichOccurrence,
    DdoRichPacket, DdoRichSelectedMember,
)
from corpus_structure.semantic.rich_knowledge_sources import rich_knowledge_inputs, rich_knowledge_declarations
from corpus_structure.semantic.rich_rules import RichRulePolicy
from corpus_structure.semantic.rich_scientific import RichScientificSourceContext, assess_rich_scientific
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.scientific_evidence import parse_scientific_assessment_reason, SCIENTIFIC_POLICY_INPUT
from corpus_structure.semantic.types import ResolvedDependencies
from semantic.data_operation_declaration_support import contract, declarations
from semantic.record_contracts_support import release_inputs
from semantic.test_external_rich_extraction import packet

PREFIX = "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/"
PACKET = "https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoExternalExtractionPacket"


@pytest.fixture(scope="module")
def scientific():
    root = Path(__file__).resolve().parents[4]
    profile = acquire_analysis_context_profile()
    bundle, dependencies = rich_knowledge_inputs(
        release_inputs()[0], ResolvedDependencies(),
        domain_rules=(root / "domains/statistics/schema/rules.yaml").read_bytes(),
        core_rules=(root / "domains/core/schema/rules.yaml").read_bytes(),
        context_profile=profile, qualification_class="StatisticsQualification", statement_class="SourceStatement",
    )
    source = SourceArtifact("scientific-example", ("""id: urn:rich-scientific
name: rich_scientific
imports: [SOURCE_ROOT]
prefixes: {r: 'urn:rich-scientific:'}
default_prefix: r
classes:
  ScientificSubject:
    is_a: Entity
    attributes:
      value:
        range: Value
        inlined: true
        multivalued: true
        annotations: {cs:constraint_scope: accepted_value, cs:role: predicate, cs:functional: true}
      observations:
        range: Value
        inlined: true
        multivalued: true
        annotations: {cs:constraint_scope: accepted_value, cs:role: predicate}
""".replace("SOURCE_ROOT", bundle.root)).encode())
    bundle = SourceBundle(source.name, (*bundle.sources, source))
    operation = contract(subject="knowledge-universe", subject_definition={"id": "knowledge-universe", "identifier_kind": "string", "scope": "project"})
    model = compile_data_operations(bundle, declarations=(*rich_knowledge_declarations(dependencies), *declarations(operation)))
    prepared = prepare_release(bundle, dependencies)
    return prepared, model, profile, RichRulePolicy(prepared)


def graph_inputs(scientific, values, *, qualifications=None, macros=None, property_name="value"):
    prepared, model, _, _ = scientific
    context = SubjectContext("project:actual", "knowledge:actual", None, b'{}', subject_definition="knowledge-universe")
    ids = {item.owner: item.key for item in model.identities if item.domain == "kind"}
    graph = RichFactGraph(prepared, model, context=context, entities={"entity:actual": frozenset({"urn:rich-scientific:ScientificSubject"})}, known_fact_ids=frozenset())
    bodies, inputs, contexts, whole_inputs = {}, [], [], []
    for index, value in enumerate(values):
        support = (ComputationalSupportReference(derivation_id=f"episode:source:{index}", admission_use_id=f"use:source:{index}"),)
        original = DdoRichSelectedMember(product_id=f"product:proposal:{index}", member_id=f"claim:{index}", kind_contract=ids[PREFIX + "DdoRichFact"], support_references=support)
        packet_ref = DdoRichSelectedMember(product_id=f"product:packet:{index}", member_id=None, kind_contract=ids[PACKET], support_references=support)
        actual_macros = macros[index] if macros is not None else {}
        body = packet()
        body["macros"] = source_value({name: item.model_dump(mode="python") for name, item in actual_macros.items()})
        # The kernel checks the actual bound typed packet, rather than accepting
        # a free macros dictionary as scientific authority.
        whole_inputs.append(RichWholeInput(packet_ref, prepared.validate_json("DdoExternalExtractionPacket", json_bytes(body))))
        contexts.append(RichScientificSourceContext(original=original, context=packet_ref, macros=actual_macros))
        inputs.extend((original, packet_ref))
        qualification = qualifications[index] if qualifications else {"modality": "asserted", "polarity": True}
        result = graph.add_property_fact(subject_entity="entity:actual", class_name="ScientificSubject", property_name=property_name,
                                         value=bind_expression_context(value, actual_macros), qualification=qualification)
        occurrence = DdoRichOccurrence(member_type="source-occurrence", occurrence_id=f"occurrence:{index}", fact_id=result.fact.fact_id,
                                       original=original, statement=None, observed_qualification_value=result.observed_qualification_value, dependencies=(), establishment="stated", statement_kind=None, statement_role=None, evidence_count=1)
        bodies[result.fact.fact_id] = result.fact
        bodies[occurrence.occurrence_id] = occurrence
    entity = DdoRichEntity(member_type="entity", entity_id="entity:actual", class_contracts=(ids["urn:rich-scientific:ScientificSubject"],), identities=({"class_contract": ids["urn:rich-scientific:ScientificSubject"], "fields": (), "label": None},), source_members=(inputs[0],))
    bodies[entity.entity_id] = entity
    bodies.update((value.value_id, value) for value in graph.values)
    packets = tuple(DdoRichPacket(member_id=identifier, kind_contract=ids[PREFIX + type(body).__name__], context=DdoRichContext(subject=context.subject, subject_definition=context.subject_definition, original_source=None, analyzed_scope={}), body=body) for identifier, body in sorted(bodies.items()))
    return dict(context=context, graph=RichGraphAssembly(members=packets, input_population=tuple(inputs)),
                inputs=tuple(inputs), source_contexts=tuple(contexts), whole_inputs=tuple(whole_inputs))


def assess(scientific, inputs):
    prepared, model, profile, policy = scientific
    return assess_rich_scientific(prepared, model, policy=policy, context_profile=profile, **inputs)


def formula(expression, binding="variable"):
    return {"kind": "formula", "language": "latex", "expression": expression, "bindings": [{"kind": binding, "symbol": "x", **({"entity": "entity:actual"} if binding == "variable" else {})}]}


@pytest.mark.parametrize("values,expected", [
    (({"kind": "text", "text": "Gaussian"}, {"kind": "text", "text": " GAUSSIAN "}), "equivalent"),
    (({"kind": "number", "number": Decimal("1")}, {"kind": "number", "number": Decimal("2")}), "different"),
    ((formula("x+x"), formula("2x")), "equivalent"),
    ((formula("x", "unresolved"), formula("x+0", "unresolved")), "undecided"),
])
def test_current_scientific_outcomes_keep_canonical_symbolic_and_unknown_distinct(scientific, values, expected):
    inputs = graph_inputs(scientific, values)
    result = assess(scientific, inputs)
    assert len(result) == 1
    assert result[0].outcome == expected
    assert result[0].occurrences == ("occurrence:0", "occurrence:1")
    assert {item.product_id for item in result[0].evidence_members} == {"product:proposal:0", "product:proposal:1", "product:packet:0", "product:packet:1"}
    reason = parse_scientific_assessment_reason(result[0].reason)
    assert reason is not None
    assert reason.policy == "consolidation-evidence-2"
    assert reason.tier == ("undecided" if expected == "undecided" else "symbolic" if values[0].get("kind") == "formula" else "canonical")
    reordered = {**inputs, "graph": inputs["graph"].model_copy(update={"members": tuple(reversed(inputs["graph"].members))}), "source_contexts": tuple(reversed(inputs["source_contexts"]))}
    assert assess(scientific, reordered) == result


def test_scientific_scope_and_functionality_are_real_boundaries_and_one_fact_needs_no_comparison(scientific):
    values = ({"kind": "number", "number": Decimal("1")}, {"kind": "number", "number": Decimal("2")})
    qualifiers = ({"modality": "asserted", "polarity": True}, {"modality": "supposed", "polarity": True})
    assert assess(scientific, graph_inputs(scientific, values, qualifications=qualifiers)) == ()
    assert assess(scientific, graph_inputs(scientific, values, property_name="observations")) == ()
    assert assess(scientific, graph_inputs(scientific, (values[0], values[0]))) == ()


def test_scientific_source_macros_require_actual_packet_correspondence_and_preserve_conflict_unknown(scientific):
    contexts = ({"\\F": MacroDef(body="x")}, {"\\F": MacroDef(body="x+1")})
    inputs = graph_inputs(scientific, (formula("\\F"), formula("\\F")), macros=contexts)
    result = assess(scientific, inputs)
    assert result[0].outcome == "undecided"
    assert "incompatible referenced" in result[0].reason
    bad_context = inputs["source_contexts"][0].model_copy(update={"macros": {}})
    with pytest.raises(ValueError, match="differ from the actual selected packet"):
        assess(scientific, {**inputs, "source_contexts": (bad_context, inputs["source_contexts"][1])})
    with pytest.raises(ValueError, match="explicit selected source context"):
        assess(scientific, {**inputs, "source_contexts": ()})
    with pytest.raises(ValueError, match="actual selected packet body"):
        assess(scientific, {**inputs, "whole_inputs": ()})


def test_scientific_requires_captured_policy_and_exact_closed_graph(scientific):
    inputs = graph_inputs(scientific, (formula("x"), formula("x+0")))
    prepared, model, profile, _ = scientific
    changed = replace(prepared, artifacts=tuple(item for item in prepared.artifacts if item.kind != SCIENTIFIC_POLICY_INPUT))
    with pytest.raises(ValueError, match="recipe is unsupported"):
        assess_rich_scientific(changed, model, policy=RichRulePolicy(changed), context_profile=profile, **inputs)
    occurrence = next(packet for packet in inputs["graph"].members if isinstance(packet.body, DdoRichOccurrence))
    forged = occurrence.model_copy(update={"body": occurrence.body.model_copy(update={"fact_id": "fact:unselected"})})
    graph = inputs["graph"].model_copy(update={"members": tuple(forged if packet.member_id == occurrence.member_id else packet for packet in inputs["graph"].members)})
    with pytest.raises(ValueError, match="actual local member kind"):
        assess(scientific, {**inputs, "graph": graph})


def test_reading_fidelity_cannot_be_lowered_into_a_scientific_fact(scientific):
    prepared, model, _, _ = scientific
    definition = prepared.index.definitions["DefinitionReading"]
    context = SubjectContext("project:actual", "knowledge:actual", None, b'{}', subject_definition="knowledge-universe")
    graph = RichFactGraph(prepared, model, context=context,
                          entities={"reading:actual": frozenset({definition.iri})}, known_fact_ids=frozenset())
    with pytest.raises(ValueError, match="source readings require their distinct assertion"):
        graph.add_property_fact(subject_entity="reading:actual", class_name="DefinitionReading", property_name="label",
                                value="A faithful quotation is not a scientific conclusion", qualification={"modality": "asserted", "polarity": True})
    assert graph.facts == ()


def test_actual_authored_propositions_supply_explicit_interpretation_without_a_synthetic_packet(scientific):
    from corpus_structure.semantic.data_operation_identity import canonical_identity
    from corpus_structure.semantic.data_operation_support import AuthoredFactSupportReference
    from corpus_structure.semantic.rich_knowledge_contracts import DdoRichAuthoredProposition, DdoRichAuthoredPacket, DdoRichAuthoredPropositions

    inputs = graph_inputs(scientific, ({"kind": "number", "number": Decimal("1")}, {"kind": "number", "number": Decimal("2")}))
    _, model, _, _ = scientific
    ids = {item.owner: item.key for item in model.identities if item.domain == "kind"}
    authored_packets, originals = [], {}
    for packet_value in inputs["graph"].members:
        body = packet_value.body
        if isinstance(body, DdoRichEntity):
            body = body.model_copy(update={"source_members": ()})
        if isinstance(body, DdoRichOccurrence):
            key = canonical_identity("rich-authored-proposition", [inputs["context"].identity_record, body.fact_id, body.observed_qualification_value, sorted(set(body.dependencies))]).key
            body = DdoRichAuthoredProposition(member_type="authored-proposition", proposition_id=key, fact_id=body.fact_id,
                                             observed_qualification_value=body.observed_qualification_value, dependencies=body.dependencies)
            originals[packet_value.member_id] = key
        identifier = body.proposition_id if isinstance(body, DdoRichAuthoredProposition) else packet_value.member_id
        authored_packets.append(DdoRichAuthoredPacket(member_id=identifier, kind_contract=ids[PREFIX + type(body).__name__], context=packet_value.context, body=body))
    authored = DdoRichAuthoredPropositions(version="rich-authored-propositions-1", standing="authored-propositions", members=tuple(authored_packets), macros={})
    reference = DdoRichSelectedMember(product_id="product:authored-domain", member_id=None, kind_contract=ids[PREFIX + "DdoRichAuthoredPropositions"],
                                      support_references=(AuthoredFactSupportReference(admission_id="admission:authored", source_reference="authored:domain"),))
    contexts, packets = [], []
    for packet_value in inputs["graph"].members:
        body = packet_value.body
        if isinstance(body, DdoRichEntity):
            body = body.model_copy(update={"source_members": (reference.model_copy(update={"member_id": body.entity_id, "kind_contract": ids[PREFIX + "DdoRichEntity"]}),)})
        elif isinstance(body, DdoRichOccurrence):
            original = reference.model_copy(update={"member_id": originals[body.occurrence_id], "kind_contract": ids[PREFIX + "DdoRichAuthoredProposition"]})
            body = body.model_copy(update={"original": original})
            contexts.append(RichScientificSourceContext(original=original, context=reference, macros={}))
        packets.append(packet_value.model_copy(update={"body": body}))
    actual = {**inputs, "graph": inputs["graph"].model_copy(update={"members": tuple(packets), "input_population": (reference,)}),
              "inputs": (reference,), "whole_inputs": (RichWholeInput(reference, authored),), "source_contexts": tuple(contexts)}
    result = assess(scientific, actual)
    assert result[0].outcome == "different" and result[0].severity is None
    assert {item.product_id for item in result[0].evidence_members} == {reference.product_id}
    assert all(item.support_references[0].kind == "authored" for item in result[0].evidence_members)


def test_known_known_comparisons_preserve_prior_assessment_but_new_known_requires_actual_context(scientific):
    from corpus_structure.semantic.rich_knowledge_contracts import DdoRichAdmission
    inputs = graph_inputs(scientific, ({"kind": "number", "number": Decimal("1")}, {"kind": "number", "number": Decimal("2")}))
    _, model, _, _ = scientific
    ids = {item.owner: item.key for item in model.identities if item.domain == "kind"}
    reference = inputs["inputs"][0].model_copy(update={"product_id": "product:known-admission", "member_id": None, "kind_contract": ids[PREFIX + "DdoRichAdmission"]})
    consolidation = reference.model_copy(update={"product_id": "historical:consolidation", "kind_contract": "historical:consolidation-kind"})
    from semantic.test_rich_value_graph import contract_selection
    root = DdoRichAdmission(**contract_selection(inputs["graph"].members),version="rich-admission-1", standing="accepted", members=inputs["graph"].members, consolidation=consolidation, policy_authorizations=(), reading_decisions=())
    retained = RichWholeInput(reference, root)
    graph = inputs["graph"].model_copy(update={"input_population": (reference,)})
    actual = {**inputs, "graph": graph, "inputs": (reference,), "source_contexts": (), "whole_inputs": (retained,), "retained_graphs": (retained,)}
    assert assess(scientific, actual) == ()
    prior_members = tuple(item for item in root.members if item.member_id != "occurrence:1")
    prior = root.model_copy(update={"members": prior_members, **contract_selection(prior_members)})
    retained = RichWholeInput(reference, prior)
    fresh = inputs["source_contexts"][1]
    selected = (reference, fresh.original, fresh.context)
    graph = graph.model_copy(update={"input_population": selected})
    actual = {**actual, "graph": graph, "inputs": selected, "source_contexts": (fresh,),
              "whole_inputs": (retained, inputs["whole_inputs"][1]), "retained_graphs": (retained,)}
    with pytest.raises(ValueError, match="explicit selected source context"):
        assess(scientific, actual)
