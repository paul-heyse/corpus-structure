"""Typed task-unit vocabulary checked against the released declaration."""

from enum import StrEnum

from corpus_structure.model.compiled import running_model


class TaskUnitType(StrEnum):
    DOCUMENT = "document"
    RENDITION = "rendition"
    SEGMENT = "segment"
    SPAN = "span"
    OBSERVATION = "observation"
    ENTITY = "entity"
    CLAIM = "claim"
    ALTERNATIVE_GROUP = "alternative_group"
    IDENTITY_GROUP = "identity_group"
    RUN = "run"
    GOLDEN_UNIT = "golden_unit"
    SOURCE_VIEW = "source_view"


def _check_declaration():
    declaration = running_model().view("task-vocabularies.yaml").get_enum("TaskUnitType")
    members = declaration.permissible_values if declaration is not None else None
    if not isinstance(members, dict) or set(members) != {member.value for member in TaskUnitType}:
        raise ValueError("TaskUnitType differs from the released vocabulary")


_check_declaration()
