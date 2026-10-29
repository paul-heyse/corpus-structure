"""Evidence types and the rendition content digest (D1 §3.1, §3.2, §10.1; ADR-0019).

Foundations §3.3.

These are the in-memory shapes ingest (I1a) produces and the locator function (I0) reads:

- `SegmentKind` (generated in `vocab.py` from the model, with its member properties), the D1
  §3.2 kinds (email kinds included); M2 builds the CHECK on `kb.segment.kind` from the model;
- `Segment`, a range `[start, end)` of the canonical text with its kind, parse status and reason,
  author-markup `attrs` and children. Its cross-field invariants are the model's `KbSegment`
  declarations, applied by the generated validator (`_model/validators.py`; F01), so the segment
  and the stored row (M2's CHECK) accept the same values. Text is not stored on the node; it is
  the canonical text's substring. Children are sorted on validation (start, then the longer
  first, then kind), because siblings may overlap and the digest needs one order;
- `MacroDef`, one entry of a rendition's macro table (D4 M01);
- `RenditionContent`, the canonical text, the document root and the macro table, which is exactly
  what the content digest covers (D1 §3.2). Segments carry no diagnostics, so the digest needs no
  exclusion list; the search configuration is outside the model and so outside the digest.

The keys here are `doc`, `ren`, `seg` and `cfg` (D1 §10.1); their parts are named objects.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator, Mapping
from typing import Any, NamedTuple, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

from corpus_structure.core._model import validators
from corpus_structure.core.canonical import CanonicalJsonError, canonical_json, digest, make_key
from corpus_structure.core.vocab import DelimitingStatus, SegmentKind

# Macros are expanded by whole control-word name (D1 §6.2), so a name is a control word.
MACRO_NAME = r"^\\[A-Za-z]+$"


_SEVERITY: dict[DelimitingStatus, int] = {
    DelimitingStatus.OK: 0,
    DelimitingStatus.PARTIAL: 1,
    DelimitingStatus.FAILED: 2,
}


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class _StoredSegment(NamedTuple):
    """A segment's fields under the names of its `kb.segment` row, which the model's `KbSegment`
    invariants are declared on."""

    start_offset: int
    end_offset: int
    parse_status: DelimitingStatus
    parse_reason: str | None


def _child_order(segment: Segment) -> tuple[int, int, str]:
    return (segment.start, -segment.end, segment.kind.value)


class Segment(_Frozen):
    kind: SegmentKind
    start: int = Field(ge=0, strict=True)
    end: int = Field(ge=0, strict=True)
    parse_status: DelimitingStatus = DelimitingStatus.OK
    parse_reason: str | None = None
    attrs: dict[str, JsonValue] = Field(default_factory=dict)
    children: tuple[Segment, ...] = ()

    @field_validator("children")
    @classmethod
    def _sorted(cls, children: tuple[Segment, ...]) -> tuple[Segment, ...]:
        return tuple(sorted(children, key=_child_order))

    @model_validator(mode="after")
    def _well_formed(self) -> Self:
        stored = _StoredSegment(self.start, self.end, self.parse_status, self.parse_reason)
        validators.kb_segment(stored)  # ordered_eq(start, end); parse_reason absent iff ok
        try:  # author markup is content: refuse what the digest would refuse, here
            canonical_json(self.attrs)
        except CanonicalJsonError as error:
            raise ValueError(f"attrs are not canonical JSON: {error}") from None
        for child in self.children:
            if child.start < self.start or child.end > self.end:
                raise ValueError(
                    f"{child.kind} [{child.start}, {child.end}) lies outside its parent "
                    f"{self.kind} [{self.start}, {self.end})"
                )
        return self

    def walk(self) -> Iterator[Segment]:
        """This segment and its descendants, parents before children, children in order."""
        yield self
        for child in self.children:
            yield from child.walk()


class MacroDef(_Frozen):
    """A macro: `nargs` arguments, an optional default for an optional first one, and the body."""

    nargs: int = Field(default=0, ge=0, le=9)
    default: str | None = None
    body: str

    @model_validator(mode="after")
    def _default_needs_an_argument(self) -> Self:
        if self.default is not None and self.nargs == 0:
            raise ValueError("a macro with an optional default takes at least one argument")
        return self


class RenditionContent(_Frozen):
    """One content of a document: what the content digest covers (D1 §3.2)."""

    canonical_text: str
    document: Segment
    macros: dict[str, MacroDef] = Field(default_factory=dict)

    @field_validator("canonical_text")
    @classmethod
    def _nfc(cls, text: str) -> str:
        if not unicodedata.is_normalized("NFC", text):
            raise ValueError("canonical text must be NFC (offsets index its code points)")
        return text

    @field_validator("macros")
    @classmethod
    def _macro_names(cls, macros: dict[str, MacroDef]) -> dict[str, MacroDef]:
        for name in macros:
            if not re.match(MACRO_NAME, name):
                raise ValueError(f"macro name {name!r} is not a control word")
        return macros

    @model_validator(mode="after")
    def _tree(self) -> Self:
        root = self.document
        if root.kind is not SegmentKind.DOCUMENT:
            raise ValueError(f"the root segment is {root.kind}, not document")
        if (root.start, root.end) != (0, len(self.canonical_text)):
            raise ValueError(
                f"the document segment [{root.start}, {root.end}) does not span the text "
                f"[0, {len(self.canonical_text)})"
            )
        seen: set[tuple[str, int, int]] = set()
        for segment in root.walk():
            identity = (segment.kind.value, segment.start, segment.end)
            if identity in seen:
                raise ValueError(
                    f"two {segment.kind} segments at [{segment.start}, {segment.end}) "
                    "would share a segment key"
                )
            seen.add(identity)
        return self

    @property
    def parse_status(self) -> DelimitingStatus:
        """The worst parse status of the rendition's segments (derived, not part of the digest)."""
        worst = max(self.document.walk(), key=lambda s: _SEVERITY[s.parse_status])
        return worst.parse_status

    def text(self, segment: Segment) -> str:
        return self.canonical_text[segment.start : segment.end]


def content_digest(content: RenditionContent) -> str:
    """SHA-256 of the canonical JSON of the whole content: text, segment tree and macro table.

    Defaults are left out (`exclude_defaults`), so adding a defaulted field later moves no digest;
    a non-default parse status or reason, like every other field, is content."""
    return digest(content.model_dump(mode="json", exclude_defaults=True))


def document_key(project_name: str, source_uri: str, content_hash: str) -> str:
    """`doc` key: the project's name (never its database id), source URI, original bytes' hash."""
    return make_key(
        "doc", {"project": project_name, "source_uri": source_uri, "content_hash": content_hash}
    )


def rendition_key(document: str, content: str) -> str:
    """`ren` key: the document key and the rendition's content digest."""
    return make_key("ren", {"document": document, "content_digest": content})


def segment_key(rendition: str, kind: SegmentKind | str, start: int, end: int) -> str:
    """`seg` key: physical, so a segment key belongs to one rendition."""
    return make_key(
        "seg",
        {"rendition": rendition, "kind": SegmentKind(kind).value, "start": start, "end": end},
    )


def config_key(method: str, version: str, params: Mapping[str, Any]) -> str:
    """`cfg` key: method name, method version and canonical params (floats are refused)."""
    return make_key("cfg", {"method": method, "version": version, "params": dict(params)})
