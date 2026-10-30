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

from corpus_structure.core._model.revision import CONTENT_HASH, LABEL
from corpus_structure.core.db import legacy_metadata as store
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
