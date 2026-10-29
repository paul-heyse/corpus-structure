"""Fates and their reader (orchestration §3.9; D6 §1; D3 §8; RC10).

Every eligible unit has a task (base steps: one per unit `select` returns; the propose stage: one
per matched candidate, or a `skipped` one; `prerequisite_failed` skips). A sealed run's fates are
its tasks as of `ops.run.cut_at`: a task whose `finished_at` is later, or null, is **unresolved**
for that run, whatever its status now. The cut is the one comparison `t.finished_at <= r.cut_at`,
the same as the run views', the coverage query's and the pool loader's. An unsealed run reads its
current statuses (progress), an open one counting as unresolved.

Run-level tasks (the passes, M19, `evaluate.score`) are outside the fate rule: they finish after the
cut by construction, and their readers select them through the seal's recorded final M19 task.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Connection, text

from corpus_structure.core.vocab import MethodTier, SkipReason, Stage

UNRESOLVED = "unresolved"
OPEN = ("pending", "running", "awaiting_agent")


@dataclass(frozen=True)
class Fate:
    task_id: int
    unit_key: str | None
    document_id: int | None
    fate: str  # a TaskStatus member, or `unresolved`
    reason: SkipReason | None


_FATES = """
SELECT t.id, t.unit_key,
       CASE t.unit_type
         WHEN 'document' THEN t.unit_id
         WHEN 'rendition' THEN (SELECT document_id FROM kb.rendition WHERE id = t.unit_id)
         WHEN 'segment' THEN (SELECT r.document_id FROM kb.segment s
                              JOIN kb.rendition r ON r.id = s.rendition_id WHERE s.id = t.unit_id)
       END AS document_id,
       CASE WHEN run.cut_at IS NOT NULL AND (t.finished_at IS NULL OR t.finished_at > run.cut_at)
              THEN 'unresolved'
            WHEN run.cut_at IS NULL AND t.status = ANY(:open) THEN 'unresolved'
            ELSE t.status END AS fate,
       CASE WHEN run.cut_at IS NULL OR t.finished_at <= run.cut_at THEN t.reason END AS reason
FROM ops.task t JOIN ops.run run ON run.id = t.run_id
WHERE t.run_id = :run AND t.unit_type <> 'run' {filters}
ORDER BY t.id
"""


def fates(
    conn: Connection,
    run_id: int,
    *,
    stage: Stage | None = Stage.PROPOSE,
    documents: Sequence[int] | None = None,
    unit_keys: Sequence[str] | None = None,
    tier: MethodTier | None = None,
) -> list[Fate]:
    """The fates of the run's eligible units (module doc), optionally of one stage, some
    documents or some unit keys."""
    filters: list[str] = []
    params: dict[str, Any] = {"run": run_id, "open": list(OPEN)}
    if stage is not None:
        filters.append("t.stage = :stage")
        params["stage"] = stage.value
    if tier is not None:
        filters.append(
            "t.method_config_id IN (SELECT id FROM ops.method_config WHERE tier = :tier)"
        )
        params["tier"] = tier.value
    if unit_keys is not None:
        filters.append("t.unit_key = ANY(:keys)")
        params["keys"] = list(unit_keys)
    rows = conn.execute(text(_FATES.format(filters="".join(f" AND {f}" for f in filters))), params)
    out = [
        Fate(
            int(r.id),
            r.unit_key,
            r.document_id,
            str(r.fate),
            SkipReason(r.reason) if r.reason else None,
        )
        for r in rows
    ]
    if documents is not None:
        wanted = set(documents)
        out = [f for f in out if f.document_id in wanted]
    return out


def unresolved(
    conn: Connection, run_id: int, stage: Stage | None = None, tier: MethodTier | None = None
) -> int:
    """How many of the run's eligible units are unresolved as of its cut (or open, unsealed)."""
    return sum(1 for f in fates(conn, run_id, stage=stage, tier=tier) if f.fate == UNRESOLVED)
