# Independent assessment B: frozen definition replay

Assessed 2026-11-06. This is an exposed development diagnostic of all **41** final proposals: **13 named definition**, **19 named explanation**, and **9 model** proposals. The assessor read the output before the source contexts and had previously assessed the nine baseline outputs. No held-out, source-first, provider re-execution, current120-run or full-corpus claim is made. No other current assessor or source-adjudication output was consulted.

[assessment.json](assessment.json) preserves all exact component IDs, original components/states, six independent facets, expected subjects/content, conditions, recognition issues, useful narrower relations and source quotations. Exact neutral-source projection pieces locate quotations in converted native items or table cells; original native text and provenance are retained separately. Original formula character spans and converted-formula offsets are different coordinate systems. Bounding boxes belong to native items/cells, not necessarily the selected substring.

The replay retains all nine baseline components **byte-for-byte unchanged**, adds **31 named proposals and one model proposal**, and removes none. Both reports cover the same 149 raw model windows and forty original sources. The added model proposal is a binomial-distribution → Chapter 3 backward reference: useful as a definition-location pointer, unsuitable as new defining statistical content. Counts of retained or added proposals do not establish semantic benefit.

Many named additions have valid local direction and useful content. Their roles differ: local random-variable definitions, density formulas, model-label assignments, named example instances and program naming should retain those distinctions. Short anaphoric content is often useful but unresolved by itself; missing full definitions do not invalidate a valid narrow relation.

Three emitted native-display captures have specific recognition problems visible without rereading PDFs:

- **B-NAMED-010**, gamma CDF: converted exponent `1` disagrees with native original `n-1`; the containing native item also includes trailing explanatory prose.
- **B-NAMED-013**, expected value: converted formula appends fragments absent from its native original formula. Absolute convergence is stated separately in the source.
- **B-NAMED-019**, conditional expectation: converted formula contains extraneous dotted marks and an additional spurious repeated expression absent from its native original.

These are recognition/capture findings. The core formulas and directed local attachments can remain useful. Exact quotation of corrupted converted source does not establish fidelity to the original formula, and comparison to native originals does not establish PDF fidelity or scientific truth.

Further material limits are anaphoric content, omitted parameters/conditions, the “Show that” exercise speech act, and overgeneralization of model labels or example instances. `assessment.json` records B-M01 through B-M05 with affected cases and concrete implications for the coordinator. The thirteen explicit definition readings do not mean thirteen independently complete or scientifically validated definitions.

The replay names COMMON001/007/016/023/031 as exposed implementation references. Those IDs are preserved as exposure context. No per-component mapping or acceptance was invented; optional source-adjudication material was not read.

Facet notation below: **S** supported narrowly as located in the source; **U** unsupported as emitted; **A** ambiguous or incomplete without the stated local context; **N** unassessed. Recognition N does not allege an error; it preserves the limit of this bounded textual reading. Scope A does not invalidate an otherwise supported local attachment. Original conversion-health success is retained separately from semantic support.

| Case / actual component prefix | Emitted type | Expected subject | Term | Content | Direction | Type | Scope | Native recognition | Useful narrower relation |
|---|---|---|---|---|---|---|---|---|---|
| B-NAMED-001 / `e849bcf4beac` | explanation | memoryless property | S | A | S | S | A | N | Named property → anaphoric property mention; useful local naming, not a self-contained statement. |
| B-NAMED-002 / `bd89dda4e816` | explanation | hypergeometric distribution | S | S | S | S | A | N | Named distribution → locally constructed distribution of X. |
| B-NAMED-003 / `fbb62fad87c6` | definition | X: number of sampled red balls | S | S | S | S | A | N | Local variable defined_by a count. |
| B-NAMED-004 / `535dbcc3e512` | explanation | females: model label for sampled balls | S | A | S | S | A | S | Label assigned to drawn balls in an urn model. |
| B-NAMED-005 / `5b5446dd1db6` | explanation | males: model label for remaining balls | S | S | S | S | A | S | Label assigned to the remaining urn balls. |
| B-NAMED-006 / `9b5f74ab7033` | explanation | marginal totals | S | S | S | S | S | N | Marginal totals is a name for the row/column sums. |
| B-NAMED-007 / `25406ed42819` | explanation | maximum likelihood estimate for N | S | A | S | S | A | N | Name assigned to the maximizer requested by part (c). |
| B-NAMED-008 / `661fe412a625` | explanation | distribution of incoming-call count Y | S | S | S | A | A | N | Exercise target formula for distribution of Y. |
| B-NAMED-009 / `29c32c893885` | definition | exponential density function | S | S | S | S | A | N | Density defined_by displayed formula. |
| B-NAMED-010 / `3c3be157a709` | explanation | CDF of Sn | S | A | S | S | A | U | CDF given_by a native display; useful subject-to-formula attachment with a corrupt capture. |
| B-NAMED-011 / `5b7093ac00ce` | definition | waiting time of a customer | S | S | S | S | A | N | Waiting time defined_by duration description. |
| B-NAMED-012 / `48aa526ace3f` | definition | normal density function with µ,σ | S | S | S | S | A | N | Normal density defined_by displayed expression. |
| B-NAMED-013 / `5225c52880fc` | definition | expected value E(X) | S | A | S | S | A | U | Expected value defined_by a sum, with a neighboring existence condition. |
| B-NAMED-014 / `3fa290893758` | definition | distribution function m(i) of local toss count X | S | S | S | S | A | N | Local distribution defined_by probability formula. |
| B-NAMED-015 / `147a86118c19` | explanation | St. Petersburg Paradox | S | A | S | S | A | N | Name assigned to the preceding example. |
| B-NAMED-016 / `c7499b228197` | explanation | utility function | S | A | S | S | A | N | Name assigned to a payment-value function. |
| B-NAMED-017 / `922961cb49b3` | explanation | run: local example of a maximal same-outcome block | S | S | S | S | A | S | Example_instance_named run. |
| B-NAMED-018 / `f4cedee85474` | explanation | distribution of local roulette winnings X | S | S | S | S | A | N | Distribution given_by table. |
| B-NAMED-019 / `f87e0447f275` | definition | conditional expectation E(X\|F) | S | A | S | S | A | U | Conditional expectation defined_by a weighted sum. |
| B-NAMED-020 / `8d28aa63ec38` | explanation | martingale: local fair-game naming | S | S | S | S | A | S | Martingale is the source name for the fair game under discussion. |
| B-NAMED-021 / `dfc77ee3e3db` | definition | line L | S | S | S | S | A | S | Local geometric auxiliary object defined_by description. |
| B-NAMED-022 / `30fcfa8622b1` | definition | variance V(X) | S | S | S | S | A | N | Variance defined_by expected squared deviation. |
| B-NAMED-023 / `413f6b5248be` | explanation | standard deviation of An | S | S | S | S | A | N | Standard deviation of this average given_by formula. |
| B-NAMED-024 / `2243949c23a2` | explanation | standardized random variable associated with X | S | S | S | S | A | N | Name assigned to X* constructed as (X-µ)/σ. |
| B-NAMED-025 / `a5a43d944e76` | definition | variance σ²=V(X) for continuous X | S | S | S | S | A | N | Variance defined_by expected squared deviation for real-valued X with density. |
| B-NAMED-026 / `0e782bcb8525` | definition | service time of first-in-line individual | S | S | S | S | A | N | Service time defined_by duration description. |
| B-NAMED-027 / `ed1f57336510` | explanation | Little's law for queues | S | A | S | S | A | N | Name assigned to the preceding queue relationship. |
| B-NAMED-028 / `661bee74f52b` | definition | correlation of X and Y | S | S | S | S | A | N | Correlation defined_by displayed quotient. |
| B-NAMED-029 / `039e35006457` | definition | conditional density of X given Y=y | S | S | S | S | A | N | Conditional density defined_by displayed quotient. |
| B-NAMED-030 / `50ddc8e35ec1` | explanation | density of sum Z=X+Y | S | S | S | S | A | N | Density of this sum given_by convolution formula. |
| B-NAMED-031 / `d3ac86c84f08` | explanation | chi-squared density with n degrees of freedom | S | A | S | S | A | N | Name assigned to the described gamma density. |
| B-NAMED-032 / `43e4ed1576a1` | explanation | DieTest program | S | A | S | S | A | S | Program named DieTest; reference to its local computational purpose. |
| B-MODEL-001 / `b999c9a550bb` | explanation | binomial distribution | S | A | S | A | A | N | Backward definition-location reference; retain useful pointer, not actual defining content. |
| B-MODEL-002 / `919aa952ce14` | definition | Poisson distribution, head distribution | S | U | U | U | A | N | Poisson distribution formula_reference Equation5.2. |
| B-MODEL-003 / `1761a117bba5` | explanation | Cauchy density mention | S | U | U | U | A | N | Cauchy averages contrast_with described Law of Large Numbers behavior; subject must change. |
| B-MODEL-004 / `20d49e0702e9` | definition | expected value | S | U | U | U | A | N | Theorem justifies average-outcome interpretation of expected value. |
| B-MODEL-005 / `e7f252c8cd01` | explanation | standard deviation in average concentration discussion | S | A | A | A | A | N | Forward reference for precision of average concentration statement. |
| B-MODEL-006 / `55e6ed613a1e` | explanation | X uniform on [0,1], variance calculation | S | A | S | S | A | N | Applied_result_reference for computing V(X). |
| B-MODEL-007 / `4c5e5520d738` | definition | hand as bridge model entity | U | U | U | U | A | N | Further_discussion_source for bridge point-count/opening-bid model problem. |
| B-MODEL-008 / `6e3d760fdcb3` | definition | opening bid | S | U | U | U | A | N | Further_discussion_source; separate local characterization is point count≥13. |
| B-MODEL-009 / `911d85f50433` | definition | hand as bridge model entity | U | U | U | U | A | N | Point-count distribution C computed_using programNFoldConvolution. |

Validation:

```bash
python docs/design_review/evidence/2026-11-06_wce-definition-refinement/assessment/b/validate.py
```

**passed**, 2026-11-06T18:06:22.481848+00:00: 41 exact component identities, 82 emitted endpoint spans, 43 source-context quotations, 498 native projection-piece overlaps and 4450 checks. Seventeen input file hashes and both original replay hash references matched. The read-only validator writes nothing; its literal standard output is captured in [validation-receipt.json](validation-receipt.json). Assessment and validator hashes are included.

Implementation/rule hashes are preserved as replay-reported references, not independently recomputed from production code. No production edit, database mutation, commit or delegation was performed. No publication or qualification permission follows.
