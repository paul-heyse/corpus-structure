"""Lossless, schema-qualified native PDF records.

Docling owns admitted field meanings. This adapter lowers that exact retained schema into
fixed document/object/membership/reference families, with finite scalar/structure payloads.
It never constructs a DoclingDocument on ordinary lowering or selective record reads.
Full native reconstruction and upstream callback validation are explicit caller requests.
Physical custody and frozen-union admission belong to the publication boundary.
"""

from __future__ import annotations

import copy
import json
import math
import struct
from collections.abc import Callable, Generator, Iterable, Iterator, Mapping
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from typing import TYPE_CHECKING, Any, Literal, Protocol

from jsonschema.validators import validator_for
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from .pdf_record_identity import ScalarDescriptor, canonical_scalar, scalar_payload

if TYPE_CHECKING:
    from docling_core.types.doc import DoclingDocument


@lru_cache(maxsize=4)
def _record_model(content: bytes) -> Mapping[str, Any]:
    import yaml

    return yaml.safe_load(content)


def _default_record_model() -> Mapping[str, Any]:
    from corpus_structure.model.compiled import model_source

    return _record_model(model_source("pdf-records.yaml"))


def _default_record_header() -> tuple[str, str]:
    fields = _default_record_model()["classes"]["PdfRecordDocument"]["attributes"]
    return (
        str(fields["contract_version"]["equals_string"]),
        str(fields["mapping_profile"]["equals_string"]),
    )


MAX_RECORD_BYTES = 65_536
# JSONB renders whitespace and escapes; leave room for its physical projection.
INLINE_SCALAR_BYTES = 512


class NativeMappingError(ValueError):
    """A precise retained-schema/native-address diagnostic, never an omitted value."""

    def __init__(
        self,
        path: str,
        message: str,
        *,
        capture=None,
        code="native_mapping_invalid",
        category="invalid_input",
        schema_path=None,
    ):
        from .correction_detail import BoundaryDiagnostic

        self.validation_capture = capture
        self.path = path
        self.boundary_diagnostic = BoundaryDiagnostic(
            code,
            category,
            "Native boundary constraint failed: " + code,
            getattr(path, "segments", () if path == "#" else None),
            schema_path,
            getattr(path, "locator", None if path.startswith("#") else path),
        )
        super().__init__(f"{path}: {message}")


@dataclass(frozen=True, slots=True)
class NativeRow:
    kind: str
    values: Mapping[str, Any]

    def physical_values(self) -> dict[str, Any]:
        """Decode declared JSON wire fields for SQLAlchemy JSONB/native boundary admission."""
        result = dict(self.values)
        for name in ("scalars_json", "structure_json", "scalar_json"):
            if name in result:
                result[name] = json.loads(result[name])
        return result


class ScalarWriter(Protocol):
    def __call__(
        self, stream_id: str, encoding_profile: str, chunks: Iterable[bytes], /
    ) -> ScalarDescriptor: ...


class NativeRecordReader(Protocol):
    """Selective immutable reader; implementations retain qualification in their query scope."""

    def record(self, record_id: str) -> Mapping[str, Any]: ...

    def members(self, parent_id: str, field_name: str) -> Iterable[Mapping[str, Any]]: ...

    def scalar(self, stream_id: str, /) -> Iterable[bytes]: ...


class AcquiredNativeDocumentRows:
    """Index one ordered native population for the shared reconstruction."""

    def __init__(
        self,
        records: Iterable[Mapping[str, Any]],
        memberships: Iterable[Mapping[str, Any]],
        scalar: Callable[[str], Iterable[bytes]],
    ):
        self._records: dict[str, Mapping[str, Any]] = {}
        self._memberships: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
        self.scalar = scalar
        for row in records:
            record_id = row["record_id"]
            if record_id in self._records:
                raise ValueError("duplicate native reconstruction record")
            self._records[record_id] = row
        for row in memberships:
            address = (row["parent_id"], row["field_name"])
            if row["parent_id"] not in self._records:
                raise ValueError("native membership parent is absent")
            self._memberships.setdefault(address, []).append(row)

    def record(self, record_id: str) -> Mapping[str, Any]:
        try:
            return self._records[record_id]
        except KeyError as error:
            raise ValueError("native reconstruction record is absent") from error

    def members(self, parent_id: str, field_name: str) -> Iterable[Mapping[str, Any]]:
        return self._memberships.get((parent_id, field_name), ())


@dataclass(frozen=True)
class NativeSchemaMapping:
    schema_bytes: bytes
    schema: Mapping[str, Any]
    validator: Any
    locations: Mapping[int, str]

    @property
    def digest(self) -> str:
        return sha256(self.schema_bytes).hexdigest()

    def resolve(self, schema: Mapping[str, Any], value: Any, path: str):
        """Select the declared native union, retaining its exact definition path."""
        schema_path = self.locations.get(id(schema), "#")
        while True:
            ref = schema.get("$ref")
            if ref is not None:
                if not ref.startswith("#/$defs/") or ref[8:] not in self.schema["$defs"]:
                    raise NativeMappingError(
                        path,
                        "unsupported native schema reference " + ref,
                        code="native_reference_profile",
                        category="unassessed",
                        schema_path=ref,
                    )
                schema_path = ref
                schema = self.schema["$defs"][ref[8:]]
                continue
            choices = schema.get("oneOf", schema.get("anyOf"))
            if choices is not None:
                match = next(
                    (s for s in choices if self.validator.evolve(schema=s).is_valid(value)), None
                )
                if match is None:
                    raise NativeMappingError(path, "no supported native union member")
                # anyOf RichTableCell precedes TableCell: rich cells retain their ref.
                schema = match
                schema_path = self.locations.get(id(schema), schema_path)
                continue
            return schema, schema_path

    def validate(self, value: Any, *, detail=False, max_errors=100) -> None:
        from .correction_detail import capture_json_errors

        capture = capture_json_errors(self.validator, value, detail=detail, max_errors=max_errors)
        error = capture.errors[0] if capture.errors else None
        if error is not None:
            path = "#" + "".join("/" + _escape(str(p)) for p in error.absolute_path)
            raise NativeMappingError(path, error.message, capture=capture) from error
        _finite_json(value, "#")


def native_validation_contract() -> Mapping[str, Any]:
    """Read the semantic owner's placement and opaque-extension interpretation contract."""
    return json.loads(_default_record_model()["annotations"]["pdr:native_validation_contract"])


def native_schema_bytes() -> bytes:
    from corpus_structure.model.compiled import model_source

    return model_source("docling-validation.schema.json")


def _difference(expected: Any, actual: Any, path: str = "#") -> str | None:
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in expected.keys() | actual.keys():
            if key not in expected or key not in actual:
                return path + "/" + _escape(key)
            changed = _difference(expected[key], actual[key], path + "/" + _escape(key))
            if changed:
                return changed
        return None
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return path
        for i, (left, right) in enumerate(zip(expected, actual, strict=True)):
            changed = _difference(left, right, f"{path}/{i}")
            if changed:
                return changed
        return None
    if type(expected) is not type(actual):
        return path
    if type(expected) is float:
        return None if struct.pack(">d", expected) == struct.pack(">d", actual) else path
    return None if expected == actual else path


@lru_cache(maxsize=8)
def prepare_native_schema_mapping(
    schema_bytes: bytes | None = None, *, allow_archived_default: bool = False
) -> NativeSchemaMapping:
    """Prepare the pinned schema; drift requires an explicit lowering update."""
    retained = native_schema_bytes() if schema_bytes is None else schema_bytes
    schema = json.loads(retained)
    baseline = json.loads(native_schema_bytes())
    if (
        allow_archived_default
        and schema.get("properties", {}).get("version", {}).get("default") == "1.10.0"
    ):
        # Core 2.105.0 and 2.106.0 share all lowering shapes. The only released
        # schema delta is this root default. Retain the producer's schema bytes.
        baseline["properties"]["version"]["default"] = "1.10.0"
    changed = _difference(baseline, schema)
    if changed:
        raise NativeMappingError(
            changed, "unsupported native schema change; update native lowering"
        )
    return _prepared_native_schema_mapping(retained)


@lru_cache(maxsize=8)
def _prepared_native_schema_mapping(retained: bytes) -> NativeSchemaMapping:
    """Realize schema bytes whose lowering compatibility was checked at acquisition."""
    schema = json.loads(retained)
    cls = validator_for(schema)
    cls.check_schema(schema)
    resource = Resource.from_contents(schema, default_specification=DRAFT202012)
    registry = Registry().with_resource("urn:corpus:pdf-native-schema", resource)
    locations: dict[int, str] = {}

    def index(value, path):
        if isinstance(value, dict):
            locations[id(value)] = path
            for key, item in value.items():
                index(item, path + "/" + _escape(key))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                index(item, path + "/" + str(i))

    index(schema, "#")
    return NativeSchemaMapping(retained, schema, cls(schema, registry=registry), locations)


def _escape(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":"))


def _inline_value(value: Any) -> Any:
    # JSONB numeric normalization cannot preserve binary64 signed zero or numeric JSON kind.
    return {"native_float64": struct.pack(">d", value).hex()} if type(value) is float else value


def _parse_inline(value: Any) -> Any:
    return (
        struct.unpack(">d", bytes.fromhex(value["native_float64"]))[0]
        if isinstance(value, dict)
        else value
    )


def _finite_json(value: Any, path: str) -> None:
    from .correction_detail import InputPath, child_path

    if not isinstance(path, InputPath):
        path = InputPath((), display=path, locator=path if path != "#" else None)
    if isinstance(value, dict):
        for key, member in value.items():
            if not isinstance(key, str):
                raise NativeMappingError(path, "native JSON object keys must be strings")
            _finite_json(member, child_path(path, key))
    elif isinstance(value, list):
        for i, member in enumerate(value):
            _finite_json(member, child_path(path, i))
    elif type(value) is float and not math.isfinite(value):
        raise NativeMappingError(
            path, "native JSON numbers must be finite", code="native_number_nonfinite"
        )
    elif value is not None and type(value) not in (str, int, float, bool):
        raise NativeMappingError(path, "unsupported non-JSON native value")


class _ExtraFields(Mapping[str, Any]):
    def __init__(self, value: Mapping[str, Any], declared: Mapping[str, Any]):
        self.value, self.declared = value, declared

    def __iter__(self):
        return (key for key in self.value if key not in self.declared)

    def __len__(self):
        return sum(1 for _ in self)

    def __getitem__(self, key):
        if key in self.declared:
            raise KeyError(key)
        return self.value[key]


def _json_chunks(value: Any) -> Iterator[bytes]:
    # Opaque native extension bytes preserve encountered member order. They are not a generic
    # semantic object canonicalizer. Escape bounded string slices rather than JSONEncoder's
    # potentially enormous single-token string allocation; no inventory sort/copy is required.
    if isinstance(value, str):
        yield b'"'
        for start in range(0, len(value), 4096):
            yield json.dumps(value[start : start + 4096], ensure_ascii=True)[1:-1].encode("ascii")
        yield b'"'
    elif isinstance(value, Mapping):
        yield b"{"
        first = True
        for key in value:
            if not first:
                yield b","
            yield from _json_chunks(key)
            yield b":"
            yield from _json_chunks(value[key])
            first = False
        yield b"}"
    elif isinstance(value, list):
        yield b"["
        for index, item in enumerate(value):
            if index:
                yield b","
            yield from _json_chunks(item)
        yield b"]"
    else:
        yield _json(value).encode("ascii")


def _raw_chunks(value: Any) -> tuple[bytes, Iterable[bytes]]:
    if isinstance(value, str):
        return b"s", (value[i : i + 8192].encode("utf-8") for i in range(0, len(value), 8192))
    kind, payload = scalar_payload(value)
    return kind, (payload,)


def _family(name: str) -> str:
    if name == "DoclingDocument":
        return "header"
    if name == "PageItem":
        return "page"
    if name in {"ProvenanceItem", "BoundingBox", "TrackSource"}:
        return "provenance"
    if name in {"TableCell", "RichTableCell", "GraphCell"}:
        return "cell"
    if name in {"TableData", "GraphData", "GraphLink"}:
        return "table"
    if name in {"RefItem", "FineRef"}:
        return "reference"
    if name.endswith("Item") or name in {"ListGroup", "InlineGroup"}:
        return "node"
    return "detail"


def iter_native_records(
    document: Mapping[str, Any],
    *,
    product_id: str | None = None,
    revision_id: str | None = None,
    release_id: str | None = None,
    source_digest: str,
    record_id_for: Callable[[str, str], str],
    write_scalar: ScalarWriter,
    mapping: NativeSchemaMapping | None = None,
    record_header: tuple[str, str] | None = None,
    native_type: str = "DoclingDocument",
    native_address: str = "#",
    detail: bool = False,
    max_errors: int = 100,
) -> Iterator[NativeRow]:
    """Lower native values without constructing or normalizing a DoclingDocument.

    The producer supplies stable source-occurrence IDs before batching. An address is supplied
    to that allocator as a locator, never used as an implicit logical ID or citation. This
    iterator emits each record once; delivery order has no semantic significance. Native
    callbacks/global graph validity are explicit frozen-union obligations, not claimed here.
    """
    from .correction_detail import InputPath, child_path

    mapping = prepare_native_schema_mapping() if mapping is None else mapping
    contract_version, mapping_profile = (
        _default_record_header() if record_header is None else record_header
    )
    if native_type == "DoclingDocument":
        root_schema = mapping.schema
        mapping.validate(document, detail=detail, max_errors=max_errors)
    elif (
        native_type in mapping.schema["$defs"]
        and "properties" in mapping.schema["$defs"][native_type]
    ):
        root_schema = {"$ref": "#/$defs/" + native_type}
        from .correction_detail import capture_json_errors

        capture = capture_json_errors(
            mapping.validator.evolve(schema=root_schema),
            document,
            detail=detail,
            max_errors=max_errors,
        )
        if capture.errors:
            error = capture.errors[0]
            raise NativeMappingError(native_address, error.message, capture=capture) from error
        _finite_json(document, native_address)
    else:
        raise NativeMappingError(native_address, "unsupported native record class " + native_type)
    if len(source_digest) != 64 or any(c not in "0123456789abcdef" for c in source_digest):
        raise ValueError("native records require an admitted source digest")
    common = {}
    if (product_id, revision_id, release_id) != (None, None, None):
        if (
            not product_id
            or not revision_id
            or not release_id
            or "\x00" in (product_id + revision_id + release_id)
        ):
            raise ValueError("PDF physical qualification requires product, revision and release")
        common = {"product_id": product_id, "revision_id": revision_id}

    def external(owner: str, field: str, value: Any, *, opaque: bool = False):
        stream = owner + "/value/" + sha256(field.encode("utf-8")).hexdigest()
        kind, chunks = (b"y", _json_chunks(value)) if opaque else _raw_chunks(value)
        profile = "pdf-record-native-json-v1" if opaque else "pdf-record-scalar-v1:" + kind.decode()
        descriptor = write_scalar(stream, profile, chunks)
        if descriptor.kind != kind:
            raise NativeMappingError(field, "scalar writer returned a different native kind")
        return {
            "kind": "parts",
            "stream_id": stream,
            "encoding_profile": profile,
            "scalar_kind": kind.decode(),
            "byte_length": descriptor.byte_length,
            "byte_root": descriptor.byte_root.hex(),
        }

    def text_projection(owner: str, field: str, value: str):
        # Traversal paths carry diagnostic metadata only inside this lowering.
        # Published native text and caller callbacks keep their ordinary str contract.
        value = str.__str__(value)
        if (
            len(value) > INLINE_SCALAR_BYTES
            or "\x00" in value
            or len(value.encode("utf-8")) > INLINE_SCALAR_BYTES
        ):
            return None, external(owner, field, value)["stream_id"]
        return value, None

    def value_descriptor(owner: str, field: str, value: Any, *, opaque: bool = False):
        if (
            opaque
            or (isinstance(value, str) and ("\x00" in value or len(value) > INLINE_SCALAR_BYTES))
            or len(_json(value)) > INLINE_SCALAR_BYTES
        ):
            return external(owner, field, value, opaque=opaque)
        return None

    def memberships(owner: str, field: str, value: Any, schema: Mapping[str, Any], path: str):
        is_map = isinstance(value, dict)
        iterator = value.items() if is_map else enumerate(value)
        for ordinal, (key, member) in enumerate(iterator):
            member_path = child_path(path, key)
            member_schema = (
                schema["additionalProperties"]
                if is_map
                else (
                    schema.get("prefixItems", [])[key]
                    if key < len(schema.get("prefixItems", []))
                    else schema.get("items", {})
                )
            )
            selected, _ = mapping.resolve(member_schema, member, member_path)
            row = {**common, "parent_id": owner, "field_name": field, "ordinal": ordinal}
            if is_map:
                if not isinstance(key, str):
                    raise NativeMappingError(path, "native map keys must be strings")
                inline_key, key_stream = text_projection(owner, field + "/key/" + str(ordinal), key)
                if inline_key is not None:
                    row["member_key"] = inline_key
                if key_stream is not None:
                    row["member_key_stream_id"] = key_stream
            if isinstance(member, (dict, list)) and (
                "properties" in selected or selected.get("type") == "array"
            ):
                child = record_id_for(
                    str(member_path),
                    "NativeArray"
                    if isinstance(member, list)
                    else selected.get("title", "NativeObject"),
                )
                yield from object_rows(member, member_schema, member_path, child)
                row.update(value_kind="record", record_id=child)
            else:
                parts = value_descriptor(
                    owner,
                    field + "/" + str(ordinal),
                    member,
                    opaque=isinstance(member, (dict, list)),
                )
                if parts:
                    row.update(value_kind="parts", stream_id=parts["stream_id"])
                else:
                    row.update(value_kind="scalar", scalar_json=_json(_inline_value(member)))
            yield NativeRow("membership", row)

    def object_rows(value: Any, schema: Mapping[str, Any], path: str, record_id: str):
        if not record_id or "\x00" in record_id or len(record_id.encode()) > 256:
            raise NativeMappingError(path, "stable source-occurrence ID must fit 256 UTF-8 bytes")
        selected, schema_path = mapping.resolve(schema, value, path)
        synthetic_array = isinstance(value, list)
        name = "NativeArray" if synthetic_array else selected.get("title", "NativeObject")
        scalars, fields = {}, {}
        structure: dict[str, Any] = {"fields": fields, "schema_path": schema_path}
        if synthetic_array:
            fields["items"] = {"kind": "array", "length": len(value)}
            yield from memberships(record_id, "items", value, selected, path)
        else:
            declared = selected.get("properties", {})
            extras = _ExtraFields(value, declared)
            if extras and selected.get("additionalProperties") is not True:
                bad = next(iter(extras))
                raise NativeMappingError(child_path(path, bad), "unsupported native field")
            if extras:
                structure["extensions"] = external(record_id, "@extensions", extras, opaque=True)
            for field, member in value.items():
                if field not in declared:
                    continue
                member_path = child_path(path, field)
                member_schema, _ = mapping.resolve(declared[field], member, member_path)
                if isinstance(member, dict) and "properties" in member_schema:
                    child = record_id_for(
                        str(member_path), member_schema.get("title", "NativeObject")
                    )
                    fields[field] = {"kind": "object", "target": child}
                    yield from object_rows(member, declared[field], member_path, child)
                elif isinstance(member, list) and member_schema.get("type") == "array":
                    fields[field] = {"kind": "array", "length": len(member)}
                    yield from memberships(record_id, field, member, member_schema, member_path)
                elif isinstance(member, dict) and isinstance(
                    member_schema.get("additionalProperties"), dict
                ):
                    fields[field] = {"kind": "map", "length": len(member)}
                    yield from memberships(record_id, field, member, member_schema, member_path)
                else:
                    parts = value_descriptor(
                        record_id, field, member, opaque=isinstance(member, (dict, list))
                    )
                    if parts:
                        fields[field] = parts
                    else:
                        scalars[field] = _inline_value(member)
                if (name in {"RefItem", "FineRef"} and field == "$ref") or (
                    name == "GraphLink" and field in {"source_cell_id", "target_cell_id"}
                ):
                    pointer, pointer_stream = text_projection(
                        record_id, field + "@reference", str(member)
                    )
                    reference = {
                        **common,
                        "reference_id": record_id + "/ref/" + field,
                        "source_id": record_id,
                        "field_name": field,
                    }
                    if pointer is not None:
                        reference["native_pointer"] = pointer
                    if pointer_stream is not None:
                        reference["native_pointer_stream_id"] = pointer_stream
                    yield NativeRow("reference", reference)
        address, address_stream = text_projection(record_id, "@address", path)
        row = {
            **common,
            "record_id": record_id,
            "native_type": name,
            "family": _family(name),
            "scalars_json": _json(scalars),
            "structure_json": _json(structure),
        }
        if address is not None:
            row["native_address"] = address
        if address_stream is not None:
            row["native_address_stream_id"] = address_stream
        for field in ("scalars_json", "structure_json"):
            # Match PostgreSQL JSONB rendering, whose whitespace is not an identity input.
            if (
                len(json.dumps(json.loads(row[field]), ensure_ascii=True).encode())
                > MAX_RECORD_BYTES
            ):
                raise NativeMappingError(
                    path, "native field inventory exceeds bounded record; unsupported schema"
                )
        yield NativeRow("native", row)

    root = record_id_for(native_address, native_type)
    yield from object_rows(
        document,
        root_schema,
        InputPath(
            (), display=native_address, locator=native_address if native_address != "#" else None
        ),
        root,
    )
    if native_type == "DoclingDocument":
        yield NativeRow(
            "document",
            {
                **common,
                **({"release_id": release_id} if release_id is not None else {}),
                "source_digest": source_digest,
                "mapping_profile": mapping_profile,
                "contract_version": contract_version,
                "native_schema_digest": mapping.digest,
                "root_id": root,
            },
        )


def _decode_scalar(chunks: Iterable[bytes], profile: str) -> Any:
    payload = b"".join(chunks)  # Explicit requested reconstruction owns this allocation.
    if profile == "pdf-record-native-json-v1":
        return json.loads(payload)
    if profile == "pdf-record-scalar-v1:s":
        return payload.decode("utf-8")
    if profile == "pdf-record-scalar-v1:i":
        return int(payload)
    if profile == "pdf-record-scalar-v1:f":
        return struct.unpack(">d", payload)[0]
    if profile == "pdf-record-scalar-v1:n":
        if payload:
            raise ValueError("invalid null scalar payload")
        return None
    if profile == "pdf-record-scalar-v1:b" and payload in (b"\x00", b"\x01"):
        return payload == b"\x01"
    raise ValueError("unsupported native scalar reconstruction profile")


def iter_native_record_values(
    reader: NativeRecordReader,
    root_id: str,
    *,
    scalar_profiles: Mapping[str, str],
    mapping: NativeSchemaMapping,
    native_type: str = "DoclingDocument",
    json_fields: Literal["text", "decoded"] = "text",
) -> Generator[tuple[str, Any]]:
    """Walk one admitted population with shared schema and closure enforcement."""
    if json_fields not in {"text", "decoded"}:
        raise ValueError("unsupported native record JSON representation")
    active: set[str] = set()

    def field_value(value: Any) -> Any:
        # The frozen capture already contains decoded JSONB values. Its adapter
        # selects that representation explicitly; strings remain native strings.
        return value if json_fields == "decoded" or value is None else json.loads(value)

    def members(record_id, field, descriptor):
        kind = descriptor["kind"]
        yield ("object" if kind == "map" else "array"), None
        keys = set()
        count = 0
        for expected, member in enumerate(reader.members(record_id, field)):
            if member["ordinal"] != expected:
                raise NativeMappingError(
                    record_id + "/" + field,
                    "missing or unordered membership",
                    code="native_membership_closure",
                    category="state_violation",
                )
            if kind == "map":
                key = member.get("member_key")
                if key is None:
                    stream = member["member_key_stream_id"]
                    key = _decode_scalar(reader.scalar(stream), scalar_profiles[stream])
                if key in keys:
                    raise NativeMappingError(
                        record_id,
                        "duplicate native map key",
                        code="native_map_key_duplicate",
                        category="state_violation",
                    )
                keys.add(key)
                yield "key", key
            value_kind = member["value_kind"]
            if value_kind == "record":
                yield from record(member["record_id"])
            elif value_kind == "scalar":
                yield "inline", field_value(member["scalar_json"])
            elif value_kind == "parts":
                yield "parts", member["stream_id"]
            else:
                raise NativeMappingError(record_id, "unsupported membership kind")
            count += 1
        if count != descriptor["length"]:
            raise NativeMappingError(
                record_id + "/" + field,
                "native membership inventory differs",
                code="native_membership_closure",
                category="state_violation",
            )
        yield "end", None

    def record(record_id: str) -> Iterator[tuple[str, Any]]:
        if record_id in active:
            raise NativeMappingError(
                record_id,
                "native containment cycle",
                code="native_containment_cycle",
                category="state_violation",
            )
        active.add(record_id)
        row = reader.record(record_id)
        if record_id == root_id and row["native_type"] != native_type:
            raise NativeMappingError(record_id, "requested native root class differs")
        scalars = field_value(row["scalars_json"])
        structure = field_value(row["structure_json"])
        schema = mapping.schema
        try:
            for component in (
                structure["schema_path"].removeprefix("#/").split("/")
                if structure["schema_path"] != "#"
                else ()
            ):
                schema = (
                    schema[int(component)]
                    if isinstance(schema, list)
                    else schema[component.replace("~1", "/").replace("~0", "~")]
                )
        except (KeyError, IndexError, ValueError, TypeError) as error:
            raise NativeMappingError(record_id, "unsupported native record schema path") from error
        expected_type = "NativeArray" if schema.get("type") == "array" else schema.get("title")
        if (
            not isinstance(expected_type, str)
            or expected_type != row["native_type"]
            or _family(expected_type) != row["family"]
        ):
            raise NativeMappingError(record_id, "native record type differs from retained schema")
        known = set(schema.get("properties", {})) if expected_type != "NativeArray" else {"items"}
        if (scalars.keys() | structure["fields"].keys()) - known or scalars.keys() & structure[
            "fields"
        ].keys():
            raise NativeMappingError(record_id, "unsupported or duplicate native record field")
        if "extensions" in structure and schema.get("additionalProperties") is not True:
            raise NativeMappingError(record_id, "native record class does not admit extensions")
        if expected_type == "NativeArray":
            descriptor = structure["fields"].get("items")
            if scalars or descriptor is None or descriptor["kind"] != "array":
                raise NativeMappingError(record_id, "native nested array has no ordered members")
            yield from members(record_id, "items", descriptor)
        else:
            yield "object", None
            for key, value in scalars.items():
                yield "key", key
                yield "inline", value
            for field, descriptor in structure["fields"].items():
                yield "key", field
                kind = descriptor["kind"]
                if kind == "object":
                    yield from record(descriptor["target"])
                elif kind == "parts":
                    yield "parts", descriptor["stream_id"]
                elif kind in {"array", "map"}:
                    yield from members(record_id, field, descriptor)
                else:
                    raise NativeMappingError(record_id, "unsupported native structure descriptor")
            if "extensions" in structure:
                yield "extension", (structure["extensions"]["stream_id"], known)
            yield "end", None
        active.remove(record_id)

    yield from record(root_id)


def reconstruct_native_document(
    reader: NativeRecordReader,
    root_id: str,
    *,
    scalar_profiles: Mapping[str, str],
    mapping: NativeSchemaMapping | None = None,
    native_type: str = "DoclingDocument",
    json_fields: Literal["text", "decoded"] = "text",
) -> dict[str, Any]:
    """Assemble explicitly requested native rows, refusing incomplete or altered structure."""
    mapping = prepare_native_schema_mapping() if mapping is None else mapping
    events = iter_native_record_values(
        reader,
        root_id,
        scalar_profiles=scalar_profiles,
        mapping=mapping,
        native_type=native_type,
        json_fields=json_fields,
    )

    def scalar(stream: str):
        return _decode_scalar(reader.scalar(stream), scalar_profiles[stream])

    def build(kind, value):
        if kind == "object":
            result = {}
            for action, payload in events:
                if action == "end":
                    return result
                if action == "extension":
                    stream, known = payload
                    extensions = scalar(stream)
                    if not isinstance(extensions, dict) or extensions.keys() & known:
                        raise NativeMappingError(
                            root_id, "native extensions overwrite declared fields"
                        )
                    result.update(extensions)
                elif action == "key":
                    result[payload] = build(*next(events))
                else:
                    raise NativeMappingError(root_id, "unexpected native object member")
        elif kind == "array":
            values = []
            for action, payload in events:
                if action == "end":
                    return values
                values.append(build(action, payload))
        elif kind == "inline":
            return _parse_inline(value)
        elif kind == "parts":
            return scalar(value)
        raise NativeMappingError(root_id, "incomplete native record reconstruction")

    try:
        result = build(*next(events))
    finally:
        events.close()
    if not isinstance(result, dict):
        raise NativeMappingError(root_id, "native document root requires an object")
    if native_type == "DoclingDocument":
        mapping.validate(result)
    else:
        mapping.validator.evolve(schema={"$ref": "#/$defs/" + native_type}).validate(result)
    return result


def validate_native_callbacks(
    document: Mapping[str, Any], *, contract: Mapping[str, Any] | None = None
) -> DoclingDocument:
    """Bounded native validation: reject upstream normalization before identity.

    Finite JSON values are checked before native model construction. All pinned Docling
    validators execute on a private copy, including version compatibility,
    unique refs, native tree/global constraints, table limits, field keys and list repair.
    Mutation or value/presence changes are refused; this is never a normalizing reader.
    Whole-native hydration is explicit here and is not the frozen-union implementation.
    """
    from importlib.metadata import version

    from docling_core.types.doc import DoclingDocument

    contract = native_validation_contract() if contract is None else contract
    required_version = contract["docling_core_version"]
    if version("docling-core") != required_version:
        raise ValueError(f"native callbacks require exactly docling-core {required_version}")
    _finite_json(document, "#")
    # The input is borrowed immutably; only the validation candidate can be mutated.
    original = document
    private = copy.deepcopy(document)
    validated = DoclingDocument.model_validate(private)

    # Read explicit model state rather than serializers: Docling's document serializer drops
    # explicitly empty field_regions/items and table serializers may add computed grids. Neither
    # is permission to lose input presence or allocate a synthetic grid during this check.
    from enum import Enum
    from pathlib import PurePath

    from pydantic import AnyUrl, BaseModel

    def supplied_state(value):
        if isinstance(value, BaseModel):
            result = {}
            for name in value.model_fields_set:
                definition = type(value).model_fields.get(name)
                alias = (
                    (definition.serialization_alias or definition.alias or name)
                    if definition
                    else name
                )
                result[alias] = supplied_state(getattr(value, name))
            return result
        if isinstance(value, dict):
            return {str(key): supplied_state(member) for key, member in value.items()}
        if isinstance(value, (list, tuple)):
            return [supplied_state(member) for member in value]
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, (AnyUrl, PurePath)):
            return str(value)
        return value

    changed = _difference(original, private)
    if changed is None:
        changed = _difference(original, supplied_state(validated))
    if changed is not None:
        raise NativeMappingError(
            changed, "native callbacks changed identified data; normalize before lowering"
        )
    return validated


def native_record_identity_fields(
    row: NativeRow,
    *,
    scalar_descriptor: Callable[[str], ScalarDescriptor],
) -> tuple[str, str, tuple[tuple[str, Any], ...]] | None:
    """Logical fields for an externally ordered identity cursor, excluding physical projections.

    The caller sorts (family,key) externally before LogicalIdentity.add_record. Large scalar
    payloads use verified descriptors; this path never decodes artifact bodies. Product/revision
    allocation, native address projections, transport grouping and stream locations are excluded.
    Native reference spelling remains a native scalar and therefore remains identity-bearing.
    """
    values = row.values
    if row.kind == "document":
        return (
            "document",
            "root",
            (
                ("mapping_profile", values["mapping_profile"]),
                ("contract_version", values["contract_version"]),
                ("native_schema_digest", values["native_schema_digest"]),
                ("root_id", values["root_id"]),
            ),
        )
    if row.kind == "reference":
        # Reference rows are a generated index of the exact scalar in their native object.
        return None
    if row.kind == "native":
        fields: list[tuple[str, Any]] = [
            ("native_type", values["native_type"]),
            ("family", values["family"]),
        ]
        scalars = json.loads(values["scalars_json"])
        structure = json.loads(values["structure_json"])
        # Structure keys are bounded by the supported class, never document cardinality.
        for field in sorted(
            scalars.keys() | structure["fields"].keys(), key=lambda v: v.encode("utf-8")
        ):
            if field in scalars:
                fields.append((field + "/value", _parse_inline(scalars[field])))
                continue
            descriptor = structure["fields"][field]
            kind = descriptor["kind"]
            if kind == "parts":
                fields.append((field + "/value", scalar_descriptor(descriptor["stream_id"])))
            else:
                fields.append((field + "/kind", kind))
                fields.append(
                    (
                        field + "/target" if kind == "object" else field + "/length",
                        descriptor["target"] if kind == "object" else descriptor["length"],
                    )
                )
        if "extensions" in structure:
            fields.append(("@extensions", scalar_descriptor(structure["extensions"]["stream_id"])))
        return "native", values["record_id"], tuple(fields)
    if row.kind == "membership":
        fields = [
            ("parent_id", values["parent_id"]),
            ("field_name", values["field_name"]),
        ]
        key_value = None
        if "member_key" in values:
            key_value = values["member_key"]
        elif "member_key_stream_id" in values:
            key_value = scalar_descriptor(values["member_key_stream_id"])
        if key_value is not None:
            fields.append(("member_key", key_value))
        else:
            fields.append(("ordinal", values["ordinal"]))
        kind = values["value_kind"]
        if kind == "record":
            fields.append(("target", values["record_id"]))
        else:
            fields.append(
                (
                    "value",
                    _parse_inline(json.loads(values["scalar_json"]))
                    if kind == "scalar"
                    else scalar_descriptor(values["stream_id"]),
                )
            )
        # Length-prefixed structured key avoids collisions between arbitrary IDs/field names.
        key = _json(
            [
                values["parent_id"],
                values["field_name"],
                canonical_scalar(key_value).hex() if key_value is not None else values["ordinal"],
            ]
        )
        return "membership", key, tuple(fields)
    raise ValueError("unsupported PDF identity family " + row.kind)
