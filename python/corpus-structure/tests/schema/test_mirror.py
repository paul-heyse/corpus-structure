"""The interim mirror guard (TM §12; model and projections §3.2): until Stage B generates the shapes
(P0-M-5), every shape fact Stage A does not generate is compared between the hand-written Pydantic
shapes and `model/core.yaml`, through `SchemaView`.

Per batch form (`model` is the authored form): each class's fields (an attribute counts in a form
by its `ci:form`; a `consolidated` one in both), their required-ness (`required`, or
`ci:required_in` for that form) and multivalued-ness, the value and condition tags (`t`, `op`), the
static enum each enum-ranged field takes, and the core qualifiers with their stored aliases and
the form-dependent `scope` range (`ci:stored_range`). The closed sets themselves (bind kinds,
evidence roles, …) and the binding fields per kind are generated, so they are not compared here.
A seeded difference on either side fails.

The source-profile half of the guard waits for ingest's profile model (P0-I-1a): there is none yet.
"""

from __future__ import annotations

import types
import typing
from pathlib import Path
from typing import Any

import pytest
import yaml
from linkml_runtime.utils.schemaview import SchemaView
from pydantic import BaseModel, create_model

from corpus_structure.core import batch, values, vocab
from corpus_structure.schema.model import CORE, ci_annotations

V, B = values, batch
BOTH = ("model", "stored")

# model class -> (authored shape, stored shape); None where a form has no such class
PAIRS: dict[str, tuple[type[BaseModel] | None, type[BaseModel] | None]] = {
    "TextValue": (V.TextValue, V.TextValue),
    "NumberValue": (V.NumberValue, V.NumberValue),
    "BoolValue": (V.BoolValue, V.BoolValue),
    "EnumValue": (V.EnumValue, V.EnumValue),
    "Formula": (V.Formula, V.Formula),
    "SetExpr": (V.SetValue, V.SetValue),
    "DateValue": (V.DateValue, V.DateValue),
    "IntervalValue": (V.IntervalValue, V.IntervalValue),
    "PhraseValue": (V.AuthoredPhrase, V.StoredPhrase),
    "EntityRef": (V.EntityRef, V.EntityRef),
    "SymbolBinding": (V.SymbolBinding, V.SymbolBinding),
    "AndNode": (V.AuthoredAnd, V.StoredAnd),
    "OrNode": (V.AuthoredOr, V.StoredOr),
    "NotNode": (V.AuthoredNot, V.StoredNot),
    "ForallNode": (V.AuthoredForall, V.StoredForall),
    "ClaimNode": (V.ClaimNode, V.ClaimNode),
    "MemberNode": (V.MemberNode, V.MemberNode),
    "CmpNode": (V.CmpNode, V.CmpNode),
    "PredNode": (V.PredNode, V.PredNode),
    "PhraseNode": (V.AuthoredPhraseNode, V.StoredPhraseNode),
    "UnsupportedNode": (V.AuthoredUnsupportedNode, V.StoredUnsupportedNode),
    "StoredScope": (None, B.StoredScope),
    "Evidence": (B.AuthoredEvidence, B.StoredEvidence),
    "EntityItem": (B.AuthoredEntity, B.StoredEntity),
    "StatementItem": (B.AuthoredStatement, B.StoredStatement),
    "ClaimItem": (B.AuthoredClaim, B.StoredClaim),
    "AlternativeItem": (B.AlternativeItem, B.AlternativeItem),
    "UnsupportedItem": (B.AuthoredUnsupported, B.StoredUnsupported),
    "Batch": (B.AuthoredBatch, B.StoredBatch),
}

STATIC_ENUMS = {
    cls.__name__: cls for cls, lc in vocab.LIFECYCLE.items() if lc is vocab.Lifecycle.STATIC
}


def _members(annotation: Any) -> list[Any]:
    """The types a field annotation names, through unions, `Annotated` and containers."""
    if typing.get_origin(annotation) is typing.Annotated:
        return _members(typing.get_args(annotation)[0])
    if isinstance(annotation, typing.TypeAliasType):
        return _members(annotation.__value__)
    origin = typing.get_origin(annotation)
    if origin in (typing.Union, types.UnionType, tuple, dict, typing.Literal):
        out = [annotation] if origin is typing.Literal else []
        for arg in typing.get_args(annotation):
            if arg is not Ellipsis and origin is not typing.Literal:
                out += _members(arg)
        return out
    return [annotation]


def _non_missing(annotation: Any) -> list[Any]:
    if typing.get_origin(annotation) in (typing.Union, types.UnionType):
        return [a for a in typing.get_args(annotation) if repr(a) != "MISSING"]
    return [annotation]


def hand_facts(cls: type[BaseModel]) -> dict[str, tuple[bool, bool | None]]:
    out: dict[str, tuple[bool, bool | None]] = {}
    for name, info in cls.model_fields.items():
        kinds = _non_missing(info.annotation)
        multivalued = None
        if len(kinds) == 1:
            base = kinds[0]
            if typing.get_origin(base) is typing.Annotated:
                base = typing.get_args(base)[0]
            multivalued = typing.get_origin(base) in (tuple, dict)
        out[name] = (info.is_required(), multivalued)
    return out


def model_facts(view: Any, cls: str, form: str) -> dict[str, tuple[bool, bool, Any]]:
    out: dict[str, tuple[bool, bool, Any]] = {}
    for slot in view.class_induced_slots(cls):
        ann = ci_annotations(slot)
        present_in = ann.get("ci:form")
        if present_in not in (None, form, "consolidated"):
            continue
        required = bool(slot.required) or ann.get("ci:required_in") == form
        out[str(slot.name)] = (required, bool(slot.multivalued), slot)
    return out


def differences(view: Any, pairs: dict = PAIRS) -> list[str]:
    found: list[str] = []
    for cls, shapes in pairs.items():
        for form, shape in zip(BOTH, shapes, strict=True):
            if shape is None:
                continue
            where = f"{cls}/{form} ({shape.__name__})"
            mine, theirs = model_facts(view, cls, form), hand_facts(shape)
            for name in sorted(set(mine) ^ set(theirs)):
                side = "the model" if name in mine else "the Pydantic shape"
                found.append(f"{where}: only {side} has {name!r}")
            for name in sorted(set(mine) & set(theirs)):
                required, multivalued, slot = mine[name]
                hand_required, hand_multivalued = theirs[name]
                if required != hand_required:
                    found.append(f"{where}.{name}: required {required} vs {hand_required}")
                if hand_multivalued is not None and multivalued != hand_multivalued:
                    found.append(f"{where}.{name}: multivalued {multivalued} vs {hand_multivalued}")
                annotation = shape.model_fields[name].annotation
                if name in ("t", "op") and slot.equals_string:
                    tags = [typing.get_args(a) for a in _members(annotation)
                            if typing.get_origin(a) is typing.Literal]  # fmt: skip
                    if tags != [(slot.equals_string,)]:
                        found.append(f"{where}.{name}: tag {slot.equals_string!r} vs {tags}")
                rng = str(slot.range)
                if rng in STATIC_ENUMS and STATIC_ENUMS[rng] not in _members(annotation):
                    found.append(f"{where}.{name}: the shape does not take {rng}")
    found += _qualifier_differences(view)
    return found


def _qualifier_differences(view: Any) -> list[str]:
    found: list[str] = []
    core = [str(n) for n, s in view.schema.slots.items()
            if ci_annotations(s).get("ci:role") == "qualifier"]  # fmt: skip
    for form, shape in (("model", batch.AuthoredQualifiers), ("stored", batch.StoredQualifiers)):
        fields = shape.model_fields
        if set(fields) != set(core):
            found.append(f"qualifiers/{form}: {sorted(fields)} vs the model's {sorted(core)}")
        for name in set(fields) & set(core):
            slot = view.get_slot(name)
            alias = fields[name].alias
            if form == "stored" and alias != f"core:{name}":
                found.append(f"qualifiers/stored.{name}: alias {alias!r}")
            rng = ci_annotations(slot).get("ci:stored_range") if form == "stored" else None
            rng = str(rng or slot.range)
            named = {getattr(m, "__name__", None) for m in _members(fields[name].annotation)}
            hand_range = {"Condition": {"AuthoredAnd", "StoredAnd"},
                          "PhraseValue": {"AuthoredPhrase", "StoredPhrase"},
                          "Entity": {"EntityRef"}}.get(rng, {rng})  # fmt: skip
            if not named & hand_range:
                found.append(f"qualifiers/{form}.{name}: range {rng} vs {sorted(map(str, named))}")
    return found


@pytest.fixture(scope="module")
def view() -> SchemaView:
    return SchemaView(str(CORE))


def test_the_hand_shapes_mirror_the_model(view: SchemaView) -> None:
    assert differences(view) == []


def _attr(data: dict, cls: str, name: str) -> dict:
    return data["classes"][cls]["attributes"][name]


def edited_view(tmp_path: Path, edit) -> SchemaView:
    data = yaml.safe_load(CORE.read_text(encoding="utf-8"))
    edit(data)
    path = tmp_path / "core.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return SchemaView(str(path))


@pytest.mark.parametrize(
    ("edit", "expected"),
    [
        (lambda d: d["classes"]["NumberValue"]["attributes"].pop("basis"),
         "NumberValue/model (NumberValue): only the Pydantic shape has 'basis'"),
        (lambda d: d["classes"]["TextValue"]["attributes"].update({"lang": {"description": "x"}}),
         "TextValue/stored (TextValue): only the model has 'lang'"),
        (lambda d: _attr(d, "PhraseValue", "start")["annotations"].pop("ci:required_in"),
         "PhraseValue/stored (StoredPhrase).start: required False vs True"),
        (lambda d: _attr(d, "Evidence", "quote")["annotations"].update({"ci:form": "stored"}),
         "Evidence/model (AuthoredEvidence): only the Pydantic shape has 'quote'"),
        (lambda d: d["classes"]["CmpNode"]["slot_usage"]["op"].update({"equals_string": "compare"}),
         "CmpNode/model (CmpNode).op: tag 'compare'"),
        (lambda d: d["slots"]["scope"]["annotations"].pop("ci:stored_range"),
         "qualifiers/stored.scope: range ScopeExtent"),
        (lambda d: d["slots"].update({"weight": {"description": "x",
                                                 "annotations": {"ci:role": "qualifier"}}}),
         "qualifiers/model:"),
    ],
)  # fmt: skip
def test_a_seeded_model_side_difference_fails(tmp_path: Path, edit, expected: str) -> None:
    found = differences(edited_view(tmp_path, edit))
    assert any(expected in f for f in found), found


def test_a_seeded_shape_side_difference_fails(view: SchemaView) -> None:
    with_lang = create_model("TextValue", __base__=values.TextValue, lang=(str, ...))
    found = differences(view, {**PAIRS, "TextValue": (with_lang, values.TextValue)})
    assert found == ["TextValue/model (TextValue): only the Pydantic shape has 'lang'"]
    loose = create_model("SymbolBinding", __base__=values.SymbolBinding, bind=(str, ...))
    found = differences(view, {**PAIRS, "SymbolBinding": (loose, loose)})
    assert "SymbolBinding/model (SymbolBinding).bind: the shape does not take BindKind" in found
