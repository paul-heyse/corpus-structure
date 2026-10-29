"""Runs (orchestration §3.4; D3 §4; D6 §2; coordinator decisions 16, 26).

**Creation.** `create_run` resolves every named configuration against the run's schema version and
records the rows (§3.2), checks every source profile a configuration names against the schema
version (the run-start profile check, DA-010: an unknown kind refuses the run before any task
exists), resolves the options, and inserts the run in one `INSERT … SELECT` that reads the project's
`promoted_run_id` into `reference_run_id` in the same statement. The insert records the model
revision, schema version, key scheme, guideline and policy versions, `corpus_hash` and the resolved
options; nothing here updates any of them afterwards.

**Options** (`RunOptions`, a frozen plain model). Each is resolved once, in this order: the explicit
option; a setting, only for the result-neutral `gpu_mode` (`Settings.gpu.mode`, when set); the
model's default. The stored options are complete, so re-reading them never consults the
environment. `agent_mode` defaults to `wait` for a `slice` run and `complete` otherwise; no setting
supplies it.

**`corpus_hash`** is the SHA-256 of the canonical JSON of the sorted (document key, content hash)
pairs of the run's corpus and the run's ingest configuration hashes (the configurations of
`ingest`-family methods), so it is computable at insert.

**Status.** Transitions are conditional updates (`WHERE status = :from`); an illegal one raises
`IllegalTransition`. `finish_run` seals and finishes a run without a final pass (`ingest`, a settled
`golden` run) in one short transaction, so the cut rule holds for every kind. `cancel_run` cancels
the run and its open tasks (`run_cancelled`).

**Liveness.** `ci run` holds `pg_advisory_lock(LIVENESS, run_id)` on one dedicated autocommit
connection for the run's life (`Liveness`); a session-level lock is released when the session ends,
however it ends. A run in `running`, `awaiting_agent` or `consolidating` whose lock no session
holds is orphaned (`pg_locks`: advisory, in this database, `classid` the namespace, `objid` the run,
`objsubid` 2; `pg_locks` lists every database's locks, and another database's run ids collide).
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
from pydantic import BaseModel
from sqlalchemy import Connection, bindparam, select, text

from corpus_structure.core._model.revision import KEY_SCHEME
from corpus_structure.core.canonical import digest
from corpus_structure.core.db import metadata
from corpus_structure.core.options import RunOptions
from corpus_structure.core.vocab import (
    AgentMode,
    AgentReuse,
    GpuMode,
    MethodFamily,
    RunKind,
    RunStatus,
    SkipReason,
    TaskStatus,
)
from corpus_structure.orchestrate.project import PackVersions
from corpus_structure.orchestrate.registry import MethodRegistry, artifact_hashes

T = metadata.tables
LIVENESS = 0x63735255  # the advisory-lock namespace of run liveness ("csRU")
REFUSED_KINDS = frozenset({RunKind.EXPERIMENT, RunKind.RESCORE})
OPEN_TASKS = (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.AWAITING_AGENT)
LIVE_STATUSES = (RunStatus.RUNNING, RunStatus.AWAITING_AGENT, RunStatus.CONSOLIDATING)


class RunError(ValueError):
    """A run that cannot be created or moved as asked."""


class ProfileRefused(RunError):
    """A source profile names a kind outside the run's schema version (DA-010)."""

    def __init__(self, issues: Sequence[tuple[str, str, str, str]]) -> None:
        self.issues = list(issues)  # (profile, code, field, value)
        super().__init__(
            "; ".join(
                f"source profile {p}: {field} {value!r}: {code}"
                for p, code, field, value in self.issues
            )
        )


class IllegalTransition(RunError):
    pass


class OptionsReport(BaseModel):
    """Every option as resolved, with where it came from (`option`, `setting` or `default`)."""

    options: RunOptions
    sources: dict[str, str]


def resolve_options(
    kind: RunKind,
    *,
    corpus: Any,
    explicit: Mapping[str, Any] | None = None,
    settings: Any = None,
    configs: Mapping[str, str] | None = None,
) -> OptionsReport:
    """The run's options by the precedence of the module doc."""
    explicit = {k: v for k, v in (explicit or {}).items() if v is not None}
    sources: dict[str, str] = {}

    def pick(name: str, default: Any, setting: Any = None) -> Any:
        if name in explicit:
            sources[name] = "option"
            return explicit[name]
        if setting is not None:
            sources[name] = "setting"
            return setting
        sources[name] = "default"
        return default

    gpu_setting = None
    if settings is not None and "mode" in settings.gpu.model_fields_set:
        gpu_setting = settings.gpu.mode
    options = RunOptions(
        agent_mode=pick(
            "agent_mode", AgentMode.WAIT if kind == RunKind.SLICE else AgentMode.COMPLETE
        ),
        agent_reuse=pick("agent_reuse", AgentReuse.FULL),
        gpu_mode=pick("gpu_mode", GpuMode.AUTO, gpu_setting),
        corpus=corpus,
        scope=pick("scope", None),
        fresh=tuple(pick("fresh", ())),
        configs=dict(configs or {}),
        method_configs=dict(pick("method_configs", {})),
    )
    sources |= {"corpus": "option", "configs": "resolved"}
    return OptionsReport(options=options, sources=sources)


def code_commit(repo: Path | None = None) -> str:
    """`git rev-parse HEAD`, with `+dirty` when the tree has changes; `unknown` outside Git."""
    cwd = repo or Path(__file__).resolve().parents[4]
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except OSError, subprocess.CalledProcessError:
        return "unknown"
    return f"{head}+dirty" if dirty else head


def corpus_hash(documents: Iterable[tuple[str, str]], ingest_configs: Iterable[str]) -> str:
    """The run's corpus hash (module doc)."""
    return digest(
        {
            "documents": sorted([list(d) for d in documents]),
            "ingest_configs": sorted(set(ingest_configs)),
        }
    )


@dataclass(frozen=True)
class SchemaVocabulary:
    """The run's schema version as the profile check reads it."""

    statement_kinds: frozenset[str]
    predicates: frozenset[str]


def schema_vocabulary(conn: Connection, schema_version_id: int) -> SchemaVocabulary:
    kinds = conn.execute(
        select(T["meta.statement_kind"].c.value).where(
            T["meta.statement_kind"].c.schema_version_id == schema_version_id
        )
    ).scalars()
    slots = T["meta.schema_slot"]
    predicates = conn.execute(
        select(slots.c.name).where(
            slots.c.schema_version_id == schema_version_id, slots.c.role == "predicate"
        )
    ).scalars()
    return SchemaVocabulary(frozenset(kinds), frozenset(predicates))


def check_profiles(conn: Connection, registry: MethodRegistry, schema_version_id: int) -> None:
    """Refuse when a source profile any configuration names lacks a kind (module doc)."""
    from corpus_structure.ingest.profile import SOURCES_DIR, check_profile, load_profile

    vocabulary = schema_vocabulary(conn, schema_version_id)
    issues, seen = [], set()
    for method, name in registry.named():
        for _, profile_name in registry.profiles(method, name):
            if profile_name in seen:
                continue
            seen.add(profile_name)
            profile = load_profile(profile_name, registry.sources or SOURCES_DIR)
            issues += [
                (profile_name, i.code, i.field, i.name) for i in check_profile(profile, vocabulary)
            ]
    if issues:
        raise ProfileRefused(issues)


@dataclass(frozen=True)
class CreatedRun:
    id: int
    options: OptionsReport
    configs: Mapping[str, Any]  # "<method>/<name>" -> ResolvedConfig with its row id


_INSERT = text("""
INSERT INTO ops.run (project_id, kind, phase, options, debug_slice_id, corpus_hash,
                     model_revision_id, schema_version_id, key_scheme, guideline_version_id,
                     policy_version_id, code_commit, parent_run_id, reference_run_id, status)
SELECT p.id, :kind, :phase, :options, :debug_slice, :corpus_hash, :model_revision,
       :schema_version, :key_scheme, :guideline_version, :policy_version, :code_commit,
       :parent_run, p.promoted_run_id, 'created'
FROM meta.project p WHERE p.id = :project
RETURNING id
""").bindparams(bindparam("options", type_=T["ops.run"].c.options.type))


def create_run(
    conn: Connection,
    *,
    project_id: int,
    kind: RunKind,
    versions: PackVersions,
    registry: MethodRegistry,
    documents: Sequence[tuple[str, str]],
    corpus: Any = None,
    phase: int = 0,
    explicit: Mapping[str, Any] | None = None,
    settings: Any = None,
    parent_run_id: int | None = None,
    commit: str | None = None,
) -> CreatedRun:
    """Create the run (module doc); `documents` are the corpus's (document key, content hash)."""
    if kind in REFUSED_KINDS:
        raise RunError(f"a {kind} run is refused in phase 0")
    resolved = registry.resolve_all(artifact_hashes(conn, versions.schema_version_id))
    check_profiles(conn, registry, versions.schema_version_id)
    recorded = registry.record(conn, resolved)
    configs = {k: v.config_hash for k, v in recorded.items()}
    unknown = sorted(
        set(m for m in (explicit or {}).get("fresh") or ()) - {m.name for m in registry.methods()}
    )
    if unknown:
        raise RunError(f"--fresh names unregistered methods {unknown}")
    report = resolve_options(
        kind,
        corpus=corpus or {"documents": sorted(d for d, _ in documents)},
        explicit=explicit,
        settings=settings,
        configs=configs,
    )
    ingest = [
        rc.config_hash
        for rc in recorded.values()
        if registry.method(rc.method).family == MethodFamily.INGEST
    ]
    run_id = conn.execute(
        _INSERT,
        {
            "project": project_id,
            "kind": kind.value,
            "phase": phase,
            "options": report.options.model_dump(mode="json"),
            "debug_slice": None,
            "corpus_hash": corpus_hash(documents, ingest),
            "model_revision": versions.model_revision_id,
            "schema_version": versions.schema_version_id,
            "key_scheme": KEY_SCHEME,
            "guideline_version": versions.guideline_version_id,
            "policy_version": versions.policy_version_id,
            "code_commit": commit or code_commit(),
            "parent_run": parent_run_id,
        },
    ).scalar_one()
    return CreatedRun(int(run_id), report, recorded)


def stored_options(conn: Connection, run_id: int) -> RunOptions:
    """A run's options as stored: no environment is read."""
    raw = conn.execute(
        select(T["ops.run"].c.options).where(T["ops.run"].c.id == run_id)
    ).scalar_one()
    return RunOptions.model_validate(raw)


def transition(conn: Connection, run_id: int, from_: Iterable[RunStatus], to: RunStatus) -> None:
    """Move the run from one of `from_` to `to`, or raise."""
    allowed = [s.value for s in from_]
    done = conn.execute(
        text(
            "UPDATE ops.run SET status = :to, started_at = coalesce(started_at, "
            "CASE WHEN :to = 'running' THEN clock_timestamp() END) "
            "WHERE id = :r AND status = ANY(:from)"
        ),
        {"to": to.value, "r": run_id, "from": allowed},
    )
    if done.rowcount != 1:
        current = conn.execute(text("SELECT status FROM ops.run WHERE id = :r"), {"r": run_id})
        raise IllegalTransition(
            f"run {run_id} is {current.scalar()}, not one of {allowed}: cannot become {to.value}"
        )


def finish_run(conn: Connection, run_id: int) -> None:
    """Seal and finish a run without a final pass in one transaction (module doc)."""
    conn.execute(text("SELECT 1 FROM ops.run WHERE id = :r FOR NO KEY UPDATE"), {"r": run_id})
    done = conn.execute(
        text(
            "UPDATE ops.run SET cut_at = coalesce(cut_at, clock_timestamp()), status = 'finished', "
            "finished_at = clock_timestamp() WHERE id = :r AND status IN ('created', 'running', "
            "'awaiting_agent')"
        ),
        {"r": run_id},
    )
    if done.rowcount != 1:
        raise IllegalTransition(f"run {run_id} cannot be finished from its status")


def fail_run(conn: Connection, run_id: int, note: str) -> None:
    conn.execute(
        text(
            "UPDATE ops.run SET status = 'failed', finished_at = clock_timestamp(), "
            "notes = coalesce(notes || E'\\n', '') || :n WHERE id = :r AND status NOT IN "
            "('finished', 'failed', 'cancelled')"
        ),
        {"r": run_id, "n": note},
    )


def cancel_run(conn: Connection, run_id: int) -> int:
    """Cancel the run and its open tasks (`run_cancelled`); the tasks cancelled."""
    done = conn.execute(
        text(
            "UPDATE ops.run SET status = 'cancelled', finished_at = "
            "clock_timestamp() WHERE id = :r AND status NOT IN ('finished', "
            "'failed', 'cancelled')"
        ),
        {"r": run_id},
    )
    if done.rowcount != 1:
        raise IllegalTransition(f"run {run_id} is already over")
    tasks = conn.execute(
        text(
            "UPDATE ops.task SET status = 'cancelled', reason = :reason, lease_until = NULL, "
            "finished_at = clock_timestamp() WHERE run_id = :r AND status = ANY(:open)"
        ),
        {
            "r": run_id,
            "reason": SkipReason.RUN_CANCELLED.value,
            "open": [s.value for s in OPEN_TASKS],
        },
    )
    return int(tasks.rowcount)


class Liveness:
    """The run's liveness lock, on its own autocommit connection outside any pool (module doc)."""

    def __init__(self, url: str, run_id: int) -> None:
        self.conn = psycopg.connect(url, autocommit=True)
        self.conn.execute("SELECT pg_advisory_lock(%s, %s)", (LIVENESS, run_id))
        self.run_id = run_id

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> Liveness:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def orphaned(conn: Connection) -> list[int]:
    """The live runs whose liveness lock no session holds."""
    rows = conn.execute(
        text(
            "SELECT r.id FROM ops.run r WHERE r.status = ANY(:live) AND NOT EXISTS (SELECT 1 FROM "
            "pg_locks l WHERE l.locktype = 'advisory' AND l.database = (SELECT oid FROM "
            "pg_database WHERE datname = current_database()) AND l.classid = :ns AND "
            "l.objid = r.id AND l.objsubid = 2 AND l.granted) ORDER BY r.id"
        ),
        {"live": [s.value for s in LIVE_STATUSES], "ns": LIVENESS},
    )
    return [int(r[0]) for r in rows]
