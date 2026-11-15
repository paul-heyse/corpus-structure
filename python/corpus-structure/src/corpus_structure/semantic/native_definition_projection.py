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
    subject_definition: str
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
    expected_subjects = {operation.semantic_id: operation.subject for operation in model.operations}
    actual_subjects = {
        row["operation_id"]: row["subject_definition"] for row in projection["operations"]
    }
    if actual_subjects != expected_subjects:
        raise ValueError("native operation subjects differ from the checked effective model")
    identities = {(item.owner, item.domain): item.key for item in model.identities}
    projected_kinds = {row["kind"]: row["kind_contract"] for row in projection["kinds"]}
    if len(projected_kinds) != len(projection["kinds"]):
        raise ValueError("native definition projection repeats a nominal kind")
    for operation in model.operations:
        kind = model.subject_definition(operation.subject).identifier_kind
        contract = identities.get((kind, "kind"))
        if contract is None or projected_kinds.get(kind) != contract:
            raise ValueError(
                "native subject identifier kind differs from the checked effective model"
            )
    expected_policies = {
        operation.semantic_id: operation.replicate_policy for operation in model.operations
    }
    actual_policies = {
        row["operation_id"]: row["support_contract"].get("replicate_policy")
        for row in projection["operations"]
    }
    from typing import get_args

    from .data_operation_model import ReplicatePolicy

    if any(policy not in get_args(ReplicatePolicy) for policy in actual_policies.values()):
        raise ValueError("unsupported native operation replicate policy")
    if actual_policies != expected_policies:
        raise ValueError(
            "native operation replicate policies differ from the checked effective model"
        )
    import json

    expected_coverage = {
        operation["semantic_id"]: operation["coverage"]
        for operation in json.loads(model.content)["operations"]
    }
    actual_coverage = {
        operation["operation_id"]: operation["support_contract"].get("coverage")
        for operation in projection["operations"]
    }
    if actual_coverage != expected_coverage:
        raise ValueError("native operation coverage differs from the checked effective model")
    return projection


DefinitionVariant = Literal["components", "applicability", "location"]


def definition_variant_contract(model, projection, variant: DefinitionVariant) -> str | None:
    """Resolve an explicit kind-owned association, never an IRI/name convention."""
    import json
    from typing import get_args

    owners = {}
    for kind in model.kinds:
        facts = json.loads(kind.facts)
        schema_value = (facts.get("json_schema") or {}).get("x-ddo-definition-variant")
        policy_value = (facts.get("policies") or {}).get("cs:definition_variant")
        values = {value for value in (schema_value, policy_value) if value is not None}
        if len(values) > 1 or any(value not in get_args(DefinitionVariant) for value in values):
            raise ValueError("invalid definition-variant association")
        if values:
            name = next(iter(values))
            if name in owners:
                raise ValueError("ambiguous definition-variant association")
            owners[name] = kind.semantic_id
    owner = owners.get(variant)
    if owner is None:
        return None
    matches = [row["kind_contract"] for row in projection["kinds"] if row["kind"] == owner]
    if len(matches) != 1:
        raise ValueError("definition variant lacks one admitted nominal kind")
    return matches[0]
