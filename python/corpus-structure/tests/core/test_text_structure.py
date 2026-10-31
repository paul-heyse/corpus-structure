from __future__ import annotations

import pytest

from corpus_structure.core.evidence import MacroDef
from corpus_structure.core.tex import expand, tokens
from corpus_structure.core.text_structure import capture_text, parse_view
from corpus_structure.ingest.macros import read_macros


def test_complete_capture_and_explicit_inner_view(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("lexical demand entered native structure")

    monkeypatch.setattr("corpus_structure.core.text_structure._structure", forbidden)
    source = "  \\(  x % $prose \\)  "
    result = capture_text(source, start=10, opener=r"\(", closer=r"\)")
    assert "".join(t.text for t in result.lexical) == source
    assert [(t.start, t.end) for t in result.lexical][:2] == [(10, 12), (12, 14)]
    # Explicit delimiters only strip when they directly enclose the segment.
    assert result.view.text == r"\(  x % $prose \)"
    view = parse_view(r"\(  x % $prose \)", start=20, opener=r"\(", closer=r"\)")
    assert (view.start, view.end, view.text) == (24, 34, "x % $prose")
    assert parse_view("$prose$", opener="$", closer="$").text == "$prose$"


def test_native_syntax_structure_and_unrecognized_text_keep_exact_capture() -> None:
    source = r"\frac{a}{b}"
    result = capture_text(source, structure=True)
    fraction = next(n for n in result.nodes if n.kind == "fraction")
    assert (fraction.start, fraction.end) == (0, len(source))
    assert result.structure_outcome == "available"
    mixed = source + " % $prose"
    unsupported = capture_text(mixed, structure=True)
    assert "".join(t.text for t in unsupported.lexical) == mixed
    assert unsupported.structure_outcome != "available"
    assert unsupported.issues


def test_unknown_and_invalid_keep_the_total_partition() -> None:
    for source in (r"\nonesuch{x}", r"\frac{a"):
        result = capture_text(source, structure=True)
        assert result.structure_outcome != "available"
        assert "".join(t.text for t in result.lexical) == source
        assert result.issues


def test_retired_macro_argument_writer_does_not_fabricate_structure() -> None:
    source = r"\foo[y]{x}"
    result = capture_text(
        source,
        structure=True,
        macros={r"\foo": MacroDef(nargs=2, default="D", body="#1+#2")},
    )
    assert "".join(t.text for t in result.lexical) == source
    assert result.structure_outcome != "available"
    assert result.nodes == ()


def test_definition_events_and_repeated_argument_default_derivation() -> None:
    source = (
        r"\newcommand{\f}[2][D]{#1+#2+#2}\providecommand{\f}{bad}\renewcommand{\f}[2][Q]{#1+#2+#2}"
    )
    read = read_macros(source, source_ref="page:defs")
    assert [event.status for event in read.events] == ["replaced", "ignored", "accepted"]
    event = read.events[-1]
    assert source[event.command.start : event.command.end] == r"\renewcommand"
    assert "".join(t.text for t in event.body_tokens) == "#1+#2+#2"
    assert source[event.default_tokens[0].start : event.default_tokens[0].end] == "Q"
    result = expand(tokens(r"\f{x}"), read.table, source_ref="canonical", bindings=read.bindings)
    assert "".join(result.tokens) == "Q+x+x"
    q, _, x1, _, x2 = result.pieces
    assert q.origins[0].source_ref == "page:defs"
    assert q.origins[0].start == source.index("Q")
    assert [(x.start, x.end) for x in (x1, x2)] == [(2, 3), (4, 5)]
    assert x1.origins[0] == x2.origins[0]
    assert [(o.source_ref, o.start, o.end) for o in x1.origins if o.source_ref == "canonical"] == [
        ("canonical", 3, 4)
    ]
    assert result.invocations[0].definition is not None
    assert result.invocations[0].definition.source_ref == "page:defs"


def test_generated_operator_is_derived_from_definition_not_fake_body_offsets() -> None:
    source = r"\DeclareMathOperator{\op}{name}"
    read = read_macros(source, source_ref="page:defs")
    result = expand(tokens(r"\op"), read.table, bindings=read.bindings)
    assert "".join(result.tokens) == r"\operatorname{name}"
    assert all(
        o.role == "derived-body" and (o.start, o.end) == (0, len(source))
        for piece in result.pieces
        for o in piece.origins
    )


def test_expansion_bound_retains_invocation_and_arguments() -> None:
    result = expand(tokens(r"\f{x}"), {r"\f": MacroDef(nargs=1, body=r"\f{#1}")})
    assert "".join(result.tokens) == r"\f{x}"
    assert result.unexpanded == (r"\f",)
    assert result.invocations[-1].outcome == "depth_bound"


def test_native_missing_syntax_tree_is_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    from corpus_structure.core.vocab import ParseOutcome
    from corpus_structure.methods.math import grammar

    monkeypatch.setattr(
        grammar, "syntax", lambda *args, **kwargs: grammar.MathResult("x", "any_value", ParseOutcome.FAILED)
    )
    result = capture_text("x", structure=True)
    assert result.structure_outcome == "invalid"
    assert result.issues == ("no_syntax_tree",)
    assert [t.text for t in result.lexical] == ["x"]


def test_undefined_macro_retains_explicit_absent_definition() -> None:
    result = expand(tokens(r"\absent{x}"), {})
    assert "".join(result.tokens) == r"\absent{x}"
    assert result.invocations[0].name == r"\absent"
    assert result.invocations[0].outcome == "undefined"
    assert result.invocations[0].definition is None
