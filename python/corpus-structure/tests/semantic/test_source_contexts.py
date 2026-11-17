"""Independent source and model positions for the bounded private context operation."""

import json
from dataclasses import replace
from typing import Literal, cast

import pytest

from corpus_structure.semantic.declared_proposal_frames import (
    DeclaredProposalFrame,
    DeclaredProposalSource,
)
from corpus_structure.semantic.declared_record_sources import DeclaredSourcePin, DeclaredSourceSlice
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.proposals import (
    ProposalSentence,
    native_address,
)
from corpus_structure.semantic.source_contexts import (
    ContextRefused,
    ContextRelationship,
    ContextRetrieval,
    NativeSpanEvidence,
    PreparedNativeSources,
    RelatedNativeSource,
    RetrievalOutcome,
    SourceInterval,
    SyntheticInterval,
    SyntheticText,
)
from semantic.source_contexts_support import (
    A,
    B,
    C,
)
from semantic.source_contexts_support import (
    context as context,
)
from semantic.source_contexts_support import (
    source as source,
)


def retrieval(
    *, candidates=(), selected=(), excluded=(), outcome=RetrievalOutcome.NO_MATCH, **kwargs
):
    return ContextRetrieval(
        ContextRelationship.DECLARATION,
        "population missing locally",
        "section:population",
        "d" * 64,
        candidates,
        selected,
        excluded,
        outcome,
        "bounded lookup complete",
        **kwargs,
    )


def test_neighbor_and_declaration_have_distinct_sources_and_repeated_strings_do_not_alias():
    primary = source(1, "X X", membership="descendants")
    neighbor = source(2, "X X")
    declaration = source(3, "X is population")
    result = context(
        primary,
        (DeclaredSourceSlice(A, 2, 3), DeclaredSourceSlice(B, 0, 1), DeclaredSourceSlice(C, 0, 1)),
        related=(
            RelatedNativeSource(
                neighbor, ContextRelationship.NEIGHBOR, "estimand in previous paragraph"
            ),
            RelatedNativeSource(
                declaration, ContextRelationship.DECLARATION, "population declaration"
            ),
        ),
    )
    assert result.text == "XXX"
    anchors = result.map_span(0, 3, allow_multiple=True)
    actual = []
    for row in anchors:
        assert isinstance(row.source, DeclaredSourcePin)
        actual.append((row.source.source_key, row.start, row.end, row.quote))
    assert actual == [
        (A, 2, 3, "X"),
        (B, 0, 1, "X"),
        (C, 0, 1, "X"),
    ]
    source_ids = []
    for row in anchors:
        assert isinstance(row, NativeSpanEvidence)
        source_ids.append(json.loads(row.locator[4:])["source_product"])
    assert source_ids == ["fixture:context:1", "fixture:context:2", "fixture:context:3"]
    assert isinstance(anchors[1], NativeSpanEvidence)
    address = json.loads(anchors[1].item_locator[4:])
    assert address["pointer"] == "#/texts/2"
    assert address["source_product"] == "fixture:context:2"
    assert address["document"] == "document:context"


def test_repeated_header_inclusions_point_to_one_native_cell_occurrence():
    primary = source(
        1,
        "Value\n4\n5",
        pieces=[
            dict(
                kind="native_text",
                item_ref="#/tables/0",
                source_field="cell_text",
                cell_index=0,
                start=0,
                end=5,
            ),
            dict(kind="synthetic_separator", start=5, end=6),
            dict(
                kind="native_text",
                item_ref="#/tables/0",
                source_field="cell_text",
                cell_index=1,
                start=6,
                end=7,
            ),
            dict(kind="synthetic_separator", start=7, end=8),
            dict(
                kind="native_text",
                item_ref="#/tables/0",
                source_field="cell_text",
                cell_index=2,
                start=8,
                end=9,
            ),
        ],
    )
    result = context(
        primary,
        (
            DeclaredSourceSlice(A, 0, 5),
            SyntheticText(":", "inserted header label delimiter"),
            DeclaredSourceSlice(A, 6, 7),
            SyntheticText("\n", "serialized row boundary"),
            DeclaredSourceSlice(A, 0, 5),
            SyntheticText(":", "inserted header label delimiter"),
            DeclaredSourceSlice(A, 8, 9),
        ),
    )
    assert result.text == "Value:4\nValue:5"
    (first,) = result.map_span(0, 5)
    (second,) = result.map_span(8, 13)
    assert isinstance(first, NativeSpanEvidence)
    assert isinstance(second, NativeSpanEvidence)
    assert (first.start, first.end, first.cell_index, first.source_field) == (0, 5, 0, "cell_text")
    assert first.locator == second.locator
    assert [
        (row.source_start, row.source_end)
        for row in result.intervals
        if isinstance(row, SourceInterval)
    ] == [
        (0, 5),
        (6, 7),
        (0, 5),
        (8, 9),
    ]


def test_original_projection_separator_is_synthetic_and_span_crossing_it_refuses():
    primary = source(
        1,
        "X\nX",
        pieces=[
            dict(kind="native_text", item_ref="#/texts/1", start=0, end=1),
            dict(kind="synthetic_separator", start=1, end=2),
            dict(kind="native_text", item_ref="#/texts/2", start=2, end=3),
        ],
    )
    result = context(primary, (DeclaredSourceSlice(A, 0, 3),))
    assert result.text == "X\nX"
    assert result.intervals[1] == SyntheticInterval(1, 2, "source projection separator")
    with pytest.raises(ContextRefused, match="synthetic"):
        result.map_span(1, 2)
    with pytest.raises(ContextRefused, match="synthetic"):
        result.map_span(0, 3, allow_multiple=True)
    (second,) = result.map_span(2, 3)
    assert isinstance(second, NativeSpanEvidence)
    assert (second.start, second.end, second.quote) == (2, 3, "X")
    assert json.loads(second.item_locator[4:])["pointer"] == "#/texts/2"


def test_inserted_punctuation_equal_to_source_text_never_becomes_evidence():
    result = context(
        source(1, "X."),
        (DeclaredSourceSlice(A, 0, 1), SyntheticText(".", "model terminal punctuation")),
    )
    assert result.text == "X."
    for start, end in ((1, 2), (0, 2)):
        with pytest.raises(ContextRefused, match="synthetic"):
            result.map_span(start, end, allow_multiple=True)


def test_multiple_real_pieces_require_role_permission_and_have_own_partial_coordinates():
    primary = source(1, "abcd")
    related = source(2, "efgh")
    result = context(
        primary,
        (DeclaredSourceSlice(A, 0, 4), DeclaredSourceSlice(B, 0, 4)),
        related=(
            RelatedNativeSource(related, ContextRelationship.NOTE, "explicitly referenced note"),
        ),
    )
    with pytest.raises(ContextRefused, match="multiple source anchors"):
        result.map_span(2, 6)
    actual = []
    for row in result.map_span(2, 6, allow_multiple=True):
        assert isinstance(row.source, DeclaredSourcePin)
        actual.append((row.source.source_key, row.start, row.end, row.quote))
    assert actual == [
        (A, 2, 4, "cd"),
        (B, 0, 2, "ef"),
    ]


def test_unicode_character_coordinates_are_not_bytes_graphemes_or_model_words():
    result = context(source(1, "😀e\u0301 X"), (DeclaredSourceSlice(A, 0, 5),))
    (anchor,) = result.map_span(1, 3)
    assert (anchor.start, anchor.end, anchor.quote) == (1, 3, "e\u0301")


@pytest.mark.parametrize("start,end", [(-1, 1), (0, 0), (1, 0), (0, 4), (True, 2)])
def test_model_span_bounds_refuse_without_rounding(start, end):
    result = context(source(1, "abc"), (DeclaredSourceSlice(A, 0, 3),))
    with pytest.raises(ContextRefused, match="model span"):
        result.map_span(start, end)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_chars": 2},
        {"max_pieces": 1},
        {"max_sources": 1},
        {"max_chars": 0},
        {"version": 1},
    ],
)
def test_bounds_refuse_whole_context_instead_of_truncating(kwargs):
    primary = source(1, "XX")
    other = source(2, "X")
    with pytest.raises(ContextRefused):
        context(
            primary,
            (DeclaredSourceSlice(A, 0, 2), DeclaredSourceSlice(B, 0, 1)),
            related=(
                RelatedNativeSource(other, ContextRelationship.NEIGHBOR, "missing qualifier"),
            ),
            **kwargs,
        )


def test_bound_counts_expanded_native_intervals_and_repeated_header_copies():
    primary = source(
        1,
        "ab",
        pieces=[
            dict(kind="native_text", item_ref="#/texts/1", start=0, end=1),
            dict(kind="native_text", item_ref="#/texts/2", start=1, end=2),
        ],
    )
    with pytest.raises(ContextRefused, match="interval bound"):
        context(primary, (DeclaredSourceSlice(A, 0, 2),), max_pieces=1)
    with pytest.raises(ContextRefused, match="character or interval bound"):
        context(primary, (DeclaredSourceSlice(A, 0, 2), DeclaredSourceSlice(A, 0, 2)), max_chars=3)


def test_identity_changes_with_membership_reasons_and_absent_retrieval_scope():
    primary = source(1, "X")
    initial = context(primary, (DeclaredSourceSlice(A, 0, 1),), retrievals=(retrieval(),))
    assert (
        context(
            primary, (DeclaredSourceSlice(A, 0, 1),), retrievals=(retrieval(),)
        ).dependency_digest
        == initial.dependency_digest
    )
    changes = (
        context(
            source(1, "X", membership="descendants"),
            (DeclaredSourceSlice(A, 0, 1),),
            retrievals=(retrieval(),),
        ),
        replace(initial, retrievals=(replace(retrieval(), membership_digest="e" * 64),)),
        replace(initial, retrievals=(replace(retrieval(), reason="estimand missing locally"),)),
        replace(
            initial, retrievals=(replace(retrieval(), outcome=RetrievalOutcome.RESOURCE_LIMIT),)
        ),
        replace(initial, policy="bounded-policy-2"),
    )
    assert all(
        result.text == "X" and result.dependency_digest != initial.dependency_digest
        for result in changes
    )


def test_changed_candidate_membership_and_exclusions_invalidate_ambiguous_lookup():
    primary = source(1, "X")
    candidate = source(2, "X").pin
    first = retrieval(candidates=(candidate,), outcome=RetrievalOutcome.AMBIGUOUS)
    result = context(primary, (DeclaredSourceSlice(A, 0, 1),), retrievals=(first,))
    second = replace(first, candidates=(candidate, source(3, "X").pin))
    excluded = replace(first, excluded=(B,))
    assert replace(result, retrievals=(second,)).dependency_digest != result.dependency_digest
    assert replace(result, retrievals=(excluded,)).dependency_digest != result.dependency_digest


def test_relationship_reason_and_individual_kind_pins_participate_in_dependency_identity():
    primary, neighbor = source(1, "X"), source(2, "X")
    entry = RelatedNativeSource(neighbor, ContextRelationship.NEIGHBOR, "antecedent")
    result = context(
        primary, (DeclaredSourceSlice(A, 0, 1), DeclaredSourceSlice(B, 0, 1)), related=(entry,)
    )
    changed_source = replace(
        neighbor,
        pin_content=canonical_bytes(
            {**neighbor.pin.values(), "kind_contract": "kind:another-current-contract"}
        ).decode(),
    )
    changes = (
        replace(entry, reason="population"),
        replace(entry, relationship=ContextRelationship.DECLARATION),
        replace(entry, source=changed_source),
    )
    assert all(
        context(primary, result.pieces, related=(changed,)).dependency_digest
        != result.dependency_digest
        for changed in changes
    )


def test_selected_retrieval_pin_must_match_the_actual_related_source():
    primary, neighbor = source(1, "X"), source(2, "X")
    pin = neighbor.pin
    receipt = retrieval(candidates=(pin,), selected=(B,), outcome=RetrievalOutcome.SELECTED)
    result = context(
        primary,
        (DeclaredSourceSlice(A, 0, 1), DeclaredSourceSlice(B, 0, 1)),
        related=(
            RelatedNativeSource(
                neighbor, ContextRelationship.DECLARATION, "population declaration"
            ),
        ),
        retrievals=(receipt,),
    )
    stale = replace(
        receipt,
        candidates=(
            DeclaredSourcePin(
                canonical_bytes({**pin.values(), "projection_digest": "f" * 64}).decode()
            ),
        ),
    )
    with pytest.raises(ContextRefused, match="stale"):
        replace(result, retrievals=(stale,))
    with pytest.raises(ContextRefused, match="absent or stale"):
        context(primary, (DeclaredSourceSlice(A, 0, 1),), retrievals=(receipt,))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"selected": (2,)},
        {"excluded": (2,)},
        {"outcome": RetrievalOutcome.SELECTED},
        {"scope_ref": ""},
    ],
)
def test_invalid_retrieval_contract_refuses(kwargs):
    initial = retrieval()
    with pytest.raises(ContextRefused):
        replace(initial, **kwargs)


def test_current_proposal_ancestor_rule_and_neighbor_context_remain_distinct():
    primary, neighbor = source(1, "X"), source(2, "X")
    with pytest.raises(ValueError, match="separately pinned direct ancestor"):
        DeclaredProposalFrame(
            primary.source_content,
            primary.pin_content,
            context_sources=(
                DeclaredProposalSource(neighbor.source_content, neighbor.pin_content),
            ),
        )
    result = context(
        primary,
        (DeclaredSourceSlice(A, 0, 1), DeclaredSourceSlice(B, 0, 1)),
        related=(RelatedNativeSource(neighbor, ContextRelationship.NEIGHBOR, "antecedent"),),
    )
    assert result.related[0].relationship == ContextRelationship.NEIGHBOR
    assert json.loads(result.primary.native_context)["ancestors"] == []


def test_explicit_ancestor_relationship_uses_existing_direct_ancestor_rule():
    primary = source(1, "X", ancestors=("#/groups/2",))
    ancestor = source(2, "Y")
    result = context(
        primary,
        (DeclaredSourceSlice(A, 0, 1), DeclaredSourceSlice(B, 0, 1)),
        related=(
            RelatedNativeSource(ancestor, ContextRelationship.ANCESTOR, "enclosing declaration"),
        ),
    )
    assert result.text == "XY"
    for changed in (source(3, "Y"), source(2, "Y", membership="descendants")):
        with pytest.raises(ValueError, match="distinct direct ancestor"):
            replace(
                result,
                related=(
                    RelatedNativeSource(changed, ContextRelationship.ANCESTOR, "declaration"),
                ),
                preparation=PreparedNativeSources((primary, changed)),
            )


def test_stale_projection_and_incompatible_product_refuse():
    primary = source(1, "X")
    with pytest.raises(ContextRefused, match="selected source"):
        context(
            replace(
                primary, source_content=canonical_bytes({**primary.value, "text": "Z"}).decode()
            ),
            (DeclaredSourceSlice(A, 0, 1),),
        )
    incompatible = source(2, "Y", document="document:foreign")
    with pytest.raises(ContextRefused, match="same pinned product"):
        context(
            primary,
            (DeclaredSourceSlice(A, 0, 1), DeclaredSourceSlice(B, 0, 1)),
            related=(
                RelatedNativeSource(incompatible, ContextRelationship.NEIGHBOR, "antecedent"),
            ),
        )


def test_current_frame_validates_qualified_sentence_addresses():
    primary = source(1, "X")
    sentence = ProposalSentence("s1", native_address(primary, start=0, end=1), 0, 1)
    frame = DeclaredProposalFrame(
        primary.source_content, primary.pin_content, sentence_values=(sentence,)
    )
    (anchor,) = context(frame, (DeclaredSourceSlice(A, 0, 1),)).map_span(0, 1)
    assert anchor.locator == sentence.locator
    with pytest.raises(ValueError, match="exact selected source extent"):
        replace(frame, sentence_values=(replace(sentence, locator="wrong"),))
    with pytest.raises(ValueError, match="declared frame pin"):
        replace(frame, version=3)


def test_lossy_mapping_other_coordinate_spaces_and_outside_source_ranges_refuse():
    with pytest.raises(ValueError, match="exact original-relative"):
        DeclaredSourceSlice(A, 0, 1, precision=cast(Literal["exact"], "lossy"))
    with pytest.raises(ValueError, match="exact original-relative"):
        DeclaredSourceSlice(
            A, 0, 1, coordinate_space=cast(Literal["native_projection"], "model_words")
        )
    for piece in (DeclaredSourceSlice(B, 0, 1), DeclaredSourceSlice(A, 0, 2)):
        with pytest.raises(ContextRefused, match=r"absent|outside"):
            context(source(1, "X"), (piece,))


def test_synthetic_only_context_and_unconsumed_selected_source_refuse():
    primary = source(1, "X")
    with pytest.raises(ContextRefused, match="consumed with source evidence"):
        context(primary, (SyntheticText("X", "inserted label"),))
    with pytest.raises(ContextRefused, match="consumed with source evidence"):
        context(
            primary,
            (DeclaredSourceSlice(A, 0, 1),),
            related=(
                RelatedNativeSource(source(2, "X"), ContextRelationship.NEIGHBOR, "antecedent"),
            ),
        )


def test_unsupported_native_projection_mapping_refuses_even_with_valid_digest():
    primary = source(
        1, "X", pieces=[dict(kind="normalized_text", item_ref="#/texts/1", start=0, end=1)]
    )
    with pytest.raises(ContextRefused, match="lossy native projection"):
        context(primary, (DeclaredSourceSlice(A, 0, 1),))


def test_literal_model_text_mismatch_refuses_without_searching_or_normalizing():
    result = context(source(1, "X X"), (DeclaredSourceSlice(A, 0, 3),))
    (anchor,) = result.map_span(2, 3, literal="X")
    assert (anchor.start, anchor.end) == (2, 3)
    with pytest.raises(ContextRefused, match="literal model span differs"):
        result.map_span(0, 1, literal="X.")


def test_conflicting_candidate_pins_refuse_even_when_candidate_was_not_selected():
    primary = source(1, "X")
    candidate = primary.pin
    stale = retrieval(
        candidates=(
            DeclaredSourcePin(
                canonical_bytes({**candidate.values(), "membership": "descendants"}).decode()
            ),
        )
    )
    with pytest.raises(ContextRefused, match="stale or contradicts"):
        context(primary, (DeclaredSourceSlice(A, 0, 1),), retrievals=(stale,))


def test_retrieval_relationship_cannot_silently_relabel_selected_neighbor_as_declaration():
    primary, neighbor = source(1, "X"), source(2, "Y")
    receipt = retrieval(
        candidates=(neighbor.pin,),
        selected=(B,),
        outcome=RetrievalOutcome.SELECTED,
    )
    with pytest.raises(ContextRefused, match="selected relationship"):
        context(
            primary,
            (DeclaredSourceSlice(A, 0, 1), DeclaredSourceSlice(B, 0, 1)),
            related=(RelatedNativeSource(neighbor, ContextRelationship.NEIGHBOR, "antecedent"),),
            retrievals=(receipt,),
        )


def test_current_recognition_outcome_is_retained_in_the_source_projection_identity():
    first = source(1, "X X", recognition=(dict(pointer="#/texts/1", outcome="failed"),))
    second = source(1, "X X", recognition=(dict(pointer="#/texts/1", outcome="succeeded"),))
    result = context(first, (DeclaredSourceSlice(A, 2, 3),))
    (anchor,) = result.map_span(0, 1, literal="X")
    assert (anchor.start, anchor.end, anchor.source.values()["projection_digest"]) == (
        2,
        3,
        first.projection_digest,
    )
    assert json.loads(result.primary.native_context)["health"] == {
        "formula_outcomes": [dict(pointer="#/texts/1", outcome="failed")]
    }
    assert (
        context(second, (DeclaredSourceSlice(A, 2, 3),)).dependency_digest
        != result.dependency_digest
    )


def test_prepared_source_view_is_shared_recursively_immutable_and_ordered():
    from corpus_structure.semantic.constructions.layers import ConstructionSource

    primary = source(1, "abc def", pieces=[
        dict(kind="native_text", item_ref="#/texts/1", start=0, end=3),
        dict(kind="synthetic_separator", start=3, end=4),
        dict(kind="native_text", item_ref="#/texts/2", start=4, end=7),
    ])
    assert primary.pieces is primary.pieces
    assert primary.items is primary.items
    assert PreparedNativeSources((primary,)).require(primary) is PreparedNativeSources((primary,)).require(primary)
    assert primary.view.ends == (3, 4, 7)
    assert [piece["start"] for piece in primary.view.selected_pieces(3, 5)] == [3, 4]
    assert [pointer for pointer, _ in primary.view.selected_items(2, 5)] == [
        "#/texts/1", "#/texts/2",
    ]
    with pytest.raises(TypeError):
        primary.items[0]["label"] = "changed"
    constructed = ConstructionSource.from_native(primary)
    assert constructed.pieces is constructed.pieces
    detached = constructed.value
    detached["pieces"][0]["end"] = 100
    assert constructed.pieces[0]["end"] == 3


@pytest.mark.parametrize("pieces", [
    [dict(kind="native_text", item_ref="#/texts/1", start=0, end=2),
     dict(kind="native_text", item_ref="#/texts/1", start=1, end=3)],
    [dict(kind="native_text", item_ref="#/texts/1", start=1, end=3)],
])
def test_prepared_view_refuses_nonpartitioned_source_pieces(pieces):
    # The fixture independently authenticates these actual bytes, so this exercises
    # ordering/partition admission rather than only a stale projection digest.
    primary = source(1, "abc", pieces=pieces)
    with pytest.raises(ValueError, match="partition"):
        _ = primary.pieces
