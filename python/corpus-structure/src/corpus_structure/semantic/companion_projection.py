"""Model-owned protected companion return shapes and their directional Arrow contract."""

from __future__ import annotations

import ast as python_ast
from dataclasses import dataclass
from functools import cached_property, lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Any

import pyarrow as pa
from linkml_runtime.utils.schemaview import SchemaView
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Double,
    Integer,
    String,
    Text,
    TypedColumns,
    bindparam,
    column,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.schema.model import ci_annotations
from corpus_structure.schema.relational import render_typed_column_class

from .metadata import PHYSICAL_MODEL_ID, metadata, physical_model_id

MODEL = Path(__file__).resolve().parents[1] / "model/semantic/companion-projections.yaml"
FAMILIES = ("input", "relation", "coverage", "mapping_report")
PIN_FIELDS = ("project_id", "run_id", "release_id", "task_id", "product_key", "content_digest")
PROJECTION_ID = (
    "pdf-companion-projection-v1:"
    + sha256((physical_model_id(MODEL) + PHYSICAL_MODEL_ID).encode()).hexdigest()
)


@dataclass(frozen=True)
class CompanionProjection:
    family: str
    function_name: str
    class_name: str
    columns: tuple[Column[Any], ...]
    expressions: tuple[str, ...]
    arrow_schema: pa.Schema
    keys: tuple[str, ...]
    projection_id: str = PROJECTION_ID

    @cached_property
    def statement(self):
        columns = {item.name: item for item in self.columns}
        function = func
        for part in self.function_name.split("."):
            function = getattr(function, part)
        relation = (
            function(*(bindparam(name, type_=columns[name].type) for name in PIN_FIELDS))
            .table_valued(*(column(item.name, item.type) for item in self.columns))
            .with_cols(self.typed_columns)
        )
        return select(relation).order_by(
            *(
                relation.c[key].collate("C")
                if isinstance(relation.c[key].type, String)
                else relation.c[key]
                for key in self.keys
            )
        )

    @property
    def typed_columns(self) -> type[TypedColumns]:
        from . import _companion_columns

        return getattr(_companion_columns, self.class_name)


def _source(view, reference):
    if reference.startswith("physical:"):
        relation, field = reference.removeprefix("physical:").rsplit(".", 1)
        original = metadata.tables[relation].c[field]
        return original.type, not original.nullable, dict(original.info)
    cls, name = reference.split(".")
    slot = next(item for item in view.class_induced_slots(cls) if item.name == name)
    kind = str(slot.range)
    enum = view.get_enum(kind)
    info = {"source": reference}
    if enum is not None:
        typ = Text()
        info["enum"] = sorted(str(value) for value in enum.permissible_values)
    elif slot.multivalued or view.get_class(kind) is not None:
        typ = JSONB()
    else:
        declared = view.get_type(kind)
        uri = str(declared.uri) if declared is not None else ""
        types = {
            "xsd:string": Text,
            "xsd:integer": Integer,
            "xsd:long": BigInteger,
            "xsd:double": Double,
            "xsd:boolean": Boolean,
        }
        if kind == "string":
            typ = Text()
        elif uri in types:
            typ = types[uri]()
        else:
            raise ValueError(f"unsupported companion projection range {kind}: {reference}")
    return typ, bool(slot.required), info


@lru_cache(maxsize=4)
def projection(family: str) -> CompanionProjection:
    if family not in FAMILIES:
        raise ValueError(f"unsupported companion projection family {family}")
    view = SchemaView(str(MODEL))
    schema = view.schema
    if schema is None:
        raise ValueError("companion projection requires its declared schema")
    name, cls = next(
        (name, cls)
        for name, cls in view.all_classes(imports=False).items()
        if ci_annotations(cls).get("cp:family") == family
    )
    columns, expressions, fields = [], [], []
    for slot in view.class_induced_slots(name):
        annotations = ci_annotations(slot)
        typ, required, info = _source(view, annotations["cp:source"])
        column = Column(str(slot.name), typ, nullable=not required, info=info)
        columns.append(column)
        expressions.append(annotations["cp:sql"].replace("{projection_id}", PROJECTION_ID))
        if isinstance(typ, JSONB):
            arrow, wire = pa.json_(), "jsonb:utf8"
        elif isinstance(typ, BigInteger):
            arrow, wire = pa.int64(), "bigint"
        elif isinstance(typ, Integer):
            arrow, wire = pa.int32(), "integer"
        elif isinstance(typ, Double):
            arrow, wire = pa.float64(), "double precision"
        elif isinstance(typ, Boolean):
            arrow, wire = pa.bool_(), "boolean"
        else:
            arrow, wire = pa.string(), "text"
        fields.append(
            pa.field(
                column.name,
                arrow,
                nullable=column.nullable,
                metadata={"postgresql": wire, "source": annotations["cp:source"]},
            )
        )
    return CompanionProjection(
        family,
        ci_annotations(cls)["cp:function"],
        str(name),
        tuple(columns),
        tuple(expressions),
        pa.schema(fields, metadata={"projection_id": PROJECTION_ID, "family": family}),
        tuple(python_ast.literal_eval(ci_annotations(cls)["cp:keys"])),
    )


def render_static_columns() -> str:
    return (
        "# Generated from model/semantic/companion-projections.yaml.\n"
        "from pydantic import JsonValue\nfrom sqlalchemy import Named, TypedColumns\n\n\n"
        + "\n\n".join(
            render_typed_column_class(
                projection(family).class_name, projection(family).columns
            ).rstrip()
            for family in FAMILIES
        )
        + "\n"
    )
