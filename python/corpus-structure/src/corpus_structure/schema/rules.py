"""The rules compiler: `rules:`, `guideline:`, `tables:`, `views:`, `at:` and `applies_to` (P0-S-2).

Schema and rules §3.5; D2 §7.4; D5 §8.2. Every expression of the core rules and of each pack's
`rules.yaml` is compiled with the rule-language helper (`schema.rulelang`) under the claim-view
language of each site the rule declares, so every error of a rules file fails construction, all of
them reported together (`RuleError`).

**The claim view** is the contract the view builder (T4) implements at both sites, with the names
`s4.rules` fixed and D5 §8.2 records. Element names are prefixed (`claim.predicate`,
`subject.type`, `identity` keys, `$enums` and `$is_a`). Qualifier attributes follow the identifier
rule below.

**Per-site type maps.** The batch site has no reading of the math grammar, so `value.parse` and
`value.math_kind` are absent there. An `at: [batch]` rule that reads them fails compilation (D5
§8.2: a rule that needs the grammar declares `at: [finalize]`). A rule at both sites is compiled
from one text under each site's language. Token-derived facts (`subject.index_symbols`,
`value.defined_symbol`) come from `core/tex.py` and exist at both sites; rules read them instead of
running a regular expression over formula text, which the helper refuses.

**Cross-claim facts** (Proposed; the T4 builder and P2's two engines implement one reading):
- `same_slot`: the other claims with the same predicate, subject and statement, where two claims
  with no statement count as having the same statement;
- `alternative_of`: only claims of the input, from the alternative groups the caller supplies;
- a `views:` fact (`claim.<view>`): source claims of the declared predicate matched on the
  declared sides. The caller filters by status (D5's "any status except rejected"), and the caller
  expands `applies_to` with `tables.expand_applies_to`. A projection through a side that names no
  input entity (a statement subject, a value object) contributes nothing;
- every claim the fact applies to has it, empty when nothing matches, never null.

**The qualifier identifier rule** (coordinator decision 25; R04). A schema qualifier's attribute in
`claim.qualifiers` is its local name when that is unique among the version's qualifiers (core and
every pack). Otherwise each colliding qualifier is `<prefix>__<local name>`, and a rule naming the
bare local name fails, naming the colliding qualifiers. The name map already refuses a local name
with two prefixed names. This check is the rule view's own, so adding a pack cannot silently
re-point a rule.

**Rule ids** are unique across the core rules and every pack's sections. A `rules:` id carries its
pack's prefix (`stat.`), and a core rule `core.`. `guideline:` ids keep D2's `guideline.` names.

**Literal vocabularies** (DA-012): predicates, subsets (`claim.groups`), statement kinds and claim
modalities of the version, the generated closed sets (statement roles, establishment, binding
kinds, relations, parse outcomes, math kinds), entity classes, value tags, slot kinds, the
condition node ops of the model, each enum-ranged qualifier's range, identity slots (`identity`
keys), enum names (`$enums` keys), classes (`$is_a` arguments) and each table's own keys.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from rule_engine import Rule

from corpus_structure.core import vocab as core_vocab
from corpus_structure.core._model import qualifiers as core_qualifiers
from corpus_structure.core._model.qualifiers import MISSING
from corpus_structure.core.vocab import (
    BindKind,
    Establishment,
    MathKind,
    ParseOutcome,
    Relation,
    StatementRole,
)
from corpus_structure.schema.lookup import CANONICAL_BY_KIND, CONDITION, Qualifier, SchemaLookup
from corpus_structure.schema.pack import Pack, PackError, RulesFile
from corpus_structure.schema.rulelang import (
    BUILTIN,
    Builtin,
    Language,
    Ref,
    RuleError,
    RuleErrorCode,
    RuleProblem,
    Vocabulary,
)
from corpus_structure.schema.tables import expand_applies_to

SITES = ("batch", "finalize")
CORE_PREFIX = "core"
READINGS = ("parse", "math_kind")  # the value's grammar reading: finalize only (D5 §8.2)
_CORE_SETS = {
    e.__name__: e
    for e in (StatementRole, Establishment, BindKind, Relation, ParseOutcome, MathKind)
}

ENTITY = {
    "id": "string",
    "key": "string?",
    "type": "string",
    "label": "string",
    "symbol": "string?",
    "identity": "map[string]",
    "index_symbols": "list[string]",
}
VALUE = {
    "t": "string",
    "latex": "string?",
    "v": "string?",
    "enum": "string?",
    "slot_kind": "string",
    "defined_symbol": "string?",  # the symbol a formula `x = …` defines (token-derived)
}
STATEMENT = {"id": "string", "key": "string?", "kind": "string"}
BINDING = {
    "symbol": "string",
    "bind": "string",
    "entity": "string?",
    "claim": "string?",
    "param": "string?",
}
NODE = {"op": "string", "ref": "string?", "name": "string?", "rel": "string?", "x_latex": "string?"}
CLAIM = {
    "id": "string",
    "key": "string?",
    "predicate": "string",
    "groups": "list[string]",
    "subject": "Entity",
    "object": "Entity?",
    "value": "Value?",
    "qualifiers": "Qualifiers",
    "statement": "Statement?",
    "statement_kind": "string?",
    "statement_role": "string?",
    "establishment": "string",
    "bindings": "list[Binding]",
    "condition_nodes": "list[Node]",
    "claim_refs": "list[string]",
    "statement_premises": "list[string]",
    "gives_symbols": "list[string]",
    "given_by_others": "list[string]",
    "same_slot": "list[string]",
    "alternative_of": "list[string]",
    "evidence_count": "number",
    "unresolved_symbols": "number",
}
_TYPE_BY_KIND = {
    "map": "map[string]",
    "condition": "list[Node]",
    "number": "number",
    "bool": "boolean",
}


# --- The qualifier identifier rule ------------------------------------------------------------


@dataclass(frozen=True)
class QualifierIdentifiers:
    """Each qualifier's attribute name in `claim.qualifiers`, by prefixed name, and each ambiguous
    local name with the qualifiers it would name."""

    attribute: Mapping[str, str]
    ambiguous: Mapping[str, tuple[str, ...]]


def qualifier_identifiers(qualifiers: Iterable[Qualifier]) -> QualifierIdentifiers:
    by_local: dict[str, list[str]] = {}
    for q in qualifiers:
        by_local.setdefault(q.name, []).append(q.prefixed)
    attribute, ambiguous = {}, {}
    for local, prefixed in sorted(by_local.items()):
        names = sorted(set(prefixed))
        if len(names) == 1:
            attribute[names[0]] = local
        else:
            ambiguous[local] = tuple(names)
            for name in names:
                attribute[name] = name.replace(":", "__", 1)
    return QualifierIdentifiers(attribute, ambiguous)


# --- The claim-view language ------------------------------------------------------------------


def _vocab(name: str, members: Iterable[str]) -> Vocabulary:
    return Vocabulary(name, frozenset(members))


def condition_ops(view: Any) -> frozenset[str]:
    """The `op` of each condition node class of the model."""
    out = set()
    for name in view.all_classes():
        if name != CONDITION and CONDITION in view.class_ancestors(name):
            op = view.induced_slot("op", name).equals_string
            if op:
                out.add(str(op))
    return frozenset(out)


@dataclass(frozen=True)
class _Version:
    """The vocabularies of one schema version, shared by both sites' languages."""

    lookup: SchemaLookup
    ops: frozenset[str]

    def enum_values(self) -> dict[str, Vocabulary]:
        """Each enum by prefixed name with its values as stored: a version-scoped set's members
        with their prefix spelling, a pack enum's as `EnumValue.v`, the core closed sets'."""
        out = {
            s.prefixed: _vocab(s.prefixed, (m.stored for m in s.members))
            for s in self.lookup.version_sets.values()
        }
        for e in self.lookup.enums.values():
            out[e.prefixed] = _vocab(e.prefixed, (m.text for m in e.members))
        for name, members in _CORE_SETS.items():
            out[f"{CORE_PREFIX}:{name}"] = _vocab(f"{CORE_PREFIX}:{name}", members)
        return dict(sorted(out.items()))

    def range_vocabulary(self, rng: str) -> Vocabulary | None:
        lookup = self.lookup
        if rng in lookup.version_sets:
            s = lookup.version_sets[rng]
            return _vocab(s.prefixed, (m.stored for m in s.members))
        if rng in lookup.enums:
            e = lookup.enums[rng]
            return _vocab(e.prefixed, (m.text for m in e.members))
        closed = getattr(core_vocab, rng, None)
        return _vocab(f"{CORE_PREFIX}:{rng}", closed) if closed is not None else None

    def values(self) -> dict[Ref, Vocabulary]:
        lookup = self.lookup
        kinds = self.range_vocabulary("StatementKind")
        assert kinds is not None
        return {
            ("Claim", "predicate"): _vocab(
                "predicates", (p.prefixed for p in lookup.predicates.values())
            ),
            ("Claim", "groups"): _vocab("predicate subsets", lookup.subsets),
            ("Claim", "statement_kind"): kinds,
            ("Statement", "kind"): kinds,
            ("Claim", "statement_role"): _vocab("core:StatementRole", StatementRole),
            ("Claim", "establishment"): _vocab("core:Establishment", Establishment),
            ("Entity", "type"): _vocab(
                "entity classes", (e.prefixed for e in lookup.entity_classes.values())
            ),
            ("Value", "t"): _vocab("value tags", lookup.value_classes.values()),
            ("Value", "enum"): _vocab("enums", self.enum_values()),
            ("Value", "slot_kind"): _vocab("object kinds", CANONICAL_BY_KIND),
            ("Value", "parse"): _vocab("core:ParseOutcome", ParseOutcome),
            ("Value", "math_kind"): _vocab("core:MathKind", MathKind),
            ("Binding", "bind"): _vocab("core:BindKind", BindKind),
            ("Node", "op"): _vocab("condition ops", self.ops),
            ("Node", "rel"): _vocab("core:Relation", Relation),
        }

    def identity_slots(self) -> Vocabulary:
        slots = {s for e in self.lookup.entity_classes.values() for s in e.identity_keys}
        return _vocab("identity slots", slots)

    def classes(self) -> Vocabulary:
        return _vocab("classes", self.lookup.class_names.values())

    def is_a(self) -> Any:
        lookup = self.lookup
        local = {v: k for k, v in lookup.class_names.items()}
        ancestors = {
            prefixed: frozenset(lookup.class_names[a] for a in lookup.ancestors.get(name, ()))
            for name, prefixed in lookup.class_names.items()
        }
        return lambda cls, of: cls in local and of in ancestors.get(cls, frozenset())


def _qualifier_type(q: Qualifier, defaults: Mapping[str, Any]) -> str:
    base = _TYPE_BY_KIND.get(q.object_kind, "string")
    has_default = defaults.get(q.prefixed, MISSING) is not MISSING
    return base if has_default else f"{base}?"


@dataclass(frozen=True)
class ClaimLanguages:
    """The claim-view language of each site, and what shaped it (the artifact body's half)."""

    languages: Mapping[str, Language]
    identifiers: QualifierIdentifiers
    tables: Mapping[str, Mapping[str, Any]]
    views: Mapping[str, Mapping[str, Any]]

    def body(self) -> dict[str, Any]:
        def vocab(table: Mapping[Ref, Vocabulary]) -> dict[str, Any]:
            return {f"{o}.{a}": sorted(v.members) for (o, a), v in sorted(table.items())}

        sites = {}
        for site, lang in self.languages.items():
            sites[site] = {
                "objects": {k: dict(v) for k, v in lang.objects.items()},
                "symbols": dict(lang.symbols),
                "builtins": {k: b.type for k, b in sorted(lang.builtins.items())},
                "values": vocab(lang.values),
                "keys": vocab(lang.keys),
                "arguments": {
                    k: [sorted(v.members) if v else None for v in args]
                    for k, args in sorted(lang.arguments.items())
                },
                "absent": {f"{o}.{a}": c for (o, a), (c, _) in sorted(lang.absent.items())},
                "no_regex": sorted(f"{o}.{a}" for o, a in lang.no_regex),
            }
        return {
            "sites": sites,
            "qualifier_identifiers": dict(sorted(self.identifiers.attribute.items())),
            "ambiguous_qualifiers": {k: list(v) for k, v in self.identifiers.ambiguous.items()},
            "tables": {k: dict(v) for k, v in self.tables.items()},
            "views": {k: dict(v) for k, v in self.views.items()},
        }


def claim_languages(
    packs: Sequence[Pack],
    lookup: SchemaLookup,
    problems: list[RuleProblem],
    qualifiers: Iterable[Qualifier] | None = None,
) -> ClaimLanguages:
    """The languages of both sites over the version's qualifiers, tables and views; table and
    view errors are appended to `problems`. `qualifiers` defaults to the lookup's."""
    quals = list(lookup.qualifiers.values() if qualifiers is None else qualifiers)
    identifiers = qualifier_identifiers(quals)
    version = _Version(lookup, condition_ops(packs[0].view))
    defaults = {q.name: q.default for q in core_qualifiers.CORE_QUALIFIERS}

    qualifier_attrs: dict[str, str] = {}
    values = version.values()
    no_regex: set[Ref] = {("Value", "latex"), ("Node", "x_latex"), ("Binding", "symbol")}
    for q in sorted(quals, key=lambda q: q.prefixed):
        attr = identifiers.attribute[q.prefixed]
        qualifier_attrs[attr] = _qualifier_type(q, defaults)
        if q.object_kind == "enum" and (v := version.range_vocabulary(q.range)) is not None:
            values[("Qualifiers", attr)] = v
        if q.object_kind == "formula":
            no_regex.add(("Qualifiers", attr))

    enum_values = version.enum_values()
    builtins = {
        "enums": Builtin(
            {k: tuple(sorted(v.members)) for k, v in enum_values.items()}, "map[list[string]]"
        ),
        "is_a": Builtin(version.is_a(), "function(string, string)->boolean"),
    }
    keys: dict[Ref, Vocabulary] = {
        ("Entity", "identity"): version.identity_slots(),
        (BUILTIN, "enums"): _vocab("enums", enum_values),
    }
    reserved = set(builtins) | {"all", "any", "abs", "filter", "map", "max", "min", "sum"}
    reserved |= {"range", "split", "e", "pi", "parse_datetime", "parse_float", "parse_timedelta"}
    tables: dict[str, Mapping[str, Any]] = {}
    for pack in packs:
        for name, table in pack.rules.tables.items():
            where = f"{pack.prefix}: tables.{name}"
            if name in reserved or name in tables:
                problems.append(RuleProblem(where, RuleErrorCode.BAD_TABLE, "name is taken"))
                continue
            entries = list(table.values())
            if entries and all(
                isinstance(v, list) and all(isinstance(x, str) for x in v) for v in entries
            ):
                builtins[name] = Builtin(
                    {k: tuple(v) for k, v in table.items()}, "map[list[string]]"
                )
            elif all(isinstance(v, str) for v in entries):
                builtins[name] = Builtin(dict(table), "map[string]")
            else:
                problems.append(
                    RuleProblem(
                        where,
                        RuleErrorCode.BAD_TABLE,
                        "a table maps strings to strings or to lists of strings",
                    )
                )
                continue
            tables[name] = table
            keys[(BUILTIN, name)] = _vocab(f"keys of ${name}", table)

    claim = dict(CLAIM)
    views: dict[str, Mapping[str, Any]] = {}
    identity = version.identity_slots().members
    for pack in packs:
        for name, decl in pack.rules.views.items():
            where = f"{pack.prefix}: views.{name}"
            found = _view_problems(lookup, decl, identity)
            if name in claim:
                found.append(f"the claim view already has an attribute {name!r}")
            problems += [RuleProblem(where, RuleErrorCode.BAD_VIEW, f) for f in found]
            if not found:
                claim[name] = "list[string]"
                views[name] = decl.model_dump(mode="json")

    languages = {}
    for site in SITES:
        value = dict(VALUE)
        absent: dict[Ref, tuple[RuleErrorCode, str]] = {}
        for local, names in identifiers.ambiguous.items():
            alternatives = " or ".join(identifiers.attribute[n] for n in names)
            absent[("Qualifiers", local)] = (
                RuleErrorCode.AMBIGUOUS_QUALIFIER,
                f"qualifier {local!r} is ambiguous: it names {' and '.join(names)}; "
                f"write {alternatives}",
            )
        if site == "finalize":
            value.update({r: "string?" for r in READINGS})
        else:
            for r in READINGS:
                absent[("Value", r)] = (
                    RuleErrorCode.READING_AT_BATCH,
                    f"value.{r} is the math grammar's reading, which exists at finalize only; "
                    "a rule reading it declares at: [finalize]",
                )
        languages[site] = Language(
            objects={
                "Claim": claim,
                "Entity": ENTITY,
                "Value": value,
                "Statement": STATEMENT,
                "Binding": BINDING,
                "Node": NODE,
                "Qualifiers": qualifier_attrs,
            },
            symbols={"claim": "Claim"},
            builtins=builtins,
            values=values,
            keys=keys,
            arguments={"is_a": (version.classes(), version.classes())},
            absent=absent,
            no_regex=frozenset(no_regex),
        )
    return ClaimLanguages(languages, identifiers, tables, views)


_PROJECTED = {"id", "key", "type", "label", "symbol"}


def _view_problems(lookup: SchemaLookup, decl: Any, identity: frozenset[str]) -> list[str]:
    found = []
    predicates = {p.prefixed for p in lookup.predicates.values()}
    if decl.source not in predicates:
        found.append(f"source names unknown predicate {decl.source!r}")
    try:
        expand_applies_to(lookup, decl.applies_to)
    except PackError as error:
        found += error.problems
    head, _, rest = decl.project.partition(".")
    attr, _, slot = rest.partition(".")
    ok = head in ("subject", "object") and (
        (attr in _PROJECTED and not slot) or (attr == "identity" and slot in identity)
    )
    if not ok:
        found.append(
            f"project {decl.project!r} is not <subject|object>.<id|key|type|label|symbol> or "
            "<subject|object>.identity.<identity slot>"
        )
    return found


# --- Compiling the rules ----------------------------------------------------------------------


@dataclass(frozen=True)
class CompiledRule:
    id: str
    group: str  # rules | guideline
    pack: str  # the pack's prefix, or core
    severity: str
    at: tuple[str, ...]
    applies_to: frozenset[str]  # prefixed predicates
    description: str
    when_text: str
    check_text: str
    when: Mapping[str, Rule]  # site -> compiled expression
    check: Mapping[str, Rule]

    def body(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "group": self.group,
            "pack": self.pack,
            "severity": self.severity,
            "at": list(self.at),
            "applies_to": sorted(self.applies_to),
            "description": self.description,
            "when": self.when_text,
            "check": self.check_text,
        }


@dataclass(frozen=True)
class CompiledRules:
    """The version's compiled rules, indexed by site and predicate for the runner."""

    rules: tuple[CompiledRule, ...]
    claim: ClaimLanguages

    def index(self, site: str) -> dict[str, tuple[CompiledRule, ...]]:
        out: dict[str, list[CompiledRule]] = {}
        for rule in self.rules:
            if site in rule.at:
                for predicate in sorted(rule.applies_to):
                    out.setdefault(predicate, []).append(rule)
        return {p: tuple(r) for p, r in out.items()}

    def body(self) -> dict[str, Any]:
        return {"rules": [r.body() for r in self.rules], **self.claim.body()}


def compile_rules(
    packs: Sequence[Pack],
    lookup: SchemaLookup,
    core_rules: RulesFile,
    qualifiers: Iterable[Qualifier] | None = None,
) -> CompiledRules:
    """Compile the core rules and every pack's `rules:` and `guideline:`; every problem of every
    file is reported in one `RuleError` (module doc)."""
    problems: list[RuleProblem] = []
    claim = claim_languages(packs, lookup, problems, qualifiers)
    sources: list[tuple[str, str, Any]] = [(CORE_PREFIX, "rules", r) for r in core_rules.rules]
    for pack in packs:
        sources += [(pack.prefix, "rules", r) for r in pack.rules.rules]
        sources += [(pack.prefix, "guideline", r) for r in pack.rules.guideline]
    seen: set[str] = set()
    compiled = []
    for prefix, group, decl in sources:
        if decl.id in seen:
            problems.append(RuleProblem(decl.id, RuleErrorCode.DUPLICATE_RULE_ID, "id is taken"))
        seen.add(decl.id)
        if group == "rules" and not decl.id.startswith(f"{prefix}."):
            problems.append(
                RuleProblem(decl.id, RuleErrorCode.RULE_ID_PREFIX, f"id must start {prefix}.")
            )
        try:
            applies = frozenset(expand_applies_to(lookup, decl.applies_to))
        except PackError as error:
            problems += [
                RuleProblem(decl.id, RuleErrorCode.UNKNOWN_APPLIES_TO, p) for p in error.problems
            ]
            applies = frozenset()
        at = tuple(decl.at) if group == "rules" else SITES
        when: dict[str, Rule] = {}
        check: dict[str, Rule] = {}
        for site in at:
            language = claim.languages[site]
            for text, out in ((decl.when, when), (decl.check, check)):
                try:
                    out[site] = language.compile(decl.id, text)
                except RuleError as error:
                    problems += [
                        RuleProblem(p.rule, p.code, f"at {site}: {p.message}")
                        for p in error.problems
                    ]
        compiled.append(
            CompiledRule(
                id=decl.id,
                group=group,
                pack=prefix,
                severity=getattr(decl, "severity", "warning"),
                at=at,
                applies_to=applies,
                description=decl.description,
                when_text=decl.when,
                check_text=decl.check,
                when=when,
                check=check,
            )
        )
    if problems:
        raise RuleError(_unique(problems))
    return CompiledRules(tuple(compiled), claim)


def _unique(problems: Iterable[RuleProblem]) -> list[RuleProblem]:
    out: dict[tuple[str, str, str], RuleProblem] = {}
    for p in problems:
        out.setdefault((p.rule, p.code, p.message), p)
    return list(out.values())
