"""Exact declared property datatype and bound projections for current consumers."""

import json
from dataclasses import asdict
from decimal import Decimal
from typing import Any

from .types import PreparedRelease


def native_constraints(prepared: PreparedRelease) -> dict[tuple[str, str], dict[str, Any]]:
    """Prepare native datatype and exact bound lowerings once per release projection."""
    from .record_contracts import record_product_classes

    primitives = {
        "string",
        "integer",
        "decimal",
        "boolean",
        "date",
        "datetime",
        "float",
        "double",
        "uri",
        "uriorcurie",
    }
    classes = {d.name for d in prepared.definitions}
    enums = {v.enum for v in prepared.vocabularies}
    definitions = {
        row.name: json.loads(row.body) for row in prepared.registry_rows if row.kind == "type"
    }
    resolved = {name: name for name in primitives | classes | enums}

    def resolve(name: str, path: frozenset[str] = frozenset()) -> str:
        if name in resolved:
            return resolved[name]
        if name in path or name not in definitions:
            raise ValueError(f"unsupported native range {name}")
        definition = definitions[name]
        parent = definition.get("typeof") or definition.get("base") or "string"
        parent = {"str": "string", "int": "integer", "bool": "boolean", "Decimal": "decimal"}.get(
            parent, parent
        )
        resolved[name] = resolve(parent, path | {name})
        return resolved[name]

    products = record_product_classes(prepared.definitions)
    result = {}
    for definition in prepared.definitions:
        if definition.name in products:
            continue
        for prop in definition.properties:
            constraints = asdict(prop)
            if (
                definition.name == "Entity" or "Entity" in definition.ancestors
            ) and prop.name in definition.identity_slots:
                constraints["structural_identifier"] = True
            constraints["native_range"] = resolve(prop.range)
            if constraints["native_range"] in {"float", "double"} and (
                prop.minimum is not None or prop.maximum is not None
            ):
                raise ValueError("exact float bounds have no admitted native lowering")
            for bound in ("minimum", "maximum"):
                raw = getattr(prop, bound)
                if raw is not None:
                    value = Decimal(raw)
                    if not value.is_finite():
                        raise ValueError("non-finite native bound")
                    lexical = format(value, "f") if value else "0"
                    if "." in lexical:
                        lexical = lexical.rstrip("0").rstrip(".")
                    constraints["native_" + bound] = lexical
            result[definition.iri, prop.iri] = constraints
    return result

