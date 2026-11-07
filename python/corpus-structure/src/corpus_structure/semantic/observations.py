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
from .metrics import validate_measurement
from .types import PreparedRelease, SourceArtifact, SourceBundle

_MODEL = Path(__file__).resolve().parents[1] / "model" / "semantic" / "observations.yaml"


def observation_inputs(bundle: SourceBundle, *, model_content: bytes | None = None) -> SourceBundle:
    """Include the source-report module through archived, hashed release preparation."""
    names = {source.name for source in bundle.sources}
    content = _MODEL.read_bytes() if model_content is None else model_content
    if names & {"observations", "observation-root"}:
        from .prepare import _view

        module = next((source for source in bundle.sources if source.name == "observations"), None)
        if (
            module is not None
            and module.content == content
            and "SourceObservation" in _view(bundle).all_classes()
        ):
            return bundle
        raise ValueError("reserved observation module name already supplied with another meaning")
    return SourceBundle(
        "observation-root",
        (
            *bundle.sources,
            SourceArtifact("observations", content),
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


def prepare_source_inputs(
    bundle: SourceBundle,
    dependencies=None,
    *,
    metric_content: bytes | None = None,
    model_content: bytes | None = None,
):
    """Explicitly acquire source-report schema and metric definitions before pure preparation."""
    from .metrics import observation_dependencies
    from .types import ResolvedDependencies

    return (
        observation_inputs(bundle, model_content=model_content),
        observation_dependencies(
            ResolvedDependencies() if dependencies is None else dependencies, metric_content
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
    invocation_key: str,
    result: UnitResult,
    method_confidence_source: str | None = None,
    coverage: Sequence[Mapping[str, str]] = (),
    records: Sequence[Mapping[str, Any]] | None = None,
    record_coordinate_texts: Sequence[Mapping[str, Any]] = (),
    contribution_coordinate_texts: Sequence[Mapping[str, Any]] = (),
) -> BaseModel:
    """Validate a recognizer's terminal product under its run's release.

    Item ordinals are inside the stable input, never database task/attempt identities. Equal
    reports at two positions stay separate; replaying a terminal product gives the same keys.
    The operational repository still fences and persists this product atomically with the task.
    Base-schema construction remains pure; every current effect owner separately requires the
    composed execution binding and its method dimensions before publication.
    """
    from .operation_results import validate_method_dimension

    if prepared.execution_model_id is not None:
        validate_method_dimension(prepared, method, "result.outcome", result.outcome.value)
    unit_key = result.ref.unit_key
    if not all(
        (
            source,
            method,
            operation_version,
            configuration_hash,
            input_hash,
            invocation_key,
            unit_key,
        )
    ):
        raise ValueError("a source report requires complete source, unit and operation identity")
    observations = []
    for ordinal, draft in enumerate(result.observations):
        item_key = f"{draft.kind!s}/{ordinal}"
        identity = [
            prepared.release_id,
            source,
            method,
            operation_version,
            configuration_hash,
            input_hash,
            invocation_key,
            unit_key,
            item_key,
        ]
        row: dict[str, Any] = {
            "observation_key": "observation:" + sha256(canonical_bytes(identity)).hexdigest(),
            "item_key": item_key,
            "family": draft.kind,
            "payload": source_value(
                draft.payload.model_dump(mode="json", by_alias=True, serialize_as_any=True)
            ),
        }
        if draft.input_refs:
            row["inputs"] = tuple(
                {"observation_key": ref.observation_key, "role": ref.role}
                for ref in draft.input_refs
            )
        row["outcome"] = draft.outcome
        if draft.score is not None:
            row["score"] = source_value(draft.score)
        confidence = (
            method_confidence_source
            if draft.confidence_source is METHOD_SOURCE
            else draft.confidence_source
        )
        if confidence is not None:
            row["confidence_source"] = confidence
        if draft.rendition_id is not None:
            row["rendition_id"] = draft.rendition_id
        if draft.segment_id is not None:
            row["segment_id"] = draft.segment_id
        if draft.span is not None:
            row["span_start"], row["span_end"] = draft.span
        if draft.source_view_id is not None:
            if (
                draft.rendition_id is not None
                or draft.segment_id is not None
                or draft.span is not None
            ):
                raise ValueError("native observation cannot alias rendition coordinates")
            row["source_view_id"] = draft.source_view_id
            if draft.native_pointer is not None:
                row["native_pointer"] = draft.native_pointer
            if draft.projected_span is not None:
                row["projected_start"], row["projected_end"] = draft.projected_span
            if draft.recognized_span is not None:
                row["recognized_start"], row["recognized_end"] = draft.recognized_span
        if prepared.execution_model_id is not None:
            validate_method_dimension(prepared, method, "observation.family", row["family"])
            validate_method_dimension(prepared, method, "observation.outcome", row["outcome"])
            validate_method_dimension(
                prepared, method, "observation.confidence_source", row.get("confidence_source")
            )
        observations.append(row)
    payload: dict[str, object] = {
        "release_id": prepared.release_id,
        "invocation_key": invocation_key,
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
                    **(
                        {"required_capability": item.required_capability}
                        if item.required_capability is not None
                        else {}
                    ),
                }
                for item in result.coverage
            ),
            *(dict(item) for item in coverage),
        ),
    }
    if records is not None:
        from .record_contracts import bind_record_candidates

        if records and result.outcome.value != "produced":
            raise ValueError("record candidates require a produced source report")
        payload["records"] = tuple(
            record.model_dump(mode="python")
            for record in bind_record_candidates(
                prepared,
                source=source,
                records=records,
                coordinate_texts=record_coordinate_texts,
            )
        )
    if result.contributions is not None or result.contribution_operations is not None:
        from .contributions import bind_contributions

        if result.contribution_operations is None or result.contributions is None:
            raise ValueError(
                "contribution population and product presence must be explicit together"
            )
        operations, contributions = bind_contributions(
            prepared,
            source=source,
            operations=result.contribution_operations,
            contributions=result.contributions,
            coordinate_texts=contribution_coordinate_texts or result.contribution_coordinate_texts,
        )
        payload["contribution_operations"] = operations
        payload["contributions"] = contributions
    if result.structural_product is not None:
        if result.ref.unit_type.value != "run" or result.outcome.value != "produced":
            raise ValueError("structural products require a produced RUN result")
        from .structural_products import StructuralProductReport

        structural = StructuralProductReport.model_validate(result.structural_product).model_dump(
            mode="python", exclude_none=True
        )
        if "retrieval_report" in structural:
            structural["retrieval_report"] = prepared.validate_json(
                "ContextualEnrichmentReport", canonical_bytes(structural["retrieval_report"])
            ).model_dump(mode="python")
        if "artifact_identity" in structural:
            for record in structural["artifact_identity"]["records"]:
                record["source_contribution"] = prepared.validate_json(
                    "SourceContribution", canonical_bytes(record["source_contribution"])
                ).model_dump(mode="python", exclude_none=True)
        if "comparison" in structural:
            for dimension in structural["comparison"]["dimensions"]:
                for side in ("left_group", "right_group"):
                    for member in dimension.get(side, {}).get("members", ()):
                        if "condition" in member:
                            member["condition"] = source_value(source_python(member["condition"]))
        payload["structural_product"] = structural
    for measurement in result.measurements:
        validate_measurement(prepared, measurement)
    payload["measurements"] = tuple(
        {
            "metric": item.metric,
            "scope_type": str(item.scope_type),
            **({"scope_id": item.scope_id} if item.scope_id is not None else {}),
            **({"scope_key": item.scope_key} if item.scope_key is not None else {}),
            "value": source_value(item.value),
            "detail": source_value(item.detail),
        }
        for item in result.measurements
    )
    if result.error is not None:
        payload["error"] = result.error
    if result.cost is not None:
        payload["cost"] = source_value(result.cost.model_dump(mode="json"))
    if result.parse_detail is not None:
        payload["parse_detail"] = source_value(result.parse_detail)
    # The absence of this declared operation module is an error, never installed-model fallback.
    return prepared.validate_python("SourceObservationBatch", payload)
