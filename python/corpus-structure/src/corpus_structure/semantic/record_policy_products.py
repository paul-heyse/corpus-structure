"""Released LinkML policy products; internal numerical DTOs confer no DB authority."""

from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path
from typing import Any

from .identity import canonical_bytes
from .record_policy import RecordAcceptanceInstance
from .types import PreparedRelease, SourceArtifact, SourceBundle


def record_policy_inputs(
    bundle: SourceBundle, *, model_content: bytes | None = None
) -> SourceBundle:
    content = (
        (Path(__file__).resolve().parents[1] / "model/semantic/record-policy.yaml").read_bytes()
        if model_content is None
        else model_content
    )
    if any(s.name in {"record_policy", "record-policy-root"} for s in bundle.sources):
        raise ValueError("record policy module already supplied")
    root = canonical_bytes(
        dict(
            id="https://corpus-structure.dev/semantic/record-policy-root",
            name="record_policy_root",
            imports=[bundle.root, "record_policy"],
        )
    )
    return SourceBundle(
        "record-policy-root",
        (
            *bundle.sources,
            SourceArtifact("record_policy", content),
            SourceArtifact("record-policy-root", root),
        ),
    )


def _without_nulls(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _without_nulls(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_without_nulls(v) for v in value]
    return value


def validate_record_policy_binding(
    prepared: PreparedRelease, binding: Mapping[str, Any]
) -> RecordAcceptanceInstance:
    """Validate released shape, canonical byte custody and numerical consistency.

    Protected evaluation authority is independently enforced by the native publication
    boundary. A structurally valid binding alone never grants acceptance.
    """
    required = {
        "instance",
        "instance_digest",
        "instance_canonical_json",
        "evaluation_id",
        "evaluation_digest",
    }
    if set(binding) != required:
        raise ValueError("record policy binding requires exact released members")
    prepared.validate_json("RecordPolicyBinding", canonical_bytes(_without_nulls(dict(binding))))
    serialized = binding["instance_canonical_json"]
    if not isinstance(serialized, str):
        raise ValueError("instance canonical JSON must be text")
    content = serialized.encode()
    decoded = json.loads(serialized)
    if decoded != binding["instance"] or canonical_bytes(decoded) != content:
        raise ValueError("instance canonical bytes differ from typed body")
    if sha256(content).hexdigest() != binding["instance_digest"]:
        raise ValueError("instance digest differs from canonical bytes")
    instance = RecordAcceptanceInstance.model_validate_json(content)
    prepared.validate_json("RecordAcceptanceInstance", canonical_bytes(_without_nulls(decoded)))
    if (
        instance.digest != binding["instance_digest"]
        or instance.feature.applicability.release_id != prepared.release_id
    ):
        raise ValueError("instance differs from frozen parameters or release")
    return instance
