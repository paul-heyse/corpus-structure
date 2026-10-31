"""Actual CPU child lifetime controls; no model/provider or PDF fidelity qualification."""
from __future__ import annotations

import multiprocessing
import os
import signal
import time
from hashlib import sha256
from pathlib import Path
from threading import Event,Thread

import pytest

from corpus_structure.ingest.pdf import PdfConversion,PdfRecipe
from corpus_structure.ingest.pdf_enrichment import PdfEnrichmentRequest
from corpus_structure.ingest.pdf_hierarchy import NativeSnapshot
from corpus_structure.ingest.pdf_worker import ConvertRequest,NativeReply,PdfWorker


from pdf_process_support import BlockingOwner,PartialOwner


def test_keyboard_interrupt_kills_and_joins_actual_owned_child_before_propagating(tmp_path):
    marker=tmp_path/'native-child.pid'
    worker=BlockingOwner(PdfRecipe('a'*40,'b'*40,device='cpu'))
    finished=Event()
    def interrupt():
        deadline=time.monotonic()+15
        while not marker.exists() and time.monotonic()<deadline:
            if finished.wait(0.01):
                return
        if not finished.is_set():
            os.kill(os.getpid(),signal.SIGINT)
    thread=Thread(target=interrupt)
    thread.start()
    try:
        with pytest.raises(KeyboardInterrupt):
            worker.convert_bytes(str(marker).encode())
    finally:
        finished.set()
        thread.join(timeout=2)
        worker.close()
    assert marker.exists()
    pid=int(marker.read_text())
    assert worker.closed and worker.pid is None
    assert all(child.pid!=pid for child in multiprocessing.active_children())
    with pytest.raises(ProcessLookupError):
        os.kill(pid,0)


def test_non_success_native_reply_disposes_actual_child_before_returning():
    worker=PartialOwner(PdfRecipe('a'*40,'b'*40,device='cpu'))
    result=worker.convert_bytes(b'process lifetime control')
    assert result.conversion_status=='partial_success'
    assert worker.closed and worker.pid is None
    worker.close()


def test_successful_empty_native_operations_reuse_one_serial_child():
    from docling_core.types.doc import DoclingDocument
    from corpus_structure.ingest.pdf_hierarchy import snapshot
    original=b'%PDF-empty-selection-lifecycle-control'
    recipe=PdfRecipe('a'*40,'b'*40,device='cpu')
    native=snapshot(DoclingDocument(name='No inference requested'))
    conversion=PdfConversion(sha256(original).hexdigest(),recipe.to_bytes(),native,'success',(),(),(),None)
    request=PdfEnrichmentRequest(conversion,original,frozenset(),r'=',r'[A-Za-z]+',0.75)
    worker=PdfWorker(recipe)
    try:
        first=worker.enrich(request)
        pid=worker.pid
        second=worker.enrich(request)
        assert pid is not None and worker.pid==pid
        assert first.native==second.native==native
        assert first.outcomes==second.outcomes==()
    finally:
        worker.close()
    assert worker.pid is None and worker.closed


def test_source_cleanup_attempts_all_closers_and_preserves_original_interrupt():
    from types import SimpleNamespace
    from corpus_structure.orchestrate.semantic import _close_source_resources
    closed=[]
    def fail():
        closed.append('first')
        raise RuntimeError('explicit teardown failure')
    def succeed():
        closed.append('second')
    registry=SimpleNamespace(methods=lambda:(SimpleNamespace(close=fail),SimpleNamespace(close=succeed)))
    original=KeyboardInterrupt()
    _close_source_resources(registry,original)
    assert closed==['first','second']
    assert 'explicit teardown failure' in original.__notes__[0]


def test_failed_shutdown_keeps_owner_handle_and_attempts_other_closers(tmp_path):
    from multiprocessing.process import BaseProcess
    from corpus_structure.ingest.pdf_assets import PreparedPdfAssets
    from corpus_structure.ingest.pdf_methods import IngestPdf
    from corpus_structure.ingest.pdf_worker import PdfWorkerError
    class StubbornProcess(BaseProcess):
        def __init__(self):
            super().__init__(name='teardown-custody-control')
            self.released=False
        @property
        def pid(self)->int|None:
            return 43210
        def is_alive(self)->bool:
            return not self.released
        def join(self,timeout:float|None=None)->None:
            pass
        def terminate(self)->None:
            pass
        def kill(self)->None:
            pass
    recipe=PdfRecipe('a'*40,'b'*40,device='cpu')
    other_recipe=PdfRecipe('a'*40,'b'*40,device='cpu',parser_threads=2)
    assets=PreparedPdfAssets(tmp_path,b'{}',(),())
    owner=IngestPdf()
    bad=PdfWorker(recipe,assets=assets)
    process=StubbornProcess()
    bad._process=process
    good=PdfWorker(other_recipe,assets=assets)
    owner._workers={recipe.digest:bad,other_recipe.digest:good}
    with pytest.raises(PdfWorkerError,match='did not exit'):
        owner.close()
    assert good.closed
    assert owner._workers=={recipe.digest:bad}
    assert bad._process is process
    with pytest.raises(PdfWorkerError,match='did not exit'):
        owner._worker(recipe,assets)
    assert owner._workers[recipe.digest] is bad
    process.released=True
    replacement=owner._worker(recipe,assets)
    assert replacement is not bad
    assert bad.pid is None
    owner.close()


def test_lost_active_claim_stops_actual_child_before_raising(tmp_path):
    marker=tmp_path/'lease-child.pid'
    worker=BlockingOwner(PdfRecipe('a'*40,'b'*40,device='cpu'))
    def check_active():
        if marker.exists():
            raise RuntimeError('authoritative claim was lost')
    with pytest.raises(RuntimeError,match='claim was lost'):
        worker.convert_bytes(str(marker).encode(),check_active=check_active)
    pid=int(marker.read_text())
    assert worker.closed and worker.pid is None
    with pytest.raises(ProcessLookupError):
        os.kill(pid,0)


def test_registries_have_distinct_pdf_owners_and_share_only_with_own_enricher():
    from corpus_structure.ingest.pdf_methods import IngestPdf,EnrichPdfMath
    from corpus_structure.orchestrate.phase0 import registry
    pack=Path(__file__).resolve().parents[1]/'domains/statistics'
    first,second=registry(pack),registry(pack)
    left,right=first.method('ingest.pdf'),second.method('ingest.pdf')
    assert isinstance(left,IngestPdf) and isinstance(right,IngestPdf)
    assert left is not right
    enrich=first.method('enrich.pdf_math')
    assert isinstance(enrich,EnrichPdfMath) and enrich.producer is left
