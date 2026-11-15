"""Subject-relative change explanations over authenticated selected DDO custody.

Source edits never execute a demand. A proposed model supplies potential relevance;
only a separately admitted target selection establishes current substitution. The
native read owner retains permission/trust authority and complete support closure.
"""

from __future__ import annotations

import base64
from collections import defaultdict
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .data_operation_json import json_bytes, json_loads
from .data_operation_model import EffectiveDataOperationModel, json_context_meaning
from .demand_results import read_demand_result, stream_selected_support


class PopulationMember(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    operation: str
    subject: str
    original_source: str
    analyzed_scope: dict[str, Any] = Field(default_factory=dict)

    @property
    def key(self) -> bytes:
        return json_bytes(
            dict(
                operation=self.operation,
                subject=self.subject,
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
    fate: str
    derivations: tuple[str, ...] = ()
    products: tuple[tuple[str, str | None, str, int, int], ...] = ()
    inputs: tuple[tuple[str, str | None, str, int, int], ...] = ()
    support: tuple[str, ...] = ()
    invalidity_causes: tuple[RevocationCause, ...] = ()


def changed_operations(before: EffectiveDataOperationModel, target: EffectiveDataOperationModel):
    """Existing admitted identity projections, with both declared dependency sides."""
    old = {op.semantic_id: op for op in before.operations}
    new = {op.semantic_id: op for op in target.operations}
    roots = set(old) ^ set(new)
    old_ids = {(row.owner, row.domain): row.key for row in before.identities}
    new_ids = {(row.owner, row.domain): row.key for row in target.identities}
    for name in old.keys() & new.keys():
        if (
            old[name].recipe != new[name].recipe
            or old[name].eligibility != new[name].eligibility
            or old_ids.get((name, "recipe")) != new_ids.get((name, "recipe"))
        ):
            roots.add(name)
    from .data_operation_identity import SemanticGraph

    names = set(old) | set(new)
    records = {
        "nodes": [dict(id=name, category="operation", payload={}) for name in sorted(names)],
        "edges": [],
    }
    for side, model in (("before", before), ("target", target)):
        for operation in model.operations:
            for relation, dependencies in (
                ("required", operation.dependencies),
                ("possible", operation.potential_dependencies),
            ):
                for position, dependency in enumerate(dependencies):
                    records["edges"].append(
                        dict(
                            source=operation.semantic_id,
                            target=dependency,
                            relation=side + "_change_" + relation,
                            position=position,
                        )
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
        if member.operation not in target_operations:
            state, reason = "inapplicable", "operation_removed_from_target"
        elif population_complete and key in old_population and key not in new_population:
            state, reason = "inapplicable", "absent_under_complete_target_population"
        elif current and current.fate == "cancelled":
            state, reason = "inapplicable", "target_demand_cancelled"
        elif current and current.fate == "unavailable":
            state = "revoked" if current.invalidity_causes else "unknown"
            reason = (
                "native_target_revocation_witness"
                if current.invalidity_causes
                else "native_target_unavailable_cause_unestablished"
            )
        elif current and current.fate == "fulfilled":
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
        elif key in new_population and key not in old_population and population_complete:
            state, reason = "awaiting", "newly_applicable_or_never_derived_subject"
        elif current and current.fate in {
            "waiting",
            "attached",
            "awaiting-external",
            "awaiting-population",
            "unavailable",
        }:
            state, reason = "awaiting", "target_execution_not_settled"
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


def _revocation_causes(index, roots, selected_uses=()):
    """Attribute only native-exported selector/epoch witnesses to reached support."""
    episodes = index.mapping("ops.data_derivation", ("id",))
    requests = index.mapping("ops.data_request", ("id",))
    admissions = index.mapping("ops.original_source_admission", ("id",))
    revocations = tuple(index.rows("ops.data_revocation"))
    uses = index.mapping("ops.demand_use", ("id",))
    populations = index.mapping("ops.data_population", ("id",))
    pending: list[tuple[str, str, tuple[str, ...]]] = [("use", use, ()) for use in selected_uses]
    if not pending:
        pending = [("episode", root, ()) for root in roots]
    visited, causes = set(), {}

    def reference_node(reference) -> tuple[str, str]:
        if reference.get("kind") in {"original-source", "authored"}:
            return "original", reference["admission_id"]
        if reference.get("admission_use_id"):
            return "use", reference["admission_use_id"]
        return "episode", reference["derivation_id"]

    while pending:
        kind, identity, path = pending.pop()
        path = (*path, kind + ":" + identity)
        if (kind, identity) in visited:
            continue
        visited.add((kind, identity))
        if kind == "use":
            use = uses.get(identity)
            if use is None:
                continue
            # The exact use selects replacement support. Its producer episode is
            # inspected directly, without following the episode's obsolete inputs.
            if use.get("derivation_id"):
                pending.append(("selected-episode", use["derivation_id"], path))
            selection = use["selection"]
            pending.extend(
                (*reference_node(reference), path) for reference in selection.get("support", ())
            )
            pending.extend(
                ("population", reference["population_id"], path)
                for reference in selection.get("populations", ())
            )
            continue
        if kind == "population":
            population = populations.get(identity)
            if population is not None:
                evidence = population["evidence"]
                if evidence.get("admission_use_id"):
                    pending.append(("use", evidence["admission_use_id"], path))
                elif evidence.get("derivation_id"):
                    pending.append(("episode", evidence["derivation_id"], path))
                parent = evidence.get("selection", {}).get("parent_population_id")
                if parent:
                    pending.append(("population", parent, path))
            continue
        episode_node = kind in {"episode", "selected-episode"}
        row = episodes.get(identity) if episode_node else admissions.get(identity)
        if row is None:
            continue
        if episode_node:
            request = requests[row["request_id"]]
            project, source = request["project_id"], request["original_source"]
            products = {
                r["product_id"]
                for r in index.rows_for("ops.data_derivation_output", derivation_id=identity)
            }
            selectors = {
                ("derivation", identity),
                ("recipe", row["recipe"]),
                ("runtime", row["runtime_id"]),
            } | {("product", product) for product in products}
            if kind == "episode":
                for support in index.rows_for(
                    "ops.data_derivation_support", derivation_id=identity
                ):
                    node: tuple[str, str] = (
                        ("use", support["admission_use_id"])
                        if support.get("admission_use_id")
                        else ("episode", support["support_derivation_id"])
                    )
                    pending.append((*node, path))
                pending.extend(
                    ("original", r["admission_id"], path)
                    for r in index.rows_for(
                        "ops.data_derivation_original_support", derivation_id=identity
                    )
                )
        else:
            project, source = row["project_id"], row["original_source"]
            selectors = {
                ("original-admission", identity),
                ("original-source", row["source_reference"]),
                ("product", row["product_id"]),
            }
        # Scope is the existing native framed JSON project/source key.
        scope = "source:" + sha256(json_bytes([project, source])).hexdigest()
        for revoked in revocations:
            if (
                revoked["scope"] == scope
                and (revoked["selector_kind"], revoked["selector"]) in selectors
            ):
                causes[revoked["id"], identity] = RevocationCause(
                    kind="direct" if episode_node and identity in roots else "upstream",
                    reference=revoked["id"],
                    derivation_id=identity if episode_node else None,
                    support_path=path,
                    selector_kind=revoked["selector_kind"],
                    selector=revoked["selector"],
                )
    return tuple(causes[key] for key in sorted(causes))


def _population_universe(selection, evidence, populations, *, scope):
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
                member = PopulationMember(operation=producer, **root)
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
    from pathlib import Path
    from tempfile import TemporaryDirectory

    from .data_operation_read_index import SelectedRecordIndex

    with TemporaryDirectory(prefix="change-impact-") as scratch:
        index = SelectedRecordIndex(Path(scratch) / "selected.sqlite")
        try:
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
                for record in stream_selected_support(connection, page):
                    index.append(json_bytes(record), allow_equal=True)
                continuation = page.continuation
                if continuation is None:
                    break
            evidence = []
            for identity, obligation in obligations.items():
                selected = uses[identity]
                member = PopulationMember(
                    operation=obligation["operation_id"],
                    subject=obligation["subject"],
                    original_source=obligation["original_source"],
                    analyzed_scope=obligation["analyzed_scope"],
                )
                edges, inputs, support, derivations = [], [], set(), set()
                for use in selected:
                    episode = use.get("derivation_id")
                    if episode is not None:
                        derivations.add(episode)
                        for row in index.rows_for(
                            "ops.data_derivation_input", derivation_id=episode
                        ):
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
                        fate="cancelled"
                        if page.record["state"] == "cancelled"
                        else obligation["fate"],
                        derivations=tuple(sorted(derivations)),
                        products=tuple(sorted(edges, key=json_bytes)),
                        inputs=tuple(sorted(inputs, key=json_bytes)),
                        support=tuple(sorted(support)),
                        invalidity_causes=_revocation_causes(
                            index, derivations, tuple(use["use_id"] for use in selected)
                        )
                        if obligation["fate"] == "unavailable"
                        else (),
                    )
                )
            population, closed = _population_universe(
                cut.record["selection"], evidence, populations.values(), scope=scope
            )
            return cut, tuple(evidence), tuple(population.values()), closed
        finally:
            index.close()


def inspect_change_impact(
    connection, request: ChangeImpactRequest, *, target_prepared, before_model=None
) -> ChangeImpactPage:
    """Same-transaction native reads; no writes beyond existing protected acquisition."""
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
