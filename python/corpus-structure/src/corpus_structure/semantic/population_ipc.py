"""Invocation-owned Arrow files sealed against mutation across CPU process handoff."""

from __future__ import annotations

import fcntl
import os
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, BinaryIO

import pyarrow as pa

# Linux UAPI, include/uapi/linux/fcntl.h. This Python build omits their symbols.
_F_ADD_SEALS = 1033
_F_GET_SEALS = 1034
_SEALS = 0x0001 | 0x0002 | 0x0004 | 0x0008  # SEAL, SHRINK, GROW, WRITE


def _binding(schema: pa.Schema, request_digest: str, projection_digest: str) -> dict[bytes, bytes]:
    if not request_digest or not projection_digest:
        raise ValueError("population IPC requires request and projection identities")
    return {
        b"corpus.request": request_digest.encode(),
        b"corpus.projection": projection_digest.encode(),
        b"corpus.schema": sha256(schema.serialize()).hexdigest().encode(),
    }


def _receive(duplicate, byte_length: int, digest: str) -> SealedPopulationIpc:
    return SealedPopulationIpc(duplicate.detach(), byte_length, digest)


class _BoundedOutput:
    def __init__(self, stream: BinaryIO, max_bytes: int):
        self.stream = stream
        self.max_bytes = max_bytes

    @property
    def closed(self) -> bool:
        return self.stream.closed

    def tell(self) -> int:
        return self.stream.tell()

    def write(self, content) -> int:
        if len(content) > self.max_bytes - self.tell():
            raise ValueError("population IPC exceeds its byte bound")
        return self.stream.write(content)


@dataclass(frozen=True)
class PopulationIpcTransfer:
    """An explicitly revocable descriptor offer to the owned process pool."""

    duplicate: Any
    byte_length: int
    digest: str

    def receive(self) -> SealedPopulationIpc:
        return _receive(self.duplicate, self.byte_length, self.digest)

    def retire(self) -> None:
        """Close the CPython share if a cancelled task never received its descriptor."""
        from multiprocessing import resource_sharer

        # The pinned CPython sharer removes a received offer before sending its
        # descriptor. Once the task/transport is settled, only an unused offer
        # can remain, and removing it does not touch other users of the sharer.
        _, key = self.duplicate._id
        resource = vars(resource_sharer)["_resource_sharer"]
        with resource._lock:
            pending = resource._cache.pop(key, None)
        if pending is not None:
            _, close = pending
            close()


class SealedPopulationIpc:
    """One sealed file descriptor, explicitly closed by its invocation or borrower.

    The Linux memfd file is memory-backed and has no mutable pathname. A transferred
    descriptor owns a separate reference to the same sealed bytes. Callers charge its
    byte length to the invocation budget before retaining or submitting it.
    """

    def __init__(self, descriptor: int, byte_length: int, digest: str):
        self._descriptor: int | None = descriptor
        self.byte_length = byte_length
        self.digest = digest

    @classmethod
    def write(
        cls,
        table: pa.Table,
        *,
        schema: pa.Schema,
        request_digest: str,
        projection_digest: str,
        max_bytes: int,
        check_active: Callable[[], None] = lambda: None,
    ) -> SealedPopulationIpc:
        """Encode the owned table and seal its file before publishing its descriptor."""
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("population IPC requires a positive byte bound")
        if not table.schema.equals(schema, check_metadata=True):
            raise ValueError("population IPC schema differs from the admitted schema")
        metadata = _binding(schema, request_digest, projection_digest)
        if table.nbytes > max_bytes:
            raise ValueError("population IPC exceeds its byte bound")
        check_active()
        descriptor = os.memfd_create("corpus-population-ipc", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
        try:
            with (
                os.fdopen(os.dup(descriptor), "wb") as target,
                pa.ipc.new_file(
                    pa.PythonFile(_BoundedOutput(target, max_bytes), mode="w"),
                    schema,
                    metadata=metadata,
                ) as writer,
            ):
                for batch in table.to_reader(max_chunksize=65536):
                    check_active()
                    writer.write_batch(batch)
            byte_length = os.fstat(descriptor).st_size
            if byte_length > max_bytes:
                raise ValueError("population IPC exceeds its byte bound")
            fcntl.fcntl(descriptor, _F_ADD_SEALS, _SEALS)
            with pa.memory_map(f"/proc/self/fd/{descriptor}", "r") as source:
                digest = sha256(source.read_buffer()).hexdigest()
            return cls(descriptor, byte_length, digest)
        except BaseException:
            os.close(descriptor)
            raise

    def __reduce__(self):
        transfer = self.offer()
        return _receive, (transfer.duplicate, transfer.byte_length, transfer.digest)

    def offer(self) -> PopulationIpcTransfer:
        from multiprocessing.reduction import DupFd

        if self._descriptor is None:
            raise ValueError("population IPC owner is closed")
        return PopulationIpcTransfer(DupFd(self._descriptor), self.byte_length, self.digest)

    @contextmanager
    def open(
        self,
        *,
        schema: pa.Schema,
        request_digest: str,
        projection_digest: str,
        max_bytes: int,
    ) -> Generator[pa.Table]:
        """Authenticate and consume one read-only mapping of the same sealed file."""
        expected = _binding(schema, request_digest, projection_digest)
        if self._descriptor is None:
            raise ValueError("population IPC owner is closed")
        if type(max_bytes) is not int or max_bytes <= 0 or not 0 < self.byte_length <= max_bytes:
            raise ValueError("population IPC exceeds its byte bound")
        if fcntl.fcntl(self._descriptor, _F_GET_SEALS) & _SEALS != _SEALS:
            raise ValueError("population IPC file is not sealed")
        if os.fstat(self._descriptor).st_size != self.byte_length:
            raise ValueError("population IPC size differs from its transfer descriptor")
        with pa.memory_map(f"/proc/self/fd/{self._descriptor}", "r") as source:
            if sha256(source.read_buffer()).hexdigest() != self.digest:
                raise ValueError("population IPC bytes differ from their transfer seal")
            source.seek(0)
            reader = pa.ipc.open_file(source)
            if reader.metadata != expected or not reader.schema.equals(schema, check_metadata=True):
                raise ValueError("population IPC changes its request, projection or schema")
            yield reader.read_all()

    def close(self) -> None:
        if self._descriptor is not None:
            os.close(self._descriptor)
            self._descriptor = None

    def __enter__(self) -> SealedPopulationIpc:
        if self._descriptor is None:
            raise ValueError("population IPC owner is closed")
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
