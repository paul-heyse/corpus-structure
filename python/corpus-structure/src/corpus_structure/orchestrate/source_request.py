"""Explicit source choices for compilation into immutable native demand intent."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Annotated, Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.core.method import MethodSettings
from corpus_structure.semantic.data_operation_service import DdoJsonValue, DemandOperationSelection
from corpus_structure.semantic.structural_products import ExternalSourceRef


class SourceRequestError(ValueError):
    """Source choices cannot be frozen against the admitted operation model."""


@dataclass(frozen=True)
class PackDefault:
    __pydantic_config__: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
    kind: Literal["pack_default"] = field(default="pack_default", kw_only=True)


@dataclass(frozen=True)
class NamedSlice:
    __pydantic_config__: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
    name: str
    kind: Literal["slice"] = field(default="slice", kw_only=True)


@dataclass(frozen=True)
class NamedScope:
    __pydantic_config__: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
    name: str
    kind: Literal["scope"] = field(default="scope", kw_only=True)


@dataclass(frozen=True)
class WholeDocument:
    __pydantic_config__: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
    kind: Literal["whole_document"] = field(default="whole_document", kw_only=True)


SourceSelection = Annotated[
    PackDefault | NamedSlice | NamedScope | WholeDocument, Field(discriminator="kind")
]


class RetainedSourceSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source: ExternalSourceRef
    selectors: tuple[dict[str, DdoJsonValue], ...] = Field(min_length=1)


class SourceRunRequest(BaseModel):
    """Source frontdoor choices, independent of stages, registries and old run IDs."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    project_id: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    runtime_id: str = Field(min_length=1)
    domain: str | None = None
    selection: SourceSelection = PackDefault()
    workflow: Literal["phase0", "capture", "characterize"] = "phase0"
    membership: Literal["direct", "descendants"] = "descendants"
    documents: tuple[str, ...] = ()
    retained_sources: tuple[RetainedSourceSelection, ...] = ()
    targets: tuple[str, ...] = ()
    selections: tuple[DemandOperationSelection, ...] = ()
    execution_profile: str = "source-native"
    inference: str = "declared"

    @field_validator("domain")
    @classmethod
    def declared_domain(cls, value):
        if value is not None and (not value or value in {".", ".."} or Path(value).name != value):
            raise ValueError("domain must name a declared pack")
        return value


def source_selection(*, slice=None, scope=None, whole_document=False, corpus=None):
    if corpus is not None:
        raise SourceRequestError("source acquisition selects registered originals")
    if whole_document and (slice is not None or scope is not None):
        raise SourceRequestError("whole-document is mutually exclusive with slice and scope")
    if slice is not None and scope is not None:
        raise SourceRequestError("choose slice or scope, not both")
    if whole_document:
        return WholeDocument()
    if slice is not None:
        return NamedSlice(slice)
    if scope is not None:
        return NamedScope(scope)
    return PackDefault()


def validate_source_agent_policy(agent_mode, agent_reuse) -> None:
    """Sealed legacy readers may still validate their recorded policy."""
    if agent_mode != "complete" or agent_reuse != "full":
        raise SourceRequestError("the retained policy requires complete mode and full packet reuse")


def validate_source_roles(native, integrated) -> None:
    if native is not None and integrated is not None:
        raise SourceRequestError("select one exact native or integrated PDF input role")


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
