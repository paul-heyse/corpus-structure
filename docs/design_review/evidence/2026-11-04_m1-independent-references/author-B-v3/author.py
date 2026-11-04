"""Independent B human-selected readings; machinery only locates/serializes exact literals."""
from pathlib import Path
import json,sys,hashlib,collections,datetime
ROOT=Path(__file__).resolve().parent
FREEZE=ROOT.parent/'freeze-002'
sys.path.insert(0,str(Path.cwd()/'python/corpus-structure/src'))
from corpus_structure.semantic.record_contracts import anchor_identity,evidence_set_identity,record_identity,interpretation_identity
CONTRACT=json.loads((FREEZE/'record-contract.json').read_text())
FAMILIES={r['family']:r for r in CONTRACT['families']}
UNITS={n:json.loads(next(FREEZE.glob(f'origin-*/unit-{n}.json')).read_text()) for n in range(1,12)}
RECORDS=collections.defaultdict(list)
LIMITS=collections.defaultdict(list)
SPECS=collections.defaultdict(list)
N=0

def unit(n):
 global N,V,T,NI,PIN
 N=n;V=UNITS[n]['source_frame']['source_views'][0];T=V['projection']['text'];NI=UNITS[n]['native_contexts'][0]['native_items'];PIN=UNITS[n]['source_frame']['evaluation_frame']['pin']

def loc(s,occ=0,within=None):
 if isinstance(s,tuple):return [s]
 base=0; hay=T
 if within:
  base=T.index(within);hay=within
 pos=-1
 for _ in range(occ+1):pos=hay.index(s,pos+1)
 return [(base+pos,base+pos+len(s))]

def at(ptr,s=None,occ=0):
 pieces=[p for p in V['projection']['pieces'] if p.get('item_ref')==ptr and p.get('kind')!='synthetic_separator']
 if s is None:
  return [(p['start'],p['end']) for p in pieces if p['end']>p['start']]
 for p in pieces:
  txt=T[p['start']:p['end']]
  if s in txt:
   pos=-1
   try:
    for _ in range(occ+1):pos=txt.index(s,pos+1)
   except ValueError:continue
   return [(p['start']+pos,p['start']+pos+len(s))]
 raise ValueError((N,ptr,s))

def L(s,occ=0,within=None):return ('literal',loc(s,occ,within))
def A(ptr,s=None,occ=0):return ('literal',at(ptr,s,occ))
def pieces(*args):return ('literal',[r for x in args for r in x[1]])
def C(kind,label,cue):return ('classified',kind,label,cue[1])
def native(ptr):return ('native',ptr)
def absent(reason='The inspected local source does not state this role.',state='unstated'):return ('absent',state,reason)
def limit(family,pointers,reason):LIMITS[N].append(dict(family=family,pointers=pointers,reason=reason,disposition='eligible_unrepresentable_or_unresolved'))

def record(family,**spec):
 cfg=FAMILIES[family];anchors={};sets={};fields=[];byrole={}
 def anch(a):
  a={'pin':PIN,**a};a['anchor_id']=anchor_identity(a);anchors[a['anchor_id']]=a;return a['anchor_id']
 def intervals(vals):
  out=[]
  for st,en in vals:
   covered=0
   for p in V['projection']['pieces']:
    if p.get('kind')=='synthetic_separator':continue
    s,e=max(st,p['start']),min(en,p['end'])
    if s>=e:continue
    ptr=p['item_ref']
    if p.get('source_field')=='cell_text':ptr+=f"/data/table_cells/{p['cell_index']}"
    if p.get('source_field','').startswith('chart_'):raise ValueError('unsupported chart anchor')
    out.append(anch(dict(space='selected_projection',pointer=ptr,precision='exact',start=s,end=e,source_piece=T[s:e])))
    covered+=e-s
   if covered==0:raise ValueError(('no genuine pieces',N,st,en))
  return out
 def ev(role,usage,aa):
  e=dict(role=role,usage=usage,ordering='ordered',anchors=aa);e['set_id']=evidence_set_identity(e);sets[e['set_id']]=e;return e['set_id']
 scopeptr=V['section_pointer']
 context=anch(dict(space='native',pointer=scopeptr,precision='item'))
 for rolecfg in cfg['roles']:
  role=rolecfg['role'];fc=rolecfg['field_class'];sp=spec.get(role,absent())
  kind=('classified' if fc in ['AssertionPolarityField','AssertionModalityField','DefinitionRelationField','MeasurementValueRoleField'] else 'native' if 'Native' in fc else 'normalized' if fc=='TransformedRecordField' else 'literal')
  f=dict(role=role,kind=kind,state='present',meaning_changing=rolecfg['meaning_changing'],evidence_status='available')
  if sp[0]=='absent':
   f.update(state=sp[1],reason=sp[2],evidence_sets=[ev(role,'context',[context])]);aa=[]
  elif sp[0]=='native':
   aa=[anch(dict(space='native',pointer=sp[1],precision='item'))];f.update(value=dict(kind='native_location',pointer=sp[1]),evidence_sets=[ev(role,'native',aa)])
  elif sp[0]=='classified':
   aa=intervals(sp[3]);f.update(value=dict(kind=sp[1],label=sp[2]),policy='statistics-m1-reference-3:explicit-source-grammar',evidence_sets=[ev(role,'classification_cue',aa)])
  else:
   aa=intervals(sp[1]);originals=[anchors[a]['source_piece'] for a in aa]
   if len(originals)==1:f.update(original=originals[0],value=dict(kind='text',text=originals[0]))
   else:f.update(original_pieces=originals,value=dict(kind='text_sequence',items=originals))
   f.update(evidence_sets=[ev(role,'literal',aa)])
  fields.append(f);byrole[role]=aa
 primary={'definition':['term','defining_text'],'assertion':['subject','predicate','object'],'measurement':['referent','property','original_value'],'table':['table','cell'],'formula_context':['formula','symbol']}[family]
 occurrence=list(dict.fromkeys(a for role in primary for a in byrole[role]))
 r=dict(contract=cfg['contract'],family=family,occurrence_recipe=cfg['occurrence_recipe'],pin=PIN,occurrence_anchors=occurrence,standing='accepted',policy_version='statistics-reference-reading-3',fields=fields,anchors=list(anchors.values()),evidence_sets=list(sets.values()))
 r['record_id']=record_identity(UNITS[N]['release_id'],r);r['interpretation_id']=interpretation_identity(r)
 RECORDS[N].append(r);SPECS[N].append(dict(family=family,record_id=r['record_id'],roles={k:v for k,v in spec.items()}));return r

def D(term,definition,alias=None,cue=None):
 return record('definition',term=term,defining_text=definition,scope=native(V['section_pointer']),alias=alias or absent(),relation_type=C('definition_relation','alias' if cue and any('synonym' in T[a:b] for a,b in cue[1]) else 'definition',cue) if cue else absent())
def Q(subject,predicate,obj,condition=None,polarity=None,modality=None,quantification=None,scope=None,attribution=None):
 return record('assertion',subject=subject,predicate=predicate,object=obj,condition=condition or absent(),polarity=polarity or absent('No independently explicit polarity classification cue beyond the quoted clause.'),modality=modality or absent('No separately explicit modal cue in the inspected clause.'),quantification=quantification or absent(),scope=scope or absent('No separate literal applicability scope is stated beyond the quoted clause and its supplied condition.'),attribution=attribution or absent())
def M(referent,prop,value,role='stated_value',cue=None,**kw):
 return record('measurement',referent=referent,property=prop,original_value=value,value_role=C('measurement_value_role',role,cue or prop),normalized_value=absent('This reference subset preserves source literals without numeric normalization.','inapplicable'),**kw)
def F(ptr,bindings=None,domain=None,assumption=None):
 formula=A(ptr)
 if not bindings:return record('formula_context',formula=formula,scope=native(V['section_pointer']),domain=domain or absent(),assumption=assumption or absent(),symbol=absent('Inspected local context has no explicit locatable symbol-to-meaning declaration for this formula occurrence.'),meaning=absent('No explicit local binding is stated for this formula occurrence.'))
 for binding in bindings:
  symbol,meaning=binding[:2];symbol_occ=binding[2] if len(binding)>2 else 0
  # First use is selected by the human-supplied exact literal, within this formula only.
  record('formula_context',formula=formula,scope=native(V['section_pointer']),symbol=A(ptr,symbol,symbol_occ),meaning=meaning,domain=domain or absent(),assumption=assumption or absent())

def q(s,p,o,cond=None,neg=False,modal=None,quant=None,scope=None,attr=None):
 def options(v):
  if isinstance(v,tuple):return [v]
  out=[];pos=-1
  while True:
   pos=T.find(v,pos+1)
   if pos<0:break
   out.append(('literal',[(pos,pos+len(v))]))
  if not out:raise ValueError(('q literal unavailable',N,v))
  return out
 triples=[]
 for ss in options(s):
  for pp in options(p):
   if ss[1][-1][1]>pp[1][0][0]:continue
   for oo in options(o):
    if pp[1][-1][1]<=oo[1][0][0]:
     triples.append((oo[1][-1][1]-ss[1][0][0],ss,pp,oo))
 if not triples:raise ValueError(('q needs explicit discontinuous authoring',N,s,p,o))
 _,ss,pp,oo=min(triples,key=lambda x:x[0])
 center=(ss[1][0][0]+oo[1][-1][1])/2
 def near(v):
  if v is None:return None
  return min(options(v),key=lambda z:abs((z[1][0][0]+z[1][-1][1])/2-center))
 return Q(ss,pp,oo,condition=near(cond),
  polarity=C('assertion_polarity','negative' if neg else 'positive',pp),
  modality=C('assertion_modality',modal or 'asserted',pp),
  quantification=near(quant),scope=near(scope),attribution=near(attr))

def d(term,clause,alias=None,cue=None):
 defining=L(clause)
 termlit=L(term,within=clause) if term in clause else L(term)
 return D(termlit,defining,L(alias,within=clause) if alias and alias in clause else L(alias) if alias else None,L(cue,within=clause) if cue and cue in clause else L(cue) if cue else None)

unit(4)
d('joint probability statements','Probability statements concerning more than one random variate are called joint probability statements',cue='are called')
d('bivariate','call the pair (X, Y) a bivariate',cue='call')
d('univariates','each of X and Y alone referred to as univariates',cue='referred to as')
d('multivariate','the collection of variates is more generally referred to as a multivariate',cue='referred to as')
d('joint range','The set ℜX,Y is the joint range of (X, Y)',cue='is the')
d('bivariate quantile','We refer to (x, y) as a bivariate quantile of (X, Y)',cue='refer to')
d('Pr[X ≤ x, Y ≤ y]','Let Pr[X ≤ x, Y ≤ y] mean "the probability that the value realized by the univariate X is less than or equal to x and the value realized by the univariate Y is less than or equal to y."',cue='mean')
d('joint probability domain','Analogous to the univariate case, ℜ α X,Y is called the joint probability domain of the bivariate (X, Y)',cue='is called')
d('distribution function','The distribution function (joint df) F associated with a bivariate (X, Y) maps from the joint range ℜX,Y into the joint probability domain ℜ α X,Y and is such that',alias='joint df')
# The definition includes the equation as a separately anchored genuine continuation.
RECORDS[4].pop();SPECS[4].pop()
D(L('distribution function'),pieces(L('The distribution function (joint df) F associated with a bivariate (X, Y) maps from the joint range ℜX,Y into the joint probability domain ℜ α X,Y and is such that'),A('#/texts/19')),L('joint df'))
D(L('bivariate probability density function'),pieces(L('When (X, Y) have a jointly continuous probability domain, the function f (x, y) is a bivariate probability density function (joint pdf) if'),A('#/texts/23'),L('for all (x, y) in ℜX,Y')),L('joint pdf'))
d('bivariate probability function','In this case f (x, y) is the bivariate probability function (joint pf)',alias='joint pf',cue='is the')
q('Joint probability statements','can be made about','a combination of variates, all having continuous domain, all having countable domain, or some combination of continuous and countable domains',modal='possible')
q('both conditions X ≤ x and Y ≤ y','hold','simultaneously',cond='In this case')
q('ℜ α X,Y','is','the line segment [0, 1]',cond='When X and Y are jointly continuous')
q('ℜ α X,Y','may be','a subset of [0, 1]',cond='In all other cases',modal='possible')
q('The function F(x, y)','is','nondecreasing in each of x and y')
q('The function F(x, y)','attains','a value of unity',cond='when both x and y are at their respective maxima')
q('the probability associated with an arbitrary bivariate quantile set A','is equal to','the area under the bivariate pdf surface A',scope='This relationship')
q('A discrete bivariate (X, Y )','takes','discrete values (x, y) with finite probabilities f (x, y)')
q('the joint range','is','ℜX,Y = {(0, 0) , (1, 0) , (2, 0) , (0, 1) , (1, 1) , (1, 2)}',cond='As the joint distribution function changes only when x reaches zero, one or two, and when y reaches zero or one')
q('the joint probability domain','is','ℜ α X,Y = { 1 8 , 1 4 , 1 2 , 3 4 , 11 16 , 1}',cond='In this case')
F('#/texts/19',[('F',L('distribution function (joint df) F')),('x',L('the real valued pair (x, y)')),('y',L('the real valued pair (x, y)'))],domain=L('( x , y ) \\in \\Re _ { X , Y } , \\, \\alpha \\in \\Re _ { X , Y } ^ { \\alpha }'))
F('#/texts/23',[('F',L('distribution function (joint df) F')),('f',L('bivariate probability density function (joint pdf)'))],domain=L('for all (x, y) in ℜX,Y'),assumption=L('When (X, Y) have a jointly continuous probability domain'))
F('#/texts/25',[('f',L('bivariate probability density function (joint pdf)')),('F',L('distribution function (joint df) F'))],assumption=L('When (X, Y) have a jointly continuous probability domain'))
F('#/texts/27',[('A',L('an arbitrary bivariate quantile set A')),('f',L('bivariate probability density function (joint pdf)'))])
F('#/texts/34',[('F',L('joint distribution function given by'))],assumption=L('Consider the discrete bivariate (X, Y)'))
# The six headerless native cells are faithful probability statements but not accepted table records:
# TableRecordFields requires a header_path that the source does not state.
limit('table',['#/tables/0'],'All six native data cells have no stated row or column header path. Required header_path cannot be invented; cells retained and read as formula/measurement statements below.')
for idx,c in enumerate(NI['#/tables/0']['data']['table_cells']):
 ptr=f'#/tables/0/data/table_cells/{idx}';text=c['text']; ref,val=text.split(' = ',1) if False else (text.rsplit(' = ',1)[0],text.rsplit(' = ',1)[1])
 # Native probability prefix is an explicit property cue; no synthesized "probability" literal.
 M(A('#/tables/0',ref),A('#/tables/0','Pr',0),A('#/tables/0',val,0),cue=A('#/tables/0','Pr',0),condition=L('Consider the discrete bivariate (X, Y)')) if idx==0 else None
 # Exact cell-located readings use projection ranges for each occurrence.
 p=next(p for p in V['projection']['pieces'] if p.get('item_ref')=='#/tables/0' and p.get('cell_index')==idx)
 start=p['start'];j=text.rfind(' = ')
 if idx==0:RECORDS[4].pop();SPECS[4].pop()
 M(L((start,start+j)),L((start,start+2)),L((start+j+3,p['end'])),condition=L('Consider the discrete bivariate (X, Y)'))
 record('formula_context',formula=L((start,p['end'])),scope=native(V['section_pointer']),symbol=absent('The headerless probability statement declares no symbol meaning locally.'),meaning=absent('No local symbol declaration is stated.'))

unit(5)
d('marginal distribution','Probabilities associated with a univariate element of a bivariate without regard to the value of the other univariate element within the same bivariate arise from the marginal distribution of that univariate')
D(L('marginal probability density function'),pieces(L('In the case of continuous bivariate (X, Y) having joint pdf f (x, y), the marginal probability density function (marginal pdf) of the univariate X is found for each quantile x by integrating the joint pdf over all possible bivariate quantiles (x, y) ∈ ℜX,Y having fixed value for x'),A('#/texts/40')),L('marginal pdf'))
D(L('marginal probability function'),pieces(L('In the case of discrete variates X and Y, the marginal probability function (marginal pf) of X is found for each quantile x by summing the joint pf associated with the bivariate quantiles (x, y) ∈ ℜX,Y having fixed x'),A('#/texts/47')),L('marginal pf'))
Q(L('the (univariate) range, quantile, and probability domain associated with the univariate element'),L('are',within='Corresponding to such a marginal distribution are'),L('Corresponding to such a marginal distribution'),scope=L('with each one consistent with the corresponding bivariate entity'),polarity=C('assertion_polarity','positive',L('are',within='Corresponding to such a marginal distribution are')))
q('The corresponding marginal domain for X','is','ℜX = {0, 1, 2}',cond='Continuing Example 4.1.1')
q('The corresponding marginal domain for X','is','ℜX = {0, 1, 2}',cond='Continuing Example 4.1.1')
RECORDS[5].pop();SPECS[5].pop()
q('marginal probability domain ℜ α X','=','{1/4, 3/4, 1}',cond='Continuing Example 4.1.1')
q('The corresponding marginal domain for Y','is','ℜY = {0, 1}',cond='Continuing Example 4.1.1')
q('marginal probability domain ℜ α Y','=','{11/16, 1}',cond='Continuing Example 4.1.1')
F('#/texts/40',[('f \\left ( x \\right )',L('marginal probability density function (marginal pdf) of the univariate X')),('f \\left ( x , y \\right )',L('joint pdf f (x, y)'))],assumption=L('In the case of continuous bivariate (X, Y) having joint pdf f (x, y)'))
F('#/texts/45',[('f \\left ( y \\right )',L('the marginal pdf of the univariate Y')),('f \\left ( x , y \\right )',L('joint pdf f (x, y)'))])
F('#/texts/47',[('f \\left ( x \\right )',L('marginal probability function (marginal pf) of X'))],assumption=L('In the case of discrete variates X and Y'))
F('#/texts/48')
for ptr in ['#/tables/1','#/tables/2']:
 limit('table',[ptr],'Headerless native equation layout has no stated header_path; all native cells inspected. Equality and probability literals cannot supply a fabricated table header.')
# Five expressly stated numeric probabilities; row geometry does not become row_label.
for ptr,ri,vi in [('#/tables/1',0,4),('#/tables/1',5,9),('#/tables/1',10,14),('#/tables/2',0,4),('#/tables/2',5,9)]:
 ps={p['cell_index']:p for p in V['projection']['pieces'] if p.get('item_ref')==ptr and 'cell_index' in p}
 a,b=ps[ri],ps[vi]
 M(L((a['start'],a['end'])),L((a['start'],a['start']+2)),L((b['start'],b['end'])),condition=L('Continuing Example 4.1.1'))

unit(6)
d('independent','Two univariates are said to be independent if the marginal probabilities associated with the outcomes of one variate are not influenced by the observed value of the other variate, and vice versa',cue='are said to be')
q('the marginal probabilities associated with the outcomes of one variate','are not influenced by','the observed value of the other variate, and vice versa',cond='Two univariates are said to be independent',neg=True)
limit('assertion',['#/texts/53','#/texts/54'],'Sentence about continuous pdf decomposition is split by the fused stray phrase "The marginal pf of Y is". Intended clause cannot be reconstructed without repairing source words.')
q('the joint pf for a discrete bivariate with independent discrete univariate elements','may be decomposed into','the product of the marginal pfs',modal='possible')
F('#/texts/55',assumption=L('with independent discrete univariate elements'))

unit(7)
d('dependent','When two univariates are not independent, they are said to be dependent',cue='are said to be')
d('conditional probabilities','Such probabilities are called conditional probabilities',cue='are called')
# Defining clauses retain the qualification and formula continuation.
D(L('conditional pf of X'),pieces(L('When conditioning on a single observed value of one univariate component Y = y of a discrete bivariate (X, Y), the conditional pf of X, given Y = y, and denoted by f (x|y), is found by taking the ratio of the joint pf f(x, y) to the marginal pf of Y, f (y), for fixed Y = y'),A('#/texts/62'),L('for all (x, y) ∈ ℜX,Y')),L('f (x|y)'))
D(L('conditional probability density function'),pieces(L('For continuous random variates, the conditional probability density function (conditional pdf) for X given Y = y and denoted by f (x|y) may be constructed using the ratio of the joint pdf over the marginal pdf of Y, for fixed Y = y'),A('#/texts/66')),L('conditional pdf'))
d('composition','Joint, marginal, and conditional probabilities satisfy the property of composition, whereby joint probabilities may be determined by the product of marginal probabilities and the appropriate conditional probability')
q('joint probabilities','may be determined by','the product of marginal probabilities and the appropriate conditional probability',modal='possible')
q('Equation (4.1)','holds','whether the variables are dependent or independent')
q('These conditional probabilities associated with the univariate X given Y = 0','are not','the same as those obtain by conditioning on a value of Y = 1',neg=True)
q('composition','may be used to reconstruct','the joint probabilities for (X, Y)',modal='possible')
F('#/texts/58',assumption=L('provided the denominator Pr[Y ≤ y] is nonzero'))
F('#/texts/62',[('f \\left ( x | y \\right )',L('the conditional pf of X, given Y = y')),('f \\left ( x , y \\right )',L('the joint pf f(x, y)')),('f \\left ( y \\right )',L('the marginal pf of Y, f (y)'))],domain=L('for all (x, y) ∈ ℜX,Y'),assumption=L('When conditioning on a single observed value of one univariate component Y = y of a discrete bivariate (X, Y)'))
F('#/texts/64',domain=L('for all (x, y) ∈ ℜX,Y'))
F('#/texts/66',[('f \\left ( x | y \\right )',L('conditional probability density function (conditional pdf) for X given Y = y'))],assumption=L('For continuous random variates'))
F('#/texts/68',assumption=L('For continuous random variates'))
for ptr in ['#/texts/72','#/texts/74']:F(ptr)
F('#/texts/76',assumption=L('if X and Y are independent'))
for ptr in ['#/texts/79','#/texts/81','#/texts/83','#/texts/84','#/texts/87','#/texts/89']:F(ptr,assumption=L('Again continuing Example 4.1.1'))
# Explicit derived numeric answers remain literal; no arithmetic performed.
for ptr,ref,val in [('#/texts/79',r'\Pr [ X = 0 | Y = 0 ]','2 / 1 1'),('#/texts/79',r'\Pr [ X = 1 | Y = 0 ]','6 / 1 1'),('#/texts/79',r'\Pr [ X = 2 | Y = 0 ]','3 / 1 1'),('#/texts/81',r'\Pr [ X = 0 | Y = 1 ]','2 / 5'),('#/texts/81',r'\Pr [ X = 1 | Y = 1 ]','2 / 5'),('#/texts/81',r'\Pr [ X = 2 | Y = 1 ]','1 / 5'),('#/texts/83',r'\Pr [ Y = 0 | X = 0 ]','1 / 2'),('#/texts/84',r'\Pr [ Y = 1 | X = 0 ]','1 / 2'),('#/texts/84',r'\Pr [ Y = 0 | X = 1 ]','3 / 4'),('#/texts/84',r'\Pr [ Y = 1 | X = 1 ]','1 / 4'),('#/texts/87',r'\Pr [ Y = 0 | X = 2 ]','3 / 4'),('#/texts/87',r'\Pr [ Y = 1 | X = 2 ]','1 / 4')]:
 # Numeric values located after their particular lhs so repeated value spellings do not alias.
 rr=A(ptr,ref);end=rr[1][-1][1];p=at(ptr)[0];j=T.index(val,end,p[1]);M(rr,L((rr[1][0][0],rr[1][0][0]+3)),L((j,j+len(val))),condition=L('Again continuing Example 4.1.1'))
M(A('#/texts/89',r'\Pr [ X = 0 , Y = 1 ]'),A('#/texts/89',r'\Pr'),A('#/texts/89',r'\frac { 1 } { 8 }'),condition=L('Again continuing Example 4.1.1'))

unit(8)
d("Bayes' theorem","A fundamental result concerning conditional probabilities is known as Bayes' theorem, providing the rule for reversing the roles of variates in a conditional probability",cue='is known as')
q('the terms denoted by f(·) in Equation (4.2)','relate to','marginal and conditional pdfs',cond='For a continuous bivariate')
q('these terms','relate to','marginal and conditional pfs',cond='for a discrete bivariate')
q("Using Bayes' theorem in Equation (4.2)",'relates','the conditional probability Pr[X = x|Y = y] to the conditional probability Pr[Y = y|X = x]',cond='Discrete Bivariate Continued')
F('#/texts/93');F('#/texts/97',assumption=L('Discrete Bivariate Continued'))
limit('measurement',['#/texts/98','#/texts/99'],'"So, for example," followed by "as before" supplies no numeric worked answer in this unit. The next section contains the formula; do not fabricate a missing occurrence here.')

unit(9)
q('ψ(X, Y)','is','a variate such that if xX and xY are random numbers of X and Y, respectively, then ψ(xX, xY ) is a random number of ψ(X, Y)',cond='If (X,Y) is a bivariate with range ℜX,Y and ψ is a functional mapping from ℜX,Y into the real line')
q('the characteristic function of the sum of two independent variates','is','the product of the characteristic functions of the individual variates',cond='when X and Y are independent and where the function is a summation, say, Z = X+Y')
q('X1 +X2','is not','the same as 2X1',cond='even though X1 ∼ X2',neg=True)
q('The term X1 +X2','is','a variate for which a random number can be obtained by choosing a random number of X1 and then another independent random number of X2 and then adding the two')
q('The term 2X1','is','a variate for which a random number can be obtained by choosing a single random number of X1 and multiplying it by two')
q('the distribution of each X variate','is governed by','the same set of parameters, (a, b)',cond='If there are n such independent variates of the form (X : a, b) to be summed',quant='each X variate')
F('#/texts/103')
M(A('#/texts/103',r'\Pr [ X = 2 | Y = 0 ]'),A('#/texts/103',r'\Pr'),A('#/texts/103','3 / 1 1'),condition=L('by analysis of the joint distribution of the variates in question'))
F('#/texts/107',assumption=L('two or more variates that are independently and identically distributed'))
F('#/texts/110',[('i',L('the subscript i identifies the ith variate'),1)],domain=L('for i = 1, 2, . . . n'),assumption=L('If there are n such independent variates of the form (X : a, b) to be summed'))
F('#/texts/113',assumption=L('When the variates to be summed differ in their parameters'))

unit(10)
d('mean','the mean is the sum of the data points divided by the number of data points',cue='is the')
d('average','We will use the term average as a synonym for the mean',alias='mean',cue='as a synonym for')
d('typical value','the term typical value to refer generically to measures of location')
d('median','the median is the value of the point which has half the data smaller than that point and half the data larger than that point',cue='is the')
d('mode','the mode is the value of the random sample that occurs with the greatest frequency',cue='is the')
d('symmetric','By symmetric, we mean that the distribution can be folded about an axis so that the 2 sides coincide',cue='we mean')
d('robustness','robustness is a lack of susceptibility to the effects of nonnormality',cue='is a')
d('Robustness of validity','Robustness of validity means that the confidence intervals for the population location have a 95% chance of covering the population location regardless of what the underlying distribution is',cue='means')
d('Robustness of efficiency','Robustness of efficiency refers to high effectiveness in the face of non-normal tails',cue='refers to')
d('Mid-Mean','Mid-Mean - computes a mean using the data between the 25th and 75th percentiles')
d('Trimmed Mean','Trimmed Mean - similar to the mid-mean except different percentile values are used')
d('Winsorized Mean','Winsorized Mean - similar to the trimmed mean. However, instead of trimming the points, they are set to the lowest (or highest) value')
d('Mid-range','Mid-range = (smallest + largest)/2',cue='=')
q('It','is not','necessarily unique',neg=True,scope='the mode is the value of the random sample that occurs with the greatest frequency')
q('The mode','is typically used','in a qualitative fashion')
q('any specific value','may not occur','more than once',cond='if the data are continuous',neg=True,modal='possible')
limit('definition',['#/texts/8','#/texts/16','#/texts/102'],'Continuous-mode alternative is split by page furniture and duplicated continuation. The repeated "of the class interval..." creates competing source boundaries; no repaired complete definition emitted.')
q('The first histogram','is','a sample from a normal distribution')
q('The normal distribution','is','a symmetric distribution with well-behaved tails and a single peak at the center of the distribution')
q('it','behaves','the same to the left and right of some center point',scope='By symmetric')
q('the mean, median, and mode','are','actually equivalent',cond='For a normal distribution')
q('The histogram above','generates','similar estimates for the mean, median, and mode')
q('it','is reasonable to use','the mean as the location estimator',cond='if a histogram or normal probability plot indicates that your data are approximated well by a normal distribution')
q('The second histogram','is','a sample from an exponential distribution')
q('The exponential distribution','is','a skewed, i. e., not symmetric, distribution')
q('the mean and median','are not','the same',cond='For skewed distributions',neg=True)
q('The mean','will be pulled','in the direction of\nthe skewness')
q('the mean','will be greater than','the median',cond='if the right tail is heavier than the left tail')
q('the mean','will be less than','the median',cond='if the left tail is heavier than the right tail')
q('all three measures','are','useful',cond='In this case',scope='For skewed distributions')
q('The third histogram','is','a sample from a Cauchy distribution')
q('The Cauchy distribution','is','a symmetric distribution with heavy tails and a single peak at the center of the distribution')
q('collecting more data','does not provide','a more accurate estimate of the mean',neg=True,scope='The Cauchy distribution')
q('the sampling distribution of the mean','is equivalent to','the sampling distribution of the original data',scope='The Cauchy distribution')
q('the mean','is','useless as a measure of the typical value',scope='for the Cauchy distribution')
q('the mean of 3.7','is','well above the vast majority of the data',cond='For this histogram')
q('the median','does provide','a useful measure for the typical value',scope='The Cauchy distribution')
q('Extreme values in the tails','distort','the mean')
q('these extreme values','do not distort','the median',cond='since the median is based on ranks',neg=True)
q('the median','provides','a better estimate of location than does the mean',cond='for data with extreme values in the tails')
q('The fourth histogram','is','a sample from a lognormal distribution')
q('The lognormal','is','also a skewed distribution')
q('the mean and median','do not provide','similar estimates for the location',scope='The lognormal',neg=True)
q('the mean','is','an optimal estimator',cond='if in fact your data are normal')
q('confidence intervals for the population location','tend to be','almost as narrow as the best that could be done if we knew the true shape of the distributuion',scope='Robustness of efficiency')
q('The mean','is','an example of an estimator that is the best we can do',cond='if the underlying distribution is normal')
q('it','lacks','robustness of validity',scope='The mean')
q('confidence intervals based on the mean','tend not to be','precise',cond='if the underlying distribution is in fact not normal',neg=True)
q('The median','tends to have','robustness of validity')
q('The median','tends to have','not robustness of efficiency',neg=True)
q('The alternative measures of location','try to balance','these two concepts of robustness')
q('the confidence intervals','should be','almost as narrow as the confidence intervals based on the mean',cond='for the case when the data are normal',modal='required')
q('they','should maintain','their validity',cond='even if the underlying data are not normal',modal='required')
q('these alternatives','address','the problem of heavy-tailed distributions')
q('all data below the 5th percentile','are set equal to','the value of the 5th percentile',cond='For example',quant='all data below the 5th percentile',scope='Winsorized Mean')
q('all data greater than the 95th percentile','are set equal to','the 95th percentile',cond='For example',quant='all data greater than the 95th percentile',scope='Winsorized Mean')
q('they','are not unduly affected by','extremes in the tails',neg=True,scope='The first three alternative location estimators defined above')
q('they','generate','estimates that are closer to the mean',cond='for data that are normal (or nearly so)',scope='The first three alternative location estimators defined above')
q('The mid-range','is not','robust',cond='since it is based on the two most extreme points',neg=True)
q('Its use','is typically restricted to','situations in which the behavior at the extreme points is relevant',scope='The mid-range')
q('Most general purpose statistical software programs','can compute','at least some of the measures of location discussed above',modal='possible')
# Numeric source statements: all values remain text, including literal signs and spaces.
for ptr,ref,vals in [('#/texts/20','The first histogram',[('mean','0.005','mean'),('median','-0.010','median'),('mode','- 0.144','stated_value')]),('#/texts/21','The second histogram',[('mean','1.001','mean'),('median','0.684','median'),('mode','0.254','stated_value')]),('#/texts/154','The fourth histogram',[('mean','1.677','mean'),('median','0.989','median'),('mode','0.680','stated_value')])]:
 for prop,val,role in vals:M(A(ptr,ref),A(ptr,prop),A(ptr,val),role,condition=A(ptr,'the mode is computed as the midpoint of the histogram interval with the highest peak') if prop=='mode' else absent())
M(L('This plot'),L('random numbers'),L('10,000'),'count',condition=L('generated from a normal, an exponential, a Cauchy, and a lognormal distribution'))
M(L('The full Cauchy data set'),L('minimum'),L('-29,000'),uncertainty=L('approximately',0))
M(L('The full Cauchy data set'),L('maximum'),L('89,000'),uncertainty=L('approximately',1))
M(L('this histogram'),L('mean',within='For this histogram, the mean of 3.7 is well above the vast majority of the data'),L('3.7'),'mean')
M(L('the confidence intervals for the population location'),L('chance'),L('95%'),condition=L('regardless of what the underlying distribution is'))
M(L('the points in both the lower and upper tails'),L('trim'),L('5%'),condition=L('A common choice'))
F('#/texts/124')
# Y tilde is the displayed canonical literal. It is not silently changed to a bar/mean symbol.
F('#/texts/133',assumption=L('if N is odd'),domain=L('a random sample sorted from smallest value to largest value'))
F('#/texts/134',assumption=L('if N is even'),domain=L('a random sample sorted from smallest value to largest value'))
record('formula_context',formula=L('(smallest + largest)/2'),scope=native(V['section_pointer']),symbol=absent('No explicit symbol binding is declared in the local mid-range formula.'),meaning=absent('No symbol declaration stated.'))

unit(11)
d('Confidence limits for the mean','Confidence limits for the mean (Snedecor and Cochran, 1989) are an interval estimate for the mean',cue='are an')
d('confidence coefficient','The confidence coefficient is simply the proportion of\nsamples of a given size that may be expected to contain the true mean',cue='is simply')
q('Interval estimates','are often','desirable',cond='because the estimate of the mean varies from sample to sample')
q('a confidence interval','generates','a lower and upper limit for the mean',scope='Instead of a single estimate for the mean')
q('The interval estimate','gives','an indication of how much uncertainty there is in our estimate of the true mean')
q('The narrower the interval','the more precise','is our estimate')
q('Confidence limits','are expressed','in terms of a confidence coefficient')
q('a 95 % confidence interval','doesnotmean','that there is a 95 % probability\nthat the interval contains the true mean',neg=True)
q('The interval computed from a given sample','either\ncontains','the true mean or it does not')
q('the level of confidence','is associated with','the\nmethod of calculating the interval')
q('about 95 % of these intervals','would contain','the true mean',cond='for a 95 %\nconfidence interval, if many samples are collected and the confidence interval computed',scope='in\nthe long run',modal='hypothetical')
q('the confidence coefficient','is','1 - α')
q('the width of the interval','is controlled by','two factors',scope='From the formula')
q('the interval','gets','narrower from the V term',cond='As N increases')
q('one way to obtain more precise estimates for the mean','is','to increase the sample\nsize')
q('The larger the sample standard deviation','the larger','the confidence interval')
q('noisy data, i.e., data with a large standard deviation','are going to generate','wider intervals than data with a smaller standard deviation')
q('the confidence interval','is converted','to hypothesis-test form',cond='To test whether the population mean has a specific value, , against the two-sided alternative that it does not have a value ,')
q('The test','is','a one-sample t-test')
q('We','reject','the null hypotheses for our two-tailed t-test',cond='because the absolute value of the test\nstatistic is greater than the critical value')
q('we','would still reject','the null hypothesis',cond='If we were to perform an upper, one-tailed test',modal='hypothetical')
q('The confidence interval','provides','an alternative to the hypothesis test')
q('H0','cannot be','rejected',cond='If the confidence\ninterval contains 5',neg=True,modal='possible')
q('the confidence interval\n(9.258242, 9.264679)','does not contain','5',cond='In our example',neg=True)
q('the population mean','does not equal','5',scope='at the 0.05 level of significance',cond='In our example',neg=True)
q('there','are','three possible alternative hypotheses and rejection regions for the one-\nsample t-test')
q('Confidence intervals for other location estimators such as the median or mid-mean','tend to be','mathematically difficult or intractable')
q('confidence intervals','can be obtained','using the bootstrap',cond='For these cases',modal='possible')
# Display Y differs from declaration Y-bar; alpha occurrence in subscript remains a genuine glyph use.
limit('formula_context',['#/texts/111','#/texts/112'],'Displayed Y is not the declared Y-bar; t subscript spelling differs from declaration. No fabricated symbol anchor for transformed glyphs; s/N/α bindings remain independently locatable.')
for sym,meaning in [('s','the sample standard deviation'),('N','the sample size'),('α','the\ndesired significance level')]:
 record('formula_context',formula=A('#/texts/111'),scope=native(V['section_pointer']),symbol=A('#/texts/111',sym),meaning=A('#/texts/112',meaning),domain=absent(),assumption=absent())
F('#/texts/84',[('N',A('#/texts/112','the sample size'))]);F('#/texts/85',[('N',A('#/texts/112','the sample size'))])
F('#/texts/80',[('N',A('#/texts/112','the sample size')),('s',A('#/texts/112','the sample standard deviation'))])
limit('formula_context',['#/texts/80','#/texts/81'],'Canonical T display contains A0 and Y, while declaration is missing except N and s from prior explicit declaration. No repair to mu0 or Y-bar; other symbol bindings not asserted.')
for ptr in ['#/texts/76','#/texts/79']:F(ptr)
for prop,val,role in [('N','195','count'),('MEAN','9.261460','mean'),('STANDARD DEVIATION','0.022789','dispersion'),('t1-0.025,N-1','1.9723','stated_value'),('LOWER LIMIT','9.261460 - 1.9723*0.022789/√195','bound'),('UPPER LIMIT','9.261460 + 1.9723*0.022789/√195','bound')]:
 M(L('ZARR13.DAT data set',1),A('#/texts/88',prop),A('#/texts/88',val),role,condition=L('95 %, two-sided confidence interval',1))
M(L('the mean',within='Thus, a 95 % confidence interval for the mean is (9.258242, 9.264679).'),L('confidence interval',within='Thus, a 95 % confidence interval for the mean is (9.258242, 9.264679).'),L('(9.258242, 9.264679)'), 'bound',condition=L('95 %',within='Thus, a 95 % confidence interval for the mean is (9.258242, 9.264679).'))
for prop,val,role in [('Test statistic','2611.284','stated_value'),('Degrees of freedom','194','count'),('Significance level','0.05','stated_value'),('Critical value','1.9723','bound')]:
 M(L('ZARR13.DAT data set',2),A('#/texts/91',prop),A('#/texts/91',val),role,condition=L('two-sided, one-sample t-test'))
M(L('an upper, one-tailed test'),L('critical value',within=NI['#/texts/140']['text']),L('1.6527'),'bound',condition=L('If we were to perform an upper, one-tailed test'))
M(L('a 95 %\nconfidence interval'),L('intervals would contain the true mean'),L('about 95 %'),condition=L('if many samples are collected and the confidence interval computed'))
limit('measurement',['#/texts/82'],'"The most commonly used value for is 0.05" loses its referent. Significance Level heading is present but absent symbol not restored; unresolved property/value association retained.')
# Explicit native table: six data cells, each with its actual column header and separately quoted row label only for rejection cells.
ptr='#/tables/0';ps={p['cell_index']:p for p in V['projection']['pieces'] if p.get('item_ref')==ptr and 'cell_index' in p}
def cell_literal(idx):
 c=NI[ptr]['data']['table_cells'][idx]
 if idx in ps:return L((ps[idx]['start'],ps[idx]['end']))
 refs=set()
 def descend(ref):
  refs.add(ref)
  for child in NI[ref].get('children',[]):descend(child['$ref'])
 descend(c['ref']['$ref'])
 return ('literal',[(p['start'],p['end']) for p in V['projection']['pieces'] if p.get('item_ref') in refs and p['end']>p['start']])
for idx,c in enumerate(NI[ptr]['data']['table_cells']):
 if c['column_header']:continue
 col=c['start_col_offset_idx'];cv=cell_literal(idx);hv=cell_literal(col);rl=cell_literal(idx-col)
 record('table',table=native(ptr),cell=native(f'{ptr}/data/table_cells/{idx}'),cell_value=cv,header_path=hv,row_label=rl if col==1 else absent('This cell itself is the stated alternative hypothesis; no separate row label is stated.'),caption=absent('No caption is stated for this native table.'),unit=absent('No unit is stated for this native table.'),note=absent('No note is attached or applicable to this native table.'))
 # Each symbolic data-cell literal is also a native formula occurrence; no declarations are invented.
 record('formula_context',formula=cv,scope=native(V['section_pointer']),symbol=absent('This table cell makes no local symbol-to-meaning declaration.'),meaning=absent('No local symbol declaration.'),domain=absent(),assumption=L('In general, there are three possible alternative hypotheses and rejection regions for the one-\nsample t-test'))

unit(2)
d('uniformly distributed','IfXis a random variable which represents the outcome of an experiment of this type, then we say thatXis uniformly distributed',cue='we say that')
d('distribution functionm(\\omega)','If the sample spaceSis of sizen, where0<n<\\infty, then the distribution functionm(\\omega)is defined to be 1_/n_ for all\\omega\\in S',cue='is defined to be')
d('binomial distribution','It is the distribution of the random variable which counts the number of heads which occur when a coin is tossedntimes, assuming that on any one toss, the probability that a head occurs isp')
D(L('geometric distribution'),pieces(L('In general, if 0< p <1, and q = 1 −p, then we say that the random variable T\nhas ageometric distributionif'),A('#/texts/290'),L('for j = 1, 2, 3, .....')),cue=L('we say that',1))
d('"memoryless" property','Thus, the probability that the customer’s service takessmore time units is independent of the length of timerthat the customer has already been served. Because of this interpretation, this property is called the "memoryless" property',cue='is called')
d('negative binomial distribution','For a generalk, we say thatXhas a negative binomial distribution',cue='we say that',alias=None)
D(L('Poisson distribution',2),pieces(A('#/texts/403'),L('The above distribution is the Poisson distribution')),cue=L('is the Poisson distribution'))
D(A('#/texts/267'),L('the notation\\lfloor x\\rfloordenotes the greatest integer not exceedingx'),cue=L('denotes'))
D(A('#/texts/127'),L('the notation\\lceil x\\rceilmeans the least integer which is greater than or equal tox'),cue=L('means the least'))
q('all outcomes of an experiment','are','equally likely',cond='in many cases, we assume',quant='all outcomes of an experiment')
q('this experiment','can be simulated','on a computer using the programGeneralSimulation',scope='all of the discrete probability distributions discussed in this chapter',modal='possible')
q('a faster algorithm','can be used','instead',cond='in this case',modal='possible')
q(L('The expression'),L('takes on as a value'),L('each integer between 1 andnwith probability 1_/n_'))
q('it','is not possible to have','an experiment which is uniform on this set',cond='If the sample space is a countably infinite set, such as the set of positive integers',neg=True,modal='possible')
q('we','use','continuous density functions',cond='If the sample space is an uncountable set, with positive, finite length, such as the interval [0, 1]')
q('One straightforward way to simulate a binomial random variable X','is','to compute the sum ofnindependent 0-1 random variables, each of which take on the value 1 with probabilityp')
q('This method','requires','ncalls to a random number generator to obtain one value of the random variable')
q('the binomial distribution','is well-approximated by','the corresponding normal density function',cond='Whennis relatively large (say at least 30)',scope='with parameters\\mu=\\npand\\sigma=\\sqrt{npq}',attr='the Central Limit Theorem')
q('we','can use','the value',cond='if-1/2\\le Y<n+1/2',modal='possible',scope='to represent the random variableX')
q('we','reject','Yand compute another value',cond='IfY <-1_/2 or Y > n+1/_2')
q('we','can determine','the distribution for any random variableXrelating to the experiment',cond='providedP(X=a) can be computed in terms of a finite number of trials',modal='possible')
q('The left-hand expression','is','just a geometric series with first term p and common\nratio q')
q('we','are more likely\nto get','large values for T',cond='as p decreases',modal='probable')
q('the most probable\nvalue for T','is','1',cond='In both cases')
q('Y','is geometrically distributed','with parameterp')
q('log(1-rnd) and log(rnd)','are','identically distributed')
q('Y','can also be generated','using the equation',cond='Since log(1-rnd) and log(rnd) are identically distributed',modal='possible')
q('either 0 or 1 new customers','arrive','at the counter',cond='suppose a line of customers waits for service at a counter',scope='in each small time unit',modal='hypothetical')
q('the timeTuntil the next arrival','has','a geometric distribution',cond='suppose a line of customers waits for service at a counter')
q('arrivals in any two time units','are','independent events',cond='suppose a line of customers waits for service at a counter')
q('the length of time required to service a customer','also has','a geometric distribution but with a different value forp',cond='It is often assumed')
q('this property','is also obeyed by','the exponential distribution',scope='the "memoryless" property')
q('X','is','geometrically distributed',cond='Whenk=1')
q('X','can be understood as','the sum ofkoutcomes of a geometrically distributed experiment with parameterp',scope='negative binomial distribution',modal='possible')
q('The Poisson distribution','can be viewed as arising from','the binomial distribution',modal='possible')
q('The Poisson distribution','can be viewed as arising from','the exponential density',modal='possible')
q('the average rate, i.e., the average number of occurrences per minute','is','a constant',cond='we must assume',modal='required')
q('the number of occurrences in two non-overlapping time intervals','are','independent',cond='Our next assumption')
q('the events that there are j calls between 5:00 and 5:15 P.M. and k calls between 6:00 and 6:15 P.M. on the same day','are','independent',cond='In our example')
q('we','can assume','that two or more occurrences happen in one subinterval with a probability which is negligible in comparison with the probability of at most one occurrence',cond='If the subintervals are sufficiently short',modal='possible')
q('the Poisson distribution','is used as','an approximation to the binomial distribution',cond='when the parameters n and p are large and small, respectively')
q('the Poisson distribution','also arises in','situations where it may not be easy to interpret or measure the parameters n and p')
q('the exact probability distribution forS100','would be obtained by','consideringS100as a result of 100 Bernoulli trials withp= 1_/1000',cond='Assume that he is setting a book with 100 words to a page',modal='hypothetical')
q('we','can regard','the number of hits that your square receives as the number ofsuccessesin a Bernoulli trials process withn=400 andp=1_/100',cond='Since there are 400 bombs',modal='possible')
q('We','can think of','Xas binomially distributed with each white blood cell in the body representing a trial',cond='Suppose that in a certain fixed amountAof blood, the average human has 40 white blood cells',modal='possible')
q('the trial corresponding to that blood cell','was','a success',cond='If a given white blood cell turns up in the sample')
q('p','should be taken as','the ratio ofAto the total amount of blood in the individual',cond='Suppose that in a certain fixed amountAof blood, the average human has 40 white blood cells',modal='required')
q('n','will be','the number of white blood cells in the individual',cond='Suppose that in a certain fixed amountAof blood, the average human has 40 white blood cells')
q('we','can think of','Xas being Poisson distributed, with parameter\\lambda=40',cond='for the average human, we then have 40 =np',modal='possible')
q('it','is easier to model','the situation using the Poisson distribution than the binomial distribution',cond='In this case')
# Stated counts, probabilities and example parameters. No corrected fused spellings.
M(L('each integer between 1 andn'),L('probability',within='takes on as a value each integer between 1 andnwith probability 1_/n_'),L('1_/n_',1),condition=L('If the sample spaceSis of sizen, where0<n<\\infty'))
M(L('n',within='Whennis relatively large (say at least 30)'),L('relatively large'),L('30'),'bound',comparator=L('at least'))
M(L('the most probable\nvalue for T'),L('value for T'),L('1',within='the most probable\nvalue for T is 1'),'stated_value',condition=L('In both cases'))
M(L('a sequence of random numbers in [0_,_ 1)'),L('steps'),L('1_/p_'),'mean',condition=L('for small values of p'),cue=L('on the average'))
M(L('a customer arrives'),L('probability',within='The probability that a customer arrives ispand that no customer arrives isq= 1 -p'),L('p',within='ispand'))
M(L('no customer arrives'),L('probability',within='The probability that a customer arrives ispand that no customer arrives isq= 1 -p'),L('q= 1 -p'),condition=L('suppose a line of customers waits for service at a counter'))
M(L('The distribution',within='The distribution for the number of tosses isu(x,2,p)'),L('number of tosses',within='The distribution for the number of tosses isu(x,2,p)'),L('u(x,2,p)'),condition=L('A fair coin is tossed until the second time a head turns up'))
M(L('distribution',within='In Figure 5.2 we give a graph of the distribution fork=2 andp=_._25.'),L('k',within='fork=2'),L('2',within='fork=2'),condition=L('In Figure 5.2'))
M(L('distribution',within='In Figure 5.2 we give a graph of the distribution fork=2 andp=_._25.'),L('p',within='andp=_._25'),L('_._25'),condition=L('In Figure 5.2'))
M(L('occurrences',within='in a given 5-minute time interval, we would expect about 5λ occurrences'),L('expect'),L('5λ'),'mean',condition=L('in a given 5-minute time interval'),uncertainty=L('about',within='we would expect about 5λ occurrences'))
M(L('A typesetter'),L('mistake'),L('one'),'mean',unit=L('per 1000 words'),condition=L('A typesetter makes, on the average, one mistake per 1000 words'),cue=L('on the average',within='A typesetter makes, on the average, one mistake per 1000 words'))
M(L('a book'),L('words to a page'),L('100',within='with 100 words to a page'),'count',condition=L('Assume that he is setting a book with 100 words to a page'))
M(L('S100',within='The expected value of S100is\\lambda=100(1/1000)=.1'),L('expected value'),A('#/texts/421','.1'),'mean',condition=L('Assume that he is setting a book with 100 words to a page'))
M(L('a particular bomb will hit your square'),L('probability',within='a particular bomb will hit your square with probability 1/100'),L('1/100',within='a particular bomb will hit your square with probability 1/100'),condition=L('We assume that a particular bomb will hit your square with probability 1/100'))
M(L('bombs',within='Since there are 400 bombs'),L('there are',within='Since there are 400 bombs'),L('400',within='Since there are 400 bombs'),'count',condition=L('Assume that you live in a district of size 10 blocks by 10 blocks so that the total district is divided into 100 small squares'))
M(L('the Poisson distribution',within='Thus we can use the Poisson distribution with\\lambda=400\\cdot1/100 = 4'),L('\\lambda',within='with\\lambda=400\\cdot1/100 = 4'),L('4',within=' = 4 to approximate'),condition=L('Since there are 400 bombs'))
M(L('The expected number of squares that receive exactlyjhits'),L('expected number'),A('#/texts/79'),'mean',condition=L('Since there are 400 bombs'))
M(L('cookies',within='enough cookie dough for 500 cookies'),L('enough cookie dough'),L('500',within='enough cookie dough for 500 cookies'),'count',condition=L('We assume that we have made enough cookie dough for 500 cookies'))
M(L('raisins',within='We put 600 raisins in the dough'),L('put',within='We put 600 raisins in the dough'),L('600',within='We put 600 raisins in the dough'),'count',condition=L('We assume that we have made enough cookie dough for 500 cookies'))
M(L('the average human'),L('white blood cells'),L('40',within='the average human has 40 white blood cells'),'mean',condition=L('Suppose that in a certain fixed amountAof blood, the average human has 40 white blood cells'))
M(L('Xas being Poisson distributed'),L('parameter',within='Xas being Poisson distributed, with parameter\\lambda=40'),L('40',within='parameter\\lambda=40'),condition=L('for the average human, we then have 40 =np'))
# Formula occurrences with explicit local declarations. Parameter letters without meanings remain unbound.
F('#/texts/5',[('n',L('sample spaceSis of sizen'))])
F('#/texts/255',[('n',L('sample spaceSis of sizen'))])
F('#/texts/257',[('m',L('distribution functionm(\\omega)'))])
F('#/texts/259',[('S',L('sample spaceSis'))])
F('#/texts/267',[('x',L('the greatest integer not exceedingx'))])
F('#/texts/271',[('\\omega_1',L('possible outcomes of the experiment'))])
F('#/texts/309')
for ptr in ['#/texts/326','#/texts/328']:F(ptr)
F('#/texts/332',[('Y',L('a normal random variable with these parameters'))])
F('#/texts/334',[('Y',L('a normal random variable with these parameters'))])
for ptr in ['#/texts/357','#/texts/359']:
 F(ptr,[('T',L('the number of trials up to and including the first success'))],assumption=L('Consider a Bernoulli trials process continued for an infinite number of trials'))
F('#/texts/360',assumption=L('whereq=1-p'))
for ptr in ['#/texts/276','#/texts/283','#/texts/290']:F(ptr)
F('#/texts/293',[('Y',L('the smallest integer satisfying the inequality'))])
F('#/texts/296',[('Y',L('the smallest integer satisfying the inequality'))])
for ptr in ['#/texts/124','#/texts/137']:F(ptr,[('Y',L('the smallest integer satisfying the inequality'))])
F('#/texts/127')
F('#/texts/155',[('T',L('the timeTuntil the next arrival'))],assumption=L('suppose a line of customers waits for service at a counter'))
F('#/texts/169',[('T',L('the length of time required to service a customer'))],assumption=L('the length of time required to service a customer also has a geometric distribution but with a different value forp'))
for ptr in ['#/texts/20','#/texts/204','#/texts/205','#/texts/206','#/texts/217']:
 F(ptr,[('k',L('a positive integerk'))] if 'k' in NI[ptr]['text'] else None,assumption=L('Suppose we are given a coin which has probabilitypof coming up heads when it is tossed'))
F('#/texts/229',assumption=L('A fair coin is tossed until the second time a head turns up'))
F('#/texts/365',[('\\lambda',L('the average rate, i.e., the average number of occurrences per minute'))])
F('#/texts/373',[('\\lambda',L('the average rate, i.e., the average number of occurrences per minute')),('t',L('a time interval of lengtht')),('n',L('nsu bintervals'))] if False else [('\\lambda',L('the average rate, i.e., the average number of occurrences per minute')),('t',L('a time interval of lengtht')),('n',L('nsubintervals'))])
F('#/texts/374',[('p',L('the probability of an occurrence in a given subinterval')),('\\lambda',L('the average rate, i.e., the average number of occurrences per minute')),('t',L('a time interval of lengtht')),('n',L('nsubintervals'))])
for ptr in ['#/texts/383','#/texts/401','#/texts/403']:
 F(ptr,[('X',L('which counts the number of occurrences in a given time interval')),('\\lambda',L('the average rate, i.e., the average number of occurrences per minute'))],assumption=L('we will assume that the time interval is of length 1'))
for ptr in ['#/texts/388','#/texts/392','#/texts/399']:F(ptr,[(r'\lambda',L('the average rate, i.e., the average number of occurrences per minute'))] if r'\lambda' in NI[ptr]['text'] else [('λ',L('the average rate, i.e., the average number of occurrences per minute'))])
F('#/texts/421',[('\\lambda',L('The expected value of S100'))],assumption=L('Assume that he is setting a book with 100 words to a page'))
F('#/texts/430',assumption=L('Assume that he is setting a book with 100 words to a page'))
F('#/texts/79',assumption=L('Since there are 400 bombs'))
# Incomplete token fragments retain their unsupported status; QED signs are page notation.
for ptr in ['#/texts/60','#/texts/62','#/texts/109']:
 limit('formula_context',[ptr],'Isolated recovered formula fragment has no complete expression or independently established local binding; do not join across native items to repair it.')
# Native Table 5.1. The blank stub header cannot be invented. Blank data cells remain unresolved.
ptr='#/tables/0';cells=NI[ptr]['data']['table_cells']
ps={p['cell_index']:p for p in V['projection']['pieces'] if p.get('item_ref')==ptr and 'cell_index' in p}
for idx,c in enumerate(cells):
 if c['column_header']:continue
 col=c['start_col_offset_idx'];row=c['start_row_offset_idx'];cellptr=f'{ptr}/data/table_cells/{idx}'
 if col==0:
  limit('table',[cellptr],'This non-header stub cell states the row label, but its column header is blank: required header_path is unavailable.')
  continue
 if not c['text']:
  limit('table',[cellptr],'Blank source cell has no stated legend assigning a value/state; not zero and not an absent reading.')
  continue
 # Header text may consist of genuine referenced native pieces; gather cell-index membership.
 def table_lit(i):
  pp=[p for p in V['projection']['pieces'] if p.get('cell_index')==i and (p.get('item_ref')==ptr or p.get('item_ref') in NI and NI[p['item_ref']].get('parent',{}).get('$ref','').startswith('#/groups/'))]
  # cell_index is globally attached only while this table is visited in this unit.
  pp=[p for p in V['projection']['pieces'] if p.get('cell_index')==i and p.get('source_field') in ['text','cell_text']]
  return ('literal',[(p['start'],p['end']) for p in pp])
 record('table',table=native(ptr),cell=native(cellptr),row_label=table_lit(row*7),header_path=table_lit(col),cell_value=table_lit(idx),caption=L('Table 5.1: Poisson approximation to the binomial distribution.'),unit=absent('No applicable unit is stated for these probability cells.'),note=absent('No table note is stated.'))

# Second census sweep of explicit inline expressions and conditions.
def E(expression,assumption=None):
 return record('formula_context',formula=L(expression),scope=native(V['section_pointer']),symbol=absent('This explicit inline occurrence supplies no separate local symbol-to-meaning declaration.'),meaning=absent('No explicit local symbol meaning for this inline occurrence.'),domain=absent(),assumption=L(assumption) if assumption else absent())
unit(2)
q('each of them','is assigned','the same probability',cond='sequences of length x with these properties')
q('there','were','exactlyk-1 heads thrown in the firstx-1 tosses',cond='IfX=x',quant='exactlyk-1')
q('a head','must have been thrown','on the _x_th toss',cond='IfX=x',modal='required')
q('the distribution','is','quite asymmetric, with a long tail reflecting the fact that large values ofxare possible',scope='In Figure 5.2')
q('there','should be','npoccurrences',cond='If this time interval is divided intonsubintervals',modal='required')
q('the sequence of subintervals','can be thought of as','a sequence of Bernoulli trials, with a success corresponding to an occurrence in the subinterval',cond='we are assuming that there is either 0 or 1 occurrence',modal='possible')
q('a good way','is','to take advantage of the relationship between the Poisson distribution and the exponential density',cond='To simulate a Poisson random variable on a computer')
q('The exact probability that S100=j','is','b(100,1/1000, j_)',cond='Assume that he is setting a book with 100 words to a page')
q('The observed frequencies','are shown as','squares',scope='In Figure 5.3')
q('the predicted frequencies','are shown as','dots',scope='In Figure 5.3')
for prop,val in [('p','.5'),('p','.2')]:
 start=T.index('for the cases p = .5 and p = .2');j=T.index(val,start)
 M(L('this distribution',within='we have plotted this distribution using'),L((j-len('p = '),j-3)) if False else L('p',within='p = '+val),L((j,j+len(val))),condition=L('In Figure 5.1'))
M(L('This method'),L('calls to a random number generator'),L('n',within='ncalls to a random number generator'),'count')
M(L('a particular bomb will hit your square'),L('probability',within='a particular bomb will hit your square with probability 1/100'),L('1/100',within='a particular bomb will hit your square with probability 1/100'),condition=L('We assume that a particular bomb will hit your square with probability 1/100'))
# Duplicate same occurrence is intentionally not another denominator member.
RECORDS[2].pop();SPECS[2].pop()
for expr,condition in [('q=1-p','Consider a Bernoulli trials process continued for an infinite number of trials'),('q = 1 −p','if 0< p <1'),('p(j)=e-44j/j!','Since there are 400 bombs'),('40 =np','for the average human'),('\\lambda=40','for the average human'),('p= 1_/1000','Assume that he is setting a book with 100 words to a page')]:E(expr,condition)
# Literal formulas already have binding records above; do not generate an additional formula-only member.
unit(7)
q('joint, marginal, and conditional pdfs (or pfs)','satisfy',A('#/texts/74'),scope='The composition property')
q('f (y|x)','=',L('f (y)',within='then f (y|x) = f (y) and f (x|y) = f (x)'),cond='if X and Y are independent')
q('f (x|y)','=',L('f (x)',within='then f (y|x) = f (y) and f (x|y) = f (x)'),cond='if X and Y are independent')
E('f (y|x) = f (y)','if X and Y are independent');E('f (x|y) = f (x)','if X and Y are independent')
unit(9)
q('The relationships between the associated functions of X and Y on the one hand and of ψ(X, Y) on the other','are not','generally straightforward',neg=True)
q('The relationships between the associated functions of X and Y on the one hand and of ψ(X, Y) on the other','must be derived','by analysis of the joint distribution of the variates in question',modal='required')
E('Z = X+Y','when X and Y are independent');E('CX+Y (t) = CX(t)CY (t)','when X and Y are independent')
unit(10)
M(A('#/texts/19','This plot'),A('#/texts/19','random numbers'),A('#/texts/19','10,000'),'count',condition=A('#/texts/19','generated from a normal, an exponential, a Cauchy, and a lognormal distribution'))
q('The uniform random numbers case study','compares','the performance of several different location estimators for a particular non-normal distribution')
# Preserve both explicit percentile endpoints as a single stated range; the source supplies no normalized probability.
M(L('Mid-Mean'),L('data'),L('between the 25th and 75th percentiles'),'bound')
M(L('Trimmed Mean'),L('data',within='calculate the mean for data between the 5th and 95th percentiles'),L('between the 5th and 95th percentiles'),'bound',condition=L('A common choice'))
unit(11)
d('Ȳ','Ȳ is the sample mean',cue='is the')
d('s', 's is the sample standard deviation',cue='is the')
d('N','N is the sample size',cue='is the')
d('α','α is the\ndesired significance level',cue='is the')
d('t1-α/2, N-1','t1-α/2, N-1 is the 100(1-α/2) percentile of the t distribution with\nN - 1 degrees of freedom',cue='is the')
D(L('Confidence limits',within='Confidence limits are defined as:'),pieces(L('Confidence limits are defined as:'),A('#/texts/111')),cue=L('are defined as'))
limit('assertion',['#/texts/92'],'Critical-region imperative has no explicit subject-predicate-object clause in the released required literal-role shape. Threshold retained as a formula reading.')
M(L('the confidence coefficient'),L('confidence coefficient'),L('1 - α'))
M(L('the width of the interval'),L('controlled by'),L('two'),'count',condition=L('From the formula'))
# Confidence coefficients explicitly stated as commonly used choices.
for val in ['90 %','95 %','99 %']:
 M(A('#/texts/106','confidence coefficient'),A('#/texts/106','intervals'),A('#/texts/106',val),condition=A('#/texts/106','in practice'))
for expr in ['T = 2611.284','ν = 194','α = 0.05','t1-α/2,ν = 1.9723','|T| > 1.9723','H0: μ = 5','Ha: μ ≠ 5','t1-α,v = 1.6527']:
 E(expr,'ZARR13.DAT data set')

# Explicit numeric qualifications are also numeric property/value occurrences.
unit(11)
for ptr in ['#/texts/137','#/texts/87']:
 M(A(ptr,'ZARR13.DAT data set'),A(ptr,'confidence interval'),A(ptr,'95 %'),condition=A(ptr,'two-sided confidence interval'))
M(A('#/texts/90','population mean'),A('#/texts/90','equal to'),A('#/texts/90','5'),condition=A('#/texts/90','null hypothesis'))
M(A('#/texts/91','H0'),A('#/texts/91','μ'),A('#/texts/91','5'),condition=L('two-sided, one-sample t-test'))
M(A('#/texts/92','|T|'),A('#/texts/92','Critical region'),A('#/texts/92','1.9723'),'bound',comparator=A('#/texts/92','>'),condition=L('two-sided, one-sample t-test'))
unit(4)
M(L('the joint range',within='the joint range is ℜX,Y ='),L('joint range',within='the joint range is ℜX,Y ='),L('{(0, 0) , (1, 0) , (2, 0) , (0, 1) , (1, 1) , (1, 2)}'),condition=L('Consider the discrete bivariate (X, Y)'))
M(L('the joint probability domain',within='In this case the joint probability domain is'),L('joint probability domain',within='In this case the joint probability domain is'),L('{ 1 8 , 1 4 , 1 2 , 3 4 , 11 16 , 1}'),condition=L('Consider the discrete bivariate (X, Y)'))
unit(5)
for ref,prop,value in [('The corresponding marginal domain for X','marginal domain','{0, 1, 2}'),('marginal probability domain ℜ α X','marginal probability domain','{1/4, 3/4, 1}'),('The corresponding marginal domain for Y','marginal domain','{0, 1}'),('marginal probability domain ℜ α Y','marginal probability domain','{11/16, 1}')]:
 M(L(ref),L(prop,within=ref),L(value),condition=L('Continuing Example 4.1.1'))

# Exact frozen-source census: every selected item and every non-representable chart piece.
for n in range(1,12):
 unit(n)
 census_path=next(FREEZE.glob(f'origin-*/unit-{n}.json')).parent/'source-census.json'
 census=json.loads(census_path.read_text())
 sourceunit=next(u for u in census['units'] if u['source_view_id']==V['id'])
 unsupported=sourceunit['unsupported_record_projection_pieces']
 for pointer in sorted({p['item_ref'] for p in unsupported}):
  pp=[p for p in unsupported if p['item_ref']==pointer]
  LIMITS[n].append(dict(family=['measurement','table','formula_context'],pointers=[pointer],reason='Frozen census supplies chart text but no exact released chart record-anchor scope. Chart values, labels and title were inspected in native source context; no table/cell addresses or exact scopes are invented.',disposition='unsupported_coordinate_routing',source_projection_pieces=pp))
 # Empty native items are explicitly retained, independently of prediction output.

if __name__=='__main__':
 coverage=dict(protocol='independent-source-census-B-v3',actor='gpt-6.1-sol-high-B-v3',guideline='statistics-m1-reference-3',release_id=UNITS[1]['release_id'],families=list(FAMILIES),inspection='Every native item and every projected source piece of all 11 frozen units was inspected. Source readings do not establish scientific truth.',units=[])
 for n in range(1,12):
  unit(n);rs=RECORDS[n]
  counts=dict(collections.Counter(r['family'] for r in rs))
  payload=dict(protocol='source-record-reference-1',release_id=UNITS[n]['release_id'],unit_ref=UNITS[n]['unit_ref'],guideline='statistics-m1-reference-3',reference_policy_version='statistics-reference-reading-3',prediction_policy_version='m1-grouped-reading-logistic-1',reason='Independent source-only B reading of all native items in this frozen unit; explicit unsupported/unresolved regions retained separately in coverage.json. No production predictions read.',records=rs)
  (ROOT/f'unit-{n}.json').write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n')
  itemrows=[]
  for ptr,item in NI.items():
   anchored={family:[r['record_id'] for r in rs if r['family']==family and any(a['pointer']==ptr or a['pointer'].startswith(ptr+'/') for a in r['anchors'] if a['space']=='selected_projection')] for family in FAMILIES}
   lim=[i for i,l in enumerate(LIMITS[n]) if ptr in l['pointers']]
   text=item.get('text')
   if ptr.startswith('#/pictures/'):
    disposition='unsupported_chart_or_visual_region' if any(p.get('item_ref')==ptr and p.get('source_field','').startswith('chart_') for p in V['projection']['pieces']) else 'visual_item_without_supported_literal_reading'
   elif lim:disposition='limitation_retained'
   elif any(anchored.values()):disposition='source_readings_authored'
   elif text=='':disposition='genuinely_empty_native_text'
   elif ptr.startswith('#/groups/'):disposition='native_structure_and_local_context_inspected'
   elif ptr.startswith('#/tables/'):disposition='native_cells_inspected_see_cell_readings_and_limitations'
   elif item.get('label') in ['section_header','page_header','page_footer','caption'] or (text and (text.startswith('Example ') or text.startswith('EXAMPLE ') or text in ['\\sqcap\\sqcup','and','then','so'])):disposition='heading_caption_or_furniture_not_an_independent_reading'
   elif text and len(text)<70:disposition='inspected_fragment_or_scope_context_not_a_separate_complete_reading'
   else:disposition='inspected_context_or_expository_transition_see_readings_and_limits'
   itemrows.append(dict(pointer=ptr,label=item.get('label'),disposition=disposition,source_text=text,source_item_sha256=hashlib.sha256(json.dumps(item,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),families_inspected=list(FAMILIES),record_ids_by_family=anchored,limitation_indexes=lim))
  coverage['units'].append(dict(unit_id=n,unit_ref=UNITS[n]['unit_ref'],section_pointer=V['section_pointer'],source_view_id=V['id'],projection_characters=len(T),native_items_inspected=len(NI),native_projection_items=V['projection']['items'],projected_pieces_inspected=V['projection']['pieces'],family_counts={f:counts.get(f,0) for f in FAMILIES},regions=itemrows,limitations=LIMITS[n],empty_unit_reason='Selected source is a title/heading only, with no eligible source-reading occurrence in any of the five families.' if n in [1,3] else None))
 (ROOT/'coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
 (ROOT/'authored-selections.json').write_text(json.dumps(SPECS,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
 inputs={}
 allowed=[FREEZE/'manifest.json',FREEZE/'guideline.md',FREEZE/'authored-schema.json',FREEZE/'record-contract.json',*sorted((FREEZE/'family-schemas').glob('*.json')),*sorted(FREEZE.glob('origin-*/source-census.json')),*sorted(FREEZE.glob('origin-*/set-manifest.json')),*sorted(FREEZE.glob('origin-*/frozen-sampling.json')),*sorted(FREEZE.glob('origin-*/unit-*.json'))]
 for f in allowed:inputs[str(f.relative_to(FREEZE))]=hashlib.sha256(f.read_bytes()).hexdigest()
 outputs={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [*sorted(ROOT.glob('unit-*.json')),ROOT/'coverage.json',ROOT/'authored-selections.json',ROOT/'author.py',ROOT/'validate.py']}
 manifest=dict(actor='gpt-6.1-sol-high-B-v3',session_name='/root/m1_reference_b_v3',model='gpt-6.1-sol',effort='high',date='2026-11-04',identity_basis='Operator-selected model/effort and delegated session name; no platform execution ID is claimed.',release_id=UNITS[1]['release_id'],guideline='statistics-m1-reference-3',input_sha256=inputs,output_sha256=outputs,source_only_access_note='An initial metadata discovery loop additionally read origin-*/frozen-sampling.json source-only sampling/frame metadata. Coordinator confirmed these are allowed source-only metadata; no predictions or author A/C output read.',production_prediction_access='not_run',model_provider_pdf_ocr_calls='not_run',registration='not_run: root coordinator owns protected registration',counts_by_unit={n:dict(collections.Counter(r['family'] for r in RECORDS[n])) for n in range(1,12)},counts_total=dict(collections.Counter(r['family'] for rs in RECORDS.values() for r in rs)))
 (ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
 print(json.dumps(manifest['counts_by_unit'],sort_keys=True));print(json.dumps(manifest['counts_total'],sort_keys=True))
