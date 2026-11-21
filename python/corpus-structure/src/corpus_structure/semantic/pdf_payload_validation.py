"""Disk-backed frozen companion inputs for the existing finite validation child."""

from __future__ import annotations

import json
from collections.abc import Collection, Iterator, Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import Column, Index, Integer, LargeBinary, MetaData, Table, Text, func, select
from sqlalchemy.exc import IntegrityError

from .sqlite_scratch import open_scratch

_METADATA = MetaData()
_ENTRY = Table(
    "entry",
    _METADATA,
    Column("family", Text, primary_key=True),
    Column("key", Text, primary_key=True),
    Column("body", Text),
    Column("companion_family", Text),
    Column("metadata_kind", Text),
    Column("page_no", Integer),
)
Index(
    "companion_kind",
    _ENTRY.c.family,
    _ENTRY.c.companion_family,
    _ENTRY.c.metadata_kind,
    _ENTRY.c.key,
)
Index(
    "companion_page",
    _ENTRY.c.family,
    _ENTRY.c.companion_family,
    _ENTRY.c.metadata_kind,
    _ENTRY.c.page_no,
    _ENTRY.c.key,
)
_PART = Table(
    "part",
    _METADATA,
    Column("stream", Text, primary_key=True),
    Column("ordinal", Integer, primary_key=True),
    Column("body", LargeBinary),
)
_PAGE = Table(
    "page",
    _METADATA,
    Column("number", Integer, primary_key=True),
    Column("local", Text, unique=True),
)


def metadata_classes(staging_source: bytes) -> dict[str, str]:
    import yaml

    model = yaml.safe_load(staging_source)
    return json.loads(model["annotations"]["pds:metadata_classes"])


class _FrozenCompanions:
    """Repeatable disk view; only indexed input-pin metadata receives bounded decoded reuse."""

    def __init__(self, store: FrozenPayloadStore, family: str):
        self.store, self.family = store, family
        self.count = store.db.execute(
            select(func.count()).select_from(_ENTRY).where(*store._selection(family, None, None))
        ).scalar_one()
        self._indexed = lru_cache(maxsize=256)(self._one)

    def __len__(self):
        return self.count

    def __iter__(self):
        for row in self.store.companions(self.family):
            yield self.store.companion_value(row)

    def _one(self, index: int):
        key = json.dumps([self.family, str(index)])
        row = self.store._entry_body("companion", key)
        if row is None:
            raise ValueError("frozen companion input index is absent")
        return self.store.companion_value(json.loads(row))

    def __getitem__(self, index: int):
        return self._indexed(index)


class FrozenPayloadStore:
    """Own immutable captured bytes on disk; hydrate only a requested metadata value."""

    def __init__(self, path: Path):
        self.db = open_scratch(path)
        try:
            _METADATA.create_all(self.db)
        except BaseException:
            self.db.close()
            raise
        self.schemas: dict[str, Any] = {}
        self.publication_kind = "native"
        self.integrated_metadata_policy: dict[str, Any] | None = None

    def close(self) -> None:
        self.db.close()

    def add(self, family: str, row: dict[str, Any]) -> None:
        if family == "validation_contract":
            from .pdf_payloads import schema_load

            self.schemas = schema_load(json.dumps(row["schemas"]))
            self.publication_kind = row.get("publication_kind", "native")
            if self.publication_kind not in {"native", "integrated"}:
                raise ValueError("unsupported frozen publication kind")
            self.integrated_metadata_policy = row.get("integrated_metadata_policy")
        elif family == "artifact_part":
            self.db.execute(
                _PART.insert().values(
                    stream=row["stream_id"],
                    ordinal=row["ordinal"],
                    body=bytes.fromhex(row["body"].removeprefix("\\x")),
                )
            )
        elif family in {"artifact_stream", "companion", "companion_field", "endpoint"}:
            if family == "artifact_stream":
                key = row["stream_id"]
            elif family == "companion_field":
                key = json.dumps([row["family"], row["local_id"], row["field_name"]])
            elif family == "companion":
                key = json.dumps([row["family"], row["local_id"]])
            else:
                key = (
                    str(row.get("local_id", row.get("relation_id", "")))
                    + ":"
                    + str(row.get("ordinal", ""))
                )
            body = row.get("body", {}) if family == "companion" else {}
            self.db.execute(
                _ENTRY.insert().values(
                    family=family,
                    key=key,
                    body=json.dumps(row),
                    companion_family=row["family"] if family == "companion" else None,
                    metadata_kind=body.get("kind"),
                    page_no=body.get("page_no"),
                )
            )

    def _entry_body(self, family: str, key: str) -> str | None:
        return self.db.execute(
            select(_ENTRY.c.body).where(_ENTRY.c.family == family, _ENTRY.c.key == key)
        ).scalar_one_or_none()

    def _entries(self, family: str) -> Iterator[dict[str, Any]]:
        for (body,) in self.db.execute(
            select(_ENTRY.c.body)
            .where(_ENTRY.c.family == family)
            .order_by(_ENTRY.c.key.collate("BINARY"))
        ):
            yield json.loads(body)

    def stream_descriptors(self) -> Iterator[dict[str, Any]]:
        return self._entries("artifact_stream")

    def parts(self, stream: str) -> Iterator[bytes]:
        for (body,) in self.db.execute(
            select(_PART.c.body).where(_PART.c.stream == stream).order_by(_PART.c.ordinal)
        ):
            yield body

    def stream(self, stream: str) -> tuple[dict[str, Any], bytes]:
        from .pdf_record_identity import byte_root

        raw = self._entry_body("artifact_stream", stream)
        if raw is None:
            raise ValueError("frozen metadata stream is missing")
        descriptor = json.loads(raw)
        chunks = []

        def consume():
            for chunk in self.parts(stream):
                chunks.append(chunk)
                yield chunk

        length, root = byte_root(consume())
        if (length, root.hex()) != (descriptor["byte_length"], descriptor["byte_root"]):
            raise ValueError("frozen metadata bytes differ from their descriptor")
        return descriptor, b"".join(chunks)

    def _selection(self, family: str, kind: str | None, page_nos: Collection[int] | None):
        predicates = [_ENTRY.c.family == "companion", _ENTRY.c.companion_family == family]
        if kind is not None:
            predicates.append(_ENTRY.c.metadata_kind == kind)
        if page_nos is not None:
            predicates.append(_ENTRY.c.page_no.in_(tuple(page_nos)))
        return predicates

    def companions(
        self, family: str, *, kind: str | None = None, page_nos: Collection[int] | None = None
    ) -> Iterator[dict[str, Any]]:
        for (raw,) in self.db.execute(
            select(_ENTRY.c.body)
            .where(*self._selection(family, kind, page_nos))
            .order_by(_ENTRY.c.key)
        ):
            yield json.loads(raw)

    def has_companions(self, family: str, *, kind: str | None = None) -> bool:
        matching = select(_ENTRY.c.key).where(*self._selection(family, kind, None))
        return self.db.execute(select(matching.exists())).scalar_one()

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
            key = json.dumps([row["family"], row["local_id"], name])
            raw = self._entry_body("companion_field", key)
            if raw is None:
                continue
            if name in body:
                raise ValueError(f"{row['family']} {name} has both inline and byte-owned values")
            field = json.loads(raw)
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
        key = json.dumps([row["family"], row["local_id"], "value"])
        raw = self._entry_body("companion_field", key)
        if raw is None:
            raise ValueError("frozen metadata field is missing")
        field = json.loads(raw)
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

    def validate(self, document: Mapping[str, Any], projection: Path) -> None:
        from .pdf_contracts import validate_pdf_report_metadata
        from .pdf_ocr_contracts import validate_pdf_page_payloads
        from .pdf_payloads import FAMILY

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
        self.db.execute(_PAGE.delete())
        for row in self.companions("native_metadata"):
            kind = row["body"]["kind"]
            if kind == FAMILY:
                try:
                    self.db.execute(
                        _PAGE.insert().values(number=row["body"]["page_no"], local=json.dumps(row))
                    )
                except IntegrityError as error:
                    raise ValueError(
                        "inline candidate page is duplicate or outside native scope"
                    ) from error
            else:
                value = decode(row)
                if kind in metadata:
                    metadata[kind].append(value)

        def pages():
            for (raw,) in self.db.execute(select(_PAGE.c.local).order_by(_PAGE.c.number)):
                yield decode(json.loads(raw))

        items, regions = [], []
        with projection.open() as source:
            for line in source:
                row = json.loads(line)
                row["body"].pop("native_json", None)
                (items if row["family"] == "access" else regions).append(row["body"])
        health = [r["body"] for r in self.companions("health") if "source_scope" in r["body"]]
        if len(health) != 1:
            raise ValueError("native health/source scope is absent or ambiguous")
        product = dict(
            kind=self.publication_kind,
            metadata_kinds=frozenset(
                row[0]
                for row in self.db.execute(
                    select(_ENTRY.c.metadata_kind)
                    .where(*self._selection("native_metadata", None, None))
                    .distinct()
                )
            ),
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
        validate_pdf_report_metadata(product, integrated_policy=self.integrated_metadata_policy)
        validate_pdf_page_payloads(product)
        if self.publication_kind == "integrated":
            self.validate_integrated_meaning(document)

    def validate_integrated_meaning(self, document: Mapping[str, Any]) -> None:
        """Apply the shared selected-content rules over disk-backed companion families."""
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
