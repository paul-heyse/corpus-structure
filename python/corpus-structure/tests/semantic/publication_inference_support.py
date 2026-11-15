"""Frozen inference intent for independent publication transport controls."""

from dataclasses import dataclass
from typing import Any

from scenario_recipes import register_scenario_builder
from sqlalchemy import select

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.releases import open_release
from semantic.inference_support import compute, setup


@dataclass(frozen=True)
class InferenceIntentRecipe:
    edges: tuple[tuple[str, str], ...] = (("a", "b"), ("b", "c"))
    rules: tuple[str, ...] = ("transitive",)


@dataclass(frozen=True)
class InferenceIntentStage:
    result: Any

    @property
    def seed_files(self):
        return ()

    def validate_clone(self, admin):
        binding = self.result.binding
        with admin.connect() as connection:
            assert open_release(connection, binding.release_id).release_id == binding.release_id
            assert (
                connection.scalar(
                    select(table("data.realization").c.data_revision).where(
                        table("data.realization").c.release_id == binding.release_id,
                        table("data.realization").c.realization_id == binding.realization_id,
                    )
                )
                == binding.data_revision
            )
            assert tuple(connection.scalars(select(table("data.batch").c.batch_id))) == ("sources",)


def build_inference_intent(recipe, admin, writer, directory, *, purpose_engine=None):
    binding, _ = setup(admin, writer, recipe.edges, rules=recipe.rules)
    return InferenceIntentStage(compute(writer, binding))


register_scenario_builder(InferenceIntentRecipe, build_inference_intent)
