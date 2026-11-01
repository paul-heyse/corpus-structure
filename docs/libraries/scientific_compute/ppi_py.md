# `ppi_py` — Comprehensive Python Library Overview

Version 0.2.3 · Research date: October 28, 2026 · Python · MIT License

Distribution: `ppi-python`\
Import: `ppi_py`\
Latest verified PyPI release: 0.2.3, published December 22, 2024.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



Primary sources

- Documentation: `https://ppi-py.readthedocs.io/en/latest/`
- Repository: `https://github.com/aangelopoulos/ppi_py`
- PyPI: `https://pypi.org/project/ppi-python/`

## 1. Purpose and conceptual architecture

`ppi_py` implements prediction-powered inference (PPI): statistical estimation and hypothesis testing that combine a relatively small collection of expensive, gold-standard observations with a much larger collection of inexpensive machine-learning predictions.

Its distinguishing capability is to exploit the information contained in imperfect predictions without generally requiring the prediction model to be unbiased, calibrated, or correctly specified.

Rather than accepting model predictions as ground truth, PPI uses observed prediction errors on the gold-standard sample to correct the estimates obtained from the larger predicted sample.

The library supports several complementary methodologies:

| Methodological family        | Principal capability                                                                  |
| ---------------------------- | ------------------------------------------------------------------------------------- |
| Classical PPI                | Bias-corrected parameter estimation and confidence intervals                          |
| PPI++                        | Data-adaptive variance reduction through power tuning                                 |
| Cross-PPI                    | Inference using predictions from models trained on overlapping labeled data           |
| Prediction-powered bootstrap | Confidence intervals for user-defined estimators                                      |
| Distribution-shift inference | Weighted inference and specialized label-shift analysis                               |
| Power analysis               | Cost-optimal labeled/unlabeled sample allocation                                      |
| Statistical baselines        | Comparisons with classical, semi-supervised, conformal, and post-prediction inference |

These are inference methods, not replacements for model-training libraries. `ppi_py` consumes predictions produced by external models and supplies the statistical machinery needed to estimate population quantities from them.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ppi-py.readthedocs.io\&sz=32)

ppi_py 0.2 documentation+2



### 1.1 The prediction-and-rectification principle

Let:

- \\(Y\\): gold-standard outcome.
- \\(\hat Y=f(X)\\): model-predicted outcome.
- \\(n\\): number of labeled observations.
- \\(N\\): number of additional observations with predictions but no gold-standard labels.

For mean estimation, the untuned prediction-powered estimator is:

\\[ \widehat{\mu}\_{\mathrm{PPI}} = \underbrace{\frac{1}{N}\sum\_{j=1}^{N}\hat Y_j^{\\,U}}\_{\text{Imputed estimate}} + \underbrace{\frac{1}{n}\sum\_{i=1}^{n}(Y_i-\hat Y_i)}\_{\text{Rectification}} \\]

The first term estimates the population mean using inexpensive predictions. The second estimates their average error using the labeled sample.

Under appropriate sampling and independence assumptions, the correction cancels systematic prediction bias.

The corresponding variance has the approximate form:

\\[ \operatorname{Var}(\widehat{\mu}\_{\mathrm{PPI}}) = \frac{\operatorname{Var}(Y-\hat Y)}{n} + \frac{\operatorname{Var}(\hat Y)}{N} \\]

This exposes the principal efficiency mechanism: when predictions closely track actual outcomes and the unlabeled collection is large, the variance of the residual correction can be much smaller than the variance of the original outcome.

The fundamental distinction is statistical validity versus statistical efficiency. An imperfect predictor can still support valid PPI; its predictive quality determines how much efficiency the method provides. Poor predictions may offer little benefit, motivating the power-tuning methods discussed below.

The same principle generalizes beyond means to quantiles, regression coefficients, and estimating equations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ppi-py.readthedocs.io\&sz=32)

ppi_py 0.2 documentation+1



## 2. Core inference capabilities

The released API primarily exposes paired functions for point estimation and confidence intervals. Regression functions receive labeled and unlabeled feature matrices as well as the corresponding response predictions; mean and quantile functions only require outcomes and predictions.

| Estimand                         | Point estimator              | Confidence interval | Important distinction                                            |
| -------------------------------- | ---------------------------- | ------------------- | ---------------------------------------------------------------- |
| Scalar or vector mean            | `ppi_mean_pointestimate`     | `ppi_mean_ci`       | Supports power tuning, weights, and multiple outcome coordinates |
| Population quantile              | `ppi_quantile_pointestimate` | `ppi_quantile_ci`   | Rectifies an empirical CDF, then inverts it                      |
| Linear regression coefficients   | `ppi_ols_pointestimate`      | `ppi_ols_ci`        | Targets the population least-squares projection                  |
| Logistic regression coefficients | `ppi_logistic_pointestimate` | `ppi_logistic_ci`   | Rectified logistic loss and gradient-based optimization          |
| Poisson regression coefficients  | `ppi_poisson_pointestimate`  | `ppi_poisson_ci`    | Count-response inference through a rectified Poisson objective   |

All five families are present in the v0.2.3 source. Poisson regression is an easily overlooked capability: its estimators exist in the released `ppi.py` module and are exported at package level, although the generated PPI API reference omits them.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ppi-py.readthedocs.io\&sz=32)

ppi_py 0.2 documentation+2



Primary source: `https://github.com/aangelopoulos/ppi_py/blob/v0.2.3/ppi_py/ppi.py`

### 2.1 Mean estimation and hypothesis testing

`ppi_mean_pointestimate` and `ppi_mean_ci` accept one-dimensional or multidimensional outcomes, allowing several related means to be estimated from the same labeled and unlabeled collections.

`ppi_mean_pval` additionally supports hypothesis testing against a specified `null` value. The documented testing interface focuses on a one-dimensional mean.

Consequential details:

- `alpha=0.1` is the default, corresponding to a nominal 90% confidence interval, not 95%.
- `alternative` accepts `two-sided`, `larger`, or `smaller`.
- `lam` controls how much information is borrowed from predictions.
- `lam_optim_mode` supports `overall` and `element`, allowing shared versus coordinate-specific tuning.
- Vector confidence intervals are returned coordinate-wise; they are not automatically simultaneous confidence regions.

The combination of vector means, weights, automatic tuning, and explicit p-values makes this family more capable than a simple predicted-mean correction.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ppi-py.readthedocs.io\&sz=32)

ppi_py 0.2 documentation+2



### 2.2 Quantile estimation through CDF rectification

Quantiles require a different mechanism from means. The library estimates a corrected cumulative distribution function:

\\[ \widehat F\_{\mathrm{PPI}}(t) = \widehat{\mathbb P}\_U(\hat Y\le t) + \widehat{\mathbb P}\_L(Y\le t) - \widehat{\mathbb P}\_L(\hat Y\le t) \\]

`ppi_quantile_pointestimate` then identifies a grid value whose rectified CDF is closest to the requested quantile level `q`.

`ppi_quantile_ci` instead evaluates the hypothesis that the corrected CDF equals `q` at each grid point and returns the extreme accepted grid values.

Grid selection is material:

- `exact_grid=False`: evaluates 5,000 evenly spaced values over the observed range.
- `exact_grid=True`: evaluates the sorted collection of observed outcome and prediction values.
- The exact-grid option eliminates the fixed-grid approximation; it does not mean that the resulting confidence interval has an unconditional finite-sample exact-coverage guarantee.

The rectified empirical CDF can be nonmonotone in finite samples because its components are added and subtracted. The implementation does not explicitly project it onto the space of valid monotone CDFs. Moreover, the CI routine returns the minimum and maximum accepted values, which can conceal disconnected acceptance regions; an empty acceptance set can cause an indexing failure.

These properties matter particularly for discrete distributions, ties, extreme quantiles, and small labeled samples.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 2.3 Regression as prediction-powered M-estimation

The regression implementations generalize the same principle from outcomes to loss functions and estimating equations.

For a parameter \\(\theta\\) and loss \\(\ell\_\theta(X,Y)\\), an idealized rectified objective is:

\\[ \widehat L\_\lambda(\theta) = \frac{1}{n}\sum_L \ell\_\theta(X,Y) + \lambda\left[ \frac{1}{N}\sum_U\ell\_\theta(X,\hat Y) - \frac{1}{n}\sum_L\ell\_\theta(X,\hat Y) \right] \\]

This preserves the expected target loss under the relevant sampling conditions, while predictions can reduce the variability of its estimating equations.

OLS. The target is the best linear projection of the true response onto the supplied covariates. It does not require the conditional response function to be exactly linear. The implementation uses least-squares machinery and sandwich-style covariance estimation, including inverse-Hessian and gradient-covariance calculations. Collinearity and poorly conditioned matrices remain consequential.

Logistic regression. The library rectifies logistic cross-entropy using actual binary outcomes and predicted responses. Predicted probabilities can contribute directly as soft responses in the objective; the prediction model need not itself be a logistic regression. Optimization uses a fitted classical logistic model for initialization and `scipy.optimize.minimize` with L-BFGS-B for the rectified objective. `optimizer_options` exposes optimizer configuration. This is inference for logistic regression coefficients, not calibration of the external classifier.

Poisson regression. The analogous implementation supports nonnegative count responses under a Poisson log-link objective, with Poisson regression initialization, rectified optimization, and coefficient intervals. It is valuable when large collections of predicted counts complement comparatively expensive measured counts; the presence of a Poisson objective does not itself establish that every count dataset satisfies a literal Poisson distribution.

Across these families, confidence intervals use gradients and Hessian-based asymptotic covariance estimates rather than a generic bootstrap. Feature design, scaling, numerical conditioning, and the definition of the regression estimand remain the caller's responsibility.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



## 3. PPI++: power tuning and variance reduction

PPI++ is one of the library's most important advanced capabilities. It addresses an inherent weakness of untuned PPI: using predictions at full strength can increase rather than decrease variance when predictions are weak.

For the mean, the tuned estimator is:

\\[ \widehat\mu\_\lambda = \overline{Y-\lambda\hat Y}\_L + \lambda\overline{\hat Y}\_U \\]

Its approximate variance is:

\\[ V(\lambda)= \frac{\operatorname{Var}(Y-\lambda\hat Y)}{n} + \frac{\lambda^2\operatorname{Var}(\hat Y)}{N} \\]

The cancellation of prediction bias is preserved for fixed \\(\lambda\\), while its value changes the precision of the resulting estimate.

| Setting       | Interpretation                                                                            |
| ------------- | ----------------------------------------------------------------------------------------- |
| `lam=0`       | Classical labeled-only estimator                                                          |
| `lam=1`       | Untuned prediction-powered estimator                                                      |
| `lam=None`    | Estimate a variance-reducing value from the available data                                |
| `0 < lam < 1` | Partially exploit predictions while retaining a stronger reliance on gold-standard labels |

### 3.1 How tuning generalizes to regression

For regression coefficients, the relevant quantity is not simply the correlation between \\(Y\\) and \\(\hat Y\\).

The code constructs gradients for true and predicted responses, estimates their covariance, and transforms them through an inverse Hessian. The optimal tuning parameter is then selected to reduce the variance of the parameter estimates.

This is significant because a predictor may have good aggregate accuracy but supply little information about a particular regression coefficient. Conversely, predictions may be especially informative for a coefficient even when global predictive metrics are modest.

The internal `_calc_lam_glm` helper supports optimization of total parameter variance or the variance of a selected coordinate. Calls using `clip=True` restrict the resulting tuning value to `[0,1]`. In the released mean interface, `lam_optim_mode='element'` can produce separate tuning coefficients for individual outcome dimensions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 3.2 Consequential tuning distinctions

- Adaptive versus predetermined tuning. A tuning parameter estimated from the labeled data is random, so the validity of its confidence interval relies on the corresponding PPI++ theory and regularity conditions, not solely on the algebraic unbiasedness of fixed-\\(\lambda\\) rectification.
- Shared versus coordinate-specific efficiency. A scalar tuning parameter can trade efficiency across coefficients. Coordinate-specific choices can improve individual intervals but need not define a single common multivariate optimization objective.
- Finite-sample variability. Estimated covariance and Hessian terms can themselves be unstable when the gold-standard sample is small.
- Implementation-specific behavior. Although the mean APIs expose `coord`, the v0.2.3 automatic tuning path passes `coord=None` to its internal optimizer. This is a reason to inspect the tagged implementation when coordinate-targeted tuning is consequential.

PPI++ therefore offers a native alternative to custom heuristics for deciding how strongly predictions should influence inference, without claiming that every adaptive interval will outperform classical inference in every finite sample.

Research basis: `https://arxiv.org/abs/2311.01453`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 3.3 Sample weighting and population targeting

Most standard PPI estimators expose separate `w` and `w_unlabeled` arguments.

These permit the labeled correction and unlabeled imputation components to be weighted differently. The released implementation typically normalizes each weight vector to have a mean of one, so multiplying all weights within a sample by a constant does not change the estimator.

Architecturally, this creates a route to importance-weighted or survey-like estimation without rewriting the rectification machinery. It does not estimate the weights, correct arbitrary selection bias automatically, or provide general complex-survey variance estimation. Validity still depends on the sampling design, the target population, and the appropriateness of the supplied weights.

Weight support is also not uniform across every family: the released Cross-PPI and `ppboot` interfaces do not expose the same weighting parameters as the core PPI estimators.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ppi-py.readthedocs.io\&sz=32)

ppi_py 0.2 documentation+2



## 4. Cross-PPI: inference when the predictor must be trained on the labeled sample

Classical PPI is especially straightforward when the prediction model is already available and can be treated as independent of the gold-standard observations used for rectification.

Cross-prediction-powered inference (Cross-PPI) addresses a different situation: the available labeled observations are also needed to train the prediction models.

Rather than reserving a separate subset for model training, Cross-PPI uses cross-fitting so that each labeled observation receives a prediction from a model that was not trained on that observation.

### 4.1 Released API

| Estimand              | Point estimator                   | Confidence interval    |
| --------------------- | --------------------------------- | ---------------------- |
| Mean                  | `crossppi_mean_pointestimate`     | `crossppi_mean_ci`     |
| Quantile              | `crossppi_quantile_pointestimate` | `crossppi_quantile_ci` |
| OLS coefficients      | `crossppi_ols_pointestimate`      | `crossppi_ols_ci`      |
| Logistic coefficients | `crossppi_logistic_pointestimate` | `crossppi_logistic_ci` |

All eight functions are documented for the released library.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ppi-py.readthedocs.io\&sz=32)

ppi_py 0.2 documentation



Source: `https://ppi-py.readthedocs.io/en/latest/crossppi.html`

### 4.2 Prediction layout and statistical mechanism

Cross-PPI takes two different prediction structures:

- `Yhat`: shape `(n,)`, containing out-of-fold predictions for the labeled observations.
- `Yhat_unlabeled`: shape `(N, K)`, containing predictions from each of the `K` fold-trained models for every unlabeled observation.

For the mean, the corresponding estimator is:

\\[ \widehat\mu\_{\mathrm{cross}} = \frac{1}{NK}\sum\_{j=1}^{N}\sum\_{k=1}^{K}\hat Y\_{jk}^{\\,U} + \frac{1}{n}\sum\_{i=1}^{n}(Y_i-\hat Y_i^{\\,\mathrm{OOF}}) \\]

The cross-fitted predictions control training-data reuse, while averaging predictions from all fold models exploits the available unlabeled observations.

The consequential architectural boundary is that the caller performs the cross-validation, model fitting, feature preprocessing, and prediction generation. `crossppi_*` consumes the resulting arrays; it is not a cross-validation training framework.

This distinction makes Cross-PPI compatible with many external modeling systems, including specialized scientific predictors and LLM-based label generation, without requiring those predictors to conform to a scikit-learn estimator interface.

### 4.3 Advanced distinctions

Cross-fitting versus ordinary validation. Out-of-fold predictions are needed for inference, not merely to estimate the prediction model's accuracy. Predictions generated by a model trained on the same observation can introduce dependence that invalidates a naive correction.

Multiple models versus model ensembling. The `(N,K)` structure is not an arbitrary ensemble interface. Its columns represent the fold-trained models corresponding to the labeled out-of-fold prediction construction.

Variance estimation. Cross-PPI CI functions expose `bootstrap_data`, a dictionary of externally supplied arrays for variance estimation. This is distinct from calling `ppboot`; the API does not automatically retrain models and generate a full cross-fitting bootstrap.

Capability differences. The released Cross-PPI interface does not expose the standard PPI family's `lam`, `w`, and `w_unlabeled` controls. Consequently, Cross-PPI is not simply classical PPI with an automatic cross-validation switch.

Method selection. Cross-PPI is relevant when preserving gold-standard labels for both model training and statistical correction matters. If a suitable independent predictor already exists, classical PPI or PPI++ provides a simpler statistical setup and explicit power-tuning controls.

The underlying research evaluates cross-prediction against training/holdout alternatives, but reported efficiency improvements should not be treated as universal guarantees for arbitrary model-training algorithms or dependence structures.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ppi-py.readthedocs.io\&sz=32)

ppi_py 0.2 documentation+1



Research: `https://arxiv.org/abs/2309.16598`

## 5. PPBoot: prediction-powered inference for user-defined estimators

`ppboot` is arguably the most general-purpose released extension point in the package.

The specialized PPI estimators depend on problem-specific gradients, Hessians, CDF inversions, or asymptotic variance formulas. PPBoot provides a different route: construct a rectified statistic and estimate its sampling distribution by bootstrap.

### 5.1 Callable-based inference

The released signature is:

`ppboot(estimator, Y, Yhat, Yhat_unlabeled, X=None, X_unlabeled=None, lam=None, n_resamples=1000, n_resamples_lam=50, alpha=0.1, alternative='two-sided', method='percentile')`

The supplied `estimator` is a callable accepting either `estimator(Y)` or `estimator(X, Y)`.

It may return a scalar or a fixed-dimensional numerical result. This permits statistics not covered by the specialized APIs, including correlations and other estimators for which deriving a PPI-specific asymptotic variance would be inconvenient.

Conceptually, for a statistical functional \\(T\\), the implemented rectification takes the form:

\\[ \widehat T\_{\mathrm{PPBoot}} = T(L\_{\mathrm{true}}) + \lambda\left[ T(U\_{\mathrm{pred}}) - T(L\_{\mathrm{pred}}) \right] \\]

Here the estimator is evaluated three times on actual labeled data, predicted labeled data, and predicted unlabeled data.

For nonlinear estimators, this is not automatically a finite-sample unbiased identity. Its validity depends on the bootstrap method's statistical assumptions and the behavior of the estimator. The published work supplies the methodological justification beyond the specialized convex M-estimation setting.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 5.2 Bootstrap design

The implementation preserves the relevant observation-level dependencies:

- Labeled outcomes, predictions, and optional covariates are resampled together.
- Unlabeled predictions and their covariates are resampled together, independently of the labeled sample.
- The rectified estimator is recomputed for each bootstrap replicate.
- An optional preliminary bootstrap stage estimates `lam` using covariance and variance of the estimator outputs.

For automatic tuning, the default is 50 preliminary resamples; the main interval calculation uses 1,000 resamples.

Supported interval construction methods are `percentile` and `basic`. The source does not implement BCa, studentized, or other advanced bootstrap interval variants through this interface.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 5.3 When this extension is consequential

PPBoot can eliminate custom influence-function derivations when an existing numerical estimator can be evaluated on both measured and predicted outcomes.

Its usefulness is conditional on several distinctions:

- The estimator must have appropriate statistical regularity; merely accepting a Python callable does not make every statistic bootstrap-valid.
- Both the true-response and predicted-response calls must represent comparable estimands.
- Computational expense scales with the number of bootstrap replicates and the cost of the estimator. Repeated optimization or matrix decomposition can dominate runtime.
- Automatically tuning `lam` introduces an additional bootstrap stage, and a small tuning-resample count can make that choice noisy.
- Standard PPBoot does not expose the per-sample weighting interface of the specialized PPI estimators.
- A generic bootstrap is not a substitute for cluster-aware, temporal, or otherwise design-specific resampling when observations are dependent.

One-sided interval caveat: the v0.2.3 source returns `(-inf, upper_bound)` for `alternative='larger'` and `(lower_bound, inf)` for `alternative='smaller'`. That is opposite to the conventional direction suggested by those alternative names. This is an observed source-level inconsistency worth accounting for when interpreting one-sided results.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



Primary sources:

`https://github.com/aangelopoulos/ppi_py/blob/v0.2.3/ppi_py/ppi.py`

`https://arxiv.org/abs/2405.18379`

## 6. Distribution shift and classification-frequency inference

The library has two materially different ways of addressing population differences: weighted standard inference and a specialized label-shift estimator.

### 6.1 Weighted PPI under distribution differences

The standard PPI estimators accept observation weights, which can support inference for a target distribution different from the raw sampling distribution.

For example, appropriate importance weights may reweight source observations toward a target covariate distribution, provided the requisite density-ratio assumptions and support overlap hold.

`ppi_py` handles the weighted statistical calculations, but it does not supply an end-to-end density-ratio estimation system, covariate-shift detector, or general domain-adaptation framework.

A user-supplied weight vector is therefore a mechanism for expressing the population target, not proof that the target has been correctly represented.

### 6.2 Explicit label-shift confidence intervals

`ppi_distribution_label_shift_ci` supports inference on a discrete label distribution under label shift.

Its main inputs are `Y`, `Yhat`, `Yhat_unlabeled`, `K`, and `nu`.

Let \\(f\\) be the unknown target-population distribution over \\(K\\) classes and \\(\nu\\) a vector of class-specific values. The function estimates a confidence interval for:

\\[ \theta=\nu^\top f \\]

The implementation proceeds by constructing a class-conditional confusion matrix from the labeled observations:

\\[ A\_{jk}=P(\hat Y=j\mid Y=k) \\]

It then uses the predicted-label frequencies in the target population and an inverse of the estimated confusion matrix to estimate the target label frequencies:

\\[ \widehat f=A^{-1}\widehat q \\]

where \\(\widehat q\\) denotes the target predicted-label distribution.

The interval construction combines uncertainty from the confusion-matrix estimate and the target predicted frequencies, including concentration bounds and an intermediate error allocation controlled by `delta`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 6.3 Important assumptions and API details

Label shift is not covariate shift. The method relies on the relationship between true classes and predicted classes remaining transportable across populations. It does not correct arbitrary changes to \\(P(X\mid Y)\\) or prediction behavior.

Confusion-matrix invertibility matters. The source explicitly computes a matrix inverse. Missing gold-standard classes, zero columns, or near-linearly dependent confusion-matrix columns can cause failure or severely unstable estimates.

Discrete inputs are expected. `Yhat` and `Yhat_unlabeled` are used as class labels in constructing frequencies. A continuous probability matrix is not directly the same input representation.

The `nu` parameter generalizes the target. An indicator vector can select a class prevalence; a more general bounded vector represents a linear population summary.

Output semantics require care. `return_counts=True` is the default and produces count bounds; `return_counts=False` gives bounds on the corresponding probability or mean quantity. The count path additionally uses a binomial inversion and allocates error through `delta`.

This is a specialized, useful native capability that could otherwise require separate confusion-matrix inversion and uncertainty propagation code. It should not be conflated with arbitrary multiclass classification evaluation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



Source: `https://ppi-py.readthedocs.io/en/latest/ppi.html`

## 7. Power analysis and cost-optimal sample allocation

The power-analysis module extends the library upstream from estimation to statistical data-acquisition design.

It addresses an important economic question: when true observations are expensive but model predictions are cheap, how many of each should be obtained?

### 7.1 Available estimators

| API                  | Information supplied                          |
| -------------------- | --------------------------------------------- |
| `ppi_power`          | Assumed PPI correlation and per-sample costs  |
| `ppi_mean_power`     | Labeled pilot outcomes and their predictions  |
| `ppi_ols_power`      | Labeled pilot data for an OLS coefficient     |
| `ppi_logistic_power` | Labeled pilot data for a logistic coefficient |
| `ppi_poisson_power`  | Labeled pilot data for a Poisson coefficient  |

The regression-specific methods estimate the relevant correlation using the gradients and inverse-Hessian transformation associated with the targeted coefficient. This is more informative than simply using a model-wide prediction score.

Source: `https://ppi-py.readthedocs.io/en/latest/ppi_power_analysis.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ppi-py.readthedocs.io\&sz=32)

ppi_py 0.2 documentation+1



### 7.2 Two optimization modes

Fixed budget — maximize information. Supply `budget`; the library searches for a labeled/unlabeled allocation intended to maximize effective sample size under the specified costs.

Fixed precision — minimize cost. Supply `effective_n`; the library searches for the cheapest allocation meeting a classical-equivalent effective sample size.

The optional `n_max` constrains the total number of observations, defined in the API as \\(n+N\\).

The cost model distinguishes the cost of acquiring covariates (`cost_X`), obtaining a gold-standard label (`cost_Y`), and generating a prediction (`cost_Yhat`).

The result is a dictionary containing `n`, `N`, `cost`, `effective_n`, and `ppi_corr`. The source explicitly gives precedence to `budget` if both optimization targets are supplied.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ppi-py.readthedocs.io\&sz=32)

ppi_py 0.2 documentation+1



### 7.3 Effective sample size and informativeness

For the formulation used in the source, the effective sample size is:

\\[ n\_{\mathrm{eff}} = \frac{n(n+N)}{n+(1-\rho^2)N} \\]

where \\(\rho\\) is the relevant prediction-powered correlation.

This captures several useful boundaries.

If \\(\rho\\) is near zero, inexpensive predictions contribute little precision. If the correlation is strong and prediction costs are low, a larger predicted sample can reduce the amount of gold-standard labeling needed. If predictions are expensive, conventional labeled-only inference may remain economically preferable.

Importantly, `effective_n` is a precision-equivalence metric, not the actual observed sample size and not a directly calculated probability of rejecting a specified null hypothesis.

The optimal allocation is conditional on the cost model and estimated correlation. Uncertainty in pilot estimates, distribution changes, fixed infrastructure costs, and additional operational constraints are not automatically resolved by the allocation routine.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



Research: `https://doi.org/10.31235/osf.io/j3bnt`

## 8. Classical and alternative-method baselines

`ppi_py` also provides comparison implementations that are useful for separating genuine prediction-powered gains from gains attributable to other statistical methods.

| Family                                 | Functions                                                                                 | Distinguishing use                                                          |
| -------------------------------------- | ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Labeled-only inference                 | `classical_mean_ci`, `classical_quantile_ci`, `classical_ols_ci`, `classical_logistic_ci` | Baseline uncertainty using actual observations                              |
| Conventional semi-supervised inference | `semisupervised_mean_ci`                                                                  | Mean inference using features and internal cross-fitting                    |
| Conformal-based mean interval          | `conformal_mean_ci`                                                                       | Distribution-free coverage approach with conservative Bonferroni adjustment |
| Earlier post-prediction inference      | `postprediction_ols_ci`                                                                   | Historical comparison without general coverage guarantees                   |
| Logistic fitting utility               | `logistic`                                                                                | Classical coefficient estimation helper                                     |

The distinctions matter more than the availability of the functions.

`semisupervised_mean_ci` accepts labeled and unlabeled features and a number of cross-fitting folds. Unlike the main PPI API, it incorporates a particular estimation procedure rather than simply consuming an already-produced array of predictions.

`conformal_mean_ci` constructs prediction intervals for unlabeled outcomes and aggregates their bounds. The documentation explicitly notes that its Bonferroni-corrected form can be extremely conservative and that disabling the correction forfeits its stated coverage guarantee.

`postprediction_ols_ci` is included for comparison and is explicitly documented as lacking general coverage guarantees unless the predictor is perfect. It should not be treated as a statistically equivalent replacement for PPI.

More generally, prediction-powered inference targets population parameters, whereas ordinary conformal prediction generally targets coverage of future individual outcomes or sets. Both involve uncertainty, but the estimands and guarantees differ.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ppi-py.readthedocs.io\&sz=32)

ppi_py 0.2 documentation+1



Source: `https://ppi-py.readthedocs.io/en/latest/baselines.html`

## 9. Development-branch extension: Predict-Then-Debias

Version distinction: present in the examined upstream `main` branch, not part of the verified v0.2.3 package-level exports.

A significant post-release extension is present in `ppi_py/ptd.py`: Predict-Then-Debias (PTD), motivated by prediction-powered inference with imputed covariates and nonuniform sampling.

The released PPI regression APIs assume that the true covariates `X` are available, even when the response `Y` is predicted. PTD addresses the more general setting where covariates themselves may also be imputed.

The development-branch functions include:

- `ptd_bootstrap`
- `ptd_linear_regression`
- `ptd_logistic_regression`

The generic `ptd_bootstrap` accepts a callable estimator, actual labeled data, predicted labeled data, predicted unlabeled data, and separate sampling weights.

Its defining extension is a tuning matrix, replacing the usual scalar tuning parameter. The exposed options are `optimal_diagonal`, `optimal`, and `None` for an identity matrix.

For a vector-valued statistic \\(T\\), the rectification has the general structure:

\\[ \widehat\theta\_{\mathrm{PTD}} = T(L\_{\mathrm{true}}) + \Lambda\left[T(U\_{\mathrm{pred}})-T(L\_{\mathrm{pred}})\right] \\]

where \\(\Lambda\\) is a matrix that can allow different parameter coordinates to borrow information from different components of the predicted statistic.

That is a material generalization of scalar power tuning: when several coefficients respond differently to errors in imputed covariates, matrix-valued tuning offers a more expressive variance-reduction mechanism.

The development code supplies bootstrap-derived tuning and intervals, with `B=2000` and `alpha=0.05` defaults. The two regression wrappers use statsmodels-based fitting and return the tuning matrix, point estimates, and intervals.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



Release boundary: the `main` package initializer imports `.ptd`, while the v0.2.3 initializer does not. Accordingly, these functions should be regarded as upstream development capabilities rather than dependable APIs of the published 0.2.3 distribution without separately verifying their packaging and behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



Sources:

`https://github.com/aangelopoulos/ppi_py/blob/main/ppi_py/ptd.py`

`https://arxiv.org/abs/2501.18577`

## 10. Implementation architecture and integration boundaries

### 10.1 Numerical stack

The released implementation relies on a conventional Python numerical-statistical stack:

| Component    | Role                                                                 |
| ------------ | -------------------------------------------------------------------- |
| NumPy        | Array-oriented calculations and covariance operations                |
| SciPy        | Optimization, numerical root finding, and probability distributions  |
| statsmodels  | Classical regression, standard errors, hypothesis-testing utilities  |
| scikit-learn | Initial regression fits and selected supporting estimators           |
| Numba        | Compiled numerical kernels for several gradient/Hessian calculations |
| pandas       | Data handling and interoperability utilities                         |
| `gdown`      | Downloading example datasets                                         |

This is not an independent statistical computation engine, GPU inference system, or model-training framework. Most of the public interface is NumPy-array-oriented, and callers using other data representations need to provide compatible numerical arrays.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 10.2 Input contracts and responsibility boundaries

The core methods assume correctly aligned data:

| Input            | Meaning                                                |
| ---------------- | ------------------------------------------------------ |
| `Y`              | Gold-standard outcomes for labeled observations        |
| `Yhat`           | Predictions for those same labeled observations        |
| `Yhat_unlabeled` | Predictions for additional unlabeled observations      |
| `X`              | Covariates of the labeled observations, where required |
| `X_unlabeled`    | Covariates of the unlabeled observations               |

Correct row correspondence is essential. A prediction attached to the wrong gold-standard observation corrupts the residual correction, even if the arrays have otherwise valid shapes.

For standard regression methods, the feature matrices must represent the same covariate definition and coefficient parameterization. Intercept handling is not universally automatic: the released logistic implementation, for example, initializes a scikit-learn model with `fit_intercept=False`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



External responsibilities include model training and prediction generation, data selection, missing-data treatment, sampling-weight construction, and assessment of data dependence. The example-dataset loader in `ppi_py.datasets` is not a general data-ingestion or label-management framework.

### 10.3 Practical statistical boundaries

The most consequential limitations can be grouped into three categories.

Statistical identification and coverage

- Prediction-model misspecification is tolerated only within the assumptions of the inference procedure. It does not eliminate the need for suitable labeled sampling, trustworthy gold-standard outcomes, or correct target-population alignment.
- Standard confidence intervals depend on asymptotic or method-specific arguments. Nominal `alpha` is not a universal finite-sample coverage guarantee.
- Clustered observations, longitudinal dependence, adaptive data collection, selection effects, and complex surveys can require statistical adjustments beyond the exposed interfaces.
- Confidence intervals for multiple regression coefficients or vector means are coordinate-wise unless a separate simultaneous-inference procedure is applied.

Numerical robustness

- Regression confidence intervals depend on estimated gradient covariances and Hessian inversions. Rank deficiencies, separation, weak identification, or extreme weights can destabilize inference.
- Quantile inversion is grid-based and can be sensitive to discreteness and empty accepted sets.
- Label-shift inversion requires informative confusion matrices and adequate representation of every relevant class.
- Bootstrap intervals depend on the estimator's behavior and can be computationally expensive.

API and source-level behavior

- `ppi_mean_ci` in v0.2.3 does not forward a nondefault `alternative` argument through its recursive `lam=None` branch. A requested one-sided interval can consequently revert to the default two-sided behavior.
- `ppi_mean_pval` computes automatic tuning without the `clip=True` argument used by `ppi_mean_ci`, so the internal tuning behavior is not identical.
- Power-analysis coordinate indices are documented as zero-based in the regression-specific functions, despite some generic PPI descriptions using mathematical one-based notation. Concrete NumPy indexing should be resolved against the specific API.
- As noted above, `ppboot` has an apparent one-sided interval-direction inconsistency.

These are observations from the tagged source, not claims based on executing a test suite. They illustrate why release-specific source inspection matters for inference code, where parameter-handling differences can alter statistical meaning.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+3



## 11. Capability interactions and architectural significance

The library's principal value is not merely its collection of estimators. It is the ability to make different statistical and economic decisions while retaining a consistent prediction-plus-correction framework.

| Problem shape                                      | Native capability or combination               | What it can avoid                                                                               |
| -------------------------------------------------- | ---------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Large predicted sample, limited measured outcomes  | Mean/quantile PPI                              | Treating predictions as truth or writing bespoke bias corrections                               |
| Highly variable prediction quality                 | PPI++ tuning                                   | Hand-designed blending heuristics                                                               |
| Several related population outcomes                | Vector mean inference with element-wise tuning | Duplicated scalar estimation procedures                                                         |
| Regression on partially labeled outcomes           | PPI OLS/logistic/Poisson                       | Deriving rectified objectives and sandwich variances manually                                   |
| Predictor trained using the available gold labels  | Cross-PPI                                      | A separate holdout strategy solely to protect the correction sample                             |
| Custom scientific estimand                         | PPBoot                                         | Problem-specific asymptotic derivations, where bootstrap conditions are suitable                |
| Target population differs from sampling population | Weighted PPI or label-shift CI                 | Some custom importance-weighted estimation or classification-frequency correction logic         |
| Gold labels have a substantial acquisition cost    | Power-analysis functions                       | Ad hoc allocation of labeling versus prediction budgets                                         |
| Covariates as well as outcomes are predicted       | PTD on upstream `main`                         | Scalar-only rectification and custom matrix-valued corrections, subject to release availability |

Several distinctions are especially useful when selecting among these mechanisms.

PPI++ versus Cross-PPI: the former optimizes the statistical use of predictions; the latter addresses dependence created by training prediction models on the gold-standard sample. They solve different problems and are not interchangeable switches in the released interface.

Specialized PPI versus PPBoot: specialized estimators expose efficient, problem-specific statistical calculations; PPBoot broadens the class of possible estimands by accepting an arbitrary callable, at the cost of repeated estimator evaluation and bootstrap assumptions.

Standard weighting versus label shift: weighting expresses a target population through per-observation contributions; label-shift inference estimates a class distribution through a stable confusion mechanism. The correct choice depends on the assumed relationship between source and target populations.

PPI++ versus power analysis: PPI++ determines how much existing predictions should influence an estimate. Power analysis determines how many labeled and predicted observations may be economically valuable before collecting more data. These are complementary decisions driven by related measures of informativeness.

PPI regression versus PTD: stable PPI regression treats covariates as observed and outcomes as potentially predicted. Development-branch PTD expands the imputation model to covariates and uses more expressive tuning matrices.

The overarching architectural opportunity is to separate prediction generation, statistical correction, and sampling design without forcing the prediction model to be statistically correct. The limits of that separation are set by data dependence, the chosen estimand, and the assumptions required for uncertainty quantification.

## 12. Primary-source reference map

Direct URLs are provided as plain text for independent reuse.

| Topic                                             | Primary source                                                      |
| ------------------------------------------------- | ------------------------------------------------------------------- |
| Released PPI estimators and statistical utilities | `https://github.com/aangelopoulos/ppi_py/blob/v0.2.3/ppi_py/ppi.py` |
| Cross-PPI APIs                                    | `https://ppi-py.readthedocs.io/en/latest/crossppi.html`             |
| Baseline inference                                | `https://ppi-py.readthedocs.io/en/latest/baselines.html`            |
| Power analysis                                    | `https://ppi-py.readthedocs.io/en/latest/ppi_power_analysis.html`   |
| Release history                                   | `https://github.com/aangelopoulos/ppi_py/releases`                  |
| Original prediction-powered inference             | `https://arxiv.org/abs/2301.09633`                                  |
| PPI++                                             | `https://arxiv.org/abs/2311.01453`                                  |
| Cross-prediction-powered inference                | `https://arxiv.org/abs/2309.16598`                                  |
| Prediction-powered bootstrap                      | `https://arxiv.org/abs/2405.18379`                                  |
| Predict-Then-Debias and imputed covariates        | `https://arxiv.org/abs/2501.18577`                                  |
| Development-branch PTD implementation             | `https://github.com/aangelopoulos/ppi_py/blob/main/ppi_py/ptd.py`   |

The most distinctive capabilities of `ppi_py` are therefore variance-optimized prediction rectification, cross-fitted inference, estimator-agnostic bootstrapping, specialized distribution-shift correction, and economically optimized sample allocation. Together, they provide considerably more than confidence intervals around machine-learning predictions: they support principled inference about real population quantities using imperfect predictions as an additional, potentially powerful source of information.