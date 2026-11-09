"""Native Docling document capture tests with controlled engine responses."""

import json
from hashlib import sha256

import pytest
from docling.models.inference_engines.vlm import VlmEngineOutput
from docling.models.stages.vlm_convert.vlm_convert_model import VlmConvertModel
from docling_core.types.doc import DoclingDocument, SectionHeaderItem
from PIL import Image

from corpus_structure.ingest import pdf_chandra
from corpus_structure.ingest.pdf_chandra_document import ChandraDocumentRuntime
from corpus_structure.ingest.pdf_recognition import transform_point

from .test_pdf_recognition import landmark_pdf


@pytest.fixture
def controlled_document(tmp_path, monkeypatch):
    model = tmp_path / "datalab-to--chandra-ocr-2"
    model.mkdir()
    data = b'{"patch_size":16}'
    (model / "preprocessor_config.json").write_bytes(data)
    monkeypatch.setattr(
        pdf_chandra, "_ARTIFACT_SHA256", {"preprocessor_config.json": sha256(data).hexdigest()}
    )
    pdf = tmp_path / "physical.pdf"
    pdf.write_bytes(landmark_pdf())

    class Engine:
        def __init__(self):
            self.calls = []
            self.fail_after = None
            self.cleaned = False

        def predict_batch(self, inputs):
            sizes = tuple(item.image.size for item in inputs)
            self.calls.append(sizes)
            if self.fail_after is not None and len(self.calls) > self.fail_after:
                return [VlmEngineOutput(text="unexpected surplus") for _ in range(len(inputs) + 1)]
            return [
                VlmEngineOutput(
                    text=(
                        '<div data-label="Section-Header" data-bbox="100 100 500 300">'
                        f"<h5>Rendered {width} by {height}</h5></div>"
                    ),
                    stop_reason="length" if width > height else "end_of_sequence",
                )
                for width, height in sizes
            ]

        def cleanup(self):
            self.cleaned = True

    engine = Engine()

    def load(runtime):
        stage = VlmConvertModel(
            enabled=False,
            enable_remote_services=False,
            artifacts_path=runtime._artifacts,
            options=runtime._options,
            accelerator_options=runtime._accelerator,
        )
        stage.enabled = True
        monkeypatch.setattr(stage, "engine", engine, raising=False)
        runtime._model = stage

    monkeypatch.setattr(pdf_chandra.ChandraRuntime, "_load_model", load)
    return pdf, engine


def test_document_capture_binds_exact_page_frames_and_native_typed_graph(
    tmp_path, controlled_document
):
    pdf, engine = controlled_document
    output = tmp_path / "captured"
    with ChandraDocumentRuntime(tmp_path, batch_size=2) as worker:
        report = worker.convert(pdf, output, page_range=(2, 4))
    assert engine.cleaned
    assert report["status"] == "partial_success"
    assert (
        report["raw_page_nos"]
        == report["typed_page_nos"]
        == report["assembled_page_nos"]
        == [2, 3, 4]
    )
    assert [batch["page_nos"] for batch in report["batches"]] == [[2, 3], [4]]
    assert engine.calls == [((800, 600), (600, 800)), ((800, 600),)]
    document = DoclingDocument.model_validate_json((output / "document.json").read_bytes())
    assert [item.prov[0].page_no for item in document.texts] == [2, 3, 4]
    assert [item.level for item in document.texts if isinstance(item, SectionHeaderItem)] == [
        4,
        4,
        4,
    ]
    assert all(page.image is None for page in document.pages.values())
    for physical in (2, 3, 4):
        directory = output / "pages" / str(physical)
        receipt = json.loads((directory / "receipt.json").read_bytes())
        assert receipt["page_no"] == physical
        assert receipt["files"] == {
            name: sha256((directory / name).read_bytes()).hexdigest()
            for name in ("submitted.png", "response.html", "prediction.json", "document.json")
        }
        with Image.open(directory / "submitted.png") as image:
            x, y = transform_point(receipt["frame"]["transform"]["affine"], 90, 170)
            assert image.getpixel((round(x), round(y))) == (255, 0, 0)
        local = DoclingDocument.model_validate_json((directory / "document.json").read_bytes())
        assert list(local.pages) == [1]
        assert isinstance(local.texts[0], SectionHeaderItem)
        assert local.texts[0].level == 5
        prediction = json.loads((directory / "prediction.json").read_bytes())
        assert prediction["stop_reason"] == ("end_of_sequence" if physical == 3 else "length")


def test_document_failure_keeps_earlier_page_and_refuses_surplus_output(
    tmp_path, controlled_document
):
    pdf, engine = controlled_document
    engine.fail_after = 1
    output = tmp_path / "captured"
    with ChandraDocumentRuntime(tmp_path, batch_size=2) as worker:
        report = worker.convert(pdf, output)
    assert report["status"] == "failure"
    assert report["raw_page_nos"] == report["typed_page_nos"] == [1, 2]
    assert report["assembled_page_nos"] == []
    assert "3 predictions for 2 submitted pages" in report["errors"][-1]["error_message"]
    assert sorted(path.name for path in (output / "pages").iterdir()) == ["1", "2"]


def test_document_reference_renderer_matches_existing_pdfium_recipe(tmp_path, controlled_document):
    from pypdfium2 import PdfDocument

    from corpus_structure.ingest.pdf_recognition import render_recognition_page

    pdf, _engine = controlled_document
    output = tmp_path / "reference"
    with ChandraDocumentRuntime(tmp_path, renderer="pdfium-reference") as worker:
        report = worker.convert(pdf, output, page_range=(2, 3))
    assert report["raw_page_nos"] == [2, 3]
    with PdfDocument(pdf) as original:
        for physical in (2, 3):
            expected, _transform = render_recognition_page(original, physical, 2.0)
            assert (output / "pages" / str(physical) / "submitted.png").read_bytes() == expected
