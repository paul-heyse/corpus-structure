"""Exact native bridge and output candidate location only; no semantic positives."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def read(p): return json.loads((ROOT/p).read_text())
def sha(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def write(p,d): (HERE/p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def packets(prefix):
    ps={str(p.relative_to(ROOT)):json.loads(p.read_text()) for p in (ROOT/prefix).glob('grinstead*.json')}
    return ps,{v['native_view']['id']:(p,i,v) for p,x in ps.items() for i,v in enumerate(x['views'])}
def identity(view):
    n=view['native_view'];return (n['native_task_id'],n['native_product_key'],n['native_content_digest'])
def leaf(view,piece):
    item=next(x for x in view['native_context']['items'] if x['self_ref']==piece['item_ref'])
    return item['data']['table_cells'][piece['cell_index']]['text'] if piece['source_field']=='cell_text' else item[piece['source_field']]
def decode(v):
    if not isinstance(v,dict): return v
    k=v.get('kind')
    if k=='object':
        names=[x['name'] for x in v['fields']]
        if len(names)!=len(set(names)): raise ValueError('duplicate object fields')
        return {x['name']:decode(x['value']) for x in v['fields']}
    if k in ['array','list','sequence']: return [decode(x) for x in v.get('items',[])]
    if k=='null': return None
    for key in ['text','integer','number','boolean','decimal']:
        if key in v:return v[key]
    return v
oldp,oldv=packets('source-packets');newp,newv=packets('source-recovery/attempt001/source-packets')
newfield={}
for vid,(path,i,v) in newv.items():
    for piece in v['native_context']['pieces']:
        if piece.get('item_ref'):
            key=identity(v)+(piece['item_ref'],piece['source_field'],piece.get('cell_index'))
            newfield.setdefault(key,[]).append((vid,path,i,v,piece))
common=read('authors/c/source-adjudication/adjudicated-source-cases.json')['cases']
extra=read('authors/c/source-recovery-assessment/source-cases.json')['cases']
transports=[]
for frame,cases in [('common32',common),('extra32',extra)]:
    for case in cases:
        mapped={}
        for name,a in case['anchors'].items():
            if frame=='extra32':
                path,i,v=newv[case['source_view_id']];s,e=a['start'],a['end'];assert v['passage']['text'][s:e]==a['text']
                pieces=[p for p in v['native_context']['pieces'] if p.get('item_ref') and p['start']<e and p['end']>s]
                segments=[]
                for p in pieces:
                    lo,hi=max(s,p['start'])-p['start'],min(e,p['end'])-p['start'];text=leaf(v,p)[lo:hi]
                    segments.append({'source_view_id':case['source_view_id'],'passage_id':v['passage']['passage_id'],'start':p['start']+lo,'end':p['start']+hi,'text':text,'native_pointer':p['item_ref'],'source_field':p['source_field'],'cell_index':p.get('cell_index'),'native_start':lo,'native_end':hi,'source_identity':list(identity(v)),'packet':path,'packet_sha256':sha(path)})
                mapped[name]={'state':'exact_current_native_bridge','segments':segments}
                continue
            oldvid=a.get('source_view_id',case['source_view_id']);op,oi,ov=oldv[oldvid];s,e=a['span'];quote=a['quote']
            if a.get('coordinate_space','passage_text')=='native_item_text':
                ref=a['native_pointer'];item=next(x for x in ov['native_context']['items'] if x['self_ref']==ref);assert item['text'][s:e]==quote
                oldsegments=[({'item_ref':ref,'source_field':'text'},s,e,quote)]
            else:
                assert ov['passage']['text'][s:e]==quote,(case['id'],name)
                oldsegments=[]
                for p in ov['native_context']['pieces']:
                    if p.get('item_ref') and p['start']<e and p['end']>s:
                        lo,hi=max(s,p['start'])-p['start'],min(e,p['end'])-p['start'];oldsegments.append((p,lo,hi,leaf(ov,p)[lo:hi]))
            segments=[];gaps=[]
            for p,lo,hi,text in oldsegments:
                key=identity(ov)+(p['item_ref'],p['source_field'],p.get('cell_index'));targets=newfield.get(key,[])
                if not targets:
                    gaps.append({'state':'native_only_not_projected','native_pointer':p['item_ref'],'native_start':lo,'native_end':hi,'text':text,'source_identity':list(identity(ov))});continue
                assert len(targets)==1,(case['id'],name,key,'ambiguous native field reuse')
                vid,np,ni,nv,nt=targets[0];assert leaf(nv,nt)==leaf(ov,p),(case['id'],name,'native leaf changed')
                assert leaf(nv,nt)[lo:hi]==text
                segments.append({'source_view_id':vid,'passage_id':nv['passage']['passage_id'],'start':nt['start']+lo,'end':nt['start']+hi,'text':text,'native_pointer':p['item_ref'],'source_field':p['source_field'],'cell_index':p.get('cell_index'),'native_start':lo,'native_end':hi,'source_identity':list(identity(nv)),'packet':np,'packet_sha256':sha(np)})
            mapped[name]={'state':'native_coordinate_gap' if gaps else 'exact_old_to_current_native_bridge','segments':segments,'gaps':gaps}
        transports.append({'frame':frame,'case_id':case['id'],'facet':case['facet'],'anchors':mapped,'meaning_transfer':'Not automatic: exact source bridge authenticates quoted source bytes only.'})
write('native-source-correspondence.json',{'protocol':'gs120-exact-source-anchor-transport-1','cases':transports})
scoped=[];files=[]
for p in sorted((ROOT/'current-structural-journey/sources002/scoped-feasibility').glob('source-*/export/items.jsonl')):
    path=str(p.relative_to(ROOT));files.append({'path':path,'sha256':sha(path)})
    for line_no,line in enumerate(p.read_text().splitlines(),1):
        obj=json.loads(line)
        if obj['population']=='interpretation':
            row=obj['row'];scoped.append({'file':path,'line':line_no,'contribution_id':row['contribution_id'],'source_view_id':row['source_view_id'],'semantic_type':row['semantic_type'],'kind':row['kind'],'value':decode(row['value']),'raw':row})
byid={x['contribution_id']:x for x in scoped}
named=read('current-contextual-journey/contextual001/named-file-page.json')['reports'][0]['definition_components']['components']
locations=[]
def overlaps(s,v,start,end):return s['source_view_id']==v and s['start']<end and s['end']>start
for transport in transports:
    segs=[(k,s) for k,a in transport['anchors'].items() for s in a['segments']]
    nr=[];participants=[];edges=[]
    for comp in named:
        hits={}
        for role in ['term','content']:
            point=comp[role];vid=int(point['passage_id'].rsplit('-',1)[1]);names=sorted({k for k,s in segs if overlaps(s,vid,point['start'],point['end'])})
            if names:hits[role]=names
        if hits:nr.append({'component_id':comp['component_id'],'interpretation':comp['interpretation'],'term':comp['term'],'content':comp['content'],'location_intersections':hits})
    for item in scoped:
        val=item['value']
        if not isinstance(val,dict) or 'start' not in val or 'end' not in val:continue
        hits=sorted({k for k,s in segs if overlaps(s,item['source_view_id'],val['start'],val['end'])})
        if hits:participants.append({k:item[k] for k in ['file','line','contribution_id','source_view_id','semantic_type','value']}|{'location_intersections':hits})
    participant_ids={x['contribution_id'] for x in participants}
    for item in scoped:
        v=item['value']
        if not isinstance(v,dict) or 'subject_id' not in v or 'target_id' not in v:continue
        if v['subject_id'] in participant_ids or v['target_id'] in participant_ids:
            edges.append({k:item[k] for k in ['file','line','contribution_id','source_view_id','semantic_type','value']}|{'subject':byid.get(v['subject_id'],{}).get('value'),'target':byid.get(v['target_id'],{}).get('value')})
    locations.append({'frame':transport['frame'],'case_id':transport['case_id'],'facet':transport['facet'],'named_location_candidates':nr,'scoped_participant_candidates':participants,'scoped_edge_candidates':edges,'semantic_capture':'unassessed_location_candidates_only'})
write('candidate-locations.json',{'protocol':'gs120-source-output-location-candidates-1','case_count':len(locations),'scoped_interpretations':len(scoped),'scoped_input_files':files,'cases':locations})
print(json.dumps({'cases':len(locations),'scoped_interpretations':len(scoped),'native_coordinate_gaps':[(c['case_id'],k) for c in transports for k,v in c['anchors'].items() if v['state']=='native_coordinate_gap']}))
