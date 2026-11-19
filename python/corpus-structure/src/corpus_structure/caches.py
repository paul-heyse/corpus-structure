"""Process-owned bounded retention for independently authenticated derived values."""

from __future__ import annotations

import os
from collections.abc import Callable, Hashable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import update_wrapper
from threading import Condition, RLock
from typing import Literal, Protocol, cast

from cachetools import Cache, LRUCache, cached
from cachetools.keys import hashkey
from pydantic import BaseModel, ConfigDict

from corpus_structure.settings import CacheSettings

type Budget = Literal[
    "model_entries",
    "program_sets",
    "release_bytes",
    "runtime_bytes",
    "parser_entries",
    "parse_memo_entries",
]


class CacheMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    budget: str
    entries: int | None = None
    size: int | None = None
    maxsize: int | None = None
    hits: int | None = None
    misses: int | None = None
    coalesced: int | None = None
    admission_skips: int | None = None
    evictions: int | None = None


class CacheObservation(CacheMetrics):
    name: str


class CacheSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    pid: int
    owner: str
    started_at: datetime
    observed_at: datetime
    generation: int
    settings: CacheSettings
    caches: tuple[CacheObservation, ...]


@dataclass(frozen=True)
class _Value:
    value: object
    weight: int


@dataclass
class _Storage:
    cache: LRUCache[tuple[str, Hashable], _Value]
    lock: RLock
    wrappers: dict[str, object] = field(default_factory=dict)


class _Counters(Protocol):
    @property
    def hits(self) -> int: ...

    @property
    def misses(self) -> int: ...

    @property
    def maxsize(self) -> float | None: ...

    @property
    def currsize(self) -> float: ...


class _Memoized[**P](Protocol):
    def __call__(self, /, *args: P.args, **kwargs: P.kwargs) -> _Value: ...

    def cache_info(self) -> _Counters: ...


_lock = RLock()
_config = CacheSettings()
_started = datetime.now(UTC)
_generation = 0
_storages: dict[Budget, _Storage] = {}
_observers: dict[str, tuple[Callable[[], CacheMetrics], Callable[[], None] | None]] = {}


def _release_storages(budgets: tuple[Budget, ...]) -> None:
    for budget in budgets:
        storage = _storages.pop(budget, None)
        if storage is not None:
            with storage.lock:
                storage.cache.clear()


def configured() -> CacheSettings:
    with _lock:
        return _config


def configure(settings: CacheSettings) -> None:
    """Select a fresh storage generation when the process budget changes."""
    global _config, _generation
    with _lock:
        if _config == settings:
            return
        _config = settings
        _release_storages(tuple(_storages))
        _generation += 1
        resets = [reset for _, reset in _observers.values() if reset is not None]
    for reset in resets:
        reset()


def register(
    name: str,
    inspect: Callable[[], CacheMetrics],
    clear: Callable[[], None] | None = None,
) -> None:
    """Register a snapshot of an explicit cache or an independently owned lifecycle."""
    with _lock:
        _observers[name] = (inspect, clear)


def clear(*budgets: Budget) -> None:
    """Release held entries and reset their counters without waiting for running loaders."""
    global _generation
    with _lock:
        _generation += 1
        _release_storages(budgets or tuple(_storages))
        resets = [] if budgets else [reset for _, reset in _observers.values() if reset is not None]
    for reset in resets:
        reset()


def snapshot(*, owner: str = "process") -> CacheSnapshot:
    from corpus_structure._query_custody import _EXECUTED
    from corpus_structure.semantic.file_custody import custody_counts

    with _lock:
        observers = sorted(_observers.items())
        config, generation = configured(), _generation
    files, companions = custody_counts()
    return CacheSnapshot(
        pid=os.getpid(),
        owner=owner,
        started_at=_started,
        observed_at=datetime.now(UTC),
        generation=generation,
        settings=config,
        caches=(
            CacheObservation(name="file-custody", budget="file-custody", entries=files),
            CacheObservation(name="code-custody", budget="file-custody", entries=len(_EXECUTED)),
            CacheObservation(
                name="companion-verification", budget="file-custody", entries=companions
            ),
            *(
                CacheObservation(name=name, **observe().model_dump())
                for name, (observe, _) in observers
            ),
        ),
    )


class _Declared[**P, T]:
    def __init__(
        self,
        name: str,
        budget: Budget,
        loader: Callable[P, T],
        key: Callable[P, Hashable] | None,
        weight: Callable[[T], int] | None,
    ) -> None:
        self.name = name
        self.budget = budget
        self.loader = loader
        self.key = key
        self.weight = weight
        update_wrapper(self, loader, updated=())
        register(name, self.observe)

    def _memoized(self) -> _Memoized[P]:
        with _lock:
            storage = _storages.get(self.budget)
            if storage is None:
                storage = _Storage(
                    LRUCache(
                        getattr(configured(), self.budget), getsizeof=lambda entry: entry.weight
                    ),
                    RLock(),
                )
                _storages[self.budget] = storage
            wrapper = storage.wrappers.get(self.name)
            if wrapper is not None:
                return cast(_Memoized[P], wrapper)

            def key(*args: P.args, **kwargs: P.kwargs) -> tuple[str, Hashable]:
                identity = (
                    hashkey(*args, **kwargs) if self.key is None else self.key(*args, **kwargs)
                )
                return self.name, identity

            @cached(storage.cache, key=key, condition=Condition(storage.lock), info=True)
            def load(*args: P.args, **kwargs: P.kwargs) -> _Value:
                value = self.loader(*args, **kwargs)
                weight = 1 if self.weight is None else self.weight(value)
                if weight < 1:
                    raise ValueError(f"{self.name} requires a positive retained weight")
                return _Value(value, weight)

            storage.wrappers[self.name] = load
            return load

    def __call__(self, /, *args: P.args, **kwargs: P.kwargs) -> T:
        return cast(T, self._memoized()(*args, **kwargs).value)

    def cache_clear(self) -> None:
        clear(self.budget)

    def cache_info(self) -> _Counters:
        return self._memoized().cache_info()

    def observe(self) -> CacheMetrics:
        with _lock:
            storage = _storages.get(self.budget)
            wrapper = None if storage is None else storage.wrappers.get(self.name)
            if storage is None or wrapper is None:
                return CacheMetrics(
                    budget=self.budget,
                    entries=0,
                    size=0,
                    maxsize=getattr(configured(), self.budget),
                    hits=0,
                    misses=0,
                )
            with storage.lock:
                keys = tuple(key for key in storage.cache if key[0] == self.name)
                # Inspect without promoting entries in the retention order.
                size = sum(Cache.__getitem__(storage.cache, key).weight for key in keys)
                info = cast(_Memoized[P], wrapper).cache_info()
                return CacheMetrics(
                    budget=self.budget,
                    entries=len(keys),
                    size=size,
                    maxsize=int(storage.cache.maxsize),
                    hits=info.hits,
                    misses=info.misses,
                )


def declare[**P, T](
    name: str,
    budget: Budget,
    *,
    key: Callable[P, Hashable] | None = None,
    weight: Callable[[T], int] | None = None,
) -> Callable[[Callable[P, T]], _Declared[P, T]]:
    """Give a synchronous derivation one namespace in its process budget."""

    def decorate(loader: Callable[P, T]) -> _Declared[P, T]:
        return _Declared(name, budget, loader, key, weight)

    return decorate
