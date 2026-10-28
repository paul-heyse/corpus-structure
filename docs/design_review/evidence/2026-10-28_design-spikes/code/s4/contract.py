"""The mirror contract test (D2 §6; schema-rules note L-01): the core Pydantic shapes against the
value classes of core.yaml, field by field through SchemaView.

The two declarations are authored independently, so the comparison is non-circular. Compared per
batch form: the set of value tags; per tag, field names, required-ness (``required`` or
``ci:required_in: <form>``), multivalued-ness and the scalar or class range; the binding kinds
against BindKind and the binding fields against SymbolBinding; EntityRef; EvidenceRole. A field
annotated ``ci:form`` belongs only to that form (``consolidated``: to neither batch form).
"""

from __future__ import annotations

import types
import typing
from typing import Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel

from . import core_shapes as C
from .pack import Pack, annotations

SCALARS = {"string": str, "boolean": bool, "integer": int}


def _strip_annotated(t):
    while get_origin(t) is typing.Annotated:
        t = get_args(t)[0]
    if hasattr(t, "__value__"):  # TypeAliasType
        return _strip_annotated(t.__value__)
    return t


def _members(t) -> list:
    t = _strip_annotated(t)
    if get_origin(t) in (Union, types.UnionType):
        out = []
        for a in get_args(t):
            out += _members(a)
        return out
    return [t]


def _tags(t) -> set[str]:
    out = set()
    for m in _members(t):
        if isinstance(m, type) and issubclass(m, BaseModel) and "t" in m.model_fields:
            out |= set(get_args(m.model_fields["t"].annotation))
    return out


def _is_multi(t) -> bool:
    t = _strip_annotated(t)
    return get_origin(t) in (tuple, dict, list)


def compare(pack: Pack, value_models: dict[str, dict[str, type]] | None = None) -> list[str]:
    sv = pack.sv
    value_models = value_models or C.VALUE_MODELS
    out: list[str] = []
    tag_of = pack.value_classes  # class -> tag
    cls_of = {t: c for c, t in tag_of.items()}

    def range_tags(rng: str) -> set[str]:
        cs = [rng] + list(sv.class_descendants(rng)) if rng in sv.all_classes() else []
        return {tag_of[c] for c in cs if c in tag_of}

    for form, models in value_models.items():
        if set(models) != set(cls_of):
            out.append(f"{form}: tags differ: pydantic {sorted(models)} linkml {sorted(cls_of)}")
        for tag in sorted(set(models) & set(cls_of)):
            m, cname = models[tag], cls_of[tag]
            slots = {}
            for s in sv.class_induced_slots(cname):
                f = annotations(s).get("ci:form")
                if s.name == "t" or (f is not None and f != form):
                    continue
                slots[s.name] = s
            fields = {k: v for k, v in m.model_fields.items() if k != "t"}
            if set(slots) != set(fields):
                out.append(f"{form} {tag}: fields differ: pydantic {sorted(fields)} linkml {sorted(slots)}")
            if sv.induced_slot("t", cname).equals_string != get_args(m.model_fields["t"].annotation)[0]:
                out.append(f"{form} {tag}: tag differs")
            for n in sorted(set(slots) & set(fields)):
                s, fi = slots[n], fields[n]
                req = bool(s.required) or annotations(s).get("ci:required_in") == form
                if req != fi.is_required():
                    out.append(f"{form} {tag}.{n}: required pydantic {fi.is_required()} linkml {req}")
                if bool(s.multivalued) != _is_multi(fi.annotation):
                    out.append(f"{form} {tag}.{n}: multivalued pydantic {_is_multi(fi.annotation)} linkml {bool(s.multivalued)}")
                rng = s.range or "string"
                if rng in SCALARS:
                    if _strip_annotated(fi.annotation) is not SCALARS[rng]:
                        out.append(f"{form} {tag}.{n}: range pydantic {fi.annotation} linkml {rng}")
                elif rng in tag_of or rng == "Value":
                    pt = _tags(fi.annotation)
                    if not pt or not pt <= range_tags(rng):
                        out.append(f"{form} {tag}.{n}: tags {sorted(pt)} not within {rng} {sorted(range_tags(rng))}")
                elif rng == "SymbolBinding":
                    if get_origin(_strip_annotated(fi.annotation)) is not dict:
                        out.append(f"{form} {tag}.{n}: symbols is not a map")
                elif rng in sv.all_enums():
                    pass
                else:
                    out.append(f"{form} {tag}.{n}: unchecked range {rng}")
    # bindings
    bind_models = _members(C.Binding)
    kinds = {k for m in bind_models for k in get_args(m.model_fields["bind"].annotation)}
    if kinds != set(pack.enum_values("BindKind")):
        out.append(f"bind kinds differ: pydantic {sorted(kinds)} linkml {pack.enum_values('BindKind')}")
    bfields = {k for m in bind_models for k in m.model_fields}
    sb = {s.name for s in sv.class_induced_slots("SymbolBinding") if not s.identifier}
    if bfields != sb:
        out.append(f"binding fields differ: pydantic {sorted(bfields)} linkml {sorted(sb)}")
    # entity reference
    if set(C.EntityRef.model_fields) != {s.name for s in sv.class_induced_slots("EntityRef")}:
        out.append("EntityRef fields differ")
    # evidence roles
    if set(get_args(C.EvidenceRole)) != set(pack.enum_values("EvidenceRole")):
        out.append("evidence roles differ")
    return out


def mutated_pydantic() -> dict[str, dict[str, type]]:
    """The value models with NumberValue's ``basis`` dropped on the Pydantic side."""
    from pydantic import create_model

    nv = create_model("NumberValue", __base__=C.Core, t=(Literal["number"], ...), v=(str, ...), unit=(str, None))
    vm = {f: dict(m) for f, m in C.VALUE_MODELS.items()}
    for f in vm:
        vm[f]["number"] = nv
    return vm


def _unused(*_: Any) -> None:  # keep typing imports referenced for readers
    return None
