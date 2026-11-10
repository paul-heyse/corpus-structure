"""Bounded comparison of source declarations, separate from resolution bindings."""

from collections import defaultdict
from dataclasses import asdict

from sqlalchemy import Text, and_, func, select

from .exclusion_comparison_types import ExclusionComparison
from .identity import canonical_bytes
from .metadata import table
from .query import ReadLimit, SemanticRefusal, _require_snapshot, _scope, bind_completed_result


def compare_declarations(left, right, *, complete):
    """Match immutable observation/local identity, never endpoint pairs or graph URIs."""

    def index(rows):
        result = {}
        for row in rows:
            key = row["observation_key"], row["local_id"]
            if key in result:
                raise SemanticRefusal("ambiguous source declaration identity")
            result[key] = row
        return result

    old, new = index(left), index(right)
    changes = []
    old_operations = {(r["operation_id"], r["operation_version"]) for r in left}
    new_operations = {(r["operation_id"], r["operation_version"]) for r in right}
    incompatible = bool(old_operations and new_operations and old_operations != new_operations)
    for key in sorted(old.keys() | new.keys()):
        a, b = old.get(key), new.get(key)
        if incompatible:
            changes.append(
                dict(identity=list(key), kind="incomparable_operation", before=a, after=b)
            )
            continue
        if a is None or b is None:
            changes.append(
                dict(
                    identity=list(key),
                    kind=("added" if a is None else "removed")
                    if complete
                    else "unmatched_unassessed",
                    before=a,
                    after=b,
                )
            )
            continue
        if (a["operation_id"], a["operation_version"]) != (
            b["operation_id"],
            b["operation_version"],
        ):
            changes.append(
                dict(identity=list(key), kind="incomparable_operation", before=a, after=b)
            )
            continue
        facets = [name for name in ("declaration", "resolution", "evidence") if a[name] != b[name]]
        if facets:
            changes.append(
                dict(identity=list(key), kind="changed", facets=facets, before=a, after=b)
            )
    return changes


def _capture(session, max_rows, max_bytes):
    rel, obs = table("data.identity_exclusion"), table("kb.observation")
    fields = (
        "local_id",
        "operation_id",
        "operation_version",
        "left_kind",
        "left_ref",
        "right_kind",
        "right_ref",
        "reason",
        "left_entity_id",
        "right_entity_id",
    )
    payload = func.jsonb_build_array(obs.c.observation_key, *(rel.c[key] for key in fields))
    selection = (
        select(rel.c.exclusion_id, func.octet_length(payload.cast(Text)).label("bytes"))
        .join_from(
            rel, obs, and_(obs.c.release_id == rel.c.release_id, obs.c.id == rel.c.observation_id)
        )
        .where(_scope(session.binding, rel))
        .order_by(obs.c.observation_key, rel.c.local_id)
        .limit(max_rows + 1)
    )
    inventory = session.connection.execute(selection).mappings().all()
    # Bound transferred variable-width data before fetching it. Fixed envelope-key
    # overhead is included conservatively; final encoded bytes are checked too.
    if sum(row["bytes"] + 512 for row in inventory[:max_rows]) > max_bytes:
        raise ReadLimit("exclusion capture exceeds byte limit", reason="oversized_item")
    selected_ids = [row["exclusion_id"] for row in inventory[:max_rows]]
    rows = (
        session.connection.execute(
            select(rel, obs.c.observation_key)
            .join_from(
                rel,
                obs,
                and_(obs.c.release_id == rel.c.release_id, obs.c.id == rel.c.observation_id),
            )
            .where(_scope(session.binding, rel), rel.c.exclusion_id.in_(selected_ids))
            .order_by(obs.c.observation_key, rel.c.local_id)
        )
        .mappings()
        .all()
        if selected_ids
        else []
    )
    complete = len(inventory) <= max_rows
    rows = rows[:max_rows]
    ids = [row["exclusion_id"] for row in rows]
    evidence = defaultdict(list)
    if ids:
        link, ev, source = (
            table("data.identity_exclusion_evidence"),
            table("data.evidence"),
            table("data.evidence_source"),
        )
        # Capture narrow immutable witness addresses, not source text or whole graph objects.
        witness_scope = and_(
            ev.c.release_id == link.c.release_id,
            ev.c.realization_id == link.c.realization_id,
            ev.c.evidence_id == link.c.evidence_id,
        )
        source_scope = and_(
            _scope(session.binding, source), source.c.evidence_id == ev.c.evidence_id
        )
        source_keys = ("source_view_id", "rendition_id", "span_id", "native_address")
        witness_select = (
            select(
                link.c.exclusion_id,
                ev.c.source_uri,
                ev.c.locator,
                ev.c.provider,
                ev.c.operation_version,
                *(source.c[key] for key in source_keys),
            )
            .join(ev, witness_scope)
            .outerjoin(source, source_scope)
            .where(_scope(session.binding, link), link.c.exclusion_id.in_(ids))
            .order_by(link.c.exclusion_id, ev.c.evidence_id)
        )
        witness_size = func.octet_length(
            func.jsonb_build_array(
                ev.c.source_uri,
                ev.c.locator,
                ev.c.provider,
                ev.c.operation_version,
                *(source.c[key] for key in source_keys),
            ).cast(Text)
        )
        sizes = (
            session.connection.execute(
                select(witness_size)
                .join_from(link, ev, witness_scope)
                .outerjoin(source, source_scope)
                .where(_scope(session.binding, link), link.c.exclusion_id.in_(ids))
                .limit(max_rows + 1)
            )
            .scalars()
            .all()
        )
        if len(sizes) > max_rows:
            raise ReadLimit("exclusion evidence exceeds examined-row limit", reason="work_limit")
        if (
            sum(sizes) + sum(row["bytes"] + 512 for row in inventory[:max_rows]) + len(sizes) * 128
            > max_bytes
        ):
            raise ReadLimit("exclusion witness capture exceeds byte limit", reason="oversized_item")
        witness_rows = session.connection.execute(witness_select).mappings().all()
        for item in witness_rows:
            evidence[item["exclusion_id"]].append(
                {
                    key: item[key]
                    for key in (
                        "source_uri",
                        "locator",
                        "provider",
                        "operation_version",
                        *source_keys,
                    )
                }
            )
    captured = []
    for row in rows:
        captured.append(
            dict(
                observation_key=row["observation_key"],
                local_id=row["local_id"],
                operation_id=row["operation_id"],
                operation_version=row["operation_version"],
                declaration={
                    key: row[key]
                    for key in ("left_kind", "left_ref", "right_kind", "right_ref", "reason")
                },
                resolution={key: row[key] for key in ("left_entity_id", "right_entity_id")},
                evidence=sorted(evidence[row["exclusion_id"]], key=canonical_bytes),
            )
        )
    if len(canonical_bytes(captured)) > max_bytes:
        raise ReadLimit("exclusion capture exceeds byte limit", reason="oversized_item")
    return captured, complete


def compare_pinned_exclusions(
    conn, before_run, after_run, *, limit=100, max_rows=1000, max_bytes=1024**2
):
    if (
        type(limit) is not int
        or not 1 <= limit <= 1000
        or type(max_rows) is not int
        or not 1 <= max_rows <= 10000
        or type(max_bytes) is not int
        or not 1 <= max_bytes <= 8 * 1024**2
    ):
        raise SemanticRefusal("unsupported comparison bounds")
    if any(type(run) is not int or run < 1 for run in (before_run, after_run)):
        raise SemanticRefusal("comparison run identities must be positive integers")
    _require_snapshot(conn)
    transaction = conn.get_transaction()
    left, right = bind_completed_result(conn, before_run), bind_completed_result(conn, after_run)
    if left.binding.release_id != right.binding.release_id:
        raise SemanticRefusal("exclusion comparison requires the same semantic release")
    a, ac = _capture(left, max_rows, max_bytes)
    b, bc = _capture(right, max_rows, max_bytes)
    if (
        transaction is None
        or not transaction.is_active
        or conn.get_transaction() is not transaction
    ):
        raise SemanticRefusal("comparison snapshot changed during capture")
    changes = compare_declarations(a, b, complete=ac and bc)
    complete = (
        ac
        and bc
        and len(changes) <= limit
        and not any(c["kind"] == "incomparable_operation" for c in changes)
    )
    unknowns = (
        []
        if complete
        else ["Selected comparison is incomplete; unmatched declarations do not establish absence."]
    )
    if any(
        not any(
            witness.get(key) is not None
            for key in ("source_view_id", "rendition_id", "span_id", "native_address")
        )
        for row in (*a, *b)
        for witness in row["evidence"]
    ):
        unknowns.append(
            "Some evidence lacks retained source custody; stored witness "
            "addresses do not establish original-source identity."
        )
        complete = False
    report = ExclusionComparison(
        before=dict(run=before_run, cut=left.completed_cut_id, binding=asdict(left.binding)),
        after=dict(run=after_run, cut=right.completed_cut_id, binding=asdict(right.binding)),
        changes=changes[:limit],
        examined_before=len(a),
        examined_after=len(b),
        complete=complete,
        unknowns=unknowns,
    )
    if len(canonical_bytes(report.model_dump(mode="json"))) > max_bytes:
        raise ReadLimit("comparison response exceeds byte limit", reason="oversized_item")
    return report
