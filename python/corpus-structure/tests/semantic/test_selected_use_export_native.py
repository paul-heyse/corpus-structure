"""Consumed-use readers over actual native publication and verified exported rows."""

from evaluate.declared_record_native_support import PROJECT, project_context, run_readings
from evaluate.declared_rich_native_support import current_rich_policy as current_rich_policy

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


def test_native_exported_finite_and_rich_readers_keep_exact_consumed_use(
    current_rich_policy, tmp_path
):
    journey = current_rich_policy
    population = run_readings(
        journey, (journey.sources[0],), policy=None, inference="selected-use-export"
    )
    request = GroupedInterpretationRequest(
        project_id=PROJECT,
        demand_id=population.demand_id,
        roots=tuple(
            InterpretationRoot(product_id=row["id"])
            for row, _ in (*population.raw, *population.resolved)
        ),
    )
    destination = tmp_path / "finite"
    with journey.kernel.purpose("read").begin() as connection:
        receipt = export_demand_result(
            connection,
            population.demand_id,
            project_id=PROJECT,
            destination=destination,
            format="jsonl",
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
        groups, metadata = grouped_interpretation_rows(selected, request, ())
        assert groups and len(metadata["finite_universes"]) == 1
        assert {row["candidate_product_id"] for row in metadata["finite_universes"]} == {
            population.raw[0][0]["id"]
        }

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
            format="jsonl",
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
