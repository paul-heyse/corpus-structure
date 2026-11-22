"""Interpret producing addresses through an independently acquired disclosure boundary."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from .data_operation_values import decode_semantic_value
from .data_product_reference import ReferenceKey, ReferenceVariant, SemanticReference

if TYPE_CHECKING:
    from .data_operation_model import BoundRoleMember


@dataclass(frozen=True, slots=True)
class ReferenceTarget:
    """Compiled target of an output reference slot."""

    role: str
    variant: ReferenceVariant
    kind_contract: str
    collection: str | None = None
    occurrence_field: str | None = None
    occurrence_binding: bool = False


@dataclass(frozen=True, slots=True)
class ProducingReferenceInput:
    role: str
    product_id: str
    kind_contract: str
    member_id: str | None = None
    occurrence: str | None = None
    multiplicity: int = 1
    occurrence_field: str | None = None
    occurrence_binding: bool = False


@dataclass(frozen=True, slots=True)
class ProducingReferenceBindings:
    derivation_id: str
    inputs: tuple[ProducingReferenceInput, ...]

    def resolve(
        self,
        reference: SemanticReference,
        *,
        occurrence_field: str | None = None,
        occurrence_binding: bool = False,
    ) -> ProducingReferenceInput:
        candidates = tuple(
            item
            for item in self.inputs
            if (item.role, item.occurrence_field, item.occurrence_binding)
            == (reference.role, occurrence_field, occurrence_binding)
        )
        if (occurrence_field is not None or occurrence_binding) and any(
            not item.occurrence for item in candidates
        ):
            raise ValueError("producing input lacks its declared reference occurrence")
        matches = tuple(item for item in candidates if item.occurrence == reference.occurrence)
        if len(matches) != 1 or matches[0].multiplicity != 1:
            raise ValueError("reference needs exactly one producing input occurrence")
        return matches[0]


def selected_producing_reference_bindings(
    producing: BoundRoleMember,
) -> ProducingReferenceBindings:
    """Read original bindings disclosed by this input's exact currently admitted producing use."""
    from .data_operation_json import json_bytes, native_json_loads
    from .producer_requirements import SelectedProducerContract

    evidence = native_json_loads(producing.support_evidence)
    observed = evidence.get("producer_contract")
    if observed is None:
        raise ValueError("producing reference requires the exact selected producer contract")
    contract = SelectedProducerContract.model_validate_json(json_bytes(observed))
    if producing.support_episodes != (contract.derivation_id,):
        raise ValueError("producing reference contract belongs to another derivation")
    return ProducingReferenceBindings(contract.derivation_id, contract.reference_inputs)


def require_selected_whole_reference(
    reference: SemanticReference,
    *,
    role: str,
    producing: BoundRoleMember,
    selected: BoundRoleMember,
) -> None:
    """Require a role-relative citation to match the caller's independent live whole pin."""
    if reference != SemanticReference.whole(role):
        raise ValueError("reference differs from its declared whole-product role")
    original = selected_producing_reference_bindings(producing).resolve(reference)
    if (
        original.member_id is not None
        or selected.member is not None
        or selected.multiplicity != 1
        or (original.product_id, original.kind_contract)
        != (selected.product, selected.kind_contract)
    ):
        raise ValueError("original reference target differs from the independently selected input")


@dataclass(frozen=True, slots=True)
class AcquiredReferencePartition:
    digest: str
    meaning: object
    address: tuple[str, ...]


class AcquiredReferenceAccess(Protocol):
    """Current selected authority or captured replay custody, scoped by its owner."""

    def authorize(self, binding: ProducingReferenceInput) -> None: ...

    def product(self, product_id: str) -> object: ...

    def member(self, product_id: str, member_id: str) -> object: ...

    def partition(
        self, product_id: str, collection: str, partition_key: str
    ) -> AcquiredReferencePartition: ...


def _field(row: object, path: str) -> str | int:
    for part in path.split("."):
        if not isinstance(row, Mapping) or part not in row:
            raise ValueError("partition item lacks its declared address field")
        row = row[part]
    if isinstance(row, str) and row:
        return row
    if isinstance(row, int) and not isinstance(row, bool):
        return row
    raise ValueError("partition item address must be a nonempty string or integer")


class ReferenceResolver:
    """Resolve through keyed access and reuse content with the same address declaration."""

    def __init__(self, producing: ProducingReferenceBindings, access: AcquiredReferenceAccess):
        self.producing = producing
        self.access = access
        self._locations: dict[tuple[str, str, str], tuple[str, tuple[str, ...]]] = {}
        self._partitions: dict[
            tuple[str, tuple[str, ...]], dict[ReferenceKey, Mapping[str, object]]
        ] = {}

    def resolve(self, reference: SemanticReference, target: ReferenceTarget) -> object:
        if (reference.role, reference.variant, reference.collection) != (
            target.role,
            target.variant,
            target.collection,
        ) or (reference.occurrence is not None) != (
            target.occurrence_field is not None or target.occurrence_binding
        ):
            raise ValueError("reference differs from its declared slot target")
        binding = self.producing.resolve(
            reference,
            occurrence_field=target.occurrence_field,
            occurrence_binding=target.occurrence_binding,
        )
        if binding.kind_contract != target.kind_contract:
            raise ValueError("reference has the wrong producing input kind")
        # Always establish access to the actual original parent before using a cached body.
        self.access.authorize(binding)
        if binding.member_id is not None and binding.member_id != reference.member_id:
            raise ValueError("reference is outside its producing input member")
        try:
            if reference.member_id is not None:
                return self.access.member(binding.product_id, reference.member_id)
            if reference.item_key is None:
                return self.access.product(binding.product_id)
            assert reference.collection is not None and reference.partition_key is not None
            location = (binding.product_id, reference.collection, reference.partition_key)
            if location not in self._locations:
                partition = self.access.partition(*location)
                if not partition.address:
                    raise ValueError("partition lacks a declared item address")
                identity = (partition.digest, partition.address)
                if identity not in self._partitions:
                    rows = decode_semantic_value(partition.meaning)
                    indexed = {
                        tuple(_field(row, field) for field in partition.address): row
                        for row in rows
                    }
                    if len(indexed) != len(rows):
                        raise ValueError("partition repeats a declared item address")
                    self._partitions[identity] = indexed
                self._locations[location] = identity
            return deepcopy(self._partitions[self._locations[location]][reference.item_key])
        except KeyError as error:
            raise ValueError("reference does not resolve its declared target") from error
