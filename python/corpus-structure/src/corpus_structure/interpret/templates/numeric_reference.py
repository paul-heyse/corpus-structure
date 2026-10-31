"""Prototype 1: a numeric reference resolved jointly with value roles (D5 §14.10).

In "At suction pressures above 2 bar, it delivered 120 m³/h, exceeding the 100 m³/h rating …
centrifugal pumps may cavitate below this pressure", the reference `this pressure` could denote
any earlier quantity, or none of them. Read alone, proximity favours the nearest quantity (the
100 m³/h rating). Jointly, three kinds of evidence settle it:

- **units** (group `units`): each quantity's dimension from the unit parser. A referent must
  have the head noun's dimension, a hard constraint, so the flow rates are excluded;
- **proximity and syntax** (group `proximity`): LLRs over the antecedent candidates;
- **frames** (group `frames`): role cues for each quantity (`above` -> condition threshold,
  `delivered` -> measured, `rating` -> rated), and the slot the reference fills in its frame
  (`cavitate below X` expects a condition threshold). The slot couples the reference decision to
  the role decision of whichever quantity it picks: the cross-decision factor where the synergy
  between streams lives.

Decisions (each with `UNKNOWN`): `ref:<reference>` over the candidate quantities, and
`role:<quantity>` over the roles. Observations are read from the store by decision id:
`dim:<quantity>` (unit dimension), `ref:<reference>` (antecedent evidence), `role:<quantity>`
(role cues) and `slot:<reference>` (the expected role of the referent).

Each record's lineage is the product of the provenance variables of every observation that
reached its component, so withdrawing any of them invalidates the record until it is
re-derived.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import reduce

from corpus_structure.interpret.acceptance import accepts
from corpus_structure.interpret.calibration import CalibrationTable
from corpus_structure.interpret.decisions import UNKNOWN, Decision
from corpus_structure.interpret.factors import DEFAULT_BUDGET, FactorGraph, Posterior
from corpus_structure.interpret.lineage import Lineage
from corpus_structure.interpret.observations import Observation, ObservationStore
from corpus_structure.interpret.records import RecordRegistry
from corpus_structure.interpret.support import effective_count

ROLES = ("condition_threshold", "measured", "rated")
REFERENCE_RECORD = "numeric_reference"
ROLE_RECORD = "value_role"


@dataclass(frozen=True, slots=True)
class QuantityMention:
    id: str
    text: str
    sentence: int


@dataclass(frozen=True, slots=True)
class ReferenceMention:
    id: str
    text: str
    sentence: int
    head_dimension: str  # the dimension the head noun names ("pressure")


@dataclass(frozen=True, slots=True)
class Mechanisms:
    """Which parts of the joint model are on, for the gain decomposition (D5 §14.9)."""

    constraints: bool = True  # unit-dimension hard constraints
    coupling: bool = True  # the reference-role slot factor
    window: int = 1  # sentences before the reference searched for candidates


FULL = Mechanisms()


@dataclass(frozen=True, slots=True)
class InterpretedRecord:
    record_type: str
    decision: str
    option: str
    probability: float
    accepted: bool
    lineage: Lineage = field(compare=False)


@dataclass(frozen=True, slots=True)
class Interpretation:
    posterior: Posterior = field(compare=False)
    records: tuple[InterpretedRecord, ...]
    uncalibrated: tuple[str, ...]  # cache keys of observations without a calibrator

    def record(self, decision: str) -> InterpretedRecord:
        for record in self.records:
            if record.decision == decision:
                return record
        raise KeyError(decision)

    def accepted(self) -> dict[str, str]:
        return {r.decision: r.option for r in self.records if r.accepted}


def _provenance(observation: Observation) -> Lineage:
    variables = sorted(observation.tags) or [observation.cache_key]
    return reduce(lambda a, b: a * b, (Lineage.var(v) for v in variables), Lineage.one())


class NumericReferenceTemplate:
    def __init__(
        self,
        quantities: Sequence[QuantityMention],
        references: Sequence[ReferenceMention],
        *,
        calibration: CalibrationTable,
        registry: RecordRegistry,
        correlated_rho: float = 1.0,
        budget: int = DEFAULT_BUDGET,
    ) -> None:
        self.quantities = tuple(quantities)
        self.references = tuple(references)
        self.calibration = calibration
        self.registry = registry
        self.correlated_rho = correlated_rho
        self.budget = budget

    def decisions(self, mechanisms: Mechanisms = FULL) -> list[Decision]:
        out = [Decision.with_unknown(f"role:{q.id}", ROLE_RECORD, ROLES) for q in self.quantities]
        for r in self.references:
            out.append(
                Decision.with_unknown(
                    f"ref:{r.id}", REFERENCE_RECORD, self._candidates(r, mechanisms)
                )
            )
        return out

    def _candidates(self, reference: ReferenceMention, mechanisms: Mechanisms) -> list[str]:
        low = reference.sentence - mechanisms.window
        return [q.id for q in self.quantities if low <= q.sentence <= reference.sentence]

    def _evidence(
        self, observations: Sequence[Observation], decision: Decision, uncalibrated: set[str]
    ) -> list[tuple[str, dict[str, float], Lineage]]:
        """Unary log-weights per correlation group, discounted to its effective count."""
        grouped: dict[str, list[Observation]] = defaultdict(list)
        for observation in observations:
            if observation.abstained:
                continue
            grouped[observation.correlation_group or observation.cache_key].append(observation)
        factors = []
        for name, members in sorted(grouped.items()):
            discount = effective_count(len(members), self.correlated_rho) / len(members)
            weights: dict[str, float] = defaultdict(float)
            lineage = Lineage.one()
            used = False
            for observation in members:
                contributed = False
                for option in decision.options:
                    llr = self.calibration.llr(observation, option)
                    if llr is None:
                        if observation.score_of(option) is not None:
                            uncalibrated.add(observation.cache_key)
                        continue
                    weights[option] += discount * llr
                    contributed = True
                if contributed:
                    lineage = lineage * _provenance(observation)
                    used = True
            if used:
                factors.append((name, dict(weights), lineage))
        return factors

    def _dimension(
        self, store: ObservationStore, quantity: QuantityMention
    ) -> tuple[str, Lineage] | None:
        observations = [o for o in store.for_decision(f"dim:{quantity.id}") if not o.abstained]
        if not observations:
            return None
        totals: dict[str, float] = defaultdict(float)
        lineage = Lineage.one()
        for observation in observations:
            for alternative in observation.alternatives:
                totals[alternative.option] += alternative.score
            lineage = lineage * _provenance(observation)
        best = max(sorted(totals), key=lambda option: totals[option])
        return best, lineage

    def interpret(self, store: ObservationStore, mechanisms: Mechanisms = FULL) -> Interpretation:
        graph = FactorGraph()
        decisions = {d.id: d for d in self.decisions(mechanisms)}
        for decision in decisions.values():
            graph.add_variable(decision.id, decision.options)
        # Lineage contributed by factors touching each variable; merged per component below.
        touches: dict[str, Lineage] = {name: Lineage.one() for name in decisions}
        uncalibrated: set[str] = set()

        for decision in decisions.values():
            for name, weights, lineage in self._evidence(
                store.for_decision(decision.id), decision, uncalibrated
            ):
                graph.add_unary(f"evidence:{decision.id}:{name}", decision.id, weights)
                touches[decision.id] = touches[decision.id] * lineage

        dimensions = {q.id: self._dimension(store, q) for q in self.quantities}
        for reference in self.references:
            ref = f"ref:{reference.id}"
            if mechanisms.constraints:
                excluded = {
                    q
                    for q in decisions[ref].candidates
                    if (found := dimensions[q]) is not None and found[0] != reference.head_dimension
                }
                if excluded:
                    graph.add_constraint(
                        f"dimension:{reference.id}",
                        (ref,),
                        lambda a, ex=excluded, v=ref: a[v] not in ex,
                    )
                    for q in decisions[ref].candidates:
                        if (found := dimensions[q]) is not None:
                            touches[ref] = touches[ref] * found[1]
            if mechanisms.coupling:
                self._couple(store, reference, decisions, graph, touches, uncalibrated)

        posterior = graph.infer(self.budget)
        component_lineage: dict[str, Lineage] = {}
        for names in graph.components():
            joined = reduce(lambda a, b: a * b, (touches[n] for n in names), Lineage.one())
            for n in names:
                component_lineage[n] = joined

        records = []
        for decision in decisions.values():
            marginal = posterior.marginal(decision.id)
            option = max(decision.options, key=lambda o: (marginal[o], o != UNKNOWN))
            record_type = self.registry[decision.decision_type]
            accepted = option != UNKNOWN and accepts(marginal[option], record_type)
            records.append(
                InterpretedRecord(
                    decision.decision_type,
                    decision.id,
                    option,
                    marginal[option],
                    accepted,
                    component_lineage[decision.id],
                )
            )
        return Interpretation(posterior, tuple(records), tuple(sorted(uncalibrated)))

    def _couple(
        self,
        store: ObservationStore,
        reference: ReferenceMention,
        decisions: Mapping[str, Decision],
        graph: FactorGraph,
        touches: dict[str, Lineage],
        uncalibrated: set[str],
    ) -> None:
        """Slot factors: picking quantity q rewards q's role matching the expected role."""
        ref = f"ref:{reference.id}"
        slot = Decision.with_unknown(f"slot:{reference.id}", "frame_slot", ROLES)
        expected = self._evidence(store.for_decision(slot.id), slot, uncalibrated)
        for name, weights, lineage in expected:
            for q in decisions[ref].candidates:
                role = f"role:{q}"
                graph.add_function(
                    f"slot:{reference.id}:{name}:{q}",
                    (ref, role),
                    lambda a, q=q, role=role, w=weights: (
                        w.get(a[role], 0.0) if a[ref] == q else 0.0
                    ),
                )
                touches[role] = touches[role] * lineage
            touches[ref] = touches[ref] * lineage
