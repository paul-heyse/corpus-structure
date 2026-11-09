"""Run-owned native model process with one live, cancellable JSONL exchange."""

from __future__ import annotations

import json
import math
import os
import select
import signal
import subprocess
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager, nullcontext, suppress
from contextvars import ContextVar
from pathlib import Path
from threading import Lock
from typing import Any, Literal

from corpus_structure.ingest.pdf_capacity import suspend_resident_nemotron

_POLL_SECONDS = 0.1
_CHUNK_BYTES = 64 * 1024
_owns_cuda: ContextVar[bool] = ContextVar("owns_pm2_cuda", default=False)


class Pm2WorkerRefused(ValueError):
    """The parent did not admit this request to native execution."""


class Pm2WorkerError(RuntimeError):
    """The native process or its protocol failed during an admitted operation."""


def _encode_request(request_id: int, payload: dict[str, Any], limit: int) -> bytearray:
    if not isinstance(payload, dict):
        raise Pm2WorkerRefused("native request payload must be an object")
    frame = bytearray()
    encoder = json.JSONEncoder(ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    try:
        request = {"kind": "infer", "request_id": request_id, "payload": payload}
        for part in encoder.iterencode(request):
            if len(frame) + len(part) >= limit:
                raise Pm2WorkerRefused("native request exceeds its frame byte bound")
            encoded = part.encode()
            if len(frame) + len(encoded) >= limit:
                raise Pm2WorkerRefused("native request exceeds its frame byte bound")
            frame.extend(encoded)
    except Pm2WorkerRefused:
        raise
    except (TypeError, ValueError, RecursionError) as error:
        raise Pm2WorkerRefused("native request is not a valid JSON object") from error
    frame.append(10)
    return frame


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("nonfinite JSON value")
    return number


def _await_pipe(poller: Any, deadline: float, check_active: Callable[[], None], phase: str) -> None:
    while True:
        check_active()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise Pm2WorkerError(f"native model {phase} timed out")
        try:
            events = poller.poll(math.ceil(1000 * min(remaining, _POLL_SECONDS)))
        except OSError as error:
            raise Pm2WorkerError(f"native IPC failed during {phase}") from error
        if events:
            return


def _live_group(group: int) -> bool:
    # Linux reports zombies as group members too. They have no device resources
    # and adopted descendants may remain zombies until their new parent reaps them.
    with os.scandir("/proc") as entries:
        for entry in entries:
            if not entry.name.isdecimal():
                continue
            try:
                stat = Path(entry.path, "stat").read_bytes().rpartition(b")")[2].split()
            except FileNotFoundError, ProcessLookupError, PermissionError:
                continue
            if int(stat[2]) == group and stat[0] not in {b"Z", b"X", b"x"}:
                return True
    return False


class Pm2Worker:
    """Resident child owned by ``open_pm2_worker``; one request, zero queued."""

    def __init__(
        self,
        process: subprocess.Popen[bytes],
        *,
        check_active: Callable[[], None],
        inference_timeout_seconds: float,
        max_request_bytes: int,
        max_reply_bytes: int,
    ) -> None:
        self._process = process
        self._check_active = check_active
        self._inference_timeout_seconds = inference_timeout_seconds
        self._max_request_bytes = max_request_bytes
        self._max_reply_bytes = max_reply_bytes
        self._lock = Lock()
        self._stop_lock = Lock()
        self._closed = False
        self._request_id = 0
        self.startup: dict[str, Any] = {}

    @property
    def pid(self) -> int:
        return self._process.pid

    def _read_frame(
        self, deadline: float, check_active: Callable[[], None], phase: str
    ) -> dict[str, Any]:
        stdout = self._process.stdout
        assert stdout is not None
        fd = stdout.fileno()
        poller = select.poll()
        poller.register(fd, select.POLLIN)
        frame = bytearray()
        while True:
            _await_pipe(poller, deadline, check_active, phase)
            try:
                chunk = os.read(fd, min(_CHUNK_BYTES, self._max_reply_bytes - len(frame)))
            except OSError as error:
                raise Pm2WorkerError(f"native IPC read failed during {phase}") from error
            if not chunk:
                raise Pm2WorkerError(f"native child exited during {phase} without a complete reply")
            frame.extend(chunk)
            if b"\n" in chunk:
                if chunk.find(b"\n") != len(chunk) - 1:
                    raise Pm2WorkerError(f"native child sent unsolicited data during {phase}")
                break
            if len(frame) == self._max_reply_bytes:
                raise Pm2WorkerError("native reply exceeds its frame byte bound")
        try:
            reply = json.loads(
                frame.decode(),
                object_pairs_hook=_json_object,
                parse_float=_finite_float,
                parse_constant=_finite_float,
            )
        except (ValueError, RecursionError) as error:
            raise Pm2WorkerError("native reply is not valid JSON") from error
        if not isinstance(reply, dict):
            raise Pm2WorkerError("native reply must be a JSON object")
        return reply

    def _write_frame(
        self, frame: bytearray, deadline: float, check_active: Callable[[], None]
    ) -> None:
        stdin = self._process.stdin
        assert stdin is not None
        fd = stdin.fileno()
        poller = select.poll()
        poller.register(fd, select.POLLOUT)
        with memoryview(frame) as data:
            sent = 0
            while sent < len(data):
                _await_pipe(poller, deadline, check_active, "inference")
                try:
                    sent += os.write(fd, data[sent : sent + _CHUNK_BYTES])
                except BlockingIOError:
                    continue
                except OSError as error:
                    raise Pm2WorkerError("native IPC write failed during inference") from error

    def _ready(self, timeout_seconds: float) -> None:
        deadline = time.monotonic() + timeout_seconds
        reply = self._read_frame(deadline, self._check_active, "startup")
        self._check_active()
        if time.monotonic() >= deadline:
            raise Pm2WorkerError("native model startup timed out")
        if reply.get("kind") == "error" and isinstance(reply.get("message"), str):
            raise Pm2WorkerError(f"native model startup failed: {reply['message'][:1800]}")
        payload = reply.get("payload", {})
        if reply.get("kind") != "ready" or "request_id" in reply or not isinstance(payload, dict):
            raise Pm2WorkerError("native model sent an unsupported startup reply")
        self.startup = payload

    def infer(
        self, payload: dict[str, Any], *, check_active: Callable[[], None] | None = None
    ) -> dict[str, Any]:
        if not self._lock.acquire(blocking=False):
            raise Pm2WorkerRefused("native admission saturated: one live request, zero queued")
        failure = None
        try:
            if self._closed:
                raise Pm2WorkerError("native child is closed")
            deadline = time.monotonic() + self._inference_timeout_seconds

            def active() -> None:
                if self._closed:
                    raise Pm2WorkerError("native child is closed")
                self._check_active()
                if check_active is not None and check_active is not self._check_active:
                    check_active()

            try:
                active()
            except BaseException as error:
                failure = error
                raise
            request_id = self._request_id + 1
            frame = _encode_request(request_id, payload, self._max_request_bytes)
            self._request_id = request_id
            try:
                self._write_frame(frame, deadline, active)
                reply = self._read_frame(deadline, active, "inference")
                active()
                if time.monotonic() >= deadline:
                    raise Pm2WorkerError("native model inference timed out")
                if type(reply.get("request_id")) is not int or reply["request_id"] != request_id:
                    raise Pm2WorkerError("native reply has a stale or unsupported request identity")
                if reply.get("kind") == "error" and isinstance(reply.get("message"), str):
                    raise Pm2WorkerError(f"native inference failed: {reply['message'][:1800]}")
                if reply.get("kind") != "result" or not isinstance(reply.get("payload"), dict):
                    raise Pm2WorkerError("native child sent an unsupported result reply")
                return reply["payload"]
            except BaseException as error:
                failure = error
                raise
        finally:
            if failure is not None:
                self._closed = True
            self._lock.release()
            if failure is not None:
                self._stop_after_error(failure)

    def _stop_after_error(self, error: BaseException) -> None:
        try:
            self._stop(graceful=False)
        except BaseException as cleanup:
            error.add_note(f"native child teardown failed: {cleanup!s}"[:1800])

    def _stop(self, *, graceful: bool) -> None:
        process = self._process
        assert process.stdin is not None and process.stdout is not None
        with self._stop_lock:
            if process.returncode is not None:
                return
            self._closed = True
            try:
                idle = self._lock.acquire(blocking=False) if graceful else False
                if idle:
                    try:
                        process.stdin.close()
                    finally:
                        self._lock.release()
                    deadline = time.monotonic() + 1.0
                    while time.monotonic() < deadline:
                        # Reserve the leader PID until after the group signal.
                        if os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT):
                            break
                        time.sleep(0.025)
            finally:
                # A native descendant may outlive a normally exited leader.
                with suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
                # A sent signal is not confirmation of exit. Keep the group ID
                # and device reserved until no member can still hold the device.
                while _live_group(process.pid):
                    time.sleep(0.025)
                process.wait()
                # The in-flight caller releases this lock before it joins
                # teardown. Keep its pipe descriptors valid until it exits I/O.
                with self._lock:
                    process.stdin.close()
                    process.stdout.close()


def _check_unrestricted() -> None:
    return None


@contextmanager
def open_pm2_worker(
    *,
    python: Path,
    script: Path,
    profile: Path,
    device: Literal["cpu", "cuda"],
    nemotron_endpoint: str | None = None,
    check_active: Callable[[], None] | None = None,
    startup_timeout_seconds: float = 300.0,
    inference_timeout_seconds: float = 120.0,
    max_request_bytes: int = 8_388_608,
    max_reply_bytes: int = 8_388_608,
) -> Generator[Pm2Worker]:
    """Launch an exact local interpreter and hold device custody through teardown."""
    if device not in {"cpu", "cuda"} or (device == "cpu" and nemotron_endpoint is not None):
        raise Pm2WorkerRefused("worker requires an explicit compatible device and handoff")
    if any(
        not math.isfinite(value) or value <= 0
        for value in (startup_timeout_seconds, inference_timeout_seconds)
    ) or any(
        type(value) is not int or value <= 0 for value in (max_request_bytes, max_reply_bytes)
    ):
        raise Pm2WorkerRefused("worker requires finite positive deadlines and frame byte bounds")
    if device == "cuda" and _owns_cuda.get():
        raise Pm2WorkerRefused("a resident PM2 GPU worker already owns this device context")
    active = check_active if check_active is not None else _check_unrestricted
    startup_deadline = time.monotonic() + startup_timeout_seconds

    def startup_active() -> None:
        active()
        if time.monotonic() >= startup_deadline:
            raise Pm2WorkerError("native model startup timed out while acquiring capacity")

    custody = (
        suspend_resident_nemotron(nemotron_endpoint, check_active=startup_active)
        if device == "cuda"
        else nullcontext()
    )
    token = _owns_cuda.set(True) if device == "cuda" else None
    try:
        with custody:
            startup_active()
            environment = {
                "PATH": os.defpath,
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "TOKENIZERS_PARALLELISM": "false",
            }
            if device == "cpu":
                environment["CUDA_VISIBLE_DEVICES"] = ""
            try:
                process = subprocess.Popen(
                    [
                        str(python.absolute()),
                        "-I",
                        "-u",
                        str(script.absolute()),
                        str(profile.absolute()),
                    ],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    env=environment,
                    start_new_session=True,
                    bufsize=0,
                )
            except OSError as error:
                raise Pm2WorkerError(
                    f"native child could not start: {type(error).__name__}"
                ) from error
            worker = Pm2Worker(
                process,
                check_active=active,
                inference_timeout_seconds=inference_timeout_seconds,
                max_request_bytes=max_request_bytes,
                max_reply_bytes=max_reply_bytes,
            )
            try:
                assert process.stdin is not None
                os.set_blocking(process.stdin.fileno(), False)
                worker._ready(startup_deadline - time.monotonic())
                yield worker
            except BaseException as error:
                worker._stop_after_error(error)
                raise
            else:
                worker._stop(graceful=True)
    finally:
        if token is not None:
            _owns_cuda.reset(token)
