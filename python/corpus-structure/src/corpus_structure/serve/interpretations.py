"""Bounded transport-neutral interpretation lookup and retained review detail."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, JsonValue

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.releases import open_release


class InterpretationAnswer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: str = "source-interpretation-1"
    kind: str
    body: dict[str, JsonValue]


def answer(kind, body, max_bytes=1024**2):
    from corpus_structure.semantic.query import ReadLimit

    content = canonical_bytes(dict(version="source-interpretation-1", kind=kind, body=body))
    if len(content) > max_bytes:
        raise ReadLimit("interpretation response exceeds byte budget", reason="oversized_item")
    return InterpretationAnswer.model_validate_json(content)


def term_lookup(conn, *, release_id, field, query=None, browse=False, max_bytes=1024**2):
    from corpus_structure.semantic.interpretations import lookup_terms

    return answer(
        "terminology_lookup",
        lookup_terms(open_release(conn, release_id), field, query, browse=browse),
        max_bytes,
    )


def review_detail(
    conn, *, review_run_id, review_cut_id, contribution_ids, limit=20, max_bytes=1024**2
):
    from corpus_structure.semantic.contribution_queries import read_source_contributions
    from corpus_structure.semantic.interpretation_queries import review_population

    if not contribution_ids or len(set(contribution_ids)) != len(contribution_ids):
        raise ValueError("review detail requires distinct contribution identities")
    review, _ = review_population(conn, run_id=review_run_id, cut_id=review_cut_id)
    prepared = open_release(conn, review.release_id)
    result = read_source_contributions(
        conn,
        prepared=prepared,
        run_id=review_run_id,
        cut_id=review_cut_id,
        contribution_ids=tuple(contribution_ids),
        include_details=True,
        limit=limit,
        max_bytes=max_bytes,
    )
    # Requested IDs absent under this exact cut are never substituted from current results.
    found = {r["contribution_id"] for r in result.contributions}
    if found != set(contribution_ids):
        raise ValueError("review contribution unavailable under selected population")
    return answer(
        "retained_review",
        dict(
            review_run_id=review_run_id,
            review_cut_id=review_cut_id,
            release_id=review.release_id,
            contributions=list(result.contributions),
            complete=not result.more,
        ),
        max_bytes,
    )
