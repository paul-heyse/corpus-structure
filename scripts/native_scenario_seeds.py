"""Worker-owned sealed scenario seeds, using PgAdmin's authenticated clone lifetime."""

from __future__ import annotations

import dataclasses
import json
import math
import stat
import threading
from collections.abc import Callable, Generator, Mapping
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from sqlalchemy import Engine, text

from corpus_structure.semantic.contracts import implementation_overridden
from corpus_structure.settings import Settings
from native_test_support import (
    DatabasePolicy,
    PgAdmin,
    RollbackCase,
    SemanticDeployment,
    database_name,
    principal_engine,
    rollback_case,
)

if TYPE_CHECKING:
    from corpus_structure.semantic.runtime import Purpose


def _recipe_value(value: object) -> object:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        if not getattr(getattr(type(value), "__dataclass_params__", None), "frozen", False):
            raise TypeError("scenario recipes must be frozen values")
        return {
            "type": type(value).__module__ + "." + type(value).__qualname__,
            "fields": {
                field.name: _recipe_value(getattr(value, field.name))
                for field in dataclasses.fields(value)
            },
        }
    if isinstance(value, bytes):
        return {"bytes": value.hex()}
    if isinstance(value, tuple):
        return [_recipe_value(item) for item in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise TypeError("scenario recipes contain only immutable data values")


def recipe_id(recipe: object) -> str:
    hash(recipe)
    return sha256(
        json.dumps(_recipe_value(recipe), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@runtime_checkable
class SeedStage(Protocol):
    @property
    def seed_files(self) -> tuple[Path, ...]: ...

    def validate_clone(self, admin: Engine) -> None: ...


@dataclass(frozen=True)
class ScenarioSeed[Stage: SeedStage]:
    database: str
    database_oid: int
    policy: DatabasePolicy
    recipe: object
    recipe_id: str
    head: str
    stage: Stage
    directory: Path

    @property
    def origin(self) -> dict[str, str]:
        label = getattr(
            self.recipe,
            "label",
            type(self.recipe).__module__ + "." + type(self.recipe).__qualname__,
        )
        if not isinstance(label, str):
            raise TypeError("scenario recipe label must be text")
        fields = {
            "scenario": label,
            "recipe_id": self.recipe_id,
            "source_database": self.database,
            "source_database_oid": str(self.database_oid),
            "head": self.head,
        }
        extras = getattr(self.stage, "seed_origin", {})
        if not isinstance(extras, Mapping) or any(
            not isinstance(key, str) or not isinstance(value, str) for key, value in extras.items()
        ):
            raise TypeError("scenario origin additions must be string mappings")
        if fields.keys() & extras.keys():
            raise ValueError("scenario origin additions cannot replace acquired seed identity")
        return fields | dict(extras)


class SeedClone[Stage: SeedStage]:
    """A frozen stage beside fresh clone engines; stage resource rebinding is explicit."""

    def __init__(
        self, seed: ScenarioSeed[Stage], admin: Engine, settings: Settings, database_oid: int
    ):
        self.seed = seed
        self.stage = seed.stage
        self.admin = admin
        self.origin = seed.origin
        self._settings = settings
        self._purposes: dict[str, Engine] = {}
        self.database_oid = database_oid

    def purpose(self, purpose) -> Engine:
        if purpose not in self._purposes:
            engine = principal_engine(
                self._settings, purpose, self.admin.url.database, scenario_seed=self.origin
            )
            try:
                with engine.connect() as connection:
                    database, oid, current, session = connection.exec_driver_sql(
                        "SELECT current_database(),(SELECT oid FROM pg_database "
                        "WHERE datname=current_database()),current_user,session_user"
                    ).one()
                if (database, oid) != (self.admin.url.database, self.database_oid):
                    raise RuntimeError(
                        "scenario purpose connection did not acquire its owned clone"
                    )
                if engine.url.username is None or (current, session) != (engine.url.username,) * 2:
                    raise RuntimeError(
                        "scenario purpose connection did not authenticate its declared login"
                    )
            except BaseException:
                engine.dispose()
                raise
            self._purposes[purpose] = engine
        return self._purposes[purpose]

    @property
    def writer(self) -> Engine:
        return self.purpose("write")

    @property
    def reader(self) -> Engine:
        return self.purpose("read")

    @property
    def evaluator(self) -> Engine:
        return self.purpose("evaluate")

    @property
    def admitter(self) -> Engine:
        return self.purpose("admit")

    def close(self) -> None:
        for engine in self._purposes.values():
            engine.dispose()


def _freeze_tree(directory: Path, modes: dict[Path, int]) -> None:
    paths = [*directory.rglob("*"), directory]
    if any(path.is_symlink() for path in paths):
        raise ValueError("scenario seed files cannot be symbolic links")
    for path in sorted(paths, key=lambda item: len(item.parts), reverse=True):
        modes[path] = stat.S_IMODE(path.stat().st_mode)
        path.chmod(modes[path] & ~0o222)


def _restore_tree(modes: dict[Path, int]) -> None:
    for path, mode in sorted(modes.items(), key=lambda item: len(item[0].parts)):
        if path.exists():
            path.chmod(mode)


class ScenarioSeeds:
    def __init__(
        self,
        server: PgAdmin,
        head: SemanticDeployment,
        settings: Settings,
        directory: Callable[[str], Path],
    ):
        self.server, self.head, self.settings = server, head, settings
        self._directory = directory
        self._seeds: dict[tuple[object, str], ScenarioSeed] = {}
        self._families: dict[tuple[object, str], str] = {}
        self._seed_lifetime = ExitStack()
        self._family_lifetime = ExitStack()
        self._lock = threading.RLock()
        self._closed = False

    def seed(self, recipe: object) -> ScenarioSeed:
        if self._closed:
            raise RuntimeError("scenario seed registry is closed")
        if implementation_overridden():
            raise RuntimeError(
                "scenario seed acquisition is unavailable under an implementation override"
            )
        identity = recipe_id(recipe)
        with self._lock:
            key = recipe, self.head.name
            if key in self._seeds:
                seed = self._seeds[key]
                self.validate(seed)
                return seed
            from scenario_recipes import scenario_builder

            name = database_name("seed").name
            directory = self._directory("seed-" + type(recipe).__name__)
            with ExitStack() as lifetime:
                admin = lifetime.enter_context(self.head.clone(name))
                with ExitStack() as build_resources:

                    def purpose_engine(purpose):
                        engine = principal_engine(self.settings, purpose, name)
                        build_resources.callback(engine.dispose)
                        return engine

                    writer = purpose_engine("write")
                    stage = scenario_builder(recipe)(
                        recipe, admin, writer, directory, purpose_engine=purpose_engine
                    )
                if not isinstance(stage, SeedStage):
                    raise TypeError(
                        "seed builders must declare seed_files and validate_clone(admin)"
                    )
                if not dataclasses.is_dataclass(stage) or not getattr(
                    getattr(type(stage), "__dataclass_params__", None), "frozen", False
                ):
                    raise TypeError("scenario seed stage output must be a frozen dataclass")
                if not isinstance(stage.seed_files, tuple):
                    raise TypeError("scenario seed files must be an immutable tuple of paths")
                for path in stage.seed_files:
                    if not isinstance(path, Path) or not path.resolve().is_relative_to(
                        directory.resolve()
                    ):
                        raise ValueError(
                            "seed runtime/source files must be owned by the supplied seed directory"
                        )
                    if not path.exists():
                        raise ValueError("declared scenario seed file is unavailable")
                stage.validate_clone(admin)
                with admin.connect() as connection:
                    unfinished = connection.execute(
                        text(
                            "SELECT id,status FROM ops.task "
                            "WHERE status::text IN ('claimed','running') ORDER BY id LIMIT 1"
                        )
                    ).one_or_none()
                if unfinished is not None:
                    raise RuntimeError(
                        f"scenario seed has unfinished task {unfinished[0]} ({unfinished[1]})"
                    )
                if self.server.policy(name) != self.head.policy:
                    raise RuntimeError("scenario seed changed its deployed database policy")
                acquired = self.server._deployment_record(name)
                if acquired is None:
                    raise RuntimeError("scenario seed database disappeared before sealing")
                oid = acquired[0]
                admin.dispose()
                self.server.seal_database(name)
                modes: dict[Path, int] = {}
                lifetime.callback(_restore_tree, modes)
                _freeze_tree(directory, modes)
                seed = ScenarioSeed(
                    name, oid, self.head.policy, recipe, identity, self.head.name, stage, directory
                )
                self.validate(seed)
                self._seed_lifetime.enter_context(lifetime.pop_all())
                self._seeds[(recipe, self.head.name)] = seed
                return seed

    def validate(self, seed: ScenarioSeed) -> None:
        if recipe_id(seed.recipe) != seed.recipe_id:
            raise RuntimeError("scenario seed recipe identity changed")
        record = self.server._deployment_record(seed.database)
        if (
            record is None
            or record[0] != seed.database_oid
            or not record[3]
            or not self.server.owned_comment(record[2], record[0])
        ):
            raise RuntimeError("scenario seed acquired database identity changed")
        if record[4] or record[5] or self.server.policy(seed.database) != seed.policy:
            raise RuntimeError("scenario seed is not sealed with its captured policy")
        with self.server.connect() as connection:
            clients = connection.execute(
                text("SELECT count(*) FROM pg_stat_activity WHERE datname=:name"),
                {"name": seed.database},
            ).scalar_one()
        if clients:
            raise RuntimeError("scenario seed has connected backends")

    @contextmanager
    def commit_clone(self, recipe: object) -> Generator[SeedClone]:
        seed = self.seed(recipe)
        with self.server.database(
            database_name("test").name, seed.database, policy=seed.policy, scenario_seed=seed.origin
        ) as admin:
            stage = seed.stage
            stage.validate_clone(admin)
            database = admin.url.database
            assert database is not None
            acquired = self.server._deployment_record(database)
            if acquired is None or acquired[0] == seed.database_oid:
                raise RuntimeError("scenario consumer must acquire a fresh clone OID")
            clone = SeedClone(seed, admin, self.settings, acquired[0])
            try:
                yield clone
            finally:
                clone.close()

    @contextmanager
    def rollback_family(
        self, recipe: object, *, reader_purpose: Purpose = "read"
    ) -> Generator[RollbackCase]:
        seed = self.seed(recipe)
        key = recipe, seed.head
        with self._lock:
            if key not in self._families:
                engine = self._family_lifetime.enter_context(
                    self.server.database(
                        database_name("test").name,
                        seed.database,
                        policy=seed.policy,
                        scenario_seed=seed.origin,
                    )
                )
                seed.stage.validate_clone(engine)
                database = engine.url.database
                assert database is not None
                self._families[key] = database
            name = self._families[key]
        with rollback_case(
            self.server,
            self.settings,
            name,
            scenario_seed=seed.origin,
            stage=seed.stage,
            reader_purpose=reader_purpose,
        ) as case:
            yield case

    def close(self) -> None:
        try:
            self._family_lifetime.close()
        finally:
            try:
                self._seed_lifetime.close()
            finally:
                self._closed = True
