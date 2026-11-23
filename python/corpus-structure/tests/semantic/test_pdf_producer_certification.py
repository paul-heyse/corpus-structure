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
from corpus_structure.semantic.pdf_companion_encoding import PdfCompanionEncodingBasis
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
    replays = streamed.write_record_batches(
        tmp_path / "records", build_id="build", release_id="release", source_digest="a" * 64
    )
    metadata = [{"kind": "runtime_report", "ordinal": 0, "value": {"effective_options": "{}"}}]
    if candidate is not None:
        metadata.append({"kind": "inline_candidate_pages", "ordinal": 1, "value": candidate})
    sets = write_pdf_companion_sets(
        tmp_path / "companions",
        PdfCompanionEncodingBasis("build", "release"),
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
    payloads = PdfProducerPayloads(tmp_path / "payloads.sqlite", contract)
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
        assert [row["body"]["pointer"] for row in rows] == ["#/body", "#/furniture"]
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
        require_lowering_identity(SimpleNamespace(domain=SimpleNamespace(source=source)))


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
        for key, raw in payloads.db.exec_driver_sql(
            "SELECT key,body FROM native_entry WHERE family='native'"
        ):
            row = json.loads(raw)
            scalars = json.loads(row["scalars_json"])
            if scalars.get("name") == "producer source":
                scalars["name"] = "lossy source"
                row["scalars_json"] = json.dumps(scalars)
                payloads.db.exec_driver_sql(
                    "UPDATE native_entry SET body=? WHERE family='native' AND key=?",
                    (json.dumps(row), key),
                )
                break
        else:
            raise AssertionError("independent native name witness is absent")
        certification = payloads.certify(document, tmp_path / "producer-access.jsonl", **basis)

        def rows(family, filters):
            if family in {"header", "native", "membership"}:
                for (raw,) in payloads.db.exec_driver_sql(
                    "SELECT body FROM native_entry WHERE family=?", (family,)
                ):
                    yield json.loads(raw)
            elif family == "companion":
                for row in payloads.companions(filters["family"]):
                    row["_fields"] = [
                        json.loads(raw)
                        for (raw,) in payloads.db.exec_driver_sql(
                            "SELECT body FROM entry WHERE family='companion_field'"
                        )
                        if (json.loads(raw)["family"], json.loads(raw)["local_id"])
                        == (row["family"], row["local_id"])
                    ]
                    yield row
            elif family == "artifact_stream":
                for (raw,) in payloads.db.exec_driver_sql(
                    "SELECT body FROM entry WHERE family='artifact_stream'"
                ):
                    row = json.loads(raw)
                    if row["stream_id"] in filters["stream_ids"]:
                        yield row
            elif family == "artifact_part":
                for stream in filters["stream_ids"]:
                    for ordinal, body in payloads.db.exec_driver_sql(
                        "SELECT ordinal,body FROM part WHERE stream=? ORDER BY ordinal", (stream,)
                    ):
                        yield {"stream_id": stream, "ordinal": ordinal, "body": body}

        capture = tmp_path / "oracle.arrow"
        write_pdf_oracle_capture(
            capture,
            context=trusted_pdf_context(),
            kind="native",
            rows=rows,
            json_fields="text",
            check_active=lambda: None,
        )
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

    from corpus_structure.semantic.pdf_publication import write_pdf_oracle_capture

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
    with pa.memory_map(str(path), "r") as source:
        reader = pa.ipc.open_file(source)
        actual = [
            json.loads(body)
            for index in range(reader.num_record_batches)
            for family, body in zip(
                reader.get_batch(index).column("family").to_pylist(),
                reader.get_batch(index).column("body").to_pylist(),
                strict=True,
            )
            if family == "membership"
        ]
    assert actual == [{"value_kind": "scalar", "scalar_json": "null"}]


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
            "build",
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
        build_id="build",
        release_id="release",
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
