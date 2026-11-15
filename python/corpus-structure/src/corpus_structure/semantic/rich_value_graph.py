"""Typed rich value lowering over the actual admitted family/property graph."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from .data_operation_identity import canonical_identity
from .data_operation_model import EffectiveDataOperationModel
from .rich_knowledge_contracts import (
    DdoRichCollectionValue, DdoRichEntityValue, DdoRichRecordValue,
    DdoRichScalarValue, DdoRichValueEntry,
    DdoRichCasefoldText, DdoRichQualificationMeaning,
)
from .types import PreparedRelease, PropertyDefinition
from .value_codec import value_meaning


type RichValue = DdoRichScalarValue | DdoRichEntityValue | DdoRichRecordValue | DdoRichCollectionValue | DdoRichCasefoldText | DdoRichQualificationMeaning


class RichValueGraph:
    """One invocation's reusable exact values, without publication/run row aliases."""

    def __init__(self, prepared: PreparedRelease, model: EffectiveDataOperationModel):
        self.prepared = prepared
        self.model = model
        self.kinds = {kind.semantic_id: kind for kind in model.kinds}
        self.contracts = {item.owner: item.key for item in model.identities if item.domain == "kind"}
        self._values: dict[str, RichValue] = {}

    @property
    def values(self) -> tuple[RichValue, ...]:
        return tuple(self._values[key] for key in sorted(self._values))

    def _contract(self, kind_id: str) -> str:
        if kind_id not in self.kinds or not self.kinds[kind_id].complete or kind_id not in self.contracts:
            raise ValueError("rich value requires its actual complete nominal range")
        return self.contracts[kind_id]

    def _property_range(self, owner: str, prop: PropertyDefinition) -> str:
        identifier = owner + "/property/" + prop.name
        kind = self.kinds.get(identifier)
        if kind is None or kind.category != "property" or not kind.complete:
            raise ValueError("rich property lacks its actual effective owner")
        target = json.loads(kind.facts)["range"]
        if {edge.target for edge in self.model.edges if edge.source == identifier and edge.relation == "range"} != {target}:
            raise ValueError("rich property range differs from its actual effective graph")
        self._contract(target)
        return target

    def lower_property(self, class_name: str, property_name: str, value: Any, *, item: bool = False) -> str:
        definition = self.prepared.index.definitions[class_name]
        prop = next(prop for prop in definition.properties if prop.name == property_name)
        checked = self.prepared.property_adapter(class_name, property_name, item=item).validate_python(value, strict=True)
        return self._property_value(definition.iri, prop, checked, item=item)

    def _property_value(self, owner: str, prop: PropertyDefinition, value: Any, *, item: bool = False) -> str:
        target = self._property_range(owner, prop)
        if value is None:
            raise ValueError("current LinkML property boundaries do not admit explicit null")
        return self._collection(value, target, prop.inlined) if prop.multivalued and not item else self._lower(value, target, prop.inlined)

    def lower_record(self, class_name: str, value: Any) -> str:
        definition = self.prepared.index.definitions[class_name]
        checked = self.prepared.validate_python(class_name, value)
        return self._lower(checked, definition.iri, True)

    def lower_qualification(self, class_name: str, value: Any) -> tuple[str, str]:
        """Keep the observed typed value and its distinct declared equality meaning."""
        from .qualification_meaning import qualification_identity_components

        definition = self.prepared.qualification_definition(class_name)
        checked = self.prepared.validate_python(class_name, value)
        observed_id = self._lower(checked, definition.iri, True)
        supplied = {name: getattr(checked, name) for name in checked.model_fields_set}
        fields = []
        for component in qualification_identity_components(self.prepared, supplied, qualification_class=class_name):
            prop = component.property
            target = self._property_range(definition.iri, prop)
            if component.equality == "casefold-text":
                property_contract = self._contract(definition.iri + "/property/" + prop.name)
                value_id = canonical_identity("rich-value", ["casefold-text", property_contract, component.equality_value]).key
                self._retain(DdoRichCasefoldText(member_type="casefold-text", value_id=value_id, property_contract=property_contract, text=component.equality_value))
            else:
                value_id = self._property_value(definition.iri, prop, component.observed)
            fields.append(DdoRichValueEntry(name=prop.iri, position=0, value_id=value_id))
        fields = tuple(sorted(fields, key=lambda field: field.name))
        contract = self._contract(definition.iri)
        identifier = canonical_identity("rich-value", ["qualification-meaning", contract, [field.model_dump(mode="python") for field in fields]]).key
        self._retain(DdoRichQualificationMeaning(member_type="qualification-meaning", value_id=identifier, qualification_contract=contract, fields=fields))
        return observed_id, identifier

    def _retain(self, value: RichValue) -> str:
        previous = self._values.get(value.value_id)
        if previous is not None and previous != value:
            raise ValueError("rich value identity has conflicting immutable meaning")
        self._values[value.value_id] = value
        return value.value_id

    def _collection(self, value: Any, kind_id: str, inlined: bool) -> str:
        if isinstance(value, Mapping):
            collection = "mapping"
            entries = tuple(DdoRichValueEntry(name=name, position=0, value_id=self._lower(member, kind_id, inlined)) for name, member in sorted(value.items()))
        elif isinstance(value, (tuple, list)):
            collection = "sequence"
            entries = tuple(DdoRichValueEntry(name="item", position=index, value_id=self._lower(member, kind_id, inlined)) for index, member in enumerate(value))
        else:
            raise ValueError("rich declared collection requires its actual sequence or mapping")
        contract = self._contract(kind_id)
        identifier = canonical_identity("rich-value", [collection, contract, [entry.model_dump(mode="python") for entry in entries]]).key
        return self._retain(DdoRichCollectionValue(member_type="collection-value", value_id=identifier, element_contract=contract, collection=collection, entries=entries))

    def _lower(self, value: Any, kind_id: str, inlined: bool) -> str:
        if value is None:
            raise ValueError("explicit null requires its actual validated property boundary")
        contract = self._contract(kind_id)
        kind = self.kinds[kind_id]
        if kind.category == "class" and not inlined:
            if type(value) is not str or not value:
                raise ValueError("rich entity reference requires its actual identifier")
            identifier = canonical_identity("rich-value", ["entity", contract, value]).key
            return self._retain(DdoRichEntityValue(member_type="entity-value", value_id=identifier, kind_contract=contract, entity_id=value))
        if isinstance(value, BaseModel):
            definition = self.prepared.index.definitions.get(type(value).__name__)
            if definition is None or (definition.iri != kind_id and kind.name not in definition.ancestors):
                raise ValueError("rich record value differs from its actual declared nominal range")
            contract = self._contract(definition.iri)
            fields = []
            for prop in definition.properties:
                if prop.name not in value.model_fields_set:
                    continue
                child = getattr(value, prop.name)
                child_id = self._property_value(definition.iri, prop, child)
                fields.append(DdoRichValueEntry(name=prop.iri, position=0, value_id=child_id))
            fields = tuple(sorted(fields, key=lambda field: field.name))
            identifier = canonical_identity("rich-value", ["record", contract, [field.model_dump(mode="python") for field in fields]]).key
            return self._retain(DdoRichRecordValue(member_type="record-value", value_id=identifier, kind_contract=contract, fields=fields))
        if isinstance(value, (Mapping, tuple, list)):
            raise ValueError("rich compound values require an actual typed record or declared collection")
        meaning = value_meaning(value)
        datatype = meaning[0]
        lexical = "" if datatype == "null" else ("true" if meaning[1] is True else "false") if datatype == "boolean" else str(meaning[1])
        identifier = canonical_identity("rich-value", [contract, meaning]).key
        return self._retain(DdoRichScalarValue(member_type="scalar-value", value_id=identifier, kind_contract=contract, datatype=datatype, lexical=lexical))
