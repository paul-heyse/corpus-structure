"""Immutable section projections and run selections over pinned native PDF products."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from functools import cached_property
from hashlib import sha256
from typing import TYPE_CHECKING, Any

from sqlalchemy import Connection, Text, and_, func, select
from sqlalchemy.dialects.postgresql import aggregate_order_by, array

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


def read_context_sources(
    conn, run_id, source, request, *, limit, read_budget, analysis_context=None
):
    """Select compact same-product relation metadata, then admit owned bodies.

    Run selection and source projections define the candidate universe. Native sibling
    ordinals supply neighbors; explicit native links supply captions/notes/references.
    No text search or document hydration is used to manufacture a declaration.
    """
    from hashlib import sha256

    from .pdf_record_reader import published_native_table
    from .refusals import ReadLimit
    from .source_contexts import (
        ContextRelationship,
        NativeSourcePin,
        RetrievalOutcome,
        SourceContextRead,
    )

    if type(limit) is not int or not 1 <= limit <= 8:
        raise ValueError("context lookup requires a source bound between one and eight")
    node = next((item for item in source.items if item["self_ref"] == request.pointer), None)
    if node is None:
        raise ValueError("context lookup pointer is outside its selected primary view")
    view, selection = table("kb.source_view"), table("ops.run_source_view")
    newer = selection.alias("context_newer")
    product = source.ref.native_product
    base = (
        select(view)
        .join(selection, selection.c.source_view_id == view.c.id)
        .where(
            selection.c.run_id == run_id,
            view.c.id != source.ref.id,
            view.c.native_task_id == product.task_id,
            view.c.native_product_key == product.product_key,
            view.c.native_content_digest == product.content_digest,
            ~select(newer.c.source_view_id)
            .where(newer.c.run_id == run_id, newer.c.supersedes_source_view_id == view.c.id)
            .exists(),
        )
    )
    relationship = request.relationship
    if request.targets:
        field = {
            ContextRelationship.CAPTION: "captions",
            ContextRelationship.NOTE: "footnotes",
            ContextRelationship.REFERENCE: "references",
        }.get(relationship)
        declared = (
            {link.get("$ref") for link in node.get(field, ()) if isinstance(link, dict)}
            if field
            else set()
        )
        if not set(request.targets) <= declared:
            raise ValueError("context targets differ from the selected item's native links")
        # A target already in the primary projection is handled locally; it must
        # not acquire a second source identity merely because projections overlap.
        targets = tuple(
            p for p in request.targets if p not in {n["self_ref"] for n in source.items}
        )
        predicate = view.c.projection["items"].op("?|")(array(targets, type_=Text()))
    elif relationship == ContextRelationship.NEIGHBOR:
        item = published_native_table()
        anchor = (
            select(item.c.ordinal, item.c.parent_pointer, item.c.section_pointer)
            .where(
                item.c.task_id == product.task_id,
                item.c.product_key == product.product_key,
                item.c.pointer == request.pointer,
            )
            .cte("context_anchor")
        )
        sibling = and_(
            item.c.task_id == product.task_id,
            item.c.product_key == product.product_key,
            item.c.parent_pointer == anchor.c.parent_pointer,
            item.c.section_pointer.is_not_distinct_from(anchor.c.section_pointer),
            item.c.label.not_in(("section", "chapter", "inline")),
        )
        before = (
            select(item.c.pointer)
            .select_from(item.join(anchor, sibling))
            .where(item.c.ordinal < anchor.c.ordinal)
            .order_by(item.c.ordinal.desc())
            .limit(1)
        )
        after = (
            select(item.c.pointer)
            .select_from(item.join(anchor, sibling))
            .where(item.c.ordinal > anchor.c.ordinal)
            .order_by(item.c.ordinal)
            .limit(1)
        )
        neighbors = before.union_all(after).subquery()
        matching = (
            select(neighbors.c.pointer)
            .where(view.c.projection["items"].op("?")(neighbors.c.pointer))
            .correlate(view)
            .exists()
        )
        predicate = matching
    elif relationship == ContextRelationship.ANCESTOR:
        predicate = and_(
            view.c.membership == "direct",
            view.c.section_pointer.in_(tuple(n["self_ref"] for n in source.ancestors)),
        )
    else:
        return SourceContextRead(
            (),
            (),
            sha256(canonical_bytes([source.ref.id, asdict(request), "missing_scope"])).hexdigest(),
            RetrievalOutcome.MISSING_SCOPE,
            "no explicit native target for this relation",
        )
    candidates = base.where(predicate).subquery("context_candidates")
    # Complete metadata membership remains server-side, including alternatives beyond
    # the supported bound. Pin changes and absent/new candidates change this digest.
    identity = func.jsonb_build_array(
        candidates.c.id,
        candidates.c.projection_digest,
        candidates.c.recipe_digest,
        candidates.c.section_pointer,
        candidates.c.membership,
    ).cast(Text)
    summary_statement = select(
        func.count().label("total"),
        func.encode(
            func.sha256(
                func.convert_to(
                    func.coalesce(
                        func.array_agg(aggregate_order_by(identity, candidates.c.id)).cast(Text), ""
                    ),
                    "UTF8",
                )
            ),
            "hex",
        ).label("membership"),
    ).select_from(candidates)
    read_budget.preflight(conn, summary_statement)
    summary = conn.execute(summary_statement).one()
    read_budget.value(tuple(summary))
    digest = sha256(
        canonical_bytes([asdict(source.ref), asdict(request), summary.total, summary.membership])
    ).hexdigest()
    columns = tuple(
        candidates.c[name]
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
    statement = select(*columns).order_by(candidates.c.id).limit(limit)
    read_budget.preflight(conn, statement)
    rows = tuple(conn.execute(statement).mappings())
    for row in rows:
        read_budget.value(dict(row))
    refs = tuple(_ref(row) for row in rows)
    pins = tuple(
        NativeSourcePin(
            ref.id,
            ref.key,
            ref.native_product,
            ref.section_pointer,
            ref.membership,
            ref.projection_digest,
            ref.recipe_digest,
            3,
        )
        for ref in refs
    )
    if summary.total > limit:
        return SourceContextRead(
            (),
            pins,
            digest,
            RetrievalOutcome.RESOURCE_LIMIT,
            "related source candidate bound exceeded before hydration",
        )
    if not refs:
        return SourceContextRead(
            (),
            (),
            digest,
            RetrievalOutcome.NO_MATCH,
            "no selected same-product view in the declared relation scope",
        )
    # Multiple views covering the same target retain an explicit ambiguity rather
    # than selecting whichever equal string or view happened to appear first.
    if request.targets and len(refs) > len(set(request.targets)):
        return SourceContextRead(
            (),
            pins,
            digest,
            RetrievalOutcome.AMBIGUOUS,
            "multiple selected projections cover an explicit target",
        )
    try:
        sources = tuple(
            load_source_view(
                conn, ref.id, analysis_context=analysis_context, read_budget=read_budget
            )
            for ref in refs
        )
    except ReadLimit:
        return SourceContextRead(
            (),
            pins,
            digest,
            RetrievalOutcome.RESOURCE_LIMIT,
            "invocation read budget exhausted before related hydration completed",
        )
    return SourceContextRead(
        sources,
        pins,
        digest,
        RetrievalOutcome.SELECTED,
        "selected native relation; semantic role attachment remains unresolved",
    )


def context_membership_digest(conn, run_id, source, *, read_budget=None):
    """Conservatively pin complete selected same-product metadata on the server."""
    from hashlib import sha256

    view, selection = table("kb.source_view"), table("ops.run_source_view")
    newer = selection.alias("membership_newer")
    product = source.ref.native_product
    identity = func.jsonb_build_array(
        view.c.id,
        view.c.projection_digest,
        view.c.recipe_digest,
        view.c.section_pointer,
        view.c.membership,
    ).cast(Text)
    statement = (
        select(
            func.encode(
                func.sha256(
                    func.convert_to(
                        func.coalesce(
                            func.array_agg(aggregate_order_by(identity, view.c.id)).cast(Text), ""
                        ),
                        "UTF8",
                    )
                ),
                "hex",
            )
        )
        .select_from(view.join(selection, selection.c.source_view_id == view.c.id))
        .where(
            selection.c.run_id == run_id,
            view.c.native_task_id == product.task_id,
            view.c.native_product_key == product.product_key,
            view.c.native_content_digest == product.content_digest,
            ~select(newer.c.source_view_id)
            .where(newer.c.run_id == run_id, newer.c.supersedes_source_view_id == view.c.id)
            .exists(),
        )
    )
    if read_budget is not None:
        read_budget.preflight(conn, statement)
    result = conn.execute(statement).scalar_one()
    if read_budget is not None:
        read_budget.value(result)
    return sha256(canonical_bytes([asdict(product), result])).hexdigest()


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


def read_native_source(conn, request):
    from corpus_structure.serve.native_source import inspect_native_source

    return inspect_native_source(conn, request)


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
    from corpus_structure.ingest.pdf_hierarchy import resolve_native_sections

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
        from .refusals import SourceReadRefused

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
