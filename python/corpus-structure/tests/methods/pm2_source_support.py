"""Controlled inputs and builders shared by the pm2 source consumers."""

from hashlib import sha256

from corpus_structure.methods.pm2_source import PM2SourceMap, SourceMapSegment
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.proposals import NativeFrameSource
from corpus_structure.semantic.source_contexts import NativeSourceContext, SourceSlice


def source_context(fields, *, identity=1, policy="test-layout"):
    """Build each field and offset independently of the mapping adapter."""
    text = ""
    items = []
    pieces = []
    for pointer, field, selected, native in fields:
        if pointer is None:
            pieces.append(
                dict(kind="synthetic_separator", start=len(text), end=len(text + selected))
            )
        else:
            pieces.append(
                dict(
                    kind="native_text",
                    item_ref=pointer,
                    source_field=field,
                    start=len(text),
                    end=len(text + selected),
                )
            )
            node = dict(self_ref=pointer, text=native)
            if field == "orig":
                node["orig"] = selected
            items.append(node)
        text += selected
    projection = dict(
        text=text,
        pieces=pieces,
        items=[item["self_ref"] for item in items],
        ancestors=[],
        health={},
    )
    primary = NativeFrameSource(
        f"unit:{identity}",
        text,
        (),
        identity,
        ProductReference(18, "integrated", "a" * 64),
        "#/groups/1",
        "direct",
        sha256(canonical_bytes(projection)).hexdigest(),
        "b" * 64,
        canonical_bytes(dict(pieces=pieces, items=items, ancestors=[], health={})).decode(),
        version=3,
    )
    return NativeSourceContext(
        primary, (), (SourceSlice(identity, 0, len(text)),), "exact read", policy, "selected"
    )


def identity_map(text, *, atoms=(), identity=1, policy="test-layout"):
    context = source_context((("#/texts/0", "text", text, text),), identity=identity, policy=policy)
    return PM2SourceMap(context, text, (SourceMapSegment(0, len(text), 0),), atoms)
