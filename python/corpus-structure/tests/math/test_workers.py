"""Focused controls for the full-corpus oracle's process lifecycle."""

import multiprocessing
import os
import threading
import time

import pytest
from math_support import PageWorkError, _run_pages, coverage_all, coverage_rows
from math_worker_cases import probe, reading_positions


def test_spawn_with_parent_thread_and_empty_input():
    done = threading.Event()
    thread = threading.Thread(target=done.wait)
    thread.start()
    try:
        assert _run_pages(probe, []) == {}
        got = _run_pages(probe, ["first", "second"], workers=1, timeout=15)
        assert set(got) == {"first", "second"}
        assert all(pid != os.getpid() and method == "spawn" for _, pid, method in got.values())
    finally:
        done.set()
        thread.join()


@pytest.mark.parametrize("page", ["error", "exit"])
def test_worker_failure_identifies_page(page):
    before = {p.pid for p in multiprocessing.active_children()}
    with pytest.raises(PageWorkError, match=page) as failure:
        _run_pages(probe, [page], workers=1, timeout=15)
    assert "incomplete pages" in " ".join(failure.value.__notes__)
    assert_settled(before)


def test_deadline_kills_stalled_worker_and_preserves_completed_diagnostics():
    before = {p.pid for p in multiprocessing.active_children()}
    with pytest.raises(PageWorkError, match="deadline") as failure:
        _run_pages(probe, ["complete", "hang", "unsubmitted"], workers=1, timeout=2)
    note = " ".join(failure.value.__notes__)
    assert "completed pages: ['complete']" in note
    assert "incomplete pages: ['hang', 'unsubmitted']" in note
    assert "not submitted pages: ['unsubmitted']" in note
    assert_settled(before)


def assert_settled(before):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if not {p.pid for p in multiprocessing.active_children()} - before:
            break
        time.sleep(0.02)
    assert not {p.pid for p in multiprocessing.active_children()} - before


def test_interruption_remains_interruption():
    before = {p.pid for p in multiprocessing.active_children()}
    with pytest.raises(KeyboardInterrupt, match="deliberate interruption") as failure:
        _run_pages(probe, ["interrupt"], workers=1, timeout=15)
    assert "incomplete pages" in " ".join(failure.value.__notes__)
    assert_settled(before)


def test_coverage_does_not_extract_values_or_scopes(monkeypatch):
    import math_support

    def unwanted(*args, **kwargs):
        raise AssertionError("coverage must not perform downstream extraction")

    monkeypatch.setattr(math_support, "formula_values", unwanted)
    monkeypatch.setattr(math_support, "extract", unwanted)
    monkeypatch.setattr(math_support, "resolve_scopes", unwanted)
    rows = coverage_rows("special/LocationScale.html")
    assert rows
    assert all(row.start < row.end for row in rows)


def test_spawned_vendored_page_returns_real_span_rows():
    got = coverage_all(["special/LocationScale.html"])
    assert set(got) == {"special/LocationScale.html"}
    rows = got["special/LocationScale.html"]
    assert isinstance(rows, list)
    assert rows and all(row.start < row.end for row in rows)


def test_keyed_payloads_preserve_page_identity_and_failure_diagnostics():
    got = _run_pages(probe, {"page-a": "same", "page-b": "same"}, workers=1, timeout=15)
    assert set(got) == {"page-a", "page-b"}
    assert [value[0] for value in got.values()] == ["same", "same"]
    with pytest.raises(PageWorkError, match="source-page") as failure:
        _run_pages(probe, {"source-page": "error"}, workers=1, timeout=15)
    assert "incomplete pages: ['source-page']" in " ".join(failure.value.__notes__)


def test_duplicate_page_jobs_are_rejected():
    with pytest.raises(ValueError, match="distinct page identities"):
        _run_pages(probe, ["same", "same"])


def small_page():
    from math_support import PageContent

    from corpus_structure.core.evidence import RenditionContent, Segment
    from corpus_structure.core.vocab import SegmentKind

    text = r"Let \(x\) be real. Then \(x + 1\) is real and \(x = 1\)."
    spans = []
    for latex in (r"\(x\)", r"\(x + 1\)", r"\(x = 1\)"):
        start = text.index(latex)
        spans.append(
            Segment(
                kind=SegmentKind.MATH_INLINE,
                start=start,
                end=start + len(latex),
                attrs={"open": r"\(", "close": r"\)"},
            )
        )
    split = text.index("Then")
    sentences = (
        Segment(kind=SegmentKind.SENTENCE, start=0, end=split - 1),
        Segment(kind=SegmentKind.SENTENCE, start=split, end=len(text)),
    )
    paragraph = Segment(
        kind=SegmentKind.PARAGRAPH, start=0, end=len(text), children=(*spans, *sentences)
    )
    unit = Segment(kind=SegmentKind.UNIT, start=0, end=len(text), children=(paragraph,))
    content = RenditionContent(
        canonical_text=text,
        document=Segment(kind=SegmentKind.DOCUMENT, start=0, end=len(text), children=(unit,)),
    )
    return PageContent("independent-small-page", content, {})


def test_real_spawn_transports_each_stage_without_preparation_or_reparsing():
    import pickle
    from types import MappingProxyType

    from lark import Token

    from math_support import extract_readings, read_content, scope_extraction

    from corpus_structure.core.vocab import ParseOutcome, ScopeExtent
    from corpus_structure.methods.math import _tree
    from corpus_structure.methods.math.printer import print_tree

    page = small_page()
    ordinary_token = Token("CONTROL", "x", 0, 1, 1, 1, 2, 1)
    ordinary_pickle = pickle.dumps(ordinary_token)
    readings = _run_pages(read_content, {page.page: page}, workers=1, timeout=30)[page.page]
    assert [r.span.latex for r in readings] == ["x", "x + 1", "x = 1"]
    assert all(r.prepared is None for r in readings)
    assert all(isinstance(r.result.macros, MappingProxyType) for r in readings)
    assert all(r.result.status is ParseOutcome.OK for r in readings)
    positions = []
    printed = []
    for reading in readings:
        result = reading.result
        assert result.tree is not None
        printed.append(print_tree(result.tree, result.latex, result.macros))
        positions.append([
            (t.start_pos, t.end_pos, t.line, t.column, t.end_line, t.end_column)
            for t in _tree.leaves(result.tree)
        ])
    assert positions == [
        [(0, 1, 1, 1, 1, 2)],
        [(0, 1, 1, 1, 1, 2), (2, 3, 1, 3, 1, 4), (4, 5, 1, 5, 1, 6)],
        [(0, 1, 1, 1, 1, 2), (2, 3, 1, 3, 1, 4), (4, 5, 1, 5, 1, 6)],
    ]
    assert printed == ["x", "x+1", "x=1"]
    assert _run_pages(
        reading_positions, {page.page: readings}, workers=1, timeout=30
    )[page.page] == reading_positions(readings)
    values, extraction = _run_pages(
        extract_readings, {page.page: readings}, workers=1, timeout=30
    )[page.page]
    assert [v.value.latex for v in values] == ["x", "x + 1", "x = 1"]
    assert [(m.name, m.start, m.end) for m in extraction.mentions] == [
        ("x", 6, 7), ("x", 26, 27), ("x", 48, 49)
    ]
    assert [(r.label, r.head, r.tail, r.operator) for r in extraction.relations] == [
        ("equals", (48, 49), (52, 53), "=")
    ]
    scopes = _run_pages(
        scope_extraction, {page.page: (page, values, extraction)}, workers=1, timeout=30
    )[page.page]
    later = next(s for s in scopes if s.mention.start == 26)
    assert later.symbol == "x"
    assert later.site is not None and later.site.extent is ScopeExtent.STATEMENT
    assert page.content.text(later.site.sentence) == r"Let \(x\) be real."
    assert pickle.dumps(ordinary_token) == ordinary_pickle


def test_stages_omit_downstream_work_and_reuse_parent_products(monkeypatch):
    import math_support as support

    calls = []

    def inline(work, pages):
        calls.append(work)
        return {key: work(payload) for key, payload in pages.items()}

    def unwanted(*args, **kwargs):
        pytest.fail("unrequested mathematical work")

    monkeypatch.setattr(support, "_run_pages", inline)
    with monkeypatch.context() as guard:
        for name in ("read_spans", "formula_values", "extract", "resolve_scopes"):
            guard.setattr(support, name, unwanted)
        retained = support.retained_pages(["special/LocationScale.html"])
        assert retained["special/LocationScale.html"].content.canonical_text
    # The same parent composition used by session fixtures runs exactly one reading
    # job. Later stages are guarded against parsing and unwanted stronger work.
    source = small_page()
    with monkeypatch.context() as guard:
        for name in ("formula_values", "extract", "resolve_scopes"):
            guard.setattr(support, name, unwanted)
        readings = support.reading_pages({source.page: source})
    with monkeypatch.context() as guard:
        guard.setattr(support, "read_spans", unwanted)
        guard.setattr(support, "resolve_scopes", unwanted)
        extraction = support.extraction_pages(readings)
    with monkeypatch.context() as guard:
        for name in ("read_spans", "formula_values", "extract"):
            guard.setattr(support, name, unwanted)
        scoped = support.scoped_pages(extraction)
    assert calls == [support.read_content, support.extract_readings, support.scope_extraction]
    key = source.page
    for view in (readings[key], extraction[key], scoped[key]):
        assert view.content is source.content
        assert view.macros is source.macros
        assert view.readings is readings[key].readings
    assert scoped[key].values is extraction[key].values
    assert scoped[key].extraction is extraction[key].extraction
    assert scoped[key].scopes


def test_staged_corpus_relations_preserve_direct_page_semantics(spike_readings, spike_extraction):
    from math_support import extract_readings, read_page

    # A whole historical page includes nested and ambiguous trees and relations
    # whose heads/tails are terminal tokens. Compare their finished source data,
    # not just printed trees (printing survives missing token end positions).
    key = "special/Normal.html"
    direct = read_page(key)
    staged = spike_readings[key]

    direct_positions = reading_positions(direct.readings)
    assert reading_positions(staged.readings) == direct_positions
    assert _run_pages(
        reading_positions, {key: staged.readings}, workers=1, timeout=30
    )[key] == direct_positions
    values, extraction = extract_readings(direct.readings)
    assert extraction.relations  # this control must actually exercise relational transport
    assert spike_extraction[key].values == values
    assert spike_extraction[key].extraction == extraction
