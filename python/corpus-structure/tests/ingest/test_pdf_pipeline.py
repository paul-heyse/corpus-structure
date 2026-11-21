"""The PDF-only adapter retains native input validity and resource ownership."""

from hashlib import sha256
from io import BytesIO
from types import SimpleNamespace
from typing import Any

import pytest
from docling.backend.docling_parse_backend import ThreadedDoclingParseDocumentBackend
from docling.datamodel.backend_options import ThreadedDoclingParseBackendOptions
from docling.datamodel.base_models import ConversionStatus, FailureCategory
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import ThreadedPdfPipelineOptions
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from pdf_region_support import landmark_pdf
from pydantic import ValidationError

from corpus_structure.ingest.pdf import PreparedPdfPipeline


def prepared(execute):
    pipeline: Any = SimpleNamespace(execute=execute)
    return PreparedPdfPipeline(
        pipeline=pipeline,
        pipeline_cls=StandardPdfPipeline,
        pipeline_options=ThreadedPdfPipelineOptions(),
        backend=ThreadedDoclingParseDocumentBackend,
        backend_options=ThreadedDoclingParseBackendOptions(parser_threads=2),
    )


def test_native_pdf_input_preserves_hash_page_selection_and_explicit_release():
    seen = []

    def execute(document, *, raises_on_error):
        assert raises_on_error is False
        seen.append(document)
        return ConversionResult(input=document, status=ConversionStatus.SUCCESS)

    original = landmark_pdf()
    result = prepared(execute).convert(BytesIO(original), filename="landmarks.pdf", page_range=(2, 3))
    assert seen == [result.input]
    assert result.input.document_hash == sha256(original).hexdigest()
    assert result.input.file.name == "landmarks.pdf"
    assert result.input.page_count == 4
    assert result.input.limits.page_range == (2, 3)
    assert result.input._backend is not None
    result.input.release()
    assert result.input._backend is None
    result.input.release()


def test_invalid_pdf_retains_native_failure_without_running_pipeline():
    def forbidden(*args, **kwargs):
        pytest.fail("invalid native PDF input reached pipeline execution")

    result = prepared(forbidden).convert(BytesIO(b"not a PDF"), filename="invalid.pdf")
    assert result.status == ConversionStatus.FAILURE
    assert result.input.valid is False
    assert result.input._backend is None
    assert result.errors
    assert result.errors[0].category == FailureCategory.BACKEND_FAILURE
    result.input.release()


@pytest.mark.parametrize("page_range", [(True, 2), (0, 2), ("1", 2)])
def test_native_limits_refuse_invalid_page_selection(page_range):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid PDF limits reached pipeline execution")

    with pytest.raises(ValidationError):
        prepared(forbidden).convert(BytesIO(landmark_pdf()), filename="limits.pdf", page_range=page_range)
