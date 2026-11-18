"""`tooling library overview FILE`: the section map of a library overview, with its stated
target version beside the installed one.

Headings come from markdown-it-py (D5): `heading_open` tokens carry their level and line map, and
fenced or indented code is its own token, so a `#` line inside code is never a heading.

- **Parts.** Each level-one heading opens a part: the first is the main text, later ones are
  addenda (`addendum 1`, `addendum 2`, ...). A part runs to the next level-one heading.
- **Sections.** Level-two headings within a part, numbered when the title starts with `N.` or
  `N`. A section runs to the next level-one or level-two heading. Deeper headings are not
  listed.
- **Flags.** `title_only_number` (a numbered section with no title, such as `## 5`),
  `numbering_gap` (a number more than one past the previous numbered section of the part, or a
  part's first number above 1), `numbering_out_of_order` (a number not above the previous one),
  `empty_title`, and `before_first_part` (a level-two heading before any level-one heading).
- **Version.** For each part, the version its title or opening lines (before its first section)
  state, from the first labelled statement (`Target: Rich 15.0.0`, `Target version: 0.51.0`,
  `Version: 0.0.101`, `Current stable release: 2.4.1`, ...) or else a version in the title
  (`# LibCST 1.9.0 — Capability Addendum`). It is compared with the version installed in the
  target for the overview's distribution (`--distribution`, default the file's stem). When no
  version is stated the field is null; nothing is guessed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, ClassVar, Literal

import typer
from markdown_it import MarkdownIt
from markdown_it import __version__ as markdown_it_version

from corpus_tooling.envelope import Column, Item, UnavailableMetadata
from corpus_tooling.library.context import library_envelope, library_state
from corpus_tooling.library.installed import Installation, normalize_name
from corpus_tooling.output import (
    DEFAULT_LIMIT,
    JsonOpt,
    LimitOpt,
    OffsetOpt,
    StrictOpt,
    ToolFailure,
    emit,
)

Role = Literal["part", "section"]
VersionStatus = Literal["same", "overview_newer", "overview_older", "not_comparable"]
Flag = Literal[
    "title_only_number",
    "numbering_gap",
    "numbering_out_of_order",
    "empty_title",
    "before_first_part",
]

_VERSION = r"v?(?P<version>\d+(?:\.\d+)+(?:(?:a|b|rc|\.post|\.dev)\d+)?)\b"
_LABEL = (
    r"Target(?:\s+(?:version|release|library))?"
    r"|Version(?:\s+scope)?"
    r"|(?:(?:Current|Latest)\s+(?:verified\s+)?)?(?:stable\s+)?(?:PyPI\s+|package\s+)?"
    r"(?:release|version)"
)
# A label followed by a colon (`Target: Rich 15.0.0`), or `Version 3.7` opening a line or a
# `·`/`|`-separated field. Prose such as "the latest stable release. Typer 0.28.0" is not one.
_LABELLED = re.compile(
    r"(?:(?<![\w-])(?P<label>" + _LABEL + r")\s*:|(?:^|[·|])\s*[*_]*Version)\s*"
    r"(?P<subject>(?:[^\s:·|]+\s+){0,4}?)" + _VERSION,
    re.IGNORECASE,
)
_TITLED = re.compile(r"^(?P<subject>[^—:|(]+?)\s+" + _VERSION)
_NUMBERED = re.compile(r"^(?P<number>\d+(?:\.\d+)*)\.?(?:\s+|$)(?P<rest>.*)$")
_RELEASE = re.compile(r"^(\d+(?:\.\d+)*)")


# --- reading the document --------------------------------------------------------------------


@dataclass(frozen=True)
class Heading:
    level: int
    line: int
    """1-based line of the heading."""
    title: str


@dataclass(frozen=True)
class StatedVersion:
    version: str
    subject: str | None
    text: str
    line: int


@dataclass(frozen=True)
class OverviewSection:
    role: Role
    part: str
    level: int
    line: int
    end_line: int
    number: str | None
    title: str
    flags: tuple[Flag, ...]
    stated: StatedVersion | None = None


def _parse(text: str) -> list[tuple[str, int, int, str]]:
    """(type, level, 1-based line, inline content) for headings and opening-text inlines."""
    tokens = MarkdownIt("commonmark").parse(text)
    found: list[tuple[str, int, int, str]] = []
    for index, token in enumerate(tokens):
        if token.map is None:
            continue
        if token.type == "heading_open":
            inline = tokens[index + 1] if index + 1 < len(tokens) else None
            content = inline.content if inline is not None and inline.type == "inline" else ""
            found.append(("heading", int(token.tag[1:]), token.map[0] + 1, content.strip()))
        elif token.type == "inline" and tokens[index - 1].type != "heading_open":
            found.append(("text", 0, token.map[0] + 1, token.content))
    return found


def stated_version(
    title: str, title_line: int, opening: list[tuple[int, str]]
) -> StatedVersion | None:
    """The first labelled version statement in the title or opening lines, else a version in
    the title; `None` when neither states one."""
    for line, content in [(title_line, title), *opening]:
        for offset, physical in enumerate(content.splitlines()):
            match = _LABELLED.search(physical)
            if match:
                subject = match["subject"].strip().strip("`*_ ") or None
                return StatedVersion(match["version"], subject, match[0].strip(), line + offset)
    match = _TITLED.match(title.strip("*_ "))
    if match:
        return StatedVersion(
            match["version"], match["subject"].strip("`*_ "), match[0].strip(), title_line
        )
    return None


def section_map(text: str) -> list[OverviewSection]:
    """Parts and level-two sections of an overview, in document order."""
    entries = _parse(text)
    total = len(text.splitlines())
    headings = [(level, line, title) for kind, level, line, title in entries if kind == "heading"]

    def end_of(position: int, levels: int) -> int:
        for level, line, _ in headings[position + 1 :]:
            if level <= levels:
                return line - 1
        return total

    sections: list[OverviewSection] = []
    part_index = -1
    previous_number = 0
    for position, (level, line, title) in enumerate(headings):
        if level == 1:
            part_index += 1
            previous_number = 0
            end = end_of(position, 1)
            following = [h for h in headings[position + 1 :] if h[0] <= 2]
            opening_end = following[0][1] if following else end + 1
            opening = [
                (text_line, content)
                for kind, _, text_line, content in entries
                if kind == "text" and line < text_line < opening_end
            ]
            sections.append(
                OverviewSection(
                    role="part",
                    part=_part_label(part_index),
                    level=1,
                    line=line,
                    end_line=end,
                    number=None,
                    title=title,
                    flags=("empty_title",) if not title else (),
                    stated=stated_version(title, line, opening),
                )
            )
        elif level == 2:
            flags: list[Flag] = []
            number = None
            shown = title
            match = _NUMBERED.match(title)
            if match:
                number, shown = match["number"], match["rest"].strip()
                if not shown:
                    flags.append("title_only_number")
                if "." not in number:
                    value = int(number)
                    if value > previous_number + 1:
                        flags.append("numbering_gap")
                    elif value <= previous_number:
                        flags.append("numbering_out_of_order")
                    previous_number = value
            elif not title:
                flags.append("empty_title")
            if part_index < 0:
                flags.append("before_first_part")
            sections.append(
                OverviewSection(
                    role="section",
                    part=_part_label(part_index),
                    level=2,
                    line=line,
                    end_line=end_of(position, 2),
                    number=number,
                    title=shown,
                    flags=tuple(flags),
                )
            )
    return sections


def _part_label(index: int) -> str:
    if index < 0:
        return "preamble"
    return "main" if index == 0 else f"addendum {index}"


def compare_versions(stated: str, installed: str) -> VersionStatus:
    """Compare the numeric release parts (`5.3.2` equals `5.3.2.0`); anything else that
    differs is `not_comparable`."""
    if stated == installed:
        return "same"
    left, right = _RELEASE.match(stated), _RELEASE.match(installed)
    if left is None or right is None:
        return "not_comparable"
    a = [int(part) for part in left[1].split(".")]
    b = [int(part) for part in right[1].split(".")]
    width = max(len(a), len(b))
    a += [0] * (width - len(a))
    b += [0] * (width - len(b))
    if a == b:
        # Same release numbers with different suffixes (`2.0rc1` against `2.0`).
        return "same" if left[0] == stated and right[0] == installed else "not_comparable"
    return "overview_newer" if a > b else "overview_older"


# --- the command -----------------------------------------------------------------------------


class OverviewEntry(Item):
    kind: Literal["overview_section"] = "overview_section"
    role: Role
    part: str
    level: int
    line: int
    end_line: int
    number: str | None
    title: str
    flags: list[Flag]
    stated_version: str | None = None
    stated_subject: str | None = None
    stated_text: str | None = None
    stated_line: int | None = None
    distribution: str | None = None
    installed_version: str | None = None
    version_status: VersionStatus | None = None

    columns: ClassVar = (
        Column("line"),
        Column("end_line", "end"),
        Column("part"),
        Column("number", "no."),
        Column("title"),
        Column("flags"),
        Column("stated_version", "stated"),
        Column("installed_version", "installed"),
        Column("version_status", "version"),
    )
    sort_fields: ClassVar = ("line",)


def overview_entries(
    sections: list[OverviewSection], distribution: str, installed: str | None
) -> list[OverviewEntry]:
    """Item rows; the version fields are filled on part rows only."""
    entries = []
    for section in sections:
        entry = OverviewEntry(
            role=section.role,
            part=section.part,
            level=section.level,
            line=section.line,
            end_line=section.end_line,
            number=section.number,
            title=section.title,
            flags=list(section.flags),
        )
        if section.role == "part":
            stated = section.stated
            entry = entry.model_copy(
                update={
                    "distribution": distribution,
                    "installed_version": installed,
                    "stated_version": stated.version if stated else None,
                    "stated_subject": stated.subject if stated else None,
                    "stated_text": stated.text if stated else None,
                    "stated_line": stated.line if stated else None,
                    "version_status": (
                        compare_versions(stated.version, installed)
                        if stated and installed
                        else None
                    ),
                }
            )
        entries.append(entry)
    return entries


def installed_version(
    installation: Installation, distribution: str
) -> tuple[str | None, list[str]]:
    lookup = installation.lookup(distribution)
    if not lookup.matches:
        close = ", ".join(lookup.close_matches)
        return None, [
            f"{distribution}: no installed distribution in the target environment"
            + (f"; close matches: {close} (pass --distribution)" if close else "")
        ]
    versions = sorted({match.version for match in lookup.matches})
    notes = (
        [
            f"{distribution}: several installed versions ({', '.join(versions)}); compared with the first"
        ]
        if len(versions) > 1
        else []
    )
    return versions[0], notes


def overview(
    ctx: typer.Context,
    file: Annotated[
        Path,
        typer.Argument(exists=True, dir_okay=False, help="A library overview (Markdown)."),
    ],
    distribution: Annotated[
        str | None,
        typer.Option(
            "--distribution",
            help="The distribution the overview describes (default: the file's stem).",
        ),
    ] = None,
    json: JsonOpt = False,
    limit: LimitOpt = DEFAULT_LIMIT,
    offset: OffsetOpt = 0,
    strict: StrictOpt = False,
) -> None:
    """Section map of an overview and its stated version against the installed one."""
    state = library_state(ctx)
    target = state.target
    try:
        text = file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ToolFailure(
            "unreadable_overview",
            f"{target.display(file)} could not be read: {type(error).__name__}: {error}",
            "Pass a UTF-8 Markdown file.",
        ) from error
    name = normalize_name(distribution or file.stem)
    installed, notes = installed_version(state.installation, name)
    sections = section_map(text)
    entries = overview_entries(sections, name, installed)
    unavailable = (
        [UnavailableMetadata(subject=name, field="installed distribution")]
        if installed is None
        else []
    )
    main = next((entry for entry in entries if entry.role == "part"), None)
    if main is None:
        notes.append(f"{target.display(file)} has no level-one heading: no parts")
    elif main.stated_version is None:
        notes.append("the main part states no target version")
    emit(
        library_envelope(
            ctx,
            OverviewEntry,
            entries,
            limit=limit,
            offset=offset,
            authorities={"markdown-it-py": markdown_it_version},
            scanned=1,
            unavailable_metadata=unavailable,
            notes=[f"overview {target.display(file)}", *notes],
        ),
        json=json,
        strict=strict,
    )


def register(group: typer.Typer) -> None:
    group.command("overview")(overview)
