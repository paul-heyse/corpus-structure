"""The set-equality harness of the two engines (pool and interchange §3.2, §6; ADR-0021; R09).

`agree(step, *inputs)` runs one set step on the Python reference and on the DuckDB engine and
returns the result when the two are equal, else raises `EngineDisagreement` naming the rows each
has alone. Both results are under the step's declared schema, in its `ORDER` key order, so equality
is row for row; set-equality, equal keys and equal ordered output are one check. A result with two
rows on one `ORDER` key is not a set and is refused too.

`engine(name)` makes the engine a pass selects (`consolidate.claims`'s `engine: duckdb | python`).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

import pyarrow as pa

from corpus_structure.pool.duckdb_engine import DuckDBEngine
from corpus_structure.pool.steps import ORDER, Engine, PythonEngine

type EngineName = Literal["duckdb", "python"]
STEPS = ("alias_links", "fuse", "disagreements", "views")


class EngineDisagreement(AssertionError):
    """The two engines' results differ on the same inputs, or one is not a set."""


def engine(name: EngineName) -> Engine:
    return DuckDBEngine() if name == "duckdb" else PythonEngine()


def _hashable(value: Any) -> Any:
    return tuple(_hashable(v) for v in value) if isinstance(value, list) else value


def _rows(table: pa.Table) -> list[tuple[Any, ...]]:
    return [tuple(_hashable(v) for v in r.values()) for r in table.to_pylist()]


def _check_set(table: pa.Table, engine_name: str) -> None:
    order = ORDER[table.schema.metadata[b"cs.relation"].decode()]
    keys = [tuple(r[k] for k in order) for r in table.select(list(order)).to_pylist()]
    if len(set(keys)) != len(keys):
        raise EngineDisagreement(f"{engine_name}: two rows on one {order} key")


def agree(step: str, *inputs: Any, engines: Sequence[Engine] | None = None) -> pa.Table:
    """The step's result when every engine gives the same one (module doc)."""
    if step not in STEPS:
        raise ValueError(f"no set step {step!r}")
    if engines is None:
        with DuckDBEngine() as duck:
            return agree(step, *inputs, engines=(PythonEngine(), duck))
    results = [(e.name, getattr(e, step)(*inputs)) for e in engines]
    first_name, first = results[0]
    _check_set(first, first_name)
    for name, result in results[1:]:
        _check_set(result, name)
        if not result.equals(first, check_metadata=True):
            mine, theirs = set(_rows(first)), set(_rows(result))
            raise EngineDisagreement(
                f"{step}: {first_name} alone {sorted(mine - theirs, key=repr)}; "
                f"{name} alone {sorted(theirs - mine, key=repr)}"
                + ("" if mine != theirs else "; same rows, different order or schema")
            )
    return first
