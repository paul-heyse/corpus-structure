"""Materialize a sealed observation cut and publish one fresh evaluated realization.

Source reports remain immutable operational data. Domain policy is an explicit release-bound
operation; storage validity and a singleton candidate never substitute for its findings.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, replace
from hashlib import sha256
from types import MappingProxyType, SimpleNamespace
from typing import Any, Mapping, Protocol

import pyarrow as pa
import yaml
from sqlalchemy import select, text, and_, case, func, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

from .analytics import AnalyticalPacket, AnalysisScope, compile_projection
from .consolidation import SourceItem, assemble
from .identity import canonical_bytes, occurrence_key
from .metadata import table
from .operations import OperationConflict, cut_observations
from .publication import AssessmentRow, CoverageRow, EvidenceRow, EvidenceSourceRow, PublicationBatch, PublicationReceipt, SelectionRow, _publish, publish_on_connection
from .query import SnapshotBinding
from .releases import load_release
from .types import PreparedRelease, ResolvedDependencies, SourceArtifact

RULE_INPUT='operation/domain-rules.yaml'
VERSION='semantic-domain-1'


class DomainOperationRefused(ValueError):
    """A required interpretation or scientific policy is unavailable; no output is selected."""


def domain_rule_inputs(dependencies: ResolvedDependencies, domain: bytes, core: bytes = b'', *, aliases: Mapping[str,Any] | None = None) -> ResolvedDependencies:
    """Archive existing rules as one operation dependency, never read latest files in a run."""
    source=yaml.safe_load(domain) or {}
    base=yaml.safe_load(core) or {}
    if set(base)-{'rules'}:
        raise ValueError('core operation rules must contain only rules')
    source['rules']=[*base.get('rules',()),*source.get('rules',())]
    if aliases is not None:source['identity']={'aliases':dict(aliases)}
    if any(a.name==RULE_INPUT for a in dependencies.artifacts):
        raise ValueError('domain rules already declared')
    return replace(dependencies,artifacts=(*dependencies.artifacts,
        SourceArtifact(RULE_INPUT,yaml.safe_dump(source,sort_keys=True).encode())))


@dataclass(frozen=True)
class ClaimCandidate:
    fact_id: str
    occurrence_id: str
    observation_key: str
    local_id: str
    subject: str
    class_name: str
    predicate: str
    object: Any
    qualification: Mapping[str,Any]
    establishment: str
    statement: str | None
    statement_kind: str | None
    statement_role: str | None
    alternatives: tuple[str,...]
    evidence_count: int
    macros: Mapping[str,Any]


@dataclass(frozen=True)
class CutInput:
    cut_id: int
    run_id: int
    project_id: str
    prepared: PreparedRelease
    output_realization_id: str
    reports: tuple[Mapping[str,Any],...]
    candidates: tuple[ClaimCandidate,...]
    batch: PublicationBatch
    entity_metadata: Mapping[str,Mapping[str,Any]]
    source_links: Mapping[str,tuple[int,int,int,int]]


@dataclass(frozen=True)
class PolicyDecision:
    selected: frozenset[str]
    assessments: tuple[AssessmentRow,...]


class DomainPolicy(Protocol):
    release_id: str
    version: str
    def evaluate(self, inputs: CutInput, scope: AnalysisScope, fused: pa.Table) -> PolicyDecision: ...


@dataclass(frozen=True)
class DomainResult:
    run_id: int
    cut_id: int
    realization_id: str
    receipt: PublicationReceipt
    reports: int
    occurrences: int
    data_revision: int
    derivation_receipts: tuple[PublicationReceipt,...] = ()


def _plain(value):
    from pydantic import BaseModel
    if isinstance(value,BaseModel):return {k:_plain(v) for k,v in value if k in value.model_fields_set}
    if isinstance(value,(list,tuple)):return [_plain(v) for v in value]
    if isinstance(value,dict):return {k:_plain(v) for k,v in value.items()}
    return value


def _reference(value,mapping):
    if isinstance(value,str):return mapping.get(value,value)
    if isinstance(value,list):return [_reference(v,mapping) for v in value]
    if isinstance(value,dict):
        # Only typed reference positions are rewritten; source strings and labels remain literal.
        result={k:_reference(v,mapping) if isinstance(v,(dict,list)) else v for k,v in value.items()}
        for field in ('target','entity','claim','ref'):
            if field in result and isinstance(result[field],str):
                result[field]=mapping.get(result[field],result[field])
        return result
    return value


def _property_value(prepared,definition,prop,value,mapping):
    value=_reference(_plain(value),mapping)
    by_name={d.name:d for d in prepared.definitions}
    if prop.range in by_name and not prop.inlined:
        if not isinstance(value,dict) or value.get('kind')!='entity':
            raise DomainOperationRefused('entity relation needs explicit EntityValue')
        return value['target']
    if prop.range in by_name:return value
    kind=value.get('kind') if isinstance(value,dict) else None
    primitive={'text':'text','number':'number','boolean':'boolean','date':'date','datetime':'instant'}
    if kind not in primitive:raise DomainOperationRefused('no admitted primitive projection for source value')
    raw=value[primitive[kind]]
    # The generated adapter remains authoritative for aliases, enums and exact bounds.
    if prop.range=='integer' and kind=='number' and raw==int(raw):raw=int(raw)
    return raw


def _cut_input(engine:Engine,cut_id:int,output:str)->CutInput:
    with engine.connect().execution_options(isolation_level='REPEATABLE READ') as conn,conn.begin():
        conn.exec_driver_sql('SET TRANSACTION READ ONLY')
        cut=conn.execute(select(table('ops.input_cut')).where(table('ops.input_cut').c.id==cut_id)).mappings().one()
        job=conn.execute(select(table('ops.run')).where(table('ops.run').c.id==cut['run_id'])).mappings().one()
        if not cut['final'] or not job['sealed']:
            raise DomainOperationRefused('consolidation requires a sealed final observation cut')
        prepared=load_release(conn,cut['release_id'])
        observations=list({row['id']:row for row in cut_observations(conn,cut_id)}.values())
        descriptors={}
        o,t,seg=table('kb.observation'),table('ops.task'),table('kb.segment')
        config,method=table('ops.method_config'),table('ops.method')
        effective=func.coalesce(o.c.rendition_id,seg.c.rendition_id,
                               case((t.c.unit_type=='rendition',t.c.unit_id)))
        source_rows=conn.execute(select(o.c.id,effective.label('rendition_id'),
            method.c.name.label('provider'),method.c.version).select_from(o.join(t,t.c.id==o.c.task_id)
            .join(config,config.c.id==t.c.method_config_id).join(method,method.c.id==config.c.method_id)
            .outerjoin(seg,and_(t.c.unit_type=='segment',seg.c.id==t.c.unit_id)))
            .where(o.c.id.in_([row['id'] for row in observations]))).mappings().all()
        chosen=set(conn.execute(select(table('ops.run_rendition').c.rendition_id).where(
            table('ops.run_rendition').c.run_id==job['id'])).scalars())
        renditions={}
        r,d=table('kb.rendition'),table('kb.document')
        for row in conn.execute(select(r,d.c.source_uri,d.c.meta).join(d,d.c.id==r.c.document_id).where(
                r.c.id.in_({row['rendition_id'] for row in source_rows if row['rendition_id'] is not None}))).mappings():
            renditions[row['id']]=row
        for source in source_rows:
            rid=source['rendition_id']
            if rid is None:
                descriptors[source['id']]=None
                continue
            if rid not in chosen:
                raise DomainOperationRefused('reused proposal is not located on this run selected rendition')
            ren=renditions[rid]
            descriptors[source['id']]={'rendition_id':rid,'source_uri':ren['source_uri'],'text':ren['canonical_text'],
                'provider':source['provider'],'version':source['version'],'rendition_key':ren['key'],
                'content':ren['content'],'page':ren['meta'].get('page',ren['source_uri'])}
        tasks=conn.execute(select(table('ops.task')).where(table('ops.task').c.run_id==job['id'])).mappings().all()
        envelopes=conn.execute(select(table('ops.task_result')).join(table('ops.cut_task'),
            table('ops.cut_task').c.origin_task_id==table('ops.task_result').c.task_id).where(
            table('ops.cut_task').c.cut_id==cut_id)).mappings().all()
    return _project_cut(prepared,job,cut,observations,descriptors,tasks,envelopes,output)


def _entity_mappings(prepared,observations,output):
    """Exact declared identity keys and explicitly global label policy, never fuzzy identity."""
    from corpus_structure.core.keys import LabelRules,normalize_label
    from corpus_structure.core.vocab import CaseRule
    by_iri={d.iri:d for d in prepared.definitions}
    meta={row.name:json.loads(row.body) for row in prepared.registry_rows if row.kind=='operation_class'}
    artifact=next((a for a in prepared.artifacts if a.kind==RULE_INPUT),None)
    policy=yaml.safe_load(artifact.content) if artifact is not None else {}
    aliases=LabelRules.model_validate((policy.get('identity') or {}).get('aliases',{}))
    prefixes={row.name:json.loads(row.body)['uri'] for row in prepared.registry_rows if row.kind=='prefix'}
    def compact(iri):
        choices=[(len(uri),prefix+':'+iri[len(uri):]) for prefix,uri in prefixes.items() if iri.startswith(uri)]
        return max(choices)[1] if choices else iri
    mappings={};entries=[];extra={};parsed={}
    for observation in observations:
        if observation['payload_definition']!='AgentStoredBatch':continue
        payload=prepared.validate_json('AgentStoredBatch',json.dumps(observation['payload'])).model_dump(mode='python',exclude_unset=True)
        parsed[observation['id']]=payload
        mapping={e['id']:'entity:'+sha256(canonical_bytes([prepared.release_id,output,observation['observation_key'],'entities',i,e['id']])).hexdigest()
                 for i,e in enumerate(payload.get('entities',()))}
        mappings[observation['id']]=mapping
        for e in payload.get('entities',()):entries.append((observation,e,by_iri[e['class_iri']]))
    resolved=set();keys={}
    pending=list(entries)
    while pending:
        progress=False;remaining=[]
        for observation,e,definition in pending:
            oid=observation['id'];mapping=mappings[oid]
            fields={p.name:p for p in definition.properties}
            attrs={}
            dependencies=[]
            for attribute in e.get('attributes',()):
                prop=next(p for p in definition.properties if p.iri==attribute['predicate'])
                value=attribute['value']
                if prop.name in {name for g in definition.identity_groups if g!=definition.identity_slots for name in g} and value.get('kind')=='entity' and value.get('target') in mapping:
                    dependencies.append((oid,value['target']))
                attrs[prop.name]=_property_value(prepared,definition,prop,value,mapping)
            if e.get('scope') is not None and 'scope_locator' in fields:
                attrs.setdefault('scope_locator',e['scope']['locator'])
                extra[oid,e['id']]={'scope_locator':e['scope']['locator']}
            groups=[g for g in definition.identity_groups if g!=definition.identity_slots]
            if groups and all(all(name in attrs for name in g) for g in groups):
                if any(dep not in resolved for dep in dependencies):
                    remaining.append((observation,e,definition));continue
                candidates=prepared.entity_keys(definition.name,output,attrs,include_identifier=False)
                matches={keys[key] for key in candidates if key in keys}
                if len(matches)>1:
                    raise DomainOperationRefused('declared keys bridge incompatible existing identity assignments')
                canonical=next(iter(matches)) if matches else min(candidates)
                for key in candidates:keys[key]=canonical
                mapping[e['id']]=canonical
            elif not groups and meta.get(definition.name,{}).get('cs:scope')=='global' and e.get('label'):
                case=CaseRule.PRESERVE if meta[definition.name].get('cs:case')=='preserve' else CaseRule.FOLD
                label=normalize_label(e['label'],compact(definition.iri),aliases,case)
                mapping[e['id']]='entity:'+sha256(canonical_bytes([prepared.release_id,output,definition.iri,'label',label])).hexdigest()
            # An absent/incomplete semantic key never licenses a label merge for a keyed class.
            resolved.add((oid,e['id']));progress=True
        if not progress:
            # Recursive, ungrounded identity declarations retain source-qualified references.
            break
        pending=remaining
    return mappings,extra,parsed


def _project_cut(prepared,job,cut,observations,descriptors,tasks,envelopes,output):
    definitions={d.iri:d for d in prepared.definitions}
    by_name={d.name:d for d in prepared.definitions}
    reports=[];items=[];claims=[];metadata={};coverage=[];source_links={};evidence_roles={};contents={}
    entity_mappings,extra_attributes,parsed=_entity_mappings(prepared,observations,output)
    def coverage_row(family,scope,outcome,reason=None):
        key='coverage:'+sha256(canonical_bytes([cut['id'],family,scope,outcome,reason])).hexdigest()
        coverage.append(CoverageRow(key,family,scope,outcome,reason))
    for task in tasks:
        if task['status'] not in {'done','empty','reused'}:
            coverage_row('task',task['unit_key'] or str(task['id']),
                         'failed' if task['status']=='failed' else 'unanalysed',str(task['status']))
    for envelope in envelopes:
        for c in envelope['body'].get('coverage',()):
            coverage_row(c['family'],c['scope'],c['outcome'],c.get('reason'))
    for observation in observations:
        reports.append(dict(observation))
        if observation['payload_definition']=='SourceObservation' and observation['kind']=='author_markup':
            from corpus_structure.semantic.observations import source_python
            from corpus_structure.semantic.source_projection import project_markup
            from corpus_structure.core.evidence import RenditionContent
            descriptor=descriptors[observation['id']]
            if descriptor is None:
                coverage_row('author_markup',observation['observation_key'],'partial','source rendition unavailable')
                continue
            payload=source_python(observation['payload']['payload'])
            # A source envelope retains the canonical markup segment key in its payload value.
            if payload.get('synthesize') is None:continue
            segment_key=(payload.get('value') or {}).get('segment')
            if segment_key is None:
                coverage_row('author_markup',observation['observation_key'],'partial','markup has no segment locator')
                continue
            if descriptor['rendition_id'] not in contents:
                contents[descriptor['rendition_id']]=RenditionContent.model_validate(descriptor['content'])
            projected=project_markup(prepared,output,observation_key=observation['observation_key'],
                payload=payload,content=contents[descriptor['rendition_id']],
                page=descriptor['page'],source_uri=descriptor['source_uri'],rendition_key=descriptor['rendition_key'],segment_key=segment_key,
                provider=descriptor['provider'],operation_version=descriptor['version'])
            coordinates={eid:(start,end) for eid,start,end in projected.evidence_ranges}
            items.extend(replace(item,evidence=tuple(replace(e,locator='rendition:'+descriptor['rendition_key']+':span:'+str(coordinates[e.evidence_id][0])+':'+str(coordinates[e.evidence_id][1])) for e in item.evidence)) for item in projected.items)
            for ordinal,(eid,start,end) in enumerate(projected.evidence_ranges):
                role=payload['synthesize']['evidence'][ordinal].get('role')
                if role is not None:evidence_roles[eid]=role
                source_links[eid]=(observation['id'],descriptor['rendition_id'],start,end)
            for locator in projected.unresolved:coverage_row('author_markup',locator,'partial','unresolved source reference')
            continue
        if observation['payload_definition']!='AgentStoredBatch':
            coverage_row(observation['kind'],observation['observation_key'],'unanalysed',
                         'source report retained; no domain assertion projection declared')
            continue
        descriptor=descriptors[observation['id']]
        payload=parsed[observation['id']]
        if descriptor is None:
            coverage_row('claim_proposal',payload['unit_ref'],'partial','source rendition unavailable')
            continue
        source=observation['observation_key']
        mapping=entity_mappings[observation['id']]
        statements={s['id']:s for s in payload.get('statements',())}
        from .source_projection import statement_identity
        statement_ids={ref:statement_identity(prepared.release_id,output,descriptor['rendition_key'],statement['anchor'])
                       for ref,statement in statements.items()}
        # Source local refs are distinct until a declared identity-resolution operation authorizes a merge.
        # This substrate never treats a fuzzy label or ontology mapping as identity.
        source_attributes={}
        for e in payload.get('entities',()):
            entity_id=mapping[e['id']]
            declared_attributes=list(e.get('attributes',()))
            definition=definitions[e['class_iri']]
            for name,value in extra_attributes.get((observation['id'],e['id']),{}).items():
                if not any(a['predicate']==next(p.iri for p in definition.properties if p.name==name) for a in declared_attributes):
                    declared_attributes.append({'predicate':next(p.iri for p in definition.properties if p.name==name),'value':{'kind':'text','text':value}})
            source_attributes[e['id']]=declared_attributes
            current={**e,'id':entity_id,'attributes':declared_attributes}
            prior=metadata.get(entity_id)
            # Rule display projection is deterministic; each source's own attributes
            # below remain distinct and never inherit the last report's values.
            if prior is None or canonical_bytes(current)<canonical_bytes(prior):metadata[entity_id]=current
        from corpus_structure.core.evidence import MacroDef
        from .expression_context import bind_expression_context
        macros={name:MacroDef.model_validate(value) for name,value in descriptor['content'].get('macros',{}).items()}
        claim_rows=[];evidence_by_entity={};claim_refs={}
        for i,claim in enumerate(payload.get('claims',())):
            located=[]
            for j,e in enumerate(claim['evidence']):
                if e.get('outcome')!='located' or e.get('start') is None or e.get('end') is None:continue
                start,end=e['start'],e['end']
                if not 0<=start<end<=len(descriptor['text']):
                    raise DomainOperationRefused('claim evidence lies outside selected rendition')
                # Location uncertainty is source evidence, never silently upgraded to exactness.
                key='evidence:'+sha256(canonical_bytes([source,'claims',i,j,e])).hexdigest()
                locator=canonical_bytes({'locator':e['locator'],'start':start,'end':end,'role':e['role']}).decode()
                located.append(EvidenceRow(key,descriptor['source_uri'],locator,descriptor['provider'],descriptor['version']))
                source_links[key]=(observation['id'],descriptor['rendition_id'],start,end)
                evidence_roles[key]=e['role']
            if not located or not any(e.get('outcome')=='located' and e['role']=='primary' for e in claim['evidence']):
                coverage_row('claim',source+'/'+claim['id'],'partial','no located primary evidence')
                continue
            subject=mapping.get(claim['subject'],claim['subject'])
            if subject not in metadata:
                coverage_row('claim',source+'/'+claim['id'],'partial','bound reference membership projection unavailable')
                continue
            definition=definitions[metadata[subject]['class_iri']]
            prop=next(p for p in definition.properties if p.iri==claim['predicate'])
            obj=_property_value(prepared,definition,prop,bind_expression_context(claim['object'],macros),mapping)
            qual=_reference(bind_expression_context(_plain(claim['qualification']),macros),{**mapping,**statement_ids})
            qclass=next(d.name for d in prepared.definitions if d.name=='AgentClaim')
            qualification_class=next(p.range for p in by_name[qclass].properties if p.name=='qualification')
            item=SourceItem(subject,definition.name,prop.name,obj,qual,source,'claims/'+str(i),claim['establishment'],tuple(located),qualification_class)
            items.append(item);claim_rows.append((claim,item))
            evidence_by_entity.setdefault(subject,tuple(located))
            if isinstance(obj,str) and obj in metadata:evidence_by_entity.setdefault(obj,tuple(located))
            claim_refs[claim['id']]=item
        # Source-declared entity fields use the actual qualified source assertion that names them.
        for local,e in ((e['id'],e) for e in payload.get('entities',())):
            subject=mapping[local]
            if subject not in evidence_by_entity:continue
            evidence=evidence_by_entity[subject]
            qitem=next((it for _,it in claim_rows if it.subject==subject or it.object==subject),None)
            if qitem is None:continue
            definition=definitions[e['class_iri']]
            for index,attribute in enumerate(({'predicate':next(p.iri for p in definition.properties if p.name=='id'),
                                                'value':{'kind':'text','text':subject}},*source_attributes[local])):
                prop=next(p for p in definition.properties if p.iri==attribute['predicate'])
                value=_property_value(prepared,definition,prop,bind_expression_context(attribute['value'],macros),mapping)
                items.append(replace(qitem,subject=subject,class_name=definition.name,property_name=prop.name,
                    object=value,item=f'entities/{local}/attributes/{index}',evidence=evidence))
        for claim,item in claim_rows:
            statement=statements.get(claim.get('statement'))
            if statement is not None:
                sid=statement_ids[claim['statement']]
                props={'id':sid,'locator':statement['anchor']}
                if statement['kind'] in prepared.enum_members('StatementKind'):props['statement_kind']=statement['kind']
                for name,value in props.items():
                    items.append(replace(item,subject=sid,class_name='SourceStatement',property_name=name,
                        object=value,item='statements/'+claim['statement']+'/'+name))
            fid=prepared.fact_identity(output,item.subject,
                next(p.iri for p in by_name[item.class_name].properties if p.name==item.property_name),
                _plain(prepared.property_adapter(item.class_name,item.property_name,
                    item=next(p.multivalued for p in by_name[item.class_name].properties if p.name==item.property_name)).validate_python(item.object,strict=True)),
                _plain(prepared.validate_python(item.qualification_class,item.qualification)),qualification_class=item.qualification_class)
            alternatives=tuple(a['id'] for a in payload.get('alternatives',()) if claim['id'] in a['members'])
            statement=statements.get(claim.get('statement'))
            claims.append(ClaimCandidate(fid,occurrence_key(prepared.release_id,output,source,item.item),source,
                claim['id'],item.subject,item.class_name,claim['predicate'],item.object,item.qualification,
                item.establishment,statement_ids.get(claim.get('statement')),statement.get('kind') if statement else None,
                claim.get('statement_role'),alternatives,len(item.evidence),descriptor['content'].get('macros',{})))
        for unsupported in payload.get('unsupported',()):
            coverage_row('unsupported',source+'/'+unsupported['id'],'partial',unsupported['reason'])
    batch_id='cut:'+sha256(canonical_bytes([prepared.release_id,output,
        [(o['observation_key'],o['payload']) for o in observations],VERSION])).hexdigest()
    batch=assemble(prepared,output,batch_id,tuple(items))
    batch=replace(batch,coverage=tuple(sorted(coverage,key=lambda c:c.coverage_id)))
    # Source links are resolved to native spans only in the final short publication transaction.
    from .publication import OccurrenceContextRow,OccurrenceEvidenceRoleRow
    batch=replace(batch,occurrence_context=tuple(OccurrenceContextRow(c.occurrence_id,c.statement,c.statement_role) for c in claims if c.statement is not None or c.statement_role is not None),
        occurrence_evidence_role=tuple(OccurrenceEvidenceRoleRow(link.occurrence_id,link.evidence_id,evidence_roles[link.evidence_id])
            for link in batch.occurrence_evidence if link.evidence_id in evidence_roles))
    from .publication import EntitySourceRow
    declared={m.entity_id for m in batch.membership}
    batch=replace(batch,entity_source=tuple(sorted({EntitySourceRow(mapping[e['id']],observation['id'],e['id']) for observation in observations if observation['payload_definition']=='AgentStoredBatch' for mapping in (entity_mappings[observation['id']],) for e in parsed[observation['id']].get('entities',()) if mapping[e['id']] in declared},key=lambda row:(row.entity_id,row.observation_id,row.local_id))))
    return CutInput(cut['id'],job['id'],job['project_id'],prepared,output,tuple(reports),tuple(claims),batch,MappingProxyType(metadata),MappingProxyType(source_links))


def consolidate_cut(engine:Engine,cut_id:int,output_realization_id:str,*,policy:DomainPolicy|None=None,
                    attempts:int=3)->DomainResult:
    inputs=_cut_input(engine,cut_id,output_realization_id)
    if policy is None:policy=ReleasedRulesPolicy(inputs.prepared)
    if policy.release_id!=inputs.prepared.release_id:
        raise DomainOperationRefused('scientific policy belongs to another release')
    binding=SnapshotBinding(inputs.prepared.release_id,output_realization_id,0,'cut:'+str(cut_id))
    compiled=compile_projection(inputs.prepared,binding)
    packet=AnalyticalPacket(binding,compiled.projection_id,compiled.profile.digest,
        MappingProxyType({p.name:pa.Table.from_pylist([],schema=p.schema) for p in compiled.relations}),scale=compiled.profile.scale,property_ids=tuple(sorted({p.iri for d in inputs.prepared.definitions for p in d.properties})))
    evidence_type=pa.list_(pa.struct([pa.field('evidence_id',pa.string())]))
    links={o.occurrence_id:[] for o in inputs.batch.occurrence}
    for link in inputs.batch.occurrence_evidence:links[link.occurrence_id].append({'evidence_id':link.evidence_id})
    candidates=pa.Table.from_pylist([{'fact_id':o.fact_id,'occurrence_id':o.occurrence_id,'evidence':links[o.occurrence_id]}
        for o in inputs.batch.occurrence],schema=pa.schema([pa.field('fact_id',pa.string()),pa.field('occurrence_id',pa.string()),pa.field('evidence',evidence_type)]))
    with AnalysisScope(packet) as scope:
        fused=scope.fuse(scope.connection.from_arrow(candidates)).to_arrow_table()
        decision=policy.evaluate(inputs,scope,fused)
    facts={f.fact_id for f in inputs.batch.fact}
    if not decision.selected.issubset(facts):raise DomainOperationRefused('policy selected facts outside its input universe')
    batch=replace(inputs.batch,selection=tuple(SelectionRow(f) for f in sorted(decision.selected)),assessment=decision.assessments)
    source_links=inputs.source_links
    def publish(conn,batch):
        conn.execute(text('SELECT data.begin_evaluation(:cut,:output)'),{'cut':cut_id,'output':output_realization_id})
        done=conn.execute(select(table('ops.run').c.status).where(table('ops.run').c.id==inputs.run_id)).scalar_one()=='finished'
        receipt=publish_on_connection(conn,batch)
        if done:return receipt
        # A source receipt, proof receipts and the run result are one atomic transaction. The
        # source receipt remains its own identity even when inference advances the final revision.
        from .inference import derive
        from .publication import stage_batch
        conn.execute(text('SELECT data.end_stage()'))
        inferred=derive(conn,SnapshotBinding(batch.release_id,batch.realization_id,receipt.data_revision,'cut:'+str(cut_id)))
        if inferred.batch.fact or inferred.batch.derivation:
            stage_batch(conn,inferred.batch)
            conn.execute(text('SELECT data.publish_analysis_batch(:r,:z,:b,:body,:revision)'),
                {'r':batch.release_id,'z':batch.realization_id,'b':inferred.batch.batch_id,
                 'body':inferred.batch.content,'revision':receipt.data_revision})
        conn.execute(text('SELECT data.finish_evaluation(:cut,:output,:batch)'),{'cut':cut_id,'output':output_realization_id,'batch':batch.batch_id})
        return receipt
    # Span sequence IDs must not alter immutable retry/receipt content. Resolve them before the
    # replay owner, then retain that exact frozen batch for all attempts.
    if source_links:
        with engine.begin() as conn:
            rows=[];span=table('kb.span')
            coordinates=sorted({(rid,start,end) for _,rid,start,end in source_links.values()})
            conn.execute(pg_insert(span).values([{'rendition_id':rid,'start_offset':start,'end_offset':end}
                for rid,start,end in coordinates]).on_conflict_do_nothing())
            ids={(row.rendition_id,row.start_offset,row.end_offset):row.id for row in conn.execute(
                select(span).where(tuple_(span.c.rendition_id,span.c.start_offset,span.c.end_offset).in_(coordinates)))}
            for eid,(oid,rid,start,end) in sorted(source_links.items()):
                rows.append(EvidenceSourceRow(eid,oid,rid,ids[rid,start,end]))
        batch=replace(batch,evidence_source=tuple(rows))
    receipt=_publish(engine,batch,publish,attempts=attempts)
    with engine.connect() as conn:
        revision=conn.execute(select(table('data.realization').c.data_revision).where(
            table('data.realization').c.realization_id==output_realization_id)).scalar_one()
        receipts=conn.execute(select(table('data.batch')).where(
            table('data.batch').c.realization_id==output_realization_id,
            table('data.batch').c.release_id==batch.release_id,
            table('data.batch').c.batch_id!=batch.batch_id).order_by(table('data.batch').c.data_revision)).mappings().all()
        proofs=tuple(PublicationReceipt(row['batch_id'],row['data_revision'],row['content_digest']) for row in receipts)
    return DomainResult(inputs.run_id,cut_id,output_realization_id,receipt,len(inputs.reports),len(batch.occurrence),revision,proofs)


class ReleasedRulesPolicy:
    """The existing rule language and finalize decision table over release-derived views."""
    version=VERSION

    def __init__(self,prepared:PreparedRelease):
        from corpus_structure.schema.rulelang import Builtin,Language,Vocabulary
        from corpus_structure.schema.rules import ENTITY,VALUE,STATEMENT,BINDING,NODE,CLAIM
        self.prepared=prepared;self.release_id=prepared.release_id
        artifact=next((a for a in prepared.artifacts if a.kind==RULE_INPUT),None)
        if artifact is None:raise DomainOperationRefused('release has no declared domain rules operation')
        self.source=yaml.safe_load(artifact.content) or {}
        if not isinstance(self.source,dict):raise DomainOperationRefused('domain rule artifact is not an object')
        self.definitions={d.name:d for d in prepared.definitions}
        self.metadata={}
        for row in prepared.registry_rows:
            if row.kind=='operation_property':
                body=json.loads(row.body)
                self.metadata[body['class'],body['property']]=body
        self.prefixes={row.name:json.loads(row.body)['uri'] for row in prepared.registry_rows if row.kind=='prefix'}
        self.enums={}
        for row in prepared.registry_rows:
            if row.kind=='enum_definition':
                body=json.loads(row.body)
                enum_uri=body.get('enum_uri')
                if enum_uri:self.enums[self.compact(prepared.expand_name(enum_uri))]=tuple(prepared.enum_members(row.name))
        # Classes, qualifier schemas and memberships come from the same immutable binding.
        qualifications=[d for d in prepared.definitions if d.name=='Qualification' or 'Qualification' in d.ancestors]
        qtypes={};qprops={}
        for definition in qualifications:
            for prop in definition.properties:
                qprops[prop.name]=prop
                if prop.multivalued and prop.range in self.definitions:
                    fields={p.name:p for p in self.definitions[prop.range].properties}
                    qtypes[prop.name]='map[Value]' if {'key','value'}.issubset(fields) else 'list[string]'
                elif prop.range=='boolean':qtypes[prop.name]='boolean?'
                elif prop.range in {'integer','decimal','float','double'}:qtypes[prop.name]='number?'
                elif prop.range in self.definitions:qtypes[prop.name]='string?'
                else:qtypes[prop.name]='string?'
        self.qprops=qprops
        claim=dict(CLAIM)
        for name in self.source.get('views',{}):claim[name]='list[string]'
        value={**VALUE,'parse':'string?','math_kind':'string?'}
        builtins={'enums':Builtin(self.enums,'map[list[string]]'),
            'is_a':Builtin(self.is_a,'function(string, string)->boolean')}
        for name,values in self.source.get('tables',{}).items():
            if all(isinstance(v,list) for v in values.values()):typ='map[list[string]]'
            elif all(isinstance(v,str) for v in values.values()):typ='map[string]'
            else:raise DomainOperationRefused('unsupported released rule lookup table')
            builtins[name]=Builtin(values,typ)
        classes=frozenset(self.compact(d.iri) for d in prepared.definitions)
        predicates=frozenset(self.compact(p.iri) for d in prepared.definitions for p in d.properties)
        groups=frozenset(g for row in self.metadata.values() for g in row.get('groups',()))
        values={('Claim','predicate'):Vocabulary('predicates',predicates),
            ('Claim','groups'):Vocabulary('predicate subsets',groups),
            ('Entity','type'):Vocabulary('entity classes',classes),
            ('Claim','establishment'):Vocabulary('Establishment',frozenset(prepared.enum_members('Establishment')))}
        from corpus_structure.core.vocab import ParseOutcome,MathKind
        statement_kinds=Vocabulary('StatementKind',frozenset(prepared.enum_members('StatementKind')))
        statement_roles=Vocabulary('StatementRole',frozenset(prepared.enum_members('StatementRole')))
        values[('Claim','statement_kind')]=statement_kinds
        values[('Statement','kind')]=statement_kinds
        values[('Claim','statement_role')]=statement_roles
        values[('Value','parse')]=Vocabulary('ParseOutcome',frozenset(m.value for m in ParseOutcome))
        values[('Value','math_kind')]=Vocabulary('MathKind',frozenset(m.value for m in MathKind))
        values[('Value','t')]=Vocabulary('Value discriminators',frozenset(p.equals_string for d in prepared.definitions
            if d.name=='Value' or 'Value' in d.ancestors for p in d.properties if p.name=='kind' and p.equals_string))
        for prop in qprops.values():
            if prop.range in {row.name for row in prepared.registry_rows if row.kind=='enum_definition'}:
                values['Qualifiers',prop.name]=Vocabulary(prop.range,frozenset(prepared.enum_members(prop.range)))
        self.language=Language(objects={'Claim':claim,'Entity':ENTITY,'Value':value,'Statement':STATEMENT,
            'Binding':BINDING,'Node':NODE,'Qualifiers':qtypes},symbols={'claim':'Claim'},builtins=builtins,
            values=values,arguments={'is_a':(Vocabulary('classes',classes),Vocabulary('classes',classes))},
            no_regex=frozenset({('Value','latex'),('Node','x_latex'),('Binding','symbol')}))
        self.rules=[]
        seen=set()
        for section in ('rules','guideline'):
            for raw in self.source.get(section,()):
                rid=raw['id']
                if rid in seen:raise DomainOperationRefused('duplicate released rule id')
                seen.add(rid)
                if 'finalize' not in raw.get('at',('batch','finalize')):continue
                self.rules.append((raw,self.language.compile(rid,raw.get('when','true')),
                                   self.language.compile(rid,raw['check'])))

    def compact(self,iri):
        choices=[(len(uri),prefix+':'+iri[len(uri):]) for prefix,uri in self.prefixes.items() if iri.startswith(uri)]
        return max(choices)[1] if choices else iri

    def is_a(self,child,parent):
        expanded=self.prepared.expand_name(child);target=self.prepared.expand_name(parent)
        definition=next((d for d in self.prepared.definitions if d.iri==expanded),None)
        ancestor=next((d.name for d in self.prepared.definitions if d.iri==target),None)
        return definition is not None and (expanded==target or ancestor in definition.ancestors)

    def applies(self,raw,candidate):
        source=raw.get('applies_to','any')
        if isinstance(source,str):source=[source]
        groups=self.metadata.get((candidate.class_name,candidate.predicate),{}).get('groups',())
        return any(value=='any' or (value.startswith('subset:') and value[7:] in groups)
                   or self.prepared.expand_name(value)==candidate.predicate for value in source)

    def evaluate(self,inputs:CutInput,scope:AnalysisScope,fused:pa.Table)->PolicyDecision:
        from corpus_structure.validate.views import EntityView,ValueView,StatementView,BindingView,NodeView,QualifiersView,_BARE,MAX_SYMBOL
        from corpus_structure.methods.math import grammar
        from corpus_structure.consolidate.finalize import GRAMMAR_KINDS
        from corpus_structure.validate.views import Reading
        errors=set();ambiguous=set();assessments=[];views={};readings={}
        candidates=inputs.candidates
        candidate_facts={c.fact_id for c in candidates}
        by_occurrence={c.occurrence_id:c.fact_id for c in candidates}
        def entity(key):
            meta=inputs.entity_metadata.get(key,{})
            identity={}
            for attribute in meta.get('attributes',()):
                value=attribute['value'];raw=value.get('text') if value.get('kind')=='text' else value.get('target')
                if isinstance(raw,str):identity[self.compact(attribute['predicate'])]=raw
            return EntityView(key,key,self.compact(meta.get('class_iri','')),meta.get('label') or '',
                              identity.get(next((k for k in identity if k.endswith(':symbol')),'')),identity)
        def nodes(value):
            if value is None:return []
            kind=value.get('kind')
            if kind in {'all','any'}:
                return [NodeView('and' if kind=='all' else 'or',None,None,None,None),
                        *(n for term in value.get('terms',()) for n in nodes(term))]
            if kind=='not':return nodes(value['term'])
            # Atomic relation nodes preserve the declared predicate and actual expression argument.
            if kind=='atomic':
                predicate=value['predicate'];op=predicate.rsplit(':',1)[-1].rsplit('/',1)[-1]
                if op not in {'member','compare','predicate'}:
                    raise DomainOperationRefused('condition operation has no declared legacy rule-view projection')
                args=value.get('arguments',())
                latex=args[0].get('expression') if args and isinstance(args[0],dict) else None
                return [NodeView(op,None,predicate,None,latex)]
            raise DomainOperationRefused('condition structure has no admitted rule projection')
        gives={}
        for candidate in candidates:
            props=self.metadata.get((candidate.class_name,candidate.predicate),{})
            param_map=props.get('cs:param_map')
            entries=candidate.qualification.get(param_map,()) if param_map else ()
            symbols=set()
            if candidate.statement_role in {'premise','example_value'}:
                for entry in entries.values() if isinstance(entries,dict) else entries:
                    value=entry.get('value',entry)
                    if value.get('kind')=='formula':
                        symbol=value['expression'].strip().lstrip('\\')
                        if len(symbol)<=MAX_SYMBOL and _BARE.fullmatch(symbol):symbols.add(symbol)
            gives[candidate.occurrence_id]=symbols
        # The rule operation evaluates source assertions. Its view item IDs are occurrence
        # references; canonical fact IDs remain separate in ClaimCandidate and assessments.
        from corpus_structure.pool.steps import VIEW_CLAIMS,VIEW_ENTITIES,VIEW_IDENTITY,VIEW_ALTERNATIVES,ViewSpec
        entities={key:entity(key) for key in inputs.entity_metadata}
        specs=[]
        for name,decl in self.source.get('views',{}).items():
            applies={c.predicate for c in candidates if self.applies({'applies_to':decl['applies_to']},c)}
            normalized={**decl,'source':self.prepared.expand_name(decl['source'])}
            specs.append(ViewSpec.from_declaration(name,normalized,applies))
        tables=(
            pa.Table.from_pylist([{'claim':c.occurrence_id,'predicate':c.predicate,'subject':c.subject,
                'object':c.object if isinstance(c.object,str) and c.object in entities else None,
                'statement':c.statement} for c in candidates],schema=VIEW_CLAIMS),
            pa.Table.from_pylist([{'entity':e.id,'key':e.key,'type':e.type,'label':e.label,'symbol':e.symbol}
                for e in entities.values()],schema=VIEW_ENTITIES),
            pa.Table.from_pylist([{'entity':e.id,'slot':slot,'value':value} for e in entities.values()
                for slot,value in e.identity.items()],schema=VIEW_IDENTITY),
            pa.Table.from_pylist([{'group':c.observation_key+'/'+group,'claim':c.occurrence_id}
                for c in candidates for group in c.alternatives],schema=VIEW_ALTERNATIVES),
        )
        facts={(row['claim'],row['view']):tuple(row['facts']) for row in scope.views(
            *(scope.connection.from_arrow(t) for t in tables),specs).to_arrow_table().to_pylist()}
        fused_ids=set(fused['fact_id'].to_pylist())
        if candidate_facts-fused_ids:raise DomainOperationRefused('fusion omitted a source-supported fact')
        for c in candidates:
            qvalues={name:None for name in self.qprops};qvalues.update(c.qualification)
            for name,value in tuple(qvalues.items()):
                if isinstance(value,(list,tuple)) and all(isinstance(v,dict) and {'key','value'}<=v.keys() for v in value):
                    qvalues[name]={v['key']:v['value'] for v in value}
            obj=None;value=None;bindings=[];unknown=None;reading_note=None
            if isinstance(c.object,str) and c.object in inputs.entity_metadata:obj=entity(c.object)
            else:
                raw=c.object
                kind=raw.get('kind') if isinstance(raw,dict) else 'text'
                latex=raw.get('expression') if isinstance(raw,dict) else None
                scalar=str(raw.get('text',raw.get('number',''))) if isinstance(raw,dict) else str(raw)
                reading=None
                if latex is not None:
                    key=(latex,kind,canonical_bytes(c.macros))
                    if key not in readings:
                        from corpus_structure.core.evidence import MacroDef
                        macros={name:MacroDef.model_validate(value) for name,value in c.macros.items()}
                        result=grammar.parse(latex,'set_expr' if kind=='set' else 'any_value',macros)
                        reading=Reading(result.status,GRAMMAR_KINDS.get(result.kind or ''),
                            tuple(sorted({o.name for o in result.occurrences if not o.constant})))
                        readings[key]=reading
                    reading=readings[key]
                    if reading.status.value!='ok':reading_note='mathematical reading '+reading.status.value
                    for binding in raw.get('bindings',()):
                        bindings.append(BindingView(binding['symbol'],binding['kind'],binding.get('entity'),binding.get('claim'),binding.get('parameter')))
                value=ValueView(kind,latex,scalar,None,kind,reading)
            # Multiple located reports of the same proposition are support, not competing
            # scientific claims. The kernels preserve occurrence addresses for source
            # policy, then these semantic set views collapse through canonical facts.
            same=tuple(sorted({by_occurrence[oid] for oid in facts.get((c.occurrence_id,'same_slot'),())
                               if by_occurrence[oid]!=c.fact_id}))
            alternatives=tuple(sorted({by_occurrence[oid] for oid in facts.get((c.occurrence_id,'alternative_of'),())
                                       if by_occurrence[oid]!=c.fact_id}))
            if alternatives:ambiguous.add(c.occurrence_id)
            try:condition_nodes=tuple(nodes(c.qualification.get('condition')))
            except DomainOperationRefused as exc:condition_nodes=();unknown=str(exc)
            statement=StatementView(c.statement,c.statement,c.statement_kind or '') if c.statement else None
            meta=self.metadata.get((c.class_name,c.predicate),{})
            view=SimpleNamespace(id=c.fact_id,key=c.fact_id,predicate=self.compact(c.predicate),
                groups=tuple(meta.get('groups',())),subject=entity(c.subject),object=obj,value=value,
                qualifiers=QualifiersView(qvalues),statement=statement,statement_kind=c.statement_kind,
                statement_role=c.statement_role,establishment=c.establishment,bindings=tuple(bindings),
                condition_nodes=condition_nodes,claim_refs=tuple(n.ref for n in condition_nodes if n.ref is not None),
                statement_premises=tuple(sorted({o.fact_id for o in candidates if o.fact_id!=c.fact_id and
                    o.statement_role=='premise' and (o.statement==c.statement or o.statement_kind=='assumption')})),
                gives_symbols=tuple(sorted(gives[c.occurrence_id])),
                given_by_others=tuple(sorted({symbol for o in candidates if o.occurrence_id!=c.occurrence_id for symbol in gives[o.occurrence_id]})),
                same_slot=same,alternative_of=alternatives,evidence_count=c.evidence_count,
                unresolved_symbols=sum(b.bind=='unresolved' for b in bindings))
            for name in self.source.get('views',{}):
                setattr(view,name,facts.get((c.occurrence_id,name),()))
            findings=[]
            if reading_note:findings.append(('operation.not_checkable','warning',reading_note))
            if unknown:
                # Unchecked projection/reading is not a passing rule result or scientific refutation.
                findings.append(('operation.not_checkable','warning',unknown))
            for raw,when,check in self.rules:
                if not self.applies(raw,c):continue
                if unknown and raw['id'].startswith('guideline.'):
                    continue
                if when.evaluate({'claim':view}) and not check.evaluate({'claim':view}):
                    findings.append((raw['id'],'warning' if raw in self.source.get('guideline',()) else raw.get('severity','error'),raw.get('description',raw['id'])))
            for rule,severity,message in findings:
                aid='assessment:'+sha256(canonical_bytes([VERSION,c.occurrence_id,rule,severity,message])).hexdigest()
                assessments.append(AssessmentRow(aid,rule,VERSION,'refuted' if severity=='error' else 'warning',
                    occurrence_id=c.occurrence_id,reason=message,uncertainty=unknown or reading_note))
                if severity=='error':errors.add(c.occurrence_id)
            status=('rejected' if c.occurrence_id in errors else 'candidate' if unknown else
                    'ambiguous' if c.occurrence_id in ambiguous else 'accepted')
            aid='assessment:'+sha256(canonical_bytes([VERSION,c.occurrence_id,status])).hexdigest()
            assessments.append(AssessmentRow(aid,'consolidate.status',VERSION,status,
                                            occurrence_id=c.occurrence_id,uncertainty=unknown))
            views[c.occurrence_id]=status
        # Structural source declarations are independent of the scientific claim decision table.
        selected={f.fact_id for f in inputs.batch.fact if f.fact_id not in candidate_facts}
        selected.update(c.fact_id for c in candidates if views[c.occurrence_id]=='accepted')
        return PolicyDecision(frozenset(selected),tuple(sorted(assessments,key=lambda a:a.assessment_id)))
