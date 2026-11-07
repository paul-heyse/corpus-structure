"""Cross-block attachments require a selected passage and an explicit native list."""

from dataclasses import replace
from hashlib import sha256

import pytest

from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.methods.scoped_relations import discover_relations
from corpus_structure.methods.source_preparation import prepare_source
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.structural_products import StructuralPassage

from .test_scoped_relations import complete_native_fields, source


@pytest.mark.parametrize("case", ["complete", "clipped", "wrong_group", "no_scope"])
def test_explicit_list_intro_has_independent_located_hosts(case):
    intro = "For each of the following, assume that all inputs are valid:"
    text = f"{intro}\nThe analyst records the input.\nThe reviewer checks the result."
    view = complete_native_fields(source(text, labels=("text", "list_item", "list_item")))
    intro_node, first, second = [
        {**node, "content_layer": "body", "children": []} for node in view.items
    ]
    parent, group = "#/groups/1", "#/groups/2"

    def ref(pointer):
        return {"$ref": pointer}

    intro_node["parent"] = ref(parent)
    first["parent"] = ref(group)
    second["parent"] = ref(parent if case == "wrong_group" else group)
    nodes = (
        dict(
            self_ref=parent,
            label="section",
            content_layer="body",
            children=[ref(intro_node["self_ref"]), ref(group)],
        ),
        intro_node,
        dict(
            self_ref=group,
            label="list",
            content_layer="body",
            parent=ref(parent),
            children=[ref(first["self_ref"]), ref(second["self_ref"])],
        ),
        first,
        second,
    )
    projection = dict(
        text=text,
        pieces=view.pieces,
        items=[node["self_ref"] for node in nodes],
        ancestors=[],
        health={},
    )
    view = replace(
        view,
        items=nodes,
        ref=replace(view.ref, projection_digest=sha256(canonical_bytes(projection)).hexdigest()),
    )
    profile = AnnotationProfile()
    prepared = prepare_source(view, profile=profile, annotations_only=True)
    assert not prepared.annotation_errors
    assert {a.block_id for a in prepared.annotations} == {"#/texts/0", "#/texts/1", "#/texts/2"}
    end = text.index("\nThe reviewer") if case == "clipped" else len(text)
    passage = StructuralPassage(
        passage_id="layout",
        scope="layout",
        source_ref="fixture",
        start=0,
        end=end,
        text=text[:end],
    )
    output = discover_relations(
        native_source_frame(view, ()),
        annotations=prepared.annotations,
        passages=None if case == "no_scope" else (passage,),
        predicate_version="3",
        witnessed_links_enabled=True,
        named_link_version="2",
    )
    rows = {row["contribution_id"]: row for row in output["contributions"]}
    inherited = [
        row["component"]
        for row in rows.values()
        if row.get("component", {}).get("host_witness") is not None
    ]
    assert len(inherited) == {"complete": 2, "clipped": 1, "wrong_group": 1, "no_scope": 0}[case]
    if inherited:
        cue_ids = {r["qualifier_contribution_id"] for r in inherited}
        (cue_id,) = cue_ids
        assert rows[cue_id]["component"]["cross_block_hosts"] == tuple(
            attachment["host_contribution_id"] for attachment in inherited
        )
        assert all(
            source_python(r["condition"])["text"] == "assume that all inputs are valid"
            and r["host_witness"] == {"kind": "list_intro", "list_group": group}
            for r in inherited
        )
    projections = [
        row
        for row in rows.values()
        if row.get("component", {}).get("attachment_kind") == "scope_inheritance"
    ]
    assert len(projections) == len(inherited)
    for projection in projections:
        cue, host = projection["members"]
        (qualified,) = [
            row
            for row in rows.values()
            if row.get("component", {}).get("kind") == "predicate_qualifier"
            and tuple(row["members"][:2]) == (cue, host)
        ]
        assert qualified["contribution_id"] in projection["computation_dependencies"]


@pytest.mark.parametrize(
    ("clause", "expected_hosts"),
    [
        ("we record the input and check the result", ("check",)),
        ("the analyst records the input and checks the result", ()),
        ("the analyst records the input and the reviewer checks the result", ()),
        ("the analyst records the input or checks the result", ()),
    ],
)
def test_scope_inheritance_requires_an_explicit_shared_clause(clause, expected_hosts):
    text = f"If the test succeeds, {clause}."
    view = complete_native_fields(source(text, labels=("text",)))
    view = replace(view, items=tuple(dict(item, content_layer="body") for item in view.items))
    prepared = prepare_source(view, annotations_only=True)
    passage = StructuralPassage(
        passage_id="scope",
        scope="scope",
        source_ref="fixture",
        start=0,
        end=len(text),
        text=text,
    )
    output = discover_relations(
        native_source_frame(view, ()),
        annotations=prepared.annotations,
        passages=(passage,),
        predicate_version="3",
        witnessed_links_enabled=True,
        named_link_version="2",
    )
    rows = {row["contribution_id"]: row for row in output["contributions"]}
    hosts = tuple(
        prepared.annotations[0].tokens[rows[row["members"][1]]["component"]["predicate_token"]]
        for row in rows.values()
        if row.get("component", {}).get("attachment_kind") == "scope_inheritance"
    )
    assert tuple(text[token.start : token.end] for token in hosts) == expected_hosts
