"""Preserve Docling's native page-element variants across JSON replay.

PageElement is an undiscriminated union: a ContainerElement's JSON also validates
as FigureElement. The native class is therefore required replay data, not a type
that may be guessed again during ordinary restoration.
"""

from collections.abc import Mapping
from typing import Any, get_args

from docling.datamodel.base_models import AssembledUnit, PageElement

_GROUPS = ("elements", "body", "headers")
_TYPES = {cls.__name__: cls for cls in get_args(PageElement)}


def assembly_types(unit: AssembledUnit) -> dict[str, list[str]]:
    result = {}
    for group in _GROUPS:
        kinds = []
        for element in getattr(unit, group):
            name = type(element).__name__
            if name not in _TYPES or type(element) is not _TYPES[name]:
                raise ValueError("unmapped native page element class: " + name)
            kinds.append(name)
        result[group] = kinds
    return result


def restore_assembly(value: Mapping[str, Any], kinds: Mapping[str, Any]) -> AssembledUnit:
    if set(kinds) != set(_GROUPS):
        raise ValueError("native assembly class inventory differs")
    groups = {}
    for group in _GROUPS:
        rows = value.get(group, [])
        tags = kinds[group]
        if not isinstance(tags, list) or len(tags) != len(rows):
            raise ValueError("native assembly class inventory differs")
        result = []
        for row, tag in zip(rows, tags, strict=True):
            if tag not in _TYPES:
                raise ValueError("unmapped native page element class")
            result.append(_TYPES[tag].model_validate(row))
        groups[group] = result
    return AssembledUnit(**groups)


def derive_v1_assembly_types(value: Mapping[str, Any]) -> dict[str, list[str]]:
    """Explicit storage derivation for retained v1 spools under pinned native rules.

    This does not repair or relabel elements. It recovers the class selected by
    PageAssembleModel2.145 from its labels and field-region shape; unknowns refuse.
    New ordinary replay always carries the original class inventory instead.
    """
    from docling.models.base_layout_model import (
        CONTAINER_LABELS,
        FIGURE_LABEL,
        TABLE_LABELS,
        TEXT_ELEM_LABELS,
    )
    from docling_core.types.doc import DocItemLabel

    result = {}
    for group in _GROUPS:
        tags = []
        for row in value.get(group, []):
            label = DocItemLabel(row["label"])
            if label == DocItemLabel.FIELD_REGION:
                tag = "FieldRegionElement"
            elif label in CONTAINER_LABELS:
                tag = "ContainerElement"
            elif label in TABLE_LABELS:
                tag = "Table"
            elif label == FIGURE_LABEL:
                tag = "FigureElement"
            elif label in TEXT_ELEM_LABELS:
                tag = "TextElement"
            else:
                raise ValueError("unmapped retained v1 page label: " + label.value)
            tags.append(tag)
        result[group] = tags
    return result
