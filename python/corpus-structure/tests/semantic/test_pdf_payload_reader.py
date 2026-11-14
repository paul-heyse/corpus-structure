"""Selected-page IPC access keeps Python export and columnar consumers coherent."""

import json
from hashlib import sha256

import pytest
from pdf_acceptance_support import inventory

from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
from corpus_structure.semantic.pdf_payloads import PROFILE, encode_page_payload
from corpus_structure.semantic.pdf_record_identity import byte_root
from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader


class PageReader(PublishedPdfReader):
    def __init__(self, pages):
        self.revision = {"release_id": "release", "source_digest": "a" * 64}
        self.requests = []
        self.decoded = []
        self.rows, self.payloads = [], {}
        for page in pages:
            prepared = encode_page_payload(page)
            stream = f"page:{page['page_no']}"
            self.payloads[stream] = prepared.content
            self.rows.append(
                {
                    "family": "native_metadata",
                    "body": {
                        "kind": "inline_candidate_pages",
                        "ordinal": page["page_no"] - 1,
                        "page_no": page["page_no"],
                        "payload_codec": PROFILE,
                        "payload_schema_digest": prepared.schema_digest,
                        "payload_logical_digest": prepared.logical_digest,
                    },
                    "_fields": [
                        {
                            "field_name": "value",
                            "scalar_kind": "y",
                            "stream_id": stream,
                            "encoding_profile": PROFILE,
                        }
                    ],
                }
            )

    def _payload_context(self):
        return trusted_pdf_context()

    def _profile(self, stream_id):
        return PROFILE

    def scalar(self, stream_id):
        self.decoded.append(stream_id)
        yield self.payloads[stream_id]

    def iter_rows(self, family, filters=None, **kwargs):
        filters = {} if filters is None else filters
        self.requests.append((family, filters))
        for row in self.rows:
            if filters.get("page_nos") is None or row["body"]["page_no"] in filters["page_nos"]:
                yield row


def test_page_selector_decodes_only_selected_page_and_hides_custody_envelope():
    first = inventory()
    second = {**inventory(), "page_no": 2, "candidates": []}
    reader = PageReader([first, second])
    assert list(reader.native_metadata("inline_candidate_pages", page_nos=[2, 2])) == [second]
    assert reader.decoded == ["page:2"]
    assert reader.requests == [
        (
            "companion",
            {
                "family": "native_metadata",
                "kind": "inline_candidate_pages",
                "page_nos": [2],
            },
        )
    ]
    assert list(reader.native_metadata("inline_candidate_pages", page_nos=[])) == []
    with pytest.raises(ValueError, match="positive integer"):
        list(reader.native_metadata("inline_candidate_pages", page_nos=[True]))


def test_owned_projected_batch_and_inventory_keep_nested_arrays():
    reader = PageReader([inventory()])
    batch = next(reader.iter_payload_batches(page_nos=[1], columns=["page_no", "ocr_regions"]))
    assert batch.schema.names == ["page_no", "ocr_regions"]
    reader.payloads.clear()
    assert batch.column("page_no")[0].as_py() == 1
    assert len(batch.column("ocr_regions")[0]) == 1

    reader = PageReader([inventory(), {"page_no": 2, "has_words": False, "has_chars": False}])
    assert list(reader.candidate_inventory()) == [
        {"page_no": 1, "candidate_count": 1, "ocr_region_count": 1, "ocr_word_count": 3},
        {"page_no": 2, "candidate_count": 0, "ocr_region_count": 0, "ocr_word_count": 0},
    ]


def test_streamed_export_decodes_ipc_to_logical_json_with_same_custody_pin():
    reader = PageReader([inventory()])
    row = reader.rows[0]
    payload = reader.payloads["page:1"]
    length, root = byte_root([payload])
    field = {
        **row["_fields"][0],
        "encoding_profile": PROFILE,
        "byte_length": length,
        "byte_root": root.hex(),
        "serialization_sha256": sha256(payload).hexdigest(),
    }
    events = iter(
        [
            {"kind": "row", "body": row["body"]},
            {"kind": "field", "field": field},
            {
                "kind": "part",
                "part": {
                    "stream_id": "page:1",
                    "ordinal": 0,
                    "byte_offset": 0,
                    "byte_length": length,
                    "body": payload.hex(),
                    "sha256_digest": sha256(payload).hexdigest(),
                },
            },
            {"kind": "close"},
        ]
    )
    exported = json.loads(b"".join(reader.iter_companion_json("native_metadata", events)))
    assert exported == {"kind": "inline_candidate_pages", "ordinal": 0, "value": inventory()}
    assert reader.decoded == []  # Joined export cursor supplied parts; no per-field SQL replay.
