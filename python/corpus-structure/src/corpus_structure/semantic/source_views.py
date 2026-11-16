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

if TYPE_CHECKING:
    from corpus_structure.ingest.sentences import SentenceConfig, TextLayout
    from corpus_structure.methods.math.native_topology import NativeTopology



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
