"""Q-1 probe: Stage B as a linkml 1.12.1 PydanticGenerator subclass over SchemaView.

What the subclass keeps from PydanticGenerator: render()'s pipeline (class collection, is_a sorting,
the lifecycle hooks, module assembly) and its Jinja template machinery with template_dir overrides
(code/q1/templates: frozen CoreModel base, PEP 695 `type` aliases, explicit Field sources). What it
overrides: _get_classes (one synthetic ClassDefinition per emitted (class, form)), generate_class,
generate_slot and get_class_slot_range (form-aware ranges, discriminated unions, MISSING, tuples,
prefixed aliases), before_generate_enums (closed sets become Literal or the vocab StrEnums).

The form expansion (ci:form model/stored/consolidated, ci:required_in, ci:stored_range) is computed
over the original SchemaView: a class whose fields, ranges or members differ by form is emitted twice,
Authored<Name> and Stored<Name>; every other class once.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from linkml.generators.pydanticgen import PydanticGenerator
from linkml.generators.pydanticgen.pydanticgen import MetadataMode
from linkml.generators.pydanticgen.template import PydanticAttribute, PydanticClass
from linkml_runtime.linkml_model.meta import ClassDefinition
from linkml_runtime.utils.schemaview import SchemaView

FORM_PREFIX = {"model": "Authored", "stored": "Stored"}
VOCAB_ENUMS = {"EntityScope", "EvidenceRole", "StatementRole"}  # Stage A's vocab.py StrEnums
BUILTIN = {"string": "str", "integer": "int", "boolean": "bool", "float": "float", "double": "float"}
TEMPLATES = Path(__file__).resolve().parent / "templates"


def ann(el, tag: str):
    if el is None or not el.annotations:
        return None
    a = el.annotations
    items = dict(a._items()) if hasattr(a, "_items") else dict(a.items())
    v = items.get(tag)
    return None if v is None else str(getattr(v, "value", v))


def scoped(value: str | None, form: str) -> list[str]:
    """'stored: x; y' -> parts applying in this form ('stored:' / 'model:' prefixes scope a part)."""
    out = []
    for part in [p.strip() for p in (value or "").split(";") if p.strip()]:
        if ":" in part.split("(")[0]:
            f, rest = part.split(":", 1)
            if f.strip() != form:
                continue
            part = rest.strip()
        out.append(part)
    return out


class CoreAttribute(PydanticAttribute):
    field_src: str | None = None


class CoreClass(PydanticClass):
    config: str | None = None
    extra_decl: bool = False
    classvars: list[str] = []
    validators_src: list[str] = []


@dataclass
class Emit:
    name: str
    origin: str
    form: str | None  # None: shared by both forms
    parent: str | None
    alias_of: list[str] | None = None  # a tagged union alias: its member names
    tag: str | None = None


class Plan:
    """The form expansion over the original SchemaView."""

    def __init__(self, sv: SchemaView) -> None:
        self.sv = sv
        self.order = list(sv.all_classes())
        self._dep: dict[str, bool] = {}
        self.emits: dict[tuple[str, str | None], Emit] = {}
        self._visiting: set = set()
        for root in ("Batch", "Value", "Condition"):
            for form in ("model", "stored"):
                self.visit(root, form)

    # -- classification ---------------------------------------------------------------------
    def py(self, c: str) -> str:
        return ann(self.sv.get_class(c), "ci:py_name") or c

    def is_entity(self, c: str) -> bool:
        return c == "Entity" or "Entity" in self.sv.class_ancestors(c)

    def is_map_entry(self, c: str) -> bool:
        return c != "MapEntry" and "MapEntry" in self.sv.class_ancestors(c)

    def concrete_desc(self, c: str) -> list[str]:
        return [d for d in self.order if d != c and c in self.sv.class_ancestors(d)
                and not self.sv.get_class(d).abstract]

    def tag(self, c: str) -> str | None:
        """The slot every concrete descendant fixes by equals_string."""
        desc = self.concrete_desc(c)
        if not desc:
            return None
        for s in self.sv.class_induced_slots(c):
            if all(self.sv.induced_slot(s.name, d).equals_string for d in desc):
                return s.name
        return None

    def is_union(self, c: str) -> bool:
        return bool(self.sv.get_class(c).abstract and self.tag(c) and self.used_as_range(c))

    def used_as_range(self, c: str) -> bool:
        for k in self.order:
            for s in self.sv.class_induced_slots(k):
                if s.range == c or any(a.range == c for a in s.any_of):
                    return True
        return False

    def ordered_slots(self, c: str):
        """Induced slots, ancestors' first (root to c), each class's slots then attributes."""
        sv = self.sv
        names: list[str] = []
        for a in reversed(sv.class_ancestors(c)):
            cd = sv.get_class(a)
            for n in [*cd.slots, *cd.attributes]:
                if n not in names:
                    names.append(n)
        return [sv.induced_slot(n, c) for n in names]

    def slots(self, c: str, form: str | None):
        """Induced slots of c in a form: other-form fields dropped, required per ci:required_in."""
        out = []
        for s in self.ordered_slots(c):
            f = ann(s, "ci:form")
            if form and f in FORM_PREFIX and f != form:
                continue
            out.append(s)
        return out

    def ranges(self, s, form: str | None) -> list[str]:
        sr = ann(s, "ci:stored_range")
        if sr and form == "stored":
            return [sr]
        return [a.range for a in s.any_of] if s.any_of else [s.range]

    def _direct(self, c: str) -> bool:
        if ann(self.sv.get_class(c), "ci:form") in FORM_PREFIX:
            return False
        return any(ann(s, "ci:form") in FORM_PREFIX or ann(s, "ci:stored_range") or ann(s, "ci:role") == "qualifier"
                   for s in self.sv.class_induced_slots(c))

    def dependent(self, c: str) -> bool:
        """Form-dependent: own form fields, or a range or union member that is (fixpoint over all classes)."""
        if not self._dep:
            sv = self.sv
            dep = {k: self._direct(k) for k in self.order}
            changed = True
            while changed:
                changed = False
                for k in self.order:
                    if dep[k] or ann(sv.get_class(k), "ci:form") in FORM_PREFIX:
                        continue
                    if self.is_union(k):
                        new = any(dep[d] for d in self.concrete_desc(k))
                    else:
                        new = any(dep.get(r, False) for s in sv.class_induced_slots(k)
                                  for r in ([a.range for a in s.any_of] if s.any_of else [s.range])
                                  if r in dep and not self.is_entity(r))
                    if new:
                        dep[k], changed = True, True
            self._dep = dep
        return self._dep[c]

    def name(self, c: str, form: str | None) -> str:
        if self.dependent(c) and form in FORM_PREFIX:
            return FORM_PREFIX[form] + self.py(c)
        return self.py(c)

    # -- reachability -----------------------------------------------------------------------
    def visit(self, c: str, form: str) -> None:
        """Post-order: a class is emitted after the classes it uses (default factories need them)."""
        sv = self.sv
        if self.is_entity(c) or self.is_map_entry(c):
            return
        key = (c, form if self.dependent(c) else None)
        if key in self.emits or key in self._visiting:
            return
        self._visiting.add(key)
        nm = self.name(c, form)
        if self.is_union(c):
            members = self.concrete_desc(c)
            for m in members:
                self.visit(m, form)
            self.emits[key] = Emit(nm, c, key[1], None, alias_of=[self.name(m, form) for m in members], tag=self.tag(c))
            return
        parent = sv.get_class(c).is_a
        pname = None
        if parent and not self.is_union(parent) and not self.is_entity(parent) and parent != "MapEntry":
            self.visit(parent, form)
            pname = self.name(parent, form)
        for s in self.slots(c, form):
            for r in self.ranges(s, form):
                if r in sv.all_classes():
                    self.visit(r, form)
        self.emits[key] = Emit(nm, c, key[1], pname)


class StageBGenerator(PydanticGenerator):
    """A PydanticGenerator subclass emitting the core shapes (see the module docstring)."""

    def __init__(self, schema, **kw) -> None:
        super().__init__(schema, template_dir=str(TEMPLATES), metadata_mode=MetadataMode.NONE, **kw)
        self.plan = Plan(self.schemaview)
        self._ctx: Emit | None = None
        self._form: str | None = None
        self._fields_cache: dict[str, dict] = {}

    # -- class collection -------------------------------------------------------------------
    def _get_classes(self, sv):
        out = []
        for e in self.plan.emits.values():
            out.append(ClassDefinition(name=e.name, is_a=e.parent))
        return out, None

    def _get_class_python_name(self, class_name: str) -> str:
        return class_name

    def before_generate_enums(self, enums, sv):
        return []

    def after_render_template(self, template: str, sv) -> str:
        names = [e.name for e in self.plan.emits.values() if not e.alias_of]
        return template.rstrip() + "\n\n" + "".join(f"{n}.model_rebuild()\n" for n in names)

    def _emit(self, name: str) -> Emit:
        return next(e for e in self.plan.emits.values() if e.name == name)

    # -- classes ----------------------------------------------------------------------------
    def generate_class(self, cls: ClassDefinition):
        from linkml.generators.pydanticgen.build import ClassResult

        e = self._emit(cls.name)
        self._ctx, self._form = e, (e.form or self._any_form(e))
        if e.alias_of:
            union = " | ".join(e.alias_of)
            return ClassResult(cls=CoreClass(name=e.name, is_type_alias=True,
                                             type_alias_value=f'Annotated[{union}, Field(discriminator="{e.tag}")]'),
                               source=self.schemaview.get_class(e.origin))
        sv = self.schemaview
        src = sv.get_class(e.origin)
        attrs: dict[str, CoreAttribute] = {}
        parent_fields = self._fields_of(e.parent) if e.parent else {}
        for s in self.plan.slots(e.origin, self._form):
            if s.identifier and e.origin == "SymbolBinding":
                continue  # the binding map's key
            res = self.generate_slot(s, src)
            a = res.attribute
            if parent_fields.get(a.name) == (a.range, a.field_src):
                continue  # inherited unchanged
            attrs[a.name] = a
        self._fields_cache[e.name] = {k: (v.range, v.field_src) for k, v in {**self._parent_attrs(e), **attrs}.items()}
        config, extra = None, False
        if src.extra_slots and src.extra_slots.allowed:
            config, extra = 'frozen=True, extra="allow"', True
        if any(a.alias for a in attrs.values()):
            config = (config or "frozen=True, extra=\"forbid\"") + \
                ", validate_by_alias=True, validate_by_name=False, serialize_by_alias=True"
        classvars = []
        if any(ann(s, "ci:form") == "consolidated" for s in sv.class_induced_slots(e.origin)) and not e.parent:
            classvars.append("__ci_expression__: ClassVar[bool] = True")
        validators = self._invariants(e, attrs) + self._hooks(e)
        bases = e.parent or "CoreModel"
        pc = CoreClass(name=e.name, bases=bases, attributes=attrs, config=config, extra_decl=extra,
                       classvars=classvars, validators_src=validators)
        return ClassResult(cls=pc, source=src)

    def _parent_attrs(self, e: Emit) -> dict:
        return {k: CoreAttribute(name=k, range=v[0], field_src=v[1]) for k, v in self._fields_of(e.parent).items()} if e.parent else {}

    def _fields_of(self, name: str | None) -> dict:
        return self._fields_cache.get(name, {}) if name else {}

    def _any_form(self, e: Emit) -> str | None:
        return None

    def _invariants(self, e: Emit, attrs) -> list[str]:
        out = []
        names = set(self._fields_cache.get(e.name, {}))
        for inv in scoped(ann(self.schemaview.get_class(e.origin), "ci:invariant"), self._form or ""):
            tpl, args = inv.split("(", 1)
            args = [a.strip() for a in args.rstrip(")").split(",")]
            if tpl == "ordered" and set(args) <= names and set(args) & set(attrs):
                a, b = args
                out.append(f'@model_validator(mode="after")\ndef _ordered_{a}_{b}(self):\n'
                           f'    if self.{a} >= self.{b}:\n'
                           f'        raise ValueError(f"span [{{self.{a}}}, {{self.{b}}}) is empty or reversed")\n'
                           f'    return self')
            elif tpl == "iff_present" and args[0] in names:
                x, cond = args[0], args[1]
                y, v = [p.strip() for p in cond.split("=")]
                out.append(f'@model_validator(mode="after")\ndef _iff_{x}(self):\n'
                           f'    if (self.{y} == "{v}") != (self.{x} is not MISSING):\n'
                           f'        raise ValueError("{x} is present exactly when {y} = {v}")\n'
                           f'    return self')
        return out

    def _hooks(self, e: Emit) -> list[str]:
        hs = scoped(ann(self.schemaview.get_class(e.origin), "ci:validator"), self._form or "")
        return [f'_hook_{h} = model_validator(mode="after")(hooks.{h})' for h in hs]

    # -- slots ------------------------------------------------------------------------------
    def generate_slot(self, slot, cls):
        result = super().generate_slot(slot, cls)  # names, alias handling, metadata
        sv, form = self.schemaview, self._form
        required = bool(slot.required) or bool(slot.equals_string) or bool(slot.equals_string_in) \
            or (form is not None and ann(slot, "ci:required_in") == form)
        rngs = self.plan.ranges(slot, form)
        pyr = self._union([self._range_of(r, slot) for r in rngs], rngs)
        extras = []
        if slot.pattern:
            extras.append(f'pattern=r"{slot.pattern}"')
        alias = None
        if form == "stored" and ann(slot, "ci:role") == "qualifier":
            alias = sv.get_uri(slot.name, expand=False)
        field_src = None
        is_dict = slot.multivalued and slot.inlined and not slot.inlined_as_list and \
            rngs[0] in sv.all_classes() and (sv.get_identifier_slot(rngs[0]) is not None)
        if is_dict:
            pyr = self._dict_range(rngs[0], form)
        elif slot.multivalued:
            pyr = f"tuple[{pyr}, ...]"
            if slot.minimum_cardinality:
                pyr = f"Annotated[{pyr}, Field(min_length={slot.minimum_cardinality})]"
        if slot.equals_string:
            pyr = f'Literal["{slot.equals_string}"]'
        elif slot.equals_string_in:
            pyr = "Literal[" + ", ".join(f'"{x}"' for x in slot.equals_string_in) + "]"
        default = None
        exclude_if = None
        if required:
            default = None
        elif slot.ifabsent:
            v = slot.ifabsent.split("(", 1)[1].rstrip(")")
            default, exclude_if = f'"{v}"', f'lambda v: v == "{v}"'
        elif is_dict:
            default = "default_factory=dict"
        elif slot.multivalued:
            default = "()"
        elif len(rngs) == 1 and rngs[0] in sv.all_classes() and not self.plan.is_union(rngs[0]) \
                and not self.plan.is_entity(rngs[0]) \
                and not any(s.required or s.equals_string or s.equals_string_in
                            for s in sv.class_induced_slots(rngs[0])):  # {} is a valid instance
            default = f"default_factory={self.plan.name(rngs[0], form)}"
        else:
            default = "MISSING"
            pyr = f"{pyr} | MISSING"
        parts = []
        if default is not None:
            parts.append(default)
        if alias:
            parts.append(f'alias="{alias}"')
        if exclude_if:
            parts.append(f"exclude_if={exclude_if}")
        parts += extras
        if parts == ["MISSING"] or parts == ["()"] or (len(parts) == 1 and parts[0].startswith('"')):
            field_src = parts[0]
        elif parts:
            field_src = f"Field({', '.join(parts)})"
        a = result.attribute
        result.attribute = CoreAttribute(**{**a.model_dump(include={"name"}), "range": pyr, "field_src": field_src,
                                            "alias": alias})
        return result

    def _union(self, parts: list[str], rngs: list[str]) -> str:
        if len(parts) == 1:
            return parts[0]
        sv = self.schemaview

        def tagged(r: str) -> bool:
            return r in sv.all_classes() and "t" in {s.name for s in sv.class_induced_slots(r)} \
                and bool(sv.induced_slot("t", r).equals_string)

        if all(tagged(r) for r in rngs):  # every member fixes the tag t: a discriminated union
            return f'Annotated[{" | ".join(parts)}, Field(discriminator="t")]'
        return " | ".join(parts)  # e.g. EntityRef | Formula: told apart by their required keys

    def _dict_range(self, c: str, form: str | None) -> str:
        sv = self.schemaview
        key = sv.get_identifier_slot(c)
        kt = self._range_of(self.plan.ranges(key, form)[0], key)
        if self.plan.is_map_entry(c):
            vs = sv.induced_slot("value", c)
            return f"dict[{kt}, {self._range_of(vs.range, vs)}]"
        return f"dict[{kt}, {self.plan.name(c, form)}]"

    def get_class_slot_range(self, slot_range: str, inlined: bool, inlined_as_list: bool) -> str:
        if self.plan.is_entity(slot_range):
            return "EntityRef"
        return self.plan.name(slot_range, self._form)

    def _range_of(self, r: str | None, slot) -> str:
        sv = self.schemaview
        r = r or sv.schema.default_range or "string"
        if r in sv.all_classes():
            return self.get_class_slot_range(r, True, False)
        if r in sv.all_enums():
            if r in VOCAB_ENUMS:
                return r
            return "Literal[" + ", ".join(f'"{v}"' for v in sv.get_enum(r).permissible_values) + "]"
        if r in sv.all_types():
            t = sv.get_type(r)
            py = ann(t, "ci:py_type")
            if py:
                return py
            for name in [r, *sv.type_ancestors(r)]:
                if name in BUILTIN:
                    return BUILTIN[name]
        raise KeyError(r)


def generate(schema_path: Path) -> str:
    return StageBGenerator(str(schema_path)).serialize()


__all__ = ["StageBGenerator", "Plan", "generate", "field", "Any"]
