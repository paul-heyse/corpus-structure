"""Stage B generation (model and projections §3.3; ADR-0020): the Pydantic shapes of the model.

`render(model)` returns each generated module's source by its path under `corpus_structure`:

- `core/_model/types.py`: the model's constrained types as `Annotated` aliases (ids, keys, names,
  offsets, scores), their patterns as constants, the frozen `CoreModel` base, the reference
  markers (`Refers`, `CITATION`) and the loader of keyed (dict-inlined) collections;
- `core/_model/shapes.py`: the core values, conditions, batch forms and keyed candidate set, the
  observation payloads, the operations JSON and the build diagnostics, with `PAYLOADS`;
- `ingest/_shapes.py`: the source-profile classes (ingest owns them; core never imports ingest).

The hand modules (`core/values.py`, `batch.py`, `payloads.py`, `candidates.py`, `parse_detail.py`,
`ingest/profile.py`) re-export these classes and keep only behaviour. What the generated classes
call or inherit is hand-written in a support module the generated module imports and that never
imports it (`core/shape_support.py`, `ingest/profile_support.py`): `ci:validator` hooks, `ci:mixin`
method classes, and the hand-written `CitationFrame` and `FrameEntry` (probe Q-1).

**A direct emitter over `SchemaView`**, not a `PydanticGenerator` subclass. Probe Q-1
(`p0q.stage-b`) reproduced the shapes with a subclass, but overrode class collection, class and slot
generation and range resolution and computed the form expansion over `SchemaView` itself, keeping
only the template pipeline; its record notes the result is close to an own emitter hosted in the
generator. Hosting it costs a dependency on linkml's generator internals (`ClassResult`, template
classes, `_get_classes`) for no rule the emitter needs, so this module emits the source directly.

**Rules.** Every class is frozen with `extra="forbid"` (`extra_slots: allowed` admits extras as
`JsonValue`); sequences are tuples.

- *Forms.* A core class is form-dependent when an attribute is present or required in one batch
  form only (`ci:form`, `ci:required_in`), has a form-specific range (`ci:stored_range`, or a
  form-scoped `ci:py_type`), is a qualifier (stored under its `core:` alias), or ranges over a
  form-dependent class (a fixpoint). A dependent class reached in both forms is emitted twice,
  `Authored<name>` and `Stored<name>`; any other class once. System classes are emitted once and
  hold the stored form (D3 §6.2: payloads hold stored-form values).
- *Names.* A class's Python name is its `ci:py_name` (else its name), prefixed by its form when it
  is emitted twice. An abstract class whose concrete descendants each fix a tag slot
  (`equals_string`) and that is used as a range is a discriminated union: a PEP 695 alias (one
  `$defs` entry), its members in model order. An `any_of` range is a union of its ranges; a named
  one (`ci:py_name` on the attribute) is an alias, PEP 695 when it is tagged. A discriminator
  slot named by `ci:discriminator` tags members that fix it by their value and the one that does
  not by its lower-cased Python name.
- *Ranges.* An entity class is `EntityRef`; a static closed set its generated `StrEnum`; a
  schema-version-scoped one `str` (packs extend it; S1's compiled models type it); a constrained
  type its alias; another type its base; `ci:py_type` replaces the range (on a class: that class's
  Python shape is the named hand-written one). `ci:refers` makes a string a typed reference
  (non-empty, with its `Refers` marker); `ci:refers: sentence` on a type marks a citation.
- *Collections.* A multivalued slot is a tuple (`minimum_cardinality`, and `maximum_cardinality`
  equal to it, as Pydantic constraints); a `MapEntry` range is a dict from its key to its value; a
  dict-inlined class with an identifier is a tuple of records that also loads the mapping form.
- *Defaults.* Required slots (`required`, `identifier`, a fixed tag, `ci:required_in` the form)
  have none. Otherwise `ci:py_default` (a Python expression; `None` admits `None`), `ifabsent`
  (left out of dumps under `ci:omit_default`), an empty collection, a fresh instance of a class
  with no required slot, else `MISSING`: absent, never null.
- *Validation.* A class with an invariant or a slot pattern calls its Stage A validator
  (`_model/validators.py`); `ci:validator` hooks follow, on the class (after the model) or on a
  slot (`before` or after the field). A slot with a hook keeps its type's pattern for the JSON
  Schema only, as the hook checks it with a corrective message.
- *Docstrings* are the model descriptions; they are the JSON Schemas' descriptions.
"""

from __future__ import annotations

import ast
import builtins
import re
import textwrap
from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

from corpus_structure.schema.model import (
    Model,
    ModelError,
    View,
    ci_annotations,
    invariants_of,
)

PACKAGE = Path(__file__).resolve().parents[1]
GENERATOR = "corpus_structure.schema.stage_b"
TYPES = "core/_model/types.py"
SHAPES = "core/_model/shapes.py"
PROFILE = "ingest/_shapes.py"

FORMS = ("model", "stored")
PREFIX = {"model": "Authored", "stored": "Stored"}
CORE_PREFIX = "core"  # the core module's prefix: a core qualifier's stored alias is core:<name>

# The classes each shape module emits, with what they reach. The core roots are both batch forms
# of the value and condition unions and the batch, the keyed candidate set (stored), the build
# diagnostics, and the payload classes of `system.yaml` (`ci:payload`) other than the hand-kept
# ones below; the profile module emits the source profile.
CORE_ROOTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Value", FORMS), ("Condition", FORMS), ("Batch", FORMS),
    ("KeyedCandidateSet", ("stored",)), ("MentionRef", ("stored",)),
)  # fmt: skip
PROFILE_ROOTS: tuple[tuple[str, tuple[str, ...]], ...] = (("SourceProfile", ("stored",)),)
# Payload classes whose Python form is not generated here: the run options are orchestration's
# settings-free model (`core/options.py`), the trigger metrics and a compiled artifact's body are
# JSON aliases, and the citation frame is the hand-written `CitationFrame` (`ci:py_type`).
HAND_PAYLOADS = frozenset({"RunOptions", "TriggerMetrics", "CompiledArtifactBody", "FrameEntries"})

BUILTIN = {"string": "str", "integer": "int", "boolean": "bool", "float": "float",
           "double": "float", "datetime": "datetime", "date": "date"}  # fmt: skip
# Names a `ci:py_type` or `ci:py_default` expression may use without declaring them.
KNOWN = {
    "Annotated": "typing", "Any": "typing", "Literal": "typing",
    "Field": "pydantic", "JsonValue": "pydantic", "MISSING": "pydantic",
}  # fmt: skip
SUPPORT = {
    SHAPES: "corpus_structure.core.shape_support",
    PROFILE: "corpus_structure.ingest.profile_support",
}


def _q(text: str) -> str:
    """A Python string literal; raw when it holds a backslash (patterns)."""
    if "\\" in text and '"' not in text and not text.endswith("\\"):
        return f'r"{text}"'
    return repr(text)


def docstring(text: str, indent: str) -> str:
    """A docstring of the description, each paragraph (a line of the description) wrapped at 100
    columns, paragraphs separated by a blank line."""
    paragraphs = [" ".join(p.split()) for p in text.strip().split("\n") if p.strip()]
    paragraphs = [p.replace("\\", "\\\\").replace('"""', "'''") for p in paragraphs]
    one = f'{indent}"""{paragraphs[0]}"""'
    if len(paragraphs) == 1 and len(one) <= 100:
        return one
    lines: list[str] = []
    for i, body in enumerate(paragraphs):
        if i:
            lines.append("")
        first = f'{indent}"""' if i == 0 else indent
        wrapped = textwrap.wrap(
            body, width=100, initial_indent=first, subsequent_indent=indent,
            break_on_hyphens=False, break_long_words=False,
        )  # fmt: skip
        lines += wrapped
    if len(lines) == 1:  # ruff would join a one-line body with its closing quotes
        head, _, last = lines[0].rpartition(" ")
        lines = [head, f"{indent}{last}"]
    return "\n".join(lines) + f'\n{indent}"""'


def _scoped(value: str | None, form: str | None) -> str | None:
    """A value that may be scoped to one form (`model: <x>` or `stored: <x>`): the part for this
    form, None when it is scoped to the other."""
    if value is None:
        return None
    m = re.match(r"^(model|stored):\s+(.*)$", value, re.S)
    if m is None:
        return value
    return m.group(2) if m.group(1) == form else None


@dataclass(frozen=True)
class Hook:
    """One `ci:validator` entry: `[model|stored] [before|after] <module>:<function>`."""

    module: str
    function: str
    form: str | None = None
    mode: str = "after"


def parse_hooks(text: str) -> list[Hook]:
    """`ci:validator`'s entries, separated by `;`; refused if malformed."""
    out = []
    for entry in (e.strip() for e in text.split(";") if e.strip()):
        *words, ref = entry.split()
        m = re.fullmatch(r"([a-z_][a-z0-9_.]*):([A-Za-z_][A-Za-z0-9_]*)", ref)
        if m is None or not set(words) <= {"model", "stored", "before", "after"}:
            raise ValueError(f"not a validator hook: {entry!r}")
        form = next((w for w in words if w in FORMS), None)
        mode = next((w for w in words if w in ("before", "after")), "after")
        out.append(Hook(m.group(1), m.group(2), form, mode))
    return out


def parse_reference(text: str) -> tuple[str, str]:
    """`<module>:<name>` (module relative to `corpus_structure`), as used by `ci:mixin`."""
    m = re.fullmatch(r"([a-z_][a-z0-9_.]*):([A-Za-z_][A-Za-z0-9_]*)", text.strip())
    if m is None:
        raise ValueError(f"not a <module>:<name> reference: {text!r}")
    return m.group(1), m.group(2)


def python_expression(text: str) -> ast.Expression:
    """A `ci:py_type` or `ci:py_default` value as a Python expression; refused if it is none."""
    try:
        return ast.parse(_scoped(text, "model") or _scoped(text, "stored") or text, mode="eval")
    except SyntaxError as error:
        raise ValueError(f"not a Python expression: {text!r} ({error.msg})") from None


def _names_in(expr: str) -> set[str]:
    tree = ast.parse(expr, mode="eval")
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}


def module_names(module: str) -> set[str]:
    """The top-level names a hand module defines, read from its source (no import)."""
    path = PACKAGE / Path(*module.split(".")).with_suffix(".py")
    if not path.exists():
        raise ModelError([f"{module}: no module at {path}"])
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.ClassDef):
            out.add(node.name)
        elif isinstance(node, ast.Assign):
            out |= {t.id for t in node.targets if isinstance(t, ast.Name)}
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            out.add(node.target.id)
        elif isinstance(node, ast.TypeAlias) and isinstance(node.name, ast.Name):
            out.add(node.name.id)
    return out


# --- The plan: which classes are emitted, in which forms and modules, under which names --------


@dataclass
class Emission:
    origin: str  # the model class
    form: str  # the form its ranges resolve in
    module: str
    union: list[tuple[str, str]] | None = None  # a union alias: its (member, form) keys


@dataclass
class Plan:
    model: Model
    order: list[tuple[str, str | None]] = field(default_factory=list)
    emits: dict[tuple[str, str | None], Emission] = field(default_factory=dict)

    @cached_property
    def view(self) -> View:
        return self.model.system

    @cached_property
    def core_classes(self) -> list[str]:
        return [str(c) for c in self.model.core.schema.classes]

    @cached_property
    def system_classes(self) -> list[str]:
        return [str(c) for c in self.model.system.schema.classes]

    @cached_property
    def all_classes(self) -> list[str]:
        return [*self.core_classes, *self.system_classes]

    def cls(self, name: str) -> Any:
        return self.view.get_class(name)

    def ann(self, element: Any, tag: str) -> str | None:
        value = ci_annotations(element).get(tag)
        return None if value is None else str(value)

    def ancestors(self, name: str) -> list[str]:
        if self.view.get_class(name) is None:
            return []
        return [str(a) for a in self.view.class_ancestors(name)]

    def is_entity(self, name: str) -> bool:
        return "Entity" in self.ancestors(name)

    def is_map_entry(self, name: str) -> bool:
        return name != "MapEntry" and "MapEntry" in self.ancestors(name)

    def concrete_descendants(self, name: str) -> list[str]:
        return [
            d for d in self.all_classes
            if d != name and name in self.ancestors(d) and not self.cls(d).abstract
        ]  # fmt: skip

    def tag_slot(self, name: str) -> str | None:
        """The slot every concrete descendant of an abstract class fixes."""
        members = self.concrete_descendants(name)
        if not members:
            return None
        for slot in self.view.class_induced_slots(name):
            if all(self.view.induced_slot(slot.name, m).equals_string for m in members):
                return str(slot.name)
        return None

    def is_union(self, name: str) -> bool:
        return bool(
            self.cls(name).abstract and not self.is_entity(name) and name != "MapEntry"
            and self.tag_slot(name) and self.used_as_range(name)
        )  # fmt: skip

    @cached_property
    def _ranges_used(self) -> set[str]:
        out: set[str] = set()
        for c in self.all_classes:
            for s in self.view.class_induced_slots(c):
                out |= set(self.slot_ranges(s, None))
        return out

    def used_as_range(self, name: str) -> bool:
        return name in self._ranges_used

    def slots(self, name: str, form: str | None) -> list[Any]:
        """The class's induced slots in its form, ancestors' first, each class's slots then its
        attributes; an attribute of the other batch form is left out."""
        names: list[str] = []
        for a in reversed(self.ancestors(name)):
            c = self.cls(a)
            for n in [*(c.slots or ()), *(c.attributes or {})]:
                if str(n) not in names:
                    names.append(str(n))
        out = []
        for n in names:
            slot = self.view.induced_slot(n, name)
            present = self.ann(slot, "ci:form")
            if form is not None and present in FORMS and present != form:
                continue
            out.append(slot)
        return out

    def slot_ranges(self, slot: Any, form: str | None) -> list[str]:
        stored = self.ann(slot, "ci:stored_range")
        if stored and form == "stored":
            return [stored]
        if slot.any_of:
            return [str(a.range) for a in slot.any_of]
        return [str(slot.range or self.view.schema.default_range or "string")]

    # -- form dependence -------------------------------------------------------------------------

    def _direct(self, name: str) -> bool:
        for s in self.view.class_induced_slots(name):
            ann = ci_annotations(s)
            py_type = ann.get("ci:py_type")
            scoped = py_type is not None and _scoped(str(py_type), "model") != _scoped(
                str(py_type), "stored"
            )
            if (ann.get("ci:form") in FORMS or ann.get("ci:required_in") or "ci:stored_range" in ann
                    or ann.get("ci:role") == "qualifier" or scoped):  # fmt: skip
                return True
        return False

    @cached_property
    def dependent(self) -> dict[str, bool]:
        """Form dependence of the core classes (module doc), a fixpoint; system classes are not."""
        dep = {c: self._direct(c) for c in self.core_classes}
        changed = True
        while changed:
            changed = False
            for c in self.core_classes:
                if dep[c]:
                    continue
                if self.is_union(c):
                    new = any(dep.get(d, False) for d in self.concrete_descendants(c))
                else:
                    new = any(dep.get(r, False)
                              for s in self.view.class_induced_slots(c)
                              for r in self.slot_ranges(s, None)
                              if not self.is_entity(r) if self.cls(r) is not None)  # fmt: skip
                if new:
                    dep[c] = changed = True
        return dep

    def key(self, name: str, form: str) -> tuple[str, str | None]:
        return (name, form if self.dependent.get(name, False) else None)

    # -- reachability ----------------------------------------------------------------------------

    def build(self) -> Plan:
        for root, forms in CORE_ROOTS:
            for form in forms:
                self.visit(root, form, SHAPES)
        for name in self.system_classes:
            payload = ci_annotations(self.cls(name)).get("ci:payload")
            if payload and name not in HAND_PAYLOADS and name not in self.profile_classes:
                    self.visit(name, "stored", SHAPES)
        for root, forms in PROFILE_ROOTS:
            for form in forms:
                self.visit(root, form, PROFILE)
        return self

    def visit(self, name: str, form: str, module: str) -> None:
        if self.is_entity(name) or self.is_map_entry(name) or self.py_type_of_class(name):
            return
        key = self.key(name, form)
        if key in self.emits:
            if self.emits[key].module != module:
                raise ModelError([f"{name} is reached from {self.emits[key].module} and {module}"])
            return
        emission = Emission(name, form, module)
        self.emits[key] = emission  # before the members: recursive unions end here
        if self.is_union(name):
            members = self.concrete_descendants(name)
            emission.union = [(m, form) for m in members]
            for m in members:
                self.visit(m, form, module)
            self.order.append(key)
            return
        parent = self.cls(name).is_a
        if parent and self.emitted_parent(str(parent)):
            self.visit(str(parent), form, module)
        for slot in self.slots(name, form):
            py_type = self.ann(slot, "ci:py_type")
            if py_type is not None and _scoped(py_type, form) is not None:
                # a Python type replaces the range: reach the model classes it names
                named = _names_in(str(_scoped(py_type, form)))
                for c in self.all_classes:
                    if c in named or (self.ann(self.cls(c), "ci:py_name") or c) in named:
                        self.visit(c, form, module)
                continue
            for rng in self.slot_ranges(slot, form):
                if self.is_entity(rng):  # an entity position takes the one reference shape
                    self.visit("EntityRef", form, module)
                elif self.cls(rng) is not None:
                    self.visit(rng, form, module)
                    if self.is_map_entry(rng):
                        for inner in self.slots(rng, form):
                            for r in self.slot_ranges(inner, form):
                                if self.cls(r) is not None:
                                    self.visit(r, form, module)
        self.order.append(key)

    def emitted_parent(self, parent: str) -> bool:
        return not (self.is_union(parent) or self.is_entity(parent) or parent == "MapEntry"
                    or self.is_map_entry(parent))  # fmt: skip

    def py_type_of_class(self, name: str) -> str | None:
        c = self.cls(name)
        return None if c is None else self.ann(c, "ci:py_type")

    # -- names -----------------------------------------------------------------------------------

    @cached_property
    def both_forms(self) -> set[str]:
        return {n for (n, f) in self.emits if f == "model"} & {
            n for (n, f) in self.emits if f == "stored"
        }

    def py_name(self, name: str) -> str:
        return self.ann(self.cls(name), "ci:py_name") or name

    def name(self, name: str, form: str) -> str:
        """The Python name of a class (or union) as emitted for a form."""
        hand = self.py_type_of_class(name)
        if hand:
            return hand
        key = self.key(name, form)
        if key[1] is not None and name in self.both_forms:
            return PREFIX[form] + self.py_name(name)
        return self.py_name(name)

    def module_of(self, name: str, form: str) -> str:
        return self.emits[self.key(name, form)].module

    @cached_property
    def profile_classes(self) -> set[str]:
        return _profile_classes(self)


def _profile_classes(plan: Plan) -> set[str]:
    """The system classes the source profile reaches (they belong to the profile module)."""
    out: set[str] = set()
    todo = [r for r, _ in PROFILE_ROOTS]
    while todo:
        c = todo.pop()
        if c in out:
            continue
        out.add(c)
        for s in plan.view.class_induced_slots(c):
            for r in plan.slot_ranges(s, "stored"):
                if plan.cls(r) is not None:
                    todo.append(r)
    return out


# --- Emitting a module -----------------------------------------------------------------------


@dataclass
class FieldSource:
    name: str
    type: str
    default: str | None  # the right-hand side, or None when required
    ignore: str | None = None  # the type: ignore code

    def line(self) -> str:
        text = f"    {self.name}: {self.type}"
        if self.default is not None:
            text += f" = {self.default}"
        if self.ignore:
            text += f"  # type: ignore[{self.ignore}]"
        return text


class Emitter:
    """One module's source: its classes and aliases, and the imports they need."""

    def __init__(self, plan: Plan, module: str, types: dict[str, str]) -> None:
        self.plan = plan
        self.view = plan.view
        self.module = module
        self.types = types  # model type -> its alias in types.py
        self.imports: dict[str, set[str]] = {}
        self.body: list[str] = []
        self.helpers: list[str] = []
        self.fields: dict[str, dict[str, tuple[str, str | None]]] = {}  # class -> its fields
        self.defined: set[str] = set()
        self.unions: dict[str, str] = {}  # alias name -> source
        self.support = SUPPORT.get(module)
        support = self.support[len("corpus_structure.") :] if self.support else None
        self.support_names = module_names(support) if support else set()

    def use(self, module: str, *names: str) -> None:
        self.imports.setdefault(module, set()).update(names)

    # -- ranges ----------------------------------------------------------------------------------

    def resolve_names(self, expr: str) -> None:
        """Import what a Python expression names (module doc: `ci:py_type`, `ci:py_default`)."""
        local = {
            self.plan.name(n, f) for (n, f0), e in self.plan.emits.items()
            for f in ((f0,) if f0 else FORMS) if e.module == self.module
        }  # fmt: skip
        vocab = self.vocab_names
        for name in _names_in(expr):
            if name in local or name in self.unions or hasattr(builtins, name):
                continue
            if name in KNOWN:
                self.use(KNOWN[name], name)
            elif name in self.types.values():
                self.use("corpus_structure.core._model.types", name)
            elif name in vocab:
                self.use("corpus_structure.core.vocab", name)
            elif name in self.support_names and self.support:
                self.use(self.support, name)
            elif self.module == PROFILE and name in self.core_shape_names:
                self.use("corpus_structure.core._model.shapes", name)
            else:
                raise ModelError([f"{self.module}: the name {name!r} in {expr!r} is unknown"])

    @cached_property
    def vocab_names(self) -> set[str]:
        return {str(e.name) for _, e in self.plan.model.enums()} | {"StrEnum"}

    @cached_property
    def core_shape_names(self) -> set[str]:
        return {self.plan.name(n, f or "stored") for (n, f), e in self.plan.emits.items()
                if e.module == SHAPES}  # fmt: skip

    def range_type(self, rng: str, form: str) -> str:
        plan = self.plan
        if plan.cls(rng) is not None:
            if plan.is_entity(rng):
                return "EntityRef"
            hand = plan.py_type_of_class(rng)
            if hand:
                self.resolve_names(hand)
                return hand
            name = plan.name(rng, form)
            if plan.module_of(rng, form) != self.module:
                self.use("corpus_structure.core._model.shapes", name)
            return name
        enum = self.view.get_enum(rng)
        if enum is not None:
            if ci_annotations(enum).get("ci:lifecycle") == "schema_version":
                return "str"
            self.use("corpus_structure.core.vocab", rng)
            return rng
        if rng in self.types:
            self.use("corpus_structure.core._model.types", self.types[rng])
            return self.types[rng]
        for name in (rng, *self.view.type_ancestors(rng)):
            if str(name) in BUILTIN:
                return BUILTIN[str(name)]
        raise ModelError([f"{self.module}: no Python type for range {rng!r}"])

    def tagged(self, ranges: list[str]) -> str | None:
        """The tag slot all class ranges fix (a discriminated union), or None."""
        tags = set()
        for r in ranges:
            if self.plan.cls(r) is None or self.plan.is_entity(r):
                return None
            fixed = [str(s.name) for s in self.view.class_induced_slots(r) if s.equals_string]
            if not fixed:
                return None
            tags.add(fixed[0])
        return tags.pop() if len(tags) == 1 else None

    def union(self, slot: Any, ranges: list[str], form: str, owner: str) -> str:
        parts = [self.range_type(r, form) for r in ranges]
        alias = self.plan.ann(slot, "ci:py_name")
        disc = self.plan.ann(slot, "ci:discriminator")
        tag = self.tagged(ranges)
        if disc:
            text = self.callable_union(disc, ranges, parts)
        elif tag:
            text = f'Annotated[{" | ".join(parts)}, Field(discriminator="{tag}")]'
            self.use("typing", "Annotated")
            self.use("pydantic", "Field")
        else:
            text = " | ".join(parts)
        if not alias:
            return text
        # prefixed when a member is emitted in both forms (the alias then differs by form)
        two = any(r in self.plan.both_forms for r in ranges)
        name = (PREFIX[form] if two else "") + alias
        if name not in self.unions:
            pep695 = bool(disc or tag)
            self.unions[name] = f"type {name} = {text}" if pep695 else f"{name} = {text}"
            self.body.append(self.unions[name])
        return name

    def callable_union(self, disc: str, ranges: list[str], parts: list[str]) -> str:
        """A union told apart by one slot: a member that fixes it by its value, the other by its
        lower-cased Python name (module doc)."""
        tags: list[str] = []
        fixed: list[str] = []
        default = None
        for r in ranges:
            value = self.view.induced_slot(disc, r).equals_string
            if value:
                tags.append(str(value))
                fixed.append(str(value))
            else:
                if default is not None:
                    raise ModelError([f"{disc}: two union members do not fix it"])
                default = self.plan.py_name(r).lower()
                tags.append(default)
        fn = "_" + "_or_".join(tags)
        if fn not in self.defined:
            self.defined.add(fn)
            self.use("typing", "Any")
            values = ", ".join(repr(f) for f in fixed)
            self.helpers.append(
                f"def {fn}(raw: Any) -> str:\n"
                f'    """The tag of a union member: its `{disc}` when that is {", ".join(fixed)},'
                f' else {default!r}."""\n'
                f'    value = (\n        raw.get("{disc}") if isinstance(raw, dict)\n'
                f'        else getattr(raw, "{disc}", None)\n    )\n'
                f"    return value if value in ({values},) else {default!r}"
            )  # fmt: skip
        self.use("typing", "Annotated")
        self.use("pydantic", "Discriminator", "Tag")
        members = " | ".join(
            f'Annotated[{p}, Tag("{t}")]' for p, t in zip(parts, tags, strict=True)
        )
        return f"Annotated[{members}, Discriminator({fn})]"

    # -- one field -------------------------------------------------------------------------------

    def constraints(self, slot: Any) -> list[str]:
        """A slot's own pattern and bounds as `Field` arguments."""
        out = []
        if slot.pattern:
            out.append(f"pattern={_q(str(slot.pattern))}")
        if slot.minimum_value is not None:
            out.append(f"ge={slot.minimum_value}")
        if slot.maximum_value is not None:
            out.append(f"le={slot.maximum_value}")
        return out

    def field(self, owner: str, slot: Any, form: str) -> FieldSource:
        """One field of a class in a form: its type, default and alias (module doc)."""
        plan, view = self.plan, self.view
        name = str(slot.name)
        ann = ci_annotations(slot)
        hooks = [h for h in parse_hooks(str(ann.get("ci:validator", ""))) if h.form in (None, form)]
        py_type = _scoped(str(ann["ci:py_type"]), form) if "ci:py_type" in ann else None
        ranges = plan.slot_ranges(slot, form)
        multivalued = bool(slot.multivalued)
        dict_like = False
        keyed: tuple[str, str | None] | None = None
        schema_pattern: str | None = None
        if py_type is not None:
            self.resolve_names(py_type)
            text = py_type
            dict_like = py_type.startswith("dict[")
        else:
            refers = ann.get("ci:refers")
            if refers:
                text = self.reference(str(refers))
            elif len(ranges) > 1:
                text = self.union(slot, ranges, form, owner)
            else:
                is_map = plan.cls(ranges[0]) is not None and plan.is_map_entry(ranges[0])
                text = "" if is_map else self.range_type(ranges[0], form)
                if hooks and ranges[0] in self.types and view.get_type(ranges[0]).pattern:
                    # the hook checks the pattern; the JSON Schema keeps it (module doc)
                    text = BUILTIN["string"]
                    schema_pattern = str(view.get_type(ranges[0]).pattern)
            extra = self.constraints(slot)
            if extra:
                self.use("typing", "Annotated")
                self.use("pydantic", "Field")
                text = f"Annotated[{text}, Field({', '.join(extra)})]"
            if slot.equals_string:
                self.use("typing", "Literal")
                text = f'Literal["{slot.equals_string}"]'
            elif slot.equals_string_in:
                self.use("typing", "Literal")
                text = "Literal[" + ", ".join(f'"{v}"' for v in slot.equals_string_in) + "]"
            rng = ranges[0]
            if multivalued and plan.cls(rng) is not None and plan.is_map_entry(rng):
                key_slot = view.induced_slot("key", rng)
                value_slot = view.induced_slot("value", rng)
                key_t = self.range_type(plan.slot_ranges(key_slot, form)[0], form)
                value_t = self.range_type(plan.slot_ranges(value_slot, form)[0], form)
                text, dict_like = f"dict[{key_t}, {value_t}]", True
            elif multivalued:
                inlined_dict = bool(slot.inlined) and not slot.inlined_as_list
                ident = view.get_identifier_slot(rng) if plan.cls(rng) is not None else None
                if inlined_dict and ident is not None:
                    others = [
                        str(s.name) for s in view.class_induced_slots(rng) if s.name != ident.name
                    ]
                    keyed = (str(ident.name), others[0] if len(others) == 1 else None)
                lo, hi = slot.minimum_cardinality, slot.maximum_cardinality
                if lo is not None and lo == hi:
                    text = f"tuple[{', '.join([text] * int(lo))}]"
                else:
                    text = f"tuple[{text}, ...]"
                    if lo:
                        self.use("typing", "Annotated")
                        self.use("pydantic", "Field")
                        text = f"Annotated[{text}, Field(min_length={lo})]"
        validators = []
        if keyed is not None:
            self.use("pydantic", "BeforeValidator")
            self.use("corpus_structure.core._model.types", "keyed")
            single = f", {keyed[1]!r}" if keyed[1] else ""
            validators.append(f"BeforeValidator(keyed({keyed[0]!r}{single}))")
        for hook in hooks:
            ref = self.hook(hook)
            kind = "BeforeValidator" if hook.mode == "before" else "AfterValidator"
            self.use("pydantic", kind)
            validators.append(f"{kind}({ref})")
        if schema_pattern is not None:
            self.use("pydantic", "Field")
            validators.insert(0, f'Field(json_schema_extra={{"pattern": {_q(schema_pattern)}}})')
        if validators:
            self.use("typing", "Annotated")
            text = f"Annotated[{text}, {', '.join(validators)}]"
        fs = self.with_default(slot, form, text, ranges, dict_like)
        if form == "stored" and ann.get("ci:role") == "qualifier":
            fs = self.aliased(fs, f"{CORE_PREFIX}:{name}")
        return fs

    def aliased(self, fs: FieldSource, alias: str) -> FieldSource:
        """The field under its stored (prefixed) alias."""
        self.use("pydantic", "Field")
        default = fs.default
        if default is None:
            return FieldSource(fs.name, fs.type, f'Field(alias="{alias}")', fs.ignore)
        if default.startswith("Field(") and default.endswith(")"):
            inner = default[len("Field(") : -1]
            return FieldSource(fs.name, fs.type, f'Field({inner}, alias="{alias}")', fs.ignore)
        return FieldSource(fs.name, fs.type, f'Field({default}, alias="{alias}")', fs.ignore)

    def reference(self, refers: str) -> str:
        kinds = refers.split()
        self.use("corpus_structure.core._model.types", "Refers")
        self.use("corpus_structure.core.vocab", "RefKind")
        self.use("typing", "Annotated")
        self.use("pydantic", "Field")
        members = ", ".join(f"RefKind.{k.upper()}" for k in kinds)
        return f"Annotated[str, Field(min_length=1), Refers(frozenset({{{members}}}))]"

    def with_default(
        self, slot: Any, form: str, text: str, ranges: list[str], dict_like: bool
    ) -> FieldSource:
        """The field with its default (module doc: Defaults); `MISSING` admits absence."""
        name, ann = str(slot.name), ci_annotations(slot)
        plan = self.plan
        required = (
            bool(slot.required) or bool(slot.identifier) or bool(slot.equals_string)
            or bool(slot.equals_string_in) or ann.get("ci:required_in") == form
        )  # fmt: skip
        if required:
            return FieldSource(name, text, None)
        py_default = ann.get("ci:py_default")
        if py_default is not None:
            default = str(py_default)
            self.resolve_names(default)
            if default == "None":
                return FieldSource(name, f"{text} | None", "None")
            if default == "MISSING":
                return FieldSource(name, f"{text} | MISSING", "MISSING", "valid-type")
            return FieldSource(name, text, default)
        if slot.ifabsent:
            value = self.ifabsent(str(slot.ifabsent), ranges)
            if ann.get("ci:omit_default"):
                self.use("pydantic", "Field")
                return FieldSource(name, text, f"Field({value}, exclude_if=lambda v: v == {value})")
            return FieldSource(name, text, value)
        if slot.multivalued:
            if dict_like:
                self.use("pydantic", "Field")
                return FieldSource(name, text, "Field(default_factory=dict)")
            return FieldSource(name, text, "()")
        rng = ranges[0]
        if (len(ranges) == 1 and plan.cls(rng) is not None and not plan.is_entity(rng)
                and not plan.is_union(rng) and not plan.py_type_of_class(rng)
                and "ci:py_type" not in ann
                and not any(s.required or s.equals_string or s.identifier
                            for s in plan.slots(rng, form))):  # fmt: skip
            self.use("pydantic", "Field")
            return FieldSource(name, text, f"Field(default_factory={plan.name(rng, form)})")
        self.use("pydantic", "MISSING")
        return FieldSource(name, f"{text} | MISSING", "MISSING", "valid-type")

    def ifabsent(self, text: str, ranges: list[str]) -> str:
        m = re.fullmatch(r"(string|int|integer|float|boolean)\((.*)\)", text)
        if m is None:
            raise ModelError([f"{self.module}: ifabsent {text!r} is not supported"])
        kind, value = m.groups()
        if kind != "string":
            return value
        for r in ranges:
            enum = self.view.get_enum(r)
            if enum is not None and value in (enum.permissible_values or {}):
                from corpus_structure.schema.generate import member_name

                self.use("corpus_structure.core.vocab", r)
                return f"{r}.{member_name(value)}"
        return repr(value)

    def hook(self, hook: Hook) -> str:
        module = f"corpus_structure.{hook.module}"
        if hook.function not in module_names(hook.module):
            raise ModelError([f"ci:validator: {module} defines no {hook.function}"])
        parent, _, leaf = module.rpartition(".")
        self.use(f"from {parent}", leaf)
        return f"{leaf}.{hook.function}"

    # -- one class -------------------------------------------------------------------------------

    def emit(self, key: tuple[str, str | None]) -> None:
        plan = self.plan
        emission = plan.emits[key]
        origin, form = emission.origin, emission.form
        name = plan.name(origin, form)
        if emission.union is not None:
            members = [plan.name(m, f) for m, f in emission.union]
            tag = plan.tag_slot(origin)
            self.use("typing", "Annotated")
            self.use("pydantic", "Field")
            union = " | ".join(members)
            self.body.append(
                f'type {name} = Annotated[{union}, Field(discriminator="{tag}")]'
            )
            self.defined.add(name)
            return
        cls = plan.cls(origin)
        parent = str(cls.is_a) if cls.is_a and plan.emitted_parent(str(cls.is_a)) else None
        parent_name = plan.name(parent, form) if parent else None
        bases = []
        mixin = plan.ann(cls, "ci:mixin")
        if mixin:
            module, mixin_name = parse_reference(mixin)
            if mixin_name not in module_names(module):
                raise ModelError([f"ci:mixin: corpus_structure.{module} defines no {mixin_name}"])
            leaf = module.rpartition(".")[2]
            self.use(f"from corpus_structure.{module.rpartition('.')[0]}", leaf)
            bases.append(f"{leaf}.{mixin_name}")
        if parent_name:
            bases.append(parent_name)
        else:
            self.use("corpus_structure.core._model.types", "CoreModel")
            bases.append("CoreModel")
        lines = [f"class {name}({', '.join(bases)}):"]
        lines.append(docstring(str(cls.description or origin), "    "))
        inherited = self.fields.get(parent_name, {}) if parent_name else {}
        aliased = form == "stored" and any(
            ci_annotations(s).get("ci:role") == "qualifier" for s in plan.slots(origin, form)
        )
        extra = bool(cls.extra_slots and cls.extra_slots.allowed)
        config = []
        if extra or aliased:
            config.append("frozen=True")
            config.append('extra="allow"' if extra else 'extra="forbid"')
        if aliased:
            config += [
                "validate_by_alias=True",
                "validate_by_name=False",
                "serialize_by_alias=True",
            ]
        body: list[str] = []
        if config:
            self.use("pydantic", "ConfigDict")
            body.append(f"    model_config = ConfigDict({', '.join(config)})")
        if extra:
            self.use("pydantic", "JsonValue")
            body.append("    # schema qualifiers, raw JSON until S1 types them (typed extras)")
            body.append(
                "    __pydantic_extra__: dict[str, JsonValue]  # type: ignore[bad-override]"
            )
        consolidated = [str(a) for a, s in (cls.attributes or {}).items()
                        if ci_annotations(s).get("ci:form") == "consolidated"]  # fmt: skip
        if consolidated:
            self.use("typing", "ClassVar")
            items = ", ".join(repr(c) for c in consolidated)
            body.append("    # set by M11 in consolidation; refused in both batch forms")
            body.append(f"    CONSOLIDATED: ClassVar[tuple[str, ...]] = ({items},)")
        own: dict[str, tuple[str, str | None]] = {}
        for slot in plan.slots(origin, form):
            fs = self.field(origin, slot, form)
            if cls.abstract and slot.name == plan.tag_slot(origin):
                tags = [str(plan.view.induced_slot(slot.name, d).equals_string)
                        for d in plan.concrete_descendants(origin)]  # fmt: skip
                self.use("typing", "Literal")
                fs = FieldSource(
                    fs.name, "Literal[" + ", ".join(f'"{t}"' for t in tags) + "]", None
                )
            own[fs.name] = (fs.type, fs.default)
            if inherited.get(fs.name) == (fs.type, fs.default):
                continue
            if fs.name in inherited and fs.ignore is None:
                fs.ignore = "assignment"
            body.append(fs.line())
        self.fields[name] = own
        validator = self.validator_name(origin)
        if validator:
            self.use("pydantic", "model_validator")
            self.use("typing", "Self")
            self.use("corpus_structure.core._model", "validators")
            body += [
                "",
                '    @model_validator(mode="after")',
                "    def _invariants(self) -> Self:",
                f"        validators.{validator}(self)",
                "        return self",
            ]
        hooks = [
            h for h in parse_hooks(plan.ann(cls, "ci:validator") or "") if h.form in (None, form)
        ]
        if hooks:
            self.use("pydantic", "model_validator")
            self.use("typing", "Self")
            body += ["", '    @model_validator(mode="after")', "    def _hooks(self) -> Self:"]
            body += [f"        {self.hook(h)}(self)" for h in hooks]
            body.append("        return self")
        if body:
            lines += ["", *body]
        self.body.append("\n".join(lines))
        self.defined.add(name)

    @cached_property
    def validator_classes(self) -> dict[str, str]:
        """Model class -> its Stage A validator function (`generate._validators`' rule)."""
        from corpus_structure.schema.generate import _snake

        out = {}
        for c in self.plan.all_classes:
            if invariants_of(self.view, c) or any(
                s.pattern for s in self.view.class_induced_slots(c)
            ):
                out[c] = _snake(c)
        return out

    def validator_name(self, origin: str) -> str | None:
        return self.validator_classes.get(origin)


# --- Rendering ---------------------------------------------------------------------------------


HEADER = (
    '"""{doc}\n\nGenerated by `{generator}` from the model (`just model generate`); do not'
    '\nedit.\n"""'
)


def _imports(imports: dict[str, set[str]]) -> list[str]:
    out = ["from __future__ import annotations", ""]
    std = {m: n for m, n in imports.items() if m in ("typing", "collections.abc", "functools")}
    third = {m: n for m, n in imports.items() if m == "pydantic"}
    own = {m: n for m, n in imports.items() if m not in std and m not in third}
    for group in (std, third):
        for module, names in sorted(group.items()):
            out.append(f"from {module} import {', '.join(sorted(names))}")
        if group:
            out.append("")
    for module, names in sorted(own.items()):
        if module.startswith("from "):
            out.append(f"{module} import {', '.join(sorted(names))}")
        else:
            out.append(f"from {module} import {', '.join(sorted(names))}")
    return out


def _types(plan: Plan) -> tuple[str, dict[str, str]]:
    """`core/_model/types.py` and the alias of each constrained model type."""
    view = plan.view
    aliases: dict[str, str] = {}
    lines: list[str] = []
    constants: list[str] = []
    for _, mview in plan.model.modules():
        for tname, typ in (mview.schema.types or {}).items():
            tname = str(tname)
            ann = ci_annotations(typ)
            refers = ann.get("ci:refers")
            if not (typ.pattern or typ.minimum_value is not None or typ.maximum_value is not None
                    or "ci:py_type" in ann or refers):  # fmt: skip
                continue
            aliases[tname] = tname
            if "ci:py_type" in ann:
                text = str(ann["ci:py_type"])
            else:
                base = "str"
                for anc in (str(typ.typeof), *map(str, view.type_ancestors(str(typ.typeof)))):
                    if anc in aliases and anc != tname and not typ.pattern:
                        base = aliases[anc]
                        break
                    if anc in BUILTIN:
                        base = BUILTIN[anc]
                        break
                metadata = []
                if typ.pattern:
                    constant = re.sub(r"(?<!^)(?=[A-Z])", "_", tname).upper()
                    constants.append(f"{constant}: Final = {_q(str(typ.pattern))}")
                    metadata.append(f"pattern={constant}")
                if typ.minimum_value is not None:
                    metadata.append(f"ge={typ.minimum_value}")
                if typ.maximum_value is not None:
                    metadata.append(f"le={typ.maximum_value}")
                parts = [base]
                if metadata:
                    parts.append(f"Field({', '.join(metadata)})")
                if refers == "sentence":
                    parts.append("CITATION")
                text = f"Annotated[{', '.join(parts)}]" if len(parts) > 1 else base
            comment = " ".join(str(typ.description or tname).split())
            lines += textwrap.wrap(comment, 100, initial_indent="# ", subsequent_indent="# ")
            lines.append(f"{tname} = {text}")
    doc = (
        "The model's constrained types, the shapes' base model and reference markers (model and\n"
        "projections §3.3).\n\n"
        "Each type of `model/core.yaml` and `model/system.yaml` with a pattern, a bound or a\n"
        "Python type is an `Annotated` alias (its pattern also a constant); `CoreModel` is every\n"
        "shape's frozen, closed base; `Refers` marks a reference position with the kinds it may\n"
        "name (`values.ref_kinds` reads it) and `CITATION` a citation position\n"
        "(`batch.rewrite_citations` finds them by it); `keyed` loads a dict-inlined collection\n"
        "(LinkML's mapping form, a single-valued body included) as its tuple of records."
    )
    out = [
        HEADER.format(doc=doc, generator=GENERATOR),
        "",
        "from __future__ import annotations",
        "",
        "from collections.abc import Callable, Mapping",
        "from dataclasses import dataclass",
        "from typing import Annotated, Final",
        "",
        "from pydantic import BaseModel, ConfigDict, Field, JsonValue",
        "",
        "from corpus_structure.core.vocab import RefKind",
        "",
        "",
        "class CoreModel(BaseModel):",
        '    """The base of every generated shape: frozen, unknown fields refused."""',
        "",
        '    model_config = ConfigDict(frozen=True, extra="forbid")',
        "",
        "",
        "@dataclass(frozen=True, slots=True)",
        "class Refers:",
        '    """The marker on a reference type\'s annotation: the kinds the position may name."""',
        "",
        "    kinds: frozenset[RefKind]",
        "",
        "",
        "class _Citation:",
        '    """The marker on a citation type\'s annotation: a field of the type cites a',
        '    sentence."""',
        "",
        "    def __repr__(self) -> str:",
        '        return "CITATION"',
        "",
        "",
        "CITATION: Final = _Citation()",
        "",
        "",
        "def keyed(key: str, single: str | None = None) -> Callable[[object], object]:",
        '    """The loader of a dict-inlined collection: `{<key>: {…}}`, or `{<key>: <single>}`',
        '    when the record has one other slot, as the list of records with `key`; a list',
        '    passes."""',
        "",
        "    def load(value: object) -> object:",
        "        if not isinstance(value, Mapping):",
        "            return value",
        "        out = []",
        "        for name, body in value.items():",
        "            if single is not None and not isinstance(body, Mapping):",
        "                body = {single: body}",
        "            if not isinstance(body, Mapping):",
        '                raise ValueError(f"{name!r}: expected a mapping, got {body!r}")',
        "            out.append({key: name, **body})",
        "        return out",
        "",
        "    return load",
        "",
        "",
        "# --- Patterns ---",
        "",
        *constants,
        "",
        "# --- Types ---",
        "",
        *lines,
        "",
        "__all__ = [",
        '    "CITATION", "CoreModel", "JsonValue", "Refers", "keyed",',
        *(f"    {a!r}," for a in aliases.values()),
        *(f"    {c.split(':')[0]!r}," for c in constants),
        "]",
    ]
    return "\n".join(out) + "\n", aliases


def _module(plan: Plan, module: str, aliases: dict[str, str], doc: str) -> str:
    em = Emitter(plan, module, aliases)
    for key in plan.order:
        if plan.emits[key].module == module:
            em.emit(key)
    emitted = [plan.emits[key] for key in plan.order]
    classes = [plan.name(e.origin, e.form) for e in emitted
               if e.module == module and e.union is None]  # fmt: skip
    tail = ["", "", "# Recursive and forward references resolve once every class exists."]
    tail += [f"{c}.model_rebuild()" for c in classes]
    extra: list[str] = []
    if module == SHAPES:
        extra = _payloads(plan, em)
    head = [HEADER.format(doc=doc, generator=GENERATOR), "", *_imports(em.imports)]
    parts = ["\n".join(head)]
    parts += em.helpers
    parts += em.body
    text = "\n\n\n".join(parts) + "\n" + "\n".join(tail) + "\n"
    if extra:
        text += "\n\n" + "\n".join(extra) + "\n"
    return text


def _payloads(plan: Plan, em: Emitter) -> list[str]:
    """`PAYLOADS`: each observation kind's payload class, by `ci:payload` (D3 §6.2)."""
    kinds = {m.text for m in plan.model.expanded("ObservationKind")}
    by_kind: dict[str, str] = {}
    for name in plan.system_classes:
        kind = ci_annotations(plan.cls(name)).get("ci:payload")
        if kind in kinds:
            by_kind[str(kind)] = plan.name(name, "stored")
    from corpus_structure.schema.generate import member_name

    em.use("corpus_structure.core.vocab", "ObservationKind")
    order = [m.text for m in plan.model.expanded("ObservationKind") if m.text in by_kind]
    return [
        "# Each observation kind's payload class (`ci:payload`; D3 §6.2).",
        "PAYLOADS: dict[ObservationKind, type[CoreModel]] = {",
        *(f"    ObservationKind.{member_name(k)}: {by_kind[k]}," for k in order),
        "}",
    ]


def render(model: Model) -> dict[str, str]:
    """Stage B's modules by path under the `corpus_structure` package (unformatted)."""
    plan = Plan(model).build()
    types_text, aliases = _types(plan)
    shapes_doc = (
        "The core shapes (D1 §6, §7; D2 §7.3; D3 §6.2, §6.3; D4 M01; D5 §8.2; model and\n"
        "projections §3.3).\n\n"
        "The values, symbol bindings and condition trees, the batch items and envelopes in both\n"
        "forms, the keyed candidate set, the observation payloads with `PAYLOADS`, the operations\n"
        "JSON and the build diagnostics, generated from `model/core.yaml` and `model/system.yaml`\n"
        "(`schema/stage_b.py` states the rules). Behaviour is hand-written: the hooks and\n"
        "method classes in `core/shape_support.py`, and the functions of the modules that\n"
        "re-export these classes (`values`, `batch`, `payloads`, `candidates`, `parse_detail`)."
    )
    profile_doc = (
        "The source-profile classes (D2 §12.1; D4 M01; ingest and math §3.2).\n\n"
        "Generated from `model/system.yaml`'s `SourceProfile` and the classes it reaches\n"
        "(`schema/stage_b.py` states the rules); their behaviour is hand-written in\n"
        "`ingest/profile_support.py`, and `ingest/profile.py` loads, checks and compiles profiles."
    )
    shapes = _module(plan, SHAPES, aliases, shapes_doc)
    profile = _module(plan, PROFILE, aliases, profile_doc)
    return {TYPES: types_text, SHAPES: shapes, PROFILE: profile}


def iter_classes(model: Model) -> Iterator[tuple[str, str, str]]:
    """(Python name, model class, module) of every generated class, in emission order."""
    plan = Plan(model).build()
    for key in plan.order:
        e = plan.emits[key]
        yield plan.name(e.origin, e.form), e.origin, e.module


