"""Prepare private, source-conditioned interpretations over retained table products."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import product
from math import isfinite, log, prod
from threading import Event
from typing import Any, Literal

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.record_interpretation import (
    Candidate,
    CandidateKind,
    CandidateSelection,
    Choice,
    CompositeEvent,
    Decision,
    DependenceScope,
    Dependency,
    DependencyKind,
    HardConstraint,
    LocalInterpretationRequest,
    LogPotential,
    SearchLimits,
)

from .local_interpretation import local_constraint_id, local_question_operation

POLICY_VERSION = "shared-table-band-3"
CORRESPONDENCE_POLICY_VERSION = "source-correspondence-1"
MAX_BAND_EDGES = 16
MODE = Literal["feasibility", "independent", "coupled"]
_RELATIONS = frozenset({"header", "unit", "note", "value_role"})
_UNRESOLVED = "unresolved"
_INAPPLICABLE = "does_not_apply"


@dataclass(frozen=True)
class TableCorrespondenceBinding:
    """One explicitly supplied correspondence hypothesis; no publication authority."""

    alignment: Literal["exact", "overlap"]
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class TableCorrespondencePremise:
    identity: str
    standing: Literal["fixed", "alternative"]
    bindings: dict[str, TableCorrespondenceBinding]


@dataclass(frozen=True)
class TableCorrespondenceRequest(LocalInterpretationRequest):
    correspondence_premises: tuple[TableCorrespondencePremise, ...] = ()
    correspondence_status: Literal["fixed", "ambiguous"] = "fixed"


def table_correspondence_request(
    edges: Sequence[Mapping[str, Any]],
    premises: Sequence[TableCorrespondencePremise],
    *,
    source_revision: str,
    source_projection: str,
    scope_id: str,
    dependency_ids: tuple[str, ...],
    weight_scale: float = 1,
) -> TableCorrespondenceRequest | None:
    """Pure finite matching over explicit hypotheses, never a native source reader.

    Callers own source selection and the meaning of the supplied evidence. No current
    declared producer consumes this helper. Missing correspondence stays unavailable;
    the retained numerical kernel cannot manufacture source or admission authority.
    """
    if not isfinite(weight_scale) or weight_scale <= 0:
        raise ValueError("correspondence weight must be finite and positive")
    if len(set(dependency_ids)) != len(dependency_ids) or not all(dependency_ids):
        raise ValueError("correspondence evidence requires distinct nonempty references")
    edge_ids = {edge["id"] for edge in edges}
    if len(edge_ids) != len(edges) or not all(edge_ids) or edge_ids & {_UNRESOLVED, _INAPPLICABLE}:
        raise ValueError("correspondence edges require distinct actual candidate references")
    declared = set(dependency_ids)
    axes: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for edge in edges:
        if (
            not edge["axis"]
            or edge["axis"] == "M"
            or edge["role"] not in _RELATIONS
            or type(edge["direct"]) is not bool
            or type(edge["disjoint"]) is not bool
            or not set(edge["evidence"]) <= declared
        ):
            raise ValueError("correspondence edge has foreign evidence or invalid axis/role")
        axes[edge["axis"]].append(edge)
    if len({p.identity for p in premises}) != len(premises) or any(
        not p.identity or p.standing not in {"fixed", "alternative"} for p in premises
    ):
        raise ValueError("correspondence premises require distinct explicit references")
    for premise in premises:
        if not premise.bindings:
            raise ValueError("correspondence premise requires actual candidate bindings")
        if not premise.bindings.keys() <= edge_ids:
            raise ValueError("correspondence binding names a foreign candidate")
        if any(
            binding.alignment not in {"exact", "overlap"}
            or not binding.dependencies
            or not set(binding.dependencies) <= declared
            for binding in premise.bindings.values()
        ):
            raise ValueError("correspondence binding names foreign or absent evidence")
    if not premises:
        return None
    policy = f"table-policy:{CORRESPONDENCE_POLICY_VERSION}:correspondence:{weight_scale:g}"
    model, ontology = "table-model:" + source_revision, "table-ontology:scoped-table-roles"
    weight = weight_scale * log(2)
    ambiguous = len(premises) != 1 or premises[0].standing != "fixed"
    decisions, potentials, constraints, dependence = [], [], [], []
    if ambiguous:
        decisions.append(
            Decision(
                "M",
                (
                    Candidate(
                        _UNRESOLVED,
                        CandidateKind.UNRESOLVED,
                        "shared correspondence unresolved within retained evidence",
                    ),
                    *(Candidate(p.identity) for p in premises),
                ),
            )
        )
        potentials.append(
            LogPotential(
                "shared-correspondence-evidence",
                ("M",),
                (0, *(weight for _ in premises)),
                tuple(sorted({p.identity for p in premises} | {policy})),
            )
        )
    events: dict[str, list[tuple[Choice, ...]]] = defaultdict(list)
    for axis, members in sorted(axes.items()):
        members = sorted(members, key=lambda edge: edge["id"])
        roles = {edge["role"] for edge in members}
        if len(roles) != 1:
            raise ValueError("correspondence axis has competing role meanings")
        role = next(iter(roles))
        candidates = [Candidate(_UNRESOLVED, CandidateKind.UNRESOLVED, "retained scope incomplete")]
        if role in {"note", "unit"}:
            candidates.append(Candidate(_INAPPLICABLE))
        candidates.extend(Candidate(edge["id"]) for edge in members)
        decisions.append(Decision(axis, tuple(candidates)))
        by_id = {edge["id"]: edge for edge in members}
        evidence = {ref for edge in members for ref in edge["evidence"]}
        potentials.append(
            LogPotential(
                "source-choice:" + axis,
                (axis,),
                tuple(
                    weight
                    if (edge := by_id.get(candidate.key)) is not None
                    and edge["direct"]
                    and not edge["disjoint"]
                    else 0
                    for candidate in candidates
                ),
                tuple(sorted(evidence | {policy})),
            )
        )
        selected = [(p, b) for p in premises for key, b in p.bindings.items() if key in by_id]
        if selected:
            order = (None, *premises) if ambiguous else tuple(premises)
            values = tuple(
                0
                if premise is None or candidate.key not in premise.bindings
                else weight
                if premise.bindings[candidate.key].alignment == "exact"
                else weight / 2
                for premise in order
                for candidate in candidates
            )
            deps = tuple(
                sorted(
                    {p.identity for p, _ in selected}
                    | {d for _, b in selected for d in b.dependencies}
                    | {policy}
                )
            )
            scope = ("M", axis) if ambiguous else (axis,)
            potentials.append(LogPotential("correspondence-role:" + axis, scope, values, deps))
            if ambiguous:
                dependence.append(
                    DependenceScope(
                        scope, deps, "One source correspondence conditions this local role reading"
                    )
                )
        if any(edge["disjoint"] for edge in members):
            constraints.append(
                HardConstraint(
                    "source-disjoint:" + axis,
                    (axis,),
                    tuple(
                        not by_id.get(candidate.key, {}).get("disjoint", False)
                        for candidate in candidates
                    ),
                    tuple(
                        sorted(
                            {d for edge in members if edge["disjoint"] for d in edge["evidence"]}
                            | {ontology}
                        )
                    ),
                )
            )
        events[role].extend((Choice(axis, edge["id"]),) for edge in members if not edge["disjoint"])
    return TableCorrespondenceRequest(
        decisions=tuple(decisions),
        potentials=tuple(potentials),
        constraints=tuple(constraints),
        dependencies=(
            *(Dependency(d, DependencyKind.OBSERVATION, source_revision) for d in dependency_ids),
            *(Dependency(p.identity, DependencyKind.CONTEXT, source_projection) for p in premises),
            Dependency(model, DependencyKind.MODEL, source_revision),
            Dependency(ontology, DependencyKind.ONTOLOGY, CORRESPONDENCE_POLICY_VERSION),
            Dependency(policy, DependencyKind.POLICY, CORRESPONDENCE_POLICY_VERSION),
        ),
        selection=CandidateSelection(
            scope_id,
            dependency_ids,
            exclusions=tuple(
                sorted("source-disjoint:" + edge["id"] for edge in edges if edge["disjoint"])
            ),
        ),
        model_dependency_id=model,
        ontology_dependency_id=ontology,
        policy_dependency_id=policy,
        events=tuple(
            CompositeEvent(
                "any-" + role,
                "At least one retained " + role + " reading applies in this table row",
                tuple(derivations),
            )
            for role, derivations in sorted(events.items())
        ),
        dependence_scopes=tuple(dependence),
        correspondence_premises=tuple(premises),
        correspondence_status="ambiguous" if ambiguous else "fixed",
    )


@dataclass(frozen=True)
class _Attachment:
    identity: str
    subject: str
    target: str
    role: str
    evidence: bool
    disjoint: bool
    level: tuple[int, int] | None
    evidence_key: str


def _value(row: Mapping[str, Any]) -> dict[str, Any]:
    value = row.get("value", {})
    return source_python(value) if value.get("kind") == "object" else value


def _extent(value: Mapping[str, Any], axis: str) -> tuple[int, int] | None:
    start, end = (value.get(f"{boundary}_{axis}_offset_idx") for boundary in ("start", "end"))
    if type(start) is int and type(end) is int and 0 <= start < end:
        return start, end
    return None


def _attachment(identity, value, subject, target, evidence_key) -> _Attachment:
    role = value["relation"]
    subject_column, target_column = _extent(subject, "col"), _extent(target, "col")
    subject_row, target_row = _extent(subject, "row"), _extent(target, "row")
    source_header = (
        role in {"header", "unit", "value_role"}
        and target.get("role") == "header"
        and subject.get("region") == target.get("region") == value["region"]
        and value.get("basis") in {"native_geometry", "matched_cue"}
    )
    disjoint = False
    contained = False
    if source_header and subject_column and target_column and subject_row and target_row:
        disjoint = subject_column[1] <= target_column[0] or target_column[1] <= subject_column[0]
        contained = (
            target_column[0] <= subject_column[0] <= subject_column[1] <= target_column[1]
            and target_row[1] <= subject_row[0]
        )
    # A located role cue and its geometry describe one reading of a physical
    # header. Reusing that header for a measure does not create another vote.
    located_cue = (
        value.get("basis") == "matched_cue"
        and bool(target.get("text"))
        and role in {"unit", "note", "value_role"}
    )
    return _Attachment(
        identity,
        value["subject_id"],
        value["target_id"],
        role,
        (contained or located_cue) and not disjoint,
        disjoint,
        target_row if source_header else None,
        evidence_key,
    )


def _decisions(edges: tuple[_Attachment, ...]) -> tuple[Decision, ...]:
    grouped: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for edge in edges:
        # Only competing readings of the same header level and role share an
        # exclusive axis. Nested bands and separate note/unit attachments can
        # coexist, including multiple uses of the same note.
        axis = edge.identity
        if edge.role == "value_role":
            axis = "value_role"
        elif edge.role == "header" and edge.level is not None:
            axis = repr(edge.level)
        grouped[edge.subject, edge.role, axis].append(edge.identity)
    decisions = []
    for (subject, role, axis), candidates in sorted(grouped.items()):
        options = [Candidate(_UNRESOLVED, CandidateKind.UNRESOLVED, "retained scope incomplete")]
        if role in {"note", "unit"}:
            options.append(Candidate(_INAPPLICABLE))
        options.extend(Candidate(candidate) for candidate in sorted(candidates))
        decisions.append(Decision(f"{subject}/{role}/{axis}", tuple(options)))
    return tuple(decisions)


def _request(question_id, deps, edges, decisions, source_revision, mode, weight_scale):
    policy_id = f"table-policy:{POLICY_VERSION}:{mode}:{weight_scale:g}"
    model_id = "table-model:" + source_revision
    ontology_id = "table-ontology:scoped-table-roles"
    dependencies = (
        *(Dependency(dep, DependencyKind.OBSERVATION, source_revision) for dep in deps),
        Dependency(model_id, DependencyKind.MODEL, source_revision),
        Dependency(ontology_id, DependencyKind.ONTOLOGY, POLICY_VERSION),
        Dependency(policy_id, DependencyKind.POLICY, POLICY_VERSION),
    )
    by_id = {edge.identity: edge for edge in edges}
    forbidden = {edge.identity for edge in edges if edge.disjoint}
    linked: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    evidence_ids: dict[str, set[str]] = defaultdict(set)
    events: dict[str, list[tuple[Choice, ...]]] = defaultdict(list)
    constraints = []
    for decision in decisions:
        masked = tuple(
            candidate.key for candidate in decision.candidates if candidate.key in forbidden
        )
        if masked:
            source_evidence = {
                key for eid in masked for key in (eid, by_id[eid].subject, by_id[eid].target)
            }
            constraints.append(
                HardConstraint(
                    "source-disjoint:" + decision.key,
                    (decision.key,),
                    tuple(candidate.key not in forbidden for candidate in decision.candidates),
                    (*sorted(source_evidence), ontology_id),
                )
            )
        for candidate in decision.candidates:
            edge = by_id.get(candidate.key)
            if edge is None or edge.disjoint:
                continue
            events[edge.role].append((Choice(decision.key, candidate.key),))
            if edge.evidence:
                linked[edge.evidence_key][decision.key].add(candidate.key)
                evidence_ids[edge.evidence_key].add(edge.target)
    evidence_weight = weight_scale * log(2.0)
    unary = defaultdict(float)
    unary_deps = defaultdict(set)
    joint = []
    scopes = []
    by_decision = {d.key: d for d in decisions}
    for observation, candidates_by_axis in sorted(linked.items()):
        axes = tuple(sorted(candidates_by_axis))
        targets = tuple(sorted(evidence_ids[observation]))
        if len(axes) > 1:
            scopes.append(
                DependenceScope(
                    axes, targets, "same located header or note constrains several readings"
                )
            )
        if mode == "feasibility":
            continue
        if mode == "coupled" and len(axes) > 1:
            # One bounded term for the shared physical evidence. Full coverage
            # receives its declared support once; unresolved/partial choices
            # remain feasible and do not acquire a second independent vote.
            assignments = product(*(by_decision[axis].candidates for axis in axes))
            values = tuple(
                evidence_weight
                if all(
                    choice.key in candidates_by_axis[axis]
                    for axis, choice in zip(axes, choices, strict=True)
                )
                else 0.0
                for choices in assignments
            )
            joint.append(
                LogPotential("shared-source:" + observation, axes, values, (*targets, policy_id))
            )
        else:
            # The independent comparison allocates the same evidence budget
            # across its unary terms, preserving the aggregate weight.
            for axis, candidates in candidates_by_axis.items():
                for candidate in candidates:
                    unary[axis, candidate] += evidence_weight / len(axes)
                unary_deps[axis].update(targets)
    potentials = tuple(
        LogPotential(
            "source-choice:" + decision.key,
            (decision.key,),
            tuple(unary[decision.key, candidate.key] for candidate in decision.candidates),
            (*sorted(unary_deps[decision.key]), policy_id),
        )
        for decision in decisions
    )
    return LocalInterpretationRequest(
        decisions=decisions,
        potentials=(*potentials, *joint),
        constraints=tuple(constraints),
        dependencies=dependencies,
        selection=CandidateSelection(
            question_id,
            deps,
            exclusions=tuple("source-disjoint:" + edge for edge in sorted(forbidden)),
        ),
        model_dependency_id=model_id,
        ontology_dependency_id=ontology_id,
        policy_dependency_id=policy_id,
        events=tuple(
            CompositeEvent(
                "any-" + role,
                "At least one retained " + role + " reading applies in this table row",
                tuple(derivations),
            )
            for role, derivations in sorted(events.items())
        ),
        dependence_scopes=tuple(scopes),
        feasibility_control=mode == "feasibility",
    )


def table_policy_operations(
    *,
    contributions,
    dependency_ids,
    source_revision: str,
    mode: MODE = "coupled",
    weight_scale: float = 1.0,
    cancellation: Event | None = None,
):
    if (
        mode not in {"feasibility", "independent", "coupled"}
        or not source_revision
        or type(weight_scale) not in {float, int}
        or weight_scale not in {0.5, 1.0, 2.0}
    ):
        raise ValueError("table policy requires declared mode, source revision and weight scale")
    by_id = {row["contribution_id"]: row for row in contributions}
    if len(by_id) != len(contributions):
        raise ValueError("table policy cannot collapse duplicate contribution identities")
    groups: dict[tuple[str, str, str, str], list[_Attachment]] = defaultdict(list)
    seen = set()
    for identity, row in by_id.items():
        if row.get("semantic_type") != "structural.scoped_attachment":
            continue
        value = _value(row)
        if value.get("protocol") != "scoped-attachment-1":
            raise ValueError("table policy requires current scoped attachments")
        if value["relation"] not in _RELATIONS:
            continue
        subject, target = value["subject_id"], value["target_id"]
        if subject not in by_id or target not in by_id:
            raise ValueError("table policy endpoint is outside retained contribution selection")
        subject_row, target_row = by_id[subject], by_id[target]
        pin = row.get("pin")
        if pin and any(endpoint.get("pin") != pin for endpoint in (subject_row, target_row)):
            raise ValueError("table policy endpoints differ from the declared source scope")
        subject_value, target_value = _value(subject_row), _value(target_row)
        group = (
            canonical_bytes(pin).decode() if pin else "",
            value["region"],
            value["scope"],
            repr(_extent(subject_value, "row") or subject),
        )
        pair = (*group, value["relation"], subject, target)
        if pair in seen:
            raise ValueError("table policy repeats one physical attachment in its band")
        seen.add(pair)
        declarations = [
            key
            for key in row.get("computation_dependencies", ())
            if key in by_id and _value(by_id[key]).get("role") == "table_role_declaration"
        ]
        if len(declarations) > 1:
            raise ValueError("one attachment cannot vote through multiple role declarations")
        evidence_key = (
            declarations[0] if declarations else target_row.get("occurrence_id") or target
        )
        groups[group].append(
            _attachment(identity, value, subject_value, target_value, evidence_key)
        )
    if not groups:
        return (
            local_question_operation(
                question="table attachment interpretation",
                contributions=contributions,
                dependency_ids=dependency_ids,
                cancellation=cancellation,
                unavailable_policy_version=POLICY_VERSION,
            ),
        )
    operations = []
    for group, unsorted_edges in sorted(groups.items()):
        edges = tuple(sorted(unsorted_edges, key=lambda edge: edge.identity))
        ids = {key for edge in edges for key in (edge.identity, edge.subject, edge.target)}
        ids.update(edge.evidence_key for edge in edges if edge.evidence_key in by_id)
        retained = tuple(by_id[key] for key in sorted(ids))
        deps = tuple(
            sorted(
                ids
                | set(dependency_ids)
                | {d for row in retained for d in row.get("computation_dependencies", ())}
            )
        )
        question = "shared table row " + repr(group)
        decisions = _decisions(edges)
        states = prod(len(decision.candidates) for decision in decisions)
        reason = None
        if len(edges) > MAX_BAND_EDGES or states > SearchLimits().max_states:
            reason = (
                f"Exact small-band policy permits at most {MAX_BAND_EDGES} attachments and "
                f"{SearchLimits().max_states} states; this row has {len(edges)} attachments and "
                f"{states} states. All located attachments remain retained and unassessed."
            )
        elif not any(edge.evidence for edge in edges):
            reason = "No located source evidence supports a weighted choice for this row."
        request = (
            _request(
                local_constraint_id(question, retained, deps),
                deps,
                edges,
                decisions,
                source_revision,
                mode,
                weight_scale,
            )
            if reason is None
            else None
        )
        operations.append(
            local_question_operation(
                question=question,
                contributions=retained,
                dependency_ids=deps,
                request=request,
                cancellation=cancellation,
                unavailable_policy_version=POLICY_VERSION,
                unavailable_reason=reason,
            )
        )
    return tuple(operations)
