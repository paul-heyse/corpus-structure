"""Independent output-contract and exact-file recovery assertions; no converter claims."""

import json
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256

import pyarrow as pa
import pytest
from docling_core.types.doc import DocItemLabel, DoclingDocument, Size

from corpus_structure.ingest.pdf_stream_types import PdfReplayRef, PdfStreamReply
from corpus_structure.ingest.pdf_streaming import (
    PdfStreamSpool,
    StreamingPdfResult,
    _atomic_bytes,
    _ref,
)
from corpus_structure.semantic.pdf_certification import (
    PdfProducerPayloads,
    prepare_pdf_producer_contract,
    write_pdf_companion_sets,
)
from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
from corpus_structure.semantic.pdf_lowering_context import capture_pdf_lowering
from corpus_structure.semantic.pdf_payloads import prepare_payload_family
from corpus_structure.semantic.pdf_replay_transport import (
    PdfReplayBinding,
    bind_copy_batch,
    read_replay_batches,
    replay_schema,
)
from corpus_structure.semantic.pdf_spool_native import (
    SPOOL_MATERIAL_PREFIX,
    spool_material_document,
)
from corpus_structure.semantic.pdf_spool_recertification import recertify_pdf_recovery


def test_archived_material_ignores_action_transport_and_refuses_schema_or_implementation_change():
    # This projection test authors a closed inventory independently of the live
    # code capture. It does not claim the production lowering closure is complete.
    document = {
        "profile": "pdf-record-lowering-contract-v2",
        "compiler_policy": "independent-test-policy",
        "code_identity": {"complete": True},
        "libraries": {"independent-library": "1.0"},
        "inputs": [
            {"name": name, "sha256": "a" * 64}
            for name in (
                *(
                    SPOOL_MATERIAL_PREFIX + suffix
                    for suffix in (
                        "code/meaning.json",
                        "schema/docling-native.json",
                        "codec/inline-candidates.arrow",
                    )
                ),
                "pdf-domain/native/actions.yaml",
                "pdf-domain/semantic/_pdf_native_calls.py",
            )
        ],
    }
    original = json.dumps(document).encode()
    incomplete = deepcopy(document)
    incomplete["code_identity"]["complete"] = False
    with pytest.raises(ValueError, match="no supported original lowering snapshot"):
        spool_material_document(json.dumps(incomplete).encode())
    action_only = deepcopy(document)
    for item in action_only["inputs"]:
        if item["name"].endswith("native/actions.yaml") or item["name"].endswith(
            "semantic/_pdf_native_calls.py"
        ):
            item["sha256"] = "f" * 64
    assert action_only != document
    assert spool_material_document(json.dumps(action_only).encode()) == spool_material_document(
        original
    )
    for suffix in ("schema/docling-native.json", "code/meaning.json"):
        changed = deepcopy(document)
        selected = next(
            item for item in changed["inputs"] if item["name"] == SPOOL_MATERIAL_PREFIX + suffix
        )
        selected["sha256"] = "e" * 64
        assert spool_material_document(json.dumps(changed).encode()) != spool_material_document(
            original
        )
    document["inputs"] = []
    with pytest.raises(ValueError, match="missing original"):
        spool_material_document(json.dumps(document).encode())


def test_authorized_original_records_supply_current_copy_carriers_and_recertify(tmp_path):
    context = trusted_pdf_context()
    contract = prepare_pdf_producer_contract(context, kind="native")
    source_digest, recipe_digest = sha256(b"source").hexdigest(), sha256(b"recipe").hexdigest()
    schema_digest = context.native_schema_digest
    original_build = PdfReplayBinding("build:original", "release:original")
    current_build = PdfReplayBinding("build:current", "release:current")
    document = DoclingDocument(name="independent exact original")
    document.add_page(page_no=1, size=Size(width=200, height=300))
    document.add_text(label=DocItemLabel.TEXT, text="Original repeated value.")
    streamed = StreamingPdfResult(
        document, PdfStreamSpool(tmp_path / "pages"), "success", (), b"recipe", ()
    )
    replays = streamed.write_record_batches(
        tmp_path / "records",
        source_digest=source_digest,
    )
    companions = write_pdf_companion_sets(
        tmp_path / "companions",
        {
            "health": [
                {
                    "conversion": "success",
                    "display_coverage": "unknown",
                    "inline_coverage": "unknown",
                    "cell_coverage": "unknown",
                    "source_scope": "whole_document",
                }
            ]
        },
        payload_family=prepare_payload_family(context),
        check_active=lambda: None,
    )
    access_path = tmp_path / "access.jsonl"
    payloads = PdfProducerPayloads(json.loads(contract.validation_contract))
    try:
        payloads.add_replays(replays)
        payloads.add_companion_replays(companions)
        certificate = payloads.certify(
            document,
            access_path,
            release_id=original_build.release_id,
            source_digest=source_digest,
            recipe_digest=recipe_digest,
            schema_digest=schema_digest,
            kind="native",
            lowering_identity="old-action-transport-identity",
            target_meanings={},
        )
    finally:
        payloads.close()
    certificate_replay = _atomic_bytes(
        tmp_path / "certificate.json", certificate.to_bytes(), "producer_certification"
    )
    reply = PdfStreamReply(
        "success",
        (),
        b"recipe",
        (),
        replays,
        companion_sets=companions,
        certification=certificate_replay,
        access_replay=_ref(access_path, "producer_access"),
    )
    originals = {
        replay.path: replay.path.read_bytes()
        for replay in (*replays, certificate_replay, *_all_companions(companions))
    }
    lowering = capture_pdf_lowering(context)
    for replay in (*replays, *_all_companions(companions)):
        name = (
            replay.family.replace("prepared_companion:", "companion:")
            if replay.family.startswith("prepared_companion:")
            else "stage:" + replay.family
        )
        physical = lowering.schema(name)
        for batch in read_replay_batches(replay, physical, check_active=lambda: None):
            assert not {"product_id", "revision_id", "release_id"}.intersection(batch.schema.names)
            bound = bind_copy_batch(batch, physical, current_build)
            assert bound.column("product_id").to_pylist() == [current_build.build_id] * len(batch)
            assert bound.column("revision_id").to_pylist() == [current_build.build_id] * len(batch)
            if "release_id" in bound.schema.names:
                assert bound.column("release_id").to_pylist() == [current_build.release_id] * len(
                    batch
                )
    recertified = recertify_pdf_recovery(
        reply,
        tmp_path / "recertified",
        original=original_build,
        original_lowering=lowering,
        original_lowering_identity=certificate.lowering_identity,
        validation_contract=contract.validation_contract,
        lowering_identity=contract.lowering_identity,
        source_digest=source_digest,
        recipe_digest=recipe_digest,
        schema_digest=schema_digest,
        check_active=lambda: None,
    )
    assert recertified.lowering_identity == contract.lowering_identity
    assert recertified.logical_digest == certificate.logical_digest
    assert recertified.native_document_digest == certificate.native_document_digest
    assert recertified.stream_inventory_digest == certificate.stream_inventory_digest
    assert {path: path.read_bytes() for path in originals} == originals
    # The original certification must authenticate every logical record, even
    # when the physical file has internally valid current Arrow structure.
    corrupted = json.loads(certificate_replay.path.read_bytes())
    corrupted["logical_digest"] = "0" * 64
    forged = _atomic_bytes(
        tmp_path / "forged.json", json.dumps(corrupted).encode(), "producer_certification"
    )
    with pytest.raises(ValueError, match="actual output differs"):
        recertify_pdf_recovery(
            replace(reply, certification=forged),
            tmp_path / "refused",
            original=original_build,
            original_lowering=lowering,
            original_lowering_identity=certificate.lowering_identity,
            validation_contract=contract.validation_contract,
            lowering_identity=contract.lowering_identity,
            source_digest=source_digest,
            recipe_digest=recipe_digest,
            schema_digest=schema_digest,
            check_active=lambda: None,
        )


def _all_companions(sets):
    return tuple(replay for prepared in sets for replay in prepared.replays)


def test_legacy_projection_requires_original_binding_and_captured_columns(tmp_path):
    physical = pa.schema(
        [("product_id", pa.string()), ("revision_id", pa.string()), ("value", pa.binary())],
        metadata={"physical_model_id": "original-layout"},
    )
    adopted = physical.with_metadata({"physical_model_id": "current-layout"})
    old = PdfReplayBinding("original", "original-release")
    new = PdfReplayBinding("target", "target-release")
    path = tmp_path / "sealed.arrow"
    with pa.ipc.new_file(str(path), physical) as writer:
        writer.write_batch(
            pa.record_batch([["original"], ["original"], [b"same"]], schema=physical)
        )
    replay = PdfReplayRef.from_path(path, "native", 1)
    eligibility = {"check_active": lambda: None, "legacy_schema": physical}
    with pytest.raises(ValueError, match="captured transport schema"):
        list(read_replay_batches(replay, adopted, **eligibility))
    with pytest.raises(ValueError, match="foreign physical carrier"):
        list(read_replay_batches(replay, adopted, legacy_binding=new, **eligibility))
    (batch,) = read_replay_batches(replay, adopted, legacy_binding=old, **eligibility)
    assert batch.schema == replay_schema(adopted)
    assert bind_copy_batch(batch, adopted, new).to_pylist() == [
        {"product_id": "target", "revision_id": "target", "value": b"same"}
    ]
    replay.verify()
