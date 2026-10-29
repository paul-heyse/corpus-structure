"""Domain-independent queries over the generated relational projection (D8 §5.1)."""
from __future__ import annotations
from collections.abc import Iterator
from typing import Any
from pydantic import BaseModel, ConfigDict, JsonValue
from sqlalchemy import select, or_, text
from corpus_structure.core.db import metadata
from corpus_structure.core.vocab import SEARCH_BLOCK
from corpus_structure.serve.protocol import Positioned, QueryContext, Scope

T = metadata.tables

class Params(BaseModel):
    model_config = ConfigDict(extra='forbid')
    include_candidates: bool = False
    include_suppositions: bool = False

class ClaimParams(Params):
    subject: str | None = None
    predicate: str | None = None
    object: str | None = None
    status: str | None = None
    modality: str | None = None

class EntityParams(BaseModel):
    model_config = ConfigDict(extra='forbid')
    key: str | None = None
    label: str | None = None

class StatementParams(Params):
    key: str | None = None
    locator: str | None = None

class EvidenceParams(BaseModel):
    model_config = ConfigDict(extra='forbid')
    key: str

class FindParams(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: str

class Row(BaseModel):
    """Query-owned answer context; domain payloads retain their declared shapes."""
    model_config = ConfigDict(extra='allow')
    key: str

class Query:
    version = '2'
    result = Row
    def scope(self, ctx: QueryContext, p: Any) -> Scope:
        return Scope.run()

class Claims(Query):
    name = 'claims'
    params: type[BaseModel] = ClaimParams
    def statement(self, ctx: QueryContext, p: Any) -> Any:
        c,e = T['kb.claim'],T['kb.entity']
        filters = p.model_dump(exclude_none=True)
        for param,column in [('subject','subject_id'),('object','object_entity_id')]:
            value = filters.pop(param,None)
            if value:
                ids=[r['key'] for r in ctx.entities(key=value) if r]
                ids += [r['key'] for r in ctx.entities(label=value) if r] if not ids else []
                filters[column] = select(e.c.id).where(e.c.run_id==ctx.run_id,e.c.key.in_(ids))
        stmt=ctx.reader.claim_statement(**{k:v for k,v in filters.items() if k not in ('subject_id','object_entity_id')})
        for col in ('subject_id','object_entity_id'):
            if col in filters:
                stmt=stmt.where(c.c[col].in_(filters[col]))
        return stmt
    def rows(self,ctx:QueryContext,p:Any,after:JsonValue=None)->Iterator[Positioned]:
        for row in ctx.reader.claims(statement=self.statement(ctx,p),after=after):
            yield Positioned(Row.model_validate(row),row['key'])

class Entity(Query):
    name,params='entity',EntityParams
    def rows(self,ctx:QueryContext,p:EntityParams,after:JsonValue=None)->Iterator[Positioned]:
        for row in ctx.entities(p.key,p.label):
            if after is None or row['key']>after:
                yield Positioned(Row.model_validate(row),row['key'])

class Statement(Claims):
    name,params='statement',StatementParams
    def statement(self,ctx:QueryContext,p:Any)->Any:
        from corpus_structure.serve.journey import QueryRefused
        value=p.key or p.locator
        if not value: raise QueryRefused('statement needs key or locator')
        ids,_=ctx.reader.resolve_statement(value)
        c=T['kb.claim']
        # Structural proof claims point at the requested statement as object.
        return ctx.reader.claim_statement(include_candidates=p.include_candidates,include_suppositions=p.include_suppositions).where(or_(c.c.statement_id.in_(ids),c.c.object_entity_id.in_(ids)))
    def scope(self,ctx:QueryContext,p:Any)->Scope:
        _,locator=ctx.reader.resolve_statement(p.key or p.locator or '')
        return Scope.of_units([locator]) if locator else Scope.run()

class Evidence(Query):
    name,params='evidence',EvidenceParams
    def rows(self,ctx:QueryContext,p:EvidenceParams,after:JsonValue=None)->Iterator[Positioned]:
        for i,row in enumerate(ctx.evidence(p.key)):
            if after is not None and not isinstance(after, int):
                raise ValueError('invalid evidence cursor')
            if after is None or i>after:
                yield Positioned(Row.model_validate({'key':p.key,**row}),i)
    def scope(self,ctx:QueryContext,p:EvidenceParams)->Scope:
        return Scope.of_units([r['unit_key'] for r in ctx.evidence(p.key) if r.get('unit_key')])

class Unsupported(Claims):
    name,params='unsupported',Params
    def statement(self,ctx:QueryContext,p:Params)->Any:
        return ctx.reader.claim_statement(include_candidates=True,include_suppositions=p.include_suppositions,predicate='core:unschematized',status='unsupported')

class Find(Query):
    name,params='find',FindParams
    def rows(self,ctx:QueryContext,p:FindParams,after:JsonValue=None)->Iterator[Positioned]:
        # pg_textsearch's operator is represented by the physical overlay's named index.
        s,rr=T['kb.segment'],T['kb.run_rendition']
        score=s.c.text.op('<@>')(text("to_bm25query(:query, 'kb.segment_bm25')"))
        stmt=select(s,score.label('score')).where(s.c.kind.in_(sorted(SEARCH_BLOCK)),s.c.ts_config==text("'english'::regconfig"),s.c.rendition_id.in_(select(rr.c.rendition_id).where(rr.c.run_id==ctx.run_id)))
        if after is not None:
            if not isinstance(after, list) or len(after) != 2:
                raise ValueError('invalid find cursor')
            stmt=stmt.where(or_(score>float(after[0]),(score==float(after[0]))&(s.c.key>after[1])))
        with ctx.conn.execute(stmt.order_by(score,s.c.key).execution_options(yield_per=64),{'query':p.text}) as result:
            for r in result.mappings():
                loc=ctx.reader.locator(r['rendition_id'],r['id'],r['start_offset'],r['end_offset'],r['text'])
                yield Positioned(Row.model_validate({'key':r['key'],'score':r['score'],**loc}),[str(r['score']),r['key']])
        for entity in ctx.entities(label=p.text):
            if after is None or (0.0, entity['key']) > (float(after[0]), after[1]):
                yield Positioned(Row.model_validate({'key':entity['key'],'score':0.0,'entity':entity}),['0.0',entity['key']])

GENERIC=(Entity(),Claims(),Statement(),Evidence(),Find(),Unsupported())
