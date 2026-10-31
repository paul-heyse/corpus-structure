"""One serial, spawned native PDF child per owned recipe; no database handles cross IPC."""
from __future__ import annotations

import multiprocessing
from dataclasses import dataclass
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from threading import Lock
from typing import TypeAlias

from .pdf import PdfConversion,PdfConverter,PdfRecipe
from .pdf_assets import PreparedPdfAssets
from .pdf_enrichment import PdfEnrichmentRequest,PdfEnrichmentResult,compute_enrichment


@dataclass(frozen=True,slots=True)
class ConvertRequest:
    original:bytes
    name:str
    page_range:tuple[int,int]|None


Request:TypeAlias=ConvertRequest|PdfEnrichmentRequest
Result:TypeAlias=PdfConversion|PdfEnrichmentResult


@dataclass(frozen=True,slots=True)
class NativeReply:
    value:Result|None=None
    error:str|None=None


class PdfWorkerError(RuntimeError):
    """A native child refused or lost its operation; no publication was performed."""


def _native_child(connection:Connection,recipe:PdfRecipe,assets:PreparedPdfAssets|None)->None:
    converter=PdfConverter(recipe,assets=assets)
    try:
        while True:
            request=connection.recv()
            if request is None:
                return
            try:
                if isinstance(request,ConvertRequest):
                    result=converter.convert_bytes(request.original,name=request.name,page_range=request.page_range)
                elif isinstance(request,PdfEnrichmentRequest):
                    result=compute_enrichment(request,converter)
                else:
                    raise TypeError('unsupported finite PDF worker request')
                connection.send(NativeReply(value=result))
            except Exception as error:
                # App-envelope preparation remains in the parent. Native failures cross as
                # ordinary bounded diagnostics, never live exceptions/models/backend handles.
                connection.send(NativeReply(error=(type(error).__name__+': '+str(error))[:1800]))
    finally:
        connection.close()


class PdfWorker:
    """Owned child lifetime across conversion and demanded enrichment, with bounded teardown.

    Cancellation disposes IPC and terminates/joins the process before it propagates. A final
    kill handles native C/GPU calls that Python threads cannot interrupt. A teardown failure
    keeps the process handle and raises; it cannot silently report successful cleanup/reuse.
    """
    _child_target=staticmethod(_native_child)

    def __init__(self,recipe:PdfRecipe,*,assets:PreparedPdfAssets|None=None)->None:
        self.recipe=recipe
        self.assets=assets
        self._process:BaseProcess|None=None
        self._connection:Connection|None=None
        self._lock=Lock()
        self._closed=False

    @property
    def closed(self)->bool:
        return self._closed

    @property
    def pid(self)->int|None:
        return self._process.pid if self._process is not None else None

    def _start(self)->None:
        if self._closed:
            raise PdfWorkerError('native PDF owner is closed')
        if self._process is not None:
            return
        context=multiprocessing.get_context('spawn')
        parent,child=context.Pipe(duplex=True)
        process=context.Process(target=self._child_target,args=(child,self.recipe,self.assets),
            name='native-pdf',daemon=True)
        self._connection=parent
        self._process=process
        try:
            process.start()
        finally:
            child.close()

    def _exchange(self,request:Request)->Result:
        with self._lock:
            try:
                self._start()
                connection=self._connection
                process=self._process
                if connection is None or process is None:
                    raise PdfWorkerError('native PDF child has no connected owner')
                connection.send(request)
                while not connection.poll(0.2):
                    if not process.is_alive():
                        raise PdfWorkerError(f'native PDF child exited with code {process.exitcode}')
                reply=connection.recv()
                if not isinstance(reply,NativeReply):
                    raise PdfWorkerError('native PDF child returned an unsupported response')
                if reply.error is not None:
                    raise PdfWorkerError(reply.error)
                if reply.value is None:
                    raise PdfWorkerError('native PDF child returned no result')
                # A timed/non-success native pipeline may have abandoned a worker thread.
                # Drain the containing process before exposing even its partial result.
                if isinstance(reply.value,PdfConversion) and reply.value.conversion_status!='success':
                    self._stop(graceful=False)
                return reply.value
            except BaseException as original:
                try:
                    self._stop(graceful=False)
                except BaseException as cleanup:
                    original.add_note('native PDF teardown failed: '+str(cleanup)[:1800])
                raise

    def convert_bytes(self,original:bytes,*,name:str='original.pdf',
                      page_range:tuple[int,int]|None=None)->PdfConversion:
        value=self._exchange(ConvertRequest(original,name,page_range))
        if not isinstance(value,PdfConversion):
            self.close()
            raise PdfWorkerError('native PDF child returned an enrichment for conversion')
        return value

    def enrich(self,request:PdfEnrichmentRequest)->PdfEnrichmentResult:
        value=self._exchange(request)
        if not isinstance(value,PdfEnrichmentResult):
            self.close()
            raise PdfWorkerError('native PDF child returned a conversion for enrichment')
        return value

    def _stop(self,*,graceful:bool)->None:
        self._closed=True
        process=self._process
        connection=self._connection
        if graceful and connection is not None and process is not None and process.is_alive():
            try:
                connection.send(None)
            except (BrokenPipeError,EOFError,OSError):
                pass
        if connection is not None:
            connection.close()
            self._connection=None
        if process is None:
            return
        if process.pid is not None:
            if graceful:
                process.join(timeout=2)
            if process.is_alive():
                process.terminate()
                process.join(timeout=2)
            if process.is_alive():
                process.kill()
                process.join(timeout=5)
            if process.is_alive():
                raise PdfWorkerError(f'native PDF child {process.pid} did not exit after terminate/kill')
        process.close()
        self._process=None

    def close(self)->None:
        with self._lock:
            self._stop(graceful=True)
