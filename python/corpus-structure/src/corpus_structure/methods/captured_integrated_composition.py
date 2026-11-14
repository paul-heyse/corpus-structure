"""Captured PDF fan-in for one exact admitted publication mode."""

from typing import ClassVar

from corpus_structure.methods.captured_document_composition import ComposeCapturedDocumentFamily


class ComposeIntegratedCapturedDocumentOperation(ComposeCapturedDocumentFamily):
    __data_operation__: ClassVar[dict] = {
        "abstract": False,
        "id": "text.compose_view/integrated-captured-full-native",
        "dependencies": ["source.pdf_integrated_views/discovery"],
        "role_overrides": [{"name": "sources", "alternatives": ["source.pdf_integrated_views/discovery"], "selected": "source.pdf_integrated_views/discovery"}],
    }
