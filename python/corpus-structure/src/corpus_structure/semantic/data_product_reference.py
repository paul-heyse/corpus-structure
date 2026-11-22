"""Governed semantic product/member addresses, independent of physical custody."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import Annotated, Literal, TypedDict

from pydantic import ConfigDict, Field, with_config

from .identity import canonical_bytes

ReferenceVariant = Literal["product", "member", "partition-item"]
ReferenceKey = tuple[str | int, ...]
_Nonempty = Annotated[str, Field(min_length=1)]


@with_config(ConfigDict(extra="forbid", strict=True))
class ReferenceTextKeyPart(TypedDict):
    kind: Literal["text"]
    text: _Nonempty


@with_config(ConfigDict(extra="forbid", strict=True))
class ReferenceIntegerKeyPart(TypedDict):
    kind: Literal["integer"]
    integer: int


ReferenceKeyPart = Annotated[
    ReferenceTextKeyPart | ReferenceIntegerKeyPart, Field(discriminator="kind")
]


@with_config(ConfigDict(extra="forbid", json_schema_extra={"x-ddo-role-reference": "product"}))
class SemanticWholeReference(TypedDict):
    """Nominal JSON projection of the shared whole-product variant without an occurrence."""

    variant: Literal["product"]
    role: _Nonempty


@with_config(ConfigDict(extra="forbid", json_schema_extra={"x-ddo-role-reference": "member"}))
class SemanticMemberReference(TypedDict):
    """Nominal JSON projection of one identified member of a scalar producing input."""

    variant: Literal["member"]
    role: _Nonempty
    member_id: _Nonempty


@with_config(
    ConfigDict(
        extra="forbid",
        json_schema_extra={"x-ddo-role-reference": "member", "x-ddo-reference-occurrence": True},
    )
)
class SemanticOccurrenceMemberReference(TypedDict):
    """One member in an input occurrence identified by its declared semantic field."""

    variant: Literal["member"]
    role: _Nonempty
    occurrence: _Nonempty
    member_id: _Nonempty


@with_config(
    ConfigDict(extra="forbid", json_schema_extra={"x-ddo-role-reference": "partition-item"})
)
class SemanticPartitionReference(TypedDict):
    """Nominal JSON projection of one addressed item of a scalar producing input."""

    variant: Literal["partition-item"]
    role: _Nonempty
    collection: _Nonempty
    partition_key: _Nonempty
    item_key: Annotated[list[ReferenceKeyPart], Field(min_length=1)]


def _identifier(value: object) -> bool:
    return type(value) is str and bool(value)


@dataclass(frozen=True, slots=True)
class SemanticReference:
    """A body reference addressed in its producing derivation's input roles."""

    variant: ReferenceVariant
    role: str
    occurrence: str | None = None
    member_id: str | None = None
    collection: str | None = None
    partition_key: str | None = None
    item_key: ReferenceKey | None = None

    def __post_init__(self):
        if not _identifier(self.role) or (
            self.occurrence is not None and not _identifier(self.occurrence)
        ):
            raise ValueError("reference requires an exact role and optional occurrence key")
        partition_fields = (self.collection, self.partition_key, self.item_key)
        if self.variant == "product":
            valid = self.member_id is None and all(field is None for field in partition_fields)
        elif self.variant == "member":
            valid = _identifier(self.member_id) and all(field is None for field in partition_fields)
        elif self.variant == "partition-item":
            valid = (
                self.member_id is None
                and _identifier(self.collection)
                and _identifier(self.partition_key)
                and isinstance(self.item_key, tuple)
                and bool(self.item_key)
                and all(type(value) is int or _identifier(value) for value in self.item_key)
            )
        else:
            valid = False
        if not valid:
            raise ValueError("reference fields must match their declared variant")

    @classmethod
    def whole(cls, role: str, *, occurrence: str | None = None):
        return cls("product", role, occurrence)

    @classmethod
    def member(cls, role: str, member_id: str, *, occurrence: str | None = None):
        return cls("member", role, occurrence, member_id=member_id)

    @classmethod
    def item(
        cls,
        role: str,
        collection: str,
        partition_key: str,
        item_key: ReferenceKey,
        *,
        occurrence: str | None = None,
    ):
        return cls(
            "partition-item",
            role,
            occurrence,
            collection=collection,
            partition_key=partition_key,
            item_key=item_key,
        )

    def values(self) -> dict[str, object]:
        value: dict[str, object] = {"variant": self.variant, "role": self.role}
        if self.occurrence is not None:
            value["occurrence"] = self.occurrence
        if self.variant == "member":
            value["member_id"] = self.member_id
        elif self.item_key is not None:
            value.update(
                collection=self.collection,
                partition_key=self.partition_key,
                item_key=[_write_reference_key_part(part) for part in self.item_key],
            )
        return value

    def whole_value(self) -> SemanticWholeReference:
        if self.variant != "product" or self.occurrence is not None:
            raise ValueError("scalar product reference required")
        return {"variant": "product", "role": self.role}

    def member_value(self) -> SemanticMemberReference:
        if self.variant != "member" or self.occurrence is not None or self.member_id is None:
            raise ValueError("scalar member reference required")
        return {"variant": "member", "role": self.role, "member_id": self.member_id}

    def occurrence_member_value(self) -> SemanticOccurrenceMemberReference:
        if self.variant != "member" or self.occurrence is None or self.member_id is None:
            raise ValueError("occurrence member reference required")
        return {
            "variant": "member",
            "role": self.role,
            "occurrence": self.occurrence,
            "member_id": self.member_id,
        }

    def partition_value(self) -> SemanticPartitionReference:
        if (
            self.variant != "partition-item"
            or self.occurrence is not None
            or self.collection is None
            or self.partition_key is None
            or self.item_key is None
        ):
            raise ValueError("scalar partition-item reference required")
        return {
            "variant": "partition-item",
            "role": self.role,
            "collection": self.collection,
            "partition_key": self.partition_key,
            "item_key": [_write_reference_key_part(part) for part in self.item_key],
        }


def read_semantic_reference(value) -> SemanticReference:
    if not isinstance(value, Mapping):
        raise ValueError("reference must be a mapping")
    fields = {field: item for field, item in value.items() if field != "item_key"}
    if "item_key" in value:
        if not isinstance(value["item_key"], list):
            raise ValueError("reference item key must be an ordered list")
        fields["item_key"] = tuple(_read_reference_key_part(part) for part in value["item_key"])
    try:
        reference = SemanticReference(**fields)
    except TypeError as error:
        raise ValueError("reference has undeclared or missing fields") from error
    if reference.values() != value:
        raise ValueError("reference must use the exact variant fields")
    return reference


def _read_reference_key_part(part: object) -> str | int:
    if isinstance(part, Mapping):
        kind = part.get("kind")
        if kind == "text" and set(part) == {"kind", "text"}:
            text = part["text"]
            if type(text) is str and text:
                return text
        elif kind == "integer" and set(part) == {"kind", "integer"}:
            number = part["integer"]
            if type(number) is int:
                return number
    raise ValueError("reference key part requires one exact text or integer value")


def _write_reference_key_part(value: str | int) -> ReferenceKeyPart:
    if isinstance(value, str):
        return {"kind": "text", "text": value}
    return {"kind": "integer", "integer": value}


def reference_inputs(bundle):
    """Capture the shared nominal address shapes alongside their existing schema owner."""
    import yaml

    from .observations import observation_inputs
    from .types import SourceArtifact, SourceBundle

    if "observations" not in {source.name for source in bundle.sources}:
        bundle = observation_inputs(bundle)

    from corpus_structure.model.compiled import model_source

    content = model_source("data-operation-references.yaml")
    name, root = "data_operation_references", "data_operation_references_root"
    existing = {source.name: source.content for source in bundle.sources}
    if name in existing:
        if existing[name] != content:
            raise ValueError("shared semantic reference model differs from installed owner")
        return bundle
    if root in existing:
        raise ValueError("semantic reference model uses a reserved root name")
    return SourceBundle(
        root,
        (
            *bundle.sources,
            SourceArtifact(name, content),
            SourceArtifact(
                root,
                yaml.safe_dump(
                    dict(
                        id="urn:corpus:data-operation-references-root",
                        name=root,
                        imports=[bundle.root, name],
                    )
                ).encode(),
            ),
        ),
    )


@dataclass(frozen=True, slots=True)
class DataProductReference:
    product_id: str

    def __post_init__(self):
        if type(self.product_id) is not str or not self.product_id:
            raise ValueError("semantic product reference requires its governed product ID")

    def values(self) -> dict[str, str]:
        return {"product_id": self.product_id}


@dataclass(frozen=True, slots=True)
class DataProductMemberReference:
    product: DataProductReference
    member_id: str

    def __post_init__(self):
        if (
            not isinstance(self.product, DataProductReference)
            or type(self.member_id) is not str
            or not self.member_id
        ):
            raise ValueError("semantic member reference requires a governed product and member ID")

    @property
    def local_id(self) -> str:
        """A member's local address inside the immutable governed product."""
        return self.member_id

    def values(self) -> dict[str, str]:
        return {"product_id": self.product.product_id, "member_id": self.member_id}

    @property
    def identity(self) -> str:
        return "member:" + sha256(canonical_bytes(self.values())).hexdigest()


def member_reference(product: DataProductReference, member_id: str) -> DataProductMemberReference:
    """Address an actual semantic member within its immutable governed product."""
    return DataProductMemberReference(product, member_id)


def read_member_reference(value) -> DataProductMemberReference:
    from collections.abc import Mapping

    if not isinstance(value, Mapping) or set(value) != {"product_id", "member_id"}:
        raise ValueError("member reference is not an exact semantic address")
    return DataProductMemberReference(DataProductReference(value["product_id"]), value["member_id"])
