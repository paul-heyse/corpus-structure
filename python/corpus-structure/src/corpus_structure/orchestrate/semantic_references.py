"""Bound global references supported by selected claims on the current source document."""
from __future__ import annotations
from dataclasses import dataclass
import json
from sqlalchemy import and_,select,union,or_,func
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationConflict

@dataclass(frozen=True)
class KnownReference:
    entity_id:str
    classes:tuple[str,...]
    label:str
    aliases:tuple[str,...]


def document_references(conn,view,document_id:int,*,limit:int):
    """Use release-declared global scope and display properties; refuse a truncated universe."""
    from corpus_structure.semantic.references import read_reference_classes
    from corpus_structure.semantic.query import SnapshotBinding,StaleSnapshot,WrongRelease
    binding=view.binding
    snapshot=SnapshotBinding(binding.release_id,binding.input_realization_id,binding.input_revision,f"semantic-run:{view.run_id}")
    meta=[json.loads(row.body) for row in view.prepared.registry_rows if row.kind=='operation_class']
    global_classes={row['iri'] for row in meta if row.get('cs:scope')=='global'}
    try:read_reference_classes(conn,snapshot,())
    except (StaleSnapshot,WrongRelease) as exc:raise OperationConflict(str(exc)) from exc
    if not global_classes:return ()
    f,v,selected,support,oe,ev,member=map(table,('data.fact','data.typed_value','data.selection','data.support','data.occurrence_evidence','data.evidence','data.membership'))
    def same(a,b):return and_(a.c.release_id==b.c.release_id,a.c.realization_id==b.c.realization_id)
    d=table('kb.document')
    uri=conn.execute(select(d.c.source_uri).where(d.c.id==document_id)).scalar_one()
    facts=select(f.c.subject_id,v.c.entity_id).join(v,and_(same(f,v),f.c.object_value_id==v.c.value_id)).join(selected,and_(same(f,selected),f.c.fact_id==selected.c.fact_id)).join(support,and_(same(f,support),f.c.fact_id==support.c.fact_id)).join(oe,and_(same(support,oe),support.c.occurrence_id==oe.c.occurrence_id)).join(ev,and_(same(oe,ev),oe.c.evidence_id==ev.c.evidence_id)).where(f.c.release_id==binding.release_id,f.c.realization_id==binding.input_realization_id,ev.c.source_uri==uri).subquery()
    candidates=union(select(facts.c.subject_id.label('entity_id')),select(facts.c.entity_id).where(facts.c.entity_id.is_not(None))).subquery()
    ids=tuple(conn.execute(select(candidates.c.entity_id).join(member,and_(member.c.entity_id==candidates.c.entity_id,member.c.release_id==binding.release_id,member.c.realization_id==binding.input_realization_id,member.c.class_id.in_(global_classes))).distinct().order_by(candidates.c.entity_id).limit(limit+1)).scalars())
    if len(ids)>limit:raise OperationConflict(f'document reference universe exceeds packet limit {limit}')
    try:classes=read_reference_classes(conn,snapshot,ids)
    except (StaleSnapshot,WrongRelease) as exc:raise OperationConflict(str(exc)) from exc
    display_meta=[json.loads(row.body) for row in view.prepared.registry_rows if row.kind=='operation_property']
    scalar=set();multiple=set()
    definitions={definition.name:definition for definition in view.prepared.definitions}
    for row in display_meta:
        if row.get('cs:role')!='display':continue
        prop=next(p for p in definitions[row['class']].properties if p.iri==row['property'])
        (multiple if prop.multivalued else scalar).add(prop.iri)
    labels={entity:[] for entity in ids};aliases={entity:[] for entity in ids}
    role=table('data.value_role');child=v.alias('display_member')
    display=select(f.c.subject_id,f.c.property_id,func.coalesce(v.c.text_value,child.c.text_value)).join(v,and_(same(f,v),f.c.object_value_id==v.c.value_id)).join(selected,and_(same(f,selected),f.c.fact_id==selected.c.fact_id)).outerjoin(role,and_(same(v,role),role.c.parent_value_id==v.c.value_id,v.c.kind=='sequence',role.c.role=='item')).outerjoin(child,and_(same(role,child),role.c.child_value_id==child.c.value_id,child.c.kind=='string')).where(f.c.release_id==binding.release_id,f.c.realization_id==binding.input_realization_id,f.c.subject_id.in_(ids),f.c.property_id.in_(scalar|multiple),or_(v.c.kind=='string',and_(v.c.kind=='sequence',child.c.text_value.is_not(None)))).order_by(f.c.subject_id,f.c.property_id,v.c.text_value,role.c.position)
    for entity,prop,text in conn.execute(display):
        (labels if prop in scalar else aliases)[entity].append(text)
    return tuple(KnownReference(entity,classes[entity],labels[entity][0] if labels[entity] else entity,tuple(sorted(set(aliases[entity])))) for entity in ids)
