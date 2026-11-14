"""Shared controlled inputs and builders for pdf payload validation support."""

from typing import Any

from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
from corpus_structure.semantic.pdf_payload_validation import FrozenPayloadStore, metadata_classes
from corpus_structure.semantic.pdf_payloads import PROFILE, prepare_payload_family
from corpus_structure.semantic.pdf_record_identity import byte_root


def captured(tmp_path, page):
    store = FrozenPayloadStore(tmp_path / "frozen.sqlite")
    context = trusted_pdf_context()
    store.schemas = {
        kind: context.boundary.json_schema(cls) for kind, cls in metadata_classes().items()
    }
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
    store.add("companion", row)
    store.add(
        "companion",
        dict(
            family="health",
            local_id="health",
            ordinal=0,
            body=dict(
                source_scope="whole_document", inline_coverage="unknown", cell_coverage="unknown"
            ),
        ),
    )
    store.add(
        "companion_field",
        dict(
            family="native_metadata",
            local_id="page:0",
            field_name="value",
            stream_id="page",
            scalar_kind="y",
        ),
    )
    store.add(
        "artifact_stream",
        dict(stream_id="page", byte_length=length, byte_root=root.hex(), encoding_profile=PROFILE),
    )
    store.add("artifact_part", dict(stream_id="page", ordinal=0, body=payload.hex()))
    projection = tmp_path / "access.jsonl"
    projection.write_text("")
    document: dict[str, Any] = {"pages": {"1": {"size": {"width": 200, "height": 300}}}}
    return store, row, document, projection
