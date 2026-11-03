"""Native source/task scenarios shared by semantic acceptance cases."""

import json
from pathlib import Path
from typing import Any

import yaml
from fastmcp import Client
from sqlalchemy import Engine, insert

from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
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
from corpus_structure.semantic.operation_results import RunId, TaskId
from corpus_structure.semantic.operations import (
    OperationBinding,
    create_run,
    register_document,
)
from corpus_structure.semantic.proposals import proposal_inputs
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.types import PreparedRelease


def build_resubmission_case(
    admin: Engine,
    engine: Engine,
    path: Path,
    *,
    composed: bool = False,
    identity_keyed: bool = False,
    global_names: bool = False,
    domain: str | None = None,
    evaluation_policy: bytes | None = None,
    query_inputs: tuple[SourceArtifact, ...] = (),
) -> tuple[PreparedRelease, RunId, TaskId, str]:
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
    if query_inputs:
        deps = ResolvedDependencies(
            (*deps.artifacts, *query_inputs), deps.vocabularies, deps.ontology_sources
        )
    if evaluation_policy is not None:
        deps = ResolvedDependencies(
            (*deps.artifacts, SourceArtifact("operation/evaluation-split.yaml", evaluation_policy)),
            deps.vocabularies,
            deps.ontology_sources,
        )
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
    profile = PreparationProfile(version="semantic-2")
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
    from pdf_acceptance_support import publish_controlled_pdf_views, write_controlled_pdf

    paragraphs = ("Alice is here.",)
    original = write_controlled_pdf(path, paragraphs)
    from corpus_structure.ingest.sentences import SentenceConfig

    config = {
        "model": "automated-resubmission",
        "mode": "extract",
        "max_units": 1,
        "packet_cap_chars": 18000,
        "sentences": SentenceConfig().model_dump(mode="json"),
    }
    with engine.begin() as conn:
        run = create_run(
            conn,
            project_id="resubmit",
            binding=OperationBinding(prepared.release_id, "input", 0, b"{}"),
            kind="full",
            options={
                "agent_configs": {"agent.opus/extract": config},
                **({"domain": domain} if domain is not None else {}),
            },
            code_commit="test",
        )
        document = register_document(
            conn,
            project_id="resubmit",
            source_uri="source.html",
            original_path=str(path),
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
        paragraphs=paragraphs,
        keys=("source.html#people",),
    )
    with engine.begin() as conn:
        locator = view.ref.key
        (task,) = queue_agent(
            conn,
            run_id=run,
            prepared=prepared,
            configuration=config,
            units=(UnitRef(TaskUnitType.SOURCE_VIEW, view.ref.id, locator),),
        )
    return prepared, run, task, locator


async def lease_and_read(
    client: Client, run: RunId, task: TaskId, *, expect_previous: bool = False
) -> dict[str, Any]:
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
