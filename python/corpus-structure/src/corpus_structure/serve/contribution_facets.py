"""Bounded current contribution interpretation and captured assessment delivery."""

from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus_structure.semantic.candidate_contribution_facets import (
    CandidateFacetKinds,
    candidate_facets,
)
from corpus_structure.semantic.contribution_facets import (
    LOCATED_KIND,
    graph_facets,
    proposal_facets,
)
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.nonrich_contribution_facets import nonrich_facets, nonrich_family
from corpus_structure.semantic.refusals import InvalidContinuation
from corpus_structure.semantic.rich_queries import RichQueryRefused, RichQueryRow

from .rich_queries import decode_rich_cursor, installed_read_implementation
from .selected_contributions import RICH_NAMESPACE, selected_contribution_scope

VERSION = "selected-contribution-facets-2"


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
    implementation: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
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


def contribution_rows(scope, request):
    candidate_kinds = CandidateFacetKinds.from_model(scope.model, scope.prepared)
    if request.include_operations:
        uses = {}
        for use in scope.index.frontier_rows("uses"):
            uses.setdefault(use["obligation_id"], []).append(use)
        for obligation in scope.index.frontier_rows("obligations"):
            row = dict(
                obligation=obligation,
                uses=uses.get(obligation["obligation_id"], []),
                standing="native-selected-operation",
                output_absence="not-inferred",
            )
            yield RichQueryRow(dict(population="operation", row=row))
    for selected in scope.products(product_id=request.product_id):
        if (
            selected.nominal
            in {
                LOCATED_KIND,
                RICH_NAMESPACE + "DdoRichAdmission",
                RICH_NAMESPACE + "DdoRichConsolidation",
            }
            and selected.reference.member_id is None
            and len(selected.body["members"]) > request.max_members
        ):
            raise RichQueryRefused("contribution graph exceeds its admitted member bound")
        if selected.nominal == LOCATED_KIND and selected.reference.member_id is None:
            rows = proposal_facets(
                selected,
                scope.prepared,
                scope.model,
                interpretation=request.include_interpretation,
                assessment=request.include_assessment,
                member_id=request.member_id,
                max_nested_members=request.max_nested_members,
            )
        elif selected.nominal in candidate_kinds.families:
            rows = candidate_facets(
                selected,
                candidate_kinds,
                interpretation=request.include_interpretation,
                assessment=request.include_assessment,
                member_id=request.member_id,
                max_members=request.max_members,
                max_nested_members=request.max_nested_members,
            )
        elif (
            selected.nominal
            in {RICH_NAMESPACE + "DdoRichAdmission", RICH_NAMESPACE + "DdoRichConsolidation"}
            and selected.reference.member_id is None
        ):
            rows = graph_facets(
                selected,
                scope.graph(selected),
                interpretation=request.include_interpretation,
                assessment=request.include_assessment,
                member_id=request.member_id,
                max_members=request.max_members,
                max_nested_members=request.max_nested_members,
            )
        elif (
            selected.reference.member_id is None
            and nonrich_family(scope.model, selected.nominal) is not None
        ):
            rows = nonrich_facets(
                selected,
                scope.model,
                interpretation=request.include_interpretation,
                assessment=request.include_assessment,
                member_id=request.member_id,
                max_members=request.max_members,
                max_nested_members=request.max_nested_members,
            )
        else:
            rows = unsupported_rows(scope, selected, request)
        for row in rows:
            reference = row.value["row"]["reference"]
            if request.kind_contract is None or reference["kind_contract"] == request.kind_contract:
                yield row


def unsupported_rows(scope, selected, request):
    candidates = [
        (
            selected.reference.member_id,
            selected.reference.kind_contract,
            selected.context.identity_record,
        )
    ]
    if selected.reference.member_id is None:
        for row in scope.index.rows_for(
            "kb.data_product_member", product_id=selected.reference.product_id
        ):
            if len(candidates) > request.max_members:
                raise RichQueryRefused("contribution projection exceeds its actual member bound")
            context = {
                name: row[name]
                for name in ("subject", "subject_definition", "original_source", "analyzed_scope")
            }
            candidates.append((row["member_id"], row["kind_contract"], context))
    for member, contract, context in candidates:
        if request.member_id is not None and member != request.member_id:
            continue
        reference = selected.reference.model_copy(
            update={"member_id": member, "kind_contract": contract}
        ).model_dump(mode="python")
        yield RichQueryRow(
            dict(
                population="contribution",
                row=dict(
                    reference=reference,
                    context=context,
                    kind_contract=contract,
                    interpretation="unavailable",
                    assessment="unknown",
                    reason="no-current-facet-decoder-for-this-declared-nominal-kind",
                ),
            )
        )


def serve_contribution_facets(connection, request: ContributionFacetsRequest):
    from corpus_structure._query_custody import COMPOSITE_READ_SOURCES, SourceCustodyError

    try:
        with installed_read_implementation(
            type(request), sources=COMPOSITE_READ_SOURCES, profile=VERSION
        ) as implementation:
            return _serve(connection, request, implementation)
    except SourceCustodyError as error:
        raise RichQueryRefused(str(error)) from error


def _serve(connection, request, implementation):
    from corpus_structure.semantic.demand_queries import _cursor

    digest = sha256(json_bytes(semantic_value(request.selection()))).hexdigest()
    if request.implementation is not None and request.implementation != implementation:
        raise InvalidContinuation(
            "contribution resource differs from actual installed meaning",
            reason="invalid_continuation",
        )
    cursor = None if request.cursor is None else decode_rich_cursor(request.cursor)
    if cursor is not None:
        if (
            set(cursor)
            != {"version", "implementation", "selection", "read_id", "cut_id", "ordinal"}
            or cursor["version"] != VERSION
            or cursor["implementation"] != implementation
            or cursor["selection"] != digest
        ):
            raise InvalidContinuation(
                "contribution cursor differs from its exact selection or implementation",
                reason="invalid_continuation",
            )
        if request.read_id is not None and (request.read_id, request.expected_cut) != (
            cursor["read_id"],
            cursor["cut_id"],
        ):
            raise InvalidContinuation(
                "contribution cursor differs from explicit native read",
                reason="invalid_continuation",
            )
        request = request.model_copy(
            update={"read_id": cursor["read_id"], "expected_cut": cursor["cut_id"]}
        )
    from contextlib import ExitStack
    from itertools import chain

    from corpus_structure.semantic.demand_results import recheck_selected_frontier
    from corpus_structure.semantic.selected_query_cache import (
        SELECTED_QUERY_CACHE,
        bounded_rows,
        byte_bounded_page,
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
    pinned = request.model_copy(
        update=dict(
            read_id=cut.record["read_id"], expected_cut=cut.identity, implementation=implementation
        )
    )
    key = json_bytes(["facets", cut.identity, implementation, digest, stamp])
    entry, remaining = SELECTED_QUERY_CACHE.get(key), None
    metadata = None
    with ExitStack() as stack:
        if entry is None:
            scope = stack.enter_context(selected_contribution_scope(connection, pinned))
            metadata = dict(records=scope.index.retained_records)
            source = (
                row.value
                for row in contribution_rows(
                    scope, request.model_copy(update={"include_operations": False})
                )
            )
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
        offset = 0 if cursor is None else cursor["ordinal"]
        if type(offset) is not int or offset < 0:
            raise InvalidContinuation(
                "invalid contribution row ordinal", reason="invalid_continuation"
            )
        derived_offset = max(0, offset - len(operations))
        rows = chain(
            operations[offset:],
            entry.rows(derived_offset)
            if entry is not None
            else uncached_rows_from(remaining, derived_offset),
        )

        def report(end, values, more):
            token = (
                None
                if not more
                else _cursor(
                    dict(
                        version=VERSION,
                        implementation=implementation,
                        selection=digest,
                        read_id=cut.record["read_id"],
                        cut_id=cut.identity,
                        ordinal=end,
                    )
                )
            )
            return dict(
                version=VERSION,
                implementation=implementation,
                cut=cut.record,
                cut_id=cut.identity,
                selection=request.selection(),
                items=values,
                cursor=token,
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
            )

        try:
            return byte_bounded_page(
                rows, offset=offset, limit=request.limit, max_bytes=request.max_bytes, report=report
            )
        except InvalidContinuation:
            raise
        except ValueError as error:
            raise RichQueryRefused(str(error)) from error
        finally:
            if remaining is not None:
                remaining.close()
