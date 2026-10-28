"""Evidence types and the rendition content digest (D1 §3.1, §3.2, §10.1; ADR-0019).

Foundations §3.3.

These are the in-memory shapes ingest (I1a) produces and the locator function (I0) reads:

- `SegmentKind`, the D1 §3.2 kinds (email kinds included); 0001's CHECK on `kb.segment.kind` is
  built from it;
- `Segment`, a range `[start, end)` of the canonical text with its kind, parse status and reason,
  author-markup `attrs` and children. Text is not stored on the node; it is the canonical text's
  substring. Children are sorted on validation (start, then the longer first, then kind), because
  siblings may overlap and the digest needs one order;
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
from enum import StrEnum
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

from corpus_structure.core.canonical import digest, make_key

# The `attrs` key under which the store writes a segment's parse reason (D3 has no column for it),
# so author markup may not use it.
RESERVED_ATTR = "parse_reason"

MACRO_NAME = r"^\\(?:[A-Za-z]+|[^A-Za-z])$"


class SegmentKind(StrEnum):
    DOCUMENT = "document"
    SECTION = "section"
    UNIT = "unit"
    PARAGRAPH = "paragraph"
    LIST = "list"
    LIST_ITEM = "list_item"
    DETAILS = "details"
    MATH_DISPLAY = "math_display"
    MATH_INLINE = "math_inline"
    HEADING = "heading"
    TABLE = "table"
    TABLE_ROW = "table_row"
    TABLE_CELL = "table_cell"
    CAPTION = "caption"
    FOOTNOTE = "footnote"
    FIGURE = "figure"
    SENTENCE = "sentence"
    EMAIL_MESSAGE = "email_message"
    QUOTED_BLOCK = "quoted_block"
    SIGNATURE = "signature"


ParseStatus = Literal["ok", "partial", "failed"]
_SEVERITY: dict[str, int] = {"ok": 0, "partial": 1, "failed": 2}


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def _child_order(segment: Segment) -> tuple[int, int, str]:
    return (segment.start, -segment.end, segment.kind.value)


class Segment(_Frozen):
    kind: SegmentKind
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    parse_status: ParseStatus = "ok"
    parse_reason: str | None = None
    attrs: dict[str, JsonValue] = Field(default_factory=dict)
    children: tuple[Segment, ...] = ()

    @field_validator("children")
    @classmethod
    def _sorted(cls, children: tuple[Segment, ...]) -> tuple[Segment, ...]:
        return tuple(sorted(children, key=_child_order))

    @model_validator(mode="after")
    def _well_formed(self) -> Self:
        if self.start > self.end:
            raise ValueError(f"{self.kind} segment has start {self.start} > end {self.end}")
        if self.parse_status == "ok" and self.parse_reason is not None:
            raise ValueError("an ok segment has no parse_reason")
        if self.parse_status != "ok" and not self.parse_reason:
            raise ValueError(f"a {self.parse_status} segment needs its parse_reason")
        if RESERVED_ATTR in self.attrs:
            raise ValueError(f"attrs key {RESERVED_ATTR!r} is reserved for the store")
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
                raise ValueError(f"macro name {name!r} is not a control sequence")
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
    def parse_status(self) -> ParseStatus:
        """The worst parse status of the rendition's segments (derived, not part of the digest)."""
        worst = max(self.document.walk(), key=lambda s: _SEVERITY[s.parse_status])
        return worst.parse_status

    def text(self, segment: Segment) -> str:
        return self.canonical_text[segment.start : segment.end]


def content_digest(content: RenditionContent) -> str:
    """SHA-256 of the canonical JSON of the whole content: text, segment tree and macro table."""
    return digest(content.model_dump(mode="json"))


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
