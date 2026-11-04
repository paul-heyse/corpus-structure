"""M24 `agent.opus` (agent interface §3.2; D4 M24, §1; D2 §12.1; D6 §4).

Family and tier `agent`, unit type `source_view` (an intact native section projection).
The pipeline never runs it: its tasks are created `awaiting_agent` and completed through
the MCP server's `propose_claims`.

- **Configuration** (`agent.opus/<name>` in `methods.yaml`): `mode`, `role` (an `expectation`
  configuration keeps golden-expectation digests apart), `examples: reference`, `hints: none`,
  `packet_cap_chars`, the resolved named sentence configuration, the declared `model`
  (recorded with every intervention; the server cannot observe the session's model), `max_units`
  (1 until A3 decides), the pack's `math` section (the fallback macros the standing context and
  parse read) and the compiled artifacts by (compiler, kind): the annotator reference, the
  model-facing JSON Schema and the rule set.
- **`select`**: the run's admitted, scoped native source views, by stable source-view key.
- **`input_digest`** assembles the packet once per unit (cached) and returns
  `Digest(bytes, packet_hash)`; the bytes are the canonical JSON of the packet hash, the prompt-part
  hashes, the artifact hashes and the declared model. Current execution hashes the complete
  immutable packet; task ids never enter it.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.core.canonical import canonical_json
from corpus_structure.core.evidence import MacroDef
from corpus_structure.core.method import (
    ArtifactRef,
    ConfigRef,
    Digest,
    MethodContext,
    PackSection,
    Resources,
    SourceRunContext,
    UnitRef,
    UnitResult,
    UnitView,
)
from corpus_structure.core.vocab import (
    ConfidenceSource,
    MethodFamily,
    MethodTier,
    TaskUnitType,
)
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


class AgentOpus:
    """`agent.opus`, M24 (module doc)."""

    name = "agent.opus"
    version = SEMANTIC_AGENT_VERSION
    family = MethodFamily.AGENT
    unit_type = TaskUnitType.SOURCE_VIEW
    tier = MethodTier.AGENT
    confidence_source: ConfidenceSource | None = ConfidenceSource.AGENT
    Config = AgentOpusConfig
    resources = Resources()

    # -- select --------------------------------------------------------------------------------

    def select(self, run: SourceRunContext, cfg: AgentOpusConfig) -> Iterable[UnitRef]:
        return tuple(
            UnitRef(TaskUnitType.SOURCE_VIEW, ref.id, ref.key) for ref in run.reader.source_views()
        )

    def input_digest(self, unit: UnitView, cfg: AgentOpusConfig) -> Digest:
        from corpus_structure.methods.math.native import native_proposal_packet

        if unit.ref.unit_type is not TaskUnitType.SOURCE_VIEW or unit.ref.unit_id is None:
            raise ValueError("agent tasks require a selected PDF SourceView")
        packet = native_proposal_packet(
            unit.run.reader,
            unit.ref.unit_id,
            unit.run.reader.prepared,
            cfg.model_dump(mode="json"),
        )
        return Digest(canonical_json({"packet": packet.hash, "model": cfg.model}), packet.hash)

    def run(
        self, units: Sequence[UnitView], cfg: AgentOpusConfig, ctx: MethodContext
    ) -> Sequence[UnitResult]:
        raise RuntimeError(
            "agent.opus tasks are completed by the session through propose_claims (D4 M24); "
            "no worker runs them"
        )


class AgentGeneral(AgentOpus):
    """A second producer identity using the same implemented proposal protocol."""

    name = "agent.general"
