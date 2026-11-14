"""Real pure preparation lifetimes, including exception-safe override isolation."""

from dataclasses import replace

import pytest

from corpus_structure.semantic.contracts import (
    current_implementation,
    implementation_override,
)
from semantic.agent_scenarios import (
    ResubmissionPreparationRecipe,
    prepare_resubmission_case,
)
from semantic.domain_scenarios import DomainPreparationRecipe, prepare_domain_case


@pytest.mark.parametrize(
    ("prepare", "recipe", "change"),
    [
        (prepare_domain_case, DomainPreparationRecipe(), {"global_person_identity": True}),
        (prepare_resubmission_case, ResubmissionPreparationRecipe(), {"identity_keyed": True}),
    ],
    ids=["domain", "resubmission"],
)
def test_preparation_reuses_only_ordinary_matching_inputs(prepare, recipe, change):
    ordinary = prepare(recipe)
    assert prepare(recipe) is ordinary
    changed = prepare(replace(recipe, **change))
    assert changed is not ordinary
    assert changed.prepared.release_id != ordinary.prepared.release_id
    assert prepare(recipe) is ordinary

    with (
        pytest.raises(RuntimeError, match="leave nested override"),
        implementation_override(current_implementation()),
    ):
        first = prepare(recipe)
        assert first is not ordinary
        assert first.prepared.release_id == ordinary.prepared.release_id
        with implementation_override(current_implementation()):
            assert prepare(recipe) is not first
            raise RuntimeError("leave nested override")
    assert prepare(recipe) is ordinary


def test_formula_prefix_key_excludes_consumer_expressions_and_retains_source_variants():
    from native_scenario_seeds import recipe_id
    from semantic.domain_scenarios import domain_case_recipe

    first = domain_case_recipe(formulas=("x + 1",))
    second = domain_case_recipe(formulas=("y + 2",))
    assert first.source_recipe == second.source_recipe
    assert recipe_id(first.source_recipe) == recipe_id(second.source_recipe)
    assert recipe_id(first) != recipe_id(second)
    assert first.source_recipe != domain_case_recipe().source_recipe
    assert (
        first.source_recipe
        != domain_case_recipe(formulas=("x + 1",), global_person_identity=True).source_recipe
    )


def test_domain_recipe_owns_canonical_configuration_values():
    from native_scenario_seeds import recipe_id
    from semantic.domain_scenarios import domain_case_recipe

    condition = {"operator": "and", "arguments": [{"symbol": "x"}]}
    recipe = domain_case_recipe(condition=condition)
    before = recipe_id(recipe)
    condition["arguments"].append({"symbol": "y"})
    assert recipe.condition == b'{"arguments":[{"symbol":"x"}],"operator":"and"}'
    assert recipe_id(recipe) == before
    assert recipe == domain_case_recipe(
        condition={"arguments": [{"symbol": "x"}], "operator": "and"}
    )


def test_resubmission_and_exclusion_seed_keys_retain_semantic_variants():
    from native_scenario_seeds import recipe_id
    from semantic.agent_scenarios import ExclusionRecipe, ResubmissionRecipe

    assert recipe_id(ResubmissionRecipe()) != recipe_id(ResubmissionRecipe(composed=True))
    baseline = recipe_id(ExclusionRecipe())
    variants = (
        ExclusionRecipe(finalize=True),
        ExclusionRecipe(citations=2),
        ExclusionRecipe(keyed=True),
        ExclusionRecipe(attribute_assertions=True),
        ExclusionRecipe(global_names=True),
        ExclusionRecipe(local_ids=("p_", "q")),
        ExclusionRecipe(reason="authored amendment"),
    )
    assert all(recipe_id(variant) != baseline for variant in variants)
