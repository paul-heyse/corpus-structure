"""Fixed native call correspondence records shared by current generators.

These immutable transport descriptions carry no operation admission, effect or
legacy execution-catalog authority. Semantic meaning belongs to effective DDO
contracts; each native call remains bound to its captured schema and source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class OperationFieldType:
    kind: str
    nullable: bool
    multivalued: bool
    enum_values: tuple[str, ...] = ()
    model_class: str | None = None


@dataclass(frozen=True)
class OperationFieldBinding:
    name: str
    source: str
    nullable: bool
    native_parameter: str | None = None
    native_field: str | None = None
    native_type: Literal["integer"] | None = None
    multivalued: bool = False
    semantic_type: str | None = None
    default_json: str | None = None
    transform: Literal["identity", "task_unit_type", "held_progress"] | None = None
    resolved: OperationFieldType | None = None
    # Explicit schema-backed lowering; the physical transport remains json_payload.
    wire_schema: str | None = None
    wire_nominals: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class OperationRecordBinding:
    name: str
    fields: tuple[OperationFieldBinding, ...]


@dataclass(frozen=True)
class OperationCallBinding:
    id: str
    symbol: str
    parameters: tuple[OperationFieldBinding, ...]
    result_class: str | None = field(default=None, kw_only=True)
    result_fields: tuple[OperationFieldBinding, ...]
    cardinality: Literal["many", "one", "optional", "none"]
    ordered: bool
    source_digest: str | None = None
    result_mode: Literal["table", "scalar", "void", "json"] = "table"
    result_source: str | None = None
    requires_context: bool = False
    order_by: tuple[str, ...] = ()
    records: tuple[OperationRecordBinding, ...] = ()
    batch: bool = False
    json_read: Literal["native", "json-text-v1"] = "native"
    backend: Literal["native", "core"] = "native"


