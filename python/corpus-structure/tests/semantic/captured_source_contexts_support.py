"""Shared controlled inputs and builders for captured source contexts support."""

import json
from typing import Any

from corpus_structure.semantic.source_contexts import (
    CapturedRecognitionSlice,
    NativeSourceContext,
    PreparedCapturedCoordinate,
    PreparedNativeSources,
    SourceSlice,
    SyntheticText,
)
from semantic.attributed_source_evidence_support import captured_note
from semantic.record_contracts_support import release_inputs
from semantic.source_contexts_support import source


def coordinate(primary, *, text="2 bar 2 h", digest="e" * 64, disposition="selected"):
    _, coordinates, _ = captured_note()
    row: dict[str, Any] = dict(coordinates[-1])
    row["pin"] = dict(
        source=primary.unit_ref,
        native_product_task_id=primary.native_product.task_id,
        product_key=primary.native_product.product_key,
        product_digest=primary.native_product.content_digest,
        projection_digest=primary.projection_digest,
        recipe_digest=primary.recipe_digest,
        source_view_id=primary.source_view_id,
    )
    row["pointer"] = "#/texts/1"
    row["text"] = text
    address = dict(
        row["recognition"],
        selected_occurrence_id="selected:1",
        content_digest=digest,
        relation_outcome=disposition,
        endpoint_role="alternative" if disposition == "retained_alternative" else "evidence",
    )
    provider = dict(json.loads(address["provider_occurrence_json"]), text=text)
    address["provider_occurrence_json"] = json.dumps(provider)
    row["recognition"] = address
    return row


def prepared_context(*, text="2 bar 2 h", with_native=True):
    primary = source(1, "native")
    captured = PreparedCapturedCoordinate.from_coordinate(
        primary, release_inputs()[2], coordinate(primary, text=text)
    )
    prepared = PreparedNativeSources((primary,), captured=(captured,))
    pieces = (
        (SourceSlice(1, 0, 6), SyntheticText("\n", "serialized boundary")) if with_native else ()
    )
    context = NativeSourceContext(
        primary,
        (),
        (*pieces, CapturedRecognitionSlice(captured.coordinate_id, 0, len(text))),
        "measurement alternatives",
        "captured-role-2",
        "bounded supplied inputs",
        version=2,
        preparation=prepared,
    )
    return context, captured
