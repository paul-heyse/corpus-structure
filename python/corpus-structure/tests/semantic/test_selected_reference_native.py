"""Real evaluator snapshot publication preserves an independently frozen source cut."""

import json
from pathlib import Path

from corpus_structure.evaluate.selected_references import author_selected_references
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_service import (
    NativeDemandRequest,
    execute_data_demand,
)
from corpus_structure.semantic.data_operation_support import authored_fact_selection
from corpus_structure.semantic.data_operation_version import MODEL_VERSION
from corpus_structure.semantic.demand_results import acquired_selected_relations, read_demand_result
from corpus_structure.semantic.observations import source_value
from native_test_support import principal_engine
from semantic.data_operation_declaration_support import source_declaration
from semantic.data_operation_demand_support import attach, claim, publish, retain
from semantic.data_operation_kernel_support import KernelRecipe, admit_kernel, prepare_kernel


def reference_recipe():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    return KernelRecipe(
        "selected-reference-native",
        core.read_text(),
        json_bytes(dict(version=MODEL_VERSION, operations=[source_declaration()])),
        "version: data-operation-inputs-v1\nroot: core\nschemas: [{name: core, path: schema.yaml}]\ndeclarations: [{name: operations, path: operations.yaml}]\nprotected_references: true\n",
    )


def test_evaluator_snapshot_executes_and_preserves_complete_authored_reference(
    commit_db_engine, native_settings, tmp_path
):
    recipe = reference_recipe()
    preparation = prepare_kernel(recipe, directory=tmp_path / "reference")
    with commit_db_engine.begin() as connection:
        kernel = admit_kernel(connection, recipe, preparation=preparation)
    source_demand, _, _, attached = attach(
        kernel, subject="source:reference", original_source="document:reference", analyzed_scope={}
    )
    fence = claim(kernel, attached)
    publish(kernel, fence, retain(kernel, fence, outputs=(41,)))
    with kernel.engine.begin() as connection:
        source = read_demand_result(connection, source_demand["demand_id"], project_id="ddo-test")
        member = source.members()[0]
    body = dict(
        reference_name="independent-source-value",
        author="independent author",
        pass_kind="C",
        direction="source_first",
        source_demand_id=source.cut.record["demand_id"],
        source_cut_id=source.cut.identity,
        source_read_id=source.cut.record["read_id"],
        source_cut=source_value(source.cut.record),
        source_release_id=source.cut.record["release_id"],
        source_runtime_id=source.cut.record["runtime_id"],
        source_members=[
            dict(
                product_id=member["product_id"],
                subject="source:reference",
                subject_definition=member["subject_definition"],
                original_source="document:reference",
                analyzed_scope_meaning='["mapping",[]]',
                kind_contract=kernel.kind,
            )
        ],
        output_addresses=[],
        cases=[],
        retained_correspondence=source_value(None),
    )
    body["cases"] = [
        dict(
            case_id="case:one",
            opportunity_id="opportunity:one",
            question="Which independent source value was observed?",
            source_members=body["source_members"],
            matcher="fields",
            expected=source_value({"value": 41}),
            judgment="supported",
        )
    ]
    context = SubjectContext(
        "ddo-test",
        "source:reference",
        "document:reference",
        b"{}",
        subject_definition="original-occurrence",
    )
    kind = kernel.identities[
        "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReference",
        "kind",
    ]
    original = authored_fact_selection(
        "independent-reference",
        body,
        kind_contract=kind,
        context=context,
        author="independent author",
        selection_id="reference:one",
    )
    request = NativeDemandRequest.model_validate(
        dict(
            project_id="ddo-test",
            release_id=kernel.prepared.release_id,
            runtime_id=kernel.runtime,
            roots=[
                dict(
                    subject=context.subject,
                    original_source=context.original_source,
                    analyzed_scope={},
                )
            ],
            targets=["reference.snapshot/declared"],
            execution_profile="execution:test",
            original_sources={original.name: original.record()},
        )
    )
    evaluator = principal_engine(native_settings, "evaluate", kernel.engine.url.database)
    admitted = principal_engine(native_settings, "admit", kernel.engine.url.database)
    try:
        authored = author_selected_references(evaluator, kernel.prepared, request=request)
        result = execute_data_demand(
            evaluator,
            authored["demand_id"],
            project_id="ddo-test",
            source_root=Path(__file__).parents[2] / "src",
            admission_engine=admitted,
            purpose="evaluate",
            database_capacity=4,
        )
        assert result.receipt_count == 1
        with evaluator.begin() as connection:
            selected = read_demand_result(connection, authored["demand_id"], project_id="ddo-test")
            snapshot = selected.members()[0]
            assert snapshot["body"] == json.loads(json.dumps(body))
            assert snapshot["derivation_id"] is not None
            with acquired_selected_relations(
                connection,
                authored["demand_id"],
                project_id="ddo-test",
                scope={},
                read_id=selected.cut.record["read_id"],
                expected_cut=selected.cut.identity,
            ) as (_, index):
                assert any(
                    row["role"] == "reference" and row["derivation_id"] == snapshot["derivation_id"]
                    for row in index.rows("ops.data_derivation_original_support")
                )
    finally:
        evaluator.dispose()
        admitted.dispose()
