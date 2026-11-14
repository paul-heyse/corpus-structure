"""The one admitted PDF capture effect contract shared by Python and native custody."""

from .data_operation_model import EffectContract

PDF_CAPTURE_EFFECT = EffectContract(
    "publish_pdf_capture",
    ("original-source", "owned-request-attempt"),
    "request-generation/source-digest/recipe-digest",
    "sealed-native-pdf-receipt",
)
PDF_CAPTURE_FACTORY = "corpus_structure.ingest.pdf_capture.PdfCaptureOperation.acquire_port"
