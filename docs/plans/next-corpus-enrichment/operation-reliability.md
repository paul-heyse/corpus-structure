<a id="NCE-12"></a>

# NCE-12 · Attachment-event reliability and uncertainty

**Development scope audited · 2026-11-07.** The [coordinator](../next-corpus-enrichment_2026-11-07.md) owns execution
state and integration. This package develops [O07](../../functional_reviews/next-corpus-enrichment_2026-11-07.md#O07)
and the statistical portions of [O11](../../functional_reviews/next-corpus-enrichment_2026-11-07.md#O11)
and [O12](../../functional_reviews/next-corpus-enrichment_2026-11-07.md#O12). Event definition and
protected reference preparation can begin on retained group-derived attachments in an admitted
cut. Refit or reassess only when the producer, exact event population or applicable contract
changes. Neither structural delivery nor [NCE-11](finite-interpretation.md#NCE-11) waits on fitting.

## Define and admit the emitted event

The [bounded availability census](../../design_review/evidence/2026-11-06_wce-gs120/assessment/operation-fit-availability/README.md)
found 82 `relation / definition.defining_text_attachment` rows, zero compatible rows for the
existing `relation.defined_by` fitter and no matching protected grade. Use a new explicit
`defining_text_attachment_correctness` event and version it independently from
`defined_by_correctness`. The event asks whether this emitted directed term-to-defining-content
attachment is supported within the scope it claims. A role may be independently useful if the
attachment fails. Source-opportunity omissions, role boundaries and correctness of other
relationships remain separate judgments. Record head role, tail role, attachment/direction and
claimed scope facets, preserving all source-supported alternatives.

- Extend the [operation fitting owner](../../../python/corpus-structure/src/corpus_structure/evaluate/operation_fitting.py),
  [finite parameter contract](../../../python/corpus-structure/src/corpus_structure/semantic/operation_policy.py)
  and [native fitting routes](../../../python/corpus-structure/src/corpus_structure/semantic/sql/operation_event_fitting.sql)
  through one explicit event selector. Keep the existing event as a distinct choice in the current contract and preserve its default for existing callers. Bind the new event to its actual emitted relation
  kind/type, producer operation/version, exact contribution and term/content endpoint anchors,
  frozen passage and scope. Authenticate exact origin task, project, completed run/cut/release
  and selected scope before using a contribution. Deduplicate immutable occurrence/event keys
  within the frame. Retain source origin for grouping across policy runs and producer arms.
- Use the existing protected output-first evaluation route for independently authored
  development or feature-fit judgments. Freeze the exact exposure, authored scope alternatives,
  rubric, adjudicated source premise and evaluation identities before fitting. Supported grades
  constrain both role endpoints and scoped witness. Distinguish unsupported, ambiguous and
  unassessed. Reused appearances are traceable without being counted as independent labels.
  Preserve the current protected evaluator/fitter boundary, aggregate availability for ordinary
  inspection, and labels/reference alternatives outside ordinary result and parameter reads.
- Derive the ordered feature vector once from authenticated source inputs and a versioned cue
  specification. Use `log1p` of each role's exact union character length, signed separation
  divided by the frozen common passage length, and presence of a declared cue such as “is
  defined as,” “is called,” “we call,” or “denoted by.” Measure half-open source extents and
  deduplicate overlap. Use the distance between disjoint role envelopes, positive when content
  follows term, negative when it precedes, zero when envelopes overlap. Use the exact common
  inspected passage for normalization and cue search, with the recipe's declared token/phrase
  normalization. Preserve missing or incomparable anchors and missing common passage as
  feature-unavailable cases, with reasons and separate counts. Score only the declared
  feature-eligible subset. Reconstruct the feature vector from the native frame and equivalent
  authorized runtime source inputs using the same semantics. Grade, authored reference and
  reference-overlap values may only inform assessment.
- Use event identity consistently through availability, selected evaluation, native frame,
  fit admission, fit read, parameter export and score applicability. Extend the existing
  [`ci eval` routes](../../../python/corpus-structure/src/corpus_structure/cli/eval.py) with
  explicit event selection for availability and fitting and typed results for reads. Distinguish
  no eligible event population, missing/incompatible protected evaluation, insufficient usable
  binary classes, nonconvergence and successfully fitted results. A verified frame records
  event, producer, rubric, feature recipe/order, reference digest, source/corpus and release
  applicability. Preserve earlier frames as immutable evidence under their original release. Apply current-only cutover when a persisted or served meaning changes. Store
  fitted results only through admitted native operations. Snapshot the authenticated frame,
  release the read transaction for fitting, and revalidate custody during the bounded write.
  Cancellation or failed validation leaves previous results intact.

## Establish the development baseline

Fit on exact admitted feature rows graded supported or unsupported. Ambiguous, unassessed
and feature-unavailable rows remain observable without entering the binary likelihood.
Reuse `DummyClassifier(strategy="prior")` and
`StandardScaler → LogisticRegression` with `C=1`, `lbfgs`, tolerance `1e-6`, maximum
2,000 iterations and unit weights. Preserve prior-only and unavailable outcomes according
to the existing contract when a class or compatible evaluation is missing. Report distinct
event and origin counts, grade states and exclusions, convergence, coefficients, Brier score,
log loss and role/scope facet disagreements. Same-corpus diagnostics are sufficient for the
development fit. Protected data reuse, calibration, release transfer and population inference
need separate scope. A fitted artifact can be read diagnostically. Runtime selection requires
a separate explicitly approved and versioned policy, evaluated for the stated consumer and
activated through the existing release workflow.

A1/A2/A3 favor the existing evaluator, native admission and score owners with distinct
meanings for event, grade, prediction, fit parameters and publication authority. A4 favors
one bounded projection of exact source features, fit outside the transaction, and unchanged
parameter/scoring machinery for the small first model. Keep expensive posterior inference
and repeated optional assessment outside the ordinary read or enrichment path.
[Current baseline implementation](../../../python/corpus-structure/src/corpus_structure/evaluate/operation_fitting.py) ·
[DummyClassifier](https://scikit-learn.org/1.9/modules/generated/sklearn.dummy.DummyClassifier.html) ·
[StandardScaler](https://scikit-learn.org/1.9/modules/generated/sklearn.preprocessing.StandardScaler.html) ·
[Pipeline](https://scikit-learn.org/1.9/modules/generated/sklearn.pipeline.Pipeline.html) ·
[LogisticRegression](https://scikit-learn.org/1.9/modules/generated/sklearn.linear_model.LogisticRegression.html)

## Acceptance and handoff

- Through the normal availability and fit routes, show the selected cut's genuine event
  count, missing evaluation, and an available protected frame when compatible grades exist.
  Use independently judged term/content examples with a positive embedded negation, an
  unsupported term-to-section reference, a correct pair with incompatible scope, ambiguous
  attachment and unassessed row. Include overlapping/fragmented source extents, direction
  reversal, cue localization and an unavailable common-passage case. Verify native/Python
  feature parity, independent facet disposition and preserved component utility.
- Test the existing event on the current contract, exact replay, repeated views or policy arms, one-class
  and convergence failure behavior, and refusal for forged or mismatched source,
  endpoints, cut, producer, grade or feature recipe. Verify denied protected reads and
  successful ordinary authorized parameter reads. Show that a successful fit alone leaves
  active selection policy unchanged.
- Run `uv run ci test -- python/corpus-structure/tests/evaluate/test_operation_fitting.py`
  and the matching native and CLI selections. Use authentic event and binary grades for
  the declared corpus journey, with fixture controls for correctness and failure. If the
  current development frame lacks a genuine class, record the observed prerequisite and
  leave native development fit unavailable. Report dated commands and outcomes, and let the
  coordinator account for the integrated qualification union.

## Completion audit follow-up

[Series disposition](../next-corpus-enrichment_2026-11-07.md#completion-audit).
The finding text records the original audit baseline.

<a id="nce-12-audit"></a>
**NCE-12-A1 · Reconstruct runtime features and preserve independent label grain.**
The native census and protected development fit stand for the selected event. Runtime
scoring takes a supplied feature vector, while the new recipe derives features only
in SQL. The retained digest probe serializes the same native features and establishes
no independently derived runtime parity. Implement the authorized source-to-vector
route and compare it against native results on exact and unavailable inputs. Count
repeated physical events across views and runs at one label and weight per event
while retaining their separate producer custody. The current frame identifies rows by
origin task and contribution, which permits repeated appearances to become separate
observations. Record independent head, tail, direction and scope dispositions and
disagreements in the protected path. Qualify repeated events, missing and single-class
frames, forged inputs, denied protected reads and ordinary authorized parameter reads
for the new event. [Feature recipe](../../../python/corpus-structure/src/corpus_structure/semantic/sql/operation_event_fitting.sql#L2) ·
[Native event frame](../../../python/corpus-structure/src/corpus_structure/semantic/sql/operation_event_fitting.sql#L137) ·
[Runtime score input](../../../python/corpus-structure/src/corpus_structure/semantic/operation_policy.py#L57).

**2026-11-07 execution.** `ci eval operation-event-features` derives an attachment
vector from its authorized source occurrence. Runtime and native derivation agreed
on the exact selected event in run 161, cut 245, task 853. A physical event uses
canonical source section and version custody, with each producer appearance retained
separately. At run 161/cut 245, 82 emissions reduce to 74 physical events, with
seven repeated identities. Across exact completed cuts, 154 emissions reduce to
the same 74 physical events, including 65 with distinct producer tasks and view
projections. The new protected rubric records head,
tail, direction and scope independently and retains the resulting joint judgment.
Blank frame creation freezes the source opportunities, and pass submission enforces
complete facet judgments.

Protected set 30 and evaluation 35 used independently authored A/B passes and
adjudicated C passes on the two fresh source frames. Fit 3 completed on 11 unique
binary events from one origin, with one supported event and ten unsupported.
The frame retained all 11 producer sightings and one independent facet disagreement.
Availability found 74 compatible physical events and zero feature-unavailable
events in the exact frame. The ordinary parameter-only read and retained-versus-runtime
feature comparison passed. The fitted diagnostic is `in_sample_development` on a
purposive same-origin cohort. [Protected rubric and aggregate receipt](../../design_review/evidence/2026-11-07_nce-attachment-v2/README.md)

## Conditional investigations

Each investigation starts on its own evidence. Record its disposition with the coordinator.
Keep fitted algorithm, dataset and evidence identities separate across arms.

| ID | Start when | Evaluate and advance when | Fallback |
|---|---|---|---|
| NCE-12-C1 · Feature and model challengers | The baseline has an independently located residual tied to a named cue family, layout or interaction and sufficient genuine examples. | Use named columns and `ColumnTransformer` for mixed features and grouped ablations. Compare a shallow tree or histogram boosting only for the identified interaction. Group by independent source origin, using `GroupKFold` or `StratifiedGroupKFold` where feasible. Fit preprocessing within folds. Advance on improved assessed error, precision/recall or coverage–selective-error tradeoff for the stated population. [Grouped validation](https://scikit-learn.org/stable/modules/cross_validation.html) | Retain the four-feature baseline and explicit applicability limits. |
| NCE-12-C2 · Bayesian event uncertainty | The prior/logistic baseline exists and a diagnostic consumer has a question about event probability uncertainty. | Compare Bayesian logistic with identical standardized features and Normal priors with standard deviations 1.5 for the intercept and 1 for coefficients, with narrower/wider sensitivity. Verify Pyro 1.9.2 on the pinned environment. Use `Bernoulli(logits=...)` and CPU `NUTS` via `MCMC` with `num_chains=4`, `warmup_steps=1000`, `num_samples=1000`, `disable_validation=False`, isolated seeded chain lifecycle, and prior/posterior predictive checks. Inspect divergences, ESS, split R-hat, stability, and cancellation cleanup. Compare `AutoLaplaceApproximation` or bounded SciPy quadrature where interval fidelity and fit burden make that comparison useful. Expose posterior intervals and means of per-draw probabilities in a separate diagnostic output bound to the frame, scaler, prior, chain/draw and algorithm versions. Use binary predictive draws separately. Advance only on an interpretable and stable uncertainty result that serves the named diagnostic. [Tagged MCMC](https://github.com/pyro-ppl/pyro/blob/1.9.2/pyro/infer/mcmc/api.py) · [Pyro guide](../../libraries/scientific_compute/pyro-ppl.md) | Retain point estimates and explicit limits. |
| NCE-12-C3 · Replicated dependence | Independent origins and genuine replicated groups identify a residual association and a named marginal or group-specific estimand. | For group-specific effects compare complete, separate and partial pooling, using Pyro non-centered effects where useful or statsmodels `BinomialBayesMixedGLM` for Laplace/VB with independent random effects. For a marginal association compare statsmodels binomial `GEE` with appropriate working covariance and adequate independent clusters. Check identifiability, sensitivity and relevant grouped prediction or uncertainty. Repeat policy executions alone supply no new independent groups. [GEE](https://www.statsmodels.org/stable/gee.html) · [Mixed GLMs](https://www.statsmodels.org/stable/mixed_glm.html) | Report grouped counts and the pooled baseline with its scope. |
| NCE-12-C4 · Calibration and threshold | A named consumer needs a probability interpretation or a selection threshold and protected data are adequate for calibration and assessment. | Start with reliability curves/`CalibrationDisplay` and grouped coverage versus selective error. Compare `CalibratedClassifierCV` or a frozen estimator with separate authorized calibration data. Choose a method and threshold on the development/calibration scope and assess on separate protected data for the decision. Advance only if the consumer benefits under an explicit policy. [Calibration](https://scikit-learn.org/stable/modules/calibration.html) · [Threshold selection](https://scikit-learn.org/stable/modules/classification_threshold.html) | Report provisional scores and preserve the existing decision policy. |
| NCE-12-C5 · Active assessment | Judgments are costly, the predictor is useful enough to prioritize discovery, and discovery has separate exposure from protected assessment. | Compare stratified and disagreement-based selection before Pyro `contrib.oed`. Use expected information gain for a declared parameter or decision and measure useful newly adjudicated information against the simpler route. Record exact discovery membership and selection. [OED](https://docs.pyro.ai/en/stable/contrib.oed.html) | Use simple discovery selection with a separate protected assessment population. |
| NCE-12-C6 · Population coverage inference | An explicit finite target population and valid independent probability-sample labels support a declared population coverage estimand, with comparable predictor outputs. | Compare design-appropriate labeled-only inference with `ppi_mean_pointestimate`/`ppi_mean_ci` for a simple valid sampling design. Use a frozen predictor and preserve weights and sampling units. Use grouped cross-fitting or design-specific uncertainty only after verifying support and assumptions. Advance if the estimate and interval are valid for the target population and prediction adds precision over the labeled baseline. Adaptive or purposive development labels do not qualify by themselves. [PPI guide](../../libraries/scientific_compute/ppi_py.md) · [Tagged implementation](https://github.com/aangelopoulos/ppi_py/blob/v0.2.3/ppi_py/ppi.py) | Report exact assessed denominators or valid labeled-only intervals. |
| NCE-12-C7 · Uncertain finite weights | NCE-11 provides an identifiable finite conditional fit and a consumer needs to distinguish uncertainty about weights from uncertainty among readings. | Use the per-draw normalized finite conditional likelihood, including its parameter-dependent partition, and preserve candidate-relative standing. Compare direct stable sums before `pyro.factor`, enumeration, structured guides or Funsor. Assess event unions, coherent alternatives and interval semantics separately. Advance on useful diagnostics and demonstrated numerical/operational fit. [Pyro inference](https://docs.pyro.ai/en/stable/inference_algos.html) | Retain fixed-weight finite inference and a separate operation reliability diagnostic. |
| NCE-12-C8 · Paired uncertainty | Independent source groups and the sampling assumptions support an uncertainty question beyond exact paired counts. | Use SciPy 1.18.1 `bootstrap(paired=True)` over the justified resampling units or a matched `permutation_test` when the selected null and exchangeability permit it. Report the unit, selection and sensitivity. [Bootstrap](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html) · [Permutation test](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html) | Keep paired counts and explicit disagreements for the frozen development frame. |

Keep `obs_mask` imputation, advanced Pyro guides, temporal or causal inference, and larger inference
runtimes deferred to a declared model and estimand. Unassessed attachment events retain their
observed status in the ordinary fit. [Pyro inference mechanisms](https://docs.pyro.ai/en/stable/inference_algos.html)
