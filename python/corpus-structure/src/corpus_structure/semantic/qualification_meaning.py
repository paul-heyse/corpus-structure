"""The declared qualification equality projection, independent of provenance storage."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from .types import PreparedRelease, PropertyDefinition


@dataclass(frozen=True)
class QualificationComponent:
    property: PropertyDefinition
    observed: Any
    equality_value: Any
    equality: Literal["exact", "casefold-text"]


def qualification_identity_components(
    prepared: PreparedRelease,
    qualification: Mapping[str, Any],
    *,
    qualification_class: str,
) -> tuple[QualificationComponent, ...]:
    """Apply the actual qualification's key-role and case policy exactly once.

    This projects equality; a normalized enum/text token is not an observed field
    value and does not acquire that property's nominal value contract.
    """
    from .unicode_identity import identity_casefold

    definition = prepared.qualification_definition(qualification_class)
    props = prepared.index.properties_by_class[definition.name]
    result = []
    for name, observed in qualification.items():
        if name not in props:
            raise ValueError(f"undeclared qualification {name}")
        prop = props[name]
        if prop.key_role == "provenance":
            continue
        folded = prop.case_policy == "casefold" and isinstance(observed, str)
        result.append(
            QualificationComponent(
                prop,
                observed,
                identity_casefold(observed) if folded else observed,
                "casefold-text" if folded else "exact",
            )
        )
    return tuple(sorted(result, key=lambda component: component.property.name))
