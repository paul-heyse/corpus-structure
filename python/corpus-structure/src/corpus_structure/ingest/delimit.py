r"""Math delimiting (D1 §3.1; D4 M01 "Math delimiting"; ingest and math §3.3 step 5).

One `regex` pattern is generated from a profile's `math` declarations, with `(?V1)` explicit and
the declared values held in named lists (`\L<opens>`, `\L<closes>`, `\L<delims>`, `\L<envs>`,
`\L<plain>`), so nothing is escaped by hand and, of overlapping items, the longer matches:

- an escaped backslash `\\` is skipped by `(*SKIP)(*F)`, as is the escaped form (`\$`) of every
  delimiter that does not start with a backslash;
- a bare display environment runs from `\begin{env}` to its `\end{env}`, or to the block's end;
- a delimited span's body is possessive and stops at the next declared delimiter, so an unclosed
  span ends there and the scan resynchronizes; a closer outside any span is a stray closer.

The pattern checks no brace or environment balance: segment status comes from delimiting alone
(`DelimitingStatus`), and what a span means is the math grammar's business (M11). Each block is
scanned with a time bound; a block that exceeds it is `partial` with reason
`delimiter scan timeout`.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from typing import Any

import regex

from corpus_structure.core.vocab import DelimitingStatus
from corpus_structure.ingest.profile import MathSpec

SCAN_TIMEOUT = 2.0  # seconds per block; Siegrist's blocks scan in microseconds
TIMEOUT_REASON = "delimiter scan timeout"


@dataclass(frozen=True, slots=True)
class MathSpan:
    """A delimited span of a block's text, `[start, end)`."""

    start: int
    end: int
    open: str
    close: str | None
    display: bool
    status: DelimitingStatus
    reason: str | None


@dataclass(frozen=True, slots=True)
class Stray:
    """A closer outside any span, at `position` in the block's text."""

    position: int
    delimiter: str


@dataclass(frozen=True, slots=True)
class Scan:
    spans: tuple[MathSpan, ...]
    strays: tuple[Stray, ...]
    timed_out: bool = False


@functools.cache
def pattern(spec: MathSpec) -> regex.Pattern[str]:
    """The delimiter pattern of a profile's math declarations (cached per declaration)."""
    pairs = spec.pairs
    opens, closes = sorted(pairs), sorted(set(pairs.values()))
    delims = sorted(set(opens) | set(closes))
    plain = sorted(d for d in delims if not d.startswith("\\"))
    lists: dict[str, list[str]] = {"opens": opens, "closes": closes, "delims": delims}
    branches = [r"\\\\ (*SKIP)(*F)"]
    escaped = ""
    if plain:
        lists["plain"] = plain
        branches.append(r"\\ \L<plain> (*SKIP)(*F)")
        escaped = r"\\ \L<plain> | "
    if spec.display_environments:
        lists["envs"] = list(spec.display_environments)
        branches.append(
            r"(?P<env>\\begin\{(?P<name>\L<envs>)\}) .*? (?P<envend>\\end\{(?P=name)\} | \Z)"
        )
    branches.append(
        r"(?P<open>\L<opens>) (?P<body>(?: \\\\ | " + escaped + r"(?!\L<delims>) . )*+)"
        r" (?P<close>\L<closes>)?"
    )
    branches.append(r"(?P<stray>\L<closes>)")
    named_lists: dict[str, Any] = dict(lists)
    flags = regex.VERBOSE | regex.DOTALL
    return regex.compile("(?V1)" + " | ".join(branches), flags, **named_lists)


def scan(text: str, spec: MathSpec, timeout: float = SCAN_TIMEOUT) -> Scan:
    """Delimit the math of one block's text; never rewrites it."""
    pairs = spec.pairs
    inline_open = spec.inline[0] if spec.inline is not None else None
    spans: list[MathSpan] = []
    strays: list[Stray] = []
    try:
        for m in pattern(spec).finditer(text, timeout=timeout):
            if m.group("stray"):
                strays.append(Stray(m.start(), m.group("stray")))
            elif m.groupdict().get("env"):
                closed = bool(m.group("envend"))
                spans.append(
                    MathSpan(
                        m.start(),
                        m.end(),
                        m.group("env"),
                        m.group("envend") if closed else None,
                        True,
                        DelimitingStatus.OK if closed else DelimitingStatus.PARTIAL,
                        None if closed else f"unclosed {m.group('env')}",
                    )
                )
            else:
                opener, closer = m.group("open"), m.group("close")
                if closer is None:
                    at_end = m.end() == len(text)
                    reason = (
                        "unclosed at block end"
                        if at_end
                        else f"unclosed {opener} before next opener"
                    )
                elif pairs[opener] != closer:
                    reason = f"{opener} closed by {closer}"
                else:
                    reason = None
                status = DelimitingStatus.OK if reason is None else DelimitingStatus.PARTIAL
                spans.append(
                    MathSpan(
                        m.start(), m.end(), opener, closer, opener != inline_open, status, reason
                    )
                )
    except TimeoutError:
        return Scan((), (), timed_out=True)
    return Scan(tuple(spans), tuple(strays))
