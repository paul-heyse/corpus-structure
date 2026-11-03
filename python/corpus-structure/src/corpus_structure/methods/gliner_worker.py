"""One run-owned, serial GLiNER CPU child with bounded cancellable IPC.

Admission is fail-fast: one live batch, zero queued batches. Callers own retries and
backpressure. No lease callbacks, source objects, databases or model handles cross IPC.
"""

from __future__ import annotations

import multiprocessing
import os
import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from multiprocessing.reduction import ForkingPickler
from threading import Event, Lock, Thread

from .gliner import (
    GlinerInput,
    GlinerPack,
    GlinerProfile,
    GlinerRefused,
    GlinerReport,
    _digest,
    _json,
    effective_profile_fingerprint,
    load_model,
    prepare_input,
)


class GlinerWorkerError(RuntimeError):
    """Failed native operation, never an empty successful report."""


@dataclass(frozen=True)
class _Request:
    serial: int
    pack: GlinerPack
    inputs: tuple[GlinerInput, ...]
    threshold: float
    overlap_policy: str


@dataclass(frozen=True)
class _Reply:
    serial: int
    reports: tuple[GlinerReport, ...] | None = None
    error: str | None = None


def _send_reply(connection: Connection, reply: _Reply, profile: GlinerProfile) -> None:
    # Bound the entire finite pickle frame, including preparation and provenance.
    frame = bytes(ForkingPickler.dumps(reply))
    if len(frame) > profile.max_reply_frame_bytes:
        raise GlinerRefused("native reply frame byte bound exceeded")
    connection.send_bytes(frame)


def _native_child(connection: Connection, profile: GlinerProfile) -> None:
    os.dup2(2, 1)
    # Defense in depth only: detached inputs and absence of DB/provider imports are
    # the application boundary. This is not an OS sandbox or secret-isolation claim.
    for name in tuple(os.environ):
        if name.startswith(
            (
                "CORPUS_DATABASE",
                "OPENAI_",
                "ANTHROPIC_",
                "GOOGLE_",
                "AZURE_",
                "AWS_",
                "HF_TOKEN",
                "HUGGING_FACE_HUB_TOKEN",
            )
        ) or any(part in name.upper() for part in ("EVALUATOR", "API_KEY", "SECRET")):
            os.environ.pop(name, None)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["OMP_NUM_THREADS"] = str(profile.threads)
    os.environ["MKL_NUM_THREADS"] = str(profile.threads)
    model = None
    effective = ""
    try:
        while True:
            request = ForkingPickler.loads(
                connection.recv_bytes(maxlength=profile.max_request_frame_bytes)
            )
            if request is None:
                return
            if not isinstance(request, _Request):
                raise GlinerWorkerError("unsupported detached native request")
            try:
                schema = request.pack.compile()
                reused = model is not None
                if model is None:
                    model, effective = load_model(profile)
                preparations = tuple(
                    prepare_input(model, schema, item, profile) for item in request.inputs
                )
                started = time.monotonic()
                raw = model.batch_extract(
                    [item.text for item in request.inputs],
                    schema,
                    batch_size=len(request.inputs),
                    num_workers=0,
                    threshold=request.threshold,
                    overlap_policy=request.overlap_policy,
                    include_spans=True,
                    include_confidence=True,
                    max_len=None,
                )
                elapsed = time.monotonic() - started
                if len(raw) != len(request.inputs):
                    raise GlinerWorkerError("native output count differs from admitted contexts")
                reports = tuple(
                    GlinerReport(
                        item.context_id,
                        item.context_digest,
                        _digest(
                            {
                                "profile": profile.fingerprint,
                                "effective_profile": effective_profile_fingerprint(effective),
                                "pack": request.pack.fingerprint,
                                "context": item.context_digest,
                                "text": item.text,
                                "threshold": request.threshold,
                                "overlap_policy": request.overlap_policy,
                                "batch": [
                                    {
                                        "id": entry.context_id,
                                        "digest": entry.context_digest,
                                        "text": entry.text,
                                    }
                                    for entry in request.inputs
                                ],
                                "operation": "batch_extract",
                            }
                        ),
                        profile.fingerprint,
                        request.pack.fingerprint,
                        prepared,
                        _json(result),
                        effective,
                        elapsed,
                        reused,
                    )
                    for item, prepared, result in zip(
                        request.inputs, preparations, raw, strict=True
                    )
                )
                _send_reply(connection, _Reply(request.serial, reports=reports), profile)
            except Exception as error:
                _send_reply(
                    connection,
                    _Reply(request.serial, error=f"{type(error).__name__}: {str(error)[:1800]}"),
                    profile,
                )
                # Failure retires residency. Retry remains with the caller's task owner.
                return
    finally:
        connection.close()


class GlinerWorker:
    """Single compatible profile, bounded live batch, persistent lazy native model.

    A supervised I/O thread allows cancellation while a pipe send/receive is blocked.
    Teardown kills and joins the child, then joins I/O before propagating the cause.
    Failure permanently closes this owner; there is no stale completion or implicit retry.
    """

    _child_target = staticmethod(_native_child)

    def __init__(self, profile: GlinerProfile) -> None:
        self.profile = profile
        self._process: BaseProcess | None = None
        self._connection: Connection | None = None
        self._lock = Lock()
        self._closed = False
        self._serial = 0

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def pid(self) -> int | None:
        return self._process.pid if self._process is not None else None

    def _start(self) -> None:
        if self._closed:
            raise GlinerWorkerError("native GLiNER owner is closed")
        if self._process is not None:
            return
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe(duplex=True)
        process = context.Process(
            target=self._child_target,
            args=(child, self.profile),
            name="native-gliner-cpu",
            daemon=True,
        )
        self._connection, self._process = parent, process
        try:
            process.start()
        finally:
            child.close()

    def extract(
        self,
        pack: GlinerPack,
        inputs: tuple[GlinerInput, ...],
        *,
        threshold: float = 0.5,
        overlap_policy: str = "flat",
        check_active: Callable[[], None] | None = None,
    ) -> tuple[GlinerReport, ...]:
        if not isinstance(inputs, tuple) or not inputs or len(inputs) > self.profile.max_batch:
            raise GlinerRefused("batch must be a nonempty bounded immutable tuple")
        if not 0 <= threshold <= 1 or overlap_policy != "flat":
            raise GlinerRefused("unsupported threshold or overlap policy")
        sizes = [len(item.text.encode()) for item in inputs]
        if max(sizes) > self.profile.max_input_bytes or sum(sizes) > self.profile.max_batch_bytes:
            raise GlinerRefused("live input byte bound exceeded")
        if len(pack.declaration_json.encode()) > self.profile.max_schema_bytes:
            raise GlinerRefused("schema byte bound exceeded")
        metadata = [
            pack.release,
            pack.version,
            overlap_policy,
            *(value for item in inputs for value in (item.context_id, item.context_digest)),
        ]
        if sum(len(value.encode()) for value in metadata) > self.profile.max_metadata_bytes:
            raise GlinerRefused("request metadata byte bound exceeded")
        if len({item.context_id for item in inputs}) != len(inputs):
            raise GlinerRefused("batch context identities must be distinct")
        if not self._lock.acquire(blocking=False):
            raise GlinerRefused("native GLiNER admission saturated: one live batch, zero queued")
        io: Thread | None = None
        done = Event()
        received: list[object] = []
        deadline = time.monotonic() + self.profile.timeout_seconds
        try:
            if check_active is not None:
                check_active()
            self._serial += 1
            request = _Request(self._serial, pack, inputs, threshold, overlap_policy)
            frame = bytes(ForkingPickler.dumps(request))
            if len(frame) > self.profile.max_request_frame_bytes:
                raise GlinerRefused("request frame byte bound exceeded")
            self._start()
            connection, process = self._connection, self._process
            if connection is None or process is None:
                raise GlinerWorkerError("native child has no connected owner")

            def exchange() -> None:
                try:
                    connection.send_bytes(frame)
                    reply_frame = connection.recv_bytes(
                        maxlength=self.profile.max_reply_frame_bytes
                    )
                    received.append(ForkingPickler.loads(reply_frame))
                except BaseException as error:
                    received.append(error)
                finally:
                    done.set()

            io = Thread(target=exchange, name="gliner-ipc", daemon=True)
            io.start()
            while not done.wait(0.1):
                if check_active is not None:
                    check_active()
                if time.monotonic() >= deadline:
                    raise GlinerWorkerError("native GLiNER operation timed out")
                if not process.is_alive():
                    # A final pipe read may still be settling; wait remains bounded.
                    done.wait(0.1)
                    if not done.is_set():
                        raise GlinerWorkerError(f"native child exited with code {process.exitcode}")
            if check_active is not None:
                check_active()
            if time.monotonic() >= deadline:
                raise GlinerWorkerError("native GLiNER operation timed out")
            reply = received[0]
            if isinstance(reply, BaseException):
                raise GlinerWorkerError(f"native IPC failed: {type(reply).__name__}") from reply
            if not isinstance(reply, _Reply) or reply.serial != request.serial:
                raise GlinerWorkerError("native reply has a stale or unsupported identity")
            if reply.error is not None:
                raise GlinerWorkerError(reply.error)
            if reply.reports is None or len(reply.reports) != len(inputs):
                raise GlinerWorkerError("native reply omitted context reports")
            for item, report in zip(inputs, reply.reports, strict=True):
                if (
                    report.context_id != item.context_id
                    or report.context_digest != item.context_digest
                    or report.profile != self.profile.fingerprint
                    or report.pack != pack.fingerprint
                ):
                    raise GlinerWorkerError("native report premises differ from admitted request")
            return reply.reports
        except BaseException as original:
            original.add_note(
                f"GLiNER operation=batch_extract profile={self.profile.fingerprint} "
                f"pack={pack.fingerprint} contexts=" + ",".join(item.context_id for item in inputs)
            )
            try:
                self._stop(graceful=False)
            except BaseException as cleanup:
                original.add_note(f"GLiNER teardown failed: {str(cleanup)[:1800]}")
                for note in getattr(cleanup, "__notes__", ()):
                    original.add_note(note)
            raise
        finally:
            if io is not None:
                io.join(timeout=2)
                if io.is_alive():
                    self._closed = True
                    self._lock.release()
                    raise GlinerWorkerError("native GLiNER IPC thread did not exit after teardown")
            self._lock.release()

    def _stop(self, *, graceful: bool) -> None:
        self._closed = True
        process, connection = self._process, self._connection
        errors: list[BaseException] = []
        try:
            if graceful and process is not None and process.is_alive() and connection is not None:
                with suppress(BrokenPipeError, EOFError, OSError):
                    connection.send(None)
            if process is not None:
                if process.pid is not None:
                    if graceful:
                        process.join(timeout=1)
                    for stop in (process.terminate, process.kill):
                        if not process.is_alive():
                            break
                        try:
                            stop()
                        except BaseException as error:
                            errors.append(error)
                        try:
                            process.join(timeout=2)
                        except BaseException as error:
                            errors.append(error)
                    if process.is_alive():
                        errors.append(
                            GlinerWorkerError(
                                "native GLiNER child did not exit after terminate/kill"
                            )
                        )
                    else:
                        process.join(timeout=0)
                        process.close()
                        self._process = None
                else:
                    process.close()
                    self._process = None
        finally:
            # IPC is independently owned even when native-process teardown fails.
            if connection is not None:
                try:
                    connection.close()
                    self._connection = None
                except BaseException as error:
                    errors.append(error)
        if errors:
            failure = GlinerWorkerError("native GLiNER teardown failed")
            for error in errors:
                failure.add_note(f"{type(error).__name__}: {str(error)[:1800]}")
            raise failure from errors[0]

    def close(self) -> None:
        # An in-flight caller owns cancellation; close never queues behind inference.
        if not self._lock.acquire(blocking=False):
            raise GlinerRefused("cancel the active operation before closing the worker")
        try:
            self._stop(graceful=True)
        finally:
            self._lock.release()
