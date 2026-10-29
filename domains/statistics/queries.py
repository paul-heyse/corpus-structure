"""Statistics questions implemented over run-pinned claims (D8 §5.2)."""
from __future__ import annotations
from typing import Any
from pydantic import JsonValue
from sqlalchemy import select,or_,literal,exists,union
from corpus_structure.serve.protocol import QueryContext,Positioned
from corpus_structure.serve.queries import Query,Params,Row,T
from corpus_structure.serve.results import TransformationAnswer,RelationAnswer,FamilyAnswer

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
    e=T['kb.entity']
    subjects_and_parameters=select(e.c.id).where(e.c.id.in_(subjects)).union(parameters)
    sources=[select(c.c.id).where(c.c.run_id==ctx.run_id,c.c.subject_id.in_(subjects_and_parameters)),select(c.c.id).where(c.c.run_id==ctx.run_id,c.c.predicate=='stat:member_of_construction',c.c.object_entity_id.in_(subjects))]
    if p.include_suppositions:
        premise=ctx.compiled.lookup.version_sets['ClaimModality'].property('premise_forming')
        sources.append(select(c.c.id).where(c.c.run_id==ctx.run_id,c.c.modality.in_(premise),c.c.object_entity_id.in_(subjects)))
    return ctx.reader.claim_statement(include_candidates=p.include_candidates,include_suppositions=p.include_suppositions).where(c.c.id.in_(union(*sources)))

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
    result=FamilyAnswer
    def rows(self,ctx:QueryContext,p:Where,after:JsonValue=None):
        c=T['kb.claim']
        stmt=ctx.reader.claim_statement(predicate=p.predicate,include_candidates=p.include_candidates,include_suppositions=p.include_suppositions)
        if p.value is not None:
            stmt=stmt.where(c.c.object_value==p.value) if isinstance(p.value,dict) else stmt.where(c.c.object_value['v'].as_string()==str(p.value))
        e,i=T['kb.entity'],T['kb.entity_identity']
        fam=e.alias('family')
        stmt=stmt.where(or_(c.c.subject_id.in_(select(e.c.id).where(e.c.run_id==ctx.run_id,e.c.type=='stat:DistributionFamily')),c.c.subject_id.in_(select(i.c.entity_id).join(fam,fam.c.id==i.c.value_entity_id).where(i.c.slot=='stat:family',fam.c.run_id==ctx.run_id,fam.c.type=='stat:DistributionFamily'))))
        for row in ctx.reader.claims(statement=stmt,after=after,with_premises=False):
            subject=row['subject']
            if subject['type']=='stat:DistributionFamily':
                family=subject
            else:
                key=(subject['identity'].get('stat:family') or {}).get('ref')
                family=next(iter(ctx.entities(key=key)),None)
            if family is not None:
                yield Positioned(FamilyAnswer(key=row['key'],family=family,claim=row),row['key'])
class ParameterMapping(Query):
    name,params='parameter_mapping',MappingParams
    def rows(self,ctx:QueryContext,p:MappingParams,after:JsonValue=None):
        c=T['kb.claim']
        construction=ids(ctx,p.construction)
        family=ids(ctx,p.family)
        subjects=construction+family
        stmt=profile(ctx,p,subjects).where(c.c.predicate.in_(['stat:member_of_construction','stat:has_parameter','stat:identical_parameter','stat:derived_parameter','stat:parameter_role','stat:parameter_domain']),or_(c.c.predicate!='stat:member_of_construction',(c.c.subject_id.in_(family)) & (c.c.object_entity_id.in_(construction))))
        for row in ctx.reader.claims(statement=stmt,after=after):
            yield Positioned(Row.model_validate(row),row['key'])
class Transformations(Query):
    name,params='transformations_of',Family
    result=TransformationAnswer
    def rows(self,ctx:QueryContext,p:Family,after:JsonValue=None):
        c,cr,er=T['kb.claim'],T['kb.claim_ref'],T['kb.claim_entity_ref']
        family=ids(ctx,p.family)
        premise=c.alias('premise')
        candidate_premises=select(premise.c.id).where(premise.c.run_id==ctx.run_id,premise.c.object_entity_id.in_(family)).union(select(er.c.claim_id).where(er.c.run_id==ctx.run_id,er.c.entity_id.in_(family)))
        premise_ids=select(premise.c.id).where(premise.c.run_id==ctx.run_id,premise.c.predicate=='stat:has_distribution',premise.c.id.in_(candidate_premises))
        conclusions=select(cr.c.claim_id).where(cr.c.kind=='condition_premise',cr.c.target_claim_id.in_(premise_ids))
        definition=c.alias('definition')
        stmt=ctx.reader.claim_statement(include_candidates=p.include_candidates,include_suppositions=p.include_suppositions).where(c.c.predicate=='stat:has_distribution',c.c.id.in_(conclusions),exists(select(definition.c.id).where(definition.c.run_id==ctx.run_id,definition.c.statement_id==c.c.statement_id,definition.c.subject_id==c.c.subject_id,definition.c.statement_role=='definiens')))
        if after is not None: stmt=stmt.where(c.c.key>after)
        with ctx.conn.execute(stmt.order_by(c.c.key).execution_options(yield_per=32)) as result:
            for batch in result.mappings().partitions(32):
                meta=list(batch)
                rows=list(ctx.reader.claims(statement=select(c).where(c.c.id.in_([x['id'] for x in meta])),with_premises=False))
                definitions=list(ctx.reader.claims(statement_id=[x['statement_id'] for x in meta],statement_role='definiens',include_suppositions=True,with_premises=False))
                premise_keys={x['key'] for r in rows for x in r['premises'] if x['kind']=='condition_premise'}
                premises=list(ctx.reader.claims(key=list(premise_keys),include_suppositions=True,include_candidates=True,with_premises=False)) if premise_keys else []
                for row in rows:
                    refs={x['key'] for x in row['premises'] if x['kind']=='condition_premise'}
                    defs=[x for x in definitions if x['statement']['key']==row['statement']['key'] and x['subject']['key']==row['subject']['key']]
                    yield Positioned(TransformationAnswer(key=row['key'],conclusion=row,premises=[x for x in premises if x['key'] in refs],definiens=defs),row['key'])
class Relations(Query):
    name,params='relations_between',Between
    result=RelationAnswer
    def rows(self,ctx:QueryContext,p:Between,after:JsonValue=None):
        c=T['kb.claim']
        edges=ctx.reader.claim_statement(include_candidates=p.include_candidates,include_suppositions=p.include_suppositions).where(c.c.predicate.in_(['stat:special_case_of','stat:transformation_of','stat:limit_of']),c.c.object_entity_id.is_not(None)).subquery()
        walk=select(edges.c.subject_id.label('origin'),edges.c.object_entity_id.label('target'),edges.c.key.label('path'),literal(1).label('depth')).where(edges.c.subject_id.in_(ids(ctx,p.a))).cte('paths',recursive=True)
        walk=walk.union_all(select(walk.c.origin,edges.c.object_entity_id,walk.c.path+literal('|')+edges.c.key,walk.c.depth+1).join(edges,edges.c.subject_id==walk.c.target).where(walk.c.depth<4))
        stmt=select(walk).where(walk.c.target.in_(ids(ctx,p.b)))
        if after is not None: stmt=stmt.where(walk.c.path>after)
        for r in ctx.conn.execute(stmt.order_by(walk.c.path)).mappings():
            keys=r['path'].split('|')
            by_key={row['key']:row for row in ctx.reader.claims(key=keys,include_suppositions=True,include_candidates=True,with_premises=False)}
            claims=[by_key[key] for key in keys]
            yield Positioned(RelationAnswer.model_validate({'key':r['path'],'depth':r['depth'],'claims':claims}),r['path'])

QUERIES=(FamilyProfile(),FamiliesWhere(),Relations(),Transformations(),ParameterMapping(),ConstructionProfile())
