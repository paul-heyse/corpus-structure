"""An explicit source evidence packet for agent inspection."""

from __future__ import annotations

from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Connection

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.serve.native_source import (
    NativeSourceRequest,
    NativeSourceResponse,
    inspect_native_source,
)


class VisualEvidencePacket(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: Literal[1] = 1
    standing: Literal["recognition_candidate"] = "recognition_candidate"
    digest: str
    source: NativeSourceResponse


def visual_evidence_packet(conn: Connection, request: NativeSourceRequest) -> VisualEvidencePacket:
    if request.view != "visual_evidence" or request.artifact_digest is not None:
        raise ValueError("visual evidence packet requires an explicit typed evidence selection")
    source = inspect_native_source(conn, request)
    content = canonical_bytes(
        {
            "version": 1,
            "standing": "recognition_candidate",
            "source": source.model_dump(mode="json"),
        }
    )
    return VisualEvidencePacket(digest=sha256(content).hexdigest(), source=source)
