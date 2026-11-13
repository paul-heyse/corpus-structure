"""Governed semantic product/member addresses, independent of physical custody."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from .identity import canonical_bytes


def reference_inputs(bundle):
    """Capture the shared nominal address shapes alongside their existing schema owner."""
    import yaml

    from .types import SourceArtifact, SourceBundle

    content = (
        Path(__file__).parents[1] / "model/semantic/data-operation-references.yaml"
    ).read_bytes()
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


def member_reference(product, member_id):
    """Keep legacy archive addressing only for an actual legacy input."""
    from .characterization import AnnotationReference
    from .product_reference import ProductReference

    if isinstance(product, DataProductReference):
        return DataProductMemberReference(product, member_id)
    if isinstance(product, ProductReference):
        return AnnotationReference(product, member_id)
    raise TypeError("member reference requires an admitted product reference")


def read_member_reference(value):
    from .characterization import AnnotationReference
    from .product_reference import ProductReference

    if set(value) == {"product_id", "member_id"}:
        return DataProductMemberReference(
            DataProductReference(value["product_id"]), value["member_id"]
        )
    if set(value) == {"layer", "local_id"}:
        return AnnotationReference(ProductReference(**value["layer"]), value["local_id"])
    raise ValueError("member reference is not an exact semantic or legacy address")
