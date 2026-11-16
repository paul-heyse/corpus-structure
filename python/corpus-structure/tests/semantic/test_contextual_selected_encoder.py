"""Controlled encoder integration exercises real query12 projection without provider inference."""

from copy import deepcopy
from dataclasses import asdict, replace
from types import SimpleNamespace

import pytest
from methods.test_declared_contextual_query import POINTER, TEXT, primary, source

from corpus_structure.methods import contextual_embeddings as embeddings
from corpus_structure.semantic.contextual_encoder import (
    execute_contextual_encoder_kernel,
    prepare_selected_query_context,
)
from corpus_structure.semantic.contributions import occurrence_identity
from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.data_operation_model import (
    BoundRoleMember,
    ResolvedRoleBinding,
    SubjectContext,
)
from corpus_structure.semantic.data_operation_source_sets import (
    FrozenSourceSet,
    SourceSetEntry,
    source_sets_record,
)
from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
from corpus_structure.semantic.record_contracts import anchor_identity
from corpus_structure.semantic.source_contexts import record_source_pin


def case(recipe):
    frame = source()
    if recipe == "located-frame-2":
        layers, ref = primary(
            frame,
            dict(
                local_id="frame",
                kind="predicate",
                family="construction.source_readings",
                vocabulary="source-linguistic-rules-1",
                literals=["A supervisor approves the request."],
                children=[
                    dict(role="predicate", target="predicate"),
                    dict(role="direct_object", target="object"),
                ],
            ),
            [
                dict(local_id="predicate", literals=["approves"], status="interpreted"),
                dict(local_id="object", literals=["the request"], status="interpreted"),
            ],
        )
        focal, expected = "request", "Predicate: approves\nArgument direct_object: the request"
    elif recipe == "located-referent-2":
        layers, ref = primary(
            frame,
            dict(
                local_id="cluster",
                kind="native.coreference_cluster",
                family="maverick.clusters",
                literals=["A supervisor", "She"],
            ),
            [
                dict(
                    local_id="first",
                    kind="native.mention",
                    family="maverick.mentions",
                    literals=["A supervisor"],
                    native_mention=dict(first=0, last=1, mapping_status="mapped"),
                ),
                dict(
                    local_id="second",
                    kind="native.mention",
                    family="maverick.mentions",
                    literals=["She"],
                    native_mention=dict(first=6, last=6, mapping_status="mapped"),
                ),
            ],
            [
                dict(local_id="link1", group="cluster", member="first", order=0),
                dict(local_id="link2", group="cluster", member="second", order=1),
            ],
        )
        focal, expected = "She", "Earlier local mention: A supervisor"
    else:
        pieces = ["A supervisor approves the request.", "She files it.", "Archive it."]
        leaves = [
            dict(
                local_id=f"edu{i}",
                kind="native.edu",
                family="dipo.edus",
                literals=[piece],
                native_edu=dict(index=i),
            )
            for i, piece in enumerate(pieces)
        ]
        root = dict(
            local_id="root",
            kind="native.rst_node",
            family="dipo.rst",
            native_label="elaboration",
            literals=pieces,
            native_rst=dict(left_start=0, left_end=1, right_start=1, right_end=3, nuclearity="NS"),
        )
        right = dict(
            local_id="right",
            kind="native.rst_node",
            family="dipo.rst",
            native_label="joint",
            literals=pieces[1:],
            native_rst=dict(left_start=1, left_end=2, right_start=2, right_end=3, nuclearity="NN"),
        )
        memberships = [
            dict(local_id=str(i), group=group, member=member, order=order)
            for i, (group, member, order) in enumerate(
                (
                    ("root", "edu0", 0),
                    ("root", "right", 1),
                    ("right", "edu1", 0),
                    ("right", "edu2", 1),
                )
            )
        ]
        layers, ref = primary(frame, root, [right, *leaves], memberships)
        focal, expected = "files", "Discourse neighbor: Archive it."
    payload = layers[ref.product].payload
    packets = [
        dict(
            member_id=row["local_id"],
            kind_contract="kind:" + tag,
            context={},
            body=dict(row, record_type=tag),
        )
        for collection, tag in (
            ("occurrences", "occurrence"),
            ("annotations", "annotation"),
            ("memberships", "membership"),
            ("terms", "term"),
        )
        for row in payload[collection]
    ]
    body = dict(
        source=payload["source"], selectors=payload["selectors"], members=packets, dependencies=[]
    )
    start = TEXT.index(focal)
    anchor = dict(
        pin=record_source_pin(frame),
        space="native",
        pointer=POINTER,
        precision="exact",
        start=start,
        end=start + len(focal),
        source_piece=focal,
    )
    anchor["anchor_id"] = anchor_identity(anchor)
    occurrence = dict(
        kind="occurrence",
        semantic_type="contextual.located_mention",
        contribution_id="source-contribution:" + "a" * 64,
        operation_key="operation:actual-source",
        occurrence_id=occurrence_identity((anchor,)),
        pin=record_source_pin(frame),
        anchors=[anchor],
    )
    context = SubjectContext(
        "project:A", "source:A", "document:A", b"{}", subject_definition="original-source-view"
    )
    member = BoundRoleMember(
        ref.product.product_id,
        "kind:primary",
        context.subject,
        context.original_source,
        context.analyzed_scope,
        b"{}",
        ("episode:primary",),
        b"{}",
        subject_definition="original-source-view",
        position=0,
        support_references=tuple(
            ComputationalSupportReference(derivation_id=episode) for episode in ("episode:primary",)
        ),
    )
    sources = source_sets_record(
        (
            FrozenSourceSet(
                "query-context-primary",
                (SourceSetEntry.from_semantic_source(ref.product, context=context),),
            ),
        )
    )
    binding = SimpleNamespace(
        roles=(ResolvedRoleBinding("primary", "present", (member,)),),
        source_sets=json_bytes(sources),
        subject_context=context,
    )
    return frame, occurrence, (body,), binding, ref, expected


@pytest.mark.parametrize(
    "recipe", ["located-frame-2", "located-referent-2", "located-discourse-neighbor-2"]
)
def test_selected_encoder_uses_exact_shared_recipe_and_vector_identity(recipe, monkeypatch):
    frame, occurrence, primary, binding, evidence, expected = case(recipe)
    context, inputs = prepare_selected_query_context(
        frame, occurrence, primary, binding=binding, recipe=recipe, evidence=evidence.values()
    )
    assert context["rendered"] == expected
    assert inputs[0]["product_id"] == "product:primary" and json_loads(inputs[0]["reference"]) == [
        "product:primary",
        None,
    ]
    calls = []

    def encode(role):
        def call(texts, **kwargs):
            calls.append((role, texts))
            return [(1.0, 0.0)] * len(texts)

        return call

    model = SimpleNamespace(
        tokenizer=SimpleNamespace(encode=lambda text, **k: tuple(text)),
        encode_query=encode("query"),
        encode_document=encode("document"),
    )
    monkeypatch.setattr(
        embeddings, "_owned_cpu_encoder", lambda *a: (model, (("controlled", "1"),), ())
    )
    profile = embeddings.EncoderProfile(
        "controlled-query12", "a" * 40, 2, "query: ", "document: ", "mean"
    )
    result = execute_contextual_encoder_kernel(
        frame.record,
        occurrence,
        asdict(profile),
        "",
        (),
        check_active=lambda: None,
        query_context_record=context,
        context_inputs=inputs,
    )
    assert expected in calls[0][1][0]
    assert result["query"]["context"] == context
    vector = result["vector"]["vector"]
    assert vector["representation_digest"] == context["representation_digest"]
    lexical = execute_contextual_encoder_kernel(
        frame.record,
        occurrence,
        asdict(profile),
        "",
        (),
        check_active=lambda: None,
    )
    assert lexical["query"]["context"]["recipe"] == "lexical-native-1"
    lexical_vector = lexical["vector"]["vector"]
    assert lexical_vector["vector_id"] != vector["vector_id"]


def test_requested_context_refuses_wrong_member_source_dependency_and_missing_population():
    recipe = "located-frame-2"
    frame, occurrence, primary, binding, evidence, _ = case(recipe)
    for refs, match in (
        (dict(product_id="product:primary", member_id="absent"), "absent"),
        (dict(product_id="product:foreign", member_id="frame"), "closure"),
    ):
        with pytest.raises(ValueError, match=match):
            prepare_selected_query_context(
                frame, occurrence, primary, binding=binding, recipe=recipe, evidence=refs
            )
    changed = deepcopy(primary)
    changed[0]["source"]["document"] = "document:wrong"
    with pytest.raises(ValueError, match="source/scope"):
        prepare_selected_query_context(
            frame, occurrence, changed, binding=binding, recipe=recipe, evidence=evidence.values()
        )
    changed = deepcopy(primary)
    changed[0]["dependencies"] = [dict(product_id="product:missing")]
    with pytest.raises(ValueError, match="closure"):
        prepare_selected_query_context(
            frame, occurrence, changed, binding=binding, recipe=recipe, evidence=evidence.values()
        )
    with pytest.raises(ValueError, match="binding"):
        prepare_selected_query_context(
            frame, occurrence, (), binding=binding, recipe=recipe, evidence=evidence.values()
        )


@pytest.mark.parametrize("failure", ["missing", "empty"])
def test_named_context_failure_precedes_cpu_dispatch_and_model_allocation(
    failure, monkeypatch, tmp_path
):
    from corpus_structure.semantic import data_operation_cpu
    from corpus_structure.semantic.contextual_encoder import (
        ContextualEncoderPlan,
        ContextualEncoderSelection,
    )
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource

    frame, occurrence, primary, binding, evidence, _ = case("located-frame-2")
    if failure == "empty":
        primary = deepcopy(primary)
        next(row["body"] for row in primary[0]["members"] if row["member_id"] == "predicate")[
            "occurrences"
        ] = []

    def refuse(*a, **k):
        raise AssertionError("unavailable requested context reached execution")

    monkeypatch.setattr(data_operation_cpu, "plan_cpu_call", refuse)
    monkeypatch.setattr(embeddings, "_owned_cpu_encoder", refuse)
    monkeypatch.setattr(
        DeclaredNativeFrameSource, "acquire", classmethod(lambda cls, *a, **k: frame)
    )

    class Prepared:
        def validate_json(self, kind, content):
            return SimpleNamespace(model_dump=lambda **k: json_loads(content))

    source_member = replace(
        binding.roles[0].members[0],
        product="product:source",
        member="member:source",
        kind_contract="kind:source",
    )
    binding.roles = (*binding.roles, ResolvedRoleBinding("source", "present", (source_member,)))
    arguments = SimpleNamespace(
        arguments=dict(
            source=frame.value,
            occurrence=occurrence,
            inventory={},
            primary=() if failure == "missing" else primary,
            context_selection=dict(recipe="located-frame-2", evidence=evidence.values()),
        )
    )
    profile = embeddings.EncoderProfile(
        "controlled-query12", "a" * 40, 2, "query: ", "document: ", "mean"
    )
    plan = ContextualEncoderPlan(
        Prepared(), ContextualEncoderSelection(profile, tmp_path, ()), selected_context=True
    )
    with pytest.raises(ValueError, match="binding" if failure == "missing" else "lexical fallback"):
        next(
            plan.plan(
                arguments, binding=binding, check_active=lambda: None, execution_owner=object()
            )
        )


def test_retrieval_refuses_query_vector_from_another_context_before_relation_allocation():
    from corpus_structure.semantic.contextual_operations import prepare_contextual_retrieval
    from semantic.test_declared_contextual_operations import inputs

    selected = inputs()
    selected["query"]["context"]["representation_digest"] = "different-selected-context"
    with pytest.raises(ValueError, match="retained source occurrence"):
        prepare_contextual_retrieval(**selected)
