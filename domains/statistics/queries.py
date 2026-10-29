"""Statistics questions implemented over run-pinned claims (D8 §5.2)."""
from __future__ import annotations
from typing import Any
from pydantic import JsonValue
from sqlalchemy import select,or_,literal
from corpus_structure.serve.protocol import QueryContext,Positioned
from corpus_structure.serve.queries import Query,Params,Row,T

class Family(Params):
    family:str
class Construction(Params):
    construction:str
class MappingParams(Construction):
    family:str
class Between(Params):
    a:str
    b:str
class Where(Params):
    predicate:str
    value:Any=None

def ids(ctx:QueryContext,value:str)->list[int]:
    e=T['kb.entity']
    found=ctx.entities(key=value) if value.startswith(('ent:','stm:')) else ctx.entities(label=value)
    return list(ctx.conn.execute(select(e.c.id).where(e.c.run_id==ctx.run_id,e.c.key.in_([x['key'] for x in found]))).scalars())

def profile(ctx:QueryContext,p:Params,subjects:list[int])->Any:
    c,i=T['kb.claim'],T['kb.entity_identity']
    parameters=select(i.c.entity_id).where(i.c.slot=='stat:family',i.c.value_entity_id.in_(subjects))
    return ctx.reader.claim_statement(include_candidates=p.include_candidates,include_suppositions=p.include_suppositions).where(or_(c.c.subject_id.in_(subjects),c.c.subject_id.in_(parameters)))

class FamilyProfile(Query):
    name,params='family_profile',Family
    def rows(self,ctx:QueryContext,p:Family,after:JsonValue=None):
        for row in ctx.reader.claims(statement=profile(ctx,p,ids(ctx,p.family)),after=after):
            yield Positioned(Row.model_validate(row),row['key'])
class ConstructionProfile(Query):
    name,params='construction_profile',Construction
    def rows(self,ctx:QueryContext,p:Construction,after:JsonValue=None):
        subjects=ids(ctx,p.construction)
        stmt=profile(ctx,p,subjects)
        if p.include_suppositions:
            c=T['kb.claim']
            er=T['kb.claim_entity_ref']
            base=select(er.c.entity_id).join(c,c.c.id==er.c.claim_id).where(c.c.run_id==ctx.run_id,c.c.subject_id.in_(subjects),er.c.role=='qualifier',er.c.slot=='stat:base_variable')
            stmt=ctx.reader.claim_statement(include_candidates=p.include_candidates,include_suppositions=True).where(or_(c.c.id.in_(stmt.with_only_columns(c.c.id)),c.c.subject_id.in_(base)))
        for row in ctx.reader.claims(statement=stmt,after=after):
            yield Positioned(Row.model_validate(row),row['key'])
class FamiliesWhere(Query):
    name,params='families_where',Where
    def rows(self,ctx:QueryContext,p:Where,after:JsonValue=None):
        c=T['kb.claim']
        stmt=ctx.reader.claim_statement(predicate=p.predicate,include_candidates=p.include_candidates,include_suppositions=p.include_suppositions)
        if p.value is not None:
            stmt=stmt.where(c.c.object_value==p.value) if isinstance(p.value,dict) else stmt.where(c.c.object_value['v'].as_string()==str(p.value))
        for row in ctx.reader.claims(statement=stmt,after=after):
            yield Positioned(Row.model_validate(row),row['key'])
class ParameterMapping(Query):
    name,params='parameter_mapping',MappingParams
    def rows(self,ctx:QueryContext,p:MappingParams,after:JsonValue=None):
        c=T['kb.claim']
        subjects=ids(ctx,p.construction)+ids(ctx,p.family)
        stmt=profile(ctx,p,subjects).where(c.c.predicate.in_(['stat:member_of_construction','stat:has_parameter','stat:identical_parameter','stat:derived_parameter','stat:parameter_role','stat:parameter_domain']))
        for row in ctx.reader.claims(statement=stmt,after=after):
            yield Positioned(Row.model_validate(row),row['key'])
class Transformations(Query):
    name,params='transformations_of',Family
    def rows(self,ctx:QueryContext,p:Family,after:JsonValue=None):
        c,cr,er=T['kb.claim'],T['kb.claim_ref'],T['kb.claim_entity_ref']
        family=ids(ctx,p.family)
        premise=c.alias('premise')
        premise_ids=select(premise.c.id).where(premise.c.run_id==ctx.run_id,premise.c.predicate=='stat:has_distribution',or_(premise.c.object_entity_id.in_(family),premise.c.id.in_(select(er.c.claim_id).where(er.c.entity_id.in_(family)))))
        conclusions=select(cr.c.claim_id).where(cr.c.kind=='condition_premise',cr.c.target_claim_id.in_(premise_ids))
        stmt=ctx.reader.claim_statement(include_candidates=p.include_candidates,include_suppositions=p.include_suppositions).where(c.c.predicate=='stat:has_distribution',c.c.id.in_(conclusions))
        for row in ctx.reader.claims(statement=stmt,after=after):
            stmtid=ctx.conn.execute(select(c.c.statement_id).where(c.c.run_id==ctx.run_id,c.c.key==row['key'])).scalar_one()
            row['definiens']=list(ctx.reader.claims(statement_id=stmtid,statement_role='definiens',subject_id=ctx.conn.execute(select(c.c.subject_id).where(c.c.run_id==ctx.run_id,c.c.key==row['key'])).scalar_one(),include_suppositions=True))
            yield Positioned(Row.model_validate(row),row['key'])
class Relations(Query):
    name,params='relations_between',Between
    def rows(self,ctx:QueryContext,p:Between,after:JsonValue=None):
        c=T['kb.claim']
        edges=ctx.reader.claim_statement(include_candidates=p.include_candidates,include_suppositions=p.include_suppositions).where(c.c.predicate.in_(['stat:special_case_of','stat:transformation_of','stat:limit_of']),c.c.object_entity_id.is_not(None)).subquery()
        walk=select(edges.c.subject_id.label('origin'),edges.c.object_entity_id.label('target'),edges.c.key.label('path'),literal(1).label('depth')).where(edges.c.subject_id.in_(ids(ctx,p.a))).cte('paths',recursive=True)
        walk=walk.union_all(select(walk.c.origin,edges.c.object_entity_id,walk.c.path+literal('|')+edges.c.key,walk.c.depth+1).join(edges,edges.c.subject_id==walk.c.target).where(walk.c.depth<4))
        stmt=select(walk).where(walk.c.target.in_(ids(ctx,p.b)))
        if after is not None: stmt=stmt.where(walk.c.path>after)
        for r in ctx.conn.execute(stmt.order_by(walk.c.path)).mappings():
            keys=r['path'].split('|')
            claims=list(ctx.reader.claims(key=keys,include_suppositions=True,include_candidates=True))
            yield Positioned(Row.model_validate({'key':r['path'],'depth':r['depth'],'claims':claims}),r['path'])

QUERIES=(FamilyProfile(),FamiliesWhere(),Relations(),Transformations(),ParameterMapping(),ConstructionProfile())
