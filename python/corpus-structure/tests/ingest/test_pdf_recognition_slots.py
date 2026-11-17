"""Real owned pipe/process controls; no model, external service or GPU execution."""

import json
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pypdfium2
import pytest
from pdf_region_support import landmark_pdf

from corpus_structure.ingest.pdf_recognition import (
    NemotronRecipe, PreparedRecognitionSource, RecognitionPage, RecognitionWorker, _RecognitionSlot,
)


@pytest.fixture
def slot(tmp_path):
    script = tmp_path / "controlled_worker.py"
    script.write_text("""
import json, os, pathlib, sys, time
for line in sys.stdin:
    job = json.loads(line)
    path = pathlib.Path(job['request'])
    request = json.loads(path.read_text())
    (path.parent / 'started').touch()
    time.sleep(request.get('delay', 0))
    (path.parent / 'result.json').write_text(json.dumps({'outcome': 'succeeded', 'worker_pid': os.getpid()}))
    print(json.dumps({'request': str(path), 'fatal': False}), flush=True)
""")
    owner: Any = SimpleNamespace(python=Path(sys.executable), script=script)
    borrower = _RecognitionSlot(owner)
    try:
        yield borrower
    finally:
        borrower.close()


def job(tmp_path, name, *, delay=0):
    root = tmp_path / name
    root.mkdir()
    path = root / "input.json"
    path.write_text(json.dumps({"delay": delay}))
    return path


def test_slot_reuses_process_and_cancellation_proves_death_before_respawn(slot, tmp_path):
    first = slot.execute(job(tmp_path, "first"), lambda: None)
    second = slot.execute(job(tmp_path, "second"), lambda: None)
    assert first["worker_pid"] == second["worker_pid"]
    pending = job(tmp_path, "cancelled", delay=10)

    def cancel():
        if (pending.parent / "started").exists():
            raise InterruptedError("page cancelled")

    with pytest.raises(InterruptedError, match="page cancelled"):
        slot.execute(pending, cancel)
    assert slot.process is None
    third = slot.execute(job(tmp_path, "third"), lambda: None)
    assert third["worker_pid"] != first["worker_pid"]


def test_operation_opens_pdf_and_gpu_lease_once_and_recovery_borrows_completed_slot(
    monkeypatch, tmp_path
):
    opened, leases, calls = [], [], []
    actual = pypdfium2.PdfDocument

    def document(source):
        opened.append(source)
        return actual(source)

    @contextmanager
    def lease(check_active=None):
        leases.append("open")
        try:
            yield
        finally:
            leases.append("closed")

    def execute(self, operation, slot, recipe, number, reuse, check_active):
        calls.append((slot, recipe.digest, number))
        return RecognitionPage(number, tmp_path, {"outcome": "succeeded"}, {})

    monkeypatch.setattr(pypdfium2, "PdfDocument", document)
    monkeypatch.setattr("corpus_structure.ingest.pdf_recognition.pdf_gpu_slot", lease)
    monkeypatch.setattr(RecognitionWorker, "_execute_page", execute)
    worker = RecognitionWorker(python=Path(sys.executable), script=tmp_path / "unused",
                               endpoint="http://unused", receipts=tmp_path)
    source = PreparedRecognitionSource.prepare(landmark_pdf())
    recipe = NemotronRecipe("1" * 64, "2" * 64)
    stream = worker.recognize_pages(source, recipe, [1, 2], concurrency=1)
    try:
        assert next(stream).page_no == 1
        recovery = worker.recognize_pages(source, recipe, [1])
        try:
            assert next(recovery).page_no == 1
        finally:
            recovery.close()
        assert calls[0][0] is calls[1][0]
        assert next(stream).page_no == 2
        assert next(stream, None) is None
    finally:
        stream.close()
    assert len(opened) == 1 and leases == ["open", "closed"]
    assert worker._operation is None
