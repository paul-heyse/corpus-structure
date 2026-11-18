"""Current selected PM2 setup; expectations remain independent in the tests."""

from contextlib import contextmanager

import pytest

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import BoundRoleMember
from corpus_structure.semantic.data_operation_service import (
    DemandOperationSelection,
    DemandRoot,
    NativeDemandRequest,
    create_native_demand,
    execute_data_demand,
)
from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
from corpus_structure.semantic.demand_results import read_demand_result
from corpus_structure.semantic.source_products import FrozenNativeSource
from semantic.current_pdf_source_support import PROJECT, ROOT, current_pdf_recipe, source_entry
from semantic.current_pm2_projection_fixture import OPERATION, operation_sources
from semantic.data_operation_kernel_support import (
    CapturedKernelInputs,
    KernelRecipe,
    prepare_kernel,
    split_captured_operations,
)


def projection_recipe(directory):
    from corpus_structure.semantic.composed import (
        data_operation_dependencies,
    )
    from corpus_structure.semantic.declared_candidate_products import candidate_inspection_inputs
    from corpus_structure.semantic.primary_operations import combine_primary_sources

    captured = current_pdf_recipe(directory).captured_inputs
    assert captured is not None
    base_dependencies, declarations, sources = split_captured_operations(captured)
    sources = combine_primary_sources(sources, operation_sources())
    dependencies = data_operation_dependencies(
        base_dependencies,
        declarations,
        sources,
    )
    return KernelRecipe(
        "current-pm2-controlled-projection",
        "",
        None,
        "",
        project_id=None,
        execution_profile="source-native",
        captured_inputs=CapturedKernelInputs(
            candidate_inspection_inputs(captured.bundle), dependencies, captured.profile
        ),
    )


@contextmanager
def table_source(scenario_seeds):
    from evaluate.declared_record_native_support import table_source_content

    from semantic.current_pdf_source_support import _published_pdf_source

    with _published_pdf_source(
        scenario_seeds,
        content=table_source_content(),
        sections=("#/groups/0",),
    ) as source:
        yield source


def projection_request(kernel, row, *, mode="mixed", operation=OPERATION):
    from corpus_structure.semantic.data_operation_source_sets import (
        FrozenSourceSet,
        source_sets_record,
    )

    return NativeDemandRequest(
        project_id=PROJECT,
        release_id=kernel.prepared.release_id,
        runtime_id=kernel.runtime,
        roots=(
            DemandRoot(
                subject=row["subject"],
                original_source=row["original_source"],
                analyzed_scope=row["analyzed_scope"],
            ),
        ),
        targets=(operation,),
        selections=(DemandOperationSelection(operation=operation, parameters={"mode": mode}),),
        source_sets=source_sets_record(
            (FrozenSourceSet.from_selected("pm2-test-source", (source_entry(row),)),)
        ),
        inference="controlled-pm2-projection",
        execution_profile="source-native",
    )


def register(kernel, request):
    with kernel.purpose("write").begin() as connection:
        return create_native_demand(connection, request, prepared=kernel.prepared)["demand_id"]


def execute(kernel, demand, *, rounds=100):
    return execute_data_demand(
        kernel.purpose("write"),
        demand,
        source_root=ROOT,
        admission_engine=kernel.purpose("admit"),
        database_capacity=6,
        max_rounds=rounds,
    )


def page(kernel, demand, *, purpose="read"):
    with kernel.purpose(purpose).begin() as connection:
        return read_demand_result(connection, demand, project_id=PROJECT, limit=1000)


def reports(kernel, demand, operation=OPERATION):
    selected = page(kernel, demand)
    obligations = {
        row["obligation_id"]
        for row in selected.record["obligations"]
        if row["operation_id"] == operation
    }
    uses = {row["use_id"] for row in selected.record["uses"] if row["obligation_id"] in obligations}
    return tuple(
        row for row in selected.members() if row["member_id"] is None and row["use_id"] in uses
    ), selected


def parser_recipe(assets):
    # Reuse the already maintained actual capture recipe, including its exact
    # runtime/profile assets. No replacement or fabricated provider selection.
    from semantic.test_native_parser_demand import _captured_parser_recipe

    return _captured_parser_recipe(assets)


def provider_recipe(directory, selection):
    from corpus_structure.semantic.composed import (
        data_operation_dependencies,
    )
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from semantic.current_pm2_provider_fixture import operation_sources as provider_sources

    captured = projection_recipe(directory).captured_inputs
    assert captured is not None
    base_dependencies, declarations, sources = split_captured_operations(captured)
    sources = combine_primary_sources(sources, provider_sources(selection))
    dependencies = data_operation_dependencies(
        base_dependencies,
        declarations,
        sources,
    )
    return KernelRecipe(
        "current-pm2-literal-provider",
        "",
        None,
        "",
        project_id=None,
        execution_profile="source-native",
        captured_inputs=CapturedKernelInputs(captured.bundle, dependencies, captured.profile),
    )


@pytest.fixture(scope="module")
def projection_prepared(tmp_path_factory):
    root = tmp_path_factory.mktemp("current-pm2-preparation")
    directory = root / "prepared"
    directory.mkdir()
    return prepare_kernel(projection_recipe(root), directory=directory)


def pure_source(preparation, text="12", *, native_text=None):
    """Finite source-owner input for independent pure decoder expectations."""
    value = FrozenNativeSource.from_projection(
        preparation.prepared,
        document="pure:original",
        section_pointer="#/groups/0",
        membership="descendants",
        text=text,
        pieces=[
            dict(
                kind="native_text",
                item_ref="#/texts/0",
                source_field="orig" if native_text else "text",
                start=0,
                end=len(text),
            )
        ],
        items=[
            dict(
                self_ref="#/texts/0",
                label="text",
                text=text if native_text is None else native_text,
                orig=text,
                prov=[],
            )
        ],
    )
    scope = dict(source=value.value["source"], selectors=value.value["selectors"])
    context = dict(
        project_id=PROJECT,
        subject="pure:source",
        subject_definition="original-source-view",
        original_source="pure:original",
        analyzed_scope=scope,
    )
    member = BoundRoleMember(
        "pure:product",
        "pure:source-kind",
        context["subject"],
        context["original_source"],
        json_bytes(scope),
        b"{}",
        (),
        b"{}",
        subject_definition=context["subject_definition"],
        support_references=(),
    )
    frame = DeclaredNativeFrameSource.acquire(
        preparation.prepared, value.value, member, project=PROJECT
    )
    return value, frame, context
