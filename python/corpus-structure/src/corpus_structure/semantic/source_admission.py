"""Authenticate an existing original source once before freezing demand intent.

This adapter reads persisted published custody. The public native admission command
independently reauthenticates it and builds its body; this value grants no write or
original-fact support authority and never supplies a caller-built publication body.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sqlalchemy import bindparam, func, select
from sqlalchemy.dialects.postgresql import JSONB

from .identity import canonical_bytes
from .metadata import table
from .pdf_record_reader import PublishedReadBudget
from .source_products import FrozenNativeSource, source_subject
from .source_views import load_source_view
from .structural_products import ExternalSourceRef
from .types import PreparedRelease

if TYPE_CHECKING:
    from sqlalchemy import Connection

    from .data_operation_demands import RootSubject
    from .data_operation_support import OriginalSourceSelection


@dataclass(frozen=True)
class OriginalSourceAcquisition:
    name: str
    reference: ExternalSourceRef
    selectors: bytes
    source: FrozenNativeSource
    original_content_hash: str

    @property
    def root(self) -> RootSubject:
        from .data_operation_demands import RootSubject

        selected = self.source.value
        return RootSubject(
            source_subject(selected["source"]),
            selected["source"]["document"],
            canonical_bytes({"source": selected["source"], "selectors": selected["selectors"]}),
        )

    def selection(self) -> OriginalSourceSelection:
        from .data_operation_support import OriginalSourceSelection

        return OriginalSourceSelection(
            self.name, canonical_bytes(self.reference.model_dump(mode="json")), self.selectors
        )


def acquire_original_source_selection(
    connection: Connection,
    prepared: PreparedRelease,
    reference: ExternalSourceRef,
    selectors: Sequence[Mapping[str, Any]],
    *,
    name: str = "original",
    read_budget: PublishedReadBudget | None = None,
) -> OriginalSourceAcquisition:
    if not name or not selectors:
        raise ValueError("original source acquisition requires its named exact selection")
    reference = ExternalSourceRef.model_validate(reference.model_dump(mode="python"))
    selected = [
        prepared.validate_json(
            "CharacterizationSourceSelector", canonical_bytes(selector)
        ).model_dump(mode="json", exclude_unset=True)
        for selector in selectors
    ]
    # Reuse the existing native completed-source proof. No Reader source discovery,
    # newest-layer lookup or source body enters a semantic policy parameter.
    connection.execute(
        select(
            func.ops.validate_structural_source(
                bindparam("original_reference", reference.model_dump(mode="json"), type_=JSONB)
            )
        )
    )
    budget = read_budget or PublishedReadBudget(max_rows=100_000, max_bytes=32 * 1024 * 1024)
    view = load_source_view(
        connection, reference.source_view_id, analysis=False, read_budget=budget
    )
    documents = table("kb.document")
    document = connection.execute(
        select(documents.c.key, documents.c.content_hash).where(
            documents.c.id == view.ref.document_id, documents.c.project_id == reference.project_id
        )
    ).one()
    source = FrozenNativeSource.from_source_view(
        prepared, view, document=document.key, selectors=selected
    )
    return OriginalSourceAcquisition(
        name, reference, canonical_bytes(selected), source, document.content_hash
    )
