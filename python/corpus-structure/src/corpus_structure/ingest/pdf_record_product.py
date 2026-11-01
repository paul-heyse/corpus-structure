"""Native publication metadata without constructing a canonical document envelope."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from corpus_structure.core.method import PdfRecordPublicationDraft

from .pdf_candidate_source import as_candidate_source
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
        from .pdf import native_conversion_health

        health = native_conversion_health(
            nodes,
            conversion.conversion_status,
            conversion.errors,
            (*conversion.formula_outcomes, *extra_outcomes),
        )
    captured = dict(metadata or {})
    if "inline_candidate_pages" not in captured:
        candidates = as_candidate_source(conversion.inline_candidates)
        captured["inline_candidate_pages"] = (
            candidates.encoded(number) for number in candidates.page_nos
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
