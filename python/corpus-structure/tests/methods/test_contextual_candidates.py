"""Independent source/role and selected-edge projection controls for actual occurrence linking."""

from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest

from corpus_structure.core.db.lifetime import DatabaseOperationCancelled
from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.methods.contextual_candidates import (
    ContextualCandidateConfig,
    ContextualCandidates,
    relationship_contributions,
    retained_occurrences,
)
from corpus_structure.methods.contextual_embeddings import EncodedVector, EncoderResult, identity
from corpus_structure.semantic.contextual_links import (
    RelationshipConstraint,
    RelationshipWitness,
    select_relationships,
)
from corpus_structure.semantic.contextual_retrieval import (
    ChannelHit,
    freeze_inventory,
    fuse_candidates,
    target_representation,
)
from corpus_structure.semantic.contributions import contribution_identity, occurrence_identity
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.record_contracts import anchor_identity
from methods.test_m1_producer import view

PIN = dict(
    source="source",
    native_product_task_id=1,
    product_key="native",
    product_digest="a" * 64,
    projection_digest="b" * 64,
    recipe_digest="c" * 64,
    source_view_id=1,
)


def located(role="term", start=0, end=4) -> dict[str, Any]:
    anchor = dict(
        pin=PIN,
        space="native",
        pointer="#/texts/1",
        precision="exact",
        start=start,
        end=end,
        source_piece="Mean is average."[start:end],
    )
    anchor["anchor_id"] = anchor_identity(anchor)
    row = dict(
        kind="occurrence",
        semantic_type="source_rule." + role,
        operation_key="producer-op",
        item_key=role,
        pin=PIN,
        anchors=(anchor,),
        occurrence_id=occurrence_identity((anchor,)),
    )
    row["contribution_id"] = contribution_identity(row)
    return row


def test_actual_roles_preserved_with_one_physical_query_context():
    a, b = located(), located("expression")
    rows, contexts, coordinates = retained_occurrences(
        {"contributions": (a, b)}, {"#/texts/1": {"text": "Mean is average."}}, PIN, "new-op"
    )
    assert len(rows) == 2 and len(contexts) == 1
    assert rows[0]["contribution_id"] != rows[1]["contribution_id"]
    assert rows[0]["occurrence_id"] == rows[1]["occurrence_id"]
    assert {source_python(row["value"])["producer_semantic_type"] for row in rows} == {
        "source_rule.term",
        "source_rule.expression",
    }
    assert coordinates[0]["text"] == "Mean is average."


def test_actual_occurrence_cannot_invent_source_extent():
    row = located()
    row["anchors"][0]["source_piece"] = "wrong"
    with pytest.raises(ValueError, match="slice"):
        retained_occurrences(
            {"contributions": (row,)}, {"#/texts/1": {"text": "Mean is average."}}, PIN, "new-op"
        )


def test_supplied_mention_and_registry_production_bridge_removed():
    with pytest.raises(ValueError):
        ContextualCandidateConfig.model_validate(dict(cases=(), registry_targets=(), scope="s"))


def test_projection_preserves_all_selected_kinds_without_first_alternative():
    from corpus_structure.methods.contextual_embeddings import EncodedVector

    source = located()
    occurrence = source["occurrence_id"]
    target = target_representation(
        "concept", "definition-component:source", "Mean", "average", scope="chapter"
    )
    semantic = {
        "term": {"text": "Mean", "start": 0},
        "content": {"text": "average", "start": 8},
        "interpretation": "definition",
        "scope": "chapter",
    }
    inventory = freeze_inventory(
        (target,),
        source_selection="component-inventory",
        scope="chapter",
        semantic_targets={"concept": semantic},
    )
    candidates = fuse_candidates(
        occurrence_id=occurrence,
        query=EncodedVector("v", occurrence, "source", "p", "digest", (1.0, 0.0)),
        inventory=inventory,
        channels={"dense": (ChannelHit("concept", 1.0),)},
    )
    original = RelationshipWitness(
        "d",
        occurrence,
        "concept",
        "denotes",
        "source",
        "chapter",
        None,
        (source["contribution_id"],),
        "producer_group",
    )
    decision = select_relationships(
        candidates=candidates,
        inventory=inventory,
        source_binding="source",
        scope="chapter",
        effective_version=None,
        constraints=(
            RelationshipConstraint("sense", ("denotes",), "usage", "sense", "one"),
            RelationshipConstraint(
                "comparison", ("compared-with",), "subject", "comparator", "many"
            ),
        ),
        witnesses=(original, replace(original, witness_id="c", relation="compared-with")),
    )
    rows = relationship_contributions(decision, (source,), inventory, "edge-op")
    assert {source_python(row["value"])["relation"] for row in rows} == {"denotes", "compared-with"}
    assert len({row["computation_dependencies"][4] for row in rows}) == 2
    assert all(
        "edge_id" not in source_python(row["value"])
        and "constraint_id" not in source_python(row["value"])
        for row in rows
    )
    assert all(row["members"] == (source["contribution_id"],) for row in rows)
    reordered = freeze_inventory(
        (target,),
        source_selection="component-inventory",
        scope="chapter",
        semantic_targets={
            "concept": {
                "content": {"start": 8, "text": "average"},
                "term": {"start": 0, "text": "Mean"},
                "scope": "chapter",
                "interpretation": "definition",
            }
        },
    )
    assert relationship_contributions(decision, (source,), reordered, "edge-op") == rows
    assert source_python(rows[0]["value"])["target"] == semantic


@pytest.mark.parametrize(
    "failure", [OSError("controlled late read failure"), DatabaseOperationCancelled("cancelled")]
)
def test_later_operation_failure_preserves_encoder_and_completed_products(monkeypatch, failure):
    source = view()
    from corpus_structure.semantic.contextual_registry import ExtractedComponentTarget
    from corpus_structure.semantic.proposals import native_source_frame
    from corpus_structure.semantic.source_contexts import record_source_pin

    pin = record_source_pin(native_source_frame(source, ()))
    products = []
    for index, (start, end) in enumerate(((0, 4), (8, 15))):
        anchor = dict(
            pin=pin,
            space="native",
            pointer="#/texts/1",
            precision="exact",
            start=start,
            end=end,
            source_piece=source.text[start:end],
        )
        anchor["anchor_id"] = anchor_identity(anchor)
        product = dict(
            kind="occurrence",
            semantic_type="source_rule.term",
            operation_key="producer",
            item_key=str(index),
            pin=pin,
            anchors=(anchor,),
            occurrence_id=occurrence_identity((anchor,)),
        )
        product["contribution_id"] = contribution_identity(product)
        products.append(product)
    cfg = ContextualCandidateConfig(
        target_components=(
            ExtractedComponentTarget.model_validate(
                dict(
                    reference=dict(
                        product_id="structural:source",
                        component_id="a" * 64,
                        operation_id="components",
                        operation_version="1",
                        project_id="source",
                        run_id=1,
                        cut_id=1,
                        release_id="release",
                        result_revision=0,
                        selected_task_id=1,
                        origin_task_id=1,
                        runtime_fingerprint="runtime",
                        dependencies=("source",),
                    ),
                    label="Mean",
                    description="An average",
                    scope="chapter5",
                )
            ),
        ),
        relationship_constraints=(
            RelationshipConstraint("sense", ("denotes",), "usage", "sense", "one"),
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
            channels={"dense": (ChannelHit("a" * 64, 1.0),)},
        )

    reader = SimpleNamespace(
        source_view=lambda _: source,
        source_result=lambda *_: dict(contributions=products),
        component_semantic_targets=lambda _: {
            "a" * 64: {
                "term": {"text": "Mean"},
                "content": {"text": "An average"},
                "interpretation": "definition",
                "scope": "chapter5",
            }
        },
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
        c for c in result.contributions if c["semantic_type"] == "contextual.relationship"
    )
    source_product = result.contributions[0]
    assert proposal["members"] == (source_product["contribution_id"],)
    assert proposal["anchors"] == source_product["anchors"]
    statement = source_python(proposal["value"])
    assert statement["target"]["term"]["text"] == "Mean" and statement["relation"] == "denotes"
    assert statement["scope"] == "chapter5" and statement["effective_version"] is None
    assert proposal["score_state"] == "missing" and "score" not in proposal
    assert first["emitted_count"] == 2
    assert "controlled late read failure" in phases[-2]["reason"]


def test_actual_named_role_group_proposes_multiple_compatible_kinds():
    from corpus_structure.methods.contextual_candidates import (
        ProducerRelationshipRecipe,
        producer_relationship_witnesses,
    )

    originals = []
    for role, start, end in (("subject", 0, 4), ("object", 8, 15)):
        original = located(role, start, end)
        original["item_key"] = "actual-group/role/" + role
        original["component"] = dict(
            kind="located_role",
            rule="typed-comparison",
            roles=(dict(role=role, outcome="complete"),),
        )
        original["contribution_id"] = contribution_identity(original)
        originals.append(original)
    upstream = {"contributions": originals}
    products, _, _ = retained_occurrences(
        upstream, {"#/texts/1": {"text": "Mean is average."}}, PIN, "current"
    )
    target = target_representation(
        "average-concept", "definition-source", "average", "an average", scope="chapter"
    )
    inventory = freeze_inventory((target,), source_selection="components", scope="chapter")
    witnesses = producer_relationship_witnesses(
        upstream,
        products,
        products[0]["occurrence_id"],
        inventory,
        {"average-concept"},
        tuple(
            ProducerRelationshipRecipe(
                rule="typed-comparison",
                occurrence_role="subject",
                target_role="object",
                relation=relation,
            )
            for relation in ("compared-with", "specializes")
        ),
        "source",
        "chapter",
        None,
    )
    assert {w.relation for w in witnesses} == {"compared-with", "specializes"}
    assert all(
        w.evidence_ids == (products[0]["contribution_id"], products[1]["contribution_id"])
        for w in witnesses
    )
    assert all(w.basis == "producer_group" and w.support_state == "unassessed" for w in witnesses)


def test_overlapping_roles_choose_only_each_edges_cited_occurrence_carrier():
    from corpus_structure.methods.contextual_candidates import (
        ProducerRelationshipRecipe,
        producer_relationship_witnesses,
    )

    unrelated = located("unrelated")
    unrelated["item_key"] = "other-group/role/unrelated"
    subject, object_ = located("subject"), located("object", 8, 15)
    for row, role in ((subject, "subject"), (object_, "object")):
        row["item_key"] = "actual-group/role/" + role
        row["component"] = dict(
            kind="located_role",
            rule="typed-specialization",
            roles=(dict(role=role, outcome="complete"),),
        )
        row["contribution_id"] = contribution_identity(row)
    unrelated["contribution_id"] = contribution_identity(unrelated)
    inventory = freeze_inventory(
        (target_representation("average", "definition", "average", "an average", scope="chapter"),),
        source_selection="components",
        scope="chapter",
    )
    observations = []
    for originals in ((unrelated, subject, object_), (subject, unrelated, object_)):
        upstream = dict(contributions=originals)
        products, contexts, _ = retained_occurrences(
            upstream,
            {"#/texts/1": {"text": "Mean is average."}},
            PIN,
            "current",
        )
        assert len(products) == 3 and len(contexts) == 2
        by_role = {source_python(p["value"])["producer_semantic_type"]: p for p in products}
        subject_product, unrelated_product = (
            by_role["source_rule.subject"],
            by_role["source_rule.unrelated"],
        )
        occurrence = subject_product["occurrence_id"]
        assert occurrence == unrelated_product["occurrence_id"]
        witnesses = producer_relationship_witnesses(
            upstream,
            products,
            occurrence,
            inventory,
            {"average"},
            (
                ProducerRelationshipRecipe(
                    rule="typed-specialization",
                    occurrence_role="subject",
                    target_role="object",
                    relation="specializes",
                ),
            ),
            "source",
            "chapter",
            None,
        )
        (witness,) = witnesses
        assert witness.evidence_ids == (
            subject_product["contribution_id"],
            by_role["source_rule.object"]["contribution_id"],
        )
        candidates = fuse_candidates(
            occurrence_id=occurrence,
            query=EncodedVector("query", occurrence, "source", "profile", "digest", (1.0, 0.0)),
            inventory=inventory,
            channels={"dense": (ChannelHit("average", 1.0),)},
        )
        decision = select_relationships(
            candidates=candidates,
            inventory=inventory,
            source_binding="source",
            scope="chapter",
            effective_version=None,
            constraints=(
                RelationshipConstraint(
                    "specialization", ("specializes",), "subject", "object", "one"
                ),
            ),
            witnesses=witnesses,
        )
        (proposal,) = relationship_contributions(decision, products, inventory, "edge-operation")
        assert proposal["members"] == (subject_product["contribution_id"],)
        assert proposal["anchors"] == subject_product["anchors"]
        assert proposal["computation_dependencies"][0] == subject_product["contribution_id"]
        assert source_python(proposal["value"])["relation"] == "specializes"
        observations.append(proposal)
        # The object-side evidence is real but belongs to another physical occurrence;
        # the unrelated same-span role is not a witness for this selected edge.
        with pytest.raises(ValueError, match="lacks a cited source occurrence"):
            relationship_contributions(
                decision,
                tuple(p for p in products if p is not subject_product),
                inventory,
                "edge-operation",
            )
        comparison = replace(
            witness,
            witness_id="separate-comparison",
            relation="compared-with",
            evidence_ids=(unrelated_product["contribution_id"],),
        )
        multi = select_relationships(
            candidates=candidates,
            inventory=inventory,
            source_binding="source",
            scope="chapter",
            effective_version=None,
            constraints=(
                *decision.constraints,
                RelationshipConstraint(
                    "comparison", ("compared-with",), "usage", "comparator", "many"
                ),
            ),
            witnesses=(*witnesses, comparison),
        )
        projected = {
            source_python(p["value"])["relation"]: p
            for p in relationship_contributions(multi, products, inventory, "edge-operation")
        }
        assert projected["specializes"]["members"] == (subject_product["contribution_id"],)
        assert projected["compared-with"]["members"] == (unrelated_product["contribution_id"],)
    assert observations[0] == observations[1]
