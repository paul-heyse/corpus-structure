"""Engine-free original-source premises beside an admitted target kernel."""

from dataclasses import dataclass
from typing import Any

from scenario_recipes import register_scenario_builder

from semantic.data_operation_kernel_support import (
    Kernel,
    KernelRecipe,
    KernelSeedStage,
    admit_kernel,
    prepare_kernel,
)
from semantic.native_record_fixtures import (
    RecordSourceRecipe,
    RecordTaskSource,
    build_record_recipe,
)


@dataclass(frozen=True)
class OriginalSeedRecipe:
    source: RecordSourceRecipe
    target: KernelRecipe


@dataclass(frozen=True)
class OriginalSeedStage:
    source: RecordTaskSource
    kernel: KernelSeedStage

    @property
    def seed_files(self):
        return self.source.seed_files + self.kernel.seed_files

    def validate_clone(self, admin):
        self.source.validate_clone(admin)
        self.kernel.validate_clone(admin)


@dataclass(frozen=True)
class OriginalSourceCase:
    source: RecordTaskSource
    kernel: Kernel
    clone: Any

    @property
    def admin(self):
        return self.clone.admin

    @property
    def writer(self):
        return self.clone.writer


def build_original_seed(recipe, admin, writer, directory, *, purpose_engine=None):
    record_directory = directory / "record"
    kernel_directory = directory / "kernel"
    record_directory.mkdir()
    kernel_directory.mkdir()
    source = build_record_recipe(recipe.source, admin, writer, record_directory)
    preparation = prepare_kernel(recipe.target, directory=kernel_directory)
    with admin.begin() as connection:
        admitted = admit_kernel(connection, recipe.target, engine=admin, preparation=preparation)
    return OriginalSeedStage(
        source, KernelSeedStage(preparation, admitted.identities, recipe.target)
    )


register_scenario_builder(OriginalSeedRecipe, build_original_seed)


def original_source_clone(request, scenario_seeds):
    recipe = getattr(request, "param", None)
    if not isinstance(recipe, OriginalSeedRecipe):
        raise TypeError("ddo_original_source requires an explicit OriginalSeedRecipe")
    with scenario_seeds.commit_clone(recipe) as clone:
        stage = clone.stage
        if not isinstance(stage, OriginalSeedStage):
            raise TypeError("original recipe produced a different stage")
        kernel = Kernel(
            clone.admin, stage.kernel.preparation, stage.kernel.identities, recipe.target, clone
        )
        yield OriginalSourceCase(stage.source, kernel, clone)
