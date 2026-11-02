"""Archive JSON lowering retains semantic inputs and exact native bytea transport."""

from decimal import Decimal

import pytest

from corpus_structure.semantic.releases import _archive_wire_payload


def test_archive_export_handles_all_nested_owned_tuple_fields_without_mutation():
    row = {
        "constraints": {"patterns": ("^a", "z$"), "nested": ({"choices": ()},)},
        "content": b"\x00\xff",
        "nullable": None,
    }
    result = _archive_wire_payload(
        {"property_applicability": [row], "input": [{"content": memoryview(b"\x42")}]}
    )
    assert result == {
        "property_applicability": [
            {
                "constraints": {"patterns": ["^a", "z$"], "nested": [{"choices": []}]},
                "content": "\\x00ff",
                "nullable": None,
            }
        ],
        "input": [{"content": "\\x42"}],
    }
    assert row["constraints"] == {"patterns": ("^a", "z$"), "nested": ({"choices": ()},)}
    assert "omitted" not in row


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_archive_export_refuses_nonfinite_json_before_native_effect(value):
    with pytest.raises(ValueError):
        _archive_wire_payload({"property_applicability": [{"constraints": {"minimum": value}}]})


def test_archive_export_does_not_apply_semantic_decimal_or_arbitrary_object_serializers():
    for value in (Decimal("1.00"), object()):
        with pytest.raises(TypeError):
            _archive_wire_payload({"property_applicability": [{"constraints": {"value": value}}]})
