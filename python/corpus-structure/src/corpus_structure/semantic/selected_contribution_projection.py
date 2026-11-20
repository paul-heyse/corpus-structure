"""Deterministic contribution rows over bounded acquired selected support."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .candidate_contribution_facets import CandidateFacetKinds, candidate_facets
from .contribution_facets import LOCATED_KIND, graph_facets, proposal_facets
from .nonrich_contribution_facets import nonrich_facets, nonrich_family
from .refusal_types import RichQueryRefused
from .rich_queries import RichQueryRow
from .selected_contribution_input import RICH_NAMESPACE

if TYPE_CHECKING:
    from .selected_contribution_input import SelectedContributionScope


@dataclass(frozen=True)
class ContributionProjectionSelection:
    """The selectors and limits that determine one contribution row population."""

    product_id: str | None
    member_id: str | None
    kind_contract: str | None
    include_interpretation: bool
    include_assessment: bool
    max_members: int
    max_nested_members: int


def contribution_rows(
    scope: SelectedContributionScope, request: ContributionProjectionSelection
) -> Iterator[RichQueryRow]:
    if type(request) is not ContributionProjectionSelection:
        raise TypeError("contribution projection requires its captured domain selection")
    candidate_kinds = CandidateFacetKinds.from_model(scope.model, scope.prepared)
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
                decimal_fixed_point_digits=scope.decimal_fixed_point_digits,
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


def unsupported_rows(
    scope: SelectedContributionScope, selected, request: ContributionProjectionSelection
) -> Iterator[RichQueryRow]:
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
