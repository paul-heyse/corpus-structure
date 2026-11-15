"""Finite current rich graph invariants over real nominal members and selected inputs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from .data_operation_identity import canonical_identity, semantic_value
from .data_operation_json import json_bytes, json_loads
from .data_operation_model import EffectiveDataOperationModel, SubjectContext, validate_subject_context
from .data_operation_ports import _untrusted_value
from .data_operation_wire import validate_wire_schema
from .rich_knowledge_contracts import (
    DdoRichAdmission, DdoRichAuthoredPropositions, DdoRichAuthoredProposition, DdoRichAlternative, DdoRichAssessment, DdoRichCasefoldText,
    DdoRichCollectionValue, DdoRichConsolidation, DdoRichDiagnostic, DdoRichEntity,
    DdoRichEntityValue, DdoRichFact, DdoRichOccurrence, DdoRichQualificationMeaning,
    DdoRichRecordValue, DdoRichScalarValue, DdoRichSelectedMember,
    DdoRichSourceReadingAssertion, DdoRichIdentityResolution, DdoRichIdentityExclusion, DdoRichOccurrenceDecision, RichGraphAssembly,
    rich_reference_key,
)
from .types import PreparedRelease
from .unicode_identity import identity_casefold

_NAMESPACE = "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/"
_VALUES = (DdoRichScalarValue, DdoRichEntityValue, DdoRichRecordValue, DdoRichCollectionValue, DdoRichQualificationMeaning, DdoRichCasefoldText)
_ORDINARY_VALUES = (DdoRichScalarValue, DdoRichEntityValue, DdoRichRecordValue)


@dataclass(frozen=True)
class RichWholeInput:
    """An actual selected whole value, supplied by the prepared binding owner."""
    reference: DdoRichSelectedMember
    value: Any


def _body_id(body) -> str:
    if isinstance(body, _VALUES):
        return body.value_id
    if isinstance(body, DdoRichEntity):
        return body.entity_id
    if isinstance(body, DdoRichFact):
        return body.fact_id
    if isinstance(body, DdoRichOccurrence):
        return body.occurrence_id
    if isinstance(body, DdoRichAuthoredProposition):
        return body.proposition_id
    if isinstance(body, DdoRichSourceReadingAssertion):
        return body.reading_id
    if isinstance(body, DdoRichAlternative):
        return body.alternative_id
    if isinstance(body, DdoRichAssessment):
        return body.assessment_id
    if isinstance(body, DdoRichDiagnostic):
        return body.diagnostic_id
    if isinstance(body, DdoRichIdentityResolution):
        return body.resolution_id
    if isinstance(body, DdoRichOccurrenceDecision):
        return body.decision_id
    if isinstance(body, DdoRichIdentityExclusion):
        return body.exclusion_id
    raise ValueError("rich member has no declared current identity owner")


def _meaning(value):
    from .identity import canonical_bytes
    return canonical_bytes(semantic_value(_untrusted_value(value)))


def _references(value):
    if isinstance(value, DdoRichSelectedMember):
        yield value
    elif isinstance(value, BaseModel):
        for name in type(value).model_fields:
            yield from _references(getattr(value, name))
    elif isinstance(value, dict):
        for item in value.values():
            yield from _references(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from _references(item)


class ValidatedRichGraph:
    def __init__(self, prepared, model, context, graph, inputs, whole_inputs, retained_states=()):
        self.prepared, self.model, self.context = prepared, model, context
        self.graph = graph
        self.kinds = {kind.semantic_id: kind for kind in model.kinds}
        self.kind_facts = {kind.semantic_id: json.loads(kind.facts) for kind in model.kinds}
        self.properties = {definition.iri + "/property/" + prop.name: (definition, prop)
                           for definition in prepared.definitions for prop in definition.properties}
        self.property_edges = {(edge.source, edge.target) for edge in model.edges if edge.relation == "property"}
        self.range_edges = {}
        for edge in model.edges:
            if edge.relation == "range":
                self.range_edges.setdefault(edge.source, set()).add(edge.target)
        self.ids = {item.owner: item.key for item in model.identities if item.domain == "kind"}
        self.owners = {contract: owner for owner, contract in self.ids.items()}
        self.members = {}
        self.packets = {}
        self._checking_member = None
        self._retained_provenance = {}
        self.retained_roots = tuple(item.selection for item in retained_states)
        self.retained_admissions = tuple(item.graph for item in retained_states)
        self._retained_sources = {}
        self.decoded = {}
        self.active = set()
        self.reached_values = set()
        from .rich_value_graph import RichValueGraph
        self.qualification_projector = RichValueGraph(prepared, model)
        self.qualification_projections = {}
        self.inputs = {rich_reference_key(item) for item in inputs}
        if len(self.inputs) != len(inputs):
            raise ValueError("rich selected input population repeats an actual address")
        observed_inputs = {rich_reference_key(item) for item in graph.input_population} if isinstance(graph, (DdoRichConsolidation, RichGraphAssembly)) else None
        if observed_inputs is not None and (observed_inputs != self.inputs or len(observed_inputs) != len(graph.input_population)):
            raise ValueError("rich graph input population differs from its actual selected inputs")
        self.whole_members = []
        from .data_operation_ports import project_product_members
        for whole in whole_inputs:
            if whole.reference.member_id is not None or rich_reference_key(whole.reference) not in self.inputs:
                raise ValueError("rich whole-input proof differs from its actual binding")
            owner = self.kind(whole.reference.kind_contract)
            packets = tuple(json_loads(packet) for packet in project_product_members(model, owner.semantic_id, whole.value))
            self.whole_members.append((whole.reference, {packet["member_id"]: packet["kind_contract"] for packet in packets}))
        for packet in graph.members:
            if packet.member_id != _body_id(packet.body) or packet.member_id in self.members:
                raise ValueError("rich member identity differs from its body or repeats")
            owner = _NAMESPACE + type(packet.body).__name__
            if owner not in self.ids or packet.kind_contract != self.ids[owner]:
                raise ValueError("rich member body differs from its actual nominal kind")
            facts = self.kind_facts[owner]
            validate_wire_schema(facts["json_schema"], json_loads(json_bytes(packet.body.model_dump(mode="python"))))
            actual = SubjectContext(context.project_id, packet.context.subject, packet.context.original_source,
                                    json_bytes(packet.context.analyzed_scope), subject_definition=packet.context.subject_definition)
            validate_subject_context(model, actual)
            if actual != context:
                raise ValueError("rich member context differs from its actual knowledge subject")
            self.members[packet.member_id] = packet.body
            self.packets[packet.member_id] = packet
            for retained in retained_states:
                original = retained.packets.get(packet.member_id)
                if original is not None and _meaning(original) == _meaning(packet):
                    self._retained_provenance[packet.member_id] = {rich_reference_key(ref) for ref in _references(original.body)}
                    self._retained_sources.setdefault(packet.member_id, {})[rich_reference_key(retained.selection.reference)] = retained.selection.reference

    def retained_sources(self, member_id: str) -> tuple[DdoRichSelectedMember, ...]:
        """Actual current whole roots proving this exact retained packet."""
        sources = self._retained_sources.get(member_id, {})
        return tuple(sources[key] for key in sorted(sources))

    @property
    def retained_member_ids(self) -> frozenset[str]:
        return frozenset(self._retained_provenance)

    def member(self, identifier, classes):
        body = self.members.get(identifier)
        if body is None or not isinstance(body, classes):
            raise ValueError("rich reference lacks its actual local member kind: " + identifier)
        return body

    def external(self, reference):
        key = rich_reference_key(reference)
        if key not in self.inputs:
            if not any(parent.product_id == reference.product_id and parent.support_references == reference.support_references
                       and members.get(reference.member_id) == reference.kind_contract
                       for parent, members in self.whole_members):
                if key in self._retained_provenance.get(self._checking_member, ()):
                    # Only an unchanged packet of an actual selected accepted root
                    # may preserve its embedded opaque historical provenance.
                    return
                raise ValueError("rich source reference differs from an actual selected input or unchanged retained packet")
        self.kind(reference.kind_contract)

    def occurrence_source(self, reference):
        """Identify an unchanged occurrence's original; this grants no input authority."""
        key = rich_reference_key(reference)
        if any(isinstance(packet.body, DdoRichOccurrence)
               and rich_reference_key(packet.body.original) == key
               and key in self._retained_provenance.get(identifier, ())
               for identifier, packet in self.packets.items()):
            return
        self.external(reference)

    def kind(self, contract):
        owner = self.owners.get(contract)
        if owner is None or not self.kinds[owner].complete:
            raise ValueError("rich reference lacks its actual complete kind contract")
        return self.kinds[owner]

    def definition(self, contract):
        kind = self.kind(contract)
        definition = self.prepared.index.definitions.get(kind.name)
        if kind.category != "class" or definition is None or definition.iri != kind.semantic_id:
            raise ValueError("rich value does not name an actual logical class owner")
        return definition

    def property(self, contract, owner=None):
        kind = self.kind(contract)
        if kind.category != "property":
            raise ValueError("rich field does not name an actual property contract")
        if owner is not None and (owner, kind.semantic_id) not in self.property_edges:
            raise ValueError("rich field belongs to a different actual class")
        facts = self.kind_facts[kind.semantic_id]
        target = facts["range"]
        if self.range_edges.get(kind.semantic_id) != {target}:
            raise ValueError("rich property range differs from its actual graph")
        logical = self.properties.get(kind.semantic_id)
        if logical is None:
            raise ValueError("rich property lacks its actual logical owner")
        definition, prop = logical
        return definition, prop, target

    def class_member(self, identifier, expected):
        entity = self.member(identifier, DdoRichEntity)
        definitions = [self.definition(contract) for contract in entity.class_contracts]
        if not any(definition.iri == expected.iri or expected.name in definition.ancestors for definition in definitions):
            raise ValueError("rich entity lacks its actual required class membership")

    def property_value(self, identifier, definition, prop, *, item=False):
        body = self.member(identifier, (*_ORDINARY_VALUES, DdoRichCollectionValue))
        owner = definition.iri + "/property/" + prop.name
        _, _, target = self.property(self.ids[owner], definition.iri)
        if prop.multivalued and not item:
            collection = self.member(identifier, DdoRichCollectionValue)
            if collection.element_contract != self.ids[target]:
                raise ValueError("rich collection element contract differs from its property")
            self.reached_values.add(identifier)
            entries = collection.entries
            if collection.collection == "sequence":
                if [(entry.name, entry.position) for entry in entries] != [("item", index) for index in range(len(entries))]:
                    raise ValueError("rich sequence positions differ from their actual ordering")
                value = tuple(self.value(entry.value_id, target) for entry in entries)
            else:
                if any(entry.position != 0 for entry in entries) or len({entry.name for entry in entries}) != len(entries):
                    raise ValueError("rich mapping repeats or mislabels an actual key")
                value = {entry.name: self.value(entry.value_id, target) for entry in entries}
            expected_id = canonical_identity("rich-value", [collection.collection, collection.element_contract, [entry.model_dump(mode="python") for entry in entries]]).key
            if expected_id != identifier:
                raise ValueError("rich collection identity differs from its actual entries")
        else:
            if isinstance(body, DdoRichCollectionValue):
                raise ValueError("rich scalar property cannot carry a collection")
            value = self.value(identifier, target)
        return self.prepared.property_adapter(definition.name, prop.name, item=item).validate_python(value, strict=True)

    def value(self, identifier, expected=None):
        body = self.member(identifier, _ORDINARY_VALUES)
        self.reached_values.add(identifier)
        actual = self.kind(body.kind_contract)
        if expected is not None and actual.semantic_id != expected:
            target = self.kinds[expected]
            if not isinstance(body, DdoRichRecordValue) or target.name not in self.definition(body.kind_contract).ancestors:
                raise ValueError("rich value contract differs from its actual property range")
        if identifier in self.active:
            raise ValueError("rich value graph contains an ungrounded cycle")
        if identifier in self.decoded:
            return self.decoded[identifier]
        self.active.add(identifier)
        try:
            if isinstance(body, DdoRichScalarValue):
                value = body.lexical if body.datatype == "string" else body.lexical == "true" if body.datatype == "boolean" else {"integer": int, "decimal": Decimal, "float": float.fromhex, "date": date.fromisoformat, "datetime": datetime.fromisoformat}[body.datatype](body.lexical)
                from .value_codec import value_meaning
                expected_id = canonical_identity("rich-value", [body.kind_contract, value_meaning(value)]).key
            elif isinstance(body, DdoRichEntityValue):
                self.class_member(body.entity_id, self.definition(body.kind_contract))
                value = body.entity_id
                expected_id = canonical_identity("rich-value", ["entity", body.kind_contract, value]).key
            else:
                definition = self.definition(body.kind_contract)
                if len({field.property_contract for field in body.fields}) != len(body.fields):
                    raise ValueError("rich record repeats an actual property")
                data = {}
                for field in body.fields:
                    _, prop, _ = self.property(field.property_contract, definition.iri)
                    data[prop.name] = self.property_value(field.value_id, definition, prop)
                value = self.prepared.validate_python(definition.name, data)
                expected_id = canonical_identity("rich-value", ["record", body.kind_contract, [field.model_dump(mode="python") for field in body.fields]]).key
            if expected_id != identifier:
                raise ValueError("rich value identity differs from its actual typed meaning")
            self.decoded[identifier] = value
            return value
        finally:
            self.active.remove(identifier)

    def qualification(self, identifier):
        body = self.member(identifier, DdoRichQualificationMeaning)
        self.reached_values.add(identifier)
        definition = self.definition(body.qualification_contract)
        self.prepared.qualification_definition(definition.name)
        present = set()
        for field in body.fields:
            if field.property_contract in present:
                raise ValueError("rich qualification repeats an actual property")
            present.add(field.property_contract)
            _, prop, _ = self.property(field.property_contract, definition.iri)
            if prop.key_role == "provenance":
                raise ValueError("rich fact equality includes source provenance")
            child = self.members.get(field.value_id)
            if isinstance(child, DdoRichCasefoldText):
                self.reached_values.add(field.value_id)
                if prop.case_policy != "casefold" or child.property_contract != field.property_contract or identity_casefold(child.text) != child.text:
                    raise ValueError("rich casefold projection differs from its actual property policy")
                expected = canonical_identity("rich-value", ["casefold-text", child.property_contract, child.text]).key
                if expected != child.value_id:
                    raise ValueError("rich casefold identity differs from its equality meaning")
            else:
                checked = self.property_value(field.value_id, definition, prop)
                if prop.case_policy == "casefold" and isinstance(checked, str):
                    raise ValueError("rich qualification lacks its explicit casefold equality projection")
        required = {self.ids[definition.iri + "/property/" + prop.name] for prop in definition.properties if prop.required and prop.key_role != "provenance"}
        if not required <= present:
            raise ValueError("rich qualification lacks required equality fields")
        expected = canonical_identity("rich-value", ["qualification-meaning", body.qualification_contract, [field.model_dump(mode="python") for field in body.fields]]).key
        if expected != identifier:
            raise ValueError("rich qualification identity differs from its actual meaning")
        return body

    def check(self):
        if isinstance(self.graph, DdoRichAuthoredPropositions):
            from .record_contracts import record_product_classes
            source_classes = record_product_classes(self.prepared.definitions)
            def domain_class(definition):
                if definition.name in source_classes or definition.name == "SourceReading" or "SourceReading" in definition.ancestors:
                    raise ValueError("authored propositions cannot manufacture source-reading or private record members")
            for body in self.members.values():
                if isinstance(body, DdoRichEntity):
                    if body.source_members:
                        raise ValueError("authored entity origin is supplied by its actual admission, not embedded source references")
                    for contract in body.class_contracts:
                        domain_class(self.definition(contract))
                elif isinstance(body, DdoRichRecordValue):
                    domain_class(self.definition(body.kind_contract))
        if isinstance(self.graph, DdoRichAdmission):
            for decision in self.graph.reading_decisions:
                if decision.assertion_member_id is not None:
                    assertion = self.member(decision.assertion_member_id, DdoRichSourceReadingAssertion)
                    if (assertion.record_id, assertion.source_interpretation_id, assertion.interpretation_id,
                        assertion.original, assertion.resolution, assertion.resolved) != (
                            decision.record_id, decision.source_interpretation_id, decision.interpretation_id,
                            decision.original, decision.resolution, decision.resolved):
                        raise ValueError("rich reading decision differs from its actual local assertion")
        for body in self.members.values():
            self._checking_member = _body_id(body)
            if isinstance(body, DdoRichEntity):
                if len(set(body.class_contracts)) != len(body.class_contracts):
                    raise ValueError("rich entity repeats actual class membership")
                for contract in body.class_contracts:
                    self.definition(contract)
                represented = set()
                for basis in body.identities:
                    if basis.class_contract not in body.class_contracts:
                        raise ValueError("rich entity identity belongs to another actual class")
                    definition = self.definition(basis.class_contract)
                    represented.add(basis.class_contract)
                    names = {name for group in definition.identity_groups if group != definition.identity_slots for name in group}
                    present = set()
                    for field in basis.fields:
                        _, prop, _ = self.property(field.property_contract, definition.iri)
                        if prop.name not in names or prop.name in present:
                            raise ValueError("rich entity basis is not an actual unique declared identity property")
                        present.add(prop.name)
                        self.property_value(field.value_id, definition, prop)
                if represented != set(body.class_contracts):
                    raise ValueError("rich entity lacks an explicit actual class identity basis")
                for reference in body.source_members:
                    self.external(reference)
            elif isinstance(body, DdoRichFact):
                definition, prop, _ = self.property(body.property_contract)
                self.class_member(body.subject_entity, definition)
                if prop.iri != body.predicate:
                    raise ValueError("rich fact predicate differs from its actual property")
                self.property_value(body.object_value, definition, prop, item=prop.multivalued)
                self.qualification(body.qualification_meaning)
                expected = canonical_identity("rich-fact", [self.context.identity_record, body.subject_entity, body.property_contract, body.object_value, body.qualification_meaning]).key
                if expected != body.fact_id:
                    raise ValueError("rich fact identity differs from its actual context and values")
            elif isinstance(body, (DdoRichOccurrence, DdoRichAuthoredProposition)):
                if isinstance(body, DdoRichOccurrence):
                    if body.establishment not in self.prepared.enum_members("Establishment"):
                        raise ValueError("rich occurrence has an unknown actual establishment")
                    if body.statement_kind is not None:
                        from .statement_types import statement_kinds
                        if body.statement_kind not in statement_kinds(self.prepared):
                            raise ValueError("rich occurrence has an unknown actual statement kind")
                    if body.statement_role is not None and body.statement_role not in self.prepared.enum_members("StatementRole"):
                        raise ValueError("rich occurrence has an unknown actual statement role")
                    if body.statement is None and (body.statement_kind is not None or body.statement_role is not None):
                        raise ValueError("rich occurrence statement metadata lacks its actual selected statement")
                fact = self.member(body.fact_id, DdoRichFact)
                if isinstance(body, DdoRichOccurrence):
                    self.external(body.original)
                    if body.statement is not None:
                        self.external(body.statement)
                else:
                    expected_id = canonical_identity("rich-authored-proposition", [
                        self.context.identity_record, body.fact_id, body.observed_qualification_value, sorted(set(body.dependencies)),
                    ]).key
                    if body.proposition_id != expected_id or len(set(body.dependencies)) != len(body.dependencies):
                        raise ValueError("authored proposition differs from its actual fact/qualification/dependency meaning")
                for dependency in body.dependencies:
                    self.member(dependency, DdoRichFact)
                observed = self.value(body.observed_qualification_value)
                expected = self.qualification_projections.get(body.observed_qualification_value)
                if expected is None:
                    _, expected = self.qualification_projector.lower_qualification(type(observed).__name__, observed)
                    self.qualification_projections[body.observed_qualification_value] = expected
                if expected != fact.qualification_meaning:
                    raise ValueError("rich occurrence qualification differs from its fact equality")
            elif isinstance(body, DdoRichSourceReadingAssertion):
                self.external(body.original)
                self.external(body.resolution)
                self.external(body.resolved)
                record = self.member(body.reading_value, DdoRichRecordValue)
                definition = self.definition(record.kind_contract)
                if definition.name != "SourceReading" and "SourceReading" not in definition.ancestors:
                    raise ValueError("rich reading assertion does not contain an actual source reading")
                self.value(body.reading_value)
            elif isinstance(body, DdoRichAlternative):
                if len(set(body.fact_ids)) != len(body.fact_ids):
                    raise ValueError("rich alternative repeats an actual fact")
                for fact in body.fact_ids:
                    self.member(fact, DdoRichFact)
                for ref in body.source_members:
                    self.external(ref)
            elif isinstance(body, DdoRichAssessment):
                for occurrence in body.occurrences:
                    self.member(occurrence, DdoRichOccurrence)
                for ref in body.evidence_members:
                    self.external(ref)
            elif isinstance(body, DdoRichIdentityResolution):
                self.member(body.resolved_entity_id, DdoRichEntity)
                for entity in body.relevant_entity_ids:
                    self.member(entity, DdoRichEntity)
                for reference in (*body.source_members, *body.dependency_sources):
                    self.external(reference)
            elif isinstance(body, DdoRichIdentityExclusion):
                from .rich_identity_exclusions import validate_rich_identity_exclusion
                validate_rich_identity_exclusion(self.prepared, self.context, body)
                for identifier in (body.left_entity_id, body.right_entity_id):
                    if identifier is not None:
                        self.member(identifier, DdoRichEntity)
                for reference in body.source_members:
                    self.external(reference)
            elif isinstance(body, DdoRichOccurrenceDecision):
                occurrence = self.member(body.occurrence_id, DdoRichOccurrence)
                if body.fact_id != occurrence.fact_id:
                    raise ValueError("rich rule decision refers to another actual occurrence fact")
                for finding in body.findings:
                    if finding.assessment_id is not None:
                        assessment = self.member(finding.assessment_id, DdoRichAssessment)
                        if body.occurrence_id not in assessment.occurrences or assessment.rule != finding.rule or assessment.severity != finding.severity:
                            raise ValueError("rich rule finding differs from its actual assessment")
            elif isinstance(body, DdoRichDiagnostic):
                for ref in body.source_members:
                    self.external(ref)
        self._checking_member = None
        self.check_selection()
        if self.reached_values != {identifier for identifier, body in self.members.items() if isinstance(body, _VALUES)}:
            raise ValueError("rich graph retains unreferenced or unchecked value members")


    def check_selection(self):
        graph = self.graph
        if isinstance(graph, DdoRichConsolidation):
            selection = graph.eligibility
        elif isinstance(graph, DdoRichAdmission):
            selection = graph
            readings = {identifier for identifier, body in self.members.items() if isinstance(body, DdoRichSourceReadingAssertion)}
            if readings != set(graph.selected_reading_ids):
                raise ValueError("admitted reading selection differs from its exact retained assertions")
        else:
            return
        for identifier in selection.selected_fact_ids:
            self.member(identifier, DdoRichFact)
        for identifier in selection.selected_occurrence_ids:
            occurrence = self.member(identifier, DdoRichOccurrence)
            if occurrence.fact_id not in selection.selected_fact_ids:
                raise ValueError("selected occurrence does not establish an actual selected fact")
        representatives = {item.fact_id: item for item in selection.scientific_representatives}
        if set(representatives) != set(selection.selected_fact_ids):
            raise ValueError("scientific representative mapping differs from the actual selected fact set")
        for representative in representatives.values():
            if representative.representative_fact_id not in representatives:
                raise ValueError("scientific representative is outside the actual selected fact set")


class _RetainedRichGraph(ValidatedRichGraph):
    """Local current meaning, with only its actual root's embedded opaque provenance."""

    def __init__(self, prepared, model, context, graph, selection):
        self.selection = selection
        self._embedded_provenance = {rich_reference_key(ref) for ref in _references(graph)}
        super().__init__(prepared, model, context, graph, (), ())

    def external(self, reference):
        if rich_reference_key(reference) not in self._embedded_provenance:
            raise ValueError("reference is not embedded unchanged in the actual retained rich root")


def read_retained_rich_graph(prepared: PreparedRelease, model: EffectiveDataOperationModel, *, context: SubjectContext,
                             retained: RichWholeInput, inputs: tuple[DdoRichSelectedMember, ...],
                             whole_inputs: tuple[RichWholeInput, ...]) -> ValidatedRichGraph:
    """Decode a selected accepted whole without pretending its old sources are inputs.

    Pure decoding grants no accepted standing. The native producer owner separately
    authenticates the actual admission/effect/CPU/common receipt and current seal.
    """
    validate_subject_context(model, context)
    if model.subject_definition(context.subject_definition).scope != "project" or context.original_source is not None:
        raise ValueError("retained rich graph requires its actual source-free project context")
    reference = DdoRichSelectedMember.model_validate(_untrusted_value(retained.reference), strict=True)
    key = rich_reference_key(reference)
    if reference.member_id is not None or key not in {rich_reference_key(item) for item in inputs}:
        raise ValueError("retained rich graph is not an actual selected whole input")
    actual = [item for item in whole_inputs if rich_reference_key(item.reference) == key]
    if len(actual) != 1 or _meaning(actual[0].value) != _meaning(retained.value):
        raise ValueError("retained rich graph differs from its actual selected whole body")
    owner = _NAMESPACE + "DdoRichAdmission"
    contract = next((item.key for item in model.identities if item.domain == "kind" and item.owner == owner), None)
    kind = next((item for item in model.kinds if item.semantic_id == owner), None)
    if kind is None or not kind.complete or reference.kind_contract != contract:
        raise ValueError("retained graph lacks its current-compatible whole admission contract; regenerate")
    validate_wire_schema(json.loads(kind.facts)["json_schema"], json_loads(json_bytes(_untrusted_value(retained.value))))
    checked = DdoRichAdmission.model_validate(_untrusted_value(retained.value))
    state = _RetainedRichGraph(prepared, model, context, checked, retained)
    state.check()
    return state


def read_rich_graph(prepared: PreparedRelease, model: EffectiveDataOperationModel, *, context: SubjectContext,
                    graph: RichGraphAssembly | DdoRichConsolidation | DdoRichAdmission | DdoRichAuthoredPropositions, inputs: tuple[DdoRichSelectedMember, ...],
                    whole_inputs: tuple[RichWholeInput, ...] = (),
                    retained_graphs: tuple[RichWholeInput, ...] = ()) -> ValidatedRichGraph:
    """Validate once and expose the same finite typed decoder to current CPU consumers."""
    validate_subject_context(model, context)
    if model.subject_definition(context.subject_definition).scope != "project" or context.original_source is not None:
        raise ValueError("rich graph requires its actual source-free project context")
    owner = type(graph)
    if owner not in {RichGraphAssembly, DdoRichAdmission, DdoRichConsolidation, DdoRichAuthoredPropositions}:
        raise ValueError("rich graph has no actual declared whole-product owner")
    checked = owner.model_validate(_untrusted_value(graph), strict=True)
    if owner is not RichGraphAssembly:
        kind = next((item for item in model.kinds if item.semantic_id == _NAMESPACE + owner.__name__), None)
        if kind is None or not kind.complete:
            raise ValueError("rich graph lacks its actual current-compatible root kind")
        validate_wire_schema(json.loads(kind.facts)["json_schema"], json_loads(json_bytes(checked.model_dump(mode="python"))))
    if len({rich_reference_key(item.reference) for item in retained_graphs}) != len(retained_graphs):
        raise ValueError("retained rich graph repeats an actual selected whole")
    retained_states = tuple(read_retained_rich_graph(prepared, model, context=context, retained=item,
                                                    inputs=inputs, whole_inputs=whole_inputs) for item in retained_graphs)
    state = ValidatedRichGraph(prepared, model, context, checked, inputs, whole_inputs, retained_states)
    if isinstance(checked, DdoRichAdmission):
        state.external(checked.consolidation)
        if state.kind(checked.consolidation.kind_contract).semantic_id != _NAMESPACE + "DdoRichConsolidation":
            raise ValueError("rich admission lacks its actual consolidation kind")
        from .record_policy_authority import AUTHORIZATION_KIND
        for reference in checked.policy_authorizations:
            state.external(reference)
            if state.kind(reference.kind_contract).semantic_id != AUTHORIZATION_KIND:
                raise ValueError("rich admission policy reference has a different actual kind")
    state.check()
    return state


def validate_rich_graph(prepared: PreparedRelease, model: EffectiveDataOperationModel, *, context: SubjectContext,
                        graph: RichGraphAssembly | DdoRichConsolidation | DdoRichAdmission | DdoRichAuthoredPropositions, inputs: tuple[DdoRichSelectedMember, ...],
                        whole_inputs: tuple[RichWholeInput, ...] = (),
                        retained_graphs: tuple[RichWholeInput, ...] = ()):
    """Validate finite graph meaning; selected/native publication custody stays with its owner."""
    return read_rich_graph(prepared, model, context=context, graph=graph, inputs=inputs, whole_inputs=whole_inputs, retained_graphs=retained_graphs).graph
