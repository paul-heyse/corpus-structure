"""Native semantic-run MCP dispatch with independent source-backed submissions; no regrading."""

import json
from pathlib import Path
from typing import Any

import anyio
import pytest
from fastmcp import Client
from mcp.types import TextContent
from sqlalchemy import insert, select

from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.orchestrate.semantic import queue_agent
from corpus_structure.semantic import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import (
    OperationBinding,
    create_run,
    create_task,
    register_document,
)
from corpus_structure.semantic.proposals import proposal_inputs
from corpus_structure.semantic.releases import persist_release


@pytest.mark.parametrize("producer_method", ["agent.opus", "agent.general"])
def test_native_tool_queue_read_schema_and_fenced_rich_submission(
    semantic_db_engine, semantic_writer_engine, tmp_path, producer_method
):
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = proposal_inputs(
        SourceBundle(
            "domain",
            (
                SourceArtifact("core", core.read_bytes()),
                SourceArtifact(
                    "domain",
                    b"""id: https://example.org/domain
name: domain
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
imports: [core]
classes:
 Person:
  is_a: Entity
  attributes:
   name: {range: string, annotations: {"cs:role": display}}
   exact: {range: decimal}
 Parameter:
  attributes:
   key: {identifier: true}
   amount: {range: decimal, required: true}
   owner: {range: Person, required: true}
 ScopedQualification:
  is_a: Qualification
  attributes:
   parameters: {range: Parameter, multivalued: true, inlined: true}
""",
                ),
            ),
        ),
        qualification_class="ScopedQualification",
    )
    from corpus_structure.semantic.analytical_profile import analytical_inputs
    from corpus_structure.semantic.composed import composed_dependencies

    bundle, dependencies = analytical_inputs(bundle, ResolvedDependencies())
    from .method_dimensions_support import fixture_execution_inputs

    dependencies = composed_dependencies(dependencies, fixture_execution_inputs('pdf.controlled-source'))
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(bundle, dependencies, profile)
    with semantic_db_engine.begin() as conn:
        persist_release(conn, bundle, dependencies, profile, prepared)
        conn.execute(insert(table("data.project")).values(project_id="mcp"))
        conn.execute(
            insert(table("data.realization")).values(
                project_id="mcp", realization_id="input", release_id=prepared.release_id
            )
        )
    raw = tmp_path / "source.html"
    cap = 512
    text = (
        "Alice has exact value 1.23456789012345678901234567890123456789 "
        + "with long source detail " * 40
        + "."
    )
    from pdf_acceptance_support import publish_controlled_pdf_views, write_controlled_pdf

    from corpus_structure.ingest.sentences import SentenceConfig

    original = write_controlled_pdf(raw, (text,))
    configuration = {
        "model": "declared-automated-agent",
        "mode": "extract",
        "max_units": 1,
        "packet_cap_chars": cap,
        "sentences": SentenceConfig().model_dump(mode="json"),
    }
    engine = semantic_writer_engine
    with engine.begin() as conn:
        run = create_run(
            conn,
            project_id="mcp",
            binding=OperationBinding(prepared.release_id, "input", 0, b"{}"),
            kind="full",
            options={"agent_configs": {f"{producer_method}/extract": configuration}},
            code_commit="native-mcp",
            guideline="Extract only what the source states.",
        )
        document = register_document(
            conn,
            project_id="mcp",
            source_uri="source.html",
            original_path=str(raw),
            original=original,
            metadata={"page": "source.html"},
            mime="application/pdf",
        )
    (view,) = publish_controlled_pdf_views(
        engine,
        prepared=prepared,
        run_id=run,
        document_id=document,
        original=original,
        paragraphs=(text,),
        keys=("source.html#detail",),
    )
    with engine.begin() as conn:
        locator = view.ref.key
        (agent_task,) = queue_agent(
            conn,
            run_id=run,
            prepared=prepared,
            configuration=configuration,
            method_name=producer_method,
            units=(UnitRef(TaskUnitType.SOURCE_VIEW, view.ref.id, locator),),
        )
    session = SemanticAgentSession(engine, run)
    server = build_semantic_server(session)

    refused_tasks = []

    async def journey():
        nonlocal agent_task
        async with Client(server) as client:
            queued = (await client.call_tool("queue_next", {"run": run})).structured_content
            assert queued is not None
            leased = queued["tasks"]
            assert [task["task_id"] for task in leased] == [agent_task]
            early = await client.call_tool(
                "propose_claims", {"task_id": agent_task, "batch": {"unit_ref": locator}}
            )
            assert early.structured_content is not None
            assert early.structured_content["status"] == "held"
            instructions = (
                await client.call_tool("read_instructions", {"task_id": agent_task})
            ).structured_content
            assert instructions is not None
            schema_hash = next(
                part["hash"] for part in instructions["parts"] if part["name"] == "schema"
            )
            for part in instructions["parts"]:
                for page in range(1, part["pages"] + 1):
                    await client.call_tool(
                        "read_instructions",
                        {"task_id": agent_task, "part": part["name"], "page": page},
                    )
            source_fragments = []
            for page in range(1, leased[0]["parts"] + 1):
                response = await client.call_tool(
                    "read_unit", {"task_id": agent_task, "part": page}
                )
                unit = response.structured_content
                assert unit is not None
                assert "sentences" not in unit
                assert len(unit["text"]) <= cap
                rendered = response.content[0]
                assert isinstance(rendered, TextContent)
                assert rendered.text == unit["text"]
                source_fragments.append(unit["text"])
            source_sentences = json.loads("".join(source_fragments))["sentences"]
            sid = next(item["id"] for item in source_sentences if item["text"] == text)
            batch: dict[str, Any] = {
                "unit_ref": locator,
                "entities": [{"id": "p", "class_iri": "https://example.org/Person"}],
                "claims": [
                    {
                        "id": "name",
                        "subject": "p",
                        "predicate": "https://example.org/name",
                        "object": {"kind": "text", "text": "Alice"},
                        "qualification": {"modality": "asserted", "polarity": True},
                        "establishment": "stated",
                        "evidence": [{"sentence": sid, "quote": text, "role": "primary"}],
                    }
                ],
            }
            from copy import deepcopy

            exact = "1.23456789012345678901234567890123456789"
            numerical = deepcopy(batch["claims"][0])
            numerical.update(
                id="exact",
                predicate="https://example.org/exact",
                object={"kind": "number", "number": exact},
            )
            batch["claims"].append(numerical)
            batch["claims"][0]["qualification"]["parameters"] = {
                "scale": {"key": "scale", "amount": exact, "owner": "p"}
            }
            rounded_map = deepcopy(batch)
            rounded_map["claims"][0]["qualification"]["parameters"]["scale"]["amount"] = float(
                exact
            )
            map_refused = (
                await client.call_tool(
                    "propose_claims", {"task_id": agent_task, "batch": rounded_map}
                )
            ).structured_content
            assert map_refused is not None and map_refused["status"] == "held"
            assert "binary floats" in map_refused["rejected"][0]["message"]
            with engine.connect() as conn:
                assert (
                    conn.execute(
                        select(table("ops.task").c.error).where(
                            table("ops.task").c.id == agent_task
                        )
                    ).scalar_one()
                    is not None
                ), map_refused
            unknown_reference = deepcopy(batch)
            unknown_reference["claims"][0]["qualification"]["parameters"]["scale"]["owner"] = (
                "missing"
            )
            reference_refused = (
                await client.call_tool(
                    "propose_claims", {"task_id": agent_task, "batch": unknown_reference}
                )
            ).structured_content
            assert reference_refused is not None
            if reference_refused["status"] != "done":
                raise AssertionError(json.dumps(reference_refused))
            assert not reference_refused["task_open"] and not any(
                reference_refused["accepted"].values()
            )
            assert "nested entity reference" in reference_refused["rejected"][0]["message"]
            refused_tasks.append(agent_task)
            # The original refused report is terminal. A fresh logical producer invocation
            # exercises the remaining decimal refusal and subsequent corrected rich report.
            with engine.begin() as conn:
                old = (
                    conn.execute(
                        select(table("ops.task")).where(table("ops.task").c.id == agent_task)
                    )
                    .mappings()
                    .one()
                )
                agent_task = create_task(
                    conn,
                    run_id=run,
                    config_id=old["method_config_id"],
                    stage="propose",
                    unit_type=old["unit_type"],
                    unit_id=old["unit_id"],
                    unit_key=old["unit_key"],
                    input_hash=old["input_hash"],
                    packet_hash=old["packet_hash"],
                    agent=True,
                    fresh=True,
                )
            fresh_queue = (await client.call_tool("queue_next", {"run": run})).structured_content
            assert fresh_queue is not None
            fresh_lease = fresh_queue["tasks"][0]
            fresh_manifest = (
                await client.call_tool("read_instructions", {"task_id": agent_task})
            ).structured_content
            assert fresh_manifest is not None
            for part in fresh_manifest["parts"]:
                for page in range(1, part["pages"] + 1):
                    await client.call_tool(
                        "read_instructions",
                        {"task_id": agent_task, "part": part["name"], "page": page},
                    )
            for part in range(1, fresh_lease["parts"] + 1):
                await client.call_tool("read_unit", {"task_id": agent_task, "part": part})
            rounded = deepcopy(batch)
            rounded["claims"][1]["object"]["number"] = float(exact)
            refused = (
                await client.call_tool("propose_claims", {"task_id": agent_task, "batch": rounded})
            ).structured_content
            assert refused is not None and refused["status"] == "held"
            assert "binary floats" in refused["rejected"][0]["message"]
            submitted = (
                await client.call_tool(
                    "propose_claims",
                    {"task_id": agent_task, "batch": batch, "schema_hash": schema_hash},
                )
            ).structured_content
            assert submitted is not None
            assert submitted["status"] == "done", submitted
            assert submitted["accepted"]["claims"] == 2
            repeated = (
                await client.call_tool("propose_claims", {"task_id": agent_task, "batch": batch})
            ).structured_content
            assert repeated is not None
            assert repeated["status"] == "not_open"
            assert not repeated["task_open"]

    anyio.run(journey)
    with engine.connect() as conn:
        observations = table("kb.observation")
        refused = (
            conn.execute(select(observations).where(observations.c.task_id == refused_tasks[0]))
            .mappings()
            .one()
        )
        assert (
            refused["payload_definition"] == "SourceObservation"
            and refused["kind"] == "semantic_proposal_refused"
        )
        envelope = conn.execute(
            select(table("ops.task_result").c.body).where(
                table("ops.task_result").c.task_id == refused_tasks[0]
            )
        ).scalar_one()
        assert envelope["result"]["execution_identity"]["binding"]["method"] == producer_method
        assert envelope["result"]["execution_identity"]["assurance"] == "manual_operator"
        assert (
            envelope["coverage"][0]["outcome"] == "failed"
            and envelope["first_result"]["result"]["issues"]
        )
        from corpus_structure.semantic.observations import source_python

        first_authored = source_python(envelope["first_result"]["result"]["authored"])
        assert (
            first_authored["claims"][0]["qualification"]["parameters"]["scale"]["amount"].hex()
            == float("1.23456789012345678901234567890123456789").hex()
        )
        row = (
            conn.execute(select(observations).where(observations.c.task_id == agent_task))
            .mappings()
            .one()
        )
        assert row["payload_definition"] == "AgentStoredBatch"
        evidence = row["payload"]["claims"][0]["evidence"][0]
        assert (evidence["start"], evidence["end"], evidence["outcome"]) == (
            0,
            len(text),
            "located",
        )
        assert row["payload"]["claims"][0]["object"] == {"kind": "text", "text": "Alice"}
        assert row["payload"]["claims"][1]["object"] == {
            "kind": "number",
            "number": "1.23456789012345678901234567890123456789",
        }

        assert (
            row["payload"]["claims"][0]["qualification"]["parameters"]["scale"]["amount"]
            == "1.23456789012345678901234567890123456789"
        )
