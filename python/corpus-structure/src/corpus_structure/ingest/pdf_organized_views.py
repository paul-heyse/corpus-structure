"""Exact publication discovery specializations; projection has one shared owner."""

from typing import ClassVar

from corpus_structure.ingest.pdf_views import PdfSourceViewsFamily


class OrganizedPdfSourceViewsOperation(PdfSourceViewsFamily):
    __data_operation__: ClassVar[dict] = {
        "abstract": False,
        "id": "source.pdf_organized_views/discovery",
        "dependencies": ["source.pdf_sections/organize"],
        "role_overrides": [{"name": "capture", "alternatives": ["source.pdf_sections/organize"], "selected": "source.pdf_sections/organize"}],
    }


