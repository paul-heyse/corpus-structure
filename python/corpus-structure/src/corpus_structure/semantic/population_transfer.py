"""Directional upload shape for privately prepared population item intake.

The caller owns intake authentication and transaction lifetime. Native admission
supplies the attempt and derives addresses and rule projections from canonical items.
"""

from __future__ import annotations

import pyarrow as pa
from sqlalchemy import Integer, MetaData, Text
from sqlalchemy.dialects.postgresql import dialect

from .arrow_transfer import ArrowWriteProfile
from .arrow_types import sql_arrow_type
from .metadata import get_metadata

_ITEM_RELATION = "ops.data_retained_population_item"
_UPLOAD_FIELDS = (
    "output_role",
    "output_position",
    "collection",
    "partition_key",
    "item_ordinal",
    "canonical_text",
)


def population_item_write_profile(
    *, release_id: str, model: MetaData | None = None
) -> ArrowWriteProfile:
    """Prepare only submitted item values against their compiled physical columns.

    The native preparation call binds the upload to its actual context. This profile
    accepts no claim, intent, product identity or caller-provided projection evidence.
    Each transfer creates its own pgpq encoder through the shared write profile.
    """
    selected = get_metadata() if model is None else model
    relation = selected.tables[_ITEM_RELATION]
    fields = []
    wire_types = []
    for name in _UPLOAD_FIELDS:
        column = relation.c[name]
        if not isinstance(column.type, (Text, Integer)):
            raise ValueError(f"unsupported population upload field {column}: {column.type}")
        wire = str(column.type.compile(dialect=dialect())).lower()
        fields.append(pa.field(column.name, sql_arrow_type(column.type), nullable=column.nullable))
        wire_types.append(wire)
    schema = pa.schema(
        fields,
        metadata={
            "source_relation": _ITEM_RELATION,
            "physical_model_id": selected.info["physical_model_id"],
            "release_id": release_id,
        },
    )
    return ArrowWriteProfile.prepare(
        release_id=release_id,
        physical_id=selected.info["physical_model_id"],
        operation="private-population-items",
        schema=schema,
        wire_types=wire_types,
    )
