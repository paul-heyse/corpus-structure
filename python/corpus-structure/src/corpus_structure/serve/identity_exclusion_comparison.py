"""Exact two-root identity-exclusion comparison and optional managed read custody."""

from contextlib import ExitStack
from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.demand_queries import _cursor
from corpus_structure.semantic.identity_exclusion_comparison import (
    compare_constraint_snapshots,
    constraint_snapshot,
)
from corpus_structure.semantic.refusals import InvalidContinuation
from corpus_structure.semantic.rich_queries import RichQueryRefused, rows_after

from .contribution_facets import ContributionFacetsRequest
from .rich_queries import decode_rich_cursor, installed_read_implementation
from .selected_contributions import RICH_NAMESPACE, selected_contribution_scope

VERSION = "selected-identity-exclusion-comparison-1"


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
    implementation: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
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


def compare_selected_exclusions(connection, request: ExclusionComparisonRequest):
    from corpus_structure._query_custody import COMPOSITE_READ_SOURCES, SourceCustodyError

    try:
        with installed_read_implementation(
            type(request), sources=COMPOSITE_READ_SOURCES, profile=VERSION
        ) as implementation:
            return _compare(connection, request, implementation)
    except SourceCustodyError as error:
        raise RichQueryRefused(str(error)) from error


def _compare(connection, request, implementation):
    if request.implementation is not None and request.implementation != implementation:
        raise InvalidContinuation(
            "constraint comparison resource differs from actual installed meaning",
            reason="invalid_continuation",
        )
    digest = sha256(json_bytes(semantic_value(request.selection()))).hexdigest()
    cursor = None if request.cursor is None else decode_rich_cursor(request.cursor)
    if cursor is not None and (
        set(cursor) != {"version", "implementation", "selection", "position"}
        or cursor["version"] != VERSION
        or cursor["implementation"] != implementation
        or cursor["selection"] != digest
    ):
        raise InvalidContinuation(
            "constraint comparison cursor differs from its actual roots or meaning",
            reason="invalid_continuation",
        )
    with ExitStack() as stack:
        before, left = _selected_snapshot(connection, request.before, request, stack)
        after, right = _selected_snapshot(connection, request.after, request, stack)
        values = []
        last = None
        more = False
        size = 0

        def report(position=None, *, items=None):
            token = (
                None
                if position is None
                else _cursor(
                    dict(
                        version=VERSION,
                        implementation=implementation,
                        selection=digest,
                        position=position,
                    )
                )
            )
            pinned = request.model_copy(update={"implementation": implementation})
            return dict(
                version=VERSION,
                implementation=implementation,
                before=before,
                after=after,
                changes=values if items is None else items,
                cursor=token,
                resource_handle=_cursor(pinned.model_dump(mode="python")),
                scope=dict(
                    matching="exact-original-declaration-product/member-address",
                    population="explicit-typed-constraints-in-two-selected-whole-roots",
                    original_source_completeness="unknown",
                    protected_dependencies="undisclosed-where-bounded-authority-leaves-occur",
                    source_change_authority="not-established",
                ),
            )

        rows = compare_constraint_snapshots(
            left,
            right,
            include_unchanged=request.include_unchanged,
            max_entries=request.max_declarations,
        )
        for row in rows_after(rows, None if cursor is None else cursor["position"]):
            if len(values) == request.limit:
                more = True
                break
            width = len(json_bytes(row.value)) + 1
            if size + width + len(json_bytes(report(row.position, items=[]))) > request.max_bytes:
                if not values:
                    raise RichQueryRefused("one complete constraint comparison exceeds max_bytes")
                more = True
                break
            values.append(row.value)
            size += width
            last = row.position
        result = report(last if more else None)
        if len(json_bytes(result)) > request.max_bytes:
            raise RichQueryRefused("complete constraint comparison envelope exceeds max_bytes")
        return result
