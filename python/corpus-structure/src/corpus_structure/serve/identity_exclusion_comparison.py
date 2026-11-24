"""Exact two-root identity-exclusion comparison and optional managed read custody."""

from contextlib import ExitStack

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.semantic.continuation_codec import decode_selection_cursor, selection_digest
from corpus_structure.semantic.continuation_codec import encode_cursor as _cursor
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.identity_exclusion_comparison import (
    compare_constraint_snapshots,
    constraint_snapshot,
)
from corpus_structure.semantic.page_envelope import PageEnvelope
from corpus_structure.semantic.refusal_types import InvalidContinuation, RichQueryRefused
from corpus_structure.semantic.selected_contribution_input import RICH_NAMESPACE
from corpus_structure.semantic.selected_pages import byte_bounded_page
from corpus_structure.semantic.serving_code import capture_page_refusal
from corpus_structure.semantic.serving_identity import installed_read_implementation

from .contribution_facets import ContributionFacetsRequest
from .selected_contributions import selected_contribution_scope

VERSION = "selected-identity-exclusion-comparison-2"
CURSOR_VERSION = "selected-identity-exclusion-comparison-cursor-3"


class ConstraintRootPin(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    demand_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    product_id: str = Field(min_length=1)
    use_id: str = Field(min_length=1)
    derivation_id: str = Field(min_length=1)
    read_id: str = Field(min_length=1)
    cut_id: str = Field(min_length=1)


class ExclusionComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    before: ConstraintRootPin
    after: ConstraintRootPin
    include_unchanged: bool = False
    implementation: str | None = Field(
        default=None, min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$"
    )
    cursor: str | None = Field(default=None, max_length=32768)
    limit: int = Field(default=100, strict=True, ge=1, le=1000)
    max_bytes: int = Field(default=1048576, strict=True, ge=1024, le=67108864)
    max_graph_bytes: int = Field(default=8388608, strict=True, ge=1024, le=67108864)
    max_graph_records: int = Field(default=100000, strict=True, ge=1, le=1000000)
    max_support_edges: int = Field(default=100000, strict=True, ge=1, le=1000000)
    max_declarations: int = Field(default=10000, strict=True, ge=1, le=100000)

    def selection(self):
        return self.model_dump(
            mode="python", exclude={"implementation", "cursor", "limit", "max_bytes"}
        )


def _selected_snapshot(connection, pin, request, stack):
    scoped = ContributionFacetsRequest(
        demand_id=pin.demand_id,
        project_id=pin.project_id,
        product_id=pin.product_id,
        read_id=pin.read_id,
        expected_cut=pin.cut_id,
        max_graph_bytes=request.max_graph_bytes,
        max_graph_records=request.max_graph_records,
        max_support_edges=request.max_support_edges,
    )
    scope = stack.enter_context(selected_contribution_scope(connection, scoped))
    products = [
        item
        for item in scope.products(product_id=pin.product_id)
        if item.use_id == pin.use_id
        and item.derivation_id == pin.derivation_id
        and item.reference.member_id is None
    ]
    if len(products) != 1:
        raise RichQueryRefused(
            "constraint comparison requires exactly one actual selected whole use/product/derivation"
        )
    selected = products[0]
    if selected.nominal not in {
        RICH_NAMESPACE + "DdoRichAdmission",
        RICH_NAMESPACE + "DdoRichConsolidation",
    }:
        raise RichQueryRefused("constraint comparison requires a declared current rich graph root")
    state = scope.graph(selected)
    snapshot = constraint_snapshot(scope, selected, state)
    if sum(map(len, snapshot.entries.values())) > request.max_declarations:
        raise RichQueryRefused("constraint snapshot exceeds its examined declaration bound")
    header = dict(
        pin=pin.model_dump(mode="python"),
        cut=scope.cut.record,
        root=snapshot.reference,
        knowledge_context=snapshot.context,
        producer=snapshot.producer,
        constraint_contract=snapshot.constraint_contract,
        eligibility_policy=snapshot.policy,
        examined_constraints=sum(map(len, snapshot.entries.values())),
        examined_records=scope.index.retained_records,
    )
    return header, snapshot


def compare_selected_exclusions(reader, request: ExclusionComparisonRequest):
    from corpus_structure._query_custody import SourceCustodyError

    try:
        with installed_read_implementation(
            type(request),
            entry="corpus_structure.semantic.identity_exclusion_comparison",
            profile=VERSION,
            callables=(
                "corpus_structure.semantic.identity_exclusion_comparison.constraint_snapshot",
                "corpus_structure.semantic.identity_exclusion_comparison.compare_constraint_snapshots",
                "corpus_structure.semantic.selected_contribution_input.SelectedContributionScope.products",
                "corpus_structure.semantic.selected_contribution_input.SelectedContributionScope.graph",
                "corpus_structure.semantic.selected_pages.byte_bounded_page",
                "corpus_structure.semantic.continuation_codec.encode_cursor",
                "corpus_structure.semantic.continuation_codec.decode_selection_cursor",
            ),
        ) as implementation:
            return _compare(reader, request, implementation)
    except SourceCustodyError as error:
        raise RichQueryRefused(str(error)) from error


def _compare(reader, request, implementation):
    if request.implementation is not None and request.implementation != implementation:
        raise InvalidContinuation(
            "constraint comparison resource differs from actual installed meaning",
            reason="invalid_continuation",
        )
    # Both explicit native cuts are part of the request selection.
    digest = selection_digest(semantic_value(request.selection()))
    cursor = None
    if request.cursor is not None:
        cursor = decode_selection_cursor(
            request.cursor,
            version=CURSOR_VERSION,
            selection=digest,
            implementation=implementation,
        )
    from corpus_structure.semantic.selected_query_cache import uncached_rows_from

    # Read the exact dependency and proof populations for both roots on every request.
    with reader() as connection, ExitStack() as stack:
        before, left = _selected_snapshot(connection, request.before, request, stack)
        after, right = _selected_snapshot(connection, request.after, request, stack)
    offset = 0 if cursor is None else cursor["position"]
    source = (
        row.value
        for row in compare_constraint_snapshots(
            left,
            right,
            include_unchanged=request.include_unchanged,
            max_entries=request.max_declarations,
        )
    )
    rows = uncached_rows_from(source, offset)

    pinned = request.model_copy(update={"implementation": implementation})
    presentation = PageEnvelope(
        reuse_refusal=capture_page_refusal(),
        header=dict(
            version=VERSION,
            implementation=implementation,
            before=before,
            after=after,
            resource_handle=_cursor(pinned.model_dump(mode="python")),
            scope=dict(
                matching="exact-original-declaration-product/member-address",
                population="explicit-typed-constraints-in-two-selected-whole-roots",
                original_source_completeness="unknown",
                protected_dependencies="undisclosed-where-bounded-authority-leaves-occur",
                source_change_authority="not-established",
            ),
        ),
        cursor_basis=dict(version=CURSOR_VERSION, implementation=implementation, selection=digest),
        cursor_field="cursor",
        position_field="position",
        arrays=(("changes", None, None, None),),
    )

    try:
        return byte_bounded_page(
            rows,
            offset=offset,
            limit=request.limit,
            max_bytes=request.max_bytes,
            presentation=presentation,
        )
    except InvalidContinuation:
        raise
    except ValueError as error:
        raise RichQueryRefused(str(error)) from error
