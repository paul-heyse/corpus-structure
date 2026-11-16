"""Independent PDF staging and inventory values; no source-run setup or provider claim."""

from __future__ import annotations

import pyarrow as pa
from docling_core.types.doc import (
    BoundingBox,
    DocItemLabel,
    DoclingDocument,
    ProvenanceItem,
    Size,
)

from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult
from corpus_structure.semantic.pdf_publication import adopt_pdf_companion_batch
from corpus_structure.semantic.pdf_staging import adopt_pdf_batch


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
