"""Resolving a citation frame on a rendition, and re-addressing a batch to a served packet.

D1 §10.3; foundations §3.5. Both run on I0's resolver (`LocatorIndex`). Neither matches
approximately: an entry whose locator does not select one sentence, or whose sentence's text
differs from the recorded text, is refused with the resolver's candidates. Every failure carries a
`FrameFailureReason` code; its message is a projection of the code and the failure's fields.

`resolve_entry` gives one entry's outcome without raising: `resolved` as recorded; `relocated` when
it did not, but exactly one sentence of the rendition carries the recorded text (the outcome names
that sentence's locator on this rendition; a consumer that keeps it writes a new frame version,
never an edit); `unresolved` otherwise, each with its code and failure. `resolve_frame` accepts only
`resolved` entries and refuses the frame with every other entry's failure.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, assert_never

from corpus_structure.core.batch import (
    AuthoredBatch,
    CitationFrame,
    FrameEntry,
    cited_sentences,
    rewrite_citations,
)
from corpus_structure.core.evidence import Segment, SegmentKind
from corpus_structure.core.locators import (
    Candidate,
    LocatorIndex,
    LocatorRefused,
    LocatorSyntaxError,
    RefusalReason,
    parse,
)
from corpus_structure.core.vocab import CITABLE_SENTENCE, FrameFailureReason


def _message(code: FrameFailureReason) -> str:
    """Each code's message; exhaustive, so a new code is a type error, not a runtime KeyError."""
    match code:
        case FrameFailureReason.LOCATOR_SYNTAX:
            return "the locator is malformed"
        case FrameFailureReason.OTHER_PAGE:
            return "the locator names another page"
        case FrameFailureReason.LOCATOR_REFUSED:
            return "the locator is refused"
        case FrameFailureReason.NOT_A_SENTENCE:
            return "the locator selects a segment that is not a sentence"
        case FrameFailureReason.TEXT_DIFFERS:
            return "the sentence's text differs from the recorded text"
        case FrameFailureReason.NOT_IN_FRAME:
            return "cited but not in the batch's frame"
        case FrameFailureReason.NOT_IN_PACKET:
            return "not in the served packet"
        case _:
            assert_never(code)


@dataclass(frozen=True)
class FrameFailure:
    """One entry that did not resolve or re-address: its code, plus the typed detail the code
    has (the resolver's refusal and candidates, the syntax fault, the kind selected)."""

    sentence: str
    locator: str
    code: FrameFailureReason
    refusal: RefusalReason | None = None  # LOCATOR_REFUSED: the resolver's typed reason
    candidates: tuple[Candidate, ...] = ()
    position: int | None = None  # LOCATOR_SYNTAX: the fault's offset in the locator
    fault: str | None = None  # LOCATOR_SYNTAX: the parser's fault at `position`
    selected: SegmentKind | None = None  # NOT_A_SENTENCE: the kind the locator selects

    @property
    def message(self) -> str:
        text = _message(self.code)
        if self.code is FrameFailureReason.LOCATOR_REFUSED:
            text += f" ({self.refusal})"
        elif self.code is FrameFailureReason.LOCATOR_SYNTAX:
            text += f" ({self.fault} at position {self.position})"
        elif self.code is FrameFailureReason.NOT_A_SENTENCE:
            text += f" ({self.selected})"
        return text


class FrameRefused(LookupError):
    """A frame (or a re-addressing) with entries that do not resolve, each with its code."""

    def __init__(self, failures: tuple[FrameFailure, ...]) -> None:
        self.failures = failures
        lines = "".join(f"\n  {f.sentence}: {f.locator} ({f.message})" for f in failures)
        super().__init__(f"{len(failures)} frame entr{'y' if len(failures) == 1 else 'ies'} "
                         f"refused:{lines}")  # fmt: skip


def _resolve_entry(
    sentence: str, locator: str, text: str, index: LocatorIndex
) -> Segment | FrameFailure:
    try:
        parsed = parse(locator)
    except LocatorSyntaxError as error:
        return FrameFailure(sentence, locator, FrameFailureReason.LOCATOR_SYNTAX,
                            position=error.position, fault=error.reason)  # fmt: skip
    if parsed.page != index.page:
        return FrameFailure(sentence, locator, FrameFailureReason.OTHER_PAGE)
    try:
        segment = index.resolve(parsed)
    except LocatorRefused as refused:
        return FrameFailure(sentence, locator, FrameFailureReason.LOCATOR_REFUSED,
                            refusal=refused.reason, candidates=refused.candidates)  # fmt: skip
    if segment.kind not in CITABLE_SENTENCE:
        return FrameFailure(sentence, locator, FrameFailureReason.NOT_A_SENTENCE,
                            selected=segment.kind)  # fmt: skip
    if index.rendition.text(segment) != text:
        return FrameFailure(sentence, locator, FrameFailureReason.TEXT_DIFFERS)
    return segment


type FrameStatus = Literal["resolved", "relocated", "unresolved"]


@dataclass(frozen=True)
class FrameOutcome:
    """One entry's outcome: its status, the code (and the failure with its detail) when it did not
    resolve as recorded, the sentence segment when resolved or relocated, and the relocated
    sentence's generated locator on this rendition."""

    sentence: str
    status: FrameStatus
    code: FrameFailureReason | None = None
    segment: Segment | None = None
    locator: str | None = None
    failure: FrameFailure | None = None


def sentences_by_text(index: LocatorIndex) -> dict[str, list[Segment]]:
    """The rendition's citable sentences by their text, for relocation (compute it once and pass
    it to `resolve_entry` when resolving many entries)."""
    out: dict[str, list[Segment]] = {}
    for segment, _ in index:
        if segment.kind in CITABLE_SENTENCE:
            out.setdefault(index.rendition.text(segment), []).append(segment)
    return out


def resolve_entry(
    sentence: str,
    entry: FrameEntry,
    index: LocatorIndex,
    by_text: Mapping[str, list[Segment]] | None = None,
) -> FrameOutcome:
    """One frame entry's outcome on the rendition (module doc); never raises."""
    found = _resolve_entry(sentence, entry.locator, entry.text, index)
    if not isinstance(found, FrameFailure):
        return FrameOutcome(sentence, "resolved", None, found)
    same = (sentences_by_text(index) if by_text is None else by_text).get(entry.text, [])
    if len(same) == 1:
        relocated = str(index.generate(same[0]))
        return FrameOutcome(sentence, "relocated", found.code, same[0], relocated, found)
    return FrameOutcome(sentence, "unresolved", found.code, failure=found)


def resolve_frame(frame: CitationFrame, index: LocatorIndex) -> dict[str, Segment]:
    """For every entry, the one sentence segment its locator selects whose text equals the
    recorded text; otherwise `FrameRefused` listing every entry that did not resolve as recorded
    (a relocatable one included: resolution never matches approximately)."""
    resolved: dict[str, Segment] = {}
    failures: list[FrameFailure] = []
    for sentence, entry in frame.root.items():
        outcome = resolve_entry(sentence, entry, index, by_text={})
        if outcome.failure is not None:
            failures.append(outcome.failure)
        elif outcome.segment is not None:
            resolved[sentence] = outcome.segment
    if failures:
        raise FrameRefused(tuple(failures))
    return resolved


def readdress(batch: AuthoredBatch, frame: CitationFrame, served: CitationFrame) -> AuthoredBatch:
    """Rewrite the batch's sentence ids into the served packet's, matching locator and text.

    A cited id missing from the batch's own frame, or an entry the served frame lacks, is refused.
    Only citation positions (fields typed `SentenceId`) are rewritten.
    """
    by_entry = {(e.locator, e.text): sentence for sentence, e in served.root.items()}
    mapping: dict[str, str] = {}
    failures: list[FrameFailure] = []
    for sentence in cited_sentences(batch):
        if sentence not in frame:
            failures.append(FrameFailure(sentence, "", FrameFailureReason.NOT_IN_FRAME))
            continue
        entry = frame[sentence]
        target = by_entry.get((entry.locator, entry.text))
        if target is None:
            failures.append(FrameFailure(sentence, entry.locator, FrameFailureReason.NOT_IN_PACKET))
        else:
            mapping[sentence] = target
    if failures:
        raise FrameRefused(tuple(failures))
    return rewrite_citations(batch, mapping.__getitem__)
