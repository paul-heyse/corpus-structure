"""Current named generic questions over release-scoped Core selections."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, exists, select

from corpus_structure.semantic.query import Coverage, _same_scope
from corpus_structure.serve.protocol import Positioned, Scope
from corpus_structure.serve.read import T
from corpus_structure.serve.results import (
    ClaimAnswer,
    EntityAnswer,
    EvidenceAnswer,
    FindAnswer,
    StatementAnswer,
)


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


class Query:
    version = "semantic-1"
    result: type[BaseModel] = ClaimAnswer

    def scope(self, ctx, p):
        return Scope.run()


def Row(claim):
    return Positioned(claim, claim.fact.occurrence_id or claim.fact.fact_id)


class Claims(Query):
    name, params = "claims", ClaimParams

    def rows(self, ctx, p, after=None):
        f, v = T["fact"], T["typed_value"]
        stmt = ctx.reader.fact_statement(
            include_candidates=p.include_candidates,
            include_suppositions=p.include_suppositions,
            predicate=p.predicate,
            status=p.status,
            modality=p.modality,
        )
        if p.subject is not None:
            stmt = stmt.where(f.c.subject_id.in_(ctx.reader.resolve(p.subject)))
        if p.object is not None:
            targets = ctx.reader.resolve(p.object)
            stmt = stmt.where(
                exists(
                    select(1).where(
                        ctx.reader.scope(v),
                        v.c.value_id == f.c.object_value_id,
                        (v.c.entity_id.in_(targets)) | (v.c.lexical == p.object),
                    )
                )
            )
        for claim in ctx.reader.claims(statement=stmt, after=after):
            yield Row(claim)


class Entity(Query):
    result: type[BaseModel]
    name, params, result = "entity", EntityParams, EntityAnswer

    def rows(self, ctx, p, after=None):
        for entity in ctx.reader.entity_rows(p.key, p.label, after):
            yield Positioned(entity, entity.entity.entity_id)


class Statement(Query):
    result: type[BaseModel]
    name, params, result = "statement", StatementParams, StatementAnswer

    def rows(self, ctx, p, after=None):
        context, o, f = T["occurrence_context"], T["occurrence"], T["fact"]
        stmt = (
            select(context.c.statement_entity_id.collate("C"))
            .where(ctx.reader.scope(context), context.c.statement_entity_id.is_not(None))
            .distinct()
        )
        if p.key:
            stmt = stmt.where(context.c.statement_entity_id == p.key)
        if p.locator:
            e, oe = T["evidence"], T["occurrence_evidence"]
            stmt = stmt.where(
                exists(
                    select(1)
                    .select_from(
                        oe.join(e, and_(_same_scope(oe, e), oe.c.evidence_id == e.c.evidence_id))
                    )
                    .where(
                        ctx.reader.scope(oe),
                        oe.c.occurrence_id == context.c.occurrence_id,
                        e.c.locator == p.locator,
                    )
                )
            )
        if after is not None:
            stmt = stmt.where(context.c.statement_entity_id.collate("C") > str(after))
        ids = (
            ctx.conn.execute(stmt.order_by(context.c.statement_entity_id.collate("C")))
            .scalars()
            .all()
        )
        entities = ctx.session._entities(set(ids))
        for id_ in ids:
            associated = (
                select(o.c.fact_id)
                .join(
                    context,
                    and_(_same_scope(o, context), o.c.occurrence_id == context.c.occurrence_id),
                )
                .where(ctx.reader.scope(o), context.c.statement_entity_id == id_)
            )
            selected = ctx.reader.fact_statement(
                include_candidates=p.include_candidates, include_suppositions=p.include_suppositions
            ).where(f.c.fact_id.in_(associated))
            claims = tuple(ctx.reader.claims(statement=selected))
            proof_ids = set(
                ctx.conn.execute(associated.where(context.c.statement_role == "proof")).scalars()
            )
            yield Positioned(
                StatementAnswer(
                    statement=entities[id_],
                    claims=tuple(c for c in claims if c.fact.fact_id not in proof_ids),
                    proofs=tuple(c for c in claims if c.fact.fact_id in proof_ids),
                ),
                id_,
            )


class Evidence(Query):
    result: type[BaseModel]
    name, params, result = "evidence", EvidenceParams, EvidenceAnswer

    def rows(self, ctx, p, after=None):
        for evidence in ctx.reader.evidence(p.key):
            if after is None or evidence.evidence_id > str(after):
                yield Positioned(
                    EvidenceAnswer(fact_id=p.key, evidence=evidence), evidence.evidence_id
                )


class Unsupported(Query):
    result: type[BaseModel]
    name, params, result = "unsupported", Params, Coverage

    def rows(self, ctx, p, after=None):
        for record in sorted(ctx.session.coverage(), key=lambda c: c.coverage_id):
            if record.source_outcome == "unsupported" and (
                after is None or record.coverage_id > str(after)
            ):
                yield Positioned(record, record.coverage_id)


class Find(Query):
    result: type[BaseModel]
    name, params, result = "find", FindParams, FindAnswer

    def rows(self, ctx, p, after=None):
        from sqlalchemy import Integer, cast, func, literal_column, or_

        from corpus_structure.core.locators import LocatorIndex
        from corpus_structure.semantic.metadata import table
        from corpus_structure.semantic.operations import read_rendition

        phase, score_after, key_after = (0, None, None) if after is None else after
        if phase not in (0, 1):
            raise ValueError("invalid source search cursor")
        r, rr, s, d, b, ct, completed = (
            table(n)
            for n in (
                "kb.rendition",
                "ops.run_rendition",
                "kb.segment",
                "kb.document",
                "ops.rendition_build",
                "ops.cut_task",
                "ops.completed_result",
            )
        )
        config = literal_column("'english'::regconfig")
        query = func.websearch_to_tsquery(config, p.text)
        document_vector = func.to_tsvector(config, r.c.canonical_text)
        content = func.substring(
            r.c.canonical_text,
            cast(s.c.start_offset + 1, Integer),
            cast(s.c.end_offset - s.c.start_offset, Integer),
        )
        vector = func.to_tsvector(config, content)
        score = func.ts_rank_cd(vector, query)
        source = (
            rr.join(r, rr.c.rendition_id == r.c.id)
            .join(d, rr.c.document_id == d.c.id)
            .join(s, s.c.rendition_id == r.c.id)
        )
        effective = exists(
            select(1)
            .select_from(
                b.join(ct, ct.c.origin_task_id == b.c.task_id).join(
                    completed, completed.c.cut_id == ct.c.cut_id
                )
            )
            .where(b.c.rendition_id == r.c.id, completed.c.run_id == ctx.run_id)
        )
        base = (
            select(
                s.c.id,
                s.c.rendition_id,
                s.c.kind,
                s.c.start_offset,
                s.c.end_offset,
                d.c.source_uri,
                content.label("text"),
                score.label("score"),
            )
            .select_from(source)
            .where(
                rr.c.run_id == ctx.run_id,
                effective,
                document_vector.op("@@")(query),
                vector.op("@@")(query),
                s.c.kind.in_(("paragraph", "list_item", "table_cell", "heading")),
            )
        )
        if phase == 0:
            indices = {}
            while True:
                stmt = base
                if score_after is not None and key_after is not None:
                    stmt = stmt.where(
                        or_(
                            score < float(score_after),
                            and_(score == float(score_after), s.c.id > int(key_after)),
                        )
                    )
                rows = (
                    ctx.conn.execute(stmt.order_by(score.desc(), s.c.id).limit(ctx.row_batch))
                    .mappings()
                    .all()
                )
                if not rows:
                    break
                for row in rows:
                    rid = row["rendition_id"]
                    if rid not in indices:
                        index = LocatorIndex(
                            read_rendition(ctx.conn, rid, prepared=ctx.session.prepared),
                            row["source_uri"],
                        )
                        indices[rid] = (
                            index,
                            {(seg.kind.value, seg.start, seg.end): seg for seg, _ in index},
                        )
                    index, segments = indices[rid]
                    segment = segments[(row["kind"], row["start_offset"], row["end_offset"])]
                    yield Positioned(
                        FindAnswer(
                            source_uri=row["source_uri"],
                            locator=str(index.generate(segment)),
                            text=row["text"],
                            score=float(row["score"]),
                        ),
                        [0, str(row["score"]), str(row["id"])],
                    )
                score_after, key_after = rows[-1]["score"], str(rows[-1]["id"])
                if len(rows) < ctx.row_batch:
                    break
        for entity in ctx.reader.entity_rows(label=p.text, after=key_after if phase == 1 else None):
            yield Positioned(FindAnswer(entity=entity), [1, "0", entity.entity.entity_id])


GENERIC = (Entity(), Claims(), Statement(), Evidence(), Find(), Unsupported())
