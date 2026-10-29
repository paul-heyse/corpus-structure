"""Domain-independent queries over the generated relational projection (D8 §5.1)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from pydantic import BaseModel, ConfigDict, JsonValue
from sqlalchemy import func, or_, select, text, tuple_

from corpus_structure.core.db import metadata
from corpus_structure.core.vocab import SEARCH_BLOCK
from corpus_structure.serve.protocol import Positioned, QueryContext, Scope
from corpus_structure.serve.results import (
    ClaimAnswer,
    EntityAnswer,
    EvidenceAnswer,
    FindAnswer,
    StatementAnswer,
)

T = metadata.tables


class Params(BaseModel):
    model_config = ConfigDict(extra="forbid")
    include_candidates: bool = False
    include_suppositions: bool = False


class ClaimParams(Params):
    subject: str | None = None
    predicate: str | None = None
    object: str | None = None
    status: str | None = None
    modality: str | None = None


class EntityParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str | None = None
    label: str | None = None


class StatementParams(Params):
    key: str | None = None
    locator: str | None = None


class EvidenceParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str


class FindParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str




Row = ClaimAnswer


class Query:
    version = "2"
    result: type[BaseModel] = Row

    def scope(self, ctx: QueryContext, p: Any) -> Scope:
        return Scope.run()


class Claims(Query):
    name = "claims"
    params: type[BaseModel] = ClaimParams

    def statement(self, ctx: QueryContext, p: Any) -> Any:
        c, e = T["kb.claim"], T["kb.entity"]
        filters = p.model_dump(exclude_none=True)
        for param, column in [("subject", "subject_id"), ("object", "object_entity_id")]:
            value = filters.pop(param, None)
            if value:
                ids = [r["key"] for r in ctx.entities(key=value) if r]
                ids += [r["key"] for r in ctx.entities(label=value) if r] if not ids else []
                filters[column] = select(e.c.id).where(e.c.run_id == ctx.run_id, e.c.key.in_(ids))
        stmt = ctx.reader.claim_statement(
            **{k: v for k, v in filters.items() if k not in ("subject_id", "object_entity_id")}
        )
        for col in ("subject_id", "object_entity_id"):
            if col in filters:
                stmt = stmt.where(c.c[col].in_(filters[col]))
        return stmt

    def rows(self, ctx: QueryContext, p: Any, after: JsonValue = None) -> Iterator[Positioned]:
        for row in ctx.reader.claims(statement=self.statement(ctx, p), after=after):
            yield Positioned(Row.model_validate(row), row["key"])


class Entity(Query):
    name, params = "entity", EntityParams
    result = EntityAnswer

    def rows(
        self, ctx: QueryContext, p: EntityParams, after: JsonValue = None
    ) -> Iterator[Positioned]:
        for row in ctx.reader.entity_rows(p.key, p.label, after):
            yield Positioned(EntityAnswer.model_validate(row), row["key"])


class Statement(Query):
    name, params = "statement", StatementParams
    result = StatementAnswer

    def rows(
        self, ctx: QueryContext, p: StatementParams, after: JsonValue = None
    ) -> Iterator[Positioned]:
        from corpus_structure.serve.journey import QueryRefused

        value = p.key or p.locator
        if not value:
            raise QueryRefused("statement needs key or locator")
        ids, _ = ctx.reader.resolve_statement(value)
        e, s = T["kb.entity"], T["kb.segment"]
        missing = e.c.statement_ordinal.is_(None)
        ordinal = func.coalesce(e.c.statement_ordinal, 0)
        order = (s.c.start_offset, missing, ordinal, e.c.key)
        stmt = (
            select(e.c.id, e.c.key, s.c.start_offset, e.c.statement_ordinal)
            .join(s, s.c.id == e.c.scope_segment_id)
            .where(e.c.run_id == ctx.run_id, e.c.id.in_(ids))
        )
        if after is not None:
            if not isinstance(after, list) or len(after) != 4:
                raise QueryRefused("invalid statement cursor")
            stmt = stmt.where(tuple_(*order) > tuple_(*after))
        with ctx.conn.execute(stmt.order_by(*order).execution_options(yield_per=32)) as result:
            for batch in result.mappings().partitions(32):
                anchors = list(batch)
                ctx.reader.prime_entities({r["id"] for r in anchors})
                flags = {
                    "include_candidates": p.include_candidates,
                    "include_suppositions": p.include_suppositions,
                }
                claims = list(ctx.reader.claims(statement_id=[r["id"] for r in anchors], **flags))
                proofs = list(
                    ctx.reader.claims(
                        object_entity_id=[r["id"] for r in anchors],
                        predicate="core:proves",
                        **flags,
                    )
                )
                for r in anchors:
                    body = [
                        x for x in claims if x["statement"] and x["statement"]["key"] == r["key"]
                    ]
                    # Referenced premises outside this statement are kept alongside conclusions.
                    needed = {
                        z["key"]
                        for x in body
                        for z in x["premises"]
                        if z["kind"] == "condition_premise"
                    }
                    body += [x for x in claims if x["key"] in needed and x not in body]
                    ranks = {"premise": 0, "definiens": 1, "restriction": 2, "conclusion": 3}
                    body.sort(key=lambda x: (ranks.get(x["role"], 4), x["key"]))
                    proof = [
                        x
                        for x in proofs
                        if isinstance(x["object"], dict) and x["object"].get("key") == r["key"]
                    ]
                    yield Positioned(
                        StatementAnswer(
                            key=r["key"],
                            ordinal=r["statement_ordinal"],
                            statement=ctx.reader.entity(r["id"]),
                            claims=body,
                            proofs=proof,
                        ),
                        [
                            r["start_offset"],
                            r["statement_ordinal"] is None,
                            r["statement_ordinal"] or 0,
                            r["key"],
                        ],
                    )

    def scope(self, ctx: QueryContext, p: StatementParams) -> Scope:
        return ctx.reader.statement_scope(p.key or p.locator or "")


class Evidence(Query):
    name, params = "evidence", EvidenceParams
    result = EvidenceAnswer

    def rows(
        self, ctx: QueryContext, p: EvidenceParams, after: JsonValue = None
    ) -> Iterator[Positioned]:
        for row, position in ctx.reader.evidence_rows(p.key, after):
            yield Positioned(EvidenceAnswer.model_validate({"key": p.key, **row}), position)

    def scope(self, ctx: QueryContext, p: EvidenceParams) -> Scope:
        return ctx.reader.evidence_scope(p.key)


class Unsupported(Claims):
    name, params = "unsupported", Params

    def statement(self, ctx: QueryContext, p: Params) -> Any:
        return ctx.reader.claim_statement(
            include_candidates=True,
            include_suppositions=p.include_suppositions,
            predicate="core:unschematized",
            status="unsupported",
        )


def _find_position(after: JsonValue) -> tuple[int, float | None, str | None]:
    if after is None:
        return 0, None, None
    if not isinstance(after, list) or len(after) != 3:
        raise ValueError("invalid find cursor")
    phase, score, key = after
    if (
        not isinstance(phase, int)
        or phase not in (0, 1)
        or not isinstance(score, str)
        or not isinstance(key, str)
    ):
        raise ValueError("invalid find cursor")
    from math import isfinite

    number = float(score)
    if not isfinite(number):
        raise ValueError("invalid find cursor score")
    return phase, number, key


class Find(Query):
    name, params = "find", FindParams
    result = FindAnswer

    def rows(
        self, ctx: QueryContext, p: FindParams, after: JsonValue = None
    ) -> Iterator[Positioned]:
        # pg_textsearch's operator is represented by the physical overlay's named index.
        s, rr = T["kb.segment"], T["kb.run_rendition"]
        score = s.c.text.op("<@>")(text("to_bm25query(:query, 'kb.segment_bm25')"))
        base = select(s, score.label("score")).where(
            s.c.kind.in_(sorted(SEARCH_BLOCK)),
            s.c.ts_config == text("'english'::regconfig"),
            s.c.rendition_id.in_(select(rr.c.rendition_id).where(rr.c.run_id == ctx.run_id)),
            score < 0,
        )
        phase, last_score, last_key = _find_position(after)
        alias_after = last_key if phase == 1 else None
        if phase == 0:
            while True:
                stmt = base
                if last_score is not None and last_key is not None:
                    stmt = stmt.where(
                        or_(score > last_score, (score == last_score) & (s.c.key > last_key))
                    )
                # Native top-k keeps the BM25 access path visible; include the entire boundary
                # tie before ordering by key, so ties never skip a logical hit.
                ranked = stmt.order_by(score).fetch(ctx.row_batch, with_ties=True).subquery()
                count = 0
                with ctx.conn.execute(
                    select(ranked)
                    .order_by(ranked.c.score, ranked.c.key)
                    .execution_options(yield_per=32),
                    {"query": p.text},
                ) as result:
                    for r in result.mappings():
                        count += 1
                        loc = ctx.reader.locator(
                            r["rendition_id"],
                            r["id"],
                            r["start_offset"],
                            r["end_offset"],
                            r["text"],
                        )
                        last_score, last_key = float(r["score"]), str(r["key"])
                        cursor: JsonValue = [0, str(last_score), last_key]
                        yield Positioned(
                            FindAnswer.model_validate(
                                {"key": r["key"], "score": r["score"], "locator": loc}
                            ),
                            cursor,
                        )
                if count < ctx.row_batch:
                    break
        for entity in ctx.entities(label=p.text):
            if alias_after is None or entity["key"] > alias_after:
                yield Positioned(
                    FindAnswer.model_validate(
                        {"key": entity["key"], "score": 0.0, "entity": entity}
                    ),
                    [1, "0.0", entity["key"]],
                )


GENERIC = (Entity(), Claims(), Statement(), Evidence(), Find(), Unsupported())
