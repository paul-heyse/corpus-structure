"""Artifact candidates keep source-work scope and evidence, without merging authority."""

import pytest

from corpus_structure.semantic.artifact_identity import (
    ArtifactNomination,
    ArtifactRecord,
    ArtifactScoringPolicy,
    SourceArtifactOccurrence,
    native_alias_candidates,
    normalized_code,
    pair_candidates,
    score_pairs,
    source_alias_fields,
)


def record(identity, *, work="book", code="5.1", title=None, aliases=(), revision=None):
    return ArtifactRecord(
        contribution_id=identity,
        occurrence_id="occurrence:" + identity,
        source_contribution={},
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
            **source_alias_fields(
                "Table 5.1" + "".join(f' (alias: "{alias}")' for alias in aliases),
                len("Table 5.1"),
                "#/texts/" + identity,
            ),
            revision=revision,
            revision_state="observed" if revision else "unknown",
            occurrence_role="caption" if title else "reference",
            scope="chapter5",
            source_pointer="#/texts/" + identity,
            dependencies=("source:" + identity,),
        ),
    )


def nomination(left, right, ordinal=1):
    return ArtifactNomination(
        left=left,
        right=right,
        relationship=dict(
            contribution_id="source-contribution:" + format(ordinal, "064x"),
            project_id="controlled",
            run_id=1,
            cut_id=1,
            release_id="release:controlled",
            result_revision=1,
            selected_task_id=1,
            origin_task_id=1,
            runtime_fingerprint="runtime:controlled",
        ),
    )


def test_shared_generators_are_one_pair_with_complete_provenance():
    records = (
        record("a", title="Moments", aliases=("T5",)),
        record("b", title="Moments", aliases=("T5", "T5")),
    )
    external = (nomination("a", "b"), nomination("a", "b", ordinal=2))
    alias, counts = native_alias_candidates(records, count_rules=True)
    assert alias == (("a", "b"),)
    assert counts[0]["marginal_comparison_count"] == 1
    assert counts[0]["cumulative_comparison_count"] == 1
    assert counts[0]["is_estimate"] is False
    (pair,) = pair_candidates(records, external_nominations=external, native_alias_pairs=alias)
    assert pair.candidate_routes == (
        "exact_code",
        "lexical_title",
        "external_pairs",
        "native_alias_array",
    )
    assert pair.dependencies == (
        "a",
        "b",
        *(n.relationship.contribution_id for n in external),
        "source:a",
        "source:b",
    )
    assert pair.model_probability is None and pair.standing == "candidate_relative_private"
    assert pair_candidates(
        tuple(reversed(records)), external_nominations=external, native_alias_pairs=alias
    ) == (pair,)


def test_parent_work_and_exclusions_refuse_false_bridges():
    records = (record("a"), record("b", work="another-book"))
    assert pair_candidates(records) == ()
    (pair,) = pair_candidates(records, external_nominations=(nomination("a", "b"),))
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
        records,
        external_nominations=(nomination("a", "b"), nomination("b", "c", 2)),
        exclusions=(("a", "c"),),
    )
    assert {(p.left, p.right) for p in pairs} == {("a", "b"), ("b", "c")}
    with pytest.raises(ValueError, match="endpoints"):
        pair_candidates(records, external_nominations=(nomination("a", "foreign"),))


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
    records = (
        record("a", code=None, aliases=("T5",)),
        record("b", code=None, aliases=("t5",)),
        record("c", work="another-book", aliases=("T5",)),
    )
    alias, _ = native_alias_candidates(records)
    assert alias == (("a", "b"),)
    policy = ArtifactScoringPolicy(prior=0.1, code_m=0.9, code_u=0.01, title_m=0.8, title_u=0.05)
    scored = score_pairs(records, pair_candidates(records, native_alias_pairs=alias), policy)
    assert scored[0].candidate_routes == ("native_alias_array",)
    assert scored[0].model_id == policy.identity
    assert "gamma_controlled_code" in {f.name for f in scored[0].model_evidence}


def test_identity_product_rejects_cross_work_scores_and_missing_citations():
    from corpus_structure.semantic.artifact_identity import ArtifactIdentityProduct

    records = (record("a"), record("b", work="foreign"))
    policy = ArtifactScoringPolicy(prior=0.1, code_m=0.9, code_u=0.01, title_m=0.8, title_u=0.05)
    pair = pair_candidates(records, external_nominations=(nomination("a", "b"),))[0]
    with pytest.raises(ValueError, match="crosses"):
        ArtifactIdentityProduct(
            records=records,
            pairs=(pair.model_copy(update={"scope_state": "compatible"}),),
            policy=policy,
            source_mapping_provenance=("manifest",),
        )
    with pytest.raises(ValueError):
        ArtifactRecord.model_validate({**records[0].model_dump(), "citations": []})


def test_strict_policy_probabilities_refuse_boundaries_and_nonfinite_values():
    for invalid in (0, 1, -0.1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            ArtifactScoringPolicy(prior=invalid, code_m=0.9, code_u=0.01, title_m=0.8, title_u=0.05)


def test_released_identity_shapes_retain_empty_unbound_and_singleton_diagnostics():
    from pathlib import Path
    from types import SimpleNamespace

    from methods.test_m1_source_preparation import source
    from methods.test_scoped_relations import complete_native_fields

    from corpus_structure.core.method import UnitRef
    from corpus_structure.core.vocab import TaskUnitType
    from corpus_structure.methods.artifact_identity import (
        ArtifactIdentityConfig,
        ArtifactIdentityMethod,
    )
    from corpus_structure.methods.scoped_relations import SourceWorkBinding
    from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
    from corpus_structure.semantic.observations import observation_inputs
    from corpus_structure.semantic.proposals import native_source_frame
    from corpus_structure.semantic.structural_products import (
        ExternalSourceRef,
        StructuralInput,
        StructuralPassage,
    )

    path = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    prepared = prepare_release(
        observation_inputs(SourceBundle("core", (SourceArtifact("core", path.read_bytes()),)))
    )
    policy = ArtifactScoringPolicy(prior=0.1, code_m=0.9, code_u=0.01, title_m=0.8, title_u=0.05)
    for raw, bind in [
        ("No numbered artifact is stated.", True),
        ("Table 5.1 Moments", True),
        ("Table 5.1 Moments", False),
    ]:
        frame = native_source_frame(complete_native_fields(source(raw, labels=("caption",))), ())
        native = frame.native_product
        reference = ExternalSourceRef(
            project_id="p",
            run_id=1,
            cut_id=1,
            release_id="r",
            result_revision=1,
            source_view_id=frame.source_view_id,
            native_task_id=native.task_id,
            native_product_key=native.product_key,
            native_content_digest=native.content_digest,
            projection_digest=frame.projection_digest,
            recipe_digest=frame.recipe_digest,
            coordinate_version=2,
        )
        inputs = StructuralInput(
            question="Artifact source development",
            scope="fixture",
            inventory_id="literal",
            policy_id="artifact-candidate-1",
            sources=(reference,),
            passages=(
                StructuralPassage(
                    passage_id="literal",
                    source_ref=reference.identity,
                    start=0,
                    end=len(raw),
                    text=raw,
                    scope="fixture",
                ),
            ),
            dependencies=("native:" + str(native.task_id),),
        )

        class Reader:
            def __init__(self, bound_inputs, selected_ref, source_frame, bound):
                self.inputs = bound_inputs
                self.source_ref = selected_ref
                self.frame = source_frame
                self.bound = bound

            def structural_source_frame(self, observed, selected):
                assert self.bound and observed == self.inputs and selected == self.source_ref
                return self.frame

        cfg = ArtifactIdentityConfig(
            inputs=inputs,
            structural_input_digest=inputs.identity,
            policy=policy,
            work_bindings=(
                SourceWorkBinding(
                    native_content_digest=native.content_digest,
                    source_work="parent",
                    provenance="literal-source",
                ),
            )
            if bind
            else (),
        )
        ctx = SimpleNamespace(
            reader=Reader(inputs, reference.identity, frame, bind), check_active=lambda: None
        )
        (result,) = ArtifactIdentityMethod().run(
            (SimpleNamespace(ref=UnitRef(TaskUnitType.RUN, unit_key=inputs.identity)),), cfg, ctx
        )
        assert result.structural_product is not None
        from corpus_structure.semantic.refusals import SemanticRefusal
        from corpus_structure.semantic.structural_admission import structural_statement
        from corpus_structure.semantic.structural_products import StructuralProductReport

        with pytest.raises(SemanticRefusal, match="No public structural policy"):
            structural_statement(StructuralProductReport.model_validate(result.structural_product))
        from corpus_structure.semantic.artifact_identity import ArtifactIdentityProduct

        product = ArtifactIdentityProduct.model_validate(
            result.structural_product["artifact_identity"]
        ).model_dump(mode="json", exclude_none=True)
        from corpus_structure.semantic.identity import canonical_bytes

        prepared.validate_json("ArtifactIdentityProduct", canonical_bytes(product))
        from corpus_structure.semantic.observations import bind_result

        bound = bind_result(
            prepared,
            source="run",
            method="structure.artifact_identity",
            operation_version=ArtifactIdentityMethod.version,
            configuration_hash="config",
            input_hash="input",
            invocation_key="invocation",
            result=result,
        )
        assert (
            bound.model_dump(mode="json", exclude_none=True)["structural_product"][
                "artifact_identity"
            ]["records"]
            == product["records"]
        )
        assert product["pairs"] == []
        assert len(product["records"]) == (1 if bind and raw.startswith("Table") else 0)
        assert product["unbound_source_ids"] == ([] if bind else [frame.source_view_id])


def test_pair_guard_uses_existing_resolver_without_transitive_bridges(monkeypatch):
    from corpus_structure.semantic import identity_resolution

    original = identity_resolution.constrained_label_groups
    calls = []

    def observed(members, exclusions, anchors):
        calls.append((tuple(members), tuple(exclusions), frozenset(anchors)))
        return original(members, exclusions, anchors)

    monkeypatch.setattr(identity_resolution, "constrained_label_groups", observed)
    records = tuple(record(identity) for identity in "abc")
    pairs = pair_candidates(records, exclusions=(("a", "c"),), known_anchor_ids=("c", "a"))
    actual = {(p.left, p.right): p.scope_state for p in pairs}
    assert actual == {("a", "b"): "compatible", ("a", "c"): "excluded", ("b", "c"): "compatible"}
    # A-B and B-C are individual proposals; neither expands the guard's universe to A-C.
    assert {members for members, _, _ in calls} == {("a", "b"), ("a", "c"), ("b", "c")}
    assert all(
        len(members) == 2
        and set(anchors) <= set(members)
        and all(set(edge) <= set(members) for edge in exclusions)
        for members, exclusions, anchors in calls
    )
    assert (
        pair_candidates(
            tuple(reversed(records)), exclusions=(("c", "a"),), known_anchor_ids=("a", "c")
        )
        == pairs
    )
    guarded = pair_candidates((record("a"), record("b")), known_anchor_ids=("a", "b"))
    assert len(guarded) == 1 and guarded[0].scope_state == "excluded"
    assert guarded[0].model_probability is None
    external = pair_candidates(
        (record("a"), record("b", work="foreign")),
        external_nominations=(nomination("a", "b"),),
        known_anchor_ids=("a", "b"),
    )
    assert external[0].scope_state == "excluded"
    for invalid in (("absent",), ("a", "a")):
        with pytest.raises(ValueError, match="known anchors"):
            pair_candidates(records, known_anchor_ids=invalid)


def test_explicit_alias_states_preserve_native_occurrences_and_unknown():
    raw = 'Table 5.1 (also called "Grid") (alias: "GRID") title'
    actual = source_alias_fields(raw, len("Table 5.1"), "#/texts/1")
    assert actual["alias_state"] == "observed"
    assert actual["aliases"] == ("Grid", "GRID")
    assert all(raw[a["start"] : a["end"]] == a["text"] for a in actual["alias_occurrences"])
    unknown = source_alias_fields("Table 5.1 just a title", len("Table 5.1"), "#/texts/1")
    assert unknown == dict(alias_state="unknown", aliases=(), alias_occurrences=())
    empty = source_alias_fields("Table 5.1 (aliases: none)", len("Table 5.1"), "#/texts/1")
    assert empty["alias_state"] == "known_empty"
    assert empty["alias_absence"]["text"] == "aliases: none"
    with pytest.raises(ValueError, match="observed aliases"):
        SourceArtifactOccurrence.model_validate(
            {**record("a").artifact.model_dump(), "alias_state": "observed", "aliases": ["title"]}
        )


def test_pilot_scores_the_fixed_labeled_support_without_nominating_a_missed_pair():
    from corpus_structure.evaluate.artifact_pilot import (
        ArtifactPairJudgment,
        evaluate_artifact_pilot,
    )
    from corpus_structure.semantic.artifact_identity import ArtifactIdentityProduct

    records = (
        record("a", title="Moments"),
        record("b", title="Moments"),
        record("c", code="??", title="reference"),
        record("d", code=None),
    )
    policy = ArtifactScoringPolicy(prior=0.1, code_m=0.9, code_u=0.01, title_m=0.8, title_u=0.05)
    product = ArtifactIdentityProduct(
        records=records, pairs=score_pairs(records, pair_candidates(records), policy), policy=policy
    )
    judgments = tuple(
        ArtifactPairJudgment(left=left, right=right, case_id=case, judgment=judgment)
        for left, right, case, judgment in (
            ("a", "b", "false-code", "unsupported"),
            ("a", "c", "miss", "supported"),
            ("c", "d", "unknown-codes", "ambiguous"),
        )
    )
    result = evaluate_artifact_pilot(product, judgments)
    cases = {c["case_id"]: c for c in result["cases"]}
    assert cases["miss"]["nomination_routes"] == []
    assert cases["miss"]["union_model_probability"] is None
    assert cases["unknown-codes"]["code_state"] == ["malformed", "unknown"]
    models = result["models"]
    primary = models["primary"]
    assert primary["label_accuracy"]
    assert primary["label_prediction_errors"]["0.5"]
    assert {(s["left"], s["right"]) for s in primary["scores"]} == {("a", "b"), ("a", "c")}
    assert models["half_prior_odds"]["policy"]["prior"] < policy.prior
    assert models["double_prior_odds"]["policy"]["prior"] > policy.prior
