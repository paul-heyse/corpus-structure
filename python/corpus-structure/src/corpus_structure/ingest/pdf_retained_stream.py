"""One-pass lossless storage migration of retained PDF envelopes.

Only the selected native document is materialized for the explicitly supported
native phase. Companion arrays are emitted one record at a time. Exact historical
byte identity is checked independently of decoded JSON values before publication.
"""
from __future__ import annotations

import gzip
from collections.abc import Iterator, Mapping
from hashlib import sha256
from pathlib import Path
from typing import Any, BinaryIO

from ijson.backends.python import parse
from ijson.common import ObjectBuilder


class _DigestReader:
    def __init__(self, stream: BinaryIO):
        self.stream = stream
        self.digest = sha256()
        self.byte_length = 0

    def read(self, size: int = -1) -> bytes:
        value = self.stream.read(size)
        self.digest.update(value)
        self.byte_length += len(value)
        return value


_ARRAYS = {
    "inputs.item": "input", "occurrences.item": "occurrence",
    "relations.item": "relation", "mapping_reports.item": "mapping_report",
    "coverage.item": "coverage", "content.recognition_coverage.item": "recognition_coverage",
    "recognition_coverage.item": "recognition_coverage",
}
_VALUES = {
    "document": "document", "content.document": "document",
    "health": "health", "content.health": "native_health",
    "artifact_digest": "artifact_digest", "content.artifact_digest": "artifact_digest",
    "source_scope": "source_scope", "content.source_scope": "source_scope",
}

for _kind in (
    "inline_candidate_pages", "derivation_mappings", "cell_reports",
    "inline_alignment_reports", "recognition_coverage",
):
    for _prefix in ("", "content."):
        _ARRAYS[_prefix + _kind + ".item"] = "native_metadata:" + _kind
for _prefix in ("", "content."):
    _VALUES[_prefix + "runtime_report"] = "native_metadata:runtime_report"



def iter_retained_pdf_values(
    stream: BinaryIO, *, expected_sha256: str,
) -> Iterator[tuple[str, Any]]:
    """Consume to exhaustion before freezing; a partial iterator verifies nothing.

    Python ijson with use_float=True deliberately matches json.loads' binary64
    native JSON profile while retaining arbitrary-size integer tokens. The C
    backend's use_float integer overflow does not satisfy that profile.
    """
    reader = _DigestReader(stream)
    builder: ObjectBuilder | None = None
    selected = ""
    depth = 0
    seen_document = False
    for prefix, event, value in parse(reader, use_float=True):
        if builder is None:
            family = _VALUES.get(prefix) or _ARRAYS.get(prefix)
            if family is None or event in {"end_map", "end_array", "map_key"}:
                continue
            if family == "document":
                if seen_document:
                    raise ValueError("retained PDF envelope has multiple native documents")
                seen_document = True
            if event not in {"start_map", "start_array"}:
                yield family, value
                continue
            builder = ObjectBuilder()
            selected = family
            depth = 0
        builder.event(event, value)
        if event in {"start_map", "start_array"}:
            depth += 1
        elif event in {"end_map", "end_array"}:
            depth -= 1
        if depth == 0:
            yield selected, builder.value
            builder = None
    if not seen_document:
        raise ValueError("retained PDF envelope has no native document")
    if reader.digest.hexdigest() != expected_sha256:
        raise ValueError("retained PDF exact serialization digest differs")


def retained_pdf_draft(
    path: Path, *, expected_sha256: str, product_key: str,
    original: bytes, schema_bytes: bytes, recipe_bytes: bytes, directory: Path,
):
    """Own the companion journal while the caller stages and seals this draft."""
    from contextlib import contextmanager
    from corpus_structure.core.method import PdfRecordPublicationDraft, RetainedPdfSerialization
    from .pdf_stream_reconciliation import ReconciliationJournal

    @contextmanager
    def owned():
        journal = ReconciliationJournal(directory)
        document = None
        health: Mapping[str, Any] | None = None
        integration_health: Mapping[str, Any] | None = None
        metadata_ordinals: dict[str, int] = {}
        opener = gzip.open if path.suffix == ".gz" else Path.open
        try:
            with opener(path, "rb") as source:
                for family, value in iter_retained_pdf_values(
                    source, expected_sha256=expected_sha256,
                ):
                    if family == "document":
                        document = value
                    elif family == "artifact_digest":
                        if value != sha256(original).hexdigest():
                            raise ValueError("retained envelope original custody differs")
                    elif family == "source_scope":
                        if value != "whole_document":
                            raise ValueError("retained storage migration requires whole-document scope")
                    elif family == "native_health":
                        health = value
                    elif family == "health":
                        integration_health = value
                    elif family.startswith("native_metadata:"):
                        kind = family.split(":", 1)[1]
                        ordinal = metadata_ordinals.get(kind, 0)
                        journal.collection("native_metadata").append({
                            "kind": kind, "ordinal": ordinal, "value": value,
                        })
                        metadata_ordinals[kind] = ordinal + 1
                    else:
                        journal.collection(family).append(value)
            journal.seal()
            if health is None:
                health = integration_health
                integration_health = None
            if document is None or health is None:
                raise ValueError("retained PDF requires native content and qualified health")
            companions = {
                family: journal.collection(family)
                for family in ("input", "occurrence", "relation", "mapping_report", "coverage", "native_metadata")
            }
            companions["health"] = ({
                "health": dict(health), "source_scope": "whole_document",
                **({"integration_health": dict(integration_health)} if integration_health is not None else {}),
                "derivation": {"kind": "retained-exact-envelope-v1", "serialization_sha256": expected_sha256},
            },)
            yield PdfRecordPublicationDraft(
                document, product_key, original, schema_bytes, recipe_bytes, health,
                companions=companions,
                retained_serialization=RetainedPdfSerialization(
                    path, expected_sha256, "gzip" if path.suffix == ".gz" else "none",
                ),
            )
        finally:
            journal.close()
    return owned()
