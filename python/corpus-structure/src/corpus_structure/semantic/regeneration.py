"""Explicit pack acquisition and reproducible semantic regeneration boundaries.

Acquisition reads named local inputs. Pure preparation and database publication remain separate;
reference/evaluation files are never acquired as extraction inputs.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from .analytical_profile import analytical_inputs
from .composed import composed_dependencies
from .domain_operations import domain_rule_inputs
from .observations import prepare_source_inputs
from .prepare import prepare_release
from .proposals import proposal_inputs
from .types import (
    PreparationProfile, PreparedRelease, ResolvedDependencies, SourceArtifact, SourceBundle,
)


def prepare_pack(pack: Path) -> tuple[SourceBundle, ResolvedDependencies, PreparationProfile, PreparedRelease]:
    """Acquire one explicit semantic pack without legacy compilation or reference discovery."""
    pack = pack.resolve()
    source = pack / "semantic.yaml"
    if not source.is_file():
        raise ValueError(f"semantic declaration missing: {source}")
    document = yaml.safe_load(source.read_bytes())
    name = document["name"]
    core = Path(__file__).resolve().parents[1] / "model/semantic/core.yaml"
    bundle = SourceBundle(name, (
        SourceArtifact(name, source.read_bytes()),
        SourceArtifact("semantic_core", core.read_bytes()),
    ))
    methods = yaml.safe_load((pack / "methods.yaml").read_bytes())
    core_rules = pack.parent / "core/schema/rules.yaml"
    rules = pack / "schema/rules.yaml"
    deps = domain_rule_inputs(
        ResolvedDependencies(), rules.read_bytes() if rules.exists() else b"rules: []",
        core_rules.read_bytes() if core_rules.exists() else b"rules: []",
        aliases=methods.get("aliases", {}),
    )
    artifacts = tuple(SourceArtifact("operation/" + filename, (pack / filename).read_bytes())
                      for filename in ("methods.yaml", "guideline.md", "queries.py", "policies.yaml", "slices.yaml")
                      if (pack / filename).is_file())
    deps = ResolvedDependencies((*deps.artifacts, *artifacts), deps.vocabularies, deps.ontology_sources)
    qualifiers = [key for key, definition in document.get("classes", {}).items()
                  if definition.get("is_a") == "Qualification"]
    if len(qualifiers) > 1:
        raise ValueError("pack requires one explicit Qualification subclass")
    bundle = proposal_inputs(bundle, deps, qualification_class=qualifiers[0] if qualifiers else "Qualification")
    bundle, deps = prepare_source_inputs(bundle, deps)
    bundle, deps = analytical_inputs(bundle, deps)
    deps = composed_dependencies(deps)
    profile = PreparationProfile(version="semantic-2")
    return bundle, deps, profile, prepare_release(bundle, deps, profile)
