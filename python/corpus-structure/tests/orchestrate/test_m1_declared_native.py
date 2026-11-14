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
from corpus_structure.semantic.terminology import acquire_terminology
from corpus_structure.semantic.types import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)

ROOT = Path(__file__).resolve().parents[4]
SENTENCE = "The sample mean is the sum of the observations divided by the sample size."


def _recipe():
    from methods.domain_configuration import candidate_configuration

    terminology, vocabulary_assets, ontology_sources = acquire_terminology(
        ROOT / "domains/statistics"
    )
    schemas = SourceBundle(
        "statistics_semantic",
        (
            *tuple(
                SourceArtifact(name, (ROOT / path).read_bytes())
                for name, path in (
                    ("statistics_semantic", "domains/statistics/semantic.yaml"),
                    (
                        "semantic_core",
                        "python/corpus-structure/src/corpus_structure/model/semantic/core.yaml",
                    ),
                )
            ),
            *terminology,
        ),
    )
    cfg = candidate_configuration(ROOT / "domains/statistics", "default")
    # This is an explicit supported producer profile, with no undeclared rule or
    # formal input and no extra local question. Family semantics remain original.
    cfg = freeze_m1_configuration(
        cfg.model_copy(
            update={
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
        ResolvedDependencies(
            (*native, *capture_port_generator_sources(), *vocabulary_assets),
            ontology_sources=ontology_sources,
        ),
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
            from corpus_structure.semantic.data_operation_source_discovery import (
                source_discovery_relations,
            )

            operation = "extract.m1_candidates"
            required = {
                operation,
                *kernel.model.projection_graph("selected-dependencies").closure((operation,)),
            }
            discovery = tuple(
                relation
                for target_operation in sorted(required)
                for relation in source_discovery_relations(
                    kernel.model, "source.selected_views/discovery", "result", target_operation
                )
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
                discovery=discovery,
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
            "read_demand_result",
            {"demand_id": demand, "view": "products", "limit": 100, "max_bytes": 8388608},
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
        candidate_facts = []
        if len(completions) != 1:
            child = next(
                row
                for row in result["obligations"]
                if row["operation_id"] == "extract.m1_candidates"
            )
            candidate_facts = [
                dict(row)
                for row in connection.execute(
                    text(
                        "SELECT product, kind_contract, subject, original_source, analyzed_scope, member, multiplicity, support_episodes, alternative_identity "
                        "FROM ops.data_binding_rows(:demand,'extract.m1_candidates',CAST(:trust AS jsonb),:read,:subject,:source,CAST(:scope AS jsonb))"
                    ),
                    {
                        "demand": demand,
                        "trust": json.dumps(result["trust_snapshot"]),
                        "read": result["read_id"],
                        "subject": child["subject"],
                        "source": child["original_source"],
                        "scope": json.dumps(child["analyzed_scope"]),
                    },
                ).mappings()
            ]
    names = {row["obligation_id"]: row["operation_id"] for row in result["obligations"]}
    diagnostic = {
        "fates": [
            {
                "operation": names.get(row["obligation_id"]),
                "fate": row["fate"],
                "reasons": row["selection"].get("reasons"),
            }
            for row in result["uses"]
            if row["fate"] != "fulfilled"
        ],
        "failures": result.get("attempt_failures"),
        "facts": candidate_facts,
    }
    assert len(completions) == 1, json.dumps(diagnostic, sort_keys=True)
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


def test_native_consumed_producers_follow_only_targeted_frozen_discovery(native_read):
    selected = {
        "operations": [
            {"operation": "consumer", "dependencies": ["annotations"]},
            {"operation": "annotations", "dependencies": []},
            {"operation": "views", "dependencies": ["capture"]},
            {"operation": "capture", "dependencies": []},
            {"operation": "unrelated", "dependencies": []},
            {"operation": "other-consumer", "dependencies": []},
        ],
        "discovery": [
            {"producer": "views", "target": "consumer"},
            {"producer": "unrelated", "target": "other-consumer"},
        ],
    }
    actual = native_read.scalar(
        text("SELECT ops.ddo_consumed_producers(CAST(:selection AS jsonb), :operation)"),
        {"selection": json.dumps(selected), "operation": "consumer"},
    )
    assert actual == ["annotations", "capture", "consumer", "views"]
    selected["discovery"] = selected["discovery"][1:]
    without = native_read.scalar(
        text("SELECT ops.ddo_consumed_producers(CAST(:selection AS jsonb), :operation)"),
        {"selection": json.dumps(selected), "operation": "consumer"},
    )
    assert without == ["annotations"]
