"""`run_pass` against PostgreSQL (P0-C-1; consolidation §3.1, §3.6, §6): `pool_run` is a sealed run
with a production rendition of the vendored Normal page written through the repository, an ingest
task so `kb.run_rendition` resolves, and `claim_proposal` observations of `fixtures/s0` batches
located by A0's `parse` under synthetic propose tasks, one of them finished after the cut."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml
from sqlalchemy import text

from corpus_structure.consolidate import run_pass
from corpus_structure.consolidate.pass_ import ConsolidateConfig
from corpus_structure.core.db import repo

REPO = Path(__file__).resolve().parents[4]
ROOT = "siegrist_random/random"
PAGE = "special/Normal.html"
CUT = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
BEFORE, AFTER = ("T2", "T3", "U6"), ("U5",)


def config() -> ConsolidateConfig:
    raw = yaml.safe_load((REPO / "domains/statistics/methods.yaml").read_text(encoding="utf-8"))
    return ConsolidateConfig(aliases=raw["aliases"], math=raw["math"])


def sql(conn: Any, query: str, **params: Any) -> Any:
    return conn.execute(text(query), params)


def seal(ns: SimpleNamespace) -> None:
    with ns.engine.begin() as conn:
        sql(
            conn,
            "UPDATE ops.run SET cut_at = :c, cut_m19_task_id = :m, status = 'consolidating' "
            "WHERE id = :r",
            c=CUT,
            m=ns.m19,
            r=ns.run,
        )


CLAIMS = (
    "SELECT key, predicate, status, modality, qualifiers::text, object_value::text, "
    "completeness::text FROM kb.claim WHERE run_id = :r"
)
ENTITIES = "SELECT key, type, label, kind FROM kb.entity WHERE run_id = :r"
SUPPORTS = (
    "SELECT DISTINCT o.task_id FROM kb.claim_support s JOIN kb.claim c ON c.id = s.claim_id "
    "JOIN kb.observation o ON o.id = s.observation_id WHERE c.run_id = :r"
)


def rows(ns: SimpleNamespace) -> dict[str, Any]:
    with ns.engine.connect() as conn:
        count = "SELECT count(*) FROM {} WHERE run_id = :r"
        return {
            "claims": sorted(map(tuple, sql(conn, CLAIMS, r=ns.run))),
            "entities": sorted(map(tuple, sql(conn, ENTITIES, r=ns.run))),
            "claim_ref": sql(conn, count.format("kb.claim_ref"), r=ns.run).scalar(),
            "entity_ref": sql(conn, count.format("kb.claim_entity_ref"), r=ns.run).scalar(),
            "supports": sorted(r[0] for r in sql(conn, SUPPORTS, r=ns.run)),
        }


def test_the_passes_write_the_run_as_of_its_cut(pool_run: SimpleNamespace) -> None:
    ns = pool_run
    with ns.engine.begin() as conn:
        report = run_pass(conn, ns.run, "assemble", None)
    assembled = rows(ns)
    assert assembled["claims"] and {c[2] for c in assembled["claims"]} <= {
        "candidate",
        "unsupported",
    }
    assert (assembled["claim_ref"], assembled["entity_ref"]) == (0, 0)  # edges at finalize only
    assert set(report.consumed) == set(ns.tasks.values())  # unsealed: every effective proposal
    seal(ns)
    with ns.engine.begin() as conn:
        report = run_pass(conn, ns.run, "finalize", ns.m19)
    final = rows(ns)
    after = {ns.tasks[u] for u in AFTER}
    assert set(report.consumed) == {ns.tasks[u] for u in BEFORE}
    assert not set(final["supports"]) & after  # the completion after the cut is absent
    assert {c[2] for c in final["claims"]} <= {"accepted", "rejected", "ambiguous", "unsupported"}
    assert final["claim_ref"] > 0 and final["entity_ref"] > 0
    assert report.rule_counts
    with ns.engine.begin() as conn:  # a repeated pass (its own M19 task) rebuilds the same rows
        again = run_pass(conn, ns.run, "finalize", ns.m19_again)
    assert rows(ns) == final and again.counts == report.counts
    with ns.engine.connect() as conn:
        keys = {r[0] for r in final["claims"]}
        found = [
            json.loads(r[0])["claim_key"] if isinstance(r[0], str) else r[0]["claim_key"]
            for r in sql(conn, "SELECT payload FROM kb.observation WHERE task_id = :t", t=ns.m19)
        ]
        assert set(found) <= keys


def test_the_final_pass_needs_the_seal(pool_run: SimpleNamespace) -> None:
    with pool_run.engine.begin() as conn, pytest.raises(ValueError, match="seal"):
        run_pass(conn, pool_run.run, "finalize", pool_run.m19)


def test_external_reference_descriptor_survives_materialization(pool_run: SimpleNamespace) -> None:
    from corpus_structure.core.batch import StoredDescriptor

    ns = pool_run
    seal(ns)
    with ns.engine.begin() as conn:
        run_pass(conn, ns.run, "finalize", ns.m19)
    with ns.engine.connect() as conn:
        row = sql(
            conn,
            "SELECT e.reference_descriptor, e.label, s.rendition_id "
            "FROM kb.entity e JOIN kb.segment s ON s.id = e.scope_segment_id "
            "WHERE e.run_id = :r AND e.type = 'core:ExternalReference'",
            r=ns.run,
        ).one()
        descriptor = StoredDescriptor.model_validate(row[0])
        content = repo.read_rendition(conn, row[2])
        assert content.canonical_text[descriptor.start : descriptor.end] == row[1]
        assert (
            sql(
                conn,
                "SELECT count(*) FROM kb.entity WHERE run_id = :r "
                "AND type <> 'core:ExternalReference' AND reference_descriptor IS NOT NULL",
                r=ns.run,
            ).scalar_one()
            == 0
        )
