"""Independent region/coordinate expectations; controlled annotation is no provider claim."""

from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace
from typing import cast

import pytest
import spacy
from sqlalchemy import Engine

from corpus_structure.core.method import UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.methods import source_preparation as prep
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.source_contexts import NativeSourcePin
from methods.m1_source_preparation_support import (
    dense_table_source as dense_table_source,
)
from methods.m1_source_preparation_support import (
    native_table_source as native_table_source,
)
from methods.m1_source_preparation_support import (
    source as source,
)
from methods.m1_source_preparation_support import (
    table_cell as table_cell,
)


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

    from corpus_structure.methods.definition_applicability import (
        DefinitionApplicabilityConfig,
        DefinitionApplicabilityMethod,
        DefinitionComponentsConfig,
        DefinitionComponentsMethod,
    )
    from corpus_structure.orchestrate.m1 import (
        M1,
        RetainedIntegratedConfig,
        RetainedIntegratedPdf,
        registry,
    )

    root = Path(__file__).resolve().parents[4]
    methods = registry(root / "domains/statistics")
    assert {method.name for method in methods.methods()} == {
        "text.compose_view",
        "text.native_evidence",
        "text.formal_evidence",
        "text.constructions",
        "text.contextual_characterization",
        "text.model_characterization",
        "text.evaluate_context",
        "ingest.pdf_integrated",
        "extract.m1_annotations",
        "extract.m1_candidates",
        "resolve.m1_readings",
        "structure.clause_classification",
        "structure.definition_components",
        "structure.definition_declaration_components",
        "structure.definitions",
        "locate.definition_terms",
        "retrieve.contextual",
    }
    for name in ("structure.definition_components", "structure.definitions"):
        assert [(method, config) for method, config in methods.named() if method == name] == [
            (name, "default")
        ]
        assert methods.file.configs[name] == {}
    components = methods.method("structure.definition_components")
    definitions = methods.method("structure.definitions")
    component_cfg = methods.overlay("structure.definition_components", "default")
    definition_cfg = methods.overlay("structure.definitions", "default")
    assert isinstance(components, DefinitionComponentsMethod)
    assert isinstance(definitions, DefinitionApplicabilityMethod)
    assert isinstance(component_cfg, DefinitionComponentsConfig)
    assert isinstance(definition_cfg, DefinitionApplicabilityConfig)
    assert component_cfg.inputs is None and definition_cfg.inputs is None
    assert components.select(None, component_cfg) == ()
    assert definitions.select(None, definition_cfg) == ()
    assert components._worker is None
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
    assert isinstance(evidence.source, NativeSourcePin)
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


def test_dense_native_table_targets_every_data_cell_once_with_complete_bounded_paths():
    from corpus_structure.semantic.source_contexts import RetrievalOutcome, SourceContextRead

    view = dense_table_source()
    reader = SimpleNamespace(
        context_sources=lambda *_args, **_kwargs: SourceContextRead(
            (), (), "e" * 64, RetrievalOutcome.NO_MATCH, "no other source"
        )
    )
    prepared = prep.prepare_source(
        view, persisted_annotations=(), max_chars=256, max_pieces=64, reader=reader
    )
    selected = [s for s in prepared.selections if s.families == ("table",)]
    assert len(selected) == 30
    expected = {
        index
        for index, cell in enumerate(view.items[1]["data"]["table_cells"])
        if not cell.get("column_header") and not cell.get("row_header")
    }
    targets = []
    for selection in selected:
        assert selection.table_targets is not None
        targets.extend(target.cell_index for target in selection.table_targets)
    assert len(expected) == len(targets) == 270 and set(targets) == expected
    assert len(set(targets)) == len(targets)
    for selection in selected:
        assert selection.table_targets is not None
        context = selection.context(
            prepared.source,
            preparation=prepared.preparation,
            related=prepared.related,
            max_chars=256,
            max_pieces=64,
        )
        assert len(context.text) <= 256 and len(context.intervals) <= 64
        assert "Caption" in context.text and "Note" in context.text
        consumed = {getattr(interval, "cell_index", None) for interval in context.intervals}
        for target in selection.table_targets:
            assert len(target.row_path) == len(target.header_path) == 1
            assert {target.cell_index, *target.row_path, *target.header_path} <= consumed
        assert len(selection.table_targets) == 9
    table = next(region for region in prepared.regions if region.pointer == "#/tables/0")
    assert table.outcome == "selected" and len(table.selections) == 30


def test_indivisible_over_limit_cell_remains_visible_while_other_cells_are_selected():
    view = native_table_source(
        (
            table_cell("value", 0, 1, column_header=True),
            table_cell("A", 1, 0, row_header=True),
            table_cell("x" * 100, 1, 1),
            table_cell("B", 2, 0, row_header=True),
            table_cell("0", 2, 1),
        )
    )
    prepared = prep.prepare_source(view, persisted_annotations=(), max_chars=32, max_pieces=8)
    selected = [s for s in prepared.selections if s.families == ("table",)]
    assert len(selected) == 1 and selected[0].table_targets is not None
    assert [target.cell_index for target in selected[0].table_targets] == [4]
    region = next(r for r in prepared.regions if r.pointer == "#/tables/0")
    assert region.outcome == "partial"
    limited_cell = "#/tables/0/data/table_cells/2: complete target/path context bound exceeded"
    assert limited_cell in region.reason
    context = selected[0].context(
        prepared.source, preparation=prepared.preparation, max_chars=32, max_pieces=8
    )
    assert context.text == "value\nB\n0"


def test_discontinuous_primary_does_not_authorize_unconsumed_middle_context():
    from corpus_structure.semantic.source_contexts import RetrievalOutcome, SourceContextRead

    view = native_table_source(
        (
            table_cell("H", 0, 0, column_header=True),
            table_cell("V", 1, 0),
        ),
        caption="caption",
    )
    pieces = (
        dict(view.pieces[0], start=0, end=1),
        dict(kind="synthetic_separator", start=1, end=2),
        dict(view.pieces[-1], start=2, end=9),
        dict(kind="synthetic_separator", start=9, end=10),
        dict(view.pieces[2], start=10, end=11),
    )
    projection = dict(
        text="H\ncaption\nV",
        pieces=pieces,
        items=[n["self_ref"] for n in view.items],
        ancestors=[],
        health={},
    )
    view = replace(
        view,
        text=projection["text"],
        pieces=pieces,
        ref=replace(view.ref, projection_digest=sha256(canonical_bytes(projection)).hexdigest()),
    )
    reader = SimpleNamespace(
        context_sources=lambda *_args, **_kwargs: SourceContextRead(
            (), (), "e" * 64, RetrievalOutcome.NO_MATCH, "no other source"
        )
    )
    prepared = prep.prepare_source(
        view, persisted_annotations=(), max_chars=32, max_pieces=3, reader=reader
    )
    selection = next(s for s in prepared.selections if s.families == ("table",))
    assert (selection.start, selection.end) == (0, 11)
    assert selection.local_dispositions == (
        ("#/texts/captions", "resource_limit", "local context character/piece bound exceeded"),
    )
    context = selection.context(
        prepared.source, preparation=prepared.preparation, max_chars=32, max_pieces=3
    )
    assert context.text == "H\nV" and len(context.intervals) == 3


def test_native_geometry_retains_nested_paths_and_refuses_crossing_header_bands():
    cells = (
        dict(table_cell("all", 0, 0, column_header=True), end_col_offset_idx=3),
        table_cell("value", 1, 1, column_header=True),
        table_cell("A", 2, 0, row_header=True),
        table_cell("0", 2, 1),
    )
    (target,) = prep.native_table_geometry(dict(data=dict(table_cells=cells)))
    assert target.header_path == (0, 1) and target.row_path == (2,)
    ambiguous = (*cells, table_cell("competing", 1, 1, column_header=True))
    (target,) = prep.native_table_geometry(dict(data=dict(table_cells=ambiguous)))
    assert target.header_path == () and target.row_path == (2,)


def test_rich_header_projection_keeps_child_fields_and_counts_internal_separators():
    cells = (
        dict(
            table_cell("summary differs", 0, 1, column_header=True), ref={"$ref": "#/groups/header"}
        ),
        table_cell("A", 1, 0, row_header=True),
        table_cell("0", 1, 1),
        table_cell("B", 2, 0, row_header=True),
        table_cell("0", 2, 1),
    )
    view = native_table_source(cells)
    header = (
        ("#/texts/header0", "Binomial"),
        ("#/texts/header1", "n = 100"),
        ("#/texts/header2", "p = .001"),
    )
    nodes = (
        *view.items,
        dict(
            self_ref="#/groups/header",
            label="unspecified",
            children=[{"$ref": pointer} for pointer, _ in header],
        ),
        *(dict(self_ref=pointer, label="text", text=text) for pointer, text in header),
    )
    chunks = [
        *((pointer, 0, "text", text) for pointer, text in header),
        *(("#/tables/0", i, "cell_text", cells[i]["text"]) for i in range(1, 5)),
    ]
    pieces, texts, offset = [], [], 0
    for pointer, index, field, text in chunks:
        if texts:
            texts.append("\n")
            pieces.append(dict(kind="synthetic_separator", start=offset, end=offset + 1))
            offset += 1
        texts.append(text)
        pieces.append(
            dict(
                kind="native_text",
                item_ref=pointer,
                cell_index=index,
                source_field=field,
                start=offset,
                end=offset + len(text),
            )
        )
        offset += len(text)
    text = "".join(texts)
    projection = dict(
        text=text, pieces=pieces, items=[n["self_ref"] for n in nodes], ancestors=[], health={}
    )
    view = replace(
        view,
        text=text,
        pieces=tuple(pieces),
        items=nodes,
        ref=replace(view.ref, projection_digest=sha256(canonical_bytes(projection)).hexdigest()),
    )
    expected_header = "Binomial\nn = 100\np = .001"
    projected = prep.native_table_cell_projection(
        nodes[1], 0, {node["self_ref"]: node for node in nodes}
    )
    assert projected.text == expected_header
    assert [
        (p.item_ref, p.cell_index, p.source_field)
        for p in projected.pieces
        if p.kind == "native_text"
    ] == [(pointer, 0, "text") for pointer, _ in header]
    prepared = prep.prepare_source(view, persisted_annotations=(), max_chars=128, max_pieces=9)
    selections = [s for s in prepared.selections if s.families == ("table",)]
    assert len(selections) == 2
    for selection, suffix in zip(selections, ("A\n0", "B\n0"), strict=True):
        context = selection.context(
            prepared.source, preparation=prepared.preparation, max_chars=128, max_pieces=9
        )
        assert context.text == expected_header + "\n" + suffix
        assert len(context.intervals) == 9
    limited = prep.prepare_source(view, persisted_annotations=(), max_chars=128, max_pieces=8)
    assert not any(s.families == ("table",) for s in limited.selections)
    region = next(r for r in limited.regions if r.pointer == "#/tables/0")
    assert region.outcome == "partial" and "bound exceeded" in region.reason


def formula_paragraph_source(leading="Let x be a value. ", trailing=" in this scope."):
    original = source("fixture", labels=("text",))
    chunks = (
        ("#/texts/0", "text", leading),
        ("#/texts/1", "formula", "x=1"),
        ("#/texts/2", "text", trailing),
    )
    nodes = [
        dict(self_ref="#/groups/1", label="section", children=[{"$ref": "#/texts/3"}]),
        dict(
            self_ref="#/texts/3",
            label="text",
            text="",
            parent={"$ref": "#/groups/1"},
            children=[{"$ref": "#/groups/0"}],
        ),
        dict(
            self_ref="#/groups/0",
            label="inline",
            parent={"$ref": "#/texts/3"},
            children=[{"$ref": pointer} for pointer, _, _ in chunks],
        ),
    ]
    pieces, offset = [], 0
    for pointer, label, text in chunks:
        nodes.append(dict(self_ref=pointer, label=label, text=text, parent={"$ref": "#/groups/0"}))
        if text:
            pieces.append(
                dict(
                    kind="native_text",
                    item_ref=pointer,
                    source_field="text",
                    start=offset,
                    end=offset + len(text),
                )
            )
        offset += len(text)
    text = "".join(chunk for _, _, chunk in chunks)
    projection = dict(
        text=text, pieces=pieces, items=[n["self_ref"] for n in nodes], ancestors=[], health={}
    )
    return replace(
        original,
        text=text,
        pieces=tuple(pieces),
        items=tuple(nodes),
        ref=replace(
            original.ref, projection_digest=sha256(canonical_bytes(projection)).hexdigest()
        ),
    )


def empty_related_reader():
    from corpus_structure.semantic.source_contexts import RetrievalOutcome, SourceContextRead

    return SimpleNamespace(
        context_sources=lambda *_args, **_kwargs: SourceContextRead(
            (), (), "f" * 64, RetrievalOutcome.NO_MATCH, "no other selected source in this relation"
        )
    )


def test_formula_consumes_complete_same_primary_paragraph_once_with_exact_occurrence():
    from corpus_structure.semantic.source_contexts import ContextRelationship, NativeSpanEvidence

    view = formula_paragraph_source()
    prepared = prep.prepare_source(view, persisted_annotations=(), reader=empty_related_reader())
    selection = next(s for s in prepared.selections if s.families == ("formula_context",))
    formula = view.pieces[1]
    assert (selection.start, selection.end) == (formula["start"], formula["end"])
    assert selection.region == "#/texts/1"
    assert selection.local_relationships[0][:2] == ("#/texts/3", ContextRelationship.ANCESTOR)
    assert selection.local_dispositions[0][:2] == ("#/texts/3", "selected")
    assert selection.relationships == ()  # No synthetic second source or relabelled primary.
    context = selection.context(
        prepared.source, preparation=prepared.preparation, max_chars=4096, max_pieces=64
    )
    assert context.text == view.text and context.text.count("x=1") == 1
    (evidence,) = context.map_span(formula["start"], formula["end"], literal="x=1")
    assert isinstance(evidence, NativeSpanEvidence)
    assert isinstance(evidence.source, NativeSourcePin)
    assert (evidence.start, evidence.end, evidence.source.source_view_id) == (
        formula["start"],
        formula["end"],
        view.ref.id,
    )
    assert selection.retrievals[0].relationship == ContextRelationship.ANCESTOR


def test_oversized_formula_enclosure_is_partial_and_never_cropped_to_fit():
    view = formula_paragraph_source()
    prepared = prep.prepare_source(
        view, persisted_annotations=(), reader=empty_related_reader(), max_chars=8, max_pieces=64
    )
    selection = next(s for s in prepared.selections if s.families == ("formula_context",))
    assert selection.local_dispositions[0][:2] == ("#/texts/3", "resource_limit")
    context = selection.context(
        prepared.source, preparation=prepared.preparation, max_chars=8, max_pieces=64
    )
    assert context.text == "x=1"
    region = next(r for r in prepared.regions if r.pointer == "#/texts/1")
    assert region.outcome == "partial" and "whole nearest native enclosure" in region.reason


def test_formula_never_borrows_foreign_parent_metadata_or_unrelated_equal_prose():
    view = formula_paragraph_source()
    foreign = dict(
        self_ref="#/texts/foreign",
        label="text",
        text="Let x be a value.",
        children=[{"$ref": "#/texts/1"}],
    )
    nodes = tuple(
        dict(node, parent={"$ref": foreign["self_ref"]})
        if node["self_ref"] == "#/texts/1"
        else node
        for node in view.items
    )
    projection = dict(
        text=view.text,
        pieces=view.pieces,
        items=[n["self_ref"] for n in nodes],
        ancestors=[foreign["self_ref"]],
        health={},
    )
    view = replace(
        view,
        items=nodes,
        ancestors=(foreign,),
        ref=replace(view.ref, projection_digest=sha256(canonical_bytes(projection)).hexdigest()),
    )
    prepared = prep.prepare_source(view, persisted_annotations=(), reader=empty_related_reader())
    selection = next(s for s in prepared.selections if s.families == ("formula_context",))
    assert selection.local_dispositions[0][:2] == (foreign["self_ref"], "missing_scope")
    context = selection.context(
        prepared.source, preparation=prepared.preparation, max_chars=4096, max_pieces=64
    )
    assert context.text == "x=1"
    region = next(r for r in prepared.regions if r.pointer == "#/texts/1")
    assert region.outcome == "partial"
