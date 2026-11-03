"""Persisted scientific assessment explanations without mathematical execution imports."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, NonNegativeInt


class ScientificAssessmentEvidence(BaseModel):
    """Versioned persisted explanation for the scientific assessment constructor."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    abi: Literal["scientific-assessment-evidence-1"] = "scientific-assessment-evidence-1"
    policy: Literal[
        "consolidation-evidence-1",
        "reference-evidence-1",
        "consolidation-evidence-2",
        "reference-evidence-2",
    ]
    tier: Literal["canonical", "symbolic", "numeric", "undecided"]
    numeric: Literal["not_run", "inconclusive", "agreement", "counterexample"]
    valid_points: NonNegativeInt
    grammar: str
    mechanism: str
    operands: tuple[str, str] | None
    context: str
    detail: str


def parse_scientific_assessment_reason(reason: str | None) -> ScientificAssessmentEvidence | None:
    if reason is None:
        return None
    try:
        document = json.loads(reason)
    except json.JSONDecodeError:
        if "scientific-assessment-evidence-" in reason:
            raise ValueError("malformed scientific assessment evidence envelope") from None
        return None
    if not isinstance(document, dict) or not str(document.get("abi", "")).startswith(
        "scientific-assessment-evidence-"
    ):
        return None
    return ScientificAssessmentEvidence.model_validate_json(reason)
