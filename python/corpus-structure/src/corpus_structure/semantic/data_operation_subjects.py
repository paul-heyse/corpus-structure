"""Owned nominal property projections for value and identifier consumers."""

import json


def subject_field_path(field: str) -> tuple[str, ...]:
    """A property name or RFC 6901 pointer identifies one owned body field."""
    if not field.startswith("/"):
        return (field,)
    parts = field[1:].split("/")
    for part in parts:
        tail = part.replace("~0", "").replace("~1", "")
        if not part or "~" in tail:
            raise ValueError("subject association has an invalid property pointer")
    return tuple(part.replace("~1", "/").replace("~0", "~") for part in parts)


def _field_range(kinds, owner: str, field: str):
    path = subject_field_path(field)
    for index, name in enumerate(path):
        prop = kinds.get(owner + "/property/" + name)
        if prop is None or prop.category != "property":
            raise ValueError("field projection requires an owned kind property")
        facts = json.loads(prop.facts)
        target = kinds.get(facts.get("range"))
        if index < len(path) - 1:
            if (
                facts.get("multivalued")
                or target is None
                or target.category != "class"
                or not facts.get("inlined")
            ):
                raise ValueError("field projection traverses only scalar inline nominal records")
            owner = target.semantic_id
        else:
            if target is None:
                raise ValueError("field projection requires a declared range")
            return facts, target
    raise ValueError("field projection requires a nonempty owned path")


def value_field_kind(kinds, owner: str, field: str):
    """Value witnesses compare the complete typed field, including nested records."""
    return _field_range(kinds, owner, field)[1]


def subject_field_kind(kinds, owner: str, field: str):
    """Subject association requires a scalar nominal or lexical identifier."""
    facts, target = _field_range(kinds, owner, field)
    target_facts = json.loads(target.facts)
    primitive = target_facts.get("primitive", target_facts.get("effective_primitive"))
    if (
        facts.get("multivalued")
        or (target.category == "class" and facts.get("inlined"))
        or (
            primitive not in {"str", "string", "uri", "uriorcurie"}
            and target.category not in {"class", "enum"}
        )
    ):
        raise ValueError("subject association requires a scalar subject identifier")
    return target


def subject_scope_values() -> tuple[str, ...]:
    """Project the checked subject owner's closed scope type for native validation."""
    from typing import get_args, get_type_hints
    from .data_operation_model import SubjectDefinition
    values=get_args(get_type_hints(SubjectDefinition)["scope"])
    if not values or any(type(value) is not str for value in values):
        raise ValueError("subject scope owner is not a closed string contract")
    return tuple(sorted(values))
