"""Controlled retained-PDF inputs for real publication/CLI lifecycle; no provider qualification."""

from __future__ import annotations

import textwrap
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
from types import SimpleNamespace

import pyarrow as pa
from docling_core.types.doc import (
    BoundingBox,
    CoordOrigin,
    DocItemLabel,
    DoclingDocument,
    GroupLabel,
    PageItem,
    ProvenanceItem,
    Size,
)
from pydantic import create_model
from sqlalchemy import Engine

from corpus_structure.ingest.pdf import PdfConversion, publication_payload
from corpus_structure.ingest.pdf_candidates import rediscover_candidates
from corpus_structure.ingest.pdf_hierarchy import snapshot
from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult
from corpus_structure.semantic.operations import (
    claim_tasks,
    complete_task,
    create_task,
    record_method,
)
from corpus_structure.semantic.pdf_contracts import (
    pdf_context_for_task,
    prepare_pdf_product,
    store_pdf_original,
)
from corpus_structure.semantic.pdf_publication import adopt_pdf_companion_batch
from corpus_structure.semantic.pdf_staging import adopt_pdf_batch


def retained_document(original: bytes, sections) -> PdfConversion:
    document = DoclingDocument(name="Controlled retained native source; no inference")
    for page_number, (title, paragraphs) in enumerate(sections, 1):
        document.pages[page_number] = PageItem(
            page_no=page_number, size=Size(width=612, height=792)
        )
        group = document.add_group(label=GroupLabel.SECTION, name=title)
        document.add_heading(
            text=title,
            level=1,
            parent=group,
            prov=ProvenanceItem(
                page_no=page_number,
                bbox=BoundingBox(l=36, t=34, r=575, b=62, coord_origin=CoordOrigin.TOPLEFT),
                charspan=(0, len(title)),
            ),
        )
        y = 700
        for paragraph in paragraphs:
            lines = len(textwrap.wrap(paragraph, width=85))
            document.add_text(
                label=DocItemLabel.TEXT,
                text=paragraph,
                orig=paragraph,
                parent=group,
                prov=ProvenanceItem(
                    page_no=page_number,
                    bbox=BoundingBox(
                        l=34,
                        t=792 - y - 15,
                        r=580,
                        b=792 - y + 15 * (lines - 1) + 6,
                        coord_origin=CoordOrigin.TOPLEFT,
                    ),
                    charspan=(0, len(paragraph)),
                ),
            )
            y -= 15 * lines + 15
    pages = rediscover_candidates(original, tuple(range(1, len(sections) + 1)), parser_threads=1)
    assert all(page.has_words and page.has_vectors and not page.candidates for page in pages)
    return PdfConversion(
        sha256(original).hexdigest(),
        b'{"fixture":"controlled-native-prose-no-inference"}',
        snapshot(document),
        "success",
        (),
        (),
        (),
        None,
        inline_candidates=pages,
    )


def write_controlled_pdf(path: Path, paragraphs: tuple[str, ...]) -> bytes:
    """Use the existing authored PDF builder; no converter or recognizer is involved."""
    import runpy

    builder = runpy.run_path(str(Path(__file__).resolve().parents[3] / "fixtures/toy/build_pdf.py"))
    builder["write_pdf"](path, ((paragraphs[0], paragraphs[1:]),))
    return path.read_bytes()


def publish_controlled_pdf_views(
    engine,
    *,
    prepared,
    run_id,
    document_id,
    original,
    paragraphs,
    source_claim=None,
    admin: Engine | None = None,
):
    """Retain authored sections; a supplied claim leaves terminal settlement with its owner."""
    from tempfile import TemporaryDirectory

    from semantic.native_record_fixtures import publish_native_record_fixture

    from corpus_structure.ingest.pdf_section_views import published_section_drafts
    from corpus_structure.semantic.operation_results import MethodConfigId, RunId
    from corpus_structure.semantic.pdf_record_reader import published_record_reader
    from corpus_structure.semantic.product_reference import ProductReference
    from corpus_structure.semantic.source_views import load_source_view, store_source_view

    document = DoclingDocument(name="Controlled source reports; no inference")
    root = document.add_group(label=GroupLabel.SECTION, name="People")
    sections = [root]
    for index in range(1, len(paragraphs)):
        sections.append(
            document.add_group(
                label=GroupLabel.SECTION,
                name="Other" if index == 1 else f"Other {index}",
                parent=root,
            )
        )
    for index, paragraph in enumerate(paragraphs):
        document.add_text(
            label=DocItemLabel.TEXT,
            text=paragraph,
            orig=paragraph,
            parent=sections[min(index, len(sections) - 1)],
        )
    conversion = PdfConversion(
        sha256(original).hexdigest(),
        b'{"fixture":"controlled-native-report-v1"}',
        snapshot(document),
        "success",
        (),
        (),
        (),
        None,
    )
    schema = (
        files("corpus_structure")
        .joinpath("model/semantic/docling-validation.schema.json")
        .read_bytes()
    )
    config: MethodConfigId | None = None
    if source_claim is None:
        if admin is None:
            raise ValueError(
                "historical source configuration requires its explicit administrative setup engine"
            )
        with admin.begin() as conn:
            config = record_method(
                conn,
                SimpleNamespace(
                    name="pdf.controlled-source",
                    version="1",
                    family="ingest",
                    tier="deterministic",
                    confidence_source=None,
                    unit_type="document",
                    Config=create_model("ControlledSource"),
                ),
                "default",
                {},
                "controlled-source-config",
                prepared=prepared,
            )
    with engine.begin() as conn:
        if source_claim is None:
            assert config is not None
            assert admin is not None
            with admin.begin() as setup:
                task = create_task(
                    setup,
                    run_id=run_id,
                    config_id=config,
                    stage="ingest",
                    unit_type="document",
                    unit_id=document_id,
                    unit_key="controlled-source",
                    input_hash=conversion.original_digest,
                )
            claim = claim_tasks(
                conn,
                run_id=RunId(run_id),
                config_id=MethodConfigId(config),
                holder="controlled-source",
            )[0]
        else:
            claim = source_claim
            task = claim.task_id
        store_pdf_original(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder=claim.holder,
            original=original,
            recipe_bytes=conversion.recipe,
        )
        payload = publication_payload(
            conversion,
            product_key="native",
            schema_digest=sha256(schema).hexdigest(),
            section_refs=frozenset(section.self_ref for section in sections),
        )
        product = prepare_pdf_product(
            payload, original, schema, conversion.recipe, context=pdf_context_for_task(conn, task)
        )
    with TemporaryDirectory(prefix="controlled-native-views-") as directory:
        published = publish_native_record_fixture(
            engine,
            Path(directory),
            task_id=task,
            attempt=claim.attempt,
            holder=claim.holder,
            product=product,
            document=document,
        )
    with engine.begin() as conn:
        reader = published_record_reader(
            conn,
            ProductReference(task, "native", published.logical_digest),
            projection_context=prepared,
        )
        if reader is None:
            raise AssertionError("controlled source has no published record binding")
        views = []
        for index, section in enumerate(sections):
            membership = "descendants" if index == 0 and len(sections) > 1 else "direct"
            (draft,) = published_section_drafts(
                reader,
                document_id=document_id,
                selections=(section.self_ref,),
                membership=membership,
                scope=None,
                consumer_release=prepared.release_id,
            )
            view_id = store_source_view(
                conn,
                run_id=run_id,
                task_id=task,
                attempt=claim.attempt,
                holder=claim.holder,
                draft=draft,
                position=index,
            )
            views.append(load_source_view(conn, view_id))
        if source_claim is None:
            complete_task(
                conn,
                task_id=task,
                attempt=claim.attempt,
                holder=claim.holder,
                prepared=prepared,
                observations=[],
                outcome="empty",
            )
        return tuple(views)


def independent_pdf_address(conn, run_id, key, *, start=None, end=None, pointer=None):
    """Author expected transport fields from immutable pins and explicit test coordinates.

    No producer frame, stored locator, citation or source-address implementation is read.
    """
    import json

    from sqlalchemy import select

    from corpus_structure.semantic.metadata import table

    views, selected = table("kb.source_view"), table("ops.run_source_view")
    row = conn.execute(
        select(views.c.id, views.c.native_content_digest, views.c.projection_digest)
        .join(selected, selected.c.source_view_id == views.c.id)
        .where(selected.c.run_id == run_id, views.c.key == key)
    ).one()
    address = {"product_digest": row.native_content_digest}
    address.update(
        {"pointer": pointer}
        if pointer is not None
        else {
            "source_view_id": row.id,
            "projection_digest": row.projection_digest,
            "start": start,
            "end": end,
        }
    )
    return "pdf:" + json.dumps(address, sort_keys=True, separators=(",", ":"))


def native_evidence_sources(inputs):
    from corpus_structure.semantic.domain_operations import NativeEvidenceLink
    from corpus_structure.semantic.publication import EvidenceSourceRow

    result = []
    for evidence_id, link in inputs.source_links.items():
        assert isinstance(link, NativeEvidenceLink)
        result.append(
            EvidenceSourceRow(
                evidence_id,
                link.observation_id,
                None,
                source_view_id=link.source_view_id,
                native_address=link.native_address,
            )
        )
    return tuple(result)


def stage_complete_native(engine, build, directory, *, cell_coverage="unknown", region=False):
    document = DoclingDocument(name="frozen fixture")
    document.add_page(page_no=1, size=Size(width=200, height=300))
    expected = "independent expected text"
    provenance = (
        ProvenanceItem(
            page_no=1, bbox=BoundingBox(l=1, t=10, r=100, b=20), charspan=(0, len(expected))
        )
        if region
        else None
    )
    document.add_text(label=DocItemLabel.TEXT, text=expected, prov=provenance)
    result = StreamingPdfResult(
        document, PdfStreamSpool(directory / "pages"), "success", (), b"{}", ()
    )
    for replay in result.write_record_batches(
        directory / "records",
        build_id=build.build_id,
        release_id=build.release_id,
        source_digest=build.source_digest,
    ):
        with pa.memory_map(str(replay.path), "r") as source:
            reader = pa.ipc.open_file(source)
            for index in range(reader.num_record_batches):
                with engine.begin() as conn:
                    adopt_pdf_batch(
                        conn,
                        build,
                        f"{replay.family}:{index}",
                        {replay.family: (reader.get_batch(index),)},
                    )
    with engine.begin() as conn:
        adopt_pdf_companion_batch(
            conn,
            build,
            "health",
            [
                {
                    "conversion": "success",
                    "display_coverage": "unknown",
                    "inline_coverage": "unknown",
                    "cell_coverage": cell_coverage,
                    "source_scope": "whole_document",
                }
            ],
            "health",
        )
    return document


def inventory():
    words = []
    for index, (spelling, start, left, right) in enumerate(
        (("x", 0, 3, 12), ("=", 2, 15, 24), ("2", 4, 27, 36))
    ):
        words.append(
            dict(
                word_index=index,
                text=spelling,
                confidence=0.9,
                start=start,
                end=start + 1,
                raster_left=left,
                raster_top=6,
                raster_right=right,
                raster_bottom=21,
                left=26 + left / 3,
                top=42,
                right=26 + right / 3,
                bottom=47,
            )
        )
    region = dict(
        region_index=0,
        engine="rapidocr",
        raster_width=120,
        raster_height=60,
        scale=3.0,
        orientation=0,
        left=26,
        top=40,
        right=66,
        bottom=60,
        outcome="complete",
        lines=[dict(line_index=0, text="x = 2", words=words)],
    )
    word = words[0]
    candidate = {key: word[key] for key in ("text", "left", "top", "right", "bottom")}
    candidate.update(
        page_no=1,
        origin="TOPLEFT",
        basis="ocr-word-token-v1",
        ocr_region_index=0,
        ocr_line_index=0,
        ocr_word_index=0,
    )
    return dict(
        page_no=1,
        has_words=False,
        has_chars=False,
        has_vectors=True,
        native_text_quality="broken",
        ocr_regions=[region],
        candidates=[candidate],
    )
