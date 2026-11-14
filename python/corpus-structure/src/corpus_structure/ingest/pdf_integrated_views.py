"""Exact publication discovery specializations; projection has one shared owner."""

from typing import ClassVar

from corpus_structure.ingest.pdf_views import PdfSourceViewsFamily


class IntegratedPdfSourceViewsOperation(PdfSourceViewsFamily):
    __data_operation__: ClassVar[dict] = {
        "abstract": False,
        "id": "source.pdf_integrated_views/discovery",
        "dependencies": ["source.pdf_integrated/reconcile"],
        "role_overrides": [{"name": "capture", "alternatives": ["source.pdf_integrated/reconcile"], "selected": "source.pdf_integrated/reconcile"}],
    }
