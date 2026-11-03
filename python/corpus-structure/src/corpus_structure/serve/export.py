"""Atomic detached SP-05 exports; a manifest qualifies every full physical relation."""

from __future__ import annotations

import base64
import json
from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from hashlib import file_digest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

import pyarrow.parquet as pq

from corpus_structure.semantic.analytics import SPINE, CapturedPacket
from corpus_structure.semantic.capture_storage import FileRelation, LogicalRows
from corpus_structure.semantic.record_queries import CompletedRecordProjection


def _json(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    raise TypeError(type(value).__name__)


def export_packet(
    packet: CapturedPacket,
    destination: Path,
    *,
    format: Literal["jsonl", "parquet"] = "parquet",
    records: CompletedRecordProjection | None = None,
) -> dict:
    """Write a fresh directory atomically; cancellation never publishes a partial export."""
    if format not in {"jsonl", "parquet"}:
        raise ValueError("export format must be jsonl or parquet")
    if set(packet.relations) != set(SPINE):
        raise ValueError("export requires the complete captured semantic projection")
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    packet.validate_manifest()
    manifest = {
        "format": "semantic-export-2" if packet.manifest else "semantic-export-1",
        "logical_digest": packet.logical_digest,
        "digest_recipe": "canonical-rows-1",
        "encoding": format,
        "binding": asdict(packet.binding),
        "projection_id": packet.projection_id,
        "profile_digest": packet.profile_digest,
        "scale": packet.scale,
        "property_ids": packet.property_ids,
        "exact_values": (
            "typed_value lexical and role graph are authoritative; "
            "derived numeric columns retain rounding flags"
        ),
        "jsonl_binary": "base64",
        "jsonl_decimal": "decimal string",
        "relations": {},
    }
    with TemporaryDirectory(prefix=".semantic-export-", dir=destination.parent) as scratch:
        root = Path(scratch) / "export"
        root.mkdir()
        for name in SPINE:
            relation = packet.relations[name]
            if isinstance(relation, FileRelation):
                relation.verify()
            logical = LogicalRows(relation.schema)
            metadata = relation.schema.metadata or {}
            expected = {
                "release": packet.binding.release_id,
                "realization": packet.binding.realization_id,
                "data_revision": str(packet.binding.data_revision),
                "capture": packet.binding.capture_id,
                "projection": packet.projection_id,
                "profile": packet.profile_digest,
                "relation": name,
            }
            if any(metadata.get(("cs." + k).encode()) != v.encode() for k, v in expected.items()):
                raise ValueError(f"relation {name} has no matching captured provenance")
            path = root / (name + "." + format)
            if format == "parquet":
                with pq.ParquetWriter(path, relation.schema, store_schema=True) as writer:
                    for batch in packet.iter_batches(name):
                        logical.write(batch)
                        writer.write_batch(batch)
            else:
                with path.open("w", encoding="utf-8") as stream:
                    for batch in packet.iter_batches(name, batch_size=1024):
                        logical.write(batch)
                        for row in batch.to_pylist():
                            stream.write(
                                json.dumps(
                                    row,
                                    default=_json,
                                    ensure_ascii=False,
                                    allow_nan=False,
                                    separators=(",", ":"),
                                )
                                + "\n"
                            )
            if (
                packet.manifest
                and logical.digest != packet.manifest["relations"][name]["logical_digest"]
            ):
                raise ValueError("export content differs from captured logical digest")
            with path.open("rb") as checksum:
                digest = file_digest(checksum, "sha256").hexdigest()
            manifest["relations"][name] = {
                "file": path.name,
                "rows": relation.num_rows,
                "logical_digest": packet.manifest["relations"][name]["logical_digest"]
                if packet.manifest
                else None,
                "sha256": digest,
                "arrow_schema": base64.b64encode(relation.schema.serialize().to_pybytes()).decode(
                    "ascii"
                ),
            }
        if records is not None:
            from corpus_structure.serve.record_export import write_record_relations

            record_manifest, record_relations = write_record_relations(
                records, root, packet.binding, format=format
            )
            manifest["format"] = "semantic-export-3"
            manifest["logical_digest_scope"] = "captured_semantic_spine"
            manifest["record_projection"] = record_manifest
            manifest["relations"].update(record_relations)
        (root / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        root.rename(destination)
    return manifest
