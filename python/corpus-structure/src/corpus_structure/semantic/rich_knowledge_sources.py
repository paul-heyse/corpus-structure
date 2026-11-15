"""Current rich source and explicit policy composition, independent of execution catalogs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

import yaml
from linkml_runtime.utils.yamlutils import DupCheckYamlLoader

from .identity import canonical_bytes
from .types import ResolvedDependencies, SourceArtifact, SourceBundle

RULE_INPUT = "operation/domain-rules.yaml"
VERSION = "semantic-domain-3"
RICH_CONTRACT_INPUT = "operation/rich-knowledge-contracts.json"


def parse_policy_yaml(content):
    """Keep LinkML duplicate refusal and lower its location-tagged strings to YAML scalars."""

    def scalars(value):
        if isinstance(value, str):
            return value[:]
        if isinstance(value, dict):
            return {scalars(k): scalars(v) for k, v in value.items()}
        if isinstance(value, list):
            return [scalars(v) for v in value]
        return value

    return scalars(yaml.load(content, Loader=DupCheckYamlLoader))


def rich_policy_inputs(
    dependencies: ResolvedDependencies,
    domain: bytes,
    core: bytes = b"",
    *,
    aliases: Mapping[str, Any] | None = None,
    context_profile,
) -> ResolvedDependencies:
    """Archive existing rules as one operation dependency, never read latest files in a run."""
    from .alias_policy import SOURCE_PROFILE
    from .scientific_evidence import scientific_policy_recipe

    source = parse_policy_yaml(domain) or {}
    base = parse_policy_yaml(core) or {}
    if set(base) - {"rules"}:
        raise ValueError("core operation rules must contain only rules")
    source["rules"] = [*base.get("rules", ()), *source.get("rules", ())]
    operation = {"name": "semantic-domain", "version": VERSION}
    if "operation" in source and source["operation"] != operation:
        raise ValueError("unsupported domain operation header")
    source["operation"] = operation
    from .rule_views import RULE_VIEW_ABI

    source["rule_view_abi"] = RULE_VIEW_ABI
    if aliases is not None:
        source["identity"] = {"aliases": dict(aliases)}
    identity = source.setdefault("identity", {})
    if not isinstance(identity, dict):
        raise ValueError("invalid operation identity policy")
    if identity.get("alias_profile", SOURCE_PROFILE) != SOURCE_PROFILE:
        raise ValueError("unsupported alias input profile")
    identity["alias_profile"] = SOURCE_PROFILE
    if any(a.name == RULE_INPUT for a in dependencies.artifacts):
        raise ValueError("domain rules already declared")
    return replace(
        dependencies,
        artifacts=(
            *dependencies.artifacts,
            SourceArtifact(RULE_INPUT, yaml.safe_dump(source, sort_keys=True).encode()),
            SourceArtifact(
                "operation/scientific-policy.json",
                canonical_bytes(scientific_policy_recipe(context_profile=context_profile)),
            ),
            *(
                SourceArtifact(
                    "operation/" + name,
                    (Path(__file__).resolve().parents[1] / "model/semantic" / name).read_bytes(),
                )
                for name in ("scientific.yaml", "scientific-policies.yaml")
            ),
            SourceArtifact(
                "operation/rule-view.yaml",
                (
                    Path(__file__).resolve().parents[1] / "model/semantic/rule-view.yaml"
                ).read_bytes(),
            ),
        ),
    )


def rich_knowledge_inputs(
    bundle: SourceBundle, dependencies: ResolvedDependencies, *,
    domain_rules: bytes, core_rules: bytes = b"", context_profile,
    aliases: Mapping[str, Any] | None = None,
) -> tuple[SourceBundle, ResolvedDependencies]:
    """Compose actual source/proposal/reading contracts and explicit rich policy.

    No installed execution model, task catalog or old pack acquisition supplies
    semantic authority. The returned declaration artifact is passed explicitly
    to the same current DDO compiler via rich_knowledge_declarations().
    """
    from .external_extraction import external_extraction_inputs
    from .observations import prepare_source_inputs
    from .record_assertions import source_reading_inputs
    from .rich_knowledge_contracts import rich_kind_declarations
    from .data_operation_model import MODEL_VERSION

    if any(artifact.name == RICH_CONTRACT_INPUT for artifact in dependencies.artifacts):
        raise ValueError("rich knowledge contracts already declared")
    bundle, dependencies = prepare_source_inputs(bundle, dependencies)
    bundle = external_extraction_inputs(bundle, dependencies)
    bundle = source_reading_inputs(bundle)
    dependencies = rich_policy_inputs(
        dependencies, domain_rules, core_rules, context_profile=context_profile, aliases=aliases,
    )
    declarations = SourceArtifact(RICH_CONTRACT_INPUT, canonical_bytes({
        "version": MODEL_VERSION, "kinds": rich_kind_declarations(),
    }))
    return bundle, replace(dependencies, artifacts=(*dependencies.artifacts, declarations))


def rich_knowledge_declarations(dependencies: ResolvedDependencies) -> tuple[SourceArtifact, ...]:
    """Select the actual captured rich declarations; never regenerate a runtime schema."""
    selected = tuple(artifact for artifact in dependencies.artifacts if artifact.name == RICH_CONTRACT_INPUT)
    if len(selected) != 1:
        raise ValueError("rich knowledge requires its exact captured nominal declarations")
    return selected
