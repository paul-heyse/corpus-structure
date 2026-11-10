"""One owner of release-producing and runtime-acceptance determinants."""

import json
import sys
from importlib.metadata import version
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import ResolvedDependencies

_BASE_BYTE_LIBRARIES = (
    "linkml",
    "linkml-runtime",
    "pydantic",
    "rdflib",
    "pyshacl",
    "oaklib",
    "pronto",
    "fastobo",
    "linkml-term-validator",
    "valuesets",
    "pyoxigraph",
    "jsonschema",
    "cattrs",
)
SCIENTIFIC_LIBRARIES = ("sympy", "rule-engine", "numpy", "lark", "regex")
BYTE_LIBRARIES = (
    *_BASE_BYTE_LIBRARIES,
    "pydantic-core",
    *SCIENTIFIC_LIBRARIES,
    "python",
    "unicode-identity",
)
BOUNDARY_LIBRARIES = ("python", "pydantic", "pydantic-core", "jsonschema", "cattrs")
DEPLOYMENT_LIBRARIES = ("sqlalchemy", "psycopg", "pglast", "alembic")
ANALYSIS_LIBRARIES = ("sqlglot", "sqlalchemy", "linkml-runtime", "pyarrow", "pgvector", "pyyaml")


def analysis_runtime() -> tuple[tuple[str, str], ...]:
    return tuple((name, determinant_version(name)) for name in ANALYSIS_LIBRARIES)


def release_library_versions(
    dependencies: ResolvedDependencies, *, base: dict[str, str] | None = None
) -> dict[str, str]:
    """One bounded manifest rule for production, persistence and full verification."""
    if base is None:
        base = {name: determinant_version(name) for name in BYTE_LIBRARIES}
    if set(base) != set(BYTE_LIBRARIES):
        raise ValueError("release compiler library set differs from the supported determinants")
    return {**base, **dict(projection_analysis_runtime(dependencies))}


def projection_analysis_runtime(
    dependencies: ResolvedDependencies,
) -> tuple[tuple[str, str], ...]:
    """Qualify production, not archive reading, before either preparation cache."""
    sources = {source.name: source.content for source in dependencies.artifacts}
    prefix = "execution/implementation/"
    if prefix + "capture/companion-projection-model.yaml" not in sources:
        return ()
    advice = "reacquire execution inputs and prepare/admit a new release"
    try:
        recorded = json.loads(sources[prefix + "libraries.json"])
    except (KeyError, ValueError, TypeError) as error:
        raise ValueError(f"projection analysis runtime provenance missing; {advice}") from error
    current = analysis_runtime()
    if not isinstance(recorded, dict) or any(recorded.get(k) != v for k, v in current):
        raise ValueError(f"projection analysis runtime differs from captured inputs; {advice}")
    return current


def determinant_version(name: str) -> str:
    if name == "unicode-identity":
        from .unicode_identity import qualified_python_identity_recipe

        return qualified_python_identity_recipe().decode("utf-8")
    return sys.version if name == "python" else version(name)


def boundary_compatible(recorded: dict[str, str], compiler: str) -> bool:
    from .types import READABLE_COMPILER_VERSIONS

    return compiler in READABLE_COMPILER_VERSIONS and all(
        recorded.get(name) == determinant_version(name) for name in BOUNDARY_LIBRARIES
    )


def scientific_compatible(recorded: dict[str, str]) -> bool:
    return all(recorded.get(name) == determinant_version(name) for name in SCIENTIFIC_LIBRARIES)
