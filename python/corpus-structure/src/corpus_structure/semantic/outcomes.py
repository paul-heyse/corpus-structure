"""Owned translations between distinct source and semantic outcome domains."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal, cast, get_args

SourceCoverageOutcome = Literal["complete", "partial", "unknown", "unsupported", "failed"]
SemanticCoverageOutcome = Literal["complete", "partial", "unanalysed", "failed"]
ScientificComparison = Literal["equivalent", "different", "undecided"]
ScientificOutcome = Literal[
    "accepted",
    "rejected",
    "candidate",
    "ambiguous",
    "equivalent",
    "different",
    "undecided",
    "unsupported",
    "warning",
    "refuted",
]
TaskProtocolOutcome = Literal["done", "empty", "failed", "reused", "skipped", "cancelled"]
TransactionOutcome = Literal[
    "applied",
    "replay",
    "conflict",
    "stale_binding",
    "run_closed",
    "recompute_required",
    "infrastructure_failure",
]
QueryKnowledgeOutcome = Literal["observed", "absent", "unknown"]
SubmissionDisposition = Literal[
    "held", "completed_accepted", "completed_refused", "refused_context"
]


@dataclass(frozen=True)
class CoverageConversion:
    outcome: SemanticCoverageOutcome
    source_outcome: SourceCoverageOutcome
    reason: str | None
    required_capability: str | None


ReadinessOutcome = Literal["source_ready", "awaiting_agent"]
HoldOutcome = Literal["held", "proceed"]
AssessmentFinding = Literal["warning", "refuted"]
SelectionOutcome = Literal["accepted", "rejected", "candidate", "ambiguous"]
ReadOutcome = Literal["source_ready", "missing", "invalid", "unsupported"]


ContinuationOutcome = Literal[
    "continued",
    "invalid_token",
    "wrong_query",
    "wrong_parameters",
    "wrong_release",
    "wrong_realization",
    "wrong_projection",
    "wrong_profile",
    "stale_revision",
    "stale_version",
    "unavailable_result",
]


CODE_OUTCOME_DOMAINS = {
    "continuation": get_args(ContinuationOutcome),
    "read": get_args(ReadOutcome),
    "readiness": get_args(ReadinessOutcome),
    "hold_decision": get_args(HoldOutcome),
    "assessment_finding": get_args(AssessmentFinding),
    "selection": get_args(SelectionOutcome),
    "protocol": get_args(TaskProtocolOutcome),
    "submission": get_args(SubmissionDisposition),
    "source_coverage": get_args(SourceCoverageOutcome),
    "semantic_coverage": get_args(SemanticCoverageOutcome),
    "scientific": get_args(ScientificOutcome),
    "scientific_comparison": get_args(ScientificComparison),
    "transaction": get_args(TransactionOutcome),
    "query_knowledge": get_args(QueryKnowledgeOutcome),
}
_BASE_TRANSLATIONS = MappingProxyType(
    {
        "complete": "complete",
        "partial": "partial",
        "failed": "failed",
        "unknown": "unanalysed",
        "unsupported": "unanalysed",
    }
)


@dataclass(frozen=True)
class PreparedCoverageLowerer:
    translations: Mapping[str, str]

    @classmethod
    def from_release(cls, prepared) -> PreparedCoverageLowerer:
        if prepared.execution_model_id is None:
            raise ValueError("coverage translation requires a composed execution binding")
        rows = [r for r in prepared.registry_rows if r.kind == "execution_model"]
        if len(rows) != 1 or rows[0].name != prepared.execution_model_id:
            raise ValueError("composed coverage requires its exact execution products")
        product = json.loads(rows[0].body)
        if product["model_id"] != prepared.execution_model_id:
            raise ValueError("coverage execution identity differs")
        translations = {}
        for rule in product["outcome_translations"]:
            if (rule["source_domain"], rule["target_domain"]) != (
                "source_coverage",
                "semantic_coverage",
            ):
                continue
            if rule["source"] in translations:
                raise ValueError("duplicate coverage translation")
            if rule["target"] not in get_args(SemanticCoverageOutcome):
                raise ValueError("unsupported semantic coverage target")
            translations[rule["source"]] = rule["target"]
        if set(translations) != set(get_args(SourceCoverageOutcome)):
            raise ValueError("coverage translation does not cover the source domain")
        return cls(MappingProxyType(translations))

    def lower(
        self, outcome: str, reason: str | None = None, required_capability: str | None = None
    ) -> CoverageConversion:
        if outcome not in self.translations:
            raise ValueError(f"unknown source coverage outcome: {outcome!r}")
        return CoverageConversion(
            cast(SemanticCoverageOutcome, self.translations[outcome]),
            cast(SourceCoverageOutcome, outcome),
            reason,
            required_capability,
        )


_BASE_LOWERER = PreparedCoverageLowerer(_BASE_TRANSLATIONS)


def lower_source_coverage(
    outcome: str, reason: str | None = None, required_capability: str | None = None
) -> CoverageConversion:
    """Internal pure-value translation; execution consumers bind their release product."""
    return _BASE_LOWERER.lower(outcome, reason, required_capability)
