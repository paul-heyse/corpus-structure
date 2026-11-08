"""CPU controls for the pinned Chandra adapter and native Docling replay."""

from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
from docling.datamodel.base_models import VlmPrediction, VlmStopReason
from docling.datamodel.vlm_prompts import CHANDRA_OCR_LAYOUT_PROMPT
from docling_core.types.doc import SectionHeaderItem
from PIL import Image

from corpus_structure.ingest import pdf_chandra
from corpus_structure.ingest.pdf_chandra import (
    ChandraCompletion,
    ChandraParseIssue,
    ChandraParseStatus,
    ChandraRuntime,
    parse_chandra_response,
)


def _parse(raw: str, stop_reason: str | None = None) -> pdf_chandra.ChandraParse:
    return parse_chandra_response(raw, image_size=(200, 300), page_no=7, stop_reason=stop_reason)


def test_native_replay_preserves_crop_pixels_and_raw_heading_level() -> None:
    result = _parse(
        '<div data-label="Section-Header" data-bbox="100 200 500 600">'
        "<h5>Printed heading</h5></div>"
    )
    assert result.status is ChandraParseStatus.PARSED
    assert result.completion is ChandraCompletion.UNKNOWN
    assert result.document is not None
    (heading,) = result.document.texts
    assert isinstance(heading, SectionHeaderItem)
    assert heading.text == "Printed heading"
    assert heading.level == 5
    (provenance,) = heading.prov
    assert provenance.page_no == 7
    box = provenance.bbox
    assert box.coord_origin.value == "TOPLEFT"
    assert (box.l, box.t, box.r, box.b) == (20, 60, 100, 180)


@pytest.mark.parametrize(
    ("raw", "status", "issues"),
    [
        ('<div data-label="Blank-Page"></div>', ChandraParseStatus.EXPLICIT_BLANK, ()),
        (" \n", ChandraParseStatus.MISSING_OUTPUT, ()),
        ("plain prose", ChandraParseStatus.MALFORMED, (ChandraParseIssue.UNSTRUCTURED_HTML,)),
        ("<p>Bare HTML</p>", ChandraParseStatus.RECOVERED, (ChandraParseIssue.UNSTRUCTURED_HTML,)),
        (
            '<div data-label="Text">Missing box</div>',
            ChandraParseStatus.RECOVERED,
            (ChandraParseIssue.MISSING_GEOMETRY,),
        ),
        *(
            (
                f'<div data-label="Text" data-bbox="{box}">Unlocated text</div>',
                ChandraParseStatus.RECOVERED,
                (ChandraParseIssue.INVALID_GEOMETRY,),
            )
            for box in ("a b", "800 200 100 300", "100 200 100 300", "nan 200 800 300")
        ),
    ],
)
def test_missing_malformed_and_unlocated_output(raw, status, issues) -> None:
    result = _parse(raw)
    assert result.status is status
    assert result.completion is ChandraCompletion.UNKNOWN
    assert result.issues == issues
    if status is ChandraParseStatus.RECOVERED:
        assert result.document is not None
        assert result.document.texts[0].text
        assert result.document.texts[0].prov == []


@pytest.mark.parametrize(
    ("stop_reason", "completion"),
    [
        ("unspecified", ChandraCompletion.UNKNOWN),
        ("length", ChandraCompletion.LENGTH),
        ("content_filter", ChandraCompletion.FILTERED),
        ("inference_error", ChandraCompletion.ERROR),
        ("stop_sequence", ChandraCompletion.STOPPED),
        ("end_of_sequence", ChandraCompletion.COMPLETE),
    ],
)
def test_completion_is_independent_of_html_recovery(stop_reason, completion) -> None:
    result = _parse('<div data-label="Text" data-bbox="100 200 800 300"><p>First part', stop_reason)
    assert result.status is ChandraParseStatus.RECOVERED
    assert result.completion is completion
    assert result.issues == (ChandraParseIssue.MALFORMED_HTML,)
    assert result.document is not None
    assert result.document.texts[0].text == "First part"


def test_replay_preserves_unmarked_repetition_as_suspect_evidence() -> None:
    repeated = "Repeated sentence. " * 24
    result = _parse(f'<div data-label="Text" data-bbox="100 200 800 300">{repeated}</div>')
    assert result.status is ChandraParseStatus.RECOVERED
    assert result.completion is ChandraCompletion.UNKNOWN
    assert result.issues == (ChandraParseIssue.REPETITION_SUSPECTED,)
    assert result.document is not None
    assert result.document.texts[0].text.count("Repeated sentence.") == 24


def test_blank_marker_conflicting_with_unlabelled_text_is_recovered() -> None:
    result = _parse('<div data-label="Blank-Page"></div><p>Unlabelled transcription</p>')
    assert result.status is ChandraParseStatus.RECOVERED
    assert result.issues == (ChandraParseIssue.BLANK_MARKER_CONFLICT,)


def test_native_empty_table_fallback_is_recovered() -> None:
    result = _parse(
        '<div data-label="Table" data-bbox="100 200 800 300">'
        "<table><caption>Caption</caption></table></div>"
    )
    assert result.status is ChandraParseStatus.RECOVERED
    assert result.issues == (ChandraParseIssue.EMPTY_TABLE,)
    assert result.document is not None
    assert result.document.texts[0].text == "Caption"


@pytest.fixture
def model_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    model = tmp_path / "datalab-to--chandra-ocr-2"
    model.mkdir()
    files = {"preprocessor_config.json": b'{"patch_size":16}', "model.safetensors": b"fixture"}
    for name, content in files.items():
        (model / name).write_bytes(content)
    monkeypatch.setattr(
        pdf_chandra,
        "_ARTIFACT_SHA256",
        {name: sha256(content).hexdigest() for name, content in files.items()},
    )
    return model


def test_unpinned_artifacts_refused_before_model_load(model_artifacts: Path) -> None:
    sidecar = model_artifacts / "added_tokens.json"
    sidecar.write_bytes(b"{}")
    with pytest.raises(ValueError, match=r"unexpected Chandra artifacts: added_tokens\.json"):
        ChandraRuntime(model_artifacts.parent)
    sidecar.unlink()
    (model_artifacts / "model.safetensors").write_bytes(b"different")
    with pytest.raises(ValueError, match=r"artifact integrity mismatch: model\.safetensors"):
        ChandraRuntime(model_artifacts.parent)


def test_native_stage_boundary_keeps_rgb_raster_and_raw_prediction(
    model_artifacts: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = ChandraRuntime(model_artifacts.parent)
    identity = runtime.identity()
    assert identity["prompt"] == CHANDRA_OCR_LAYOUT_PROMPT
    assert identity["engine"]["torch_dtype"] == "bfloat16"
    assert not identity["engine"]["load_in_8bit"]
    assert not identity["engine"]["trust_remote_code"]
    assert runtime.effective_device is None
    with pytest.raises(ValueError, match="RGB raster"):
        runtime.recognize(Image.new("RGBA", (25, 40)))

    raster = Image.new("RGB", (25, 40), (7, 8, 9))
    prediction = VlmPrediction(text="<div unparsed", stop_reason=VlmStopReason.UNSPECIFIED)
    cleanup = []

    def process_images(images, prompt):
        assert images[0] is raster
        assert prompt == CHANDRA_OCR_LAYOUT_PROMPT
        yield prediction

    monkeypatch.setattr(
        runtime,
        "_model",
        SimpleNamespace(
            process_images=process_images,
            engine=SimpleNamespace(cleanup=lambda: cleanup.append(True)),
        ),
    )
    assert runtime.recognize(raster) is prediction
    runtime.close()
    runtime.close()
    assert cleanup == [True]
