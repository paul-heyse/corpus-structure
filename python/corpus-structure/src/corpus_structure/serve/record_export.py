"""The released record relations inside the existing atomic semantic export."""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, fields
from hashlib import file_digest, sha256
from pathlib import Path
from types import UnionType
from typing import Any, Literal, cast, get_args, get_origin, get_type_hints

import pyarrow as pa
import pyarrow.parquet as pq

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import SnapshotBinding
from corpus_structure.semantic.record_projection import RECORD_ROW_TYPES, read_record_projection
from corpus_structure.semantic.record_queries import CompletedRecordProjection
from corpus_structure.semantic.refusals import WrongBinding
from corpus_structure.serve.record_results import presented_coverage


def write_record_relations(
    projection: CompletedRecordProjection,
    root: Path,
    binding: SnapshotBinding,
    *,
    format: Literal["jsonl", "parquet"],
    include_diagnostics: bool = False,
) -> tuple[dict, dict]:
    """Write already detached rows before their enclosing directory is published.

    Arrow types derive from the same finite public row declarations as the native
    reader. Decimal lexical forms stay strings, including exponent and scale.
    """
    if (
        projection.release_id,
        projection.realization_id,
        projection.data_revision,
    ) != (binding.release_id, binding.realization_id, binding.data_revision):
        raise WrongBinding("record export differs from its captured semantic snapshot")
    relations = {}
    coverage = presented_coverage(projection.coverage, include_diagnostics=include_diagnostics)
    row_relations = cast(Mapping[str, Sequence[Any]], projection.rows)
    arrow_types = {int: pa.int64(), bool: pa.bool_(), str: pa.string()}
    for name, row_type in RECORD_ROW_TYPES.items():
        hints = get_type_hints(row_type)
        schema_fields = []
        for field in fields(row_type):
            annotation = hints[field.name]
            nullable = get_origin(annotation) is UnionType and type(None) in get_args(annotation)
            scalar = (
                next(t for t in get_args(annotation) if t is not type(None))
                if nullable
                else annotation
            )
            schema_fields.append(pa.field(field.name, arrow_types[scalar], nullable=nullable))
        schema = pa.schema(
            schema_fields,
            metadata={
                ("cs." + key).encode(): str(value).encode()
                for key, value in dict(
                    release=binding.release_id,
                    realization=binding.realization_id,
                    data_revision=binding.data_revision,
                    capture=binding.capture_id,
                    relation=name,
                    record_projection=projection.projection_digest,
                    run=projection.run_id,
                    cut=projection.cut_id,
                ).items()
            },
        )
        path = root / (name + "." + format)
        rows = row_relations[name]
        if format == "jsonl":
            with path.open("wb") as stream:
                for row in rows:
                    stream.write(canonical_bytes(asdict(row)) + b"\n")
        else:
            with pq.ParquetWriter(path, schema, store_schema=True) as writer:
                for offset in range(0, len(rows), 1024):
                    writer.write_table(
                        pa.Table.from_pylist(
                            [asdict(row) for row in rows[offset : offset + 1024]], schema=schema
                        )
                    )
        with path.open("rb") as checksum:
            checksum_digest = file_digest(checksum, "sha256").hexdigest()
        relations[name] = dict(
            file=path.name,
            rows=len(rows),
            sha256=checksum_digest,
            arrow_schema=base64.b64encode(schema.serialize().to_pybytes()).decode("ascii"),
        )
    manifest = dict(
        version="source-record-export-1",
        run_id=projection.run_id,
        cut_id=projection.cut_id,
        projection_digest=projection.projection_digest,
        source_view_ids=projection.source_view_ids,
        report_source_view_ids=dict(projection.report_source_view_ids),
        coverage=[asdict(report) for report in coverage],
        include_diagnostics=include_diagnostics,
        released_projection=read_record_projection(projection.prepared),
        semantic_release_manifest=json.loads(projection.prepared.manifest),
        logical_digest=sha256(
            canonical_bytes(
                dict(
                    binding=asdict(projection.binding),
                    projection=projection.projection_digest,
                    rows={
                        name: [asdict(row) for row in rows] for name, rows in row_relations.items()
                    },
                    report_source_view_ids=dict(projection.report_source_view_ids),
                    coverage=[asdict(report) for report in coverage],
                )
            )
        ).hexdigest(),
        exact_values="decimal_lexical preserves original exact decimal/scientific text",
        source_coverage="not_established_by_record_projection",
    )
    return manifest, relations


def export_record_support(ledger, destination: Path) -> dict:
    """Export the same bounded pinned support contract returned by query/CLI/MCP."""
    content = ledger.model_dump_json().encode("utf-8")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        stream.write(content)
    return dict(
        path=str(destination),
        version=ledger.version,
        binding=ledger.page.binding,
        sha256=sha256(content).hexdigest(),
        bytes=len(content),
    )
