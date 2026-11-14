"""Genuine archived PDF rendering custody; mathematical analysis uses native demands."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Engine, select

from corpus_structure.core.method import CoverageDraft, UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType

from .identity import canonical_bytes
from .metadata import table
from .operation_results import MethodConfigId, RunId
from .operations import (
    OperationBinding,
    OperationDescriptor,
    binding_of,
    claim_tasks,
    create_run,
    create_task,
    end_source_run,
    record_method,
    seal_cut,
)
from .source_views import load_source_view, selected_source_views, store_region_artifact

if TYPE_CHECKING:
    from sqlalchemy import Connection

    from .runtime_bindings import RuntimeBinding
    from .types import PreparedRelease


def prepare_native_renderer(
    conn: Connection,
    prepared: PreparedRelease,
    *,
    runtime_binding: RuntimeBinding | None = None,
) -> dict[str, str]:
    """Qualify the installed renderer under a separate exact runtime binding."""
    from .contracts import bound_execution_model
    from .runtime_bindings import require_installed_runtime

    model = bound_execution_model(prepared)
    model.require_operation("publish_pdf_region_artifact")
    runtime = require_installed_runtime(prepared, runtime_binding)
    libraries = json.loads(runtime.input("libraries.json").content)
    return dict(
        implementation_digest=runtime.input("pdf/regions.py").digest,
        **{name: libraries[name] for name in ("pypdfium2", "Pillow")},
    )


class NativeRequestLimits(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)
    seconds: float = Field(default=2, gt=0)
    scale: float = Field(default=2, gt=0, le=8)


class NativeRequestConfig(NativeRequestLimits):
    source_view_id: int = Field(gt=0)
    native_product: dict[str, Any]
    projection_digest: str
    recipe_digest: str
    demand: Literal["render"]
    pointer: str | None = None
    region_index: int | None = Field(default=None, ge=0)
    ancestor_context: str = "{}"
    renderer: dict[str, str] | None = None


@dataclass(frozen=True)
class NativeRequestResult:
    run_id: int
    task_id: int
    cut_id: int | None
    status: str
    source_view_id: int
    product_digest: str | None = None
    artifact_digest: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


def request_source_view(
    engine: Engine,
    *,
    source_run_id: int,
    source_view_id: int,
    demand: Literal[
        "lexical", "structure", "syntax", "interpretation", "symbolic", "assessment", "render"
    ],
    code_commit: str,
    pointer: str | None = None,
    seconds: float = 2,
    region_index: int | None = None,
    scale: float = 2,
    holder: str = "native-source-request",
    writer_release: str | None = None,
    writer_realization: str | None = None,
) -> NativeRequestResult:
    if demand != "render":
        raise ValueError(
            "mathematical analysis requires an explicit NativeDemandRequest and native demand execution"
        )
    if (writer_release is None) != (writer_realization is None):
        raise ValueError("an explicit render writer requires both release and realization")
    if writer_release is not None and demand != "render":
        raise ValueError("a separate writer release is available only for rendering")

    from .claim_lifetime import maintained_claims
    from .contracts import require_bound_operation
    from .releases import open_release
    from .runtime_bindings import require_installed_runtime

    limits = NativeRequestLimits(seconds=seconds, scale=scale)
    seconds, scale = limits.seconds, limits.scale
    if demand == "render" and (pointer is None or region_index is None):
        raise ValueError("render requires native occurrence and region index")
    runs, tasks = table("ops.run"), table("ops.task")
    archived_cut = None
    archived_region = None
    view = None
    with engine.begin() as conn:
        origin = conn.execute(select(runs).where(runs.c.id == source_run_id)).mappings().one()
        source_archive = open_release(conn, origin["release_id"])
        prepared = source_archive if writer_release is None else open_release(conn, writer_release)
        require_bound_operation(prepared, "request_native_source")
        if not conn.execute(
            select(table("ops.run_source_view").c.source_view_id).where(
                table("ops.run_source_view").c.run_id == source_run_id,
                table("ops.run_source_view").c.source_view_id == source_view_id,
            )
        ).scalar_one_or_none():
            raise ValueError("native source request requires an explicitly selected source view")
        source_binding = binding_of(conn, source_run_id)
        target_binding = source_binding
        if writer_release is not None:
            dependencies = {"native_render_source": source_run_id}
            if writer_release != origin["release_id"] and origin["status"] != "finished":
                cuts = table("ops.input_cut")
                ready = cuts.alias("source_ready")
                archived_cut = conn.scalar(
                    select(cuts.c.id).where(
                        cuts.c.run_id == source_run_id,
                        cuts.c.release_id == origin["release_id"],
                        cuts.c.source_revision == origin["input_revision"],
                        cuts.c.final,
                        origin["sealed"] and origin["status"] == "consolidating",
                        select(ready.c.id)
                        .where(
                            ready.c.run_id == cuts.c.run_id,
                            ready.c.release_id == cuts.c.release_id,
                            ready.c.source_revision == cuts.c.source_revision,
                            ready.c.name == "source-ready",
                        )
                        .exists(),
                    )
                )
                if archived_cut is None:
                    raise ValueError("cross-release rendering requires a sealed source-ready cut")
                dependencies["native_render_cut"] = archived_cut
            realizations = table("data.realization")
            revision = conn.execute(
                select(realizations.c.data_revision).where(
                    realizations.c.realization_id == writer_realization,
                    realizations.c.project_id == origin["project_id"],
                    realizations.c.release_id == writer_release,
                    realizations.c.state == "active",
                )
            ).scalar_one_or_none()
            if revision is None:
                raise ValueError(
                    "render writer must be an active realization of the source project"
                )
            assert writer_realization is not None
            target_binding = OperationBinding(
                writer_release,
                writer_realization,
                revision,
                canonical_bytes(dependencies),
            )
        if archived_cut is not None:
            from .pdf_record_reader import published_record_reader

            refs = selected_source_views(conn, source_run_id, source_view_id=source_view_id)
            views = table("kb.source_view")
            if not refs or not conn.scalar(
                select(views.c.id).where(
                    views.c.id == source_view_id, views.c.projection["items"].has_key(pointer)
                )
            ):
                raise ValueError("render pointer is outside the selected archived source view")
            reference = refs[0]
            published = published_record_reader(
                conn, reference.native_product, projection_context=source_archive
            )
            if published is None:
                raise ValueError("archive has no published record-backed source")
            assert pointer is not None and region_index is not None
            archived_region = published.region(pointer, region_index)
        else:
            view = load_source_view(conn, source_view_id, analysis=False)
            reference = view.ref
        runtime_binding = require_installed_runtime(prepared)
        renderer = prepare_native_renderer(conn, prepared, runtime_binding=runtime_binding)
    config = NativeRequestConfig(
        source_view_id=source_view_id,
        native_product=reference.native_product.values(),
        projection_digest=reference.projection_digest,
        recipe_digest=reference.recipe_digest,
        demand=demand,
        pointer=pointer,
        seconds=seconds,
        region_index=region_index,
        scale=scale,
        renderer=renderer,
    )
    from .pdf_contracts import pdf_context_for_release

    with engine.connect() as conn:
        pdf_context_for_release(conn, prepared).boundary.validate_json(
            "PdfNativeAnalysisRequest", config.model_dump_json(exclude_none=True)
        )
    params = config.model_dump(mode="json")
    digest = sha256(canonical_bytes(params)).hexdigest()
    unit = (
        UnitRef(TaskUnitType.DOCUMENT, reference.document_id, "native-archive-render:" + digest)
        if archived_cut is not None
        else UnitRef(TaskUnitType.SOURCE_VIEW, source_view_id, "native-request:" + digest)
    )
    method = OperationDescriptor(
        "native.source_request",
        "6" if archived_cut is not None else "5",
        "normalize",
        "deterministic",
        unit.unit_type,
        NativeRequestConfig,
    )
    with engine.begin() as conn:
        run_id = create_run(
            conn,
            project_id=origin["project_id"],
            binding=target_binding,
            kind="slice",
            options={"native_request": params},
            code_commit=code_commit,
            prepared=prepared,
            runtime_binding=runtime_binding,
        )
        if archived_cut is None:
            from ._operation_calls import select_source_view
            from ._operation_ids import SourceViewId

            select_source_view(
                conn,
                run_id=run_id,
                source_run_id=RunId(source_run_id),
                source_view_id=SourceViewId(source_view_id),
                projection_context=prepared,
            )
        config_id = record_method(conn, method, "request", params, digest, prepared=prepared)
        task_id = create_task(
            conn,
            run_id=run_id,
            config_id=config_id,
            stage="parsing",
            unit_type=unit.unit_type,
            unit_id=unit.unit_id,
            unit_key=unit.unit_key,
            input_hash=digest,
        )
        reused = conn.execute(
            select(tasks.c.reused_task_id).where(tasks.c.id == task_id)
        ).scalar_one()
        if reused is not None:
            body = conn.execute(
                select(table("ops.task_result").c.body).where(
                    table("ops.task_result").c.task_id == reused
                )
            ).scalar_one()
            result = None
            artifact = conn.execute(
                select(table("ops.native_region_artifact").c.artifact_digest).where(
                    table("ops.native_region_artifact").c.task_id == reused
                )
            ).scalar_one_or_none()
            if demand == "render" and artifact is None:
                raise ValueError("reused render task has no protected artifact")
            cut = seal_cut(conn, run_id, "native-request-source", final=True)
            return NativeRequestResult(
                run_id,
                task_id,
                cut,
                "source_ready",
                source_view_id,
                sha256(canonical_bytes(body)).hexdigest(),
                artifact,
                result,
            )
        claim = claim_tasks(
            conn,
            run_id=RunId(run_id),
            config_id=MethodConfigId(config_id),
            holder=holder,
            prepared=prepared,
        )[0]
    try:
        with maintained_claims(engine, (claim,), holder) as owner:
            from .operations import prepare_unit_completion
            from .query import read_snapshot

            with read_snapshot(engine) as conn:
                region: dict[str, Any] | None = None
                original = None
                if demand == "render":
                    from .pdf_record_reader import published_record_reader

                    published = published_record_reader(
                        conn, reference.native_product, projection_context=source_archive
                    )
                    if published is None:
                        raise ValueError(
                            "current rendering requires a published record-backed source"
                        )
                    if pointer is None or region_index is None:
                        raise ValueError(
                            "render requires an exact published pointer and region index"
                        )
                    region = (
                        archived_region
                        if archived_region is not None
                        else published.region(pointer, region_index)
                    )
                    build, artifact = table("ops.source_build"), table("kb.source_artifact")
                    original = bytes(
                        conn.execute(
                            select(artifact.c.content)
                            .join(build, build.c.artifact_digest == artifact.c.artifact_digest)
                            .where(
                                build.c.task_id == reference.native_product.task_id,
                                build.c.artifact_digest == published.revision["source_digest"],
                            )
                        ).scalar_one()
                    )
                    if sha256(original).hexdigest() != published.revision["source_digest"]:
                        raise ValueError("render original differs from the archived PDF digest")

            def terminal_intent(result):
                with read_snapshot(engine) as preparation_conn:
                    return prepare_unit_completion(
                        preparation_conn,
                        task_id=task_id,
                        attempt=claim.attempt,
                        holder=holder,
                        prepared=prepared,
                        result=result,
                        method=method,
                        configuration_hash=digest,
                        source=reference.key,
                    )

            owner()
            artifact_bytes = None
            from corpus_structure.serve.native_regions import render_pdf_region

            assert original is not None and region is not None
            artifact_bytes = render_pdf_region(original, region, scale=scale)
            owner()
            result = UnitResult(
                ref=unit,
                outcome=ObservationOutcome.EMPTY,
                coverage=(
                    CoverageDraft(
                        family=method.name,
                        scope=reference.key,
                        outcome="complete",
                        required_capability="render",
                    ),
                ),
            )
            with engine.begin() as conn:
                artifact_digest = None
                if artifact_bytes is not None:
                    selection = dict(
                        reference.native_product.values(),
                        pointer=pointer,
                        region_index=region_index,
                    )
                    recipe = canonical_bytes(
                        dict(
                            recipe="pdf-region-render-v2",
                            selection=selection,
                            scale=scale,
                            renderer=renderer,
                        )
                    )
                    artifact_digest = store_region_artifact(
                        conn,
                        task_id=task_id,
                        attempt=claim.attempt,
                        holder=holder,
                        selection=selection,
                        recipe_bytes=recipe,
                        content=artifact_bytes,
                    )
            owner.settle(claim, terminal_intent(result).apply)
        with engine.begin() as conn:
            cut = seal_cut(conn, run_id, "native-request-source", final=True)
            body = conn.execute(
                select(table("ops.task_result").c.body).where(
                    table("ops.task_result").c.task_id == task_id
                )
            ).scalar_one()
        return NativeRequestResult(
            run_id,
            task_id,
            cut,
            "source_ready",
            source_view_id,
            sha256(canonical_bytes(body)).hexdigest(),
            artifact_digest,
            None,
        )
    except BaseException as error:
        try:
            with engine.begin() as conn:
                end_source_run(
                    conn,
                    RunId(run_id),
                    failure={"message": str(error), "exception": type(error).__name__},
                    prepared=prepared,
                )
        except BaseException as cleanup:
            error.add_note("native request failure settlement failed: " + repr(cleanup))
        raise
