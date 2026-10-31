"""Independent, immutable references and grades on the admitted semantic release.

Only the evaluator principal can call the protected storage functions. These rows are never
inputs to source proposals, consolidation, publication or the extractor's tool server.
"""

from __future__ import annotations

import copy
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Connection, select, text

from corpus_structure.semantic.contracts import require_bound_operation, require_database_operation
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.proposals import NativeProposalFrame, ProposalFrame, locate_proposal
from corpus_structure.semantic.releases import open_release

from .semantic_alignment import SemanticSide, TierCounts, align_semantic
from .semantic_values import entity_references, rewrite_references


class ReferenceError(ValueError):
    """A reference is incomplete, stale or belongs to another immutable binding."""


class ReferenceReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: int
    project_id: str
    run_id: int
    set_id: int
    reference_snapshot: list[dict[str, Any]]
    result: dict[str, Any]


@dataclass(frozen=True)
class StoredReferencePass:
    id: int
    unit_id: int
    release_id: str
    pass_kind: str
    authored: bytes
    content_digest: str
    frame_id: int
    frame: tuple[dict[str, Any], ...]
    rendition_id: int | None
    rendition_digest: str | None
    batch: Mapping[str, Any]
    source_view_id: int | None = None
    projection_digest: str | None = None


def _call(conn, sql, **params):
    return conn.execute(text(sql), params)


def _json(value):
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), allow_nan=False, default=lambda v: str(v)
    )


def _unit(conn, unit_id):
    u, s = table("eval.reference_unit"), table("eval.reference_set")
    result = (
        conn.execute(
            select(u, s.c.release_id, s.c.project_id, s.c.source_run_id)
            .join(s, u.c.set_id == s.c.id)
            .where(u.c.id == unit_id)
        )
        .mappings()
        .one_or_none()
    )
    if result is None:
        raise ReferenceError(f"unknown reference unit {unit_id}")
    return result


def _completed(conn, run_id, project_id=None):
    c, r = table("ops.completed_result"), table("ops.run")
    row = (
        conn.execute(
            select(c, r.c.project_id).join(r, c.c.run_id == r.c.id).where(c.c.run_id == run_id)
        )
        .mappings()
        .one_or_none()
    )
    if row is None or (project_id is not None and row["project_id"] != project_id):
        raise ReferenceError("completed result does not belong to the selected project")
    return row


def _source_units(conn, run_id):
    """Frozen source frames in the completed cut, regardless of extracted answer presence.

    A valid empty or refused producer report still belongs to the evaluation universe. The
    immutable frame owns unit/rendition identity; prediction observations cannot define it.
    Reused work follows the cut's explicit origin task rather than the continuation's new task.
    Missing required frames refuse with an actionable recovery route instead of shrinking recall.
    """
    from corpus_structure.semantic.source_frames import packet_bound_source_tasks

    native = _native_source_units(conn, run_id)
    if native is not None:
        return native
    completed, frames, renditions, documents, segments = map(
        table,
        ("ops.completed_result", "ops.source_frame", "kb.rendition", "kb.document", "kb.segment"),
    )
    cut_id = conn.execute(
        select(completed.c.cut_id).where(completed.c.run_id == run_id)
    ).scalar_one()
    origins = packet_bound_source_tasks(run_id, cut_id=cut_id).subquery()
    missing = (
        conn.execute(
            select(origins.c.id)
            .outerjoin(frames, frames.c.task_id == origins.c.id)
            .where(frames.c.task_id.is_(None))
            .distinct()
            .order_by(origins.c.id)
        )
        .scalars()
        .all()
    )
    if missing:
        raise ReferenceError(
            f"completed run {run_id} has packet-bound source tasks without immutable frames: "
            f"{missing}; use semantic.source_frames.backfill_source_frames"
            f"(writer_engine, {run_id}) "
            "to verify their original packet hashes and capture missing frames before evaluation"
        )
    return (
        conn.execute(
            select(
                frames.c.rendition_id,
                frames.c.unit_ref.label("unit_key"),
                documents.c.source_uri,
                documents.c.id.label("document_id"),
                segments.c.segment_key,
                segments.c.kind.label("segment_kind"),
                segments.c.attrs.label("segment_attrs"),
            )
            .select_from(origins)
            .join(frames, frames.c.task_id == origins.c.id)
            .join(renditions, renditions.c.id == frames.c.rendition_id)
            .join(documents, documents.c.id == renditions.c.document_id)
            .outerjoin(
                segments,
                (segments.c.id == frames.c.unit_segment_id)
                & (segments.c.rendition_id == frames.c.rendition_id),
            )
            .distinct()
            .order_by(frames.c.unit_ref, frames.c.rendition_id)
        )
        .mappings()
        .all()
    )


def _native_source_units(conn, run_id):
    from corpus_structure.semantic.source_frames import packet_bound_source_tasks
    completed = table("ops.completed_result")
    cut = conn.execute(select(completed.c.cut_id).where(completed.c.run_id == run_id)).scalar_one()
    origins = packet_bound_source_tasks(run_id, cut_id=cut).subquery()
    kinds = set(conn.execute(select(origins.c.unit_type).distinct()).scalars())
    if "source_view" not in kinds:
        return None
    if kinds != {"source_view"}:
        raise ReferenceError("reference creation requires one declared source-frame ABI")
    from corpus_structure.semantic.source_frames import load_source_frames
    from corpus_structure.semantic.source_views import load_source_view
    frames = load_source_frames(conn, conn.execute(select(origins.c.id)).scalars())
    result = {}
    document = table("kb.document")
    for frame in frames.values():
        if not isinstance(frame, NativeProposalFrame):
            raise ReferenceError("native source cut contains an incompatible source frame")
        view = load_source_view(conn, frame.source_view_id)
        source = conn.execute(select(document).where(
            document.c.id == view.ref.document_id)).mappings().one()
        result[view.ref.id] = dict(rendition_id=None, source_view_id=view.ref.id,
            projection_digest=view.ref.projection_digest, unit_key=frame.unit_ref,
            source_uri=source["source_uri"], document_id=view.ref.document_id,
            segment_key=None, segment_kind="section", segment_attrs={})
    return list(result.values())


def _reference_pool(conn: Connection, completed, units):
    """One Core read of metric rows selected by this exact completed source cut."""
    from .sampling import PoolUnit

    measurements, cut = table("ops.measurement"), table("ops.cut_task")
    rows = conn.execute(
        select(measurements.c.scope_key, measurements.c.value)
        .join(cut, cut.c.origin_task_id == measurements.c.task_id)
        .where(
            cut.c.cut_id == completed["cut_id"],
            measurements.c.metric == "segment.math_share",
            measurements.c.scope_type == "segment",
            measurements.c.scope_key.in_(
                [u["segment_key"] for u in units if u["segment_key"] is not None]
            ),
        )
    ).all()
    shares = {}
    for key, value in rows:
        if value is None:
            continue
        if key in shares and shares[key] != value:
            raise ReferenceError("completed source cut has conflicting math-share measurements")
        shares[key] = value
    result = []
    for unit in units:
        attrs = unit["segment_attrs"] or {}
        hint = attrs.get("hint") or {}
        if not isinstance(hint, Mapping):
            hint = {}
        kind = hint.get("statement_kind") or unit["segment_kind"] or "narrative"
        value = shares.get(unit["segment_key"])
        if value is not None and not 0 <= value <= 1:
            raise ReferenceError("source math-share metric is outside its declared fraction range")
        result.append(
            PoolUnit(
                unit["unit_key"],
                str(kind),
                float(value) if value is not None else None,
                document_id=unit["document_id"],
                rendition_id=unit["rendition_id"],
            )
        )
    return result


def evaluation_config(conn: Connection, release_id: str):
    """Only the exact archived policy is authoritative; installed pack files are never read."""
    import yaml

    from .split import EvalConfig

    content = conn.scalar(
        select(table("sem.input").c.content).where(
            table("sem.input").c.release_id == release_id,
            table("sem.input").c.input_kind == "dependency",
            table("sem.input").c.input_name == "operation/evaluation-split.yaml",
        )
    )
    return (
        EvalConfig()
        if content is None
        else EvalConfig.model_validate(yaml.safe_load(bytes(content)) or {})
    )


def _forced_slice_units(conn, release_id, pool, names):
    import yaml

    from corpus_structure.core.evidence import RenditionContent
    from corpus_structure.core.locators import LocatorIndex
    from corpus_structure.core.locators import parse as parse_locator

    if not names:
        return (), ()
    content = conn.scalar(
        select(table("sem.input").c.content).where(
            table("sem.input").c.release_id == release_id,
            table("sem.input").c.input_kind == "dependency",
            table("sem.input").c.input_name == "operation/slices.yaml",
        )
    )
    if content is None:
        raise ReferenceError("forced reference slices require an archived slices declaration")
    declarations = (yaml.safe_load(bytes(content)) or {}).get("slices", {})

    def expand(name, ancestors=()):
        if name in ancestors:
            raise ReferenceError("cyclic forced reference slice")
        if name not in declarations:
            raise ReferenceError(f"unknown archived forced reference slice {name}")
        for entry in declarations[name]:
            if isinstance(entry, str):
                yield entry
            elif isinstance(entry, dict) and set(entry) == {"include"}:
                yield from expand(entry["include"], (*ancestors, name))
            else:
                raise ReferenceError(
                    "forced reference slices require explicit source locators or includes"
                )

    by_page = {}
    indexes = {}
    for unit in pool:
        by_page.setdefault(parse_locator(unit["unit_key"]).page, []).append(unit)
    forced = set()
    outside_cut = {}
    for name in names:
        for locator in expand(name):
            parsed = parse_locator(locator)
            page_units = by_page.get(parsed.page, ())
            if not page_units:
                outside_cut[locator] = "source_page_outside_completed_cut"
                continue
            matched = set()
            for unit in page_units:
                rid = unit["rendition_id"]
                if rid not in indexes:
                    raw = conn.scalar(
                        select(table("kb.rendition").c.content).where(
                            table("kb.rendition").c.id == rid
                        )
                    )
                    indexes[rid] = LocatorIndex(RenditionContent.model_validate(raw), parsed.page)
                try:
                    expected = indexes[rid].resolve(locator)
                    candidate = indexes[rid].resolve(unit["unit_key"])
                except (ValueError, KeyError, LookupError) as error:
                    raise ReferenceError(
                        "forced reference locator is absent or ambiguous on its source page: "
                        f"{locator}"
                    ) from error
                if (expected.start, expected.end) == (candidate.start, candidate.end):
                    matched.add((unit["unit_key"], rid))
            if len(matched) > 1:
                raise ReferenceError(
                    f"forced reference locator is ambiguous in the completed source pool: {locator}"
                )
            if matched:
                forced.add(next(iter(matched))[0])
            else:
                outside_cut[locator] = "source_unit_outside_completed_cut"
    return tuple(sorted(forced)), tuple(
        {"locator": locator, "reason": reason} for locator, reason in sorted(outside_cut.items())
    )


def create_reference_set(
    conn: Connection,
    *,
    project_id: str,
    source_run_id: int,
    label: str,
    split: str = "dev",
    size: int | None = None,
    seed: int | None = None,
    guideline: str | None = None,
    forced: Sequence[str] = (),
) -> dict[str, Any]:
    from .sampling import sample

    result = _completed(conn, source_run_id, project_id)
    release = open_release(conn, result["release_id"])
    require_bound_operation(release, "reference_set")
    config = evaluation_config(conn, release.release_id)
    split_documents(conn, project_id, config.split, release_id=release.release_id)
    pool = _source_units(conn, source_run_id)
    assigned = {
        row.source_uri: row.split
        for row in conn.execute(
            select(table("eval.document_split")).where(
                table("eval.document_split").c.project_id == project_id
            )
        )
    }
    pool = [u for u in pool if assigned.get(u["source_uri"]) == split]
    if not pool:
        raise ReferenceError(
            "no completed source units in the requested document split; "
            "assign document splits first"
        )
    # A forced slice constrains the immutable run's sample. It cannot enlarge that run's
    # completed source cut. Preserve excluded locators explicitly instead of silently dropping
    # policy constraints or substituting source tasks from another run.
    native = bool(pool) and all(unit.get("source_view_id") is not None for unit in pool)
    if native:
        policy_forced,outside_cut=(),()
        available={unit["unit_key"] for unit in pool}
        missing=set(forced)-available
        if missing:
            raise ReferenceError("forced native reference units are outside completed source cut: "+str(sorted(missing)))
    else:
        policy_forced, outside_cut = _forced_slice_units(
            conn,release.release_id,pool,
            config.golden.forced_slices if split=="dev" else (),
        )
    forced = tuple(sorted(set(forced) | set(policy_forced)))
    requested_size = config.golden.sizes[split] if size is None else size
    if requested_size <= 0:
        raise ReferenceError("reference sample size must be positive")
    sampled = sample(
        _reference_pool(conn, result, pool),
        requested_size,
        config.split.seed if seed is None else seed,
        forced,
    )
    if native:
        sampled.sampling["source_frame_abi"]="native-source-view-1"
        sampled.sampling["explicit_forced_units"]=list(forced)
        sampled.sampling["historical_slice_constraints"]={
            "slices":list(config.golden.forced_slices),
            "disposition":"historical HTML locators do not identify native PDF source units"}
    if outside_cut:
        sampled.sampling["forced_outside_completed_cut"] = list(outside_cut)
    if guideline is None:
        guideline = (
            conn.scalar(
                select(table("ops.run").c.guideline).where(table("ops.run").c.id == source_run_id)
            )
            or "independent-reference-v1"
        )
    identity = _call(
        conn,
        "SELECT eval.create_reference_set(:p,:r,:run,:label,:split,:g,CAST(:sampling AS jsonb))",
        p=project_id,
        r=release.release_id,
        run=source_run_id,
        label=label,
        split=split,
        g=guideline,
        sampling=_json(sampled.sampling),
    ).scalar_one()
    units = {}
    by_key = {u["unit_key"]: u for u in pool}
    for key in sampled.units:
        native = by_key[key].get("source_view_id")
        function = "add_native_reference_unit" if native is not None else "add_reference_unit"
        units[key] = _call(conn,
            f"SELECT eval.{function}(:s,:r,:k,'[]'::jsonb)",
            s=identity, r=native if native is not None else by_key[key]["rendition_id"], k=key,
        ).scalar_one()
    return {
        "set_id": identity,
        "project_id": project_id,
        "release_id": release.release_id,
        "source_run_id": source_run_id,
        "units": units,
        "sampling": sampled.sampling,
    }


def record_pass(
    conn: Connection,
    *,
    unit_id: int,
    pass_kind: str,
    actor: str,
    authored: bytes,
    frame: ProposalFrame | NativeProposalFrame,
) -> int:
    unit = _unit(conn, unit_id)
    if not isinstance(authored, bytes):
        raise TypeError("authored reference input must be the exact submitted bytes")
    native = isinstance(frame, NativeProposalFrame)
    if native:
        from corpus_structure.semantic.source_views import load_source_view
        view = load_source_view(conn, unit["source_view_id"])
        if (frame.unit_ref != unit["unit_key"] or frame.source_view_id != view.ref.id
                or frame.text != view.text or frame.projection_digest != view.ref.projection_digest
                or frame.native_product != view.ref.native_product
                or frame.recipe_digest != view.ref.recipe_digest or frame.membership != view.ref.membership
                or frame.section_pointer != view.ref.section_pointer):
            raise ReferenceError("reference frame differs from its bound native source view")
    else:
        rendition = conn.execute(select(table("kb.rendition")).where(
            table("kb.rendition").c.id == unit["rendition_id"])).mappings().one()
        if frame.unit_ref != unit["unit_key"] or frame.text != rendition["canonical_text"]:
            raise ReferenceError("reference source frame differs from bound unit/rendition")
    release = open_release(conn, unit["release_id"])
    require_bound_operation(release, "reference_pass")
    raw = json.loads(authored)
    # Use the same rich release/reference validator and citation cascade as source admission.
    # Reference bytes remain private and never enter a source task or publication batch.
    known = {}
    for entity, cls in conn.execute(
        select(table("data.membership").c.entity_id, table("data.membership").c.class_id).where(
            table("data.membership").c.realization_id
            == _completed(conn, unit["source_run_id"])["output_realization_id"]
        )
    ):
        known.setdefault(entity, []).append(cls)
    located = locate_proposal(
        release, raw, frame, known_classes={k: tuple(v) for k, v in known.items()}
    )
    if not located.clean:
        raise ReferenceError(
            "reference citations must be unambiguous and exactly located: " + str(located.issues)
        )
    stored = located.stored.model_dump(mode="json", exclude_none=True)
    entries = []
    for family in ("claims", "unsupported", "identity_exclusions"):
        for item in stored.get(family, ()):
            for i, citation in enumerate(item["evidence"]):
                entries.append(
                    {**citation, "family": family, "item_ref": item["id"], "evidence_index": i}
                )
    return int(
        _call(
            conn,
            "SELECT eval." + ("record_native_reference_pass" if native else "record_reference_pass")
            + "(:u,:k,:a,:b,CAST(:f AS jsonb))",
            u=unit_id,
            k=pass_kind,
            a=actor,
            b=authored,
            f=_json(entries),
        ).scalar_one()
    )


def read_pass(
    conn: Connection, pass_id: int, *, frame_id: int | None = None
) -> StoredReferencePass:
    p, f = table("eval.reference_pass"), table("eval.reference_frame")
    row = conn.execute(select(p).where(p.c.id == pass_id)).mappings().one()
    unit = _unit(conn, row["unit_id"])
    query = select(f).where(f.c.pass_id == pass_id)
    query = (
        query.where(f.c.id == frame_id)
        if frame_id is not None
        else query.order_by(f.c.version.desc()).limit(1)
    )
    citation = conn.execute(query).mappings().one()
    authored = bytes(row["authored"])
    if sha256(authored).hexdigest() != row["content_digest"]:
        raise ReferenceError("reference authored bytes no longer match their digest")
    release = open_release(conn, unit["release_id"])
    batch = release.validate_json("AgentAuthoredBatch", authored).model_dump(mode="json")
    fields = {(e["family"], e["item_ref"], e["evidence_index"]): e for e in citation["frame"]}
    for family in ("claims", "unsupported", "identity_exclusions"):
        for item in batch.get(family, ()):
            for i, e in enumerate(item.get("evidence", ())):
                placed = fields.get((family, item["id"], i))
                if placed is None or placed["quote"] != e["quote"]:
                    raise ReferenceError(
                        "immutable frame is incomplete for its authored reference pass"
                    )
                item["evidence"][i] = {
                    k: v
                    for k, v in placed.items()
                    if k not in {"family", "item_ref", "evidence_index"}
                }
    validated = release.validate_json("AgentStoredBatch", _json(batch)).model_dump(mode="json")
    return StoredReferencePass(
        pass_id,
        row["unit_id"],
        unit["release_id"],
        row["pass_kind"],
        authored,
        row["content_digest"],
        citation["id"],
        tuple(citation["frame"]),
        citation["rendition_id"],
        citation["rendition_digest"],
        validated,
        citation.get("source_view_id"), citation.get("projection_digest"),
    )


def ensure_items(
    conn: Connection, pass_id: int, *, frame_id: int | None = None
) -> StoredReferencePass:
    stored = read_pass(conn, pass_id, frame_id=frame_id)
    require_database_operation(conn, stored.release_id, "reference_items")
    items = sorted(
        [
            {"item_kind": family, "local_ref": item["id"], "payload": item}
            for family in (
                "entities",
                "statements",
                "claims",
                "unsupported",
                "identity_exclusions",
                "alternatives",
            )
            for item in stored.batch.get(family, ())
        ],
        key=lambda x: (x["item_kind"], x["local_ref"]),
    )
    _call(
        conn,
        "SELECT eval.record_reference_items(:p,:f,CAST(:i AS jsonb))",
        p=pass_id,
        f=stored.frame_id,
        i=_json(items),
    )
    return stored


def relocate_frame(conn: Connection, pass_id: int, *, rendition_id: int) -> int:
    stored = read_pass(conn, pass_id)
    if stored.source_view_id is not None:
        raise ReferenceError("native PDF reference anchors cannot be silently relocated to a rendition")
    require_database_operation(conn, stored.release_id, "reference_frame")
    rendition = (
        conn.execute(
            select(table("kb.rendition")).where(table("kb.rendition").c.id == rendition_id)
        )
        .mappings()
        .one()
    )
    new = []
    for entry in stored.frame:
        quote = entry["quote"]
        text_ = rendition["canonical_text"]
        start = text_.find(quote)
        if start < 0 or text_.find(quote, start + 1) >= 0:
            raise ReferenceError(
                "reference frame is stale: citation is absent or has ambiguous relocation"
            )
        new.append({**entry, "start": start, "end": start + len(quote)})
    return int(
        _call(
            conn,
            "SELECT eval.relocate_reference_frame(:p,:parent,:r,CAST(:f AS jsonb))",
            p=pass_id,
            parent=stored.frame_id,
            r=rendition_id,
            f=_json(new),
        ).scalar_one()
    )


def unit_passes(conn: Connection, unit_id: int) -> dict[str, list[int]]:
    p = table("eval.reference_pass")
    result = {kind: [] for kind in ("A", "B", "C")}
    for row in conn.execute(
        select(p.c.id, p.c.pass_kind).where(p.c.unit_id == unit_id).order_by(p.c.id)
    ):
        result[row.pass_kind].append(row.id)
    return result


def latest_pass_c(conn: Connection, unit_id: int) -> StoredReferencePass | None:
    ids = unit_passes(conn, unit_id)["C"]
    return read_pass(conn, ids[-1]) if ids else None


def golden_units(
    conn: Connection, project_id: str, label: str, split: str | None = None
) -> list[dict[str, Any]]:
    u, s = table("eval.reference_unit"), table("eval.reference_set")
    query = (
        select(u, s.c.split)
        .join(s, u.c.set_id == s.c.id)
        .where(s.c.project_id == project_id, s.c.label == label)
    )
    if split is not None:
        query = query.where(s.c.split == split)
    return [dict(r) for r in conn.execute(query.order_by(u.c.unit_key)).mappings()]


def golden_set_status(conn: Connection, set_id: int) -> dict[str, Any]:
    u = table("eval.reference_unit")
    units = conn.execute(select(u).where(u.c.set_id == set_id)).mappings().all()
    counts = Counter()
    for unit in units:
        passes = unit_passes(conn, unit["id"])
        counts[
            "adjudicated"
            if passes["C"]
            else "double_passed"
            if passes["A"] and passes["B"]
            else "draft"
        ] += 1
    return {"set_id": set_id, "units": len(units), "status": dict(counts)}


def split_documents(
    conn: Connection,
    project_id: str,
    config=None,
    seed: int | None = None,
    *,
    release_id: str | None = None,
) -> dict[str, Any]:
    from corpus_structure.core.vocab import DocumentSplit

    from .split import Assignment, SplitDocument, assign

    if config is None:
        release_id = release_id or conn.scalar(
            select(table("data.project").c.active_release_id).where(
                table("data.project").c.project_id == project_id
            )
        )
        if release_id is None:
            raise ReferenceError(
                "split assignment requires an active admitted release "
                "or explicit archived evaluation policy"
            )
        config = evaluation_config(conn, release_id).split
    release_id = release_id or conn.scalar(
        select(table("data.project").c.active_release_id).where(
            table("data.project").c.project_id == project_id
        )
    )
    if release_id is None:
        raise ReferenceError("split assignment requires an explicitly bound release")
    require_database_operation(conn, release_id, "reference_split")
    d = table("kb.document")
    docs = [
        SplitDocument(
            r.id,
            r.source_uri,
            str(r.meta["chapter"]) if r.meta.get("chapter") is not None else None,
        )
        for r in conn.execute(select(d).where(d.c.project_id == project_id))
    ]
    previous = {
        r.source_uri: r.split
        for r in conn.execute(
            select(table("eval.document_split")).where(
                table("eval.document_split").c.project_id == project_id
            )
        )
    }
    existing = {
        d.id: Assignment(d.id, DocumentSplit(previous[d.source_uri]), "persisted", None)
        for d in docs
        if d.source_uri in previous
    }
    new = assign(docs, config, existing, seed)
    by_id = {d.id: d.source_uri for d in docs}
    fresh = {by_id[row.document_id]: row for row in new}
    for uri, row in fresh.items():
        _call(
            conn,
            "SELECT eval.assign_document_split(:p,:u,:s)",
            p=project_id,
            u=uri,
            s=row.split.value,
        )
    totals = Counter({**previous, **{uri: row.split.value for uri, row in fresh.items()}}.values())
    return {
        "project_id": project_id,
        "seed": config.seed if seed is None else seed,
        "added": dict(Counter(r.split.value for r in fresh.values())),
        "total": dict(totals),
    }


def _external_ids(prepared, batch):
    declared = {
        item["id"] for family in ("entities", "statements") for item in batch.get(family, ())
    }
    return (
        entity_references(prepared, "AgentStoredBatch", batch)
        | {c["subject"] for c in batch.get("claims", ())}
    ) - declared


def _reference_side(conn, unit, stored, prepared):
    known = {identity: identity for identity in _external_ids(prepared, stored.batch)}
    return SemanticSide(unit["unit_key"], stored.batch, frozenset(unit["context"]), known_ids=known)


def _prediction(conn, completed, unit, prepared):
    """Admitted completed source occurrences, not raw task reports or selected-pointer guesses."""
    source_predicate = ("o.source_view_id=:source_view" if unit.get("source_view_id") is not None
                        else "o.rendition_id=:rendition")
    observations = (
        conn.execute(
            text("""SELECT DISTINCT o.id,o.payload,o.observation_key FROM kb.observation o
      JOIN data.occurrence x ON x.source=o.observation_key AND x.release_id=o.release_id
      WHERE x.realization_id=:z AND x.release_id=:r AND """ + source_predicate + """
      AND o.payload_definition='AgentStoredBatch'
        AND o.payload->>'unit_ref'=:unit ORDER BY o.id"""),
            {
                "z": completed["output_realization_id"],
                "r": completed["release_id"],
                "rendition": unit["rendition_id"],
                "source_view": unit.get("source_view_id"),
                "unit": unit["unit_key"],
            },
        )
        .mappings()
        .all()
    )
    rows = (
        conn.execute(
            select(table("data.occurrence")).where(
                table("data.occurrence").c.realization_id == completed["output_realization_id"],
                table("data.occurrence").c.release_id == completed["release_id"],
                table("data.occurrence").c.source.in_([o["observation_key"] for o in observations]),
            )
        )
        .mappings()
        .all()
    )
    admitted = {(r["source"], r["item"]): r["fact_id"] for r in rows}
    declarations = (
        conn.execute(
            select(table("data.entity_source")).where(
                table("data.entity_source").c.realization_id == completed["output_realization_id"],
                table("data.entity_source").c.release_id == completed["release_id"],
                table("data.entity_source").c.observation_id.in_([o["id"] for o in observations]),
            )
        )
        .mappings()
        .all()
    )
    mappings = {(r["observation_id"], r["local_id"]): r["entity_id"] for r in declarations}
    batch: dict[str, Any] = {
        "unit_ref": unit["unit_key"],
        "entities": [],
        "statements": [],
        "claims": [],
        "alternatives": [],
    }
    known: dict[str, str] = {}
    seen = set()
    claim_aliases = {}
    for observation in observations:
        source = observation["payload"]
        prefix = str(observation["id"]) + "/"
        # Source-local identifiers are scoped before combining independent extraction reports.
        ids = {
            item["id"]: mappings.get((observation["id"], item["id"]), prefix + item["id"])
            for family in ("entities", "statements", "claims", "unsupported")
            for item in source.get(family, ())
        }
        rewritten = rewrite_references(prepared, "AgentStoredBatch", source, ids, ids)
        for family in ("entities", "statements"):
            for item in rewritten.get(family, ()):
                value = dict(item)
                value["id"] = ids[item["id"]]
                if not any(v["id"] == value["id"] for v in batch[family]):
                    batch[family].append(value)
                if (observation["id"], item["id"]) in mappings:
                    known[value["id"]] = mappings[observation["id"], item["id"]]
        for index, claim in enumerate(rewritten.get("claims", ())):
            fact = admitted.get((observation["observation_key"], "claims/" + str(index)))
            if fact is None:
                continue
            c = copy.deepcopy(claim)
            c["id"] = ids[claim["id"]]
            c["subject"] = ids.get(c["subject"], c["subject"])
            if c.get("statement"):
                c["statement"] = ids.get(c["statement"], c["statement"])
            if fact in seen:
                old = next(v for v in batch["claims"] if v["_fact_id"] == fact)
                claim_aliases[c["id"]] = old["id"]
                old["evidence"].extend(e for e in c.get("evidence", ()) if e not in old["evidence"])
                continue
            seen.add(fact)
            c["_fact_id"] = fact
            batch["claims"].append(c)
        for alternative in rewritten.get("alternatives", ()):
            members = [
                ids.get(m, m)
                for m in alternative["members"]
                if any(c["id"] == ids.get(m, m) for c in batch["claims"])
            ]
            if len(members) > 1:
                batch["alternatives"].append(
                    {**alternative, "id": prefix + alternative["id"], "members": members}
                )
    fact_to_claim = {c["_fact_id"]: c["id"] for c in batch["claims"]}
    native_groups = {}
    members = table("data.alternative_member")
    for group, fact in conn.execute(
        select(members.c.group_id, members.c.fact_id).where(
            members.c.realization_id == completed["output_realization_id"],
            members.c.release_id == completed["release_id"],
            members.c.fact_id.in_(fact_to_claim),
        )
    ):
        native_groups.setdefault(group, []).append(fact_to_claim[fact])
    for group, claims in native_groups.items():
        if len(set(claims)) > 1:
            batch["alternatives"].append({"id": group, "members": sorted(set(claims))})
    for c in batch["claims"]:
        c.pop("_fact_id", None)
    batch = rewrite_references(prepared, "AgentStoredBatch", batch, {}, claim_aliases)
    for group in batch["alternatives"]:
        group["members"] = list(
            dict.fromkeys(claim_aliases.get(member, member) for member in group["members"])
        )
    known.update((identity, identity) for identity in _external_ids(prepared, batch))
    return SemanticSide(unit["unit_key"], batch, known_ids=known)


def agreement(conn: Connection, unit_id: int) -> dict[str, Any]:
    passes = unit_passes(conn, unit_id)
    if not passes["A"] or not passes["B"]:
        raise ReferenceError("agreement requires independent A and B passes")
    a, b = ensure_items(conn, passes["A"][-1]), ensure_items(conn, passes["B"][-1])
    unit = _unit(conn, unit_id)
    if a.rendition_id != b.rendition_id or a.rendition_digest != b.rendition_digest:
        raise ReferenceError("agreement requires the same source rendition")
    prepared = open_release(conn, unit["release_id"])
    from corpus_structure.semantic.scientific_evidence import require_scientific_policy

    require_scientific_policy(prepared)
    return {
        "unit_id": unit_id,
        "pass_a": a.id,
        "pass_b": b.id,
        "a_to_b": align_semantic(
            _reference_side(conn, unit, a, prepared),
            _reference_side(conn, unit, b, prepared),
            prepared,
        ).as_dict(),
        "b_to_a": align_semantic(
            _reference_side(conn, unit, b, prepared),
            _reference_side(conn, unit, a, prepared),
            prepared,
        ).as_dict(),
    }


def reference_evaluate(
    conn: Connection, *, project_id: str, run_id: int, set_id: int
) -> ReferenceReport:
    completed = _completed(conn, run_id, project_id)
    definition = (
        conn.execute(
            select(table("eval.reference_set")).where(
                table("eval.reference_set").c.id == set_id,
                table("eval.reference_set").c.project_id == project_id,
            )
        )
        .mappings()
        .one()
    )
    if definition["release_id"] != completed["release_id"]:
        raise ReferenceError(
            "references and completed result have different releases; "
            "explicit reference migration is required"
        )
    prepared = open_release(conn, completed["release_id"])
    require_bound_operation(prepared, "reference_grade")
    from corpus_structure.semantic.scientific_evidence import require_scientific_policy

    require_scientific_policy(prepared)
    units = (
        conn.execute(
            select(table("eval.reference_unit"))
            .where(table("eval.reference_unit").c.set_id == set_id)
            .order_by(table("eval.reference_unit").c.id)
        )
        .mappings()
        .all()
    )
    native = bool(units) and all(u.get("source_view_id") is not None for u in units)
    snapshot = _call(conn, "SELECT eval." + ("native_reference_snapshot" if native else "reference_snapshot")
                     + "(:s)", s=set_id).scalar_one()
    if not units or len(snapshot) != len(units):
        raise ReferenceError("every reference unit requires an adjudicated pass C")
    snaps = {s["unit_id"]: s for s in snapshot}
    reports = []
    targets = {(u.get("source_view_id") if native else u["rendition_id"], u["unit_key"])
               for u in _source_units(conn, run_id)}
    for unit in units:
        snap = snaps[unit["id"]]
        reference = ensure_items(conn, snap["pass_id"], frame_id=snap["frame_id"])
        if native:
            from corpus_structure.semantic.source_views import load_source_view
            if reference.source_view_id is None:
                raise ReferenceError("native reference frame has no source view")
            view = load_source_view(conn, reference.source_view_id)
            if view.ref.projection_digest != reference.projection_digest:
                raise ReferenceError("native reference citation frame is stale")
            identity = reference.source_view_id
        else:
            digest = conn.scalar(select(table("kb.rendition").c.content_digest).where(
                table("kb.rendition").c.id == reference.rendition_id))
            if digest != reference.rendition_digest:
                raise ReferenceError("reference citation frame is stale")
            identity = reference.rendition_id
        if (identity, unit["unit_key"]) not in targets:
            raise ReferenceError("reference frame is absent from completed target source cut")
        bound_unit = {**unit, "rendition_id": reference.rendition_id,
                      "source_view_id": reference.source_view_id}
        reports.append(
            align_semantic(
                _reference_side(conn, unit, reference, prepared),
                _prediction(conn, completed, bound_unit, prepared),
                prepared,
            ).as_dict()
        )
    tiers = {
        k: TierCounts(
            sum(u["tiers"][k]["reference"] for u in reports),
            sum(u["tiers"][k]["prediction"] for u in reports),
            sum(u["tiers"][k]["matched"] for u in reports),
        ).as_dict()
        for k in ("core", "full", "evidence")
    }
    coverage = [
        dict(row)
        for row in conn.execute(
            select(table("data.coverage")).where(
                table("data.coverage").c.realization_id == completed["output_realization_id"],
                table("data.coverage").c.release_id == completed["release_id"],
            )
        ).mappings()
    ]
    result = {
        "release_id": completed["release_id"],
        "output_realization_id": completed["output_realization_id"],
        "family": "agent_claims",
        "grain": "distinct_fact_per_source_unit",
        "tiers": tiers,
        "units": reports,
        "coverage": coverage,
        "reference_units_scored": len(reports),
    }
    from corpus_structure.semantic.scientific_evidence import validate_reference_science

    validate_reference_science(result)
    identity = _call(
        conn,
        "SELECT eval." + ("record_native_reference_evaluation" if native else "record_reference_evaluation") + "(:p,:run,:s,"
        "CAST(:snapshot AS jsonb),CAST(:result AS jsonb))",
        p=project_id,
        run=run_id,
        s=set_id,
        snapshot=_json(snapshot),
        result=_json(result),
    ).scalar_one()
    return ReferenceReport(
        id=identity,
        project_id=project_id,
        run_id=run_id,
        set_id=set_id,
        reference_snapshot=snapshot,
        result=result,
    )
