"""Common seed identity, cleanup and fresh-clone serving isolation."""

from dataclasses import dataclass, replace

import pytest
from scenario_recipes import register_scenario_builder
from sqlalchemy import select

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding, create_run
from semantic.serving_scenarios import serving_read_scenario as serving_read_scenario
from semantic.serving_scenarios import serving_scenario_seed as serving_scenario_seed


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
    with second.writer.begin() as connection:
        second_run = create_run(
            connection,
            project_id="resubmit",
            binding=OperationBinding(seed.stage.prepared.release_id, "input", 0, b"{}"),
            kind="full",
            options={},
            code_commit="scenario-isolation-test",
        )
    with second.writer.connect() as connection:
        assert (
            connection.execute(
                select(table("ops.run").c.id).where(table("ops.run").c.id == second_run)
            ).scalar_one()
            == second_run
        )
    with first.reader.connect() as connection:
        assert (
            connection.execute(
                select(table("ops.run").c.id).where(table("ops.run").c.id == second_run)
            ).scalar_one_or_none()
            is None
        )


def test_failed_seed_build_releases_owned_database(failed_serving_seed):
    names, exists = failed_serving_seed
    assert len(names) == 1
    assert exists == [False]
