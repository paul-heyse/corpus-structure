"""Selective published record reads and explicitly streamed native serialization.

The caller owns the Connection and its snapshot. Iterators own only bounded result
pages; no iterator returns a model initialized from a different product pin.
"""

from __future__ import annotations

import codecs
import json
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from typing import Any, BinaryIO

from sqlalchemy import Connection, text

from .product_reference import ProductReference


@dataclass(frozen=True, slots=True)
class PdfExportReceipt:
    byte_length: int
    serialization_sha256: str


def published_native_table(conn: Connection, kind: str = "item"):
    """Use current published projections, retaining the archived deployment route."""
    from sqlalchemy import MetaData
    from .metadata import table
    if kind not in {"item", "region"}:
        raise ValueError("unknown native access projection")
    name = "ops.pdf_published_" + kind
    exists = conn.execute(text("SELECT to_regclass(:name) IS NOT NULL"), {"name": name}).scalar_one()
    legacy = table("kb.native_document_" + kind)
    return legacy.to_metadata(MetaData(), name="pdf_published_" + kind, schema="ops") if exists else legacy


def published_record_reader(conn: Connection, reference: ProductReference):
    """Return the published port, or None for an explicitly archived PDF product."""
    available = conn.execute(text(
        "SELECT to_regprocedure('ops.read_pdf_published_revision(bigint,text,text)') IS NOT NULL"
    )).scalar_one()
    if not available:
        return None
    row = conn.execute(text(
        "SELECT * FROM ops.read_pdf_published_revision(:task,:product,:digest)"
    ), dict(task=reference.task_id, product=reference.product_key,
            digest=reference.content_digest)).mappings().one_or_none()
    return PublishedPdfReader(conn, reference, revision=dict(row)) if row else None


class PublishedPdfReader:
    def __init__(self, conn: Connection, reference: ProductReference, *, revision: Mapping[str, Any] | None = None):
        self.conn, self.reference = conn, reference
        if revision is None:
            row = conn.execute(text(
                "SELECT * FROM ops.read_pdf_published_revision(:task,:product,:digest)"
            ), dict(task=reference.task_id, product=reference.product_key,
                    digest=reference.content_digest)).mappings().one()
            revision = dict(row)
        self.revision: dict[str, Any] = dict(revision)
        self._cached_record: Callable[[str], dict[str, Any]] = lru_cache(maxsize=256)(self._record)

    def iter_rows(self, family: str, filters: Mapping[str, Any] | None = None,
                  *, after=None, batch_size: int = 100) -> Iterator[dict[str, Any]]:
        if not 1 <= batch_size <= 1000:
            raise ValueError("published record batch size must be 1..1000")
        while True:
            # Each bounded function call rechecks the immutable published binding. Close
            # Result before yielding so abandonment cannot leak a server-side cursor.
            with self.conn.execute(text(
                "SELECT * FROM ops.read_pdf_record_rows(:task,:product,:digest,:family,"
                "CAST(:filters AS jsonb),CAST(:after AS jsonb),:limit)"
            ).execution_options(yield_per=batch_size), dict(
                task=self.reference.task_id, product=self.reference.product_key,
                digest=self.reference.content_digest, family=family,
                filters=json.dumps(dict(filters or {})),
                after=json.dumps(after) if after is not None else None, limit=batch_size,
            )) as result:
                rows = [dict(r[0]) for r in result]
            if not rows:
                return
            for row in rows:
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
        rows = self.iter_rows(family, filters, batch_size=2)
        first = next(rows, None)
        if first is None or next(rows, None) is not None:
            raise ValueError("published native record is absent or ambiguous")
        return first

    def record(self, record_id: str) -> dict[str, Any]:
        return self._cached_record(record_id)

    def _record(self, record_id: str) -> dict[str, Any]:
        return self._one("native", {"record_id": record_id})

    def members(self, parent_id: str, field_name: str):
        yield from self.iter_rows("membership", {"parent_id": parent_id,
                                                 "field_name": field_name})

    def scalar(self, stream_id: str):
        from .pdf_record_identity import ArtifactPart, ArtifactPin, replay_artifact
        stream = self._one("artifact_stream", {"stream_id": stream_id})
        pin = ArtifactPin(stream_id, self.revision["release_id"],
                          self.revision["source_digest"], stream["byte_length"],
                          stream["serialization_sha256"], bytes.fromhex(stream["byte_root"]))
        parts = (ArtifactPart(stream_id, row["ordinal"], row["byte_offset"],
                              row["byte_length"], row["body"], row["sha256_digest"])
                 for row in self.iter_rows("artifact_part", {"stream_id": stream_id}))
        yield from replay_artifact(parts, pin, release_id=self.revision["release_id"],
                                   source_digest=self.revision["source_digest"])

    def _profile(self, stream_id):
        return self._one("artifact_stream", {"stream_id": stream_id})["encoding_profile"]

    def hydrate(self, record_id: str, *, native_type: str) -> dict[str, Any]:
        from .pdf_records import reconstruct_native_document
        class Profiles(dict[str, str]):
            def __missing__(_, stream_id):
                value = self._profile(stream_id)
                _[stream_id] = value
                return value
        return reconstruct_native_document(self, record_id, scalar_profiles=Profiles(),
                                            native_type=native_type)

    def hydrate_document(self):
        """Explicit whole-value demand uses one ordered native cursor, without repairs."""
        return json.loads(b"".join(self.iter_native_json()))

    def product_kind(self) -> str:
        return self.conn.execute(text(
            "SELECT kind FROM ops.pdf_product WHERE task_id=:task AND product_key=:product "
            "AND content_digest=:digest"
        ), dict(task=self.reference.task_id,product=self.reference.product_key,
                digest=self.reference.content_digest)).scalar_one()


    def native_items(self, pointers):
        result = {}
        for pointer in dict.fromkeys(pointers):
            row = self._one("native", {"native_address": pointer})
            result[pointer] = self.hydrate(row["record_id"], native_type=row["native_type"])
        return result

    def native_metadata(self, kind, *, pointer=None):
        filters = {"family":"native_metadata", "kind":kind}
        if pointer is not None:
            filters["pointer"] = pointer
        for row in self.iter_rows("companion", filters):
            yield row["body"]["value"]

    def native_product_values(self):
        """Explicit materialization for native transformations; never a small read."""
        document = self.hydrate_document()
        health_rows = list(self.iter_companions("health"))
        wrappers = [h for h in health_rows if "source_scope" in h]
        if len(wrappers) != 1:
            raise ValueError("native health/source scope is absent or ambiguous")
        wrapper = wrappers[0]
        health = {key:value for key,value in wrapper.items() if key not in {"source_scope", "page_start", "page_end"}}
        outcomes = list(self.native_metadata("formula_outcomes"))
        if outcomes:
            health["formula_outcomes"] = outcomes
        value = dict(recipe="pdf-native-v1", native_schema_version=document["version"],
                     derivation_mappings=[], product_key=self.reference.product_key,
                     artifact_digest=self.revision["source_digest"],
                     schema_digest=self.revision["schema_digest"],
                     recipe_digest=self.revision["recipe_digest"], document=document,
                     source_scope=wrapper["source_scope"], health=health)
        if wrapper["source_scope"] == "page_range":
            if not all(key in wrapper for key in ("page_start", "page_end")):
                raise ValueError("native page range has no admitted bounds")
            value.update(page_start=wrapper["page_start"],page_end=wrapper["page_end"])
        for kind in ("inline_candidate_pages", "derivation_mappings", "cell_reports",
                     "inline_alignment_reports", "recognition_coverage"):
            values = list(self.native_metadata(kind))
            if values:
                value[kind] = values
        structural = next((r for r in self.iter_companions("input") if r.get("role") == "structural"), None)
        if structural is not None:
            value.update(parent_task_id=structural["task_id"], parent_product_key=structural["product_key"],
                         parent_digest=structural["content_digest"])
        runtime = list(self.native_metadata("runtime_report"))
        if runtime:
            if len(runtime) != 1:
                raise ValueError("native runtime metadata is ambiguous")
            value["runtime_report"] = runtime[0]
        return value

    def iter_companions(self, family):
        for row in self.iter_rows("companion", {"family": family}):
            yield row["body"]

    def context_rows(self, family, pointers, section_pointer):
        after = ""
        while True:
            with self.conn.execute(text(
                "SELECT * FROM ops.read_pdf_record_context_rows(:task,:product,:digest,"
                "CAST(:pointers AS text[]),:section,:family,:after,:limit)"
            ), dict(task=self.reference.task_id, product=self.reference.product_key,
                    digest=self.reference.content_digest, pointers=list(pointers),
                    section=section_pointer, family=family, after=after, limit=100)) as result:
                rows = [dict(row[0]) for row in result]
            for row in rows:
                after = row["local_id"]
                yield row
            if len(rows) < 100:
                return

    def source_context(self, pointers, section_pointer, *, row_budget: int | None = None) -> dict[str, Any]:
        common = {"task_id": self.reference.task_id, "product_key": self.reference.product_key}
        used = 0
        def consume(family):
            nonlocal used
            for row in self.context_rows(family, pointers, section_pointer):
                used += 1
                if row_budget is not None and used > row_budget:
                    raise ValueError("PDF mandatory companion exceeds requested row budget")
                yield row
        inputs = {int(row["local_id"]):row["body"] for row in consume("input")}
        def wrapped(family):
            nonlocal used
            for row in consume(family):
                body, index = row["body"], row["local_id"]
                if family == "occurrence":
                    yield dict(common, occurrence_id=body["occurrence_id"],
                               pointer=body.get("pointer"), kind=body["kind"], body=body)
                elif family == "relation":
                    endpoints = []
                    for ordinal, endpoint in enumerate(body["endpoints"]):
                        used += 1
                        if row_budget is not None and used > row_budget:
                            raise ValueError("PDF mandatory companion exceeds requested row budget")
                        target = inputs[endpoint["input_index"]] if "input_index" in endpoint else self.reference.values()
                        endpoints.append(dict(common, relation_id=body["relation_id"],
                            endpoint_index=ordinal, role=endpoint["role"],
                            target_task_id=target["task_id"],target_product_key=target["product_key"],
                            target_content_digest=target["content_digest"],occurrence_id=endpoint["occurrence_id"]))
                    yield dict(common, relation_id=body["relation_id"], kind=body["kind"],
                               body={k:v for k,v in body.items() if k != "endpoints"}, endpoints=endpoints)
                elif family == "coverage":
                    yield dict(common, coverage_id=body["coverage_id"], body=body)
                else:
                    yield dict(common, report_index=int(index), input_index=body["input_index"], body=body)
        return dict(selection=dict(common, content_digest=self.reference.content_digest),
                    descriptor={"version":2,"kind":"integrated","revision":self.revision},
                    inputs=[dict(common,input_index=index,role=body["role"], input_task_id=body["task_id"],
                                 input_product_key=body["product_key"], input_content_digest=body["content_digest"])
                            for index,body in sorted(inputs.items())],
                    **{name:list(wrapped(family)) for family,name in (
                        ("occurrence","occurrences"),("relation","relations"),
                        ("coverage","coverage"),("mapping_report","mapping_reports"))})

    def iter_native_json(self) -> Iterator[bytes]:
        """One ordered containment cursor; scalar parts remain bounded owned reads."""
        from .pdf_records import _parse_inline, _decode_scalar
        def encode(value):
            return json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode()
        def scalar(stream_id):
            profile = self._profile(stream_id)
            if profile == "pdf-record-native-json-v1":
                yield from self.scalar(stream_id)
            elif profile == "pdf-record-scalar-v1:s":
                yield b'"'
                decoder = codecs.getincrementaldecoder("utf-8")()
                for chunk in self.scalar(stream_id):
                    yield encode(decoder.decode(chunk))[1:-1]
                yield encode(decoder.decode(b"",final=True))[1:-1]
                yield b'"'
            else:
                yield encode(_decode_scalar(self.scalar(stream_id),profile))
        for event in self.iter_native_events():
            kind,value = event["kind"],event["value"]
            if kind == "literal":
                yield value.encode("utf-8")
            elif kind == "inline":
                yield encode(_parse_inline(value))
            elif kind in {"parts","key_parts"}:
                if kind == "key_parts":
                    yield event["prefix"].encode()
                yield from scalar(value)
                if kind == "key_parts":
                    yield b":"
            elif kind == "extension":
                pending,opened,separator = b"",False,event["prefix"]
                for chunk in self.scalar(value):
                    if not opened:
                        if not chunk.startswith(b"{"):
                            raise ValueError("native extension is not an object")
                        chunk,opened = chunk[1:],True
                    pending += chunk
                    if len(pending)>1:
                        if separator:
                            yield separator.encode(); separator=""
                        yield pending[:-1]
                        pending=pending[-1:]
                if not opened or pending != b"}":
                    raise ValueError("native extension object is incomplete")
            else:
                raise ValueError("unsupported published export event")

    def iter_native_events(self):
        with self.conn.execute(text(
            "SELECT * FROM ops.read_pdf_native_events(:task,:product,:digest)"
        ).execution_options(yield_per=256), dict(task=self.reference.task_id,
                 product=self.reference.product_key,digest=self.reference.content_digest)) as result:
            for row in result:
                yield row[0]

    def write_native_json(self, sink: BinaryIO) -> PdfExportReceipt:
        digest, size = sha256(), 0
        for chunk in self.iter_native_json():
            sink.write(chunk)
            digest.update(chunk)
            size += len(chunk)
        return PdfExportReceipt(size, digest.hexdigest())

    def write_integrated_json(self, sink: BinaryIO, *, binding=None) -> PdfExportReceipt:
        """Version2 export carries native values, typed companions and immutable bindings.

        Its serialization hash is distinct from the admitted logical digest. It is
        not the historical version1 canonical-envelope replay format.
        """
        if self.product_kind() != "integrated":
            raise ValueError("integrated JSON export requires an integrated product")
        digest, size = sha256(), 0
        def write(chunk):
            nonlocal size
            sink.write(chunk); digest.update(chunk); size += len(chunk)
        def encode(value):
            return json.dumps(value, ensure_ascii=False, allow_nan=False,
                              separators=(",", ":")).encode()
        write(b'{"export_profile":"pdf-integrated-record-export-v2","binding":' + encode(binding or {}) +
              b',"product":{"version":2,"kind":"integrated","product_key":' + encode(self.reference.product_key) +
              b',"logical_digest":' + encode(self.reference.content_digest) +
              b',"revision":' + encode(self.revision) + b',"content":')
        for chunk in self.iter_native_json():
            write(chunk)
        for family, name in (("input", "inputs"), ("occurrence", "occurrences"),
                             ("relation", "relations"), ("mapping_report", "mapping_reports"),
                             ("coverage", "coverage"), ("health", "health"),
                             ("request_outcome", "request_outcomes"),
                             ("native_metadata", "native_metadata")):
            write(b"," + encode(name) + b":[")
            for index, row in enumerate(self.iter_companions(family)):
                write((b"," if index else b"") + encode(row))
            write(b"]")
        write(b"}}")
        return PdfExportReceipt(size, digest.hexdigest())
