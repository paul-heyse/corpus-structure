"""Explicit reconstruction verification of a currently authorized PDF publication."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Engine

from corpus_structure.core.db.lifetime import BorrowerCancellation
from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.serve.selected_pdf import SelectedPdfSourceReference
from corpus_structure.settings import AnalyticsSettings


class PdfSourceVerification(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    source: SelectedPdfSourceReference
    cut_id: str
    assurance: Literal["round-trip-verified"] = "round-trip-verified"
    release_id: str
    lowering_identity: str
    kind: Literal["native", "integrated"]
    logical_digest: str
    native_document_digest: str
    reconstructed_native_digest: str


def verify_selected_pdf_source(
    engine: Engine,
    source_reference: SelectedPdfSourceReference,
    *,
    directory: Path,
    cancellation: BorrowerCancellation,
    analytics_settings: AnalyticsSettings,
    execution_policy: CharacterizationExecutionPolicy,
) -> PdfSourceVerification:
    """Capture under authority, compute without a checkout, then recheck authority."""
    from corpus_structure.semantic.demand_results import selected_read_snapshot
    from corpus_structure.semantic.pdf_contracts import pdf_context_for_release
    from corpus_structure.semantic.pdf_publication import (
        capture_published_pdf_oracle,
        verify_published_pdf_oracle,
    )
    from corpus_structure.semantic.pdf_record_reader import published_record_reader
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.serve.selected_pdf import acquire_selected_pdf_source

    with selected_read_snapshot(engine, cancellation=cancellation) as connection:
        selected = acquire_selected_pdf_source(connection, source_reference)
        publication = selected.receipt.publication
        # Retained publications keep their producing release's lowering contract.
        prepared = open_release(connection, publication.release_id)
        context = pdf_context_for_release(connection, prepared)
        reader = published_record_reader(
            connection,
            selected.physical,
            cancellation=cancellation,
            projection_context=prepared,
        )
        if reader is None:
            raise ValueError("selected PDF publication is absent")
        capture = capture_published_pdf_oracle(
            reader,
            context=context,
            directory=directory,
            check_active=cancellation.check_active,
        )
        cut_id = selected.cut.identity
    verified = verify_published_pdf_oracle(
        capture,
        check_active=cancellation.check_active,
        settings=analytics_settings,
        policy=execution_policy,
    )
    cancellation.check_active()
    with selected_read_snapshot(engine, cancellation=cancellation) as connection:
        current = acquire_selected_pdf_source(connection, source_reference)
        if current.cut.identity != cut_id or current.receipt != selected.receipt:
            raise ValueError("PDF selection changed during reconstruction verification")
    kind = verified.kind
    if kind not in ("native", "integrated"):
        raise ValueError("unknown PDF publication kind")
    return PdfSourceVerification(
        source=source_reference,
        cut_id=cut_id,
        release_id=verified.release_id,
        lowering_identity=verified.lowering_identity,
        kind=kind,
        logical_digest=verified.logical_digest,
        native_document_digest=verified.native_document_digest,
        reconstructed_native_digest=verified.reconstructed_native_digest,
    )
