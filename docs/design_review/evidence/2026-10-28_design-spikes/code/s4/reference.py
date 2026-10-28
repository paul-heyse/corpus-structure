"""The annotator-reference compiler (D2 §7.5, §10.10): generated from SchemaView, the compiled batch
models and the rules file, with the pack's worked examples.

Sources per part: entity types (entity classes: description, ci:scope, unique_keys, examples); predicate
cards grouped by the pack's subsets (domain, range, the object's exact shape from the compiled model,
description, the predicate's own qualifiers, ci:functional, symmetric, transitive), each with the
guideline rules that apply to it (rules.yaml ``guideline:``, by ``applies_to``) and the subsets'
descriptions; the role and modality tables (``tables:``); qualifiers and enums with their
descriptions; the exact shapes of values, bindings, condition nodes and batch items, rendered from the
core Pydantic models; the worked examples from ``reference/``. No predicate, class or subset name and
no rule text is written here.
"""

from __future__ import annotations

import json
import typing
from typing import Literal, Union, get_args, get_origin

from pydantic import BaseModel

from . import core_shapes as C
from . import paths
from .batch_models import BatchCompiler
from .pack import Pack

GROUP_ORDER_TITLE = "Claims in no predicate subset"


def _one(s: str) -> str:
    return " ".join(str(s or "").split())


def _strip(t):
    while get_origin(t) is typing.Annotated:
        t = get_args(t)[0]
    if hasattr(t, "__value__"):
        return _strip(t.__value__)
    return t


def shape(t, depth: int = 0) -> str:
    """A compact JSON-like template of a type (fields in declaration order; ``?`` marks optional)."""
    t = _strip(t)
    o = get_origin(t)
    if o is Literal:
        vals = get_args(t)
        return json.dumps(vals[0]) if len(vals) == 1 else " | ".join(json.dumps(v) for v in vals)
    if o in (Union, typing.Union) or type(t).__name__ == "UnionType":
        names: list[str] = []
        for a in get_args(t):
            n = _name(_strip(a))
            if n not in names:
                names.append(n)
        return " | ".join(names)
    if o is tuple:
        return f"[{_name(_strip(get_args(t)[0]))}, …]"
    if o is dict:
        return f"{{<key>: {_name(_strip(get_args(t)[1]))}}}"
    if isinstance(t, type) and issubclass(t, BaseModel):
        parts = []
        for n, f in t.model_fields.items():
            q = "" if f.is_required() else "?"
            parts.append(f'"{n}"{q}: {shape(f.annotation, depth + 1) if depth < 1 else _name(_strip(f.annotation))}')
        return "{" + ", ".join(parts) + "}"
    return {str: "<string>", int: "<integer>", bool: "<boolean>"}.get(t, getattr(t, "__name__", str(t)))


_NAMES = {"Formula": "formula", "SetValue": "set", "EntityRef": "entity ref", "PhraseMF": "phrase", "NumberValue": "number",
          "DateValue": "date", "EvidenceMF": "evidence", "IntervalValue": "interval", "EntityBinding": "binding",
          "ClaimBinding": "binding", "BareBinding": "binding", "AlternativeItem": "alternative", "UnsupportedMF": "unsupported",
          "Entity_model": "entity", "Statement_model": "statement"}


def _name(t) -> str:
    if isinstance(t, type) and issubclass(t, BaseModel):
        n = t.__name__
        if n.startswith("Claim_"):
            return "<claim>"
        if n in C.__dict__ and "op" in t.model_fields:
            return "<condition>"
        return "<" + _NAMES.get(n, n) + ">"
    if get_origin(t) is Literal:
        return shape(t)
    if get_origin(t) in (tuple, dict) or get_origin(t) in (Union, typing.Union) or type(t).__name__ == "UnionType":
        return shape(t, 2)
    if hasattr(t, "__name__") and t.__name__.startswith("Condition"):
        return "<condition>"
    return {str: "<string>", int: "<integer>", bool: "<boolean>"}.get(t, "<" + getattr(t, "__name__", str(t)) + ">")


def generate(pack: Pack, bc: BatchCompiler, examples: dict[str, tuple[str, dict]], kinds: set[str] | None = None) -> dict[str, str]:
    """The reference as named parts (so they can be sized); ``kinds`` filters the worked examples to
    those with a statement of one of the kinds (V4)."""
    sv, rf = pack.sv, pack.rules
    parts: dict[str, list[str]] = {}
    head = ["# Annotation reference (generated from the schema)", "",
            "Schemas " + ", ".join(f"`{s.name}` {s.version}" for k, s in sv.schema_map.items() if s.version) + ". "
            "The guideline says what to capture; this says how to write it: which entity type, which predicate, "
            "which qualifiers, how claims take roles, modality and conditions, the exact shape of every item.", ""]
    parts["head"] = head

    # 1 entity types
    L = ["## 1. Entity types", "", "| Type | What it is | Scope | Identity slots | Examples |", "|---|---|---|---|---|"]
    for c in pack.batch_entity_types():
        el = sv.get_class(c)
        L.append(f"| `{c}` | {_one(el.description)} | {pack.scope(c)} | {', '.join(pack.identity_keys(c)) or '—'} | "
                 f"{', '.join(str(e.value) for e in el.examples) or '—'} |")
    st = bc.statement_model("model")
    L += ["", f"`Statement` ({_one(sv.get_class('Statement').description)}) is a `statements[]` item: `{shape(st)}`; "
          "anchor `\"unit\"`, the sentence ids it lies in, or `\"outside\"` for a statement outside the unit that the unit refers to.",
          f"An `entities[]` item: `{shape(bc.entity_model('model'))}`. A local entity has an `extent`; identity holds the class's "
          "identity slots, an entity-valued slot as a local-ref string.", ""]
    parts["entities"] = L

    # 2 predicates by subset
    guide = [(g, set(pack.expand_applies_to(g.applies_to))) for g in rf.guideline]
    used: dict[str, list[str]] = {}
    for eid, (_, b) in sorted(examples.items()):
        for c in b.get("claims", []):
            used.setdefault(c["predicate"], []).append(f"{eid} `{c['local_ref']}`")
    L = ["## 2. Predicates", "", "Grouped by the schema's predicate subsets; a predicate in two subsets is listed under the first.", ""]
    done: set[str] = set()
    groups = [(str(s), pack.subsets[str(s)]) for s in sv.all_subsets()] + [(None, [p for p in pack.predicates if not pack.predicates[p].subsets])]
    for sname, preds in groups:
        preds = [p for p in preds if p not in done]
        if not preds:
            continue
        L += [f"### {sname or GROUP_ORDER_TITLE}", ""]
        if sname:
            L += [pack.subset_description(sname), ""]
        for p in preds:
            done.add(p)
            i = pack.predicates[p]
            obj = bc.models["model"][p].model_fields["object"].annotation
            L.append(f"#### `{p}`")
            L.append("")
            L.append(f"- **Subject:** {i.domain}. **Object:** {i.range} as `{shape(obj) if i.object_kind == 'enum' else _name(_strip(obj))}`.")
            L.append(f"- **Meaning:** {i.description}")
            if i.qualifiers:
                L.append(f"- **Its qualifiers:** {', '.join(f'`{q}`' for q in i.qualifiers)} (besides the core qualifiers).")
            flags = [x for x, on in (("one object per subject in a statement", i.functional), ("symmetric", i.symmetric),
                                     ("transitive", i.transitive)) if on]
            if len(i.subsets) > 1:
                flags.append("also in " + ", ".join(s for s in i.subsets if s != sname))
            if flags:
                L.append(f"- **Also:** {'; '.join(flags)}.")
            rules = [g for g, ps in guide if p in ps and g.applies_to != "any"]
            if rules:
                L.append("- **Rules:** " + " ".join(_one(g.description) for g in rules))
            if used.get(p):
                L.append(f"- **In the worked examples:** {', '.join(used[p])}.")
            L.append("")
    general = [g for g, _ in guide if g.applies_to == "any"]
    L += ["### Rules for every claim", ""] + [f"- {_one(g.description)}" for g in general] + [""]
    parts["predicates"] = L

    # 3 roles and modality tables
    L = ["## 3. Statement roles and modality", ""]
    for name, table in rf.tables.items():
        L.append(f"`{name}`:")
        L.append("")
        for k, v in table.items():
            L.append(f"- {k}: {', '.join(map(str, v)) if isinstance(v, list) else v}" + (" (none: no statement_role)" if v == ["none"] else ""))
        L.append("")
    parts["tables"] = L

    # 4 qualifiers
    q = bc.models["model"]
    L = ["## 4. Qualifiers", "", "Core qualifiers are allowed on every predicate; the others only where a card lists them. "
         "An absent qualifier is omitted, never null; `modality` defaults to `asserted`, `polarity` to `positive`.", "",
         "| Qualifier | Value | Meaning |", "|---|---|---|"]
    allq = {}
    for p, m in q.items():
        for n, f in m.model_fields["qualifiers"].annotation.model_fields.items():
            allq.setdefault(n, f.annotation)
    for n, qi in pack.qualifiers.items():
        L.append(f"| `{n}`{' (core)' if qi.core else ''} | `{shape(allq[n]) if get_origin(_strip(allq[n])) is Literal else _name(_strip(allq[n]))}` | {qi.description} |")
    parts["qualifiers"] = L + [""]

    # 5 enums
    L = ["## 5. Enumerations", ""]
    for n in pack.enums:
        e = sv.get_enum(n)
        L.append(f"- **{n}:** " + "; ".join(f"`{k}`" + (f" ({_one(v.description)})" if v.description else "") for k, v in e.permissible_values.items()))
    parts["enums"] = L + [""]

    # 6 shapes
    L = ["## 6. Exact shapes", "", "Fields marked `?` may be omitted; an omitted field is absent, never `null`.", "", "| Item | Shape |", "|---|---|"]
    for tag, m in C.VALUE_MODELS["model"].items():
        L.append(f"| {tag} value | `{shape(m)}` |")
    L.append(f"| entity reference | `{shape(C.EntityRef)}` (objects, entity qualifiers and `pred` arguments) |")
    for m in (C.EntityBinding, C.ClaimBinding, C.BareBinding):
        L.append(f"| binding | `{shape(m)}` |")
    for m in (C.AndMF, C.NotMF, C.ClaimNode, C.MemberNode, C.CmpNode, C.PredNode, C.ForallMF, C.PhraseNodeMF, C.UnsupportedNodeMF):
        L.append(f"| condition node | `{shape(m)}` |")
    L.append(f"| map qualifier | `{{<canonical name>: <formula>}}` (`param_values`, `param_symbols`), `{{<canonical name>: <string>}}` (`param_mapping`) |")
    L.append(f"| evidence | `{shape(C.EvidenceMF)}`; sentence `sN` of the unit or `cN` of its standing context; quote an exact substring |")
    L.append(f"| alternative | `{shape(C.AlternativeItem)}` |")
    L.append(f"| unsupported | `{shape(C.UnsupportedMF)}` |")
    L.append(f"| claim | `{shape(bc.models['model'][next(iter(pack.predicates))]).replace(json.dumps(next(iter(pack.predicates))), '<predicate>')}` |")
    L.append(f"| batch | `{shape(bc.batch_model('model'))}` |")
    L += ["", "Condition predicates (`pred` `name`): " + "; ".join(
        f"`{k}` ({a.get('ci:arity')} {a.get('ci:args')})" for k, a in pack.pv_annotations("ConditionPredicate").items()), ""]
    parts["shapes"] = L

    # 7 worked examples
    L = ["## 7. Worked examples", ""]
    for eid, (packet, b) in sorted(examples.items()):
        if kinds is not None and not ({s["kind"] for s in b.get("statements", [])} & kinds):
            continue
        L += [f"### {eid}", "", "Packet:", "", "```text", packet.rstrip(), "```", "", "Batch:", "", "```json",
              json.dumps(b, indent=1, ensure_ascii=False), "```", ""]
    parts["examples"] = L
    return {k: "\n".join(v) + "\n" for k, v in parts.items()}


def load_examples() -> dict[str, tuple[str, dict]]:
    out = {}
    for d in sorted(p for p in paths.PACK_REFERENCE.iterdir() if p.is_dir()):
        out[d.name] = ((d / "packet.md").read_text(encoding="utf-8"), json.loads((d / "batch.json").read_text(encoding="utf-8")))
    return out
