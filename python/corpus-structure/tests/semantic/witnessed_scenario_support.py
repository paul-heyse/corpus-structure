"""Controlled native WCE setup shared by custody and publication consumers.

Source/component/relationship production is real; provider kernels are controlled.
Reference meanings remain explicit original-source literals, never producer projections.
"""

import json
from collections.abc import Mapping
from dataclasses import asdict, replace
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel
from sqlalchemy import select

from corpus_structure.core.method import Digest, MethodSettings, Resources, UnitRef
from corpus_structure.core.vocab import MethodTier, Stage, TaskUnitType
from corpus_structure.evaluate.record_references import assign_origin
from corpus_structure.evaluate.structural_assessment import (
    StructuralAuthoredReference,
    StructuralEvaluationFrame,
    StructuralReferenceCase,
    StructuralSourceGroup,
    StructuralSourceOpportunity,
    create_structural_reference_set,
    record_structural_reference_pass,
)
from corpus_structure.methods.contextual_candidates import (
    ContextualCandidatesWithQueryContext,
    ContextualQueryConfig,
    ProducerRelationshipRecipe,
)
from corpus_structure.methods.contextual_embeddings import EncodedVector, EncoderResult, identity
from corpus_structure.methods.model_observation import (
    batch_receipt,
    installed_policy,
    observation_digest,
)
from corpus_structure.orchestrate import semantic
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.semantic._operation_calls import select_source_view
from corpus_structure.semantic._operation_ids import RunId, SourceViewId
from corpus_structure.semantic.contextual_links import RelationshipConstraint, select_relationships
from corpus_structure.semantic.contextual_registry import ExtractedComponentTarget
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding
from corpus_structure.semantic.structural_products import (
    ExternalSourceRef,
    RetainedComponentRef,
    StructuralInput,
    StructuralPassage,
    StructuralProductReport,
)

from .native_record_fixtures import (
    complete_contributions,
    contribution_drafts,
)


def completed_metadata(case, run):
    with case.writer.connect() as conn:
        completed = (
            conn.execute(
                select(table("ops.completed_result")).where(
                    table("ops.completed_result").c.run_id == run
                )
            )
            .mappings()
            .one()
        )
        batch = (
            conn.execute(
                select(table("data.batch")).where(
                    table("data.batch").c.release_id == completed["release_id"],
                    table("data.batch").c.realization_id == completed["output_realization_id"],
                    table("data.batch").c.batch_id == completed["batch_id"],
                )
            )
            .mappings()
            .one()
        )
        runtime = conn.scalar(
            select(table("ops.run").c.runtime_id).where(table("ops.run").c.id == run)
        )
    return completed, batch["data_revision"], runtime


def completed_component_case(case, tmp_path):
    """Real completed native source/component custody for controlled policy tests."""
    with case.writer.begin() as conn:
        complete_contributions(case, conn, contribution_drafts(case))
    finalize_bound_run(case.writer, case.run, "wce-source")
    source_result, source_revision, _ = completed_metadata(case, case.run)
    v = case.view_row
    source = ExternalSourceRef(
        project_id="private-records",
        run_id=case.run,
        cut_id=source_result["cut_id"],
        release_id=case.prepared.release_id,
        result_revision=source_revision,
        source_view_id=case.view,
        native_task_id=v["native_task_id"],
        native_product_key=v["native_product_key"],
        native_content_digest=v["native_content_digest"],
        projection_digest=v["projection_digest"],
        recipe_digest=v["recipe_digest"],
        coordinate_version=2,
    )
    passage = StructuralPassage(
        passage_id="literal",
        source_ref=source.identity,
        start=0,
        end=2,
        text="12",
        scope="controlled-source",
    )
    inputs = StructuralInput(
        question="inspect located numeral attachment",
        scope="controlled-source",
        inventory_id="controlled-original-source",
        policy_id="controlled-component-1",
        sources=(source,),
        passages=(passage,),
        dependencies=("controlled-native-source",),
    )
    from corpus_structure.methods.definition_applicability import (
        DefinitionComponentsConfig,
        DefinitionComponentsMethod,
    )
    from corpus_structure.methods.gliner import GlinerPreparation, GlinerProfile, GlinerReport

    profile = GlinerProfile(
        tmp_path,
        "controlled-kernel",
        "immutable",
        tuple(
            (name, "a" * 64)
            for name in (
                "config.json",
                "encoder_config/config.json",
                "model.safetensors",
                "tokenizer.json",
                "tokenizer_config.json",
            )
        ),
    )
    component_cfg = DefinitionComponentsConfig(
        inputs=inputs,
        structural_input_digest=inputs.identity,
        target_ids=("literal",),
        profile=profile,
        use_named_candidates=False,
    )

    class ControlledComponentWorker:
        def __init__(self, declared_profile):
            self.profile = declared_profile

        def close(self):
            pass

        def extract(self, pack, requests, **kwargs):
            endpoint = dict(start=0, end=2, text="12")
            raw = dict(
                entities={
                    "defined term or expression": [dict(endpoint, interpretation="definition")],
                    "defining text or formula": [endpoint],
                },
                relation_extraction={
                    "term is defined or explained by": [dict(head=endpoint, tail=endpoint)]
                },
            )
            receipt = batch_receipt(
                pack,
                asdict(self.profile),
                requests,
                kwargs["threshold"],
                kwargs["overlap_policy"],
                kwargs.get("evaluation", False),
                installed_policy()[0]["inference"],
            )
            key = receipt["digest"]
            raw_json = json.dumps(raw)
            return tuple(
                GlinerReport(
                    request.context_id,
                    request.context_digest,
                    key,
                    self.profile.fingerprint,
                    pack.fingerprint,
                    GlinerPreparation(request.text, "", 1, 1, len(request.text.encode())),
                    raw_json,
                    "{}",
                    0.0,
                    False,
                    request_digest=key,
                    observation_digest=observation_digest(
                        key, raw_json, "{}", ordinal=ordinal, member=receipt["members"][ordinal]
                    ),
                    batch_receipt_json=json.dumps(receipt),
                    member_ordinal=ordinal,
                )
                for ordinal, request in enumerate(requests)
            )

    def produce_component(*, structural_admission=()):
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(
                "corpus_structure.methods.definition_applicability.GlinerWorker",
                ControlledComponentWorker,
            )
            component_run = semantic.run_source_methods(
                case.writer,
                project_id="private-records",
                prepared=case.prepared,
                binding=OperationBinding(
                    case.prepared.release_id, "wce-source", source_revision, b"{}"
                ),
                registry=MethodRegistry(
                    [DefinitionComponentsMethod()],
                    MethodsFile(
                        configs={
                            "structure.definition_components": {
                                "default": component_cfg.model_dump(mode="json")
                            }
                        }
                    ),
                ),
                graph=Graph(
                    ((Stage.ASSEMBLE, (Step("structure.definition_components/default"),)),),
                    policy_propose=False,
                ),
                method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
                structural_admission=structural_admission,
            )
        return component_run

    component_run = produce_component()
    with case.writer.connect() as conn:
        tasks, results = table("ops.task"), table("ops.task_result")
        component_body = conn.execute(
            select(results.c.body)
            .join(tasks, tasks.c.id == results.c.task_id)
            .where(tasks.c.run_id == component_run.run_id)
        ).scalar_one()
    report = StructuralProductReport.model_validate(component_body["structural_product"])
    assert report.definition_components is not None
    (component,) = report.definition_components.components
    assert component.term.text == component.content.text == "12"
    finalize_bound_run(case.writer, component_run.run_id, "wce-components")
    component_result, component_revision, runtime = completed_metadata(case, component_run.run_id)
    with case.writer.connect() as conn:
        task = (
            conn.execute(
                select(table("ops.task")).where(table("ops.task").c.run_id == component_run.run_id)
            )
            .mappings()
            .one()
        )
    reference = RetainedComponentRef(
        product_id=report.product_id,
        component_id=component.component_id,
        operation_id="structure.definition_components",
        operation_version=DefinitionComponentsMethod.version,
        project_id="private-records",
        run_id=component_run.run_id,
        cut_id=component_result["cut_id"],
        release_id=case.prepared.release_id,
        result_revision=component_revision,
        selected_task_id=task["id"],
        origin_task_id=task["id"],
        runtime_fingerprint=runtime,
        dependencies=inputs.dependencies,
    )
    target = ExtractedComponentTarget(
        reference=reference, label="12", description="12", scope="controlled-source"
    )
    return SimpleNamespace(
        case=case,
        source=source,
        passage=passage,
        inputs=inputs,
        component=component,
        report=report,
        component_run=component_run,
        reference=reference,
        target=target,
        component_revision=component_revision,
        source_revision=source_revision,
        view=v,
        selected_task=task,
        produce_component=produce_component,
        component_config=component_cfg,
    )


def completed_relationship_case(case, monkeypatch, tmp_path, *, overlapping_recipe=None):
    completed = completed_component_case(case, tmp_path)
    target, component_revision, v, task = (
        completed.target,
        completed.component_revision,
        completed.view,
        completed.selected_task,
    )
    parameters = dict(
        source_dependency_method="private.records",
        target_components=(target,),
        relationship_constraints=(
            RelationshipConstraint("sense", ("denotes",), "usage", "sense", "one"),
            RelationshipConstraint(
                "comparison", ("compared-with",), "subject", "comparator", "many"
            ),
            RelationshipConstraint("definition", ("defined-by",), "usage", "definition", "one"),
        ),
        source_product_digest=v["native_content_digest"],
        source_projection_digest=v["projection_digest"],
        scope="controlled-source",
    )

    if overlapping_recipe is not None:
        parameters.update(
            {
                "relationship_constraints": (
                    RelationshipConstraint(
                        "specialization", ("specializes",), "subject", "object", "one"
                    ),
                ),
                "relationship_recipes": (
                    ProducerRelationshipRecipe(
                        rule="native-specialization",
                        occurrence_role="subject",
                        target_role="object",
                        relation="specializes",
                    ),
                ),
            }
        )

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
            return tuple(
                UnitRef(TaskUnitType.SOURCE_VIEW, view.id, view.key)
                for view in run.reader.source_views()
                if view.id == case.view
            )

        def input_digest(self, unit, cfg):
            return Digest(b"controlled-actual-source-roles")

        def run(self, units, cfg, ctx):
            from corpus_structure.semantic.contributions import (
                contribution_identity,
                occurrence_identity,
            )
            from corpus_structure.semantic.proposals import native_source_frame
            from corpus_structure.semantic.record_contracts import anchor_identity
            from corpus_structure.semantic.source_contexts import record_source_pin

            results = []
            for unit in units:
                draft = contribution_drafts(case)
                pin = record_source_pin(
                    native_source_frame(ctx.reader.source_view(unit.ref.unit_id), ())
                )
                products = []
                assert draft.contributions is not None
                assert draft.contribution_operations is not None
                originals: tuple[Mapping[str, Any], ...] = draft.contributions
                if overlapping_recipe is not None:
                    base = next(row for row in originals if row["kind"] == "occurrence")
                    roles = ("unrelated", "subject", "object")
                    if overlapping_recipe:
                        roles = ("subject", "unrelated", "object")
                    originals = tuple(
                        dict(
                            base,
                            semantic_type="source_rule." + role,
                            item_key=("other-group" if role == "unrelated" else "actual-group")
                            + "/role/"
                            + role,
                            anchors=tuple(
                                dict(
                                    anchor,
                                    pointer=case.table
                                    + "/data/table_cells/"
                                    + ("0" if role == "object" else "1"),
                                )
                                for anchor in base["anchors"]
                            ),
                        )
                        for role in roles
                    )
                for original in originals:
                    anchors = []
                    for anchor in original["anchors"]:
                        located: dict[str, Any] = dict(anchor)
                        located["pin"] = pin
                        located["anchor_id"] = anchor_identity(located)
                        anchors.append(located)
                    product: dict[str, Any] = dict(
                        original,
                        pin=pin,
                        anchors=tuple(anchors),
                        occurrence_id=occurrence_identity(anchors),
                    )
                    if overlapping_recipe is not None:
                        role = product["semantic_type"].removeprefix("source_rule.")
                        dependencies = ("native:" + str(pin["native_product_task_id"]),)
                        product["computation_dependencies"] = dependencies
                        product["component"] = dict(
                            protocol="witnessed-component-1",
                            kind="located_role",
                            question="inspect_cell",
                            question_version="1",
                            scope="controlled-source",
                            interpretation="unassessed",
                            bases=(
                                dict(
                                    kind="producer_group",
                                    dependencies=dependencies,
                                    anchor_ids=tuple(a["anchor_id"] for a in anchors),
                                ),
                            ),
                            dependencies=dependencies,
                            rule="unrelated" if role == "unrelated" else "native-specialization",
                            variant="controlled-1",
                            roles=(
                                dict(
                                    role=role,
                                    anchor_ids=tuple(a["anchor_id"] for a in anchors),
                                    head_token=0,
                                    expansion="exact",
                                    outcome="complete",
                                ),
                            ),
                        )
                    product["contribution_id"] = contribution_identity(product)
                    products.append(product)
                results.append(
                    replace(
                        draft,
                        ref=unit.ref,
                        contributions=tuple(products),
                        contribution_operations=tuple(
                            dict(operation, emitted_count=len(products))
                            if operation["operation_key"] == "locate-cell-1"
                            else operation
                            for operation in draft.contribution_operations
                        ),
                        contribution_coordinate_texts=tuple(
                            dict(c, pin=pin) for c in draft.contribution_coordinate_texts
                        )
                        + (
                            (
                                dict(
                                    pin=pin,
                                    space="native",
                                    pointer=case.table + "/data/table_cells/1",
                                    text="12",
                                ),
                            )
                            if overlapping_recipe is not None
                            else ()
                        ),
                    )
                )
            return tuple(results)

    start = semantic.start_run

    def select_original(conn, run):
        start(conn, run)
        select_source_view(
            conn,
            run_id=RunId(run),
            source_run_id=RunId(case.run),
            source_view_id=SourceViewId(case.view),
            projection_context=case.prepared,
        )

    monkeypatch.setattr(semantic, "start_run", select_original)

    def controlled_encoder(items, profile, **kwargs):
        vectors = []
        for item in items:
            digest = "c" * 64
            vid = identity(
                "context-vector",
                [
                    item.object_id,
                    item.source_binding,
                    profile.profile_id,
                    digest,
                    item.representation_digest,
                ],
            )
            vectors.append(
                EncodedVector(
                    vid,
                    item.object_id,
                    item.source_binding,
                    profile.profile_id,
                    digest,
                    (1.0,) + (0.0,) * (profile.dimension - 1),
                    item.representation_digest,
                )
            )
        return EncoderResult(profile.profile_id, (), tuple(vectors), ())

    def controlled_interpretation(**kwargs):
        witness = kwargs["witnesses"][0]
        kwargs["witnesses"] = (
            *kwargs["witnesses"],
            replace(
                witness,
                witness_id="controlled-comparison",
                relation="compared-with",
                basis="model_reading",
            ),
            replace(
                witness,
                witness_id="controlled-definition",
                relation="defined-by",
                basis="model_reading",
            ),
        )
        return select_relationships(**kwargs)

    monkeypatch.setattr(
        "corpus_structure.methods.contextual_candidates.verify_encoder_implementation", lambda _: ()
    )
    monkeypatch.setattr(
        "corpus_structure.methods.contextual_candidates.encode_contexts", controlled_encoder
    )
    if overlapping_recipe is None:
        monkeypatch.setattr(
            "corpus_structure.methods.contextual_candidates.select_relationships",
            controlled_interpretation,
        )

    # The current literal-only operation freezes its exact actual carriers. Settle
    # their native publication before constructing the retrieval configuration;
    # the later graph selects/reuses that same ordinary source producer.
    population = semantic.run_source_methods(
        case.writer,
        project_id="private-records",
        prepared=case.prepared,
        binding=OperationBinding(
            case.prepared.release_id, "wce-components", component_revision, b"{}"
        ),
        registry=MethodRegistry(
            [ActualOccurrenceProducer()],
            MethodsFile(configs={"private.records": {"default": {}}}),
        ),
        graph=Graph(((Stage.EXTRACT, (Step("private.records/default"),)),), policy_propose=False),
        method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
    )
    assert population.status == "source_ready"
    with case.writer.connect() as conn:
        tasks, results = table("ops.task"), table("ops.task_result")
        body = conn.execute(
            select(results.c.body)
            .select_from(tasks)
            .join(results, results.c.task_id == tasks.c.id)
            .where(tasks.c.run_id == population.run_id)
        ).scalar_one()
    cfg = ContextualQueryConfig(
        **parameters,
        required_occurrence_ids=tuple(
            sorted(
                {row["occurrence_id"] for row in body["contributions"] if "occurrence_id" in row}
            )
        ),
    )

    def produce_relationship(*, local_semantic_admission=()):
        return semantic.run_source_methods(
            case.writer,
            project_id="private-records",
            prepared=case.prepared,
            binding=OperationBinding(
                case.prepared.release_id, "wce-components", component_revision, b"{}"
            ),
            registry=MethodRegistry(
                [ActualOccurrenceProducer(), ContextualCandidatesWithQueryContext()],
                MethodsFile(
                    configs={
                        "private.records": {"default": {}},
                        "retrieve.contextual": {"default": cfg.model_dump(mode="json")},
                    }
                ),
            ),
            graph=Graph(
                (
                    (Stage.EXTRACT, (Step("private.records/default"),)),
                    (Stage.ASSEMBLE, (Step("retrieve.contextual/default"),)),
                ),
                policy_propose=False,
            ),
            method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
            local_semantic_admission=local_semantic_admission,
        )

    outcome = produce_relationship()
    assert outcome.status == "source_ready"
    with case.writer.connect() as conn:
        tasks, results, configs, methods = (
            table(n) for n in ("ops.task", "ops.task_result", "ops.method_config", "ops.method")
        )
        body = conn.execute(
            select(results.c.body)
            .join(tasks, tasks.c.id == results.c.task_id)
            .join(configs, configs.c.id == tasks.c.method_config_id)
            .join(methods, methods.c.id == configs.c.method_id)
            .where(tasks.c.run_id == outcome.run_id, methods.c.name == "retrieve.contextual")
        ).scalar_one()
        payload = body["contribution_operations"][0]["contextual_enrichment"]
        assert payload["version"] == "contextual-enrichment-2"
        assert {
            edge["relation"]
            for decision in payload["relationship_decisions"]
            for edge in decision["selected_edges"]
        } == (
            {"denotes", "compared-with", "defined-by"}
            if overlapping_recipe is None
            else {"specializes"}
        )
        assert payload["component_targets"][0]["reference"]["origin_task_id"] == task["id"]
        assert {c["semantic_type"] for c in body["contributions"]} == {
            "contextual.located_mention",
            "contextual.relationship",
        }
        assert all(
            w["support_state"] == "unassessed"
            for w in payload["relationship_decisions"][0]["witnesses"]
        )
    return SimpleNamespace(
        completed=completed,
        outcome=outcome,
        body=body,
        payload=payload,
        cfg=cfg,
        produce_relationship=produce_relationship,
    )


def authored_component_admission(completed, evaluator_engine):
    """Persist a literal, independently authored exact component authority fixture."""
    case = completed.case
    source = completed.source
    # Literal expectations are authored independently of the production statement projector.
    citation = dict(
        source=dict(
            project_id="private-records",
            native_product_key=source.native_product_key,
            native_content_digest=source.native_content_digest,
            projection_digest=source.projection_digest,
            recipe_digest=source.recipe_digest,
            coordinate_version=2,
        ),
        start=0,
        end=2,
        text="12",
        scope="controlled-source",
    )
    expected = dict(
        version="structural-public-statement-3",
        kind="definition_components",
        scope="controlled-source",
        coverage_limits=[],
        exclusions=[],
        definition_component=dict(
            term=citation, content=citation, interpretation="definition", scope="controlled-source"
        ),
    )
    frozen = StructuralEvaluationFrame(
        inputs=completed.inputs,
        operation="definition_components",
        direction="source_first",
        rubric_version="independent-definition-component-1",
        rubric_text=(
            "Controlled exact located attachment only, "
            "no usage applicability or semantic-quality claim."
        ),
        partition="development",
        source_groups=(
            StructuralSourceGroup(source_ref=source.identity, origin_group="controlled-source"),
        ),
        opportunities=(
            StructuralSourceOpportunity(
                opportunity_id="attachment",
                passage_id="literal",
                facet="attachment",
                source_state="stated",
            ),
        ),
        inspected_scope="literal",
    )
    reference = StructuralAuthoredReference(
        frame_digest=frozen.identity,
        cases=(
            StructuralReferenceCase(
                case_id="attachment",
                component_id=completed.component.component_id,
                facet="public_statement",
                path=("public_statement",),
                expected=expected,
                source_passages=("literal",),
                judgment="supported",
                explanation=(
                    "Controlled exact authority input; stronger applicability is unassessed."
                ),
            ),
        ),
    )
    with evaluator_engine.begin() as conn:
        assign_origin(
            conn,
            project_id="private-records",
            origin_group="controlled-source",
            partition="development",
            source_uris=("source.pdf",),
            provenance={"kind": "controlled-native-fixture"},
        )
        set_id = create_structural_reference_set(
            conn, project_id="private-records", release_id=case.prepared.release_id, frame=frozen
        )
        payload = canonical_bytes(reference.model_dump(mode="json", exclude_none=True))
        a = record_structural_reference_pass(
            conn, set_id=set_id, pass_kind="A", actor="independent-a", authored=payload
        )
        b = record_structural_reference_pass(
            conn, set_id=set_id, pass_kind="B", actor="independent-b", authored=payload
        )
        c = record_structural_reference_pass(
            conn,
            set_id=set_id,
            pass_kind="C",
            actor="independent-c",
            authored=payload,
            parents=(a, b),
        )
        digest = conn.scalar(
            select(table("eval.structural_reference_pass").c.content_digest).where(
                table("eval.structural_reference_pass").c.id == c
            )
        )
    admission = dict(
        product_id=completed.report.product_id,
        component_id=completed.component.component_id,
        set_id=set_id,
        c_pass_id=c,
        c_content_digest=digest,
        frame_digest=frozen.identity,
        policy_id="independent-definition-component-1",
    )

    return SimpleNamespace(
        admission=admission, expected=expected, frame=frozen, reference=reference
    )
