"""Current derived source-reading schemas from actual supplied record families."""

from typing import Any

import yaml
from linkml_runtime.dumpers import json_dumper

from .rich_record_readings import (
    READING_CLASSES as _FAMILIES,
)
from .rich_record_readings import (
    READING_VALUE_FIELDS as _VALUE_FIELDS,
)
from .types import PreparationProfile, SourceArtifact, SourceBundle

_NAMESPACE = "https://corpus-structure.dev/semantic/source-reading/"
_MODULE = "source-readings"
_ROOT = "source-reading-root"


def _scalar_name(name: str) -> str:
    return "SourceReading" + (name[6:] if name.startswith("Record") else name)


def _field_name(name: str) -> str:
    return "SourceReading" + name.replace("RecordField", "").removesuffix("Field") + "Value"


def source_reading_inputs(bundle: SourceBundle, *, require_families: bool = True) -> SourceBundle:
    """Derive graph declarations from the effective supplied LinkML family contracts.

    Call after observation inputs, before prepare_release. No release ID or prepared
    registry is needed. The resulting source bytes are archived/hashed normally.
    """
    from .prepare import _view

    if any(source.name in {_MODULE, _ROOT} for source in bundle.sources):
        if bundle.root != _ROOT:
            raise ValueError("reserved source-reading module already supplied")
        original_root = yaml.safe_load(next(s.content for s in bundle.sources if s.name == _ROOT))[
            "imports"
        ][0]
        original = SourceBundle(
            original_root, tuple(s for s in bundle.sources if s.name not in {_MODULE, _ROOT})
        )
        if source_reading_inputs(original, require_families=require_families) != bundle:
            raise ValueError("source-reading declarations differ from effective family contracts")
        return bundle
    view = _view(bundle, PreparationProfile(version="semantic-2"))
    classes = {str(name): definition for name, definition in view.all_classes().items()}
    if "SemanticRecordFields" not in classes:
        if not require_families:
            return bundle
        raise ValueError("source reading derivation requires observation record declarations")
    families: dict[str, tuple[str, list[Any]]] = {}
    for name in sorted(classes):
        if name == "SemanticRecordFields" or "SemanticRecordFields" not in view.class_ancestors(
            name
        ):
            continue
        slots = {str(slot.name): slot for slot in view.class_induced_slots(name)}
        family = slots["family"].equals_string or ""
        if family not in _FAMILIES or family in families:
            raise ValueError("unsupported or duplicate source-reading family")
        families[family] = (
            name,
            [slot for key, slot in slots.items() if key not in {"family", "occurrence_recipe"}],
        )
    if not families:
        if not require_families:
            return bundle
        raise ValueError("source reading derivation requires an effective family")
    scalar_classes = {
        name
        for name in classes
        if name == "RecordScalar" or "RecordScalar" in view.class_ancestors(name)
    }
    field_classes = {str(slot.range) for _, roles in families.values() for slot in roles}
    names = {name: _scalar_name(name) for name in scalar_classes}
    names.update({name: _field_name(name) for name in field_classes})
    if len(set(names.values())) != len(names) or set(names.values()) & set(classes):
        raise ValueError("derived source-reading value name collision")

    def attribute(slot, *, owner: str):
        body = json_dumper.to_dict(slot)
        # Induced ownership is compiler metadata, not another declared relationship.
        for key in (
            "name",
            "owner",
            "domain_of",
            "from_schema",
            "domain",
            "is_a",
            "mixins",
            "pattern",
        ):
            body.pop(key, None)
        body["slot_uri"] = "source_reading:" + owner + "/" + str(slot.name)
        if str(slot.range) in names:
            body["range"] = names[str(slot.range)]
        elif str(slot.range) in classes:
            raise ValueError(
                "graph-safe reading value cannot reference private class " + str(slot.range)
            )
        return body

    derived: dict[str, Any] = {
        "SourceReading": {
            "is_a": "Entity",
            "abstract": True,
            "class_uri": "source_reading:SourceReading",
            "annotations": {"cs:scope": "local", "cs:case": "preserve"},
        }
    }
    for name in sorted(scalar_classes | field_classes):
        target = names[name]
        attrs = {
            str(slot.name): attribute(slot, owner=target)
            for slot in view.class_induced_slots(name)
            if name in scalar_classes or str(slot.name) in _VALUE_FIELDS
        }
        body: dict[str, Any] = {"class_uri": "source_reading:" + target, "attributes": attrs}
        if name in scalar_classes:
            original = classes[name]
            if original.is_a and str(original.is_a) in scalar_classes:
                body["is_a"] = names[str(original.is_a)]
            if original.abstract:
                body["abstract"] = True
        derived[target] = body
    for family, (_, roles) in sorted(families.items()):
        target = _FAMILIES[family]
        if target in classes:
            raise ValueError("derived source-reading class collision")
        attrs = {}
        for slot in roles:
            if not slot.required or slot.multivalued or not slot.inlined:
                raise ValueError("reading roles require scalar required inlined fields")
            attrs[str(slot.name)] = {
                "range": names[str(slot.range)],
                "required": True,
                "inlined": True,
                "slot_uri": "source_reading:" + target + "/" + str(slot.name),
            }
        derived[target] = {
            "is_a": "SourceReading",
            "class_uri": "source_reading:" + target,
            "attributes": attrs,
        }
    module = {
        "id": _NAMESPACE,
        "name": "semantic_source_readings",
        "default_range": "string",
        "prefixes": {"source_reading": _NAMESPACE},
        "default_prefix": "source_reading",
        "classes": derived,
    }
    return SourceBundle(
        _ROOT,
        (
            *bundle.sources,
            SourceArtifact(_MODULE, yaml.safe_dump(module, sort_keys=True).encode()),
            SourceArtifact(
                _ROOT,
                yaml.safe_dump(
                    {
                        "id": _NAMESPACE + "root",
                        "name": "semantic_source_reading_root",
                        "imports": [bundle.root, _MODULE],
                    },
                    sort_keys=True,
                ).encode(),
            ),
        ),
    )
