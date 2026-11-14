"""One actually acquired PDF predecessor; the finite family owns execution."""
from typing import ClassVar
from corpus_structure.ingest.pdf_enrichment_operation import PdfEnrichmentOperation

class RawPdfEnrichmentOperation(PdfEnrichmentOperation):
    __data_operation__: ClassVar[dict] = {
        "abstract": False,
        "dependencies": ["source.pdf/capture"],
        "role_overrides": [{"name": "capture", "alternatives": ["source.pdf/capture"], "selected": "source.pdf/capture"}],
    }
