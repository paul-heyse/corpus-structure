"""Linked review views preserve the distinction between observations and judgments."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from typing import Any


def compose_review_views(
    selection, rows: Iterable[tuple[str, Mapping[str, Any]]]
) -> Iterator[tuple[str, Mapping[str, Any]]]:
    """Stream derived views; only explicitly selected evaluations carry current standing.

    A missing public admission witness says nothing about private assessment. A
    zero-output operation is an execution fact, not evidence of a semantic miss.
    Historical grades remain available without being silently promoted to current
    authority or compared against a different independent case population.
    """
    evaluations = {}
    try:
        for name, payload in rows:
            yield name, payload
            if name == "inventory":
                row = payload["row"]
                population = payload["population"]
                base = {
                    "selection_index": payload["selection_index"],
                    "selected_task_id": row.get("selected_task_id"),
                    "origin_task_id": row.get("origin_task_id"),
                    "source_view_id": row.get("source_view_id"),
                }
                if population == "operation":
                    yield (
                        "capabilities",
                        {
                            **base,
                            "operation_key": row["operation_key"],
                            "operation_version": row.get("operation_version"),
                            "question": row.get("question"),
                            "outcome": row.get("outcome"),
                            "inspected_count": row.get("inspected_count"),
                            "emitted_count": row.get("emitted_count"),
                            "semantic_quality": "not_established_by_execution",
                            "assessment": "see_explicit_selected_assessment_matrix",
                            "complete_record_standing": "separate_contract",
                        },
                    )
                    if row.get("emitted_count") == 0 or row.get("outcome") not in {
                        "succeeded",
                        "success",
                        "produced",
                    }:
                        yield (
                            "gaps",
                            {
                                **base,
                                "operation_key": row["operation_key"],
                                "basis": "observed_operation_outcome",
                                "outcome": row.get("outcome"),
                                "emitted_count": row.get("emitted_count"),
                                "semantic_miss": "not_established",
                                "cause": "not_inferred_from_stage_status",
                            },
                        )
                elif population == "contribution":
                    yield (
                        "assessment_matrix",
                        {
                            **base,
                            "contribution_id": row["contribution_id"],
                            "facet": "independent_assessment_availability",
                            "assessment_state": "see_selected_evaluations_and_public_witnesses",
                            "private_assessment_state": "unknown_on_ordinary_reader",
                        },
                    )
                elif population == "assessment":
                    yield (
                        "assessment_matrix",
                        {
                            **base,
                            "contribution_id": row["contribution_id"],
                            "facet": "published_admission_witness",
                            "assessment_state": row["outcome"],
                            "assessment_scope": row.get("scope"),
                            "witnesses": row.get("witnesses", []),
                            "private_assessment_state": "unknown_on_ordinary_reader",
                        },
                    )
            elif name == "structural_products":
                report = payload["report"]
                yield (
                    "capabilities",
                    {
                        "product_id": payload["product_id"],
                        "operation": report["kind"],
                        "standing": report["standing"],
                        "scope": report["inputs"]["scope"],
                        "coverage_limits": report["inputs"]["coverage_limits"],
                        "semantic_quality": "requires_independent_group_assessment",
                        "source_population": "declared_original_source_refs_only",
                    },
                )
                yield (
                    "assessment_matrix",
                    {
                        "product_id": payload["product_id"],
                        "facet": "group_assessment_availability",
                        "assessment_state": "see_explicit_selected_group_assessment",
                        "public_eligibility": "not_established_by_retention",
                    },
                )
            elif name == "assessment_history" and payload.get("kind") == "evaluation":
                value = payload["value"]
                evaluation_id = value["id"]
                evaluations[evaluation_id] = value
                result = value["result"]
                for unit in result.get("units", []):
                    for case in unit.get("cases", []):
                        row = {
                            "evaluation_id": evaluation_id,
                            "selected_for_current_assessment": (
                                evaluation_id in selection.selected_evaluation_ids
                            ),
                            "project_id": payload["project_id"],
                            "set_id": payload["set_id"],
                            "run_id": value["run_id"],
                            "unit_id": unit["unit_id"],
                            "source_view_id": unit.get("source_view_id"),
                            "direction": unit["direction"],
                            "frame_digest": result["frame_digest"],
                            "reference_snapshot": value["reference_snapshot"],
                            **case,
                        }
                        yield "assessment_matrix", row
                        if case["judgment"] != "supported":
                            yield (
                                "gaps",
                                {
                                    **row,
                                    "basis": "independent_case_evaluation",
                                    "cause": "not_inferred_from_error_category",
                                },
                            )
        required = set(selection.selected_evaluation_ids)
        for comparison in selection.comparisons:
            required.update((comparison.baseline_evaluation_id, comparison.revised_evaluation_id))
        if not required <= evaluations.keys():
            raise ValueError(
                "selected assessment evaluation is absent from captured authorized history"
            )
        for comparison in selection.comparisons:
            from corpus_structure.evaluate.operation_assessment import compare_assessments
            from corpus_structure.evaluate.semantic import ReferenceError

            baseline = evaluations[comparison.baseline_evaluation_id]
            revised = evaluations[comparison.revised_evaluation_id]
            identity = {
                "baseline_evaluation_id": baseline["id"],
                "revised_evaluation_id": revised["id"],
            }
            try:
                if baseline["project_id"] != revised["project_id"]:
                    raise ReferenceError("comparison requires one original project")
                changes = compare_assessments(baseline["result"], revised["result"])
            except ReferenceError as error:
                yield "changes", {**identity, "outcome": "incomparable", "reason": str(error)}
            else:
                yield "changes", {**identity, "outcome": "comparable", **changes}
    finally:
        close = getattr(rows, "close", None)
        if close is not None:
            close()
