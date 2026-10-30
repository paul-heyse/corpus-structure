"""Operation-owned HTML5 lexical custody and source contribution transport.

html5lib 1.1 remains the tokenizer and tree-construction algorithm. The private
hooks here observe its stream, emission loop and lxml mutations. Upgrade these
hooks together with the pinned library; no global patch or second HTML parser is
used. Partitions and provenance coverage are deliberately independent.
"""

from __future__ import annotations

import codecs
import json
import re
from base64 import b64encode
from bisect import bisect_left, bisect_right
from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass, replace
from hashlib import sha256
from itertools import pairwise
from typing import Any

from html5lib import HTMLParser, _tokenizer, treebuilders
from html5lib.constants import EOF, _ReparseException, spaceCharacters, tokenTypes

_SPACE = re.compile(r"\s+|[^\s]+")
_NEWLINE = re.compile(r"\r\n|\r")
_TAG_SPACES = re.escape("".join(sorted(spaceCharacters)))
_TAG_PIECES = re.compile(f"[{_TAG_SPACES}]+|[\"'=<>/!]|[^{_TAG_SPACES}\"'=<>/!]+")
_NATIVE_BUILDER: Any = treebuilders.getTreeBuilder("lxml")


@dataclass(frozen=True, slots=True)
class Extent:
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class Contribution:
    length: int
    sources: tuple[Extent, ...]
    reason: str
    synthetic: bool = False


@dataclass(frozen=True, slots=True)
class Projection:
    start: int
    end: int
    sources: tuple[Extent, ...]
    category: str = "text"
    reason: str = "canonical normalization"
    synthetic: bool = False
    known: bool = True

    def shifted(self, offset: int) -> Projection:
        return replace(self, start=self.start + offset, end=self.end + offset)


def source_union(contributions: Any) -> tuple[Extent, ...]:
    # Keep encounter order, including reordered source pieces, without duplicating
    # the same occurrence when normalization combines adjacent contributions.
    return tuple(dict.fromkeys(s for item in contributions for s in item.sources))


@dataclass(frozen=True, slots=True)
class SourceProduct:
    """Immutable pure-producer result; semantic preparation is a publication port."""

    payload: bytes
    original: bytes

    def values(self) -> dict[str, Any]:
        return json.loads(self.payload)


class _Cursor:
    def __init__(self, native: Any) -> None:
        self.native = native
        self.cursor = 0
        self.state = "dataState"
        self.runs: list[tuple[int, int, str]] = []
        self.native_chunks: list[str] = []
        read_chunk = native.readChunk

        def observed_read_chunk(chunkSize: Any = None) -> bool:
            result = read_chunk(chunkSize)
            if result:
                self.native_chunks.append(native.chunk)
            return result

        native.readChunk = observed_read_chunk

    def __getattr__(self, name: str) -> Any:
        return getattr(self.native, name)

    def _consume(self, value: str | None) -> Any:
        if value is EOF or not value:
            return value
        start = self.cursor
        self.cursor += len(value)
        if self.runs and self.runs[-1][2] == self.state:
            a, _, state = self.runs[-1]
            self.runs[-1] = (a, self.cursor, state)
        else:
            self.runs.append((start, self.cursor, self.state))
        return value

    def char(self) -> Any:
        return self._consume(self.native.char())

    def charsUntil(self, characters: Any, opposite: bool = False) -> str:
        return self._consume(self.native.charsUntil(characters, opposite))

    def unget(self, value: Any) -> None:
        self.native.unget(value)
        if value is EOF:
            return
        self.cursor -= len(value)
        while self.runs and self.runs[-1][0] >= self.cursor:
            self.runs.pop()
        if self.runs and self.runs[-1][1] > self.cursor:
            a, _, state = self.runs[-1]
            self.runs[-1] = (a, self.cursor, state)


class _Tokenizer(_tokenizer.HTMLTokenizer):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.cursor_stream = _Cursor(self.stream)
        native: Any = self
        native.stream = self.cursor_stream
        self.records: list[dict[str, Any]] = []
        self.attributes: list[tuple[tuple[str, str], ...]] = []
        self.entities: list[Extent] = []
        self.emitted_tag: Any = None

    def consumeEntity(self, allowedChar: Any = None, fromAttribute: bool = False) -> None:
        start = self.cursor_stream.cursor - 1  # ampersand consumed by the calling native state
        super().consumeEntity(allowedChar=allowedChar, fromAttribute=fromAttribute)
        if self.cursor_stream.cursor > start + 1:
            self.entities.append(Extent(start, self.cursor_stream.cursor))

    def emitCurrentToken(self) -> None:
        token: Any = self.currentToken
        if token is None:
            raise ValueError("native tag emission has no token")
        if token["type"] == tokenTypes["StartTag"]:
            attributes = tuple((str(pair[0]), str(pair[1])) for pair in token["data"])
            self.attributes.append(attributes)
            token["_source_attributes"] = attributes
        super().emitCurrentToken()
        self.emitted_tag = token

    def __iter__(self) -> Iterator[Any]:
        # This is the upstream 1.1 emission loop with sidecar custody. State
        # implementations and parser feedback are unchanged.
        self.tokenQueue = deque()
        start = self.cursor_stream.cursor
        while True:
            state = self.state.__name__
            self.cursor_stream.state = state
            more = self.state()
            after = self.cursor_stream.cursor
            while self.stream.errors:
                yield {"type": tokenTypes["ParseError"], "data": self.stream.errors.pop(0)}
            count = sum(t["type"] != tokenTypes["ParseError"] for t in self.tokenQueue)
            while self.tokenQueue:
                token: Any = self.tokenQueue.popleft()
                if token["type"] != tokenTypes["ParseError"]:
                    identifier = len(self.records)
                    token["_source_id"] = identifier
                    self.records.append(
                        dict(token, start=start, end=after, state=state, shared=count > 1)
                    )
                    self.parser.tree.active_sources = (identifier,)
                yield token
            if count:
                start = after
            if not more:
                token: Any = self.currentToken
                if (
                    token is not None
                    and token is not self.emitted_tag
                    and token["type"] in (tokenTypes["StartTag"], tokenTypes["EndTag"])
                ):
                    record: dict[str, Any] = dict(
                        token,
                        start=start,
                        end=after,
                        state="unfinished-tag",
                        shared=False,
                        unfinished=True,
                    )
                    record["_source_attributes"] = tuple(
                        (str(pair[0]), str(pair[1])) for pair in token["data"]
                    )
                    self.records.append(record)
                break


class _Builder(_NATIVE_BUILDER):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.active_sources: tuple[int, ...] = ()
        self.tokenizer: _Tokenizer | None = None
        self.nodes: dict[Any, dict[str, Any]] = {}
        self.slots: dict[tuple[Any, str], tuple[Contribution, ...]] = {}
        self.clones: list[tuple[str, str]] = []
        self.initial_comment_sources: deque[int] = deque()
        self.creating_initial_comments = False
        super().__init__(*args, **kwargs)
        native_element: Any = self.elementClass
        owner = self

        class Element(native_element):
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                super().__init__(*args, **kwargs)
                owner.nodes[self._element] = dict(
                    node_id=f"n{len(owner.nodes)}",
                    kind="element",
                    name=str(self._element.tag),
                    origin="synthetic",
                    origin_reason="HTML5 implied or reconstructed element",
                )

            def cloneNode(self):
                result = super().cloneNode()
                owner.clones.append(
                    (owner.nodes[result._element]["node_id"], owner.nodes[self._element]["node_id"])
                )
                return result

            def insertText(self, data: str, insertBefore: Any = None) -> None:
                element, slot = owner._destination(self, insertBefore)
                before = getattr(element, slot) or ""
                super().insertText(data, insertBefore)
                added = (getattr(element, slot) or "")[len(before) :]
                if added:
                    sources = owner._sources()
                    reason = "HTML5 text insertion"
                    if owner.tokenizer is not None:
                        emitted = "".join(
                            str(owner.tokenizer.records[i].get("data", ""))
                            for i in owner.active_sources
                        )
                        if added != emitted:
                            reason = "HTML5 text filtering or partial token insertion"
                    key = (element, slot)
                    owner.slots[key] = (
                        *owner.slots.get(key, ()),
                        Contribution(len(added), sources, reason),
                    )

            def reparentChildren(self, newParent: Any) -> None:
                # Native etree moves this node's text into the destination's last
                # tail/text, then reparents children with their existing tails.
                destination = owner._destination(newParent, None)
                key = (self._element, "text")
                contributions = owner.slots.pop(key, ())
                super().reparentChildren(newParent)
                if contributions:
                    owner.slots[destination] = (*owner.slots.get(destination, ()), *contributions)

        native_comment: Any = self.commentClass

        class Comment(native_comment):
            def __init__(self, data: str) -> None:
                super().__init__(data)
                owner.nodes[self._element] = dict(
                    node_id=f"n{len(owner.nodes)}",
                    kind="comment",
                    value=str(self._element.text),
                    origin="synthetic",
                    origin_reason="HTML5 comment without qualified lexical origin",
                )
                identifiers = (
                    (owner.initial_comment_sources.popleft(),)
                    if owner.creating_initial_comments and owner.initial_comment_sources
                    else owner.active_sources
                )
                if (
                    owner.tokenizer is not None
                    and len(identifiers) == 1
                    and owner.tokenizer.records[identifiers[0]]["type"] == tokenTypes["Comment"]
                ):
                    owner._literal(self, {"_source_id": identifiers[0]})

        self.elementClass = Element
        self.commentClass = Comment

    def insertRoot(self, token: dict[str, Any]) -> None:
        self.initial_comment_sources = deque(item["_source_id"] for item in self.initial_comments)
        self.creating_initial_comments = True
        try:
            super().insertRoot(token)
            self._literal(self.openElements[0], token)
        finally:
            self.creating_initial_comments = False

    def reset(self) -> None:
        super().reset()
        self.nodes.clear()
        self.slots.clear()
        self.clones.clear()
        self.active_sources = ()
        self.initial_comment_sources.clear()
        self.creating_initial_comments = False

    @staticmethod
    def _destination(parent: Any, before: Any) -> tuple[Any, str]:
        if not len(parent._element):
            return parent._element, "text"
        if before is None:
            return parent._element[-1], "tail"
        children = list(parent._element)
        index = children.index(before._element)
        return (children[index - 1], "tail") if index else (parent._element, "text")

    def _sources(self) -> tuple[Extent, ...]:
        if self.tokenizer is None:
            return ()
        if any(self.tokenizer.records[i]["shared"] for i in self.active_sources):
            return ()
        return tuple(
            Extent(self.tokenizer.records[i]["start"], self.tokenizer.records[i]["end"])
            for i in self.active_sources
        )

    def _literal(self, result: Any, token: dict[str, Any]) -> Any:
        identifier = token.get("_source_id")
        if identifier is not None and self.tokenizer is not None:
            record = self.tokenizer.records[identifier]
            row = dict(self.nodes[result._element])
            row.pop("origin_reason", None)
            row.update(
                origin="literal",
                representation_id="decoded",
                unit="codepoint",
                start_offset=record["start"],
                end_offset=record["end"],
            )
            self.nodes[result._element] = row
        return result

    def insertElementNormal(self, token: dict[str, Any]) -> Any:
        return self._literal(super().insertElementNormal(token), token)

    def createElement(self, token: dict[str, Any]) -> Any:
        return self._literal(super().createElement(token), token)

    def reconstructActiveFormattingElements(self) -> None:
        before = tuple(self.activeFormattingElements)
        super().reconstructActiveFormattingElements()
        for old, new in zip(before, self.activeFormattingElements, strict=False):
            if old is not new and hasattr(old, "_element") and hasattr(new, "_element"):
                pair = (self.nodes[new._element]["node_id"], self.nodes[old._element]["node_id"])
                if pair not in self.clones:
                    self.clones.append(pair)


class CaptureParser(HTMLParser):
    """One stateful native parser and contribution sidecar per source operation."""

    def __init__(self) -> None:
        super().__init__(tree=_Builder, namespaceHTMLElements=False)
        self.encodings: list[str] = []
        native_phase: Any = type(self.phases["inTableText"])

        class TableText(native_phase):
            def flushCharacters(phase: Any) -> Any:
                before = phase.tree.active_sources
                phase.tree.active_sources = tuple(t["_source_id"] for t in phase.characterTokens)
                try:
                    return super().flushCharacters()
                finally:
                    phase.tree.active_sources = before

        self.phases["inTableText"] = TableText(self, self.tree)

    def _parse(
        self,
        stream: Any,
        innerHTML: bool = False,
        container: str = "div",
        scripting: bool = False,
        **kwargs: Any,
    ) -> None:
        self.innerHTMLMode, self.container, self.scripting = innerHTML, container, scripting
        tokenizer = _Tokenizer(stream, parser=self, **kwargs)
        self.tokenizer = tokenizer
        self.source_tokenizer = tokenizer
        self.tree.tokenizer = tokenizer
        self.reset()
        self.encodings = [self.tokenizer.stream.charEncoding[0].name]
        try:
            self.mainLoop()
        except _ReparseException:
            self.source_tokenizer.records.clear()
            self.source_tokenizer.attributes.clear()
            self.source_tokenizer.entities.clear()
            self.source_tokenizer.cursor_stream.cursor = 0
            self.source_tokenizer.cursor_stream.runs.clear()
            self.source_tokenizer.cursor_stream.native_chunks.clear()
            self.encodings.append(self.tokenizer.stream.charEncoding[0].name)
            self.reset()
            self.mainLoop()


@dataclass(frozen=True, slots=True)
class Lexeme:
    start: int
    end: int
    category: str


def _append(rows: list[Lexeme], start: int, end: int, category: str) -> None:
    if start == end:
        return
    if rows and rows[-1].end == start and rows[-1].category == category:
        rows[-1] = Lexeme(rows[-1].start, end, category)
    else:
        rows.append(Lexeme(start, end, category))


def _tag_category(state: str, value: str) -> str:
    is_space = all(character in spaceCharacters for character in value)
    if state in {"attributeValueDoubleQuotedState", "attributeValueSingleQuotedState"}:
        quote = '"' if state == "attributeValueDoubleQuotedState" else "'"
        return "attribute_delimiter" if value == quote else "attribute_value"
    if state == "attributeValueUnQuotedState":
        return "whitespace" if is_space else "tag_close" if value == ">" else "attribute_value"
    if state == "beforeAttributeValueState":
        return (
            "whitespace"
            if is_space
            else "attribute_delimiter"
            if value in ('"', "'")
            else "tag_close"
            if value == ">"
            else "attribute_value"
        )
    if state == "afterAttributeValueState":
        return "whitespace" if is_space else "tag_close" if value in ("/", ">") else "malformed"
    if is_space:
        return "whitespace"
    if state in {"attributeNameState", "beforeAttributeNameState", "afterAttributeNameState"}:
        return (
            "attribute_delimiter"
            if value == "="
            else "tag_close"
            if value in ("/", ">")
            else "attribute_name"
        )
    if value in ("<", "/", ">", "!"):
        return "tag_open" if value in ("<", "!") else "tag_close"
    return "tag_name"


def lexical_partition(source: str, tokenizer: _Tokenizer) -> tuple[Lexeme, ...]:
    """Use emitted native envelopes and consumed-state runs; never reparse markup."""
    tokens = tokenizer.records
    boundaries = {0, len(source)}
    for row in tokens:
        boundaries.update((row["start"], row["end"]))
    for start, end, _ in tokenizer.cursor_stream.runs:
        boundaries.update((start, end))
    for extent in tokenizer.entities:
        boundaries.update((extent.start, extent.end))
    # Delimiter/whitespace boundaries are native lexical values, not a second
    # grammar: classify them only inside a native tag envelope.
    for row in tokens:
        if row["type"] in (tokenTypes["StartTag"], tokenTypes["EndTag"]):
            for match in _TAG_PIECES.finditer(source[row["start"] : row["end"]]):
                boundaries.update((row["start"] + match.start(), row["start"] + match.end()))
    ordered = sorted(boundaries)
    token_starts = {token["start"] for token in tokens}
    result: list[Lexeme] = []
    ti = si = ei = 0
    for start, end in pairwise(ordered):
        while ti < len(tokens) and tokens[ti]["end"] <= start:
            ti += 1
        while (
            si < len(tokenizer.cursor_stream.runs) and tokenizer.cursor_stream.runs[si][1] <= start
        ):
            si += 1
        while ei < len(tokenizer.entities) and tokenizer.entities[ei].end <= start:
            ei += 1
        row = tokens[ti] if ti < len(tokens) and tokens[ti]["start"] <= start else None
        state = (
            tokenizer.cursor_stream.runs[si][2]
            if si < len(tokenizer.cursor_stream.runs)
            else "unknown"
        )
        value = source[start:end]
        category = "malformed"
        if row is not None:
            kind = row["type"]
            if kind == tokenTypes["Comment"]:
                category = "comment"
            elif kind == tokenTypes["Doctype"]:
                category = "doctype"
            elif kind in (tokenTypes["StartTag"], tokenTypes["EndTag"]):
                category = _tag_category(state, value)
            else:
                category = (
                    "raw_text"
                    if any(s in row["state"].lower() for s in ("script", "rawtext", "cdata"))
                    else "text"
                )
                if value.isspace():
                    category = "whitespace"
        if "\x00" in value:
            category = "malformed"
        if (
            ei < len(tokenizer.entities)
            and tokenizer.entities[ei].start <= start
            and end <= tokenizer.entities[ei].end
        ):
            category = "character_reference"
        if start in token_starts:
            result.append(Lexeme(start, end, category))
        else:
            _append(result, start, end, category)
    return tuple(result)


def _decode(raw: bytes, encoding: str) -> tuple[str, list[tuple[int, int, int, int]]]:
    """Decode using the native selected codec; grouped contributions retain errors.

    Reversible UTF-8/single-byte input uses native bulk decoding. Only sources
    containing decoder replacement or a stateful/non-reversible codec need the
    incremental contribution fallback. No per-byte events enter the product.
    """
    skip = 0
    for marker, codec in (
        (codecs.BOM_UTF8, "utf-8"),
        (codecs.BOM_UTF16_LE, "utf-16le"),
        (codecs.BOM_UTF16_BE, "utf-16be"),
    ):
        if raw.startswith(marker) and encoding.replace("-", "") == codec.replace("-", ""):
            skip = len(marker)
            break
    source = raw[skip:].decode(encoding, errors="replace")
    try:
        reversible = source.encode(encoding) == raw[skip:]
    except UnicodeEncodeError:
        reversible = False
    if reversible and (encoding == "utf-8" or len(source) == len(raw) - skip):
        return source, [(0, skip, 0, 0)] if skip else []
    decoder = codecs.getincrementaldecoder(encoding)(errors="replace")
    groups: list[tuple[int, int, int, int]] = [(0, skip, 0, 0)] if skip else []
    byte_start, text_start = skip, 0
    for end in range(skip + 1, len(raw) + 1):
        value = decoder.decode(raw[end - 1 : end], final=False)
        if value:
            groups.append((byte_start, end, text_start, text_start + len(value)))
            byte_start, text_start = end, text_start + len(value)
    value = decoder.decode(b"", final=True)
    if value:
        groups.append((byte_start, len(raw), text_start, text_start + len(value)))
        byte_start, text_start = len(raw), text_start + len(value)
    if byte_start < len(raw):
        groups.append((byte_start, len(raw), text_start, text_start))
    return source, groups


class SourceCapture:
    def __init__(self, raw: bytes, parser: CaptureParser) -> None:
        self.raw = raw
        self.parser = parser
        encoding = parser.documentEncoding
        if encoding is None:
            raise ValueError("HTML byte parser did not select an encoding")
        # Web encoding labels are not necessarily Python codec aliases (for example
        # windows-874 and macintosh). Reuse the exact codec selected by the native
        # input stream, including after an encoding restart.
        self.encoding = parser.source_tokenizer.cursor_stream.charEncoding[0].codec_info.name
        self.decoded, self.decoder_groups = _decode(raw, self.encoding)
        self.source = self.decoded.replace("\r\n", "\n").replace("\r", "\n")
        cursor = parser.source_tokenizer.cursor_stream
        if len(self.source) != cursor.cursor or "".join(cursor.native_chunks) != self.source:
            raise ValueError("native decoder and source-capture coordinate spaces differ")
        cursor.native_chunks.clear()
        self.lexemes = lexical_partition(self.source, parser.source_tokenizer)
        used = {
            source for rows in parser.tree.slots.values() for row in rows for source in row.sources
        }
        self.exclusions: list[tuple[tuple[Extent, ...], str]] = [
            ((Extent(token["start"], token["end"]),), "HTML5 ignored NUL character")
            for token in parser.source_tokenizer.records
            if token.get("data") == "\x00" and Extent(token["start"], token["end"]) not in used
        ]

    def slot(self, element: Any, name: str) -> tuple[Contribution, ...]:
        value = getattr(element, name) or ""
        rows = self.parser.tree.slots.get((element, name), ())
        if sum(row.length for row in rows) != len(value):
            return (
                (Contribution(len(value), (), "unavailable native text-slot origin"),)
                if value
                else ()
            )
        return rows

    def exclude(self, element: Any, reason: str) -> None:
        rows = [
            item
            for node in element.iter()
            for name in (("text",) if node is element else ("text", "tail"))
            for item in self.slot(node, name)
        ]
        sources = list(source_union(rows))
        sources.extend(
            Extent(record["start_offset"], record["end_offset"])
            for node in element.iter()
            if (record := self.parser.tree.nodes.get(node)) is not None
            and record["origin"] == "literal"
        )
        self.exclusions.append((tuple(dict.fromkeys(sources)), reason))

    def finish(self, canonical: str, projections: tuple[Projection, ...]) -> SourceProduct:
        components: list[dict[str, Any]] = []
        mappings: list[dict[str, Any]] = []
        endpoints: list[dict[str, Any]] = []

        def component(rep: str, unit: str, ordinal: int, row: Lexeme) -> None:
            components.append(
                dict(
                    component_id=f"{rep}:{ordinal}",
                    ordinal=ordinal,
                    category=row.category,
                    representation_id=rep,
                    unit=unit,
                    start_offset=row.start,
                    end_offset=row.end,
                )
            )

        for ordinal, row in enumerate(self.lexemes):
            component("decoded", "codepoint", ordinal, row)
        # Map normalized decoded boundaries back through newline preprocessing,
        # then through a reversible codec or grouped incremental decoder.
        crlf = tuple(match for match in _NEWLINE.finditer(self.decoded) if match.group() == "\r\n")
        crlf_normalized = tuple(match.start() - i for i, match in enumerate(crlf))
        crlf_ends = tuple(match.end() for match in crlf)

        def before_normalization(position: int) -> int:
            return position + bisect_left(crlf_normalized, position)

        def after_normalization(position: int) -> int:
            return position - bisect_right(crlf_ends, position)

        decoded_links: list[tuple[Extent, Extent]] = []
        decoder_exclusions: list[tuple[Extent, str]] = []
        raw_rows: list[Lexeme] = []
        if not self.decoder_groups or (
            len(self.decoder_groups) == 1 and self.decoder_groups[0][3] == 0
        ):
            byte_cursor = self.decoder_groups[0][1] if self.decoder_groups else 0
            if byte_cursor:
                _append(raw_rows, 0, byte_cursor, "encoding_marker")
                decoder_exclusions.append((Extent(0, byte_cursor), "encoding byte-order mark"))
            for row in self.lexemes:
                value = self.decoded[
                    before_normalization(row.start) : before_normalization(row.end)
                ]
                end = byte_cursor + len(value.encode(self.encoding))
                _append(raw_rows, byte_cursor, end, row.category)
                decoded_links.append((Extent(byte_cursor, end), Extent(row.start, row.end)))
                byte_cursor = end
        else:
            # A decoder group may emit several codepoints (e.g. invalid UTF-8
            # E2 41 -> replacement + A). Its byte extent is indivisible here.
            lexeme_index = 0
            for start, end, a, b in self.decoder_groups:
                while (
                    lexeme_index < len(self.lexemes)
                    and before_normalization(self.lexemes[lexeme_index].end) <= a
                ):
                    lexeme_index += 1
                row = self.lexemes[lexeme_index] if lexeme_index < len(self.lexemes) else None
                category = (
                    "encoding_marker"
                    if a == b
                    else "malformed"
                    if "\ufffd" in self.decoded[a:b]
                    else row.category
                    if row is not None and before_normalization(row.end) >= b
                    else "unknown"
                )
                previous_category = raw_rows[-1].category if raw_rows else None
                _append(raw_rows, start, end, category)
                target = Extent(after_normalization(a), after_normalization(b))
                if target.start == target.end:
                    decoder_exclusions.append(
                        (
                            Extent(start, end),
                            "encoding byte-order mark"
                            if start == 0
                            and self.raw[start:end]
                            in (codecs.BOM_UTF8, codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)
                            else "decoder state bytes with no decoded codepoints",
                        )
                    )
                else:
                    if (
                        decoded_links
                        and previous_category == category
                        and decoded_links[-1][0].end == start
                        and decoded_links[-1][1].end == target.start
                    ):
                        old_source, old_target = decoded_links.pop()
                        decoded_links.append(
                            (Extent(old_source.start, end), Extent(old_target.start, target.end))
                        )
                    else:
                        decoded_links.append((Extent(start, end), target))
        for ordinal, row in enumerate(raw_rows):
            component("raw", "byte", ordinal, row)
        canonical_rows: list[Lexeme] = []
        for projection in projections:
            for match in _SPACE.finditer(canonical[projection.start : projection.end]):
                category = (
                    projection.category
                    if projection.category in {"canonical_separator", "marker", "math", "reference"}
                    else "whitespace"
                    if match.group().isspace()
                    else "text"
                )
                _append(
                    canonical_rows,
                    projection.start + match.start(),
                    projection.start + match.end(),
                    category,
                )
        for ordinal, row in enumerate(canonical_rows):
            component("canonical", "codepoint", ordinal, row)

        def mapping(
            operation: str,
            reason: str,
            sources: tuple[Extent, ...],
            targets: tuple[Extent, ...],
            *,
            synthetic: bool = False,
            source_rep: str = "decoded",
            source_unit: str = "codepoint",
            target_rep: str = "canonical",
            known: bool = True,
        ) -> None:
            key = f"m{len(mappings)}"
            mappings.append(
                dict(
                    mapping_id=key,
                    operation=operation,
                    reason=reason,
                    fidelity="synthetic"
                    if synthetic
                    else "excluded"
                    if sources and not targets
                    else "transformed"
                    if known and sources and targets
                    else "unknown",
                )
            )
            for side, rows in (("source", sources), ("target", targets)):
                for ordinal, row in enumerate(rows):
                    endpoints.append(
                        dict(
                            mapping_id=key,
                            side=side,
                            ordinal=ordinal,
                            representation_id=source_rep if side == "source" else target_rep,
                            unit=source_unit if side == "source" else "codepoint",
                            start_offset=row.start,
                            end_offset=row.end,
                        )
                    )

        # Keep decoding as its own contribution, never call replacement decoding
        # exact byte identity. Individual malformed groups remain inspectable.
        for original, decoded in decoded_links:
            mapping(
                "decode",
                f"{self.parser.documentEncoding} replacement decoder; CRLF/CR to LF; "
                f"selected pass {len(self.parser.encodings)}",
                (original,),
                (decoded,),
                source_rep="raw",
                source_unit="byte",
                target_rep="decoded",
            )
        for source, reason in decoder_exclusions:
            mapping("exclude", reason, (source,), (), source_rep="raw", source_unit="byte")
        for projection in projections:
            mapping(
                "synthetic" if projection.synthetic else "normalize",
                projection.reason,
                projection.sources,
                (Extent(projection.start, projection.end),),
                synthetic=projection.synthetic,
                known=projection.known,
            )
        for sources, reason in self.exclusions:
            if sources:
                mapping("exclude", reason, sources, ())
        nodes = [
            dict(
                node_id="document",
                kind="document",
                name="#document",
                origin="synthetic",
                origin_reason="HTML5 document root",
            ),
            *self.parser.tree.nodes.values(),
        ]
        relationships: list[dict[str, Any]] = []
        relation_endpoints: list[dict[str, Any]] = []
        pairs = []
        native_ordinals = {
            child: ordinal
            for parent in self.parser.tree.nodes
            for ordinal, child in enumerate(parent)
        }
        for element, row in self.parser.tree.nodes.items():
            parent = element.getparent()
            if parent in self.parser.tree.nodes:
                row["ordinal"] = native_ordinals[element]
                pairs.append(
                    ("structural_parent", self.parser.tree.nodes[parent]["node_id"], row["node_id"])
                )
        native_root = self.parser.tree.document._elementTree.getroot()
        before = []
        sibling = native_root.getprevious()
        while sibling is not None:
            before.append(sibling)
            sibling = sibling.getprevious()
        following = []
        sibling = native_root.getnext()
        while sibling is not None:
            following.append(sibling)
            sibling = sibling.getnext()
        top_level = [*reversed(before), native_root, *following]
        for ordinal, element in enumerate(top_level):
            if element in self.parser.tree.nodes:
                self.parser.tree.nodes[element]["ordinal"] = ordinal
                pairs.append(
                    ("structural_parent", "document", self.parser.tree.nodes[element]["node_id"])
                )
        pairs.extend(("derived_from", target, source) for target, source in self.parser.tree.clones)
        for kind, first, second in pairs:
            key = f"r{len(relationships)}"
            relationships.append(dict(relationship_id=key, kind=kind))
            roles = ("parent", "child") if kind == "structural_parent" else ("target", "source")
            relation_endpoints.extend(
                dict(relationship_id=key, ordinal=i, role=role, node_id=node)
                for i, (role, node) in enumerate(zip(roles, (first, second), strict=True))
            )
        decoded_components = [(ordinal, row) for ordinal, row in enumerate(self.lexemes)]
        component_starts = tuple(row.start for _, row in decoded_components)
        for (element, slot), _ in self.parser.tree.slots.items():
            value = getattr(element, slot) or ""
            owner = self.parser.tree.nodes.get(element)
            if not value or owner is None:
                continue
            contributions = self.slot(element, slot)
            known = bool(contributions) and all(item.sources for item in contributions)
            identifier = f"text:{len(nodes)}"
            nodes.append(
                dict(
                    node_id=identifier,
                    kind="text",
                    name=slot,
                    value=value,
                    ordinal=0 if slot == "text" else 1,
                    origin="derived",
                    origin_reason="native final text slot"
                    if known
                    else "native final text slot with unavailable origin",
                )
            )
            key = f"r{len(relationships)}"
            relationships.append(dict(relationship_id=key, kind="text_of"))
            relation_endpoints.extend(
                (
                    dict(relationship_id=key, ordinal=0, role="text", node_id=identifier),
                    dict(relationship_id=key, ordinal=1, role="owner", node_id=owner["node_id"]),
                )
            )
            order = 0
            for contribution in contributions:
                for source in contribution.sources:
                    a, b = (
                        bisect_left(component_starts, source.start),
                        bisect_left(component_starts, source.end),
                    )
                    for ordinal, _component_row in decoded_components[a:b]:
                        key = f"r{len(relationships)}"
                        relationships.append(
                            dict(relationship_id=key, kind="derived_from", ordinal=order)
                        )
                        relation_endpoints.extend(
                            (
                                dict(
                                    relationship_id=key,
                                    ordinal=0,
                                    role="target",
                                    node_id=identifier,
                                ),
                                dict(
                                    relationship_id=key,
                                    ordinal=1,
                                    role="source",
                                    component_id=f"decoded:{ordinal}",
                                ),
                            )
                        )
                        order += 1

        # Attribute occurrences use pre-deduplication native order and consumed
        # lexical boundaries. Empty/boolean values still have a nonempty whole
        # attribute extent; no zero-length lexical partition component is invented.
        attribute_complete = True
        lexical_starts = tuple(row.start for row in self.lexemes)
        state_runs = self.parser.source_tokenizer.cursor_stream.runs
        state_starts = tuple(row[0] for row in state_runs)
        node_names = {row["node_id"]: row.get("name", "") for row in nodes}
        literal_owners: dict[tuple[int, int], list[str]] = {}
        for row in nodes:
            if row["origin"] == "literal":
                literal_owners.setdefault(
                    (int(row["start_offset"]), int(row["end_offset"])), []
                ).append(str(row["node_id"]))
        for token in self.parser.source_tokenizer.records:
            attributes = token.get("_source_attributes", ())
            if not attributes:
                continue
            first = bisect_left(lexical_starts, token["start"])
            last = bisect_left(lexical_starts, token["end"])
            names = [row for row in self.lexemes[first:last] if row.category == "attribute_name"]
            if len(names) != len(attributes):
                attribute_complete = False
                continue
            owners = literal_owners.get((token["start"], token["end"]), ())
            seen = set()
            for ordinal, ((name, value), lexical_name) in enumerate(
                zip(attributes, names, strict=True)
            ):
                following = names[ordinal + 1].start if ordinal + 1 < len(names) else token["end"]
                a, b = (
                    bisect_left(lexical_starts, lexical_name.start),
                    bisect_left(lexical_starts, following),
                )
                parts = [
                    row
                    for row in self.lexemes[a:b]
                    if row.category not in {"whitespace", "tag_close"}
                ]
                end = max((row.end for row in parts), default=lexical_name.end)
                identifier = f"a{len(nodes)}"
                outcome = (
                    "discarded_duplicate" if name in seen else "retained" if owners else "unknown"
                )
                seen.add(name)
                adjusted: dict[str, Any] = {"data": {name: value}}
                owner_name = node_names.get(owners[0], "") if owners else ""
                if owner_name.startswith("{http://www.w3.org/2000/svg}"):
                    self.parser.adjustSVGAttributes(adjusted)
                    self.parser.adjustForeignAttributes(adjusted)
                elif owner_name.startswith("{http://www.w3.org/1998/Math/MathML}"):
                    self.parser.adjustMathMLAttributes(adjusted)
                    self.parser.adjustForeignAttributes(adjusted)
                qualified = next(iter(adjusted["data"]))
                if isinstance(qualified, tuple):
                    local_name = self.parser.tree.infosetFilter.coerceAttribute(qualified[1])
                    qualified = f"{{{qualified[2]}}}{local_name}"
                else:
                    qualified = self.parser.tree.infosetFilter.coerceAttribute(qualified)
                attribute = dict(
                    node_id=identifier,
                    kind="attribute",
                    name=qualified,
                    value=value,
                    ordinal=ordinal,
                    attribute_outcome=outcome,
                    origin="literal",
                    representation_id="decoded",
                    unit="codepoint",
                    start_offset=lexical_name.start,
                    end_offset=end,
                    name_start_offset=lexical_name.start,
                    name_end_offset=lexical_name.end,
                )
                a, b = bisect_left(state_starts, lexical_name.start), bisect_left(state_starts, end)
                value_open = next(
                    (
                        stop - 1
                        for start, stop, state in state_runs[a:b]
                        if state == "beforeAttributeValueState"
                        and self.source[stop - 1 : stop] in ('"', "'")
                    ),
                    None,
                )
                value_parts = [
                    row
                    for row in parts
                    if row.category in {"attribute_value", "character_reference"}
                ]
                if value_open is not None:
                    # The opening quote is consumed by beforeAttributeValueState;
                    # the emitted complete tag's final attribute character is its
                    # matching native closing quote. Empty quoted values retain
                    # an explicit zero-width value extent, outside the partition.
                    attribute.update(
                        value_start_offset=value_open + 1,
                        value_end_offset=end if token.get("unfinished") else end - 1,
                    )
                elif value_parts:
                    attribute.update(
                        value_start_offset=value_parts[0].start,
                        value_end_offset=value_parts[-1].end,
                    )
                nodes.append(attribute)
                for owner in owners:
                    key = f"r{len(relationships)}"
                    relationships.append(dict(relationship_id=key, kind="attribute_of"))
                    relation_endpoints.extend(
                        (
                            dict(
                                relationship_id=key, ordinal=0, role="attribute", node_id=identifier
                            ),
                            dict(relationship_id=key, ordinal=1, role="owner", node_id=owner),
                        )
                    )
        representations = [
            dict(
                representation_id="raw",
                kind="original",
                unit="byte",
                extent_length=len(self.raw),
                partition_state="complete",
                recognition_state="partial"
                if any(r.category == "unknown" for r in raw_rows)
                else "complete",
            ),
            dict(
                representation_id="decoded",
                kind="decoded",
                unit="codepoint",
                extent_length=len(self.source),
                text_content=self.source,
                partition_state="complete",
                recognition_state="complete" if attribute_complete else "partial",
                encoding=self.parser.documentEncoding,
                decoder=f"html5lib-1.1/{self.encoding}/replace",
                newline_policy="CRLF/CR to LF",
            ),
            dict(
                representation_id="canonical",
                kind="canonical",
                unit="codepoint",
                extent_length=len(canonical),
                text_content=canonical,
                partition_state="complete",
                recognition_state="complete",
            ),
        ]
        if "\x00" in self.source:
            representations[1]["text_content_utf8_base64"] = b64encode(
                self.source.encode("utf-8")
            ).decode("ascii")
            del representations[1]["text_content"]
        value = dict(
            recipe="source-products-v1",
            adapter_id="html5lib-source-1",
            provenance_universe="canonical_output",
            artifact_digest=sha256(self.raw).hexdigest(),
            lifecycle="available",
            semantic_state="ok",
            provenance_state="complete"
            if all(m["fidelity"] != "unknown" for m in mappings)
            else "partial",
            representations=representations,
            components=components,
            nodes=nodes,
            relationships=relationships,
            endpoints=relation_endpoints,
            mappings=mappings,
            mapping_endpoints=endpoints,
        )
        return SourceProduct(
            json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(),
            self.raw,
        )
