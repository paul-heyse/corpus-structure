"""Versioned, bounded safe observations; managed.py owns publication and read leases."""

from __future__ import annotations

import base64
import hashlib
import math
import os
import re
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import structlog
from pydantic import BaseModel, ConfigDict, Field, JsonValue

from corpus_structure._diagnostic_capture import safe_text
from corpus_structure.cli.exception_observations import ExceptionTrace

JOURNAL_BYTES = 8 * 1024 * 1024
RECORD_BYTES = 64 * 1024  # Includes the terminating newline.
PAGE_BYTES = 256 * 1024
SPOOL_BYTES = 2 * 1024 * 1024
LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
Severity = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
_SECRET = re.compile(r"password|token|api[_-]?key|credential|secret", re.I)
_RENDER_JSON = structlog.processors.JSONRenderer(ensure_ascii=False, separators=(",", ":"))


class ObservationError(ValueError):
    """An unavailable journal, incompatible cursor, or invalid selection."""


class Bindings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    invocation_id: str | None = None
    run_id: int | None = None
    provider_invocation: str | None = None
    task_id: int | None = None
    attempt: int | None = None
    request_id: str | None = None
    method: str | None = None
    project: str | None = None
    release_id: str | None = None


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal[1] = 1
    sequence: int = Field(ge=1)
    timestamp: str
    kind: str
    severity: Severity = "INFO"
    stage: str | None = None
    message: str
    fields: dict[str, JsonValue] = Field(default_factory=dict)
    exception: ExceptionTrace | None = None
    bindings: Bindings = Field(default_factory=Bindings)
    producer: str
    producer_sequence: int = Field(ge=1)
    assurance: Literal["native", "provider_reported", "observation"] = "observation"
    omissions: tuple[str, ...] = ()


class Journal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    id: str = Field(default_factory=lambda: uuid4().hex)
    standing: Literal["unsealed", "sealed", "unavailable"] = "unsealed"
    length: int | None = None
    sha256: str | None = None
    omitted: int | None = None
    unavailable_reason: str | None = None
    collection_threshold: Severity = "INFO"
    retained_bytes_limit: int = JOURNAL_BYTES
    record_bytes_limit: int = RECORD_BYTES


class ObservationSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    severity: Severity = "DEBUG"
    stage: str | None = None
    method: str | None = None
    provider_invocation: str | None = None
    task: int | None = Field(default=None, ge=1)
    attempt: int | None = Field(default=None, ge=1)
    limit: int = Field(default=100, ge=1, le=1000)
    max_bytes: int = Field(default=PAGE_BYTES, ge=65536, le=1024 * 1024)
    examined_bytes: int = Field(default=PAGE_BYTES, ge=65536, le=1024 * 1024)

    def require_qualified_attempt(self) -> None:
        if self.attempt is not None and (self.provider_invocation is None or self.task is None):
            raise ObservationError("an attempt requires --provider-invocation and --task")

    def matches(self, row: Observation) -> bool:
        return (
            LEVELS[row.severity] >= LEVELS[self.severity]
            and (self.stage is None or row.stage == self.stage)
            and (self.method is None or row.bindings.method == self.method)
            and (
                self.provider_invocation is None
                or row.bindings.provider_invocation == self.provider_invocation
            )
            and (self.task is None or row.bindings.task_id == self.task)
            and (self.attempt is None or row.bindings.attempt == self.attempt)
        )


class Cursor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    result: str
    journal: str
    identity: tuple[int, int]
    offset: int = Field(ge=0)
    sequence: int = Field(ge=0)
    observed_bytes: int = Field(ge=0)

    def encode(self) -> str:
        return base64.urlsafe_b64encode(self.model_dump_json().encode()).decode().rstrip("=")

    @classmethod
    def decode(cls, value: str) -> Cursor:
        try:
            if len(value) > 2048:
                raise ValueError("oversized cursor")
            return cls.model_validate_json(
                base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
            )
        except (ValueError, TypeError) as error:
            raise ObservationError("invalid observation cursor") from error


class ObservationPage(BaseModel):
    version: Literal[1] = 1
    result: str
    journal: str | None = None
    availability: Literal["available", "unavailable"] = "available"
    standing: Literal["running", "unsealed", "sealed", "unavailable"] = "unsealed"
    coverage: Literal[
        "complete_prefix", "continued", "pending", "corrupt", "unavailable", "latest_window"
    ] = "complete_prefix"
    ordering: Literal["parent_journal_sequence"] = "parent_journal_sequence"
    rows: list[Observation] = Field(default_factory=list)
    next_after: str | None = None
    observed_bytes: int = 0
    examined_bytes: int = 0
    authentication_bytes: int = 0
    selected_count: int = 0
    selection_kind: Literal["page", "latest_window"] = "page"
    position_semantics: Literal["page_scan", "watch_scan_progress"] = "page_scan"
    window_limit: int | None = None
    returned_sequence_range: tuple[int, int] | None = None
    window_evicted: int = 0
    window_budget_evicted: int = 0
    start_offset: int = 0
    end_offset: int = 0
    pending_tail: bool = False
    corrupt: bool = False
    continuation: bool = False
    response_omitted: int = 0
    collection_omitted: int | None = None
    collection_threshold: Severity = "INFO"
    unavailable_reason: str | None = None


def normalize(value: Any, *, max_bytes: int = 32768) -> tuple[JsonValue, tuple[str, ...]]:
    """Own nested values before fan-out, without invoking arbitrary repr/str methods."""
    omissions: list[str] = []
    remaining = max_bytes
    seen: set[int] = set()

    def omitted(path: str, reason: str) -> str:
        if len(omissions) < 32:
            omissions.append(f"{path}: {reason}")
        return f"[omitted: {reason}]"

    def visit(item: Any, path: str, depth: int) -> JsonValue:
        nonlocal remaining
        if remaining <= 0:
            return omitted(path, "byte limit")
        if item is None or type(item) is bool:
            remaining -= 5
            return item
        if type(item) in (int, float):
            if type(item) is int and item.bit_length() > 256:
                return omitted(path, "oversized integer")
            if type(item) is float and not math.isfinite(item):
                return omitted(path, "nonfinite number")
            remaining -= 32
            return item
        if isinstance(item, str):
            clean = safe_text(item).encode("utf-8", errors="replace")
            cap = max(0, min(4096, remaining))
            remaining -= min(len(clean), cap)
            if len(clean) > cap:
                return clean[:cap].decode("utf-8", errors="ignore") + omitted(path, "text limit")
            return clean.decode("utf-8")
        if depth >= 10:
            return omitted(path, "depth limit")
        if isinstance(item, (dict, list, tuple)):
            if id(item) in seen:
                return omitted(path, "cycle")
            seen.add(id(item))
            try:
                if isinstance(item, dict):
                    result: dict[str, JsonValue] = {}
                    for index, (key, child) in enumerate(item.items()):
                        if index >= 32 or remaining <= 0:
                            result["__omitted__"] = omitted(path, "item or byte limit")
                            break
                        if not isinstance(key, str):
                            omitted(path, "non-text key")
                            continue
                        # Do not shorten keys: they locate the approved data being omitted.
                        if len(key.encode("utf-8", errors="replace")) > 256:
                            omitted(path, "oversized key")
                            continue
                        clean_key = safe_text(key)
                        remaining -= len(clean_key.encode())
                        result[clean_key] = (
                            "**********"
                            if _SECRET.search(key)
                            else visit(child, f"{path}.{clean_key}", depth + 1)
                        )
                    return result
                result_list: list[JsonValue] = []
                for index, child in enumerate(item):
                    if index >= 32 or remaining <= 0:
                        result_list.append(omitted(path, "item or byte limit"))
                        break
                    result_list.append(visit(child, f"{path}[{index}]", depth + 1))
                return result_list
            finally:
                seen.remove(id(item))
        return omitted(path, "unsupported " + type(item).__name__[:80])

    return visit(value, "$", 0), tuple(omissions)


def encode_row(row: Observation) -> bytes:
    rendered = _RENDER_JSON(None, "info", row.model_dump(mode="json"))
    assert isinstance(rendered, str)
    return (rendered + "\n").encode("utf-8")


class ObservationWriter:
    """One process owns the file; its local producer threads share this writer lock."""

    def __init__(self, path: Path, *, limit: int = JOURNAL_BYTES, producer: str | None = None):
        self.path = path
        self.journal = Journal(retained_bytes_limit=limit)
        self.producer = producer or f"process:{os.getpid()}:{uuid4().hex}"
        self._stream = path.open("x+b", buffering=0)
        path.chmod(0o600)
        self._lock = threading.RLock()
        self._sequence = self._producer_sequence = self._bytes = self._omitted = 0
        self._closed = False
        self._truncated = False

    def unavailable(self, reason: str) -> None:
        self.journal.standing = "unavailable"
        self.journal.unavailable_reason = safe_text(reason)[:256]

    def _append(self, row: Observation) -> None:
        data = encode_row(row)
        # A complete row is pre-encoded and serialized under the lock. Reads still handle tears.
        view = memoryview(data)
        while view:
            written = self._stream.write(view)
            if written is None or written <= 0:
                raise OSError("observation append made no progress")
            view = view[written:]
        self._bytes += len(data)
        self._sequence = row.sequence

    def _marker(self, kind: str, fields: dict[str, JsonValue]) -> Observation:
        self._producer_sequence += 1
        return Observation(
            sequence=self._sequence + 1,
            timestamp=datetime.now(UTC).isoformat(),
            kind=kind,
            message=(
                "Observation collection is bounded; "
                "omitted events cannot be recovered by filtering."
            ),
            fields=fields,
            producer=self.producer,
            producer_sequence=self._producer_sequence,
        )

    def append(
        self,
        event: dict[str, Any],
        *,
        imported: Observation | None = None,
        normalized: bool = False,
    ) -> None:
        with self._lock:
            if self._closed or self.journal.standing == "unavailable":
                return
            try:
                self._producer_sequence += 1
                if imported is not None:
                    row = imported.model_copy(update={"sequence": self._sequence + 1})
                else:
                    safe_event, omissions = (dict(event), ()) if normalized else normalize(event)
                    assert isinstance(safe_event, dict)
                    normalized_event = safe_event
                    if normalized:
                        recorded_omissions = normalized_event.pop("normalization_omissions", [])
                        omissions = (
                            tuple(item for item in recorded_omissions if isinstance(item, str))
                            if isinstance(recorded_omissions, list)
                            else ()
                        )
                    binding_values = normalized_event.pop("bindings", {})
                    binding = Bindings.model_validate(binding_values)
                    row = Observation.model_validate(
                        {
                            "sequence": self._sequence + 1,
                            "timestamp": normalized_event.pop(
                                "timestamp", datetime.now(UTC).isoformat()
                            ),
                            "kind": normalized_event.pop("kind", "log"),
                            "severity": str(normalized_event.pop("severity", "INFO")).upper(),
                            "stage": normalized_event.pop("stage", None),
                            "message": normalized_event.pop(
                                "message", normalized_event.pop("event", "Observation")
                            ),
                            "exception": normalized_event.pop("exception", None),
                            "fields": normalized_event,
                            "bindings": binding,
                            "producer": self.producer,
                            "producer_sequence": self._producer_sequence,
                            "assurance": normalized_event.pop("assurance", "observation"),
                            "omissions": omissions,
                        }
                    )
                if len(encode_row(row)) > RECORD_BYTES:
                    row = row.model_copy(
                        update={
                            "message": "Oversized observation omitted.",
                            "fields": {},
                            "exception": ExceptionTrace(stacks=(), omissions=())
                            if row.exception is not None
                            else None,
                            "omissions": (*row.omissions[:16], "$: encoded record limit"),
                        }
                    )
                if (
                    self._truncated
                    or self._bytes + len(encode_row(row)) > self.journal.retained_bytes_limit - 2048
                ):
                    self._omitted += 1
                    if not self._truncated:
                        self._truncated = True
                        self._append(self._marker("collection_truncated", {"omitted_at_least": 1}))
                    return
                self._append(row)
            except Exception as error:
                self.unavailable(type(error).__name__)

    def close(self) -> Journal:
        with self._lock:
            if self._closed:
                return self.journal
            try:
                if self._truncated:
                    self._append(self._marker("collection_summary", {"omitted": self._omitted}))
                self.journal.omitted = self._omitted
                if self.journal.standing != "unavailable":
                    data = os.pread(self._stream.fileno(), self.journal.retained_bytes_limit + 1, 0)
                    if len(data) > self.journal.retained_bytes_limit:
                        raise OSError("observation retention limit exceeded")
                    self.journal.length = len(data)
                    self.journal.sha256 = hashlib.sha256(data).hexdigest()
                    self.journal.standing = "sealed"
            except Exception as error:
                self.unavailable(type(error).__name__)
            finally:
                self._closed = True
                try:
                    self._stream.close()
                except Exception as error:
                    self.unavailable(type(error).__name__)
            return self.journal


class ObservationReader:
    """A leased, publication-checked descriptor; sealed input is authenticated and pinned once."""

    def __init__(self, result: str, journal: Journal, fd: int):
        self.result, self.journal, self.fd = result, journal, fd
        info = os.fstat(fd)
        self.identity = (info.st_dev, info.st_ino)
        self._authenticated: bytes | None = None
        self.authentication_bytes = 0
        self._positions: dict[int, tuple[int, int]] = {}

    def read(
        self,
        selection: ObservationSelection,
        *,
        after: str | None = None,
        running: bool = False,
        journal: Journal | None = None,
    ) -> ObservationPage:
        selection.require_qualified_attempt()
        current = journal or self.journal
        size = os.fstat(self.fd).st_size
        if size > JOURNAL_BYTES or size > current.retained_bytes_limit:
            raise ObservationError("journal exceeds its retained byte limit")
        if current.standing == "unavailable":
            return ObservationPage(
                result=self.result,
                journal=current.id,
                availability="unavailable",
                standing="unavailable",
                coverage="unavailable",
                unavailable_reason=current.unavailable_reason,
            )
        if current.standing == "sealed" and self._authenticated is None:
            data = os.pread(self.fd, JOURNAL_BYTES + 1, 0)
            self.authentication_bytes = len(data)
            if len(data) != current.length or hashlib.sha256(data).hexdigest() != current.sha256:
                raise ObservationError("sealed observation journal digest or length mismatch")
            self._authenticated = data
        if self._authenticated is not None:
            size = len(self._authenticated)
        cursor = (
            Cursor.decode(after)
            if after
            else Cursor(
                result=self.result,
                journal=current.id,
                identity=self.identity,
                offset=0,
                sequence=0,
                observed_bytes=0,
            )
        )
        if (
            cursor.result != self.result
            or cursor.journal != current.id
            or cursor.identity != self.identity
        ):
            raise ObservationError("observation cursor belongs to a different result or journal")
        if size < cursor.observed_bytes or cursor.offset > size:
            raise ObservationError("observation journal shortened since the cursor")
        if cursor.offset:
            previous = (
                self._authenticated[cursor.offset - 1 : cursor.offset]
                if self._authenticated is not None
                else os.pread(self.fd, 1, cursor.offset - 1)
            )
            if previous != b"\n":
                raise ObservationError("observation cursor is not at a complete record boundary")
        batch = (
            self._authenticated[cursor.offset : cursor.offset + selection.examined_bytes]
            if self._authenticated is not None
            else os.pread(
                self.fd, min(selection.examined_bytes, size - cursor.offset), cursor.offset
            )
        )
        page = ObservationPage(
            result=self.result,
            journal=current.id,
            standing="sealed"
            if current.standing == "sealed"
            else "running"
            if running
            else "unsealed",
            observed_bytes=size,
            authentication_bytes=self.authentication_bytes,
            examined_bytes=len(batch),
            start_offset=cursor.offset,
            end_offset=cursor.offset,
            collection_omitted=current.omitted,
            collection_threshold=current.collection_threshold,
        )
        offset, sequence, index = cursor.offset, cursor.sequence, 0
        self._positions = {}
        while index < len(batch):
            newline = batch.find(b"\n", index)
            if newline < 0:
                at_end = cursor.offset + len(batch) == size
                page.pending_tail = at_end
                if len(batch) - index >= RECORD_BYTES or (at_end and current.standing == "sealed"):
                    page.corrupt = True
                break
            line = batch[index : newline + 1]
            try:
                if len(line) > RECORD_BYTES:
                    raise ValueError("oversized record")
                row = Observation.model_validate_json(line)
                if row.sequence != sequence + 1:
                    raise ValueError("nonconsecutive journal sequence")
            except ValueError:
                page.corrupt = True
                break
            selected = selection.matches(row)
            if selected:
                self._positions[row.sequence] = (offset, sequence)
            if selected and len(page.rows) >= selection.limit:
                break
            if selected:
                # Leave conservative room for the complete coverage/cursor envelope.
                if (
                    sum(len(encode_row(item)) for item in page.rows) + len(encode_row(row))
                    > selection.max_bytes - 8192
                ):
                    page.response_omitted += 1
                    if not page.rows:
                        # An individual row cannot fit this response. Return a located omission
                        # and advance, so the minimum response budget always makes progress.
                        row = row.model_copy(
                            update={
                                "message": "Observation omitted from response byte budget.",
                                "fields": {},
                                "omissions": (*row.omissions[:16], "$: response byte limit"),
                            }
                        )
                    else:
                        break
                page.rows.append(row)
            sequence = row.sequence
            consumed = newline + 1 - index
            offset += consumed
            index = newline + 1
        page.end_offset = offset
        page.selected_count = len(page.rows)
        page.continuation = not page.corrupt and offset < size and not page.pending_tail
        page.coverage = (
            "corrupt"
            if page.corrupt
            else "pending"
            if page.pending_tail
            else "continued"
            if page.continuation
            else "complete_prefix"
        )
        page.next_after = Cursor(
            result=self.result,
            journal=current.id,
            identity=self.identity,
            offset=offset,
            sequence=sequence,
            observed_bytes=size,
        ).encode()
        # Model bytes, not a sum of payload bytes, define the public response contract.
        if len(page.model_dump_json().encode()) > selection.max_bytes:
            raise ObservationError("observation response envelope exceeds byte budget")
        return page

    def withhold_rows(self, page: ObservationPage, keep: int) -> ObservationPage:
        """Return a bounded continuation before the first withheld complete selected record."""
        withheld = page.rows[keep:]
        if not withheld:
            return page
        offset, sequence = self._positions[withheld[0].sequence]
        return page.model_copy(
            update={
                "rows": page.rows[:keep],
                "selected_count": keep,
                "end_offset": offset,
                "continuation": True,
                "coverage": "continued",
                "corrupt": False,
                "pending_tail": False,
                "response_omitted": page.response_omitted + len(withheld),
                "next_after": Cursor(
                    result=self.result,
                    journal=self.journal.id,
                    identity=self.identity,
                    offset=offset,
                    sequence=sequence,
                    observed_bytes=page.observed_bytes,
                ).encode(),
            }
        )
