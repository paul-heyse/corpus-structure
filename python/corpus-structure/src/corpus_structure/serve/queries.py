"""Current named generic questions over release-scoped Core selections."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, JsonValue
from sqlalchemy import and_, exists, select

from corpus_structure.semantic.query import Coverage, same_scope_clause
from corpus_structure.semantic.structural_products import StructuralProductReport
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
    statement: str | None = None
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
    version = "ordinary-answer-2"
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
        if p.statement is not None:
            occurrence, context = T["occurrence"], T["occurrence_context"]
            linked = select(occurrence.c.fact_id).join(
                context,
                and_(
                    same_scope_clause(occurrence, context),
                    occurrence.c.occurrence_id == context.c.occurrence_id,
                ),
            )
            stmt = stmt.where(
                f.c.fact_id.in_(
                    linked.where(
                        ctx.reader.scope(occurrence), context.c.statement_entity_id == p.statement
                    )
                )
            )
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
        while True:
            ids = (
                ctx.conn.execute(
                    stmt.order_by(context.c.statement_entity_id.collate("C")).limit(ctx.row_batch)
                )
                .scalars()
                .all()
            )
            if not ids:
                break
            entities = ctx.session.load_entities(set(ids))
            for id_ in ids:
                associated = (
                    select(o.c.fact_id)
                    .join(
                        context,
                        and_(
                            same_scope_clause(o, context),
                            o.c.occurrence_id == context.c.occurrence_id,
                        ),
                    )
                    .where(ctx.reader.scope(o), context.c.statement_entity_id == id_)
                )
                selected = ctx.reader.fact_statement(
                    include_candidates=p.include_candidates,
                    include_suppositions=p.include_suppositions,
                ).where(f.c.fact_id.in_(associated))
                selected_ids = (
                    ctx.conn.execute(
                        selected.with_only_columns(f.c.fact_id)
                        .order_by(f.c.fact_id.collate("C"))
                        .limit(9)
                    )
                    .scalars()
                    .all()
                )
                claims = tuple(
                    ctx.reader.claims(statement=selected.where(f.c.fact_id.in_(selected_ids[:8])))
                )
                proof_ids = set(
                    ctx.conn.execute(
                        associated.where(
                            context.c.statement_role == "proof", o.c.fact_id.in_(selected_ids[:8])
                        ).distinct()
                    ).scalars()
                )
                yield Positioned(
                    StatementAnswer(
                        statement=entities[id_],
                        claims=tuple(c for c in claims if c.fact.fact_id not in proof_ids),
                        proofs=tuple(c for c in claims if c.fact.fact_id in proof_ids),
                        population_complete=len(selected_ids) <= 8,
                        claims_query={
                            "query": "claims",
                            "params": {
                                "statement": id_,
                                "include_candidates": p.include_candidates,
                                "include_suppositions": p.include_suppositions,
                            },
                        }
                        if len(selected_ids) > 8
                        else None,
                    ),
                    id_,
                )
            if len(ids) < ctx.row_batch:
                break
            stmt = stmt.where(context.c.statement_entity_id.collate("C") > ids[-1])


class Evidence(Query):
    result: type[BaseModel]
    name, params, result = "evidence", EvidenceParams, EvidenceAnswer

    def rows(self, ctx, p, after=None):
        standing = ctx.session.fact_standing({p.key})[p.key]
        for evidence in ctx.reader.evidence(p.key, after=after):
            if after is None or evidence.evidence_id > str(after):
                yield Positioned(
                    EvidenceAnswer(fact_id=p.key, evidence=evidence, standing=standing),
                    evidence.evidence_id,
                )


class Unsupported(Query):
    result: type[BaseModel]
    name, params, result = "unsupported", Params, Coverage

    def rows(self, ctx, p, after=None):
        relation = T["coverage"]
        while True:
            stmt = select(relation).where(
                ctx.reader.scope(relation), relation.c.source_outcome == "unsupported"
            )
            if after is not None:
                stmt = stmt.where(relation.c.coverage_id.collate("C") > after)
            rows = (
                ctx.conn.execute(
                    stmt.order_by(relation.c.coverage_id.collate("C")).limit(ctx.row_batch)
                )
                .mappings()
                .all()
            )
            for row in rows:
                record = Coverage(**{key: row[key] for key in Coverage.model_fields})
                yield Positioned(record, record.coverage_id)
            if len(rows) < ctx.row_batch:
                break
            after = rows[-1]["coverage_id"]


class Find(Query):
    result: type[BaseModel]
    name, params, result = "find", FindParams, FindAnswer
    version = "integrated-source-4"

    def rows(self, ctx, p, after=None):
        from corpus_structure.serve.source_search import source_search_rows

        phase, score_after, key_after = (0, None, None) if after is None else after
        if phase not in (0, 1):
            raise ValueError("invalid source search cursor")
        if phase == 0:
            from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget

            budget = PublishedReadBudget(10000, 8 * 1024 * 1024)
            while True:
                rows = source_search_rows(
                    ctx.conn,
                    run_id=ctx.run_id,
                    text=p.text,
                    limit=ctx.row_batch,
                    after_score=None if score_after is None else float(score_after),
                    after_id=None if key_after is None else int(key_after),
                    read_budget=budget,
                )
                for row in rows:
                    yield Positioned(
                        FindAnswer(
                            source_uri=row.source_uri,
                            source_selection=row.selection,
                            source_view_id=row.source_view_id,
                            projection_digest=row.projection_digest,
                            text=row.excerpt,
                            text_is_excerpt=True,
                            score=row.score,
                        ),
                        [0, str(row.score), str(row.source_view_id)],
                    )
                if len(rows) < ctx.row_batch:
                    break
                score_after, key_after = rows[-1].score, str(rows[-1].source_view_id)
        for entity in ctx.reader.entity_rows(label=p.text, after=key_after if phase == 1 else None):
            yield Positioned(FindAnswer(entity=entity), [1, "0", entity.entity.entity_id])


class StructuralParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    include_publication: bool = False
    include_support: bool = False
    page_bytes: int = Field(default=1_000_000, ge=1, le=8_000_000)


class StructuralAnswer(BaseModel):
    """A retained report and separately admitted witnesses; graph selection grants no standing."""

    product_id: str
    structural_product: StructuralProductReport
    public_assertions: tuple[dict[str, JsonValue], ...] = ()
    producer_standing: str = "private_proposal"
    assessment_scope: str = "published_admission_witnesses_only"


class StructuralProducts(Query):
    version = "structural-query-1"
    params, result = StructuralParams, StructuralAnswer

    def __init__(self, name, kind):
        self.name, self.kind = name, kind

    def rows(self, ctx, p, after=None):
        from corpus_structure.serve.structural_products import (
            StructuralRequest,
            serve_structural_products,
        )

        self.validate_position(after)
        position = int(after) if after is not None else 0
        while True:
            page = serve_structural_products(
                ctx.conn,
                StructuralRequest(
                    run_id=ctx.run_id,
                    kind=self.kind,
                    after_task_id=position,
                    limit=min(ctx.row_batch, 100),
                    max_bytes=p.page_bytes,
                    include_publication=p.include_publication,
                    include_support=p.include_support,
                ),
            )
            for task_id, report in zip(page.task_ids, page.reports, strict=True):
                yield Positioned(
                    StructuralAnswer(
                        product_id=report.product_id,
                        structural_product=report,
                        public_assertions=tuple(
                            row
                            for row in page.public_assertions
                            if row["product_id"] == report.product_id
                        ),
                    ),
                    str(task_id),
                )
            if page.next_after_task_id is None:
                break
            position = page.next_after_task_id

    def validate_position(self, position):
        if position is not None and (
            not isinstance(position, str) or not position.isascii() or not position.isdecimal()
        ):
            from corpus_structure.semantic.refusals import InvalidContinuation

            raise InvalidContinuation("invalid structural query position")


GENERIC = (
    Entity(),
    Claims(),
    Statement(),
    Evidence(),
    Find(),
    Unsupported(),
    StructuralProducts("structural_definitions", "definition_applicability"),
    StructuralProducts("structural_comparisons", "qualified_comparison"),
    StructuralProducts("structural_dossiers", "dossier"),
)
