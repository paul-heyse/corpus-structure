"""Store test rows (P0-F-4): the minimal world the repository and invariant tests write into.

`world` builds, inside the rolled-back `db` connection, one model revision, the registry's payload
schemas (M4's content, plus rows for the opaque payload columns that have no payload class yet),
a project and a schema version with its member rows and the trace's predicates, a method and an
ingest configuration, a policy version, a run, an ingest task and a document. Values are written
by hand for the tests; the repository's own primitives write what they own.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import Connection, insert, select

from corpus_structure.core import db as store
from corpus_structure.core._model.revision import CONTENT_HASH, LABEL
from corpus_structure.core.vocab import ClaimModality, StatementKind
from corpus_structure.schema import model, registry

T = store.metadata.tables
PREDICATES = ("stat:has_distribution", "stat:defined_as", "core:proves")
OPAQUE = ("parse_detail", "intervention_refs", "compiled_artifact")


def ins(conn: Connection, table: str, **values: Any) -> int:
    return int(
        conn.execute(insert(T[table]).values(**values).returning(T[table].c.id)).scalar_one()
    )


def payload_schema_rows(conn: Connection, revision_id: int) -> dict[str, int]:
    """The registry's rows for the installed model revision, and test rows for opaque payloads."""
    out = {}
    registry._ensure_model_revision(conn, model.load())
    out.update(registry._ensure_payload_schemas(conn, model.load(), revision_id))
    for kind in OPAQUE:  # no payload class declares these yet (M4's reported gap)
        out[kind] = ins(
            conn,
            "meta.payload_schema",
            model_revision_id=revision_id,
            **{"class": f"test:{kind}"},
            kind=kind,
            version=1,
            compatibility_class="initial",
            json_schema_id=f"test:{kind}",
            arrow_schema=b"",
            reason="test",
            authorized_by="test",
        )
    return out


def build_world(conn: Connection) -> SimpleNamespace:
    w = SimpleNamespace()
    w.revision = ins(
        conn,
        "meta.model_revision",
        label=LABEL,
        content_hash=CONTENT_HASH,
        compilers={},
        key_scheme=1,
    )
    w.payload = payload_schema_rows(conn, w.revision)
    w.project = ins(conn, "meta.project", name="test", domain="statistics")
    w.schema_version = ins(
        conn,
        "meta.schema_version",
        project_id=w.project,
        domain="statistics",
        label="0.1.0",
        content_hash="a" * 64,
        model_revision_id=w.revision,
        source={},
        created_by="human:test",
    )
    for name in PREDICATES:
        conn.execute(
            insert(T["meta.schema_slot"]).values(
                schema_version_id=w.schema_version, name=name, role="predicate", annotations={}
            )
        )
    for member in ClaimModality:
        conn.execute(
            insert(T["meta.claim_modality"]).values(
                schema_version_id=w.schema_version, value=member.value
            )
        )
    for member in StatementKind:
        conn.execute(
            insert(T["meta.statement_kind"]).values(
                schema_version_id=w.schema_version, value=member.value
            )
        )
    w.method = ins(conn, "ops.method", name="ingest.html", version="1", family="ingest")
    w.config = ins(conn, "ops.method_config", method_id=w.method, params={}, config_hash="cfg:1")
    w.config2 = ins(
        conn, "ops.method_config", method_id=w.method, params={"x": 1}, config_hash="cfg:2"
    )
    w.policy = ins(
        conn,
        "ops.policy_version",
        project_id=w.project,
        label="p",
        content_hash="p",
        source="",
        created_by="human:test",
    )
    w.run = new_run(conn, w)
    w.task = new_task(conn, w, w.run)
    w.document = ins(
        conn,
        "kb.document",
        project_id=w.project,
        key="doc:" + "0" * 32,
        source_uri="siegrist_random/random/special/Normal.html",
        content_hash="h",
        original_path="o",
        mime="text/html",
    )
    w.document_key = "doc:" + "0" * 32
    return w


def new_run(conn: Connection, w: SimpleNamespace, **values: Any) -> int:
    return ins(
        conn,
        "ops.run",
        **{
            "project_id": w.project,
            "kind": "full",
            "phase": 0,
            "corpus_hash": "c",
            "model_revision_id": w.revision,
            "schema_version_id": w.schema_version,
            "key_scheme": 1,
            "policy_version_id": w.policy,
            "code_commit": "test",
            "status": "running",
            **values,
        },
    )


def new_task(conn: Connection, w: SimpleNamespace, run: int, **values: Any) -> int:
    return ins(
        conn,
        "ops.task",
        **{
            "run_id": run,
            "stage": "ingest",
            "unit_type": "document",
            "method_config_id": w.config,
            "input_hash": "i",
            "status": "running",
            **values,
        },
    )


@pytest.fixture
def world(db: Connection) -> SimpleNamespace:
    return build_world(db)


@pytest.fixture(scope="session")
def helpers() -> SimpleNamespace:
    """The builders above, for tests (importlib import mode leaves this module unimportable)."""
    return SimpleNamespace(
        ins=ins, new_run=new_run, new_task=new_task, build_world=build_world, select=select, T=T
    )


@pytest.fixture
def pool_run(committing_db, helpers):
    import hashlib
    import json
    from datetime import UTC, datetime, timedelta
    from pathlib import Path
    from types import SimpleNamespace

    import yaml
    from sqlalchemy import text

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
    BEFORE, AFTER = ("T2", "T3", "U6"), ("U5",)

    def config():
        raw = yaml.safe_load((REPO / "domains/statistics/methods.yaml").read_text())
        return ConsolidateConfig(aliases=raw["aliases"], math=raw["math"])

    def sql(conn, query, **params):
        return conn.execute(text(query), params)

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


@pytest.fixture
def finalized_pool_run(pool_run):
    from datetime import UTC, datetime

    from sqlalchemy import text

    from corpus_structure.consolidate import run_pass

    with pool_run.engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE ops.run SET "
                "cut_at=:cut,cut_m19_task_id=:m,status='consolidating' WHERE id=:r"
            ),
            {
                "cut": datetime(2026, 10, 28, 12, 0, tzinfo=UTC),
                "m": pool_run.m19,
                "r": pool_run.run,
            },
        )
    with pool_run.engine.begin() as conn:
        run_pass(conn, pool_run.run, "finalize", pool_run.m19)
        conn.execute(
            text("UPDATE ops.run SET status='finished',finished_at=now() WHERE id=:r"),
            {"r": pool_run.run},
        )
    return pool_run
