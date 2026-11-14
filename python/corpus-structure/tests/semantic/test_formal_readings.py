"""Exact retained field projections preserve scope, ambiguity and domain validity."""

import pytest

from corpus_structure.methods.structural_products import _literal_reading, _threshold_inventory
from corpus_structure.semantic.formal_readings import (
    FormalSourceReadings,
    coordination_reading,
    formal_field_readings,
    lexical_fact_readings,
)
from corpus_structure.semantic.structural_products import ExternalSourceRef, LocatedDefinitionSpan
from semantic.primary_formal_fixture import formal_layers
from semantic.typed_structural_composition_support import threshold_inputs


def test_whole_normalized_fields_and_lexical_basis_are_consumed_without_parsing(monkeypatch):
    from corpus_structure.semantic import formal_evidence, structural_parsing

    text = (
        "revenue ≥ 2.50e3 USD\nComparison basis: annual gross revenue.\n"
        "Identifier: Form-A and Date: 2025-01-15."
    )
    inputs = threshold_inputs(text, text)
    passage, source = inputs.passages[0], inputs.sources[0]
    layers = formal_layers(inputs)

    def unexpected(*_args, **_kwargs):
        pytest.fail("comparison consumer reran field recognition")

    monkeypatch.setattr(formal_evidence, "nominate_fields", unexpected)
    for name in ("parse_threshold", "parse_comparison_literal", "threshold_fields"):
        monkeypatch.setattr(structural_parsing, name, unexpected)
    primary = FormalSourceReadings(layers, source)
    fields, complete = _threshold_inventory(passage, source, primary)
    assert complete and len(fields) == 1
    (field,) = fields
    assert field.typed is not None
    assert (
        field.typed.value,
        field.typed.comparator,
        field.typed.quantity,
        field.typed.unit,
        field.typed.basis,
    ) == ("2500", ">=", "revenue", "USD", "annual gross revenue")
    assert field.typed.primary_formal is not None and field.typed.primary_basis is not None
    for spelling, kind, value in (
        ("Identifier: Form-A", "identifier", "Form-A"),
        ("Date: 2025-01-15", "date", "2025-01-15"),
    ):
        start = text.index(spelling)
        span = LocatedDefinitionSpan(
            passage_id=passage.passage_id, start=start, end=start + len(spelling), text=spelling
        )
        literal, reference = _literal_reading(span, source, primary)
        assert literal is not None and reference is not None
        assert (literal.kind, literal.value) == (kind, value)
        assert _literal_reading(span.model_copy(update=dict(text="wrong")), source, primary) == (
            None,
            None,
        )
    a = text.index("Form-A") + len("Form-A")
    b = text.index("Date:")
    cue = coordination_reading(primary, source, start=a, end=b)
    assert cue is not None and cue.value == "and" and cue.text == "and"


def test_rival_layer_origins_and_invalid_domains_do_not_become_known_absence():
    inputs = threshold_inputs("X > 2 kg", "Date: 2025-02-30")
    layers = formal_layers(inputs)
    source, passage = inputs.sources[0], inputs.passages[0]
    assert isinstance(source, ExternalSourceRef)
    pin = next(
        pin
        for pin, report in layers.items()
        if source.source_view_id in report.payload["source_scope"]["source_view_ids"]
    )
    rival = {**layers, layers[pin].reference(9999): layers[pin]}
    fields, complete = formal_field_readings(
        rival, source, family="formal.threshold", start=passage.start, end=passage.end
    )
    assert fields == () and not complete
    assert _threshold_inventory(passage, source, {}) == ((), False)
    invalid, second = inputs.passages[1], inputs.sources[1]
    fields, complete = formal_field_readings(
        layers, second, family="formal.date", start=invalid.start, end=invalid.end
    )
    assert fields == () and not complete
    with pytest.raises(ValueError, match="source binding"):
        formal_field_readings(
            layers,
            source.model_copy(update=dict(recipe_digest="d" * 64)),
            family="formal.threshold",
            start=passage.start,
            end=passage.end,
        )


def test_revision_identifiers_and_exception_marker_retain_named_source_members():
    text = "Clause policy.\nRevision R2 supersedes revision R1.\nNo exceptions."
    inputs = threshold_inputs(text, text)
    passage, source = inputs.passages[0], inputs.sources[0]
    layers = formal_layers(inputs)
    (fact,) = lexical_fact_readings(
        layers, source, kind="formal.revision_succession", start=0, end=len(text)
    )
    assert fact.text == "Revision R2 supersedes revision R1."
    assert [(role, value) for role, _reference, value in fact.bindings] == [
        ("newer_revision", "R2"),
        ("older_revision", "R1"),
    ]
    (empty,) = lexical_fact_readings(
        layers, source, kind="formal.exception_empty", start=0, end=len(text)
    )
    assert empty.text == "No exceptions" and empty.value == "empty"
    assert passage.text[empty.start : empty.end] == empty.text


@pytest.mark.parametrize(
    ("surface", "expected"),
    [
        ("Quantity: 1e100 kg", dict(kind="quantity", value="1" + "0" * 100, unit="kg")),
        ("Quantity: 1e101 kg", None),
        ("Quantity: -1e101 kg", None),
        ("Quantity: 1e-100 kg", dict(kind="quantity", value="0." + "0" * 99 + "1", unit="kg")),
        ("Quantity: 1e-101 kg", None),
        ("Quantity: 1e1000000 kg", None),
        ("Quantity: 1e-1000000 kg", None),
        ("Quantity: -0e1000 kg", dict(kind="quantity", value="0", unit="kg")),
        (
            "Range: [1e-100, 1e100] kg",
            dict(
                kind="range",
                lower="0." + "0" * 99 + "1",
                upper="1" + "0" * 100,
                lower_closed=True,
                upper_closed=True,
                unit="kg",
            ),
        ),
        ("Range: [1e-101, 1] kg", None),
        ("Range: [0, 1e101] kg", None),
        ("Identifier: " + "A" * 244, dict(kind="identifier", value="A" * 244)),
        ("Identifier: " + "A" * 245, None),
    ],
)
def test_comparison_projection_preserves_existing_numeric_and_source_size_bounds(surface, expected):
    inputs = threshold_inputs(surface, surface)
    source, passage = inputs.sources[0], inputs.passages[0]
    literal, reference = _literal_reading(passage, source, formal_layers(inputs))
    assert (literal.model_dump(mode="json", exclude_none=True) if literal else None) == expected
    assert (reference is not None) == (expected is not None)


@pytest.mark.parametrize("surface", ["1e1000000", "1e-1000000"])
def test_comparison_refusal_preserves_exact_large_and_tiny_primary_facts(surface):
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.structural_products import ComparisonLiteral

    spelling = f"Quantity: {surface} kg"
    inputs = threshold_inputs(spelling, spelling)
    source, passage = inputs.sources[0], inputs.passages[0]
    layers = formal_layers(inputs)
    (field,), complete = formal_field_readings(
        layers, source, family="formal.quantity", start=passage.start, end=passage.end
    )
    assert complete and field.text == spelling
    assert field.normalized["value"] == surface
    assert field.normalized["domain_status"] == "unresolved"
    before = {pin: canonical_bytes(report.payload) for pin, report in layers.items()}
    assert _literal_reading(passage, source, layers) == (None, None)
    assert before == {pin: canonical_bytes(report.payload) for pin, report in layers.items()}
    with pytest.raises(ValueError, match="bounded decimal range"):
        ComparisonLiteral(kind="quantity", value=surface, unit="kg")
    with pytest.raises(ValueError, match="bounded decimal range"):
        ComparisonLiteral(
            kind="range", lower="0", upper=surface, lower_closed=True, upper_closed=True, unit="kg"
        )
