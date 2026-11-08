"""Independent source/role and selected-edge projection controls for actual occurrence linking."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from corpus_structure.core.db.lifetime import DatabaseOperationCancelled
from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.methods.contextual_candidates import (
    ContextualCandidateConfig,
    ContextualCandidates,
    ContextualCandidatesWithNamedBindings,
    ContextualCandidatesWithNeighborhood,
    explicit_definition_section,
    relationship_contributions,
    retained_occurrences,
)
from corpus_structure.methods.contextual_embeddings import EncodedVector, EncoderResult, identity
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
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


def test_coarse_native_occurrence_is_retained_without_an_encoder_span():
    row = located()
    anchor = row["anchors"][0]
    anchor.pop("start")
    anchor.pop("end")
    anchor.pop("source_piece")
    anchor["precision"] = "item"
    anchor["anchor_id"] = anchor_identity(anchor)
    row["occurrence_id"] = occurrence_identity((anchor,))
    row["contribution_id"] = contribution_identity(row)
    (actual,), contexts, _ = retained_occurrences(
        {"contributions": (row,)}, {"#/texts/1": {"text": "Mean is average."}}, PIN, "new-op"
    )
    assert actual["anchors"] == (anchor,)
    assert contexts == {}


def test_supplied_mention_and_registry_production_bridge_removed():
    with pytest.raises(ValueError):
        ContextualCandidateConfig.model_validate(dict(cases=(), registry_targets=(), scope="s"))


def test_typed_definition_cue_cannot_fall_back_to_literal_after_refusal():
    from corpus_structure.semantic.observations import source_value

    text = 'The phrase "as defined in Section 6.2" is quoted.'
    start = text.index("Section")
    marker = dict(
        kind="definition_reference",
        designator="6.2",
        scope="chapter",
        resolution="insufficient_evidence",
    )
    product = dict(
        anchors=(
            {
                "pointer": "#/texts/1",
                "start": start,
                "end": start + len("Section 6.2"),
                "precision": "exact",
                "source_piece": "Section 6.2",
            },
        ),
        value=source_value(
            dict(
                producer_semantic_type="structural.located_participant",
                producer_value=source_value(dict(role="named_link_subject", named_cue=marker)),
            )
        ),
    )
    nodes = {"#/texts/1": {"text": text}}
    assert explicit_definition_section(product, nodes, scope="chapter") is None


@pytest.fixture(scope="module")
def contextual_report_release():
    from corpus_structure.semantic.observations import observation_inputs

    path = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    return prepare_release(
        observation_inputs(SourceBundle("core", (SourceArtifact("core", path.read_bytes()),)))
    )


@pytest.mark.parametrize(
    (
        "labels",
        "complete",
        "budget",
        "expected",
        "selected",
        "provider_available",
        "catalog_complete",
    ),
    [
        (("6.2 Target",), True, 1, "selected", True, False, None),
        (("6.2 Target", "7.1 Unrelated"), True, 1, "selected", True, True, None),
        (("6.2 Target", "6.2 Competitor"), True, 2, "ambiguous", False, False, None),
        (("6.2 Target", "6.2 Competitor"), True, 1, "witness_budget_exceeded", False, False, None),
        (("6.2 Target",), False, 1, "unavailable_representation", False, False, None),
        ((), True, 1, "no_compatible_candidate", False, False, None),
        ((), True, 1, "outside_inventory", False, False, True),
        ((), True, 1, "no_compatible_candidate", False, False, False),
    ],
)
def test_retained_cross_view_heading_coverage_precedes_exploration(
    monkeypatch,
    labels,
    complete,
    budget,
    expected,
    selected,
    provider_available,
    catalog_complete,
    contextual_report_release,
):
    from corpus_structure.semantic.contextual_registry import SectionHeadingTarget
    from corpus_structure.semantic.observations import source_value
    from corpus_structure.semantic.proposals import native_source_frame
    from corpus_structure.semantic.source_contexts import record_source_pin
    from corpus_structure.semantic.structural_products import ExternalSourceRef

    text = "See Section 6.2."
    source = view()
    source = replace(
        source,
        text=text,
        pieces=(dict(source.pieces[0], end=len(text)),),
        items=(source.items[0], dict(source.items[1], text=text)),
    )
    pin = record_source_pin(native_source_frame(source, ()))
    cue_ref = ExternalSourceRef(
        project_id="project",
        run_id=1,
        cut_id=1,
        release_id="release",
        result_revision=0,
        source_view_id=source.ref.id,
        native_task_id=source.ref.native_product.task_id,
        native_product_key=source.ref.native_product.product_key,
        native_content_digest=source.ref.native_product.content_digest,
        projection_digest=source.ref.projection_digest,
        recipe_digest=source.ref.recipe_digest,
        coordinate_version=2,
    )
    destination = cue_ref.model_copy(update={"source_view_id": source.ref.id + 1})
    outside_ref = cue_ref.model_copy(update={"source_view_id": source.ref.id + 2})
    targets = []
    for index, label in enumerate(labels, 2):
        pointer = f"#/texts/{index}"
        targets.append(
            SectionHeadingTarget(
                target_id=identity(
                    "section-heading",
                    [
                        destination.native_content_digest,
                        destination.native_product_key,
                        pointer,
                        0,
                        len(label),
                    ],
                ),
                label=label,
                designator=label.split()[0],
                pointer=pointer,
                work_id="work",
                scope="chapter",
                citations=(destination,),
            )
        )
    cfg = ContextualCandidateConfig(
        source_dependency_method="structure.scoped_relations",
        section_sources=(cue_ref, destination),
        section_catalog_sources=(outside_ref,) if catalog_complete is not None else (),
        source_product_digest=source.ref.native_product.content_digest,
        source_projection_digest=source.ref.projection_digest,
        scope="chapter",
        unique_target_budget=budget,
    )
    anchor = dict(
        pin=pin,
        space="native",
        pointer="#/texts/1",
        precision="exact",
        start=4,
        end=15,
        source_piece="Section 6.2",
    )
    anchor["anchor_id"] = anchor_identity(anchor)
    original = dict(
        kind="occurrence",
        semantic_type="structural.located_participant",
        operation_key="producer",
        item_key="section-mention",
        pin=pin,
        anchors=(anchor,),
        occurrence_id=occurrence_identity((anchor,)),
        value=source_value(
            dict(
                role="named_link_subject",
                named_cue=dict(
                    kind="section_citation",
                    designator="6.2",
                    scope="chapter",
                    resolution="target_selection_required",
                ),
            )
        ),
    )
    original["contribution_id"] = contribution_identity(original)

    def unavailable(_profile):
        raise OSError("encoder unavailable")

    monkeypatch.setattr(
        "corpus_structure.methods.contextual_candidates.verify_encoder_implementation",
        (lambda _profile: ()) if provider_available else unavailable,
    )

    def encoded(items, profile, **_kwargs):
        digest = "a" * 64
        vectors = tuple(
            EncodedVector(
                identity(
                    "context-vector",
                    [
                        item.object_id,
                        item.source_binding,
                        profile.profile_id,
                        digest,
                        item.representation_digest,
                    ],
                ),
                item.object_id,
                item.source_binding,
                profile.profile_id,
                digest,
                (1.0,) + (0.0,) * (profile.dimension - 1),
                item.representation_digest,
            )
            for item in items
        )
        return EncoderResult(profile.profile_id, (), vectors, ())

    monkeypatch.setattr("corpus_structure.methods.contextual_candidates.encode_contexts", encoded)

    def retrieve(**request):
        (wrong,) = [target for target in targets if target.designator != "6.2"]
        return fuse_candidates(
            occurrence_id=request["occurrence_id"],
            query=request["query"],
            inventory=request["inventory"],
            budget=1,
            lexical_query=request["lexical_query"],
            channels={"dense": (ChannelHit(wrong.target_id, 0.9),)},
        )

    outside_label = "6.2 Outside selected views"
    outside_target = SectionHeadingTarget(
        target_id=identity(
            "section-heading",
            [
                outside_ref.native_content_digest,
                outside_ref.native_product_key,
                "#/texts/99",
                0,
                len(outside_label),
            ],
        ),
        label=outside_label,
        designator="6.2",
        pointer="#/texts/99",
        work_id="work",
        scope="chapter",
        citations=(outside_ref,),
    )

    def heading_inventory(refs, *_):
        assert refs[:2] == (cue_ref, destination)
        if len(refs) == 3:
            assert refs[2] == outside_ref and catalog_complete is not None
            rows = [*targets, outside_target]
            coverage = catalog_complete
        else:
            rows = targets
            coverage = complete
        return {
            "targets": [target.model_dump(mode="json") for target in rows],
            "complete": coverage,
        }

    reader = SimpleNamespace(
        source_view=lambda _: source,
        source_result=lambda *_: {"contributions": (original,), "origin_task_id": 1},
        contextual_section_headings=heading_inventory,
        cached_contextual_vectors=lambda **_: (),
        contextual_candidates=retrieve,
    )
    unit = SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, source.ref.id, source.ref.key))
    ctx = SimpleNamespace(reader=reader, check_active=lambda: None)

    (result,) = ContextualCandidates().run((unit,), cfg, ctx)
    assert result.contribution_operations is not None
    for operation in result.contribution_operations:
        contextual_report_release.validate_python("SourceContributionOperation", operation)
    report = result.contribution_operations[0]["contextual_enrichment"]
    (resolution,) = report["section_resolutions"]
    assert resolution["outcome"] == expected
    matching = tuple(sorted(target.target_id for target in targets if target.designator == "6.2"))
    assert resolution["eligible_target_ids"] == matching
    (decision,) = report["relationship_decisions"]
    assert bool(decision["selected_edges"]) is selected
    assert bool(decision["alternative_groups"]) is (expected == "ambiguous")
    (candidate,) = report["candidate_lists"]
    assert ("query_vector_id" in candidate) is provider_available
    channels = {channel["channel"]: channel["hits"] for channel in candidate["channel_results"]}
    assert len(channels["witness"]) == min(budget, len(matching))
    if catalog_complete is not None:
        assert report["section_catalog_sources"] == (outside_ref.model_dump(mode="json"),)
        assert report["section_targets"] == () and candidate["candidates"] == ()
    if provider_available:
        (winner,) = candidate["candidates"]
        assert winner["target_id"] == matching[0]
        assert channels["dense"][0]["target_id"] != winner["target_id"]


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
    assert [p["emitted_count"] for p in phases] == [0, 0, 0, 0]
    assert result.contributions is not None
    assert len(result.contributions) == 2
    assert all(row["semantic_type"] == "contextual.located_mention" for row in result.contributions)
    (decision,) = report["relationship_decisions"]
    assert decision["outcome"] == "insufficient_evidence"
    assert not decision["selected_edges"]
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


@pytest.mark.parametrize("provider_available", [True, False])
@pytest.mark.parametrize(
    "method, subject",
    [
        (ContextualCandidates, "section"),
        (ContextualCandidatesWithNeighborhood, "section"),
        (ContextualCandidatesWithNeighborhood, "term"),
        (ContextualCandidatesWithNamedBindings, "identifier"),
    ],
)
def test_explicit_cross_view_definition_witness_survives_exploration(
    monkeypatch,
    provider_available,
    method,
    subject,
):
    from corpus_structure.semantic.contextual_registry import ExtractedComponentTarget
    from corpus_structure.semantic.observations import source_value
    from corpus_structure.semantic.proposals import native_source_frame
    from corpus_structure.semantic.source_contexts import record_source_pin

    quoted = subject != "section"
    spelling = {"term": "Expected definition", "identifier": "PX:18.1", "section": "Section 6.2"}[
        subject
    ]
    text = {
        "term": f'Use "{spelling}" as defined in section\t6.2.',
        "identifier": f'Use definition ID "{spelling}" as defined in section\t6.2.',
        "section": "Use the value as defined in Section 6.2.",
    }[subject]
    source = view()
    source = replace(
        source,
        text=text,
        pieces=(dict(source.pieces[0], end=len(text)),),
        items=(source.items[0], dict(source.items[1], text=text)),
    )
    pin = record_source_pin(native_source_frame(source, ()))
    start = text.index(spelling)
    anchor = dict(
        pin=pin,
        space="native",
        pointer="#/texts/1",
        precision="exact",
        start=start,
        end=start + len(spelling),
        source_piece=spelling,
    )
    anchor["anchor_id"] = anchor_identity(anchor)
    original = dict(
        kind="occurrence",
        semantic_type="structural.located_participant",
        operation_key="producer",
        item_key="section-mention",
        pin=pin,
        anchors=(anchor,),
        occurrence_id=occurrence_identity((anchor,)),
        value=source_value(
            dict(
                role="named_link_definition_subject",
                start=start,
                **({"definition_subject_kind": subject} if subject == "identifier" else {}),
                named_cue=dict(
                    scope="chapter",
                    kind="definition_reference",
                    resolution="target_selection_required",
                    designator="6.2",
                    cue=(text.index("as defined in"), text.index("section") - 1),
                ),
            )
            if quoted
            else dict(role="named_link_subject")
        ),
    )
    original["contribution_id"] = contribution_identity(original)

    def target(component, label):
        return ExtractedComponentTarget.model_validate(
            dict(
                reference=dict(
                    product_id="structural:source",
                    component_id=component,
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
                label=label,
                description=f"Definition of {label}",
                scope="chapter",
            )
        )

    wrong, right = (
        target("a" * 64, "Section 6.2"),
        target("b" * 64, spelling if quoted else "Expected definition"),
    )
    cfg = ContextualCandidateConfig(
        target_components=(wrong, right),
        relationship_constraints=(
            RelationshipConstraint("definition", ("defined-by",), "usage", "definition", "one"),
        ),
        source_product_digest=source.ref.native_product.content_digest,
        source_projection_digest=source.ref.projection_digest,
        scope="chapter",
        unique_target_budget=1,
    )

    def encoded(items, profile, **_kwargs):
        if not provider_available:
            raise OSError("controlled encoder failure")
        vectors = []
        for item in items:
            digest = "a" * 64
            vectors.append(
                EncodedVector(
                    identity(
                        "context-vector",
                        [
                            item.object_id,
                            item.source_binding,
                            profile.profile_id,
                            digest,
                            item.representation_digest,
                        ],
                    ),
                    item.object_id,
                    item.source_binding,
                    profile.profile_id,
                    digest,
                    (1.0,) + (0.0,) * (profile.dimension - 1),
                    item.representation_digest,
                )
            )
        return EncoderResult(profile.profile_id, (), tuple(vectors), ())

    def retrieve(**request):
        return fuse_candidates(
            occurrence_id=request["occurrence_id"],
            query=request["query"],
            inventory=request["inventory"],
            budget=1,
            lexical_query="Section 6.2",
            channels={
                "alias": (ChannelHit(wrong.reference.component_id, 1),),
                "dense": (ChannelHit(wrong.reference.component_id, 0.9),),
            },
        )

    looked_up = []

    def retained_component_section(reference, work_digest):
        # The native-owned port determines section from the target's other view.
        assert work_digest == pin["product_digest"]
        looked_up.append(reference.component_id)
        return "6.2" if reference == right.reference else "6.1"

    reader = SimpleNamespace(
        source_view=lambda _: source,
        source_result=lambda *_: dict(
            contributions=(original,), operation_version="10" if subject == "identifier" else "9"
        ),
        component_semantic_targets=lambda _: {
            t.reference.component_id: {
                "term": {"text": t.label},
                "content": {"text": t.description},
                "interpretation": "definition",
                "scope": "chapter",
            }
            for t in (wrong, right)
        },
        retained_component_section=retained_component_section,
        cached_contextual_vectors=lambda **_: (),
        contextual_candidates=retrieve,
        contextual_mutual_neighbors=lambda _: {"directed_ranks": [], "edges": []},
    )
    monkeypatch.setattr(
        "corpus_structure.methods.contextual_candidates.verify_encoder_implementation", lambda _: ()
    )
    monkeypatch.setattr("corpus_structure.methods.contextual_candidates.encode_contexts", encoded)
    ctx = SimpleNamespace(reader=reader, check_active=lambda: None)
    unit = SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, source.ref.id, source.ref.key))

    (result,) = method().run((unit,), cfg, ctx)
    assert set(looked_up) == {wrong.reference.component_id, right.reference.component_id}
    assert result.contribution_operations is not None
    primary, retrieval, selection = result.contribution_operations
    report = primary["contextual_enrichment"]
    (candidate,) = report["candidate_lists"]
    (winner,) = candidate["candidates"]
    (decision,) = report["relationship_decisions"]
    assert winner["target_id"] == right.reference.component_id
    if method is ContextualCandidatesWithNeighborhood and not quoted:
        assert decision["outcome"] == "insufficient_evidence"
        assert not decision.get("selected_edges")
    else:
        (edge,) = decision["selected_edges"]
        assert tuple(edge["member_target_ids"]) == (right.reference.component_id,)
        assert decision["outcome"] == "selected" and selection["outcome"] == "succeeded"
    if provider_available:
        assert candidate["query_vector_id"]
        assert retrieval["outcome"] == "succeeded"
    else:
        assert "query_vector_id" not in candidate and report["vectors"] == ()
        assert (
            retrieval["outcome"] == "limited"
            and "controlled encoder failure" in retrieval["reason"]
        )

    import json

    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.serve.contextual_witness_replay import verify_contextual_witness_closure

    stored = json.loads(
        canonical_bytes(
            {
                "origin_task_id": 8,
                "origin_unit_id": source.ref.id,
                "method": ContextualCandidates.name,
                "configuration": cfg.model_dump(mode="json"),
                "body": {
                    "source": source.ref.key,
                    "operation_version": method.version,
                    "contribution_operations": result.contribution_operations,
                    "contributions": result.contributions,
                },
            }
        )
    )

    def detached_relation(_root, _manifest, name):
        if name == "reports":
            return (stored,)
        return (
            {
                "source_view_id": source.ref.id,
                "ref": {"native_product": {"content_digest": pin["product_digest"]}},
                "context": {"items": source.items},
            },
        )

    monkeypatch.setattr(
        "corpus_structure.serve.review_bundle._detached_relation",
        detached_relation,
    )
    monkeypatch.setattr(
        "corpus_structure.serve.contextual_witness_replay._term_binding",
        lambda t, *_: (
            SimpleNamespace(native_content_digest=pin["product_digest"]),
            SimpleNamespace(text=t.label),
            "6.2" if t.reference == right.reference else "6.1",
        ),
    )
    monkeypatch.setattr(
        "corpus_structure.serve.contextual_witness_replay._section",
        lambda code, _term: code,
    )
    monkeypatch.setattr(
        "corpus_structure.serve.contextual_navigation.verify_detached_neighborhood",
        lambda *_args, **_kwargs: None,
    )
    verify_contextual_witness_closure(None, {"relations": {"reports": {}}})
    if quoted:
        (stored_decision,) = stored["body"]["contribution_operations"][0]["contextual_enrichment"][
            "relationship_decisions"
        ]
        stored_decision["outcome"] = "insufficient_evidence"
        with pytest.raises(ValueError, match="exact source-bound selection"):
            verify_contextual_witness_closure(None, {"relations": {"reports": {}}})
        stored_decision["outcome"] = "selected"
    stored_candidate = stored["body"]["contribution_operations"][0]["contextual_enrichment"][
        "candidate_lists"
    ][0]
    stored_candidate["channel_results"] = [
        ch for ch in stored_candidate["channel_results"] if ch["channel"] != "witness"
    ]
    with pytest.raises(ValueError, match="complete source population"):
        verify_contextual_witness_closure(None, {"relations": {"reports": {}}})


def test_detached_alias_matches_the_original_term_occurrence():
    from corpus_structure.serve.contextual_witness_replay import _term_alias

    pin = dict(native_product_task_id=4, product_key="organized", product_digest="digest")
    source = {
        "ref": {
            "native_product": {"task_id": 4, "product_key": "organized", "content_digest": "digest"}
        },
        "context": {
            "pieces": [{"kind": "native_text", "item_ref": "#/texts/3", "start": 50, "end": 80}]
        },
    }
    target = SimpleNamespace(scope="chapter", effective_version="1")
    term = SimpleNamespace(start=52, end=57, text="Event")
    named_term = dict(pin=pin, pointer="#/texts/3", start=2, end=7, source_piece="Event")
    alias = dict(pin=pin, pointer="#/texts/3", start=11, end=12, source_piece="E")
    edge = dict(scope="chapter", effective_version="1")
    assert _term_alias(target, term, source, (edge, (named_term, alias))) == "E"
    assert (
        _term_alias(target, term, source, (edge, (dict(named_term, start=15, end=20), alias)))
        is None
    )
    assert (
        _term_alias(target, term, source, (dict(edge, effective_version="2"), (named_term, alias)))
        is None
    )
