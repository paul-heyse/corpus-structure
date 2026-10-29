"""Batch models and their JSON Schemas per form (P0-S-1; schema and rules §3.3; D2 §7.3).

One claim model per predicate is built with `pydantic.create_model` over foundations' item models
(`core/batch.py`): a `Literal` predicate, the object typed by the predicate's object kind, and a
qualifier model with the core qualifiers (the version's modalities as a `Literal`) plus the
predicate's listed schema qualifiers, each typed by its object kind, unknown ones refused. The
claim models are a union discriminated on `predicate` inside the envelope of each form:

- `model` (authored): local names, sentence ids and quotes;
- `stored`: prefixed names (`stat:has_distribution`, `stat:RandomVariable`, `stat:param_values`)
  and, for pack members of version-scoped sets, `<prefix>:<name>`; offsets and segment keys.

A `TypeAdapter` per form validates on the JSON path (`validate_json(text, strict=True)`) and exports
its draft 2020-12 JSON Schema through the core generator, with an `$id` naming the model revision,
the schema version and the form (M3's convention, `core.schemas.schema_id`). The `statements[]`
union holds the version's kind-bearing statement and foundations' `outside` item (an
`ExternalReference` with its descriptor), discriminated on `anchor == "outside"`. The
decoding form (T6) is a pure transform of the model-facing schema, with D2 §7.3's backend
assertions; a violated assertion is a compile error.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Annotated, Any, Literal, Union

from pydantic import MISSING, ConfigDict, Discriminator, Field, Tag, TypeAdapter, create_model

from corpus_structure.core import batch as B
from corpus_structure.core import values as V
from corpus_structure.core.batch import DEFAULT_MODALITY, DEFAULT_POLARITY
from corpus_structure.core.schemas import json_schema
from corpus_structure.core.schemas import schema_id as core_schema_id
from corpus_structure.core.vocab import Polarity
from corpus_structure.schema.lookup import NameMap, Predicate, Qualifier, SchemaLookup
from corpus_structure.schema.pack import PackError

FORMS = ("model", "stored")
# Types built at run time from the lookup: the generic forms read as `Any` for the type checker.
_DICT: Any = dict
_TUPLE: Any = tuple
_UNION: Any = Union


class _AuthoredQualifiers(B.AuthoredQualifiers):
    """The authored qualifiers of one predicate: its schema qualifiers typed, others refused."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class _StoredQualifiers(B.StoredQualifiers):
    """The stored qualifiers of one predicate, by prefixed name, others refused."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_by_alias=True,
        validate_by_name=False,
        serialize_by_alias=True,
    )


def schema_id(model_revision: str, schema_version: str, form: str) -> str:
    """The `$id` of a batch schema of one schema version (M3's convention)."""
    return core_schema_id(f"batch.{form}", model_revision, schema_version)


def _literal(values: tuple[str, ...]) -> Any:
    """Construct a runtime type form from the acquired closed vocabulary."""
    return getattr(Literal, "__getitem__")(values)


def _optional(t: Any) -> tuple[Any, Any]:
    return (t | MISSING, MISSING)


class BatchCompiler:
    """The per-predicate batch models of one schema version, both forms."""

    def __init__(self, lookup: SchemaLookup, names: NameMap) -> None:
        self.lookup = lookup
        self.names = names
        self.claims: dict[str, dict[str, type]] = {f: {} for f in FORMS}
        self.models = {f: self._batch(f) for f in FORMS}
        self.adapters: dict[str, TypeAdapter[Any]] = {
            f: TypeAdapter(m) for f, m in self.models.items()
        }

    # -- names per form --------------------------------------------------------------------------

    def _name(self, local: str, form: str) -> str:
        return local if form == "model" else self.names.prefixed(local)

    def _members(self, set_name: str, form: str) -> tuple[str, ...]:
        members = self.lookup.version_sets[set_name].members
        return tuple(m.text if form == "model" else m.stored for m in members)

    # -- positions -------------------------------------------------------------------------------

    def _position(self, kind: str, rng: str, form: str, map_kind: str | None = None) -> Any:
        phrase = V.AuthoredPhrase if form == "model" else V.StoredPhrase
        condition = V.AuthoredCondition if form == "model" else V.StoredCondition
        simple = {
            "entity": V.EntityRef,
            "formula": V.Formula,
            "set": V.SetValue,
            "phrase": phrase,
            "condition": condition,
            "interval": V.IntervalValue,
            "number": V.NumberValue,
            "date": V.DateValue,
            "bool": V.BoolValue,
            "text": str,
        }
        if kind in simple:
            return simple[kind]
        if kind == "map":
            assert map_kind is not None
            return _DICT[str, self._position(map_kind, "string", form)]
        if kind == "enum":
            return _literal(tuple(m.text for m in self.lookup.enums[rng].members))
        raise PackError([f"no batch position for object kind {kind!r} ({rng})"])

    def _object(self, p: Predicate, form: str) -> Any:
        phrase = V.AuthoredPhrase if form == "model" else V.StoredPhrase
        values = {
            "entity": V.EntityRef,
            "formula": V.Formula,
            "set": V.SetValue,
            "phrase": phrase,
            "text": V.TextValue,
            "number": V.NumberValue,
            "bool": V.BoolValue,
            "date": V.DateValue,
            "interval": V.IntervalValue,
        }
        if p.object_kind in values:
            return values[p.object_kind]
        if p.object_kind == "enum":
            enum = self.lookup.enums[p.range]
            name = enum.name if form == "model" else enum.prefixed
            return create_model(
                f"{enum.name}Value_{form}",
                __base__=V.AuthoredEnumValue if form == "model" else V.StoredEnumValue,
                enum=(_literal((name,)), ...),
                v=(_literal(tuple(m.text for m in enum.members)), ...),
            )
        raise PackError([f"{p.name}: no object for kind {p.object_kind!r}"])

    # -- items -----------------------------------------------------------------------------------

    def _qualifiers(self, p: Predicate, form: str) -> type:
        base = _AuthoredQualifiers if form == "model" else _StoredQualifiers
        modality = _literal(self._members("ClaimModality", form))
        fields: dict[str, Any] = {}
        default = (str(DEFAULT_MODALITY), str(DEFAULT_POLARITY))
        if form == "model":
            fields["modality"] = (modality, Field(default[0], exclude_if=lambda v: v == default[0]))
            fields["polarity"] = (Polarity, Field(default[1], exclude_if=lambda v: v == default[1]))
        else:
            fields["modality"] = (
                modality,
                Field(default[0], alias="core:modality", exclude_if=lambda v: v == default[0]),
            )
            fields["polarity"] = (
                Polarity,
                Field(default[1], alias="core:polarity", exclude_if=lambda v: v == default[1]),
            )
        for name in p.qualifiers:
            q: Qualifier = self.lookup.qualifiers[name]
            t = self._position(q.object_kind, q.range, form, q.map_value_kind)
            if form == "model":
                fields[name] = _optional(t)
            else:
                fields[name] = (t | MISSING, Field(MISSING, alias=q.prefixed))
        return create_model(f"Qualifiers_{p.name}_{form}", __base__=base, **fields)

    def _claim(self, p: Predicate, form: str) -> type:
        base = B.AuthoredClaim if form == "model" else B.StoredClaim
        qualifiers = self._qualifiers(p, form)
        model = create_model(
            f"Claim_{p.name}_{form}",
            __base__=base,
            __doc__=p.description,
            predicate=(_literal((self._name(p.name, form),)), ...),
            object=(self._object(p, form), ...),
            qualifiers=(qualifiers, Field(default_factory=qualifiers)),
        )
        self.claims[form][p.name] = model
        return model

    def _entity(self, form: str) -> type:
        base = B.AuthoredEntity if form == "model" else B.StoredEntity
        types = tuple(self._name(n, form) for n in self.lookup.batch_entity_types())
        return create_model(f"Entity_{form}", __base__=base, type=(_literal(types), ...))

    def _statement(self, form: str) -> Any:
        base = B.AuthoredStatement if form == "model" else B.StoredStatement
        kinds = _literal(self._members("StatementKind", form))
        statement = create_model(f"Statement_{form}", __base__=base, kind=(kinds, ...))
        outside = B.AuthoredOutside if form == "model" else B.StoredOutside
        return Annotated[
            Annotated[statement, Tag("statement")] | Annotated[outside, Tag("outside")],
            Discriminator(B._statement_or_outside),
        ]

    def _batch(self, form: str) -> type:
        base = B.AuthoredBatch if form == "model" else B.StoredBatch
        claims = tuple(self._claim(p, form) for p in self.lookup.predicates.values())
        claim = Annotated[_UNION[claims], Field(discriminator="predicate")]
        return create_model(
            f"Batch_{form}",
            __base__=base,
            entities=(_TUPLE[self._entity(form), ...], ()),
            statements=(_TUPLE[self._statement(form), ...], ()),
            claims=(_TUPLE[claim, ...], ()),
        )

    # -- outputs ---------------------------------------------------------------------------------

    def validate(self, text: str, form: str) -> Any:
        """A submission on the JSON path, strict (schema and rules §3.3)."""
        return self.adapters[form].validate_json(text, strict=True)

    def json_schema(self, form: str, schema_id_: str) -> dict[str, Any]:
        out = json_schema(self.adapters[form])
        return {"$schema": out.pop("$schema"), "$id": schema_id_, **out}


# --- The decoding form (T6; D2 §7.3) -----------------------------------------------------------

DECODING_DROP = frozenset({"discriminator", "description", "default", "examples", "title"})
FORBIDDEN = frozenset(
    {
        "if",
        "then",
        "else",
        "not",
        "multipleOf",
        "uniqueItems",
        "contains",
        "minContains",
        "maxContains",
        "dependentRequired",
        "dependentSchemas",
        "propertyNames",
        "format",
        "patternProperties",
    }
)
MAX_DEPTH = 64


def decoding_form(model_schema: dict[str, Any], schema_id_: str) -> dict[str, Any]:
    """The structured-output schema: the model-facing schema with the keywords a constrained
    decoder does not take removed (its declared omissions), each `oneOf` branch inlined one level
    (xgrammar proves disjointness only over inline branches), and D2 §7.3's assertions checked."""

    def drop(node: Any, parent: str | None = None) -> Any:
        if isinstance(node, dict):
            return {
                k: drop(v, k)
                for k, v in node.items()
                if parent == "properties" or k not in DECODING_DROP
            }
        if isinstance(node, list):
            return [drop(v) for v in node]
        return node

    out = drop(copy.deepcopy(model_schema))
    defs = out.get("$defs", {})

    def inline(node: Any) -> Any:
        if isinstance(node, dict):
            res = {k: inline(v) for k, v in node.items()}
            if isinstance(res.get("oneOf"), list):
                res["oneOf"] = [
                    copy.deepcopy(defs[b["$ref"].split("/")[-1]]) if set(b) == {"$ref"} else b
                    for b in res["oneOf"]
                ]
            return res
        if isinstance(node, list):
            return [inline(v) for v in node]
        return node

    for name in list(defs):
        defs[name] = inline(defs[name])
    out["$defs"] = defs
    out = inline(out)
    out["$id"] = schema_id_
    problems = decoding_problems(out)
    if problems:
        raise PackError([f"decoding form: {p}" for p in problems])
    return out


def _resolve(node: Any, root: Mapping[str, Any]) -> Any:
    while isinstance(node, dict) and "$ref" in node:
        node = root["$defs"][node["$ref"].split("/")[-1]]
    return node


TAGS = ("t", "op", "bind", "predicate", "anchor")
_JSON_TYPES = {str: "string", bool: "boolean", int: "integer", float: "number"}


def _values(s: Mapping[str, Any]) -> tuple[set[Any], set[str]] | None:
    """A tag property's admitted values: (consts, JSON types admitting any value), or None."""
    if "const" in s:
        return {s["const"]}, set()
    if "enum" in s:
        return set(s["enum"]), set()
    if "anyOf" in s:
        consts: set[Any] = set()
        types: set[str] = set()
        for branch in s["anyOf"]:
            if "const" in branch or "enum" in branch:
                inner = _values(branch)
                assert inner is not None
                consts |= inner[0]
            elif isinstance(branch.get("type"), str) and branch["type"] != "string":
                types.add(branch["type"])
            else:
                return None
        return consts, types
    return None


def _tag(branch: Any, root: Mapping[str, Any]) -> tuple[str, set[Any], set[str]] | None:
    b = _resolve(branch, root)
    props = b.get("properties") or {}
    for prop, s in props.items():
        if prop in (b.get("required") or ()) and "const" in s:
            return prop, {s["const"]}, set()
    for prop, s in props.items():
        if prop in (b.get("required") or ()) and prop in TAGS and (v := _values(s)) is not None:
            return prop, *v
    return None


def _disjoint(tags: list[tuple[str, set[Any], set[str]]]) -> bool:
    """Branches disjoint by one property: no const shared, no type shared, no const of a type
    another branch admits wholly (a string-typed branch admitting any string is not a tag)."""
    for i, (_, consts, types) in enumerate(tags):
        for _, other_consts, other_types in tags[i + 1 :]:
            if consts & other_consts or types & other_types:
                return False
            if {_JSON_TYPES.get(type(c)) for c in consts} & other_types:
                return False
            if {_JSON_TYPES.get(type(c)) for c in other_consts} & types:
                return False
    return True


def decoding_problems(schema: Mapping[str, Any]) -> list[str]:
    """D2 §7.3's backend rules: no forbidden keyword, no multi-branch `allOf`, every `oneOf`
    disjoint by one property (a `const` per branch, or, for a tag property such as the statement
    `anchor`, value sets that cannot overlap), nesting at most 64 levels."""
    problems: list[str] = []
    deepest = 0

    def walk(node: Any, path: str, depth: int, parent: str | None = None) -> None:
        nonlocal deepest
        deepest = max(deepest, depth)
        if isinstance(node, dict):
            for k, v in node.items():
                if parent != "properties":
                    if k in FORBIDDEN:
                        problems.append(f"{path}/{k}: forbidden keyword")
                    if k in DECODING_DROP:
                        problems.append(f"{path}/{k}: a keyword the decoding form drops")
                    if k == "allOf" and isinstance(v, list) and len(v) > 1:
                        problems.append(f"{path}/allOf: more than one branch")
                    if k == "oneOf":
                        tags = [_tag(b, schema) for b in v]
                        found = [t for t in tags if t is not None]
                        props = {t[0] for t in found}
                        if len(found) != len(tags) or len(props) != 1 or not _disjoint(found):
                            problems.append(f"{path}/oneOf: branches not disjoint by one const")
                walk(v, f"{path}/{k}", depth + 1, k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}/{i}", depth + 1)

    walk(schema, "#", 0)
    if deepest > MAX_DEPTH:
        problems.append(f"nesting {deepest} exceeds {MAX_DEPTH}")
    return problems
