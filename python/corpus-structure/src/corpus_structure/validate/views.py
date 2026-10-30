"""T4: the rule views of a keyed candidate set at either site (P0-S-2; schema and rules §3.6).

`build_views(candidates, compiled, site, readings=None)` returns one plain, read-only view object
per claim, which rule-engine reads through `getattr` under the site's language (`schema.rules`).
Attributes are `functools.cached_property`s, computed once per view and never written back. The
names are D5 §8.2's, fixed by `s4.rules`; element names are prefixed.

**Cross-claim facts** are built by indexing the candidate set once (`CrossClaimIndex`): claims by
(predicate, subject, statement) for `same_slot`, the alternative groups, the premise claims per
statement and of `assumption` statements, the symbols each claim gives as a parameter value, and
for each `views:` declaration its source claims by the declared side. No view scans the set, so
building every view is linear in claims (Proposed). The readings of the cross-claim facts are the
ones `schema.rules` records, which P2's two engines implement too.

**Sites.** At the batch site the candidates are the batch's own items, and symbols are read with
`core/tex.py` only (total and fast); `value.parse` and `value.math_kind` are not in the batch
language. At finalize the caller passes the grammar's `readings`, keyed by (claim id, value path),
computed by consolidation on its main thread; `validate` never imports `methods.math`.

**Token-derived facts** (`core/tex.py`): an entity's `index_symbols` (the letters after `_` in its
symbol) and a formula's `defined_symbol` (the symbol a formula of the form `x = …` defines).

**References** to an item the set lacks (a rejected one) give an entity view with an empty type,
never `None`; `claim.object` and `claim.statement` are null when the claim has none.
"""

from __future__ import annotations

import re
import typing
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from functools import cached_property
from typing import Any, NamedTuple

import pyarrow as pa
from pydantic import MISSING

from corpus_structure.core import tex
from corpus_structure.core._model.qualifiers import CORE_QUALIFIERS
from corpus_structure.core.candidates import (
    CandidateClaim,
    CandidateEntity,
    KeyedCandidateSet,
    Unkeyed,
)
from corpus_structure.core.canonical import canonical_json
from corpus_structure.core.translations import Omitted
from corpus_structure.core.vocab import MathKind, ParseOutcome, StatementRole
from corpus_structure.pool.steps import (
    ALTERNATIVE_OF,
    SAME_SLOT,
    VIEW_ALTERNATIVES,
    VIEW_CLAIMS,
    VIEW_ENTITIES,
    VIEW_IDENTITY,
    Engine,
    ViewSpec,
)
from corpus_structure.schema.tables import expand_applies_to

if typing.TYPE_CHECKING:
    from corpus_structure.schema.compile import CompiledSchema

SITES = ("batch", "finalize")
STATEMENT_CLASS = "core:Statement"
REFERENCE_CLASS = "core:ExternalReference"
GIVERS = frozenset({StatementRole.PREMISE.value, StatementRole.EXAMPLE_VALUE.value})
PREMISE = StatementRole.PREMISE.value
ASSUMPTION = "assumption"

type ValuePath = tuple[str | int, ...]
# A bare (optionally indexed) symbol, as written in a binding key: `mu`, `sigma_1`, `x_{ij}`.
_BARE = re.compile(r"[A-Za-z]+(_\{?\w+\}?)?")
MAX_SYMBOL = 64


class Reading(NamedTuple):
    """The math grammar's reading of one value (finalize only): its parse status, the kind it read
    as (`MathKind`), and its symbols."""

    status: ParseOutcome
    kind: MathKind | None = None
    symbols: tuple[str, ...] = ()


type Readings = Mapping[tuple[str, ValuePath], Reading]
# Precomputed pool facts (P2's `views` step): (claim id, attribute) -> the sorted distinct values.
type ViewFacts = Mapping[tuple[str, str], tuple[str, ...]]
OBJECT_PATH: ValuePath = ("object",)


# --- Token-derived facts ----------------------------------------------------------------------


def _significant(latex: str) -> list[tex.Token]:
    return [t for t in tex.tokens(latex) if t.kind != "space"]


def index_symbols(symbol: str | None) -> tuple[str, ...]:
    """The index letters of an indexed symbol: `i` of `X_i`, `i` and `j` of `X_{ij}`."""
    if not symbol:
        return ()
    toks = _significant(symbol)
    out: set[str] = set()
    for i, t in enumerate(toks):
        if t.text != "_" or i + 1 >= len(toks):
            continue
        nxt = toks[i + 1]
        if nxt.kind == "open":
            for inner in toks[i + 2 :]:
                if inner.kind == "close":
                    break
                if inner.kind == "char" and inner.text.isascii() and inner.text.isalpha():
                    out.add(inner.text)
        elif nxt.kind == "char" and nxt.text.isascii() and nxt.text.isalpha():
            out.add(nxt.text)
    return tuple(sorted(out))


def defined_symbol(latex: str | None) -> str | None:
    """The symbol a formula of the form `x = …` defines: a letter or control word, optionally
    indexed, then `=` (not `==`)."""
    if not latex:
        return None
    toks = _significant(latex)
    if not toks or not (
        (toks[0].kind == "char" and toks[0].text.isascii() and toks[0].text.isalpha())
        or toks[0].kind == "word"
    ):
        return None
    i = 1
    if i < len(toks) and toks[i].text == "_":
        i += 1
        if i < len(toks) and toks[i].kind == "open":
            depth = 0
            while i < len(toks):
                depth += {"open": 1, "close": -1}.get(toks[i].kind, 0)
                i += 1
                if depth == 0:
                    break
        else:
            i += 1
    if (
        i < len(toks)
        and toks[i].text == "="
        and not (i + 1 < len(toks) and toks[i + 1].text == "=")
    ):
        return latex[toks[0].start : toks[i - 1].end]
    return None


# --- The view objects -------------------------------------------------------------------------


@dataclass(frozen=True)
class EntityView:
    id: str
    key: str | None
    type: str
    label: str
    symbol: str | None
    identity: Mapping[str, str]

    @cached_property
    def index_symbols(self) -> tuple[str, ...]:
        return index_symbols(self.symbol)


@dataclass(frozen=True)
class ValueView:
    t: str
    latex: str | None
    v: str | None
    enum: str | None
    slot_kind: str
    reading: Reading | None = None

    @cached_property
    def defined_symbol(self) -> str | None:
        return defined_symbol(self.latex) if self.t == "formula" else None

    @property
    def parse(self) -> str | None:
        return self.reading.status.value if self.reading else None

    @property
    def math_kind(self) -> str | None:
        return self.reading.kind.value if self.reading and self.reading.kind else None


@dataclass(frozen=True)
class StatementView:
    id: str
    key: str | None
    kind: str


@dataclass(frozen=True)
class BindingView:
    symbol: str
    bind: str
    entity: str | None
    claim: str | None
    param: str | None


@dataclass(frozen=True)
class NodeView:
    op: str
    ref: str | None
    name: str | None
    rel: str | None
    x_latex: str | None


class QualifiersView:
    """One attribute per qualifier identifier of the version (null when absent)."""

    def __init__(self, values: Mapping[str, Any]) -> None:
        self.__dict__.update(values)


def _key(key: Any) -> str | None:
    return None if isinstance(key, Unkeyed) else str(key)


def _nodes(tree: Any) -> Iterator[dict[str, Any]]:
    if not isinstance(tree, dict) or "op" not in tree:
        return
    yield tree
    if tree["op"] in ("and", "or"):
        for arg in tree.get("args") or ():
            yield from _nodes(arg)
    for name in ("arg", "body"):
        if name in tree:
            yield from _nodes(tree[name])


def _node_view(n: Mapping[str, Any]) -> NodeView:
    x = n.get("x")
    return NodeView(
        op=n["op"],
        ref=n.get("ref"),
        name=n.get("name"),
        rel=n.get("rel"),
        x_latex=x["latex"].strip() if isinstance(x, dict) and "latex" in x else None,
    )


def _values(node: Any) -> Iterator[dict[str, Any]]:
    if isinstance(node, dict):
        if node.get("t") in ("formula", "set"):
            yield node
        for k, v in node.items():
            if k != "symbols":
                yield from _values(v)
    elif isinstance(node, list | tuple):
        for v in node:
            yield from _values(v)


def _gives(claim: CandidateClaim, param_map: str | None) -> frozenset[str]:
    """The bare symbols a supposition or setup value gives as parameter values: the formula values
    of its `ci:param_map` qualifier that are a bare symbol (D5 §8.2 `gives_symbols`)."""
    if claim.statement_role is None or str(claim.statement_role) not in GIVERS or not param_map:
        return frozenset()
    entries = (claim.qualifiers.__pydantic_extra__ or {}).get(param_map)
    out = set()
    for v in (entries or {}).values() if isinstance(entries, dict) else ():
        if isinstance(v, dict) and v.get("t") == "formula":
            text = str(v.get("latex", "")).strip().lstrip("\\")
            if len(text) <= MAX_SYMBOL and _BARE.fullmatch(text):
                out.add(text)
    return frozenset(out)


# --- The index --------------------------------------------------------------------------------


@dataclass
class CrossClaimIndex:
    """Every cross-claim fact's index, built once over the set; `reads` counts lookups, `built`
    the claims indexed per `views:` declaration (the linear-views check)."""

    slots: dict[tuple[str, str, str | None], list[str]] = field(default_factory=dict)
    alternatives: dict[str, set[str]] = field(default_factory=dict)
    premises: dict[str | None, list[str]] = field(default_factory=dict)
    assumption_premises: list[str] = field(default_factory=list)
    gives: dict[str, frozenset[str]] = field(default_factory=dict)
    given_count: dict[str, int] = field(default_factory=dict)
    views: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    applies: dict[str, frozenset[str]] = field(default_factory=dict)
    reads: int = 0
    built: dict[str, int] = field(default_factory=dict)

    def view(self, name: str, side_id: str | None) -> tuple[str, ...]:
        self.reads += 1
        if side_id is None:
            return ()
        return tuple(sorted(set(self.views[name].get(side_id, ()))))


def _side(claim: CandidateClaim, side: str) -> str | None:
    if side == "subject":
        return claim.subject
    obj = claim.object
    return getattr(obj, "ref", None)


# --- The builder ------------------------------------------------------------------------------


class _Builder:
    def __init__(
        self,
        candidates: KeyedCandidateSet,
        compiled: CompiledSchema,
        site: str,
        readings: Readings | None,
        facts: ViewFacts | None = None,
    ) -> None:
        if site not in SITES:
            raise ValueError(f"site {site!r} is not one of {SITES}")
        self.cs = candidates
        self.compiled = compiled
        self.site = site
        self.readings = readings or {}
        self.facts = facts
        lookup = compiled.lookup
        self.predicates = {p.prefixed: p for p in lookup.predicates.values()}
        self.qualifiers = {q.prefixed: q for q in lookup.qualifiers.values()}
        self.identifiers = compiled.rules.claim.identifiers.attribute
        self.entities = {e.id: e for e in candidates.entities}
        self.statements = {s.id: s for s in candidates.statements}
        self.references = {r.id: r for r in candidates.references}
        self.index = self._index()

    def _index(self) -> CrossClaimIndex:
        index = CrossClaimIndex()
        for c in self.cs.claims:
            statement = c.statement if isinstance(c.statement, str) else None
            index.slots.setdefault((c.predicate, c.subject, statement), []).append(c.id)
            role = str(c.statement_role) if isinstance(c.statement_role, str) else None
            if role == PREMISE:
                index.premises.setdefault(statement, []).append(c.id)
                st = self.statements.get(statement or "")
                if st is not None and st.kind == ASSUMPTION:
                    index.assumption_premises.append(c.id)
            p = self.predicates.get(c.predicate)
            gives = (
                _gives(c, p.param_map and self.qualifiers_prefixed(p.param_map))
                if p
                else frozenset()
            )
            index.gives[c.id] = gives
            for s in gives:
                index.given_count[s] = index.given_count.get(s, 0) + 1
        claims = {c.id for c in self.cs.claims}
        for group in self.cs.alternatives:
            members = [r for r in group.refs if r in claims]  # only claims of the input
            for r in members:
                index.alternatives.setdefault(r, set()).update(x for x in members if x != r)
        lookup = self.compiled.lookup
        for name, decl in self.compiled.rules.claim.views.items():
            index.applies[name] = frozenset(expand_applies_to(lookup, decl["applies_to"]))
            by_side: dict[str, list[str]] = {}
            count = 0
            for c in self.cs.claims:
                if c.predicate != decl["source"]:
                    continue
                count += 1
                key = _side(c, decl["match"]["source"])
                value = self._project(c, decl["project"])
                if key is not None and value is not None:
                    by_side.setdefault(key, []).append(value)
            index.views[name] = by_side
            index.built[name] = count
        return index

    def qualifiers_prefixed(self, local: str) -> str:
        return self.compiled.names.prefixed(local)

    def _project(self, claim: CandidateClaim, project: str) -> str | None:
        side, _, rest = project.partition(".")
        entity = self.entities.get(_side(claim, side) or "")
        if entity is None:
            return None  # a statement, a reference, a value object or a rejected item
        attr, _, slot = rest.partition(".")
        if attr == "identity":
            value = entity.identity.get(slot)
        else:
            value = getattr(entity, attr, None)
            value = _key(value) if attr == "key" else value
        return value if isinstance(value, str) else None

    def entity(self, ref: str) -> EntityView:
        e = self.entities.get(ref)
        if isinstance(e, CandidateEntity):
            symbol = e.symbol if isinstance(e.symbol, str) else None
            return EntityView(e.id, _key(e.key), e.type, e.label, symbol, dict(e.identity))
        if ref in self.statements:
            st = self.statements[ref]
            return EntityView(st.id, _key(st.key), STATEMENT_CLASS, st.kind, None, {})
        if ref in self.references:
            r = self.references[ref]
            return EntityView(r.id, _key(r.key), REFERENCE_CLASS, "", None, {})
        return EntityView(ref, None, "", "", None, {})  # an item the set lacks (rejected)

    def build(self) -> ClaimViews:
        views = tuple(ClaimView(self, c) for c in self.cs.claims)
        return ClaimViews(views, self.index)


@dataclass(frozen=True)
class ClaimViews(Sequence["ClaimView"]):
    """The claim views of a set, in claim order, with the index they share."""

    views: tuple[ClaimView, ...]
    cross: CrossClaimIndex

    def __len__(self) -> int:
        return len(self.views)

    @typing.overload
    def __getitem__(self, i: int) -> ClaimView: ...
    @typing.overload
    def __getitem__(self, i: slice) -> Sequence[ClaimView]: ...
    def __getitem__(self, i: int | slice) -> ClaimView | Sequence[ClaimView]:
        return self.views[i]


class ClaimView:
    """One claim's view (D5 §8.2). Pack `views:` facts are attributes by their declared name."""

    def __init__(self, builder: _Builder, claim: CandidateClaim) -> None:
        self._b = builder
        self._c = claim
        self.id = claim.id
        self.key = _key(claim.key)
        self.predicate = claim.predicate
        self.establishment = str(claim.establishment)
        role = claim.statement_role
        self.statement_role = str(role) if isinstance(role, str) else None
        self.evidence_count = len(claim.evidence)

    def __getattr__(self, name: str) -> Any:
        # a pack view (`claim.family_params`): computed once from the shared index
        b = self.__dict__.get("_b")
        if b is None or name not in b.index.views:
            raise AttributeError(name)
        claim: CandidateClaim = self.__dict__["_c"]
        decl = b.compiled.rules.claim.views[name]
        if b.facts is not None:
            value = b.facts.get((claim.id, name), ())
        elif claim.predicate in b.index.applies[name]:
            value = b.index.view(name, _side(claim, decl["match"]["claim"]))
        else:
            value = ()
        self.__dict__[name] = value
        return value

    @property
    def candidate(self) -> CandidateClaim:
        return self._c

    @cached_property
    def _predicate(self) -> Any:
        return self._b.predicates.get(self._c.predicate)

    @cached_property
    def groups(self) -> tuple[str, ...]:
        return tuple(self._predicate.subsets) if self._predicate else ()

    @cached_property
    def subject(self) -> EntityView:
        return self._b.entity(self._c.subject)

    @cached_property
    def object(self) -> EntityView | None:
        ref = getattr(self._c.object, "ref", None)
        return self._b.entity(ref) if isinstance(ref, str) else None

    @cached_property
    def value(self) -> ValueView | None:
        obj = self._c.object
        if hasattr(obj, "ref"):
            return None
        d = obj.model_dump(mode="json")
        reading = (
            self._b.readings.get((self._c.id, OBJECT_PATH)) if self._b.site == "finalize" else None
        )
        v = d.get("text") if d["t"] == "phrase" else d.get("v")
        return ValueView(
            t=d["t"],
            latex=d.get("latex"),
            v=v if isinstance(v, str) else (str(v) if v is not None else None),
            enum=d.get("enum"),
            slot_kind=self._predicate.object_kind if self._predicate else "",
            reading=reading,
        )

    @cached_property
    def _qualifiers(self) -> dict[str, Any]:
        return self._c.qualifiers.model_dump(mode="json", by_alias=True)

    @cached_property
    def qualifiers(self) -> QualifiersView:
        b = self._b
        q = self._c.qualifiers
        dumped = dict(self._qualifiers)
        # Compact stored dumps omit defaults. Restore them from the generated model
        # declarations, then project defaults and explicit values through one path.
        for spec in CORE_QUALIFIERS:
            if spec.default is not MISSING:
                dumped.setdefault(spec.name, getattr(q, spec.local_name))
        values: dict[str, Any] = {}
        for prefixed, attr in b.identifiers.items():
            info = b.qualifiers.get(prefixed)
            raw = dumped.get(prefixed)
            values[attr] = _qualifier_value(info.object_kind if info else "", prefixed, raw)
        return QualifiersView(values)

    @cached_property
    def statement(self) -> StatementView | None:
        st = (
            self._b.statements.get(self._c.statement)
            if isinstance(self._c.statement, str)
            else None
        )
        return StatementView(st.id, _key(st.key), st.kind) if st else None

    @cached_property
    def statement_kind(self) -> str | None:
        return self.statement.kind if self.statement else None

    @cached_property
    def bindings(self) -> tuple[BindingView, ...]:
        out = []
        source = {"object": self._c.object.model_dump(mode="json"), "q": self._qualifiers}
        for value in _values(source):
            for symbol, bnd in (value.get("symbols") or {}).items():
                out.append(
                    BindingView(
                        symbol, bnd["bind"], bnd.get("entity"), bnd.get("claim"), bnd.get("param")
                    )
                )
        return tuple(out)

    @cached_property
    def _condition_nodes(self) -> tuple[dict[str, Any], ...]:
        return tuple(_nodes(self._qualifiers.get("core:conditions")))

    @cached_property
    def condition_nodes(self) -> tuple[NodeView, ...]:
        return tuple(_node_view(n) for n in self._condition_nodes)

    @cached_property
    def claim_refs(self) -> tuple[str, ...]:
        return tuple(n["ref"] for n in self._condition_nodes if n["op"] == "claim")

    @cached_property
    def statement_premises(self) -> tuple[str, ...]:
        index = self._b.index
        statement = self._c.statement if isinstance(self._c.statement, str) else None
        found = [*index.premises.get(statement, ()), *index.assumption_premises]
        return tuple(sorted({p for p in found if p != self.id}))

    @cached_property
    def gives_symbols(self) -> tuple[str, ...]:
        return tuple(sorted(self._b.index.gives.get(self.id, ())))

    @cached_property
    def given_by_others(self) -> tuple[str, ...]:
        index = self._b.index
        own = index.gives.get(self.id, frozenset())
        return tuple(sorted(s for s, n in index.given_count.items() if n - (s in own) > 0))

    @cached_property
    def same_slot(self) -> tuple[str, ...]:
        if self._b.facts is not None:
            return self._b.facts.get((self.id, SAME_SLOT), ())
        c = self._c
        statement = c.statement if isinstance(c.statement, str) else None
        group = self._b.index.slots.get((c.predicate, c.subject, statement), [])
        return tuple(sorted(x for x in group if x != self.id))

    @cached_property
    def alternative_of(self) -> tuple[str, ...]:
        if self._b.facts is not None:
            return self._b.facts.get((self.id, ALTERNATIVE_OF), ())
        return tuple(sorted(self._b.index.alternatives.get(self.id, ())))

    @cached_property
    def unresolved_symbols(self) -> int:
        return sum(b.bind == "unresolved" for b in self.bindings)


def _qualifier_value(kind: str, prefixed: str, raw: Any) -> Any:
    """A qualifier's view value by object kind (D5 §8.2)."""
    if raw is None:
        return None
    if kind == "map" and isinstance(raw, dict):
        return {
            k: (v.get("latex", v.get("v", v.get("text"))) if isinstance(v, dict) else v)
            for k, v in raw.items()
        }
    if kind == "condition":
        return tuple(_node_view(n) for n in _nodes(raw))
    if kind == "entity" and isinstance(raw, dict):
        return raw.get("ref")
    if kind in ("formula", "set") and isinstance(raw, dict):
        return raw.get("latex")
    if kind == "phrase" and isinstance(raw, dict):
        return raw.get("text")
    if prefixed == "core:scope" and isinstance(raw, dict):
        return raw.get("extent")
    if kind == "number" and isinstance(raw, dict):
        return Decimal(str(raw.get("v")))
    if kind == "bool" and isinstance(raw, dict):
        return bool(raw.get("v"))
    if isinstance(raw, StrEnum):
        return raw.value
    if isinstance(raw, str):
        return raw
    if isinstance(raw, bool):
        return raw
    return canonical_json(raw)


def build_views(
    candidates: KeyedCandidateSet,
    compiled: CompiledSchema,
    site: str,
    readings: Readings | None = None,
    facts: ViewFacts | None = None,
) -> ClaimViews:
    """One view per claim of the set, at `site` (module doc). `facts`, when given, are the pool
    facts precomputed by P2's `views` step (`same_slot`, `alternative_of` and each `views:`
    declaration, by claim id and attribute); otherwise the builder's own index computes them."""
    return _Builder(candidates, compiled, site, readings, facts).build()


# --- P2's `views` step: its inputs from a candidate set, its output as facts ------------------


@dataclass(frozen=True)
class ViewTables:
    """The inputs of P2's `views` step (`pool/steps.py`) for one candidate set."""

    claims: pa.Table
    entities: pa.Table
    identity: pa.Table
    alternatives: pa.Table
    specs: tuple[ViewSpec, ...]


def view_tables(candidates: KeyedCandidateSet, compiled: CompiledSchema) -> ViewTables:
    """P2's `views` inputs: every claim with its sides and statement, every entity of the set
    (statements and `ExternalReference` nodes are no entity of a projection), their identity
    slots, the alternative groups, and the version's compiled `views:` declarations."""
    claims = [
        {
            "claim": c.id,
            "predicate": c.predicate,
            "subject": c.subject,
            "object": _side(c, "object"),
            "statement": c.statement if isinstance(c.statement, str) else None,
        }
        for c in candidates.claims
    ]
    entities = [
        {
            "entity": e.id,
            "key": _key(e.key),
            "type": e.type,
            "label": e.label,
            "symbol": e.symbol if isinstance(e.symbol, str) else None,
        }
        for e in candidates.entities
    ]
    identity = [
        {"entity": e.id, "slot": slot, "value": value}
        for e in candidates.entities
        for slot, value in sorted(e.identity.items())
    ]
    alternatives = [
        {"group": str(i), "claim": ref}
        for i, group in enumerate(candidates.alternatives)
        for ref in dict.fromkeys(group.refs)
    ]
    lookup = compiled.lookup
    specs = tuple(
        ViewSpec.from_declaration(name, decl, expand_applies_to(lookup, decl["applies_to"]))
        for name, decl in compiled.rules.claim.views.items()
    )
    return ViewTables(
        pa.Table.from_pylist(claims, schema=VIEW_CLAIMS),
        pa.Table.from_pylist(entities, schema=VIEW_ENTITIES),
        pa.Table.from_pylist(identity, schema=VIEW_IDENTITY),
        pa.Table.from_pylist(alternatives, schema=VIEW_ALTERNATIVES),
        specs,
    )


def view_facts(table: pa.Table) -> ViewFacts:
    """P2's `views` output (`VIEW_FACTS`) as facts by (claim id, attribute)."""
    return {(r["claim"], r["view"]): tuple(r["facts"]) for r in table.to_pylist()}


def engine_facts(
    engine: Engine, candidates: KeyedCandidateSet, compiled: CompiledSchema
) -> ViewFacts:
    """The pool facts of a candidate set computed by a P2 engine."""
    t = view_tables(candidates, compiled)
    return view_facts(engine.views(t.claims, t.entities, t.identity, t.alternatives, t.specs))


# --- The T4 declaration (TM §7, DP-08) --------------------------------------------------------


@dataclass(frozen=True)
class ViewMap:
    """One candidate type into one object of the claim-view language: each source field mapped to
    the attribute(s) it fills or declared omitted with why, and the attributes computed from
    elsewhere."""

    source: str
    fields: Mapping[str, str | tuple[str, ...] | Omitted]
    target: str
    introduced: Mapping[str, str] = field(default_factory=dict)


_NO_SPAN = Omitted("a span or segment key; no rule reads a position")
_M23 = Omitted("a derivation's provenance (M23); no rule reads it")

T4: tuple[ViewMap, ...] = (
    ViewMap(
        "KeyedCandidateSet",
        {
            "renditions": Omitted("the set's renditions; no rule reads them"),
            "entities": ("subject", "object"),
            "references": ("subject", "object"),
            "statements": ("statement", "statement_kind", "statement_premises"),
            "claims": ("same_slot", "given_by_others"),
            "alternatives": "alternative_of",
            "unsupported": Omitted(
                "text the schema cannot express; D5 §5.1 makes it a claim later"
            ),
        },
        "Claim",
        {"<views:>": "each `views:` declaration, from the claims it indexes"},
    ),
    ViewMap(
        "CandidateClaim",
        {
            "id": "id",
            "key": "key",
            "predicate": ("predicate", "groups"),
            "subject": "subject",
            "object": ("object", "value"),
            "qualifiers": (
                "qualifiers",
                "bindings",
                "condition_nodes",
                "claim_refs",
                "gives_symbols",
                "unresolved_symbols",
            ),
            "statement": ("statement", "statement_kind", "same_slot"),
            "statement_role": "statement_role",
            "establishment": "establishment",
            "derived_from": _M23,
            "rule": _M23,
            "evidence": "evidence_count",
        },
        "Claim",
    ),
    ViewMap(
        "CandidateEntity",
        {
            "id": "id",
            "key": "key",
            "type": "type",
            "label": "label",
            "symbol": ("symbol", "index_symbols"),
            "identity": "identity",
            "scope": Omitted("checked against ci:scope at submission"),
            "extent": Omitted("checked as INV-05 at submission"),
            "scope_segment": _NO_SPAN,
            "aliases": Omitted("keying's label rules read them"),
        },
        "Entity",
    ),
    ViewMap(
        "CandidateReference",
        {
            "id": "id",
            "key": "key",
            "descriptor": _NO_SPAN,
            "resolved_to": Omitted("consolidation's resolution, after the views"),
        },
        "Entity",
        {
            "type": "core:ExternalReference",
            "label": "empty: the quote is a span",
            "symbol": "null",
            "identity": "empty",
            "index_symbols": "empty",
        },
    ),
    ViewMap(
        "CandidateStatement",
        {"id": "id", "key": "key", "kind": "kind", "anchor": _NO_SPAN},
        "Statement",
    ),
    ViewMap(
        "StoredValue",
        {
            "t": "t",
            "latex": ("latex", "defined_symbol"),
            "v": "v",
            "text": "v",
            "enum": "enum",
            "symbols": Omitted("read as claim.bindings"),
            "sympy": Omitted("M11's; refused in a batch"),
            "parse": Omitted("M11's; the finalize reading is the readings argument"),
            "unit": Omitted("no rule reads a unit"),
            "basis": Omitted("no rule reads a basis"),
            "start": Omitted("a span, or an interval bound no rule reads"),
            "end": Omitted("a span, or an interval bound no rule reads"),
            "coarse": _NO_SPAN,
            "start_incl": Omitted("an interval bound no rule reads"),
            "end_incl": Omitted("an interval bound no rule reads"),
        },
        "Value",
        {
            "slot_kind": "the predicate's object kind",
            "parse": "the finalize reading's status",
            "math_kind": "the finalize reading's kind",
        },
    ),
)
