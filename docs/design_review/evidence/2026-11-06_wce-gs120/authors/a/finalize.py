import hashlib,json
from pathlib import Path
from author import ROOT,SRC
relations={
'A-191-004':('finite uniform outcome','has_probability','1/n'),
'A-191-010':('projected binomial formula','has_state','recognition damaged'),
'A-191-014':('normal approximation','uses_parameters','mean np and standard deviation sqrt(npq)'),
'A-191-015':('out-of-range normal sample','triggers','rejection and resampling'),
'A-191-019':('geometric waiting count','has_support','positive integers'),
'A-191-020':('decreased success probability','increases','likelihood of large waiting count'),
'A-191-024':('ceiling operation','returns','least integer at least its argument'),
'A-191-029':('geometric service duration','has_property','memorylessness'),
'A-191-032':('negative binomial with k=1','specializes_to','geometric distribution'),
'A-191-035':('Poisson occurrence rate lambda','has_unit','occurrences per minute'),
'A-191-047':('expected frequency of squares with j hits','equals','100 times per-square j-hit probability'),
'A-201-006':('hypergeometric law with fixed target fraction','converges_to','binomial law as population grows'),
'A-201-013':('row and column sums','named','marginal totals'),
'A-201-017':('first cell with fixed margins','determines','other three 2x2 cells'),
'A-201-021':('hypergeometric sample loop','terminates_when','n balls have been selected'),
'A-201-024':('Benford treatment','restricted_to','first significant digit'),
'A-201-027':('Benford predicted series','uses_marker','squares'),
'A-201-030':('maximum likelihood estimate','maximizes','observed sample probability'),
'A-201-031':('Poisson count over duration t','has_parameter','lambda times t'),
'A-211-006':('inter-emission durations','assumed','independent exponential with common rate'),
'A-211-008':('exponential rate','equals','reciprocal mean duration'),
'A-211-011':('sum of common-rate exponential durations','has_density_family','gamma'),
'A-211-017':('customer finding no predecessor','enters_state','immediate service'),
'A-211-021':('arrival rate greater than service rate','causes_in_model','queue growth'),
'A-211-022':('system residence time','includes','waiting plus service'),
'A-211-026':('density transformation corollary','derived_by','chain rule from CDF theorem'),
'A-211-031':('inverse-CDF sample','has_same_CDF_as','target variable'),
'A-221-002':('three-dimensional normal-component speed','has_density_family','Maxwell'),
'A-221-003':('two-dimensional standard-normal radius','has_density_family','Rayleigh'),
'A-221-016':('chi-squared reference density','approximates','null sampling density of discrepancy statistic'),
'A-221-018':('chi-squared density parameter','named','degrees of freedom'),
'A-221-019':('a-by-b independence table','has_degrees_of_freedom','(a-1)(b-1)'),
'A-221-021':('statistic at or above critical value','triggers','independence-hypothesis rejection'),
'A-221-030':('zero affine scaling','excluded_from','density transformation exercise'),
'A-231-009':('discrete expectation','requires','absolute convergence'),
'A-231-010':('expected value','also_named','mean'),
'A-231-015':('St Petersburg payment of 2^n','has_probability','2^(-n)'),
'A-231-017':('divergent-payment example','named','St Petersburg paradox'),
'A-231-019':('utility function','maps','monetary payment to assigned value'),
'A-231-028':('number of runs in three tosses','has_distribution','m(1)=1/4,m(2)=1/2,m(3)=1/4'),
'A-231-035':('linearity of expectation','does_not_require','mutual independence'),
'A-231-037':('uniform random permutation','has_expected_fixed_points','one'),
'A-241-001':('Bernoulli success count','has_expectation','n times p'),
'A-241-006':('independence','sufficient_for','product-expectation factorization'),
'A-241-009':('jth record indicator','has_expectation','1/j under symmetry premise'),
'A-241-014':('craps nonterminal initial roll','establishes','point r'),
'A-241-023':('prison state P1 on zero','transitions_to','double prison P2'),
'A-241-024':('double prison P2 on red','transitions_to','prison P1'),
'A-241-030':('total-expectation partition','requires','disjoint exhaustive events'),
'A-241-034':('conditionally fair fortune process','named','martingale'),
'A-251-002':('gross roulette return36','corresponds_to','net profit35'),
'A-251-010':('six consecutive doubling losses','prevents','required64-dollar next bet with100-dollar bankroll'),
'A-251-029':('ESP recurrence','has_boundary_values','h(0,0)=h(-1,0)=h(0,-1)=0'),
'A-251-030':('feedback guessing strategy','selects','remaining majority with randomized ties'),
'A-261-002':('variance','equals','expected squared centered variable'),
'A-261-003':('standard deviation','equals','square root of variance'),
'A-261-011':('scaling variable by c','scales_variance_by','c squared'),
'A-261-012':('constant translation','preserves','variance'),
'A-261-017':('independence','implies','mixed expectation equals product of means'),
'A-261-024':('large independent sample average','usually_near','common mean under finite variance'),
'A-261-033':('decreasing geometric success probability','increases','variance'),
'A-271-013':('denominator n-1 sample variance','has_expectation','population variance'),
'A-271-018':('covariance','equals','expected product of centered variables'),
'A-271-019':('self-covariance','equals','variance'),
'A-271-020':('zero covariance','does_not_imply','independence'),
'A-271-026':('time until nth success','decomposes_into','sum of inter-success gaps'),
'A-271-039':('product expectation theorem','requires','independence and finite expected values'),
'A-281-008':('traffic intensity','equals','mean service time divided by mean interarrival time'),
'A-281-016':('equilibrium queue count','has_support','nonnegative integers'),
'A-281-018':('stable queue mean time','equals','1/(service rate-arrival rate)'),
'A-281-037':('variance of dependent sum','includes','twice covariance'),
'A-281-042':('conditional density','equals','joint density divided by conditioning marginal'),
'A-291-008':('convolution','has_property','commutativity'),
'A-291-009':('convolution','has_property','associativity'),
'A-291-018':('independent thirteen-card model','approximates','actual bridge sampling without replacement'),
'A-291-022':('same-p binomial convolution','adds','trial-count parameters'),
'A-291-033':('independent continuous sum','has_density','convolution of component densities'),
'A-301-002':('independent normal sum','has_parameters','sum of means and sum of variances'),
'A-301-009':('average of two independent unit Cauchy variables','has_density','unit Cauchy'),
'A-301-019':('chi-squared construction','sums','squares of independent standard normals'),
'A-301-020':('n squared independent standard normals','has_gamma_parameters','rate1/2 and shape n/2'),
'A-301-027':('goodness-of-fit reference','has_degrees_of_freedom','number of categories minus one'),
'A-301-031':('observed fair-die discrepancy statistic','has_value','13.6 for supplied table'),
'A-301-045':('sum density','obtained_by','differentiating sum CDF')
}
ledger=[];total=0;checks=[]
for first in range(191,311,10):
 inp=SRC/f'grinstead-snell-physical{first}-{first+9}.json';raw=inp.read_bytes();d=json.loads(raw)
 out=ROOT/f'physical{first}-{first+9}.json';a=json.loads(out.read_text()); assert a['input_sha256']==hashlib.sha256(raw).hexdigest()
 views={v['source']['source_view_id']:v for v in d['views']};present=set()
 for c in a['cases']:
  assert c['id'].startswith(f'A-{first}-')
  if c['id'] in relations:
   s,p,o=relations[c['id']];c['proposed_relation']={'subject':s,'predicate':p,'object':o}
  for e in c['evidence_spans']:
   v=views[e['source_view_id']];assert c['source_ref']==v['passage']['source_ref'];assert v['passage']['text'][e['start']:e['end']]==e['text'];assert e['coordinate_space']=='projection'
 for cv in a['coverage']:present.update(cv['parent_physical_pages'])
 absent=sorted(set(a['parent_physical_pages'])-present)
 a['page_coverage']=[{'parent_physical_page':p,'state':'projection_inspected' if p in present else 'uninspected','case_count':sum(p in c['parent_physical_pages'] for c in a['cases']),'limitation':'Figures and PDF image regions not visually inspected.' if p in present else 'No native-provenance item for this parent page appears in permitted projected views; PDF not inspected.'} for p in a['parent_physical_pages']]
 if absent:a['remaining_gaps'].append({'uninspected_parent_physical_pages':absent,'reason':'No supplied projection view/native-provenance item for these pages; no PDF image inspection performed.'})
 out.write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n');ledger.extend(a['page_coverage']);total+=len(a['cases']);checks.append({'packet':out.name,'cases':len(a['cases']),'span_validation':'passed','input_sha256_validation':'passed','uninspected_pages':absent})
assert len(ledger)==120;assert {x['parent_physical_page'] for x in ledger}==set(range(191,311))
summary={'protocol':'gs120-source-author-1','author':'A','scope':'Shared development source physical191–310; source-only independent semantic inventory; no producer outputs read.','inspection_basis':'All supplied passage.text projections read in full. Physical page coverage inferred only from native item provenance. No actual PDF pages or figures visually inspected.','inventory_status':'Selective substantial inventory; not an exhaustive census.','total_cases':total,'relation_endpoint_cases':len(relations),'pages':ledger,'checks':checks,'remaining_gaps':['Uninspected pages/regions listed explicitly; damaged formulas, flattened table association, graphical content and exercise solutions remain partial.','No claim that source assertions are scientific truth; supported judgments mean source attribution.']}
(ROOT/'coverage-ledger.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print('cases',total,'projected pages',sum(x['state']=='projection_inspected' for x in ledger),'uninspected',[x['parent_physical_page'] for x in ledger if x['state']=='uninspected'])
print('all120 pages represented; exact span validation passed; input sha256 validation passed')
