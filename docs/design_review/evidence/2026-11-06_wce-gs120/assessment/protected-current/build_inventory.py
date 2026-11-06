"""Authenticate author source inventories without promoting them to machine gold."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
GS=HERE.parents[1]
ROOT=GS.parent

def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    files=[GS/'authors/current-named-review/a/assessment.json',GS/'authors/current-named-review/b/assessment.json',GS/'authors/current-named-review/c/assessment.json',GS/'authors/common-review/a/review.json',GS/'authors/common-review/b/review.json',GS/'authors/c/source-adjudication/adjudicated-source-cases.json',GS/'authors/c/source-recovery-assessment/source-cases.json']
    old={v['passage']['passage_id']:(p,v) for p in (GS/'source-packets').glob('grinstead-snell-physical*.json') for v in load(p)['views']}
    current={v['passage']['passage_id']:(p,v) for p in (GS/'source-recovery/attempt001/source-packets').glob('grinstead-snell-physical*.json') for v in load(p)['views']}
    viewmap={}
    for pid,(p,v) in old.items():
        matches=[(np,nf,nv) for np,(nf,nv) in current.items() if v['native_view']['source_uri']==nv['native_view']['source_uri'] and v['source']['native_content_digest']==nv['source']['native_content_digest'] and v['native_context']==nv['native_context'] and v['passage']['text']==nv['passage']['text']]
        if len(matches)!=1:raise ValueError('no exact old/current native source match: '+pid)
        viewmap[pid]=matches[0]
    common=load(files[5]);extra=load(files[6]);cases=[];native_only=[]
    for family,data in [('source_common32',common),('source_recovered_C32',extra)]:
        for c in data['cases']:
            anchors=[]
            for aid,a in c['anchors'].items():
                if family=='source_common32':
                    pid=a.get('passage_id',c['passage_id']);np,nf,nv=viewmap[pid];start,end=a['span'];quote=a['quote'];coordinate=a.get('coordinate_space','passage_text')
                else:
                    np=a['passage_id'];nf,nv=current[np];start,end=a['start'],a['end'];quote=a['text'];coordinate=a.get('coordinate_space','passage_text')
                pointer=a.get('native_pointer');projection_span=None
                if coordinate=='native_item_text':
                    node=next(it for it in nv['native_context']['items'] if it.get('self_ref')==pointer)
                    if node['text'][start:end]!=quote:raise ValueError('native item quote mismatch')
                    pieces=[pc for pc in nv['native_context']['pieces'] if pc.get('item_ref')==pointer and pc.get('source_field')=='text']
                    if len(pieces)==1:projection_span=[pieces[0]['start']+start,pieces[0]['start']+end]
                    else:native_only.append({'case_id':c['id'],'anchor':aid,'pointer':pointer,'reason':'native text exists but is absent from this source projection; do not reinterpret native offsets as passage offsets or fabricate an exact projection bridge'})
                elif coordinate in {'passage_text','selected_projection'}:
                    if nv['passage']['text'][start:end]!=quote:raise ValueError('projected source quote mismatch')
                    projection_span=[start,end]
                else:raise ValueError('unhandled explicit coordinate space: '+coordinate)
                anchors.append({'author_anchor':aid,'quote':quote,'coordinate_space':coordinate,'author_span':[start,end],'current_passage_id':np,'current_source_view_id':nv['source']['source_view_id'],'current_pin':nv['source'],'current_projection_span':projection_span,'packet':str(nf.relative_to(ROOT)),'native_pointer':pointer,'cell_index':a.get('cell_index'),'state':'source/coordinate correspondence authenticated only; no semantic machine alternative inferred'})
            cases.append({'family':family,'case_id':c['id'],'source_authors':'Independent A/B common-question reviews plus C dispositions; facet-level authorship must remain distinct' if family=='source_common32' else 'C only; independent recovered-region population, no A/B votes','roles':c.get('roles',[]),'relations':c.get('relations',[]),'anchors':anchors,'typed_native_alternatives':'not_authored_for_actual_operation_ABI','limits':'No prose-to-gold synthesis, source-semantic-type relabeling, copying actual output as expected, or synthetic votes.'})
    a,b,c=(load(f) for f in files[:3]);ids=[e['component_id'] for e in a['components']]
    if ids!=[e['component_id'] for e in b['entries']] or ids!=[e['component_id'] for e in c['entries']]:raise ValueError('current A/B/C output membership differs')
    current_cases=[]
    for aa,bb,cc in zip(a['components'],b['entries'],c['entries'],strict=True):
        current_cases.append({'component_id':aa['component_id'],'A_origin':f"/components/{aa['ordinal']-1}/independently_authored_expectation",'A_state':'prose assessment; root requested bounded independent typed literal authoring separately','B_origin':bb['assessment_case_id'],'B_state':'six facets preserved; bounded four literals plus whole-completeness unassessed prepared here, remaining diagnostics not automatically machine gold','C_origin':f"/entries/{cc['ordinal']-1}/narrow_public_attachment",'C_state':'C-selected exact narrow extents; future C typed alternatives adjudicate actual independent A/B literals, not 35 invented agreements','current_pin':bb['current_source_pin']})
    result={'protocol':'wce-protected-current-representability-1','status':'prepared_waiting_root_GO','database_writes':'not_run','inputs':[{'path':str(f.relative_to(ROOT)),'sha256':sha(f)} for f in files],'current35':current_cases,'source_cases':cases,'native_only_anchors_without_projection_bridge':native_only,'counts':{'current_output_questions':len(current_cases),'source_common_cases':len(common['cases']),'C_only_recovered_cases':len(extra['cases']),'source_anchor_correspondences':sum(len(x['anchors']) for x in cases),'native_only_anchors':len(native_only)},'required_final_pins':['project/release, candidate run/completed cut, selected/origin tasks and exact structural product ID/body','authenticated prior35-to-final component/source/payload correspondence preserving removals and semantic changes','complete ExternalSourceRef pins and physical source correspondence without recipe/run/view aliases','grinstead-snell origin assignment and development/feature_fit partition','actual distinct author identities, exact authored bytes/hashes and exact native C A/B parent IDs','actual native source-unit keys/source_binding pins for operation frames','literal contribution population and complete endpoint closure for operation relationships','independently authored exact alternatives and semantic ABI mapping; unsupported/unresolved/unassessed facets remain explicit'],'representation_limits':['Current35 uses structural product/frame API; structural component IDs are not OperationCase contribution IDs.','Source-common32 and extraC32 rich semantic roles/relations need actual OperationCase literal alternatives in the chosen contribution ABI. Their prose/anchor inventories alone are not native exact gold.','C-only recovered cases can remain a single independent authored pass with C origin explicitly preserved; cannot become three votes or C adjudication without independent parents.','Native-only captions require an honest native item/coordinate treatment; no projection span is fabricated.','Structural public statements require exact component selection; whole-report refusal is literal owner behavior, while whole-report completeness stays unassessed.','No relabeling contextual.relationship as relation.defined_by; defined_by event fitting remains unavailable absent genuine native event population and grade.']}
    (HERE/'representability-inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'outcome':'passed','database_writes':'not_run',**result['counts'],'native_only_anchors':native_only},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
