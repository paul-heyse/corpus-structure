"""A supported bound input referent survives the actual MCP packet and fresh evaluation."""

import json
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import anyio
import yaml
from fastmcp import Client
from pydantic import BaseModel
from sqlalchemy import insert, select
from typer.testing import CliRunner

from corpus_structure.core.evidence import RenditionContent, Segment
from corpus_structure.core.locators import LocatorIndex
from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import SegmentKind, TaskUnitType
from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.orchestrate.semantic import agent_packet, queue_agent
from corpus_structure.semantic import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.analytical_profile import analytical_inputs
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.consolidation import SourceItem, assemble
from corpus_structure.semantic.domain_operations import domain_rule_inputs
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import observation_inputs
from corpus_structure.semantic.operations import (
    OperationBinding,
    claim_tasks,
    complete_task,
    create_run,
    create_task,
    record_method,
    register_document,
    store_rendition,
)
from corpus_structure.semantic.proposals import proposal_inputs
from corpus_structure.semantic.publication import EvidenceRow, SelectionRow, publish_batch
from corpus_structure.semantic.releases import persist_release


def test_native_known_reference_packet_mcp_and_finalizer(
    semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch
):
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    domain = {
        "id": "https://example.org/known",
        "name": "known",
        "imports": ["core"],
        "prefixes": {"ex": "https://example.org/"},
        "default_prefix": "ex",
        "classes": {
            "Person": {
                "is_a": "Entity",
                "annotations": {"cs:scope": "global"},
                "attributes": {"name": {"range": "string"}},
            }
        },
    }
    deps = domain_rule_inputs(ResolvedDependencies(), b"rules: []")
    bundle = SourceBundle(
        "known",
        (
            SourceArtifact("core", core.read_bytes()),
            SourceArtifact("known", yaml.safe_dump(domain).encode()),
        ),
    )
    bundle = observation_inputs(proposal_inputs(bundle, deps))
    bundle, deps = analytical_inputs(bundle, deps)
    deps = composed_dependencies(deps)
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(bundle, deps, profile)
    with semantic_db_engine.begin() as conn:
        persist_release(conn, bundle, deps, profile, prepared)
        conn.execute(insert(table("data.project")).values(project_id="known"))
        conn.execute(
            insert(table("data.realization")).values(
                realization_id="input", project_id="known", release_id=prepared.release_id
            )
        )
    evidence = (EvidenceRow("input-evidence", "source.html", "source.html#source", "source", "1"),)
    item = SourceItem(
        "known-alice",
        "Person",
        "id",
        "known-alice",
        {"modality": "asserted", "polarity": True},
        "source",
        "id",
        "stated",
        evidence,
    )
    batch = assemble(
        prepared,
        "input",
        "bootstrap",
        (
            item,
            replace(item, property_name="label", object="Alice", item="label"),
            replace(item, property_name="aliases", object="A. Example", item="alias"),
            replace(item, property_name="name", object="Alice", item="name"),
        ),
    )
    batch = replace(
        batch, selection=tuple(SelectionRow(row.fact_id) for row in batch.fact)
    ).bind_preparation(prepared)
    publish_batch(semantic_writer_engine, batch)
    text = "Alice is here."
    path = tmp_path / "source.html"
    path.write_text("<p>" + text + "</p>")
    sentence = Segment(kind=SegmentKind.SENTENCE, start=0, end=len(text))
    paragraph = Segment(kind=SegmentKind.PARAGRAPH, start=0, end=len(text), children=(sentence,))
    content = RenditionContent(
        canonical_text=text,
        document=Segment(kind=SegmentKind.DOCUMENT, start=0, end=len(text), children=(paragraph,)),
    )
    locator = str(LocatorIndex(content, "source.html").generate(paragraph))
    configuration = {
        "model": "automated-test-agent",
        "mode": "extract",
        "max_units": 1,
        "packet_cap_chars": 18000,
    }
    e = semantic_writer_engine
    with e.begin() as conn:
        run = create_run(
            conn,
            project_id="known",
            binding=OperationBinding(prepared.release_id, "input", 1, b"{}"),
            kind="full",
            options={"agent_configs": {"extract": configuration}},
            code_commit="native-known",
        )
        document = register_document(
            conn,
            project_id="known",
            source_uri="source.html",
            original_path=str(path),
            original=path.read_bytes(),
            metadata={"page": "source.html"},
         mime='text/html')

        class SourceConfig(BaseModel):
            pass

        config = record_method(
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
        task = create_task(
            conn, run_id=run, config_id=config, stage="ingest", unit_type="run", input_hash="input"
        )
        claim = claim_tasks(conn, run_id=run, config_id=config, holder="source")[0]
        rendition = store_rendition(
            conn,
            run_id=run,
            document_id=document,
            content=content,
            task_id=task,
            config_id=config,
            parse_detail={},
        )
        complete_task(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="source",
            prepared=prepared,
            observations=[],
            outcome="empty",
        )
        segment = conn.execute(
            select(table("kb.segment").c.id).where(
                table("kb.segment").c.rendition_id == rendition,
                table("kb.segment").c.kind == "paragraph",
            )
        ).scalar_one()
        (agent,) = queue_agent(
            conn,
            run_id=run,
            prepared=prepared,
            configuration=configuration,
            units=(UnitRef(TaskUnitType.SEGMENT, segment, locator),),
        )
        packet = agent_packet(conn, run, agent, prepared)
        assert dict(packet.known_classes)["known-alice"] == ("https://example.org/Person",)
        assert packet.known_entities[0].label == "Alice" and packet.known_entities[0].aliases == (
            "A. Example",
        )
        assert not packet.bootstrap_terms
    server = build_semantic_server(SemanticAgentSession(e, run))

    async def journey():
        async with Client(server) as client:
            queue = (await client.call_tool("queue_next", {"run": run})).structured_content
            assert queue is not None
            leased = queue["tasks"][0]
            manifest = (
                await client.call_tool("read_instructions", {"task_id": agent})
            ).structured_content
            assert manifest is not None
            for part in manifest["parts"]:
                for page in range(1, part["pages"] + 1):
                    await client.call_tool(
                        "read_instructions", {"task_id": agent, "part": part["name"], "page": page}
                    )
            bodies = []
            for page in range(1, leased["parts"] + 1):
                result = await client.call_tool("read_unit", {"task_id": agent, "part": page})
                assert result.structured_content is not None
                bodies.append(result.structured_content["text"])
                assert "sentences" not in result.structured_content
            authored = json.loads("".join(bodies))
            assert authored["known_entities"][0]["entity_id"] == "known-alice"
            sid = next(
                sentence["id"] for sentence in authored["sentences"] if sentence["text"] == text
            )
            raw = {
                "unit_ref": locator,
                "entities": [],
                "claims": [
                    {
                        "id": "name",
                        "subject": "known-alice",
                        "predicate": "https://example.org/name",
                        "object": {"kind": "text", "text": "Alice"},
                        "qualification": {"modality": "asserted", "polarity": True},
                        "establishment": "stated",
                        "evidence": [{"sentence": sid, "quote": text, "role": "primary"}],
                    }
                ],
            }
            result = (
                await client.call_tool("propose_claims", {"task_id": agent, "batch": raw})
            ).structured_content
            assert result is not None
            assert result["status"] == "done", result

    anyio.run(journey)
    from corpus_structure.cli import orchestrate as cli
    from corpus_structure.cli.app import app

    @contextmanager
    def engine(_, **kwargs):
        yield e

    monkeypatch.setattr(cli, "ENGINE", engine)
    finalized = CliRunner().invoke(
        app, ["run", "finalize", str(run), "--output-realization", "evaluated-known", "--json"]
    )
    assert finalized.exit_code == 0, (finalized.output, finalized.exception)
    result = json.loads(finalized.stdout)
    assert result["receipt"]["data_revision"] == 1
    with e.connect() as conn:
        lineage = (
            conn.execute(
                select(table("data.entity_input")).where(
                    table("data.entity_input").c.realization_id == "evaluated-known"
                )
            )
            .mappings()
            .all()
        )
        assert any(row["input_entity_id"] == "known-alice" for row in lineage)
        claims = (
            conn.execute(
                select(table("data.fact").c.subject_id).where(
                    table("data.fact").c.realization_id == "evaluated-known",
                    table("data.fact").c.property_id == "https://example.org/name",
                )
            )
            .scalars()
            .all()
        )
        assert claims == ["known-alice"]
