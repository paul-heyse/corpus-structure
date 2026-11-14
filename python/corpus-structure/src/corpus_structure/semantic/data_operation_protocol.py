"""Pure DDO projections of explicitly supplied authoritative protocol bytes."""

from __future__ import annotations

from hashlib import sha256

import yaml
from linkml_runtime.utils.yamlutils import DupCheckYamlLoader

# These are semantic projections, not independently authored membership lists.
VALUE_SET_PATHS = {
    "RecordableFate": ("definitions", "fate", "enum"),
    "HistoricalFate": ("definitions", "historical_fate", "enum"),
    "VisibleFate": ("definitions", "visible_fate", "enum"),
    "RevocationSelectorKind": (
        "definitions",
        "revoke_data_support_request",
        "properties",
        "selector_kind",
        "enum",
    ),
}


def protocol_value_sets(content: bytes) -> dict[str, tuple[str, ...]]:
    """Read closed value sets without acquiring any ambient declaration."""
    document = yaml.load(content, Loader=DupCheckYamlLoader)
    result = {}
    for name, path in VALUE_SET_PATHS.items():
        value = document
        try:
            for segment in path:
                value = value[segment]
        except (KeyError, TypeError) as error:
            raise ValueError(f"missing protocol value set {name}") from error
        if (
            not isinstance(value, list)
            or not value
            or any(not isinstance(item, str) or not item for item in value)
            or len(set(value)) != len(value)
        ):
            raise ValueError(f"invalid protocol value set {name}")
        result[name] = tuple(value)
    return result


def recordable_fate_sql(content: bytes) -> str:
    """Compile a finite literal list, with SQL quoting independent of its values."""
    return ",".join(
        "'" + value.replace("'", "''") + "'"
        for value in protocol_value_sets(content)["RecordableFate"]
    )


def generated_fate_source(content: bytes) -> str:
    """Static typing consumes the same protocol bytes as native/physical derivation."""
    return (
        '"""Generated from the authoritative DDO protocol; do not edit."""\n\n'
        + "from typing import Literal\n\n"
        + f"PROTOCOL_SHA256 = {sha256(content).hexdigest()!r}\n\n"
        + "\n\n".join(
            f"type {name} = Literal[" + ", ".join(repr(value) for value in values) + "]"
            for name, values in protocol_value_sets(content).items()
        )
        + "\n"
    )
