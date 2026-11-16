"""Exact declared formal inventories for shared positioned downstream readers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from .data_operation_identity import decode_semantic_value
from .data_operation_json import json_bytes, json_loads
from .data_product_reference import DataProductReference, member_reference
from .identity import canonical_bytes


@dataclass(frozen=True)
class DeclaredFormalInventory:
    """One validated target inventory; the product reference remains semantic."""

    reference: DataProductReference
    inventory_content: bytes

    @property
    def payload(self) -> dict[str, Any]:
        return json_loads(self.inventory_content)


def declared_formal_layers(products, source):
    """Freeze original-source inventories once, without any task/layer projection."""
    selected = source.value
    result = {}
    for product in products:
        body = product.value
        if isinstance(body, BaseModel):
            body = body.model_dump(mode="json", exclude_unset=True)
        if canonical_bytes(body["source"]) != canonical_bytes(
            selected["source"]
        ) or canonical_bytes(body["selectors"]) != canonical_bytes(selected["selectors"]):
            raise ValueError(
                "formal inventory differs from its exact original source and analyzed scope"
            )
        reference = DataProductReference(product.semantic_id)
        if reference in result:
            raise ValueError("formal input repeats a selected native product")
        result[reference] = DeclaredFormalInventory(
            reference,
            canonical_bytes(
                {
                    **product.inventory(),
                    "source": body["source"],
                    "selectors": body["selectors"],
                    "dependencies": body.get("dependencies", []),
                }
            ),
        )
    return result


def formal_member_reference(product: DataProductReference, identifier):
    """Positioned evidence retains its exact current semantic product/member address."""
    if not isinstance(product, DataProductReference):
        raise TypeError("positioned formal evidence requires its actual nominal product reference")
    return member_reference(product, identifier)


class SelectedCharacterizationInventories(Mapping):
    """Lazy pinned native product inventories; disk owns the full required closure."""

    def __init__(self, products):
        self.products = products

    def __getitem__(self, reference):
        if not isinstance(reference, DataProductReference):
            raise KeyError(reference)
        record = self.products[reference.product_id]
        body = decode_semantic_value(record["canonical_body"])
        if not isinstance(body, dict) or not {"source", "selectors", "members"} <= body.keys():
            raise ValueError("selected primary dependency is not a declared characterization")
        names = dict(
            occurrence="occurrences",
            annotation="annotations",
            membership="memberships",
            role="roles",
            term="terms",
            choice="choices",
            native_block="native_block",
            native_token="native_token",
            native_sentence="native_sentence",
        )
        inventory = {name: [] for name in names.values()}
        seen = set()
        for packet in body["members"]:
            member = packet["body"]
            kind = member.get("record_type")
            if kind not in names:
                continue
            identifier = member["local_id"]
            if packet["member_id"] != identifier or identifier in seen:
                raise ValueError("selected characterization has ambiguous semantic member identity")
            seen.add(identifier)
            if kind in {"native_block", "native_token", "native_sentence"}:
                from .sentence_products import _id
                from .source_products import source_subject

                context = dict(
                    subject=source_subject(body["source"]),
                    subject_definition="original-source-view",
                    original_source=body["source"]["document"],
                    analyzed_scope=dict(source=body["source"], selectors=body["selectors"]),
                )
                if packet["context"] != context or identifier != _id(
                    body["source"],
                    kind.removeprefix("native_"),
                    member["block_id"],
                    member["start"],
                    member["end"],
                ):
                    raise ValueError("selected native member changes its declared source identity")
            inventory[names[kind]].append(member)
        inventory.update(
            source=body["source"],
            selectors=body["selectors"],
            dependencies=body.get("dependencies", []),
        )
        return DeclaredFormalInventory(reference, json_bytes(inventory))

    def __iter__(self):
        return (DataProductReference(key) for key in self.products)

    def __len__(self):
        return len(self.products)
