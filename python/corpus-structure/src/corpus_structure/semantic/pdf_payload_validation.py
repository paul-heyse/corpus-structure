"""Keyed typed PDF validation inputs under the captured publication policy."""

from __future__ import annotations

import json
from struct import unpack_from
from collections.abc import Collection, Iterable, Iterator, Mapping
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from typing import Any

import pyarrow as pa

from .pdf_record_identity import BLOCK_BYTES, byte_root


@dataclass(frozen=True, slots=True)
class _Row:
    batch: pa.RecordBatch
    index: int

    def __getitem__(self, name: str) -> Any:
        return self.batch.column(name)[self.index].as_py()

    def binary(self, name: str) -> memoryview:
        column = self.batch.column(name)
        validity, offsets, values = column.buffers()
        position = column.offset + self.index
        if validity is not None and not (memoryview(validity)[position // 8] & (1 << (position % 8))):
            raise ValueError("artifact part body is null")
        if pa.types.is_binary(column.type):
            start, end = unpack_from("<ii", offsets, position * 4)
        elif pa.types.is_large_binary(column.type):
            start, end = unpack_from("<qq", offsets, position * 8)
        else:
            raise ValueError("artifact part body requires a binary Arrow column")
        return memoryview(values).cast("B")[start:end]

    def values(self) -> dict[str, Any]:
        return {name: self[name] for name in self.batch.schema.names}


_KEYS = {
    "header": ("root_id",),
    "native": ("record_id",),
    "membership": ("parent_id", "field_name", "ordinal"),
    "artifact_stream": ("stream_id",),
    "companion_field": ("family", "local_id", "field_name"),
}


def metadata_classes(staging_source: bytes) -> dict[str, str]:
    import yaml

    model = yaml.safe_load(staging_source)
    return json.loads(model["annotations"]["pds:metadata_classes"])


class _FrozenCompanions:
    """Repeatable ordered view over the exact frozen companion family."""

    def __init__(self, store: FrozenPayloadStore, family: str):
        self.store, self.family = store, family
        self.count = len(store._companions.get(family, ()))
        self._indexed = lru_cache(maxsize=256)(self._one)

    def __len__(self):
        return self.count

    def __iter__(self):
        for row in self.store.companions(self.family):
            yield self.store.companion_value(row)

    def _one(self, index: int):
        row = self.store._companions.get(self.family, {}).get(str(index))
        if row is None:
            raise ValueError("frozen companion input index is absent")
        return self.store.companion_value(self.store._companion(row))

    def __getitem__(self, index: int):
        return self._indexed(index)


class FrozenPayloadStore:
    """Index typed rows by compact coordinates and borrow their original binary buffers."""

    def __init__(self, validation_contract: Mapping[str, Any]):
        from .pdf_payloads import schema_load

        self._batches: dict[str, list[pa.RecordBatch]] = {}
        self._rows: dict[str, dict[tuple[Any, ...], _Row]] = {family: {} for family in _KEYS}
        self._members: dict[tuple[str, str], list[tuple[int, _Row]]] = {}
        self._parts: dict[str, dict[int, _Row]] = {}
        self._part_coordinates: list[pa.RecordBatch] = []
        self._descriptors: list[pa.RecordBatch] = []
        self._companions: dict[str, dict[str, _Row]] = {}
        self._metadata: dict[str, list[tuple[int | None, str]]] = {}
        self._verified_streams: set[str] = set()
        self.schemas = schema_load(json.dumps(validation_contract["schemas"]))
        self.publication_kind = validation_contract["publication_kind"]
        if self.publication_kind not in {"native", "integrated"}:
            raise ValueError("unsupported frozen publication kind")
        self.integrated_metadata_policy = validation_contract.get("integrated_metadata_policy")

    def close(self) -> None:
        self._batches.clear()
        self._rows.clear()
        self._members.clear()
        self._parts.clear()
        self._part_coordinates.clear()
        self._descriptors.clear()
        self._companions.clear()
        self._metadata.clear()
        self._verified_streams.clear()

    @staticmethod
    def _insert(rows, key, row, family):
        if key in rows:
            raise ValueError(f"duplicate PDF {family} key: {key!r}")
        rows[key] = row

    def add_batch(self, family: str, batch: pa.RecordBatch) -> None:
        if family == "reference":
            # Native references are represented in the canonical document and
            # checked independently against the native reference relation on adoption.
            return
        if family != "artifact_part":
            self._batches.setdefault(family, []).append(batch)
        if family == "artifact_part":
            self._part_coordinates.append(
                batch.select(("stream_id", "ordinal", "byte_offset", "byte_length"))
            )
            for index, (stream, ordinal) in enumerate(
                zip(
                    batch.column("stream_id").to_pylist(),
                    batch.column("ordinal").to_pylist(),
                    strict=True,
                )
            ):
                rows = self._parts.setdefault(stream, {})
                self._insert(rows, ordinal, _Row(batch, index), "artifact part")
                self._verified_streams.discard(stream)
            return
        if family == "companion":
            for index, (kind, local) in enumerate(
                zip(
                    batch.column("family").to_pylist(),
                    batch.column("local_id").to_pylist(),
                    strict=True,
                )
            ):
                row = _Row(batch, index)
                self._insert(self._companions.setdefault(kind, {}), local, row, kind)
                if kind == "native_metadata":
                    projection = json.loads(row["body"])
                    self._metadata.setdefault(projection["kind"], []).append(
                        (projection.get("page_no"), local)
                    )
            return
        if family == "artifact_stream":
            self._descriptors.append(batch.select(("stream_id", "byte_length")))
        key_fields = _KEYS[family]
        for index, key in enumerate(
            zip(*(batch.column(name).to_pylist() for name in key_fields), strict=True)
        ):
            row = _Row(batch, index)
            self._insert(self._rows[family], key, row, family)
            if family == "membership":
                parent, field, ordinal = key
                self._members.setdefault((parent, field), []).append((ordinal, row))

    def batches(self, family: str) -> Iterator[pa.RecordBatch]:
        """Borrow captured-schema batches in their original delivery order."""
        yield from self._batches.get(family, ())

    def entries(self, family: str) -> Iterator[dict[str, Any]]:
        for row in self._rows[family].values():
            yield row.values()

    def record(self, record_id: str) -> dict[str, Any]:
        return self._rows["native"][(record_id,)].values()

    def members(self, parent_id: str, field_name: str) -> Iterator[dict[str, Any]]:
        for _, row in sorted(
            self._members.get((parent_id, field_name), ()), key=lambda value: value[0]
        ):
            yield row.values()

    def check_artifact_coordinates(self, analytical) -> None:
        """Prove stream correspondence using compact coordinates, excluding part bodies."""
        from duckdb import coalesce, col, fn, lit

        if not self._part_coordinates:
            if any(row["byte_length"] for row in self.stream_descriptors()):
                raise ValueError("frozen metadata bytes differ from their descriptor")
            return
        parts = analytical.from_arrow(pa.Table.from_batches(self._part_coordinates))
        position = [col("ordinal").asc().nulls_last()]
        stream = [col("stream_id")]
        ordered = parts.select(
            col("ordinal"),
            col("byte_offset"),
            fn("row_number").over(partition_by=stream, order_by=position).alias("rank"),
            coalesce(
                fn("lag", col("byte_offset") + col("byte_length")).over(
                    partition_by=stream, order_by=position
                ),
                lit(0),
            ).alias("expected_offset"),
        )
        if (
            ordered.filter(
                (col("ordinal") != col("rank") - lit(1))
                | (col("byte_offset") != col("expected_offset"))
            )
            .limit(1)
            .fetchall()
        ):
            raise ValueError("artifact parts must be one contiguous ordered stream")
        if not self._descriptors:
            raise ValueError("PDF artifact parts have no stream descriptor")
        lengths = parts.aggregate(
            [col("stream_id"), fn("sum", col("byte_length")).alias("actual_length")]
        ).set_alias("observed")
        declared = analytical.from_arrow(pa.Table.from_batches(self._descriptors)).set_alias(
            "declared"
        )
        invalid = declared.join(
            lengths, col("declared", "stream_id") == col("observed", "stream_id"), how="full"
        ).filter(
            (col("declared", "stream_id").isnull())
            | (col("declared", "byte_length") != coalesce(col("actual_length"), lit(0)))
        )
        if invalid.limit(1).fetchall():
            raise ValueError("frozen metadata bytes differ from their descriptor")

    def check_membership(self, analytical) -> None:
        """Require closed keyed memberships before the nominal tree traversal."""
        from duckdb import col, count_all, fn, lit

        expected = []
        actual = []
        for (record_id,), row in self._rows["native"].items():
            structure = json.loads(row["structure_json"])
            for field, descriptor in structure["fields"].items():
                kind = descriptor["kind"]
                if kind not in {"array", "map"}:
                    continue
                count = descriptor["length"]
                if count:
                    expected.append(
                        dict(parent=record_id, field=field, length=count, lo=0, hi=count - 1)
                    )
                if kind == "map":
                    keys = set()
                    for _, member in self._members.get((record_id, field), ()):
                        key = member["member_key"]
                        if key is None:
                            key = b"".join(self.scalar(member["member_key_stream_id"])).decode()
                        if key in keys:
                            raise ValueError("duplicate native map key")
                        keys.add(key)
        for (parent, field), members in self._members.items():
            actual.extend(
                dict(parent=parent, field=field, ordinal=ordinal) for ordinal, _ in members
            )
        shape = [("parent", pa.string()), ("field", pa.string())]
        members = analytical.from_arrow(
            pa.Table.from_pylist(actual, schema=pa.schema([*shape, ("ordinal", pa.int64())]))
        ).aggregate(
            [
                col("parent"),
                col("field"),
                count_all().alias("length"),
                fn("min", col("ordinal")).alias("lo"),
                fn("max", col("ordinal")).alias("hi"),
            ]
        )
        requested = analytical.from_arrow(
            pa.Table.from_pylist(
                expected,
                schema=pa.schema(
                    [*shape, ("length", pa.int64()), ("lo", pa.int64()), ("hi", pa.int64())]
                ),
            )
        )
        if (
            members.except_all(requested).select(lit(1)).limit(1).fetchall()
            or requested.except_all(members).select(lit(1)).limit(1).fetchall()
        ):
            raise ValueError("native membership inventory differs")

    def part_rows(self, stream: str) -> Iterator[dict[str, Any]]:
        rows = self._parts.get(stream, {})
        for ordinal in sorted(rows):
            yield rows[ordinal].values()

    def field(self, family: str, local: str, name: str):
        row = self._rows["companion_field"].get((family, local, name))
        return None if row is None else row.values()

    def stream_descriptors(self) -> Iterator[dict[str, Any]]:
        rows = self._rows["artifact_stream"]
        unexpected = self._parts.keys() - {stream for (stream,) in rows}
        if unexpected:
            raise ValueError("PDF artifact parts have no stream descriptor")
        for key in sorted(rows):
            yield rows[key].values()

    def descriptor(self, stream: str) -> dict[str, Any]:
        row = self._rows["artifact_stream"].get((stream,))
        if row is None:
            raise ValueError("frozen metadata stream is missing")
        return row.values()

    def parts(self, stream: str) -> Iterator[memoryview]:
        rows = self._parts.get(stream, {})
        offset = 0
        verify = stream not in self._verified_streams
        for expected, ordinal in enumerate(sorted(rows)):
            row = rows[ordinal]
            body = row.binary("body")
            if verify:
                if ordinal != expected or row["byte_offset"] != offset:
                    raise ValueError("artifact parts must be one contiguous ordered stream")
                if (
                    not 0 < len(body) <= BLOCK_BYTES
                    or len(body) != row["byte_length"]
                    or sha256(body).hexdigest() != row["sha256_digest"]
                ):
                    raise ValueError("artifact part actual bytes differ from length/digest")
                offset += len(body)
            yield body

    def scalar(self, stream_id: str, /) -> Iterable[memoryview]:
        self.verify_stream(self.descriptor(stream_id))
        return self.parts(stream_id)

    def _verify(self, descriptor: Mapping[str, Any], chunks, *, check_active=lambda: None) -> None:
        digest = sha256()

        def consume():
            for chunk in chunks:
                check_active()
                digest.update(chunk)
                yield chunk

        length, root = byte_root(consume())
        if (length, root.hex()) != (descriptor["byte_length"], descriptor["byte_root"]) or (
            descriptor.get("serialization_sha256") is not None
            and descriptor["serialization_sha256"] != digest.hexdigest()
        ):
            raise ValueError("frozen metadata bytes differ from their descriptor")
        self._verified_streams.add(descriptor["stream_id"])

    def verify_stream(self, descriptor: Mapping[str, Any], *, check_active=lambda: None) -> None:
        if descriptor["stream_id"] not in self._verified_streams:
            self._verify(descriptor, self.parts(descriptor["stream_id"]), check_active=check_active)

    def stream(self, stream: str) -> tuple[dict[str, Any], bytes]:
        descriptor = self.descriptor(stream)
        if stream in self._verified_streams:
            return descriptor, b"".join(self.parts(stream))
        chunks = []

        def collect():
            for body in self.parts(stream):
                chunks.append(body)
                yield body

        self._verify(descriptor, collect())
        return descriptor, b"".join(chunks)

    @staticmethod
    def _companion(row: _Row) -> dict[str, Any]:
        values = row.values()
        values["body"] = json.loads(values["body"])
        return values

    def companions(
        self, family: str, *, kind: str | None = None, page_nos: Collection[int] | None = None
    ) -> Iterator[dict[str, Any]]:
        rows = self._companions.get(family, {})
        keys = (
            rows.keys()
            if kind is None
            else (
                local
                for page_no, local in self._metadata.get(kind, ())
                if page_nos is None or page_no in page_nos
            )
        )
        if page_nos is not None and not page_nos:
            return
        for key in sorted(keys):
            value = self._companion(rows[key])
            if page_nos is None or kind is not None or value["body"].get("page_no") in page_nos:
                yield value

    def has_companions(self, family: str, *, kind: str | None = None) -> bool:
        return bool(self._companions.get(family) if kind is None else self._metadata.get(kind))

    def companion_value(self, row: Mapping[str, Any]) -> dict[str, Any]:
        """Decode declared overflow fields from their frozen bytes."""
        from .pdf_records import _decode_scalar

        body = dict(row["body"])
        if row["family"] == "occurrence":
            expected = (("text", "s", "pdf-record-scalar-v1:s"),)
        elif row["family"] == "relation":
            expected = (
                ("endpoints", "y", "pdf-companion-json-field-v1"),
                ("evidence", "s", "pdf-record-scalar-v1:s"),
            )
        else:
            return body
        for name, kind, profile in expected:
            field = self.field(row["family"], row["local_id"], name)
            if field is None:
                continue
            if name in body:
                raise ValueError(f"{row['family']} {name} has both inline and byte-owned values")
            descriptor, payload = self.stream(field["stream_id"])
            if field["scalar_kind"] != kind or descriptor["encoding_profile"] != profile:
                raise ValueError(f"frozen {row['family']} {name} encoding differs")
            body[name] = json.loads(payload) if kind == "y" else _decode_scalar((payload,), profile)
        return body

    def _prepare(self, kind: str):
        from .pdf_payloads import FAMILY, prepare_payload_schema, prepare_schema_validator

        schema = self.schemas[kind]
        return (
            prepare_payload_schema(schema) if kind == FAMILY else None,
            prepare_schema_validator(schema) if kind != FAMILY else None,
        )

    def value(self, row: Mapping[str, Any]) -> Any:
        return self._value(row, self._prepare(row["body"]["kind"]))

    def _value(self, row: Mapping[str, Any], prepared) -> Any:
        from .pdf_payloads import PROFILE

        body = row["body"]
        field = self.field(row["family"], row["local_id"], "value")
        if field is None:
            raise ValueError("frozen metadata field is missing")
        descriptor, payload = self.stream(field["stream_id"])
        kind = body["kind"]
        codec, validator = prepared
        if descriptor["encoding_profile"] == PROFILE:
            if codec is None:
                raise ValueError("frozen page locator differs from payload")
            value = codec.decode(
                payload,
                schema_digest=body["payload_schema_digest"],
                logical_digest=body["payload_logical_digest"],
            )
            if (
                kind != "inline_candidate_pages"
                or body["page_no"] != value["page_no"]
                or body["payload_codec"] != PROFILE
            ):
                raise ValueError("frozen page locator differs from payload")
        elif descriptor["encoding_profile"] == "pdf-companion-json-field-v1":
            if validator is None:
                raise ValueError("unsupported frozen page metadata encoding")
            value = json.loads(payload)
            validator.validate(value)
        else:
            raise ValueError("unsupported frozen metadata encoding")
        if isinstance(value, dict):
            pointer = next(
                (
                    value[k]
                    for k in ("pointer", "prose_pointer", "table_pointer")
                    if isinstance(value.get(k), str)
                ),
                None,
            )
            if body.get("pointer") != pointer:
                raise ValueError("metadata pointer projection differs")
            # Older captures carry only the original opaque value. New adoption
            # requires a matching occurrence projection.
            if (
                kind == "inline_alignment_reports"
                and "item_pointers" in body
                and body["item_pointers"] != value["item_pointers"]
            ):
                raise ValueError("metadata item pointer projection differs")
            if kind == "formula_outcomes" and (
                body.get("outcome") != value.get("outcome")
                or body.get("has_diagnostic") != ("error" in value)
            ):
                raise ValueError("metadata health projection differs")
        return value

    def values(self, kind: str) -> Iterator[Any]:
        prepared = self._prepare(kind)
        for row in self.companions("native_metadata", kind=kind):
            yield self._value(row, prepared)

    def validate(self, document: Mapping[str, Any], *, items, regions) -> None:
        from .pdf_ocr_contracts import _SourceIndex, validate_pdf_page_payloads
        from .pdf_payloads import FAMILY
        from .pdf_report_validation import validate_pdf_report_metadata

        # Preparation and decoded reuse belong only to this exact frozen invocation.
        # Page payloads are never accumulated: their locators index immutable bytes.
        prepared = {}

        def decode(row):
            kind = row["body"]["kind"]
            if kind not in prepared:
                prepared[kind] = self._prepare(kind)
            return self._value(row, prepared[kind])

        needed = {
            "cell_reports",
            "inline_alignment_reports",
            "recognition_coverage",
            "formula_outcomes",
            "runtime_report",
        }
        metadata = {kind: [] for kind in needed}
        page_rows = {}
        for row in self.companions("native_metadata"):
            kind = row["body"]["kind"]
            if kind == FAMILY:
                number = row["body"]["page_no"]
                if type(number) is not int or number < 1 or number in page_rows:
                    raise ValueError("inline candidate page is duplicate or outside native scope")
                page_rows[number] = row
            else:
                value = decode(row)
                if kind in metadata:
                    metadata[kind].append(value)

        def pages():
            for number in sorted(page_rows):
                yield decode(page_rows[number])

        health = [r["body"] for r in self.companions("health") if "source_scope" in r["body"]]
        if len(health) != 1:
            raise ValueError("native health/source scope is absent or ambiguous")
        product = dict(
            kind=self.publication_kind,
            metadata_kinds=frozenset(self._metadata),
            document=document,
            items=items,
            regions=regions,
            health=dict(health[0]),
            source_scope=health[0]["source_scope"],
            page_start=health[0].get("page_start"),
            page_end=health[0].get("page_end"),
            cell_reports=metadata["cell_reports"],
            inline_candidate_pages=pages(),
            inline_alignment_reports=metadata["inline_alignment_reports"],
            recognition_coverage=metadata["recognition_coverage"],
        )
        product["health"]["formula_outcomes"] = metadata["formula_outcomes"]
        runtime = metadata["runtime_report"]
        if len(runtime) > 1:
            raise ValueError("native runtime metadata is ambiguous")
        if runtime:
            product["runtime_report"] = runtime[0]
        structural = [
            r["body"] for r in self.companions("input") if r["body"].get("role") == "structural"
        ]
        if len(structural) == 1:
            parent = structural[0]
            product.update(
                parent_task_id=parent["task_id"],
                parent_product_key=parent["product_key"],
                parent_digest=parent["content_digest"],
            )
        source = _SourceIndex(product)
        validate_pdf_report_metadata(
            product, integrated_policy=self.integrated_metadata_policy, source=source
        )
        validate_pdf_page_payloads(product, source=source)
        if self.publication_kind == "integrated":
            self.validate_integrated_meaning(document)

    def validate_integrated_meaning(self, document: Mapping[str, Any]) -> None:
        """Apply the shared selected-content rules over typed companion families."""
        from .pdf_integrated import validate_pdf_product_meaning

        validate_pdf_product_meaning(
            dict(
                kind="integrated",
                content={"document": document},
                **{
                    name: _FrozenCompanions(self, family)
                    for name, family in (
                        ("inputs", "input"),
                        ("occurrences", "occurrence"),
                        ("relations", "relation"),
                        ("coverage", "coverage"),
                        ("mapping_reports", "mapping_report"),
                    )
                },
            )
        )
