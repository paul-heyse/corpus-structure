# Additional independent second-read judgments, executed in author.py's namespace.
# Explicit parameters and final source-stated answers in worked examples.
M(2,'Figure 5.1','p','.5',condition='for the cases p = .5 and p = .2')
M(2,'Figure 5.1','p','.2',condition='for the cases p = .5 and p = .2')
M(2,'Figure 5.2','k','2',condition='In Figure 5.2 we give a graph of the distribution fork=2 andp=_._25')
M(2,'Figure 5.2','p','_._25',condition='In Figure 5.2 we give a graph of the distribution fork=2 andp=_._25')
M(2,'S100','Bernoulli trials','100','count',condition='consideringS100as a result of 100 Bernoulli trials')
M(2,'S100','p','1_/1000',condition='consideringS100as a result of 100 Bernoulli trials withp= 1_/1000')
M(2,'Bernoulli trials process','n','400','count',condition='We assume that a particular bomb will hit your square with probability 1/100')
M(2,'Bernoulli trials process','p','1_/100',condition='We assume that a particular bomb will hit your square with probability 1/100')
M(2,'X','parameter','40',condition='Suppose that in a certain fixed amountAof blood, the average human has 40 white blood cells',after='But for the average human')
M(2,'the time interval','length','1',condition='For ease of calculation, we will assume that the time interval is of length 1')
M(2,'the average rate','occurrences','5λ',role='mean',condition='in a given 5-minute time interval',unc='about')
# Each final probability below is explicitly printed in a native formula; no arithmetic oracle.
for ref,val in [
 ('[ X = 0 | Y = 0 ]','2 / 1 1'),('[ X = 1 | Y = 0 ]','6 / 1 1'),('[ X = 2 | Y = 0 ]','3 / 1 1'),
 ('[ X = 0 | Y = 1 ]','2 / 5'),('[ X = 1 | Y = 1 ]','2 / 5'),('[ X = 2 | Y = 1 ]','1 / 5'),
 ('[ Y = 0 | X = 0 ]','1 / 2'),('[ Y = 1 | X = 0 ]','1 / 2'),('[ Y = 0 | X = 1 ]','3 / 4'),
 ('[ Y = 1 | X = 1 ]','1 / 4'),('[ Y = 0 | X = 2 ]','3 / 4'),('[ Y = 1 | X = 2 ]','1 / 4')]:
 M(7,ref,'\\Pr',val,condition='Again continuing Example 4.1.1')
M(9,'[ X = 2 | Y = 0 ]','\\Pr','3 / 1 1')
M(11,'ZARR13.DAT data set','LOWER LIMIT','9.261460 - 1.9723*0.022789/√195','bound',condition='We generated a 95 %, two-sided confidence interval for the ZARR13.DAT data set')
M(11,'ZARR13.DAT data set','UPPER LIMIT','9.261460 + 1.9723*0.022789/√195','bound',condition='We generated a 95 %, two-sided confidence interval for the ZARR13.DAT data set')
M(11,'|T|','>','1.9723','bound',condition='Critical region: Reject H0 if |T| > 1.9723',comp='>')
M(11,'the population mean','level of significance','0.05',condition='In our example, the confidence interval\n(9.258242, 9.264679) does not contain 5')
A(2,'the Poisson distribution','also arises','in situations where it may not be easy to interpret or measure the parameters n and p')
A(2,'The observed frequencies','are shown as','squares',after='In Figure 5.3')
A(2,'the predicted frequencies','are shown as','dots',after='In Figure 5.3')
A(2,'We','can think of','Xas binomially distributed with each white blood cell in the body representing a trial',condition='Suppose that in a certain fixed amountAof blood, the average human has 40 white blood cells',mod='possible',after='Example 5.5')
A(2,'the trial corresponding to that blood cell','was','a success',condition='If a given white blood cell turns up in the sample')
A(2,'it','is easier','to model the situation using the Poisson distribution than the binomial distribution',condition='In this case',after='parameter\\lambda=40')
A(9,'The relationships between the associated functions of X and Y on the one hand and of ψ(X, Y) on the other','are not generally','straightforward',pol='negative')
# Clause split by a displaced formula: preserve actual text pieces; never insert synthetic text.
A(9,'The relationships between the associated functions of X and Y on the one hand and of ψ(X, Y) on the other','must be derived','by analysis of the joint distribution of the variates in question',mod='required')
A(10,'The first histogram','is','a sample from a normal distribution')
A(10,'The second histogram','is','a sample from an exponential distribution')
A(10,'The third histogram','is','a sample from a Cauchy distribution')
A(10,'The fourth histogram','is','a sample from a lognormal distribution')
A(10,'confidence intervals for the population location','tend to be','almost as narrow as the best that could be done',condition='if we knew the true shape of the distributuion')
A(11,'the width of the interval','is controlled by','two factors')
# Native inline formula equalities retain their exact source spellings and declared use.
for n,phrase,bind in [
 (2,'q=1-p',('q','1-p')),(2,'q = 1 −p',('q','1 −p')),
 (2,'p(j)=e-44j/j!',('j','hits')),
 (9,'CX+Y (t) = CX(t)CY (t)',('C','the characteristic function C(t)')),
 (10,'(smallest + largest)/2',None),
 (11,'1 - α',('α','the\ndesired significance level')),
 (11,'|T| > 1.9723',None),
]:
 a,b=span(n,phrase);v=dict(formula=lit((a,b)),scope=nat(V(n)['section_pointer']))
 primary=['formula']
 if bind:
  symbol,meaning=bind;k=text(n).index(symbol,a,b);v.update(symbol=lit((k,k+len(symbol))),meaning=lit(meaning));primary.append('symbol')
 record(n,'formula_context',v,primary)
A(4,'the joint range','is','ℜX,Y = {(0, 0) , (1, 0) , (2, 0) , (0, 1) , (1, 1) , (1, 2)}',condition='As the joint distribution function changes only when x reaches zero, one or two, and when y reaches zero or one')
A(4,'the joint probability domain','is','ℜ α X,Y = { 1 8 , 1 4 , 1 2 , 3 4 , 11 16 , 1}',condition='In this case')
A(5,'The corresponding marginal domain for X','is','ℜX = {0, 1, 2}',condition='Continuing Example 4.1.1')
M(5,'X','marginal probability domain','{1/4, 3/4, 1}',condition='Continuing Example 4.1.1')
A(5,'The corresponding marginal domain for Y','is','ℜY = {0, 1}',condition='Continuing Example 4.1.1')
M(5,'Y','marginal probability domain','{11/16, 1}',condition='Continuing Example 4.1.1')
A(9,'ψ(X, Y)','is','a variate',condition='If (X,Y) is a bivariate with range ℜX,Y and ψ is a functional mapping from ℜX,Y into the real line')
# Continuous-population mode definition is discontinuous across page furniture in the source.
a=span(10,'What may be a more meaningful, if less exact measure, is the midpoint')
b=ptrspan(10,'#/texts/102')
record(10,'definition',dict(term=lit('the mode',after='When taking samples from continuous populations'),defining_text=lit([a,b]),scope=nat(V(10)['section_pointer'])),('term','defining_text'))
LIMITS[11].append(dict(pointer='#/texts/141',family='assertion',disposition='unrepresentable',literal='If the confidence\ninterval contains 5, then H0 cannot be rejected',reason='Explicit intransitive passive proposition has no independently stated object for required subject/predicate/object shape. No synthetic object is supplied.'))
D(2,'T','letTbe the number of trials up to and including the first success',after='For example, ')
D(2,'X','letXrepresent the number of tosses',after='Suppose we are given a coin')
D(2,'S100','LetS100be the number of mistakes that he makes on a single page')
D(2,'X','LetXbe the random variable which gives the number of white blood cells in a random sample of sizeAfrom a random individual',after='Example 5.5')
D(2,'λ','the average rate, i.e., the average number of occurrences per minute')
A(2,'neither of these parameters','is','very easy to measure accurately',after='will be the number of white blood cells')
A(2,'the number 40','is','easy to measure',condition='presumably')
A(2,'One straightforward way to simulate a binomial random variable X','is','to compute the sum ofnindependent 0-1 random variables, each of which take on the value 1 with probabilityp')
A(2,'The distribution for the number of tosses','is','u(x,2,p)',condition='A fair coin is tossed until the second time a head turns up')
A(2,'each of them','is assigned','the same probability, namely\np^{k-1}q^{-x-k}')
A(10,'A fundamental task in many statistical analyses','is','to estimate a location parameter for the distribution; i.e., to find a typical or central value that best describes the data')
A(10,'Most general purpose statistical software programs','can compute','at least some of the measures of location discussed above',mod='possible')
A(10,'The uniform random numbers case study','compares','the performance of several different location estimators for a particular non-normal distribution')
LIMITS[10].append(dict(pointer='#/texts/103',family='measurement',disposition='overlapping_native_duplicate',reason='Repeated 10,000-number caption overlaps #/texts/19 on frozen original page 2: native original text has bottom-left bbox l105.238,t656.706,b619.324; recovered item has top-left bbox l102.816,t133.056,b173.844. Read the original text19 occurrence once rather than inventing an additional original-source observation. Both native items remain inspected.'))
LIMITS[11].append(dict(pointer='#/texts/137',family='measurement',disposition='unresolved_native_overlap',reason='Fragment repeats the complete generated-95%-interval statement at #/texts/87 but has no native page provenance. No additional original occurrence is fabricated from this fragment.'))
