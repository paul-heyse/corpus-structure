"""Runtime preparation contracts; these controls do not impersonate model/provider execution."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus_structure.ingest.pdf import PdfRecipe
from corpus_structure.ingest.pdf_assets import prepare_pdf_assets
from corpus_structure.ingest.pdf_candidates import capture_candidates
from corpus_structure.ingest.pdf_methods import PdfIngestConfig


def test_active_registry_selects_integrated_pdf_production():
    from corpus_structure.ingest.pdf_recognition_methods import PdfIntegratedIngestConfig
    from corpus_structure.orchestrate.phase0 import PHASE0, registry

    configured = registry(Path(__file__).resolve().parents[1] / "domains/statistics")
    assert {"ingest.pdf", "ingest.pdf_integrated"} <= {m.name for m in configured.methods()}
    assert "ingest.html" not in {m.name for m in configured.methods()}
    cfg = configured.resolve("ingest.pdf_integrated", "default").config
    assert isinstance(cfg, PdfIntegratedIngestConfig)
    assert cfg.originals == ("siegrist_random/Full_PDF/Full.pdf",)
    assert PHASE0.stages[0][1][0].config == "ingest.pdf_integrated/default"
    assert PdfIngestConfig().recipe().timeout_seconds is None


def test_retained_native_input_binding_preserves_domain_definition():
    from corpus_structure.ingest.pdf_recognition_methods import PdfIntegratedIngestConfig
    from corpus_structure.orchestrate.phase0 import bind_pdf_source, registry
    from corpus_structure.semantic.product_reference import ProductReference

    base = registry(Path(__file__).resolve().parents[1] / "domains/statistics")
    original = base.resolve("ingest.pdf_integrated", "default")
    pin = ProductReference(17, "organized", "a" * 64)
    bound = bind_pdf_source(base, pin)
    selected = bound.resolve("ingest.pdf_integrated", "default")
    assert isinstance(selected.config, PdfIntegratedIngestConfig)
    assert selected.config.native_product == pin
    assert selected.config.integrated_product is None
    assert selected.params["native_product"] == pin.values()
    assert selected.config_hash != original.config_hash
    assert base.resolve("ingest.pdf_integrated", "default").params == original.params
    assert "native_product" not in base.file.configs["ingest.pdf_integrated"]["default"]


def test_owned_assets_pin_actual_table_revision_and_detect_changed_bytes(tmp_path, monkeypatch):
    import huggingface_hub

    revisions = {
        "docling-project/docling-layout-heron": "a" * 40,
        "docling-project/CodeFormulaV2": "b" * 40,
        "docling-project/docling-models": "c" * 40,
    }
    for repository, revision in revisions.items():
        directory = tmp_path / "snapshots" / repository.replace("/", "--") / revision
        directory.mkdir(parents=True)
        (directory / "config.json").write_text('{"model":"independent asset fixture"}')

    def resolve(repo_id, revision, local_files_only):
        assert local_files_only is True
        return str(tmp_path / "snapshots" / repo_id.replace("/", "--") / revisions[repo_id])

    monkeypatch.setattr(huggingface_hub, "snapshot_download", resolve)
    cache = tmp_path / "models"
    (cache / "RapidOcr").mkdir(parents=True)
    for name in (
        "PP-OCRv6_det_small.onnx",
        "ch_ppocr_mobile_v2.0_cls_mobile.onnx",
        "PP-OCRv6_rec_small.onnx",
    ):
        (cache / "RapidOcr" / name).write_bytes(b"independent artifact bytes")
    assets = prepare_pdf_assets(PdfRecipe("a" * 40, "b" * 40), cache=cache)
    assert dict(assets.repositories)["docling-project/docling-models"] == "c" * 40
    assert len(assets.files) == 6
    changed = assets.root / assets.files[0][0]
    changed.chmod(0o644)
    changed.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="integrity"):
        assets.verify()


def test_native_inline_capture_distinguishes_missing_cells_from_empty_and_retains_math_font():
    from docling_core.types.doc import BoundingBox

    box = BoundingBox(l=1, t=2, r=9, b=12)
    cell = SimpleNamespace(
        text="x", font_name="ABCDEF+CMMI10", rect=SimpleNamespace(to_bounding_box=lambda: box)
    )
    captured = capture_candidates(
        SimpleNamespace(
            page_no=1,
            cells=[cell],
            parsed_page=SimpleNamespace(word_cells=[cell], has_words=True, has_chars=False),
        )
    )
    assert captured.has_words is True
    assert captured.candidates[0].text == "x"
    assert captured.candidates[0].basis == "native-math-font-v1"
    missing = capture_candidates(SimpleNamespace(page_no=2, parsed_page=None))
    assert missing.has_words is False
    assert missing.candidates == ()


def test_unnumbered_organizational_subheads_preserve_native_levels():
    from docling_core.types.doc import DocItemLabel, DoclingDocument

    from corpus_structure.ingest.pdf_hierarchy import load_snapshot, organize, snapshot

    document = DoclingDocument(name="independent unnumbered hierarchy fixture")
    for label, level in [
        ("1.1: Sets", 1),
        ("Sets and subsets", 2),
        ("Definition", 3),
        ("Proof of Theorem 1", 3),
        ("Examples and Applications", 2),
        ("Answer", 3),
        ("Distribution Functions", 2),
    ]:
        document.add_heading(text=label, level=level)
        document.add_text(label=DocItemLabel.TEXT, text="Content under " + label)
    organization = organize(snapshot(document), PdfIngestConfig().section_policy())
    derived = load_snapshot(organization.document)
    names = [derived.groups[int(s.group_ref.rsplit("/", 1)[1])].name for s in organization.sections]
    assert names == [
        "1.1: Sets",
        "Sets and subsets",
        "Examples and Applications",
        "Distribution Functions",
    ]
    assert [s.level for s in organization.sections] == [1, 2, 2, 2]


def test_inline_decomposition_keeps_prose_and_qualified_formula_in_same_native_hierarchy():
    from docling_core.types.doc import (
        BoundingBox,
        DocItemLabel,
        DoclingDocument,
        PageItem,
        ProvenanceItem,
        Size,
    )
    from PIL import Image

    from corpus_structure.ingest.pdf_candidates import InlineCandidate
    from corpus_structure.ingest.pdf_enrichment import PositionedCandidate, enrich_inline
    from corpus_structure.ingest.pdf_health import ObservedFormulaStage
    from corpus_structure.ingest.pdf_hierarchy import (
        load_snapshot,
        organize,
        project_section,
        snapshot,
    )

    class Engine:
        def predict_batch(self, inputs):
            return [SimpleNamespace(text="x") for _ in inputs]

    class CatchingStage:
        enabled = True
        elements_batch_size = 4

        def __init__(self, engine):
            self.engine = engine

        def __call__(self, doc, element_batch):
            batch = list(element_batch)
            self.engine.predict_batch(batch)
            yield from (e.item for e in batch)

    document = DoclingDocument(name="independent inline geometry fixture")
    document.pages[1] = PageItem(page_no=1, size=Size(width=100, height=100))
    document.add_heading(text="1.1: Sets", level=1)
    paragraph = document.add_text(
        label=DocItemLabel.TEXT,
        text="Let x be real.",
        orig="Let x be real.",
        prov=ProvenanceItem(page_no=1, bbox=BoundingBox(l=10, t=10, r=95, b=30), charspan=(0, 14)),
    )
    organized = organize(snapshot(document), PdfIngestConfig().section_policy())
    inline = InlineCandidate(1, "x", 25, 10, 35, 30, "TOPLEFT", "CMMI10", "native-math-font-v1")
    source = organized.document
    result = enrich_inline(
        source,
        (PositionedCandidate(paragraph.self_ref, 4, 5, inline),),
        stage=ObservedFormulaStage(CatchingStage(Engine())),
        render_region=lambda page, box: Image.new("RGB", (20, 40)),
    )
    native = load_snapshot(result.native)
    section = organized.sections[0].group_ref
    projected = project_section(
        native, result.native.digest, section, "direct", section_refs=frozenset([section])
    )
    assert projected.text == "1.1: Sets\nLet x be real."
    formulas = [n for n in native.texts if str(n.label) == "formula"]
    assert len(formulas) == 1
    assert formulas[0].text == "x"
    assert formulas[0].prov[0].charspan == (0, 1)
    formula_mapping = next(m for m in result.mappings if m["pointer"] == formulas[0].self_ref)
    assert formula_mapping["origin_pointer"] == paragraph.self_ref
    assert (formula_mapping["start"], formula_mapping["end"]) == (4, 5)
    assert [(m["start"], m["end"]) for m in result.mappings] == [(0, 4), (4, 5), (5, 14)]
    assert native.texts[int(paragraph.self_ref.rsplit("/", 1)[1])].orig == "Let x be real."
    assert result.outcomes[0].outcome == "succeeded"


def test_pinned_adoption_recipe_does_not_initialize_models(tmp_path):
    from corpus_structure.ingest.pdf_methods import IngestPdf
    from corpus_structure.semantic.product_reference import ProductReference

    cfg = PdfIngestConfig(
        native_product=ProductReference(1, "organized", "a" * 64), model_cache=tmp_path / "missing"
    )
    producer = IngestPdf()
    recipe = producer.original_recipe(cfg)
    assert b"native-pdf-adoption-v1" in recipe
    assert not producer._prepared
    assert not producer._workers


def test_source_view_key_qualifies_consumer_release_and_full_native_pin():
    from docling_core.types.doc import DocItemLabel, DoclingDocument

    from corpus_structure.ingest.pdf_hierarchy import organize, snapshot
    from corpus_structure.ingest.pdf_methods import _drafts
    from corpus_structure.semantic.product_reference import ProductReference

    document = DoclingDocument(name="independent adoption fixture")
    document.add_heading(text="1.1: Sets", level=1)
    document.add_text(label=DocItemLabel.TEXT, text="Source content")
    organized = organize(snapshot(document), PdfIngestConfig().section_policy())
    section = organized.sections[0].group_ref
    health = {"conversion": "success", "formula_outcomes": []}
    first = _drafts(
        1,
        ProductReference(1, "organized", "a" * 64),
        organized.document,
        health,
        (section,),
        "direct",
        "release1",
    )[0]
    new_release = _drafts(
        1,
        ProductReference(1, "organized", "a" * 64),
        organized.document,
        health,
        (section,),
        "direct",
        "release2",
    )[0]
    new_producer = _drafts(
        1,
        ProductReference(2, "organized", "a" * 64),
        organized.document,
        health,
        (section,),
        "direct",
        "release1",
    )[0]
    assert len({first.key, new_release.key, new_producer.key}) == 3
    assert first.text == new_release.text == new_producer.text


def test_formula_page_cache_released_after_last_native_crop_not_each_formula():
    from docling.datamodel.base_models import Page
    from docling_core.types.doc import BoundingBox, DocItemLabel, DoclingDocument, ProvenanceItem
    from PIL import Image

    from corpus_structure.ingest.pdf_health import FormulaPageLifetime

    document = DoclingDocument(name="independent native lifetime control")
    first = document.add_text(
        label=DocItemLabel.FORMULA,
        text="x",
        prov=ProvenanceItem(page_no=1, bbox=BoundingBox(l=1, t=2, r=9, b=12), charspan=(0, 1)),
    )
    second = document.add_text(
        label=DocItemLabel.FORMULA,
        text="y",
        prov=ProvenanceItem(page_no=1, bbox=BoundingBox(l=10, t=2, r=18, b=12), charspan=(0, 1)),
    )
    page = Page(page_no=1)
    cached = Image.new("RGB", (100, 100))
    page._image_cache = {2.0: cached}

    class Model:
        def is_processable(self, doc, item):
            return str(item.label) == "formula"

        def prepare_element(self, conv, item):
            assert conv.pages[0]._image_cache[2.0] is cached
            return cached.crop((0, 0, 10, 10))

    lifetime = FormulaPageLifetime()
    result = SimpleNamespace(document=document, pages=[page])
    one = lifetime.prepare(result, Model(), first)
    assert page._image_cache[2.0] is cached
    two = lifetime.prepare(result, Model(), second)
    assert page._image_cache == {}
    assert one.size == two.size == (10, 10)
    one.close()
    two.close()
    cached.close()


def test_cell_inventory_does_not_turn_plain_headers_into_formula_items():
    from docling_core.types.doc import (
        BoundingBox,
        DoclingDocument,
        PageItem,
        ProvenanceItem,
        Size,
        TableCell,
        TableData,
    )

    from corpus_structure.ingest.pdf_candidates import CandidatePage
    from corpus_structure.ingest.pdf_enrichment import classify_cells, table_candidates
    from corpus_structure.ingest.pdf_methods import PdfEnrichConfig

    document = DoclingDocument(name="independent mixed native cell fixture")
    document.pages[1] = PageItem(page_no=1, size=Size(width=100, height=100))
    cells = [
        TableCell(
            text=value,
            bbox=BoundingBox(l=1, t=i * 20, r=90, b=i * 20 + 15),
            start_row_offset_idx=i,
            end_row_offset_idx=i + 1,
            start_col_offset_idx=0,
            end_col_offset_idx=1,
            column_header=i == 0,
        )
        for i, value in enumerate(("Probability distribution", "x", "???"))
    ]
    table = document.add_table(
        data=TableData(num_rows=3, num_cols=1, table_cells=cells),
        prov=ProvenanceItem(page_no=1, bbox=BoundingBox(l=1, t=0, r=90, b=60), charspan=(0, 0)),
    )
    cfg = PdfEnrichConfig()
    candidates = table_candidates(document, frozenset([table.self_ref]))
    demanded, reports = classify_cells(
        document,
        candidates,
        (CandidatePage(1, True, False, ()),),
        math_pattern=cfg.cell_math_pattern,
        prose_pattern=cfg.cell_prose_pattern,
    )
    assert [r["classification"] for r in reports] == ["prose", "math", "unknown"]
    assert [c.cell_index for c in demanded] == [1]
    assert table.data.table_cells[0].column_header is True
    assert not any(str(item.label) == "formula" for item in document.texts)


@pytest.mark.parametrize(
    "with_ancestor,missing_vectors,unresolved_context",
    [(False, False, False), (True, False, False), (False, True, False), (False, False, True)],
)
def test_document_enrichment_reads_one_native_parent_and_replaces_intact_view(
    monkeypatch, with_ancestor, missing_vectors, unresolved_context
):
    """Pure orchestration control; this does not qualify a model or database publication."""
    import json

    from docling_core.types.doc import (
        BoundingBox,
        DocItemLabel,
        DoclingDocument,
        PageItem,
        ProvenanceItem,
        Size,
    )
    from PIL import Image

    from corpus_structure.core.method import SourceViewRef, UnitRef, UnitView
    from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
    from corpus_structure.ingest.pdf import PdfConversion, PdfConverter, publication_payload
    from corpus_structure.ingest.pdf_candidates import CandidatePage, InlineCandidate
    from corpus_structure.ingest.pdf_health import ObservedFormulaStage
    from corpus_structure.ingest.pdf_hierarchy import organize, snapshot
    from corpus_structure.ingest.pdf_methods import EnrichPdfMath, IngestPdf, PdfEnrichConfig
    from corpus_structure.semantic.product_reference import ProductReference

    document = DoclingDocument(name="independent document-operation fixture")
    if with_ancestor:
        document.add_heading(text="1: Parent", level=1)
        document.add_text(label=DocItemLabel.TEXT, text="Parent context.")
    document.pages[1] = PageItem(page_no=1, size=Size(width=100, height=100))
    document.add_heading(text="1.1: Sets", level=2 if with_ancestor else 1)
    paragraph = document.add_text(
        label=DocItemLabel.TEXT,
        text="Let x be real.",
        orig="Let x be real.",
        prov=ProvenanceItem(page_no=1, bbox=BoundingBox(l=0, t=0, r=100, b=40), charspan=(0, 14)),
    )
    if with_ancestor:
        document.pages[2] = PageItem(page_no=2, size=Size(width=100, height=100))
        document.add_heading(text="1.2: Unselected sibling", level=2)
        document.add_text(
            label=DocItemLabel.TEXT,
            text="Outside requested units.",
            prov=ProvenanceItem(
                page_no=2, bbox=BoundingBox(l=0, t=0, r=100, b=40), charspan=(0, 24)
            ),
        )
    organization = organize(snapshot(document), PdfIngestConfig().section_policy())
    section = organization.sections[1 if with_ancestor else 0].group_ref
    membership = "descendants" if with_ancestor else "direct"
    candidate = InlineCandidate(1, "x", 25, 10, 35, 30, "TOPLEFT", "CMMI10", "native-math-font-v1")
    if unresolved_context:
        candidate = InlineCandidate(
            1,
            "",
            25,
            10,
            35,
            30,
            "TOPLEFT",
            None,
            "native-vector-gap-v1",
            "absent native context",
            "",
        )
    from hashlib import sha256

    conversion = PdfConversion(
        sha256(b"%PDF-fixture").hexdigest(),
        b"{}",
        organization.document,
        "success",
        (),
        (),
        (),
        None,
        inline_candidates=(CandidatePage(1, True, False, (candidate,), not missing_vectors),),
    )
    payload = publication_payload(
        conversion,
        product_key="organized",
        schema_digest="b" * 64,
        section_refs=frozenset([section]),
    )
    pin = ProductReference(1, "organized", "c" * 64)
    view = SourceViewRef(10, "selected-view", 1, pin, section, membership, "d" * 64, "e" * 64)
    reads = []
    prepared = []
    captured_directories = []

    class Reader:
        def source_views(self):
            return (view,)

        def native_document(self, reference, *, include_candidate_pages=True):
            reads.append(reference)
            assert include_candidate_pages is False
            return SimpleNamespace(
                values=lambda: {
                    key: value for key, value in payload.items() if key != "inline_candidate_pages"
                },
                original=b"%PDF-fixture",
                schema_bytes=b"{}",
                recipe_bytes=b"original-native-fixture",
            )

        def capture_pdf_candidates(self, reference, directory):
            from corpus_structure.ingest.pdf_candidate_source import as_candidate_source
            from corpus_structure.ingest.pdf_streaming import PdfStreamSpool

            assert reference == pin
            captured_directories.append(directory)
            spool = PdfStreamSpool(directory)
            for page in as_candidate_source(conversion.inline_candidates).iter_pages():
                spool.capture_candidates(page)
            return spool.candidate_source

        def prepare_pdf_product(self, value, original, schema, recipe):
            prepared.append(value)
            return SimpleNamespace(digest="f" * 64)

        def native_product_reference(self, document, key, digest):
            return ProductReference(2, key, digest)

    class Engine:
        def predict_batch(self, inputs):
            return [SimpleNamespace(text="x") for _ in inputs]

    class Stage:
        enabled = True
        elements_batch_size = 2
        options = SimpleNamespace()

        def __init__(self):
            self.engine = Engine()

        def __call__(self, doc, element_batch):
            batch = list(element_batch)
            self.engine.predict_batch(batch)
            yield from (e.item for e in batch)

    stage = ObservedFormulaStage(Stage())
    monkeypatch.setattr(
        "corpus_structure.ingest.pdf_candidates.rediscover_candidates",
        lambda original, pages, parser_threads: (
            CandidatePage(1, True, False, (candidate,), not missing_vectors),
        ),
    )
    cfg = PdfEnrichConfig()
    producer = IngestPdf()
    recipe = cfg.recipe()
    converter = PdfConverter(recipe)
    converter._prepared_options_report = (
        recipe.options().model_dump_json(serialize_as_any=True).encode()
    )
    monkeypatch.setattr(converter, "formula_stage", lambda: stage)
    monkeypatch.setattr(converter, "runtime_bindings", lambda: ())
    from corpus_structure.ingest.pdf_enrichment import compute_enrichment
    from corpus_structure.ingest.pdf_worker import PdfWorker

    worker = PdfWorker(recipe)
    monkeypatch.setattr(
        worker, "enrich", lambda request, **kwargs: compute_enrichment(request, converter)
    )
    producer._workers[recipe.digest] = worker
    monkeypatch.setattr(producer, "_runtime", lambda cfg: (recipe, None))
    monkeypatch.setattr(
        "corpus_structure.ingest.pdf_methods._consumer_release", lambda ctx: "release1"
    )
    guarded = []
    monkeypatch.setattr(
        "corpus_structure.ingest.pdf_methods._require_enrichment_operation",
        lambda ctx, release: guarded.append(release),
    )

    class Renderer:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def __call__(self, page, bbox):
            return Image.new("RGB", (20, 20))

    monkeypatch.setattr("corpus_structure.ingest.pdf_enrichment.PdfRegionRenderer", Renderer)
    reader = Reader()
    run = SimpleNamespace(reader=reader)
    import logging

    from corpus_structure.core.method import MethodContext, MethodSettings

    reader_port = SimpleNamespace(
        source_views=reader.source_views,
        native_document=reader.native_document,
        capture_pdf_candidates=reader.capture_pdf_candidates,
        prepare_pdf_product=reader.prepare_pdf_product,
        native_product_reference=reader.native_product_reference,
    )
    ctx = MethodContext(
        run,
        reader_port,
        MethodSettings(data_dir=Path("."), model_cache=Path(".")),
        logging.getLogger(__name__),
        retain_pdf_records=lambda unit, draft: retain(draft),
    )

    def retain(draft):
        # This pure control consumes the record draft synchronously, as its production
        # custody owner does; it does not claim database/provider qualification.
        prepared.append(
            {
                "health": dict(draft.health),
                **draft.metadata,
                "derivation_mappings": list(draft.metadata["derivation_mappings"]),
            }
        )
        return ProductReference(2, "math-enriched", "f" * 64)

    unit = UnitView(UnitRef(TaskUnitType.DOCUMENT, 1, "actual-original-key"), run)
    (result,) = EnrichPdfMath(producer).run((unit,), cfg, ctx)
    assert result.outcome is ObservationOutcome.EMPTY
    assert guarded == ["release1"]
    assert reads == [pin]
    assert len(result.native_products) == 0
    assert len(prepared) == 1
    assert captured_directories and all(not path.exists() for path in captured_directories)
    assert result.source_views[0].replaces_source_view_id == 10
    assert result.source_views[0].native_product == ProductReference(2, "math-enriched", "f" * 64)
    assert result.source_views[0].text == "1.1: Sets\nLet x be real."
    assert prepared[0]["health"]["inline_coverage"] == "unknown"
    row = next(
        r
        for r in prepared[0]["recognition_coverage"]
        if r["section_pointer"] == section and r["universe"] == "inline"
    )
    assert row["membership"] == membership
    expected_coverage = "partial" if missing_vectors or unresolved_context else "complete"
    assert row["outcome"] == expected_coverage
    assert result.source_views[0].health["inline_coverage"] == expected_coverage
    if unresolved_context:
        assert prepared[0]["inline_alignment_reports"][0]["item_pointers"] == [paragraph.self_ref]
        assert prepared[0]["inline_alignment_reports"][0]["candidate_index"] == 0
        assert prepared[0]["derivation_mappings"] == []
        return
    if with_ancestor:
        assert len(result.source_views) == 2
        assert result.source_views[1].membership == "direct"
        assert result.source_views[1].analysis_eligible is False
        assert result.source_views[1].text == "1: Parent\nParent context."
        assert {r["section_pointer"] for r in prepared[0]["recognition_coverage"]} == {
            s.group_ref for s in organization.sections[:2]
        }
        assert len(prepared[0]["recognition_coverage"]) == 6
    assert len(prepared[0]["derivation_mappings"]) == 3
    assert {r["origin_pointer"] for r in prepared[0]["derivation_mappings"]} == {paragraph.self_ref}
    assert "runtime_report" in prepared[0]
    assert (
        json.loads(prepared[0]["runtime_report"]["effective_options"])["do_formula_enrichment"]
        is True
    )


def test_source_view_drafts_derive_local_display_and_refuse_outside_scoped_inline_health():
    from docling_core.types.doc import DocItemLabel, DoclingDocument

    from corpus_structure.ingest.pdf_hierarchy import organize, snapshot
    from corpus_structure.ingest.pdf_methods import _drafts
    from corpus_structure.semantic.product_reference import ProductReference

    document = DoclingDocument(name="independent scoped health projection")
    document.add_heading(text="1.1: Sets", level=1)
    first = document.add_text(label=DocItemLabel.FORMULA, text="x")
    document.add_heading(text="1.2: Functions", level=1)
    second = document.add_text(label=DocItemLabel.FORMULA, text="y")
    organized = organize(snapshot(document), PdfIngestConfig().section_policy())
    left, right = (s.group_ref for s in organized.sections)
    health = {
        "conversion": "success",
        "display_coverage": "partial",
        "inline_coverage": "complete",
        "cell_coverage": "complete",
        "inline_scope": [left],
        "cell_scope": [left],
        "inline_membership": "direct",
        "cell_membership": "direct",
        "formula_outcomes": [
            {"pointer": first.self_ref, "outcome": "succeeded"},
            {"pointer": second.self_ref, "outcome": "failed"},
        ],
    }
    a, b = _drafts(
        1,
        ProductReference(1, "organized", "a" * 64),
        organized.document,
        health,
        (left, right),
        "direct",
        "release1",
    )
    assert (a.health["display_coverage"], b.health["display_coverage"]) == ("complete", "partial")
    assert (a.health["inline_coverage"], b.health["inline_coverage"]) == ("complete", "unknown")
    assert (a.health["cell_coverage"], b.health["cell_coverage"]) == ("complete", "unknown")
    assert a.health["formula_outcomes"] == [{"pointer": first.self_ref, "outcome": "succeeded"}]
    assert b.health["formula_outcomes"] == [{"pointer": second.self_ref, "outcome": "failed"}]


def test_descendant_projection_selects_scoped_nested_roots_before_reader_filtering():
    from docling_core.types.doc import DocItemLabel, DoclingDocument

    from corpus_structure.ingest.pdf_hierarchy import (
        load_snapshot,
        native_nodes,
        organize,
        snapshot,
    )
    from corpus_structure.ingest.pdf_methods import PdfEnrichConfig, _select_sections

    document = DoclingDocument(name="independent scoped descendant selection")
    for title, level in [
        ("1: Probability", 1),
        ("1.1: Sets", 2),
        ("Operations", 3),
        ("1.2: Functions", 2),
    ]:
        document.add_heading(text=title, level=level)
        document.add_text(label=DocItemLabel.TEXT, text=title + " content")
    organized = organize(snapshot(document), PdfIngestConfig().section_policy())
    nodes = native_nodes(load_snapshot(organized.document))
    cfg = PdfIngestConfig(membership="descendants")
    parent, sets, _operations, _functions = (s.group_ref for s in organized.sections)
    scope = {"kind": "native_sections", "sections": ["1.1: Sets"], "include_descendants": True}
    assert _select_sections(nodes, cfg, scope=scope) == (sets,)
    scope["sections"] = ["Sets", "Operations"]
    assert _select_sections(nodes, cfg, scope=scope) == (sets,)
    assert _select_sections(nodes, cfg) == (parent,)
    assert not isinstance(PdfEnrichConfig(), PdfIngestConfig)
    assert "originals" not in PdfEnrichConfig.model_fields


def test_application_wire_omits_absent_optionals_without_altering_native_nulls():
    from corpus_structure.ingest.pdf_candidates import CandidatePage, InlineCandidate
    from corpus_structure.ingest.pdf_hierarchy import ProjectedPiece

    candidate = InlineCandidate(1, "", 1, 2, 3, 4, "TOPLEFT", None, "native-vector-gap-v1")
    assert "font" not in candidate.to_wire()
    assert InlineCandidate.from_wire(candidate.to_wire()) == candidate
    assert (
        "font" not in CandidatePage(1, True, False, (candidate,), True).to_wire()["candidates"][0]
    )
    assert ProjectedPiece(None, 0, 1, "synthetic_separator").to_wire() == {
        "start": 0,
        "end": 1,
        "kind": "synthetic_separator",
    }
    assert ProjectedPiece("#/texts/0", 1, 2, "native_text", 0, "text").to_wire() == {
        "item_ref": "#/texts/0",
        "start": 1,
        "end": 2,
        "kind": "native_text",
        "cell_index": 0,
        "source_field": "text",
    }


def test_validation_error_terminal_summary_is_bounded_and_omits_input():
    from pydantic import BaseModel, ValidationError

    from corpus_structure.ingest.pdf_methods import _error_summary

    class Row(BaseModel):
        font: str

    class Report(BaseModel):
        rows: list[Row]

    with pytest.raises(ValidationError) as caught:
        Report.model_validate({"rows": [{"font": None} for _ in range(1000)]})
    summary = _error_summary(caught.value)
    assert "1000 errors" in summary
    assert "rows.0.font" in summary
    assert "rows.3.font" not in summary
    assert "input_value" not in summary
    assert len(summary) < 1800
