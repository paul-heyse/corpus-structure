"""Protected split effects retain actual inputs and reject conflicting intentions."""

import copy
import json

import pytest
from psycopg import Error as PostgresError
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.evaluate.semantic import split_documents, split_provenance_summary
from corpus_structure.evaluate.split import SplitConfig
from corpus_structure.semantic.metadata import table
from semantic.agent_scenarios import ResubmissionRecipe

_composed_case = pytest.mark.parametrize(
    "resubmission_case", [ResubmissionRecipe(composed=True)], indirect=True
)


def prepare(resubmission_case):
    # The shared fixture installs the actual selected head. Functional consumers do not
    # author or replace native definitions in setup; I04 checks that route separately.
    prepared, *_ = resubmission_case.stage.result
    with resubmission_case.admin.connect() as conn:
        uri = conn.scalar(select(table("kb.document").c.source_uri))
    return prepared, uri


def invoke(conn, release, intent):
    return conn.scalar(
        text("SELECT eval.assign_document_split_decision('resubmit',:r,CAST(:i AS jsonb))"),
        {"r": release, "i": json.dumps(intent)},
    )


@_composed_case
def test_nontext_chapter_has_explicit_python_and_native_refusal(
    resubmission_case,
    tmp_path,
):
    from corpus_structure.semantic.operations import register_document
    from corpus_structure.semantic.refusals import SemanticOperationRefusal

    commit_writer_engine = resubmission_case.writer
    commit_evaluator_engine = resubmission_case.evaluator
    release, _ = prepare(resubmission_case)
    source = tmp_path / "chapter.txt"
    source.write_bytes(b"a separately registered chapter")
    with commit_writer_engine.begin() as conn:
        register_document(
            conn,
            project_id="resubmit",
            source_uri="chapter.txt",
            original_path=str(source),
            original=source.read_bytes(),
            mime="text/plain",
            metadata={"chapter": True},
            prepared=release,
        )
    with commit_evaluator_engine.begin() as conn:
        with pytest.raises(SemanticOperationRefusal, match="unsupported split chapter"):
            split_documents(conn, "resubmit", SplitConfig(), release_id=release.release_id)
        forged = dict(
            version="split-decision-1",
            algorithm="chapter-uri-hash-1",
            project_id="resubmit",
            release_id=release.release_id,
            seed=0,
            seed_origin="policy",
            policy=dict(seed=0, forced_dev=[], reserved=[]),
            population=[],
            previous=[],
            assignments=[],
        )
        with pytest.raises(DBAPIError, match="unsupported split chapter"), conn.begin_nested():
            invoke(conn, release.release_id, forged)
        assert conn.scalar(text("SELECT count(*) FROM eval.split_decision")) == 0
        assert conn.scalar(text("SELECT count(*) FROM eval.document_split")) == 0


@_composed_case
def test_actual_override_reason_replay_and_immutable_provenance(
    resubmission_case,
    tmp_path,
):
    commit_evaluator_engine = resubmission_case.evaluator
    release, uri = prepare(resubmission_case)
    with commit_evaluator_engine.begin() as conn:
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


@_composed_case
def test_changed_outputs_refuse_without_orphan_decision(
    resubmission_case,
    tmp_path,
):
    from corpus_structure.evaluate.split import SplitDocument
    from corpus_structure.evaluate.split_decisions import prepare_split_decision

    commit_evaluator_engine = resubmission_case.evaluator
    release, uri = prepare(resubmission_case)
    with commit_evaluator_engine.begin() as conn:
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


@_composed_case
def test_existing_policy_conflict_and_malformed_policy_refuse(
    resubmission_case,
    tmp_path,
):
    commit_evaluator_engine = resubmission_case.evaluator
    release, uri = prepare(resubmission_case)
    with commit_evaluator_engine.begin() as conn:
        first = split_documents(
            conn,
            "resubmit",
            SplitConfig(forced_dev={uri: "dev"}),
            seed=19,
            release_id=release.release_id,
        )
        recorded = conn.scalar(select(table("eval.split_decision").c.intent))
        current = copy.deepcopy(recorded)
        current["previous"] = [
            {"document_id": row["document_id"], "split": "dev", "reason": "persisted", "seed": None}
            for row in current["population"]
        ]
        current["assignments"] = []
        reserved = copy.deepcopy(current)
        reserved["policy"]["forced_dev"] = []
        reserved["policy"]["reserved"] = [[uri, "new worked example"]]
        with pytest.raises(DBAPIError, match="contradicts immutable"), conn.begin_nested():
            invoke(conn, release.release_id, reserved)
        no_seed = copy.deepcopy(current)
        del no_seed["policy"]["seed"]
        with pytest.raises(DBAPIError, match="unsupported split"), conn.begin_nested():
            invoke(conn, release.release_id, no_seed)
        duplicate = copy.deepcopy(current)
        duplicate["policy"]["forced_dev"] = [[uri, "one"], [uri, "two"]]
        with pytest.raises(DBAPIError, match="duplicate split policy"), conn.begin_nested():
            invoke(conn, release.release_id, duplicate)
        wrong_population = copy.deepcopy(current)
        wrong_population["population"] = []
        with pytest.raises(DBAPIError, match="basis changed"), conn.begin_nested():
            invoke(conn, release.release_id, wrong_population)
        assert (
            conn.scalar(select(table("eval.split_decision").c.decision_id)) == first["decision_id"]
        )


@_composed_case
def test_new_noop_decision_does_not_relabel_legacy_assignments(
    resubmission_case,
    tmp_path,
):
    commit_db_engine = resubmission_case.admin
    commit_evaluator_engine = resubmission_case.evaluator
    release, uri = prepare(resubmission_case)
    # Trusted fixture represents a retained predecessor row with unavailable provenance.
    with commit_db_engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        conn.execute(
            text(
                "INSERT INTO eval.document_split(project_id,source_uri,split) "
                "VALUES('resubmit',:u,'dev')"
            ),
            {"u": uri},
        )
    with commit_evaluator_engine.begin() as conn:
        result = split_documents(
            conn, "resubmit", SplitConfig(seed=42), release_id=release.release_id
        )
        assert result["added"] == {}
        assert result["decision_provenance"] == "recorded"
        assert result["assignment_provenance"] == {"recorded": 0, "legacy_unavailable": 1}
        split = conn.execute(select(table("eval.document_split"))).mappings().one()
        assert split["split"] == "dev" and split["decision_id"] is None and split["reason"] is None


@pytest.mark.parametrize("same_intent", [True, False])
@_composed_case
def test_concurrent_intentions_replay_or_refuse_changed_basis(
    resubmission_case,
    tmp_path,
    same_intent,
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from corpus_structure.evaluate.split import SplitDocument
    from corpus_structure.evaluate.split_decisions import prepare_split_decision

    commit_db_engine = resubmission_case.admin
    commit_evaluator_engine = resubmission_case.evaluator
    release, uri = prepare(resubmission_case)
    with commit_db_engine.connect() as conn:
        d = conn.execute(select(table("kb.document"))).mappings().one()
    document = SplitDocument(d["id"], uri, d["meta"].get("chapter"))
    policy = SplitConfig(forced_dev={uri: "dev"})
    intentions = [
        json.loads(
            prepare_split_decision(
                "resubmit", release.release_id, [document], policy, {}, seed=seed
            ).intent
        )
        for seed in (19, 19 if same_intent else 20)
    ]
    barrier = Barrier(2)

    def apply(intent):
        try:
            with commit_evaluator_engine.begin() as conn:
                barrier.wait(timeout=15)
                return invoke(conn, release.release_id, intent)["outcome"]
        except DBAPIError as error:
            assert isinstance(error.orig, PostgresError)
            assert error.orig.sqlstate == "40001"
            return "changed_basis"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(apply, intentions))
    assert sorted(outcomes) == (
        ["committed", "exact_replay"] if same_intent else ["changed_basis", "committed"]
    )
    with commit_evaluator_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM eval.split_decision")) == 1
        assert conn.scalar(text("SELECT count(*) FROM eval.document_split")) == 1


def test_forward_upgrade_preserves_unavailable_predecessor_split(semantic_database_at):
    from corpus_structure.semantic.migrations import upgrade

    with semantic_database_at("semantic_m1_records_20261103") as engine:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO data.project(project_id) VALUES('legacy')"))
            conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
            conn.execute(text("SELECT eval.assign_document_split('legacy','legacy:source','dev')"))
            before = conn.execute(text("SELECT id,source_uri,split FROM eval.document_split")).one()
        with engine.begin() as conn:
            upgrade(conn)
            after = conn.execute(
                text("SELECT id,source_uri,split,decision_id,reason FROM eval.document_split")
            ).one()
            assert tuple(after[:3]) == tuple(before)
            assert after.decision_id is None and after.reason is None
