"""Independent adversarial expectations for characterization assessment, no model calls."""

import json
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
EXTENT = dict(source_view_id=23, projection="c" * 64, native_pointer="#/texts/0", start=0, end=20)


















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
        output_key(dict(product_id=PIN["product_id"], collection="coverage", member_id="native.tokens"))[-1]
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




def test_named_binding_graph_alpha_renames_generated_refs_but_keeps_head_direction():
    def layer(prefix):
        def local(name):
            return prefix + name

        def ref(name):
            return dict(product_id=PIN["product_id"], member_id=local(name))

        occurrences = [
            dict(local_id=local(f"o{i}"), extents=[dict(EXTENT, start=i * 5, end=i * 5 + 1)])
            for i in (0, 1)
        ]
        tokens = [
            dict(
                local_id=local(f"token{i}"),
                kind="native_token",
                vocabulary="native",
                family="syntax",
                status="native_evidence",
                occurrences=[local(f"o{i}")],
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
        match = dict(
            local_id=local("match"),
            kind="named",
            vocabulary="source",
            family="syntax",
            status="interpreted",
            occurrences=[local("o0")],
            named_match=dict(
                rule=prefix + "rule",
                variant="default",
                mechanism="dependency",
                protocol="named-1",
                dependency_digest=prefix + "digest",
                native_container=ref("token0"),
                status="complete",
                bindings=[
                    dict(
                        role="subject",
                        node=prefix + "pattern",
                        head=ref("token0"),
                        members=[ref("token1")],
                        expansion="head",
                        status="complete",
                    )
                ],
            ),
        )
        return dict(
            occurrences=occurrences,
            annotations=[*tokens, match],
            memberships=[],
            roles=[],
            terms=[],
            choices=[],
            coverage=[],
        ), ref("match")

    left, root = layer("producer-")
    right, expected_root = layer("independent-")
    actual = LayerProjection(lambda _: left).project(
        dict(product_id=PIN["product_id"], collection="annotations", member_id=root["member_id"])
    )["graph"]
    expected = LayerProjection(lambda _: right).project(
        dict(product_id=PIN["product_id"], collection="annotations", member_id=expected_root["member_id"])
    )["graph"]
    assert graph_equal(actual, expected, "source_semantics")
    right["annotations"][-1]["named_match"]["bindings"][0]["head"] = dict(
        product_id=PIN["product_id"], member_id="independent-token1"
    )
    reversed_head = LayerProjection(lambda _: right).project(
        dict(product_id=PIN["product_id"], collection="annotations", member_id=expected_root["member_id"])
    )["graph"]
    assert not graph_equal(actual, reversed_head, "source_semantics")


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
    ).project(dict(product_id=PIN["product_id"], collection="annotations", member_id="independent-token"))["graph"]
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
                    dict(name="head", index=0, native_node=dict(product_id=PIN["product_id"], member_id=prefix + "t0"))
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
        dict(product_id=PIN["product_id"], collection="annotations", member_id="producer-navigation")
    )["graph"]
    expected = LayerProjection(lambda _: layer("independent-")).project(
        dict(product_id=PIN["product_id"], collection="annotations", member_id="independent-navigation")
    )["graph"]
    assert graph_equal(actual, expected, "source_semantics")
    assert not graph_equal(actual, expected, "native_fidelity")
    wrong = LayerProjection(lambda _: layer("independent-", subject=1)).project(
        dict(product_id=PIN["product_id"], collection="annotations", member_id="independent-navigation")
    )["graph"]
    assert not graph_equal(actual, wrong, "source_semantics")


















def test_author_witness_graph_enforces_budget_before_full_closure():
    body = {"terms": [dict(local_id="term", kind="predicate", value="x" * 100)]}
    with pytest.raises(ReferenceError, match="byte bound"):
        LayerProjection(lambda pin: body).graph(PIN, "term", max_bytes=32, witness_closure=True)


@pytest.mark.parametrize("provider,column,value", [
    ("spacy", "pos", "VERB"), ("spacy", "lemma", "run"),
    ("spacy", "dependency", "ROOT"), ("hanlp", "tag", "VBZ"),
    ("spacy", "morphology", {}),
])
def test_current_member_projection_preserves_native_column_provider_and_empty_value(provider, column, value):
    from corpus_structure.evaluate.characterization_assessment import _matches

    # Controlled transport values establish projection fidelity, not provider execution.
    native = dict(native_run="run", scheme="provider-native", **{column: value})
    body = dict(annotations=[dict(local_id="token", kind="native_token", native_token=native)],
                native_runs=[dict(local_id="run", provider=provider)])
    output = dict(product_id=PIN["product_id"], member_id="token", collection="annotations")
    actual = LayerProjection(lambda pin: body).project(output, include_graph=False)
    expected = dict(native_provider=provider, value=dict(native_token={column: value, "scheme": "provider-native"}))
    assert _matches(actual, expected)
    assert not _matches(actual, dict(native_provider="other-provider"))
    assert not _matches(actual, dict(value=dict(native_token=dict(scheme="other-scheme"))))
    del body["annotations"][0]["native_token"][column]
    absent = LayerProjection(lambda pin: body).project(output, include_graph=False)
    assert column not in absent["value"]["native_token"]
    assert not _matches(absent, expected)


def test_current_graph_semantics_keeps_label_independent_of_native_score():
    body = dict(annotations=[dict(local_id="token", kind="native_token", vocabulary="native",
                                native_label="VERB", scores=[dict(value=0.9)])])
    before = LayerProjection(lambda pin: body).graph(PIN, "token")
    body["annotations"][0]["scores"] = [dict(value=0.1)]
    changed_score = LayerProjection(lambda pin: body).graph(PIN, "token")
    assert graph_equal(before, changed_score, "source_semantics")
    assert not graph_equal(before, changed_score, "native_fidelity")
    body["annotations"][0]["native_label"] = "NOUN"
    changed_label = LayerProjection(lambda pin: body).graph(PIN, "token")
    assert not graph_equal(before, changed_label, "source_semantics")


def test_assessment_projection_refuses_old_task_addresses():
    from corpus_structure.evaluate.characterization_assessment import pin_key

    with pytest.raises(ReferenceError, match="current product"):
        pin_key(dict(task_id=7, product_key="layer", content_digest="a" * 64))
    with pytest.raises(ReferenceError, match="product/member"):
        output_key(dict(layer=PIN, local_id="token", collection="annotations"))
