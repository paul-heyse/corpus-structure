"""The active source-entry boundary is PDF-only; HTML history remains readable."""

from pathlib import Path

from corpus_structure.orchestrate.phase0 import registry


def test_active_registry_has_no_html_writer_or_source_capture_module():
    methods = registry(Path(__file__).resolve().parents[4] / "domains/statistics")
    assert "ingest.pdf" in {m.name for m in methods.methods()}
    assert "ingest.html" not in {m.name for m in methods.methods()}
    source = Path(__file__).resolve().parents[2] / "src/corpus_structure/ingest"
    assert not (source / "html.py").exists()
    assert not (source / "source_capture.py").exists()
