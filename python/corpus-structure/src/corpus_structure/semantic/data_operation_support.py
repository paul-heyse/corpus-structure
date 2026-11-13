"""Typed computational and original-fact support, with frozen original source selection."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from .identity import canonical_bytes

Nonempty = Annotated[str, Field(min_length=1)]


class ComputationalSupportReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["computation"] = "computation"
    derivation_id: Nonempty
    admission_use_id: Nonempty | None = None


class OriginalSourceSupportReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["original-source"] = "original-source"
    admission_id: Nonempty
    source_reference: Nonempty


type SupportReference = Annotated[
    ComputationalSupportReference | OriginalSourceSupportReference,
    Field(discriminator="kind"),
]
_SUPPORTS = TypeAdapter(tuple[SupportReference, ...])


def read_support_references(value) -> tuple[SupportReference, ...]:
    return _SUPPORTS.validate_python(value)


def support_reference_records(value: tuple[SupportReference, ...]) -> list[dict]:
    return [reference.model_dump(mode="json", exclude_none=True) for reference in value]


@dataclass(frozen=True)
class OriginalSourceSelection:
    """Freeze exact original pins and selectors; native admission reauthenticates them."""

    name: str
    reference: bytes
    selectors: bytes

    def __post_init__(self) -> None:
        from .structural_products import ExternalSourceRef

        if type(self.name) is not str or not self.name or any(
            type(value) is not bytes for value in (self.reference, self.selectors)
        ):
            raise TypeError("original source selections require immutable named canonical bytes")
        reference = ExternalSourceRef.model_validate_json(self.reference)
        if canonical_bytes(reference.model_dump(mode="json", exclude_none=True)) != self.reference:
            raise ValueError("original source reference must preserve its exact canonical pins")
        selectors = json.loads(self.selectors)
        if (
            not isinstance(selectors, list) or not selectors
            or canonical_bytes(selectors) != self.selectors
        ):
            raise ValueError("original source selectors require a nonempty canonical JSON array")

    def record(self) -> dict:
        return {"reference": json.loads(self.reference), "selectors": json.loads(self.selectors)}


def original_source_selections_record(selections: tuple[OriginalSourceSelection, ...]) -> dict:
    if len({selection.name for selection in selections}) != len(selections):
        raise ValueError("duplicate frozen original source selection name")
    return {
        selection.name: selection.record() for selection in sorted(selections, key=lambda s: s.name)
    }


ORIGINAL_REFERENCE_SCHEMA = "native/data-operation-original-reference.json"


def original_source_reference_schema() -> bytes:
    from jsonschema import Draft7Validator

    from .structural_products import ExternalSourceRef

    schema = TypeAdapter(ExternalSourceRef).json_schema(ref_template="#/definitions/{model}")
    if "$defs" in schema:
        schema["definitions"] = schema.pop("$defs")
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    Draft7Validator.check_schema(schema)
    return canonical_bytes(schema)
