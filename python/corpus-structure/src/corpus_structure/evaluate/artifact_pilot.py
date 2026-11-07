"""Evaluate a bounded artifact proposal product against independent pair judgments."""

from __future__ import annotations

from collections import Counter
from typing import Literal

from pydantic import Field
from rapidfuzz.fuzz import ratio
from splink.internals.splink_dataframe import SplinkDataFrame

from corpus_structure.semantic.artifact_identity import (
    ARTIFACT_ROUTES,
    ArtifactIdentityProduct,
    ArtifactPairKey,
    artifact_linker,
    artifact_score_status,
    native_alias_candidates,
    normalized_code,
    predict_artifact_pairs,
)

PREDICTION_THRESHOLDS = (0.25, 0.5, 0.75)
CLERICAL_THRESHOLD = 0.5
WEIGHT_ROUNDING = 0.1


class ArtifactPairJudgment(ArtifactPairKey):
    case_id: str = Field(min_length=1)
    judgment: Literal["supported", "unsupported", "ambiguous", "unassessed"]
    question: Literal["reference_reachability", "same_lineage"] = "reference_reachability"


def _code_state(code: str | None) -> str:
    if code is None:
        return "unknown"
    return "malformed" if normalized_code(code) is None else "observed"


def _prior_with_odds_scale(prior: float, scale: float) -> float:
    return (scale * prior) / ((1 - prior) + scale * prior)


def evaluate_artifact_pilot(
    product: ArtifactIdentityProduct,
    judgments: tuple[ArtifactPairJudgment, ...],
    *,
    exclusions: tuple[tuple[str, str], ...] = (),
    title_threshold: float = 70.0,
) -> dict:
    """Retain nomination coverage separately from common-support score diagnostics."""
    by_id = {record.contribution_id: record for record in product.records}
    pairs = {(pair.left, pair.right): pair for pair in product.pairs}
    exclusions_ = {tuple(sorted(pair)) for pair in exclusions}
    anchors = frozenset(product.known_anchor_ids)
    seen_cases = set()
    seen_pairs = set()
    case_rows = []
    common = set()
    for case in judgments:
        key = (case.left, case.right)
        if (
            case.case_id in seen_cases
            or key in seen_pairs
            or case.left >= case.right
            or not set(key) <= by_id.keys()
        ):
            raise ValueError("artifact evaluation requires unique exact cohort pairs and case IDs")
        seen_cases.add(case.case_id)
        seen_pairs.add(key)
        a, b = (by_id[endpoint] for endpoint in key)
        left, right = a.artifact, b.artifact
        eligibility = artifact_score_status(
            a, b, excluded=key in exclusions_ or set(key) <= anchors
        )
        known = case.judgment in ("supported", "unsupported")
        if eligibility == "eligible" and known and case.question == "same_lineage":
            common.add(key)
        code = normalized_code(left.controlled_code)
        exact = code is not None and code == normalized_code(right.controlled_code)
        lexical = ratio(left.title, right.title) / 100 if left.title and right.title else None
        candidate = pairs.get(key)
        case_rows.append(
            {
                **case.model_dump(mode="json"),
                "eligible": eligibility == "eligible",
                "score_applicability": eligibility,
                "nomination_routes": list(candidate.candidate_routes) if candidate else [],
                "union_model_probability": candidate.model_probability if candidate else None,
                "exact_key_control": exact,
                "lexical_score": lexical,
                "lexical_control": lexical is not None and lexical * 100 >= title_threshold,
                "code_state": [_code_state(a.controlled_code) for a in (left, right)],
                "alias_state": [a.alias_state for a in (left, right)],
            }
        )

    alias, alias_counts = native_alias_candidates(product.records, count_rules=True)
    retained_alias = {(p.left, p.right) for p in product.native_alias_pairs}
    if set(alias) != retained_alias:
        raise ValueError("provider alias blocking differs from retained actual nomination ledger")
    candidates = {
        route: {key for key, p in pairs.items() if route in p.candidate_routes}
        for route in ARTIFACT_ROUTES
    }
    eligible = {key for key, p in pairs.items() if p.score_status == "scored"}
    previous: set[tuple[str, str]] = set()
    route_counts = []
    for route, nominated in candidates.items():
        present = nominated & eligible
        route_counts.append(
            {
                "route": route,
                "nominated": len(nominated),
                "excluded": sum(pairs[key].scope_state == "excluded" for key in nominated),
                "eligible": len(present),
                "marginal_eligible": len(present - previous),
                "cumulative_eligible": len(previous | present),
                "labeled_eligible": len(present & common),
            }
        )
        previous |= present
    if previous != eligible:
        raise ValueError("artifact evaluation encountered a candidate with an undeclared route")

    labeled_rows = [
        {
            "unique_id_l": case["left"],
            "unique_id_r": case["right"],
            "source_dataset_l": "artifacts",
            "source_dataset_r": "artifacts",
            "clerical_match_score": int(case["judgment"] == "supported"),
        }
        for case in case_rows
        if (case["left"], case["right"]) in common
    ]
    scored_keys = tuple(sorted(eligible | common))
    models = {}
    if scored_keys:
        for name, odds_scale in (
            ("primary", 1.0),
            ("half_prior_odds", 0.5),
            ("double_prior_odds", 2.0),
        ):
            policy = product.policy.model_copy(
                update={"prior": _prior_with_odds_scale(product.policy.prior, odds_scale)}
            )
            with artifact_linker(product.records, policy) as linker:
                scored = predict_artifact_pairs(linker, scored_keys)
                if name == "primary":
                    for key in eligible:
                        original = pairs[key].model_probability
                        if (
                            original is None
                            or abs(scored[key]["match_probability"] - original) > 1e-10
                        ):
                            raise ValueError(
                                "primary scoring differs from retained candidate model"
                            )
                if labeled_rows:
                    labels = linker.table_management.register_labels_table(
                        linker.table_management.register_table(
                            labeled_rows, "owned_artifact_labels"
                        )
                    )
                    accuracy_table = linker.evaluation.accuracy_analysis_from_labels_table(
                        labels,
                        output_type="table",
                        threshold_match_probability=CLERICAL_THRESHOLD,
                        match_weight_round_to_nearest=WEIGHT_ROUNDING,
                    )
                    if not isinstance(accuracy_table, SplinkDataFrame):
                        raise TypeError("Splink did not return its declared accuracy table")
                    accuracy = accuracy_table.as_record_list()
                    prediction_errors = {
                        str(threshold): linker.evaluation.prediction_errors_from_labels_table(
                            labels, threshold_match_probability=threshold
                        ).as_record_list()
                        for threshold in PREDICTION_THRESHOLDS
                    }
                else:
                    accuracy, prediction_errors = [], {}
            models[name] = {
                "policy": policy.model_dump(mode="json"),
                "model_id": policy.identity,
                "scores": [
                    {
                        "left": left,
                        "right": right,
                        "provider_probability": row["match_probability"],
                        "provider_weight": row["match_weight"],
                        "nominated": (left, right) in eligible,
                        "in_independent_common_support": (left, right) in common,
                    }
                    for (left, right), row in sorted(scored.items())
                ],
                "label_accuracy": accuracy,
                "label_prediction_errors": prediction_errors,
            }

    return {
        "protocol": "artifact-pilot-assessment-1",
        "score_standing": "candidate_relative_private",
        "candidate_counts": route_counts,
        "splink_native_alias_rule_counts": list(alias_counts),
        "candidate_populations": [
            {
                "left": left,
                "right": right,
                "scope_state": pair.scope_state,
                "score_status": pair.score_status,
                "nomination_routes": list(pair.candidate_routes),
                "nomination_dependencies": list(pair.dependencies),
            }
            for (left, right), pair in sorted(pairs.items())
        ],
        "native_alias_provider_outcome": (
            "passed"
            if sum(bool(record.artifact.aliases) for record in product.records) >= 2
            else "not_run"
        ),
        "external_nomination_count": len(product.external_nominations),
        "external_nomination_outcome": "passed" if product.external_nominations else "not_run",
        "external_nomination_unavailable_reason": (
            None
            if product.external_nominations
            else "No authenticated external pair nominations supplied."
        ),
        "alias_state_counts": dict(Counter(r.artifact.alias_state for r in by_id.values())),
        "supported_reachability": {
            question: {
                "judged": sum(
                    c["question"] == question and c["judgment"] == "supported" for c in case_rows
                ),
                "nominated": sum(
                    c["question"] == question
                    and c["judgment"] == "supported"
                    and bool(c["nomination_routes"])
                    for c in case_rows
                ),
            }
            for question in ("reference_reachability", "same_lineage")
        },
        "cases": case_rows,
        "clerical_cutoff": CLERICAL_THRESHOLD,
        "prediction_cutoffs": list(PREDICTION_THRESHOLDS),
        "prediction_error_provider_boundaries": "strict_gt_or_lt",
        "match_weight_rounding": WEIGHT_ROUNDING,
        "models": models,
    }
