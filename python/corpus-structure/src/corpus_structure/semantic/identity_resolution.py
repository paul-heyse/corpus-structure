"""Deterministic label partitions constrained by explicit identity exclusions."""
from __future__ import annotations


def constrained_label_groups(members, exclusions, anchors):
    """Partition one label candidate set without quadratic candidate-edge materialization.

    Anchors are immutable known-input identities. Distinct anchors never merge. All candidate
    order is canonical; an exclusion prohibits a union even through another member.
    """
    forbidden = {member: set() for member in members}
    for left, right in exclusions:
        if left in forbidden and right in forbidden:
            forbidden[left].add(right)
            forbidden[right].add(left)
    groups = []
    for member in sorted(members):
        for group in groups:
            if forbidden[member].isdisjoint(group) and not (
                member in anchors and any(other in anchors for other in group)
            ):
                group.add(member)
                break
        else:
            groups.append({member})
    return tuple(frozenset(group) for group in groups)
