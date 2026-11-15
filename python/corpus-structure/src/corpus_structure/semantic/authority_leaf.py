"""Explicit bounded public provenance for a native-issued protected conclusion."""

from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class NativeAuthorityLeaf(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    format: Literal["ddo-native-authority-leaf-v1"]
    derivation_id: str = Field(min_length=1)
    use_id: str | None
    issuer_operation: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    runtime_id: str = Field(min_length=1)
    recipe: str = Field(min_length=1)
    product_id: str = Field(min_length=1)
    kind_contract: str = Field(min_length=1)
    intent_id: str = Field(min_length=1)
    receipt_id: str = Field(min_length=1)
    standing: Literal["valid", "unavailable"]
    protected_dependencies: Literal["undisclosed"]


def validate_authority_leaf(value, *, products, kinds, definitions, runtimes, schema=None):
    """Check a bounded native assertion against actual captured release contracts.

    This establishes exported interpretation, never current native permission or
    independent verification of hidden judgments. Its capture custodian supplies
    authenticity just as for other exported native rows.
    """
    from .record_policy_authority import (
        AUTHORIZATION_EFFECT, AUTHORIZATION_FACTORY, AUTHORIZATION_KIND, AUTHORIZATION_OPERATION,
        DdoRecordPolicyAuthorization,
    )

    if schema is not None:
        from jsonschema import Draft7Validator

        Draft7Validator(schema).validate(value)
    leaf = NativeAuthorityLeaf.model_validate(value)
    if definitions is None or runtimes is None or kinds is None:
        raise ValueError("bounded authority requires its captured release/kind/runtime contracts")
    definition = definitions.get((leaf.release_id, leaf.issuer_operation))
    product = products.get(leaf.product_id)
    kind = kinds.get(leaf.kind_contract)
    if (
        leaf.issuer_operation != AUTHORIZATION_OPERATION or definition is None
        or product is None or product["kind_contract"] != leaf.kind_contract
        or kind is None or kind["kind"] != AUTHORIZATION_KIND or kind["universe"] != "ordinary"
        or (leaf.release_id, leaf.runtime_id) not in runtimes
    ):
        raise ValueError("bounded authority differs from its captured issuer or ordinary output")
    support = definition["support_contract"]
    effect = {**asdict(AUTHORIZATION_EFFECT), "authorization": list(AUTHORIZATION_EFFECT.authorization)}
    capability = support.get("capabilities", {})
    if (
        definition["profile"] != "command" or definition["recipe"] != leaf.recipe
        or support.get("effects") != [effect]
        or capability.get("preparation") != "native-publication"
        or capability.get("forms") != ["scalar"]
        or capability.get("prepared_factory", {}).get("entrypoint") != AUTHORIZATION_FACTORY
    ):
        raise ValueError("bounded authority differs from its captured command/effect/factory")
    from .data_operation_identity import decode_semantic_value
    from .identity import canonical_bytes

    DdoRecordPolicyAuthorization.model_validate_json(canonical_bytes(decode_semantic_value(product["canonical_body"])))
    return leaf
