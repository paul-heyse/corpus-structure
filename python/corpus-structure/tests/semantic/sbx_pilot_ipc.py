"""Bounded raw IPC framing for the SBX transport comparison."""

import json
import struct
from hashlib import sha256

import pyarrow as pa

from corpus_structure.semantic.identity import canonical_bytes

_PREFIX = struct.Struct("!8sIQ")
_MAGIC = b"SBXIPC01"
_MAX_HEADER = 65536


def encode_arrow_frame(table: pa.Table, projection_id: str) -> bytes:
    table.validate(full=True)
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    payload = sink.getvalue().to_pybytes()
    header = canonical_bytes(
        {
            "projection": projection_id,
            "schema": sha256(table.schema.serialize().to_pybytes()).hexdigest(),
            "payload": sha256(payload).hexdigest(),
        }
    )
    return _PREFIX.pack(_MAGIC, len(header), len(payload)) + header + payload


def decode_arrow_frame(
    content: bytes, *, expected_projection: str, expected_schema: pa.Schema
) -> pa.Table:
    if len(content) < _PREFIX.size:
        raise ValueError("truncated IPC frame")
    magic, header_size, payload_size = _PREFIX.unpack_from(content)
    if magic != _MAGIC or not 0 < header_size <= _MAX_HEADER:
        raise ValueError("invalid IPC frame header")
    if len(content) != _PREFIX.size + header_size + payload_size:
        raise ValueError("IPC frame length differs")
    header_start = _PREFIX.size
    payload_start = header_start + header_size
    header = json.loads(content[header_start:payload_start])
    payload = content[payload_start:]
    expected = {
        "projection": expected_projection,
        "schema": sha256(expected_schema.serialize().to_pybytes()).hexdigest(),
        "payload": sha256(payload).hexdigest(),
    }
    if header != expected:
        raise ValueError("IPC projection, schema or payload differs")
    source = pa.BufferReader(payload)
    try:
        with pa.ipc.open_stream(source) as reader:
            if not reader.schema.equals(expected_schema, check_metadata=True):
                raise ValueError("IPC schema differs from admitted projection")
            table = reader.read_all()
        if source.tell() != payload_size:
            raise ValueError("IPC payload has trailing bytes")
        table.validate(full=True)
    except pa.ArrowException as error:
        raise ValueError("invalid IPC payload") from error
    return table
