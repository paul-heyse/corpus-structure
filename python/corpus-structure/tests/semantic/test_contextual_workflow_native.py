"""Current native source → component → actual occurrence → compatible-edge custody.

The encoder and relationship interpretation kernels are controlled here. Native
completion, source selection, retained-component authentication and replay are real;
this test makes no model/provider or semantic-quality claim.
"""

from dataclasses import replace

from pydantic import BaseModel
from sqlalchemy import select

from corpus_structure.core.method import Digest, MethodSettings, Resources, UnitRef
from corpus_structure.core.vocab import MethodFamily, MethodTier, Stage, TaskUnitType
from corpus_structure.methods.contextual_candidates import ContextualCandidateConfig, ContextualCandidates
from corpus_structure.methods.contextual_embeddings import EncodedVector, EncoderResult, identity
from corpus_structure.methods.structural_products import StructuralProductsMethod
from corpus_structure.orchestrate import semantic
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.semantic._operation_calls import select_source_view
from corpus_structure.semantic._operation_ids import RunId, SourceViewId
from corpus_structure.semantic.contextual_links import RelationshipConstraint, select_relationships
from corpus_structure.semantic.contextual_registry import ExtractedComponentTarget
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding
from corpus_structure.semantic.structural_products import (
    DefinitionComponentsProduct, ExternalSourceRef, LocatedDefinitionSpan,
    RetainedComponentRef, StructuralInput, StructuralPassage, StructuralProductReport,
    definition_component,
)
from .native_record_fixtures import (
    complete_contributions, contribution_drafts,
    private_source as private_source,
    private_source_options as private_source_options,
)


def completed_metadata(case, run):
    with case.writer.connect() as conn:
        completed = conn.execute(select(table("ops.completed_result")).where(table("ops.completed_result").c.run_id == run)).mappings().one()
        batch = conn.execute(select(table("data.batch")).where(
            table("data.batch").c.release_id == completed["release_id"],
            table("data.batch").c.realization_id == completed["output_realization_id"],
            table("data.batch").c.batch_id == completed["batch_id"],
        )).mappings().one()
        runtime = conn.scalar(select(table("ops.run").c.runtime_id).where(table("ops.run").c.id == run))
    return completed, batch["data_revision"], runtime


def test_registered_actual_occurrences_resolve_component_and_retain_compatible_edges(private_source, monkeypatch, tmp_path):
    case = private_source
    with case.writer.begin() as conn:
        complete_contributions(case, conn, contribution_drafts(case))
    finalize_bound_run(case.writer, case.run, "wce-source")
    source_result, source_revision, _ = completed_metadata(case, case.run)
    v = case.view_row
    source = ExternalSourceRef(project_id="private-records", run_id=case.run,
        cut_id=source_result["cut_id"], release_id=case.prepared.release_id,
        result_revision=source_revision, source_view_id=case.view,
        native_task_id=v["native_task_id"], native_product_key=v["native_product_key"],
        native_content_digest=v["native_content_digest"], projection_digest=v["projection_digest"],
        recipe_digest=v["recipe_digest"], coordinate_version=2)
    passage = StructuralPassage(passage_id="literal", source_ref=source.identity, start=0, end=2, text="12", scope="controlled-source")
    inputs = StructuralInput(question="inspect located numeral attachment", scope="controlled-source",
        inventory_id="controlled-original-source", policy_id="controlled-component-1",
        sources=(source,), passages=(passage,), dependencies=("controlled-native-source",))
    span = LocatedDefinitionSpan(passage_id="literal", start=0, end=2, text="12")
    component = definition_component(term=span, content=span, interpretation="unresolved",
        basis="native_geometry", scope="controlled-source", evidence=("literal",),
        reason="controlled located component; interpretation remains unassessed")
    report = StructuralProductReport(kind="definition_components", inputs=inputs,
        definition_components=DefinitionComponentsProduct(components=(component,), stages=()))
    component_run = semantic.run_source_methods(case.writer, project_id="private-records", prepared=case.prepared,
        binding=OperationBinding(case.prepared.release_id, "wce-source", source_revision, b"{}"),
        registry=MethodRegistry([StructuralProductsMethod()], MethodsFile(configs={"structure.products": {"default": dict(report=report.model_dump(mode="json"), structural_input_digest=inputs.identity)}})),
        graph=Graph(((Stage.ASSEMBLE, (Step("structure.products/default"),)),), policy_propose=False),
        method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path))
    finalize_bound_run(case.writer, component_run.run_id, "wce-components")
    component_result, component_revision, runtime = completed_metadata(case, component_run.run_id)
    with case.writer.connect() as conn:
        task = conn.execute(select(table("ops.task")).where(table("ops.task").c.run_id == component_run.run_id)).mappings().one()
    reference = RetainedComponentRef(product_id=report.product_id, component_id=component.component_id,
        operation_id="structure.products", operation_version=StructuralProductsMethod.version,
        project_id="private-records", run_id=component_run.run_id, cut_id=component_result["cut_id"],
        release_id=case.prepared.release_id, result_revision=component_revision, selected_task_id=task["id"],
        origin_task_id=task["id"], runtime_fingerprint=runtime, dependencies=inputs.dependencies)
    target = ExtractedComponentTarget(reference=reference, label="12", description="12", scope="controlled-source")
    cfg = ContextualCandidateConfig(source_dependency_method="private.records", target_components=(target,),
        relationship_constraints=(RelationshipConstraint("sense", ("denotes",), "usage", "sense", "one"),
                                 RelationshipConstraint("comparison", ("compared-with",), "subject", "comparator", "many")),
        source_product_digest=v["native_content_digest"], source_projection_digest=v["projection_digest"], scope="controlled-source")

    class ActualOccurrenceProducer:
        name = "private.records"
        version = "2"
        family = MethodFamily.RECORD
        tier = MethodTier.DETERMINISTIC
        unit_type = TaskUnitType.SOURCE_VIEW
        confidence_source = None
        Config = BaseModel
        resources = Resources()

        def select(self, run, config):
            return (UnitRef(TaskUnitType.SOURCE_VIEW, case.view, "private-unit"),)

        def input_digest(self, unit, config):
            return Digest(b"controlled-actual-source-roles")

        def run(self, units, config, context):
            return tuple(replace(contribution_drafts(case), ref=unit.ref) for unit in units)

    start = semantic.start_run
    def select_original(conn, run):
        start(conn, run)
        select_source_view(conn, run_id=RunId(run), source_run_id=RunId(case.run),
                           source_view_id=SourceViewId(case.view), projection_context=case.prepared)
    monkeypatch.setattr(semantic, "start_run", select_original)

    def controlled_encoder(items, profile, **kwargs):
        vectors = []
        for item in items:
            digest = "c" * 64
            vid = identity("context-vector", [item.object_id, item.source_binding, profile.profile_id, digest, item.representation_digest])
            vectors.append(EncodedVector(vid, item.object_id, item.source_binding, profile.profile_id, digest,
                (1.,) + (0.,) * (profile.dimension - 1), item.representation_digest))
        return EncoderResult(profile.profile_id, (), tuple(vectors), ())

    def controlled_interpretation(**kwargs):
        witness = kwargs["witnesses"][0]
        kwargs["witnesses"] = (*kwargs["witnesses"], replace(witness, witness_id="controlled-comparison",
                                                         relation="compared-with", basis="model_reading"))
        return select_relationships(**kwargs)
    monkeypatch.setattr("corpus_structure.methods.contextual_candidates.verify_encoder_implementation", lambda _: ())
    monkeypatch.setattr("corpus_structure.methods.contextual_candidates.encode_contexts", controlled_encoder)
    monkeypatch.setattr("corpus_structure.methods.contextual_candidates.select_relationships", controlled_interpretation)
    outcome = semantic.run_source_methods(case.writer, project_id="private-records", prepared=case.prepared,
        binding=OperationBinding(case.prepared.release_id, "wce-components", component_revision, b"{}"),
        registry=MethodRegistry([ActualOccurrenceProducer(), ContextualCandidates()], MethodsFile(configs={
            "private.records": {"default": {}}, "retrieve.contextual": {"default": cfg.model_dump(mode="json")}})),
        graph=Graph(((Stage.ASSEMBLE, (Step("retrieve.contextual/default"),)),), policy_propose=False),
        method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path))
    assert outcome.status == "source_ready"
    with case.writer.connect() as conn:
        tasks, results, configs, methods = (table(n) for n in ("ops.task", "ops.task_result", "ops.method_config", "ops.method"))
        body = conn.execute(select(results.c.body).join(tasks, tasks.c.id == results.c.task_id)
            .join(configs, configs.c.id == tasks.c.method_config_id).join(methods, methods.c.id == configs.c.method_id)
            .where(tasks.c.run_id == outcome.run_id, methods.c.name == "retrieve.contextual")).scalar_one()
        payload = body["contribution_operations"][0]["contextual_enrichment"]
        assert payload["version"] == "contextual-enrichment-2"
        assert {edge["relation"] for edge in payload["relationship_decisions"][0]["selected_edges"]} == {"denotes", "compared-with"}
        assert payload["component_targets"][0]["reference"]["origin_task_id"] == task["id"]
        assert {c["semantic_type"] for c in body["contributions"]} == {"contextual.located_mention", "contextual.relationship"}
        assert all(w["support_state"] == "unassessed" for w in payload["relationship_decisions"][0]["witnesses"])
    finalize_bound_run(case.writer, outcome.run_id, "wce-links")
    from corpus_structure.serve.contributions import (
        ContributionRequest, export_contribution_selection, serve_contributions,
    )

    with case.writer.connect() as conn:
        page = serve_contributions(conn, ContributionRequest(run_id=outcome.run_id, method="retrieve.contextual", include_details=True))
        rendered = page.model_dump_json()
        assert "contextual-enrichment-2" in rendered and "compared-with" in rendered
        assert page.standing == "retained_private"
        exported = export_contribution_selection(conn, ContributionRequest(run_id=outcome.run_id, method="retrieve.contextual"), tmp_path / "current-links")
        assert exported
    exported_text = "\n".join(path.read_text() for path in (tmp_path / "current-links").rglob("*.jsonl"))
    assert "compared-with" in exported_text and "denotes" in exported_text
