"""Trusted semantic physical metadata and generated typed SQLAlchemy column surfaces.

Only the captured physical and read-projection models compile to tables. Runtime
candidate schemas remain separate semantic definitions, never physical authority.
"""

from __future__ import annotations

import hashlib
import keyword
from collections.abc import Iterable, Mapping
from typing import Any, Literal

from linkml_runtime.linkml_model import SlotDefinition
from pgvector.sqlalchemy import VECTOR as Vector
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError
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
    and_,
    case,
    cast,
    func,
    literal,
    not_,
    or_,
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
    array,
)
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.sqltypes import ARRAY as BaseARRAY
from sqlalchemy.types import TypeEngine

from corpus_structure.schema.declarations import (
    ModelError,
    View,
    ci_annotations,
    expand_enum,
)
from corpus_structure.schema.integrity import (
    annotation_values,
    integrity_from_view,
    relation_annotations,
    validate_relation_profile,
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


def _stored_enum_members(view: View, name: str) -> tuple[str, ...]:
    enum = view.get_enum(name)
    if enum is None:
        return ()
    excluded = {
        str(value.text)
        for value in enum.permissible_values.values()
        if value.status == "provisional"
        or annotation_values(value).get("ph:omit_from_storage") is True
    }
    return tuple(member.text for member in expand_enum(view, name) if member.text not in excluded)


def check_name(table: str, what: str, sql: str) -> str:
    name = f"ck_{table}_{what}_{digest(sql)}"
    if len(name) > MAX_NAME:
        raise ModelError([f"CHECK name {name} exceeds {MAX_NAME} characters"])
    return name


class _PhysicalDeclaration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PhysicalField(_PhysicalDeclaration):
    field: str


class PhysicalSearchConfiguration(_PhysicalDeclaration):
    search_configuration: str


class PhysicalValue(_PhysicalDeclaration):
    value: str | int | float | bool | None


class PhysicalCall(_PhysicalDeclaration):
    call: Literal[
        "jsonb_typeof",
        "octet_length",
        "convert_to",
        "sha256",
        "encode",
        "ops.pdf_product_descriptor",
    ]
    args: tuple[PhysicalExpression, ...]


class PhysicalCast(_PhysicalDeclaration):
    cast: Literal["text", "jsonb"]
    value: PhysicalExpression


class PhysicalOperator(_PhysicalDeclaration):
    op: Literal[
        "eq",
        "ne",
        "gt",
        "lt",
        "ge",
        "le",
        "distinct",
        "not_distinct",
        "regex",
        "like",
        "concat",
        "json",
        "json_text",
        "all",
        "any",
        "not",
        "is_null",
        "is_not_null",
        "in",
        "not_in",
        "between",
        "case",
    ]
    args: tuple[PhysicalExpression, ...]


type PhysicalExpression = (
    PhysicalField
    | PhysicalSearchConfiguration
    | PhysicalValue
    | PhysicalCall
    | PhysicalCast
    | PhysicalOperator
)
for _declaration in (PhysicalCall, PhysicalCast, PhysicalOperator):
    _declaration.model_rebuild()


class PhysicalCheck(_PhysicalDeclaration):
    name: str = Field(min_length=1, max_length=MAX_NAME)
    predicate: PhysicalExpression


class PhysicalIndex(_PhysicalDeclaration):
    name: str | None = None
    columns: tuple[str, ...] = ()
    expression: PhysicalExpression | None = None
    where: PhysicalExpression | None = None
    collations: dict[str, str] = Field(default_factory=dict)
    using: Literal["btree", "gin", "gist", "hash", "brin", "spgist"] = "btree"
    include: tuple[str, ...] | None = None


def _physical_expression(expression: PhysicalExpression, table: Table) -> ColumnElement[Any]:
    """Bind finite physical predicates to the selected, typed relation."""
    if isinstance(expression, PhysicalField):
        if expression.field not in table.c:
            raise ModelError([f"{table.fullname}: unknown physical field {expression.field!r}"])
        return table.c[expression.field]
    if isinstance(expression, PhysicalSearchConfiguration):
        relation, field = expression.search_configuration.rsplit(".", 1)
        source = table.metadata.tables.get(relation)
        configuration = (
            source.c[field].info.get("search_configuration")
            if source is not None and field in source.c
            else None
        )
        if not isinstance(configuration, str) or not configuration:
            raise ModelError([f"{table.fullname}: unresolved search configuration reference"])
        return literal(configuration, Text())
    if isinstance(expression, PhysicalValue):
        return literal(expression.value)
    if isinstance(expression, PhysicalCast):
        target_type: TypeEngine[Any] = Text() if expression.cast == "text" else JSONB()
        return cast(_physical_expression(expression.value, table), target_type)
    arguments = tuple(_physical_expression(arg, table) for arg in expression.args)
    if isinstance(expression, PhysicalCall):
        arities = {
            "jsonb_typeof": 1,
            "octet_length": 1,
            "convert_to": 2,
            "sha256": 1,
            "encode": 2,
            "ops.pdf_product_descriptor": 1,
        }
        if len(arguments) != arities[expression.call]:
            raise ModelError([f"{table.fullname}: invalid {expression.call} argument count"])
        function: Any = func
        for part in expression.call.split("."):
            function = getattr(function, part)
        return function(*arguments)
    op = expression.op
    if op in {"all", "any"}:
        if not arguments:
            raise ModelError([f"{table.fullname}: empty physical Boolean expression"])
        return and_(*arguments) if op == "all" else or_(*arguments)
    arity = 1 if op in {"not", "is_null", "is_not_null"} else 3 if op in {"between", "case"} else 2
    if op in {"in", "not_in"}:
        if len(arguments) < 2 or not all(
            isinstance(arg, PhysicalValue) for arg in expression.args[1:]
        ):
            raise ModelError([f"{table.fullname}: physical membership requires literal choices"])
        members = [arg.value for arg in expression.args[1:] if isinstance(arg, PhysicalValue)]
        return arguments[0].in_(members) if op == "in" else arguments[0].not_in(members)
    if len(arguments) != arity:
        raise ModelError([f"{table.fullname}: invalid {op} operand count"])
    first = arguments[0]
    if op == "not":
        return not_(first)
    if op == "is_null":
        return first.is_(None)
    if op == "is_not_null":
        return first.is_not(None)
    if op == "case":
        return case((first, arguments[1]), else_=arguments[2])
    if op == "between":
        return first.between(arguments[1], arguments[2])
    second = arguments[1]
    comparisons = {
        "eq": first.__eq__,
        "ne": first.__ne__,
        "gt": first.__gt__,
        "lt": first.__lt__,
        "ge": first.__ge__,
        "le": first.__le__,
        "distinct": first.is_distinct_from,
        "not_distinct": first.is_not_distinct_from,
        "like": first.like,
    }
    if op in comparisons:
        return comparisons[op](second)
    if op == "regex":
        return first.bool_op("~")(second)
    result_type = {"concat": Text(), "json": JSONB(), "json_text": Text()}[op]
    return first.op(
        {"concat": "||", "json": "->", "json_text": "->>"}[op], return_type=result_type
    )(second)


def physical_expression_sql(expression: ColumnElement[Any]) -> str:
    """Render a bound CHECK without a relation qualifier for native scratch contexts."""
    from sqlalchemy.dialects.postgresql import dialect

    return str(
        expression.compile(
            dialect=dialect(paramstyle="named"),
            compile_kwargs={"literal_binds": True, "include_table": False},
        )
    )


def _physical_checks(value, table: Table) -> tuple[PhysicalCheck, ...]:
    try:
        return TypeAdapter(tuple[PhysicalCheck, ...]).validate_python(value)
    except ValidationError as error:
        raise ModelError([f"{table.fullname}: invalid typed physical checks: {error}"]) from error


# --- Compilation -------------------------------------------------------------------------------


def _physical_default(
    typ: TypeEngine[Any], annotations: Mapping[str, Any], location: str
) -> ColumnElement[Any] | None:
    value = annotations.get("ph:server_default_value")
    factory = annotations.get("ph:server_default_factory")
    if "ph:default" in annotations or (value is not None and factory is not None):
        raise ModelError([f"{location}: invalid server default declaration"])
    if factory == "uuid_text" and isinstance(typ, Text):
        return cast(func.gen_random_uuid(), Text())
    if factory == "empty_object" and isinstance(typ, JSONB):
        return cast(literal("{}", Text()), JSONB())
    if factory is not None:
        raise ModelError([f"{location}: unsupported server default factory {factory!r}"])
    if value is None:
        return None
    if (
        (isinstance(typ, Boolean) and isinstance(value, bool))
        or (isinstance(typ, Integer) and isinstance(value, int) and not isinstance(value, bool))
        or (isinstance(typ, Text) and isinstance(value, str))
    ):
        return literal(value, typ)
    raise ModelError([f"{location}: server default is incompatible with its physical type"])


def _physical_generated(
    typ: TypeEngine[Any],
    annotations: Mapping[str, Any],
    slots: Mapping[str, SlotDefinition],
    location: str,
) -> ColumnElement[Any] | None:
    generated = annotations.get("ph:generated_as")
    source = annotations.get("ph:generated_source")
    configuration = annotations.get("ph:search_configuration")
    if "ph:computed" in annotations:
        raise ModelError([f"{location}: generated columns require a declared projection"])
    if generated is None and source is None and configuration is None:
        return None
    if (
        not isinstance(source, str)
        or source not in slots
        or slots[source].multivalued
        or annotations.get("ph:identity") is not None
    ):
        raise ModelError([f"{location}: invalid generated column source"])
    source_range = str(slots[source].range or "string")
    if (
        generated == "search_vector"
        and source_range == "string"
        and isinstance(typ, TSVECTOR)
        and isinstance(configuration, str)
        and configuration
    ):
        return func.to_tsvector(
            cast(literal(configuration, Text()), REGCONFIG()), sql_column(source, Text())
        )
    if configuration is None:
        if (
            generated == "integer_point_range"
            and source_range == "integer"
            and isinstance(typ, INT8RANGE)
        ):
            point = sql_column(source, BigInteger())
            return func.int8range(point, point, "[]")
        endpoints = {"visual_region_x": ("left", "right"), "visual_region_y": ("top", "bottom")}
        if generated in endpoints and source_range == "json_payload" and isinstance(typ, NUMRANGE):
            region = sql_column(source, JSONB()).op("->", return_type=JSONB())("source_region")
            first, last = (
                region.op("->>", return_type=Text())(edge) for edge in endpoints[generated]
            )
            return case(
                (
                    and_(first.is_not(None), last.is_not(None)),
                    func.numrange(cast(first, Numeric()), cast(last, Numeric()), "[)"),
                )
            )
    raise ModelError([f"{location}: unsupported generated projection {generated!r}"])


def compile_metadata(view: View, *, target: str) -> MetaData:
    """Compile one explicitly selected trusted physical or read-projection model."""
    if target not in {"semantic", "semantic-read"}:
        raise ModelError([f"unknown relational target {target!r}"])
    return _compile_physical(view, read_only=target == "semantic-read")


def physical_range_type(view: View, rng: str) -> TypeEngine[Any]:
    """Resolve a declared range through the same backend used by physical columns."""
    physical_types = {
        "int8": BigInteger,
        "text": Text,
        "bool": Boolean,
        "float8": Double,
        "bytea": BYTEA,
        "jsonb": JSONB,
        "numeric": Numeric,
        "int8range": INT8RANGE,
        "numrange": NUMRANGE,
        "vector": Vector,
        "timestamptz": lambda: TIMESTAMP(timezone=True),
        "tsvector": TSVECTOR,
    }
    declared = view.get_type(rng)
    sql_type = ci_annotations(declared).get("ph:sql_type")
    if sql_type is not None:
        try:
            return physical_types[str(sql_type)]()
        except KeyError as error:
            raise ModelError([f"unsupported physical SQL type {sql_type}"]) from error
    if view.get_enum(rng) is not None:
        return Text()
    if rng == "integer":
        return BigInteger()
    if rng == "boolean":
        return Boolean()
    if rng == "string":
        return Text()
    if declared is not None and str(declared.uri) in URI_TYPES:
        return URI_TYPES[str(declared.uri)]()
    raise ModelError([f"unsupported physical range {rng}"])


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
    integrity_policy = integrity_from_view(view)
    schemas = {}
    for name, subset in view.all_subsets().items():
        policy = annotation_values(subset)
        if policy.get("ph:physical_schema") is not True:
            continue
        if "ph:read_roles" not in policy or policy.get("ph:frontier_guard") not in {
            "guarded",
            "exempt",
        }:
            raise ModelError([f"physical schema {name} lacks read/guard defaults"])
        policy["ph:read_roles"] = integrity_policy.require_roles(policy["ph:read_roles"])
        schemas[str(name)] = policy
    if not schemas:
        raise ModelError(["physical model declares no physical schemas"])
    md = MetaData(naming_convention=dict(NAMING_CONVENTION))
    md.info["physical_schemas"] = tuple(schemas)
    md.info["integrity_policy"] = integrity_policy
    # Trusted physical imports may contribute stored relations. Imported payload
    # classes without a physical subset remain boundary types, never tables.
    physical_classes = dict(view.schema.classes)
    if not read_only:
        physical_classes.update(
            {
                name: cls
                for name, cls in view.all_classes().items()
                if name not in physical_classes
                and any(str(subset) in schemas for subset in cls.in_subset)
            }
        )
    nominal = _physical_nominals(view)
    for name, cls in physical_classes.items():
        subsets = [str(s) for s in cls.in_subset]
        if len(subsets) != 1 or subsets[0] not in schemas:
            raise ModelError([f"{name}: physical table needs exactly one trusted physical subset"])
        columns = []
        slots = {str(slot.name): slot for slot in view.class_induced_slots(name)}
        for slot in slots.values():
            rng = str(slot.range or "string")
            typ = physical_range_type(view, rng)
            if slot.multivalued:
                typ = ARRAY(typ)
            validate_relation_profile(
                view, annotation_values(slot), f"{name}.{slot.name}", profile="PhysicalColumn"
            )
            annotations = ci_annotations(slot)
            location = f"{name}.{slot.name}"
            default = _physical_default(typ, annotations, location)
            computed = _physical_generated(typ, annotations, slots, location)
            if default is not None and (
                computed is not None or annotations.get("ph:identity") is not None
            ):
                raise ModelError([f"{location}: server default conflicts with generated value"])
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
                    server_default=default,
                    info={
                        **nominal(subsets[0], str(name), str(slot.name)),
                        "search_configuration": annotations.get("ph:search_configuration"),
                        "minimum": slot.minimum_value,
                        "maximum": slot.maximum_value,
                        "pattern": slot.pattern,
                        "enum": (str(slot.equals_string),)
                        if slot.equals_string is not None
                        else _stored_enum_members(view, rng),
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
        physical_annotations = relation_annotations(view, name)
        validate_relation_profile(view, physical_annotations, str(name))
        schema_policy = schemas[subsets[0]]
        read_roles = physical_annotations.get("ph:read_roles", schema_policy["ph:read_roles"])
        if not isinstance(read_roles, (list, tuple)):
            raise ModelError([f"{name}: physical read roles must be structured roles"])
        table_info["read_roles"] = integrity_policy.require_roles(read_roles)
        frontier = physical_annotations.get("ph:frontier_guard", schema_policy["ph:frontier_guard"])
        if frontier not in {"guarded", "exempt"}:
            raise ModelError([f"{name}: invalid frontier guard policy"])
        table_info["frontier_guard"] = frontier
        table = Table(str(name), md, *columns, schema=subsets[0], info=table_info)
        for slot in view.class_induced_slots(name):
            if slot.equals_string is not None:
                expression = table.c[str(slot.name)] == str(slot.equals_string)
                sql = str(slot.name) + " = " + quote(str(slot.equals_string))
                table.append_constraint(
                    CheckConstraint(expression, name=check_name(table.name, str(slot.name), sql))
                )
            if view.get_enum(str(slot.range)) is not None:
                members = _stored_enum_members(view, str(slot.range))
                field = table.c[str(slot.name)]
                if slot.multivalued:
                    expression = and_(
                        field.contained_by(array(sorted(members), type_=Text())),
                        func.array_position(field, None).is_(None),
                    )
                    sql = str(expression.compile(compile_kwargs={"literal_binds": True}))
                else:
                    expression = field.in_(sorted(members))
                    sql = in_check(str(slot.name), members)
                table.append_constraint(
                    CheckConstraint(expression, name=check_name(table.name, str(slot.name), sql))
                )
            for bound, operator in ((slot.minimum_value, ">="), (slot.maximum_value, "<=")):
                if bound is not None:
                    expression = (
                        table.c[str(slot.name)] >= bound
                        if operator == ">="
                        else table.c[str(slot.name)] <= bound
                    )
                    sql = f"{slot.name} {operator} {bound}"
                    table.append_constraint(
                        CheckConstraint(
                            expression, name=check_name(table.name, str(slot.name), sql)
                        )
                    )
            if slot.pattern:
                expression = table.c[str(slot.name)].bool_op("~")(str(slot.pattern))
                sql = str(slot.name) + " ~ " + quote(str(slot.pattern))
                table.append_constraint(
                    CheckConstraint(expression, name=check_name(table.name, str(slot.name), sql))
                )
        for key_name, key in cls.unique_keys.items():
            constraint = PrimaryKeyConstraint if key_name == "primary_key" else UniqueConstraint
            table.append_constraint(constraint(*map(str, key.unique_key_slots)))
    for name, cls in physical_classes.items():
        schema = str(cls.in_subset[0])
        table = md.tables[f"{schema}.{name}"]
        ann = relation_annotations(view, name)
        for fk in ann.get("ph:foreign_keys", []):
            target_name, remote = fk["target"].rsplit(".", 1)
            local = fk["columns"]
            target = [f"{target_name}.{col}" for col in remote.split(",")]
            table.append_constraint(
                ForeignKeyConstraint(
                    local, target, name=fk.get("name"), info={"shared": tuple(local[:-1])}
                )
            )
        for declaration in _physical_checks(ann.get("ph:checks", []), table):
            table.append_constraint(
                CheckConstraint(
                    _physical_expression(declaration.predicate, table), name=declaration.name
                )
            )
        for raw in ann.get("ph:indexes", []):
            try:
                declaration = PhysicalIndex.model_validate(
                    raw if isinstance(raw, dict) else {"columns": raw}
                )
            except ValidationError as error:
                raise ModelError(
                    [f"{table.fullname}: invalid typed physical index: {error}"]
                ) from error
            if bool(declaration.columns) == (declaration.expression is not None):
                raise ModelError([f"{table.fullname}: index requires columns or an expression"])
            for name in (
                *declaration.columns,
                *(declaration.include or ()),
                *declaration.collations,
            ):
                if name not in table.c:
                    raise ModelError([f"{table.fullname}: unknown physical index field {name!r}"])
            expressions = (
                (_physical_expression(declaration.expression, table),)
                if declaration.expression is not None
                else tuple(
                    table.c[c].collate(declaration.collations[c])
                    if c in declaration.collations
                    else table.c[c]
                    for c in declaration.columns
                )
            )
            Index(
                declaration.name,
                *expressions,
                postgresql_where=_physical_expression(declaration.where, table)
                if declaration.where is not None
                else None,
                postgresql_using=declaration.using,
                postgresql_include=declaration.include,
            )
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
