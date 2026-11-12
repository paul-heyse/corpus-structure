"""Pure source-operation intent and shared settings construction.

Implementation dependencies (engines, graphs and registries) are supplied separately.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Annotated, Any, ClassVar, Literal, cast

from pydantic import ConfigDict, Field, TypeAdapter

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.core.method import MethodSettings
from corpus_structure.semantic.product_reference import ProductReference


class SourceRequestError(ValueError):
    """A complete source operation refused before acquiring execution resources."""


@dataclass(frozen=True)
class PackDefault:
    kind: Literal["pack_default"] = field(default="pack_default", kw_only=True)
    pass


@dataclass(frozen=True)
class NamedSlice:
    kind: Literal["slice"] = field(default="slice", kw_only=True)
    name: str


@dataclass(frozen=True)
class NamedScope:
    kind: Literal["scope"] = field(default="scope", kw_only=True)
    name: str


@dataclass(frozen=True)
class WholeDocument:
    kind: Literal["whole_document"] = field(default="whole_document", kw_only=True)
    pass


SourceSelection = Annotated[
    PackDefault | NamedSlice | NamedScope | WholeDocument, Field(discriminator="kind")
]


@dataclass(frozen=True)
class EnsurePrimary:
    kind: Literal["ensure_primary"] = field(default="ensure_primary", kw_only=True)
    pass


@dataclass(frozen=True)
class RetainedViews:
    kind: Literal["retained_views"] = field(default="retained_views", kw_only=True)
    views: tuple[ProductReference, ...]

    def __post_init__(self):
        object.__setattr__(self, "views", tuple(self.views))
        if not all(isinstance(pin, ProductReference) for pin in self.views):
            raise SourceRequestError("retained views require exact product pins")
        if not 1 <= len(self.views) <= 256 or len(set(self.views)) != len(self.views):
            raise SourceRequestError(
                "analytical source binding requires 1..256 distinct enriched-document views"
            )


@dataclass(frozen=True)
class Phase0Analysis:
    kind: Literal["phase0_analysis"] = field(default="phase0_analysis", kw_only=True)
    primary: EnsurePrimary | RetainedViews = EnsurePrimary()

    def __post_init__(self):
        if not isinstance(self.primary, (EnsurePrimary, RetainedViews)):
            raise SourceRequestError("unknown primary input selection")


@dataclass(frozen=True)
class CharacterizationOptions:
    """Canonical immutable method options, interpreted by the characterization owner."""

    content: bytes

    @classmethod
    def from_options(cls, options: dict[str, Any]):
        if not isinstance(options, dict):
            raise SourceRequestError("characterization method options must be an object")
        return cls(json.dumps(options, sort_keys=True, allow_nan=False).encode())

    def options(self) -> dict[str, Any]:
        value = json.loads(self.content)
        if not isinstance(value, dict):
            raise SourceRequestError("characterization method options must be an object")
        return value


@dataclass(frozen=True)
class Capture:
    kind: Literal["capture"] = field(default="capture", kw_only=True)
    enrichment: CharacterizationOptions | None = None

    def __post_init__(self):
        if self.enrichment is not None and not isinstance(self.enrichment, CharacterizationOptions):
            raise SourceRequestError("capture enrichment requires characterization options")


M1Configuration = Literal["default", "described", "readings", "contextual", "source-only"]


@dataclass(frozen=True)
class M1Candidate:
    kind: Literal["m1_candidate"] = field(default="m1_candidate", kw_only=True)
    configuration: Literal["default", "described", "readings", "contextual", "source-only"] = (
        "default"
    )
    record_policy: bytes | None = None
    primary: EnsurePrimary | RetainedViews = EnsurePrimary()

    def __post_init__(self):
        if not isinstance(self.primary, (EnsurePrimary, RetainedViews)):
            raise SourceRequestError("unknown primary input selection")
        if self.configuration not in {
            "default",
            "described",
            "readings",
            "contextual",
            "source-only",
        }:
            raise SourceRequestError(
                "M1 configuration must be default, described, readings, contextual or source-only"
            )
        if self.record_policy is not None:
            if self.configuration not in {"readings", "contextual"}:
                raise SourceRequestError(
                    "record policy parameters require an M1 reading-resolution configuration"
                )
            if not isinstance(json.loads(self.record_policy), dict):
                raise SourceRequestError("record policy parameters must be an object")
        if self.configuration == "source-only" and isinstance(self.primary, RetainedViews):
            raise SourceRequestError("source-only M1 cannot select characterization views")


@dataclass(frozen=True)
class DeclaredInputs:
    kind: Literal["declared_inputs"] = field(default="declared_inputs", kw_only=True)
    pass


@dataclass(frozen=True)
class ConfiguredGraph:
    kind: Literal["configured_graph"] = field(default="configured_graph", kw_only=True)
    inputs: DeclaredInputs | RetainedViews = DeclaredInputs()

    def __post_init__(self):
        if not isinstance(self.inputs, (DeclaredInputs, RetainedViews)):
            raise SourceRequestError("unknown configured graph input selection")


SourceWorkflow = Annotated[
    Phase0Analysis | Capture | M1Candidate | ConfiguredGraph, Field(discriminator="kind")
]


@dataclass(frozen=True)
class SourceRunRequest:
    __pydantic_config__: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
    project_id: str
    release_id: str | None = None
    realization_id: str | None = None
    domain: str | None = None
    selection: SourceSelection = PackDefault()
    workflow: SourceWorkflow = Phase0Analysis()
    membership: Literal["direct", "descendants"] | None = None
    native_product: ProductReference | None = None
    integrated_product: ProductReference | None = None
    fresh: tuple[str, ...] = ()
    phase: int = 0
    agent_mode: str = "complete"
    agent_reuse: str = "full"
    registration_corpus: Path | None = None

    def __post_init__(self):
        if not isinstance(self.selection, (PackDefault, NamedSlice, NamedScope, WholeDocument)):
            raise SourceRequestError("unknown source selection")
        if not isinstance(self.workflow, (Phase0Analysis, Capture, M1Candidate, ConfiguredGraph)):
            raise SourceRequestError("unknown source workflow")
        for variant in (self.selection, self.workflow):
            if variant.kind != variant.__dataclass_fields__["kind"].default:
                raise SourceRequestError("source variant tag differs from its typed selection")
        if isinstance(self.fresh, (str, bytes)):
            raise SourceRequestError("fresh methods require nonempty method names")
        try:
            fresh = tuple(self.fresh)
        except TypeError as error:
            raise SourceRequestError("fresh methods require nonempty method names") from error
        if any(not isinstance(name, str) or not name.strip() for name in fresh):
            raise SourceRequestError("fresh methods require nonempty method names")
        object.__setattr__(self, "fresh", fresh)
        if not isinstance(self.project_id, str) or not self.project_id.strip():
            raise SourceRequestError("source operation requires a project")
        for name in ("release_id", "realization_id"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise SourceRequestError(f"{name} requires a nonempty identity")
        if type(self.phase) is not int:
            raise SourceRequestError("source phase must be an integer")
        validate_source_agent_policy(self.agent_mode, self.agent_reuse)
        if self.domain is not None and (
            not isinstance(self.domain, str)
            or not self.domain.strip()
            or self.domain in {".", ".."}
            or Path(self.domain).name != self.domain
        ):
            raise SourceRequestError("domain must name a declared pack")
        if self.membership not in {None, "direct", "descendants"}:
            raise SourceRequestError("source membership must be direct or descendants")
        validate_source_roles(self.native_product, self.integrated_product)
        if any(
            value is not None and not isinstance(value, ProductReference)
            for value in (self.native_product, self.integrated_product)
        ):
            raise SourceRequestError("source products require exact ProductReference pins")
        if isinstance(self.workflow, M1Candidate) and (
            self.native_product is not None
            or not isinstance(self.integrated_product, ProductReference)
        ):
            raise SourceRequestError(
                "M1 requires one exact retained integrated PDF product pin; "
                "conversion and fallback are disabled"
            )
        if isinstance(self.workflow, Capture) and self.workflow.enrichment is not None:
            self.workflow.enrichment.options()
        primary = getattr(self.workflow, "primary", getattr(self.workflow, "inputs", None))
        if primary is not None and primary.kind != primary.__dataclass_fields__["kind"].default:
            raise SourceRequestError("source variant tag differs from its typed selection")
        if isinstance(primary, RetainedViews):
            from .characterization import PRIMARY_PRODUCERS

            if set(self.fresh) & PRIMARY_PRODUCERS:
                raise SourceRequestError(
                    "retained characterization views cannot request fresh inference"
                )
        if isinstance(self.selection, (NamedSlice, NamedScope)) and (
            not isinstance(self.selection.name, str) or not self.selection.name.strip()
        ):
            raise SourceRequestError("source selection requires a nonempty name")


def validate_source_agent_policy(agent_mode, agent_reuse) -> None:
    if agent_mode != "complete":
        raise SourceRequestError(
            "semantic agent wait barrier is not implemented; "
            "use complete and finalize after automated tasks finish"
        )
    if agent_reuse != "full":
        raise SourceRequestError(
            "semantic agent reuse requires the full immutable packet and configuration"
        )


def validate_source_roles(native, integrated) -> None:
    """The same completeness rule applies before and after product-file parsing."""
    if native is not None and integrated is not None:
        raise SourceRequestError(
            "native-source and integrated-source are mutually exclusive; "
            "select one exact native or integrated PDF input role"
        )


def source_selection(*, slice=None, scope=None, whole_document=False, corpus=None):
    if whole_document and (slice is not None or scope is not None):
        raise SourceRequestError("whole-document is mutually exclusive with slice and scope")
    if slice is not None and scope is not None:
        raise SourceRequestError("choose slice or scope, not both")
    if corpus is not None:
        raise SourceRequestError(
            "PDF source acquisition selects registered originals; corpus selectors are retired"
        )
    if whole_document:
        return WholeDocument()
    if slice is not None:
        return NamedSlice(slice)
    if scope is not None:
        return NamedScope(scope)
    return PackDefault()


def source_workflow(
    *,
    extraction_policy="phase0",
    m1_configuration="default",
    record_policy=None,
    source_only=False,
    characterization_views=(),
):
    primary = (
        RetainedViews(tuple(characterization_views)) if characterization_views else EnsurePrimary()
    )
    if extraction_policy not in {"phase0", "m1-candidate"}:
        raise SourceRequestError("unknown extraction policy")
    if extraction_policy == "m1-candidate":
        if source_only:
            raise SourceRequestError("M1 source-only is selected by its named configuration")
        return M1Candidate(
            cast(M1Configuration, m1_configuration),
            json.dumps(record_policy).encode() if record_policy is not None else None,
            primary,
        )
    if m1_configuration != "default":
        raise SourceRequestError("nondefault M1 configuration requires the m1-candidate policy")
    if record_policy is not None:
        raise SourceRequestError(
            "record policy parameters require an M1 reading-resolution configuration"
        )
    if source_only:
        if characterization_views:
            raise SourceRequestError("capture cannot select characterization views")
        return Capture()
    return Phase0Analysis(primary)


def integrated_product_pin(
    task: int | None = None, key: str | None = None, digest: str | None = None
):
    values = (task, key, digest)
    if any(value is not None for value in values) and not all(
        value is not None for value in values
    ):
        raise SourceRequestError(
            "integrated product task, key and digest must be supplied together"
        )
    if task is None:
        return None
    assert key is not None and digest is not None
    return ProductReference(task, key, digest)


def method_settings(settings, overrides: dict[str, Any] | None = None) -> MethodSettings:
    """Merge result-neutral overrides and build the complete shared method view."""
    policy = settings.characterization_execution
    if overrides is not None:
        if not isinstance(overrides, dict):
            raise SourceRequestError("execution policy must be an object")
        policy = TypeAdapter(CharacterizationExecutionPolicy).validate_python(
            {**asdict(policy), **overrides}
        )
    return MethodSettings(
        data_dir=settings.paths.data_dir,
        model_cache=settings.paths.model_cache,
        nemotron_endpoint=settings.nemotron.endpoint,
        nemotron_python=settings.nemotron.python,
        nemotron_worker=settings.nemotron.worker,
        nemotron_receipts=settings.nemotron.receipts,
        nemotron_timeout_seconds=settings.nemotron.timeout_seconds,
        execution_policy=policy,
    )
