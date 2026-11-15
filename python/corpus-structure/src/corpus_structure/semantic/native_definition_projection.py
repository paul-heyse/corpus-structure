"""One typed read boundary for captured native definition projections.

Reading authenticates the model binding; it grants no native admission or effect.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any, Literal, TypedDict

from pydantic import ConfigDict, TypeAdapter, with_config


@with_config(ConfigDict(extra="forbid"))
class NativeKindProjection(TypedDict):
    kind_contract: str
    kind: str
    body_schema: dict[str, Any]
    meaning_schema: dict[str, Any]
    member_schema: dict[str, Any]
    member_contracts: list[str]
    families: list[str]
    universe: Literal["ordinary", "source", "evaluator"]


@with_config(ConfigDict(extra="forbid"))
class NativeOperationProjection(TypedDict):
    operation_id: str
    recipe: str
    profile: str
    binding: dict[str, Any]
    definition: str
    eligibility: str
    implementation_revision: str
    input_roles: list[dict[str, Any]]
    output_roles: list[dict[str, Any]]
    support_contract: dict[str, Any]


@with_config(ConfigDict(extra="forbid"))
class NativeDefinitionProjection(TypedDict):
    model_digest: str
    native_digest: str
    kinds: list[NativeKindProjection]
    operations: list[NativeOperationProjection]


_ADAPTER = TypeAdapter(NativeDefinitionProjection)


def read_native_definition_projection(prepared, *, model=None) -> NativeDefinitionProjection:
    from .data_operation_admission import bound_data_operation_model

    if model is None:
        model = bound_data_operation_model(prepared)
    artifacts = [
        artifact
        for artifact in prepared.artifacts
        if artifact.kind == "data_operation_native_definitions.json"
    ]
    if len(artifacts) != 1:
        raise ValueError("release requires exactly one native definition projection")
    projection = _ADAPTER.validate_json(artifacts[0].content, strict=True)
    if projection["model_digest"] != sha256(model.content).hexdigest():
        raise ValueError("native definition projection belongs to another effective model")
    kinds = [row["kind_contract"] for row in projection["kinds"]]
    operations = [row["operation_id"] for row in projection["operations"]]
    if len(set(kinds)) != len(kinds) or len(set(operations)) != len(operations):
        raise ValueError("native definition projection repeats a nominal identity")
    return projection
