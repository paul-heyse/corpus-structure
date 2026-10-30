"""Effective input roles, derived once from the immutable release definitions."""

import json
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import PreparedRelease


def property_roles(prepared: PreparedRelease):
    authored = {
        (body["class"], body["property"]): body.get("cs:role")
        for row in prepared.registry_rows
        if row.kind == "operation_property"
        for body in (json.loads(row.body),)
    }
    result: dict[tuple[str, str], frozenset[str]] = {}
    for definition in prepared.definitions:
        identity = {name for group in definition.identity_groups for name in group}
        for prop in definition.properties:
            roles = set()
            if prop.name in identity:
                roles.add("identity")
            if prop.required or (prop.minimum_cardinality or 0) > 0:
                roles.add("required")
            if authored.get((definition.name, prop.iri)) == "display":
                roles.add("display")
            if roles:
                result[definition.iri, prop.iri] = frozenset(roles)
    return MappingProxyType(result)
