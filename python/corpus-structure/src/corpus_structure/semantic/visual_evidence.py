"""Current unselected visual observations, mappings and their original-frame candidates."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    JsonValue,
    model_validator,
)

MAX_VISUAL_EVIDENCE_BYTES = 8 * 1024 * 1024
MAX_VISUAL_EVIDENCE_ROWS = 10_000


class _VisualModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class VisualEvidencePin(_VisualModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    use_id: str = Field(min_length=1)
    product_id: str = Field(min_length=1)
    derivation_id: str = Field(min_length=1)


class VisualSourceRegion(_VisualModel):
    """A coarse region in the original page's top-left PDF point frame."""

    left: FiniteFloat = Field(ge=0)
    top: FiniteFloat = Field(ge=0)
    right: FiniteFloat = Field(gt=0)
    bottom: FiniteFloat = Field(gt=0)
    precision: Literal["coarse"] = "coarse"
    address_space: Literal["pdf_points"] = "pdf_points"
    origin: Literal["top_left"] = "top_left"
    enclosing_occurrence_id: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def ordered(self):
        if self.left >= self.right or self.top >= self.bottom:
            raise ValueError("visual source region requires positive area")
        return self


class _VisualOccurrence(_VisualModel):
    occurrence_id: str = Field(min_length=1)
    provider_locator: str | None = Field(default=None, min_length=1)
    parent_occurrence_id: str | None = Field(default=None, min_length=1)
    source_region: VisualSourceRegion | None = None


class VisualPicture(_VisualOccurrence):
    kind: Literal["picture"] = "picture"
    metadata: dict[str, JsonValue] | None = None


class VisualCaption(_VisualOccurrence):
    """A transcription candidate with the parser's attachment."""

    kind: Literal["caption"] = "caption"
    parent_occurrence_id: str = Field(min_length=1)
    text: str
    parser_attachment_occurrence_ids: tuple[str, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )


class VisualCaptionCandidate(_VisualOccurrence):
    """A detached transcription candidate with optional source-qualified associations."""

    kind: Literal["caption_candidate"] = "caption_candidate"
    parent_occurrence_id: None = None
    text: str
    associated_picture_occurrence_ids: tuple[str, ...] = ()
    parser_attachment_occurrence_ids: tuple[str, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )


class VisualText(_VisualOccurrence):
    kind: Literal["picture_description", "picture_text", "formula", "mermaid", "cell_text"]
    text: str
    native_label: str | None = Field(default=None, exclude_if=lambda value: value is None)
    original_text: str | None = Field(default=None, exclude_if=lambda value: value is None)


class VisualCellGroup(_VisualOccurrence):
    kind: Literal["cell_group"] = "cell_group"
    parent_occurrence_id: str = Field(min_length=1)
    native_label: str


class VisualTableCell(_VisualModel):
    text: str
    start_row_offset_idx: int = Field(ge=0)
    end_row_offset_idx: int = Field(gt=0)
    start_col_offset_idx: int = Field(ge=0)
    end_col_offset_idx: int = Field(gt=0)
    column_header: bool = False
    row_header: bool = False
    content_occurrence_id: str | None = Field(
        default=None, min_length=1, exclude_if=lambda value: value is None
    )
    column_header_path: tuple[int, ...] = Field(default=(), exclude_if=lambda value: not value)
    row_header_path: tuple[int, ...] = Field(default=(), exclude_if=lambda value: not value)

    @model_validator(mode="after")
    def ordered(self):
        if (
            self.start_row_offset_idx >= self.end_row_offset_idx
            or self.start_col_offset_idx >= self.end_col_offset_idx
        ):
            raise ValueError("visual table cell requires positive spans")
        return self


class VisualTable(_VisualOccurrence):
    kind: Literal["table"] = "table"
    cells: tuple[VisualTableCell, ...]
    num_rows: int = Field(ge=0)
    num_cols: int = Field(ge=0)

    @model_validator(mode="after")
    def cells_in_table(self):
        if any(
            cell.end_row_offset_idx > self.num_rows or cell.end_col_offset_idx > self.num_cols
            for cell in self.cells
        ):
            raise ValueError("visual table cell exceeds table dimensions")
        for cell in self.cells:
            for path, axis in (
                (cell.column_header_path, "column_header"),
                (cell.row_header_path, "row_header"),
            ):
                if len(path) != len(set(path)) or any(
                    index < 0 or index >= len(self.cells) or not getattr(self.cells[index], axis)
                    for index in path
                ):
                    raise ValueError("visual header paths require distinct header cell indices")
        return self


VisualEvidenceRow = Annotated[
    VisualPicture
    | VisualCaption
    | VisualCaptionCandidate
    | VisualText
    | VisualTable
    | VisualCellGroup,
    Field(discriminator="kind"),
]

VisualEvidenceKind = Literal[
    "picture",
    "caption",
    "caption_candidate",
    "picture_description",
    "picture_text",
    "formula",
    "mermaid",
    "table",
    "cell_group",
    "cell_text",
]


class VisualEvidenceArtifact(_VisualModel):
    """One submitted page/crop. Row identities preserve distinct repeated occurrences."""

    version: Literal[1] = 1
    page_no: int = Field(gt=0)
    rows: tuple[VisualEvidenceRow, ...] = Field(max_length=MAX_VISUAL_EVIDENCE_ROWS)

    @model_validator(mode="after")
    def validate_occurrences(self):
        seen: dict[str, VisualEvidenceRow] = {}
        if self.row_count > MAX_VISUAL_EVIDENCE_ROWS:
            raise ValueError("visual evidence exceeds its aggregate occurrence/cell bound")
        for row in self.rows:
            if row.occurrence_id in seen:
                raise ValueError("visual evidence has duplicate occurrence identity")
            if row.parent_occurrence_id is not None and row.parent_occurrence_id not in seen:
                raise ValueError("visual evidence requires its parent before each child")
            region = row.source_region
            if region is not None and region.enclosing_occurrence_id is not None:
                parent = seen.get(row.parent_occurrence_id or "")
                parent_region = parent.source_region if parent is not None else None
                if (
                    parent is None
                    or parent_region is None
                    or region.enclosing_occurrence_id
                    != (parent_region.enclosing_occurrence_id or parent.occurrence_id)
                    or (region.left, region.top, region.right, region.bottom)
                    != (
                        parent_region.left,
                        parent_region.top,
                        parent_region.right,
                        parent_region.bottom,
                    )
                ):
                    raise ValueError("visual evidence inherits only its parent's qualified region")
            seen[row.occurrence_id] = row
        for row in self.rows:
            if isinstance(row, VisualTable):
                for cell in row.cells:
                    if cell.content_occurrence_id is None:
                        continue
                    group = seen.get(cell.content_occurrence_id)
                    if not isinstance(group, VisualCellGroup) or (
                        group.parent_occurrence_id != row.occurrence_id
                    ):
                        raise ValueError("rich visual cells require their exact table-owned group")
            if isinstance(row, (VisualCaption, VisualCaptionCandidate)):
                attachments = row.parser_attachment_occurrence_ids
                if len(attachments) != len(set(attachments)) or any(
                    not isinstance(seen.get(target), (VisualPicture, VisualTable))
                    for target in attachments
                ):
                    raise ValueError("parser attachments require distinct picture or table targets")
            if isinstance(row, VisualCaptionCandidate) and row.associated_picture_occurrence_ids:
                targets = row.associated_picture_occurrence_ids
                if (
                    len(targets) != len(set(targets))
                    or row.source_region is None
                    or any(
                        not isinstance(target := seen.get(target_id), VisualPicture)
                        or target.source_region is None
                        for target_id in targets
                    )
                ):
                    raise ValueError(
                        "visual caption associations require qualified distinct pictures"
                    )
        return self

    @property
    def row_count(self) -> int:
        return len(self.rows) + sum(
            len(row.cells) for row in self.rows if isinstance(row, VisualTable)
        )

    def artifact_bytes(self) -> bytes:
        from corpus_structure.semantic.query import ReadLimit

        content = self.model_dump_json(exclude_none=True).encode()
        if len(content) > MAX_VISUAL_EVIDENCE_BYTES:
            raise ReadLimit(
                "mapped visual evidence exceeds its byte bound", reason="oversized_item"
            )
        return content


class VisualEvidenceRead(_VisualModel):
    """Original and incumbent scope alongside attributed recognition candidates."""

    standing: Literal["recognition_candidate"] = "recognition_candidate"
    evidence: VisualEvidencePin
    raw_evidence: VisualEvidencePin
    producer: dict[str, JsonValue]
    raw_producer: dict[str, JsonValue]
    page_no: int
    original_artifact_digest: str
    original_regions: list[dict[str, JsonValue]]
    submitted_region: VisualSourceRegion | None
    observation_release_id: str
    observation: dict[str, JsonValue]
    observation_health: dict[str, JsonValue] | None = None
    mapping_availability: Literal["available", "unavailable", "not_selected"]
    items: tuple[VisualEvidenceRow, ...] = ()
