"""Current domain property facts over a checked closed entity/fact universe."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .data_operation_identity import canonical_identity
from .data_operation_model import EffectiveDataOperationModel, SubjectContext, validate_subject_context
from .rich_knowledge_contracts import DdoRichFact
from .rich_value_graph import RichValueGraph
from .types import PreparedRelease


@dataclass(frozen=True)
class RichFactResult:
    fact: DdoRichFact
    observed_qualification_value: str


class RichFactGraph(RichValueGraph):
    """Lower explicit domain claims; source reading reports cannot enter this path.

    Pure construction grants no accepted standing. The caller supplies the actual
    selected closed universe; native publication independently checks that custody.
    """

    def __init__(self, prepared: PreparedRelease, model: EffectiveDataOperationModel, *,
                 context: SubjectContext, entities: Mapping[str, frozenset[str]], known_fact_ids: frozenset[str]):
        super().__init__(prepared, model)
        validate_subject_context(model, context)
        if model.subject_definition(context.subject_definition).scope != "project" or context.original_source is not None:
            raise ValueError("rich knowledge requires its actual source-free project subject")
        self.context = context
        self.entities = dict(entities)
        self._known_facts = set(known_fact_ids)
        self._facts: dict[str, DdoRichFact] = {}
        definitions = {definition.iri: definition for definition in prepared.definitions}
        for identifier, classes in self.entities.items():
            if not identifier or not classes or any(class_iri not in definitions for class_iri in classes):
                raise ValueError("rich entity universe requires actual checked class references")
        self._definitions_by_iri = definitions

    @property
    def facts(self) -> tuple[DdoRichFact, ...]:
        return tuple(self._facts[key] for key in sorted(self._facts))

    def _references(self, class_name: str, value: Any) -> None:
        from .reference_positions import collect_references

        for reference in collect_references(self.prepared, class_name, value):
            available = self.entities if reference.kind == "class" else self._known_facts
            if reference.target not in available:
                raise ValueError("rich claim refers outside its exact selected entity/fact universe")
            if reference.kind == "class" and not self._class_member(reference.target, reference.range):
                raise ValueError("rich reference lacks its actual selected class membership")

    def _class_member(self, identifier: str, class_name: str) -> bool:
        definition = self.prepared.index.definitions[class_name]
        return identifier in self.entities and any(
            class_iri == definition.iri or class_name in self._definitions_by_iri[class_iri].ancestors
            for class_iri in self.entities[identifier]
        )

    def add_property_fact(self, *, subject_entity: str, class_name: str, property_name: str,
                          value: Any, qualification: Any, qualification_class: str = "Qualification") -> RichFactResult:
        from .record_contracts import record_product_classes

        definition = self.prepared.index.definitions[class_name]
        if class_name in record_product_classes(self.prepared.definitions) or class_name == "SourceReading" or "SourceReading" in definition.ancestors:
            raise ValueError("source readings require their distinct assertion member, never a domain fact")
        if not self._class_member(subject_entity, class_name):
            raise ValueError("rich claim subject lacks its actual selected class membership")
        prop = next(prop for prop in definition.properties if prop.name == property_name)
        checked = self.prepared.property_adapter(class_name, property_name, item=prop.multivalued).validate_python(value, strict=True)
        if checked is not None and prop.reference_role == "fact" and checked not in self._known_facts:
            raise ValueError("rich claim names a fact outside its selected dependency universe")
        if checked is not None and prop.range in self.prepared.index.definitions:
            if prop.inlined:
                self._references(prop.range, checked)
            elif checked not in self.entities:
                raise ValueError("rich claim object is outside its selected entity universe")
            elif not self._class_member(checked, prop.range):
                raise ValueError("rich object lacks its actual selected class membership")
        qvalue = self.prepared.validate_python(qualification_class, qualification)
        self._references(qualification_class, qvalue)
        before = len(self._values)
        try:
            obj = self.lower_property(class_name, property_name, checked, item=prop.multivalued)
            observed, meaning = self.lower_qualification(qualification_class, qvalue)
            property_contract = self._contract(definition.iri + "/property/" + property_name)
            identifier = canonical_identity("rich-fact", [self.context.identity_record, subject_entity, property_contract, obj, meaning]).key
            fact = DdoRichFact(member_type="fact", fact_id=identifier, subject_entity=subject_entity,
                               property_contract=property_contract, predicate=prop.iri,
                               object_value=obj, qualification_meaning=meaning)
            previous = self._facts.get(identifier)
            if previous is not None and previous != fact:
                raise ValueError("rich fact identity has conflicting immutable meaning")
        except BaseException:
            # Only newly inserted immutable values are rolled back. Reusing an
            # existing node never changes dict insertion order or its contents.
            while len(self._values) > before:
                self._values.popitem()
            raise
        self._facts[identifier] = fact
        self._known_facts.add(identifier)
        return RichFactResult(fact, observed)
