"""Native PDF adapter boundaries, without substituting fake inference for provider evidence."""

from __future__ import annotations

from contextlib import suppress
from types import SimpleNamespace

import pytest

from corpus_structure.ingest.pdf import PdfRecipe
from corpus_structure.ingest.pdf_health import ObservedFormulaStage
from corpus_structure.ingest.pdf_hierarchy import (
    SectionPolicy,
    load_snapshot,
    native_nodes,
    organize,
    project_section,
    snapshot,
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
    elements_batch_size = 4

    def __init__(self, engine):
        self.engine = engine

    def __call__(self, doc, element_batch):
        elements = list(element_batch)
        # Native stage's known swallowed exception behavior.
        with suppress(Exception):
            self.engine.predict_batch(elements)
        yield from (e.item for e in elements)


@pytest.mark.parametrize(
    "fails,short,expected",
    [(False, False, "succeeded"), (True, False, "failed"), (False, True, "failed")],
)
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
    derived_nodes = native_nodes(derived)
    assert original_refs <= derived_nodes.keys()
    assert derived_nodes.keys() - original_refs == {
        section.group_ref for section in result.sections
    }
    for section in result.sections:
        group = derived_nodes[section.group_ref]
        assert group.children[0].cref == section.heading_ref
        assert derived_nodes[section.heading_ref].level == section.level
        assert section.rule_id == "numbered-book-headings-v1"
    sections = frozenset(s.group_ref for s in result.sections)
    direct = project_section(
        derived,
        result.document.digest,
        result.sections[0].group_ref,
        "direct",
        section_refs=sections,
    )
    descendant = project_section(
        derived,
        result.document.digest,
        result.sections[0].group_ref,
        "descendant",
        section_refs=sections,
    )
    assert "Proof content." in direct.text
    assert "Operations" not in direct.text
    assert "Operations" in descendant.text
    assert "Functions" not in descendant.text
    for piece in direct.pieces:
        if piece.kind == "synthetic_separator":
            assert direct.text[piece.start : piece.end] == "\n"


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
    from docling_core.types.doc import DocItemLabel

    formula = document.add_text(label=DocItemLabel.FORMULA, text="x")
    native = snapshot(document)
    conversion = PdfConversion(
        "c" * 64,
        b"{}",
        native,
        "success",
        (),
        (FormulaOutcome(formula.self_ref, "failed", "native stage failed"),),
        (),
        None,
    )
    payload = publication_payload(conversion, product_key="raw", schema_digest="d" * 64)
    rows = payload["items"]
    assert len({r["pointer"] for r in rows}) == len(native_nodes(document))
    assert {r["pointer"] for r in rows} == set(native_nodes(document))
    assert [r["ordinal"] for r in rows] == list(range(len(rows)))
    assert payload["health"]["formula_outcomes"] == [
        {"pointer": formula.self_ref, "outcome": "failed", "error": "native stage failed"}
    ]
    assert payload["health"]["cell_coverage"] == "unknown"


def test_cell_enrichment_retains_raw_and_creates_native_rich_reference():
    from docling_core.types.doc import (
        BoundingBox,
        DoclingDocument,
        PageItem,
        ProvenanceItem,
        RichTableCell,
        Size,
        TableCell,
        TableData,
    )
    from PIL import Image

    from corpus_structure.ingest.pdf import CellCandidate, enrich_cells

    document = DoclingDocument(name="independent cell geometry fixture")
    document.pages[1] = PageItem(page_no=1, size=Size(width=100, height=100))
    box = BoundingBox(l=10, t=10, r=40, b=30)
    cell = TableCell(
        text="n k",
        bbox=box,
        start_row_offset_idx=0,
        end_row_offset_idx=1,
        start_col_offset_idx=0,
        end_col_offset_idx=1,
    )
    table = document.add_table(
        data=TableData(num_rows=1, num_cols=1, table_cells=[cell]),
        prov=ProvenanceItem(page_no=1, bbox=box, charspan=(0, 0)),
    )
    raw = snapshot(document)
    stage = ObservedFormulaStage(CatchingStage(Engine()))
    calls = []

    def render(page_no, bbox):
        calls.append((page_no, bbox))
        return Image.new("RGB", (30, 20))

    result = enrich_cells(
        raw, (CellCandidate(table.self_ref, 0, 1),), stage=stage, render_region=render
    )
    assert snapshot(document) == raw
    derived = load_snapshot(result.native)
    rich_cell = derived.tables[0].data.table_cells[0]
    assert isinstance(rich_cell, RichTableCell)
    formula = rich_cell.ref.resolve(derived)
    assert formula.parent.cref == table.self_ref
    assert formula.orig == "n k"
    assert formula.prov[0].bbox == box
    assert calls == [(1, box)]
    assert result.outcomes[0].outcome == "succeeded"
    from dataclasses import replace

    from corpus_structure.ingest.pdf import PdfConversion, publication_payload

    conversion = PdfConversion("c" * 64, b"{}", raw, "success", (), (), (), None)
    payload = publication_payload(
        conversion,
        product_key="cells",
        schema_digest="d" * 64,
        native=result.native,
        enrichment=result,
        parent=(1, "raw", "e" * 64),
    )
    assert payload["health"]["formula_outcomes"][0]["outcome"] == "succeeded"
    with pytest.raises(ValueError, match="qualified"):
        publication_payload(
            conversion,
            product_key="cells",
            schema_digest="d" * 64,
            native=result.native,
            enrichment=replace(result, source_digest="f" * 64),
            parent=(1, "raw", "e" * 64),
        )


def test_non_pdf_is_refused_without_converter_preparation(tmp_path):
    from corpus_structure.ingest.pdf import PdfConverter

    converter = PdfConverter(PdfRecipe("a" * 40, "b" * 40))
    path = tmp_path / "document.html"
    path.write_text("<html/>")
    with pytest.raises(ValueError, match="only PDF"):
        converter.convert(path)
    assert converter._converter is None


def test_converter_hashes_and_consumes_same_immutable_snapshot(tmp_path, monkeypatch):
    from hashlib import sha256

    from corpus_structure.ingest.pdf import PdfConverter

    path = tmp_path / "source.pdf"
    original = b"%PDF-1.7 immutable initial bytes"
    path.write_bytes(original)
    producer = PdfConverter(PdfRecipe("a" * 40, "b" * 40))
    consumed = []

    def convert(stream, **kwargs):
        consumed.append(stream.stream.getvalue())
        return SimpleNamespace(
            document=native_document(),
            errors=[],
            status=SimpleNamespace(value="success"),
            input=SimpleNamespace(release=lambda: None),
            confidence=SimpleNamespace(model_dump_json=lambda: '{"layout_score":0.75}'),
        )

    def prepare():
        path.write_bytes(b"%PDF-1.7 replaced during expensive initialization")
        producer._converter = SimpleNamespace(convert=convert)
        producer._formula = ObservedFormulaStage(CatchingStage(Engine()))
        producer._options = SimpleNamespace(model_dump_json=lambda **kwargs: "{}")

    monkeypatch.setattr(producer, "_prepare", prepare)
    monkeypatch.setattr(producer, "runtime_bindings", lambda: ())
    result = producer.convert(path)
    assert consumed == [original]
    assert result.original_digest == sha256(original).hexdigest()
    assert path.read_bytes() != original
