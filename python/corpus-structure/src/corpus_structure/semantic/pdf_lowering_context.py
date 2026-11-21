"""Immutable record schemas and producer policy acquired from one PDF domain."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pyarrow as pa


@dataclass(frozen=True, slots=True)
class CapturedPdfLowering:
    encoded_schemas: tuple[tuple[str, bytes], ...]
    artifact_profiles: tuple[tuple[str, str], ...]
    max_batch_bytes: int
    max_batch_rows: int
    schemas: tuple[tuple[str, pa.Schema], ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        names = [name for name, _ in self.encoded_schemas]
        if len(set(names)) != len(names) or not names:
            raise ValueError("captured PDF lowering requires unique record schemas")
        limits = (self.max_batch_bytes, self.max_batch_rows)
        if any(type(limit) is not int or limit < 1 for limit in limits):
            raise ValueError("captured PDF lowering requires positive batch limits")
        profiles = [name for name, _ in self.artifact_profiles]
        if len(set(profiles)) != len(profiles) or any(
            not isinstance(value, str) or not value for _, value in self.artifact_profiles
        ):
            raise ValueError("captured PDF lowering requires unique artifact profiles")
        object.__setattr__(
            self,
            "schemas",
            tuple(
                (name, pa.ipc.read_schema(pa.BufferReader(content)))
                for name, content in self.encoded_schemas
            ),
        )

    def schema(self, name: str) -> pa.Schema:
        for candidate, schema in self.schemas:
            if candidate == name:
                return schema
        raise ValueError("captured PDF lowering lacks record schema: " + name)

    def artifact_profile(self, name: str) -> str:
        for candidate, profile in self.artifact_profiles:
            if candidate == name:
                return profile
        raise ValueError("captured PDF lowering lacks artifact profile: " + name)

    def document(self) -> dict[str, Any]:
        return {
            "profile": "captured-pdf-lowering-v1",
            "schemas": {name: content.hex() for name, content in self.encoded_schemas},
            "artifact_profiles": dict(self.artifact_profiles),
            "max_batch_bytes": self.max_batch_bytes,
            "max_batch_rows": self.max_batch_rows,
        }

    @classmethod
    def from_document(cls, document: Any) -> CapturedPdfLowering:
        fields = {"profile", "schemas", "artifact_profiles", "max_batch_bytes", "max_batch_rows"}
        if (
            not isinstance(document, dict)
            or set(document) != fields
            or document["profile"] != "captured-pdf-lowering-v1"
        ):
            raise ValueError("unsupported captured PDF lowering contract")
        return cls(
            tuple(
                (name, bytes.fromhex(content))
                for name, content in sorted(document["schemas"].items())
            ),
            tuple(sorted(document["artifact_profiles"].items())),
            document["max_batch_bytes"],
            document["max_batch_rows"],
        )


def capture_pdf_lowering(context) -> CapturedPdfLowering:
    """Project already archived schemas and staging policy, without rebuilding metadata."""
    import yaml

    from .pdf_publication import COMPANION_STAGE_TARGETS
    from .pdf_staging import UPLOAD_STAGE_FAMILIES

    annotations = yaml.safe_load(context.staging.content)["annotations"]
    upload = json.loads(annotations["pds:upload_profile"])
    families = {
        **{"stage:" + family: target for family, target in UPLOAD_STAGE_FAMILIES.items()},
        **{"companion:" + family: target for family, target in COMPANION_STAGE_TARGETS.items()},
    }
    return CapturedPdfLowering(
        tuple(
            (
                family,
                context.domain.source(
                    "implementation/pdf/lowering/codec/" + target + ".arrow"
                ).content,
            )
            for family, target in sorted(families.items())
        ),
        tuple(sorted(json.loads(annotations["pds:artifact_profiles"]).items())),
        upload["max_bytes"],
        upload["max_rows"],
    )
