"""Exact declared formal inventories for shared positioned downstream readers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import cached_property
from typing import Any

from pydantic import BaseModel

from .data_operation_json import json_bytes, json_loads
from .data_operation_values import decode_semantic_value
from .data_product_reference import DataProductReference, member_reference
from .identity import canonical_bytes


@dataclass(frozen=True)
class DeclaredFormalInventory:
    """One validated target inventory; the product reference remains semantic."""

    reference: DataProductReference
    inventory_content: bytes

    @cached_property
    def payload(self) -> dict[str, Any]:
        return json_loads(self.inventory_content)


class PreparedFormalLayers(Mapping):
    """Original product occurrences and their reusable positioned formal indexes."""

    def __init__(self, layers):
        self.layers = layers
        self.occurrences = {}
        self.nodes = {}
        self.symbols = {}
        self.inputs = []
        self.unprojected_symbols = set()
        self._captured = {}
        self._inline = {}
        for pin, report in layers.items():
            body = report.payload
            self.occurrences[pin] = {row["local_id"]: row for row in body["occurrences"]}
            nodes = self.nodes[pin] = {row["local_id"]: row for row in body["annotations"]}
            for annotation in nodes.values():
                formal = annotation.get("formal")
                if annotation["kind"] == "formal.symbol" and formal is not None:
                    self.symbols.setdefault((pin, formal["input_id"]), []).append(annotation)
                if formal is not None and "SYMBOL" in formal.get("rule", ""):
                    self.unprojected_symbols.add((pin, formal.get("input_id")))
                value = annotation.get("formal_input")
                if value is None:
                    continue
                row = pin, body, annotation, value
                self.inputs.append(row)
                extents = self.occurrences[pin][value["parent_occurrence"]]["extents"]
                if extents:
                    self._captured.setdefault(
                        (value["text"], value["representation"], extents[0].get("start")), []
                    ).append(row)
                if len(extents) == 1:
                    extent = extents[0]
                    self._inline.setdefault(
                        (extent.get("native_pointer"), extent.get("start"), extent.get("end")), []
                    ).append(row)

    def __getitem__(self, key):
        return self.layers[key]

    def __iter__(self):
        return iter(self.layers)

    def __len__(self):
        return len(self.layers)

    def captured_inputs(self, text, representation, source_start):
        return self._captured.get((text, representation, source_start), ())

    def inline_inputs(self, pointer=None, start=None, end=None):
        if pointer is not None and start is not None and end is not None:
            return self._inline.get((pointer, start, end), ())
        return self.inputs


def prepare_formal_layers(layers):
    if isinstance(layers, PreparedFormalLayers):
        return layers
    return PreparedFormalLayers(layers)


def declared_formal_layers(products, source):
    """Freeze original-source inventories once, without any task/layer projection."""
    from .construction_products import InterpretedProduct

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
                    "dependencies": [
                        {"product_id": parent}
                        for parent in (
                            product.dependency_products
                            if isinstance(product, InterpretedProduct)
                            else ()
                        )
                    ],
                }
            ),
        )
    return PreparedFormalLayers(result)


def formal_member_reference(product: DataProductReference, identifier):
    """Positioned evidence retains its exact current semantic product/member address."""
    if not isinstance(product, DataProductReference):
        raise TypeError("positioned formal evidence requires its actual nominal product reference")
    return member_reference(product, identifier)


class SelectedCharacterizationInventories(Mapping):
    """Lazy pinned native product inventories; disk owns the full required closure."""

    def __init__(
        self,
        products,
        *,
        index=None,
        cut=None,
        construction_formal_parents=None,
        contextual_input_parents=None,
        learned_dependencies=None,
    ):
        self.products = products
        self.index = index
        self.cut = cut
        self.construction_formal_parents = construction_formal_parents or {}
        self.contextual_input_parents = contextual_input_parents or {}
        self.learned_dependencies = learned_dependencies or {}

    def __getitem__(self, reference):
        if not isinstance(reference, DataProductReference):
            raise KeyError(reference)
        record = self.products[reference.product_id]
        body = decode_semantic_value(record["canonical_body"])
        contextual_parents = self.contextual_input_parents.get(reference.product_id, ())
        construction_parents = self.construction_formal_parents.get(reference.product_id, ())
        dependency_products = ()
        if not isinstance(body, dict) or not {"source", "selectors", "members"} <= body.keys():
            raise ValueError("selected primary dependency is not a declared characterization")
        if self.index is not None:
            from .construction_formal_references import expand_selected_construction_formal_support
            from .contextual_input_references import expand_selected_contextual_inputs
            from .contextual_proxy_references import expand_selected_contextual_proxies

            body, native_parents = expand_selected_contextual_proxies(
                body, self.index, self.cut, reference.product_id, with_parents=True
            )
            body, construction_inputs = expand_selected_construction_formal_support(
                body, self.index, self.cut, reference.product_id, with_parents=True
            )
            body, contextual_parents = expand_selected_contextual_inputs(
                body, self.index, self.cut, reference.product_id, with_parents=True
            )
            dependency_products = tuple(
                item[2] for item in (*native_parents, *construction_inputs, *contextual_parents)
            )
        elif "formal_support" in body:
            from .construction_formal_references import project_construction_formal_support

            body = project_construction_formal_support(body, construction_parents)
            dependencies = self.learned_dependencies.get(reference.product_id)
            if dependencies is None:
                raise ValueError("construction graph lacks its exact acquired input closure")
            dependency_products = dependencies
        if self.index is None and "formal_member_support" in body:
            from .contextual_input_references import project_contextual_input_support

            body = project_contextual_input_support(body, contextual_parents)
            dependency_products = tuple(item[2] for item in contextual_parents)
        if self.index is None and "formal_proxy_support" in body:
            from .construction_products import CharacterizationSnapshot
            from .contextual_proxy_references import (
                CONTEXTUAL_NATIVE_INPUT_ROLES,
                project_contextual_proxy_graph,
            )

            dependencies = self.learned_dependencies.get(reference.product_id)
            if dependencies is None or len(dependencies) != len(CONTEXTUAL_NATIVE_INPUT_ROLES):
                raise ValueError("native contextual graph lacks its exact acquired input closure")
            inputs = {
                role: CharacterizationSnapshot(
                    parent,
                    json_bytes(decode_semantic_value(self.products[parent]["canonical_body"])),
                )
                for role, parent in zip(CONTEXTUAL_NATIVE_INPUT_ROLES, dependencies, strict=True)
                if role in {"formal", "constructions"}
            }
            body = project_contextual_proxy_graph(body, inputs)
            dependency_products = dependencies
        names = dict(
            occurrence="occurrences",
            annotation="annotations",
            membership="memberships",
            role="roles",
            term="terms",
            choice="choices",
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
            inventory[names[kind]].append(member)
        inventory.update(
            source=body["source"],
            selectors=body["selectors"],
            dependencies=[{"product_id": parent} for parent in dict.fromkeys(dependency_products)],
            annotation_support=body.get("annotation_support", []),
        )
        return DeclaredFormalInventory(reference, json_bytes(inventory))

    def __iter__(self):
        return (DataProductReference(key) for key in self.products)

    def __len__(self):
        return len(self.products)
