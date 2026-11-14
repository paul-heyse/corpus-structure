"""Independently authored symbolic endpoints and structural inheritance boundaries."""

from types import SimpleNamespace

from methods.contextual_characterization_support import add_metadata, context_builder, dipo_reply
from methods.native_evidence_support import builder_for, metadata
from methods.native_evidence_support import native_source as native_source
from methods.native_evidence_support import prepared as prepared

from corpus_structure.semantic.characterization import validate_layer
from corpus_structure.semantic.contextual_characterization import (
    ContextInput,
    ContextPart,
    ContextualLayer,
)


def symbolic_layer(source, prepared, *, conflicting=False):
    builder, tokens = builder_for(source, full=False)
    metadata(builder)
    body = builder.finish(prepared).payload
    family = "construction.predication"
    body["operation"]["produced_families"].append(family)
    body["coverage"].append(
        dict(
            family=family,
            operation=body["operation"]["key"],
            eligible=source[5]["selectors"],
            examined=source[5]["selectors"],
            unexamined=[],
            availability="available",
            outcome="complete",
            profile="fixture-symbolic",
        )
    )

    def term(key, kind, value, occurrence, children=(), choices=()):
        return dict(
            local_id=key,
            kind=kind,
            value=value,
            vocabulary="independent-symbolic-fixture",
            status="interpreted",
            family=family,
            occurrences=[occurrence],
            children=list(children),
            required_choices=list(choices),
        )

    def edge(role, target):
        return dict(role=role, target=target, structural=True)

    a, b, c, d = [token["occurrence"] for token in tokens[:4]]
    body["terms"] = [
        term("variable-a", "participant", "X", a, choices=["choice-b"] if conflicting else []),
        term("variable-b", "participant", "X", b),
        term("restriction", "participant", "population", a),
        term("body", "predicate", "changes", c),
        term(
            "binder-a",
            "binder",
            "all",
            a,
            [
                edge("variable", "variable-a"),
                edge("restrictor", "restriction"),
                edge("body", "body"),
            ],
            ["choice-a"] if conflicting else [],
        ),
        term(
            "binder-b",
            "binder",
            "all",
            b,
            [
                edge("variable", "variable-b"),
                edge("restrictor", "restriction"),
                edge("body", "body"),
            ],
        ),
        term("operator", "operator", "condition", a),
        term("content", "predicate", "reported", d),
        term(
            "attribution",
            "attribution",
            "reported_by",
            c,
            [edge("source", "variable-a"), edge("content", "content")],
        ),
    ]
    body["choices"] = [
        dict(
            local_id="exclusive-site",
            family=family,
            compatibility="exclusive",
            members=[
                dict(local_id="choice-a", root="body"),
                dict(local_id="choice-b", root="content"),
            ],
        )
    ]
    return validate_layer(prepared, body)


def test_distinct_binders_host_and_attribution_keep_exact_original_term_endpoints(
    native_source, prepared
):
    symbolic = symbolic_layer(native_source, prepared)
    pin = symbolic.reference(123)
    builder = context_builder(native_source)
    builder.depend({pin: symbolic})
    builder.dipo(dict(text=builder.context.text), dipo_reply())
    builder.hypotheses()
    add_metadata(builder, ["dipo"])
    body = builder.finish(prepared, dependencies={pin: symbolic}).payload
    nodes = {a["local_id"]: a for a in body["annotations"]}

    def original(key):
        return nodes[key]["external_premises"][0]["local_id"]

    bindings = [
        (original(r["owner"]), original(r["member"]))
        for r in body["roles"]
        if r["role"] == "declared_binding_site"
    ]
    assert bindings == [("binder-a", "variable-a"), ("binder-b", "variable-b")]
    hosts = [
        (original(r["owner"]), original(r["member"]))
        for r in body["roles"]
        if r["role"] == "native_condition_host_candidate"
    ]
    assert ("operator", "body") in hosts
    attribution = [
        (r["role"], original(r["member"]))
        for r in body["roles"]
        if r["role"].startswith("attribution_")
    ]
    assert attribution == [("attribution_source", "variable-a"), ("attribution_content", "content")]
    assert all(r["basis"]["status"] == "private_proposal" for r in body["roles"])
    assert symbolic.payload["terms"][0]["local_id"] == "variable-a"
    assert not body["terms"]  # No second environment evaluator or rewritten symbolic result.


def test_incompatible_external_choices_do_not_erase_completed_native_evidence(
    native_source, prepared
):
    symbolic = symbolic_layer(native_source, prepared, conflicting=True)
    original = symbolic.content
    pin = symbolic.reference(123)
    builder = context_builder(native_source)
    builder.depend({pin: symbolic})
    builder.dipo(dict(text=builder.context.text), dipo_reply())
    builder.hypotheses()
    add_metadata(builder, ["dipo"])
    body = builder.finish(prepared, dependencies={pin: symbolic}).payload
    assert any(a["kind"] == "native.rst_node" for a in body["annotations"])
    assert (
        next(c for c in body["coverage"] if c["family"] == "context.binding")["outcome"]
        == "partial"
    )
    proxy = {
        a["external_premises"][0]["local_id"]: a["local_id"]
        for a in body["annotations"]
        if a.get("external_premises")
    }
    assert not any(
        r["role"] == "declared_binding_site" and r["owner"] == proxy["binder-a"]
        for r in body["roles"]
    )
    assert symbolic.content == original


def test_heading_qualifies_actual_list_group_and_quotation_blocks_outside_inheritance(
    native_source, prepared
):
    original, base, scope, operation = native_source[3:]
    text = "Heading.\nItemA.\n“ItemB.”"
    heading = dict(
        self_ref="#/texts/header", label="section_header", parent={"$ref": "#/groups/section"}
    )
    first = dict(self_ref="#/texts/first", label="list_item", parent={"$ref": "#/groups/list"})
    quoted = dict(self_ref="#/texts/quoted", label="list_item", parent={"$ref": "#/groups/list"})
    view = SimpleNamespace(
        ref=original.ref,
        text=text,
        pieces=[
            dict(kind="native_text", item_ref=heading["self_ref"], start=0, end=8),
            dict(kind="synthetic_separator", start=8, end=9),
            dict(kind="native_text", item_ref=first["self_ref"], start=9, end=15),
            dict(kind="synthetic_separator", start=15, end=16),
            dict(kind="native_text", item_ref=quoted["self_ref"], start=16, end=len(text)),
        ],
        items=[heading, first, quoted],
        ancestors=[
            dict(self_ref="#/groups/list", parent={"$ref": "#/groups/section"}),
            dict(self_ref="#/groups/section"),
        ],
    )
    context = ContextInput.build([ContextPart(view, 0, len(text))], [])
    builder = ContextualLayer(base, scope, operation, context)
    builder.structural()
    builder.hypotheses()
    body = builder.finish(prepared).payload
    inheritance = [r for r in body["roles"] if r["role"] == "heading_context"]
    assert len(inheritance) == 1
    nodes = {a["local_id"]: a for a in body["annotations"]}
    occurrences = {o["local_id"]: o for o in body["occurrences"]}
    owner = nodes[inheritance[0]["owner"]]
    assert [
        (e["start"], e["end"]) for oid in owner["occurrences"] for e in occurrences[oid]["extents"]
    ] == [(9, 15)]
    assert len([a for a in body["annotations"] if a["kind"] == "context.quotation"]) == 1
    assert (
        next(c for c in body["coverage"] if c["family"] == "context.inheritance")["outcome"]
        == "partial"
    )
