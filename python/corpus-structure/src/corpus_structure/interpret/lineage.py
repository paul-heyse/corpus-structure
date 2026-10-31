"""Provenance polynomials and their semiring evaluations (D5 §14.6).

Every accepted record carries a lineage polynomial in N[X] over provenance variables: one per
observation, decision outcome or rule application used. Joining inputs multiplies (`*`, the
semiring's ⊗); alternative derivations add (`+`, ⊕). One polynomial answers several questions by
evaluation in a different semiring:

- Boolean: does the record still hold when some inputs are withdrawn?
- counting: in how many ways is it derived?
- Viterbi `([0, 1], max, *)`: the probability of its best single derivation;
- why-provenance: the minimal sets of inputs that each suffice.

Probability is not a semiring evaluation, because derivations share variables. `probability`
computes it exactly by Shannon expansion when the variables are independent; correlated
variables belong in one factor model and are evaluated through its posterior instead. When only
the inputs' marginals are known, `frechet_and` and `frechet_or` give the sharp bounds.

Withdrawing an input (a retracted source, a superseded model output) is `restrict(x, False)`:
the polynomial becomes zero exactly when no derivation survives.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import reduce

Monomial = tuple[str, ...]  # sorted variable names, repeated by exponent


@dataclass(frozen=True, slots=True)
class Semiring[T]:
    name: str
    zero: T
    one: T
    plus: Callable[[T, T], T]
    times: Callable[[T, T], T]


BOOLEAN: Semiring[bool] = Semiring(
    "boolean", False, True, lambda a, b: a or b, lambda a, b: a and b
)
COUNTING: Semiring[int] = Semiring("counting", 0, 1, lambda a, b: a + b, lambda a, b: a * b)
VITERBI: Semiring[float] = Semiring("viterbi", 0.0, 1.0, max, lambda a, b: a * b)


def _why_plus(
    a: frozenset[frozenset[str]], b: frozenset[frozenset[str]]
) -> frozenset[frozenset[str]]:
    return _minimal(a | b)


def _why_times(
    a: frozenset[frozenset[str]], b: frozenset[frozenset[str]]
) -> frozenset[frozenset[str]]:
    return _minimal(frozenset(x | y for x in a for y in b))


def _minimal(sets: frozenset[frozenset[str]]) -> frozenset[frozenset[str]]:
    return frozenset(s for s in sets if not any(other < s for other in sets))


# Minimal witness sets (the absorptive form of why-provenance).
WHY: Semiring[frozenset[frozenset[str]]] = Semiring(
    "why", frozenset(), frozenset({frozenset()}), _why_plus, _why_times
)


def why_valuation(variables: Iterable[str]) -> dict[str, frozenset[frozenset[str]]]:
    return {x: frozenset({frozenset({x})}) for x in variables}


class Lineage:
    """A polynomial in N[X]: monomials with positive integer coefficients."""

    __slots__ = ("_terms",)

    def __init__(self, terms: Mapping[Monomial, int] | None = None) -> None:
        cleaned: dict[Monomial, int] = {}
        for monomial, coefficient in (terms or {}).items():
            if coefficient < 0:
                raise ValueError("lineage coefficients are natural numbers")
            if coefficient:
                key = tuple(sorted(monomial))
                cleaned[key] = cleaned.get(key, 0) + coefficient
        self._terms = cleaned

    @classmethod
    def var(cls, name: str) -> Lineage:
        return cls({(name,): 1})

    @classmethod
    def zero(cls) -> Lineage:
        return cls()

    @classmethod
    def one(cls) -> Lineage:
        return cls({(): 1})

    @property
    def terms(self) -> Mapping[Monomial, int]:
        return dict(self._terms)

    @property
    def variables(self) -> frozenset[str]:
        return frozenset(x for monomial in self._terms for x in monomial)

    def is_zero(self) -> bool:
        return not self._terms

    def __add__(self, other: Lineage) -> Lineage:
        merged = Counter(self._terms)
        merged.update(other._terms)
        return Lineage(merged)

    def __mul__(self, other: Lineage) -> Lineage:
        product: Counter[Monomial] = Counter()
        for m1, c1 in self._terms.items():
            for m2, c2 in other._terms.items():
                product[tuple(sorted(m1 + m2))] += c1 * c2
        return Lineage(product)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Lineage) and self._terms == other._terms

    def __hash__(self) -> int:
        return hash(frozenset(self._terms.items()))

    def __repr__(self) -> str:
        if not self._terms:
            return "Lineage(0)"
        parts = []
        for monomial, coefficient in sorted(self._terms.items()):
            body = "·".join(monomial) or "1"
            parts.append(body if coefficient == 1 else f"{coefficient}{body}")
        return f"Lineage({' + '.join(parts)})"

    def evaluate[T](self, semiring: Semiring[T], valuation: Mapping[str, T]) -> T:
        """The polynomial's value in `semiring` with each variable valued by `valuation`."""
        total = semiring.zero
        for monomial, coefficient in self._terms.items():
            term = reduce(semiring.times, (valuation[x] for x in monomial), semiring.one)
            for _ in range(coefficient):
                total = semiring.plus(total, term)
        return total

    def restrict(self, variable: str, value: bool) -> Lineage:
        """Set one variable to 1 (`True`) or 0 (`False`, the input withdrawn)."""
        terms: Counter[Monomial] = Counter()
        for monomial, coefficient in self._terms.items():
            if variable not in monomial:
                terms[monomial] += coefficient
            elif value:
                terms[tuple(x for x in monomial if x != variable)] += coefficient
        return Lineage(terms)

    def holds(self, present: Iterable[str]) -> bool:
        """Boolean evaluation: true when some derivation uses only `present` inputs."""
        keep = frozenset(present)
        return self.evaluate(BOOLEAN, {x: x in keep for x in self.variables})

    def probability(self, marginals: Mapping[str, float]) -> float:
        """`P(lineage holds)` for independent Boolean variables, exactly (Shannon expansion)."""
        memo: dict[frozenset[Monomial], float] = {}

        def expand(monomials: frozenset[Monomial]) -> float:
            if not monomials:
                return 0.0
            if () in monomials:
                return 1.0
            if monomials in memo:
                return memo[monomials]
            counts = Counter(x for m in monomials for x in set(m))
            pivot = max(sorted(counts), key=lambda x: counts[x])
            when_true = frozenset(tuple(x for x in m if x != pivot) for m in monomials)
            when_false = frozenset(m for m in monomials if pivot not in m)
            p = marginals[pivot]
            result = p * expand(when_true) + (1.0 - p) * expand(when_false)
            memo[monomials] = result
            return result

        # Boolean semantics: exponents and coefficients collapse.
        return expand(frozenset(tuple(sorted(set(m))) for m in self._terms))


def frechet_and(probabilities: Sequence[float]) -> tuple[float, float]:
    """Sharp bounds on `P(all hold)` given only the marginals."""
    if not probabilities:
        return (1.0, 1.0)
    lower = max(0.0, sum(probabilities) - (len(probabilities) - 1))
    return (lower, min(probabilities))


def frechet_or(probabilities: Sequence[float]) -> tuple[float, float]:
    """Sharp bounds on `P(at least one holds)` given only the marginals."""
    if not probabilities:
        return (0.0, 0.0)
    return (max(probabilities), min(1.0, sum(probabilities)))
