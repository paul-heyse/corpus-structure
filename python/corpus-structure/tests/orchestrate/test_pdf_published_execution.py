"""Parent operation ordering; actual SQL admission has separate native controls."""
from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
import sys

import pytest

from corpus_structure.core.method import PdfRecordPublicationDraft
from corpus_structure.orchestrate.pdf_streaming import publish_pdf_record_draft


@pytest.mark.parametrize("invalid", [False, True])
def test_validation_precedes_visibility_and_failure_never_seals(monkeypatch, tmp_path, invalid):
    calls = []
    @contextmanager
    def transaction():
        calls.append("begin")
        yield object()
        calls.append("commit")
    engine = SimpleNamespace(begin=transaction)
    claim = SimpleNamespace(task_id=12, attempt=2)
    build = SimpleNamespace(build_id="owned", release_id="release")
    publication = ModuleType("corpus_structure.semantic.pdf_publication")
    def retain(*args, **kwargs):
        calls.append("recipe")
    def companions(*args, **kwargs):
        calls.append("companions")
    def freeze(*args):
        calls.append("freeze")
        return "frozen"
    def prepare(*args):
        calls.append("prepare")
    def validate(*args, **kwargs):
        calls.append("validate")
        if invalid:
            raise ValueError("native conformance failed")
    def seal(*args, **kwargs):
        calls.append("seal")
        return "published"
    vars(publication).update(
        retain_pdf_stage_recipe=retain, adopt_pdf_companion_batch=companions,
        freeze_pdf_build=freeze, prepare_pdf_build=prepare, validate_pdf_build=validate,
        seal_pdf_build=seal,
    )
    monkeypatch.setitem(sys.modules, publication.__name__, publication)
    from corpus_structure.semantic import pdf_staging
    monkeypatch.setattr(pdf_staging, "begin_pdf_build", lambda *a, **k: build)
    from corpus_structure.ingest.pdf_streaming import StreamingPdfResult
    def write(*args, **kwargs):
        calls.append("records")
        return ()
    monkeypatch.setattr(StreamingPdfResult, "write_record_batches", write)
    draft = PdfRecordPublicationDraft({}, "native", b"%PDF-1.7", b"{}", b"{}",
                                     {"conversion": "success"})
    def run():
        return publish_pdf_record_draft(engine, claim, "holder", draft,
                                        directory=tmp_path, check_active=lambda: None)
    if invalid:
        with pytest.raises(ValueError, match="native conformance"):
            run()
        assert "seal" not in calls
    else:
        assert run() == "published"
        assert calls.index("validate") < calls.index("seal")
    assert calls.index("records") < calls.index("companions") < calls.index("freeze")
    assert calls.index("freeze") < calls.index("prepare") < calls.index("validate")
