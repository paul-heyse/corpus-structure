"""Release-owned logical rule views with checked public rule-engine accessors."""

from __future__ import annotations

import decimal
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from functools import cached_property
from typing import Any, Literal, NamedTuple

import yaml
from linkml_runtime.linkml_model import SchemaDefinition
from linkml_runtime.loaders import yaml_loader
from linkml_runtime.utils.schemaview import SchemaView
from pydantic import AwareDatetime, BaseModel, ConfigDict, TypeAdapter, create_model
from rule_engine import DataType

from corpus_structure.core import tex
from corpus_structure.schema.rulelang import Language

from .types import PreparedRelease, PropertyDefinition
from .refusals import SemanticOperationRefusal, SemanticReason

RULE_VIEW_INPUT = "operation/rule-view.yaml"
RULE_VIEW_ABI = "semantic-rule-view-2"
_BARE = re.compile(r"[A-Za-z]+(_\{?\w+\}?)?")
MAX_SYMBOL = 64


class Reading(NamedTuple):
    """Operation reading; the archived rule schema owns its admitted dimensions."""

    status: str
    kind: str | None = None
    symbols: tuple[str, ...] = ()


# --- Token-derived facts ----------------------------------------------------------------------


def _significant(latex: str) -> list[tex.Token]:
    return [t for t in tex.tokens(latex) if t.kind != "space"]


def index_symbols(symbol: str | None) -> tuple[str, ...]:
    """The index letters of an indexed symbol: `i` of `X_i`, `i` and `j` of `X_{ij}`."""
    if not symbol:
        return ()
    toks = _significant(symbol)
    out: set[str] = set()
    for i, t in enumerate(toks):
        if t.text != "_" or i + 1 >= len(toks):
            continue
        nxt = toks[i + 1]
        if nxt.kind == "open":
            for inner in toks[i + 2 :]:
                if inner.kind == "close":
                    break
                if inner.kind == "char" and inner.text.isascii() and inner.text.isalpha():
                    out.add(inner.text)
        elif nxt.kind == "char" and nxt.text.isascii() and nxt.text.isalpha():
            out.add(nxt.text)
    return tuple(sorted(out))


def defined_symbol(latex: str | None) -> str | None:
    """The symbol a formula of the form `x = …` defines: a letter or control word, optionally
    indexed, then `=` (not `==`)."""
    if not latex:
        return None
    toks = _significant(latex)
    if not toks or not (
        (toks[0].kind == "char" and toks[0].text.isascii() and toks[0].text.isalpha())
        or toks[0].kind == "word"
    ):
        return None
    i = 1
    if i < len(toks) and toks[i].text == "_":
        i += 1
        if i < len(toks) and toks[i].kind == "open":
            depth = 0
            while i < len(toks):
                depth += {"open": 1, "close": -1}.get(toks[i].kind, 0)
                i += 1
                if depth == 0:
                    break
        else:
            i += 1
    if (
        i < len(toks)
        and toks[i].text == "="
        and not (i + 1 < len(toks) and toks[i + 1].text == "=")
    ):
        return latex[toks[0].start : toks[i - 1].end]
    return None


# --- The view objects -------------------------------------------------------------------------


@dataclass(frozen=True)
class EntityView:
    id: str
    key: str | None
    type: str
    label: str
    symbol: str | None
    identity: Mapping[str, str]

    @cached_property
    def index_symbols(self) -> tuple[str, ...]:
        return index_symbols(self.symbol)


@dataclass(frozen=True)
class ValueView:
    t: str
    latex: str | None
    v: str | None
    enum: str | None
    slot_kind: str
    reading: Reading | None = None
    declared_range: str = "Value"
    expression_form: str | None = None

    @property
    def value_kind(self) -> str:
        return self.t

    @property
    def enum_id(self) -> str | None:
        return self.enum

    @property
    def reading_status(self) -> str:
        return self.parse or ("missing" if self.t == "missing" else "unavailable")

    @cached_property
    def defined_symbol(self) -> str | None:
        return (
            defined_symbol(self.latex)
            if self.expression_form == "formula" or self.t == "formula"
            else None
        )

    @property
    def parse(self) -> str | None:
        return str(self.reading.status) if self.reading else None

    @property
    def math_kind(self) -> str | None:
        return str(self.reading.kind) if self.reading and self.reading.kind else None


@dataclass(frozen=True)
class StatementView:
    id: str
    key: str | None
    kind: str


@dataclass(frozen=True)
class BindingView:
    symbol: str
    bind: str
    entity: str | None
    claim: str | None
    param: str | None


@dataclass(frozen=True)
class NodeView:
    op: str
    ref: str | None
    name: str | None
    rel: str | None
    x_latex: str | None


class QualifiersView:
    """One attribute per qualifier identifier of the version (null when absent)."""

    def __init__(self, values: Mapping[str, Any]) -> None:
        self.__dict__.update(values)


@dataclass(frozen=True)
class _Field:
    range: str
    nullable: bool = False
    collection: str = "scalar"
    source_class: str | None = None
    source_property: str | None = None
    parameter_map: bool = False


def _annotations(slot) -> dict[str, str]:
    raw = slot.annotations or {}
    entries = raw.items() if hasattr(raw, "items") else vars(raw).items()
    return {str(name): str(getattr(value, "value", value)) for name, value in entries}


def project_rule_value(
    prepared: PreparedRelease,
    binding: PropertyDefinition | str,
    value: Any,
    reading: Reading | None = None,
) -> ValueView | None:
    """One translation for claim roots, inlined values and keyed parameter entries.

    The declared binding, rather than the discriminator, owns range and enum identity.
    Reading absence is unavailable, and failed readings retain their actual status.
    """
    if value is None:
        return None
    declared = binding.range if isinstance(binding, PropertyDefinition) else binding
    if isinstance(value, ValueView):
        if value.declared_range != declared:
            raise ValueError("rule value belongs to another declared range")
        return value
    enum = declared if any(v.enum == declared for v in prepared.vocabularies) else None
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="python", exclude_unset=True)
    if isinstance(value, Mapping):
        kind = value["kind"]
        lexical = value.get("expression")
        scalar = next(
            (
                value[name]
                for name in ("text", "number", "boolean", "date", "instant", "lexical", "target")
                if name in value
            ),
            None,
        )
        form = value.get("form") or (
            kind if kind in {"formula", "set", "relation", "membership", "list"} else None
        )
    else:
        kind = "entity" if declared in prepared.index.definitions else "text"
        lexical, scalar, form = None, value, None
    if isinstance(scalar, date):
        scalar = scalar.isoformat()
    return ValueView(
        str(kind),
        lexical,
        None if scalar is None else str(scalar),
        enum,
        declared,
        reading,
        declared,
        form,
    )


def build_rule_language(
    prepared: PreparedRelease,
    *,
    qprops,
    builtins,
    values,
    arguments,
    keys=None,
    views=(),
) -> Language:
    """Compile the archived LinkML logical view into public rule-engine OBJECT schemas.

    Accessors validate the values they actually return. The engine's accessor path itself
    skips type verification, so parse-time OBJECT types alone would not discharge fidelity.
    """
    from typing import ForwardRef

    from pydantic import FiniteFloat

    from .publication import native_constraints

    artifact = next((a for a in prepared.artifacts if a.kind == RULE_VIEW_INPUT), None)
    if artifact is None:
        raise SemanticOperationRefusal(SemanticReason(
            "preparation_failed", "evaluate", prepared.release_id,
            references=(RULE_VIEW_INPUT,), detail="release lacks its archived semantic rule-view recipe",
        ))
    document = yaml.safe_load(artifact.content)
    if document.get("version") != RULE_VIEW_ABI:
        raise SemanticOperationRefusal(SemanticReason(
            "incompatible_bindings", "evaluate", prepared.release_id,
            expected=RULE_VIEW_ABI, actual=document.get("version"),
        ))
    schema = yaml_loader.loads(artifact.content.decode(), target_class=SchemaDefinition)
    if not isinstance(schema, SchemaDefinition):
        raise ValueError("archived semantic rule-view is not a LinkML schema")
    view = SchemaView(schema)
    declarations: dict[str, dict[str, _Field]] = {}
    for name in view.all_classes():
        declarations[str(name)] = {
            str(slot.name): _Field(
                str(slot.range or "string"),
                _annotations(slot).get("rv:nullable") == "true",
                _annotations(slot).get("rv:collection", "scalar"),
            )
            for slot in view.class_induced_slots(name)
        }
    declarations["Claim"].update({name: _Field("string", collection="array") for name in views})
    definitions = {definition.name: definition for definition in prepared.definitions}
    constraints = native_constraints(prepared)
    param_maps = {
        body["cs:param_map"]
        for row in prepared.registry_rows
        if row.kind == "operation_property"
        for body in (json.loads(row.body),)
        if body.get("cs:param_map")
    }
    primitive_annotations = {
        "string": str,
        "boolean": bool,
        "decimal": int | FiniteFloat | decimal.Decimal,
        "integer": int,
        "float": FiniteFloat,
        "date": date,
        "datetime": AwareDatetime,
    }
    primitive_types = {
        "string": DataType.STRING,
        "boolean": DataType.BOOLEAN,
        "decimal": DataType.FLOAT,
        "integer": DataType.FLOAT,
        "float": DataType.FLOAT,
        "date": DataType.DATETIME,
        "datetime": DataType.DATETIME,
    }

    # Logical reading dimensions belong to the archived operation recipe, rather
    # than to a legacy runtime enum. The same vocabulary constrains compiler literals
    # and actual accessor values through the cached strict adapters.
    logical_enums = {str(name): tuple(str(member) for member in enum.permissible_values)
                     for name, enum in view.all_enums().items()}
    values = dict(values)
    for name, members in logical_enums.items():
        primitive_annotations[name] = Literal[tuple(members)]
        primitive_types[name] = DataType.STRING
    from corpus_structure.schema.rulelang import Vocabulary
    for owner, fields in declarations.items():
        for name, spec in fields.items():
            if spec.range in logical_enums:
                values[owner, name] = Vocabulary(spec.range, frozenset(logical_enums[spec.range]))

    def domain_range(class_name: str) -> str:
        if class_name == "Value" or "Value" in definitions[class_name].ancestors:
            return "Value"
        name = "Semantic_" + class_name
        if name not in declarations:
            declarations[name] = {}
            definition = definitions[class_name]
            for prop in definition.properties:
                declarations[name][prop.name] = property_field(definition, prop)
        return name

    def property_field(definition, prop) -> _Field:
        native = constraints[definition.iri, prop.iri]["native_range"]
        if prop.range in definitions:
            target = domain_range(prop.range) if prop.inlined else "string"
        elif prop.range in {v.enum for v in prepared.vocabularies}:
            target = "string"
        else:
            target = {"double": "float", "uri": "string", "uriorcurie": "string"}.get(
                native, native
            )
        return _Field(
            target,
            not prop.required,
            "mapping" if prop.collection_key else "array" if prop.multivalued else "scalar",
            definition.name,
            prop.name,
        )

    for name, prop in qprops.items():
        owner = next(
            d
            for d in prepared.definitions
            if (d.name == "Qualification" or "Qualification" in d.ancestors)
            and prop in d.properties
        )
        if name in param_maps:
            definition = definitions.get(prop.range)
            fields = {p.name: p for p in definition.properties} if definition else {}
            if (
                not prop.inlined
                or not prop.multivalued
                or not {"key", "value"} <= fields.keys()
                or fields["value"].range not in definitions
                or not fields["value"].inlined
            ):
                raise ValueError(
                    f"{name}: parameter-map projection lacks a declared keyed Value entry"
                )
            if domain_range(fields["value"].range) != "Value":
                raise ValueError(f"{name}: parameter-map values are not semantic Values")
            declarations["Qualifiers"][name] = _Field(
                "Value", not prop.required, "mapping", owner.name, prop.name, True
            )
        else:
            declarations["Qualifiers"][name] = property_field(owner, prop)

    models: dict[str, Any] = {}
    for name, fields in declarations.items():
        entries: dict[str, Any] = {}
        for field_name, spec in fields.items():
            annotation: Any = primitive_annotations.get(
                spec.range, ForwardRef("Rule_" + spec.range)
            )
            if spec.collection == "array":
                annotation = tuple[annotation, ...]
            elif spec.collection == "mapping":
                annotation = dict[str, annotation]
            if spec.nullable:
                annotation = annotation | None
            entries[field_name] = (annotation, None if spec.nullable else ...)
        models[name] = create_model(
            "Rule_" + name,
            __config__=ConfigDict(strict=True, frozen=True, from_attributes=True),
            **entries,
        )
    namespace = {model.__name__: model for model in models.values()}
    for model in models.values():
        model.model_rebuild(_types_namespace=namespace)
    native_types = {}

    def field_value(owner: str, obj: Any, name: str) -> Any:
        value: Any
        spec = declarations[owner][name]
        if spec.nullable:
            value = obj.get(name) if isinstance(obj, Mapping) else getattr(obj, name, None)
        else:
            value = obj[name] if isinstance(obj, Mapping) else getattr(obj, name)
        if value is not None and not isinstance(obj, BaseModel):
            if spec.parameter_map:
                if isinstance(value, Mapping) and all(
                    isinstance(v, Mapping) and "kind" in v for v in value.values()
                ):
                    parent = prepared.index.properties[spec.source_class, spec.source_property]
                    entry_binding = prepared.index.properties[parent.range, "value"]
                    value = {
                        key: project_rule_value(prepared, entry_binding, member)
                        for key, member in value.items()
                    }
                else:
                    entries = list(value.values()) if isinstance(value, Mapping) else value
                    projected = {}
                    for entry in entries:
                        key = entry["key"]
                        if key in projected:
                            raise ValueError("parameter-map projection contains duplicate keys")
                        parent = prepared.index.properties[spec.source_class, spec.source_property]
                        entry_binding = prepared.index.properties[parent.range, "value"]
                        projected[key] = project_rule_value(prepared, entry_binding, entry["value"])
                    value = projected
            elif spec.range == "Value" and spec.source_class is not None:
                # Native schema fields also occur inside keyed records. Logical rule-view
                # fields already hold projected Values and have no source_class.
                value = (
                    {
                        key: project_rule_value(
                            prepared,
                            prepared.index.properties[spec.source_class, spec.source_property],
                            v,
                        )
                        for key, v in value.items()
                    }
                    if spec.collection == "mapping"
                    else tuple(
                        project_rule_value(
                            prepared,
                            prepared.index.properties[spec.source_class, spec.source_property],
                            v,
                        )
                        for v in value
                    )
                    if spec.collection == "array"
                    else project_rule_value(
                        prepared,
                        prepared.index.properties[spec.source_class, spec.source_property],
                        value,
                    )
                )
        if spec.collection == "array" and isinstance(value, list):
            value = tuple(value)
        if spec.range in declarations and value is not None:

            def project(member):
                return {
                    field: field_value(spec.range, member, field)
                    for field in declarations[spec.range]
                }

            if spec.collection == "array":
                value = tuple(project(member) for member in value)
            elif spec.collection == "mapping":
                value = {key: project(member) for key, member in value.items()}
            else:
                value = project(value)
        return value

    def accessor(owner: str):
        def read(obj, name):
            value = field_value(owner, obj, name)
            adapter = adapters[owner, name]
            return adapter.validate_python(value, strict=True, from_attributes=True)

        return read

    adapters = {
        (owner, name): TypeAdapter(model.model_fields[name].rebuild_annotation())
        for owner, model in models.items()
        for name in model.model_fields
    }
    for name, fields in declarations.items():
        attrs = {}
        for field_name, spec in fields.items():
            target = primitive_types.get(spec.range)
            if target is None:
                target = DataType.OBJECT.reference(spec.range)
            if spec.collection == "array":
                target = DataType.ARRAY(target)
            elif spec.collection == "mapping":
                target = DataType.MAPPING(DataType.STRING, target)
            if spec.nullable:
                target = DataType.NULLABLE(target)
            attrs[field_name] = target
        native_types[name] = DataType.OBJECT(name, attributes=attrs, accessor=accessor(name))
    annotations = _annotations(view.schema)
    context = decimal.Context(
        prec=int(annotations["rv:decimal_precision"]),
        rounding=getattr(decimal, annotations["rv:decimal_rounding"]),
    )
    return Language(
        objects={},
        symbols={"claim": "Claim"},
        native_types=native_types,
        decimal_context=context,
        builtins=builtins,
        values=values,
        keys=keys or {},
        arguments=arguments,
        no_regex=frozenset({("Value", "latex"), ("Node", "x_latex"), ("Binding", "symbol")}),
    )
