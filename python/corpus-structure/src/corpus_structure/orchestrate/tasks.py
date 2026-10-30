"""Tasks, digests and reuse (orchestration §3.5; D6 §4; D3 §4, §8).

`create_tasks(conn, run_id, stage, config, method, units, …)` per unit:
1. a unit given a skip reason is a `skipped` task with that `SkipReason`, `finished_at` now and the
   sentinel input hash `skip:<reason>`; no digest is computed. A unit whose upstream task (of a
   method the step declares upstream) failed for its document or rendition gets
   `skipped(prerequisite_failed)` the same way;
2. otherwise the method's `input_digest` gives the `Digest`; `input_hash` is the SHA-256 of the
   canonical JSON of (method name, version, config hash, digest bytes) and `packet_hash` the
   digest's;
3. the tasks are inserted in one `INSERT … SELECT … FROM unnest(…) LEFT JOIN LATERAL (…)` over
   `task_cache`: a `done` or `empty` task of the same configuration and input hash makes the new
   task `reused`, pointing at it, with `finished_at`; otherwise it starts `pending`, or
   `awaiting_agent` for an agent-tier method.
A task of unit type `run`, or of a method in the run's `fresh`, is never reused. Skipped sentinels
can never match: `task_cache` covers only `done` and `empty`, and twins only `awaiting_agent`.
`unit_key` is the unit key for annotation units and the document key for document and rendition
tasks, so it is stable across renditions.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Connection, bindparam, text

from corpus_structure.core.canonical import digest
from corpus_structure.core.db.legacy_metadata import metadata
from corpus_structure.core.method import Method, ResolvedConfig, UnitView
from corpus_structure.core.vocab import MethodTier, SkipReason, Stage, TaskStatus, TaskUnitType

T = metadata.tables


def input_hash(method: Method[Any], config_hash: str, digest_bytes: bytes) -> str:
    """D6 §4's input hash (module doc)."""
    return digest([method.name, method.version, config_hash, digest_bytes.hex()])


def skip_hash(reason: SkipReason) -> str:
    return f"skip:{reason.value}"


@dataclass(frozen=True)
class CreatedTask:
    id: int
    unit_key: str | None
    status: TaskStatus
    reused_task_id: int | None


_CREATE = text("""
WITH u(unit_type, unit_id, unit_key, input_hash, packet_hash, initial, reason, ordinal) AS (
  SELECT * FROM unnest(CAST(:types AS text[]), CAST(:ids AS bigint[]), CAST(:keys AS text[]),
                       CAST(:hashes AS text[]), CAST(:packets AS text[]), CAST(:initials AS text[]),
                       CAST(:reasons AS text[]), CAST(:ordinals AS integer[])))
INSERT INTO ops.task (run_id, stage, unit_type, unit_id, unit_key, method_config_id,
                      trigger_rule_id, trigger_metrics, input_hash, packet_hash, status, reason,
                      reused_task_id, finished_at)
SELECT :run, :stage, u.unit_type, u.unit_id, u.unit_key, :config, :rule, :metrics, u.input_hash,
       u.packet_hash,
       CASE WHEN c.id IS NOT NULL THEN 'reused' ELSE u.initial END, u.reason, c.id,
       CASE WHEN c.id IS NOT NULL OR u.initial = 'skipped' THEN clock_timestamp() END
FROM u LEFT JOIN LATERAL (
  SELECT t.id FROM ops.task t
  WHERE :reuse AND u.initial <> 'skipped' AND t.method_config_id = :config
    AND t.input_hash = u.input_hash AND t.status IN ('done', 'empty') AND t.unit_type <> 'run'
  ORDER BY t.id LIMIT 1
) c ON true
ORDER BY u.ordinal
RETURNING id, unit_key, status, reused_task_id
""").bindparams(bindparam("metrics", type_=T["ops.task"].c.trigger_metrics.type))


def failed_upstream(conn: Connection, run_id: int, methods: Iterable[str]) -> set[tuple[str, int]]:
    """(unit type, unit id) of the run's failed tasks of the upstream methods."""
    names = sorted(set(methods))
    if not names:
        return set()
    rows = conn.execute(
        text(
            "SELECT t.unit_type, t.unit_id FROM ops.task t JOIN ops.method_config c ON c.id = "
            "t.method_config_id JOIN ops.method m ON m.id = c.method_id WHERE t.run_id = :r AND "
            "t.status = 'failed' AND m.name = ANY(:names) AND t.unit_id IS NOT NULL"
        ),
        {"r": run_id, "names": names},
    )
    return {(str(r[0]), int(r[1])) for r in rows}


def _unit_failed(unit: UnitView, failed: set[tuple[str, int]]) -> bool:
    keys = set()
    if unit.document_id is not None:
        keys.add((TaskUnitType.DOCUMENT.value, unit.document_id))
    if unit.rendition_id is not None:
        keys.add((TaskUnitType.RENDITION.value, unit.rendition_id))
    if unit.ref.unit_id is not None:
        keys.add((unit.ref.unit_type.value, unit.ref.unit_id))
    return bool(keys & failed)


def create_tasks(
    conn: Connection,
    run_id: int,
    stage: Stage,
    config: ResolvedConfig,
    method: Method[Any],
    units: Sequence[UnitView],
    *,
    skipped: Mapping[int, SkipReason] | None = None,
    upstream: Iterable[str] = (),
    fresh: bool = False,
    trigger_rule_id: int | None = None,
    trigger_metrics: Mapping[str, Any] | None = None,
) -> list[CreatedTask]:
    """The step's tasks for `units`, reused where a finished twin exists (module doc). `skipped`
    maps a unit's index in `units` to its skip reason."""
    if not units:
        return []
    if config.method_config_id is None:
        raise ValueError(f"{config.method}/{config.name} has no recorded configuration row")
    skipped = dict(skipped or {})
    failed = failed_upstream(conn, run_id, upstream)
    initial = (
        TaskStatus.AWAITING_AGENT if method.tier == MethodTier.AGENT else TaskStatus.PENDING
    ).value
    rows: dict[str, list[Any]] = {
        k: []
        for k in ("types", "ids", "keys", "hashes", "packets", "initials", "reasons", "ordinals")
    }
    for i, unit in enumerate(units):
        reason = skipped.get(i)
        if reason is None and _unit_failed(unit, failed):
            reason = SkipReason.PREREQUISITE_FAILED
        if reason is not None:
            hash_, packet, status = skip_hash(reason), None, TaskStatus.SKIPPED.value
        else:
            d = method.input_digest(unit, config.config)
            hash_, packet, status = (
                input_hash(method, config.config_hash, d.bytes),
                d.packet_hash,
                initial,
            )
        rows["types"].append(unit.ref.unit_type.value)
        rows["ids"].append(unit.ref.unit_id)
        rows["keys"].append(unit.ref.unit_key)
        rows["hashes"].append(hash_)
        rows["packets"].append(packet)
        rows["initials"].append(status)
        rows["reasons"].append(reason.value if reason is not None else None)
        rows["ordinals"].append(i)
    reuse = not fresh and method.unit_type != TaskUnitType.RUN
    result = conn.execute(
        _CREATE,
        {
            **rows,
            "run": run_id,
            "stage": stage.value,
            "config": config.method_config_id,
            "rule": trigger_rule_id,
            "metrics": dict(trigger_metrics or {}),
            "reuse": reuse,
        },
    )
    return [
        CreatedTask(int(r.id), r.unit_key, TaskStatus(r.status), r.reused_task_id) for r in result
    ]
