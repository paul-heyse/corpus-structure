"""Model-derived, lossless page payloads in self-contained Arrow IPC streams.

The application JSON Schema owns field meaning. This finite realization preserves supplied
fields and Python integer/binary64 kinds rather than normalizing them during Arrow conversion.
Buffer validity and schema validation remain separate from OCR/coverage domain validation.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from importlib.resources import files
from typing import Any, NoReturn

import pyarrow as pa
import yaml
from jsonschema.validators import validator_for
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from .identity import canonical_bytes

_DECLARATION = yaml.safe_load(
    files("corpus_structure").joinpath("model/semantic/pdf-payloads.yaml").read_bytes()
)["annotations"]
PROFILE: str = _DECLARATION["pdp:codec"]
CLASS_NAME: str = _DECLARATION["pdp:logical_class"]
FAMILY: str = _DECLARATION["pdp:family"]
_LOGICAL_IDENTITY = _DECLARATION["pdp:logical_identity_profile"].encode() + b"\0"
_PRESENCE = "__present"


class PayloadContractError(ValueError):
    """Located payload or interpretation mismatch; never silently omitted content."""


def _error(path: str, message: str) -> NoReturn:
    raise PayloadContractError(f"{path}: {message}")


def _resolve(schema, root):
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"):
            _error(ref, "only retained local definition references are supported")
        return root["$defs"][ref.removeprefix("#/$defs/")]
    return schema


def _arrow_type(schema, root, path):
    schema = _resolve(schema, root)
    kind = schema.get("type")
    if kind == "object":
        props = schema.get("properties", {})
        if _PRESENCE in props or schema.get("additionalProperties") is not False:
            _error(path, "payload objects require declared fields without extensions")
        return pa.struct(
            [
                pa.field(_PRESENCE, pa.binary((len(props) + 7) // 8), nullable=False),
                *(
                    pa.field(name, _arrow_type(child, root, path + "/" + name), nullable=True)
                    for name, child in props.items()
                ),
            ]
        )
    if kind == "array":
        return pa.large_list(
            pa.field("item", _arrow_type(schema["items"], root, path + "/*"), nullable=False)
        )
    if kind == "number":
        return pa.struct(
            [
                pa.field("kind", pa.int8(), nullable=False),
                pa.field("integer", pa.int64()),
                pa.field("binary64", pa.float64()),
            ]
        )
    types = {
        "integer": pa.int64(),
        "string": pa.large_string(),
        "boolean": pa.bool_(),
        "null": pa.null(),
    }
    if kind not in types:
        _error(path, f"unsupported schema type {kind!r}; update the finite payload mapping")
    return types[kind]


def _to_arrow(value, schema, root, path):
    schema = _resolve(schema, root)
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, dict):
            _error(path, "expected an object")
        props = schema["properties"]
        if value.keys() - props.keys():
            _error(path, "undeclared object field")
        presence = bytearray((len(props) + 7) // 8)
        result = {}
        for index, (name, child) in enumerate(props.items()):
            if name in value:
                presence[index // 8] |= 1 << (index % 8)
                result[name] = _to_arrow(value[name], child, root, path + "/" + name)
            else:
                result[name] = None
        result[_PRESENCE] = bytes(presence)
        return result
    if kind == "array":
        if not isinstance(value, list):
            _error(path, "expected a list")
        return [
            _to_arrow(item, schema["items"], root, f"{path}/{i}") for i, item in enumerate(value)
        ]
    if kind in {"integer", "number"}:
        if type(value) is int:
            if not -(2**63) <= value < 2**63:
                _error(path, "integer exceeds the declared signed64 transport profile")
            return {"kind": 0, "integer": value, "binary64": None} if kind == "number" else value
        if kind == "number" and type(value) is float and math.isfinite(value):
            return {"kind": 1, "integer": None, "binary64": value}
        _error(path, "expected finite integer/binary64 value without coercion")
    expected = {"boolean": bool, "string": str, "null": type(None)}[kind]
    if type(value) is not expected:
        _error(path, f"expected {kind} without coercion")
    return value


def _from_arrow(value, schema, root, path):
    schema = _resolve(schema, root)
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, dict):
            _error(path, "null object")
        props = schema["properties"]
        mask = value.get(_PRESENCE)
        if not isinstance(mask, bytes) or len(mask) != (len(props) + 7) // 8:
            _error(path, "invalid object presence bitmap")
        if mask and len(props) % 8 and mask[-1] >> (len(props) % 8):
            _error(path, "unknown supplied field bits")
        result = {}
        for index, (name, child) in enumerate(props.items()):
            if mask[index // 8] & (1 << (index % 8)):
                result[name] = _from_arrow(value[name], child, root, path + "/" + name)
            elif value[name] is not None:
                _error(path + "/" + name, "absent field has a physical value")
        return result
    if kind == "array":
        if not isinstance(value, list):
            _error(path, "null list")
        return [
            _from_arrow(item, schema["items"], root, f"{path}/{i}") for i, item in enumerate(value)
        ]
    if kind == "number":
        if not isinstance(value, dict):
            _error(path, "null numeric representation")
        if value["kind"] == 0 and value["integer"] is not None and value["binary64"] is None:
            return value["integer"]
        if (
            value["kind"] == 1
            and value["integer"] is None
            and value["binary64"] is not None
            and math.isfinite(value["binary64"])
        ):
            return value["binary64"]
        _error(path, "invalid numeric kind/value correspondence")
    return value


def _canonical_scalar(value, schema, root, path):
    """Yield canonical logical JSON directly from Arrow, without a page object graph."""
    schema = _resolve(schema, root)
    kind = schema.get("type")
    if kind == "object":
        if not value.is_valid:
            _error(path, "null object")
        props = schema["properties"]
        mask = value[_PRESENCE].as_py()
        if not isinstance(mask, bytes) or len(mask) != (len(props) + 7) // 8:
            _error(path, "invalid object presence bitmap")
        if mask and len(props) % 8 and mask[-1] >> (len(props) % 8):
            _error(path, "unknown supplied field bits")
        yield b"{"
        first = True
        for index, (name, child) in enumerate(props.items()):
            if mask[index // 8] & (1 << (index % 8)):
                if not first:
                    yield b","
                first = False
                yield json.dumps(name, ensure_ascii=False).encode()
                yield b":"
                yield from _canonical_scalar(value[name], child, root, path + "/" + name)
            elif value[name].is_valid:
                _error(path + "/" + name, "absent field has a physical value")
        yield b"}"
    elif kind == "array":
        if not value.is_valid:
            _error(path, "null list")
        yield b"["
        for index, item in enumerate(value.values):
            if index:
                yield b","
            yield from _canonical_scalar(item, schema["items"], root, f"{path}/{index}")
        yield b"]"
    else:
        logical = _from_arrow(value.as_py(), schema, root, path)
        yield json.dumps(
            logical, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        ).encode()


@dataclass(frozen=True)
class EncodedPagePayload:
    content: bytes
    schema_digest: str
    logical_digest: str
    page_no: int


@dataclass(frozen=True)
class PreparedPayloadFamily:
    json_schema: Mapping[str, Any]
    arrow_schema: pa.Schema
    schema_digest: str
    validator: Any

    def _validated_row(self, value: Mapping[str, Any]) -> dict[str, Any]:
        errors = sorted(
            self.validator.iter_errors(value), key=lambda e: tuple(map(str, e.absolute_path))
        )
        if errors:
            error = errors[0]
            _error("#/" + "/".join(map(str, error.absolute_path)), error.message)
        # Strict type/finite checks are not supplied by JSON Schema's integer/number tests.
        row = _to_arrow(value, self.json_schema, self.json_schema, "#")
        if not isinstance(row, dict):
            _error("#", "page payload requires an object")
        return row

    def validate(self, value: Mapping[str, Any]) -> None:
        self._validated_row(value)

    def logical_digest(self, value: Mapping[str, Any]) -> str:
        self.validate(value)
        return sha256(
            _LOGICAL_IDENTITY + self.schema_digest.encode() + b"\0" + canonical_bytes(value)
        ).hexdigest()

    def batch(self, value: Mapping[str, Any]) -> pa.RecordBatch:
        row = self._validated_row(value)
        batch = pa.RecordBatch.from_pylist([row], schema=self.arrow_schema)
        batch.validate(full=True)
        return batch

    def encode(self, value: Mapping[str, Any], *, compression: str | None = None) -> bytes:
        sink = pa.BufferOutputStream()
        with pa.ipc.new_stream(
            sink, self.arrow_schema, options=pa.ipc.IpcWriteOptions(compression=compression)
        ) as writer:
            writer.write_batch(self.batch(value))
        return sink.getvalue().to_pybytes()

    def read_batch(
        self, payload: bytes, *, schema_digest: str | None = None, logical_digest: str | None = None
    ) -> pa.RecordBatch:
        """Return owning Arrow buffers after framing, schema and optional identity checks.

        This physical reader does not reconstruct domain mappings. Full JSON Schema and
        cross-field admission remain the publication/``decode`` boundary's responsibility.
        """
        if schema_digest is not None and schema_digest != self.schema_digest:
            _error("#", "payload schema binding differs")
        source = pa.BufferReader(payload)
        try:
            # Page-local reads share existing admission; do not add Arrow decompression workers.
            with pa.ipc.open_stream(
                source, options=pa.ipc.IpcReadOptions(use_threads=False)
            ) as reader:
                if not reader.schema.equals(self.arrow_schema, check_metadata=True):
                    _error("#", "IPC schema/profile differs")
                page_batch = None
                for batch in reader:
                    batch.validate(full=True)
                    if batch.num_rows > 1 or (page_batch is not None and batch.num_rows):
                        _error("#", "page payload requires exactly one logical page")
                    if batch.num_rows:
                        page_batch = batch
            if source.tell() != len(payload):
                _error("#", "trailing bytes outside IPC stream")
        except (pa.ArrowInvalid, pa.ArrowTypeError) as error:
            raise PayloadContractError(f"#: invalid IPC payload: {error}") from error
        if page_batch is None:
            _error("#", "page payload requires exactly one logical page")
        if logical_digest is not None:
            digest = sha256(_LOGICAL_IDENTITY + self.schema_digest.encode() + b"\0")
            # A StructScalar keeps nested lists/structs in Arrow until each scalar is needed.
            row = pa.StructArray.from_arrays(
                list(page_batch.columns), fields=list(page_batch.schema)
            )[0]
            for chunk in _canonical_scalar(row, self.json_schema, self.json_schema, "#"):
                digest.update(chunk)
            if digest.hexdigest() != logical_digest:
                _error("#", "payload logical digest differs")
        return page_batch

    def decode(
        self, payload: bytes, *, schema_digest: str | None = None, logical_digest: str | None = None
    ) -> dict[str, Any]:
        batch = self.read_batch(payload, schema_digest=schema_digest, logical_digest=logical_digest)
        value = _from_arrow(batch.to_pylist()[0], self.json_schema, self.json_schema, "#")
        if not isinstance(value, dict):
            _error("#", "page payload requires an object")
        self.validate(value)
        return value


@lru_cache(maxsize=32)
def _schema_validator(schema_json: bytes):
    schema = schema_load(schema_json)
    cls = validator_for(schema)
    cls.check_schema(schema)
    registry = Registry().with_resource(
        "urn:corpus:pdf-page-payload",
        Resource.from_contents(schema, default_specification=DRAFT202012),
    )
    return cls(schema, registry=registry)


def prepare_schema_validator(schema: Mapping[str, Any]):
    """Reuse a checked, local-only validator for a captured released JSON Schema."""
    return _schema_validator(schema_dump(schema))


@lru_cache(maxsize=16)
def _prepare(schema_json: bytes) -> PreparedPayloadFamily:
    schema = schema_load(schema_json)
    validator = _schema_validator(schema_json)
    digest = sha256(schema_json).hexdigest()
    struct = _arrow_type(schema, schema, "#")
    arrow = pa.schema(
        list(struct),
        metadata={"payload_profile": PROFILE, "logical_class": CLASS_NAME, "schema_digest": digest},
    )
    return PreparedPayloadFamily(schema, arrow, digest, validator)


def schema_dump(schema: Mapping[str, Any]) -> bytes:
    """Retain schema mappings and exact Decimal constraints in a stable JSON envelope.

    The tagged Decimal representation is an internal capture format, decoded before
    JSON Schema interpretation; Decimal constraints are never coerced to strings/floats.
    """
    from decimal import Decimal

    def decimal(value):
        if isinstance(value, Decimal):
            return {"__schema_decimal__": str(value)}
        raise TypeError(f"unsupported schema value: {type(value).__name__}")

    return json.dumps(schema, sort_keys=True, separators=(",", ":"), default=decimal).encode()


def schema_load(payload: bytes | str) -> dict[str, Any]:
    """Restore a captured schema or schema collection before validator preparation."""
    from decimal import Decimal

    value = json.loads(
        payload,
        object_hook=lambda value: (
            Decimal(value["__schema_decimal__"]) if set(value) == {"__schema_decimal__"} else value
        ),
    )
    if not isinstance(value, dict):
        raise ValueError("captured schema must be an object")
    return value


def prepare_payload_schema(schema: Mapping[str, Any]) -> PreparedPayloadFamily:
    """Prepare the exact released schema captured for a DB-free validation child."""
    return _prepare(schema_dump(schema))


def prepare_payload_family(context=None) -> PreparedPayloadFamily:
    if context is None:
        from .contracts import trusted_execution_inputs
        from .pdf_contracts import _boundary

        # The codec consumes the logical boundary only. Unrelated execution grammar/
        # transformer compilation is neither its input nor a prerequisite for IPC work.
        boundary = _boundary(trusted_execution_inputs().schema)
        return prepare_payload_schema(boundary.json_schema(CLASS_NAME))
    return prepare_payload_schema(context.boundary.json_schema(CLASS_NAME))


def encode_page_payload(
    value: Mapping[str, Any], context=None, *, compression: str | None = None
) -> EncodedPagePayload:
    family = prepare_payload_family(context)
    return EncodedPagePayload(
        family.encode(value, compression=compression),
        family.schema_digest,
        family.logical_digest(value),
        value["page_no"],
    )


def decode_page_payload(
    payload: bytes,
    context=None,
    *,
    schema_digest: str | None = None,
    logical_digest: str | None = None,
) -> dict[str, Any]:
    return prepare_payload_family(context).decode(
        payload, schema_digest=schema_digest, logical_digest=logical_digest
    )


def page_payload_batches(
    payload: bytes,
    context=None,
    *,
    schema_digest: str | None = None,
    logical_digest: str | None = None,
    columns: Sequence[str] | None = None,
) -> Iterator[pa.RecordBatch]:
    family = prepare_payload_family(context)
    batch = family.read_batch(payload, schema_digest=schema_digest, logical_digest=logical_digest)
    yield batch.select(columns) if columns is not None else batch
