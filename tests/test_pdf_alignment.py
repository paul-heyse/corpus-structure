"""Retained physical-page20 regression and honest unresolved native alignment controls."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from docling_core.types.doc import (
    BoundingBox,
    CoordOrigin,
    DocItemLabel,
    DoclingDocument,
    PageItem,
    ProvenanceItem,
    Size,
)

from corpus_structure.ingest.pdf_candidates import (
    CandidatePage,
    InlineCandidate,
    capture_candidates,
)
from corpus_structure.ingest.pdf_enrichment import positioned_inline_candidates

EVIDENCE = (
    Path(__file__).resolve().parents[1] / "docs/design_review/evidence/2026-10-31_pdf-adoption/raw"
)


def retained_paragraph():
    receipt = json.loads((EVIDENCE / "inline-alignment-text513.json").read_bytes())
    assert (
        receipt["source_product"]["content_digest"]
        == "f89813cf6ce20c9dd3105838674766862211742629ec6d3a44f706064efe7cba"
    )
    assert receipt["item"]["self_ref"] == "#/texts/513"
    page = receipt["page"]
    document = DoclingDocument(name="compact retained native paragraph regression")
    document.pages[page["page_no"]] = PageItem(
        page_no=page["page_no"], size=Size(width=page["page_width"], height=page["page_height"])
    )
    # A compact valid native document gives the retained paragraph a local pointer.
    # Source text, original text and native provenance remain byte-for-value unchanged.
    item = document.add_text(
        label=DocItemLabel.TEXT,
        text=receipt["item"]["text"],
        orig=receipt["item"]["orig"],
        prov=ProvenanceItem.model_validate(receipt["item"]["prov"][0]),
    )
    return receipt, document, item


def test_retained_comma_gap_preserves_punctuation_and_qualifies_native_word_order(monkeypatch):
    receipt, document, item = retained_paragraph()
    page = receipt["pages"][0]
    old = CandidatePage(
        page["page_no"],
        page["has_words"],
        page["has_chars"],
        tuple(InlineCandidate.from_wire(row) for row in page["candidates"]),
        page["has_vectors"],
    )
    missing = positioned_inline_candidates(document, (old,), frozenset({item.self_ref}))
    report = next(row for row in missing.reports if row.candidate_index == 2)
    assert report.page_no == 20 and report.item_pointers == (item.self_ref,)
    assert report.basis == "unmatched-native-text"
    assert "start" not in report.to_wire() and "end" not in report.to_wire()

    raw = json.loads((EVIDENCE / "inline-page20-native-words.json").read_bytes())
    words = []
    for row in raw:
        box = BoundingBox(
            l=row["left"],
            t=row["top"],
            r=row["right"],
            b=row["bottom"],
            coord_origin=CoordOrigin.TOPLEFT,
        )
        words.append(
            SimpleNamespace(
                text=row["text"], rect=SimpleNamespace(to_bounding_box=lambda box=box: box)
            )
        )
    glyph = page["candidates"][2]
    box = BoundingBox(
        l=glyph["left"],
        t=glyph["top"],
        r=glyph["right"],
        b=glyph["bottom"],
        coord_origin=CoordOrigin.TOPLEFT,
    )
    monkeypatch.setattr(
        "corpus_structure.ingest.pdf_candidates.vector_boxes", lambda backend, size: [box]
    )
    source = SimpleNamespace(
        page_no=20,
        size=document.pages[20].size,
        _backend=object(),
        cells=words,
        parsed_page=SimpleNamespace(word_cells=words, has_words=True, has_chars=False),
    )
    legacy = capture_candidates(source, centroid_order=False)
    current = capture_candidates(source)
    assert legacy.candidates[0].after == "often called"
    assert current.candidates[0].after == ", often"
    found = positioned_inline_candidates(document, (current,), frozenset({item.self_ref}))
    assert not found.reports
    (position,) = found.candidates
    assert position.item_ref == item.self_ref
    assert position.start == position.end == item.text.index(", often called")
    assert item.text[position.start - 1].isspace()
    assert item.text[position.end :].startswith(", often called")
    assert position.candidate.before == "specified set"
    assert position.candidate.basis == "native-vector-gap-v1"
    assert item.text == receipt["item"]["text"]
    # A graphic containing words does not become a glyph gap merely because
    # its centroid lies between their centroids.
    graphic = BoundingBox(l=0, t=490, r=612, b=535, coord_origin=CoordOrigin.TOPLEFT)
    monkeypatch.setattr(
        "corpus_structure.ingest.pdf_candidates.vector_boxes", lambda backend, size: [graphic]
    )
    assert not any(
        candidate.basis == "native-vector-gap-v1"
        for candidate in capture_candidates(source).candidates
    )


def test_genuine_context_gap_retains_source_qualified_report_without_position():
    receipt, document, item = retained_paragraph()
    value = dict(receipt["pages"][0]["candidates"][2], before="not present in the source")
    page = CandidatePage(20, True, False, (InlineCandidate.from_wire(value),), True)
    found = positioned_inline_candidates(document, (page,), frozenset({item.self_ref}))
    assert not found.candidates
    assert len(found.reports) == 1
    assert found.reports[0].to_wire() == {
        "page_no": 20,
        "candidate_index": 0,
        "item_pointers": [item.self_ref],
        "outcome": "unresolved",
        "basis": "unmatched-native-text",
        "detail": "native word context has no unique exact projection anchor or reading order",
    }
    assert item.text == receipt["item"]["text"]


def test_overlapping_native_items_remain_ambiguous_without_inventing_offsets():
    receipt, document, item = retained_paragraph()
    other = document.add_text(
        label=DocItemLabel.TEXT, text=item.text, orig=item.orig, prov=item.prov[0]
    )
    page = CandidatePage(
        20, True, False, (InlineCandidate.from_wire(receipt["pages"][0]["candidates"][2]),), True
    )
    found = positioned_inline_candidates(
        document, (page,), frozenset({item.self_ref, other.self_ref})
    )
    assert not found.candidates
    assert found.reports[0].basis == "ambiguous-native-items"
    assert found.reports[0].item_pointers == tuple(sorted((item.self_ref, other.self_ref)))


def test_actual_native_backend_recovers_retained_page20_comma_without_inference():
    from corpus_structure.ingest.pdf_candidates import rediscover_candidates

    receipt, document, item = retained_paragraph()
    original = (
        EVIDENCE.parents[4] / "docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf"
    )
    if not original.exists():
        pytest.skip("retained Siegrist PDF unavailable")
    (page,) = rediscover_candidates(original.read_bytes(), (20,), parser_threads=2)
    candidate = next(
        candidate for candidate in page.candidates if candidate.before == "specified set"
    )
    assert candidate.after == ", often"
    found = positioned_inline_candidates(document, (page,), frozenset({item.self_ref}))
    anchor = next(
        position for position in found.candidates if position.candidate.before == "specified set"
    )
    assert anchor.start == anchor.end == item.text.index(", often called")
    assert item.text == receipt["item"]["text"]


def repeated_paragraph():
    document = DoclingDocument(name="independent repeated context ordering")
    document.pages[1] = PageItem(page_no=1, size=Size(width=100, height=100))
    value = "before after. before after."
    item = document.add_text(
        label=DocItemLabel.TEXT,
        text=value,
        orig=value,
        prov=ProvenanceItem(
            page_no=1,
            bbox=BoundingBox(l=0, t=0, r=100, b=40, coord_origin=CoordOrigin.TOPLEFT),
            charspan=(0, len(value)),
        ),
    )
    return document, item


def gap(left, right, page_no=1):
    return InlineCandidate(
        page_no,
        "",
        left,
        10,
        right,
        20,
        "TOPLEFT",
        None,
        "native-vector-gap-v1",
        "before",
        "after.",
    )


def test_repeated_contexts_use_unique_native_item_reading_order_not_input_order():
    document, item = repeated_paragraph()
    page = CandidatePage(1, True, False, (gap(80, 85), gap(10, 15)), True)
    found = positioned_inline_candidates(document, (page,), frozenset({item.self_ref}))
    assert not found.reports
    assert [part.candidate.left for part in found.candidates] == [10, 80]
    assert [part.start for part in found.candidates] == [
        len("before "),
        len("before after. before "),
    ]
    assert all(part.start == part.end for part in found.candidates)


@pytest.mark.parametrize("candidates", [(gap(10, 20), gap(10, 20)), (gap(10, 20),)])
def test_overlapping_or_unequal_repeated_contexts_stay_unresolved(candidates):
    document, item = repeated_paragraph()
    found = positioned_inline_candidates(
        document, (CandidatePage(1, True, False, candidates, True),), frozenset({item.self_ref})
    )
    assert not found.candidates
    assert len(found.reports) == len(candidates)
    assert all(report.basis == "unmatched-native-text" for report in found.reports)


def test_multi_page_context_order_uses_native_charspans_and_page_qualified_candidate_indices():
    document, item = repeated_paragraph()
    document.pages[2] = PageItem(page_no=2, size=Size(width=100, height=100))
    item.prov[0].charspan = (0, 13)
    item.prov.append(ProvenanceItem(page_no=2, bbox=item.prov[0].bbox, charspan=(14, 27)))
    pages = (
        CandidatePage(2, True, False, (gap(10, 15, 2),), True),
        CandidatePage(1, True, False, (gap(10, 15),), True),
    )
    found = positioned_inline_candidates(document, pages, frozenset({item.self_ref}))
    assert not found.reports
    assert [part.candidate.page_no for part in found.candidates] == [1, 2]
