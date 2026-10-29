"""Assembly (consolidation §3.2 to §3.4; D5 §3, §5, §11 row 0): the pool to the run's knowledge.

`assemble(pool, inputs, engine, tally)` is a pure function of the pool, the run's renditions, the
compiled schema version and the pass settings; it reads no database. Identity is computed in Python
(`core/keys.py`) and reaches the set steps (`pool/steps.py`, run on the selected engine) as data.

1. **Proposals.** Each `claim_proposal` observation's stored batch, as stored when its rendition is
   the run's rendition of the document, else located again on the run's rendition with A0's `parse`
   from its `authored` batch and `citation_frame` (`rederived`). Each passes S2's stored-form checks
   (`validate.runner.check_stored`), the validator `propose_claims` ran at submission; a rejected
   item is dropped and counted by its check code, and the rest is the keyed candidate set (T2).
   Candidate ids are local to their observation, so every set is keyed on its own.
2. **Markup statements**: every segment of a `statement_anchor` kind on the run's renditions, its
   kind from the unit's profile hint or the `details` markup (when `use_markup_hints`), and the
   containment claims the profile declares (`synthesize` on a `details` markup observation).
3. **Keying, round 1**: entities, statements and `ExternalReference` nodes.
   - **Linking** (D5 §3.3 point 3): each global entity's type and normalized label against the
     reference run's aliases (`alias_links`). One matching reference entity gives its key; several
     are `link_ambiguous`; none keeps the computed key.
   - **Resolution** (RC11): an external reference's link target, read as a locator on the run's
     rendition of its page, resolves when the segment it names anchors a statement of the run; the
     node then stands as that statement where it is cited. Otherwise it stays unresolved, counted
     by refusal code.
4. **Keying, round 2**: claims, with linked entity keys and resolved references preset, plus each
   `unsupported` item as a `core:unschematized` claim on the statement anchored where it lies.
   Drops by `DropReason`; then `malformed_evidence` (a stated claim with no primary evidence),
   `orphaned_premise` (a supposed claim whose dependants were all dropped) and their dependants.
5. **Fusion and alternatives** (D5 §5.3): `fuse` unions supports and evidence per claim key;
   `disagreements` finds keys whose candidates differ on meaning-bearing qualifiers or bindings.
   Those candidates are keyed again with F2b's member keys (round 3), fused per member key, and
   form an `alt` group; a batch's `alternatives[]` form a group of their claim keys. Members are
   `ambiguous`, with one `alternative_of` link per unordered pair, smaller key to larger.

Output rows are in key order; observation ids enter only supports and mentions.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

import pyarrow as pa
from pydantic import MISSING

from corpus_structure.consolidate.report import Tally
from corpus_structure.core._model.names import LOCAL_TO_PREFIXED
from corpus_structure.core.batch import AuthoredBatch, CitationFrame, StoredBatch
from corpus_structure.core.candidates import (
    AWAITING,
    CandidateClaim,
    CandidateEntity,
    CandidateReference,
    CandidateStatement,
    KeyedCandidateSet,
)
from corpus_structure.core.canonical import canonical_json
from corpus_structure.core.evidence import (
    MacroDef,
    RenditionContent,
    Segment,
    SegmentKind,
    segment_key,
)
from corpus_structure.core.keys import (
    KeyContext,
    Keys,
    LabelRules,
    Member,
    Uniform,
    alternative_group_key,
    citing_statement,
    key_claims,
    member_parts,
    normalize_label,
    statement_anchor,
    statement_key,
    text_form,
)
from corpus_structure.core.locators import LocatorRefused, LocatorSyntaxError
from corpus_structure.core.locators import parse as parse_locator
from corpus_structure.core.vocab import (
    SECTION_LIKE,
    STATEMENT_ANCHOR,
    AliasKind,
    CaseRule,
    DropReason,
    EntityScope,
    Establishment,
    EvidenceRole,
    MarkupKind,
    PassOutcome,
    ReferenceRefusal,
    StatementKind,
)
from corpus_structure.methods.llm.parse import RenditionView, parse
from corpus_structure.pool import contract
from corpus_structure.pool.steps import KEYED_CLAIMS, LINKABLE, MEANINGS, Engine
from corpus_structure.validate.runner import check_stored

STATEMENT = LOCAL_TO_PREFIXED["Statement"]
REFERENCE = LOCAL_TO_PREFIXED["ExternalReference"]
UNSCHEMATIZED = LOCAL_TO_PREFIXED["unschematized"]
FALLBACK_KIND = StatementKind.REMARK.value
NARRATIVE = StatementKind.NARRATIVE.value
ASSUMPTION = StatementKind.ASSUMPTION.value
SUPPOSED = "supposed"


# --- Inputs ------------------------------------------------------------------------------------


@dataclass
class Page:
    """One of the run's renditions: its document, page and content, the effective macro table
    and the stored segment ids by key."""

    rendition_id: int
    document_id: int
    document_key: str
    page: str
    content: RenditionContent
    macros: Mapping[str, MacroDef]
    segment_ids: Mapping[str, int]
    title: str | None = None  # the document's page title (`kb.document.title`)

    @cached_property
    def ctx(self) -> KeyContext:
        return KeyContext(self.document_key, self.content, self.page, self.macros)

    @cached_property
    def view(self) -> RenditionView:
        return RenditionView(self.content, self.page, self.ctx.rendition_key, self.macros)

    def key_of(self, segment: Segment) -> str:
        return segment_key(self.ctx.rendition_key, segment.kind, segment.start, segment.end)

    def segment_id(self, segment: Segment) -> int:
        return self.segment_ids[self.key_of(segment)]


@dataclass(frozen=True)
class Inputs:
    pages: Mapping[int, Page]  # by rendition id
    documents: Mapping[int, int]  # rendition id -> document id, for every rendition observed
    compiled: Any  # CompiledSchema
    labels: LabelRules = field(default_factory=LabelRules)
    use_markup_hints: bool = True

    @cached_property
    def by_document(self) -> dict[int, Page]:
        return {p.document_id: p for p in self.pages.values()}

    @cached_property
    def by_page(self) -> dict[str, Page]:
        return {p.page: p for p in self.pages.values()}


# --- Outputs -----------------------------------------------------------------------------------


@dataclass
class EntityRow:
    key: str
    type: str
    label: str
    scope: str
    scope_segment_id: int | None = None
    kind: str | None = None
    resolved_to: str | None = None  # a statement key, for a resolved ExternalReference
    descriptor: dict[str, Any] | None = None  # an ExternalReference's, as stored
    aliases: set[tuple[str, str, str]] = field(default_factory=set)  # alias, normalized, kind
    anchors: set[int] = field(default_factory=set)
    mentions: set[int] = field(default_factory=set)
    identity: dict[str, tuple[str | None, str | None]] = field(default_factory=dict)


@dataclass
class ClaimRow:
    key: str
    claim: CandidateClaim  # refs as keys
    rendition_id: int
    evidence: list[dict[str, Any]]
    supports: list[int]
    status: str = "accepted"
    group: str | None = None
    statement_kind: str | None = None


@dataclass(frozen=True)
class LinkRow:
    from_key: str
    link_type: str
    to_key: str
    detail: Mapping[str, Any]


@dataclass
class Knowledge:
    entities: dict[str, EntityRow] = field(default_factory=dict)
    claims: dict[str, ClaimRow] = field(default_factory=dict)
    links: list[LinkRow] = field(default_factory=list)
    groups: dict[str, tuple[str, ...]] = field(default_factory=dict)  # alt key -> member keys
    consumed: set[int] = field(default_factory=set)  # observation ids read


# --- Proposals ---------------------------------------------------------------------------------


@dataclass
class Proposal:
    observation_id: int
    task_id: int
    page: Page
    cs: KeyedCandidateSet
    keys: Keys = field(default_factory=Keys)
    mapping: dict[str, str] = field(default_factory=dict)  # local id -> key, every kind


def sorted_json(value: Any) -> str:
    """JSON text with sorted keys: a total order for choosing among equal-key candidates."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _json(text: str | None) -> Any:
    return None if text is None else json.loads(text)


def _proposals(pool: contract.Pool, inputs: Inputs, tally: Tally) -> list[Proposal]:
    index = {r["id"]: r for r in pool[contract.OBSERVATIONS].to_pylist()}
    out = []
    for row in pool.payload("claim_proposal").to_pylist():
        oid = row["observation_id"]
        obs = index[oid]
        page = inputs.by_document.get(inputs.documents.get(obs["rendition_id"] or -1, -1))
        if page is None:
            tally.drop(PassOutcome.UNREADABLE_PROPOSAL, f"observation:{oid}")
            continue
        if obs["rendition_id"] == page.rendition_id:
            stored: Any = StoredBatch.model_validate(_json(row["batch"]))
        elif row["authored"] is not None and row["citation_frame"] is not None:
            parsed = parse(
                page.view,
                AuthoredBatch.model_validate(_json(row["authored"])),
                CitationFrame.model_validate(_json(row["citation_frame"])),
                inputs.compiled.names.to_prefixed,
            )
            tally.count(PassOutcome.REDERIVED)
            for problem in parsed.report.problems:
                tally.drop(problem.code, f"observation:{oid}:{problem.path}")
            stored = parsed.stored
        else:
            tally.drop(PassOutcome.UNREADABLE_PROPOSAL, f"observation:{oid}")
            continue
        outcome = check_stored(stored, inputs.compiled, canonical_text=page.content.canonical_text)
        for issue in outcome.report.issues:
            tally.drop(issue.code, f"observation:{oid}:{'.'.join(map(str, issue.path))}")
        for d in outcome.drops:
            tally.drop(d.code, f"observation:{oid}:{d.ref}")
        if outcome.candidates is None:
            continue
        out.append(Proposal(oid, obs["task_id"], page, outcome.candidates))
    return sorted(out, key=lambda p: (p.page.page, p.cs.model_dump_json()))


# --- Markup ------------------------------------------------------------------------------------


@dataclass
class Markup:
    """A page's markup statements (ids are segment keys) and declared containment claims."""

    page: Page
    statements: dict[str, CandidateStatement] = field(default_factory=dict)
    kinds: dict[str, str] = field(default_factory=dict)  # segment key -> hinted kind
    claims: list[tuple[int, CandidateClaim]] = field(default_factory=list)  # (observation, claim)
    terms: list[str] = field(default_factory=list)  # dfn terms


def _markup(pool: contract.Pool, inputs: Inputs) -> dict[int, Markup]:
    out = {rid: Markup(page) for rid, page in inputs.pages.items()}
    for m in out.values():
        for segment in m.page.content.document.walk():
            if segment.kind not in STATEMENT_ANCHOR:
                continue
            key = m.page.key_of(segment)
            m.statements[key] = CandidateStatement(id=key, kind=FALLBACK_KIND, anchor=(key,))
            hint = segment.attrs.get("hint")
            if inputs.use_markup_hints and isinstance(hint, dict) and "statement_kind" in hint:
                m.kinds[key] = str(hint["statement_kind"])
    renditions = {r["id"]: r["rendition_id"] for r in pool[contract.OBSERVATIONS].to_pylist()}
    for row in pool.payload("author_markup").to_pylist():
        m = out.get(renditions.get(row["observation_id"]) or -1)
        if m is None:
            continue
        value = _json(row["value"]) or {}
        if row["markup"] == MarkupKind.DFN and isinstance(value, dict) and value.get("term"):
            m.terms.append(str(value["term"]))
        if row["markup"] != MarkupKind.DETAILS or not isinstance(value, dict):
            continue
        key = value.get("segment")
        if key not in m.statements:
            continue
        if inputs.use_markup_hints and value.get("statement_kind"):
            m.kinds[key] = str(value["statement_kind"])
        synth = _json(row["synthesize"])
        unit = (value.get("unit") or {}).get("segment")
        if synth and unit in m.statements:
            claim = CandidateClaim(
                id=f"synth:{row['observation_id']}",
                predicate=synth["predicate"],
                subject=key,
                object={"ref": unit},
                statement=key,
                evidence=tuple(synth["evidence"]),
            )
            m.claims.append((row["observation_id"], claim))
    return out


# --- External references -----------------------------------------------------------------------


def _target_locator(target: str, page: str) -> str:
    """An author link target read as a locator: `page#id`, with a bare `#id` on this page and a
    relative page joined to this page's directory."""
    if target.startswith("#"):
        return page + target
    if "/" not in target.split("#", 1)[0] and "/" in page:
        return page.rsplit("/", 1)[0] + "/" + target
    return target.removeprefix("./")


def _resolve(
    reference: CandidateReference, page: Page, inputs: Inputs, statements: set[str]
) -> tuple[str | None, ReferenceRefusal | None]:
    """The statement key the reference resolves to, or None with the refusal code."""
    target = reference.descriptor.target
    if target is MISSING:
        return None, ReferenceRefusal.NO_TARGET
    try:
        locator = parse_locator(_target_locator(str(target), page.page))
    except LocatorSyntaxError:
        return None, ReferenceRefusal.LOCATOR_SYNTAX
    there = inputs.by_page.get(locator.page)
    if there is None:
        return None, ReferenceRefusal.OTHER_PAGE
    try:
        segment = there.ctx.index.resolve(locator)
    except LocatorRefused:
        return None, ReferenceRefusal.LOCATOR_REFUSED
    probe = CandidateStatement(id="target", kind=FALLBACK_KIND, anchor=(there.key_of(segment),))
    key = statement_key(probe, there.ctx)
    return (key, None) if key in statements else (None, ReferenceRefusal.NO_STATEMENT)


# --- Keying ------------------------------------------------------------------------------------


def _schema_case(inputs: Inputs, type_: str) -> CaseRule:
    return inputs.compiled.key_schema.label_case.get(type_, CaseRule.FOLD)


def _mapping(cs: KeyedCandidateSet, keys: Keys) -> dict[str, str]:
    out = {**keys.entities, **keys.statements, **keys.claims}
    for r in cs.references:
        if r.id in keys.references:
            out[r.id] = keys.references[r.id] if r.resolved_to is AWAITING else str(r.resolved_to)
    return out


def _rekey(node: Any, mapping: Mapping[str, str]) -> Any:
    """A stored item's JSON with every local reference replaced by its key."""
    if isinstance(node, dict):
        out: dict[str, Any] = {}
        for k, v in node.items():
            if k in ("ref", "subject", "statement", "entity", "claim") and isinstance(v, str):
                out[k] = mapping.get(v, v)
            elif k == "derived_from" and isinstance(v, list):
                out[k] = [mapping.get(x, x) for x in v]
            else:
                out[k] = _rekey(v, mapping)
        return out
    if isinstance(node, list):
        return [_rekey(v, mapping) for v in node]
    return node


def _unschematized(p: Proposal) -> tuple[list[CandidateStatement], list[CandidateClaim]]:
    """Each unsupported item as a `core:unschematized` claim on the statement anchored where it
    lies (a `narrative` statement outside every statement anchor)."""
    statements, claims = [], []
    text = p.page.content.canonical_text
    for u in p.cs.unsupported:
        holder = min(
            (s for s in p.page.content.document.walk() if s.start <= u.start and u.end <= s.end),
            key=lambda s: s.end - s.start,
        )
        sid = f"unschematized:{u.id}"
        probe = CandidateStatement(id=sid, kind=NARRATIVE, anchor=(p.page.key_of(holder),))
        anchor, _ = statement_anchor(probe, p.page.ctx)
        statements.append(
            probe.model_copy(
                update={"key": statement_key(probe, p.page.ctx), "anchor": (p.page.key_of(anchor),)}
            )
        )
        coarse = {} if u.coarse is MISSING else {"coarse": u.coarse}
        claims.append(
            CandidateClaim(
                id=u.id,
                predicate=UNSCHEMATIZED,
                subject=sid,
                statement=sid,
                object={
                    "t": "phrase",
                    "text": text[u.start : u.end],
                    "start": u.start,
                    "end": u.end,
                    **coarse,
                },
                evidence=({"start": u.start, "end": u.end, "role": "primary", **coarse},),
            )
        )
    return statements, claims


def drop_after_keying(p: Proposal, tally: Tally) -> None:
    """`malformed_evidence`, `orphaned_premise` and the claims depending on them."""
    keys = p.keys
    claims = {c.id: c for c in p.cs.claims}
    deps = {cid: set(_condition_refs(c)) & set(claims) for cid, c in claims.items()}
    gone: dict[str, str] = {}
    for cid, c in claims.items():
        stated = c.establishment is Establishment.STATED
        if (
            cid in keys.claims
            and stated
            and not any(e.role is EvidenceRole.PRIMARY for e in c.evidence)
        ):
            gone[cid] = DropReason.MALFORMED_EVIDENCE
    for cid, c in claims.items():
        users = {u for u, d in deps.items() if cid in d}
        if (
            cid in keys.claims
            and c.qualifiers.modality == SUPPOSED
            and users
            and all(u not in keys.claims or u in gone for u in users)
        ):
            gone[cid] = DropReason.ORPHANED_PREMISE
    changed = True
    while changed:
        changed = False
        for cid, d in deps.items():
            if cid in keys.claims and cid not in gone and d & set(gone):
                gone[cid] = DropReason.DROPPED_DEPENDENCY
                changed = True
    for cid, code in sorted(gone.items()):
        keys.claims.pop(cid, None)
        tally.drop(code, f"observation:{p.observation_id}:{cid}")


def _condition_refs(claim: CandidateClaim) -> Iterator[str]:
    def walk(node: Any) -> Iterator[str]:
        if isinstance(node, dict):
            if node.get("op") == "claim" and isinstance(node.get("ref"), str):
                yield node["ref"]
            for v in node.values():
                yield from walk(v)
        elif isinstance(node, list):
            for v in node:
                yield from walk(v)

    tree = claim.qualifiers.conditions
    if tree is not MISSING:
        yield from walk(tree.model_dump(mode="json"))  # type: ignore[union-attr]


# --- Assembly ----------------------------------------------------------------------------------


def _table(rows: list[dict[str, Any]], schema: pa.Schema) -> pa.Table:
    return pa.Table.from_pylist(rows, schema=schema)


def _evidence(items: Iterable[Any], rendition_id: int) -> list[dict[str, Any]]:
    out = []
    for e in items:
        d = e if isinstance(e, dict) else e.model_dump(mode="json")
        out.append({**d, "rendition": rendition_id})
    return out


def _meaning(claim: CandidateClaim, schema: Any, p: Proposal, names: Sequence[str]) -> str:
    member = Member(qualifiers=tuple(names), bindings=True)
    resolver = Uniform(lambda ref: p.mapping.get(ref, ref))
    parts = member_parts(claim, member, {}, p.page.ctx, resolver, schema)
    return canonical_json(parts["member"]).decode()


@dataclass
class Record:
    """One keyed claim candidate: its key, its proposal (None for a declared containment claim),
    the claim, its page and support, and its set's local id -> key map."""

    key: str
    proposal: Proposal | None
    claim: CandidateClaim
    page: Page
    observation_id: int
    mapping: Mapping[str, str]
    meaning: str | None = None
    member: str | None = None


def _records(
    proposals: Sequence[Proposal], synth: Sequence[tuple[Page, KeyedCandidateSet, Keys, list[int]]]
) -> list[Record]:
    out = []
    for p in proposals:
        for c in p.cs.claims:
            if c.id in p.keys.claims:
                out.append(Record(p.keys.claims[c.id], p, c, p.page, p.observation_id, p.mapping))
    for page, cs, keys, oids in synth:
        mapping = {**keys.statements, **keys.claims}
        for c, oid in zip(cs.claims, oids, strict=True):
            if c.id in keys.claims:
                out.append(Record(keys.claims[c.id], None, c, page, oid, mapping))
    return out


def _fuse(engine: Engine, rows: Sequence[tuple[str, Record]]) -> dict[str, dict[str, Any]]:
    """`fuse` over the records by the given key: supports and evidence (with its rendition)."""
    keyed = [
        {
            "key": key,
            "observation_id": r.observation_id,
            "evidence": json.dumps(_evidence(r.claim.evidence, r.page.rendition_id)),
        }
        for key, r in rows
    ]
    return {x["key"]: x for x in engine.fuse(_table(keyed, KEYED_CLAIMS)).to_pylist()}


def _member_keys(
    records: Sequence[Record],
    split: set[str],
    proposals: Sequence[Proposal],
    schema: Any,
    labels: LabelRules,
    tally: Tally,
) -> None:
    """Round 3: each candidate of a disagreeing key keyed as a member, disagreeing on the
    meaning-bearing qualifiers whose canonical values differ in its key, and on bindings when
    those differ."""
    by_key: dict[str, list[Record]] = defaultdict(list)
    for r in records:
        if r.key in split and r.meaning is not None:
            by_key[r.key].append(r)
    wanted: dict[int, dict[str, Member]] = defaultdict(dict)
    for group in by_key.values():
        forms = [json.loads(r.meaning or "{}") for r in group]
        names = sorted(
            {
                n
                for f in forms
                for n in f["qualifiers"]
                if len({sorted_json(g["qualifiers"].get(n)) for g in forms}) > 1
            }
        )
        bindings = len({sorted_json(f.get("bindings")) for f in forms}) > 1
        for r in group:
            assert r.proposal is not None
            wanted[id(r.proposal)][r.claim.id] = Member(tuple(names), bindings)
    for p in proposals:
        members = wanted.get(id(p))
        if not members:
            continue
        keys = key_claims(p.cs, p.page.ctx, schema, labels, members=members)
        for r in records:
            if r.proposal is p and r.claim.id in keys.members:
                r.member = keys.members[r.claim.id]
        for ref, d in sorted(keys.dropped_members.items()):
            tally.drop(d.code, f"observation:{p.observation_id}:{ref}")


def _join_assumptions(
    proposals: Sequence[Proposal], statement_keys: dict[str, tuple[Page, CandidateStatement]]
) -> dict[tuple[int, str], str]:
    """Context premises (D5 §3.5): an `assumption` statement whose first sentence lies in another
    statement's anchor takes the key of the statement anchored there whose sentences contain it,
    the one with the greatest first-sentence ordinal not after its own (the markup statement opens
    every unit and `details` block, so a unit the run did not extract joins its markup
    statement). Outside units, with no other statement there, it keeps its own key. Joined keys
    no other statement holds leave `statement_keys`."""
    at: dict[tuple[int, str], list[tuple[int, str]]] = defaultdict(list)
    own: Counter[str] = Counter()
    for key, (page, statement) in statement_keys.items():
        if statement.kind != ASSUMPTION:
            anchor, ordinal = statement_anchor(statement, page.ctx)
            at[page.rendition_id, page.key_of(anchor)].append((ordinal, key))
    joined: dict[tuple[int, str], str] = {}
    for p in proposals:
        for s in p.cs.statements:
            if s.id not in p.keys.statements:
                continue
            key = p.keys.statements[s.id]
            if s.kind != ASSUMPTION:
                own[key] += 1
                continue
            anchor, ordinal = statement_anchor(s, p.page.ctx)
            before = [
                x
                for x in at.get((p.page.rendition_id, p.page.key_of(anchor)), ())
                if x[0] <= ordinal and x[1] != key
            ]
            if before:
                joined[p.observation_id, s.id] = max(before)[1]
            else:
                own[key] += 1
    for key, (_, statement) in list(statement_keys.items()):
        if statement.kind == ASSUMPTION and not own[key]:
            del statement_keys[key]
    return joined


def _statement_label(kind: str, anchor: Segment, page: Page) -> str:
    """D2 §6: `<kind> <unit id>`; `<kind> unit <n>` for a unit without an id (n its ordinal among
    the page's units); else `<kind> ¶<n>` (n the anchor's ordinal among the blocks of its kind in
    its innermost section)."""
    if anchor.kind is SegmentKind.UNIT:
        ident = anchor.attrs.get("id")
        if ident:
            return f"{kind} {ident}"
        units = [s for s in page.content.document.walk() if s.kind is SegmentKind.UNIT]
        return f"{kind} unit {units.index(anchor) + 1}"
    section = next(
        (a for a in page.ctx.ancestors(anchor) if a.kind in SECTION_LIKE), page.content.document
    )
    blocks = [s for s in section.walk() if s.kind is anchor.kind]
    return f"{kind} ¶{blocks.index(anchor) + 1}"


def assemble(pool: contract.Pool, inputs: Inputs, engine: Engine, tally: Tally) -> Knowledge:
    """The run's knowledge from its pool (module doc)."""
    schema = inputs.compiled.key_schema
    labels = inputs.labels
    knowledge = Knowledge()
    proposals = _proposals(pool, inputs, tally)
    markup = _markup(pool, inputs)

    # Round 1: entities, statements and references.
    for p in proposals:
        p.keys = key_claims(p.cs, p.page.ctx, schema, labels)
    statement_keys: dict[str, tuple[Page, CandidateStatement]] = {}
    for m in markup.values():
        for statement in m.statements.values():
            key = statement_key(statement, m.page.ctx)
            statement_keys.setdefault(key, (m.page, statement))
    for p in proposals:
        for s in p.cs.statements:
            if s.id in p.keys.statements:
                statement_keys.setdefault(p.keys.statements[s.id], (p.page, s))

    joined = _join_assumptions(proposals, statement_keys)

    linkable = []
    for p in proposals:
        for e in p.cs.entities:
            if e.scope is EntityScope.GLOBAL and e.id in p.keys.entities:
                case = _schema_case(inputs, e.type)
                linkable.append(
                    {
                        "entity": p.keys.entities[e.id],
                        "type": e.type,
                        "normalized": normalize_label(e.label, e.type, labels, case),
                    }
                )
    links = engine.alias_links(
        _table(linkable, LINKABLE),
        pool[contract.REFERENCE_ENTITIES],
        pool[contract.REFERENCE_ALIASES],
    )
    linked: dict[str, str] = {}
    for row in links.to_pylist():
        if row["matches"] == 1:
            linked[row["entity"]] = row["key"]
    for entity in sorted({r["entity"] for r in links.to_pylist()}):
        tally.count(PassOutcome.LINKED if entity in linked else PassOutcome.LINK_AMBIGUOUS)

    resolved: dict[tuple[int, str], str] = {}
    for p in proposals:
        for r in p.cs.references:
            if r.id not in p.keys.references:
                continue
            key, code = _resolve(r, p.page, inputs, set(statement_keys))
            if key is None:
                tally.count(PassOutcome.REFERENCE_UNRESOLVED)
                tally.unresolved[str(code)] += 1
            else:
                tally.count(PassOutcome.REFERENCE_RESOLVED)
                resolved[p.observation_id, r.id] = key

    # Round 2: claims, with linked entities, resolved references and unsupported items.
    for p in proposals:
        entities = tuple(
            e.model_copy(update={"key": linked.get(p.keys.entities[e.id], p.keys.entities[e.id])})
            if e.id in p.keys.entities
            else e
            for e in p.cs.entities
        )
        references = tuple(
            r.model_copy(update={"resolved_to": resolved[p.observation_id, r.id]})
            if (p.observation_id, r.id) in resolved
            else r
            for r in p.cs.references
        )
        extra_statements, extra_claims = _unschematized(p)
        statements = tuple(
            s.model_copy(update={"key": joined[p.observation_id, s.id]})
            if (p.observation_id, s.id) in joined
            else s
            for s in p.cs.statements
        )
        p.cs = p.cs.model_copy(
            update={
                "entities": entities,
                "references": references,
                "statements": (*statements, *extra_statements),
                "claims": (*p.cs.claims, *extra_claims),
                "unsupported": (),
            }
        )
        p.keys = key_claims(p.cs, p.page.ctx, schema, labels)
        for ref, d in sorted(p.keys.dropped.items()):
            tally.drop(d.code, f"observation:{p.observation_id}:{ref}")
        drop_after_keying(p, tally)
        p.mapping = _mapping(p.cs, p.keys)
        knowledge.consumed.add(p.observation_id)

    synth_sets: list[tuple[Page, KeyedCandidateSet, Keys, list[int]]] = []
    for m in markup.values():
        if not m.claims:
            continue
        statements = tuple(
            s.model_copy(update={"key": statement_key(s, m.page.ctx)})
            for s in m.statements.values()
        )
        cs = KeyedCandidateSet(
            renditions=(m.page.ctx.rendition_key,),
            statements=statements,
            claims=tuple(c for _, c in m.claims),
        )
        keys = key_claims(cs, m.page.ctx, schema, labels)
        synth_sets.append((m.page, cs, keys, [oid for oid, _ in m.claims]))

    records = _records(proposals, synth_sets)
    for r in records:
        if any(e.coarse is True for e in r.claim.evidence):
            tally.count(PassOutcome.COARSE_EVIDENCE)
    fused = _fuse(engine, [(r.key, r) for r in records])

    meanings = []
    for r in records:
        if r.proposal is not None:
            names = schema.meaning_qualifiers(r.claim.predicate, r.claim.qualifiers.modality)
            r.meaning = _meaning(r.claim, schema, r.proposal, names)
            meanings.append({"key": r.key, "meaning": r.meaning})
    split = {x["key"] for x in engine.disagreements(_table(meanings, MEANINGS)).to_pylist()}
    _member_keys(records, split, proposals, schema, labels, tally)
    fused_members = _fuse(engine, [(r.member, r) for r in records if r.member is not None])

    # Claim rows: one per claim key, or per member key in a group.
    chosen: dict[str, tuple[Record, str]] = {}  # final key -> (record, canonical dump)
    finals: dict[str, set[str]] = defaultdict(set)  # claim key -> its rows' keys
    for r in records:
        if r.key in split and r.member is None:
            continue  # a member that could not be keyed
        final = r.member or r.key
        finals[r.key].add(final)
        dump = sorted_json(_rekey(r.claim.model_dump(mode="json", by_alias=True), r.mapping))
        if final not in chosen or dump < chosen[final][1]:
            chosen[final] = (r, dump)
    for final, (r, dump) in sorted(chosen.items()):
        row = fused_members[final] if r.member is not None else fused[r.key]
        claim = CandidateClaim.model_validate({**json.loads(dump), "id": final, "key": final})
        knowledge.claims[final] = ClaimRow(
            final, claim, r.page.rendition_id, json.loads(row["evidence"]), list(row["supports"])
        )
    for k in sorted(split):
        members = sorted(finals.get(k, ()))
        if len(members) >= 2:
            _group(knowledge, members, {"reason": "disagreement"})
    for p in proposals:
        for a in p.cs.alternatives:
            keys_ = {p.keys.claims[ref] for ref in a.refs if ref in p.keys.claims}
            members = sorted({m for k in keys_ for m in finals.get(k, ())})
            if len(members) >= 2:
                _group(knowledge, members, {"reason": a.reason})

    _entities(knowledge, proposals, markup, statement_keys, joined, inputs, tally)
    return knowledge


def _group(knowledge: Knowledge, members: list[str], detail: Mapping[str, Any]) -> None:
    group = alternative_group_key(members)
    knowledge.groups[group] = tuple(members)
    for m in members:
        knowledge.claims[m].status = "ambiguous"
        knowledge.claims[m].group = group
    for i, a in enumerate(members):
        for b in members[i + 1 :]:
            knowledge.links.append(LinkRow(a, "alternative_of", b, {"group": group, **detail}))


# --- Entities, statements and references -------------------------------------------------------


def _canonical_label(labels: Sequence[str], terms: Sequence[str]) -> str:
    """The most frequent surface form; a `dfn` term or page title whose normalization equals the
    entity's first; ties by code point order (D5 §3.3 point 4)."""
    pool = list(terms) or list(labels)
    counts = Counter(pool)
    return min(counts, key=lambda s: (-counts[s], s))


def _entities(
    knowledge: Knowledge,
    proposals: Sequence[Proposal],
    markup: Mapping[int, Markup],
    statement_keys: Mapping[str, tuple[Page, CandidateStatement]],
    joined: Mapping[tuple[int, str], str],
    inputs: Inputs,
    tally: Tally,
) -> None:
    schema = inputs.compiled.key_schema
    labels = inputs.labels
    members: dict[str, list[tuple[Proposal, CandidateEntity]]] = defaultdict(list)
    for p in proposals:
        for e in p.cs.entities:
            if e.id in p.keys.entities:
                members[p.keys.entities[e.id]].append((p, e))
    terms_by_page = {
        m.page.rendition_id: [*m.terms, *([m.page.title] if m.page.title else [])]
        for m in markup.values()
    }
    for key, found in sorted(members.items()):
        _p0, e0 = found[0]
        case = _schema_case(inputs, e0.type)
        normal = normalize_label(e0.label, e0.type, labels, case)
        surfaces = [s for _, e in found for s in (e.label, *e.aliases)]
        terms = [
            t
            for p, _ in found
            for t in terms_by_page.get(p.page.rendition_id, ())
            if normalize_label(t, e0.type, labels, case) == normal
        ]
        row = EntityRow(key, e0.type, _canonical_label(surfaces, terms), e0.scope.value)
        for p, e in found:
            row.mentions.add(p.observation_id)
            kind = AliasKind.LABEL.value
            for s in (e.label, *e.aliases):
                row.aliases.add((s, normalize_label(s, e.type, labels, case), kind))
            if e.symbol is not MISSING and e.symbol:
                row.aliases.add(
                    (
                        str(e.symbol),
                        text_form(str(e.symbol), CaseRule.PRESERVE),
                        AliasKind.SYMBOL.value,
                    )
                )
            if e.scope_segment is not MISSING:
                sid = p.page.segment_ids.get(str(e.scope_segment))
                row.scope_segment_id = sid
                if sid is not None:
                    row.anchors.add(sid)
            entity_slots = set(schema.entity_identity.get(e.type, ()))
            for slot, value in e.identity.items():
                if slot in entity_slots:
                    row.identity[slot] = (p.mapping.get(value, value), None)
                else:
                    slot_case = schema.slot_case.get(slot, CaseRule.FOLD)
                    row.identity[slot] = (None, text_form(value, slot_case))
        for t in terms:
            row.aliases.add((t, normalize_label(t, e0.type, labels, case), AliasKind.TERM.value))
        knowledge.entities[key] = row

    kinds: dict[str, Counter[str]] = defaultdict(Counter)
    hinted: dict[str, str] = {}
    mentions: dict[str, set[int]] = defaultdict(set)
    for m in markup.values():
        for seg_key, kind in m.kinds.items():
            hinted[statement_key(m.statements[seg_key], m.page.ctx)] = kind
    for p in proposals:
        for s in p.cs.statements:
            if s.id in p.keys.statements:
                k = p.keys.statements[s.id]
                if (p.observation_id, s.id) not in joined:  # a joined premise has no vote
                    kinds[k][s.kind] += 1
                mentions[k].add(p.observation_id)
    for key, (page, statement) in sorted(statement_keys.items()):
        if key in hinted:
            kind = hinted[key]
        elif kinds[key]:
            kind = min(kinds[key], key=lambda k: (-kinds[key][k], k))
        else:
            kind = FALLBACK_KIND
            tally.count(PassOutcome.UNHINTED_STATEMENT_KIND)
        anchor, _ = statement_anchor(statement, page.ctx)
        sid = page.segment_id(anchor)
        label = _statement_label(kind, anchor, page)
        row = EntityRow(key, STATEMENT, label, EntityScope.LOCAL.value, sid, kind)
        row.anchors.add(sid)
        row.mentions |= mentions.get(key, set())
        knowledge.entities[key] = row
    for p in proposals:
        for s in p.cs.statements:  # unschematized statements keyed in round 2
            if s.id in p.keys.statements and p.keys.statements[s.id] not in knowledge.entities:
                k = p.keys.statements[s.id]
                anchor, _ = statement_anchor(s, p.page.ctx)
                sid = p.page.segment_id(anchor)
                label = _statement_label(s.kind, anchor, p.page)
                row = EntityRow(k, STATEMENT, label, EntityScope.LOCAL.value, sid, s.kind)
                row.anchors.add(sid)
                knowledge.entities[k] = row
            if s.id in p.keys.statements:
                knowledge.entities[p.keys.statements[s.id]].mentions.add(p.observation_id)

    for p in proposals:
        keyed = [s for s in p.cs.statements if s.id in p.keys.statements]
        for r in p.cs.references:
            if r.id not in p.keys.references:
                continue
            key = p.keys.references[r.id]
            citing = citing_statement(r, keyed, p.page.ctx)
            anchor, _ = statement_anchor(citing, p.page.ctx)
            d = r.descriptor
            quote = p.page.content.canonical_text[d.start : d.end]
            row = knowledge.entities.get(key) or EntityRow(
                key, REFERENCE, quote, EntityScope.LOCAL.value, p.page.segment_id(anchor)
            )
            row.resolved_to = None if r.resolved_to is AWAITING else str(r.resolved_to)
            row.descriptor = d.model_dump(mode="json")
            row.mentions.add(p.observation_id)
            row.aliases.add((quote, text_form(quote), AliasKind.LABEL.value))
            knowledge.entities[key] = row
