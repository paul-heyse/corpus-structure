"""Owned semantic set kernels and the typed operation views they consume.

These projections use occurrence/fact identifiers supplied by the bound operation.
They are independent of the retired pool's storage or reference-class vocabulary.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

SAME_SLOT, ALTERNATIVE_OF = "same_slot", "alternative_of"


def projected_attributes():
    from corpus_structure.model.compiled import running_model

    owner = running_model().view("rule-view.yaml").get_class("Entity")
    if owner is None or owner.attributes is None:
        raise ValueError("rule-view model lacks Entity")
    return tuple(name for name in owner.attributes if name not in {"identity", "index_symbols"})


type Side = Literal["subject", "object"]


@dataclass(frozen=True)
class ViewSpec:
    name: str
    applies_to: frozenset[str]
    source: str
    match_source: Side
    match_claim: Side
    head: Side
    attr: str
    slot: str | None = None

    def __post_init__(self) -> None:
        if not self.name or self.name in {SAME_SLOT, ALTERNATIVE_OF}:
            raise ValueError("declared view shadows a generic fact or has no name")
        if (
            self.match_source not in {"subject", "object"}
            or self.match_claim not in {"subject", "object"}
            or self.head not in {"subject", "object"}
        ):
            raise ValueError("view sides must be subject or object")
        if not (
            (self.attr in projected_attributes() and self.slot is None)
            or (self.attr == "identity" and self.slot)
        ):
            raise ValueError("unsupported view projection")

    @classmethod
    def from_declaration(
        cls, name: str, declaration: Mapping[str, Any], applies_to: Iterable[str]
    ) -> ViewSpec:
        head, _, rest = str(declaration["project"]).partition(".")
        attr, _, slot = rest.partition(".")
        if head not in ("subject", "object") or not (
            (attr in projected_attributes() and not slot) or (attr == "identity" and slot)
        ):
            raise ValueError(f"view {name}: cannot project {declaration['project']!r}")
        selected_head: Side = "subject" if head == "subject" else "object"
        match = declaration["match"]
        return cls(
            name,
            frozenset(applies_to),
            str(declaration["source"]),
            match["source"],
            match["claim"],
            selected_head,
            attr,
            slot or None,
        )


@dataclass(frozen=True, slots=True)
class ViewClaim:
    claim: str
    predicate: str
    subject: str
    object: str | None
    statement: str | None


@dataclass(frozen=True, slots=True)
class ViewEntity:
    entity: str
    key: str | None
    class_id: str
    label: str
    symbol: str | None


@dataclass(frozen=True, slots=True)
class ViewIdentity:
    entity: str
    slot: str
    value: str


@dataclass(frozen=True, slots=True)
class ViewAlternative:
    group: str
    claim: str


@dataclass(frozen=True, slots=True)
class ViewFacts:
    claim: str
    view: str
    facts: tuple[str, ...]


def checked_view_specs(
    specs: Iterable[ViewSpec], property_ids: Iterable[str]
) -> tuple[ViewSpec, ...]:
    """Validate actual declared property references without a transport projection."""
    specs = tuple(specs)
    names = [spec.name for spec in specs]
    if len(set(names)) != len(names) or {SAME_SLOT, ALTERNATIVE_OF} & set(names):
        raise ValueError("view names repeat or shadow a generic fact")
    declared = set(property_ids)
    for spec in specs:
        if spec.source not in declared or not spec.applies_to <= declared:
            raise ValueError("view uses a property outside this release")
    return specs


_ENTITY_FIELDS = {
    "id": "entity",
    "types": "class_id",
    "key": "key",
    "label": "label",
    "symbol": "symbol",
}


def operation_views(
    claims: Sequence[ViewClaim],
    entities: Sequence[ViewEntity],
    identity: Sequence[ViewIdentity],
    alternatives: Sequence[ViewAlternative],
    specs: Sequence[ViewSpec],
) -> tuple[ViewFacts, ...]:
    """Realize bounded occurrence views using indexes over their typed domain rows."""
    unsupported = set(projected_attributes()) - _ENTITY_FIELDS.keys()
    if unsupported:
        raise ValueError(
            "rule-view Entity differs from its typed working shape: "
            + ", ".join(sorted(unsupported))
        )
    by_predicate: dict[str, list[ViewClaim]] = defaultdict(list)
    slots: dict[tuple[str, str, str | None], set[str]] = defaultdict(set)
    claim_ids = {claim.claim for claim in claims}
    facts: dict[tuple[str, str], set[str]] = {}
    for claim in claims:
        by_predicate[claim.predicate].append(claim)
        slots[claim.predicate, claim.subject, claim.statement].add(claim.claim)
        facts.setdefault((claim.claim, SAME_SLOT), set())
        facts.setdefault((claim.claim, ALTERNATIVE_OF), set())
    for claim in claims:
        facts[claim.claim, SAME_SLOT].update(
            slots[claim.predicate, claim.subject, claim.statement] - {claim.claim}
        )
    groups: dict[str, set[str]] = defaultdict(set)
    for member in alternatives:
        groups[member.group].add(member.claim)
    for members in groups.values():
        present = members & claim_ids
        for claim in present:
            facts[claim, ALTERNATIVE_OF].update(present - {claim})
    by_entity: dict[str, list[ViewEntity]] = defaultdict(list)
    for entity in entities:
        by_entity[entity.entity].append(entity)
    identities: dict[tuple[str, str], set[str]] = defaultdict(set)
    for item in identity:
        identities[item.entity, item.slot].add(item.value)
    for spec in specs:
        projected: dict[str, set[str]] = defaultdict(set)
        for source in by_predicate.get(spec.source, ()):
            match = getattr(source, spec.match_source)
            head = getattr(source, spec.head)
            # Joins never equate two absent endpoints.
            if match is None or head is None:
                continue
            for entity in by_entity.get(head, ()):
                if spec.attr == "identity":
                    assert spec.slot is not None  # Validated by ViewSpec.
                    projected[match].update(identities.get((entity.entity, spec.slot), ()))
                else:
                    value = getattr(entity, _ENTITY_FIELDS[spec.attr])
                    if value is not None:
                        projected[match].add(value)
        for predicate in spec.applies_to:
            for claim in by_predicate.get(predicate, ()):
                selected = facts.setdefault((claim.claim, spec.name), set())
                match = getattr(claim, spec.match_claim)
                if match is not None:
                    selected.update(projected.get(match, ()))
    return tuple(
        ViewFacts(claim, view, tuple(sorted(values)))
        for (claim, view), values in sorted(facts.items())
    )
