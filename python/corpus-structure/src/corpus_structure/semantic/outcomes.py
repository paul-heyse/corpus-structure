"""Owned translations between distinct source and semantic outcome domains."""
from dataclasses import dataclass
from typing import Literal

SourceCoverageOutcome = Literal["complete", "partial", "unknown", "unsupported", "failed"]
SemanticCoverageOutcome = Literal["complete", "partial", "unanalysed", "failed"]
ScientificOutcome = Literal["accepted", "rejected", "candidate", "ambiguous", "equivalent", "different", "undecided", "unsupported", "warning", "refuted"]
TaskProtocolOutcome = Literal["done", "empty", "failed", "reused", "skipped", "cancelled"]
TransactionOutcome = Literal["applied", "replay", "conflict", "stale_binding", "run_closed", "recompute_required", "infrastructure_failure"]
QueryKnowledgeOutcome = Literal["observed", "absent", "unknown"]
SubmissionDisposition = Literal["held", "completed_accepted", "completed_refused", "refused_context"]

@dataclass(frozen=True)
class CoverageConversion:
    outcome: SemanticCoverageOutcome
    source_outcome: SourceCoverageOutcome
    reason: str | None
    required_capability: str | None

def lower_source_coverage(outcome: str, reason: str | None = None,
                          required_capability: str | None = None) -> CoverageConversion:
    """Preserve source evidence while translating only its declared outcome domain."""
    if outcome not in {"complete", "partial", "unknown", "unsupported", "failed"}:
        raise ValueError(f"unknown source coverage outcome: {outcome!r}")
    from typing import cast
    source = cast(SourceCoverageOutcome, outcome)
    semantic = "unanalysed" if source in {"unknown", "unsupported"} else source
    return CoverageConversion(cast(SemanticCoverageOutcome, semantic), source, reason,
                              required_capability)
