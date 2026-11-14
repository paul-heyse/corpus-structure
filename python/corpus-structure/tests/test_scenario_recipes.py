"""A scenario recipe has one explicit builder owner, selected by its exact type."""

from dataclasses import dataclass

import pytest
from scenario_recipes import register_scenario_builder, scenario_builder


def test_recipe_values_find_their_registered_builder():
    @dataclass(frozen=True)
    class Recipe:
        composition: str

    def build(recipe, admin, writer, directory, *, purpose_engine):
        return recipe.composition, admin, writer, directory, purpose_engine

    register_scenario_builder(Recipe, build)
    first, same = Recipe("controlled"), Recipe("controlled")
    assert first == same and hash(first) == hash(same)
    assert scenario_builder(same) is build
    assert scenario_builder(same)(
        same, "admin", "writer", "directory", purpose_engine="purposes"
    ) == (
        "controlled",
        "admin",
        "writer",
        "directory",
        "purposes",
    )


def test_duplicate_recipe_owner_refuses_without_replacing_the_original():
    @dataclass(frozen=True)
    class Recipe:
        pass

    def original(*args, **kwargs):
        return "original"

    register_scenario_builder(Recipe, original)
    with pytest.raises(ValueError, match="scenario recipe already has a builder: Recipe"):
        register_scenario_builder(Recipe, lambda *args, **kwargs: "replacement")
    assert scenario_builder(Recipe()) is original


def test_unregistered_subtype_does_not_inherit_another_recipes_builder():
    @dataclass(frozen=True)
    class BaseRecipe:
        pass

    @dataclass(frozen=True)
    class OtherRecipe(BaseRecipe):
        pass

    register_scenario_builder(BaseRecipe, lambda *args, **kwargs: None)
    with pytest.raises(ValueError, match="unknown scenario recipe type: OtherRecipe"):
        scenario_builder(OtherRecipe())
