"""Immutable recipe identity and owned-file boundaries without native acquisition."""

from dataclasses import dataclass
from typing import Any, cast

import pytest

from native_scenario_seeds import _freeze_tree, _restore_tree, recipe_id


@dataclass(frozen=True)
class Recipe:
    name: str
    source: bytes = b"source"
    options: tuple[str, ...] = ()


@dataclass(frozen=True)
class OtherRecipe:
    name: str
    source: bytes = b"source"
    options: tuple[str, ...] = ()


def test_recipe_identity_includes_exact_recipe_type_and_immutable_values():
    assert recipe_id(Recipe("case")) == recipe_id(Recipe("case"))
    assert recipe_id(Recipe("case")) != recipe_id(OtherRecipe("case"))
    assert recipe_id(Recipe("case")) != recipe_id(Recipe("case", b"changed"))
    assert recipe_id(Recipe("case")) != recipe_id(Recipe("case", options=("extra",)))


def test_recipe_identity_refuses_callable_and_mutable_recipe_values():
    with pytest.raises(TypeError):
        recipe_id(Recipe("case", options=cast(Any, ["mutable"])))
    with pytest.raises(TypeError):
        recipe_id(Recipe("case", source=cast(Any, lambda: b"source")))


def test_seed_files_and_directory_are_read_only_until_owner_cleanup(tmp_path):
    directory = tmp_path / "owned"
    directory.mkdir()
    source = directory / "source.bin"
    source.write_bytes(b"immutable source")
    modes = {}
    try:
        _freeze_tree(directory, modes)
        assert source.read_bytes() == b"immutable source"
        with pytest.raises(PermissionError):
            source.write_bytes(b"changed")
        with pytest.raises(PermissionError):
            (directory / "new-file").write_bytes(b"new")
    finally:
        _restore_tree(modes)
    source.write_bytes(b"owner cleanup")


def test_seed_freezing_rejects_links_without_changing_external_file(tmp_path):
    directory = tmp_path / "owned"
    directory.mkdir()
    external = tmp_path / "external.bin"
    external.write_bytes(b"another owner")
    mode = external.stat().st_mode
    (directory / "linked.bin").symlink_to(external)
    with pytest.raises(ValueError, match="symbolic links"):
        _freeze_tree(directory, {})
    assert external.stat().st_mode == mode


@pytest.mark.parametrize("counts", [(1, 0), (1, 1)])
def test_seed_validation_waits_for_exit_but_refuses_persistent_backends(monkeypatch, counts):
    from contextlib import contextmanager
    from types import SimpleNamespace

    import native_test_support
    from native_scenario_seeds import ScenarioSeeds
    from native_test_support import PgAdmin

    observed = []
    pending = iter(counts)

    class Connection:
        def execute(self, statement, parameters):
            assert "pg_stat_activity" in str(statement)
            assert parameters == {"name": "owned-seed"}
            count = next(pending)
            observed.append(count)
            return SimpleNamespace(scalar_one=lambda: count)

    @contextmanager
    def connect():
        yield Connection()

    # Exercise the shared bounded waiter with a deterministic deadline rather
    # than spending two seconds on the deliberate persistent-session control.
    clock = iter((0.0, 0.0, 3.0))
    monkeypatch.setattr(
        native_test_support,
        "time",
        SimpleNamespace(monotonic=lambda: next(clock), sleep=lambda _: None),
    )
    recipe = Recipe("case")
    policy = object()
    server = SimpleNamespace(
        _deployment_record=lambda _: (42, None, "owned", True, False, False),
        owned_comment=lambda comment, oid: (comment, oid) == ("owned", 42),
        policy=lambda _: policy,
        connect=connect,
        _wait_for_backend_exit=PgAdmin._wait_for_backend_exit,
    )
    registry = ScenarioSeeds(cast(Any, server), cast(Any, None), cast(Any, None), cast(Any, None))
    seed = SimpleNamespace(
        recipe=recipe,
        recipe_id=recipe_id(recipe),
        database="owned-seed",
        database_oid=42,
        policy=policy,
    )
    if counts[-1]:
        with pytest.raises(RuntimeError, match="still has connected backends"):
            registry.validate(cast(Any, seed))
    else:
        registry.validate(cast(Any, seed))
    assert observed == list(counts)
