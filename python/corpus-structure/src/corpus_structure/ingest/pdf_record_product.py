"""Native publication metadata without constructing a canonical document envelope."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from corpus_structure.core.method import PdfRecordPublicationDraft

from .pdf_hierarchy import load_snapshot, native_nodes


def native_publication_draft(
    conversion: Any,
    *,
    product_key: str,
    original: bytes,
    schema_bytes: bytes,
    native: Any = None,
    recipe_bytes: bytes | None = None,
    extra_outcomes: Iterable[Any] = (),
    health: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> PdfRecordPublicationDraft:
    selected = conversion.native if native is None else native
    document = load_snapshot(selected)
    nodes = native_nodes(document)
    if health is None:
        outcomes = {}
        for row in (*conversion.formula_outcomes, *extra_outcomes):
            if row.item_ref not in nodes or str(nodes[row.item_ref].label) != "formula":
                raise ValueError("formula health names missing native occurrence")
            if row.item_ref in outcomes:
                raise ValueError("duplicate native formula outcome")
            outcomes[row.item_ref] = row
        for pointer, node in nodes.items():
            if str(node.label) == "formula" and pointer not in outcomes:
                from .pdf_health import FormulaOutcome

                outcomes[pointer] = FormulaOutcome(
                    pointer, "unknown", "no attributable inference outcome"
                )
        display = [
            p
            for p, n in nodes.items()
            if str(n.label) == "formula"
            and (n.parent is None or str(nodes[n.parent.cref].label) not in {"table", "inline"})
        ]
        health = {
            "conversion": conversion.conversion_status,
            "display_coverage": "complete"
            if conversion.conversion_status == "success"
            and all(outcomes[p].outcome == "succeeded" for p in display)
            else "partial",
            "inline_coverage": "unknown",
            "cell_coverage": "unknown",
            "issues": list(conversion.errors),
            "formula_outcomes": [
                dict(
                    pointer=r.item_ref, outcome=r.outcome, **({"error": r.error} if r.error else {})
                )
                for r in outcomes.values()
            ],
        }
    captured = dict(metadata or {})
    captured.setdefault(
        "inline_candidate_pages", (p.to_wire() for p in conversion.inline_candidates)
    )
    if conversion.packages or conversion.runtime or conversion.effective_options != b"{}":
        captured.setdefault(
            "runtime_report",
            {
                "packages": [dict(name=n, version=v) for n, v in conversion.packages],
                "bindings": [dict(name=n, value=v) for n, v in conversion.runtime],
                "effective_options": conversion.effective_options.decode(),
                **(
                    {"confidence": conversion.confidence.decode()}
                    if conversion.confidence != b"{}"
                    else {}
                ),
            },
        )
    return PdfRecordPublicationDraft(
        document=document,
        product_key=product_key,
        original=original,
        schema_bytes=schema_bytes,
        recipe_bytes=recipe_bytes or conversion.recipe,
        health=health,
        metadata=captured,
        kind="native",
    )


def native_occurrence_rows(document):
    """Native occurrence projection shares the integration pointer/cell vocabulary.

    The content graph remains identified separately. This derives its query index,
    not a replacement native value or a source interpretation.
    """
    from types import SimpleNamespace

    from docling_core.types.doc import DoclingDocument

    from .pdf_reconciliation import _iter_selected_occurrences

    if isinstance(document, Mapping):
        from copy import deepcopy

        projected = DoclingDocument.model_validate(deepcopy(document))
    else:
        projected = document
    nodes = native_nodes(projected)
    origins = {id(node): SimpleNamespace(input_index=0) for node in nodes.values()}
    for row in _iter_selected_occurrences(projected, origins):
        # Text remains in the native field/stream, not duplicated into this
        # bounded address index. Its optional cached text is deliberately absent.
        row = {key: value for key, value in row.items() if key != "text"}
        if row["address_space"] == "selected_item":
            row = {**row, "address_space": "native_item"}
        yield row
    for pointer, node in nodes.items():
        for index, prov in enumerate(getattr(node, "prov", ())):
            box = prov.bbox
            yield {
                "occurrence_id": f"{pointer}/prov/{index}",
                "pointer": pointer,
                "kind": "region",
                "address_space": "pdf_points",
                "precision": "item",
                "region_index": index,
                "page_no": prov.page_no,
                "region": {
                    "address_space": "pdf_points",
                    "precision": "item",
                    "normalization": "none",
                    "left": box.l,
                    "top": box.t,
                    "right": box.r,
                    "bottom": box.b,
                    "origin": "top_left" if box.coord_origin.value == "TOPLEFT" else "bottom_left",
                },
            }
