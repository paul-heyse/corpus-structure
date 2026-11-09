"""Explicit local visual recognition against an immutable published PDF selection."""

from __future__ import annotations

import json
import re
from contextlib import ExitStack, contextmanager
from functools import cache
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from time import monotonic
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import and_, cast, func, select, text, true
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.core.method import UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin

from .identity import canonical_bytes
from .metadata import table
from .operations import (
    OperationBinding,
    OperationConflict,
    OperationDescriptor,
    claim_tasks,
    create_run,
    create_task,
    end_source_run,
    prepare_unit_completion,
    record_method,
    seal_cut,
)
from .pdf_contracts import pdf_context_for_release
from .pdf_integrated import (
    RetainedPdfOriginal,
    prepare_integrated_pdf_product,
    store_pdf_observation,
)
from .product_reference import ProductReference
from .query import read_snapshot
from .releases import open_release

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from .operation_results import ClaimedTask

_PROVIDER = "datalab-chandra-2"
_RENDER_POLICY = "pdfium-cropbox-media-top-left-scale-2-v1"
_CROP_POLICY = "qualified-pdf-region-enclosing-pixels-quarter-turn-v1"
_MAX_REPLAY_BYTES = 8 * 1024 * 1024
VISUAL_REQUEST_CUT = "visual-request-source"
VISUAL_REQUEST_CODE_COMMIT = "chandra-visual-source-v1"
VISUAL_GROUP_VERSION = "chandra-visual-group-v1"
VISUAL_NOMINATION_VERSION = "visual-nomination-v2"
MAX_VISUAL_GROUP = 4
_INFERENCE_RECIPE_VERSION = "chandra-inference-v2"


class VisualSelection(BaseModel):
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


class VisualRequestConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    step: Literal["inference", "mapping"]
    selection: VisualSelection
    recipe_digest: str


class VisualRequestResult(BaseModel):
    run_id: int
    task_id: int
    cut_id: int | None = None
    status: Literal["source_ready", "failed"]
    source: VisualEvidencePin
    raw: VisualEvidencePin | None = None
    mapped: VisualEvidencePin | None = None
    attempt_receipt: str | None = None
    error: str | None = None


class VisualGroupMember(VisualRequestResult):
    selection: VisualSelection


class VisualGroupResult(BaseModel):
    run_id: int
    cut_id: int | None = None
    status: Literal["source_ready", "failed"]
    source: VisualEvidencePin
    members: tuple[VisualGroupMember, ...]


def retained_visual_scope(options, selection):
    if "visual_group" not in options:
        return options.get("visual_request")
    scope = VisualSelection.model_validate(selection).scope()
    return scope if scope in options["visual_group"]["selections"] else None


_METHOD = OperationDescriptor(
    "native.source_request",
    "5",
    "normalize",
    "deterministic",
    TaskUnitType.DOCUMENT,
    VisualRequestConfig,
)


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
    pdf_context_for_release(conn, archive).execution.require_operation("read_native_source")
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


def _original_loader(engine, original: RetainedPdfOriginal):
    @cache
    def load() -> bytes:
        with engine.connect() as conn:
            return _read_visual_original(conn, original)

    return load


def _selection_region(reader, selection):
    region = None
    if selection.pointer is not None and selection.region_index is not None:
        region = reader.region(selection.pointer, selection.region_index)
        if region["page_no"] != selection.page_no:
            raise ValueError("visual request crop belongs to another physical page")
    return region


def _load_selection(conn, selection: VisualSelection):
    project, document, original, reader = _load_visual_source(conn, selection.source)
    return (
        project,
        document,
        _read_visual_original(conn, original),
        _selection_region(reader, selection),
    )


def _open_observation(conn, pin: VisualEvidencePin, project_id: str, selection: VisualSelection):
    """Verify an exact raw pin, its direct structural edge and immutable bytes."""
    products, bodies, tasks, runs = map(
        table, ("ops.pdf_product", "ops.pdf_product_body", "ops.task", "ops.run")
    )
    row = conn.execute(
        select(
            products.c.release_id,
            products.c.artifact_digest,
            bodies.c.payload,
            runs.c.options,
            table("ops.method_config").c.params["selection"].label("selection"),
        )
        .join(
            bodies,
            (bodies.c.task_id == products.c.task_id)
            & (bodies.c.product_key == products.c.product_key),
        )
        .join(tasks, tasks.c.id == products.c.task_id)
        .join(
            table("ops.method_config"), table("ops.method_config").c.id == tasks.c.method_config_id
        )
        .join(runs, runs.c.id == tasks.c.run_id)
        .where(
            products.c.task_id == pin.task_id,
            products.c.product_key == pin.product_key,
            products.c.content_digest == pin.content_digest,
            products.c.kind == "recognition_observation",
            products.c.release_id == runs.c.release_id,
            runs.c.id == pin.run_id,
            runs.c.project_id == project_id,
        )
    ).one_or_none()
    if row is None or _digest(payload := bytes(row.payload)) != pin.content_digest:
        raise ValueError("visual replay requires an exact retained raw observation")
    origin = retained_visual_scope(row.options, row.selection)
    if (
        not isinstance(origin, dict)
        or VisualSelection.model_validate(origin).scope() != selection.scope()
    ):
        raise ValueError("visual replay differs from the originating source selection")
    archive = open_release(conn, row.release_id)
    context = pdf_context_for_release(conn, archive)
    body = context.boundary.validate_json("PdfObservationProduct", payload).model_dump(
        mode="json", exclude_none=True
    )
    structural = {"role": "structural", **_reference(selection.source).values()}
    obs = body["observation"]
    if (
        body["inputs"] != [structural]
        or body["artifact_digest"] != row.artifact_digest
        or obs["binding"]["provider"] != _PROVIDER
        or obs["pass_role"] != ("chandra_crop" if selection.pointer else "chandra_page")
        or obs["image"]["page_no"] != selection.page_no
        or "mapped_evidence_digest" in obs
    ):
        raise ValueError("visual replay does not identify the exact raw Chandra request")
    attached, artifacts = map(table, ("ops.pdf_product_artifact", "kb.source_artifact"))

    def content(digest):
        value = conn.execute(
            select(artifacts.c.content)
            .join(attached, attached.c.artifact_digest == artifacts.c.artifact_digest)
            .where(
                attached.c.task_id == pin.task_id,
                attached.c.product_key == pin.product_key,
                attached.c.artifact_digest == digest,
            )
        ).scalar_one_or_none()
        if value is None or _digest(data := bytes(value)) != digest:
            raise ValueError("visual replay artifact differs from the retained raw observation")
        return data

    raw_digest = obs.get("raw_response_digest")
    if raw_digest is None:
        raise ValueError("raw observation has no retained response to replay")
    return body, content(obs["image"]["artifact_digest"]), content(raw_digest)


def _recognition_recipe(selection, original, runtime_identity):
    from pypdfium2.version import PDFIUM_INFO, PYPDFIUM_INFO

    return {
        "version": _INFERENCE_RECIPE_VERSION,
        "selection": selection.scope(),
        "runtime": runtime_identity,
        "original_digest": original.digest,
        "render_policy": _RENDER_POLICY,
        "crop_policy": _CROP_POLICY,
        "renderer": {"pypdfium2": str(PYPDFIUM_INFO), "pdfium": str(PDFIUM_INFO)},
    }


def _recognition_basis(recipe):
    return {
        key: value
        for key, value in recipe.items()
        if key not in {"submitted_png_digest", "transform"}
    }


def _compatible_raw(conn, project, selection, original, recipe):
    """Resolve a settled raw result by its actual recognition determinants."""
    inputs, products, tasks, runs, configs, bodies, attachments, artifacts = map(
        table,
        (
            "ops.pdf_product_input",
            "ops.pdf_product",
            "ops.task",
            "ops.run",
            "ops.method_config",
            "ops.pdf_product_body",
            "ops.pdf_product_artifact",
            "kb.source_artifact",
        ),
    )
    observation = bodies.c.descriptor["observation"]
    image = observation["image"]
    raw_attachment = attachments.alias("raw_attachment")
    raw_artifact = artifacts.alias("raw_artifact")
    has_raw_response = (
        select(raw_attachment.c.artifact_digest)
        .join(raw_artifact, raw_artifact.c.artifact_digest == raw_attachment.c.artifact_digest)
        .where(
            raw_attachment.c.task_id == products.c.task_id,
            raw_attachment.c.product_key == products.c.product_key,
            raw_attachment.c.artifact_digest == observation["raw_response_digest"].as_string(),
            func.octet_length(raw_artifact.c.content) > 0,
        )
        .exists()
    )
    retained_transform = cast(func.convert_from(artifacts.c.content, "UTF8"), JSONB).op("->")(
        "transform"
    )
    candidate = conn.execute(
        select(
            runs.c.id.label("run_id"),
            products.c.task_id,
            products.c.product_key,
            products.c.content_digest,
            bodies.c.recipe_digest,
            artifacts.c.content,
            image["artifact_digest"].as_string().label("png_digest"),
            (retained_transform == image["transform"]).label("transform_matches"),
        )
        .select_from(inputs)
        .join(
            products,
            and_(
                products.c.task_id == inputs.c.task_id,
                products.c.product_key == inputs.c.product_key,
            ),
        )
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
            attachments,
            and_(
                attachments.c.task_id == products.c.task_id,
                attachments.c.product_key == products.c.product_key,
                attachments.c.artifact_digest == bodies.c.recipe_digest,
            ),
        )
        .join(artifacts, artifacts.c.artifact_digest == attachments.c.artifact_digest)
        .where(
            inputs.c.input_task_id == selection.source.task_id,
            inputs.c.input_product_key == selection.source.product_key,
            inputs.c.input_content_digest == selection.source.content_digest,
            inputs.c.role == "structural",
            runs.c.project_id == project,
            tasks.c.status.in_(("done", "empty")),
            tasks.c.unit_key == products.c.product_key,
            products.c.product_key.startswith("chandra-inference:"),
            products.c.artifact_digest == original.digest,
            configs.c.params["selection"] == selection.model_dump(mode="json"),
            # Provider completion standing stays with the observation. An
            # unspecified stop can still have exact settled response bytes.
            observation["outcome"].as_string().in_(("succeeded", "unknown")),
            has_raw_response,
            observation["binding"]["decoding_json"]
            .as_string()
            .cast(JSONB)["recognition_digest"]
            .as_string()
            == _digest(canonical_bytes(recipe)),
            func.octet_length(artifacts.c.content) <= 256 * 1024,
        )
        .order_by(products.c.task_id)
        .limit(1)
    ).one_or_none()
    if candidate is None:
        return None
    retained = bytes(candidate.content)
    if _digest(retained) != candidate.recipe_digest:
        raise OperationConflict("retained visual recognition recipe differs from its digest")
    retained_recipe = json.loads(retained)
    if (
        canonical_bytes(_recognition_basis(retained_recipe)) != canonical_bytes(recipe)
        or retained_recipe.get("submitted_png_digest") != candidate.png_digest
        or candidate.transform_matches is not True
    ):
        raise OperationConflict("retained visual recognition recipe differs from its exact inputs")
    return VisualEvidencePin(
        run_id=candidate.run_id,
        task_id=candidate.task_id,
        product_key=candidate.product_key,
        content_digest=candidate.content_digest,
    )


def _prediction_details(
    prediction, runtime, recipe, claim, invocation_error: str | None
) -> tuple[dict[str, Any], bytes | None]:
    from docling.datamodel.base_models import VlmStopReason
    from pydantic_core import to_jsonable_python

    raw = prediction.text.encode() if prediction is not None else None
    stop = prediction.stop_reason if prediction is not None else None
    error = None
    if prediction is None:
        outcome = "failed"
        error = invocation_error or "Chandra invocation ended without a prediction"
    elif stop in (VlmStopReason.INFERENCE_ERROR, VlmStopReason.CONTENT_FILTERED):
        outcome = "failed"
        error = prediction.error_message or f"Chandra stopped with {stop.value}"
    elif not raw or not raw.strip():
        outcome, error = "failed", "Chandra did not return response text"
    elif stop == VlmStopReason.END_OF_SEQUENCE:
        outcome = "succeeded"
    elif stop is None or stop == VlmStopReason.UNSPECIFIED:
        outcome, error = "unknown", "Chandra did not report a completion reason"
    else:
        outcome, error = "partial", f"Chandra stopped with {stop.value}"
    identity = recipe["runtime"]
    artifacts = identity["artifacts_sha256"]
    observation = {
        "outcome": outcome,
        "binding": dict(
            provider=_PROVIDER,
            package_identity=";".join(
                f"{name}=={version}" for name, version in sorted(identity["packages"].items())
            ),
            source_identity=f"{identity['repository']}@{identity['revision']}",
            weights_digest=artifacts["model.safetensors"],
            tokenizer_digest=artifacts["tokenizer.json"],
            prompt_digest=_digest(identity["prompt"].encode()),
            decoding_json=canonical_bytes(
                {
                    "decode": identity["decode"],
                    "effective_device": runtime.effective_device,
                    "inference_recipe_digest": _digest(canonical_bytes(recipe)),
                    "recognition_digest": _digest(canonical_bytes(_recognition_basis(recipe))),
                    "provider_attempt": {
                        "run_id": claim.run_id,
                        "task_id": claim.task_id,
                        "invocation_key": claim.invocation_key,
                        "attempt": claim.attempt,
                    },
                }
            ).decode(),
            seed="unreported",
            render_policy=_RENDER_POLICY,
            crop_policy=_CROP_POLICY,
            merge_policy="alternatives",
        ),
        "usage_availability": "unavailable",
    }
    if stop is not None:
        observation["finish_reason"] = stop.value
    if raw is not None:
        observation["raw_response_digest"] = _digest(raw)
    if error is not None:
        observation["diagnostic"] = error[:1800]
    if prediction is not None and prediction.usage is not None:
        usage = to_jsonable_python(prediction.usage)
        observation["usage_json"] = canonical_bytes(
            usage if isinstance(usage, dict) else {"reported": usage}
        ).decode()
        observation["usage_availability"] = "available"
    return observation, raw


def _retain_attempt_receipt(
    root: Path,
    claim: ClaimedTask,
    recipe: bytes,
    payload: dict[str, Any],
    pixels: bytes,
    raw: bytes | None,
    *,
    interrupted: bool,
) -> tuple[Path, bytes]:
    """Publish the local receipt marker only after its attempt-owned bytes are durable."""
    from corpus_structure.ingest.pdf_streaming import _atomic_bytes

    directory = _attempt_directory(root, claim, claim.attempt)
    directory.mkdir(parents=True, mode=0o700)
    values = {
        "recipe.json": recipe,
        "observation.json": canonical_bytes(payload),
        "submitted.png": pixels,
    }
    if raw is not None:
        values["response.html"] = raw
    files = {
        name: {"sha256": ref.digest, "byte_length": ref.byte_length}
        for name, content in values.items()
        for ref in (_atomic_bytes(directory / name, content, "chandra-attempt"),)
    }
    manifest = canonical_bytes(
        {
            "version": "chandra-attempt-receipt-v1",
            "run_id": claim.run_id,
            "task_id": claim.task_id,
            "release_id": claim.release_id,
            "invocation_key": claim.invocation_key,
            "attempt": claim.attempt,
            "interrupted": interrupted,
            "files": files,
        }
    )
    marker = directory / "receipt.json"
    _atomic_bytes(marker, manifest, "chandra-attempt")
    return marker, manifest


def _attempt_directory(root: Path, claim: ClaimedTask, attempt: int) -> Path:
    invocation = _digest(claim.invocation_key.encode())
    return (
        root
        / "chandra"
        / f"run-{claim.run_id}-task-{claim.task_id}-{invocation}"
        / (f"attempt-{attempt}")
    )


def _recover_attempt_receipt(root, claim, selection, original, recipe, context):
    """Read a complete prior response, retaining its actual provider attempt."""
    for attempt in range(claim.attempt - 1, 0, -1):
        directory = _attempt_directory(root, claim, attempt)
        marker = directory / "receipt.json"
        if not marker.exists():
            continue
        if marker.is_symlink() or marker.stat().st_size > 8192:
            raise OperationConflict("invalid visual attempt receipt marker")
        manifest = marker.read_bytes()
        body = json.loads(manifest)
        provenance = {
            "run_id": claim.run_id,
            "task_id": claim.task_id,
            "invocation_key": claim.invocation_key,
            "attempt": attempt,
        }
        if any(body.get(key) != value for key, value in provenance.items()) or (
            body.get("release_id") != claim.release_id
            or body.get("version") != "chandra-attempt-receipt-v1"
        ):
            raise OperationConflict("visual attempt receipt belongs to another claim")
        files = body.get("files")
        required = {"observation.json", "recipe.json", "submitted.png"}
        if not isinstance(files, dict) or set(files) not in (
            required,
            required | {"response.html"},
        ):
            raise OperationConflict("visual attempt receipt file inventory differs")
        recovered = {}
        for name, expected in files.items():
            path = directory / name
            limit = 96 * 1024 * 1024 if name == "submitted.png" else _MAX_REPLAY_BYTES
            if path.is_symlink() or path.stat().st_size > limit:
                raise OperationConflict("invalid retained visual attempt artifact")
            data = path.read_bytes()
            if expected != {"sha256": _digest(data), "byte_length": len(data)}:
                raise OperationConflict("visual attempt receipt artifact differs from its hash")
            recovered[name] = data
        if recovered["recipe.json"] != recipe:
            raise OperationConflict(
                "visual attempt receipt recipe differs from the claimed request"
            )
        raw = recovered.get("response.html")
        if raw is None:
            continue
        payload = context.boundary.validate_json(
            "PdfObservationProduct", recovered["observation.json"]
        ).model_dump(mode="json", exclude_none=True)
        pixels = recovered["submitted.png"]
        observation = payload["observation"]
        image = observation["image"]
        settings = json.loads(recipe)
        decoding = json.loads(observation["binding"]["decoding_json"])
        if (
            payload["product_key"] != claim.unit_key
            or payload["recipe_digest"] != _digest(recipe)
            or payload["artifact_digest"] != original.digest
            or payload["inputs"]
            != [{"role": "structural", **_reference(selection.source).values()}]
            or observation["binding"]["provider"] != _PROVIDER
            or observation["pass_role"] != ("chandra_crop" if selection.pointer else "chandra_page")
            or "mapped_evidence_digest" in observation
            or observation.get("raw_response_digest") != _digest(raw)
            or image["page_no"] != selection.page_no
            or image["artifact_digest"] != _digest(pixels)
            or image["artifact_digest"] != settings["submitted_png_digest"]
            or image["transform"] != settings["transform"]
            or decoding.get("inference_recipe_digest") != _digest(recipe)
            or decoding.get("provider_attempt") != provenance
        ):
            raise OperationConflict("retained visual attempt differs from its source or recipe")
        return marker, manifest, payload, pixels, raw
    return None


def _product(
    selection,
    original,
    key,
    recipe,
    observation,
    *,
    mapping="unknown",
    detail,
    coverage,
    raw_pin=None,
    mapped=None,
) -> dict[str, Any]:
    inputs = [{"role": "structural", **_reference(selection.source).values()}]
    if raw_pin is not None:
        inputs.append({"role": "recognition", **_reference(raw_pin).values()})
    if mapped is not None:
        observation = {**observation, "mapped_evidence_digest": _digest(mapped)}
    return dict(
        version=1,
        kind="recognition_observation",
        product_key=key,
        artifact_digest=original.digest,
        recipe_digest=_digest(recipe),
        observation=observation,
        inputs=inputs,
        occurrences=[],
        relations=[],
        health=dict(
            execution_outcome=observation["outcome"],
            mapping_outcome=mapping,
            source_fidelity="unassessed",
            validation_report=detail,
        ),
        coverage=[
            dict(
                coverage_id="visual-observation",
                scope=f"page:{selection.page_no}",
                family=observation["pass_role"],
                discovery_policy="explicit-chandra-request-v1",
                outcome=coverage,
                detail=detail,
            )
        ],
    )


def _start_task(
    conn,
    run_id,
    prepared,
    document_id,
    selection,
    step,
    recipe,
    holder,
    *,
    grouped=False,
    replay: VisualEvidencePin | None = None,
):
    params = VisualRequestConfig(step=step, selection=selection, recipe_digest=_digest(recipe))
    values = params.model_dump(mode="json")
    configuration = _digest(canonical_bytes(values))
    config_id = record_method(conn, _METHOD, step, values, configuration, prepared=prepared)
    key = f"chandra-{step}:{params.recipe_digest}"
    tasks = table("ops.task")
    retained = _visual_task(conn, run_id, step, selection if grouped else None)
    if retained is None:
        task_id = create_task(
            conn,
            run_id=run_id,
            config_id=config_id,
            stage="parsing",
            unit_type="document",
            unit_id=document_id,
            unit_key=key,
            input_hash=params.recipe_digest,
            trigger={"visual_raw": replay.model_dump(mode="json")} if replay is not None else None,
        )
    else:
        if retained.unit_key != key or retained.method_config_id != config_id:
            raise OperationConflict("visual resume differs from the retained task recipe")
        task_id = retained.id
    task = conn.execute(
        select(tasks.c.status, tasks.c.reused_task_id).where(tasks.c.id == task_id)
    ).one()
    if task.status in {"done", "empty", "reused"}:
        return (
            task_id,
            key,
            configuration,
            None,
            _task_product_pin(conn, task.reused_task_id or task_id, key),
        )
    claims = claim_tasks(conn, run_id=run_id, config_id=config_id, holder=holder, prepared=prepared)
    if len(claims) != 1 or claims[0].task_id != task_id:
        raise OperationConflict("visual task is terminal or its previous claim has not expired")
    return task_id, key, configuration, claims[0], None


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


def _settle(
    engine,
    owner,
    claim: ClaimedTask,
    prepared,
    context,
    configuration,
    original,
    recipe,
    *,
    payload=None,
    artifacts=(),
    detail=None,
    error=None,
):
    assert claim.unit_key is not None
    prepared_product = (
        prepare_integrated_pdf_product(
            payload, original, recipe, artifacts=artifacts, context=context
        )
        if payload is not None
        else None
    )
    with read_snapshot(engine) as conn:
        terminal = prepare_unit_completion(
            conn,
            task_id=claim.task_id,
            attempt=claim.attempt,
            holder=claim.holder,
            prepared=prepared,
            result=UnitResult(
                ref=UnitRef(TaskUnitType.DOCUMENT, claim.unit_id, claim.unit_key),
                outcome=ObservationOutcome.FAILED if error else ObservationOutcome.EMPTY,
                error=error,
                parse_detail=detail,
            ),
            method=_METHOD,
            configuration_hash=configuration,
            source=claim.unit_key,
        )

    def complete(conn):
        digest = None
        if payload is not None and prepared_product is not None:
            products = table("ops.pdf_product")
            published = conn.execute(
                select(products.c.content_digest).where(
                    products.c.task_id == claim.task_id,
                    products.c.product_key == payload["product_key"],
                )
            ).scalar_one_or_none()
            if published is None:
                digest = store_pdf_observation(
                    conn,
                    task_id=claim.task_id,
                    attempt=claim.attempt,
                    holder=claim.holder,
                    product=prepared_product,
                    context=context,
                )
            else:
                # A commit retry must replay terminal custody under the same attempt.
                if published != prepared_product.digest:
                    raise ValueError("visual observation settlement differs from retained bytes")
                digest = published
        terminal.apply(conn)
        return digest

    return owner.settle(claim, complete)


def _bind_visual_run(
    conn, project_id, semantic_release, realization, *, recognize, options, resume_run_id
):
    from .runtime_bindings import require_installed_runtime

    realizations = table("data.realization")
    revision = conn.execute(
        select(realizations.c.data_revision).where(
            realizations.c.realization_id == realization,
            realizations.c.project_id == project_id,
            realizations.c.release_id == semantic_release,
            realizations.c.state == "active",
        )
    ).scalar_one_or_none()
    if revision is None:
        raise ValueError(
            "visual effect requires an active realization of the release in the source project"
        )
    prepared = open_release(conn, semantic_release)
    context = pdf_context_for_release(conn, prepared)
    context.execution.require_operation("publish_pdf_observation")
    if recognize:
        context.execution.require_operation("recognize_chandra_observation")
    installed = require_installed_runtime(prepared)
    if resume_run_id is None:
        run_id = create_run(
            conn,
            project_id=project_id,
            binding=OperationBinding(
                semantic_release,
                realization,
                revision,
                canonical_bytes({"visual_request": "chandra-observation-v1"}),
            ),
            kind="slice",
            options=options,
            code_commit=VISUAL_REQUEST_CODE_COMMIT,
            prepared=prepared,
            runtime_binding=installed,
        )
    else:
        run_id = resume_run_id
        retained = _visual_run(conn, run_id)
        if (
            retained is None
            or retained.project_id != project_id
            or retained.release_id != semantic_release
            or retained.runtime_id != installed.runtime_id
            or retained.input_realization_id != realization
            or retained.input_revision != revision
            or retained.options != options
        ):
            raise OperationConflict("visual resume differs from its retained run binding")
    return run_id, prepared, context, installed


def _activate_visual_run(engine, supervisor, run_id):
    from corpus_structure.orchestrate.liveness import record_supervisor

    runs = table("ops.run")
    with engine.connect() as conn:
        current = conn.execute(
            select(runs.c.status, runs.c.sealed).where(runs.c.id == run_id)
        ).one()
    if current.sealed or current.status not in {"created", "running"}:
        raise OperationConflict("visual request run is terminal")
    record_supervisor(supervisor, run_id, waiting=False)
    supervisor.commit()


def request_visual_observation(
    engine: Engine,
    *,
    selection: VisualSelection,
    semantic_release: str,
    realization: str,
    receipts: Path,
    artifacts: Path | None = None,
    replay: VisualEvidencePin | None = None,
    nemotron_endpoint: str | None = None,
    holder: str = "visual-source-request",
    resume_run_id: int | None = None,
) -> VisualRequestResult:
    from corpus_structure.orchestrate.liveness import (
        run_supervisor,
        supervisor_connection,
    )

    if not semantic_release or not realization:
        raise ValueError("visual request requires an explicit semantic release and realization")
    if (artifacts is None) == (replay is None):
        raise ValueError("select either pinned Chandra artifacts or one exact raw observation")
    raw_body: dict[str, Any] | None = None
    pixels: bytes | None = None
    raw: bytes | None = None
    recovery = {
        "artifacts": str(artifacts.resolve()) if artifacts is not None else None,
        "replay": replay.model_dump(mode="json") if replay is not None else None,
    }
    options = {"visual_request": selection.scope(), "visual_recovery": recovery}
    with (
        supervisor_connection(engine) as supervisor,
        _source_supervisor(supervisor, selection.source),
    ):
        with engine.begin() as conn:
            project_id, document_id, original, reader = _load_visual_source(conn, selection.source)
            region = _selection_region(reader, selection)
            if replay is not None:
                raw_body, pixels, raw = _open_observation(conn, replay, project_id, selection)
                if raw_body["artifact_digest"] != original.digest:
                    raise ValueError("visual replay original differs from the selected PDF")
            run_id, prepared, context, installed = _bind_visual_run(
                conn,
                project_id,
                semantic_release,
                realization,
                recognize=artifacts is not None,
                options=options,
                resume_run_id=resume_run_id,
            )
        with run_supervisor(supervisor, run_id):
            _activate_visual_run(engine, supervisor, run_id)
            if resume_run_id is not None and artifacts is not None:
                with engine.connect() as conn:
                    task = _visual_task(conn, run_id, "inference")
                    if task is not None and task.status in {"done", "empty", "reused"}:
                        replay = _task_product_pin(
                            conn, task.reused_task_id or task.id, task.unit_key
                        )
                        raw_body, pixels, raw = _open_observation(
                            conn, replay, project_id, selection
                        )
                        if raw_body["artifact_digest"] != original.digest:
                            raise OperationConflict("retained visual response original differs")
                        artifacts = None
            return _execute_visual_request(
                engine,
                run_id,
                selection,
                prepared,
                installed,
                context,
                project_id,
                document_id,
                original,
                region,
                receipts,
                artifacts,
                replay,
                nemotron_endpoint,
                holder,
                raw_body,
                pixels,
                raw,
                load_original=_original_loader(engine, original),
            )


@contextmanager
def _source_supervisor(conn, source: VisualEvidencePin):
    """Fence simultaneous acquisition of the same exact source's requests."""
    lock_id = int.from_bytes(
        sha256(b"chandra-source:" + canonical_bytes(source.model_dump(mode="json"))).digest()[:8],
        signed=True,
    )
    if not conn.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": lock_id}):
        raise OperationConflict("the exact PDF source already has an active visual request")
    try:
        yield
    finally:
        try:
            if not conn.invalidated:
                conn.rollback()
                conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": lock_id})
        except Exception:
            conn.invalidate()


class _GroupInference:
    def __init__(self, artifacts, endpoint, lifetime):
        self.artifacts = artifacts
        self.endpoint = endpoint
        self.lifetime = lifetime
        self._runtime = None
        self._child = None
        self._recognize = None
        self._page = None
        self._identity = None

    def runtime(self):
        from corpus_structure.ingest.pdf_chandra import ChandraRuntime

        if self._runtime is None:
            self._runtime = ChandraRuntime(self.artifacts)
        return self._runtime

    def recognition_identity(self):
        from corpus_structure.ingest.pdf_chandra import chandra_recognition_identity

        if self._identity is None:
            self._identity = chandra_recognition_identity()
        return self._identity

    def render(self, load_original, page_no, region, rotation):
        from .pdf_visual_mapping import _prepare_visual_page

        if self._page is None or self._page.page_no != page_no:
            self._page = None
            self._page = _prepare_visual_page(load_original(), page_no)
        return self._page.submit(region, rotation)

    def recognize(self, pixels, *, check_active, before_submit):
        from corpus_structure.ingest.pdf_capacity import suspend_resident_nemotron
        from corpus_structure.ingest.pdf_chandra import ChandraWorkerLost, supervised_chandra

        if self._child is None:
            self.lifetime.enter_context(
                suspend_resident_nemotron(self.endpoint, check_active=check_active)
            )
            self._child = self.lifetime.enter_context(ExitStack())
        if self._recognize is None:
            self._recognize = self._child.enter_context(supervised_chandra(self.runtime()))
        try:
            return self._recognize(pixels, check_active=check_active, before_submit=before_submit)
        except ChandraWorkerLost:
            # Retain the failed member and let subsequent members use a fresh child.
            self._recognize = None
            self._child.close()
            raise


def request_visual_group(
    engine: Engine,
    *,
    selections: tuple[VisualSelection, ...],
    semantic_release: str,
    realization: str,
    receipts: Path,
    artifacts: Path,
    nemotron_endpoint: str | None = None,
    holder: str = "visual-source-request",
    resume_run_id: int | None = None,
    campaign_group: str | None = None,
    nomination_run_id: int | None = None,
) -> VisualGroupResult:
    """Run a finite group, optionally recovering a retained campaign demand."""
    from corpus_structure.orchestrate.liveness import (
        run_supervisor,
        supervisor_connection,
    )

    if not 1 <= len(selections) <= MAX_VISUAL_GROUP:
        raise ValueError(f"visual groups require 1 to {MAX_VISUAL_GROUP} selections")
    source = selections[0].source
    scopes = [selection.scope() for selection in selections]
    if any(selection.source != source for selection in selections):
        raise ValueError("visual group selections must share one exact published PDF")
    if len({canonical_bytes(scope) for scope in scopes}) != len(scopes):
        raise ValueError("visual group selections must be distinct")
    selections = tuple(VisualSelection.model_validate(scope) for scope in scopes)
    options: dict[str, Any] = {
        "visual_group": {"version": VISUAL_GROUP_VERSION, "selections": scopes},
        "visual_recovery": {"artifacts": str(artifacts.resolve()), "replay": None},
    }
    if campaign_group is not None:
        if re.fullmatch(r"[0-9a-f]{64}", campaign_group) is None:
            raise ValueError("visual campaign group requires a SHA-256 key")
        options["visual_campaign_group"] = campaign_group
    if nomination_run_id is not None:
        options["visual_nomination_run_id"] = nomination_run_id
    with supervisor_connection(engine) as supervisor, _source_supervisor(supervisor, source):
        with engine.begin() as conn:
            project_id, document_id, original, reader = _load_visual_source(conn, source)
            if nomination_run_id is not None:
                _require_group_nomination(
                    conn, nomination_run_id, project_id, semantic_release, realization, scopes
                )
            if campaign_group is not None:
                retained_id = _campaign_group_run(conn, project_id, source, campaign_group)
                if resume_run_id is not None and resume_run_id != retained_id:
                    raise OperationConflict("visual resume does not own the campaign group")
                if retained_id is None:
                    _require_no_pending_group_overlap(conn, project_id, selections)
                else:
                    resume_run_id = retained_id
                    retained = _visual_run(conn, retained_id)
                    if (
                        retained is None
                        or retained.release_id != semantic_release
                        or retained.input_realization_id != realization
                        or retained.options != options
                    ):
                        raise OperationConflict(
                            "visual request differs from the retained campaign group"
                        )
                    settled = _settled_campaign_group(
                        conn, retained_id, retained, selections, project_id
                    )
                    if settled is not None:
                        return settled
            regions = tuple(_selection_region(reader, selection) for selection in selections)
            run_id, prepared, context, installed = _bind_visual_run(
                conn,
                project_id,
                semantic_release,
                realization,
                recognize=True,
                options=options,
                resume_run_id=resume_run_id,
            )
        with run_supervisor(supervisor, run_id):
            _activate_visual_run(engine, supervisor, run_id)
            members = []
            with ExitStack() as lifetime:
                group = _GroupInference(artifacts, nemotron_endpoint, lifetime)
                load_original = _original_loader(engine, original)
                for selection, region in zip(selections, regions, strict=True):
                    replay = raw_body = pixels = raw = None
                    with engine.connect() as conn:
                        inference = _visual_task(conn, run_id, "inference", selection)
                        mapping = _visual_task(conn, run_id, "mapping", selection)
                        settled = _settled_group_member(
                            conn, run_id, selection, project_id, inference, mapping
                        )
                        if (
                            settled is None
                            and inference is not None
                            and inference.status in {"done", "empty", "reused"}
                        ):
                            replay = _task_product_pin(
                                conn, inference.reused_task_id or inference.id, inference.unit_key
                            )
                        elif settled is None and mapping is not None:
                            replay = _visual_mapping_raw_pin(conn, mapping, selection, project_id)
                            if replay is None:
                                raise OperationConflict(
                                    "retained mapping has no qualified raw input"
                                )
                        elif settled is None and inference is None:
                            try:
                                identity = group.recognition_identity()
                            except OSError, RuntimeError, ValueError:
                                identity = None
                            if identity is not None:
                                replay = _compatible_raw(
                                    conn,
                                    project_id,
                                    selection,
                                    original,
                                    _recognition_recipe(selection, original, identity),
                                )
                        if replay is not None:
                            raw_body, pixels, raw = _open_observation(
                                conn, replay, project_id, selection
                            )
                            if raw_body["artifact_digest"] != original.digest:
                                raise OperationConflict("retained visual response original differs")
                    if settled is None:
                        settled = _execute_visual_request(
                            engine,
                            run_id,
                            selection,
                            prepared,
                            installed,
                            context,
                            project_id,
                            document_id,
                            original,
                            region,
                            receipts,
                            artifacts if replay is None else None,
                            replay,
                            nemotron_endpoint,
                            holder,
                            raw_body,
                            pixels,
                            raw,
                            load_original=load_original,
                            group=group,
                        )
                    members.append(VisualGroupMember(selection=selection, **settled.model_dump()))
            with engine.begin() as conn:
                failed = any(member.status == "failed" for member in members)
                cut_id = None
                if failed:
                    end_source_run(
                        conn,
                        run_id,
                        failure={"message": "one or more visual members failed"},
                        prepared=prepared,
                    )
                    runs = table("ops.run")
                    status = conn.execute(
                        select(runs.c.status).where(runs.c.id == run_id)
                    ).scalar_one()
                    if status == "cancelled":
                        raise OperationConflict(f"visual group run {run_id} was cancelled")
                    if status != "failed":
                        raise OperationConflict(
                            f"visual group run {run_id} did not settle as failed"
                        )
                else:
                    cut_id = seal_cut(conn, run_id, VISUAL_REQUEST_CUT, final=True)
            return VisualGroupResult(
                run_id=run_id,
                cut_id=cut_id,
                source=source,
                status="failed" if failed else "source_ready",
                members=tuple(members),
            )


def _require_group_nomination(conn, nomination, project, release, realization, scopes):
    runs = table("ops.run")
    options = conn.scalar(
        select(runs.c.options).where(
            runs.c.id == nomination,
            runs.c.project_id == project,
            runs.c.release_id == release,
            runs.c.input_realization_id == realization,
            runs.c.code_commit == VISUAL_REQUEST_CODE_COMMIT,
            runs.c.sealed,
        )
    )
    retained = options.get("visual_nomination") if options else None
    if (
        retained is None
        or retained.get("version") != VISUAL_NOMINATION_VERSION
        or any(scope not in retained["selections"] for scope in scopes)
    ):
        raise OperationConflict("visual group differs from the frozen nomination")


def _campaign_group_run(conn, project_id, source, key):
    """Find the demand while holding the exact source supervisor lock."""
    runs = table("ops.run")
    return conn.execute(
        select(runs.c.id).where(
            runs.c.project_id == project_id,
            runs.c.code_commit == VISUAL_REQUEST_CODE_COMMIT,
            runs.c.options.contains(
                {
                    "visual_campaign_group": key,
                    "visual_group": {
                        "selections": [{"source": source.model_dump(mode="json")}],
                    },
                }
            ),
        )
    ).scalar_one_or_none()


def _require_no_pending_group_overlap(conn, project_id, selections):
    """Reserve pending members independently of campaign grouping under the source lock."""
    source = selections[0].source
    runs, cuts = map(table, ("ops.run", "ops.input_cut"))
    final = select(cuts.c.id).where(cuts.c.run_id == runs.c.id, cuts.c.final).exists()
    pending = conn.execute(
        select(runs.c.id, runs.c.options).where(
            runs.c.project_id == project_id,
            runs.c.code_commit == VISUAL_REQUEST_CODE_COMMIT,
            runs.c.status.in_(("created", "running")),
            ~runs.c.sealed,
            ~final,
            runs.c.options["visual_campaign_group"].astext.is_not(None),
            runs.c.options.contains(
                {"visual_group": {"selections": [{"source": source.model_dump(mode="json")}]}},
            ),
        )
    )
    for run_id, options in pending:
        for selection in selections:
            if selection.scope() in options["visual_group"]["selections"]:
                inference = _visual_task(conn, run_id, "inference", selection)
                mapping = _visual_task(conn, run_id, "mapping", selection)
                if (
                    _settled_group_member(conn, run_id, selection, project_id, inference, mapping)
                    is None
                ):
                    raise OperationConflict(
                        f"exact visual selection has a pending campaign demand in run {run_id}"
                    )


def _settled_campaign_group(conn, run_id, retained, selections, project_id):
    if retained.status == "cancelled":
        raise OperationConflict(f"visual campaign group run {run_id} was cancelled")
    cuts = table("ops.input_cut")
    cut_id = conn.scalar(
        select(cuts.c.id).where(
            cuts.c.run_id == run_id, cuts.c.name == VISUAL_REQUEST_CUT, cuts.c.final
        )
    )
    if cut_id is None and retained.status in {"created", "running"} and not retained.sealed:
        return None
    source = selections[0].source
    members = []
    for selection in selections:
        inference = _visual_task(conn, run_id, "inference", selection)
        mapping = _visual_task(conn, run_id, "mapping", selection)
        settled = _settled_group_member(conn, run_id, selection, project_id, inference, mapping)
        if settled is None:
            raise OperationConflict(f"terminal visual group run {run_id} lacks a settled member")
        members.append(VisualGroupMember(selection=selection, **settled.model_dump()))
    failed = any(member.status == "failed" for member in members)
    if (cut_id is None and (retained.status != "failed" or not failed)) or (
        cut_id is not None and (retained.status == "failed" or failed)
    ):
        raise OperationConflict(f"terminal visual group run {run_id} has inconsistent custody")
    return VisualGroupResult(
        run_id=run_id,
        cut_id=cut_id,
        source=source,
        status="failed" if failed else "source_ready",
        members=tuple(members),
    )


def _settled_group_member(conn, run_id, selection, project_id, inference, mapping):
    task = mapping or inference
    if task is None:
        return None
    if task.status == "failed":
        return VisualRequestResult(
            run_id=run_id,
            task_id=task.id,
            source=selection.source,
            status="failed",
            raw=_visual_product_pin(conn, inference)
            or _visual_mapping_raw_pin(conn, mapping, selection, project_id),
            mapped=_visual_product_pin(conn, mapping),
            error=(task.error or {}).get("message") or task.reason or "visual member failed",
        )
    if mapping is not None and mapping.status in {"done", "empty", "reused"}:
        raw = _visual_product_pin(conn, inference) or _visual_mapping_raw_pin(
            conn, mapping, selection, project_id
        )
        mapped = _visual_product_pin(conn, mapping)
        if raw is None or mapped is None:
            raise OperationConflict("settled visual member lacks its exact product pins")
        return VisualRequestResult(
            run_id=run_id,
            task_id=mapping.id,
            source=selection.source,
            status="source_ready",
            raw=raw,
            mapped=mapped,
        )
    return None


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


def _visual_run(conn, run_id: int):
    runs = table("ops.run")
    row = conn.execute(
        select(
            runs.c.project_id,
            runs.c.release_id,
            runs.c.runtime_id,
            runs.c.input_realization_id,
            runs.c.input_revision,
            runs.c.options,
            runs.c.status,
            runs.c.sealed,
        ).where(runs.c.id == run_id, runs.c.code_commit == VISUAL_REQUEST_CODE_COMMIT)
    ).one_or_none()
    return (
        row
        if row is not None and ("visual_request" in row.options or "visual_group" in row.options)
        else None
    )


def resume_visual_observation(
    engine: Engine,
    run_id: int,
    *,
    project: str,
    receipts: Path,
    nemotron_endpoint: str | None,
    prepare_only: bool,
    select_result: bool,
    activate_release: bool,
) -> VisualRequestResult | VisualGroupResult | None:
    """Dispatch only runs owned by the visual request operation."""
    with engine.connect() as conn:
        retained = _visual_run(conn, run_id)
    if retained is None:
        return None
    if retained.project_id != project:
        raise OperationConflict("resume run has another project")
    if prepare_only or select_result or activate_release:
        raise OperationConflict("visual resume accepts only the retained recognition effect")
    recovery = retained.options.get("visual_recovery")
    if recovery is None:
        raise OperationConflict("legacy visual run has no retained recovery binding")
    if group := retained.options.get("visual_group"):
        if group["version"] != VISUAL_GROUP_VERSION:
            raise OperationConflict("unsupported retained visual group version")
        return request_visual_group(
            engine,
            selections=tuple(
                VisualSelection.model_validate(value) for value in group["selections"]
            ),
            semantic_release=retained.release_id,
            realization=retained.input_realization_id,
            receipts=receipts,
            artifacts=Path(recovery["artifacts"]),
            nemotron_endpoint=nemotron_endpoint,
            resume_run_id=run_id,
            campaign_group=retained.options.get("visual_campaign_group"),
            nomination_run_id=retained.options.get("visual_nomination_run_id"),
        )
    return request_visual_observation(
        engine,
        selection=VisualSelection.model_validate(retained.options["visual_request"]),
        semantic_release=retained.release_id,
        realization=retained.input_realization_id,
        receipts=receipts,
        artifacts=Path(recovery["artifacts"]) if recovery["artifacts"] is not None else None,
        replay=VisualEvidencePin.model_validate(recovery["replay"])
        if recovery["replay"] is not None
        else None,
        nemotron_endpoint=nemotron_endpoint,
        resume_run_id=run_id,
    )


def _execute_visual_request(
    engine,
    run_id,
    selection,
    prepared,
    installed,
    context,
    project_id,
    document_id,
    original,
    region,
    receipts,
    artifacts,
    replay,
    nemotron_endpoint,
    holder,
    raw_body,
    pixels,
    raw,
    *,
    load_original,
    group=None,
):
    from PIL import Image

    from corpus_structure.ingest.pdf_capacity import pdf_gpu_slot, suspend_resident_nemotron
    from corpus_structure.ingest.pdf_chandra import (
        ChandraRuntime,
        chandra_parser_identity,
        parse_chandra_response,
        recognize_supervised,
    )

    from .claim_lifetime import maintained_claims
    from .pdf_visual_mapping import map_visual_result, render_visual_input

    raw_pin = replay
    mapped_pin = None
    attempt_receipt = None
    try:
        if artifacts is not None:
            error: str | None = None
            recipe: dict[str, Any] = {
                "version": _INFERENCE_RECIPE_VERSION,
                "selection": selection.scope(),
            }
            runtime = None
            transform = None
            try:
                runtime = ChandraRuntime(artifacts) if group is None else group.runtime()
                if group is None:
                    pixels, transform = render_visual_input(
                        load_original(), selection.page_no, region, selection.rotation or 0
                    )
                else:
                    pixels, transform = group.render(
                        load_original, selection.page_no, region, selection.rotation or 0
                    )
                recipe = dict(
                    _recognition_recipe(selection, original, runtime.identity()),
                    submitted_png_digest=_digest(pixels),
                    transform=transform,
                )
            except (OSError, RuntimeError, ValueError) as exc:
                error = str(exc)[:1800] or type(exc).__name__
                recipe["preparation_failed"] = True
            inference = canonical_bytes(recipe)
            with engine.begin() as conn:
                task_id, key, configuration, claim, raw_pin = _start_task(
                    conn,
                    run_id,
                    prepared,
                    document_id,
                    selection,
                    "inference",
                    inference,
                    holder,
                    grouped=group is not None,
                )
                if raw_pin is not None:
                    raw_body, pixels, raw = _open_observation(conn, raw_pin, project_id, selection)
            if claim is not None:
                with maintained_claims(engine, (claim,), holder) as owner:
                    payload, retained = None, ()
                    detail: dict[str, Any] = {"stage": "inference"}
                    recovered = _recover_attempt_receipt(
                        receipts, claim, selection, original, inference, context
                    )
                    if recovered is not None:
                        marker, manifest, payload, pixels, raw = recovered
                        observation = payload["observation"]
                        attempt_receipt = str(marker)
                        detail["attempt_receipt_digest"] = _digest(manifest)
                        raw_body, retained = payload, (pixels, manifest, raw)
                        if observation["outcome"] == "failed":
                            error = observation["diagnostic"]
                    elif error is None:
                        assert pixels is not None and transform is not None and runtime is not None
                        prediction = None
                        submitted = False
                        interruption = None
                        image_size = None
                        next_check = 0.0

                        def active():
                            nonlocal next_check
                            owner()
                            if monotonic() >= next_check:
                                runs = table("ops.run")
                                with engine.connect() as conn:
                                    status = conn.scalar(
                                        select(runs.c.status).where(runs.c.id == run_id)
                                    )
                                if status not in {"created", "running"}:
                                    raise OperationConflict(
                                        "visual inference run is no longer active"
                                    )
                                next_check = monotonic() + 1

                        def mark_submission():
                            nonlocal submitted
                            active()
                            submitted = True

                        try:
                            with Image.open(BytesIO(pixels)) as image:
                                image_size = image.size
                            if group is not None:
                                prediction = group.recognize(
                                    pixels, check_active=active, before_submit=mark_submission
                                )
                            else:
                                with (
                                    pdf_gpu_slot(check_active=active),
                                    suspend_resident_nemotron(
                                        nemotron_endpoint, check_active=active
                                    ),
                                ):
                                    prediction = recognize_supervised(
                                        runtime,
                                        pixels,
                                        check_active=active,
                                        before_submit=mark_submission,
                                    )
                        except (KeyboardInterrupt, OperationConflict) as exc:
                            interruption = exc
                            error = "Chandra request interrupted"
                        except Exception as exc:
                            error = str(exc)[:1800] or type(exc).__name__
                        if submitted:
                            assert image_size is not None
                            observation, raw = _prediction_details(
                                prediction, runtime, recipe, claim, error
                            )
                            observation.update(
                                pass_role="chandra_crop" if selection.pointer else "chandra_page",
                                image=dict(
                                    artifact_digest=_digest(pixels),
                                    page_no=selection.page_no,
                                    width=image_size[0],
                                    height=image_size[1],
                                    encoding="png",
                                    precision=transform["status"],
                                    transform=transform,
                                ),
                            )
                            if observation["outcome"] == "failed" and error is None:
                                error = observation["diagnostic"]
                            payload = _product(
                                selection,
                                original,
                                key,
                                inference,
                                observation,
                                detail="Provider attempt retained. Source fidelity is unassessed.",
                                coverage=(
                                    "capped"
                                    if observation.get("finish_reason") == "length"
                                    else "unknown"
                                ),
                            )
                            marker, manifest = _retain_attempt_receipt(
                                receipts,
                                claim,
                                inference,
                                payload,
                                pixels,
                                raw,
                                interrupted=interruption is not None,
                            )
                            attempt_receipt = str(marker)
                            detail["attempt_receipt_digest"] = _digest(manifest)
                            raw_body, retained = payload, (pixels, manifest)
                            if raw is not None:
                                retained += (raw,)
                        if interruption is not None:
                            raise interruption
                    detail["observation"] = payload is not None
                    digest = _settle(
                        engine,
                        owner,
                        claim,
                        prepared,
                        context,
                        configuration,
                        original,
                        inference,
                        payload=payload,
                        artifacts=retained,
                        detail=detail,
                        error=error,
                    )
                    if digest is not None:
                        raw_pin = VisualEvidencePin(
                            run_id=run_id, task_id=task_id, product_key=key, content_digest=digest
                        )
                if error is not None:
                    if group is None:
                        with engine.begin() as conn:
                            end_source_run(
                                conn, run_id, failure={"message": error}, prepared=prepared
                            )
                    return VisualRequestResult(
                        run_id=run_id,
                        task_id=task_id,
                        status="failed",
                        source=selection.source,
                        raw=raw_pin,
                        attempt_receipt=attempt_receipt,
                        error=error,
                    )
        assert (
            raw_pin is not None and raw_body is not None and raw is not None and pixels is not None
        )
        mapping = canonical_bytes(
            {
                "version": "chandra-mapping-v2",
                "selection": selection.scope(),
                "raw": raw_pin.model_dump(mode="json"),
                "parser": chandra_parser_identity(),
                "runtime_id": installed.runtime_id,
            }
        )
        with engine.begin() as conn:
            task_id, key, configuration, claim, mapped_pin = _start_task(
                conn,
                run_id,
                prepared,
                document_id,
                selection,
                "mapping",
                mapping,
                holder,
                grouped=group is not None,
                replay=raw_pin if group is not None else None,
            )
        error = None
        if claim is not None:
            with maintained_claims(engine, (claim,), holder) as owner:
                observation = raw_body["observation"]
                image = observation["image"]
                size = (image["width"], image["height"])
                mapped = payload = None
                parse_detail: dict[str, Any] = {"stage": "mapping"}
                try:
                    owner()
                    if len(raw) > _MAX_REPLAY_BYTES:
                        raise ValueError("retained Chandra response exceeds the parser byte limit")
                    parsed = parse_chandra_response(
                        raw.decode(),
                        image_size=size,
                        page_no=selection.page_no,
                        stop_reason=observation.get("finish_reason"),
                    )
                    parse_detail.update(
                        status=parsed.status.value,
                        completion=parsed.completion.value,
                        issues=[issue.value for issue in parsed.issues],
                    )
                    if parsed.document is None:
                        error = parsed.error or f"Chandra parse outcome was {parsed.status.value}"
                    else:
                        mapped = map_visual_result(
                            parsed.document,
                            page_no=selection.page_no,
                            transform=image["transform"],
                            image_size=size,
                        ).artifact_bytes()
                    payload = _product(
                        selection,
                        original,
                        key,
                        mapping,
                        observation,
                        mapping=(
                            "unknown"
                            if mapped is None
                            else "partial"
                            if parsed.issues
                            else "coarse"
                        ),
                        detail=canonical_bytes(parse_detail).decode(),
                        coverage="capped" if parsed.completion.value == "length" else "partial",
                        raw_pin=raw_pin,
                        mapped=mapped,
                    )
                except Exception as exc:
                    error = str(exc)[:1800] or type(exc).__name__
                retained = (pixels, raw) if mapped is None else (pixels, raw, mapped)
                digest = _settle(
                    engine,
                    owner,
                    claim,
                    prepared,
                    context,
                    configuration,
                    original,
                    mapping,
                    payload=payload,
                    artifacts=retained,
                    detail=parse_detail,
                    error=error,
                )
                if digest is not None:
                    mapped_pin = VisualEvidencePin(
                        run_id=run_id, task_id=task_id, product_key=key, content_digest=digest
                    )
        cut_id = None
        if group is None:
            with engine.begin() as conn:
                if error is None:
                    cut_id = seal_cut(conn, run_id, VISUAL_REQUEST_CUT, final=True)
                else:
                    end_source_run(conn, run_id, failure={"message": error}, prepared=prepared)
        return VisualRequestResult(
            run_id=run_id,
            task_id=task_id,
            cut_id=cut_id,
            status="source_ready" if error is None else "failed",
            source=selection.source,
            raw=raw_pin,
            mapped=mapped_pin,
            attempt_receipt=attempt_receipt,
            error=error,
        )
    except BaseException as exc:
        if attempt_receipt is not None:
            exc.add_note(f"visual provider receipt retained at {attempt_receipt}")
        exc.add_note(f"inspect visual run {run_id} before resuming or cancelling it")
        raise
