"""Pure invariant checks over assembled knowledge; semantic publication owns writes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from corpus_structure.consolidate.assemble import Inputs, Knowledge
from corpus_structure.core.vocab import Establishment, EvidenceRole


class InvariantViolation(AssertionError):
    """A row the checks should have dropped: a defect below them. The pass raises and rolls back."""

    def __init__(self, invariant: str, keys: Sequence[str]) -> None:
        self.invariant, self.keys = invariant, tuple(keys)
        super().__init__(f"{invariant}: {', '.join(self.keys)}")


def check_invariants(knowledge: Knowledge, inputs: Inputs) -> None:
    unprimary = [
        k
        for k, r in knowledge.claims.items()
        if r.claim.establishment is Establishment.STATED
        and not any(e["role"] == EvidenceRole.PRIMARY.value for e in r.evidence)
    ]
    if unprimary:
        raise InvariantViolation("INV-01", sorted(unprimary))
    dangling = []
    for k, r in knowledge.claims.items():
        c = r.claim
        refs = [
            c.subject,
            getattr(c.object, "ref", None),
            c.statement if isinstance(c.statement, str) else None,
            getattr(c.qualifiers.attribution, "ref", None),
        ]
        if any(ref is not None and ref not in knowledge.entities for ref in refs):
            dangling.append(k)
    if dangling:
        raise InvariantViolation("INV-02", sorted(dangling))
    outside = [
        k
        for k, r in knowledge.claims.items()
        for e in r.evidence
        if not 0
        <= e["start"]
        < e["end"]
        <= len(inputs.pages[e["rendition"]].content.canonical_text)
    ]
    if outside:
        raise InvariantViolation("INV-10", sorted(set(outside)))


def statuses_of(knowledge: Knowledge) -> Mapping[str, int]:
    out: dict[str, int] = {}
    for r in knowledge.claims.values():
        out[r.status] = out.get(r.status, 0) + 1
    return out
