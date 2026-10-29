"""The set steps over the pool and their Python reference implementation (pool and interchange
§1, §3.1; TM §10; ADR-0021).

`Engine` is the interface both implementations serve: this module's `PythonEngine`, the reference,
and the DuckDB 2.0 engine (`pool/duckdb_engine.py`), which must be set-equal with it on the same
inputs (`pool/harness.py`). Consolidation owns what each step means and when it runs
(consolidation §3.2 to §3.4); identity (keys, normalized labels, canonical qualifier values) is
computed in Python and reaches a step as data.
Each step takes and returns Arrow relations under the schemas declared here, conformed on the way
in; its result is a set, held in the key order `ORDER` names, and aggregates are ordered by key.

- `alias_links(LINKABLE, reference_entities, reference_aliases) -> LINKS`: for each entity (an
  identifier, its type and normalized label), each key of a reference entity of its type with an
  alias whose normalized form equals the label, and how many such keys there are (one links;
  several are ambiguous; consolidation §3.3).
- `fuse(KEYED_CLAIMS) -> FUSED`: per claim key, the supports (observation ids) and the evidence
  items unioned, and the number of candidates (consolidation §3.4).
- `disagreements(MEANINGS) -> DISAGREEMENTS`: per claim key whose candidates hold two or more
  distinct meanings (the canonical text of their meaning-bearing values outside the key; null when
  a candidate sets none, which counts as a meaning), each distinct meaning (consolidation §3.4).
- `views(VIEW_CLAIMS, VIEW_ENTITIES, VIEW_IDENTITY, VIEW_ALTERNATIVES, specs) -> VIEW_FACTS`: the
  claim view's pool facts (D5 §8.2), one row per claim and view attribute with its values, distinct
  and sorted:
  - `same_slot`, for every claim: the other claims with the same predicate, subject and statement
    (an absent statement equals an absent statement);
  - `alternative_of`, for every claim: the other claims of the input that share an alternatives
    group with it;
  - each `ViewSpec` (a pack's compiled `views:` declaration, S2), for every claim whose predicate
    the declaration applies to: the projected field of each source claim (predicate `source`)
    whose `match.source` side names the entity or statement this claim's `match.claim` side
    names; the projection reads the entity view (`<subject|object>.<id|key|type|label|symbol>`)
    or an identity slot (`<subject|object>.identity.<slot>`), and a side that names no entity of
    the input projects nothing; an `ExternalReference` (`REFERENCE_CLASS`) is no entity there,
    like a statement or a value object (S2, `schema/rules.py`).
  Which claims are in the input (statuses, the call site) is the caller's: claim ids are local
  refs at submission and keys at finalize.

Evidence items travel as `arrow.json` lists of `core:Evidence` in stored form; `fuse` returns them
distinct, each item's keys sorted, ordered by `(start, end, role, coarse)` and then its text.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol

import pyarrow as pa

from corpus_structure.core._model.names import LOCAL_TO_PREFIXED
from corpus_structure.pool.contract import REFERENCE_ALIASES, REFERENCE_ENTITIES, conform
from corpus_structure.schema import interchange


def _schema(name: str, *fields: pa.Field) -> pa.Schema:
    return pa.schema(list(fields), metadata={b"cs.relation": name.encode()})


def _evidence() -> pa.Field:
    meta = {b"cs.class": b"core:Evidence"}
    return pa.field("evidence", interchange.JSON, nullable=False, metadata=meta)


_ID = pa.string()  # an identifier or key, text as `core:Key` is
LINKABLE = _schema(
    "linkable",
    pa.field("entity", _ID, nullable=False),
    pa.field("type", pa.string(), nullable=False),
    pa.field("normalized", pa.string(), nullable=False),
)
LINKS = _schema(
    "links",
    pa.field("entity", _ID, nullable=False),
    pa.field("key", _ID, nullable=False),
    pa.field("matches", pa.int64(), nullable=False),
)
KEYED_CLAIMS = _schema(
    "keyed_claims",
    pa.field("key", _ID, nullable=False),
    pa.field("observation_id", pa.int64(), nullable=False),
    _evidence(),
)
FUSED = _schema(
    "fused",
    pa.field("key", _ID, nullable=False),
    pa.field("supports", pa.list_(pa.field("item", pa.int64(), nullable=False)), nullable=False),
    _evidence(),
    pa.field("candidates", pa.int64(), nullable=False),
)
MEANINGS = _schema(
    "meanings",
    pa.field("key", _ID, nullable=False),
    pa.field("meaning", pa.string(), nullable=True),
)
DISAGREEMENTS = _schema(
    "disagreements",
    pa.field("key", _ID, nullable=False),
    pa.field("meaning", pa.string(), nullable=True),
)
VIEW_CLAIMS = _schema(
    "view_claims",
    pa.field("claim", _ID, nullable=False),
    pa.field("predicate", pa.string(), nullable=False),
    pa.field("subject", _ID, nullable=False),
    pa.field("object", _ID, nullable=True),  # an entity or statement; null for a value object
    pa.field("statement", _ID, nullable=True),
)
VIEW_ENTITIES = _schema(
    "view_entities",
    pa.field("entity", _ID, nullable=False),
    pa.field("key", _ID, nullable=True),
    pa.field("type", pa.string(), nullable=False),
    pa.field("label", pa.string(), nullable=False),
    pa.field("symbol", pa.string(), nullable=True),
)
VIEW_IDENTITY = _schema(
    "view_identity",
    pa.field("entity", _ID, nullable=False),
    pa.field("slot", pa.string(), nullable=False),
    pa.field("value", pa.string(), nullable=False),
)
VIEW_ALTERNATIVES = _schema(
    "view_alternatives",
    pa.field("group", _ID, nullable=False),
    pa.field("claim", _ID, nullable=False),
)
VIEW_FACTS = _schema(
    "view_facts",
    pa.field("claim", _ID, nullable=False),
    pa.field("view", pa.string(), nullable=False),
    pa.field("facts", pa.list_(pa.field("item", pa.string(), nullable=False)), nullable=False),
)
SAME_SLOT, ALTERNATIVE_OF = "same_slot", "alternative_of"
REFERENCE_CLASS = LOCAL_TO_PREFIXED["ExternalReference"]
ORDER: Mapping[str, tuple[str, ...]] = {
    "links": ("entity", "key"),
    "fused": ("key",),
    "disagreements": ("key", "meaning"),  # null meaning first
    "view_facts": ("claim", "view"),
}
PROJECTED = ("id", "key", "type", "label", "symbol")
type Side = Literal["subject", "object"]


@dataclass(frozen=True)
class ViewSpec:
    """A compiled `views:` declaration (S2's `ViewDecl`, D2 §7.4) with its `applies_to` expanded to
    predicates (S2's `expand_applies_to`)."""

    name: str
    applies_to: frozenset[str]
    source: str
    match_source: Side
    match_claim: Side
    head: Side
    attr: str  # one of PROJECTED, or "identity"
    slot: str | None = None  # the identity slot when attr is "identity"

    @classmethod
    def from_declaration(
        cls, name: str, declaration: Mapping[str, Any], applies_to: Iterable[str]
    ) -> ViewSpec:
        head, _, rest = str(declaration["project"]).partition(".")
        attr, _, slot = rest.partition(".")
        if head not in ("subject", "object") or not (
            (attr in PROJECTED and not slot) or (attr == "identity" and slot)
        ):
            raise ValueError(f"view {name}: cannot project {declaration['project']!r}")
        if head=='subject':selected_head:Side='subject'
        else:selected_head='object'
        match = declaration["match"]
        return cls(name, frozenset(applies_to), str(declaration["source"]), match["source"],
                   match["claim"], selected_head, attr, slot or None)  # fmt: skip


def view_inputs(
    claims: pa.Table,
    entities: pa.Table,
    identity: pa.Table,
    alternatives: pa.Table,
    specs: Sequence[ViewSpec],
) -> tuple[pa.Table, pa.Table, pa.Table, pa.Table]:
    """The `views` inputs conformed, claim and entity ids unique, view names distinct and not the
    generic facts' (both implementations call it, so they refuse the same inputs)."""
    out = (conform(claims, VIEW_CLAIMS), conform(entities, VIEW_ENTITIES),
           conform(identity, VIEW_IDENTITY), conform(alternatives, VIEW_ALTERNATIVES))  # fmt: skip
    for table, column in ((out[0], "claim"), (out[1], "entity")):
        values = table.column(column).to_pylist()
        if len(set(values)) != len(values):
            raise ValueError(f"views: {column} ids are not unique")
    names = [s.name for s in specs]
    if len(set(names)) != len(names) or {SAME_SLOT, ALTERNATIVE_OF} & set(names):
        raise ValueError(f"views: view names {names} repeat or shadow a generic fact")
    return out


class Engine(Protocol):
    """The set steps (module doc); implementations are set-equal on equal inputs."""

    name: str

    def alias_links(
        self, linkable: pa.Table, reference_entities: pa.Table, reference_aliases: pa.Table
    ) -> pa.Table: ...

    def fuse(self, claims: pa.Table) -> pa.Table: ...

    def disagreements(self, meanings: pa.Table) -> pa.Table: ...

    def views(
        self,
        claims: pa.Table,
        entities: pa.Table,
        identity: pa.Table,
        alternatives: pa.Table,
        specs: Sequence[ViewSpec],
    ) -> pa.Table: ...


def as_schema(table: pa.Table, schema: pa.Schema) -> pa.Table:
    """An engine's output under its declared step schema: columns by name, strings re-tagged as
    `arrow.json` where the schema says JSON (DuckDB's Arrow output drops the tag), other types
    cast (a list's item field, an integer width); a null where the schema forbids one is refused."""
    columns = []
    for f in schema:
        column = table.column(f.name).combine_chunks()
        if f.type == interchange.JSON and column.type == pa.string():
            column = pa.ExtensionArray.from_storage(interchange.JSON, column)
        elif column.type != f.type:
            column = column.cast(f.type)
        if not f.nullable and column.null_count:
            raise ValueError(f"{f.name}: a null where the step schema forbids one")
        columns.append(column)
    return pa.Table.from_arrays(columns, schema=schema)


def pool_relation(table: pa.Table, name: str) -> pa.Table:
    """A pool relation conformed to its own schema (it carries its `cs.relation`)."""
    if (table.schema.metadata or {}).get(b"cs.relation") != name.encode():
        raise ValueError(f"expected the pool's {name} relation")
    return table


def _canonical(item: Mapping[str, Any]) -> str:
    return json.dumps(item, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _evidence_key(item: Mapping[str, Any]) -> tuple[int, int, str, bool, str]:
    coarse = bool(item.get("coarse", False))
    return (item["start"], item["end"], item["role"], coarse, _canonical(item))


class PythonEngine:
    """The reference implementation: plain Python over rows, no engine."""

    name = "python"

    def alias_links(
        self, linkable: pa.Table, reference_entities: pa.Table, reference_aliases: pa.Table
    ) -> pa.Table:
        entities = pool_relation(reference_entities, REFERENCE_ENTITIES)
        aliases = pool_relation(reference_aliases, REFERENCE_ALIASES)
        by_id = {
            r["id"]: (r["type"], r["key"])
            for r in entities.select(["id", "type", "key"]).to_pylist()
        }
        keys: dict[tuple[str, str], set[str]] = defaultdict(set)
        for r in aliases.select(["entity_id", "normalized"]).to_pylist():
            if r["entity_id"] in by_id:
                type_, key = by_id[r["entity_id"]]
                keys[type_, r["normalized"]].add(key)
        found: dict[str, set[str]] = defaultdict(set)
        for r in conform(linkable, LINKABLE).to_pylist():
            found[r["entity"]] |= keys.get((r["type"], r["normalized"]), set())
        rows = [
            {"entity": entity, "key": key, "matches": len(matched)}
            for entity, matched in sorted(found.items())
            for key in sorted(matched)
        ]
        return pa.Table.from_pylist(rows, schema=LINKS)

    def fuse(self, claims: pa.Table) -> pa.Table:
        supports: dict[str, set[int]] = defaultdict(set)
        evidence: dict[str, dict[str, Mapping[str, Any]]] = defaultdict(dict)
        count: dict[str, int] = defaultdict(int)
        for r in conform(claims, KEYED_CLAIMS).to_pylist():
            key = r["key"]
            supports[key].add(r["observation_id"])
            count[key] += 1
            for item in json.loads(r["evidence"]):
                evidence[key][_canonical(item)] = item
        rows = [
            {
                "key": key,
                "supports": sorted(supports[key]),
                "evidence": "["
                + ",".join(_canonical(i) for i in sorted(evidence[key].values(), key=_evidence_key))
                + "]",
                "candidates": count[key],
            }
            for key in sorted(count)
        ]
        return pa.Table.from_pylist(rows, schema=FUSED)

    def disagreements(self, meanings: pa.Table) -> pa.Table:
        by_key: dict[str, set[str | None]] = defaultdict(set)
        for r in conform(meanings, MEANINGS).to_pylist():
            by_key[r["key"]].add(r["meaning"])
        rows = [
            {"key": key, "meaning": meaning}
            for key in sorted(by_key)
            if len(by_key[key]) > 1
            for meaning in sorted(by_key[key], key=lambda m: (m is not None, m or ""))
        ]
        return pa.Table.from_pylist(rows, schema=DISAGREEMENTS)

    def views(
        self,
        claims: pa.Table,
        entities: pa.Table,
        identity: pa.Table,
        alternatives: pa.Table,
        specs: Sequence[ViewSpec],
    ) -> pa.Table:
        c_t, e_t, i_t, a_t = view_inputs(claims, entities, identity, alternatives, specs)
        rows = c_t.to_pylist()
        entity = {r["entity"]: r for r in e_t.to_pylist()}
        slots: dict[tuple[str, str], set[str]] = defaultdict(set)
        for r in i_t.to_pylist():
            slots[r["entity"], r["slot"]].add(r["value"])
        known = {r["claim"] for r in rows}
        groups: dict[str, set[str]] = defaultdict(set)
        for r in a_t.to_pylist():
            groups[r["group"]].add(r["claim"])
        facts: dict[tuple[str, str], set[str]] = {}
        for c in rows:
            facts[c["claim"], SAME_SLOT] = {
                d["claim"] for d in rows if d["claim"] != c["claim"]
                and (d["predicate"], d["subject"], d["statement"])
                == (c["predicate"], c["subject"], c["statement"])
            }  # fmt: skip
            facts[c["claim"], ALTERNATIVE_OF] = set()
        for members in groups.values():
            for claim in members & known:
                facts[claim, ALTERNATIVE_OF] |= (members & known) - {claim}

        def project(spec: ViewSpec, source: Mapping[str, Any]) -> set[str]:
            head = entity.get(source[spec.head])
            if head is None or head["type"] == REFERENCE_CLASS:
                return set()
            if spec.attr == "identity":
                return slots.get((head["entity"], str(spec.slot)), set())
            value = head["entity"] if spec.attr == "id" else head[spec.attr]
            return set() if value is None else {value}

        for spec in specs:
            for c in rows:
                if c["predicate"] not in spec.applies_to:
                    continue
                matched = c[spec.match_claim]
                facts[c["claim"], spec.name] = set().union(*(
                    project(spec, s) for s in rows
                    if s["predicate"] == spec.source and matched is not None
                    and s[spec.match_source] == matched
                ))  # fmt: skip
        out = [
            {"claim": claim, "view": view, "facts": sorted(values)}
            for (claim, view), values in sorted(facts.items())
        ]
        return pa.Table.from_pylist(out, schema=VIEW_FACTS)
