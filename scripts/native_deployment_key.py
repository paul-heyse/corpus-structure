"""Pure source and acquired-server inputs for the native test deployment key."""

from __future__ import annotations

import ast
import importlib.machinery
import importlib.util
import json
import sys
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path
from typing import TypedDict


class DeploymentKeyComponents(TypedDict):
    chain: list[tuple[str, str]]
    artifacts: list[tuple[str, int, int]]
    module_imports: list[tuple[str, str]]
    construction: list[tuple[str, str]]
    lockfile: str
    interpreter: str
    server: dict[str, object]


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


class _Imports(ast.NodeVisitor):
    def __init__(self, *, nested: bool) -> None:
        self.nested = nested
        self.nodes: list[ast.Import | ast.ImportFrom] = []

    def visit_Import(self, node: ast.Import) -> None:
        self.nodes.append(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.nodes.append(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if self.nested:
            self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if self.nested:
            self.generic_visit(node)


def _module_files(name: str, search: tuple[Path, ...], allowed: tuple[Path, ...]):
    """Resolve through import machinery without importing package initializers."""
    locations = [str(root) for root in search]
    found = []
    for index, _part in enumerate(name.split("."), 1):
        current = ".".join(name.split(".")[:index])
        spec = importlib.machinery.PathFinder.find_spec(current, locations)
        if spec is None:
            break
        if spec.origin and spec.origin not in {"built-in", "frozen"}:
            path = Path(spec.origin).resolve()
            if path.suffix == ".py" and any(path.is_relative_to(root) for root in allowed):
                found.append((current, path))
        if spec.submodule_search_locations is None:
            break
        locations = list(spec.submodule_search_locations)
    return found


def import_closure(
    sources: tuple[tuple[str, Path], ...],
    *,
    search: tuple[Path, ...],
    allowed: tuple[Path, ...],
    nested: bool,
) -> tuple[Path, ...]:
    """Read selected local source imports to a fixed point, including package initializers."""
    pending = [(module, path, nested) for module, path in sources]
    visited: dict[Path, bool] = {}
    while pending:
        module, path, implementation = pending.pop()
        implementation = implementation and path.name != "__init__.py"
        if path in visited and (visited[path] or not implementation):
            continue
        visited[path] = implementation
        # Importing a package executes its initializer, not every lazy API defined there.
        # Construction's directly imported implementation modules still include nested helpers.
        imports = _Imports(nested=implementation)
        imports.visit(ast.parse(path.read_bytes(), filename=str(path)))
        package = module if path.name == "__init__.py" else module.rpartition(".")[0]
        for node in imports.nodes:
            if isinstance(node, ast.Import):
                names = [item.name for item in node.names]
            else:
                if node.level and not package:
                    continue
                base = importlib.util.resolve_name("." * node.level + (node.module or ""), package)
                names = [base, *(base + "." + item.name for item in node.names if item.name != "*")]
            for name in names:
                resolved = _module_files(name, search, allowed)
                for index, (dependency, source) in enumerate(resolved):
                    # Initializer side effects stay module-level through their imports.
                    # A directly selected implementation may inspect its nested helpers.
                    pending.append(
                        (dependency, source, implementation and index == len(resolved) - 1)
                    )
    return tuple(sorted(visited))


def deployment_key(
    *,
    repository: Path,
    chain: Path,
    package: Path,
    construction: Path,
    lockfile: Path,
    server: Mapping[str, object],
) -> tuple[str, DeploymentKeyComponents]:
    """Hash the declared narrow inputs; frozen bulk artifacts contribute file metadata."""
    repository, chain, package, construction, lockfile = (
        path.resolve() for path in (repository, chain, package, construction, lockfile)
    )

    def relative(path: Path) -> str:
        return path.relative_to(repository).as_posix()

    chain_files = sorted(
        path for path in chain.rglob("*") if path.is_file() and "__pycache__" not in path.parts
    )
    source = [path for path in chain_files if path.suffix in {".py", ".mako"}]
    artifacts = [path for path in chain_files if path.suffix not in {".py", ".mako", ".pyc"}]
    closure = import_closure(
        tuple(("", path) for path in source if path.suffix == ".py"),
        search=(package.parent,),
        allowed=(package,),
        nested=False,
    )
    construction_closure = import_closure(
        ((construction.stem, construction),),
        search=(construction.parent, package.parent),
        allowed=(construction.parent, package),
        nested=True,
    )
    # The chain files already have their own component; their imported package files do not.
    components: DeploymentKeyComponents = {
        "chain": [(relative(path), _digest(path)) for path in source],
        "artifacts": [
            (relative(path), path.stat().st_size, path.stat().st_mtime_ns) for path in artifacts
        ],
        "module_imports": [
            (relative(path), _digest(path)) for path in closure if path.is_relative_to(package)
        ],
        "construction": [(relative(path), _digest(path)) for path in construction_closure],
        "lockfile": _digest(lockfile),
        "interpreter": sys.version,
        "server": dict(server),
    }
    encoded = json.dumps(components, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest(), components
