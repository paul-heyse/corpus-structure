"""Portable source projection replay over the exact selected native closure."""

from __future__ import annotations

import json
import re
from hashlib import sha256

from sqlalchemy import select

from corpus_structure.ingest.pdf_hierarchy import project_section_nodes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.pdf_record_reader import published_record_reader
from corpus_structure.semantic.releases import open_release

_COMPLETE_INVENTORY_RECIPE = "native-section-text-v10"
_SECTIONS = {"section", "chapter"}


def _outside_children(nodes, members):
    return {
        child["$ref"]
        for pointer in members
        for child in nodes[pointer].get("children", ())
        if child["$ref"] not in nodes
    }


def capture_source_projection(connection, source, budget):
    """Carry only the policy and excluded frontier needed to replay this selected view."""
    view, artifact, document = map(table, ("kb.source_view", "kb.source_artifact", "kb.document"))
    query = (
        select(view.c.release_id, document.c.content_hash, artifact.c.content)
        .join_from(view, artifact, view.c.recipe_digest == artifact.c.artifact_digest)
        .join_from(view, document, view.c.document_id == document.c.id)
        .where(view.c.id == source.ref.id)
    )
    budget.preflight(connection, query)
    release_id, original_digest, raw = connection.execute(query).one()
    recipe = bytes(raw)
    budget.value(recipe)
    if sha256(recipe).hexdigest() != source.ref.recipe_digest:
        raise ValueError("review source recipe differs from its retained identity")
    if json.loads(recipe).get("recipe") != _COMPLETE_INVENTORY_RECIPE:
        return None
    nodes = {item["self_ref"]: item for item in (*source.items, *source.ancestors)}
    frontier = sorted(_outside_children(nodes, (item["self_ref"] for item in source.items)))
    excluded = {}
    if frontier:
        reader = published_record_reader(
            connection,
            source.ref.native_product,
            projection_context=open_release(connection, release_id),
            read_budget=budget,
        )
        if reader is None or reader.revision["source_digest"] != original_digest:
            raise ValueError("review source frontier lacks its qualified published original")
        excluded = reader.selected_native_items(frontier)
    return dict(recipe=recipe.decode(), original_digest=original_digest, excluded=excluded)


def verify_source_projection(value):
    """Independently rederive current ordered pieces from the supplied native members."""
    evidence = value.get("projection_inputs")
    if evidence is None:
        if value.get("source_coverage") == "selected_projection_replay":
            raise ValueError("review source projection replay inputs are missing")
        return None
    ref, context = value["ref"], value["context"]
    recipe = evidence["recipe"].encode()
    policy = json.loads(recipe)
    original = evidence["original_digest"]
    if (
        sha256(recipe).hexdigest() != ref["recipe_digest"]
        or policy.get("recipe") != _COMPLETE_INVENTORY_RECIPE
        or policy.get("organization_owner") != ref["native_product"]
        or policy.get("analysis_eligible") is not ref["analysis_eligible"]
        or not isinstance(original, str)
        or re.fullmatch("[0-9a-f]{64}", original) is None
    ):
        raise ValueError("review source projection policy or original pin differs")
    selected = tuple(item["self_ref"] for item in context["items"])
    ancestry = tuple(item["self_ref"] for item in context["ancestors"])
    nodes = {item["self_ref"]: item for item in (*context["items"], *context["ancestors"])}
    excluded = evidence["excluded"]
    if len(nodes) != len(selected) + len(ancestry) or set(excluded) != _outside_children(
        nodes, selected
    ):
        raise ValueError("review source projection frontier differs from its exact closure")
    direct = ref["membership"] == "direct"
    if any(
        node["self_ref"] != pointer
        or (
            node.get("content_layer", "body") == "body"
            and not (direct and node["label"] in _SECTIONS)
        )
        for pointer, node in excluded.items()
    ):
        raise ValueError("review source projection frontier includes an eligible occurrence")
    nodes.update(excluded)
    projection = project_section_nodes(
        nodes,
        ref["native_product"]["content_digest"],
        ref["section_pointer"],
        "direct" if direct else "descendant",
        section_refs=frozenset(
            pointer
            for pointer, node in nodes.items()
            if pointer == "#/body" or node.get("label") in _SECTIONS
        ),
        selected_items=selected,
        projection_policy=recipe,
        original_digest=original,
    )
    if (
        projection.text != value["text"]
        or [p.to_wire() for p in projection.pieces] != context["pieces"]
    ):
        raise ValueError(
            "review source field address inventory differs from selected native occurrences"
        )
    return original
