"""Owned prose resources and unsupported lexical alternatives fail before reuse."""

import pytest

from corpus_structure.semantic.constructions import forest
from corpus_structure.semantic.constructions.lexical import (
    PositionedTerminal,
    ProtectedAtom,
    classify,
)
from corpus_structure.semantic.file_custody import FileCustodyError


def test_parser_cache_rechecks_grammar_content_and_accepts_equal_touch(tmp_path, monkeypatch):
    grammar = tmp_path / "prose.lark"
    grammar.write_text("start: WORD")
    owner = forest._grammar_resource
    resource = owner(grammar)
    monkeypatch.setattr(forest, "_grammar_resource", lambda path: owner(grammar))
    parser = object()
    calls = []

    def prepared(*args):
        calls.append(args[3])
        return parser

    monkeypatch.setattr(forest, "_prepared_parser", prepared)
    assert forest.prepared_parser("text", ()) is parser
    grammar.touch()
    assert forest.prepared_parser("text", ()) is parser
    assert calls == [resource.digest, resource.digest]
    grammar.write_text("start: OTHER")
    with pytest.raises(FileCustodyError, match="restart"):
        forest.prepared_parser("text", ())
    assert len(calls) == 2


def test_same_terminal_alternative_extents_refuse_instead_of_losing_a_reading():
    with pytest.raises(ValueError, match="same-terminal same-start"):
        forest.prepared_parser(
            "alpha",
            (),
            terminals=(
                PositionedTerminal("WORD", 0, 2, "al"),
                PositionedTerminal("WORD", 0, 5, "alpha"),
            ),
        )


def test_classifier_owns_one_extent_per_terminal_start_across_protected_regions():
    text = "Every alpha is x and each beta is y."
    atom = ProtectedAtom(text.index("x"), text.index("x") + 1, "formula:x")
    rows = classify(text, (atom,))
    keys = [(row.terminal, row.start) for row in rows]
    assert len(keys) == len(set(keys))
    assert all(row.end <= atom.start or atom.end <= row.start for row in rows)
    assert [(row.start, row.end, row.text) for row in rows if row.terminal == "QUANT"] == [
        (0, 5, "Every"),
        (21, 25, "each"),
    ]
