"""Explicit acquisition and release-bound metric declarations; no inferred metric names."""

import json
import math
from pathlib import Path

from .types import PreparedRelease, ResolvedDependencies, SourceArtifact

METRIC_INPUT = "operation/metric-definitions.yaml"


def observation_dependencies(
    dependencies: ResolvedDependencies, content: bytes | None = None
) -> ResolvedDependencies:
    """Acquire packaged declarations at an explicit entry boundary, or accept exact caller bytes."""
    if any(a.name == METRIC_INPUT for a in dependencies.artifacts):
        raise ValueError("metric declarations are already supplied")
    if content is None:
        content = (Path(__file__).resolve().parents[1] / "model/semantic/metrics.yaml").read_bytes()
    return ResolvedDependencies(
        (*dependencies.artifacts, SourceArtifact(METRIC_INPUT, content)),
        dependencies.vocabularies,
        dependencies.ontology_sources,
    )


def metric_definitions(prepared: PreparedRelease) -> dict[str, dict]:
    return {
        r.name: json.loads(r.body) for r in prepared.registry_rows if r.kind == "metric_definition"
    }


def validate_measurement(prepared: PreparedRelease, measurement) -> None:
    definition = metric_definitions(prepared).get(measurement.metric)
    if definition is None:
        raise ValueError(f"unresolved metric definition: {measurement.metric}")
    if str(measurement.scope_type) != definition["subject_kind"]:
        raise ValueError("measurement subject differs from metric definition")
    if measurement.value is not None and type(measurement.value) not in (int, float):
        raise ValueError("measurement value differs from declared numeric source profile")
    if measurement.value is not None:
        try:
            finite = math.isfinite(float(measurement.value))
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError("measurement requires a finite float-compatible source number")
