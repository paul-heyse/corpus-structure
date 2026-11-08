"""Disk-backed frozen companion inputs for the existing finite validation child."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Collection, Iterator, Mapping
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any


def metadata_classes() -> dict[str, str]:
    import yaml

    model = yaml.safe_load(
        files("corpus_structure").joinpath("model/semantic/pdf-staging.yaml").read_bytes()
    )
    return json.loads(model["annotations"]["pds:metadata_classes"])


class _FrozenCompanions:
    """Repeatable disk view; only indexed input-pin metadata receives bounded decoded reuse."""

    def __init__(self, store: FrozenPayloadStore, family: str):
        self.store, self.family = store, family
        where, parameters = store._selection(family, None, None)
        self.count = store.db.execute(
            "SELECT count(*) FROM entry WHERE " + where, parameters
        ).fetchone()[0]
        self._indexed = lru_cache(maxsize=256)(self._one)

    def __len__(self):
        return self.count

    def __iter__(self):
        for row in self.store.companions(self.family):
            yield self.store.companion_value(row)

    def _one(self, index: int):
        key = json.dumps([self.family, str(index)])
        row = self.store.db.execute(
            "SELECT body FROM entry WHERE family='companion' AND key=?", (key,)
        ).fetchone()
        if row is None:
            raise ValueError("frozen companion input index is absent")
        return self.store.companion_value(json.loads(row[0]))

    def __getitem__(self, index: int):
        return self._indexed(index)


class FrozenPayloadStore:
    """Own immutable captured bytes on disk; hydrate only a requested metadata value."""

    def __init__(self, path: Path):
        self.db = sqlite3.connect(path)
        self.db.executescript("""
        CREATE TABLE entry(family TEXT, key TEXT, body TEXT, companion_family TEXT,
                           metadata_kind TEXT, page_no INTEGER, PRIMARY KEY(family,key));
        CREATE INDEX companion_kind ON entry(family,companion_family,metadata_kind,key);
        CREATE INDEX companion_page ON entry(family,companion_family,metadata_kind,page_no,key);
        CREATE TABLE part(stream TEXT, ordinal INTEGER, body BLOB, PRIMARY KEY(stream,ordinal));
        CREATE TABLE page(number INTEGER PRIMARY KEY, local TEXT UNIQUE);
        """)
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
                "INSERT INTO part VALUES(?,?,?)",
                (row["stream_id"], row["ordinal"], bytes.fromhex(row["body"].removeprefix("\\x"))),
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
                "INSERT INTO entry VALUES(?,?,?,?,?,?)",
                (
                    family,
                    key,
                    json.dumps(row),
                    row["family"] if family == "companion" else None,
                    body.get("kind"),
                    body.get("page_no"),
                ),
            )

    def parts(self, stream: str) -> Iterator[bytes]:
        for (body,) in self.db.execute(
            "SELECT body FROM part WHERE stream=? ORDER BY ordinal", (stream,)
        ):
            yield body

    def stream(self, stream: str) -> tuple[dict[str, Any], bytes]:
        from .pdf_record_identity import byte_root

        raw = self.db.execute(
            "SELECT body FROM entry WHERE family='artifact_stream' AND key=?", (stream,)
        ).fetchone()
        if raw is None:
            raise ValueError("frozen metadata stream is missing")
        descriptor = json.loads(raw[0])
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
        where = "family='companion' AND companion_family=?"
        parameters: list[Any] = [family]
        if kind is not None:
            where += " AND metadata_kind=?"
            parameters.append(kind)
        if page_nos is not None:
            if not page_nos:
                where += " AND 0"
            else:
                where += " AND page_no IN (" + ",".join("?" for _ in page_nos) + ")"
                parameters.extend(page_nos)
        return where, parameters

    def companions(
        self, family: str, *, kind: str | None = None, page_nos: Collection[int] | None = None
    ) -> Iterator[dict[str, Any]]:
        where, parameters = self._selection(family, kind, page_nos)
        for (raw,) in self.db.execute(
            "SELECT body FROM entry WHERE " + where + " ORDER BY key", parameters
        ):
            yield json.loads(raw)

    def has_companions(self, family: str, *, kind: str | None = None) -> bool:
        where, parameters = self._selection(family, kind, None)
        return bool(
            self.db.execute(
                "SELECT EXISTS(SELECT 1 FROM entry WHERE " + where + ")", parameters
            ).fetchone()[0]
        )

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
            raw = self.db.execute(
                "SELECT body FROM entry WHERE family='companion_field' AND key=?", (key,)
            ).fetchone()
            if raw is None:
                continue
            if name in body:
                raise ValueError(f"{row['family']} {name} has both inline and byte-owned values")
            field = json.loads(raw[0])
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
        raw = self.db.execute(
            "SELECT body FROM entry WHERE family='companion_field' AND key=?", (key,)
        ).fetchone()
        if raw is None:
            raise ValueError("frozen metadata field is missing")
        field = json.loads(raw[0])
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
        self.db.execute("DELETE FROM page")
        for row in self.companions("native_metadata"):
            kind = row["body"]["kind"]
            if kind == FAMILY:
                try:
                    self.db.execute(
                        "INSERT INTO page VALUES(?,?)",
                        (row["body"]["page_no"], json.dumps(row)),
                    )
                except sqlite3.IntegrityError as error:
                    raise ValueError(
                        "inline candidate page is duplicate or outside native scope"
                    ) from error
            else:
                value = decode(row)
                if kind in metadata:
                    metadata[kind].append(value)

        def pages():
            for (raw,) in self.db.execute("SELECT local FROM page ORDER BY number"):
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
                    "SELECT DISTINCT metadata_kind FROM entry "
                    "WHERE family='companion' AND companion_family='native_metadata'"
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
