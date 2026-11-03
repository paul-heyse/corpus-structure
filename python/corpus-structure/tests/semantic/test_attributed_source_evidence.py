"""Independent positions and custody variants for ADR-0051's private boundary."""

import json
from copy import deepcopy
from dataclasses import replace
from typing import Any

import pytest

from corpus_structure.semantic.record_contracts import (
    anchor_identity,
    bind_record_candidates,
    evidence_set_identity,
    interpretation_identity,
    record_identity,
)
from corpus_structure.semantic.source_contexts import (
    ContextRefused,
    NativeSourceContext,
    PreparedNativeSources,
    SourceSlice,
    SyntheticText,
)

from .test_record_contracts import PIN, release_inputs, table_record
from .test_source_contexts import source

BINDING = dict(version=2, relationship="selected_context", policy="attributed-selected-source-2")


def replace_note(record, anchor):
    previous = next(a for a in record["anchors"] if a["pointer"] == "#/texts/4")
    anchor["anchor_id"] = anchor_identity(anchor)
    record["anchors"] = tuple(anchor if a is previous else a for a in record["anchors"])
    sets = []
    replacements = {}
    for evidence in record["evidence_sets"]:
        changed: dict[str, Any] = dict(
            evidence,
            anchors=tuple(
                anchor["anchor_id"] if key == previous["anchor_id"] else key
                for key in evidence["anchors"]
            ),
        )
        changed["set_id"] = evidence_set_identity(changed)
        replacements[evidence["set_id"]] = changed["set_id"]
        sets.append(changed)
    record["evidence_sets"] = tuple(sets)
    for field in record["fields"]:
        field["evidence_sets"] = tuple(replacements[key] for key in field["evidence_sets"])
    record["record_id"] = record_identity(release_inputs()[2].release_id, record)
    record["interpretation_id"] = interpretation_identity(record)
    return record


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


def captured_note():
    record, contexts = table_record()
    note = deepcopy(next(a for a in record["anchors"] if a["pointer"] == "#/texts/4"))
    provider = dict(
        occurrence_id="provider:7",
        kind="text",
        precision="coarse",
        address_space="submitted_pixels",
        text="hypothetical",
        region=dict(precision="coarse", left=0, right=80),
    )
    address = dict(
        selected_occurrence_id="selected:4",
        task_id=12,
        product_key="recognition",
        content_digest="e" * 64,
        occurrence_id="provider:7",
        relation_id="decision:4",
        endpoint_role="evidence",
        relation_kind="decision",
        relation_outcome="selected",
        provider_occurrence_json=json.dumps(provider),
        observation_json=json.dumps(
            dict(image=dict(precision="unknown"), raw_response_digest="f" * 64)
        ),
    )
    note.update(
        binding=dict(BINDING, relationship="primary"),
        space="captured_recognition",
        recognition=address,
    )
    replace_note(record, note)
    coordinate = dict(
        pin=PIN,
        space="captured_recognition",
        pointer="#/texts/4",
        recognition=address,
        text="hypothetical",
    )
    return record, (*contexts, coordinate), provider


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
