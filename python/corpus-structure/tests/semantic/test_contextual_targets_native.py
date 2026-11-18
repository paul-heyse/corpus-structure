"""Real target discovery/materialization; never claims encoder/provider execution."""

from pathlib import Path

import pytest

from corpus_structure.methods.contextual_embeddings import EncoderProfile
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.contextual_encoder import (
    ContextualEncoderSelection,
    contextual_encoder_declarations,
    contextual_encoder_operation_sources,
)
from corpus_structure.semantic.contextual_operations import (
    contextual_inputs,
    contextual_operation_declarations,
)
from corpus_structure.semantic.contextual_selection import freeze_contextual_target_demand
from corpus_structure.semantic.data_operation_artifacts import capture_port_generator_sources
from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
    DiscoverySelection,
    RootSubject,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_service import execute_data_demand
from corpus_structure.semantic.data_operation_storage import (
    DataOperationStorage,
    native_operation_declarations,
    native_protocol_sources,
)
from corpus_structure.semantic.data_operation_support import authored_fact_selection
from corpus_structure.semantic.declared_structural_calls import (
    structural_inputs,
    structural_operation_declarations,
)
from corpus_structure.semantic.demand_results import read_demand_result, selected_record_index
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.types import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)
from semantic.data_operation_kernel_support import CapturedKernelInputs, Kernel, KernelRecipe

ROOT = Path(__file__).resolve().parents[4]
PROJECT = "ddo-test"


@pytest.fixture(scope="module")
def contextual_target_recipe(tmp_path_factory):
    # These are capture-only model files. This test executes no encoder or model
    # loader: the finite target population and canonical projection are genuine.
    model_path = tmp_path_factory.mktemp("unallocated-contextual-model")
    for name in ("config.json", "modules.json"):
        (model_path / name).write_text("{}")
    selection = ContextualEncoderSelection.acquire(
        EncoderProfile("controlled-unallocated", "a" * 40, 2, "query: ", "passage: ", "mean"),
        model_path,
    )
    bundle = contextual_inputs(
        structural_inputs(
            SourceBundle(
                "core",
                (
                    SourceArtifact(
                        "core",
                        (
                            ROOT
                            / "python/corpus-structure/src/corpus_structure/model/semantic/core.yaml"
                        ).read_bytes(),
                    ),
                ),
            )
        )
    )
    native = native_protocol_sources()
    dependencies = data_operation_dependencies(
        ResolvedDependencies((*native, *capture_port_generator_sources())),
        declarations=(
            native_operation_declarations(native),
            contextual_encoder_declarations(),
            contextual_operation_declarations(),
            structural_operation_declarations(),
        ),
        python_sources=contextual_encoder_operation_sources(selection),
    )
    return KernelRecipe(
        "contextual-target-projection",
        "",
        None,
        "",
        captured_inputs=CapturedKernelInputs(
            bundle, dependencies, PreparationProfile(version="semantic-2")
        ),
    )


@pytest.fixture
def contextual_target_kernel(contextual_target_recipe, scenario_seeds):
    # Reuse immutable preparation, while keeping each case's committed data private.
    with scenario_seeds.commit_clone(contextual_target_recipe) as clone:
        stage = clone.stage
        yield Kernel(
            clone.admin, stage.preparation, stage.identities, contextual_target_recipe, clone
        )


def _project(kernel, names):
    context = SubjectContext(
        PROJECT, "curated-registry", None, b"{}", subject_definition="contextual-registry"
    )
    kind = kernel.identities[
        "https://corpus-structure.dev/semantic/data-operation-contextual/DdoCuratedContextualTargets",
        "kind",
    ]
    authored = authored_fact_selection(
        "curated-targets",
        dict(
            targets=source_value(
                [
                    dict(target_id=name, label="alpha", description="Meaning " + name)
                    for name in names
                ]
            )
        ),
        kind_contract=kind,
        context=context,
        author="test operator",
        selection_id="selected-target-descriptions",
    )
    intent = freeze_demand(
        kernel.model,
        roots=(RootSubject(context.subject, None, b"{}"),),
        targets=("retrieve.contextual_targets/curated",),
        discovery=(
            DiscoverySelection(
                "retrieve.contextual_targets/curated",
                "result",
                "retrieve.contextual_target/declared",
                "contextual-targets",
                target_role="target",
            ),
        ),
        inference="target-description-control",
        execution_profile=kernel.recipe.execution_profile,
        original_sources=(authored,),
    )
    with kernel.purpose("write").begin() as connection:
        demand = DemandPlanner(kernel.model, DataOperationStorage(connection)).register(
            intent, project=PROJECT, release=kernel.prepared.release_id, runtime=kernel.runtime
        )["demand_id"]
    execute_data_demand(
        kernel.purpose("write"),
        demand,
        source_root=ROOT,
        project_id=PROJECT,
        admission_engine=kernel.purpose("admit"),
        database_capacity=6,
    )
    with (
        kernel.purpose("read").begin() as connection,
        selected_record_index(
            connection, demand, project_id=PROJECT, scope={}, capture_frontier=True
        ) as (cut, index),
    ):
        requests = index.mapping("ops.data_request", ("id",))
        derivations = index.mapping("ops.data_derivation", ("id",))
        target_kind = kernel.identities[
            "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualTarget",
            "kind",
        ]
        values = {}
        for product in index.rows("kb.data_product"):
            if product["kind_contract"] != target_kind:
                continue
            body = decode_semantic_value(product["canonical_body"])
            from corpus_structure.semantic.observations import source_python

            target_id = source_python(body["descriptor"])["target_id"]
            outputs = list(index.rows_for("ops.data_derivation_output", product_id=product["id"]))
            episodes = {
                row["derivation_id"]
                for row in outputs
                if requests[derivations[row["derivation_id"]]["request_id"]]["operation_id"]
                == "retrieve.contextual_target/declared"
            }
            assert episodes and product["original_source"] is None
            values[target_id] = (product["id"], body, episodes)
        # A closed empty discovery has no child use to reach it through support.
        # Its actual population receipt belongs to the captured demand frontier.
        population_page = read_demand_result(
            connection,
            demand,
            project_id=PROJECT,
            continuation=dict(
                demand_id=demand,
                read_id=cut.record["read_id"],
                scope=cut.record["scope"],
                view="frontier",
            ),
            cut=cut,
            view="frontier",
        )
        populations = population_page.record["populations"]
        assert len(populations) == 1 and populations[0]["complete"] is True
        assert len(populations[0]["members"]) == len(names)
        return values


def test_changed_curated_population_materializes_same_target_products_with_authentic_new_support(
    contextual_target_kernel,
):
    first = _project(contextual_target_kernel, ("one", "two"))
    second = _project(contextual_target_kernel, ("one", "two", "three"))
    assert set(first) == {"one", "two"} and set(second) == {"one", "two", "three"}
    for key in first:
        assert first[key][:2] == second[key][:2]
        assert first[key][2] != second[key][2]


def test_explicit_empty_curated_population_closes_without_invented_targets(
    contextual_target_kernel,
):
    assert _project(contextual_target_kernel, ()) == {}


def test_curated_target_request_refuses_invented_query_original_before_native(
    contextual_target_kernel,
):
    with pytest.raises(ValueError, match="inherit a query original"):
        freeze_contextual_target_demand(
            contextual_target_kernel.model,
            roots=(RootSubject("curated", "query-document", b"{}"),),
            producer="retrieve.contextual_targets/curated",
            replicate="selected-original-observation",
            inference="retained-observation",
            execution_profile="execution:test",
        )
