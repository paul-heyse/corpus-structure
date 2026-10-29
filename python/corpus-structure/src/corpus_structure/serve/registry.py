"""The query registry (D8 §5.2; consolidation and queries §3.9).

`build_registry(generic, pack)` registers `serve`'s generic queries and the pack's plug-in,
`<pack>/queries.py`, imported from the pack directory and exposing `QUERIES`. A plug-in query that
lacks a protocol member, or whose name clashes with another query, is refused with the reason
(`QueryRegistryError`). The registry is built from files alone: no database is touched, so shell
completion can list the queries.
"""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from corpus_structure.serve.protocol import DomainQuery

PLUGIN = "queries.py"


class QueryRegistryError(ValueError):
    """A plug-in or query the registry refuses; `problems` names each."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("; ".join(problems))


def _problems(query: Any, where: str) -> list[str]:
    out = []
    for member in ("name", "version"):
        value = getattr(query, member, None)
        if not isinstance(value, str) or not value:
            out.append(f"{where}: no {member}")
    for member in ("params", "result"):
        value = getattr(query, member, None)
        if not (inspect.isclass(value) and issubclass(value, BaseModel)):
            out.append(f"{where}: {member} is not a Pydantic model")
    for member in ("rows", "scope"):
        if not callable(getattr(query, member, None)):
            out.append(f"{where}: no {member}()")
    return out


def load_plugin(pack: Path) -> list[Any]:
    """The pack's `QUERIES`, or none when it has no `queries.py`."""
    path = pack / PLUGIN
    if not path.exists():
        return []
    identity = hashlib.sha256(str(path.resolve()).encode() + path.read_bytes()).hexdigest()[:20]
    module_name = f"corpus_pack_{pack.name}_queries_{identity}"
    if module_name in sys.modules:
        queries = getattr(sys.modules[module_name], "QUERIES", None)
        if not isinstance(queries, list | tuple):
            raise QueryRegistryError([f"{path}: no QUERIES sequence"])
        return list(queries)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise QueryRegistryError([f"{path}: cannot be imported"])
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    queries = getattr(module, "QUERIES", None)
    if not isinstance(queries, list | tuple):
        raise QueryRegistryError([f"{path}: no QUERIES sequence"])
    return list(queries)


def build_registry(
    generic: Iterable[DomainQuery] = (), pack: Path | None = None
) -> Mapping[str, DomainQuery]:
    """Every query by name (module doc)."""
    out: dict[str, DomainQuery] = {}
    problems: list[str] = []
    sources = [("serve", q) for q in generic]
    if pack is not None:
        sources += [(str(pack / PLUGIN), q) for q in load_plugin(pack)]
    for where, query in sources:
        found = _problems(query, where)
        if found:
            problems += found
            continue
        if query.name in out:
            problems.append(f"{where}: query {query.name!r} clashes with another query")
            continue
        out[query.name] = query
    if problems:
        raise QueryRegistryError(problems)
    return out
