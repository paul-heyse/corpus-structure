"""Release-bound source reports, kept distinct from admitted domain knowledge.

Pure recognizers may return their own typed models. This boundary preserves their complete
source report while binding it to immutable semantic inputs. It does not promote a successful
read or an observation into a selected fact, and is not the model-facing agent proposal schema.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from corpus_structure.core.method import METHOD_SOURCE, UnitResult

from .identity import canonical_bytes
from .types import PreparedRelease, SourceArtifact, SourceBundle

_MODEL = Path(__file__).resolve().parents[1] / "model" / "semantic" / "observations.yaml"


def observation_inputs(bundle: SourceBundle) -> SourceBundle:
    """Include the source-report module through archived, hashed release preparation."""
    names = {source.name for source in bundle.sources}
    if names & {"observations", "observation-root"}:
        raise ValueError("reserved observation module name already supplied")
    return SourceBundle(
        "observation-root",
        (
            *bundle.sources,
            SourceArtifact("observations", _MODEL.read_bytes()),
            SourceArtifact(
                "observation-root",
                yaml.safe_dump(
                    {
                        "id": "https://corpus-structure.dev/semantic/observation-root",
                        "name": "semantic_observation_root",
                        "imports": [bundle.root, "observations"],
                    }
                ).encode(),
            ),
        ),
    )


def source_value(value: Any) -> dict[str, Any]:
    """Losslessly represent JSON source products with explicit scalar and container kinds."""
    if value is None:
        return {"kind": "null"}
    if type(value) is bool:
        return {"kind": "boolean", "boolean": value}
    if type(value) is int:
        return {"kind": "integer", "integer": value}
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("source report contains a nonfinite number")
        return {"kind": "float", "hexadecimal": value.hex()}
    if type(value) is str:
        return {"kind": "text", "text": value}
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise TypeError("source report object keys must be strings")
        return {
            "kind": "object",
            "fields": tuple(
                {"name": key, "position": position, "value": source_value(item)}
                for position, (key, item) in enumerate(value.items())
            ),
        }
    if isinstance(value, (tuple, list)):
        return {"kind": "array", "items": tuple(source_value(item) for item in value)}
    raise TypeError(f"unsupported source report value {type(value).__name__}")


def source_python(value: Mapping[str, Any]) -> Any:
    """Decode a validated source value without conflating null, absence or false."""
    kind = value["kind"]
    if kind == "null":
        return None
    if kind == "boolean":
        return value["boolean"]
    if kind == "integer":
        return value["integer"]
    if kind == "float":
        result = float.fromhex(value["hexadecimal"])
        if not math.isfinite(result):
            raise ValueError("source report contains a nonfinite number")
        return result
    if kind == "text":
        return value["text"]
    if kind == "array":
        return [source_python(item) for item in value.get("items", ())]
    if kind == "object":
        fields = value.get("fields", ())
        if [field["position"] for field in fields] != list(range(len(fields))):
            raise ValueError("source report fields are not contiguous and ordered")
        names = [field["name"] for field in fields]
        if len(names) != len(set(names)):
            raise ValueError("source report contains a repeated field name")
        return {field["name"]: source_python(field["value"]) for field in fields}
    raise ValueError(f"unknown source report kind {kind}")


def bind_result(
    prepared: PreparedRelease,
    *,
    source: str,
    method: str,
    operation_version: str,
    configuration_hash: str,
    input_hash: str,
    result: UnitResult,
    method_confidence_source: str | None = None,
    coverage: Sequence[Mapping[str, str]] = (),
) -> BaseModel:
    """Validate a recognizer's terminal product under its run's release.

    Item ordinals are inside the stable input, never database task/attempt identities. Equal
    reports at two positions stay separate; replaying a terminal product gives the same keys.
    The operational repository still fences and persists this product atomically with the task.
    """
    unit_key = result.ref.unit_key
    if not all((source, method, operation_version, configuration_hash, input_hash, unit_key)):
        raise ValueError("a source report requires complete source, unit and operation identity")
    observations = []
    for ordinal, draft in enumerate(result.observations):
        item_key = f"{draft.kind.value}/{ordinal}"
        identity = [
            prepared.release_id,
            source,
            method,
            operation_version,
            configuration_hash,
            input_hash,
            unit_key,
            item_key,
        ]
        row: dict[str, Any] = {
            "observation_key": "observation:" + sha256(canonical_bytes(identity)).hexdigest(),
            "item_key": item_key,
            "family": draft.kind.value,
            "payload": source_value(
                draft.payload.model_dump(mode="json", by_alias=True, serialize_as_any=True)
            ),
        }
        row["outcome"] = draft.outcome.value
        if draft.score is not None:
            row["score"] = source_value(draft.score)
        confidence = (
            method_confidence_source
            if draft.confidence_source is METHOD_SOURCE
            else draft.confidence_source
        )
        if confidence is not None:
            row["confidence_source"] = str(confidence)
        if draft.rendition_id is not None:
            row["rendition_id"] = draft.rendition_id
        if draft.segment_id is not None:
            row["segment_id"] = draft.segment_id
        if draft.span is not None:
            row["span_start"], row["span_end"] = draft.span
        observations.append(row)
    payload: dict[str, object] = {
        "release_id": prepared.release_id,
        "source": source,
        "method": method,
        "operation_version": operation_version,
        "configuration_hash": configuration_hash,
        "input_hash": input_hash,
        "unit_key": unit_key,
        "outcome": result.outcome.value,
        "observations": tuple(observations),
        "coverage": (
            *(
                {
                    "family": item.family,
                    "scope": item.scope,
                    "outcome": item.outcome,
                    **({"reason": item.reason} if item.reason is not None else {}),
                }
                for item in result.coverage
            ),
            *(dict(item) for item in coverage),
        ),
    }
    if result.error is not None:
        payload["error"] = result.error
    if result.cost is not None:
        payload["cost"] = source_value(result.cost.model_dump(mode="json"))
    if result.parse_detail is not None:
        payload["parse_detail"] = source_value(result.parse_detail)
    # The absence of this declared operation module is an error, never installed-model fallback.
    return prepared.validate_python("SourceObservationBatch", payload)
