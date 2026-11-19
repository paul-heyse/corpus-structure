"""Independent output-contract and exact-file recovery assertions; no converter claims."""

import json
from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace

import pyarrow as pa
import pytest
from docling_core.types.doc import DocItemLabel, DoclingDocument, Size

from corpus_structure.ingest.pdf_stream_types import PdfStreamReply
from corpus_structure.ingest.pdf_streaming import (
    PdfStreamSpool,
    StreamingPdfResult,
    _atomic_bytes,
    _ref,
)
from corpus_structure.semantic.pdf_certification import (
    PdfProducerCertification,
    PdfProducerPayloads,
    prepare_pdf_producer_contract,
    write_pdf_companion_sets,
)
from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
from corpus_structure.semantic.pdf_lowering import LOWERING_CONTRACT
from corpus_structure.semantic.pdf_payloads import prepare_payload_family
from corpus_structure.semantic.pdf_spool_native import (
    SPOOL_MATERIAL_PREFIX,
    spool_material_document,
)
from corpus_structure.semantic.pdf_spool_recertification import (
    rebind_pdf_recovery_reply,
    recertify_pdf_recovery,
)


def test_archived_material_ignores_action_transport_and_refuses_schema_or_implementation_change():
    context = trusted_pdf_context()
    original = context.domain.source(LOWERING_CONTRACT).content
    document = json.loads(original)
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
    for suffix in ("schema/inline_candidate_pages.json", "semantic/pdf_certification.py"):
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


def test_authorized_original_records_rebind_only_carriers_and_recertify_actual_output(tmp_path):
    context = trusted_pdf_context()
    contract = prepare_pdf_producer_contract(context, kind="native")
    source_digest, recipe_digest = sha256(b"source").hexdigest(), sha256(b"recipe").hexdigest()
    schema_digest = context.native_schema_digest
    original_build = SimpleNamespace(build_id="build:original", release_id="release:original")
    current_build = SimpleNamespace(build_id="build:current", release_id="release:current")
    document = DoclingDocument(name="independent exact original")
    document.add_page(page_no=1, size=Size(width=200, height=300))
    document.add_text(label=DocItemLabel.TEXT, text="Original repeated value.")
    streamed = StreamingPdfResult(
        document, PdfStreamSpool(tmp_path / "pages"), "success", (), b"recipe", ()
    )
    replays = streamed.write_record_batches(
        tmp_path / "records",
        build_id=original_build.build_id,
        release_id=original_build.release_id,
        source_digest=source_digest,
    )
    companions = write_pdf_companion_sets(
        tmp_path / "companions",
        original_build,
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
    payloads = PdfProducerPayloads(
        tmp_path / "original.sqlite", json.loads(contract.validation_contract)
    )
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
    derived = []
    rebound = rebind_pdf_recovery_reply(
        reply,
        tmp_path / "rebound",
        original_build=original_build.build_id,
        original_release=original_build.release_id,
        build=current_build,
        on_replay=derived.append,
        check_active=lambda: None,
    )
    for replay in (*rebound.record_replays, *_all_companions(rebound.companion_sets)):
        with pa.memory_map(str(replay.path), "r") as source:
            reader = pa.ipc.open_file(source)
            for index in range(reader.num_record_batches):
                rows = reader.get_batch(index).to_pylist()
                assert all(
                    row.get("product_id", current_build.build_id) == current_build.build_id
                    for row in rows
                )
    current = recertify_pdf_recovery(
        rebound,
        tmp_path / "recertified",
        original_release=original_build.release_id,
        validation_contract=contract.validation_contract,
        lowering_identity=contract.lowering_identity,
        build=current_build,
        source_digest=source_digest,
        recipe_digest=recipe_digest,
        schema_digest=schema_digest,
        on_replay=derived.append,
        check_active=lambda: None,
    )
    recertified = PdfProducerCertification(**json.loads(current.certification.path.read_bytes()))
    assert recertified.lowering_identity == contract.lowering_identity
    assert recertified.logical_digest == certificate.logical_digest
    assert recertified.native_document_digest == certificate.native_document_digest
    assert recertified.stream_inventory_digest == certificate.stream_inventory_digest
    assert current.access_replay == reply.access_replay
    assert {path: path.read_bytes() for path in originals} == originals
    # The original certification must authenticate every logical record, even
    # when the physical file has internally valid current Arrow structure.
    corrupted = json.loads(certificate_replay.path.read_bytes())
    corrupted["logical_digest"] = "0" * 64
    forged = _atomic_bytes(
        tmp_path / "forged.json", json.dumps(corrupted).encode(), "producer_certification"
    )
    from dataclasses import replace

    with pytest.raises(ValueError, match="actual output differs"):
        recertify_pdf_recovery(
            replace(rebound, certification=forged),
            tmp_path / "refused",
            original_release=original_build.release_id,
            validation_contract=contract.validation_contract,
            lowering_identity=contract.lowering_identity,
            build=current_build,
            source_digest=source_digest,
            recipe_digest=recipe_digest,
            schema_digest=schema_digest,
            on_replay=derived.append,
            check_active=lambda: None,
        )


def _all_companions(sets):
    return tuple(replay for prepared in sets for replay in prepared.replays)
