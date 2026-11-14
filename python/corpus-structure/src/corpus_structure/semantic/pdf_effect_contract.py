"""The one admitted PDF capture effect contract shared by Python and native custody."""

from .data_operation_model import EffectContract

PDF_CAPTURE_EFFECT = EffectContract(
    "publish_pdf_capture",
    ("original-source", "owned-request-attempt"),
    "request-generation/source-digest/recipe-digest",
    "sealed-native-pdf-receipt",
)
PDF_CAPTURE_FACTORY = "corpus_structure.ingest.pdf_capture.PdfCaptureOperation.acquire_port"

PDF_ENRICHMENT_EFFECT = EffectContract(
    "publish_pdf_enrichment",
    ("original-source", "exact-selected-pdf", "owned-request-attempt"),
    "request-generation/source-digest/recipe-digest",
    "sealed-native-pdf-receipt",
)
PDF_INTEGRATION_EFFECT = EffectContract(
    "publish_pdf_integration",
    ("original-source", "exact-selected-pdf", "owned-request-attempt"),
    "request-generation/source-digest/recipe-digest",
    "sealed-native-pdf-receipt",
)
PDF_ENRICHMENT_FACTORY = (
    "corpus_structure.ingest.pdf_enrichment_operation.PdfEnrichmentOperation.acquire_port"
)
PDF_INTEGRATION_FACTORY = (
    "corpus_structure.ingest.pdf_integration_operation.PdfIntegrationOperation.acquire_port"
)

PDF_ORGANIZATION_EFFECT = EffectContract(
    "publish_pdf_organization",
    ("original-source", "exact-selected-pdf", "owned-request-attempt"),
    "request-generation/source-digest/recipe-digest",
    "sealed-native-pdf-receipt",
)
PDF_ORGANIZATION_FACTORY = (
    "corpus_structure.ingest.pdf_organization_operation.PdfOrganizationOperation.acquire_port"
)
