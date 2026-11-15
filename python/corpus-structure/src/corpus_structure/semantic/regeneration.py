"""Explicit pack acquisition and reproducible semantic regeneration boundaries.

Acquisition reads named local inputs. Pure preparation and database publication remain separate;
reference/evaluation files are never acquired as extraction inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .prepare import prepare_release
from .refusals import SemanticRefusal
from .rich_knowledge_sources import rich_policy_inputs
from .types import (
    PreparationProfile,
    PreparedRelease,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)


class PackInputError(SemanticRefusal):
    """Explicit local pack inputs cannot form a supported semantic preparation."""


def _mapping(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_bytes())
    except (OSError, yaml.YAMLError) as error:
        raise PackInputError(f"cannot read pack declaration {path}: {error}") from error
    if not isinstance(value, dict):
        raise PackInputError(f"pack declaration must be a mapping: {path}")
    return value


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


def acquire_pack(pack: Path) -> PackInputs:
    """Capture domain schema, terminology and declared policy bytes without compilation."""
    source = pack / "semantic.yaml"
    if not source.is_file():
        raise PackInputError(f"semantic declaration missing: {source}")
    document = _mapping(source)
    name = document.get("name")
    if not isinstance(name, str) or not name:
        raise PackInputError(f"pack declaration requires a nonempty name: {source}")
    if name in {
        "semantic_core",
        "composed_pack",
        "agent",
        "agent-root",
        "observations",
        "observation-root",
        "characterization",
        "characterization-root",
        "record_references",
        "record-reference-root",
        "record_policy",
        "record-policy-root",
        "analytics",
        "analytical-root",
    }:
        raise PackInputError(f"reserved semantic module name {name}")
    core = Path(__file__).resolve().parents[1] / "model/semantic/core.yaml"
    bundle = SourceBundle(
        name,
        (
            SourceArtifact(name, source.read_bytes()),
            SourceArtifact("semantic_core", core.read_bytes()),
        ),
    )
    from .terminology import acquire_terminology

    terminology_sources, terminology_artifacts, ontology_names = acquire_terminology(pack)
    bundle = SourceBundle(bundle.root, (*bundle.sources, *terminology_sources))
    methods = _mapping(pack / "methods.yaml")
    core_rules = pack.parent / "core/schema/rules.yaml"
    rules = pack / "schema/rules.yaml"
    from .analysis_contracts import acquire_analysis_context_profile

    deps = rich_policy_inputs(
        ResolvedDependencies(),
        rules.read_bytes() if rules.exists() else b"rules: []",
        core_rules.read_bytes() if core_rules.exists() else b"rules: []",
        aliases=methods.get("aliases", {}),
        context_profile=acquire_analysis_context_profile(),
    )
    artifacts = tuple(
        SourceArtifact("operation/" + filename, (pack / filename).read_bytes())
        for filename in (
            "methods.yaml",
            "guideline.md",
            "queries.py",
            "policies.yaml",
            "slices.yaml",
            "interpretation-questions.yaml",
            "pm2-definition-policy.json",
        )
        if (pack / filename).is_file()
    )
    from .query_compatibility import acquire_query_inputs

    artifacts += acquire_query_inputs(pack)
    split_policy = pack / "eval/split.yaml"
    if split_policy.is_file():
        artifacts += (SourceArtifact("operation/evaluation-split.yaml", split_policy.read_bytes()),)
    deps = ResolvedDependencies(
        (*deps.artifacts, *artifacts, *terminology_artifacts),
        deps.vocabularies,
        (*deps.ontology_sources, *ontology_names),
    )
    qualifiers = [
        key
        for key, definition in document.get("classes", {}).items()
        if definition.get("is_a") == "Qualification"
    ]
    if len(qualifiers) > 1:
        raise PackInputError("pack requires one explicit Qualification subclass")
    statement_classes = [
        key
        for key, definition in document.get("classes", {}).items()
        if definition.get("is_a") == "SourceStatement"
    ]
    if len(statement_classes) > 1:
        raise PackInputError("pack requires one explicit SourceStatement subclass")
    return PackInputs(
        str(pack.resolve()),
        pack.name,
        bundle,
        deps,
        tuple(qualifiers),
        tuple(statement_classes),
    )


def compose_pack_inputs(acquired: tuple[PackInputs, ...]):
    """Compose acquired immutable inputs without any filesystem reads or preparation."""
    if not acquired:
        raise PackInputError("at least one semantic pack is required")
    if len(acquired) == 1:
        inputs = acquired[0]
        bundle, deps = inputs.bundle, inputs.dependencies
    else:
        from .alias_policy import RULE_INPUT, SOURCE_PROFILE
        from .identity import canonical_bytes

        sources: dict[str, SourceArtifact] = {}
        composed_artifacts: dict[str, SourceArtifact] = {}
        qualifiers = []
        statement_classes = []
        shared_policy = None
        shared_origin = None
        alias_contexts = []
        # These remain one operation's inputs. Equal inputs coalesce; incompatible
        # policies require an explicit future operation binding, not an order winner.
        shared_artifacts: dict[str, SourceArtifact] = {}
        ontology_names: set[str] = set()
        supplied_vocabularies = {}
        for inputs in acquired:
            bundle, deps = inputs.bundle, inputs.dependencies
            ontology_names.update(deps.ontology_sources)
            for snapshot in deps.vocabularies:
                previous = supplied_vocabularies.setdefault(snapshot.enum, snapshot)
                if previous != snapshot:
                    raise PackInputError(f"packs disagree on vocabulary snapshot {snapshot.enum}")
            for source in bundle.sources:
                previous = sources.setdefault(source.name, source)
                if previous != source:
                    raise PackInputError(f"packs disagree on semantic module {source.name}")
            qualifiers.extend(inputs.qualifications)
            statement_classes.extend(inputs.statements)
            rule_input = next(a for a in deps.artifacts if a.name == RULE_INPUT)
            policy = yaml.safe_load(rule_input.content)
            identity = policy.pop("identity", {})
            if (
                not isinstance(identity, dict)
                or set(identity) - {"alias_profile", "aliases"}
                or identity.get("alias_profile") != SOURCE_PROFILE
            ):
                raise PackInputError(f"unsupported acquired alias input: {inputs.origin}")
            try:
                differs = shared_policy is not None and canonical_bytes(policy) != canonical_bytes(
                    shared_policy
                )
            except (TypeError, ValueError) as error:
                raise PackInputError(
                    f"invalid non-alias operation policy: {inputs.origin}"
                ) from error
            if differs:
                raise PackInputError(
                    f"incompatible non-alias operation policy: {shared_origin} and {inputs.origin}"
                )
            shared_policy, shared_origin = policy, inputs.origin
            alias_contexts.append(
                # Source-module attribution is reproducible across checkout paths.
                {"origin": bundle.root, "root": bundle.root, "aliases": identity.get("aliases", {})}
            )
            # Operation configuration remains pack-scoped, not a merged executable graph.
            for artifact in deps.artifacts:
                if (
                    artifact.name.startswith("terminology/")
                    or artifact.name in deps.ontology_sources
                ):
                    previous = shared_artifacts.setdefault(artifact.name, artifact)
                    if previous != artifact:
                        raise PackInputError(f"packs disagree on terminology input {artifact.name}")
                    continue
                if artifact.name in {
                    "operation/rule-view.yaml",
                    "operation/scientific-policy.json",
                    "operation/scientific.yaml",
                    "operation/scientific-policies.yaml",
                }:
                    previous = shared_artifacts.setdefault(artifact.name, artifact)
                    if previous != artifact:
                        raise PackInputError(f"packs disagree on operation input {artifact.name}")
                artifact = SourceArtifact(f"pack/{inputs.name}/{artifact.name}", artifact.content)
                previous = composed_artifacts.setdefault(artifact.name, artifact)
                if previous != artifact:
                    raise PackInputError(f"packs disagree on dependency {artifact.name}")
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
        if len(statement_classes) > 1:
            raise PackInputError(
                "composed packs require one explicit source-statement operation binding"
            )
        bundle = SourceBundle(
            "composed_pack",
            (*sources.values(), SourceArtifact("composed_pack", yaml.safe_dump(root).encode())),
        )
        assert shared_policy is not None  # acquired is nonempty and every pack has RULE_INPUT
        shared_policy["identity"] = {
            "alias_profile": SOURCE_PROFILE,
            "alias_contexts": alias_contexts,
        }
        deps = ResolvedDependencies(
            (
                *composed_artifacts.values(),
                *shared_artifacts.values(),
                SourceArtifact(RULE_INPUT, yaml.safe_dump(shared_policy, sort_keys=True).encode()),
            ),
            tuple(supplied_vocabularies.values()),
            tuple(sorted(ontology_names)),
        )
    # Resolve module and prefix agreement against captured schema bytes only. Rich
    # source/proposal constructors are acquisition, and run after this pure merge.
    from .prepare import _view

    profile = PreparationProfile()
    _view(bundle, profile)
    return bundle, deps, profile


def _boundary_classes(acquired: tuple[PackInputs, ...]) -> tuple[str, str]:
    qualifications = tuple(name for inputs in acquired for name in inputs.qualifications)
    statements = tuple(name for inputs in acquired for name in inputs.statements)
    if len(statements) > 1:
        raise PackInputError(
            "composed packs require one explicit source-statement operation binding"
        )
    qualification = (
        "ComposedQualification"
        if len(acquired) > 1 and qualifications
        else qualifications[0]
        if qualifications
        else "Qualification"
    )
    return qualification, statements[0] if statements else "SourceStatement"


def acquire_packs(
    packs: tuple[Path, ...],
    *,
    physical_sources: dict[str, bytes] | None = None,
) -> tuple[SourceBundle, ResolvedDependencies, PreparationProfile]:
    """Acquire the current domain/source/DDO capsule after pure pack composition."""
    from .composed import data_operation_dependencies
    from .data_operation_artifacts import capture_port_generator_sources
    from .data_operation_storage import native_operation_declarations, native_protocol_sources
    from .record_policy_authority import record_policy_kind_declarations
    from .rich_invocations import rich_knowledge_operation_sources
    from .rich_knowledge_sources import (
        rich_knowledge_declarations,
        rich_knowledge_schema_inputs,
    )

    packs = tuple(sorted({pack.resolve() for pack in packs}))
    acquired = tuple(acquire_pack(pack) for pack in packs)
    bundle, dependencies, _profile = compose_pack_inputs(acquired)
    qualification, statement = _boundary_classes(acquired)
    bundle, dependencies = rich_knowledge_schema_inputs(
        bundle,
        dependencies,
        qualification_class=qualification,
        statement_class=statement,
    )
    native_options = {}
    if physical_sources is not None:
        from corpus_structure.schema.physical import linkml_types_source

        native_options = {
            "physical_sources": physical_sources,
            "linkml_types": linkml_types_source(),
        }
    native = native_protocol_sources(**native_options)
    dependencies = data_operation_dependencies(
        ResolvedDependencies(
            (*dependencies.artifacts, *native, *capture_port_generator_sources()),
            dependencies.vocabularies,
            dependencies.ontology_sources,
        ),
        (
            *rich_knowledge_declarations(dependencies),
            record_policy_kind_declarations(),
            native_operation_declarations(native),
        ),
        rich_knowledge_operation_sources(),
    )
    return bundle, dependencies, PreparationProfile(version="semantic-2")


def prepare_packs(
    packs: tuple[Path, ...],
    *,
    physical_sources: dict[str, bytes] | None = None,
) -> tuple[SourceBundle, ResolvedDependencies, PreparationProfile, PreparedRelease]:
    bundle, deps, profile = acquire_packs(packs, physical_sources=physical_sources)
    return bundle, deps, profile, prepare_release(bundle, deps, profile)
