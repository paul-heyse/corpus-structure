"""Read-only actual GS120 operation-event fitting availability; no fit invocation.

Use exact completed-run receipts and the current contract. Do not retype semantic
products, invent references/frames, or import a held-out/independent-origin gate.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, UTC
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import traceback

from sqlalchemy import text
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
ROOT=BASE.parents[3]
PROJECT='wce-gs120-method-development-20261106'


def load(path):return json.loads(path.read_bytes())
def digest(path):return sha256(path.read_bytes()).hexdigest()
def relative(path):return str(path.relative_to(ROOT))


def main():
    paths=[BASE/'current-contextual-journey/contextual001/summary.json',BASE/'current-structural-journey/sources002/result.json',BASE/'current-structural-journey/comparison001/native/completed.json',BASE/'assessment/run160-final-named001/manifest.json',BASE/'assessment/run161-final-model001/manifest.json']
    contextual,sources,comparison,named,model=map(load,paths)
    selected=[dict(capability='named_components',run_id=named['run']['id'],cut_id=named['completed_result']['cut_id']),dict(capability='model_source_and_components',run_id=model['run']['id'],cut_id=model['completed_result']['cut_id']),dict(capability='comparison',run_id=comparison['run_id'],cut_id=comparison['cut_id']),dict(capability='artifact_identity',run_id=sources['artifact']['run_id'],cut_id=sources['artifact']['cut_id'])]
    selected += [dict(capability='contextual',source_view_id=r['source_view_id'],run_id=r['run_id'],cut_id=r['cut_id']) for r in contextual['runs']]
    selected += [dict(capability='scoped_'+a['mode'],run_id=a['run']['run_id'],cut_id=a['run']['cut_id']) for a in sources['arms']]
    selected.sort(key=lambda x:x['run_id']);run_ids=[r['run_id'] for r in selected]
    assert run_ids==[160,161,162,163,164,165,166,167,168,170,171,172,177,178,179,180,183]
    parameters=dict(project=PROJECT,run_ids=run_ids)
    with open_runtime_engine(Settings(),'wce-fit-availability-current',purpose='read') as engine,read_snapshot(engine) as conn:
        principal=dict(conn.execute(text('SELECT current_user,session_user')).mappings().one())
        rows=[dict(r) for r in conn.execute(text((HERE/'contribution-census.sql').read_text()),parameters).mappings()]
        runs=[dict(r) for r in conn.execute(text('SELECT r.id run_id,r.project_id,r.status,r.sealed,r.release_id,r.runtime_id,c.cut_id FROM ops.run r JOIN ops.completed_result c ON c.run_id=r.id WHERE r.project_id=:project AND r.id=ANY(:run_ids) ORDER BY r.id'),parameters).mappings()]
    assert len(runs)==len(selected) and all(r['sealed'] and r['status']=='finished' for r in runs)
    assert [(r['run_id'],r['cut_id']) for r in runs]==[(r['run_id'],r['cut_id']) for r in selected]
    with open_runtime_engine(Settings(),'wce-fit-availability-protected-metadata',purpose='evaluate') as engine,read_snapshot(engine) as conn:
        evaluator_principal=dict(conn.execute(text('SELECT current_user,session_user')).mappings().one())
        grades=[dict(r) for r in conn.execute(text((HERE/'protected-grade-census.sql').read_text()),parameters).mappings()]
    compatible=[r for r in rows if r['kind']=='relation' and r['semantic_type']=='relation.defined_by']
    grade_candidates=[g for g in grades if g['protocol']=='source-operation-evaluation-1' and g['partition'] in ('development','feature_fit') and g['event_case_count']>0]
    by_family=[]
    for capability in sorted({s['capability'] for s in selected}):
        members={s['run_id'] for s in selected if s['capability']==capability};counter=Counter()
        for row in rows:
            if row['run_id'] in members:counter[(row['kind'],row['semantic_type'])]+=row['contribution_count']
        by_family.append(dict(capability=capability,run_ids=sorted(members),contributions=sum(counter.values()),event_compatible_contributions=sum(n for (kind,semantic),n in counter.items() if kind=='relation' and semantic=='relation.defined_by'),populations=[dict(kind=k[0],semantic_type=k[1],count=n) for k,n in sorted(counter.items())]))
    fit_source=ROOT/'python/corpus-structure/src/corpus_structure/evaluate/operation_fitting.py';native_source=ROOT/'python/corpus-structure/src/corpus_structure/semantic/sql/operation_event_fitting.sql'
    inputs=[*paths,fit_source,native_source,HERE/'contribution-census.sql',HERE/'protected-grade-census.sql',Path(__file__).resolve()]
    result=dict(protocol='wce-current-corpus-operation-fit-availability-1',checked_at=datetime.now(UTC).isoformat(),census_outcome='passed',availability='compatible_emissions_require_root_review' if compatible else 'unavailable',fit_outcome='not_run',project_id=PROJECT,code_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),command='uv run python '+relative(Path(__file__)),selected_run_receipts=selected,actual_completed_runs=runs,contribution_census=dict(principal=principal,categories=len(rows),selected_cut_rows=sum(r['contribution_count'] for r in rows),populations=rows,compatible_events=compatible,compatible_event_count=sum(r['contribution_count'] for r in compatible),count_grain='Rows selected by each exact completed cut; repeated structural arms are separate declared outputs, not independent source origins.'),protected_grade_metadata=dict(purpose='evaluate',principal=evaluator_principal,evaluations=grades,compatible_metadata_candidates=grade_candidates,authored_reference_alternatives_read=False,exposure_or_reference_rows_written=False),by_capability=by_family,current_contract=dict(event='defined_by_correctness',event_version='defined-by-exact-endpoints-scope-1',contribution_kind='relation',semantic_type='relation.defined_by',grade_protocol='source-operation-evaluation-1',grade_partition=['development','feature_fit'],frame_direction='output_first',case_identity=['contribution_id','facet=defined_by_correctness'],positive_scope='Current independently authored C case must bind actual head and tail endpoint semantics with nonempty exact anchor scopes.',native_custody='Exact original task, source-view, completed final cut, grade digest and C snapshot; one emitted event cannot be weighted twice.',feature_names=['native_score','native_score_present','head_exact_endpoint_count','tail_exact_endpoint_count'],binary_fit_requirement='At least one supported and one unsupported independently judged event; ambiguous/unassessed are not negatives.',assessment_mode='in_sample_development',independent_origin_requirement='none',held_out_requirement='none'),missing_prerequisites=[] if compatible else ['No contribution in the selected completed cuts has the exact current event kind=relation and semantic_type=relation.defined_by.','No protected reference_evaluation row exists for these selected runs; a fit additionally requires an output-first exact-contribution-ID defined_by_correctness C evaluation with both binary classes under the current source-operation contract.'],not_run_reasons=['No native frame/read/fit call: no eligible current emission/grade selection to supply; no IDs invented.', 'No fitting, scoring, new reference authoring, protected pass/exposure write, DB mutation, provider execution, product/plan edit or commit.', 'The controlled two-positive/two-negative mechanism fit remains separate evidence and is not a current-corpus cohort.'],identity_limits=['proposal/contextual.relationship is not relation/relation.defined_by.', 'Model definition.defining_text_attachment and definition.alias_attachment are distinct current source relations, not interchangeable event tags.', 'Structural component public_statement assessments use a separate group-frame/component contract and cannot substitute for contribution_id/defined_by_correctness operation grades.', 'No inference of absence outside the17 explicitly selected completed runs; no semantic quality, scientific truth, public authority or general fit-readiness claim.'],input_pins=[dict(path=relative(p),sha256=digest(p)) for p in inputs])
    (HERE/'availability001.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(census_outcome=result['census_outcome'],availability=result['availability'],fit_outcome=result['fit_outcome'],runs=len(runs),selected_cut_contributions=result['contribution_census']['selected_cut_rows'],compatible_events=result['contribution_census']['compatible_event_count'],protected_evaluations=len(grades))))


if __name__=='__main__':
    try:main()
    except BaseException as error:
        (HERE/'census-failure001.json').write_text(json.dumps(dict(outcome='failed',type=type(error).__name__,message=str(error)),indent=2)+'\n')
        (HERE/'census-failure001.txt').write_text(traceback.format_exc());raise
