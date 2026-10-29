"""Explicit immutable execution inputs for the composed semantic profile.

Acquisition is an entry-point operation. Pure preparation resolves only supplied bytes;
trusted execution classes never enter the domain extraction/query class namespace.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .contracts import ExecutionModelInputs, ExecutionModelProducts

from .identity import canonical_bytes
from .types import ResolvedDependencies, SourceArtifact, SourceBundle

_PREFIX = "execution/"
_MANIFEST = _PREFIX + "manifest.json"


def composed_dependencies(
    dependencies: ResolvedDependencies, execution: ExecutionModelInputs | None = None
) -> ResolvedDependencies:
    """Acquire the trusted model explicitly, or package an explicitly supplied candidate."""
    from .contracts import trusted_execution_inputs

    inputs = trusted_execution_inputs() if execution is None else execution
    if any(item.name.startswith(_PREFIX) for item in dependencies.artifacts):
        raise ValueError("execution inputs are already supplied or use a reserved name")
    schema_names = [item.name for item in inputs.schema.sources]
    if len(schema_names) != len(set(schema_names)):
        raise ValueError("duplicate execution schema input")
    artifacts = (
        SourceArtifact(
            _MANIFEST,
            canonical_bytes(
                {
                    "root": inputs.schema.root,
                    "schemas": schema_names,
                    "catalog": inputs.catalog.name,
                }
            ),
        ),
        SourceArtifact(_PREFIX + "catalog.yaml", inputs.catalog.content),
        *(
            SourceArtifact(_PREFIX + "schema/" + item.name, item.content)
            for item in inputs.schema.sources
        ),
    )
    return ResolvedDependencies(
        (*dependencies.artifacts, *artifacts),
        dependencies.vocabularies,
        dependencies.ontology_sources,
    )


def execution_model_from_dependencies(dependencies: ResolvedDependencies) -> ExecutionModelProducts:
    """Resolve and compile supplied contract bytes, with no installed-model fallback."""
    from .contracts import ExecutionModelInputs, compile_execution_model

    sources = {item.name: item for item in dependencies.artifacts if item.name.startswith(_PREFIX)}
    if len(sources) != sum(item.name.startswith(_PREFIX) for item in dependencies.artifacts):
        raise ValueError("duplicate execution input")
    if _MANIFEST not in sources:
        raise ValueError("semantic-2 requires explicit execution inputs")
    manifest = json.loads(sources[_MANIFEST].content)
    if (
        set(manifest) != {"root", "schemas", "catalog"}
        or not isinstance(manifest["root"], str)
        or not isinstance(manifest["schemas"], list)
        or not isinstance(manifest["catalog"], str)
        or not manifest["catalog"]
    ):
        raise ValueError("invalid execution input manifest")
    names = manifest["schemas"]
    if any(not isinstance(name, str) or not name for name in names) or len(names) != len(
        set(names)
    ):
        raise ValueError("invalid execution schema names")
    expected = {
        _MANIFEST,
        _PREFIX + "catalog.yaml",
        *(_PREFIX + "schema/" + name for name in names),
    }
    if set(sources) != expected:
        raise ValueError("execution input set differs from manifest")
    bundle = SourceBundle(
        manifest["root"],
        tuple(SourceArtifact(name, sources[_PREFIX + "schema/" + name].content) for name in names),
    )
    inputs = ExecutionModelInputs(
        bundle, SourceArtifact(manifest["catalog"], sources[_PREFIX + "catalog.yaml"].content)
    )
    return compile_execution_model(inputs)
