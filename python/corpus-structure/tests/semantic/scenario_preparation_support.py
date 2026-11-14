"""Immutable pure preparation shared by native scenario stage consumers."""

from dataclasses import dataclass

from sqlalchemy import Engine

from corpus_structure.semantic.types import (
    PreparationProfile,
    PreparedRelease,
    ResolvedDependencies,
    SourceBundle,
)


@dataclass(frozen=True)
class ScenarioPreparation[Recipe]:
    recipe: Recipe
    bundle: SourceBundle
    dependencies: ResolvedDependencies
    profile: PreparationProfile
    prepared: PreparedRelease


@dataclass(frozen=True)
class PersistedScenario[Recipe]:
    preparation: ScenarioPreparation[Recipe]
    writer: Engine

    @property
    def prepared(self) -> PreparedRelease:
        return self.preparation.prepared
