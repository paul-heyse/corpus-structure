"""Current native source → component → actual occurrence → compatible-edge custody.

The encoder and relationship interpretation kernels are controlled here. Native
completion, source selection, retained-component authentication and replay are real;
this test makes no model/provider or semantic-quality claim.
"""

from dataclasses import replace
import json

import pytest
from types import SimpleNamespace

from pydantic import BaseModel
from sqlalchemy import select

from corpus_structure.core.method import Digest, MethodSettings, Resources, UnitRef
from corpus_structure.core.vocab import MethodTier, Stage, TaskUnitType
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


def completed_component_case(case, tmp_path):
    """Real completed native source/component custody for controlled policy tests."""
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
    from corpus_structure.methods.definition_applicability import DefinitionComponentsConfig, DefinitionComponentsMethod
    from corpus_structure.methods.gliner import GlinerProfile, GlinerPreparation, GlinerReport

    profile = GlinerProfile(tmp_path, "controlled-kernel", "immutable", tuple((name, "a" * 64) for name in
        ("config.json", "encoder_config/config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json")))
    component_cfg = DefinitionComponentsConfig(inputs=inputs, structural_input_digest=inputs.identity,
        target_ids=("literal",), profile=profile, use_named_candidates=False)

    class ControlledComponentWorker:
        def __init__(self, declared_profile):
            self.profile = declared_profile

        def close(self):
            pass

        def extract(self, pack, requests, **kwargs):
            endpoint = dict(start=0, end=2, text="12")
            raw = dict(entities={"defined term or expression": [dict(endpoint, interpretation="definition")],
                                 "defining text or formula": [endpoint]},
                       relation_extraction={"term is defined or explained by": [dict(head=endpoint, tail=endpoint)]})
            return tuple(GlinerReport(request.context_id, request.context_digest, "controlled-kernel",
                profile.fingerprint, pack.fingerprint, GlinerPreparation("12", "", 1, 1, 2), json.dumps(raw),
                "{}", 0., False) for request in requests)

    def produce_component(*, structural_admission=()):
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr("corpus_structure.methods.definition_applicability.GlinerWorker", ControlledComponentWorker)
            component_run = semantic.run_source_methods(case.writer, project_id="private-records", prepared=case.prepared,
                binding=OperationBinding(case.prepared.release_id, "wce-source", source_revision, b"{}"),
                registry=MethodRegistry([DefinitionComponentsMethod()], MethodsFile(configs={"structure.definition_components": {"default": component_cfg.model_dump(mode="json")}})),
                graph=Graph(((Stage.ASSEMBLE, (Step("structure.definition_components/default"),)),), policy_propose=False),
                method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
                structural_admission=structural_admission)
        return component_run

    component_run = produce_component()
    with case.writer.connect() as conn:
        tasks, results = table("ops.task"), table("ops.task_result")
        component_body = conn.execute(select(results.c.body).join(tasks, tasks.c.id == results.c.task_id).where(tasks.c.run_id == component_run.run_id)).scalar_one()
    report = StructuralProductReport.model_validate(component_body["structural_product"])
    assert report.definition_components is not None
    (component,) = report.definition_components.components
    assert component.term.text == component.content.text == "12"
    finalize_bound_run(case.writer, component_run.run_id, "wce-components")
    component_result, component_revision, runtime = completed_metadata(case, component_run.run_id)
    with case.writer.connect() as conn:
        task = conn.execute(select(table("ops.task")).where(table("ops.task").c.run_id == component_run.run_id)).mappings().one()
    reference = RetainedComponentRef(product_id=report.product_id, component_id=component.component_id,
        operation_id="structure.definition_components", operation_version=DefinitionComponentsMethod.version,
        project_id="private-records", run_id=component_run.run_id, cut_id=component_result["cut_id"],
        release_id=case.prepared.release_id, result_revision=component_revision, selected_task_id=task["id"],
        origin_task_id=task["id"], runtime_fingerprint=runtime, dependencies=inputs.dependencies)
    target = ExtractedComponentTarget(reference=reference, label="12", description="12", scope="controlled-source")
    return SimpleNamespace(case=case, source=source, passage=passage, inputs=inputs,
                           component=component, report=report, component_run=component_run,
                           reference=reference, target=target, component_revision=component_revision,
                           source_revision=source_revision, view=v, selected_task=task,
                           produce_component=produce_component, component_config=component_cfg)


def completed_relationship_case(case, monkeypatch, tmp_path):
    completed = completed_component_case(case, tmp_path)
    target, reference, component_revision, v, task = (completed.target, completed.reference,
        completed.component_revision, completed.view, completed.selected_task)
    cfg = ContextualCandidateConfig(source_dependency_method="private.records", target_components=(target,),
        relationship_constraints=(RelationshipConstraint("sense", ("denotes",), "usage", "sense", "one"),
                                 RelationshipConstraint("comparison", ("compared-with",), "subject", "comparator", "many"),
                                 RelationshipConstraint("definition", ("defined-by",), "usage", "definition", "one")),
        source_product_digest=v["native_content_digest"], source_projection_digest=v["projection_digest"], scope="controlled-source")

    class OccurrenceConfig(BaseModel):
        pass

    class ActualOccurrenceProducer:
        name = "private.records"
        version = "2"
        family = case.method.family
        tier = MethodTier.DETERMINISTIC
        unit_type = TaskUnitType.SOURCE_VIEW
        confidence_source = None
        Config = OccurrenceConfig
        resources = Resources()

        def select(self, run, cfg):
            return tuple(UnitRef(TaskUnitType.SOURCE_VIEW, view.id, view.key) for view in run.reader.source_views() if view.id == case.view)

        def input_digest(self, unit, cfg):
            return Digest(b"controlled-actual-source-roles")

        def run(self, units, cfg, ctx):
            from corpus_structure.semantic.proposals import native_source_frame
            from corpus_structure.semantic.source_contexts import record_source_pin
            from corpus_structure.semantic.record_contracts import anchor_identity
            from corpus_structure.semantic.contributions import occurrence_identity, contribution_identity

            results = []
            for unit in units:
                draft = contribution_drafts(case)
                pin = record_source_pin(native_source_frame(ctx.reader.source_view(unit.ref.unit_id), ()))
                products = []
                for original in draft.contributions:
                    anchors = []
                    for anchor in original["anchors"]:
                        anchor = dict(anchor, pin=pin)
                        anchor["anchor_id"] = anchor_identity(anchor)
                        anchors.append(anchor)
                    product = dict(original, pin=pin, anchors=tuple(anchors), occurrence_id=occurrence_identity(anchors))
                    product["contribution_id"] = contribution_identity(product)
                    products.append(product)
                results.append(replace(draft, ref=unit.ref, contributions=tuple(products),
                    contribution_coordinate_texts=tuple(dict(c, pin=pin) for c in draft.contribution_coordinate_texts)))
            return tuple(results)

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
                                                         relation="compared-with", basis="model_reading"),
                                  replace(witness, witness_id="controlled-definition", relation="defined-by", basis="model_reading"))
        return select_relationships(**kwargs)
    monkeypatch.setattr("corpus_structure.methods.contextual_candidates.verify_encoder_implementation", lambda _: ())
    monkeypatch.setattr("corpus_structure.methods.contextual_candidates.encode_contexts", controlled_encoder)
    monkeypatch.setattr("corpus_structure.methods.contextual_candidates.select_relationships", controlled_interpretation)
    def produce_relationship(*, local_semantic_admission=()):
        return semantic.run_source_methods(case.writer, project_id="private-records", prepared=case.prepared,
        binding=OperationBinding(case.prepared.release_id, "wce-components", component_revision, b"{}"),
        registry=MethodRegistry([ActualOccurrenceProducer(), ContextualCandidates()], MethodsFile(configs={
            "private.records": {"default": {}}, "retrieve.contextual": {"default": cfg.model_dump(mode="json")}})),
        graph=Graph(((Stage.EXTRACT, (Step("private.records/default"),)), (Stage.ASSEMBLE, (Step("retrieve.contextual/default"),))), policy_propose=False),
        method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path), local_semantic_admission=local_semantic_admission)
    outcome = produce_relationship()
    assert outcome.status == "source_ready"
    with case.writer.connect() as conn:
        tasks, results, configs, methods = (table(n) for n in ("ops.task", "ops.task_result", "ops.method_config", "ops.method"))
        body = conn.execute(select(results.c.body).join(tasks, tasks.c.id == results.c.task_id)
            .join(configs, configs.c.id == tasks.c.method_config_id).join(methods, methods.c.id == configs.c.method_id)
            .where(tasks.c.run_id == outcome.run_id, methods.c.name == "retrieve.contextual")).scalar_one()
        payload = body["contribution_operations"][0]["contextual_enrichment"]
        assert payload["version"] == "contextual-enrichment-2"
        assert {edge["relation"] for edge in payload["relationship_decisions"][0]["selected_edges"]} == {"denotes", "compared-with", "defined-by"}
        assert payload["component_targets"][0]["reference"]["origin_task_id"] == task["id"]
        assert {c["semantic_type"] for c in body["contributions"]} == {"contextual.located_mention", "contextual.relationship"}
        assert all(w["support_state"] == "unassessed" for w in payload["relationship_decisions"][0]["witnesses"])
    return SimpleNamespace(completed=completed, outcome=outcome, body=body, payload=payload,
                           cfg=cfg, produce_relationship=produce_relationship)


def test_registered_actual_occurrences_resolve_component_and_retain_compatible_edges(private_source, monkeypatch, tmp_path):
    case = private_source
    linked = completed_relationship_case(case, monkeypatch, tmp_path)
    completed, outcome, body, payload = linked.completed, linked.outcome, linked.body, linked.payload
    tasks, configs, methods = (table(n) for n in ("ops.task", "ops.method_config", "ops.method"))
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
    from corpus_structure.methods.definition_applicability import (
        DefinitionApplicabilityConfig, DefinitionApplicabilityMethod,
    )
    from corpus_structure.semantic.contextual_links import RetainedRelationshipDecisionRef
    from corpus_structure.semantic.observations import source_python

    linked_result, linked_revision, linked_runtime = completed_metadata(case, outcome.run_id)
    with case.writer.connect() as conn:
        link_task = conn.execute(select(tasks).join(configs, configs.c.id == tasks.c.method_config_id)
            .join(methods, methods.c.id == configs.c.method_id).where(tasks.c.run_id == outcome.run_id,
                                                                   methods.c.name == "retrieve.contextual")).mappings().one()
    decision = payload["relationship_decisions"][0]
    edge = next(e for e in decision["selected_edges"] if e["relation"] == "defined-by")
    occurrence = next(c for c in body["contributions"] if c["semantic_type"] == "contextual.located_mention"
                      and source_python(c["value"])["producer_semantic_type"] == "table.cell_value")
    link_ref = RetainedRelationshipDecisionRef(project_id="private-records", run_id=outcome.run_id,
        cut_id=linked_result["cut_id"], release_id=case.prepared.release_id, result_revision=linked_revision,
        selected_task_id=link_task["id"], origin_task_id=link_task["id"], runtime_fingerprint=linked_runtime,
        operation_key=body["contribution_operations"][0]["operation_key"], decision_id=decision["decision_id"],
        edge_id=edge["edge_id"], occurrence_contribution_id=occurrence["contribution_id"])
    for mode, expected in (("defining_occurrence", "applicable_definition"), ("contextual_usage", "unresolved")):
        app_inputs = completed.inputs.model_copy(update={"policy_id": "definition-introduction-1" if mode == "defining_occurrence" else "contextual-usage-1",
            "dependencies": (*completed.inputs.dependencies, completed.report.product_id, decision["decision_id"])})
        app_cfg = DefinitionApplicabilityConfig(inputs=app_inputs, structural_input_digest=app_inputs.identity,
            usage_id="literal", selection_refs=(link_ref,), applicability_scope=mode)
        app_run = semantic.run_source_methods(case.writer, project_id="private-records", prepared=case.prepared,
            binding=OperationBinding(case.prepared.release_id, "wce-links", linked_revision, b"{}"),
            registry=MethodRegistry([DefinitionApplicabilityMethod()], MethodsFile(configs={"structure.definitions": {"default": app_cfg.model_dump(mode="json")}})),
            graph=Graph(((Stage.ASSEMBLE, (Step("structure.definitions/default"),)),), policy_propose=False),
            method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path))
        with case.writer.connect() as conn:
            app_body = conn.execute(select(results.c.body).join(tasks, tasks.c.id == results.c.task_id).where(tasks.c.run_id == app_run.run_id)).scalar_one()
        assert app_body["structural_product"]["definition"]["readings"][0]["outcome"] == expected
        assert app_body["structural_product"]["standing"] == "private_proposal"
        assert app_body["structural_product"]["definition"]["readings"][0]["link_ref"]["edge_id"] == edge["edge_id"]
