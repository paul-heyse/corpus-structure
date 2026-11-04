"""Independent region/coordinate expectations; controlled annotation is no provider claim."""

from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace
from typing import cast

import pytest
import spacy
from sqlalchemy import Engine

from corpus_structure.core.method import SourceViewRef, UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.methods import source_preparation as prep
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.source_views import PreparedSourceView


def source(text="Mean is average.\nX+Y\n12\n?", *, labels=("text", "formula", "table", "unknown")):
    chunks = text.split("\n")
    pieces, nodes = [], []
    offset = 0
    for index, (chunk, label) in enumerate(zip(chunks, labels, strict=True)):
        pointer = f"#/texts/{index}"
        nodes.append(dict(self_ref=pointer, label=label))
        if chunk:
            pieces.append(
                dict(item_ref=pointer, start=offset, end=offset + len(chunk), kind="native_text")
            )
            offset += len(chunk)
        if index < len(chunks) - 1:
            pieces.append(dict(start=offset, end=offset + 1, kind="synthetic_separator"))
            offset += 1
    projection = dict(
        text=text, pieces=pieces, items=[n["self_ref"] for n in nodes], ancestors=[], health={}
    )
    ref = SourceViewRef(
        7,
        "source:7",
        1,
        ProductReference(23, "integrated", "a" * 64),
        "#/groups/1",
        "descendants",
        sha256(canonical_bytes(projection)).hexdigest(),
        "c" * 64,
    )
    return PreparedSourceView(ref, text, tuple(pieces), tuple(nodes), (), {})


@pytest.fixture
def controlled(monkeypatch):
    nlp = spacy.blank("en")
    captured = []
    monkeypatch.setattr(prep, "pipeline", lambda _: nlp)

    def annotations(inputs, profile):
        for item in inputs:
            captured.append(item)
            # Controlled exact two-sentence boundaries, never model inference.
            starts = item.layout.block_start
            middle = item.block.text.find(". ")
            ends = (middle + 1, len(item.block.text)) if middle >= 0 else (len(item.block.text),)
            sentences = []
            a = 0
            for b in ends:
                sentences.append(SimpleNamespace(start=starts + a, end=starts + b))
                a = b
            yield SimpleNamespace(block_id=item.block_id, sentences=tuple(sentences))

    monkeypatch.setattr(prep, "annotate", annotations)
    return captured


def test_every_native_region_and_unknown_broad_route_are_retained(controlled):
    result = prep.prepare_source(source())
    assert len(result.regions) == 4
    assert [row.families for row in result.regions] == [
        ("definition", "assertion", "measurement"),
        ("formula_context",),
        ("table",),
        ("definition", "assertion", "measurement"),
    ]
    assert [row.outcome for row in result.regions] == ["selected"] * 4
    assert [(s.start, s.end) for s in result.selections] == [(0, 16), (17, 20), (21, 23), (24, 25)]
    assert controlled[1].layout.tokens[0].role == "math"
    assert controlled[1].layout.display == ((17, 20),)
    for selection in result.selections:
        context = selection.context(result.source, max_chars=4096, max_pieces=64)
        assert context.text == result.source.text[selection.start : selection.end]
        assert context.primary is result.source
        assert not hasattr(selection, "text")


def test_empty_unprojected_and_native_limits_keep_denominator(controlled):
    view = source("\nlong formula\n12\n?", labels=("text", "formula", "table", "unknown"))
    result = prep.prepare_source(view, max_chars=4)
    assert result.regions[0].outcome == "unsupported"
    assert result.regions[1].outcome == "partial"
    assert not result.regions[1].selections
    assert "bound exceeded" in result.regions[1].reason
    assert len(result.regions) == 4


def test_coherent_sentence_windows_preserve_offsets_without_truncation(controlled):
    result = prep.prepare_source(source("One. Two.", labels=("text",)), max_chars=5)
    assert [(s.start, s.end) for s in result.selections] == [(0, 4), (4, 9)]
    assert "".join(result.source.text[s.start : s.end] for s in result.selections) == "One. Two."
    limited = prep.prepare_source(source("Undivided sentence.", labels=("text",)), max_chars=5)
    assert limited.regions[0].outcome == "partial"
    assert limited.selections == ()


def test_reference_atom_identity_survives_preparation(controlled):
    result = prep.prepare_source(source("[3]", labels=("reference_marker",)))
    assert controlled[0].layout.tokens[0].role == "reference"
    assert result.regions[0].families == prep.PROSE_FAMILIES


@pytest.mark.parametrize("separator", ["", "\n"])
def test_native_inline_children_share_one_coherent_context_and_annotation(controlled, separator):
    view = replace(
        source("Mean is average.", labels=("text",)), text="Mean is " + separator + "average."
    )
    nodes = (
        dict(self_ref="#/texts/parent", label="text", children=[{"$ref": "#/groups/inline"}]),
        dict(self_ref="#/groups/inline", label="inline", parent={"$ref": "#/texts/parent"}),
        dict(self_ref="#/texts/0", label="text", parent={"$ref": "#/groups/inline"}),
        dict(self_ref="#/texts/1", label="text", parent={"$ref": "#/groups/inline"}),
    )
    pieces = (
        dict(kind="native_text", item_ref="#/texts/0", start=0, end=8),
        *((dict(kind="synthetic_separator", start=8, end=9),) if separator else ()),
        dict(
            kind="native_text", item_ref="#/texts/1", start=8 + len(separator), end=len(view.text)
        ),
    )
    projection = dict(
        text=view.text, pieces=pieces, items=[n["self_ref"] for n in nodes], ancestors=[], health={}
    )
    view = replace(
        view,
        items=nodes,
        pieces=pieces,
        ref=replace(view.ref, projection_digest=sha256(canonical_bytes(projection)).hexdigest()),
    )
    result = prep.prepare_source(view)
    assert len(controlled) == 1
    assert controlled[0].block.text == view.text
    assert len(result.selections) == 1
    assert result.selections[0].region == "#/texts/parent"
    assert [region.selections for region in result.regions] == [(0,), (0,), (0,), (0,)]


def test_old_record_absence_and_new_inspected_empty_are_distinct():
    ref = UnitRef(TaskUnitType.SOURCE_VIEW, 7, "source:7")
    old = UnitResult(ref=ref, outcome=ObservationOutcome.EMPTY)
    assert old.records is None
    assert replace(old, records=()).records == ()
    assert UnitResult(
        ref=ref, outcome=ObservationOutcome.PRODUCED, records=({"record_id": "candidate"},)
    ).records
    with pytest.raises(ValueError):
        replace(old, records=({"record_id": "candidate"},))


def test_m1_refuses_unpinned_or_native_input_before_database_access():
    from corpus_structure.orchestrate.commands import CommandError, start_bound_run

    for pin in (None, ProductReference(23, "native", "a" * 64)):
        # Preserve the invalid runtime engine: pin preflight must never touch it.
        with pytest.raises(CommandError, match="retained integrated"):
            start_bound_run(
                cast(Engine, object()),
                release_id="release",
                realization_id="input",
                project_id="project",
                domain="statistics",
                method_settings=None,
                extraction_policy="m1-candidate",
                native_product=pin,
            )


def test_m1_registry_has_no_agent_or_general_llm_route():
    from pathlib import Path

    from corpus_structure.orchestrate.m1 import (
        M1,
        RetainedIntegratedConfig,
        RetainedIntegratedPdf,
        registry,
    )

    root = Path(__file__).resolve().parents[4]
    methods = registry(root / "domains/statistics")
    assert {method.name for method in methods.methods()} == {
        "ingest.pdf_integrated",
        "extract.m1_annotations",
        "extract.m1_candidates",
        "resolve.m1_readings",
    }
    assert M1.policy_propose is False
    steps = M1.stages[1][1]
    assert steps[1].upstream == ("extract.m1_annotations",)
    assert not any("agent" in name or "llm" in name for name, _ in methods.named())
    method = methods.method("ingest.pdf_integrated")
    cfg = methods.overlay("ingest.pdf_integrated", "default")
    assert isinstance(method, RetainedIntegratedPdf)
    assert isinstance(cfg, RetainedIntegratedConfig)
    with pytest.raises(ValueError, match="conversion disabled"):
        method.original_recipe(cfg)


def test_owned_neighbor_context_preserves_pins_maps_and_failed_retrieval(controlled):
    from corpus_structure.semantic.proposals import native_source_frame
    from corpus_structure.semantic.source_contexts import (
        ContextRelationship,
        NativeSourcePin,
        RetrievalOutcome,
        SourceContextRead,
        SyntheticInterval,
    )

    primary = source("0.4", labels=("text",))
    neighbor = source("Population mean.", labels=("text",))
    neighbor = replace(neighbor, ref=replace(neighbor.ref, id=8, key="source:8"))
    pin = NativeSourcePin.from_source(native_source_frame(neighbor, ()))
    requests = []

    def related(identity, request, *, limit, read_budget):
        requests.append((identity, request, limit, read_budget))
        assert request.missing_roles == ("scope", "condition", "referent")
        return SourceContextRead(
            (neighbor,), (pin,), "b" * 64, RetrievalOutcome.SELECTED, "native previous sibling"
        )

    # Distinct native pointers, even if strings or recipes happen to match.
    neighbor_nodes = (dict(self_ref="#/texts/neighbor", label="text"),)
    neighbor_pieces = (dict(kind="native_text", item_ref="#/texts/neighbor", start=0, end=16),)
    projection = dict(
        text=neighbor.text,
        pieces=neighbor_pieces,
        items=["#/texts/neighbor"],
        ancestors=[],
        health={},
    )
    neighbor = replace(
        neighbor,
        items=neighbor_nodes,
        pieces=neighbor_pieces,
        ref=replace(
            neighbor.ref, projection_digest=sha256(canonical_bytes(projection)).hexdigest()
        ),
    )
    pin = NativeSourcePin.from_source(native_source_frame(neighbor, ()))
    result = prep.prepare_source(primary, reader=SimpleNamespace(context_sources=related))
    selection = result.selections[0]
    context = selection.context(
        result.source,
        related=result.related,
        preparation=result.preparation,
        max_chars=4096,
        max_pieces=64,
    )
    assert context.text == "0.4\nPopulation mean."
    assert context.version == 2 and context.preparation is result.preparation
    assert context.related[0].relationship == ContextRelationship.NEIGHBOR
    evidence = context.map_span(4, 20, literal="Population mean.")[0]
    assert evidence.source.source_view_id == 8 and (evidence.start, evidence.end) == (0, 16)
    assert isinstance(context.intervals[1], SyntheticInterval)
    assert requests[0][3].max_bytes == 4_194_304
    assert selection.retrievals[0].selected == (8,)
    limited = prep.prepare_source(
        primary, reader=SimpleNamespace(context_sources=related), max_chars=4
    )
    assert limited.selections[0].retrievals[0].outcome == RetrievalOutcome.RESOURCE_LIMIT
    assert limited.selections[0].retrievals[0].excluded == (8,)
    assert limited.selections[0].relationships == ()
    changed = replace(selection.retrievals[0], membership_digest="c" * 64)
    changed_context = replace(selection, retrievals=(changed,)).context(
        result.source,
        related=result.related,
        preparation=result.preparation,
        max_chars=4096,
        max_pieces=64,
    )
    assert changed_context.dependency_digest != context.dependency_digest


def test_native_table_links_have_missing_scope_and_no_automatic_note_attachment(controlled):
    from corpus_structure.semantic.source_contexts import RetrievalOutcome, SourceContextRead

    requests = []

    def related(identity, request, **_):
        requests.append(request)
        return SourceContextRead(
            (),
            (),
            "d" * 64,
            RetrievalOutcome.MISSING_SCOPE,
            "native table has no explicit note/caption target",
        )

    result = prep.prepare_source(
        source("0", labels=("table",)), reader=SimpleNamespace(context_sources=related)
    )
    assert [request.relationship.value for request in requests] == ["caption", "note"]
    assert [row.outcome for row in result.selections[0].retrievals] == [
        RetrievalOutcome.MISSING_SCOPE
    ] * 2
    assert result.regions[0].families == ("table",)
    assert result.selections[0].missing_roles == ("header_path", "unit", "caption", "note")


def test_local_related_budget_counts_projection_separators(controlled):
    from corpus_structure.semantic.source_contexts import RetrievalOutcome, SourceContextRead

    original = source("a\nB C", labels=("formula", "text"))
    nodes = (dict(original.items[0], captions=[{"$ref": "#/texts/1"}]), original.items[1])
    pieces = (
        *original.pieces[:2],
        dict(kind="native_text", item_ref="#/texts/1", start=2, end=3),
        dict(kind="synthetic_separator", start=3, end=4),
        dict(kind="native_text", item_ref="#/texts/1", start=4, end=5),
    )
    projection = dict(
        text=original.text,
        pieces=pieces,
        items=[n["self_ref"] for n in nodes],
        ancestors=[],
        health={},
    )
    original = replace(
        original,
        items=nodes,
        pieces=pieces,
        ref=replace(
            original.ref, projection_digest=sha256(canonical_bytes(projection)).hexdigest()
        ),
    )
    reader = SimpleNamespace(
        context_sources=lambda *_args, **_kwargs: SourceContextRead(
            (), (), "e" * 64, RetrievalOutcome.NO_MATCH, "no other source"
        )
    )
    result = prep.prepare_source(original, reader=reader, max_pieces=4)
    selection = result.selections[0]
    assert selection.local_dispositions == (
        ("#/texts/1", "resource_limit", "local context character/piece bound exceeded"),
    )
    context = selection.context(
        result.source,
        related=result.related,
        preparation=result.preparation,
        max_chars=4096,
        max_pieces=4,
    )
    assert context.text == "a" and len(context.intervals) == 1
