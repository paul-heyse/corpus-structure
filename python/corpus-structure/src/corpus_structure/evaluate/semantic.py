"""Independent, immutable references and grades on the admitted semantic release.

Only the evaluator principal can call the protected storage functions. These rows are never
inputs to source proposals, consolidation, publication or the extractor's tool server.
"""
from __future__ import annotations

import copy
import json
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from collections.abc import Mapping,Sequence
from typing import Any
from sqlalchemy import Connection,select,text
from pydantic import BaseModel,ConfigDict
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.releases import load_release
from corpus_structure.semantic.proposals import ProposalFrame,locate_proposal
from .semantic_alignment import SemanticSide,TierCounts,align_semantic

class ReferenceError(ValueError):
    """A reference is incomplete, stale or belongs to another immutable binding."""

class ReferenceReport(BaseModel):
    model_config=ConfigDict(frozen=True,extra='forbid')
    id:int
    project_id:str
    run_id:int
    set_id:int
    reference_snapshot:list[dict[str,Any]]
    result:dict[str,Any]

@dataclass(frozen=True)
class StoredReferencePass:
    id:int
    unit_id:int
    release_id:str
    pass_kind:str
    authored:bytes
    content_digest:str
    frame_id:int
    frame:tuple[dict[str,Any],...]
    rendition_id:int
    rendition_digest:str
    batch:Mapping[str,Any]

def _call(conn,sql,**params):
    return conn.execute(text(sql),params)

def _json(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False,default=lambda v:str(v))

def _unit(conn,unit_id):
    u,s=table('eval.reference_unit'),table('eval.reference_set')
    result=conn.execute(select(u,s.c.release_id,s.c.project_id,s.c.source_run_id).join(s,u.c.set_id==s.c.id).where(u.c.id==unit_id)).mappings().one_or_none()
    if result is None:raise ReferenceError(f'unknown reference unit {unit_id}')
    return result

def _completed(conn,run_id,project_id=None):
    c,r=table('ops.completed_result'),table('ops.run')
    row=conn.execute(select(c,r.c.project_id).join(r,c.c.run_id==r.c.id).where(c.c.run_id==run_id)).mappings().one_or_none()
    if row is None or project_id is not None and row['project_id']!=project_id:raise ReferenceError('completed result does not belong to the selected project')
    return row

def _source_units(conn,run_id):
    """Units actually represented in the completed cut, including reused origin tasks."""
    return conn.execute(text('''SELECT DISTINCT o.rendition_id,o.payload->>'unit_ref' AS unit_key,d.source_uri
      FROM ops.completed_result c JOIN ops.cut_task ct ON ct.cut_id=c.cut_id
      JOIN kb.observation o ON o.task_id=ct.origin_task_id
      JOIN kb.rendition r ON r.id=o.rendition_id JOIN kb.document d ON d.id=r.document_id
      WHERE c.run_id=:run AND o.payload_definition='AgentStoredBatch'
        AND o.payload->>'unit_ref' IS NOT NULL ORDER BY unit_key,o.rendition_id'''),{'run':run_id}).mappings().all()

def create_reference_set(conn:Connection,*,project_id:str,source_run_id:int,label:str,split:str='dev',size:int|None=None,seed:int=0,guideline:str|None=None,forced:Sequence[str]=())->dict[str,Any]:
    from .sampling import PoolUnit,sample
    result=_completed(conn,source_run_id,project_id)
    release=load_release(conn,result['release_id'])
    pool=_source_units(conn,source_run_id)
    assigned={row.source_uri:row.split for row in conn.execute(select(table('eval.document_split')).where(table('eval.document_split').c.project_id==project_id))}
    pool=[u for u in pool if assigned.get(u['source_uri'])==split]
    if not pool:raise ReferenceError('no completed source units in the requested document split; assign document splits first')
    sampled=sample([PoolUnit(u['unit_key'],'source',0,rendition_id=u['rendition_id']) for u in pool],len(pool) if size is None else size,seed,forced)
    if guideline is None:
        guideline=conn.scalar(select(table('ops.run').c.guideline).where(table('ops.run').c.id==source_run_id)) or 'independent-reference-v1'
    identity=_call(conn,'SELECT eval.create_reference_set(:p,:r,:run,:label,:split,:g,CAST(:sampling AS jsonb))',p=project_id,r=release.release_id,run=source_run_id,label=label,split=split,g=guideline,sampling=_json(sampled.sampling)).scalar_one()
    units={}
    by_key={u['unit_key']:u for u in pool}
    for key in sampled.units:
        units[key]=_call(conn,"SELECT eval.add_reference_unit(:s,:r,:k,'[]'::jsonb)",s=identity,r=by_key[key]['rendition_id'],k=key).scalar_one()
    return {'set_id':identity,'project_id':project_id,'release_id':release.release_id,'source_run_id':source_run_id,'units':units,'sampling':sampled.sampling}

def record_pass(conn:Connection,*,unit_id:int,pass_kind:str,actor:str,authored:bytes,frame:ProposalFrame)->int:
    unit=_unit(conn,unit_id)
    if not isinstance(authored,bytes):raise TypeError('authored reference input must be the exact submitted bytes')
    rendition=conn.execute(select(table('kb.rendition')).where(table('kb.rendition').c.id==unit['rendition_id'])).mappings().one()
    if frame.unit_ref!=unit['unit_key'] or frame.text!=rendition['canonical_text']:raise ReferenceError('reference source frame differs from bound unit/rendition')
    release=load_release(conn,unit['release_id'])
    raw=json.loads(authored)
    # Use the same rich release/reference validator and citation cascade as source admission.
    # Reference bytes remain private and never enter a source task or publication batch.
    known={}
    for entity,cls in conn.execute(select(table('data.membership').c.entity_id,table('data.membership').c.class_id).where(table('data.membership').c.realization_id==_completed(conn,unit['source_run_id'])['output_realization_id'])):
        known.setdefault(entity,[]).append(cls)
    located=locate_proposal(release,raw,frame,known_classes={k:tuple(v) for k,v in known.items()})
    if not located.clean:raise ReferenceError('reference citations must be unambiguous and exactly located: '+str(located.issues))
    stored=located.stored.model_dump(mode='json',exclude_none=True)
    entries=[]
    for family in ('claims','unsupported','identity_exclusions'):
        for item in stored.get(family,()):
            for i,citation in enumerate(item['evidence']):
                entries.append({**citation,'family':family,'item_ref':item['id'],'evidence_index':i})
    return int(_call(conn,'SELECT eval.record_reference_pass(:u,:k,:a,:b,CAST(:f AS jsonb))',u=unit_id,k=pass_kind,a=actor,b=authored,f=_json(entries)).scalar_one())

def read_pass(conn:Connection,pass_id:int,*,frame_id:int|None=None)->StoredReferencePass:
    p,f=table('eval.reference_pass'),table('eval.reference_frame')
    row=conn.execute(select(p).where(p.c.id==pass_id)).mappings().one()
    unit=_unit(conn,row['unit_id'])
    query=select(f).where(f.c.pass_id==pass_id)
    query=query.where(f.c.id==frame_id) if frame_id is not None else query.order_by(f.c.version.desc()).limit(1)
    citation=conn.execute(query).mappings().one()
    authored=bytes(row['authored'])
    if sha256(authored).hexdigest()!=row['content_digest']:raise ReferenceError('reference authored bytes no longer match their digest')
    release=load_release(conn,unit['release_id'])
    batch=release.validate_json('AgentAuthoredBatch',authored).model_dump(mode='json')
    fields={(e['family'],e['item_ref'],e['evidence_index']):e for e in citation['frame']}
    for family in ('claims','unsupported','identity_exclusions'):
        for item in batch.get(family,()):
            for i,e in enumerate(item.get('evidence',())):
                placed=fields.get((family,item['id'],i))
                if placed is None or placed['quote']!=e['quote']:raise ReferenceError('immutable frame is incomplete for its authored reference pass')
                item['evidence'][i]={k:v for k,v in placed.items() if k not in {'family','item_ref','evidence_index'}}
    validated=release.validate_json('AgentStoredBatch',_json(batch)).model_dump(mode='json')
    return StoredReferencePass(pass_id,row['unit_id'],unit['release_id'],row['pass_kind'],authored,row['content_digest'],citation['id'],tuple(citation['frame']),citation['rendition_id'],citation['rendition_digest'],validated)

def ensure_items(conn:Connection,pass_id:int,*,frame_id:int|None=None)->StoredReferencePass:
    stored=read_pass(conn,pass_id,frame_id=frame_id)
    items=sorted([{'item_kind':family,'local_ref':item['id'],'payload':item} for family in ('entities','statements','claims','unsupported','identity_exclusions','alternatives') for item in stored.batch.get(family,())],key=lambda x:(x['item_kind'],x['local_ref']))
    _call(conn,'SELECT eval.record_reference_items(:p,:f,CAST(:i AS jsonb))',p=pass_id,f=stored.frame_id,i=_json(items))
    return stored

def relocate_frame(conn:Connection,pass_id:int,*,rendition_id:int)->int:
    stored=read_pass(conn,pass_id)
    rendition=conn.execute(select(table('kb.rendition')).where(table('kb.rendition').c.id==rendition_id)).mappings().one()
    new=[]
    for entry in stored.frame:
        quote=entry['quote'];text_=rendition['canonical_text'];start=text_.find(quote)
        if start<0 or text_.find(quote,start+1)>=0:raise ReferenceError('reference frame is stale: citation is absent or has ambiguous relocation')
        new.append({**entry,'start':start,'end':start+len(quote)})
    return int(_call(conn,'SELECT eval.relocate_reference_frame(:p,:parent,:r,CAST(:f AS jsonb))',p=pass_id,parent=stored.frame_id,r=rendition_id,f=_json(new)).scalar_one())

def unit_passes(conn:Connection,unit_id:int)->dict[str,list[int]]:
    p=table('eval.reference_pass');result={kind:[] for kind in ('A','B','C')}
    for row in conn.execute(select(p.c.id,p.c.pass_kind).where(p.c.unit_id==unit_id).order_by(p.c.id)):result[row.pass_kind].append(row.id)
    return result

def latest_pass_c(conn:Connection,unit_id:int)->StoredReferencePass|None:
    ids=unit_passes(conn,unit_id)['C']
    return read_pass(conn,ids[-1]) if ids else None

def golden_units(conn:Connection,project_id:str,label:str,split:str|None=None)->list[dict[str,Any]]:
    u,s=table('eval.reference_unit'),table('eval.reference_set')
    query=select(u,s.c.split).join(s,u.c.set_id==s.c.id).where(s.c.project_id==project_id,s.c.label==label)
    if split is not None:query=query.where(s.c.split==split)
    return [dict(r) for r in conn.execute(query.order_by(u.c.unit_key)).mappings()]

def golden_set_status(conn:Connection,set_id:int)->dict[str,Any]:
    u=table('eval.reference_unit');units=conn.execute(select(u).where(u.c.set_id==set_id)).mappings().all();counts=Counter()
    for unit in units:
        passes=unit_passes(conn,unit['id'])
        counts['adjudicated' if passes['C'] else 'double_passed' if passes['A'] and passes['B'] else 'draft']+=1
    return {'set_id':set_id,'units':len(units),'status':dict(counts)}

def split_documents(conn:Connection,project_id:str,config=None,seed:int|None=None)->dict[str,Any]:
    from .split import SplitConfig,SplitDocument,Assignment,assign
    from corpus_structure.core.vocab import DocumentSplit
    config=SplitConfig() if config is None else config
    d=table('kb.document');docs=[SplitDocument(r.id,r.source_uri,None) for r in conn.execute(select(d).where(d.c.project_id==project_id))]
    previous={r.source_uri:r.split for r in conn.execute(select(table('eval.document_split')).where(table('eval.document_split').c.project_id==project_id))}
    existing={d.id:Assignment(d.id,DocumentSplit(previous[d.source_uri]),'persisted',None) for d in docs if d.source_uri in previous}
    new=assign(docs,config,existing,seed)
    for row in new:_call(conn,'SELECT eval.assign_document_split(:p,:u,:s)',p=project_id,u=next(d.source_uri for d in docs if d.id==row.document_id),s=row.split.value)
    totals=Counter(previous.values());totals.update(row.split.value for row in new)
    return {'project_id':project_id,'seed':config.seed if seed is None else seed,'added':dict(Counter(r.split.value for r in new)),'total':dict(totals)}

def _prediction(conn,completed,unit):
    """Admitted completed source occurrences, not raw task reports or selected-pointer guesses."""
    observations=conn.execute(text('''SELECT DISTINCT o.id,o.payload,o.observation_key FROM kb.observation o
      JOIN data.occurrence x ON x.source=o.observation_key AND x.release_id=o.release_id
      WHERE x.realization_id=:z AND x.release_id=:r AND o.rendition_id=:rendition
      AND o.payload_definition='AgentStoredBatch' AND o.payload->>'unit_ref'=:unit ORDER BY o.id'''),{'z':completed['output_realization_id'],'r':completed['release_id'],'rendition':unit['rendition_id'],'unit':unit['unit_key']}).mappings().all()
    rows=conn.execute(select(table('data.occurrence')).where(table('data.occurrence').c.realization_id==completed['output_realization_id'],table('data.occurrence').c.release_id==completed['release_id'])).mappings().all()
    admitted={(r['source'],r['item']):r['fact_id'] for r in rows}
    declarations=conn.execute(select(table('data.entity_source')).where(table('data.entity_source').c.realization_id==completed['output_realization_id'],table('data.entity_source').c.release_id==completed['release_id'])).mappings().all()
    mappings={(r['observation_id'],r['local_id']):r['entity_id'] for r in declarations}
    batch={'unit_ref':unit['unit_key'],'entities':[],'statements':[],'claims':[],'alternatives':[]};known={};seen=set()
    for observation in observations:
        source=observation['payload'];prefix=str(observation['id'])+'/'
        # Source-local identifiers are scoped before combining independent extraction reports.
        ids={item['id']:mappings.get((observation['id'],item['id']),prefix+item['id']) for family in ('entities','statements','claims','unsupported') for item in source.get(family,())}
        def rewrite(value):
            if isinstance(value,dict):return {k:(ids.get(v,v) if k in {'target','subject','statement','attribution','entity','ref','claim'} and isinstance(v,str) else rewrite(v)) for k,v in value.items()}
            if isinstance(value,list):return [rewrite(v) for v in value]
            return value
        for family in ('entities','statements'):
            for item in source.get(family,()):
                value=rewrite(item);value['id']=ids[item['id']]
                if not any(v['id']==value['id'] for v in batch[family]):batch[family].append(value)
                if (observation['id'],item['id']) in mappings:known[value['id']]=mappings[observation['id'],item['id']]
        for index,claim in enumerate(source.get('claims',())):
            fact=admitted.get((observation['observation_key'],'claims/'+str(index)))
            if fact is None:continue
            c=rewrite(copy.deepcopy(claim));c['id']=ids[claim['id']]
            if fact in seen:
                old=next(v for v in batch['claims'] if v['_fact_id']==fact)
                old['evidence'].extend(e for e in c.get('evidence',()) if e not in old['evidence'])
                continue
            seen.add(fact);c['_fact_id']=fact;batch['claims'].append(c)
    for c in batch['claims']:c.pop('_fact_id',None)
    return SemanticSide(unit['unit_key'],batch,known_ids=known)

def agreement(conn:Connection,unit_id:int)->dict[str,Any]:
    passes=unit_passes(conn,unit_id)
    if not passes['A'] or not passes['B']:raise ReferenceError('agreement requires independent A and B passes')
    a,b=ensure_items(conn,passes['A'][-1]),ensure_items(conn,passes['B'][-1]);unit=_unit(conn,unit_id)
    if a.rendition_id!=b.rendition_id or a.rendition_digest!=b.rendition_digest:raise ReferenceError('agreement requires the same source rendition')
    prepared=load_release(conn,unit['release_id']);ctx=frozenset(unit['context'])
    return {'unit_id':unit_id,'pass_a':a.id,'pass_b':b.id,'a_to_b':align_semantic(SemanticSide(unit['unit_key'],a.batch,ctx),SemanticSide(unit['unit_key'],b.batch,ctx),prepared).as_dict(),'b_to_a':align_semantic(SemanticSide(unit['unit_key'],b.batch,ctx),SemanticSide(unit['unit_key'],a.batch,ctx),prepared).as_dict()}

def reference_evaluate(conn:Connection,*,project_id:str,run_id:int,set_id:int)->ReferenceReport:
    completed=_completed(conn,run_id,project_id)
    definition=conn.execute(select(table('eval.reference_set')).where(table('eval.reference_set').c.id==set_id,table('eval.reference_set').c.project_id==project_id)).mappings().one()
    if definition['release_id']!=completed['release_id']:raise ReferenceError('references and completed result have different releases; explicit reference migration is required')
    prepared=load_release(conn,completed['release_id'])
    snapshot=_call(conn,'SELECT eval.reference_snapshot(:s)',s=set_id).scalar_one()
    units=conn.execute(select(table('eval.reference_unit')).where(table('eval.reference_unit').c.set_id==set_id).order_by(table('eval.reference_unit').c.id)).mappings().all()
    if not units or len(snapshot)!=len(units):raise ReferenceError('every reference unit requires an adjudicated pass C')
    snaps={s['unit_id']:s for s in snapshot};reports=[]
    for unit in units:
        snap=snaps[unit['id']];reference=ensure_items(conn,snap['pass_id'],frame_id=snap['frame_id'])
        rendition=conn.scalar(select(table('kb.rendition').c.content_digest).where(table('kb.rendition').c.id==reference.rendition_id))
        if rendition!=reference.rendition_digest:raise ReferenceError('reference citation frame is stale')
        if reference.rendition_id!=unit['rendition_id']:raise ReferenceError('relocated reference requires an explicitly bound target source unit')
        reports.append(align_semantic(SemanticSide(unit['unit_key'],reference.batch,frozenset(unit['context'])),_prediction(conn,completed,unit),prepared).as_dict())
    tiers={k:TierCounts(sum(u['tiers'][k]['reference'] for u in reports),sum(u['tiers'][k]['prediction'] for u in reports),sum(u['tiers'][k]['matched'] for u in reports)).as_dict() for k in ('core','full','evidence')}
    coverage=[dict(row) for row in conn.execute(select(table('data.coverage')).where(table('data.coverage').c.realization_id==completed['output_realization_id'],table('data.coverage').c.release_id==completed['release_id'])).mappings()]
    result={'release_id':completed['release_id'],'output_realization_id':completed['output_realization_id'],'grain':'distinct_fact_per_source_unit','tiers':tiers,'units':reports,'coverage':coverage,'reference_units_scored':len(reports)}
    identity=_call(conn,'SELECT eval.record_reference_evaluation(:p,:run,:s,CAST(:snapshot AS jsonb),CAST(:result AS jsonb))',p=project_id,run=run_id,s=set_id,snapshot=_json(snapshot),result=_json(result)).scalar_one()
    return ReferenceReport(id=identity,project_id=project_id,run_id=run_id,set_id=set_id,reference_snapshot=snapshot,result=result)
