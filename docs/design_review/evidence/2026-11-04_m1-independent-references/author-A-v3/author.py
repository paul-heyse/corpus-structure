"""Independent A-v3 manual source readings; helpers serialize supplied judgments only."""
import json, pathlib, hashlib, sys, collections, re
ROOT=pathlib.Path(__file__).resolve().parent
F=ROOT.parent/'freeze-002'
sys.path.insert(0,str(pathlib.Path.cwd()/'python/corpus-structure/src'))
from corpus_structure.semantic.record_contracts import anchor_identity,evidence_set_identity,record_identity,interpretation_identity
CONTRACT=json.loads((F/'record-contract.json').read_text())
ROLES={x['family']:x for x in CONTRACT['families']}
UNITS={int(p.stem.split('-')[1]):json.loads(p.read_text()) for p in F.glob('origin-*/unit-*.json')}
OUT={n:[] for n in UNITS}; LIMITS={n:[] for n in UNITS}

def V(n):return UNITS[n]['source_frame']['source_views'][0]
def text(n):return V(n)['projection']['text']
def items(n):return UNITS[n]['native_contexts'][0]['native_items']
def span(n,phrase,after=None):
 t=text(n);start=t.index(phrase,0 if after is None else t.index(after)+len(after));return(start,start+len(phrase))
def ptrspan(n,p):
 a=[x for x in V(n)['projection']['pieces'] if x.get('item_ref')==p and x.get('source_field')=='text'];assert len(a)==1,(n,p,a);return a[0]['start'],a[0]['end']
def lit(s,after=None):return ('literal',s,after)
def nat(p):return ('native',p)
def cls(kind,label,cue,after=None):return ('classified',kind,label,cue,after)
def absent(reason,state='unstated'):return ('absent',state,reason)
def location(n,s,after=None):
 if isinstance(s,list):return [a for piece in s for a in location(n,piece)]
 a,b=s if isinstance(s,tuple) else span(n,s,after);ans=[]
 for p in V(n)['projection']['pieces']:
  if p['kind']=='synthetic_separator':continue
  lo=max(a,p['start']);hi=min(b,p['end'])
  if lo>=hi:continue
  ptr=p['item_ref']
  if p.get('source_field')=='cell_text':ptr+=f"/data/table_cells/{p['cell_index']}"
  ans.append(dict(pin=UNITS[n]['source_frame']['evaluation_frame']['pin'],space='selected_projection',pointer=ptr,precision='exact',start=lo,end=hi,source_piece=text(n)[lo:hi]))
 assert ans,(n,s)
 return ans

def record(n,family,values,primary,context=None):
 pin=UNITS[n]['source_frame']['evaluation_frame']['pin'];anchors={};sets={};fields=[];pa=[]
 def anchor(a):
  a=dict(a);a['anchor_id']=anchor_identity(a);anchors[a['anchor_id']]=a;return a['anchor_id']
 def evidence(role,aa,usage):
  ids=[anchor(a) for a in aa];s=dict(role=role,ordering='ordered',usage=usage,anchors=ids);s['set_id']=evidence_set_identity(s);sets[s['set_id']]=s;return s['set_id'],ids
 for roledef in ROLES[family]['roles']:
  role=roledef['role'];value=values.get(role,absent('Inspected local reading and section; this supplemental role is not explicitly stated.'))
  kind=value[0];field=dict(role=role,kind='literal',state='present',meaning_changing=roledef['meaning_changing'],evidence_status='available')
  if kind=='literal':
   aa=location(n,value[1],value[2]);sp=[a['source_piece'] for a in aa]
   if len(sp)==1:field.update(original=sp[0],value=dict(kind='text',text=sp[0]))
   else:field.update(original_pieces=sp,value=dict(kind='text_sequence',items=sp))
   sid,ids=evidence(role,aa,'literal')
  elif kind=='native':
   field['kind']='native';field['value']=dict(kind='native_location',pointer=value[1]);sid,ids=evidence(role,[dict(pin=pin,space='native',pointer=value[1],precision='item')],'native')
  elif kind=='classified':
   field.update(kind='classified',value=dict(kind=value[1],label=value[2]),policy='statistics-m1-reference-3');sid,ids=evidence(role,location(n,value[3],value[4]),'classification_cue')
  elif kind=='absent':
   field.update(kind={'normalized_value':'normalized','value_role':'classified','relation_type':'classified','polarity':'classified','modality':'classified','scope':'native' if family in ('definition','formula_context') else 'literal','table':'native','cell':'native'}.get(role,'literal'),state=value[1],reason=value[2]);sid,ids=evidence(role,[dict(pin=pin,space='native',pointer=context or V(n)['section_pointer'],precision='item')],'association')
  field['evidence_sets']=[sid];fields.append(field)
  if role in primary:pa.extend(ids)
 r=dict(record_id='',contract=ROLES[family]['contract'],family=family,occurrence_recipe='source-anchor-membership-1',pin=pin,occurrence_anchors=list(dict.fromkeys(pa)),interpretation_id='',standing='accepted',policy_version='statistics-reference-reading-3',fields=fields,anchors=list(anchors.values()),evidence_sets=list(sets.values()))
 r['record_id']=record_identity(UNITS[n]['release_id'],r);r['interpretation_id']=interpretation_identity(r);OUT[n].append(r);return r

def D(n,term,clause,alias=None,cue=None,after=None):
 v=dict(term=lit(term,after),defining_text=lit(clause,after),scope=nat(V(n)['section_pointer']))
 if alias:v['alias']=lit(alias,after)
 if cue:v['relation_type']=cls('definition_relation','definition',cue,after)
 record(n,'definition',v,('term','defining_text'))
def ordered(n,parts,after=None):
 t=text(n);floor=0 if after is None else t.index(after)+len(after);candidates=[]
 for m in re.finditer(re.escape(parts[0]),t[floor:]):
  a=m.start()+floor;positions=[(a,a+len(parts[0]))];end=positions[-1][1]
  try:
   for z in parts[1:]:
    k=t.index(z,end);positions.append((k,k+len(z)));end=k+len(z)
   candidates.append((end-a,positions))
  except ValueError:pass
 if not candidates:raise ValueError((n,parts,after))
 return min(candidates,key=lambda x:x[0])[1]
def near(n,phrase,pos):
 return min([(m.start(),m.end()) for m in re.finditer(re.escape(phrase),text(n))],key=lambda p:abs(p[0]-pos))
def A(n,s,p,o,condition=None,quant=None,pol=None,mod=None,attribution=None,after=None):
 ss,pp,oo=ordered(n,[s,p,o],after)
 v=dict(subject=lit(ss),predicate=lit(pp),object=lit(oo))
 if condition:
  v['condition']=lit(near(n,condition,ss[0]))
  if condition.startswith(('For ', 'for ', 'In our example', 'In both cases', 'In all other cases', 'In general')):v['scope']=lit(near(n,condition,ss[0]))
 if quant:v['quantification']=lit(quant)
 if pol:v['polarity']=cls('assertion_polarity',pol,pp)
 if mod:v['modality']=cls('assertion_modality',mod[0],mod[1]) if isinstance(mod,tuple) else cls('assertion_modality',mod,pp)
 if attribution:v['attribution']=lit(attribution,after)
 record(n,'assertion',v,('subject','predicate','object'))
def cluster(n,parts,after=None):
 t=text(n);floor=0 if after is None else t.index(after)+len(after);matches=[]
 for z in parts:
  pattern=re.escape(z)
  if z and z[0].isdigit():pattern=r'(?<![0-9.])'+pattern
  if z and z[-1].isdigit():pattern+=r'(?![0-9])'
  found=[(m.start()+floor,m.end()+floor) for m in re.finditer(pattern,t[floor:])]
  if not found:raise ValueError((n,z,after))
  matches.append(found)
 combos=[]
 for group in matches:
  for a,b in group:
   choice=[min(g,key=lambda p:min(abs(p[0]-a),abs(p[1]-b))) for g in matches]
   combos.append((max(p[1] for p in choice)-min(p[0] for p in choice),choice))
 return min(combos,key=lambda p:p[0])[1]
def M(n,r,p,val,role='stated_value',condition=None,unit=None,comp=None,unc=None,reference=None,after=None):
 rr,pp,vv=cluster(n,[r,p,val],after)
 v=dict(referent=lit(rr),property=lit(pp),original_value=lit(vv),value_role=cls('measurement_value_role',role,pp),normalized_value=absent('Original literal only; normalization excluded by statistics-m1-reference-3.','inapplicable'))
 for k,z in [('condition',condition),('unit',unit),('comparator',comp),('uncertainty',unc),('reference_quantity',reference)]:
  if z:v[k]=lit(near(n,z,rr[0]))
 if n==10 and p=='mode':
  qual='(the mode is computed as the midpoint of the histogram interval with the highest peak)'
  v['condition']=lit([near(n,condition,rr[0]),near(n,qual,rr[0])])
 if n==2 and r=='A typesetter':v['value_role']=cls('measurement_value_role',role,'on the average')
 if n==2 and r=='the average human':v['value_role']=cls('measurement_value_role',role,'the average human')
 if n==11 and p=='N':v['value_role']=cls('measurement_value_role',role,'the sample size')
 record(n,'measurement',v,('referent','property','original_value'))

# Independently authored definitions, preserving source recognition, not repairing it.
D(2,'uniformly distributed','IfXis a random variable which represents the outcome of an experiment of this type, then we say thatXis uniformly distributed',cue='we say that')
D(2,'binomial distribution','It is the distribution of the random variable which counts the number of heads which occur when a coin is tossedntimes, assuming that on any one toss, the probability that a head occurs isp',cue='is the distribution')
D(2,'geometric distribution','In general, if 0< p <1, and q = 1 −p, then we say that the random variable T\nhas ageometric distributionif\nP(T = j) = qj−1p ,\nfor j = 1, 2, 3, .....',cue='we say that')
D(2,'negative binomial distribution','For a generalk, we say thatXhas a negative binomial distribution',cue='we say that')
D(2,'"memoryless" property','the probability that the customer’s service takessmore time units is independent of the length of timerthat the customer has already been served',cue='is called')
D(2,'\\lfloor x\\rfloor','the greatest integer not exceedingx',cue='denotes')
D(2,'\\lceil x\\rceil','the least integer which is greater than or equal tox',cue='means')
D(2,'Poisson distribution','The above distribution is the Poisson distribution',cue='is the')
D(4,'joint probability statements','Probability statements concerning more than one random variate are called joint probability statements',cue='are called')
D(4,'a bivariate','call the pair (X, Y) a bivariate',cue='call')
D(4,'univariates','each of X and Y alone referred to as univariates',cue='referred to as')
D(4,'a multivariate','In the general case of more than one variate (including the bivariate case), the collection of variates is more generally referred to as a multivariate',cue='referred to as')
D(4,'joint range','Let ℜX,Y be the set of all pairs of (real number) values that the bivariate (X, Y) can take. The set ℜX,Y is the joint range of (X, Y)',cue='is the joint range')
D(4,'a bivariate quantile','Let the real valued pair (x, y) denote a general element of the joint range ℜX,Y . We refer to (x, y) as a bivariate quantile of (X, Y)',cue='refer to')
D(4,'Pr[X ≤ x, Y ≤ y]','the probability that the value realized by the univariate X is less than or equal to x and the value realized by the univariate Y is less than or equal to y',cue='mean')
D(4,'joint probability domain','Analogous to the univariate case, ℜ α X,Y is called the joint probability domain of the bivariate (X, Y)',cue='is called')
D(4,'distribution function','The distribution function (joint df) F associated with a bivariate (X, Y) maps from the joint range ℜX,Y into the joint probability domain ℜ α X,Y and is such that\n'+items(4)['#/texts/19']['text'],alias='joint df')
D(4,'bivariate probability density function','When (X, Y) have a jointly continuous probability domain, the function f (x, y) is a bivariate probability density function (joint pdf) if\n'+items(4)['#/texts/23']['text']+'\nfor all (x, y) in ℜX,Y',alias='joint pdf',cue='is a bivariate probability density function')
D(4,'bivariate probability function','In this case f (x, y) is the bivariate probability function (joint pf)',alias='joint pf',cue='is the bivariate probability function')
D(5,'marginal distribution','Probabilities associated with a univariate element of a bivariate without regard to the value of the other univariate element within the same bivariate arise from the marginal distribution of that univariate')
D(5,'marginal probability density function','In the case of continuous bivariate (X, Y) having joint pdf f (x, y), the marginal probability density function (marginal pdf) of the univariate X is found for each quantile x by integrating the joint pdf over all possible bivariate quantiles (x, y) ∈ ℜX,Y having fixed value for x,\n'+items(5)['#/texts/40']['text'],alias='marginal pdf')
D(5,'marginal probability function','In the case of discrete variates X and Y, the marginal probability function (marginal pf) of X is found for each quantile x by summing the joint pf associated with the bivariate quantiles (x, y) ∈ ℜX,Y having fixed x\n'+items(5)['#/texts/47']['text'],alias='marginal pf')
D(6,'independent','Two univariates are said to be independent if the marginal probabilities associated with the outcomes of one variate are not influenced by the observed value of the other variate, and vice versa',cue='are said to be')
D(7,'dependent','When two univariates are not independent, they are said to be dependent',cue='are said to be')
D(7,'conditional probabilities','probabilities associated with one variate given information about the realized value of the other variate')
D(7,'conditional pf','When conditioning on a single observed value of one univariate component Y = y of a discrete bivariate (X, Y), the conditional pf of X, given Y = y, and denoted by f (x|y), is found by taking the ratio of the joint pf f(x, y) to the marginal pf of Y, f (y), for fixed Y = y\n'+items(7)['#/texts/62']['text']+'\nfor all (x, y) ∈ ℜX,Y',alias='f (x|y)')
D(7,'conditional probability density function','For continuous random variates, the conditional probability density function (conditional pdf) for X given Y = y and denoted by f (x|y) may be constructed using the ratio of the joint pdf over the marginal pdf of Y, for fixed Y = y\n'+items(7)['#/texts/66']['text'],alias='conditional pdf')
D(7,'composition','Joint, marginal, and conditional probabilities satisfy the property of composition, whereby joint probabilities may be determined by the product of marginal probabilities and the appropriate conditional probability')
D(8,"Bayes' theorem", "A fundamental result concerning conditional probabilities is known as Bayes' theorem, providing the rule for reversing the roles of variates in a conditional probability",cue='is known as')
D(10,'the mean','the mean is the sum of the data points divided by the number of data points',alias='the average',cue='is the sum')
D(10,'the median','the median is the value of the point which has half the data smaller than that point and half the data larger than that point',cue='is the value')
D(10,'the mode','the mode is the value of the random sample that occurs with the greatest frequency',cue='is the value')
D(10,'symmetric','the distribution can be folded about an axis so that the 2 sides coincide',cue='we mean that')
D(10,'robustness','robustness is a lack of susceptibility to the effects of nonnormality',cue='is a lack')
D(10,'Robustness of validity','Robustness of validity means that the confidence intervals for the population location have a 95% chance of covering the population location regardless of what the underlying distribution is',cue='means')
D(10,'Robustness of efficiency','Robustness of efficiency refers to high effectiveness in the face of non-normal tails',cue='refers to')
D(10,'Mid-Mean','computes a mean using the data between the 25th and 75th percentiles')
D(10,'Trimmed Mean','similar to the mid-mean except different percentile values are used')
D(10,'Winsorized Mean','similar to the trimmed mean. However, instead of trimming the points, they are set to the lowest (or highest) value')
D(10,'Mid-range','(smallest + largest)/2')
D(11,'Confidence limits for the mean','Confidence limits for the mean (Snedecor and Cochran, 1989) are an interval estimate for the mean',cue='are an interval estimate')
D(11,'confidence coefficient','The confidence coefficient is simply the proportion of\nsamples of a given size that may be expected to contain the true mean',cue='is simply')
# Explicit numeric statements, including hypothetical worked examples.
M(2,'each integer between 1 andn','probability','1_/n_',condition='IfXis a random variable which represents the outcome of an experiment of this type')
M(2,'T','most probable\nvalue','1',condition='In both cases')
M(2,'a typesetter' if False else 'A typesetter','mistake','one',role='mean',unit='per 1000 words',condition='Example 5.3')
M(2,'a book','words to a page','100',role='count',condition='Assume that he is setting a book with 100 words to a page')
M(2,'S100','expected value','.1',role='mean',condition='Example 5.3')
M(2,'a district','blocks','10',role='count',unit='blocks',condition='Assume that you live in a district of size 10 blocks by 10 blocks')
M(2,'the total district','small squares','100',role='count',condition='Assume that you live in a district of size 10 blocks by 10 blocks')
M(2,'the total area','bombs','400',role='count',condition='if the total area is hit by 400 bombs')
M(2,'a particular bomb','probability','1/100',condition='We assume that a particular bomb will hit your square with probability 1/100')
M(2,'the Poisson distribution','\\lambda','4',condition='Example 5.4',after='Thus we can use')
M(2,'cookie dough','cookies','500',role='count',condition='We assume that we have made enough cookie dough for 500 cookies')
M(2,'the dough','raisins','600',role='count',condition='We put 600 raisins in the dough')
M(2,'the average human','white blood cells','40',role='mean',condition='Suppose that in a certain fixed amountAof blood, the average human has 40 white blood cells',unit='in a certain fixed amountAof blood')
for n,ref,prop,value,role,cond in [
 (10,'The first histogram','mean','0.005','mean','The first histogram is a sample from a normal distribution'),
 (10,'The first histogram','median','-0.010','median','The first histogram is a sample from a normal distribution'),
 (10,'The first histogram','mode','- 0.144','stated_value','The first histogram is a sample from a normal distribution'),
 (10,'The second histogram','mean','1.001','mean','The second histogram is a sample from an exponential distribution'),
 (10,'The second histogram','median','0.684','median','The second histogram is a sample from an exponential distribution'),
 (10,'The second histogram','mode','0.254','stated_value','The second histogram is a sample from an exponential distribution'),
 (10,'The full Cauchy data set','minimum','-29,000','bound','The full Cauchy data set in fact'),
 (10,'The full Cauchy data set','maximum','89,000','bound','The full Cauchy data set in fact'),
 (10,'this histogram','mean','3.7','mean','For this histogram'),
 (10,'The fourth histogram','mean','1.677','mean','The fourth histogram is a sample from a lognormal distribution'),
 (10,'The fourth histogram','median','0.989','median','The fourth histogram is a sample from a lognormal distribution'),
 (10,'The fourth histogram','mode','0.680','stated_value','The fourth histogram is a sample from a lognormal distribution')]:
 # Property cues are locally located after the referent, preventing equal-spelling merges.
 M(n,ref,prop,value,role,condition=cond,unc='approximately' if value in ('-29,000','89,000') else None)
M(10,'This plot','random numbers','10,000','count',condition='generated from a normal, an exponential, a Cauchy, and a lognormal distribution',after='Exponential Distribution ')
M(10,'the confidence intervals for the population location','chance','95%',condition='regardless of what the underlying distribution is')
M(10,'the points','trim','5%',condition='A common choice is to trim 5% of the points in both the lower and upper tails')
M(11,'many samples','contain the true mean','95 %',condition='for a 95 %\nconfidence interval, if many samples are collected and the confidence interval computed, in\nthe long run about 95 % of these intervals would contain the true mean',unc='about',after='That is, for a 95 %')
M(11,'Significance Level','value','0.05',condition='The most commonly used value for is 0.05')
M(11,'ZARR13.DAT data set','N','195','count',condition='We generated a 95 %, two-sided confidence interval for the ZARR13.DAT data set')
M(11,'ZARR13.DAT data set','MEAN','9.261460','mean',condition='We generated a 95 %, two-sided confidence interval for the ZARR13.DAT data set')
M(11,'ZARR13.DAT data set','STANDARD DEVIATION','0.022789','dispersion',condition='We generated a 95 %, two-sided confidence interval for the ZARR13.DAT data set')
M(11,'ZARR13.DAT data set','t1-0.025,N-1','1.9723',condition='We generated a 95 %, two-sided confidence interval for the ZARR13.DAT data set')
M(11,'the mean','confidence interval','(9.258242, 9.264679)','bound',condition='Thus, a 95 % confidence interval for the mean is (9.258242, 9.264679)')
M(11,'the population mean','equal to','5',condition='the null hypothesis that the population mean is equal to 5')
M(11,'ZARR13.DAT data set','Test statistic','2611.284',condition='We performed a two-sided, one-sample t-test using the ZARR13.DAT data set')
M(11,'ZARR13.DAT data set','Degrees of freedom','194','count',condition='We performed a two-sided, one-sample t-test using the ZARR13.DAT data set')
M(11,'ZARR13.DAT data set','Significance level','0.05',condition='We performed a two-sided, one-sample t-test using the ZARR13.DAT data set')
M(11,'ZARR13.DAT data set','Critical value','1.9723',condition='We performed a two-sided, one-sample t-test using the ZARR13.DAT data set')
M(11,'the critical value','t1-α,v','1.6527',condition='If we were to perform an upper, one-tailed test')

# Clausal propositions selected by reading every native text item. No scientific correction.
A(2,'all outcomes of an experiment','are','equally likely',condition='in many cases, we assume that',quant='all')
A(2,'it','is not possible','to have an experiment which is uniform on this set',condition='If the sample space is a countably infinite set, such as the set of positive integers',pol='negative')
A(2,'we','use','continuous density functions',condition='If the sample space is an uncountable set, with positive, finite length, such as the interval [0, 1]')
A(2,'the binomial distribution','is well-approximated by','the corresponding normal density function',condition='Whennis relatively large (say at least 30)')
A(2,'This method','requires','ncalls to a random number generator to obtain one value of the random variable')
A(2,'we','can determine','the distribution for any random variableXrelating to the experiment',condition='providedP(X=a) can be computed in terms of a finite number of trials',mod='possible')
A(2,'we','are more likely','to get large values for T',condition='as p decreases',mod='probable')
A(2,'the most probable\nvalue for T','is','1',condition='In both cases')
A(2,'Y','is','geometrically distributed with parameterp',after='Then we have')
A(2,'log(1-rnd) and log(rnd)','are','identically distributed')
A(2,'the timeTuntil the next arrival','has','a geometric distribution',condition='It is often assumed that, in each small time unit, either 0 or 1 new customers arrive at the counter')
A(2,'arrivals in any two time units','are','independent events')
A(2,'the length of time required to service a customer','has','a geometric distribution but with a different value forp',condition='It is often assumed that')
A(2,'the probability that the customer’s service takessmore time units','is independent of','the length of timerthat the customer has already been served',condition='It is often assumed that the length of time required to service a customer also has a geometric distribution')
A(2,'X','is','geometrically distributed',condition='Whenk=1',after='letXrepresent')
A(2,'there','were','exactlyk-1 heads thrown in the firstx-1 tosses',condition='IfX=x',mod=('required','must be true'))
A(2,'a head','must have been thrown','on the _x_th toss',condition='IfX=x',mod='required')
A(2,'X','can be understood as','the sum ofkoutcomes of a geometrically distributed experiment with parameterp',after='One can simulate this',mod='possible')
A(2,'the distribution','is','quite asymmetric, with a long tail reflecting the fact that large values ofxare possible',after='In Figure 5.2')
A(2,'The Poisson distribution','can be viewed as','arising from the binomial distribution or from the exponential density',mod='possible')
A(2,'the average rate, i.e., the average number of occurrences per minute','is','a constant',condition='we must assume that')
A(2,'the number of occurrences in two non-overlapping time intervals','are','independent',condition='Our next assumption is that')
A(2,'two or more occurrences','happen','in one subinterval with a probability which is negligible in comparison with the probability of at most one occurrence',condition='If the subintervals are sufficiently short, we can assume that')
A(2,'the sequence of subintervals','can be thought of as','a sequence of Bernoulli trials, with a success corresponding to an occurrence in the subinterval',mod='possible')
A(2,'The Poisson distribution','is used as','an approximation to the binomial distribution',condition='when the parameters n and p are large and small, respectively')
A(4,'Joint probability statements','can be made about','a combination of variates, all having continuous domain, all having countable domain, or some combination of continuous and countable domains',mod='possible')
A(4,'both conditions X ≤ x and Y ≤ y','hold','simultaneously')
A(4,'ℜ α X,Y','is','the line segment [0, 1]',condition='When X and Y are jointly continuous')
A(4,'ℜ α X,Y','may be','a subset of [0, 1]',condition='In all other cases',mod='possible',after='In all other cases,')
A(4,'The function F(x, y)','is','nondecreasing in each of x and y')
A(4,'The function F(x, y)','attains','a value of unity',condition='when both x and y are at their respective maxima')
A(4,'the probability associated with an arbitrary bivariate quantile set A','is equal to','the area under the bivariate pdf surface A')
A(4,'A discrete bivariate (X, Y )','takes','discrete values (x, y) with finite probabilities f (x, y)')
A(5,'each one','consistent with','the corresponding bivariate entity')

# Native split phrase is preserved, but contaminated intervening words are not silently repaired.
LIMITS[6].append(dict(pointer='#/texts/53',family='assertion',disposition='unresolved',reason='Joint pdf product clause is interrupted by displaced marginal-pf text; unreconstructed intended object is not asserted as literal source.'))
A(6,'the joint pf for a discrete bivariate with independent discrete univariate elements','may be decomposed into','the product of the marginal pfs',mod='possible')
A(7,'Joint, marginal, and conditional probabilities','satisfy','the property of composition')
A(7,'joint probabilities','may be determined by','the product of marginal probabilities and the appropriate conditional probability',mod='possible')
A(7,'Equation (4.1)','holds','whether the variables are dependent or independent')
A(7,'f (y|x)','=','f (y)',condition='if X and Y are independent')
A(7,'f (x|y)','=','f (x)',condition='if X and Y are independent')
A(7,'These conditional probabilities associated with the univariate X given Y = 0','are not','the same as those obtain by conditioning on a value of Y = 1',pol='negative')
A(7,'composition','may be used','to reconstruct the joint probabilities for (X, Y)',mod='possible')
A(8,'the terms denoted by f(·) in Equation (4.2)','relate to','marginal and conditional pdfs',condition='For a continuous bivariate')
A(8,'these terms','relate to','marginal and conditional pfs',condition='for a discrete bivariate')
A(8,"Using Bayes' theorem in Equation (4.2)",'relates','the conditional probability Pr[X = x|Y = y] to the conditional probability Pr[Y = y|X = x]')
A(9,'ψ(xX, xY )','is','a random number of ψ(X, Y)',condition='If (X,Y) is a bivariate with range ℜX,Y and ψ is a functional mapping from ℜX,Y into the real line, then ψ(X, Y) is a variate such that if xX and xY are random numbers of X and Y, respectively')
A(9,'the characteristic function of the sum of two independent variates','is','the product of the characteristic functions of the individual variates')
A(9,'X1 +X2','is not','the same as 2X1',condition='even though X1 ∼ X2',pol='negative')
A(9,'The term X1 +X2','is','a variate for which a random number can be obtained by choosing a random number of X1 and then another independent random number of X2 and then adding the two')
A(9,'The term 2X1','is','a variate for which a random number can be obtained by choosing a single random number of X1 and multiplying it by two')
A(9,'the distribution of each X variate','is governed by','the same set of parameters, (a, b)',condition='If there are n such independent variates of the form (X : a, b) to be summed')
A(10,'It','is not','necessarily unique',after='the mode is the value',pol='negative')
A(10,'The mode','is typically used','in a qualitative fashion')
A(10,'any specific value','may not occur','more than once',condition='if the data are continuous',pol='negative',mod='possible')
A(10,'The normal distribution','is','a symmetric distribution with well-behaved tails and a single peak at the center of the distribution')
A(10,'it','behaves','the same to the left and right of some center point')
A(10,'the mean, median, and mode','are','actually equivalent',condition='For a normal distribution')
A(10,'The histogram above','generates','similar estimates for the mean, median, and mode')
A(10,'it','is reasonable','to use the mean as the location estimator',condition='if a histogram or normal probability plot indicates that your data are approximated well by a normal distribution')
A(10,'The exponential distribution','is','a skewed, i. e., not symmetric, distribution')
A(10,'the mean and median','are not','the same',condition='For skewed distributions',pol='negative')
A(10,'The mean','will be pulled','in the direction of\nthe skewness')
A(10,'the mean','will be','greater than the median',condition='if the right tail is heavier than the left tail')
A(10,'the mean','will be','less than the median',condition='if the left tail is heavier than the right tail')
A(10,'all three measures','are','useful',condition='For skewed distributions')
A(10,'The Cauchy distribution','is','a symmetric distribution with heavy tails and a single peak at the center of the distribution')
A(10,'collecting more data','does not provide','a more accurate estimate of the mean',pol='negative')
A(10,'the sampling distribution of the mean','is equivalent to','the sampling distribution of the original data')
A(10,'the mean','is','useless as a measure of the typical value',condition='for the Cauchy distribution')
A(10,'the mean of 3.7','is','well above the vast majority of the data',condition='For this histogram')
A(10,'the median','does provide','a useful measure for the typical value')
A(10,'Extreme values in the tails','distort','the mean')
A(10,'these extreme values','do not distort','the median',condition='since the median is based on ranks',pol='negative')
A(10,'the median','provides','a better estimate of location than does the mean',condition='In general, for data with extreme values in the tails')
A(10,'The lognormal','is also','a skewed distribution')
A(10,'the mean and median','do not provide','similar estimates for the location',pol='negative')
A(10,'the mean','is','an optimal estimator',condition='if in fact your data are normal')
A(10,'The mean','is','an example of an estimator that is the best we can do',condition='if the underlying distribution is normal')
A(10,'it','lacks','robustness of validity',after='The mean is an example')
A(10,'confidence intervals based on the mean','tend not to be','precise',condition='if the underlying distribution is in fact not normal',pol='negative')
A(10,'The median','is','an example of a an estimator that tends to have robustness of validity but not robustness of efficiency')
A(10,'the confidence intervals for the case when the data are normal','should be','almost as narrow as the confidence intervals based on the mean',mod='required')
A(10,'they','should maintain','their validity',condition='even if the underlying data are not normal',mod='required')
A(10,'these alternatives','address','the problem of heavy-tailed distributions')
A(10,'all data below the 5th percentile','are set equal to','the value of the 5th percentile',condition='For example',quant='all')
A(10,'all data greater than the 95th percentile','are set equal to','the 95th percentile',condition='For example',quant='all')
A(10,'they','are not unduly affected by','extremes in the tails',after='The first three alternative location estimators',pol='negative')
A(10,'they','generate','estimates that are closer to the mean',condition='for data that are normal (or nearly so)',after='The first three alternative location estimators')
A(10,'The mid-range','is not','robust',condition='since it is based on the two most extreme points',pol='negative')
A(10,'Its use','is typically restricted to','situations in which the behavior at the extreme points is relevant')
A(11,'Interval estimates','are often','desirable',condition='because the estimate of the mean varies from sample to sample')
A(11,'a confidence interval','generates','a lower and upper limit for the mean')
A(11,'The interval estimate','gives','an indication of how much uncertainty there is in our estimate of the true mean')
A(11,'The narrower the interval','the more precise is','our estimate')
A(11,'Confidence limits','are expressed','in terms of a confidence coefficient')
A(11,'90 %, 95 %, and 99 % intervals','are\noften used','with 95 % being the most commonly used')
A(11,'a 95 % confidence interval','doesnotmean','that there is a 95 % probability\nthat the interval contains the true mean',pol='negative')
A(11,'The interval computed from a given sample','either\ncontains','the true mean or it does not')
A(11,'the level of confidence','is associated with','the\nmethod of calculating the interval')
A(11,'the interval','gets','narrower from the V term',condition='As N increases')
A(11,'one way to obtain more precise estimates for the mean','is','to increase the sample\nsize')
A(11,'noisy data, i.e., data with a large standard deviation','are going to generate','wider intervals than data with a smaller standard deviation')
A(11,'the confidence coefficient','is','1 - α')
A(11,'the confidence interval','is converted to','hypothesis-test form',condition='To test whether the population mean has a specific value, , against the two-sided alternative that it does not have a value ,')
A(11,'We','reject','the null hypotheses for our two-tailed t-test',condition='because the absolute value of the test\nstatistic is greater than the critical value')
A(11,'we','would still reject','the null hypothesis',condition='If we were to perform an upper, one-tailed test')
A(11,'The confidence interval','provides','an alternative to the hypothesis test')
A(11,'H0','cannot be rejected','',condition='If the confidence\ninterval contains 5',pol='negative') if False else None
A(11,'the confidence interval\n(9.258242, 9.264679)','does not contain','5',condition='In our example',pol='negative')
A(11,'the population mean','does not equal','5',condition='at the 0.05 level of significance',pol='negative')
A(11,'Confidence intervals for other location estimators such as the median or mid-mean','tend to be','mathematically difficult or intractable')
A(11,'confidence intervals','can be obtained','using the bootstrap',condition='For these cases',mod='possible')
# Formula binding judgments map individual occurrences to their explicit local declarations.
# The automatic part only locates the FIRST exact use of each authored symbol in that formula.
def Formula(n,p,bindings=(),domain=None,assumption=None):
 a,b=ptrspan(n,p);f=text(n)[a:b]
 if not bindings:
  vv=dict(formula=lit((a,b)),scope=nat(V(n)['section_pointer']))
  if domain:vv['domain']=lit(domain)
  if assumption:vv['assumption']=lit(assumption)
  record(n,'formula_context',vv,('formula',),context=p);return
 for symbol,meaning in bindings:
  protected=[m.span() for m in re.finditer(r'\\[A-Za-z]+|\\(?:begin|end)\{[^}]+\}',f)]
  # TeX command names and environment names are not symbol uses.
  protected += [m.span() for m in re.finditer(r'\\(?:begin|end)\{[^}]+\}',f)]
  matches=[m for m in re.finditer(re.escape(symbol),f) if not any(lo<=m.start()<hi for lo,hi in protected) or f[m.start():m.end()]==symbol and symbol.startswith('\\')]
  match=matches[0] if matches else None
  if not match:
   LIMITS[n].append(dict(pointer=p,family='formula_context',disposition='unresolved',symbol=symbol,reason='Declared binding has no exact primary in-formula spelling; transformed/macro glyph cannot be invented.'));continue
  v=dict(formula=lit((a,b)),scope=nat(V(n)['section_pointer']),symbol=lit((a+match.start(),a+match.end())),meaning=lit(meaning))
  if domain:v['domain']=lit(domain)
  if assumption:v['assumption']=lit(assumption)
  record(n,'formula_context',v,('formula','symbol'),context=p)

nmeaning='size';pmeaning='the probability that a head occurs';Tmeaning='the number of trials up to and including the first success';qmeaning='1-p'
map2={
255:[('n',nmeaning)],257:[('m','the distribution function')],259:[('S','the sample space')],5:[('n',nmeaning)],267:[('\\lfloor x\\rfloor','the greatest integer not exceedingx')],
309:[('n','a coin is tossedntimes'),('p',pmeaning),('q',qmeaning)],328:[('n','a coin is tossedntimes'),('p',pmeaning),('q',qmeaning)],332:[('Y','a normal random variable with these parameters'),('n','a coin is tossedntimes')],334:[('Y','a normal random variable with these parameters')],
357:[('T',Tmeaning),('p',pmeaning),('q',qmeaning)],359:[('T',Tmeaning),('p',pmeaning),('q',qmeaning)],360:[('p','first term p'),('q','common\nratio q')],276:[('p','first term p'),('q','common\nratio q')],283:[('T',Tmeaning),('q',qmeaning)],290:[('T',Tmeaning),('p',pmeaning),('q','1 −p')],
293:[('Y','the smallest integer satisfying the inequality'),('q','1 −p')],296:[('Y','the smallest integer satisfying the inequality'),('q','1 −p'),('p',pmeaning)],124:[('Y','the smallest integer satisfying the inequality'),('q','1 −p')],127:[('\\lceil x\\rceil','the least integer which is greater than or equal tox')],137:[('Y','the smallest integer satisfying the inequality'),('q','1 −p')],
155:[('T','the timeTuntil the next arrival'),('k','time units'),('p','The probability that a customer arrives'),('q','that no customer arrives')],169:[('T','service time'),('r','the length of timerthat the customer has already been served'),('s','more time units')],
20:[('k','a positive integer'),('x','tosses')],204:[('p','probabilitypof coming up heads'),('k','a positive integer'),('x','tosses')],205:[('X','the number of tosses'),('p','probabilitypof coming up heads'),('k','a positive integer'),('x','tosses')],206:[('k','a positive integer'),('x','tosses')],217:[('k','a positive integer'),('q',qmeaning)],229:[('x','tosses')],
365:[('t','a time interval of lengtht')],373:[('t','a time interval of lengtht'),('n','subintervals'),('p','the probability of an occurrence in a given subinterval')],374:[('p','the probability of an occurrence in a given subinterval'),('t','a time interval of lengtht'),('n','subintervals')],
383:[('X','the number of occurrences in a given time interval'),('n','subintervals'),('p','the probability of an occurrence in a given subinterval')],392:[('n','subintervals'),('p','the probability of an occurrence in a given subinterval'),('q',qmeaning)],
401:[('X','the number of occurrences in a given time interval')],403:[('X','the number of occurrences in a given time interval')],79:[('j','hits')]
}
LIMITS[2].append(dict(pointer='#/texts/206',family='formula_context',disposition='unresolved',reason='Source contains \\p^k rather than a plain p use; no p first-use binding is asserted. Exact k/x readings are retained.'))
for p,x in items(2).items():
 if x.get('label')!='formula':continue
 i=int(p.rsplit('/',1)[1])
 if i in (244,437,87,111):continue # end-of-example furniture
 if i in (60,109,62):
  LIMITS[2].append(dict(pointer=p,family='formula_context',disposition='unrepresentable',reason='Isolated formula fragment/operator; neighboring original numbers are separate native items. Entire expression is not a single native formula occurrence.'));continue
 if i==326:
  LIMITS[2].append(dict(pointer=p,family='formula_context',disposition='unresolved',reason='Formula \\mu=\\np has a fused macro; n/p binding first use cannot be located honestly.'));continue
 bindings=map2.get(i,())
 if i in (309,328):bindings=[z for z in bindings if z[0]!='q']
 if i in (357,359,290,296):bindings=[z for z in bindings if z[0]!='p']
 if '\\lambda' in x['text']:
  LIMITS[2].append(dict(pointer=p,family='formula_context',disposition='unresolved',reason='Local rate declaration uses λ while formula uses \\lambda. No transformed glyph binding is invented; exact other bindings remain.'))
  if not bindings:continue
 Formula(2,p,bindings,domain='for j = 1, 2, 3, .....' if i==290 else None,assumption='assuming that on any one toss, the probability that a head occurs isp' if i==309 else 'Whennis relatively large (say at least 30)' if i in (328,332,334) else None)

map4={19:[('F','The distribution function'),('x','a bivariate quantile'),('y','a bivariate quantile')],23:[('F','The distribution function'),('f','a bivariate probability density function')],25:[('f','a bivariate probability density function'),('F','The distribution function')],27:[('A','an arbitrary bivariate quantile set'),('f','a bivariate probability density function')],34:[('F','joint distribution function')]}
for i,bindings in map4.items():Formula(4,f'#/texts/{i}',bindings,assumption='When (X, Y) have a jointly continuous probability domain' if i in (23,25,27) else None)
for i in (40,45):LIMITS[5].append(dict(pointer=f'#/texts/{i}',family='formula_context',disposition='unresolved',reason='Distinct marginal and joint f bindings have argument-dependent identities and transformed TeX spellings; bare f first-use cannot arbitrarily identify both.'))
for i in (47,48):LIMITS[5].append(dict(pointer=f'#/texts/{i}',family='formula_context',disposition='unresolved',reason='Distinct marginal and joint f bindings have argument-dependent identities and transformed TeX spellings; bare f first-use cannot arbitrarily identify both.'))
LIMITS[6].append(dict(pointer='#/texts/55',family='formula_context',disposition='unresolved',reason='Joint and marginal f bindings are overloaded by arguments; nearby interrupted joint-pdf clause and pf clause offer different domains. No arbitrary bare f binding is chosen.'))
Formula(7,'#/texts/58',assumption='provided the denominator Pr[Y ≤ y] is nonzero')
for i in (62,64,66,68,74,76):LIMITS[7].append(dict(pointer=f'#/texts/{i}',family='formula_context',disposition='unresolved',reason='Conditional, joint and marginal f bindings are explicitly distinguished by their arguments, whose native TeX and declaration spellings differ. Bare repeated f is not sufficient binding association; no arbitrary binding or formula-only fallback.'))
for i in (72,79,81,83,84,87,89):Formula(7,f'#/texts/{i}')
LIMITS[8].append(dict(pointer='#/texts/93',family='formula_context',disposition='unresolved',reason='One f occurrence has explicit continuous-pdf and discrete-pf conditional readings. The submitted shape cannot accept two interpretations of the same occurrence, and independent field alternatives cannot express their paired meaning/assumption association; no branch is arbitrarily selected.',readings=[dict(symbol='f',meaning='marginal and conditional pdfs',assumption='For a continuous bivariate'),dict(symbol='f',meaning='marginal and conditional pfs',assumption='for a discrete bivariate')]))
Formula(8,'#/texts/97')
Formula(9,'#/texts/103')
Formula(9,'#/texts/107',[('Z','X + Y')],assumption='where X ∼ Y')
Formula(9,'#/texts/110',[('i','the ith variate'),('n','independent variates')],domain='for i = 1, 2, . . . n',assumption='If there are n such independent variates of the form (X : a, b) to be summed')
Formula(9,'#/texts/113',[('i','the ith variate')],assumption='When the variates to be summed differ in their parameters')
for i in (124,133,134):
 Formula(10,f'#/texts/{i}',assumption='if N is odd' if i==133 else 'if N is even' if i==134 else None)
# NIST confidence interval is recovered as native text, with an incompatible Y/Y-bar declaration.
Formula(11,'#/texts/111',[('s','the sample standard deviation'),('N','the sample size'),('α','the\ndesired significance level')])
LIMITS[11].append(dict(pointer='#/texts/111',family='formula_context',disposition='unresolved',reason='Formula Y differs from declaration Ȳ; t1-α/2,N−1 differs from declaration t1-α/2, N-1. No transformed-symbol binding or equality is manufactured. Other exact s,N,α bindings retained.'))
for i in (76,79,80,84,85):
 if i==80:
  Formula(11,f'#/texts/{i}',[('s','the sample standard deviation'),('N','the sample size')]);LIMITS[11].append(dict(pointer=f'#/texts/{i}',family='formula_context',disposition='unresolved',reason='T statistic has Y −A0 while declaration omits those symbols; undeclared bindings not reconstructed.'))
 else:Formula(11,f'#/texts/{i}')
def descendants(n,p):
 ans={p}
 for c in items(n).get(p,{}).get('children',[]):ans.update(descendants(n,c['$ref']))
 return ans

def cellrange(n,table,idx):
 cell=items(n)[table]['data']['table_cells'][idx];ref=cell.get('ref',{}).get('$ref');ds=descendants(n,ref) if ref else set()
 pp=[p for p in V(n)['projection']['pieces'] if (p.get('item_ref')==table and p.get('cell_index')==idx) or p.get('item_ref') in ds]
 if not pp:return None
 return min(p['start'] for p in pp),max(p['end'] for p in pp)

# Header paths and labels are separately read from actual native cells, never parser flags alone.
for n in (2,11):
 table='#/tables/0';cells=items(n)[table]['data']['table_cells']
 for idx,c in enumerate(cells):
  row,col=c['start_row_offset_idx'],c['start_col_offset_idx'];ptr=f'{table}/data/table_cells/{idx}'
  if row==0:continue
  if n==2 and col==0:
   LIMITS[n].append(dict(pointer=ptr,family='table',disposition='unrepresentable',literal=c['text'],reason='Row index is explicit, but its column has a blank header; required literal header_path cannot be honestly stated.'));continue
  if not c['text']:
   LIMITS[n].append(dict(pointer=ptr,family='table',disposition='unresolved',literal='',reason='Blank native data cell; no source legend gives blank a numeric/state meaning and exact empty literal is not representable.'));continue
  head=next(i for i,h in enumerate(cells) if h['start_row_offset_idx']==0 and h['start_col_offset_idx']==col)
  cr=cellrange(n,table,idx);hr=cellrange(n,table,head)
  assert cr and hr,(n,idx)
  v=dict(table=nat(table),cell=nat(ptr),header_path=lit(hr),cell_value=lit(cr))
  if col>0:
   ridx=next(i for i,c0 in enumerate(cells) if c0['start_row_offset_idx']==row and c0['start_col_offset_idx']==0)
   v['row_label']=lit(cellrange(n,table,ridx))
  if n==2:v['caption']=lit('Table 5.1: Poisson approximation to the binomial distribution.')
  record(n,'table',v,('table','cell'),context=table)
# Forbes printed arrays are headerless native tables. Keep table-family limitation per cell.
for n,table in ((4,'#/tables/0'),(5,'#/tables/1'),(5,'#/tables/2')):
 for idx,c in enumerate(items(n)[table]['data']['table_cells']):
  LIMITS[n].append(dict(pointer=f'{table}/data/table_cells/{idx}',family='table',disposition='unrepresentable',literal=c['text'],reason='Inspected native equation array has no header; required header_path is unavailable. Equation/probability source content remains eligible separately.'))
# Explicit numerical results in the Forbes arrays, no recomputation.
for idx,c in enumerate(items(4)['#/tables/0']['data']['table_cells']):
 a,b=cellrange(4,'#/tables/0',idx);s=text(4)[a:b];lhs,rhs=s.rsplit(' = ',1)
 M(4,lhs,'Pr',rhs,condition='Consider the discrete bivariate (X, Y) with joint distribution function given by')
 for symbol in ('X','Y'):
  k=text(4).index(symbol,a,b)
  record(4,'formula_context',dict(formula=lit((a,b)),scope=nat(V(4)['section_pointer']),symbol=lit((k,k+1)),meaning=lit('two variates')),('formula','symbol'),context='#/tables/0')
for table,rows in [('#/tables/1',[(0,4),(5,9),(10,14)]),('#/tables/2',[(0,4),(5,9)])]:
 for left,right in rows:
  l=cellrange(5,table,left);r=cellrange(5,table,right);assert l and r
  lhs=text(5)[l[0]:l[1]];rhs=text(5)[r[0]:r[1]]
  M(5,lhs,'Pr',rhs,condition='Continuing Example 4.1.1')
  aa,bb=l[0],r[1];symbol='X' if table.endswith('/1') else 'Y';k=text(5).index(symbol,aa,bb)
  record(5,'formula_context',dict(formula=lit((aa,bb)),scope=nat(V(5)['section_pointer']),symbol=lit((k,k+1)),meaning=lit('the univariate X' if symbol=='X' else 'the univariate Y')),('formula','symbol'),context=table)

exec((ROOT/'supplement.py').read_text(),globals())

# Full source-region coverage, preserving all native chart cells even though their exact scopes are unreleased.
coverage=[]
for n,d in sorted(UNITS.items()):
 v=V(n)
 inspected=[]
 for ptr,x in items(n).items():
  row=dict(pointer=ptr,label=x.get('label'),inspected=True)
  if ptr.startswith('#/groups/'):
   row['disposition']='native structural scope inspected'
  elif 'data' in x:
   row.update(disposition='all native cells inspected',cells=[dict(pointer=f'{ptr}/data/table_cells/{i}',literal=c.get('text',''),row=c['start_row_offset_idx'],column=c['start_col_offset_idx'],column_header=c.get('column_header'),row_header=c.get('row_header')) for i,c in enumerate(x['data']['table_cells'])])
  elif ptr.startswith('#/pictures/'):
   chart=x.get('meta',{}).get('tabular_chart',{})
   if chart:
    row.update(disposition='unsupported exact chart coordinates',native_chart=chart)
    LIMITS[n].append(dict(pointer=ptr,families=['table','measurement','formula_context'],disposition='unsupported',reason='Frozen native chart title/cells inspected, but release has no exact chart anchor scopes. No invented table addresses or chart numeric readings.',source_payload=chart))
   else:row['disposition']='native picture inspected; no independently readable frozen image payload; no invented visual content'
  else:
   row['literal']=x.get('text','');row['disposition']='inspected text; compare authored role anchors and limitations'
   if not row['literal']:row['disposition']='genuinely empty native text item'
   elif x.get('label') in ('section_header','page_header','page_footer','footnote'):row['disposition']='heading, page furniture or bibliographic footnote; no independent statistical reading'
   elif x.get('text')=='\\sqcap\\sqcup':row['disposition']='end-of-example furniture'
  row['accepted_families']=sorted({rec['family'] for rec in OUT[n] if any(a['pointer']==ptr or a['pointer'].startswith(ptr+'/data/') for a in rec['anchors'] if a['space']=='selected_projection')})
  row['limitation_families']=sorted({lim.get('family','chart_content') for lim in LIMITS[n] if lim['pointer']==ptr or lim['pointer'].startswith(ptr+'/data/')})
  inspected.append(row)
 counts=dict(collections.Counter(r['family'] for r in OUT[n]))
 coverage.append(dict(unit_id=n,unit_ref=d['unit_ref'],source_section=v['section_pointer'],all_five_families_inspected=['definition','assertion','measurement','table','formula_context'],no_output_reason='Only a chapter/title heading; all five families ineligible here.' if n in (1,3) else None,source_health=v['projection']['health'],items=inspected,accepted_counts=counts,limitations=LIMITS[n]))

def dump(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
for n,d in sorted(UNITS.items()):
 batch=dict(protocol='source-record-reference-1',release_id=d['release_id'],unit_ref=d['unit_ref'],guideline=d['guideline'],reference_policy_version='statistics-reference-reading-3',prediction_policy_version='m1-grouped-reading-logistic-1',reason='Independent A-v3 source-only reading of every frozen native item and all five families; unresolved and unsupported readings retained in coverage.json. Quoted source values are not verified scientific claims.',records=OUT[n])
 dump(ROOT/f'unit-{n}.json',batch)
dump(ROOT/'coverage.json',dict(protocol='independent-source-census-A-v3',guideline='statistics-m1-reference-3',release_id=UNITS[1]['release_id'],units=coverage))
inputs={str(p.relative_to(F)):hashlib.sha256(p.read_bytes()).hexdigest() for p in F.rglob('*') if p.is_file()}
outputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.glob('*.json')) if p.name!='manifest.json'}
dump(ROOT/'manifest.json',dict(actor='gpt-6.1-sol-high-A-v3',session_name='/root/m1_reference_a_v3',model='gpt-6.1-sol',reasoning_effort='high',date='2026-11-04',release_id=UNITS[1]['release_id'],inputs=inputs,outputs=outputs,production_predictions_read=False,other_authors_read=False,platform_execution_id=None,counts={str(n):dict(collections.Counter(r['family'] for r in OUT[n])) for n in sorted(UNITS)}))
print(json.dumps({n:dict(collections.Counter(r['family'] for r in rs)) for n,rs in sorted(OUT.items())},indent=2))
