"""Actual M1 CPU continuation and provider questions publish through native demand custody."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path

import pytest
from semantic.data_operation_kernel_support import CapturedKernelInputs, Kernel, KernelRecipe
from semantic.data_operation_original_support import OriginalSeedRecipe
from semantic.native_record_fixtures import RecordSourceRecipe, claim_record_source
from semantic.original_source_fixture import completed_original_source_reference
from sqlalchemy import text

from corpus_structure.orchestrate.data_operations import NativeDemandExecutor
from corpus_structure.semantic.composed import (
    data_operation_dependencies,
    read_data_operation_inputs,
)
from corpus_structure.semantic.data_operation_artifacts import capture_port_generator_sources
from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
    DiscoverySelection,
    OperationSelection,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_storage import (
    DataOperationStorage,
    native_operation_declarations,
    native_protocol_sources,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.m1_products import (
    freeze_m1_configuration,
    m1_operation_inputs,
    m1_operation_sources,
)
from corpus_structure.semantic.original_documents import acquire_original_document_selection
from corpus_structure.semantic.source_admission import acquire_original_source_selection
from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.semantic.types import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)

ROOT = Path(__file__).resolve().parents[4]
SENTENCE = "The sample mean is the sum of the observations divided by the sample size."


def _recipe():
    from corpus_structure.orchestrate.m1 import registry

    schemas = SourceBundle(
        "statistics_semantic",
        tuple(
            SourceArtifact(name, (ROOT / path).read_bytes())
            for name, path in (
                ("statistics_semantic", "domains/statistics/semantic.yaml"),
                ("statistics_terminology", "domains/statistics/terminology.yaml"),
                (
                    "semantic_core",
                    "python/corpus-structure/src/corpus_structure/model/semantic/core.yaml",
                ),
            )
        ),
    )
    cfg = registry(ROOT / "domains/statistics").overlay("extract.m1_candidates", "default")
    # This is an explicit supported producer profile, with no undeclared rule or
    # formal input and no extra local question. Family semantics remain original.
    cfg = freeze_m1_configuration(
        cfg.model_copy(
            update={
                "annotation_rules": (),
                "formula_syntax": False,
                "local_schema": None,
                "region_pointers": ("#/texts/0",),
                "max_context_chars": 512,
            }
        )
    )
    bundle = m1_operation_inputs(schemas)
    sources = m1_operation_sources(cfg, record_schemas=schemas)
    native = native_protocol_sources()
    dependencies = data_operation_dependencies(
        ResolvedDependencies((*native, *capture_port_generator_sources())),
        (native_operation_declarations(native),),
        sources,
    )
    return KernelRecipe(
        "actual-m1-selected-source",
        "",
        None,
        "",
        execution_profile="execution:m1-native",
        project_id=None,
        captured_inputs=CapturedKernelInputs(
            bundle, dependencies, PreparationProfile(version="semantic-2")
        ),
    )


@contextmanager
def _case(scenario_seeds, *, empty):
    target = _recipe()
    recipe = OriginalSeedRecipe(RecordSourceRecipe(sibling_captions=(SENTENCE,)), target)
    with scenario_seeds.commit_clone(recipe) as clone:
        stage = clone.stage
        kernel = Kernel(
            clone.admin, stage.kernel.preparation, stage.kernel.identities, target, clone
        )
        source = claim_record_source(stage.source, writer=clone.writer, clone=clone)
        reference, _ = completed_original_source_reference(source)
        with clone.admin.begin() as connection:
            other = load_source_view(connection, source.other_view, analysis=False)
            reference = reference.model_copy(
                update={
                    "source_view_id": source.other_view,
                    "projection_digest": other.ref.projection_digest,
                    "recipe_digest": other.ref.recipe_digest,
                }
            )
            selectors = [
                dict(
                    projection=reference.projection_digest,
                    **({"start": 0, "end": 0} if empty else {}),
                )
            ]
            selected = acquire_original_source_selection(
                connection, kernel.prepared, reference, selectors, name="selected-view"
            )
            original = acquire_original_document_selection(
                connection,
                project_id=source.project_id,
                document_key=selected.root.original_source,
                name="original-document",
            )
            intent = freeze_demand(
                kernel.model,
                roots=(original.root,),
                targets=("source.selected_views/discovery",),
                selections=(
                    OperationSelection(
                        "source.selected_views/discovery",
                        parameters=canonical_bytes({"complete": True}),
                    ),
                ),
                discovery=tuple(
                    DiscoverySelection(
                        "source.selected_views/discovery",
                        "result",
                        "extract.m1_candidates",
                        population,
                    )
                    for population in ("m1-primary-source", "m1-context-sources")
                ),
                inference="m1-native-test",
                execution_profile=target.execution_profile,
                original_sources=(original.selection(), selected.selection()),
            )
            demand = DemandPlanner(kernel.model, DataOperationStorage(connection)).register(
                intent,
                project=source.project_id,
                release=kernel.prepared.release_id,
                runtime=kernel.runtime,
            )["demand_id"]
        acquired = read_data_operation_inputs(kernel.preparation.dependencies)
        assert acquired is not None and acquired[1] is not None
        captured = acquired[1]
        executor = NativeDemandExecutor(
            clone.writer,
            kernel.prepared,
            kernel.preparation.runtime,
            captured,
            runtime_locations={item.module: Path(item.filename) for item in captured.sources},
            schema=kernel.preparation.bundle,
            admission_engine=clone.purpose("admit"),
        )
        yield kernel, source, selected, demand, executor


def _m1_result(kernel, demand):
    with kernel.engine.begin() as connection:
        result = DataOperationStorage(connection).invoke(
            "read_demand_result", {"demand_id": demand, "view": "products"}
        )
        completions = (
            connection.execute(
                text(
                    "SELECT i.payload FROM ops.data_completion_intent i JOIN ops.data_request r ON r.id=i.request_id WHERE r.operation_id='extract.m1_candidates'"
                )
            )
            .scalars()
            .all()
        )
    assert len(completions) == 1, result
    completion = completions[0]
    if isinstance(completion, str):
        completion = json.loads(completion)
    completion = completion.get("completion", completion)
    assert completion["outcome"] == "success"
    report = decode_semantic_value(completion["outputs"][0]["product"]["body"])
    assert any(
        use["fate"] == "fulfilled"
        and any(
            product["body"] == completion["outputs"][0]["product"]["body"]
            for product in use["products"]
        )
        for use in result["uses"]
    )
    return report, completion["execution_evidence"]


def test_actual_m1_cpu_empty_scope_publishes_exact_empty_inspection_and_resumes(scenario_seeds):
    with _case(scenario_seeds, empty=True) as (kernel, _source, selected, demand, executor):
        executed = executor.run(demand)
        report, evidence = _m1_result(kernel, demand)
        assert executed.receipt_count >= 3
        assert report["inspection_outcome"] == "empty" and report["members"] == []
        assert report["source_pin"]["original_source"] == selected.root.original_source
        assert report["source_pin"]["analyzed_scope_meaning"]
        assert evidence["host_receipts"] == [] and evidence.get("provider_receipts", []) == []
        (cpu,) = evidence["cpu_receipts"]
        assert cpu["pid"] != os.getpid() and cpu["pid"] > 0
        # A clipped/unselected native atom is never promoted to complete absence.
        assert report["coverage"] and all(
            row["outcome"] != "complete" for row in report["coverage"]
        )
        assert executor.budget.used_bytes == 0
        assert executor.run(demand).receipt_count == 0


@pytest.mark.gpu
@pytest.mark.provider_evidence
@pytest.mark.prerequisite("pm2_native_assets")
def test_actual_m1_bounded_gliner_questions_publish_candidate_inspection_with_cohort_custody(
    scenario_seeds,
):
    with _case(scenario_seeds, empty=False) as (kernel, _source, selected, demand, executor):
        executed = executor.run(demand)
        report, evidence = _m1_result(kernel, demand)
        assert executed.receipt_count >= 3
        assert report["inspection_outcome"] in {"produced", "empty"}
        assert report["source_pin"]["original_source"] == selected.root.original_source
        assert report["standing"] == "private_uncalibrated_candidates"
        diagnostics = json.loads(report["diagnostics_json"])
        assert "producer_failure" not in diagnostics
        assert evidence["cpu_receipts"] and evidence["host_receipts"] == []
        receipts = evidence["provider_receipts"]
        assert receipts and all(receipt["physical"] for receipt in receipts)
        assert all(receipt["logical_members"] for receipt in receipts)
        assert all(
            member["request_id"] == evidence["request_id"]
            and member["generation"] == evidence["generation"]
            and member["task_id"] == evidence["task_id"]
            and member["attempt"] == evidence["attempt"]
            for receipt in receipts
            for member in receipt["logical_members"]
        )
        assert all(
            packet["body"]["pin"]["source_product"] == report["source_pin"]["source_product"]
            for packet in report["members"]
        )
        assert executor.budget.used_bytes == 0
        assert executor.run(demand).receipt_count == 0
