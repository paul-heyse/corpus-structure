"""The active source-entry boundary is PDF-only; HTML history remains readable."""

from pathlib import Path


def test_active_registry_has_no_html_writer_or_source_capture_module():
    from corpus_structure.semantic.pdf_capture import pdf_capture_operation_sources

    assert callable(pdf_capture_operation_sources)
    source = Path(__file__).resolve().parents[2] / "src/corpus_structure/ingest"
    assert not (source / "html.py").exists()
    assert not (source / "source_capture.py").exists()
