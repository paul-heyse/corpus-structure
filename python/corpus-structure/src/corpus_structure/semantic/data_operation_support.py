"""Typed computational and original-fact support, with frozen original source selection."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter, model_validator

from .identity import canonical_bytes

Nonempty = Annotated[str, Field(min_length=1)]


class OriginalDocumentRef(BaseModel):
    """An immutable original document fact, distinct from a selected native view."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    kind: Literal["original-document"]
    project_id: Nonempty
    document_key: Nonempty
    content_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    mime: Nonempty


class AuthoredFactRef(BaseModel):
    """Explicit immutable operator input, never a provider or computation episode."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    kind: Literal["authored-fact"]
    project_id: Nonempty
    author: Nonempty
    selection_id: Nonempty
    kind_contract: Nonempty
    subject: Nonempty
    original_source: Nonempty
    analyzed_scope: JsonValue
    meaning_body: JsonValue

    @model_validator(mode="after")
    def exact_semantic_body(self):
        from .data_operation_identity import decode_semantic_value

        decode_semantic_value(self.meaning_body)
        return self


def read_original_source_reference(content: bytes):
    from .structural_products import ExternalSourceRef

    return TypeAdapter(OriginalDocumentRef | ExternalSourceRef | AuthoredFactRef).validate_json(
        content, strict=True
    )


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


class AuthoredFactSupportReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["authored"] = "authored"
    admission_id: Nonempty
    source_reference: Nonempty


type SupportReference = Annotated[
    ComputationalSupportReference | OriginalSourceSupportReference | AuthoredFactSupportReference,
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
        if (
            type(self.name) is not str
            or not self.name
            or any(type(value) is not bytes for value in (self.reference, self.selectors))
        ):
            raise TypeError("original source selections require immutable named canonical bytes")
        reference = read_original_source_reference(self.reference)
        if canonical_bytes(reference.model_dump(mode="json", exclude_none=True)) != self.reference:
            raise ValueError("original source reference must preserve its exact canonical pins")
        selectors = json.loads(self.selectors)
        if (
            not isinstance(selectors, list)
            or not selectors
            or canonical_bytes(selectors) != self.selectors
        ):
            raise ValueError("original source selectors require a nonempty canonical JSON array")
        if isinstance(reference, OriginalDocumentRef) and selectors != [
            {"scope": "whole-document"}
        ]:
            raise ValueError("original document selection requires its exact whole-document scope")
        if isinstance(reference, AuthoredFactRef) and selectors != [{"scope": "authored-fact"}]:
            raise ValueError("authored admission requires its explicit authored-fact scope")

    def record(self) -> dict:
        return {"reference": json.loads(self.reference), "selectors": json.loads(self.selectors)}


def original_source_selections_record(selections: tuple[OriginalSourceSelection, ...]) -> dict:
    if len({selection.name for selection in selections}) != len(selections):
        raise ValueError("duplicate frozen original source selection name")
    return {
        selection.name: selection.record() for selection in sorted(selections, key=lambda s: s.name)
    }


def authored_fact_selection(name, value, *, kind_contract, context, author, selection_id):
    """Freeze actual authored input at its typed, completely qualified boundary.

    Native admission validates the kind/body, caller purpose, frozen intent and
    root context. Possessing this value grants no publication permission.
    """
    from .data_operation_identity import semantic_value
    from .data_operation_json import json_loads

    reference = AuthoredFactRef(
        kind="authored-fact",
        project_id=context.project_id,
        author=author,
        selection_id=selection_id,
        kind_contract=kind_contract,
        subject=context.subject,
        original_source=context.original_source,
        analyzed_scope=json_loads(context.analyzed_scope),
        meaning_body=semantic_value(value),
    )
    return OriginalSourceSelection(
        name,
        canonical_bytes(reference.model_dump(mode="json")),
        canonical_bytes([{"scope": "authored-fact"}]),
    )


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


ORIGINAL_SUPPORT_REFERENCE_SCHEMA = "native/data-operation-original-support-reference.json"


def original_support_reference_schema() -> bytes:
    from jsonschema import Draft7Validator

    from .structural_products import ExternalSourceRef

    schema = TypeAdapter(OriginalDocumentRef | ExternalSourceRef | AuthoredFactRef).json_schema(
        ref_template="#/definitions/{model}"
    )
    if "$defs" in schema:
        schema["definitions"] = schema.pop("$defs")
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    Draft7Validator.check_schema(schema)
    return canonical_bytes(schema)
