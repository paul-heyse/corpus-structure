"""Semantic lowering preserves supplied Python values rather than presentation serializers."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_serializer

from corpus_structure.semantic.domain_operations import _native, _plain
from corpus_structure.semantic.reference_positions import _plain as reference_plain


class Item(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    amount: Decimal = Field(alias="wire_amount")
    date: date
    missing: str | None = None
    supplied_null: str | None = None
    target: str


class ExtendedItem(Item):
    attribution: str


class Container(BaseModel):
    items: tuple[Item, ...]


def test_python_lowering_and_prepared_dump_agree_on_supplied_typed_values():
    item = ExtendedItem(
        amount=Decimal("1.2300"),
        date=date(2026, 11, 2),
        supplied_null=None,
        target="entity:preserved-reference",
        attribution="source:independent",
    )
    value = Container(items=(item,))
    expected_item = dict(
        amount=Decimal("1.2300"),
        date=date(2026, 11, 2),
        supplied_null=None,
        target="entity:preserved-reference",
        attribution="source:independent",
    )
    dumped = value.model_dump(
        mode="python",
        exclude_unset=True,
        by_alias=False,
        serialize_as_any=True,
        exclude_computed_fields=True,
    )
    assert dumped == _native(value) == reference_plain(value) == {"items": (expected_item,)}
    assert _plain(value) == {"items": [expected_item]}
    assert dumped["items"][0]["amount"].as_tuple().exponent == -4
    assert value.model_dump(mode="json", exclude_unset=True)["items"][0]["amount"] == "1.2300"
    assert value.model_dump(by_alias=True)["items"][0]["wire_amount"] == Decimal("1.2300")


class Presented(BaseModel):
    value: Decimal

    @field_serializer("value")
    def display_value(self, value: Decimal) -> str:
        return f"display:{value}"

    @computed_field
    @property
    def label(self) -> str:
        return "presentation only"


def test_presentation_serializers_are_not_a_substitute_for_semantic_python_values():
    value = Presented(value=Decimal("2.500"))
    assert value.model_dump(mode="python", exclude_unset=True) == {
        "value": "display:2.500",
        "label": "presentation only",
    }
    for lower in (_native, _plain, reference_plain):
        assert lower(value) == {"value": Decimal("2.500")}
