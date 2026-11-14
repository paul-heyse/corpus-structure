"""Sealed premises for runtime, inference-intent and source-interpretation refusals."""

from dataclasses import dataclass, replace
from typing import Any

from scenario_recipes import register_scenario_builder
from sqlalchemy import select

from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import seal_cut
from corpus_structure.semantic.releases import open_release
from semantic.inference_support import compute, setup
from semantic.local_admission_scenarios import LocalPublicationStage
from semantic.native_record_fixtures import (
    RecordSourceRecipe,
    build_record_recipe,
    candidate,
    claim_record_source,
    complete,
)
from semantic.operation_scenario_support import prepare_operation_scenario

_INTERPRETATION_RECORD_SOURCE = RecordSourceRecipe(composition="interpretations")


@dataclass(frozen=True)
class RuntimeRegistrationRecipe:
    pass


@dataclass(frozen=True)
class RuntimeRegistrationStage:
    prepared: Any

    @property
    def seed_files(self):
        return ()

    def validate_clone(self, admin):
        with admin.connect() as connection:
            assert (
                open_release(connection, self.prepared.release_id).release_id
                == self.prepared.release_id
            )
            assert (
                connection.scalar(select(table("sem.runtime_binding").c.runtime_id).limit(1))
                is None
            )


def build_runtime_registration(recipe, admin, writer, directory, *, purpose_engine=None):
    return RuntimeRegistrationStage(prepare_operation_scenario(admin))


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


@dataclass(frozen=True)
class InterpretationSourceRecipe:
    source: RecordSourceRecipe = _INTERPRETATION_RECORD_SOURCE


@dataclass(frozen=True)
class InterpretationSourceStage(LocalPublicationStage):
    result: Any = None
    data_revision: int = 0

    def validate_clone(self, admin):
        super().validate_clone(admin)
        with admin.connect() as connection:
            assert (
                connection.scalar(
                    select(table("data.realization").c.data_revision).where(
                        table("data.realization").c.realization_id == self.result.realization_id,
                        table("data.realization").c.release_id == self.case.prepared.release_id,
                    )
                )
                == self.data_revision
            )


def build_interpretation_source(recipe, admin, writer, directory, *, purpose_engine=None):
    case = claim_record_source(
        build_record_recipe(recipe.source, admin, writer, directory), writer=writer
    )
    with writer.begin() as connection:
        complete(case, connection, (candidate(case),))
        cut = seal_cut(connection, case.run, "source-final", final=True)
    result = consolidate_cut(writer, cut, "interpretation-source-result")
    with admin.connect() as connection:
        revision = connection.scalar(
            select(table("data.realization").c.data_revision).where(
                table("data.realization").c.realization_id == result.realization_id,
                table("data.realization").c.release_id == case.prepared.release_id,
            )
        )
    return InterpretationSourceStage(
        replace(case, writer=None, clone=None),
        case.run,
        cut,
        result=result,
        data_revision=revision,
    )


register_scenario_builder(RuntimeRegistrationRecipe, build_runtime_registration)
register_scenario_builder(InferenceIntentRecipe, build_inference_intent)
register_scenario_builder(InterpretationSourceRecipe, build_interpretation_source)
