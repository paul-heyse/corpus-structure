"""Narrow independently adjudicated local semantic claims.

The native owner consumes the existing operation-reference grade and immutable C
case, returning only exact selected public candidate rows. Ordinary producers never
receive authored cases or held-out labels. Atomic publication repeats the same native
applicability checks; Python transports the resulting narrow immutable rows.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .identity import canonical_bytes

POLICY_ID = "independent-contextual-denotation-1"
FACET = "denotation"
RUBRIC = "contextual-denotation-1"
CONTEXT_POLICY = "declared-native-source-and-curated-targets-1"
QUESTION = "contextual denotation selection for supplied occurrence"


@dataclass(frozen=True)
class LocalSemanticAssertionRow:
    assertion_id: str
    claim_id: str
    selected_task_id: int
    origin_task_id: int
    cut_id: int
    contribution_id: str
    operation_key: str
    operation_version: str
    operation_question: str
    policy_id: str
    policy_version: str
    source: str
    occurrence_id: str
    evaluation_id: int
    evaluation_digest: str
    unit_id: int
    pass_id: int
    frame_id: int
    case_id: str
    facet: str
    rubric_version: str
    context_policy: str
    statement_json: str
    anchors_json: str


def semantic_assertion_identity(values: Mapping[str, Any]) -> str:
    return "local-semantic-assertion:" + sha256(canonical_bytes(values)).hexdigest()


def load_semantic_grade_evidence(
    conn, job: Mapping[str, Any], cut_id: int
) -> tuple[Mapping[str, Any], ...]:
    import json

    from sqlalchemy import text

    dependencies = json.loads(job["dependencies"]) if job.get("dependencies") else {}
    if not dependencies.get("local_semantic_admission"):
        return ()
    rows = conn.execute(
        text("SELECT data.local_semantic_publication_candidates(:project,:release,:run,:cut)"),
        dict(project=job["project_id"], release=job["release_id"], run=job["id"], cut=cut_id),
    ).scalar_one()
    return tuple(rows)


def project_semantic_assertions(
    prepared, evidence: Sequence[Mapping[str, Any]]
) -> tuple[LocalSemanticAssertionRow, ...]:
    """Adapt the native-owned narrow row preparation without exposing reference labels."""
    if not evidence:
        return ()
    if "LocalSemanticPublicationPolicy" not in prepared.index.definitions:
        raise ValueError("release does not support independently judged local publication")
    prepared.validate_python(
        "LocalSemanticPublicationPolicy",
        dict(
            policy_id=POLICY_ID,
            policy_version="1",
            facet=FACET,
            rubric_version=RUBRIC,
            context_policy=CONTEXT_POLICY,
        ),
    )
    return tuple(LocalSemanticAssertionRow(**row) for row in evidence)


def semantic_assertion_facets(
    values: Mapping[str, Any], *, support: bool = False
) -> dict[str, Any]:
    import json

    result = {
        key: value for key, value in values.items() if key not in {"statement_json", "anchors_json"}
    }
    result.update(
        standing="admitted_local_semantic_claim",
        assessment="independently_adjudicated_exact_case",
        semantic_scope="supplied_target_denotation_in_declared_source_context",
        canonical_identity="not_established",
        scientific_support="unmodeled",
        original_pdf_glyph_fidelity="not_established_by_local_publication",
    )
    if support:
        result.update(
            statement=json.loads(values["statement_json"]),
            anchors=json.loads(values["anchors_json"]),
        )
    return result
