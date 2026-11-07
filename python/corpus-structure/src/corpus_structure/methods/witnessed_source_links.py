"""Source-local link recipes over exact retained native text pieces."""

from __future__ import annotations

import re
from dataclasses import dataclass

QUESTION = "source_witnessed_links"
VERSION = "1"

# A recap names both the declared meaning and the literal occurrence used by
# the equation. A bare repeat of the same glyph is not a scope witness.
DECLARATION = re.compile(
    r"^Let (?P<symbol>[A-Za-z]) be (?P<description>a [^.\n]+)\. "
    r"A (?P<family>[^.\n]+?) with these parameters is said to be a (?P<name>[^.\n]+)\."
)
RECAP = re.compile(
    r"^We have seen above that it is possible to simulate a (?P<name>[^.\n]+) "
    r"(?P<symbol>[A-Za-z])\.[^.\n]*\bthe simulated values for (?P=symbol)"
    r" using the equation (?P<equation>[^.\n]+)\."
)
LET = re.compile(r"\bLet ([A-Za-z]) (?:be|denote|represent)\b")


@dataclass(frozen=True, slots=True)
class RecappedDeclaration:
    declaration_pointer: str
    use_pointer: str
    symbol: str
    name: tuple[int, int]
    declaration: tuple[int, int]
    recap: tuple[int, int]
    equation: tuple[int, int]
    scope: str
    passage: str
    effective_version: str | None


def recapped_declarations(text, pieces, items, passages):
    """Resolve a named recap only within one complete selected passage and parent."""
    physical = [
        p
        for p in pieces
        if p.get("kind") == "native_text"
        and p.get("source_field", "text") == "text"
        and "cell_index" not in p
        and items.get(p.get("item_ref"), {}).get("content_layer") == "body"
    ]
    for passage in passages or ():
        rows = [
            (p, items[p["item_ref"]], text[p["start"] : p["end"]])
            for p in physical
            if passage.start <= p["start"] < p["end"] <= passage.end
        ]
        for i, (piece, node, literal) in enumerate(rows):
            use = RECAP.match(literal)
            parent = node.get("parent")
            if use is None or parent is None:
                continue
            symbol, name = use["symbol"], use["name"]
            earlier = [
                (p, block)
                for p, other, block in rows[:i]
                if other.get("parent") == parent and symbol in LET.findall(block)
            ]
            if len(earlier) != 1 or LET.findall(earlier[0][1]).count(symbol) != 1:
                continue
            declaration, declaration_text = earlier[0]
            binding = DECLARATION.match(declaration_text)
            if (
                binding is None
                or binding["symbol"] != symbol
                or binding["name"] != name
                or not binding["description"].startswith(
                    "a " + binding["family"] + " with parameters "
                )
            ):
                continue

            def extent(start, match, group):
                return start + match.start(group), start + match.end(group)

            yield RecappedDeclaration(
                declaration["item_ref"],
                piece["item_ref"],
                symbol,
                extent(declaration["start"], binding, "name"),
                extent(declaration["start"], binding, "description"),
                (piece["start"], piece["start"] + use.end("symbol")),
                extent(piece["start"], use, "equation"),
                passage.scope,
                passage.passage_id,
                passage.effective_version,
            )


NAMED_QUESTION = "source_named_links"
_NAME = r"[A-Za-z][A-Za-z0-9_ -]{0,79}?"
_NAMED_LINK = re.compile(
    r"^(?P<left>" + _NAME + r") (?P<cue>is hereafter called|is renamed to|specializes|supersedes)"
    r" (?P<right>" + _NAME + r")\.$"
)
_ACRONYM = re.compile(
    r"^(?P<left>[A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+){1,7}) (?P<cue>\()(?P<right>[A-Z]{2,8})\)\.$"
)
SECTION_CUE = re.compile(
    r"\b(?P<cue>[Ss]ee|[Aa]s defined in) (?P<mention>Section (?P<code>[0-9]+(?:\.[0-9]+)+))\b"
)
_EXTERNAL_CUE = re.compile(
    r"\b(?P<cue>[Ss]ee) "
    r"(?P<mention>ISO(?:/IEC)? [0-9]+(?::[0-9]{4})?|RFC [0-9]+"
    r"|[A-Z][A-Za-z]+ and [A-Z][A-Za-z]+\.[0-9]+)(?=[. ,;)]|$)"
)
_SECTION_HEADING = re.compile(r"^(?:Section )?(?P<code>[0-9]+(?:\.[0-9]+)+)(?:\s|$)")
_KINDS = {
    "is hereafter called": "alias",
    "is renamed to": "renames",
    "specializes": "specializes",
    "supersedes": "supersedes",
}


@dataclass(frozen=True, slots=True)
class NamedLink:
    pointer: str
    kind: str
    left: tuple[int, int]
    cue: tuple[int, int]
    target_pointer: str | None
    right: tuple[int, int] | None
    scope: str
    passage: str
    resolution: str | None = None


def named_source_links(text, pieces, items, passages):
    """Resolve exact naming grammar and same-selection structural citations."""
    for passage in passages or ():
        rows = [
            (p["item_ref"], p["start"], text[p["start"] : p["end"]])
            for p in pieces
            if p.get("kind") == "native_text"
            and p.get("source_field", "text") == "text"
            and "cell_index" not in p
            and passage.start <= p["start"] < p["end"] <= passage.end
            and items.get(p["item_ref"], {}).get("content_layer") == "body"
        ]
        headings = {}
        for pointer, start, literal in rows:
            if items[pointer].get("label") == "section_header" and (
                heading := _SECTION_HEADING.match(literal)
            ):
                headings.setdefault(heading["code"], []).append(
                    (pointer, start, start + len(literal))
                )
        for pointer, start, literal in rows:
            if items[pointer].get("label") not in {"text", "paragraph", "list_item"}:
                continue

            def extent(match, group, start=start):
                a, b = match.span(group)
                return start + a, start + b

            if match := _NAMED_LINK.fullmatch(literal):
                if match["left"].casefold() != match["right"].casefold():
                    yield NamedLink(
                        pointer,
                        _KINDS[match["cue"]],
                        extent(match, "left"),
                        extent(match, "cue"),
                        pointer,
                        extent(match, "right"),
                        passage.scope,
                        passage.passage_id,
                    )
            elif (match := _ACRONYM.fullmatch(literal)) and (
                "".join(word[0] for word in match["left"].split()) == match["right"]
            ):
                yield NamedLink(
                    pointer,
                    "alias",
                    extent(match, "left"),
                    extent(match, "cue"),
                    pointer,
                    extent(match, "right"),
                    passage.scope,
                    passage.passage_id,
                )
            for match in SECTION_CUE.finditer(literal):
                targets = headings.get(match["code"], ())
                target = targets[0] if len(targets) == 1 else None
                yield NamedLink(
                    pointer,
                    "section_citation" if match["cue"].lower() == "see" else "definition_reference",
                    extent(match, "mention"),
                    extent(match, "cue"),
                    target[0] if target else None,
                    target[1:] if target else None,
                    passage.scope,
                    passage.passage_id,
                )
            for match in _EXTERNAL_CUE.finditer(literal):
                yield NamedLink(
                    pointer,
                    "external_citation",
                    extent(match, "mention"),
                    extent(match, "cue"),
                    None,
                    None,
                    passage.scope,
                    passage.passage_id,
                    "external_target_unavailable",
                )
