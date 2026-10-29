"""`propose_claims`: the submission pipeline and its one transaction (agent interface §3.6; D8 §2.1;
D4 M24, §4.3; D6 §3.1).

Outside any transaction:
1. **Envelope.** This instance holds the task's lease and served every part of its packet (the
   frame attached is the one served); `schema_hash`, when given, equals the run's `schema` part;
   `unit_ref` equals the task's unit key (else one issue at `unit_ref` and nothing is parsed).
2. **Checks** (`validate.check_authored`) against the run's schema version and the packet's
   sentence ids; the rejected items and those depending on them are set aside.
3. **Parse** (A0) of the accepted items on the task's rendition, with the frame built from the
   served packet's sentence map for the ids the batch cites.
4. **Stored checks and M19 at the batch site** (`validate.check_stored`): rejected stored items,
   dropped dependencies, rule errors and `guideline:` warnings. No formula is parsed with the
   grammar (P0CL-14).

**Outcomes.** A submission is clean when nothing was rejected or dropped, every quote was located
exactly and no rule fired. A first unclean submission is held open: the completion primitive keeps
this result in `ops.task.error` and renews the lease (`task_open: true`). A clean first submission,
or a second one, completes the task: `done` with one `claim_proposal` observation (the accepted
items stored, the submission as authored with its served frame, the cascade and schema versions,
the rejected items, the rationale), or `empty` when a clean batch has no items. An all-rejected
second submission is `done`.

**The transaction**: the completion primitive first (fenced on `attempt`; it settles twins and sends
`NOTIFY`, delivered at commit), then the observation and an `ops.intervention` (kind `extract`,
actor `agent:<declared model>`, `session_ref` the instance id, `refs` the observation). A task no
longer open (twin settled, cancelled, leased again) writes nothing and the result says why; a
failure after the fence rolls everything back and the task stays leased.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ValidationError
from sqlalchemy import text

from corpus_structure.core import batch as B
from corpus_structure.core.db import repo
from corpus_structure.core.payloads import (
    ClaimProposalPayload,
    InterventionRefs,
    InterventionTarget,
    RejectedItem,
)
from corpus_structure.core.vocab import (
    InterventionKind,
    InterventionTargetKind,
    ObservationKind,
    TaskStatus,
)
from corpus_structure.intervene.service import (
    Session,
    TaskContext,
    ToolFailure,
    assembled,
    require_lease,
    run_parts,
    task_context,
)
from corpus_structure.methods.llm.parse import RenditionView, parse
from corpus_structure.orchestrate import agent
from corpus_structure.validate.runner import accepted_items, check_authored, check_stored


class ItemIssue(BaseModel):
    path: str
    category: str
    code: str
    message: str


class QuoteIssue(BaseModel):
    path: str
    quote: str
    sentence: str | None
    outcome: Literal["coarse", "dropped"]
    code: str | None = None


class RuleFinding(BaseModel):
    rule: str
    severity: str
    claim: str
    message: str


class SubmissionResult(BaseModel):
    submission_disposition: (
        Literal["held", "completed_accepted", "completed_refused", "refused_context"] | None
    ) = None
    task_id: int
    status: Literal["held", "done", "empty", "not_open"]
    task_open: bool
    reason: str | None = None  # why a task is not open: twin_settled, cancelled, leased_again, …
    rejected: list[ItemIssue] = []
    quotes: list[QuoteIssue] = []
    dropped: list[ItemIssue] = []
    findings: list[RuleFinding] = []
    accepted: dict[str, int] = {}
    observation_id: int | None = None
    cascade_version: str | None = None

    @property
    def clean(self) -> bool:
        return not (self.rejected or self.quotes or self.dropped or self.findings)


def _path(path: Any) -> str:
    out = ""
    for p in path:
        out += f"[{p}]" if isinstance(p, int) else (f".{p}" if out else str(p))
    return out


def _code(q: Any) -> str | None:
    """A quote's drop code, else its sentence's frame code."""
    code = q.dropped if q.dropped is not None else q.frame
    return None if code is None else str(code.value)


def _empty_authored(unit_key: str) -> dict[str, Any]:
    return {"unit_ref": unit_key}


class _Checked(BaseModel):
    """The pipeline's products before the transaction."""

    model_config = {"arbitrary_types_allowed": True}

    result: SubmissionResult
    payload: ClaimProposalPayload | None
    items: int


def check(
    session: Session,
    task: TaskContext,
    batch: Mapping[str, Any],
    schema_hash: str | None,
    rationale: str | None,
) -> _Checked:
    """Steps 1 to 4 of the module doc (no transaction)."""
    require_lease(session, task)
    with session._lock:
        served = session.served.get(task.id)
    packet = assembled(session, task)
    if served is None or served.attempt != task.attempt or served.packet.hash != packet.hash:
        raise ToolFailure(f"task {task.id}: read every part with read_unit before submitting")
    if not served.complete:
        missing = sorted(set(range(1, len(packet.parts) + 1)) - served.parts_read)
        raise ToolFailure(f"task {task.id}: parts {missing} were not read; read them first")
    parts = run_parts(session, task)
    if schema_hash is not None and schema_hash != parts["schema"].hash:
        raise ToolFailure(
            f"schema_hash {schema_hash[:12]} is not the run's ({parts['schema'].hash[:12]}); "
            "read the schema part again"
        )
    with session.engine.connect() as conn:
        compiled = session.compiled(conn, task.view.schema_version_id)
        content, page, segment = task.segment()
    result = SubmissionResult(task_id=task.id, status="held", task_open=True)
    raw = json.loads(json.dumps(batch))
    ids = [s.id for s in packet.sentences]
    if not isinstance(raw, dict) or raw.get("unit_ref") != task.unit_key:
        result.rejected.append(
            ItemIssue(
                path="unit_ref",
                category="envelope",
                code="unit_ref_mismatch",
                message=f"unit_ref must be the task's unit key {task.unit_key!r}",
            )
        )
        accepted: dict[str, Any] = _empty_authored(task.unit_key)
        rejected_items = [RejectedItem(item=raw, reason="unit_ref_mismatch")]
    else:
        report = check_authored(raw, ids, compiled)
        result.rejected += [
            ItemIssue(path=_path(i.path), category=i.category.value, code=i.code, message=i.message)
            for i in report.issues
        ]
        if any(len(i.path) < 2 for i in report.issues):  # the envelope itself is refused
            accepted = _empty_authored(task.unit_key)
            rejected_items = [RejectedItem(item=raw, reason=", ".join(sorted(report.codes())))]
        else:
            accepted, drops = accepted_items(raw, report)
            rejected_items = list(report.rejected())
            result.dropped += [
                ItemIssue(path=d.ref, category="dependency", code=d.code.value, message=d.message)
                for d in drops
            ]
    try:
        authored = B.AuthoredBatch.model_validate(accepted)
    except ValidationError as error:  # never expected after the checks; reported, not raised
        result.rejected.append(
            ItemIssue(path="", category="malformed", code="not_authored", message=str(error))
        )
        authored = B.AuthoredBatch.model_validate(_empty_authored(task.unit_key))
    frame = packet.frame(B.cited_sentences(authored))
    view = RenditionView(content, page, _rendition_key(session, task), task_macros(task, content))
    parsed = parse(view, authored, frame, dict(compiled.names.to_prefixed))
    result.cascade_version = parsed.report.cascade_version
    for q in parsed.report.quotes:
        if q.dropped is not None or q.coarse:
            result.quotes.append(
                QuoteIssue(
                    path=q.path,
                    quote=q.quote,
                    sentence=q.sentence,
                    outcome="dropped" if q.dropped is not None else "coarse",
                    code=_code(q),
                )
            )
    for p in parsed.report.problems:
        result.dropped.append(
            ItemIssue(path=p.path, category="parse", code=p.code.value, message=p.detail)
        )
    stored = check_stored(
        parsed.stored,
        compiled,
        canonical_text=content.canonical_text,
        unit_ranges=[(segment.start, segment.end)],
    )
    result.rejected += [
        ItemIssue(path=_path(i.path), category=i.category.value, code=i.code, message=i.message)
        for i in stored.report.issues
    ]
    rejected_items += list(stored.report.rejected())
    result.dropped += [
        ItemIssue(path=d.ref, category="dependency", code=d.code.value, message=d.message)
        for d in stored.drops
    ]
    if stored.rules is not None:
        result.findings += [
            RuleFinding(rule=f.rule, severity=f.severity, claim=f.claim, message=f.message)
            for f in stored.rules.findings
        ]
    kept = stored.batch
    if kept is None:  # the stored envelope was refused: nothing of it is kept
        kept = B.StoredBatch.model_validate(
            parse(
                view,
                B.AuthoredBatch.model_validate(_empty_authored(task.unit_key)),
                packet.frame(()),
                dict(compiled.names.to_prefixed),
            ).stored.model_dump(mode="json", by_alias=True)
        )
    sections = ("entities", "statements", "claims", "alternatives", "unsupported")
    result.accepted = {s: len(getattr(kept, s, ()) or ()) for s in sections}
    items = sum(result.accepted.values())
    try:
        as_authored = B.AuthoredBatch.model_validate(raw)
    except ValidationError:
        as_authored = authored
    # The compiled batch's subclasses declare pack qualifier fields. Serialize them before
    # crossing into the core envelope; its base-class serializer otherwise drops those fields.
    stored_batch = B.StoredBatch.model_validate(
        kept.model_dump(mode="json", by_alias=True, serialize_as_any=True)
    )
    payload = ClaimProposalPayload(
        batch=stored_batch,
        schema_version=compiled.schema_version,
        authored=as_authored,
        citation_frame=packet.frame(B.cited_sentences(as_authored)),
        cascade_version=parsed.report.cascade_version,
        **({"rationale": rationale} if rationale else {}),
        **({"rejected": tuple(rejected_items)} if rejected_items else {}),
    )
    return _Checked(result=result, payload=payload, items=items)


def _rendition_key(session: Session, task: TaskContext) -> str:
    with session.engine.connect() as conn:
        return str(
            conn.execute(
                text("SELECT key FROM kb.rendition WHERE id = :r"), {"r": task.unit.rendition_id}
            ).scalar_one()
        )


def task_macros(task: TaskContext, content: Any) -> dict[str, Any]:
    from corpus_structure.core import tex

    return dict(tex.effective_macros(content.macros, task.config.math.macro_table()))


def propose_claims(
    session: Session,
    task_id: int,
    batch: Mapping[str, Any],
    schema_hash: str | None = None,
    rationale: str | None = None,
) -> SubmissionResult:
    """The submission (module doc)."""
    with session.engine.connect() as conn:
        task = task_context(conn, task_id)
        if task.status in (TaskStatus.REUSED, TaskStatus.CANCELLED):
            reason = "twin_settled" if task.status == TaskStatus.REUSED else "cancelled"
            return SubmissionResult(
                task_id=task_id, status="not_open", task_open=False, reason=reason
            )
        checked = check(session, task, batch, schema_hash, rationale)
    result = checked.result
    clean = result.clean
    outcome = TaskStatus.EMPTY if clean and checked.items == 0 else TaskStatus.DONE
    try:
        with session.engine.begin() as conn:
            got = agent.complete_agent_task(
                conn,
                task.id,
                task.attempt,
                session.instance,
                clean=clean,
                outcome=outcome,
                first_result=result.model_dump(mode="json"),
            )
            if got == "held":
                result.status, result.task_open = "held", True
                return result
            result.status, result.task_open = outcome.value, False  # type: ignore[assignment]
            if outcome == TaskStatus.DONE:
                result.observation_id = _write(conn, session, task, checked)
    except agent.TaskNotOpen as error:
        with session._lock:
            session.served.pop(task_id, None)
        return SubmissionResult(
            task_id=task_id, status="not_open", task_open=False, reason=error.reason
        )
    with session._lock:
        session.served.pop(task_id, None)
    return result


def _write(conn: Any, session: Session, task: TaskContext, checked: _Checked) -> int:
    assert checked.payload is not None
    row = repo.ObservationRow(
        0,
        ObservationKind.CLAIM_PROPOSAL.value,
        checked.payload,
        rendition_id=task.unit.rendition_id,
        segment_id=task.unit_id,
    )
    repo.write_observations(conn, task.id, task.attempt, [row])
    observation = int(
        conn.execute(
            text("SELECT id FROM kb.observation WHERE task_id = :t AND ordinal = 0"),
            {"t": task.id},
        ).scalar_one()
    )
    schema = repo.registered_ids(conn, ["intervention_refs"])["intervention_refs"]
    repo.record_intervention(
        conn,
        {
            "project_id": task.project_id,
            "run_id": task.run_id,
            "task_id": task.id,
            "actor": f"agent:{task.config.model}",
            "session_ref": session.instance,
            "kind": InterventionKind.EXTRACT.value,
            "target": InterventionTarget(
                kind=InterventionTargetKind.UNIT, ref=task.unit_key
            ).model_dump(mode="json"),
            "refs": InterventionRefs(observations=(observation,)).model_dump(mode="json"),
            "payload_schema_id": schema,
            "rationale": checked.payload.rationale
            if isinstance(checked.payload.rationale, str)
            else None,
        },
    )
    return observation
