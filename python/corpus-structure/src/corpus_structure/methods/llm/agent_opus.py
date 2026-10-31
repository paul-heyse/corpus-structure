"""M24 `agent.opus` (agent interface §3.2; D4 M24, §1; D2 §12.1; D6 §4).

Family and tier `agent`, unit type `source_view` (an intact native section projection). The pipeline never runs it: its
tasks are created `awaiting_agent` and completed through the MCP server's `propose_claims`.

- **Configuration** (`agent.opus/<name>` in `methods.yaml`): `mode`, `role` (an `expectation`
  configuration keeps golden-expectation digests apart), `examples: reference`, `hints: none`,
  `packet_cap_chars`, the resolved named sentence configuration, the declared `model` (recorded with every intervention; the server cannot
  observe the session's model), `max_units` (1 until A3 decides), the pack's `math` section (the
  fallback macros the standing context and parse read) and the compiled artifacts by (compiler,
  kind): the annotator reference, the model-facing JSON Schema and the rule set.
- **`select`**: the run's admitted, scoped native source views, by stable source-view key.
- **`input_digest`** assembles the packet once per unit (cached) and returns
  `Digest(bytes, packet_hash)`; the bytes are the canonical JSON of the packet hash, the prompt-part
  hashes, the artifact hashes and the declared model. Under `agent_reuse: by_unit` the guideline
  input is `parts.by_unit_guideline` for the unit instead of the guideline part's hash. Task ids
  never enter it.
"""

from __future__ import annotations

import threading
from collections.abc import Iterable, Mapping, Sequence
from typing import Annotated, Any, Literal

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
    AgentReuse,
    ConfidenceSource,
    MethodFamily,
    MethodTier,
    TaskUnitType,
)
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.llm import packet as P
from corpus_structure.methods.llm import parts as parts_

VERSION = "5"  # bumped on any change to the packet rendering or the prompts
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


def page_of(conn: Any, document_id: int) -> str:
    from sqlalchemy import text

    page = conn.execute(
        text("SELECT meta->>'page' FROM kb.document WHERE id = :d"), {"d": document_id}
    ).scalar()
    if not page:
        raise LookupError(f"document {document_id} records no page (project init records it)")
    return str(page)


class AgentOpus:
    """`agent.opus`, M24 (module doc)."""

    name = "agent.opus"
    version = VERSION
    family = MethodFamily.AGENT
    unit_type = TaskUnitType.SOURCE_VIEW
    tier = MethodTier.AGENT
    confidence_source: ConfidenceSource | None = ConfidenceSource.AGENT
    Config = AgentOpusConfig
    resources = Resources()

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._packets: dict[tuple[int, str, int, int, bytes], P.Packet] = {}
        self._parts: dict[tuple[int, str, str], dict[str, parts_.Part]] = {}

    # -- select --------------------------------------------------------------------------------

    def select(self, run: SourceRunContext, cfg: AgentOpusConfig) -> Iterable[UnitRef]:
        return tuple(
            UnitRef(TaskUnitType.SOURCE_VIEW, ref.id, ref.key) for ref in run.reader.source_views()
        )

    # -- the packet and the parts --------------------------------------------------------------

    def inputs(self, unit: UnitView, cfg: AgentOpusConfig, golden: bool = False) -> P.UnitInputs:
        if unit.rendition_id is None or unit.ref.unit_key is None:
            raise ValueError(f"{unit.ref}: an agent.opus unit names its rendition and unit key")
        return P.unit_inputs(
            unit.run.reader,
            rendition_id=unit.rendition_id,
            document_id=unit.document_id,
            unit_key=unit.ref.unit_key,
            reference_run_id=unit.run.reference_run_id,
            pack_macros=cfg.math.macro_table(),
            golden=golden,
        )

    def packet(self, unit: UnitView, cfg: AgentOpusConfig) -> P.Packet:
        assert unit.rendition_id is not None and unit.ref.unit_key is not None
        key = (
            unit.run.run_id,
            unit.ref.unit_key,
            unit.rendition_id,
            cfg.packet_cap_chars,
            canonical_json(cfg.math.model_dump(mode="json")),
        )
        with self._lock:
            found = self._packets.get(key)
        if found is None:
            found = self.inputs(unit, cfg).packet(cfg.packet_cap_chars)
            with self._lock:
                self._packets[key] = found
        return found

    def parts(self, run: SourceRunContext, cfg: AgentOpusConfig) -> dict[str, parts_.Part]:
        key = (run.run_id, cfg.reference, cfg.json_schema)
        with self._lock:
            found = self._parts.get(key)
        if found is None:
            reader = run.reader
            found = parts_.build_parts(
                reader.guideline(),
                reader.artifact(cfg.reference),
                cfg.reference,
                reader.artifact(cfg.json_schema),
                cfg.json_schema,
            )
            with self._lock:
                self._parts[key] = found
        return found

    # -- the digest ----------------------------------------------------------------------------

    def digest_inputs(
        self, unit: UnitView, cfg: AgentOpusConfig, packet: P.Packet
    ) -> Mapping[str, Any]:
        found = self.parts(unit.run, cfg)
        hashes = {name: part.hash for name, part in found.items()}
        reuse = unit.run.options.get("agent_reuse", AgentReuse.FULL.value)
        if reuse == AgentReuse.BY_UNIT.value:
            segment = self.inputs(unit, cfg, golden=True).unit[0]
            hashes["guideline"] = "by_unit:" + parts_.by_unit_guideline(
                unit.run.reader.guideline(), segment
            )
        return {
            "packet": packet.hash,
            "parts": hashes,
            "artifacts": {
                "reference": cfg.reference,
                "schema": cfg.json_schema,
                "rules": cfg.rules,
            },
            "model": cfg.model,
        }

    def input_digest(self, unit: UnitView, cfg: AgentOpusConfig) -> Digest:
        if unit.ref.unit_type is TaskUnitType.SOURCE_VIEW:
            from corpus_structure.methods.math.native import native_proposal_packet

            if unit.ref.unit_id is None:
                raise ValueError("native agent task requires a source-view row")
            packet = native_proposal_packet(
                unit.run.reader,
                unit.ref.unit_id,
                unit.run.reader.prepared,
                cfg.model_dump(mode="json"),
            )
            return Digest(canonical_json({"packet": packet.hash, "model": cfg.model}), packet.hash)
        packet = self.packet(unit, cfg)
        return Digest(canonical_json(self.digest_inputs(unit, cfg, packet)), packet.hash)

    def run(
        self, units: Sequence[UnitView], cfg: AgentOpusConfig, ctx: MethodContext
    ) -> Sequence[UnitResult]:
        raise RuntimeError(
            "agent.opus tasks are completed by the session through propose_claims (D4 M24); "
            "no worker runs them"
        )
