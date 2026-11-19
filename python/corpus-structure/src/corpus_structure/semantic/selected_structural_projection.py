"""Deterministic structural reports and dossier pages over acquired typed support."""

from collections import defaultdict

from .data_operation_json import json_bytes, json_loads
from .nonrich_contribution_facets import read_nonrich_root
from .observations import source_python

STRUCTURAL_QUERY_ROOTS = (
    "corpus_structure.semantic.selected_structural_projection.selected_root",
    "corpus_structure.semantic.selected_structural_projection.structural_report",
    "corpus_structure.semantic.selected_structural_projection.selected_contextual",
    "corpus_structure.semantic.selected_structural_projection.dossier_rows",
    "corpus_structure.semantic.selected_structural_projection.producer",
    "corpus_structure.semantic.selected_pages.byte_bounded_page",
    "corpus_structure.semantic.continuation_codec.encode_cursor",
    "corpus_structure.semantic.continuation_codec.decode_rich_cursor",
)


def selected_root(scope, root):
    """An exact selected output, never a body found merely in dependency closure."""
    candidates = tuple(
        selected
        for selected in scope.products(product_id=root.product_id)
        if selected.reference.member_id == root.member_id
        and selected.use_id == root.use_id
        and selected.derivation_id == root.derivation_id
    )
    if not candidates:
        return None
    first = candidates[0]
    if any(item.reference != first.reference or item.body != first.body for item in candidates):
        raise ValueError("selected structural output address has conflicting values")
    return first


def structural_report(scope, selected):
    root = read_nonrich_root(scope.model, selected)
    if root.structural is None:
        raise ValueError("selected output has no current structural report contract")
    return root.structural


def selected_contextual(scope, selected):
    """Validate the captured nominal schema before interpreting its encoded source values."""
    from corpus_structure.semantic.data_operation_wire import validate_wire_schema

    nominal = "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualRetrievalProduct"
    kind = next((kind for kind in scope.model.kinds if kind.semantic_id == nominal), None)
    contract = next(
        (
            identity.key
            for identity in scope.model.identities
            if identity.domain == "kind" and identity.owner == nominal
        ),
        None,
    )
    if (
        selected.nominal != nominal
        or selected.reference.member_id is not None
        or kind is None
        or not kind.complete
        or contract != selected.reference.kind_contract
    ):
        raise ValueError("contextual journey requires its actual captured retrieval whole")
    schema = json_loads(kind.facts).get("json_schema")
    if schema is None:
        raise ValueError("contextual retrieval has no captured nominal schema")
    validate_wire_schema(schema, json_loads(json_bytes(selected.body)))
    return {
        **selected.body,
        **{
            name: source_python(selected.body[name])
            for name in ("inventory", "candidate_list", "relationship_decision")
        },
    }


def producer(selected):
    return dict(
        reference=selected.reference.model_dump(mode="python"),
        context=selected.context.identity_record,
        nominal=selected.nominal,
        operation_id=selected.operation_id,
        use_id=selected.use_id,
        derivation_id=selected.derivation_id,
        output=selected.output,
    )


def dossier_member_page(report, *, population, offset, limit):
    """The display policy chooses from immutable membership; reading changes neither."""
    if report.dossier is None:
        raise ValueError("selected output is not a dossier")
    dossier = report.dossier
    representation = dossier.representation
    members = {member.member_id: member for member in dossier.members}
    keys = (
        tuple(member.member_id for member in dossier.members)
        if population == "membership"
        else representation.selected
    )
    if offset < 0 or offset > len(keys):
        raise ValueError("dossier continuation is outside its immutable population")
    chosen = keys[offset : offset + limit]
    selected = set(chosen)
    passages = {passage.passage_id: passage for passage in report.inputs.passages}
    sources = {source.identity: source for source in report.inputs.sources}
    citations = []
    for key in chosen:
        member = members[key]
        if member.contribution_citations:
            cited = tuple(citation.span for citation in member.contribution_citations)
        else:
            cited = (member.citation,)
        for span in cited:
            source = sources[passages[span.passage_id].source_ref]
            citations.append(
                dict(
                    member_id=key,
                    source=source.model_dump(mode="python"),
                    citation=span.model_dump(mode="python"),
                )
            )
        if member.comparison_binding is not None:
            binding = member.comparison_binding
            citations.append(
                dict(
                    member_id=key,
                    context="opposite_comparison_side",
                    source=binding.opposite_source.model_dump(mode="python"),
                    citation=binding.opposite_citation.model_dump(mode="python"),
                )
            )
    end = offset + len(chosen)
    return dict(
        members=[members[key].model_dump(mode="python", exclude_none=True) for key in chosen],
        citations=citations,
        supported_facets=[
            facet.model_dump(mode="python")
            for facet in dossier.supported_facets
            if facet.member_id in selected
        ],
        next_offset=end if end < len(keys) else None,
        full_member_count=len(members),
        display_member_count=len(representation.selected),
        omitted_member_count=len(representation.omitted),
        missing_facet_count=len(representation.missing_facets),
        mandatory_overflow=representation.mandatory_overflow,
        membership_digest=representation.membership_digest,
        facet_digest=representation.facet_digest,
        policy=representation.policy,
        product_id=report.product_id,
    )


def dossier_rows(report, *, population, provenance):
    complete = dossier_member_page(
        report, population=population, offset=0, limit=len(report.dossier.members)
    )
    citations, facets = defaultdict(list), defaultdict(list)
    for citation in complete["citations"]:
        citations[citation["member_id"]].append(citation)
    for ordinal, facet in enumerate(complete["supported_facets"]):
        facets[facet["member_id"]].append(dict(ordinal=ordinal, value=facet))
    items = [
        dict(
            members=[member],
            citations=citations[member["member_id"]],
            supported_facets=facets[member["member_id"]],
        )
        for member in complete["members"]
    ]
    metadata = {
        name: value
        for name, value in complete.items()
        if name not in {"members", "citations", "supported_facets", "next_offset"}
    }
    metadata["producer"] = provenance
    return items, metadata
