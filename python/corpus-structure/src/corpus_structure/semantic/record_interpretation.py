"""Private, pure M1 candidate interpretation; no admission or publication authority.

Only the three selected record templates are supported. Callers supply already computed
log potentials and assignment-relative hard masks, including their evidence dependencies.
Enumeration is exact over the declared retained joint, subject to floating-point arithmetic.
The total-joint guard is deliberately conservative: component discovery is diagnostic and
does not authorize splitting, approximate fallback, or claims about ordinary component fit.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from threading import Event
from time import monotonic
from typing import Literal

import networkx as nx
import numpy as np
from scipy.special import logsumexp


class CandidateKind(StrEnum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    LOCAL_NEW = "local_new"


@dataclass(frozen=True)
class Candidate:
    key: str
    kind: CandidateKind = CandidateKind.RESOLVED
    reason: str | None = None


@dataclass(frozen=True)
class Decision:
    key: str
    candidates: tuple[Candidate, ...]


@dataclass(frozen=True)
class ValuePropertyReferentCondition:
    value: Decision
    property: Decision
    referent: Decision
    condition: Decision
    qualifiers: tuple[Decision, ...] = ()
    auxiliary: tuple[Decision, ...] = ()


@dataclass(frozen=True)
class MentionIdentityTypeRelation:
    mention_id: str
    identity: Decision
    type: Decision
    relation: Decision
    qualifiers: tuple[Decision, ...] = ()
    auxiliary: tuple[Decision, ...] = ()


@dataclass(frozen=True)
class TableHeaderRowCellUnitNote:
    table_id: str
    header: Decision
    row_identity: Decision
    cell_value: Decision
    unit: Decision
    note: Decision
    qualifiers: tuple[Decision, ...] = ()
    auxiliary: tuple[Decision, ...] = ()


type RecordTemplate = (
    ValuePropertyReferentCondition | MentionIdentityTypeRelation | TableHeaderRowCellUnitNote
)


class DependencyKind(StrEnum):
    OBSERVATION = "observation"
    COUNTEREVIDENCE = "counterevidence"
    REJECTED_ALTERNATIVE = "rejected_alternative"
    RETRIEVAL = "retrieval"
    CONTEXT = "context"
    SELECTION = "selection"
    MODEL = "model"
    ONTOLOGY = "ontology"
    POLICY = "policy"


@dataclass(frozen=True)
class Dependency:
    key: str
    kind: DependencyKind
    revision: str


@dataclass(frozen=True)
class CandidateSelection:
    """Declared candidate universe, including prior omissions of unknown probability mass."""

    scope_id: str
    dependency_ids: tuple[str, ...]
    retrieval_limit: int | None = None
    exclusions: tuple[str, ...] = ()
    truncations: tuple[str, ...] = ()


@dataclass(frozen=True)
class LogPotential:
    """Flat C-order table whose axes follow scope and each decision's candidate order."""

    key: str
    scope: tuple[str, ...]
    values: tuple[float, ...]
    dependency_ids: tuple[str, ...]


@dataclass(frozen=True)
class HardConstraint:
    """Precomputed feasibility under the meanings selected on all named axes."""

    key: str
    scope: tuple[str, ...]
    allowed: tuple[bool, ...]
    dependency_ids: tuple[str, ...]


@dataclass(frozen=True)
class DependenceScope:
    """Real evidence/selection dependence, distinct from shared release metadata."""

    scope: tuple[str, ...]
    dependency_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class Choice:
    decision: str
    candidate: str


@dataclass(frozen=True)
class RecordEvent:
    """Union of derivations of ONE qualified reading; overlapping assignments count once.

    Every derivation specifies all record roles and meaning-changing qualifiers. Auxiliary
    evidence decisions may be omitted or constrained differently by individual derivations.
    """

    key: str
    derivations: tuple[tuple[Choice, ...], ...]


@dataclass(frozen=True)
class SearchLimits:
    max_states: int = 65_536
    block_states: int = 1_024
    max_workspace_bytes: int = 64 * 1024 * 1024
    max_seconds: float = 10.0
    displayed_alternatives: int = 5


@dataclass(frozen=True)
class InterpretationRequest:
    template: RecordTemplate
    potentials: tuple[LogPotential, ...]
    constraints: tuple[HardConstraint, ...]
    events: tuple[RecordEvent, ...]
    dependencies: tuple[Dependency, ...]
    selection: CandidateSelection
    model_dependency_id: str
    ontology_dependency_id: str
    policy_dependency_id: str
    dependence_scopes: tuple[DependenceScope, ...] = ()
    limits: SearchLimits = SearchLimits()


class Outcome(StrEnum):
    COMPLETED = "completed"
    INVALID_INPUT = "invalid_input"
    INFEASIBLE = "infeasible"
    NUMERICAL_FAILURE = "numerical_failure"
    RESOURCE_LIMIT = "resource_limit"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class EventProbability:
    event: str
    probability: float


@dataclass(frozen=True)
class Marginal:
    decision: str
    candidate: str
    probability: float


@dataclass(frozen=True)
class CoherentAlternative:
    choices: tuple[Choice, ...]
    probability: float


@dataclass(frozen=True)
class SearchDiagnostics:
    retained_states: int
    examined_states: int
    positive_states: int
    components: tuple[tuple[str, ...], ...]
    workspace_bound_bytes: int
    elapsed_seconds: float
    limits: SearchLimits


@dataclass(frozen=True)
class InterpretationResult:
    outcome: Outcome
    detail: str
    search: SearchDiagnostics
    dependencies: tuple[Dependency, ...]
    selection: CandidateSelection
    event_probabilities: tuple[EventProbability, ...] = ()
    marginals: tuple[Marginal, ...] = ()
    alternatives: tuple[CoherentAlternative, ...] = ()
    log_partition: float | None = None
    exact_retained_support: bool = False
    probability_standing: Literal["provisional_candidate_relative"] = (
        "provisional_candidate_relative"
    )
    omitted_candidate_mass: Literal["unknown"] = "unknown"


class _Stop(Exception):
    def __init__(self, outcome: Outcome, detail: str) -> None:
        self.outcome = outcome
        self.detail = detail


def _roles(template: RecordTemplate) -> tuple[tuple[Decision, ...], Decision]:
    match template:
        case ValuePropertyReferentCondition():
            return (template.value, template.property, template.referent, template.condition), (
                template.referent
            )
        case MentionIdentityTypeRelation():
            if template.mention_id:
                return (template.identity, template.type, template.relation), template.identity
        case TableHeaderRowCellUnitNote():
            if template.table_id:
                return (
                    template.header,
                    template.row_identity,
                    template.cell_value,
                    template.unit,
                    template.note,
                ), template.row_identity
    raise _Stop(Outcome.INVALID_INPUT, "unsupported template or missing source context")


def interpret_records(
    request: InterpretationRequest, *, cancellation: Event | None = None
) -> InterpretationResult:
    """Evaluate a private retained model, without accepting records or changing any store.

    Limits cover this operation's numerical workspace (including converted factor tables),
    rather than caller-owned input objects or the whole Python process. MemoryError is also
    reported explicitly. Polling is cooperative between bounded numerical calls; this is not
    CPU admission/supervision or a hard process-memory/time fence.
    """

    started = monotonic()
    retained = examined = positive = workspace = 0
    components: tuple[tuple[str, ...], ...] = ()
    limits = request.limits
    duration = 0.0

    def poll() -> None:
        if cancellation is not None and cancellation.is_set():
            raise _Stop(Outcome.CANCELLED, "cancelled; no partial probabilities returned")
        if monotonic() - started >= duration:
            raise _Stop(Outcome.RESOURCE_LIMIT, "elapsed time limit")

    def result(outcome: Outcome, detail: str, **kwargs) -> InterpretationResult:
        if outcome is Outcome.COMPLETED:
            poll()
        return InterpretationResult(
            outcome=outcome,
            detail=detail,
            search=SearchDiagnostics(
                retained, examined, positive, components, workspace, monotonic() - started, limits
            ),
            dependencies=request.dependencies,
            selection=request.selection,
            **kwargs,
        )

    try:
        # Dataclass annotations are not a runtime boundary. Reject fractional, Boolean and
        # nonfinite counts before they reach comparisons, range(), slicing or allocation.
        for count, minimum in (
            (limits.max_states, 1),
            (limits.block_states, 1),
            (limits.max_workspace_bytes, 1),
            (limits.displayed_alternatives, 0),
        ):
            if type(count) is not int or count < minimum:
                raise _Stop(Outcome.INVALID_INPUT, "search counts/bytes must be exact integers")
        if type(limits.max_seconds) not in (int, float):
            raise _Stop(Outcome.INVALID_INPUT, "elapsed limit must be a finite real duration")
        try:
            duration = float(limits.max_seconds)
        except OverflowError:
            raise _Stop(
                Outcome.INVALID_INPUT, "elapsed limit is outside finite float range"
            ) from None
        if not math.isfinite(duration) or duration < 0:
            raise _Stop(Outcome.INVALID_INPUT, "elapsed limit must be finite and nonnegative")
        poll()
        roles, identity = _roles(request.template)
        required = (*roles, *request.template.qualifiers)
        decisions = (*required, *request.template.auxiliary)
        by_key = {decision.key: decision for decision in decisions}
        if len(by_key) != len(decisions) or not all(by_key):
            raise _Stop(Outcome.INVALID_INPUT, "decision keys must be nonempty and unique")
        shape = tuple(len(d.candidates) for d in decisions)
        retained = math.prod(shape)
        if retained > limits.max_states or retained > np.iinfo(np.intp).max:
            raise _Stop(Outcome.RESOURCE_LIMIT, "total retained joint exceeds state guard")
        indices: dict[str, dict[str, int]] = {}
        for decision in decisions:
            poll()
            positions = {candidate.key: i for i, candidate in enumerate(decision.candidates)}
            if not positions or len(positions) != len(decision.candidates) or not all(positions):
                raise _Stop(Outcome.INVALID_INPUT, "candidate keys must be nonempty and unique")
            if not any(c.kind is CandidateKind.UNRESOLVED for c in decision.candidates):
                raise _Stop(Outcome.INVALID_INPUT, "each decision needs an unresolved candidate")
            for candidate in decision.candidates:
                if not isinstance(candidate.kind, CandidateKind) or (
                    candidate.kind is CandidateKind.UNRESOLVED and not candidate.reason
                ):
                    raise _Stop(Outcome.INVALID_INPUT, "unresolved needs a reason; invalid kind")
            indices[decision.key] = positions
        if not any(c.kind is CandidateKind.LOCAL_NEW for c in identity.candidates):
            raise _Stop(Outcome.INVALID_INPUT, "identity needs a genuine local/new candidate")
        dependencies = {d.key: d for d in request.dependencies}
        if len(dependencies) != len(request.dependencies) or any(
            not d.key or not d.revision or not isinstance(d.kind, DependencyKind)
            for d in request.dependencies
        ):
            raise _Stop(Outcome.INVALID_INPUT, "invalid dependency identity or revision")

        def dependency_ids(keys: tuple[str, ...]) -> None:
            if not keys or any(key not in dependencies for key in keys):
                raise _Stop(Outcome.INVALID_INPUT, "missing declared computation dependency")

        for key, kind in (
            (request.model_dependency_id, DependencyKind.MODEL),
            (request.ontology_dependency_id, DependencyKind.ONTOLOGY),
            (request.policy_dependency_id, DependencyKind.POLICY),
        ):
            if key not in dependencies or dependencies[key].kind is not kind:
                raise _Stop(Outcome.INVALID_INPUT, f"missing {kind} input")
        selection = request.selection
        dependency_ids(selection.dependency_ids)
        if not selection.scope_id or (
            selection.retrieval_limit is not None
            and (type(selection.retrieval_limit) is not int or selection.retrieval_limit < 0)
        ):
            raise _Stop(Outcome.INVALID_INPUT, "invalid candidate selection scope/limit")

        graph = nx.Graph()
        graph.add_nodes_from(by_key)

        def scope_size(scope: tuple[str, ...]) -> int:
            if not scope or len(set(scope)) != len(scope) or any(k not in by_key for k in scope):
                raise _Stop(Outcome.INVALID_INPUT, "invalid factor/constraint/dependence scope")
            # A spanning star represents the same component relation as a clique.
            graph.add_edges_from((scope[0], key) for key in scope[1:])
            return math.prod(len(by_key[key].candidates) for key in scope)

        covered: set[str] = set()
        table_bytes = 0
        table_keys: set[str] = set()
        for table in (*request.potentials, *request.constraints):
            poll()
            dependency_ids(table.dependency_ids)
            count = scope_size(table.scope)
            if not table.key or table.key in table_keys:
                raise _Stop(Outcome.INVALID_INPUT, "table keys must be nonempty and unique")
            table_keys.add(table.key)
            values = table.values if isinstance(table, LogPotential) else table.allowed
            if count != len(values):
                raise _Stop(Outcome.INVALID_INPUT, "table size does not match declared scope")
            table_bytes += count * (8 if isinstance(table, LogPotential) else 1)
            if isinstance(table, LogPotential):
                covered.update(table.scope)
        if covered != set(by_key):
            raise _Stop(Outcome.INVALID_INPUT, "every decision needs an explicit log potential")
        for dependence in request.dependence_scopes:
            poll()
            dependency_ids(dependence.dependency_ids)
            scope_size(dependence.scope)
            if not dependence.reason:
                raise _Stop(Outcome.INVALID_INPUT, "dependence needs a reason")
        components = tuple(sorted(tuple(sorted(c)) for c in nx.connected_components(graph)))

        # Reserve support, index/sort/reduction temporaries and block arrays conservatively.
        # No product-shaped broadcasting or full-joint assignment matrix is allocated.
        block_size = min(limits.block_states, retained)
        workspace = (
            table_bytes
            + retained * 96
            + block_size * (32 * len(decisions) + 128)
            + 8 * (len(request.events) + sum(shape))
        )
        if workspace > limits.max_workspace_bytes:
            raise _Stop(Outcome.RESOURCE_LIMIT, "numerical workspace memory limit")

        positions = {d.key: i for i, d in enumerate(decisions)}
        required_keys = {d.key for d in required}
        event_keys: set[str] = set()
        if not request.events:
            raise _Stop(Outcome.INVALID_INPUT, "at least one qualified record event is required")
        for event in request.events:
            poll()
            if not event.key or event.key in event_keys or not event.derivations:
                raise _Stop(
                    Outcome.INVALID_INPUT, "event keys/derivations must be nonempty and unique"
                )
            event_keys.add(event.key)
            reading: frozenset[Choice] | None = None
            for derivation in event.derivations:
                poll()
                bindings = {choice.decision: choice.candidate for choice in derivation}
                if len(bindings) != len(derivation) or not required_keys <= bindings.keys():
                    raise _Stop(Outcome.INVALID_INPUT, "event omits a record role or qualifier")
                if any(k not in indices or v not in indices[k] for k, v in bindings.items()):
                    raise _Stop(Outcome.INVALID_INPUT, "event refers to an unknown candidate")
                current = frozenset(c for c in derivation if c.decision in required_keys)
                if reading is not None and reading != current:
                    raise _Stop(
                        Outcome.INVALID_INPUT, "derivations mix distinct qualified readings"
                    )
                reading = current

        potentials = []
        constraints = []
        for table in request.potentials:
            poll()
            # Validate before NumPy conversion, polling even through large supplied tables.
            for offset in range(0, len(table.values), block_size):
                poll()
                for value in table.values[offset : offset + block_size]:
                    if isinstance(value, (bool, np.bool_)) or not isinstance(
                        value, (int, float, np.integer, np.floating)
                    ):
                        raise _Stop(Outcome.INVALID_INPUT, "log potentials must be real numbers")
                    numeric = float(value)
                    if math.isnan(numeric) or numeric == math.inf:
                        raise _Stop(
                            Outcome.NUMERICAL_FAILURE, "NaN or positive-infinity log potential"
                        )
                    if numeric == -math.inf and value != -math.inf:
                        raise _Stop(
                            Outcome.NUMERICAL_FAILURE, "finite log potential exceeds float range"
                        )
            dimensions = tuple(len(by_key[key].candidates) for key in table.scope)
            potentials.append(
                (
                    tuple(positions[k] for k in table.scope),
                    np.asarray(table.values, dtype=np.float64).reshape(dimensions),
                )
            )
        for table in request.constraints:
            poll()
            for offset in range(0, len(table.allowed), block_size):
                poll()
                if any(type(v) is not bool for v in table.allowed[offset : offset + block_size]):
                    raise _Stop(Outcome.INVALID_INPUT, "hard constraint entries must be booleans")
            dimensions = tuple(len(by_key[key].candidates) for key in table.scope)
            constraints.append(
                (
                    tuple(positions[k] for k in table.scope),
                    np.asarray(table.allowed, dtype=np.bool_).reshape(dimensions),
                )
            )

        weights = np.empty(retained, dtype=np.float64)
        for start in range(0, retained, block_size):
            poll()
            stop = min(start + block_size, retained)
            assignment = np.unravel_index(np.arange(start, stop), shape)
            block = np.zeros(stop - start, dtype=np.float64)
            # Establish hard zeros before arithmetic. An impossible assignment cannot fail
            # merely because its unused finite potentials would overflow when added.
            for axes, allowed in constraints:
                poll()
                block[~allowed[tuple(assignment[axis] for axis in axes)]] = -np.inf
            for axes, values in potentials:
                poll()
                block[np.isneginf(values[tuple(assignment[axis] for axis in axes)])] = -np.inf
            active = np.isfinite(block)
            with np.errstate(over="raise", invalid="raise"):
                for axes, values in potentials:
                    poll()
                    block[active] += values[tuple(assignment[axis] for axis in axes)][active]
            weights[start:stop] = block
            examined += stop - start
        positive = int(np.count_nonzero(np.isfinite(weights)))
        poll()
        if not positive:
            return result(Outcome.INFEASIBLE, "retained model has no positive feasible support")
        poll()
        origin = float(np.max(weights))
        # Center BEFORE logsumexp subtraction: very large common offsets must not erase log Z.
        with np.errstate(over="raise", invalid="raise"):
            weights -= origin
        log_z = float(logsumexp(weights))
        log_partition = origin + log_z
        if not math.isfinite(log_z) or not math.isfinite(log_partition):
            raise _Stop(Outcome.NUMERICAL_FAILURE, "nonfinite partition")

        event_logs = np.full(len(request.events), -np.inf)
        marginal_logs = [np.full(size, -np.inf) for size in shape]
        for start in range(0, retained, block_size):
            poll()
            stop = min(start + block_size, retained)
            assignment = np.unravel_index(np.arange(start, stop), shape)
            block = weights[start:stop]
            for event_index, event in enumerate(request.events):
                poll()
                mask = np.zeros(stop - start, dtype=np.bool_)
                for derivation in event.derivations:
                    poll()
                    selected = np.ones(stop - start, dtype=np.bool_)
                    for choice in derivation:
                        selected &= (
                            assignment[positions[choice.decision]]
                            == indices[choice.decision][choice.candidate]
                        )
                    mask |= selected
                event_logs[event_index] = np.logaddexp(
                    event_logs[event_index], logsumexp(block[mask])
                )
            for axis, size in enumerate(shape):
                poll()
                for candidate in range(size):
                    poll()
                    marginal_logs[axis][candidate] = np.logaddexp(
                        marginal_logs[axis][candidate],
                        logsumexp(block[assignment[axis] == candidate]),
                    )
        poll()
        # Display only after full-support normalization. Sorting preserves deterministic ties
        # for the declared ordering; no displayed-list renormalization is performed.
        ranked = np.argsort(-weights, kind="stable")
        alternatives = []
        for flat in ranked[: min(positive, limits.displayed_alternatives)]:
            poll()
            assignment = np.unravel_index(flat, shape)
            alternatives.append(
                CoherentAlternative(
                    tuple(
                        Choice(d.key, d.candidates[int(i)].key)
                        for d, i in zip(decisions, assignment, strict=True)
                    ),
                    math.exp(float(weights[flat]) - log_z),
                )
            )
        poll()
        return result(
            Outcome.COMPLETED,
            "complete retained joint; provisional candidate-relative event probabilities",
            event_probabilities=tuple(
                EventProbability(e.key, math.exp(float(p) - log_z))
                for e, p in zip(request.events, event_logs, strict=True)
            ),
            marginals=tuple(
                Marginal(d.key, c.key, math.exp(float(p) - log_z))
                for d, logs in zip(decisions, marginal_logs, strict=True)
                for c, p in zip(d.candidates, logs, strict=True)
            ),
            alternatives=tuple(alternatives),
            log_partition=log_partition,
            exact_retained_support=True,
        )
    except _Stop as exc:
        return result(exc.outcome, exc.detail)
    except MemoryError:
        return result(Outcome.RESOURCE_LIMIT, "numerical allocation failed")
    except (FloatingPointError, OverflowError) as exc:
        return result(Outcome.NUMERICAL_FAILURE, str(exc))
