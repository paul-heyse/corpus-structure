"""Selected ordinary structural conclusions with explicit bounded native authority."""

from typing import Any

from corpus_structure.semantic.authority_leaf import NativeAuthorityLeaf
from corpus_structure.semantic.data_operation_identity import decode_semantic_value, semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.declared_structural_admission import (
    ADMISSION_KIND,
    ADMISSION_OPERATION,
    DdoStructuralAdmission,
)
from corpus_structure.semantic.declared_structural_references import DeclaredProductRef
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_admission import structural_statement


def _selected_structural_conclusion(scope, root):
    """Only an actual native authority leaf grants this ordinary scoped standing."""
    if root.member_id is not None:
        raise ValueError("structural admission requires its actual whole conclusion")
    leaves = tuple(
        NativeAuthorityLeaf.model_validate(value)
        for value in scope.index.rows("ops.data_authority_leaf")
        if value["product_id"] == root.product_id
        and value["derivation_id"] == root.derivation_id
        and value["use_id"] == root.use_id
    )
    if not leaves:
        return None
    if len(leaves) != 1:
        raise ValueError("structural admission repeats a native authority identity")
    leaf = leaves[0]
    if leaf.issuer_operation != ADMISSION_OPERATION:
        raise ValueError("selected authority is not a structural admission issuer")
    kinds = scope.index.mapping("sem.data_kind_contract", ("kind_contract",))
    products = scope.index.mapping("kb.data_product", ("id",))
    contracts = {
        identity.key
        for identity in scope.model.identities
        if identity.domain == "kind" and identity.owner == ADMISSION_KIND
    }
    complete = any(
        kind.semantic_id == ADMISSION_KIND and kind.complete for kind in scope.model.kinds
    )
    if (
        not complete
        or leaf.kind_contract not in contracts
        or kinds[leaf.kind_contract]["universe"] != "ordinary"
    ):
        raise ValueError("structural admission lacks its exact captured ordinary kind contract")
    # The native selected reader already authenticates original issuer and runtime
    # visibility. Detached acquisition verifies actual archived issuer/runtime rows;
    # this projection does not manufacture a second runtime attestation.
    if leaf.standing != "valid":
        return None
    product = products[leaf.product_id]
    if (
        product["project_id"] != scope.cut.record["project_id"]
        or kinds[leaf.kind_contract]["kind"] != ADMISSION_KIND
    ):
        raise ValueError("structural admission belongs to another selected project or kind")
    value = DdoStructuralAdmission.model_validate_json(
        json_bytes(decode_semantic_value(product["canonical_body"]))
    )
    return value, leaf


def selected_structural_admission(scope, root, selected_report, report):
    admitted = _selected_structural_conclusion(scope, root)
    if admitted is None:
        return None
    value, leaf = admitted
    context = selected_report.context
    from corpus_structure.semantic.data_operation_model import json_context_meaning

    reference = DeclaredProductRef(
        product_id=selected_report.reference.product_id,
        member_id=selected_report.reference.member_id,
        kind_contract=selected_report.reference.kind_contract,
        project_id=context.project_id,
        subject=context.subject,
        subject_definition=context.subject_definition,
        original_source=context.original_source,
        analyzed_scope_meaning=json_context_meaning(context.analyzed_scope).decode(),
    )
    if (
        value.report != reference
        or value.statement_meaning_json
        != canonical_bytes(
            semantic_value(structural_statement(report, value.component_id))
        ).decode()
    ):
        raise ValueError("structural admission differs from exact selected report and statement")
    return value, leaf


def selected_structural_support_root(scope, root, admission_root):
    """Read one ordinary report through its native selectively disclosed issuer edge."""
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
    from corpus_structure.semantic.declared_structural_admission import (
        validate_structural_report_support,
    )
    from corpus_structure.semantic.rich_knowledge_contracts import DdoRichSelectedMember
    from corpus_structure.semantic.selected_contribution_input import SelectedContribution

    admitted = _selected_structural_conclusion(scope, admission_root)
    if admitted is None or root.member_id is not None:
        return None
    _, leaf = admitted
    edges = [
        edge
        for edge in scope.index.rows("ops.data_derivation_support")
        if edge["derivation_id"] == leaf.derivation_id
        and edge["support_derivation_id"] == root.derivation_id
        and edge.get("admission_use_id") == root.use_id
    ]
    if not edges:
        return None
    if len(edges) != 1:
        raise ValueError("structural report root repeats its actual ordinary issuer edge")
    products = scope.index.mapping("kb.data_product", ("id",))
    kinds = scope.index.mapping("sem.data_kind_contract", ("kind_contract",))
    requests = scope.index.mapping("ops.data_request", ("id",))
    value, used, episode, output = validate_structural_report_support(
        edges[0],
        leaf=leaf,
        products=products,
        kinds=kinds,
        uses=scope.index.mapping("ops.demand_use", ("id",)),
        episodes=scope.index.mapping("ops.data_derivation", ("id",)),
        outputs=scope.index.rows("ops.data_derivation_output"),
        requests=requests,
        definitions=scope.index.mapping(
            "sem.data_operation_definition", ("release_id", "operation_id")
        ),
        intents=scope.index.mapping("ops.data_completion_intent", ("id",)),
        receipts=scope.index.rows("ops.data_publication_receipt"),
    )
    if value.report.product_id != root.product_id:
        return None
    product = products[root.product_id]
    context = SubjectContext(
        product["project_id"],
        product["subject"],
        product["original_source"],
        json_bytes(product["analyzed_scope"]),
        subject_definition=product["subject_definition"],
    )
    reference = DdoRichSelectedMember(
        product_id=root.product_id,
        member_id=None,
        kind_contract=product["kind_contract"],
        support_references=(
            ComputationalSupportReference(derivation_id=episode["id"], admission_use_id=used["id"]),
        ),
    )
    return SelectedContribution(
        reference,
        context,
        decode_semantic_value(product["canonical_body"]),
        kinds[product["kind_contract"]]["kind"],
        requests[episode["request_id"]]["operation_id"],
        used["id"],
        episode["id"],
        output,
    )


def supported_comparison_gap_rows(
    request, report, admission, binding_report
) -> list[dict[str, Any]]:
    def unavailable(reason):
        return [
            dict(
                status="unavailable",
                reason=reason,
                operation="qualified_comparison",
                outcome="not_assessed",
                evidence={},
            )
        ]

    if report.comparison is None:
        raise ValueError("supported comparison gap requires its actual comparison report")
    if request.scope not in (None, report.inputs.scope):
        raise ValueError("scope differs from the exact selected comparison")
    if admission is None:
        return unavailable("authorized_comparison_support_unavailable")
    if binding_report is None:
        return unavailable("binding_production_unavailable")
    if binding_report.dossier is None:
        raise ValueError("comparison binding root is not an actual dossier")
    value, leaf = admission
    from corpus_structure.semantic.declared_structural_references import DeclaredStructuralRef

    reference = DeclaredStructuralRef(**value.report.model_dump(), structural_id=report.product_id)
    dossier = binding_report.dossier
    if reference not in dossier.predecessors:
        return unavailable("comparison_outside_binding_selection")
    bound = {
        member.comparison_binding.side
        for member in dossier.members
        if member.comparison_binding is not None
        and member.comparison_binding.comparison_ref == reference
    }
    missing = {"left", "right"} - bound
    if not missing:
        return []
    passages = {passage.passage_id: passage for passage in report.inputs.passages}
    sources = {source.identity: source for source in report.inputs.sources}
    comparison = report.comparison
    sides = {}
    for side in sorted(missing):
        passage = passages[getattr(comparison, side + "_id")]
        sides[side] = dict(
            passage=passage.model_dump(mode="python"),
            source=sources[passage.source_ref].model_dump(mode="python"),
            reading=getattr(comparison, side + "_reading").model_dump(mode="python"),
        )
    return [
        dict(
            status="actionable",
            reason="no_qualifying_root_binding",
            operation="qualified_comparison",
            outcome="produced",
            evidence=dict(
                comparison=reference.model_dump(mode="python"),
                sides=sides,
                support=dict(
                    admission=value.model_dump(mode="python"),
                    authority=leaf.model_dump(mode="python"),
                ),
                root=dossier.root_component.model_dump(mode="python"),
                binding_product_id=binding_report.product_id,
                binding_status="inspected_no_binding",
                assessment_scope="comparison_statement",
                scientific_truth="not_established",
            ),
        )
    ]
