"""Configuration descriptors for release-bound domain operations, never legacy executors."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.core.evidence import MacroDef
from corpus_structure.core.keys import LabelRules
from corpus_structure.core.method import (
    ArtifactRef,
    Digest,
    MethodContext,
    PackSection,
    Resources,
    RunView,
    UnitRef,
    UnitResult,
    UnitView,
)
from corpus_structure.core.vocab import ConfidenceSource, MethodFamily, MethodTier, TaskUnitType

METHOD = "consolidate.claims"
VERSION = "2"


class ConsolidateConfig(BaseModel):
    """`consolidate.claims`'s configuration: the set-step engine, markup hints, and the pack's
    `aliases` (label normalization, D5 §3.3) and `math` (the fallback macro map) sections."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    engine: Literal["duckdb"] = "duckdb"
    use_markup_hints: bool = True
    aliases: Annotated[dict[str, Any], PackSection("aliases")] = Field(default_factory=dict)
    math: Annotated[dict[str, Any], PackSection("math")] = Field(default_factory=dict)

    def labels(self, to_prefixed: Mapping[str, str]) -> LabelRules:
        """The label rules, head words keyed by prefixed class (the pack writes local names)."""
        heads = {
            to_prefixed.get(k, k): tuple(v)
            for k, v in (self.aliases.get("head_words") or {}).items()
        }
        return LabelRules.model_validate({**self.aliases, "head_words": heads})

    def macros(self) -> dict[str, MacroDef]:
        return {
            k: MacroDef(body=v) if isinstance(v, str) else MacroDef.model_validate(v)
            for k, v in (self.math.get("macros") or {}).items()
        }


class ConsolidateMethod:
    """Configuration descriptor; semantic domain operations perform consolidation."""

    name = METHOD
    version = VERSION
    family = MethodFamily.CONSOLIDATE
    unit_type = TaskUnitType.RUN
    tier = MethodTier.DETERMINISTIC
    confidence_source: ConfidenceSource | None = None
    Config = ConsolidateConfig
    resources = Resources()

    def select(self, run: RunView, cfg: ConsolidateConfig) -> Iterable[UnitRef]:
        return [UnitRef(TaskUnitType.RUN)]

    def input_digest(self, unit: UnitView, cfg: ConsolidateConfig) -> Digest:
        return Digest(f"{self.name}|{self.version}".encode())

    def run(
        self, units: Sequence[UnitView], cfg: ConsolidateConfig, ctx: MethodContext
    ) -> Sequence[UnitResult]:
        raise RuntimeError("use semantic.domain_operations.consolidate_cut for publication")


class RulesConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rules: Annotated[str, ArtifactRef("rules", "rules")] = ""


class RulesMethod:
    """Rule configuration; semantic domain operations own validation/publication."""

    name = "validate.rules"
    version = "1"
    family = MethodFamily.VALIDATE
    unit_type = TaskUnitType.RUN
    tier = MethodTier.DETERMINISTIC
    confidence_source: ConfidenceSource | None = ConfidenceSource.RULES
    Config = RulesConfig
    resources = Resources()

    def select(self, run: RunView, cfg: RulesConfig) -> Iterable[UnitRef]:
        return [UnitRef(TaskUnitType.RUN)]

    def input_digest(self, unit: UnitView, cfg: RulesConfig) -> Digest:
        return Digest(f"{self.name}|{self.version}|{cfg.rules}".encode())

    def run(
        self, units: Sequence[UnitView], cfg: RulesConfig, ctx: MethodContext
    ) -> Sequence[UnitResult]:
        raise RuntimeError(
            "validate.rules runs inside consolidation's finalize pass (D4 M19); "
            "no orchestrator worker runs it"
        )
