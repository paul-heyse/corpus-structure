"""Captured PDF fan-in for one exact admitted publication mode."""

from typing import ClassVar

from corpus_structure.methods.captured_document_composition import ComposeCapturedDocumentFamily


class ComposeOrganizedCapturedDocumentOperation(ComposeCapturedDocumentFamily):
    __data_operation__: ClassVar[dict] = {
        "abstract": False,
        "id": "text.compose_view/organized-captured-full-native",
        "dependencies": ["source.pdf_organized_views/discovery"],
        "role_overrides": [{"name": "sources", "alternatives": ["source.pdf_organized_views/discovery"], "selected": "source.pdf_organized_views/discovery"}],
    }
