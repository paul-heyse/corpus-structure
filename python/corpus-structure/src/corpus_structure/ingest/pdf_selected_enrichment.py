"""One selected-source enrichment kernel; ownership and publication stay with the caller."""

from __future__ import annotations

import dataclasses
from typing import Any

from .pdf import CellEnrichment
from .pdf_candidate_geometry import candidate_page_status
from .pdf_candidate_source import as_candidate_source
from .pdf_enrichment import PdfEnrichmentRequest
from .pdf_hierarchy import load_snapshot, native_nodes
from .pdf_methods import _conversion_from_product, _member_order
from .pdf_record_product import native_publication_draft


def enrich_selected_pdf(
    product, parent, specs, options, recipe_bytes, candidate_source, worker, *, check_active
):
    conversion = _conversion_from_product(product, recipe_bytes, candidate_source)
    document = load_snapshot(conversion.native)
    nodes = native_nodes(document)
    # Selected analysis units and their explicit ancestor context share one original.
    specs = list(dict.fromkeys(specs))
    if not specs or any(
        pointer not in nodes or membership not in {"direct", "descendants"}
        for pointer, membership in specs
    ):
        raise ValueError("PDF enrichment requires exact retained section selections")
    selected_scopes = set(specs)
    for section, _ in tuple(specs):
        current = nodes[section]
        while current.parent is not None:
            pointer = current.parent.cref
            current = nodes[pointer]
            if (
                str(current.label) in {"section", "chapter"}
                and (pointer, "direct") not in selected_scopes
            ):
                specs.append((pointer, "direct"))
                selected_scopes.add((pointer, "direct"))
    section_refs = frozenset(
        pointer for pointer, node in nodes.items() if str(node.label) in {"section", "chapter"}
    )
    scope_members = {scope: tuple(_member_order(nodes, section_refs, *scope)) for scope in specs}
    required_pages_by_scope = {
        (section, membership): {
            prov.page_no
            for pointer in scope_members[(section, membership)]
            if str(nodes[pointer].label) in {"text", "list_item", "caption", "footnote"}
            and not nodes[pointer].children
            and nodes[pointer].text.strip()
            for prov in getattr(nodes[pointer], "prov", ())
        }
        for section, membership in specs
    }
    selected = set().union(*scope_members.values())
    computed = worker.enrich(
        PdfEnrichmentRequest(
            conversion,
            product.original,
            frozenset(selected),
            options.cell_math_pattern,
            options.cell_prose_pattern,
            options.crop_padding_points,
        ),
        check_active=check_active,
    )
    conversion = dataclasses.replace(
        conversion,
        packages=computed.packages,
        runtime=computed.runtime,
        effective_options=computed.effective_options,
        inline_candidates=computed.candidate_pages,
    )
    derived = computed.native
    document = load_snapshot(derived)
    nodes = native_nodes(document)
    reports = list(computed.cell_reports)
    enriched = CellEnrichment(
        conversion.native.digest, derived, computed.outcomes, computed.mappings
    )
    draft = native_publication_draft(
        conversion,
        product_key="math-enriched",
        original=product.original,
        schema_bytes=product.schema_bytes,
        native=derived,
        recipe_bytes=recipe_bytes,
        extra_outcomes=enriched.outcomes,
    )
    payload: dict[str, Any] = {"health": dict(draft.health)}
    payload["cell_reports"] = reports
    payload["inline_alignment_reports"] = [row.to_wire() for row in computed.alignment_reports]
    # Whole-book native content is retained; only the declared rows close recognition.
    payload["health"].update(
        inline_coverage="unknown",
        cell_coverage="unknown",
        candidate_policy="native-font-token-vector-ocr-word-v3",
        cells_policy="all-nonempty-selected-cells-v1",
    )
    nodes = native_nodes(document)
    outcomes = {row["pointer"]: row["outcome"] for row in payload["health"]["formula_outcomes"]}

    candidate_pages = candidate_page_status(
        as_candidate_source(conversion.inline_candidates),
        set().union(*required_pages_by_scope.values()),
    )
    reports_by_table = {}
    for report in reports:
        reports_by_table.setdefault(report["table_pointer"], []).append(report)
    alignment_pointers = frozenset(
        pointer for report in computed.alignment_reports for pointer in report.item_pointers
    )
    coverage = []
    for section, membership in specs:
        pointers = _member_order(nodes, section_refs, section, membership)
        scope_pointers = set(pointers)
        formula_refs = [pointer for pointer in pointers if str(nodes[pointer].label) == "formula"]
        inline_refs = [
            pointer
            for pointer in formula_refs
            if nodes[pointer].parent is not None
            and str(nodes[nodes[pointer].parent.cref].label) == "inline"
        ]
        display_refs = [
            pointer
            for pointer in formula_refs
            if nodes[pointer].parent is None
            or str(nodes[nodes[pointer].parent.cref].label) not in {"inline", "table"}
        ]
        cell_rows = [row for pointer in pointers for row in reports_by_table.get(pointer, ())]
        required_pages = required_pages_by_scope[(section, membership)]
        discovery_complete = all(
            number in candidate_pages
            and candidate_pages[number].usable_words
            and candidate_pages[number].has_vectors
            for number in required_pages
        )
        states = {
            "display": all(outcomes.get(pointer) == "succeeded" for pointer in display_refs),
            "inline": discovery_complete
            and scope_pointers.isdisjoint(alignment_pointers)
            and all(outcomes.get(pointer) == "succeeded" for pointer in inline_refs),
            "cell": all(
                row["classification"] == "prose" or row["outcome"] == "succeeded"
                for row in cell_rows
            ),
        }
        policies = {
            "display": "detected-native-display-v1",
            "inline": "native-font-token-vector-ocr-word-v3",
            "cell": "all-nonempty-selected-cells-v1",
        }
        coverage.extend(
            dict(
                section_pointer=section,
                membership=membership,
                universe=universe,
                outcome="complete"
                if complete and conversion.conversion_status == "success"
                else "partial",
                policy=policies[universe],
            )
            for universe, complete in states.items()
        )
    payload["recognition_coverage"] = coverage
    draft = dataclasses.replace(
        draft,
        health=payload["health"],
        metadata={
            **draft.metadata,
            "recognition_coverage": coverage,
            "derivation_mappings": enriched.mappings,
            "cell_reports": reports,
            "inline_alignment_reports": payload["inline_alignment_reports"],
        },
        companions={"input": ({**parent.values(), "role": "structural"},)},
    )
    return draft
