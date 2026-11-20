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
from corpus_structure.semantic.demand_results import selected_record_index
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.selected_contribution_input import (
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
def selected_contribution_scope(connection, request, *, product_ids=None):
    scope = selected_contribution_selection(request, product_ids=product_ids)
    with selected_record_index(
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
        model = bound_data_operation_model(prepared)
        index.freeze()
        yield SelectedContributionScope(
            cut,
            index,
            prepared,
            model,
            scope,
            request.max_support_edges,
            decimal_fixed_point_digits=decimal_digit_limit(),
        )
