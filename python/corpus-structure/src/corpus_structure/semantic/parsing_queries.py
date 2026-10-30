"""Typed, bounded Core reads over a pinned parsing product; no implicit build selection."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Connection, select, text

from .metadata import table
from .parsing_products import PreparedParsingContext, parsing_context_for_task


class ParsingReadLimit(ValueError):
    """The required answer exceeds the explicit bound; no partial answer was returned."""


@dataclass(frozen=True, slots=True)
class ComponentOccurrence:
    component_id: str
    representation_id: str
    unit: str
    start_offset: int
    end_offset: int
    ordinal: int
    category: str


@dataclass(frozen=True, slots=True)
class RelationshipEndpoint:
    relationship_id: str
    ordinal: int
    role: str
    target_task_id: int
    component_id: str | None
    node_id: str | None
    dependency_name: str | None


@dataclass(frozen=True, slots=True)
class MappedExtent:
    side: str
    ordinal: int
    target_task_id: int
    dependency_name: str | None
    representation_id: str
    unit: str
    start_offset: int
    end_offset: int


@dataclass(frozen=True, slots=True)
class TransformationTrace:
    mapping_id: str
    operation: str
    reason: str
    fidelity: str
    source: tuple[MappedExtent, ...]
    target: tuple[MappedExtent, ...]


def _bound(limit: int) -> None:
    if isinstance(limit, bool) or not 1 <= limit <= 10000:
        raise ValueError("parsing read limit must be between 1 and 10000")


def _guard(
    conn: Connection, task_id: int, context: PreparedParsingContext | None
) -> PreparedParsingContext:
    context = parsing_context_for_task(conn, task_id, context)
    context.execution.require_operation("read_parsing_product")
    conn.execute(
        text("SELECT ops.require_parsing_product(:task,:contract)"),
        {"task": task_id, "contract": context.contract_digest},
    )
    return context


def _range(
    conn: Connection,
    task_id: int,
    representation_id: str,
    start: int,
    end: int,
    *,
    canonical: bool = False,
) -> dict[str, Any]:
    rep = table("kb.parsing_representation")
    row = (
        conn.execute(
            select(rep.c.extent_length, rep.c.kind, rep.c.unit).where(
                rep.c.task_id == task_id, rep.c.representation_id == representation_id
            )
        )
        .mappings()
        .one()
    )
    if (
        isinstance(start, bool)
        or isinstance(end, bool)
        or not 0 <= start <= end <= row["extent_length"]
    ):
        raise ValueError("query range is outside the pinned representation")
    if canonical and row["kind"] != "canonical":
        raise ValueError("mapping trace requires an explicitly pinned canonical representation")

    return dict(extent_length=row["extent_length"],kind=row["kind"],unit=row["unit"])


def _validated(
    context: PreparedParsingContext, class_name: str, row: Any, task_id: int
) -> dict[str, Any]:
    values = {key: value for key, value in row.items() if key != "task_id" and value is not None}
    if values.get("target_task_id") == task_id:
        values.pop("target_task_id")
    return context.boundary.validate_json(class_name, json.dumps(values)).model_dump(mode="json")


def components(
    conn: Connection,
    *,
    task_id: int,
    representation_id: str,
    start: int,
    end: int,
    category: str | None = None,
    limit: int = 1000,
    context: PreparedParsingContext | None = None,
) -> tuple[ComponentOccurrence, ...]:
    """Return complete overlapping components or explicitly refuse the answer bound."""
    _bound(limit)
    context = _guard(conn, task_id, context)
    _range(conn, task_id, representation_id, start, end)
    if start == end:
        return ()
    rows = table("kb.parsing_component")
    query = select(rows).where(
        rows.c.task_id == task_id,
        rows.c.representation_id == representation_id,
        rows.c.start_offset < end,
        rows.c.end_offset > start,
    )
    if category is not None:
        categories = next(v for v in context.boundary.vocabularies if v.enum == "ComponentCategory")
        if category not in {m.value for m in categories.members}:
            raise ValueError("unsupported component category")
        query = query.where(rows.c.category == category)
    found = (
        conn.execute(query.order_by(rows.c.ordinal, rows.c.component_id).limit(limit + 1))
        .mappings()
        .all()
    )
    if len(found) > limit:
        raise ParsingReadLimit("component answer exceeds its explicit bound")
    return tuple(
        ComponentOccurrence(**_validated(context, "ParsingComponent", r, task_id)) for r in found
    )


def relationship_endpoints(
    conn: Connection,
    *,
    task_id: int,
    relationship_id: str,
    limit: int = 1000,
    context: PreparedParsingContext | None = None,
) -> tuple[RelationshipEndpoint, ...]:
    _bound(limit)
    context = _guard(conn, task_id, context)
    rows = table("kb.parsing_endpoint")
    found = (
        conn.execute(
            select(rows)
            .where(rows.c.task_id == task_id, rows.c.relationship_id == relationship_id)
            .order_by(rows.c.ordinal)
            .limit(limit + 1)
        )
        .mappings()
        .all()
    )
    if len(found) > limit:
        raise ParsingReadLimit("relationship endpoint answer exceeds its explicit bound")
    result = []
    for row in found:
        values = _validated(context, "ParsingEndpoint", row, task_id)
        result.append(
            RelationshipEndpoint(
                relationship_id=values["relationship_id"],
                ordinal=values["ordinal"],
                role=values["role"],
                target_task_id=row["target_task_id"],
                component_id=row["component_id"],
                node_id=row["node_id"],
                dependency_name=row["dependency_name"],
            )
        )
    return tuple(result)


def trace_mapping(
    conn: Connection,
    *,
    task_id: int,
    representation_id: str,
    start: int,
    end: int,
    limit: int = 1000,
    endpoint_limit: int = 10000,
    context: PreparedParsingContext | None = None,
) -> tuple[TransformationTrace, ...]:
    context = _guard(conn, task_id, context)
    return _mapping_traces(
        conn,
        task_id=task_id,
        representation_id=representation_id,
        start=start,
        end=end,
        limit=limit,
        endpoint_limit=endpoint_limit,
        context=context,
        canonical=True,
    )


def _mapping_traces(
    conn: Connection,
    *,
    task_id: int,
    representation_id: str,
    start: int,
    end: int,
    limit: int,
    endpoint_limit: int,
    context: PreparedParsingContext,
    canonical: bool,
) -> tuple[TransformationTrace, ...]:
    """Trace canonical overlap to whole ordered source/target sets, retaining unknown fidelity."""
    _bound(limit)
    _bound(endpoint_limit)
    _range(conn, task_id, representation_id, start, end, canonical=canonical)
    if start == end:
        return ()
    mapping, endpoints = table("kb.parsing_mapping"), table("kb.parsing_mapping_endpoint")
    touches = (
        select(endpoints.c.mapping_id)
        .where(
            endpoints.c.task_id == mapping.c.task_id,
            endpoints.c.mapping_id == mapping.c.mapping_id,
            endpoints.c.side == "target",
            endpoints.c.target_task_id == task_id,
            endpoints.c.representation_id == representation_id,
            endpoints.c.start_offset < end,
            endpoints.c.end_offset > start,
        )
        .exists()
    )
    found = (
        conn.execute(
            select(mapping)
            .where(mapping.c.task_id == task_id, touches)
            .order_by(mapping.c.mapping_id)
            .limit(limit + 1)
        )
        .mappings()
        .all()
    )
    if len(found) > limit:
        raise ParsingReadLimit("mapping answer exceeds its explicit bound")
    if not found:
        return ()
    ids = [r["mapping_id"] for r in found]
    extents = (
        conn.execute(
            select(endpoints)
            .where(endpoints.c.task_id == task_id, endpoints.c.mapping_id.in_(ids))
            .order_by(endpoints.c.mapping_id, endpoints.c.side, endpoints.c.ordinal)
            .limit(endpoint_limit + 1)
        )
        .mappings()
        .all()
    )
    if len(extents) > endpoint_limit:
        raise ParsingReadLimit("mapping endpoint answer exceeds its explicit bound")
    groups: dict[tuple[str, str], list[MappedExtent]] = {}
    for row in extents:
        values = _validated(context, "ParsingMappingEndpoint", row, task_id)
        values.pop("mapping_id")
        values.update(target_task_id=row["target_task_id"], dependency_name=row["dependency_name"])
        groups.setdefault((row["mapping_id"], row["side"]), []).append(MappedExtent(**values))
    return tuple(
        TransformationTrace(
            **_validated(context, "ParsingMapping", row, task_id),
            source=tuple(groups.get((row["mapping_id"], "source"), ())),
            target=tuple(groups.get((row["mapping_id"], "target"), ())),
        )
        for row in found
    )


@dataclass(frozen=True, slots=True)
class OriginStep:
    task_id: int
    mapping_id: str
    operation: str
    fidelity: str


@dataclass(frozen=True, slots=True)
class OriginContribution:
    kind: str
    extent: MappedExtent
    path: tuple[OriginStep, ...]
    reason: str


@dataclass(frozen=True, slots=True)
class OriginTrace:
    outcome: str
    contributions: tuple[OriginContribution, ...]
    examined_mappings: int


def trace_origins(
    conn: Connection,
    *,
    task_id: int,
    representation_id: str,
    start: int,
    end: int,
    max_depth: int = 32,
    mapping_limit: int = 1000,
    endpoint_limit: int = 10000,
    context: PreparedParsingContext | None = None,
    canonical_only: bool = True,
) -> OriginTrace:
    """Follow declared contributions to original bytes/synthetic rules with explicit limits.

    Transformed extent sets are covering contributions, never a claim of byte identity.
    Unknown origins, cycles and exhausted bounds remain distinct terminal outcomes.
    """
    from collections import deque

    from .parsing_products import _covers

    _bound(mapping_limit)
    _bound(endpoint_limit)
    _bound(max_depth)
    context = _guard(conn, task_id, context)
    initial_rep = _range(conn, task_id, representation_id, start, end, canonical=canonical_only)
    initial = MappedExtent("target", 0, task_id, None, representation_id, initial_rep["unit"], start, end)
    queue: deque[tuple[MappedExtent, tuple[OriginStep, ...]]] = deque([(initial, ())])
    result: list[OriginContribution] = []
    outcome = "complete"
    examined = 0
    guarded = {task_id}
    representation_kinds: dict[tuple[int, str], str] = {}
    trace_cache: dict[tuple[int, str, int, int], tuple[TransformationTrace, ...]] = {}
    while queue:
        extent, path = queue.popleft()
        rep = table("kb.parsing_representation")
        if extent.target_task_id not in guarded:
            _guard(conn, extent.target_task_id, context)
            guarded.add(extent.target_task_id)
        representation_key = (extent.target_task_id, extent.representation_id)
        if representation_key not in representation_kinds:
            representation_kinds[representation_key] = conn.execute(
                select(rep.c.kind).where(
                    rep.c.task_id == extent.target_task_id,
                    rep.c.representation_id == extent.representation_id,
                )
            ).scalar_one()
        kind = representation_kinds[representation_key]
        if kind == "original":
            result.append(OriginContribution("original", extent, path, "immutable original bytes"))
            continue
        if len(path) >= max_depth:
            return OriginTrace(
                "limit",
                tuple(
                    [
                        *result,
                        OriginContribution(
                            "unavailable", extent, path, "origin depth bound reached"
                        ),
                    ]
                ),
                examined,
            )
        try:
            trace_key = (
                extent.target_task_id,
                extent.representation_id,
                extent.start_offset,
                extent.end_offset,
            )
            if trace_key not in trace_cache:
                trace_cache[trace_key] = _mapping_traces(
                    conn,
                    task_id=extent.target_task_id,
                    representation_id=extent.representation_id,
                    start=extent.start_offset,
                    end=extent.end_offset,
                    limit=mapping_limit,
                    endpoint_limit=endpoint_limit,
                    context=context,
                    canonical=False,
                )
            traces = trace_cache[trace_key]
        except ParsingReadLimit:
            return OriginTrace(
                "limit",
                tuple(
                    [
                        *result,
                        OriginContribution(
                            "unavailable", extent, path, "origin answer bound reached"
                        ),
                    ]
                ),
                examined,
            )
        examined += len(traces)
        if examined > mapping_limit:
            return OriginTrace(
                "limit",
                tuple(
                    [
                        *result,
                        OriginContribution(
                            "unavailable", extent, path, "origin mapping bound reached"
                        ),
                    ]
                ),
                examined,
            )
        covered = []
        for trace in traces:
            step = OriginStep(
                extent.target_task_id, trace.mapping_id, trace.operation, trace.fidelity
            )
            if any(p.task_id == step.task_id and p.mapping_id == step.mapping_id for p in path):
                outcome = "cycle"
                result.append(
                    OriginContribution("cycle", extent, (*path, step), "mapping dependency cycle")
                )
                continue
            if trace.fidelity == "unknown":
                if outcome != "cycle":
                    outcome = "partial"
                result.append(
                    OriginContribution("unavailable", extent, (*path, step), trace.reason)
                )
                continue
            covered.extend(
                (
                    max(e.start_offset, extent.start_offset) - extent.start_offset,
                    min(e.end_offset, extent.end_offset) - extent.start_offset,
                )
                for e in trace.target
                if e.target_task_id == extent.target_task_id
                and e.representation_id == extent.representation_id
                and e.start_offset < extent.end_offset
                and e.end_offset > extent.start_offset
            )
            if trace.fidelity == "synthetic":
                result.append(OriginContribution("synthetic", extent, (*path, step), trace.reason))
            else:
                queue.extend((source, (*path, step)) for source in trace.source)
                if len(queue) > endpoint_limit:
                    return OriginTrace("limit", tuple(result), examined)
        if not _covers(covered, extent.end_offset - extent.start_offset):
            if outcome != "cycle":
                outcome = "partial"
            result.append(
                OriginContribution(
                    "unavailable", extent, path, "required contribution range is not fully mapped"
                )
            )
    return OriginTrace(outcome, tuple(result), examined)


def trace_layered_origins(
    conn: Connection, *, reference, representation_id: str, start: int, end: int,
    limit: int = 1000,
) -> dict[str, Any]:
    """Trace qualified immutable product mappings to original or named artifact custody.

    A transformed source extent is a contributing extent set, not an exact character
    correspondence. Unknowns, cycles and bounds are returned as explicit outcomes.
    """
    from collections import deque
    from dataclasses import asdict
    from hashlib import sha256
    from pydantic_core import to_jsonable_python
    from .parsing_products import ProductReference, PreparedParsingProduct, read_layered_product, representation_text, _covers

    _bound(limit)
    queue: deque[tuple[Any, str, int, int, tuple[dict[str, Any], ...], tuple[tuple[Any, str, int, int], ...]]] = deque([(reference, representation_id, start, end, (), ())])
    cache = {}
    contributions = []
    outcome = "complete"
    examined = 0
    while queue:
        ref, rep_id, first, last, path, visited = queue.popleft()
        if len(contributions) >= limit or examined > limit:
            return dict(outcome="limit", contributions=contributions, examined_mappings=examined)
        product = cache.get(ref)
        if product is None:
            product = read_layered_product(conn, ref)
            if product is None:
                raise ValueError("retained origin dependency is unavailable")
            cache[ref] = product
        extent = dict(product=ref.values(), representation_id=rep_id, start_offset=first, end_offset=last)
        if isinstance(product, PreparedParsingProduct):
            remaining = limit-examined
            if remaining <= 0:
                return dict(outcome="limit", contributions=contributions, examined_mappings=examined)
            traced = trace_origins(conn, task_id=ref.task_id, representation_id=rep_id,
                                   start=first, end=last, mapping_limit=remaining,
                                   endpoint_limit=max(1,limit-len(contributions)),
                                   canonical_only=False)
            examined += traced.examined_mappings
            if traced.outcome != "complete": outcome = traced.outcome
            for item in traced.contributions:
                entry=to_jsonable_python(asdict(item))
                entry["path"]=[*path,*[{**step,"product_key":"source"} for step in entry["path"]]]
                if len(contributions) >= limit or examined > limit:
                    return dict(outcome="limit", contributions=contributions, examined_mappings=examined)
                contributions.append(entry)
            continue
        values=product.values()
        reps={row["representation_id"]:row for row in values["representations"]}
        rep=reps.get(rep_id)
        if rep is None or not 0 <= first <= last <= rep["extent_length"]:
            raise ValueError("origin extent is outside its qualified representation")
        if first == last: continue
        signature=(ref,rep_id,first,last)
        if signature in visited:
            outcome="cycle"
            contributions.append(dict(kind="cycle",extent=extent,path=list(path),reason="mapping dependency cycle"))
            continue
        extent["unit"]=rep["unit"]
        text_value=representation_text(rep)
        digest=sha256(text_value.encode("utf8")).hexdigest()
        artifacts={d["artifact_digest"] for d in values["dependencies"] if d["kind"]=="artifact"}
        if digest in artifacts:
            contributions.append(dict(kind="artifact",extent={**extent,"artifact_digest":digest},path=list(path),reason="named immutable artifact representation"))
            continue
        mappings={row["mapping_id"]:row for row in values["mappings"]}
        selected={row["mapping_id"] for row in values["mapping_endpoints"]
                  if row["side"]=="target" and row.get("target_task_id") is None
                  and row["representation_id"]==rep_id and row["start_offset"]<last and row["end_offset"]>first}
        covered=[]
        for mapping_id in sorted(selected):
            if examined >= limit or len(contributions) >= limit:
                return dict(outcome="limit", contributions=contributions, examined_mappings=examined)
            mapping=mappings[mapping_id]
            examined+=1
            step=dict(product=ref.values(),mapping_id=mapping_id,operation=mapping["operation"],fidelity=mapping["fidelity"])
            endpoints=[e for e in values["mapping_endpoints"] if e["mapping_id"]==mapping_id]
            targets=[e for e in endpoints if e["side"]=="target" and e.get("target_task_id") is None and e["representation_id"]==rep_id]
            covered.extend((max(first,e["start_offset"])-first,min(last,e["end_offset"])-first) for e in targets if e["start_offset"]<last and e["end_offset"]>first)
            if mapping["fidelity"]=="unknown":
                outcome="partial"
                contributions.append(dict(kind="unavailable",extent=extent,path=[*path,step],reason=mapping["reason"]))
                continue
            sources=sorted((e for e in endpoints if e["side"]=="source"),key=lambda e:e["ordinal"])
            if not sources:
                if mapping["operation"]!="synthetic":
                    outcome="partial"
                contributions.append(dict(kind="synthetic" if mapping["operation"]=="synthetic" else "unavailable",extent=extent,path=[*path,step],reason=mapping["reason"]))
            for source in sources:
                source_ref=ref if source.get("target_task_id") is None else ProductReference(source["target_task_id"],source["target_product_key"],source["target_content_digest"])
                if len(queue)+len(contributions) >= limit:
                    return dict(outcome="limit", contributions=contributions, examined_mappings=examined)
                queue.append((source_ref,source["representation_id"],source["start_offset"],source["end_offset"],(*path,step),(*visited,signature)))
        if not _covers(covered,last-first):
            if outcome != "cycle": outcome="partial"
            if len(contributions) >= limit:
                return dict(outcome="limit", contributions=contributions, examined_mappings=examined)
            contributions.append(dict(kind="unavailable",extent=extent,path=list(path),reason="no qualified mapping covers this extent"))
    return dict(outcome=outcome,contributions=contributions,examined_mappings=examined)
