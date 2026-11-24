"""Actual CPU child lifetime controls; no model/provider or PDF fidelity qualification."""

from __future__ import annotations

import multiprocessing
import os
import signal
import time
from functools import partial
from hashlib import sha256
from threading import Event, Thread

import pytest
from pdf_process_support import BlockingOwner, PartialOwner

from corpus_structure.ingest.pdf import PdfRecipe
from corpus_structure.ingest.pdf_enrichment import PdfEnrichmentRequest
from corpus_structure.ingest.pdf_worker import PdfWorker


def test_keyboard_interrupt_kills_and_joins_actual_owned_child_before_propagating(tmp_path):
    marker = tmp_path / "native-child.pid"
    worker = BlockingOwner(PdfRecipe("a" * 40, "b" * 40, device="cpu"))
    finished = Event()

    def interrupt():
        deadline = time.monotonic() + 15
        while not marker.exists() and time.monotonic() < deadline:
            if finished.wait(0.01):
                return
        if not finished.is_set():
            os.kill(os.getpid(), signal.SIGINT)

    thread = Thread(target=interrupt)
    thread.start()
    try:
        with pytest.raises(KeyboardInterrupt):
            worker.convert_bytes(str(marker).encode())
    finally:
        finished.set()
        thread.join(timeout=2)
        worker.close()
    assert marker.exists()
    pid = int(marker.read_text())
    assert worker.closed and worker.pid is None
    assert all(child.pid != pid for child in multiprocessing.active_children())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_non_success_native_reply_disposes_actual_child_before_returning():
    worker = PartialOwner(PdfRecipe("a" * 40, "b" * 40, device="cpu"))
    result = worker.convert_bytes(b"process lifetime control")
    assert result.conversion_status == "partial_success"
    assert worker.closed and worker.pid is None
    worker.close()


def _observed_enrichment_child(*args, validation_log):
    from corpus_structure.ingest import pdf_enrichment, pdf_worker
    from corpus_structure.semantic import pdf_records

    validate = pdf_records.validate_native_callbacks

    def observe(document, *, contract):
        native = validate(document, contract=contract)
        with validation_log.open("a") as log:
            log.write(f"{os.getpid()}\n")
        return native

    def refuse_snapshot(document):
        raise AssertionError("native worker repeated whole-document validation to emit its reply")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(pdf_records, "validate_native_callbacks", observe)
        patch.setattr(pdf_enrichment, "snapshot", refuse_snapshot)
        pdf_worker._native_child(*args)


def test_successful_empty_native_operations_reuse_one_serial_child(tmp_path, monkeypatch):
    from docling_core.types.doc import DoclingDocument

    from corpus_structure.ingest.pdf_hierarchy import native_snapshot_values, snapshot
    from corpus_structure.ingest.pdf_record_product import PdfConversionMetadata
    from corpus_structure.semantic.pdf_records import native_validation_contract

    original = b"%PDF-empty-selection-lifecycle-control"
    recipe = PdfRecipe("a" * 40, "b" * 40, device="cpu")
    native = snapshot(DoclingDocument(name="No inference requested"))
    conversion = PdfConversionMetadata(
        original_digest=sha256(original).hexdigest(),
        recipe=recipe.to_bytes(),
        conversion_status="success",
        errors=(),
        formula_outcomes=(),
        packages=(),
        runtime=(),
        effective_options=b"{}",
        inline_candidates=(),
        confidence=b"{}",
    )
    request = PdfEnrichmentRequest(
        conversion,
        native,
        original,
        frozenset(),
        r"=",
        r"[A-Za-z]+",
        0.75,
        native_validation_contract(),
    )
    validation_log = tmp_path / "validated-by"
    monkeypatch.setattr(
        PdfWorker,
        "_child_target",
        staticmethod(partial(_observed_enrichment_child, validation_log=validation_log)),
    )
    worker = PdfWorker(recipe)
    try:
        first = worker.enrich(request)
        pid = worker.pid
        assert pid is not None
        assert validation_log.read_text().splitlines() == [str(pid)]
        second = worker.enrich(request)
        assert worker.pid == pid
        assert validation_log.read_text().splitlines() == [str(pid), str(pid)]
        assert first.native == second.native
        assert native_snapshot_values(first.native) == native_snapshot_values(native)
        assert first.outcomes == second.outcomes == ()
        assert first.candidate_overrides == second.candidate_overrides == {}
    finally:
        worker.close()
    assert worker.pid is None and worker.closed


def test_provider_cleanup_attempts_all_owned_lanes_after_one_teardown_failure():
    from types import SimpleNamespace

    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
    from corpus_structure.methods.characterization_resources import ProviderExecution
    from corpus_structure.semantic.cpu_execution import OwnedByteBudget

    closed = []

    def fail():
        closed.append("first")
        raise RuntimeError("explicit teardown failure")

    def succeed():
        closed.append("second")

    policy = CharacterizationExecutionPolicy()
    owner = ProviderExecution(
        OwnedByteBudget(policy.max_owned_bytes), policy, native_group=SimpleNamespace()
    )
    owner._lanes = {"first": SimpleNamespace(close=fail), "second": SimpleNamespace(close=succeed)}
    with pytest.raises(RuntimeError, match="native invocation teardown failed") as caught:
        owner.close()
    assert closed == ["first", "second"]
    assert "explicit teardown failure" in caught.value.__notes__[0]


def test_failed_shutdown_retains_actual_child_handle_until_exit(tmp_path):
    from multiprocessing.process import BaseProcess

    from corpus_structure.ingest.pdf_assets import PreparedPdfAssets
    from corpus_structure.ingest.pdf_worker import PdfWorkerError

    class StubbornProcess(BaseProcess):
        def __init__(self):
            super().__init__(name="teardown-custody-control")
            self.released = False

        @property
        def pid(self) -> int | None:
            return 43210

        def is_alive(self) -> bool:
            return not self.released

        def join(self, timeout: float | None = None) -> None:
            pass

        def terminate(self) -> None:
            pass

        def kill(self) -> None:
            pass

    recipe = PdfRecipe("a" * 40, "b" * 40, device="cpu")
    other_recipe = PdfRecipe("a" * 40, "b" * 40, device="cpu", parser_threads=2)
    assets = PreparedPdfAssets(tmp_path, b"{}", (), ())
    bad = PdfWorker(recipe, assets=assets)
    process = StubbornProcess()
    bad._process = process
    good = PdfWorker(other_recipe, assets=assets)
    with pytest.raises(PdfWorkerError, match="did not exit"):
        bad.close()
    good.close()
    assert good.closed

    def current_pid(worker: PdfWorker) -> int | None:
        return worker.pid

    assert bad._process is process and current_pid(bad) == 43210
    with pytest.raises(PdfWorkerError, match="did not exit"):
        bad.close()
    assert bad._process is process
    process.released = True
    bad.close()
    assert bad.pid is None


def test_lost_active_claim_stops_actual_child_before_raising(tmp_path):
    marker = tmp_path / "lease-child.pid"
    worker = BlockingOwner(PdfRecipe("a" * 40, "b" * 40, device="cpu"))

    def check_active():
        if marker.exists():
            raise RuntimeError("authoritative claim was lost")

    with pytest.raises(RuntimeError, match="claim was lost"):
        worker.convert_bytes(str(marker).encode(), check_active=check_active)
    pid = int(marker.read_text())
    assert worker.closed and worker.pid is None
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)
