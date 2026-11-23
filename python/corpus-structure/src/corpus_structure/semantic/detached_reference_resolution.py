"""Resolve role-relative references inside an authenticated captured closure."""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import closing
from functools import partial

from ._data_operation_wire import WireOutputMember
from .data_operation_subjects import subject_field_path
from .data_operation_values import decode_semantic_value
from .data_product_reference import read_semantic_reference
from .reference_resolution import (
    AcquiredReferencePartition,
    CapturedPartitionItems,
    ProducingReferenceBindings,
    ProducingReferenceInput,
    ReferenceResolver,
    ReferenceTarget,
)


class IndexedReferenceAccess:
    """Keyed body packets from a support index already acquired by its caller."""

    def __init__(self, row_map, project_id: str, *, product_headers=None, population_archive=None):
        self.project_id = project_id
        self.products = row_map("kb.data_product", "id")
        self.members = row_map("kb.data_product_member", "product_id", "member_id")
        self.partitions = row_map(
            "kb.data_product_partition", "product_id", "collection", "partition_key"
        )
        self.kinds = row_map("sem.data_kind_contract", "kind_contract")
        self._product_headers = {} if product_headers is None else product_headers
        self._complete_product_headers = product_headers is not None
        self._population_archive = population_archive
        self._partition_items = CapturedPartitionItems()

    def product_header(self, product_id: str) -> dict[str, str] | None:
        if product_id not in self._product_headers and not self._complete_product_headers:
            row = self.products.get(product_id)
            if row is None:
                return None
            self._product_headers[product_id] = {
                field: row[field] for field in ("project_id", "kind_contract") if field in row
            }
        return self._product_headers.get(product_id)

    def authorize(self, binding: ProducingReferenceInput) -> None:
        row = self.product_header(binding.product_id)
        if row is None or row["project_id"] != self.project_id:
            raise ValueError("captured reference parent is outside the authenticated closure")

    def product(self, product_id: str):
        return decode_semantic_value(self.products[product_id]["canonical_body"])

    def member(self, product_id: str, member_id: str):
        return decode_semantic_value(self.members[product_id, member_id]["body"])

    def item(self, product_id, collection, partition_key, item_key):
        if self._population_archive is not None:
            try:
                return self._population_archive.item(
                    product_id, collection, partition_key, item_key
                )
            except KeyError:
                pass
        return self._partition_items.item(
            (product_id, collection, partition_key), item_key, self._partition
        )

    def _partition(self, product_id: str, collection: str, partition_key: str):
        partition = self.partitions[product_id, collection, partition_key]
        parent = self.product_header(product_id)
        if parent is None:
            raise KeyError(product_id)
        kind = self.kinds[parent["kind_contract"]]
        spec = kind["collections"]["declarations"][collection]
        return AcquiredReferencePartition(
            partition["partition_digest"], partition["body"], tuple(spec["address"])
        )


def reference_role_contracts(input_roles, target) -> tuple[str, ...]:
    """Read the admitted nominal family for the exact declared producing role."""
    roles = tuple(
        role
        for role in input_roles
        if role["name"] == target["input_role"] and role["kind"] == target["input_kind"]
    )
    if len(roles) != 1:
        raise ValueError("reference lacks its one admitted producing input role")
    return tuple(roles[0]["accepted_kind_contracts"])


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


def _output_bodies(output, collection, *, population_archive=None, product_id=None):
    product = output["product"]
    if collection is not None:
        if population_archive is not None and product_id is not None:
            from .data_operation_json import native_json_loads
            from .selected_population_archive import POPULATION_HEADERS, POPULATION_ITEMS

            fields = dict(product_id=product_id, collection=collection)
            with closing(population_archive.rows(POPULATION_HEADERS, **fields)) as headers:
                present = next(headers, None) is not None
            if present:
                for row in population_archive.rows(POPULATION_ITEMS, **fields):
                    yield decode_semantic_value(native_json_loads(row["canonical_text"]))
                return
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
    input_roles: Sequence[dict],
    outputs: Sequence[WireOutputMember],
    product_headers=None,
    population_archive=None,
    output_products=None,
) -> None:
    """Check output references after authenticating their producing derivation and manifest."""
    access = IndexedReferenceAccess(
        row_map, project_id, product_headers=product_headers, population_archive=population_archive
    )
    captured = tuple(rows_for("ops.data_derivation_input", derivation_id=derivation_id))
    decoded_outputs = {}
    checked_contribution_outputs = set()
    for target in targets:
        contracts = reference_role_contracts(input_roles, target)
        bindings = []
        occurrence_field = target.get("occurrence_field")
        occurrence_binding = target.get("occurrence_binding", False)
        occurrence_position = target.get("occurrence_position", False)
        for row in captured:
            if row["role"] != target["input_role"]:
                continue
            parent = access.product_header(row["product_id"])
            if parent is None:
                raise ValueError("captured reference is missing its producing input")
            member_id = row.get("member_id")
            kind = (
                parent["kind_contract"]
                if member_id is None
                else access.members[row["product_id"], member_id]["kind_contract"]
            )
            if kind not in access.kinds or kind not in contracts:
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
                    row.get("occurrence_label")
                    if occurrence_binding
                    else str(row["position"])
                    if occurrence_position
                    else reference_input_occurrence(access, provisional, occurrence_field),
                    row["multiplicity"],
                    occurrence_field,
                    occurrence_binding,
                    occurrence_position,
                )
            )
        original = ProducingReferenceBindings(derivation_id, tuple(bindings))
        resolver = ReferenceResolver(original, access)
        for output in outputs:
            if output["role"] != target["output_role"]:
                continue
            location = id(output), target.get("output_collection")
            if location not in decoded_outputs:
                decoded_outputs[location] = tuple(
                    _output_bodies(
                        output,
                        location[1],
                        population_archive=population_archive,
                        product_id=(output_products or {}).get(
                            (output["role"], output["position"])
                        ),
                    )
                )
            for body in decoded_outputs[location]:
                choice_references = set()
                if isinstance(body, dict) and "formal_member_support" in body:
                    from .contextual_input_references import CONTEXTUAL_MEMBER_FIELDS

                    choice_references = {
                        read_semantic_reference(slot["target"])
                        for field in CONTEXTUAL_MEMBER_FIELDS
                        if target["path"] == "/" + field + "/*/target"
                        for slot in body[field]
                        if slot["use"] in {"choice", "basis_choice", "choices"}
                    }
                contribution_members = None
                if isinstance(body, dict) and "construction_support" in body:
                    from .contribution_input_references import check_contribution_input_support

                    if id(body) not in checked_contribution_outputs:
                        check_contribution_input_support(body)
                        checked_contribution_outputs.add(id(body))
                    contribution_members = {
                        packet["member_id"]: packet["body"] for packet in body["members"]
                    }
                    for field in ("construction_support", "formal_support"):
                        if target["path"] == "/" + field + "/*/target":
                            choice_references.update(
                                read_semantic_reference(slot["target"])
                                for slot in body[field]
                                if slot["field"].split("/")[-1] == "primary_choices"
                            )
                for value in _reference_values(body, target["path"]):
                    reference = read_semantic_reference(value)
                    binding = original.resolve(
                        reference,
                        occurrence_field=occurrence_field,
                        occurrence_binding=occurrence_binding,
                        occurrence_position=occurrence_position,
                    )
                    declared = ReferenceTarget(
                        target["input_role"],
                        target["variant"],
                        binding.kind_contract,
                        target.get("collection"),
                        occurrence_field,
                        occurrence_binding,
                        occurrence_position,
                    )
                    if target["variant"] == reference.variant == "product":
                        if binding.member_id is not None:
                            raise ValueError(
                                "whole reference is outside its producing input member"
                            )
                        access.authorize(binding)
                        continue
                    resolved = resolver.resolve(reference, declared)
                    if (
                        contribution_members is not None
                        and target["path"] == "/inherited_support/*/target"
                    ):
                        for slot in body["inherited_support"]:
                            if (
                                read_semantic_reference(slot["target"]) == reference
                                and contribution_members[slot["member_id"]] != resolved
                            ):
                                raise ValueError(
                                    "inherited contribution differs from its original predicate member"
                                )
                    if reference in choice_references:
                        from .contextual_input_references import (
                            require_contextual_choice_alternative,
                        )

                        require_contextual_choice_alternative(
                            reference, resolved, partial(resolver.resolve, target=declared)
                        )
