"""Immutable configuration ABI for genuine archived semantic-agent packets.

Current external execution uses declared packet/result operations. These values
remain for exact historical producer/configuration interpretation only.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.core.evidence import MacroDef
from corpus_structure.core.method import ArtifactRef, ConfigRef, PackSection
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.semantic.proposals import SEMANTIC_AGENT_VERSION

DEFAULT_MODEL = "claude-opus-5-5"


class MathSection(BaseModel):
    """The pack's `math` section as M24 reads it (the fallback macro table)."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    macros: dict[str, str] = Field(default_factory=dict)
    constants: tuple[str, ...] = ()

    def macro_table(self) -> dict[str, MacroDef]:
        return {name: MacroDef(body=body) for name, body in self.macros.items()}


class AgentOpusConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    characterization_layers: tuple[dict[str, Any], ...] = ()

    proposal_protocol: Literal["semantic-claims"] = "semantic-claims"
    proposal_version: str = SEMANTIC_AGENT_VERSION
    execution_kind: Literal["agent"] = "agent"
    mode: Literal["extract", "adjudicate"] = "extract"
    role: Literal["live", "expectation"] = "live"
    examples: Literal["reference"] = "reference"
    hints: Literal["none"] = "none"
    packet_cap_chars: int = Field(18_000, gt=0)
    max_alternatives: int | None = None
    model: str = DEFAULT_MODEL
    max_units: int = Field(1, ge=1)
    sentences: Annotated[str | SentenceConfig, ConfigRef("segment.sentences")] = (
        "segment.sentences/default"
    )
    math: Annotated[MathSection, PackSection("math")] = MathSection()
    reference: Annotated[str, ArtifactRef("annotator_reference", "reference")] = ""
    json_schema: Annotated[str, ArtifactRef("json_schema", "batch.model_facing")] = ""
    rules: Annotated[str, ArtifactRef("rules", "rules")] = ""
