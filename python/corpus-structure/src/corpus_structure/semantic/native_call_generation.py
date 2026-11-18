"""Generate fixed native interfaces from explicitly owned, resolved call assets."""

from __future__ import annotations

import json
from dataclasses import asdict
from hashlib import sha256

from corpus_structure.model.compiled import field_kinds

from .identity import canonical_bytes
from .native_call_sources import _integer_bounds


def _enum_alias(field):
    parts = field.source.split(":", 1)[-1].replace(".", "_").split("_")
    return "".join(part[0].upper() + part[1:] for part in parts if part)


def _all_call_fields(call):
    return (*call.parameters, *call.result_fields, *(f for r in call.records for f in r.fields))


def render_call_identifiers(calls, *, canonical_identifiers=False):
    """Keep identifiers importable without inventing another semantic model."""
    aliases = {
        field.semantic_type: field_kinds()[field.resolved.kind].python
        for _, call in calls
        for field in _all_call_fields(call)
        if field.semantic_type
    }
    enums = {
        _enum_alias(field): field.resolved.enum_values
        for _, call in calls
        for field in _all_call_fields(call)
        if field.resolved.enum_values
    }
    return "\n".join(
        [
            (
                '"""Generated fixed-call enumeration types; physical declarations own nominal identities."""'
                if canonical_identifiers
                else '"""Generated semantic identifiers from execution correspondences; do not edit."""'
            ),
            "from datetime import datetime",
            "from decimal import Decimal",
            "from typing import Literal, NewType",
            "",
            *(
                f"{name} = NewType({name!r}, {kind})"
                for name, kind in sorted(aliases.items())
                if not canonical_identifiers
            ),
            *(
                f"type {name} = Literal[{', '.join(repr(value) for value in values)}]"
                for name, values in sorted(enums.items())
            ),
            "",
        ]
    )


def render_call_bindings(
    calls,
    metadata=None,
    *,
    identifiers_module,
    canonical_identifiers=False,
    context_validator=None,
    value_base=None,
    row_base=None,
    wire_schemas=None,
):
    """Emit already resolved immutable correspondences, irrespective of their model owner."""
    if not identifiers_module:
        raise ValueError("fixed native generation requires its explicit identifier owner")
    if context_validator is None and any(call.requires_context for _, call in calls):
        raise ValueError("fixed native generation requires its actual context owner")

    def context_check(indent, operation, name):
        if context_validator is None:
            return f"{indent}raise ValueError('this native call has no declared context owner')"
        return f"{indent}require_call_context(projection_context, {operation!r}, {name!r}, {name.upper()}_CONTRACT_DIGEST)"

    out = [
        (
            '"""Generated from authenticated fixed-call assets; do not edit."""'
            if canonical_identifiers
            else '"""Generated from execution call correspondences; do not edit."""'
        ),
        "from __future__ import annotations",
        "",
        "from dataclasses import dataclass",
        "from collections.abc import Callable, Mapping, Sequence",
        "from datetime import datetime",
        "from decimal import Decimal",
        "from typing import Annotated, "
        + ("ClassVar, " if wire_schemas else "")
        + "Any, Literal, Never, NewType, NotRequired, Protocol, Required, TypedDict, cast",
        "",
        "from pydantic import Field, JsonValue, TypeAdapter",
        "from sqlalchemy import (ARRAY, BigInteger, Boolean, Column, Connection, DateTime, Double, "
        "Float, Integer, Named, Numeric, Result, Select, Text, TypedColumns, "
        "bindparam, column, func, null, select)",
        "from sqlalchemy.sql import ColumnElement",
        "from sqlalchemy.dialects.postgresql import BYTEA, JSONB, TIMESTAMP",
        "from .task_types import TaskUnitType",
        "from .types import PreparedRelease",
        "from .metadata import table as _core_table",
        "from .operation_value_types import (HeldProgress, NativeResultViolation, "
        + ("OperationResult, " if value_base is None else "")
        + ("NativeRowResult, " if row_base is None else "")
        + "held_progress, "
        + "native_result_scope, native_result_value, SQL_NULL, SqlNull)",
    ]
    if value_base is not None:
        module, symbol = value_base
        out += [f"from {module} import {symbol} as OperationResult"]
    if row_base is not None:
        module, symbol = row_base
        out += [f"from {module} import {symbol} as NativeRowResult"]
    if context_validator is not None:
        module, symbol = context_validator
        out += [f"from {module} import {symbol} as require_call_context"]
    from .data_operation_wire import render_wire_types, wire_type_name

    structural = [
        call
        for _, call in calls
        if any(f.wire_schema is not None for f in (*call.parameters, *call.result_fields))
    ]
    if structural or wire_schemas:
        out += ["from .data_operation_wire import encode_native_wire_request, prepare_wire_schema"]
    definitions, nominals = {}, {}
    if structural:
        for call in structural:
            for field in (*call.parameters, *call.result_fields):
                if field.wire_schema is None:
                    raise ValueError(
                        "mixed native structural lowering requires an explicit boundary"
                    )
                schema = json.loads(field.wire_schema)
                for key, value in schema.get("definitions", {}).items():
                    if key in definitions and definitions[key] != value:
                        raise ValueError("structural native definition collision at " + key)
                    definitions[key] = value
                for path, name in field.wire_nominals:
                    if path in nominals and nominals[path] != name:
                        raise ValueError("structural native nominal collision at " + path)
                    nominals[path] = name
        out += [
            "from .data_operation_json import json_bytes, wire_json_loads",
            "",
            render_wire_types(definitions, tuple(nominals.items())),
        ]
    aliases, emitted = {}, set()
    enum_aliases = {
        field.source: _enum_alias(field)
        for _, call in calls
        for field in _all_call_fields(call)
        if field.resolved.enum_values
    }

    def raw_type(field, *, native=False, json_text=False):
        typ = field.resolved
        if typ is None:
            raise ValueError("call source fields have not been resolved")
        if json_text and typ.kind == "json_payload":
            return "str"
        kind = typ.model_class if typ.model_class and not native else field_kinds()[typ.kind].python
        if typ.enum_values and not native:
            kind = enum_aliases.get(field.source) or (
                "Literal[" + ", ".join(repr(v) for v in typ.enum_values) + "]"
            )
        if typ.multivalued:
            kind = ("list[" if native else "tuple[") + kind + ("]" if native else ", ...]")
        return kind

    def field_type(field, *, json_text=False):
        typ = (
            "TaskUnitType"
            if field.transform == "task_unit_type"
            else "HeldProgress"
            if field.transform == "held_progress"
            else field.semantic_type or raw_type(field, json_text=json_text)
        )
        if field.resolved.multivalued and field.semantic_type:
            typ = f"tuple[{field.semantic_type}, ...]"
        return typ + (" | None" if field.nullable else "")

    def column_type(field, *, json_text=False):
        kind = (
            "str"
            if json_text and field.resolved.kind == "json_payload"
            else field.semantic_type or raw_type(field, native=not bool(field.resolved.enum_values))
        )
        return kind + (" | None" if field.resolved.nullable else "")

    def sql_type(field):
        typ = field.resolved
        if field.native_type == "integer":
            return "Integer()"
        expression = (
            "JSONB(none_as_null=True)"
            if typ.kind == "json_payload" and field.nullable
            else field_kinds()[typ.kind].expression
        )
        return "ARRAY(" + expression + ")" if typ.multivalued else expression

    def request_type(field):
        if field.resolved.kind != "integer":
            return field_type(field)
        lower, upper = _integer_bounds(field)
        scalar = field.semantic_type or "int"
        lower_bound = f"{field.semantic_type}({lower})" if field.semantic_type else str(lower)
        upper_bound = f"{field.semantic_type}({upper})" if field.semantic_type else str(upper)
        annotation = f"Annotated[{scalar}, Field(ge={lower_bound}, le={upper_bound})]"
        if field.resolved.multivalued:
            annotation = f"tuple[{annotation}, ...]"
        return annotation + (" | None" if field.nullable else "")

    def convert(field, value, operation, result_class, *, json_text=False):
        typ = field.resolved
        if typ.nullable and not field.nullable and (typ.kind != "json_payload" or json_text):
            value = f"_required({value}, {field.name!r}, {result_class!r}, {operation!r})"
        if json_text and typ.kind == "json_payload":
            return value
        if typ.model_class:
            value = f"{typ.model_class}.model_validate({value}, strict=True)"
        elif typ.enum_values:
            value = f"cast({raw_type(field)}, {value})"
        elif typ.multivalued:
            value = (
                f"tuple({value})"
                if not field.nullable
                else f"None if {value} is None else tuple({value})"
            )
        if field.transform == "task_unit_type":
            value = (
                f"native_result_value({operation!r}, {result_class!r}, "
                f"{field.name!r}, TaskUnitType, {value})"
            )
        elif field.transform == "held_progress":
            value = (
                f"native_result_value({operation!r}, {result_class!r}, "
                f"{field.name!r}, held_progress, {value})"
            )
        elif field.semantic_type:
            value = (
                f"{field.semantic_type}({value})"
                if not field.nullable
                else f"None if {value} is None else {field.semantic_type}({value})"
            )
        return value

    for _, call in calls:
        for field in _all_call_fields(call):
            if field.semantic_type:
                aliases[field.semantic_type] = field_kinds()[field.resolved.kind].python
    if canonical_identifiers:
        if metadata is None:
            raise ValueError("canonical call identities require explicit physical metadata")
        canonical = {}
        for relation in metadata.tables.values():
            for column in relation.columns:
                if qualified := column.info.get("python_type"):
                    module, name = qualified.rsplit(".", 1)
                    declaration = (module, column.type.python_type.__name__)
                    if name in canonical and canonical[name] != declaration:
                        raise ValueError(
                            "canonical physical identifier declarations differ: " + name
                        )
                    canonical[name] = declaration
        for name, kind in sorted(aliases.items()):
            if name not in canonical or canonical[name][1] != kind:
                raise ValueError("call nominal lacks its canonical physical encoding: " + name)
            out += [f"from {canonical[name][0]} import {name} as {name}"]
    else:
        out += [f"from {identifiers_module} import {name} as {name}" for name in sorted(aliases)]
    out += [
        f"from {identifiers_module} import {name} as {name}"
        for name in sorted(set(enum_aliases.values()))
    ]
    out += [
        "",
        "def _required[T](value: T | None, field: str, result_class: str, operation: str) -> T:",
        "    if value is None:",
        "        raise NativeResultViolation(operation, result_class, field)",
        "    return value",
        "",
    ]
    for _, call in calls:
        for record in call.records:
            if record.name in emitted:
                continue
            emitted.add(record.name)
            out += ["", f"class {record.name}(OperationResult):"]
            out += [f"    {f.name}: {field_type(f)}" for f in record.fields]
    for operation, call in calls:
        row_types = []
        name = call.id
        json_text = call.json_read == "json-text-v1"
        request_class = (
            "".join(part.capitalize() for part in name.split("_")) + "Parameters"
            if call.batch
            else f"_{name}Request"
        )
        if (
            operation.startswith("data.")
            and any(field.source == "native-wire" for field in call.parameters)
            and not call.wire_contract_digest
        ):
            raise ValueError("DDO native wire call lacks its captured installed wire contract")
        if call in structural:
            if (
                len(call.parameters) != 1
                or len(call.result_fields) != 1
                or call.result_mode != "json"
            ):
                raise ValueError("structural native call requires the fixed JSON envelope")
            parameter, result = call.parameters[0], call.result_fields[0]
            installed_contract = call.wire_contract_digest
            if operation.startswith("data.") and installed_contract is None:
                raise ValueError("DDO structural call lacks its captured installed wire contract")
            request_schema, result_schema = (
                json.loads(field.wire_schema) for field in (parameter, result)
            )
            request_annotation = wire_type_name(
                request_schema["$ref"].removeprefix("#/definitions/")
            )
            result_type = wire_type_name(result_schema["$ref"].removeprefix("#/definitions/"))
            digest = sha256(canonical_bytes([asdict(call)])).hexdigest()
            boundary_input = (
                wire_schemas[call.id]["input"]
                if wire_schemas
                else canonical_bytes(
                    {
                        "type": "object",
                        "properties": {parameter.name: {"$ref": request_schema["$ref"]}},
                        "required": [parameter.name],
                        "additionalProperties": False,
                        "definitions": definitions,
                    }
                )
            )
            boundary_output = (
                wire_schemas[call.id]["output"]
                if wire_schemas
                else canonical_bytes(
                    {
                        "type": "object",
                        "properties": {result.name: {"$ref": result_schema["$ref"]}},
                        "required": [result.name],
                        "additionalProperties": False,
                        "definitions": definitions,
                    }
                )
            )
            out += [
                "",
                f"{name.upper()}_CONTRACT_DIGEST = {digest!r}",
                "",
                f"class {request_class}(TypedDict):",
                f"    {parameter.name}: {request_annotation}",
                "",
                f"class {call.result_class}(TypedDict):",
                f"    {result.name}: {result_type}",
                "",
                *(
                    []
                    if installed_contract
                    else [f"_{name}_validate_input = prepare_wire_schema({boundary_input!r})"]
                ),
                f"_{name}_validate_output = prepare_wire_schema({boundary_output!r})",
                "",
                f"_{name}_statement = select(func.{call.symbol}(",
                f"    bindparam({parameter.name!r}, type_=Text()).cast(JSONB()),",
                ").cast(Text()))",
                "",
                f"def prepare_{name}(*,",
                f"    {parameter.name}: {request_annotation},",
                "    projection_context: PreparedRelease,"
                if call.requires_context
                else "    projection_context: PreparedRelease | None = None,",
                ") -> Select[str]:",
            ]
            if call.requires_context:
                out += [context_check("    ", operation, name)]
            else:
                out += [
                    "    if projection_context is not None:",
                    context_check("        ", operation, name),
                ]
            out += [
                *(
                    [
                        f"    return _{name}_statement.params({parameter.name}=encode_native_wire_request({parameter.name}))"
                    ]
                    if installed_contract
                    else [
                        f"    checked = _{name}_validate_input({{{parameter.name!r}: {parameter.name}}})",
                        f"    return _{name}_statement.params({parameter.name}=json_bytes(checked[{parameter.name!r}]).decode())",
                    ]
                ),
                "",
                f"def {name}(conn: Connection, *,",
                f"    {parameter.name}: {request_annotation},",
                "    projection_context: PreparedRelease,"
                if call.requires_context
                else "    projection_context: PreparedRelease | None = None,",
                f") -> {call.result_class}:",
                f"    statement = prepare_{name}({parameter.name}={parameter.name}, projection_context=projection_context)",
                f"    with native_result_scope({operation!r}, {call.result_class!r}):",
                "        encoded = conn.scalar(statement)",
                "        value = wire_json_loads(encoded)",
                *(
                    [
                        "        if not isinstance(value, dict) or set(value) != {'payload', 'contract_digest'}:",
                        "            raise ValueError('native data operation returned a malformed fixed envelope')",
                        f"        if value['contract_digest'] != {installed_contract!r}:",
                        "            raise ValueError('native installed wire contract differs from the captured client')",
                        "        value = {'payload': value['payload']}",
                    ]
                    if installed_contract
                    else []
                ),
                f"        return cast({call.result_class}, _{name}_validate_output(value))",
            ]
            continue
        out += [
            "",
            f"{name.upper()}_CONTRACT_DIGEST = "
            + repr(sha256(canonical_bytes([asdict(call)])).hexdigest()),
        ]
        if call.result_class and call.result_class not in emitted:
            emitted.add(call.result_class)
            out += [""]
            if call.result_mode == "void":
                out += ["@dataclass(frozen=True)"]
            out += [
                f"class {call.result_class}"
                + (
                    ":"
                    if call.result_mode == "void"
                    else "(NativeRowResult):"
                    if call.result_mode == "table" or json_text
                    else "(OperationResult):"
                )
            ]
            if wire_schemas and (schema := wire_schemas.get(call.id, {}).get("output")) is not None:
                out += [
                    f"    __wire_schema__: ClassVar[bytes | None] = {schema!r}",
                    "    __wire_validation__: ClassVar[tuple[bytes, Callable[[Any], Any]] | None] = "
                    "(cast(bytes, __wire_schema__), prepare_wire_schema(cast(bytes, __wire_schema__)))",
                ]
            json_fields = tuple(
                f.name
                for f in call.result_fields
                if json_text and f.resolved.kind == "json_payload"
            )
            if json_fields:
                out += [f"    __json_fields__ = {json_fields!r}"]
            out += [
                f"    {f.name}: {field_type(f, json_text=json_text)}" for f in call.result_fields
            ]
        out += ["", f"class {request_class}(OperationResult):"]
        if wire_schemas and (schema := wire_schemas.get(call.id, {}).get("input")) is not None:
            out += [
                f"    __wire_schema__: ClassVar[bytes | None] = {schema!r}",
                "    __wire_validation__: ClassVar[tuple[bytes, Callable[[Any], Any]] | None] = "
                "(cast(bytes, __wire_schema__), prepare_wire_schema(cast(bytes, __wire_schema__)))",
            ]
        out += [
            f"    {f.name}: {request_type(f)}"
            + ("" if f.default_json is None else " = " + repr(json.loads(f.default_json)))
            for f in call.parameters
        ]
        if not call.parameters:
            out += ["    pass"]
        if call.backend == "core":
            parameter_lines = [f"    {f.name}: {field_type(f)}," for f in call.parameters]
            context_line = (
                "    projection_context: PreparedRelease,"
                if call.requires_context
                else "    projection_context: PreparedRelease | None = None,"
            )
            out += ["", f"def prepare_{name}(*,"]
            out += [*parameter_lines, context_line, f") -> {request_class}:"]
            out += [f"    _request = {request_class}("]
            out += [f"        {f.name}={f.name}," for f in call.parameters]
            out += ["    )"]
            if not call.requires_context:
                out += ["    if projection_context is not None:"]
            indent = "    " if call.requires_context else "        "
            out += [
                context_check(indent, operation, name),
                "    return _request",
            ]
            groups = {}
            for field in call.parameters:
                if field.source.startswith("physical:"):
                    relation, native = field.source.removeprefix("physical:").rsplit(".", 1)
                    groups.setdefault(relation, []).append((native, field))
            for relation, fields in groups.items():
                suffix = relation.replace(".", "_")
                values_class = (
                    "".join(part[0].upper() + part[1:] for part in (name + "_" + suffix).split("_"))
                    + "Values"
                )
                out += ["", f"class {values_class}(TypedDict):"]
                out += [
                    f"    {native}: {field_type(f)}"
                    + (
                        " | ColumnElement[None]"
                        if f.nullable and f.resolved.kind == "json_payload"
                        else ""
                    )
                    for native, f in fields
                ]
                out += [
                    "",
                    f"def values_{name}_{suffix}(request: {request_class}) -> {values_class}:",
                    "    return {",
                ]
                out += [
                    f"        {native!r}: "
                    + (
                        f"null() if request.{f.name} is None else request.{f.name}"
                        if f.nullable and f.resolved.kind == "json_payload"
                        else f"request.{f.name}"
                    )
                    + ","
                    for native, f in fields
                ]
                out += ["    }"]
                out += ["", f"class {values_class}Expected(TypedDict):"]
                out += [
                    f"    {native}: {field_type(f)}"
                    + (" | SqlNull" if f.nullable and f.resolved.kind == "json_payload" else "")
                    for native, f in fields
                ]
                out += [
                    "",
                    f"def expected_{name}_{suffix}(request: {request_class}) "
                    f"-> {values_class}Expected:",
                    "    return {",
                ]
                out += [
                    f"        {native!r}: "
                    + (
                        f"SQL_NULL if request.{f.name} is None else request.{f.name}"
                        if f.nullable and f.resolved.kind == "json_payload"
                        else f"request.{f.name}"
                    )
                    + ","
                    for native, f in fields
                ]
                out += ["    }"]
            column_types = [column_type(f, json_text=json_text) for f in call.result_fields]
            row_types = [
                raw_type(f, native=True, json_text=json_text)
                + (" | None" if f.resolved.nullable else "")
                for f in call.result_fields
            ]
            result_relations = {}
            for field in call.result_fields:
                if not field.source.startswith("physical:"):
                    raise ValueError("Core result projection requires a physical source field")
                relation, native = field.source.removeprefix("physical:").rsplit(".", 1)
                result_relations.setdefault(relation, {})[native] = field
            views = {}
            for relation, fields in result_relations.items():
                suffix = relation.replace(".", "_")
                columns_class = f"_{name}_{suffix}Columns"
                if metadata is not None:
                    from corpus_structure.schema.relational import render_typed_column_class

                    declaration = render_typed_column_class(
                        columns_class,
                        (metadata.tables[relation].c[native] for native in fields),
                        bindings={native: column_type(f) for native, f in fields.items()},
                    ).rstrip()
                else:
                    declaration = "\n".join(
                        [
                            f"class {columns_class}(TypedColumns):",
                            *[
                                f"    {native}: Named[{raw_type(f, native=True)}"
                                + (" | None" if f.resolved.nullable else "")
                                + "]"
                                for native, f in fields.items()
                            ],
                        ]
                    )
                out += ["", declaration]
                protocol = columns_class + "Protocol"
                out += [
                    "",
                    declaration.replace(
                        columns_class + "(TypedColumns)", protocol + "(Protocol)"
                    ).replace("Named[", "Column["),
                ]
                view = f"_{name}_{suffix}"
                views[relation] = view + "_columns"
                out += [
                    "",
                    f"{view} = _core_table({relation!r}).with_cols({columns_class})",
                    f"{view}_columns = cast({protocol}, {view}.c)",
                ]
            out += [
                "",
                f"projection_{name}: tuple["
                + ", ".join(f"ColumnElement[{typ}]" for typ in column_types)
                + "] = (",
            ]
            for field in call.result_fields:
                relation, native = field.source.removeprefix("physical:").rsplit(".", 1)
                value = f"{views[relation]}.{native}"
                if json_text and field.resolved.kind == "json_payload":
                    value += ".cast(Text())"
                    if field.resolved.nullable:
                        # SQL CAST preserves a SQL NULL; SQLAlchemy's Text generic omits it.
                        value = f"cast(ColumnElement[str | None], {value})"
                out += [f"    {value}.label({field.name!r}),"]
            out += [")"]
            result_type = call.result_class or field_type(
                call.result_fields[0], json_text=json_text
            )
            if not call.result_class:
                out += ["", f"_{name}_adapter = TypeAdapter({result_type})"]
            out += [
                "",
                f"def materialize_{name}(row: tuple[{', '.join(row_types)}]) -> {result_type}:",
                f"    with native_result_scope({operation!r}, {result_type!r}):",
            ]
            if call.result_class:
                out += [f"        return {call.result_class}("]
                out += [
                    f"            {f.name}="
                    f"{convert(f, f'row[{i}]', operation, call.result_class, json_text=json_text)},"
                    for i, f in enumerate(call.result_fields)
                ]
                out += ["        )"]
            else:
                out += [f"        return _{name}_adapter.validate_python(row[0], strict=True)"]
            collected = (
                f"tuple[{result_type}, ...]"
                if call.cardinality == "many"
                else result_type + " | None"
                if call.cardinality == "optional"
                else result_type
            )
            out += [
                "",
                f"def collect_{name}(result: Result[{', '.join(column_types)}]) -> {collected}:",
                f"    with native_result_scope({operation!r}, {result_type!r}):",
            ]
            if call.cardinality == "many":
                out += [f"        return tuple(materialize_{name}(row) for row in result)"]
            elif call.cardinality == "optional":
                out += [
                    "        row = result.one_or_none()",
                    f"        return None if row is None else materialize_{name}(row)",
                ]
            else:
                out += [f"        return materialize_{name}(result.one())"]
            continue
        out += ["", f"_{name}_function = func.{call.symbol}("]
        out += [f"    bindparam({f.name!r}, type_={sql_type(f)})," for f in call.parameters]
        if call.result_mode == "table":
            native_names = [
                f.native_field or f.source.rsplit(".", 1)[-1] for f in call.result_fields
            ]
            out += [").table_valued("]
            out += [
                f"    column({n!r}, {sql_type(f)}),"
                for n, f in zip(native_names, call.result_fields, strict=True)
            ]
            out += [")", "", f"class _{name}Columns(Protocol):"]
            for n, f in zip(native_names, call.result_fields, strict=True):
                annotation = column_type(f)
                out += [f"    {n}: Column[{annotation}]"]
            out += [
                "",
                f"_{name}_columns = cast(_{name}Columns, _{name}_function.c)",
                f"_{name}_statement = select(",
            ]
            out += [
                f"    _{name}_columns.{n}.cast(Text()).label({n!r}),"
                if json_text and f.resolved.kind == "json_payload"
                else f"    _{name}_columns.{n},"
                for n, f in zip(native_names, call.result_fields, strict=True)
            ]
            out += [")"]
            if call.order_by:
                out[-1] += ".order_by("
                for public in call.order_by:
                    index = next(i for i, f in enumerate(call.result_fields) if f.name == public)
                    suffix = (
                        '.collate("C")'
                        if call.result_fields[index].resolved.kind == "string"
                        else ""
                    )
                    out += [f"    _{name}_columns.{native_names[index]}{suffix},"]
                out += [")"]
            row_types = [
                raw_type(f, native=True, json_text=json_text)
                + (
                    " | None"
                    if f.resolved.nullable and (f.resolved.kind != "json_payload" or json_text)
                    else ""
                )
                for f in call.result_fields
            ]
            out += [
                "",
                f"def _{name}_result(row: tuple[{', '.join(row_types)}]) -> {call.result_class}:",
                f"    with native_result_scope({operation!r}, {call.result_class!r}):",
                f"        return {call.result_class}(",
            ]
            out += [
                f"            {f.name}="
                f"{convert(f, f'row[{i}]', operation, call.result_class, json_text=json_text)},"
                for i, f in enumerate(call.result_fields)
            ]
            out += ["        )"]
        else:
            if call.result_mode == "scalar":
                out += [f"    type_={sql_type(call.result_fields[0])},"]
            elif call.result_mode == "json":
                out += ["    type_=JSONB(),"]
            expression = f"_{name}_function"
            if call.result_mode == "json" or (
                json_text and call.result_fields[0].resolved.kind == "json_payload"
            ):
                expression += ".cast(Text())"
            out += [")", f"_{name}_statement = select({expression})"]
        if call.result_class:
            result_type = call.result_class
        elif call.result_fields:
            result_type = field_type(call.result_fields[0], json_text=json_text)
        else:
            result_type = "None"
        if call.cardinality == "many":
            result_type = f"tuple[{result_type}, ...]"
        elif call.cardinality == "optional":
            result_type += " | None"
        parameter_lines = [
            f"    {f.name}: {field_type(f)}"
            + ("" if f.default_json is None else " = " + repr(json.loads(f.default_json)))
            + ","
            for f in call.parameters
        ]
        context_line = (
            "    projection_context: PreparedRelease,"
            if call.requires_context
            else "    projection_context: PreparedRelease | None = None,"
        )
        native_types = (
            [column_type(f, json_text=json_text) for f in call.result_fields]
            if call.result_mode == "table"
            else ["None"]
            if call.result_mode == "void"
            else ["str"]
            if call.result_mode == "json"
            else [
                raw_type(call.result_fields[0], native=True, json_text=json_text)
                + (" | None" if call.result_fields[0].nullable else "")
            ]
        )
        out += ["", f"def prepare_{name}(*,"]
        out += [
            *parameter_lines,
            context_line,
            f") -> Select[{', '.join(native_types)}]:",
            f"    _request = {request_class}(",
        ]
        out += [f"        {f.name}={f.name}," for f in call.parameters]
        out += ["    )"]
        if call.requires_context:
            out += [context_check("    ", operation, name)]
        else:
            out += [
                "    if projection_context is not None:",
                context_check("        ", operation, name),
            ]
        needs_cast = (call.result_mode == "table" and len(call.result_fields) > 9) or (
            call.result_mode == "scalar"
            and call.result_fields[0].resolved.kind == "json_payload"
            and not json_text
        )
        prefix = f"cast(Select[{', '.join(native_types)}], " if needs_cast else ""
        out += [f"    return {prefix}_{name}_statement.params(**{{"]
        out += [f"        {f.name!r}: _request.{f.name}," for f in call.parameters]
        out += ["    }))" if needs_cast else "    })"]
        if call.result_mode == "table":
            out += ["", f"materialize_{name} = _{name}_result"]
        elif call.result_mode == "scalar":
            field = call.result_fields[0]
            value_type = field_type(field, json_text=json_text)
            row_type = native_types[0]
            if call.cardinality == "optional" and "None" not in row_type:
                row_type += " | None"
            materialized_type = call.result_class or value_type
            if call.cardinality == "optional":
                materialized_type += " | None"
            out += [
                "",
                f"_{name}_adapter = TypeAdapter({value_type})",
                "",
                f"def materialize_{name}(row: tuple[{row_type}]) -> {materialized_type}:",
                f"    with native_result_scope({operation!r}, "
                f"{call.result_class or call.id!r}, {field.name!r}):",
            ]
            if call.cardinality == "optional":
                out += ["        if row[0] is None:", "            return None"]
            out += [
                f"        checked = _{name}_adapter.validate_python(row[0], strict=True)",
                f"        return {call.result_class}({field.name}=checked)"
                if call.result_class
                else "        return checked",
            ]
        out += ["", f"def {name}(conn: Connection, *,"]
        out += [*parameter_lines, context_line, f") -> {result_type}:"]
        out += [f"    _statement = prepare_{name}("]
        out += [f"        {f.name}={f.name}," for f in call.parameters]
        out += [
            "        projection_context=projection_context,",
            "    )",
            "    _native_result = conn.execute(_statement)",
        ]
        if call.result_mode == "table":
            out += [f"    with native_result_scope({operation!r}, {call.result_class!r}):"]
            if call.cardinality == "many":
                out += [f"        return tuple(_{name}_result(row) for row in _native_result)"]
            elif call.cardinality == "one":
                out += [f"        return _{name}_result(_native_result.one())"]
            else:
                out += [
                    "        row = _native_result.one_or_none()",
                    f"        return None if row is None else _{name}_result(row)",
                ]
        elif call.result_mode == "json":
            out += [
                f"    with native_result_scope({operation!r}, {call.result_class!r}):",
                "        value = _native_result.scalar_one()",
                f"        return {call.result_class}.model_validate_json(value, strict=True)",
            ]
        elif call.result_mode == "void":
            out += [
                f"    with native_result_scope({operation!r}, {call.result_class or call.id!r}):",
                "        _native_result.scalar_one()",
            ]
            if call.result_class:
                out += [f"    return {call.result_class}("]
                out += [
                    f"        {f.name}={f.source.removeprefix('parameter:')},"
                    for f in call.result_fields
                ]
                out += ["    )"]
            else:
                out += ["    return None"]
        else:
            if call.cardinality == "many":
                out += [
                    f"    with native_result_scope({operation!r}, "
                    f"{call.result_class or call.id!r}):",
                    f"        return tuple(materialize_{name}(row) for row in _native_result)",
                ]
                continue
            out += [
                f"    with native_result_scope({operation!r}, {call.result_class or call.id!r}):",
                "        row = _native_result.one_or_none()"
                if call.cardinality == "optional"
                else "        row = _native_result.one()",
            ]
            if call.cardinality == "optional":
                out += ["        if row is None:", "            return None"]
            out += [f"        return materialize_{name}(row)"]
        if call.batch:
            out += [
                "",
                f"def {name}_batch(conn: Connection, *,",
                f"    requests: Sequence[{request_class}],",
                "    projection_context: PreparedRelease | None = None,",
                ") -> None:",
                "    if projection_context is not None:",
                context_check("        ", operation, name),
                "    if not requests:",
                "        return",
                f"    conn.execute(_{name}_statement, [{{",
            ]
            out += [f"        {f.name!r}: request.{f.name}," for f in call.parameters]
            out += ["    } for request in requests])"]
    out += [
        "",
        "CALL_CONTRACT_DIGEST = "
        + repr(sha256(canonical_bytes([asdict(call) for _, call in calls])).hexdigest()),
        "",
    ]
    return "\n".join(out)
