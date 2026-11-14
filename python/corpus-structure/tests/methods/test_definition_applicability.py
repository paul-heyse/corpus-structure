"""Independent endpoint, role and compatibility controls; no mocked efficacy claims."""

from dataclasses import asdict, replace
from itertools import pairwise
from typing import Literal

import pytest

from corpus_structure.methods.annotation_rules import AnnotationRuleMatch, LocatedRole
from corpus_structure.methods.definition_applicability import (
    ApplicabilityCandidate,
    DefinitionApplicabilityConfig,
    DefinitionApplicabilityMethod,
    DefinitionComponentsConfig,
    DefinitionComponentsMethod,
    DefinitionScope,
    assess_applicability,
    components_from_named_matches,
    decode_definition_components,
    definition_pack,
)
from corpus_structure.methods.gliner import GlinerRefused
from corpus_structure.methods.model_observation import (
    MODEL_OBSERVATION_INPUT,
    installed_policy,
    observation_digest,
    request_digest,
)
from corpus_structure.semantic.contextual_links import RetainedRelationshipDecisionRef
from corpus_structure.semantic.structural_admission import structural_statement
from corpus_structure.semantic.structural_products import (
    ApplicabilityPremise,
    DefinitionBasisWitness,
    DefinitionComponentsProduct,
    ExternalSourceRef,
    RetainedComponentRef,
    StructuralInput,
    StructuralPassage,
    StructuralProductReport,
)


def inputs(text="We call the expected squared deviation variance."):
    source = ExternalSourceRef(
        project_id="book",
        run_id=1,
        cut_id=1,
        release_id="r",
        result_revision=1,
        source_view_id=1,
        native_task_id=1,
        native_product_key="native",
        native_content_digest="a" * 64,
        projection_digest="b" * 64,
        recipe_digest="c" * 64,
        coordinate_version=3,
    )
    return StructuralInput(
        question="What is defined?",
        scope="s",
        inventory_id="i",
        policy_id="p",
        sources=(source,),
        passages=(
            StructuralPassage(
                passage_id="target",
                source_ref=source.identity,
                start=10,
                end=10 + len(text),
                text=text,
                scope="s",
                parent="test-parent",
            ),
            StructuralPassage(
                passage_id="usage",
                source_ref=source.identity,
                start=100,
                end=108,
                text="variance",
                scope="s",
                parent="test-parent",
            ),
        ),
        dependencies=("source", "structural:component-report"),
    )


def raw(text):
    term = {
        "start": text.index("variance"),
        "end": text.index("variance") + 8,
        "text": "variance",
        "interpretation": "definition",
    }
    content = {
        "start": text.index("expected"),
        "end": text.index(" deviation") + 10,
        "text": "expected squared deviation",
    }
    return {
        "entities": {"defined term or expression": [term], "defining text or formula": [content]},
        "relation_extraction": {
            "term is defined or explained by": [
                {"head": {k: v for k, v in term.items() if k != "interpretation"}, "tail": content}
            ]
        },
    }


def component():
    value = inputs()
    return decode_definition_components(
        raw(value.passages[0].text), value.passages[0], DefinitionComponentsConfig()
    )[0]


def reference():
    return RetainedComponentRef(
        product_id="structural:component-report",
        component_id=component().component_id,
        operation_id="structure.definition_components",
        operation_version="1",
        project_id="book",
        run_id=1,
        cut_id=1,
        release_id="r",
        result_revision=1,
        selected_task_id=1,
        origin_task_id=1,
        runtime_fingerprint="runtime",
        dependencies=("source",),
    )


def link_reference():
    return RetainedRelationshipDecisionRef(
        project_id="book",
        run_id=1,
        cut_id=1,
        release_id="r",
        result_revision=1,
        selected_task_id=2,
        origin_task_id=2,
        runtime_fingerprint="runtime",
        operation_key="operation",
        decision_id="decision",
        edge_id="edge",
        occurrence_contribution_id="occurrence",
    )


def premises(
    state: Literal["compatible", "incompatible", "unknown", "inapplicable"] = "compatible",
):
    return tuple(
        ApplicabilityPremise(
            dimension=d,
            state=state if d == "sense" else "inapplicable",
            evidence=("usage", "target"),
            reason="Independently specified literal compatibility test.",
        )
        for d in ("sense", "parameterization", "convention")
    )


def test_absent_operations_cannot_smuggle_partial_inputs():
    assert DefinitionComponentsMethod().select(None, DefinitionComponentsConfig()) == ()
    assert DefinitionApplicabilityMethod().select(None, DefinitionApplicabilityConfig()) == ()
    with pytest.raises(ValueError, match="partial"):
        DefinitionComponentsConfig(target_ids=("target",))


def test_target_local_pack_qualifies_attributes_without_whole_pair_labels():
    schema = definition_pack("r", DefinitionComponentsConfig()).compile().to_dict()
    assert schema["entity_attributes"]["interpretation"]["applies_to"] == [
        "defined term or expression"
    ]
    assert "classifications" not in schema


def test_reversed_surface_order_retains_correct_original_endpoints():
    c = component()
    assert (c.term.text, c.content.text) == ("variance", "expected squared deviation")
    assert c.content.start < c.term.start
    assert c.term.start == 49 and c.content.start == 22
    assert c.basis == "model_reading"


def test_unattached_span_does_not_invent_definition_or_role():
    value = inputs()
    returned = raw(value.passages[0].text)
    returned["relation_extraction"] = {}
    assert (
        decode_definition_components(returned, value.passages[0], DefinitionComponentsConfig())
        == ()
    )
    returned = raw(value.passages[0].text)
    returned["entities"]["defined term or expression"][0]["text"] = "sigma"
    with pytest.raises(GlinerRefused, match="slice"):
        decode_definition_components(returned, value.passages[0], DefinitionComponentsConfig())


def test_missing_span_attribute_is_unavailable_not_a_default_definition():
    value = inputs()
    returned = raw(value.passages[0].text)
    del returned["entities"]["defined term or expression"][0]["interpretation"]
    with pytest.raises(GlinerRefused, match="interpretation"):
        decode_definition_components(returned, value.passages[0], DefinitionComponentsConfig())


def test_component_closure_rejects_relocated_text_and_old_report_protocol():
    value = inputs()
    c = component()
    report = StructuralProductReport(
        kind="definition_components",
        inputs=value,
        definition_components=DefinitionComponentsProduct(components=(c,), stages=()),
    )
    with pytest.raises(ValueError):
        StructuralProductReport.model_validate(
            {**report.model_dump(), "version": "structural-product-1"}
        )
    with pytest.raises(ValueError, match="original passage"):
        StructuralProductReport(
            kind="definition_components",
            inputs=value.model_copy(
                update={
                    "passages": (
                        value.passages[0].model_copy(
                            update={"text": "X" * len(value.passages[0].text)}
                        ),
                        value.passages[1],
                    )
                }
            ),
            definition_components=report.definition_components,
        )
    with pytest.raises(ValueError, match="selector"):
        structural_statement(report)
    statement = structural_statement(report, c.component_id)
    assert statement["definition_component"]["term"]["text"] == "variance"
    assert statement["definition_component"]["content"]["start"] == 22


def test_applicability_is_separate_and_unknown_premises_preserve_component():
    candidate = ApplicabilityCandidate(
        target_id="target",
        reference=reference(),
        link_ref=link_reference(),
        component=component(),
        premises=premises("unknown"),
    )
    assert assess_applicability(inputs(), "usage", candidate).outcome == "unresolved"
    assert candidate.component.term.text == "variance"
    assert (
        assess_applicability(
            inputs(), "usage", candidate.model_copy(update={"premises": premises()})
        ).outcome
        == "applicable_definition"
    )
    assert (
        assess_applicability(
            inputs(), "usage", candidate.model_copy(update={"premises": premises("incompatible")})
        ).outcome
        == "incompatible"
    )


def test_named_roles_use_bindings_not_surface_order():
    passage = inputs().passages[0]
    term = LocatedRole("term", "last", 5, "exact", (5,), ((49, 57),), "complete")
    content = LocatedRole(
        "content", "first", 2, "subtree", (2, 3, 4), ((22, 30), (31, 38), (39, 48)), "complete"
    )
    cue = LocatedRole("defining_cue", "cue", 1, "exact", (1,), ((13, 17),), "complete")
    match = AnnotationRuleMatch(
        "call",
        "reversed",
        "dependency",
        (1, 5, 2),
        ((13, 57),),
        (),
        (),
        "d",
        (content, term, cue),
    )
    scope = DefinitionScope(1, "positive", "supported")
    witness = DefinitionBasisWitness(
        annotation_task_id=6,
        block_id="#/texts/17",
        dependency_digest="f" * 64,
        rule="call",
        variant="reversed",
        nodes=(1, 5, 2),
    )
    options = dict(scopes={match: scope}, term_role="term", content_role="content")
    (found,) = components_from_named_matches(
        passage, (match,), **options, witnesses={match: witness}
    )
    assert found.term.text == "variance"
    assert found.witness == witness
    (unqualified,) = components_from_named_matches(passage, (match,), **options, witnesses={})
    assert unqualified.basis == "unqualified"
    assert unqualified.interpretation == "unresolved"
    assert unqualified.witness is None and unqualified.component_id != found.component_id
    unavailable = replace(match, roles=(replace(term, status="unavailable"), content, cue))
    assert (
        components_from_named_matches(
            passage,
            (unavailable,),
            scopes={unavailable: scope},
            term_role="term",
            content_role="content",
        )
        == ()
    )


def test_following_display_requires_explicit_cue_and_direct_native_element():
    from corpus_structure.methods.definition_applicability import components_from_following_display

    value = inputs("Density is defined as follows:\nf(x)=x.")
    passage = value.passages[0]
    term = LocatedRole("defined_term", "term", 0, "noun_chunk", (0,), ((10, 17),), "complete")
    cue = LocatedRole("following_content_cue", "cue", 4, "exact", (4,), ((32, 39),), "complete")
    match = AnnotationRuleMatch(
        "defining", "follows", "dependency", (0, 4), ((10, 39),), (), (), "d", (term, cue)
    )
    scopes = {match: DefinitionScope(3, "positive", "supported")}
    found = components_from_following_display(
        passage, (match,), ((41, 48),), scopes=scopes, term_role="defined_term"
    )
    assert (
        len(found) == 1 and found[0].term.text == "Density" and found[0].content.text == "f(x)=x."
    )
    assert found[0].basis == "native_geometry"
    no_cue = replace(match, roles=(term,))
    assert (
        components_from_following_display(
            passage,
            (no_cue,),
            ((41, 48),),
            scopes={no_cue: scopes[match]},
            term_role="defined_term",
        )
        == ()
    )
    # A non-adjacent display cannot be attached across intervening prose.
    assert (
        components_from_following_display(
            passage, (match,), ((43, 48),), scopes=scopes, term_role="defined_term"
        )
        == ()
    )


def test_definition_introduction_does_not_transfer_to_other_occurrences():
    from corpus_structure.methods.definition_applicability import is_defining_occurrence

    value = inputs()
    defined = component()
    target = value.passages[0]
    introduction = StructuralPassage(
        passage_id="intro",
        source_ref=target.source_ref,
        start=defined.term.start,
        end=defined.term.end,
        text=defined.term.text,
        scope=defined.scope,
        effective_version=defined.effective_version,
        parent=target.parent,
    )
    assert is_defining_occurrence(value, introduction, defined, "defined-by")
    assert not is_defining_occurrence(value, introduction, defined, "denotes")
    assert not is_defining_occurrence(
        value,
        introduction.model_copy(
            update={"start": introduction.start + 1, "end": introduction.end + 1}
        ),
        defined,
        "defined-by",
    )
    assert not is_defining_occurrence(
        value,
        introduction.model_copy(update={"effective_version": "different"}),
        defined,
        "defined-by",
    )


def test_definition_introduction_scope_requires_the_domain_policy():
    value = inputs()
    with pytest.raises(ValueError, match="introduction policy"):
        DefinitionApplicabilityConfig(
            inputs=value,
            structural_input_digest=value.identity,
            usage_id="usage",
            selection_refs=(link_reference(),),
            applicability_scope="defining_occurrence",
        )


def test_definition_windows_bound_model_work_and_preserve_original_coordinates(monkeypatch):
    from corpus_structure.methods.definition_applicability import definition_windows

    text = " ".join("concept" + str(i) for i in range(120))
    passage = inputs(text).passages[0]
    from pathlib import Path

    from corpus_structure.methods import definition_applicability as owner
    from corpus_structure.methods.gliner import GlinerProfile

    profile = GlinerProfile(
        Path("/model"),
        "checkpoint",
        "revision",
        tuple(
            (name, "a" * 64)
            for name in (
                "config.json",
                "encoder_config/config.json",
                "model.safetensors",
                "tokenizer.json",
                "tokenizer_config.json",
            )
        ),
        max_input_bytes=1200,
    )
    value = inputs(text)
    cfg = DefinitionComponentsConfig(
        inputs=value,
        structural_input_digest=value.identity,
        target_ids=("target",),
        profile=profile,
    )
    windows = definition_windows(passage, cfg)
    assert len(windows) > 1 and windows[0].start == passage.start and windows[-1].end == passage.end
    for window in windows:
        assert window.text == text[window.start - passage.start : window.end - passage.start]
        assert len(window.text) <= 300
    assert all(left.end >= right.start for left, right in pairwise(windows))
    monkeypatch.setattr(owner, "_DEFINITION_MAX_WINDOWS", 1)
    limited = definition_windows(passage, cfg)
    assert "max_window_chars" not in DefinitionComponentsConfig.model_json_schema()["properties"]
    assert len(limited) == 1 and limited[-1].end < passage.end


def test_located_span_success_survives_empty_or_failed_attachment():
    from corpus_structure.methods.definition_applicability import located_entity_count

    value = inputs()
    passage = value.passages[0]
    returned = raw(passage.text)
    returned["relation_extraction"] = {}
    assert located_entity_count(returned, passage, DefinitionComponentsConfig()) == 2
    assert decode_definition_components(returned, passage, DefinitionComponentsConfig()) == ()
    del returned["entities"]["defined term or expression"][0]["interpretation"]
    assert located_entity_count(returned, passage, DefinitionComponentsConfig()) == 2
    with pytest.raises(GlinerRefused, match="interpretation"):
        decode_definition_components(returned, passage, DefinitionComponentsConfig())


def test_located_roles_keep_exact_independent_envelope_indices():
    from corpus_structure.methods.definition_applicability import located_definition_roles

    passage = inputs().passages[0]
    cfg = DefinitionComponentsConfig()
    returned = raw(passage.text)
    returned["relation_extraction"] = {}
    returned["entities"][cfg.term_entity].insert(0, {"start": -1, "end": 3, "text": "bad"})
    errors = []
    term, content = located_definition_roles(
        returned, passage, cfg, envelope="pinned", errors=errors
    )
    assert (term.role, term.index, term.span.text) == ("term", 1, "variance")
    assert (content.role, content.index, content.span.text) == (
        "content",
        0,
        "expected squared deviation",
    )
    assert (term.envelope, content.envelope) == ("pinned", "pinned")
    assert len(errors) == 1 and errors[0]["index"] == 0
    assert decode_definition_components(returned, passage, cfg, candidate_errors=[]) == ()


def test_description_arm_uses_same_roles_and_relation_with_distinct_native_prompts():
    baseline = DefinitionComponentsConfig()
    described = baseline.model_copy(update={"description_arm": "described"})
    bare_pack = definition_pack("r", baseline)
    described_pack = definition_pack("r", described)
    bare = bare_pack.compile().to_dict()
    updated = described_pack.compile().to_dict()
    assert list(bare["entities"]) == list(updated["entities"])
    assert list(bare["relations"]) == list(updated["relations"])
    assert bare["entity_attributes"] == updated["entity_attributes"]
    assert bare_pack.fingerprint != described_pack.fingerprint


def test_independent_valid_attachment_survives_other_candidates_role_failure():
    passage = inputs().passages[0]
    returned = raw(passage.text)
    relation = returned["relation_extraction"]["term is defined or explained by"][0]
    returned["relation_extraction"]["term is defined or explained by"].insert(
        0, {"head": relation["tail"], "tail": relation["head"]}
    )
    errors = []
    (found,) = decode_definition_components(
        returned, passage, DefinitionComponentsConfig(), candidate_errors=errors
    )
    assert found.term.text == "variance" and found.content.text == "expected squared deviation"
    assert errors == [
        dict(
            channel="attachment",
            index=0,
            type="GlinerRefused",
            reason="attachment endpoints lack the declared decoded roles",
        )
    ]
    # Strict callers retain the original refusal contract; production records both grains.
    with pytest.raises(GlinerRefused, match="declared decoded roles"):
        decode_definition_components(returned, passage, DefinitionComponentsConfig())


def test_invalid_term_interpretation_does_not_relabel_or_erase_another_valid_attachment():
    passage = inputs().passages[0]
    returned = raw(passage.text)
    returned["entities"]["defined term or expression"].append(
        {"start": 0, "end": 2, "text": "We", "interpretation": "invented"}
    )
    errors = []
    (found,) = decode_definition_components(
        returned, passage, DefinitionComponentsConfig(), candidate_errors=errors
    )
    assert found.term.text == "variance"
    assert len(errors) == 1 and errors[0]["channel"] == "term" and errors[0]["index"] == 1


def test_production_retains_valid_attachment_and_failed_stage_with_indexed_raw_error(monkeypatch):
    import json
    from pathlib import Path
    from types import SimpleNamespace

    from corpus_structure.core.method import UnitRef
    from corpus_structure.core.vocab import TaskUnitType
    from corpus_structure.methods.gliner import GlinerPreparation, GlinerProfile, GlinerReport
    from corpus_structure.serve.model_observation_replay import _verify_definition_roles

    value = inputs()
    returned = raw(value.passages[0].text)
    relation = returned["relation_extraction"]["term is defined or explained by"][0]
    returned["relation_extraction"]["term is defined or explained by"].append(
        {"head": relation["tail"], "tail": relation["head"]}
    )
    profile = GlinerProfile(
        Path("/controlled-model"),
        "checkpoint",
        "revision",
        tuple(
            (name, "a" * 64)
            for name in (
                "config.json",
                "encoder_config/config.json",
                "model.safetensors",
                "tokenizer.json",
                "tokenizer_config.json",
            )
        ),
    )
    cfg = DefinitionComponentsConfig(
        inputs=value,
        structural_input_digest=value.identity,
        target_ids=("target",),
        profile=profile,
        use_named_candidates=False,
    )

    class ControlledWorker:
        def __init__(self):
            self.profile = profile

        def extract(self, pack, requests, **kwargs):
            (request,) = requests
            key = request_digest(
                pack,
                asdict(profile),
                requests,
                kwargs["threshold"],
                kwargs["overlap_policy"],
                kwargs.get("evaluation", False),
                policy["inference"],
            )
            from corpus_structure.methods.model_observation import batch_receipt

            receipt = batch_receipt(
                pack,
                asdict(profile),
                requests,
                kwargs["threshold"],
                kwargs["overlap_policy"],
                kwargs.get("evaluation", False),
                policy["inference"],
            )
            raw = json.dumps(returned)
            return (
                GlinerReport(
                    request.context_id,
                    request.context_digest,
                    key,
                    profile.fingerprint,
                    pack.fingerprint,
                    GlinerPreparation(request.text, "", 0, 0, len(request.text)),
                    raw,
                    "{}",
                    0.0,
                    False,
                    request_digest=key,
                    observation_digest=observation_digest(
                        key, raw, "{}", ordinal=0, member=receipt["members"][0]
                    ),
                    batch_receipt_json=json.dumps(receipt),
                    member_ordinal=0,
                ),
            )

    policy, policy_digest = installed_policy()
    method = DefinitionComponentsMethod()
    monkeypatch.setattr(method, "_worker", ControlledWorker())
    ctx = SimpleNamespace(
        check_active=lambda: None,
        reader=SimpleNamespace(
            validate_structural_inputs=lambda _: None,
            prepared=SimpleNamespace(
                release_id="r",
                manifest=json.dumps({"dependencies": [(MODEL_OBSERVATION_INPUT, policy_digest)]}),
            ),
        ),
    )
    (result,) = method.run(
        (SimpleNamespace(ref=UnitRef(TaskUnitType.RUN, unit_key="control")),), cfg, ctx
    )
    report = StructuralProductReport.model_validate(result.structural_product)
    assert report.definition_components is not None
    assert len(report.definition_components.components) == 1
    assert (
        next(s for s in report.definition_components.stages if s.operation == "attachment").outcome
        == "failed"
    )
    assert result.parse_detail is not None
    retained = result.parse_detail["raw_reports"]
    assert isinstance(retained, list) and isinstance(retained[0], dict)
    assert retained[0]["raw_json"] == json.dumps(returned)
    assert retained[0]["decoded_attachment_count"] == 1
    assert retained[0]["candidate_errors"] == [
        dict(
            channel="attachment",
            index=1,
            type="GlinerRefused",
            reason="attachment endpoints lack the declared decoded roles",
        )
    ]
    config = cfg.model_dump(mode="json", exclude_none=True)
    _verify_definition_roles(report, config, result.parse_detail, "r", policy, primary=True)
    original_window = retained[0]["window_start"]
    assert isinstance(original_window, int)
    retained[0]["window_start"] = original_window + 1
    with pytest.raises(ValueError, match="returned window"):
        _verify_definition_roles(report, config, result.parse_detail, "r", policy, primary=True)
    retained[0]["window_start"] = original_window
    with pytest.raises(ValueError, match="exact configured population"):
        _verify_definition_roles(
            report,
            config,
            {**result.parse_detail, "window_outcomes": []},
            "r",
            policy,
            primary=True,
        )
    # All entity roles and exact source coordinates survive, but the valid directed
    # relation is gone. The component can no longer be admitted as a model reading.
    returned["relation_extraction"][cfg.attachment_relation].pop(0)
    retained[0]["raw_json"] = json.dumps(returned)
    receipt_text = retained[0]["batch_receipt_json"]
    ordinal = retained[0]["member_ordinal"]
    assert isinstance(receipt_text, str) and type(ordinal) is int
    retained[0]["observation_digest"] = observation_digest(
        retained[0]["computation"],
        retained[0]["raw_json"],
        "{}",
        ordinal=ordinal,
        member=json.loads(receipt_text)["members"][ordinal],
    )
    with pytest.raises(ValueError, match="retained directed attachments"):
        _verify_definition_roles(report, config, result.parse_detail, "r", policy, primary=True)


def test_labelled_copula_display_requires_same_block_explicit_definition_label():
    from corpus_structure.methods.definition_applicability import components_from_following_display

    passage = inputs("Definition 1. Variance is\nf(x)=x.").passages[0]
    term = LocatedRole("nominal_subject", "term", 3, "noun_chunk", (3,), ((24, 32),), "complete")
    cue = LocatedRole("copular_cue", "cue", 4, "exact", (4,), ((33, 35),), "complete")
    requirement = replace(cue, role="definition_label_required")
    match = AnnotationRuleMatch(
        "definition_context",
        "labelled_copula_display",
        "dependency",
        (3, 4),
        (),
        (),
        (),
        "d",
        (term, cue, requirement),
    )
    label = replace(term, role="definition_label", extents=((10, 22),), nodes=(0, 1))
    label_match = replace(match, rule="definition_context", roles=(label,))
    scopes = {match: DefinitionScope(4, "positive", "supported")}
    assert (
        components_from_following_display(
            passage, (match,), ((36, 43),), scopes=scopes, term_role="defined_term"
        )
        == ()
    )
    (found,) = components_from_following_display(
        passage, (label_match, match), ((36, 43),), scopes=scopes, term_role="defined_term"
    )
    assert found.term.text == "Variance" and found.content.text == "f(x)=x."
    # An intervening reference is source content, not punctuation or a formula.
    reference_passage = inputs("Definition 1. Variance is Equation 2\nf(x)=x.").passages[0]
    assert (
        components_from_following_display(
            reference_passage,
            (label_match, match),
            ((47, 54),),
            scopes=scopes,
            term_role="defined_term",
        )
        == ()
    )


def test_parent_context_is_a_required_applicability_distinction():
    value = inputs()
    candidate = ApplicabilityCandidate(
        target_id=component().component_id,
        reference=reference(),
        link_ref=link_reference(),
        component=component(),
        premises=premises(),
    )
    usage = value.passages[1]
    mismatched = value.model_copy(
        update={
            "passages": (value.passages[0], usage.model_copy(update={"parent": "different-parent"}))
        }
    )
    decision = assess_applicability(mismatched, "usage", candidate)
    assert decision.outcome == "incompatible"
    assert next(p.state for p in decision.premises if p.dimension == "parent") == "incompatible"
    unavailable = value.model_copy(
        update={"passages": (value.passages[0], usage.model_copy(update={"parent": None}))}
    )
    undecided = assess_applicability(unavailable, "usage", candidate)
    assert undecided.outcome == "unresolved"
    assert next(p.state for p in undecided.premises if p.dimension == "parent") == "unknown"


def test_introduction_policy_label_is_not_an_actual_introduction_binding():
    value = inputs()
    defined = component()
    target = value.passages[0].model_copy(update={"parent": None})
    usage = StructuralPassage(
        passage_id="usage",
        source_ref=target.source_ref,
        start=defined.term.start,
        end=defined.term.end,
        text=defined.term.text,
        scope=defined.scope,
    )
    value = value.model_copy(
        update={"policy_id": "definition-introduction-1", "passages": (target, usage)}
    )
    candidate = ApplicabilityCandidate(
        target_id=defined.component_id,
        reference=reference(),
        link_ref=link_reference(),
        component=defined,
        premises=premises("unknown"),
    )
    contextual = assess_applicability(value, "usage", candidate)
    assert next(p.state for p in contextual.premises if p.dimension == "parent") == "unknown"
    introduction = assess_applicability(value, "usage", candidate, defining_occurrence=True)
    assert next(p.state for p in introduction.premises if p.dimension == "parent") == "inapplicable"


def test_explicit_linguistic_only_mode_has_no_provider_profile():
    value = inputs()
    cfg = DefinitionComponentsConfig(
        inputs=value,
        structural_input_digest=value.identity,
        target_ids=("target",),
        use_model=False,
    )
    assert cfg.profile is None and not cfg.use_model
    with pytest.raises(ValueError, match="named candidates"):
        DefinitionComponentsConfig(
            inputs=value,
            structural_input_digest=value.identity,
            target_ids=("target",),
            use_model=False,
            use_named_candidates=False,
        )


@pytest.mark.parametrize("context", ("unique", "competing", "outside_selection", "separate_piece"))
def test_naming_resolves_only_a_unique_selected_restricted_antecedent(context):
    from types import SimpleNamespace

    import yaml

    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.ingest.pdf_hierarchy import ProjectedPiece
    from corpus_structure.methods.definition_applicability import retained_annotation_components
    from corpus_structure.schema.pack import DOMAINS
    from methods.predicate_frames_support import _PREFIX, retained

    restriction = (
        "the set of points (x, y) in the xy-plane such that fX,Y (x, y) = C for some constant C."
    )
    sentence = f"Now suppose that we want to know {restriction}"
    if context == "competing":
        sentence = sentence[:-1] + " and the set of points such that y = 0."
    mention = "This set of points"
    text = f"{sentence} {mention} is called a set of constant density."
    offset = len(_PREFIX)
    mention_start = offset + len(sentence) + 1
    pieces = None
    if context == "separate_piece":
        pieces = (
            ProjectedPiece("#/texts/3", offset, mention_start, "native_text"),
            ProjectedPiece("#/texts/4", mention_start, offset + len(text), "native_text"),
        )
    source_text, product = retained(text, AnnotationProfile(), pieces=pieces)
    start = mention_start if context == "outside_selection" else offset
    selected = (
        inputs()
        .passages[0]
        .model_copy(update={"start": start, "end": len(source_text), "text": source_text[start:]})
    )
    rules = yaml.safe_load((DOMAINS / "statistics/construction.yaml").read_bytes())
    config = DefinitionComponentsConfig(
        annotation_rules=rules["annotation_rules"],
    )
    from methods.primary_reading_fixture import primary_product

    product = primary_product(
        source_text, product, AnnotationProfile(), rules=config.annotation_rules
    )
    result = retained_annotation_components(
        None,
        None,
        selected,
        config,
        witness_policy=installed_policy()[0]["definition_witness"],
        retained=SimpleNamespace(
            source=SimpleNamespace(text=source_text),
            annotations=(product,),
            errors=(),
            annotation_task_id=594,
        ),
    )
    assert result.components, result.reason
    (found,) = result.components
    assert found.term.text == "a set of constant density"
    assert found.content.text == (restriction if context == "unique" else mention)
    assert source_text[found.content.start : found.content.end] == found.content.text
    (match,) = next(
        operation["matches"]
        for operation in result.operations
        if operation["variant"] == "passive_called_term"
    )
    if context == "unique":
        assert found.basis == "unqualified" and found.interpretation == "unresolved"
        assert match["content_antecedent"] == found.content.model_dump(mode="json")
        (role,) = [role for role in match["roles"] if role["role"] == "defining_content"]
        assert source_text[role["extents"][0][0] : role["extents"][-1][1]] == mention
    else:
        assert "content_antecedent" not in match


def test_detached_named_basis_refuses_genuine_spans_without_its_witness():
    from corpus_structure.semantic.structural_products import (
        LocatedDefinitionSpan,
        definition_component,
    )
    from corpus_structure.serve.model_observation_replay import _verify_primary_observation

    original = inputs()
    passage = original.passages[0]

    def located(start, end):
        return LocatedDefinitionSpan(
            passage_id=passage.passage_id,
            start=start,
            end=end,
            text=passage.text[start - passage.start : end - passage.start],
        )

    unsupported = definition_component(
        term=located(49, 57),
        content=located(22, 48),
        interpretation="explanation",
        basis="matched_cue",
        scope=passage.scope,
        evidence=(passage.passage_id,),
        reason="Both phrases are in the source.",
    )
    report = StructuralProductReport(
        kind="definition_components",
        inputs=original,
        definition_components=DefinitionComponentsProduct(components=(unsupported,), stages=()),
    )
    with pytest.raises(ValueError, match="exact retained annotation witness"):
        _verify_primary_observation(
            None, {}, dict(body={}, configuration={}), report, {}, iter(()), None
        )


@pytest.mark.parametrize(
    ("method", "version"),
    [
        ("structure.definition_components", "8"),
        ("structure.definition_components", "9"),
        ("structure.definition_declaration_components", "1"),
    ],
)
def test_obsolete_semantic_closure_requires_regeneration_without_reinterpreting_bytes(
    monkeypatch, method, version
):
    from corpus_structure.serve import model_observation_replay as replay
    from corpus_structure.serve import review_bundle

    report = StructuralProductReport(
        kind="definition_components",
        inputs=inputs(),
        definition_components=DefinitionComponentsProduct(components=(), stages=()),
    )
    original = dict(origin_task_id=1, body=dict(method=method, operation_version=version))
    monkeypatch.setattr(
        review_bundle,
        "_detached_relation",
        lambda _root, _manifest, relation: [original] if relation == "reports" else [],
    )
    with pytest.raises(ValueError, match="requires regeneration"):
        replay.verify_model_observation_closure(None, {}, [(None, None, 1, report)], (), ())


def test_current_named_definition_primary_witness_crosses_released_batch():
    from types import SimpleNamespace

    import yaml
    from semantic.structural_release_fixture import released_report

    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.methods.definition_applicability import retained_annotation_components
    from corpus_structure.schema.pack import DOMAINS
    from methods.predicate_frames_support import _PREFIX, retained
    from methods.primary_reading_fixture import primary_product

    profile = AnnotationProfile()
    text, product = retained("The expected squared deviation is called variance.", profile)
    declarations = yaml.safe_load((DOMAINS / "statistics/construction.yaml").read_bytes())
    rules = declarations["annotation_rules"]
    cfg = DefinitionComponentsConfig(annotation_rules=rules)
    product = primary_product(text, product, profile, rules=cfg.annotation_rules)
    from corpus_structure.semantic.source_contexts import NativeSourcePin

    native = product.source
    assert isinstance(native, NativeSourcePin)
    source = (
        inputs()
        .sources[0]
        .model_copy(
            update=dict(
                source_view_id=native.source_view_id,
                native_task_id=native.native_product.task_id,
                native_product_key=native.native_product.product_key,
                native_content_digest=native.native_product.content_digest,
                projection_digest=native.projection_digest,
                recipe_digest=native.recipe_digest,
                coordinate_version=native.version,
            )
        )
    )
    selected = (
        inputs()
        .passages[0]
        .model_copy(
            update=dict(
                source_ref=source.identity,
                start=len(_PREFIX),
                end=len(text),
                text=text[len(_PREFIX) :],
            )
        )
    )
    named = retained_annotation_components(
        None,
        None,
        selected,
        cfg,
        witness_policy=installed_policy()[0]["definition_witness"],
        retained=SimpleNamespace(
            source=SimpleNamespace(text=text),
            annotations=(product,),
            errors=(),
            annotation_task_id=594,
        ),
    )
    (component,) = named.components
    assert (component.term.text, component.content.text) == (
        "variance",
        "The expected squared deviation",
    )
    assert component.witness is not None
    assert component.witness.primary_match is not None and component.witness.primary_scope
    value = inputs().model_copy(update=dict(sources=(source,), passages=(selected,)))
    report = StructuralProductReport(
        kind="definition_components",
        inputs=value,
        definition_components=DefinitionComponentsProduct(components=(component,), stages=()),
    )
    released = released_report(report, method=DefinitionComponentsMethod.name, version="10")
    witness = released["definition_components"]["components"][0]["witness"]
    assert witness["primary_match"] == component.witness.primary_match.values()
    assert witness["primary_scope"] == [ref.values() for ref in component.witness.primary_scope]
