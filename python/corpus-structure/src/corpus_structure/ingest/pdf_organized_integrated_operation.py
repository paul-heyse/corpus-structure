"""One actually acquired PDF predecessor; the finite family owns execution."""

from typing import ClassVar

from corpus_structure.ingest.pdf_integration_operation import PdfIntegrationOperation


class OrganizedPdfIntegrationOperation(PdfIntegrationOperation):
    __data_operation__: ClassVar[dict] = {
        "abstract": False,
        "dependencies": ["source.pdf_sections/organize", "source.pdf_recognition/observe"],
        "role_overrides": [
            {
                "name": "capture",
                "alternatives": ["source.pdf_sections/organize"],
                "selected": "source.pdf_sections/organize",
            }
        ],
    }
