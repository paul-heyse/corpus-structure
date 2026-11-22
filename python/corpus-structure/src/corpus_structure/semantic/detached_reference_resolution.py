"""Resolve role-relative references inside an authenticated captured closure."""

from __future__ import annotations

from collections.abc import Sequence

from ._data_operation_wire import WireOutputMember
from .data_operation_subjects import subject_field_path
from .data_operation_values import decode_semantic_value
from .data_product_reference import read_semantic_reference
from .reference_resolution import (
    AcquiredReferencePartition,
    ProducingReferenceBindings,
    ProducingReferenceInput,
    ReferenceResolver,
    ReferenceTarget,
)


class IndexedReferenceAccess:
    """Keyed body packets from a support index already acquired by its caller."""

    def __init__(self, row_map, project_id: str):
        self.project_id = project_id
        self.products = row_map("kb.data_product", "id")
        self.members = row_map("kb.data_product_member", "product_id", "member_id")
        self.partitions = row_map(
            "kb.data_product_partition", "product_id", "collection", "partition_key"
        )
        self.kinds = row_map("sem.data_kind_contract", "kind_contract")

    def authorize(self, binding: ProducingReferenceInput) -> None:
        row = self.products.get(binding.product_id)
        if row is None or row["project_id"] != self.project_id:
            raise ValueError("captured reference parent is outside the authenticated closure")

    def product(self, product_id: str):
        return decode_semantic_value(self.products[product_id]["canonical_body"])

    def member(self, product_id: str, member_id: str):
        return decode_semantic_value(self.members[product_id, member_id]["body"])

    def partition(self, product_id: str, collection: str, partition_key: str):
        partition = self.partitions[product_id, collection, partition_key]
        kind = self.kinds[self.products[product_id]["kind_contract"]]
        spec = kind["collections"]["declarations"][collection]
        return AcquiredReferencePartition(
            partition["partition_digest"], partition["body"], tuple(spec["address"])
        )


def reference_input_occurrence(access, bound, pointer):
    if pointer is None:
        return None
    access.authorize(bound)
    value = (
        access.product(bound.product_id)
        if bound.member_id is None
        else access.member(bound.product_id, bound.member_id)
    )
    for part in subject_field_path(pointer):
        if not isinstance(value, dict) or part not in value:
            raise ValueError("producing input lacks its declared occurrence")
        value = value[part]
    if not isinstance(value, str) or not value:
        raise ValueError("producing input occurrence must be a nonempty string")
    return value


def _reference_values(body, pointer):
    if not pointer:
        yield body
        return
    values = [body]
    for step in subject_field_path(pointer):
        if step == "*":
            if any(not isinstance(value, list) for value in values):
                raise ValueError("captured reference member step requires an array")
            values = [entry for value in values for entry in value]
        else:
            if any(not isinstance(value, dict) for value in values):
                raise ValueError("captured reference property step requires a record")
            values = [value[step] for value in values if step in value and value[step] is not None]
    yield from values


def _output_bodies(output, collection):
    product = output["product"]
    if collection is not None:
        for packet in product.get("partitions", ()):
            if packet["collection"] == collection:
                yield from decode_semantic_value(packet["body"])
    elif (member_id := output.get("member_id")) is not None:
        (packet,) = [packet for packet in product["members"] if packet["member_id"] == member_id]
        yield decode_semantic_value(packet["body"])
    else:
        yield decode_semantic_value(product["body"])


def require_detached_output_references(
    *,
    row_map,
    rows_for,
    derivation_id: str,
    project_id: str,
    targets: list[dict],
    outputs: Sequence[WireOutputMember],
) -> None:
    """Check output references after authenticating their producing derivation and manifest."""
    access = IndexedReferenceAccess(row_map, project_id)
    captured = tuple(rows_for("ops.data_derivation_input", derivation_id=derivation_id))
    for target in targets:
        bindings = []
        occurrence_field = target.get("occurrence_field")
        for row in captured:
            if row["role"] != target["input_role"]:
                continue
            parent = access.products.get(row["product_id"])
            if parent is None:
                raise ValueError("captured reference is missing its producing input")
            member_id = row.get("member_id")
            kind = (
                parent["kind_contract"]
                if member_id is None
                else access.members[row["product_id"], member_id]["kind_contract"]
            )
            if access.kinds[kind]["kind"] != target["input_kind"]:
                raise ValueError(
                    "captured producing input differs from its declared reference kind"
                )
            provisional = ProducingReferenceInput(row["role"], row["product_id"], kind, member_id)
            bindings.append(
                ProducingReferenceInput(
                    row["role"],
                    row["product_id"],
                    kind,
                    member_id,
                    reference_input_occurrence(access, provisional, occurrence_field),
                    row["multiplicity"],
                    occurrence_field,
                )
            )
        original = ProducingReferenceBindings(derivation_id, tuple(bindings))
        resolver = ReferenceResolver(original, access)
        for output in outputs:
            if output["role"] != target["output_role"]:
                continue
            for body in _output_bodies(output, target.get("output_collection")):
                for value in _reference_values(body, target["path"]):
                    reference = read_semantic_reference(value)
                    binding = original.resolve(reference, occurrence_field=occurrence_field)
                    resolver.resolve(
                        reference,
                        ReferenceTarget(
                            target["input_role"],
                            target["variant"],
                            binding.kind_contract,
                            target.get("collection"),
                            occurrence_field,
                        ),
                    )
