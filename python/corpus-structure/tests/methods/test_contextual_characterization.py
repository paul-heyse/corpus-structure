"""Complete current contextual inventories retain native source hypotheses."""

import json
from dataclasses import replace

import pytest

from corpus_structure.semantic.contextual_characterization import (
    ContextInput,
    ContextPart,
    ContextualLayer,
)
from corpus_structure.semantic.identity import canonical_bytes
from methods.contextual_characterization_support import (
    canonical_tokens,
    context_builder,
    context_product,
    dipo_reply,
)
from methods.native_evidence_support import native_source as native_source


def mention_reply(tokens):
    return dict(
        tokens=[token["text"] for token in tokens],
        mentions=[[0, 0], [1, 1], [2, 2], [3, 4]],
        clusters=[[[0, 0], [1, 1]]],
        mentions_subtokens=[[1, 1], [2, 2], [7, 8]],
        clusters_subtokens=[[[1, 1], [2, 2]]],
        unmapped_mentions=[dict(subtokens=[7, 8], reason="special_token_endpoint")],
    )


def test_detected_unassigned_raw_subtokens_and_complete_group_candidates_survive_current_product(
    native_source,
):
    tokens = canonical_tokens(native_source, context_builder(native_source))
    product = context_product(native_source, maverick=mention_reply(tokens))
    # Revalidation exercises the current nominal codec without reconstructing a legacy report.
    _ = product.value
    body = product.inventory()
    mentions = [row for row in body["annotations"] if row["kind"] == "native.mention"]
    assert len(mentions) == 4
    assert [
        (row["native_mention"]["first"], row["native_mention"]["last"])
        for row in mentions
        if not row["native_mention"]["clustered"]
    ] == [(2, 2), (3, 4)]
    unmapped = [row for row in body["annotations"] if row["kind"] == "native.unmapped_mention"]
    assert len(unmapped) == 3
    assert (
        next(row for row in unmapped if row["native_mention"]["first"] == 7)["native_mention"][
            "reason"
        ]
        == "special_token_endpoint"
    )
    assert (
        len([row for row in body["annotations"] if row["kind"] == "contextual.referent_hypothesis"])
        == 2
    )
    roles = [
        row for row in body["roles"] if row["role"] == "source_local_coreference_group_candidate"
    ]
    assert len(roles) == 2 and len({row["member"] for row in roles}) == 1
    assert (
        len(
            [
                row
                for row in body["memberships"]
                if row["group"] == roles[0]["member"] and row["role"] == "native_member"
            ]
        )
        == 2
    )
    assert all(row["basis"]["kind"] == "contextual_proposal" for row in roles)
    assert all(
        "source_view_id" not in extent for row in body["occurrences"] for extent in row["extents"]
    )


def test_false_native_cluster_merge_and_cross_sentence_mention_are_explicit(native_source):
    builder = context_builder(native_source)
    tokens = canonical_tokens(native_source, builder)
    reply = mention_reply(tokens)
    with pytest.raises(ValueError, match="competing"):
        builder.maverick(
            tokens,
            dict(sentences=builder.sentences(tokens)),
            dict(reply, clusters=[[[0, 0], [1, 1]], [[1, 1], [2, 2]]]),
        )
    tokens[1]["sentence"] = "different-native-sentence"
    builder.maverick(
        tokens,
        dict(sentences=builder.sentences(tokens)),
        dict(
            reply,
            mentions=[[0, 1]],
            clusters=[],
            mentions_subtokens=[],
            clusters_subtokens=[],
            unmapped_mentions=[],
        ),
    )
    member = next(row for row in builder.annotations if row["kind"] == "native.unmapped_mention")
    assert member["native_mention"]["mapping_status"] == "unmapped"
    assert "sentence" in member["native_mention"]["reason"]
    assert member["occurrences"] == builder.support


def test_raw_dipo_keeps_exact_edus_native_nuclearity_and_boundary_provenance(native_source):
    product = context_product(native_source, dipo=dipo_reply())
    body = product.inventory()
    edus = [row for row in body["annotations"] if row["kind"] == "native.edu"]
    assert [
        (
            row["native_edu"]["provider_start"],
            row["native_edu"]["provider_end"],
            row["native_edu"]["text"],
        )
        for row in edus
    ] == [(0, 4, "X X"), (4, 14, "é x+y [3].")]
    rst = next(row for row in body["annotations"] if row["kind"] == "native.rst_node")
    assert (
        rst["native_label"] == "contingency-condition" and rst["native_rst"]["nuclearity"] == "SN"
    )
    assert [
        (row["order"], row["role"])
        for row in body["memberships"]
        if row["group"] == rst["local_id"]
    ] == [(0, "satellite"), (1, "nucleus")]
    assert [
        row["native_boundary"]
        for row in body["annotations"]
        if row["kind"] == "native.edu_boundary"
    ] == dipo_reply()["boundaries"]
    builder = context_builder(native_source)
    with pytest.raises(ValueError, match="raw-source"):
        builder.dipo(
            dict(text=builder.context.text, mode="supplied_edus"),
            dict(dipo_reply(), mode="supplied_edus"),
        )


def test_context_keeps_cross_page_selection_gaps_and_rejects_missing_source_piece(native_source):
    frame = native_source.primary.frame
    context = ContextInput.build([ContextPart(frame, 0, 1), ContextPart(frame, 2, 3)], [])
    assert context.text == "X\nX"
    assert context.gaps[0]["reason"] == "synthetic selection join; original crossing unexamined"
    builder = ContextualLayer(frame.value["source"], {"selectors": []}, {"key": "fixture"}, context)
    assert len(context.occurrences(builder, 0, 3)) == 2
    builder.structural()
    builder.hypotheses()
    assert (
        next(row for row in builder.coverage_values() if row["family"] == "context.reference")[
            "outcome"
        ]
        == "partial"
    )
    broken = replace(frame, source_content=canonical_bytes(dict(frame.value, pieces=[])).decode())
    with pytest.raises(ValueError, match="not covered"):
        ContextualLayer(
            frame.value["source"],
            {"selectors": []},
            {"key": "fixture"},
            ContextInput.build([ContextPart(broken, 0, 3)], []),
        )


def test_selected_native_observations_reuse_without_invoking_any_provider(native_source):
    tokens = canonical_tokens(native_source, context_builder(native_source))
    reply = mention_reply(tokens)
    original = context_product(native_source, maverick=reply, dipo=dipo_reply())
    reused = context_product(native_source, maverick=reply, dipo=dipo_reply())
    assert reused.semantic_id == original.semantic_id
    assert reused.content == original.content
    assert all(
        row["outcome"] == "complete"
        for row in json.loads(reused.content)["coverage"]
        if row["family"] in {"maverick.mentions", "maverick.clusters", "dipo.edus", "dipo.rst"}
    )


def test_missing_native_evidence_cannot_become_empty_referent_or_host_inventory(native_source):
    product = context_product(native_source)
    coverage = {row["family"]: row for row in json.loads(product.content)["coverage"]}
    assert coverage["maverick.mentions"]["outcome"] == "partial"
    assert coverage["context.reference"]["outcome"] == "partial"
    assert coverage["context.host"]["outcome"] == "partial"


@pytest.mark.parametrize("population", [1, 3, 4])
def test_contextual_evaluation_retains_one_group_candidate_per_mention(native_source, population):
    from corpus_structure.semantic.construction_products import (
        CharacterizationSnapshot,
        interpreted_member_contracts,
        interpreted_product_value,
        validate_interpreted_product,
    )
    from corpus_structure.semantic.constructions.evaluation import ContextualEvaluator, environment
    from corpus_structure.semantic.data_product_reference import member_reference
    from methods.native_evidence_support import profiles

    tokens = canonical_tokens(native_source, context_builder(native_source))
    spans = [[index, index] for index in range(population)]
    native = context_product(
        native_source,
        maverick=dict(
            tokens=[token["text"] for token in tokens],
            mentions=spans,
            clusters=[spans],
            mentions_subtokens=[],
            clusters_subtokens=[],
            unmapped_mentions=[],
        ),
    )
    data = native.inventory()
    mentions = [row for row in data["annotations"] if row["kind"] == "native.mention"]
    (cluster,) = [row for row in data["annotations"] if row["kind"] == "native.coreference_cluster"]
    prepared, model = profiles()
    # Independently authored literal participants preserve each native mention's support.
    facts = dict(
        occurrences=data["occurrences"],
        annotations=[],
        memberships=[],
        roles=[],
        choices=[],
        coverage=[
            dict(
                family="construction.predication",
                operation="literal-symbolic-construction",
                profile="literal-fixture",
                eligible=native_source.primary.source.value["selectors"],
                examined=native_source.primary.source.value["selectors"],
                unexamined=[],
                availability="available",
                outcome="complete",
            )
        ],
        outcome="complete",
        terms=[
            dict(
                local_id=f"symbol-{index}",
                kind="participant",
                family="construction.predication",
                vocabulary="literal-symbols",
                value=mention["native_label"],
                status="interpreted",
                occurrences=mention["occurrences"],
                children=[],
                external_premises=[
                    member_reference(native.reference, mention["local_id"]).values()
                ],
            )
            for index, mention in enumerate(mentions)
        ],
    )
    snapshot = CharacterizationSnapshot(native.semantic_id, native.content)
    value = interpreted_product_value(
        native_source.primary.source,
        facts,
        interpreted_member_contracts(prepared, model),
        (snapshot,),
    )
    symbolic = validate_interpreted_product(
        prepared,
        model,
        value,
        native_source.primary.source,
        (snapshot,),
        subject_context=native_source.primary.context,
    )
    evaluator = ContextualEvaluator.from_products(
        native_source.primary.source, (symbolic, snapshot), symbolic_products=(symbolic.reference,)
    )
    env = environment(context_layers=(native.reference,))
    roots = [member_reference(symbolic.reference, row["local_id"]) for row in facts["terms"]]
    evaluated = [evaluator.evaluate(root, env) for root in roots]
    relations = list(evaluator.roles.values())
    if population == 1:
        assert relations == []
        assert (
            "native cluster supplies no distinct source-local referent candidate"
            in evaluator.diagnostics
        )
        return
    assert len(relations) == population
    assert {row["owner"] for row in relations} == set(evaluated)
    assert {row["role"] for row in relations} == {"source-local-referent-group-candidate"}
    (group_id,) = {row["member"] for row in relations}
    group = evaluator.terms[group_id]
    assert group["external_premises"] == [
        member_reference(native.reference, cluster["local_id"]).values()
    ]
    assert group["occurrences"] == [] and group["status"] == "private_proposal"
    source_roles = {row["local_id"]: row for row in data["roles"]}
    support = {
        key: mention["occurrences"] for key, mention in zip(evaluated, mentions, strict=True)
    }
    for relation in relations:
        (premise,) = relation["basis"]["external_premises"]
        assert premise["product_id"] == native.semantic_id
        assert source_roles[premise["member_id"]]["owner"] in {row["local_id"] for row in mentions}
        assert relation["occurrences"] == support[relation["owner"]]
        assert len(relation["occurrences"]) < len(cluster["occurrences"])
        assert relation["basis"]["status"] == "private_proposal"
    first_role = next(row for row in data["roles"] if row["owner"] == mentions[0]["local_id"])
    selected = environment(
        context_layers=(native.reference,),
        hypotheses=(member_reference(native.reference, first_role["local_id"]),),
    )
    evaluator.evaluate(roots[0], selected)
    assert {row["member"] for row in evaluator.roles.values()} == {group_id}
    assert evaluator.terms[group_id]["occurrences"] == []
    evaluator.facts(
        {"selectors": native_source.primary.source.value["selectors"]},
        {"key": "text.evaluate_context"},
        roots,
        env,
    )
