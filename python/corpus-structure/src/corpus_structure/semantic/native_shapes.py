"""Native JSON shape guards from the effective semantic definitions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from itertools import count
from typing import Any

from pglast import ast
from pglast.stream import RawStream
from sqlalchemy import (
    Numeric,
    Text,
    and_,
    any_,
    cast,
    column,
    false,
    func,
    literal_column,
    not_,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSON, JSONB, array, dialect

from .native_program import Block, If, Raise, _body
from .prepared_sql import prepare_sql
from .types import PreparedRelease


def record_shape_expression(
    prepared: PreparedRelease,
    class_name: str,
    expression,
    *,
    fields=None,
    field_names=None,
    deferred_arrays=frozenset(),
):
    """Compile the exact invalid-record predicate over typed JSON expressions."""
    definitions = {definition.name: definition for definition in prepared.definitions}
    vocabularies = {
        v.enum: tuple(member.value for member in v.members) for v in prepared.vocabularies
    }
    names = count()
    strings = {"ParsingString", "PdfString", "PdfDigest", "PdfPointer", "string"}

    def rows(name, value, datatype):
        return (
            getattr(func, name)(value)
            .table_valued(column("value", datatype))
            .render_derived()
            .alias("shape_" + str(next(names)))
        )

    def invalid_record(name, value, *, root=False):
        definition = definitions[name]
        if definition.abstract:
            members = [
                d.name for d in definitions.values() if name in d.ancestors and not d.abstract
            ]
            if not members:
                raise ValueError(f"abstract parsing boundary has no concrete variants: {name}")
            return and_(*(invalid_record(member, value) for member in members))
        storage = (
            "json"
            if isinstance(value.type, JSON) and not isinstance(value.type, JSONB)
            else "jsonb"
        )
        keys = (
            rows("unnest", field_names, Text())
            if root and field_names is not None
            else rows(storage + "_object_keys", value, Text())
        )
        allowed = array([prop.name for prop in definition.properties], type_=Text())
        invalid: list[Any] = [
            select(keys.c.value).where(not_(keys.c.value == any_(allowed))).exists()
        ]
        for prop in definition.properties:
            field = (
                fields[prop.name] if root and fields and prop.name in fields else value[prop.name]
            )
            field_storage = (
                "json"
                if isinstance(field.type, JSON) and not isinstance(field.type, JSONB)
                else "jsonb"
            )
            field_kind = getattr(func, field_storage + "_typeof")
            present: Any = (
                prop.name == any_(field_names)
                if root and field_names is not None
                else value.bool_op("?")(prop.name)
                if storage == "jsonb"
                else value[prop.name].is_not(None)
            )
            scalar = field.op("#>>", return_type=Text())(array([], type_=Text()))
            if prop.required:
                invalid.append(not_(present))
            if prop.multivalued:
                predicates = [field_kind(field).is_distinct_from("array")]
                if prop.range in strings or prop.range in vocabularies:
                    elements = rows(field_storage + "_array_elements", field, field.type)
                    predicates.append(
                        select(elements.c.value)
                        .where(field_kind(elements.c.value).is_distinct_from("string"))
                        .exists()
                    )
                if prop.range in definitions and not (root and prop.name in deferred_arrays):
                    elements = rows(field_storage + "_array_elements", field, field.type)
                    predicates.append(
                        select(elements.c.value)
                        .where(
                            or_(
                                field_kind(elements.c.value).is_distinct_from("object"),
                                invalid_record(prop.range, elements.c.value),
                            )
                        )
                        .exists()
                    )
                length = getattr(func, field_storage + "_array_length")(field)
                if prop.minimum_cardinality is not None and prop.minimum_cardinality > 0:
                    predicates.append(length < prop.minimum_cardinality)
                if prop.maximum_cardinality is not None:
                    predicates.append(length > prop.maximum_cardinality)
                predicate = or_(*predicates)
            elif prop.range in {"ParsingBoolean", "PdfBoolean", "boolean"}:
                predicate = field_kind(field).is_distinct_from("boolean")
            elif prop.range in {"ParsingInteger", "PdfInteger", "integer"}:
                predicate = or_(
                    field_kind(field).is_distinct_from("number"), scalar.bool_op("!~")("^[0-9]+$")
                )
            elif prop.range in {"PdfNumber", "float", "double", "decimal"}:
                predicate = field_kind(field).is_distinct_from("number")
            elif prop.range in strings or prop.range in vocabularies:
                predicate = field_kind(field).is_distinct_from("string")
                if prop.range in vocabularies:
                    predicate = or_(predicate, scalar.not_in(vocabularies[prop.range]))
            elif prop.range in definitions:
                predicate = or_(
                    field_kind(field).is_distinct_from("object"), invalid_record(prop.range, field)
                )
            else:
                raise ValueError(f"unsupported required parsing native shape: {name}/{prop.name}")
            invalid.append(and_(present, predicate))
            if prop.equals_string is not None:
                invalid.append(scalar.is_distinct_from(prop.equals_string))
            for pattern in prop.patterns or ((prop.pattern,) if prop.pattern else ()):
                if prop.multivalued:
                    elements = rows(field_storage + "_array_elements_text", field, Text())
                    invalid.append(
                        and_(
                            present,
                            select(elements.c.value)
                            .where(elements.c.value.bool_op("!~")(pattern))
                            .exists(),
                        )
                    )
                else:
                    invalid.append(and_(present, scalar.bool_op("!~")(pattern)))
            if prop.minimum is not None:
                invalid.append(and_(present, cast(scalar, Numeric()) < prop.minimum))
            if prop.maximum is not None:
                invalid.append(and_(present, cast(scalar, Numeric()) > prop.maximum))
        return or_(*invalid, false())

    return invalid_record(class_name, expression, root=True)


def record_shape_steps(prepared, class_name, expression, **options):
    """Two procedural refusals over the shared structured predicate."""
    return (
        If(
            func.jsonb_typeof(expression).is_distinct_from("object"),
            (Raise("parsing record must be an object: " + class_name, "23514"),),
        ),
        If(
            record_shape_expression(prepared, class_name, expression, **options),
            (Raise("parsing record shape differs: " + class_name, "23514"),),
        ),
    )


def _expression(source, datatype):
    """Bridge existing trusted declaration expressions to the typed compiler."""
    statement = prepare_sql("SELECT " + source, source="native shape expression").statements[0].stmt
    if (
        not isinstance(statement, ast.SelectStmt)
        or len(statement.targetList or ()) != 1
        or statement.fromClause
        or not statement.targetList
    ):
        raise ValueError("native shape requires one lexical expression")
    return literal_column(RawStream()(statement.targetList[0].val), type_=datatype)


def record_shape_predicate(prepared: PreparedRelease, class_name: str, expression: str) -> str:
    return str(
        record_shape_expression(prepared, class_name, _expression(expression, JSONB())).compile(
            dialect=dialect(paramstyle="named"),
            compile_kwargs={"literal_binds": True},
        )
    )


def record_shape_guards(prepared: PreparedRelease, class_name: str, expression: str) -> str:
    return _guard_body(record_shape_steps(prepared, class_name, _expression(expression, JSONB())))


def _guard_body(steps):
    body = _body(Block(steps))
    return body.removeprefix("BEGIN\n").removesuffix("\nEND") + "\n"


@dataclass(frozen=True)
class DecomposedRecordGuards:
    envelope: str
    rows: Mapping[str, str]


def decomposed_record_guards(
    prepared: PreparedRelease,
    class_name: str,
    expression: str,
    *,
    field_names: str,
    collections: Mapping[str, tuple[str, str]],
    records: Mapping[str, str],
) -> DecomposedRecordGuards:
    definition = next(d for d in prepared.definitions if d.name == class_name)
    properties = {p.name: p for p in definition.properties}
    classes = {d.name for d in prepared.definitions}
    fields = {name: _expression(value, JSON()) for name, (value, _) in collections.items()}
    fields.update({name: _expression(value, JSONB()) for name, value in records.items()})
    rows = {}
    for name, (_, record) in collections.items():
        prop = properties[name]
        if not prop.multivalued or prop.range not in classes:
            raise ValueError(f"decomposed record collection has no modeled record range: {name}")
        rows[name] = record_shape_guards(prepared, prop.range, record)
    if any(
        p.multivalued and p.range in classes and p.name not in collections
        for p in definition.properties
    ):
        raise ValueError("every top-level record collection needs a complete row guard binding")
    return DecomposedRecordGuards(
        _guard_body(
            record_shape_steps(
                prepared,
                class_name,
                _expression(expression, JSONB()),
                fields=fields,
                field_names=_expression(field_names, ARRAY(Text())),
                deferred_arrays=frozenset(collections),
            )
        ),
        rows,
    )
