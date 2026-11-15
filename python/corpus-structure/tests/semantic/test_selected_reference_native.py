"""Real evaluator snapshot publication preserves an independently frozen source cut."""

import json
from pathlib import Path

import pytest

from corpus_structure.evaluate.selected_references import author_selected_references
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import MODEL_VERSION, SubjectContext
from corpus_structure.semantic.data_operation_service import (
    NativeDemandRequest,
    execute_data_demand,
)
from corpus_structure.semantic.data_operation_support import authored_fact_selection
from corpus_structure.semantic.demand_results import read_demand_result, selected_record_index
from corpus_structure.semantic.observations import source_value
from semantic.data_operation_declaration_support import source_declaration
from semantic.data_operation_demand_support import attach, claim, publish, retain
from semantic.data_operation_kernel_support import KernelRecipe


def reference_recipe():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    return KernelRecipe(
        "selected-reference-native",
        core.read_text(),
        json_bytes(dict(version=MODEL_VERSION, operations=[source_declaration()])),
        "version: data-operation-inputs-v1\nroot: core\nschemas: [{name: core, path: schema.yaml}]\ndeclarations: [{name: operations, path: operations.yaml}]\nprotected_references: true\n",
    )


@pytest.mark.parametrize("ddo_kernel", [reference_recipe()], indirect=True)
def test_evaluator_snapshot_executes_and_preserves_complete_authored_reference(ddo_kernel):
    kernel = ddo_kernel
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
                original_source="document:reference",
                analyzed_scope_meaning='["mapping",[]]',
                kind_contract=kernel.kind,
            )
        ],
        output_members=[],
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
    evaluator = kernel.purpose("evaluate")
    admitted = kernel.purpose("admit")
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
            with selected_record_index(
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
