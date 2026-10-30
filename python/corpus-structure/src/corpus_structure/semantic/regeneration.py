"""Explicit pack acquisition and reproducible semantic regeneration boundaries.

Acquisition reads named local inputs. Pure preparation and database publication remain separate;
reference/evaluation files are never acquired as extraction inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .analytical_profile import analytical_inputs
from .composed import composed_dependencies
from .contracts import ExecutionModelInputs, trusted_execution_inputs
from .domain_operations import domain_rule_inputs
from .observations import prepare_source_inputs
from .prepare import prepare_release
from .proposals import proposal_inputs
from .types import (
    PreparationProfile,
    PreparedRelease,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)


def prepare_pack(
    pack: Path,
) -> tuple[SourceBundle, ResolvedDependencies, PreparationProfile, PreparedRelease]:
    """Acquire one explicit semantic pack without legacy compilation or reference discovery."""
    return prepare_packs((pack,))


@dataclass(frozen=True)
class PackInputs:
    """Named acquired bytes and operation dependencies, without compiler products."""

    origin: str
    name: str
    bundle: SourceBundle
    dependencies: ResolvedDependencies
    qualifications: tuple[str, ...]
    statements: tuple[str, ...]
    trusted_sources: tuple[SourceArtifact, ...]
    execution: ExecutionModelInputs


def acquire_pack(pack: Path) -> PackInputs:
    """Read explicit pack inputs once; never compile to discover dependencies."""
    source = pack / "semantic.yaml"
    if not source.is_file():
        raise ValueError(f"semantic declaration missing: {source}")
    document = yaml.safe_load(source.read_bytes())
    name = document["name"]
    if name in {
        "semantic_core",
        "composed_pack",
        "agent",
        "agent-root",
        "observations",
        "observation-root",
        "analytics",
        "analytical-root",
    }:
        raise ValueError(f"reserved semantic module name {name}")
    core = Path(__file__).resolve().parents[1] / "model/semantic/core.yaml"
    bundle = SourceBundle(
        name,
        (
            SourceArtifact(name, source.read_bytes()),
            SourceArtifact("semantic_core", core.read_bytes()),
        ),
    )
    methods = yaml.safe_load((pack / "methods.yaml").read_bytes())
    core_rules = pack.parent / "core/schema/rules.yaml"
    rules = pack / "schema/rules.yaml"
    deps = domain_rule_inputs(
        ResolvedDependencies(),
        rules.read_bytes() if rules.exists() else b"rules: []",
        core_rules.read_bytes() if core_rules.exists() else b"rules: []",
        aliases=methods.get("aliases", {}),
    )
    artifacts = tuple(
        SourceArtifact("operation/" + filename, (pack / filename).read_bytes())
        for filename in (
            "methods.yaml",
            "guideline.md",
            "queries.py",
            "policies.yaml",
            "slices.yaml",
        )
        if (pack / filename).is_file()
    )
    from corpus_structure.ingest.profile import SOURCES_DIR
    from corpus_structure.orchestrate.phase0 import registry as method_registry

    registry = method_registry(pack)
    profiles = {
        profile
        for method, config in registry.named()
        for _, profile in registry.profiles(method, config)
    }
    artifacts += tuple(
        SourceArtifact(f"source-profile/{name}.yaml", (SOURCES_DIR / f"{name}.yaml").read_bytes())
        for name in sorted(profiles)
    )
    split_policy = pack / "eval/split.yaml"
    if split_policy.is_file():
        artifacts += (SourceArtifact("operation/evaluation-split.yaml", split_policy.read_bytes()),)
    deps = ResolvedDependencies(
        (*deps.artifacts, *artifacts), deps.vocabularies, deps.ontology_sources
    )
    qualifiers = [
        key
        for key, definition in document.get("classes", {}).items()
        if definition.get("is_a") == "Qualification"
    ]
    if len(qualifiers) > 1:
        raise ValueError("pack requires one explicit Qualification subclass")
    statement_classes = [
        key
        for key, definition in document.get("classes", {}).items()
        if definition.get("is_a") == "SourceStatement"
    ]
    if len(statement_classes) > 1:
        raise ValueError("pack requires one explicit SourceStatement subclass")
    trusted_model = core.parent
    trusted = tuple(
        SourceArtifact(name, (trusted_model / name).read_bytes())
        for name in (
            "agent.yaml",
            "observations.yaml",
            "analytics.yaml",
            "metrics.yaml",
            "analytical-profile.json",
        )
    )
    return PackInputs(
        str(pack.resolve()),
        pack.name,
        bundle,
        deps,
        tuple(qualifiers),
        tuple(statement_classes),
        trusted,
        trusted_execution_inputs(),
    )


def compose_pack_inputs(acquired: tuple[PackInputs, ...]):
    """Compose acquired immutable inputs without any filesystem reads or preparation."""
    if not acquired:
        raise ValueError("at least one semantic pack is required")
    trusted = acquired[0].trusted_sources
    execution = acquired[0].execution
    if any(
        inputs.trusted_sources != trusted or inputs.execution != execution for inputs in acquired
    ):
        raise ValueError("packs disagree on trusted semantic inputs")
    content = {source.name: source.content for source in trusted}
    if len(acquired) == 1:
        inputs = acquired[0]
        bundle, deps = inputs.bundle, inputs.dependencies
        qualification = inputs.qualifications[0] if inputs.qualifications else "Qualification"
        statement_class = inputs.statements[0] if inputs.statements else "SourceStatement"
    else:
        sources: dict[str, SourceArtifact] = {}
        composed_artifacts: dict[str, SourceArtifact] = {}
        qualifiers = []
        statement_classes = []
        for inputs in acquired:
            bundle, deps = inputs.bundle, inputs.dependencies
            for source in bundle.sources:
                if source.name in {
                    "agent",
                    "agent-root",
                    "observations",
                    "observation-root",
                    "analytics",
                    "analytical-root",
                }:
                    continue
                previous = sources.setdefault(source.name, source)
                if previous != source:
                    raise ValueError(f"packs disagree on semantic module {source.name}")
            qualifiers.extend(inputs.qualifications)
            statement_classes.extend(inputs.statements)
            # Operation configuration remains pack-scoped, not a merged executable graph.
            for artifact in deps.artifacts:
                if artifact.name.startswith(("execution/", "operation/analytical")):
                    continue
                artifact = SourceArtifact(f"pack/{inputs.name}/{artifact.name}", artifact.content)
                previous = composed_artifacts.setdefault(artifact.name, artifact)
                if previous != artifact:
                    raise ValueError(f"packs disagree on dependency {artifact.name}")
        root: dict[str, Any] = {
            "id": "https://corpus-structure.dev/semantic/composed-pack",
            "name": "composed_pack",
            "prefixes": {"cs": "https://corpus-structure.dev/semantic/"},
            "default_prefix": "cs",
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
            raise ValueError(
                "composed packs require one explicit source-statement operation binding"
            )
        bundle = SourceBundle(
            "composed_pack",
            (*sources.values(), SourceArtifact("composed_pack", yaml.safe_dump(root).encode())),
        )
        deps = ResolvedDependencies(tuple(composed_artifacts.values()))
    bundle = proposal_inputs(
        bundle,
        deps,
        qualification_class=qualification,
        statement_class=statement_class,
        model_content=content["agent.yaml"],
        observation_content=content["observations.yaml"],
    )
    bundle, deps = prepare_source_inputs(
        bundle,
        deps,
        model_content=content["observations.yaml"],
        metric_content=content["metrics.yaml"],
    )
    bundle, deps = analytical_inputs(
        bundle,
        deps,
        model_content=content["analytics.yaml"],
        profile=content["analytical-profile.json"],
    )
    deps = composed_dependencies(deps, execution)
    return bundle, deps, PreparationProfile(version="semantic-2")


def prepare_packs(
    packs: tuple[Path, ...],
) -> tuple[SourceBundle, ResolvedDependencies, PreparationProfile, PreparedRelease]:
    packs = tuple(sorted({pack.resolve() for pack in packs}))
    acquired = tuple(acquire_pack(pack) for pack in packs)
    bundle, deps, profile = compose_pack_inputs(acquired)
    return bundle, deps, profile, prepare_release(bundle, deps, profile)
