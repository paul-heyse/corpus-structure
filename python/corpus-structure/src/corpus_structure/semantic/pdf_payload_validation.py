"""Disk-backed frozen companion inputs for the existing finite validation child."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Mapping
from importlib.resources import files
from pathlib import Path
from typing import Any


def metadata_classes() -> dict[str, str]:
    import yaml

    model = yaml.safe_load(
        files("corpus_structure").joinpath("model/semantic/pdf-staging.yaml").read_bytes()
    )
    return json.loads(model["annotations"]["pds:metadata_classes"])


class FrozenPayloadStore:
    """Own immutable captured bytes on disk; hydrate only a requested metadata value."""

    def __init__(self, path: Path):
        self.db = sqlite3.connect(path)
        self.db.executescript("""
        CREATE TABLE entry(family TEXT, key TEXT, body TEXT, PRIMARY KEY(family,key));
        CREATE TABLE part(stream TEXT, ordinal INTEGER, body BLOB, PRIMARY KEY(stream,ordinal));
        CREATE TABLE page(number INTEGER PRIMARY KEY, local TEXT UNIQUE);
        """)
        self.schemas: dict[str, Any] = {}

    def close(self) -> None:
        self.db.close()

    def add(self, family: str, row: dict[str, Any]) -> None:
        if family == "validation_contract":
            from .pdf_payloads import schema_load

            self.schemas = schema_load(json.dumps(row["schemas"]))
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
            self.db.execute("INSERT INTO entry VALUES(?,?,?)", (family, key, json.dumps(row)))

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
        length, root = byte_root(self.parts(stream))
        if (length, root.hex()) != (descriptor["byte_length"], descriptor["byte_root"]):
            raise ValueError("frozen metadata bytes differ from their descriptor")
        return descriptor, b"".join(self.parts(stream))

    def companions(self, family: str) -> Iterator[dict[str, Any]]:
        for (raw,) in self.db.execute(
            "SELECT body FROM entry WHERE family='companion' ORDER BY key"
        ):
            row = json.loads(raw)
            if row["family"] == family:
                yield row

    def value(self, row: Mapping[str, Any]) -> Any:
        from .pdf_payloads import PROFILE, prepare_payload_schema, prepare_schema_validator

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
        schema = self.schemas[kind]
        if descriptor["encoding_profile"] == PROFILE:
            codec = prepare_payload_schema(schema)
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
            value = json.loads(payload)
        else:
            raise ValueError("unsupported frozen metadata encoding")
        prepare_schema_validator(schema).validate(value)
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
        for row in self.companions("native_metadata"):
            if row["body"]["kind"] == kind:
                yield self.value(row)

    def validate(self, document: Mapping[str, Any], projection: Path) -> None:
        from .pdf_ocr_contracts import validate_pdf_inline_reports, validate_pdf_ocr_pages

        store = self
        # Validate every retained metadata class, not only the columnar family.
        for row in self.companions("native_metadata"):
            value = self.value(row)
            if row["body"]["kind"] == "inline_candidate_pages":
                self.db.execute("INSERT INTO page VALUES(?,?)", (value["page_no"], json.dumps(row)))

        class Values:
            def __init__(self, kind):
                self.kind = kind

            def __iter__(self):
                return store.values(self.kind)

            def __bool__(self):
                return any(
                    row["body"]["kind"] == self.kind for row in store.companions("native_metadata")
                )

        class Pages(Mapping):
            def __init__(self):
                self.last_number = None
                self.last_value = None

            def __getitem__(self, number):
                if number == self.last_number:
                    return self.last_value
                raw = store.db.execute(
                    "SELECT local FROM page WHERE number=?", (number,)
                ).fetchone()
                if raw is None:
                    raise KeyError(number)
                value = store.value(json.loads(raw[0]))
                self.last_number, self.last_value = number, value
                return value

            def __iter__(self):
                return (row[0] for row in store.db.execute("SELECT number FROM page"))

            def __len__(self):
                return store.db.execute("SELECT count(*) FROM page").fetchone()[0]

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
            document=document,
            items=items,
            regions=regions,
            health=dict(health[0]),
            source_scope=health[0]["source_scope"],
            page_start=health[0].get("page_start"),
            page_end=health[0].get("page_end"),
            cell_reports=Values("cell_reports"),
            inline_candidate_pages=Values("inline_candidate_pages"),
            inline_alignment_reports=Values("inline_alignment_reports"),
            recognition_coverage=Values("recognition_coverage"),
        )
        product["health"]["formula_outcomes"] = Values("formula_outcomes")
        runtime = list(self.values("runtime_report"))
        if len(runtime) > 1:
            raise ValueError("native runtime metadata is ambiguous")
        if runtime:
            product["runtime_report"] = runtime[0]
        inputs = list(self.companions("input"))
        structural = [r["body"] for r in inputs if r["body"].get("role") == "structural"]
        if len(structural) == 1:
            parent = structural[0]
            product.update(
                parent_task_id=parent["task_id"],
                parent_product_key=parent["product_key"],
                parent_digest=parent["content_digest"],
            )
        from .pdf_contracts import validate_pdf_report_metadata

        validate_pdf_report_metadata(product)
        validate_pdf_ocr_pages(product)
        validate_pdf_inline_reports(product, page_lookup=Pages())
