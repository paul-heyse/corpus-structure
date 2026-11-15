"""Declared target meaning stays distinct from source drift and native currentness."""

from dataclasses import replace
from typing import Any, cast

import pytest

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_model import compiled_graph_projections
from corpus_structure.semantic.model_comparison import compare_declared_models
from corpus_structure.semantic.source_comparison import compare_data_operation_models
from semantic.data_operation_declaration_support import contract, declarations
from semantic.test_data_operation_compilation import operation_source, python_inputs


def test_body_change_reports_recipe_identity_without_claiming_changed_output():
    before = compile_data_operations(python_sources=python_inputs(operation_source()))
    after = compile_data_operations(python_sources=python_inputs(operation_source(body="return helper(x) + 1")))
    report = compare_declared_models(before, after, before_release="old", after_release="new")
    recipe = next(change for change in report.changes if change.model_ref == "urn:test:derive/recipe")
    assert recipe.aspect == "identity"
    assert recipe.before != recipe.after
    assert recipe.consumers == ("urn:test:derive",)
    assert report.complete
    assert report.version == "declared-data-model-comparison-v1"
    assert (report.before_release, report.after_release) == ("old", "new")
    assert "state" not in report.model_dump()


def test_descriptive_metadata_change_is_absent_from_declared_semantic_difference():
    before = compile_data_operations(python_sources=python_inputs(operation_source()))
    after = compile_data_operations(python_sources=python_inputs(operation_source(metadata=contract(behavior="rewritten descriptive prose"))))
    assert not compare_declared_models(before, after).changes
    source = compare_data_operation_models(before, after)
    assert source.changes
    assert not {"recipe", "eligibility", "implementation"} & {change.facet for change in source.changes}


def test_checked_subject_change_reports_meaning_and_both_dependency_sides():
    producer = contract()
    consumer = contract(id="urn:test:consumer", dependencies=[producer["id"]])
    before = compile_data_operations(declarations=declarations(producer, consumer))
    new_subject = {**producer["subject_definition"], "scope": "invocation"}
    after = compile_data_operations(declarations=declarations(
        contract(subject_definition=new_subject),
        contract(id="urn:test:consumer", subject_definition=new_subject),
    ))
    report = compare_declared_models(before, after)
    subject = next(change for change in report.changes if change.model_ref == "subject:original-occurrence" and change.aspect == "semantic-node")
    assert cast(dict[str, Any], subject.before)["payload"]["scope"] == "project"
    assert cast(dict[str, Any], subject.after)["payload"]["scope"] == "invocation"
    assert subject.consumers == ("urn:test:consumer", "urn:test:derive")
    edge = next(change for change in report.changes if change.model_ref == "urn:test:consumer" and change.aspect == "semantic-edges")
    assert any(item["relation"] == "operation_dependency" for item in cast(list[dict[str, Any]], edge.before))
    assert not any(item["relation"] == "operation_dependency" for item in cast(list[dict[str, Any]], edge.after))


def test_relationship_position_and_multiplicity_are_not_collapsed():
    before = compile_data_operations(declarations=declarations(contract()))
    changed = tuple(replace(edge, position=2, multiplicity=3) if edge.relation == "input_kind" else edge for edge in before.edges)
    after = replace(before, edges=changed, graph_projections=compiled_graph_projections(before.nodes, changed, before.implementation_slices))
    report = compare_declared_models(before, after)
    (change,) = report.changes
    assert change.aspect == "semantic-edges"
    assert change.consumers == ("urn:test:derive",)
    assert any(item["position"] == 2 and item["multiplicity"] == 3 for item in cast(list[dict[str, Any]], change.after))


def test_incomplete_model_and_unsupported_encoding_do_not_claim_complete_comparison():
    before = compile_data_operations(python_sources=python_inputs(operation_source(body="return callback(x)").replace("x: int = 2", "x: int = 2, callback: object = None")))
    report = compare_declared_models(before, before)
    assert not report.complete
    assert any("incomplete implementation" in unknown for unknown in report.unknowns)
    with pytest.raises(ValueError, match="historical model"):
        compare_declared_models(replace(before, version="data-operation-model-v6"), before)
