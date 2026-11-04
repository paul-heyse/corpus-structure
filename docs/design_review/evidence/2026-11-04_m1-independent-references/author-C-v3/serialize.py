"""C's source-only adjudication serialization. No production prediction imports or reads.

Inputs are the protected C packets (exact native source, exact A/B author bytes).
Choices and repairs below are C's source readings; identity functions only are shared.
"""
import copy, hashlib, json, pathlib, collections
from corpus_structure.semantic.record_contracts import anchor_identity, evidence_set_identity, record_identity, interpretation_identity
ROOT=pathlib.Path(__file__).resolve().parent.parent
OUT=pathlib.Path(__file__).resolve().parent
RELEASE='release:bc69d3be658e27e079ae61d4c4fa2051eabf006326b80443f2d28a9e8662b5bd'
FAMILIES=['definition','assertion','measurement','table','formula_context']
PACKETS={i:json.loads((ROOT/f'adjudication-inputs-002/unit-{i}.json').read_text()) for i in range(1,12)}
BATCHES={i:[json.loads(a['authored_utf8']) for a in p['authors']]for i,p in PACKETS.items()}
OUTPUT={i:[]for i in PACKETS};LIMITS={i:[]for i in PACKETS};DECISIONS={i:[]for i in PACKETS}
COV_A={u['unit_id']:u for u in json.loads((ROOT/'author-A-v3/coverage.json').read_text())['units']}
COV_B={u['unit_id']:u for u in json.loads((ROOT/'author-B-v3/coverage.json').read_text())['units']}

def field(r,role):return next(f for f in r['fields']if f['role']==role)
def value(r,role):
 f=field(r,role);v=f.get('value',{});return v.get('text',v.get('items',v.get('label',v.get('pointer',f['state']))))
def ptr(r,role):
 f=field(r,role);es={s['set_id']:s for s in r['evidence_sets']};an={a['anchor_id']:a for a in r['anchors']}
 return [an[z]['pointer']for sid in f.get('evidence_sets',[])for z in es[sid]['anchors']]
def frame(i):return PACKETS[i]['source']['source_frame']['evaluation_frame']
def native(i):return PACKETS[i]['source']['native_contexts'][0]['native_items']
def section(i):return PACKETS[i]['source']['source_frame']['source_views'][0]['section_pointer']
def projection(i):return PACKETS[i]['source']['source_frame']['source_views'][0]['projection']
def note(i,reason,**kwargs):DECISIONS[i].append({'reason':reason,**kwargs})
def limit(i,pointers,family,reason,**kwargs):
 if isinstance(pointers,str):pointers=[pointers]
 LIMITS[i].append({'pointers':pointers,'family':family,'disposition':'eligible_unrepresentable_or_unresolved','reason':reason,**kwargs})
def loc(i,p,text=None,occ=0):
 if isinstance(p,int):p=f'#/texts/{p}'
 proj=projection(i);pieces=[x for x in proj['pieces']if x.get('item_ref')==p]
 if '/data/table_cells/'in p:
  base,n=p.split('/data/table_cells/');pieces=[x for x in proj['pieces']if x.get('item_ref')==base and x.get('cell_index')==int(n)]
 if text is None:
  assert len(pieces)==1,(i,p,pieces)
  text=proj['text'][pieces[0]['start']:pieces[0]['end']]
 matches=[]
 for piece in pieces:
  s=proj['text'][piece['start']:piece['end']];pos=0
  while True:
   at=s.find(text,pos)
   if at<0:break
   matches.append((piece['start']+at,piece['start']+at+len(text)));pos=at+1
 assert matches,(i,p,text)
 start,end=matches[occ]
 a={'pin':frame(i)['pin'],'space':'selected_projection','pointer':p,'precision':'exact','start':start,'end':end,'source_piece':text}
 a['anchor_id']=anchor_identity(a);return a

def native_anchor(i,p):
 a={'pin':frame(i)['pin'],'space':'native','pointer':p,'precision':'item'};a['anchor_id']=anchor_identity(a);return a

def selection(i,author,index):
 r=copy.deepcopy(BATCHES[i]['AB'.index(author)]['records'][index]);r['_origin']={'author':author,'index':index,'record_id':r['record_id']};return r

def add(i,r):OUTPUT[i].append(r);return r

def pick(i,author,indices):return [add(i,selection(i,author,k))for k in indices]

def put(i,r,role,anchors,*,state='present',label=None,reason=None,kind=None):
 f=copy.deepcopy(field(r,role));kind=kind or f['kind'];f={k:v for k,v in f.items()if k in ['role','meaning_changing']}
 f.update(kind=kind,state=state,evidence_status='available')
 if state=='present':
  if kind=='classified':
   vk={'polarity':'assertion_polarity','modality':'assertion_modality','relation_type':'definition_relation','value_role':'measurement_value_role'}[role]
   f['value']={'kind':vk,'label':label};f['policy']='statistics-m1-reference-3';usage='classification_cue'
  elif kind=='native':f['value']={'kind':'native_location','pointer':anchors[0]['pointer']};usage='native'
  else:
   texts=[a['source_piece']for a in anchors];usage='literal'
   if len(texts)==1:f['original']=texts[0];f['value']={'kind':'text','text':texts[0]}
   else:f['original_pieces']=texts;f['value']={'kind':'text_sequence','items':texts}
 else:
  usage='context';f['reason']=reason or f'Inspected the local source clause and selected section for {role}; no explicit {role} is stated for this reading.'
 es={'role':role,'ordering':'ordered','usage':usage,'anchors':[a['anchor_id']for a in anchors]};es['set_id']=evidence_set_identity(es);f['evidence_sets']=[es['set_id']]
 r['fields']=[f if x['role']==role else x for x in r['fields']]
 r['anchors'].extend(a for a in anchors if a['anchor_id']not in {x['anchor_id']for x in r['anchors']})
 r['evidence_sets']=[x for x in r['evidence_sets']if x['role']!=role]+[es]
 return r

def lit(i,r,role,p,text=None,occ=0):return put(i,r,role,[loc(i,p,text,occ)])
def seq(i,r,role,parts):return put(i,r,role,[loc(i,*part)if isinstance(part,tuple)else loc(i,part)for part in parts])
def absent(i,r,role,reason=None,state='unstated'):return put(i,r,role,[native_anchor(i,section(i))],state=state,reason=reason)
def cls(i,r,role,label,p,text,occ=0):return put(i,r,role,[loc(i,p,text,occ)],label=label)
def get_anchors(r,role):
 sets={x['set_id']:x for x in r['evidence_sets']};anchors={x['anchor_id']:x for x in r['anchors']}
 return [anchors[z]for sid in field(r,role).get('evidence_sets',[])for z in sets[sid]['anchors']]
def copy_role(i,r,role,other):
 f=field(other,role)
 return put(i,r,role,get_anchors(other,role),state=f['state'],label=f.get('value',{}).get('label'),reason=f.get('reason'),kind=f['kind'])

def finalize(i,r):
 r=copy.deepcopy(r);r.pop('_origin',None)
 # Remove orphaned evidence and anchor objects after C's role repairs.
 used_sets={z for f in r['fields']for z in f.get('evidence_sets',[])}
 r['evidence_sets']=[s for s in r['evidence_sets']if s['set_id']in used_sets]
 role_primary={'definition':['term','defining_text'],'assertion':['subject','predicate','object'],'measurement':['referent','property','original_value'],'table':['table','cell'],'formula_context':['formula']}
 roles=role_primary[r['family']]
 if r['family']=='formula_context'and field(r,'symbol')['state']=='present':roles=roles+['symbol']
 r['occurrence_anchors']=list(dict.fromkeys(a['anchor_id']for role in roles for a in get_anchors(r,role)))
 used={z for s in r['evidence_sets']for z in s['anchors']}|set(r['occurrence_anchors'])
 r['anchors']=[a for a in r['anchors']if a['anchor_id']in used]
 r['record_id']=record_identity(RELEASE,r);r['interpretation_id']=interpretation_identity(r)
 return r

# Initial per-unit source-reviewed selections. Formula decisions are independent below.
for i in PACKETS:
 for n,r in enumerate(BATCHES[i][1]['records']):
  if r['family']!='formula_context':add(i,selection(i,'B',n))

# Definitions whose complete source meaning was omitted or shortened in either reading.
r=OUTPUT[2][0];seq(2,r,'defining_text',[(246,'In Chapter 1, we saw that in many cases, we assume that all outcomes of an experiment are equally likely.'),247,248,249,(250,'is uniformly distributed')])
r=OUTPUT[2][5];seq(2,r,'defining_text',[177,178,179,180,181,(183,'let'),184,(185,'represent the number of tosses.'),(189,'For a general'),190,191,192,(193,'has a negative binomial distribution')])
pick(2,'A',[218,219,220,221,222])
# Author A's extra explicit example parameters/counts have genuine source roles.
pick(2,'A',[13,14,15,202,203,204,205,207])
# Service-memoryless statement and further explicit local propositions omitted by B.
pick(2,'A',[34,223,224,226,227])
# The conjunction has two distinct clauses, not two alternative source meanings.
# All these retain their hypothetical / assumed context in their literal conditions.
for r in OUTPUT[2]:
 if r['family']=='assertion'and r.get('_origin',{}).get('author')=='A':
  n=r['_origin']['index'];pol='negative'if n==223 else 'positive'
  if n==223:cls(2,r,'polarity',pol,104,'neither');cls(2,r,'modality','asserted',104,'is')
  elif n==224:cls(2,r,'polarity',pol,104,'is');cls(2,r,'modality','probable',104,'presumably')
  elif n==34:cls(2,r,'polarity',pol,173,'is independent of');cls(2,r,'modality','asserted',173,'is independent of')
  elif n==226:cls(2,r,'polarity',pol,220,'is');cls(2,r,'modality','asserted',220,'is')
  elif n==227:cls(2,r,'polarity',pol,21,'is assigned');cls(2,r,'modality','asserted',21,'is assigned')
# Hypothetical queue arrivals cannot acquire a bare unconditional probability.
r=next(r for r in OUTPUT[2]if r.get('_origin')=={'author':'B','index':54,'record_id':r['record_id']});lit(2,r,'condition',140,'suppose a line of customers waits for service at a counter')
# This is source approximation, not unqualified equality.
for r in OUTPUT[2]:
 if r.get('_origin',{}).get('author')=='B'and r['_origin']['index']==17:
  cls(2,r,'modality','asserted',325,'is well-approximated by')
# Full literal defining clauses, including the setup that makes a named symbol meaningful.
for n in [1,3,4,5]:
 r=next(r for r in OUTPUT[4]if r.get('_origin',{}).get('index')==n)
 a=selection(4,'A',n)
 copy_role(4,r,'term',a);copy_role(4,r,'defining_text',a)
r=next(r for r in OUTPUT[4]if r.get('_origin',{}).get('index')==7)
seq(4,r,'defining_text',[(16,'Let α ∈ [0, 1] and let ℜ α X,Y be the set of all values (of probability) that Pr[X ≤ x, Y ≤ y] can take.'),(16,'Analogous to the univariate case, ℜ α X,Y is called the joint probability domain of the bivariate (X, Y)')])
r=next(r for r in OUTPUT[4]if r.get('_origin',{}).get('index')==10);lit(4,r,'defining_text',29,'A discrete bivariate (X, Y ) takes discrete values (x, y) with finite probabilities f (x, y). In this case f (x, y) is the bivariate probability function (joint pf)')
# Required source qualifications stay in assertion fields, not inferred default scope.
r=next(r for r in OUTPUT[4]if r.get('_origin',{}).get('index')==17);lit(4,r,'condition',22,'When (X, Y) have a jointly continuous probability domain')
# Marginal consistency is a distinct clause; B's inverted are/Corresponding reading loses it.
OUTPUT[5]=[r for r in OUTPUT[5]if r.get('_origin',{}).get('index')!=3]
r=add(5,selection(5,'A',3));cls(5,r,'polarity','positive',37,'consistent with');absent(5,r,'modality','The subordinate with-clause states consistency but has no finite asserted/modal verb of its own.');lit(5,r,'quantification',37,'each one')
# Source lacks the missing first product object in the displaced independence sentence.
OUTPUT[6]=[r for r in OUTPUT[6]if r.get('_origin',{}).get('index')!=1]
limit(6,['#/texts/52','#/texts/53'],'assertion','The continuous joint-pdf product clause is interrupted by displaced "The marginal pf of Y is" text. Its intended complete literal object cannot be reconstructed.')
# Conditional probabilities definition needs its actual antecedent, not just "Such".
r=next(r for r in OUTPUT[7]if r.get('_origin',{}).get('index')==1);lit(7,r,'defining_text',57,'In this case, interest often focuses on computing probabilities associated with one variate given information about the realized value of the other variate. Such probabilities are called conditional probabilities')
r=add(7,selection(7,'A',5));cls(7,r,'polarity','positive',71,'satisfy');cls(7,r,'modality','asserted',71,'satisfy')
# Bayes source gives conditional pdf/pf alternatives, not one undeclared-symbol formula.
# Other Bayes literal scope, if present in A, is an explicitly quoted author scope.
for n in [1,2]:
 r=next(r for r in OUTPUT[8]if r.get('_origin',{}).get('index')==n);copy_role(8,r,'scope',selection(8,'A',n))
# Displaced example formula is not governed by the following summation prose.
for r in OUTPUT[9]:
 if r['family']=='measurement':absent(9,r,'condition','The displaced native probability formula is adjacent to general mapping prose, which does not supply a condition for this worked probability.')
# Two distinct nested consequences, with complete inherited condition (not duplicate long object).
OUTPUT[9]=[r for r in OUTPUT[9]if r.get('_origin',{}).get('index')!=0]
for n in [0,15]:
 r=add(9,selection(9,'A',n));cls(9,r,'polarity','positive',101,'is',3 if n==0 else 2);cls(9,r,'modality','asserted',101,'is',3 if n==0 else 2)
# Source-defined mode for continuous data is a distinct, nonadjacent literal definition.
pick(10,'A',[74,75])
r=OUTPUT[10][-1];cls(10,r,'polarity','positive',4,'is');cls(10,r,'modality','asserted',4,'is')
# Exact original-page overlap, not another 10,000-number observation.
OUTPUT[10]=[r for r in OUTPUT[10]if r.get('_origin',{}).get('index')!=79]
# Keep source determiners in the defined noun phrases.
for b,a in [(0,0),(3,1),(4,2)]:
 r=next(r for r in OUTPUT[10]if r.get('_origin',{}).get('author')=='B'and r['_origin']['index']==b);copy_role(10,r,'term',selection(10,'A',a))
# All stated mean/median/mode values retain their explicit generating sample.
for r in OUTPUT[10]:
 if r['family']=='measurement'and r.get('_origin',{}).get('author')=='B':
  n=r['_origin']['index']
  if n in [60,61,62]:parts=[(20,'a sample from a normal distribution')]
  elif n in [63,64,65]:parts=[(21,'a sample from an exponential distribution')]
  elif n in [66,67,68]:parts=[(154,'a sample from a lognormal distribution')]
  else:continue
  if n in [62,65,68]:parts.append((20 if n==62 else 21 if n==65 else 154,'the mode is computed as the midpoint of the histogram interval with the highest peak'))
  seq(10,r,'condition',parts)
# The explicit approximate extrema are bounds, not generic stated quantities.
for r in OUTPUT[10]:
 if r.get('_origin',{}).get('author')=='B'and r['_origin']['index']in [70,71]:
  cls(10,r,'value_role','bound',25,'minimum'if r['_origin']['index']==70 else 'maximum')
# Confidence-scope omissions and source inconsistencies stay visible.
pick(11,'A',[20,54])
r=OUTPUT[11][-2];cls(11,r,'polarity','positive',106,'are\noften used');cls(11,r,'modality','asserted',106,'are\noften used')
# A's standalone significance sentence invents the lost symbol; no acceptance.
limit(11,'#/texts/82','measurement','The phrase "The most commonly used value for is 0.05" loses the referent after "for". The heading does not restore the absent symbol or uniquely establish its literal referent/property pair.')
# Confidence record 49 separates approximate quantity from explicit long-run condition.
r=next(r for r in OUTPUT[11]if r.get('_origin',{}).get('author')=='B'and r['_origin']['index']==49)
lit(11,r,'original_value',110,'95 %',2);lit(11,r,'uncertainty',110,'about');seq(11,r,'condition',[(110,'for a 95 %\nconfidence interval, if many samples are collected and the confidence interval computed'),(110,'in\nthe long run')])
# A duplicate recovered interval setup overlaps the same original source line.
OUTPUT[11]=[r for r in OUTPUT[11]if r.get('_origin',{}).get('index')!=82]
# Explicit units in quoted percentages remain separately located, without numeric parsing.
for i,rs in OUTPUT.items():
 for r in rs:
  if r['family']!='measurement':continue
  ov=field(r,'original_value');aa=get_anchors(r,'original_value')
  if len(aa)==1 and '%'in aa[0].get('source_piece',''):
   a=aa[0];lit(i,r,'unit',a['pointer'],'%',projection(i)['text'][next(p['start']for p in projection(i)['pieces']if p.get('item_ref')==a['pointer']) :a['start']].count('%'))

# Source dispositions are recorded in the final writer, after formulas are authored below.

# C formula adjudication. Argument-bearing function tokens are retained literally;
# one symbol is never labelled with another overload's meaning.
pick(2,'A',[46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,73,74,75,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,101,102,103,104,105,106,107,108,109,110,111,113,114,115,117,215,216,217])
pick(2,'B',[71,72,101,102,106,110,112,114,115,116,117,118,219])
# A's q binding in negative-binomial simulation borrowed a different subsection.
OUTPUT[2]=[r for r in OUTPUT[2]if not(r.get('_origin',{}).get('author')=='A'and r['_origin']['index']in [217])]
# Use complete declared meanings and each source-local assumption.
for r in OUTPUT[2]:
 if r['family']!='formula_context':continue
 fp=ptr(r,'formula')[0];sym=value(r,'symbol')
 if fp in ['#/texts/124','#/texts/137','#/texts/293','#/texts/296']:
  seq(2,r,'assumption',[(285,'if 0'),286,(287,'1')])
 if fp=='#/texts/155':lit(2,r,'assumption',140,'suppose a line of customers waits for service at a counter')
 if fp=='#/texts/169':seq(2,r,'assumption',[(166,'It is often assumed that the length of time required to service a customer also has a geometric distribution but with a different value for'),167])
 if fp in ['#/texts/20','#/texts/204','#/texts/205','#/texts/206','#/texts/217']:
  seq(2,r,'assumption',[177,178,(179,'of coming up heads when it is tossed.')])
 if fp in ['#/texts/383','#/texts/401','#/texts/403']:
  lit(2,r,'assumption',380,'we will assume that the time interval is of length 1')
 if fp=='#/texts/79':lit(2,r,'assumption',52,'Since there are 400 bombs')
 if fp in ['#/texts/127','#/texts/267']:
  # Ceil/floor is the symbol being defined, not x with the operator's meaning.
  pass
 if fp=='#/texts/392'and sym=='q':
  # No local Poisson paragraph explicitly defines q: do not import a binomial q.
  limit(2,[fp,'#/texts/312'],'formula_context','The Poisson-ratio formula uses q without a local declaration. A borrows the earlier binomial q=1-p; the selected section does not merge equal symbol spellings across subsections.',symbol='q')
# Remove only the unsupported imported q binding; other located declared symbols remain.
OUTPUT[2]=[r for r in OUTPUT[2]if not(r['family']=='formula_context'and ptr(r,'formula')[0]=='#/texts/392'and value(r,'symbol')=='q')]
limit(2,'#/texts/326','formula_context','The native formula literal is "\\mu=\\np". The \\np control sequence does not expose separately located n and p variable tokens; no reconstruction to np or inference of a mean is made.')
# Formula templates are serialization shape only; all meanings below are source selections.
def new_formula(i,parts,symbol=None,meaning=None,domain=None,assumption=None):
 t=next((r for r in OUTPUT[i]if r['family']=='formula_context'),None)
 if t is None:
  t=copy.deepcopy(next(r for r in BATCHES[i][1]['records']if r['family']=='formula_context'))
 r=copy.deepcopy(t);r.pop('_origin',None);r['_origin']={'author':'C','source_authored':True}
 seq(i,r,'formula',parts);put(i,r,'scope',[native_anchor(i,section(i))],kind='native')
 for role,spec in [('symbol',symbol),('meaning',meaning),('domain',domain),('assumption',assumption)]:
  if spec is None:absent(i,r,role)
  elif isinstance(spec,list):seq(i,r,role,spec)
  else:lit(i,r,role,*spec)
 add(i,r);return r
# The sample-space outcomes are explicitly labelled, not an unbound formula.
for sym in ['\\omega_1','\\omega_2','\\omega_n']:
 new_formula(2,[271],(271,sym),(270,'the possible outcomes of the experiment'))
# A/B missed a locally explicit q assignment for the binomial formula.
for fp in [309,328]:
 new_formula(2,[fp],(fp,'q'),[(313,'1-'),314],assumption=[(306,'assuming that on any one toss, the probability that a head occurs is'),307]if fp==309 else [(323,'When'),324,(325,'is relatively large (say at least 30)')])
# Native formula and original local declaration are kept separately at the bomb example.
new_formula(2,[60],None,None,assumption=(52,'Since there are 400 bombs'))
limit(2,['#/texts/60','#/texts/61','#/texts/62','#/texts/63','#/texts/64','#/texts/65'],'formula_context','The recovered bomb parameter equation is split after "\\lambda=" into numeric fragments. The complete ordered literal is retained in the following full reading; \\lambda alone is not given the blood-example meaning.')
new_formula(2,[60,61,62,63,64,(65,'100 = 4')],(60,'\\lambda'),None,assumption=(52,'Since there are 400 bombs'))
# The two local quantities are declared explicitly by their source labels.
new_formula(2,[104,105],None,None,assumption=(104,'for the average human'))
# Missing declared X binding in the blood-example incomplete native formula.
new_formula(2,[109, (110,'40')],(109,'\\lambda'),(108,'parameter'),assumption=[90,91,(92,'of blood, the average human has 40 white blood cells.')])
# Unsupported macro spelling and malformed literal are not silently repaired.
limit(2,'#/texts/206','formula_context','The frozen formula contains \\p rather than an exact p token; k and x are separately locatable, but the p binding is not fabricated.',symbol='p')

# Joint-distribution formulas: pair declarations remain pairs; x and y are not each
# falsely called a whole bivariate quantile.
pick(4,'B',[21,24,25,26,27,28,29,30])
for r in OUTPUT[4]:
 if r['family']!='formula_context':continue
 fp=ptr(r,'formula')[0]
 if fp in ['#/texts/27']:
  lit(4,r,'assumption',22,'When (X, Y) have a jointly continuous probability domain')
for fp in [19,23,25,27,34]:
 new_formula(4,[fp],(fp,'\\left ( x , y \\right )' if fp==25 else '( x , y )'),(8,'a bivariate quantile of (X, Y)'),assumption=(22,'When (X, Y) have a jointly continuous probability domain')if fp in [23,25,27]else None)
for fp in [19,23,25,27,34]:
 for sym in ['X','Y']:
  # Only formulas which actually contain the explicitly named upper-case variate.
  if sym in native(4)[f'#/texts/{fp}']['text']:
   new_formula(4,[fp],(fp,sym),(4,'univariates'),assumption=(33,'Consider the discrete bivariate (X, Y)')if fp==34 else None)
# The declared probability-domain alpha is a domain-bound symbol; no invented meaning.
new_formula(4,[19],(19,'\\alpha'),None,(16,'[0, 1]'))
for cell in range(6):
 cp=f'#/tables/0/data/table_cells/{cell}'
 for sym in ['X','Y']:
  new_formula(4,[cp],(cp,sym),(4,'univariates'),assumption=(33,'Consider the discrete bivariate (X, Y)'))
# Marginal formulas use their whole argument-bearing symbols as actually captured.
pick(5,'B',[8,9,10,11,12])
for fp in [47,48]:
 new_formula(5,[fp],(fp,'f \\left ( x , y \\right )'),(46,'the joint pf'),assumption=(46,'In the case of discrete variates X and Y'))
# The adjacent Y formula is explicit but has no independently declared marginal-f(y)
# meaning in this paragraph; the joint binding is enough to retain the occurrence.
for r in OUTPUT[5]:
 if r['family']=='formula_context'and ptr(r,'formula')[0]in ['#/texts/45']:
  lit(5,r,'assumption',39,'In the case of continuous bivariate (X, Y) having joint pdf f (x, y)')
# Full equation-array rows, not the incomplete Pr(...) cell alone.
for table,starts in [(1,[0,5,10]),(2,[0,5])]:
 for start in starts:
  parts=[f'#/tables/{table}/data/table_cells/{n}'for n in range(start,start+5)]
  for sym,decl,meaning in [('X',39,'the univariate X'),('Y',44,'the univariate Y')]:
   new_formula(5,parts,(parts[0],sym)if sym in projection(5)['text'][loc(5,parts[0])['start']:loc(5,parts[0])['end']]else (parts[2],sym),(decl,meaning),assumption=(50,'Continuing Example 4.1.1'))

# The independence product has two genuine source-qualified uses, with one interrupted
# prose branch. The frozen one-accepted-interpretation policy cannot select one branch.
limit(6,['#/texts/52','#/texts/53','#/texts/55'],'formula_context','The product formula follows both a continuous joint-pdf and a discrete joint-pf reading. A leaves it unresolved; B picks the discrete branch. No branch is arbitrarily selected under the one accepted interpretation per occurrence rule.',alternatives=[{'meaning':'the joint pdf for a continuous bivariate','condition':'with independent continuous univariate elements'},{'meaning':'the joint pf for a discrete bivariate','condition':'with independent discrete univariate elements'}])
# Conditional formulas: separately located argument-bearing bindings are representable.
pick(7,'B',[9,10,11,12,13,14,15,16,19,20,21,22,23,24,41,42])
for r in OUTPUT[7]:
 if r['family']=='formula_context'and ptr(r,'formula')[0]in ['#/texts/66','#/texts/68']:
  lit(7,r,'domain',67,'for all (x, y) ∈ ℜX,Y')
# In the composition identity, pdf/pf conditions apply jointly; independent field
# alternatives would lose their pairing, and formula-only would hide the declarations.
for fp in [74,76]:
 limit(7,f'#/texts/{fp}','formula_context','The source states the composition identity for pdfs (or pfs), and the independence reduction retains both source-qualified meanings. The released occurrence shape cannot accept incompatible paired meanings/conditions for the same first function use; no formula-only fallback or arbitrary branch.',alternatives=['joint, marginal, and conditional pdfs','joint, marginal, and conditional pfs'])
# B omitted the first composition proposition? It is retained separately above.

# Bayes: exact conditional-pdf/discrete-pf alternatives remain visible.
pick(8,'B',[5])
limit(8,['#/texts/93','#/texts/94'],'formula_context','For the same first f-use, the source explicitly supplies continuous-bivariate pdf and discrete-bivariate pf meanings. B formula-only suppresses these declarations. A correctly retains the two paired readings as a limitation; no single accepted branch can preserve them.',alternatives=[{'meaning':'marginal and conditional pdfs','condition':'For a continuous bivariate'},{'meaning':'marginal and conditional pfs','condition':'for a discrete bivariate'}])

# Functions of a multivariate: use the actual local index declaration; do not invent
# a link from the displaced Bayes example to the following general-mapping sentence.
pick(9,'A',[6,7,8,9,10])
for r in OUTPUT[9]:
 if r['family']=='formula_context'and value(r,'symbol')=='n':absent(9,r,'domain','The stated i=1,2,...,n range declares the index i, not a separate domain for n.')
new_formula(9,[(105,'Z = X+Y')],(105,'Z'),(105,'a summation'),assumption=(105,'when X and Y are independent'))
limit(9,'#/texts/105','formula_context','The source declares the characteristic function C(t), but the following captured inline formula fuses the function/subscript text as CX+Y (t) = CX(t)CY (t). Its exact function symbol membership is ambiguous; A bare-C binding and B formula-only each conceal this issue. No TeX/subscript repair.',formula_literal='CX+Y (t) = CX(t)CY (t)')

# Measures of location: literal native formulas retain the captured Y/X disagreement.
pick(10,'B',[75,76,77,78])
limit(10,['#/texts/126','#/texts/127','#/texts/128','#/texts/129','#/texts/130','#/texts/131','#/texts/132','#/texts/133','#/texts/134'],'formula_context','The sorted sample is declared with X tokens but the median formulas use Y. No X-to-Y symbol binding is invented. Formula literals and stated parity conditions are retained as formula-only readings; undeclared symbol meanings remain unstated.')

# Confidence formulas: declared s, N and alpha are retained; missing Y-bar and
# transformed t spellings remain explicit source limitations.
pick(11,'B',[28,29,30,31,32,33,34,35,36,51,53,55,57,59,61,73,74,75,76,77,78,79,80])
pick(11,'A',[56])
for fp in [84,85]:
 new_formula(11,[fp],(fp,'\\alpha'),(112,'the\ndesired significance level'))
limit(11,['#/texts/111','#/texts/112'],'formula_context','The native confidence-limit display has Y instead of the explicitly declared Y-bar, and t1-α/2,N−1 differs from the spaced/hyphenated declaration. No missing bar or transformed t-symbol identity is manufactured; s/N/α bindings remain accepted.')
limit(11,['#/texts/80','#/texts/81'],'formula_context','The native statistic display has Y and A0; the following declaration text loses the corresponding symbols. No repair to Y-bar or mu0 is made. Exact s/N bindings remain available.')
# T has an actual located label; formula-only T displays should not omit that binding.
for r in OUTPUT[11]:
 if r['family']!='formula_context':continue
 fas=get_anchors(r,'formula')
 first=next((a for a in fas if 'T' in a.get('source_piece','')),None)
 if first and value(r,'symbol')=='unstated':
  lit(11,r,'symbol',first['pointer'],'T');lit(11,r,'meaning',78,'Test Statistic')
# Explicit code equations in the confidence-example input are native formula occurrences.
for expression in ['N = 195','MEAN = 9.261460','STANDARD DEVIATION = 0.022789','t1-0.025,N-1 = 1.9723','LOWER LIMIT = 9.261460 - 1.9723*0.022789/√195','UPPER LIMIT = 9.261460 + 1.9723*0.022789/√195']:
 new_formula(11,[(88,expression)],(88,'N')if expression=='N = 195'else None,(112,'the sample size')if expression=='N = 195'else None,assumption=(87,'ZARR13.DAT data set'))

# Inherit only source-confirmed limitations: missing table headers, source blanks,
# chart-routing limits and original-page duplicate observations. Formula judgements
# above replace each author's differing interpretation rather than merging them.
for i in PACKETS:
 for old in COV_A[i].get('limitations',[]):
  fam=old.get('family',old.get('families'))
  if fam=='table' or old.get('disposition')in ['unsupported','overlapping_native_duplicate']:
   z=copy.deepcopy(old)
   if 'pointer'in z:z['pointers']=[z.pop('pointer')]
   z['source_review']='C inspected the frozen native item and source projection; this limitation is retained.'
   LIMITS[i].append(z)
# Retain the original native chart payload and exact frozen projection pieces for all
# picture items whose numeric/layout content lacks released exact chart scopes.
for i in PACKETS:
 for p,item in native(i).items():
  if item.get('label')!='picture':continue
  data=item.get('chart_data') or item.get('data')
  if not data:continue
  if any(p in z.get('pointers',[])for z in LIMITS[i]):continue
  limit(i,p,['table','measurement','formula_context'],'Frozen native chart content has no exact released chart anchor scopes. Native chart data are retained here; table addresses and numeric role associations are not invented.',source_payload=item,source_projection_pieces=[x for x in projection(i)['pieces']if x.get('item_ref')==p])


for issue in LIMITS[2]:
 if issue['pointers']==['#/texts/60','#/texts/61','#/texts/62','#/texts/63','#/texts/64','#/texts/65']:issue['disposition']='source_fragment_reconciled'

# C's final semantic pass: source ambiguities are not resolved by serialization success.
# Complete the explicit rate-symbol definition and the shared finite clause for typical value.
for r in OUTPUT[2]:
 if r.get('_origin',{}).get('author')=='A'and r['_origin']['index']==222:
  lit(2,r,'defining_text',28,'we must assume that the average rate, i.e., the average number of occurrences per minute, is a constant. This rate we will denote by λ')
for r in OUTPUT[10]:
 if r.get('_origin',{}).get('author')=='B'and r['_origin']['index']==2:
  seq(10,r,'defining_text',[(6,'We will use'),(6,'the term typical value to refer generically to measures of location')])
# Remove a fragment duplicate of the complete parameter equation, and shorten the
# native 40=np equation to the actual equation pieces instead of its preceding prose.
OUTPUT[2]=[r for r in OUTPUT[2]if not(r['family']=='formula_context'and value(r,'formula')=='\\lambda='and r.get('_origin',{}).get('author')=='C')]
for r in OUTPUT[2]:
 if r['family']=='formula_context'and ptr(r,'formula')==['#/texts/104','#/texts/105']:
  seq(2,r,'formula',[(104,'40 ='),105])
# A recovered repetition of the confidence-example setup is the same original line.
limit(11,['#/texts/87','#/texts/137','#/texts/139'],'measurement','Frozen source repeats the confidence-example setup at texts/87 and texts/137+139, but the latter have no original-page provenance. A distinct original occurrence versus a recovery duplicate cannot be established. The located texts/87 reading is accepted; the additional recovered reading remains eligible and unresolved.',source_disposition='unresolved_original_occurrence_identity')
# A genuine either/or proposition cannot carry positive or negative polarity alone.
OUTPUT[11]=[r for r in OUTPUT[11]if not(r.get('_origin',{}).get('author')=='B'and r['_origin']['index']in [8,15])]
limit(11,'#/texts/110','assertion','"The interval computed from a given sample either contains the true mean or it does not" is an explicit disjunction. A single positive polarity on B\'s first predicate conceals the negative alternative; splitting it into independent accepted claims would assert a branch. The released source reading remains unrepresentable here.',alternatives=['contains the true mean','does not contain the true mean'])
limit(11,'#/texts/115','assertion','The comparative clause "The larger the sample standard deviation, the larger the confidence interval" has no explicit subject-predicate-object triple with all required literal roles. B assigns its comparative antecedent as subject and comparative adjective as predicate; no missing copula is invented. The following noisy-data proposition is accepted separately.')
for r in OUTPUT[11]:
 if r.get('_origin',{}).get('author')=='B'and r['_origin']['index']==5:
  lit(11,r,'subject',68,'our estimate');lit(11,r,'predicate',68,'is',2);lit(11,r,'object',68,'the more precise');lit(11,r,'condition',68,'The narrower the interval')

# Complete the remaining explicitly declared statistic bindings, independently of
# whether another symbol already gave the formula an accepted reading.
formula_groups={}
for r in list(OUTPUT[11]):
 if r['family']=='formula_context':
  key=tuple((a['pointer'],a['start'],a['end'])for a in get_anchors(r,'formula'))
  formula_groups.setdefault(key,[]).append(r)
for key,rs in formula_groups.items():
 base=rs[0];fa=get_anchors(base,'formula');syms={value(r,'symbol')for r in rs}
 for sym,decl,meaning in [('T',78,'Test Statistic'),('α',112,'the\ndesired significance level')]:
  if sym in syms:continue
  a=next((a for a in fa if sym in a['source_piece']),None)
  if a is None:continue
  # T denotes the statistic only when the actual formula piece contains a T use.
  r=copy.deepcopy(base);r['_origin']={'author':'C','source_authored':True}
  lit(11,r,'symbol',a['pointer'],sym);lit(11,r,'meaning',decl,meaning);add(11,r)
# Meanings use the shortest complete noun phrase with the source determiner.
for r in OUTPUT[4]:
 if r['family']!='formula_context':continue
 sym=value(r,'symbol')
 if sym=='F':
  if ptr(r,'formula')[0]=='#/texts/34':lit(4,r,'meaning',33,'joint distribution function')
  else:lit(4,r,'meaning',18,'The distribution function')
 elif sym=='f':lit(4,r,'meaning',22,'a bivariate probability density function')
 elif sym=='A':lit(4,r,'meaning',26,'an arbitrary bivariate quantile set')
# Apply an exact, source-local first-use selection for every declared formula symbol.
# Macro names (sqrt, infty, etc.) and text/environment names are not variable uses.
import re
for i,rows in OUTPUT.items():
 for r in rows:
  if r['family']!='formula_context' or field(r,'symbol')['state']!='present':continue
  sym=value(r,'symbol')
  if not isinstance(sym,str):continue
  match=None
  for fa in get_anchors(r,'formula'):
   text=fa['source_piece'];excluded=[]
   if not sym.startswith('\\'):
    excluded.extend((m.start(),m.end())for m in re.finditer(r'\\[A-Za-z]+',text))
    excluded.extend((m.start(),m.end())for m in re.finditer(r'\\(?:begin|end|text)\s*\{[^}]*\}',text))
   for m in re.finditer(re.escape(sym),text):
    if any(lo<=m.start()<hi for lo,hi in excluded):continue
    match=copy.deepcopy(fa);match['start']=fa['start']+m.start();match['end']=fa['start']+m.end();match['source_piece']=sym;match.pop('anchor_id',None);match['anchor_id']=anchor_identity(match);break
   if match:break
  assert match,('declared symbol has no genuine exact use',i,sym,value(r,'formula'))
  put(i,r,'symbol',[match])


for r in OUTPUT[9]:
 if r['family']=='formula_context':
  if value(r,'symbol')=='n':lit(9,r,'meaning',109,'n such independent variates')
  elif value(r,'symbol')=='i':lit(9,r,'meaning',111,'the subscript i identifies the ith variate')

# Ordinary-grammar classification cues use the actual finite predicate, avoiding
# equally spelled substrings in words such as statistical, distribution or precise.
for i,indexes in [(2,[224,226]),(10,[75])]:
 for r in OUTPUT[i]:
  if r.get('_origin',{}).get('author')!='A' or r['_origin']['index']not in indexes:continue
  put(i,r,'polarity',get_anchors(r,'predicate'),label='positive')
  if not(i==2 and r['_origin']['index']==224):put(i,r,'modality',get_anchors(r,'predicate'),label='asserted')
# Concise source-grounded resolution reasons accompany every author's record.
UNIT_REASONS={
 1:'Both no-output readings are confirmed by the sole chapter heading.',
 2:'Retain complete defining antecedents, ordinary grammar cues, all explicit example parameters/counts and source-local declared formula bindings. Reject borrowed subsection meanings and malformed macro bindings; preserve every blank/headerless table cell as a limitation.',
 3:'Both no-output readings are confirmed by the sole multivariate-distributions heading.',
 4:'Retain setup clauses and discrete/continuous conditions. The declared quantile is an ordered pair, not a whole quantile meaning for each individual coordinate. Function tokens exclude letters in TeX macro names. Native probability-array cells remain headerless table limitations.',
 5:'Argument-bearing function tokens distinguish the locally declared joint/marginal functions without treating every f as one binding. Full equation-array rows retain separate source pieces. All native cells without a header path remain table limitations.',
 6:'Retain the explicit independence definition and discrete-pf product proposition. The interrupted continuous object and joint formula\'s two genuine source-qualified uses are limitations, rather than an arbitrary discrete branch.',
 7:'Retain complete conditional definitions, exact argument-bearing function tokens, denominator/domain conditions and worked literal probabilities. The pdf/pf composition alternatives are not collapsed to one accepted meaning.',
 8:'Retain explicit Bayes definition and literal conditional scopes. The equation with paired continuous-pdf/discrete-pf meanings is a limitation; the unbound Pr(...) version remains separately eligible.',
 9:'Separate the nested mapping consequences, retain the explicit local index declaration and summation condition, and remove a displaced-example condition. The fused characteristic-function/subscript capture is a source limitation.',
 10:'Retain determiners, complete shared defining clauses, explicit generating-sample conditions, approximate bounds and percentage units. Original-page repetitions do not add a second observation. Chart scopes are not fabricated.',
 11:'Retain source declarations, literal confidence/example values, explicit units and the native alternative-hypothesis/rejection-region table. Correct source role assignment, retain missing/transformed symbols and genuine disjunctions as limitations, and count repeated original lines once.'}
for i in PACKETS:
 note(i,UNIT_REASONS[i],scope='all five families and every frozen native item',method='source adjudication; no voting/union/intersection',adjudication_passes=PACKETS[i]['adjudication_passes'])
 for ai,author in enumerate(PACKETS[i]['authors']):
  for n,old in enumerate(BATCHES[i][ai]['records']):
   primary=set(old['occurrence_anchors'])
   related=[r for r in OUTPUT[i]if r['family']==old['family'] and (set(finalize(i,r)['occurrence_anchors'])&primary)]
   exact=any(finalize(i,r)['interpretation_id']==old['interpretation_id']for r in related)
   status='accepted_exact'if exact else 'source_corrected_or_resegmented'if related else 'source_not_accepted_or_limitation'
   note(i,UNIT_REASONS[i],author=author['actor'],pass_id=author['pass_id'],input_record_id=old['record_id'],input_interpretation_id=old['interpretation_id'],disposition=status,output_record_ids=list(dict.fromkeys(finalize(i,r)['record_id']for r in related)))

# Explicit source-only adjudication account, including every native source item.
def write_outputs():
 coverage={'protocol':'independent-source-census-C-v3','actor':'gpt-6.1-sol-high-C-v3','canonical_session':'/root/m1_reference_c_v3','guideline':'statistics-m1-reference-3','reference_policy_version':'statistics-reference-reading-3','prediction_policy_version':'m1-grouped-reading-logistic-1','release_id':RELEASE,'source_only':True,'prediction_access':'not_run','quality_claim':'not_established','units':[]}
 for i in PACKETS:
  rows=[finalize(i,r)for r in OUTPUT[i]]
  unique={}
  for r in rows:
   if r['record_id']in unique:
    assert r['interpretation_id']==unique[r['record_id']]['interpretation_id'],('incompatible C interpretation',i,r['record_id'])
   unique[r['record_id']]=r
  rows=list(unique.values())
  payload={'protocol':'source-record-reference-1','release_id':RELEASE,'unit_ref':PACKETS[i]['source']['unit_ref'],'guideline':'statistics-m1-reference-3','reference_policy_version':'statistics-reference-reading-3','prediction_policy_version':'m1-grouped-reading-logistic-1','reason':'Independent source-only C adjudication of both exact registered author submissions and every frozen native item. Complete local source readings, located classification cues and source limitations govern acceptance; no production predictions or scientific-truth inference. See coverage.json for pointer-based decisions and limitations.','adjudication_passes':PACKETS[i]['adjudication_passes'],'records':rows}
  (OUT/f'rawunit-{i}.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
  counts=dict(collections.Counter(r['family']for r in rows))
  items=[]
  for p,item in native(i).items():
   accepted={r['family']for r in rows if any(a['pointer']==p or a['pointer'].startswith(p+'/')for a in r['anchors'])}
   limits=[z for z in LIMITS[i]if p in z.get('pointers',[])or any(x.startswith(p+'/')for x in z.get('pointers',[]))]
   label=item.get('label','native_item')
   if accepted:disposition='Located accepted source readings or their explicit field/context evidence; all five families inspected.'
   elif limits:disposition='Eligible source content remains unresolved or unrepresentable; see limitations.'
   elif label in ['section','section_header','footnote','page_header','page_footer']:disposition='Structure, title, page furniture or bibliographic metadata; no separate statistical occurrence.'
   elif not item.get('text','').strip()and label!='table':disposition='Empty native item or non-text source container inspected; no recovered literal statistical occurrence.'
   else:disposition='Discourse, isolated continuation/notation or supporting context inspected within its complete local clause; no distinct additional five-family occurrence.'
   items.append({'pointer':p,'label':label,'inspected':True,'disposition':disposition,'accepted_families':sorted(accepted),'limitation_count':len(limits),'source_text_sha256':hashlib.sha256(item.get('text','').encode()).hexdigest()if 'text'in item else None})
  # Include every table data cell separately, including source blank/header dispositions.
  for p,item in native(i).items():
   if item.get('label')!='table':continue
   for n,cell in enumerate(item['data']['table_cells']):
    cp=f'{p}/data/table_cells/{n}';acc=[r['record_id']for r in rows if r['family']=='table'and value(r,'cell')==cp]
    items.append({'pointer':cp,'label':'table_cell','inspected':True,'literal':cell['text'],'disposition':'native header'if cell.get('column_header')else 'accepted native data cell'if acc else 'eligible data cell limitation','accepted_records':acc,'limitation_count':sum(cp in z.get('pointers',[])for z in LIMITS[i])})
  census=next(u for path in (ROOT/'freeze-002').glob('origin-*/source-census.json')for u in json.loads(path.read_text())['units']if u['unit_key']==payload['unit_ref'])
  assert census['native_items']==len(native(i))
  unsupported_pointers={p['item_ref']for p in census['unsupported_record_projection_pieces']}
  assert unsupported_pointers<={p for z in LIMITS[i]for p in z.get('pointers',[])}
  coverage['units'].append({'source_census':census,'native_items_inspected':len(native(i)),'projected_pieces_inspected':len(projection(i)['pieces']),'unit_id':i,'unit_ref':payload['unit_ref'],'source_section':section(i),'all_five_families_inspected':FAMILIES,'adjudication_passes':payload['adjudication_passes'],'accepted_counts':counts,'no_output_reason':'Only a chapter/title heading; no eligible reading in any family.'if not rows and i in [1,3]else None,'source_health':projection(i)['health'],'items':items,'limitations':LIMITS[i],'disagreement_dispositions':DECISIONS[i],'author_counts':{a['actor']:dict(collections.Counter(r['family']for r in json.loads(a['authored_utf8'])['records']))for a in PACKETS[i]['authors']},'strict_reference_disagreement':PACKETS[i]['disagreement']})
 (OUT/'coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+'\n')
 return coverage

if __name__=='__main__':
 c=write_outputs();print(json.dumps({'outcome':'serialized','unit_counts':{u['unit_id']:u['accepted_counts']for u in c['units']},'limitations':sum(len(u['limitations'])for u in c['units'])},indent=2))
