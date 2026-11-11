"""Exact retained inline normalization maps replace consumer-side mathematical parsing."""

import pytest

from corpus_structure.methods.inline_formula_occurrences import inline_equations, inline_symbols
from corpus_structure.semantic.formal_evidence import build_formal_layer
from corpus_structure.semantic.formal_sources import (
    NORMALIZATION_RECIPE,
    mapped_formal_extents,
    normalize_inline_equation,
)
from semantic.test_formal_evidence import operation, source
from semantic.test_formal_evidence import prepared as prepared


def case(prepared, text="Z using the equation X = σZ + µ.", **options):  # noqa: RUF001 - literal mathematical sigma
    view = source((text, "text", "", ""))
    layer = build_formal_layer(view, prepared, operation(), **options)
    return view, layer, {layer.reference(12): layer}


def equations(view, layers, selection=None, max_chars=2048):
    return tuple(
        inline_equations(
            view.text,
            view.pieces,
            {item["self_ref"]: item for item in view.items},
            selection,
            max_chars=max_chars,
            primary_layers=layers,
            projection=view.ref.projection_digest,
        )
    )


def test_normalization_has_explicit_source_atoms_and_synthetic_separators():
    normalized = normalize_inline_equation("X = σZ + µ")  # noqa: RUF001 - literal mathematical sigma
    assert normalized is not None
    assert normalized.text == r"X = \sigma Z + \mu "
    assert [
        (piece.input_start, piece.input_end, piece.relation, piece.source_start, piece.source_end)
        for piece in normalized.pieces
    ] == [
        (0, 4, "exact", 0, 4),
        (4, 10, "normalized", 4, 5),
        (10, 11, "synthetic", 5, 5),
        (11, 15, "exact", 5, 9),
        (15, 18, "normalized", 9, 10),
        (18, 19, "synthetic", 10, 10),
    ]
    assert normalize_inline_equation("X = χZ + µ") is None


def test_retained_inline_reader_maps_unicode_and_second_equal_word_without_inference(
    prepared, monkeypatch
):
    from corpus_structure.methods.math import grammar
    from corpus_structure.semantic import formal_sources

    view, layer, layers = case(prepared)
    monkeypatch.setattr(
        formal_sources,
        "nominate_inline_equations",
        lambda *args, **kwargs: pytest.fail("retained read nominated source"),
    )
    monkeypatch.setattr(
        formal_sources,
        "normalize_inline_equation",
        lambda *args: pytest.fail("retained read normalized source"),
    )
    monkeypatch.setattr(
        grammar, "syntax_forest", lambda *args, **kwargs: pytest.fail("retained read parsed source")
    )
    (equation,) = equations(view, layers)
    symbols, outcome = inline_symbols(
        view.text, equation, primary_layers=layers, projection=view.ref.projection_digest
    )
    assert outcome == "parsed"
    assert [
        (symbol.start, symbol.end, view.text[symbol.start : symbol.end]) for symbol in symbols
    ] == [
        (21, 22, "X"),
        (25, 26, "σ"),  # noqa: RUF001 - literal mathematical sigma
        (26, 27, "Z"),
        (30, 31, "µ"),
    ]
    assert all(symbol.primary_node and symbol.parent_occurrence for symbol in symbols)
    root = next(
        annotation
        for annotation in layer.payload["annotations"]
        if annotation.get("native_label") == "introduced_inline_equation"
    )
    value = root["formal_input"]
    assert (
        value["representation"] == "normalized_latex"
        and value["normalization_recipe"] == NORMALIZATION_RECIPE
    )
    assert value["original_text"] == "X = σZ + µ"  # noqa: RUF001 - literal mathematical sigma
    assert {row["relation"] for row in value["correspondence"]} == {
        "exact",
        "normalized",
        "synthetic",
    }


def test_normalized_atom_cuts_and_synthetic_only_spans_never_gain_source_authority(prepared):
    _view, layer, _layers = case(prepared)
    value = next(
        annotation["formal_input"]
        for annotation in layer.payload["annotations"]
        if annotation.get("native_label") == "introduced_inline_equation"
    )
    occurrences = {
        occurrence["local_id"]: occurrence for occurrence in layer.payload["occurrences"]
    }
    with pytest.raises(ValueError, match="normalized source atom"):
        mapped_formal_extents(value, 5, 6, occurrences)
    with pytest.raises(ValueError, match="original-source"):
        mapped_formal_extents(value, 10, 11, occurrences)
    (sigma,) = mapped_formal_extents(value, 4, 10, occurrences)
    assert (sigma["start"], sigma["end"], sigma["text"]) == (25, 26, "σ")  # noqa: RUF001 - literal mathematical sigma


def test_reader_selection_requires_actual_nomination_support_and_explicit_primary(prepared):
    view, _layer, layers = case(prepared)
    assert equations(view, layers, [("clipped", 21, 31, None)]) == ()
    (equation,) = equations(view, layers)
    assert inline_symbols(view.text, equation) == ((), "unsupported")
    assert tuple(inline_equations(view.text, view.pieces, {}, None, max_chars=2048)) == ()


@pytest.mark.parametrize(
    ("text", "bound", "expected"),
    [
        ("using the equation X = χZ + µ.", 2048, "unsupported"),
        ("using the equation X = σZ + µ.", 6, "limited"),  # noqa: RUF001 - literal mathematical sigma
        ("using the equation X = σZ + µ", 2048, "unsupported"),  # noqa: RUF001 - literal mathematical sigma
    ],
)
def test_nomination_failure_is_retained_and_not_retried_in_consumer(
    prepared, text, bound, expected
):
    view, _layer, layers = case(prepared, text, max_inline_chars=bound)
    (equation,) = equations(view, layers)
    assert equation.status == expected
    assert inline_symbols(
        view.text, equation, primary_layers=layers, projection=view.ref.projection_digest
    ) == ((), expected)
