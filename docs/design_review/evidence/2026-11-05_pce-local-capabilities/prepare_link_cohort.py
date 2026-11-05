"""Fresh source-only development questions; never read predictions or old judgments."""
import json
import re
from hashlib import sha256
from pathlib import Path

HERE = Path(__file__).resolve().parent
source = HERE.parent / '2026-11-05_pce-foundations/raw/source-only-unit-2-002.json'
data = json.loads(source.read_bytes())
items = data['native_contexts'][0]['native_items']
# Independently curated input inventory: these descriptions are candidate inputs,
# not source-grounded assertions, reference answers, or canonical identities.
entries = [
 ('discrete_uniform','Discrete uniform distribution','Equal probability for each outcome in a finite set.'),
 ('continuous_uniform','Continuous uniform distribution','Constant probability density on a bounded interval.'),
 ('binomial','Binomial distribution','Number of successes in a fixed number of independent Bernoulli trials.'),
 ('negative_binomial','Negative binomial distribution','Count or waiting time associated with reaching a fixed number of successes.'),
 ('geometric','Geometric distribution','Discrete waiting time until a first success, with a declared counting convention.'),
 ('poisson','Poisson distribution','Discrete nonnegative count model with a rate parameter.'),
 ('bernoulli','Bernoulli trial','A single success or failure experiment with a success probability.'),
 ('exponential','Exponential density','Continuous waiting-time density with a rate parameter.'),
 ('normal','Normal distribution','Gaussian location-scale family with mean and variance parameters.'),
 ('standard_normal','Standard normal distribution','The normal distribution with mean zero and variance one.'),
 ('gamma','Gamma distribution','Positive continuous shape-and-rate or shape-and-scale family.'),
 ('beta','Beta distribution','Continuous distribution on the unit interval with two shape parameters.'),
 ('chi_squared','Chi-squared distribution','Distribution of a sum of squared independent standard normal variables.'),
 ('student_t','Student t distribution','Symmetric continuous family indexed by degrees of freedom.'),
 ('central_limit','Central Limit Theorem','A theorem about standardized sums approaching a normal limit under its assumptions.'),
 ('random_variable','Random variable','A measurable numerical function of an outcome.'),
 ('mass_function','Probability mass function','Probabilities assigned to individual values of a discrete random variable.'),
 ('cdf','Cumulative distribution function','Probability that a random variable is at most the argument.'),
 ('hypergeometric','Hypergeometric distribution','Success count in sampling without replacement from a finite population.'),
 ('large_numbers','Law of Large Numbers','Convergence of averages under stated assumptions.'),
]
selected = ['#/texts/25','#/texts/35','#/texts/42','#/texts/140','#/texts/148','#/texts/166','#/texts/193','#/texts/325']
cases = []
pattern = re.compile(r'Poisson distribution|binomial distribution|exponential density|geometric distribution|negative binomial distribution|Central Limit Theorem|normal density function', re.I)
for pointer in selected:
    text = items[pointer]['text']
    for match in pattern.finditer(text):
        cases.append(dict(case_id=f'context-{len(cases)+1}', pointer=pointer, text=text,
                          start=match.start(), end=match.end(), mention=match.group(),
                          question='Which curated target(s) does this exact usage denote? Separately identify any relation explicitly stated between concepts in this passage.'))
packet = dict(protocol='pce-contextual-development-1', source_packet_sha256=sha256(source.read_bytes()).hexdigest(),
              physical_pin=data['source_frame']['evaluation_frame']['pin'],
              scope='Eight declared native text items in retained Chapter5; selected reference mentions, not an exhaustive corpus or discovery frame.',
              inventory=[dict(target_id='statistics:'+key,label=label,description=description) for key,label,description in entries],
              cases=cases, assessor_instructions='Read exact source/context and the candidate input inventory. For every case give permissible target IDs or explain insufficient inventory/context; distinguish explicit relationship kinds, direction and scope from lexical similarity. Do not invent source support from the curated descriptions. Record ambiguity and disagreement reasons. No producer candidates, ranks, vectors or prior judgments are supplied.')
target=HERE/'raw/contextual-source-author-packet-001.json'
with target.open('x') as f:
    json.dump(packet,f,indent=2);f.write('\n')
print(json.dumps(dict(outcome='passed',cases=len(cases),inventory=len(entries),source=packet['source_packet_sha256'],packet=str(target))))
