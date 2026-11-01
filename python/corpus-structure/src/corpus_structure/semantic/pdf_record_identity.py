"""Versioned PDF record identity and bounded exact-byte artifact custody.

This profile is deliberately separate from historical ``content_digest``. It is a
domain-separated SHA-256 *fold*, not SHA-256 of concatenated upload parts. Every
scalar is represented by its type, exact payload length and the fold of canonical
64 KiB byte blocks. Inline and external storage therefore have identical meaning.
The payload vocabulary and fold framing are mirrored independently in PostgreSQL.

Callers supply records in UTF-8 binary (family, key) order, normally by an ordered
database cursor/external sort. Schema-declared field order is meaning-bearing.
Neither physical batch metadata nor native array addresses are implicit inputs.
"""

from __future__ import annotations

import math
import re
import struct
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from typing import BinaryIO, Final

PROTOCOL: Final = "pdf-record-sha256-fold-v1"
BLOCK_BYTES: Final = 65_536
MAX_FRAME_BYTES: Final = 65_536
_MAX_LENGTH: Final = (1 << 63) - 1
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_START: Final = b"corpus.pdf.fold.v1/start\x00"
_STEP: Final = b"corpus.pdf.fold.v1/step\x00"
_END: Final = b"corpus.pdf.fold.v1/end\x00"


class _Absent:
    __slots__ = ()


ABSENT: Final = _Absent()
type Scalar = _Absent | bool | int | float | str | bytes | Decimal | None


def _length(value: int) -> bytes:
    if type(value) is not int or not 0 <= value <= _MAX_LENGTH:
        raise ValueError("length/ordinal must be a nonnegative signed-64-bit integer")
    return struct.pack(">q", value)


def frame(tag: bytes, payload: bytes) -> bytes:
    """One-byte type and network-order uint63 length; payload is bounded."""
    if len(tag) != 1 or len(payload) > MAX_FRAME_BYTES:
        raise ValueError("identity frame requires a one-byte tag and bounded payload")
    return tag + _length(len(payload)) + payload


class IdentityFold:
    """Constant-space fold over bounded frames; finalization does not mutate state."""

    def __init__(self, domain: str) -> None:
        self._state = sha256(_START + frame(b"D", domain.encode("utf-8"))).digest()
        self.count = 0
        self.byte_length = 0

    def add(self, payload: bytes) -> None:
        if len(payload) > MAX_FRAME_BYTES:
            raise ValueError("identity fold frame exceeds 64 KiB")
        _length(self.byte_length + len(payload))
        self._state = sha256(
            _STEP + self._state + _length(self.count) + frame(b"F", payload)
        ).digest()
        self.count += 1
        self.byte_length += len(payload)

    def digest(self) -> bytes:
        return sha256(_END + self._state + _length(self.count) + _length(self.byte_length)).digest()


def canonical_blocks(chunks: Iterable[bytes]) -> Iterator[bytes]:
    """Reblock an arbitrary byte delivery into canonical 64 KiB blocks."""
    pending = bytearray()
    for chunk in chunks:
        if not isinstance(chunk, bytes):
            raise TypeError("byte stream chunks must be bytes")
        remaining = memoryview(chunk)
        while remaining:
            amount = min(BLOCK_BYTES - len(pending), len(remaining))
            pending.extend(remaining[:amount])
            remaining = remaining[amount:]
            if len(pending) == BLOCK_BYTES:
                yield bytes(pending)
                pending.clear()
    if pending:
        yield bytes(pending)


def byte_root(chunks: Iterable[bytes]) -> tuple[int, bytes]:
    """Return actual byte length and the fixed-block fold, never a claimed hash."""
    folded = IdentityFold("bytes")
    for block in canonical_blocks(chunks):
        folded.add(block)
    return folded.byte_length, folded.digest()


def emit_parts(stream_id: str, chunks: Iterable[bytes]) -> Iterator[ArtifactPart]:
    """Prepare bounded transport parts; stream identity is supplied by its owner."""
    if not stream_id:
        raise ValueError("artifact stream identity is required")
    offset = 0
    for ordinal, body in enumerate(canonical_blocks(chunks)):
        yield ArtifactPart(stream_id, ordinal, offset, len(body), body, sha256(body).hexdigest())
        offset += len(body)


@dataclass(frozen=True, slots=True)
class ScalarDescriptor:
    """Bounded logical value descriptor; artifact location is deliberately absent.

    External descriptors require an owner-validated typed scalar payload. A byte
    root establishes byte integrity, not scalar validity or native correspondence.
    """

    kind: bytes
    byte_length: int
    byte_root: bytes

    def __post_init__(self) -> None:
        if self.kind not in (b"a", b"n", b"b", b"i", b"f", b"s", b"y", b"d"):
            raise ValueError("unsupported scalar kind")
        _length(self.byte_length)
        if len(self.byte_root) != 32:
            raise ValueError("scalar byte root must be a SHA-256 fold digest")
        if (
            (self.kind in (b"a", b"n") and self.byte_length != 0)
            or (self.kind == b"b" and self.byte_length != 1)
            or (self.kind == b"f" and self.byte_length != 8)
        ):
            raise ValueError("scalar kind has an invalid payload length")

    def encode(self) -> bytes:
        return self.kind + _length(self.byte_length) + self.byte_root


def scalar_payload(value: Scalar) -> tuple[bytes, bytes]:
    """Exact scalar payload vocabulary, with no Unicode or numeric rounding."""
    if value is ABSENT:
        return b"a", b""
    if value is None:
        return b"n", b""
    if type(value) is bool:
        return b"b", bytes((int(value),))
    if type(value) is int:
        return b"i", str(value).encode("ascii")
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("PDF record binary64 must be finite")
        return b"f", struct.pack(">d", value)
    if type(value) is str:
        return b"s", value.encode("utf-8")
    if type(value) is bytes:
        return b"y", value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("PDF record decimal must be finite")
        parts = value.as_tuple()
        digits = "".join(str(digit) for digit in parts.digits)
        return b"d", f"{parts.sign}:{digits}:{parts.exponent}".encode("ascii")
    raise TypeError(f"unsupported PDF record scalar: {type(value).__name__}")


def describe_scalar(value: Scalar) -> ScalarDescriptor:
    if type(value) is str:
        # At most 16K codepoints/64K UTF-8 bytes are encoded at once. The
        # materializing scalar_payload helper remains explicit, not this path.
        size = BLOCK_BYTES // 4
        length, root = byte_root(
            value[offset : offset + size].encode("utf-8") for offset in range(0, len(value), size)
        )
        return ScalarDescriptor(b"s", length, root)
    kind, payload = scalar_payload(value)
    length, root = byte_root((payload,))
    return ScalarDescriptor(kind, length, root)


def canonical_scalar(value: Scalar | ScalarDescriptor) -> bytes:
    return (value if isinstance(value, ScalarDescriptor) else describe_scalar(value)).encode()


def record_frame(
    schema_id: str,
    family: str,
    key: str,
    fields: Iterable[tuple[str, Scalar | ScalarDescriptor]],
) -> bytes:
    """Encode one fixed-family record in its declared field order."""
    if not schema_id or not family or not key:
        raise ValueError("record requires schema, family and qualified logical key")
    body = bytearray(
        frame(b"s", schema_id.encode("utf-8"))
        + frame(b"f", family.encode("utf-8"))
        + frame(b"k", key.encode("utf-8"))
    )
    count = 0
    seen: set[str] = set()
    # Field lists are fixed by schema, unlike unbounded collection membership rows.
    for name, value in fields:
        if not name or name in seen:
            raise ValueError("record fields must be named and unique")
        seen.add(name)
        body.extend(frame(b"n", name.encode("utf-8")))
        body.extend(canonical_scalar(value))
        count += 1
        if len(body) + 8 > MAX_FRAME_BYTES - 9:
            raise ValueError("record frame exceeds 64 KiB; lower collections into rows")
    if len(body) + 17 > MAX_FRAME_BYTES:
        raise ValueError("record frame exceeds 64 KiB")
    return frame(b"R", _length(count) + bytes(body))


@dataclass(frozen=True, slots=True)
class LogicalPin:
    schema_id: str
    release_id: str
    source_digest: str
    logical_digest: str
    protocol: str = PROTOCOL

    def __post_init__(self) -> None:
        if self.protocol != PROTOCOL or not self.schema_id or not self.release_id:
            raise ValueError("logical pin requires supported protocol, schema and release")
        if not _HEX.fullmatch(self.source_digest) or not _HEX.fullmatch(self.logical_digest):
            raise ValueError("logical pin requires qualified source and logical digests")

    def require_context(self, *, schema_id: str, release_id: str, source_digest: str) -> None:
        if (self.schema_id, self.release_id, self.source_digest) != (
            schema_id,
            release_id,
            source_digest,
        ):
            raise ValueError("logical pin schema/release/source differs")


class LogicalIdentity:
    """Streaming ordered records, qualified by schema, semantic release and source."""

    def __init__(self, schema_id: str, release_id: str, source_digest: str) -> None:
        LogicalPin(schema_id, release_id, source_digest, "0" * 64)
        self.schema_id, self.release_id, self.source_digest = schema_id, release_id, source_digest
        self._fold = IdentityFold("records")
        self._fold.add(
            record_frame(
                schema_id,
                "@context",
                "@context",
                (("protocol", PROTOCOL), ("release", release_id), ("source", source_digest)),
            )
        )
        self._previous: tuple[bytes, bytes] | None = None

    def add_record(
        self,
        family: str,
        key: str,
        fields: Iterable[tuple[str, Scalar | ScalarDescriptor]],
    ) -> None:
        order = family.encode("utf-8"), key.encode("utf-8")
        if self._previous is not None and order <= self._previous:
            raise ValueError("records must be unique in UTF-8 binary (family,key) order")
        encoded = record_frame(self.schema_id, family, key, fields)
        self._fold.add(encoded)
        self._previous = order

    def pin(self) -> LogicalPin:
        return LogicalPin(
            self.schema_id, self.release_id, self.source_digest, self._fold.digest().hex()
        )


@dataclass(frozen=True, slots=True)
class ArtifactPart:
    stream_id: str
    ordinal: int
    offset: int
    byte_length: int
    body: bytes
    sha256_digest: str

    def verify(self) -> None:
        _length(self.ordinal)
        _length(self.offset)
        if not self.stream_id or not 0 < self.byte_length <= BLOCK_BYTES:
            raise ValueError("artifact part requires stream identity and bounded nonempty bytes")
        if (
            self.byte_length != len(self.body)
            or sha256(self.body).hexdigest() != self.sha256_digest
        ):
            raise ValueError("artifact part actual bytes differ from length/digest")


@dataclass(frozen=True, slots=True)
class ArtifactPin:
    stream_id: str
    release_id: str
    source_digest: str
    byte_length: int
    serialization_sha256: str
    byte_root: bytes

    def __post_init__(self) -> None:
        if not self.stream_id or not self.release_id:
            raise ValueError("artifact pin requires stream and release")
        _length(self.byte_length)
        if not _HEX.fullmatch(self.source_digest) or not _HEX.fullmatch(self.serialization_sha256):
            raise ValueError("artifact pin requires source and exact serialization SHA-256")
        if len(self.byte_root) != 32:
            raise ValueError("artifact pin requires byte fold root")

    def scalar(self, kind: bytes) -> ScalarDescriptor:
        return ScalarDescriptor(kind, self.byte_length, self.byte_root)


def replay_artifact(
    parts: Iterable[ArtifactPart],
    pin: ArtifactPin,
    *,
    release_id: str,
    source_digest: str,
    already_admitted: BinaryIO | None = None,
) -> Iterator[bytes]:
    """Verify actual contiguous bytes while replaying; exhaust to establish success.

    ``already_admitted`` compares every actual part directly with retained bytes.
    Its stream starts at the admitted artifact's beginning. A digest alone is not
    correspondence evidence. Duplicate rows, including equal duplicates, refuse;
    replay/idempotency of a submitted *part* is handled by ``same_part``.
    """
    if (pin.release_id, pin.source_digest) != (release_id, source_digest):
        raise ValueError("artifact release/source pin differs")
    standard = sha256()
    ordinal = 0
    offset = 0

    def read_exact(source: BinaryIO, length: int) -> bytes:
        result = bytearray()
        while len(result) < length:
            chunk = source.read(length - len(result))
            if not chunk:
                break
            result.extend(chunk)
        return bytes(result)

    def verified() -> Iterator[bytes]:
        nonlocal ordinal, offset
        for part in parts:
            part.verify()
            if (part.stream_id, part.ordinal, part.offset) != (pin.stream_id, ordinal, offset):
                raise ValueError("artifact parts must be one contiguous ordered stream")
            if (
                already_admitted is not None
                and read_exact(already_admitted, part.byte_length) != part.body
            ):
                raise ValueError("artifact bytes differ from already-admitted retained bytes")
            standard.update(part.body)
            ordinal += 1
            offset += part.byte_length
            yield part.body

    folded = IdentityFold("bytes")
    for block in canonical_blocks(verified()):
        folded.add(block)
        yield block
    if already_admitted is not None and already_admitted.read(1):
        raise ValueError("already-admitted retained bytes have a trailing suffix")
    if (
        offset != pin.byte_length
        or standard.hexdigest() != pin.serialization_sha256
        or folded.digest() != pin.byte_root
    ):
        raise ValueError("artifact inventory, exact SHA-256 or byte root differs")


def same_part(admitted: ArtifactPart, submitted: ArtifactPart) -> bool:
    """An exact retry is idempotent; conflicting duplicate keys always refuse."""
    admitted.verify()
    submitted.verify()
    if (admitted.stream_id, admitted.ordinal) != (submitted.stream_id, submitted.ordinal):
        raise ValueError("part retry must address the admitted stream/ordinal")
    if admitted != submitted:
        raise ValueError("conflicting artifact part retry")
    return True
