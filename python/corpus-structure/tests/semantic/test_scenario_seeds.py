"""Common seed lifecycle on real PostgreSQL, with explicit fixture-time requests."""

from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path

import pytest
from scenario_recipes import register_scenario_builder


@dataclass(frozen=True)
class TinyRecipe:
    name: str
    unfinished: bool = False
    expired: bool = False
    external_file: bool = False


@dataclass(frozen=True)
class TinyStage:
    name: str
    source: Path

    @property
    def seed_files(self):
        return (self.source,)

    def validate_clone(self, admin):
        with admin.connect() as connection:
            assert (
                connection.exec_driver_sql("SELECT name FROM public.seed_control").scalar_one()
                == self.name
            )
        assert self.source.read_bytes() == self.name.encode()


_BUILDS = Counter()
_DATABASES = []
_PATCH_STATE = {}


def build_tiny_seed(recipe, admin, writer, directory, *, purpose_engine=None):
    _BUILDS[recipe] += 1
    _DATABASES.append(admin.url.database)
    with pytest.MonkeyPatch.context() as patch:
        patch.setitem(_PATCH_STATE, "building", True)
        with admin.begin() as connection:
            connection.exec_driver_sql("CREATE TABLE public.seed_control(name text NOT NULL)")
            connection.exec_driver_sql("GRANT SELECT ON public.seed_control TO PUBLIC")
            connection.exec_driver_sql(
                "INSERT INTO public.seed_control VALUES (%s)", (recipe.name,)
            )
        source = directory / "source.bin"
        if recipe.external_file:
            source = directory.with_name(directory.name + "-external.bin")
        source.write_bytes(recipe.name.encode())
        if recipe.unfinished:
            from semantic.data_operation_demand_support import attach, claim, expire_lease
            from semantic.data_operation_kernel_support import (
                STORAGE,
                Kernel,
                build_kernel,
            )

            stage = build_kernel(STORAGE, admin, writer, directory / "current-kernel")
            kernel = Kernel(writer, stage.preparation, stage.identities, STORAGE)
            attached = attach(kernel)[-1]
            fence = claim(kernel, attached, holder="unfinished-seed")
            if recipe.expired:
                expire_lease(replace(kernel, engine=admin), fence)
    return TinyStage(recipe.name, source)


register_scenario_builder(TinyRecipe, build_tiny_seed)


def test_direct_consumer_uses_one_writable_clone_without_sealing(
    scenario_seeds, native_server, tmp_path
):
    seeds_before = set(native_server.names("ci_seed_"))
    with scenario_seeds.build_for_consumer(TinyRecipe("direct"), tmp_path) as acquired:
        name = acquired.admin.url.database
        assert name is not None and native_server.exists(name)
        assert acquired.origin["acquisition"] == "built-for-consumer"
        assert "source_database" not in acquired.origin
        with acquired.reader.connect() as connection:
            assert (
                connection.exec_driver_sql("SELECT name FROM public.seed_control").scalar_one()
                == "direct"
            )
        acquired.stage.source.write_bytes(b"writable")
    assert not native_server.exists(name)
    assert set(native_server.names("ci_seed_")) == seeds_before


@pytest.fixture
def seed_consumers(scenario_seeds, native_server, monkeypatch):
    import qualification_plugin

    observed = []
    record = qualification_plugin.record_native_context

    def capture(context, **kwargs):
        observed.append(context)
        record(context, **kwargs)

    monkeypatch.setattr(qualification_plugin, "record_native_context", capture)
    recipe = TinyRecipe("shared-prefix")
    sessions = native_server.names("ci_test_")
    first = scenario_seeds.seed(recipe)
    second = scenario_seeds.seed(TinyRecipe("shared-prefix"))
    assert first is second
    with scenario_seeds.commit_clone(recipe) as clone:
        with clone.reader.connect() as connection:
            assert (
                connection.exec_driver_sql("SELECT name FROM public.seed_control").scalar_one()
                == recipe.name
            )
        commit_oid = clone.database_oid
    with scenario_seeds.rollback_family(recipe) as family:
        first_family = family.connection.engine.url.database
        family.connection.exec_driver_sql("UPDATE public.seed_control SET name='rolled back'")
        assert (
            family.connection.exec_driver_sql("SELECT name FROM public.seed_control").scalar_one()
            == "rolled back"
        )
        with family.reader.connect() as reader:
            assert (
                reader.exec_driver_sql("SELECT name FROM public.seed_control").scalar_one()
                == recipe.name
            )
    with scenario_seeds.rollback_family(recipe) as next_case:
        assert next_case.connection.engine.url.database == first_family
        assert (
            next_case.connection.exec_driver_sql(
                "SELECT name FROM public.seed_control"
            ).scalar_one()
            == recipe.name
        )
    yield first, commit_oid, observed, _BUILDS[recipe], native_server.names("ci_test_") == sessions


def test_equal_recipe_builds_once_with_read_only_files_and_seed_origin(seed_consumers):
    seed, clone_oid, observed, builds, no_session_clone = seed_consumers
    assert builds == 1 and no_session_clone
    assert clone_oid != seed.database_oid
    assert "building" not in _PATCH_STATE
    source = seed.stage.seed_files[0]
    with pytest.raises(PermissionError):
        source.write_bytes(b"changed")
    origins = [
        context["acquired"]["scenario_seed"]
        for context in observed
        if context.get("acquired", {}).get("scenario_seed")
    ]
    assert origins and all(origin == seed.origin for origin in origins)
    assert {
        context["requested"]["purpose"]
        for context in observed
        if context.get("acquired", {}).get("scenario_seed")
    } >= {"maintenance", "read"}


@pytest.fixture(params=[False, True], ids=["active", "expired"])
def unfinished_seed_refusal(request, scenario_seeds, native_server):
    before = len(_DATABASES)
    recipe = TinyRecipe("unfinished-" + str(request.param), unfinished=True, expired=request.param)
    with pytest.raises(RuntimeError, match="unfinished task"):
        scenario_seeds.seed(recipe)
    names = _DATABASES[before:]
    return names, [native_server.exists(name) for name in names]


def test_claimed_task_refuses_seed_even_after_lease_expiry(unfinished_seed_refusal):
    names, remains = unfinished_seed_refusal
    assert len(names) == 1 and remains == [False]
    assert "building" not in _PATCH_STATE


@pytest.fixture
def external_file_refusal(scenario_seeds, native_server):
    before = len(_DATABASES)
    with pytest.raises(ValueError, match="owned by the supplied seed directory"):
        scenario_seeds.seed(TinyRecipe("external", external_file=True))
    names = _DATABASES[before:]
    return names, [native_server.exists(name) for name in names]


def test_external_reusable_files_cannot_enter_a_seed(external_file_refusal):
    names, remains = external_file_refusal
    assert len(names) == 1 and remains == [False]
