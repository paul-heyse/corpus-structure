"""Native durable automated resubmission; uncertain source reports never become located facts."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import anyio
import pytest
import yaml
from fastmcp import Client
from sqlalchemy import insert, select, text, update

from corpus_structure.core.evidence import RenditionContent, Segment
from corpus_structure.core.locators import LocatorIndex
from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import SegmentKind, TaskUnitType
from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.orchestrate.semantic import queue_agent
from corpus_structure.semantic import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.analytical_profile import analytical_inputs
from corpus_structure.semantic.domain_operations import domain_rule_inputs
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import (
    OperationBinding,
    OperationConflict,
    claim_tasks,
    complete_task,
    create_run,
    create_task,
    hold_agent_result,
    record_method,
    register_document,
    store_rendition,
)
from corpus_structure.semantic.proposals import proposal_inputs
from corpus_structure.semantic.releases import persist_release


def source_task(admin, engine, path, *, composed=False, identity_keyed=False, global_names=False, evaluation_policy:bytes|None=None):
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    schema: dict[str, Any] = {
        "id": "https://example.org/resubmit",
        "name": "resubmit",
        "imports": ["core"],
        "prefixes": {"ex": "https://example.org/"},
        "default_prefix": "ex",
        "classes": {"Person": {"is_a": "Entity", "attributes": {"name": {"range": "string"}}}},
    }
    if global_names:
        schema["classes"]["Person"]["annotations"] = {"cs:scope": "global"}
    if identity_keyed:
        schema["classes"]["Person"]["unique_keys"] = {"name": {"unique_key_slots": ["name"]}}
    deps = domain_rule_inputs(ResolvedDependencies(), b"rules: []")
    if evaluation_policy is not None:
        deps=ResolvedDependencies((*deps.artifacts,SourceArtifact('operation/evaluation-split.yaml',evaluation_policy)),deps.vocabularies,deps.ontology_sources)
    bundle = proposal_inputs(
        SourceBundle(
            "domain",
            (
                SourceArtifact("core", core.read_bytes()),
                SourceArtifact("domain", yaml.safe_dump(schema).encode()),
            ),
        ),
        deps,
    )
    bundle, deps = analytical_inputs(bundle, deps)
    profile = PreparationProfile(version="semantic-2" if composed else "semantic-1")
    if composed:
        from corpus_structure.semantic.composed import composed_dependencies

        deps = composed_dependencies(deps)
    prepared = prepare_release(bundle, deps, profile)
    with admin.begin() as conn:
        persist_release(conn, bundle, deps, profile, prepared)
        conn.execute(insert(table("data.project")).values(project_id="resubmit"))
        if composed:
            from corpus_structure.semantic.releases import activate_release

            activate_release(
                conn, "resubmit", prepared.release_id, expected_parent=None, expected_generation=0
            )
        conn.execute(
            insert(table("data.realization")).values(
                project_id="resubmit", realization_id="input", release_id=prepared.release_id
            )
        )
    text_value = "Alice is here."
    path.write_text("<p>" + text_value + "</p>")
    sentence = Segment(kind=SegmentKind.SENTENCE, start=0, end=len(text_value))
    paragraph = Segment(
        kind=SegmentKind.PARAGRAPH, start=0, end=len(text_value), children=(sentence,)
    )
    content = RenditionContent(
        canonical_text=text_value,
        document=Segment(
            kind=SegmentKind.DOCUMENT, start=0, end=len(text_value), children=(paragraph,)
        ),
    )
    locator = str(LocatorIndex(content, "source.html").generate(paragraph))
    config = {
        "model": "automated-resubmission",
        "mode": "extract",
        "max_units": 1,
        "packet_cap_chars": 18000,
    }
    with engine.begin() as conn:
        run = create_run(
            conn,
            project_id="resubmit",
            binding=OperationBinding(prepared.release_id, "input", 0, b"{}"),
            kind="full",
            options={"agent_configs": {"extract": config}},
            code_commit="test",
        )
        document = register_document(
            conn,
            project_id="resubmit",
            source_uri="source.html",
            original_path=str(path),
            original=path.read_bytes(),
            metadata={"page": "source.html"},
        )
        from pydantic import BaseModel

        class SourceConfig(BaseModel):
            pass

        cid = record_method(
            conn,
            SimpleNamespace(
                name="read",
                version="1",
                family="ingest",
                tier="deterministic",
                confidence_source=None,
                unit_type=TaskUnitType.RUN,
                Config=SourceConfig,
            ),
            "default",
            {},
            "read-config",
        )
        source = create_task(
            conn, run_id=run, config_id=cid, stage="ingest", unit_type="run", input_hash="source"
        )
        claim = claim_tasks(conn, run_id=run, config_id=cid, holder="source")[0]
        rid = store_rendition(
            conn,
            run_id=run,
            document_id=document,
            content=content,
            task_id=source,
            config_id=cid,
            parse_detail={},
        )
        complete_task(
            conn,
            task_id=source,
            attempt=claim.attempt,
            holder="source",
            prepared=prepared,
            observations=[],
            outcome="empty",
        )
        segment = conn.execute(
            select(table("kb.segment").c.id).where(
                table("kb.segment").c.rendition_id == rid, table("kb.segment").c.kind == "paragraph"
            )
        ).scalar_one()
        (task,) = queue_agent(
            conn,
            run_id=run,
            prepared=prepared,
            configuration=config,
            units=(UnitRef(TaskUnitType.SEGMENT, segment, locator),),
        )
    return prepared, run, task, locator


async def lease_and_read(client, run, task, *, expect_previous=False):
    queue = (await client.call_tool("queue_next", {"run": run})).structured_content
    assert queue is not None
    leased = queue["tasks"][0]
    assert leased["task_id"] == task
    assert bool(leased.get("previous_issues")) == expect_previous
    if expect_previous:
        assert all(set(issue) == {"path", "code", "detail"} for issue in leased["previous_issues"])
    manifest = (await client.call_tool("read_instructions", {"task_id": task})).structured_content
    assert manifest is not None
    for part in manifest["parts"]:
        for page in range(1, part["pages"] + 1):
            await client.call_tool(
                "read_instructions", {"task_id": task, "part": part["name"], "page": page}
            )
    pieces = []
    for part in range(1, leased["parts"] + 1):
        page = (
            await client.call_tool("read_unit", {"task_id": task, "part": part})
        ).structured_content
        assert page is not None
        pieces.append(page["text"])
    return json.loads("".join(pieces))


@pytest.mark.parametrize("refused", (False, True))
def test_uncertain_first_hold_survives_session_restart_and_terminal_second_report(
    semantic_db_engine, semantic_writer_engine, tmp_path, refused
):
    _prepared, run, task, locator = source_task(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html"
    )
    engine = semantic_writer_engine
    first = SemanticAgentSession(engine, run)
    fabricated = "Zyxwvu qrst nop invented quotation."

    async def journey():
        async with Client(build_semantic_server(first)) as client:
            unit = await lease_and_read(client, run, task)
            raw = {
                "unit_ref": locator,
                "entities": [{"id": "person", "class_iri": "https://example.org/Person"}],
                "claims": [
                    {
                        "id": "name",
                        "subject": "person",
                        "predicate": "https://example.org/name",
                        "object": {"kind": "text", "text": "Alice"},
                        "qualification": {"modality": "asserted", "polarity": True},
                        "establishment": "stated",
                        "evidence": [
                            {
                                "sentence": unit["sentences"][0]["id"],
                                "quote": fabricated,
                                "role": "primary",
                            }
                        ],
                    }
                ],
            }
            if refused:
                raw["claims"][0]["predicate"] = "https://example.org/not-declared"
                raw["claims"][0]["evidence"][0]["quote"] = "Alice is here."
            protocol = (
                await client.call_tool(
                    "propose_claims", {"task_id": task, "batch": raw, "schema_hash": "wrong"}
                )
            ).structured_content
            assert protocol is not None
            assert protocol["status"] == "held"
            assert protocol["submission_disposition"] == "refused_context"
            with engine.connect() as conn:
                assert (
                    conn.execute(
                        select(table("ops.task").c.error).where(table("ops.task").c.id == task)
                    ).scalar_one()
                    is None
                )
            held = (
                await client.call_tool("propose_claims", {"task_id": task, "batch": raw})
            ).structured_content
            assert held is not None
            assert held["status"] == "held" and held["rejected"] and held["task_open"]
            assert held["submission_disposition"] == "held"
            with engine.connect() as conn:
                row = (
                    conn.execute(select(table("ops.task")).where(table("ops.task").c.id == task))
                    .mappings()
                    .one()
                )
                first_attempt = row["attempt"]
                packet = row["packet_hash"]
                assert row["error"]["semantic_proposal_first_result"]["result"]["issues"]
                assert not conn.execute(
                    select(table("kb.observation").c.id).where(
                        table("kb.observation").c.task_id == task
                    )
                ).first()
        # A replaced host cannot renew the previous lease. Advance its persisted expiry
        # directly instead of sleeping, then exercise the real native reclaim path.
        with engine.begin() as conn:
            conn.execute(
                update(table("ops.task"))
                .where(table("ops.task").c.id == task)
                .values(lease_until=text("clock_timestamp()-interval '1 second'"))
            )
        second = SemanticAgentSession(engine, run)
        async with Client(build_semantic_server(second)) as client:
            await lease_and_read(client, run, task, expect_previous=True)
            with pytest.raises(OperationConflict), engine.begin() as conn:
                hold_agent_result(
                    conn,
                    task_id=task,
                    attempt=first_attempt,
                    holder=first.holder,
                    packet_hash=packet,
                    clean=False,
                    result={},
                )
            terminal = (
                await client.call_tool("propose_claims", {"task_id": task, "batch": raw})
            ).structured_content
            assert terminal is not None
            assert (
                terminal["status"] == "done" and not terminal["task_open"] and terminal["rejected"]
            )
            repeated = (
                await client.call_tool("propose_claims", {"task_id": task, "batch": raw})
            ).structured_content
            assert repeated is not None
            assert repeated["status"] == "not_open"
            assert terminal["submission_disposition"] == (
                "completed_refused" if refused else "completed_accepted"
            )

    anyio.run(journey)
    with engine.connect() as conn:
        rows = (
            conn.execute(
                select(table("kb.observation")).where(table("kb.observation").c.task_id == task)
            )
            .mappings()
            .all()
        )
        assert len(rows) == 1
        if refused:
            from corpus_structure.semantic.observations import source_python

            assert (
                rows[0]["payload_definition"] == "SourceObservation"
                and rows[0]["kind"] == "semantic_proposal_refused"
            )
            original = source_python(rows[0]["payload"]["payload"])
            assert (
                original["authored"]["claims"][0]["predicate"] == "https://example.org/not-declared"
            )
        else:
            assert rows[0]["payload_definition"] == "AgentStoredBatch"
            evidence = rows[0]["payload"]["claims"][0]["evidence"][0]
            assert evidence["quote"] == fabricated and evidence["outcome"] in (
                "unlocated",
                "coarse",
            )
        envelope = conn.execute(
            select(table("ops.task_result").c.body).where(
                table("ops.task_result").c.task_id == task
            )
        ).scalar_one()
        assert envelope["first_result"]["attempt"] == 1 and envelope["result"]["issues"]
    from corpus_structure.orchestrate.commands import finalize_bound_run

    result = finalize_bound_run(engine, run, "evaluated-uncertain")
    with engine.connect() as conn:
        assert not conn.execute(
            select(table("data.fact").c.fact_id).where(
                table("data.fact").c.realization_id == result.realization_id,
                table("data.fact").c.property_id == "https://example.org/name",
            )
        ).first()
        assert conn.execute(
            select(table("data.coverage").c.coverage_id).where(
                table("data.coverage").c.realization_id == result.realization_id,
                table("data.coverage").c.family == ("claim_proposal" if refused else "claim"),
                table("data.coverage").c.outcome == ("failed" if refused else "partial"),
            )
        ).first()
