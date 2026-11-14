"""Complete native inventories and scoped hypotheses, with independent meanings."""

from types import SimpleNamespace

import pytest

from corpus_structure.core.method import MethodSettings, UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.methods.contextual_characterization import (
    ContextualCharacterizationConfig,
    ContextualCharacterizationMethod,
    canonical_tokens,
    reuse_native,
)
from corpus_structure.semantic.characterization import decode_layer, encode_layer
from corpus_structure.semantic.contextual_characterization import (
    ContextInput,
    ContextPart,
    ContextualLayer,
)
from methods.contextual_characterization_support import (
    add_metadata as add_metadata,
)
from methods.contextual_characterization_support import (
    context_builder as context_builder,
)
from methods.contextual_characterization_support import (
    dipo_reply as dipo_reply,
)
from methods.native_evidence_support import builder_for, metadata
from methods.native_evidence_support import native_source as native_source
from methods.native_evidence_support import prepared as prepared


def legacy_dependencies(builder):
    from corpus_structure.semantic.characterization import LayerReport
    from corpus_structure.semantic.product_reference import ProductReference

    result: dict[ProductReference, LayerReport] = {}
    for pin, report in builder._dependencies.items():
        assert isinstance(pin, ProductReference) and isinstance(report, LayerReport)
        result[pin] = report
    return result


def token_population(source, builder, prepared):
    original, _ = builder_for(source, full=False)
    metadata(original)
    layer = original.finish(prepared)
    pin = layer.reference(77)
    builder.depend({pin: layer})
    return canonical_tokens(builder, {pin: layer}, pin.values()), pin, layer


def mention_reply(tokens):
    return dict(
        tokens=[t["text"] for t in tokens],
        mentions=[[0, 0], [1, 1], [2, 2], [3, 4]],
        clusters=[[[0, 0], [1, 1]]],
        mentions_subtokens=[[1, 1], [2, 2], [7, 8]],
        clusters_subtokens=[[[1, 1], [2, 2]]],
        unmapped_mentions=[dict(subtokens=[7, 8], reason="special_token_endpoint")],
    )


def test_detected_unassigned_raw_subtokens_and_complete_group_candidates_survive_codec(
    native_source, prepared
):
    builder = context_builder(native_source)
    tokens, _, _ = token_population(native_source, builder, prepared)
    builder.maverick(tokens, dict(sentences=builder.sentences(tokens)), mention_reply(tokens))
    builder.hypotheses()
    add_metadata(builder, ["maverick"])
    report = builder.finish(prepared, dependencies=builder._dependencies)
    body = decode_layer(
        prepared, encode_layer(report), dependencies=legacy_dependencies(builder)
    ).payload
    mentions = [a for a in body["annotations"] if a["kind"] == "native.mention"]
    assert len(mentions) == 4
    assert [
        (a["native_mention"]["first"], a["native_mention"]["last"])
        for a in mentions
        if not a["native_mention"]["clustered"]
    ] == [(2, 2), (3, 4)]
    unmapped = [a for a in body["annotations"] if a["kind"] == "native.unmapped_mention"]
    assert len(unmapped) == 3
    assert (
        next(a for a in unmapped if a["native_mention"]["first"] == 7)["native_mention"]["reason"]
        == "special_token_endpoint"
    )
    hypotheses = [a for a in body["annotations"] if a["kind"] == "contextual.referent_hypothesis"]
    assert len(hypotheses) == 2
    roles = [r for r in body["roles"] if r["role"] == "source_local_coreference_group_candidate"]
    assert len(roles) == 2 and len({r["member"] for r in roles}) == 1
    cluster = roles[0]["member"]
    assert (
        len(
            [
                m
                for m in body["memberships"]
                if m["group"] == cluster and m["role"] == "native_member"
            ]
        )
        == 2
    )
    assert all(r["basis"]["kind"] == "contextual_proposal" for r in roles)


def test_false_native_cluster_merge_and_cross_sentence_mention_are_explicit(
    native_source, prepared
):
    builder = context_builder(native_source)
    tokens, _, _ = token_population(native_source, builder, prepared)
    reply = mention_reply(tokens)
    invalid = dict(reply, clusters=[[[0, 0], [1, 1]], [[1, 1], [2, 2]]])
    with pytest.raises(ValueError, match="competing"):
        builder.maverick(tokens, dict(sentences=builder.sentences(tokens)), invalid)
    tokens[1]["sentence"] = ("different", "native", "sentence")
    reply = dict(
        reply,
        mentions=[[0, 1]],
        clusters=[],
        mentions_subtokens=[],
        clusters_subtokens=[],
        unmapped_mentions=[],
    )
    builder.maverick(tokens, dict(sentences=builder.sentences(tokens)), reply)
    member = next(a for a in builder.annotations if a["kind"] == "native.unmapped_mention")
    assert member["native_mention"]["mapping_status"] == "unmapped"
    assert "sentence" in member["native_mention"]["reason"]
    assert member["occurrences"] == builder.support


def test_raw_dipo_keeps_exact_edus_native_nuclearity_and_boundary_provenance(
    native_source, prepared
):
    builder = context_builder(native_source)
    builder.dipo(dict(text=builder.context.text, mode="learned"), dipo_reply())
    add_metadata(builder, ["dipo"])
    body = builder.finish(prepared).payload
    edus = [a for a in body["annotations"] if a["kind"] == "native.edu"]
    assert [
        (
            a["native_edu"]["provider_start"],
            a["native_edu"]["provider_end"],
            a["native_edu"]["text"],
        )
        for a in edus
    ] == [(0, 4, "X X"), (4, 14, "é x+y [3].")]
    rst = next(a for a in body["annotations"] if a["kind"] == "native.rst_node")
    assert (
        rst["native_label"] == "contingency-condition" and rst["native_rst"]["nuclearity"] == "SN"
    )
    assert [
        (m["order"], m["role"]) for m in body["memberships"] if m["group"] == rst["local_id"]
    ] == [(0, "satellite"), (1, "nucleus")]
    boundaries = [
        a["native_boundary"] for a in body["annotations"] if a["kind"] == "native.edu_boundary"
    ]
    assert boundaries == dipo_reply()["boundaries"]
    with pytest.raises(ValueError, match="raw-source"):
        builder.dipo(
            dict(text=builder.context.text, mode="supplied_edus"),
            dict(dipo_reply(), mode="supplied_edus"),
        )


def test_context_keeps_cross_page_selection_gaps_and_rejects_missing_source_piece(
    native_source, prepared
):
    view, base, scope, operation = native_source[3:]
    context = ContextInput.build([ContextPart(view, 0, 1), ContextPart(view, 2, 3)], [])
    assert context.text == "X\nX"
    assert context.gaps[0]["reason"] == "synthetic selection join; original crossing unexamined"
    builder = ContextualLayer(base, scope, operation, context)
    assert len(context.occurrences(builder, 0, 3)) == 2
    builder.structural()
    builder.hypotheses()
    body = builder.finish(prepared).payload
    assert (
        next(c for c in body["coverage"] if c["family"] == "context.reference")["outcome"]
        == "partial"
    )
    broken_view = SimpleNamespace(ref=view.ref, text=view.text, pieces=[])
    with pytest.raises(ValueError, match="not covered"):
        ContextualLayer(
            base, scope, operation, ContextInput.build([ContextPart(broken_view, 0, 3)], [])
        )


def test_retained_native_reuse_does_not_invoke_any_provider(native_source, prepared):
    native = context_builder(native_source)
    tokens, _, _ = token_population(native_source, native, prepared)
    native.maverick(tokens, dict(sentences=native.sentences(tokens)), mention_reply(tokens))
    native.dipo(dict(text=native.context.text), dipo_reply())
    native.hypotheses()
    add_metadata(native)
    report = native.finish(prepared, dependencies=native._dependencies)
    pin = report.reference(88)
    new = context_builder(native_source)
    new.depend({pin: report, **legacy_dependencies(native)})
    reuse_native(new, {pin: report})
    new.hypotheses()
    layer = new.finish(prepared, dependencies=new._dependencies)
    assert not layer.payload["native_runs"]
    old_coverage = {row["family"]: row["outcome"] for row in report.payload["coverage"]}
    new_coverage = {row["family"]: row["outcome"] for row in layer.payload["coverage"]}
    for family in ("maverick.mentions", "maverick.clusters", "dipo.edus", "dipo.rst"):
        assert old_coverage[family] == new_coverage[family] == "complete"
        original = {
            row["local_id"] for row in report.payload["annotations"] if row["family"] == family
        }
        retained = {
            ref["local_id"]
            for row in layer.payload["annotations"]
            if row["family"] == family
            for ref in row.get("external_premises", ())
            if ref["layer"] == pin.values()
        }
        assert retained == original
        assert all(
            row["status"] == "native_evidence"
            for row in layer.payload["annotations"]
            if row["family"] == family
        )
    original_members = {
        row["local_id"]
        for row in report.payload["memberships"]
        if row["family"] in {"maverick.clusters", "dipo.rst"}
    }
    retained_members = {
        ref["local_id"]
        for row in layer.payload["memberships"]
        for ref in row.get("external_premises", ())
    }
    assert original_members <= retained_members
    assert (
        len(
            [
                a
                for a in layer.payload["annotations"]
                if a["kind"] == "contextual.referent_hypothesis"
            ]
        )
        == 2
    )
    refs = [ref for a in layer.payload["annotations"] for ref in a.get("external_premises", ())]
    assert any(ref["layer"] == pin.values() for ref in refs)


def test_missing_native_evidence_cannot_become_empty_referent_or_host_inventory(
    native_source, prepared, tmp_path
):
    _, _, _, view, base, scope, operation = native_source
    reader = SimpleNamespace(
        prepared=prepared,
        source_views=lambda: [view.ref],
        source_view_ref=lambda _: view.ref,
        source_view=lambda _: view,
        characterization_layers=lambda _: {},
    )
    unit = SimpleNamespace(
        ref=UnitRef(TaskUnitType.DOCUMENT, 17), run=SimpleNamespace(reader=reader)
    )
    ctx = SimpleNamespace(
        check_active=lambda: None,
        characterization_operation=lambda _: dict(
            operation, key="text.contextual_characterization"
        ),
        settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
    )
    cfg = ContextualCharacterizationConfig(
        characterization_base_document=base,
        characterization_source_scope=scope,
        native_mode="retained",
    )
    (result,) = ContextualCharacterizationMethod().run([unit], cfg, ctx)
    assert result.characterization_layer is not None
    coverage = {c["family"]: c for c in result.characterization_layer.payload["coverage"]}
    assert coverage["maverick.mentions"]["outcome"] == "failed"
    assert coverage["context.reference"]["outcome"] == "partial"
    assert coverage["context.host"]["outcome"] == "partial"


@pytest.mark.parametrize("population", [1, 3, 4])
def test_contextual_evaluation_retains_one_group_candidate_per_mention(
    native_source, prepared, population
):
    from copy import deepcopy

    from corpus_structure.semantic.characterization import AnnotationReference, validate_layer
    from corpus_structure.semantic.constructions.evaluation import ContextualEvaluator, environment

    builder = context_builder(native_source)
    tokens, _, _ = token_population(native_source, builder, prepared)
    spans = [[index, index] for index in range(population)]
    builder.maverick(
        tokens,
        dict(sentences=builder.sentences(tokens)),
        dict(
            tokens=[token["text"] for token in tokens],
            mentions=spans,
            clusters=[spans],
            mentions_subtokens=[],
            clusters_subtokens=[],
            unmapped_mentions=[],
        ),
    )
    builder.hypotheses()
    add_metadata(builder, ["maverick"])
    native = builder.finish(prepared, dependencies=builder._dependencies)
    data = deepcopy(native.payload)
    mentions = [row for row in data["annotations"] if row["kind"] == "native.mention"]
    assert len(mentions) == population
    (cluster,) = [row for row in data["annotations"] if row["kind"] == "native.coreference_cluster"]
    # Literal symbolic participants carry each source mention's exact support;
    # recognition and native membership above are the real primary producers.
    data["terms"] = [
        dict(
            local_id=f"symbol-{index}",
            kind="participant",
            family="context.reference",
            vocabulary="literal-symbols",
            value=mention["native_label"],
            status="interpreted",
            occurrences=mention["occurrences"],
            premises=[mention["local_id"]],
            children=[],
        )
        for index, mention in enumerate(mentions)
    ]
    report = validate_layer(prepared, data, dependencies=legacy_dependencies(builder))
    pin = report.reference(89)
    evaluator = ContextualEvaluator({**legacy_dependencies(builder), pin: report})
    env = environment(context_layers=(pin,))
    roots = [AnnotationReference(pin, row["local_id"]) for row in data["terms"]]
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
    group_term = evaluator.terms[group_id]
    assert group_term["external_premises"] == [
        AnnotationReference(pin, cluster["local_id"]).values()
    ]
    assert group_term["occurrences"] == []
    assert group_term["status"] == "private_proposal"
    source_roles = {row["local_id"]: row for row in data["roles"]}
    mention_support = {
        key: mention["occurrences"] for key, mention in zip(evaluated, mentions, strict=True)
    }
    for relation in relations:
        (support,) = relation["basis"]["external_premises"]
        assert support["layer"] == pin.values()
        assert source_roles[support["local_id"]]["owner"] in {row["local_id"] for row in mentions}
        assert relation["occurrences"] == mention_support[relation["owner"]]
        assert len(relation["occurrences"]) < len(cluster["occurrences"])
        assert relation["basis"]["status"] == "private_proposal"

    # A different immutable selection can evaluate the same mention again while
    # the qualified group reference remains one shared, occurrence-free term.
    first_role = next(row for row in data["roles"] if row["owner"] == mentions[0]["local_id"])
    selected = environment(
        context_layers=(pin,), hypotheses=(AnnotationReference(pin, first_role["local_id"]),)
    )
    evaluator.evaluate(roots[0], selected)
    assert {row["member"] for row in evaluator.roles.values()} == {group_id}
    assert evaluator.terms[group_id]["occurrences"] == []
    evaluator.finish(
        prepared,
        data["source_scope"],
        dict(data["operation"], key="text.evaluate_context"),
        roots,
        env,
    )
