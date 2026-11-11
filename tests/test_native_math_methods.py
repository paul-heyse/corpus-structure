"""Actual M09/M11/M13 branches consume immutable SourceViews and native addresses."""

import logging
from collections.abc import Sequence
from functools import cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Never

from corpus_structure.core.method import (
    CoverageDraft,
    MethodContext,
    MethodSettings,
    RunView,
    SourceCoverageReading,
    SourceViewRef,
    UnitRef,
    UnitView,
)
from corpus_structure.core.method import (
    Reader as ReaderPort,
)
from corpus_structure.core.vocab import ObservationKind, RunKind, TaskUnitType
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.math.methods import (
    ExtractMath,
    ExtractMathConfig,
    NormalizeFormula,
    NormalizeFormulaConfig,
    SymbolScope,
    SymbolScopeConfig,
)
from corpus_structure.methods.math.native import NativeDomainRule, domain_blocks
from corpus_structure.methods.math.scope import Binders
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.source_views import PreparedSourceView
from corpus_structure.semantic.types import PreparedRelease


def view():
    text = "Let x. Then x+x."
    items = (
        {"self_ref": "#/texts/0", "label": "text", "text": "Let "},
        {"self_ref": "#/texts/1", "label": "formula", "text": "x", "orig": "x"},
        {"self_ref": "#/texts/2", "label": "text", "text": ". Then "},
        {"self_ref": "#/texts/3", "label": "formula", "text": "x+x", "orig": "x+x"},
        {"self_ref": "#/texts/4", "label": "text", "text": "."},
    )
    extents = [(0, 4), (4, 5), (5, 12), (12, 15), (15, 16)]
    pieces = tuple(
        dict(item_ref=i["self_ref"], start=a, end=b, kind="native_text")
        for i, (a, b) in zip(items, extents, strict=True)
    )
    ref = SourceViewRef(
        7,
        "native-section:7",
        1,
        ProductReference(2, "organized", "a" * 64),
        "#/groups/0",
        "direct",
        "b" * 64,
        "c" * 64,
    )
    health = {
        "formula_outcomes": [
            {"pointer": "#/texts/1", "outcome": "succeeded"},
            {"pointer": "#/texts/3", "outcome": "succeeded"},
        ],
        "inline_coverage": "complete",
        "cell_coverage": "complete",
        "display_coverage": "complete",
    }
    return PreparedSourceView(ref, text, pieces, items, (), health)


@cache
def pure_source_release() -> PreparedRelease:
    from corpus_structure.semantic import PreparationProfile, ResolvedDependencies, prepare_release
    from corpus_structure.semantic.composed import composed_dependencies
    from corpus_structure.semantic.contracts import trusted_execution_inputs

    inputs = trusted_execution_inputs()
    return prepare_release(
        inputs.schema,
        composed_dependencies(ResolvedDependencies(), inputs),
        PreparationProfile(version="semantic-2"),
    )


class Reader(ReaderPort):
    @property
    def prepared(self) -> PreparedRelease:
        return pure_source_release()

    math_readings_batch = None

    def _unavailable(self, *args: object, **kwargs: object) -> Never:
        raise AssertionError("this native consumer control does not supply that reader capability")

    native_document = _unavailable
    native_section_drafts = _unavailable
    capture_pdf_candidates = _unavailable
    native_product_reference = _unavailable
    prepare_pdf_product = _unavailable
    prepare_integrated_pdf_product = _unavailable
    pdf_context = _unavailable
    renditions = _unavailable
    content = _unavailable
    segments = _unavailable
    observations = _unavailable
    source_coverage = _unavailable
    measurements = _unavailable
    artifact = _unavailable
    guideline = _unavailable
    original = _unavailable
    connection = _unavailable
    characterization_layers = _unavailable
    characterization_release = _unavailable
    characterization_view = _unavailable
    characterization_memberships = _unavailable

    def __init__(self):
        self.view = view()
        self.views: dict[int, PreparedSourceView] = {7: self.view}
        self.outputs: dict[tuple[int, str, ObservationKind], list[Any]] = {}

    def source_views(self):
        return [self.view.ref]

    def documents(self, originals: Sequence[str]) -> tuple[UnitRef, ...]:
        # This fixture has no retained original-source selection.
        return ()

    def source_view_documents(self) -> tuple[UnitRef, ...]:
        return tuple(
            UnitRef(TaskUnitType.DOCUMENT, identity, f"document:{identity}")
            for identity in sorted({view.ref.document_id for view in self.views.values()})
        )

    def source_view(self, source_view_id: int) -> PreparedSourceView:
        return self.views[source_view_id]

    def ancestor_source_views(self, source_view_id: int) -> list[SourceViewRef]:
        child = self.source_view(source_view_id)
        pointers = {item["self_ref"] for item in child.ancestors}
        return [
            parent.ref
            for parent in self.views.values()
            if parent.ref.section_pointer in pointers
            and parent.ref.native_product == child.ref.native_product
        ]

    def source_observations(self, source_view_id, method, kind):
        return self.outputs.get((source_view_id, method, kind), [])

    def source_formula_metadata(self, source_view_id, pointer):
        retained = self.views[source_view_id]
        return retained.ref, {
            item["pointer"]: item["outcome"] for item in retained.health.get("formula_outcomes", ())
        }

    def source_observations_for_ref(self, reference, method, kind):
        assert reference == self.views[reference.id].ref
        return self.source_observations(reference.id, method, kind)

    def source_view_coverage(self, source_view_id, method):
        return (
            SourceCoverageReading(
                task_id=4,
                release_id="fixture",
                position=0,
                coverage=CoverageDraft(family=method, scope="native-section:7", outcome="complete"),
            ),
        )

    def store(self, method, result):
        for ordinal, draft in enumerate(result.observations):
            row = SimpleNamespace(
                payload=draft.payload.model_dump(mode="json"),
                native_pointer=draft.native_pointer,
                observation_key=f"{method}:{ordinal}",
                payload_hash=str(ordinal),
                task_id=42,
            )
            self.outputs.setdefault((draft.source_view_id, method, draft.kind), []).append(row)


def run_for(reader: Reader) -> RunView:
    return RunView(
        run_id=1,
        kind=RunKind.FULL,
        phase=0,
        reference_run_id=None,
        model_revision="fixture",
        schema_version_id=1,
        guideline_version_id=None,
        policy_version_id=None,
        key_scheme=1,
        options={},
        reader=reader,
    )


def context_for(reader: Reader) -> MethodContext:
    return MethodContext(
        run_for(reader),
        reader,
        MethodSettings(data_dir=Path("."), model_cache=Path(".")),
        logging.getLogger(__name__),
    )


def test_actual_methods_select_source_views_and_keep_native_offsets():
    reader = Reader()
    run = run_for(reader)
    unit = UnitView(
        UnitRef(TaskUnitType.SOURCE_VIEW, 7, "native-section:7"),
        run,
        document_id=1,
        source_view_id=7,
    )
    ctx = context_for(reader)
    assert list(ExtractMath().select(run, ExtractMathConfig())) == [unit.ref]
    m09 = ExtractMath().run([unit], ExtractMathConfig(), ctx)[0]
    mentions = [o for o in m09.observations if o.kind is ObservationKind.MENTION]
    assert len(mentions) == 3
    assert [o.recognized_span for o in mentions] == [(0, 1), (0, 1), (2, 3)]
    assert [o.projected_span for o in mentions] == [(4, 5), (12, 13), (14, 15)]
    assert all(o.rendition_id is None and o.span is None for o in mentions)
    reader.store("extract.math", m09)
    m11 = NormalizeFormula().run([unit], NormalizeFormulaConfig(), ctx)[0]
    assert len([o for o in m11.observations if o.kind is ObservationKind.VALUE]) == 2
    records = [o for o in m11.observations if o.kind is ObservationKind.RECORD]
    assert len(records) == 1
    assert records[0].payload.items[0]["interpretation_ref"]["observation_key"]
    assert records[0].payload.items[0]["symbolic"]["expression"] == "Symbol('x')"
    reader.store("normalize.formula", m11)
    cfg = SymbolScopeConfig(binders=Binders(sentence_initial=("let",)), sentences=SentenceConfig())
    # Scope consumes recorded M09/M11 values and may not re-enter mathematical inference.
    import unittest.mock

    with unittest.mock.patch(
        "corpus_structure.methods.math.native.readings", side_effect=AssertionError("reparsed")
    ):
        result = SymbolScope().run([unit], cfg, ctx)[0]
    assert all(o.source_view_id == 7 and o.rendition_id is None for o in result.observations)
    scopes = [o.payload for o in result.observations if o.kind is ObservationKind.SCOPE]
    assert len(scopes) == 3
    assert all(scope.outcome == "resolved" for scope in scopes)
    assert scopes[1].binding_observation == scopes[0].binding_observation


def test_domain_roles_are_release_rules_and_do_not_imply_proof_truth():
    source = SimpleNamespace(
        ref=view().ref,
        ancestors=(),
        text="Proof. Details.",
        items=({"self_ref": "#/texts/0", "label": "section_header", "text": "Proof."},),
        pieces=({"item_ref": "#/texts/0", "start": 0, "end": 6},),
    )
    assert domain_blocks(source, ()) == ()
    rule = NativeDomainRule(
        rule_id="proof-heading-1", pattern=r"^Proof\.", statement_kind="proof", scope_role="proof"
    )
    recognized = domain_blocks(source, (rule,))
    assert recognized[0][2] == "#/texts/0"
    assert recognized[0][3].rule_id == "proof-heading-1"


def test_ancestor_function_roles_require_forward_native_tree_order():
    from dataclasses import replace

    from corpus_structure.core.vocab import ParseOutcome
    from corpus_structure.methods.math.methods import MathSection
    from corpus_structure.methods.math.native import native_ancestor_declarations, readings

    rule = NativeDomainRule(
        rule_id="proof-heading-1", pattern=r"^Proof\.", statement_kind="proof", scope_role="proof"
    )
    parent_group = {
        "self_ref": "#/groups/0",
        "label": "section",
        "children": [
            {"$ref": "#/texts/0"},
            {"$ref": "#/texts/1"},
            {"$ref": "#/groups/1"},
            {"$ref": "#/texts/2"},
        ],
    }
    parent_items = (
        parent_group,
        {
            "self_ref": "#/texts/0",
            "label": "formula",
            "text": "f(2)",
            "orig": "f(2)",
            "parent": {"$ref": "#/groups/0"},
        },
        {
            "self_ref": "#/texts/1",
            "label": "formula",
            "text": "f(x)=x",
            "orig": "f(x)=x",
            "parent": {"$ref": "#/groups/0"},
        },
        {
            "self_ref": "#/texts/2",
            "label": "formula",
            "text": "g(x)=x",
            "orig": "g(x)=x",
            "parent": {"$ref": "#/groups/0"},
        },
    )
    child_group = {
        "self_ref": "#/groups/1",
        "label": "section",
        "parent": {"$ref": "#/groups/0"},
        "children": [{"$ref": "#/texts/3"}, {"$ref": "#/texts/4"}],
    }
    child_items = (
        child_group,
        {
            "self_ref": "#/texts/3",
            "label": "formula",
            "text": "f(2)",
            "orig": "f(2)",
            "parent": {"$ref": "#/groups/1"},
        },
        {
            "self_ref": "#/texts/4",
            "label": "formula",
            "text": "g(2)",
            "orig": "g(2)",
            "parent": {"$ref": "#/groups/1"},
        },
    )

    def make(id, group, items, ancestors):
        texts = []
        pieces = []
        position = 0
        for item in items:
            if "text" not in item:
                continue
            text = item["text"]
            texts.append(text)
            pieces.append(dict(item_ref=item["self_ref"], start=position, end=position + len(text)))
            position += len(text)
        ref = replace(view().ref, id=id, key=f"native:{id}", section_pointer=group["self_ref"])
        health = {
            "formula_outcomes": [
                {"pointer": i["self_ref"], "outcome": "succeeded"}
                for i in items
                if i.get("label") == "formula"
            ],
            "display_coverage": "complete",
            "inline_coverage": "complete",
            "cell_coverage": "complete",
        }
        return PreparedSourceView(ref, "".join(texts), tuple(pieces), items, ancestors, health)

    parent = make(7, parent_group, parent_items, ())
    child = make(8, child_group, child_items, (parent_group,))
    reader = Reader()
    reader.views = {7: parent, 8: child}
    reader.math_readings_batch = None
    reader.source_views = lambda: [parent.ref, child.ref]
    cfg = NormalizeFormulaConfig(math=MathSection(native_domain_rules=(rule,)))
    declarations, issues = native_ancestor_declarations(reader, child, (rule,))
    assert issues == ()
    assert [d["symbol"] for d in declarations] == ["f"]
    assert "#/texts/1" in declarations[0]["evidence"]
    earlier = readings(parent, cfg, reader)[0]
    assert earlier.result.status is ParseOutcome.AMBIGUOUS
    child_readings = readings(child, cfg, reader)
    assert child_readings[0].result.status is ParseOutcome.OK
    assert child_readings[1].result.status is ParseOutcome.AMBIGUOUS


def test_local_proof_function_definition_does_not_escape_to_child_section():
    from dataclasses import replace

    from corpus_structure.methods.math.native import native_ancestor_declarations

    parent_group = {
        "self_ref": "#/groups/0",
        "label": "section",
        "children": [{"$ref": "#/texts/0"}, {"$ref": "#/texts/1"}, {"$ref": "#/groups/1"}],
    }
    heading = {
        "self_ref": "#/texts/0",
        "label": "section_header",
        "text": "Proof.",
        "parent": {"$ref": "#/groups/0"},
    }
    formula = {
        "self_ref": "#/texts/1",
        "label": "formula",
        "text": "h(x)=x",
        "orig": "h(x)=x",
        "parent": {"$ref": "#/groups/0"},
    }
    child_group = {
        "self_ref": "#/groups/1",
        "label": "section",
        "parent": {"$ref": "#/groups/0"},
        "children": [],
    }
    parent = PreparedSourceView(
        view().ref,
        "Proof.h(x)=x",
        (
            {"item_ref": "#/texts/0", "start": 0, "end": 6},
            {"item_ref": "#/texts/1", "start": 6, "end": 12},
        ),
        (parent_group, heading, formula),
        (),
        {"formula_outcomes": [{"pointer": "#/texts/1", "outcome": "succeeded"}]},
    )
    child = PreparedSourceView(
        replace(view().ref, id=8, key="child", section_pointer="#/groups/1"),
        "",
        (),
        (child_group,),
        (parent_group,),
        {},
    )
    reader = Reader()
    reader.views = {7: parent, 8: child}
    reader.source_views = lambda: [parent.ref, child.ref]
    rule = NativeDomainRule(
        rule_id="proof-heading-1", pattern=r"^Proof\.", statement_kind="proof", scope_role="proof"
    )
    assert native_ancestor_declarations(reader, child, (rule,))[0] == ()


def test_context_only_parent_prepares_weak_variable_binding_for_child(monkeypatch):
    from dataclasses import replace

    from corpus_structure.methods.math.methods import MathSection
    from corpus_structure.methods.math.native import native_scope_result
    from corpus_structure.methods.math.prepared import PreparedMathInput

    rule = NativeDomainRule(
        rule_id="proof-heading-1", pattern=r"^Proof\.", statement_kind="proof", scope_role="proof"
    )
    group = {
        "self_ref": "#/groups/0",
        "label": "section",
        "children": [
            {"$ref": "#/texts/0"},
            {"$ref": "#/texts/1"},
            {"$ref": "#/texts/2"},
            {"$ref": "#/groups/1"},
        ],
    }
    child_group = {
        "self_ref": "#/groups/1",
        "label": "section",
        "parent": {"$ref": "#/groups/0"},
        "children": [{"$ref": "#/texts/3"}],
    }
    parent_items = (
        group,
        {
            "self_ref": "#/texts/0",
            "label": "text",
            "text": "Let ",
            "parent": {"$ref": "#/groups/0"},
        },
        {
            "self_ref": "#/texts/1",
            "label": "formula",
            "text": "x",
            "orig": "x",
            "parent": {"$ref": "#/groups/0"},
        },
        {"self_ref": "#/texts/2", "label": "text", "text": ".", "parent": {"$ref": "#/groups/0"}},
    )
    parent = PreparedSourceView(
        view().ref,
        "Let x.",
        tuple(
            dict(item_ref=pointer, start=a, end=b)
            for pointer, a, b in [("#/texts/0", 0, 4), ("#/texts/1", 4, 5), ("#/texts/2", 5, 6)]
        ),
        parent_items,
        (),
        {"formula_outcomes": [{"pointer": "#/texts/1", "outcome": "succeeded"}]},
    )
    child = PreparedSourceView(
        replace(view().ref, id=8, key="child", section_pointer="#/groups/1"),
        "x+x",
        ({"item_ref": "#/texts/3", "start": 0, "end": 3},),
        (
            child_group,
            {
                "self_ref": "#/texts/3",
                "label": "formula",
                "text": "x+x",
                "orig": "x+x",
                "parent": {"$ref": "#/groups/1"},
            },
        ),
        (group,),
        {
            "formula_outcomes": [{"pointer": "#/texts/3", "outcome": "succeeded"}],
            "inline_coverage": "complete",
            "cell_coverage": "complete",
        },
    )
    reader = Reader()
    reader.views = {7: parent, 8: child}
    reader.source_views = lambda: [child.ref]
    ctx = context_for(reader)
    run = run_for(reader)
    cfg = SymbolScopeConfig(
        math=MathSection(native_domain_rules=(rule,)),
        binders=Binders(sentence_initial=("let",)),
        sentences=SentenceConfig(),
    )
    parent_unit = SimpleNamespace(
        ref=UnitRef(TaskUnitType.SOURCE_VIEW, 7, parent.ref.key), context_only=True
    )
    with monkeypatch.context() as guard:
        guard.setattr(
            PreparedMathInput,
            "symbolic_value",
            lambda *a, **k: (_ for _ in ()).throw(AssertionError("strong")),
        )
        context = native_scope_result(parent_unit, cfg, ctx)
    assert context.observations[0].payload.declarations[0].symbol == "x"
    reader.store("resolve.symbol_scope", context)
    unit = UnitView(UnitRef(TaskUnitType.SOURCE_VIEW, 8, child.ref.key), run, source_view_id=8)
    mathcfg = ExtractMathConfig(math=MathSection(native_domain_rules=(rule,)))
    reader.store("extract.math", ExtractMath().run([unit], mathcfg, ctx)[0])
    reader.store(
        "normalize.formula",
        NormalizeFormula().run([unit], NormalizeFormulaConfig(math=mathcfg.math), ctx)[0],
    )
    result = SymbolScope().run([unit], cfg, ctx)[0]
    assert all(
        o.payload.outcome == "resolved"
        for o in result.observations
        if o.kind is ObservationKind.SCOPE
    )
    assert all(
        o.payload.binding_source_view_id == 7
        for o in result.observations
        if o.kind is ObservationKind.SCOPE
    )
    assert all(
        any(ref.role == "native_parent_context" for ref in o.input_refs)
        for o in result.observations
        if o.kind is ObservationKind.SCOPE
    )


def test_occurrence_owner_is_weak_and_normalization_reuses_retained_tree(monkeypatch):
    from corpus_structure.methods.math import grammar
    from corpus_structure.methods.math.prepared import PreparedMathInput
    from corpus_structure.semantic.native_analysis import stored_native_analysis

    reader = Reader()
    run = run_for(reader)
    ctx = context_for(reader)
    unit = UnitView(
        UnitRef(TaskUnitType.SOURCE_VIEW, 7, reader.view.ref.key), run, source_view_id=7
    )
    with monkeypatch.context() as guard:
        guard.setattr(
            PreparedMathInput,
            "symbolic_value",
            lambda *a, **k: (_ for _ in ()).throw(AssertionError("unasked symbolic work")),
        )
        guard.setattr(
            PreparedMathInput,
            "definedness_result",
            lambda *a, **k: (_ for _ in ()).throw(AssertionError("unasked definedness work")),
        )
        weak = ExtractMath().run([unit], ExtractMathConfig(), ctx)[0]
    reader.store("extract.math", weak)
    # Neither normalization nor inspection may reconstruct the original syntax tree.
    with monkeypatch.context() as guard:
        guard.setattr(
            grammar, "syntax", lambda *a, **k: (_ for _ in ()).throw(AssertionError("reparsed"))
        )
        strong = NormalizeFormula().run([unit], NormalizeFormulaConfig(), ctx)[0]
        reader.store("normalize.formula", strong)
        recorded = stored_native_analysis(reader, 7, "#/texts/3")["#/texts/3"]
    assert recorded["interpretation"]["recognized_latex"] == "x+x"
    assert recorded["normalization"]["symbolic"]["expression"] == "Mul(Integer(2), Symbol('x'))"
    assert [row["method"] for row in recorded["observations"]] == [
        "extract.math",
        "normalize.formula",
    ]


def test_normalization_refuses_missing_named_occurrence_owner():
    import pytest

    reader = Reader()
    run = run_for(reader)
    ctx = context_for(reader)
    unit = UnitView(
        UnitRef(TaskUnitType.SOURCE_VIEW, 7, reader.view.ref.key), run, source_view_id=7
    )
    with pytest.raises(ValueError, match="one exact completed"):
        NormalizeFormula().run([unit], NormalizeFormulaConfig(), ctx)


def test_stored_analysis_refuses_cycles_and_stale_pins():
    import pytest

    from corpus_structure.semantic.native_analysis import (
        NativeAnalysisUnavailable,
        stored_native_analysis,
    )

    reader = Reader()
    payload = dict(
        demand="symbolic",
        source_view_id=7,
        native_product=reader.view.ref.native_product.values(),
        projection_digest=reader.view.ref.projection_digest,
        recipe_digest=reader.view.ref.recipe_digest,
        items=[
            dict(
                pointer="#/texts/1",
                interpretation_ref=dict(observation_key="self", pointer="#/texts/1"),
            )
        ],
    )
    row = SimpleNamespace(payload=payload, observation_key="self", task_id=1, payload_hash="hash")
    reader.outputs[(7, "normalize.formula", ObservationKind.RECORD)] = [row]
    with pytest.raises(NativeAnalysisUnavailable, match="cycle"):
        stored_native_analysis(reader, 7, "#/texts/1")
    payload["native_product"] = {**payload["native_product"], "content_digest": "d" * 64}
    with pytest.raises(NativeAnalysisUnavailable, match="pinned source view"):
        stored_native_analysis(reader, 7, "#/texts/1")


def test_scope_digest_binds_exact_ancestor_preparation_record():
    from dataclasses import replace

    reader = Reader()
    source = reader.view
    parent = PreparedSourceView(
        replace(source.ref, id=6, key="parent", section_pointer="#/groups/parent"),
        "",
        (),
        (),
        (),
        {},
    )
    group = {
        "self_ref": "#/groups/parent",
        "label": "section",
        "children": [{"$ref": "#/groups/0"}],
    }
    child = replace(source, ancestors=(group,))
    reader.views = {6: parent, 7: child}
    row = SimpleNamespace(observation_key="parent-context", payload_hash="first")
    reader.outputs[(6, "resolve.symbol_scope", ObservationKind.RECORD)] = [row]
    run = run_for(reader)
    unit = UnitView(UnitRef(TaskUnitType.SOURCE_VIEW, 7, child.ref.key), run, source_view_id=7)
    first = SymbolScope().input_digest(unit, SymbolScopeConfig()).bytes
    row.payload_hash = "second"
    assert SymbolScope().input_digest(unit, SymbolScopeConfig()).bytes != first


def test_strong_request_reuses_qualified_stored_parent_roles_without_parsing(monkeypatch):
    from dataclasses import replace

    from corpus_structure.methods.math.native import (
        native_request_analysis,
        stored_native_ancestor_declarations,
    )
    from corpus_structure.methods.math.prepared import PreparedMathInput

    parent_group = {
        "self_ref": "#/groups/parent",
        "label": "section",
        "children": [{"$ref": "#/texts/parent"}, {"$ref": "#/groups/0"}],
    }
    parent = PreparedSourceView(
        replace(view().ref, id=6, key="parent", section_pointer="#/groups/parent"),
        "f(x)=x",
        ({"item_ref": "#/texts/parent", "start": 0, "end": 6},),
        (
            parent_group,
            {
                "self_ref": "#/texts/parent",
                "label": "formula",
                "text": "f(x)=x",
                "orig": "f(x)=x",
                "parent": {"$ref": "#/groups/parent"},
            },
        ),
        (),
        {
            "display_coverage": "complete",
            "inline_coverage": "complete",
            "cell_coverage": "complete",
        },
    )
    child_group = {
        "self_ref": "#/groups/0",
        "label": "section",
        "parent": {"$ref": "#/groups/parent"},
    }
    child = PreparedSourceView(
        view().ref,
        "f(2)",
        ({"item_ref": "#/texts/0", "start": 0, "end": 4},),
        (
            child_group,
            {
                "self_ref": "#/texts/0",
                "label": "formula",
                "text": "f(2)",
                "orig": "f(2)",
                "parent": {"$ref": "#/groups/0"},
            },
        ),
        (parent_group,),
        {"formula_outcomes": [dict(pointer="#/texts/0", outcome="succeeded")]},
    )
    payload = dict(
        demand="context_declarations",
        source_view_id=6,
        native_product=parent.ref.native_product.values(),
        projection_digest=parent.ref.projection_digest,
        declarations=[
            dict(
                symbol="f",
                role="function",
                rule_id="function-definition-1",
                source_pointer="#/texts/parent",
                recognized_start=0,
                recognized_end=1,
                scope_pointer=parent.ref.section_pointer,
                quote="f(x)=x",
            )
        ],
    )
    row = SimpleNamespace(
        payload=payload, observation_key="parent-function", payload_hash="qualified"
    )
    reader = Reader()
    reader.views = {6: parent, 7: child}
    reader.outputs[(6, "resolve.symbol_scope", ObservationKind.RECORD)] = [row]
    with monkeypatch.context() as guard:
        guard.setattr(
            PreparedMathInput,
            "syntax",
            lambda *a, **k: (_ for _ in ()).throw(AssertionError("parent reparse")),
        )
        declarations, issues = stored_native_ancestor_declarations(reader, child)
    assert issues == ()
    assert declarations[0]["symbol"] == "f" and "parent-function" in declarations[0]["evidence"]
    result = native_request_analysis(
        child, None, "interpretation", ancestor_declarations=declarations
    )
    assert result.items[0]["outcome"] == "ok"
    payload["projection_digest"] = "e" * 64
    declarations, issues = stored_native_ancestor_declarations(reader, child)
    assert declarations == () and any(
        "differs from supplied source pin" in issue for issue in issues
    )
    payload["projection_digest"] = parent.ref.projection_digest
    payload["declarations"] = []
    declarations, issues = stored_native_ancestor_declarations(reader, child)
    assert declarations == () and any(
        "function role preparation unavailable" in issue for issue in issues
    )


def test_descendant_view_preserves_section_roles_and_scope_without_sibling_leakage():
    from dataclasses import replace

    from corpus_structure.methods.math.methods import MathSection
    from corpus_structure.methods.math.native import native_request_analysis

    root = {"self_ref": "#/groups/0", "label": "section", "children": []}
    rows: list[dict[str, Any]] = [root]
    pieces = []
    parts = []
    offset = 0
    formulas = {}

    def group(ref, parent):
        value = {
            "self_ref": ref,
            "label": "section",
            "parent": {"$ref": parent["self_ref"]},
            "children": [],
        }
        parent["children"].append({"$ref": ref})
        rows.append(value)
        return value

    def add(text, parent, formula=None):
        nonlocal offset
        pointer = f"#/texts/{len(pieces)}"
        value = {
            "self_ref": pointer,
            "label": "text" if formula is None else "formula",
            "text": text,
            "orig": text,
            "parent": {"$ref": parent["self_ref"]},
        }
        parent["children"].append({"$ref": pointer})
        rows.append(value)
        pieces.append(
            dict(
                kind="native_text",
                item_ref=pointer,
                source_field="text",
                start=offset,
                end=offset + len(text),
            )
        )
        parts.append(text)
        offset += len(text)
        if formula is not None:
            formulas[formula] = pointer

    add("Let ", root)
    add("x", root, "root_x")
    add(". ", root)
    add("f(t)=t", root, "root_f")
    add(". ", root)
    child = group("#/groups/1", root)
    add("Let ", child)
    add("y", child, "child_y")
    add(". ", child)
    add("g(t)=t", child, "child_g")
    add(". ", child)
    add("f(2)", child, "child_f_call")
    add(". ", child)
    add("g(2)", child, "child_g_call")
    add(". ", child)
    grandchild = group("#/groups/2", child)
    add("y", grandchild, "grandchild_y")
    add(". ", grandchild)
    add("g(2)", grandchild, "grandchild_g_call")
    add(". ", grandchild)
    sibling = group("#/groups/3", root)
    add("x", sibling, "sibling_x")
    add(". ", sibling)
    add("y", sibling, "sibling_y")
    add(". ", sibling)
    add("f(2)", sibling, "sibling_f_call")
    add(". ", sibling)
    add("g(2)", sibling, "sibling_g_call")
    add(".", sibling)
    source = PreparedSourceView(
        replace(view().ref, membership="descendants"),
        "".join(parts),
        tuple(pieces),
        tuple(rows),
        (),
        dict(
            formula_outcomes=[
                dict(pointer=pointer, outcome="succeeded") for pointer in formulas.values()
            ],
            inline_coverage="complete",
            cell_coverage="complete",
        ),
    )
    reader = Reader()
    reader.view = source
    reader.views = {7: source}
    run = run_for(reader)
    ctx = context_for(reader)
    unit = UnitView(UnitRef(TaskUnitType.SOURCE_VIEW, 7, source.ref.key), run, source_view_id=7)
    rule = NativeDomainRule(
        rule_id="proof-heading-1", pattern=r"^Proof\.", statement_kind="proof", scope_role="proof"
    )
    section = MathSection(native_domain_rules=(rule,))
    weak = ExtractMath().run([unit], ExtractMathConfig(math=section), ctx)[0]
    record = next(o.payload for o in weak.observations if o.kind is ObservationKind.RECORD)
    outcomes = {item["pointer"]: item["outcome"] for item in record.items}
    assert outcomes[formulas["child_f_call"]] == "ok"
    assert outcomes[formulas["child_g_call"]] == "ok"
    assert outcomes[formulas["grandchild_g_call"]] == "ok"
    assert outcomes[formulas["sibling_f_call"]] == "ok"
    assert outcomes[formulas["sibling_g_call"]] == "ambiguous"
    demanded = native_request_analysis(source, None, "interpretation", domain_rules=(rule,))
    assert {item["pointer"]: item["outcome"] for item in demanded.items} == outcomes
    reader.store("extract.math", weak)
    reader.store(
        "normalize.formula",
        NormalizeFormula().run([unit], NormalizeFormulaConfig(math=section), ctx)[0],
    )
    scoped = SymbolScope().run(
        [unit],
        SymbolScopeConfig(
            math=section, binders=Binders(sentence_initial=("let",)), sentences=SentenceConfig()
        ),
        ctx,
    )[0]
    scopes = {
        o.payload.source_pointer: o.payload
        for o in scoped.observations
        if o.kind is ObservationKind.SCOPE and o.payload.symbol in {"x", "y"}
    }
    assert scopes[formulas["sibling_x"]].outcome == "resolved"
    assert scopes[formulas["sibling_x"]].scope_pointer == root["self_ref"]
    assert scopes[formulas["grandchild_y"]].outcome == "resolved"
    assert scopes[formulas["grandchild_y"]].scope_pointer == child["self_ref"]
    assert scopes[formulas["sibling_y"]].outcome == "unresolved"
    # Weak context preparation also retains declaration ownership inside this view.
    from corpus_structure.methods.math.native import native_context_result

    context = native_context_result(
        unit,
        source,
        SymbolScopeConfig(
            math=section, binders=Binders(sentence_initial=("let",)), sentences=SentenceConfig()
        ),
        reader,
    )
    declarations = context.observations[0].payload.declarations
    assert next(d.scope_pointer for d in declarations if d.symbol == "f") == root["self_ref"]
    assert next(d.scope_pointer for d in declarations if d.symbol == "g") == child["self_ref"]


def test_native_layout_uses_explicit_sentence_configuration_and_scoped_cache():
    import pytest

    source = view()
    configuration = SentenceConfig()
    first = source.layout_for(configuration)
    assert source.layout_for(configuration) is first
    with pytest.raises(OSError):
        source.layout_for(
            configuration.model_copy(update={"model": "native_sentence_control_missing_model"})
        )


def test_native_frame_refuses_unresolved_sentence_configuration():
    import pytest

    from corpus_structure.methods.math.native import native_proposal_packet

    with pytest.raises(ValueError, match="resolved admitted sentence configuration"):
        native_proposal_packet(Reader(), 7, None, {"sentences": "segment.sentences/default"})


def test_partial_recognition_preserves_usable_consumers_without_complete_context(monkeypatch):
    import json
    from dataclasses import replace

    from corpus_structure.core.vocab import ObservationOutcome
    from corpus_structure.methods.math import native
    from corpus_structure.methods.math.methods import MathSection
    from corpus_structure.semantic import proposals
    from corpus_structure.semantic.identity import canonical_bytes

    rule = NativeDomainRule(
        rule_id="proof-heading-1",
        pattern=r"^Proof\.",
        statement_kind="proof",
        scope_role="proof",
    )
    section = MathSection(native_domain_rules=(rule,))
    configuration = SymbolScopeConfig(
        math=section, binders=Binders(sentence_initial=("let",)), sentences=SentenceConfig()
    )
    for recognition in ("partial", "unknown"):
        reader = Reader()
        reader.view.health["inline_coverage"] = recognition
        unit = UnitView(
            UnitRef(TaskUnitType.SOURCE_VIEW, 7, reader.view.ref.key),
            run_for(reader),
            source_view_id=7,
        )
        ctx = context_for(reader)
        weak = ExtractMath().run([unit], ExtractMathConfig(math=section), ctx)[0]
        assert weak.outcome is ObservationOutcome.PRODUCED
        assert len([o for o in weak.observations if o.kind is ObservationKind.MENTION]) == 3
        assert weak.coverage[0].outcome == "partial"
        reader.store("extract.math", weak)
        normalized = NormalizeFormula().run([unit], NormalizeFormulaConfig(math=section), ctx)[0]
        assert normalized.outcome is ObservationOutcome.PRODUCED
        assert len([o for o in normalized.observations if o.kind is ObservationKind.VALUE]) == 2
        assert normalized.coverage[0].outcome == "partial"
        reader.store("normalize.formula", normalized)
        monkeypatch.setattr(
            reader,
            "source_view_coverage",
            lambda source_view_id, method, weak=weak: (
                SourceCoverageReading(weak.coverage[0], 42, "fixture", 0),
            ),
        )
        scoped = SymbolScope().run([unit], configuration, ctx)[0]
        assert scoped.outcome is ObservationOutcome.PRODUCED
        assert scoped.coverage[0].outcome == "partial"
        assert any(o.kind is ObservationKind.SCOPE for o in scoped.observations)

        context_only = native.native_context_result(unit, reader.view, configuration, reader)
        assert context_only.coverage[0].outcome == "partial"
        context = context_only.observations[0].payload
        assert context.declarations
        assert any(f"inline recognition context {recognition}" in issue for issue in context.issues)

        requested = native.native_request_analysis(
            reader.view,
            reader.prepared,
            "interpretation",
            pointer="#/texts/3",
            domain_rules=(rule,),
        )
        item = requested.items[0]
        assert item["availability"] == "available" and item["outcome"] == "ok"
        assert item["context"]["coverage"] == "unknown"
        assert any(
            f"inline recognition context {recognition}" in issue
            for issue in item["context"]["issues"]
        )
        assert item["stages"]["symbolic"]["work"] == "not_requested"

        # Keep real packet source preparation; the unrelated schema boundary is controlled here.
        monkeypatch.setattr(reader, "guideline", lambda: "Source-only packet control")

        def packet_boundary(prepared, frame, **values):
            return proposals.ProposalPacket(
                prepared.release_id,
                frame,
                b"{}",
                values["guideline"],
                canonical_bytes(values["configuration"]),
                native_observations=values["native_observations"],
            )

        monkeypatch.setattr(proposals, "proposal_packet", packet_boundary)
        packet = native.native_proposal_packet(
            reader, 7, reader.prepared, {"sentences": SentenceConfig().model_dump(mode="json")}
        )
        frame = packet.frame
        assert isinstance(frame, proposals.NativeProposalFrame)
        assert frame.text == reader.view.text
        assert json.loads(frame.native_context)["health"]["inline_coverage"] == recognition
        assert len(packet.hash) == 64

        parent = replace(
            reader.view,
            ref=replace(reader.view.ref, id=6, key="parent", section_pointer="#/groups/parent"),
        )
        child = replace(
            reader.view, ancestors=({"self_ref": "#/groups/parent", "label": "section"},)
        )
        reader.views = {6: parent, 7: child}
        parents, issues = native.ancestor_views(reader, child)
        assert parents == (parent,)
        assert any(f"inline recognition context {recognition}" in issue for issue in issues)
