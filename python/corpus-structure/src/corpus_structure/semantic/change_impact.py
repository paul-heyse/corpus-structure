"""Subject-relative change explanations over authenticated selected DDO custody.

Source edits never execute a demand. A proposed model supplies potential relevance;
only a separately admitted target selection establishes current substitution. The
native read owner retains permission/trust authority and complete support closure.
"""

from __future__ import annotations

import base64
from collections import defaultdict
from hashlib import sha256
from typing import Any, Literal, assert_never

from pydantic import BaseModel, ConfigDict, Field

from ._data_operation_fates import VisibleFate
from .data_operation_json import json_bytes, json_loads
from .data_operation_model import EffectiveDataOperationModel, json_context_meaning
from .demand_results import read_demand_result, stream_selected_support


class PopulationMember(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    operation: str
    subject: str
    subject_definition: str
    original_source: str | None
    analyzed_scope: dict[str, Any] = Field(default_factory=dict)

    @property
    def key(self) -> bytes:
        return json_bytes(
            dict(
                operation=self.operation,
                subject=self.subject,
                subject_definition=self.subject_definition,
                original_source=self.original_source,
                analyzed_scope_meaning=json_context_meaning(
                    json_bytes(self.analyzed_scope)
                ).decode(),
            )
        )


class ChangeImpactRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    project_id: str = Field(min_length=1)
    before_demand_id: str = Field(min_length=1)
    target_release_id: str = Field(min_length=1)
    target_demand_id: str | None = None
    before_population: tuple[PopulationMember, ...] = ()
    target_population: tuple[PopulationMember, ...] = ()
    population_complete: bool = False
    scope: dict[str, Any] = Field(default_factory=dict)
    read_id: str | None = None
    expected_cut: str | None = None
    target_read_id: str | None = None
    expected_target_cut: str | None = None
    cursor: str | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    max_bytes: int = Field(default=8388608, ge=1024, le=8388608)


ImpactState = Literal[
    "potential", "awaiting", "stale", "revoked", "substitutable", "inapplicable", "unknown"
]


class ChangeImpactItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    member: PopulationMember
    state: ImpactState
    reasons: tuple[str, ...]
    changed_roots: tuple[str, ...] = ()
    witnesses: tuple[str, ...] = ()
    invalidity_causes: tuple[RevocationCause, ...] = ()


class _Continuation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    comparison: str
    request_identity: str
    offset: int = Field(ge=0, strict=True)
    before_read: str
    before_cut: str
    target_read: str | None
    target_cut: str | None


class ChangeImpactPage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal["ddo-change-impact-v1"] = "ddo-change-impact-v1"
    comparison_id: str
    before_cut: dict[str, Any]
    target_cut: dict[str, Any] | None
    target_release_id: str
    items: tuple[ChangeImpactItem, ...]
    complete: bool
    population_complete: bool
    unknowns: tuple[str, ...]
    continuation: str | None


class RevocationCause(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["direct", "upstream"]
    reference: str
    selector_kind: str
    selector: str
    derivation_id: str | None = None
    support_path: tuple[str, ...] = ()


class SelectionEvidence(BaseModel):
    """Detached native observation, never an alternate admission decision."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    member: PopulationMember
    fate: VisibleFate
    derivations: tuple[str, ...] = ()
    products: tuple[tuple[str, str | None, str, int, int], ...] = ()
    inputs: tuple[tuple[str, str | None, str, int, int], ...] = ()
    support: tuple[str, ...] = ()
    invalidity_causes: tuple[RevocationCause, ...] = ()
    read_unknowns: tuple[str, ...] = ()


def _impact_fate_class(
    fate: VisibleFate,
) -> Literal["fulfilled", "awaiting", "unavailable", "cancelled", "inapplicable", "unestablished"]:
    """Total protocol interpretation; observation fate alone is never value admission."""
    match fate:
        case "fulfilled":
            return "fulfilled"
        case (
            "waiting"
            | "attached"
            | "awaiting-discovery"
            | "awaiting-inputs"
            | "awaiting-external"
            | "awaiting-population"
        ):
            return "awaiting"
        case "unavailable":
            return "unavailable"
        case "cancelled":
            return "cancelled"
        case "not-applicable":
            return "inapplicable"
        case "failed" | "partial" | "invalid" | "unknown" | "known-absent" | "closed":
            return "unestablished"
        case _:
            assert_never(fate)


OperationChange = Literal["introduced", "removed", "recipe", "eligibility", "dependencies"]


def operation_determinant_changes(
    before: EffectiveDataOperationModel, target: EffectiveDataOperationModel
) -> dict[str, tuple[OperationChange, ...]]:
    """Compare effective operations independently of release identity and reachability."""
    old = {op.semantic_id: op for op in before.operations}
    new = {op.semantic_id: op for op in target.operations}
    old_ids = {(row.owner, row.domain): row.key for row in before.identities}
    new_ids = {(row.owner, row.domain): row.key for row in target.identities}
    changes: dict[str, tuple[OperationChange, ...]] = {}
    for name in sorted(old.keys() | new.keys()):
        if name not in old:
            changes[name] = ("introduced",)
            continue
        if name not in new:
            changes[name] = ("removed",)
            continue
        reasons: list[OperationChange] = []
        if old[name].recipe != new[name].recipe or old_ids.get((name, "recipe")) != new_ids.get(
            (name, "recipe")
        ):
            reasons.append("recipe")
        if old[name].eligibility != new[name].eligibility:
            reasons.append("eligibility")
        if (old[name].dependencies, old[name].potential_dependencies) != (
            new[name].dependencies,
            new[name].potential_dependencies,
        ):
            reasons.append("dependencies")
        if reasons:
            changes[name] = tuple(reasons)
    return changes


def changed_operations(before: EffectiveDataOperationModel, target: EffectiveDataOperationModel):
    """Project conservative reachability over both declared dependency sides."""
    from .data_operation_identity import SemanticGraph

    roots = set(operation_determinant_changes(before, target))
    names = {operation.semantic_id for model in (before, target) for operation in model.operations}
    records = {
        "nodes": [dict(id=name, category="operation", payload={}) for name in sorted(names)],
        "edges": [],
    }
    for side, model in (("before", before), ("target", target)):
        projection = model.projection_graph(
            "selected-dependencies",
            selected_dependencies=tuple(
                (operation.semantic_id, operation.potential_dependencies)
                for operation in model.operations
            ),
        )
        for edge in projection.edges:
            records["edges"].append(
                {**edge.record(), "relation": side + "_change_" + edge.relation}
            )
    graph = SemanticGraph(records)
    affected: dict[str, set[str]] = defaultdict(set)
    for root in sorted(roots):
        for name in graph.closure((root,), direction="dependents"):
            affected[name].add(root)
    return roots, affected


def classify_change_impact(
    before_model: EffectiveDataOperationModel,
    target_model: EffectiveDataOperationModel,
    *,
    before: tuple[SelectionEvidence, ...],
    target: tuple[SelectionEvidence, ...] = (),
    before_population: tuple[PopulationMember, ...] = (),
    target_population: tuple[PopulationMember, ...] = (),
    population_complete: bool = False,
    target_observed: bool = False,
) -> tuple[ChangeImpactItem, ...]:
    """Compare exact contexts; graph reachability establishes potential only.

    A fulfilled target read is native proof of its own support/admission. Equal
    output IDs alone cannot grant reuse: a target must actually be fulfilled.
    """
    _, affected = changed_operations(before_model, target_model)
    old, new = {r.member.key: r for r in before}, {r.member.key: r for r in target}
    if len(old) != len(before) or len(new) != len(target):
        raise ValueError("impact observations repeat an operation/context")
    old_population = {r.key: r for r in before_population}
    new_population = {r.key: r for r in target_population}
    if len(old_population) != len(before_population) or len(new_population) != len(
        target_population
    ):
        raise ValueError("population witness repeats an operation/context")
    members = (
        old_population
        | new_population
        | {k: r.member for k, r in old.items()}
        | {k: r.member for k, r in new.items()}
    )
    target_operations = {op.semantic_id for op in target_model.operations}
    rows = []
    for key, member in sorted(members.items()):
        previous, current = old.get(key), new.get(key)
        roots = tuple(sorted(affected.get(member.operation, ())))
        witnesses = tuple(
            sorted(
                set(
                    (previous.derivations if previous else ())
                    + (current.derivations if current else ())
                )
            )
        )
        fate_class = _impact_fate_class(current.fate) if current else None
        if member.operation not in target_operations:
            state, reason = "inapplicable", "operation_removed_from_target"
        elif population_complete and key in old_population and key not in new_population:
            state, reason = "inapplicable", "absent_under_complete_target_population"
        elif fate_class == "cancelled":
            state, reason = "inapplicable", "target_demand_cancelled"
        elif current and fate_class == "inapplicable":
            state, reason = "inapplicable", "native_target_not_applicable"
        elif current and fate_class == "unavailable":
            state = "revoked" if current.invalidity_causes else "unknown"
            reason = (
                "native_target_revocation_witness"
                if current.invalidity_causes
                else "native_target_unavailable_cause_unestablished"
            )
        elif current and fate_class == "fulfilled":
            if previous and previous.products == current.products:
                # A direct producer revocation cannot be laundered by reusing its
                # exact episode; a distinct admitted producer may establish equal value.
                shared = set(previous.derivations) & set(current.derivations)
                direct_revoked = any(
                    cause.kind == "direct"
                    and (
                        cause.derivation_id in shared
                        or (cause.selector_kind == "derivation" and cause.selector in shared)
                    )
                    for cause in previous.invalidity_causes
                )
                if direct_revoked:
                    state, reason = (
                        "unknown",
                        "unavailable_producer_requires_distinct_native_admission",
                    )
                else:
                    state, reason = "substitutable", "equal_value_with_native_target_admission"
            elif previous:
                state, reason = "stale", "admitted_target_outputs_differ"
            else:
                state, reason = "substitutable", "newly_derived_native_target_selection"
        elif previous and previous.fate == "unavailable":
            state = "revoked" if previous.invalidity_causes else "unknown"
            reason = (
                "native_selected_revocation_witness"
                if previous.invalidity_causes
                else "native_selected_unavailable_cause_unestablished"
            )
        elif current and fate_class == "unestablished":
            state, reason = "unknown", "native_target_" + current.fate.replace("-", "_")
        elif fate_class == "awaiting":
            state, reason = "awaiting", "target_execution_not_settled"
        elif key in new_population and key not in old_population and population_complete:
            state, reason = "awaiting", "newly_applicable_or_never_derived_subject"
        elif roots:
            state, reason = (
                "awaiting" if target_observed else "potential",
                "changed_declared_dependency",
            )
        elif previous and previous.fate == "fulfilled" and not target_observed:
            state, reason = "unknown", "target_admission_not_observed"
        else:
            state, reason = "unknown", "insufficient_selected_or_population_evidence"
        causes = tuple(
            cause
            for observation in (previous, current)
            if observation
            for cause in observation.invalidity_causes
        )
        witnesses = tuple(sorted(set(witnesses) | {cause.reference for cause in causes}))
        reason_codes = (
            reason,
            *sorted({cause.kind + "_" + cause.selector_kind + "_revocation" for cause in causes}),
        )
        rows.append(
            ChangeImpactItem(
                member=member,
                state=state,
                reasons=reason_codes,
                changed_roots=roots,
                witnesses=witnesses,
                invalidity_causes=causes,
            )
        )
    return tuple(rows)


def _native_revocation_causes(index, roots, selected_uses):
    """Classify native witnesses whose paths record a root and reached endpoint."""
    causes = {}
    selected = set(selected_uses)
    for row in index.rows("ops.data_support_explanation"):
        if row["root_use_id"] not in selected or row["valid"] or row["revocation_id"] is None:
            continue
        episode = row["node_kind"] in {"episode", "producer"}
        causes[row["revocation_id"], "episode" if episode else row["node_kind"], row["node_id"]] = (
            RevocationCause(
                kind="direct" if episode and row["node_id"] in roots else "upstream",
                reference=row["revocation_id"],
                derivation_id=row["node_id"] if episode else None,
                support_path=tuple(row["support_path"]),
                selector_kind=row["selector_kind"],
                selector=row["selector"],
            )
        )
    return tuple(causes[key] for key in sorted(causes))


def _population_universe(selection, evidence, populations, *, model, scope):
    """Require an authentic complete receipt for each frozen producer context."""
    population = {row.member.key: row.member for row in evidence}
    closed = True
    rows = tuple(populations)
    for relation in selection.get("discovery", ()):
        producer = relation["producer"]
        required = {
            row.member.key: row.member for row in evidence if row.member.operation == producer
        }
        if producer in selection["root_operations"]:
            for root in selection["roots"]:
                member = PopulationMember(
                    operation=producer, subject_definition=model.operation(producer).subject, **root
                )
                required[member.key] = member
        if not required:
            closed = False
        for context in required.values():
            matching = []
            for row in rows:
                fact = row["evidence"]
                owner = fact.get("producer_context")
                if (
                    row["name"] != relation["population"]
                    or owner is None
                    or "selection" in fact
                    or fact.get("member_role") != relation["output_role"]
                ):
                    continue
                if (
                    PopulationMember(
                        operation=owner["operation_id"],
                        subject=owner["subject"],
                        subject_definition=owner["subject_definition"],
                        original_source=owner["original_source"],
                        analyzed_scope=owner["analyzed_scope"],
                    ).key
                    == context.key
                ):
                    matching.append(row)
            if len(matching) != 1 or matching[0]["complete"] is not True:
                closed = False
                continue
            for member in matching[0]["members"]:
                child = PopulationMember(
                    operation=relation["target"],
                    subject=member["subject"],
                    subject_definition=member["subject_definition"],
                    original_source=member["original_source"],
                    analyzed_scope=member["analyzed_scope"],
                )
                if scope and child.key not in population:
                    closed = False
                else:
                    population[child.key] = child
    return population, closed


def _acquire(connection, demand, *, project, scope, read_id, expected_cut, max_bytes):
    """Protected Core/native projection owns visibility, trust and support walking."""
    from contextlib import closing

    from .acquired_selected_relations import LiveSelectedRelations

    with closing(LiveSelectedRelations()) as index:
        continuation = (
            None
            if read_id is None
            else dict(demand_id=demand, read_id=read_id, scope=scope, view="frontier")
        )
        cut, obligations, uses, populations = None, {}, defaultdict(list), {}
        while True:
            page = read_demand_result(
                connection,
                demand,
                project_id=project,
                scope=scope,
                view="frontier",
                continuation=continuation,
                cut=cut,
                limit=100,
                max_bytes=max_bytes,
            )
            cut = page.cut
            if expected_cut is not None and cut.identity != expected_cut:
                raise ValueError("impact request belongs to another cut/trust assessment")
            for row in page.record["populations"]:
                populations[row["population_id"]] = row
            for row in page.record["obligations"]:
                obligations[row["obligation_id"]] = row
            for row in page.record["uses"]:
                uses[row["obligation_id"]].append(row)
            continuation = page.continuation
            if continuation is None:
                break
        for record in stream_selected_support(connection, page, whole_read=True, facts_only=True):
            index.append_record(record, allow_equal=True)
        from .data_operation_admission import bound_data_operation_model
        from .releases import open_release

        model = bound_data_operation_model(open_release(connection, cut.record["release_id"]))
        read_unknowns = tuple(
            sorted(
                {
                    "selected read has undisclosed protected dependencies at authority "
                    + row["derivation_id"]
                    for row in index.rows("ops.data_authority_leaf")
                }
            )
        )
        evidence = []
        for identity, obligation in obligations.items():
            selected = uses[identity]
            if (
                obligation["subject_definition"]
                != model.operation(obligation["operation_id"]).subject
            ):
                raise ValueError(
                    "impact obligation subject definition differs from checked operation"
                )
            member = PopulationMember(
                operation=obligation["operation_id"],
                subject=obligation["subject"],
                subject_definition=obligation["subject_definition"],
                original_source=obligation["original_source"],
                analyzed_scope=obligation["analyzed_scope"],
            )
            edges, inputs, support, derivations = [], [], set(), set()
            for use in selected:
                episode = use.get("derivation_id")
                if episode is not None:
                    derivations.add(episode)
                    for row in index.rows_for("ops.data_derivation_input", derivation_id=episode):
                        inputs.append(
                            (
                                row["product_id"],
                                row.get("member_id"),
                                row["role"],
                                row["position"],
                                row["multiplicity"],
                            )
                        )
                    selection = use["selection"]
                    if "support" in selection:
                        support.update(
                            row["derivation_id"]
                            for row in selection["support"]
                            if row.get("derivation_id")
                        )
                    else:
                        for row in index.rows_for(
                            "ops.data_derivation_support", derivation_id=episode
                        ):
                            support.add(row["support_derivation_id"])
                for product in use["products"]:
                    edges.append(
                        (
                            product["product_id"],
                            product.get("member_id"),
                            product["role"],
                            product["position"],
                            product["multiplicity"],
                        )
                    )
            evidence.append(
                SelectionEvidence(
                    member=member,
                    fate="cancelled" if page.record["state"] == "cancelled" else obligation["fate"],
                    derivations=tuple(sorted(derivations)),
                    products=tuple(sorted(edges, key=json_bytes)),
                    inputs=tuple(sorted(inputs, key=json_bytes)),
                    support=tuple(sorted(support)),
                    read_unknowns=read_unknowns,
                    invalidity_causes=_native_revocation_causes(
                        index, derivations, tuple(use["use_id"] for use in selected)
                    )
                    if obligation["fate"] == "unavailable"
                    else (),
                )
            )
        population, closed = _population_universe(
            cut.record["selection"], evidence, populations.values(), model=model, scope=scope
        )
        return cut, tuple(evidence), tuple(population.values()), closed


def inspect_change_impact(
    connection, request: ChangeImpactRequest, *, target_prepared, before_model=None
) -> ChangeImpactPage:
    """Same-transaction native reads; no writes beyond existing protected acquisition."""
    from .serving_identity import installed_read_implementation

    with installed_read_implementation(
        ChangeImpactRequest,
        entry="corpus_structure.semantic.change_impact",
        profile="change-impact-1",
        callables=("corpus_structure.semantic.change_impact.classify_change_impact",),
    ) as implementation:
        return _inspect_change_impact(
            connection,
            request,
            target_prepared=target_prepared,
            before_model=before_model,
            implementation=implementation,
        )


def _inspect_change_impact(
    connection, request, *, target_prepared, before_model, implementation
) -> ChangeImpactPage:
    request_identity = sha256(
        json_bytes(
            request.model_dump(
                mode="python",
                exclude={
                    "cursor",
                    "limit",
                    "read_id",
                    "expected_cut",
                    "target_read_id",
                    "expected_target_cut",
                },
            )
        )
    ).hexdigest()
    if request.cursor:
        try:
            token = _Continuation.model_validate(
                json_loads(base64.urlsafe_b64decode(request.cursor))
            ).model_dump()
        except Exception as error:
            raise ValueError("invalid impact continuation") from error
        if token["request_identity"] != request_identity:
            raise ValueError("impact continuation belongs to another comparison request scope")
        for field, pin in (
            ("read_id", "before_read"),
            ("expected_cut", "before_cut"),
            ("target_read_id", "target_read"),
            ("expected_target_cut", "target_cut"),
        ):
            explicit = getattr(request, field)
            if explicit is not None and explicit != token[pin]:
                raise ValueError("impact continuation conflicts with explicit " + field)
        request = request.model_copy(
            update={
                "read_id": token["before_read"],
                "expected_cut": token["before_cut"],
                "target_read_id": token["target_read"],
                "expected_target_cut": token["target_cut"],
            }
        )
    else:
        token = None
    before_cut, before, before_population, before_closed = _acquire(
        connection,
        request.before_demand_id,
        project=request.project_id,
        scope=request.scope,
        read_id=request.read_id,
        expected_cut=request.expected_cut,
        max_bytes=request.max_bytes,
    )
    from .data_operation_admission import bound_data_operation_model
    from .releases import open_release

    acquired_before = bound_data_operation_model(
        open_release(connection, before_cut.record["release_id"])
    )
    if before_model is not None and before_model.content != acquired_before.content:
        raise ValueError("before model differs from the authenticated selected release")
    before_model = acquired_before
    if target_prepared.release_id != request.target_release_id:
        raise ValueError("target model belongs to another release")
    target_model = bound_data_operation_model(target_prepared)
    target_cut, target, target_population, target_closed = None, (), (), False
    if request.target_demand_id is not None:
        target_cut, target, target_population, target_closed = _acquire(
            connection,
            request.target_demand_id,
            project=request.project_id,
            scope=request.scope,
            read_id=request.target_read_id,
            expected_cut=request.expected_target_cut,
            max_bytes=request.max_bytes,
        )
        if target_cut.record["release_id"] != request.target_release_id:
            raise ValueError("target selection belongs to another release")
    fingerprint = dict(
        implementation=implementation,
        request=request.model_dump(
            mode="python",
            exclude={
                "cursor",
                "limit",
                "read_id",
                "expected_cut",
                "target_read_id",
                "expected_target_cut",
            },
        ),
        before_model=sha256(before_model.content).hexdigest(),
        target_model=sha256(target_model.content).hexdigest(),
        before_cut=before_cut.identity,
        target_cut=None if target_cut is None else target_cut.identity,
    )
    comparison = "change-impact:" + sha256(json_bytes(fingerprint)).hexdigest()
    if token is not None and token["comparison"] != comparison:
        raise ValueError("impact continuation belongs to another comparison/context")
    population_complete = before_closed and target_closed
    unknowns = []
    unknowns.extend(
        sorted({reason for observed in (*before, *target) for reason in observed.read_unknowns})
    )
    if not population_complete:
        unknowns.append(
            "native before/target requested and discovery populations are not both closed"
        )
    for supplied, native, side in (
        (request.before_population, before_population, "before"),
        (request.target_population, target_population, "target"),
    ):
        if supplied and {row.key for row in supplied} != {row.key for row in native}:
            unknowns.append(
                side + " supplied population differs from authenticated native requested universe"
            )
    from .selected_query_cache import SELECTED_QUERY_CACHE, bounded_rows, served_key

    key = served_key(
        connection,
        "change-impact",
        implementation=implementation,
        selection=fingerprint,
        basis=[before_cut.identity, None if target_cut is None else target_cut.identity],
    )
    with SELECTED_QUERY_CACHE.loading(key) as entry:
        if entry is None:
            rows = classify_change_impact(
                before_model,
                target_model,
                before=before,
                target=target,
                before_population=before_population,
                target_population=target_population,
                population_complete=population_complete,
                target_observed=target_cut is not None,
            )
            entry, remaining = bounded_rows((row.model_dump(mode="python") for row in rows), {})
            if entry is not None:
                SELECTED_QUERY_CACHE.put(key, entry)
            elif remaining is not None:
                remaining.close()
        else:
            rows = tuple(ChangeImpactItem.model_validate(row) for row in entry.rows())
    offset = 0 if token is None else token["offset"]
    if type(offset) is not int or offset < 0 or offset > len(rows):
        raise ValueError("invalid impact continuation position")
    end = min(offset + request.limit, len(rows))
    while (
        end > offset
        and len(json_bytes([row.model_dump(mode="python") for row in rows[offset:end]]))
        > request.max_bytes - 512
    ):
        end -= 1
    if end == offset and end < len(rows):
        raise ValueError("one complete impact item exceeds max_bytes")
    next_token = (
        None
        if end == len(rows)
        else base64.urlsafe_b64encode(
            json_bytes(
                dict(
                    comparison=comparison,
                    request_identity=request_identity,
                    offset=end,
                    before_read=before_cut.record["read_id"],
                    before_cut=before_cut.identity,
                    target_read=None if target_cut is None else target_cut.record["read_id"],
                    target_cut=None if target_cut is None else target_cut.identity,
                )
            )
        ).decode()
    )
    result = ChangeImpactPage(
        comparison_id=comparison,
        before_cut=before_cut.record,
        target_cut=None if target_cut is None else target_cut.record,
        target_release_id=request.target_release_id,
        items=rows[offset:end],
        complete=end == len(rows),
        population_complete=population_complete,
        unknowns=tuple(unknowns),
        continuation=next_token,
    )
    if len(json_bytes(result.model_dump(mode="python"))) > request.max_bytes:
        raise ValueError("complete impact page exceeds max_bytes")
    return result


def resume_changed_demand(engine, demand_id, *, project_id, source_root, **execution_options):
    """Explicit execution retains native coalescing, substitution and equal-value cutoff."""
    from .data_operation_service import execute_data_demand

    return execute_data_demand(
        engine, demand_id, project_id=project_id, source_root=source_root, **execution_options
    )
