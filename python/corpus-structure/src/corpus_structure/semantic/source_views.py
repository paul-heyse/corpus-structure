"""Immutable section projections and run selections over pinned native PDF products."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Any

from pydantic import JsonValue
from sqlalchemy import Connection, select, text

from corpus_structure.core.method import SourceViewDraft, SourceViewRef

from .identity import canonical_bytes
from .metadata import table
from .product_reference import ProductReference

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
    conn: Connection, run_id: int, *, read_budget: Any = None
) -> tuple[SourceViewRef, ...]:
    view, selection = table("kb.source_view"), table("ops.run_source_view")
    newer = selection.alias("newer")
    statement = (
        select(*(view.c[name] for name in (
            "id", "key", "document_id", "native_task_id", "native_product_key",
            "native_content_digest", "section_pointer", "membership", "projection_digest",
            "recipe_digest", "analysis_eligible",
        )))
        .join(selection, selection.c.source_view_id == view.c.id)
        .where(
            selection.c.run_id == run_id,
            ~select(newer.c.source_view_id)
            .where(newer.c.run_id == run_id, newer.c.supersedes_source_view_id == view.c.id)
            .exists(),
        )
        .order_by(selection.c.position, view.c.id)
    )
    if read_budget is not None:
        read_budget.preflight(conn, statement)
    refs = []
    for row in conn.execute(statement).mappings():
        if read_budget is not None:
            read_budget.value(dict(row))
        refs.append(_ref(row))
    return tuple(refs)


def load_source_view(
    conn: Connection, source_view_id: int, *, analysis: bool = True, read_budget: Any = None
) -> PreparedSourceView:
    """Hydrate retained fields; analytical mode additionally binds the archived text policy."""
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

    policy = prepare_text_policy(projection_context) if analysis else None
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
            context.execution, "publish_source_view", exc, release_id=context.release_id
        )
        if failure is not None:
            raise InvariantViolation(failure) from exc
        raise


def select_reused_source_views(conn: Connection, *, run_id: int, task_id: int) -> None:
    from ._operation_calls import RunId, TaskId
    from ._operation_calls import select_reused_source_views as invoke
    from .pdf_contracts import pdf_context_for_task
    from .releases import open_release

    context = pdf_context_for_task(conn, task_id)
    if context.release_id is None:
        raise ValueError("reused source selection requires its bound task release")
    invoke(
        conn,
        run_id=RunId(run_id),
        task_id=TaskId(task_id),
        projection_context=open_release(conn, context.release_id),
    )


def store_native_source_frame(
    conn: Connection, *, task_id: int, packet_hash: str, frame: dict[str, Any]
) -> None:
    from .pdf_contracts import pdf_context_for_task

    context = pdf_context_for_task(conn, task_id)
    value = context.boundary.validate_json("PdfNativeProposalFrame", json.dumps(frame))
    from ._operation_calls import TaskId
    from ._operation_calls import capture_native_source_frame as invoke
    from .releases import open_release

    if context.release_id is None:
        raise ValueError("native source frame requires its bound task release")
    invoke(
        conn,
        task_id=TaskId(task_id),
        packet_hash=packet_hash,
        frame=value.model_dump(mode="json"),
        projection_context=open_release(conn, context.release_id),
    )


def load_native_source_frames(conn: Connection, task_ids):
    """Decode the exact captured native sources; historical primaries stay primary-only."""
    from .proposals import NativeProposalFrame, ProposalSentence, native_frame_from_dict

    rows = conn.execute(
        text("SELECT * FROM ops.native_source_frame WHERE task_id=ANY(:ids)"),
        dict(ids=list(task_ids)),
    ).mappings()
    result = {}
    views = {}
    for row in rows:
        if row["source_frame"] is not None:
            result[row["task_id"]] = native_frame_from_dict(row["source_frame"])
            continue
        view_id = row["source_view_id"]
        if view_id not in views:
            views[view_id] = load_source_view(conn, view_id)
        view = views[view_id]
        sentences = conn.execute(
            text(
                "SELECT sentence_id,locator,start_offset,end_offset FROM "
                "ops.native_source_frame_sentence WHERE task_id=:task ORDER BY "
                "start_offset,end_offset,sentence_id"
            ),
            dict(task=row["task_id"]),
        ).mappings()
        result[row["task_id"]] = NativeProposalFrame(
            row["unit_ref"],
            view.text,
            tuple(
                ProposalSentence(r["sentence_id"], r["locator"], r["start_offset"], r["end_offset"])
                for r in sentences
            ),
            view_id,
            view.ref.native_product,
            view.ref.section_pointer,
            view.ref.membership,
            row["projection_digest"],
            row["recipe_digest"],
            canonical_bytes(row["context_json"]).decode(),
        )
    return result


def read_native_source(conn, request):
    from corpus_structure.serve.native_source import inspect_native_source

    return inspect_native_source(conn, request)


def request_source_view(*args, **kwargs):
    from .native_requests import request_source_view as request

    return request(*args, **kwargs)


def store_region_artifact(
    conn: Connection,
    *,
    task_id: int,
    attempt: int,
    holder: str,
    selection: Mapping[str, JsonValue],
    recipe_bytes: bytes,
    content: bytes,
) -> str:
    from ._operation_calls import TaskAttempt, TaskId
    from ._operation_calls import publish_pdf_region_artifact as invoke
    from .invariant_failures import InvariantViolation, classify_invariant_failure
    from .pdf_contracts import pdf_context_for_task
    from .refusals import DATABASE_ERRORS
    from .releases import open_release

    context = pdf_context_for_task(conn, task_id)
    if context.release_id is None:
        raise ValueError("region artifact requires its bound task release")
    prepared = open_release(conn, context.release_id)
    try:
        return invoke(
            conn,
            task_id=TaskId(task_id),
            attempt=TaskAttempt(attempt),
            holder=holder,
            selection=dict(selection),
            recipe=recipe_bytes,
            content=content,
            projection_context=prepared,
        )
    except DATABASE_ERRORS as exc:
        failure = classify_invariant_failure(
            context.execution, "publish_pdf_region_artifact", exc, release_id=context.release_id
        )
        if failure is not None:
            raise InvariantViolation(failure) from exc
        raise


def _native_section_title_parts(value: str) -> tuple[str | None, str]:
    import re
    import unicodedata

    prefix = re.match(
        r"^\s*(\d+(?:\.\d+)*)(?=$|\s|[:.)\u2013\u2014-])(?:\s|[:.)\u2013\u2014-])*", value
    )
    number = prefix[1] if prefix else None
    title = value[prefix.end() :] if prefix else value
    title = "".join(" " if unicodedata.category(char).startswith("P") else char for char in title)
    return number, " ".join(title.casefold().split())


def normalized_native_section_title(value: str) -> str:
    """Normalize title punctuation while retaining an explicit section number."""
    number, title = _native_section_title_parts(value)
    return " ".join(part for part in (number, title) if part)


def resolve_native_sections[Key](
    catalog: Mapping[Key, str], selectors: Sequence[str]
) -> tuple[Key, ...]:
    """Resolve each title selector to one actual catalog occurrence, never an alias set."""
    from .operations import SourceReadRefused

    normalized = {key: _native_section_title_parts(title) for key, title in catalog.items()}
    resolved: dict[Key, None] = {}
    for selector in selectors:
        number, title = _native_section_title_parts(selector)
        if not number and not title:
            raise SourceReadRefused("invalid", "native section selector is empty")
        matches = [
            key
            for key, (candidate_number, candidate_title) in normalized.items()
            if (number is None or candidate_number == number)
            and (not title or candidate_title == title)
        ]
        if not matches:
            raise SourceReadRefused(
                "missing", f"requested native section is unavailable: {selector!r}"
            )
        if len(matches) != 1:
            choices = "; ".join(f"{catalog[key]!r} [{key}]" for key in matches)
            raise SourceReadRefused(
                "invalid", f"ambiguous native section selector {selector!r}: {choices}"
            )
        resolved[matches[0]] = None
    return tuple(resolved)


def scope_source_views(conn: Connection, selected, scope):
    """Match released organizational titles, then include declared descendants once."""
    ids = [ref.id for ref in selected]
    relation = table("kb.source_view")
    raw = (
        conn.execute(
            select(
                relation.c.id,
                relation.c.release_id,
                relation.c.native_build_id,
                relation.c.native_revision_id,
                relation.c.projection["ancestors"].label("ancestors"),
            ).where(relation.c.id.in_(ids))
        )
        .mappings()
        .all()
    )
    references = {ref.id: ref for ref in selected}
    from .pdf_record_reader import published_record_reader
    from .published_document import PublishedDocumentBinding
    from .releases import open_release

    grouped = {}
    for row in raw:
        reference = references[row["id"]]
        grouped.setdefault((reference.native_product, row["release_id"]), []).append(row)
    rows: list[dict[str, Any]] = []
    for (pin, release_id), group in grouped.items():
        reader = published_record_reader(
            conn, pin, projection_context=open_release(conn, release_id)
        )
        if reader is None:
            raise ValueError("current source scope requires a published record binding")
        binding = PublishedDocumentBinding.from_revision(pin, reader.revision)
        pointers = tuple(
            dict.fromkeys(
                pointer
                for row in group
                for pointer in (references[row["id"]].section_pointer, *row["ancestors"])
            )
        )
        values = reader.selected_native_items(pointers)
        for row in group:
            binding.require_placement(row)
            rows.append(
                dict(
                    id=row["id"],
                    section=values[references[row["id"]].section_pointer],
                    ancestors=[values[pointer] for pointer in row["ancestors"]],
                )
            )
    catalog = {}
    ancestors_by_id = {}
    for row in rows:
        reference = references[row["id"]]
        catalog[reference.native_product, reference.section_pointer] = row["section"].get(
            "name", ""
        )
        ancestors_by_id[row["id"]] = {parent["self_ref"] for parent in row["ancestors"]}
        for parent in row["ancestors"]:
            catalog[reference.native_product, parent["self_ref"]] = parent.get("name", "")
    wanted = set(resolve_native_sections(catalog, scope["sections"]))
    matched = set()
    represented = set()
    for reference in selected:
        pointers = {reference.section_pointer}
        if scope["include_descendants"]:
            pointers.update(ancestors_by_id.get(reference.id, ()))
        selected_roots = {(reference.native_product, pointer) for pointer in pointers} & wanted
        represented.update(selected_roots)
        if selected_roots:
            matched.add(reference.id)
    if wanted - represented:
        from .operations import SourceReadRefused

        raise SourceReadRefused("missing", "requested native section has no selected source view")
    roots = tuple(ref for ref in selected if ref.id in matched)
    return tuple(
        ref
        for ref in roots
        if ref.membership != "descendants"
        or not any(
            other.id != ref.id
            and other.membership == "descendants"
            and other.native_product == ref.native_product
            and other.section_pointer in ancestors_by_id.get(ref.id, ())
            for other in roots
        )
    )


def formula_health_summary(
    outcomes: Sequence[Mapping[str, Any]], reference: ProductReference
) -> list[dict[str, Any]]:
    """Keep queryable formula state and qualify diagnostics retained in exact metadata."""
    summary: list[dict[str, Any]] = []
    for ordinal, outcome in enumerate(outcomes):
        value: dict[str, Any] = {"pointer": outcome["pointer"], "outcome": outcome["outcome"]}
        if "diagnostic_ref" in outcome:
            value["diagnostic_ref"] = dict(outcome["diagnostic_ref"])
        elif "error" in outcome:
            value["diagnostic_ref"] = dict(
                reference.values(), family="native_metadata", local_id=f"formula_outcomes:{ordinal}"
            )
        summary.append(value)
    return summary


def source_view_health(
    health,
    section_pointer,
    membership,
    items,
    ancestors,
    *,
    recognition_coverage=(),
    recognition_coverage_present: bool = False,
):
    """Project coverage onto its named section and retain only local recognition outcomes.

    Native item mappings permit locally detected display processing to be qualified;
    pointer-only archival callers conservatively retain the producer summary.
    """
    value = dict(health)
    nodes = {item["self_ref"]: item for item in items if isinstance(item, dict)}
    pointers = {item["self_ref"] if isinstance(item, dict) else item for item in items}
    outcomes = {row["pointer"]: row["outcome"] for row in health.get("formula_outcomes", ())}
    value["formula_outcomes"] = [
        row for row in health.get("formula_outcomes", ()) if row["pointer"] in pointers
    ]
    if nodes:
        display = {
            pointer
            for pointer, item in nodes.items()
            if item.get("label") == "formula"
            and nodes.get(item.get("parent", {}).get("$ref"), {}).get("label")
            not in {"table", "inline"}
        }
        value["display_coverage"] = (
            "complete"
            if all(outcomes.get(pointer) == "succeeded" for pointer in display)
            else "partial"
            if any(pointer in outcomes for pointer in display)
            else "unknown"
        )
    if recognition_coverage_present or recognition_coverage:
        for key in (
            "inline_scope",
            "cell_scope",
            "inline_membership",
            "cell_membership",
            "candidate_policy",
            "cells_policy",
        ):
            value.pop(key, None)
        for universe in ("display", "inline", "cell"):
            exact = [
                row
                for row in recognition_coverage
                if row["universe"] == universe
                and row["section_pointer"] == section_pointer
                and row["membership"] == membership
            ]
            inherited = [
                row
                for row in recognition_coverage
                if row["universe"] == universe
                and row["outcome"] == "complete"
                and row["membership"] == "descendants"
                and (
                    row["section_pointer"] == section_pointer or row["section_pointer"] in ancestors
                )
            ]
            chosen = exact or inherited
            if not chosen:
                value[universe + "_coverage"] = "unknown"
                continue
            row = chosen[0]
            value[universe + "_coverage"] = row["outcome"]
            if universe != "display":
                value[universe + "_scope"] = [section_pointer]
                value[universe + "_membership"] = membership
                value["candidate_policy" if universe == "inline" else "cells_policy"] = row[
                    "policy"
                ]
        return value
    for universe in ("inline", "cell"):
        scopes = health.get(universe + "_scope", ())
        source_membership = health.get(universe + "_membership")
        covered = (section_pointer in scopes and membership == source_membership) or (
            source_membership == "descendants"
            and (section_pointer in scopes or any(pointer in scopes for pointer in ancestors))
        )
        if not covered and health.get(universe + "_coverage") in {"complete", "partial"}:
            value[universe + "_coverage"] = "unknown"
    return value
