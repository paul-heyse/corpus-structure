"""Readers for `fixtures/s0` and `fixtures/trace`, and the target shapes beyond F2b's.

Foundations §3.7 (P0-F-3); documented in `fixtures/trace/README.md`. The batches and frames are
the core models (`AuthoredBatch`, `CitationFrame`); this module adds only what the fixture files
hold around them:

- `S0Fixture`: one annotation unit's authored batch, frame and provenance (an `outside`
  statement's descriptor is in the batch since P0-F-2e);
- `TraceSegments`: the expected segments of one trace annotation unit (I1a's acceptance);
- `TraceTarget`: a trace unit's target batch and frame, its `must_not` patterns (`MustNot`, an
  `EntityPattern` or a `ClaimPattern`), its D8 §5.3 `questions` (`Question`), the phase-2 claims
  held outside the batch (`Deferred`) and the phase marks.

Patterns are partial: a field left out matches anything. `{"ref": r}` (`TargetRef`) names the item
the target's local ref `r` keys to, so patterns compare by key equality, never key value; LaTeX in a
`ValuePattern` is compared by token form (D1 §6.2) by the matcher, which is C3's.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from corpus_structure.core.batch import AuthoredBatch, CitationFrame
from corpus_structure.core.evidence import SegmentKind
from corpus_structure.core.vocab import DelimitingStatus

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


# --- fixtures/s0 -------------------------------------------------------------------------------


class S0Fixture(_Model):
    unit_key: str
    batch: AuthoredBatch
    frame: CitationFrame
    provenance: dict[str, JsonValue]

    @model_validator(mode="after")
    def _unit_ref(self) -> S0Fixture:
        if self.batch.unit_ref != self.unit_key:
            raise ValueError(f"unit_ref {self.batch.unit_ref!r} is not the unit key")
        return self


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


# --- fixtures/trace targets --------------------------------------------------------------------


class TargetRef(_Model):
    """The item the target's local ref keys to."""

    ref: str = Field(min_length=1)


class ValuePattern(_Model):
    t: str | None = None
    latex: str | None = None
    v: str | None = None

    @model_validator(mode="after")
    def _something(self) -> ValuePattern:
        if self.t is None and self.latex is None and self.v is None:
            raise ValueError("a value pattern constrains at least one field")
        return self


class ConditionPattern(_Model):
    """A condition node that occurs anywhere in a claim's condition tree."""

    op: str
    ref: str | None = None  # a `claim` node's target local ref
    x: ValuePattern | None = None
    set: ValuePattern | None = None


class EntityPattern(_Model):
    kind: Literal["entity"]
    type: str | None = None
    label: str | None = None
    identity: dict[str, str | TargetRef] | None = None


class ClaimPattern(_Model):
    kind: Literal["claim"]
    subject: TargetRef | EntityPattern | None = None
    predicate: str | None = None
    object: TargetRef | EntityPattern | ValuePattern | None = None
    modality: str | None = None
    param_values: dict[str, ValuePattern] | None = None  # entries of the `param_values` qualifier
    param_value: ValuePattern | None = None  # any entry of `param_values`
    condition: ConditionPattern | None = None
    lacks_condition: ConditionPattern | None = None


class MustNot(_Model):
    line: str  # trace.md's "must not appear" text
    pattern: Annotated[EntityPattern | ClaimPattern, Field(discriminator="kind")]


QueryName = Literal["statement", "construction_profile", "family_profile", "transformations_of"]


class Question(_Model):
    question: str
    query: QueryName
    params: dict[str, str]
    returns: tuple[str, ...]
    returns_with_suppositions: tuple[str, ...]
    returns_from_phase_2: tuple[str, ...] = ()
    note: str | None = None


class Deferred(_Model):
    pending: str
    claims: tuple[dict[str, JsonValue], ...]


class Phases(_Model):
    default: int
    items: dict[str, int]


class TraceTarget(_Model):
    trace_unit: Literal["T1", "T2", "T3", "T4"]
    page: str
    units: tuple[str, ...] = Field(min_length=1)
    batch: AuthoredBatch
    frame: CitationFrame
    unit_ref_note: str | None = None
    deferred: Deferred | None = None
    must_not: tuple[MustNot, ...]
    questions: tuple[Question, ...] = Field(min_length=1)
    phases: Phases
    sources: dict[str, JsonValue]

    def refs(self) -> set[str]:
        """Every local ref of the target, the deferred claims' included."""
        refs = {ref for _, ref in self.batch.local_refs()}
        if self.deferred is not None:
            refs |= {str(c["local_ref"]) for c in self.deferred.claims}
        return refs


# --- loaders -----------------------------------------------------------------------------------


def _read(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def load_s0(name: str) -> S0Fixture:
    return S0Fixture.model_validate(_read(S0_DIR / f"{name}.json"))


def load_segments(name: str) -> TraceSegments:
    return TraceSegments.model_validate(_read(TRACE_DIR / f"{name}.segments.json"))


def load_target(name: str) -> TraceTarget:
    return TraceTarget.model_validate(_read(TRACE_DIR / f"{name}.target.json"))
