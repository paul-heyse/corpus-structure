"""Private parser products before the source contribution boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .pm2_source import MappedSource, SourceMapRefused


PARSER_QUESTIONS = {
    "hanlp": "pm2.hanlp.frames",
    "maverick": "pm2.maverick.coreference",
    "dipo": "pm2.dipo.discourse",
}


@dataclass(frozen=True)
class ParserProduct:
    key: str
    semantic_type: str
    value: dict[str, Any]
    members: tuple[str, ...]


@dataclass(frozen=True)
class ParserProducts:
    locations: dict[str, MappedSource | SourceMapRefused]
    products: tuple[ParserProduct, ...]
