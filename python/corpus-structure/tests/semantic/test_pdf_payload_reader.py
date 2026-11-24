"""Selected-page IPC access keeps Python export and columnar consumers coherent."""

import json
from dataclasses import replace
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


def test_published_projection_checks_unrequested_physical_page_number():
    reader = PageReader([inventory()])
    assert next(reader.iter_payload_batches(columns=["candidates", "has_words"])).schema.names == [
        "candidates",
        "has_words",
    ]
    reader.rows[0]["body"]["page_no"] = 2
    with pytest.raises(ValueError, match="candidate payload page binding differs"):
        next(reader.iter_payload_batches(page_nos=[2], columns=["candidates", "has_words"]))
    with pytest.raises(ValueError, match="candidate payload page binding differs"):
        next(reader.iter_candidate_payloads())
    with pytest.raises(ValueError, match="candidate payload page binding differs"):
        next(reader.native_metadata("inline_candidate_pages", page_nos=[2]))


def test_recovered_candidate_projects_previously_admitted_bytes(tmp_path, monkeypatch):
    from corpus_structure.ingest.pdf_candidate_source import ReplayCandidatePageSource
    from corpus_structure.ingest.pdf_stream_types import PdfReplayRef
    from corpus_structure.semantic.pdf_payloads import PreparedPayloadFamily, prepare_payload_family

    family = prepare_payload_family()
    original = family.encode_page(inventory())
    path = tmp_path / "received.arrow"
    path.write_bytes(original.content)
    replay = replace(
        PdfReplayRef.from_path(path, "candidate_payload", 1),
        page_no=1,
        schema_digest=original.schema_digest,
        logical_digest=original.logical_digest,
    )
    source = ReplayCandidatePageSource({1: replay}, family)
    requested = ("candidates", "has_words")
    reads = []
    read_batch = PreparedPayloadFamily.read_batch

    def traced(codec, payload, **options):
        reads.append((options.get("columns"), options.get("logical_digest")))
        return read_batch(codec, payload, **options)

    monkeypatch.setattr(PreparedPayloadFamily, "read_batch", traced)
    (admitted,) = source.iter_batches(columns=requested)
    (projected,) = source.iter_batches(columns=requested)
    assert projected.equals(admitted) and projected.schema.names == list(requested)
    assert reads == [
        (None, original.logical_digest),
        ((*requested, "page_no"), None),
    ]

    # Unselected OCR values changed without changing candidate geometry.
    changed_value = inventory()
    changed_value["ocr_regions"][0]["lines"][0]["words"][1]["confidence"] = 0.8
    changed = family.encode_page(changed_value)
    path.write_bytes(changed.content)
    with pytest.raises(ValueError, match="changed"):
        list(source.iter_batches(columns=requested))
    unproven = replace(
        replay, digest=sha256(changed.content).hexdigest(), byte_length=len(changed.content)
    )
    with pytest.raises(ValueError, match="logical digest differs"):
        list(ReplayCandidatePageSource({1: unproven}, family).iter_batches(columns=requested))


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
                    "body": payload,
                    "sha256_digest": sha256(payload).hexdigest(),
                },
            },
            {"kind": "close"},
        ]
    )
    exported = json.loads(b"".join(reader.iter_companion_json("native_metadata", events)))
    assert exported == {"kind": "inline_candidate_pages", "ordinal": 0, "value": inventory()}
    assert reader.decoded == []  # Joined export cursor supplied parts; no per-field SQL replay.
