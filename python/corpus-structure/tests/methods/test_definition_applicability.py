"""Independent endpoint, role and compatibility controls; no mocked efficacy claims."""

from dataclasses import replace
from itertools import pairwise
from typing import Literal

import pytest
from semantic.definition_component_members_support import (
    unadmitted_component_members,
)
from semantic.structural_products_support import input_from_passages, root_references

from corpus_structure.methods.annotation_rules import AnnotationRuleMatch, LocatedRole
from corpus_structure.methods.definition_applicability import (
    DefinitionScope,
    applicability_assessment,
    components_from_named_matches,
    decode_definition_components,
    definition_pack,
)
from corpus_structure.methods.gliner import GlinerRefused
from corpus_structure.semantic.declared_structural_references import (
    DeclaredRelationshipRef,
)
from corpus_structure.semantic.definition_applicability_products import (
    DeclaredApplicabilityCandidate,
)
from corpus_structure.semantic.definition_model_products import (
    DefinitionExtractionOptions,
    DefinitionQuestion,
    decode_definition_window,
)
from corpus_structure.semantic.structural_admission import structural_statement
from corpus_structure.semantic.structural_products import (
    ApplicabilityPremise,
    DeclaredDefinitionBasisWitness,
    DeclaredDefinitionComponentsProduct,
    DeclaredDefinitionComponentsReport,
    DeclaredStructuralProductReport,
    StructuralPassage,
)


def inputs(text="We call the expected squared deviation variance."):
    return input_from_passages(
        (
            dict(
                document="definition-original",
                passage_id="target",
                start=10,
                text=text,
                parent="test-parent",
            ),
            dict(
                document="definition-original",
                passage_id="usage",
                start=max(100, 20 + len(text)),
                text="variance",
                parent="test-parent",
            ),
        ),
        question="What is defined?",
        scope="s",
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
        raw(value.passages[0].text), value.passages[0], DefinitionQuestion(profile=None)
    )[0]


def reference():
    return root_references(inputs())[0].model_copy(
        update=dict(component_id=component().component_id)
    )


def link_reference():
    root = reference()
    return DeclaredRelationshipRef(
        **{
            key: value
            for key, value in root.model_dump().items()
            if key not in {"component_id", "structural_id"}
        },
        edge_id="fixture:definition-edge",
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


def test_target_local_pack_qualifies_attributes_without_whole_pair_labels():
    schema = definition_pack("r", DefinitionQuestion(profile=None)).compile().to_dict()
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
        decode_definition_components(returned, value.passages[0], DefinitionQuestion(profile=None))
        == ()
    )
    returned = raw(value.passages[0].text)
    returned["entities"]["defined term or expression"][0]["text"] = "sigma"
    with pytest.raises(GlinerRefused, match="slice"):
        decode_definition_components(returned, value.passages[0], DefinitionQuestion(profile=None))


def test_missing_span_attribute_is_unavailable_not_a_default_definition():
    value = inputs()
    returned = raw(value.passages[0].text)
    del returned["entities"]["defined term or expression"][0]["interpretation"]
    with pytest.raises(GlinerRefused, match="interpretation"):
        decode_definition_components(returned, value.passages[0], DefinitionQuestion(profile=None))


def test_component_closure_rejects_relocated_text_and_old_report_protocol():
    value = inputs()
    c = component()
    report = DeclaredDefinitionComponentsReport(
        kind="definition_components",
        inputs=value,
        members=unadmitted_component_members((c,)),
        definition_components=DeclaredDefinitionComponentsProduct(stages=()),
    )
    with pytest.raises(ValueError):
        DeclaredStructuralProductReport.model_validate(
            {**report.model_dump(), "version": "structural-product-1"}
        )
    with pytest.raises(ValueError, match="original passage"):
        DeclaredDefinitionComponentsReport(
            kind="definition_components",
            members=report.members,
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
    candidate = DeclaredApplicabilityCandidate(
        target_id="target",
        reference=reference(),
        link_ref=link_reference(),
        component=component(),
        premises=premises("unknown"),
    )
    assert applicability_assessment(inputs(), "usage", candidate).outcome == "unresolved"
    assert candidate.component.term.text == "variance"
    assert (
        applicability_assessment(inputs(), "usage", replace(candidate, premises=premises())).outcome
        == "applicable_definition"
    )
    assert (
        applicability_assessment(
            inputs(), "usage", replace(candidate, premises=premises("incompatible"))
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
    witness = DeclaredDefinitionBasisWitness(
        annotation_product={"variant": "product", "role": "annotations"},
        block_id="#/texts/17",
        dependency_digest="f" * 64,
        rule="call",
        variant="reversed",
        nodes=(1, 5, 2),
    )
    options = dict(scopes={match: scope}, term_role="term", content_role="content")
    recorded = {}
    (found,) = components_from_named_matches(
        passage, (match,), **options, witnesses={match: witness}, witnesses_by_component=recorded
    )
    assert found.term.text == "variance"
    assert recorded == {found.component_id: witness}
    (unqualified,) = components_from_named_matches(passage, (match,), **options, witnesses={})
    assert unqualified.basis == "unqualified"
    assert unqualified.interpretation == "unresolved"
    assert unqualified.component_id != found.component_id
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
    cfg = DefinitionQuestion(profile=profile)
    windows = definition_windows(passage, cfg)
    assert len(windows) > 1 and windows[0].start == passage.start and windows[-1].end == passage.end
    for window in windows:
        assert window.text == text[window.start - passage.start : window.end - passage.start]
        assert len(window.text) <= 300
    assert all(left.end >= right.start for left, right in pairwise(windows))
    monkeypatch.setattr(owner, "_DEFINITION_MAX_WINDOWS", 1)
    limited = definition_windows(passage, cfg)
    assert len(limited) == 1 and limited[-1].end < passage.end


def test_located_span_success_survives_empty_or_failed_attachment():
    from corpus_structure.methods.definition_applicability import located_entity_count

    value = inputs()
    passage = value.passages[0]
    returned = raw(passage.text)
    returned["relation_extraction"] = {}
    assert located_entity_count(returned, passage, DefinitionQuestion(profile=None)) == 2
    assert decode_definition_components(returned, passage, DefinitionQuestion(profile=None)) == ()
    del returned["entities"]["defined term or expression"][0]["interpretation"]
    assert located_entity_count(returned, passage, DefinitionQuestion(profile=None)) == 2
    with pytest.raises(GlinerRefused, match="interpretation"):
        decode_definition_components(returned, passage, DefinitionQuestion(profile=None))


def test_located_roles_keep_exact_independent_envelope_indices():
    from corpus_structure.methods.definition_applicability import located_definition_roles

    passage = inputs().passages[0]
    cfg = DefinitionQuestion(profile=None)
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
    baseline = DefinitionQuestion(profile=None)
    described = replace(baseline, description_arm="described")
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
        returned, passage, DefinitionQuestion(profile=None), candidate_errors=errors
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
        decode_definition_components(returned, passage, DefinitionQuestion(profile=None))


def test_invalid_term_interpretation_does_not_relabel_or_erase_another_valid_attachment():
    passage = inputs().passages[0]
    returned = raw(passage.text)
    returned["entities"]["defined term or expression"].append(
        {"start": 0, "end": 2, "text": "We", "interpretation": "invented"}
    )
    errors = []
    (found,) = decode_definition_components(
        returned, passage, DefinitionQuestion(profile=None), candidate_errors=errors
    )
    assert found.term.text == "variance"
    assert len(errors) == 1 and errors[0]["channel"] == "term" and errors[0]["index"] == 1


def test_current_window_retains_valid_attachment_and_indexed_raw_error():
    passage = inputs().passages[0]
    returned = raw(passage.text)
    relation = returned["relation_extraction"]["term is defined or explained by"][0]
    returned["relation_extraction"]["term is defined or explained by"].append(
        {"head": relation["tail"], "tail": relation["head"]}
    )
    decoded = decode_definition_window(
        returned, passage, None, envelope="unadmitted:literal-response"
    )
    assert len(decoded["components"]) == 1
    assert decoded["components"][0]["term"]["text"] == "variance"
    assert len(decoded["role_candidates"]) == 2
    assert decoded["errors"] == [
        dict(
            channel="attachment",
            index=1,
            type="GlinerRefused",
            reason="attachment endpoints lack the declared decoded roles",
        )
    ]


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
    candidate = DeclaredApplicabilityCandidate(
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
    decision = applicability_assessment(mismatched, "usage", candidate)
    assert decision.outcome == "incompatible"
    assert next(p.state for p in decision.premises if p.dimension == "parent") == "incompatible"
    unavailable = value.model_copy(
        update={"passages": (value.passages[0], usage.model_copy(update={"parent": None}))}
    )
    undecided = applicability_assessment(unavailable, "usage", candidate)
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
    candidate = DeclaredApplicabilityCandidate(
        target_id=defined.component_id,
        reference=reference(),
        link_ref=link_reference(),
        component=defined,
        premises=premises("unknown"),
    )
    contextual = applicability_assessment(value, "usage", candidate)
    assert next(p.state for p in contextual.premises if p.dimension == "parent") == "unknown"
    introduction = applicability_assessment(value, "usage", candidate, defining_occurrence=True)
    assert next(p.state for p in introduction.premises if p.dimension == "parent") == "inapplicable"


@pytest.mark.parametrize(
    "options",
    [
        dict(term_entity="same", content_entity="same"),
        dict(description_arm="invented"),
        dict(evaluation_overlap="invented"),
    ],
)
def test_current_extraction_options_reject_unsupported_questions(options):
    with pytest.raises(ValueError, match="explicit distinct roles and supported"):
        DefinitionExtractionOptions(**options)
