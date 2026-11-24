"""Current certification of authorized original PDF output without rewriting replays."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from corpus_structure.ingest.pdf_stream_types import PdfStreamReply

from .pdf_certification import PdfProducerCertification, PdfProducerPayloads
from .pdf_lowering_context import CapturedPdfLowering
from .pdf_replay_transport import PdfReplayBinding


def recertify_pdf_recovery(
    reply: PdfStreamReply,
    root: Path,
    *,
    original: PdfReplayBinding,
    original_lowering: CapturedPdfLowering,
    original_lowering_identity: str,
    validation_contract: bytes,
    lowering_identity: str,
    source_digest: str,
    recipe_digest: str,
    schema_digest: str,
    check_active,
) -> PdfProducerCertification:
    """Re-establish logical and byte roots after native checks material equivalence."""
    if reply.certification is None or reply.access_replay is None:
        raise ValueError("recovered PDF lacks original certified output custody")
    certificate = PdfProducerCertification(**json.loads(reply.certification.read_bytes()))
    if (
        certificate.lowering_identity,
        certificate.kind,
        certificate.source_digest,
        certificate.recipe_digest,
        certificate.schema_digest,
    ) != (original_lowering_identity, "native", source_digest, recipe_digest, schema_digest):
        raise ValueError("original PDF certification differs from its material premises")
    root.mkdir(parents=True, exist_ok=False)
    payloads = PdfProducerPayloads(root / "payloads.sqlite", json.loads(validation_contract))
    try:
        payloads.add_replays(
            reply.record_replays,
            check_active=check_active,
            legacy_binding=original,
            legacy_lowering=original_lowering,
        )
        payloads.add_companion_replays(
            reply.companion_sets,
            check_active=check_active,
            legacy_binding=original,
            legacy_lowering=original_lowering,
        )
        check_active()
        digest = payloads.logical_digest(
            release_id=original.release_id,
            source_digest=source_digest,
            recipe_digest=recipe_digest,
            schema_digest=schema_digest,
            kind="native",
            target_meanings={},
        )
        if (
            digest != certificate.logical_digest
            or payloads.stream_inventory_digest != certificate.stream_inventory_digest
        ):
            raise ValueError("recovered PDF actual output differs from original certification")
        return replace(certificate, lowering_identity=lowering_identity)
    finally:
        payloads.close()
