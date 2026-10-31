"""Native Docling occurrence projections replace HTML lexical source capture."""

from docling_core.types.doc import DocItemLabel, DoclingDocument

from corpus_structure.ingest.pdf_hierarchy import (
    SectionPolicy,
    load_snapshot,
    organize,
    project_section,
    snapshot,
)


def test_native_item_identity_and_unicode_offsets_survive_section_projection():
    native = DoclingDocument(name="native Unicode occurrence fixture")
    native.add_heading(text="1.1: Sets", level=1)
    item = native.add_text(label=DocItemLabel.TEXT, text="Same \u03b1. Same \u03b1.")
    raw = snapshot(native)
    organized = organize(raw, SectionPolicy("fixture"))
    section = organized.sections[0].group_ref
    projected = project_section(
        load_snapshot(organized.document),
        organized.document.digest,
        section,
        "direct",
        section_refs=frozenset([section]),
    )
    piece = next(p for p in projected.pieces if p.item_ref == item.self_ref)
    assert projected.text[piece.start : piece.end] == "Same \u03b1. Same \u03b1."
    assert raw.payload == snapshot(native).payload
