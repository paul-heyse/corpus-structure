"""Supplied captured coordinates: pure mapping only; native custody is rechecked separately."""

import json
from dataclasses import replace

import pytest

from corpus_structure.methods.gliner import (
    GlinerPreparation,
    GlinerRefused,
    GlinerReport,
    map_literal,
)
from corpus_structure.methods.record_assembly import assemble_native_records, native_table_groups
from corpus_structure.semantic.proposals import NativeFrameSource
from corpus_structure.semantic.source_contexts import (
    CapturedRecognitionInterval,
    CapturedRecognitionSlice,
    CapturedSpanEvidence,
    ContextRefused,
    NativeSpanEvidence,
    PreparedCapturedCoordinate,
    PreparedNativeSources,
)
from semantic.captured_source_contexts_support import (
    coordinate as coordinate,
)
from semantic.captured_source_contexts_support import (
    prepared_context as prepared_context,
)
from semantic.record_contracts_support import release_inputs


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
    assert isinstance(context.primary, NativeFrameSource)
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
