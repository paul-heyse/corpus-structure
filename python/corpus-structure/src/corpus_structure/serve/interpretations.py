"""Bounded transport-neutral interpretation lookup and retained review detail."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from corpus_structure.semantic.data_operation_json import DdoJsonValue, json_bytes
from corpus_structure.semantic.demand_queries import DemandQueryRequest, serve_demand_query
from corpus_structure.semantic.grouped_record_interpretations import GroupedInterpretationRequest
from corpus_structure.semantic.page_envelope import PageEnvelope
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.selected_pages import byte_bounded_page
from corpus_structure.semantic.serving_code import capture_page_refusal


class InterpretationAnswer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: str = "source-interpretation-1"
    kind: str
    body: dict[str, DdoJsonValue]


def answer(kind, body, max_bytes=1024**2):
    from corpus_structure.semantic.refusal_types import ReadLimit

    report = InterpretationAnswer(kind=kind, body=body)
    content = json_bytes(report.model_dump(mode="python"))
    if len(content) > max_bytes:
        raise ReadLimit("interpretation response exceeds byte budget", reason="oversized_item")
    return report


def term_lookup(conn, *, release_id, field, query=None, browse=False, max_bytes=1024**2):
    from corpus_structure.semantic.interpretations import lookup_terms

    return answer(
        "terminology_lookup",
        lookup_terms(open_release(conn, release_id), field, query, browse=browse),
        max_bytes,
    )


class SelectedProposalRequest(DemandQueryRequest):
    """A genuine selected private proposal member, never an integer review alias."""

    view: Literal["members"] = "members"
    containers_only: Literal[False] = False


def inspect_selected_proposals(connection, request: SelectedProposalRequest):
    """Inspect actual captured private proposal kinds without granting accepted standing.

    Grouped measurement interpretation is not supplied by this selected member view.
    Native purpose and authority-leaf controls remain the only disclosure authority.
    """
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model

    result = serve_demand_query(connection, request)
    prepared = open_release(connection, result["cut"]["release_id"])
    contracts = {
        identity.owner: identity.key
        for identity in bound_data_operation_model(prepared).identities
        if identity.domain == "kind"
    }
    kinds = {
        contracts[definition.iri]: definition.name
        for definition in prepared.index.definitions.values()
        if definition.iri in contracts and "DdoRichProposalValue" in definition.ancestors
    }
    if request.kind_contract is not None and request.kind_contract not in kinds:
        raise ValueError("selected contract is not a captured private proposal member kind")
    items = []
    for row in result["items"]:
        nominal = kinds.get(row["kind_contract"])
        if nominal is None:
            continue
        checked = prepared.validate_json(nominal, json_bytes(row["body"])).model_dump(
            mode="python", exclude_unset=True
        )
        if checked["standing"] != "private_proposed":
            raise ValueError("selected proposal cannot assert accepted standing")
        items.append({**row, "body": checked})
    return answer(
        "selected_private_proposals",
        {
            **result,
            "items": items,
            "knowledge": "observed" if items else "unknown",
            "capability": "selected_private_proposal_members" if kinds else "unavailable",
        },
        request.max_bytes,
    )


def group_selected_interpretations(
    connection, request: GroupedInterpretationRequest
) -> InterpretationAnswer:
    """Read complete occurrence groups from exact selected candidate universes."""
    from corpus_structure._query_custody import (
        SourceCustodyError,
    )
    from corpus_structure.semantic.serving_identity import installed_read_implementation

    try:
        with installed_read_implementation(
            type(request),
            entry="corpus_structure.semantic.grouped_interpretation_projection",
            profile="grouped-source-records-2",
            callables=(
                "corpus_structure.semantic.grouped_interpretation_projection.grouped_interpretation_rows",
                "corpus_structure.semantic.selected_contribution_input.SelectedContributionScope.products",
                "corpus_structure.semantic.selected_pages.byte_bounded_page",
                "corpus_structure.semantic.continuation_codec.encode_cursor",
                "corpus_structure.semantic.continuation_codec.decode_cursor",
            ),
        ) as implementation:
            return _group_selected_interpretations(connection, request, implementation)
    except SourceCustodyError as error:
        raise ValueError(str(error)) from error


def _group_selected_interpretations(connection, request, implementation):
    import base64
    from hashlib import sha256

    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.semantic.grouped_interpretation_projection import (
        grouped_interpretation_rows,
    )
    from corpus_structure.semantic.refusal_types import InvalidContinuation, ReadLimit
    from corpus_structure.serve.selected_contributions import selected_contribution_scope

    if request.implementation is not None and request.implementation != implementation:
        raise ValueError("grouped interpretation resource differs from actual installed meaning")
    selection = request.selection()
    digest = sha256(json_bytes(selection)).hexdigest()
    cursor = None
    if request.cursor is not None:
        try:
            cursor = json_loads(base64.b64decode(request.cursor, altchars=b"-_", validate=True))
        except (ValueError, TypeError) as error:
            raise ValueError("invalid grouped interpretation cursor") from error
        if (
            not isinstance(cursor, dict)
            or set(cursor)
            != {"version", "implementation", "selection", "read_id", "cut_id", "offset"}
            or cursor["version"] != "grouped-source-records-2"
            or cursor["implementation"] != implementation
            or cursor["selection"] != digest
            or type(cursor["offset"]) is not int
            or cursor["offset"] < 0
        ):
            raise ValueError("cursor differs from the exact grouped interpretation selection")
    if (
        cursor is not None
        and request.read_id is not None
        and (request.read_id, request.expected_cut) != (cursor["read_id"], cursor["cut_id"])
    ):
        raise ValueError("grouped interpretation cursor differs from explicit native read")
    acquired = (
        request
        if cursor is None
        else request.model_copy(
            update={"read_id": cursor["read_id"], "expected_cut": cursor["cut_id"]}
        )
    )
    roots = {}
    for root in request.roots:
        roots.setdefault(root.product_id, []).append(root)
    from corpus_structure.semantic.authored_interpretations import JUDGMENT_KINDS
    from corpus_structure.semantic.demand_results import read_selected_operation_frontier
    from corpus_structure.semantic.selected_query_cache import uncached_rows_from

    from .selected_contributions import selected_contribution_selection

    scope = selected_contribution_selection(
        acquired, product_ids=(*roots, *request.authored_products)
    )
    current_cut, frontier = read_selected_operation_frontier(
        connection,
        request.demand_id,
        project_id=request.project_id,
        scope=scope,
        read_id=acquired.read_id,
        expected_cut=acquired.expected_cut,
        max_bytes=request.max_graph_bytes,
        max_records=request.max_graph_records,
    )
    acquired = acquired.model_copy(
        update=dict(read_id=current_cut.record["read_id"], expected_cut=current_cut.identity)
    )
    # Acquire each authored cut and the determining bodies before rendering the grouped rows.
    with selected_contribution_scope(
        connection,
        acquired,
        product_ids=(*roots, *request.authored_products),
        require_support=bool(request.authored_products),
    ) as selected:
        authored_judgments = []
        if request.authored_products or request.authored_reads:
            from .interpretation_authoring import (
                read_authored_judgment_selection,
                selected_authored_judgments,
            )

            authored_judgments.extend(
                selected_authored_judgments(connection, selected, request.authored_products)
            )
            for authored_read in request.authored_reads:
                authored_judgments.extend(
                    read_authored_judgment_selection(connection, request, authored_read)
                )
        items, metadata = grouped_interpretation_rows(selected, request, tuple(authored_judgments))
    universes, finite_universes, judgment_contracts = (
        metadata["universes"],
        metadata["finite_universes"],
        metadata["judgment_contracts"],
    )
    cut_id, cut = current_cut.identity, current_cut.record
    obligations = tuple(frontier["obligations"])
    offset = 0 if cursor is None else cursor["offset"]
    rows = uncached_rows_from(iter(items), offset)
    total = len(items)

    presentation = PageEnvelope(
        reuse_refusal=capture_page_refusal(),
        header={
            "version": "grouped-source-records-2",
            "implementation": implementation,
            "cut_id": cut_id,
            "cut": cut,
            "selection": selection,
            "candidate_universes": universes,
            "finite_universes": finite_universes,
            "authored_judgment_contracts": judgment_contracts,
            "authored_judgment_products": list(request.authored_products),
            "authored_judgment_reads": [
                value.model_dump(mode="python") for value in request.authored_reads
            ],
            "examined_groups": total,
            "obligations": obligations,
            "capability": "complete_private_source_record_groups",
            "unavailable_capabilities": [
                *(
                    ["authored_measurement_and_terminology_judgments"]
                    if set(judgment_contracts) != set(JUDGMENT_KINDS)
                    else []
                ),
                "accepted_knowledge",
            ],
        },
        cursor_basis={
            "version": "grouped-source-records-2",
            "implementation": implementation,
            "selection": digest,
            "read_id": cut["read_id"],
            "cut_id": cut_id,
        },
        cursor_field="continuation",
        position_field="offset",
        include_knowledge=True,
        include_page_complete=True,
    )

    try:
        body = byte_bounded_page(
            rows,
            offset=offset,
            limit=request.limit,
            max_bytes=request.max_bytes
            - len(
                json_bytes(
                    dict(
                        version="source-interpretation-1",
                        kind="grouped_source_record_interpretations",
                        body={},
                    )
                )
            )
            + 2,
            presentation=presentation,
        )
        return answer("grouped_source_record_interpretations", body, request.max_bytes)
    except InvalidContinuation:
        raise
    except ValueError as error:
        raise ReadLimit(str(error), reason="oversized_item") from error
