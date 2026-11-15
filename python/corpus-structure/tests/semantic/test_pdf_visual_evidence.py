"""Explicit visual evidence has independent identity, scope and bounded delivery."""

import json
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import ReadLimit
from corpus_structure.semantic.refusals import InvalidContinuation
from corpus_structure.serve import pdf_visual_evidence
from corpus_structure.serve.native_source import (
    NativeSourceRequest,
    _source_cursor,
    _source_position,
)
from corpus_structure.semantic.visual_evidence import VisualCaption, VisualCaptionCandidate, VisualCellGroup, VisualEvidenceArtifact, VisualEvidencePin, VisualPicture, VisualSourceRegion, VisualTable, VisualText

SOURCE = dict(project_id="project",demand_id="demand",read_id="read",use_id="source-use",product_id="source-product",derivation_id="source-episode")
EVIDENCE = VisualEvidencePin(use_id="visual-use",product_id="mapped",derivation_id="visual-episode")


def test_visual_request_binds_both_pins_and_scope_to_cursor():
    request = NativeSourceRequest(**SOURCE, view="visual_evidence", evidence=EVIDENCE, page_no=3)
    cursor = _source_cursor(request, 2)
    assert _source_position(request.model_copy(update={"cursor": cursor, "limit": 3})) == 2
    for changes in (
        {"product_id":"other"},
        {"evidence": EVIDENCE.model_copy(update={"use_id":"other-use"})},
        {"evidence": EVIDENCE.model_copy(update={"product_id":"other"})},
        {"page_no": 4},
        {"artifact_digest": "c" * 64},
        {"occurrence_id": "#/pictures/0"},
        {"visual_kind": "picture", "visual_query": "distribution"},
    ):
        with pytest.raises(InvalidContinuation):
            _source_position(request.model_copy(update={"cursor": cursor, **changes}))
    with pytest.raises(ValidationError, match="page/item scope"):
        NativeSourceRequest(**SOURCE, view="visual_evidence", evidence=EVIDENCE)
    with pytest.raises(ValidationError, match="submitted page scope"):
        NativeSourceRequest(
            **SOURCE,
            view="visual_evidence",
            evidence=EVIDENCE,
            pointer="#/pictures/0",
            artifact_digest="c" * 64,
        )


def test_mapping_retains_shared_caption_and_rich_cell_ownership():
    from corpus_structure.ingest.pdf_chandra import parse_chandra_response
    from corpus_structure.semantic.pdf_visual_mapping import map_visual_result

    parsed = parse_chandra_response(
        '<div data-label="Figure" data-bbox="10 10 350 400">'
        '<img alt="First histogram"/><figcaption>Shared distributions</figcaption></div>'
        '<div data-label="Figure" data-bbox="400 10 700 400"><img alt="Second histogram"/></div>'
        '<div data-label="Caption" data-bbox="400 420 700 450">Unrelated note</div>'
        '<div data-label="Table" data-bbox="10 500 700 900"><table>'
        "<thead><tr><th>Reading</th><th>Value</th></tr></thead>"
        "<tbody>"
        '<tr><td rowspan="2"><p>Two terms</p><p><math>x^2</math></p></td><td>1</td></tr>'
        "<tr><td>2</td></tr></tbody></table></div>",
        page_no=1,
        image_size=(100, 100),
    )
    document = parsed.document
    assert document is not None
    first, second = document.pictures
    (caption_ref,) = first.captions
    second.captions.append(caption_ref)
    artifact = map_visual_result(
        document,
        page_no=1,
        image_size=(100, 100),
        transform=dict(
            status="coarse",
            affine=(1, 0, 0, 1, 0, 0),
            page_width=100,
            page_height=100,
        ),
    )
    shared = [row for row in artifact.rows if isinstance(row, VisualCaption)]
    assert len(shared) == 1
    assert shared[0].parent_occurrence_id == first.self_ref
    assert shared[0].parser_attachment_occurrence_ids == (first.self_ref, second.self_ref)
    assert [row.occurrence_id for row in artifact.rows if isinstance(row, VisualPicture)] == [
        first.self_ref,
        second.self_ref,
    ]

    (table,) = [row for row in artifact.rows if isinstance(row, VisualTable)]
    assert len(table.cells) == 5
    rich = table.cells[2]
    assert (rich.start_row_offset_idx, rich.end_row_offset_idx) == (1, 3)
    assert rich.column_header_path == (0,)
    (group,) = [row for row in artifact.rows if isinstance(row, VisualCellGroup)]
    assert rich.content_occurrence_id == group.occurrence_id
    assert group.provider_locator == group.occurrence_id
    prose, formula = [
        row for row in artifact.rows if row.parent_occurrence_id == group.occurrence_id
    ]
    assert isinstance(prose, VisualText) and (prose.kind, prose.text) == ("cell_text", "Two terms")
    assert isinstance(formula, VisualText) and (formula.kind, formula.text) == ("formula", "x^2")
    assert table.cells[1].content_occurrence_id is None


def test_visual_artifact_retains_inherited_and_repeated_occurrences():
    panel = VisualSourceRegion(left=1, top=2, right=5, bottom=6)
    other_panel = VisualSourceRegion(left=10, top=2, right=14, bottom=6)
    inherited = panel.model_copy(update={"enclosing_occurrence_id": "p1"})
    artifact = VisualEvidenceArtifact(
        page_no=3,
        rows=(
            VisualPicture(occurrence_id="p1", source_region=panel),
            VisualCaption(
                occurrence_id="c1",
                parent_occurrence_id="p1",
                source_region=inherited,
                text="A shared caption",
            ),
            VisualText(
                occurrence_id="m1",
                parent_occurrence_id="p1",
                source_region=inherited,
                kind="mermaid",
                text="graph TD; A-->B",
            ),
            VisualPicture(occurrence_id="p2", source_region=other_panel),
            VisualCaptionCandidate(
                occurrence_id="c2",
                source_region=other_panel,
                associated_picture_occurrence_ids=("p1", "p2"),
                text="A shared caption",
            ),
        ),
    )
    rows = VisualEvidenceArtifact.model_validate_json(artifact.artifact_bytes()).rows
    assert rows == artifact.rows
    first, second = rows[1], rows[-1]
    assert isinstance(first, VisualCaption) and isinstance(second, VisualCaptionCandidate)
    assert first.source_region == inherited and first.parent_occurrence_id == "p1"
    assert second.associated_picture_occurrence_ids == ("p1", "p2")
    assert first.text == second.text and first.occurrence_id != second.occurrence_id
