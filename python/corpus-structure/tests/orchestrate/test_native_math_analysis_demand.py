"""Actual admitted math request and demand-only resume on retained formula custody."""

from pathlib import Path

from semantic.current_pdf_source_support import (
    admit_current_target,
    current_consumer_request,
)
from semantic.current_pdf_source_support import (
    current_pdf_source_factory as current_pdf_source_factory,
)
from semantic.data_operation_kernel_support import CapturedKernelInputs, KernelRecipe

from corpus_structure.core.method import MethodSettings
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_service import (
    create_native_demand,
    execute_data_demand,
    read_data_demand,
)
from corpus_structure.semantic.data_operation_values import decode_semantic_value
from corpus_structure.semantic.native_protocol_authoring import (
    native_operation_declarations,
    native_protocol_sources,
)
from corpus_structure.semantic.primary_operations import combine_primary_sources
from corpus_structure.semantic.types import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)

ROOT = Path(__file__).resolve().parents[4]


def recipe():
    from corpus_structure.ingest.sentences import SentenceConfig
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
        source_profile_declarations,
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
        characterization_operation_sources(sentence_configuration=SentenceConfig(exclude=("ner",))),
        math_operation_sources(),
        math_analysis_operation_sources(),
    )
    native = native_protocol_sources()
    dependencies = data_operation_dependencies(
        ResolvedDependencies(native),
        (
            native_operation_declarations(native),
            source_profile_declarations(),
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
        execution_profile="source-native",
        captured_inputs=CapturedKernelInputs(
            bundle, dependencies, PreparationProfile(version="semantic-2")
        ),
    )


def test_actual_math_request_retains_source_coordinates_and_resumes_without_new_work(
    current_pdf_source_factory,
    tmp_path,
):
    with current_pdf_source_factory((("formula", "f(x)=x", "f(x)=x", "succeeded"),)) as source:
        kernel = admit_current_target(source, recipe(), tmp_path / "consumer")
        request = current_consumer_request(source, kernel, ("analyze.math/lexical",), discover=True)
        with kernel.purpose("write").begin() as connection:
            registered = create_native_demand(connection, request, prepared=kernel.prepared)
        methods = MethodSettings(data_dir=tmp_path, model_cache=tmp_path)
        result = execute_data_demand(
            kernel.purpose("write"),
            registered["demand_id"],
            source_root=ROOT,
            policy=methods.execution_policy,
            admission_engine=kernel.purpose("admit"),
            database_capacity=6,
        )
        with kernel.engine.begin() as connection:
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
            kernel.purpose("write"),
            result.demand_id,
            source_root=ROOT,
            policy=methods.execution_policy,
            admission_engine=kernel.purpose("admit"),
            database_capacity=6,
        )
        assert resumed.demand_id == result.demand_id and resumed.receipt_count == 0
