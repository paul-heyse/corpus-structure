"""A run's options as stored (orchestration §3.4; D6 §2, §4, §5, §8; coordinator decision 26).

`RunOptions` is the `system` model's class of the same name: a frozen plain `BaseModel`, never a
`BaseSettings`, so reading a stored run's options never consults the environment (DP-24). Every
option is stored resolved: `ops.run.options` has no field that means "the current setting".
`scope` alone may be absent, for a run over its whole corpus (P0-O-2 resolves slices).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from corpus_structure.core.vocab import AgentMode, AgentReuse, GpuMode


class RunOptions(BaseModel):
    """The run's resolved options (module doc)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    agent_mode: AgentMode
    agent_reuse: AgentReuse = AgentReuse.FULL
    gpu_mode: GpuMode = GpuMode.AUTO
    corpus: JsonValue
    scope: JsonValue = None
    fresh: tuple[str, ...] = ()
    configs: dict[str, str] = Field(default_factory=dict)  # "<method>/<name>" -> config hash
    method_configs: dict[str, str] = Field(default_factory=dict)  # method -> configuration name
