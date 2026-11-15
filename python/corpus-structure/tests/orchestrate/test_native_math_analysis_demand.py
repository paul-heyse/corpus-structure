"""Actual admitted math request and demand-only resume on retained formula custody."""

import json
from pathlib import Path

import pytest
from semantic.data_operation_kernel_support import (
    CapturedKernelInputs,
    KernelRecipe,
    admit_kernel,
    prepare_kernel,
)
from semantic.native_record_fixtures import (
    private_source_with_originals as private_source_with_originals,
)
from semantic.original_source_fixture import completed_original_source_reference
from sqlalchemy import select

from corpus_structure.core.method import MethodSettings
from corpus_structure.semantic import SourceArtifact, SourceBundle
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_artifacts import capture_port_generator_sources
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_service import (
    DemandOriginalSelection,
    DemandRoot,
    NativeDemandRequest,
    create_native_demand,
    execute_data_demand,
    read_data_demand,
)
from corpus_structure.semantic.data_operation_storage import (
    native_operation_declarations,
    native_protocol_sources,
)
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.primary_operations import combine_primary_sources
from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies

ROOT = Path(__file__).resolve().parents[4]


def recipe():
    from corpus_structure.semantic.characterization_ports import characterization_operation_sources
    from corpus_structure.semantic.construction_products import construction_product_inputs
    from corpus_structure.semantic.declared_math_analysis import (
        math_analysis_declarations,
        math_analysis_operation_sources,
    )
    from corpus_structure.semantic.declared_math_products import (
        math_operation_declarations,
        math_operation_sources,
    )
    from corpus_structure.semantic.formal_products import formal_operation_sources
    from corpus_structure.semantic.source_discovery import (
        source_discovery_inputs,
        source_discovery_operation_sources,
    )
    from corpus_structure.semantic.source_profiles import (
        source_profile_inputs,
        source_profile_operation_sources,
    )

    core = ROOT / "python/corpus-structure/src/corpus_structure/model/semantic/core.yaml"
    bundle = construction_product_inputs(
        source_profile_inputs(
            source_discovery_inputs(
                SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
            )
        )
    )
    sources = combine_primary_sources(
        source_discovery_operation_sources(),
        source_profile_operation_sources(),
        formal_operation_sources(),
        characterization_operation_sources(),
        math_operation_sources(),
        math_analysis_operation_sources(),
    )
    native = native_protocol_sources()
    dependencies = data_operation_dependencies(
        ResolvedDependencies((*native, *capture_port_generator_sources())),
        (
            native_operation_declarations(native),
            math_operation_declarations(),
            math_analysis_declarations(),
        ),
        sources,
    )
    return KernelRecipe(
        "actual-declared-native-math-analysis",
        "",
        None,
        "",
        project_id=None,
        source_stage="private-source",
        execution_profile="source-native",
        captured_inputs=CapturedKernelInputs(
            bundle, dependencies, PreparationProfile(version="semantic-2")
        ),
    )


@pytest.mark.parametrize(
    "private_source_with_originals",
    [(("f(x)=x",), ("f(x)=x",))],
    indirect=True,
    ids=["readable-formula"],
)
def test_actual_math_request_retains_source_coordinates_and_resumes_without_new_work(
    private_source_with_originals,
    commit_db_engine,
    commit_writer_engine,
    commit_admitter_engine,
    tmp_path,
):
    retained = private_source_with_originals
    # The existing source fixture owns the authored policy override until test
    # teardown. Acquire the target while that exact policy is active, too.
    target = recipe()
    directory = tmp_path / "kernel"
    directory.mkdir()
    preparation = prepare_kernel(target, directory=directory)
    with commit_db_engine.begin() as connection:
        kernel = admit_kernel(connection, target, engine=commit_db_engine, preparation=preparation)
    reference, _ = completed_original_source_reference(retained)
    with commit_db_engine.connect() as connection:
        views = table("kb.source_view")
        row = (
            connection.execute(select(views).where(views.c.id == retained.other_view))
            .mappings()
            .one()
        )
    reference = reference.model_copy(
        update={
            "source_view_id": row["id"],
            "native_task_id": row["native_task_id"],
            "native_product_key": row["native_product_key"],
            "native_content_digest": row["native_content_digest"],
            "projection_digest": row["projection_digest"],
            "recipe_digest": row["recipe_digest"],
        }
    )
    from corpus_structure.semantic.source_admission import acquire_original_source_selection

    with commit_db_engine.begin() as connection:
        acquired = acquire_original_source_selection(
            connection,
            kernel.prepared,
            reference,
            [{"projection": reference.projection_digest}],
            name="formula-source",
        )
    request = NativeDemandRequest(
        project_id=retained.project_id,
        release_id=kernel.prepared.release_id,
        runtime_id=kernel.runtime,
        roots=(
            DemandRoot(
                subject=acquired.root.subject,
                original_source=acquired.root.original_source,
                analyzed_scope=json.loads(acquired.root.analyzed_scope),
            ),
        ),
        targets=("analyze.math/lexical",),
        original_sources={
            acquired.name: DemandOriginalSelection(
                reference=reference.model_dump(mode="json"),
                selectors=tuple(json.loads(acquired.selectors)),
            )
        },
        execution_profile="source-native",
    )
    with commit_writer_engine.begin() as connection:
        registered = create_native_demand(connection, request, prepared=kernel.prepared)
    methods = MethodSettings(data_dir=tmp_path, model_cache=tmp_path)
    result = execute_data_demand(
        commit_writer_engine,
        registered["demand_id"],
        source_root=ROOT,
        policy=methods.execution_policy,
        admission_engine=commit_admitter_engine,
        database_capacity=6,
    )
    with commit_db_engine.begin() as connection:
        snapshot = read_data_demand(connection, result.demand_id, view="products")
    pending = [value for value in snapshot["obligations"] if value["fate"] != "fulfilled"]
    assert pending == []
    bodies = [
        decode_semantic_value(product["body"])
        for use in snapshot["uses"]
        for product in use["products"]
    ]
    analyses = [
        body for body in bodies if isinstance(body, dict) and body.get("demand") == "lexical"
    ]
    assert len(analyses) == 1
    analysis = analyses[0]
    assert analysis["source"]["original_source"] == analysis["source"]["document"]
    assert "source_view_id" not in analysis["source"] and analysis["formal_input"]["product_id"]
    (item,) = analysis["items"]
    assert item["recognized_latex"] == "f(x)=x" and item["orig"] == "f(x)=x"
    assert item["lexical"] and "symbolic" not in item
    resumed = execute_data_demand(
        commit_writer_engine,
        result.demand_id,
        source_root=ROOT,
        policy=methods.execution_policy,
        admission_engine=commit_admitter_engine,
        database_capacity=6,
    )
    assert resumed.demand_id == result.demand_id and resumed.receipt_count == 0
