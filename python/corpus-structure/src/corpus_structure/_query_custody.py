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
from types import ModuleType

QUERY_SOURCES = (
    "_query_custody.py",
    "serve/queries.py",
    "serve/registry.py",
    "serve/read.py",
    "serve/results.py",
    "serve/protocol.py",
    "serve/journey.py",
    "serve/source_search.py",
    "serve/structural_products.py",
    "serve/contextual_navigation.py",
    "serve/source_decision_journey.py",
    "serve/structural_gaps.py",
    "serve/explain.py",
    "serve/native_source.py",
    "semantic/query.py",
    "semantic/consolidation.py",
    "semantic/coverage_contract.py",
    "semantic/continuations.py",
    "semantic/query_compatibility.py",
    "semantic/value_codec.py",
    "semantic/types.py",
    "semantic/scientific_evidence.py",
    "semantic/scientific_evidence_schema.py",
    "semantic/outcomes.py",
    "semantic/analysis_contracts.py",
    "semantic/identity.py",
    "semantic/unicode_identity.py",
    "methods/llm/producer.py",
    "semantic/metadata.py",
    "semantic/source_views.py",
    "semantic/structural_products.py",
    "semantic/structural_admission.py",
    "semantic/product_reference.py",
    "semantic/published_document.py",
    "semantic/pdf_record_reader.py",
    "semantic/pdf_storage.py",
    "semantic/native_requests.py",
    "semantic/_operation_calls.py",
    "semantic/_operation_ids.py",
    "semantic/operation_results.py",
    "semantic/operation_value_types.py",
    "semantic/pdf_contracts.py",
    "semantic/pdf_payloads.py",
    "schema/relational.py",
    "core/canonical.py",
)
_BASE = Path(__file__).resolve().parent
_NAMES = {
    "corpus_structure." + name[:-3].replace("/", "."): str(_BASE / name) for name in QUERY_SOURCES
}
_KNOWN_PATHS = frozenset(_NAMES.values())
_EXECUTED: dict[ModuleType, tuple[str, str, bool]] = {}
_EXPECTED: ContextVar[dict[str, str] | None] = ContextVar("query_source_custody", default=None)
_PACK: ContextVar[str | None] = ContextVar("query_source_pack", default=None)


class SourceCustodyError(RuntimeError):
    """Installed source does not identify the helper objects in this process."""


class _CapturedLoader(SourceFileLoader):
    def exec_module(self, module: ModuleType) -> None:
        if module in _EXECUTED or any(not key.startswith("__") for key in module.__dict__):
            raise SourceCustodyError("query-helper reload is unsupported; restart the process")
        source = self.get_data(self.path)
        digest = sha256(source).hexdigest()
        path = str(Path(self.path).resolve())
        expected = _EXPECTED.get()
        required = expected.get(path) if expected is not None else None
        if required is not None and required != digest:
            raise SourceCustodyError("query-helper bytes changed before import")
        # Compile the actual captured installed bytes, without stale timestamp pyc.
        exec(compile(source, self.path, "exec", dont_inherit=True), module.__dict__)
        _EXECUTED[module] = (path, digest, False)


class _CustodyFinder:
    def find_spec(self, fullname, path=None, target=None):
        expected = _EXPECTED.get() or {}
        if fullname not in _NAMES and not expected:
            return None
        spec = PathFinder.find_spec(fullname, path, target)
        if spec is None or not isinstance(spec.loader, SourceFileLoader) or spec.origin is None:
            return None
        origin = str(Path(spec.origin).resolve())
        pack = _PACK.get()
        if pack is not None and Path(origin).is_relative_to(pack) and origin not in expected:
            raise SourceCustodyError("query helper is outside its declared source bundle")
        if origin in _KNOWN_PATHS or origin in expected:
            spec.loader = _CapturedLoader(fullname, spec.origin)
            return spec
        return None


def install(bootstrap_source: bytes) -> None:
    """Called once by package entry, before owned answer helpers can import."""
    _EXECUTED[sys.modules[__name__]] = (
        str(Path(__file__).resolve()),
        sha256(bootstrap_source).hexdigest(),
        False,
    )
    if not any(isinstance(finder, _CustodyFinder) for finder in sys.meta_path):
        sys.meta_path.insert(0, _CustodyFinder())


def record_plugin(module: ModuleType, path: Path, source: bytes) -> None:
    _EXECUTED[module] = (str(path.resolve()), sha256(source).hexdigest(), True)


def verify_plugin(module: ModuleType, path: Path, source: bytes) -> None:
    if _EXECUTED.get(module) != (str(path.resolve()), sha256(source).hexdigest(), True):
        raise SourceCustodyError("query plugin cache has no matching source custody")


def _check_loaded(expected: dict[str, str], pack: str) -> None:
    # Retain custody for helper objects still referenced by cached query code even
    # if somebody removed their module from sys.modules before importing it again.
    for module in [*sys.modules.values(), *_EXECUTED]:
        if not isinstance(module, ModuleType):
            continue
        attributes = vars(module)
        name = attributes.get("__name__")
        known = _NAMES.get(name) if isinstance(name, str) else None
        origin = known or attributes.get("__file__")
        if origin is None:
            continue
        path = str(Path(origin).resolve())
        record = _EXECUTED.get(module)
        if record is not None and record[2]:
            continue  # The selected plugin cache entry is verified by its loader.
        if Path(path).is_relative_to(pack) and path not in expected:
            raise SourceCustodyError("unlisted warm query helper; restart with its declared bundle")
        if path not in expected:
            continue
        if record != (path, expected[path], False):
            raise SourceCustodyError(
                "query helper was loaded without matching source custody; restart the process"
            )


@contextmanager
def query_sources(expected: dict[str, str], *, pack: Path):
    """Check already-loaded helpers and constrain later imports to captured bytes."""
    root = str(pack.resolve())
    _check_loaded(expected, root)
    token = _EXPECTED.set(expected)
    pack_token = _PACK.set(root)
    try:
        yield
        _check_loaded(expected, root)
    finally:
        _EXPECTED.reset(token)
        _PACK.reset(pack_token)
