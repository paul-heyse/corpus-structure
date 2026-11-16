"""Actual named-definition CPU/receipt custody with controlled independent C labels.

Source decoding is controlled. The real sentence provider and current named
construction/component operations execute. Assigned C labels exercise a numerical
development procedure; this fixture makes no linguistic accuracy claim.
"""

from dataclasses import replace
from typing import Any,Literal

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import SubjectContext
from semantic.current_pdf_source_support import PROJECT, ROOT
from semantic.structural_admission_native_support import Product
from semantic.structural_production_native_support import recipe as structural_recipe


def recipe(directory):
    from corpus_structure.evaluate.declared_operation_events import operation_event_kind_declarations, operation_event_operation_sources
    from corpus_structure.semantic.composed import data_operation_dependencies, read_data_operation_inputs
    from corpus_structure.semantic.operation_score_sources import operation_score_inputs, operation_score_sources
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from corpus_structure.semantic.types import ResolvedDependencies
    from semantic.operation_event_feature_fixture import operation_sources as feature_sources

    original = structural_recipe(directory)
    captured = original.captured_inputs
    assert captured is not None
    acquired = read_data_operation_inputs(captured.dependencies)
    assert acquired is not None and acquired[1] is not None
    declarations, sources = acquired
    assert sources is not None
    dependencies = data_operation_dependencies(
        ResolvedDependencies(tuple(artifact for artifact in captured.dependencies.artifacts
                                  if not artifact.name.startswith("data-operations/")),
                             captured.dependencies.vocabularies, captured.dependencies.ontology_sources),
        (*declarations, *operation_score_inputs(), operation_event_kind_declarations()),
        combine_primary_sources(sources, operation_event_operation_sources(), operation_score_sources(), feature_sources()),
    )
    return replace(original, name="current-operation-event-development",
                   captured_inputs=replace(captured, dependencies=dependencies))


def project_context(kernel):
    return SubjectContext(PROJECT, "operation-event:controlled-current-corpus", None, b"{}", subject_definition="fitted-operation-event")


def execute(kernel, pending, *, authored=False, purpose: Literal["write","evaluate"]="evaluate") -> tuple[dict[str,Any],Any]:
    from corpus_structure.semantic.data_operation_service import create_native_demand, execute_data_demand
    from corpus_structure.serve.interpretation_authoring import author_interpretations
    retained:dict[str,Any]
    if authored:
        retained = dict(author_interpretations(kernel.purpose("evaluate"), kernel.prepared, request=pending))
    else:
        with kernel.purpose(purpose).begin() as connection:
            retained = dict(create_native_demand(connection, pending, prepared=kernel.prepared))
    demand_id = retained["demand_id"]
    assert isinstance(demand_id,str)
    execution = execute_data_demand(kernel.purpose(purpose), demand_id, source_root=ROOT,
        purpose=purpose, admission_engine=kernel.purpose("admit"), fitter_engine=kernel.purpose("fit"),
        project_id=PROJECT, database_capacity=6)
    return retained, execution


def selected(kernel, demand, kind, *, purpose="evaluate"):
    from corpus_structure.semantic.demand_results import read_demand_result
    with kernel.purpose(purpose).begin() as connection:
        page = read_demand_result(connection, demand, project_id=PROJECT, limit=1000)
    return page, tuple(Product(row,row["body"]) for row in page.members()
                       if row["kind_contract"] == kernel.identities[kind,"kind"])


def cut_selection(page):
    from corpus_structure.evaluate.selected_operation_events import SelectedEventRead
    cut = page.cut
    return SelectedEventRead(project_id=PROJECT, demand_id=cut.record["demand_id"], read_id=cut.record["read_id"],
        release_id=cut.record["release_id"], runtime_id=cut.record["runtime_id"],
        cut_id=cut.identity, cut_canonical_json=cut.content.decode())
