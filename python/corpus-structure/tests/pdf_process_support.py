"""CPU lifecycle children for real process controls; never model/provider qualification."""

import os
import signal
import time
from multiprocessing.connection import Connection
from pathlib import Path

from corpus_structure.ingest.pdf import PdfConversion, PdfRecipe
from corpus_structure.ingest.pdf_assets import PreparedPdfAssets
from corpus_structure.ingest.pdf_hierarchy import NativeSnapshot
from corpus_structure.ingest.pdf_worker import ConvertRequest, NativeReply, PdfWorker


def _blocked_child(connection: Connection, recipe: PdfRecipe, assets: PreparedPdfAssets | None):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    request = connection.recv()
    assert isinstance(request, ConvertRequest)
    Path(request.original.decode()).write_text(str(os.getpid()))
    while True:
        time.sleep(60)


class BlockingOwner(PdfWorker):
    _child_target = staticmethod(_blocked_child)


def _partial_child(connection: Connection, recipe: PdfRecipe, assets: PreparedPdfAssets | None):
    connection.recv()
    connection.send(
        NativeReply(
            value=PdfConversion(
                "a" * 64,
                b"{}",
                NativeSnapshot(b"{}", "b" * 64, "fixture"),
                "partial_success",
                ("explicit lifecycle control",),
                (),
                (),
                None,
            )
        )
    )
    while True:
        time.sleep(60)


class PartialOwner(PdfWorker):
    _child_target = staticmethod(_partial_child)
