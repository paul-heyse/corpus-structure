"""Owned, bounded preparation of original cross-source pins and exact passages."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from sqlalchemy import select

from .metadata import table
from .pdf_record_reader import PublishedReadBudget
from .query import read_snapshot
from .source_views import load_source_view, selected_source_views
from .structural_products import (
    ExternalSourceRef,
    Nonempty,
    Positive,
    StructuralPassage,
    StructuralValue,
)

if TYPE_CHECKING:
    from corpus_structure.ingest.annotations import AnnotationProduct

    from .proposals import NativeProposalFrame


class StructuralPassageSelection(StructuralValue):
    run_id: Positive
    source_view_id: Positive
    passage_id: Nonempty
    start: Annotated[int, Field(strict=True, ge=0)]
    end: Positive
    scope: Nonempty
    effective_version: str | None = None
    parent: str | None = None


@dataclass(frozen=True)
class PreparedStructuralSources:
    sources: tuple[ExternalSourceRef, ...]
    passages: tuple[StructuralPassage, ...]


def prepare_structural_sources(
    engine,
    selections: Sequence[StructuralPassageSelection],
    *,
    read_budget: PublishedReadBudget | None = None,
    cancellation=None,
) -> PreparedStructuralSources:
    """Authenticate each original view once, settle its snapshot, then return values.

    A consumed passage is an exact projected excerpt. Source health/pieces remain
    available through its original immutable source view and the review closure.
    """
    if not selections or len(selections) > 256:
        raise ValueError("structural source selection requires 1..256 explicit passages")
    if len({s.passage_id for s in selections}) != len(selections):
        raise ValueError("duplicate structural passage selection")
    budget = (
        read_budget
        if read_budget is not None
        else PublishedReadBudget(max_rows=100_000, max_bytes=64 * 1024 * 1024)
    )
    refs: dict[tuple[int, int], ExternalSourceRef] = {}
    views = {}
    passages = []
    run, completed, batch = table("ops.run"), table("ops.completed_result"), table("data.batch")
    with read_snapshot(engine, cancellation=cancellation) as conn:
        for selection in selections:
            if cancellation is not None:
                cancellation.check_active()
            key = (selection.run_id, selection.source_view_id)
            if key not in refs:
                original = (
                    conn.execute(
                        select(
                            run.c.project_id,
                            run.c.release_id,
                            run.c.sealed,
                            run.c.status,
                            completed.c.cut_id,
                            batch.c.data_revision,
                        )
                        .select_from(
                            run.join(completed, completed.c.run_id == run.c.id).join(
                                batch,
                                (batch.c.release_id == completed.c.release_id)
                                & (batch.c.realization_id == completed.c.output_realization_id)
                                & (batch.c.batch_id == completed.c.batch_id),
                            )
                        )
                        .where(run.c.id == selection.run_id)
                    )
                    .mappings()
                    .one()
                )
                if not original["sealed"] or original["status"] != "finished":
                    raise ValueError("structural source must name a completed original run")
                selected = selected_source_views(
                    conn,
                    selection.run_id,
                    read_budget=budget,
                    source_view_id=selection.source_view_id,
                )
                if len(selected) != 1:
                    raise ValueError("structural passage view is not selected in its original run")
                view = load_source_view(
                    conn, selection.source_view_id, analysis=False, read_budget=budget
                )
                views[key] = view
                native = view.ref.native_product
                refs[key] = ExternalSourceRef(
                    project_id=original["project_id"],
                    run_id=selection.run_id,
                    cut_id=original["cut_id"],
                    release_id=original["release_id"],
                    result_revision=original["data_revision"],
                    source_view_id=view.ref.id,
                    native_task_id=native.task_id,
                    native_product_key=native.product_key,
                    native_content_digest=native.content_digest,
                    projection_digest=view.ref.projection_digest,
                    recipe_digest=view.ref.recipe_digest,
                    coordinate_version=3 if view.integrated_context is not None else 2,
                )
            view = views[key]
            if not 0 <= selection.start < selection.end <= len(view.text):
                raise ValueError("structural passage outside original projected text")
            passages.append(
                StructuralPassage(
                    passage_id=selection.passage_id,
                    source_ref=refs[key].identity,
                    start=selection.start,
                    end=selection.end,
                    text=view.text[selection.start : selection.end],
                    scope=selection.scope,
                    effective_version=selection.effective_version,
                    parent=selection.parent,
                )
            )
    return PreparedStructuralSources(tuple(refs.values()), tuple(passages))


@dataclass(frozen=True)
class PreparedStructuralAnnotations:
    """Detached current-format linguistic products under their original source custody."""

    source: NativeProposalFrame
    annotations: tuple[AnnotationProduct, ...]
    errors: tuple[str, ...]
    annotation_task_id: int | None
    annotation_input_hash: str | None


def load_structural_annotations(conn, inputs, source_ref, profile, *, read_budget=None):
    """Read an original source and annotation task from the same authenticated final cut.

    This consumes unchanged source/annotation formats. It opens no historical semantic
    release and supplies no compatibility interpretation of an old semantic result.
    """
    from sqlalchemy import func

    from corpus_structure.ingest.annotations import restore_annotations

    from .observations import source_python
    from .proposals import native_source_frame
    from .source_contexts import NativeSourcePin

    source = next((source for source in inputs.sources if source.identity == source_ref), None)
    if source is None:
        raise ValueError("structural annotation source lies outside authenticated inputs")
    budget = (
        read_budget if read_budget is not None else PublishedReadBudget(100_000, 64 * 1024 * 1024)
    )
    view = load_source_view(conn, source.source_view_id, analysis=False, read_budget=budget)
    frame = native_source_frame(view, ())
    task, origin, result, membership, config, method = (
        table("ops.task"),
        table("ops.task").alias("annotation_origin"),
        table("ops.task_result"),
        table("ops.cut_task"),
        table("ops.method_config"),
        table("ops.method"),
    )
    query = (
        select(
            task.c.id.label("selected_task_id"),
            origin.c.id.label("origin_task_id"),
            origin.c.release_id,
            origin.c.unit_key,
            origin.c.input_hash,
            config.c.config_hash,
            method.c.version,
            result.c.body,
        )
        .select_from(membership)
        .join(task, task.c.id == membership.c.task_id)
        .join(origin, origin.c.id == func.coalesce(task.c.reused_task_id, task.c.id))
        .join(result, result.c.task_id == origin.c.id)
        .join(config, config.c.id == origin.c.method_config_id)
        .join(method, method.c.id == config.c.method_id)
        .where(
            membership.c.cut_id == source.cut_id,
            task.c.run_id == source.run_id,
            task.c.unit_type == "source_view",
            task.c.unit_id == source.source_view_id,
            task.c.status.in_(("done", "reused")),
            membership.c.origin_task_id == origin.c.id,
            method.c.name == "extract.m1_annotations",
        )
    )
    budget.preflight(conn, query)
    rows = tuple(conn.execute(query).mappings())
    if not rows:
        return PreparedStructuralAnnotations(
            frame, (), ("original cut has no retained linguistic annotation product",), None, None
        )
    if len(rows) != 1:
        raise ValueError("original cut has ambiguous linguistic annotation products")
    row = rows[0]
    body = row["body"]
    budget.value(body)
    if (
        row["release_id"] != source.release_id
        or body.get("release_id") != row["release_id"]
        or body.get("source") != frame.unit_ref
        or body.get("method") != "extract.m1_annotations"
        or body.get("operation_version") != row["version"]
        or body.get("unit_key") != row["unit_key"]
        or body.get("input_hash") != row["input_hash"]
        or body.get("configuration_hash") != row["config_hash"]
    ):
        raise ValueError("original annotation result differs from its native task custody")
    if row["version"] != "2":
        return PreparedStructuralAnnotations(
            frame,
            (),
            (
                f"Authenticated retained annotation operation version {row['version']} "
                "is unsupported; current annotation contract is version2. "
                "No historical decoder executed.",
            ),
            row["origin_task_id"],
            row["input_hash"],
        )
    details = source_python(body["parse_detail"])
    if details.get("recipe") != "m1-owned-linguistic-product-1" or details.get(
        "source_pin"
    ) != asdict(NativeSourcePin.from_source(frame)):
        raise ValueError("original annotation source or recipe differs")
    products = restore_annotations(details["annotations"], source=frame, profile=profile)
    errors = tuple(details.get("annotation_errors", ()))
    if body.get("outcome") == "failed" and not errors:
        errors = ("original annotation operation failed",)
    return PreparedStructuralAnnotations(
        frame, products, errors, row["origin_task_id"], row["input_hash"]
    )
