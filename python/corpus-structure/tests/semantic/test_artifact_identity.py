"""Artifact candidates keep source-work scope and evidence, without merging authority."""

import pytest

from corpus_structure.semantic.artifact_identity import (
    ArtifactRecord,
    ArtifactScoringPolicy,
    SourceArtifactOccurrence,
    normalized_code,
    pair_candidates,
    score_pairs,
)


def record(identity, *, work="book", code="5.1", title=None, aliases=(), revision=None):
    return ArtifactRecord(
        contribution_id=identity,
        occurrence_id="occurrence:" + identity,
        citations=(
            dict(
                source_ref="source:" + identity,
                passage_id="p:" + identity,
                source_pointer="#/texts/" + identity,
                start=0,
                end=3,
                text="5.1",
            ),
        ),
        artifact=SourceArtifactOccurrence(
            source_work=work,
            artifact_kind="table",
            controlled_code=code,
            title=title,
            aliases=aliases,
            revision=revision,
            revision_state="observed" if revision else "unknown",
            occurrence_role="caption" if title else "reference",
            scope="chapter5",
            source_pointer="#/texts/" + identity,
            dependencies=("source:" + identity,),
        ),
    )


def test_shared_generators_are_one_pair_with_complete_provenance():
    records = (
        record("a", title="Moments", aliases=("T5",)),
        record("b", title="Moments", aliases=("T5", "T5")),
    )
    (pair,) = pair_candidates(records, external_pairs=(("b", "a"), ("a", "b")))
    assert pair.candidate_routes == ("exact_code", "lexical_title", "alias_array", "external_pairs")
    assert pair.dependencies == ("a", "b", "source:a", "source:b")
    assert pair.model_probability is None and pair.standing == "candidate_relative_private"
    assert pair_candidates(tuple(reversed(records)), external_pairs=(("a", "b"),)) == (pair,)


def test_parent_work_and_exclusions_refuse_false_bridges():
    records = (record("a"), record("b", work="another-book"))
    assert pair_candidates(records) == ()
    (pair,) = pair_candidates(records, external_pairs=(("a", "b"),))
    assert pair.scope_state == "excluded"
    assert (
        pair_candidates((record("a"), record("b")), exclusions=(("a", "b"),))[0].scope_state
        == "excluded"
    )


def test_malformed_equal_codes_are_not_exact_evidence():
    assert normalized_code("not a code") is None
    assert pair_candidates((record("a", code="???"), record("b", code="???"))) == ()
    assert normalized_code("5.1") == "5.1"


def test_revisions_distinguish_lineage_from_immutable_version():
    pair = pair_candidates((record("a", revision="1"), record("b", revision="2")))[0]
    assert pair.revision_relation == "different_observed"
    assert pair.scope_state == "compatible" and pair.model_probability is None
    assert pair_candidates((record("a"), record("b")))[0].revision_relation == "unknown"


def test_external_missing_edge_does_not_grow_a_component():
    records = tuple(record(x, code=None) for x in "abc")
    pairs = pair_candidates(
        records, external_pairs=(("a", "b"), ("b", "c")), exclusions=(("a", "c"),)
    )
    assert {(p.left, p.right) for p in pairs} == {("a", "b"), ("b", "c")}
    with pytest.raises(ValueError, match="endpoints"):
        pair_candidates(records, external_pairs=(("a", "foreign"),))


def test_actual_splink_scores_exact_registered_pairs():
    pytest.importorskip("splink")
    records = (record("a", title="Moments"), record("b"), record("c", code="5.2"))
    pairs = pair_candidates(records)
    result = score_pairs(
        records,
        pairs,
        ArtifactScoringPolicy(prior=0.1, code_m=0.9, code_u=0.01, title_m=0.8, title_u=0.05),
    )
    assert len(result) == 1
    assert result[0].model_probability == pytest.approx(10 / 11)
    assert result[0].candidate_routes == pairs[0].candidate_routes


def test_native_alias_blocking_is_source_scoped_and_frozen_model_is_recorded():
    from corpus_structure.semantic.artifact_identity import native_alias_candidates

    records = (
        record("a", aliases=("T5",)),
        record("b", aliases=("T5",)),
        record("c", work="another-book", aliases=("T5",)),
    )
    assert native_alias_candidates(records) == (("a", "b"),)
    policy = ArtifactScoringPolicy(prior=0.1, code_m=0.9, code_u=0.01, title_m=0.8, title_u=0.05)
    scored = score_pairs(records, pair_candidates(records), policy)
    assert scored[0].model_id == policy.identity
    assert "gamma_controlled_code" in {f.name for f in scored[0].model_evidence}


def test_identity_product_rejects_cross_work_scores_and_missing_citations():
    from corpus_structure.semantic.artifact_identity import ArtifactIdentityProduct

    records = (record("a"), record("b", work="foreign"))
    policy = ArtifactScoringPolicy(prior=0.1, code_m=0.9, code_u=0.01, title_m=0.8, title_u=0.05)
    pair = pair_candidates(records, external_pairs=(("a", "b"),))[0]
    with pytest.raises(ValueError, match="crosses"):
        ArtifactIdentityProduct(
            records=records,
            pairs=(pair.model_copy(update={"scope_state": "compatible"}),),
            policy=policy,
            source_mapping_provenance=("manifest",),
        )
    with pytest.raises(ValueError):
        ArtifactRecord.model_validate({**records[0].model_dump(), "citations": []})
