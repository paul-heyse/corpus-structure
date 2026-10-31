"""Log-linear factor models with exact inference inside a budget (D5 §14.5).

The joint model over a template's decisions `z` is

    log P(z | e, O) = sum_a w_a f_a(z, e) + sum_b u_b g_b(z, O) - log Z

Evidence factors `f_a` carry calibrated LLRs; constraint and compatibility factors `g_b` come
from the template and the ontology, with hard constraints at `-inf`. Synergy between streams
lives only in factors whose scope spans two or more decisions: with unary factors alone the
joint is a product of independent per-decision posteriors.

Templates are local (one passage, one table, one frame), so inference is exact: the graph is
split into connected components and each component's joint is enumerated. A component whose
joint has more than `budget` states is refused with `FactorBudgetExceeded`, never approximated
silently; the template has to prune candidates (conformal sizing) or split the decision.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np

DEFAULT_BUDGET = 1 << 16


class FactorBudgetExceeded(ValueError):
    """A component's joint state space is larger than the inference budget."""


class Infeasible(ValueError):
    """Hard constraints exclude every joint assignment of a component."""


@dataclass(frozen=True, slots=True)
class Variable:
    name: str
    domain: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.domain or len(set(self.domain)) != len(self.domain):
            raise ValueError(f"{self.name}: the domain must be non-empty and distinct")

    def index(self, option: str) -> int:
        try:
            return self.domain.index(option)
        except ValueError:
            raise KeyError(f"{option!r} is not an option of {self.name}") from None


@dataclass(frozen=True, slots=True)
class Factor:
    """A log-space table over `scope`, with axes in scope order."""

    name: str
    scope: tuple[str, ...]
    table: np.ndarray = field(compare=False)

    def __post_init__(self) -> None:
        if len(set(self.scope)) != len(self.scope):
            raise ValueError(f"factor {self.name}: a variable repeats in the scope")
        if self.table.ndim != len(self.scope):
            raise ValueError(f"factor {self.name}: the table rank differs from the scope")
        if np.isnan(self.table).any() or np.isposinf(self.table).any():
            raise ValueError(f"factor {self.name}: log values must be finite or -inf")


def _logsumexp(values: np.ndarray, axis: int | tuple[int, ...] | None = None) -> np.ndarray:
    peak = np.max(values, axis=axis, keepdims=True)
    safe = np.where(np.isfinite(peak), peak, 0.0)
    with np.errstate(divide="ignore"):
        total = np.log(np.sum(np.exp(values - safe), axis=axis, keepdims=True)) + safe
    return np.squeeze(total, axis=axis) if axis is not None else total.reshape(())


class FactorGraph:
    """Variables and factors of one template instance."""

    def __init__(self) -> None:
        self._variables: dict[str, Variable] = {}
        self._factors: list[Factor] = []

    @property
    def variables(self) -> Mapping[str, Variable]:
        return self._variables

    @property
    def factors(self) -> tuple[Factor, ...]:
        return tuple(self._factors)

    def add_variable(self, name: str, domain: Sequence[str]) -> Variable:
        if name in self._variables:
            raise ValueError(f"variable {name!r} already exists")
        variable = Variable(name, tuple(domain))
        self._variables[name] = variable
        return variable

    def _shape(self, scope: Sequence[str]) -> tuple[int, ...]:
        missing = [name for name in scope if name not in self._variables]
        if missing:
            raise KeyError(f"unknown variables {missing}")
        return tuple(len(self._variables[name].domain) for name in scope)

    def add_factor(self, factor: Factor) -> Factor:
        if factor.table.shape != self._shape(factor.scope):
            raise ValueError(f"factor {factor.name}: the table shape differs from the domains")
        self._factors.append(factor)
        return factor

    def add_unary(self, name: str, variable: str, log_weights: Mapping[str, float]) -> Factor:
        """A unary factor; options not named get 0 (no evidence either way)."""
        domain = self._variables[variable].domain
        table = np.zeros(len(domain))
        for option, weight in log_weights.items():
            table[self._variables[variable].index(option)] = weight
        return self.add_factor(Factor(name, (variable,), table))

    def add_function(
        self, name: str, scope: Sequence[str], fn: Callable[[Mapping[str, str]], float]
    ) -> Factor:
        """A factor whose log value for each joint assignment of `scope` is `fn(assignment)`."""
        scope = tuple(scope)
        shape = self._shape(scope)
        table = np.empty(shape)
        domains = [self._variables[v].domain for v in scope]
        for index in itertools.product(*(range(n) for n in shape)):
            assignment = {
                v: domains[i][k] for i, (v, k) in enumerate(zip(scope, index, strict=True))
            }
            table[index] = fn(assignment)
        return self.add_factor(Factor(name, scope, table))

    def add_constraint(
        self, name: str, scope: Sequence[str], allowed: Callable[[Mapping[str, str]], bool]
    ) -> Factor:
        """A hard constraint: assignments for which `allowed` is false get `-inf`."""
        return self.add_function(name, scope, lambda a: 0.0 if allowed(a) else -math.inf)

    def components(self) -> list[tuple[str, ...]]:
        """Connected components of the variable graph, each in declaration order."""
        parent = {name: name for name in self._variables}

        def find(name: str) -> str:
            while parent[name] != name:
                parent[name] = parent[parent[name]]
                name = parent[name]
            return name

        for factor in self._factors:
            for other in factor.scope[1:]:
                parent[find(other)] = find(factor.scope[0])
        grouped: dict[str, list[str]] = {}
        for name in self._variables:
            grouped.setdefault(find(name), []).append(name)
        return [tuple(names) for names in grouped.values()]

    def infer(self, budget: int = DEFAULT_BUDGET) -> Posterior:
        """Exact posterior, component by component."""
        components: list[_Component] = []
        log_z = 0.0
        for names in self.components():
            shape = self._shape(names)
            size = math.prod(shape)
            if size > budget:
                raise FactorBudgetExceeded(
                    f"component {names} has {size} joint states; the budget is {budget}"
                )
            position = {name: i for i, name in enumerate(names)}
            joint = np.zeros(shape)
            for factor in self._factors:
                if factor.scope[0] not in position:
                    continue
                axes = [position[name] for name in factor.scope]
                order = np.argsort(axes)
                table = np.transpose(factor.table, order)
                expanded = [1] * len(names)
                for axis in sorted(axes):
                    expanded[axis] = shape[axis]
                joint = joint + table.reshape(expanded)
            component_z = float(_logsumexp(joint))
            if not math.isfinite(component_z):
                raise Infeasible(f"no assignment of {names} satisfies the hard constraints")
            log_z += component_z
            components.append(_Component(names, joint - component_z))
        return Posterior(dict(self._variables), components, log_z)


@dataclass(frozen=True, slots=True)
class _Component:
    names: tuple[str, ...]
    log_joint: np.ndarray  # normalized


class Posterior:
    """The exact posterior of a factor graph."""

    def __init__(
        self, variables: Mapping[str, Variable], components: Iterable[_Component], log_z: float
    ) -> None:
        self._variables = dict(variables)
        self._components = list(components)
        self._where = {name: c for c in self._components for name in c.names}
        self.log_partition = log_z

    def marginal(self, variable: str) -> dict[str, float]:
        component = self._where[variable]
        axis = component.names.index(variable)
        others = tuple(i for i in range(len(component.names)) if i != axis)
        log_marginal = (
            _logsumexp(component.log_joint, axis=others) if others else component.log_joint
        )
        probabilities = np.exp(log_marginal)
        return dict(zip(self._variables[variable].domain, probabilities.tolist(), strict=True))

    def map_assignment(self) -> dict[str, str]:
        """The jointly most probable assignment (not the per-variable argmax)."""
        assignment: dict[str, str] = {}
        for component in self._components:
            index = np.unravel_index(int(np.argmax(component.log_joint)), component.log_joint.shape)
            for name, k in zip(component.names, index, strict=True):
                assignment[name] = self._variables[name].domain[int(k)]
        return assignment

    def probability(self, event: Callable[[Mapping[str, str]], bool], over: Sequence[str]) -> float:
        """`P(event)`, the event reading only the variables in `over`."""
        over = tuple(dict.fromkeys(over))
        pieces: list[tuple[tuple[str, ...], np.ndarray]] = []
        for component in self._components:
            kept = tuple(name for name in component.names if name in over)
            if not kept:
                continue
            drop = tuple(i for i, name in enumerate(component.names) if name not in kept)
            table = _logsumexp(component.log_joint, axis=drop) if drop else component.log_joint
            pieces.append((kept, np.exp(table)))
        names = tuple(name for kept, _ in pieces for name in kept)
        if set(names) != set(over):
            raise KeyError(f"unknown variables {sorted(set(over) - set(names))}")
        joint = np.ones(())
        for _, table in pieces:
            joint = np.multiply.outer(joint, table)
        total = 0.0
        domains = [self._variables[name].domain for name in names]
        for index in itertools.product(*(range(len(d)) for d in domains)):
            assignment = {
                n: domains[i][k] for i, (n, k) in enumerate(zip(names, index, strict=True))
            }
            if event(assignment):
                total += float(joint[index])
        return total
