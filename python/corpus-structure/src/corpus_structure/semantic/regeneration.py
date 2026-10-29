"""Explicit pack acquisition and reproducible semantic regeneration boundaries.

Acquisition reads named local inputs. Pure preparation and database publication remain separate;
reference/evaluation files are never acquired as extraction inputs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

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
    return prepare_packs((pack,))


def prepare_packs(packs: tuple[Path, ...]) -> tuple[SourceBundle, ResolvedDependencies, PreparationProfile, PreparedRelease]:
    """Compose explicitly selected packs; reference files never enter acquired dependencies."""
    if not packs:
        raise ValueError("at least one semantic pack is required")
    packs = tuple(sorted({pack.resolve() for pack in packs}))
    if len(packs) > 1:
        acquired = [prepare_pack(pack) for pack in packs]
        sources: dict[str, SourceArtifact] = {}
        composed_artifacts: dict[str, SourceArtifact] = {}
        qualifiers = []
        statement_classes = []
        for pack, (bundle, deps, _, _) in zip(packs, acquired, strict=True):
            for source in bundle.sources:
                if source.name in {"agent", "agent-root", "observations", "observation-root", "analytics", "analytical-root"}:
                    continue
                previous = sources.setdefault(source.name, source)
                if previous != source:
                    raise ValueError(f"packs disagree on semantic module {source.name}")
            declaration = yaml.safe_load((pack / "semantic.yaml").read_bytes())
            qualifiers.extend(name for name, definition in declaration.get("classes", {}).items()
                              if definition.get("is_a") == "Qualification")
            statement_classes.extend(name for name, definition in declaration.get("classes", {}).items()
                                     if definition.get("is_a") == "SourceStatement")
            # Operation configuration is pack-scoped in a composed schema, not a merged executable graph.
            for artifact in deps.artifacts:
                if artifact.name.startswith(("execution/", "operation/analytical")):
                    continue
                artifact = SourceArtifact(f"pack/{pack.name}/{artifact.name}", artifact.content)
                composed_artifacts[artifact.name] = artifact
        root: dict[str, Any] = {
            "id": "https://corpus-structure.dev/semantic/composed-pack", "name": "composed_pack",
            "prefixes": {"cs": "https://corpus-structure.dev/semantic/"}, "default_prefix": "cs",
            "imports": list(sources),
        }
        qualification = "Qualification"
        if qualifiers:
            qualification = "ComposedQualification"
            root["classes"] = {qualification: {"is_a": "Qualification", "mixins": qualifiers}}
        statement_class = "SourceStatement"
        if len(statement_classes) == 1:
            statement_class = statement_classes[0]
        elif statement_classes:
            raise ValueError("composed packs require one explicit source-statement operation binding")
        bundle = SourceBundle("composed_pack", (*sources.values(), SourceArtifact("composed_pack", yaml.safe_dump(root).encode())))
        deps = ResolvedDependencies(tuple(composed_artifacts.values()))
        bundle = proposal_inputs(bundle, deps, qualification_class=qualification, statement_class=statement_class)
        bundle, deps = prepare_source_inputs(bundle, deps)
        bundle, deps = analytical_inputs(bundle, deps)
        deps = composed_dependencies(deps)
        profile = PreparationProfile(version="semantic-2")
        return bundle, deps, profile, prepare_release(bundle, deps, profile)
    pack = packs[0]
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
    from corpus_structure.ingest.profile import SOURCES_DIR
    from corpus_structure.orchestrate.phase0 import registry as method_registry

    registry = method_registry(pack)
    profiles = {profile for method, config in registry.named()
                for _, profile in registry.profiles(method, config)}
    artifacts += tuple(SourceArtifact(f"source-profile/{name}.yaml", (SOURCES_DIR / f"{name}.yaml").read_bytes())
                       for name in sorted(profiles))
    deps = ResolvedDependencies((*deps.artifacts, *artifacts), deps.vocabularies, deps.ontology_sources)
    qualifiers = [key for key, definition in document.get("classes", {}).items()
                  if definition.get("is_a") == "Qualification"]
    if len(qualifiers) > 1:
        raise ValueError("pack requires one explicit Qualification subclass")
    statement_classes = [key for key, definition in document.get("classes", {}).items()
                         if definition.get("is_a") == "SourceStatement"]
    if len(statement_classes) > 1:
        raise ValueError("pack requires one explicit SourceStatement subclass")
    bundle = proposal_inputs(bundle, deps, qualification_class=qualifiers[0] if qualifiers else "Qualification",
                            statement_class=statement_classes[0] if statement_classes else "SourceStatement")
    bundle, deps = prepare_source_inputs(bundle, deps)
    bundle, deps = analytical_inputs(bundle, deps)
    deps = composed_dependencies(deps)
    profile = PreparationProfile(version="semantic-2")
    return bundle, deps, profile, prepare_release(bundle, deps, profile)
