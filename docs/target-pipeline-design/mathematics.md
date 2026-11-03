# Mathematics of stream synthesis

**Proposed long-term formalization (2026-11-01).** This page preserves the interpretation model and measurement design alongside the 2026-11-03 corrections. The [first production milestone](first-production-milestone.md) governs the initial implementation. The [synthesis and interpretation](synthesis-and-interpretation.md) page gives the contracts and the pump trace. The reference branch implements parts of the formalization with illustrative inputs, which leave calibration, operating thresholds and corpus behavior to be evaluated. [Mathematical foundations](https://app.notion.com/p/40a141b5836981798d81c84a75d61194), [Mathematical assessment and inference contract](https://app.notion.com/p/40d141b5836981e2bdcac2a511da386c)

## Value and interaction

Let N be the registered stream groups, S a subset of N, and V(S) the value obtained on a fixed labelled evaluation population under a fixed comparison policy. A useful definition sums value vᵣ for correct accepted records and subtracts cost cᵣ for incorrect accepted records. Define the alignment, eligibility, thresholds or matched coverage, and resource limits before comparing subsets. CPU and other costs can be reported separately or included under an explicit utility policy.

For disjoint A and B, complementarity means V(A ∪ B) > V(A) + V(B) − V(∅). For overlapping sets replace V(∅) with V(A ∩ B). Use the Möbius transform to assign each contribution to the smallest coalition terms that explain it. Its inverse reconstructs the original set value.

```text
m(T) = Σ[S ⊆ T] (−1)^(|T|−|S|) V(S)
V(S) = Σ[T ⊆ S] m(T)
```

A singleton contributes V({i}) − V(∅). Positive dividends describe gain beyond the contributions of smaller subsets. Negative dividends can reflect redundancy, interference, resource effects or overlap between successful routes. Check the corresponding inequalities across contexts before making a global claim about complementarity or diminishing returns.

The Shapley value of i averages its marginal value over all insertion orders. The pairwise interaction index averages the difference of two such increments across background sets S, with n = |N|.

```text
ΔᵢV(S) = V(S ∪ {i}) − V(S)
φᵢ = Σ[S ⊆ N ∖ {i}] |S|! (n−|S|−1)! / n! × ΔᵢV(S)
   = Σ[T ∋ i] m(T) / |T|

ΔᵢⱼV(S) = V(S ∪ {i,j}) − V(S ∪ {i}) − V(S ∪ {j}) + V(S)
Iᵢⱼ = Σ[S ⊆ N ∖ {i,j}] |S|! (n−|S|−2)! / (n−1)! × ΔᵢⱼV(S)
```

Partial information decomposition is the corresponding information question. It separates evidence unique to each stream, redundant evidence and information available only jointly, as in XOR. The operational objective measures correct and incorrect records and their consequences. [Value function and synergy](https://app.notion.com/p/40b141b5836981778e63c81add619c75)

## Four mechanisms

1. **Conjunctive assembly.** A frame can be assembled when the stream set covers every required role R. Its probability of being correct is the joint event that every required role is correct. An ideal AND game where every stream is necessary has its interaction mass on the full required set. With only marginals pₖ, the Fréchet bounds for the conjunction are max(0, Σₖpₖ − (|R|−1)) and minₖpₖ. Products of marginals require independence.
2. **Mutual disambiguation.** A compatibility factor links decisions Z₁ and Z₂. Evidence E₂ for Z₂ can then help resolve Z₁. In the specified distribution the reduction in expected uncertainty is H(Z₁ | E₁) − H(Z₁ | E₁,E₂) = I(Z₁; E₂ | E₁) ≥ 0. It is zero under the relevant conditional independence. A real improvement still requires evaluation. Complementary evidence about the same decision, assembly and thresholding can also yield positive utility interactions.
3. **Deductive closure.** Start from accepted premises Γ and apply scoped, adopted rules R to their least fixpoint Cnᵣ(Γ). The new facts are Cnᵣ(Γ) ∖ Γ. Unit conversions, arithmetic comparisons and supported type entailments carry their premises and rule steps. A two-premise rule can have quadratically many comparable pairs within a large group, so block on the relevant join keys. Compatibility pruning during interpretation belongs to mutual disambiguation.
4. **Corpus aggregation.** Qualified equivalents, contrasts, support groups, drift and value distributions become visible across documents. Their comparison units depend on alignment and qualification. Repeated reporting increases counts without necessarily supplying additional distinct evidence.

[Four mechanisms of synergy](https://app.notion.com/p/40b141b5836981f7bfa4f8f8607de63d)

## Derivation algebra and recomputation

For a derived record, a join combines premises with multiplication and alternative derivations combine with addition in a provenance polynomial. A text assertion and a table cell for the **same** qualified measurement could supply separate derivations with a shared condition, as in the following polynomial.

```text
prov(m) = x_qty × x_coref × x_unit × x_cond
        + x_cell × x_row_entity × x_header × x_cond
```

In the pump trace, Table 3 backs the rating, so this polynomial is a general illustration for a text–cell match. The target includes Boolean derivability, counting derivations with their multiplicity, Viterbi scoring of the strongest derivation under a suitable factorization, and why-provenance for inspecting the supporting premise sets. For probability, evaluate the corresponding Boolean event Φₘ under an explicit joint distribution. A semiring expression of proof structure alone supplies no such distribution.

```text
P(m | e,O) = Σ_z P(z | e,O) × 1[Φₘ(z)]
P(Φ) = P(x) P(Φ | x = 1) + (1 − P(x)) P(Φ | x = 0)
```

The second identity is Shannon expansion. A Boolean representation reuses the same condition event on both routes. Use exact enumeration locally, or consider compiled decision diagrams when lineage complexity warrants it. Repeated expansion with unconditional variable probabilities requires independent premises. Shared or mutually exclusive decisions use the joint model. With only marginal confidences, report bounds where available. [Lineage and provenance semirings](https://app.notion.com/p/40b141b583698137a349c19bc78b7e4d)

**M1 contract.** Separate derivation lineage from the complete computation dependency set. Setting a variable to zero answers whether a derivation survives the removal of that premise in a fixed lineage. Withdrawing an observation from an inference run can change candidates, constraints or scores and can raise a record's probability if the withdrawn evidence opposed it. Recompute the affected inference component and its dependents. The reference implementation's product of every observation touching a component can serve as a conservative invalidation signature. Scientific justification comes from the actual derivations. [M1 inference contract, §7](https://app.notion.com/p/40d141b5836981e2bdcac2a511da386c)

## Bounded joint model and calibration

Let z be the assignments to typed decisions in one connected component, e the retained observations, O the accepted ontology version, and H(z,O) the declared hard-constraint predicate. The model normalizes the following weights over feasible assignments.

```text
Pθ(z | e,O) = exp[Σ_g fθ,g(z_g,e_g) + Σ_j w_j ψ_j(z_j,O)]
              × 1[H(z,O)] / Zθ(e,O)
```

Evidence potentials f read observation groups. Compatibility potentials ψ can couple units with property and referent, column property with row type, entity types with relation labels, and condition scope with frame roles. The normalizer Z sums over feasible assignments. Equivalently the model multiplies exponentiated evidence and compatibility factors and hard indicators before normalization. Unary factors alone supply no cross-decision disambiguation. The record event sums weights over coherent assignments that establish the whole record. A MAP assignment can differ from the most probable record event, and collecting top field marginals can produce an incompatible record.

Hard constraints act on each candidate assignment under scoped structural, logical or physical premises. Accepted entailments can run as deterministic closure over premises. Soft expectations use finite weights or diagnostics. Open possibilities preserve UNKNOWN. Markov-logic-style features can count satisfied ground rules, with weight wᵢ and score Σᵢwᵢnᵢ(z), for designs that warrant this generalization. An OCR-preferred unit reading stays a candidate, so the template can recover a compatible pressure reading even when the raw extractor slightly favors hours.

For a binary event Y under matched conditioning, subtract the calibration population's prior log-odds from calibrated posterior log-odds to obtain a likelihood-ratio feature.

```text
LLR(s) = log[P(s | Y=1) / P(s | Y=0)]
       = logit P(Y=1 | s) − logit P(Y=1)
```

Model, decision type, source-quality grade and generator policy affect the conditioning. Candidate-versus-rest scores need a coherent multiclass treatment when candidate sets vary. Preserve raw score semantics and uncertainty. The target considers Platt or isotonic fits, conditional likelihood or pseudolikelihood for compatibility weights, and empirical reliability checks, including proper scoring rules and reliability plots. M1 permits regularized stacking or fitted grouped log-linear potentials. Group observations with shared model, encoder, prompts, passage, OCR or derivation. Use conservative representative features provisionally where grouped fitting lacks data. A high-quality parse or common quality grade leaves shared error possible. Exact enumeration certifies computation within the model, while held-out evaluation establishes empirical confidence.

The prototype enumerates up to 65,536 assignments per connected component. M1 starts with that configurable guard plus time and memory limits and emits an explicit resource-limit outcome. Independent components can be solved separately. Consider variable elimination when measured intermediate factor size or induced width warrants it. Approximation requires explicit semantics and evaluation. Splink linkage, probabilistic soft logic for larger coupled MAP problems, and Pyro for measured reliability heterogeneity are possible later paths. Soft-logic MAP scores have different semantics from discrete event marginals.

The long-term split-conformal proposal sets s(x,y) = 1 − p(y | x), takes the order statistic indexed by ceil((n+1)(1−α)) among n calibration scores, with an infinite threshold if the index is n+1, and returns all labels with s(x,y) at most that threshold plus UNKNOWN. The standard guarantee is marginal over exchangeable calibration and test draws. Restricted retrieval, subsequent truncation and deployment shift can break the intended coverage. Report candidate recall and misses outside retrieval directly. M1 starts with bounded candidates and diagnostics and leaves conformal sets to a separately evaluated adoption. [Joint model and calibration](https://app.notion.com/p/40b141b583698193ab8fd8313f46b0f5), [M1 inference contract, §§2–6](https://app.notion.com/p/40d141b5836981e2bdcac2a511da386c)

## Corpus support

The earlier proposal grouped qualified assertions by origin, set r_g as a likelihood ratio for a correctly read assertion and π_g as its interpretation confidence. It then proposed the following aggregation.

```text
Λ_g = π_g r_g + (1 − π_g)
k_eff = k / [1 + (k−1)ρ]
log posterior odds = log prior odds + (k_eff / k) Σ_g log Λ_g
```

Here ρ represented average residual correlation across k distinct provenance groups. The effective count ranges from k to 1 as ρ runs from 0 to 1. The prototype documentation also used source reliability and recall terminology for these parameters, whose meanings differ from interpretation confidence and likelihood ratios. The effective count can describe sensitivity under a design-effect assumption. Scaling heterogeneous log-likelihood contributions by it is a heuristic.

For a latent reading state R, evidence E and scientific hypothesis H, the general likelihood ratio sums over the reading states under each hypothesis.

```text
LR(E) = [Σ_r P(E | H,R=r) P(R=r | H)]
        / [Σ_r P(E | ¬H,R=r) P(R=r | ¬H)]
```

A posterior interpretation weight already conditioned on E generally cannot serve as the prior mixture weight. A Dawid–Skene or hierarchical model might estimate reliability under assumptions about latent labels, sources and dependence that require separate evaluation. For contradiction, compare equivalent proposition content with opposed assertions and overlapping conditions, time and scope. A product of individual event probabilities requires independence. Use a joint event when they share decisions, and use deterministic checks for established interval and condition relations.

M1 retains supporting and opposing qualified assertions, citation and dependency groups, source types and known shared origins in a ledger. It preserves author modality, interpretation confidence, source reliability and corpus support separately. Any later probability of scientific truth requires an identifiable and evaluated model. See also the repository's [confidence design](../design/D5-consolidation-identity-confidence.md) for the relationship to its cold-start confidence and latent-truth proposals. [Corpus evidence](https://app.notion.com/p/40b141b5836981c48348e0fc536bce5b), [M1 inference contract, §8](https://app.notion.com/p/40d141b5836981e2bdcac2a511da386c)

## Acceptance and escalation

If accepting a correct record is worth vᵣ, accepting a wrong record costs cᵣ and abstaining has zero utility, the break-even threshold follows from the utility of acceptance.

```text
EU_accept(r) = pᵣ vᵣ − (1 − pᵣ)cᵣ
τᵣ = cᵣ / (cᵣ + vᵣ)                 accept when pᵣ ≥ τᵣ
U = Σ_r aᵣ EU_accept(r) − λ × CPU(actions)
```

Here aᵣ indicates acceptance and λ is the specified price of a CPU-second. The illustrative ratios c/v = 3 and 9 give 0.75 and 0.90. M1 uses an evaluated acceptance policy with per-family thresholds chosen on held-out precision and coverage, and keeps model-resolved records provisional until the gate is met. Deterministic derivations over validated premises can carry an explicit proof. Required unresolved slots prevent acceptance of a complete record. Optional fields can remain absent, inapplicable or unresolved when the other supported fields are useful.

For a possible observation o returned by action a, the long-term policy compares expected utility before and after observing o.

```text
EVI(a) = E[o | e,a] max_d EU(d | e,o) − max_d EU(d | e)
```

Compare EVI with the applicable action cost. Actions include reading a caption or table note, re-converting one region, scoped specialist extraction, a grounded CPU LLM or review. The expression presumes an explicit outcome model and comparable utility and cost units. Ordering by EVI per unit cost is a heuristic. Near-optimality needs additional structure such as adaptive submodularity. M1 records unresolved cases and action costs and defers a learned EVI controller. [Acceptance and escalation](https://app.notion.com/p/40b141b5836981f7ac70e9d7fa7cef88)

## Measuring contribution

Compare independent union, deterministic joins and rules, and joint interpretation on a common target. The long-term decomposition separates three differences.

```text
V_joint,e2e − V_union =
    (V_rules − V_union)                assembly and closure
  + (V_joint,fixed − V_rules)          disambiguation at fixed candidates
  + (V_joint,e2e − V_joint,fixed)       changed candidate coverage and upstream effects
```

Control each comparison's candidate universe and downstream policy before interpreting a term. Remove ontology factors at fixed evidence to examine compatibility, and compare dependence handling on precision, coverage and calibration to distinguish gain from overconfidence. Fixed-evidence ablation can mask reusable observations if their inputs and candidate universe stay fixed. A component removal that changes mentions, labels, preprocessing, context windows or retrieval must recompute dependent observations and candidates for an end-to-end result.

The reference harness specifies exact subset enumeration up to 12 groups. Eight functional groups give 256 subsets, and adding corpus and LLM yields 1,024. The target considers Monte Carlo permutation sampling for finer within-group contributions. Bootstrap at document or source-family level, keeping dependent passages and editions together. Consider prediction-powered inference for aggregate quality only with an independently adjudicated, representative audit and an appropriate dependence-aware sampling design. Report candidate recall, complete-record precision and coverage, qualifier attachment, abstentions and resource costs before reporting attribution summaries. Use the stronger simpler method where coupling fails to produce a sufficient benefit. [Measuring the synergy](https://app.notion.com/p/40b141b58369815e898fd46f2b34bfdd), [Rollout and evaluation](rollout-and-evaluation.md)


## M1 numerical realization

**Proposed · 2026-11-03; [review O04](../functional_reviews/m1-target-design_2026-11-03.md#O04).**
Keep domain decisions in the existing semantic operation model. NumPy arrays are the bounded
physical representation; SciPy supplies numerical kernels, not an independent interpretation
policy. The product already pins SciPy 1.18.1 and NetworkX 3.7; this review changes neither.

1. Assign stable finite domains, including unresolved and genuine local/new identity alternatives.
   Declare all factor scopes, evidence-dependence scopes and constraints before forming components.
   `networkx.connected_components` can partition this dependency graph. Shared release metadata
   alone does not couple variables; a real shared factor or global constraint does.
2. Enumerate bounded assignment blocks, evaluate feasibility under selected meanings, and accumulate
   log potentials. An infeasible assignment has log weight negative infinity. Reject invalid model
   inputs/nonfinite potentials explicitly. If feasible positive support is empty, return infeasible
   rather than a uniform distribution or a successful empty extraction.
3. Use `scipy.special.logsumexp` for the partition and record-event sums. With log weights `a` and
   event mask `M`, compute `exp(logsumexp(a[M]) - logsumexp(a))`. Repeated derivations of the same
   event do not count an assignment twice. The event includes every meaning-changing qualifier.
4. Normalize over complete enumerated support before reducing to displayed alternatives. Record
   probabilities are conditional on the declared retained-candidate model. Candidates never
   generated have unknown omitted mass, not a computed probability of being wrong. Keep candidate
   recall, inference exactness and empirical calibration separate.
5. Return coherent alternatives, event probability/score standing, useful marginals, dependencies
   and feasibility/search/limit diagnostics. A state limit, elapsed limit and numerical failure
   have different outcomes. No marginal product, silent split or MAP fallback substitutes for the
   requested record-event sum.

Sources: [SciPy §12.1](../libraries/scientific_compute/scipy.md),
[logsumexp](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.logsumexp.html),
[NetworkX §3](../libraries/scientific_compute/networkx.md).

### Factorized and optimized alternatives

pgmpy `DiscreteMarkovNetwork` plus `DiscreteFactor` matches undirected compatibility potentials.
Evaluate `VariableElimination` or junction-tree inference only for a concrete workload where
factorization/repeated queries improve the complete route. Preserve variable/state ordering and
hard zeros, establish a positive finite partition, and explicitly normalize the returned factor
where the selected route does not. Current upstream Markov-network query paths do not share all
normalization behavior of Bayesian/junction-tree branches; pin and inspect the selected version.
Probability-space factor products also require stability qualification. An arbitrary `FactorGraph`
query route is not assumed supported from a base-class signature.

Elimination order and intermediate factors can defeat a small output bound. Requesting a full joint
can reproduce enumeration's output size. Require small independent expected cases for event sums,
zero support, state permutations and extreme log weights before substitution. Exact inference
still says nothing about empirical calibration. Sources: [pgmpy §§5, 10](../libraries/scientific_compute/pgmpy.md),
[exact-inference source](https://pgmpy.org/_modules/pgmpy/inference/ExactInference.html).

Z3 satisfiability/unsat explanations and SciPy `milp` or CVXPY constrained optimization remain
options for a demonstrated constraint/best-assignment problem. None by itself supplies a partition
function or posterior marginals. Approximate inference needs its own error/status policy and a
separately evaluated reason to replace the exact supported subset.

### Fitting, calibration and population uncertainty

Fit grouped evidence features first; assess/calibrate final record-event predictions after
constraints and coupling; then choose family thresholds on development data and freeze before
final assessment. Head calibration does not survive arbitrary factor addition by assumption.
A regularized logistic `Pipeline` and `CalibratedClassifierCV` are focused scikit-learn candidates
when isolated labels support fitting; use explicit group-separated index splits. Sparse fitting
data warrants provisional scores, not an unsupported calibrated label.

For paired comparisons, resample independent source groups and recompute aggregate complete-record
ratios from each group's contributions. SciPy `stats.bootstrap` supplies resampling machinery;
`paired=True` does not infer clusters or fix the sampling design. A zero-error sample can make a
naive percentile/BCa interval degenerate; it cannot automatically establish the proposed precision
lower bound. Few source groups limit generalization even with many records. Freeze a suitable
sampling/interval procedure before final assessment; insufficiency keeps the gate unestablished.
Statsmodels GEE and prediction-powered inference are later population-analysis options with their
own estimands and assumptions, not per-record certification.

Sources: [SciPy §8](../libraries/scientific_compute/scipy.md),
[bootstrap](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html),
[scikit-learn calibration](https://scikit-learn.org/stable/modules/calibration.html),
[statsmodels](../libraries/scientific_compute/statsmodels.md),
[PPI](../libraries/scientific_compute/ppi_py.md). No fitting, calibration or numerical execution
was performed for this design review.
