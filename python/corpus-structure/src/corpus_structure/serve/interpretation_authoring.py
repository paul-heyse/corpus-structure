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
from corpus_structure.semantic.runtime_binding_store import runtime_binding_for_release
from corpus_structure.semantic.refusals import SemanticRefusal


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
        raise SemanticRefusal("authored input requires at least one explicit authored-fact selection")
    intent = freeze_native_demand(prepared, request)
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model

    with engine.begin() as connection:
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
