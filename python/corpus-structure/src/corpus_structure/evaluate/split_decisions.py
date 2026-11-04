"""Frozen inputs for the protected split-decision operation.

Preparation has no database effects. Canonical bytes retain the actual population and
prior assignments; a digest alone is never substituted for these replay inputs.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.refusals import SemanticOperationRefusal, SemanticReason

from .split import Assignment, SplitConfig, SplitDocument, SplitError, assign


@dataclass(frozen=True)
class PreparedSplitDecision:
    intent: bytes

    @property
    def decision_id(self) -> str:
        return "split-decision:" + sha256(self.intent).hexdigest()


def prepare_split_decision(
    project_id: str,
    release_id: str,
    documents: Sequence[SplitDocument],
    policy: SplitConfig,
    previous: Mapping[int, Assignment],
    seed: int | None = None,
) -> PreparedSplitDecision:
    """Freeze effective intent without consulting mutable project defaults.

    Ordered policy entries preserve first-matching reason semantics. The native consumer
    must independently validate the recorded basis and output before publishing effects.
    """
    if not project_id or not release_id:
        raise SplitError("split decision requires a project and producing release")
    ids = {document.id for document in documents}
    if len(ids) != len(documents) or not set(previous) <= ids:
        raise SplitError("split decision requires unique documents and in-population prior rows")
    for document in documents:
        if document.chapter is not None and not isinstance(document.chapter, str):
            raise SemanticOperationRefusal(
                SemanticReason(
                    "unsupported_interpretation",
                    "reference_split",
                    release_id,
                    expected="string or null chapter metadata",
                    actual=type(document.chapter).__name__,
                    detail=f"document {document.id} has unsupported split chapter metadata",
                )
            )
    population = [
        {"document_id": d.id, "source_uri": d.source_uri, "chapter": d.chapter}
        for d in sorted(documents, key=lambda d: d.id)
    ]
    prior = [
        {"document_id": key, "split": value.split.value, "reason": value.reason, "seed": value.seed}
        for key, value in sorted(previous.items())
    ]
    outputs = [
        {
            "document_id": row.document_id,
            "split": row.split.value,
            "reason": row.reason,
            "seed": row.seed,
        }
        for row in assign(documents, policy, previous, seed)
    ]
    return PreparedSplitDecision(
        canonical_bytes(
            {
                "version": "split-decision-1",
                "algorithm": "chapter-uri-hash-1",
                "project_id": project_id,
                "release_id": release_id,
                "seed": policy.seed if seed is None else seed,
                "seed_origin": "policy" if seed is None else "override",
                "policy": {
                    "seed": policy.seed,
                    "forced_dev": list(policy.forced_dev.items()),
                    "reserved": list(policy.reserved.items()),
                },
                "population": population,
                "previous": prior,
                "assignments": outputs,
            }
        )
    )
