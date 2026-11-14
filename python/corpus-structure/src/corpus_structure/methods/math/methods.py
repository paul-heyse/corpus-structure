"""Sealed mathematical reading configuration and shared native batch custody."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.core.method import PackSection
from corpus_structure.methods.math.grammar import PARSE_SECONDS

from .configuration import MathSection

MathFromPack = Annotated[MathSection | None, PackSection("math")]


class _Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    math: MathFromPack = None
    characterization_layers: tuple[dict[str, Any], ...] = ()

    def section(self) -> MathSection:
        return self.math or MathSection()


class ExtractMathConfig(_Config):
    """`extract.math/<name>`: the pack's math section and the parse deadline."""

    parse_seconds: float = Field(default=PARSE_SECONDS, gt=0)


@dataclass
class MathReadingsBatch:
    """One reader-owned native mathematical preparation batch."""

    owner: object | None = field(default=None, repr=False)
    native: dict[tuple[Any, ...], tuple[Any, ...]] = field(default_factory=dict)

    def bind(self, reader: object) -> None:
        if self.owner is None:
            self.owner = reader
        elif self.owner is not reader:
            raise ValueError("math preparation belongs to another source reader")
