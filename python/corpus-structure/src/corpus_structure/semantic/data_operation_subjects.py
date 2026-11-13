"""Declared identifier projections through owned nominal properties."""

import json


def subject_field_path(field: str) -> tuple[str, ...]:
    """A property name or RFC 6901 pointer identifies one scalar body leaf."""
    if not field.startswith("/"):
        return (field,)
    parts = field[1:].split("/")
    for part in parts:
        tail = part.replace("~0", "").replace("~1", "")
        if not part or "~" in tail:
            raise ValueError("subject association has an invalid property pointer")
    return tuple(part.replace("~1", "/").replace("~0", "~") for part in parts)


def subject_field_kind(kinds, owner: str, field: str):
    path = subject_field_path(field)
    for index, name in enumerate(path):
        prop = kinds.get(owner + "/property/" + name)
        if prop is None or prop.category != "property":
            raise ValueError("subject association requires an owned kind property")
        facts = json.loads(prop.facts)
        target = kinds.get(facts.get("range"))
        if facts.get("multivalued"):
            raise ValueError("subject association requires a scalar subject identifier")
        if index < len(path) - 1:
            if target is None or target.category != "class" or not facts.get("inlined"):
                raise ValueError("subject association traverses only inline nominal records")
            owner = target.semantic_id
            continue
        target_facts = json.loads(target.facts) if target is not None else {}
        primitive = target_facts.get("primitive", target_facts.get("effective_primitive"))
        if primitive not in {"str", "string", "uri", "uriorcurie"} and not (
            target is not None and target.category in {"class", "enum"} and not facts.get("inlined")
        ):
            raise ValueError("subject association requires a scalar subject identifier")
        return target
