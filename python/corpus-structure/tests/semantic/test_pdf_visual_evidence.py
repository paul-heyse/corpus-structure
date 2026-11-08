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
from corpus_structure.serve.pdf_visual_evidence import (
    VisualCaption,
    VisualCaptionCandidate,
    VisualCellGroup,
    VisualEvidenceArtifact,
    VisualEvidencePin,
    VisualPicture,
    VisualSourceRegion,
    VisualTable,
    VisualText,
    _read_visual_artifact,
)

SOURCE = dict(run_id=7, task_id=13, product_key="selected", content_digest="a" * 64)
EVIDENCE = VisualEvidencePin(run_id=17, task_id=19, product_key="mapped", content_digest="b" * 64)


def test_visual_request_binds_both_pins_and_scope_to_cursor():
    request = NativeSourceRequest(**SOURCE, view="visual_evidence", evidence=EVIDENCE, page_no=3)
    cursor = _source_cursor(request, 2)
    assert _source_position(request.model_copy(update={"cursor": cursor, "limit": 3})) == 2
    for changes in (
        {"content_digest": "c" * 64},
        {"evidence": EVIDENCE.model_copy(update={"run_id": 21})},
        {"evidence": EVIDENCE.model_copy(update={"content_digest": "c" * 64})},
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


def test_ordinary_v4_digest_preserves_the_prior_request_shape():
    request = NativeSourceRequest(**SOURCE)
    prior = {
        **SOURCE,
        "version": 4,
        "view": "items",
        "section_pointer": None,
        "membership": None,
        "pointer": None,
        "cell_index": None,
        "occurrence_id": None,
        "artifact_digest": None,
        "collection": None,
        "max_rows": 10000,
        "max_bytes": 1024 * 1024,
    }
    prior_digest = sha256(json.dumps(prior, sort_keys=True, separators=(",", ":")).encode())
    assert request.selection_digest() == prior_digest.hexdigest()


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


@pytest.mark.parametrize("offset,size,max_bytes", [(None, 10_000, 1024), (0, 800, 1024)])
def test_visual_artifact_refuses_excess_bytes_before_fetch(offset, size, max_bytes):
    conn = Mock()
    conn.scalar.return_value = size
    with pytest.raises(ReadLimit) as refused:
        _read_visual_artifact(
            conn, EVIDENCE, "c" * 64, PublishedReadBudget(10, max_bytes), offset=offset
        )
    assert refused.value.reason == "oversized_item"
    assert "octet_length" in str(conn.scalar.call_args.args[0])
    conn.execute.assert_not_called()


def test_visual_artifact_delivers_only_the_selected_observation_image_or_raw(monkeypatch):
    from corpus_structure.semantic import pdf_contracts, pdf_record_reader, pdf_storage, releases
    from corpus_structure.serve import native_source

    image_digest, raw_digest = "c" * 64, "d" * 64
    observation = {
        "image": {
            "artifact_digest": image_digest,
            "page_no": 3,
            "transform": {"status": "unknown"},
        },
        "raw_response_digest": raw_digest,
    }
    qualify = Mock(
        return_value=dict(
            release_id="evidence-release",
            artifact_digest="original",
            contract_digest="contract",
            status="done",
            finished_at=object(),
            recipe_digest="recipe",
            observation=observation,
        )
    )
    monkeypatch.setattr(pdf_visual_evidence, "_qualified_observation", qualify)
    transfer = Mock(return_value=(b"test", 4))
    monkeypatch.setattr(pdf_visual_evidence, "_read_visual_artifact", transfer)
    incumbent = [{"pointer": "#/pictures/0", "label": "picture", "text": "incumbent"}]
    monkeypatch.setattr(pdf_visual_evidence, "_page_incumbent", Mock(return_value=incumbent))
    context = Mock(contract_digest="contract")
    context.execution.lifecycle.return_value.states = [
        SimpleNamespace(terminal=True, values=[SimpleNamespace(dimension="status", value="done")])
    ]
    monkeypatch.setattr(releases, "open_release", lambda *args: "archive")
    monkeypatch.setattr(pdf_contracts, "pdf_context_for_release", lambda *args: context)
    monkeypatch.setattr(pdf_record_reader, "published_record_reader", Mock())
    monkeypatch.setattr(pdf_storage, "_record_product_identity", Mock())
    monkeypatch.setattr(
        native_source,
        "_published_native_header",
        lambda *args, **kwargs: SimpleNamespace(
            release_id="source-release",
            artifact_digest="original",
            page_start=None,
            page_end=None,
            health={"ocr": "incumbent"},
        ),
    )
    conn = Mock()
    request = NativeSourceRequest(**SOURCE, view="visual_evidence", evidence=EVIDENCE, page_no=3)
    settings = dict(
        project_id="project",
        projection_context=Mock(release_id="source-release"),
        cancellation=Mock(),
        read_budget=PublishedReadBudget(10, 4096),
    )
    with pytest.raises(ValueError, match="image/raw custody"):
        pdf_visual_evidence.inspect_pdf_visual_evidence(
            conn, request.model_copy(update={"artifact_digest": "e" * 64}), **settings
        )
    raw_only = pdf_visual_evidence.inspect_pdf_visual_evidence(conn, request, **settings)
    assert raw_only.rows == incumbent
    assert raw_only.visual_evidence is not None
    assert raw_only.visual_evidence.mapping_availability == "unavailable"
    assert raw_only.visual_evidence.items == ()
    transfer.assert_not_called()
    for digest, media_type in (
        (image_digest, "image/png"),
        (raw_digest, "text/html; charset=utf-8"),
    ):
        selection = request.model_copy(update={"artifact_digest": digest})
        read = pdf_visual_evidence.inspect_pdf_visual_evidence(conn, selection, **settings)
        assert qualify.call_args.args[1:5] == (selection, EVIDENCE, "project", "source-release")
        assert transfer.call_args.args[1:3] == (EVIDENCE, digest)
        assert read.rows[0]["media_type"] == media_type
        assert read.rows[0]["data"] == "dGVzdA=="
        assert read.health == {"ocr": "incumbent"}
        assert read.visual_evidence is not None
        assert read.visual_evidence.mapping_availability == "unavailable"
