"""Native PDF adapter boundaries, without substituting fake inference for provider evidence."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from corpus_structure.ingest.pdf import PdfRecipe
from corpus_structure.ingest.pdf_health import ObservedFormulaStage
from corpus_structure.ingest.pdf_hierarchy import (
    SectionPolicy, load_snapshot, native_nodes, organize, project_section, snapshot,
)


def test_recipe_requires_immutable_model_revisions():
    with pytest.raises(ValueError, match="immutable"):
        PdfRecipe("main", "main")
    with pytest.raises(ValueError, match="capacity"):
        PdfRecipe("a" * 40, "b" * 40, parser_threads=0)
    assert PdfRecipe("a" * 40, "b" * 40).to_bytes() == PdfRecipe("a" * 40, "b" * 40).to_bytes()


def test_native_option_variants_are_reconstructed():
    pytest.importorskip("docling")
    recipe = PdfRecipe("a" * 40, "b" * 40)
    options = recipe.options()
    assert type(options.code_formula_options).__name__ == "CodeFormulaVlmOptions"
    assert options.code_formula_options.engine_options.engine_type.value == "transformers"
    assert options.layout_options.model_spec.revision == "a" * 40
    assert options.code_formula_options.model_spec.revision == "b" * 40
    assert options.ocr_options.rapidocr_params["Rec.use_cuda"] is False


class Engine:
    def __init__(self, *, fails=False, short=False):
        self.fails = fails
        self.short = short

    def predict_batch(self, inputs):
        if self.fails:
            raise RuntimeError("actual native runtime failure")
        return [] if self.short else [SimpleNamespace(text="unchanged") for _ in inputs]


class CatchingStage:
    enabled = True

    def __init__(self, engine):
        self.engine = engine

    def __call__(self, doc, element_batch):
        elements = list(element_batch)
        try:
            self.engine.predict_batch(elements)
        except Exception:
            pass  # Native stage's known swallowed exception behavior.
        yield from (e.item for e in elements)


@pytest.mark.parametrize("fails,short,expected", [(False, False, "succeeded"),
                                                  (True, False, "failed"),
                                                  (False, True, "failed")])
def test_swallowed_failure_and_unchanged_success_are_attributed(fails, short, expected):
    engine = Engine(fails=fails, short=short)
    native = CatchingStage(engine)
    wrapped = ObservedFormulaStage(native)
    item = SimpleNamespace(self_ref="#/texts/0", text="unchanged")
    assert list(wrapped(None, [SimpleNamespace(item=item)])) == [item]
    assert wrapped.outcomes[0].outcome == expected
    assert native.engine is engine


def native_document():
    doc = pytest.importorskip("docling_core.types.doc")
    document = doc.DoclingDocument(name="independent section fixture")
    document.add_heading(text="1.1: Sets", level=1)
    document.add_text(label=doc.DocItemLabel.TEXT, text="Before.")
    document.add_heading(text="Proof", level=2)
    document.add_text(label=doc.DocItemLabel.TEXT, text="Proof content.")
    document.add_heading(text="1.1.1: Operations", level=2)
    document.add_text(label=doc.DocItemLabel.TEXT, text="Same spelling.")
    document.add_heading(text="1.2: Functions", level=1)
    document.add_text(label=doc.DocItemLabel.TEXT, text="Same spelling.")
    return document


def test_organization_keeps_proof_local_and_direct_membership_distinct():
    document = native_document()
    source = snapshot(document)
    original_refs = set(native_nodes(document))
    result = organize(source, SectionPolicy("numbered-book-headings-v1"))
    assert len(result.sections) == 3
    assert source.payload == snapshot(document).payload
    derived = load_snapshot(result.document)
    assert original_refs <= native_nodes(derived).keys()
    sections = frozenset(s.group_ref for s in result.sections)
    direct = project_section(derived, result.document.digest, result.sections[0].group_ref,
                             "direct", section_refs=sections)
    descendant = project_section(derived, result.document.digest, result.sections[0].group_ref,
                                 "descendant", section_refs=sections)
    assert "Proof content." in direct.text
    assert "Operations" not in direct.text
    assert "Operations" in descendant.text
    assert "Functions" not in descendant.text
    for piece in direct.pieces:
        if piece.kind == "synthetic_separator":
            assert direct.text[piece.start:piece.end] == "\n"


def test_snapshot_refuses_integrity_and_unqualified_section():
    import dataclasses
    document = native_document()
    saved = snapshot(document)
    with pytest.raises(ValueError, match="integrity"):
        load_snapshot(dataclasses.replace(saved, payload=b"{}"))
    with pytest.raises(ValueError, match="qualified"):
        project_section(document, saved.digest, "#/body", "direct", section_refs=frozenset())


def test_native_dangling_reference_refuses_before_identity():
    document = native_document()
    document.texts[0].parent.cref = "#/groups/999"
    with pytest.raises((ValueError, IndexError)):
        snapshot(document)


def test_publication_projection_preserves_native_occurrences_and_health():
    from corpus_structure.ingest.pdf import PdfConversion, publication_payload
    from corpus_structure.ingest.pdf_health import FormulaOutcome
    document = native_document()
    native = snapshot(document)
    conversion = PdfConversion("c" * 64, b"{}", native, "success", (),
        (FormulaOutcome("#/texts/0", "failed", "native stage failed"),), (), None)
    payload = publication_payload(conversion, product_key="raw", schema_digest="d" * 64)
    rows = payload["items"]
    assert len({r["pointer"] for r in rows}) == len(native_nodes(document))
    assert {r["pointer"] for r in rows} == set(native_nodes(document))
    assert [r["ordinal"] for r in rows] == list(range(len(rows)))
    assert payload["health"]["formula_outcomes"] == [
        {"pointer": "#/texts/0", "outcome": "failed", "error": "native stage failed"}]
    assert payload["health"]["cell_coverage"] == "unknown"
