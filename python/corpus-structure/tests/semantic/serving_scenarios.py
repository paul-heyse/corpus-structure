"""Serving scenarios with explicit seed identity and fresh native consumer clones."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import anyio
import pytest
from fastmcp import Client
from pydantic import BaseModel
from scenario_recipes import register_scenario_builder
from sqlalchemy import insert, select
from sqlalchemy.engine import Engine

from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operation_results import RunId, TaskId
from corpus_structure.semantic.query_compatibility import acquire_query_inputs
from corpus_structure.semantic.types import PreparedRelease
from native_scenario_seeds import ScenarioSeed, SeedClone

from .agent_scenarios import build_resubmission_case, lease_and_read


def build_completed_serving_case(
    admin: Engine,
    writer: Engine,
    tmp_path: Path,
    *,
    complete_coverage: bool = False,
    query_pack: Path | None = None,
) -> tuple[PreparedRelease, RunId, TaskId, str]:
    prepared, run, task, locator = build_resubmission_case(
        admin,
        writer,
        tmp_path / "source.html",
        composed=True,
        domain="statistics",
        query_inputs=acquire_query_inputs(
            query_pack or Path(__file__).resolve().parents[4] / "domains/statistics"
        ),
    )

    async def submit():
        async with Client(build_semantic_server(SemanticAgentSession(writer, run))) as client:
            unit = await lease_and_read(client, run, task)
            claims = [
                {
                    "id": item,
                    "subject": "person2" if name == "Bob" else "person",
                    "predicate": "https://example.org/name",
                    "object": {"kind": "text", "text": name},
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
                for item, name in [("name1", "Alice"), ("name2", "Alice"), ("name3", "Bob")]
            ]
            result = await client.call_tool(
                "propose_claims",
                {
                    "task_id": task,
                    "batch": {
                        "unit_ref": locator,
                        "entities": [
                            {"id": "person", "class_iri": "https://example.org/Person"},
                            {"id": "person2", "class_iri": "https://example.org/Person"},
                        ],
                        "claims": claims,
                    },
                },
            )
            assert result.structured_content is not None
            assert result.structured_content["submission_disposition"] == "completed_accepted", (
                json.dumps(result.structured_content, sort_keys=True)
            )

    anyio.run(submit)
    if complete_coverage:
        from types import SimpleNamespace

        from corpus_structure.core.method import CoverageDraft, UnitRef, UnitResult
        from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
        from corpus_structure.semantic.operations import (
            claim_tasks,
            complete_unit_result,
            create_task,
            record_method,
        )

        class WitnessConfig(BaseModel):
            pass

        method = SimpleNamespace(
            name="coverage.witness",
            version="1",
            family="extract",
            tier="deterministic",
            unit_type=TaskUnitType.RUN,
            Config=WitnessConfig,
            confidence_source=None,
        )
        with writer.begin() as conn:
            config = record_method(
                conn, method, "default", {}, "coverage-witness", prepared=prepared
            )
            task_id = create_task(
                conn,
                run_id=run,
                config_id=config,
                stage="extract",
                unit_type="run",
                unit_key="global",
                input_hash="coverage-witness",
            )
            claimed = claim_tasks(conn, run_id=run, config_id=config, holder="coverage-witness")[0]
            complete_unit_result(
                conn,
                task_id=task_id,
                attempt=claimed.attempt,
                holder="coverage-witness",
                prepared=prepared,
                method=method,
                configuration_hash="coverage-witness",
                source="coverage-witness",
                result=UnitResult(
                    ref=UnitRef(TaskUnitType.RUN, unit_key="global"),
                    outcome=ObservationOutcome.EMPTY,
                    coverage=(
                        CoverageDraft(
                            family="https://example.org/name",
                            scope="*",
                            outcome="complete",
                        ),
                    ),
                ),
            )
    finalize_bound_run(writer, run, "served-result")
    return prepared, run, task, locator


@dataclass(frozen=True)
class ServingRecipe:
    complete_coverage: bool = False

    @property
    def label(self) -> str:
        return (
            "serving.completed/coverage" if self.complete_coverage else "serving.completed/default"
        )


@dataclass(frozen=True)
class ServingStage:
    prepared: PreparedRelease
    run: RunId
    task: TaskId
    locator: str
    manifest_digest: str
    seed_files: tuple[Path, ...]

    @property
    def seed_origin(self) -> dict[str, str]:
        return {"release_id": self.prepared.release_id, "manifest_digest": self.manifest_digest}

    def validate_clone(self, admin: Engine) -> None:
        if hashlib.sha256(self.prepared.manifest).hexdigest() != self.manifest_digest:
            raise RuntimeError("serving prepared source identity changed")
        release = table("data.realization")
        with admin.connect() as connection:
            actual = connection.execute(
                select(release.c.release_id).where(
                    release.c.project_id == "resubmit",
                    release.c.realization_id == "served-result",
                )
            ).scalar_one_or_none()
        if actual != self.prepared.release_id:
            raise RuntimeError("scenario clone lacks the seeded serving realization")


def build_serving_recipe(
    recipe: ServingRecipe, admin: Engine, writer: Engine, directory: Path, *, purpose_engine=None
) -> ServingStage:
    prepared, run, task, locator = build_completed_serving_case(
        admin, writer, directory, complete_coverage=recipe.complete_coverage
    )
    return ServingStage(
        prepared,
        run,
        task,
        locator,
        hashlib.sha256(prepared.manifest).hexdigest(),
        (directory / "source.html",),
    )


register_scenario_builder(ServingRecipe, build_serving_recipe)


@pytest.fixture(scope="session")
def serving_scenario_seed(scenario_seeds) -> ScenarioSeed[ServingStage]:
    return scenario_seeds.seed(ServingRecipe())


@pytest.fixture
def serving_read_scenario(
    serving_scenario_seed, scenario_seeds
) -> Iterator[SeedClone[ServingStage]]:
    with scenario_seeds.commit_clone(serving_scenario_seed.recipe) as clone:
        yield clone


def install_pack_scenario(admin, writer, name, entries, *, contexts=False):
    from dataclasses import replace

    from corpus_structure.semantic.consolidation import SourceItem, assemble
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.publication import EvidenceRow, SelectionRow, publish_batch
    from corpus_structure.semantic.regeneration import prepare_packs
    from corpus_structure.semantic.releases import persist_release

    root = Path(__file__).resolve().parents[4]
    bundle, dependencies, profile, prepared = prepare_packs((root / f"domains/{name}",))
    with admin.begin() as conn:
        persist_release(conn, bundle, dependencies, profile, prepared)
        conn.execute(insert(table("data.project")).values(project_id="pack"))
        conn.execute(
            insert(table("data.realization")).values(
                project_id="pack", realization_id="pack", release_id=prepared.release_id
            )
        )
    if callable(entries):
        entries = entries(prepared)
    entries = list(entries) + [
        (subject, cls, "id", subject, {"modality": "asserted", "polarity": True}, "Qualification")
        for subject, cls in sorted({(row[0], row[1]) for row in entries})
    ]
    evidence = (EvidenceRow("pack-evidence", "pack.html", "pack.html#p", "native-parser", "1"),)
    items = tuple(
        SourceItem(
            subject, cls, prop, obj, qualification, "pack-source", str(i), "stated", evidence, qcls
        )
        for i, (subject, cls, prop, obj, qualification, qcls) in enumerate(entries)
    )
    batch = assemble(prepared, "pack", "pack-test", items)
    if contexts:
        from corpus_structure.semantic.publication import OccurrenceContextRow

        batch = replace(
            batch,
            occurrence_context=tuple(
                OccurrenceContextRow(
                    o.occurrence_id,
                    "stmt",
                    "definiens"
                    if items[int(o.item)].property_name == "defined_as"
                    else "premise"
                    if items[int(o.item)].qualification["modality"] == "supposed"
                    else "conclusion",
                )
                for o in batch.occurrence
                if items[int(o.item)].subject in {"rv0", "rv1"}
                and items[int(o.item)].property_name in {"has_distribution", "defined_as"}
            ),
        )
    batch = replace(
        batch, selection=tuple(SelectionRow(f.fact_id) for f in batch.fact)
    ).bind_preparation(prepared)
    publish_batch(writer, batch)
    return prepared, batch
