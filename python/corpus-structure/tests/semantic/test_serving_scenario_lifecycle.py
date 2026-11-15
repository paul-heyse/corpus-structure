"""Common seed identity, cleanup and fresh-clone serving isolation."""

from dataclasses import dataclass, replace

import pytest
from scenario_recipes import register_scenario_builder
from sqlalchemy import select

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.data_operation_demands import DemandPlanner, RootSubject, freeze_demand
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from semantic.serving_scenarios import declared_serving_case as serving_read_scenario
from semantic.serving_scenarios import declared_serving_seed as serving_scenario_seed


@dataclass(frozen=True)
class FailedServingRecipe:
    name: str = "failed-serving"


_FAILED_DATABASES = []


def _fail_serving_build(recipe, admin, writer, directory, *, purpose_engine=None):
    _FAILED_DATABASES.append(admin.url.database)
    raise RuntimeError("partial serving scenario build")


register_scenario_builder(FailedServingRecipe, _fail_serving_build)


@pytest.fixture
def second_serving_clone(scenario_seeds, serving_scenario_seed):
    with scenario_seeds.commit_clone(serving_scenario_seed.recipe) as clone:
        yield clone


@pytest.fixture
def failed_serving_seed(scenario_seeds, native_server):
    before = len(_FAILED_DATABASES)
    with pytest.raises(RuntimeError, match="partial serving scenario build"):
        scenario_seeds.seed(FailedServingRecipe())
    created = _FAILED_DATABASES[before:]
    return created, [native_server.exists(name) for name in created]


def test_changed_seed_recipe_is_refused(serving_scenario_seed, scenario_seeds):
    scenario_seeds.validate(serving_scenario_seed)
    altered = replace(serving_scenario_seed, recipe_id="0" * 64)
    with pytest.raises(RuntimeError, match="recipe identity changed"):
        scenario_seeds.validate(altered)


def test_two_fresh_serving_clones_are_isolated(
    serving_scenario_seed, serving_read_scenario, second_serving_clone
):
    seed, first, second = serving_scenario_seed, serving_read_scenario, second_serving_clone
    assert len({seed.database_oid, first.database_oid, second.database_oid}) == 3
    agent = seed.stage.agent
    frozen = freeze_demand(
        agent.kernel.preparation.model,
        roots=(RootSubject("isolated", agent.original_source, b'{}'),),
        targets=("urn:ddo-test:source",),
        inference="scenario-isolation-test",
        execution_profile="execution:test",
    )
    with second.writer.begin() as connection:
        demand = DemandPlanner(agent.kernel.preparation.model, DataOperationStorage(connection)).register(
            frozen, project=agent.project_id, release=agent.prepared.release_id, runtime=agent.runtime
        )["demand_id"]
    demands = table("ops.data_demand")
    with second.admin.connect() as connection:
        assert connection.scalar(select(demands.c.id).where(demands.c.id == demand)) == demand
    with first.admin.connect() as connection:
        assert connection.scalar(select(demands.c.id).where(demands.c.id == demand)) is None


def test_failed_seed_build_releases_owned_database(failed_serving_seed):
    names, exists = failed_serving_seed
    assert len(names) == 1
    assert exists == [False]
