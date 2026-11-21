"""Captured closed projections over actual current visual evidence products."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter

from .identity import canonical_bytes
from .types import SourceArtifact
from .visual_evidence import VisualEvidencePin, VisualEvidenceRow

if TYPE_CHECKING:
    from .native_program_registry import ProgramDeclaration

SOURCE = "native/data-operation-visual-read.schema.json"
ARTIFACT_SOURCE = "native/data-operation-visual-artifact.schema.json"


class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class VisualReadHeader(_Record):
    evidence: VisualEvidencePin
    raw: VisualEvidencePin
    producer: dict[str, JsonValue]
    raw_producer: dict[str, JsonValue]
    observation: dict[str, JsonValue]
    mapping_availability: Literal["not_selected", "unavailable", "available"]
    mapped_digest: str | None
    mapping: dict[str, JsonValue] | None


class VisualHeaderReply(_Record):
    kind: Literal["header"]
    header: VisualReadHeader


class VisualRowsReply(_Record):
    kind: Literal["rows"]
    items: tuple[VisualEvidenceRow, ...]
    next_after: int | None


class VisualArtifactReply(_Record):
    kind: Literal["artifact"]
    digest: str
    media_type: Literal["image/png", "text/html; charset=utf-8", "application/json"]
    content_hex: str = Field(
        pattern="^(?:[0-9a-f]{2})*$",
        json_schema_extra={"not": {"pattern": "[^0-9a-f]"}},
    )
    offset: int = Field(ge=0)
    total_bytes: int = Field(ge=0)
    next_offset: int | None


VisualReadReply = Annotated[
    VisualHeaderReply | VisualRowsReply | VisualArtifactReply, Field(discriminator="kind")
]


def _schema(value: Any) -> bytes:
    from .data_operation_wire import NativeJsonSchema

    schema = TypeAdapter(value).json_schema(
        ref_template="#/definitions/{model}", schema_generator=NativeJsonSchema, mode="validation"
    )
    definitions = schema.pop("definitions", {})
    prefix = "visual_read_"

    def reference(value):
        if isinstance(value, str) and value.startswith("#/definitions/"):
            return "#/definitions/" + prefix + value.removeprefix("#/definitions/")
        return value

    def rename(value: Any) -> Any:
        if isinstance(value, dict):
            discriminator = value.get("discriminator")
            if isinstance(discriminator, dict) and isinstance(discriminator.get("mapping"), dict):
                value = {
                    **value,
                    "discriminator": {
                        **discriminator,
                        "mapping": {
                            tag: reference(target)
                            for tag, target in discriminator["mapping"].items()
                        },
                    },
                }
            return {
                key: reference(child) if key == "$ref" else rename(child)
                for key, child in value.items()
            }
        if isinstance(value, list):
            return [rename(child) for child in value]
        return value

    schema = rename(schema)
    schema["definitions"] = {prefix + name: rename(value) for name, value in definitions.items()}
    return canonical_bytes(schema)


def visual_read_schema() -> bytes:
    return _schema(VisualReadReply)


def visual_read_sources(*, target_metadata=None) -> tuple[SourceArtifact, ...]:
    from .visual_evidence import VisualEvidenceArtifact
    from .visual_read_native import visual_read_programs

    if target_metadata is None:
        from .metadata import get_metadata

        target_metadata = get_metadata()
    artifact_schema = _schema(VisualEvidenceArtifact)
    return (
        SourceArtifact(ARTIFACT_SOURCE, artifact_schema),
        SourceArtifact(SOURCE, visual_read_schema()),
        SourceArtifact("native/data-operation-visual-read.py", Path(__file__).read_bytes()),
        SourceArtifact(
            "native/visual-evidence.py", Path(__file__).with_name("visual_evidence.py").read_bytes()
        ),
        SourceArtifact(
            "native/visual-read-native.py",
            Path(__file__).with_name("visual_read_native.py").read_bytes(),
        ),
        SourceArtifact(
            "native/data-operation-visual-read.sql",
            visual_read_programs(target_metadata, artifact_schema).encode(),
        ),
    )


def visual_read_declarations(
    *, target_metadata=None, sources=None
) -> tuple[ProgramDeclaration, ...]:
    """Use the exact captured artifact contract at the typed visual producer."""
    from .metadata import get_metadata
    from .native_objects import native_sql_script
    from .visual_read_native import visual_read_native_programs

    selected = get_metadata() if target_metadata is None else target_metadata
    captured = visual_read_sources(target_metadata=selected) if sources is None else tuple(sources)
    by_name = {source.name: source.content for source in captured}
    declarations = visual_read_native_programs(selected, by_name[ARTIFACT_SOURCE])
    if (
        native_sql_script(item.routine.render() for item in declarations).encode()
        != by_name["native/data-operation-visual-read.sql"]
    ):
        raise ValueError(
            "visual source declarations differ from captured model/artifact statements"
        )
    return declarations


def visual_read_sql(sources=None) -> str:
    captured = visual_read_sources() if sources is None else sources
    return next(
        source.content.decode()
        for source in captured
        if source.name == "native/data-operation-visual-read.sql"
    )
