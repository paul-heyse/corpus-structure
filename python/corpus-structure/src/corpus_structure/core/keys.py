"""Canonical forms, label normalization and the entity, statement, claim and group keys.

D1 §6.2, §7, §10.1; D5 §3.3, §5.2, §5.3; foundations §3.6.

Every function here is pure. Schema facts (`KeySchema`) and label rules (`LabelRules`) arrive as
data from S1 and the pack, and the rendition (`KeyContext`) from the caller; nothing reads the
database or a pack file. Which claims are alternatives, and on what they disagree, is C1's
decision, passed to `key_claims` as `members`.

Canonical forms work on the JSON form of stored values (`model_dump(mode="json")`), so authored and
stored inputs give the same parts wherever text enters by its text form alone.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Self

import regex
from pydantic import Field, model_validator

from corpus_structure.core.candidates import (
    CandidateClaim,
    CandidateEntity,
    CandidateStatement,
    KeyedCandidateSet,
)
from corpus_structure.core.canonical import canonical_json, make_key
from corpus_structure.core.evidence import (
    MacroDef,
    RenditionContent,
    Segment,
    SegmentKind,
    content_digest,
    rendition_key,
    segment_key,
)
from corpus_structure.core.locators import LocatorIndex
from corpus_structure.core.tex import token_form
from corpus_structure.core.values import CoreModel
from corpus_structure.core.vocab import EntityScope

Json = Any
Resolve = Callable[[str], str]  # a reference (entity, statement or claim id) to its key


# --- Text and label forms ----------------------------------------------------------------------


def collapse(text: str) -> str:
    """NFC with whitespace runs collapsed to one space and the ends trimmed."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def text_form(text: str) -> str:
    """The D1 §6.2 text form: NFC, casefolded, whitespace collapsed."""
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


class Rewrite(CoreModel):
    """One pack rewrite (`match`/`replace`, applied with `regex.sub`) of the `aliases:` section."""

    match: str
    replace: str


class LabelRules(CoreModel):
    """Label-normalization data from the pack's `aliases:` section; core holds no word list."""

    articles: tuple[str, ...] = ()
    head_words: dict[str, tuple[str, ...]] = Field(default_factory=dict)  # class -> words
    rewrites: tuple[Rewrite, ...] = ()


def normalize_label(text: str, type_: str, rules: LabelRules) -> str:
    """Text form; one leading article removed; the rewrites in order; the class's head words
    removed as trailing whole words; whitespace collapsed again. Never empties a label."""
    label = text_form(text)
    words = label.split(" ")
    articles = {text_form(a) for a in rules.articles}
    if len(words) > 1 and words[0] in articles:
        label = " ".join(words[1:])
    for rewrite in rules.rewrites:
        label = regex.sub(rewrite.match, rewrite.replace, label)
    label = text_form(label)
    heads = {text_form(w) for w in rules.head_words.get(type_, ())}
    words = label.split(" ") if label else []
    while len(words) > 1 and words[-1] in heads:
        words.pop()
    return text_form(" ".join(words))


def symbol_form(symbol: str, macros: Mapping[str, MacroDef]) -> str:
    """A symbol as keys and symbol maps write it: token form, a lone control word unescaped."""
    form = token_form(symbol, macros)
    if regex.fullmatch(r"\\[A-Za-z]+", form):
        return form[1:]
    return form


# --- Canonical values and conditions -----------------------------------------------------------


def canonical_value(value: Json, macros: Mapping[str, MacroDef], resolve: Resolve) -> Json:
    """The key form of a value or entity reference (JSON), per D1 §6.2."""
    if "t" not in value:
        return {"key": resolve(value["ref"])}  # an entity reference
    t = value["t"]
    if t == "text":
        return {"t": t, "v": text_form(value["v"])}
    if t == "number":
        out = {"t": t, "v": value["v"]}
        for name in ("unit", "basis"):
            if name in value:
                out[name] = collapse(value[name])
        return out
    if t in ("formula", "set"):
        return {"t": t, "latex": token_form(value["latex"], macros)}
    if t == "interval":
        out = {"t": t}
        for name in ("start", "end"):
            if name in value:
                out[name] = canonical_value(value[name], macros, resolve)
        for name in ("start_incl", "end_incl"):
            if name in value:
                out[name] = value[name]
        return out
    if t == "phrase":
        return {"t": t, "text": text_form(value["text"])}
    return dict(value)  # bool, enum, date: as written


def _sort(items: Iterable[Json]) -> list[Json]:
    return sorted(items, key=canonical_json)


def canonical_condition(
    node: Json,
    macros: Mapping[str, MacroDef],
    resolve: Resolve,
    symmetric: frozenset[str] = frozenset(),
) -> Json | None:
    """The D1 §7 canonical form of a condition tree, bottom-up; `None` is no condition."""

    def walk(n: Json) -> Json | None:
        op = n["op"]
        if op in ("and", "or"):
            args: list[Json] = []
            for child in n["args"]:
                c = walk(child)
                if c is None:
                    continue
                args.extend(c["args"] if c["op"] == op else [c])
            unique = list({canonical_json(a): a for a in args}.values())  # identical args once
            if not unique:
                return None
            if len(unique) == 1:
                return unique[0]
            return {"op": op, "args": _sort(unique)}
        if op == "not":
            inner = walk(n["arg"])
            return None if inner is None else {"op": op, "arg": inner}
        if op == "claim":
            return {"op": op, "ref": resolve(n["ref"])}
        if op == "member":
            x = canonical_value(n["x"], macros, resolve)
            return {"op": op, "x": x, "set": canonical_value(n["set"], macros, resolve)}
        if op == "cmp":
            rel, lhs, rhs = n["rel"], n["lhs"], n["rhs"]
            if rel in (">", ">="):
                rel, lhs, rhs = {">": "<", ">=": "<="}[rel], rhs, lhs
            sides = [canonical_value(lhs, macros, resolve), canonical_value(rhs, macros, resolve)]
            if rel in ("=", "!="):  # symmetric relations: operands in canonical order
                sides = _sort(sides)
            return {"op": op, "rel": rel, "lhs": sides[0], "rhs": sides[1]}
        if op == "pred":
            pred_args = [canonical_value(a, macros, resolve) for a in n["args"]]
            if n["name"] in symmetric:
                pred_args = _sort(pred_args)
            return {"op": op, "name": n["name"], "args": pred_args}
        if op == "forall":
            body = walk(n["body"])
            if body is None:
                return None
            return {
                "op": op,
                "var": symbol_form(n["var"], macros),
                "set": canonical_value(n["set"], macros, resolve),
                "body": body,
            }
        if op in ("phrase", "unsupported"):
            return {"op": op, "text": text_form(n["text"])}
        raise ValueError(f"unknown condition node {op!r}")

    return walk(node)


def claim_refs(node: Json) -> list[str]:
    """The claim refs a condition tree references, in tree order."""
    out: list[str] = []

    def walk(n: Json) -> None:
        op = n["op"]
        if op == "claim":
            out.append(n["ref"])
        for child in n.get("args", ()) if op in ("and", "or") else ():
            walk(child)
        if op == "not":
            walk(n["arg"])
        if op == "forall":
            walk(n["body"])

    walk(node)
    return out


def canonical_binding(
    symbol: str, binding: Json, macros: Mapping[str, MacroDef], resolve: Resolve
) -> Json:
    """The key form of one symbol binding (used only in alternative member keys)."""
    out: Json = {"symbol": symbol_form(symbol, macros), "bind": binding["bind"]}
    for name in ("entity", "claim"):
        if name in binding:
            out[name] = resolve(binding[name])
    if "param" in binding:
        out["param"] = binding["param"]
    return out


def _bindings(node: Json, macros: Mapping[str, MacroDef], resolve: Resolve) -> list[Json]:
    """Every formula's or set's canonical bindings beside its canonical value, sorted by canonical
    JSON, so neither argument order nor a rewritten comparison moves them."""
    out: list[Json] = []

    def walk(n: Any) -> None:
        if isinstance(n, dict):
            if n.get("t") in ("formula", "set"):
                symbols = n.get("symbols", {})
                bound = [canonical_binding(s, b, macros, resolve) for s, b in symbols.items()]
                out.append({
                    "value": canonical_value(n, macros, resolve),
                    "symbols": _sort(bound),
                })  # fmt: skip
            for key in sorted(n):
                walk(n[key])
        elif isinstance(n, list):
            for item in n:
                walk(item)

    walk(node)
    return _sort(out)


# --- Schema facts and the rendition ------------------------------------------------------------


class KeyingError(LookupError):
    """A candidate that cannot be keyed: the reason is counted, never raised past `key_claims`."""


class KeySchema(CoreModel):
    """The schema facts keys need (from S1's compiled lookup).

    `predicate_names` maps every predicate the schema knows from its bare name to its prefixed
    name; keys and every lookup use the prefixed spelling, so `has_distribution` and
    `stat:has_distribution` are one predicate and an unknown one is refused."""

    identity_keys: dict[str, tuple[str, ...]] = Field(default_factory=dict)  # class -> slots
    entity_identity: dict[str, tuple[str, ...]] = Field(default_factory=dict)  # entity-valued
    predicate_names: dict[str, str] = Field(default_factory=dict)  # bare -> prefixed
    identity_qualifiers: dict[str, tuple[str, ...]] = Field(default_factory=dict)  # by prefixed
    symmetric_predicates: frozenset[str] = frozenset()  # condition predicates

    @model_validator(mode="after")
    def _qualifiers_by_prefixed_name(self) -> Self:
        for name in self.identity_qualifiers:
            if name not in self.predicate_names.values():
                raise ValueError(f"identity_qualifiers names {name!r}, not a prefixed predicate")
        return self

    def predicate(self, name: str) -> str:
        """The prefixed spelling of a bare or prefixed predicate name; refuses an unknown one."""
        if name in self.predicate_names:
            return self.predicate_names[name]
        if name in self.predicate_names.values():
            return name
        raise KeyingError(f"predicate {name!r} is not in the schema")


@dataclass
class KeyContext:
    """One rendition: the document key, its content and page, and the effective macro table."""

    document_key: str
    content: RenditionContent
    page: str
    macros: Mapping[str, MacroDef] = field(default_factory=dict)

    @cached_property
    def index(self) -> LocatorIndex:
        return LocatorIndex(self.content, self.page)

    @cached_property
    def segments(self) -> dict[str, Segment]:
        """Segment key -> segment on this rendition."""
        ren = rendition_key(self.document_key, content_digest(self.content))
        return {segment_key(ren, s.kind, s.start, s.end): s for s in self.content.document.walk()}

    @cached_property
    def parents(self) -> dict[tuple[str, int, int], Segment]:
        out: dict[tuple[str, int, int], Segment] = {}
        for segment in self.content.document.walk():
            for child in segment.children:
                out[(child.kind.value, child.start, child.end)] = segment
        return out

    def segment(self, key: str) -> Segment:
        try:
            return self.segments[key]
        except KeyError:
            raise KeyingError(f"segment key {key} is not on this rendition") from None

    def ancestors(self, segment: Segment) -> list[Segment]:
        """The segment's ancestors, innermost first."""
        out = []
        current = self.parents.get((segment.kind.value, segment.start, segment.end))
        while current is not None:
            out.append(current)
            current = self.parents.get((current.kind.value, current.start, current.end))
        return out

    def locator_key(self, segment: Segment) -> Json:
        return self.index.generate(segment).key_form(self.document_key)


# --- Entity and statement keys -----------------------------------------------------------------


def global_entity_key(
    entity: CandidateEntity, schema: KeySchema, rules: LabelRules, resolve: Resolve
) -> str:
    """`ent`: type and identity attributes; the normalized label when identity is incomplete."""
    declared = schema.identity_keys.get(entity.type, ())
    entity_slots = set(schema.entity_identity.get(entity.type, ()))
    identity: Json = {}
    for slot in declared:
        if slot in entity.identity:
            value = entity.identity[slot]
            identity[slot] = resolve(value) if slot in entity_slots else text_form(value)
    parts: Json = {"type": entity.type, "identity": identity}
    if not declared or len(identity) < len(declared):
        parts["label"] = normalize_label(entity.label, entity.type, rules)
    return make_key("ent", parts)


def local_entity_key(entity: CandidateEntity, ctx: KeyContext, rules: LabelRules) -> str:
    """`ent`: type, the scope segment's locator (structured), and the symbol or normalized label."""
    assert entity.scope_segment is not None
    parts: Json = {"type": entity.type, "scope": ctx.locator_key(ctx.segment(entity.scope_segment))}
    if entity.symbol:
        parts["symbol"] = symbol_form(entity.symbol, ctx.macros)
    else:
        parts["label"] = normalize_label(entity.label, entity.type, rules)
    return make_key("ent", parts)


def statement_anchor(statement: CandidateStatement, ctx: KeyContext) -> tuple[Segment, int]:
    """The statement's anchor segment and the 1-based ordinal of its first sentence there.

    The anchor is the innermost `details` or `unit` containing the first anchor segment, else the
    annotation unit containing it, else the top-level block outside every unit that contains it (a
    list, table, figure, …: an `uncovered` block of `annotation_units`), else the outermost
    block below sections and the document; never the document unless that is the segment itself.
    """
    if statement.anchor == "outside":
        raise KeyingError(f"statement {statement.id!r} lies outside the unit and is unresolved")
    first = min((ctx.segment(k) for k in statement.anchor), key=lambda s: (s.start, -s.end))
    chain = [first, *ctx.ancestors(first)]
    anchor = next((s for s in chain if s.kind in (SegmentKind.DETAILS, SegmentKind.UNIT)), None)
    if anchor is None:
        found = ctx.index.annotation_units()
        tops = {
            (s.kind, s.start, s.end) for s in (*(u.segment for u in found.units), *found.uncovered)
        }
        anchor = next((s for s in chain if (s.kind, s.start, s.end) in tops), None)
    if anchor is None:
        blocks = [s for s in chain if s.kind not in (SegmentKind.SECTION, SegmentKind.DOCUMENT)]
        anchor = blocks[-1] if blocks else first
    before = sum(
        1 for s in anchor.walk() if s.kind is SegmentKind.SENTENCE and s.start < first.start
    )
    return anchor, before + 1


def statement_key(statement: CandidateStatement, ctx: KeyContext) -> str:
    """`stm`: the anchor's generated locator (structured) and the first sentence's ordinal."""
    anchor, ordinal = statement_anchor(statement, ctx)
    return make_key("stm", {"anchor": ctx.locator_key(anchor), "ordinal": ordinal})


# --- Claim keys --------------------------------------------------------------------------------


def claim_parts(
    claim: CandidateClaim,
    schema: KeySchema,
    macros: Mapping[str, MacroDef],
    resolve: Resolve,
) -> Json:
    """The parts of a claim key: subject, prefixed predicate, object, identity qualifiers."""
    predicate = schema.predicate(claim.predicate)
    raw = claim.model_dump(mode="json")
    qualifiers_raw: Json = raw.get("qualifiers", {})
    obj = raw["object"]
    parts: Json = {
        "subject": resolve(claim.subject),
        "predicate": predicate,
        "object": {"key": resolve(obj["ref"])}
        if "t" not in obj
        else {"value": canonical_value(obj, macros, resolve)},
    }
    identity: Json = {}
    for name in ("modality", "polarity"):
        if name in qualifiers_raw:  # present only when not the default
            identity[name] = qualifiers_raw[name]
    if claim.statement is not None:
        identity["statement"] = resolve(claim.statement)
    if "conditions" in qualifiers_raw:
        tree = canonical_condition(
            qualifiers_raw["conditions"], macros, resolve, schema.symmetric_predicates
        )
        if tree is not None:
            identity["conditions"] = tree
    if "valid_time" in qualifiers_raw:
        identity["valid_time"] = canonical_value(qualifiers_raw["valid_time"], macros, resolve)
    if qualifiers_raw.get("modality") == "cited" and "attribution" in qualifiers_raw:
        identity["attribution"] = resolve(qualifiers_raw["attribution"]["ref"])
    for name in schema.identity_qualifiers.get(predicate, ()):
        if name in qualifiers_raw:
            identity[name] = canonical_qualifier(qualifiers_raw[name], macros, resolve)
    parts["qualifiers"] = identity
    return parts


def canonical_qualifier(value: Json, macros: Mapping[str, MacroDef], resolve: Resolve) -> Json:
    """A schema qualifier's canonical form: a value, an entity reference, or a map/list of them."""
    if isinstance(value, dict) and ("t" in value or set(value) == {"ref"}):
        return canonical_value(value, macros, resolve)
    if isinstance(value, dict):
        return {k: canonical_qualifier(v, macros, resolve) for k, v in value.items()}
    if isinstance(value, list):
        return [canonical_qualifier(v, macros, resolve) for v in value]
    return text_form(value) if isinstance(value, str) else value


@dataclass(frozen=True)
class Member:
    """C1's decision for one alternative member: the qualifiers it disagrees on, and whether its
    bindings disagree with the other members'."""

    qualifiers: tuple[str, ...] = ()
    bindings: bool = False


def member_parts(
    claim: CandidateClaim, member: Member, base: Json, ctx: KeyContext, resolve: Resolve
) -> Json:
    """A member's key parts: the claim's parts plus its canonical disagreeing qualifiers (null when
    it leaves one unset) and, when bindings disagree, its canonical bindings. A stored `scope`
    enters by its extent and its segment's locator, never by the physical segment key."""
    raw = claim.model_dump(mode="json")
    qualifiers_raw: Json = raw.get("qualifiers", {})
    own: Json = {}
    for name in sorted(member.qualifiers):
        value = qualifiers_raw.get(name)
        if value is None:
            own[name] = None
        elif name == "scope":
            locator = ctx.locator_key(ctx.segment(value["segment"]))
            own[name] = {"extent": value["extent"], "segment": locator}
        else:
            own[name] = canonical_qualifier(value, ctx.macros, resolve)
    extra: Json = {"qualifiers": own}
    if member.bindings:
        tree = {"object": raw["object"], "qualifiers": qualifiers_raw}
        extra["bindings"] = _bindings(tree, ctx.macros, resolve)
    return {**base, "member": extra}


def group_key(prefix: str, member_keys: Iterable[str]) -> str:
    """`alt` or `idg`: the hash of the sorted member keys."""
    if prefix not in ("alt", "idg"):
        raise ValueError(f"group prefix must be alt or idg, not {prefix!r}")
    return make_key(prefix, sorted(member_keys))


def alternative_group_key(member_keys: Iterable[str]) -> str:
    return group_key("alt", member_keys)


def identity_group_key(member_keys: Iterable[str]) -> str:
    return group_key("idg", member_keys)


# --- Batch keying ------------------------------------------------------------------------------


@dataclass
class Keys:
    """Keys by candidate id, alternatives' member keys, and the dropped claims with reasons."""

    entities: dict[str, str] = field(default_factory=dict)
    statements: dict[str, str] = field(default_factory=dict)
    claims: dict[str, str] = field(default_factory=dict)
    members: dict[str, str] = field(default_factory=dict)
    dropped: dict[str, str] = field(default_factory=dict)
    dropped_members: dict[str, str] = field(default_factory=dict)
    outside: set[str] = field(default_factory=set)  # unresolved "outside" statements

    def of(self, ref: str) -> str:
        for table in (self.entities, self.statements, self.claims):
            if ref in table:
                return table[ref]
        if ref in self.outside:
            raise KeyingError(f"statement {ref!r} lies outside the unit and is unresolved")
        raise KeyingError(f"unknown or dropped item {ref!r}")


def _entity_keys(
    candidates: KeyedCandidateSet,
    ctx: KeyContext,
    schema: KeySchema,
    rules: LabelRules,
    keys: Keys,
) -> None:
    by_id = {e.id: e for e in candidates.entities}
    visiting: set[str] = set()

    def key_of(entity_id: str) -> str:
        if entity_id in keys.entities:
            return keys.entities[entity_id]
        entity = by_id.get(entity_id)
        if entity is None:
            raise KeyingError(f"identity names unknown entity {entity_id!r}")
        if entity_id in visiting:
            raise KeyingError(f"entity identity cycle through {entity_id!r}")
        visiting.add(entity_id)
        if entity.key is not None:
            key = entity.key
        elif entity.scope is EntityScope.LOCAL:
            key = local_entity_key(entity, ctx, rules)
        else:
            key = global_entity_key(entity, schema, rules, key_of)
        visiting.discard(entity_id)
        keys.entities[entity_id] = key
        return key

    for entity in candidates.entities:
        try:
            key_of(entity.id)
        except KeyingError as error:
            keys.dropped.setdefault(entity.id, str(error))
            visiting.clear()


def key_claims(
    candidates: KeyedCandidateSet,
    ctx: KeyContext,
    schema: KeySchema,
    rules: LabelRules,
    members: Mapping[str, Member] | None = None,
) -> Keys:
    """Key every candidate: entities, statements, then claims in a topological order of their
    condition `claim` references. A candidate that cannot be keyed (on or behind a reference
    cycle, naming an unknown or dropped item, an unknown predicate, an unresolved `outside`
    statement) is dropped with its reason (D5 §5.2), never raised. `members` (C1's) adds member
    keys; a member that cannot be keyed is in `dropped_members` with its reason."""
    keys = Keys()
    _entity_keys(candidates, ctx, schema, rules, keys)
    for statement in candidates.statements:
        if statement.key is not None:
            keys.statements[statement.id] = statement.key
        elif statement.anchor == "outside":
            keys.outside.add(statement.id)  # consolidation resolves it to the statement it names
        else:
            try:
                keys.statements[statement.id] = statement_key(statement, ctx)
            except KeyingError as error:
                keys.dropped[statement.id] = str(error)

    claims = {c.id: c for c in candidates.claims}
    deps: dict[str, list[str]] = {}
    for claim in candidates.claims:
        tree = claim.qualifiers.model_dump(mode="json").get("conditions")
        deps[claim.id] = [] if tree is None else claim_refs(tree)

    state: dict[str, str] = {}  # id -> "active" | "done" | "dropped"
    stack: list[str] = []

    def drop(claim_id: str, reason: str) -> None:
        state[claim_id] = "dropped"
        keys.dropped.setdefault(claim_id, reason)

    def visit(claim_id: str) -> bool:
        status = state.get(claim_id)
        if status == "done":
            return True
        if status == "dropped":
            return False
        if status == "active":
            cycle = [*stack[stack.index(claim_id) :], claim_id]
            for member in cycle[:-1]:
                drop(member, "condition reference cycle: " + " -> ".join(cycle))
            return False
        state[claim_id] = "active"
        stack.append(claim_id)
        ok = True
        for ref in deps[claim_id]:
            if ref not in claims:
                drop(claim_id, f"condition references unknown claim {ref!r}")
                ok = False
            elif not visit(ref):
                drop(claim_id, f"depends on dropped claim {ref!r}")
                ok = False
        stack.pop()
        if not ok or state.get(claim_id) == "dropped":
            state[claim_id] = "dropped"
            return False
        claim = claims[claim_id]
        try:
            keys.claims[claim_id] = claim.key or make_key(
                "clm", claim_parts(claim, schema, ctx.macros, keys.of)
            )
        except KeyingError as error:
            drop(claim_id, str(error))
            return False
        state[claim_id] = "done"
        return True

    for claim in candidates.claims:
        visit(claim.id)

    for claim_id, member in (members or {}).items():
        if claim_id not in keys.claims:
            keys.dropped_members[claim_id] = f"claim {claim_id!r} has no key"
            continue
        claim = claims[claim_id]
        try:
            base = claim_parts(claim, schema, ctx.macros, keys.of)
            parts = member_parts(claim, member, base, ctx, keys.of)
        except KeyingError as error:
            keys.dropped_members[claim_id] = str(error)
            continue
        keys.members[claim_id] = make_key("clm", parts)
    return keys
