"""Private PDF record representations compiled from the trusted model.

These are foundation schemas, not a publication or staging API. Field order, types
and nullability come from the shared physical projection, including inherited
record declarations. JSON uses a declared UTF-8 wire representation in Arrow.
"""

from __future__ import annotations

import json
from decimal import Decimal
from functools import lru_cache
from typing import Annotated, Any, Literal

import pyarrow as pa
from pydantic import ConfigDict, Field, JsonValue, TypeAdapter, create_model
from sqlalchemy import BigInteger, Boolean, Integer, MetaData, Numeric, Text
from sqlalchemy.dialects.postgresql import BYTEA, JSONB

from .arrow_transfer import ArrowWriteProfile
from .metadata import get_metadata


def _record_tables(model: MetaData | None, *, derived: bool | None):
    selected = get_metadata() if model is None else model
    return {
        name: table
        for name, table in selected.tables.items()
        if (table.name.startswith("pdf_record_") or table.name.startswith("pdf_artifact_"))
        and (
            derived is None
            or (table.info.get("pdf_record_boundary_role") == "derived_core") == derived
        )
    }


def record_tables(model: MetaData | None = None):
    """Select every private record relation for native custody and privilege management."""
    return _record_tables(model, derived=None)


def record_upload_tables(model: MetaData | None = None):
    """Select upload/wire records; derived query projections use SQLAlchemy Core."""
    return _record_tables(model, derived=False)


def derived_record_tables(model: MetaData | None = None):
    """Select model-declared projections without inventing a bounded Arrow numeric type."""
    return _record_tables(model, derived=True)


def _types(column):
    if isinstance(column.type, Text):
        return str, pa.string(), "text"
    if isinstance(column.type, BigInteger):
        return int, pa.int64(), "bigint"
    if isinstance(column.type, Integer):
        return int, pa.int32(), "integer"
    if isinstance(column.type, Boolean):
        return bool, pa.bool_(), "boolean"
    if isinstance(column.type, BYTEA):
        return bytes, pa.binary(), "bytea"
    if isinstance(column.type, JSONB):
        return JsonValue, pa.string(), "jsonb:utf8"
    raise ValueError(f"unsupported PDF record field {column}: {column.type}")


@lru_cache(maxsize=32)
def artifact_part_upload_table(model: MetaData | None = None):
    """Compile the declared part wire shape without installing a part table."""
    import yaml

    from corpus_structure.schema.physical import compile_physical

    selected = get_metadata() if model is None else model
    sources = dict(selected.info["physical_sources"])
    root = yaml.safe_load(sources["physical.yaml"])
    owner = yaml.safe_load(sources["pdf-records.yaml"])["classes"]["PdfArtifactPart"]["annotations"]
    root["classes"]["pdf_stage_artifact_part"] = {
        "is_a": "PdfArtifactPart",
        "in_subset": ["ops"],
        "unique_keys": {"primary_key": {"unique_key_slots": json.loads(owner["pds:upload_key"])}},
        "annotations": {
            "ph:checks": {"tag": "ph:checks", "value": json.loads(owner["pds:upload_checks"])}
        },
    }
    sources["physical.yaml"] = yaml.safe_dump(root, sort_keys=False).encode()
    overlay = compile_physical(sources, linkml_types=selected.info["physical_linkml_types"])
    # The overlay is a compilation device, not another installed physical model.
    # Its wire fields/checks derive from this exact supplied source population.
    overlay.info.update(selected.info)
    overlay.info["pdf_upload_only"] = True
    return overlay.tables["ops.pdf_stage_artifact_part"]


def record_upload_table(name: str, model: MetaData | None = None):
    selected = get_metadata() if model is None else model
    return (
        artifact_part_upload_table(selected)
        if name == "ops.pdf_stage_artifact_part"
        else selected.tables[name]
    )


def record_arrow_schema(name: str, *, model: MetaData | None = None) -> pa.Schema:
    selected = get_metadata() if model is None else model
    table = record_upload_table(name, selected)
    if table.info.get("pdf_record_boundary_role") == "derived_core":
        raise ValueError(f"derived PDF record projection {name} uses the SQLAlchemy Core boundary")
    return pa.schema(
        [
            pa.field(
                column.name,
                _types(column)[1],
                nullable=column.nullable,
                metadata={
                    "postgresql": _types(column)[2],
                    "constraints": json.dumps(column.info, sort_keys=True),
                },
            )
            for column in table.columns
        ],
        metadata={"relation": name, "physical_model_id": selected.info["physical_model_id"]},
    )


def record_boundary_adapter(name: str, *, model: MetaData | None = None) -> TypeAdapter[Any]:
    table = record_upload_table(name, model)
    fields: dict[str, Any] = {}
    literal_factory: Any = Literal
    for column in table.columns:
        kind: Any = Decimal if isinstance(column.type, Numeric) else _types(column)[0]
        if column.info.get("enum"):
            kind = literal_factory[column.info["enum"]]
        kind = Annotated[
            kind,
            Field(
                ge=column.info.get("minimum"),
                le=column.info.get("maximum"),
                pattern=column.info.get("pattern"),
            ),
        ]
        fields[column.name] = (kind | None, None) if column.nullable else (kind, ...)
    boundary = create_model(
        "PdfRecord_" + table.name,
        __config__=ConfigDict(strict=True, extra="forbid"),
        **fields,
    )
    return TypeAdapter(boundary)


def record_write_profile(
    name: str, *, release_id: str, model: MetaData | None = None
) -> ArrowWriteProfile:
    """Derive private write fields and wire types from the same physical projection."""
    if model is None:
        return _default_write_profile(name, release_id)
    return _write_profile(name, release_id, model)


@lru_cache(maxsize=128)
def _default_write_profile(name: str, release_id: str) -> ArrowWriteProfile:
    return _write_profile(name, release_id, get_metadata())


def _write_profile(name: str, release_id: str, selected: MetaData) -> ArrowWriteProfile:
    return ArrowWriteProfile.prepare(
        release_id=release_id,
        physical_id=selected.info["physical_model_id"],
        operation="private-pdf:" + name,
        schema=record_arrow_schema(name, model=selected),
        wire_types=tuple(
            _types(c)[2].removesuffix(":utf8") for c in record_upload_table(name, selected).columns
        ),
    )
