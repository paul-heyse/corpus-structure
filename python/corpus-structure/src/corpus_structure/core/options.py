"""A run's options as stored (orchestration §3.4; D6 §2, §4, §5, §8; coordinator decision 26).

`RunOptions` is generated from the `system` model's class of the same name (`_model/shapes.py`,
Stage B) and re-exported here: a frozen plain `BaseModel`, never a `BaseSettings`, so reading a
stored run's options never consults the environment (DP-24). Every option is stored resolved:
`ops.run.options` has no field that means "the current setting". `scope` alone may be absent
(`MISSING`, or a stored null), for a run over its whole corpus (P0-O-2 resolves slices);
`agent_reuse` and `gpu_mode` default to the model's `ifabsent`.
"""

from __future__ import annotations

from corpus_structure.core._model.shapes import RunOptions

__all__ = ["RunOptions"]
