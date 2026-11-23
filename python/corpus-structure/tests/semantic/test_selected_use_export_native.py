"""Consumed-use readers over actual native publication and verified exported rows."""

from dataclasses import replace

import pytest
from evaluate.declared_record_native_support import (
    PROJECT,
    authored,
    current_record_policy_journey,
    project_context,
    request,
)
from evaluate.declared_rich_native_support import rich_policy_recipe

from corpus_structure.semantic.grouped_interpretation_projection import grouped_interpretation_rows
from corpus_structure.semantic.grouped_record_interpretations import (
    GroupedInterpretationRequest,
    InterpretationRoot,
)
from corpus_structure.semantic.selected_contribution_input import SelectedContributionScope
from corpus_structure.semantic.value_codec import decimal_digit_limit
from corpus_structure.serve.demand_export import export_demand_result, verified_demand_export
from semantic.rich_domain_native_support import publish_domain
from semantic.rich_domain_preservation_support import DomainGraph, t2


@pytest.fixture
def selected_use_journey(scenario_seeds, tmp_path, monkeypatch):
    from corpus_structure.semantic.composed import data_operation_dependencies
    from corpus_structure.semantic.finite_interpretation_products import (
        finite_interpretation_declarations,
        finite_interpretation_inputs,
        finite_interpretation_operation_sources,
    )
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from semantic.data_operation_kernel_support import (
        CapturedKernelInputs,
        split_captured_operations,
    )

    recipe = rich_policy_recipe(tmp_path)
    captured = recipe.captured_inputs
    assert captured is not None
    dependencies, declarations, sources = split_captured_operations(captured)
    dependencies = data_operation_dependencies(
        dependencies,
        (*declarations, finite_interpretation_declarations()),
        combine_primary_sources(sources, finite_interpretation_operation_sources()),
    )
    recipe = replace(
        recipe,
        name="selected-use-finite-rich",
        captured_inputs=CapturedKernelInputs(
            finite_interpretation_inputs(captured.bundle),
            dependencies,
            captured.profile,
        ),
    )
    with current_record_policy_journey(
        scenario_seeds, tmp_path, monkeypatch, recipe=recipe, source_count=1
    ) as journey:
        yield journey


def test_native_exported_finite_and_rich_readers_keep_exact_consumed_use(
    selected_use_journey, tmp_path
):
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet
    from corpus_structure.semantic.observations import source_value
    from corpus_structure.serve.interpretation_authoring import author_interpretations
    from semantic.data_operation_kernel_support import execute_captured_kernel_demand

    journey = selected_use_journey
    source = journey.sources[0]
    pending = request(
        journey,
        ("fixture.record_candidates", "interpret.finite_candidates"),
        (source.context,),
        originals=(
            authored(
                journey,
                "selected-use:question",
                {
                    "source_pin_json": json_bytes(
                        source.pin.model_dump(mode="json", exclude_none=True)
                    ).decode(),
                    "empty": False,
                },
                kind="https://example.test/current-record-policy/FixtureCandidateQuestion",
                context=source.context,
            ),
            authored(
                journey,
                "selected-use:finite-policy",
                {
                    "version": "finite-interpretation-policy-1",
                    "mode": "records",
                    "requests": source_value({}),
                    "dependencies": [],
                },
                kind="https://corpus-structure.dev/semantic/data-operation-interpretation/DdoFiniteInterpretationPolicy",
                context=source.context,
            ),
        ),
        source_sets=(FrozenSourceSet.from_selected("fixture-record-sources", (source.entry(),)),),
        inference="selected-use-export",
    )
    retained = author_interpretations(
        journey.kernel.purpose("write"), journey.kernel.prepared, request=pending
    )
    execution = execute_captured_kernel_demand(journey.kernel, retained["demand_id"])
    assert execution.receipt_count == 2
    _, products, _, _, _ = journey.selected_products(
        journey.kernel.purpose("read"),
        retained["demand_id"],
        kind=(
            "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
            "https://corpus-structure.dev/semantic/data-operation-interpretation/DdoFiniteInterpretationProduct",
        ),
    )
    raw_id = next(row["id"] for row, body in products if "reports" not in body)
    selection = GroupedInterpretationRequest(
        project_id=PROJECT,
        demand_id=retained["demand_id"],
        roots=tuple(InterpretationRoot(product_id=row["id"]) for row, _ in products),
    )
    destination = tmp_path / "finite"
    with journey.kernel.purpose("read").begin() as connection:
        receipt = export_demand_result(
            connection,
            retained["demand_id"],
            project_id=PROJECT,
            destination=destination,
            format="parquet",
            page_rows=1,
        )
    with verified_demand_export(destination, manifest_digest=receipt.manifest_digest) as (
        manifest,
        prepared,
        models,
        index,
    ):
        release = manifest.cut["release_id"]
        selected = SelectedContributionScope(
            manifest.cut_selection,
            index,
            prepared[release],
            models[release],
            {},
            100000,
            decimal_fixed_point_digits=decimal_digit_limit(),
        )
        assert all("binding" not in row for row in index.rows("ops.data_request"))
        groups, metadata = grouped_interpretation_rows(selected, selection, ())
        assert groups and len(metadata["finite_universes"]) == 1
        assert {row["candidate_product_id"] for row in metadata["finite_universes"]} == {raw_id}

    graph = DomainGraph(
        (journey.kernel.prepared, journey.kernel.model, "StatisticsQualification"),
        {
            "normal": "DistributionFamily",
            "X": "RandomVariable",
            **{
                key: "FamilyParameter"
                for key in ("location", "scale", "mean", "standard_deviation")
            },
        },
        context=project_context(journey, "rich.consolidate"),
    )
    t2(graph)
    publication = publish_domain(journey, graph, inference="selected-use-rich-export")
    destination = tmp_path / "rich"
    with journey.kernel.purpose("read").begin() as connection:
        receipt = export_demand_result(
            connection,
            publication.demand_id,
            project_id=PROJECT,
            destination=destination,
            format="parquet",
            page_rows=1,
        )
    with verified_demand_export(destination, manifest_digest=receipt.manifest_digest) as (
        manifest,
        prepared,
        models,
        index,
    ):
        release = manifest.cut["release_id"]
        selected = SelectedContributionScope(
            manifest.cut_selection,
            index,
            prepared[release],
            models[release],
            {},
            100000,
            decimal_fixed_point_digits=decimal_digit_limit(),
        )
        assert all("binding" not in row for row in index.rows("ops.data_request"))
        private = next(
            row
            for row in selected.products()
            if row.reference.product_id == publication.consolidation_product["id"]
        )
        state = selected.graph(private)
        assert state.graph.model_dump(mode="python") == publication.consolidation.model_dump(
            mode="python"
        )
