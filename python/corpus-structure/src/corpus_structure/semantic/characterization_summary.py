"""Bounded metadata from actual retained characterization executions.

These fields report the selected product's original provenance and availability;
they do not assert current provider activity or analytical member truth.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FamilyOutcomeSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    family: str
    outcome: Literal["complete", "empty", "partial", "failed", "unknown", "unsupported"]
    availability: Literal["available", "unknown", "unsupported", "unavailable"]


class ProviderAvailabilitySummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    family: str
    attribute: str
    status: Literal["complete", "partial", "absent", "not_applicable"]


class RetainedProviderSummary(BaseModel):
    """Actual retained provider metadata, never current physical activity."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    provider: str
    profile: str
    model: str
    model_version: str
    runtime_version: str
    configuration_digest: str
    availability: tuple[ProviderAvailabilitySummary, ...] = Field(max_length=32)
    availability_omitted: int = Field(ge=0)


