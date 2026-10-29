"""Writing the run's knowledge (consolidation §3.6; D3 §5, §8; D5 §1): one rebuild per pass.

Inside the caller's transaction: delete the run's links, claims and entities (children cascade);
pre-allocate ids; upsert evidence spans (P0-F-4's `upsert_spans`); binary COPY in dependency order
(`repo.copy_rows` over the generated tables): entities with `resolved_to_id`, aliases, anchors,
mentions, claims with `modality`, `polarity` and `attribution_entity_id` as columns (the qualifier
map keeps the rest), evidence, supports, links; at the final pass also the edge and identity rows;
and M19's failing outcomes as `verification` observations of the M19 task. An absent JSONB value is
SQL NULL. Before any write, the in-memory invariants are asserted (`InvariantViolation`, naming
the keys): INV-01 (a stated claim has primary evidence), INV-02 (every subject, object, statement
and attribution is a row of the run), INV-10 (every evidence span lies in its rendition's text).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import MISSING
from sqlalchemy import Connection, text

from corpus_structure.consolidate.assemble import Inputs, Knowledge
from corpus_structure.consolidate.finalize import ClaimEdge, EntityEdge
from corpus_structure.core import db as store
from corpus_structure.core._model import names
from corpus_structure.core.db import repo
from corpus_structure.core.payloads import VerificationDetail, VerificationPayload
from corpus_structure.core.vocab import Establishment, EvidenceRole, VerificationVerdict
from corpus_structure.validate.runner import Finding

T = store.metadata.tables
COLUMNS = (names.MODALITY, names.POLARITY, names.ATTRIBUTION)
VERIFIER = "validate.rules"


class InvariantViolation(AssertionError):
    """A row the checks should have dropped: a defect below them. The pass raises and rolls back."""

    def __init__(self, invariant: str, keys: Sequence[str]) -> None:
        self.invariant, self.keys = invariant, tuple(keys)
        super().__init__(f"{invariant}: {', '.join(self.keys)}")


def check_invariants(knowledge: Knowledge, inputs: Inputs) -> None:
    unprimary = [
        k
        for k, r in knowledge.claims.items()
        if r.claim.establishment is Establishment.STATED
        and not any(e["role"] == EvidenceRole.PRIMARY.value for e in r.evidence)
    ]
    if unprimary:
        raise InvariantViolation("INV-01", sorted(unprimary))
    dangling = []
    for k, r in knowledge.claims.items():
        c = r.claim
        refs = [
            c.subject,
            getattr(c.object, "ref", None),
            c.statement if isinstance(c.statement, str) else None,
            getattr(c.qualifiers.attribution, "ref", None),
        ]
        if any(ref is not None and ref not in knowledge.entities for ref in refs):
            dangling.append(k)
    if dangling:
        raise InvariantViolation("INV-02", sorted(dangling))
    outside = [
        k
        for k, r in knowledge.claims.items()
        for e in r.evidence
        if not 0
        <= e["start"]
        < e["end"]
        <= len(inputs.pages[e["rendition"]].content.canonical_text)
    ]
    if outside:
        raise InvariantViolation("INV-10", sorted(set(outside)))


def write(
    conn: Connection,
    run_id: int,
    schema_version_id: int,
    knowledge: Knowledge,
    edges: tuple[Sequence[ClaimEdge], Sequence[EntityEdge]] | None,
) -> None:
    """The rebuild (module doc); `edges` only at the final pass."""
    for table in ("kb.claim_link", "kb.claim", "kb.entity"):
        conn.execute(text(f"DELETE FROM {table} WHERE run_id = :r"), {"r": run_id})
    entities = sorted(knowledge.entities)
    claims = sorted(knowledge.claims)
    eid = dict(zip(entities, repo.allocate_ids(conn, T["kb.entity"], len(entities)), strict=True))
    cid = dict(zip(claims, repo.allocate_ids(conn, T["kb.claim"], len(claims)), strict=True))

    rows: list[tuple[Any, ...]] = []
    for k in entities:
        e = knowledge.entities[k]
        rows.append(
            (
                eid[k],
                run_id,
                k,
                schema_version_id,
                e.type,
                e.label,
                e.scope,
                e.scope_segment_id,
                {},
                e.descriptor.model_dump(mode="json") if e.descriptor is not None else None,
                e.kind,
                eid.get(e.resolved_to) if e.resolved_to else None,
            )
        )
    repo.copy_rows(
        conn,
        T["kb.entity"],
        (
            "id",
            "run_id",
            "key",
            "schema_version_id",
            "type",
            "label",
            "scope",
            "scope_segment_id",
            "attrs",
            "reference_descriptor",
            "kind",
            "resolved_to_id",
        ),
        rows,
    )
    aliases: dict[tuple[int, str, str], str] = {}
    for k in entities:
        for alias, normalized, kind in sorted(knowledge.entities[k].aliases):
            aliases.setdefault((eid[k], normalized, kind), alias)
    repo.copy_rows(
        conn,
        T["kb.entity_alias"],
        ("entity_id", "normalized", "alias_kind", "alias"),
        [(*key, alias) for key, alias in sorted(aliases.items())],
    )
    repo.copy_rows(
        conn,
        T["kb.entity_anchor"],
        ("entity_id", "segment_id"),
        sorted((eid[k], s) for k in entities for s in knowledge.entities[k].anchors),
    )
    repo.copy_rows(
        conn,
        T["kb.entity_mention"],
        ("entity_id", "observation_id"),
        sorted((eid[k], o) for k in entities for o in knowledge.entities[k].mentions),
    )

    rows = []
    for k in claims:
        r = knowledge.claims[k]
        c = r.claim
        dump = c.model_dump(mode="json", by_alias=True)
        q = c.qualifiers
        obj = getattr(c.object, "ref", None)
        attribution = getattr(q.attribution, "ref", None)
        qualifiers = {n: v for n, v in (dump.get("qualifiers") or {}).items() if n not in COLUMNS}
        rows.append(
            (
                cid[k],
                run_id,
                k,
                eid[c.subject],
                c.predicate,
                eid[obj] if obj is not None else None,
                None if obj is not None else dump["object"],
                schema_version_id,
                str(q.modality),
                q.polarity.value,
                eid[attribution] if attribution is not None else None,
                qualifiers,
                eid[c.statement] if isinstance(c.statement, str) else None,
                None if c.statement_role is MISSING else str(c.statement_role),
                r.status,
                c.establishment.value,
                _completeness(r),
            )
        )
    repo.copy_rows(
        conn,
        T["kb.claim"],
        (
            "id",
            "run_id",
            "key",
            "subject_id",
            "predicate",
            "object_entity_id",
            "object_value",
            "schema_version_id",
            "modality",
            "polarity",
            "attribution_entity_id",
            "qualifiers",
            "statement_id",
            "statement_role",
            "status",
            "establishment",
            "completeness",
        ),
        rows,
    )

    by_rendition: dict[int, list[tuple[int, int]]] = {}
    for k in claims:
        for e in knowledge.claims[k].evidence:
            by_rendition.setdefault(e["rendition"], []).append((e["start"], e["end"]))
    span: dict[tuple[int, int, int], int] = {}
    for rendition, ranges in sorted(by_rendition.items()):
        distinct = sorted(set(ranges))
        for rng, sid in zip(distinct, repo.upsert_spans(conn, rendition, distinct), strict=True):
            span[(rendition, *rng)] = sid
    evidence = sorted(
        {
            (cid[k], span[(e["rendition"], e["start"], e["end"])], e["role"])
            for k in claims
            for e in knowledge.claims[k].evidence
        }
    )
    repo.copy_rows(conn, T["kb.claim_evidence"], ("claim_id", "span_id", "role"), evidence)
    repo.copy_rows(
        conn,
        T["kb.claim_support"],
        ("claim_id", "observation_id"),
        sorted({(cid[k], o) for k in claims for o in knowledge.claims[k].supports}),
    )
    links = sorted(knowledge.links, key=lambda x: (x.from_key, x.link_type, x.to_key))
    lid = repo.allocate_ids(conn, T["kb.claim_link"], len(links))
    repo.copy_rows(
        conn,
        T["kb.claim_link"],
        ("id", "run_id", "from_claim_id", "link_type", "to_claim_id", "detail"),
        [
            (i, run_id, cid[x.from_key], x.link_type, cid[x.to_key], dict(x.detail))
            for i, x in zip(lid, links, strict=True)
        ],
    )

    if edges is None:
        return
    claim_edges, entity_edges = edges
    repo.copy_rows(
        conn,
        T["kb.claim_ref"],
        ("run_id", "claim_id", "kind", "path", "target_claim_id"),
        sorted({(run_id, cid[x.claim], x.kind, x.path, cid[x.target]) for x in claim_edges}),
    )
    repo.copy_rows(
        conn,
        T["kb.claim_entity_ref"],
        ("run_id", "claim_id", "role", "slot", "path", "entity_id"),
        sorted(
            {(run_id, cid[x.claim], x.role, x.slot, x.path, eid[x.entity]) for x in entity_edges},
            key=repr,
        ),
    )
    identity: list[tuple[int, str, int | None, str | None]] = []
    for k in entities:
        for slot, (value_key, value_text) in sorted(knowledge.entities[k].identity.items()):
            if value_key is not None and value_key in eid:
                identity.append((eid[k], slot, eid[value_key], None))
            elif value_text is not None:
                identity.append((eid[k], slot, None, value_text))
    repo.copy_rows(
        conn,
        T["kb.entity_identity"],
        ("entity_id", "slot", "value_entity_id", "value_text"),
        identity,
    )


def _completeness(row: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if any(e.get("coarse") is True for e in row.evidence):
        out["evidence_coarse"] = True
    return out


def write_findings(
    conn: Connection, m19_task_id: int, findings: Sequence[Finding], attempt: int = 1
) -> int:
    """M19's failing outcomes as `refuted` verification observations of the M19 task."""
    rows = [
        repo.ObservationRow(
            i,
            "verification",
            VerificationPayload(
                claim_key=f.claim,
                verifier=VERIFIER,
                verdict=VerificationVerdict.REFUTED,
                detail=VerificationDetail(rule=f.rule, severity=f.severity, message=f.message),
            ),
        )
        for i, f in enumerate(sorted(findings, key=lambda f: (f.claim, f.rule)))
    ]
    return repo.write_observations(conn, m19_task_id, attempt, rows) if rows else 0


def statuses_of(knowledge: Knowledge) -> Mapping[str, int]:
    out: dict[str, int] = {}
    for r in knowledge.claims.values():
        out[r.status] = out.get(r.status, 0) + 1
    return out
