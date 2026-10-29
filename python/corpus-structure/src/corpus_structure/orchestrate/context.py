"""The run a method works in (orchestration §3.1; P0CL-02): `RunView` and the database `Reader`.

`run_view(conn, run_id)` reads the run row (identity, versions, key scheme, stored options) and
binds a `DbReader` to it. The reader returns what a method reads, already scoped to the run: its
documents and renditions through `kb.run_rendition`, rendition content rebuilt from the stored
segments, the run's effective observations through `kb.run_observation` (reuse and, once sealed,
the cut) and method-written measurements through `ops.run_measurement`, compiled artifacts by hash,
the guideline body, and the connection for method-specific queries. One implementation keeps every
method from re-deriving those joins.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Connection, text

from corpus_structure.core.db import repo
from corpus_structure.core.evidence import RenditionContent
from corpus_structure.core.method import (
    MeasurementView,
    ObservationView,
    RunRendition,
    RunView,
    payload_hash,
)
from corpus_structure.core.vocab import (
    MeasurementScope,
    ObservationKind,
    ObservationOutcome,
    RunKind,
)


class DbReader:
    """The `Reader` over the database, scoped to one run (module doc)."""

    def __init__(self, conn: Connection, run_id: int) -> None:
        self.conn = conn
        self.run_id = run_id

    def renditions(self) -> Sequence[RunRendition]:
        rows = self.conn.execute(
            text(
                "SELECT DISTINCT rr.document_id, d.key, rr.rendition_id, r.key AS rkey "
                "FROM kb.run_rendition rr JOIN kb.document d ON d.id = rr.document_id "
                "JOIN kb.rendition r ON r.id = rr.rendition_id WHERE rr.run_id = :run "
                "ORDER BY d.key"
            ),
            {"run": self.run_id},
        )
        return [RunRendition(int(r[0]), str(r[1]), int(r[2]), str(r[3])) for r in rows]

    def content(self, rendition_id: int) -> RenditionContent:
        return repo.read_rendition(self.conn, rendition_id)

    def segments(self, rendition_id: int) -> Mapping[str, int]:
        return repo.segment_ids(self.conn, rendition_id)

    def observations(
        self, rendition_id: int, method: str, kind: ObservationKind
    ) -> Sequence[ObservationView]:
        rows = self.conn.execute(
            text(
                "SELECT o.id, o.task_id, o.kind, o.rendition_id, o.segment_id, o.span_id, "
                "o.payload, "
                "o.payload_schema_id, o.score, o.outcome FROM kb.run_observation o "
                "JOIN ops.task t ON t.id = o.task_id JOIN ops.method_config c ON c.id = "
                "t.method_config_id JOIN ops.method m ON m.id = c.method_id "
                "WHERE o.run_id = :run AND o.rendition_id = :ren AND m.name = :method AND "
                "o.kind = :kind ORDER BY o.task_id, o.ordinal"
            ),
            {"run": self.run_id, "ren": rendition_id, "method": method, "kind": kind.value},
        )
        return [
            ObservationView(
                int(r.id),
                int(r.task_id),
                ObservationKind(r.kind),
                r.rendition_id,
                r.segment_id,
                r.span_id,
                r.payload,
                int(r.payload_schema_id),
                payload_hash(r.payload),
                r.score,
                ObservationOutcome(r.outcome),
            )
            for r in rows
        ]

    def measurements(self, method: str, metric: str) -> Sequence[MeasurementView]:
        rows = self.conn.execute(
            text(
                "SELECT rm.id, rm.task_id, rm.metric, rm.scope_type, rm.scope_id, rm.scope_key, "
                "rm.value, rm.detail FROM ops.run_measurement rm "
                "JOIN ops.task t ON t.id = rm.task_id "
                "JOIN ops.method_config c ON c.id = t.method_config_id JOIN ops.method m ON m.id = "
                "c.method_id WHERE rm.run_id = :run AND m.name = :method AND rm.metric = :metric "
                "ORDER BY rm.id"
            ),
            {"run": self.run_id, "method": method, "metric": metric},
        )
        return [
            MeasurementView(
                int(r.id),
                int(r.task_id),
                r.metric,
                MeasurementScope(r.scope_type),
                r.scope_id,
                r.scope_key,
                r.value,
                r.detail,
            )
            for r in rows
        ]

    def artifact(self, artifact_hash: str) -> bytes:
        body = self.conn.execute(
            text(
                "SELECT a.body::text FROM meta.compiled_artifact a JOIN ops.run r ON "
                "r.schema_version_id = a.schema_version_id "
                "WHERE r.id = :run AND a.hash = :h LIMIT 1"
            ),
            {"run": self.run_id, "h": artifact_hash},
        ).scalar()
        if body is None:
            raise LookupError(f"no artifact {artifact_hash[:12]} in the run's schema version")
        return str(body).encode("utf-8")

    def guideline(self) -> str:
        body = self.conn.execute(
            text(
                "SELECT g.body FROM ops.run r JOIN meta.guideline_version g ON g.id = "
                "r.guideline_version_id WHERE r.id = :run"
            ),
            {"run": self.run_id},
        ).scalar()
        if body is None:
            raise LookupError(f"run {self.run_id} has no guideline version")
        return str(body)

    @contextmanager
    def connection(self) -> Iterator[Any]:
        yield self.conn


def run_view(conn: Connection, run_id: int) -> RunView:
    """The run's view with a database reader (module doc)."""
    row = conn.execute(
        text(
            "SELECT r.id, r.kind, r.phase, r.reference_run_id, m.content_hash, "
            "r.schema_version_id, "
            "r.guideline_version_id, r.policy_version_id, r.key_scheme, r.options FROM ops.run r "
            "JOIN meta.model_revision m ON m.id = r.model_revision_id WHERE r.id = :r"
        ),
        {"r": run_id},
    ).one()
    return RunView(
        int(row.id),
        RunKind(row.kind),
        int(row.phase),
        row.reference_run_id,
        str(row.content_hash),
        int(row.schema_version_id),
        row.guideline_version_id,
        row.policy_version_id,
        int(row.key_scheme),
        row.options,
        DbReader(conn, run_id),
    )
