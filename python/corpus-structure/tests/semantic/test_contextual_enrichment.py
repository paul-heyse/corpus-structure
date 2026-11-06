"""Independent controls for context, candidate ranking and source-supported relationships."""

from dataclasses import replace
from math import sqrt
from threading import Event

import pytest
from sqlalchemy.dialects import postgresql

from corpus_structure.methods.contextual_embeddings import (
    E5,
    ContextInput,
    EncodedVector,
    EncoderCancelled,
    encode_contexts,
    identity,
    render_context,
    validate_vector,
)
from corpus_structure.semantic.contextual_links import (
    ProposalWitness,
    RelationKind,
    RelationshipWitness,
    RelationshipConstraint,
    select_relationships,
)
from corpus_structure.semantic.contextual_retrieval import (
    ChannelHit,
    freeze_inventory,
    fuse_candidates,
    target_representation,
)
from corpus_structure.semantic.contextual_storage import eligible_vector_relation, enrichment_report


def target(id_, **kw):
    return target_representation(id_, "source", "normal", "a distribution", **kw)


def query():
    return EncodedVector("v", "occ", "source", "p", "d", (1.0, 0.0))


def inventory(*targets):
    return freeze_inventory(
        targets or (target("a"), target("b")), source_selection="selected-source", scope="chapter5"
    )


def candidates(inv=None, channels=None):
    return fuse_candidates(
        occurrence_id="occ",
        query=query(),
        inventory=inv or inventory(),
        channels=channels or {"dense": (ChannelHit("a", 0.9), ChannelHit("b", 0.8))},
    )


def witness(id_="w", target_="a", relation: RelationKind = "defined-by", **kw):
    return RelationshipWitness(
        id_,
        "occ",
        target_,
        relation,
        "source",
        "chapter5",
        None,
        ("evidence",),
        "explicit_source_cue",
        **kw,
    )


def selection(c=None, inv=None, **kw):
    return select_relationships(
        candidates=c or candidates(),
        inventory=inv or inventory(),
        source_binding="source",
        scope="chapter5",
        effective_version=None,
        constraints=(RelationshipConstraint("sense", ("denotes", "alias-of", "defined-by"), "usage", "sense", "one"),
                   RelationshipConstraint("comparison", ("compared-with",), "subject", "comparator", "many"),
                   RelationshipConstraint("specialization", ("specializes",), "specialization", "parent", "many"),
                   RelationshipConstraint("participation", ("participates-in",), "participant", "process", "many")),
        **kw,
    )


def test_occurrence_preserved_at_end_and_prompts_counted():
    source = "x " * 100 + "\u03c3"
    item = ContextInput(
        "occ",
        "source",
        "query",
        "\u03c3",
        source,
        len(source) - 1,
        len(source),
        heading="normal",
        parent="distribution",
    )
    rendered = render_context(item, replace(E5, max_tokens=110), len)
    assert rendered.truncated
    assert "Mention: \u03c3" in rendered.text
    assert "Parent: distribution" in rendered.text
    assert "Heading: normal" in rendered.text
    assert len(E5.query_prompt + rendered.text) <= 110
    assert rendered.source_binding == "source"
    assert not rendered.text.startswith("query: ")


def test_mandatory_context_cannot_silently_truncate():
    item = ContextInput("occ", "source", "query", "normal", "normal", 0, 6, heading="long" * 100)
    with pytest.raises(ValueError, match="discriminating"):
        render_context(item, replace(E5, max_tokens=50), len)


def test_exact_source_correspondence_and_repeated_occurrence_identity():
    with pytest.raises(ValueError, match="exact source"):
        ContextInput("occ", "source", "query", "qs", "qs qs", 1, 3)
    first = ContextInput("occ1", "source", "query", "qs", "qs qs", 0, 2)
    second = replace(first, object_id="occ2", start=3, end=5)
    assert render_context(first, E5, len).object_id != render_context(second, E5, len).object_id


def test_operational_bound_repair_preserves_profile_identity():
    assert replace(E5, timeout_seconds=400, max_input_bytes=2000000).profile_id == E5.profile_id
    assert replace(E5, query_prompt="different: ").profile_id != E5.profile_id


@pytest.mark.parametrize(
    "values,dim", [((0, 0), 2), ((float("nan"), 1), 2), ((1, 0), 3), ((2, 0), 2)]
)
def test_invalid_vectors_refused(values, dim):
    with pytest.raises(ValueError):
        validate_vector(values, dim)


def test_normalized_float_vector_accepted():
    assert validate_vector((1 / sqrt(2), 1 / sqrt(2)), 2) == (1 / sqrt(2), 1 / sqrt(2))


def test_cancellation_prevents_model_allocation():
    event = Event()
    event.set()
    with pytest.raises(EncoderCancelled):
        encode_contexts((ContextInput("o", "s", "query", "x", "x", 0, 1),), cancel=event)


def test_inventory_unknown_type_preserves_plausible_targets_and_versions():
    inv = freeze_inventory(
        (
            target("a", type_name="distribution"),
            target("b"),
            target("c", type_name="procedure"),
            target("d", effective_version="v2"),
            target("e", scope="other"),
        ),
        source_selection="s",
        scope="chapter5",
        reliable_type="distribution",
    )
    assert inv.target_ids == ("a", "b", "d")
    assert inventory(target("a"), target("b")).target_ids == ("a", "b")
    assert inventory(target("a"), target("b")).inventory_id != inventory(target("a")).inventory_id


def test_same_label_never_merges_ids_and_duplicate_ids_refuse():
    assert inventory(target("a"), target("b")).target_ids == ("a", "b")
    with pytest.raises(ValueError, match="duplicate target"):
        inventory(target("a"), target("a"))


def test_rrf_deduplicates_by_target_and_keeps_raw_channel_evidence():
    result = candidates(
        channels={
            "alias": (ChannelHit("b", 1),),
            "lexical": (ChannelHit("a", 100), ChannelHit("b", 0.2)),
            "dense": (ChannelHit("b", 0.9), ChannelHit("a", 0.8)),
        }
    )
    assert [c.target_id for c in result.candidates] == ["b", "a"]
    assert result.candidates[0].fusion_score == pytest.approx(2 / 61 + 1 / 62)
    assert len(result.candidates[0].channels) == 3
    assert {e.channel: e.raw_score for e in result.candidates[1].channels}["lexical"] == 100


def test_equal_rank_ties_use_target_identity_and_unique_budget():
    result = fuse_candidates(
        occurrence_id="occ",
        query=query(),
        inventory=inventory(),
        budget=1,
        channels={
            "lexical": (ChannelHit("a", 1), ChannelHit("b", 0.5)),
            "dense": (ChannelHit("b", 1), ChannelHit("a", 0.5)),
        },
    )
    assert len(result.candidates) == 1
    assert result.candidates[0].target_id == "a"


@pytest.mark.parametrize(
    "hits",
    [
        (ChannelHit("a", 1), ChannelHit("a", 0.5)),
        (ChannelHit("foreign", 1),),
        (ChannelHit("a", float("inf")),),
    ],
)
def test_foreign_duplicate_or_nonfinite_channel_refused(hits):
    with pytest.raises(ValueError):
        candidates(channels={"dense": hits})


def test_similarity_only_produces_insufficient_evidence():
    decision = selection()
    assert decision.outcome == "insufficient_evidence"
    assert decision.selected_edges == ()


def test_distinct_relationships_and_ambiguity_survive():
    first = selection(witnesses=(witness(),))
    assert first.outcome == "partial"
    second = selection(witnesses=(witness(), witness("w2", "b", "compared-with")))
    assert second.outcome == "partial"
    assert {w.relation for w in second.selected_edges} == {"defined-by", "compared-with"}


def test_cannot_link_blocks_alias_without_erasing_comparison():
    decision = selection(
        witnesses=(witness(relation="alias-of"), witness("w2", relation="compared-with")),
        exclusions=frozenset({("occ", "a")}),
    )
    assert [w.relation for w in decision.selected_edges] == ["compared-with"]


def test_foreign_version_and_source_witness_refuse():
    for value in (
        replace(witness(), effective_version="v2"),
        replace(witness(), source_binding="foreign"),
    ):
        with pytest.raises(ValueError, match="differs"):
            selection(witnesses=(value,))


def test_novelty_requires_explicit_source_proposal_and_examined_inventory():
    inv, c = inventory(), candidates()
    proposal = ProposalWitness(
        "p",
        "occ",
        inv.inventory_id,
        "source",
        "chapter5",
        None,
        "local:1",
        "local_sense",
        ("a", "b"),
        ("evidence",),
        "source explicitly introduces a scoped sense",
    )
    assert selection(c, inv, proposal=proposal).outcome == "local_sense"
    with pytest.raises(ValueError, match="examined"):
        selection(c, inv, proposal=replace(proposal, examined_targets=("a",)))


def test_report_profiles_and_list_closure():
    vector = replace(query(), profile_id=E5.profile_id, values=(1.0,) + (0.0,) * 383)
    vector = replace(
        vector,
        vector_id=identity(
            "context-vector",
            [
                vector.object_id,
                vector.source_binding,
                vector.profile_id,
                vector.input_digest,
                vector.representation_digest,
            ],
        ),
    )
    report = enrichment_report(profiles=(E5,), vectors=(vector,))
    assert report["version"] == "contextual-enrichment-2"
    with pytest.raises(ValueError, match="unavailable"):
        enrichment_report(profiles=(E5,), vectors=(vector,), candidate_lists=(candidates(),))


def test_read_projection_is_task_bound_and_uses_native_vector_type():
    relation = eligible_vector_relation(7)
    sql = str(relation.select().compile(dialect=postgresql.dialect()))
    assert "task_id" in sql and "contextual_target_vector" in sql


def test_profile_versions_and_curated_descriptor_reuse_boundaries():
    from corpus_structure.semantic.contextual_registry import RegistryTarget, registry_input

    for changed in (
        replace(E5, sentence_transformers_version="changed-implementation"),
        replace(E5, transformers_version="changed-implementation"),
        replace(E5, torch_version="changed-implementation"),
        replace(E5, tokenizers_version="changed-implementation"),
    ):
        assert changed.profile_id != E5.profile_id
    first = RegistryTarget(target_id="a", label="normal", description="Gaussian distribution")
    second = RegistryTarget(target_id="b", label="Poisson", description="A count distribution")
    original_id, original = registry_input((first,))
    extended_id, extended = registry_input((first, second))
    assert original_id != extended_id
    assert original[0] == extended[0]
    changed_id, changed = registry_input(
        (replace_registry(first, description="changed description"),)
    )
    assert changed_id != original_id
    assert changed[0].representation_digest != original[0].representation_digest


def replace_registry(target, **changes):
    return type(target).model_validate(target.model_dump(mode="python") | changes)


def test_unknown_source_version_keeps_versions_but_refuses_unjustified_selection():
    targets = (
        target("a", effective_version="v1"),
        target("b", effective_version="v2"),
        target("generic"),
    )
    unknown = inventory(*targets)
    assert unknown.target_ids == ("a", "b", "generic")
    constraint = candidates(unknown, {"dense": (ChannelHit("a", 1.0), ChannelHit("b", 0.5))})
    result = selection(constraint, unknown, witnesses=(witness(target_="a"),))
    assert result.outcome == "insufficient_evidence"
    assert result.reason is not None
    assert "version is unestablished" in result.reason
    known = freeze_inventory(
        targets, source_selection="selected-source", scope="chapter5", effective_version="v1"
    )
    assert known.target_ids == ("a", "generic")


def test_exclusive_senses_do_not_hide_compatible_comparison():
    decision = selection(witnesses=(witness("sense-a", "a", "denotes"),
                                   witness("sense-b", "b", "denotes"),
                                   witness("compare", "a", "compared-with")))
    assert decision.outcome == "partial"
    assert [(e.member_target_ids, e.relation) for e in decision.selected_edges] == [(("a",), "compared-with")]
    assert len(decision.alternative_groups) == 1
    assert {(e.member_target_ids, e.relation) for e in decision.alternative_groups[0].edges} == {(("a",), "denotes"), (("b",), "denotes")}
    assert decision.alternative_groups[0].constraint_id == "sense"


def test_parallel_witnesses_are_one_edge_and_order_invariant():
    witnesses = (witness("first"), witness("second"))
    first = selection(witnesses=witnesses)
    second = selection(witnesses=tuple(reversed(witnesses)))
    assert first == second
    assert len(first.selected_edges) == 1
    assert {w.witness_id for w in first.selected_edges[0].witnesses} == {"first", "second"}
    assert first.selected_edges[0].selection == "preferred"
    assert first.selected_edges[0].witnesses[0].support_state == "unassessed"


def test_rejected_witness_inputs_remain_in_replay_population():
    original = witness("unsupported", support_state="unsupported")
    decision = selection(witnesses=(original,))
    assert decision.witnesses == (original,)
    assert not decision.selected_edges
    assert decision.outcome == "insufficient_evidence"


def test_component_target_preserves_authenticated_origin_not_curated_text():
    from corpus_structure.semantic.contextual_registry import (
        ExtractedComponentTarget,
        component_target_input,
    )

    target = ExtractedComponentTarget.model_validate(dict(
        reference=dict(product_id="structural:original", component_id="a" * 64,
                       operation_id="structure.definition_components", operation_version="1",
                       project_id="source-project", run_id=1, cut_id=2, release_id="source-release",
                       result_revision=0, selected_task_id=3, origin_task_id=4,
                       runtime_fingerprint="original-runtime", dependencies=("original-source",)),
        label="normal density", description="source-stated defining content", scope="chapter5",
    ))
    original_inventory, representations = component_target_input((target,))
    assert representations[0].target_id == "a" * 64
    assert representations[0].source_binding == "definition-component:" + target.reference.identity
    assert representations[0].label == "normal density"
    changed = target.model_copy(update={"description": "different text"})
    changed_inventory, changed_representations = component_target_input((changed,))
    assert changed_inventory != original_inventory
    assert changed_representations[0].representation_digest != representations[0].representation_digest
    with pytest.raises(ValueError):
        ExtractedComponentTarget.model_validate(target.model_dump() | {"reference": {"component_id": "a" * 64}})


def test_report_replays_complete_constraints_witnesses_and_selected_edges():
    inv = inventory()
    vectors = []
    for object_id, binding, representation in (("occ", "source", ""), *((t.target_id, t.source_binding, t.representation_digest) for t in inv.targets)):
        values = (1.,) + (0.,) * (E5.dimension - 1)
        vector = EncodedVector("", object_id, binding, E5.profile_id, "input", values, representation)
        vectors.append(replace(vector, vector_id=identity("context-vector", [object_id, binding, E5.profile_id, "input", representation])))
    candidate_list = fuse_candidates(occurrence_id="occ", query=vectors[0], inventory=inv,
                                     channels={"dense": (ChannelHit("a", 1.), ChannelHit("b", .5))})
    decision = selection(candidate_list, inv, witnesses=(witness("supported"), witness("refused", "b", support_state="unsupported")))
    report = enrichment_report(profiles=(E5,), vectors=vectors, inventories=(inv,), candidate_lists=(candidate_list,), relationship_decisions=(decision,))
    stored = report["relationship_decisions"][0]
    assert {w["witness_id"] for w in stored["witnesses"]} == {"supported", "refused"}
    assert stored["selected_edges"][0]["member_target_ids"] == ("a",)
    assert "alternatives" not in stored
    with pytest.raises(ValueError, match="selection semantics"):
        enrichment_report(profiles=(E5,), vectors=vectors, inventories=(inv,), candidate_lists=(candidate_list,), relationship_decisions=(replace(decision, selected_edges=()),))


def semantic_definition_meaning():
    source = dict(project_id="book", native_content_digest="a" * 64,
                  native_product_key="native", projection_digest="b" * 64,
                  recipe_digest="c" * 64, coordinate_version=2)
    return dict(term=dict(source=source, start=0, end=4, text="Mean", scope="chapter5", parent="distribution"),
                content=dict(source=source, start=8, end=15, text="average", scope="chapter5", parent="distribution"),
                interpretation="definition", scope="chapter5")


def definition_inventory(meanings, *, versions=None):
    targets = tuple(target_representation(key, "definition-component:" + key,
                    "Mean", "average", scope="chapter5",
                    effective_version=(versions or {}).get(key)) for key in meanings)
    return freeze_inventory(targets, source_selection="all-original-component-proposals", scope="chapter5", semantic_targets=meanings)


def select_definition_origins(inv, witnesses):
    return select_relationships(candidates=candidates(inv), inventory=inv,
        source_binding="source", scope="chapter5", effective_version=None,
        constraints=(RelationshipConstraint("definition-binding", ("defined-by",), "term", "definition", "one"),),
        witnesses=witnesses)


def test_same_source_meaning_different_producer_bases_corroborate_one_edge():
    from copy import deepcopy

    meaning = semantic_definition_meaning()
    inv = definition_inventory({"a": meaning, "b": deepcopy(meaning)})
    assert len(inv.semantic_groups) == 1
    assert inv.semantic_groups[0].member_target_ids == ("a", "b")
    a = witness("rule", "a")
    b = replace(witness("model", "b"), basis="model_reading")
    result = select_definition_origins(inv, (a, b))
    assert result.outcome == "selected" and not result.alternative_groups
    (edge,) = result.selected_edges
    assert edge.member_target_ids == ("a", "b")
    assert {w.basis for w in edge.witnesses} == {"explicit_source_cue", "model_reading"}
    assert edge.target_id == inv.semantic_groups[0].target_id
    assert select_definition_origins(inv, (b, a)) == result
    single = select_definition_origins(inv, (a,))
    assert single.selected_edges[0].edge_id == edge.edge_id
    assert single.decision_id != result.decision_id
    from corpus_structure.methods.contextual_candidates import relationship_contributions
    source = dict(contribution_id="located-role", item_key="retained-source-term",
                  pin={}, anchors=(), occurrence_id="occ")
    (single_observation,) = relationship_contributions(single, source, inv, "selection-operation")
    (corroborated_observation,) = relationship_contributions(result, source, inv, "selection-operation")
    assert single_observation["value"] == corroborated_observation["value"]
    assert single_observation["contribution_id"] != corroborated_observation["contribution_id"]
    assert single_observation["computation_dependencies"][2] == single.decision_id
    assert corroborated_observation["computation_dependencies"][2] == result.decision_id
    denied = select_definition_origins(inv, (a, replace(b, support_state="unsupported")))
    assert denied.selected_edges[0].member_target_ids == ("a",)
    assert len(denied.selected_edges[0].witnesses) == 1
    assert len(denied.witnesses) == 2


@pytest.mark.parametrize("difference", ["source", "content", "parent", "interpretation", "scope"])
def test_distinct_source_meanings_remain_competing_definition_edges(difference):
    from copy import deepcopy

    first = semantic_definition_meaning()
    second = deepcopy(first)
    if difference == "source":
        second["term"]["source"]["project_id"] = "another-book"
    elif difference == "content":
        second["content"].update(text="total", end=13)
    elif difference == "parent":
        second["term"]["parent"] = "another-parent"
    elif difference == "scope":
        second["term"]["scope"] = "another-scope"
    else:
        second["interpretation"] = "explanation"
    inv = definition_inventory({"a": first, "b": second})
    assert len(inv.semantic_groups) == 2
    result = select_definition_origins(inv, (witness("first", "a"), witness("second", "b")))
    assert result.outcome == "ambiguous" and not result.selected_edges
    assert len(result.alternative_groups[0].edges) == 2


def test_different_versions_keep_distinct_groups_and_unknown_version_withholds_selection():
    from copy import deepcopy

    first = semantic_definition_meaning() | {"effective_version": "v1"}
    second = deepcopy(first) | {"effective_version": "v2"}
    inv = definition_inventory({"a": first, "b": second}, versions={"a": "v1", "b": "v2"})
    assert len(inv.semantic_groups) == 2
    result = select_definition_origins(inv, (witness("first", "a"), witness("second", "b")))
    assert result.outcome == "insufficient_evidence"
    assert not result.selected_edges
    assert "version is unestablished" in result.reason
