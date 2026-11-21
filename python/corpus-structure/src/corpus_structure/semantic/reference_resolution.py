"""Interpret producing addresses through an independently acquired disclosure boundary."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from .data_product_reference import ReferenceKey, ReferenceVariant, SemanticReference


@dataclass(frozen=True, slots=True)
class ReferenceTarget:
    """Compiled target of an output reference slot."""

    role: str
    variant: ReferenceVariant
    kind_contract: str
    collection: str | None = None
    requires_occurrence: bool = False


@dataclass(frozen=True, slots=True)
class ProducingReferenceInput:
    role: str
    product_id: str
    kind_contract: str
    member_id: str | None = None
    occurrence: str | None = None
    multiplicity: int = 1


@dataclass(frozen=True, slots=True)
class ProducingReferenceBindings:
    derivation_id: str
    inputs: tuple[ProducingReferenceInput, ...]

    def resolve(self, reference: SemanticReference) -> ProducingReferenceInput:
        matches = tuple(
            item
            for item in self.inputs
            if item.role == reference.role
            and (reference.occurrence is None or item.occurrence == reference.occurrence)
        )
        if len(matches) != 1 or matches[0].multiplicity != 1:
            raise ValueError("reference needs exactly one producing input occurrence")
        return matches[0]


class AcquiredReferenceAccess(Protocol):
    """Current selected authority or captured replay custody, scoped by its owner."""

    def authorize(self, binding: ProducingReferenceInput) -> None: ...

    def product(self, product_id: str) -> object: ...

    def member(self, product_id: str, member_id: str) -> object: ...

    def partition(
        self, product_id: str, collection: str, partition_key: str
    ) -> tuple[Sequence[Mapping[str, object]], tuple[str, ...]]: ...


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
    """Resolve through keyed access, with one decoded index per acquired partition."""

    def __init__(self, producing: ProducingReferenceBindings, access: AcquiredReferenceAccess):
        self.producing = producing
        self.access = access
        self._partitions: dict[tuple[str, str, str], dict[ReferenceKey, Mapping[str, object]]] = {}

    def resolve(self, reference: SemanticReference, target: ReferenceTarget) -> object:
        if (reference.role, reference.variant, reference.collection) != (
            target.role,
            target.variant,
            target.collection,
        ) or (reference.occurrence is not None) != target.requires_occurrence:
            raise ValueError("reference differs from its declared slot target")
        binding = self.producing.resolve(reference)
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
            key = (binding.product_id, reference.collection, reference.partition_key)
            if key not in self._partitions:
                rows, fields = self.access.partition(*key)
                if not fields:
                    raise ValueError("partition lacks a declared item address")
                indexed = {tuple(_field(row, field) for field in fields): row for row in rows}
                if len(indexed) != len(rows):
                    raise ValueError("partition repeats a declared item address")
                self._partitions[key] = indexed
            return self._partitions[key][reference.item_key]
        except KeyError as error:
            raise ValueError("reference does not resolve its declared target") from error
