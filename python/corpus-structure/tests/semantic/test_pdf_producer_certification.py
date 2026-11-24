"""Producer checks actual output and encoded payloads without staging or reconstruction."""

import json
from hashlib import sha256
from typing import Any, Literal, TypedDict

import pytest
from docling_core.types.doc import DoclingDocument, PageItem, Size

from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult
from corpus_structure.semantic.pdf_certification import (
    PdfProducerPayloads,
    jsonb_canonical_text,
    write_pdf_companion_sets,
)
from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
from corpus_structure.semantic.pdf_lowering import LOWERING_CONTRACT, require_lowering_identity
from corpus_structure.semantic.pdf_payload_validation import metadata_classes
from corpus_structure.semantic.pdf_payloads import prepare_payload_family
from corpus_structure.semantic.pdf_records import native_schema_bytes


class ProducerBasis(TypedDict):
    release_id: str
    source_digest: str
    recipe_digest: str
    schema_digest: str
    kind: Literal["native"]
    lowering_identity: str
    target_meanings: dict[tuple[int, str, str], Any]


def prepared(tmp_path, *, candidate=None):
    document = DoclingDocument(name="producer source")
    document.pages[1] = PageItem(page_no=1, size=Size(width=100, height=100))
    context = trusted_pdf_context()
    from corpus_structure.semantic.pdf_lowering_context import capture_pdf_lowering

    contract = {
        "lowering": capture_pdf_lowering(context).document(),
        "schemas": {
            kind: context.boundary.json_schema(cls)
            for kind, cls in metadata_classes(context.staging.content).items()
        },
        "publication_kind": "native",
        "integrated_metadata_policy": None,
    }
    streamed = StreamingPdfResult(
        document, PdfStreamSpool(tmp_path / "pages"), "success", (), b"recipe", ()
    )
    replays = streamed.write_record_batches(tmp_path / "records", source_digest="a" * 64)
    metadata = [{"kind": "runtime_report", "ordinal": 0, "value": {"effective_options": "{}"}}]
    if candidate is not None:
        metadata.append({"kind": "inline_candidate_pages", "ordinal": 1, "value": candidate})
    sets = write_pdf_companion_sets(
        tmp_path / "companions",
        {
            "native_metadata": metadata,
            "health": (
                {
                    "conversion": "success",
                    "display_coverage": "unknown",
                    "inline_coverage": "unknown",
                    "cell_coverage": "unknown",
                    "issues": [],
                    "source_scope": "whole_document",
                },
            ),
        },
        payload_family=prepare_payload_family(context),
        check_active=lambda: None,
    )
    payloads = PdfProducerPayloads(contract)
    payloads.add_replays(replays)
    payloads.add_companion_replays(sets)
    basis: ProducerBasis = {
        "release_id": "release",
        "source_digest": "a" * 64,
        "recipe_digest": sha256(b"recipe").hexdigest(),
        "schema_digest": sha256(native_schema_bytes()).hexdigest(),
        "kind": "native",
        "lowering_identity": require_lowering_identity(context),
        "target_meanings": {},
    }
    return payloads, document, basis


def test_producer_certifies_existing_document_and_prepared_bytes_without_reconstructing(
    tmp_path, monkeypatch
):
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
        assert [row["body"]["native_json"]["self_ref"] for row in rows] == [
            "#/body",
            "#/furniture",
        ]
        assert all(set(row["body"]) == {"native_json"} for row in rows)
        assert all(row["family"] == "access" for row in rows)
    finally:
        payloads.close()


def test_correctly_hashed_payload_with_invalid_geometry_refuses_before_staging(tmp_path):
    candidate = {
        "page_no": 1,
        "has_words": True,
        "has_chars": False,
        "candidates": [
            {
                "page_no": 1,
                "text": "outside",
                "left": 0,
                "top": 1,
                "right": 101,
                "bottom": 3,
                "origin": "TOPLEFT",
                "basis": "native-math-token-v1",
            }
        ],
    }
    payloads, document, basis = prepared(tmp_path, candidate=candidate)
    try:
        with pytest.raises(ValueError, match="outside physical page"):
            payloads.certify(document, tmp_path / "access.jsonl", **basis)
    finally:
        payloads.close()


def test_lowering_identity_is_the_retained_contract_over_sources_schemas_and_codec():
    context = trusted_pdf_context()
    artifact = context.domain.source(LOWERING_CONTRACT)
    manifest = json.loads(artifact.content)
    names = {item["name"] for item in manifest["inputs"]}
    meaning_name = next(name for name in names if name.endswith("code/meaning.json"))
    meaning = json.loads(context.domain.source(meaning_name.removeprefix("pdf-domain/")).content)
    assert {
        "corpus_structure.semantic.pdf_records",
        "corpus_structure.semantic.pdf_certification",
    } <= {module for module, _ in meaning["modules"]}
    assert any(name.endswith("codec/inline-candidates.arrow") for name in names)
    assert {"docling-core", "pydantic", "jsonschema", "pyarrow", "python"} <= manifest[
        "libraries"
    ].keys()


@pytest.mark.parametrize(
    ("artifact_name", "message"),
    [
        (LOWERING_CONTRACT, "PDF lowering contract differs from the captured execution basis"),
        ("code/meaning.json", "captured PDF lowering source differs from its contract"),
    ],
)
def test_lowering_identity_requires_matching_captured_artifacts(artifact_name, message):
    from dataclasses import replace
    from types import SimpleNamespace

    context = trusted_pdf_context()
    domain = context.domain
    assert domain is not None and require_lowering_identity(context)

    def source(name):
        artifact = domain.source(name)
        if name == artifact_name or name.endswith("/" + artifact_name):
            return replace(artifact, content=artifact.content + b"\n")
        return artifact

    with pytest.raises(ValueError, match=message):
        require_lowering_identity(
            replace(context, domain=SimpleNamespace(source=source, sources=domain.sources))
        )


def test_companion_frame_json_uses_postgresql_numeric_spelling():
    assert (
        jsonb_canonical_text({"b": -0.0, "a": [1.0, 1e-7, 1e20]})
        == '{"a":[1.0,0.0000001,100000000000000000000],"b":0.0}'
    )


def test_independent_oracle_refuses_lossy_but_callback_valid_lowering(tmp_path):
    from corpus_structure.semantic.pdf_publication import (
        verify_pdf_oracle_capture,
        write_pdf_oracle_capture,
    )

    payloads, document, basis = prepared(tmp_path)
    try:
        certification = payloads.certify(document, tmp_path / "producer-access.jsonl", **basis)
        substituted = []

        def rows(family, filters):
            if family in {"header", "native", "membership"}:
                for row in payloads.entries(family):
                    if family == "native":
                        scalars = json.loads(row["scalars_json"])
                        if scalars.get("name") == "producer source":
                            scalars["name"] = "lossy source"
                            row["scalars_json"] = json.dumps(scalars)
                            substituted.append(row["record_id"])
                    yield row
            elif family == "companion":
                for row in payloads.companions(filters["family"]):
                    row["_fields"] = [
                        field
                        for field in payloads.entries("companion_field")
                        if (field["family"], field["local_id"]) == (row["family"], row["local_id"])
                    ]
                    yield row
            elif family == "artifact_stream":
                for row in payloads.stream_descriptors():
                    if row["stream_id"] in filters["stream_ids"]:
                        yield row
            elif family == "artifact_part":
                for stream in filters["stream_ids"]:
                    yield from payloads.part_rows(stream)

        capture = tmp_path / "oracle.arrow"
        write_pdf_oracle_capture(
            capture,
            context=trusted_pdf_context(),
            kind="native",
            rows=rows,
            json_fields="text",
            check_active=lambda: None,
        )
        assert len(substituted) == 1
        with pytest.raises(ValueError, match="differs from the certified producer document"):
            verify_pdf_oracle_capture(
                capture,
                tmp_path / "oracle-access.jsonl",
                release_id="release",
                lowering_identity=certification.lowering_identity,
                kind="native",
                logical_digest=certification.logical_digest,
                native_document_digest=certification.native_document_digest,
                check_active=lambda: None,
            )
    finally:
        payloads.close()


@pytest.mark.parametrize("representation,value", [("decoded", "null"), ("text", '"null"')])
def test_oracle_capture_preserves_json_looking_native_strings(tmp_path, representation, value):
    import pyarrow as pa

    from corpus_structure.semantic.pdf_publication import (
        _oracle_family_path,
        write_pdf_oracle_capture,
    )

    def rows(family, filters):
        if family == "membership":
            yield {"value_kind": "scalar", "scalar_json": value}

    path = tmp_path / "literal.arrow"
    write_pdf_oracle_capture(
        path,
        context=trusted_pdf_context(),
        kind="native",
        rows=rows,
        json_fields=representation,
        check_active=lambda: None,
    )
    with pa.memory_map(str(_oracle_family_path(path, "membership")), "r") as source:
        reader = pa.ipc.open_file(source)
        batch = reader.get_batch(0)
        assert batch.column("value_kind").to_pylist() == ["scalar"]
        assert batch.column("scalar_json").to_pylist() == ['"null"']


def test_acquired_record_schemas_do_not_rebuild_ambient_metadata(tmp_path, monkeypatch):
    from corpus_structure.semantic import pdf_record_model, pdf_staging

    trusted_pdf_context()

    def forbidden(*args, **kwargs):
        raise AssertionError("producer must consume its acquired record schemas")

    monkeypatch.setattr(pdf_record_model, "record_arrow_schema", forbidden)
    monkeypatch.setattr(pdf_staging, "stage_schema", forbidden)
    payloads, document, basis = prepared(tmp_path)
    try:
        assert payloads.lowering.schema("stage:header").get_field_index("product_id") >= 0
        certificate = payloads.certify(document, tmp_path / "access.jsonl", **basis)
        assert certificate.source_digest == "a" * 64
    finally:
        payloads.close()


def test_metadata_class_projection_uses_the_supplied_staging_source():
    source = b"""annotations:
  pds:metadata_classes: '{"retained":"ArchivedMetadata"}'
"""
    assert metadata_classes(source) == {"retained": "ArchivedMetadata"}


def test_stream_requires_captured_lowering_before_provider_preparation(tmp_path):
    from types import SimpleNamespace

    from corpus_structure.ingest.pdf_stream_types import OwnedPdfSource, PdfStreamRequest
    from corpus_structure.ingest.pdf_streaming import run_pdf_stream

    original = tmp_path / "input.pdf"
    original.write_bytes(b"%PDF-1.7\ncontrolled original")

    def forbidden(*args, **kwargs):
        raise AssertionError("invalid lowering context must refuse before provider work")

    with OwnedPdfSource.acquire(original, tmp_path / "owned") as source:
        request = PdfStreamRequest(
            source,
            tmp_path / "pages",
            tmp_path / "records",
            "release",
            b"{}",
            "lowering",
            b"{}",
        )
        with pytest.raises(ValueError, match="unsupported captured PDF lowering"):
            run_pdf_stream(
                request,
                SimpleNamespace(prepare=forbidden, convert=forbidden),
                on_replay=forbidden,
            )
    assert not (tmp_path / "pages").exists()


def test_native_mapping_and_callback_policy_use_the_acquired_context(tmp_path, monkeypatch):
    from dataclasses import replace

    import pyarrow as pa

    from corpus_structure.semantic import pdf_records
    from corpus_structure.semantic.pdf_lowering_context import capture_pdf_lowering

    context = trusted_pdf_context()
    lowering = capture_pdf_lowering(context)
    payloads, document, basis = prepared(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("native production must consume its acquired mapping and policy")

    monkeypatch.setattr(pdf_records, "prepare_native_schema_mapping", forbidden)
    monkeypatch.setattr(pdf_records, "native_validation_contract", forbidden)
    monkeypatch.setattr(pdf_records, "native_schema_bytes", forbidden)
    monkeypatch.setattr(pdf_records, "_default_record_header", forbidden)
    streamed = StreamingPdfResult(
        document,
        PdfStreamSpool(tmp_path / "explicit-pages", payload_family=prepare_payload_family(context)),
        "success",
        (),
        b"recipe",
        (),
    )
    replays = streamed.write_record_batches(
        tmp_path / "explicit-records",
        source_digest="a" * 64,
        lowering=lowering,
    )
    headers = []
    for replay in replays:
        if replay.family == "header":
            with pa.memory_map(str(replay.path), "r") as source:
                headers.extend(pa.ipc.open_file(source).read_all().to_pylist())
    assert len(headers) == 1
    assert headers[0]["contract_version"] == "pdf-native-records-v1"
    assert headers[0]["mapping_profile"] == "pdf-native-records-v1"
    try:
        certificate = payloads.certify(document, tmp_path / "explicit-access.jsonl", **basis)
        assert certificate.source_digest == "a" * 64
        policy = lowering.callback_policy()
        policy["docling_core_version"] = "unavailable-profile"
        payloads.lowering = replace(lowering, native_policy=json.dumps(policy).encode())
        with pytest.raises(
            ValueError, match="native callbacks require exactly docling-core unavailable-profile"
        ):
            payloads.certify(document, tmp_path / "wrong-policy.jsonl", **basis)
    finally:
        payloads.close()


def test_batch_native_identity_prepares_captured_columns_with_independent_fields(tmp_path):
    import pyarrow as pa

    from corpus_structure.semantic.pdf_records import native_record_identity_fields_batch

    batch = pa.RecordBatch.from_pylist([
        {"record_id": "r", "native_type": "TextItem", "family": "texts", "scalars_json": '{"é":null,"alpha":{"native_float64":"8000000000000000"},"value":1e-20}', "structure_json": '{"fields":{"children":{"kind":"array","length":0}}}'},
    ])
    def forbidden(stream):
        raise AssertionError("inline identity requested an artifact")

    assert list(native_record_identity_fields_batch(batch, kind="native", scalar_descriptor=forbidden)) == [
        ("native", "r", (("native_type", "TextItem"), ("family", "texts"), ("alpha/value", -0.0), ("children/kind", "array"), ("children/length", 0), ("value/value", 1e-20), ("é/value", None)))
    ]


def test_batch_certification_matches_independent_ordered_record_reference(tmp_path):
    from corpus_structure.semantic.pdf_record_identity import LogicalIdentity
    from corpus_structure.semantic.pdf_records import NativeRow, native_record_identity_fields

    payloads, _document, basis = prepared(tmp_path)
    try:
        expected = []
        for family in ("header", "native", "membership"):
            for values in payloads.entries(family):
                row = {name: value for name, value in values.items() if value is not None}
                expected.append(native_record_identity_fields(NativeRow("document" if family == "header" else family, row), scalar_descriptor=payloads._descriptor))
        inputs = {row["local_id"]: row["body"] for row in payloads.companions("input")}
        for family in payloads._companions:
            for row in payloads.companions(family):
                expected.extend(payloads._companion_frames(row, inputs, {}))
        expected.append(("publication", "root", (("kind", basis["kind"]), ("recipe_digest", basis["recipe_digest"]))))
        folded = LogicalIdentity(basis["schema_digest"], basis["release_id"], basis["source_digest"])
        for family, key, fields in sorted(expected, key=lambda row: (row[0].encode(), row[1].encode())):
            folded.add_record(family, key, fields)
        actual = payloads.logical_digest(**{name: basis[name] for name in ("release_id", "source_digest", "recipe_digest", "schema_digest", "kind", "target_meanings")})
        assert actual == folded.pin().logical_digest
    finally:
        payloads.close()


@pytest.mark.parametrize("corrupt", [None, "shared", "unreferenced"])
def test_certifier_checks_shared_and_unreferenced_live_part_buffers(tmp_path, corrupt):
    import pyarrow as pa
    from semantic.pdf_payload_validation_support import add_row

    from corpus_structure.semantic.pdf_record_identity import BLOCK_BYTES, byte_root

    payloads, _document, basis = prepared(tmp_path)
    try:
        for stream in ("shared", "unreferenced"):
            raw = (b"a" if stream == "shared" else b"z") * (BLOCK_BYTES + 13)
            length, root = byte_root((raw,))
            add_row(payloads, "artifact_stream", {
                "stream_id": stream, "byte_length": length, "byte_root": root.hex(),
                "encoding_profile": "pdf-record-scalar-v1:s", "serialization_sha256": sha256(raw).hexdigest(),
            })
            offset = 0
            for ordinal, chunk in enumerate((raw[:17], raw[17:BLOCK_BYTES], raw[BLOCK_BYTES:])):
                original = chunk
                if stream == corrupt and ordinal == 0:
                    chunk = b"!" + chunk[1:]
                add_row(payloads, "artifact_part", {
                    "stream_id": stream, "ordinal": ordinal, "byte_offset": offset,
                    "body": chunk, "sha256_digest": sha256(original).hexdigest(),
                })
                offset += len(chunk)
        schema = next(payloads.batches("native")).schema
        for identity in ("shared:a", "shared:b"):
            payloads.add_batch("native", pa.RecordBatch.from_pylist([
                {"record_id": identity, "native_type": "TextItem", "family": "texts", "scalars_json": "{}", "structure_json": '{"fields":{"text":{"kind":"parts","stream_id":"shared"}}}'},
            ], schema=schema))
        options = {name: basis[name] for name in ("release_id", "source_digest", "recipe_digest", "schema_digest", "kind", "target_meanings")}
        if corrupt is not None:
            with pytest.raises(ValueError, match="part actual bytes"):
                payloads.logical_digest(**options)
        else:
            digest = payloads.logical_digest(**options)
            assert len(digest) == 64
            assert payloads._verified_streams >= {"shared", "unreferenced"}
    finally:
        payloads.close()
