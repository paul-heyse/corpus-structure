"""Acquire original document fact pins; native admission independently proves bytes."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from sqlalchemy import Connection, select

from .data_operation_demands import RootSubject
from .data_operation_support import OriginalDocumentRef, OriginalSourceSelection
from .identity import canonical_bytes
from .metadata import table


@dataclass(frozen=True)
class OriginalDocumentAcquisition:
    name: str
    reference: OriginalDocumentRef

    @property
    def root(self) -> RootSubject:
        coordinate = {"document": self.reference.document_key}
        return RootSubject(
            "original-document:" + sha256(canonical_bytes(coordinate)).hexdigest(),
            self.reference.document_key,
            canonical_bytes({**coordinate, "scope": "whole-document"}),
        )

    def selection(self) -> OriginalSourceSelection:
        return OriginalSourceSelection(
            self.name, canonical_bytes(self.reference.model_dump(mode="json")),
            canonical_bytes([{"scope": "whole-document"}]),
        )


def acquire_original_document_selection(
    connection: Connection, *, project_id: str, document_key: str, name: str = "original",
) -> OriginalDocumentAcquisition:
    """Read exact immutable metadata; this value does not grant fact admission."""
    if not name:
        raise ValueError("original document selection requires its explicit name")
    document = table("kb.document")
    row = connection.execute(select(
        document.c.project_id, document.c.key, document.c.content_hash, document.c.mime,
    ).where(document.c.project_id == project_id, document.c.key == document_key)).one()
    return OriginalDocumentAcquisition(name, OriginalDocumentRef(
        kind="original-document", project_id=row.project_id, document_key=row.key,
        content_hash=row.content_hash, mime=row.mime,
    ))
