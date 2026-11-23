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
from sqlalchemy import text

from corpus_structure.core.method import MethodSettings
from corpus_structure.orchestrate.source_operation import _default_profile_source_sets
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_service import (
    create_native_demand,
    execute_data_demand,
    read_data_demand,
)
from corpus_structure.semantic.data_operation_values import decode_semantic_value
from corpus_structure.semantic.demand_results import CutSelection, read_selected_answer
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
    from corpus_structure.semantic.construction_products import (
        ConstructionOptions,
        construction_product_inputs,
    )
    from corpus_structure.semantic.constructions.math_scope import Binders
    from corpus_structure.semantic.declared_math_analysis import (
        math_analysis_declarations,
        math_analysis_operation_sources,
    )
    from corpus_structure.semantic.declared_math_products import (
        DeclaredMathOptions,
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
    binders = Binders(sentence_initial=("suppose",))
    math_options = DeclaredMathOptions(math_scope_binders=binders)
    sources = combine_primary_sources(
        source_discovery_operation_sources(),
        source_profile_operation_sources(),
        formal_operation_sources(),
        characterization_operation_sources(
            sentence_configuration=SentenceConfig(exclude=("ner",)),
            construction_options=ConstructionOptions(math_scope_binders=binders),
        ),
        math_operation_sources(math_options),
        math_analysis_operation_sources(math_options),
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
        scope_operation = "resolve.symbol_scope/declared"
        request = current_consumer_request(
            source, kernel, ("analyze.math/lexical", scope_operation), discover=True
        )
        graph = kernel.model.projection_graph(
            "selected-dependencies",
            selected_dependencies=tuple(
                (selection.operation, selection.selected_dependencies)
                for selection in request.selections
            ),
        )
        requested = set(request.targets) | {
            operation
            for selection in request.discovery
            for operation in (selection.producer, selection.target)
        }
        closure = requested.union(*(graph.closure((operation,)) for operation in requested))
        # The fixture has no retained ancestor scopes. Supply the explicitly
        # empty source sets used by the ordinary fresh-source profile.
        request = request.model_copy(
            update={
                "source_sets": {
                    **_default_profile_source_sets(kernel.model, closure),
                    **request.source_sets,
                }
            }
        )
        with kernel.purpose("write").begin() as connection:
            registered = create_native_demand(connection, request, prepared=kernel.prepared)
        methods = MethodSettings(data_dir=tmp_path, model_cache=tmp_path)
        result = execute_data_demand(
            kernel.purpose("write"),
            registered["demand_id"],
            source_root=ROOT / "python/corpus-structure/src",
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

        phases = {}
        for use in snapshot["uses"]:
            for product in use["products"]:
                body = decode_semantic_value(product["body"])
                if isinstance(body, dict) and body.get("phase") in {
                    "occurrences",
                    "symbolic",
                    "scope",
                }:
                    phase = body["phase"]
                    assert phase not in phases
                    phases[phase] = (use, product, body)
        assert set(phases) == {"occurrences", "symbolic", "scope"}
        _, occurrence, occurrence_body = phases["occurrences"]
        _, symbolic, symbolic_body = phases["symbolic"]
        scope_use, scope_product, scope_body = phases["scope"]
        assert occurrence_body["source"] == symbolic_body["source"] == scope_body["source"]
        (context,) = occurrence_body["contexts"]
        assert context["configuration_basis"] and context["model_id"]
        assert symbolic_body["contexts"] == [context]
        assert symbolic_body["occurrence_input"] == {"variant": "product", "role": "occurrences"}
        assert scope_body["occurrence_input"]["product_id"] == occurrence["product_id"]
        assert scope_body["symbolic_input"]["product_id"] == symbolic["product_id"]
        with kernel.engine.begin() as connection:
            answer = read_selected_answer(
                connection,
                "read_selected_outputs",
                result.demand_id,
                project_id=CutSelection.from_native(snapshot).record["project_id"],
                scope={"operation_id": scope_operation},
                use_id=scope_use["use_id"],
                product_id=scope_product["product_id"],
                body=True,
            )
            (selected_scope,) = answer["rows"]
            assert selected_scope["use_id"] == scope_use["use_id"]
            assert selected_scope["derivation_id"] == scope_use["derivation_id"]
            assert decode_semantic_value(selected_scope["meaning_body"]) == scope_body
            facts = read_selected_answer(
                connection,
                "read_selected_derivation_facts",
                result.demand_id,
                project_id=CutSelection.from_native(snapshot).record["project_id"],
                read_id=answer["cut"]["read_id"],
                scope={"operation_id": scope_operation},
                use_id=scope_use["use_id"],
                derivation_id=scope_use["derivation_id"],
            )
            original_binding = connection.execute(
                text(
                    "SELECT r.binding FROM ops.data_derivation AS d "
                    "JOIN ops.data_request AS r ON r.id = d.request_id WHERE d.id = :episode"
                ),
                {"episode": scope_use["derivation_id"]},
            ).scalar_one()
        for role, product in (("occurrences", occurrence), ("symbolic", symbolic)):
            (fact,) = [row for row in facts["rows"] if row["role"] == role]
            (bound,) = [row for row in original_binding["inputs"] if row["role"] == role]
            assert fact["product_id"] == bound["product_id"] == product["product_id"]
            # An episode's exact input use can belong to a different demand from
            # the displayed producer use of the same retained product.
            expected = {
                (row["derivation_id"], row.get("admission_use_id"))
                for row in original_binding["support"]
                if row["role"] == role
                and row["position"] == bound["position"]
                and row.get("derivation_id") in bound["support_derivation_ids"]
            }
            assert expected
            assert {
                (row["derivation_id"], row.get("admission_use_id")) for row in fact["support"]
            } == expected

        resumed = execute_data_demand(
            kernel.purpose("write"),
            result.demand_id,
            source_root=ROOT / "python/corpus-structure/src",
            policy=methods.execution_policy,
            admission_engine=kernel.purpose("admit"),
            database_capacity=6,
        )
        assert resumed.demand_id == result.demand_id and resumed.receipt_count == 0
