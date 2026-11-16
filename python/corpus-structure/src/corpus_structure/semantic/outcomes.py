"""Owned translations between distinct source and semantic outcome domains."""

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


@dataclass(frozen=True)
class CoverageConversion:
    outcome: SemanticCoverageOutcome
    source_outcome: SourceCoverageOutcome
    reason: str | None
    required_capability: str | None


ReadinessOutcome = Literal["source_ready", "awaiting_agent"]
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
    "assessment_finding": get_args(AssessmentFinding),
    "selection": get_args(SelectionOutcome),
    "protocol": get_args(TaskProtocolOutcome),
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
