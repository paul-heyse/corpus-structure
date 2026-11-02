"""Generate fixed native calls and positional materializers from the owned call contract."""

from __future__ import annotations

import json
import keyword
from dataclasses import asdict, replace
from hashlib import sha256
from typing import Any

import yaml
from linkml_runtime.utils.yamlutils import DupCheckYamlLoader

from .identity import canonical_bytes

_PRIMITIVES = {
    "integer": "int",
    "boolean": "bool",
    "string": "str",
    "timestamp": "datetime",
    "json_payload": "JsonValue",
    "bytes": "bytes",
    "decimal": "Decimal",
    "float": "float",
}
_TRANSFORMS = {
    "task_unit_type": "physical:ops.task.unit_type",
    "held_progress": "physical:ops.task.error",
}


def _integer_bounds(field):
    bits = 32 if field.native_type == "integer" else 64
    return -(1 << (bits - 1)), (1 << (bits - 1)) - 1


def _source_view(inputs):
    """Resolve supplied model modules, including package data acquired at the entry point."""
    from linkml_runtime.dumpers import json_dumper
    from linkml_runtime.linkml_model.meta import SchemaDefinition
    from linkml_runtime.loaders import yaml_loader
    from linkml_runtime.utils.schemaview import SchemaView

    from .contracts import _fail

    artifacts = {item.name: item.content for item in inputs.implementations}
    names = {
        "physical": "pdf/record-physical.yaml",
        "read_projections": "pdf/read-projections.yaml",
        "pdf_records": "pdf/record-model.yaml",
        "pdf_staging": "pdf/staging-model.yaml",
        "companion_projections": "capture/companion-projection-model.yaml",
        "linkml:types": "unified/linkml-types.yaml",
    }
    aliases = {
        "pdf-records": "pdf_records",
        "pdf-staging": "pdf_staging",
        "pdf-products": "pdf_products",
        "companion-projections": "companion_projections",
    }
    supplied = {item.name: item.content for item in inputs.schema.sources}
    for name, artifact in names.items():
        if artifact not in artifacts:
            _fail("operation_source", artifact, "required source module is unavailable")
        supplied[name] = artifacts[artifact]
    schemas = {}
    try:
        for name, content in supplied.items():
            body = yaml.load(content, Loader=DupCheckYamlLoader)
            if not isinstance(body, dict):
                _fail("operation_source", name, "source module must be a mapping")
            body["imports"] = [aliases.get(str(i), str(i)) for i in body.get("imports", ())]
            prefix = body.get("default_prefix")
            for cls in body.get("classes", {}).values():
                for attr_name, attr in cls.get("attributes", {}).items():
                    attr.setdefault("range", body.get("default_range", "string"))
                    attr.setdefault(
                        "slot_uri",
                        f"{prefix}:{attr_name}" if prefix else body["id"] + "/" + attr_name,
                    )
            schema = yaml_loader.load(body, SchemaDefinition)
            if not isinstance(schema, SchemaDefinition):
                _fail("operation_source", name, "source must define a schema")
            schemas[name] = schema
    except (ValueError, TypeError, yaml.YAMLError) as exc:
        _fail("operation_source", "operations/calls", str(exc))
    for name, schema in schemas.items():
        for imported in schema.imports or ():
            if str(imported) not in schemas:
                _fail("operation_source", name, "undeclared import " + str(imported))
    root = SchemaDefinition(
        id="urn:corpus:operation-sources", name="operation_sources", imports=list(schemas)
    )
    schemas["operation_sources"] = root
    importmap: dict[str, dict[str, Any] | str] = {}
    for name, schema in schemas.items():
        entry = json_dumper.to_dict(schema)
        if not isinstance(entry, dict):
            _fail("operation_source", name, "serialized schema must be a mapping")
        importmap[str(name)] = dict(entry)
    view = SchemaView(root, importmap=importmap)
    view.merge_imports()
    merged = view.schema
    if merged is None:
        _fail("operation_source", "operations/calls", "merged source schema is unavailable")
    merged.imports = []
    return SchemaView(merged)


def _kind(view, name, trail=()):
    from corpus_structure.schema.model import ci_annotations

    from .contracts import _fail

    enum = view.get_enum(name)
    if enum is not None:
        return "string", tuple(sorted(str(value) for value in enum.permissible_values))
    if view.get_class(name) is not None:
        return "json_payload", ()
    if name in trail:
        _fail("operation_source", name, "cyclic value type")
    typ = view.get_type(name)
    if typ is not None:
        sql = ci_annotations(typ).get("ph:sql_type")
        if sql in {"jsonb", "bytea", "numeric", "timestamptz"}:
            return {
                "jsonb": "json_payload",
                "bytea": "bytes",
                "numeric": "decimal",
                "timestamptz": "timestamp",
            }[sql], ()
        uri = str(typ.uri or "")
        for ending, kind in (
            ("string", "string"),
            ("integer", "integer"),
            ("long", "integer"),
            ("boolean", "boolean"),
            ("decimal", "decimal"),
            ("double", "float"),
            ("float", "float"),
            ("dateTime", "timestamp"),
        ):
            if uri.endswith(":" + ending) or uri.endswith("#" + ending):
                return kind, ()
        if typ.typeof:
            return _kind(view, str(typ.typeof), (*trail, name))
    if name in _PRIMITIVES:
        return name, ()
    _fail("operation_source", name, "unsupported value representation")


def validate_call_bindings(model, inputs):
    """Compile qualified fixed variants from explicit field references and closed sources."""
    from corpus_structure.schema.model import ci_annotations

    from .contracts import OperationFieldBinding, OperationFieldType, OperationRecordBinding, _fail

    view = _source_view(inputs)
    aliases, identifiers, result_shapes = {}, set(), {}
    # Reuse the identifier owned by an explicit physical correspondence, including
    # through model projections. Nested records must retain the same distinctions.
    semantic_sources = {}
    for operation in model.operations:
        for call in operation.calls:
            for field in (*call.parameters, *call.result_fields):
                if field.semantic_type and field.source.startswith("physical:"):
                    previous = semantic_sources.setdefault(field.source, field.semantic_type)
                    if previous != field.semantic_type:
                        _fail("operation_field", field.source, "semantic identifiers differ")

    def model_field(name, slot):
        reference = f"model:{name}.{slot.name}"
        source = reference
        seen = set()
        while source.startswith("model:"):
            if source in seen:
                _fail("operation_source", reference, "cyclic model field projection")
            seen.add(source)
            cls, field_name = source.removeprefix("model:").split(".")
            owner = next(s for s in view.class_induced_slots(cls) if s.name == field_name)
            source = ci_annotations(owner).get("cp:source", "")
        return OperationFieldBinding(
            str(slot.name), reference, False, semantic_type=semantic_sources.get(source)
        )

    def resolve(field, parameters, stack=()):
        reference = field.source
        if reference in stack:
            _fail("operation_source", reference, "cyclic field projection")
        if reference.startswith("parameter:"):
            original = parameters.get(reference.removeprefix("parameter:"))
            if original is None or original.resolved is None:
                _fail("operation_source", reference, "local receipt parameter is unavailable")
            return original.resolved, {
                "parameter": original.source,
                "type": asdict(original.resolved),
            }
        if reference.startswith("primitive:"):
            kind = reference.removeprefix("primitive:")
            if kind not in _PRIMITIVES:
                _fail("operation_source", reference, "unsupported primitive parameter")
            resolved = OperationFieldType(kind, field.nullable, field.multivalued)
            return resolved, asdict(resolved)
        if reference.startswith("physical:"):
            parts = reference.removeprefix("physical:").split(".")
            if len(parts) != 3:
                _fail("operation_source", reference, "physical source must be qualified")
            schema, cls, name = parts
            definition = view.get_class(cls)
            if definition is None or schema not in (definition.in_subset or ()):
                _fail("operation_source", reference, "physical source relation is unavailable")
        elif reference.startswith("model:"):
            parts = reference.removeprefix("model:").split(".")
            if len(parts) != 2:
                _fail("operation_source", reference, "model field source must be qualified")
            cls, name = parts
        else:
            _fail("operation_source", reference, "unsupported field reference")
        slot = next((s for s in view.class_induced_slots(cls) if s.name == name), None)
        if slot is None:
            _fail("operation_field", reference, "physical source field is unavailable")
        annotations = ci_annotations(slot)
        if parent := annotations.get("cp:source"):
            resolved, source = resolve(
                replace(field, source=parent), parameters, (*stack, reference)
            )
            constraints = {
                "required": slot.required,
                "value_presence": str(slot.value_presence) if slot.value_presence else None,
                "minimum_cardinality": slot.minimum_cardinality,
            }
            return resolved, {
                "projection": reference,
                "source": source,
                **{key: value for key, value in constraints.items() if value is not None},
            }
        kind, members = _kind(view, str(slot.range))
        multiple = bool(field.multivalued or slot.multivalued) and kind != "json_payload"
        required = bool(
            slot.required
            or slot.identifier
            or (slot.minimum_cardinality or 0) > 0
            or str(slot.value_presence) == "PRESENT"
        )
        model_class = str(slot.range) if view.get_class(str(slot.range)) is not None else None
        resolved = OperationFieldType(kind, not required, multiple, members, model_class)
        return resolved, {
            "reference": reference,
            "uri": view.get_uri(slot, expand=True),
            "range": str(slot.range),
            "type": asdict(resolved),
            "minimum": str(slot.minimum_value) if slot.minimum_value is not None else None,
            "maximum": str(slot.maximum_value) if slot.maximum_value is not None else None,
            "pattern": slot.pattern,
        }

    def resolve_fields(fields, parameters, location, *, parameter, backend="native"):
        if len({f.name for f in fields}) != len(fields):
            _fail("operation_field", location, "operation fields repeat a name")
        resolved_fields, sources = [], {}
        for field in fields:
            if not field.name.isidentifier() or keyword.iskeyword(field.name):
                _fail("operation_field", location, "invalid field name")
            if parameter and (
                field.name.startswith("_")
                or field.name in {"conn", "projection_context"}
                or (
                    backend == "native"
                    and (not field.native_parameter or not field.native_parameter.isidentifier())
                )
            ):
                _fail("operation_field", location, "native parameter correspondence is required")
            if backend == "core" and field.native_parameter is not None:
                _fail("operation_field", location, "Core fields cannot name native parameters")
            if not parameter and field.native_parameter is not None:
                _fail("operation_field", location, "result cannot declare a native input parameter")
            if field.native_field is not None and not field.native_field.isidentifier():
                _fail("operation_field", location, "invalid native result field")
            typ, source = resolve(field, parameters)
            if field.native_type is not None and (
                not parameter or typ.kind != "integer" or typ.multivalued
            ):
                _fail(
                    "operation_field", location, "native integer width needs one integer parameter"
                )
            if field.resolved is not None and field.resolved != typ:
                _fail("operation_source", location, "resolved field representation differs")
            if field.transform not in {None, "identity"}:
                if (
                    parameter
                    or _TRANSFORMS.get(field.transform) != field.source
                    or field.semantic_type
                ):
                    _fail("operation_transform", location, "unqualified transform source/type")
                if field.transform == "held_progress" and not field.nullable:
                    _fail("operation_transform", location, "held progress is optional")
            if field.semantic_type:
                name = field.semantic_type
                if (
                    not name.isidentifier()
                    or keyword.iskeyword(name)
                    or name.startswith("_")
                    or name
                    in {
                        *_PRIMITIVES.values(),
                        "Connection",
                        "Column",
                        "Protocol",
                        "NewType",
                        "JsonValue",
                        "TaskUnitType",
                        "OperationResult",
                        "HeldProgress",
                    }
                ):
                    _fail("operation_field", location, "invalid semantic identifier")
                if (
                    typ.multivalued
                    or typ.enum_values
                    or typ.model_class
                    or typ.kind == "json_payload"
                ):
                    _fail("operation_field", location, "semantic identifier must encode one scalar")
                if name in aliases and aliases[name] != typ.kind:
                    _fail("operation_field", location, "semantic identifier encodings differ")
                aliases[name] = typ.kind
            if field.default_json is not None:
                if not parameter:
                    _fail("operation_default", location, "results cannot declare defaults")
                try:
                    default = json.loads(field.default_json)
                except ValueError:
                    _fail("operation_default", location, "default must be exact JSON")
                expected = {"integer": int, "string": str, "boolean": bool}.get(typ.kind)
                if not (default is None and field.nullable) and (
                    typ.multivalued or expected is None or type(default) is not expected
                ):
                    _fail("operation_default", location, "default differs from source type")
                if type(default) is int:
                    lower, upper = _integer_bounds(field)
                    if not lower <= default <= upper:
                        _fail("operation_default", location, "default exceeds native integer width")
            resolved_fields.append(replace(field, resolved=typ))
            sources[field.source] = source
        return tuple(resolved_fields), sources

    def projected_nullable(slot, resolved):
        if ci_annotations(slot).get("cp:source"):
            if slot.required is not None:
                return not slot.required
            if (
                slot.identifier
                or (slot.minimum_cardinality or 0) > 0
                or str(slot.value_presence) == "PRESENT"
            ):
                return False
        return resolved.nullable

    operations = []
    for operation in model.operations:
        calls = []
        for call in operation.calls:
            location = "operations/" + operation.id + "/calls/" + call.id
            if call.id in identifiers or not call.id.isidentifier() or keyword.iskeyword(call.id):
                _fail("operation_call", location, "call identifier must be unique and valid")
            identifiers.add(call.id)
            parts = call.symbol.split(".")
            if call.backend == "native" and (
                len(parts) != 2
                or parts[0] not in {"ops", "data", "sem", "eval"}
                or not all(p.isidentifier() for p in parts)
            ):
                _fail("operation_call", location, "native symbol must be qualified")
            if operation.implementation is None:
                _fail(
                    "operation_call", location, "fixed call needs its trusted implementation owner"
                )
            if call.backend == "core":
                binding = next(i for i in model.implementations if i.id == operation.implementation)
                if call.symbol != binding.owner + "." + binding.symbol:
                    _fail("operation_call", location, "Core symbol differs from its trusted owner")
                if call.result_mode not in {"table", "scalar"} or call.batch:
                    _fail("operation_call", location, "Core boundaries support fixed rows/scalars")
            if call.backend == "native" and (
                len({p.native_parameter for p in call.parameters}) != len(call.parameters)
            ):
                _fail("operation_field", location, "native parameters repeat a name")
            parameters, sources = resolve_fields(
                call.parameters, {}, location, parameter=True, backend=call.backend
            )
            if call.backend == "core":
                sources["core_owner"] = call.symbol
            parameter_map = {p.name: p for p in parameters}
            fields = call.result_fields
            result_class = call.result_class
            if call.result_source:
                if not call.result_source.startswith("model:"):
                    _fail("operation_source", location, "result source must identify a model class")
                cls = call.result_source.removeprefix("model:")
                if view.get_class(cls) is None:
                    _fail("operation_source", location, "result source class is unavailable")
                derived = []
                for slot in view.class_induced_slots(cls):
                    field = model_field(cls, slot)
                    typ, _ = resolve(field, parameter_map)
                    derived.append(replace(field, nullable=projected_nullable(slot, typ)))
                if fields and tuple(replace(f, resolved=None) for f in fields) != tuple(derived):
                    _fail(
                        "operation_source",
                        location,
                        "result source has independently authored fields",
                    )
                fields = tuple(derived)
                result_class = result_class or cls
            results, result_sources = resolve_fields(
                fields, parameter_map, location, parameter=False
            )
            sources.update(result_sources)
            records = {}

            def record(name, records, parameter_map, sources, location, trail=()):
                if name in trail:
                    _fail("operation_source", location, "recursive result models are unsupported")
                if name in records:
                    return
                fields = []
                for slot in view.class_induced_slots(name):
                    field = model_field(name, slot)
                    typ, _ = resolve(field, parameter_map)
                    fields.append(replace(field, nullable=projected_nullable(slot, typ)))
                resolved, record_sources = resolve_fields(
                    fields, parameter_map, location, parameter=False
                )
                sources.update(record_sources)
                for field in resolved:
                    if field.resolved.model_class:
                        record(
                            field.resolved.model_class,
                            records,
                            parameter_map,
                            sources,
                            location,
                            (*trail, name),
                        )
                records[name] = OperationRecordBinding(name, resolved)

            for field in results:
                if field.resolved.model_class:
                    record(field.resolved.model_class, records, parameter_map, sources, location)
            resolved_records = tuple(records.values())
            if call.records and call.records != resolved_records:
                _fail("operation_source", location, "resolved nested result models differ")
            if call.result_mode == "table":
                if not results or call.cardinality == "none" or result_class is None:
                    _fail("operation_result", location, "table calls need a concrete row result")
                if any(f.source.startswith("parameter:") for f in results):
                    _fail("operation_result", location, "native rows cannot be local receipts")
                native_names = [f.native_field or f.source.rsplit(".", 1)[-1] for f in results]
                if len(set(native_names)) != len(native_names):
                    _fail("operation_result", location, "native result names repeat")
            elif call.result_mode == "scalar":
                if len(results) != 1 or call.cardinality not in {"one", "optional", "many"}:
                    _fail("operation_result", location, "scalar result needs one field")
            elif call.result_mode == "json":
                if not call.result_source or not result_class or call.cardinality != "one":
                    _fail("operation_result", location, "JSON result needs one model-bound object")
            elif call.result_mode == "void":
                if any(
                    not f.source.startswith("parameter:") for f in results
                ) or call.cardinality not in {"one", "none"}:
                    _fail(
                        "operation_result", location, "void result may only project a local receipt"
                    )
                if bool(results) != bool(result_class) or (
                    not results and call.cardinality != "none"
                ):
                    _fail("operation_result", location, "void receipt shape/cardinality differs")
            if call.batch and (call.result_mode != "void" or call.cardinality != "none"):
                _fail("operation_result", location, "batch calls require a void native effect")
            if call.json_read == "json-text-v1" and (
                call.result_mode not in {"table", "scalar"}
                or any(f.transform not in {None, "identity"} for f in results)
            ):
                _fail(
                    "operation_result",
                    location,
                    "JSON text requires an untransformed row/scalar read",
                )
            if call.ordered != bool(call.order_by) or any(
                name not in {f.name for f in results} for name in call.order_by
            ):
                _fail("operation_order", location, "order must identify explicit result fields")
            if result_class:
                if (
                    not result_class.isidentifier()
                    or keyword.iskeyword(result_class)
                    or result_class in aliases
                ):
                    _fail("operation_result", location, "invalid result class")
                shape = (
                    call.result_mode == "void",
                    call.json_read,
                    tuple(
                        (f.name, f.resolved, f.nullable, f.semantic_type, f.transform)
                        for f in results
                    ),
                )
                if result_class in result_shapes and result_shapes[result_class] != shape:
                    _fail("operation_result", location, "one result class has conflicting shapes")
                result_shapes[result_class] = shape
            digest = sha256(canonical_bytes(sources)).hexdigest()
            if call.source_digest is not None and call.source_digest != digest:
                _fail("operation_source", location, "resolved source representation differs")
            calls.append(
                replace(
                    call,
                    parameters=parameters,
                    result_fields=results,
                    result_class=result_class,
                    source_digest=digest,
                    records=resolved_records,
                )
            )
        operations.append(replace(operation, calls=tuple(calls)))
    return replace(model, operations=tuple(operations))


def _enum_alias(field):
    parts = field.source.split(":", 1)[-1].replace(".", "_").split("_")
    return "".join(part[0].upper() + part[1:] for part in parts if part)


def _all_call_fields(call):
    return (*call.parameters, *call.result_fields, *(f for r in call.records for f in r.fields))


def render_operation_identifiers(model):
    """Keep semantic identifiers importable without SQL, models, or Arrow initialization."""
    aliases = {
        field.semantic_type: _PRIMITIVES[field.resolved.kind]
        for operation in model.operations
        for call in operation.calls
        for field in _all_call_fields(call)
        if field.semantic_type
    }
    enums = {
        _enum_alias(field): field.resolved.enum_values
        for operation in model.operations
        for call in operation.calls
        for field in call.parameters
        if field.resolved.enum_values
    }
    return "\n".join(
        [
            '"""Generated semantic identifiers from execution correspondences; do not edit."""',
            "from datetime import datetime",
            "from decimal import Decimal",
            "from typing import Literal, NewType",
            "",
            *(f"{name} = NewType({name!r}, {kind})" for name, kind in sorted(aliases.items())),
            *(
                f"type {name} = Literal[{', '.join(repr(value) for value in values)}]"
                for name, values in sorted(enums.items())
            ),
            "",
        ]
    )


def render_operation_calls(model, metadata=None):
    """Emit fixed callable signatures, Core invocations and positional materializers."""
    calls = [(operation.id, call) for operation in model.operations for call in operation.calls]
    out = [
        '"""Generated from execution call correspondences; do not edit."""',
        "from __future__ import annotations",
        "",
        "from dataclasses import dataclass",
        "from collections.abc import Sequence",
        "from datetime import datetime",
        "from decimal import Decimal",
        "from typing import Annotated, Literal, Protocol, TypedDict, cast",
        "",
        "from pydantic import Field, JsonValue, TypeAdapter",
        "from sqlalchemy import (ARRAY, BigInteger, Boolean, Column, Connection, DateTime, "
        "Float, Integer, Named, Numeric, Result, Select, Text, TypedColumns, "
        "bindparam, column, func, null, select)",
        "from sqlalchemy.sql import ColumnElement",
        "from sqlalchemy.dialects.postgresql import BYTEA, JSONB",
        "from corpus_structure.core.vocab import TaskUnitType",
        "from .types import PreparedRelease",
        "from .metadata import table as _core_table",
        "from .operation_value_types import (HeldProgress, NativeResultViolation, "
        "OperationResult, NativeRowResult, held_progress, require_call_context, "
        "native_result_scope, native_result_value, SQL_NULL, SqlNull)",
    ]
    aliases, emitted = {}, set()
    enum_aliases = {
        field.source: _enum_alias(field)
        for _, call in calls
        for field in call.parameters
        if field.resolved.enum_values
    }

    def raw_type(field, *, native=False, json_text=False):
        typ = field.resolved
        if typ is None:
            raise ValueError("call source fields have not been resolved")
        if json_text and typ.kind == "json_payload":
            return "str"
        kind = typ.model_class if typ.model_class and not native else _PRIMITIVES[typ.kind]
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

    def sql_type(field):
        typ = field.resolved
        if field.native_type == "integer":
            return "Integer()"
        expression = {
            "integer": "BigInteger()",
            "string": "Text()",
            "boolean": "Boolean()",
            "timestamp": "DateTime(timezone=True)",
            "json_payload": "JSONB(none_as_null=True)" if field.nullable else "JSONB()",
            "bytes": "BYTEA()",
            "decimal": "Numeric()",
            "float": "Float()",
        }[typ.kind]
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
                aliases[field.semantic_type] = _PRIMITIVES[field.resolved.kind]
    out += [f"from ._operation_ids import {name} as {name}" for name in sorted(aliases)]
    out += [
        f"from ._operation_ids import {name} as {name}"
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
                f"{indent}require_call_context(projection_context, {operation!r}, "
                f"{name!r}, {name.upper()}_CONTRACT_DIGEST)",
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
                        columns_class, (metadata.tables[relation].c[native] for native in fields)
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
                + ", ".join(f"ColumnElement[{typ}]" for typ in row_types)
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
                f"def collect_{name}(result: Result[{', '.join(row_types)}]) -> {collected}:",
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
                annotation = raw_type(f, native=True) + (
                    " | None" if f.resolved.nullable and f.resolved.kind != "json_payload" else ""
                )
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
            row_types
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
            out += [
                f"    require_call_context(projection_context, {operation!r}, "
                f"{name!r}, {name.upper()}_CONTRACT_DIGEST)"
            ]
        else:
            out += [
                "    if projection_context is not None:",
                f"        require_call_context(projection_context, {operation!r}, "
                f"{name!r}, {name.upper()}_CONTRACT_DIGEST)",
            ]
        out += [f"    return _{name}_statement.params(**{{"]
        out += [f"        {f.name!r}: _request.{f.name}," for f in call.parameters]
        out += ["    })"]
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
                f"        require_call_context(projection_context, {operation!r}, "
                f"{name!r}, {name.upper()}_CONTRACT_DIGEST)",
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


def generated_source() -> str:
    from corpus_structure.schema.generate import _format

    from .contracts import compile_execution_model, trusted_execution_inputs
    from .metadata import metadata

    return _format(
        "semantic/_operation_calls.py",
        render_operation_calls(compile_execution_model(trusted_execution_inputs()), metadata),
    )
