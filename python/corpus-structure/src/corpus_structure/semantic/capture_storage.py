"""Owned detached capture storage and batch-independent logical content encoding."""

from __future__ import annotations

import base64
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from hashlib import file_digest, sha256
from pathlib import Path
from tempfile import TemporaryDirectory

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from .identity import canonical_bytes


def _scalar(value: pa.Scalar):
    if not value.is_valid:
        return None
    kind = value.type
    if (
        pa.types.is_timestamp(kind)
        or pa.types.is_date(kind)
        or pa.types.is_time(kind)
        or pa.types.is_duration(kind)
    ):
        return [str(kind), value.value]
    data = value.as_py()
    if isinstance(data, Decimal):
        parts = data.as_tuple()
        return ["decimal", parts.sign, list(parts.digits), parts.exponent]
    if isinstance(data, float):
        return ["float", data.hex()]
    if isinstance(data, bytes):
        return ["binary", base64.b64encode(data).decode("ascii")]
    return data


class FrozenManifest(Mapping):
    """Canonical immutable bytes; callers receive detached values on access."""

    def __init__(self, value):
        self._content = canonical_bytes(dict(value))

    def __getitem__(self, key):
        return json.loads(self._content)[key]

    def __iter__(self):
        return iter(json.loads(self._content))

    def __len__(self):
        return len(json.loads(self._content))


def validate_batch_scope(batch):
    metadata = batch.schema.metadata or {}
    for field in batch.schema:
        if not field.nullable and batch[field.name].null_count:
            raise ValueError("captured batch has missing required values")
    for column, tag in (("release_id", b"cs.release"), ("realization_id", b"cs.realization")):
        if tag in metadata and (
            column not in batch.schema.names
            or pc.call_function(
                "all",
                [pc.call_function("equal", [batch[column], pa.scalar(metadata[tag].decode())])],
            ).as_py()
            is False
        ):
            raise ValueError("captured batch row scope differs")


class LogicalRows:
    """Length-framed typed rows; neither chunk boundaries nor file codecs enter identity."""

    def __init__(self, schema: pa.Schema, keys: tuple[str, ...] = ()):
        self._hash = sha256()
        self._keys = keys
        self._previous = None
        self.rows = 0
        self._update(
            [
                "canonical-rows-1",
                base64.b64encode(schema.remove_metadata().serialize().to_pybytes()).decode("ascii"),
            ]
        )

    def _update(self, value):
        data = canonical_bytes(value)
        self._hash.update(len(data).to_bytes(8, "big"))
        self._hash.update(data)

    def write(self, batch: pa.RecordBatch) -> None:
        for index in range(batch.num_rows):
            if self._keys:
                key = tuple(
                    batch.column(batch.schema.get_field_index(name))[index].as_py()
                    for name in self._keys
                )
                if self._previous is not None and key <= self._previous:
                    raise ValueError("capture rows are not in unique primary-key order")
                self._previous = key
            self._update([_scalar(column[index]) for column in batch.columns])
        self.rows += batch.num_rows

    @property
    def digest(self) -> str:
        return self._hash.hexdigest()


@dataclass(frozen=True)
class FileRelation:
    path: Path
    schema: pa.Schema
    num_rows: int
    sha256: str
    logical_digest: str

    def iter_batches(self, batch_size=65536):
        yield from pq.ParquetFile(self.path).iter_batches(batch_size=batch_size)

    def verify(self) -> None:
        with self.path.open("rb") as source:
            digest = file_digest(source, "sha256").hexdigest()
        if digest != self.sha256:
            raise ValueError("captured file integrity differs")
        metadata = pq.ParquetFile(self.path)
        if metadata.metadata.num_rows != self.num_rows or not metadata.schema_arrow.equals(
            self.schema, check_metadata=True
        ):
            raise ValueError("captured file integrity/schema differs")


class CaptureOwner:
    """Disposable directory: close forbids new scopes, last lease removes backing files."""

    def __init__(self, scratch_path=None):
        if scratch_path is not None:
            Path(scratch_path).mkdir(parents=True, exist_ok=True)
        self._temporary = TemporaryDirectory(prefix="corpus-capture-", dir=scratch_path)
        self.root = Path(self._temporary.name)
        self.closed = False
        self.leases = 0
        self._admitted = {}

    def owns(self, name, relation):
        return self._admitted.get(name) is relation

    def acquire(self):
        if self.closed:
            raise RuntimeError("captured packet is closed")
        self.leases += 1

    def release(self):
        self.leases -= 1
        if self.closed and not self.leases:
            self._temporary.cleanup()

    def close(self):
        self.closed = True
        if not self.leases:
            self._temporary.cleanup()


def store_relation(
    owner: CaptureOwner | None,
    name: str,
    schema: pa.Schema,
    batches: Iterable[pa.RecordBatch],
    keys: tuple[str, ...],
    budget: list[int],
    limit: int,
):
    logical = LogicalRows(schema, keys)
    retained = []
    path = owner.root / (name + ".parquet") if owner else None
    writer = pq.ParquetWriter(path, schema, store_schema=True) if path else None
    try:
        for batch in batches:
            validate_batch_scope(batch)
            logical.write(batch)
            if writer:
                writer.write_batch(batch)
            else:
                budget[0] += batch.nbytes
                if budget[0] > limit:
                    raise ValueError("resident capture byte limit exceeded; select spooled mode")
                retained.append(batch)
    except BaseException as error:
        if writer:
            try:
                writer.close()
            except BaseException as cleanup:
                error.add_note(f"writer cleanup also failed: {cleanup!r}")
        raise
    else:
        if writer:
            writer.close()
    if path:
        with path.open("rb") as source:
            digest = file_digest(source, "sha256").hexdigest()
        value = FileRelation(path, schema, logical.rows, digest, logical.digest)
        assert owner is not None
        owner._admitted[name] = value
    else:
        value = pa.Table.from_batches(retained, schema=schema)
    descriptor = {
        "name": name,
        "rows": logical.rows,
        "logical_digest": logical.digest,
        "arrow_schema": base64.b64encode(schema.serialize().to_pybytes()).decode("ascii"),
    }
    if isinstance(value, FileRelation):
        descriptor.update(file=value.path.name, sha256=value.sha256)
    return value, descriptor


def manifest_digest(manifest):
    scope = {key: value for key, value in manifest["binding"].items() if key != "capture_id"}
    identity = {
        "binding": scope,
        "projection": manifest["projection_id"],
        "profile": manifest["profile_digest"],
        "relations": {
            name: {"rows": value["rows"], "logical_digest": value["logical_digest"]}
            for name, value in manifest["relations"].items()
        },
    }
    return sha256(canonical_bytes(identity)).hexdigest()


def finish_manifest(owner, binding, projection, profile, descriptors):
    manifest = {
        "format": "semantic-capture-1",
        "digest_recipe": "canonical-rows-1",
        "complete": True,
        "binding": binding,
        "projection_id": projection,
        "profile_digest": profile,
        "logical_digest": "",
        "relations": descriptors,
    }
    manifest["logical_digest"] = manifest_digest(manifest)
    from .analysis_contracts import validate_capture_manifest

    validate_capture_manifest(manifest)
    if owner:
        temporary = owner.root / ".manifest.json"
        temporary.write_text(json.dumps(manifest, indent=2) + "\n")
        temporary.rename(owner.root / "manifest.json")
    return FrozenManifest(manifest)
