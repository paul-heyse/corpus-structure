"""Acquire bounded native support before deterministic selected-contribution reads."""

from contextlib import contextmanager

from corpus_structure.semantic._data_operation_wire import (
    WireDemandReadScope,
    WireOperationId,
    WireOriginalSourceId,
    WireProductId,
    WireSubjectId,
)
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.demand_results import (
    CutSelection,
    acquired_selected_relations,
    read_selected_answer,
)
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.selected_contribution_input import (
    LiveContributionRead,
    SelectedContributionScope,
)
from corpus_structure.semantic.value_codec import decimal_digit_limit


def selected_contribution_selection(request, *, product_ids=None) -> WireDemandReadScope:
    if product_ids is None:
        product_ids = None if request.product_id is None else [request.product_id]
    else:
        product_ids = sorted(set(product_ids))
        if not product_ids or (
            request.product_id is not None and product_ids != [request.product_id]
        ):
            raise ValueError("selected product roots differ from the requested product scope")
    scope: WireDemandReadScope = {}
    if request.operation_id is not None:
        scope["operation_id"] = WireOperationId(request.operation_id)
    if request.subject is not None:
        scope["subject"] = WireSubjectId(request.subject)
    if product_ids is not None:
        scope["product_ids"] = [WireProductId(product) for product in product_ids]
    if "original_source" in request.model_fields_set:
        source = request.original_source
        scope["original_source"] = None if source is None else WireOriginalSourceId(source)
    return scope


@contextmanager
def selected_contribution_scope(connection, request, *, product_ids=None, require_support=False):
    scope = selected_contribution_selection(request, product_ids=product_ids)
    if require_support:
        with acquired_selected_relations(
            connection,
            request.demand_id,
            project_id=request.project_id,
            scope=scope,
            read_id=request.read_id,
            expected_cut=request.expected_cut,
            max_bytes=request.max_graph_bytes,
            max_total_bytes=request.max_graph_bytes,
            max_total_records=request.max_graph_records,
            capture_frontier=True,
        ) as (cut, index):
            prepared = open_release(connection, cut.record["release_id"])
            index.freeze()
            yield SelectedContributionScope(
                cut,
                index,
                prepared,
                bound_data_operation_model(prepared),
                scope,
                request.max_support_edges,
                decimal_fixed_point_digits=decimal_digit_limit(),
            )
        return
    first = read_selected_answer(
        connection,
        "read_selected_outputs",
        request.demand_id,
        project_id=request.project_id,
        scope=scope,
        read_id=request.read_id,
        limit=1,
        max_bytes=request.max_graph_bytes,
    )
    cut = CutSelection.from_native(first["cut"])
    if request.expected_cut is not None and request.expected_cut != cut.identity:
        raise ValueError("selected contribution differs from its expected cut")
    prepared = open_release(connection, cut.record["release_id"])
    model = bound_data_operation_model(prepared)
    live = LiveContributionRead(
        connection, model, cut, scope, request.max_graph_bytes, request.max_graph_records
    )
    yield SelectedContributionScope(
        cut,
        live,
        prepared,
        model,
        scope,
        request.max_support_edges,
        decimal_fixed_point_digits=decimal_digit_limit(),
        live=live,
    )
