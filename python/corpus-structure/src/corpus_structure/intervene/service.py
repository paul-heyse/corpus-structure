"""The main profile's application functions (agent interface §3.5; D8 §2.1, §2.3).

A `Session` is one server instance: its engine, its instance id (`mcp-<hex>`, the `claimed_by`
holder `agent:<instance>` and the interventions' `session_ref`), the in-memory record of what it
served, and caches of compiled schema versions and assembled packets. The tools call these
functions on worker threads; each opens its own short transaction.

**Errors.** `ToolFailure` is an envelope or infrastructure failure (an unknown task, a lease this
instance does not hold, a stale `schema_hash`, a packet-hash mismatch); the server reports it with
`isError`. Every content problem is a successful call with a typed result.

**Serving re-assembles.** `read_unit` assembles the task's packet again from its recorded inputs
and compares its hash with the task's `packet_hash`; a mismatch names the task and is never served.
"""

from __future__ import annotations

import secrets
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import Connection, Engine, text

from corpus_structure.core.method import RunView, UnitRef, UnitView
from corpus_structure.core.vocab import InterventionKind, TaskStatus, TaskUnitType
from corpus_structure.methods.llm import packet as P
from corpus_structure.methods.llm import parts as parts_
from corpus_structure.methods.llm.agent_opus import AgentOpus, AgentOpusConfig
from corpus_structure.orchestrate import agent
from corpus_structure.orchestrate.context import run_view
from corpus_structure.semantic.proposals import ProposalIssue

METHOD = "agent.opus"


class ToolFailure(RuntimeError):
    """An envelope or infrastructure failure: reported with `isError`, naming the task."""


@dataclass
class Served:
    """What this instance served of a task at one attempt: the packet and the parts read."""

    attempt: int
    packet: P.Packet
    parts_read: set[int] = field(default_factory=set)

    @property
    def complete(self) -> bool:
        return self.parts_read >= set(range(1, len(self.packet.parts) + 1))


@dataclass
class Session:
    engine: Engine
    instance: str = field(default_factory=lambda: f"mcp-{secrets.token_hex(6)}")
    domains: Path | None = None
    method: AgentOpus = field(default_factory=AgentOpus)
    served: dict[int, Served] = field(default_factory=dict)
    _compiled: dict[int, Any] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def holder(self) -> str:
        return f"agent:{self.instance}"

    def compiled(self, conn: Connection, schema_version_id: int) -> Any:
        """The run's compiled schema version, rebuilt once per instance."""
        with self._lock:
            found = self._compiled.get(schema_version_id)
        if found is None:
            from corpus_structure.schema.registry import compiled_for

            found = compiled_for(conn, schema_version_id)
            with self._lock:
                self._compiled[schema_version_id] = found
        return found


# --- The task -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class TaskContext:
    id: int
    run_id: int
    project_id: int
    attempt: int
    status: TaskStatus
    claimed_by: str | None
    unit_key: str
    unit_id: int | None
    packet_hash: str | None
    held: bool
    config: AgentOpusConfig
    view: RunView
    unit: UnitView

    def segment(self) -> Any:
        from corpus_structure.core.locators import LocatorIndex
        from corpus_structure.core.locators import parse as parse_locator

        assert self.unit.rendition_id is not None
        content = self.view.reader.content(self.unit.rendition_id)
        page = parse_locator(self.unit_key).page
        return content, page, LocatorIndex(content, page).resolve(self.unit_key)


def task_context(conn: Connection, task_id: int) -> TaskContext:
    from corpus_structure.orchestrate.runner import unit_view

    row = conn.execute(
        text(
            "SELECT t.id, t.run_id, r.project_id, t.attempt, t.status, t.claimed_by, t.unit_key, "
            "t.unit_id, t.packet_hash, t.error IS NOT NULL AS held, c.params, m.name AS method "
            "FROM ops.task t JOIN ops.run r ON r.id = t.run_id "
            "JOIN ops.method_config c ON c.id = t.method_config_id "
            "JOIN ops.method m ON m.id = c.method_id WHERE t.id = :t"
        ),
        {"t": task_id},
    ).first()
    if row is None:
        raise ToolFailure(f"no task {task_id}")
    if row.method != METHOD:
        raise ToolFailure(f"task {task_id} is a {row.method} task, not {METHOD}")
    view = run_view(conn, int(row.run_id))
    ref = UnitRef(TaskUnitType.SEGMENT, row.unit_id, row.unit_key)
    return TaskContext(
        int(row.id),
        int(row.run_id),
        int(row.project_id),
        int(row.attempt),
        TaskStatus(row.status),
        row.claimed_by,
        str(row.unit_key),
        row.unit_id,
        row.packet_hash,
        bool(row.held),
        AgentOpusConfig.model_validate(row.params),
        view,
        unit_view(conn, view, ref),
    )


def require_lease(session: Session, task: TaskContext) -> None:
    if task.status != TaskStatus.AWAITING_AGENT or task.claimed_by != session.holder:
        raise ToolFailure(
            f"task {task.id}: this instance holds no lease on it (status {task.status}, held by "
            f"{task.claimed_by or 'nobody'}); lease it with queue_next"
        )


def assembled(session: Session, task: TaskContext) -> P.Packet:
    """The task's packet, assembled again and checked against its recorded hash."""
    packet = session.method.packet(task.unit, task.config)
    if task.packet_hash is not None and packet.hash != task.packet_hash:
        raise ToolFailure(
            f"task {task.id}: the packet assembled now hashes to {packet.hash[:12]}, the task "
            f"recorded {task.packet_hash[:12]}: an input changed; nothing is served"
        )
    return packet


@contextmanager
def _tx(session: Session) -> Iterator[Connection]:
    with session.engine.begin() as conn:
        yield conn


def _renew(conn: Connection, task: TaskContext) -> None:
    agent.renew_agent_lease(conn, task.id, task.attempt)


# --- queue_status, queue_next ----------------------------------------------------------------


class QueueCount(BaseModel):
    run_id: int
    mode: str
    stage: str
    awaiting: int


class QueueStatus(BaseModel):
    queues: list[QueueCount]
    budget_left: int | None = None  # the agent budget (D6 §7.4) is P0-O-2's; none in phase 0 yet


def queue_status(session: Session, run: int | None = None) -> QueueStatus:
    with session.engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT t.run_id, c.params->>'mode' AS mode, t.stage, count(*) AS n FROM ops.task "
                "t "
                "JOIN ops.method_config c ON c.id = t.method_config_id JOIN ops.method m ON "
                "m.id = c.method_id WHERE m.name = :m AND t.status = 'awaiting_agent' AND "
                "(CAST(:run AS bigint) IS NULL OR t.run_id = :run) "
                "GROUP BY 1, 2, 3 ORDER BY 1 DESC, 2, 3"
            ),
            {"m": METHOD, "run": run},
        )
        return QueueStatus(
            queues=[
                QueueCount(
                    run_id=r.run_id, mode=r.mode or "extract", stage=r.stage, awaiting=int(r.n)
                )
                for r in rows
            ]
        )


class LeasedTask(BaseModel):
    task_id: int
    run_id: int
    unit_key: str
    parts: int
    chars: int
    previous_issues: tuple[ProposalIssue, ...] = Field(
        default=(), exclude_if=lambda issues: not issues
    )


class QueueNext(BaseModel):
    tasks: list[LeasedTask]


def queue_next(
    session: Session,
    mode: Literal["extract", "adjudicate"] = "extract",
    run: int | None = None,
    max_units: int | None = None,
) -> QueueNext:
    """Lease the next unit of `mode` (agent interface §3.5); `max_units` is bounded by the
    configuration's (1 until A3 decides)."""
    with _tx(session) as conn:
        configs = [
            int(i)
            for (i,) in conn.execute(
                text(
                    "SELECT c.id FROM ops.method_config c JOIN ops.method m ON m.id = c.method_id "
                    "WHERE m.name = :m AND coalesce(c.params->>'mode', 'extract') = :mode"
                ),
                {"m": METHOD, "mode": mode},
            )
        ]
        if not configs:
            return QueueNext(tasks=[])
        leases = agent.lease_agent_tasks(
            conn, session_ref=session.instance, method_configs=configs, run_id=run
        )
    out = []
    for lease in leases:
        with session.engine.connect() as conn:
            task = task_context(conn, lease.id)
            packet = assembled(session, task)
        with session._lock:
            session.served[lease.id] = Served(lease.attempt, packet)
        out.append(
            LeasedTask(
                task_id=lease.id,
                run_id=lease.run_id,
                unit_key=task.unit_key,
                parts=len(packet.parts),
                chars=packet.chars,
            )
        )
    return QueueNext(tasks=out)


# --- read_unit, read_instructions --------------------------------------------------------------


class SentenceView(BaseModel):
    id: str
    locator: str
    text: str


class UnitPart(BaseModel):
    """`read_unit`'s structured content beside the packet text."""

    task_id: int
    part: int
    parts: int
    hash: str
    sentences: list[SentenceView]


def read_unit(session: Session, task_id: int, part: int = 1) -> tuple[str, UnitPart]:
    """One part of the task's packet and its sentence map; renews the lease."""
    with _tx(session) as conn:
        task = task_context(conn, task_id)
        require_lease(session, task)
        packet = assembled(session, task)
        if not 1 <= part <= len(packet.parts):
            raise ToolFailure(f"task {task_id} has {len(packet.parts)} part(s), not part {part}")
        _renew(conn, task)
    with session._lock:
        served = session.served.get(task_id)
        if served is None or served.attempt != task.attempt or served.packet.hash != packet.hash:
            served = session.served[task_id] = Served(task.attempt, packet)
        served.parts_read.add(part)
    sentences = [
        SentenceView(id=s.id, locator=s.locator, text=s.text)
        for s in packet.part_sentences(part - 1)
    ]
    return packet.parts[part - 1], UnitPart(
        task_id=task_id, part=part, parts=len(packet.parts), hash=packet.hash, sentences=sentences
    )


class PartInfo(BaseModel):
    name: str
    chars: int
    pages: int
    hash: str


class Instructions(BaseModel):
    """The part list (`part` absent), or one page of one part."""

    task_id: int
    parts: list[PartInfo]
    part: str | None = None
    page: int | None = None
    page_count: int | None = None
    text: str | None = None


def run_parts(session: Session, task: TaskContext) -> dict[str, parts_.Part]:
    return session.method.parts(task.view, task.config)


def read_instructions(
    session: Session, task_id: int, part: str | None = None, page: int = 1
) -> Instructions:
    with _tx(session) as conn:
        task = task_context(conn, task_id)
        require_lease(session, task)
        found = run_parts(session, task)
        _renew(conn, task)
    infos = [
        PartInfo(name=p.name, chars=len(p.text), pages=len(p.pages()), hash=p.hash)
        for p in found.values()
    ]
    if part is None:
        return Instructions(task_id=task_id, parts=infos)
    if part not in found:
        raise ToolFailure(f"no part {part!r}; the parts are {list(found)}")
    paged = found[part].pages()
    if not 1 <= page <= len(paged):
        raise ToolFailure(f"part {part!r} has {len(paged)} page(s), not page {page}")
    return Instructions(
        task_id=task_id,
        parts=infos,
        part=part,
        page=page,
        page_count=len(paged),
        text=paged[page - 1],
    )


# --- release, record_direction ----------------------------------------------------------------


class Released(BaseModel):
    task_id: int
    released: bool
    reason: str


def release(session: Session, task_id: int, reason: str) -> Released:
    with _tx(session) as conn:
        task = task_context(conn, task_id)
        require_lease(session, task)
        done = agent.release(conn, task_id, task.attempt)
    with session._lock:
        session.served.pop(task_id, None)
    return Released(task_id=task_id, released=done, reason=reason)


class DirectionRecorded(BaseModel):
    intervention_id: int
    project: str
    file: str


def record_direction(
    engine: Engine,
    direction: str,
    scope: str | None = None,
    *,
    actor: str,
    session_ref: str | None = None,
    project: str | None = None,
    domains: Path | None = None,
) -> DirectionRecorded:
    """An `ops.intervention` of kind `direction` and an entry appended to the pack's
    `directions.md`, outside the guideline's hash (D2 §10.11, D7 §8.2). `ci direct` calls it too."""
    from corpus_structure.core.db import repo
    from corpus_structure.core.payloads import InterventionRefs, InterventionTarget
    from corpus_structure.core.vocab import InterventionTargetKind
    from corpus_structure.orchestrate.commands import project_id
    from corpus_structure.schema.pack import DOMAINS

    if not direction.strip():
        raise ToolFailure("a direction has text")
    with engine.begin() as conn:
        pid, domain = project_id(conn, project)
        name = conn.execute(
            text("SELECT name FROM meta.project WHERE id = :p"), {"p": pid}
        ).scalar_one()
        schema = repo.registered_ids(conn, ["intervention_refs"]).get("intervention_refs")
        if schema is None:
            raise ToolFailure("the payload-schema registry has no intervention_refs row")
        target = InterventionTarget(kind=InterventionTargetKind.GUIDELINE, ref=scope or "all")
        iid = repo.record_intervention(
            conn,
            {
                "project_id": pid,
                "actor": actor,
                "session_ref": session_ref,
                "kind": InterventionKind.DIRECTION.value,
                "target": target.model_dump(mode="json"),
                "refs": InterventionRefs().model_dump(mode="json"),
                "payload_schema_id": schema,
                "body": direction,
            },
        )
        path = (domains or DOMAINS) / domain / "directions.md"
        stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ")
        entry = (
            f"- {stamp} ({actor}{', ' + scope if scope else ''}; intervention {iid}): {direction}\n"
        )
        new = not path.exists()
        with path.open("a", encoding="utf-8") as out:
            if new:
                out.write(
                    "# Directions\n\nOperator and session directions, newest last (D7 §8.2).\n\n"
                )
            out.write(entry)
    return DirectionRecorded(intervention_id=iid, project=str(name), file=str(path))
