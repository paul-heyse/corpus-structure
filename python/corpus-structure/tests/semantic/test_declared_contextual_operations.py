"""Exact native ranking and current consumers over explicitly retained vector facts."""

from dataclasses import asdict
from pathlib import Path

import pytest

from corpus_structure.methods.contextual_embeddings import EncodedVector, EncoderProfile, identity
from corpus_structure.semantic.contextual_operations import (
    contextual_inputs,
    contextual_interpretation_candidates,
    contextual_inventory_values,
    contextual_operation_declarations,
    contextual_operation_sources,
    contextual_retrieval_values,
)
from corpus_structure.semantic.contextual_retrieval import freeze_inventory, target_representation
from corpus_structure.semantic.contextual_storage import lexical_target_rows
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.declared_structural_calls import structural_operation_declarations
from corpus_structure.semantic.observations import source_python, source_value
from corpus_structure.semantic.types import SourceArtifact, SourceBundle


def inputs():
    profile = EncoderProfile(
        "controlled-retained-vectors", "a" * 40, 2, "query: ", "passage: ", "mean"
    )
    targets = tuple(
        target_representation(key, "source:" + key, "alpha", "alpha " + key)
        for key in ("one", "two")
    )
    inventory = freeze_inventory(
        targets, source_selection="selected-authored-targets", scope="source-scope"
    )

    def vector(object_id, binding, representation, values):
        digest = identity(
            "context-vector",
            [object_id, binding, profile.profile_id, "actual-input", representation],
        )
        return EncodedVector(
            digest, object_id, binding, profile.profile_id, "actual-input", values, representation
        )

    query_vector = vector("occurrence", "source:original", "", (1.0, 0.0))
    vectors = (
        query_vector,
        *(
            vector(target.target_id, target.source_binding, target.representation_digest, values)
            for target, values in zip(targets, ((1.0, 0.0), (0.0, 1.0)), strict=True)
        ),
    )
    query = {
        "source_pin": {"source": "source:original"},
        "occurrence_id": "occurrence",
        "lexical_query": "alpha",
        "context": dict(
            recipe="lexical-native-1",
            report=source_value(None),
            rendered="",
            representation_digest="",
        ),
        "context_inputs": [],
        "query_vector_id": query_vector.vector_id,
        "anchors": ({"anchor_id": "original-relative-location"},),
    }
    policy = {
        "budget": 2,
        "channel_budget": 3,
        "constraints": source_value(
            [
                {
                    "constraint_id": "meaning",
                    "relation_kinds": ["denotes"],
                    "occurrence_role": "mention",
                    "target_role": "concept",
                    "multiplicity": "one",
                }
            ]
        ),
        "exclusions": source_value([]),
    }
    return {
        "query": query,
        "inventory": {"inventory": source_value(asdict(inventory))},
        "vectors": {
            "profile": source_value(asdict(profile)),
            "lexical_targets": source_value(lexical_target_rows(inventory)),
            "vectors": source_value([asdict(value) for value in vectors]),
        },
        "policy": policy,
    }


def test_contextual_retrieval_captures_factory_and_source_witness():
    root = Path(__file__).parents[2] / "src/corpus_structure/model/semantic"
    bundle = contextual_inputs(
        SourceBundle("core", (SourceArtifact("core", (root / "core.yaml").read_bytes()),))
    )
    model = compile_data_operations(
        bundle,
        declarations=(
            contextual_operation_declarations(),
            structural_operation_declarations(),
        ),
        python_sources=contextual_operation_sources(),
    )
    operation = model.operation("retrieve.contextual/declared")
    assert operation.capabilities.prepared_factory is not None
    assert len(operation.output_witnesses) == 1
    assert all(item.complete for item in model.implementation_slices), [
        (value.root, value.unknowns) for value in model.implementation_slices if not value.complete
    ]


def test_contextual_native_ranking_preserves_equal_labels_and_private_standing(native_rollback):
    product = contextual_retrieval_values(native_rollback.connection, **inputs())
    candidates = contextual_interpretation_candidates(product)
    assert [(value.target_id, value.label, value.rank) for value in candidates.targets] == [
        ("one", "alpha", 1),
        ("two", "alpha", 2),
    ]
    decision = source_python(product["relationship_decision"])
    assert decision["outcome"] == "insufficient_evidence"
    assert decision["selected_edges"] == []
    assert candidates.anchors == ({"anchor_id": "original-relative-location"},)


def test_contextual_retrieval_refuses_duplicate_or_foreign_vector_before_database():
    values = inputs()
    raw = source_python(values["vectors"]["vectors"])
    values["vectors"]["vectors"] = source_value([*raw, raw[0]])
    with pytest.raises(ValueError, match="membership"):
        contextual_retrieval_values(None, **values)
    values = inputs()
    raw = source_python(values["vectors"]["vectors"])
    raw[1]["representation_digest"] = "foreign-description"
    raw[1]["vector_id"] = identity(
        "context-vector",
        [
            raw[1]["object_id"],
            raw[1]["source_binding"],
            raw[1]["profile_id"],
            raw[1]["input_digest"],
            raw[1]["representation_digest"],
        ],
    )
    values["vectors"]["vectors"] = source_value(raw)
    with pytest.raises(ValueError, match="another representation"):
        contextual_retrieval_values(None, **values)


def test_contextual_inventory_freezes_explicit_targets_without_legacy_reader():
    targets = tuple(
        target_representation(key, "source:" + key, "alpha", "retained " + key, scope=scope)
        for key, scope in (("one", "selected"), ("two", "other"))
    )
    product = contextual_inventory_values(
        {
            "source_selection": "actual-authored-selection",
            "scope": "selected",
            "targets": source_value([asdict(value) for value in targets]),
            "semantic_targets": source_value({}),
        }
    )
    inventory = source_python(product["inventory"])
    assert [value["target_id"] for value in inventory["targets"]] == ["one"]
    assert inventory["source_selection"] == "actual-authored-selection"


def test_native_relationship_decoder_preserves_selected_target_carriers_and_rejects_absence():
    from corpus_structure.semantic.contextual_links import (
        RelationshipConstraint,
        RelationshipWitness,
        select_relationships,
    )
    from corpus_structure.semantic.contextual_operations import (
        admitted_contextual_inventory,
        contextual_relationship_binding,
    )
    from corpus_structure.semantic.contextual_retrieval import ChannelHit, fuse_candidates

    values = inputs()
    inventory = admitted_contextual_inventory(values["inventory"])
    candidates = fuse_candidates(
        occurrence_id="occurrence",
        query=None,
        inventory=inventory,
        channels={"witness": (ChannelHit("one", 1.0),)},
        budget=2,
        channel_budget=3,
    )
    witness = RelationshipWitness(
        "actual-supported-witness",
        "occurrence",
        "one",
        "denotes",
        "source:original",
        inventory.scope,
        None,
        ("actual-evidence",),
        "explicit_source_cue",
        "supported",
    )
    decision = select_relationships(
        candidates=candidates,
        inventory=inventory,
        source_binding="source:original",
        scope=inventory.scope,
        effective_version=None,
        constraints=(RelationshipConstraint("meaning", ("denotes",), "mention", "concept", "one"),),
        witnesses=(witness,),
    )
    assert len(decision.selected_edges) == 1
    product = {
        "version": "declared-contextual-retrieval-1",
        "source_pin": values["query"]["source_pin"],
        "anchors": values["query"]["anchors"],
        "inventory": values["inventory"]["inventory"],
        "candidate_list": source_value(asdict(candidates)),
        "relationship_decision": source_value(asdict(decision)),
    }
    selected = contextual_relationship_binding(
        product, decision_id=decision.decision_id, edge_id=decision.selected_edges[0].edge_id
    )
    assert selected.edge.relation == "denotes"
    assert [value.target_id for value in selected.representations] == ["one"]
    assert selected.source_pin == {"source": "source:original"}
    with pytest.raises(ValueError, match="actually selected edge"):
        contextual_relationship_binding(
            product, decision_id=decision.decision_id, edge_id="foreign"
        )
    with pytest.raises(ValueError, match="retained identity"):
        contextual_relationship_binding(
            product, decision_id="foreign", edge_id=decision.selected_edges[0].edge_id
        )


def test_current_definition_inventory_preserves_semantic_meaning_without_legacy_reference():
    from corpus_structure.semantic.contextual_operations import admitted_contextual_inventory

    target = target_representation(
        "actual-component",
        "current-native-product-and-member-reference",
        "alpha",
        "A source definition",
        type_name="definition",
        scope="selected",
    )
    meaning = {
        "term": "alpha",
        "content": "A source definition",
        "interpretation": "definition",
        "scope": "selected",
    }
    selection = {
        "source_selection": "actual-authored-target-selection",
        "scope": "selected",
        "targets": source_value([asdict(target)]),
        "semantic_targets": source_value({target.target_id: meaning}),
    }
    product = contextual_inventory_values(selection)
    inventory = admitted_contextual_inventory(product)
    assert inventory.semantic_groups[0].meaning == meaning
    assert inventory.targets[0].source_binding == "current-native-product-and-member-reference"
    selection["semantic_targets"] = source_value({})
    with pytest.raises(ValueError, match="actual selected semantic target meaning"):
        contextual_inventory_values(selection)
