"""The relational pool (pool and interchange §3.1, §3.2; ADR-0021; coordinator decision 22).

- `contract`: the pool's model-typed Arrow relations, their metadata and determinism rules, and
  `build`, the pure function from what the loader reads to a `Pool`;
- Historical ADBC pool loading lives only in database-test support; current production uses
  the release-bound semantic snapshot and analytics owners.
- `hydrate`: T3, the pool's candidates as keyed candidate sets, one per proposal observation;
- `steps`: the set-step interface, its schemas and the Python reference implementation;
- `duckdb_engine`: the in-process DuckDB 2.0 implementation of the same steps;
- `harness`: the set-equality check of the two, and the engine a pass selects.
"""

from corpus_structure.pool.contract import Pool, PoolMeta, RunRow, build
from corpus_structure.pool.duckdb_engine import DuckDBEngine
from corpus_structure.pool.harness import EngineDisagreement, agree, engine
from corpus_structure.pool.hydrate import Hydrated, hydrate
from corpus_structure.pool.steps import Engine, PythonEngine, ViewSpec

__all__ = [
    "DuckDBEngine",
    "Engine",
    "EngineDisagreement",
    "Hydrated",
    "Pool",
    "PoolMeta",
    "PythonEngine",
    "RunRow",
    "ViewSpec",
    "agree",
    "build",
    "engine",
    "hydrate",
]
