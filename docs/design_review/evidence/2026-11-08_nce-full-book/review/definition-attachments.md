# Grinstead–Snell retained definition attachments

**Measured, 2026-11-08, for the exact reviewed population.** LLM reviewer
`review_middle` examined all 160 indexed retained components in the common
`definitions.jsonl` packet. It identifies the original run, view, physical
page set and component identity for each index. The review compares the term,
attached content, and declared basis with the retained source context shown
for that index. Multiple rows may concern one event or term. This is an
exposed development corpus. The review covers these retained attachments. Missing definitions and
unattached model candidates are separate populations.

A retained source span establishes a location for the text it contains. Term boundaries, semantic roles, and sufficient content require separate
evidence. I used these judgments:

- **D** means the retained pair states a source-supported definition, local
  notation, or independently readable naming equivalence within the shown
  scope.
- **E** means a source-supported example, assignment, naming instance, or
  explanation is present, with narrower meaning than a general definition.
- **P** means the source supports the intended attachment but the retained
  term, content, condition, or capture is materially incomplete.
- **X** means the displayed pair misbinds a term or makes an unsupported
  attachment, including an unrelated source span or a corrupted material claim.
- **U** means the packet is insufficient to settle the pairing.

Basis **Cue** is the matched-cue route, **Geometry** is native geometric
association, and **Model** is a model reading. Cue detection and geometric
placement are mechanisms for selecting candidates. The outcome column is my
semantic judgment. Text described as clipped or corrupted refers to the
retained representation. Native anchor revalidation and expression typography were spot checks.

## Component dispositions

| Index | Basis | Outcome | Source-grounded judgment |
| --- | --- | --- | --- |
| 1 | Cue | E | The four die-roll variables are instances of the named class. The next sentence contains the actual gloss. |
| 2 | Cue | P | The name applies to the displayed mass function, and the retained function token omits its meaning and probability assignment. |
| 3 | Cue | P | Bernoulli Trials names a model for the preceding coin experiment. The attachment retains only the deictic model phrase. |
| 4 | Cue | P | The Monte Carlo name is correct. The content retains only a backward reference to a simulation method. |
| 5 | Cue | D | The possible-outcomes set is the source's sample-space definition. |
| 6 | Cue | X | The candidate treats `each subset` as the term. The source defines an event by its being a subset of the sample space. |
| 7 | Cue | P | The number `P(E)` is introduced, but the component stops before its defining sum. |
| 8 | Geometry | E | The four equal masses assign a distribution in this coin-toss example. |
| 9 | Geometry | X | The equation is for a uniform distribution on a finite sample space. The generic `the function` is a misbound name. |
| 10 | Geometry | P | The explicit three masses belong to the barred `q` on the reduced space. The retained term drops the bar. |
| 11 | Geometry | E | `17/18` is the example's complement probability, tied to the displayed event. |
| 12 | Geometry | P | The geometric assignment is source-backed. The retained pair omits the stated range for `r` and support. |
| 13 | Cue | P | The fallacy name matches, while `this phenomenon` leaves the ranking error unbound. |
| 14 | Geometry | P | The limit is relevant to this exercise's definition. The retained term is clipped, the content trails into garbled prose, and the existence condition is missing. |
| 15 | Cue | P | The source names the density function and explains its area interpretation. The component retains only its symbol. |
| 16 | Geometry | E | `P([0,a])=a²` is a context-specific geometric probability. |
| 17 | Cue | P | The term is valid. Its content is a backward reference and omits the Euclidean-coordinate criterion. |
| 18 | Cue | P | The component loses the relation to a continuous sample space. |
| 19 | Geometry | X | `the dart lands` supplies only part of the event described by the displayed probability integral. |
| 20 | Geometry | X | The attachment confuses the dart-landing event with the separate density `f(r)`. |
| 21 | Geometry | E | The interval-probability integral supports the local explanation. The attached suffix is corrupted. |
| 22 | Cue | P | The class is named, but `These functions` does not supply the subsequent definition. |
| 23 | Geometry | P | The CDF in the example is the intended object. The retained piecewise formula is truncated and ends in recognition noise. |
| 24 | Cue | P | The name is correct. The waiting-time property is only referenced anaphorically. |
| 25 | Cue | E | `λ` names the failure rate in the stated bulb model. |
| 26 | Cue | P | The named reliability probability is valid. The relevant survival event and time threshold are omitted from the content. |
| 27 | Model | X | The preface discusses Markov chains and a probability course. The candidate misbinds these separate preface topics. |
| 28 | Model | X | Cardano's book is a historical reference selected as the meaning of probability. |
| 29 | Model | X | Buffon's formula uses an assumed approximation to `π`. The attachment reverses the use of `π` as an input. |
| 30 | Model | X | The Chapter 1 cross-reference points to a density estimation example. The candidate assigns it to the experiment term. |
| 31 | Cue | D | Rearrangement and permutation are locally interchangeable under the described mapping. |
| 32 | Cue | X | The defined expression is `0!`. The candidate's `The expression` drops the defining symbol. |
| 33 | Cue | P | `RandomPermutation` is the procedure's name, but the selected content omits its steps. |
| 34 | Cue | P | The source names permutations with no fixed point. The attached `such permutations` omits that criterion. |
| 35 | Cue | P | The letter denotes the previously specified circumference. The attachment omits the unit-radius antecedent. |
| 36 | Geometry | X | The term is an exercise-number fragment. The relevant bounds on `n!` also have a garbled attached suffix. |
| 37 | Cue | P | The zero extension is valid only when `j<0` or `j>n`. Omitting both conditions changes its meaning. |
| 38 | Cue | P | The branch-product rule is source-backed. The term drops its closing delimiter and the content loses the path variable. |
| 39 | Cue | P | The distribution is named correctly, but the retained content omits what `B` counts and its Bernoulli parameters. |
| 40 | Cue | P | The claim serves as the alternate hypothesis. The candidate fails to retain the claim's substance. |
| 41 | Cue | D | The local game defines Yin suits exactly as Hearts and Clubs. |
| 42 | Cue | P | The Bayes name matches the inverse conditional probability, but the condition is outside the retained content. |
| 43 | Cue | P | Zero is assigned only to the impossible outcome `(1,0,1)`, which the retained term omits. |
| 44 | Cue | P | The local name is correct. The attachment omits the joint variables and the support that make it informative. |
| 45 | Cue | X | The source defines the joint random vector. The component assigns that definition to its last coordinate `Xn`. |
| 46 | Cue | D | The retained individual-variable distributions give the named marginals' meaning. |
| 47 | Cue | P | The Bayes probabilities are named in the source, but the attached pronoun does not resolve the two-stage conditional relation. |
| 48 | Cue | P | Posterior probabilities are the conditional `P(H_i\mid E)` values. The content is only a deictic reference. |
| 49 | Cue | P | The point-winning probability must be conditioned on the team serving. The retained content omits that condition. |
| 50 | Cue | P | The source names `m_E` as conditional given `E`. The term loses `given E`, and the content only names the function. |
| 51 | Cue | P | The notation carries `E`, but the selected term truncates the name before `given E`. |
| 52 | Geometry | E | The case-specific conditional density is recognizable. Its trailing prose is garbled. |
| 53 | Geometry | D | The formula correctly defines the joint CDF by simultaneous coordinate events. |
| 54 | Cue | P | The problem name is supported. The candidate does not identify the actual problem statement. |
| 55 | Cue | P | The name refers to elapsed service time being irrelevant. The attached phrase omits that meaning. |
| 56 | Cue | D | The local random variable is the count of red balls drawn. |
| 57 | Cue | P | The name applies to the count distribution. The attachment omits the sampling conditions and parameters. |
| 58 | Cue | P | `females` is a local simulation label. `these balls` loses the drawn subset distinction. |
| 59 | Cue | D | The row and column sums are exactly the table's marginal totals. |
| 60 | Cue | E | The remaining `t12` balls are labeled males in the described urn simulation. |
| 61 | Cue | P | The likelihood estimate is the maximizing `N`. The candidate retains only `This value`. |
| 62 | Geometry | E | The displayed law gives the Poisson mass function for the call count `Y`. |
| 63 | Geometry | P | The piecewise density is right. The retained candidate omits the stipulated positivity of `λ`. |
| 64 | Geometry | X | The gamma CDF should end its truncated series with power `n−1`. The attached expression has power 1 and absorbs surrounding prose. |
| 65 | Cue | D | Arrival to start of service is the exact waiting-time definition. |
| 66 | Geometry | D | The retained Gaussian density formula agrees with the defining display. |
| 67 | Geometry | P | The integral supports the exercise statement, but the component omits independence and the meaning of `G`. |
| 68 | Geometry | P | The expected-value sum is relevant. Absolute convergence is a defining condition omitted from the structured content, whose suffix is also corrupted. |
| 69 | Geometry | E | The formula gives the local waiting-time mass function. The geometric name and support are in context. |
| 70 | Cue | P | The example is named correctly. The attachment does not state the divergent expectation or the game. |
| 71 | Cue | P | The source names a function mapping payment to value. The component keeps only the anaphoric phrase. |
| 72 | Cue | E | Three initial heads are one instance of a run. The scope is the particular coin sequence. |
| 73 | Geometry | E | The signed winnings and masses give the source's dollar-bet distribution. |
| 74 | Cue | E | The source names a fair game a martingale in the stated setting. The retained synonym alone omits the conditional-fortune criterion. |
| 75 | Cue | P | The horizontal endpoint line is described correctly, but the defined identifier `L` is omitted. |
| 76 | Geometry | D | The expected squared deviation is the source definition of variance. |
| 77 | Geometry | E | The formula correctly gives the standard deviation of the specified sample average `A_n`. |
| 78 | Cue | P | The name matches `X*`; the defining centering and scaling are outside the retained content. |
| 79 | Geometry | D | The retained equality identifies both variance notation and the defining expectation. |
| 80 | Cue | P | Little's law is named. The selected deictic phrase omits `N=λT` and equilibrium context. |
| 81 | Geometry | P | The coefficient formula is correct. The stated requirement of positive variances is outside the component. |
| 82 | Geometry | D | The ratio states the source's conditional density for `X` given `Y=y`. |
| 83 | Cue | D | The level-set condition `f_{X,Y}(x,y)=C` supplies the actual definition. |
| 84 | Model | X | The diagram is a technique for staged experiments. The nearby word `task` refers to a counted procedure. |
| 85 | Model | X | Historical Remarks is the section containing a solution, while the surrounding sentence states the actual hat check problem. |
| 86 | Model | X | Binomial coefficients are tools used for the trials process. The attachment confuses method and modeled process. |
| 87 | Model | X | Equation 3.3 is the referenced inclusion-exclusion identity used in the proof. |
| 88 | Model | X | Chapter 3 is a location reference. The distribution of the count of heads is the substantive explanation nearby. |
| 89 | Model | P | The equation reference points to this Poisson law. The candidate retains neither the formula nor a specific distribution name. |
| 90 | Model | X | The law supports the interpretation of long-run averages. The attachment treats that supporting theorem as the meaning of expected value. |
| 91 | Model | X | Stirling's formula approximates an expectation later in the exercise, a different role from the probability `p_r`. |
| 92 | Model | X | Harris Schultz is credited for the proof. That attribution supplies no semantic content for the expectation. |
| 93 | Model | X | The cited author belongs to the preceding exercise. The retained probability term belongs to the matchbox exercise. |
| 94 | Model | X | Example 6.13 supplies roulette options for a separate expected-winnings question. |
| 95 | Model | X | Chapter 8 is where a limit statement is formalized. The excerpt describes standard deviation separately as a measure of spread. |
| 96 | Geometry | E | The retained integral gives the source's convolution density for the sum. |
| 97 | Cue | P | The name matches. The candidate omits the gamma parameters and degrees of freedom. |
| 98 | Cue | P | The program is correctly named, but the actual repeated die experiment and statistic are only referenced. |
| 99 | Cue | P | The source defines support by `f(x)>0`; the retained `the set` omits that criterion. |
| 100 | Cue | P | The name matches the theorem, with no substantive antecedent in the retained content. |
| 101 | Cue | D | The attachment accurately records the textbook's retrospective mathematical characterization of probability in this paragraph. |
| 102 | Geometry | E | The retained sum is the correct local probability of the stated mean-deviation event. |
| 103 | Geometry | X | The term is only the threshold fragment `at least ϵ`. The whole deviation event is the subject of the sum. |
| 104 | Cue | E | The described version of the Law of Large Numbers is locally called the Weak Law. |
| 105 | Cue | D | The paragraph explicitly gives `law of averages` as a synonym for the Law of Large Numbers. |
| 106 | Geometry | D | The formula retains the standardized variable's centering and scaling. |
| 107 | Geometry | X | `Definition` is a heading marker. The formula defines the standardized sum. |
| 108 | Geometry | D | The formula correctly defines the standardized Bernoulli count. |
| 109 | Cue | P | The normal CDF's defining upper limit `x` and notation `N(x)` are missing. |
| 110 | Cue | X | One retained term, `the mean`, is assigned both the mean and variance symbols. The source gives distinct roles. |
| 111 | Geometry | E | The formula models the stated offspring heights with a deterministic term and a residual. |
| 112 | Cue | P | The contrasted germ cells are correctly named. The retained phrase loses what makes them the remaining cells. |
| 113 | Cue | D | The full stated non-transmission criterion is retained for somatic cells. |
| 114 | Cue | D | The unordered pair-of-alleles definition is retained. |
| 115 | Cue | P | The source refers to alternative forms of a gene, but the content only says `These various forms`. |
| 116 | Geometry | P | The first moment supplies the mean. The attached array also includes the distinct variance formula. |
| 117 | Cue | P | The source ties the moment-generating function to `g(t)`. The retained term is clipped. |
| 118 | Geometry | X | The generic `the function` precedes the definition of `h`, while the attachment is the adjacent formula for `g`. |
| 119 | Geometry | X | The component assigns the formula for `g(t)` to `h`, which has its own following formula. |
| 120 | Geometry | E | The moment sequence is the stated worked example for one discrete variable. |
| 121 | Geometry | P | The expected waiting-time formula is relevant. The candidate's term is deictic and the formula's suffix is garbled. |
| 122 | Cue | E | The source names `r` the service rate in the one-minute model. The probability interpretation remains in context. |
| 123 | Cue | E | The source names `p` the arrival rate in the one-minute model. The probability interpretation remains in context. |
| 124 | Geometry | E | The formula gives the moment-generating function for the specified normal random variable. |
| 125 | Cue | P | The characteristic function is named, but the component retains only its notation and loses the transform. |
| 126 | Geometry | P | The integral is for barred `g(t)`. The selected term drops the bar and its closing delimiter. |
| 127 | Model | X | NFoldConvolution computes the point-count distribution and plays a different role from the count itself. |
| 128 | Model | X | The program computes a distribution on 13-card hands. The attachment confuses the tool with its modeled input. |
| 129 | Model | X | The Epstein text is a bibliography citation attached to a preceding gambling example. |
| 130 | Model | X | Chapter 4.3 points to an earlier introduction. The actual density is described by the gamma parameters nearby. |
| 131 | Model | X | The candidate already declares unresolved. Chebyshev's inequality constrains a deviation probability for `X`. The attachment confuses the variable with that constraint. |
| 132 | Model | X | The quincunx is the device. The Central Limit Theorem explains an approximation for its output distribution. |
| 133 | Cue | P | The term names the process correctly. The retained phrase omits the state-transition relationship. |
| 134 | Cue | D | Each move in the described Markov chain is called a step. |
| 135 | Cue | P | The matrix name is correct. `Such a square array` omits what its entries represent. |
| 136 | Cue | P | The function is named correctly. The defining `f=Pf` property is outside the attached content. |
| 137 | Cue | E | The source gives the fair-game gloss of martingales here. The component omits the technical conditions. |
| 138 | Cue | P | The gene proportion is the intended definition. The term is clipped and the attachment runs into the next instruction. |
| 139 | Geometry | X | The rendered matrix includes the column labels as an extra first row. The original source is the two-state swap matrix. |
| 140 | Cue | P | The term is correct, but the retained `w` omits the fixed-point condition `wP=w`. |
| 141 | Cue | X | The source equation is `Px=x`. The attachment stops after the equals sign. |
| 142 | Cue | D | The named traffic intensity is the retained ratio `s=p/r`. |
| 143 | Cue | P | The name is the minimum component of `Py`. The attachment omits the vector and includes the consequence `m1>0`. |
| 144 | Geometry | E | The product formula describes the transitions of the specific joint chain. |
| 145 | Cue | P | The matrix symbol is right. Its zero off-diagonal structure and recurrence-time diagonal are omitted. |
| 146 | Cue | P | The source names the inverse of `I−P+W`. The attachment stops at `this inverse`. |
| 147 | Geometry | E | The two adjacent-state transitions and zero otherwise agree with the stated urn model. |
| 148 | Cue | P | The constant is named. The content omits the defining sum and its independence from the initial state. |
| 149 | Geometry | P | The displayed mass function describes the common increment distribution. The retained term is only the variable family. |
| 150 | Geometry | X | The formula is a return probability at time `2m`. The selected term is the index `m`. |
| 151 | Cue | X | The source defines `f_{2m}`. The retained term cuts the indexed symbol to `f2` and the content omits the event. |
| 152 | Geometry | X | The formula concerns the first-return probability, with `m` only its index. |
| 153 | Cue | D | The source explicitly assigns the local zeroth coefficient `u_0=1`. |
| 154 | Cue | X | The source defines `g_{2m}`. The retained term cuts it to `g2`. |
| 155 | Cue | P | The ruin probability must precede reaching `M` and start at `k`. Both conditions are outside the retained content. |
| 156 | Cue | D | The source's local bookkeeping rule defines current fortune as the value of the next wagered counter. |
| 157 | Cue | P | The first-maximum subscript is correctly described. The term omits `K_n`. |
| 158 | Cue | P | The candidate preserves the name `W*` and omits the reversed order of the summands. |
| 159 | Model | X | The Binomial Theorem is one method for computing the first-return coefficients. |
| 160 | Model | X | Theorem 12.2 justifies a proof step. The attached term `j` is a summation index. |

## Findings

| Basis | Definition or exact naming | Local explanation | Incomplete | Unsupported | Reviewed |
| --- | ---: | ---: | ---: | ---: | ---: |
| Matched cue | 16 | 9 | 57 | 7 | 89 |
| Native geometry | 7 | 16 | 12 | 12 | 47 |
| Model reading | 0 | 0 | 1 | 23 | 24 |
| Total | 23 | 25 | 70 | 42 | 160 |

- **Matched cues often find the right phrase and lose the proposition.** The
  waiting-time definition and row/column marginal totals show the useful case
  at indices 65 and 59. Indices 49, 68, and 155 show the consequence of losing
  a condition. They omit serving, absolute convergence, and prior ruin before
  a specified upper stake, respectively. Indices 45, 151, and 154 show term
  boundary failures involving indexed notation.
- **Geometry can recover mathematical content and propagate recognition
  errors.** Indices 53, 66, 76, and 108 bind usable formulas. The original
  page images confirm that index 64 changes the last gamma-CDF power from
  `n−1` to `1` and index 139 includes column labels in the two-state
  transition matrix. A correct attachment can still contain a wrong
  mathematical expression.
- **Model readings in this retained set mostly select nearby references.**
  Chapters, author credits, theorem names, and software names are located
  spans with their own roles. They were frequently attached as definitions
  or explanations of neighboring terms. Index 89 is the one incomplete
  source-backed reference in this model-reading set. These judgments
  apply to the 24 retained model-reading components in this packet.
