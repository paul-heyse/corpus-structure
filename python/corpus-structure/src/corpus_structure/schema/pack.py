"""Domain packs: loading, the pack declaration check, and the schema version (P0-S-1).

Schema and rules §3.1; D2 §2, §3, §3.4. A pack is `domains/<name>/` (or a test pack in
`fixtures/packs/<name>/`): `schema/<name>.yaml`, `schema/rules.yaml`, `reference/E*/` (each a
`packet.md` and an authored `batch.json`) and `guideline.md`. The pack schema imports the model's
`core` module as `core`; the loader maps that import to the packaged `model/core.yaml`.

**The declaration check** applies M1's vocabulary (`schema.model.VOCABULARY`) to the pack's own
elements, and the pack rules of §3.1:
- the list annotations (`ci:qualifiers`, `ci:identity_qualifiers`) name declared schema
  qualifiers, never a core one, and the identity list is within the allowed list;
- `ci:param_map` names a listed map qualifier; `ci:parameter_class` names an identity slot;
- a slot's `ci:key_role` agrees with every `ci:identity_qualifiers` list that lists it or not;
- `ci:key_role_when` is a member property of the version's `ClaimModality`;
- `ci:case` stands on a class or a string-ranged slot;
- a pack enum may extend a core set (`inherits` / `include`) only when the model declares that set
  `schema_version` (`StatementKind`, `ClaimModality`); a static set refuses pack members, and a
  pack member that collides with a core member is refused (`schema.model.expand_enum`);
- `rules.yaml` has exactly the sections `views`, `rules`, `guideline`, `tables`, `derive`, each
  entry well formed (S2 compiles the expressions).

Every problem is collected into one `PackError`, with its file and element.

**Inference declarations** (Q-8, settled by reasoning): closures over the knowledge graph are
declared natively on predicates (`symmetric`, `transitive`, `inverse`), so a later recursive-SQL
compiler reads them from the lookup and the schema tables; `derive:` holds only template rules a
closure cannot state (a variance to a standard deviation, a construction's parameter mapping), in
the pack's own rule format (`DeriveDecl`). No engine is built here; M23 applies them in phase 2.

**The schema version** is the SHA-256 of the canonical JSON (D1 §10.1) of the parsed pack schemas,
their `rules.yaml`, the core rules, the worked examples and the model revision id. A YAML float
becomes its canonical decimal string; a YAML value that is no JSON scalar (a date) is refused.
Comments and formatting do not count; a description edit does.
"""

from __future__ import annotations

import datetime
import json
import re
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml
from linkml_runtime.utils.schemaview import SchemaView
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from corpus_structure.core.canonical import decimal_of_float, digest
from corpus_structure.schema.model import (
    CORE,
    VOCABULARY,
    EnumExpansionError,
    Member,
    ci_annotations,
    expand_enum,
)

REPOSITORY = Path(__file__).resolve().parents[5]
DOMAINS = REPOSITORY / "domains"
CORE_RULES = DOMAINS / "core" / "schema" / "rules.yaml"
LIST_ANNOTATIONS = frozenset({"ci:qualifiers", "ci:identity_qualifiers", "ci:target"})

# The model's sets a pack may extend: its `schema_version` closed sets (D2 §3.4).
VERSION_SCOPED = ("StatementKind", "ClaimModality")


class PackError(ValueError):
    """A pack that does not load or check; `problems` lists every problem with its element."""

    def __init__(self, problems: Sequence[str]) -> None:
        self.problems = list(problems)
        super().__init__("pack refused:\n  " + "\n  ".join(self.problems))


# --- rules.yaml: the typed file model (structure only; S2 compiles the expressions) --------------


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ViewDecl(_Strict):
    """A rule view: facts from source claims a rule reads (D2 §7.4)."""

    description: str
    applies_to: str | tuple[str, ...]
    source: str
    match: dict[Literal["source", "claim"], Literal["subject", "object"]]
    project: str


class RuleDecl(_Strict):
    """A named check with its severity and call sites."""

    id: str
    applies_to: str | tuple[str, ...]
    severity: Literal["warning", "error"]
    at: tuple[Literal["batch", "finalize"], ...] = Field(min_length=1)
    description: str
    when: str = "true"
    check: str

    @field_validator("check", "when")
    @classmethod
    def _one_line(cls, value: str) -> str:
        return " ".join(value.split())


class GuidelineDecl(_Strict):
    """A guideline check: always a warning, at both call sites."""

    id: str
    applies_to: str | tuple[str, ...]
    description: str
    when: str = "true"
    check: str

    @field_validator("check", "when")
    @classmethod
    def _one_line(cls, value: str) -> str:
        return " ".join(value.split())


class DeriveTemplate(_Strict):
    """The derived claim a derivation produces: references into the matched source claims
    (`source.subject`, `source.object`, …) or literals, and an optional registered helper that
    computes a value (never inline code)."""

    predicate: str
    subject: str
    object: str
    qualifiers: dict[str, str] = {}
    helper: str | None = None


class DeriveDecl(_Strict):
    """A template derivation (D2 §7.4, D4 M23; applied in phase 2). It names its source
    predicates, a rule-language match condition over them, and the claim it derives, which
    inherits the conjunction of its sources' conditions. Closures (symmetric, transitive,
    inverse) are not written here: they are the predicates' native metaslots."""

    id: str
    description: str
    sources: tuple[str, ...] = Field(min_length=1)
    when: str = "true"
    derive: DeriveTemplate

    @field_validator("when")
    @classmethod
    def _one_line(cls, value: str) -> str:
        return " ".join(value.split())


class RulesFile(_Strict):
    """A `rules.yaml`: the pack's (or the core's) views, rules, guideline checks, tables and
    derivations."""

    views: dict[str, ViewDecl] = {}
    rules: tuple[RuleDecl, ...] = ()
    guideline: tuple[GuidelineDecl, ...] = ()
    tables: dict[str, dict[str, Any]] = {}
    derive: tuple[DeriveDecl, ...] = ()


# --- Parsing YAML as JSON ------------------------------------------------------------------------


def _json_scalars(value: Any, where: str, problems: list[str]) -> Any:
    """YAML data as JSON: a float becomes its canonical decimal (D1 §10.1); a value that is no
    JSON scalar (a date, a timestamp) is a problem."""
    if isinstance(value, bool) or value is None or isinstance(value, int | str):
        return value
    if isinstance(value, float):
        return decimal_of_float(value)
    if isinstance(value, dict):
        return {str(k): _json_scalars(v, f"{where}.{k}", problems) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_scalars(v, f"{where}[{i}]", problems) for i, v in enumerate(value)]
    if isinstance(value, datetime.date):
        problems.append(f"{where}: {value!r} is a YAML date, not a JSON scalar; quote it")
        return str(value)
    problems.append(f"{where}: {type(value).__name__} is not a JSON value")
    return None


def _parse_yaml(path: Path, problems: list[str]) -> Any:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        problems.append(f"{path.name}: {error}")
        return None
    return _json_scalars(raw, path.name, problems)


# --- The loaded pack ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Example:
    """A worked example: its packet text and its authored (model-facing) batch."""

    name: str
    packet: str
    batch: dict[str, Any]


@dataclass(frozen=True)
class Pack:
    """One loaded pack: its schema through `SchemaView` (core imported), its parsed files, rules,
    examples and guideline. `sources` keeps each file's text, which registration stores."""

    name: str
    root: Path
    prefix: str
    view: Any  # SchemaView over the pack with the model's core imported
    schema: dict[str, Any]  # the parsed pack schema
    rules_data: dict[str, Any]
    rules: RulesFile
    examples: tuple[Example, ...]
    guideline: str | None
    sources: Mapping[str, str] = field(default_factory=dict)

    @property
    def schema_path(self) -> Path:
        return self.root / "schema" / f"{self.name}.yaml"


def pack_view(schema_path: Path) -> SchemaView:
    """`SchemaView` over a pack, its `core` import resolved to the model's packaged core module."""
    return SchemaView(str(schema_path), importmap={"core": str(CORE.with_suffix(""))})


def load_rules(path: Path, problems: list[str]) -> tuple[dict[str, Any], RulesFile]:
    data = _parse_yaml(path, problems) or {}
    try:
        return data, RulesFile.model_validate(data)
    except ValidationError as error:
        for e in error.errors():
            problems.append(f"{path.name}: {'.'.join(map(str, e['loc']))}: {e['msg']}")
        return data, RulesFile()


def load_pack(root: Path, *, check: bool = True) -> Pack:
    """The pack at `root` (`<root>/schema/<name>.yaml`, its name the directory's), loaded and,
    unless `check` is false, checked; `PackError` lists every problem."""
    name = root.name
    problems: list[str] = []
    schema_path = root / "schema" / f"{name}.yaml"
    rules_path = root / "schema" / "rules.yaml"
    if not schema_path.exists():
        raise PackError([f"{schema_path}: no pack schema"])
    schema = _parse_yaml(schema_path, problems) or {}
    rules_data, rules = (
        load_rules(rules_path, problems) if rules_path.exists() else ({}, RulesFile())
    )
    try:
        view: Any = pack_view(schema_path)
        view.all_elements()  # resolve imports now, so a broken import is this pack's problem
    except Exception as error:
        raise PackError([*problems, f"{schema_path.name}: {error}"]) from None
    examples = []
    sources = {f"schema/{name}.yaml": schema_path.read_text(encoding="utf-8")}
    if rules_path.exists():
        sources["schema/rules.yaml"] = rules_path.read_text(encoding="utf-8")
    reference = root / "reference"
    for d in sorted(p for p in reference.iterdir() if p.is_dir()) if reference.exists() else []:
        packet = (d / "packet.md").read_text(encoding="utf-8")
        batch_text = (d / "batch.json").read_text(encoding="utf-8")
        examples.append(Example(d.name, packet, json.loads(batch_text)))
        sources[f"reference/{d.name}/packet.md"] = packet
        sources[f"reference/{d.name}/batch.json"] = batch_text
    guideline_path = root / "guideline.md"
    guideline = guideline_path.read_text(encoding="utf-8") if guideline_path.exists() else None
    pack = Pack(
        name,
        root,
        str(view.schema.default_prefix),
        view,
        schema,
        rules_data,
        rules,
        tuple(examples),
        guideline,
        sources,
    )
    if check:
        problems += pack_problems(pack)
    if problems:
        raise PackError(problems)
    return pack


# --- The pack declaration check ----------------------------------------------------------------


def _elements(pack: Pack) -> Iterator[tuple[str, str, Any]]:
    """(path, kind, element) for the pack's own annotatable elements."""
    s = pack.view.schema
    file = pack.schema_path.name
    for name, cls in (s.classes or {}).items():
        yield f"{file}: classes.{name}", "class", cls
        for attr, a in (cls.attributes or {}).items():
            yield f"{file}: classes.{name}.{attr}", "attribute", a
    for name, slot in (s.slots or {}).items():
        yield f"{file}: slots.{name}", "slot", slot
    for name, enum in (s.enums or {}).items():
        yield f"{file}: enums.{name}", "enum", enum
        for text, pv in (enum.permissible_values or {}).items():
            yield f"{file}: enums.{name}.{text}", "member", pv
    for name, typ in (s.types or {}).items():
        yield f"{file}: types.{name}", "type", typ


def _admitted(pack: Pack, tag: str, value: Any) -> bool:
    decl = VOCABULARY[tag]
    text = str(value).lower() if isinstance(value, bool) else str(value)
    if decl.enum is not None:
        try:
            return text in {m.text for m in expand_enum(pack.view, decl.enum)}
        except EnumExpansionError:
            return False
    if decl.values is not None:
        return text in decl.values
    if decl.pattern is not None:
        return re.match(decl.pattern, text) is not None
    return bool(text.strip())


def extensions(pack: Pack) -> dict[str, tuple[str, ...]]:
    """Core set -> the pack enums that extend it (by `inherits` or an `include` of it)."""
    out: dict[str, list[str]] = {}
    for name, enum in (pack.view.schema.enums or {}).items():
        bases = [str(b) for b in enum.inherits or ()]
        bases += [str(b) for expr in enum.include or () for b in expr.inherits or ()]
        for base in bases:
            if pack.view.get_enum(base) is not None and base not in pack.view.schema.enums:
                out.setdefault(base, []).append(str(name))
    return {k: tuple(v) for k, v in out.items()}


def version_members(pack: Pack, core_set: str) -> list[Member]:
    """A version-scoped core set's members in this pack's version: the core members, then each
    extending pack enum's own, with their member properties from their defining enum."""
    out = list(expand_enum(pack.view, core_set))
    seen = {m.text for m in out}
    for name in extensions(pack).get(core_set, ()):
        for member in expand_enum(pack.view, name):
            if member.text not in seen:
                seen.add(member.text)
                out.append(member)
    return out


def pack_problems(pack: Pack) -> list[str]:
    """Every declaration problem of a loaded pack (module doc)."""
    problems: list[str] = []
    view = pack.view
    own = pack.view.schema
    for path, kind, element in _elements(pack):
        for tag, value in ci_annotations(element).items():
            decl = VOCABULARY.get(tag)
            if decl is None:
                problems.append(f"{path}: {tag} is not in the declaration vocabulary")
            elif not decl.consumers:
                problems.append(f"{path}: {tag} has no consumer (reserved)")
            elif kind not in decl.on:
                problems.append(f"{path}: {tag} is not declared on a {kind}")
            elif tag not in LIST_ANNOTATIONS and not _admitted(pack, tag, value):
                problems.append(f"{path}: {tag} value {value!r} is not admitted")
    slots = own.slots or {}
    qualifiers = {
        str(n)
        for n, s in view.all_slots().items()
        if ci_annotations(s).get("ci:role") == "qualifier"
    }
    core_qualifiers = {
        q
        for q in qualifiers
        if str(view.get_uri(view.get_slot(q), expand=False)).startswith("core:")
    }
    file = pack.schema_path.name
    listed_identity: dict[str, list[tuple[str, bool]]] = {}
    for name, slot in slots.items():
        ann = ci_annotations(slot)
        where = f"{file}: slots.{name}"
        if ann.get("ci:role") != "predicate":
            continue
        allowed = str(ann.get("ci:qualifiers", "")).split()
        identity = str(ann.get("ci:identity_qualifiers", "")).split()
        for q in allowed + identity:
            if q in core_qualifiers:
                problems.append(
                    f"{where}: {q} is a core qualifier, allowed everywhere, never listed"
                )
            elif q not in qualifiers:
                problems.append(f"{where}: lists {q!r}, which is no declared qualifier")
        for q in identity:
            if q not in allowed:
                problems.append(f"{where}: identity qualifier {q!r} is not in ci:qualifiers")
        for q in allowed:
            listed_identity.setdefault(q, []).append((str(name), q in identity))
        pmap = ann.get("ci:param_map")
        if pmap is not None:
            rng = view.induced_slot(str(pmap)).range if pmap in qualifiers else None
            if pmap not in allowed or rng is None or "MapEntry" not in view.class_ancestors(rng):
                problems.append(f"{where}: ci:param_map {pmap!r} is not a listed map qualifier")
    modality_properties = {p for m in version_members(pack, "ClaimModality") for p in m.properties}
    for name, slot in slots.items():
        ann = ci_annotations(slot)
        where = f"{file}: slots.{name}"
        role = ann.get("ci:key_role")
        if role is not None:
            for predicate, is_identity in listed_identity.get(str(name), ()):
                if is_identity != (role == "identity"):
                    problems.append(
                        f"{where}: ci:key_role {role} contradicts "
                        f"{predicate}'s ci:identity_qualifiers"
                    )
        when = ann.get("ci:key_role_when")
        if when is not None and when not in modality_properties:
            problems.append(
                f"{where}: ci:key_role_when {when!r} is no ClaimModality member property"
            )
        if "ci:case" in ann and (slot.range or "string") != "string":
            problems.append(f"{where}: ci:case stands on a string-ranged slot, not {slot.range}")
    for name, cls in (own.classes or {}).items():
        ann = ci_annotations(cls)
        pc = ann.get("ci:parameter_class")
        if pc is not None:
            keys = [s for uk in (cls.unique_keys or {}).values() for s in uk.unique_key_slots]
            if pc not in keys:
                problems.append(
                    f"{file}: classes.{name}: ci:parameter_class {pc!r} is no identity slot"
                )
    for core_set, enums in extensions(pack).items():
        lifecycle = ci_annotations(view.get_enum(core_set)).get("ci:lifecycle")
        if core_set not in VERSION_SCOPED or lifecycle != "schema_version":
            problems.append(f"{file}: enums {', '.join(enums)} extend {core_set}, a static set")
            continue
        for name in enums:
            try:
                expand_enum(view, name)
            except EnumExpansionError as error:
                problems.append(f"{file}: enums.{name}: {error}")
    for name, enum in (own.enums or {}).items():
        lifecycle = ci_annotations(enum).get("ci:lifecycle", "schema_version")
        if lifecycle != "schema_version":
            problems.append(f"{file}: enums.{name}: a pack enum is schema_version-scoped")
    return problems


# --- The schema version ------------------------------------------------------------------------


def version_inputs(packs: Iterable[Pack], core_rules: Path, model_revision: str) -> dict[str, Any]:
    """What the schema version hashes (module doc)."""
    problems: list[str] = []
    out: dict[str, Any] = {
        "model_revision": model_revision,
        "core_rules": _parse_yaml(core_rules, problems),
        "packs": {},
    }
    for pack in packs:
        out["packs"][pack.name] = {
            "schema": pack.schema,
            "rules": pack.rules_data,
            "reference": {
                e.name: {"packet": e.packet, "batch": _json_scalars(e.batch, e.name, problems)}
                for e in pack.examples
            },
        }
    if problems:
        raise PackError(problems)
    return out


def schema_version(packs: Iterable[Pack], core_rules: Path, model_revision: str) -> str:
    """The schema-version hash: SHA-256 of the canonical JSON of `version_inputs`."""
    return digest(version_inputs(packs, core_rules, model_revision))
