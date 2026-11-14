"""Real spawned annotation retains exact source coordinates and explicit availability."""

from dataclasses import asdict

import pytest

from corpus_structure.core.work import drive_prepared_work
from corpus_structure.ingest.annotations import AnnotationInput, AnnotationProfile
from corpus_structure.ingest.pdf_hierarchy import ProjectedPiece
from corpus_structure.ingest.sentences import Block, SentenceConfig, pipeline, prepare_layout
from corpus_structure.methods.characterization_resources import ProviderExecution
from corpus_structure.semantic.cpu_execution import CPUExecutionScope
from corpus_structure.semantic.native_annotations import annotation_work
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.source_contexts import NativeSourcePin
from semantic.primary_formal_fixture import prepared as prepared


def _plan(work):
    (reply,) = yield (work,)
    return reply


def test_actual_hosted_annotation_preserves_native_atoms_pieces_and_token_positions(prepared):
    profile = AnnotationProfile()
    text = "Let x+y be a value [3]."
    start = 23
    block = Block(text, ((4, 7),), (), ((19, 22),))
    layout = prepare_layout(pipeline(profile.configuration), block, start=start)
    source = NativeSourcePin(
        7,
        "source:7",
        ProductReference(17, "integrated", "a" * 64),
        "#/groups/7",
        "descendants",
        "b" * 64,
        "c" * 64,
        3,
    )
    item = AnnotationInput(
        source,
        "paragraph:7",
        "paragraph",
        block,
        layout,
        (ProjectedPiece("#/texts/7", start, start + len(text), "native_text"),),
    )
    cpu = CPUExecutionScope(prepared)
    execution = ProviderExecution(cpu.budget, cpu.policy)
    try:
        result = drive_prepared_work(
            _plan(annotation_work(execution, (item,), profile, lambda: None)), lambda: None
        )
        (product,) = result.require_available()
        assert product.source == source
        assert product.native_pieces == item.native_pieces
        assert tuple((t.start, t.end, t.space, t.role) for t in product.tokens) == tuple(
            (t.start, t.end, t.space, t.role) for t in layout.tokens
        )
        assert tuple(
            text[t.start - start : t.end - start] for t in product.tokens if t.role != "prose"
        ) == ("x+y", "[3]")
        assert product.layout_digest
        assert all(row.status in {"complete", "not_applicable"} for row in product.availability)
        assert all(not hasattr(value, "vocab") for value in asdict(product).values())
    finally:
        execution.close()
        cpu.close()
    assert execution.budget.used_bytes == 0


def test_spawned_annotation_profile_refusal_retains_structured_availability(prepared):
    cpu = CPUExecutionScope(prepared)
    execution = ProviderExecution(cpu.budget, cpu.policy)
    profile = AnnotationProfile(SentenceConfig(spacy_version="0.0.0"))
    try:
        from corpus_structure.ingest.sentences import SentenceConfigError

        with pytest.raises(SentenceConfigError, match=r"0\.0\.0"):
            annotation_work(execution, (), profile, lambda: None)
        assert not execution.native_group._serving
    finally:
        execution.close()
        cpu.close()
    assert execution.budget.used_bytes == 0


def test_annotation_handle_forwards_flush_and_ownership(monkeypatch):
    """The driver must flush queued native work before waiting for its reply."""
    from concurrent.futures import Future
    from time import monotonic
    from types import SimpleNamespace

    from corpus_structure.core.work import PreparedWork
    from corpus_structure.semantic import native_annotations

    events = []

    class Queued:
        future = Future()

        def flush(self):
            events.append("flush")
            self.future.set_result(None)

        def collect(self):
            assert self.future.done()
            return SimpleNamespace(payload={"documents": []}, startup={})

        def cancel(self):
            events.append("cancel")

        def retire(self):
            events.append("retire")
            return True

    queued = Queued()
    nlp = SimpleNamespace(observe=lambda startup: None, decode=lambda documents: [])

    def annotate(inputs, profile, *, require_complete, processed_docs):
        assert inputs == () and processed_docs == []
        return ("owned-result",)

    monkeypatch.setattr(native_annotations, "annotate", annotate)
    wrapped = native_annotations._AnnotationHandle(queued, (), None, nlp, False)
    deadline = monotonic() + 2

    def check_active():
        if monotonic() >= deadline:
            raise TimeoutError("annotation work remained queued without flush")

    result = drive_prepared_work(_plan(PreparedWork(lambda: wrapped)), check_active)
    assert result.products == ("owned-result",)
    assert events == ["flush", "retire"]
    wrapped.cancel()
    assert events[-1] == "cancel"
