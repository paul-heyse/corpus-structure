"""Supplied captured coordinates: pure mapping only; native custody is rechecked separately."""

import json
from dataclasses import replace
from typing import Any

import pytest

from corpus_structure.methods.gliner import (
    GlinerPreparation,
    GlinerRefused,
    GlinerReport,
    map_literal,
)
from corpus_structure.methods.record_assembly import assemble_native_records, native_table_groups
from corpus_structure.semantic.source_contexts import (
    CapturedRecognitionInterval,
    CapturedRecognitionSlice,
    CapturedSpanEvidence,
    ContextRefused,
    NativeSourceContext,
    NativeSpanEvidence,
    PreparedCapturedCoordinate,
    PreparedNativeSources,
    SourceSlice,
    SyntheticText,
)

from .test_attributed_source_evidence import captured_note
from .test_record_contracts import release_inputs
from .test_source_contexts import source


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


def test_captured_coordinates_never_replace_canonical_text_or_provider_geometry():
    context, captured = prepared_context()
    assert context.primary.text == "native"
    assert context.text == "native\n2 bar 2 h"
    assert isinstance(context.intervals[-1], CapturedRecognitionInterval)
    (native,) = context.map_span(0, 6)
    assert isinstance(native, NativeSpanEvidence)
    (span,) = context.map_span(7, 12, literal="2 bar")
    assert isinstance(span, CapturedSpanEvidence)
    assert (span.start, span.end, span.quote) == (0, 5, "2 bar")
    assert not hasattr(span, "locator") and not hasattr(span, "source_field")
    anchor = span.record_anchor(relationship="primary")
    assert anchor["space"] == "captured_recognition"
    assert (anchor["start"], anchor["end"], anchor["precision"]) == (0, 5, "exact")
    assert json.loads(anchor["recognition"]["provider_occurrence_json"])["precision"] == "coarse"
    assert "start" not in json.loads(anchor["recognition"]["provider_occurrence_json"])
    assert captured.text == "2 bar 2 h"
    (second,) = context.map_span(13, 14, literal="2")
    assert isinstance(second, CapturedSpanEvidence) and (second.start, second.end) == (6, 7)
    release_inputs()[2].validate_python("RecordAnchor", anchor)


def test_whitespace_reading_retains_explicit_native_and_captured_piece_variants():
    context, _ = prepared_context(text="2 bar")
    reading = context.read_span(
        0, len(context.text), prepared=release_inputs()[2], policy="synthetic-whitespace-1"
    )
    assert reading.original_pieces == ("native", "2 bar")
    assert isinstance(reading.pieces[0], NativeSpanEvidence)
    assert isinstance(reading.pieces[1], CapturedSpanEvidence)
    assert [(gap.model_start, gap.model_end) for gap in reading.gaps] == [(6, 7)]
    with pytest.raises(ContextRefused, match="synthetic"):
        context.map_span(0, len(context.text), allow_multiple=True)


def test_considered_equal_text_alternative_and_source_substitution_invalidate_context():
    context, captured = prepared_context(with_native=False)
    alternative = PreparedCapturedCoordinate.from_coordinate(
        context.primary,
        release_inputs()[2],
        coordinate(context.primary, digest="f" * 64, disposition="retained_alternative"),
    )
    assert alternative.coordinate_id != captured.coordinate_id
    preparation = PreparedNativeSources((context.primary,), captured=(captured, alternative))
    considered = replace(
        context, preparation=preparation, captured_dependencies=(alternative.coordinate_id,)
    )
    assert (
        considered.text == context.text
        and considered.dependency_digest != context.dependency_digest
    )
    selected = replace(
        context,
        preparation=preparation,
        pieces=(CapturedRecognitionSlice(alternative.coordinate_id, 0, 9),),
    )
    assert selected.text == context.text and selected.dependency_digest != context.dependency_digest
    with pytest.raises(ContextRefused, match="absent"):
        replace(context, captured_dependencies=(alternative.coordinate_id,))
    with pytest.raises(ContextRefused, match="exact invocation"):
        PreparedNativeSources(
            (replace(context.primary, recipe_digest="d" * 64),), captured=(captured,)
        )


def test_captured_preparation_and_context_bounds_refuse_without_truncation():
    context, captured = prepared_context(with_native=False)
    other = PreparedCapturedCoordinate.from_coordinate(
        context.primary, release_inputs()[2], coordinate(context.primary, digest="f" * 64)
    )
    with pytest.raises(ContextRefused, match="bounded distinct"):
        PreparedNativeSources((context.primary,), captured=(captured, other), max_captured=1)
    with pytest.raises(ContextRefused, match="bounded distinct"):
        PreparedNativeSources((context.primary,), captured=(captured,), max_captured_chars=3)
    with pytest.raises(ContextRefused, match="unbounded"):
        replace(context, max_sources=1)
    with pytest.raises(ContextRefused, match="outside"):
        replace(context, pieces=(CapturedRecognitionSlice(captured.coordinate_id, 0, 10),))
    with pytest.raises(ContextRefused, match="absent"):
        replace(context, pieces=(CapturedRecognitionSlice("0" * 64, 0, 1),))
    with pytest.raises(ContextRefused, match="unsupported"):
        replace(context, version=1)
    invalid = coordinate(context.primary)
    invalid["text"] = "canonical substitution"
    with pytest.raises(ContextRefused, match="provider occurrence"):
        PreparedCapturedCoordinate.from_coordinate(context.primary, release_inputs()[2], invalid)


def test_canonical_producer_and_assembler_explicitly_refuse_captured_variants():
    context, _ = prepared_context(with_native=False)
    report = GlinerReport(
        "context",
        context.dependency_digest,
        "compute",
        "profile",
        "pack",
        GlinerPreparation(context.text, "", 4, 5, len(context.text.encode())),
        "{}",
        "{}",
        0.0,
        False,
    )
    with pytest.raises(GlinerRefused, match="captured recognition"):
        map_literal(report, context, dict(start=0, end=5, text="2 bar"))
    with pytest.raises(GlinerRefused, match="captured recognition"):
        assemble_native_records(
            release_inputs()[2],
            context,
            contract="TableRecordFields",
            occurrence_roles=("table",),
            policy_version="unadopted",
            groups=(),
        )
    with pytest.raises(GlinerRefused, match="captured recognition"):
        native_table_groups(
            context, table_pointer="#/tables/0", cells=(), row_paths={}, header_paths={}
        )
