"""Independent positions and custody variants for ADR-0051's private boundary."""

import json
from copy import deepcopy
from dataclasses import replace

import pytest

from corpus_structure.semantic.record_contracts import (
    bind_record_candidates,
    interpretation_identity,
)
from corpus_structure.semantic.source_contexts import (
    ContextRefused,
    NativeSourceContext,
    PreparedNativeSources,
    SourceSlice,
    SyntheticText,
)
from semantic.attributed_source_evidence_support import (
    BINDING as BINDING,
)
from semantic.attributed_source_evidence_support import (
    captured_note as captured_note,
)
from semantic.attributed_source_evidence_support import (
    replace_note as replace_note,
)
from semantic.record_contracts_support import PIN, release_inputs, table_record
from semantic.source_contexts_support import source


def test_related_selected_context_retains_own_pin_and_primary_occurrence():
    record, contexts = table_record()
    note = deepcopy(next(a for a in record["anchors"] if a["pointer"] == "#/texts/4"))
    note["pin"] = dict(PIN, source="note:separate", source_view_id=8, recipe_digest="d" * 64)
    note["binding"] = BINDING
    replace_note(record, note)
    coordinate = dict(pin=note["pin"], space="native", pointer="#/texts/4", text="hypothetical")
    bound = bind_record_candidates(
        release_inputs()[2],
        source=PIN["source"],
        records=(record,),
        coordinate_texts=(*contexts, coordinate),
    )[0].model_dump(mode="python")
    assert bound["pin"] == PIN
    assert bound["occurrence_anchors"] == record["occurrence_anchors"]
    assert (
        next(a for a in bound["anchors"] if a["pointer"] == "#/texts/4")["pin"]["source_view_id"]
        == 8
    )
    forged = deepcopy(record)
    forged["occurrence_anchors"] = (note["anchor_id"],)
    with pytest.raises(ValueError, match="occurrence anchors"):
        bind_record_candidates(
            release_inputs()[2],
            source=PIN["source"],
            records=(forged,),
            coordinate_texts=(*contexts, coordinate),
        )


def test_captured_characters_do_not_promote_provider_geometry_or_alias_canonical_text():
    record, contexts, provider = captured_note()
    bound = bind_record_candidates(
        release_inputs()[2], source=PIN["source"], records=(record,), coordinate_texts=contexts
    )[0]
    note = next(
        a
        for a in bound.model_dump(mode="python")["anchors"]
        if a["space"] == "captured_recognition"
    )
    assert (note["start"], note["end"], note["precision"]) == (0, 12, "exact")
    assert json.loads(note["recognition"]["provider_occurrence_json"]) == provider
    with pytest.raises(ValueError, match="lacks pinned coordinate"):
        bind_record_candidates(
            release_inputs()[2],
            source=PIN["source"],
            records=(record,),
            coordinate_texts=contexts[:-1],
        )
    note["space"] = "recognized_text"
    with pytest.raises(ValueError, match="reinterpret"):
        replace_note(record, note)
        bind_record_candidates(
            release_inputs()[2], source=PIN["source"], records=(record,), coordinate_texts=contexts
        )


def prepared_context(pieces):
    primary = source(1, "2 bar")
    prepared = PreparedNativeSources((primary,))
    return NativeSourceContext(
        primary, (), pieces, "measurement", "roles-2", "bounded", version=2, preparation=prepared
    )


def test_whitespace_reading_preserves_original_pieces_and_gap_diagnostics():
    result = prepared_context(
        (SourceSlice(1, 0, 1), SyntheticText("\n ", "serialized gap"), SourceSlice(1, 2, 5))
    )
    reading = result.read_span(
        0, 6, prepared=release_inputs()[2], policy="synthetic-whitespace-1", literal="2\n bar"
    )
    assert reading.original_pieces == ("2", "bar")
    assert [(piece.start, piece.end) for piece in reading.pieces] == [(0, 1), (2, 5)]
    assert [(gap.model_start, gap.model_end) for gap in reading.gaps] == [(1, 3)]
    with pytest.raises(ContextRefused, match="synthetic"):
        result.map_span(0, 6, allow_multiple=True)
    with pytest.raises(ContextRefused, match="genuine"):
        result.read_span(1, 3, prepared=release_inputs()[2], policy="synthetic-whitespace-1")
    punctuation = prepared_context(
        (SourceSlice(1, 0, 1), SyntheticText(":", "label"), SourceSlice(1, 2, 5))
    )
    with pytest.raises(ContextRefused, match="punctuation"):
        punctuation.read_span(0, 5, prepared=release_inputs()[2], policy="synthetic-whitespace-1")


def test_many_contexts_reuse_one_prepared_index_without_reparsing(monkeypatch):
    import corpus_structure.semantic.source_contexts as owner

    primary = source(1, "2 bar")
    prepared = PreparedNativeSources((primary,))

    def refuse(_):
        raise AssertionError("source was prepared again")

    monkeypatch.setattr(owner, "_source_context", refuse)
    for start, end in ((0, 1), (2, 5)):
        result = NativeSourceContext(
            primary,
            (),
            (SourceSlice(1, start, end),),
            "measurement",
            "roles-2",
            "bounded",
            version=2,
            preparation=prepared,
        )
        assert result.map_span(0, end - start)[0].start == start
    with pytest.raises(ContextRefused, match="exact invocation"):
        NativeSourceContext(
            replace(primary, recipe_digest="d" * 64),
            (),
            (SourceSlice(1, 0, 1),),
            "measurement",
            "roles-2",
            "bounded",
            version=2,
            preparation=prepared,
        )


def test_captured_recognition_cannot_replace_the_primary_occurrence_recipe():
    record, contexts, _ = captured_note()
    record["occurrence_anchors"] = (
        next(a["anchor_id"] for a in record["anchors"] if a["space"] == "captured_recognition"),
    )
    with pytest.raises(ValueError, match="occurrence anchors"):
        bind_record_candidates(
            release_inputs()[2], source=PIN["source"], records=(record,), coordinate_texts=contexts
        )


def test_upstream_alternative_keeps_captured_literal_candidate_usage():
    record, contexts, _ = captured_note()
    note = deepcopy(next(a for a in record["anchors"] if a["space"] == "captured_recognition"))
    note["recognition"].update(endpoint_role="alternative", relation_outcome="retained_alternative")
    replace_note(record, note)
    record["standing"] = "candidate"
    record["interpretation_id"] = interpretation_identity(record)
    coordinates = (*contexts[:-1], dict(contexts[-1], recognition=note["recognition"]))
    bound = bind_record_candidates(
        release_inputs()[2], source=PIN["source"], records=(record,), coordinate_texts=coordinates
    )[0]
    assert (
        next(
            a
            for a in bound.model_dump(mode="python")["anchors"]
            if a["space"] == "captured_recognition"
        )["recognition"]["endpoint_role"]
        == "alternative"
    )
