"""Owned, bounded preparation of original cross-source pins and exact passages."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated

from pydantic import Field
from sqlalchemy import select

from .metadata import table
from .pdf_record_reader import PublishedReadBudget
from .query import read_snapshot
from .source_views import load_source_view, selected_source_views
from .structural_products import ExternalSourceRef, Nonempty, Positive, StructuralPassage, StructuralValue


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


def prepare_structural_sources(engine, selections: Sequence[StructuralPassageSelection], *, read_budget: PublishedReadBudget | None = None, cancellation=None) -> PreparedStructuralSources:
    """Authenticate each original view once, settle its snapshot, then return values.

    A consumed passage is an exact projected excerpt. Source health/pieces remain
    available through its original immutable source view and the review closure.
    """
    if not selections or len(selections)>256:
        raise ValueError("structural source selection requires 1..256 explicit passages")
    if len({s.passage_id for s in selections})!=len(selections):
        raise ValueError("duplicate structural passage selection")
    budget = read_budget if read_budget is not None else PublishedReadBudget(max_rows=100_000,max_bytes=64*1024*1024)
    refs: dict[tuple[int,int],ExternalSourceRef]={}
    views={}
    passages=[]
    run, completed, batch = table("ops.run"), table("ops.completed_result"), table("data.batch")
    with read_snapshot(engine,cancellation=cancellation) as conn:
        for selection in selections:
            if cancellation is not None:
                cancellation.check_active()
            key=(selection.run_id,selection.source_view_id)
            if key not in refs:
                original=conn.execute(select(run.c.project_id,run.c.release_id,run.c.sealed,run.c.status,completed.c.cut_id,batch.c.data_revision).select_from(run.join(completed,completed.c.run_id==run.c.id).join(batch,(batch.c.release_id==completed.c.release_id)&(batch.c.realization_id==completed.c.output_realization_id)&(batch.c.batch_id==completed.c.batch_id))).where(run.c.id==selection.run_id)).mappings().one()
                if not original["sealed"] or original["status"]!="finished":
                    raise ValueError("structural source must name a completed original run")
                selected=selected_source_views(conn,selection.run_id,read_budget=budget,source_view_id=selection.source_view_id)
                if len(selected)!=1:
                    raise ValueError("structural passage view is not selected in its original run")
                view=load_source_view(conn,selection.source_view_id,analysis=False,read_budget=budget)
                views[key]=view
                native=view.ref.native_product
                refs[key]=ExternalSourceRef(project_id=original["project_id"],run_id=selection.run_id,cut_id=original["cut_id"],release_id=original["release_id"],result_revision=original["data_revision"],source_view_id=view.ref.id,native_task_id=native.task_id,native_product_key=native.product_key,native_content_digest=native.content_digest,projection_digest=view.ref.projection_digest,recipe_digest=view.ref.recipe_digest,coordinate_version=3 if view.integrated_context is not None else 2)
            view=views[key]
            if not 0<=selection.start<selection.end<=len(view.text):
                raise ValueError("structural passage outside original projected text")
            passages.append(StructuralPassage(passage_id=selection.passage_id,source_ref=refs[key].identity,start=selection.start,end=selection.end,text=view.text[selection.start:selection.end],scope=selection.scope,effective_version=selection.effective_version,parent=selection.parent))
    return PreparedStructuralSources(tuple(refs.values()),tuple(passages))
