"""Resolving a citation frame on a rendition, and re-addressing a batch to a served packet.

D1 §10.3; foundations §3.5. Both run on I0's resolver (`LocatorIndex`). Neither matches
approximately: an entry whose locator does not select one sentence, or whose sentence's text
differs from the recorded text, is refused with the resolver's candidates. Every failure carries a
`FrameFailureReason` code; its message is a projection of the code and the failure's fields.
"""

from __future__ import annotations

from dataclasses import dataclass

from corpus_structure.core.batch import (
    AuthoredBatch,
    CitationFrame,
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
from corpus_structure.core.vocab import FrameFailureReason

_MESSAGES: dict[FrameFailureReason, str] = {
    FrameFailureReason.LOCATOR_SYNTAX: "the locator is malformed",
    FrameFailureReason.OTHER_PAGE: "the locator names another page",
    FrameFailureReason.LOCATOR_REFUSED: "the locator is refused",
    FrameFailureReason.NOT_A_SENTENCE: "the locator selects a segment that is not a sentence",
    FrameFailureReason.TEXT_DIFFERS: "the sentence's text differs from the recorded text",
    FrameFailureReason.NOT_IN_FRAME: "cited but not in the batch's frame",
    FrameFailureReason.NOT_IN_PACKET: "not in the served packet",
}


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
        text = _MESSAGES[self.code]
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
    if segment.kind is not SegmentKind.SENTENCE:
        return FrameFailure(sentence, locator, FrameFailureReason.NOT_A_SENTENCE,
                            selected=segment.kind)  # fmt: skip
    if index.rendition.text(segment) != text:
        return FrameFailure(sentence, locator, FrameFailureReason.TEXT_DIFFERS)
    return segment


def resolve_frame(frame: CitationFrame, index: LocatorIndex) -> dict[str, Segment]:
    """For every entry, the one sentence segment its locator selects whose text equals the
    recorded text; otherwise `FrameRefused` listing every failing entry."""
    resolved: dict[str, Segment] = {}
    failures: list[FrameFailure] = []
    for sentence, entry in frame.root.items():
        outcome = _resolve_entry(sentence, entry.locator, entry.text, index)
        if isinstance(outcome, FrameFailure):
            failures.append(outcome)
        else:
            resolved[sentence] = outcome
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
