"""Independent reference grades and immutable pass C snapshots on a real native store."""

import copy
import json

import anyio
import pytest
from fastmcp import Client
from pydantic import JsonValue
from sqlalchemy import create_engine, insert, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.pool import NullPool

from corpus_structure.evaluate.semantic import (
    ReferenceError,
    agreement,
    create_reference_set,
    ensure_items,
    record_pass,
    reference_evaluate,
    relocate_frame,
    split_documents,
)
from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.proposals import ProposalFrame, ProposalSentence

from .test_agent_resubmission import lease_and_read, source_task


def test_independent_reference_grade_retains_exact_pass_and_qualification(
    semantic_db_engine, semantic_writer_engine, tmp_path, cli
):
    prepared, run, task, locator = source_task(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html", composed=True
    )
    source_session = SemanticAgentSession(semantic_writer_engine, run)

    async def source():
        async with Client(build_semantic_server(source_session)) as client:
            unit = await lease_and_read(client, run, task)
            response = await client.call_tool(
                "propose_claims",
                {
                    "task_id": task,
                    "batch": {
                        "unit_ref": locator,
                        "entities": [
                            {
                                "id": "prediction_person",
                                "class_iri": "https://example.org/Person",
                                "label": "Alice",
                            }
                        ],
                        "claims": [
                            {
                                "id": "prediction_name",
                                "subject": "prediction_person",
                                "predicate": "https://example.org/name",
                                "object": {"kind": "text", "text": "Alice"},
                                "qualification": {"modality": "asserted", "polarity": True},
                                "establishment": "stated",
                                "evidence": [
                                    {
                                        "sentence": unit["sentences"][0]["id"],
                                        "quote": "Alice is here.",
                                        "role": "primary",
                                    }
                                ],
                            }
                        ],
                    },
                },
            )
            assert response.structured_content is not None
            assert response.structured_content["submission_disposition"] == "completed_accepted"

    anyio.run(source)
    finalize_bound_run(semantic_writer_engine, run, "reference-result")
    # Independent expected authoring: different local names, explicit qualifier and source text.
    authored = {
        "unit_ref": locator,
        "entities": [
            {"id": "reference_person", "class_iri": "https://example.org/Person", "label": "Alice"}
        ],
        "claims": [
            {
                "id": "reference_name",
                "subject": "reference_person",
                "predicate": "https://example.org/name",
                "object": {"kind": "text", "text": "Alice"},
                "qualification": {"modality": "asserted", "polarity": True},
                "establishment": "stated",
                "evidence": [
                    {"sentence": "reference_sentence", "quote": "Alice is here.", "role": "primary"}
                ],
            }
        ],
    }
    frame = ProposalFrame(
        locator, "Alice is here.", (ProposalSentence("reference_sentence", locator, 0, 14),)
    )
    evaluator = create_engine(
        semantic_db_engine.url.set(username="corpus_sem_evaluator"), poolclass=NullPool
    )
    try:
        with evaluator.begin() as conn:
            split_documents(conn, "resubmit")
            made = create_reference_set(
                conn,
                project_id="resubmit",
                source_run_id=run,
                label="independent",
                split="dev",
                size=1,
            )
            assert set(made["sampling"]["allocation"]) == {"paragraph/unknown"}
            uid = next(iter(made["units"].values()))
            raw = ("  " + json.dumps(authored) + "\n").encode()
            a = record_pass(
                conn,
                unit_id=uid,
                pass_kind="A",
                actor="automated-reference-A",
                authored=raw,
                frame=frame,
            )
            b = record_pass(
                conn,
                unit_id=uid,
                pass_kind="B",
                actor="automated-reference-B",
                authored=json.dumps(authored).encode(),
                frame=frame,
            )
            assert agreement(conn, uid)["a_to_b"]["tiers"]["full"]["f1"] == 1
            c = record_pass(
                conn,
                unit_id=uid,
                pass_kind="C",
                actor="automated-adjudicator",
                authored=raw,
                frame=frame,
            )
            stored = ensure_items(conn, c)
            assert stored.authored == raw
            report = reference_evaluate(
                conn, project_id="resubmit", run_id=run, set_id=made["set_id"]
            )
            for tier in ("core", "full", "evidence"):
                assert report.result["tiers"][tier] == {
                    "reference": 1,
                    "prediction": 1,
                    "matched": 1,
                    "precision": 1.0,
                    "recall": 1.0,
                    "f1": 1.0,
                }
            assert report.reference_snapshot[0]["pass_id"] == c
            first_report = report.id
        # A changed adjudication creates a new grade while the old snapshot stays immutable.
        with evaluator.begin() as conn:
            other = copy.deepcopy(authored)
            other["claims"][0]["qualification"]["polarity"] = False
            new_c = record_pass(
                conn,
                unit_id=uid,
                pass_kind="C",
                actor="automated-adjudicator",
                authored=json.dumps(other).encode(),
                frame=frame,
            )
            changed = reference_evaluate(
                conn, project_id="resubmit", run_id=run, set_id=made["set_id"]
            )
            assert changed.result["tiers"]["core"]["matched"] == 1
            assert changed.result["tiers"]["full"]["matched"] == 0
            old = (
                conn.execute(
                    select(table("eval.reference_evaluation")).where(
                        table("eval.reference_evaluation").c.id == first_report
                    )
                )
                .mappings()
                .one()
            )
            assert old["reference_snapshot"][0]["pass_id"] == c
            assert changed.reference_snapshot[0]["pass_id"] == new_c
            # Native caller cannot forge a grade against an earlier, unselected C snapshot.
            with pytest.raises(DBAPIError, match="incomplete or stale"):
                with conn.begin_nested():
                    conn.execute(
                        text(
                            "SELECT eval.record_reference_evaluation(:p,:r,:s,CAST(:snap AS jsonb),'{}'::jsonb)"
                        ),
                        {
                            "p": "resubmit",
                            "r": run,
                            "s": made["set_id"],
                            "snap": json.dumps(report.reference_snapshot),
                        },
                    )
        with semantic_writer_engine.connect() as conn, pytest.raises(DBAPIError):
            conn.execute(select(table("eval.reference_pass")))
        # Source-frame movement is versioned; a different target cut cannot silently reuse it.
        with semantic_db_engine.begin() as conn:
            original = conn.execute(select(table("kb.rendition"))).mappings().one()
            relocated = conn.scalar(
                insert(table("kb.rendition"))
                .values(
                    document_id=original["document_id"],
                    key="reference-relocated",
                    content_digest="relocated-digest",
                    canonical_text="Intro. Alice is here.",
                    content=original["content"],
                    parse_status="ok",
                )
                .returning(table("kb.rendition").c.id)
            )
        with evaluator.begin() as conn:
            before = ensure_items(conn, new_c)
            moved = relocate_frame(conn, new_c, rendition_id=relocated)
            after = ensure_items(conn, new_c)
            assert after.frame_id == moved and after.authored == before.authored
            assert before.frame[0]["start"] == 0 and after.frame[0]["start"] == 7
            assert (
                conn.scalar(
                    select(table("eval.reference_frame").c.parent_id).where(
                        table("eval.reference_frame").c.id == moved
                    )
                )
                == before.frame_id
            )
            with pytest.raises(ReferenceError, match="target source cut"):
                reference_evaluate(conn, project_id="resubmit", run_id=run, set_id=made["set_id"])
        # Actual Typer dispatch uses the evaluator credential purpose and persistent native APIs.
        from dataclasses import asdict

        from corpus_structure.settings import Settings

        settings = lambda: Settings(
            database={
                "url": semantic_writer_engine.url.set(drivername="postgresql").render_as_string(
                    hide_password=False
                ),
                "maintenance_url": semantic_db_engine.url.set(
                    drivername="postgresql"
                ).render_as_string(hide_password=False),
                "evaluator_url": evaluator.url.set(drivername="postgresql").render_as_string(
                    hide_password=False
                ),
            }
        )
        split_result = cli("golden", "split", "--project", "resubmit", "--json", settings=settings)
        assert split_result.exit_code == 0, split_result.stderr
        created = cli(
            "golden",
            "create",
            "--project",
            "resubmit",
            "--from-run",
            str(run),
            "--label",
            "cli-reference",
            "--split",
            "dev",
            "--size",
            "1",
            "--json",
            settings=settings,
        )
        assert created.exit_code == 0, created.stderr
        made_cli = json.loads(created.stdout)
        authored_file = tmp_path / "reference.json"
        authored_file.write_bytes(json.dumps(authored).encode())
        frame_file = tmp_path / "frame.json"
        frame_file.write_text(json.dumps(asdict(frame)))
        submitted = cli(
            "golden",
            "submit",
            "--project",
            "resubmit",
            "--unit",
            str(next(iter(made_cli["units"].values()))),
            "--pass",
            "C",
            "--actor",
            "automated-independent-reference",
            "--authored",
            str(authored_file),
            "--frame",
            str(frame_file),
            "--json",
            settings=settings,
        )
        assert submitted.exit_code == 0, submitted.stderr
        status = cli(
            "golden",
            "status",
            "--project",
            "resubmit",
            "--label",
            "cli-reference",
            "--json",
            settings=settings,
        )
        assert status.exit_code == 0 and json.loads(status.stdout)[0]["status"] == {
            "adjudicated": 1
        }, status.stderr
        graded = cli(
            "eval",
            "run",
            "--project",
            "resubmit",
            "--run",
            str(run),
            "--set-id",
            str(made_cli["set_id"]),
            "--json",
            settings=settings,
        )
        assert graded.exit_code == 0, graded.stderr
        assert json.loads(graded.stdout)["result"]["tiers"]["full"]["matched"] == 1
    finally:
        evaluator.dispose()


def test_archived_split_policy_preserves_reserved_forced_and_chapter_partitions(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    from corpus_structure.evaluate.semantic import evaluation_config

    policy = b"""split:
  seed: 17
  reserved:
    Reserved.html: independent worked example
  forced_dev:
    source.html: source reference unit
    ch1/Page0.html: required development page
golden:
  sizes: {dev: 2, test: 1}
"""
    prepared, _, _, _ = source_task(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path / "source.html",
        composed=True,
        evaluation_policy=policy,
    )
    with semantic_db_engine.begin() as conn:
        for chapter in ("ch1", "ch2"):
            for i in range(5):
                conn.execute(
                    insert(table("kb.document")).values(
                        project_id="resubmit",
                        key=f"{chapter}-{i}",
                        source_uri=f"https://example.org/{chapter}/Page{i}.html",
                        content_hash="independent-fixture",
                        original_path="unused",
                        mime="text/html",
                        meta={"chapter": chapter},
                    )
                )
        conn.execute(
            insert(table("kb.document")).values(
                project_id="resubmit",
                key="reserved",
                source_uri="https://example.org/Reserved.html",
                content_hash="independent-fixture",
                original_path="unused",
                mime="text/html",
                meta={"chapter": "ch1"},
            )
        )
    evaluator = create_engine(
        semantic_db_engine.url.set(username="corpus_sem_evaluator"), poolclass=NullPool
    )
    try:
        with evaluator.begin() as conn:
            assert evaluation_config(conn, prepared.release_id).golden.sizes == {
                "dev": 2,
                "test": 1,
            }
            first = split_documents(conn, "resubmit")
            assert first["seed"] == 17 and first["added"] == {"dev": 10, "test": 1, "reserved": 1}
            rows = {
                row.source_uri: row.split
                for row in conn.execute(select(table("eval.document_split")))
            }
            assert rows["https://example.org/Reserved.html"] == "reserved"
            assert rows["https://example.org/ch1/Page0.html"] == "dev"
            assert sum(split == "test" for uri, split in rows.items() if "/ch1/" in uri) == 0
            assert sum(split == "test" for uri, split in rows.items() if "/ch2/" in uri) == 1
            replay = split_documents(conn, "resubmit", seed=999)
            assert replay["added"] == {} and replay["total"] == first["total"]
            assert {
                row.source_uri: row.split
                for row in conn.execute(select(table("eval.document_split")))
            } == rows
    finally:
        evaluator.dispose()


def test_duplicate_premise_fact_preserves_later_local_claim_references(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    prepared, run, task, locator = source_task(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html", composed=True
    )

    async def source():
        async with Client(
            build_semantic_server(SemanticAgentSession(semantic_writer_engine, run))
        ) as client:
            unit = await lease_and_read(client, run, task)
            evidence = [
                {
                    "sentence": unit["sentences"][0]["id"],
                    "quote": "Alice is here.",
                    "role": "primary",
                }
            ]

            def claim(identity, condition=None):
                qualification: dict[str, JsonValue] = {"modality": "asserted", "polarity": True}
                if condition is not None:
                    qualification["condition"] = {"kind": "claim", "ref": condition}
                return {
                    "id": identity,
                    "subject": "source_person",
                    "predicate": "https://example.org/name",
                    "object": {"kind": "text", "text": "Alice"},
                    "qualification": qualification,
                    "establishment": "stated",
                    "evidence": evidence,
                }

            response = await client.call_tool(
                "propose_claims",
                {
                    "task_id": task,
                    "batch": {
                        "unit_ref": locator,
                        "entities": [
                            {
                                "id": "source_person",
                                "class_iri": "https://example.org/Person",
                                "label": "Alice",
                            }
                        ],
                        "claims": [
                            claim("first_premise"),
                            claim("duplicate_premise"),
                            claim("conclusion", "duplicate_premise"),
                        ],
                    },
                },
            )
            assert response.structured_content is not None
            assert response.structured_content["submission_disposition"] == "completed_accepted"

    anyio.run(source)
    finalize_bound_run(semantic_writer_engine, run, "duplicate-premise-result")
    # The independent expected claims have one premise and refer to that retained fact.
    citation = [{"sentence": "independent_sentence", "quote": "Alice is here.", "role": "primary"}]
    reference = {
        "unit_ref": locator,
        "entities": [
            {"id": "reference_person", "class_iri": "https://example.org/Person", "label": "Alice"}
        ],
        "claims": [
            {
                "id": "expected_premise",
                "subject": "reference_person",
                "predicate": "https://example.org/name",
                "object": {"kind": "text", "text": "Alice"},
                "qualification": {"modality": "asserted", "polarity": True},
                "establishment": "stated",
                "evidence": citation,
            },
            {
                "id": "expected_conclusion",
                "subject": "reference_person",
                "predicate": "https://example.org/name",
                "object": {"kind": "text", "text": "Alice"},
                "qualification": {
                    "modality": "asserted",
                    "polarity": True,
                    "condition": {"kind": "claim", "ref": "expected_premise"},
                },
                "establishment": "stated",
                "evidence": citation,
            },
        ],
    }
    evaluator = create_engine(
        semantic_db_engine.url.set(username="corpus_sem_evaluator"), poolclass=NullPool
    )
    try:
        with evaluator.begin() as conn:
            made = create_reference_set(
                conn, project_id="resubmit", source_run_id=run, label="premise-alias", size=1
            )
            record_pass(
                conn,
                unit_id=next(iter(made["units"].values())),
                pass_kind="C",
                actor="independent-reference",
                authored=json.dumps(reference).encode(),
                frame=ProposalFrame(
                    locator,
                    "Alice is here.",
                    (ProposalSentence("independent_sentence", locator, 0, 14),),
                ),
            )
            grade = reference_evaluate(
                conn, project_id="resubmit", run_id=run, set_id=made["set_id"]
            )
            assert grade.result["tiers"]["full"] == {
                "reference": 2,
                "prediction": 2,
                "matched": 2,
                "precision": 1.0,
                "recall": 1.0,
                "f1": 1.0,
            }
    finally:
        evaluator.dispose()
