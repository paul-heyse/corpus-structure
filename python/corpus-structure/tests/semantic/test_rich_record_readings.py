"""Actual current record families lower completely, with independent evidence refusals."""

from copy import deepcopy

import pytest

from corpus_structure.semantic.rich_record_readings import rich_reading_value
from semantic.rich_record_readings_support import current, inspected_reading


@pytest.mark.parametrize(
    "family,class_name,field_count",
    [
        ("definition", "DefinitionReading", 5),
        ("assertion", "QualifiedAssertionReading", 9),
        ("measurement", "MeasurementReading", 10),
        ("table", "TableAssertionReading", 8),
        ("formula_context", "FormulaContextReading", 6),
    ],
)
def test_complete_source_reading_values_keep_every_original_field_without_scientific_fact(
    family, class_name, field_count
):
    prepared, model = current()
    row, coordinates = inspected_reading(family)
    value = rich_reading_value(prepared, model, row, coordinate_texts=coordinates)
    assert value.class_name == class_name
    assert len(value.fields) == field_count
    assert set(value.fields) == {field["role"] for field in row["fields"]}
    assert all(
        "role" not in field and "evidence_sets" not in field and "alternatives" not in field
        for field in value.fields.values()
    )
    assert row["standing"] == "candidate"
    assert not hasattr(value, "fact_id")
    for field in row["fields"]:
        assert value.fields[field["role"]]["state"] == field["state"]
        if field["state"] != "present":
            assert "value" not in value.fields[field["role"]]
            assert value.fields[field["role"]]["reason"] == field["reason"]


def test_incomplete_reading_has_no_partial_lowering_and_no_forged_evidence():
    prepared, model = current()
    row, coordinates = inspected_reading("table")
    original = deepcopy(row)
    for change in ("missing-field", "missing-support", "forged-coordinate"):
        invalid = deepcopy(row)
        texts = coordinates
        if change == "missing-field":
            invalid["fields"] = invalid["fields"][:-1]
        elif change == "missing-support":
            invalid["fields"][0]["evidence_sets"] = ()
        else:
            texts = [{**value, "text": "forged source"} for value in coordinates]
        with pytest.raises(ValueError):
            rich_reading_value(prepared, model, invalid, coordinate_texts=texts)
    assert row == original
