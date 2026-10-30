"""Independent reference grades and immutable pass C snapshots on a real native store."""

import copy
import json

import anyio
import pytest
from fastmcp import Client
from pydantic import JsonValue
from sqlalchemy import insert, select, text
from sqlalchemy.exc import DBAPIError

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
    semantic_db_engine, semantic_writer_engine, tmp_path, cli, semantic_evaluator_engine
):
    _prepared, run, task, locator = source_task(
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
    evaluator = semantic_evaluator_engine
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
        record_pass(
            conn,
            unit_id=uid,
            pass_kind="A",
            actor="automated-reference-A",
            authored=raw,
            frame=frame,
        )
        record_pass(
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
        report = reference_evaluate(conn, project_id="resubmit", run_id=run, set_id=made["set_id"])
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
        # Exercise the protected SQL consumer with an independently changed report, bypassing
        # Python construction deliberately. Nested comparisons must reach the same policy rows.
        nested = copy.deepcopy(report.result)
        comparison = {
            "policy_id": "reference-evidence-1",
            "evidence_profile": "reference-evidence-1",
            "reference_path": [],
            "prediction_path": [],
            "evidence_tier": "canonical",
            "agreement": "agrees",
            "decision_tier": "canonical",
            "outcome": "equivalent",
            "numeric": "not_run",
            "valid_points": 0,
            "grammar": "text",
            "mechanism": "canonical",
            "operands": ["Alice", "Alice"],
            "context": "{}",
            "detail": "equal canonical text",
        }
        nested["units"][0]["comparisons"].append(
            {
                **comparison,
                "reference": "reference_name",
                "prediction": "prediction_name",
                "field": "object",
            }
        )
        nested["units"][0]["undecided"].append({"comparisons": [copy.deepcopy(comparison)]})
        from corpus_structure.semantic.scientific_evidence import validate_reference_science

        validate_reference_science(nested)

        def record_native(result):
            return conn.scalar(
                text(
                    "SELECT eval.record_reference_evaluation(:p,:run,:set,"
                    "CAST(:snapshot AS jsonb),CAST(:result AS jsonb))"
                ),
                {
                    "p": "resubmit",
                    "run": run,
                    "set": made["set_id"],
                    "snapshot": json.dumps(report.reference_snapshot),
                    "result": json.dumps(result),
                },
            )

        assert record_native(nested) > report.id
        # An independent administrative fault simulates a formerly admitted bad recipe.
        # The restricted persistence operation must reject it even without reactivation.
        from hashlib import sha256

        from .archive_faults import administrative_archive_edit

        for layout in ("empty", "partial", "moved"):
            with (
                semantic_db_engine.begin() as admin,
                administrative_archive_edit(admin, table("sem.artifact")),
            ):
                original = bytes(
                    admin.scalar(
                        text(
                            "SELECT content FROM sem.artifact WHERE release_id=:r "
                            "AND artifact_name='operation/scientific-policy.json'"
                        ),
                        {"r": _prepared.release_id},
                    )
                )
                altered = json.loads(original)
                if layout == "empty":
                    altered["comparison_paths"], altered["array_rules"] = [], []
                elif layout == "partial":
                    altered["comparison_paths"] = altered["comparison_paths"][:1]
                else:
                    altered["comparison_paths"][0] = "$.unconsumed[*].comparisons[*]"
                encoded = json.dumps(altered).encode()
                admin.execute(
                    text(
                        "UPDATE sem.artifact SET content=:content,content_digest=:digest "
                        "WHERE release_id=:r "
                        "AND artifact_name='operation/scientific-policy.json'"
                    ),
                    {
                        "content": encoded,
                        "digest": sha256(encoded).hexdigest(),
                        "r": _prepared.release_id,
                    },
                )
            try:
                with (
                    pytest.raises(DBAPIError, match="unsupported scientific report layout"),
                    conn.begin_nested(),
                ):
                    record_native(nested)
            finally:
                with (
                    semantic_db_engine.begin() as admin,
                    administrative_archive_edit(admin, table("sem.artifact")),
                ):
                    admin.execute(
                        text(
                            "UPDATE sem.artifact SET content=:content,content_digest=:digest "
                            "WHERE release_id=:r "
                            "AND artifact_name='operation/scientific-policy.json'"
                        ),
                        {
                            "content": original,
                            "digest": sha256(original).hexdigest(),
                            "r": _prepared.release_id,
                        },
                    )
        for location in ("direct", "nested"):
            changed_policy = copy.deepcopy(nested)
            selected = (
                changed_policy["units"][0]["comparisons"][0]
                if location == "direct"
                else changed_policy["units"][0]["undecided"][-1]["comparisons"][0]
            )
            selected["outcome"] = (
                "different" if selected["outcome"] != "different" else "equivalent"
            )
            with (
                pytest.raises(DBAPIError, match="scientific decision differs"),
                conn.begin_nested(),
            ):
                record_native(changed_policy)
        missing = copy.deepcopy(nested)
        del missing["units"][0]["comparisons"]
        with (
            pytest.raises(DBAPIError, match="scientific report array differs"),
            conn.begin_nested(),
        ):
            record_native(missing)
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
        changed = reference_evaluate(conn, project_id="resubmit", run_id=run, set_id=made["set_id"])
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
        with pytest.raises(DBAPIError, match="incomplete or stale"), conn.begin_nested():
            conn.execute(
                text(
                    "SELECT eval.record_reference_evaluation(:p,:r,:s,"
                    "CAST(:snap AS jsonb),'{}'::jsonb)"
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

    def settings():
        return Settings(
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
    assert status.exit_code == 0 and json.loads(status.stdout)[0]["status"] == {"adjudicated": 1}, (
        status.stderr
    )
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


def test_archived_split_policy_preserves_reserved_forced_and_chapter_partitions(
    semantic_db_engine, semantic_writer_engine, tmp_path, semantic_evaluator_engine
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
    evaluator = semantic_evaluator_engine
    with evaluator.begin() as conn:
        assert evaluation_config(conn, prepared.release_id).golden.sizes == {
            "dev": 2,
            "test": 1,
        }
        first = split_documents(conn, "resubmit")
        assert first["seed"] == 17 and first["added"] == {"dev": 10, "test": 1, "reserved": 1}
        rows = {
            row.source_uri: row.split for row in conn.execute(select(table("eval.document_split")))
        }
        assert rows["https://example.org/Reserved.html"] == "reserved"
        assert rows["https://example.org/ch1/Page0.html"] == "dev"
        assert sum(split == "test" for uri, split in rows.items() if "/ch1/" in uri) == 0
        assert sum(split == "test" for uri, split in rows.items() if "/ch2/" in uri) == 1
        replay = split_documents(conn, "resubmit", seed=999)
        assert replay["added"] == {} and replay["total"] == first["total"]
        assert {
            row.source_uri: row.split for row in conn.execute(select(table("eval.document_split")))
        } == rows


def test_duplicate_premise_fact_preserves_later_local_claim_references(
    semantic_db_engine, semantic_writer_engine, tmp_path, semantic_evaluator_engine
):
    _prepared, run, task, locator = source_task(
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
    evaluator = semantic_evaluator_engine
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
        grade = reference_evaluate(conn, project_id="resubmit", run_id=run, set_id=made["set_id"])
        assert grade.result["tiers"]["full"] == {
            "reference": 2,
            "prediction": 2,
            "matched": 2,
            "precision": 1.0,
            "recall": 1.0,
            "f1": 1.0,
        }


@pytest.mark.parametrize("empty_observations", [False, True])
def test_empty_producer_keeps_frozen_source_in_reference_pool(
    semantic_db_engine,
    semantic_writer_engine,
    semantic_evaluator_engine,
    tmp_path,
    empty_observations,
):
    from corpus_structure.evaluate.semantic import _source_units

    _prepared, run, task, locator = source_task(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html", composed=True
    )
    session = SemanticAgentSession(semantic_writer_engine, run)

    async def empty_source():
        async with Client(build_semantic_server(session)) as client:
            await lease_and_read(client, run, task)
            if empty_observations:
                from corpus_structure.semantic.operations import complete_task

                active = session.active(task)
                with semantic_writer_engine.begin() as conn:
                    complete_task(
                        conn,
                        task_id=task,
                        attempt=active.attempt,
                        holder=session.holder,
                        prepared=_prepared,
                        observations=[],
                        outcome="empty",
                    )
            else:
                response = await client.call_tool(
                    "propose_claims",
                    {"task_id": task, "batch": {"unit_ref": locator, "entities": [], "claims": []}},
                )
                assert response.structured_content is not None
                assert response.structured_content["submission_disposition"] == "completed_accepted"

    anyio.run(empty_source)
    finalize_bound_run(semantic_writer_engine, run, "empty-reference-result")
    with semantic_evaluator_engine.begin() as conn:
        # The completed native cut and immutable source frame retain this unit even though
        # the producer supplied no knowledge assertions. Reference recall must expose that.
        source = _source_units(conn, run)
        assert [unit["unit_key"] for unit in source] == [locator]
        if empty_observations:
            assert (
                conn.scalar(
                    select(table("kb.observation").c.id).where(
                        table("kb.observation").c.task_id == task,
                        table("kb.observation").c.payload_definition == "AgentStoredBatch",
                    )
                )
                is None
            )
        made = create_reference_set(
            conn, project_id="resubmit", source_run_id=run, label="empty-producer", size=1
        )
        authored = {
            "unit_ref": locator,
            "entities": [
                {
                    "id": "expected_person",
                    "class_iri": "https://example.org/Person",
                    "label": "Alice",
                }
            ],
            "claims": [
                {
                    "id": "expected_name",
                    "subject": "expected_person",
                    "predicate": "https://example.org/name",
                    "object": {"kind": "text", "text": "Alice"},
                    "qualification": {"modality": "asserted", "polarity": True},
                    "establishment": "stated",
                    "evidence": [
                        {
                            "sentence": "expected_sentence",
                            "quote": "Alice is here.",
                            "role": "primary",
                        }
                    ],
                }
            ],
        }
        record_pass(
            conn,
            unit_id=next(iter(made["units"].values())),
            pass_kind="C",
            actor="independent-source-only-reference",
            authored=json.dumps(authored).encode(),
            frame=ProposalFrame(
                locator,
                "Alice is here.",
                (ProposalSentence("expected_sentence", locator, 0, 14),),
            ),
        )
        grade = reference_evaluate(conn, project_id="resubmit", run_id=run, set_id=made["set_id"])
        for tier in ("core", "full", "evidence"):
            assert grade.result["tiers"][tier]["reference"] == 1
            assert grade.result["tiers"][tier]["prediction"] == 0
            assert grade.result["tiers"][tier]["matched"] == 0


@pytest.mark.parametrize("reuse_origin", [False, True])
def test_missing_empty_source_frame_refuses_until_hash_verified_backfill(
    semantic_db_engine,
    semantic_writer_engine,
    semantic_evaluator_engine,
    tmp_path,
    monkeypatch,
    reuse_origin,
):
    from corpus_structure.semantic import source_frames
    from corpus_structure.semantic.operations import (
        binding_of,
        claim_tasks,
        complete_task,
        create_run,
        create_task,
    )

    # Reproduce an earlier producer that retained packet custody but omitted frame capture.
    # Task creation/claim/completion and source data are still real native operations.
    with monkeypatch.context() as earlier:
        earlier.setattr(source_frames, "capture_source_frame", lambda conn, task_id, packet: None)
        earlier.setattr(source_frames, "backfill_source_frames", lambda engine, run_id: 0)
        prepared, origin_run, task, locator = source_task(
            semantic_db_engine, semantic_writer_engine, tmp_path / "source.html", composed=True
        )
        with semantic_writer_engine.begin() as conn:
            source = (
                conn.execute(select(table("ops.task")).where(table("ops.task").c.id == task))
                .mappings()
                .one()
            )
            claim = claim_tasks(
                conn,
                run_id=origin_run,
                config_id=source["method_config_id"],
                holder="empty-source",
                agent=True,
            )[0]
            complete_task(
                conn,
                task_id=task,
                attempt=claim.attempt,
                holder="empty-source",
                prepared=prepared,
                observations=[],
                outcome="empty",
            )
            packet_hash = source["packet_hash"]
        finalize_bound_run(semantic_writer_engine, origin_run, "missing-source-frame-origin")
        run = origin_run
        if reuse_origin:
            with semantic_writer_engine.begin() as conn:
                original = (
                    conn.execute(
                        select(table("ops.run")).where(table("ops.run").c.id == origin_run)
                    )
                    .mappings()
                    .one()
                )
                run = create_run(
                    conn,
                    project_id="resubmit",
                    binding=binding_of(conn, origin_run),
                    kind="full",
                    options=original["options"],
                    code_commit="source-frame-reuse",
                )
                originals = (
                    conn.execute(
                        select(table("ops.task"))
                        .where(table("ops.task").c.run_id == origin_run)
                        .order_by(table("ops.task").c.id)
                    )
                    .mappings()
                    .all()
                )
                for original_task in originals:
                    reused = create_task(
                        conn,
                        run_id=run,
                        config_id=original_task["method_config_id"],
                        stage=original_task["stage"],
                        unit_type=original_task["unit_type"],
                        unit_id=original_task["unit_id"],
                        unit_key=original_task["unit_key"],
                        input_hash=original_task["input_hash"],
                        packet_hash=original_task["packet_hash"],
                        agent=original_task["packet_hash"] is not None,
                        trigger=original_task["trigger"],
                    )
                    assert (
                        conn.scalar(
                            select(table("ops.task").c.reused_task_id).where(
                                table("ops.task").c.id == reused
                            )
                        )
                        == original_task["id"]
                    )
            finalize_bound_run(semantic_writer_engine, run, "missing-source-frame-reused")

    with (
        pytest.raises(ReferenceError, match="backfill_source_frames"),
        semantic_evaluator_engine.begin() as conn,
    ):
        create_reference_set(
            conn, project_id="resubmit", source_run_id=run, label="missing-frame", size=1
        )
    assert source_frames.backfill_source_frames(semantic_writer_engine, run) == 1
    assert source_frames.backfill_source_frames(semantic_writer_engine, run) == 0
    with semantic_writer_engine.connect() as conn:
        frame = (
            conn.execute(
                select(table("ops.source_frame")).where(table("ops.source_frame").c.task_id == task)
            )
            .mappings()
            .one()
        )
        assert frame["packet_hash"] == packet_hash and frame["unit_ref"] == locator
        assert (
            conn.scalar(
                select(table("kb.observation").c.id).where(
                    table("kb.observation").c.task_id == task
                )
            )
            is None
        )
    with semantic_evaluator_engine.begin() as conn:
        made = create_reference_set(
            conn, project_id="resubmit", source_run_id=run, label="backfilled-frame", size=1
        )
        assert set(made["units"]) == {locator}
        expected = {
            "unit_ref": locator,
            "entities": [{"id": "expected", "class_iri": "https://example.org/Person"}],
            "claims": [
                {
                    "id": "expected_name",
                    "subject": "expected",
                    "predicate": "https://example.org/name",
                    "object": {"kind": "text", "text": "Alice"},
                    "qualification": {"modality": "asserted", "polarity": True},
                    "establishment": "stated",
                    "evidence": [
                        {
                            "sentence": "expected_sentence",
                            "quote": "Alice is here.",
                            "role": "primary",
                        }
                    ],
                }
            ],
        }
        record_pass(
            conn,
            unit_id=next(iter(made["units"].values())),
            pass_kind="C",
            actor="independent-source-reference",
            authored=json.dumps(expected).encode(),
            frame=ProposalFrame(
                locator,
                "Alice is here.",
                (ProposalSentence("expected_sentence", locator, 0, 14),),
            ),
        )
        grade = reference_evaluate(conn, project_id="resubmit", run_id=run, set_id=made["set_id"])
        assert grade.result["tiers"]["full"]["reference"] == 1
        assert grade.result["tiers"]["full"]["prediction"] == 0
        assert grade.result["tiers"]["full"]["matched"] == 0
