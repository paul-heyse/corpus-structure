"""Bounded current contribution interpretation and captured assessment delivery."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus_structure.semantic.continuation_codec import (
    bind_cursor_request,
    decode_pinned_cursor,
    pinned_cursor_basis,
    require_cursor_cut,
    require_cursor_implementation,
    selection_digest,
)
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.page_envelope import PageEnvelope
from corpus_structure.semantic.refusal_types import InvalidContinuation, RichQueryRefused
from corpus_structure.semantic.selected_contribution_projection import (
    ContributionProjectionSelection,
    contribution_rows,
)
from corpus_structure.semantic.selected_pages import byte_bounded_page
from corpus_structure.semantic.serving_code import capture_page_refusal
from corpus_structure.semantic.serving_identity import installed_read_implementation

from .selected_contributions import selected_contribution_scope

VERSION = "selected-contribution-facets-2"
CURSOR_VERSION = "selected-contribution-facets-cursor-3"


class ContributionFacetsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    demand_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    product_id: str | None = None
    operation_id: str | None = None
    subject: str | None = None
    original_source: str | None = None
    member_id: str | None = None
    kind_contract: str | None = None
    include_interpretation: bool = True
    include_assessment: bool = True
    include_operations: bool = True
    read_id: str | None = None
    expected_cut: str | None = None
    implementation: str | None = Field(
        default=None, min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$"
    )
    cursor: str | None = Field(default=None, max_length=32768)
    limit: int = Field(default=100, strict=True, ge=1, le=1000)
    max_bytes: int = Field(default=1048576, strict=True, ge=1024, le=67108864)
    max_graph_bytes: int = Field(default=8388608, strict=True, ge=1024, le=67108864)
    max_graph_records: int = Field(default=100000, strict=True, ge=1, le=1000000)
    max_members: int = Field(default=100000, strict=True, ge=1, le=1000000)
    max_nested_members: int = Field(default=1000, strict=True, ge=1, le=10000)
    max_support_edges: int = Field(default=100000, strict=True, ge=1, le=1000000)

    @model_validator(mode="after")
    def pinned_read(self):
        if (self.read_id is None) != (self.expected_cut is None):
            raise ValueError("current contribution read requires both read_id and expected_cut")
        return self

    def selection(self):
        value = self.model_dump(
            mode="python",
            exclude={"read_id", "expected_cut", "implementation", "cursor", "limit", "max_bytes"},
        )
        if "original_source" not in self.model_fields_set:
            value.pop("original_source")
        return value

    def projection(self) -> ContributionProjectionSelection:
        return ContributionProjectionSelection(
            product_id=self.product_id,
            member_id=self.member_id,
            kind_contract=self.kind_contract,
            include_interpretation=self.include_interpretation,
            include_assessment=self.include_assessment,
            max_members=self.max_members,
            max_nested_members=self.max_nested_members,
        )


def serve_contribution_facets(connection, request: ContributionFacetsRequest):
    from corpus_structure._query_custody import SourceCustodyError

    try:
        with installed_read_implementation(
            type(request),
            entry="corpus_structure.semantic.selected_contribution_projection",
            profile=VERSION,
            callables=(
                "corpus_structure.semantic.selected_contribution_projection.contribution_rows",
                "corpus_structure.semantic.selected_contribution_input.SelectedContributionScope.products",
                "corpus_structure.semantic.selected_contribution_input.SelectedContributionScope.graph",
                "corpus_structure.semantic.selected_pages.byte_bounded_page",
                "corpus_structure.semantic.continuation_codec.encode_cursor",
                "corpus_structure.semantic.continuation_codec.decode_pinned_cursor",
                "corpus_structure.semantic.continuation_codec.bind_cursor_request",
            ),
        ) as implementation:
            return _serve(connection, request, implementation)
    except SourceCustodyError as error:
        raise RichQueryRefused(str(error)) from error


def _serve(connection, request, implementation):
    from corpus_structure.semantic.continuation_codec import encode_cursor as _cursor

    digest = selection_digest(semantic_value(request.selection()))
    if request.implementation is not None and request.implementation != implementation:
        raise InvalidContinuation(
            "contribution resource differs from actual installed meaning",
            reason="invalid_continuation",
        )
    cursor = None
    if request.cursor is not None:
        cursor = decode_pinned_cursor(request.cursor, version=CURSOR_VERSION, selection=digest)
        require_cursor_implementation(cursor, implementation)
        request = bind_cursor_request(request, cursor)
    from contextlib import ExitStack
    from itertools import chain

    from corpus_structure.semantic.demand_results import recheck_selected_frontier
    from corpus_structure.semantic.selected_query_cache import (
        SELECTED_QUERY_CACHE,
        bounded_rows,
        served_key,
        uncached_rows_from,
    )

    from .selected_contributions import selected_contribution_selection

    cut, frontier, stamp = recheck_selected_frontier(
        connection,
        request.demand_id,
        project_id=request.project_id,
        scope=selected_contribution_selection(request),
        read_id=request.read_id,
        expected_cut=request.expected_cut,
        max_bytes=request.max_graph_bytes,
        max_records=request.max_graph_records,
    )
    if cursor is not None:
        require_cursor_cut(cursor, cut)
    pinned = request.model_copy(
        update=dict(
            read_id=cut.record["read_id"], expected_cut=cut.identity, implementation=implementation
        )
    )
    key = served_key(
        connection,
        "facets",
        implementation=implementation,
        basis=cut.identity,
        selection=["facets", cut.identity, implementation, digest, stamp],
    )
    remaining = None
    metadata = None
    with SELECTED_QUERY_CACHE.loading(key) as entry, ExitStack() as stack:
        if entry is None:
            scope = stack.enter_context(selected_contribution_scope(connection, pinned))
            metadata = dict(records=scope.index.retained_records)
            source = (row.value for row in contribution_rows(scope, request.projection()))
            entry, remaining = bounded_rows(source, metadata)
            if entry is not None:
                SELECTED_QUERY_CACHE.put(key, entry)
        metadata = entry.record() if entry is not None else metadata
        assert metadata is not None
        operations = []
        if request.include_operations:
            uses = {}
            for use in frontier["uses"]:
                # The existing selected record index deliberately omits product
                # bodies from native operation rows. Rebuild those authority
                # observations fresh, preserving that exact projection.
                value = {key: value for key, value in use.items() if key != "products"}
                uses.setdefault(use["obligation_id"], []).append(value)
            operations = [
                dict(
                    population="operation",
                    row=dict(
                        obligation=obligation,
                        uses=uses.get(obligation["obligation_id"], []),
                        standing="native-selected-operation",
                        output_absence="not-inferred",
                    ),
                )
                for obligation in frontier["obligations"]
            ]
        offset = 0 if cursor is None else cursor["position"]
        derived_offset = max(0, offset - len(operations))
        rows = chain(
            operations[offset:],
            entry.rows(derived_offset)
            if entry is not None
            else uncached_rows_from(remaining, derived_offset),
        )

        presentation = PageEnvelope(
            reuse_refusal=capture_page_refusal(),
            header=dict(
                version=VERSION,
                implementation=implementation,
                cut=cut.record,
                cut_id=cut.identity,
                selection=request.selection(),
                resource_handle=_cursor(pinned.model_dump(mode="python", exclude_unset=True)),
                examination=dict(
                    records=metadata["records"],
                    scope="exact-native-selected-product-and-disclosed-support-population",
                    global_completeness="unknown",
                    protected_dependencies="undisclosed-where-bounded-authority-leaves-occur",
                ),
                interpretation_scope="declared-rich-graph-private-candidate-finite-and-structural-meaning",
                assessment_scope="captured-native-producer-judgments",
                source_completeness="unknown",
            ),
            cursor_basis=pinned_cursor_basis(CURSOR_VERSION, digest, cut, implementation),
            cursor_field="cursor",
            position_field="position",
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
        finally:
            if remaining is not None:
                remaining.close()
