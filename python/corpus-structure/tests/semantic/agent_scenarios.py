"""Native source/task scenarios shared by semantic acceptance cases."""

import json
from dataclasses import dataclass
from functools import cache
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import anyio
import yaml
from fastmcp import Client
from pydantic import create_model
from scenario_recipes import register_scenario_builder
from sqlalchemy import Engine, insert, select, text

from corpus_structure.core.method import SourceViewDraft, UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.orchestrate.semantic import propose_agents, queue_agent
from corpus_structure.semantic import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic._operation_ids import DocumentId
from corpus_structure.semantic.analytical_profile import analytical_inputs
from corpus_structure.semantic.contracts import implementation_overridden
from corpus_structure.semantic.domain_operations import domain_rule_inputs
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operation_results import MethodConfigId, RunId, TaskId
from corpus_structure.semantic.operations import (
    OperationBinding,
    claim_tasks,
    complete_task,
    create_run,
    create_task,
    record_method,
    register_document,
)
from corpus_structure.semantic.pdf_contracts import prepare_pdf_product, store_pdf_original
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.proposals import proposal_inputs
from corpus_structure.semantic.releases import activate_release, persist_release
from corpus_structure.semantic.source_views import store_source_view
from corpus_structure.semantic.types import PreparedRelease
from semantic.native_record_fixtures import publish_native_record_fixture, qualified_view_draft
from semantic.scenario_preparation_support import PersistedScenario, ScenarioPreparation


@dataclass(frozen=True)
class ResubmissionPreparationRecipe:
    identity_keyed: bool = False
    global_names: bool = False
    evaluation_policy: bytes | None = None
    query_inputs: tuple[SourceArtifact, ...] = ()


def _assemble_resubmission_preparation(
    recipe: ResubmissionPreparationRecipe,
) -> ScenarioPreparation[ResubmissionPreparationRecipe]:
    identity_keyed = recipe.identity_keyed
    global_names = recipe.global_names
    evaluation_policy = recipe.evaluation_policy
    query_inputs = recipe.query_inputs
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
    from semantic.method_dimensions_support import fixture_execution_inputs

    deps = composed_dependencies(
        deps, fixture_execution_inputs("pdf.controlled-source", "coverage.witness")
    )
    from corpus_structure.semantic.characterization import characterization_inputs

    bundle = characterization_inputs(bundle)
    prepared = prepare_release(bundle, deps, profile)
    return ScenarioPreparation(recipe, bundle, deps, profile, prepared)


_cached_resubmission_preparation = cache(_assemble_resubmission_preparation)


def prepare_resubmission_case(
    recipe: ResubmissionPreparationRecipe,
) -> ScenarioPreparation[ResubmissionPreparationRecipe]:
    """Reuse the pure input assembly; overrides leave the ordinary memo untouched."""
    if implementation_overridden():
        return _assemble_resubmission_preparation(recipe)
    return _cached_resubmission_preparation(recipe)


def persist_resubmission_release(
    admin: Engine,
    engine: Engine,
    preparation: ScenarioPreparation[ResubmissionPreparationRecipe],
    *,
    composed: bool = False,
) -> PersistedScenario[ResubmissionPreparationRecipe]:
    """Persist only the release/project stage, without PDF publication or task creation."""
    bundle, deps, profile, prepared = (
        preparation.bundle,
        preparation.dependencies,
        preparation.profile,
        preparation.prepared,
    )
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
    return PersistedScenario(preparation, engine)


@dataclass(frozen=True)
class ResubmissionRecipe:
    preparation: ResubmissionPreparationRecipe = ResubmissionPreparationRecipe()
    composed: bool = False
    domain: str | None = None
    model: str = "automated-resubmission"


@dataclass(frozen=True)
class ResubmissionSourceStage:
    preparation: ScenarioPreparation[ResubmissionPreparationRecipe]
    document: DocumentId
    run: RunId
    view: Any
    configuration: bytes

    @property
    def seed_files(self) -> tuple[Path, ...]:
        return ()

    def validate_clone(self, admin: Engine) -> None:
        from corpus_structure.semantic.operations import read_original

        documents, artifacts = table("kb.document"), table("kb.source_artifact")
        with admin.connect() as connection:
            retained = connection.scalar(
                select(artifacts.c.artifact_digest)
                .select_from(
                    documents.join(
                        artifacts, artifacts.c.artifact_digest == documents.c.content_hash
                    )
                )
                .where(documents.c.id == self.document)
            )
            if retained is None:
                raise ValueError("resubmission seed has no retained original")
            read_original(connection, self.document, prepared=self.preparation.prepared)


@dataclass(frozen=True)
class QueuedResubmissionStage:
    source: ResubmissionSourceStage
    run: RunId
    task: Any
    locator: str

    @property
    def result(self) -> tuple[PreparedRelease, RunId, TaskId, str]:
        return self.source.preparation.prepared, self.run, self.task, self.locator

    @property
    def seed_files(self) -> tuple[Path, ...]:
        return self.source.seed_files

    def validate_clone(self, admin: Engine) -> None:
        self.source.validate_clone(admin)
        task = table("ops.task")
        with admin.connect() as connection:
            state = connection.execute(
                select(
                    task.c.run_id,
                    task.c.status,
                    task.c.attempt,
                    task.c.claimed_by,
                    task.c.lease_until,
                ).where(task.c.id == self.task)
            ).one_or_none()
        if state != (self.run, "awaiting_agent", 0, None, None):
            raise ValueError("resubmission seed task is claimed or differs")


def publish_resubmission_source(
    preparation, engine, path, *, model="automated-resubmission", domain=None, fresh=False
):
    prepared = preparation.prepared
    from pdf_acceptance_support import publish_controlled_pdf_views, write_controlled_pdf

    paragraphs = ("Alice is here.",)
    original = write_controlled_pdf(path, paragraphs)
    from corpus_structure.ingest.sentences import SentenceConfig

    config = {
        "model": model,
        "mode": "extract",
        "max_units": 1,
        "packet_cap_chars": 18000,
        "sentences": SentenceConfig().model_dump(mode="json"),
    }
    with engine.begin() as conn:
        run = create_run(
            conn,
            project_id="resubmit",
            binding=OperationBinding(
                prepared.release_id,
                "input",
                0,
                canonical_bytes(
                    {
                        "operations": {},
                        "agent_configurations": {"agent.opus/extract": config},
                    }
                ),
            ),
            kind="full",
            options={
                "agent_configs": {"agent.opus/extract": config},
                **({"domain": domain} if domain is not None else {}),
                **({"fresh": ["agent.opus"]} if fresh else {}),
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
    )
    return ResubmissionSourceStage(preparation, document, run, view, canonical_bytes(config))


def queue_resubmission_agent(source, engine):
    prepared, run, view, config = (
        source.preparation.prepared,
        source.run,
        source.view,
        json.loads(source.configuration),
    )
    from semantic.primary_native_support import bind_primary_agent_run

    with engine.begin() as conn:
        run, config = bind_primary_agent_run(conn, run, prepared, (view.ref.id,), config)
        locator = view.ref.key
        (task,) = queue_agent(
            conn,
            run_id=run,
            prepared=prepared,
            configuration=config,
            units=(UnitRef(TaskUnitType.SOURCE_VIEW, view.ref.id, locator),),
        )
    return QueuedResubmissionStage(source, run, task, locator)


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
    model: str = "automated-resubmission",
) -> tuple[PreparedRelease, RunId, TaskId, str]:
    preparation = prepare_resubmission_case(
        ResubmissionPreparationRecipe(
            identity_keyed=identity_keyed,
            global_names=global_names,
            evaluation_policy=evaluation_policy,
            query_inputs=query_inputs,
        )
    )
    prepared = preparation.prepared
    persist_resubmission_release(admin, engine, preparation, composed=composed)
    source = publish_resubmission_source(preparation, engine, path, model=model, domain=domain)
    queued = queue_resubmission_agent(source, engine)
    return prepared, queued.run, queued.task, queued.locator


@dataclass(frozen=True)
class ResubmissionSourceRecipe:
    case: ResubmissionRecipe = ResubmissionRecipe()


def build_resubmission_source_recipe(recipe, admin, writer, directory, *, purpose_engine=None):
    case = recipe.case
    preparation = prepare_resubmission_case(case.preparation)
    persist_resubmission_release(admin, writer, preparation, composed=case.composed)
    return publish_resubmission_source(
        preparation,
        writer,
        directory / "source.pdf",
        model=case.model,
        domain=case.domain,
    )


def build_resubmission_recipe(recipe, admin, writer, directory, *, purpose_engine=None):
    source = build_resubmission_source_recipe(
        ResubmissionSourceRecipe(recipe),
        admin,
        writer,
        directory,
        purpose_engine=purpose_engine,
    )
    return queue_resubmission_agent(source, writer)


register_scenario_builder(ResubmissionSourceRecipe, build_resubmission_source_recipe)

register_scenario_builder(ResubmissionRecipe, build_resubmission_recipe)


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


def native_build_resubmission_case(admin, writer, tmp_path, *, ancestor=False):
    from docling_core.types.doc import DocItemLabel, DoclingDocument, GroupLabel

    from corpus_structure.ingest.pdf import PdfConversion, publication_payload
    from corpus_structure.ingest.pdf_hierarchy import snapshot
    from corpus_structure.semantic.composed import composed_dependencies

    schema = dict(
        id="https://example.org/native-person",
        name="native_person",
        imports=["core"],
        prefixes={"ex": "https://example.org/"},
        default_prefix="ex",
        classes={"Person": {"is_a": "Entity", "attributes": {"name": {"range": "string"}}}},
    )
    dependencies = domain_rule_inputs(ResolvedDependencies(), b"rules: []\n")
    dependencies = ResolvedDependencies(
        (
            *dependencies.artifacts,
            SourceArtifact(
                "operation/evaluation-split.yaml",
                b"split:\n  seed: 17\n  forced_dev: {source.pdf: independent native source}\n"
                b"golden:\n  sizes: {dev: 1, test: 1}\n",
            ),
        ),
        dependencies.vocabularies,
        dependencies.ontology_sources,
    )
    bundle = proposal_inputs(
        SourceBundle(
            "domain",
            (
                SourceArtifact(
                    "core",
                    files("corpus_structure").joinpath("model/semantic/core.yaml").read_bytes(),
                ),
                SourceArtifact("domain", yaml.safe_dump(schema).encode()),
            ),
        ),
        dependencies,
    )
    bundle, dependencies = analytical_inputs(bundle, dependencies)
    from semantic.method_dimensions_support import fixture_execution_inputs

    dependencies = composed_dependencies(
        dependencies, fixture_execution_inputs("pdf.consumer-fixture")
    )
    profile = PreparationProfile(version="semantic-2")
    from corpus_structure.semantic.characterization import characterization_inputs

    bundle = characterization_inputs(bundle)
    prepared = prepare_release(bundle, dependencies, profile)
    with admin.begin() as conn:
        persist_release(conn, bundle, dependencies, profile, prepared)
        conn.execute(insert(table("data.project")).values(project_id="native-consumer"))
        activate_release(
            conn,
            "native-consumer",
            prepared.release_id,
            expected_parent=None,
            expected_generation=0,
        )
        conn.execute(
            insert(table("data.realization")).values(
                project_id="native-consumer",
                realization_id="native-input",
                release_id=prepared.release_id,
            )
        )
    original = b"%PDF-1.7\nindependent native custody input"
    recipe = b'{"recipe":"native-consumer-fixture"}'
    native_schema = (
        files("corpus_structure")
        .joinpath("model/semantic/docling-validation.schema.json")
        .read_bytes()
    )
    doc = DoclingDocument(name="Independent source")
    parent = sibling = parent_text = sibling_text = None
    if ancestor:
        parent = doc.add_group(label=GroupLabel.SECTION, name="Assumptions")
        parent_text = doc.add_text(
            label=DocItemLabel.TEXT,
            text="Suppose Alice is here.",
            orig="Suppose Alice is here.",
            parent=parent,
        )
    section = doc.add_group(label=GroupLabel.SECTION, name="People", parent=parent)
    if ancestor:
        sibling = doc.add_group(label=GroupLabel.SECTION, name="Other people", parent=parent)
        sibling_text = doc.add_text(
            label=DocItemLabel.TEXT, text="Bob is there.", orig="Bob is there.", parent=sibling
        )
    paragraph = doc.add_text(
        label=DocItemLabel.TEXT, text="Alice is here.", orig="Alice is here.", parent=section
    )
    conversion = PdfConversion(
        sha256(original).hexdigest(), recipe, snapshot(doc), "success", (), (), (), None
    )
    sections = {section.self_ref}
    if parent is not None:
        assert sibling is not None
        sections.update((parent.self_ref, sibling.self_ref))
    payload = publication_payload(
        conversion,
        product_key="native",
        schema_digest=sha256(native_schema).hexdigest(),
        section_refs=frozenset(sections),
    )
    product = prepare_pdf_product(payload, original, native_schema, recipe)
    from corpus_structure.ingest.sentences import SentenceConfig

    configuration = {
        "model": "automated-native-fixture",
        "mode": "extract",
        "max_units": 1,
        "packet_cap_chars": 18000,
        "sentences": SentenceConfig().model_dump(mode="json"),
    }
    with writer.begin() as conn:
        run = create_run(
            conn,
            project_id="native-consumer",
            binding=OperationBinding(prepared.release_id, "native-input", 0, b"{}"),
            kind="full",
            options={"agent_configs": {"agent.opus/extract": configuration}},
            code_commit="native-consumer-test",
        )
        config = record_method(
            conn,
            SimpleNamespace(
                name="pdf.consumer-fixture",
                version="1",
                family="ingest",
                tier="deterministic",
                confidence_source=None,
                unit_type="document",
                Config=create_model("NativeConsumerFixture"),
            ),
            "default",
            {},
            "native-consumer-fixture",
            prepared=prepared,
        )
        path = tmp_path / "source.pdf"
        path.write_bytes(original)
        document = register_document(
            conn,
            project_id="native-consumer",
            source_uri="source.pdf",
            original_path=str(path),
            original=original,
            mime="application/pdf",
        )
        source = create_task(
            conn,
            run_id=run,
            config_id=config,
            stage="ingest",
            unit_type="document",
            unit_id=document,
            unit_key="source.pdf",
            input_hash=sha256(original).hexdigest(),
        )
        claim = claim_tasks(
            conn, run_id=RunId(run), config_id=MethodConfigId(config), holder="native-fixture"
        )[0]
        store_pdf_original(
            conn,
            task_id=source,
            attempt=claim.attempt,
            holder="native-fixture",
            original=original,
            recipe_bytes=recipe,
        )
    published = publish_native_record_fixture(
        writer,
        tmp_path / "native-records",
        task_id=source,
        attempt=claim.attempt,
        holder="native-fixture",
        product=product,
        document=doc,
    )
    native_reference = ProductReference(source, "native", published.logical_digest)
    with writer.begin() as conn:
        if parent is not None:
            assert parent_text is not None and sibling is not None and sibling_text is not None
            parent_draft = SourceViewDraft(
                "native-parent-section",
                document,
                native_reference,
                parent.self_ref,
                "direct",
                parent_text.text,
                (
                    {
                        "item_ref": parent_text.self_ref,
                        "start": 0,
                        "end": len(parent_text.text),
                        "kind": "native_text",
                        "source_field": "text",
                    },
                ),
                (parent.self_ref, parent_text.self_ref),
                (),
                dict(payload["health"], formula_outcomes=[]),
                b'{"recipe":"parent-section"}',
                analysis_eligible=False,
            )
            store_source_view(
                conn,
                run_id=run,
                task_id=source,
                attempt=claim.attempt,
                holder="native-fixture",
                draft=qualified_view_draft(parent_draft, prepared.release_id),
                position=0,
            )
            sibling_draft = SourceViewDraft(
                "native-sibling-section",
                document,
                native_reference,
                sibling.self_ref,
                "direct",
                sibling_text.text,
                (
                    {
                        "item_ref": sibling_text.self_ref,
                        "start": 0,
                        "end": len(sibling_text.text),
                        "kind": "native_text",
                        "source_field": "text",
                    },
                ),
                (sibling.self_ref, sibling_text.self_ref),
                (parent.self_ref,),
                dict(payload["health"], formula_outcomes=[]),
                b'{"recipe":"sibling-section"}',
                analysis_eligible=False,
            )
            store_source_view(
                conn,
                run_id=run,
                task_id=source,
                attempt=claim.attempt,
                holder="native-fixture",
                draft=qualified_view_draft(sibling_draft, prepared.release_id),
                position=2,
            )
        draft = SourceViewDraft(
            "native-person-section",
            document,
            native_reference,
            section.self_ref,
            "direct",
            "Alice is here.",
            (
                {
                    "item_ref": paragraph.self_ref,
                    "start": 0,
                    "end": 14,
                    "kind": "native_text",
                    "source_field": "text",
                },
            ),
            (section.self_ref, paragraph.self_ref),
            (() if parent is None else (parent.self_ref,)),
            dict(payload["health"], formula_outcomes=[]),
            b'{"recipe":"native-person-section"}',
        )
        draft = qualified_view_draft(draft, prepared.release_id)
        view = store_source_view(
            conn,
            run_id=run,
            task_id=source,
            attempt=claim.attempt,
            holder="native-fixture",
            draft=draft,
            position=1 if ancestor else 0,
        )
        complete_task(
            conn,
            task_id=source,
            attempt=claim.attempt,
            holder="native-fixture",
            prepared=prepared,
            observations=[],
            outcome="empty",
        )
        from corpus_structure.semantic.source_views import selected_source_views
        from semantic.primary_native_support import bind_primary_agent_run

        run, configuration = bind_primary_agent_run(
            conn,
            run,
            prepared,
            tuple(v.id for v in selected_source_views(conn, run)),
            configuration,
        )
        from corpus_structure.ingest.methods import SegmentSentences
        from corpus_structure.methods.llm.agent_opus import AgentOpus
        from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile

        registry = MethodRegistry(
            (AgentOpus(), SegmentSentences()),
            MethodsFile(configs={"agent.opus": {"extract": configuration}}),
        )
        queued = propose_agents(
            conn,
            run,
            prepared,
            registry,
            "version: '0.2'\n"
            "chains:\n"
            "  propose:\n"
            "    - key: native-source-policy\n"
            "      unit_type: source_view\n"
            "      when: \"unit.kind == 'source_view' and unit.statement_kind "
            '== null and unit.claim_bearing == null"\n'
            "      do: {method: agent.opus/extract, then: stop}\n",
        )
        assert queued == 1
        task = conn.execute(
            text(
                "SELECT id FROM ops.task WHERE run_id=:run AND "
                "unit_type='source_view' AND stage='propose'"
            ),
            {"run": run},
        ).scalar_one()
        trigger = conn.scalar(text("SELECT trigger FROM ops.task WHERE id=:task"), {"task": task})
        assert trigger["values"]["unit.kind"] == "source_view"
        assert trigger["values"]["unit.statement_kind"] is None
        assert trigger["values"]["unit.claim_bearing"] is None
    return prepared, run, task, view, draft.key


def submit_exclusion_case(
    stage: QueuedResubmissionStage,
    writer: Engine,
    *,
    finalize=True,
    citations=1,
    keyed=False,
    attribute_assertions=False,
    local_ids=("p", "q"),
    reason="separate source identities",
    output_realization_id="excluded-result",
):
    """Submit this queued source's authored exclusion and optionally finalize its run."""
    prepared, run, task, locator = stage.result
    session = SemanticAgentSession(writer, run)

    async def submit():
        async with Client(build_semantic_server(session)) as client:
            unit = await lease_and_read(client, run, task)
            response = await client.call_tool(
                "propose_claims",
                {
                    "task_id": task,
                    "batch": {
                        "unit_ref": locator,
                        "entities": [
                            {
                                "id": ref,
                                "class_iri": "https://example.org/Person",
                                "label": "Alice",
                                "attributes": [
                                    {
                                        "predicate": "https://example.org/name",
                                        "value": {"kind": "text", "text": "Alice"},
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
                                ]
                                if keyed or attribute_assertions
                                else [],
                            }
                            for ref in local_ids
                        ],
                        "identity_exclusions": [
                            {
                                "id": "different",
                                "left": {"kind": "local", "target": local_ids[0]},
                                "right": {"kind": "local", "target": local_ids[1]},
                                "reason": reason,
                                "evidence": [
                                    {
                                        "sentence": unit["sentences"][0]["id"],
                                        "quote": "Alice is here.",
                                        "role": "primary",
                                    },
                                    *(
                                        [
                                            {
                                                "sentence": unit["sentences"][0]["id"],
                                                "quote": "Alice",
                                                "role": "supporting",
                                            }
                                        ]
                                        if citations == 2
                                        else []
                                    ),
                                ],
                            }
                        ],
                    },
                },
            )
            assert response.structured_content is not None
            assert response.structured_content["submission_disposition"] == "completed_accepted", (
                json.dumps(response.structured_content, indent=2)
            )

    anyio.run(submit)
    if not finalize:
        from corpus_structure.semantic.operations import seal_cut

        with writer.begin() as conn:
            cut = seal_cut(conn, run, "evaluation", final=True)
        return prepared, run, cut, None
    result = finalize_bound_run(writer, run, output_realization_id)
    with writer.connect() as conn:
        cut = conn.scalar(
            select(table("ops.input_cut").c.id)
            .where(table("ops.input_cut").c.run_id == run)
            .order_by(table("ops.input_cut").c.id.desc())
            .limit(1)
        )
    return prepared, run, cut, result


@dataclass(frozen=True)
class ExclusionRecipe:
    finalize: bool = False
    citations: int = 1
    keyed: bool = False
    attribute_assertions: bool = False
    global_names: bool = False
    local_ids: tuple[str, str] = ("p", "q")
    reason: str = "separate source identities"


@dataclass(frozen=True)
class ExclusionStage:
    prepared: PreparedRelease
    run: RunId
    cut: Any
    completed: Any

    @property
    def result(self):
        return self.prepared, self.run, self.cut, self.completed

    @property
    def seed_files(self) -> tuple[Path, ...]:
        return ()

    def validate_clone(self, admin: Engine) -> None:
        from corpus_structure.semantic.operations import read_original

        documents, artifacts, selected, views = map(
            table,
            (
                "kb.document",
                "kb.source_artifact",
                "ops.run_source_view",
                "kb.source_view",
            ),
        )
        with admin.connect() as connection:
            rows = connection.execute(
                select(documents.c.id, artifacts.c.artifact_digest)
                .select_from(
                    selected.join(views, views.c.id == selected.c.source_view_id)
                    .join(documents, documents.c.id == views.c.document_id)
                    .join(artifacts, artifacts.c.artifact_digest == documents.c.content_hash)
                )
                .where(selected.c.run_id == self.run)
                .distinct()
            ).all()
            if not rows:
                raise ValueError("exclusion seed has no retained source original")
            for document, digest in rows:
                if digest is None:
                    raise ValueError("exclusion seed original custody is missing")
                read_original(connection, document, prepared=self.prepared)
            if (
                connection.scalar(
                    select(table("ops.input_cut").c.run_id).where(
                        table("ops.input_cut").c.id == self.cut
                    )
                )
                != self.run
            ):
                raise ValueError("exclusion seed lacks its exact sealed cut")


def build_exclusion_recipe(recipe, admin, writer, directory, *, purpose_engine=None):
    preparation = prepare_resubmission_case(
        ResubmissionPreparationRecipe(
            identity_keyed=recipe.keyed,
            global_names=recipe.global_names,
        )
    )
    persist_resubmission_release(admin, writer, preparation, composed=True)
    source = publish_resubmission_source(preparation, writer, directory / "exclusions.pdf")
    queued = queue_resubmission_agent(source, writer)
    result = submit_exclusion_case(
        queued,
        writer,
        finalize=recipe.finalize,
        citations=recipe.citations,
        keyed=recipe.keyed,
        attribute_assertions=recipe.attribute_assertions,
        local_ids=recipe.local_ids,
        reason=recipe.reason,
    )
    return ExclusionStage(*result)


register_scenario_builder(ExclusionRecipe, build_exclusion_recipe)
