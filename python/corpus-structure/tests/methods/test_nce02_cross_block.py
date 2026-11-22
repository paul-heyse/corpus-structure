"""Cross-block attachments require a selected passage and an explicit native list."""

import pytest

from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.ingest.sentences import pipeline
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.structural_products import StructuralPassage
from methods.m1_source_preparation_support import prepare_declared_source, projection, source
from methods.scoped_relations_support import discover_relations


@pytest.mark.parametrize(
    "case",
    ["complete", "clipped", "wrong_group", "no_scope", "duplicate_children", "missing_parent"],
)
def test_explicit_list_intro_has_independent_located_hosts(case):
    intro = "For each of the following, assume that all inputs are valid:"
    text = f"{intro}\nThe analyst records the input.\nThe reviewer checks the result."
    view = source(text, labels=("text", "list_item", "list_item"))
    intro_node, first, second = [
        {**node, "content_layer": "body", "children": []} for node in view.items
    ]
    parent, group = "#/groups/1", "#/groups/2"
    actual_parent = "#/groups/missing" if case == "missing_parent" else parent

    def ref(pointer):
        return {"$ref": pointer}

    intro_node["parent"] = ref(actual_parent)
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
            parent=ref(actual_parent),
            children=[ref(first["self_ref"]), ref(second["self_ref"])]
            + ([ref(first["self_ref"])] if case == "duplicate_children" else []),
        ),
        first,
        second,
    )
    view = projection(view.text, pieces=view.pieces, items=nodes)
    native_items = {item["self_ref"]: item for item in view.value["items"]}
    assert native_items[intro_node["self_ref"]]["parent"] == actual_parent
    assert native_items[group]["children"] == (first["self_ref"], second["self_ref"]) + (
        (first["self_ref"],) if case == "duplicate_children" else ()
    )
    profile = AnnotationProfile()
    prepared = prepare_declared_source(view, profile=profile, annotations_only=True)
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
        view,
        annotations=prepared.annotations,
        annotation_native_profile=pipeline(AnnotationProfile().configuration).selection().native,
        passages=None if case == "no_scope" else (passage,),
        witnessed_links_enabled=True,
    )
    rows = {row["contribution_id"]: row for row in output["contributions"]}
    inherited = [
        row["component"]
        for row in rows.values()
        if row.get("component", {}).get("host_witness") is not None
    ]
    assert (
        len(inherited)
        == {
            "complete": 2,
            "clipped": 1,
            "wrong_group": 1,
            "no_scope": 0,
            "duplicate_children": 0,
            "missing_parent": 0,
        }[case]
    )
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
    for projected in projections:
        cue, host = projected["members"]
        (qualified,) = [
            row
            for row in rows.values()
            if row.get("component", {}).get("kind") == "predicate_qualifier"
            and tuple(row["members"][:2]) == (cue, host)
        ]
        assert qualified["contribution_id"] in projected["computation_dependencies"]


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
    view = source(text, labels=("text",))
    view = projection(
        view.text,
        pieces=view.pieces,
        items=tuple(dict(item, content_layer="body") for item in view.items),
    )
    prepared = prepare_declared_source(view, annotations_only=True)
    passage = StructuralPassage(
        passage_id="scope",
        scope="scope",
        source_ref="fixture",
        start=0,
        end=len(text),
        text=text,
    )
    output = discover_relations(
        view,
        annotations=prepared.annotations,
        annotation_native_profile=pipeline(AnnotationProfile().configuration).selection().native,
        passages=(passage,),
        witnessed_links_enabled=True,
    )
    rows = {row["contribution_id"]: row for row in output["contributions"]}
    hosts = tuple(
        prepared.annotations[0].tokens[rows[row["members"][1]]["component"]["predicate_token"]]
        for row in rows.values()
        if row.get("component", {}).get("attachment_kind") == "scope_inheritance"
    )
    assert tuple(text[token.start : token.end] for token in hosts) == expected_hosts


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("complete", ("first", "second")),
        ("clipped", ("first",)),
        ("wrong_group", ("first",)),
        ("duplicate_children", ()),
        ("missing_parent", ()),
        ("unselected_group", ()),
    ],
)
def test_current_pointer_columns_preserve_independent_cross_block_hosts(case, expected):
    """Literal typed linguistic columns test layout fidelity; no provider standing."""
    from dataclasses import replace
    from types import SimpleNamespace

    from corpus_structure.semantic.constructions.retained_rules import (
        CrossBlockTarget,
        recognize_cross_block,
    )
    from methods.structural_roles_support import annotation

    intro = "For each of the following, assume that all inputs are valid:"
    first, second = "The analyst records the input.", "The reviewer checks the result."
    text = "\n".join((intro, first, second))
    specifications = (
        ("For", "ADP", "prep", 6, "IN"),
        ("each", "DET", "pobj", 0, "DT"),
        ("of", "ADP", "prep", 1, "IN"),
        ("the", "DET", "det", 4, "DT"),
        ("following", "NOUN", "pobj", 2, "NN"),
        (",", "PUNCT", "punct", 6, ","),
        ("assume", "VERB", "ROOT", 6, "VB"),
        ("that", "SCONJ", "mark", 10, "IN"),
        ("all", "DET", "det", 9, "DT"),
        ("inputs", "NOUN", "nsubj", 10, "NNS"),
        ("are", "AUX", "ccomp", 6, "VBP"),
        ("valid", "ADJ", "acomp", 10, "JJ"),
        (":", "PUNCT", "punct", 6, ":"),
    )
    intro_product, _ = annotation(intro, specifications)
    products = [intro_product]
    for spelling, name, actor, action, object_ in (
        (first, "first", "analyst", "records", "input"),
        (second, "second", "reviewer", "checks", "result"),
    ):
        product, _ = annotation(
            spelling,
            (
                ("The", "DET", "det", 1, "DT"),
                (actor, "NOUN", "nsubj", 2, "NN"),
                (action, "VERB", "ROOT", 2, "VBZ"),
                ("the", "DET", "det", 4, "DT"),
                (object_, "NOUN", "dobj", 2, "NN"),
            ),
        )
        start = text.index(spelling)
        products.append(
            replace(
                product,
                block_id="#/texts/" + name,
                kind="list_item",
                block_start=start,
                block_end=start + len(spelling),
                tokens=tuple(
                    replace(token, start=start + token.start, end=start + token.end)
                    for token in product.tokens
                ),
            )
        )
    group, parent = "#/groups/list", "#/groups/section"
    intro_pointer = intro_product.block_id
    children = ["#/texts/first", "#/texts/second"] + (
        ["#/texts/first"] if case == "duplicate_children" else []
    )
    parent_pointer = "#/groups/unknown" if case == "missing_parent" else parent
    items = [
        dict(self_ref=intro_pointer, label="text", parent=parent_pointer, content_layer="body"),
        dict(
            self_ref=group,
            label="list",
            parent=parent_pointer,
            children=children,
            content_layer="body",
        ),
        dict(self_ref="#/texts/first", label="list_item", parent=group, content_layer="body"),
        dict(
            self_ref="#/texts/second",
            label="list_item",
            parent=parent if case == "wrong_group" else group,
            content_layer="body",
        ),
    ]
    ancestors: list[dict] = [dict(self_ref=parent, children=[intro_pointer, group])]
    if case == "unselected_group":
        ancestors.append(items.pop(1))
    pieces = [
        dict(item_ref=product.block_id, start=product.block_start, end=product.block_end)
        for product in products
    ]
    hosts = tuple(
        CrossBlockTarget(
            product.block_id.rsplit("/", 1)[-1],
            "reading",
            "described_process",
            "positive",
            product,
            2,
        )
        for product in products[1:]
    )
    (cue,) = tuple(
        recognize_cross_block(
            SimpleNamespace(text=text),
            products,
            SimpleNamespace(
                start=0, end=text.index(second) - 1 if case == "clipped" else len(text)
            ),
            hosts,
            (),
            dict(items=items, ancestors=ancestors),
            pieces,
        )
    )
    assert cue.cue.variant == "list_assumption"
    assert tuple(target.frame for target in cue.targets) == expected
    assert (
        text[cue.cue.span.extents[0][0] : cue.cue.span.extents[0][1]]
        == "assume that all inputs are valid"
    )
    assert cue.witness == (dict(kind="list_intro", list_group=group) if expected else None)
