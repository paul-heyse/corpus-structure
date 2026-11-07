"""Prepare private, source-conditioned interpretations over retained table products."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from itertools import product
from math import log, prod
from threading import Event
from typing import Any, Literal

from pydantic import TypeAdapter

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
    alignment: Literal["exact", "overlap"]
    dependencies: tuple[str, ...]
    observed_anchor: str
    schematic_anchor: str
    declaration_anchor: str


@dataclass(frozen=True)
class TableCorrespondencePremise:
    identity: str
    standing: Literal["fixed", "alternative"]
    source_revision: str
    source_view_id: int
    source_projection: str
    source_recipe: str
    observed_table: str
    schematic_table: str
    observed_caption: str
    schematic_caption: str
    declaration_pointer: str
    bindings: dict[str, TableCorrespondenceBinding]


@dataclass(frozen=True)
class TableCorrespondenceRequest(LocalInterpretationRequest):
    correspondence_premises: tuple[TableCorrespondencePremise, ...] = ()
    correspondence_status: Literal["fixed", "ambiguous", "unavailable"] = "unavailable"
    correspondence_reason: str | None = None


@cache
def _correspondence_request_adapter() -> TypeAdapter[TableCorrespondenceRequest]:
    return TypeAdapter(TableCorrespondenceRequest)


def execute_table_correspondence(
    contributions: Sequence[Mapping[str, Any]],
    prepared: Sequence[Mapping[str, Any]],
    *,
    cancellation: Event | None = None,
) -> tuple[dict[str, Any], ...]:
    """Hydrate native requests and run the finite executor over their frozen support."""
    by_id = {row["contribution_id"]: row for row in contributions}
    operations = []
    for question in prepared:
        retained = tuple(by_id[key] for key in question["contribution_ids"])
        dependencies = tuple(question["dependencies"])
        raw_request = question["request"]
        request = (
            _correspondence_request_adapter().validate_python(raw_request)
            if raw_request is not None
            else None
        )
        operation = local_question_operation(
            question=question["question"],
            contributions=retained,
            dependency_ids=dependencies,
            request=request,
            cancellation=cancellation,
            unavailable_policy_version=CORRESPONDENCE_POLICY_VERSION,
            unavailable_reason=question["reason"],
        )
        if operation["operation_key"] != question["scope_id"]:
            raise ValueError("prepared table correspondence differs from the selected band")
        operations.append(operation)
    return tuple(operations)


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
            str(pin["source_view_id"]) if pin else "",
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
