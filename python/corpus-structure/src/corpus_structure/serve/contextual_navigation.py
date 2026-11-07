"""Selected, immutable neighborhood delivery without reopening retrieval or embedding work."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue
from sqlalchemy import text

from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.serve.protocol import Positioned, Scope


class NeighborhoodParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: int = Field(strict=True, gt=0)
    target_id: str = Field(min_length=1)


class NeighborhoodAnswer(BaseModel):
    kind: Literal["exploratory_cosine_neighbors"] = "exploratory_cosine_neighbors"
    selected_task_id: int
    origin_task_id: int
    inventory_id: str
    source_selection: str
    profile_id: str | None = None
    status: Literal["completed", "profile_unavailable", "vector_coverage_unavailable"]
    group: dict[str, JsonValue]
    neighbors: tuple[dict[str, JsonValue], ...]
    witnessed_relationships: tuple[dict[str, JsonValue], ...]


class ContextualNeighborhoodQuery:
    name = "contextual_neighborhood"
    version = "contextual-neighborhood-query-1"
    params = NeighborhoodParams
    result = NeighborhoodAnswer

    def scope(self, ctx, p):
        return Scope.run()

    def validate_position(self, position):
        if position is not None and position != "done":
            raise SemanticRefusal("invalid contextual neighborhood continuation")

    def rows(self, ctx, p, after=None):
        self.validate_position(after)
        if after == "done":
            return
        row = ctx.conn.execute(
            text("""
            SELECT ct.origin_task_id, o->'contextual_enrichment' AS report
            FROM ops.cut_task ct JOIN ops.task_result r ON r.task_id=ct.origin_task_id
            CROSS JOIN LATERAL jsonb_array_elements(r.body->'contribution_operations') o
            WHERE ct.cut_id=:cut AND ct.task_id=:task AND r.body->>'method'='retrieve.contextual'
              AND o->'contextual_enrichment' ? 'neighborhood'
              AND octet_length((o->'contextual_enrichment')::text)<=8000000
            """),
            {"cut": ctx.session.completed_cut_id, "task": p.task_id},
        ).one_or_none()
        if row is None:
            raise SemanticRefusal("neighborhood unavailable in the exact selected task")
        report = row.report
        inventory = report["inventories"][0]
        result = report["neighborhood"]
        if result["inventory_id"] != inventory["inventory_id"]:
            raise SemanticRefusal("neighborhood inventory differs from selected producer")
        groups = {group["target_id"]: group for group in inventory["semantic_groups"]}
        group = next(
            (
                group
                for group in groups.values()
                if p.target_id == group["target_id"] or p.target_id in group["member_target_ids"]
            ),
            None,
        )
        if group is None:
            raise SemanticRefusal("target is outside the exact eligible inventory")
        group_id = group["target_id"]
        neighbors = []
        for edge in result["edges"]:
            if edge["left_group"] == group_id:
                neighbors.append((edge["left_rank"], dict(edge, peer=groups[edge["right_group"]])))
            elif edge["right_group"] == group_id:
                neighbors.append((edge["right_rank"], dict(edge, peer=groups[edge["left_group"]])))
        witnesses = tuple(
            {
                "decision_id": decision["decision_id"],
                "occurrence_id": decision["occurrence_id"],
                "relationship": relationship,
            }
            for decision in report["relationship_decisions"]
            for relationship in decision["selected_edges"]
            if relationship["target_id"] == group_id
        )
        yield Positioned(
            NeighborhoodAnswer(
                selected_task_id=p.task_id,
                origin_task_id=row.origin_task_id,
                inventory_id=inventory["inventory_id"],
                source_selection=inventory["source_selection"],
                profile_id=result.get("profile_id"),
                status=result["status"],
                group=group,
                neighbors=tuple(value for _, value in sorted(neighbors, key=lambda item: item[0])),
                witnessed_relationships=witnesses,
            ),
            "done",
        )


def _verify_native_rank_intersection(result, reps, targets, points):
    from collections import defaultdict
    from math import isclose, isfinite

    import numpy as np

    rows = result["directed_ranks"]
    edges = result["edges"]
    if result["status"] != "completed":
        if rows or edges:
            raise ValueError("unavailable neighborhood has ranks or edges")
        return
    k = min(5, max(0, len(reps) - 1))
    expected_order = [(source, rank) for source in sorted(reps) for rank in range(1, k + 1)]
    if [(row["from_id"], row["rank"]) for row in rows] != expected_order:
        raise ValueError("detached directed ranks differ from the eligible representative frame")
    by_pair = {}
    previous = None
    ids = sorted(reps)
    matrix = np.asarray([points[identifier] for identifier in ids], dtype=np.float64)
    if k:
        matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    position = {identifier: i for i, identifier in enumerate(ids)}
    identical = defaultdict(list)
    identity = {identifier: (points[identifier] + np.float32(0)).tobytes() for identifier in ids}
    for identifier in ids:
        identical[identity[identifier]].append(identifier)
    tolerance = 1e-6
    distances = ()
    selected = set()
    exact_distances = {}
    for row in rows:
        source, peer, rank, distance = (row["from_id"], row["to_id"], row["rank"], row["distance"])
        if (
            type(rank) is not int
            or peer not in reps
            or source == peer
            or (source, peer) in by_pair
            or not isfinite(distance)
            or not 0 <= distance <= 2
            or (rank > 1 and previous is not None and previous >= (distance, peer))
        ):
            raise ValueError("detached directed rank differs from native distance and ID order")
        if rank == 1:
            distances = 1 - matrix @ matrix[position[source]]
            selected = set()
            exact_distances = {}
        if not isclose(distance, distances[position[peer]], rel_tol=0, abs_tol=tolerance):
            raise ValueError("detached directed distance differs from its frozen vectors")
        selected.add(peer)
        if rank == k:
            omitted = reps.keys() - selected - {source}
            if any(distances[position[other]] < distance - tolerance for other in omitted):
                raise ValueError("detached directed ranks omit a closer eligible representative")
        identity_key = identity[peer]
        exact_peers = identical[identity_key]
        if exact_distances.setdefault(identity_key, distance) != distance or any(
            other < peer and other != source and other not in selected for other in exact_peers
        ):
            raise ValueError("detached directed rank differs from the exact equal-vector ID order")
        by_pair[source, peer] = row
        previous = (distance, peer)
    expected_edges = [
        {
            "left_id": left,
            "right_id": right,
            "left_group": reps[left],
            "right_group": reps[right],
            "left_digest": targets[left]["representation_digest"],
            "right_digest": targets[right]["representation_digest"],
            "left_rank": row["rank"],
            "right_rank": by_pair[right, left]["rank"],
            "distance": row["distance"],
        }
        for (left, right), row in sorted(by_pair.items())
        if left < right and (right, left) in by_pair
    ]
    if edges != expected_edges:
        raise ValueError("detached mutual edges differ from the exact directed-rank intersection")


def verify_detached_neighborhood(report, *, native_ranks=False):
    """Check the retained projection against the frozen vector frame without a server."""
    from collections import defaultdict
    from math import isclose

    import numpy as np

    result = report["neighborhood"]
    (inventory,) = report["inventories"]
    profiles = report["profiles"]
    profile = profiles[0] if len(profiles) == 1 else None
    if (
        result["policy"]
        != ("mutual-exact-cosine-top5-2" if native_ranks else "mutual-exact-cosine-top5-1")
        or result["inventory_id"] != inventory["inventory_id"]
        or result.get("profile_id") != (profile["profile_id"] if profile else None)
    ):
        raise ValueError("detached neighborhood differs from its frozen scope")
    targets = {target["target_id"]: target for target in inventory["targets"]}
    vectors = defaultdict(list)
    for vector in report["vectors"]:
        if vector["object_id"] in targets and vector["profile_id"] == result.get("profile_id"):
            vectors[vector["object_id"]].append(vector)
    points = {}
    for target_id, target in targets.items():
        (vector,) = vectors[target_id] if len(vectors[target_id]) == 1 else (None,)
        if vector is None or any(
            vector[key] != target[key] for key in ("representation_digest", "source_binding")
        ):
            continue
        point = np.asarray(vector["values"], dtype=np.float32)
        if (
            profile is not None
            and point.shape == (profile["dimension"],)
            and np.isfinite(point).all()
            and abs(float(np.linalg.norm(point)) - 1) <= 1e-5
        ):
            points[target_id] = point
    status = "completed"
    if targets and profile is None:
        status = "profile_unavailable"
    elif points.keys() != targets.keys():
        status = "vector_coverage_unavailable"
    if result["status"] != status:
        raise ValueError("detached neighborhood vector coverage differs")
    groups = inventory["semantic_groups"]
    members = [member for group in groups for member in group["member_target_ids"]]
    if len(members) != len(set(members)) or set(members) != targets.keys():
        raise ValueError("detached neighborhood groups do not cover the exact inventory")
    reps = {min(group["member_target_ids"]): group["target_id"] for group in groups}
    if native_ranks:
        if not isinstance(result.get("directed_ranks"), list):
            raise ValueError("detached neighborhood has no native directed ranks")
        _verify_native_rank_intersection(result, reps, targets, points)
        return
    if status != "completed" or len(reps) <= 1:
        if result["edges"]:
            raise ValueError("detached neighborhood must be empty")
        return
    from sklearn.neighbors import NearestNeighbors

    ids = sorted(reps)
    distances, peers = (
        NearestNeighbors(metric="cosine", algorithm="brute")
        .fit(np.asarray([points[identifier] for identifier in ids], dtype=np.float64))
        .kneighbors(X=None, n_neighbors=len(ids) - 1)
    )
    tolerance = 1e-6
    directed = {}
    for source, ds, indexes in zip(ids, distances, peers, strict=True):
        ordered = sorted(
            (distance, ids[index]) for distance, index in zip(ds, indexes, strict=True)
        )
        values = np.asarray([distance for distance, _ in ordered])
        for distance, peer in ordered:
            # The native float32 cosine kernel can quantize near-collinear peers
            # into a different tie. Check every unambiguous rank and membership.
            low = int(np.searchsorted(values, distance - tolerance, side="left")) + 1
            high = int(np.searchsorted(values, distance + tolerance, side="right"))
            directed[source, peer] = (low, high, distance)
    required = {
        (a, b)
        for (a, b), (_, upper, _) in directed.items()
        if a < b and upper <= 5 and directed[b, a][1] <= 5
    }
    keys = [(edge["left_id"], edge["right_id"]) for edge in result["edges"]]
    if keys != sorted(set(keys)) or not required.issubset(keys):
        raise ValueError("detached mutual pair membership differs")
    assigned_ranks = set()
    for edge, (left, right) in zip(result["edges"], keys, strict=True):
        if left >= right or (left, right) not in directed:
            raise ValueError("detached neighbor lies outside the eligible pair population")
        left_lo, left_hi, distance = directed[left, right]
        right_lo, right_hi, _ = directed[right, left]
        left_rank, right_rank = edge["left_rank"], edge["right_rank"]
        ranks = {(left, left_rank), (right, right_rank)}
        if (
            not left_lo <= left_rank <= min(5, left_hi)
            or not right_lo <= right_rank <= min(5, right_hi)
            or assigned_ranks.intersection(ranks)
            or not isclose(edge["distance"], distance, rel_tol=0, abs_tol=tolerance)
            or (edge["left_group"], edge["right_group"]) != (reps[left], reps[right])
            or (edge["left_digest"], edge["right_digest"])
            != (targets[left]["representation_digest"], targets[right]["representation_digest"])
        ):
            raise ValueError("detached mutual edge differs from its retained rank or evidence")
        assigned_ranks.update(ranks)


class SourceDecisionParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: int = Field(strict=True, gt=0)
    occurrence_id: str = Field(min_length=1)
    target_id: str | None = None


class SourceDecisionAnswer(BaseModel):
    selected_task_id: int
    origin_task_id: int
    occurrence_id: str
    source_capture: Literal["represented", "unrepresented_in_inspected_product"]
    representation: tuple[dict[str, JsonValue], ...]
    eligibility: tuple[dict[str, JsonValue], ...]
    routes: tuple[dict[str, JsonValue], ...]
    decisions: tuple[dict[str, JsonValue], ...]
    membership: tuple[dict[str, JsonValue], ...]
    display: tuple[str, ...]
    inspected_layers: tuple[str, ...]


class SourceDecisionDiagnosisQuery:
    name = "source_decision_diagnosis"
    version = "source-decision-diagnosis-1"
    params = SourceDecisionParams
    result = SourceDecisionAnswer

    def scope(self, ctx, p):
        return Scope.run()

    def validate_position(self, position):
        if position is not None and position != "done":
            raise SemanticRefusal("invalid source diagnosis continuation")

    def rows(self, ctx, p, after=None):
        self.validate_position(after)
        if after == "done":
            return
        captured = capture_source_decision(ctx.conn, p, ctx.session.completed_cut_id)
        yield Positioned(source_decision_from_capture(p, captured), "done")


class SourceDecisionRequest(SourceDecisionParams):
    run_id: int = Field(strict=True, gt=0)
    cut_id: int = Field(strict=True, gt=0)


def capture_source_decision(conn, p, cut_id):
    if cut_id is None:
        raise SemanticRefusal("diagnosis requires a completed cut")
    row = conn.execute(
        text("""
        SELECT ct.origin_task_id, r.body
        FROM ops.cut_task ct JOIN ops.task_result r ON r.task_id=ct.origin_task_id
        WHERE ct.cut_id=:cut AND ct.task_id=:task AND octet_length(r.body::text)<=8000000
        """),
        {"cut": cut_id, "task": p.task_id},
    ).one_or_none()
    if row is None:
        raise SemanticRefusal("diagnosis requires a bounded task in the exact completed cut")
    return source_decision_capture_from_body(p, cut_id, row.origin_task_id, row.body)


def source_decision_capture_from_body(p, cut_id, origin, body):
    occurrence = p.occurrence_id
    contextual = []
    for operation in body.get("contribution_operations") or ():
        if report := operation.get("contextual_enrichment"):
            contextual.append(
                dict(
                    inventories=report["inventories"],
                    candidate_lists=[
                        row
                        for row in report["candidate_lists"]
                        if row["occurrence_id"] == occurrence
                    ],
                    relationship_decisions=[
                        row
                        for row in report["relationship_decisions"]
                        if row["occurrence_id"] == occurrence
                    ],
                )
            )
    represented = [
        dict(
            contribution_id=row["contribution_id"],
            occurrence_id=row.get("occurrence_id"),
            source_view_id=row["pin"]["source_view_id"],
            semantic_type=row["semantic_type"],
            anchors=row.get("anchors", []),
        )
        for row in body.get("contributions") or ()
        if occurrence in (row.get("occurrence_id"), row["contribution_id"])
    ]
    return {
        "cut_id": cut_id,
        "selected_task_id": p.task_id,
        "origin_task_id": origin,
        "structural": body.get("structural_product") or {},
        "contextual": contextual,
        "represented": represented,
    }


def source_decision_from_capture(p, captured):
    return diagnose_source_decision(
        p,
        captured["origin_task_id"],
        captured["structural"],
        captured["contextual"],
        captured["represented"],
    )


def _comparison_sides(comparison, occurrence):
    return tuple(
        side
        for side in ("left", "right")
        if occurrence
        in (
            comparison[f"{side}_id"],
            (comparison.get(f"{side}_reading") or {}).get("contribution_id"),
        )
    )


def diagnose_source_decision(p, origin_task_id, structural, contextual, represented):
    occurrence = p.occurrence_id
    representations = list(represented)
    eligibility, routes, decisions, membership, display = [], [], [], [], []
    layers = ["source_capture", "representation"]
    for report in contextual:
        layers.extend(("eligibility", "nomination", "decision"))
        for candidate in report["candidate_lists"]:
            if candidate["occurrence_id"] != occurrence:
                continue
            eligible = next(
                i for i in report["inventories"] if i["inventory_id"] == candidate["inventory_id"]
            )
            eligibility.append(
                dict(
                    inventory_id=eligible["inventory_id"],
                    eligible_target_count=candidate["eligible_target_count"],
                    requested_target_eligible=any(
                        target["target_id"] == p.target_id for target in eligible["targets"]
                    )
                    if p.target_id is not None
                    else None,
                )
            )
            for channel in candidate["channel_results"]:
                routes.append(
                    dict(
                        channel=channel["channel"],
                        outcome="succeeded" if channel["hits"] else "empty",
                        hits=[
                            hit
                            for hit in channel["hits"]
                            if p.target_id is None or hit["target_id"] == p.target_id
                        ],
                    )
                )
        decisions.extend(
            d for d in report["relationship_decisions"] if d["occurrence_id"] == occurrence
        )
    if comparison := structural.get("comparison"):
        layers.extend(("comparison", "applicability"))
        for side in _comparison_sides(comparison, occurrence):
            representations.append(
                {
                    "side": side,
                    "reading": comparison.get(f"{side}_reading"),
                    "source_passage_id": comparison[f"{side}_id"],
                }
            )
            decisions.append(
                {
                    "kind": "comparison_side",
                    "side": side,
                    "applicability": comparison["applicability"],
                    "reason": comparison["applicability_reason"],
                    "dimensions": comparison["dimensions"],
                }
            )
    if artifact := structural.get("artifact_identity"):
        layers.extend(("eligibility", "nomination", "score"))
        selected_ids = {
            record["contribution_id"]
            for record in artifact["records"]
            if occurrence in (record["contribution_id"], record["occurrence_id"])
        }
        representations.extend(
            {
                key: record[key]
                for key in ("contribution_id", "occurrence_id", "citations", "artifact")
            }
            for record in artifact["records"]
            if record["contribution_id"] in selected_ids
        )
        for pair in artifact["pairs"]:
            endpoints = {pair["left"], pair["right"]}
            if not (endpoints & selected_ids) or (
                p.target_id is not None and p.target_id not in endpoints
            ):
                continue
            eligibility.append(
                {
                    key: pair[key]
                    for key in (
                        "left",
                        "right",
                        "scope_state",
                        "numbering_relation",
                        "revision_relation",
                    )
                }
            )
            routes.append({key: pair[key] for key in ("left", "right", "candidate_routes")})
            decisions.append(dict(kind="artifact_pair_score", **pair))
        decisions.extend(
            dict(
                nomination, kind="directed_artifact_nomination", witness_kind=nomination.get("kind")
            )
            for nomination in artifact["external_nominations"]
            if {nomination["left"], nomination["right"]} & selected_ids
            and (p.target_id is None or p.target_id in {nomination["left"], nomination["right"]})
        )
        decisions.extend(
            dict(kind="artifact_reference_resolution", **resolution)
            for resolution in artifact.get("reference_resolutions", ())
            if resolution["attachment"] in selected_ids
        )
    if dossier := structural.get("dossier"):
        layers.extend(("membership", "display"))
        for member in dossier["members"]:
            binding = member.get("comparison_binding")
            contribution = member.get("contribution_ref") or {}
            if occurrence in (member["member_id"], contribution.get("contribution_id")) or (
                binding is not None
                and binding["side"] in _comparison_sides(binding["comparison"], occurrence)
            ):
                membership.append(member)
        representations.extend(
            {"member_id": member["member_id"], "citation": member["citation"]}
            for member in membership
        )
        display.extend(
            member["member_id"]
            for member in membership
            if member["member_id"] in dossier["representation"]["selected"]
        )
    return SourceDecisionAnswer(
        selected_task_id=p.task_id,
        origin_task_id=origin_task_id,
        occurrence_id=occurrence,
        source_capture="represented" if representations else "unrepresented_in_inspected_product",
        representation=tuple(representations),
        eligibility=tuple(eligibility),
        routes=tuple(routes),
        decisions=tuple(decisions),
        membership=tuple(membership),
        display=tuple(display),
        inspected_layers=tuple(dict.fromkeys(layers)),
    )
