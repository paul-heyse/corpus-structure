"""Statistics algorithms composed from the archived semantic fact/value relations."""
from __future__ import annotations
from typing import Any
from itertools import batched
from pydantic import BaseModel, JsonValue
from sqlalchemy import and_, exists, literal, or_, select
from corpus_structure.semantic.query import _same_scope
from corpus_structure.serve.protocol import Positioned
from corpus_structure.serve.queries import Params, Query, Row
from corpus_structure.serve.read import T
from corpus_structure.serve.results import FamilyAnswer, RelationAnswer, TransformationAnswer
class Family(Params): family:str
class Construction(Params): construction:str
class MappingParams(Construction): family:str
class Between(Params):
    a:str
    b:str
class Where(Params):
    predicate:str
    value:Any=None

def ids(ctx,value): return ctx.reader.resolve(value)
def base(ctx,p): return ctx.reader.fact_statement(include_candidates=p.include_candidates,include_suppositions=p.include_suppositions)
def target(ctx,root,targets):
    v=T["typed_value"]
    return exists(select(1).where(ctx.reader.scope(v),v.c.value_id == root,v.c.entity_id.in_(targets)))
def parameters(ctx,subjects):
    f,v=T["fact"].alias(),T["typed_value"].alias()
    return select(f.c.subject_id).join(v,and_(_same_scope(f,v),f.c.object_value_id == v.c.value_id)).where(ctx.reader.scope(f),f.c.property_id == ctx.reader.iri("stat:family"),v.c.entity_id.in_(subjects))
def profile(ctx,p,subjects):
    f=T["fact"]
    return base(ctx,p).where(or_(f.c.subject_id.in_(subjects),f.c.subject_id.in_(parameters(ctx,subjects)),and_(f.c.property_id == ctx.reader.iri("stat:member_of_construction"),target(ctx,f.c.object_value_id,subjects))))
class FamilyProfile(Query):
    name,params="family_profile",Family
    def rows(self,ctx,p,after=None):
        for row in ctx.reader.claims(statement=profile(ctx,p,ids(ctx,p.family)),after=after): yield Row(row)
class ConstructionProfile(Query):
    name,params="construction_profile",Construction
    def rows(self,ctx,p,after=None):
        subjects=ids(ctx,p.construction)
        stmt=profile(ctx,p,subjects)
        if p.include_suppositions:
            f,r,v=T["fact"],T["value_role"],T["typed_value"]
            roots=select(f.c.qualification_value_id).where(ctx.reader.scope(f),f.c.subject_id.in_(subjects))
            variables=select(v.c.entity_id).join(r,and_(_same_scope(r,v),r.c.child_value_id == v.c.value_id)).where(ctx.reader.scope(v),r.c.parent_value_id.in_(roots),r.c.role == "base_variable")
            stmt=base(ctx,p).where(or_(f.c.fact_id.in_(stmt.with_only_columns(f.c.fact_id)),f.c.subject_id.in_(variables)))
        for row in ctx.reader.claims(statement=stmt,after=after): yield Row(row)
class FamiliesWhere(Query):
    result: type[BaseModel]
    name,params,result="families_where",Where,FamilyAnswer
    def rows(self,ctx,p,after=None):
        f,v=T["fact"],T["typed_value"]
        families=ctx.reader.entity_ids(class_name="DistributionFamily")
        stmt=base(ctx,p).where(f.c.property_id == ctx.reader.iri(p.predicate),or_(f.c.subject_id.in_(families),f.c.subject_id.in_(parameters(ctx,families))))
        for batch in batched(ctx.reader.claims(statement=stmt,after=after),ctx.row_batch):
            subject_ids={row.fact.subject.entity_id for row in batch}
            family_by_subject={row.fact.subject.entity_id:row.fact.subject for row in batch if any(m.class_iri == ctx.reader.iri("DistributionFamily") for m in row.fact.subject.memberships)}
            parent_rows=ctx.conn.execute(select(f.c.subject_id,v.c.entity_id).join(v,and_(_same_scope(f,v),f.c.object_value_id == v.c.value_id)).where(ctx.reader.scope(f),f.c.subject_id.in_(subject_ids-family_by_subject.keys()),f.c.property_id == ctx.reader.iri("stat:family"))).all()
            parents=ctx.session._entities({row.entity_id for row in parent_rows})
            family_by_subject.update({row.subject_id:parents[row.entity_id] for row in parent_rows})
            for row in batch:
                if p.value is not None:
                    cls=next(d for d in ctx.compiled.definitions if d.iri in {m.class_iri for m in row.fact.subject.memberships} and any(x.iri == row.fact.property_iri for x in d.properties))
                    prop=next(x for x in cls.properties if x.iri == row.fact.property_iri)
                    expected=ctx.compiled.property_adapter(cls.name,prop.name,item=prop.multivalued).validate_python(p.value)
                    if expected != row.fact.object: continue
                family=family_by_subject.get(row.fact.subject.entity_id)
                if family is not None: yield Positioned(FamilyAnswer(family=family,claim=row),row.fact.occurrence_id or row.fact.fact_id)

class ParameterMapping(Query):
    name,params="parameter_mapping",MappingParams
    def rows(self,ctx,p,after=None):
        f=T["fact"]; construction=ids(ctx,p.construction);family=ids(ctx,p.family)
        stmt=profile(ctx,p,construction+family).where(f.c.property_id.in_([ctx.reader.iri("stat:"+name) for name in ("member_of_construction","has_parameter","identical_parameter","derived_parameter","parameter_role","parameter_domain")]),or_(f.c.property_id != ctx.reader.iri("stat:member_of_construction"),and_(f.c.subject_id.in_(family),target(ctx,f.c.object_value_id,construction))))
        for row in ctx.reader.claims(statement=stmt,after=after): yield Row(row)
def condition_refs(claim):
    def walk(value):
        if hasattr(value,"model_dump"): value=value.model_dump(mode="python")
        if isinstance(value,dict):
            if value.get("kind") == "claim" and isinstance(value.get("ref"),str): yield value["ref"]
            for child in value.values(): yield from walk(child)
        elif isinstance(value,(tuple,list)):
            for child in value: yield from walk(child)
    return set(walk(claim.fact.qualification))
class Transformations(Query):
    result: type[BaseModel]
    name,params,result="transformations_of",Family,TransformationAnswer
    def rows(self,ctx,p,after=None):
        f=T["fact"]; family=ids(ctx,p.family)
        candidates=base(ctx,p).where(f.c.property_id == ctx.reader.iri("stat:has_distribution"))
        # The algorithm's decision universe includes all premises; paging selects conclusions only.
        premises={r.fact.fact_id:r for r in ctx.reader.claims(statement=ctx.reader.fact_statement(include_candidates=True,include_suppositions=True).where(f.c.property_id == ctx.reader.iri("stat:has_distribution"),target(ctx,f.c.object_value_id,family)))}
        o,c=T["occurrence"],T["occurrence_context"]
        for batch in batched(ctx.reader.claims(statement=candidates,after=after),ctx.row_batch):
            refs_by_fact={row.fact.fact_id:condition_refs(row)&premises.keys() for row in batch}
            wanted={row.fact.fact_id for row in batch if refs_by_fact[row.fact.fact_id]}
            if not wanted: continue
            contexts=ctx.conn.execute(select(o.c.fact_id,c.c.statement_entity_id).join(c,and_(_same_scope(o,c),o.c.occurrence_id == c.c.occurrence_id)).where(ctx.reader.scope(o),o.c.fact_id.in_(wanted),c.c.statement_entity_id.is_not(None))).all()
            statements_by_fact={key:{r.statement_entity_id for r in contexts if r.fact_id == key} for key in wanted}
            statement_ids={r.statement_entity_id for r in contexts}
            definition_contexts=ctx.conn.execute(select(o.c.fact_id,c.c.statement_entity_id).join(c,and_(_same_scope(o,c),o.c.occurrence_id == c.c.occurrence_id)).where(ctx.reader.scope(o),c.c.statement_entity_id.in_(statement_ids),c.c.statement_role == "definiens")).all()
            definitions=tuple(ctx.reader.claims(statement=ctx.reader.fact_statement(include_candidates=p.include_candidates,include_suppositions=True).where(f.c.fact_id.in_({r.fact_id for r in definition_contexts}))))
            for conclusion in batch:
                key=conclusion.fact.fact_id
                if key not in wanted: continue
                def_ids={r.fact_id for r in definition_contexts if r.statement_entity_id in statements_by_fact[key]}
                defs=tuple(d for d in definitions if d.fact.fact_id in def_ids and d.fact.subject.entity_id == conclusion.fact.subject.entity_id)
                if defs: yield Positioned(TransformationAnswer(conclusion=conclusion,premises=tuple(premises[k] for k in sorted(refs_by_fact[key])),definiens=defs),conclusion.fact.occurrence_id or conclusion.fact.fact_id)

class Relations(Query):
    result: type[BaseModel]
    name,params,result="relations_between",Between,RelationAnswer
    def rows(self,ctx,p,after=None):
        f,v=T["fact"],T["typed_value"]
        edges=base(ctx,p).join(v,and_(_same_scope(f,v),f.c.object_value_id == v.c.value_id)).with_only_columns(f.c.fact_id,f.c.subject_id,v.c.entity_id.label("target")).where(f.c.property_id.in_([ctx.reader.iri("stat:"+n) for n in ("special_case_of","transformation_of","limit_of")]),v.c.kind == "entity").subquery()
        walk=select(edges.c.subject_id.label("origin"),edges.c.target,edges.c.fact_id.label("path"),literal(1).label("depth")).where(edges.c.subject_id.in_(ids(ctx,p.a))).cte("semantic_relation_paths",recursive=True)
        walk=walk.union_all(select(walk.c.origin,edges.c.target,walk.c.path+literal("|")+edges.c.fact_id,walk.c.depth+1).join(edges,edges.c.subject_id == walk.c.target).where(walk.c.depth < 4))
        stmt=select(walk).where(walk.c.target.in_(ids(ctx,p.b)))
        if after is not None: stmt=stmt.where(walk.c.path.collate("C") > str(after))
        for batch in ctx.conn.execute(stmt.order_by(walk.c.path.collate("C"))).mappings().partitions(ctx.row_batch):
            keys={key for row in batch for key in row["path"].split("|")}
            facts={r.fact.fact_id:r for r in ctx.reader.claims(statement=ctx.reader.fact_statement(include_candidates=True,include_suppositions=True).where(f.c.fact_id.in_(keys)))}
            for row in batch:
                yield Positioned(RelationAnswer(depth=row["depth"],claims=tuple(facts[k] for k in row["path"].split("|"))),row["path"])
QUERIES=(FamilyProfile(),FamiliesWhere(),Relations(),Transformations(),ParameterMapping(),ConstructionProfile())
