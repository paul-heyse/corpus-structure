"""Native Docling occurrence projections replace HTML lexical source capture."""
from docling_core.types.doc import DocItemLabel,DoclingDocument
from corpus_structure.ingest.pdf_hierarchy import organize,snapshot,load_snapshot,project_section,SectionPolicy


def test_native_item_identity_and_unicode_offsets_survive_section_projection():
    native=DoclingDocument(name='native Unicode occurrence fixture')
    native.add_heading(text='1.1: Sets',level=1)
    item=native.add_text(label=DocItemLabel.TEXT,text='Same α. Same α.')
    raw=snapshot(native)
    organized=organize(raw,SectionPolicy('fixture'))
    section=organized.sections[0].group_ref
    projected=project_section(load_snapshot(organized.document),organized.document.digest,section,'direct',section_refs=frozenset([section]))
    piece=next(p for p in projected.pieces if p.item_ref==item.self_ref)
    assert projected.text[piece.start:piece.end]=='Same α. Same α.'
    assert raw.payload==snapshot(native).payload
