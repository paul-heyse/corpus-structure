"""Same-host control of one live, managed execution."""

from __future__ import annotations

import os
import secrets
import socket
import struct
from contextlib import contextmanager
from pathlib import Path
from threading import Event, Thread
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from corpus_structure._diagnostic_capture import safe_text
from corpus_structure.core.execution_control import (
    ExecutionStopped,
    ExecutionStopRequest,
    execution_stop_scope,
)

if TYPE_CHECKING:
    from corpus_structure.cli.managed import Invocation, ResultStore


_MAX_MESSAGE = 8192
_OWNER_FIELD = "execution_control"
_State = Literal[
    "stop_requested",
    "draining",
    "confirmed_retirement",
    "unresolved_custody",
    "already_terminal",
    "unavailable",
]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class _Owner(_Model):
    address: str = Field(pattern=r"^corpus-stop-[0-9a-f]{32}$")
    result: str
    pid: int = Field(gt=0)
    uid: int = Field(ge=0)
    boot: str
    started: int = Field(ge=0)


class _Stop(_Model):
    owner: _Owner
    reason: str = Field(min_length=1, max_length=512)


class StopReport(_Model):
    result: str
    state: _State
    outcome: str | None = None
    next_action: str | None = None


def _peer(endpoint: socket.socket) -> tuple[int, int]:
    size = struct.calcsize("3i")
    pid, uid, _gid = struct.unpack(
        "3i",
        endpoint.getsockopt(
            socket.SOL_SOCKET,
            socket.SO_PEERCRED,
            size,
        ),
    )
    return pid, uid


def _boot() -> str:
    return Path("/proc/sys/kernel/random/boot_id").read_text().strip()


def _started(pid: int) -> int:
    return int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19])


@contextmanager
def stoppable_invocation(invocation: Invocation):
    """Expose one authenticated local request and let the run own its effects."""
    if not hasattr(socket, "SO_PEERCRED") or not hasattr(socket, "SOCK_SEQPACKET"):
        yield
        return

    pid = os.getpid()
    owner = _Owner(
        result=invocation.id,
        address="corpus-stop-" + secrets.token_hex(16),
        pid=pid,
        uid=os.getuid(),
        boot=_boot(),
        started=_started(pid),
    )
    control = ExecutionStopRequest()
    closing = Event()
    reason: list[str] = []
    with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as listener:
        listener.bind("\0" + owner.address)
        listener.listen(4)
        listener.settimeout(0.1)
        invocation.manifest.details[_OWNER_FIELD] = owner.model_dump(mode="json")
        invocation.stage(invocation.manifest.stage)

        def listen():
            while not closing.is_set():
                try:
                    endpoint, _ = listener.accept()
                except TimeoutError:
                    continue
                except OSError:
                    return
                with endpoint:
                    endpoint.settimeout(0.25)
                    try:
                        _, caller = _peer(endpoint)
                        if caller != owner.uid:
                            continue
                        packet = endpoint.recv(_MAX_MESSAGE + 1)
                        if len(packet) > _MAX_MESSAGE:
                            continue
                        command = _Stop.model_validate_json(packet)
                        if command.owner != owner or closing.is_set():
                            continue
                        if not control.requested.is_set():
                            reason.append(command.reason)
                            control.requested.set()
                        report = StopReport(
                            result=owner.result,
                            state="draining" if control.draining.is_set() else "stop_requested",
                            next_action=f"ci results show {owner.result}",
                        )
                        endpoint.sendall(report.model_dump_json().encode())
                    except OSError, ValidationError:
                        continue

        listener_thread = Thread(target=listen, name="managed-execution-control")
        listener_thread.start()
        try:
            with execution_stop_scope(control):
                yield
        except ExecutionStopped:
            invocation.observe("interruption", "managed stop", reason=safe_text(reason[0]))
            raise
        finally:
            closing.set()
            listener_thread.join()


def stop_result(store: ResultStore, result: str, reason: str) -> StopReport:
    with store.lease(result):
        manifest = store.show(result)
        owner_value = manifest.details.get(_OWNER_FIELD)

        def observed():
            selected = store.show(result)
            if selected.settled is None:
                state: _State = "unavailable"
            elif selected.details.get("custody_unsettled"):
                state = "unresolved_custody"
            elif (
                selected.outcome == "interrupted"
                and selected.details.get("error_type") == "ExecutionStopped"
                and selected.custody_settled()
            ):
                state = "confirmed_retirement"
            else:
                state = "already_terminal"
            return StopReport(
                result=result,
                state=state,
                outcome=selected.outcome,
                next_action=f"ci results show {result}",
            )

        if manifest.settled is not None or owner_value is None:
            return observed()
        try:
            owner = _Owner.model_validate(owner_value)
            if owner.result != result or owner.uid != os.getuid() or owner.boot != _boot():
                return observed()
            with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as endpoint:
                endpoint.settimeout(2)
                endpoint.connect("\0" + owner.address)
                if (
                    _peer(endpoint) != (owner.pid, owner.uid)
                    or _started(owner.pid) != owner.started
                ):
                    return observed()
                request = _Stop(owner=owner, reason=safe_text(reason))
                endpoint.sendall(request.model_dump_json().encode())
                report = StopReport.model_validate_json(endpoint.recv(_MAX_MESSAGE + 1))
                if report.result == result and report.state in {"stop_requested", "draining"}:
                    return report
        except OSError, ValueError, IndexError:
            return observed()
        return observed()
