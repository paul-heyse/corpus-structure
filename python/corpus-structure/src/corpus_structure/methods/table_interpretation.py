"""Source-bound shared table-band policy over current scoped attachment products.

Uniform per-edge applicability priors and a declared soft coherence preference are policy
assumptions, not measured likelihoods. Each shared candidate band contributes once;
no physical source observation is multiplied once per row. Private posterior standing
remains separate from independently established support.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import product
from math import log
from threading import Event
from typing import Literal

from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.record_interpretation import (
    Candidate,
    CandidateSelection,
    Decision,
    Dependency,
    DependencyKind,
    LocalInterpretationRequest,
    LogPotential,
    SearchLimits,
)

from .local_interpretation import local_constraint_id, local_question_operation

POLICY_VERSION = "shared-table-band-2"
# The selected exact-enumeration pilot handles small ambiguity bands. Discovery
# and private evidence retention cover larger tables without constructing their
# exponential applicability joint or inventing a uniformly applicable band.
MAX_BAND_EDGES = 16
MODE = Literal["feasibility", "independent", "coupled"]


def table_policy_operations(
    *,
    contributions,
    dependency_ids,
    source_revision: str,
    mode: MODE = "coupled",
    cancellation: Event | None = None,
):
    if mode not in {"feasibility", "independent", "coupled"} or not source_revision:
        raise ValueError("table policy requires declared mode and source revision")
    by_id = {row["contribution_id"]: row for row in contributions}
    if len(by_id) != len(contributions):
        raise ValueError("table policy cannot collapse duplicate contribution identities")
    groups = defaultdict(dict)
    selected = defaultdict(set)
    for row in contributions:
        if row.get("semantic_type") != "structural.scoped_attachment":
            continue
        raw = row["value"]
        value = source_python(raw) if raw.get("kind") == "object" else raw
        if value.get("protocol") != "scoped-attachment-1":
            raise ValueError("table policy requires current scoped attachments")
        if value["relation"] not in {"header", "unit", "note", "value_role"}:
            continue
        subject, target = value["subject_id"], value["target_id"]
        if subject not in by_id or target not in by_id:
            raise ValueError("table policy endpoint is outside retained contribution selection")
        key = (value["region"], value["scope"], value["relation"], target)
        if subject in groups[key]:
            raise ValueError("table policy repeats one physical attachment in its band")
        groups[key][subject] = row["contribution_id"]
        selected[key].update((subject, target, row["contribution_id"]))
    if not groups:
        return (
            local_question_operation(
                question="table attachment interpretation",
                contributions=contributions,
                dependency_ids=dependency_ids,
                cancellation=cancellation,
            ),
        )
    operations = []
    for group, edges in sorted(groups.items()):
        ids = selected[group]
        retained = tuple(by_id[key] for key in sorted(ids))
        deps = tuple(
            sorted(
                set(dependency_ids)
                | {d for row in retained for d in row.get("computation_dependencies", ())}
            )
        )
        question = "shared table band " + repr(group)
        scope = local_constraint_id(question, retained, deps)
        if len(edges) > MAX_BAND_EDGES:
            operations.append(
                local_question_operation(
                    question=question,
                    contributions=retained,
                    dependency_ids=deps,
                    cancellation=cancellation,
                    unavailable_policy_version=POLICY_VERSION,
                    unavailable_reason=(
                        f"Exact small-band policy supports at most {MAX_BAND_EDGES} "
                        f"attachment applicability axes; this band has {len(edges)}. "
                        "All located attachments remain retained and unassessed; "
                        "no applicability posterior or uniform-band claim is computed."
                    ),
                )
            )
            continue
        decisions = tuple(
            Decision(edge, (Candidate("does_not_apply"), Candidate("applies")))
            for _subject, edge in sorted(edges.items())
        )
        metadata = (
            Dependency("table-model:" + source_revision, DependencyKind.MODEL, source_revision),
            Dependency(
                "table-ontology:scoped-attachment-1", DependencyKind.ONTOLOGY, "scoped-attachment-1"
            ),
            Dependency("table-policy:" + POLICY_VERSION, DependencyKind.POLICY, POLICY_VERSION),
        )
        dependencies = (
            tuple(Dependency(d, DependencyKind.OBSERVATION, source_revision) for d in deps)
            + metadata
        )
        potentials = list(
            LogPotential(
                "uniform:" + d.key,
                (d.key,),
                tuple(0.0 for _ in d.candidates),
                (metadata[-1].key,),
            )
            for d in decisions
        )
        states = 1
        for d in decisions:
            states *= len(d.candidates)
        if mode == "coupled" and len(decisions) > 1 and states <= SearchLimits().max_states:
            weights = tuple(
                log(2.0) if len(set(state)) == 1 else 0.0
                for state in product(*(tuple(c.key for c in d.candidates) for d in decisions))
            )
            potentials.append(
                LogPotential(
                    "shared-band:" + scope,
                    tuple(d.key for d in decisions),
                    weights,
                    (*deps, metadata[-1].key),
                )
            )
        request = LocalInterpretationRequest(
            decisions=decisions,
            potentials=tuple(potentials),
            constraints=(),
            dependencies=dependencies,
            selection=CandidateSelection(scope, deps),
            model_dependency_id=metadata[0].key,
            ontology_dependency_id=metadata[1].key,
            policy_dependency_id=metadata[2].key,
            feasibility_control=mode == "feasibility",
        )
        operations.append(
            local_question_operation(
                question=question,
                contributions=retained,
                dependency_ids=deps,
                request=request,
                cancellation=cancellation,
            )
        )
    return tuple(operations)
