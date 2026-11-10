"""Model-owned protected companion return shapes and their directional Arrow contract."""

from __future__ import annotations

import ast as python_ast
import json
import re
from dataclasses import dataclass
from dataclasses import field as dataclass_field
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
    MetaData,
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

from .projection_recipe import (
    Field,
    HelperDefinition,
    Join,
    JoinKey,
    Order,
    OutputField,
    ParameterDefinition,
    ProjectionRecipe,
    SourceDefinition,
    SourceReference,
    core_statement,
    expression_fields,
    expression_type,
    mapping,
    read_expression,
    refuse,
    shape,
)
from .types import PreparationError

MODEL = Path(__file__).resolve().parents[1] / "model/semantic/companion-projections.yaml"
FAMILIES = ("input", "relation", "coverage", "mapping_report")
PIN_FIELDS = (
    "project_id",
    "run_id",
    "selection_release_id",
    "task_id",
    "product_key",
    "content_digest",
)
RECIPE_VERSION = "pdf-companion-projection-v3"
JSON_MATERIALIZATION = {"python": "jsonb-text-v1", "arrow": "jsonb-arrow-json-v1"}


@lru_cache(maxsize=1)
def installed_projection_id() -> str:
    from .metadata import PHYSICAL_MODEL_ID, physical_model_id

    return (
        RECIPE_VERSION
        + ":"
        + sha256((physical_model_id(MODEL) + PHYSICAL_MODEL_ID).encode()).hexdigest()
    )


@dataclass(frozen=True)
class CompanionProjection:
    family: str
    function_name: str
    class_name: str
    columns: tuple[Column[Any], ...]
    recipe: ProjectionRecipe
    arrow_schema: pa.Schema
    keys: tuple[str, ...]
    _physical: MetaData = dataclass_field(repr=False, compare=False)
    projection_id: str

    @cached_property
    def body_statement(self):
        return core_statement(self.recipe, self._physical)

    @cached_property
    def _native_relation(self):
        columns = {item.name: item for item in self.columns}
        function = func
        for part in self.function_name.split("."):
            function = getattr(function, part)
        return function(
            *(bindparam(name, type_=columns[name].type) for name in PIN_FIELDS)
        ).table_valued(*(column(item.name, item.type) for item in self.columns))

    def _ordered(self, relation):
        return select(relation).order_by(
            *(
                relation.c[order.field].collate(order.collation)
                if order.collation
                else relation.c[order.field]
                for order in self.recipe.order
            )
        )

    @cached_property
    def statement(self):
        """Python materialization preserves SQL NULL versus JSON null as None versus 'null'."""
        fields = [
            self._native_relation.c[item.name].cast(Text()).label(item.name)
            if isinstance(item.type, JSONB)
            else self._native_relation.c[item.name]
            for item in self.columns
        ]
        relation = select(*fields).subquery().with_cols(self.typed_columns)
        return self._ordered(relation)

    @cached_property
    def arrow_statement(self):
        """Retain JSONB OIDs so ADBC carries JSON text and its independent Arrow null bitmap."""
        return self._ordered(self._native_relation)

    @cached_property
    def materialized_columns(self):
        return tuple(
            Column(
                item.name,
                Text() if isinstance(item.type, JSONB) else item.type,
                nullable=item.nullable,
                info=dict(item.info),
            )
            for item in self.columns
        )

    @property
    def typed_columns(self) -> type[TypedColumns]:
        from . import _companion_columns

        return getattr(_companion_columns, self.class_name)


def _source(view, reference, physical):
    if not isinstance(reference, str):
        refuse("companion-projections.source", "source reference must be text")
    if reference.startswith("physical:"):
        relation, field = reference.removeprefix("physical:").rsplit(".", 1)
        original = physical.tables[relation].c[field]
        return original.type, not original.nullable, dict(original.info)
    cls, name = reference.split(".")
    slot = next(item for item in view.class_induced_slots(cls) if item.name == name)
    kind = str(slot.range)
    enum = view.get_enum(kind)
    info: dict[str, Any] = {"source": reference}
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
    return (
        typ,
        bool(
            slot.required or slot.value_presence == "PRESENT" or (slot.minimum_cardinality or 0) > 0
        ),
        info,
    )


def _json_annotation(annotations, name, path):
    try:
        return json.loads(annotations[name])
    except (KeyError, TypeError, ValueError) as error:
        return refuse(path, f"missing/invalid {name}: {error}")


def _name(value, path):
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", value) is None:
        refuse(path, "invalid declared identifier")
    return value


def _reference(value, path):
    value = shape(value, path, {"name", "alias"})
    return SourceReference(_name(value["name"], path), _name(value["alias"], path))


def _recipe(view, family, cls, fields, keys, projection_id, physical):
    path = "companion-projections." + str(cls.name)
    root = ci_annotations(view.schema)
    parameters = []
    for index, raw in enumerate(_json_annotation(root, "cp:parameters", path)):
        location = path + f".parameters.{index}"
        raw = shape(raw, location, {"name", "native_name", "source"})
        typ, required, _ = _source(view, raw["source"], physical)
        parameters.append(
            ParameterDefinition(
                _name(raw["name"], location),
                _name(raw["native_name"], location),
                raw["source"],
                typ,
                not required,
            )
        )
    if tuple(p.name for p in parameters) != PIN_FIELDS or len(
        {p.native_name for p in parameters}
    ) != len(parameters):
        refuse(path, "public parameter layout differs from the declared six-part pin")
    helpers = []
    for raw in _json_annotation(root, "cp:helpers", path):
        raw = shape(raw, path, {"name", "function", "arguments", "result_source"})
        if raw["function"] != "ops.pdf_companion_body":
            refuse(path, "helper has no admitted companion implementation")
        helpers.append(
            HelperDefinition(
                _name(raw["name"], path),
                raw["function"],
                tuple(raw["arguments"]),
                raw["result_source"],
                tuple(_source(view, name, physical)[0] for name in raw["arguments"]),
                _source(view, raw["result_source"], physical)[0],
            )
        )
    if len({h.name for h in helpers}) != len(helpers):
        refuse(path, "duplicate helper declaration")
    parameter_index = {p.name: p for p in parameters}
    helper_index = {h.name: h for h in helpers}
    sources = []
    available = {}

    def check(expression, aliases, location):
        return expression_type(expression, aliases, parameter_index, helper_index, location)

    for raw in _json_annotation(root, "cp:sources", path):
        raw = mapping(raw, path)
        name = _name(raw.get("name"), path)
        if name in available:
            refuse(path, "duplicate source: " + name)
        if "relation" in raw:
            raw = shape(raw, path, {"name", "relation"})
            if raw["relation"] not in physical.tables:
                refuse(path, "unknown physical source: " + str(raw["relation"]))
            table = physical.tables[raw["relation"]]
            source_fields = tuple(
                OutputField(
                    c.name,
                    Field(name, c.name),
                    "physical:" + table.fullname + "." + c.name,
                    "source",
                    c.type,
                    c.nullable,
                )
                for c in table.c
            )
            source = SourceDefinition(name, table.fullname, None, source_fields)
        else:
            raw = shape(raw, path, {"name", "input", "fields", "predicate", "materialized"})
            reference = _reference(raw["input"], path)
            if reference.name not in available:
                refuse(
                    path,
                    "derived source must reference an earlier source; "
                    "cycles/forward references are unsupported",
                )
            if type(raw["materialized"]) is not bool:
                refuse(path, "materialization must be an explicit Boolean")
            aliases = {reference.alias: available[reference.name]}
            source_fields = []
            for item in raw["fields"]:
                item = shape(item, path, {"name", "source", "expression"})
                typ, required, _ = _source(view, item["source"], physical)
                expression = read_expression(item["expression"], path + ".sources." + name)
                actual = check(expression, aliases, path)
                if actual._type_affinity is not typ._type_affinity:
                    refuse(path, "derived field type differs from its declared source")
                source_fields.append(
                    OutputField(
                        _name(item["name"], path),
                        expression,
                        item["source"],
                        "source",
                        typ,
                        not required,
                    )
                )
            predicate = read_expression(raw["predicate"], path)
            if not isinstance(check(predicate, aliases, path), Boolean):
                refuse(path, "source filter is not Boolean")
            source = SourceDefinition(
                name, None, reference, tuple(source_fields), predicate, raw["materialized"]
            )
        if len({f.name for f in source.fields}) != len(source.fields):
            refuse(path, "duplicate source output field")
        available[name] = {f.name: f.sql_type for f in source.fields}
        sources.append(source)
    body = shape(
        _json_annotation(ci_annotations(cls), "cp:recipe", path),
        path,
        {"source", "families", "joins", "predicate"},
    )
    source = _reference(body["source"], path)
    if source.name not in available:
        refuse(path, "unknown main source")
    families = body["families"]
    if (
        not isinstance(families, list)
        or family not in families
        or len(set(families)) != len(families)
        or any(f not in FAMILIES for f in families)
    ):
        refuse(path, "invalid declared companion family universe")
    aliases = {source.alias: available[source.name]}
    joins = []
    for index, raw in enumerate(body["joins"]):
        location = path + f".joins.{index}"
        raw = shape(
            raw,
            location,
            {"source", "keys", "relationship", "left_role", "right_role", "multiplicity"},
            {"predicate"},
        )
        reference = _reference(raw["source"], location)
        if reference.name not in available or reference.alias in aliases:
            refuse(location, "unknown source or duplicate join alias")
        previous = set(aliases)
        aliases[reference.alias] = available[reference.name]
        _source(view, raw["relationship"], physical)
        if (
            raw["multiplicity"] not in {"one_to_many", "many_to_one"}
            or not raw["left_role"]
            or not raw["right_role"]
        ):
            refuse(location, "join requires declared roles and supported multiplicity")
        join_keys = []
        for item in raw["keys"]:
            item = shape(item, location, {"left", "right"})
            left, right = (read_expression(item[k], location) for k in ("left", "right"))
            left_sources = {field.source for field in expression_fields(left)}
            right_sources = {field.source for field in expression_fields(right)}
            if (
                not left_sources
                or not left_sources <= previous
                or right_sources != {reference.alias}
            ):
                refuse(location, "join keys must link prior and newly joined source fields")
            if (
                check(left, aliases, location)._type_affinity
                is not check(right, aliases, location)._type_affinity
            ):
                refuse(location, "join key types differ")
            join_keys.append(JoinKey(left, right))
        if not join_keys or len(set(join_keys)) != len(join_keys):
            refuse(location, "join requires distinct explicit keys")
        predicate = read_expression(raw["predicate"], location) if "predicate" in raw else None
        if predicate is not None and not isinstance(check(predicate, aliases, location), Boolean):
            refuse(location, "join predicate is not Boolean")
        joins.append(
            Join(
                reference,
                tuple(join_keys),
                raw["relationship"],
                raw["left_role"],
                raw["right_role"],
                raw["multiplicity"],
                predicate,
            )
        )
    for field in fields:
        if (
            check(field.expression, aliases, path + "." + field.name)._type_affinity
            is not field.sql_type._type_affinity
        ):
            refuse(path + "." + field.name, "output type requires an explicit supported cast")
    predicate = read_expression(body["predicate"], path)
    if not isinstance(check(predicate, aliases, path), Boolean):
        refuse(path, "main predicate is not Boolean")
    if len(set(keys)) != len(keys) or not keys or not set(keys) <= {f.name for f in fields}:
        refuse(path, "ordering keys must identify distinct output fields")
    order = []
    for raw in _json_annotation(ci_annotations(cls), "cp:order", path):
        raw = shape(raw, path, {"field"}, {"collation"})
        if raw["field"] not in keys or raw.get("collation") not in {None, "C"}:
            refuse(path, "unsupported order field/collation")
        typ = next(f.sql_type for f in fields if f.name == raw["field"])
        if raw.get("collation") and not isinstance(typ, String):
            refuse(path, "collation requires a text output")
        order.append(Order(raw["field"], raw.get("collation")))
    if tuple(o.field for o in order) != keys:
        refuse(path, "declared order must cover the logical keys exactly once")
    consumers = _json_annotation(ci_annotations(cls), "cp:consumers", path)
    if (
        not isinstance(consumers, list)
        or not consumers
        or not all(isinstance(value, str) for value in consumers)
        or len(set(consumers)) != len(consumers)
    ):
        refuse(path, "projection consumers must be unique qualified operation or port names")
    for consumer in consumers:
        if len(consumer.split(".")) < 2:
            refuse(path, "projection consumer must be qualified")
        for part in consumer.split("."):
            _name(part, path)
    return ProjectionRecipe(
        family,
        projection_id,
        tuple(parameters),
        tuple(helpers),
        tuple(sources),
        source,
        tuple(joins),
        tuple(fields),
        predicate,
        tuple(order),
        tuple(families),
        tuple(consumers),
    )


def _prepare_projection(
    view: SchemaView, family: str, *, projection_id: str, physical: MetaData
) -> CompanionProjection:
    if family not in FAMILIES:
        raise ValueError(f"unsupported companion projection family {family}")
    schema = view.schema
    if schema is None:
        raise ValueError("companion projection requires its declared schema")
    if ci_annotations(schema).get("cp:version") != RECIPE_VERSION:
        refuse("companion-projections.version", "unsupported companion recipe version")
    if (
        _json_annotation(ci_annotations(schema), "cp:json_materialization", str(schema.name))
        != JSON_MATERIALIZATION
    ):
        refuse("companion-projections.json_materialization", "unsupported JSON read direction")
    name, cls = next(
        (name, cls)
        for name, cls in view.all_classes(imports=False).items()
        if ci_annotations(cls).get("cp:family") == family
    )
    columns, outputs, fields = [], [], []
    for slot in view.class_induced_slots(name):
        annotations = ci_annotations(slot)
        typ, required, info = _source(view, annotations["cp:source"], physical)
        column = Column(str(slot.name), typ, nullable=not required, info=info)
        columns.append(column)
        role = annotations.get("cp:role")
        if role not in {"provenance", "identity", "value"}:
            refuse(str(name) + "." + str(slot.name), "missing/unsupported output role")
        outputs.append(
            OutputField(
                str(slot.name),
                read_expression(
                    _json_annotation(annotations, "cp:expr", str(name) + "." + str(slot.name)),
                    str(name) + "." + str(slot.name),
                ),
                annotations["cp:source"],
                role,
                typ,
                not required,
            )
        )
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
    keys = tuple(python_ast.literal_eval(ci_annotations(cls)["cp:keys"]))
    recipe = _recipe(view, family, cls, outputs, keys, projection_id, physical)
    function_name = ci_annotations(cls)["cp:function"]
    if not isinstance(function_name, str) or len(function_name.split(".")) != 2:
        refuse(str(name), "projection function must have a declared schema and name")
    for part in function_name.split("."):
        _name(part, str(name))
        if part.startswith("__"):
            refuse(str(name), "reserved implementation attribute is not a function name")
    return CompanionProjection(
        family,
        function_name,
        str(name),
        tuple(columns),
        recipe,
        pa.schema(fields, metadata={"projection_id": projection_id, "family": family}),
        keys,
        _physical=physical,
        projection_id=projection_id,
    )


def prepare_projection(
    view: SchemaView, family: str, *, projection_id: str, physical: MetaData
) -> CompanionProjection:
    """Resolve supplied effective inputs, including their compiled physical metadata."""
    try:
        return _prepare_projection(view, family, projection_id=projection_id, physical=physical)
    except PreparationError:
        raise
    except (KeyError, StopIteration, TypeError, ValueError) as error:
        return refuse("companion-projections." + family, str(error))


@lru_cache(maxsize=4)
def projection(family: str) -> CompanionProjection:
    from .metadata import metadata

    return prepare_projection(
        SchemaView(str(MODEL)),
        family,
        projection_id=installed_projection_id(),
        physical=metadata,
    )


def render_static_columns() -> str:
    from dataclasses import replace

    from .contracts import compile_execution_model, trusted_execution_inputs
    from .operation_call_generation import _PRIMITIVES, source_bindings

    inputs = trusted_execution_inputs()
    model = compile_execution_model(inputs)
    view, _, model_field, resolve = source_bindings(model, inputs)
    declarations, imports = [], set()
    for family in FAMILIES:
        selected = projection(family)
        fields = {}
        slots = {str(slot.name): slot for slot in view.class_induced_slots(selected.class_name)}
        for selected_column in selected.materialized_columns:
            field = model_field(selected.class_name, slots[selected_column.name])
            typ, _ = resolve(field, {})
            field = replace(field, resolved=typ)
            kind = field.semantic_type or (
                "Literal[" + ", ".join(repr(v) for v in typ.enum_values) + "]"
                if typ.enum_values
                else _PRIMITIVES[typ.kind]
            )
            if typ.kind == "json_payload":
                kind = "str"  # This materialized direction carries raw JSON text.
            if field.semantic_type:
                imports.add(field.semantic_type)
            if typ.multivalued:
                kind = f"list[{kind}]"
            if selected_column.nullable:
                kind += " | None"
            fields[selected_column.name] = kind
        declarations.append(
            render_typed_column_class(
                selected.class_name,
                selected.materialized_columns,
                bindings=fields,
            ).rstrip()
        )
    return (
        "# Generated from model/semantic/companion-projections.yaml.\n"
        "from typing import Literal\n"
        "from sqlalchemy import Named, TypedColumns\n"
        + "".join(f"from ._operation_ids import {name} as {name}\n" for name in sorted(imports))
        + "\n\n"
        + "\n\n".join(declarations)
        + "\n"
    )
