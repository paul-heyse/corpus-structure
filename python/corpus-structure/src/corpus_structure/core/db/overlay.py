"""The physical overlay (model and projections §3.4; ADR-0020; D3 §1): every access-path choice.

The model declares no index or physical setting (TM §4); this module owns them, bound by name to
the generated tables of `_tables.py`. A missing table or column fails the import of `core.db`
(`OverlayBindingError`), as does a composite foreign key without a supporting index.

- **Indexes**: the queue's partial indexes, `task_unit`, the edge and identity indexes, the BM25
  partial index (`'english'::regconfig` and the `search_block` kinds of `_model.sql`), and the
  supporting index of every composite foreign key that no key or index starts with (coordinator
  decision 18; probe Q-4: without one, deleting a run's entities took 9.3 s, with it 32 ms).
  An index *supports* a composite foreign key when some leading run of its columns lies within the
  key's columns and includes every column the key does not share with its target (`info["shared"]`);
  a partial index qualifies when its predicate is `<column> IS NOT NULL`. The `kb.embedding` HNSW
  indexes wait on its dimension (S7, OPEN-D3-2) and on the phase 1 migration that creates it.
- **Views**, through SQLAlchemy 2.1's `CreateView`, carrying the run-cut predicate (D3 §8):
  `kb.run_observation`, `ops.run_measurement`, `kb.run_rendition`. Each view's `Table` has
  `is_view` (native) and `info["is_view"]`, so a migration environment's `include_object` can filter
  views on either (Alembic 1.20 has no view support; probe Q-3).
- **Before the tables**: the extension assertion, by version, from the record of expected
  extension versions `ops/postgresql/extensions.txt` (DA-018), then the four schemas.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import (
    DDL,
    Column,
    ForeignKeyConstraint,
    Index,
    MetaData,
    Table,
    UniqueConstraint,
    and_,
    cast,
    event,
    func,
    literal,
    or_,
    select,
    union_all,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import REGCONFIG
from sqlalchemy.sql.ddl import CreateView

from corpus_structure.core._model.sql import SEARCH_BLOCK
from corpus_structure.core.db import _tables, extensions
from corpus_structure.core.vocab import Stage, TaskStatus, TaskUnitType

SCHEMAS = ("meta", "ops", "kb", "eval")
EXTENSION_RECORD = extensions.EXTENSION_RECORD
# One BM25 partial index per text-search configuration (D3 §5); phase 0 indexes english.
TEXT_CONFIGS = ("english",)
# Tables the model declares that a later migration creates (`info["deferred"]` names why): migration
# 0001, `alembic check` and the catalog comparison leave them out.
DEFERRED = {
    "kb.embedding": "the phase 1 migration that adds M04; its halfvec dimension waits on S7 "
    "(OPEN-D3-2), and so do its HNSW indexes (D3 §5)",
}


def deployed(md: MetaData) -> list[Table]:
    """The tables (not views) that migration 0001 creates: every table but the deferred ones."""
    return [t for t in md.sorted_tables if not t.is_view and not t.info.get("deferred")]


class OverlayBindingError(LookupError):
    """The overlay names a table or column the generated `MetaData` lacks, or a composite foreign
    key has no supporting index."""


@dataclass(frozen=True)
class Overlay:
    """What `apply` added to the metadata."""

    indexes: tuple[Index, ...]
    views: tuple[Table, ...]


def _status(value: str) -> str:
    """A `TaskStatus` member by value, failing at import if the model lacks it."""
    return TaskStatus(value).value


def _unit(value: str) -> str:
    return TaskUnitType(value).value


# --- Bindings ----------------------------------------------------------------------------------


def _table(md: MetaData, name: str) -> Table:
    if name not in md.tables:
        raise OverlayBindingError(f"overlay: no table {name}")
    return md.tables[name]


class _Columns:
    """A table's columns by attribute, failing on a missing name."""

    def __init__(self, table: Table) -> None:
        self._table = table

    def __getattr__(self, name: str) -> Column[Any]:
        if name not in self._table.c:
            raise OverlayBindingError(f"overlay: no column {self._table.fullname}.{name}")
        return self._table.c[name]


def _cols(md: MetaData, name: str) -> _Columns:
    return _Columns(_table(md, name))


# --- Indexes -----------------------------------------------------------------------------------


def indexes(md: MetaData) -> list[Index]:
    seg, task = _cols(md, "kb.segment"), _cols(md, "ops.task")
    build, obs = _cols(md, "kb.rendition_build"), _cols(md, "kb.observation")
    ent, alias, claim = _cols(md, "kb.entity"), _cols(md, "kb.entity_alias"), _cols(md, "kb.claim")
    link, ref = _cols(md, "kb.claim_link"), _cols(md, "kb.claim_ref")
    eref, ident = _cols(md, "kb.claim_entity_ref"), _cols(md, "kb.entity_identity")
    meas, interv = _cols(md, "ops.measurement"), _cols(md, "ops.intervention")
    align, result = _cols(md, "eval.alignment"), _cols(md, "eval.result")
    out = [
        Index("segment_range", seg.rendition_id, seg.start_offset, seg.end_offset),
        Index("segment_kind", seg.rendition_id, seg.kind),
        *(
            Index(
                "segment_bm25" if config == "english" else f"segment_bm25_{config}",
                seg.text,
                postgresql_using="bm25",
                postgresql_with={"text_config": f"'{config}'"},
                postgresql_where=and_(
                    seg.kind.in_(SEARCH_BLOCK), seg.ts_config == cast(literal(config), REGCONFIG)
                ),
            )
            for config in TEXT_CONFIGS
        ),
        # the queue (store note L-S1): what workers claim, what expires, what the agent leases
        Index(
            "task_pending",
            task.run_id,
            task.stage,
            task.method_config_id,
            task.priority.desc(),
            task.id,
            postgresql_where=task.status == _status("pending"),
        ),
        Index("task_lease", task.lease_until, postgresql_where=task.status == _status("running")),
        Index(
            "task_agent",
            task.run_id,
            task.priority.desc(),
            task.id,
            postgresql_where=task.status == _status("awaiting_agent"),
        ),
        Index(
            "task_cache",
            task.method_config_id,
            task.input_hash,
            postgresql_where=and_(
                task.status.in_([_status("done"), _status("empty")]), task.unit_type != _unit("run")
            ),
        ),
        Index("task_run", task.run_id, task.stage),
        Index("task_unit", task.run_id, task.unit_key),
        Index("rendition_build_rendition", build.rendition_id),
        Index("observation_span", obs.span_id),
        Index("observation_segment", obs.segment_id, obs.kind),
        Index("entity_type", ent.run_id, ent.type),
        Index("entity_alias_lookup", alias.normalized),
        Index("claim_pred", claim.run_id, claim.predicate, claim.status),
        Index("claim_subject", claim.run_id, claim.subject_id),
        Index("claim_object", claim.run_id, claim.object_entity_id),
        Index("claim_statement", claim.run_id, claim.statement_id),
        Index("claim_link_to", link.to_claim_id),
        Index("claim_ref_target", ref.target_claim_id),
        Index("claim_entity_ref_entity", eref.entity_id, eref.role),
        Index("entity_identity_value", ident.slot, ident.value_entity_id),
        Index("measurement_lookup", meas.run_id, meas.metric, meas.scope_type, meas.scope_id),
        Index("measurement_task", meas.task_id, postgresql_where=meas.task_id.is_not(None)),
        Index("intervention_run", interv.run_id, interv.kind),
        Index("alignment_run", align.run_id),
        Index("result_run", result.run_id),
        # supporting indexes of composite foreign keys (decision 18; probe Q-4)
        Index(
            "entity_resolved_to",
            ent.run_id,
            ent.resolved_to_id,
            postgresql_where=ent.resolved_to_id.is_not(None),
        ),
        Index(
            "entity_kind", ent.schema_version_id, ent.kind, postgresql_where=ent.kind.is_not(None)
        ),
        Index(
            "claim_attribution",
            claim.run_id,
            claim.attribution_entity_id,
            postgresql_where=claim.attribution_entity_id.is_not(None),
        ),
        Index("claim_version_predicate", claim.schema_version_id, claim.predicate),
        Index("claim_version_modality", claim.schema_version_id, claim.modality),
    ]
    return out


# --- Views -------------------------------------------------------------------------------------


def _effective(t: Any, r: Any) -> Any:
    """A task's fate as of its run's cut (D3 §8): finished by the cut, or the run is unsealed."""
    done = [_status("done"), _status("empty"), _status("reused")]
    return and_(t.c.status.in_(done), or_(r.c.cut_at.is_(None), t.c.finished_at <= r.c.cut_at))


def views(md: MetaData) -> list[Table]:
    task, run = _table(md, "ops.task"), _table(md, "ops.run")
    obs, meas = _table(md, "kb.observation"), _table(md, "ops.measurement")
    build = _table(md, "kb.rendition_build")
    for table, names in (
        (
            task,
            (
                "run_id",
                "reused_task_id",
                "id",
                "status",
                "finished_at",
                "stage",
                "unit_type",
                "unit_id",
                "method_config_id",
            ),
        ),
        (run, ("id", "cut_at")),
        (obs, ("task_id",)),
        (meas, ("task_id", "run_id")),
        (build, ("document_id", "rendition_id", "method_config_id")),
    ):
        for name in names:
            getattr(_Columns(table), name)
    t, r = task.alias("t"), run.alias("r")
    o, m, b = obs.alias("o"), meas.alias("m"), build.alias("b")
    reused = func.coalesce(t.c.reused_task_id, t.c.id)
    run_observation = (
        select(t.c.run_id, *o.c)
        .select_from(t.join(r, r.c.id == t.c.run_id).join(o, o.c.task_id == reused))
        .where(_effective(t, r))
    )
    fields = (
        "id",
        "task_id",
        "iteration",
        "scope_type",
        "scope_id",
        "scope_key",
        "metric",
        "value",
        "detail",
    )
    for name in fields:
        getattr(_Columns(meas), name)
    run_measurement = union_all(
        select(t.c.run_id, *(m.c[f] for f in fields))
        .select_from(t.join(r, r.c.id == t.c.run_id).join(m, m.c.task_id == reused))
        .where(_effective(t, r)),
        select(m.c.run_id, *(m.c[f] for f in fields)).where(m.c.task_id.is_(None)),
    )
    run_rendition = (
        select(t.c.run_id, b.c.document_id, b.c.rendition_id)
        .select_from(
            t.join(
                b,
                and_(b.c.document_id == t.c.unit_id, b.c.method_config_id == t.c.method_config_id),
            )
        )
        .where(
            t.c.stage == Stage("ingest").value,
            t.c.unit_type == _unit("document"),
            t.c.status.in_([_status("done"), _status("reused")]),
        )
    )
    out = []
    for name, schema, query in (
        ("run_observation", "kb", run_observation),
        ("run_measurement", "ops", run_measurement),
        ("run_rendition", "kb", run_rendition),
    ):
        view = CreateView(query, name, schema=schema, metadata=md).table
        view.info["is_view"] = True
        out.append(view)
    return out


# --- Composite foreign keys and their supporting indexes ---------------------------------------


def _leading_runs(columns: list[str]) -> Iterable[set[str]]:
    for k in range(1, len(columns) + 1):
        yield set(columns[:k])


def _index_columns(table: Table) -> list[list[str]]:
    """The column lists of the table's keys and of its indexes usable for a foreign key lookup."""
    out = [[c.name for c in table.primary_key.columns]]
    out += [
        [col.name for col in c.columns]
        for c in table.constraints
        if isinstance(c, UniqueConstraint)
    ]
    for index in table.indexes:
        where = index.dialect_options["postgresql"].get("where")
        if where is not None:
            sql = str(where.compile(dialect=postgresql.dialect()))
            m = re.fullmatch(r"(?:\w+\.)*(\w+) IS NOT NULL", sql)
            if m is None or m.group(1) not in table.c:
                continue
        columns = [e for e in index.expressions if isinstance(e, Column)]
        if len(columns) == len(index.expressions):
            out.append([e.name for e in columns])
    return out


def unsupported_foreign_keys(md: MetaData) -> list[str]:
    """Each composite foreign key that no key or index supports (module doc)."""
    missing = []
    for table in md.tables.values():
        if table.is_view:
            continue
        candidates = _index_columns(table)
        for fk in table.constraints:
            if not isinstance(fk, ForeignKeyConstraint) or len(fk.columns) < 2:
                continue
            columns = set(fk.columns.keys())
            own = columns - set(fk.info.get("shared", ()))
            if not any(own <= run <= columns for cols in candidates for run in _leading_runs(cols)):
                missing.append(f"{table.fullname} ({', '.join(fk.columns.keys())})")
    return missing


# --- The extension assertion and the schemas ---------------------------------------------------


def expected_extensions(path: Path = EXTENSION_RECORD) -> dict[str, str]:
    """The record of expected extension versions (`core/db/extensions.py`)."""
    return extensions.expected_extensions(path)


def extension_assertion(expected: Mapping[str, str] | None = None) -> str:
    """The extension assertion's `DO` block (`core/db/extensions.py`)."""
    return extensions.assertion_sql(expected)


def _before_create(md: MetaData) -> None:
    def assert_extensions(target: Any, connection: Any, **kw: Any) -> None:
        # DDL formats with %, so the RAISE placeholder is escaped
        connection.execute(DDL(extension_assertion().replace("%", "%%")))

    event.listen(md, "before_create", assert_extensions)
    for schema in SCHEMAS:
        event.listen(md, "before_create", DDL(f"CREATE SCHEMA IF NOT EXISTS {schema}"))


# --- Applying the overlay ----------------------------------------------------------------------


def apply(md: MetaData) -> Overlay:
    """Bind the overlay to `md` (once per `MetaData`): indexes, views and the create events."""
    added = tuple(indexes(md))
    made = tuple(views(md))
    for name, reason in DEFERRED.items():
        _table(md, name).info["deferred"] = reason
    missing = unsupported_foreign_keys(md)
    if missing:
        raise OverlayBindingError(
            "overlay: composite foreign keys without a supporting index: " + "; ".join(missing)
        )
    _before_create(md)
    return Overlay(added, made)


OVERLAY = apply(_tables.metadata)
