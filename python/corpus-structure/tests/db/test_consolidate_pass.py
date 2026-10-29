"""`run_pass` against PostgreSQL (P0-C-1; consolidation §3.1, §3.6, §6): `pool_run` is a sealed run
with a production rendition of the vendored Normal page written through the repository, an ingest
task so `kb.run_rendition` resolves, and `claim_proposal` observations of `fixtures/s0` batches
located by A0's `parse` under synthetic propose tasks, one of them finished after the cut."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml
from sqlalchemy import Engine, text

from corpus_structure.consolidate import run_pass
from corpus_structure.consolidate.pass_ import ConsolidateConfig
from corpus_structure.core.batch import AuthoredBatch, CitationFrame
from corpus_structure.core.db import repo
from corpus_structure.core.evidence import content_digest, document_key, rendition_key
from corpus_structure.core.payloads import validate_payload
from corpus_structure.ingest.html import build_rendition
from corpus_structure.ingest.profile import compile_profile, load_profile
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.llm.parse import RenditionView, parse
from corpus_structure.schema import registry
from corpus_structure.schema.lookup import name_map
from corpus_structure.schema.pack import load_pack

REPO = Path(__file__).resolve().parents[4]
ROOT = "siegrist_random/random"
PAGE = "special/Normal.html"
CUT = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
BEFORE, AFTER = ("T2", "T3"), ("U5",)


def config() -> ConsolidateConfig:
    raw = yaml.safe_load((REPO / "domains/statistics/methods.yaml").read_text(encoding="utf-8"))
    return ConsolidateConfig(aliases=raw["aliases"], math=raw["math"])


def sql(conn: Any, query: str, **params: Any) -> Any:
    return conn.execute(text(query), params)


@pytest.fixture
def pool_run(committing_db: Engine, helpers: SimpleNamespace) -> SimpleNamespace:
    uri = f"{ROOT}/{PAGE}"
    raw = (REPO / "fixtures/trace/corpus" / uri).read_bytes()
    content = build_rendition(
        raw, compile_profile(load_profile("siegrist")), SentenceConfig(), source_uri=uri
    ).content
    doc_key = document_key("statistics", uri, hashlib.sha256(raw).hexdigest())
    from corpus_structure.core import tex

    view = RenditionView(
        content,
        PAGE,
        rendition_key(doc_key, content_digest(content)),
        tex.effective_macros(content.macros, config().macros()),
    )
    names = dict(name_map([load_pack(REPO / "domains/statistics")]).to_prefixed)
    ins = helpers.ins
    with committing_db.begin() as conn:
        w = helpers.build_world(conn)
        ref = registry.ensure(conn, w.project, [REPO / "domains/statistics"], "human:test")
        run = helpers.new_run(
            conn, w, schema_version_id=ref.id, model_revision_id=ref.model_revision_id
        )
        ingest_cfg = ins(
            conn,
            "ops.method_config",
            method_id=w.method,
            config_hash="cfg:ingest",
            params={"source_profile": {"root": ROOT}},
        )
        document = ins(
            conn,
            "kb.document",
            project_id=w.project,
            key=doc_key,
            source_uri=uri,
            content_hash="h2",
            original_path="o",
            mime="text/html",
        )
        ingest = helpers.new_task(conn, w, run, unit_id=document, method_config_id=ingest_cfg)
        stored = repo.store_rendition(
            conn,
            document,
            doc_key,
            content,
            repo.Build(ingest_cfg, ingest, w.payload["parse_detail"]),
        )
        sql(
            conn,
            "UPDATE ops.task SET status = 'done', finished_at = :t WHERE id = :i",
            t=CUT - timedelta(hours=1),
            i=ingest,
        )
        propose = ins(conn, "ops.method", name="agent.opus", version="1", family="llm")
        propose_cfg = ins(
            conn, "ops.method_config", method_id=propose, params={}, config_hash="cfg:propose"
        )
        tasks = {}
        for n, unit in enumerate((*BEFORE, *AFTER)):
            s0 = json.loads((REPO / "fixtures/s0" / f"{unit}.json").read_text(encoding="utf-8"))
            batch = parse(
                view,
                AuthoredBatch.model_validate(s0["batch"]),
                CitationFrame.model_validate(s0["frame"]),
                names,
            ).stored
            payload = validate_payload(
                "claim_proposal",
                {
                    "batch": batch.model_dump(mode="json", by_alias=True),
                    "schema_version": ref.content_hash,
                },
            )
            task = helpers.new_task(
                conn,
                w,
                run,
                stage="propose",
                unit_type="segment",
                unit_key=unit,
                method_config_id=propose_cfg,
                input_hash=f"i{n}",
            )
            repo.write_observations(
                conn,
                task,
                0,
                [repo.ObservationRow(0, "claim_proposal", payload, rendition_id=stored.id)],
            )
            finished = CUT + (timedelta(minutes=1) if unit in AFTER else -timedelta(minutes=1))
            sql(
                conn,
                "UPDATE ops.task SET status = 'done', finished_at = :t WHERE id = :i",
                t=finished,
                i=task,
            )
            tasks[unit] = task
        method = ins(
            conn, "ops.method", name="consolidate.claims", version="1", family="consolidate"
        )
        cfg = ins(
            conn,
            "ops.method_config",
            method_id=method,
            config_hash="cfg:consolidate",
            params=config().model_dump(mode="json"),
        )
        rules = ins(conn, "ops.method", name="validate.rules", version="1", family="validate")
        rules_cfg = ins(
            conn, "ops.method_config", method_id=rules, params={}, config_hash="cfg:rules"
        )
        common = {"unit_type": "run", "unit_key": "run", "status": "running", "attempt": 1}
        assemble_task = helpers.new_task(
            conn, w, run, stage="assemble", method_config_id=cfg, input_hash="a", **common
        )
        final = helpers.new_task(
            conn, w, run, stage="finalize", method_config_id=cfg, input_hash="f", **common
        )
        m19 = helpers.new_task(
            conn, w, run, stage="finalize", method_config_id=rules_cfg, input_hash="m", **common
        )
        m19_again = helpers.new_task(
            conn, w, run, stage="finalize", method_config_id=rules_cfg, input_hash="m2", **common
        )
    return SimpleNamespace(
        engine=committing_db,
        run=run,
        m19=m19,
        m19_again=m19_again,
        tasks=tasks,
        assemble_task=assemble_task,
        final=final,
    )


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
