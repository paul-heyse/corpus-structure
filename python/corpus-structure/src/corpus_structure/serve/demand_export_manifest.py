"""Typed framing of a detached export around its separately owned native cut."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus_structure.semantic.data_operation_json import (
    json_bytes,
    native_json_loads,
    own_wire_json_value,
)

_Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
_Count = Annotated[int, Field(ge=0)]


class _ManifestRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ExportFile(_ManifestRecord):
    sha256: _Digest
    bytes: _Count


class ExportRelation(_ManifestRecord):
    file: str
    rows: _Count


class DemandExportManifest(_ManifestRecord):
    format: Literal["demand-result-export-v3"]
    encoding: Literal["jsonl", "parquet"]
    cut_id: str
    cut: dict[str, Any]
    pages: list[str]
    closure: str
    reader_contract: str
    authority_contract: str
    execution_evidence_contract: str
    support_disclosure: Literal["bounded", "complete"]
    execution_evidence_disclosure: Literal["bounded", "complete"]
    releases: dict[str, str]
    runtimes: list[str]
    source_artifacts: dict[str, str]
    relations: dict[str, ExportRelation]
    files: dict[str, ExportFile]
    trust: Literal["selected historical acquisition; current trust requires native reassessment"]

    @model_validator(mode="after")
    def check_references(self):
        from corpus_structure.semantic.demand_results import CutSelection

        selected = CutSelection(json_bytes(self.cut))
        if selected.identity != self.cut_id:
            raise ValueError("detached manifest cut identity differs from its native pins")
        for path in self.files:
            name = PurePosixPath(path)
            if not path or name.is_absolute() or ".." in name.parts or "\\" in path:
                raise ValueError("detached manifest requires relative export file names")
        references = [
            *self.pages,
            self.closure,
            self.reader_contract,
            self.authority_contract,
            self.execution_evidence_contract,
            *self.releases.values(),
            *self.runtimes,
            *self.source_artifacts.values(),
            *(relation.file for relation in self.relations.values()),
        ]
        if any(name not in self.files for name in references):
            raise ValueError("detached manifest references a file absent from its inventory")
        return self


@dataclass(frozen=True)
class PublishedDemandExport:
    manifest: DemandExportManifest
    manifest_digest: str

    def report(self) -> dict[str, Any]:
        return {
            **self.manifest.model_dump(mode="python"),
            "manifest_digest": self.manifest_digest,
        }


def checked_export_manifest(value: dict[str, Any]) -> DemandExportManifest:
    """Validate metadata without projecting contextual pins onto presentation numbers."""
    return DemandExportManifest.model_validate(value)


def decode_export_manifest(content: bytes) -> DemandExportManifest:
    """Decode strict JSON framing and preserve the native cut's existing numeric contract."""
    parsed = native_json_loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("detached manifest must be a JSON object")
    if "cut" in parsed:
        # The cut has its own contextual numeric contract. All framing fields below
        # are validated strictly and cannot infer semantics from nested key names.
        parsed["cut"] = own_wire_json_value(parsed["cut"])
    return checked_export_manifest(parsed)
