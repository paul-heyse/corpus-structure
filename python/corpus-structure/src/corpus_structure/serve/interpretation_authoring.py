"""Retain explicit authored inputs under native demand custody.

Authorship is input standing. It neither creates a computational episode nor
constructs a private registry, source run, consolidation cut or active selection.
"""

from __future__ import annotations

from corpus_structure.semantic.data_operation_demands import DemandPlanner
from corpus_structure.semantic.data_operation_service import (
    NativeDemandRequest,
    freeze_native_demand,
)
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.data_operation_support import (
    AuthoredFactRef,
    read_original_source_reference,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.semantic.runtime_binding_store import runtime_binding_for_release


def author_interpretations(engine, prepared, *, request: NativeDemandRequest):
    """Admit the exact typed facts frozen with their intended downstream demand.

    The supplied effective kind validates each body natively. The writer purpose,
    immutable demand, exact root context and actual admitting principal remain
    native authority; a caller's author string is retained as an assertion.
    """
    if not isinstance(request, NativeDemandRequest) or request.release_id != prepared.release_id:
        raise SemanticRefusal(
            "authored input requires its exact admitted release and native demand request"
        )
    names = tuple(
        name
        for name, selected in request.original_sources.items()
        if isinstance(
            read_original_source_reference(canonical_bytes(selected.reference)), AuthoredFactRef
        )
    )
    if not names:
        raise SemanticRefusal(
            "authored input requires at least one explicit authored-fact selection"
        )
    intent = freeze_native_demand(prepared, request)
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model

    with engine.begin() as connection:
        from corpus_structure.semantic.authored_interpretations import JUDGMENT_KINDS
        from corpus_structure.semantic.data_operation_identity import decode_semantic_value
        from corpus_structure.semantic.data_operation_json import json_bytes

        model = bound_data_operation_model(prepared)
        definitions = {item.iri: item.name for item in prepared.definitions}
        judgment_kinds = {
            item.key: item.owner
            for item in model.identities
            if item.domain == "kind" and definitions.get(item.owner) in JUDGMENT_KINDS
        }
        for value in request.original_sources.values():
            reference = value.reference
            kind_contract = reference.get("kind_contract")
            nominal = judgment_kinds.get(kind_contract) if isinstance(kind_contract, str) else None
            if reference.get("kind") != "authored-fact" or nominal is None:
                continue
            body, context = authenticate_judgment_source(
                connection,
                prepared,
                nominal,
                decode_semantic_value(reference["meaning_body"]),
                expected_project=request.project_id,
            )
            if reference["project_id"] != body["source_record"]["project_id"] or any(
                json_bytes(reference[name]) != json_bytes(getattr(context, name))
                for name in ("subject", "subject_definition", "original_source", "analyzed_scope")
            ):
                raise SemanticRefusal(
                    "authored judgment admission differs from selected source context"
                )
        runtime_binding_for_release(connection, prepared, request.runtime_id)
        storage = DataOperationStorage(connection)
        registered = DemandPlanner(bound_data_operation_model(prepared), storage).register(
            intent,
            project=request.project_id,
            release=prepared.release_id,
            runtime=request.runtime_id,
            strength=request.strength,
        )
        if registered.get("state") == "cancelled":
            raise SemanticRefusal("cancelled demand cannot admit new authored facts")
        from corpus_structure.semantic.demand_results import read_demand_result

        continuation, cut, found = None, None, {}
        while True:
            page = read_demand_result(
                connection,
                registered["demand_id"],
                project_id=request.project_id,
                continuation=continuation,
                cut=cut,
                limit=1000,
                view="frontier",
            )
            cut = page.cut
            for value in page.record["original_source_admissions"]:
                if value["selection_name"] in names:
                    previous = found.setdefault(value["admission_id"], value)
                    if previous != value:
                        raise SemanticRefusal("authored admission changed across its pinned read")
            continuation = page.continuation
            if continuation is None:
                break
        admissions = tuple(found[key] for key in sorted(found))
        if len(admissions) != len(names) or any(
            not isinstance(value["evidence"], dict)
            or value["evidence"].get("standing") != "authored"
            for value in admissions
        ):
            raise SemanticRefusal("native demand did not retain the exact authored fact admissions")
    return {
        "demand_id": registered["demand_id"],
        "release_id": prepared.release_id,
        "runtime_id": request.runtime_id,
        "authored_admissions": admissions,
        "standing": "authored",
        "selected": False,
    }


def authenticate_judgment_source(connection, prepared, nominal, body, *, expected_project=None):
    """Reopen the actual pinned source cut, never infer custody from payload labels."""
    from corpus_structure.semantic.authored_interpretations import (
        checked_judgment,
        judgment_reading,
    )
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.semantic.demand_results import selected_record_index
    from corpus_structure.semantic.grouped_record_interpretations import (
        GroupedInterpretationRequest,
        InterpretationRoot,
        grouped_candidate_product,
    )
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.selected_contribution_input import SelectedContributionScope

    body = checked_judgment(prepared, nominal, body)
    source = body["source_record"]
    if expected_project is not None and source["project_id"] != expected_project:
        raise ValueError("authored judgment source belongs to another selected project")
    scope = json_loads(source["read_scope_json"])
    if not isinstance(scope, dict):
        raise ValueError("authored judgment source read requires its exact object scope")
    request = GroupedInterpretationRequest(
        project_id=source["project_id"],
        demand_id=source["demand_id"],
        read_id=source["read_id"],
        expected_cut=source["cut_id"],
        roots=(InterpretationRoot(product_id=source["product_id"], member_id=source["member_id"]),),
    )
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
        original = open_release(connection, cut.record["release_id"])
        selected = SelectedContributionScope(
            cut,
            index,
            original,
            bound_data_operation_model(original),
            scope,
            request.max_support_edges,
        )
        groups = tuple(
            group
            for product in selected.products(product_id=source["product_id"])
            if product.reference.member_id is None
            for group in grouped_candidate_product(
                selected.prepared, selected.model, product, request.roots
            )
        )
        group, _reading = judgment_reading(body, groups, selected.cut)
        return body, group.context


def selected_authored_judgments(connection, selected, product_ids):
    """Read actual authored admissions from this selected demand's pinned native index."""
    from corpus_structure.semantic.data_operation_identity import decode_semantic_value
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_support import AuthoredFactSupportReference
    from corpus_structure.semantic.rich_knowledge_contracts import DdoRichSelectedMember

    products = selected.index.mapping("kb.data_product", ("id",))
    kinds = selected.index.mapping("sem.data_kind_contract", ("kind_contract",))
    admissions = selected.index.mapping("ops.original_source_admission", ("id",))
    found = set()
    for frontier in selected.index.frontier_rows("original_source_admissions"):
        product_id = frontier["product_id"]
        if product_id not in product_ids:
            continue
        admission = admissions.get(frontier["admission_id"])
        if admission is None or any(
            json_bytes(frontier[name]) != json_bytes(admission[name])
            for name in (
                "product_id",
                "selection_name",
                "source_reference",
                "subject",
                "original_source",
                "analyzed_scope",
                "trust_snapshot",
                "evidence",
            )
        ):
            raise ValueError("valid authored frontier differs from its exact original admission")
        if (
            admission["demand_id"] != selected.cut.record["demand_id"]
            or admission["project_id"] != selected.cut.record["project_id"]
            or admission["evidence"].get("standing") != "authored"
        ):
            raise ValueError(
                "judgment requires an actual authored admission in this selected demand"
            )
        original = read_original_source_reference(json_bytes(admission["reference"]))
        if not isinstance(original, AuthoredFactRef):
            raise ValueError("selected judgment cannot relabel an original or computed input")
        product = products[product_id]
        if (
            frontier["kind_contract"] != product["kind_contract"]
            or frontier["subject_definition"] != product["subject_definition"]
        ):
            raise ValueError("authored frontier differs from its actual captured product contract")
        body = decode_semantic_value(product["canonical_body"])
        if (
            original.kind_contract != product["kind_contract"]
            or original.project_id != product["project_id"]
            or json_bytes(decode_semantic_value(original.meaning_body)) != json_bytes(body)
            or any(
                json_bytes(getattr(original, name)) != json_bytes(product[name])
                for name in ("subject", "subject_definition", "original_source", "analyzed_scope")
            )
        ):
            raise ValueError("authored judgment differs from its admitted original body or context")
        body, context = authenticate_judgment_source(
            connection,
            selected.prepared,
            kinds[product["kind_contract"]]["kind"],
            body,
            expected_project=selected.cut.record["project_id"],
        )
        if any(
            json_bytes(getattr(original, name)) != json_bytes(getattr(context, name))
            for name in ("subject", "subject_definition", "original_source")
        ) or json_bytes(original.analyzed_scope) != json_bytes(context.analyzed_scope):
            raise ValueError("authored judgment context differs from its actual selected source")
        found.add(product_id)
        yield (
            body,
            dict(
                reference=DdoRichSelectedMember(
                    product_id=product_id,
                    member_id=None,
                    kind_contract=product["kind_contract"],
                    support_references=(
                        AuthoredFactSupportReference(
                            admission_id=admission["id"],
                            source_reference=admission["source_reference"],
                        ),
                    ),
                ),
                author=original.author,
                selection_id=original.selection_id,
                source_reference=admission["source_reference"],
            ),
        )
    if found != set(product_ids):
        raise ValueError("authored judgment roots require exact selected authored admissions")


def read_authored_judgment_selection(connection, request, selected_read):
    """Acquire one explicitly pinned authored input read using common native custody."""
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.demand_results import selected_record_index
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.selected_contribution_input import SelectedContributionScope

    with selected_record_index(
        connection,
        selected_read.demand_id,
        project_id=request.project_id,
        scope=selected_read.scope,
        read_id=selected_read.read_id,
        expected_cut=selected_read.expected_cut,
        max_bytes=request.max_graph_bytes,
        max_total_bytes=request.max_graph_bytes,
        max_total_records=request.max_graph_records,
        capture_frontier=True,
    ) as (cut, index):
        prepared = open_release(connection, cut.record["release_id"])
        selected = SelectedContributionScope(
            cut,
            index,
            prepared,
            bound_data_operation_model(prepared),
            selected_read.scope,
            request.max_support_edges,
        )
        yield from selected_authored_judgments(connection, selected, selected_read.product_ids)
