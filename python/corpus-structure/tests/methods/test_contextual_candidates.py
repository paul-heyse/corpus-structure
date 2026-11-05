"""Controlled workflow faults prove retention, never native encoder or retrieval quality."""

from types import SimpleNamespace

import pytest

from corpus_structure.core.db.lifetime import DatabaseOperationCancelled
from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.methods.contextual_candidates import (
    ContextualCandidateConfig,
    ContextualCandidates,
)
from corpus_structure.methods.contextual_embeddings import EncodedVector, EncoderResult, identity
from corpus_structure.semantic.contextual_retrieval import ChannelHit, fuse_candidates
from corpus_structure.semantic.observations import source_python
from methods.test_m1_producer import view


@pytest.mark.parametrize(
    "failure", [OSError("controlled late read failure"), DatabaseOperationCancelled("cancelled")]
)
def test_later_operation_failure_preserves_encoder_and_completed_products(monkeypatch, failure):
    source = view()
    cfg = ContextualCandidateConfig(
        registry_targets=(dict(target_id="a", label="Mean", description="An average."),),
        cases=(
            dict(
                case_id="first",
                pointer="#/texts/1",
                text=source.text,
                start=0,
                end=4,
                mention="Mean",
            ),
            dict(
                case_id="second",
                pointer="#/texts/1",
                text=source.text,
                start=8,
                end=15,
                mention="average",
            ),
        ),
        source_product_digest=source.ref.native_product.content_digest,
        source_projection_digest=source.ref.projection_digest,
        scope="chapter5",
    )

    def encoded(inputs, profile, **kwargs):
        vectors = []
        for item in inputs:
            digest = "a" * 64
            vector_id = identity(
                "context-vector",
                [
                    item.object_id,
                    item.source_binding,
                    profile.profile_id,
                    digest,
                    item.representation_digest,
                ],
            )
            vectors.append(
                EncodedVector(
                    vector_id,
                    item.object_id,
                    item.source_binding,
                    profile.profile_id,
                    digest,
                    (1.0,) + (0.0,) * (profile.dimension - 1),
                    item.representation_digest,
                )
            )
        return EncoderResult(profile.profile_id, (), tuple(vectors), ())

    calls = []

    def retrieve(**request):
        calls.append(request)
        if len(calls) == 2:
            raise failure
        return fuse_candidates(
            occurrence_id=request["occurrence_id"],
            query=request["query"],
            inventory=request["inventory"],
            channels={"dense": (ChannelHit("a", 1.0),)},
        )

    reader = SimpleNamespace(
        source_view=lambda _: source,
        cached_contextual_vectors=lambda **_: (),
        contextual_candidates=retrieve,
    )
    ctx = SimpleNamespace(reader=reader, check_active=lambda: None)
    unit = SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, source.ref.id, source.ref.key))
    monkeypatch.setattr(
        "corpus_structure.methods.contextual_candidates.verify_encoder_implementation", lambda _: ()
    )
    monkeypatch.setattr("corpus_structure.methods.contextual_candidates.encode_contexts", encoded)
    if isinstance(failure, DatabaseOperationCancelled):
        with pytest.raises(DatabaseOperationCancelled):
            ContextualCandidates().run((unit,), cfg, ctx)
        return
    (result,) = ContextualCandidates().run((unit,), cfg, ctx)
    assert result.contribution_operations is not None
    first, *phases = result.contribution_operations
    report = first["contextual_enrichment"]
    assert first["outcome"] == "succeeded" and "encoder products" in first["question"]
    assert report["product_counts"]["vectors"] == 3
    assert report["product_counts"]["candidate_lists"] == 1
    assert report["product_counts"]["relationship_decisions"] == 1
    assert [p["outcome"] for p in phases] == ["succeeded", "succeeded", "failed", "not_run"]
    assert [p["emitted_count"] for p in phases] == [0, 1, 0, 0]
    assert result.contributions is not None
    proposal = next(
        c for c in result.contributions if c["semantic_type"] == "contextual.denotation"
    )
    source_product = result.contributions[0]
    assert proposal["members"] == (source_product["contribution_id"],)
    assert proposal["anchors"] == source_product["anchors"]
    statement = source_python(proposal["value"])
    assert statement["target_id"] == "a" and statement["relation"] == "denotes"
    assert statement["scope"] == "chapter5" and statement["effective_version"] is None
    assert proposal["score_state"] == "missing" and "score" not in proposal
    assert first["emitted_count"] == 2
    assert "controlled late read failure" in phases[-2]["reason"]
