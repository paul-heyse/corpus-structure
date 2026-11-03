"""Protected split effects retain actual inputs and reject conflicting intentions."""

import copy
import json

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations, ops
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.evaluate.semantic import split_documents, split_provenance_summary
from corpus_structure.evaluate.split import SplitConfig
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.native_candidate import prepare_series_candidate
from corpus_structure.semantic.native_objects import admit_native

from .agent_scenarios import build_resubmission_case


def prepare(admin, writer, tmp_path):
    with admin.begin() as conn:
        script, authoring = prepare_series_candidate(conn, owned_authoring=True)
        operations = Operations(MigrationContext.configure(conn))

        def apply(operation):
            if isinstance(operation, ops.OpContainer):
                for child in operation.ops:
                    apply(child)
            else:
                operations.invoke(operation)

        apply(script.upgrade_ops)
        admit_native(conn, authoring.desired)
    prepared, *_ = build_resubmission_case(admin, writer, tmp_path / "source.html", composed=True)
    with admin.connect() as conn:
        uri = conn.scalar(select(table("kb.document").c.source_uri))
    return prepared, uri


def invoke(conn, release, intent):
    return conn.scalar(
        text("SELECT eval.assign_document_split_decision('resubmit',:r,CAST(:i AS jsonb))"),
        {"r": release, "i": json.dumps(intent)},
    )


def test_actual_override_reason_replay_and_immutable_provenance(
    semantic_db_engine,
    semantic_writer_engine,
    semantic_evaluator_engine,
    tmp_path,
):
    release, uri = prepare(semantic_db_engine, semantic_writer_engine, tmp_path)
    with semantic_evaluator_engine.begin() as conn:
        result = split_documents(
            conn,
            "resubmit",
            SplitConfig(seed=3, forced_dev={uri: "fixture development"}),
            seed=19,
            release_id=release.release_id,
        )
        decisions = table("eval.split_decision")
        intent = conn.scalar(
            select(decisions.c.intent).where(decisions.c.decision_id == result["decision_id"])
        )
        assert intent["seed"] == 19 and intent["seed_origin"] == "override"
        assert intent["policy"]["seed"] == 3
        assert intent["assignments"][0]["reason"] == "forced_dev: fixture development"
        assert intent["assignments"][0]["split"] == "dev"
        assert invoke(conn, release.release_id, intent) == {
            "decision_id": result["decision_id"],
            "outcome": "exact_replay",
        }
        assert split_provenance_summary(conn, "resubmit") == {
            "recorded": 1,
            "legacy_unavailable": 0,
        }
        changed = copy.deepcopy(intent)
        changed["seed"] = 20  # same forced-dev label cannot reuse the old decision.
        with pytest.raises(DBAPIError, match="basis changed"), conn.begin_nested():
            invoke(conn, release.release_id, changed)
        assert (
            conn.scalar(select(table("eval.document_split").c.decision_id)) == result["decision_id"]
        )
        assert conn.scalar(select(decisions.c.decision_id)) == result["decision_id"]


def test_changed_outputs_refuse_without_orphan_decision(
    semantic_db_engine,
    semantic_writer_engine,
    semantic_evaluator_engine,
    tmp_path,
):
    from corpus_structure.evaluate.split import SplitDocument
    from corpus_structure.evaluate.split_decisions import prepare_split_decision

    release, uri = prepare(semantic_db_engine, semantic_writer_engine, tmp_path)
    with semantic_evaluator_engine.begin() as conn:
        d = conn.execute(select(table("kb.document"))).mappings().one()
        intent = json.loads(
            prepare_split_decision(
                "resubmit",
                release.release_id,
                [SplitDocument(d["id"], uri, d["meta"].get("chapter"))],
                SplitConfig(forced_dev={uri: "dev"}),
                {},
            ).intent
        )
        intent["assignments"][0]["split"] = "test"
        with pytest.raises(DBAPIError, match="differ from frozen"), conn.begin_nested():
            invoke(conn, release.release_id, intent)
        assert conn.scalar(text("SELECT count(*) FROM eval.split_decision")) == 0
        assert conn.scalar(text("SELECT count(*) FROM eval.document_split")) == 0
