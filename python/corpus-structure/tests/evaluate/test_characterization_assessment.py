"""Independent adversarial expectations for characterization assessment, no model calls."""

from copy import deepcopy
from typing import Any

import pytest

from corpus_structure.evaluate.characterization_assessment import (
    LayerProjection,
    graph_equal,
    output_key,
)
from corpus_structure.semantic.refusals import ReferenceError

PIN = {"product_id": "product:characterization-control"}
EXTENT = dict(projection="c" * 64, native_pointer="#/texts/0", start=0, end=20)


def graph() -> dict[str, Any]:
    return dict(
        root="choice",
        nodes=[
            dict(
                id="choice",
                value={"collection": "choices", "compatibility": "exclusive"},
                edges=[
                    {"label": "alternative", "target": "left", "position": 0},
                    {"label": "alternative", "target": "right", "position": 1},
                ],
            ),
            dict(
                id="left",
                value={"collection": "choice_member"},
                edges=[
                    {"label": "root", "target": "first"},
                    {"label": "required_choices", "target": "right", "position": 0},
                ],
            ),
            dict(
                id="right",
                value={"collection": "choice_member"},
                edges=[{"label": "root", "target": "second"}],
            ),
            dict(id="first", value={"kind": "operator", "value": "not"}, edges=[]),
            dict(id="second", value={"kind": "operator", "value": "not"}, edges=[]),
        ],
    )


def test_graph_alpha_renaming_preserves_independently_named_shared_identity():
    left = graph()
    right = deepcopy(left)
    names = {n["id"]: f"independent-{i}" for i, n in enumerate(right["nodes"])}
    right["root"] = names[right["root"]]
    for node in right["nodes"]:
        node["id"] = names[node["id"]]
        for edge in node["edges"]:
            edge["target"] = names[edge["target"]]
    assert graph_equal(left, right)


@pytest.mark.parametrize(
    "mutation", ("crossed", "merged", "unknown", "semantic_or", "role", "parallel")
)
def test_graph_comparison_refuses_lost_correlation_or_meaning(mutation):
    original, changed = graph(), graph()
    if mutation == "crossed":
        changed["nodes"][1]["edges"][1]["target"] = "left"
    elif mutation == "merged":
        changed["nodes"][2]["edges"][0]["target"] = "first"
        changed["nodes"].pop()
    elif mutation == "unknown":
        changed["nodes"][0]["value"]["compatibility"] = "unknown"
    elif mutation == "semantic_or":
        changed["nodes"][0]["value"] = {"kind": "operator", "value": "or"}
    elif mutation == "role":
        changed["nodes"][1]["edges"][0]["label"] = "participant"
    else:
        changed["nodes"][1]["edges"].append(dict(changed["nodes"][1]["edges"][0]))
    assert not graph_equal(original, changed)


def test_graph_projection_keeps_same_spelling_binders_distinct_and_linear():
    terms = [
        dict(
            local_id="root",
            kind="operator",
            value="and",
            children=[
                dict(role="left", target="one", structural=True, order=0),
                dict(role="right", target="two", structural=True, order=1),
            ],
        ),
        dict(local_id="one", kind="binder", value="x", children=[]),
        dict(local_id="two", kind="binder", value="x", children=[]),
    ]
    layer = {
        name: []
        for name in ("occurrences", "annotations", "memberships", "roles", "choices", "coverage")
    }
    layer["terms"] = terms
    actual = LayerProjection(lambda _: layer).project(
        dict(product_id=PIN["product_id"], collection="terms", member_id="root")
    )["graph"]
    assert isinstance(actual, dict)
    assert len(actual["nodes"]) == 3
    assert actual["nodes"][0]["edges"][0]["target"] != actual["nodes"][0]["edges"][1]["target"]
    assert (
        output_key(
            dict(product_id=PIN["product_id"], collection="coverage", member_id="native.tokens")
        )[-1]
        == "native.tokens"
    )


def test_semantic_graph_projection_is_frozen_and_ignores_incidental_evidence():
    actual = graph()
    for node in actual["nodes"]:
        node["value"]["collection"] = node["value"].get("collection", "terms")
        node["value"]["scores"] = [{"value": 0.7}]
        node["value"]["provenance"] = ["provider-specific-runtime"]
    expected = deepcopy(actual)
    for node in expected["nodes"]:
        node["value"].pop("scores")
        node["value"].pop("provenance")
    assert graph_equal(actual, expected, "source_semantics")
    assert not graph_equal(actual, expected, "native_fidelity")
    changed = deepcopy(expected)
    changed["nodes"][1]["edges"][1]["target"] = "left"
    assert not graph_equal(actual, changed, "source_semantics")


def test_semantic_graph_projection_preserves_scope_and_shared_binders():
    actual = graph()
    for node in actual["nodes"]:
        node["value"]["collection"] = node["value"].get("collection", "terms")
    changed = deepcopy(actual)
    changed["nodes"][2]["edges"][0]["target"] = "first"
    changed["nodes"].pop()
    assert not graph_equal(actual, changed, "source_semantics")
    changed = deepcopy(actual)
    changed["nodes"][3]["value"]["value"] = "every"
    assert not graph_equal(actual, changed, "source_semantics")


def test_source_graph_preserves_model_answer_but_ignores_request_and_scores():
    from corpus_structure.semantic.observations import source_value

    answer: dict[str, Any] = dict(
        family="character_modal_force_v1",
        question_key="force",
        stage="2",
        answer_kind="choice",
        state="proposed",
        declaration_digest="d" * 64,
        request_digest="a" * 64,
        candidate_list_digest="c" * 64,
        native_answer=source_value({"choice": "possible", "score": 0.7}),
        selected_keys=["possible"],
        alternatives=[dict(key="possible", state="proposed", score={"value": 0.7})],
    )
    actual: dict[str, Any] = dict(
        root="a",
        nodes=[
            dict(
                id="a",
                value={
                    "collection": "annotations",
                    "kind": "modal",
                    "status": "private_proposal",
                    "model_answer": answer,
                },
                edges=[],
            )
        ],
    )
    expected = deepcopy(actual)
    expected_answer = expected["nodes"][0]["value"]["model_answer"]
    for name in ("declaration_digest", "request_digest", "candidate_list_digest"):
        expected_answer.pop(name)
    expected_answer["native_answer"] = source_value({"choice": "possible"})
    expected_answer["alternatives"] = [dict(key="possible", state="proposed")]
    assert graph_equal(actual, expected, "source_semantics")
    assert not graph_equal(actual, expected, "native_fidelity")
    changed = deepcopy(expected)
    changed["nodes"][0]["value"]["model_answer"]["selected_keys"] = ["necessary"]
    assert not graph_equal(actual, changed, "source_semantics")


def test_source_graph_preserves_native_token_alignment_without_run_identity():
    token = dict(
        index=0,
        native_run="producer-run-1",
        container="doc-17",
        sentence="sentence-4",
        text="may",
        space=False,
        whitespace=" ",
        source_role="prose",
        pos="AUX",
        dependency="aux",
        native_head=1,
        head_index_base=0,
    )
    actual: dict[str, Any] = dict(
        root="token",
        nodes=[
            dict(
                id="token",
                value={"collection": "annotations", "kind": "native_token", "native_token": token},
                edges=[],
            )
        ],
    )
    expected = deepcopy(actual)
    details = expected["nodes"][0]["value"]["native_token"]
    for name in ("native_run", "container", "sentence"):
        details.pop(name)
    assert graph_equal(actual, expected, "source_semantics")
    assert not graph_equal(actual, expected, "native_fidelity")
    details["dependency"] = "subject"
    assert not graph_equal(actual, expected, "source_semantics")


def test_semantic_choice_and_prerequisite_order_is_not_incidental_identity():
    actual = graph()
    for node in actual["nodes"]:
        node["value"]["collection"] = node["value"].get("collection", "terms")
    expected = deepcopy(actual)
    expected["nodes"][0]["edges"].reverse()
    for position, edge in enumerate(expected["nodes"][0]["edges"]):
        edge["position"] = position
    assert graph_equal(actual, expected, "source_semantics")
    assert not graph_equal(actual, expected, "native_fidelity")
    crossed = deepcopy(expected)
    crossed["nodes"][1]["edges"][1]["target"] = "left"
    assert not graph_equal(actual, crossed, "source_semantics")


@pytest.fixture(scope="module")
def named_witness_case() -> dict[str, Any]:
    import json
    from unittest.mock import patch

    from annotation_support import ControlledPipeline, selected_item
    from methods.declared_primary_fixture import profiles, retained_source_annotations

    from corpus_structure.ingest.annotations import AnnotationProfile, annotate
    from corpus_structure.methods.annotation_rules import AnnotationRule
    from corpus_structure.semantic.construction_products import ConstructionOptions
    from corpus_structure.semantic.formal_products import FormalEvidenceOptions

    controlled = ControlledPipeline()
    request, source, frame, context = selected_item(
        controlled, "Mean is finite.", start=0, block_id="#/texts/1"
    )
    profile = AnnotationProfile(execution_profile=controlled.selection().native.fingerprint)
    with patch("corpus_structure.ingest.annotations.pipeline", return_value=controlled):
        (columns,) = annotate((request,), profile)
    native = retained_source_annotations(source, frame, context, (columns,), profile)
    formal, construction = profiles()
    primary = formal.run(source, FormalEvidenceOptions(), subject_context=context)
    rule = AnnotationRule(
        rule="copula",
        variant="is",
        mechanism="token",
        pattern=[{"TEXT": "is"}],
        bindings={"cue": {"node": "match"}},
    )
    product = construction.run(
        source,
        (primary,),
        ConstructionOptions(annotation_rules=(rule,)),
        sentences=native,
        subject_context=context,
    )
    products = {
        value.semantic_id: json.loads(value.content) for value in (primary, native, product)
    }
    match = next(
        packet["body"]
        for packet in products[product.semantic_id]["members"]
        if packet["body"].get("kind") == "construction.named_binding"
    )
    return dict(
        products=products,
        product=product.semantic_id,
        native=native.semantic_id,
        formal=primary.semantic_id,
        member=match["local_id"],
        block=request.block_id,
    )


def _named_witness(case):
    from corpus_structure.semantic.data_operation_identity import semantic_value
    from corpus_structure.semantic.data_product_reference import DataProductReference
    from corpus_structure.semantic.declared_formal_readings import (
        SelectedCharacterizationInventories,
    )

    records = {
        key: dict(canonical_body=semantic_value(value)) for key, value in case["products"].items()
    }
    inventories = SelectedCharacterizationInventories(records)
    projection = LayerProjection(
        lambda pin: inventories[DataProductReference(pin["product_id"])].payload
    )
    return projection.graph(dict(product_id=case["product"]), case["member"], witness_closure=True)


def test_named_witness_closes_actual_native_block_and_token_packets(named_witness_case):
    case = named_witness_case
    graph = _named_witness(case)
    nodes = {node["id"]: node for node in graph["nodes"]}
    root = nodes[graph["root"]]
    assert root["qualified_identity"] == dict(product_id=case["product"], member_id=case["member"])
    native = case["products"][case["native"]]
    (block,) = [p["body"] for p in native["members"] if p["body"]["record_type"] == "native_block"]
    (token,) = [
        p["body"]
        for p in native["members"]
        if p["body"]["record_type"] == "native_token"
        and (p["body"]["start"], p["body"]["end"]) == (5, 7)
    ]
    assert block["block_id"] == case["block"] and block["local_id"] != case["block"]
    match = next(
        p["body"]
        for p in case["products"][case["product"]]["members"]
        if p["member_id"] == case["member"]
    )
    assert match["named_match"]["native_container"] == dict(
        product_id=case["native"], block_id=case["block"]
    )

    # These expected relationships follow the declared rule and literal 'is' extent,
    # independently of the projection implementation.
    selected = {
        (
            edge["label"],
            edge.get("position"),
            tuple(sorted(nodes[edge["target"]]["qualified_identity"].items())),
        )
        for edge in root["edges"]
        if edge["label"] in {"named_match.native_container", "named_match.nodes"}
    }
    assert selected == {
        (
            "named_match.native_container",
            None,
            tuple(sorted(dict(product_id=case["native"], member_id=block["local_id"]).items())),
        ),
        (
            "named_match.nodes",
            0,
            tuple(sorted(dict(product_id=case["native"], member_id=token["local_id"]).items())),
        ),
    }
    (binding_edge,) = [edge for edge in root["edges"] if edge["label"] == "named_match.binding"]
    binding = nodes[binding_edge["target"]]
    assert binding["value"]["collection"] == "named_binding" and binding["value"]["role"] == "cue"
    assert {
        (
            edge["label"],
            edge.get("position"),
            nodes[edge["target"]]["qualified_identity"]["member_id"],
        )
        for edge in binding["edges"]
    } == {("head", None, token["local_id"]), ("members", 0, token["local_id"])}
    actual_native = [
        node
        for node in nodes.values()
        if node["qualified_identity"]["product_id"] == case["native"]
    ]
    assert {node["value"]["collection"] for node in actual_native} == {
        "native_block",
        "native_token",
    }
    for node in actual_native:
        original = next(
            p["body"]
            for p in native["members"]
            if p["member_id"] == node["qualified_identity"]["member_id"]
        )
        assert node["value"] == {
            "collection": original["record_type"],
            **{key: value for key, value in original.items() if key != "local_id"},
        }
        assert "lemma" not in node["value"]  # Position-only packets do not invent native columns.


def test_named_binding_graph_alpha_renames_generated_refs_but_keeps_head_direction(
    named_witness_case,
):
    actual = _named_witness(named_witness_case)
    expected = deepcopy(actual)
    names = {
        node["id"]: "independent-" + str(index) for index, node in enumerate(expected["nodes"])
    }
    expected["root"] = names[expected["root"]]
    for node in expected["nodes"]:
        node["id"] = names[node["id"]]
        for edge in node["edges"]:
            edge["target"] = names[edge["target"]]
    assert graph_equal(actual, expected, "source_semantics")
    binding = next(
        node for node in expected["nodes"] if node["value"]["collection"] == "named_binding"
    )
    head = next(edge for edge in binding["edges"] if edge["label"] == "head")
    token = next(node for node in expected["nodes"] if node["id"] == head["target"])
    binding["edges"].remove(head)
    token["edges"].append(dict(label="head", target=binding["id"]))
    assert not graph_equal(actual, expected, "source_semantics")


@pytest.mark.parametrize(
    "mutation",
    (
        "member_as_block",
        "wrong_block",
        "block_member_as_physical_id",
        "wrong_product",
        "missing_product",
        "undeclared_product",
        "foreign_source",
        "foreign_scope",
        "wrong_token_kind",
        "wrong_token_product",
        "ambiguous_block",
        "changed_member_identity",
    ),
)
def test_named_witness_refuses_foreign_or_ambiguous_native_closure(named_witness_case, mutation):
    from hashlib import sha256

    from corpus_structure.semantic.identity import canonical_bytes

    case = deepcopy(named_witness_case)
    product = case["products"][case["product"]]
    native = case["products"][case["native"]]
    match = next(
        p["body"]["named_match"] for p in product["members"] if p["member_id"] == case["member"]
    )
    block = next(p for p in native["members"] if p["body"]["record_type"] == "native_block")
    if mutation == "member_as_block":
        match["native_container"] = dict(product_id=case["native"], member_id=block["member_id"])
    elif mutation == "wrong_block":
        match["native_container"]["block_id"] = "#/texts/foreign"
    elif mutation == "block_member_as_physical_id":
        match["native_container"]["block_id"] = block["member_id"]
    elif mutation == "wrong_product":
        match["native_container"]["product_id"] = case["formal"]
    elif mutation == "missing_product":
        case["products"].pop(case["native"])
    elif mutation == "undeclared_product":
        product["dependencies"] = [
            ref for ref in product["dependencies"] if ref["product_id"] != case["native"]
        ]
    elif mutation == "foreign_source":
        native["source"]["document"] = "document:foreign"
    elif mutation == "foreign_scope":
        native["selectors"][0]["native_pointer"] = "#/texts/foreign"
    elif mutation == "wrong_token_kind":
        match["bindings"][0]["head"]["member_id"] = block["member_id"]
    elif mutation == "wrong_token_product":
        match["bindings"][0]["head"]["product_id"] = case["formal"]
    elif mutation == "ambiguous_block":
        other = deepcopy(block)
        other["body"]["end"] -= 1
        other["body"]["local_id"] = other["member_id"] = sha256(
            canonical_bytes(
                dict(
                    source=native["source"],
                    kind="block",
                    block_id=case["block"],
                    start=0,
                    end=other["body"]["end"],
                )
            )
        ).hexdigest()
        native["members"].append(other)
    elif mutation == "changed_member_identity":
        block["body"]["local_id"] = block["member_id"] = "not-the-source-owned-identity"
    with pytest.raises(ValueError):
        _named_witness(case)


def test_formal_graph_keeps_source_link_and_meaning_without_generated_input_ids():
    def layer(prefix, symbol="x", correspondence_source="primary"):
        occurrence = dict(local_id=prefix + "occurrence", extents=[dict(EXTENT, start=0, end=1)])
        other = dict(local_id=prefix + "other-occurrence", extents=[dict(EXTENT, start=5, end=6)])
        source = dict(
            local_id=prefix + "input",
            kind="formal_input",
            vocabulary="formal",
            family="formal",
            status="native_evidence",
            occurrences=[occurrence["local_id"]],
            formal_input=dict(
                parent_occurrence=occurrence["local_id"],
                representation="source_text",
                text="x",
                grammar="grammar-" + prefix,
                start_symbol="expression",
                macro_identity=prefix + "macro",
                syntax_outcome="complete",
                interpretation_outcome="not_requested",
                symbol_outcome="not_requested",
                correspondence=[
                    dict(
                        input_start=0,
                        input_end=1,
                        relation="exact",
                        source_occurrences=[
                            occurrence["local_id"]
                            if correspondence_source == "primary"
                            else other["local_id"]
                        ],
                    )
                ],
            ),
        )
        token = dict(
            local_id=prefix + "token",
            kind="formal_node",
            vocabulary="formal",
            family="formal",
            status="native_evidence",
            occurrences=[occurrence["local_id"]],
            formal=dict(
                input_id=source["local_id"],
                node_kind="token",
                rule="identifier",
                start=0,
                end=1,
                normalized=dict(kind="identifier", value=symbol, domain_status="not_requested"),
            ),
        )
        return dict(
            occurrences=[occurrence, other],
            annotations=[source, token],
            memberships=[],
            roles=[],
            terms=[],
            choices=[],
            coverage=[],
        )

    actual = LayerProjection(lambda _: layer("producer-")).project(
        dict(product_id=PIN["product_id"], collection="annotations", member_id="producer-token")
    )["graph"]
    expected = LayerProjection(lambda _: layer("independent-")).project(
        dict(product_id=PIN["product_id"], collection="annotations", member_id="independent-token")
    )["graph"]
    assert graph_equal(actual, expected, "source_semantics")
    wrong = LayerProjection(lambda _: layer("independent-", "y")).project(
        dict(product_id=PIN["product_id"], collection="annotations", member_id="independent-token")
    )["graph"]
    assert not graph_equal(actual, wrong, "source_semantics")
    wrong_correspondence = LayerProjection(
        lambda _: layer("independent-", correspondence_source="other")
    ).project(
        dict(product_id=PIN["product_id"], collection="annotations", member_id="independent-token")
    )["graph"]
    assert not graph_equal(actual, wrong_correspondence, "source_semantics")


def test_navigation_graph_lifts_real_role_token_and_source_label_references():
    def layer(prefix, subject=0):
        occurrences = [
            dict(local_id=prefix + f"o{i}", extents=[dict(EXTENT, start=i * 5, end=i * 5 + 1)])
            for i in (0, 1)
        ]
        tokens = [
            dict(
                local_id=prefix + f"t{i}",
                kind="native_token",
                vocabulary="native",
                family="syntax",
                status="native_evidence",
                occurrences=[prefix + f"o{i}"],
                native_token=dict(
                    index=i,
                    native_run=prefix + "run",
                    container=prefix + "container",
                    sentence=prefix + "sentence",
                    text="x",
                    space=False,
                    whitespace=" ",
                    source_role="prose",
                ),
            )
            for i in (0, 1)
        ]
        annotation = dict(
            local_id=prefix + "navigation",
            kind="navigation",
            vocabulary="source",
            family="syntax",
            status="interpreted",
            occurrences=[prefix + "o0"],
            navigation=dict(
                codec="source-navigation-v1",
                kind="named_link",
                pointer=EXTENT["native_pointer"],
                status="complete",
                rule=prefix + "compiled-rule",
                block=prefix + "block",
                roles=[
                    dict(role="subject", occurrences=[prefix + f"o{subject}"]),
                    dict(role="cue", occurrences=[prefix + "o1"]),
                ],
                native_tokens=[
                    dict(
                        name="head",
                        index=0,
                        native_node=dict(product_id=PIN["product_id"], member_id=prefix + "t0"),
                    )
                ],
                source_labels=[
                    dict(kind="numbering_namespace", value="Eq", occurrences=[prefix + "o0"])
                ],
            ),
        )
        return dict(
            occurrences=occurrences,
            annotations=[*tokens, annotation],
            memberships=[],
            roles=[],
            terms=[],
            choices=[],
            coverage=[],
        )

    actual = LayerProjection(lambda _: layer("producer-")).project(
        dict(
            product_id=PIN["product_id"], collection="annotations", member_id="producer-navigation"
        )
    )["graph"]
    expected = LayerProjection(lambda _: layer("independent-")).project(
        dict(
            product_id=PIN["product_id"],
            collection="annotations",
            member_id="independent-navigation",
        )
    )["graph"]
    assert graph_equal(actual, expected, "source_semantics")
    assert not graph_equal(actual, expected, "native_fidelity")
    wrong = LayerProjection(lambda _: layer("independent-", subject=1)).project(
        dict(
            product_id=PIN["product_id"],
            collection="annotations",
            member_id="independent-navigation",
        )
    )["graph"]
    assert not graph_equal(actual, wrong, "source_semantics")


def test_author_witness_graph_enforces_budget_before_full_closure():
    body = {"terms": [dict(local_id="term", kind="predicate", value="x" * 100)]}
    with pytest.raises(ReferenceError, match="byte bound"):
        LayerProjection(lambda pin: body).graph(PIN, "term", max_bytes=32, witness_closure=True)


def _selected_member_projection(annotations):
    from corpus_structure.semantic.data_operation_identity import semantic_value
    from corpus_structure.semantic.data_product_reference import DataProductReference
    from corpus_structure.semantic.declared_formal_readings import (
        SelectedCharacterizationInventories,
    )

    # Literal current member packets test retained reading, without an admission/provider claim.
    source = dict(document="document:control", projection="c" * 64)
    selectors = [dict(projection=source["projection"], native_pointer="#/texts/0")]
    body = dict(
        source=source,
        selectors=selectors,
        members=[
            dict(
                member_id=row["local_id"],
                kind_contract="kind:annotation-control",
                context=dict(
                    subject="original:control",
                    subject_definition="original-source-view",
                    original_source=source["document"],
                    analyzed_scope=dict(source=source, selectors=selectors),
                ),
                body=dict(record_type="annotation", **row),
            )
            for row in annotations
        ],
    )
    inventories = SelectedCharacterizationInventories(
        {PIN["product_id"]: dict(canonical_body=semantic_value(body))}
    )
    return LayerProjection(lambda pin: inventories[DataProductReference(pin["product_id"])].payload)


@pytest.mark.parametrize(
    "column,value",
    [
        ("pos", "VERB"),
        ("lemma", "run"),
        ("dependency", "ROOT"),
        ("tag", "VBZ"),
        ("morphology", []),
    ],
)
def test_current_member_projection_preserves_native_column_scheme_and_empty_value(column, value):
    from corpus_structure.evaluate.characterization_assessment import _matches

    native = dict(
        index=0,
        native_run="working-doc",
        container="block",
        text="runs",
        space=False,
        whitespace="",
        source_role="prose",
        **{column: value},
    )
    annotation = dict(
        local_id="token",
        kind="native.token",
        vocabulary="native",
        family="syntax",
        status="native_evidence",
        native_scheme="provider-native",
        native_token=native,
    )
    output = dict(product_id=PIN["product_id"], member_id="token", collection="annotations")
    actual = _selected_member_projection([annotation]).project(output, include_graph=False)
    expected = dict(value=dict(native_token={column: value}, native_scheme="provider-native"))
    assert _matches(actual, expected)
    assert actual["value"]["native_token"][column] == value
    assert not _matches(actual, dict(value=dict(native_scheme="other-scheme")))
    del native[column]
    absent = _selected_member_projection([annotation]).project(output, include_graph=False)
    assert column not in absent["value"]["native_token"]
    assert not _matches(absent, expected)


def test_current_graph_semantics_keeps_label_independent_of_native_score():
    annotation = dict(
        local_id="token",
        kind="native.token",
        vocabulary="native",
        native_label="VERB",
        scores=[dict(value=0.9)],
    )
    before = _selected_member_projection([annotation]).graph(PIN, "token")
    annotation["scores"] = [dict(value=0.1)]
    changed_score = _selected_member_projection([annotation]).graph(PIN, "token")
    assert graph_equal(before, changed_score, "source_semantics")
    assert not graph_equal(before, changed_score, "native_fidelity")
    annotation["native_label"] = "NOUN"
    changed_label = _selected_member_projection([annotation]).graph(PIN, "token")
    assert not graph_equal(before, changed_label, "source_semantics")


def test_assessment_projection_refuses_old_task_addresses():
    from corpus_structure.evaluate.characterization_assessment import pin_key

    with pytest.raises(ReferenceError, match="current product"):
        pin_key(dict(task_id=7, product_key="layer", content_digest="a" * 64))
    with pytest.raises(ReferenceError, match="product/member"):
        output_key(dict(layer=PIN, local_id="token", collection="annotations"))
