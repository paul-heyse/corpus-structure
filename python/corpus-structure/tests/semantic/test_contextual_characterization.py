"""Independently authored symbolic endpoints and structural inheritance boundaries."""

from hashlib import sha256
from types import SimpleNamespace
from typing import Any

import pytest
from methods.contextual_characterization_support import context_builder, context_product, dipo_reply
from methods.declared_primary_fixture import selected_source
from methods.native_evidence_support import native_source as native_source
from methods.native_evidence_support import profiles

from corpus_structure.semantic.construction_products import (
    interpreted_member_contracts,
    interpreted_product_value,
    validate_interpreted_product,
)
from corpus_structure.semantic.contextual_characterization import (
    ContextInput,
    ContextPart,
    ContextualLayer,
)


def symbolic_layer(case, *, conflicting=False):
    builder = context_builder(case)
    family = "construction.predication"
    body: dict[str, Any] = builder.inventory()
    body["coverage"] = [
        dict(
            family=family,
            operation="literal-symbolic-construction",
            profile="literal-fixture",
            eligible=case.primary.frame.value["selectors"],
            examined=case.primary.frame.value["selectors"],
            unexamined=[],
            availability="available",
            outcome="complete",
        )
    ]
    body["outcome"] = "complete"

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

    a, b, c, d = [
        builder.occurrence(case.primary.frame, row["start"], row["end"]) for row in case.words[:4]
    ]
    body["occurrences"] = list(builder.occurrences.values())
    body["annotations"] = []
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
    prepared, model = profiles()
    value = interpreted_product_value(
        case.primary.source, body, interpreted_member_contracts(prepared, model), ()
    )
    value["annotation_support"] = []
    value["formal_atom_support"] = []
    return validate_interpreted_product(
        prepared, model, value, case.primary.source, (), subject_context=case.primary.context
    )


def test_distinct_binders_host_and_attribution_keep_exact_original_term_endpoints(native_source):
    from corpus_structure.semantic.identity import canonical_bytes

    symbolic = symbolic_layer(native_source)
    product = context_product(native_source, dipo=dipo_reply(), products=(symbolic,))
    body = {**product.inventory(), "coverage": product.value["coverage"]}
    nodes = {a["local_id"]: a for a in body["annotations"]}

    def original(key):
        return nodes[key]["external_premises"][0]["member_id"]

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
    assert symbolic.inventory()["terms"][0]["local_id"] == "variable-a"
    assert not body["terms"]  # No second environment evaluator or rewritten symbolic result.
    assert not product.value["formal_proxy_support"]
    targets = {
        slot["owner"]: slot["target"] for slot in product.value["construction_proxy_support"]
    }
    assert targets
    for packet in product.value["members"]:
        if packet["member_id"] in targets:
            assert "external_premises" not in packet["body"]
            assert targets[packet["member_id"]] == {
                "variant": "member",
                "role": "constructions",
                "member_id": original(packet["member_id"]),
            }
            assert packet["member_id"] == (
                "context-proxy:" + sha256(canonical_bytes(targets[packet["member_id"]])).hexdigest()
            )


def test_incompatible_external_choices_do_not_erase_completed_native_evidence(native_source):
    symbolic = symbolic_layer(native_source, conflicting=True)
    original = symbolic.content
    product = context_product(native_source, dipo=dipo_reply(), products=(symbolic,))
    body = {**product.inventory(), "coverage": product.value["coverage"]}
    assert any(a["kind"] == "native.rst_node" for a in body["annotations"])
    assert (
        next(c for c in body["coverage"] if c["family"] == "context.binding")["outcome"]
        == "partial"
    )
    proxy = {
        a["external_premises"][0]["member_id"]: a["local_id"]
        for a in body["annotations"]
        if a.get("external_premises")
    }
    assert not any(
        r["role"] == "declared_binding_site" and r["owner"] == proxy["binder-a"]
        for r in body["roles"]
    )
    assert symbolic.content == original


def test_heading_qualifies_actual_list_group_and_quotation_blocks_outside_inheritance(
    native_source,
):
    text = "Heading.\nItemA.\n“ItemB.”"
    heading = dict(
        self_ref="#/texts/header",
        label="section_header",
        text="Heading.",
        orig="Heading.",
        parent={"$ref": "#/groups/section"},
    )
    first = dict(
        self_ref="#/texts/first",
        label="list_item",
        text="ItemA.",
        orig="ItemA.",
        parent={"$ref": "#/groups/list"},
    )
    quoted = dict(
        self_ref="#/texts/quoted",
        label="list_item",
        text="“ItemB.”",
        orig="“ItemB.”",
        parent={"$ref": "#/groups/list"},
    )
    source, view, context = selected_source(
        text,
        pieces=[
            dict(
                kind="native_text",
                source_field="text",
                item_ref=heading["self_ref"],
                start=0,
                end=8,
            ),
            dict(kind="synthetic_separator", start=8, end=9),
            dict(
                kind="native_text", source_field="text", item_ref=first["self_ref"], start=9, end=15
            ),
            dict(kind="synthetic_separator", start=15, end=16),
            dict(
                kind="native_text",
                source_field="text",
                item_ref=quoted["self_ref"],
                start=16,
                end=len(text),
            ),
        ],
        items=[
            heading,
            first,
            quoted,
            dict(self_ref="#/groups/list", label="list", parent={"$ref": "#/groups/section"}),
            dict(self_ref="#/groups/section", label="section"),
        ],
    )
    context = ContextInput.build([ContextPart(view, 0, len(text))], [])
    builder = ContextualLayer(
        source.value["source"], {"selectors": []}, {"key": "fixture"}, context
    )
    builder.structural()
    builder.hypotheses()
    body: dict[str, Any] = builder.inventory()
    body["coverage"] = builder.coverage_values()
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


def test_selected_native_contextual_proxy_graph_keeps_role_and_exact_original():
    from corpus_structure.semantic.data_operation_values import semantic_value
    from corpus_structure.semantic.data_product_reference import (
        DataProductReference,
        SemanticReference,
    )
    from corpus_structure.semantic.declared_formal_readings import (
        SelectedCharacterizationInventories,
    )

    operation = "text.contextual_native/source-native"
    variants = (
        ("formal", "formal_proxy_support", "context.evidence_site"),
        ("constructions", "construction_proxy_support", "context.symbolic_site"),
    )
    value = {"source": {}, "selectors": [], "members": []}
    parents, targets, inputs, members = {}, [], [], {}
    for position, (role, field, kind) in enumerate(variants):
        parent = role + ":original"
        parents[parent] = {"project_id": "project", "kind_contract": role}
        members[(parent, "overlapping-local-id")] = {
            "body": semantic_value(
                {"record_type": "term", "local_id": "overlapping-local-id", "kind": kind}
            )
        }
        inputs.append({"role": role, "product_id": parent, "position": position, "multiplicity": 1})
        targets.append(
            dict(
                output_role="result",
                path=f"/{field}/*/target",
                input_role=role,
                input_kind=role,
                variant="member",
            )
        )
        value[field] = [
            {
                "owner": role,
                "target": SemanticReference.member(role, "overlapping-local-id").values(),
            }
        ]
        value["members"].append(
            {
                "member_id": role,
                "body": {"record_type": "annotation", "local_id": role, "kind": kind},
            }
        )
    use = dict(id="use", derivation_id="episode", fate="fulfilled", selection={"inputs": inputs})
    output = dict(derivation_id="episode", product_id="contextual", role="result")
    definition = {
        "support_contract": {"reference_targets": targets},
        "input_roles": [
            {"name": role, "kind": role, "accepted_kind_contracts": [role]}
            for role, _, _ in variants
        ],
    }
    parents["contextual"] = {"canonical_body": semantic_value(value)}
    maps = {
        "ops.data_derivation_output": {"output": output},
        "ops.data_derivation_input": {
            pin["role"]: {"derivation_id": "episode", **pin} for pin in inputs
        },
        "ops.data_derivation": {"episode": {"release_id": "release", "request_id": "request"}},
        "ops.data_request": {"request": {"operation_id": operation}},
        "ops.demand_use": {"use": use},
        "sem.data_operation_definition": {("release", operation): definition},
        "kb.data_product": parents,
        "kb.data_product_member": members,
        "kb.data_product_partition": {},
        "sem.data_kind_contract": {role: {} for role, _, _ in variants},
    }

    def rows_for(relation, **criteria):
        return tuple(
            row
            for row in maps[relation].values()
            if all(row.get(field) == expected for field, expected in criteria.items())
        )

    inventories = SelectedCharacterizationInventories(
        parents,
        index=SimpleNamespace(mapping=lambda relation, _: maps[relation], rows_for=rows_for),
        cut=SimpleNamespace(record={"project_id": "project"}),
    )
    contextual = DataProductReference("contextual")
    expected = [
        {"product_id": role + ":original", "member_id": "overlapping-local-id"}
        for role, _, _ in variants
    ]

    def endpoints():
        return [
            row["external_premises"][0] for row in inventories[contextual].payload["annotations"]
        ]

    assert endpoints() == expected
    reused = {
        **use,
        "id": "reused-use",
        "selection": {
            "inputs": [{**inputs[0], "product_id": "formal:equal-meaning-replacement"}, inputs[1]]
        },
    }
    uses = maps["ops.demand_use"]
    uses["reused-use"] = reused
    assert endpoints() == expected
    uses["second-exact-use"] = {**use, "id": "second-exact-use"}
    assert endpoints() == expected
    del uses["use"], uses["second-exact-use"]
    with pytest.raises(ValueError, match="unavailable in any exact selected use"):
        endpoints()
    uses["other-reused-use"] = {
        **use,
        "id": "other-reused-use",
        "selection": {
            "inputs": [inputs[0], {**inputs[1], "product_id": "constructions:replacement"}]
        },
    }
    with pytest.raises(ValueError, match="unavailable in any exact selected use"):
        endpoints()

    # A historical receipt for the same output and parents cannot authorize
    # a path its own release never declared.
    old_derivation = "older-episode"
    maps["ops.data_derivation_output"] = {
        "older-output": {**output, "derivation_id": old_derivation},
        "output": output,
    }
    maps["ops.data_derivation"][old_derivation] = {
        "release_id": "older-release",
        "request_id": "request",
    }
    maps["sem.data_operation_definition"]["older-release", operation] = {
        **definition,
        "support_contract": {"reference_targets": []},
    }
    maps["ops.data_derivation_input"].update(
        {"older-" + pin["role"]: {"derivation_id": old_derivation, **pin} for pin in inputs}
    )
    uses["older-use"] = {**use, "id": "older-use", "derivation_id": old_derivation}
    with pytest.raises(ValueError, match="requires its one declared output target"):
        endpoints()
    uses["use"] = use
    assert endpoints() == expected
    del maps["ops.data_derivation_input"]["older-constructions"]
    assert endpoints() == expected

    parents["empty-contextual"] = {
        "canonical_body": semantic_value(
            {
                **value,
                "formal_proxy_support": [],
                "construction_proxy_support": [],
                "members": [],
            }
        )
    }
    assert inventories[DataProductReference("empty-contextual")].payload["annotations"] == []
