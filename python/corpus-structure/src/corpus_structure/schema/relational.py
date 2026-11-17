"""Trusted semantic physical metadata and generated typed SQLAlchemy column surfaces.

Only the captured physical and read-projection models compile to tables. Runtime
candidate schemas remain separate semantic definitions, never physical authority.
"""

from __future__ import annotations

import hashlib
import json
import keyword
from collections.abc import Iterable, Mapping
from typing import Any

from pgvector.sqlalchemy import VECTOR as Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Computed,
    Double,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    MetaData,
    Numeric,
    PrimaryKeyConstraint,
    SmallInteger,
    Table,
    Text,
    UniqueConstraint,
    cast,
    func,
    literal,
    text,
)
from sqlalchemy import column as sql_column
from sqlalchemy.dialects.postgresql import (
    ARRAY,
    BYTEA,
    INT8RANGE,
    JSONB,
    NUMRANGE,
    REAL,
    REGCONFIG,
    TIMESTAMP,
    TSVECTOR,
)
from sqlalchemy.sql.sqltypes import ARRAY as BaseARRAY
from sqlalchemy.types import TypeEngine

from corpus_structure.schema.model import (
    ModelError,
    View,
    ci_annotations,
    expand_enum,
)

MAX_NAME = 63  # PostgreSQL's identifier length

NAMING_CONVENTION: Mapping[str, str] = {
    "pk": "pk_%(table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s",
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "ck": "%(constraint_name)s",  # CHECKs carry their digest name
}


URI_TYPES: Mapping[str, Any] = {
    "xsd:long": BigInteger,
    "xsd:short": SmallInteger,
    "xsd:integer": Integer,
    "xsd:int": Integer,
    "xsd:float": REAL,
    "xsd:double": Double,
    "xsd:boolean": Boolean,
    "xsd:dateTime": lambda: TIMESTAMP(timezone=True),
    "xsd:string": Text,
}


def digest(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()[:10]


def quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def in_check(column: str, members: Iterable[str]) -> str:
    """A closed set's CHECK: `col IN ('a', 'b')`, members sorted (the order carries no meaning)."""
    return f"{column} IN ({', '.join(quote(m) for m in sorted(members))})"


def check_name(table: str, what: str, sql: str) -> str:
    name = f"ck_{table}_{what}_{digest(sql)}"
    if len(name) > MAX_NAME:
        raise ModelError([f"CHECK name {name} exceeds {MAX_NAME} characters"])
    return name


# --- Compilation -------------------------------------------------------------------------------


def compile_metadata(view: View, *, target: str) -> MetaData:
    """Compile one explicitly selected trusted physical or read-projection model."""
    if target not in {"semantic", "semantic-read"}:
        raise ModelError([f"unknown relational target {target!r}"])
    return _compile_physical(view, read_only=target == "semantic-read")


def _compile_physical(view: View, *, read_only: bool = False) -> MetaData:
    expected = "read-projections" if read_only else "physical"
    if str(view.schema.id) != "https://corpus-structure.org/model/semantic/" + expected:
        raise ModelError(["semantic target requires its trusted physical module"])
    if any(
        ci_annotations(enum).get("ph:values_from") is not None for enum in view.all_enums().values()
    ):
        raise ModelError(
            ["referenced physical value sets require compile_physical with captured inputs"]
        )
    md = MetaData(naming_convention=dict(NAMING_CONVENTION))
    # Trusted physical imports may contribute stored relations. Imported payload
    # classes without a physical subset remain boundary types, never tables.
    physical_classes = dict(view.schema.classes)
    if not read_only:
        physical_classes.update(
            {
                name: cls
                for name, cls in view.all_classes().items()
                if name not in physical_classes
                and any(
                    str(subset) in {"sem", "data", "ops", "kb", "eval"} for subset in cls.in_subset
                )
            }
        )
    physical_types = {
        "bytea": BYTEA,
        "jsonb": JSONB,
        "numeric": Numeric,
        "int8range": INT8RANGE,
        "numrange": NUMRANGE,
        "vector": Vector,
        "timestamptz": lambda: TIMESTAMP(timezone=True),
        "tsvector": TSVECTOR,
    }
    nominal = _physical_nominals(view)
    for name, cls in physical_classes.items():
        subsets = [str(s) for s in cls.in_subset]
        if len(subsets) != 1 or subsets[0] not in {"sem", "data", "ops", "kb", "eval"}:
            raise ModelError([f"{name}: physical table needs exactly one trusted physical subset"])
        columns = []
        slots = {str(slot.name): slot for slot in view.class_induced_slots(name)}
        for slot in slots.values():
            rng = str(slot.range or "string")
            declared = view.get_type(rng)
            sql_type = ci_annotations(declared).get("ph:sql_type")
            typ: TypeEngine[Any]
            if sql_type is not None:
                typ = physical_types[str(sql_type)]()
            elif view.get_enum(rng) is not None:
                typ = Text()
            elif rng == "integer":
                typ = BigInteger()
            elif rng == "boolean":
                typ = Boolean()
            elif rng == "string":
                typ = Text()
            elif declared is not None and str(declared.uri) in URI_TYPES:
                typ = URI_TYPES[str(declared.uri)]()
            else:
                raise ModelError([f"{name}.{slot.name}: unsupported physical range {rng}"])
            if slot.multivalued:
                typ = ARRAY(typ)
            annotations = ci_annotations(slot)
            default = annotations.get("ph:default")
            computed = annotations.get("ph:computed")
            search_source = annotations.get("ph:search_vector_source")
            configuration = annotations.get("ph:search_configuration")
            if search_source is not None or configuration is not None:
                location = f"{name}.{slot.name}"
                if (
                    not isinstance(search_source, str)
                    or search_source not in slots
                    or not isinstance(configuration, str)
                    or not configuration
                    or default is not None
                    or computed is not None
                    or annotations.get("ph:identity") is not None
                    or not isinstance(typ, TSVECTOR)
                ):
                    raise ModelError([f"{location}: invalid generated search-vector declaration"])
                source = slots[search_source]
                if source.range != "string" or source.multivalued:
                    raise ModelError(
                        [f"{location}: generated search-vector source must be scalar text"]
                    )
                computed = func.to_tsvector(
                    cast(literal(configuration, Text()), REGCONFIG()),
                    sql_column(search_source, Text()),
                )
            columns.append(
                Column[Any](
                    str(slot.name),
                    typ,
                    *(
                        [Identity(always=True)]
                        if ci_annotations(slot).get("ph:identity") == "true"
                        else [Computed(computed, persisted=True)]
                        if computed is not None
                        else []
                    ),
                    nullable=not slot.required,
                    server_default=text(default) if default is not None else None,
                    info={
                        **nominal(subsets[0], str(name), str(slot.name)),
                        "minimum": slot.minimum_value,
                        "maximum": slot.maximum_value,
                        "pattern": slot.pattern,
                        "enum": (str(slot.equals_string),)
                        if slot.equals_string is not None
                        else tuple(m.text for m in expand_enum(view, rng))
                        if view.get_enum(rng) is not None
                        else (),
                    },
                )
            )
        table_info: dict[str, Any] = {
            "model_class": str(name),
            "immutability": ci_annotations(cls).get("ph:immutability"),
        }
        archive_role = ci_annotations(cls).get("ph:archive_role")
        if archive_role is not None:
            table_info["archive_role"] = str(archive_role)
        # Preserve the model-owned upload/derived boundary through physical inheritance.
        # Downstream PDF wire selection must use this projection, including counterfactuals.
        for ancestor in view.class_ancestors(str(name), reflexive=True):
            boundary_role = ci_annotations(view.get_class(ancestor)).get("pds:record_boundary_role")
            if boundary_role is not None:
                table_info["pdf_record_boundary_role"] = str(boundary_role)
                break
        read_roles = ci_annotations(cls).get("ph:read_roles")
        if read_roles is not None:
            table_info["read_roles"] = json.loads(read_roles)
        table = Table(str(name), md, *columns, schema=subsets[0], info=table_info)
        for slot in view.class_induced_slots(name):
            if slot.equals_string is not None:
                sql = str(slot.name) + " = " + quote(str(slot.equals_string))
                table.append_constraint(
                    CheckConstraint(sql, name=check_name(table.name, str(slot.name), sql))
                )
            if view.get_enum(str(slot.range)) is not None:
                sql = in_check(str(slot.name), (m.text for m in expand_enum(view, str(slot.range))))
                table.append_constraint(
                    CheckConstraint(sql, name=check_name(table.name, str(slot.name), sql))
                )
            for bound, operator in ((slot.minimum_value, ">="), (slot.maximum_value, "<=")):
                if bound is not None:
                    sql = f"{slot.name} {operator} {bound}"
                    table.append_constraint(
                        CheckConstraint(sql, name=check_name(table.name, str(slot.name), sql))
                    )
            if slot.pattern:
                sql = str(slot.name) + " ~ " + quote(str(slot.pattern))
                table.append_constraint(
                    CheckConstraint(sql, name=check_name(table.name, str(slot.name), sql))
                )
        for key_name, key in cls.unique_keys.items():
            constraint = PrimaryKeyConstraint if key_name == "primary_key" else UniqueConstraint
            table.append_constraint(constraint(*map(str, key.unique_key_slots)))
    for name, cls in physical_classes.items():
        schema = str(cls.in_subset[0])
        table = md.tables[f"{schema}.{name}"]
        ann = ci_annotations(cls)
        for fk in json.loads(ann.get("ph:foreign_keys", "[]")):
            target_name, remote = fk["target"].rsplit(".", 1)
            local = fk["columns"]
            target = [f"{target_name}.{col}" for col in remote.split(",")]
            table.append_constraint(
                ForeignKeyConstraint(local, target, info={"shared": tuple(local[:-1])})
            )
        for sql in json.loads(ann.get("ph:checks", "[]")):
            table.append_constraint(
                CheckConstraint(sql, name=check_name(table.name, "physical", sql))
            )
        for declaration in json.loads(ann.get("ph:indexes", "[]")):
            if isinstance(declaration, dict):
                expressions = (
                    (text(declaration["expression"]),)
                    if "expression" in declaration
                    else tuple(
                        table.c[c].collate(declaration["collations"][c])
                        if c in declaration.get("collations", {})
                        else table.c[c]
                        for c in declaration["columns"]
                    )
                )
                index = Index(
                    declaration.get("name"),
                    *expressions,
                    postgresql_where=text(declaration["where"]) if "where" in declaration else None,
                    postgresql_using=declaration.get("using", "btree"),
                    postgresql_include=declaration.get("include"),
                )
                if "expression" in declaration:
                    table.append_constraint(index)
            else:
                Index(None, *(table.c[c] for c in declaration))
    return md


def _physical_nominals(view: View):
    """Resolve explicit scalar identities without consulting an operation catalog."""
    resolved: dict[str, dict[str, str]] = {}
    encodings: dict[str, tuple] = {}

    def field(schema: str, cls: str, name: str, trail: tuple[str, ...] = ()):
        reference = f"physical:{schema}.{cls}.{name}"
        if reference in trail:
            raise ModelError([f"{reference}: cyclic physical type correspondence"])
        if reference in resolved:
            return resolved[reference]
        definition = view.get_class(cls)
        if definition is None or schema not in (definition.in_subset or ()):
            raise ModelError([f"{reference}: physical type source relation is unavailable"])
        slot = next((slot for slot in view.class_induced_slots(cls) if slot.name == name), None)
        if slot is None:
            raise ModelError([f"{reference}: physical type source field is unavailable"])
        annotations = ci_annotations(slot)
        result: dict[str, str] = {}
        if declared := annotations.get("ph:python_type"):
            parts = declared.split(".")
            if len(parts) < 2 or any(
                not part.isidentifier() or keyword.iskeyword(part) for part in parts
            ):
                raise ModelError([f"{reference}: Python nominal requires a qualified identifier"])
            encoding = _physical_encoding(view, slot)
            if (
                encoding[0] not in {"string", "integer"}
                or slot.multivalued
                or view.get_enum(str(slot.range)) is not None
            ):
                raise ModelError([f"{reference}: Python nominal requires one scalar"])
            if declared in encodings and encodings[declared] != encoding:
                raise ModelError([f"{reference}: physical nominal encodings differ"])
            encodings[declared] = encoding
            result["python_type"] = declared
        parent = annotations.get("cp:type_source")
        if parent == reference:
            # A model projection can declare the physical field as its type source.
            # Its inherited backreference does not become a reflexive physical edge.
            ancestors = [
                view.get_class(ancestor) for ancestor in view.class_ancestors(cls, reflexive=True)
            ]

            def declared_edge(definition):
                for declared in (definition.attributes.get(name), definition.slot_usage.get(name)):
                    if declared is not None and (
                        edge := ci_annotations(declared).get("cp:type_source")
                    ):
                        return edge
                if name in (definition.slots or ()):
                    return ci_annotations(view.get_slot(name)).get("cp:type_source")
                return None

            if not any(
                schema in (ancestor.in_subset or ()) and declared_edge(ancestor)
                for ancestor in ancestors
                if ancestor is not None
            ) and any(
                schema not in (ancestor.in_subset or ()) and declared_edge(ancestor) == reference
                for ancestor in ancestors
                if ancestor is not None
            ):
                parent = None
        if parent:
            parts = parent.removeprefix("physical:").split(".")
            if not parent.startswith("physical:") or len(parts) != 3:
                raise ModelError([f"{reference}: physical type source must be qualified"])
            inherited = field(parts[0], parts[1], parts[2], (*trail, reference))
            target = next(
                (slot for slot in view.class_induced_slots(parts[1]) if slot.name == parts[2]), None
            )
            assert target is not None  # validated by recursive source resolution
            if _physical_encoding(view, slot) != _physical_encoding(view, target):
                raise ModelError([f"{reference}: physical type correspondence encoding differs"])
            if result and inherited and result != inherited:
                raise ModelError([f"{reference}: physical nominal identifiers differ"])
            result = result or inherited
        resolved[reference] = result
        return result

    return field


def _physical_encoding(view: View, slot):
    """Compare transport encodings while retaining distinct model-owned identities."""
    name = str(slot.range or "string")
    declared = view.get_type(name)
    sql = ci_annotations(declared).get("ph:sql_type")
    uri = str(declared.uri) if declared is not None else ""
    primitive = sql or {
        "xsd:string": "string",
        "xsd:long": "integer",
        "xsd:integer": "integer",
        "xsd:int": "integer",
        "xsd:boolean": "boolean",
    }.get(uri, name)
    members = (
        tuple(sorted(m.text for m in expand_enum(view, name)))
        if view.get_enum(name) is not None
        else ()
    )
    return primitive, bool(slot.multivalued), members


def column_type_annotation(column: Column[Any]) -> str:
    """Project a checked physical column, preserving nominal, closed and optional types."""
    if isinstance(column.type, TSVECTOR):
        kind = "str"
    elif isinstance(column.type, JSONB):
        kind = "JsonValue"
    elif isinstance(column.type, BaseARRAY):
        item_type = column.type.item_type.python_type
        if item_type is object:
            raise ModelError([f"unsupported typed column {column}"])
        kind = f"list[{item_type.__name__}]"
    else:
        try:
            python_type = column.type.python_type
            if python_type is object:
                raise ModelError([f"unsupported typed column {column}"])
            kind = python_type.__name__
        except NotImplementedError as exc:
            raise ModelError([f"unsupported typed column {column}"]) from exc
    if members := column.info.get("enum"):
        kind = "Literal[" + ", ".join(repr(value) for value in sorted(members)) + "]"
        if isinstance(column.type, BaseARRAY):
            kind = f"list[{kind}]"
    if nominal := column.info.get("python_type"):
        kind = nominal.rsplit(".", 1)[1]
    if column.nullable:
        kind += " | None"
    return kind


def render_typed_column_class(
    name: str, columns: Iterable[Column[Any]], *, bindings: Mapping[str, str] | None = None
) -> str:
    """Render a static SQLAlchemy surface from already compiled model columns.

    Also accepts columns selected for a protected function's return projection; callers
    must supply the model-owned selection, rather than separately authored annotations.
    """
    if not name.isidentifier():
        raise ModelError([f"invalid TypedColumns class name {name!r}"])
    result = [f"class {name}(TypedColumns):"]
    for column in columns:
        if not column.name.isidentifier():
            raise ModelError([f"invalid typed column name {column.name!r}"])
        kind = column_type_annotation(column)
        kind = bindings.get(column.name, kind) if bindings is not None else kind
        result.append(f"    {column.name}: Named[{kind}]")
    if len(result) == 1:
        result.append("    pass")
    return "\n".join(result) + "\n"


def render_typed_column_protocol(
    name: str, columns: Iterable[Column[Any]], *, bindings: Mapping[str, str] | None = None
) -> str:
    """Narrow attribute access without ColumnCollection's dynamic-name fallback."""
    declaration = render_typed_column_class(name, columns, bindings=bindings)
    return declaration.replace("(TypedColumns):", "(Protocol):").replace("Named[", "Column[")


def render_typed_columns(
    metadata: MetaData,
    names: Iterable[str],
    revision: str,
    *,
    bindings: Mapping[str, Mapping[str, str]] | None = None,
    imports: Iterable[str] = (),
    type_model_id: str | None = None,
    identifiers_module: str,
) -> str:
    """Generate declarations and typed views of existing model-owned Core tables."""
    out = [
        '"""Generated model column surfaces; '
        'python -m corpus_structure.semantic.typed_generation."""',
        "",
        "from __future__ import annotations",
        "",
        "from datetime import date, datetime, time",
        "from decimal import Decimal",
        "",
        "from typing import Literal, Protocol, cast",
        "",
        "from pydantic import JsonValue",
        "from sqlalchemy import Column, Named, TypedColumns",
        "",
        "from .metadata import table",
        "",
        *(f"from {identifiers_module} import {name} as {name}" for name in sorted(imports)),
        f"PHYSICAL_MODEL_ID = {revision!r}",
        f"TYPE_MODEL_ID = {type_model_id!r}",
    ]
    for fullname in names:
        source = metadata.tables[fullname]
        variable = fullname.replace(".", "_")
        class_name = "".join(part.title() for part in variable.split("_")) + "Columns"
        out += [
            "",
            "",
            render_typed_column_class(
                class_name, source.columns, bindings=(bindings or {}).get(fullname)
            ).rstrip(),
            "",
            "",
            render_typed_column_protocol(
                class_name + "Set", source.columns, bindings=(bindings or {}).get(fullname)
            ).rstrip(),
            "",
            "",
            f"{variable} = table({fullname!r}).with_cols({class_name})",
            f"{variable}_columns = cast({class_name}Set, {variable}.c)",
        ]
    return "\n".join(out) + "\n"
