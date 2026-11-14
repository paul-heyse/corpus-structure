"""Shared controlled inputs and builders for contextual enrichment support."""

from corpus_structure.methods.contextual_embeddings import EncodedVector
from corpus_structure.semantic.contextual_links import (
    RelationKind,
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


def semantic_definition_meaning():
    source = dict(
        project_id="book",
        native_content_digest="a" * 64,
        native_product_key="native",
        projection_digest="b" * 64,
        recipe_digest="c" * 64,
        coordinate_version=2,
    )
    return dict(
        term=dict(
            source=source, start=0, end=4, text="Mean", scope="chapter5", parent="distribution"
        ),
        content=dict(
            source=source, start=8, end=15, text="average", scope="chapter5", parent="distribution"
        ),
        interpretation="definition",
        scope="chapter5",
    )


def definition_inventory(meanings, *, versions=None):
    targets = tuple(
        target_representation(
            key,
            "definition-component:" + key,
            "Mean",
            "average",
            scope="chapter5",
            effective_version=(versions or {}).get(key),
        )
        for key in meanings
    )
    return freeze_inventory(
        targets,
        source_selection="all-original-component-proposals",
        scope="chapter5",
        semantic_targets=meanings,
    )


def select_definition_origins(inv, witnesses):
    return select_relationships(
        candidates=candidates(inv),
        inventory=inv,
        source_binding="source",
        scope="chapter5",
        effective_version=None,
        constraints=(
            RelationshipConstraint(
                "definition-binding", ("defined-by",), "term", "definition", "one"
            ),
        ),
        witnesses=witnesses,
    )
