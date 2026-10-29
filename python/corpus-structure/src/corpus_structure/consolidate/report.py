"""The pass report (consolidation §3.7; DA-013, R07): what a pass dropped and counted, by code.

`PassReport.counts` holds one count per code: a `DropReason` member, a batch-check `IssueCode`, a
`FrameFailureReason` from `parse`, or a `PassOutcome` (modelled closed sets, `core/vocab.py`);
`drops` names the refs or keys each drop code dropped; `unresolved` counts external references by
`ReferenceRefusal`. Messages are projections of the codes; nothing counts by message text.
`rule_counts` (M19's views evaluated per rule) and `consumed` (the `propose` tasks whose
observations the pass read) are what orchestration's runner records (orchestration §3.8).

"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field

from corpus_structure.core.vocab import DropReason, PassOutcome

__all__ = ["DROPS", "PassOutcome", "PassReport", "Tally"]


DROPS = frozenset(
    {DropReason.ORPHANED_PREMISE, DropReason.MALFORMED_EVIDENCE, PassOutcome.UNREADABLE_PROPOSAL}
)


@dataclass
class Tally:
    """The report as a pass builds it."""

    counts: Counter[str] = field(default_factory=Counter)
    drops: dict[str, set[str]] = field(default_factory=dict)
    unresolved: Counter[str] = field(default_factory=Counter)  # refusal code -> references

    def count(self, code: str, n: int = 1) -> None:
        self.counts[code] += n

    def drop(self, code: str, ref: str) -> None:
        self.counts[code] += 1
        self.drops.setdefault(code, set()).add(ref)


@dataclass(frozen=True)
class PassReport:
    pass_: str
    counts: Mapping[str, int] = field(default_factory=dict)
    drops: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    statuses: Mapping[str, int] = field(default_factory=dict)
    groups: tuple[str, ...] = ()  # alternative group keys
    unresolved: Mapping[str, int] = field(default_factory=dict)  # external references by code
    rule_counts: Mapping[str, int] = field(default_factory=dict)
    consumed: tuple[int, ...] = ()  # propose tasks whose observations the pass read

    @classmethod
    def of(
        cls,
        pass_: str,
        tally: Tally,
        statuses: Mapping[str, int],
        groups: tuple[str, ...],
        rule_counts: Mapping[str, int],
        consumed: tuple[int, ...],
    ) -> PassReport:
        return cls(
            pass_,
            dict(sorted(tally.counts.items())),
            {code: tuple(sorted(refs)) for code, refs in sorted(tally.drops.items())},
            dict(sorted(statuses.items())),
            groups,
            dict(sorted(tally.unresolved.items())),
            dict(sorted(rule_counts.items())),
            consumed,
        )
