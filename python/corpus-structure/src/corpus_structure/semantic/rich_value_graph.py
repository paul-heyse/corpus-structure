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
)
from .types import PreparedRelease, PropertyDefinition
from .value_codec import value_meaning


type RichValue = DdoRichScalarValue | DdoRichEntityValue | DdoRichRecordValue | DdoRichCollectionValue


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
        target = self._property_range(definition.iri, prop)
        return self._collection(checked, target, prop.inlined) if prop.multivalued and not item else self._lower(checked, target, prop.inlined)

    def lower_record(self, class_name: str, value: Any) -> str:
        definition = self.prepared.index.definitions[class_name]
        checked = self.prepared.validate_python(class_name, value)
        return self._lower(checked, definition.iri, True)

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
        return self._retain(DdoRichCollectionValue(member_type="collection-value", value_id=identifier, kind_contract=contract, collection=collection, entries=entries))

    def _lower(self, value: Any, kind_id: str, inlined: bool) -> str:
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
                target = self._property_range(definition.iri, prop)
                child_id = self._collection(child, target, prop.inlined) if prop.multivalued else self._lower(child, target, prop.inlined)
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
