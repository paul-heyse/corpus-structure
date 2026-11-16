"""Controlled inputs and builders shared by the pm2 source consumers."""

from corpus_structure.methods.pm2_source import PM2SourceMap, SourceMapSegment
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext, PreparedNativeSources, source_slice,
)
from methods.record_assembly_support import source


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
            node = dict(self_ref=pointer, label="text", text=native)
            if field == "orig":
                node["orig"] = selected
            items.append(node)
        text += selected
    primary = source(text, identity=identity, pieces=pieces, items=items, ancestors=())
    return NativeSourceContext(
        primary, (), (source_slice(primary, 0, len(text)),), "exact read", policy, "selected",
        version=2, preparation=PreparedNativeSources((primary,)),
    )


def identity_map(text, *, atoms=(), identity=1, policy="test-layout"):
    context = source_context((("#/texts/0", "text", text, text),), identity=identity, policy=policy)
    return PM2SourceMap(context, text, (SourceMapSegment(0, len(text), 0),), atoms)
