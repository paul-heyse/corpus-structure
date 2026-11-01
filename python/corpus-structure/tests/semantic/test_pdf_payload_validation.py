"""Actual frozen payloads must satisfy semantics beyond IPC shape/checksums."""

import json
from copy import deepcopy
from typing import Any

import pytest

from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
from corpus_structure.semantic.pdf_payload_validation import FrozenPayloadStore, metadata_classes
from corpus_structure.semantic.pdf_payloads import PROFILE, prepare_payload_family
from corpus_structure.semantic.pdf_record_identity import byte_root

from .test_pdf_ocr_contracts import inventory


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


def test_valid_frozen_page_checks_actual_bytes_and_semantics(tmp_path):
    page = inventory()
    store, row, document, projection = captured(tmp_path, page)
    try:
        assert store.value(row) == page
        store.validate(document, projection)
    finally:
        store.close()


@pytest.mark.parametrize(
    "defect,diagnostic",
    [
        ("offset", "recognized line range"),
        ("geometry", "raster-to-PDF"),
        ("endpoint", "estimated-word address"),
        ("page", "outside native scope"),
    ],
)
def test_structurally_legal_persisted_payload_cannot_bypass_domain_rules(
    tmp_path, defect, diagnostic
):
    page = deepcopy(inventory())
    if defect == "offset":
        page["ocr_regions"][0]["lines"][0]["words"][0]["end"] = 2
    elif defect == "geometry":
        page["ocr_regions"][0]["lines"][0]["words"][0]["left"] += 1
    elif defect == "endpoint":
        page["candidates"][0]["ocr_word_index"] = 99
    else:
        page["page_no"] = 2
    store, _, document, projection = captured(tmp_path, page)
    try:
        with pytest.raises(ValueError, match=diagnostic):
            store.validate(document, projection)
    finally:
        store.close()


def test_forged_logical_claim_fails_against_captured_ipc(tmp_path):
    store, row, _, _ = captured(tmp_path, inventory())
    row["body"]["payload_logical_digest"] = "0" * 64
    try:
        with pytest.raises(ValueError, match="logical digest"):
            store.value(row)
    finally:
        store.close()


def test_runtime_report_is_not_omitted_from_frozen_semantics(tmp_path):
    store, _, document, projection = captured(tmp_path, inventory())
    value = dict(effective_options="[]")
    # Isolate the shared cross-field rule: the primitive field is a legal JSON string.
    store.schemas["runtime_report"] = {"type": "object"}
    payload = json.dumps(value).encode()
    length, root = byte_root((payload,))
    store.add(
        "companion",
        dict(
            family="native_metadata",
            local_id="runtime:0",
            ordinal=1,
            body=dict(kind="runtime_report", ordinal=0),
        ),
    )
    store.add(
        "companion_field",
        dict(
            family="native_metadata", local_id="runtime:0", field_name="value", stream_id="runtime"
        ),
    )
    store.add(
        "artifact_stream",
        dict(
            stream_id="runtime",
            byte_length=length,
            byte_root=root.hex(),
            encoding_profile="pdf-companion-json-field-v1",
        ),
    )
    store.add("artifact_part", dict(stream_id="runtime", ordinal=0, body=payload.hex()))
    try:
        with pytest.raises(ValueError, match="upstream option object"):
            store.validate(document, projection)
    finally:
        store.close()


def test_false_complete_coverage_fails_over_captured_page_inventory(tmp_path):
    page = inventory()
    page["ocr_regions"][0]["outcome"] = "partial"
    store, _, document, projection = captured(tmp_path, page)
    document["groups"] = [dict(self_ref="#/groups/0", label="section")]
    document["texts"] = [dict(self_ref="#/texts/0", label="text", text="x", children=[])]
    health = dict(
        source_scope="whole_document",
        inline_coverage="complete",
        inline_scope=["#/groups/0"],
        inline_membership="direct",
        candidate_policy="native-font-token-vector-ocr-word-v3",
    )
    store.db.execute(
        "UPDATE entry SET body=? WHERE family='companion' AND key=?",
        (
            json.dumps(dict(family="health", local_id="health", body=health)),
            json.dumps(["health", "health"]),
        ),
    )
    projection.write_text(
        "\n".join(
            json.dumps(dict(family=family, body=body))
            for family, body in [
                ("access", dict(pointer="#/groups/0", section_pointer="#/groups/0")),
                (
                    "access",
                    dict(
                        pointer="#/texts/0",
                        parent_pointer="#/groups/0",
                        section_pointer="#/groups/0",
                    ),
                ),
                ("region", dict(pointer="#/texts/0", page_no=1)),
            ]
        )
    )
    try:
        with pytest.raises(ValueError, match="complete word inventory"):
            store.validate(document, projection)
    finally:
        store.close()
