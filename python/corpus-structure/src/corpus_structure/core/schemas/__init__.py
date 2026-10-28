"""JSON Schemas of the core shapes (D3 §6; foundations §3.5) and their deterministic generator.

`CoreJsonSchema` is the one generator for core and compiled schemas (S1 reuses it): draft 2020-12
(`$schema` set), no titles, validation mode, output fixed by the models alone. `SCHEMAS` names
every file of this directory; `write()` regenerates them (`python -m corpus_structure.core.schemas`)
and a test fails when a committed file differs. Production validates with Pydantic; these files are
for documentation and external consumers.

jsonschema's agreement with Pydantic over these files is derivation conformance, not an
independent oracle: both come from one model, so a shared mistake passes both (coordinator
decision 24; R12; F02). The independent controls for these shapes are the external S0 and S0-R2
batches (`fixtures/s0`, S1's acceptance), the hand-written expectations and relational key oracles
of the core tests (and F2e's hand-authored conformance vectors), the negative store tests, and tex
parity with the spike's output.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaMode, JsonSchemaValue
from pydantic_core import CoreSchema

DRAFT = "https://json-schema.org/draft/2020-12/schema"
DIRECTORY = Path(__file__).parent


class CoreJsonSchema(GenerateJsonSchema):
    """Draft 2020-12, without titles; deterministic for given models."""

    def field_title_should_be_set(self, schema: Any) -> bool:
        return False

    def generate(self, schema: CoreSchema, mode: JsonSchemaMode = "validation") -> JsonSchemaValue:
        out = _strip_titles(super().generate(schema, mode=mode))
        return {"$schema": DRAFT, **out}


def _strip_titles(node: Any) -> Any:
    if isinstance(node, dict):
        return {
            k: _strip_titles(v)
            for k, v in node.items()
            if not (k == "title" and isinstance(v, str))
        }
    if isinstance(node, list):
        return [_strip_titles(v) for v in node]
    return node


def json_schema(adapter: TypeAdapter[Any]) -> dict[str, Any]:
    return adapter.json_schema(mode="validation", schema_generator=CoreJsonSchema)


def _adapters() -> dict[str, TypeAdapter[Any]]:
    from corpus_structure.core import batch, payloads, values

    out: dict[str, TypeAdapter[Any]] = {
        "value.authored": values.VALUE_ADAPTERS["authored"],
        "value.stored": values.VALUE_ADAPTERS["stored"],
        "condition.authored": values.CONDITION_ADAPTERS["authored"],
        "condition.stored": values.CONDITION_ADAPTERS["stored"],
        "citation_frame": TypeAdapter(batch.CitationFrame),
        "batch.authored": TypeAdapter(batch.AuthoredBatch),
        "batch.stored": TypeAdapter(batch.StoredBatch),
        "mention_ref": TypeAdapter(payloads.MentionRef),
        "cost": TypeAdapter(payloads.Cost),
        "policy_action": TypeAdapter(payloads.PolicyAction),
        "intervention_target": TypeAdapter(payloads.InterventionTarget),
        "trigger_metrics": payloads.TRIGGER_METRICS,
    }
    for kind, model in payloads.PAYLOADS.items():
        out[f"payload.{kind.value}"] = TypeAdapter(model)
    return out


SCHEMAS: Callable[[], dict[str, TypeAdapter[Any]]] = _adapters


def render(adapter: TypeAdapter[Any]) -> str:
    return json.dumps(json_schema(adapter), indent=2, ensure_ascii=False) + "\n"


def write(directory: Path = DIRECTORY) -> list[Path]:
    """Regenerate every schema file; remove files no adapter produces. Returns the files written."""
    written = []
    adapters = SCHEMAS()
    for name, adapter in adapters.items():
        path = directory / f"{name}.json"
        path.write_text(render(adapter), encoding="utf-8")
        written.append(path)
    for stale in directory.glob("*.json"):
        if stale.stem not in adapters:
            stale.unlink()
    return written
