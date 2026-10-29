"""A build's diagnostics: the `parse_detail` payload (`kb.rendition_build.parse_detail`; D4 M01).

The classes live in `core`, beside the other payload shapes, and ingest builds them. They equal
the `ParseDetail` payload class of `model/system.yaml` and its nested classes, field for field,
which the interim mirror guard checks (P0-M-1). The payload is registered as
`parse_detail` in the payload-schema registry, so O1's rendition write finds its schema. These are
parser-dependent diagnostics: they never enter segment attributes or the content digest (D1 §3.2).

This module imports only Pydantic and the generated vocabulary, so the core schema generator can
take its JSON Schema without loading the HTML parser.
"""

from __future__ import annotations

from pydantic import MISSING, BaseModel, ConfigDict, Field, JsonValue

from corpus_structure.core.vocab import SegmentKind


class _Detail(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ParserError(_Detail):
    """One html5lib parse error."""

    line: int
    column: int
    code: str


class RoleConflict(_Detail):
    """An element two exclusive profile roles claim."""

    tag: str
    classes: tuple[str, ...] = ()
    roles: tuple[str, ...] = Field(min_length=1)


class ExcludedElement(_Detail):
    """An element a profile exclusion rule removed (excluded text is recorded per rule)."""

    rule: str
    tag: str
    classes: tuple[str, ...] = ()
    chars: int


class MathAnomaly(_Detail):
    """A delimiting anomaly outside any math span (a stray closer)."""

    kind: str
    delimiter: str
    context: str


class OrphanRun(_Detail):
    """Text placed directly in a container, kept as an orphan paragraph."""

    container: SegmentKind
    text: str
    sourceline: int | MISSING = MISSING  # type: ignore[valid-type]


class UnicodeChange(_Detail):
    """A chunk of text NFC normalization changed."""

    before: str
    after: str


class ParseDetail(_Detail):
    """An ingest build's diagnostics, never part of the rendition's content."""

    encoding: str | MISSING = MISSING  # type: ignore[valid-type]
    parser_errors: tuple[ParserError, ...] = ()
    data_loss_warnings: int
    role_conflicts: tuple[RoleConflict, ...] = ()
    exclusions: tuple[ExcludedElement, ...] = ()
    math_anomalies: tuple[MathAnomaly, ...] = ()
    orphans: tuple[OrphanRun, ...] = ()
    unicode_changed: tuple[UnicodeChange, ...] = ()
    references_rendered: int = 0
    macro_notes: tuple[str, ...] = ()
    synthesize_notes: tuple[str, ...] = ()

    def to_json(self) -> dict[str, JsonValue]:
        return self.model_dump(mode="json")
