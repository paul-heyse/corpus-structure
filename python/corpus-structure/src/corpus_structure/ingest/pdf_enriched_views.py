"""Exact publication discovery specializations; projection has one shared owner."""

from typing import ClassVar

from corpus_structure.ingest.pdf_views import PdfSourceViewsFamily


class EnrichedPdfSourceViewsOperation(PdfSourceViewsFamily):
    __data_operation__: ClassVar[dict] = {
        "abstract": False,
        "id": "source.pdf_enriched_views/discovery",
        "dependencies": ["source.pdf_math/enrich"],
        "role_overrides": [{"name": "capture", "alternatives": ["source.pdf_math/enrich"], "selected": "source.pdf_math/enrich"}],
    }


