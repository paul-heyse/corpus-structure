"""Seed identity, cleanup, and fresh-clone isolation for repeated serving journeys."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import select

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding, create_run
from native_test_support import principal_engine

from . import serving_scenarios
from .serving_scenarios import (
    _validate_serving_seed,
)
from .serving_scenarios import (
    serving_read_scenario as serving_read_scenario,
)
from .serving_scenarios import (
    serving_scenario_seed as serving_scenario_seed,
)


def test_changed_seed_recipe_is_refused(serving_scenario_seed, native_server):
    altered = replace(serving_scenario_seed, source_manifest_digest="0" * 64)
    with pytest.raises(AssertionError, match="recipe or prepared source identity changed"):
        _validate_serving_seed(native_server, altered)


def test_two_fresh_serving_clones_are_isolated(
    serving_scenario_seed,
    serving_read_scenario,
    native_server,
    native_settings,
):
    seed = serving_scenario_seed
    first = serving_read_scenario
    second_name = f"cs_sem_test_{uuid4().hex[:20]}"
    with native_server.database(second_name, seed.database, policy=seed.policy) as admin:
        second_oid = serving_scenarios._database_oid(native_server, second_name)
        assert second_oid != seed.database_oid
        writer = principal_engine(native_settings, "write", second_name, scenario_seed=seed.origin)
        try:
            with writer.begin() as conn:
                second_run = create_run(
                    conn,
                    project_id="resubmit",
                    binding=OperationBinding(seed.prepared.release_id, "input", 0, b"{}"),
                    kind="full",
                    options={},
                    code_commit="scenario-isolation-test",
                )
            with writer.connect() as conn:
                assert (
                    conn.execute(
                        select(table("ops.run").c.id).where(table("ops.run").c.id == second_run)
                    ).scalar_one()
                    == second_run
                )
            with first.reader.connect() as conn:
                assert (
                    conn.execute(
                        select(table("ops.run").c.id).where(table("ops.run").c.id == second_run)
                    ).scalar_one_or_none()
                    is None
                )
        finally:
            writer.dispose()
            admin.dispose()


def test_failed_seed_build_releases_owned_database(
    native_server,
    semantic_head_template,
    native_settings,
    tmp_path_factory,
):
    captured: list[str] = []

    def fail_after_acquisition(admin, writer, tmp_path):
        captured.append(admin.url.database)
        raise RuntimeError("partial serving scenario build")

    generator = serving_scenarios._serving_seed_lifecycle(
        native_server,
        semantic_head_template,
        native_settings,
        tmp_path_factory,
        scenario_builder=fail_after_acquisition,
    )
    with pytest.raises(RuntimeError, match="partial serving scenario build"):
        next(generator)
    assert len(captured) == 1
    assert not native_server.exists(captured[0])
