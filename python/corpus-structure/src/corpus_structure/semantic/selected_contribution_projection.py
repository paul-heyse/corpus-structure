"""Deterministic contribution rows over bounded acquired selected support."""

from .candidate_contribution_facets import CandidateFacetKinds, candidate_facets
from .contribution_facets import LOCATED_KIND, graph_facets, proposal_facets
from .nonrich_contribution_facets import nonrich_facets, nonrich_family
from .refusal_types import RichQueryRefused
from .rich_queries import RichQueryRow
from .selected_contribution_input import RICH_NAMESPACE


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
