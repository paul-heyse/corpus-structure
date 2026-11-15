"""Closed model-backed field resolution for current fixed native call assets.

Call admission belongs to the effective DDO operation and its authenticated facet.
This owner resolves transport correspondences from explicitly supplied sources.
"""

from __future__ import annotations

import keyword
import json
from collections.abc import Mapping
from dataclasses import asdict, replace
from hashlib import sha256
from typing import Any, cast, Never

import yaml
from linkml_runtime.utils.yamlutils import DupCheckYamlLoader

from .identity import canonical_bytes
from .native_call_contracts import OperationCallBinding
from .types import Diagnostic, PreparationError


def _fail(code: str, location: str, message: str) -> Never:
    raise PreparationError((Diagnostic(code, location, message),))


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


def _source_view(logical_sources: Mapping[str, bytes], physical_sources: Mapping[str, bytes]):
    """Resolve supplied model modules, including package data acquired at the entry point."""
    from linkml_runtime.dumpers import json_dumper
    from linkml_runtime.linkml_model.meta import SchemaDefinition
    from linkml_runtime.loaders import yaml_loader
    from linkml_runtime.utils.schemaview import SchemaView

    from corpus_structure.schema.physical import physical_model_documents

    aliases = {
        "pdf-records": "pdf_records",
        "pdf-staging": "pdf_staging",
        "pdf-products": "pdf_products",
        "companion-projections": "companion_projections",
    }
    supplied = dict(logical_sources)
    roots = list(supplied)
    for filename, document in physical_model_documents(physical_sources).items():
        name = aliases.get(filename.removesuffix(".yaml"), filename.removesuffix(".yaml"))
        if (
            filename not in {"physical.yaml", "pdf-records.yaml", "pdf-staging.yaml"}
            and name in supplied
        ):
            _fail("operation_source", name, "physical import conflicts with a declared module")
        supplied[name] = yaml.safe_dump(document, sort_keys=False).encode()
        if filename == "physical.yaml" and name not in roots:
            roots.append(name)
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
        id="urn:corpus:operation-sources", name="operation_sources", imports=roots
    )
    schemas["operation_sources"] = root
    importmap: dict[str, dict[str, Any] | str] = {}
    for name, schema in schemas.items():
        entry = json_dumper.to_dict(schema)
        if not isinstance(entry, dict):
            _fail("operation_source", name, "serialized schema must be a mapping")
        importmap[name] = dict(entry)
    view = SchemaView(root, importmap=importmap)
    view.merge_imports()
    merged = view.schema
    if merged is None:
        _fail("operation_source", "operations/calls", "merged source schema is unavailable")
    merged.imports = []
    return SchemaView(merged)

def _kind(view, name, trail=()):
    from corpus_structure.schema.model import ci_annotations

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

def source_bindings(
    calls: tuple[tuple[str, OperationCallBinding], ...],
    *, logical_sources: Mapping[str, bytes], physical_sources: Mapping[str, bytes],
):
    """Compile qualified fixed variants from explicit field references and closed sources."""
    from corpus_structure.schema.model import ci_annotations

    from .native_call_contracts import OperationFieldBinding, OperationFieldType
    view = _source_view(logical_sources, physical_sources)
    # Reuse the identifier owned by an explicit physical correspondence, including
    # through model projections. Nested records must retain the same distinctions.
    semantic_sources = {}
    for _, call in calls:
        for field in (*call.parameters, *call.result_fields):
            if field.semantic_type and field.source.startswith("physical:"):
                previous = semantic_sources.setdefault(field.source, field.semantic_type)
                if previous != field.semantic_type:
                    _fail("operation_field", field.source, "semantic identifiers differ")

    def qualified(reference):
        return reference if ":" in reference else "model:" + reference

    def declared_type_edge(definition, name):
        attributes = cast(dict[str, Any], definition.attributes or {})
        usage = cast(dict[str, Any], definition.slot_usage or {})
        for declared in (attributes.get(name), usage.get(name)):
            if declared is not None and (edge := ci_annotations(declared).get("cp:type_source")):
                return edge
        if name in (definition.slots or ()):
            declared = view.get_slot(name)
            if declared is not None:
                return ci_annotations(declared).get("cp:type_source")
        return None

    def field_annotations(reference, slot):
        annotations = ci_annotations(slot)
        if reference.startswith("physical:") and annotations.get("cp:type_source") == reference:
            schema, cls, name = reference.removeprefix("physical:").split(".")
            ancestors = []
            for ancestor in view.class_ancestors(cls, reflexive=True):
                definition = view.get_class(ancestor)
                if definition is None:
                    _fail("operation_source", reference, "type correspondence field is unavailable")
                ancestors.append(definition)
            if any(
                schema in (definition.in_subset or ()) and declared_type_edge(definition, name)
                for definition in ancestors
            ):
                return annotations
            if any(
                schema not in (definition.in_subset or ())
                and declared_type_edge(definition, name) == reference
                for definition in ancestors
            ):
                # Only a positively identified model-to-physical backreference is
                # inherited without declaring a reflexive physical correspondence.
                annotations.pop("cp:type_source")
        return annotations

    semantic_types = {}

    def semantic_type(reference, stack=()):
        reference = qualified(reference)
        if reference in stack:
            _fail("operation_source", reference, "cyclic type correspondence")
        if reference in semantic_types:
            return semantic_types[reference]
        if not reference.startswith(("physical:", "model:")):
            return None
        parts = reference.split(":", 1)[1].split(".")
        cls, name = parts[-2:]
        slot = next((s for s in view.class_induced_slots(cls) if s.name == name), None)
        if slot is None:
            _fail("operation_source", reference, "type correspondence field is unavailable")
        annotations = field_annotations(reference, slot)
        anchors = {semantic_sources[reference]} if reference in semantic_sources else set()
        # An explicit anchor names this field; it cannot waive validation of its edges.
        for edge in ("cp:source", "cp:type_source"):
            if parent := annotations.get(edge):
                inherited = semantic_type(parent, (*stack, reference))
                if inherited is not None:
                    anchors.add(inherited)
        if len(anchors) > 1:
            _fail("operation_source", reference, "semantic identifiers differ")
        semantic_types[reference] = next(iter(anchors), None)
        return semantic_types[reference]

    def model_field(name, slot):
        reference = f"model:{name}.{slot.name}"
        return OperationFieldBinding(
            str(slot.name), reference, False, semantic_type=semantic_type(reference)
        )

    def correspond(reference, local, inherited):
        if inherited.kind != local.kind or inherited.multivalued != local.multivalued:
            _fail("operation_source", reference, "type correspondence encoding differs")
        if (
            local.enum_values
            and inherited.enum_values
            and set(local.enum_values) != set(inherited.enum_values)
        ):
            _fail("operation_source", reference, "type correspondence members differ")
        return replace(local, enum_values=local.enum_values or inherited.enum_values)

    def resolve(field, parameters, stack=()):
        reference = qualified(field.source)
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
        annotations = field_annotations(reference, slot)
        if parent := annotations.get("cp:source"):
            resolved, source = resolve(
                replace(field, source=parent), parameters, (*stack, reference)
            )
            constraints = {
                "required": slot.required,
                "value_presence": str(slot.value_presence) if slot.value_presence else None,
                "minimum_cardinality": slot.minimum_cardinality,
            }
            source = {
                "projection": reference,
                "source": source,
                **{key: value for key, value in constraints.items() if value is not None},
            }
            if parent := annotations.get("cp:type_source"):
                inherited, type_source = resolve(
                    replace(field, source=qualified(parent)), parameters, (*stack, reference)
                )
                resolved = correspond(reference, resolved, inherited)
                source = {**source, "type_source": type_source}
            semantic_type(reference)
            return resolved, source
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
        type_source = None
        if parent := annotations.get("cp:type_source"):
            inherited, type_source = resolve(
                replace(field, source=qualified(parent)), parameters, (*stack, reference)
            )
            resolved = correspond(reference, resolved, inherited)
        semantic_type(reference)
        return resolved, {
            **({"type_source": type_source} if type_source else {}),
            "reference": reference,
            "uri": view.get_uri(slot, expand=True),
            "range": str(slot.range),
            "type": asdict(resolved),
            "minimum": str(slot.minimum_value) if slot.minimum_value is not None else None,
            "maximum": str(slot.maximum_value) if slot.maximum_value is not None else None,
            "pattern": slot.pattern,
        }

    return view, semantic_type, model_field, resolve

def resolve_call_bindings(
    calls: tuple[tuple[str, OperationCallBinding], ...],
    *, logical_sources: Mapping[str, bytes], physical_sources: Mapping[str, bytes],
    core_owners: Mapping[str, str] | None = None,
) -> tuple[tuple[str, OperationCallBinding], ...]:
    """Compile qualified fixed variants from explicit field references and closed sources."""
    from corpus_structure.schema.model import ci_annotations

    from .native_call_contracts import OperationRecordBinding
    view, semantic_type, model_field, resolve = source_bindings(
        calls, logical_sources=logical_sources, physical_sources=physical_sources
    )
    core_owners = {} if core_owners is None else core_owners
    aliases, identifiers, result_shapes = {}, set(), {}

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
            if field.semantic_type is None and field.transform in {None, "identity"}:
                field = replace(field, semantic_type=semantic_type(field.source))
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

    resolved_calls = []
    for owner, call in calls:
        location = "operations/" + owner + "/calls/" + call.id
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
        if call.backend == "core":
            if call.symbol != core_owners.get(owner):
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
        resolved_calls.append(
            (owner, replace(
                call,
                parameters=parameters,
                result_fields=results,
                result_class=result_class,
                source_digest=digest,
                records=resolved_records,
            ))
        )
    return tuple(resolved_calls)

