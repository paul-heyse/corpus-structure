"""Immutable section projections and run selections over pinned native PDF products."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cached_property
from hashlib import sha256
from typing import TYPE_CHECKING, Any

from sqlalchemy import Connection, select

from corpus_structure.core.method import SourceViewDraft, SourceViewRef

from .identity import canonical_bytes
from .metadata import table
from .product_reference import ProductReference

if TYPE_CHECKING:
    from corpus_structure.ingest.sentences import SentenceConfig, TextLayout
    from corpus_structure.methods.math.native_topology import NativeTopology

    from .types import PreparedRelease


@dataclass(frozen=True)
class PreparedSourceView:
    ref: SourceViewRef
    text: str
    pieces: tuple[dict[str, Any], ...]
    items: tuple[dict[str, Any], ...]
    ancestors: tuple[dict[str, Any], ...]
    health: dict[str, Any]
    text_policy: Any = None
    analysis_enabled: bool = True
    integrated_context: dict[str, Any] | None = None

    @cached_property
    def topology(self) -> NativeTopology:
        from corpus_structure.methods.math.native_topology import prepare_native_topology

        return prepare_native_topology(self)

    @cached_property
    def layout(self) -> TextLayout:
        from corpus_structure.ingest.sentences import SentenceConfig

        return self.layout_for(SentenceConfig())

    @cached_property
    def _layouts(self) -> dict[bytes, TextLayout]:
        return {}

    def layout_for(self, configuration: SentenceConfig) -> TextLayout:
        if not self.analysis_enabled:
            raise ValueError("retained source view cannot prepare analytical layout")
        from dataclasses import asdict

        from corpus_structure.ingest.sentences import Block, pipeline, prepare_layout

        from .analysis_contracts import prepare_text_policy

        policy = self.text_policy or prepare_text_policy()
        key = canonical_bytes(
            dict(configuration=configuration.model_dump(mode="json"), policy=asdict(policy))
        )
        if key not in self._layouts:
            native = {item["self_ref"]: item for item in self.items}
            math = tuple(
                (piece["start"], piece["end"])
                for piece in self.pieces
                if piece.get("item_ref") in native
                and native[piece["item_ref"]].get("label") == "formula"
            )
            self._layouts[key] = prepare_layout(
                pipeline(configuration), Block(self.text, math, (), ()), recipe=policy.recipe
            )
        return self._layouts[key]

    def context(self) -> dict[str, Any]:
        value: dict[str, Any] = dict(
            pieces=self.pieces, items=self.items, ancestors=self.ancestors, health=self.health
        )
        if self.integrated_context is not None:
            value["integrated_context_json"] = canonical_bytes(self.integrated_context).decode()
        return value


def _ref(row) -> SourceViewRef:
    return SourceViewRef(
        row["id"],
        row["key"],
        row["document_id"],
        ProductReference(
            row["native_task_id"], row["native_product_key"], row["native_content_digest"]
        ),
        row["section_pointer"],
        row["membership"],
        row["projection_digest"],
        row["recipe_digest"],
        row["analysis_eligible"],
    )


def selected_source_views(
    conn: Connection, run_id: int, *, read_budget: Any = None, source_view_id: int | None = None
) -> tuple[SourceViewRef, ...]:
    view, selection = table("kb.source_view"), table("ops.run_source_view")
    newer = selection.alias("newer")
    statement = (
        select(
            *(
                view.c[name]
                for name in (
                    "id",
                    "key",
                    "document_id",
                    "native_task_id",
                    "native_product_key",
                    "native_content_digest",
                    "section_pointer",
                    "membership",
                    "projection_digest",
                    "recipe_digest",
                    "analysis_eligible",
                )
            )
        )
        .join(selection, selection.c.source_view_id == view.c.id)
        .where(
            selection.c.run_id == run_id,
            ~select(newer.c.source_view_id)
            .where(newer.c.run_id == run_id, newer.c.supersedes_source_view_id == view.c.id)
            .exists(),
        )
        .order_by(selection.c.position, view.c.id)
    )
    if source_view_id is not None:
        statement = statement.where(view.c.id == source_view_id)
    if read_budget is not None:
        read_budget.preflight(conn, statement)
    refs = []
    for row in conn.execute(statement).mappings():
        if read_budget is not None:
            read_budget.value(dict(row))
        refs.append(_ref(row))
    return tuple(refs)


def load_source_view(
    conn: Connection,
    source_view_id: int,
    *,
    analysis: bool = True,
    analysis_context: PreparedRelease | None = None,
    read_budget: Any = None,
) -> PreparedSourceView:
    """Keep original source custody and bind new analysis to its consuming release."""
    views = table("kb.source_view")
    statement = select(views).where(views.c.id == source_view_id)
    if read_budget is not None:
        read_budget.preflight(conn, statement)
    row = conn.execute(statement).mappings().one()
    reference = _ref(row)
    projection = row["projection"]
    if read_budget is not None:
        read_budget.value(projection)
    pointers = tuple(dict.fromkeys([*projection["items"], *projection["ancestors"]]))
    from .pdf_record_reader import published_record_reader
    from .published_document import PublishedDocumentBinding
    from .releases import open_release

    projection_context = open_release(conn, row["release_id"])
    budget_options = {} if read_budget is None else {"read_budget": read_budget}
    reader = published_record_reader(
        conn, reference.native_product, projection_context=projection_context, **budget_options
    )
    if reader is None:
        raise ValueError("current source view has no published record binding")
    binding = PublishedDocumentBinding.from_revision(reference.native_product, reader.revision)
    binding.require_placement(row)
    native = reader.selected_native_items(pointers)
    from .analysis_contracts import prepare_text_policy

    policy = prepare_text_policy(analysis_context or projection_context) if analysis else None
    from .pdf_storage import integrated_source_context

    integrated = integrated_source_context(
        conn,
        task_id=reference.native_product.task_id,
        product_key=reference.native_product.product_key,
        content_digest=reference.native_product.content_digest,
        pointers=projection["items"],
        section_pointer=reference.section_pointer,
        membership=reference.membership,
        **budget_options,
    )
    return PreparedSourceView(
        reference,
        projection["text"],
        tuple(projection["pieces"]),
        tuple(native[p] for p in projection["items"]),
        tuple(native[p] for p in projection["ancestors"]),
        projection["health"],
        policy,
        analysis,
        integrated,
    )


def store_source_view(
    conn: Connection,
    *,
    run_id: int,
    task_id: int,
    attempt: int,
    holder: str,
    draft: SourceViewDraft,
    position: int,
) -> int:
    from .contracts import require_database_operation

    run = table("ops.run")
    release = conn.execute(select(run.c.release_id).where(run.c.id == run_id)).scalar_one()
    require_database_operation(conn, release, "publish_source_view")
    payload = dict(
        key=draft.key,
        document_id=draft.document_id,
        analysis_eligible=draft.analysis_eligible,
        native_task_id=draft.native_product.task_id,
        native_product_key=draft.native_product.product_key,
        native_content_digest=draft.native_product.content_digest,
        section_pointer=draft.section_pointer,
        membership=draft.membership,
        projection_digest=draft.projection_digest,
        recipe_digest=draft.recipe_digest,
        projection=draft.projection(),
    )
    if draft.replaces_source_view_id is not None:
        payload["replaces_source_view_id"] = draft.replaces_source_view_id
    from .pdf_contracts import pdf_context_for_task

    context = pdf_context_for_task(conn, task_id)
    context.require_operation("publish_source_view")
    payload = context.boundary.validate_json(
        "PdfSourceViewPublication", json.dumps(payload)
    ).model_dump(mode="json", exclude_none=True)
    from ._operation_calls import RunId, TaskAttempt, TaskId
    from ._operation_calls import publish_source_view as invoke
    from .invariant_failures import InvariantViolation, classify_invariant_failure
    from .refusals import DATABASE_ERRORS
    from .releases import open_release

    prepared = open_release(conn, release)
    try:
        return invoke(
            conn,
            run_id=RunId(run_id),
            task_id=TaskId(task_id),
            attempt=TaskAttempt(attempt),
            holder=holder,
            position=position,
            payload=canonical_bytes(payload),
            recipe=draft.recipe_bytes,
            projection_context=prepared,
        )
    except DATABASE_ERRORS as exc:
        failure = classify_invariant_failure(
            context.domain.invariants,
            "publish_source_view",
            exc,
            model_id="pdf-domain:" + sha256(context.domain.content).hexdigest(),
            release_id=context.release_id,
        )
        if failure is not None:
            raise InvariantViolation(failure) from exc
        raise
