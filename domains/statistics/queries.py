"""Statistics algorithms composed from the archived semantic fact/value relations."""

from __future__ import annotations

import json
from collections import deque
from itertools import batched
from typing import Any

from pydantic import BaseModel, Field, JsonValue
from sqlalchemy import and_, exists, or_, select

from corpus_structure.core.canonical import canonical_json
from corpus_structure.semantic.query import ReadLimit, _same_scope
from corpus_structure.semantic.refusals import InvalidContinuation
from corpus_structure.serve.protocol import Positioned
from corpus_structure.serve.queries import Params, Query, Row
from corpus_structure.serve.read import T
from corpus_structure.serve.results import FamilyAnswer, RelationAnswer, TransformationAnswer


class Family(Params):
    family: str


class Construction(Params):
    construction: str


class MappingParams(Construction):
    family: str


class Between(Params):
    a: str
    b: str
    depth: int = Field(default=4, ge=1, le=4, strict=True)
    max_edges: int = Field(default=100_000, ge=1, le=1_000_000, strict=True)
    max_frontier: int = Field(default=20_000, ge=1, le=100_000, strict=True)
    max_state_bytes: int = Field(default=8 * 1024 * 1024, ge=1, le=32 * 1024 * 1024, strict=True)


class Where(Params):
    predicate: str
    value: Any = None


def ids(ctx, value):
    return ctx.reader.resolve(value)


def base(ctx, p):
    return ctx.reader.fact_statement(
        include_candidates=p.include_candidates, include_suppositions=p.include_suppositions
    )


def target(ctx, root, targets):
    v = T["typed_value"]
    return exists(
        select(1).where(ctx.reader.scope(v), v.c.value_id == root, v.c.entity_id.in_(targets))
    )


def parameters(ctx, subjects):
    f, v = T["fact"].alias(), T["typed_value"].alias()
    return (
        select(f.c.subject_id)
        .join(v, and_(_same_scope(f, v), f.c.object_value_id == v.c.value_id))
        .where(
            ctx.reader.scope(f),
            f.c.property_id == ctx.reader.iri("stat:family"),
            v.c.entity_id.in_(subjects),
        )
    )


def profile(ctx, p, subjects):
    f = T["fact"]
    return base(ctx, p).where(
        or_(
            f.c.subject_id.in_(subjects),
            f.c.subject_id.in_(parameters(ctx, subjects)),
            and_(
                f.c.property_id == ctx.reader.iri("stat:member_of_construction"),
                target(ctx, f.c.object_value_id, subjects),
            ),
        )
    )


class FamilyProfile(Query):
    name, params = "family_profile", Family

    def rows(self, ctx, p, after=None):
        for row in ctx.reader.claims(statement=profile(ctx, p, ids(ctx, p.family)), after=after):
            yield Row(row)


class ConstructionProfile(Query):
    name, params = "construction_profile", Construction

    def rows(self, ctx, p, after=None):
        subjects = ids(ctx, p.construction)
        stmt = profile(ctx, p, subjects)
        if p.include_suppositions:
            f, r, v = T["fact"], T["value_role"], T["typed_value"]
            roots = select(f.c.qualification_value_id).where(
                ctx.reader.scope(f), f.c.subject_id.in_(subjects)
            )
            variables = (
                select(v.c.entity_id)
                .join(r, and_(_same_scope(r, v), r.c.child_value_id == v.c.value_id))
                .where(
                    ctx.reader.scope(v), r.c.parent_value_id.in_(roots), r.c.role == "base_variable"
                )
            )
            stmt = base(ctx, p).where(
                or_(
                    f.c.fact_id.in_(stmt.with_only_columns(f.c.fact_id)),
                    f.c.subject_id.in_(variables),
                )
            )
        for row in ctx.reader.claims(statement=stmt, after=after):
            yield Row(row)


class FamiliesWhere(Query):
    result: type[BaseModel]
    name, params, result = "families_where", Where, FamilyAnswer

    def rows(self, ctx, p, after=None):
        f, v = T["fact"], T["typed_value"]
        families = ctx.reader.entity_ids(class_name="DistributionFamily")
        stmt = base(ctx, p).where(
            f.c.property_id == ctx.reader.iri(p.predicate),
            or_(f.c.subject_id.in_(families), f.c.subject_id.in_(parameters(ctx, families))),
        )
        for batch in batched(
            ctx.reader.claims(statement=stmt, after=after), ctx.row_batch, strict=False
        ):
            subject_ids = {row.fact.subject.entity_id for row in batch}
            family_by_subject = {
                row.fact.subject.entity_id: row.fact.subject
                for row in batch
                if any(
                    m.class_iri == ctx.reader.iri("DistributionFamily")
                    for m in row.fact.subject.memberships
                )
            }
            parent_rows = ctx.conn.execute(
                select(f.c.subject_id, v.c.entity_id)
                .join(v, and_(_same_scope(f, v), f.c.object_value_id == v.c.value_id))
                .where(
                    ctx.reader.scope(f),
                    f.c.subject_id.in_(subject_ids - family_by_subject.keys()),
                    f.c.property_id == ctx.reader.iri("stat:family"),
                )
            ).all()
            parents = ctx.session._entities({row.entity_id for row in parent_rows})
            family_by_subject.update(
                {row.subject_id: parents[row.entity_id] for row in parent_rows}
            )
            for row in batch:
                if p.value is not None:
                    cls = next(
                        d
                        for d in ctx.compiled.definitions
                        if d.iri in {m.class_iri for m in row.fact.subject.memberships}
                        and any(x.iri == row.fact.property_iri for x in d.properties)
                    )
                    prop = next(x for x in cls.properties if x.iri == row.fact.property_iri)
                    expected = ctx.compiled.property_adapter(
                        cls.name, prop.name, item=prop.multivalued
                    ).validate_json(json.dumps(p.model_dump(mode="json")["value"]), strict=True)
                    if expected != row.fact.object:
                        continue
                family = family_by_subject.get(row.fact.subject.entity_id)
                if family is not None:
                    yield Positioned(
                        FamilyAnswer(family=family, claim=row),
                        row.fact.occurrence_id or row.fact.fact_id,
                    )


class ParameterMapping(Query):
    name, params = "parameter_mapping", MappingParams

    def rows(self, ctx, p, after=None):
        f = T["fact"]
        construction = ids(ctx, p.construction)
        family = ids(ctx, p.family)
        stmt = profile(ctx, p, construction + family).where(
            f.c.property_id.in_(
                [
                    ctx.reader.iri("stat:" + name)
                    for name in (
                        "member_of_construction",
                        "has_parameter",
                        "identical_parameter",
                        "derived_parameter",
                        "parameter_role",
                        "parameter_domain",
                    )
                ]
            ),
            or_(
                f.c.property_id != ctx.reader.iri("stat:member_of_construction"),
                and_(f.c.subject_id.in_(family), target(ctx, f.c.object_value_id, construction)),
            ),
        )
        for row in ctx.reader.claims(statement=stmt, after=after):
            yield Row(row)


def condition_refs(claim):
    def walk(value):
        if hasattr(value, "model_dump"):
            value = value.model_dump(mode="python")
        if isinstance(value, dict):
            if value.get("kind") == "claim" and isinstance(value.get("ref"), str):
                yield value["ref"]
            for child in value.values():
                yield from walk(child)
        elif isinstance(value, (tuple, list)):
            for child in value:
                yield from walk(child)

    return set(walk(claim.fact.qualification))


class Transformations(Query):
    result: type[BaseModel]
    name, params, result = "transformations_of", Family, TransformationAnswer

    def rows(self, ctx, p, after=None):
        f = T["fact"]
        family = ids(ctx, p.family)
        candidates = base(ctx, p).where(f.c.property_id == ctx.reader.iri("stat:has_distribution"))
        # The algorithm's decision universe includes all premises; paging selects conclusions only.
        premise_selection = ctx.reader.fact_statement(
            include_candidates=True, include_suppositions=True
        ).where(
            f.c.property_id == ctx.reader.iri("stat:has_distribution"),
            target(ctx, f.c.object_value_id, family),
        )
        o, c = T["occurrence"], T["occurrence_context"]
        for batch in batched(
            ctx.reader.claims(statement=candidates, after=after), ctx.row_batch, strict=False
        ):
            referenced = set().union(*(condition_refs(row) for row in batch))
            premises = {
                row.fact.fact_id: row
                for row in ctx.reader.claim_tuple(
                    statement=premise_selection.where(f.c.fact_id.in_(referenced))
                )
            }
            refs_by_fact = {
                row.fact.fact_id: condition_refs(row) & premises.keys() for row in batch
            }
            wanted = {row.fact.fact_id for row in batch if refs_by_fact[row.fact.fact_id]}
            if not wanted:
                continue
            contexts = ctx.conn.execute(
                select(o.c.fact_id, c.c.statement_entity_id)
                .distinct()
                .join(c, and_(_same_scope(o, c), o.c.occurrence_id == c.c.occurrence_id))
                .where(
                    ctx.reader.scope(o),
                    o.c.fact_id.in_(wanted),
                    c.c.statement_entity_id.is_not(None),
                )
                .limit(10001)
            ).all()
            if len(contexts) > 10000:
                raise ReadLimit(
                    "transformation statement context budget exhausted", reason="work_limit"
                )
            statements_by_fact = {
                key: {r.statement_entity_id for r in contexts if r.fact_id == key} for key in wanted
            }
            statement_ids = {r.statement_entity_id for r in contexts}
            definition_contexts = ctx.conn.execute(
                select(o.c.fact_id, c.c.statement_entity_id)
                .distinct()
                .join(c, and_(_same_scope(o, c), o.c.occurrence_id == c.c.occurrence_id))
                .where(
                    ctx.reader.scope(o),
                    c.c.statement_entity_id.in_(statement_ids),
                    c.c.statement_role == "definiens",
                )
                .limit(10001)
            ).all()
            if len(definition_contexts) > 10000:
                raise ReadLimit(
                    "transformation definition context budget exhausted", reason="work_limit"
                )
            definitions = ctx.reader.claim_tuple(
                statement=ctx.reader.fact_statement(
                    include_candidates=p.include_candidates, include_suppositions=True
                ).where(f.c.fact_id.in_({r.fact_id for r in definition_contexts}))
            )
            for conclusion in batch:
                key = conclusion.fact.fact_id
                if key not in wanted:
                    continue
                def_ids = {
                    r.fact_id
                    for r in definition_contexts
                    if r.statement_entity_id in statements_by_fact[key]
                }
                defs = tuple(
                    d
                    for d in definitions
                    if d.fact.fact_id in def_ids
                    and d.fact.subject.entity_id == conclusion.fact.subject.entity_id
                )
                if defs:
                    yield Positioned(
                        TransformationAnswer(
                            conclusion=conclusion,
                            premises=tuple(premises[k] for k in sorted(refs_by_fact[key])),
                            definiens=defs,
                        ),
                        conclusion.fact.occurrence_id or conclusion.fact.fact_id,
                    )


class Relations(Query):
    result: type[BaseModel]
    name, params, result = "relations_between", Between, RelationAnswer
    version = "bounded-walks-2"

    def validate_position(self, position):
        if position is None:
            return
        if (
            not isinstance(position, dict)
            or set(position) != {"walk_version", "depth", "origin", "path"}
            or type(position["walk_version"]) is not int
            or position["walk_version"] != 2
            or type(position["depth"]) is not int
            or not 1 <= position["depth"] <= 4
            or not isinstance(position["origin"], str)
            or not isinstance(position["path"], list)
            or len(position["path"]) != position["depth"]
            or any(not isinstance(key, str) or not key for key in position["path"])
        ):
            raise InvalidContinuation(
                "invalid bounded-walk position", reason="invalid_continuation"
            )

    def rows(self, ctx, p, after=None):
        """Exact BFS witnesses; replay consumes the same admission as fresh search."""
        self.validate_position(after)
        f, v = T["fact"], T["typed_value"]
        edges = (
            base(ctx, p)
            .join(v, and_(_same_scope(f, v), f.c.object_value_id == v.c.value_id))
            .with_only_columns(f.c.fact_id, f.c.subject_id, v.c.entity_id.label("target"))
            .where(
                f.c.property_id.in_(
                    [
                        ctx.reader.iri("stat:" + n)
                        for n in ("special_case_of", "transformation_of", "limit_of")
                    ]
                ),
                v.c.kind == "entity",
            )
        )
        roots = sorted(ctx.reader.resolve(p.a, limit=p.max_frontier + 1))
        targets = set(ctx.reader.resolve(p.b, limit=p.max_frontier + 1))
        if max(len(roots), len(targets)) > p.max_frontier:
            raise ReadLimit(
                "walk root/target population exceeds frontier bound", reason="work_limit"
            )
        queue: deque[tuple[tuple[str, str, tuple[str, ...]], int]] = deque()
        retained = len(canonical_json(sorted(targets)))
        for root in roots:
            state = (root, root, ())
            size = len(canonical_json(state))
            retained += size
            queue.append((state, size))
        if retained > p.max_state_bytes:
            raise ReadLimit("walk roots/targets exceed retained-state bytes", reason="work_limit")
        examined = 0
        replayed = after is None
        while queue:
            (origin, subject, path), state_bytes = queue.popleft()
            # Retain the current state until its adjacency has been completely examined.
            edge_after = None
            while True:
                available = p.max_edges - examined
                batch_size = min(ctx.row_batch, 64, available + 1)
                stmt = edges.where(f.c.subject_id == subject)
                if edge_after is not None:
                    stmt = stmt.where(f.c.fact_id.collate("C") > edge_after)
                rows = (
                    ctx.conn.execute(stmt.order_by(f.c.fact_id.collate("C")).limit(batch_size))
                    .mappings()
                    .all()
                )
                for edge in rows:
                    examined += 1
                    if examined > p.max_edges:
                        raise ReadLimit("walk adjacency budget exhausted", reason="work_limit")
                    witness = (*path, edge["fact_id"])
                    state = (origin, edge["target"], witness)
                    position: dict[str, JsonValue] = {
                        "walk_version": 2,
                        "depth": len(witness),
                        "origin": origin,
                        "path": list(witness),
                    }
                    if len(witness) < p.depth:
                        size = len(canonical_json(state))
                        if len(queue) + 2 > p.max_frontier or retained + size > p.max_state_bytes:
                            raise ReadLimit(
                                "walk retained frontier budget exhausted", reason="work_limit"
                            )
                        queue.append((state, size))
                        retained += size
                    if edge["target"] in targets:
                        if not replayed:
                            if position == after:
                                replayed = True
                            continue
                        # Only the admitted witness is hydrated. Parallel edges/cycles survive.
                        facts = {
                            r.fact.fact_id: r
                            for r in ctx.reader.claims(
                                statement=ctx.reader.fact_statement(
                                    include_candidates=True, include_suppositions=True
                                ).where(f.c.fact_id.in_(witness))
                            )
                        }
                        yield Positioned(
                            RelationAnswer(
                                depth=len(witness), claims=tuple(facts[key] for key in witness)
                            ),
                            position,
                        )
                if len(rows) < batch_size:
                    break
                edge_after = rows[-1]["fact_id"]
            retained -= state_bytes
        if not replayed:
            raise InvalidContinuation(
                "walk position is not a matching witness under this binding",
                reason="invalid_continuation",
            )


QUERIES = (
    FamilyProfile(),
    FamiliesWhere(),
    Relations(),
    Transformations(),
    ParameterMapping(),
    ConstructionProfile(),
)
