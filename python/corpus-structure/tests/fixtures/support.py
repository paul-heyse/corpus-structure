"""Read retained fixture JSON and independently typed source segment witnesses."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from corpus_structure.core.evidence import SegmentKind
from corpus_structure.semantic.source_types import DelimitingStatus

REPO = Path(__file__).resolve().parents[4]
S0_DIR = REPO / "fixtures/s0"
TRACE_DIR = REPO / "fixtures/trace"
CORPUS_DIR = TRACE_DIR / "corpus"
INDEX_FILE = TRACE_DIR / "index/siegrist_sections.tsv"
CORPUS_ROOT = "siegrist_random/random"  # the Siegrist source profile's `root` (D2 §12.1)

S0_UNITS = (
    "T1-leadin", "T1-dfn1", "T2", "T3", "T4",
    "U5", "U6", "U7", "U8", "U9", "U10", "U11", "U12",
)  # fmt: skip
TRACE_ANNOTATION_UNITS = ("T1-leadin", "T1-dfn1", "T2", "T3", "T4")
TRACE_UNITS = ("T1", "T2", "T3", "T4")
VENDORED_PAGES = (
    "special/LocationScale.html",
    "special/Normal.html",
    "special/LogNormal.html",
    "special/Gamma.html",
)


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# --- fixtures/trace segments -------------------------------------------------------------------


class SegmentRow(_Model):
    kind: SegmentKind
    locator: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    attrs: dict[str, JsonValue]
    parse_status: DelimitingStatus
    parse_reason: str | None = None


class MarkupRow(_Model):
    markup: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    text: str


class TraceSegments(_Model):
    trace_unit: Literal["T1", "T2", "T3", "T4"]
    page: str
    source_uri: str
    unit_key: str
    ancestors: tuple[SegmentRow, ...]
    segments: tuple[SegmentRow, ...] = Field(min_length=1)
    counts: dict[SegmentKind, int]
    markup: tuple[MarkupRow, ...]
    trace_md: dict[str, JsonValue]
    provenance: dict[str, JsonValue]


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_s0(name: str):
    return _read(S0_DIR / f"{name}.json")


def load_segments(name: str) -> TraceSegments:
    return TraceSegments.model_validate(_read(TRACE_DIR / f"{name}.segments.json"))


def load_target(name: str):
    return _read(TRACE_DIR / f"{name}.target.json")
