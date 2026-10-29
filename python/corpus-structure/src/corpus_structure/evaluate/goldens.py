"""The golden store: sets, units, passes, frame versions, agreement, items and staleness
(D7 §3.2-§3.5; D3 §7; evaluation §3.3, P0-E-1).

This is the only module that writes `eval.golden_*` and `eval.citation_frame` rows, through the
repository's primitives (`store_golden_pass`, `set_golden_unit`, `insert_returning`), inside the
caller's transaction. A2's `write_golden` calls `record_pass`, `record_agreement` and
`mark_adjudicated` in its own transaction, which holds the unit row's lock.

- **Passes** (`record_pass`) store the authored batch as written and its citation frame as frame
  version 1, with the `payload_schema_id` of the registered `golden_batch` payload class, which
  names the schema of the batch and of every frame version of the pass. `read_pass` dispatches on
  that recorded id through the registry's readers: an id the readers do not hold is refused
  (`UnknownPayloadSchema`), as is one registered for another kind.
- **Items** (`ensure_items`) are keyed by (pass C, rendition, cascade version, schema version): the
  cascade version is A0's `CASCADE_VERSION`, the schema version the one whose name map derives the
  stored form. Absent items are derived from pass C's batch and the newest frame version that
  resolves on the rendition, through A0's `parse`, one row per entity, statement, claim,
  alternative group and unsupported item, each recording that frame version. `context` marks a
  context premise of the unit (`context_refs`, D2 §10.2). Items are inserted, never updated.
- **Frame resolution** is A0's (`resolve_entries`, on I0's resolver). A frame version resolves
  when every entry resolves as recorded. When none does but every entry of each of the unit's
  passes either resolves or re-locates (its recorded text in exactly one sentence of the page),
  the unit is **re-located**: each pass whose newest version does not resolve gains a version
  with the new locators, the recorded texts unchanged, a parent link to the version it re-locates
  and its reason naming the rendition; no version is rewritten, so items derived from earlier
  versions and every result that scored them stay as they were. The unit's `current_locator` is
  updated when its own locator moved (found as the annotation unit holding its `sN` sentences),
  and the unit returns to `adjudicated`. Anything else marks the unit `stale` and derives nothing;
  re-location never takes a nearest match.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, Literal

from pydantic import JsonValue
from sqlalchemy import Connection, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from corpus_structure.core import batch as B
from corpus_structure.core.db import metadata, repo
from corpus_structure.core.evidence import MacroDef, Segment
from corpus_structure.core.frame import FrameOutcome
from corpus_structure.core.locators import LocatorIndex, LocatorRefused, LocatorSyntaxError
from corpus_structure.core.locators import parse as parse_locator
from corpus_structure.core.payload_schemas import PayloadReaders
from corpus_structure.core.payloads import GoldenBatchPayload
from corpus_structure.core.vocab import (
    GoldenItemType,
    GoldenPass,
    GoldenUnitStatus,
    StatementKind,
    StatementRole,
)
from corpus_structure.methods.llm import parse as A0

if TYPE_CHECKING:
    from corpus_structure.evaluate.agreement import AgreementResult

T = metadata.tables
PAYLOAD_KIND = "golden_batch"
AUTHORED = "authored"


class GoldenStoreError(ValueError):
    """A golden write or read the store refuses."""


# --- Sets and units ----------------------------------------------------------------------------


def insert_set(conn: Connection, values: Mapping[str, Any]) -> int:
    """An `eval.golden_set` row; `UNIQUE (project, label, split)` refuses a reused label."""
    return repo.insert_returning(conn, T["eval.golden_set"], [dict(values)])[0]


def insert_units(conn: Connection, set_id: int, units: Sequence[tuple[str, int]]) -> dict[str, int]:
    """`draft` units (unit key, authored rendition) of a set; each unit's id by its key."""
    rows = [
        {
            "golden_set_id": set_id,
            "unit_key": key,
            "current_locator": key,
            "authored_rendition_id": rendition,
            "status": GoldenUnitStatus.DRAFT.value,
        }
        for key, rendition in units
    ]
    ids = repo.insert_returning(conn, T["eval.golden_unit"], rows)
    return {key: id_ for (key, _), id_ in zip(units, ids, strict=True)}


# --- Passes ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class FrameVersion:
    id: int
    version: int
    parent_id: int | None
    frame: B.CitationFrame
    reason: str


@dataclass(frozen=True)
class StoredPass:
    id: int
    unit_id: int
    pass_: GoldenPass
    guideline_version_id: int
    payload_schema_id: int
    batch: B.AuthoredBatch
    frames: tuple[FrameVersion, ...]  # oldest first

    @property
    def newest(self) -> FrameVersion:
        return self.frames[-1]


def payload_schema_id(conn: Connection) -> int:
    """The registered `golden_batch` payload schema (its newest version)."""
    found = repo.registered_ids(conn, [PAYLOAD_KIND])
    if PAYLOAD_KIND not in found:
        raise repo.UnregisteredPayload(f"no registered payload schema for {PAYLOAD_KIND!r}")
    return found[PAYLOAD_KIND]


def record_pass(
    conn: Connection,
    unit_id: int,
    pass_: GoldenPass,
    *,
    guideline_version_id: int,
    batch: B.AuthoredBatch,
    frame: B.CitationFrame,
    session_ref: str,
    model: str,
    inputs: Mapping[str, JsonValue],
    decisions: JsonValue | None = None,
) -> int:
    """Store a pass and its frame as version 1 (module doc); unique per (unit, pass, guideline)."""
    if not model or not inputs or not session_ref:
        raise GoldenStoreError("a golden pass records its session, model and inputs")
    if (pass_ is GoldenPass.C) != (decisions is not None):
        raise GoldenStoreError("pass c, and only pass c, records its decisions")
    payload = GoldenBatchPayload(batch=batch, citation_frame=frame).model_dump(mode="json")
    pass_id = repo.store_golden_pass(
        conn,
        {
            "golden_unit_id": unit_id,
            "pass": pass_.value,
            "guideline_version_id": guideline_version_id,
            "batch": payload["batch"],
            "decisions": decisions,
            "session_ref": session_ref,
            "model": model,
            "inputs": dict(inputs),
            "payload_schema_id": payload_schema_id(conn),
        },
    )
    repo.insert_returning(
        conn,
        T["eval.citation_frame"],
        [{"golden_pass_id": pass_id, "version": 1, "frame": payload["citation_frame"],
          "reason": AUTHORED}],
    )  # fmt: skip
    return pass_id


def read_pass(conn: Connection, pass_id: int, readers: PayloadReaders | None = None) -> StoredPass:
    """A pass with its frame versions, read under its recorded payload schema (module doc)."""
    gp, cf = T["eval.golden_pass"], T["eval.citation_frame"]
    row = conn.execute(select(gp).where(gp.c.id == pass_id)).one()
    readers = repo.payload_readers(conn) if readers is None else readers
    kind = readers.row(int(row.payload_schema_id)).kind
    if kind != PAYLOAD_KIND:
        raise GoldenStoreError(
            f"golden pass {pass_id} records payload schema {row.payload_schema_id} of kind "
            f"{kind!r}, not {PAYLOAD_KIND!r}"
        )
    frames: list[FrameVersion] = []
    batch: B.AuthoredBatch | None = None
    for f in conn.execute(select(cf).where(cf.c.golden_pass_id == pass_id).order_by(cf.c.version)):
        read = readers.read(
            int(row.payload_schema_id), {"batch": row.batch, "citation_frame": f.frame}
        )
        assert isinstance(read, GoldenBatchPayload)
        batch = read.batch
        frames.append(FrameVersion(int(f.id), int(f.version), f.parent_id, read.citation_frame,
                                   str(f.reason)))  # fmt: skip
    if batch is None:
        raise GoldenStoreError(f"golden pass {pass_id} has no frame version")
    return StoredPass(
        int(row.id),
        int(row.golden_unit_id),
        GoldenPass(row._mapping["pass"]),
        int(row.guideline_version_id),
        int(row.payload_schema_id),
        batch,
        tuple(frames),
    )


def unit_passes(conn: Connection, unit_id: int) -> list[int]:
    """The unit's pass ids, oldest first."""
    gp = T["eval.golden_pass"]
    return [
        int(i)
        for i in conn.execute(
            select(gp.c.id).where(gp.c.golden_unit_id == unit_id).order_by(gp.c.id)
        ).scalars()
    ]


def latest_pass_c(conn: Connection, unit_id: int) -> int | None:
    gp = T["eval.golden_pass"]
    return conn.execute(
        select(gp.c.id)
        .where(gp.c.golden_unit_id == unit_id, gp.c["pass"] == GoldenPass.C.value)
        .order_by(gp.c.id.desc())
        .limit(1)
    ).scalar()


# --- Unit status and agreement -----------------------------------------------------------------


def _unit(conn: Connection, unit_id: int) -> Any:
    unit = T["eval.golden_unit"]
    row = conn.execute(select(unit).where(unit.c.id == unit_id)).first()
    if row is None:
        raise GoldenStoreError(f"no golden unit {unit_id}")
    return row


def _set_status(conn: Connection, unit_id: int, status: GoldenUnitStatus) -> None:
    repo.set_golden_unit(conn, unit_id, status.value, _unit(conn, unit_id).agreement)


def record_agreement(conn: Connection, unit_id: int, result: AgreementResult | Mapping) -> None:
    """Store E2a's whole agreement result on the unit, validated against its model here."""
    from corpus_structure.evaluate.agreement import AgreementResult

    raw = result.model_dump(mode="json") if isinstance(result, AgreementResult) else result
    checked = AgreementResult.model_validate(raw).model_dump(mode="json")
    repo.set_golden_unit(conn, unit_id, str(_unit(conn, unit_id).status), checked)


def mark_adjudicated(conn: Connection, unit_id: int) -> None:
    """The unit is adjudicated once it has a pass C."""
    if latest_pass_c(conn, unit_id) is None:
        raise GoldenStoreError(f"golden unit {unit_id} has no pass c")
    _set_status(conn, unit_id, GoldenUnitStatus.ADJUDICATED)


# --- Context premises --------------------------------------------------------------------------


def _context_only(sentences: Sequence[str]) -> bool:
    return bool(sentences) and all(s.startswith("c") for s in sentences)


def context_refs(batch: B.AuthoredBatch) -> frozenset[str]:
    """The local refs of the unit's context premises (D2 §10.2): an `assumption` statement
    anchored only at standing-context sentences, and a `premise` claim whose evidence cites only
    them. They are scored only through the claims that reference them (D7 §5.1)."""
    out = {
        s.local_ref
        for s in batch.statements
        if isinstance(s, B.AuthoredStatement)
        and s.kind == StatementKind.ASSUMPTION
        and not isinstance(s.anchor, str)
        and _context_only(s.anchor)
    }
    out |= {
        c.local_ref
        for c in batch.claims
        if c.statement_role == StatementRole.PREMISE
        and _context_only([e.sentence for e in c.evidence])
    }
    return frozenset(out)


# --- Frame resolution and re-location ----------------------------------------------------------


@dataclass(frozen=True)
class Rendition:
    id: int
    key: str
    page: str
    index: LocatorIndex


def load_rendition(conn: Connection, rendition_id: int, page: str) -> Rendition:
    from corpus_structure.orchestrate.context import DbReader

    key = conn.execute(
        select(T["kb.rendition"].c.key).where(T["kb.rendition"].c.id == rendition_id)
    ).scalar_one()
    content = DbReader(conn, 0).content(rendition_id)  # content reads no run-scoped rows
    return Rendition(rendition_id, str(key), page, LocatorIndex(content, page))


type FrameState = Literal["resolved", "relocated", "unresolved"]


@dataclass(frozen=True)
class PassFrame:
    """A pass's frame on a rendition: the newest version that resolves, or the newest version's
    entries re-located, or unresolved."""

    state: FrameState
    version: FrameVersion
    outcomes: Mapping[str, FrameOutcome]

    def relocated(self) -> B.CitationFrame:
        root = self.version.frame.root
        return B.CitationFrame(
            {
                s: B.FrameEntry(locator=self.outcomes[s].locator or e.locator, text=e.text)
                if self.outcomes[s].status == "relocated"
                else e
                for s, e in root.items()
            }
        )


def pass_frame(stored: StoredPass, index: LocatorIndex) -> PassFrame:
    """Resolve the pass's frame versions, newest first (module doc)."""
    newest: dict[str, FrameOutcome] | None = None
    for version in reversed(stored.frames):
        outcomes = A0.resolve_entries(version.frame, index)
        newest = outcomes if newest is None else newest
        if all(o.status == "resolved" for o in outcomes.values()):
            return PassFrame("resolved", version, outcomes)
    assert newest is not None
    state: FrameState = (
        "relocated" if all(o.status != "unresolved" for o in newest.values()) else "unresolved"
    )
    return PassFrame(state, stored.newest, newest)


def frame_status(conn: Connection, pass_id: int, rendition_id: int) -> PassFrame:
    """A pass's frame on a rendition (its page is the unit key's)."""
    stored = read_pass(conn, pass_id)
    page = parse_locator(str(_unit(conn, stored.unit_id).unit_key)).page
    return pass_frame(stored, load_rendition(conn, rendition_id, page).index)


def _unit_segment(
    locator: str, frame: PassFrame, index: LocatorIndex
) -> tuple[Segment, str] | None:
    """The unit's segment and locator: its locator as recorded, else the one annotation unit that
    holds every resolved unit sentence (`sN`) of the frame."""
    try:
        return index.resolve(locator), locator
    except LocatorRefused, LocatorSyntaxError:
        pass
    inside = [o.segment for s, o in frame.outcomes.items() if s.startswith("s") and o.segment]
    if not inside:
        return None
    holding = [
        u
        for u in index.annotation_units().units
        if all(u.segment.start <= s.start and s.end <= u.segment.end for s in inside)
    ]
    if len(holding) != 1:
        return None
    return holding[0].segment, holding[0].key


# --- Items -------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Items:
    """What `ensure_items` found or did."""

    state: Literal["existing", "derived", "stale"]
    unit_id: int
    rendition_id: int
    cascade_version: str
    frame_version_id: int | None = None
    relocated: bool = False
    count: int = 0
    coarse: int = 0  # unlocated quotes given a coarse span over their cited sentence
    dropped: int = 0  # items the cascade dropped (A0's codes)


def _existing(
    conn: Connection, pass_id: int, rendition_id: int, cascade: str, schema_version_id: int
) -> int:
    gi = T["eval.golden_item"]
    rows = conn.execute(
        select(gi.c.id).where(
            gi.c.golden_pass_id == pass_id,
            gi.c.rendition_id == rendition_id,
            gi.c.cascade_version == cascade,
            gi.c.schema_version_id == schema_version_id,
        )
    )
    return len(rows.all())


def _item_rows(stored: B.StoredBatch) -> Iterator[tuple[GoldenItemType, str, Any]]:
    for e in stored.entities:
        yield GoldenItemType.ENTITY, e.local_ref, e
    for s in stored.statements:
        yield GoldenItemType.STATEMENT, s.local_ref, s
    for c in stored.claims:
        yield GoldenItemType.CLAIM, c.local_ref, c
    for i, a in enumerate(stored.alternatives):
        yield GoldenItemType.ALTERNATIVE, f"alt{i}", a
    for u in stored.unsupported:
        yield GoldenItemType.UNSUPPORTED, u.local_ref, u


def coarse_spans(payload: Any) -> int:
    """The coarse spans in a stored item's JSON."""
    if isinstance(payload, Mapping):
        return int(payload.get("coarse") is True) + sum(coarse_spans(v) for v in payload.values())
    if isinstance(payload, list):
        return sum(coarse_spans(v) for v in payload)
    return 0


def _add_version(conn: Connection, stored: StoredPass, frame: PassFrame, rendition: int) -> int:
    dumped = json.loads(frame.relocated().model_dump_json())
    return repo.insert_returning(
        conn,
        T["eval.citation_frame"],
        [
            {
                "golden_pass_id": stored.id,
                "version": stored.newest.version + 1,
                "parent_id": stored.newest.id,
                "frame": dumped,
                "reason": f"relocated onto rendition {rendition} from version "
                f"{stored.newest.version}",
            }
        ],
    )[0]


def ensure_items(
    conn: Connection,
    pass_c_id: int,
    rendition_id: int,
    schema_version_id: int,
    *,
    names: Mapping[str, str] | None = None,
    macros: Mapping[str, MacroDef] | None = None,
) -> Items:
    """Pass C's items on the rendition under A0's cascade version and the schema version (module
    doc). `names` defaults to the schema version's compiled name map; `macros` is the pack's
    fallback macro table."""
    cascade = A0.CASCADE_VERSION
    stored = read_pass(conn, pass_c_id)
    if stored.pass_ is not GoldenPass.C:
        raise GoldenStoreError(f"golden pass {pass_c_id} is pass {stored.pass_}, not c")
    unit = _unit(conn, stored.unit_id)
    out = Items("existing", int(unit.id), rendition_id, cascade)
    found = _existing(conn, pass_c_id, rendition_id, cascade, schema_version_id)
    if found:
        return replace(out, count=found)
    ren = load_rendition(conn, rendition_id, parse_locator(str(unit.unit_key)).page)
    frames = {pid: read_pass(conn, pid) for pid in unit_passes(conn, int(unit.id))}
    resolved = {pid: pass_frame(p, ren.index) for pid, p in frames.items()}
    mine = resolved[pass_c_id]
    located = _unit_segment(str(unit.current_locator), mine, ren.index)
    if any(f.state == "unresolved" for f in resolved.values()) or located is None:
        _set_status(conn, int(unit.id), GoldenUnitStatus.STALE)
        return replace(out, state="stale")
    relocated = any(f.state == "relocated" for f in resolved.values())
    frame_id = mine.version.id
    for pid, f in resolved.items():
        if f.state == "relocated":
            new = _add_version(conn, frames[pid], f, rendition_id)
            frame_id = new if pid == pass_c_id else frame_id
    frame = mine.relocated() if mine.state == "relocated" else mine.version.frame
    _, unit_locator = located
    if unit_locator != unit.current_locator:
        relocated = True
        conn.execute(
            T["eval.golden_unit"].update().where(T["eval.golden_unit"].c.id == unit.id)
            .values(current_locator=unit_locator)
        )  # fmt: skip
    if relocated:
        _set_status(conn, int(unit.id), GoldenUnitStatus.ADJUDICATED)
    if names is None:
        from corpus_structure.schema.registry import compiled_for

        names = dict(compiled_for(conn, schema_version_id).names.to_prefixed)
    from corpus_structure.core import tex

    view = A0.RenditionView(
        ren.index.rendition,
        ren.page,
        ren.key,
        tex.effective_macros(ren.index.rendition.macros, macros or {}),
    )
    batch = stored.batch
    if batch.unit_ref != unit_locator:  # the unit's own locator moved: derive at the new one
        batch = batch.model_copy(update={"unit_ref": unit_locator})
    parsed = A0.parse(view, batch, frame, names)
    if parsed.report.cascade_version != cascade:
        raise GoldenStoreError("the cascade's report names another version than its key")
    context = context_refs(stored.batch)
    rows = [
        {
            "golden_pass_id": pass_c_id,
            "citation_frame_id": frame_id,
            "rendition_id": rendition_id,
            "cascade_version": cascade,
            "schema_version_id": schema_version_id,
            "item_type": kind.value,
            "local_ref": ref,
            "payload": item.model_dump(mode="json"),
            "context": ref in context,
        }
        for kind, ref, item in _item_rows(parsed.stored)
    ]
    if rows:
        conn.execute(pg_insert(T["eval.golden_item"]).values(rows).on_conflict_do_nothing())
    return Items(
        "derived",
        int(unit.id),
        rendition_id,
        cascade,
        frame_id,
        relocated,
        len(rows),
        sum(coarse_spans(r["payload"]) for r in rows),
        len(parsed.report.problems),
    )
