"""Governed semantic product/member addresses, independent of physical custody."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from .identity import canonical_bytes


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
