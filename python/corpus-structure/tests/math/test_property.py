"""The tree/token property (D1 §6.2; ingest and math §6 P0-I-2a; KEYS-01; record s5.keys-property).

For every value the grammar reads, the tree printer's form equals `core/tex.py`'s token form of the
value as given. The token form is the key, so a disagreement is listed with its cause and fixed on
the tree side; a new one fails these tests.

- **Corpus layer**: every span the grammar reads on the four spike pages' production renditions
  (the 78-page run is `test_coverage.py`'s). S5-A: 0 disagreements over 28,370 read spans.
- **Generated layer**: Hypothesis `from_lark` draws strings from the assembled grammar (start
  `any_value`, printable ASCII), with explicit strategies for the generated macro terminals
  (`GEN_SET`, `GEN_OP`, `GEN_STYLE`) from the Siegrist table. `from_lark` drives the dynamic-lexer
  grammar and its whole-name lookahead terminals, so no fallback strategy is needed. S5-A: 2,837
  of 3,000 generated strings read, 0 disagreements.
"""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from hypothesis.extra.lark import from_lark

from corpus_structure.core import tex
from corpus_structure.core.evidence import MacroDef
from corpus_structure.methods.math import grammar as G
from corpus_structure.methods.math.printer import print_tree

pytestmark = pytest.mark.filterwarnings("error::sympy.utilities.exceptions.SymPyDeprecationWarning")


def agrees(result: G.MathResult, given_text: str) -> tuple[bool, str, str]:
    assert result.tree is not None
    printed = print_tree(result.tree, result.latex, result.macros, result.tail)
    token = tex.token_form(given_text, result.macros)
    return printed == token, printed, token


@pytest.mark.parametrize(
    "latex",
    [
        "b^{2} \\, \\sigma^2",
        "\\left( x \\right)",
        "\\R \\setminus \\{0\\}",
        "\\E(X) = \\mu",
        "a + b \\, Z",
        "\\sigma_{X_1}^{2}",
        "e^{\\mu}",
        "a \\big/ b",
        "\\Bigl( x \\Bigr)",
        "\\mu x + \\mu_{x}",  # a control word before a letter keeps its space
        "x + y,",  # T1: the dropped tail is printed after the trimmed reading
        "\\begin{align} f(x) & = x^2 \\\\ & = y \\end{align}",  # T2: an outer environment
        "X_n \\to X \\text{ as  } n \\to \\infty",  # T3: a text-mode argument from the source
        "\\text{var}(X) + \\operatorname{cov} (X, Y)",  # T3: operator words
    ],
)
def test_the_printer_agrees_on_cases(latex: str, env: Any) -> None:
    macros = tex.effective_macros({}, env.macros)
    result = G.parse(latex, "any_value", macros)
    assert result.tree is not None, result.failure
    ok, printed, token = agrees(result, latex)
    assert ok, (printed, token)


def test_corpus_layer_on_the_spike_pages(spike_pages: dict[str, Any]) -> None:
    read = 0
    disagreements = []
    for page in spike_pages.values():
        for reading in page.readings:
            if reading.result.tree is None:
                continue
            read += 1
            ok, printed, token = agrees(reading.result, page.content.text(reading.span.segment))
            if not ok:
                disagreements.append((page.page, reading.span.segment.start, printed, token))
    print(f"\ntree/token property, spike pages: {read} read spans, {len(disagreements)} disagree")
    assert read > 900
    assert disagreements == []


def _strategy(env: Any) -> tuple[st.SearchStrategy[str], dict[str, MacroDef]]:
    macros = tex.effective_macros({}, env.macros)
    classes = G.classify(macros)
    parser = G.parser_for(classes).lark
    explicit = {
        "GEN_SET": st.sampled_from([n for n, _ in classes.sets]),
        "GEN_OP": st.sampled_from([n for n, _ in classes.ops]),
        "GEN_STYLE": st.sampled_from([n for n, _ in classes.styles]),
    }
    alphabet = st.characters(min_codepoint=32, max_codepoint=126)
    return from_lark(parser, start="any_value", explicit=explicit, alphabet=alphabet), macros


def test_generated_layer(env: Any) -> None:
    strategy, macros = _strategy(env)
    counts = {"generated": 0, "read": 0}

    @settings(suppress_health_check=list(HealthCheck), deadline=None)
    @given(strategy)
    def check(latex: str) -> None:
        counts["generated"] += 1
        result = G.parse(latex, "any_value", macros)
        if result.tree is None:
            return
        counts["read"] += 1
        ok, printed, token = agrees(result, latex)
        assert ok, (latex, printed, token)

    check()
    print(f"\ntree/token property, generated: {counts}")
    assert counts["read"] > 0
