"""Package manual C cases with original parents and metadata; no projection or DB."""
import copy
import hashlib
import json
from pathlib import Path
import re
import runpy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PARENT = 'assessment/protected-current/'

def read(path): return json.loads((ROOT/path).read_text())
def digest(path): return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def canonical(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def write(name,value): (HERE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n')

parents = {
    'A': {'authored': PARENT+'author-a/A.authored.json','frame':PARENT+'author-a/frame.json','provenance':PARENT+'author-a/source-provenance.json'},
    'B': {'authored': PARENT+'prepared-b-run152/B.authored.json','frame':PARENT+'prepared-b-run152/frame.json','provenance':PARENT+'prepared-b-run152/B.authoring-provenance.json'},
}
for author, files in parents.items():
    for kind,path in list(files.items()):
        dest=HERE/f'{author}.{kind}.original.json'
        dest.write_bytes((ROOT/path).read_bytes())
        files[kind+'_sha256']=digest(path)
a=read(parents['A']['authored']);b=read(parents['B']['authored']);af=read(parents['A']['frame']);bf=read(parents['B']['frame'])
assert af['inputs']==bf['inputs'] and af['product_ids']==bf['product_ids']
assert hashlib.sha256(canonical(af)).hexdigest()==a['frame_digest']
assert hashlib.sha256(canonical(bf)).hexdigest()==b['frame_digest']
specs=runpy.run_path(str(HERE/'author_literals.py'))['CASES']
all_passages=[p['passage_id'] for p in bf['inputs']['passages']]
assert len(all_passages)==48
packets={str(p.relative_to(ROOT)):json.loads(p.read_text()) for p in (ROOT/'source-recovery/attempt001/source-packets').glob('grinstead*.json')}
views={v['native_view']['id']:(path,i,v) for path,p in packets.items() for i,v in enumerate(p['views'])}
anchors={}

def select(key,vid,number,literal):
    path,index,view=views[vid];packet=packets[path]
    piece=next(p for p in view['native_context']['pieces'] if p.get('item_ref')==f'#/texts/{number}')
    ni=next(i for i,p in enumerate(view['native_context']['items']) if p['self_ref']==piece['item_ref'])
    item=view['native_context']['items'][ni];text=item[piece['source_field']]
    literal=text if literal is None else literal
    found=re.search(r'(?<!\w)'+re.escape(literal)+r'(?!\w)',text)
    assert found is not None,(vid,number,literal)
    start=piece['start']+found.start();end=start+len(literal)
    assert view['passage']['text'][start:end]==literal
    mp={p['excerpt_physical_page']:p['parent_physical_page'] for p in packet['page_map']}
    anchors[key]={'packet':path,'packet_sha256':digest(path),'view_index':index,'passage_id':view['passage']['passage_id'],'source_view_id':vid,'start':start,'end':end,'text':literal,'piece':piece,'native_item_pointer':f'/views/{index}/native_context/items/{ni}','native_pointer':item['self_ref'],'native_text_start':found.start(),'native_text_end':found.start()+len(literal),'native_original_text':item.get('orig'),'native_provenance':item.get('prov',[]),'parent_physical_pages':sorted({mp[p['page_no']] for p in item.get('prov',[])})}
    pin={k:view['source'][k] for k in ['project_id','native_product_key','native_content_digest','recipe_digest','projection_digest','coordinate_version']}
    return {'source':pin,'start':start,'end':end,'text':literal,'scope':view['passage']['scope']}

cases=[];decisions=[];correspondence={}
for spec in specs:
    cid=spec['case_id'];vid=spec['source_view_id'];path,index,view=views[vid]
    term=select(cid+'-term',vid,spec['term_item'],spec['term_text'])
    content=select(cid+'-content',vid,spec['content_item'],spec['content_text'])
    scope=view['passage']['scope']
    expected={'version':'structural-public-statement-3','kind':'definition_components','scope':scope,'definition_component':{'scope':scope,'interpretation':spec['interpretation'],'term':term,'content':content},'exclusions':[],'coverage_limits':[]}
    case={'case_id':cid,'component_id':spec['component_id'],'facet':'public_statement','path':['public_statement'],'expected':expected,'source_passages':all_passages,'judgment':spec['judgment'],'explanation':spec['explanation']}
    cases.append(case);correspondence[cid]={'A':spec['A_case_id'],'B':spec['B_case_id']}
    ac=next(x for x in a['cases'] if x['case_id']==spec['A_case_id']);bc=next(x for x in b['cases'] if x['case_id']==spec['B_case_id'])
    context=[]
    for number in spec['context_items']:
        key=cid+f'-context-{number}';select(key,vid,number,None);context.append(key)
    decisions.append({'case_id':cid,'component_id':spec['component_id'],'parent_case_ids':correspondence[cid],'A_exact_object':ac,'B_exact_object':bc,'C_exact_object':case,'A_B_expected_exact_agreement':ac['expected']==bc['expected'],'C_A_expected_exact_agreement':expected==ac['expected'],'C_B_expected_exact_agreement':expected==bc['expected'],'judgment_agreement':case['judgment']==ac['judgment']==bc['judgment'],'source_evidence':context,'source_execution_pin':view['source'],'native_view':view['native_view'],'qualifier_limits':spec['qualifier_limits'],'administrative_closure':'C cites all48 selected frame passages for typed publication witness closure; only this local case was semantically adjudicated.','selection_reason':spec['explanation']})
whole={'case_id':'C-WHOLE-REPORT-COMPLETENESS-UNASSESSED','component_id':None,'facet':'completeness','path':['definition_components','components'],'expected':None,'source_passages':all_passages,'judgment':'unassessed','explanation':'Four bounded component judgments do not supply an exact expected value or semantic approval for the entire report. No exhaustive recall annotation or scientific-truth assessment is provided.'}
cases.append(whole);correspondence[whole['case_id']]={'A':'A-whole-report-completeness-unassessed','B':'B-WHOLE-REPORT-COMPLETENESS-UNASSESSED'}
# This is a current-run proposal only. Root authenticates final run and rebinds frames later.
frame=copy.deepcopy(bf)
frame['rubric_version']='independent-definition-component-1'
frame['rubric_text']='Independent narrow source-attributed public-statement cases. A/B original expected literals and disagreements remain preserved; C adjudicates the same bounded questions. Local attachment is separate from whole-report completeness, conditions, recognition, scientific truth and publication permission.'
frame['inspected_scope']='Four run152/cut204/task605 component questions: marginals, normal density, probability subject and historical contrast. Whole-report completeness unassessed. Common-frame proposal awaiting root final source/product authentication.'
frame['exposure_history']=list(dict.fromkeys(af['exposure_history']+bf['exposure_history']+['C previously read baseline9/current35 outputs, A/B current reviews, and source common/recovered accounts; current C adjudication reread original neutral context after seeing frozen A/B alternatives. Exposed development, not held out.']))
frame['opportunities']=[{'opportunity_id':c['case_id'],'passage_id':('gs120-recovered-source-'+str(s['source_view_id'])),'facet':'public_statement','source_state':'stated'} for c,s in zip(cases,specs)]
frame['opportunities'].append({'opportunity_id':whole['case_id'],'passage_id':'gs120-recovered-source-111','facet':'completeness','source_state':'uninspected'})
frame_digest=hashlib.sha256(canonical(frame)).hexdigest()
authored={'protocol':'structural-reference-3','frame_digest':frame_digest,'cases':cases}
write('frame.proposed-run152.json',frame);write('C.authored.json',authored);write('adjudication-decisions.json',{'protocol':'gs120-protected-C-adjudication-decisions-1','date':'2026-11-06','parents':parents,'cases':decisions,'completeness':whole,'frame_state':'proposed_run152_common_frame_pending_root_authentication'})
write('adjudication-case-correspondence.json',correspondence)
refusal=read(PARENT+'prepared-b-run152/whole-report-refusal.json')
write('mechanism-refusal.json',{'observed_B_refusal':refusal,'source_artifact':PARENT+'prepared-b-run152/whole-report-refusal.json','source_sha256':digest(PARENT+'prepared-b-run152/whole-report-refusal.json'),'C_reexecution':'not_run','separation':'No-component projection refusal is a mechanism observation, not a completeness gold verdict or public_statement expected value.'})
inputs=[p[k] for p in parents.values() for k in ['authored','frame','provenance']]+[PARENT+'prepared-b-run152/whole-report-refusal.json','current-extraction/named001/structural-inspection.json']+sorted({x['packet'] for x in anchors.values()})
provenance={'protocol':'gs120-protected-C-authoring-provenance-1','actor':'adjudicator-C:/root/baseline_output_adjudication_c','pass_kind':'C','date':'2026-11-06','authoring_kind':'adjudication','source_reading':'C reread original neutral converted/native.orig context for allfour questions. No projection was called to derive expected values. Manual literals in author_literals.py were packaged using only physical pin metadata.','exposure':'Prior baseline/current output and source review exposure plus frozen A/B alternatives; no blinded, held-out or independent-source corroboration claim.','frame_digest':frame_digest,'frame_state':'run152_common_frame_proposal_not_final_transport','parents':parents,'parent_case_correspondence':correspondence,'native_parent_binding':{'state':'pending_actual_native_A_B_pass_ids','required_before_C_attachment':True,'C_authored_sha256':hashlib.sha256((HERE/'C.authored.json').read_bytes()).hexdigest(),'instruction':'When real A/B IDs are supplied, freeze a C-owned binding sidecar/envelope recording those exact IDs and the authenticated C/frame/parent hashes before attachment. No fabricated IDs or silent modification of authored case bytes.'},'anchors':anchors,'frozen_inputs':[{'path':p,'sha256':digest(p)} for p in inputs],'case_origins':{c['case_id']:{'source_artifact':'author_literals.py' if c['component_id'] else 'adjudication-decisions.json','source_sha256':hashlib.sha256((HERE/('author_literals.py' if c['component_id'] else 'adjudication-decisions.json')).read_bytes()).hexdigest(),'source_pointer':'/CASES/'+str(i) if c['component_id'] else '/completeness','mapping_decision':'Explicit same component/facet/path mapping to the frozen original A/B case IDs; source semantics selected by C, not a vote or copied actual product.','copied_actual_as_expected':False} for i,c in enumerate(cases)}}
write('source-provenance.json',provenance)
write('transport-conditions.json',{'state':'pending_root_final_pins_common_frame_and_native_parent_ids','current_candidate':{'run_id':152,'cut_id':204,'task_id':605,'product_ids':bf['product_ids']},'original_parent_frames':{'A':a['frame_digest'],'B':b['frame_digest']},'C_proposed_frame':frame_digest,'requirements':['Root authenticates final named002 source/component correspondence before transporting current literals.','A/B wrappers may rebind frame_digest only, preserving every original case literal, judgment, explanation and source_passages list; original files remain pinned.','Preserve the historical A/B/C expected-content/interpretation disagreement.','C cites all48 passages for administrative closure, not all48 semantic approval.','Real native A/B pass IDs and exact frame/authored hashes must be recorded in C binding bytes before C attachment; SQL uses external parent IDs, so do not add unknown keys to StructuralAuthoredReference.','Whole-report completeness remains unassessed; no-component projection refusal is a separate mechanism record.'],'database_writes':'not_run','publication':'not_requested'})
print(json.dumps({'outcome':'authored','frame_digest':frame_digest,'literal_cases':4,'completeness':'unassessed','native_parents':'pending'}))
