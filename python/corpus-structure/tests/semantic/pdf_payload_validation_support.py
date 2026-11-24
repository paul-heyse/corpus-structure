"""Shared controlled inputs and builders for pdf payload validation support."""

import json
from hashlib import sha256
from typing import Any

import pyarrow as pa

from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
from corpus_structure.semantic.pdf_lowering_context import capture_pdf_lowering
from corpus_structure.semantic.pdf_payload_validation import FrozenPayloadStore, metadata_classes
from corpus_structure.semantic.pdf_payloads import PROFILE, prepare_payload_family
from corpus_structure.semantic.pdf_record_identity import byte_root
from corpus_structure.semantic.pdf_replay_transport import replay_schema


def typed_store(*, kind="native", integrated_policy=None):
    context = trusted_pdf_context()
    return FrozenPayloadStore(
        dict(
            schemas={
                kind: context.boundary.json_schema(cls)
                for kind, cls in metadata_classes(context.staging.content).items()
            },
            publication_kind=kind,
            integrated_metadata_policy=integrated_policy,
        )
    )


def add_row(store, family, row):
    context = trusted_pdf_context()
    paths = {
        "companion": "companion:companion",
        "companion_field": "companion:field",
        "artifact_stream": "stage:artifact_stream",
        "artifact_part": "stage:artifact_part",
    }
    schema = replay_schema(capture_pdf_lowering(context).schema(paths[family]))
    row = dict(row)
    if family == "companion":
        row["body"] = json.dumps(row["body"], ensure_ascii=False)
    elif family == "artifact_part":
        body = row["body"]
        row.setdefault("byte_offset", 0)
        row.setdefault("byte_length", len(body))
        row.setdefault("sha256_digest", sha256(body).hexdigest())
    store.add_batch(family, pa.RecordBatch.from_pylist([row], schema=schema))


def captured(tmp_path, page, *, health=None, defect=None, integrated_policy=None):
    store = typed_store(
        kind="native" if integrated_policy is None else "integrated",
        integrated_policy=integrated_policy,
    )
    context = trusted_pdf_context()
    codec = prepare_payload_family(context)
    payload = codec.encode(page)
    length, root = byte_root((payload,))
    row = dict(
        family="native_metadata",
        local_id="page:0",
        ordinal=0,
        body=dict(
            kind="inline_candidate_pages",
            ordinal=0,
            page_no=page["page_no"],
            payload_codec=PROFILE,
            payload_schema_digest=codec.schema_digest,
            payload_logical_digest=codec.logical_digest(page),
        ),
    )
    if defect in {"schema", "logical", "locator"}:
        field = {
            "schema": "payload_schema_digest",
            "logical": "payload_logical_digest",
            "locator": "page_no",
        }[defect]
        row["body"][field] = 2 if defect == "locator" else "0" * 64
    add_row(store, "companion", row)
    add_row(
        store,
        "companion",
        dict(
            family="health",
            local_id="health",
            ordinal=0,
            body=health
            if health is not None
            else dict(
                source_scope="whole_document", inline_coverage="unknown", cell_coverage="unknown"
            ),
        ),
    )
    add_row(
        store,
        "companion_field",
        dict(
            family="native_metadata",
            local_id="page:0",
            field_name="value",
            stream_id="page",
            scalar_kind="y",
        ),
    )
    add_row(
        store,
        "artifact_stream",
        dict(
            stream_id="page",
            byte_length=length,
            byte_root=root.hex(),
            encoding_profile="pdf-companion-json-field-v1" if defect == "encoding" else PROFILE,
        ),
    )
    add_row(
        store,
        "artifact_part",
        dict(stream_id="page", ordinal=0, body=b"changed" if defect == "bytes" else payload),
    )
    projection = tmp_path / "access.jsonl"
    projection.write_text("")
    document: dict[str, Any] = {"pages": {"1": {"size": {"width": 200, "height": 300}}}}
    return store, row, document, projection


def validate_projection_fixture(store, document, projection):
    """Read independent expected projections supplied by validator tests."""
    items, regions = [], []
    for line in projection.read_text().splitlines():
        row = json.loads(line)
        (items if row["family"] == "access" else regions).append(row["body"])
    store.validate(document, items=items, regions=regions)
