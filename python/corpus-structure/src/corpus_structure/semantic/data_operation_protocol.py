"""Pure DDO projections of explicitly supplied authoritative protocol bytes."""

from __future__ import annotations

from hashlib import sha256

import yaml
from linkml_runtime.utils.yamlutils import DupCheckYamlLoader

from corpus_structure.schema.integrity import role_name

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
    if (
        any(
            not isinstance(policy[key], str) or policy[key] not in states
            for key in ("initial", "running")
        )
        or policy["initial"] == policy["running"]
    ):
        raise ValueError("data task lifecycle has invalid initial/running state")
    for key in ("terminal", "receipt_required"):
        values = policy[key]
        if (
            not isinstance(values, list)
            or not values
            or any(not isinstance(value, str) for value in values)
            or len(values) != len(set(values))
            or not set(values) <= states
        ):
            raise ValueError("data task lifecycle has invalid " + key)
    if not set(policy["receipt_required"]) <= set(policy["terminal"]) or {
        policy["initial"],
        policy["running"],
    } & set(policy["terminal"]):
        raise ValueError("data task terminal/receipt policy overlaps live states")
    if states != {policy["initial"], policy["running"], *policy["terminal"]}:
        raise ValueError("data task lifecycle leaves an unclassified state")
    for key in ("new_attempt", "same_attempt"):
        edges = policy[key]
        if (
            not isinstance(edges, list)
            or not edges
            or any(
                not isinstance(edge, list)
                or len(edge) != 2
                or any(not isinstance(state, str) or state not in states for state in edge)
                for edge in edges
            )
        ):
            raise ValueError("data task lifecycle has invalid " + key)
        if len({tuple(edge) for edge in edges}) != len(edges) or any(
            edge[0] in policy["terminal"] for edge in edges
        ):
            raise ValueError("data task lifecycle repeats transition or mutates terminal state")
    if any(after != policy["running"] for _, after in policy["new_attempt"]):
        raise ValueError("new task attempt must enter running state")
    return policy


def render_data_task_guard(content: bytes, *, target_metadata) -> str:
    """Compile captured task columns and lifecycle policy into the trigger program."""
    from sqlalchemy import Text, and_, exists, func, or_, select, tuple_

    from .native_program import Block, If, Raise, Return, core_variable, function, pg_type, variable

    policy = data_task_lifecycle(content)
    task = target_metadata.tables["ops.task"]
    requests = target_metadata.tables["ops.data_request"]
    new = {column.name: core_variable("new", column.type, column.name) for column in task.c}
    old = {column.name: core_variable("old", column.type, column.name) for column in task.c}
    state_transition = tuple_(old["status"], new["status"])

    def check(condition, message, sqlstate="P0001"):
        return If(condition, (Raise(message, sqlstate),))

    claim = check(
        or_(
            new["attempt"] != old["attempt"] + 1,
            new["status"] != policy["running"],
            func.nullif(new["claimed_by"], "").is_(None),
            new["lease_until"].is_(None),
            new["lease_until"] <= func.pg_catalog.clock_timestamp(),
            ~state_transition.in_([tuple(edge) for edge in policy["new_attempt"]]),
            and_(
                old["status"] == policy["running"],
                or_(
                    old["lease_until"].is_(None),
                    old["lease_until"] > func.pg_catalog.clock_timestamp(),
                ),
            ),
        ),
        "invalid data claim fence",
    )
    initial = check(
        or_(
            new["status"] != policy["initial"],
            new["attempt"] != 0,
            new["claimed_by"].is_not(None),
            new["lease_until"].is_not(None),
        ),
        "invalid initial data task",
    )
    association = ("data_request_id", "data_generation", "release_id", "invocation_key")
    update = (
        check(
            or_(
                tuple_(*(new[name] for name in association)).is_distinct_from(
                    tuple_(*(old[name] for name in association))
                ),
                old["status"].in_(policy["terminal"]),
            ),
            "data task association/terminal state immutable",
        ),
        If(
            new["attempt"] != old["attempt"],
            (claim,),
            (
                If(
                    new["claimed_by"].is_distinct_from(old["claimed_by"]),
                    (Raise("data holder requires new attempt", "P0001"),),
                    (
                        check(
                            and_(
                                new["status"] != old["status"],
                                ~state_transition.in_(
                                    [tuple(edge) for edge in policy["same_attempt"]]
                                ),
                            ),
                            "invalid data task transition",
                        ),
                    ),
                ),
            ),
        ),
    )
    return function(
        "ops",
        "guard_execution_task",
        parameters=(),
        returns=pg_type("trigger"),
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                check(
                    or_(new["data_request_id"].is_(None), new["data_generation"].is_(None)),
                    "physical task requires declared request generation",
                    "23514",
                ),
                check(
                    or_(
                        func.current_user() != role_name("publisher"),
                        ~exists(
                            select(1)
                            .select_from(requests)
                            .where(
                                requests.c.id == new["data_request_id"],
                                requests.c.release_id == new["release_id"],
                                requests.c.generation == new["data_generation"],
                            )
                        ),
                    ),
                    "data task requires protected admitted request generation",
                    "23514",
                ),
                If(core_variable("tg_op", Text()) == "INSERT", (initial,), update),
                check(
                    and_(
                        new["status"] == policy["running"],
                        or_(
                            new["attempt"] <= 0,
                            new["claimed_by"].is_(None),
                            new["lease_until"].is_(None),
                        ),
                    ),
                    "data running task requires exact fence",
                ),
                check(
                    and_(new["status"] != policy["running"], new["lease_until"].is_not(None)),
                    "data terminal task retains lease",
                ),
                check(
                    and_(
                        new["status"].in_(policy["receipt_required"]),
                        new["result_digest"].is_(None),
                    ),
                    "data completion requires receipt",
                ),
                Return(variable("new")),
            )
        ),
    )
