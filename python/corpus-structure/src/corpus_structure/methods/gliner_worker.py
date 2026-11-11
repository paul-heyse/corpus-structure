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
from dataclasses import asdict, dataclass
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from multiprocessing.reduction import ForkingPickler
from threading import Event, Lock, Thread
from typing import TYPE_CHECKING

from .gliner import (
    BOUNDARY_DIAGNOSTIC,
    MAX_DIAGNOSTIC_SPANS,
    GlinerInput,
    GlinerPack,
    GlinerProfile,
    GlinerRefused,
    GlinerReport,
    _digest,
    _json,
    boundary_diagnostic,
    effective_profile_fingerprint,
    load_model,
    prepare_input,
)

if TYPE_CHECKING:
    from .pm2_source import PM2SourceMap


class GlinerWorkerError(RuntimeError):
    """Failed native operation, never an empty successful report."""


@dataclass(frozen=True)
class _Diagnostic:
    source_map_digest: str
    supplied: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class _Request:
    serial: int
    pack: GlinerPack
    inputs: tuple[GlinerInput, ...]
    threshold: float
    overlap_policy: str
    evaluation: bool
    diagnostic: _Diagnostic | None = None


@dataclass(frozen=True)
class _Reply:
    serial: int
    reports: tuple[GlinerReport, ...] | None = None
    error: str | None = None
    error_kind: str | None = None


def _send_reply(connection: Connection, reply: _Reply, profile: GlinerProfile) -> None:
    # Bound the entire finite pickle frame, including preparation and provenance.
    frame = bytes(ForkingPickler.dumps(reply))
    if len(frame) > profile.max_reply_frame_bytes:
        raise GlinerRefused("native reply frame byte bound exceeded")
    connection.send_bytes(frame)


def _native_child(connection: Connection, profile: GlinerProfile) -> None:
    from .model_observation import installed_policy, observation_digest, request_digest

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
            loading = False
            try:
                schema = request.pack.compile()
                reused = model is not None
                if model is None:
                    loading = True
                    model, effective = load_model(profile)
                    loading = False
                preparations = tuple(
                    prepare_input(model, schema, item, profile) for item in request.inputs
                )
                started = time.monotonic()
                if request.diagnostic is not None:
                    (item,) = request.inputs
                    (prepared,) = preparations
                    diagnostic = request.diagnostic
                    raw = boundary_diagnostic(model, schema, item, prepared, diagnostic.supplied)
                    report = GlinerReport(
                        item.context_id,
                        item.context_digest,
                        _digest(
                            {
                                "operation": BOUNDARY_DIAGNOSTIC,
                                "context": item.context_digest,
                                "text": item.text,
                                "source_map": diagnostic.source_map_digest,
                                "profile": profile.fingerprint,
                                "effective_profile": effective_profile_fingerprint(effective),
                                "pack": request.pack.fingerprint,
                                "supplied": diagnostic.supplied,
                            }
                        ),
                        profile.fingerprint,
                        request.pack.fingerprint,
                        prepared,
                        _json({**raw, "source_map_digest": diagnostic.source_map_digest}),
                        effective,
                        time.monotonic() - started,
                        reused,
                        diagnostics=(("proposal_pool", "native_diagnostic"),),
                    )
                    _send_reply(connection, _Reply(request.serial, reports=(report,)), profile)
                    continue
                inference = installed_policy()[0]["inference"]
                settings = {key: value for key, value in inference.items() if key != "operation"}
                request_key = (
                    request_digest(
                        request.pack,
                        asdict(profile),
                        request.inputs,
                        request.threshold,
                        request.overlap_policy,
                        request.evaluation,
                        inference,
                    )
                    if any(item.operation for item in request.inputs)
                    else None
                )
                raw = model.batch_extract(
                    [item.text for item in request.inputs],
                    schema,
                    batch_size=len(request.inputs),
                    threshold=request.threshold,
                    overlap_policy=request.overlap_policy,
                    **settings,
                )
                elapsed = time.monotonic() - started
                if len(raw) != len(request.inputs):
                    raise GlinerWorkerError("native output count differs from admitted contexts")
                reports = tuple(
                    GlinerReport(
                        item.context_id,
                        item.context_digest,
                        request_key
                        or _digest(
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
                        request_digest=request_key,
                        observation_digest=(
                            observation_digest(request_key, _json(result), effective)
                            if request_key
                            else None
                        ),
                    )
                    for item, prepared, result in zip(
                        request.inputs, preparations, raw, strict=True
                    )
                )
                _send_reply(connection, _Reply(request.serial, reports=reports), profile)
            except Exception as error:
                _send_reply(
                    connection,
                    _Reply(
                        request.serial,
                        error=f"{type(error).__name__}: {str(error)[:1800]}",
                        error_kind="request_refused"
                        if isinstance(error, GlinerRefused) and not loading
                        else "worker_error",
                    ),
                    profile,
                )
                if not isinstance(error, GlinerRefused) or loading:
                    # True failure retires residency; task owners control retry.
                    return
    finally:
        connection.close()


class GlinerWorker:
    """Single compatible profile, bounded live batch, persistent lazy native model.

    A supervised I/O thread allows cancellation while a pipe send/receive is blocked.
    Teardown kills and joins the child, then joins I/O before propagating the cause.
    Worker/IPC failure permanently closes this owner; request refusal preserves it.
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
        evaluation: bool = False,
        check_active: Callable[[], None] | None = None,
    ) -> tuple[GlinerReport, ...]:
        return self._exchange(
            pack,
            inputs,
            threshold=threshold,
            overlap_policy=overlap_policy,
            evaluation=evaluation,
            check_active=check_active,
        )

    def diagnose(
        self,
        pack: GlinerPack,
        mapping: PM2SourceMap,
        supplied: tuple[tuple[int, int], ...] = (),
        *,
        check_active: Callable[[], None] | None = None,
    ) -> GlinerReport:
        """Observe the ordinary pool and optional source-authorized spans without decoding."""
        from corpus_structure.semantic.source_contexts import ContextRefused

        from .pm2_source import ProviderSpan

        context = mapping.context
        if mapping.provider_text != context.text:
            raise GlinerRefused("GLiNER diagnosis requires the exact selected source text")
        if not isinstance(supplied, tuple) or len(supplied) > MAX_DIAGNOSTIC_SPANS:
            raise GlinerRefused("diagnostic supplied span population exceeds its bound")
        try:
            context.require_native_projection()
            for start, end in supplied:
                if type(start) is not int or type(end) is not int:
                    raise GlinerRefused("supplied spans require integer half-open coordinates")
                mapping.map_extents(
                    (ProviderSpan(start, end, context.text[start:end]),),
                    scope_digest=mapping.scope_digest,
                )
        except ContextRefused as error:
            raise GlinerRefused(str(error)) from error
        (report,) = self._exchange(
            pack,
            (GlinerInput.from_context(context),),
            threshold=0.5,
            overlap_policy="flat",
            evaluation=True,
            check_active=check_active,
            diagnostic=_Diagnostic(mapping.input_digest, supplied),
        )
        return report

    def _exchange(
        self,
        pack: GlinerPack,
        inputs: tuple[GlinerInput, ...],
        *,
        threshold: float,
        overlap_policy: str,
        evaluation: bool,
        check_active: Callable[[], None] | None,
        diagnostic: _Diagnostic | None = None,
    ) -> tuple[GlinerReport, ...]:
        if not isinstance(inputs, tuple) or not inputs or len(inputs) > self.profile.max_batch:
            raise GlinerRefused("batch must be a nonempty bounded immutable tuple")
        # Decoding policy belongs to the requesting operation. Private language
        # characterization needs overlapping cues without claiming evaluation custody.
        supported_overlap = {"flat", "nested", "allow"}
        if not 0 <= threshold <= 1 or overlap_policy not in supported_overlap:
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
            request = _Request(
                self._serial, pack, inputs, threshold, overlap_policy, evaluation, diagnostic
            )
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
                if reply.error_kind == "request_refused":
                    raise GlinerRefused(reply.error)
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
        except GlinerRefused:
            # A validated request refusal leaves the child and its immutable model
            # healthy. True worker/IPC/cancellation faults still retire it below.
            raise
        except BaseException as original:
            original.add_note(
                f"GLiNER operation={BOUNDARY_DIAGNOSTIC if diagnostic else 'batch_extract'} "
                f"profile={self.profile.fingerprint} "
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
