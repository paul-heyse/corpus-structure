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

RICH_QUERY_SOURCES = (
    "_query_custody.py",
    "semantic/rich_queries.py",
    "semantic/rich_statistics_queries.py",
    "serve/rich_queries.py",
    "serve/rich_knowledge.py",
    "semantic/rich_graph_validation.py",
    "semantic/rich_knowledge_contracts.py",
    "semantic/rich_decisions.py",
    "semantic/rich_value_graph.py",
    "semantic/rich_identity_exclusions.py",
    "semantic/declared_structural_references.py",
    "semantic/structural_base.py",
    "semantic/qualification_meaning.py",
    "semantic/reference_positions.py",
    "semantic/statement_types.py",
    "semantic/alias_policy.py",
    "core/keys.py",
    "core/tex.py",
    "core/vocab.py",
    "semantic/data_operation_identity.py",
    "semantic/data_operation_json.py",
    "semantic/data_operation_model.py",
    "semantic/data_operation_ports.py",
    "semantic/data_operation_support.py",
    "semantic/data_operation_wire.py",
    "semantic/property_roles.py",
    "semantic/identity.py",
    "semantic/value_codec.py",
    "semantic/types.py",
    "semantic/unicode_identity.py",
    "semantic/graph_runtime.py",
)
COMPOSITE_READ_SOURCES = (
    *(name for name in RICH_QUERY_SOURCES if name != "semantic/rich_statistics_queries.py"),
    "serve/selected_contributions.py",
    "serve/contribution_facets.py",
    "serve/identity_exclusion_comparison.py",
    "semantic/nonrich_contribution_facets.py",
    "semantic/candidate_contribution_facets.py",
    "semantic/data_operation_kind_refinements.py",
    "semantic/graph_topology.py",
    "semantic/observations.py",
    "semantic/structural_products.py",
    "semantic/artifact_identity.py",
    "semantic/characterization.py",
    "semantic/contextual_links.py",
    "semantic/contribution_facets.py",
    "semantic/identity_exclusion_comparison.py",
    "semantic/rich_proposals.py",
    "semantic/demand_results.py",
    "semantic/data_operation_read_index.py",
    "semantic/authority_leaf.py",
    "semantic/declared_structural_admission.py",
    "semantic/operation_policy.py",
    "evaluate/selected_operation_events.py",
    "evaluate/declared_operation_events.py",
    "semantic/execution_evidence_leaf.py",
    "semantic/record_policy_authority.py",
    "semantic/record_policy.py",
)
GROUPED_INTERPRETATION_SOURCES = tuple(
    dict.fromkeys(
        (
            *COMPOSITE_READ_SOURCES,
            "serve/interpretations.py",
            "semantic/grouped_record_interpretations.py",
            "semantic/authored_interpretations.py",
            "semantic/interpretations.py",
            "semantic/terminology.py",
            "serve/interpretation_authoring.py",
            "methods/record_readings.py",
            "semantic/record_contracts.py",
            "semantic/declared_candidate_products.py",
            "semantic/reading_resolution_products.py",
            "semantic/finite_interpretation_products.py",
        )
    )
)
STRUCTURAL_READ_SOURCES = tuple(
    dict.fromkeys(
        (
            *COMPOSITE_READ_SOURCES,
            "serve/selected_structural.py",
            "serve/structural_products.py",
            "serve/structural_gaps.py",
            "serve/source_decision_journey.py",
            "serve/selected_structural_admission.py",
            "serve/selected_math.py",
            "semantic/source_products.py",
            "semantic/contextual_operations.py",
            "semantic/declared_structural_admission.py",
            "semantic/structural_admission.py",
        )
    )
)
_CURRENT_READ_SOURCES = tuple(
    dict.fromkeys(
        (
            *RICH_QUERY_SOURCES,
            *COMPOSITE_READ_SOURCES,
            *GROUPED_INTERPRETATION_SOURCES,
            *STRUCTURAL_READ_SOURCES,
        )
    )
)
_BASE = Path(__file__).resolve().parent
_NAMES = {
    "corpus_structure." + name[:-3].replace("/", "."): str(_BASE / name) for name in _CURRENT_READ_SOURCES
}
_KNOWN_PATHS = frozenset(_NAMES.values())
_EXECUTED: dict[ModuleType, tuple[str, str]] = {}
_EXPECTED: ContextVar[dict[str, str] | None] = ContextVar("query_source_custody", default=None)


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
        _EXECUTED[module] = (path, digest)


class _CustodyFinder:
    def find_spec(self, fullname, path=None, target=None):
        expected = _EXPECTED.get() or {}
        if fullname not in _NAMES and not expected:
            return None
        spec = PathFinder.find_spec(fullname, path, target)
        if spec is None or not isinstance(spec.loader, SourceFileLoader) or spec.origin is None:
            return None
        origin = str(Path(spec.origin).resolve())
        if origin in _KNOWN_PATHS or origin in expected:
            spec.loader = _CapturedLoader(fullname, spec.origin)
            return spec
        return None


def install(bootstrap_source: bytes) -> None:
    """Called once by package entry, before owned answer helpers can import."""
    _EXECUTED[sys.modules[__name__]] = (
        str(Path(__file__).resolve()),
        sha256(bootstrap_source).hexdigest(),
    )
    if not any(isinstance(finder, _CustodyFinder) for finder in sys.meta_path):
        sys.meta_path.insert(0, _CustodyFinder())


def _check_loaded(expected: dict[str, str]) -> None:
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
        if path not in expected:
            continue
        if record != (path, expected[path]):
            raise SourceCustodyError(
                "query helper was loaded without matching source custody; restart the process"
            )


@contextmanager
def query_sources(expected: dict[str, str]):
    """Check already-loaded helpers and constrain later imports to captured bytes."""
    _check_loaded(expected)
    token = _EXPECTED.set(expected)
    try:
        yield
        _check_loaded(expected)
    finally:
        _EXPECTED.reset(token)
