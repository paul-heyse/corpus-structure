"""Exact retained field projections preserve scope, ambiguity and domain validity."""

import pytest

from corpus_structure.methods.structural_products import _literal_reading, _threshold_inventory
from corpus_structure.semantic.formal_readings import (
    FormalSourceReadings,
    coordination_reading,
    formal_field_readings,
    lexical_fact_readings,
)
from corpus_structure.semantic.structural_products import LocatedDefinitionSpan
from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
from corpus_structure.semantic.formal_products import FormalEvidenceOptions, FrozenFormalSource
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import StructuralPassage
from semantic.formal_products_support import profile as profile
from semantic.formal_products_support import selected_rows, publication_context



def case(profile, text):
    """Pure supplied structural address; parser products carry real current meanings."""
    from corpus_structure.semantic.data_operation_model import json_context_meaning
    from corpus_structure.semantic.source_products import source_subject

    source = selected_rows(profile, (text, "text", "", ""))
    product = profile.run(source, FormalEvidenceOptions(), subject_context=publication_context(source))
    selected = source.value
    coordinate = selected["source"]
    address = DeclaredStructuralSource(
        source=canonical_bytes(["fixture:formal-source", None]).decode(),
        source_product="fixture:formal-source", kind_contract="kind:fixture-source",
        subject=source_subject(coordinate), subject_definition="original-source-view",
        document=coordinate["document"], original_source=coordinate["document"],
        projection_digest=coordinate["projection"],
        section_pointer=coordinate["section_pointer"], membership=coordinate["membership"],
        project_id="fixture:formal", analyzed_scope_meaning=json_context_meaning(canonical_bytes(
            dict(source=coordinate, selectors=selected["selectors"])
        )).decode(),
    )
    passage = StructuralPassage(passage_id="p", source_ref=address.identity,
                               start=0, end=len(text), text=text, scope="fixture")
    readings = FormalSourceReadings.from_products((product,), source)
    return source, product, address, passage, readings


def test_whole_normalized_fields_and_lexical_basis_are_consumed_without_parsing(profile, monkeypatch):
    from corpus_structure.semantic import formal_evidence, structural_parsing

    text = (
        "revenue ≥ 2.50e3 USD\nComparison basis: annual gross revenue.\n"
        "Identifier: Form-A and Date: 2025-01-15."
    )
    _native, _product, source, passage, primary = case(profile, text)

    def unexpected(*_args, **_kwargs):
        pytest.fail("comparison consumer reran field recognition")

    monkeypatch.setattr(formal_evidence, "nominate_fields", unexpected)
    for name in ("parse_threshold", "parse_comparison_literal", "threshold_fields"):
        monkeypatch.setattr(structural_parsing, name, unexpected)
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
    cue = coordination_reading(primary, primary.source, start=a, end=b)
    assert cue is not None and cue.value == "and" and cue.text == "and"


def test_distinct_examined_scopes_and_invalid_domains_do_not_become_known_absence(profile):
    native, product, source, passage, primary = case(profile, "X > 2 kg\nDate: 2025-02-30")
    narrowed = native.value
    narrowed["selectors"] = [dict(projection=source.projection_digest, start=0, end=8)]
    selected = FrozenFormalSource.acquire(profile.prepared, narrowed)
    other = profile.run(selected, FormalEvidenceOptions(), subject_context=publication_context(selected))
    assert other.content != product.content
    rival = FormalSourceReadings.from_products((product, other), native)
    fields, complete = formal_field_readings(
        rival, rival.source, family="formal.threshold", start=0, end=8
    )
    assert fields == () and not complete
    missing = FormalSourceReadings.from_products((), native)
    assert _threshold_inventory(passage, source, missing) == ((), False)
    fields, complete = formal_field_readings(
        primary, primary.source, family="formal.date", start=9, end=len(passage.text)
    )
    assert fields == () and not complete
    with pytest.raises(ValueError, match="another original source"):
        _threshold_inventory(passage, source.model_copy(update=dict(projection_digest="d" * 64)), primary)


def test_revision_identifiers_and_exception_marker_retain_named_source_members(profile):
    text = "Clause policy.\nRevision R2 supersedes revision R1.\nNo exceptions."
    _native, _product, source, passage, layers = case(profile, text)
    (fact,) = lexical_fact_readings(
        layers, layers.source, kind="formal.revision_succession", start=0, end=len(text)
    )
    assert fact.text == "Revision R2 supersedes revision R1."
    assert [(role, value) for role, _reference, value in fact.bindings] == [
        ("newer_revision", "R2"),
        ("older_revision", "R1"),
    ]
    (empty,) = lexical_fact_readings(
        layers, layers.source, kind="formal.exception_empty", start=0, end=len(text)
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
def test_comparison_projection_preserves_existing_numeric_and_source_size_bounds(profile, surface, expected):
    _native, _product, source, passage, primary = case(profile, surface)
    literal, reference = _literal_reading(passage, source, primary)
    assert (literal.model_dump(mode="json", exclude_none=True) if literal else None) == expected
    assert (reference is not None) == (expected is not None)


@pytest.mark.parametrize("surface", ["1e1000000", "1e-1000000"])
def test_comparison_refusal_preserves_exact_large_and_tiny_primary_facts(profile, surface):
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.structural_products import ComparisonLiteral

    spelling = f"Quantity: {surface} kg"
    _native, product, source, passage, layers = case(profile, spelling)
    (field,), complete = formal_field_readings(
        layers, layers.source, family="formal.quantity", start=passage.start, end=passage.end
    )
    assert complete and field.text == spelling
    assert field.normalized["value"] == surface
    assert field.normalized["domain_status"] == "unresolved"
    before = product.content
    assert _literal_reading(passage, source, layers) == (None, None)
    assert before == product.content
    with pytest.raises(ValueError, match="bounded decimal range"):
        ComparisonLiteral(kind="quantity", value=surface, unit="kg")
    with pytest.raises(ValueError, match="bounded decimal range"):
        ComparisonLiteral(
            kind="range", lower="0", upper=surface, lower_closed=True, upper_closed=True, unit="kg"
        )
