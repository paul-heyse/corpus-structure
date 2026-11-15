"""Pure DDO projections of explicitly supplied authoritative protocol bytes."""

from __future__ import annotations

from hashlib import sha256

import yaml
from linkml_runtime.utils.yamlutils import DupCheckYamlLoader

# These are semantic projections, not independently authored membership lists.
VALUE_SET_PATHS = {
    "DataTaskState": ("definitions", "data_task_state", "enum"),
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


def data_task_lifecycle(content: bytes) -> dict:
    """Validate the captured state/transition projection consumed by the task guard."""
    document = yaml.load(content, Loader=DupCheckYamlLoader)
    states = set(protocol_value_sets(content)["DataTaskState"])
    policy = document["definitions"]["data_task_state"].get("x-ddo-lifecycle")
    expected = {"initial", "running", "terminal", "receipt_required", "new_attempt", "same_attempt"}
    if not isinstance(policy, dict) or set(policy) != expected:
        raise ValueError("data task lifecycle requires its complete closed projection")
    if any(not isinstance(policy[key], str) or policy[key] not in states for key in ("initial", "running")) or policy["initial"] == policy["running"]:
        raise ValueError("data task lifecycle has invalid initial/running state")
    for key in ("terminal", "receipt_required"):
        values = policy[key]
        if not isinstance(values, list) or not values or any(not isinstance(value, str) for value in values) or len(values) != len(set(values)) or not set(values) <= states:
            raise ValueError("data task lifecycle has invalid " + key)
    if not set(policy["receipt_required"]) <= set(policy["terminal"]) or {policy["initial"], policy["running"]} & set(policy["terminal"]):
        raise ValueError("data task terminal/receipt policy overlaps live states")
    if states != {policy["initial"], policy["running"], *policy["terminal"]}:
        raise ValueError("data task lifecycle leaves an unclassified state")
    for key in ("new_attempt", "same_attempt"):
        edges = policy[key]
        if not isinstance(edges, list) or not edges or any(not isinstance(edge, list) or len(edge) != 2 or any(not isinstance(state, str) or state not in states for state in edge) for edge in edges):
            raise ValueError("data task lifecycle has invalid " + key)
        if len({tuple(edge) for edge in edges}) != len(edges) or any(edge[0] in policy["terminal"] for edge in edges):
            raise ValueError("data task lifecycle repeats transition or mutates terminal state")
    if any(after != policy["running"] for _, after in policy["new_attempt"]):
        raise ValueError("new task attempt must enter running state")
    return policy


def render_data_task_guard(content: bytes, template: str) -> str:
    """Lower only declared lifecycle literals; all ownership/fence checks stay in SQL."""
    policy = data_task_lifecycle(content)

    def quote(value):
        return "'" + value.replace("'", "''") + "'"

    def transitions(key):
        return "(OLD.status,NEW.status) IN (" + ",".join(
            "(" + quote(before) + "," + quote(after) + ")"
            for before, after in policy[key]
        ) + ")"

    products = {
        "INITIAL": quote(policy["initial"]),
        "RUNNING": quote(policy["running"]),
        "TERMINAL": ",".join(map(quote, policy["terminal"])),
        "RECEIPT_REQUIRED": ",".join(map(quote, policy["receipt_required"])),
        "NEW_ATTEMPT": transitions("new_attempt"),
        "SAME_ATTEMPT": transitions("same_attempt"),
    }
    for name, value in products.items():
        token = "__DDO_TASK_" + name + "__"
        if token not in template:
            raise ValueError("data task guard lacks lifecycle projection " + name)
        template = template.replace(token, value)
    if "__DDO_TASK_" in template:
        raise ValueError("data task guard has unresolved lifecycle projection")
    return template
