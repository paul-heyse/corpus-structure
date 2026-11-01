# statsmodels 0.15.0 — Comprehensive Python Library Overview

Research date: October 27, 2026 | Target: statsmodels 0.15.0 (stable, released August 27, 2026) | Language: Python

statsmodels is a statistical modeling, estimation, inference, and diagnostics framework. Its principal strength is the integration of statistical model specification, numerical estimation, hypothesis testing, uncertainty quantification, residual analysis, and prediction through reusable Python interfaces.

Unlike libraries primarily concerned with numerical optimization or predictive accuracy, statsmodels emphasizes understanding the statistical structure of data and estimating interpretable model parameters with associated measures of uncertainty.

It combines three broad capabilities:

1. Statistical model estimation: Regression, generalized linear models, hierarchical and correlated-data models, discrete choice, count processes, survival analysis, and multivariate models.
2. Time-series and dynamical modeling: Autoregressive models, state-space systems, Kalman filtering and smoothing, structural decomposition, regime switching, cointegration, and forecasting.
3. Statistical inference and analytical infrastructure: Hypothesis tests, covariance estimation, diagnostics, power analysis, treatment effects, missing-data methods, resampling, and distributional modeling.

The library is particularly valuable when a system needs more than parameter estimates or predictions: it needs statistically meaningful uncertainty, interpretable effects, formal model comparisons, and diagnostic evidence.

Version 0.15.0 is a significant release. It introduces a formula-engine abstraction supporting Patsy and Formulaic, Polars input interoperability, new robust statistical estimators, additional tests, consistent random-number handling, and more structured statistical result types. Some newly introduced APIs are explicitly preliminary or experimental.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



Primary references:

- Official versioned documentation: [https://www.statsmodels.org/v0.15.0/](https://www.statsmodels.org/v0.15.0/?utm_source=chatgpt.com)
- User guide: [https://www.statsmodels.org/v0.15.0/user-guide.html](https://www.statsmodels.org/v0.15.0/user-guide.html?utm_source=chatgpt.com)
- API reference: [https://www.statsmodels.org/v0.15.0/api.html](https://www.statsmodels.org/v0.15.0/api.html?utm_source=chatgpt.com)
- Release 0.15.0 notes: [https://www.statsmodels.org/v0.15.0/release/](https://www.statsmodels.org/v0.15.0/release/?utm_source=chatgpt.com)

## 1. Architectural orientation

### 1.1 Core conceptual model

Most statsmodels estimators follow a common lifecycle:

Data and model specification

Response, regressors, formulas, distributional assumptions, dependence structure

Statistical model

Likelihood, moments, estimating equations, state-space representation, or least-squares objective

Numerical estimation

Linear algebra, iterative estimation, optimization, filtering, or smoothing

Fitted results object

Parameters, covariance, fitted values, statistical tests, diagnostics, predictions

The separation between model definitions and fitted results is one of the library's most useful architectural properties.

- Model objects represent statistical assumptions, data and estimator configuration.
- Estimation methods such as `fit()`, `fit_regularized()`, `filter()`, or `smooth()` perform the applicable computation.
- Results objects encapsulate parameter estimates, estimated uncertainty, goodness-of-fit statistics, residuals, and model-specific post-estimation operations.
- Statistical utilities provide reusable diagnostics, distributional methods, tests, and comparisons independently of a particular fitted model.

This creates a common conceptual interface across otherwise very different estimation methodologies. It is not a promise that every estimator implements identical methods or inference semantics.

### 1.2 Capability map

| Functional domain                       | Principal capabilities                                                                                 |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Linear and robust regression            | OLS, WLS, GLS, GLSAR, robust M-estimation, quantile regression, rolling and recursive regression       |
| Generalized regression                  | GLM families and links, GAM splines, regularization, offsets and exposure                              |
| Dependent and hierarchical observations | GEE, linear mixed effects, Bayesian generalized mixed models                                           |
| Discrete and count processes            | Binary, multinomial, ordinal, conditional, Poisson, negative binomial, zero-inflated and hurdle models |
| Temporal modeling                       | AR, ARDL, UECM, ARIMA, SARIMAX, exponential smoothing, structural models                               |
| State-space and regimes                 | Kalman filtering, smoothing, simulation, custom state-space systems, Markov switching                  |
| Multivariate time series                | VAR, SVAR, VECM, VARMAX, dynamic factors, impulse responses, forecast error decomposition              |
| Statistical inference                   | Robust covariance, Wald and likelihood tests, ANOVA, diagnostics, bootstrapping and resampling         |
| Specialized statistics                  | Survival analysis, treatment effects, GMM, empirical likelihood, nonparametrics, distributions         |
| Data and reporting infrastructure       | Formula engines, NumPy/pandas/Polars integration, missing-data models, statistical tables and plots    |

The remaining sections examine the functional families, their less obvious mechanisms, and the distinctions that matter when composing them.

## 2. Regression and generalized statistical models

### 2.1 Linear regression, covariance structures, and time-varying estimation

The linear regression family shares a common structural equation,

\\[ y=X\beta+\varepsilon,\qquad \operatorname{Cov}(\varepsilon)=\Sigma \\]

but supports different assumptions and treatments of the error covariance matrix.

| Model                                                                               | Distinctive capability                                                                     |
| ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `OLS`                                                                               | Ordinary least squares; standard baseline for linear conditional means                     |
| `WLS`                                                                               | Observation-specific weights for known or estimated heteroskedasticity                     |
| `GLS`                                                                               | General, potentially nondiagonal observation error covariance                              |
| `GLSAR`                                                                             | Feasible GLS with autoregressive error structure                                           |
| `QuantReg`                                                                          | Conditional quantile estimation rather than only conditional means                         |
| `RecursiveLS`                                                                       | Sequential parameter estimation, recursive residuals, parameter stability analysis         |
| `RollingOLS`, `RollingWLS`                                                          | Window-local parameter trajectories                                                        |
| `ProcessMLE`                                                                        | Joint mean, scale, and correlation modeling through Gaussian process covariance structures |
| `SlicedInverseReg`, `PrincipalHessianDirections`, `SlicedAverageVarianceEstimation` | Supervised sufficient-dimension-reduction techniques                                       |

`RecursiveLS` and `RollingOLS` are particularly useful distinctions. Rolling regression repeatedly analyzes moving windows; recursive least squares updates estimates as observations accumulate and supports statistical stability analysis. Neither is automatically equivalent to a latent time-varying parameter model, for which state-space methods may be more appropriate.

`ProcessMLE` is another easily overlooked capability: it models structured dependence through a Gaussian covariance process rather than requiring independent residuals. It is distinct from the general-purpose Gaussian-process regression systems commonly found in machine-learning libraries.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0



Source: [https://www.statsmodels.org/stable/regression.html](https://www.statsmodels.org/stable/regression.html?utm_source=chatgpt.com)

### 2.2 Robust inference versus robust estimation

These solve fundamentally different problems.

Robust covariance estimation keeps the fitted regression coefficients but changes the covariance estimator used for statistical inference.

Important options include:

- Heteroskedasticity-consistent HC0–HC3 covariance estimators.
- HAC/Newey–West covariance for serially correlated observations.
- Cluster-robust covariance, including CRV1 and the new 0.15.0 CRV3 and cluster-jackknife variants.
- Panel-oriented HAC covariance, including `hac-panel` and Driscoll–Kraay-style `hac-groupsum`.

`RegressionResults.get_robustcov_results()` constructs a new results object in which subsequent parameter tests and intervals use the selected covariance estimate. Cluster estimators require group identifiers; HAC estimators require temporal bandwidth choices; panel HAC methods impose additional ordering and structure requirements.

Robust regression, in contrast, changes how the coefficients themselves are estimated.

`RLM` supports M-estimation through configurable robust loss/norm functions such as Huber, Hampel, Tukey-type redescending norms, and associated robust scale estimators.

Version 0.15.0 adds high-breakdown robust covariance/scale tools (`CovDetMCD`, `CovDetS`, `CovDetMM`) and resistant regression (`RLMDetSMM`). The release notes explicitly characterize several of these APIs as preliminary or experimental.

Thus, robust standard errors do not make the fitted coefficients resistant to outliers, while robust regression does not automatically solve clustered-data dependence or all inferential problems.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+2



Sources:

- [https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html?utm_source=chatgpt.com)
- [https://www.statsmodels.org/stable/rlm.html](https://www.statsmodels.org/stable/rlm.html?utm_source=chatgpt.com)
- [https://www.statsmodels.org/stable/release/](https://www.statsmodels.org/stable/release/?utm_source=chatgpt.com)

### 2.3 Generalized linear models: families, links, and regularization

`GLM` separates the conditional mean relationship from the response variance structure:

\\[ g(\mathbb E[Y\mid X])=X\beta,\qquad \operatorname{Var}(Y\mid X)=\phi V(\mu)/w \\]

It provides a composable system of distribution families, link functions, variance functions, observation weights, offsets, and exposure.

Supported families include Gaussian, Binomial, Poisson, Gamma, Inverse Gaussian, Negative Binomial, and Tweedie, with links including identity, log, logit, probit, complementary log-log, and power functions.

Advanced mechanisms include:

- `offset` and `exposure` for known contributions to the linear predictor, particularly count rates.
- `freq_weights` and `var_weights`, which have different statistical interpretations.
- `fit_constrained()` for coefficient restrictions.
- `fit_regularized()` for elastic-net regularization and coefficient-specific penalty weights.
- `GLMResults.get_margeff()`, added in 0.15.0, for marginal effects.
- Access to score, Hessian, information matrix, deviance, Pearson residuals, and likelihood-related quantities.
- Extensible family, link, and variance-function machinery.

Version 0.15.0 also introduces an `l1_slsqp` solver as an alternative to coordinate descent in `GLM.fit_regularized()`. The new option handles L1-only penalization through a constrained reformulation; existing elastic-net support remains available.

An important distinction: the GLM Negative Binomial family typically treats its dispersion parameter as specified, whereas the standalone discrete `NegativeBinomial` model can estimate dispersion. Likewise, a Tweedie GLM and a zero-inflated count model represent different distributional assumptions even when both accommodate many zeros.

Post-selection inference from penalized regression requires particular care: conventional confidence intervals following variable selection are not automatically valid.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+2



Sources:

- [https://www.statsmodels.org/stable/glm.html](https://www.statsmodels.org/stable/glm.html?utm_source=chatgpt.com)
- [https://www.statsmodels.org/stable/generated/statsmodels.genmod.generalized_linear_model.GLM.fit_regularized.html](https://www.statsmodels.org/stable/generated/statsmodels.genmod.generalized_linear_model.GLM.fit_regularized.html?utm_source=chatgpt.com)

### 2.4 Generalized additive models

`GLMGam` extends GLMs with smooth, penalized functions of predictors:

\\[ g(\mu)=X\beta+\sum_j f_j(z_j) \\]

Principal mechanisms include:

- B-spline bases through `BSplines`.
- Cyclic splines and polynomial smoothers.
- Penalty matrices for controlling function roughness.
- Smoothing-parameter selection, including cross-validation mechanisms.
- Parametric and nonlinear terms in the same model.
- Partial-effect visualization and prediction.

This allows interpretable nonlinear effects without building a completely custom nonlinear likelihood estimator.

GAMs differ from high-dimensional machine-learning models in emphasizing explicit smooth functions, controlled complexity, and model-based inference. The appropriate smoothing penalty and uncertainty calculations depend on the modeling assumptions.

The GAM framework has historically carried experimental qualifications; its interfaces should be evaluated individually rather than assuming every spline and inference combination is equally mature.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0



Source: [https://www.statsmodels.org/stable/gam.html](https://www.statsmodels.org/stable/gam.html?utm_source=chatgpt.com)

## 3. Discrete outcomes, correlated observations, and hierarchical models

### 3.1 Discrete-choice and count modeling

statsmodels offers several likelihood families for variables that conventional Gaussian regression does not represent appropriately.

| Response structure                               | Models                                                                                   |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| Binary                                           | `Logit`, `Probit`                                                                        |
| Unordered categories                             | `MNLogit`                                                                                |
| Ordered categories                               | `OrderedModel`                                                                           |
| Group-conditioned outcomes                       | `ConditionalLogit`, `ConditionalMNLogit`, `ConditionalPoisson`                           |
| Counts                                           | `Poisson`, `NegativeBinomial`, `NegativeBinomialP`, `GeneralizedPoisson`                 |
| Excess structural zeros                          | `ZeroInflatedPoisson`, `ZeroInflatedNegativeBinomialP`, `ZeroInflatedGeneralizedPoisson` |
| Separate zero and positive-count processes       | `HurdleCountModel`                                                                       |
| Truncated counts                                 | `TruncatedLFPoisson`, `TruncatedLFNegativeBinomialP`                                     |
| Continuous proportions in the open unit interval | `BetaModel`                                                                              |

Several distinctions are consequential:

Zero-inflated versus hurdle models. Zero-inflated models mix an extra-zero process with a count distribution that may itself generate zeros. Hurdle models separately model crossing the zero boundary and the strictly positive, zero-truncated count process.

Conditional versus ordinary discrete models. Conditional logit/Poisson estimators exploit grouped likelihood structures, enabling estimation that conditions out certain group-specific nuisance effects. These are not simply ordinary pooled regressions with clustered standard errors.

Ordinal versus multinomial models. Ordinal models use the ordering among outcome categories, whereas multinomial logit treats categories as nominal.

Count-model diagnostics. Poisson and count-model results expose distribution-sensitive diagnostics and predictions, including quantities that can reveal systematic discrepancies between observed and predicted count frequencies.

Version 0.15.0 adds regularized estimation to `HurdleCountModel`. Some of the more specialized count-model interfaces remain relatively young, and users should distinguish model availability from the maturity of every associated post-estimation method.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+2



Sources:

- [https://www.statsmodels.org/stable/discretemod.html](https://www.statsmodels.org/stable/discretemod.html?utm_source=chatgpt.com)
- [https://www.statsmodels.org/stable/other_models.html](https://www.statsmodels.org/stable/other_models.html?utm_source=chatgpt.com)
- [https://www.statsmodels.org/stable/examples/notebooks/generated/count_hurdle.html](https://www.statsmodels.org/stable/examples/notebooks/generated/count_hurdle.html?utm_source=chatgpt.com)

### 3.2 GEE: population-averaged effects under within-cluster dependence

`GEE` estimates marginal regression models for correlated observations, typically longitudinal, panel, or clustered data.

The statistical structure combines a GLM-type conditional mean with a working correlation structure.

Built-in working covariance structures include independence, exchangeable, autoregressive, stationary, nested, and unstructured forms, among others.

Additional capabilities include `OrdinalGEE`, `NominalGEE`, and `QIF` (quadratic inference functions).

The key architectural advantage is the separation of the target marginal mean model from a potentially approximate within-cluster covariance model. Sandwich-style robust covariance estimation supports inference under suitable assumptions even when the working correlation structure is not exactly correct.

GEE does not ordinarily estimate subject-specific random-effect distributions. Its coefficients describe population-averaged relationships. Reliable uncertainty estimates still depend on conditions such as independent clusters and adequate effective cluster information.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0



Source: [https://www.statsmodels.org/stable/gee.html](https://www.statsmodels.org/stable/gee.html?utm_source=chatgpt.com)

### 3.3 Mixed-effects models: group-specific variation

`MixedLM` explicitly models latent group-level variation:

\\[ y_i=X_i\beta+Z_i b_i+\varepsilon_i \\]

where \\(\beta\\) contains fixed effects and \\(b_i\\) represents group-specific random effects.

Its major capabilities include random intercepts, correlated random slopes, variance components, maximum likelihood (ML), restricted maximum likelihood (REML), random-effect prediction, and profile-likelihood methods.

A non-obvious extension is partial support for crossed random effects through variance-component specifications. The official documentation explains that crossed structures can be represented by treating the full dataset as one group and defining variance components accordingly. The implementation remains primarily group-based and handles most non-crossed and some crossed structures, rather than offering an unrestricted arbitrary-effects engine.

For non-Gaussian outcomes, `BinomialBayesMixedGLM` and `PoissonBayesMixedGLM` provide Bayesian generalized mixed models via Laplace and variational Bayes approximations. These currently support independent random effects and are not general-purpose Bayesian inference frameworks.

The choice between GEE and mixed effects is therefore substantive: marginal population effects versus conditional, group-specific effects, with different dependence assumptions and inference machinery.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+1



Sources:

- [https://www.statsmodels.org/stable/mixed_linear.html](https://www.statsmodels.org/stable/mixed_linear.html?utm_source=chatgpt.com)
- [https://www.statsmodels.org/stable/mixed_glm.html](https://www.statsmodels.org/stable/mixed_glm.html?utm_source=chatgpt.com)

## 4. Time-series modeling, decomposition, and forecasting

statsmodels provides several modeling pathways for temporal data. They differ in how much of the data-generating process is explicitly represented, which numerical engine estimates the parameters, and what kinds of inference or forecast uncertainty they support.

Documentation correction: The accessible 0.15.0 documentation is published under `https://www.statsmodels.org/stable/`, rather than the `/v0.15.0/` paths listed in the opening references. The corresponding tagged source is available at `https://github.com/statsmodels/statsmodels/tree/v0.15.0`.

### 4.1 Autoregression, distributed lags, and integrated processes

| Model family           | Core mechanism                                 | Important capabilities                                                                         |
| ---------------------- | ---------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `AutoReg`              | Autoregressive regression with selectable lags | Sparse or consecutive lag selection, deterministic terms, seasonal terms, exogenous regressors |
| `ARIMA`                | Integrated ARMA modeling                       | Seasonal terms, trend, exogenous regression, multiple estimation approaches                    |
| `SARIMAX`              | State-space ARIMA-type modeling                | Seasonal structure, exogenous regressors, Kalman-based likelihood, missing observations        |
| `ARDL`                 | Autoregressive distributed-lag regression      | Flexible lag structures across response and explanatory series                                 |
| `UECM`                 | Unrestricted error-correction representation   | Short-run dynamics, long-run relationships, bounds testing                                     |
| `MarkovRegression`     | Hidden discrete regimes                        | Regime-specific means, coefficients, variances, transition probabilities                       |
| `MarkovAutoregression` | Regime-dependent autoregression                | Regime-switching autoregressive processes                                                      |

Several features deserve particular attention.

ARDL and UECM connect short-run regression dynamics with long-run equilibrium relationships. `ardl_select_order()` supports lag selection, while `UECM.from_ardl()` relates the distributed-lag representation to an error-correction specification. `UECMResults.bounds_test()` supports the Pesaran–Shin–Smith bounds-testing approach for a potential levels relationship.

This is valuable when both contemporaneous/lagged responses and long-run adjustment matter. However, the test's interpretation depends on integration-order assumptions; it is not appropriate to treat any regression among trending series as evidence of cointegration.

ARIMA and SARIMAX are related but not interchangeable interfaces. Both can express ARIMA-type structures, but `ARIMA` exposes multiple estimation methods and a regression-with-ARIMA-errors perspective, while `SARIMAX` is explicitly built around the general state-space framework. Differences in treatment of trends, exogenous regressors, and likelihood configuration can matter even for apparently similar specifications.

Markov-switching models introduce latent discrete regimes rather than merely continuous latent states. They estimate transition probabilities and filtered/smoothed regime probabilities, with the possibility of coefficients or variances changing between regimes. This is distinct from a structural-break test that merely asks whether model parameters remained constant.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+3



Sources:

- [https://www.statsmodels.org/stable/tsa.html](https://www.statsmodels.org/stable/tsa.html?utm_source=chatgpt.com)
- [https://www.statsmodels.org/stable/generated/statsmodels.tsa.ardl.ARDL.html](https://www.statsmodels.org/stable/generated/statsmodels.tsa.ardl.ARDL.html?utm_source=chatgpt.com)
- [https://www.statsmodels.org/stable/generated/statsmodels.tsa.ardl.UECM.html](https://www.statsmodels.org/stable/generated/statsmodels.tsa.ardl.UECM.html?utm_source=chatgpt.com)
- [https://www.statsmodels.org/stable/generated/statsmodels.tsa.arima.model.ARIMA.html](https://www.statsmodels.org/stable/generated/statsmodels.tsa.arima.model.ARIMA.html?utm_source=chatgpt.com)

### 4.2 Exponential smoothing: three separate implementations

A consequential API distinction is that statsmodels provides three exponential-smoothing implementations with overlapping names but different model semantics.

| Implementation                           | Statistical mechanism                              | Distinctive properties                                                                              |
| ---------------------------------------- | -------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `tsa.holtwinters.ExponentialSmoothing`   | Classical Holt–Winters recursions                  | Additive and multiplicative trend/seasonal components; relatively direct computation                |
| `tsa.exponential_smoothing.ets.ETSModel` | Innovations state-space error/trend/seasonal model | Explicit error types, including multiplicative errors, likelihood-based ETS inference and forecasts |
| `tsa.statespace.ExponentialSmoothing`    | Linear Gaussian state-space formulation            | Kalman filtering, forecast intervals, state-space diagnostics, parameter constraints                |

The state-space `ExponentialSmoothing` class uses a multiple-sources-of-error formulation, unlike the single-source-of-error innovations formulation associated with ETS. The official guide explicitly notes that the classical Holt–Winters implementation does not supply forecast confidence intervals, while the linear state-space implementation does.

These are therefore different statistical and computational choices, not aliases for one algorithm. Even nominally similar trend and seasonal specifications may imply different likelihoods or forecast distributions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+2



Sources:

- [https://www.statsmodels.org/stable/statespace.html](https://www.statsmodels.org/stable/statespace.html?utm_source=chatgpt.com)
- [https://www.statsmodels.org/stable/generated/statsmodels.tsa.exponential_smoothing.ets.ETSModel.html](https://www.statsmodels.org/stable/generated/statsmodels.tsa.exponential_smoothing.ets.ETSModel.html?utm_source=chatgpt.com)

### 4.3 Decomposition, deterministic features, and signal analysis

The temporal toolbox is substantially broader than autoregressive forecasting.

- Decomposition: `seasonal_decompose`, robust STL decomposition, and `MSTL` for multiple seasonal periods.
- Deterministic components: `DeterministicProcess`, `TimeTrend`, `Seasonality`, `Fourier`, and calendar-aware time trends or Fourier terms.
- Cycle extraction: Hodrick–Prescott, Baxter–King, Christiano–Fitzgerald, and, newly in 0.15.0, Hamilton filtering.
- Forecasting compositions: `STLForecast` combines seasonal decomposition with a forecasting model; `ThetaModel` implements a separate forecasting methodology.
- Stochastic process tools: `ArmaProcess`, lag-polynomial conversion, simulated processes, theoretical autocovariances, spectral properties, and impulse responses.
- Temporal diagnostics: ACF, PACF, cross-correlation, partial cross-correlation, stationarity tests, unit-root tests, cointegration tests, and nonlinear dependence tests.

The `DeterministicProcess` family is especially useful because it provides a shared mechanism for producing correctly structured trend, seasonal, and Fourier regressors instead of manually constructing lagged design matrices and seasonal dummy columns.

These operations have different statistical interpretations. STL is principally a decomposition technique; a state-space structural model estimates stochastic latent components with model-based uncertainty. Likewise, a deterministic seasonal regressor is not equivalent to stochastic seasonal dynamics.

Version 0.15.0 adds partial cross-correlation (`pccf`), the Leybourne–McCabe stationarity test, and the Hamilton filter. External X-13ARIMA-SEATS integration is also supported, but requires the corresponding external executable rather than relying solely on Python packages.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+1



Source: [https://www.statsmodels.org/stable/tsa.html](https://www.statsmodels.org/stable/tsa.html?utm_source=chatgpt.com)

## 5. State-space modeling as a reusable computational engine

The state-space subsystem is one of statsmodels' most architecturally significant capabilities. It separates the statistical definition of a dynamic process from the numerical operations needed to evaluate its likelihood, estimate hidden states, predict observations, and simulate trajectories.

### 5.1 General linear Gaussian state-space representation

The supported representation is

\\[ \begin{aligned} y_t &= Z_t\alpha_t+d_t+\varepsilon_t,\\\ \alpha\_{t+1}&=T_t\alpha_t+c_t+R_t\eta_t, \end{aligned} \\]

with

\\[ \varepsilon_t\sim N(0,H_t),\qquad \eta_t\sim N(0,Q_t). \\]

The matrices can be time-invariant or time-varying. The system explicitly separates:

- Observation generation from hidden-state evolution.
- Deterministic intercepts from stochastic disturbances.
- Observation-error covariance from latent-state disturbance covariance.
- Statistical parameters from filtering and smoothing algorithms.

Consequently, models that appear unrelated at the application level can share the same Kalman filtering, likelihood, prediction, and state-estimation infrastructure.

Missing observations can be handled through the state-space representation without requiring every time series to be completely observed. This is a meaningful advantage over manually constructing regression matrices that discard incomplete periods.

The common framework covers important linear-Gaussian systems; it is not a general nonlinear/non-Gaussian particle-filtering or probabilistic-programming engine.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0



### 5.2 Built-in state-space model families

| Class                              | Main representation                                  | Distinctive uses                                                                         |
| ---------------------------------- | ---------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `SARIMAX`                          | Seasonal ARIMA plus regressors                       | Forecasting with stochastic serial dependence                                            |
| `UnobservedComponents`             | Latent trend, level, seasonal and cycle components   | Structural interpretation and decomposition                                              |
| `VARMAX`                           | Multivariate vector ARMA plus regressors             | Joint dynamic modeling of several response series                                        |
| `DynamicFactor`                    | Latent dynamic factors                               | Common variation across a moderate number of series; supports exogenous variables        |
| `DynamicFactorMQ`                  | Mixed-frequency dynamic factors estimated with EM    | Large multivariate systems, monthly/quarterly observations, configurable factor loadings |
| State-space `ExponentialSmoothing` | Linear Gaussian smoothing system                     | State estimation and forecast intervals within a common infrastructure                   |
| Custom `MLEModel`                  | User-specified system matrices and parameter mapping | New linear Gaussian dynamical models                                                     |

`DynamicFactorMQ` merits particular attention. The official guide describes an expectation–maximization estimator designed to handle hundreds of observed series and to control which variables load on which factors. It also supports mixed monthly/quarterly frequency designs.

Its main contrasting limitation is the lack of exogenous regressor support, whereas `DynamicFactor` supports exogenous regressors but is more suitable for smaller systems. This illustrates why the two classes should not be treated as implementation variants of one fully interchangeable model.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+1



### 5.3 Filtering, smoothing, likelihood, and simulation

The common engine provides distinct computational operations:

| Operation                    | Meaning                                                                         |
| ---------------------------- | ------------------------------------------------------------------------------- |
| `filter()`                   | Estimate states sequentially from data available through each time point        |
| `smooth()`                   | Re-estimate historical states using observations from the full available sample |
| `fit()`                      | Estimate unknown model parameters, typically by likelihood optimization         |
| `loglike()` / `loglikeobs()` | Evaluate likelihood and observation-level likelihood contributions              |
| `get_prediction()`           | Obtain in-sample/dynamic and, where supported, out-of-sample prediction results |
| `get_forecast()`             | Return structured future predictions and uncertainty                            |
| `simulate()`                 | Generate trajectories from a specified model and initial conditions             |
| `impulse_responses()`        | Study the effects of shocks under model-defined assumptions                     |
| `simulation_smoother()`      | Simulate conditional latent-state and disturbance trajectories                  |

The distinction between filtering and smoothing is fundamental. Filtering is causal with respect to the observation timeline: a state estimate at \\(t\\) uses information available by \\(t\\). Smoothing incorporates later observations and is therefore suitable for historical reconstruction, not necessarily for reproducing what was knowable in real time.

Likewise, `forecast()` generally returns point forecasts, while `get_forecast()` exposes an associated prediction-results object with variance and interval functionality. These estimates inherit the statistical assumptions of the fitted model.

The lower-level `Representation`, `Initialization`, `KalmanFilter`, `KalmanSmoother`, `SimulationSmoother`, and `CFASimulationSmoother` classes also permit use of the dynamical engine without requiring an ordinary high-level forecast workflow.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+2



### 5.4 Updating models with additional observations

State-space result objects provide several distinct data-extension operations:

- `append()`: Extend the original sample with later observations, retaining the full dataset in the resulting model.
- `extend()`: Filter new observations using the previous terminal state and existing parameters; the resulting object covers the new segment, avoiding repeated processing of the full historical sample.
- `apply()`: Apply an estimated state-space model to another dataset.
- `news()`: Attribute changes in estimates or forecasts to newly available data and revisions of earlier observations.

For `append()` and `extend()`, optional refitting behavior differs, and the default is to reuse the fitted parameters. A fast update of filtered states is not equivalent to online re-estimation of model parameters.

`news()` is particularly distinctive: it provides a model-based decomposition of forecast revisions into effects attributable to incoming or revised data, a capability otherwise requiring substantial bespoke calculations. Version 0.15.0 also improves its implementation performance.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+2



### 5.5 Custom models and numerical controls

`MLEModel` provides a high-value extension mechanism. A custom subclass can specify the fixed state-space matrices, parameter names, initial estimates, and the `update()` mapping from an optimization parameter vector into the system matrices.

The library then supplies the numerical filtering and much of the estimation, inference, diagnostics, simulation, and forecasting machinery.

Advanced numerical controls include:

- Known, stationary, diffuse, and approximate-diffuse state initialization.
- Parameter transformations to enforce constraints such as stationarity or positive variances.
- Fixed or constrained parameter estimation.
- Filtering and smoothing output selection.
- Matrix-inversion and stability-method configuration.
- Complex-step numerical differentiation in supported operations.
- Memory-conservation modes that avoid retaining selected intermediate arrays.

These controls are not independent conveniences. Initialization affects the likelihood; filtered-output selection affects which subsequent operations remain possible; and aggressive memory conservation can remove arrays needed for smoothing or diagnostics.

The resulting architectural pattern is powerful: specify the mathematical state evolution once, then reuse library-owned state estimation, likelihood evaluation, simulation, and forecast uncertainty rather than building separate mechanisms for each operation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+1



Sources:

- [https://www.statsmodels.org/stable/statespace.html](https://www.statsmodels.org/stable/statespace.html?utm_source=chatgpt.com)
- [https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.mlemodel.MLEModel.html](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.mlemodel.MLEModel.html?utm_source=chatgpt.com)
- [https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.mlemodel.MLEResults.html](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.mlemodel.MLEResults.html?utm_source=chatgpt.com)

## 6. Multivariate temporal systems and shock analysis

### 6.1 VAR, SVAR, and VECM

`VAR` estimates jointly autoregressive dynamics among multiple endogenous variables.

Its associated analytical machinery includes:

- Lag-order selection using information criteria.
- Joint forecasting and forecast intervals.
- Impulse-response functions and Monte Carlo error bands.
- Forecast-error variance decomposition.
- Stability, residual whiteness, and normality analysis.
- Granger noncausality tests and coefficient restrictions.

`SVAR` introduces structural identification restrictions through contemporaneous relationships, supporting structurally interpretable shocks when the identifying assumptions are defensible.

`VECM` models cointegrated multivariate series through adjustment toward long-run equilibrium:

\\[ \Delta y_t=\alpha\beta^\top y\_{t-1} +\sum\_{j=1}^{p-1}\Gamma_j\Delta y\_{t-j} +\text{deterministic terms}+\varepsilon_t. \\]

Here, \\(\beta\\) identifies cointegrating relationships and \\(\alpha\\) governs adjustment to deviations. Johansen cointegration-rank tests and explicit placement of deterministic terms inside or outside the cointegration relationship are supported.

An important 0.15.0 implementation improvement removes an \\(O(T^2)\\) projection-matrix construction from VECM, reducing computational and memory overhead for affected calculations. This is an implementation-specific improvement, not a general runtime guarantee for all multivariate models.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+2



### 6.2 Local projections

Version 0.15.0 adds `LocalProjections`, implementing the Jordà approach for estimating impulse responses with separate regression equations across forecast horizons.

Compared with iterating a fitted VAR's dynamics, local projections can offer greater flexibility in the assumed horizon-specific response relationship. They may also use Newey–West HAC standard errors.

The tradeoff is that local projections and VAR impulse responses estimate related but not necessarily identical objects and can differ in efficiency and behavior under model misspecification. A regression-based impulse response should not be interpreted as a causal treatment effect without appropriate shock identification.

Granger causality is similarly a predictive restriction, not proof of intervention-based causality. Orthogonalized impulse responses from Cholesky identification also depend on variable ordering; structural identification restrictions deserve explicit documentation when they matter.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+2



Sources:

- [https://www.statsmodels.org/stable/vector_ar.html](https://www.statsmodels.org/stable/vector_ar.html?utm_source=chatgpt.com)
- [https://www.statsmodels.org/stable/generated/statsmodels.tsa.vector_ar.local_proj.LocalProjections.html](https://www.statsmodels.org/stable/generated/statsmodels.tsa.vector_ar.local_proj.LocalProjections.html?utm_source=chatgpt.com)

## 7. Statistical inference, model diagnostics, and hypothesis testing

statsmodels' statistical utilities are substantial enough to function independently of its model-fitting APIs. They are distributed primarily across `statsmodels.stats`, `statsmodels.stats.diagnostic`, `statsmodels.stats.sandwich_covariance`, and model-specific results classes.

### 7.1 Inference as a reusable post-estimation layer

Fitted model results commonly provide coefficient covariance matrices, standard errors, confidence intervals, and tests of linear parameter restrictions.

Important interfaces include:

- `cov_params()`, `conf_int()`, `t_test()`, `f_test()`, and `wald_test()`.
- `wald_test_terms()` for formula-term-based restrictions.
- `get_robustcov_results()` for supported alternative covariance estimates.
- Likelihood-ratio tests and nested-model comparisons where the models and estimators satisfy their assumptions.
- `get_prediction()` and prediction result objects, where supported, for uncertainty associated with new observations or fitted means.
- Marginal effects and contrasts for supported nonlinear models.

The distinction between estimation, covariance estimation, and hypothesis testing is important. One fitted coefficient vector can support several inferential assumptions, but not every covariance method is valid for every dependence structure.

Wald, likelihood-ratio, and score tests also have different finite-sample behavior. Their asymptotic equivalence does not establish interchangeability under weak identification, model misspecification, or boundary parameters.

### 7.2 Diagnostics and specification testing

| Diagnostic concern          | Important mechanisms                                                                             |
| --------------------------- | ------------------------------------------------------------------------------------------------ |
| Serial dependence           | Durbin–Watson, Breusch–Godfrey, Ljung–Box, LM tests                                              |
| Heteroskedasticity          | Breusch–Pagan, White, Goldfeld–Quandt, ARCH LM                                                   |
| Distributional assumptions  | Jarque–Bera, omnibus normality, Anderson–Darling, Lilliefors                                     |
| Outliers and influence      | `OLSInfluence`, `GLMInfluence`, `MLEInfluence`, leverage, studentized residuals, Cook's distance |
| Collinearity                | Variance inflation factors, matrix rank and condition diagnostics                                |
| Functional specification    | Ramsey RESET, Rainbow, Harvey–Collier, White specification tests                                 |
| Parameter stability         | CUSUM, Hansen stability test, recursive residuals                                                |
| Non-nested model comparison | Cox, J and encompassing tests                                                                    |
| Forecast accuracy           | Diebold–Mariano, Pesaran–Timmermann                                                              |

The influence-analysis objects are especially useful because they centralize leverage, residual, and observation-level influence calculations instead of requiring separate manual recomputation of leave-one-out regression statistics.

`GLMInfluence` and `MLEInfluence` are labeled experimental in the official statistical API reference.

The forecast-comparison tests newly added in 0.15.0 distinguish equality of predictive accuracy from directional forecasting ability. Their validity depends on the underlying forecast evaluation design, dependence in forecast errors, loss specification, and horizon. They are not substitutes for properly constructed out-of-sample evaluations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+2



Source: [https://www.statsmodels.org/stable/stats.html](https://www.statsmodels.org/stable/stats.html?utm_source=chatgpt.com)

### 7.3 Descriptive inference, multiple testing, and experimental design

The statistical utility modules cover substantially more than regression coefficient p-values.

Sample comparison and equivalence testing

`DescrStatsW`, `CompareMeans`, independent and paired t-tests, z-tests, and two one-sided tests (TOST) provide ordinary and equivalence-testing capabilities. Equivalence tests answer a distinct question from failure to reject a difference: they assess whether effects can be statistically bounded within prespecified equivalence margins.

Proportions, rates, and count outcomes

The `proportion` and `rates` modules supply confidence intervals and comparisons for binomial proportions, Poisson rates, and related count-based quantities, with options for independent samples, rate ratios, differences, and equivalence tests.

Power and sample-size analysis

`statsmodels.stats.power` supports calculations for t, z, F, ANOVA, and chi-square testing. Related modules provide specialized calculations for proportions and count rates.

ANOVA and post-hoc comparisons

`anova_lm`, `AnovaRM`, `anova_oneway`, and multiple-comparison tools support factor tests, repeated-measures analysis, variance-heterogeneous comparisons, and effect-size calculations.

Version 0.15.0 adds Games–Howell post-hoc comparisons, useful when equal group variance assumptions are inappropriate.

Multiplicity control

`multipletests` includes family-wise error and false-discovery-rate adjustments; `fdrcorrection`, two-stage FDR methods, and local FDR machinery enable related inferential regimes.

Two notable advanced features are `RegressionFDR` and knockoff-related regression-effect tools, which provide a different pathway from independently adjusting a collection of ordinary p-values. The 0.15.0 `local_fdr_correction` addition estimates local false discovery rates from the distribution of p-values.

Robust and nonparametric tests

Rank-based comparisons, probability-of-superiority inference, runs tests, sign tests, and the new Jonckheere–Terpstra ordered-trend test provide tests for cases where conventional mean-based tests are unsuitable.

Some of the `statsmodels.stats.oneway`, `rates`, and multivariate testing interfaces carry explicit experimental or API-change warnings.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+4



Sources:

- [https://www.statsmodels.org/stable/stats.html](https://www.statsmodels.org/stable/stats.html?utm_source=chatgpt.com)
- [https://www.statsmodels.org/stable/release/](https://www.statsmodels.org/stable/release/?utm_source=chatgpt.com)

### 7.4 Multivariate covariance and auxiliary statistical operations

Less obvious functionality includes:

- `corr_nearest()` and `cov_nearest()` to construct valid positive-semidefinite approximations to problematic correlation/covariance matrices.
- Factor-structured and regularized covariance methods.
- Distance covariance/correlation statistics and independence tests.
- Robust skewness, kurtosis, and medcouple statistics.
- Moment and cumulant conversions.
- Fixed- and random-effects meta-analysis via `combine_effects()`.
- Inter-rater agreement measures including Cohen's and Fleiss' kappa.

These are useful building blocks for statistical validation, covariance regularization, evidence synthesis, and dependence analysis even in systems that never fit a statsmodels regression.

For example, adjusting an estimated covariance matrix to a valid positive-semidefinite matrix is a different operation from merely suppressing an exception during Cholesky decomposition: it explicitly changes the matrix being modeled, with consequential effects on uncertainty and downstream calculations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+1



Source: [https://www.statsmodels.org/stable/stats.html](https://www.statsmodels.org/stable/stats.html?utm_source=chatgpt.com)

## 8. Specialized modeling and statistical methods

### 8.1 Survival and duration analysis

The `duration` package provides nonparametric survival estimation and proportional hazards regression.

- `SurvfuncRight`: Kaplan–Meier-type survival estimation, quantile inference, pointwise confidence intervals, and simultaneous confidence bands.
- `CumIncidenceRight`: Cumulative incidence estimation for competing-event outcomes.
- `survdiff`: Log-rank and alternative weighted tests including Fleming–Harrington, Gehan–Breslow, and Tarone–Ware variants.
- `PHReg`: Cox proportional hazards regression with partial likelihood, stratification, delayed entry, and Breslow/Efron treatments of tied event times.

This family separates distribution-free estimation of survival functions from covariate-conditioned hazard regression.

The official guide states that the duration module currently handles right censoring only. It should not be treated as a complete framework for arbitrary interval-censored survival outcomes or general event-history models.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+2



Source: [https://www.statsmodels.org/stable/duration.html](https://www.statsmodels.org/stable/duration.html?utm_source=chatgpt.com)

### 8.2 Nonparametric estimation

`statsmodels.nonparametric` contains three important approaches:

| Method                       | Capability                                         | Key tradeoff                                                                          |
| ---------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `lowess`                     | Locally weighted smoothing, with robust iterations | Useful descriptive smooth; not a general multivariate probabilistic model             |
| `KDEUnivariate`              | Kernel density estimation using FFT acceleration   | Efficient for continuous univariate densities; limited bandwidth selection mechanisms |
| `KDEMultivariate`            | Product-kernel density estimation                  | Supports continuous, ordered and unordered variables; computationally more expensive  |
| `KDEMultivariateConditional` | Conditional density estimation                     | Estimates conditional distributions rather than only a conditional mean               |
| `KernelReg`                  | Nonparametric kernel regression                    | Mixed variable types and data-dependent bandwidths                                    |
| `KernelCensoredReg`          | Kernel regression for censored responses           | More specialized assumptions and computational cost                                   |

The distinction between univariate and multivariate density estimation is consequential: the former uses FFT-based algorithms and rule-of-thumb bandwidths; the latter supports least-squares and maximum-likelihood cross-validation for bandwidths and mixed variable types.

This makes the multivariate API more expressive, but generally more expensive. The official guide notes that even one-dimensional use of `KDEMultivariate` can be much slower than `KDEUnivariate`.

Semiparametric partial-linear and single-index approaches are also represented in `sandbox.nonparametric`, but are not presented as equally established public APIs.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0



Source: [https://www.statsmodels.org/stable/nonparametric.html](https://www.statsmodels.org/stable/nonparametric.html?utm_source=chatgpt.com)

### 8.3 Multivariate statistics and latent factors

Separate from multivariate time-series models, `statsmodels.multivariate` provides:

- `PCA` with centering, scaling, missing-data and dimension-reduction options.
- `Factor` for statistical factor analysis.
- Orthogonal and oblique factor rotations, including Procrustes, target rotation, and Promax.
- `CanCorr` for canonical correlation analysis.
- `MANOVA` and multivariate hypothesis tests.
- `MultivariateLS`, introduced in 0.15.0, for jointly modeled continuous response variables.

PCA, factor analysis, and dynamic-factor models represent different objects.

PCA constructs variance-oriented linear components. Factor analysis uses a statistical latent-factor representation. Dynamic-factor time-series models further represent how common factors evolve over time.

This distinction matters when an analysis needs latent-variable uncertainty or temporal dynamics rather than merely a lower-dimensional data representation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+1



Source: [https://www.statsmodels.org/stable/multivariate.html](https://www.statsmodels.org/stable/multivariate.html?utm_source=chatgpt.com)

### 8.4 Distributions and dependence structures

The `distributions` package includes functionality not available from standard regression APIs:

- Empirical cumulative distributions and step-function representations.
- Generalized, zero-inflated, and discretized count distributions.
- Gaussian and Student-t copulas.
- Frank, Clayton, Gumbel, and other Archimedean copulas.
- Extreme-value and independence copulas.
- `CopulaDistribution` for pairing marginal distributions with a copula dependence structure.
- Bernstein-polynomial distributions for nonparametric or semiparametric distribution construction.
- Mixture-distribution construction and random sampling.

The copula interfaces are noteworthy because they permit explicit separation of marginal behavior from multivariate dependence. This can express tail or asymmetric dependence structures that a multivariate Gaussian assumption cannot.

However, availability of distribution construction and evaluation does not imply that every copula family has a comprehensive, high-level joint parameter-estimation workflow. Some count-distribution methods rely on generic inherited implementations that the documentation describes as potentially slow.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+1



Source: [https://www.statsmodels.org/stable/distributions.html](https://www.statsmodels.org/stable/distributions.html?utm_source=chatgpt.com)

### 8.5 Generalized method of moments and instrumental variables

The GMM implementation is located primarily in `statsmodels.sandbox.regression.gmm`, and includes:

- `GMM`: Estimation from arbitrary user-defined moment conditions.
- `IV2SLS`: Two-stage least squares.
- `IVGMM`, `LinearIVGMM`, and `NonlinearIVGMM`.
- Iterative estimation of optimal weighting matrices.
- Subclass-based extension through `momcond()`.

For a moment condition \\(g_i(\theta)\\), the framework estimates parameters by minimizing a weighted sample-moment criterion:

\\[ \hat{\theta} =\arg\min\_{\theta} \bar g(\theta)^\top W\bar g(\theta). \\]

This is a powerful extension mechanism because it can express estimators that do not naturally fit a full likelihood model.

Its maturity boundary is important. The official guide states that the general nonlinear GMM framework works through arbitrary moments, while the linear IV implementation originated as a test case and is not fully optimized around linear structure. The corresponding APIs also reside under `sandbox`, signaling that they deserve more compatibility and numerical scrutiny than the established linear-regression core.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0



Source: [https://www.statsmodels.org/stable/gmm.html](https://www.statsmodels.org/stable/gmm.html?utm_source=chatgpt.com)

## 9. Missing data, treatment effects, and semiparametric inference

### 9.1 Multiple imputation rather than complete-case deletion

`statsmodels.imputation` supplies several different mechanisms for missing observations.

MICE — Multiple Imputation by Chained Equations

`MICEData` models variables with missing values conditionally on other variables, repeatedly updates imputations, and uses predictive mean matching. `MICE` coordinates estimation of a statistical model over multiply imputed datasets and pools the resulting inferential quantities.

The combination makes it possible to reuse much of the ordinary statsmodels estimator infrastructure while accounting for between-imputation and within-imputation variation.

Other interfaces include `MI` and `BayesGaussMI` for Gaussian Bayesian imputation, together with `impute_ros` for regression-on-order-statistics treatment of left-censored nondetect observations.

Version 0.15.0 makes `MICEData` iterable, so successive chain states can be obtained directly as datasets.

These techniques do not eliminate the statistical assumptions behind the missing-data mechanism. Multiple imputation is not automatically valid under arbitrary missing-not-at-random processes, and imputation-model specification can materially affect downstream inference.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+1



Source: [https://www.statsmodels.org/stable/imputation.html](https://www.statsmodels.org/stable/imputation.html?utm_source=chatgpt.com)

### 9.2 Treatment-effect estimation

`TreatmentEffect` estimates average effects under conditional independence assumptions, with methods including:

- Outcome regression adjustment (`ra`).
- Inverse probability weighting (`ipw`).
- Augmented inverse probability weighting (`aipw`).
- Weighted augmentation and inverse-probability-weighted regression adjustment (`aipw_wls`, `ipw_ra`).

Supported estimands include average treatment effects and potential-outcome means, with average effects on treated observations available for certain methods.

A significant implementation detail is that standard errors can be computed using a joint GMM representation incorporating the treatment-assignment model, outcome model, and treatment-effect estimating equations.

The AIPW methods have doubly robust properties under their specified regularity and nuisance-model conditions. This does not mean causal identification survives unmeasured confounding, lack of overlap, or inappropriate treatment timing.

Other relevant tools include `statsmodels.stats.mediation.Mediation` for mediation effects and `OaxacaBlinder` for decomposition of differences between groups. Their inferential interpretations likewise depend on identifying assumptions beyond the act of model estimation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+2



Sources:

- [https://www.statsmodels.org/stable/treatment.html](https://www.statsmodels.org/stable/treatment.html?utm_source=chatgpt.com)
- [https://www.statsmodels.org/stable/generated/statsmodels.treatment.treatment_effects.TreatmentEffect.html](https://www.statsmodels.org/stable/generated/statsmodels.treatment.treatment_effects.TreatmentEffect.html?utm_source=chatgpt.com)

### 9.3 Empirical likelihood

`statsmodels.emplike` provides nonparametric likelihood-based inference without requiring a complete parametric family for the data distribution.

Its principal established capabilities include empirical likelihood tests and confidence intervals for descriptive quantities such as means, variances, correlations, and multivariate means.

The method constructs a constrained likelihood over probability weights assigned to observed samples. Inference follows from empirical likelihood ratios rather than assuming, for example, a normal likelihood for the original observations.

The official guide explicitly states that broader empirical-likelihood regression, instrumental-variable, and accelerated-failure-time inference remains under development, despite related classes appearing in the module reference.

The main tradeoff is computational: empirical likelihood often requires solving constrained numerical problems, so reducing distributional assumptions does not automatically reduce computational complexity.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0



Source: [https://www.statsmodels.org/stable/emplike.html](https://www.statsmodels.org/stable/emplike.html?utm_source=chatgpt.com)

## 10. Data interoperability, extensibility, and reporting

### 10.1 Array-oriented versus formula-oriented modeling

statsmodels exposes two complementary model-construction interfaces.

| Interface                 | Example                                 | Main properties                                                                   |
| ------------------------- | --------------------------------------- | --------------------------------------------------------------------------------- |
| `statsmodels.api`         | `sm.OLS(y, X)`                          | Explicit response and design matrices; direct control of numerical representation |
| `statsmodels.formula.api` | `smf.ols("y ~ x1 + C(group)", data=df)` | Declarative statistical specification; automated design-matrix construction       |

The first interface uses the conventional `endog` (endogenous/response) and `exog` (exogenous/explanatory) arguments. These names describe modeling roles, not a guarantee that the explanatory variables are causally exogenous.

The formula interface provides a higher-level statistical specification layer. It supports categorical encodings, transformations, polynomial terms, interactions, and intercept control:

| Formula feature               | Typical expression | Meaning                                         |
| ----------------------------- | ------------------ | ----------------------------------------------- |
| Main effects                  | `y ~ x1 + x2`      | Two explanatory terms                           |
| Categorical encoding          | `y ~ C(group)`     | Design-matrix columns for group levels          |
| Interaction only              | `y ~ x1:x2`        | Product/interaction term                        |
| Main effects plus interaction | `y ~ x1*x2`        | Expands to both main effects and interaction    |
| Remove intercept              | `y ~ x1 - 1`       | No automatically included constant              |
| Transformation                | `y ~ np.log(x)`    | Apply transformation during matrix construction |

Important semantic difference: formula models ordinarily include an intercept by default; array-oriented `OLS` does not automatically add a constant. `statsmodels.tools.add_constant()` supplies an explicit constant-column helper.

Formula construction also retains information about categorical contrasts and transformations that can be reused when predicting on new observations. This avoids a class of errors caused by reconstructing dummy-variable columns manually, provided the original formula engine and fitted design metadata are preserved.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0



Sources:

[https://www.statsmodels.org/stable/example_formulas.html](https://www.statsmodels.org/stable/example_formulas.html?utm_source=chatgpt.com)

[https://www.statsmodels.org/stable/endog_exog.html](https://www.statsmodels.org/stable/endog_exog.html?utm_source=chatgpt.com)

### 10.2 Patsy and Formulaic integration in 0.15.0

Version 0.15.0 introduces a generalized formula-handling layer in `statsmodels.formula`.

It supports two underlying formula engines:

- Patsy: The default when installed, preserving historical behavior.
- Formulaic: A supported alternative that can be selected explicitly.

Engine selection uses the `SM_FORMULA_ENGINE` environment variable with values `patsy` or `formulaic`.

Formulaic version 1.1.0 or later is a required runtime dependency even when Patsy is the selected default engine.

The principal architectural change is that formula parsing and matrix construction are separated from statistical estimation. The statistical model does not need to own a particular formula parser.

This separation opens opportunities to standardize declarative model specifications while retaining several estimation families. It does not guarantee perfectly identical transformations, categorical conventions, or metadata between formula engines. Formula semantics should be verified for complex expressions or engine-dependent behavior.

One documentation nuance: parts of the formula tutorial still describe Patsy as the only engine; the 0.15.0 release notes are authoritative for the newly introduced engine abstraction.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0



### 10.3 NumPy, pandas, and Polars

statsmodels' core computational interfaces are built around NumPy arrays and SciPy numerical routines, with pandas providing labeled tabular data and indexes.

Version 0.15.0 expands accepted inputs to include Polars `DataFrame` and `Series` objects wherever pandas inputs are supported.

However, Polars support is an input interoperability feature, not a native Polars execution engine.

The release notes explicitly state that Polars input is converted to pandas at the data-entry boundary, after which the existing pandas/NumPy computational pathways are used.

Consequences include:

- Column names and relevant prediction metadata can be preserved.
- Statistical estimators do not automatically acquire Polars' lazy execution, streaming, or query optimization capabilities.
- Data conversions and materialization still matter for memory and performance.
- Polars remains an optional dependency, whereas NumPy, SciPy, pandas, and Formulaic participate in the established runtime stack.

This makes statsmodels useful as an inferential endpoint for data prepared through other data-processing engines, while keeping the model-fitting boundary explicitly in memory.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0



### 10.4 Extending likelihood estimators

`GenericLikelihoodModel` is one of the principal mechanisms for defining statistical models not already supplied by the library.

A subclass can implement a model-specific likelihood or per-observation negative log-likelihood through methods such as `loglike()` and `nloglikeobs()`.

statsmodels can then reuse its general optimization and result-handling machinery. The official demonstration constructs a custom count-model likelihood using this mechanism.

By default, the generic framework can obtain gradients and Hessians numerically where explicit implementations are unavailable. This is numerical differentiation, not a general automatic-differentiation system comparable to JAX or PyTorch.

The approach is valuable when a model has a tractable likelihood but requires nonstandard distributions or parameterizations. Its limitations are equally important: numerical differentiation can be expensive or unstable, parameter constraints require appropriate handling, and generic post-estimation procedures are only as valid as the model's statistical assumptions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0



Source:

[https://www.statsmodels.org/stable/examples/notebooks/generated/generic_mle.html](https://www.statsmodels.org/stable/examples/notebooks/generated/generic_mle.html?utm_source=chatgpt.com)

### 10.5 Other extension mechanisms

The library supports extension at several different statistical layers.

| Extension boundary              | Mechanism                                | Reusable infrastructure                              |
| ------------------------------- | ---------------------------------------- | ---------------------------------------------------- |
| Custom likelihood               | `GenericLikelihoodModel`                 | Optimization, parameter covariance, model results    |
| Custom dynamical model          | `MLEModel`                               | Kalman filtering, smoothing, likelihood, forecasting |
| Custom estimating moments       | `GMM.momcond()`                          | Moment weighting, estimation, GMM tests              |
| Custom response distribution    | GLM `Family`, `Link`, variance functions | Generalized regression machinery                     |
| Custom correlation assumptions  | GEE covariance structures                | Correlated-data estimating equations                 |
| Custom random-effect structures | `MixedLM` variance components            | Group-based hierarchical estimation                  |
| Robust estimation               | M-estimator norms and scale functions    | Robust iterative estimation                          |
| Semiparametric smoothing        | Kernel, bandwidth, spline specifications | Nonparametric or GAM estimators                      |

These extension mechanisms differ in maturity and generality. In particular, GMM APIs located under `sandbox` should not be treated as equally stable substitutes for the principal public model classes.

The higher-level architectural opportunity is the reuse of complete estimation systems: a new statistical specification can inherit optimization, result structures, inference, and diagnostics without independently implementing all of them.

### 10.6 Optimization and execution behavior

statsmodels uses several computational approaches rather than one universal optimizer:

- Closed-form or numerical linear algebra for linear regression.
- Iteratively reweighted least squares for GLMs.
- SciPy optimization routines for many nonlinear likelihood problems.
- Expectation–maximization algorithms for selected latent-variable models.
- Kalman filtering and smoothing for state-space models.
- Iterative algorithms for robust regression, mixed models, and penalized estimation.

The generic optimization interfaces expose algorithms such as Newton, BFGS, L-BFGS, nonlinear conjugate gradient, Nelder–Mead, and Powell methods, with availability depending on the model.

This matters because optimization controls are not uniformly transferable across all estimators. A solver or gradient configuration applicable to generic likelihood estimation may not apply to iterative least squares, EM, or state-space filtering.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0



Source:

[https://www.statsmodels.org/stable/optimization.html](https://www.statsmodels.org/stable/optimization.html?utm_source=chatgpt.com)

### 10.7 Large-data strategies and distributed estimation

The official large-data guide states that most of statsmodels and its surrounding numerical stack operate in memory.

Two general approaches are described:

Reducing materialization: Preparing or selecting only the necessary variables and observations before model construction, including column selection from external storage.

Dividing estimation work: `DistributedModel` supplies a divide-and-conquer interface in which observations are partitioned, parameter estimates are calculated on partitions, and the estimates are aggregated through a joining procedure.

`DistributedModel` exposes configuration for the partition-level estimation and joining algorithms. The documented implementation includes sequential and joblib-backed fitting mechanisms.

This is not equivalent to a general-purpose distributed statistics engine that automatically makes every statsmodels estimator scalable. The guide identifies limitations around formula handling, and the mathematical validity of combining partition estimates depends on the estimator and aggregation method.

For example, averaging independently fitted nonlinear-model parameters is not generically equivalent to maximizing the likelihood over the combined dataset.

Where estimation involves dense covariance matrices, large design matrices, or state-space intermediates, memory and numerical complexity can remain substantial regardless of the original data's storage format.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+1



Sources:

[https://www.statsmodels.org/stable/large_data.html](https://www.statsmodels.org/stable/large_data.html?utm_source=chatgpt.com)

[https://www.statsmodels.org/stable/generated/statsmodels.base.distributed_estimation.DistributedModel.html](https://www.statsmodels.org/stable/generated/statsmodels.base.distributed_estimation.DistributedModel.html?utm_source=chatgpt.com)

### 10.8 Results, statistical reporting, and visualization

statsmodels' results objects provide a reusable interface between numerical estimation and analytical reporting.

The reporting layer includes `summary()`, `summary2()`, `Summary`, and `SimpleTable`, with tabular output formats including text, HTML, CSV, and LaTeX.

The plotting infrastructure includes regression diagnostic plots, influence plots, partial-regression plots, Q–Q and probability plots, seasonal graphics, autocorrelation plots, and model-specific visualizations.

An important advantage is that diagnostics can be derived from the original statistical model and its estimated covariance or residual structure, rather than treating predictions as an unstructured numerical output.

Nevertheless, result formats are not fully uniform across model classes. A generic downstream consumer should distinguish common parameter/result concepts from model-specific diagnostics and forecast objects.

Serialization is supported through pickle-based helpers and model-specific result save/load methods. Pickled objects require compatibility and trust considerations; they should not be treated as a language-independent, security-hardened statistical interchange format.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0



Sources:

[https://www.statsmodels.org/stable/iolib.html](https://www.statsmodels.org/stable/iolib.html?utm_source=chatgpt.com)

[https://www.statsmodels.org/stable/graphics.html](https://www.statsmodels.org/stable/graphics.html?utm_source=chatgpt.com)

## 11. Numerical reliability, statistical validity, and maturity boundaries

### 11.1 Nonconvergence, identification, and singularity

The official pitfalls guide makes several important qualifications.

Rank-deficient design matrices: Linear regression and related models can use generalized inverses, so perfect multicollinearity does not necessarily raise an exception. A returned parameter vector may therefore be non-unique or numerically unstable.

Likelihood convergence: A successful optimization termination condition does not prove that parameters are well identified or that a unique finite maximum has been found. Optimizers may satisfy objective-based tolerances while parameters remain unstable.

Separation: Binary Logit/Probit models may detect perfect prediction, but the documentation notes that quasi-perfect prediction is not comprehensively checked.

Stateful model/result relationships: Some fitted results retain references to attributes of their originating model object. Reusing and refitting that model with changed settings can invalidate assumptions made by an earlier results object.

These are particularly consequential for automated statistical workflows: numerical completion, statistical identification, and model adequacy are separate conditions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0



Source:

[https://www.statsmodels.org/stable/pitfalls.html](https://www.statsmodels.org/stable/pitfalls.html?utm_source=chatgpt.com)

### 11.2 Semantics that must remain distinct

| Distinction                                           | Why it matters                                                                                                |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Statistical association versus causality              | Model coefficients, Granger tests, and predictive accuracy do not independently identify causal interventions |
| Coefficient uncertainty versus prediction uncertainty | Uncertainty about expected responses differs from uncertainty in future observations                          |
| Robust coefficients versus robust standard errors     | Resistant estimation and dependence-adjusted inference address different problems                             |
| Marginal versus conditional effects                   | GEE and mixed-effects models answer different statistical questions                                           |
| Filtering versus smoothing                            | Historical smoothing can use future observations unavailable at forecast time                                 |
| Complete-case versus imputed inference                | Missing-data handling changes statistical assumptions and uncertainty calculations                            |
| Identified versus numerically fitted parameters       | Optimizer success does not establish uniqueness or practical identifiability                                  |
| Regularization versus valid post-selection inference  | Penalization or automatic variable selection does not automatically yield conventional confidence intervals   |
| Structural versus reduced-form innovations            | Multivariate impulse responses require appropriate identification to carry structural meaning                 |

The library supplies extensive diagnostics, but diagnostics cannot universally validate model assumptions. Formal test selection, dependence structures, multiple comparisons, and sample sizes remain statistical design questions.

### 11.3 Stable, experimental, and sandbox functionality

The 0.15.0 release is stable, but API maturity varies within it.

| Maturity                    | Examples                                                                                     | Interpretation                                                                  |
| --------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Established core            | OLS, GLM, principal discrete models, VAR, SARIMAX, many statistical tests                    | Broadly documented public interfaces                                            |
| Advanced, model-specific    | GEE, MixedLM, DynamicFactorMQ, MLEModel, treatment effects                                   | Public functionality with significant statistical and computational assumptions |
| Experimental or preliminary | Newly introduced robust covariance estimators; some influence, GAM and statistics interfaces | Usable functionality, but specific APIs may evolve                              |
| Sandbox                     | Some GMM/IV, semiparametric and experimental model utilities                                 | Quality, test coverage, and interface stability vary substantially              |
| Development branch          | Features present only under `/dev/`                                                          | Not attributable to the 0.15.0 stable release unless specifically verified      |

The official sandbox documentation explicitly warns that its modules are not yet integrated to the standards of the main package and that testing and quality vary widely. The release notes similarly caution that newly added public functionality is not guaranteed to have fully stabilized APIs.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+1



Source:

[https://www.statsmodels.org/stable/sandbox.html](https://www.statsmodels.org/stable/sandbox.html?utm_source=chatgpt.com)

### 11.4 The consequential changes in version 0.15.0

Beyond new estimators and tests discussed earlier, several cross-cutting changes affect interoperability and compatibility.

| Change                         | Released behavior in 0.15.0                                                                                        |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| Random-number configuration    | Standardized `rng=`; older `seed=` and `random_state=` names issue deprecation warnings                            |
| Statistical return types       | Many functions now expose named result fields through `NamedTuple` classes                                         |
| Variable-length legacy tuples  | Selected functions retain previous default returns with warnings; `result_object=True` opts into structured output |
| Formula infrastructure         | Patsy/Formulaic engine selection via `SM_FORMULA_ENGINE`                                                           |
| Polars interoperability        | Polars inputs accepted and converted at the data boundary                                                          |
| Build backend                  | `meson-python` replaces setuptools-based builds                                                                    |
| New robust procedures          | High-breakdown covariance and resistant regression methods                                                         |
| Additional statistical methods | Local projections, forecast comparisons, stationarity and trend tests, broader GLM marginal effects                |
| Numerical and validation fixes | Numerous model-specific corrections, improved warnings, and stricter option validation                             |

The release notes specify that the default behavior of selected transitioning `NamedTuple` APIs is intended to change in version 0.16. That is a future transition, not the default behavior of 0.15.0.

The package requires Python 3.10 or newer. Its released runtime dependency minimums include NumPy 1.23.5, SciPy 1.8, pandas 1.4, Patsy 0.5.6 where installed, and Formulaic 1.1.0.

Source builds have different, stricter requirements: NumPy 2.0+, SciPy 1.13+, Cython 3.0.13+, and the Meson/Ninja toolchain. These build requirements should not be mistaken for the minimum versions required to run a prebuilt wheel.

The release also includes experimental Pyodide/WebAssembly and free-threaded Python work; these should not be interpreted as universal platform or concurrency guarantees.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.statsmodels.org\&sz=32)

statsmodels 0.15.0+2



Sources:

[https://www.statsmodels.org/stable/release/](https://www.statsmodels.org/stable/release/?utm_source=chatgpt.com)

[https://pypi.org/project/statsmodels/](https://pypi.org/project/statsmodels/?utm_source=chatgpt.com)

## 12. Architectural synthesis and capability selection

statsmodels is most effectively understood as several complementary engines sharing a broad inference-oriented design:

| Problem structure                                          | Most relevant engine or family                                    |
| ---------------------------------------------------------- | ----------------------------------------------------------------- |
| Interpretable linear or generalized response relationships | Regression, GLM, GAM                                              |
| Correlated repeated observations                           | GEE, MixedLM                                                      |
| Discrete outcomes and complex count generation             | Discrete and count models                                         |
| Dynamic forecasting with latent continuous states          | State-space and Kalman machinery                                  |
| Temporal feedback among multiple variables                 | VAR, VECM, SVAR, local projections                                |
| Hidden discrete economic or physical regimes               | Markov-switching models                                           |
| Statistical validity and model scrutiny                    | Tests, robust covariance, diagnostics, influence                  |
| Nonstandard likelihood or estimating equations             | `GenericLikelihoodModel`, GMM                                     |
| Missing-data-aware estimation                              | MICE and imputation utilities                                     |
| Treatment effect inference                                 | Treatment-effect and mediation estimators                         |
| Nonparametric distributions and nonlinear relationships    | KDE, kernel regression, copulas, empirical likelihood             |
| Reusable statistical reporting                             | Fitted results, predictions, confidence intervals, summary tables |

### Three architectural capabilities distinguish the library

1\. Models are coupled to inference rather than merely prediction.

Fitting can produce a connected analytical object containing parameter estimates, uncertainty, statistical restrictions, residual structure, influence measures, and predictions. This is more expressive than treating a model as a function that returns predicted values.

2\. Complex numerical infrastructure is reusable across model definitions.

The state-space implementation is the clearest example: filtering, smoothing, likelihood, simulation, and forecasting serve multiple built-in models and can support custom ones. GLM, GMM, and likelihood extensions offer analogous reuse at other statistical levels.

3\. Statistical assumptions are explicit enough to support meaningful model comparison and diagnostics.

Different error structures, dependence models, latent-variable mechanisms, distribution families, and covariance estimators can often be represented without writing the underlying numerical algorithms from scratch.

The qualification is that these facilities are not a universal interchangeable model interface. Model results, numerical methods, uncertainty guarantees, and supported extensions vary by family.

For a system primarily concerned with statistical estimation and inference, this diversity is a major capability. For one primarily concerned with massive-scale execution, GPU-accelerated tensor computation, unrestricted probabilistic programming, or arbitrary distributed estimation, statsmodels is better understood as a specialized inferential component rather than a complete execution framework.

### Primary documentation map

The following direct sources provide the most useful entry points for further investigation:

| Topic                                           | Official source                                                                                                                                                                             |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Entire stable library                           | [https://www.statsmodels.org/stable/](https://www.statsmodels.org/stable/?utm_source=chatgpt.com)                                                                                           |
| Full API hierarchy                              | [https://www.statsmodels.org/stable/api.html](https://www.statsmodels.org/stable/api.html?utm_source=chatgpt.com)                                                                           |
| User guide and model families                   | [https://www.statsmodels.org/stable/user-guide.html](https://www.statsmodels.org/stable/user-guide.html?utm_source=chatgpt.com)                                                             |
| Version 0.15.0 capabilities and migration notes | [https://www.statsmodels.org/stable/release/](https://www.statsmodels.org/stable/release/?utm_source=chatgpt.com)                                                                           |
| Statistical modeling examples                   | [https://www.statsmodels.org/stable/examples/index.html](https://www.statsmodels.org/stable/examples/index.html?utm_source=chatgpt.com)                                                     |
| State-space models and numerical internals      | [https://www.statsmodels.org/stable/statespace.html](https://www.statsmodels.org/stable/statespace.html?utm_source=chatgpt.com)                                                             |
| Time-series model families                      | [https://www.statsmodels.org/stable/tsa.html](https://www.statsmodels.org/stable/tsa.html?utm_source=chatgpt.com)                                                                           |
| Statistics and inference functions              | [https://www.statsmodels.org/stable/stats.html](https://www.statsmodels.org/stable/stats.html?utm_source=chatgpt.com)                                                                       |
| Custom maximum-likelihood models                | [https://www.statsmodels.org/stable/examples/notebooks/generated/generic_mle.html](https://www.statsmodels.org/stable/examples/notebooks/generated/generic_mle.html?utm_source=chatgpt.com) |
| Optimization infrastructure                     | [https://www.statsmodels.org/stable/optimization.html](https://www.statsmodels.org/stable/optimization.html?utm_source=chatgpt.com)                                                         |
| Large-data methods                              | [https://www.statsmodels.org/stable/large_data.html](https://www.statsmodels.org/stable/large_data.html?utm_source=chatgpt.com)                                                             |
| Numerical and modeling pitfalls                 | [https://www.statsmodels.org/stable/pitfalls.html](https://www.statsmodels.org/stable/pitfalls.html?utm_source=chatgpt.com)                                                                 |
| Experimental/sandbox modules                    | [https://www.statsmodels.org/stable/sandbox.html](https://www.statsmodels.org/stable/sandbox.html?utm_source=chatgpt.com)                                                                   |
| Tagged 0.15.0 source                            | [https://github.com/statsmodels/statsmodels/tree/v0.15.0](https://github.com/statsmodels/statsmodels/tree/v0.15.0?utm_source=chatgpt.com)                                                   |

Overall: statsmodels offers an unusually broad set of statistically rigorous modeling capabilities, with its greatest architectural value coming from the combination of model specification, reusable estimation engines, covariance and hypothesis-testing infrastructure, structured results, and diagnostics. Its advanced state-space, hierarchical, robust, discrete, semiparametric, and post-estimation facilities are especially worth understanding before introducing bespoke statistical machinery.