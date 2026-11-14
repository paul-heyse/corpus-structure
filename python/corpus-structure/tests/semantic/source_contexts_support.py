"""Shared controlled inputs and builders for source contexts support."""

from hashlib import sha256

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.proposals import NativeFrameSource
from corpus_structure.semantic.source_contexts import NativeSourceContext

PRODUCT = ProductReference(17, "integrated", "a" * 64)


def source(identity, text, *, pieces=None, ancestors=(), membership="direct", version=3):
    """Build independent projected-source fixtures, never search to locate model quotes."""
    if pieces is None:
        pieces = [dict(kind="native_text", item_ref=f"#/texts/{identity}", start=0, end=len(text))]
    pointers = list(dict.fromkeys(piece["item_ref"] for piece in pieces if "item_ref" in piece))
    context = dict(
        pieces=pieces,
        items=[dict(self_ref=pointer) for pointer in pointers],
        ancestors=[dict(self_ref=pointer) for pointer in ancestors],
        health={"inline_coverage": "unknown"},
    )
    projection = dict(
        text=text,
        pieces=pieces,
        items=pointers,
        ancestors=list(ancestors),
        health=context["health"],
    )
    return NativeFrameSource(
        f"unit:{identity}",
        text,
        (),
        identity,
        PRODUCT,
        f"#/groups/{identity}",
        membership,
        sha256(canonical_bytes(projection)).hexdigest(),
        "c" * 64,
        canonical_bytes(context).decode(),
        version=version,
    )


def context(primary, pieces, *, related=(), retrievals=(), **kwargs):
    return NativeSourceContext(
        primary,
        related,
        pieces,
        "measurement roles",
        "bounded-policy-1",
        "roles supplied",
        retrievals,
        **kwargs,
    )
