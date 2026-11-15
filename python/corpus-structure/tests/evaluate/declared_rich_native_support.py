"""Actual protected reading/fit/issuer inputs for current rich native admission.

The converter and record extractor remain explicitly controlled. No run aliases,
standalone accepted graphs, fabricated native receipts or copied protected labels
supply this journey's authority.
"""

from dataclasses import dataclass
from typing import Any

import pytest
from evaluate.declared_record_native_support import (
    PROJECT,
    ROOT,
    CurrentRecordPolicyJourney,
    ReadingPopulation,
    authored,
    current_record_policy_journey,
    policy_recipe,
    project_context,
    request,
)
from semantic.data_operation_kernel_support import CapturedKernelInputs, KernelRecipe

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.types import ResolvedDependencies

NAMESPACE = "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/"


def rich_policy_recipe(directory):
    from corpus_structure.semantic.composed import (
        data_operation_dependencies,
        read_data_operation_inputs,
    )
    from corpus_structure.semantic.math_context import acquire_analysis_context_profile
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from corpus_structure.semantic.rich_invocations import rich_knowledge_operation_sources
    from corpus_structure.semantic.rich_knowledge_sources import (
        rich_knowledge_declarations,
        rich_knowledge_schema_inputs,
        rich_policy_inputs,
    )

    original = policy_recipe(directory)
    captured = original.captured_inputs
    assert captured is not None
    acquired = read_data_operation_inputs(captured.dependencies)
    assert acquired is not None and acquired[1] is not None
    declarations, sources = acquired
    assert sources is not None
    dependencies = ResolvedDependencies(
        tuple(
            artifact
            for artifact in captured.dependencies.artifacts
            if not artifact.name.startswith("data-operations/")
        ),
        captured.dependencies.vocabularies,
        captured.dependencies.ontology_sources,
    )
    bundle, dependencies = rich_knowledge_schema_inputs(
        captured.bundle,
        dependencies,
        qualification_class="StatisticsQualification",
        statement_class="SourceStatement",
    )
    dependencies = rich_policy_inputs(
        dependencies,
        (ROOT / "domains/statistics/schema/rules.yaml").read_bytes(),
        (ROOT / "domains/core/schema/rules.yaml").read_bytes(),
        context_profile=acquire_analysis_context_profile(),
    )
    dependencies = data_operation_dependencies(
        dependencies,
        (*declarations, *rich_knowledge_declarations(dependencies)),
        combine_primary_sources(sources, rich_knowledge_operation_sources()),
    )
    return KernelRecipe(
        "current-rich-record-policy",
        "",
        None,
        "",
        project_id=None,
        execution_profile=original.execution_profile,
        captured_inputs=CapturedKernelInputs(bundle, dependencies, captured.profile),
    )


@pytest.fixture
def current_rich_policy(scenario_seeds, tmp_path, monkeypatch):
    with current_record_policy_journey(
        scenario_seeds, tmp_path, monkeypatch, recipe=rich_policy_recipe(tmp_path)
    ) as journey:
        yield journey


def selected_entry(row):
    from corpus_structure.semantic.data_operation_source_sets import SourceSetEntry
    from corpus_structure.semantic.data_product_reference import DataProductReference

    return SourceSetEntry.from_semantic_source(
        DataProductReference(row["id"]),
        context=SubjectContext(
            PROJECT,
            row["subject"],
            row["original_source"],
            json_bytes(row["analyzed_scope"]),
            subject_definition=row["subject_definition"],
        ),
    )


@dataclass(frozen=True)
class RichAdmissionSelection:
    journey: CurrentRecordPolicyJourney
    demand_id: str
    product: dict[str, Any]
    admission: Any
    consolidation: Any
    cut: Any
    episode: str


def run_rich_admission(
    journey,
    readings: ReadingPopulation,
    authorization,
    *,
    selected_source,
    inference,
    policy_contracts=None,
):
    from corpus_structure.semantic.data_operation_service import execute_data_demand
    from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet
    from corpus_structure.semantic.rich_knowledge_contracts import (
        DdoRichAdmission,
        DdoRichConsolidation,
    )
    from corpus_structure.semantic.rich_policy_binding import rich_policy_value
    from corpus_structure.serve.interpretation_authoring import author_interpretations

    raw = tuple(
        (row, body)
        for row, body in readings.raw
        if body["source_pin"]["source"] == selected_source.pin.source
    )
    resolved = tuple(
        (row, body)
        for row, body in readings.resolved
        if body["source_pin"]["source"] == selected_source.pin.source
    )
    assert len(raw) == len(resolved) == 1
    context = project_context(journey, "rich.consolidate")
    policy = rich_policy_value(
        journey.kernel.prepared, journey.kernel.model, allowed_domain_contracts=policy_contracts
    )
    fact = authored(
        journey,
        inference + ":checked-rich-policy",
        policy.model_dump(mode="python"),
        kind=NAMESPACE + "DdoRichConsolidationPolicy",
        context=context,
    )
    source_sets = (
        *tuple(
            FrozenSourceSet(name, ())
            for name in (
                "rich-proposals",
                "rich-proposal-contexts",
                "rich-authored-propositions",
                "rich-known-universe",
            )
        ),
        FrozenSourceSet("rich-records", tuple(selected_entry(row) for row, _ in raw)),
        FrozenSourceSet("rich-readings", tuple(selected_entry(row) for row, _ in resolved)),
        FrozenSourceSet("rich-policy-authorizations", (selected_entry(authorization),)),
    )
    pending = request(
        journey,
        ("rich.consolidate", "rich.admit"),
        (context,),
        originals=(fact,),
        source_sets=source_sets,
        inference=inference,
    )
    retained = author_interpretations(
        journey.kernel.purpose("write"), journey.kernel.prepared, request=pending
    )
    result = execute_data_demand(
        journey.kernel.purpose("write"),
        retained["demand_id"],
        source_root=ROOT,
        admission_engine=journey.kernel.purpose("admit"),
        project_id=PROJECT,
        database_capacity=6,
    )
    assert result.receipt_count == 2
    cut, products, _uses, _episodes, outputs = journey.selected_products(
        journey.kernel.purpose("write"),
        retained["demand_id"],
        kind=(NAMESPACE + "DdoRichAdmission", NAMESPACE + "DdoRichConsolidation"),
    )
    kinds = {
        identity.owner: identity.key
        for identity in journey.kernel.model.identities
        if identity.domain == "kind"
    }
    ((product, body),) = [
        (row, value)
        for row, value in products
        if row["kind_contract"] == kinds[NAMESPACE + "DdoRichAdmission"]
    ]
    ((_, consolidation),) = [
        (row, value)
        for row, value in products
        if row["kind_contract"] == kinds[NAMESPACE + "DdoRichConsolidation"]
    ]
    return RichAdmissionSelection(
        journey,
        retained["demand_id"],
        product,
        DdoRichAdmission.model_validate(body),
        DdoRichConsolidation.model_validate(consolidation),
        cut,
        next(
            row["derivation_id"]
            for row in outputs
            if row["product_id"] == product["id"] and row["role"] == "admission"
        ),
    )
