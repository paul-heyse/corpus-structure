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


def _json(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    raise TypeError(type(value).__name__)


def export_packet(
    packet: CapturedPacket, destination: Path, *, format: Literal["jsonl", "parquet"] = "parquet"
) -> dict:
    """Write a fresh directory atomically; cancellation never publishes a partial export."""
    if format not in {"jsonl", "parquet"}:
        raise ValueError("export format must be jsonl or parquet")
    if set(packet.relations) != set(SPINE):
        raise ValueError("export requires the complete captured semantic projection")
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "format": "semantic-export-1",
        "encoding": format,
        "binding": asdict(packet.binding),
        "projection_id": packet.projection_id,
        "profile_digest": packet.profile_digest,
        "scale": packet.scale,
        "property_ids": packet.property_ids,
        "exact_values": "typed_value lexical and role graph are authoritative; derived numeric columns retain rounding flags",
        "jsonl_binary": "base64",
        "jsonl_decimal": "decimal string",
        "relations": {},
    }
    with TemporaryDirectory(prefix=".semantic-export-", dir=destination.parent) as scratch:
        root = Path(scratch) / "export"
        root.mkdir()
        for name in SPINE:
            relation = packet.relations[name]
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
                pq.write_table(relation, path, store_schema=True)
            else:
                with path.open("w", encoding="utf-8") as stream:
                    for batch in relation.to_batches(max_chunksize=1024):
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
            with path.open("rb") as checksum:
                digest = file_digest(checksum, "sha256").hexdigest()
            manifest["relations"][name] = {
                "file": path.name,
                "rows": relation.num_rows,
                "sha256": digest,
                "arrow_schema": base64.b64encode(relation.schema.serialize().to_pybytes()).decode(
                    "ascii"
                ),
            }
        (root / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        root.rename(destination)
    return manifest
