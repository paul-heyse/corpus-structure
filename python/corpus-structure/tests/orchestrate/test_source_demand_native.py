"""Bounded actual ordinary-source demand, scoped fan-in and demand-only recovery."""

from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import select, text

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.core.method import MethodSettings
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.orchestrate.source_operation import prepare_source_demand, run_source_operation
from corpus_structure.orchestrate.source_request import (
    RetainedSourceSelection, SourceRunRequest, WholeDocument,
)
from corpus_structure.semantic import SourceArtifact, SourceBundle
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_service import execute_data_demand, read_data_demand
from corpus_structure.semantic.hanlp_products import prepare_hanlp_selection
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.primary_operations import primary_operation_inputs
from corpus_structure.semantic.source_views import load_source_view
from semantic.data_operation_kernel_support import CapturedKernelInputs, Kernel, KernelRecipe
from semantic.data_operation_original_support import OriginalSeedRecipe
from semantic.native_record_fixtures import RecordSourceRecipe, claim_record_source
from semantic.original_source_fixture import completed_original_source_reference

ROOT = Path(__file__).resolve().parents[4]
PASSAGES = (
    "A random variable has an expected value. Its variance measures dispersion.",
    "Independent observations form a sample. The sample mean estimates the population mean.",
)


def _recipe(assets):
    inputs = primary_operation_inputs(
        SourceBundle("toy_semantic", (
            SourceArtifact("toy_semantic", (ROOT / "domains/toy/semantic.yaml").read_bytes()),
            SourceArtifact("semantic_core", (ROOT / "python/corpus-structure/src/corpus_structure/model/semantic/core.yaml").read_bytes()),
        )),
        sentence_configuration=SentenceConfig(exclude=("ner", "lemmatizer")),
        hanlp_selection=prepare_hanlp_selection(assets),
    )
    return KernelRecipe(
        "ordinary-primary-source-demand", "", None, "", project_id=None,
        source_stage="private-source", execution_profile="source-native",
        captured_inputs=CapturedKernelInputs(inputs.bundle, inputs.dependencies, inputs.profile),
    )


@pytest.fixture
def primary_source_case(scenario_seeds):
    assets = Path(os.environ["CORPUS_PM2_NATIVE_TEST_ASSETS"])
    recipe = OriginalSeedRecipe(RecordSourceRecipe(sibling_captions=PASSAGES), _recipe(assets))
    with scenario_seeds.commit_clone(recipe) as clone:
        kernel = Kernel(clone.admin, clone.stage.kernel.preparation, clone.stage.kernel.identities, recipe.target, clone)
        retained = claim_record_source(clone.stage.source, writer=clone.writer, clone=clone)
        reference, _ = completed_original_source_reference(retained)
        with clone.admin.connect() as connection:
            views = table("kb.source_view")
            row = connection.execute(select(views).where(views.c.id == retained.other_view)).mappings().one()
            reference = reference.model_copy(update={
                "source_view_id": row["id"], "native_task_id": row["native_task_id"],
                "native_product_key": row["native_product_key"],
                "native_content_digest": row["native_content_digest"],
                "projection_digest": row["projection_digest"], "recipe_digest": row["recipe_digest"],
            })
            view = load_source_view(connection, row["id"], analysis=False)
        selections = tuple(RetainedSourceSelection(
            source=reference,
            selectors=({"projection": reference.projection_digest, "native_pointer": next(
                item["self_ref"] for item in view.items if item.get("text") == passage
            )},),
        ) for passage in PASSAGES)
        request = SourceRunRequest(
            project_id=retained.project_id, release_id=kernel.prepared.release_id,
            runtime_id=kernel.runtime, domain="toy", workflow="characterize",
            selection=WholeDocument(), retained_sources=selections,
        )
        yield clone, kernel, request


def _products(snapshot):
    return [product for use in snapshot["uses"] for product in use["products"]]


@pytest.mark.gpu
@pytest.mark.provider_evidence
@pytest.mark.prerequisite("pm2_native_assets")
def test_two_language_regions_use_native_source_demand_and_exact_resume(primary_source_case, tmp_path):
    clone, kernel, request = primary_source_case
    methods = MethodSettings(data_dir=tmp_path, model_cache=tmp_path)
    with clone.admin.connect() as connection:
        builds_before = connection.scalar(text("SELECT count(*) FROM ops.pdf_build"))
        frozen = prepare_source_demand(connection, request)
    selected = {value.operation: value for value in frozen.selections}
    assert selected["source.selected_views/discovery"].parameters == {"complete": True}
    assert set(selected["text.compose_view/full-native"].selected_dependencies) == {
        "segment.sentences/source-native", "segment.sentences/canonical-projection",
        "text.hanlp_native/source-native", "text.formal_evidence/source-native",
        "text.constructions/source-native", "text.contextual_evaluation/source-native",
    }
    result = run_source_operation(
        kernel.purpose("write"), request, methods, source_root=ROOT,
        admission_engine=kernel.purpose("admit"),
    )
    with clone.admin.begin() as connection:
        snapshot = read_data_demand(connection, result.demand_id, view="products")
        builds_after = connection.scalar(text("SELECT count(*) FROM ops.pdf_build"))
    assert builds_after == builds_before, "retained sources must never recapture their original"
    assert all(value["fate"] == "fulfilled" for value in snapshot["obligations"]), snapshot["obligations"]
    document_obligations = [value for value in snapshot["obligations"] if value["operation_id"] in {
        "source.selected_views/discovery", "text.compose_view/full-native",
    }]
    assert len(document_obligations) == 2
    for operation in selected["text.compose_view/full-native"].selected_dependencies:
        children = [value for value in snapshot["obligations"] if value["operation_id"] == operation]
        assert len(children) == 2 and len({str(value["analyzed_scope"]) for value in children}) == 2
        assert all(value["subject"] != frozen.roots[0].subject for value in children)
    products = _products(snapshot)
    assert products and all(value["body_state"] == "present" for value in products)
    bodies = [decode_semantic_value(value["body"]) for value in products]
    source_bodies = [
        member["body"] for value in bodies
        if isinstance(value, dict) and "document" in value and "members" in value
        for member in value["members"]
        if isinstance(member.get("body"), dict) and "text" in member["body"]
    ]
    assert len(source_bodies) == 2
    assert {value["selectors"][0]["native_pointer"] for value in source_bodies} == {
        value.selectors[0]["native_pointer"] for value in request.retained_sources
    }
    assert all(value["source"]["document"] == frozen.roots[0].original_source for value in source_bodies)
    # Capacity changes are physical. Recovery consumes the original immutable
    # demand and must not synthesize another run anchor or repeat provider work.
    resumed = execute_data_demand(
        kernel.purpose("write"), result.demand_id, source_root=ROOT,
        policy=replace(methods.execution_policy, workers=1, max_regions=1),
        admission_engine=kernel.purpose("admit"),
    )
    assert resumed.demand_id == result.demand_id and resumed.receipt_count == 0
    assert result.receipts and all(json.loads(value)["physical"] for value in result.receipts)


@pytest.mark.gpu
@pytest.mark.provider_evidence
@pytest.mark.prerequisite("pm2_native_assets")
def test_empty_selected_source_population_closes_without_invented_language_products(primary_source_case, tmp_path):
    clone, kernel, request = primary_source_case
    # The source owner explicitly closes an empty examined selection. This is
    # different from incomplete discovery; no fabricated source/language work is due.
    from corpus_structure.semantic.data_operation_service import create_native_demand

    with clone.admin.begin() as connection:
        frozen = prepare_source_demand(connection, request)
        empty = frozen.model_copy(update={"original_sources": {
            key: value for key, value in frozen.original_sources.items() if key.startswith("original:")
        }})
        snapshot = create_native_demand(connection, empty)
    result = execute_data_demand(
        kernel.purpose("write"), snapshot["demand_id"], source_root=ROOT,
        admission_engine=kernel.purpose("admit"),
    )
    with clone.admin.begin() as connection:
        snapshot = read_data_demand(connection, result.demand_id, view="products")
    assert all(value["fate"] == "fulfilled" for value in snapshot["obligations"])
    assert {value["operation_id"] for value in snapshot["obligations"]} == {
        "source.selected_views/discovery", "text.compose_view/full-native",
    }
    assert len(snapshot["populations"]) >= 1
    assert all(value["complete"] and not value["members"] for value in snapshot["populations"])
