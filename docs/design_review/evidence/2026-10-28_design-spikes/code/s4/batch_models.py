"""The batch schema compiler (D2 §7.3; schema-rules note L-02, L-03).

One claim model per predicate, built with ``pydantic.create_model`` from the pack (subject and object
types, the value type, the allowed qualifiers with enum literals injected), unioned and discriminated
on ``predicate``, wrapped in the batch envelope over the core shapes. One ``TypeAdapter`` per form
validates submissions (strict JSON) and exports the draft 2020-12 JSON Schema in validation mode
through a deterministic generator (no titles, ``$schema`` set). The decoding form is a pure transform
of the model-facing schema with structural checks of the backend rules.
"""

from __future__ import annotations

import copy
import json
from typing import Annotated, Any, Literal, Union

from pydantic import Field, TypeAdapter, create_model
from pydantic.json_schema import GenerateJsonSchema

from . import core_shapes as C
from .pack import Pack

DRAFT = "https://json-schema.org/draft/2020-12/schema"
FORMS = ("model", "stored")


def lit(values) -> Any:
    values = tuple(values)
    return Literal[values]  # type: ignore[valid-type]


class Generator(GenerateJsonSchema):
    """Deterministic draft 2020-12 output without titles."""

    def field_title_should_be_set(self, schema) -> bool:  # noqa: D102
        return False

    def generate(self, schema, mode="validation"):  # noqa: D102
        out = super().generate(schema, mode=mode)
        out = _strip(out, {"title"})
        return {"$schema": DRAFT, **out}


def _strip(node, keys: set[str]):
    if isinstance(node, dict):
        return {k: _strip(v, keys) for k, v in node.items() if k not in keys or not isinstance(v, str)}
    if isinstance(node, list):
        return [_strip(v, keys) for v in node]
    return node


class BatchCompiler:
    def __init__(self, pack: Pack):
        self.pack = pack
        self.models: dict[str, dict[str, type]] = {f: {} for f in FORMS}
        self.adapters = {f: TypeAdapter(self.batch_model(f)) for f in FORMS}

    # ---------------------------------------------------------------- positions by object kind

    def position(self, kind: str, rng: str, form: str, map_value: str | None = None) -> Any:
        p = self.pack
        if kind == "entity":
            return C.EntityRef
        if kind == "formula":
            return C.Formula
        if kind == "set":
            return C.SetValue
        if kind == "phrase":
            return C.FORM_PHRASE[form]
        if kind == "condition":
            return C.FORM_CONDITION[form]
        if kind == "interval":
            return C.IntervalValue
        if kind == "map":
            return dict[str, {"formula": C.Formula, "set": C.SetValue}.get(map_value, str)]
        if kind == "enum":
            return lit(p.enum_values(rng))
        if kind == "text":
            return str
        raise ValueError(f"no position for {kind}")

    def object_type(self, pred: str, form: str) -> Any:
        i = self.pack.predicates[pred]
        if i.object_kind == "enum":
            return create_model(
                f"Enum_{i.range}",
                __base__=C.EnumValue,
                t=(Literal["enum"], ...),
                enum=(Literal[i.range], ...),  # type: ignore[valid-type]
                v=(lit(self.pack.enum_values(i.range)), ...),
            )
        return self.position(i.object_kind, i.range, form)

    def qualifiers_model(self, pred: str, form: str) -> type:
        fields: dict[str, Any] = {}
        for q in self.pack.predicate_qualifiers(pred):
            qi = self.pack.qualifiers[q]
            if q == "scope" and form == "stored":
                t = C.ScopeSt
            else:
                t = self.position(qi.object_kind, qi.range, form, qi.map_value_kind)
            if q == "modality":
                fields[q] = (t, Field("asserted", exclude_if=lambda v: v == "asserted"))
            elif q == "polarity":
                fields[q] = (t, Field("positive", exclude_if=lambda v: v == "positive"))
            else:
                fields[q] = (t, None)
        return create_model(f"Q_{pred}_{form}", __base__=C.Core, **fields)

    def claim_model(self, pred: str, form: str) -> type:
        p = self.pack
        qm = self.qualifiers_model(pred, form)
        m = create_model(
            f"Claim_{pred}_{form}",
            __base__=C.Core,
            local_ref=(str, ...),
            predicate=(Literal[pred], ...),  # type: ignore[valid-type]
            subject=(str, ...),
            object=(self.object_type(pred, form), ...),
            qualifiers=(qm, Field(default_factory=qm)),
            statement=(str, None),
            statement_role=(lit(p.enum_values("StatementRole")), None),
            evidence=(tuple[C.FORM_EVIDENCE[form], ...], Field(min_length=1)),
        )
        self.models[form][pred] = m
        return m

    def entity_model(self, form: str) -> type:
        p = self.pack
        fields: dict[str, Any] = dict(
            local_ref=(str, ...),
            type=(lit(p.batch_entity_types()), ...),
            label=(str, ...),
            scope=(Literal["global", "local"], ...),
            extent=(Literal["statement", "section"], None),
            symbol=(str, None),
            aliases=(tuple[str, ...], ()),
            identity=(dict[str, str], Field(default_factory=dict)),
        )
        if form == "stored":
            fields["scope_segment"] = (str, None)
        return create_model(f"Entity_{form}", __base__=C.Core, **fields)

    def statement_model(self, form: str) -> type:
        kinds = lit(self.pack.enum_values("StatementKind"))
        anchor = Union[Literal["unit", "outside"], Annotated[tuple[str, ...], Field(min_length=1)]] if form == "model" \
            else Union[Literal["outside"], Annotated[tuple[str, ...], Field(min_length=1)]]
        return create_model(f"Statement_{form}", __base__=C.Core, local_ref=(str, ...), kind=(kinds, ...), anchor=(anchor, ...))

    def batch_model(self, form: str) -> type:
        claims = [self.claim_model(p, form) for p in self.pack.predicates]
        claim = Annotated[Union[tuple(claims)], Field(discriminator="predicate")]
        return create_model(
            f"ClaimProposalBatch_{form}",
            __base__=C.Core,
            unit_ref=(str, ...),
            entities=(tuple[self.entity_model(form), ...], ()),
            statements=(tuple[self.statement_model(form), ...], ()),
            claims=(tuple[claim, ...], ()),
            alternatives=(tuple[C.AlternativeItem, ...], ()),
            unsupported=(tuple[C.FORM_UNSUPPORTED[form], ...], ()),
        )

    # ---------------------------------------------------------------- outputs

    def json_schema(self, form: str) -> dict:
        return self.adapters[form].json_schema(mode="validation", schema_generator=Generator)

    def validate(self, raw_text: str, form: str):
        return self.adapters[form].validate_json(raw_text, strict=True)


# ------------------------------------------------------------------------ decoding form (D2 §7.3)

DECODING_DROP = {"discriminator", "description", "default", "examples", "title"}
FORBIDDEN = {"if", "then", "else", "not", "multipleOf", "uniqueItems", "contains", "minContains", "maxContains",
             "dependentRequired", "dependentSchemas", "propertyNames", "format", "patternProperties"}


def decoding_form(model_schema: dict) -> dict:
    """The structured-output schema: the model-facing schema with non-JSON-Schema and model-invisible
    keywords removed (``discriminator`` is OpenAPI; descriptions are not shown to a constrained model)."""

    def walk(node, parent_key=None):
        if isinstance(node, dict):
            out = {}
            for k, v in node.items():
                # property *names* such as a field called "default" are kept; only keywords are dropped
                if parent_key != "properties" and k in DECODING_DROP:
                    continue
                out[k] = walk(v, k)
            return out
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    out = walk(copy.deepcopy(model_schema))
    defs = out.get("$defs", {})

    def inline(node):
        # xgrammar 0.2.7 proves a oneOf's branches disjoint only when they are inline: a $ref branch
        # falls back to anyOf (S4-D probe). Inline each branch one level; refs inside stay refs.
        if isinstance(node, dict):
            res = {k: inline(v) for k, v in node.items()}
            if isinstance(res.get("oneOf"), list):
                res["oneOf"] = [copy.deepcopy(defs[b["$ref"].split("/")[-1]]) if set(b) == {"$ref"} else b for b in res["oneOf"]]
            return res
        if isinstance(node, list):
            return [inline(v) for v in node]
        return node

    # inline inside the definitions first, so a branch copied from a definition carries inline branches too
    for name in list(defs):
        defs[name] = inline(defs[name])
    out["$defs"] = defs
    return inline(out)


def structural_checks(schema: dict) -> dict:
    """The D2 §7.3 decoding-form rules, checked on the schema text."""
    issues, depth_max = [], 0
    oneofs = anyofs = 0

    def depth(node, d=0):
        nonlocal depth_max
        depth_max = max(depth_max, d)
        if isinstance(node, dict):
            for v in node.values():
                depth(v, d + 1)
        elif isinstance(node, list):
            for v in node:
                depth(v, d + 1)

    def walk(node, path, parent_key=None):
        nonlocal oneofs, anyofs
        if isinstance(node, dict):
            for k, v in node.items():
                if parent_key != "properties":
                    if k in FORBIDDEN:
                        issues.append(f"{path}/{k}: forbidden keyword")
                    if k in DECODING_DROP:
                        issues.append(f"{path}/{k}: keyword the decoding form drops")
                    if k == "allOf" and isinstance(v, list) and len(v) > 1:
                        issues.append(f"{path}/allOf: more than one branch")
                    if k == "pattern" and any(x in node for x in ("minLength", "maxLength")):
                        issues.append(f"{path}: pattern with length bounds")
                    if k == "oneOf":
                        oneofs += 1
                        tags = [_const_tag(b, schema) for b in v]
                        props = {t[0] for t in tags if t}
                        seen: list[str] = [x for t in tags if t for x in t[1]]
                        if None in tags or len(props) != 1 or len(seen) != len(set(seen)):
                            issues.append(f"{path}/oneOf: branches not disjoint by one const or enum property")
                    if k == "anyOf":
                        anyofs += 1
                walk(v, f"{path}/{k}", k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}/{i}")

    walk(schema, "#")
    depth(schema)
    return {"issues": issues, "json_depth": depth_max, "oneOf": oneofs, "anyOf": anyofs,
            "bytes_compact": len(json.dumps(schema, separators=(",", ":"), sort_keys=True))}


def _resolve(node: dict, root: dict) -> dict:
    while isinstance(node, dict) and "$ref" in node:
        name = node["$ref"].split("/")[-1]
        node = root["$defs"][name]
    return node


def _const_tag(branch: dict, root: dict):
    """(property, frozenset of allowed values) that makes a oneOf branch distinct, or None."""
    b = _resolve(branch, root)
    for prop, s in (b.get("properties") or {}).items():
        if prop in (b.get("required") or []):
            if "const" in s:
                return [prop, [s["const"]]]
            if "enum" in s and prop in ("t", "op", "bind", "predicate"):
                return [prop, sorted(s["enum"])]
    return None
