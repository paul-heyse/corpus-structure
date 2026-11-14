"""Exact declared formal inventories for shared positioned downstream readers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pydantic import BaseModel
from typing import Any

from .data_product_reference import DataProductReference, member_reference
from .identity import canonical_bytes


@dataclass(frozen=True)
class DeclaredFormalInventory:
    """One validated target inventory; the product reference remains semantic."""

    reference: DataProductReference
    inventory_content: bytes

    @property
    def payload(self) -> dict[str, Any]:
        return json.loads(self.inventory_content)


def declared_formal_layers(products, source):
    """Freeze original-source inventories once, without any task/layer projection."""
    selected = source.value
    result = {}
    for product in products:
        body = product.value
        if isinstance(body, BaseModel):
            body = body.model_dump(mode="json", exclude_unset=True)
        if canonical_bytes(body["source"]) != canonical_bytes(selected["source"]) or canonical_bytes(body["selectors"]) != canonical_bytes(selected["selectors"]):
            raise ValueError("formal inventory differs from its exact original source and analyzed scope")
        reference = DataProductReference(product.semantic_id)
        if reference in result:
            raise ValueError("formal input repeats a selected native product")
        result[reference] = DeclaredFormalInventory(reference, canonical_bytes(product.inventory()))
    return result


def formal_member_reference(product, identifier):
    """Keep actual target addresses and exact historical replay addresses distinct."""
    if isinstance(product, DataProductReference):
        return member_reference(product, identifier)
    from .product_reference import ProductReference
    from .characterization import annotation_reference

    if isinstance(product, ProductReference):
        return annotation_reference(product, identifier)
    raise TypeError("positioned formal evidence requires its actual nominal product reference")
