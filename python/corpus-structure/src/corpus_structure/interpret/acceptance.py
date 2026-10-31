"""Acceptance by threshold and escalation by value of information (D5 §14.7).

A record is accepted when its posterior `p` reaches its type's threshold `tau = c / (c + v)`;
the expected utility of the decision is `max(0, p v - (1 - p) c)`, the better of accepting and
withholding. An extra observation `a` (a second parser, a CPU LLM call, a human check) with
outcomes `o` is worth

    EVI(a) = E_o[ max_d EU(d | e, o) ] - max_d EU(d | e)

and is requested only when `EVI(a) > lambda * cost(a)`, best ratio first. EVI is never negative,
and it is zero when no outcome could change the decision, which is why confident decisions and
hopeless ones both stay off the LLM queue.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from corpus_structure.interpret.records import RecordType


def accepts(p: float, record_type: RecordType) -> bool:
    return p >= record_type.threshold


def expected_utility(p: float, record_type: RecordType) -> float:
    """The expected utility of the better of accepting and withholding."""
    return max(0.0, p * record_type.value - (1.0 - p) * record_type.cost)


def realized_utility(accepted: bool, correct: bool, record_type: RecordType) -> float:
    if not accepted:
        return 0.0
    return record_type.value if correct else -record_type.cost


@dataclass(frozen=True, slots=True)
class Outcome:
    """One possible result of an observation: its probability and the posterior it leaves."""

    probability: float
    posterior: float


def evi(prior: float, outcomes: Sequence[Outcome], record_type: RecordType) -> float:
    """The expected value of information of an observation with these outcomes."""
    total = sum(o.probability for o in outcomes)
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"outcome probabilities sum to {total}, not 1")
    mean_posterior = sum(o.probability * o.posterior for o in outcomes)
    if abs(mean_posterior - prior) > 1e-6:
        raise ValueError("the outcomes' posteriors must average to the prior")
    after = sum(o.probability * expected_utility(o.posterior, record_type) for o in outcomes)
    return max(0.0, after - expected_utility(prior, record_type))


def binary_check_outcomes(prior: float, sensitivity: float, specificity: float) -> list[Outcome]:
    """The outcomes of a yes/no check with known sensitivity and specificity, by Bayes' rule."""
    yes = prior * sensitivity + (1.0 - prior) * (1.0 - specificity)
    outcomes = []
    if yes > 0:
        outcomes.append(Outcome(yes, prior * sensitivity / yes))
    if yes < 1:
        outcomes.append(Outcome(1.0 - yes, prior * (1.0 - sensitivity) / (1.0 - yes)))
    return outcomes


@dataclass(frozen=True, slots=True)
class Escalation:
    decision: str
    action: str
    evi: float
    cost: float

    @property
    def net(self) -> float:
        return self.evi - self.cost


def plan_escalations(
    candidates: Sequence[tuple[str, str, float, float]], cpu_price: float
) -> list[Escalation]:
    """The escalations worth making, best EVI per unit cost first.

    Each candidate is `(decision, action, evi, cpu_cost)`; `cpu_price` is lambda, the utility
    one unit of CPU is worth. At most one action is kept per decision.
    """
    worth = [
        Escalation(decision, action, value, cpu_price * cpu_cost)
        for decision, action, value, cpu_cost in candidates
        if value > cpu_price * cpu_cost
    ]
    worth.sort(key=lambda e: (-(e.evi / e.cost) if e.cost > 0 else float("-inf"), e.decision))
    chosen: dict[str, Escalation] = {}
    for escalation in worth:
        chosen.setdefault(escalation.decision, escalation)
    return list(chosen.values())
