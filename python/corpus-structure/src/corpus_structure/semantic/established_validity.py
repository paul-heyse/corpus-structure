"""Actual trusted-producer validation, retained in its original sealed intent.

This is a record of successful Python validation, not independent native replay or
current support authority. Readers still acquire current support and caller rights.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from .data_operation_identity import body_identity, canonical_identity
from .data_operation_json import json_loads, scope_identity
from .data_operation_partitions import partition_group_digests
from .data_operation_values import decode_semantic_value, semantic_value

if TYPE_CHECKING:
    from ._data_operation_wire import WireOutputMember, WireProductPartition
    from .data_operation_model import EffectiveDataRule, EffectiveKind, SubjectContext


class RuleAttestation(BaseModel):
    """Assertion emitted by the declared checker for one exact producer output."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    rule_id: str = Field(min_length=1)
    rule_fingerprint: str = Field(min_length=1)
    premise: str = Field(min_length=1)
    output_role: str = Field(min_length=1)
    output_position: int = Field(ge=0)
    partition_key: str | None = Field(min_length=1)


def _observed_field(value, path: str):
    for segment in path.split("."):
        if not isinstance(value, Mapping) or segment not in value:
            return None
        value = value[segment]
    return semantic_value(value)


@dataclass(frozen=True)
class RuleObservedInput:
    """An actual acquired role value, in the order seen by the checker."""

    value: object
    multiplicity: int = 1


def successful_rule_attestation(
    rule: EffectiveDataRule,
    kind: EffectiveKind,
    operation: str,
    output: WireOutputMember,
    context: SubjectContext,
    *,
    partition: WireProductPartition | None = None,
    selected_inputs: Mapping[str, Sequence[RuleObservedInput]] | None = None,
) -> RuleAttestation:
    """Project the output or exact partition the declared checker just validated."""
    if (
        rule.checker != "producer"
        or rule.checker_operation != operation
        or not rule.checker_determinant
        or rule.kind != kind.semantic_id
        or rule.kind_contract != output["product"]["kind_contract"]
        or output.get("member_id") is not None
        or rule.scope not in ("partition", "product")
        or (rule.scope == "partition") != (partition is not None)
        or (partition is not None and partition["collection"] != rule.collection)
    ):
        raise ValueError("attestation requires its declared checker and exact whole-output scope")
    product = output["product"]
    reads = tuple(read for read in rule.reads if read.side == "source")
    paths = {read.path for read in reads}
    whole = "$all" in paths
    observed = {path for path in paths if not path.startswith("$")}
    if rule.collection is None:
        body = decode_semantic_value(product["body"])
        facts = [
            body_identity(body).key if whole else None,
            {path: _observed_field(body, path) for path in observed} or None,
        ]
    else:
        declaration = json_loads(kind.facts)["collections"][rule.collection]
        group_names = {group for read in reads for group in read.groups}
        groups = {name: declaration["field_groups"][name] for name in group_names}
        exact = {read.path for read in reads if read.path in observed and not read.groups}
        partitions = (
            (partition,)
            if partition is not None
            else sorted(
                (
                    packet
                    for packet in product.get("partitions", [])
                    if packet["collection"] == rule.collection
                ),
                key=lambda packet: packet["partition_key"],
            )
        )
        facts = []
        for packet in partitions:
            placement = packet["placement"]
            items = decode_semantic_value(packet["body"]) if groups or exact else ()
            facts.append(
                [
                    packet["partition_key"] if partition is None else None,
                    packet["ordinal"] if rule.scope == "product" and whole else None,
                    placement["start"] if whole or "$placement.start" in paths else None,
                    placement["end"] if whole or "$placement.end" in paths else None,
                    packet["partition_digest"] if whole else None,
                    partition_group_digests(items, groups) or None,
                    {path: [_observed_field(item, path) for item in items] for path in exact}
                    or None,
                ]
            )
    pins = [
        context.original_source if whole or "$source" in paths else None,
        json_loads(context.analyzed_scope) if whole or "$analyzed_scope" in paths else None,
    ]
    # PostgreSQL wraps projected facts in JSONB before tagging. Apply those same
    # decimal-value semantics to plain placement, order and scope numbers.
    premise = canonical_identity(
        "rule-premise", scope_identity([rule.scope, facts, None, pins])
    ).key
    input_reads = json_loads(rule.parameters).get("input_reads", {})
    supplied = selected_inputs or {}
    if supplied.keys() != input_reads.keys():
        raise ValueError("attestation requires every declared observed input role")
    if input_reads:
        observed_inputs = [
            [
                name,
                [
                    [
                        row.multiplicity,
                        [
                            body_identity(row.value).key
                            if path == "$all"
                            else _observed_field(row.value, path)
                            for path in paths
                        ],
                    ]
                    for row in supplied[name]
                ],
            ]
            for name, paths in sorted(input_reads.items())
        ]
        premise = canonical_identity(
            "rule-observed-premise", scope_identity([premise, observed_inputs])
        ).key
    return RuleAttestation(
        rule_id=rule.id,
        rule_fingerprint=rule.fingerprint,
        premise=premise,
        output_role=output["role"],
        output_position=output["position"],
        partition_key=partition["partition_key"] if partition is not None else None,
    )
