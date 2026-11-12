"""Operation-owned shared CUDA host transport, admission and proven cleanup."""

from __future__ import annotations

import json
import os
import select
import signal
import subprocess
import time
from concurrent.futures import CancelledError, Future, TimeoutError
from contextlib import ExitStack, suppress
from dataclasses import dataclass
from queue import Queue
from threading import BoundedSemaphore, Event, Lock, Thread, current_thread
from uuid import uuid4

from corpus_structure.ingest.pdf_capacity import suspend_resident_nemotron

from .native_profiles import NativeSelection
from .pm2_worker import Pm2WorkerError, Pm2WorkerRefused, _finite_float, _json_object, _live_group


def encode_host_frame(message, limit):
    """Encode actual ordered UTF-8 JSONL, including complete multiplex framing."""
    frame = bytearray()
    try:
        for part in json.JSONEncoder(
            ensure_ascii=False, allow_nan=False, separators=(",", ":")
        ).iterencode(message):
            encoded = part.encode()
            if len(frame) + len(encoded) >= limit:
                raise Pm2WorkerRefused("native request exceeds its frame byte bound")
            frame.extend(encoded)
    except (TypeError, ValueError, RecursionError) as error:
        if isinstance(error, Pm2WorkerRefused):
            raise
        raise Pm2WorkerRefused("native host frame is not valid JSON") from error
    frame.append(10)
    return frame


def inference_frame(generation, request_id, selection, payload):
    return dict(
        kind="infer",
        generation=generation,
        request_id=request_id,
        provider=selection.provider,
        profile=selection.native.fingerprint,
        payload=payload,
    )


def host_request_frame_size(selection, payload, limit):
    # Generation/request IDs have fixed-width ASCII representations; admission uses
    # the exact encoder and full header before any transport buffer is allocated.
    return len(encode_host_frame(inference_frame("0" * 32, "0" * 32, selection, payload), limit))


@dataclass
class _Pending:
    selection: NativeSelection
    future: Future
    permit: BoundedSemaphore


class NativeHost:
    """One supervised process, shared by a frozen declared resident population."""

    def __init__(
        self, selections, policy, *, check_active, startup_timeout=300.0, command=None, adopt=None
    ):
        self.generation = uuid4().hex
        self.policy, self.selections = policy, tuple(selections)
        self._lock, self._write_lock, self._close_lock = Lock(), Lock(), Lock()
        self._pending = {}
        self._permits = {s.provider: BoundedSemaphore(policy.max_provider_jobs) for s in selections}
        self._accepting = True
        self._failure = None
        self._ready = Future()
        self.startup = {}
        self._process = None
        self._reader = None
        if adopt is not None:
            adopt(self)
        first = self.selections[0]
        caches = {
            str(s.assets.absolute() / "hub")
            for s in self.selections
            if s.provider in {"d1", "hanlp", "maverick", "dipo"}
        }
        if len(caches) > 1:
            raise Pm2WorkerRefused("shared host residents require one offline backbone cache")
        environment = dict(
            PATH=os.defpath,
            HF_HUB_OFFLINE="1",
            TRANSFORMERS_OFFLINE="1",
            TOKENIZERS_PARALLELISM="false",
            OMP_NUM_THREADS=str(first.native.threads),
            MKL_NUM_THREADS=str(first.native.threads),
        )
        if caches:
            environment["HF_HUB_CACHE"] = next(iter(caches))
        self._process = subprocess.Popen(
            command or [str(first.python.absolute()), "-I", "-u", str(first.script.absolute())],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            env=environment,
            start_new_session=True,
            bufsize=0,
        )
        self._reader = Thread(
            target=self._read, name="nlp-host-reader-" + self.generation[:8], daemon=True
        )
        self._reader.start()
        try:
            self._write(
                dict(
                    kind="initialize",
                    generation=self.generation,
                    residents=[s.declaration() for s in self.selections],
                    max_jobs=policy.max_provider_jobs,
                    max_request_bytes=policy.max_native_request_bytes,
                    max_reply_bytes=policy.max_native_reply_bytes,
                ),
                time.monotonic() + startup_timeout,
                limit=max(policy.max_native_request_bytes, 1024 * 1024),
            )
            deadline = time.monotonic() + startup_timeout
            while True:
                check_active()
                try:
                    metadata = self._ready.result(
                        timeout=min(0.1, max(0.001, deadline - time.monotonic()))
                    )
                    break
                except TimeoutError:
                    if time.monotonic() >= deadline:
                        raise Pm2WorkerError("native host startup timed out") from None
            expected = {s.native.fingerprint: s for s in self.selections}
            if not isinstance(metadata, dict) or set(metadata) != set(expected):
                raise Pm2WorkerError("native host changed its declared resident population")
            for identity, observation in metadata.items():
                self._validate_startup(expected[identity], observation)
            self.startup = metadata
        except BaseException as error:
            try:
                self.close(grace_seconds=0)
            except BaseException as cleanup:
                error.add_note(f"native host startup cleanup remains unproven: {cleanup}")
            raise

    @staticmethod
    def _validate_startup(selection, observation):
        profile = selection.native
        if (
            not isinstance(observation, dict)
            or observation.get("provider") != profile.provider
            or observation.get("profile") != profile.fingerprint
            or observation.get("runtime_identity") != profile.runtime_identity
            or observation.get("assets") != profile.artifacts
            or str(observation.get("device", "")).split(":")[0] != profile.device
            or observation.get("dtype") != "torch." + profile.dtype
            or observation.get("backend") != profile.backend
            or observation.get("matmul_precision") != profile.matmul_precision
            or observation.get("cudnn_allow_tf32") is not profile.cudnn_allow_tf32
            or observation.get("native_threads", {}).get("intra_op") != profile.threads
            or observation.get("native_threads", {}).get("inter_op") != profile.interop_threads
        ):
            raise Pm2WorkerError("native host executed a different frozen provider profile")

    @property
    def closed(self):
        return not self._accepting

    def _leader_exited(self):
        process = self._process
        return process is None or (
            process.returncode is not None
            or os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None
        )

    def _write(self, message, deadline, *, limit=None):
        frame = encode_host_frame(message, limit or self.policy.max_native_request_bytes)
        return self._write_frame(frame, deadline)

    def _write_frame(self, frame, deadline):
        with self._write_lock:
            process = self._process
            if process is None:
                raise Pm2WorkerError("native host has not started")
            stream = process.stdin
            if stream is None or stream.closed:
                raise Pm2WorkerError("native host input is closed")
            os.set_blocking(stream.fileno(), False)
            offset = 0
            while offset < len(frame):
                if time.monotonic() >= deadline:
                    raise Pm2WorkerError("native host write timed out")
                if self._leader_exited():
                    raise Pm2WorkerError("native host exited during request write")
                if select.select([], [stream], [], 0.1)[1]:
                    with suppress(BlockingIOError):
                        offset += os.write(
                            stream.fileno(), memoryview(frame)[offset : offset + 65536]
                        )

    def _fail(self, error):
        with self._lock:
            self._accepting = False
            self._failure = self._failure or error
            pending, self._pending = self._pending, {}
            if not self._ready.done():
                self._ready.set_exception(error)
        for request in pending.values():
            request.permit.release()
            if not request.future.done():
                request.future.set_exception(error)

    def _read(self):
        process = self._process
        if process is None:
            self._fail(Pm2WorkerError("native host reader has no owned process"))
            return
        stream = process.stdout
        assert stream is not None
        buffer = bytearray()
        try:
            while True:
                if not select.select([stream], [], [], 0.1)[0]:
                    if self._leader_exited():
                        raise Pm2WorkerError("native host exited without a complete reply")
                    continue
                chunk = os.read(stream.fileno(), 65536)
                if not chunk:
                    raise Pm2WorkerError("native host reply stream closed")
                buffer.extend(chunk)
                while b"\n" in buffer:
                    line, _, rest = buffer.partition(b"\n")
                    buffer = bytearray(rest)
                    if len(line) + 1 > self.policy.max_native_reply_bytes:
                        raise Pm2WorkerError("native host reply exceeds frame byte bound")
                    message = json.loads(
                        line, object_pairs_hook=_json_object, parse_float=_finite_float
                    )
                    self._route(message)
                if len(buffer) >= self.policy.max_native_reply_bytes:
                    raise Pm2WorkerError("native host reply exceeds frame byte bound")
        except BaseException as error:
            self._fail(error)

    def _route(self, message):
        if not isinstance(message, dict) or message.get("generation") != self.generation:
            raise Pm2WorkerError("native reply belongs to a different host generation")
        if message.get("kind") == "ready":
            if self._ready.done() or "request_id" in message:
                raise Pm2WorkerError("native host sent a duplicate/invalid startup")
            self._ready.set_result(message.get("residents"))
            return
        if message.get("kind") == "fatal":
            raise Pm2WorkerError(str(message.get("message", "native host failed"))[:1800])
        request_id = message.get("request_id")
        with self._lock:
            pending = self._pending.get(request_id)
            if pending is None:
                raise Pm2WorkerError("native reply has an unknown or duplicate request identity")
            if (
                message.get("provider") != pending.selection.provider
                or message.get("profile") != pending.selection.native.fingerprint
            ):
                raise Pm2WorkerError("native reply differs from its admitted provider/profile")
            if message.get("kind") not in {"result", "refused", "cancelled"}:
                raise Pm2WorkerError("native host returned an unsupported response")
            del self._pending[request_id]
        pending.permit.release()
        if message["kind"] == "result":
            if not isinstance(message.get("payload"), dict):
                pending.future.set_exception(Pm2WorkerError("native result is not an object"))
                raise Pm2WorkerError("native result is not an object")
            pending.future.set_result(message["payload"])
        else:
            kind = CancelledError if message["kind"] == "cancelled" else Pm2WorkerRefused
            pending.future.set_exception(kind(str(message.get("message", message["kind"]))[:1800]))

    def infer(self, selection, payload, *, check_active, timeout=120.0):
        check_active()
        permit = self._permits[selection.provider]
        if not permit.acquire(blocking=False):
            raise Pm2WorkerRefused("native host provider submission exceeds admitted job count")
        future, request_id = Future(), uuid4().hex
        try:
            frame = encode_host_frame(
                inference_frame(self.generation, request_id, selection, payload),
                self.policy.max_native_request_bytes,
            )
        except BaseException:
            permit.release()
            raise
        with self._lock:
            if not self._accepting:
                permit.release()
                raise Pm2WorkerError("native host generation is fenced") from self._failure
            self._pending[request_id] = _Pending(selection, future, permit)
        deadline = time.monotonic() + timeout
        cancelled = None
        try:
            self._write_frame(frame, deadline)
            while True:
                try:
                    check_active()
                except BaseException as error:
                    if cancelled is None:
                        cancelled = error
                        self._write(
                            dict(kind="cancel", generation=self.generation, request_id=request_id),
                            deadline,
                        )
                try:
                    reply = future.result(timeout=0.1)
                    if cancelled is not None:
                        raise cancelled
                    return reply
                except TimeoutError:
                    if time.monotonic() >= deadline:
                        raise Pm2WorkerError("native host inference timed out") from None
        except CancelledError, Pm2WorkerRefused:
            raise
        except BaseException as error:
            # Cancellation still waits for its physical reply; it never kills a
            # useful sibling. Genuine transport/deadline failure fences this host.
            if error is not cancelled:
                self._fail(error)
                self.close(grace_seconds=0)
            raise

    def close(self, *, grace_seconds=5.0):
        with self._close_lock:
            self._accepting = False
            process = self._process
            if process is None:
                return
            if not self._leader_exited() and grace_seconds:
                with suppress(Exception):
                    self._write(
                        dict(kind="shutdown", generation=self.generation), time.monotonic() + 0.5
                    )
                deadline = time.monotonic() + grace_seconds
                while not self._leader_exited() and time.monotonic() < deadline:
                    time.sleep(0.025)
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGTERM)
            deadline = time.monotonic() + 2
            while _live_group(process.pid) and time.monotonic() < deadline:
                time.sleep(0.025)
            if _live_group(process.pid):
                with suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
                deadline = time.monotonic() + 2
                while _live_group(process.pid) and time.monotonic() < deadline:
                    time.sleep(0.025)
            if _live_group(process.pid):
                raise Pm2WorkerError("native host process-group death remains unproven")
            process.wait(timeout=1)
            self._fail(Pm2WorkerError("native host generation closed"))
            if (
                self._reader is not None
                and self._reader.ident is not None
                and current_thread() is not self._reader
            ):
                self._reader.join(timeout=1)
                if self._reader.is_alive():
                    raise Pm2WorkerError("native host reader did not drain")
            for stream in (process.stdin, process.stdout):
                if stream is not None:
                    stream.close()


class NativeHostGroup:
    """One explicit operation lease; all owned hosts die before custody is restored."""

    def __init__(self, policy, endpoint=None, *, host_factory=NativeHost):
        self.policy, self.endpoint, self.host_factory = policy, endpoint, host_factory
        self._selections = {}
        self._hosts = {}
        self._lock = Lock()
        self._stop = Event()
        self._ready = None
        self._thread = None
        self._commands = Queue(maxsize=1)
        self._serving = False
        self._closed = False
        self._close_error = None

    def declare(self, selections):
        with self._lock:
            self._active()
            proposed = dict(self._selections)
            for selection in selections:
                key = selection.native.fingerprint
                existing = proposed.get(key)
                if existing is not None:
                    if existing.identity != selection.identity:
                        raise Pm2WorkerRefused(
                            "native profile has conflicting acquisition locations"
                        )
                    continue
                if self._serving:
                    raise Pm2WorkerRefused(
                        "new native profile was not declared before host serving"
                    )
                if (selection.native.threads, selection.native.interop_threads) != (
                    self.policy.provider_threads,
                    self.policy.provider_interop_threads,
                ):
                    raise Pm2WorkerRefused(
                        "native frozen profile differs from shared host thread policy"
                    )
                proposed[key] = selection
            caches = {}
            for selection in proposed.values():
                if selection.provider in {"d1", "hanlp", "maverick", "dipo"}:
                    caches.setdefault(selection.native.host, set()).add(
                        str(selection.assets.absolute() / "hub")
                    )
            if any(len(population) > 1 for population in caches.values()):
                raise Pm2WorkerRefused("shared host residents require one offline backbone cache")
            self._selections = proposed

    def _active(self):
        if self._stop.is_set():
            raise CancelledError("native host group admission is closed")

    def ensure(self, check_active):
        with self._lock:
            self._active()
            if self._ready is None:
                if not self._selections:
                    raise Pm2WorkerRefused("native host group has no declared residents")
                self._serving = True
                self._ready = Future()
                self._thread = Thread(target=self._manage, name="native-gpu-custody", daemon=True)
                self._thread.start()
            ready = self._ready
        while True:
            check_active()
            try:
                ready.result(timeout=0.1)
                return
            except TimeoutError:
                pass

    def _manage(self):
        ready = self._ready
        assert ready is not None
        stack = ExitStack()
        try:
            stack.enter_context(suspend_resident_nemotron(self.endpoint, check_active=self._active))
            groups = {}
            for selection in self._selections.values():
                groups.setdefault(selection.native.host, []).append(selection)
            for name, population in groups.items():
                self._active()
                self.host_factory(
                    population,
                    self.policy,
                    check_active=self._active,
                    adopt=lambda host, name=name: self._hosts.__setitem__(name, host),
                )
        except BaseException as error:
            ready.set_exception(error)
        else:
            ready.set_result(None)
        while True:
            closed = self._commands.get()
            failures = []
            for host in self._hosts.values():
                try:
                    host.close()
                except BaseException as error:
                    failures.append(error)
            if failures:
                # Keep the manager and its lease alive. A signal/cancelled future
                # is not proof that every host released its native resources.
                failure = Pm2WorkerError("native host group teardown remains unproven")
                for error in failures:
                    failure.add_note(str(error))
                closed.set_exception(failure)
                continue
            try:
                stack.close()
            except BaseException as error:
                self._close_error = error
                closed.set_exception(error)
            else:
                closed.set_result(None)
            self._closed = True
            return

    def startup(self, selection, check_active):
        self.declare((selection,))
        self.ensure(check_active)
        return self._hosts[selection.native.host].startup[selection.native.fingerprint]

    def infer(self, selection, payload, check_active, *, timeout=120.0):
        self.startup(selection, check_active)
        return self._hosts[selection.native.host].infer(
            selection, payload, check_active=check_active, timeout=timeout
        )

    def close(self):
        self._stop.set()
        if self._closed:
            if self._close_error is not None:
                raise self._close_error
            return
        if self._thread is None:
            self._closed = True
            return
        closed = Future()
        self._commands.put(closed, timeout=1)
        closed.result(timeout=330)
        self._thread.join(timeout=1)
        if self._thread.is_alive():
            raise Pm2WorkerError("native GPU custody owner did not drain")

    def __enter__(self):
        return self

    def __exit__(self, *error):
        self.close()
