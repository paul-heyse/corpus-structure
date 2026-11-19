"""Installed query-helper source custody at Python's existing import boundary.

The finite allowlist is owner-declared. This neither discovers dependencies nor loads
archived Python. Unrelated imports keep their ordinary loaders and cache behavior.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from contextvars import ContextVar
from hashlib import sha256
from importlib.machinery import PathFinder, SourceFileLoader
from pathlib import Path
from types import CodeType, ModuleType

_BASE = Path(__file__).resolve().parent
_NAMES: dict[str, str] = {}
_EXECUTED: dict[ModuleType, tuple[str, str]] = {}
_EXPECTED: ContextVar[dict[str, str] | None] = ContextVar("query_source_custody", default=None)
_CLOSED: ContextVar[bool] = ContextVar("closed_query_source_custody", default=False)


class SourceCustodyError(RuntimeError):
    """Installed source does not identify the helper objects in this process."""


class _CapturedLoader(SourceFileLoader):
    def exec_module(self, module: ModuleType) -> None:
        if (
            module in _EXECUTED
            or any(vars(previous).get("__name__") == self.name for previous in _EXECUTED)
            or any(not key.startswith("__") for key in module.__dict__)
        ):
            raise SourceCustodyError("query-helper reload is unsupported; restart the process")
        source = self.get_data(self.path)
        digest = sha256(source).hexdigest()
        path = str(Path(self.path).resolve())
        expected = _EXPECTED.get()
        required = expected.get(path) if expected is not None else None
        if required is None and _CLOSED.get() and Path(path).is_relative_to(_BASE):
            raise SourceCustodyError("query helper is outside the authenticated workload")
        if required is not None and required != digest:
            raise SourceCustodyError(
                "query-helper bytes changed before import; restart the process"
            )
        # Compile the actual captured installed bytes, without stale timestamp pyc.
        exec(compile(source, self.path, "exec", dont_inherit=True), module.__dict__)
        # Compile only the captured bytes. Shared custody then confirms those
        # bytes against a stable file observation before the import can finish.
        # file_custody itself reaches this point after defining its primitives.
        from corpus_structure.semantic.file_custody import observed_file

        try:
            record = observed_file(Path(path))
            if record.digest != digest:
                raise SourceCustodyError(
                    "query-helper bytes changed during import; restart the process"
                )
        except (ValueError, OSError) as error:
            raise SourceCustodyError(
                "query-helper source custody changed; restart the process"
            ) from error
        _EXECUTED[module] = (path, digest)


class _CustodyFinder:
    def find_spec(self, fullname, path=None, target=None):
        # Previously captured promises retain import custody even outside the
        # request context that first admitted their lazy module.
        if any(vars(module).get("__name__") == fullname for module in _EXECUTED):
            raise SourceCustodyError("query-helper reload is unsupported; restart the process")
        expected = _EXPECTED.get() or {}
        if not fullname.startswith("corpus_structure.") and fullname not in _NAMES and not expected:
            return None
        spec = PathFinder.find_spec(fullname, path, target)
        if spec is None or not isinstance(spec.loader, SourceFileLoader) or spec.origin is None:
            if _CLOSED.get() and fullname.startswith("corpus_structure."):
                raise SourceCustodyError("query helper has no admitted source loader")
            return None
        origin = str(Path(spec.origin).resolve())
        if (
            Path(origin).is_relative_to(_BASE)
            or origin == _NAMES.get(fullname)
            or origin in expected
        ):
            spec.loader = _CapturedLoader(fullname, spec.origin)
            return spec
        if _CLOSED.get() and fullname.startswith("corpus_structure."):
            raise SourceCustodyError("query helper origin is outside the authenticated workload")
        return None


def install(bootstrap_source: bytes, package_code: CodeType) -> None:
    """Called once by package entry, before owned answer helpers can import."""
    _EXECUTED[sys.modules[__name__]] = (
        str(Path(__file__).resolve()),
        sha256(bootstrap_source).hexdigest(),
    )
    if not any(isinstance(finder, _CustodyFinder) for finder in sys.meta_path):
        sys.meta_path.insert(0, _CustodyFinder())
    # Verify the module body executing the handoff, including eager setup.
    package = sys.modules["corpus_structure"]
    package_path = _BASE / "__init__.py"
    package_source = package_path.read_bytes()
    compiled = compile(package_source, str(package_path), "exec", dont_inherit=True)
    origin = getattr(package.__spec__, "origin", None)
    if origin is None or Path(origin).resolve() != package_path or package_code != compiled:
        raise SourceCustodyError("package bootstrap differs; restart the process")
    _EXECUTED[package] = (str(package_path), sha256(package_source).hexdigest())
    from corpus_structure.semantic.file_custody import verified_file

    verified_file(package_path, sha256(package_source).hexdigest())
    verified_file(Path(__file__).resolve(), sha256(bootstrap_source).hexdigest())


def _check_loaded(expected: dict[str, str]) -> None:
    # Imported object custody survives sys.modules eviction. Replacing or dropping
    # a module cannot authenticate the stale objects retained by query consumers.
    for module, (path, digest) in tuple(_EXECUTED.items()):
        name = vars(module).get("__name__")
        if path in expected and (
            digest != expected[path]
            or not isinstance(name, str)
            or sys.modules.get(name) is not module
            or str(Path(vars(module).get("__file__", "")).resolve()) != path
        ):
            raise SourceCustodyError("query-helper module changed; restart the process")
    known_paths = set(_NAMES.values())
    names = _NAMES.copy()
    for path in expected:
        absolute = Path(path)
        if absolute.is_relative_to(_BASE) and absolute.suffix == ".py":
            parts = absolute.relative_to(_BASE).with_suffix("").parts
            segments = parts[:-1] if parts[-1] == "__init__" else parts
            names[".".join(("corpus_structure", *segments))] = path
            known_paths.add(path)
    for name, path in names.items():
        if path not in expected:
            continue
        module = sys.modules.get(name)
        if module is not None and _EXECUTED.get(module) != (path, expected[path]):
            raise SourceCustodyError(
                "query helper was loaded without matching source custody; restart the process"
            )
    # Explicit owner-promised paths can also be outside the finite installed set.
    # Only that unusual route needs to locate previously loaded unknown modules.
    unknown = set(expected) - known_paths
    if unknown:
        for module in tuple(sys.modules.values()):
            if not isinstance(module, ModuleType):
                continue
            origin = vars(module).get("__file__")
            if origin is None:
                continue
            path = str(Path(origin).resolve())
            if path in unknown and _EXECUTED.get(module) != (path, expected[path]):
                raise SourceCustodyError(
                    "query helper was loaded without matching source custody; restart the process"
                )


def _check_files(expected: dict[str, str]) -> None:
    from corpus_structure.semantic.file_custody import verified_file

    try:
        for path, digest in expected.items():
            verified_file(Path(path), digest)
    except (ValueError, OSError) as error:
        raise SourceCustodyError(
            "query-helper source custody changed; restart the process"
        ) from error


def capture_sources(paths) -> dict[str, str]:
    """Capture imported digests and promised lazy sources without importing them."""
    from corpus_structure.semantic.file_custody import observed_file

    imported = {path: digest for path, digest in _EXECUTED.values()}
    try:
        captured = {
            str(Path(path).resolve()): imported.get(str(Path(path).resolve()))
            or observed_file(Path(path).resolve()).digest
            for path in paths
        }
    except (ValueError, OSError) as error:
        raise SourceCustodyError(
            "query-helper source custody changed; restart the process"
        ) from error
    _check_loaded(captured)
    _check_files(captured)
    return captured


def bootstrap_sources(root: Path) -> dict[str, str]:
    """Return the authenticated fixed package-to-loader handoff for this checkout."""
    if root != _BASE:
        return {}
    expected = {}
    for name in ("corpus_structure", __name__):
        module = sys.modules.get(name)
        if module not in _EXECUTED:
            return {}
        path, digest = _EXECUTED[module]
        expected[path] = digest
    _check_loaded(expected)
    _check_files(expected)
    return expected


def capture_workload_sources(root: Path, identity) -> dict[str, str]:
    """Bind the exact parsed source bytes to the actual loaded or promised modules."""
    selected = (identity.determining_modules if identity.complete else ()) or identity.modules
    expected = {
        str((root / item.filename).resolve()): sha256(item.content).hexdigest() for item in selected
    }
    if capture_sources(expected) != expected:
        raise SourceCustodyError("analyzed source differs from running code; restart the process")
    return expected


@contextmanager
def query_sources(expected: dict[str, str], *, closed: bool = False):
    """Check already-loaded helpers and constrain later imports to captured bytes."""
    _check_loaded(expected)
    _check_files(expected)
    if _CLOSED.get():
        outer = _EXPECTED.get() or {}
        if any(outer.get(path) != digest for path, digest in expected.items()):
            raise SourceCustodyError("nested custody extends the authenticated workload")
        expected = outer
    token = _EXPECTED.set(expected)
    closed_token = _CLOSED.set(closed or _CLOSED.get())
    try:
        yield
        _check_loaded(expected)
        _check_files(expected)
    finally:
        _CLOSED.reset(closed_token)
        _EXPECTED.reset(token)
