"""Finite model-derived Arrow candidate for the annotation-fork comparison.

The caller owns admission and exact selected-use authority. This module supplies no
publication or read authority and deliberately keeps the ordinary canonical encoder.
"""

import json
from dataclasses import dataclass

import duckdb
import pyarrow as pa

from corpus_structure import analytics
from corpus_structure.semantic.data_operation_values import decode_semantic_value, semantic_value
from corpus_structure.semantic.data_product_reference import SemanticReference


@dataclass(frozen=True)
class ArrowProjection:
    fingerprint: str
    header: dict
    partitions: tuple[dict, ...]
    fields: tuple[str, ...]
    table: pa.Table


def _scalar_type(prop):
    types = {"string": pa.string(), "integer": pa.int64(), "boolean": pa.bool_()}
    if prop.range not in types:
        raise ValueError("pilot does not silently coerce unsupported field " + prop.name)
    typ = types[prop.range]
    return pa.list_(typ) if prop.multivalued else typ


def projection_schema(profile):
    """Derive columns from the compiled selected role and induced model slots."""
    (role,) = [role for role in profile.operation.roles if role.direction == "input"]
    kind = next(kind for kind in profile.model.kinds if kind.semantic_id == role.kind)
    slots = profile.prepared.index.definitions[kind.name].properties
    collection = next(prop for prop in slots if prop.name == "rows")
    properties = {
        prop.name: prop for prop in profile.prepared.index.definitions[collection.range].properties
    }
    layouts = json.loads(profile.input_layouts)
    (selection,) = profile.input_projection.collections
    if selection.name != "rows" or not all(
        (selection.membership, selection.order, selection.placement)
    ):
        raise ValueError("pilot requires the canonical declared ordered placed population")
    names = tuple(
        sorted(
            {
                path
                for group in selection.groups
                for path in layouts[selection.name]["field_groups"][group]
            }
        )
    )
    fields = [
        pa.field("_partition_key", pa.string(), nullable=False),
        pa.field("_row_index", pa.int64(), nullable=False),
    ]
    for name in names:
        if "." in name:
            raise ValueError("pilot requires its declared flat annotation geometry")
        fields.extend(
            (
                pa.field(name, _scalar_type(properties[name])),
                pa.field("_present_" + name, pa.bool_(), nullable=False),
            )
        )
    return names, pa.schema(
        fields, metadata={b"read_projection": profile.input_projection.fingerprint.encode()}
    )


def project_annotation_rows(profile, header, packets):
    """Read admitted logical rows once without rebuilding their tagged projection."""
    names, schema = projection_schema(profile)
    selected_header = {
        name: header[name] for name in profile.input_projection.header if name in header
    }
    metadata = []
    rows = []
    for packet in sorted(packets, key=lambda packet: packet["ordinal"]):
        metadata.append({name: packet[name] for name in ("partition_key", "ordinal", "placement")})
        for index, source in enumerate(decode_semantic_value(packet["body"])):
            row = {"_partition_key": packet["partition_key"], "_row_index": index}
            for name in names:
                row[name] = source.get(name)
                row["_present_" + name] = name in source
            rows.append(row)
    table = pa.Table.from_pylist(rows, schema=schema)
    table.validate(full=True)
    return ArrowProjection(
        profile.input_projection.fingerprint, selected_header, tuple(metadata), names, table
    )


def canonical_values(projected, projection_spec):
    """Assemble canonical publication once from the admitted columnar population."""
    from corpus_structure.semantic.characterization_manifests import append_manifest
    from corpus_structure.semantic.data_operation_identity import canonical_identity

    coverage = [
        row for row in projected.header["coverage"] if row["family"] in projection_spec["families"]
    ]
    header = {name: projected.header[name] for name in ("source", "selectors", "block_coverage")}
    header.update(
        coverage=coverage,
        outcome="complete"
        if all(row["outcome"] in {"complete", "empty"} for row in coverage)
        else "partial",
    )
    by_partition = {part["partition_key"]: [] for part in projected.partitions}
    for physical in projected.table.to_pylist():
        row = {name: physical[name] for name in projected.fields if physical["_present_" + name]}
        key = physical["_partition_key"]
        row["annotation"] = SemanticReference.item(
            "inventory", "rows", key, (row["record_type"], row["ordinal"]), occurrence=None
        ).values()
        by_partition[key].append(row)
    packets = []
    for part in projected.partitions:
        rows = by_partition[part["partition_key"]]
        packets.append(
            {
                "collection": "rows",
                **part,
                "body": semantic_value(rows),
                "partition_digest": canonical_identity("partition", rows).key,
            }
        )
    return {
        "header": append_manifest(header, projection_spec["manifest_contract"]),
        "partitions": packets,
    }


def missing_annotation_items(projected, references):
    """One set query over the admitted projection replaces per-reference membership."""
    schema = pa.schema(
        [
            pa.field("wanted_partition", pa.string(), nullable=False),
            pa.field("wanted_type", pa.string(), nullable=False),
            pa.field("wanted_ordinal", pa.int64(), nullable=False),
            pa.field("wanted_position", pa.int64(), nullable=False),
        ]
    )
    wanted = pa.Table.from_pylist(
        [
            dict(
                wanted_partition=key,
                wanted_type=kind,
                wanted_ordinal=ordinal,
                wanted_position=index,
            )
            for index, (key, kind, ordinal) in enumerate(references)
        ],
        schema=schema,
    )
    col = duckdb.ColumnExpression
    with analytics.connection() as connection:
        missing = (
            connection.from_arrow(wanted)
            .join(
                connection.from_arrow(projected.table),
                (col("wanted_partition") == col("_partition_key"))
                & (col("wanted_type") == col("record_type"))
                & (col("wanted_ordinal") == col("ordinal")),
                how="anti",
            )
            .sort(col("wanted_position").asc().nulls_last())
        )
        return tuple((key, kind, ordinal) for key, kind, ordinal, _ in missing.fetchall())
