"""Typed framing of a detached export around its separately owned native cut."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, ValidationInfo, model_validator

from corpus_structure.semantic.data_operation_json import (
    decode_retained_json_members,
    json_bytes,
)

if TYPE_CHECKING:
    from corpus_structure.semantic.demand_results import CutSelection

_Digest = Annotated[str, Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")]
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
    _cut: CutSelection = PrivateAttr()
    _snapshot: dict[str, Any] = PrivateAttr()
    _content: bytes | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def check_references(self, info: ValidationInfo):
        from corpus_structure.semantic.demand_results import CutSelection

        selected = (info.context or {}).get("cut_selection")
        if selected is None:
            selected = CutSelection(json_bytes(self.cut))
        if not isinstance(selected, CutSelection):
            raise ValueError("detached manifest requires its exact cut selection")
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
        self.cut = selected.record
        self._cut = selected
        self._snapshot = self.model_dump(mode="python")
        return self

    @property
    def cut_selection(self) -> CutSelection:
        """Return the original cut owner whose immutable bytes establish cut_id."""
        return self._cut

    def to_bytes(self) -> bytes:
        """Emit authenticated v3 framing with the exact embedded cut bytes."""
        from corpus_structure.semantic.demand_wire import _same_json_material

        view = self.model_dump(mode="python")
        if not _same_json_material(view, self._snapshot):
            raise ValueError("detached manifest changed after validation")
        if self._content is not None:
            return self._content
        return (
            b"{"
            + b",".join(
                json_bytes(name)
                + b":"
                + (self._cut.content if name == "cut" else json_bytes(view[name]))
                for name in sorted(view)
            )
            + b"}"
        )


@dataclass(frozen=True)
class PublishedDemandExport:
    manifest: DemandExportManifest
    manifest_digest: str

    def report(self) -> dict[str, Any]:
        return {
            **self.manifest.model_dump(mode="python"),
            "manifest_digest": self.manifest_digest,
        }


def checked_export_manifest(
    value: dict[str, Any], *, cut: CutSelection | None = None
) -> DemandExportManifest:
    """Validate metadata without projecting contextual pins onto presentation numbers."""
    if cut is None:
        return DemandExportManifest.model_validate(value)
    if "cut" in value:
        raise ValueError("supply the exact cut separately from manifest metadata")
    return DemandExportManifest.model_validate(
        {**value, "cut": cut.record}, context={"cut_selection": cut}
    )


def decode_export_manifest(content: bytes) -> DemandExportManifest:
    """Decode strict JSON framing and preserve the native cut's existing numeric contract."""
    from corpus_structure.semantic.demand_results import CutSelection

    parsed, members = decode_retained_json_members(content, ("cut",))
    cut = CutSelection(members["cut"])
    result = DemandExportManifest.model_validate(parsed, context={"cut_selection": cut})
    result._content = content
    return result
