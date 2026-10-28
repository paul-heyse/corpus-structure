"""Resolving a citation frame on a rendition, and re-addressing a batch to a served packet.

D1 §10.3; foundations §3.5. Both run on I0's resolver (`LocatorIndex`). Neither matches
approximately: an entry whose locator does not select one sentence, or whose sentence's text
differs from the recorded text, is refused with the resolver's candidates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from corpus_structure.core.batch import AuthoredBatch, CitationFrame, cited_sentences
from corpus_structure.core.evidence import Segment, SegmentKind
from corpus_structure.core.locators import (
    Candidate,
    LocatorIndex,
    LocatorRefused,
    LocatorSyntaxError,
)


@dataclass(frozen=True)
class FrameFailure:
    sentence: str
    locator: str
    reason: str
    candidates: tuple[Candidate, ...] = ()


class FrameRefused(LookupError):
    """A frame (or a re-addressing) with entries that do not resolve, each with its reason."""

    def __init__(self, failures: tuple[FrameFailure, ...]) -> None:
        self.failures = failures
        lines = "".join(f"\n  {f.sentence}: {f.locator} ({f.reason})" for f in failures)
        super().__init__(f"{len(failures)} frame entr{'y' if len(failures) == 1 else 'ies'} "
                         f"refused:{lines}")  # fmt: skip


def resolve_frame(frame: CitationFrame, index: LocatorIndex) -> dict[str, Segment]:
    """For every entry, the one sentence segment its locator selects whose text equals the
    recorded text; otherwise `FrameRefused` listing every failing entry."""
    resolved: dict[str, Segment] = {}
    failures: list[FrameFailure] = []
    for sentence, entry in frame.root.items():
        try:
            segment = index.resolve(entry.locator)
        except LocatorRefused as refused:
            failures.append(
                FrameFailure(sentence, entry.locator, refused.reason, refused.candidates)
            )
            continue
        except (LocatorSyntaxError, ValueError) as error:
            failures.append(FrameFailure(sentence, entry.locator, str(error)))
            continue
        if segment.kind is not SegmentKind.SENTENCE:
            failures.append(
                FrameFailure(sentence, entry.locator, f"selects a {segment.kind}, not a sentence")
            )
        elif index.rendition.text(segment) != entry.text:
            failures.append(FrameFailure(sentence, entry.locator, "sentence text differs"))
        else:
            resolved[sentence] = segment
    if failures:
        raise FrameRefused(tuple(failures))
    return resolved


def readdress(batch: AuthoredBatch, frame: CitationFrame, served: CitationFrame) -> AuthoredBatch:
    """Rewrite the batch's sentence ids into the served packet's, matching locator and text.

    A cited id missing from the batch's own frame, or an entry the served frame lacks, is refused.
    """
    by_entry = {(e.locator, e.text): sentence for sentence, e in served.root.items()}
    mapping: dict[str, str] = {}
    failures: list[FrameFailure] = []
    for sentence in cited_sentences(batch):
        if sentence not in frame:
            failures.append(FrameFailure(sentence, "", "cited but not in the batch's frame"))
            continue
        entry = frame[sentence]
        target = by_entry.get((entry.locator, entry.text))
        if target is None:
            failures.append(FrameFailure(sentence, entry.locator, "not in the served packet"))
        else:
            mapping[sentence] = target
    if failures:
        raise FrameRefused(tuple(failures))
    return AuthoredBatch.model_validate(_rewrite(batch.model_dump(mode="json"), mapping))


def _rewrite(node: Any, mapping: dict[str, str]) -> Any:
    if isinstance(node, dict):
        out: dict[str, Any] = {}
        for key, item in node.items():
            if key == "sentence" and isinstance(item, str):
                out[key] = mapping[item]
            elif key == "anchor" and isinstance(item, list):
                out[key] = [mapping[s] for s in item]
            else:
                out[key] = _rewrite(item, mapping)
        return out
    if isinstance(node, list):
        return [_rewrite(item, mapping) for item in node]
    return node
