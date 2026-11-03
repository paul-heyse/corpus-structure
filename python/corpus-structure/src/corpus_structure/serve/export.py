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
        manifest["format"] = "semantic-export-4"
        manifest["logical_digest_scope"] = "captured_semantic_spine"
        manifest["ordinary_answer_contract"] = "ordinary-answer-coverage-2"
        manifest["source_payloads"] = "excluded; explicit immutable report reads required"
        manifest["relations"]["fact_standing_v2"] = _write_fact_standing(packet, root, format)
        (root / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        root.rename(destination)
    return manifest


def _write_fact_standing(packet, root, format):
    """A versioned derived relation; captured physical relations remain its authority."""
    from corpus_structure.semantic.analytics import AnalysisScope

    sql = """
        WITH assessed AS (
            SELECT fact_id, assessment_id, operation_id, operation_version, outcome,
                context_value_id
            FROM assessment WHERE fact_id IS NOT NULL
            UNION
            SELECT o.fact_id, a.assessment_id, a.operation_id, a.operation_version, a.outcome,
                a.context_value_id
            FROM assessment a JOIN occurrence o ON a.occurrence_id = o.occurrence_id
        ), ranked_assessments AS (
            SELECT *, count(*) OVER(PARTITION BY fact_id) AS population,
                row_number() OVER(PARTITION BY fact_id ORDER BY assessment_id) AS reference_rank
            FROM assessed
        ), assessments AS (
            SELECT fact_id, max(population) AS population,
                list(struct_pack(assessment_id := assessment_id, operation_id := operation_id,
                    operation_version := operation_version, outcome := outcome,
                    context_value_id := context_value_id) ORDER BY assessment_id) FILTER(WHERE
                        reference_rank <= 8) AS refs
            FROM ranked_assessments GROUP BY fact_id
        ), established AS (
            SELECT o.fact_id, o.occurrence_id AS reference_id, e.establishment AS kind, 'supports'
                AS collection
            FROM occurrence o JOIN occurrence_establishment e USING(occurrence_id)
            UNION ALL
            SELECT conclusion_fact_id AS fact_id, derivation_id AS reference_id,
                'inference' AS kind, 'derivations' AS collection FROM derivation
        ), ranked_establishments AS (
            SELECT *, count(*) OVER(PARTITION BY fact_id) AS population,
                row_number() OVER(PARTITION BY fact_id ORDER BY collection, reference_id) AS
                    reference_rank
            FROM established
        ), establishments AS (
            SELECT fact_id, max(population) AS population,
                list(struct_pack(reference_id := reference_id, kind := kind,
                    collection := collection) ORDER BY collection, reference_id) FILTER(WHERE
                        reference_rank <= 8) AS refs
            FROM ranked_establishments GROUP BY fact_id
        )
        SELECT f.fact_id, f.release_id, f.realization_id,
            CASE WHEN s.fact_id IS NULL THEN 'not_selected' ELSE 'selected' END AS selection,
            CASE WHEN s.fact_id IS NULL THEN [] ELSE [s.fact_id] END AS selection_references,
            struct_pack(collection := 'assessments', count := coalesce(a.population, 0),
                availability := CASE WHEN a.population IS NULL THEN 'unassessed' ELSE 'available'
                    END,
                "references" := coalesce(a.refs, []), population_complete := coalesce(a.population,
                    0) <= 8) AS assessments,
            struct_pack(collection := 'establishments', count := coalesce(e.population, 0),
                availability := CASE WHEN e.population IS NULL THEN 'unavailable' ELSE 'available'
                    END,
                "references" := coalesce(e.refs, []), population_complete := coalesce(e.population,
                    0) <= 8) AS establishments
        FROM fact f LEFT JOIN selection s USING(fact_id)
        LEFT JOIN assessments a USING(fact_id) LEFT JOIN establishments e USING(fact_id)
        ORDER BY f.fact_id
    """
    name = "fact_standing_v2"
    path = root / (name + "." + format)
    metadata = {
        b"cs.contract": b"ordinary-answer-coverage-2",
        b"cs.binding": json.dumps(asdict(packet.binding), sort_keys=True).encode("utf-8"),
        b"cs.derivation": b"selection-assessment-establishment-2",
    }
    with (
        AnalysisScope(packet) as scope,
        scope.reader(scope.connection.sql(sql), batch_size=1024) as reader,
    ):
        schema = reader.schema.with_metadata(metadata)
        logical = LogicalRows(schema)
        count = 0
        if format == "parquet":
            with pq.ParquetWriter(path, schema, store_schema=True) as writer:
                for batch in reader:
                    batch = batch.replace_schema_metadata(metadata)
                    logical.write(batch)
                    count += batch.num_rows
                    writer.write_batch(batch)
        else:
            with path.open("w", encoding="utf-8") as stream:
                for batch in reader:
                    logical.write(batch)
                    count += batch.num_rows
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
        checksum_digest = file_digest(checksum, "sha256").hexdigest()
    return {
        "file": path.name,
        "rows": count,
        "logical_digest": logical.digest,
        "sha256": checksum_digest,
        "arrow_schema": base64.b64encode(schema.serialize().to_pybytes()).decode("ascii"),
        "derived_contract": "ordinary-answer-coverage-2",
        "source_relations": [
            "fact",
            "selection",
            "assessment",
            "occurrence",
            "occurrence_establishment",
            "derivation",
        ],
        "population_complete": True,
        "inline_reference_limit": 8,
        "detail_population": (
            "complete captured source_relations; inline references explicitly report completeness"
        ),
    }
