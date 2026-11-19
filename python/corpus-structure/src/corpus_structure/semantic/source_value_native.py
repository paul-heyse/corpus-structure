"""Generate the pure native SourceValue codec from its captured LinkML layout."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Double,
    Integer,
    Text,
    and_,
    cast,
    column,
    func,
    literal,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import BIT, JSONB, aggregate_order_by

from corpus_structure.schema.integrity import role_name

from .native_objects import INTERNAL_PROGRAM, native_privilege_sql
from .native_program import (
    Assign,
    Block,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Raise,
    Return,
    SelectInto,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration
from .types import SourceArtifact

_INTEGER = r"^-?(0|[1-9][0-9]*)$"


@dataclass(frozen=True)
class SourceVariant:
    tag: str
    payload: str | None


def _layout(source: bytes) -> dict[str, SourceVariant]:
    from corpus_structure.model.compiled import compiled_model

    view = compiled_model({"source-values.yaml": source}).private_view("source-values.yaml")
    variants = {}
    for name in ("Text", "Integer", "Float", "Boolean", "Null", "Array", "Object"):
        slots = {str(slot.name): slot for slot in view.class_induced_slots("Source" + name)}
        kind = slots.pop("kind")
        if not kind.equals_string or len(slots) != (0 if name == "Null" else 1):
            raise ValueError(f"Source{name} does not declare one finite codec variant")
        variants[name] = SourceVariant(
            str.__str__(kind.equals_string),
            str.__str__(next(iter(slots))) if slots else None,
        )
    fields = {slot.name for slot in view.class_induced_slots("SourceField")}
    if fields != {"name", "position", "value"}:
        raise ValueError("SourceField requires the ordered name/position/value codec contract")
    return variants


def source_value_native_sources(source: bytes) -> tuple[SourceArtifact, ...]:
    return (
        SourceArtifact(
            "native/data-operation-source-values.sql", source_value_native_sql(source).encode()
        ),
        SourceArtifact("native/data-operation-source-values.py", Path(__file__).read_bytes()),
        SourceArtifact("native/data-operation-source-values-model.yaml", source),
    )


def _refuse(message: str) -> tuple[Raise, ...]:
    return (Raise(message, "23514"),)


def _array(value, *, ordered: bool = False):
    fields = (column("value", JSONB()),)
    return (
        func.jsonb_array_elements(value)
        .table_valued(*fields, **({"with_ordinality": "position"} if ordered else {}))
        .render_derived(name="items")
    )


def _each(value):
    return (
        func.jsonb_each(value)
        .table_valued(column("key", Text()), column("value", JSONB()))
        .render_derived(name="fields")
    )


def _aggregate(value, order):
    return func.coalesce(
        func.jsonb_agg(aggregate_order_by(value, order)), cast(literal("[]"), JSONB())
    )


def _routine(
    name: str, parameters: tuple[Parameter, ...], returns: str, body: Block, *, strict=False
) -> NativeRoutine:
    return NativeRoutine(
        "data",
        name,
        parameters=parameters,
        returns=pg_type(returns),
        body=body,
        volatility="immutable",
        strict=strict,
        search_path=("pg_catalog", "pg_temp"),
    )


def source_value_native_programs(source: bytes) -> tuple[ProgramDeclaration, ...]:
    layout = _layout(source)
    p = core_variable("p", JSONB())
    kind = core_variable("kind", Text())
    result = core_variable("result", JSONB())
    parameters = (Parameter("p", pg_type("jsonb")),)
    null_json = cast(literal("null"), JSONB())
    empty_array = cast(literal("[]"), JSONB())
    empty_object = cast(literal("{}"), JSONB())
    tags = {name: variant.tag for name, variant in layout.items()}
    payloads = {
        name: variant.payload for name, variant in layout.items() if variant.payload is not None
    }
    text_field = payloads["Text"]
    integer_field = payloads["Integer"]
    float_field = payloads["Float"]
    boolean_field = payloads["Boolean"]
    array_field = payloads["Array"]
    object_field = payloads["Object"]

    value = core_variable("value", JSONB())
    member = core_variable("member", Text())
    fields = _array(value[object_field])
    selected = (
        select(fields.c.value["value"])
        .where(fields.c.value["name"].astext == member)
        .scalar_subquery()
    )
    report_parameters = (Parameter("value", pg_type("jsonb")), Parameter("member", pg_type("text")))
    report = NativeRoutine(
        "data",
        "report_field",
        parameters=report_parameters,
        returns=pg_type("jsonb"),
        body=select(selected).where(value["kind"].astext == tags["Object"]),
        volatility="immutable",
        strict=True,
        search_path=("pg_catalog", "pg_temp"),
    )

    lexical = core_variable("lexical", Text())
    digits = core_variable("digits", Text())
    exponent = core_variable("exponent", Integer())
    floating = core_variable("result", Double())
    float_body = Block(
        (
            If(
                p["kind"].astext == tags["Integer"],
                (
                    If(
                        or_(
                            func.jsonb_typeof(p[integer_field]).is_distinct_from("number"),
                            ~p[integer_field].astext.regexp_match(_INTEGER),
                        ),
                        _refuse("source report integer must be an integer"),
                    ),
                    Return(cast(p[integer_field].astext, Double())),
                ),
            ),
            If(
                or_(
                    p["kind"].astext.is_distinct_from(tags["Float"]),
                    func.jsonb_typeof(p[float_field]).is_distinct_from("string"),
                ),
                _refuse("record event score is not numeric"),
            ),
            Assign("lexical", func.data.require_float_lexical(p[float_field].astext)),
            Assign(
                "digits",
                func.replace(
                    func.split_part(func.split_part(func.ltrim(lexical, "-"), "p", 1), "x", 2),
                    ".",
                    "",
                ),
            ),
            Assign("exponent", cast(func.split_part(lexical, "p", 2), Integer()) - 52),
            # Preserve exact binary scaling including subnormals and negative zero.
            Assign(
                "result",
                cast(
                    cast(cast(literal("x") + func.lpad(digits, 16, "0"), BIT(64)), BigInteger()),
                    Double(),
                )
                * func.power(cast(literal(2), Double()), exponent),
            ),
            If(func.left(lexical, 1) == "-", (Assign("result", -floating),)),
            Return(floating),
        ),
        (
            Local("lexical", pg_type("text")),
            Local("digits", pg_type("text")),
            Local("exponent", pg_type("int4")),
            Local("result", pg_type("float8")),
        ),
    )

    array = _array(func.coalesce(p[array_field], empty_array), ordered=True)
    fields = _array(func.coalesce(p[object_field], empty_array), ordered=True)
    invalid_positions = core_variable("invalid_positions", Boolean())
    invalid_fields = core_variable("invalid_fields", Boolean())
    repeated_names = core_variable("repeated_names", Boolean())
    scalar_steps = tuple(
        If(
            kind == tags[name],
            (
                If(
                    or_(
                        func.jsonb_typeof(p[payloads[name]]).is_distinct_from(json_kind),
                        *(
                            [~p[integer_field].astext.regexp_match(_INTEGER)]
                            if name == "Integer"
                            else []
                        ),
                    ),
                    _refuse(f"invalid source report {tags[name]} scalar"),
                ),
                Return(p[payloads[name]]),
            ),
        )
        for name, json_kind in (("Text", "string"), ("Boolean", "boolean"), ("Integer", "number"))
    )
    source_body = Block(
        (
            If(p.is_(None), (Return(null_json),)),
            If(kind == tags["Null"], (Return(null_json),)),
            *scalar_steps,
            If(kind == tags["Float"], (Return(func.to_jsonb(func.data.record_source_float(p))),)),
            If(
                kind == tags["Array"],
                (
                    If(
                        and_(
                            p.has_key(literal(array_field, Text())),
                            func.jsonb_typeof(p[array_field]).is_distinct_from("array"),
                        ),
                        _refuse("source report items must be an array"),
                    ),
                    SelectInto(
                        select(
                            _aggregate(
                                func.data.record_source_json(array.c.value), array.c.position
                            )
                        ),
                        ("result",),
                    ),
                    Return(result),
                ),
            ),
            If(
                kind == tags["Object"],
                (
                    If(
                        and_(
                            p.has_key(literal(object_field, Text())),
                            func.jsonb_typeof(p[object_field]).is_distinct_from("array"),
                        ),
                        _refuse("source report fields must be an array"),
                    ),
                    SelectInto(
                        select(
                            func.bool_or(
                                or_(
                                    func.jsonb_typeof(fields.c.value["position"]).is_distinct_from(
                                        "number"
                                    ),
                                    fields.c.value["position"].astext.is_distinct_from(
                                        cast(fields.c.position - 1, Text())
                                    ),
                                )
                            ),
                            func.bool_or(
                                or_(
                                    func.jsonb_typeof(fields.c.value["name"]).is_distinct_from(
                                        "string"
                                    ),
                                    ~fields.c.value.has_key(literal("value", Text())),
                                )
                            ),
                            func.count()
                            != func.count(fields.c.value["name"].astext.collate("C").distinct()),
                        ),
                        ("invalid_positions", "invalid_fields", "repeated_names"),
                    ),
                    If(
                        invalid_positions,
                        _refuse("source report fields are not contiguous and ordered"),
                    ),
                    If(
                        invalid_fields,
                        _refuse("source report field requires a string name and encoded value"),
                    ),
                    If(repeated_names, _refuse("source report contains a repeated field name")),
                    SelectInto(
                        select(
                            func.coalesce(
                                func.jsonb_object_agg(
                                    fields.c.value["name"].astext,
                                    func.data.record_source_json(fields.c.value["value"]),
                                ),
                                empty_object,
                            )
                        ),
                        ("result",),
                    ),
                    Return(result),
                ),
            ),
            Raise("unsupported sealed record event JSON", "23514"),
        ),
        (
            Local("result", pg_type("jsonb")),
            Local("kind", pg_type("text"), p["kind"].astext),
            Local("invalid_positions", pg_type("bool")),
            Local("invalid_fields", pg_type("bool")),
            Local("repeated_names", pg_type("bool")),
        ),
    )

    array = _array(p, ordered=True)
    each = _each(p)
    ordered = select(
        each.c.key,
        each.c.value,
        func.row_number().over(order_by=each.c.key.collate("C")).label("position"),
    ).subquery("ordered_fields")
    encode_body = Block(
        (
            If(kind == "null", (Return(func.jsonb_build_object("kind", tags["Null"])),)),
            If(
                kind == "string",
                (Return(func.jsonb_build_object("kind", tags["Text"], text_field, p)),),
            ),
            If(
                kind == "boolean",
                (Return(func.jsonb_build_object("kind", tags["Boolean"], boolean_field, p)),),
            ),
            If(
                kind == "number",
                (
                    If(
                        ~p.op("#>>", return_type=Text())(
                            cast(literal("{}"), ARRAY(Text()))
                        ).regexp_match(_INTEGER),
                        _refuse("source metadata requires exact integer JSON numbers"),
                    ),
                    Return(func.jsonb_build_object("kind", tags["Integer"], integer_field, p)),
                ),
            ),
            If(
                kind == "array",
                (
                    SelectInto(
                        select(
                            _aggregate(
                                func.data.record_json_source(array.c.value), array.c.position
                            )
                        ),
                        ("result",),
                    ),
                    Return(func.jsonb_build_object("kind", tags["Array"], array_field, result)),
                ),
            ),
            If(
                kind == "object",
                (
                    SelectInto(
                        select(
                            _aggregate(
                                func.jsonb_build_object(
                                    "name",
                                    ordered.c.key,
                                    "position",
                                    ordered.c.position - 1,
                                    "value",
                                    func.data.record_json_source(ordered.c.value),
                                ),
                                ordered.c.position,
                            )
                        ),
                        ("result",),
                    ),
                    Return(func.jsonb_build_object("kind", tags["Object"], object_field, result)),
                ),
            ),
            Raise("unsupported source metadata JSON", "23514"),
        ),
        (Local("result", pg_type("jsonb")), Local("kind", pg_type("text"), func.jsonb_typeof(p))),
    )

    meaning_body = Block(
        (
            If(func.jsonb_typeof(p) == "null", (Return(func.jsonb_build_array("null")),)),
            If(func.jsonb_typeof(p) == "string", (Return(func.jsonb_build_array("string", p)),)),
            If(func.jsonb_typeof(p) == "boolean", (Return(func.jsonb_build_array("boolean", p)),)),
            If(
                func.jsonb_typeof(p) == "number",
                (
                    Return(
                        func.jsonb_build_array(
                            "integer",
                            p.op("#>>", return_type=Text())(cast(literal("{}"), ARRAY(Text()))),
                        )
                    ),
                ),
            ),
            If(
                func.jsonb_typeof(p) == "array",
                (
                    SelectInto(
                        select(
                            _aggregate(
                                func.data.record_json_meaning(array.c.value), array.c.position
                            )
                        ),
                        ("result",),
                    ),
                    Return(func.jsonb_build_array("sequence", result)),
                ),
            ),
            If(
                func.jsonb_typeof(p) == "object",
                (
                    SelectInto(
                        select(
                            _aggregate(
                                func.jsonb_build_array(
                                    each.c.key, func.data.record_json_meaning(each.c.value)
                                ),
                                each.c.key.collate("C"),
                            )
                        ),
                        ("result",),
                    ),
                    Return(func.jsonb_build_array("mapping", result)),
                ),
            ),
            Raise("unsupported record graph value", "23514"),
        ),
        (Local("result", pg_type("jsonb")),),
    )
    routines = (
        report,
        _routine("record_source_float", parameters, "float8", float_body, strict=True),
        _routine("record_source_json", parameters, "jsonb", source_body),
        _routine("record_json_source", parameters, "jsonb", encode_body, strict=True),
        _routine("record_json_meaning", parameters, "jsonb", meaning_body),
    )
    return tuple(
        ProgramDeclaration(
            routine,
            source="data-operations:forward",
            owner=role_name("publisher"),
            access=INTERNAL_PROGRAM,
        )
        for routine in routines
    )


def source_value_native_sql(source: bytes) -> str:
    """Render the captured codec and its original PUBLIC revocations."""
    return "".join(
        declaration.routine.render()
        + ";\n"
        + native_privilege_sql(declaration.identity, "PUBLIC", grant=False)
        + ";\n"
        for declaration in source_value_native_programs(source)
    )
