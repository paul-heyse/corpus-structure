"""Actual owned PDF processes retain custody when native teardown cannot be proven."""

import multiprocessing
import time

import pytest

from corpus_structure.core.work import PhysicalRetirementUncertain
from corpus_structure.ingest.pdf import PdfRecipe
from corpus_structure.ingest.pdf_worker import ConvertRequest, PdfRetirementUncertain, PdfWorker


def child(connection, started):
    started.set()
    if connection is not None:
        connection.recv()
        connection.send("invalid native reply")
    while True:
        time.sleep(0.1)


def owned_worker(*, exchange=False):
    context = multiprocessing.get_context("spawn")
    started = context.Event()
    parent, child_end = context.Pipe()
    process = context.Process(target=child, args=(child_end if exchange else None, started))
    process.start()
    child_end.close()
    assert started.wait(15)
    worker = PdfWorker(PdfRecipe("a" * 40, "b" * 40))
    worker._process = process
    worker._connection = parent
    return worker, process


def refuse_termination():
    raise OSError("controlled native termination refusal")


def test_unproven_actual_pdf_process_retains_handle_and_typed_custody(monkeypatch):
    worker, process = owned_worker()
    try:
        with monkeypatch.context() as patch:
            patch.setattr(process, "terminate", refuse_termination)
            with pytest.raises(PdfRetirementUncertain) as raised:
                worker.close()
            assert isinstance(raised.value, PhysicalRetirementUncertain)
            assert process.is_alive() and worker.pid == process.pid
    finally:
        process.kill()
        process.join(5)
        worker.close()
    assert worker.pid is None


def test_original_protocol_error_keeps_retirement_uncertainty_structural(monkeypatch):
    worker, process = owned_worker(exchange=True)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(process, "terminate", refuse_termination)
            with pytest.raises(ExceptionGroup) as raised:
                worker._exchange(ConvertRequest(b"input", "control", None))
            assert any(isinstance(error, PhysicalRetirementUncertain)
                       for error in raised.value.exceptions)
            assert any("unsupported response" in str(error) for error in raised.value.exceptions)
            assert process.is_alive()
    finally:
        process.kill()
        process.join(5)
        worker.close()
    assert worker.pid is None
