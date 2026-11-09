"""Independent provider extents against selected native fields."""

import json
from hashlib import sha256

import pytest

from corpus_structure.ingest.annotations import AnnotationInput
from corpus_structure.ingest.pdf_hierarchy import ProjectedPiece
from corpus_structure.ingest.sentences import Block, TextLayout, TextToken
from corpus_structure.methods.pm2_source import (
    D1SourceField,
    PM2SourceMap,
    PM2TokenMap,
    ProviderSpan,
    ProviderToken,
    SourceMapReason,
    SourceMapRefused,
    SourceMapSegment,
    map_d1,
    map_dipo,
    map_hanlp,
    map_maverick,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.proposals import NativeFrameSource
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext,
    NativeSourcePin,
    SourceSlice,
)


def source_context(fields, *, identity=1, policy="test-layout"):
    """Build each field and offset independently of the mapping adapter."""
    text = ""
    items = []
    pieces = []
    for pointer, field, selected, native in fields:
        if pointer is None:
            pieces.append(
                dict(kind="synthetic_separator", start=len(text), end=len(text + selected))
            )
        else:
            pieces.append(
                dict(
                    kind="native_text",
                    item_ref=pointer,
                    source_field=field,
                    start=len(text),
                    end=len(text + selected),
                )
            )
            node = dict(self_ref=pointer, text=native)
            if field == "orig":
                node["orig"] = selected
            items.append(node)
        text += selected
    projection = dict(
        text=text,
        pieces=pieces,
        items=[item["self_ref"] for item in items],
        ancestors=[],
        health={},
    )
    primary = NativeFrameSource(
        f"unit:{identity}",
        text,
        (),
        identity,
        ProductReference(18, "integrated", "a" * 64),
        "#/groups/1",
        "direct",
        sha256(canonical_bytes(projection)).hexdigest(),
        "b" * 64,
        canonical_bytes(dict(pieces=pieces, items=items, ancestors=[], health={})).decode(),
        version=3,
    )
    return NativeSourceContext(
        primary, (), (SourceSlice(identity, 0, len(text)),), "exact read", policy, "selected"
    )


def identity_map(text, *, atoms=(), identity=1, policy="test-layout"):
    context = source_context((("#/texts/0", "text", text, text),), identity=identity, policy=policy)
    return PM2SourceMap(context, text, (SourceMapSegment(0, len(text), 0),), atoms)


def test_prepared_layout_binds_source_and_supplies_protected_atoms():
    text = "[4] applies"
    context = identity_map(text).context
    segments = (SourceMapSegment(0, 11, 0),)
    layout = TextLayout(
        0,
        11,
        sha256(text.encode()).hexdigest(),
        (TextToken(0, 3, True, "reference"), TextToken(4, 11, False)),
        (),
    )
    prepared = AnnotationInput(
        NativeSourcePin.from_source(context.primary),
        "block",
        "paragraph",
        Block(text, (), (), ((0, 3),)),
        layout,
        (ProjectedPiece("#/texts/0", 0, 11, "native_text", source_field="text"),),
    )
    mapping = PM2SourceMap.from_annotation_input(context, prepared, text, segments)
    with pytest.raises(SourceMapRefused) as atom:
        map_d1(mapping, ProviderSpan(1, 2, "4"), scope_digest=mapping.scope_digest)
    assert atom.value.reason == SourceMapReason.PROTECTED_ATOM
    result = map_d1(mapping, ProviderSpan(0, 3, "[4]"), scope_digest=mapping.scope_digest)
    assert result.pieces[0].quote == "[4]"

    other = identity_map(text, identity=2).context
    with pytest.raises(SourceMapRefused) as wrong_layout:
        PM2SourceMap.from_annotation_input(other, prepared, text, segments)
    assert wrong_layout.value.reason == SourceMapReason.WRONG_SCOPE


@pytest.mark.parametrize(
    ("word", "policy"), [("μ̂", "estimate-clause"), ("créneau", "procedure-clause")]
)
def test_all_four_native_offsets_map_second_occurrence_under_same_contract(word, policy):
    width = len(word)
    text = f"{word} {word}."
    mapping = identity_map(text, policy=policy)
    tokens = PM2TokenMap(
        mapping,
        (
            ProviderToken(word, 0, width, 0),
            ProviderToken(word, width + 1, width * 2 + 1, 0),
            ProviderToken(".", width * 2 + 1, width * 2 + 2, 0),
        ),
    )
    start, end = width + 1, width * 2 + 1
    extent = ProviderSpan(start, end, word)
    scope = dict(scope_digest=mapping.scope_digest, native=True)

    results = (
        map_hanlp(tokens, 0, ((1, 2),), **scope),
        map_maverick(tokens, 1, 1, **scope),
        map_dipo(mapping, (extent,), **scope),
        map_d1(mapping, extent, **scope),
    )
    for result in results:
        assert result.scope_digest == mapping.scope_digest
        assert result.provider_spans == (extent,)
        assert [(p.start, p.end, p.quote, p.source_field) for p in result.pieces] == [
            (start, end, word, "text")
        ]
        assert [(a["pointer"], a["start"], a["end"], a["space"]) for a in result.anchors] == [
            ("#/texts/0", start, end, "native")
        ]
        assert result.coordinate_texts[0]["text"] == text
    assert results[0].anchors == results[-1].anchors
    assert tokens.input_digest != mapping.input_digest


def test_dipo_preserves_disjoint_ranges_and_refuses_crossed_seams_and_atoms():
    context = source_context(
        (
            ("#/texts/0", "text", "a ", "a "),
            ("#/texts/1", "orig", "x + y", "x+y"),
            (None, None, "\n", None),
            ("#/texts/2", "text", "a", "a"),
        )
    )
    mapping = PM2SourceMap(context, context.text, (SourceMapSegment(0, 9, 0),), ((2, 7),))
    scope = dict(scope_digest=mapping.scope_digest)
    result = map_dipo(mapping, (ProviderSpan(2, 7, "x + y"), ProviderSpan(8, 9, "a")), **scope)

    assert [(p.start, p.end, p.source_field) for p in result.pieces] == [
        (2, 7, "orig"),
        (8, 9, "text"),
    ]
    assert [a["space"] for a in result.anchors] == ["selected_projection", "selected_projection"]
    assert result.anchors[0]["source_piece"] == "x + y"
    with pytest.raises(SourceMapRefused, match="synthetic") as crossed:
        map_dipo(mapping, (ProviderSpan(2, 9, "x + y\na"),), **scope)
    assert crossed.value.reason == SourceMapReason.SOURCE_REFUSED
    with pytest.raises(SourceMapRefused) as atom:
        map_dipo(mapping, (ProviderSpan(2, 3, "x"),), **scope)
    assert atom.value.reason == SourceMapReason.PROTECTED_ATOM
    with pytest.raises(SourceMapRefused, match="unchanged"):
        map_dipo(mapping, (ProviderSpan(2, 7, "x + y"),), native=True, **scope)
    with pytest.raises(SourceMapRefused) as reversed_spans:
        map_dipo(mapping, tuple(reversed(result.provider_spans)), **scope)
    assert reversed_spans.value.reason == SourceMapReason.INVALID_EXTENT


def test_provider_and_layout_gaps_have_no_authority():
    context = identity_map("one two").context
    inserted = PM2SourceMap(
        context, "one[X] two", (SourceMapSegment(0, 3, 0), SourceMapSegment(6, 10, 3)), ()
    )
    omitted = PM2SourceMap(
        context, "onetwo", (SourceMapSegment(0, 3, 0), SourceMapSegment(3, 6, 4)), ()
    )
    with pytest.raises(SourceMapRefused) as injected:
        map_dipo(inserted, (ProviderSpan(0, 10, "one[X] two"),), scope_digest=inserted.scope_digest)
    assert injected.value.reason == SourceMapReason.UNMAPPED
    with pytest.raises(SourceMapRefused) as skipped:
        map_dipo(omitted, (ProviderSpan(0, 6, "onetwo"),), scope_digest=omitted.scope_digest)
    assert skipped.value.reason == SourceMapReason.UNMAPPED
    result = map_dipo(
        omitted,
        (ProviderSpan(0, 3, "one"), ProviderSpan(3, 6, "two")),
        scope_digest=omitted.scope_digest,
    )
    assert [(p.start, p.end) for p in result.pieces] == [(0, 3), (4, 7)]


def test_maverick_inclusive_endpoints_and_hanlp_sentence_coordinates():
    mapping = identity_map("Ada smiled. Ada waited.")
    tokens = PM2TokenMap(
        mapping,
        (
            ProviderToken("[SPEAKER]", None, None, 0),
            ProviderToken("Ada", 0, 3, 0),
            ProviderToken("smiled", 4, 10, 0),
            ProviderToken(".", 10, 11, 0),
            ProviderToken("Ada", 12, 15, 1),
            ProviderToken("waited", 16, 22, 1),
            ProviderToken(".", 22, 23, 1),
        ),
    )
    scope = dict(scope_digest=mapping.scope_digest)
    nested = map_maverick(tokens, 4, 4, **scope)
    outer = map_maverick(tokens, 4, 5, **scope)
    assert nested.pieces[0].quote == "Ada"
    assert nested.pieces[0].start == 12
    assert outer.pieces[0].quote == "Ada waited"
    assert map_hanlp(tokens, 1, ((0, 1), (2, 3)), **scope).provider_spans == (
        ProviderSpan(12, 15, "Ada"),
        ProviderSpan(22, 23, "."),
    )
    with pytest.raises(SourceMapRefused) as injected:
        map_maverick(tokens, 0, 1, **scope)
    assert injected.value.reason == SourceMapReason.UNMAPPED
    with pytest.raises(SourceMapRefused, match="crosses sentences"):
        map_maverick(tokens, 3, 4, **scope)
    with pytest.raises(SourceMapRefused, match="HanLP sentence"):
        map_hanlp(tokens, 1, ((0, 4),), **scope)


def test_wrong_scope_or_provider_literal_cannot_supply_an_exact_witness():
    mapping = identity_map("ratio")
    extent = ProviderSpan(0, 5, "ratio")
    another = identity_map("ratio", identity=2)
    with pytest.raises(SourceMapRefused) as wrong_scope:
        map_dipo(mapping, (extent,), scope_digest=another.scope_digest)
    assert wrong_scope.value.reason == SourceMapReason.WRONG_SCOPE
    assert wrong_scope.value.scope_digest == mapping.scope_digest
    with pytest.raises(SourceMapRefused) as forged:
        map_d1(mapping, ProviderSpan(0, 5, "share"), scope_digest=mapping.scope_digest)
    assert forged.value.reason == SourceMapReason.LITERAL_MISMATCH


def test_d1_json_offset_inverts_escapes_and_proves_repeated_field_origin():
    source = 'A "β"\nB'
    mapping = identity_map(source)
    rendered = json.dumps({"source/~": [source], "candidate": source}, ensure_ascii=False)
    source_field = D1SourceField(rendered, "/source~1~0/0", 15, 25)
    extent = ProviderSpan(17, 24, '"β"\n')
    scope = dict(scope_digest=mapping.scope_digest)

    result = map_d1(mapping, extent, field=source_field, path="/source~1~0/0", **scope)
    assert result.provider_spans == (extent,)
    assert [(p.start, p.end, p.quote) for p in result.pieces] == [(2, 6, '"β"\n')]
    assert result.input_digest != mapping.input_digest

    with pytest.raises(SourceMapRefused) as candidate:
        map_d1(mapping, extent, field=source_field, path="/candidate", **scope)
    assert candidate.value.reason == SourceMapReason.INVALID_FIELD

    substituted = D1SourceField(rendered, "/source~1~0/0", 43, 53)
    with pytest.raises(SourceMapRefused) as wrong_occurrence:
        map_d1(
            mapping,
            ProviderSpan(45, 52, '"β"\n'),
            field=substituted,
            path="/source~1~0/0",
            **scope,
        )
    assert wrong_occurrence.value.reason == SourceMapReason.INVALID_FIELD

    with pytest.raises(SourceMapRefused) as split_escape:
        map_d1(
            mapping,
            ProviderSpan(18, 24, '"β"\n'),
            field=source_field,
            path="/source~1~0/0",
            **scope,
        )
    assert split_escape.value.reason == SourceMapReason.INVALID_FIELD
