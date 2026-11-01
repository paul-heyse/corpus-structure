"""JSON Schemas of the core shapes (D3 §6; foundations §3.5) and their deterministic generator.

`CoreJsonSchema` is the one generator for core and compiled schemas (S1 reuses it): draft 2020-12
(`$schema` set), no titles, validation mode, output fixed by the models alone. `SCHEMAS` names
every file of this directory; `write()` regenerates them (`python -m corpus_structure.core.schemas`,
and `just model generate`) and a test fails when a committed file differs. Production validates
with Pydantic; these files are for documentation and external consumers.

**`$id`** (model and projections §3.5; DA-009): every committed schema names the model revision it
was generated under, `https://corpus-structure.dev/schemas/<model revision>/<name>.json`, where the
model revision is the first 12 hex digits of its content hash (`_model.revision.CONTENT_HASH`).
A schema compiled per schema version adds that version's hash as a further segment
(`…/<model revision>/<schema version>/<name>.json`; S1's batch forms). `schema_id` writes both.

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

from pydantic import JsonValue, TypeAdapter
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaMode, JsonSchemaValue
from pydantic_core import CoreSchema

DRAFT = "https://json-schema.org/draft/2020-12/schema"
DIRECTORY = Path(__file__).parent
ID_ROOT = "https://corpus-structure.dev/schemas"


def schema_id(
    name: str, model_revision: str | None = None, schema_version: str | None = None
) -> str:
    """The `$id` of a generated schema (module doc); the revision defaults to the installed one."""
    if model_revision is None:
        from corpus_structure.core._model.revision import CONTENT_HASH

        model_revision = CONTENT_HASH
    segments = [ID_ROOT, model_revision[:12]]
    if schema_version is not None:
        segments.append(schema_version[:12])
    return "/".join([*segments, f"{name}.json"])


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
    from corpus_structure.core import batch, options, payloads, values

    out: dict[str, TypeAdapter[Any]] = {
        "value.authored": values.VALUE_ADAPTERS["authored"],
        "value.stored": values.VALUE_ADAPTERS["stored"],
        "condition.authored": values.CONDITION_ADAPTERS["authored"],
        "condition.stored": values.CONDITION_ADAPTERS["stored"],
        "citation_frame": TypeAdapter(batch.CitationFrame),
        "golden_batch": TypeAdapter(payloads.GoldenBatchPayload),
        "batch.authored": TypeAdapter(batch.AuthoredBatch),
        "batch.stored": TypeAdapter(batch.StoredBatch),
        "mention_ref": TypeAdapter(payloads.MentionRef),
        "cost": TypeAdapter(payloads.Cost),
        "policy_action": TypeAdapter(payloads.PolicyAction),
        "intervention_target": TypeAdapter(payloads.InterventionTarget),
        "trigger_metrics": payloads.TRIGGER_METRICS,
        "compiled_artifact": TypeAdapter(JsonValue),  # a compiled artifact's body: any JSON
        "run_options": TypeAdapter(options.RunOptions),
        "intervention_refs": TypeAdapter(payloads.InterventionRefs),
    }
    for kind, model in payloads.PAYLOADS.items():
        out[f"payload.{kind.value}"] = TypeAdapter(model)
    return out


SCHEMAS: Callable[[], dict[str, TypeAdapter[Any]]] = _adapters


def render(name: str, adapter: TypeAdapter[Any], model_revision: str | None = None) -> str:
    """A committed schema file's text: the schema with its `$id` after `$schema`."""
    out = json_schema(adapter)
    out = {"$schema": out.pop("$schema"), "$id": schema_id(name, model_revision), **out}
    return json.dumps(out, indent=2, ensure_ascii=False) + "\n"


def write(directory: Path = DIRECTORY, model_revision: str | None = None) -> list[Path]:
    """Regenerate every schema file; remove files no adapter produces. Returns the files written."""
    written = []
    adapters = SCHEMAS()
    for name, adapter in adapters.items():
        path = directory / f"{name}.json"
        path.write_text(render(name, adapter, model_revision), encoding="utf-8")
        written.append(path)
    for stale in directory.glob("*.json"):
        if stale.stem not in adapters:
            stale.unlink()
    return written
