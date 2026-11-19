"""Independent context, demand and authored-support counterexamples."""

from dataclasses import replace

import pytest

from corpus_structure.semantic.math_context import (
    acquire_analysis_context_profile,
    prepare_interpretation_context,
)
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.types import PreparationError


def context(**kwargs):
    return prepare_interpretation_context(
        context_profile=acquire_analysis_context_profile(), macros={}, **kwargs
    )


def source_role(role, **extra):
    return {
        "symbol": "f",
        "role": role,
        "authority": "source",
        "evidence": "observation:1",
        "source_id": "rendition:1",
        "scope": "statement:1",
        **extra,
    }


def test_function_without_entity_and_scoped_authority():
    function = context(
        source_id="rendition:1", scope="statement:1", declarations=[source_role("function")]
    )
    variable = context(
        source_id="rendition:1", scope="statement:1", declarations=[source_role("variable")]
    )
    assert "f" in function.grammar_context.functions
    assert "f" in variable.grammar_context.variables
    assert function.key() != variable.key()
    outside = context(
        source_id="rendition:2", scope="statement:1", declarations=[source_role("function")]
    )
    assert "f" not in outside.grammar_context.functions


def test_conflicting_evidence_retains_ambiguity():
    prepared = context(
        source_id="rendition:1",
        scope="statement:1",
        declarations=[source_role("function"), source_role("variable", evidence="observation:2")],
    )
    assert prepared.conflicts == {"f"}
    assert "f" not in prepared.grammar_context.functions | prepared.grammar_context.variables


def test_binding_semantic_identity_is_a_dependency():
    a = context(bindings=[{"kind": "variable", "symbol": "x", "entity": "entity:a"}])
    b = context(bindings=[{"kind": "variable", "symbol": "x", "entity": "entity:b"}])
    assert a.key() != b.key()
    assert a.stage_key("lexical") == b.stage_key("lexical")
    unresolved = context(bindings=[{"kind": "unresolved", "symbol": "x"}])
    assert "x" not in unresolved.grammar_context.variables
    assert unresolved.unresolved == {"x"}


def test_role_defaults_yield_to_explicit_evidenced_declaration():
    prepared = context(
        source_id="rendition:1",
        scope="statement:1",
        bindings=[{"kind": "variable", "symbol": "f", "entity": "entity:f"}],
        declarations=[source_role("function")],
    )
    assert "f" in prepared.grammar_context.functions
    assert "f" not in prepared.grammar_context.variables


def test_source_declaration_requires_custody_and_ordered_extent():
    with pytest.raises(PreparationError):
        context(
            declarations=[
                {
                    "symbol": "f",
                    "role": "function",
                    "authority": "source",
                    "evidence": "observation:1",
                }
            ]
        )
    with pytest.raises(PreparationError):
        context(declarations=[source_role("function", start=12, end=3)])
    prepared = context(
        source_id="rendition:1",
        scope="statement:1",
        offset=20,
        declarations=[source_role("function", start=1, end=10)],
    )
    assert "f" not in prepared.grammar_context.functions


def test_demand_completion_is_separate_from_interpretation():
    occurrences = context(demand="occurrences")
    occurrences.validate_result(
        produced=["lexical", "syntax", "occurrences"], interpretation="unanalysed"
    )
    with pytest.raises(PreparationError):
        occurrences.validate_result(
            produced=["lexical", "occurrences"], interpretation="unanalysed"
        )
    with pytest.raises(PreparationError):
        occurrences.validate_result(
            produced=["lexical", "syntax", "occurrences"], interpretation="ok"
        )
    with pytest.raises(PreparationError):
        context(demand="symbolic").validate_result(
            produced=["lexical", "syntax", "occurrences", "interpretation"], interpretation="ok"
        )
    context(demand="symbolic").validate_result(
        produced=[], interpretation="unsupported", completeness="unsupported"
    )
    with pytest.raises(PreparationError):
        context(demand="invented")


def test_scientific_key_requires_policy_and_conditions():
    prepared = context()
    with pytest.raises(PreparationError):
        prepared.stage_key("scientific")
    first = prepared.stage_key(
        "scientific", conditions=[], precision=30, sampling="seeded-1", decision_policy="reference"
    )
    second = prepared.stage_key(
        "scientific", conditions=[], precision=50, sampling="seeded-1", decision_policy="reference"
    )
    assert first != second


def test_unknown_result_and_binding_kind_refuse():
    with pytest.raises(PreparationError):
        context().validate_result(
            produced=["lexical", "occurrences", "interpretation"], interpretation="invented"
        )
    with pytest.raises(PreparationError):
        context(bindings=[{"kind": "invented", "symbol": "x"}])


def test_caller_cannot_override_prepared_dependency_identity():
    prepared = context()
    for name in ("grammar", "profile", "macros", "declarations"):
        with pytest.raises(PreparationError):
            prepared.stage_key("scientific", **{name: "forged"})


@pytest.mark.parametrize("authority", ["profile", "expression_local", "binding"])
def test_external_declarations_cannot_claim_owned_authority(authority):
    declaration = source_role("function", authority=authority, evidence="made-up")
    with pytest.raises(PreparationError, match="external declarations require source evidence"):
        context(source_id="rendition:1", scope="statement:1", declarations=[declaration])


def test_scientific_profile_and_source_sharing_are_admitted_data():
    computation = next(
        item
        for item in acquire_analysis_context_profile().profile.scientific_profiles
        if item.policy_id == "reference-evidence-2"
    )
    assert computation.minimum_valid_points == 12
    assert computation.numeric_requires == "no-restrictions"
    assert context().profile.grammar_recipe == "extended-lark-3"
    assert context().profile.transformer_recipe == "sympy-transform-3"


def test_candidate_scientific_parameters_rebind_supplied_recipe_without_ambient_acquisition():
    import json

    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.math_context import acquire_analysis_context_profile
    from corpus_structure.semantic.scientific_evidence import (
        SCIENTIFIC_POLICY_INPUT,
        SemanticComparator,
        require_scientific_policy,
        scientific_policy_recipe,
    )
    from corpus_structure.semantic.types import PreparedArtifact, SourceArtifact, SourceBundle

    current = acquire_analysis_context_profile()
    profile = replace(
        current,
        profile=replace(
            current.profile,
            scientific_profiles=tuple(
                replace(item, minimum_valid_points=7)
                if item.policy_id == "consolidation-evidence-2"
                else item
                for item in current.profile.scientific_profiles
            ),
        ),
    )
    prepared = prepare_release(
        SourceBundle(
            "scientific",
            (
                SourceArtifact(
                    "scientific", b"id: urn:scientific\nname: scientific\nclasses: {Thing: {}}\n"
                ),
            ),
        )
    )
    recipe = PreparedArtifact(
        SCIENTIFIC_POLICY_INPUT, canonical_bytes(scientific_policy_recipe(context_profile=profile))
    )
    prepared = replace(prepared, artifacts=(*prepared.artifacts, recipe))
    decoded = json.loads(recipe.content)
    assert decoded["consolidation"]["minimum_valid_points"] == 7
    assert decoded["computation_profiles"][0]["minimum_valid_points"] == 7
    assert (
        SemanticComparator(
            {}, prepared=prepared, context_profile=profile
        ).computation.minimum_valid_points
        == 7
    )
    require_scientific_policy(prepared, context_profile=profile)
    decoded["consolidation"]["minimum_valid_points"] = 6
    altered = replace(
        prepared,
        artifacts=tuple(
            replace(item, content=canonical_bytes(decoded)) if item is recipe else item
            for item in prepared.artifacts
        ),
    )
    with pytest.raises(ValueError, match="recipe is unsupported"):
        require_scientific_policy(altered, context_profile=profile)


def test_captured_semantic_assets_determine_every_analysis_stage():
    first_profile = acquire_analysis_context_profile()
    changed_profile = replace(
        first_profile,
        implementation_digests=(
            *first_profile.implementation_digests,
            ("grammar/alternate", "changed"),
        ),
    )
    first = prepare_interpretation_context(context_profile=first_profile, macros={})
    changed = prepare_interpretation_context(context_profile=changed_profile, macros={})
    assert changed.model_id != first.model_id
    for demand in ("lexical", "structure", "syntax", "occurrences", "interpretation", "symbolic"):
        assert changed.stage_key(demand) != first.stage_key(demand)
