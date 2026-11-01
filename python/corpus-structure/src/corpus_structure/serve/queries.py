"""Current named generic questions over release-scoped Core selections."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, exists, select

from corpus_structure.semantic.query import Coverage, same_scope_clause
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

    def validate_position(self, position):
        if position is not None and not isinstance(position, str):
            from corpus_structure.serve.journey import StaleToken

            raise StaleToken("invalid generic query cursor")

    def scope(self, ctx, p):
        return Scope.run()


def Row(claim):
    return Positioned(claim, claim.fact.occurrence_id or claim.fact.fact_id)


class Claims(Query):
    name, params = "claims", ClaimParams

    def rows(self, ctx, p, after=None):
        f = T["fact"]
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
                ctx.session.object_predicate(
                    p.predicate, p.object, targets, projection=ctx.projection
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
                        oe.join(
                            e, and_(same_scope_clause(oe, e), oe.c.evidence_id == e.c.evidence_id)
                        )
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
        entities = ctx.session.load_entities(set(ids))
        for id_ in ids:
            associated = (
                select(o.c.fact_id)
                .join(
                    context,
                    and_(
                        same_scope_clause(o, context), o.c.occurrence_id == context.c.occurrence_id
                    ),
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
    version = "integrated-source-3"

    def rows(self, ctx, p, after=None):
        from sqlalchemy import func, literal_column, or_

        from corpus_structure.semantic.metadata import table
        from corpus_structure.serve.native_source import NativeSourceRequest

        phase, score_after, key_after = (0, None, None) if after is None else after
        if phase not in (0, 1):
            raise ValueError("invalid source search cursor")
        view, selected, document = map(
            table, ("kb.source_view", "ops.run_source_view", "kb.document")
        )
        newer = selected.alias("newer_search_source")
        config = literal_column("'english'::regconfig")
        query = func.websearch_to_tsquery(config, p.text)
        source_text = view.c.projection["text"].as_string()
        vector = func.to_tsvector(config, source_text)
        score = func.ts_rank_cd(vector, query)
        base = (
            select(
                view.c.id,
                view.c.native_task_id,
                view.c.native_product_key,
                view.c.native_content_digest,
                view.c.section_pointer,
                view.c.membership,
                view.c.projection_digest,
                document.c.source_uri,
                func.ts_headline(config, source_text, query, "MaxWords=45,MinWords=15").label(
                    "excerpt"
                ),
                score.label("score"),
            )
            .join(selected, selected.c.source_view_id == view.c.id)
            .join(document, document.c.id == view.c.document_id)
            .where(
                selected.c.run_id == ctx.run_id,
                ~select(newer.c.source_view_id)
                .where(newer.c.run_id == ctx.run_id, newer.c.supersedes_source_view_id == view.c.id)
                .exists(),
                vector.op("@@")(query),
            )
        )
        if phase == 0:
            while True:
                stmt = base
                if score_after is not None and key_after is not None:
                    stmt = stmt.where(
                        or_(
                            score < float(score_after),
                            and_(score == float(score_after), view.c.id > int(key_after)),
                        )
                    )
                rows = (
                    ctx.conn.execute(stmt.order_by(score.desc(), view.c.id).limit(ctx.row_batch))
                    .mappings()
                    .all()
                )
                if not rows:
                    break
                for row in rows:
                    selection = NativeSourceRequest(
                        run_id=ctx.run_id,
                        task_id=row["native_task_id"],
                        product_key=row["native_product_key"],
                        content_digest=row["native_content_digest"],
                        section_pointer=row["section_pointer"],
                        membership=row["membership"],
                    )
                    yield Positioned(
                        FindAnswer(
                            source_uri=row["source_uri"],
                            source_selection=selection,
                            source_view_id=row["id"],
                            projection_digest=row["projection_digest"],
                            text=row["excerpt"],
                            text_is_excerpt=True,
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
