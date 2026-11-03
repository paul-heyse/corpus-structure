"""Serving scenarios with explicit seed identity and fresh native consumer clones."""

from __future__ import annotations

import hashlib
import inspect
import json
import os
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import anyio
import pytest
from fastmcp import Client
from pydantic import BaseModel
from sqlalchemy import insert, select, text
from sqlalchemy.engine import Engine

from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operation_results import RunId, TaskId
from corpus_structure.semantic.query_compatibility import acquire_query_inputs
from corpus_structure.semantic.types import PreparedRelease
from corpus_structure.settings import Settings
from native_test_support import (
    DatabasePolicy,
    PgAdmin,
    SemanticTemplate,
    principal_engine,
)

from .agent_scenarios import build_resubmission_case, lease_and_read


def build_completed_serving_case(
    admin, writer, tmp_path, *, complete_coverage=False, query_pack=None
):
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
            config = record_method(conn, method, "default", {}, "coverage-witness")
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
class ServingScenarioSeed:
    database: str
    database_oid: int
    policy: DatabasePolicy
    recipe_id: str
    source_manifest_digest: str
    prepared: PreparedRelease
    run: RunId
    task: TaskId
    locator: str

    @property
    def origin(self) -> dict[str, str]:
        return {
            "scenario": "serving.completed/default",
            "recipe_id": self.recipe_id,
            "source_database": self.database,
            "source_database_oid": str(self.database_oid),
            "release_id": self.prepared.release_id,
            "manifest_digest": self.source_manifest_digest,
        }


@dataclass(frozen=True)
class ServingReadScenario:
    prepared: PreparedRelease
    run: RunId
    task: TaskId
    locator: str
    reader: Engine
    seed_origin: dict[str, str]


def _serving_recipe_id(prepared: PreparedRelease) -> tuple[str, str]:
    manifest_digest = hashlib.sha256(prepared.manifest).hexdigest()
    source = (
        inspect.getsource(build_completed_serving_case)
        + inspect.getsource(build_resubmission_case)
        + inspect.getsource(lease_and_read)
    ).encode()
    recipe = hashlib.sha256(
        b"serving.completed/default/v1\0" + manifest_digest.encode() + b"\0" + source
    ).hexdigest()
    return recipe, manifest_digest


def _database_oid(server: PgAdmin, name: str) -> int:
    with server.connect() as conn:
        oid = conn.execute(
            text("SELECT oid FROM pg_database WHERE datname=:name"), {"name": name}
        ).scalar_one()
    if not isinstance(oid, int) or oid <= 0:
        raise AssertionError(f"database {name!r} has no positive observed OID")
    return oid


def _validate_serving_seed(server: PgAdmin, seed: ServingScenarioSeed) -> None:
    actual_oid = _database_oid(server, seed.database)
    if actual_oid != seed.database_oid:
        raise AssertionError("serving seed database OID no longer matches its recorded origin")
    if server.policy(seed.database) != seed.policy:
        raise AssertionError("serving seed policy no longer matches its recorded origin")
    recipe_id, manifest_digest = _serving_recipe_id(seed.prepared)
    if (recipe_id, manifest_digest) != (seed.recipe_id, seed.source_manifest_digest):
        raise AssertionError("serving seed recipe or prepared source identity changed")
    with server.connect() as conn:
        allowed, clients = conn.execute(
            text(
                "SELECT d.datallowconn, count(a.pid) "
                "FROM pg_database AS d LEFT JOIN pg_stat_activity AS a "
                "ON a.datid=d.oid AND a.pid<>pg_backend_pid() "
                "WHERE d.datname=:name GROUP BY d.datallowconn"
            ),
            {"name": seed.database},
        ).one()
    if allowed or clients:
        raise AssertionError("serving seed must be sealed against connections and client-free")


def _serving_seed_lifecycle(
    native_server: PgAdmin,
    semantic_head_template: SemanticTemplate,
    native_settings: Settings,
    tmp_path_factory: pytest.TempPathFactory,
    *,
    scenario_builder: Callable[..., tuple[PreparedRelease, RunId, TaskId, str]] = (
        build_completed_serving_case
    ),
) -> Iterator[ServingScenarioSeed]:
    name = f"cs_sem_test_{os.getpid()}_{uuid4().hex[:12]}"
    with native_server.database(
        name, semantic_head_template.name, policy=semantic_head_template.policy
    ) as admin:
        writer = principal_engine(native_settings, "write", name)
        try:
            prepared, run, task, locator = scenario_builder(
                admin, writer, tmp_path_factory.mktemp("serving-seed")
            )
        finally:
            writer.dispose()
            admin.dispose()

        seed_policy = native_server.policy(name)
        if seed_policy != semantic_head_template.policy:
            raise AssertionError("serving seed changed the deployed database policy")
        seed_oid = _database_oid(native_server, name)
        recipe_id, manifest_digest = _serving_recipe_id(prepared)
        seed = ServingScenarioSeed(
            database=name,
            database_oid=seed_oid,
            policy=seed_policy,
            recipe_id=recipe_id,
            source_manifest_digest=manifest_digest,
            prepared=prepared,
            run=run,
            task=task,
            locator=locator,
        )
        admin.dispose()
        with native_server.connect() as conn:
            quoted = conn.dialect.identifier_preparer.quote(name)
            conn.exec_driver_sql(f"ALTER DATABASE {quoted} ALLOW_CONNECTIONS false")
        _validate_serving_seed(native_server, seed)
        yield seed


@pytest.fixture(scope="session")
def serving_scenario_seed(
    native_server: PgAdmin,
    semantic_head_template: SemanticTemplate,
    native_settings: Settings,
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[ServingScenarioSeed]:
    yield from _serving_seed_lifecycle(
        native_server, semantic_head_template, native_settings, tmp_path_factory
    )


@pytest.fixture
def serving_read_scenario(
    serving_scenario_seed: ServingScenarioSeed,
    native_server: PgAdmin,
    native_settings: Settings,
) -> Iterator[ServingReadScenario]:
    seed = serving_scenario_seed
    _validate_serving_seed(native_server, seed)
    name = f"cs_sem_test_{os.getpid()}_{uuid4().hex[:12]}"
    with native_server.database(name, seed.database, policy=seed.policy) as admin:
        if native_server.policy(name) != seed.policy:
            raise AssertionError("scenario clone policy replay differs from its seed")
        clone_oid = _database_oid(native_server, name)
        if clone_oid == seed.database_oid:
            raise AssertionError("scenario consumer must own a fresh clone OID")
        release = table("data.realization")
        with admin.connect() as conn:
            actual_release = conn.execute(
                select(release.c.release_id).where(
                    release.c.project_id == "resubmit",
                    release.c.realization_id == "served-result",
                )
            ).scalar_one_or_none()
        if actual_release != seed.prepared.release_id:
            raise AssertionError("scenario clone does not contain the seeded serving realization")

        reader = principal_engine(native_settings, "read", name, scenario_seed=seed.origin)
        try:
            with reader.connect() as conn:
                database, observed_oid, current_user, session_user = conn.exec_driver_sql(
                    "SELECT current_database(), "
                    "(SELECT oid FROM pg_database WHERE datname=current_database()), "
                    "current_user, session_user"
                ).one()
            if (database, observed_oid) != (name, clone_oid):
                raise AssertionError("purpose connection did not acquire the owned scenario clone")
            if current_user != reader.url.username or session_user != reader.url.username:
                raise AssertionError(
                    "scenario reader did not authenticate as its actual purpose login"
                )
            yield ServingReadScenario(
                seed.prepared, seed.run, seed.task, seed.locator, reader, seed.origin
            )
        finally:
            reader.dispose()


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
