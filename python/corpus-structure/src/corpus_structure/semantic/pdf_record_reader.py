"""Selective published record reads and explicitly streamed native serialization.

The caller owns the Connection and its snapshot. Iterators own only bounded result
pages; no iterator returns a model initialized from a different product pin.
"""

from __future__ import annotations

import codecs
import json
from collections import OrderedDict
from collections.abc import Callable, Generator, Iterator, Mapping, Sequence
from contextlib import closing, contextmanager, nullcontext
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from typing import TYPE_CHECKING, Any, BinaryIO, TypedDict

import pyarrow as pa
import pyarrow.compute as pc
from sqlalchemy import Connection, Text, any_, func, literal, select

from corpus_structure.core.db.lifetime import BorrowerCancellation
from corpus_structure.core.db.store import (
    DatabaseOperationFailure,
    DatabasePhase,
    EffectKnowledge,
    classify_error,
    record_operation_failure,
)

from ._operation_ids import ContentDigest, ProductKey
from .product_reference import ProductReference

if TYPE_CHECKING:
    from ._operation_calls import ContentDigest, ProductKey, TaskId
    from .operation_value_types import NativeRowResult
    from .types import PreparedRelease


@dataclass
class PublishedReadBudget:
    """Invocation-owned source rows and bytes; full exports choose explicit streaming."""

    max_rows: int
    max_bytes: int
    rows: int = 0
    bytes: int = 0

    def preflight(self, conn, statement, *, payload_reserved=False):
        from .query import ReadLimit

        # Only scalar lengths/count cross this first protected read. Data remains on
        # the server until its exact immutable selection has passed admission.
        requested = statement.subquery()
        selected = select(requested).limit(self.max_rows - self.rows + 1).subquery()
        size = sum(
            (func.coalesce(func.octet_length(column.cast(Text)), 0) for column in selected.c),
            literal(0),
        )
        summary = conn.execute(
            select(
                func.count().label("rows"),
                func.coalesce(func.sum(size), 0).label("bytes"),
                func.coalesce(func.max(size), 0).label("largest"),
            ).select_from(selected)
        ).one()
        if self.rows + summary.rows > self.max_rows:
            raise ReadLimit("native source row-work budget exhausted", reason="work_limit")
        allowance = self.max_bytes if payload_reserved else self.max_bytes - self.bytes
        # PostgreSQL JSON text has insignificant whitespace/hex byte transport. A
        # bounded 2x transfer preflight precedes canonical decoded-row accounting.
        if summary.largest > 2 * self.max_bytes:
            raise ReadLimit(
                "a native source object exceeds the byte budget", reason="oversized_item"
            )
        if summary.bytes > 2 * allowance:
            raise ReadLimit("native source byte-work budget exhausted", reason="work_limit")
        self.rows += summary.rows

    def value(self, value):
        from pydantic_core import to_jsonable_python

        from .identity import canonical_bytes
        from .query import ReadLimit

        size = len(canonical_bytes(to_jsonable_python(value)))
        if size > self.max_bytes:
            raise ReadLimit(
                "a native source object exceeds the byte budget", reason="oversized_item"
            )
        self.reserve(size)

    def reserve(self, size):
        from .query import ReadLimit

        if type(size) is not int or size < 0:
            raise ValueError("source byte length must be a nonnegative integer")
        if size > self.max_bytes:
            raise ReadLimit(
                "a native source payload exceeds the byte budget", reason="oversized_item"
            )
        if self.bytes + size > self.max_bytes:
            raise ReadLimit("native source byte-work budget exhausted", reason="work_limit")
        self.bytes += size


class _ProjectionParameters(TypedDict):
    task_id: TaskId
    product_key: ProductKey
    content_digest: ContentDigest
    projection_context: PreparedRelease


class _RecordParameters(TypedDict):
    task_id: TaskId
    product_key: ProductKey
    content_digest: ContentDigest


def _record_parameters(reference: ProductReference) -> _RecordParameters:
    from ._operation_ids import ContentDigest, ProductKey, TaskId

    return _RecordParameters(
        task_id=TaskId(reference.task_id),
        product_key=ProductKey(reference.product_key),
        content_digest=ContentDigest(reference.content_digest),
    )


def _record_envelope(row: NativeRowResult) -> dict[str, Any]:
    body = row.decoded_json_fields(operation="read_native_source")["body"]
    if not isinstance(body, dict):
        raise ValueError("published record envelope requires an object")
    return body


def _published_revision(conn: Connection, reference: ProductReference, *, read_budget=None):
    from ._operation_calls import (
        materialize_read_pdf_published_revision,
        prepare_read_pdf_published_revision,
    )
    from ._operation_ids import TaskId

    statement = prepare_read_pdf_published_revision(
        task_id=TaskId(reference.task_id),
        product_key=ProductKey(reference.product_key),
        logical_digest=ContentDigest(reference.content_digest),
    )
    if read_budget is not None:
        read_budget.preflight(conn, statement)
    with conn.execute(statement) as result:
        row = result.one_or_none()
        decoded = (
            materialize_read_pdf_published_revision(row).model_dump(mode="python")
            if row is not None
            else None
        )
    if read_budget is not None and decoded is not None:
        read_budget.value(decoded)
    return decoded


_METADATA_PROJECTIONS = (
    "pointer",
    "outcome",
    "has_diagnostic",
    "page_no",
    "payload_schema_digest",
    "payload_codec",
    "payload_logical_digest",
)


@dataclass(frozen=True, slots=True)
class PdfExportReceipt:
    byte_length: int
    serialization_sha256: str


class PublishedRecordUnavailable(ValueError):
    """An exact published record address is absent under its immutable pin."""


class PublishedSchemaUnavailable(ValueError):
    """Retained schema custody or its explicit supported decoding profile is unavailable."""


def published_native_table(kind: str = "item"):
    """Use the current released projection shape without a legacy deployment fallback."""
    from .metadata import table

    if kind not in {"item", "region"}:
        raise ValueError("unknown native access projection")
    return table("ops.pdf_published_" + kind)


def published_record_reader(
    conn: Connection,
    reference: ProductReference,
    *,
    cancellation: BorrowerCancellation | None = None,
    projection_context: PreparedRelease | None = None,
    read_budget: PublishedReadBudget | None = None,
):
    """Return the current published port, or None for a non-source observation."""
    cancellation = cancellation or BorrowerCancellation()
    with cancellation.borrow(conn):
        row = _published_revision(conn, reference, read_budget=read_budget)
        return (
            PublishedPdfReader(
                conn,
                reference,
                revision=dict(row),
                cancellation=cancellation,
                projection_context=projection_context,
                read_budget=read_budget,
            )
            if row
            else None
        )


class PublishedRegionUnavailable(ValueError):
    """The qualified published reader established that the requested region is absent."""


class PublishedPdfReader:
    def __init__(
        self,
        conn: Connection,
        reference: ProductReference,
        *,
        revision: Mapping[str, Any] | None = None,
        cancellation: BorrowerCancellation | None = None,
        projection_context: PreparedRelease | None = None,
        read_budget: PublishedReadBudget | None = None,
    ):
        self.read_budget = read_budget
        self.projection_context = projection_context
        self.conn, self.reference = conn, reference
        self.cancellation = cancellation or BorrowerCancellation()
        if revision is None:
            with self._read_scope():
                revision = _published_revision(conn, reference)
            if revision is None:
                raise ValueError("published native revision is absent")
        self.revision: dict[str, Any] = dict(revision)
        self._cached_record: Callable[[str], dict[str, Any]] = lru_cache(maxsize=256)(self._record)

    @contextmanager
    def _read_scope(self) -> Generator[None]:
        """Cancel only this live read; the caller retains its connection/snapshot owner."""
        cancellation = getattr(self, "cancellation", None)
        scope = cancellation.borrow(self.conn) if cancellation is not None else nullcontext()
        try:
            with scope:
                yield
                self._check_active()
        except Exception as error:
            record_operation_failure(
                error,
                DatabaseOperationFailure(
                    classify_error(
                        error,
                        phase=DatabasePhase.EXECUTING,
                        effects=EffectKnowledge.NONE,
                        cancellation_requested=cancellation is not None and cancellation.requested,
                    ),
                    f"pdf:{self.reference.task_id}:{self.reference.product_key}",
                    "close_read_snapshot",
                    getattr(self, "revision", {}).get("release_id"),
                ),
            )
            raise

    def _check_active(self) -> None:
        cancellation = getattr(self, "cancellation", None)
        if cancellation is not None:
            cancellation.check_active()

    def _raw_rows(self, statement, *, payload_reserved=False):
        with self._read_scope():
            budget = getattr(self, "read_budget", None)
            if budget is not None:
                budget.preflight(self.conn, statement, payload_reserved=payload_reserved)
            with self.conn.execute(statement) as result:
                return list(result)

    def _read_operation(self, name, *, selection=None, **parameters):
        from . import _operation_calls as calls

        statement = getattr(calls, "prepare_" + name)(**parameters)
        if selection is not None:
            statement = selection(statement)
        materialize = getattr(calls, "materialize_" + name)
        return tuple(materialize(row) for row in self._raw_rows(statement))

    def _admit_value(self, value):
        budget = getattr(self, "read_budget", None)
        if budget is not None:
            budget.value(value)
        return value

    def iter_rows(
        self,
        family: str,
        filters: Mapping[str, Any] | None = None,
        *,
        after=None,
        batch_size: int = 100,
        _payload_reserved=False,
    ) -> Generator[dict[str, Any]]:
        from ._operation_calls import materialize_read_pdf_record_rows, prepare_read_pdf_record_rows

        if not 1 <= batch_size <= 1000:
            raise ValueError("published record batch size must be 1..1000")
        if getattr(self, "read_budget", None) is not None:
            batch_size = min(batch_size, 64)
        while True:
            # Each bounded function call rechecks the immutable published binding. Close
            # Result before yielding so abandonment cannot leak a server-side cursor.
            statement = prepare_read_pdf_record_rows(
                **_record_parameters(self.reference),
                family=family,
                filters=dict(filters or {}),
                after=after,
                limit=batch_size,
            )
            rows = [
                _record_envelope(materialize_read_pdf_record_rows(row))
                for row in self._raw_rows(statement, payload_reserved=_payload_reserved)
            ]
            for row in rows:
                self._admit_value(
                    {key: value for key, value in row.items() if key != "body"}
                    if family == "artifact_part" and _payload_reserved
                    else row
                )
            if not rows:
                return
            for row in rows:
                self._check_active()
                after = row.pop("_cursor")
                for name in ("scalars_json", "structure_json", "scalar_json"):
                    if name in row and row[name] is not None:
                        row[name] = json.dumps(row[name], ensure_ascii=False, allow_nan=False)
                if family == "artifact_part":
                    row["body"] = bytes.fromhex(row["body"].removeprefix("\\x"))
                yield row
            if len(rows) < batch_size:
                return

    def _one(self, family, filters=None):
        with closing(self.iter_rows(family, filters, batch_size=2)) as rows:
            first = next(rows, None)
            if first is None:
                raise PublishedRecordUnavailable("published native record is absent")
            if next(rows, None) is not None:
                raise ValueError("published native record is ambiguous")
            return first

    def record(self, record_id: str) -> dict[str, Any]:
        self._check_active()
        return self._cached_record(record_id)

    def _record(self, record_id: str) -> dict[str, Any]:
        return self._one("native", {"record_id": record_id})

    def members(self, parent_id: str, field_name: str):
        yield from self.iter_rows("membership", {"parent_id": parent_id, "field_name": field_name})

    def scalar(self, stream_id: str) -> Generator[bytes]:
        from .pdf_record_identity import ArtifactPart, ArtifactPin, replay_artifact

        stream = self._one("artifact_stream", {"stream_id": stream_id})
        pin = ArtifactPin(
            stream_id,
            self.revision["release_id"],
            self.revision["source_digest"],
            stream["byte_length"],
            stream["serialization_sha256"],
            bytes.fromhex(stream["byte_root"]),
        )
        budget = getattr(self, "read_budget", None)
        if budget is not None:
            budget.reserve(stream["byte_length"])
        parts = (
            ArtifactPart(
                stream_id,
                row["ordinal"],
                row["byte_offset"],
                row["byte_length"],
                row["body"],
                row["sha256_digest"],
            )
            for row in self.iter_rows(
                "artifact_part", {"stream_id": stream_id}, _payload_reserved=True
            )
        )
        with closing(parts) as owned_parts:
            for chunk in replay_artifact(
                owned_parts,
                pin,
                release_id=self.revision["release_id"],
                source_digest=self.revision["source_digest"],
            ):
                self._check_active()
                yield chunk
        self._check_active()

    @contextmanager
    def _projection_scope(self) -> Generator[_ProjectionParameters]:
        from ._operation_calls import ContentDigest, ProductKey, TaskId

        if self.projection_context is None:
            raise ValueError("selected published projection requires its explicit consumer release")
        with self._read_scope():
            yield _ProjectionParameters(
                task_id=TaskId(self.reference.task_id),
                product_key=ProductKey(self.reference.product_key),
                content_digest=ContentDigest(self.reference.content_digest),
                projection_context=self.projection_context,
            )

    def _projection_values(self, rows: Sequence[NativeRowResult], *, placement=True):
        from .published_document import PublishedDocumentBinding

        binding = PublishedDocumentBinding.from_revision(self.reference, self.revision)
        result = [
            self._admit_value(row.decoded_json_fields(operation="read_native_source"))
            for row in rows
        ]
        if placement and any(
            (row["product_id"], row["revision_id"])
            != (binding.native_build_id, binding.native_revision_id)
            for row in result
        ):
            raise ValueError("published projection escaped its exact placement")
        return result

    def sections(self, *, after=None, section_pointer=None, membership="direct", limit=None):
        def selected(statement):
            root = statement.subquery()
            query = select(root)
            if after is not None:
                query = query.where(root.c.ordinal > after)
            if section_pointer is not None:
                query = query.where(
                    literal(section_pointer) == any_(root.c.ancestors)
                    if membership == "descendants"
                    else root.c.parent_pointer == section_pointer
                )
            return query.order_by(root.c.ordinal).limit(limit)

        with self._projection_scope() as pin:
            rows = self._read_operation("read_published_sections", **pin, selection=selected)
        return self._projection_values(rows, placement=False)

    def section_nodes(self, section: str, membership: str):

        if membership not in {"direct", "descendants"}:
            raise ValueError("invalid published section membership")
        with self._projection_scope() as pin:
            rows = self._read_operation(
                "read_published_section_nodes", **pin, section=section, membership=membership
            )
        return self._projection_values(rows)

    def selected_native_items(self, pointers: Sequence[str]):

        with self._projection_scope() as pin:
            projected = self._read_operation(
                "read_published_items", **pin, pointers=tuple(pointers)
            )
        rows = self._projection_values(projected)
        values = {row["pointer"]: row["native_json"] for row in rows}
        if len(values) != len(set(pointers)) or set(values) != set(pointers):
            raise ValueError("published native item selection is absent or ambiguous")
        return values

    def require_native_item_inventory(self, pointers: Sequence[str]) -> None:
        """Validate complete address membership without transferring sibling bodies."""
        from ._operation_calls import prepare_read_published_items
        from .published_document import PublishedDocumentBinding

        wanted = tuple(dict.fromkeys(pointers))
        binding = PublishedDocumentBinding.from_revision(self.reference, self.revision)
        with self._projection_scope() as pin:
            selected = prepare_read_published_items(**pin, pointers=wanted)
            columns = selected.selected_columns
            statement = selected.with_only_columns(
                columns.product_id,
                columns.revision_id,
                columns.pointer,
                maintain_column_froms=True,
            ).order_by(None)
            rows = self._raw_rows(statement)
        actual = []
        for product, revision, pointer in rows:
            row = self._admit_value(dict(product_id=product, revision_id=revision, pointer=pointer))
            if (row["product_id"], row["revision_id"]) != (
                binding.native_build_id,
                binding.native_revision_id,
            ):
                raise ValueError("published inventory escaped its exact placement")
            actual.append(row["pointer"])
        if len(actual) != len(wanted) or set(actual) != set(wanted):
            raise ValueError("published native inventory is absent or ambiguous")

    def item_page(self, *, section=None, membership="direct", pointer=None, after=-1, limit=100):

        if membership not in {"direct", "descendants"}:
            raise ValueError("invalid published item membership")
        with self._projection_scope() as pin:
            rows = self._read_operation(
                "read_published_item_page",
                **pin,
                section=section,
                membership=membership,
                pointer=pointer,
                after=after,
                limit=limit,
            )
        return self._projection_values(rows)

    def regions(self, pointer: str):

        with self._projection_scope() as pin:
            rows = self._read_operation("read_published_regions", **pin, pointer=pointer)
        return self._projection_values(rows)

    def selected_regions(self, pointers: Sequence[str]):

        with self._projection_scope() as pin:
            rows = self._read_operation(
                "read_published_region_batch", **pin, pointers=tuple(pointers)
            )
        return self._projection_values(rows)

    def item_ancestors(self, pointer: str):

        with self._projection_scope() as pin:
            rows = self._read_operation("read_published_item_ancestors", **pin, pointer=pointer)
        return self._projection_values(rows)

    def _remember_metadata_report(self, row, body):
        cache = self.__dict__.setdefault("_metadata_report_cache", OrderedDict())
        cache[row["local_id"]] = body
        cache.move_to_end(row["local_id"])
        if len(cache) > 256:
            cache.popitem(last=False)
        order = self.__dict__.setdefault("_metadata_report_order", {})
        order[row["local_id"]] = (row["ordinal"], row["local_id"])

    def _metadata_report_index(self, kind):
        """Scan one known family in bounded pages, retaining addresses rather than bodies."""
        indexes = self.__dict__.setdefault("_metadata_report_indexes", {})
        if kind in indexes:
            return indexes[kind]
        index = {}
        for row in self.iter_rows("companion", {"family": "native_metadata", "kind": kind}):
            body = self.decode_companion_row(row)
            value = body["value"]
            pointers = (
                value["item_pointers"]
                if kind == "inline_alignment_reports"
                else (value["table_pointer" if kind == "cell_reports" else "pointer"],)
            )
            for pointer in pointers:
                index.setdefault(pointer, []).append(row["local_id"])
            self._remember_metadata_report(row, body)
        indexes[kind] = index
        return index

    def _metadata_report_value(self, local_id):
        from copy import deepcopy

        cache = self.__dict__.setdefault("_metadata_report_cache", OrderedDict())
        if local_id not in cache:
            row = self._one("companion", {"family": "native_metadata", "local_id": local_id})
            self._remember_metadata_report(row, self.decode_companion_row(row))
        cache.move_to_end(local_id)
        # Callers can attach presentation custody without changing original retained values.
        return deepcopy(cache[local_id])

    def selected_item_reports(
        self,
        pointers: Sequence[str],
        *,
        kinds=(
            "cell_reports",
            "derivation_mappings",
            "inline_alignment_reports",
        ),
    ):
        """Select known diagnostics through original byte-owned companion fields.

        Single-pointer cell/derivation reads use their existing native selector. An
        inline or bulk family is streamed once per reader into a pointer/local-id
        index; at most 256 decoded reports remain cached. No native JSONB conversion
        is used for opaque values or arbitrary strings.
        """
        from .contracts import bound_execution_model

        allowed = {"cell_reports", "derivation_mappings", "inline_alignment_reports"}
        if not set(kinds) <= allowed:
            raise ValueError("unknown selected native diagnostic family")
        with self._projection_scope() as pin:
            bound_execution_model(pin["projection_context"]).require_operation("read_native_source")
            if not pointers:
                return []
            selected = set(pointers)
            ancestry = set()
            local_ids = set()
            for kind in dict.fromkeys(kinds):
                if kind != "inline_alignment_reports" and len(selected) == 1:
                    for row in self.iter_rows(
                        "companion",
                        {
                            "family": "native_metadata",
                            "kind": kind,
                            "pointer": next(iter(selected)),
                        },
                    ):
                        self._remember_metadata_report(row, self.decode_companion_row(row))
                        local_ids.add(row["local_id"])
                    continue
                if kind == "inline_alignment_reports" and not ancestry:
                    ancestry = {
                        row["pointer"]
                        for pointer in selected
                        for row in self.item_ancestors(pointer)
                    }
                index = self._metadata_report_index(kind)
                for pointer in ancestry if kind == "inline_alignment_reports" else selected:
                    local_ids.update(index.get(pointer, ()))
            order = self.__dict__.get("_metadata_report_order", {})
            return [
                dict(
                    local_id=local_id,
                    ordinal=order[local_id][0],
                    body=self._metadata_report_value(local_id),
                )
                for local_id in sorted(local_ids, key=order.__getitem__)
            ]

    def section_reports(self, pointers: Sequence[str], sections: Sequence[str]):

        with self._projection_scope() as pin:
            rows = self._read_operation(
                "read_published_section_reports",
                **pin,
                pointers=tuple(pointers),
                sections=tuple(sections),
            )
        return self._projection_values(rows, placement=False)

    def region(self, pointer: str, region_index: int):

        with self._projection_scope() as pin:
            row = self._read_operation(
                "read_published_region", **pin, pointer=pointer, region_index=region_index
            )
        row = row[0] if len(row) == 1 else None
        if row is None:
            raise PublishedRegionUnavailable("published region is absent or ambiguous")
        return self._projection_values((row,))[0]

    def _profile(self, stream_id):
        return self._one("artifact_stream", {"stream_id": stream_id})["encoding_profile"]

    def hydrate(self, record_id: str, *, native_type: str) -> dict[str, Any]:
        from .pdf_records import reconstruct_native_document

        class Profiles(dict[str, str]):
            def __missing__(_, stream_id):
                value = self._profile(stream_id)
                _[stream_id] = value
                return value

        self._check_active()
        value = reconstruct_native_document(
            self,
            record_id,
            scalar_profiles=Profiles(),
            native_type=native_type,
            mapping=self._native_schema_mapping(),
        )
        self._check_active()
        return value

    def _native_schema_mapping(self):
        """Decode requested native values with their retained producer schema bytes."""
        from sqlalchemy import select

        from .metadata import table
        from .pdf_records import NativeMappingError, prepare_native_schema_mapping

        if not hasattr(self, "_prepared_native_mapping"):
            context = self._payload_context()
            context.execution.require_operation("read_pdf_product")
            digest = self.revision["schema_digest"]
            if digest != context.native_schema_digest:
                raise PublishedSchemaUnavailable(
                    "native record schema differs from its producer archive"
                )
            artifacts = table("kb.source_artifact")
            statement = select(artifacts.c.content).where(artifacts.c.artifact_digest == digest)
            budget = getattr(self, "read_budget", None)
            if budget is not None:
                length = self.conn.execute(
                    select(func.octet_length(artifacts.c.content)).where(
                        artifacts.c.artifact_digest == digest
                    )
                ).scalar_one_or_none()
                if length is not None:
                    budget.reserve(length)
            with self._read_scope(), self.conn.execute(statement) as result:
                retained = result.scalar_one_or_none()
            if retained is None:
                raise PublishedSchemaUnavailable("retained native schema artifact is missing")
            schema = bytes(retained)
            if sha256(schema).hexdigest() != digest:
                raise PublishedSchemaUnavailable(
                    "retained native schema bytes differ from their digest"
                )
            try:
                self._prepared_native_mapping = prepare_native_schema_mapping(
                    schema, allow_archived_default=True
                )
            except (NativeMappingError, json.JSONDecodeError) as error:
                raise PublishedSchemaUnavailable(
                    "retained native schema has no supported mapping"
                ) from error
        return self._prepared_native_mapping

    def hydrate_document(self):
        """Explicit whole-value demand uses one ordered native cursor, without repairs."""
        with closing(self.iter_native_json()) as chunks:
            value = json.loads(b"".join(chunks))
        self._check_active()
        return value

    def product_kind(self) -> str:
        self._check_active()
        return self.revision["kind"]

    def validation_receipt(self):
        """Read immutable sealed assurance, including its original contract epoch."""
        from ._operation_calls import (
            materialize_read_pdf_published_validation,
            prepare_read_pdf_published_validation,
        )

        with (
            self._read_scope(),
            self.conn.execute(
                prepare_read_pdf_published_validation(**_record_parameters(self.reference))
            ) as result,
        ):
            row = result.one_or_none()
            return None if row is None else materialize_read_pdf_published_validation(row)

    def product_descriptor(self) -> dict[str, Any]:
        """Retain assessed integration health without hydrating native content."""
        from itertools import islice

        self._payload_context().execution.require_operation("read_pdf_product")
        with closing(self.iter_rows("companion", {"family": "health"}, batch_size=3)) as rows:
            health_rows = [self.decode_companion_row(row) for row in islice(rows, 3)]
        if len(health_rows) > 2:
            raise ValueError("published product health inventory is ambiguous")
        assessments = [row for row in health_rows if "source_scope" not in row]
        if len(assessments) > 1:
            raise ValueError("published product integration health is ambiguous")
        descriptor = dict(version=2, kind=self.product_kind(), revision=dict(self.revision))
        if assessments:
            descriptor["health"] = assessments[0]
        return descriptor

    def native_items(self, pointers):
        """Archived producer decoding; explicit native consumers retain this port."""
        result = {}
        for pointer in dict.fromkeys(pointers):
            row = self._one("native", {"native_address": pointer})
            result[pointer] = self.hydrate(row["record_id"], native_type=row["native_type"])
        return result

    def _metadata_rows(self, kind: str, *, pointer=None, page_nos: Sequence[int] | None = None):
        filters: dict[str, Any] = {"family": "native_metadata", "kind": kind}
        if pointer is not None:
            filters["pointer"] = pointer
        if page_nos is not None:
            if any(type(number) is not int or number < 1 for number in page_nos):
                raise ValueError("payload page selectors require positive integer page numbers")
            if not page_nos:
                return
            filters["page_nos"] = sorted(set(page_nos))
        yield from self.iter_rows("companion", filters)

    def _payload_context(self):
        """Prepare once from the producing release, independent of installed current schemas."""
        if not hasattr(self, "_prepared_payload_context"):
            from .pdf_contracts import pdf_context_for_release
            from .releases import open_release

            with self._read_scope():
                self._prepared_payload_context = pdf_context_for_release(
                    self.conn, open_release(self.conn, self.revision["release_id"])
                )
        return self._prepared_payload_context

    def has_native_metadata(self, kind: str) -> bool:
        with closing(
            self.iter_rows("companion", {"family": "native_metadata", "kind": kind}, batch_size=1)
        ) as rows:
            return next(rows, None) is not None

    def native_metadata(self, kind, *, pointer=None, page_nos: Sequence[int] | None = None):
        """Materialize only selected metadata pages, preserving the logical Python contract."""
        for row in self._metadata_rows(kind, pointer=pointer, page_nos=page_nos):
            yield self.decode_companion_row(row)["value"]

    def iter_payload_batches(
        self,
        kind: str = "inline_candidate_pages",
        *,
        page_nos: Sequence[int] | None = None,
        columns: Sequence[str] | None = None,
        context=None,
    ) -> Iterator[pa.RecordBatch]:
        """Yield owned selected-page batches after closing each artifact result page."""
        from .pdf_payloads import FAMILY, PROFILE, prepare_payload_family

        if kind != FAMILY:
            raise ValueError("metadata family has no declared Arrow payload realization")
        for row in self._metadata_rows(kind, page_nos=page_nos):
            body = row["body"]
            fields = row.get("_fields", ())
            if len(fields) != 1 or fields[0]["field_name"] != "value":
                raise ValueError("page payload requires exactly one external value")
            field = fields[0]
            if body.get("payload_codec") != PROFILE or field["encoding_profile"] != PROFILE:
                raise ValueError(
                    "page payload encoding profile differs from envelope: "
                    f"expected={PROFILE!r}, envelope={body.get('payload_codec')!r}, "
                    f"field={field['encoding_profile']!r}; inspect the producing release "
                    "and rebuild from compatible retained evidence"
                )
            payload = b"".join(self.scalar(field["stream_id"]))
            self._check_active()
            # scalar() verifies the admitted immutable artifact's byte root and SHA. Selected
            # columns retain schema/framing checks without rescanning unrelated OCR values.
            batch = prepare_payload_family(
                context if context is not None else self._payload_context()
            ).read_batch(
                payload,
                schema_digest=body["payload_schema_digest"],
                logical_digest=body["payload_logical_digest"] if columns is None else None,
                columns=columns,
            )
            self._check_active()
            yield batch

    def candidate_bases(self, addresses: Sequence[tuple[int, int]]) -> dict[tuple[int, int], str]:
        """Read selected candidate basis scalars without decoding page/OCR mappings."""
        wanted = set(addresses)
        if not wanted:
            return {}
        result = {}
        for batch in self.iter_payload_batches(
            page_nos=sorted({page for page, _ in wanted}), columns=("page_no", "candidates")
        ):
            page = batch.column("page_no")[0].as_py()
            candidates = batch.column("candidates")[0]
            if not candidates.is_valid:
                continue
            bases = candidates.values.field("basis")
            for address in wanted:
                if address[0] == page and 0 <= address[1] < len(bases):
                    result[address] = bases[address[1]].as_py()
        if result.keys() != wanted:
            raise ValueError("inline diagnostic candidate is absent from admitted page inventory")
        return result

    def candidate_inventory(self, *, page_nos: Sequence[int] | None = None, context=None):
        """Project page inventory through Arrow kernels without hydrating candidate/OCR objects."""
        for batch in self.iter_payload_batches(
            page_nos=page_nos, columns=("page_no", "candidates", "ocr_regions"), context=context
        ):
            candidates = pc.call_function("list_value_length", [batch.column("candidates")])
            regions = batch.column("ocr_regions")
            region_count = pc.call_function("list_value_length", [regions])
            # Each payload is exactly one page; nested word inventory stays in columnar arrays.
            lines = pc.call_function(
                "list_flatten",
                [
                    pc.call_function(
                        "struct_field",
                        [pc.call_function("list_flatten", [regions])],
                        options=pc.StructFieldOptions("lines"),
                    )
                ],
            )
            words = pc.call_function(
                "list_flatten",
                [pc.call_function("struct_field", [lines], options=pc.StructFieldOptions("words"))],
            )
            yield {
                "page_no": batch.column("page_no")[0].as_py(),
                "candidate_count": candidates[0].as_py() or 0,
                "ocr_region_count": region_count[0].as_py() or 0,
                "ocr_word_count": len(words),
            }

    def iter_candidate_payloads(self, *, context=None):
        """Yield exact source-qualified IPC bytes without reconstructing nested values."""
        from .pdf_payloads import PROFILE, EncodedPagePayload, prepare_payload_family

        family = prepare_payload_family(context if context is not None else self._payload_context())
        for row in self._metadata_rows("inline_candidate_pages"):
            body = row["body"]
            fields = row.get("_fields", ())
            if len(fields) != 1 or fields[0]["field_name"] != "value":
                raise ValueError("page payload requires exactly one external value")
            field = fields[0]
            if body.get("payload_codec") != PROFILE or field["encoding_profile"] != PROFILE:
                raise ValueError("page payload requires its released Arrow realization")
            payload = b"".join(self.scalar(field["stream_id"]))
            batch = family.read_batch(
                payload,
                schema_digest=body["payload_schema_digest"],
                logical_digest=body["payload_logical_digest"],
            )
            page_no = batch.column("page_no")[0].as_py()
            if page_no != body["page_no"]:
                raise ValueError("candidate payload page differs from its envelope")
            self._check_active()
            yield EncodedPagePayload(
                payload, body["payload_schema_digest"], body["payload_logical_digest"], page_no
            )

    def native_product_values(self, *, include_candidate_pages: bool = True):
        """Explicit materialization for native transformations; never a small read."""
        document = self.hydrate_document()
        health_rows = list(self.iter_companions("health"))
        wrappers = [h for h in health_rows if "source_scope" in h]
        if len(wrappers) != 1:
            raise ValueError("native health/source scope is absent or ambiguous")
        wrapper = wrappers[0]
        health = {
            key: value
            for key, value in wrapper.items()
            if key not in {"source_scope", "page_start", "page_end"}
        }
        outcomes = list(self.native_metadata("formula_outcomes"))
        if outcomes:
            health["formula_outcomes"] = outcomes
        value = dict(
            recipe="pdf-native-v1",
            native_schema_version=document["version"],
            derivation_mappings=[],
            product_key=self.reference.product_key,
            artifact_digest=self.revision["source_digest"],
            schema_digest=self.revision["schema_digest"],
            recipe_digest=self.revision["recipe_digest"],
            document=document,
            source_scope=wrapper["source_scope"],
            health=health,
        )
        if wrapper["source_scope"] == "page_range":
            if not all(key in wrapper for key in ("page_start", "page_end")):
                raise ValueError("native page range has no admitted bounds")
            value.update(page_start=wrapper["page_start"], page_end=wrapper["page_end"])
        for kind in (
            "inline_candidate_pages",
            "derivation_mappings",
            "cell_reports",
            "inline_alignment_reports",
            "recognition_coverage",
        ):
            if kind == "inline_candidate_pages" and not include_candidate_pages:
                continue
            values = list(self.native_metadata(kind))
            if values:
                value[kind] = values
        structural = next(
            (r for r in self.iter_companions("input") if r.get("role") == "structural"), None
        )
        if structural is not None:
            value.update(
                parent_task_id=structural["task_id"],
                parent_product_key=structural["product_key"],
                parent_digest=structural["content_digest"],
            )
        runtime = list(self.native_metadata("runtime_report"))
        if runtime:
            if len(runtime) != 1:
                raise ValueError("native runtime metadata is ambiguous")
            value["runtime_report"] = runtime[0]
        return value

    def decode_companion_row(self, row: Mapping[str, Any]) -> dict[str, Any]:
        """Materialize one requested field from exact bytes, retaining JSON float bits."""
        self._check_active()
        body = dict(row["body"])
        if row.get("family") == "native_metadata":
            for projection in _METADATA_PROJECTIONS:
                body.pop(projection, None)
        for field in row.get("_fields", ()):
            name, kind = field["field_name"], field["scalar_kind"]
            if name in body:
                raise ValueError("companion field has both inline and external values")
            payload = b"".join(self.scalar(field["stream_id"]))
            from .pdf_payloads import PROFILE, decode_page_payload

            self._check_active()
            profile = field["encoding_profile"]
            if profile == PROFILE:
                if row["body"].get("payload_codec") != PROFILE:
                    raise ValueError("page payload encoding profile differs from envelope")
                body[name] = decode_page_payload(
                    payload,
                    self._payload_context(),
                    schema_digest=row["body"]["payload_schema_digest"],
                    logical_digest=row["body"]["payload_logical_digest"],
                )
            elif kind == "y":
                body[name] = json.loads(payload)
            elif kind == "s":
                body[name] = payload.decode("utf-8")
            else:
                raise ValueError("unsupported companion scalar kind")
            self._check_active()
        self._check_active()
        return body

    def iter_companions(self, family) -> Iterator[Mapping[str, Any]]:
        for row in self.iter_rows("companion", {"family": family}):
            yield self.decode_companion_row(row)

    def iter_companion_export_events(self, family) -> Generator[dict[str, Any]]:
        from ._operation_calls import (
            materialize_read_pdf_companion_export_events,
            prepare_read_pdf_companion_export_events,
        )

        with (
            self._read_scope(),
            self.conn.execute(
                prepare_read_pdf_companion_export_events(
                    **_record_parameters(self.reference),
                    family=family,
                ).execution_options(yield_per=32),
            ) as result,
        ):
            for row in result:
                self._check_active()
                yield _record_envelope(materialize_read_pdf_companion_export_events(row))

    def iter_companion_json(self, family, events=None) -> Generator[bytes]:
        """One joined cursor streams exact fields without per-field SQL or JSONB coercion."""
        from .pdf_record_identity import ArtifactPart, ArtifactPin, replay_artifact

        def encode(value):
            self._check_active()
            encoded = json.dumps(
                value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
            ).encode()
            self._check_active()
            return encoded

        owns_events = events is None
        events = self.iter_companion_export_events(family) if owns_events else events
        pending = None
        envelope = {}
        first_row = True
        first_field = True
        try:
            while True:
                self._check_active()
                event = pending if pending is not None else next(events, None)
                pending = None
                if event is None:
                    return
                kind = event["kind"]
                if kind == "row":
                    if not first_row:
                        yield b","
                    first_row = False
                    envelope = event["body"]
                    body = dict(envelope)
                    if family == "native_metadata":
                        for projection in _METADATA_PROJECTIONS:
                            body.pop(projection, None)
                    encoded = encode(body)
                    yield b"{" + encoded[1:-1]
                    first_field = not bool(body)
                elif kind == "field":
                    field = event["field"]
                    yield (b"" if first_field else b",") + encode(field["field_name"]) + b":"
                    first_field = False
                    pin = ArtifactPin(
                        field["stream_id"],
                        self.revision["release_id"],
                        self.revision["source_digest"],
                        field["byte_length"],
                        field["serialization_sha256"],
                        bytes.fromhex(field["byte_root"]),
                    )

                    def parts():
                        nonlocal pending
                        for following in events:
                            if following["kind"] != "part":
                                pending = following
                                return
                            part = following["part"]
                            yield ArtifactPart(
                                part["stream_id"],
                                part["ordinal"],
                                part["byte_offset"],
                                part["byte_length"],
                                bytes.fromhex(part["body"].removeprefix("\\x")),
                                part["sha256_digest"],
                            )

                    chunks = replay_artifact(
                        parts(),
                        pin,
                        release_id=self.revision["release_id"],
                        source_digest=self.revision["source_digest"],
                    )
                    from .pdf_payloads import PROFILE, decode_page_payload

                    if field["encoding_profile"] == PROFILE:
                        if envelope.get("payload_codec") != PROFILE:
                            raise ValueError("page payload encoding profile differs from envelope")
                        yield encode(
                            decode_page_payload(
                                b"".join(chunks),
                                self._payload_context(),
                                schema_digest=envelope["payload_schema_digest"],
                                logical_digest=envelope["payload_logical_digest"],
                            )
                        )
                    elif field["scalar_kind"] == "y":
                        yield from chunks
                    elif field["scalar_kind"] == "s":
                        yield b'"'
                        decoder = codecs.getincrementaldecoder("utf-8")()
                        for chunk in chunks:
                            yield encode(decoder.decode(chunk))[1:-1]
                        yield encode(decoder.decode(b"", final=True))[1:-1]
                        yield b'"'
                    else:
                        raise ValueError("unsupported companion scalar kind")
                elif kind == "close":
                    yield b"}"
                else:
                    raise ValueError("unexpected companion export event")
        finally:
            if owns_events:
                events.close()

    def context_rows(self, family, pointers, section_pointer):
        from ._operation_calls import (
            materialize_read_pdf_record_context_rows,
            prepare_read_pdf_record_context_rows,
        )

        after = ""
        while True:
            statement = prepare_read_pdf_record_context_rows(
                **_record_parameters(self.reference),
                pointers=tuple(pointers),
                section=section_pointer,
                family=family,
                after=after,
                limit=64,
            )
            rows = [
                self._admit_value(_record_envelope(materialize_read_pdf_record_context_rows(row)))
                for row in self._raw_rows(statement)
            ]
            for row in rows:
                self._check_active()
                after = row["local_id"]
                yield row
            if len(rows) < 64:
                return

    def source_context(
        self,
        pointers,
        section_pointer,
        *,
        row_budget: int | None = None,
        membership: str = "direct",
    ) -> dict[str, Any]:
        """Use the same published relational context constructor as native frame guards."""
        from ._operation_calls import (
            materialize_record_integrated_source_context,
            prepare_record_integrated_source_context,
        )

        statement = prepare_record_integrated_source_context(
            **_record_parameters(self.reference),
            pointers=tuple(pointers),
            section=section_pointer,
            membership=membership,
            row_budget=row_budget,
        )
        rows = self._raw_rows(statement)
        if len(rows) != 1:
            raise ValueError("published source context is unavailable or ambiguous")
        return self._admit_value(
            _record_envelope(materialize_record_integrated_source_context(rows[0]))
        )

    def occurrence_context(
        self, selected: Sequence[Mapping[str, Any]], section_pointer: str, *, row_budget: int
    ) -> dict[str, Any]:
        """Compose exact occurrence relationships through existing protected byte selectors."""
        if row_budget < 1:
            raise ValueError("PDF companion row budget must be positive")
        count = 0

        def consume(amount=1):
            nonlocal count
            count += amount
            if count > row_budget:
                raise ValueError("PDF mandatory companion exceeds requested row budget")

        own = self.reference.task_id, self.reference.product_key, self.reference.content_digest

        def target(endpoint):
            pin = (
                endpoint["target_task_id"],
                endpoint["target_product_key"],
                endpoint["target_content_digest"],
            )
            return own if pin == (0, "@self", "@self") else pin

        def wrap(**value) -> dict[str, Any]:
            return dict(task_id=own[0], product_key=own[1], **value)

        occurrences, relation_ids, input_indices = [], set(), set()
        pointers = set()
        for row in selected:
            consume()
            body = self.decode_companion_row(row)
            local = row["local_id"]
            pointer = body.get("pointer")
            if pointer is not None:
                pointers.add(pointer)
            occurrences.append(
                wrap(
                    occurrence_id=local,
                    pointer=pointer,
                    kind=body["kind"],
                    precision=body["precision"],
                    address_space=body["address_space"],
                    body=body,
                )
            )
            with closing(self.iter_rows("endpoint", {"occurrence_id": local})) as endpoints:
                for endpoint in endpoints:
                    if target(endpoint) == own:
                        relation_ids.add(endpoint["relation_id"])
                        if len(relation_ids) + len(occurrences) > row_budget:
                            consume(row_budget + 1)
        relations = []
        for relation_id in sorted(relation_ids):
            consume()
            row = self._one("companion", {"family": "relation", "local_id": relation_id})
            body = self.decode_companion_row(row)
            input_indices.update(
                endpoint["input_index"]
                for endpoint in body["endpoints"]
                if endpoint.get("input_index") is not None
            )
            rendered = []
            with closing(self.iter_rows("endpoint", {"relation_id": relation_id})) as endpoints:
                for endpoint in endpoints:
                    consume()
                    task, key, digest = target(endpoint)
                    rendered.append(
                        wrap(
                            relation_id=relation_id,
                            endpoint_index=endpoint["ordinal"],
                            role=endpoint["role"],
                            target_task_id=task,
                            target_product_key=key,
                            target_content_digest=digest,
                            occurrence_id=endpoint["occurrence_id"],
                        )
                    )
            relations.append(
                (
                    row["ordinal"],
                    relation_id,
                    wrap(
                        relation_id=relation_id,
                        kind=body["kind"],
                        body={key: value for key, value in body.items() if key != "endpoints"},
                        endpoints=rendered,
                    ),
                )
            )
        coverage = []
        # Only typed scoped coverage metadata is selected here. Occurrence/relation
        # bodies are never obtained through a broader table-pointer context.
        with closing(self.context_rows("coverage", sorted(pointers), section_pointer)) as rows:
            for row in rows:
                consume()
                body = row["body"]
                input_indices.update(support["input_index"] for support in body.get("supports", ()))
                coverage.append(wrap(coverage_id=row["local_id"], body=body))
        inputs = []
        for index in sorted(input_indices):
            consume()
            row = self._one("companion", {"family": "input", "local_id": str(index)})
            body = self.decode_companion_row(row)
            inputs.append(
                wrap(
                    input_index=index,
                    role=body["role"],
                    input_task_id=body["task_id"],
                    input_product_key=body["product_key"],
                    input_content_digest=body["content_digest"],
                )
            )
        reports = []
        if input_indices:
            with closing(
                self.context_rows("mapping_report", sorted(pointers), section_pointer)
            ) as rows:
                for row in rows:
                    body = row["body"]
                    if body.get("input_index") in input_indices:
                        consume()
                        reports.append(
                            wrap(
                                report_index=int(row["local_id"]),
                                input_index=body.get("input_index"),
                                body=body,
                            )
                        )
        return dict(
            selection=dict(task_id=own[0], product_key=own[1], content_digest=own[2]),
            descriptor=dict(version=2, kind=self.product_kind(), revision=dict(self.revision)),
            occurrences=occurrences,
            relations=[
                row[2]
                for row in sorted(relations, key=lambda row: (row[0] is None, row[0], row[1]))
            ],
            inputs=inputs,
            coverage=coverage,
            mapping_reports=reports,
        )

    def iter_native_json(self, events=None) -> Generator[bytes]:
        """One ordered containment cursor; scalar parts remain bounded owned reads."""
        from .pdf_records import _decode_scalar, _parse_inline

        def encode(value):
            self._check_active()
            encoded = json.dumps(
                value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
            ).encode()
            self._check_active()
            return encoded

        def scalar(stream_id):
            profile = self._profile(stream_id)
            with closing(self.scalar(stream_id)) as chunks:
                if profile == "pdf-record-native-json-v1":
                    yield from chunks
                elif profile == "pdf-record-scalar-v1:s":
                    yield b'"'
                    decoder = codecs.getincrementaldecoder("utf-8")()
                    for chunk in chunks:
                        yield encode(decoder.decode(chunk))[1:-1]
                    yield encode(decoder.decode(b"", final=True))[1:-1]
                    yield b'"'
                else:
                    yield encode(_decode_scalar(chunks, profile))

        scope = closing(self.iter_native_events()) if events is None else nullcontext(events)
        with scope as owned_events:
            for event in owned_events:
                self._check_active()
                kind, value = event["kind"], event["value"]
                if kind == "literal":
                    yield value.encode("utf-8")
                elif kind == "inline":
                    yield encode(_parse_inline(value))
                elif kind in {"parts", "key_parts"}:
                    if kind == "key_parts":
                        yield event["prefix"].encode()
                    yield from scalar(value)
                    if kind == "key_parts":
                        yield b":"
                elif kind == "extension":
                    pending, opened, separator = b"", False, event["prefix"]
                    with closing(self.scalar(value)) as chunks:
                        for chunk in chunks:
                            if not opened:
                                if not chunk.startswith(b"{"):
                                    raise ValueError("native extension is not an object")
                                chunk, opened = chunk[1:], True
                            pending += chunk
                            if len(pending) > 1:
                                if separator:
                                    yield separator.encode()
                                    separator = ""
                                yield pending[:-1]
                                pending = pending[-1:]
                    if not opened or pending != b"}":
                        raise ValueError("native extension object is incomplete")
                else:
                    raise ValueError("unsupported published export event")

    def iter_native_events(self) -> Generator[dict[str, Any]]:
        from ._operation_calls import (
            materialize_read_pdf_native_events,
            prepare_read_pdf_native_events,
        )

        with (
            self._read_scope(),
            self.conn.execute(
                prepare_read_pdf_native_events(
                    **_record_parameters(self.reference)
                ).execution_options(yield_per=256),
            ) as result,
        ):
            for row in result:
                self._check_active()
                yield _record_envelope(materialize_read_pdf_native_events(row))

    def write_native_json(self, sink: BinaryIO) -> PdfExportReceipt:
        digest, size = sha256(), 0
        with closing(self.iter_native_json()) as chunks:
            for chunk in chunks:
                self._check_active()
                sink.write(chunk)
                self._check_active()
                digest.update(chunk)
                size += len(chunk)
        self._check_active()
        return PdfExportReceipt(size, digest.hexdigest())

    def write_integrated_json(self, sink: BinaryIO, *, binding=None) -> PdfExportReceipt:
        """Version2 export carries native values, typed companions and immutable bindings.

        Its serialization hash is distinct from the admitted logical digest. It is
        not the historical version1 canonical-envelope replay format.
        """
        if self.product_kind() != "integrated":
            raise ValueError("integrated JSON export requires an integrated product")
        return self._write_complete_json(
            sink, binding=binding, export_profile="pdf-integrated-record-export-v2"
        )

    def write_complete_json(self, sink: BinaryIO, *, binding=None) -> PdfExportReceipt:
        """Stream a complete native or integrated document and every retained companion."""
        if self.product_kind() not in {"native", "integrated"}:
            raise ValueError("complete JSON export requires a document product")
        return self._write_complete_json(
            sink, binding=binding, export_profile="pdf-complete-record-export-v1"
        )

    def _write_complete_json(self, sink: BinaryIO, *, binding, export_profile) -> PdfExportReceipt:
        digest, size = sha256(), 0

        def write(chunk):
            nonlocal size
            self._check_active()
            sink.write(chunk)
            self._check_active()
            digest.update(chunk)
            size += len(chunk)

        def encode(value):
            self._check_active()
            encoded = json.dumps(
                value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
            ).encode()
            self._check_active()
            return encoded

        write(
            b'{"export_profile":'
            + encode(export_profile)
            + b',"binding":'
            + encode(binding or {})
            + b',"product":{"version":2,"kind":'
            + encode(self.product_kind())
            + b',"product_key":'
            + encode(self.reference.product_key)
            + b',"logical_digest":'
            + encode(self.reference.content_digest)
            + b',"revision":'
            + encode(self.revision)
            + b',"content":'
        )
        with closing(self.iter_native_json()) as chunks:
            for chunk in chunks:
                write(chunk)
        for family, name in (
            ("input", "inputs"),
            ("occurrence", "occurrences"),
            ("relation", "relations"),
            ("mapping_report", "mapping_reports"),
            ("coverage", "coverage"),
            ("health", "health"),
            ("request_outcome", "request_outcomes"),
            ("native_metadata", "native_metadata"),
        ):
            write(b"," + encode(name) + b":[")
            with closing(self.iter_companion_json(family)) as chunks:
                for chunk in chunks:
                    write(chunk)
            write(b"]")
        write(b"}}")
        self._check_active()
        return PdfExportReceipt(size, digest.hexdigest())
