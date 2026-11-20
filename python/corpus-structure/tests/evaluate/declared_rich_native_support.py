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
    FittedJourney,
    ReadingPopulation,
    authored,
    current_record_policy_journey,
    policy_recipe,
    project_context,
    request,
)
from semantic.data_operation_kernel_support import (
    CapturedKernelInputs,
    KernelRecipe,
    execute_captured_kernel_demand,
    split_captured_operations,
)

from corpus_structure.semantic.data_operation_source_sets import SelectedSourceSetEntry

NAMESPACE = "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/"


def rich_policy_recipe(directory):
    from corpus_structure.semantic.composed import (
        data_operation_dependencies,
    )
    from corpus_structure.semantic.effect_policy import ApprovedEffect
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
    base_dependencies, declarations, sources = split_captured_operations(captured)
    dependencies = base_dependencies
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
        effect_approvals=(
            *original.effect_approvals,
            ApprovedEffect("rich.admit", "native-rich-knowledge-admission"),
        ),
        captured_inputs=CapturedKernelInputs(bundle, dependencies, captured.profile),
    )


@pytest.fixture
def current_rich_policy(scenario_seeds, tmp_path, monkeypatch):
    with current_record_policy_journey(
        scenario_seeds, tmp_path, monkeypatch, recipe=rich_policy_recipe(tmp_path)
    ) as journey:
        yield journey


def selected_entry(row):
    """Use the retained selected packet, never recover support from product identity."""
    (entry,) = row["_selected_entries"]
    return entry


def selected_policy_authorization(fitted: FittedJourney) -> SelectedSourceSetEntry:
    from corpus_structure.semantic.demand_results import read_demand_result

    scope = {
        "operation_id": "record_policy.authorize",
        "product_ids": [fitted.authorization_product_id],
    }
    with fitted.journey.kernel.purpose("write").begin() as connection:
        page = read_demand_result(connection, fitted.demand_id, project_id=PROJECT, scope=scope)
    (header,) = page.members()
    assert header["product_id"] == fitted.authorization_product_id
    assert header["body"] == fitted.authorization
    assert page.cut.record["scope"] == scope
    assert page.cut.record["selection"]["version"] == "data-demand-public-selection-v1"
    entry = SelectedSourceSetEntry.from_selected_header(header, page.cut)
    assert entry.read.cut_id == page.cut.identity
    return entry


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
    authorization: SelectedSourceSetEntry,
    *,
    selected_source,
    inference,
):
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
    policy = rich_policy_value(journey.kernel.prepared, journey.kernel.model)
    fact = authored(
        journey,
        inference + ":checked-rich-policy",
        policy.model_dump(mode="python"),
        kind=NAMESPACE + "DdoRichConsolidationPolicy",
        context=context,
    )
    source_sets = (
        *tuple(
            FrozenSourceSet.from_selected(name, ())
            for name in (
                "rich-proposals",
                "rich-proposal-contexts",
                "rich-authored-propositions",
                "rich-known-universe",
            )
        ),
        FrozenSourceSet.from_selected("rich-records", tuple(selected_entry(row) for row, _ in raw)),
        FrozenSourceSet.from_selected(
            "rich-readings", tuple(selected_entry(row) for row, _ in resolved)
        ),
        FrozenSourceSet.from_selected("rich-policy-authorizations", (authorization,)),
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
    result = execute_captured_kernel_demand(
        journey.kernel,
        retained["demand_id"],
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
