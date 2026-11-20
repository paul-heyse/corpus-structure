"""Actual named-definition CPU/receipt custody with controlled independent C labels.

Source decoding is controlled. The real sentence provider and current named
construction/component operations execute. Assigned C labels exercise a numerical
development procedure; this fixture makes no linguistic accuracy claim.
"""

from dataclasses import replace
from typing import Any, Literal

from corpus_structure.semantic.data_operation_model import SubjectContext
from semantic.current_pdf_source_support import PROJECT
from semantic.data_operation_kernel_support import (
    execute_captured_kernel_demand,
    split_captured_operations,
)
from semantic.structural_admission_native_support import Product
from semantic.structural_production_native_support import recipe as structural_recipe


def recipe(directory):
    from corpus_structure.evaluate.declared_operation_events import (
        operation_event_kind_declarations,
        operation_event_operation_sources,
    )
    from corpus_structure.semantic.composed import (
        data_operation_dependencies,
    )
    from corpus_structure.semantic.operation_score_sources import (
        operation_score_inputs,
        operation_score_sources,
    )
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from semantic.operation_event_feature_fixture import operation_sources as feature_sources

    original = structural_recipe(directory)
    captured = original.captured_inputs
    assert captured is not None
    base_dependencies, declarations, sources = split_captured_operations(captured)
    dependencies = data_operation_dependencies(
        base_dependencies,
        (*declarations, *operation_score_inputs(), operation_event_kind_declarations()),
        combine_primary_sources(
            sources,
            operation_event_operation_sources(),
            operation_score_sources(),
            feature_sources(),
        ),
    )
    return replace(
        original,
        name="current-operation-event-development",
        captured_inputs=replace(captured, dependencies=dependencies),
    )


def project_context(kernel):
    return SubjectContext(
        PROJECT,
        "operation-event:controlled-current-corpus",
        None,
        b"{}",
        subject_definition="fitted-operation-event",
    )


def execute(
    kernel, pending, *, authored=False, purpose: Literal["write", "evaluate"] = "evaluate"
) -> tuple[dict[str, Any], Any]:
    from corpus_structure.semantic.data_operation_service import create_native_demand
    from corpus_structure.serve.interpretation_authoring import author_interpretations

    retained: dict[str, Any]
    if authored:
        retained = dict(
            author_interpretations(kernel.purpose("evaluate"), kernel.prepared, request=pending)
        )
    else:
        with kernel.purpose(purpose).begin() as connection:
            retained = dict(create_native_demand(connection, pending, prepared=kernel.prepared))
    demand_id = retained["demand_id"]
    assert isinstance(demand_id, str)
    execution = execute_captured_kernel_demand(kernel, demand_id, purpose=purpose, fit=True)
    return retained, execution


def selected(kernel, demand, kind, *, purpose="evaluate", scope=None):
    from corpus_structure.semantic.demand_results import read_demand_result
    from corpus_structure.semantic.selected_support import SelectedReadReference

    with kernel.purpose(purpose).begin() as connection:
        page = read_demand_result(connection, demand, project_id=PROJECT, limit=1000, scope=scope)
    read = SelectedReadReference.from_cut(page.cut)
    return page, tuple(
        Product(row, row["body"], read)
        for row in page.members()
        if row["kind_contract"] == kernel.identities[kind, "kind"]
    )


def cut_selection(cut):
    from corpus_structure.evaluate.selected_operation_events import SelectedEventRead

    return SelectedEventRead.from_cut(cut)
