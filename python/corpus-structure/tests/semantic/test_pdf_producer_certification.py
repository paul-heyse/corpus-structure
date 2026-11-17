"""Producer checks actual output and encoded payloads without staging or reconstruction."""

import json
from hashlib import sha256

import pytest
from docling_core.types.doc import DoclingDocument, PageItem, Size

from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult
from corpus_structure.semantic.pdf_certification import PdfProducerPayloads, jsonb_canonical_text, write_pdf_companion_sets
from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
from corpus_structure.semantic.pdf_lowering import LOWERING_CONTRACT, require_lowering_identity
from corpus_structure.semantic.pdf_payload_validation import metadata_classes
from corpus_structure.semantic.pdf_payloads import prepare_payload_family
from corpus_structure.semantic.pdf_publication import PdfCompanionEncodingBasis
from corpus_structure.semantic.pdf_records import native_schema_bytes


def prepared(tmp_path, *, candidate=None):
    document = DoclingDocument(name="producer source")
    document.pages[1] = PageItem(page_no=1, size=Size(width=100, height=100))
    context = trusted_pdf_context()
    contract = {"schemas": {kind: context.boundary.json_schema(cls) for kind, cls in metadata_classes().items()},
                "publication_kind": "native", "integrated_metadata_policy": None}
    streamed = StreamingPdfResult(document, PdfStreamSpool(tmp_path / "pages"), "success", (), b"recipe", ())
    replays = streamed.write_record_batches(tmp_path / "records", build_id="build", release_id="release", source_digest="a" * 64)
    metadata = [{"kind": "runtime_report", "ordinal": 0, "value": {"effective_options": "{}"}}]
    if candidate is not None:
        metadata.append({"kind": "inline_candidate_pages", "ordinal": 1, "value": candidate})
    sets = write_pdf_companion_sets(tmp_path / "companions", PdfCompanionEncodingBasis("build", "release"),
        {"native_metadata": metadata, "health": ({"conversion": "success", "display_coverage": "unknown",
        "inline_coverage": "unknown", "cell_coverage": "unknown", "issues": [], "source_scope": "whole_document"},)},
        payload_family=prepare_payload_family(context), check_active=lambda: None)
    payloads = PdfProducerPayloads(tmp_path / "payloads.sqlite", contract)
    payloads.add_replays(replays)
    payloads.add_companion_replays(sets)
    return payloads, document, dict(release_id="release", source_digest="a" * 64,
        recipe_digest=sha256(b"recipe").hexdigest(), schema_digest=sha256(native_schema_bytes()).hexdigest(),
        kind="native", lowering_identity=require_lowering_identity(context), target_meanings={})


def test_producer_certifies_existing_document_and_prepared_bytes_without_reconstructing(tmp_path, monkeypatch):
    payloads, document, basis = prepared(tmp_path)
    from corpus_structure.semantic import pdf_records

    def forbidden(*args, **kwargs):
        raise AssertionError("producer reconstructed its already-owned document")
    monkeypatch.setattr(pdf_records, "reconstruct_native_document", forbidden)
    try:
        certification = payloads.certify(document, tmp_path / "access.jsonl", **basis)
        assert certification.source_digest == "a" * 64
        assert len(certification.logical_digest) == len(certification.native_document_digest) == 64
        rows = [json.loads(line) for line in (tmp_path / "access.jsonl").read_text().splitlines()]
        assert [row["body"]["pointer"] for row in rows] == ["#/body", "#/furniture"]
        assert all(row["family"] == "access" for row in rows)
    finally:
        payloads.close()


def test_correctly_hashed_payload_with_invalid_geometry_refuses_before_staging(tmp_path):
    candidate = {"page_no": 1, "has_words": True, "has_chars": False, "candidates": [{
        "page_no": 1, "text": "outside", "left": 0, "top": 1, "right": 101, "bottom": 3,
        "origin": "TOPLEFT", "basis": "native-math-token-v1",
    }]}
    payloads, document, basis = prepared(tmp_path, candidate=candidate)
    try:
        with pytest.raises(ValueError, match="outside physical page"):
            payloads.certify(document, tmp_path / "access.jsonl", **basis)
    finally:
        payloads.close()


def test_lowering_identity_is_the_retained_contract_over_sources_schemas_and_codec():
    context = trusted_pdf_context()
    artifact = context.domain.source(LOWERING_CONTRACT)
    assert require_lowering_identity(context) == sha256(artifact.content).hexdigest()
    manifest = json.loads(artifact.content)
    names = {item["name"] for item in manifest["inputs"]}
    assert any(name.endswith("semantic/pdf_records.py") for name in names)
    assert any(name.endswith("semantic/pdf_certification.py") for name in names)
    assert any(name.endswith("codec/inline-candidates.arrow") for name in names)
    assert {"docling-core", "pydantic", "jsonschema", "pyarrow", "python"} <= manifest["libraries"].keys()


def test_companion_frame_json_uses_postgresql_numeric_spelling():
    assert jsonb_canonical_text({"b": -0.0, "a": [1.0, 1e-7, 1e20]}) == '{"a":[1.0,0.0000001,100000000000000000000],"b":0.0}'


def test_independent_oracle_refuses_lossy_but_callback_valid_lowering(tmp_path):
    from corpus_structure.semantic.pdf_publication import write_pdf_oracle_capture, verify_pdf_oracle_capture

    payloads, document, basis = prepared(tmp_path)
    try:
        for key, raw in payloads.db.execute("SELECT key,body FROM native_entry WHERE family='native'"):
            row = json.loads(raw)
            scalars = json.loads(row["scalars_json"])
            if scalars.get("name") == "producer source":
                scalars["name"] = "lossy source"
                row["scalars_json"] = json.dumps(scalars)
                payloads.db.execute("UPDATE native_entry SET body=? WHERE family='native' AND key=?", (json.dumps(row), key))
                break
        else:
            raise AssertionError("independent native name witness is absent")
        certification = payloads.certify(document, tmp_path / "producer-access.jsonl", **basis)
        def rows(family, filters):
            if family in {"header", "native", "membership"}:
                for (raw,) in payloads.db.execute("SELECT body FROM native_entry WHERE family=?", (family,)):
                    yield json.loads(raw)
            elif family == "companion":
                for row in payloads.companions(filters["family"]):
                    row["_fields"] = [json.loads(raw) for (raw,) in payloads.db.execute(
                        "SELECT body FROM entry WHERE family='companion_field'")
                        if (json.loads(raw)["family"], json.loads(raw)["local_id"]) == (row["family"], row["local_id"])]
                    yield row
            elif family == "artifact_stream":
                for (raw,) in payloads.db.execute("SELECT body FROM entry WHERE family='artifact_stream'"):
                    row = json.loads(raw)
                    if row["stream_id"] in filters["stream_ids"]:
                        yield row
            elif family == "artifact_part":
                for stream in filters["stream_ids"]:
                    for ordinal, body in payloads.db.execute("SELECT ordinal,body FROM part WHERE stream=? ORDER BY ordinal", (stream,)):
                        yield {"stream_id": stream, "ordinal": ordinal, "body": body}
        capture = tmp_path / "oracle.arrow"
        write_pdf_oracle_capture(capture, context=trusted_pdf_context(), kind="native", rows=rows, check_active=lambda: None)
        with pytest.raises(ValueError, match="differs from the certified producer document"):
            verify_pdf_oracle_capture(capture, tmp_path / "oracle-access.jsonl", release_id="release",
                lowering_identity=certification.lowering_identity, kind="native", logical_digest=certification.logical_digest,
                native_document_digest=certification.native_document_digest, check_active=lambda: None)
    finally:
        payloads.close()
