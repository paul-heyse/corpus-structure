"""Deterministic structural reports and dossier pages over acquired typed support."""

from collections import defaultdict
from typing import cast

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
    from .data_product_reference import read_semantic_reference
    from .live_reference_resolution import require_selected_output_reference
    from .structural_products import (
        DeclaredClauseReport,
        DeclaredDefinitionApplicabilityReport,
        DeclaredDossierReport,
        DeclaredNamedDefinitionComponentsReport,
    )

    condition = root.structural.condition_qualification
    if condition is not None:
        attachment = read_semantic_reference(condition.attachment)
        body = require_selected_output_reference(
            scope, selected, attachment, path="/condition_qualification/attachment"
        )
        identifier = body.get("contribution_id") if isinstance(body, dict) else None
        if (
            not isinstance(body, dict)
            or body.get("candidate_type") != "contribution"
            or body.get("semantic_type") != "structural.predicate_qualification"
            or not isinstance(identifier, str)
            or attachment.member_id != "contribution:" + identifier
        ):
            raise ValueError("selected condition attachment does not resolve its qualification")
    if root.nominal == "urn:corpus:structural:DeclaredNamedDefinitionComponentsReport":
        for recorded in cast(DeclaredNamedDefinitionComponentsReport, root.structural).witnesses:
            witness = recorded.basis
            prefix = "/witnesses/*/basis/"
            require_selected_output_reference(
                scope,
                selected,
                read_semantic_reference(witness.annotation_product),
                path=prefix + "annotation_product",
                metadata_only=True,
            )
            for field, values in (
                ("primary_match", (witness.primary_match,) if witness.primary_match else ()),
                ("primary_scope/*", witness.primary_scope),
            ):
                for value in values:
                    require_selected_output_reference(
                        scope,
                        selected,
                        read_semantic_reference(value),
                        path=prefix + field,
                    )
    if isinstance(root.structural, DeclaredDefinitionApplicabilityReport):
        applicability = root.structural
        relationship = require_selected_output_reference(
            scope,
            selected,
            read_semantic_reference(applicability.relationship_input),
            path="/relationship_input",
            metadata_only=True,
        )
        for reading in applicability.definition.readings:
            link = reading.link_ref
            if (link.product_id, link.kind_contract, link.member_id) != (
                relationship.product_id,
                relationship.kind_contract,
                relationship.member_id,
            ):
                raise ValueError(
                    "selected applicability link differs from its original relationship input"
                )
    if isinstance(root.structural, DeclaredDossierReport):
        dossier = root.structural
        components = require_selected_output_reference(
            scope,
            selected,
            read_semantic_reference(dossier.components_input),
            path="/components_input",
            metadata_only=True,
        )
        root_component = dossier.dossier.root_component
        if (root_component.product_id, root_component.kind_contract, root_component.member_id) != (
            components.product_id,
            components.kind_contract,
            components.member_id,
        ):
            raise ValueError("selected dossier root differs from its original components input")
    clause = root.structural.clause_classification
    if clause is not None:
        clause_report = cast(DeclaredClauseReport, root.structural)
        require_selected_output_reference(
            scope,
            selected,
            read_semantic_reference(clause_report.predicate_input),
            path="/predicate_input",
            metadata_only=True,
        )
        from .observations import source_python

        for reading in clause.readings:
            for field, values, semantic_type in (
                (
                    "primary_gliner_functions",
                    reading.primary_gliner_functions,
                    "interpretation.character_gliner_function_v1",
                ),
                (
                    "primary_d1_functions",
                    reading.primary_d1_functions,
                    "interpretation.character_function_v1",
                ),
            ):
                for value in values:
                    reference = read_semantic_reference(value)
                    body = require_selected_output_reference(
                        scope,
                        selected,
                        reference,
                        path="/clause_classification/readings/*/" + field + "/*",
                    )
                    if (
                        not isinstance(body, dict)
                        or body.get("candidate_type") != "contribution"
                        or body.get("semantic_type") != semantic_type
                        or reference.member_id != "contribution:" + body.get("contribution_id", "")
                        or source_python(body["value"]).get("question_key") != "functions"
                    ):
                        raise ValueError(
                            "selected clause function does not resolve its exact answer"
                        )
        # The report constructor ensures that every focus or unprojectable
        # frame is in the inspected inventory.
        for value in clause.inspected_frames:
            reference = read_semantic_reference(value)
            body = require_selected_output_reference(
                scope, selected, reference, path="/clause_classification/inspected_frames/*"
            )
            identifier = body.get("contribution_id") if isinstance(body, dict) else None
            if (
                not isinstance(body, dict)
                or body.get("candidate_type") != "contribution"
                or (body.get("component") or {}).get("kind") != "predicate_frame"
                or not isinstance(identifier, str)
                or reference.member_id != "contribution:" + identifier
            ):
                raise ValueError(
                    "selected clause frame does not resolve its predicate contribution"
                )
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
