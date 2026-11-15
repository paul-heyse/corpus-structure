"""Read stored visual observation/dispatch custody through its original producing pins.

The retained visual evidence and dispatch readers consume these exact stored
run-option selections, PDF publication edges and immutable original bytes.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import and_, select, true

from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin

from .metadata import table
from .pdf_contracts import pdf_context_for_release
from .pdf_integrated import RetainedPdfOriginal
from .product_reference import ProductReference
from .releases import open_release

VISUAL_REQUEST_CUT = "visual-request-source"
VISUAL_REQUEST_CODE_COMMIT = "chandra-visual-source-v1"
VISUAL_NOMINATION_VERSION = "visual-nomination-v2"
_PROVIDER = "datalab-chandra-2"


class RetainedVisualSelection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source: VisualEvidencePin
    page_no: int = Field(gt=0)
    pointer: str | None = Field(default=None, pattern=r"^#/.+")
    region_index: int | None = Field(default=None, ge=0)
    rotation: Literal[0, 90, 180, 270] | None = None

    @model_validator(mode="after")
    def validate_crop(self):
        if (self.pointer is None) != (self.region_index is None):
            raise ValueError("a visual crop requires both pointer and region index")
        if self.rotation is not None and self.pointer is None:
            raise ValueError("visual rotation requires a qualified crop")
        return self

    def scope(self):
        scope = self.model_dump(mode="json", exclude_none=True)
        if scope.get("rotation") == 0:
            del scope["rotation"]
        return scope


def retained_visual_scope(options, selection):
    if "visual_group" not in options:
        return options.get("visual_request")
    scope = RetainedVisualSelection.model_validate(selection).scope()
    return scope if scope in options["visual_group"]["selections"] else None


def _digest(content: bytes) -> str:
    return sha256(content).hexdigest()


def _reference(pin: VisualEvidencePin) -> ProductReference:
    return ProductReference(pin.task_id, pin.product_key, pin.content_digest)


def _load_visual_source(conn, pin: VisualEvidencePin):
    from .pdf_record_reader import published_record_reader
    from .pdf_storage import _record_product_identity

    runs, tasks = table("ops.run"), table("ops.task")
    source = conn.execute(
        select(runs.c.project_id, runs.c.release_id, tasks.c.unit_type, tasks.c.unit_id)
        .join(tasks, tasks.c.run_id == runs.c.id)
        .where(runs.c.id == pin.run_id, tasks.c.id == pin.task_id)
    ).one_or_none()
    if source is None or source.unit_type != "document" or source.unit_id is None:
        raise ValueError("visual request requires the exact producing PDF run and task")
    archive = open_release(conn, source.release_id)
    pdf_context_for_release(conn, archive).require_operation("read_native_source")
    reader = published_record_reader(conn, _reference(pin), projection_context=archive)
    if (
        reader is None
        or reader.product_kind() != "integrated"
        or reader.revision["release_id"] != source.release_id
    ):
        raise ValueError("visual request requires an exact published integrated PDF")
    identity = _record_product_identity(
        conn, pin.task_id, pin.product_key, pin.content_digest, reader
    )
    builds, artifacts, documents = map(
        table, ("ops.source_build", "kb.source_artifact", "kb.document")
    )
    digest = reader.revision["source_digest"]
    if identity["artifact_digest"] != digest:
        raise ValueError("visual request original differs from the admitted PDF product")
    row = conn.execute(
        select(artifacts.c.artifact_digest)
        .join(builds, builds.c.artifact_digest == artifacts.c.artifact_digest)
        .join(documents, documents.c.content_hash == artifacts.c.artifact_digest)
        .where(
            builds.c.task_id == pin.task_id,
            builds.c.release_id == source.release_id,
            builds.c.artifact_digest == digest,
            documents.c.id == source.unit_id,
            documents.c.project_id == source.project_id,
        )
    ).one_or_none()
    if row is None:
        raise ValueError("visual request original differs from the published source")
    return source.project_id, source.unit_id, RetainedPdfOriginal(digest), reader


def _read_visual_original(conn, original: RetainedPdfOriginal) -> bytes:
    artifacts = table("kb.source_artifact")
    content = conn.scalar(
        select(artifacts.c.content).where(artifacts.c.artifact_digest == original.digest)
    )
    if content is None or _digest(content) != original.digest:
        raise ValueError("visual request original differs from the published source")
    return bytes(content)


def _selection_region(reader, selection):
    region = None
    if selection.pointer is not None and selection.region_index is not None:
        region = reader.region(selection.pointer, selection.region_index)
        if region["page_no"] != selection.page_no:
            raise ValueError("visual request crop belongs to another physical page")
    return region


def _load_selection(conn, selection: RetainedVisualSelection):
    project, document, original, reader = _load_visual_source(conn, selection.source)
    return (
        project,
        document,
        _read_visual_original(conn, original),
        _selection_region(reader, selection),
    )


def _visual_task(conn, run_id, step, selection=None):
    tasks, configs = map(table, ("ops.task", "ops.method_config"))
    scope = (
        configs.c.params["selection"] == selection.model_dump(mode="json")
        if selection is not None
        else true()
    )
    return conn.execute(
        select(
            tasks.c.id,
            tasks.c.status,
            tasks.c.unit_key,
            tasks.c.method_config_id,
            tasks.c.reused_task_id,
            tasks.c.reason,
            tasks.c.error,
            tasks.c.trigger,
        )
        .join(configs, configs.c.id == tasks.c.method_config_id)
        .where(tasks.c.run_id == run_id, tasks.c.unit_key.startswith(f"chandra-{step}:"), scope)
    ).one_or_none()


def _task_product_pin(conn, task_id, key):
    tasks, products = map(table, ("ops.task", "ops.pdf_product"))
    row = conn.execute(
        select(tasks.c.run_id, products.c.content_digest)
        .join(products, products.c.task_id == tasks.c.id)
        .where(tasks.c.id == task_id, products.c.product_key == key)
    ).one()
    return VisualEvidencePin(
        run_id=row.run_id, task_id=task_id, product_key=key, content_digest=row.content_digest
    )


def _visual_product_pin(conn, task):
    if task is None:
        return None
    products = table("ops.pdf_product")
    producer = task.reused_task_id or task.id
    if not conn.scalar(
        select(products.c.task_id).where(
            products.c.task_id == producer, products.c.product_key == task.unit_key
        )
    ):
        return None
    return _task_product_pin(conn, producer, task.unit_key)


def _visual_mapping_raw_pin(conn, mapping, selection, project_id):
    if mapping is None:
        return None
    inputs = table("ops.pdf_product_input")
    edge = conn.execute(
        select(inputs.c.input_task_id, inputs.c.input_product_key).where(
            inputs.c.task_id == (mapping.reused_task_id or mapping.id),
            inputs.c.product_key == mapping.unit_key,
            inputs.c.role == "recognition",
        )
    ).one_or_none()
    if edge is not None:
        return _task_product_pin(conn, *edge)
    try:
        pin = VisualEvidencePin.model_validate((mapping.trigger or {}).get("visual_raw"))
    except ValueError:
        return None
    products, tasks, runs, configs, bodies = map(
        table,
        ("ops.pdf_product", "ops.task", "ops.run", "ops.method_config", "ops.pdf_product_body"),
    )
    observation = bodies.c.descriptor["observation"]
    origin = conn.execute(
        select(runs.c.options, configs.c.params["selection"].label("selection"))
        .select_from(products)
        .join(tasks, tasks.c.id == products.c.task_id)
        .join(runs, runs.c.id == tasks.c.run_id)
        .join(configs, configs.c.id == tasks.c.method_config_id)
        .join(
            bodies,
            and_(
                bodies.c.task_id == products.c.task_id,
                bodies.c.product_key == products.c.product_key,
            ),
        )
        .join(
            inputs,
            and_(
                inputs.c.task_id == products.c.task_id,
                inputs.c.product_key == products.c.product_key,
            ),
        )
        .where(
            products.c.task_id == pin.task_id,
            products.c.product_key == pin.product_key,
            products.c.content_digest == pin.content_digest,
            products.c.release_id == runs.c.release_id,
            products.c.kind == "recognition_observation",
            runs.c.id == pin.run_id,
            runs.c.project_id == project_id,
            tasks.c.unit_key == pin.product_key,
            tasks.c.status.in_(("done", "empty")),
            products.c.product_key.startswith("chandra-inference:"),
            observation["binding"]["provider"].as_string() == _PROVIDER,
            observation["raw_response_digest"].as_string().is_not(None),
            observation["image"]["page_no"].as_integer() == selection.page_no,
            inputs.c.role == "structural",
            inputs.c.input_task_id == selection.source.task_id,
            inputs.c.input_product_key == selection.source.product_key,
            inputs.c.input_content_digest == selection.source.content_digest,
        )
    ).one_or_none()
    if (
        origin is None
        or retained_visual_scope(origin.options, origin.selection) != selection.scope()
    ):
        return None
    return pin
