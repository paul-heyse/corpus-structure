"""Typed, candidate-only Chandra evidence retained outside the source projection."""

from __future__ import annotations

import json
from base64 import b64encode
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    JsonValue,
    TypeAdapter,
    model_validator,
)

if TYPE_CHECKING:
    from sqlalchemy import Connection

    from corpus_structure.core.db.lifetime import BorrowerCancellation
    from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
    from corpus_structure.semantic.types import PreparedRelease
    from corpus_structure.serve.native_source import NativeSourceRequest, NativeSourceResponse

MAX_VISUAL_EVIDENCE_BYTES = 8 * 1024 * 1024
MAX_VISUAL_EVIDENCE_ROWS = 10_000


class _VisualModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class VisualEvidencePin(_VisualModel):
    run_id: int = Field(gt=0)
    task_id: int = Field(gt=0)
    product_key: str = Field(min_length=1)
    content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


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
    page_no: int
    original_artifact_digest: str
    original_regions: list[dict[str, JsonValue]]
    submitted_region: VisualSourceRegion | None
    observation_release_id: str
    observation: dict[str, JsonValue]
    observation_health: dict[str, JsonValue] | None = None
    mapping_availability: Literal["available", "unavailable"]
    items: tuple[VisualEvidenceRow, ...] = ()


def _visual_dependents(request, project_id, source_release):
    """Resolve Chandra products only through their exact integrated structural input."""
    from sqlalchemy import func, select

    from corpus_structure.semantic.metadata import table

    products, tasks, runs = map(table, ("ops.pdf_product", "ops.task", "ops.run"))
    edges, bodies = map(table, ("ops.pdf_product_input", "ops.pdf_product_body"))
    configs = table("ops.method_config")
    source = products.alias("visual_source_product")
    producer = tasks.alias("visual_source_task")
    observation = bodies.c.descriptor["observation"]
    scope = func.coalesce(
        runs.c.options["visual_request"], func.jsonb_strip_nulls(configs.c.params["selection"])
    )
    statement = (
        select(
            products.c.release_id,
            products.c.artifact_digest,
            products.c.contract_digest,
            tasks.c.status,
            tasks.c.finished_at,
            bodies.c.recipe_digest,
            observation.label("observation"),
            bodies.c.descriptor["health"].label("observation_health"),
            scope.label("visual_request"),
        )
        .select_from(products)
        .join(tasks, tasks.c.id == products.c.task_id)
        .join(runs, runs.c.id == tasks.c.run_id)
        .join(configs, configs.c.id == tasks.c.method_config_id)
        .join(
            bodies,
            (bodies.c.task_id == products.c.task_id)
            & (bodies.c.product_key == products.c.product_key),
        )
        .join(
            edges,
            (edges.c.task_id == products.c.task_id)
            & (edges.c.product_key == products.c.product_key),
        )
        .join(
            source,
            (source.c.task_id == edges.c.input_task_id)
            & (source.c.product_key == edges.c.input_product_key)
            & (source.c.content_digest == edges.c.input_content_digest),
        )
        .join(producer, producer.c.id == source.c.task_id)
        .where(
            products.c.kind == "recognition_observation",
            products.c.release_id == runs.c.release_id,
            observation["pass_role"].astext.in_(("chandra_page", "chandra_crop")),
            runs.c.project_id == project_id,
            edges.c.role == "structural",
            source.c.task_id == request.task_id,
            source.c.product_key == request.product_key,
            source.c.content_digest == request.content_digest,
            source.c.kind == "integrated",
            source.c.release_id == source_release,
            source.c.artifact_digest == products.c.artifact_digest,
            producer.c.run_id == request.run_id,
        )
    )
    return statement, products, tasks, runs, bodies, scope


def _qualified_observation(conn, request, evidence, project_id, source_release, budget):
    """Resolve an exact downstream structural edge before opening evidence custody."""
    from corpus_structure.semantic.pdf_storage import _budgeted_mappings

    statement, products, _, runs, _, _ = _visual_dependents(request, project_id, source_release)
    rows = _budgeted_mappings(
        conn,
        statement.where(
            products.c.task_id == evidence.task_id,
            products.c.product_key == evidence.product_key,
            products.c.content_digest == evidence.content_digest,
            runs.c.id == evidence.run_id,
        ).limit(2),
        budget,
    )
    if len(rows) != 1:
        raise ValueError(
            "visual evidence does not directly depend on the exact integrated source/run"
        )
    return rows[0]


class VisualObservationEntry(_VisualModel):
    page_no: int = Field(gt=0)
    pointer: str | None = None
    region_index: int | None = None
    rotation: Literal[0, 90, 180, 270] | None = None
    raw: VisualEvidencePin
    mapped: VisualEvidencePin | None = None
    execution_outcome: str
    mapping_availability: Literal["raw_only", "unavailable", "available"]


class VisualObservationManifest(_VisualModel):
    source: VisualEvidencePin
    observations: tuple[VisualObservationEntry, ...]
    next_after_task: int | None = None


def visual_observation_manifest(
    conn: Connection,
    source: VisualEvidencePin,
    *,
    page_no: int | None,
    after_task: int,
    limit: int,
) -> VisualObservationManifest:
    """List settled observations and their exact raw/mapped dependencies."""
    from sqlalchemy import or_, select

    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.pdf_contracts import pdf_context_for_release
    from corpus_structure.semantic.pdf_record_reader import (
        PublishedReadBudget,
        published_record_reader,
    )
    from corpus_structure.semantic.pdf_storage import _budgeted_mappings
    from corpus_structure.semantic.product_reference import ProductReference
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.visual_requests import VisualSelection

    if not (1 <= limit <= 1000 and after_task >= 0 and (page_no is None or page_no > 0)):
        raise ValueError("invalid visual observation manifest page, position or limit")
    runs, tasks = map(table, ("ops.run", "ops.task"))
    identity = conn.execute(
        select(runs.c.project_id, runs.c.release_id)
        .join(tasks, tasks.c.run_id == runs.c.id)
        .where(runs.c.id == source.run_id, tasks.c.id == source.task_id)
    ).one_or_none()
    if identity is None:
        raise ValueError("visual observation manifest requires the exact producing run and task")
    archive = open_release(conn, identity.release_id)
    pdf_context_for_release(conn, archive).execution.require_operation("read_native_source")
    reader = published_record_reader(
        conn,
        ProductReference(source.task_id, source.product_key, source.content_digest),
        projection_context=archive,
    )
    if (
        reader is None
        or reader.revision["release_id"] != identity.release_id
        or reader.product_kind() != "integrated"
    ):
        raise ValueError("visual observation manifest requires an exact published integrated PDF")

    base, products, tasks, runs, bodies, scope = _visual_dependents(
        source, identity.project_id, identity.release_id
    )
    observation = bodies.c.descriptor["observation"]
    selected = base.with_only_columns(
        tasks.c.id.label("task_id"),
        runs.c.id.label("run_id"),
        products.c.product_key,
        products.c.content_digest,
        products.c.release_id,
        products.c.artifact_digest,
        observation["image"]["page_no"].as_integer().label("page_no"),
        observation["pass_role"].astext.label("pass_role"),
        observation["outcome"].astext.label("execution_outcome"),
        observation["mapped_evidence_digest"].astext.label("mapped_digest"),
        scope.label("scope"),
    ).where(
        tasks.c.id > after_task,
        tasks.c.finished_at.is_not(None),
        tasks.c.unit_key == products.c.product_key,
        or_(
            runs.c.options["visual_request"].is_not(None),
            runs.c.options["visual_group"].is_not(None),
        ),
        or_(
            products.c.product_key.startswith("chandra-inference:"),
            products.c.product_key.startswith("chandra-mapping:"),
        ),
    )
    if page_no is not None:
        selected = selected.where(observation["image"]["page_no"].as_integer() == page_no)
    selected = selected.order_by(tasks.c.id).limit(limit + 1).cte("visual_manifest_page")

    edges = table("ops.pdf_product_input").alias("visual_raw_input")
    raw_source = table("ops.pdf_product_input").alias("visual_raw_source")
    raw = products.alias("visual_raw_product")
    raw_task, raw_run = tasks.alias("visual_raw_task"), runs.alias("visual_raw_run")
    query = (
        select(
            selected,
            raw.c.task_id.label("raw_task_id"),
            raw.c.product_key.label("raw_product_key"),
            raw.c.content_digest.label("raw_content_digest"),
            raw_run.c.id.label("raw_run_id"),
            raw.c.release_id.label("raw_release_id"),
        )
        .outerjoin(
            edges,
            (edges.c.task_id == selected.c.task_id)
            & (edges.c.product_key == selected.c.product_key)
            & (edges.c.role == "recognition"),
        )
        .outerjoin(
            raw,
            (raw.c.task_id == edges.c.input_task_id)
            & (raw.c.product_key == edges.c.input_product_key)
            & (raw.c.content_digest == edges.c.input_content_digest)
            & (raw.c.kind == "recognition_observation")
            & (raw.c.artifact_digest == selected.c.artifact_digest)
            & raw.c.product_key.startswith("chandra-inference:")
            & select(1)
            .select_from(raw_source)
            .where(
                raw_source.c.task_id == raw.c.task_id,
                raw_source.c.product_key == raw.c.product_key,
                raw_source.c.role == "structural",
                raw_source.c.input_task_id == source.task_id,
                raw_source.c.input_product_key == source.product_key,
                raw_source.c.input_content_digest == source.content_digest,
            )
            .exists(),
        )
        .outerjoin(raw_task, (raw_task.c.id == raw.c.task_id) & raw_task.c.finished_at.is_not(None))
        .outerjoin(
            raw_run,
            (raw_run.c.id == raw_task.c.run_id)
            & (raw_run.c.project_id == identity.project_id)
            & (raw_run.c.release_id == raw.c.release_id),
        )
        .order_by(selected.c.task_id)
        .limit(limit + 1)
    )
    budget = PublishedReadBudget(limit + 1, MAX_VISUAL_EVIDENCE_BYTES)
    rows = _budgeted_mappings(conn, query, budget)
    entries = []
    allowed_releases: set[str] = set()
    seen: set[int] = set()
    for row in rows[:limit]:
        task_id = row["task_id"]
        if task_id in seen:
            raise ValueError("visual manifest has multiple raw inputs for a mapped observation")
        seen.add(task_id)
        for release in (row["release_id"], row["raw_release_id"]):
            if release is not None and release not in allowed_releases:
                context = pdf_context_for_release(conn, open_release(conn, release))
                context.execution.require_operation("read_pdf_product")
                allowed_releases.add(release)
        scope = VisualSelection.model_validate(row["scope"])
        if (
            scope.source != source
            or scope.page_no != row["page_no"]
            or ((scope.pointer is not None) != (row["pass_role"] == "chandra_crop"))
        ):
            raise ValueError("visual manifest observation differs from its retained selection")
        observed = VisualEvidencePin(
            run_id=row["run_id"],
            task_id=task_id,
            product_key=row["product_key"],
            content_digest=row["content_digest"],
        )
        mapped = observed if row["product_key"].startswith("chandra-mapping:") else None
        if mapped is None:
            raw_pin = observed
        else:
            if row["raw_run_id"] is None:
                raise ValueError("visual manifest mapping lacks a qualified raw input")
            raw_pin = VisualEvidencePin(
                run_id=row["raw_run_id"],
                task_id=row["raw_task_id"],
                product_key=row["raw_product_key"],
                content_digest=row["raw_content_digest"],
            )
        entries.append(
            VisualObservationEntry(
                page_no=scope.page_no,
                pointer=scope.pointer,
                region_index=scope.region_index,
                rotation=scope.rotation,
                raw=raw_pin,
                mapped=mapped,
                execution_outcome=row["execution_outcome"],
                mapping_availability=(
                    "raw_only"
                    if mapped is None
                    else "available"
                    if row["mapped_digest"] is not None
                    else "unavailable"
                ),
            )
        )
    return VisualObservationManifest(
        source=source,
        observations=tuple(entries),
        next_after_task=rows[limit - 1]["task_id"] if len(rows) > limit else None,
    )


def _read_visual_artifact(conn, evidence, digest, budget, *, offset=None):
    """Read a whole bounded mapped artifact or a raw byte page from direct custody."""
    from sqlalchemy import func, select

    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.query import ReadLimit

    custody, artifacts = map(table, ("ops.pdf_product_artifact", "kb.source_artifact"))
    retained = custody.join(artifacts, artifacts.c.artifact_digest == custody.c.artifact_digest)
    criteria = (
        custody.c.task_id == evidence.task_id,
        custody.c.product_key == evidence.product_key,
        custody.c.artifact_digest == digest,
    )
    size = conn.scalar(
        select(func.octet_length(artifacts.c.content)).select_from(retained).where(*criteria)
    )
    if size is None:
        raise ValueError("visual artifact is unavailable in the exact observation custody")
    if offset is None and size > MAX_VISUAL_EVIDENCE_BYTES:
        raise ReadLimit("mapped visual evidence exceeds its byte bound", reason="oversized_item")
    start = 0 if offset is None else offset
    if start > size or (start == size and start != 0):
        raise ValueError("visual artifact continuation exceeds retained byte length")
    length = size if offset is None else min(65536, size - start)
    if offset is not None and 4 * ((length + 2) // 3) > budget.max_bytes:
        raise ReadLimit(
            "encoded visual artifact page exceeds the byte bound", reason="oversized_item"
        )
    _charge_rows(budget, 1)
    budget.reserve(length)
    payload = conn.execute(
        select(func.substring(artifacts.c.content, start + 1, length))
        .select_from(retained)
        .where(*criteria)
    ).scalar_one()
    return bytes(payload), size


def _charge_rows(budget, count):
    from corpus_structure.semantic.query import ReadLimit

    if budget.rows + count > budget.max_rows:
        raise ReadLimit("visual evidence row-work budget exhausted", reason="work_limit")
    budget.rows += count


def _native_region(row):
    top, bottom = row["top"], row["bottom"]
    if row["origin"] == "bottom_left":
        top, bottom = row["page_height"] - top, row["page_height"] - bottom
    elif row["origin"] != "top_left":
        raise ValueError("visual selection has an unsupported original coordinate origin")
    return VisualSourceRegion(left=row["left"], top=top, right=row["right"], bottom=bottom)


def _overlaps(a, b):
    return a.left < b.right and b.left < a.right and a.top < b.bottom and b.top < a.bottom


def _media_region(row, image):
    """Map a published displayed CropBox region into media-relative evidence points."""
    from corpus_structure.ingest.pdf_recognition import inverse_transform_point

    display = _native_region(row)
    sx = image["width"] / float(row["page_width"])
    sy = image["height"] / float(row["page_height"])
    affine = image["transform"]["affine"]
    corners = [
        inverse_transform_point(affine, x * sx, y * sy)
        for x in (display.left, display.right)
        for y in (display.top, display.bottom)
    ]
    xs, ys = zip(*corners, strict=True)
    return VisualSourceRegion(
        left=max(0, min(xs)), top=max(0, min(ys)), right=max(xs), bottom=max(ys)
    )


def _selected_visual_rows(rows, *, occurrence_id, cell_index, kind, figure_query):
    if occurrence_id is not None:
        anchor = next((row for row in rows if row.get("occurrence_id") == occurrence_id), None)
        if anchor is None:
            raise ValueError("visual candidate occurrence is outside the submitted scope")
        if cell_index is None:
            rows = [anchor]
        else:
            if anchor.get("kind") != "table":
                raise ValueError("visual cell reads require a table candidate")
            table = VisualTable.model_validate(anchor)
            if not 0 <= cell_index < len(table.cells):
                raise ValueError("visual cell index is outside its candidate table")
            group = table.cells[cell_index].content_occurrence_id
            if group is None:
                raise ValueError("visual cell has no retained rich content group")
            subtree = set()
            for row in rows:
                pointer = row.get("occurrence_id")
                parent = row.get("parent_occurrence_id")
                if (pointer == group and parent == occurrence_id) or parent in subtree:
                    subtree.add(pointer)
            if group not in subtree:
                raise ValueError("visual cell content is outside the submitted scope")
            rows = [row for row in rows if row.get("occurrence_id") in subtree]
    if figure_query is not None:
        phrase = " ".join(figure_query.casefold().split())
        figure_roots: dict[str, str] = {}
        matches: set[str] = set()
        for row in rows:
            pointer, parent = row.get("occurrence_id"), row.get("parent_occurrence_id")
            if row.get("kind") == "picture":
                figure_roots[pointer] = pointer
            elif parent in figure_roots:
                figure_roots[pointer] = figure_roots[parent]
            if row.get("kind") not in {
                "picture_text",
                "picture_description",
                "caption",
                "caption_candidate",
            }:
                continue
            if phrase in " ".join(row.get("text", "").casefold().split()):
                if pointer in figure_roots:
                    matches.add(figure_roots[pointer])
                matches.update(row.get("parser_attachment_occurrence_ids", ()))
                matches.update(row.get("associated_picture_occurrence_ids", ()))
        rows = [row for row in rows if row.get("occurrence_id") in matches]
    if kind is not None:
        rows = [row for row in rows if row.get("kind") == kind]
    return rows


def _mapped_page(
    content,
    *,
    page_no,
    submitted,
    regions,
    budget,
    after,
    limit,
    occurrence_id=None,
    cell_index=None,
    kind=None,
    figure_query=None,
):
    """Charge the bounded locator scan, then validate only the selected candidate bodies."""
    from corpus_structure.semantic.refusals import InvalidContinuation

    body = json.loads(content)
    if (
        not isinstance(body, dict)
        or set(body) != {"version", "page_no", "rows"}
        or type(body["version"]) is not int
        or body["version"] != 1
        or type(body["page_no"]) is not int
        or body["page_no"] != page_no
        or not isinstance(body["rows"], list)
    ):
        raise ValueError(
            "mapped visual evidence differs from the submitted page or artifact contract"
        )
    _charge_rows(budget, len(body["rows"]))
    scoped = []
    for row in body["rows"]:
        if not isinstance(row, dict):
            raise ValueError("mapped visual evidence row is invalid")
        if row.get("kind") == "table":
            cells = row.get("cells")
            if not isinstance(cells, list):
                raise ValueError("mapped visual evidence table has no cell inventory")
            _charge_rows(budget, len(cells))
        raw_region = row.get("source_region")
        region = VisualSourceRegion.model_validate(raw_region) if raw_region is not None else None
        if region is not None and (
            submitted is None
            or region.left < submitted.left - 1e-5
            or region.right > submitted.right + 1e-5
            or region.top < submitted.top - 1e-5
            or region.bottom > submitted.bottom + 1e-5
        ):
            raise ValueError("mapped visual evidence lies outside the submitted frame")
        if not regions or (region is not None and any(_overlaps(region, r) for r in regions)):
            scoped.append(row)
    selected = _selected_visual_rows(
        scoped,
        occurrence_id=occurrence_id,
        cell_index=cell_index,
        kind=kind,
        figure_query=figure_query,
    )
    matched = len(selected)
    if after and after >= matched:
        raise InvalidContinuation(
            "visual evidence continuation is out of scope", reason="invalid_continuation"
        )
    end = after + limit
    return _VISUAL_ITEMS.validate_python(selected[after:end]), end if end < matched else None


_VISUAL_ITEMS = TypeAdapter(tuple[VisualEvidenceRow, ...])


def _read_mapped_locator(conn, evidence, digest, request, regions, budget, after):
    """Seek within admitted metadata before hydrating the requested candidate bodies."""
    from sqlalchemy import Numeric, Text, and_, cast, func, or_, select

    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.query import ReadLimit
    from corpus_structure.semantic.refusals import InvalidContinuation

    index, locator, cells = map(
        table, ("ops.pdf_visual_index", "kb.pdf_visual_locator", "kb.pdf_visual_cell")
    )

    def pin(relation):
        return (
            relation.c.task_id == evidence.task_id,
            relation.c.product_key == evidence.product_key,
            relation.c.artifact_digest == digest,
        )

    if conn.scalar(select(index.c.row_count).where(*pin(index))) is None:
        raise ValueError("mapped visual evidence has no admitted locator")
    if after == 0 and request.cursor is None:
        position = 0
    elif (
        isinstance(after, dict)
        and set(after) == {"visual_locator"}
        and (type(after["visual_locator"]) is int and after["visual_locator"] > 0)
    ):
        position = after["visual_locator"]
    else:
        raise InvalidContinuation(
            "visual locator continuation version differs", reason="invalid_continuation"
        )

    body = locator.c.body
    region = body["source_region"].label("region")
    metadata = select(
        locator.c.ordinal, locator.c.occurrence_id, locator.c.kind, locator.c.parent_id, region
    ).where(*pin(locator))

    def scoped(row):
        return not regions or (
            row.region is not None
            and any(
                _overlaps(VisualSourceRegion.model_validate(row.region), requested)
                for requested in regions
            )
        )

    def bounded(statement, maximum=None):
        remaining = budget.max_rows - budget.rows
        if remaining <= 0:
            raise ReadLimit("visual evidence row-work budget exhausted", reason="work_limit")
        limit = remaining + 1 if maximum is None else min(remaining + 1, maximum)
        rows = conn.execute(statement.limit(limit)).all()
        _charge_rows(budget, len(rows))
        return rows

    def exact(occurrence):
        rows = bounded(metadata.where(locator.c.occurrence_id == occurrence), 1)
        return rows[0] if rows and scoped(rows[0]) else None

    if request.occurrence_id is not None:
        anchor = exact(request.occurrence_id)
        if anchor is None:
            raise ValueError("visual candidate occurrence is outside the submitted scope")
        if request.cell_index is None:
            candidates = [anchor]
        else:
            if anchor.kind != "table":
                raise ValueError("visual cell reads require a table candidate")
            cell = conn.execute(
                select(cells.c.group_id).where(
                    *pin(cells),
                    cells.c.occurrence_id == anchor.occurrence_id,
                    cells.c.cell_index == request.cell_index,
                )
            ).one_or_none()
            _charge_rows(budget, int(cell is not None))
            if cell is None:
                raise ValueError("visual cell index is outside its candidate table")
            if cell.group_id is None:
                raise ValueError("visual cell has no retained rich content group")
            root = exact(cell.group_id)
            if root is None:
                raise ValueError("visual cell content is outside the submitted scope")
            tree = metadata.where(locator.c.occurrence_id == root.occurrence_id).cte(
                "visual_cell_subtree", recursive=True
            )
            children = metadata.join(tree, locator.c.parent_id == tree.c.occurrence_id)
            if regions:
                coords = body["source_region"]
                children = children.where(
                    or_(
                        *(
                            and_(
                                cast(coords["left"].as_string(), Numeric) < area.right,
                                cast(coords["right"].as_string(), Numeric) > area.left,
                                cast(coords["top"].as_string(), Numeric) < area.bottom,
                                cast(coords["bottom"].as_string(), Numeric) > area.top,
                            )
                            for area in regions
                        )
                    )
                )
            tree = tree.union_all(children)
            candidates = bounded(select(tree))
        candidates = sorted(
            (row for row in candidates if row.ordinal > position), key=lambda row: row.ordinal
        )
    elif request.visual_query is not None:
        phrase = " ".join(request.visual_query.casefold().split())
        textual = bounded(
            metadata.add_columns(
                body["text"].as_string().label("reading"),
                body["parser_attachment_occurrence_ids"].label("parser_targets"),
                body["associated_picture_occurrence_ids"].label("association_targets"),
            )
            .where(
                locator.c.kind.in_(
                    ("picture_text", "picture_description", "caption", "caption_candidate")
                )
            )
            .order_by(locator.c.kind, locator.c.ordinal)
        )
        targets = set()
        for row in textual:
            if not scoped(row) or phrase not in " ".join((row.reading or "").casefold().split()):
                continue
            targets.update(row.parser_targets or ())
            targets.update(row.association_targets or ())
            ancestor = row
            while ancestor is not None and ancestor.parent_id is not None:
                ancestor = exact(ancestor.parent_id)
                if ancestor is not None and ancestor.kind == "picture":
                    targets.add(ancestor.occurrence_id)
                    break
        candidates = (
            []
            if not targets
            else bounded(
                metadata.where(
                    locator.c.occurrence_id.in_(targets),
                    locator.c.ordinal > position,
                ).order_by(locator.c.ordinal)
            )
        )
        candidates = [row for row in candidates if scoped(row)]
    else:
        selection = metadata.where(locator.c.ordinal > position)
        if request.visual_kind is not None:
            selection = selection.where(locator.c.kind == request.visual_kind)
        candidates = [
            row
            for row in bounded(
                selection.order_by(locator.c.ordinal), request.limit + 1 if not regions else None
            )
            if scoped(row)
        ]

    if request.visual_kind is not None:
        candidates = [row for row in candidates if row.kind == request.visual_kind]
    if position and not candidates:
        raise InvalidContinuation(
            "visual evidence continuation is out of scope", reason="invalid_continuation"
        )
    page = candidates[: request.limit]
    if not page:
        return (), None
    selected = (*pin(locator), locator.c.ordinal.in_([row.ordinal for row in page]))
    sizes = conn.execute(
        select(
            func.octet_length(cast(body, Text)),
            func.coalesce(func.jsonb_array_length(body["cells"]), 0),
        ).where(*selected)
    ).all()
    _charge_rows(budget, sum(row[1] for row in sizes))
    budget.reserve(sum(row[0] for row in sizes))
    bodies = conn.execute(select(body).where(*selected).order_by(locator.c.ordinal)).scalars().all()
    following = {"visual_locator": page[-1].ordinal} if len(candidates) > len(page) else None
    return _VISUAL_ITEMS.validate_python(bodies), following


def _page_incumbent(conn, source, page_no, budget):
    """Select existing projected items on this page before fetching their bounded prose."""
    from sqlalchemy import select

    from corpus_structure.semantic.pdf_record_reader import published_native_table
    from corpus_structure.semantic.pdf_storage import _budgeted_mappings

    regions, items = published_native_table("region"), published_native_table()
    pointers = select(regions.c.pointer).where(
        regions.c.task_id == source.task_id,
        regions.c.product_key == source.product_key,
        regions.c.page_no == page_no,
    )
    query = (
        select(items.c.pointer, items.c.label, items.c.content_layer, items.c.text)
        .where(
            items.c.task_id == source.task_id,
            items.c.product_key == source.product_key,
            items.c.pointer.in_(pointers),
        )
        .order_by(items.c.ordinal)
        .limit(budget.max_rows - budget.rows + 1)
    )
    return _budgeted_mappings(conn, query, budget)


def inspect_pdf_visual_evidence(
    conn: Connection,
    request: NativeSourceRequest,
    *,
    project_id: str,
    projection_context: PreparedRelease,
    cancellation: BorrowerCancellation,
    read_budget: PublishedReadBudget,
) -> NativeSourceResponse:
    """Read a candidate observation beside its exact, independently retained source."""
    from pydantic_core import to_jsonable_python

    from corpus_structure.semantic.pdf_contracts import pdf_context_for_release
    from corpus_structure.semantic.pdf_record_reader import published_record_reader
    from corpus_structure.semantic.pdf_storage import _record_product_identity
    from corpus_structure.semantic.product_reference import ProductReference
    from corpus_structure.semantic.query import ReadLimit
    from corpus_structure.semantic.refusals import InvalidContinuation
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.serve.native_source import (
        NativeSourceResponse,
        _published_native_header,
        _source_cursor,
        _source_position,
    )

    evidence = request.evidence
    if evidence is None:
        raise ValueError("visual evidence requires its exact observation pin")
    after = _source_position(request) if request.cursor is not None else 0
    if request.artifact_digest is not None and (type(after) is not int or after < 0):
        raise InvalidContinuation(
            "invalid visual evidence continuation", reason="invalid_continuation"
        )
    qualified = _qualified_observation(
        conn, request, evidence, project_id, projection_context.release_id, read_budget
    )
    evidence_release = qualified["release_id"]
    context = pdf_context_for_release(conn, open_release(conn, evidence_release))
    context.execution.require_operation("read_pdf_product")
    # The archive governs which observation may be opened. These display filters
    # apply only to its admitted, bounded candidate rows and bind the read cursor.
    context.boundary.validate_json(
        "PdfNativeReadRequest",
        request.model_dump_json(exclude={"visual_kind", "visual_query"}, exclude_none=True),
    )
    states = context.execution.lifecycle("task").states
    matching = [
        state
        for state in states
        if any(
            value.dimension == "status" and value.value == qualified["status"]
            for value in state.values
        )
    ]
    if (
        not matching
        or not all(state.terminal for state in matching)
        or qualified["finished_at"] is None
    ):
        raise ValueError("visual evidence requires a finished producing task")
    if context.contract_digest != qualified["contract_digest"]:
        raise ValueError("visual evidence differs from its archived producing contract")
    observation = qualified["observation"]
    image = observation["image"]
    page_no = image["page_no"]
    if request.page_no is not None and request.page_no != page_no:
        raise ValueError("visual evidence differs from the selected physical page")
    artifact_media_type = None
    if request.artifact_digest is not None:
        if request.artifact_digest == image["artifact_digest"]:
            artifact_media_type = "image/png"
        elif request.artifact_digest == observation.get("raw_response_digest"):
            artifact_media_type = "text/html; charset=utf-8"
        else:
            raise ValueError("visual artifact is outside the exact submitted image/raw custody")
    source = ProductReference(request.task_id, request.product_key, request.content_digest)
    published = published_record_reader(
        conn,
        source,
        cancellation=cancellation,
        projection_context=projection_context,
        read_budget=read_budget,
    )
    if published is None:
        raise ValueError("visual evidence requires a retained integrated source")
    _record_product_identity(
        conn, source.task_id, source.product_key, source.content_digest, published
    )
    published._native_schema_mapping()
    header = _published_native_header(published, request.run_id, runtime=False)
    if header.artifact_digest != qualified["artifact_digest"] or (
        header.page_start is not None and not header.page_start <= page_no <= header.page_end
    ):
        raise ValueError("visual evidence differs from the retained original or page range")
    transform = image["transform"]
    submitted = (
        VisualSourceRegion(
            left=transform["crop_left"],
            top=transform["crop_top"],
            right=transform["crop_right"],
            bottom=transform["crop_bottom"],
        )
        if transform["status"] == "coarse"
        else None
    )
    rows, original_regions, scope_regions = [], [], []
    companion, following, items = None, None, ()
    mapped_digest = observation.get("mapped_evidence_digest")
    if request.pointer is not None:
        rows = published.item_page(pointer=request.pointer, limit=1)
        original_regions = (
            published.regions(request.pointer)
            if request.region_index is None
            else [published.region(request.pointer, request.region_index)]
        )
        original_regions = [row for row in original_regions if row["page_no"] == page_no]
        if not rows or not original_regions:
            raise ValueError("selected source item/region is outside the qualified submitted scope")
        if observation["pass_role"] == "chandra_crop":
            selected = qualified.get("visual_request") or {}
            if request.pointer != selected.get("pointer") or request.region_index != selected.get(
                "region_index"
            ):
                raise ValueError(
                    "visual crop inspection requires the exact requested source region"
                )
            scope_regions = [submitted] if submitted is not None else []
        elif submitted is not None:
            scope_regions = [_media_region(row, image) for row in original_regions]
            if not any(_overlaps(region, submitted) for region in scope_regions):
                raise ValueError(
                    "selected source item/region is outside the qualified submitted scope"
                )
        if submitted is None:
            mapped_digest = None
        remaining = read_budget.max_rows - read_budget.rows
        if remaining < 2:
            raise ReadLimit("visual evidence row-work budget exhausted", reason="work_limit")
        companion = published.source_context(
            (request.pointer,),
            rows[0].get("section_pointer") or "#/body",
            row_budget=remaining - 1,
        )
        _charge_rows(
            read_budget,
            sum(
                len(companion[name])
                for name in ("inputs", "occurrences", "relations", "coverage", "mapping_reports")
            )
            + sum(len(relation["endpoints"]) for relation in companion["relations"]),
        )
        rows[0]["native_item"] = published.selected_native_items((request.pointer,))[
            request.pointer
        ]
    elif request.artifact_digest is None:
        rows = _page_incumbent(conn, source, page_no, read_budget)
    if request.artifact_digest is not None:
        content, size = _read_visual_artifact(
            conn, evidence, request.artifact_digest, read_budget, offset=after
        )
        following = after + len(content) if after + len(content) < size else None
        rows = [
            dict(
                artifact_digest=request.artifact_digest,
                total_bytes=size,
                offset=after,
                length=len(content),
                encoding="base64",
                media_type=artifact_media_type,
                data=b64encode(content).decode("ascii"),
                next_offset=following,
            )
        ]
    elif mapped_digest is not None:
        items, following = _read_mapped_locator(
            conn, evidence, mapped_digest, request, scope_regions, read_budget, after
        )
    elif after:
        raise InvalidContinuation(
            "visual evidence has no candidate continuation", reason="invalid_continuation"
        )
    return NativeSourceResponse(
        selection=request,
        release_id=header.release_id,
        health=to_jsonable_python(header.health),
        rows=to_jsonable_python(rows),
        next_cursor=_source_cursor(request, following) if following is not None else None,
        companion=to_jsonable_python(companion),
        visual_evidence=VisualEvidenceRead(
            page_no=page_no,
            original_artifact_digest=header.artifact_digest,
            original_regions=to_jsonable_python(original_regions),
            submitted_region=submitted,
            observation_release_id=evidence_release,
            observation=to_jsonable_python(
                dict(observation, recipe_digest=qualified["recipe_digest"])
            ),
            observation_health=to_jsonable_python(qualified.get("observation_health")),
            mapping_availability="available" if mapped_digest is not None else "unavailable",
            items=items,
        ),
    )
