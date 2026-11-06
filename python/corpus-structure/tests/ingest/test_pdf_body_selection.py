"""A root-body source is a residual scope, not a fabricated organizational section."""

from docling_core.types.doc import DocItemLabel, DoclingDocument, GroupLabel

from corpus_structure.ingest.pdf_hierarchy import native_nodes, snapshot
from corpus_structure.ingest.pdf_methods import PdfIngestConfig, _drafts, _select_sections
from corpus_structure.semantic.product_reference import ProductReference


def test_native_graph_default_projection_covers_body_prefix_once_and_named_selection_does_not():
    document = DoclingDocument(name="source")
    prefix = document.add_text(label=DocItemLabel.TEXT, text="unheaded prefix")
    section = document.add_group(label=GroupLabel.SECTION, name="Named")
    document.add_text(label=DocItemLabel.TEXT, text="section content", parent=section)
    nodes = native_nodes(document)
    native = snapshot(document)
    cfg = PdfIngestConfig(membership="descendants")
    scopes = _select_sections(nodes, cfg)
    assert scopes == ("#/body", section.self_ref)
    drafts = _drafts(
        1,
        ProductReference(1, "native", native.digest),
        native,
        dict(conversion="success"),
        scopes,
        cfg.membership,
        "consumer",
        document=document,
        node_index=nodes,
    )
    assert [(d.section_pointer, d.membership, d.text) for d in drafts] == [
        ("#/body", "direct", "unheaded prefix"),
        (section.self_ref, "descendants", "section content"),
    ]
    assert drafts[0].items == ("#/body", prefix.self_ref)
    assert _select_sections(nodes, cfg.model_copy(update=dict(sections=("Named",)))) == (
        section.self_ref,
    )


def test_no_heading_graph_can_project_original_body_directly():
    document = DoclingDocument(name="unheaded")
    document.add_text(label=DocItemLabel.TEXT, text="all original body")
    nodes = native_nodes(document)
    native = snapshot(document)
    cfg = PdfIngestConfig()
    assert _select_sections(nodes, cfg) == ("#/body",)
    (draft,) = _drafts(
        1,
        ProductReference(1, "native", native.digest),
        native,
        dict(conversion="success"),
        ("#/body",),
        "descendants",
        "consumer",
        document=document,
        node_index=nodes,
    )
    assert (
        draft.section_pointer == "#/body"
        and draft.membership == "direct"
        and draft.text == "all original body"
    )
