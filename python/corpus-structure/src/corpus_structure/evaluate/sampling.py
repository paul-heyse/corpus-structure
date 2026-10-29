"""Deterministic stratified reference sampling; pure and independent of physical stores."""
from __future__ import annotations
import hashlib
import math
from collections.abc import Collection,Sequence
from dataclasses import dataclass
from typing import Any

SAMPLER_VERSION = "1"


class GoldenSetError(ValueError):
    """A golden set that cannot be created, settled or listed as asked."""


# --- The sampler ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class PoolUnit:
    key: str
    kind: str
    math_share: float
    document_id: int = 0
    rendition_id: int = 0


def _order(key: str, seed: int) -> str:
    return hashlib.sha256((key + str(seed)).encode("utf-8")).hexdigest()


def cut_points(shares: Sequence[float]) -> tuple[float, float]:
    """The pool's 1/3 and 2/3 order statistics (the ceil(n p)-th smallest)."""
    s = sorted(shares)
    n = len(s)
    return s[math.ceil(n / 3) - 1], s[math.ceil(2 * n / 3) - 1]


def stratum(unit: PoolUnit, cuts: tuple[float, float]) -> str:
    tercile = 0 if unit.math_share <= cuts[0] else 1 if unit.math_share <= cuts[1] else 2
    return f"{unit.kind}/t{tercile}"


def allocate(
    pool: Mapping[str, int], forced: Mapping[str, int], size: int
) -> dict[str, dict[str, float]]:
    """Places per stratum (module doc): pool, exact share, quota and forced count each."""
    total = sum(pool.values())
    exact = {s: size * n / total for s, n in pool.items()}
    quota = {s: max(1, math.floor(x)) for s, x in exact.items()}
    by_remainder = sorted(pool, key=lambda s: (-(exact[s] - math.floor(exact[s])), s))
    for s in by_remainder:
        if sum(quota.values()) >= size:
            break
        if quota[s] < pool[s]:
            quota[s] += 1
    for s, f in forced.items():
        quota[s] = max(quota[s], f)
    while sum(quota.values()) > size:
        shrinkable = [s for s in pool if quota[s] > max(1, forced.get(s, 0))]
        if not shrinkable:
            raise GoldenSetError(
                f"{size} places cannot hold one unit per stratum and the forced units"
            )
        quota[max(shrinkable, key=lambda s: (quota[s] - exact[s], s))] -= 1
    return {
        s: {"pool": pool[s], "exact": exact[s], "quota": quota[s], "forced": forced.get(s, 0)}
        for s in sorted(pool)
    }


@dataclass(frozen=True)
class Sample:
    units: tuple[str, ...]  # sorted
    sampling: dict[str, Any]


def sample(pool: Sequence[PoolUnit], size: int, seed: int, forced: Collection[str] = ()) -> Sample:
    """The sample (module doc); input order is irrelevant."""
    by_key = {u.key: u for u in pool}
    forced = set(forced)
    if missing := sorted(forced - set(by_key)):
        raise GoldenSetError(f"forced units outside the pool: {missing}")
    if len(forced) > size:
        raise GoldenSetError(f"{len(forced)} forced units exceed the set size {size}")
    if size > len(by_key):
        raise GoldenSetError(f"the pool holds {len(by_key)} units, fewer than {size}")
    cuts = cut_points([u.math_share for u in by_key.values()])
    strata: dict[str, list[str]] = {}
    for key in sorted(by_key):
        strata.setdefault(stratum(by_key[key], cuts), []).append(key)
    forced_by = {s: sum(k in forced for k in keys) for s, keys in strata.items()}
    allocation = allocate({s: len(k) for s, k in strata.items()}, forced_by, size)
    chosen = set(forced)
    for s, keys in strata.items():
        free = sorted((k for k in keys if k not in forced), key=lambda k: (_order(k, seed), k))
        chosen |= set(free[: int(allocation[s]["quota"]) - forced_by[s]])
    return Sample(
        tuple(sorted(chosen)),
        {
            "sampler_version": SAMPLER_VERSION,
            "seed": seed,
            "size": size,
            "cut_points": list(cuts),
            "allocation": allocation,
            "forced": sorted(forced),
        },
    )


