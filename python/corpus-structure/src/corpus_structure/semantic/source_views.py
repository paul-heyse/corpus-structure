"""Immutable section projections and run selections over pinned native PDF products."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Any

from sqlalchemy import Connection, select, text

from corpus_structure.core.method import SourceViewDraft, SourceViewRef

from .identity import canonical_bytes
from .metadata import table
from .parsing_products import ProductReference

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
        return dict(
            pieces=self.pieces, items=self.items, ancestors=self.ancestors, health=self.health
        )


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


def selected_source_views(conn: Connection, run_id: int) -> tuple[SourceViewRef, ...]:
    view, selection = table("kb.source_view"), table("ops.run_source_view")
    newer = selection.alias("newer")
    rows = conn.execute(
        select(view)
        .join(selection, selection.c.source_view_id == view.c.id)
        .where(
            selection.c.run_id == run_id,
            ~select(newer.c.source_view_id)
            .where(newer.c.run_id == run_id, newer.c.supersedes_source_view_id == view.c.id)
            .exists(),
        )
        .order_by(selection.c.position, view.c.id)
    ).mappings()
    return tuple(_ref(row) for row in rows)


def load_source_view(conn: Connection, source_view_id: int) -> PreparedSourceView:
    views = table("kb.source_view")
    row = conn.execute(select(views).where(views.c.id == source_view_id)).mappings().one()
    reference = _ref(row)
    projection = row["projection"]
    product = table("ops.native_document_product")
    pointers = tuple(dict.fromkeys([*projection["items"], *projection["ancestors"]]))
    # One set-shaped query transfers only selected native values, never the book JSON.
    values = conn.execute(
        text("""SELECT refs.pointer,i.native_json AS item
        FROM kb.native_document_item i JOIN unnest(CAST(:pointers AS text[])) WITH ORDINALITY refs(pointer,position) ON refs.pointer=i.pointer
        WHERE i.task_id=:task AND i.product_key=:key ORDER BY refs.position"""),
        dict(
            pointers=list(pointers),
            task=reference.native_product.task_id,
            key=reference.native_product.product_key,
        ),
    ).mappings()
    native = {r["pointer"]: r["item"] for r in values}
    if any(native.get(p) is None for p in pointers):
        raise ValueError("source view has lost its pinned native occurrences")
    from .analysis_contracts import prepare_text_policy
    from .releases import open_release

    policy = prepare_text_policy(open_release(conn, row["release_id"]))
    return PreparedSourceView(
        reference,
        projection["text"],
        tuple(projection["pieces"]),
        tuple(native[p] for p in projection["items"]),
        tuple(native[p] for p in projection["ancestors"]),
        projection["health"],
        policy,
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
    return conn.execute(
        text(
            "SELECT ops.publish_source_view(:run,:task,:attempt,:holder,:position,:payload,:recipe)"
        ),
        dict(
            run=run_id,
            task=task_id,
            attempt=attempt,
            holder=holder,
            position=position,
            payload=canonical_bytes(payload),
            recipe=draft.recipe_bytes,
        ),
    ).scalar_one()


def select_reused_source_views(conn: Connection, *, run_id: int, task_id: int) -> None:
    conn.execute(
        text("SELECT ops.select_reused_source_views(:run,:task)"), dict(run=run_id, task=task_id)
    )


def store_native_source_frame(
    conn: Connection, *, task_id: int, packet_hash: str, frame: dict[str, Any]
) -> None:
    from .pdf_contracts import pdf_context_for_task

    context = pdf_context_for_task(conn, task_id)
    context.boundary.validate_json("PdfNativeProposalFrame", json.dumps(frame))
    conn.execute(
        text("SELECT ops.capture_native_source_frame(:task,:hash,CAST(:frame AS jsonb))"),
        dict(task=task_id, hash=packet_hash, frame=json.dumps(frame)),
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
                "SELECT sentence_id,locator,start_offset,end_offset FROM ops.native_source_frame_sentence WHERE task_id=:task ORDER BY start_offset,end_offset,sentence_id"
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


def store_region_artifact(conn, *, task_id, attempt, holder, selection, recipe_bytes, content):
    return conn.execute(
        text(
            "SELECT ops.publish_pdf_region_artifact(:task,:attempt,:holder,CAST(:selection AS jsonb),:recipe,:content)"
        ),
        dict(
            task=task_id,
            attempt=attempt,
            holder=holder,
            selection=json.dumps(selection),
            recipe=recipe_bytes,
            content=content,
        ),
    ).scalar_one()


def normalized_native_section_title(value: str) -> str:
    """The admitted title selector's shared normalization, never source identity."""
    import re

    return re.sub(r"^\s*\d+(?:\.\d+)*\s*[:.)-]?\s*", "", " ".join(value.split())).casefold()


def scope_source_views(conn: Connection, selected, scope):
    """Match released organizational titles, then include declared descendants once."""
    wanted = {normalized_native_section_title(title) for title in scope["sections"]}
    ids = [ref.id for ref in selected]
    rows = conn.execute(
        text("""SELECT v.id,i.native_json AS section,
       (SELECT COALESCE(jsonb_agg(a.native_json ORDER BY refs.n),'[]') FROM jsonb_array_elements_text(v.projection->'ancestors') WITH ORDINALITY refs(value,n) JOIN kb.native_document_item a ON a.task_id=v.native_task_id AND a.product_key=v.native_product_key AND a.pointer=refs.value) AS ancestors
       FROM kb.source_view v JOIN kb.native_document_item i ON i.task_id=v.native_task_id AND i.product_key=v.native_product_key AND i.pointer=v.section_pointer
       WHERE v.id=ANY(:ids)"""),
        dict(ids=ids),
    ).mappings()
    matched = set()
    represented = set()
    ancestors_by_id = {}
    for row in rows:
        section = row["section"]
        names = [section.get("name", "")]
        if scope["include_descendants"]:
            names += [parent.get("name", "") for parent in row["ancestors"]]
        ancestors_by_id[row["id"]] = {parent["self_ref"] for parent in row["ancestors"]}
        row_names = {normalized_native_section_title(name) for name in names}
        represented.update(row_names & wanted)
        if row_names & wanted:
            matched.add(row["id"])
    if wanted - represented:
        from .operations import SourceReadRefused

        raise SourceReadRefused(
            "missing",
            "requested native sections are unavailable: " + ", ".join(sorted(wanted - represented)),
        )
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


def source_view_health(
    health, section_pointer, membership, items, ancestors, *, recognition_coverage=()
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
    if recognition_coverage:
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
