"""Native semantic-run MCP dispatch with independent source-backed submissions; no regrading."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import anyio
from fastmcp import Client
from sqlalchemy import insert, select

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
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import (
    OperationBinding,
    create_run,
    create_task,
    record_method,
    register_document,
    store_rendition,
)
from corpus_structure.semantic.proposals import proposal_inputs
from corpus_structure.semantic.releases import persist_release


def test_native_tool_queue_read_schema_and_fenced_rich_submission(
    semantic_db_engine, semantic_writer_engine, tmp_path
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
   name: {range: string}
   exact: {range: decimal}
""",
                ),
            ),
        )
    )
    prepared = prepare_release(bundle)
    with semantic_db_engine.begin() as conn:
        persist_release(conn, bundle, ResolvedDependencies(), PreparationProfile(), prepared)
        conn.execute(insert(table("data.project")).values(project_id="mcp"))
        conn.execute(
            insert(table("data.realization")).values(
                project_id="mcp", realization_id="input", release_id=prepared.release_id
            )
        )
    raw = tmp_path / "source.html"
    text = "Alice has exact value 1.23456789012345678901234567890123456789."
    raw.write_text("<p>" + text + "</p>", encoding="utf-8")
    sentence = Segment(kind=SegmentKind.SENTENCE, start=0, end=len(text))
    paragraph = Segment(kind=SegmentKind.PARAGRAPH, start=0, end=len(text), children=(sentence,))
    content = RenditionContent(
        canonical_text=text,
        document=Segment(kind=SegmentKind.DOCUMENT, start=0, end=len(text), children=(paragraph,)),
    )
    locator = str(LocatorIndex(content, "source.html").generate(paragraph))
    engine = semantic_writer_engine
    with engine.begin() as conn:
        run = create_run(
            conn,
            project_id="mcp",
            binding=OperationBinding(prepared.release_id, "input", 0, b"{}"),
            kind="full",
            options={'agent_configs':{'extract':{
                'model':'declared-automated-agent','mode':'extract','max_units':1,'packet_cap_chars':18000,
            }}},
            code_commit="native-mcp",
            guideline="Extract only what the source states.",
        )
        config = record_method(
            conn,
            SimpleNamespace(
                name="ingest",
                version="1",
                family="ingest",
                tier="deterministic",
                confidence_source=None,
            ),
            "default",
            {},
            "config:source",
        )
        task = create_task(
            conn, run_id=run, config_id=config, stage="ingest", unit_type="run", input_hash="source"
        )
        document = register_document(
            conn,
            project_id="mcp",
            source_uri="source.html",
            original_path=str(raw),
            original=raw.read_bytes(),
            metadata={"page": "source.html"},
        )
        rendition = store_rendition(
            conn,
            run_id=run,
            document_id=document,
            content=content,
            task_id=task,
            config_id=config,
            parse_detail={},
        )
        segments = table("kb.segment")
        segment = conn.execute(
            select(segments.c.id).where(
                segments.c.rendition_id == rendition, segments.c.kind == "paragraph"
            )
        ).scalar_one()
        (agent_task,) = queue_agent(
            conn,
            run_id=run,
            prepared=prepared,
            configuration={
                "model": "declared-automated-agent",
                "mode": "extract",
                "max_units": 1,
                "packet_cap_chars": 18000,
            },
            units=(UnitRef(TaskUnitType.SEGMENT, segment, locator),),
        )
    session = SemanticAgentSession(engine, run)
    server = build_semantic_server(session)

    async def journey():
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
            source_sentences = []
            for page in range(1, leased[0]["parts"] + 1):
                unit = (
                    await client.call_tool("read_unit", {"task_id": agent_task, "part": page})
                ).structured_content
                assert unit is not None
                source_sentences.extend(unit["sentences"])
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
