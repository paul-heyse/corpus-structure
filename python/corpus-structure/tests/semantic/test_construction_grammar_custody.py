"""Owned prose resources and unsupported lexical alternatives fail before reuse."""

import pytest

from corpus_structure.semantic.constructions import forest
from corpus_structure.semantic.constructions.lexical import (
    PositionedTerminal,
    ProtectedAtom,
    classify,
)
from corpus_structure.semantic.file_custody import FileCustodyError
from semantic.prose_regex_oracle import _regex_parser_oracle


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


@pytest.mark.parametrize(
    ("text", "atoms"),
    [
        ("Every trial does not succeed.", ()),
        ('Ada says "Rain may fall."', ()),
        ("Not every\r\ntrial succeeds.", ()),
        ("\N{GREEK SMALL LETTER ALPHA} uses \N{GREEK SMALL LETTER BETA}.", ()),
        ("x + y uses x + y.", (ProtectedAtom(0, 5, "first"), ProtectedAtom(11, 16, "second"))),
        ("A uses  .", (ProtectedAtom(7, 8, "blank"),)),
    ],
)
def test_supplied_terminal_candidate_preserves_independent_regex_forest(text, atoms):
    # This bounded differential control complements, and cannot replace, the
    # coordinator's actual book-region equality/adoption experiment.
    observations = classify(text, atoms)
    actual = forest.prepared_parser(text, atoms, terminals=observations).parse(text)
    expected = _regex_parser_oracle(text, atoms, terminals=observations).parse(text)
    assert _forest_shape(actual) == _forest_shape(expected)
    actual_reducer = forest.PackedReducer(text, atoms)
    expected_reducer = forest.PackedReducer(text, atoms)
    assert actual_reducer.transform(actual) == expected_reducer.transform(expected)
    for name in ("terms", "choices", "syntax", "positions", "uninterpreted", "sequences"):
        assert getattr(actual_reducer, name) == getattr(expected_reducer, name)


def _forest_shape(root):
    """Ordered SPPF graph, including sharing, without expanding derivations."""
    from lark.parsers.earley_forest import PackedNode, SymbolNode, TokenNode

    identities: dict[int, int] = {}
    records: list[object] = []

    def rule(value):
        return (
            str(value.origin),
            tuple(str(item) for item in value.expansion),
            str(value.alias),
            value.order,
            value.options.keep_all_tokens,
            value.options.expand1,
            value.options.priority,
            value.options.empty_indices,
        )

    def visit(node):
        if node is None:
            return None
        key = id(node)
        if key in identities:
            return identities[key]
        ordinal = identities[key] = len(records)
        records.append(None)
        if isinstance(node, TokenNode):
            token = node.token
            record = (
                "token",
                token.type,
                str(token),
                token.start_pos,
                token.end_pos,
                token.line,
                token.column,
                token.end_line,
                token.end_column,
                node.priority,
            )
        elif isinstance(node, PackedNode):
            record = (
                "packed",
                rule(node.rule),
                node.start,
                node.priority,
                visit(node.left),
                visit(node.right),
            )
        elif isinstance(node, SymbolNode):
            label = (rule(node.s[0]), node.s[1]) if node.is_intermediate else str(node.s)
            record = (
                "symbol",
                node.is_intermediate,
                label,
                node.start,
                node.end,
                node.priority,
                tuple(visit(child) for child in node.children),
            )
        else:
            raise AssertionError("unexpected native forest node " + type(node).__name__)
        records[ordinal] = record
        return ordinal

    visit(root)
    return records


def test_regions_share_one_compile_without_retaining_or_replacing_another_matcher(monkeypatch):
    forest._grammar_prototype.cache_clear()
    original, constructed = forest.Lark, []

    def compile_grammar(*args, **kwargs):
        constructed.append(args[0])
        return original(*args, **kwargs)

    monkeypatch.setattr(forest, "Lark", compile_grammar)
    first = forest.prepared_parser("Rain falls.", ())
    second = forest.prepared_parser("All trials succeed.", ())
    before = _forest_shape(first.parse("Rain falls."))
    assert _forest_shape(second.parse("All trials succeed.")) != before
    assert _forest_shape(first.parse("Rain falls.")) == before
    assert len(constructed) == 1
    with pytest.raises(ValueError, match="different source region"):
        first.parse("All trials succeed.")
    forest._grammar_prototype.cache_clear()


def test_authored_native_terminal_keeps_its_native_matcher():
    imports = ", ".join(["clause", *forest.LEXICAL, "ATOM"])
    grammar = f'%import .prose ({imports})\nstart: WORD BANG\nBANG: "!"'
    text = "alpha!"
    actual = forest.prepared_parser(text, (), grammar).parse(text)
    expected = _regex_parser_oracle(text, (), grammar).parse(text)
    assert _forest_shape(actual) == _forest_shape(expected)


@pytest.mark.parametrize(
    "row",
    [
        PositionedTerminal("UNKNOWN", 0, 5, "alpha"),
        PositionedTerminal("WORD", 0, 5, "changed"),
        PositionedTerminal("WORD", 0, 0, ""),
        PositionedTerminal("WORD", 0, 6, "alpha!"),
    ],
)
def test_supplied_matcher_rejects_nonexact_observations_before_parse(row):
    with pytest.raises(ValueError, match="exact original source"):
        forest.prepared_parser("alpha", (), terminals=(row,))
