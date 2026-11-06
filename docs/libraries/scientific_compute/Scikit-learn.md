# Scikit-learn 1.9.1 — Comprehensive Python Library Capability Overview

Research date: October 27, 2026 | Target: scikit-learn 1.9.1 (stable, released September 10, 2026) | Python 3.11+ | BSD-3-Clause

## 1. Executive orientation

Scikit-learn is a general-purpose machine-learning framework built around a unified estimator protocol that connects numerical algorithms, feature transformations, model composition, statistical validation, hyperparameter optimization, and model inspection.

Its architectural significance extends beyond its collection of machine-learning algorithms. Scikit-learn provides a reusable execution and composition model through which preprocessing, learning, evaluation, and model selection can be treated as interoperable components.

The library's defining capabilities fall into three broad categories:

1. Statistical and numerical modeling: Classification, regression, clustering, representation learning, dimensionality reduction, density estimation, anomaly detection, and probabilistic modeling.
2. Declarative machine-learning composition: Estimators, transformers, pipelines, feature unions, column transformations, meta-estimators, metadata routing, and parameter introspection.
3. Evaluation and execution infrastructure: Cross-validation, search strategies, metrics, calibration, decision-threshold optimization, inspection, parallel execution, incremental learning, and hardware-aware array operations.

The result is a framework in which many capabilities that otherwise require custom orchestration—data preparation, leakage-safe validation, parameter search, nested model composition, and fitted-model inspection—are already integrated.

Scikit-learn 1.9.1 is the current stable release. Version 1.10 remains in development. The 1.9 series adds an experimental callback API, broader Array API interoperability, configurable SciPy sparse-array output, richer estimator introspection, and further metadata-routing support.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+2



Primary references:

- Official user guide: [https://scikit-learn.org/1.9/user_guide.html](https://scikit-learn.org/1.9/user_guide.html?utm_source=chatgpt.com)
- Complete API reference: [https://scikit-learn.org/1.9/api/index.html](https://scikit-learn.org/1.9/api/index.html?utm_source=chatgpt.com)
- Version 1.9 release history: [https://scikit-learn.org/1.9/whats_new/v1.9.html](https://scikit-learn.org/1.9/whats_new/v1.9.html?utm_source=chatgpt.com)
- Version 1.9 release highlights: [https://scikit-learn.org/1.9/auto_examples/release_highlights/plot_release_highlights_1_9_0.html](https://scikit-learn.org/1.9/auto_examples/release_highlights/plot_release_highlights_1_9_0.html?utm_source=chatgpt.com)

### 1.1 Capability map

| Capability family          | Principal mechanisms                                                       | Architectural significance                                                       |
| -------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Estimator architecture     | `BaseEstimator`, estimator tags, `clone`, `get_params`, `set_params`       | Shared interface across heterogeneous algorithms and third-party implementations |
| Model composition          | `Pipeline`, `ColumnTransformer`, `FeatureUnion`, meta-estimators           | Integrated feature processing, modeling, and parameter optimization              |
| Supervised learning        | Linear models, SVMs, trees, ensembles, Gaussian processes, neural networks | Multiple statistical and computational approaches through compatible interfaces  |
| Unsupervised learning      | Clustering, decomposition, manifolds, mixtures, covariance estimation      | Representation discovery, structural analysis, and anomaly detection             |
| Feature engineering        | Encoders, scalers, imputers, basis expansions, feature selection           | Reusable, trainable feature transformations                                      |
| Model selection            | CV splitters, grid/random search, successive halving                       | Systematic comparison and hyperparameter optimization                            |
| Evaluation                 | Scorers, metrics, calibration, threshold tuning, inspection                | Separation of training objectives from evaluation and decision objectives        |
| Metadata orchestration     | Metadata routing and method-specific requests                              | Structured propagation of sample weights, groups, and custom metadata            |
| Incremental execution      | `partial_fit`, `warm_start`, mini-batch estimators                         | Selective online and repeated-fit workflows                                      |
| Numerical interoperability | NumPy, SciPy sparse, pandas, Polars, experimental Array API                | Integration with numerical and dataframe ecosystems                              |
| Extensibility              | Custom estimators, tags, validation, estimator checks, callback hooks      | Reuse of native composition and validation infrastructure                        |
| Execution management       | joblib, OpenMP, BLAS, threadpoolctl, caching                               | Parallelism and computational resource control                                   |

## 2. Core architecture: the estimator protocol

The estimator abstraction is scikit-learn's most important unifying mechanism. It defines how algorithms are configured, fitted, invoked, inspected, cloned, composed, and validated.

### 2.1 Estimator categories and lifecycle

Scikit-learn distinguishes several compatible object types:

| Object type           | Core methods                                                        | Functional role                                                          |
| --------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Estimator             | `fit(X, y=None)`                                                    | Learns state from supplied observations                                  |
| Predictor             | `predict(X)`                                                        | Produces labels or numerical predictions                                 |
| Classifier            | `predict`, optionally `predict_proba`, `decision_function`          | Classification and confidence or decision-score estimation               |
| Transformer           | `fit`, `transform`, optionally `fit_transform`, `inverse_transform` | Learns and applies a data transformation                                 |
| Incremental estimator | `partial_fit`                                                       | Updates fitted state through successive batches                          |
| Meta-estimator        | Wraps one or more estimators                                        | Adds composition, validation, ensembles, calibration, or other behaviors |
| Scorer                | Callable scoring protocol                                           | Quantifies model performance within selection and evaluation             |

These are overlapping behavioral roles rather than a rigid, disjoint class hierarchy.

A model's constructor represents its configuration; fitting produces learned state. By convention:

- Constructor parameters are inspectable through `get_params()` and changeable through `set_params()`.
- Fitted attributes end in `_`, such as `coef_`, `classes_`, `n_features_in_`, or `feature_importances_`.
- `clone()` creates a new unfitted estimator with the corresponding configuration, rather than duplicating its learned state.
- `fit()` ordinarily resets learned state, whereas `partial_fit()` and certain `warm_start` configurations explicitly permit continuation or reuse.
- `score()` is a model-specific convenience method, not a universally comparable performance measure.

This separation permits the same estimator to participate in cross-validation, hyperparameter search, pipelines, and higher-order models without each integration needing custom fitting logic.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+1



### 2.2 Parameter hierarchy and introspection

Nested estimators expose parameter trees using the `component__parameter` naming convention.

For example, a pipeline can contain a column transformer with separate numerical and categorical preprocessing branches, followed by a classifier. Model-selection tools can modify parameters inside any supported nested estimator.

This enables:

- Joint optimization of preprocessing and prediction parameters.
- Replacement of entire modeling components during search.
- Programmatic inspection of nested estimator configuration.
- Reproduction and comparison of model configurations.
- Construction of reusable estimator factories without bespoke parameter-propagation logic.

The parameter hierarchy is an object-composition mechanism, not a declarative computation graph with general-purpose execution optimization.

### 2.3 Estimator tags and capability discovery

Scikit-learn's structured estimator tags, exposed through `__sklearn_tags__()` and `sklearn.utils.get_tags()`, describe properties relevant to estimator interoperability.

Examples include whether an estimator:

- Is a classifier, regressor, transformer, or another estimator type.
- Requires a target.
- Supports particular input representations or sparsity.
- Accommodates missing values.
- Supports multiple outputs.
- Is intrinsically nondeterministic.

Tags are used by framework utilities, including estimator checks, to determine appropriate behavior. They can depend on an estimator's configuration and are not simply static class declarations.

Architectural value: Estimator tags provide a machine-readable capability layer for automated compatibility checks, conditional testing, model registries, and estimator-aware tooling.

They are not, however, a complete declarative schema of every supported solver, parameter combination, hardware backend, or performance characteristic.

### 2.4 Custom estimators and third-party integration

`BaseEstimator`, `ClassifierMixin`, `RegressorMixin`, `TransformerMixin`, and related interfaces allow external implementations to behave like native scikit-learn components.

The integration contract includes constructor conventions, fitted attributes, parameter introspection, validation, estimator tags, and supported method signatures. Compatible custom estimators can participate in pipelines and model selection without implementing these higher-order systems themselves.

The developer interface also includes:

- `validate_data()` for consistent shape and feature validation.
- `check_is_fitted()` and `__sklearn_is_fitted__()` for fitted-state verification.
- `check_estimator()` and `parametrize_with_checks()` for compatibility testing.
- `get_feature_names_out()` and `OneToOneFeatureMixin` for transformation schema propagation.
- Metadata-routing interfaces for nested auxiliary-data handling.
- Callback integration hooks introduced in 1.9.

This is one of scikit-learn's strongest opportunities for reducing bespoke machine-learning infrastructure: an external algorithm can adopt a relatively small protocol and inherit a substantial ecosystem of composition, tuning, validation, and inspection facilities.

Official developer reference:

[https://scikit-learn.org/1.9/developers/develop.html](https://scikit-learn.org/1.9/developers/develop.html?utm_source=chatgpt.com)

## 3. Model composition and feature-engineering infrastructure

Scikit-learn's compositional facilities turn a collection of estimators into a trainable, inspectable, and tunable higher-order estimator.

### 3.1 Pipeline, ColumnTransformer, and FeatureUnion

These three components establish different composition semantics.

| Component                    | Composition semantics                                     | Important capabilities                                                                                |
| ---------------------------- | --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `Pipeline`                   | Sequential execution                                      | Fitted transformation chain, final estimator, end-to-end cross-validation, parameter search, caching  |
| `ColumnTransformer`          | Parallel transformation of selected feature subsets       | Heterogeneous schemas, column selection by name/dtype, sparse/dense concatenation, feature provenance |
| `FeatureUnion`               | Parallel transformation of the same input                 | Multiple representation families, weighted concatenation, joint optimization                          |
| `TransformedTargetRegressor` | Transformation of the regression target                   | Fit on transformed targets, inverse-transform predictions                                             |
| `FunctionTransformer`        | Custom function as an estimator-compatible transformation | Incorporation of stateless or externally implemented numerical operations                             |

A `Pipeline` is especially consequential because preprocessing and modeling become one estimator. When cross-validation clones and fits that composite object, learned preprocessing statistics are computed within each training fold instead of on the entire dataset.

This directly addresses a common source of information leakage without requiring custom fold-by-fold orchestration.

Additional composition mechanisms include:

- `memory`: joblib-backed caching of fitted intermediate transformers.
- `named_steps`, `named_transformers_`: retrieval of fitted components.
- `passthrough` and `drop`: conditional removal of components.
- Nested parameter addressing: changing individual steps or entire estimator choices.
- `get_feature_names_out()`: tracking transformed feature names where supported.
- `verbose_feature_names_out`: controlled naming in column transformations.
- `transform_input`: transformation of selected metadata arguments along a pipeline, with metadata routing enabled.

Caching is particularly valuable when expensive deterministic preprocessing is reused across parameter searches. It does not imply that the entire pipeline, final estimator, or every intermediate result is cached. Enabling pipeline caching also changes estimator-object identity because transformers are cloned before fitting.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+1



Documentation:

[https://scikit-learn.org/stable/modules/compose.html](https://scikit-learn.org/stable/modules/compose.html?utm_source=chatgpt.com)

### 3.2 Heterogeneous feature processing

`ColumnTransformer` can operate on dataframe columns selected by name, position, slice, boolean mask, or callable. `make_column_selector` can select columns by data type or naming pattern.

The resulting feature space can combine:

- Numerical scaling and missing-value imputation.
- Categorical encoding.
- Text vectorization.
- Feature selection and dimensionality reduction.
- Custom domain transformations.
- Unmodified columns through `remainder="passthrough"`.

A consequential design distinction is that `ColumnTransformer` produces a common feature matrix by concatenating transformed outputs. It is not a general relational data-processing engine: its transformations are column-oriented and preserve the sample correspondence expected by estimators.

For operations involving joins, grouping, relational integrity, or arbitrary row changes, those responsibilities remain outside its native abstraction.

### 3.3 Preprocessing primitives

Scikit-learn includes a substantial library of fitted and stateless feature transformations.

| Family                      | Representative capabilities                                           | Key distinctions                                                                    |
| --------------------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Scaling                     | `StandardScaler`, `MinMaxScaler`, `RobustScaler`, `MaxAbsScaler`      | Feature standardization, bounded scaling, outlier sensitivity, sparse compatibility |
| Distribution transformation | `PowerTransformer`, `QuantileTransformer`, `Normalizer`               | Marginal distribution changes versus sample-wise normalization                      |
| Categorical encoding        | `OneHotEncoder`, `OrdinalEncoder`, `TargetEncoder`                    | Sparse expansion, ordered encodings, supervised statistics                          |
| Nonlinear basis expansion   | `PolynomialFeatures`, `SplineTransformer`, `KBinsDiscretizer`         | Interactions, nonlinear functional bases, discretization                            |
| Missing values              | `SimpleImputer`, `KNNImputer`, `IterativeImputer`, `MissingIndicator` | Univariate, neighbor-based, model-based, and missingness-aware representations      |
| Label transformation        | `LabelEncoder`, `LabelBinarizer`, `MultiLabelBinarizer`               | Target coding rather than general feature preprocessing                             |
| Feature normalization       | `normalize`, `Normalizer`, `Binarizer`                                | Geometric normalization and thresholding                                            |

Two particularly important capabilities deserve separate attention.

Infrequent-category handling. `OneHotEncoder` supports `min_frequency`, `max_categories`, and `handle_unknown="infrequent_if_exist"`. These permit rare-category grouping and controlled behavior for previously unseen categorical values, reducing custom category-management logic.

Cross-fitted target encoding. `TargetEncoder` learns category-to-target statistics, but its `fit_transform()` uses internal cross-fitting to reduce target leakage. Consequently, `fit_transform(X, y)` is intentionally not always equivalent to `fit(X, y).transform(X)`. In 1.9, metadata routing can also pass group information to its internal CV splitter. This distinction is essential when composing target encoders with downstream predictors.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+2



Experimental imputation. `IterativeImputer` models each incomplete feature as a function of other features. It can use custom regressors and optionally sample from posterior predictive distributions. Its experimental status and potentially significant computational costs distinguish it from ordinary production-stable imputation interfaces.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



References:

[https://scikit-learn.org/stable/modules/preprocessing.html](https://scikit-learn.org/stable/modules/preprocessing.html?utm_source=chatgpt.com)

[https://scikit-learn.org/stable/modules/impute.html](https://scikit-learn.org/stable/modules/impute.html?utm_source=chatgpt.com)

[https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html?utm_source=chatgpt.com)

### 3.4 Feature extraction and transformation without fitted vocabularies

The feature-extraction system includes:

- `CountVectorizer` and `TfidfVectorizer` for word or character n-gram representations.
- `HashingVectorizer` for fixed-dimensional, stateless text vectorization.
- `DictVectorizer` for feature dictionaries.
- `FeatureHasher` for hashing arbitrary feature-value mappings.
- Image-patch extraction and image-to-graph utilities.
- Sparse representations suitable for high-dimensional text and categorical models.

Hash-based representations are important because they avoid maintaining an expanding feature vocabulary. This reduces vocabulary storage and enables independent batch transformation, but introduces hash collisions and removes direct reversibility of feature identities.

The library also contains `Nystroem`, `RBFSampler`, `AdditiveChi2Sampler`, and `SkewedChi2Sampler` for approximating kernel feature maps. These can replace an expensive kernel matrix with explicit transformed features, allowing linear estimators to approximate certain nonlinear kernel methods.

This is a meaningful architectural alternative to implementing custom kernel expansion or materializing dense pairwise similarity matrices.

References:

[https://scikit-learn.org/stable/modules/feature_extraction.html](https://scikit-learn.org/stable/modules/feature_extraction.html?utm_source=chatgpt.com)

[https://scikit-learn.org/stable/modules/kernel_approximation.html](https://scikit-learn.org/stable/modules/kernel_approximation.html?utm_source=chatgpt.com)

## 4. Metadata routing: structured auxiliary-data propagation

Metadata routing is one of scikit-learn's most important advanced composition capabilities.

Historically, passing sample weights, groups, or other auxiliary information through nested estimators required special handling. Metadata routing formalizes which objects request, propagate, reject, or consume those values.

### 4.1 Consumer and router model

The metadata system distinguishes:

- Consumers: Estimators, scorers, and CV splitters that use metadata.
- Routers: Pipelines, model-selection utilities, and meta-estimators that forward metadata to appropriate consumers.
- Requests: Method-specific declarations such as `set_fit_request()` and `set_score_request()`.

Common metadata include `sample_weight`, `groups`, and estimator-specific auxiliary inputs. Third-party implementations may define additional metadata.

Request semantics include:

| Request value | Meaning                                                    |
| ------------- | ---------------------------------------------------------- |
| `True`        | Request and forward metadata if supplied                   |
| `False`       | Do not request metadata                                    |
| `None`        | Explicitly reject the metadata if supplied through routing |
| String alias  | Accept metadata under a different externally supplied name |
| `UNCHANGED`   | Preserve the current request configuration                 |

Metadata requests are method-specific. A model may require weights for fitting while a scorer independently requests weights for evaluation. A group-based CV splitter consumes groups to construct folds but does not ordinarily pass those groups as model features.

### 4.2 Composition with pipelines and model selection

With routing enabled, a workflow can:

1. Pass sample weights to the estimator performing fitting.
2. Pass those same weights to a compatible metric or scorer.
3. Pass group labels to a group-aware CV splitter.
4. Pass custom metadata to a third-party estimator.
5. Exclude metadata from intermediate components that do not consume it.

The routing configuration can be inspected through `get_metadata_routing()`, with routing definitions represented through `MetadataRequest`, `MetadataRouter`, and associated utilities.

`Pipeline(transform_input=...)` adds another capability: selected metadata inputs can undergo the relevant transformations before reaching their consuming estimator, rather than simply being forwarded unchanged.

For example, a supported pipeline can transform a validation feature matrix using earlier fitted preprocessing stages before a downstream component consumes that matrix.

Limitations: In 1.9, metadata routing remains explicitly experimental and disabled by default. Coverage is broad but not universal, and unsupported nested components or missing routing requests can prevent metadata propagation. Version 1.9.1 specifically fixes several cases where metadata was incorrectly dropped through intermediate meta-estimators.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+2



Reference:

[https://scikit-learn.org/stable/metadata_routing.html](https://scikit-learn.org/stable/metadata_routing.html?utm_source=chatgpt.com)

## 5. Supervised learning: major model families and numerical mechanisms

Scikit-learn provides multiple algorithmic approaches to the same prediction problems. These differ in statistical assumptions, optimization methods, scalability, sparsity, treatment of nonlinearities, and types of prediction outputs.

### 5.1 Linear, generalized linear, and robust models

The `sklearn.linear_model` family extends substantially beyond ordinary least squares and logistic regression.

| Model family                     | Representative estimators                                                    | Distinctive capabilities                                                     |
| -------------------------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Least squares and regularization | `LinearRegression`, `Ridge`, `Lasso`, `ElasticNet`                           | L1/L2 penalties, coefficient sparsity, stable estimation under collinearity  |
| Regularization paths and CV      | `RidgeCV`, `LassoCV`, `ElasticNetCV`, `lars_path`, `lasso_path`, `enet_path` | Specialized paths, internal model selection, reuse of optimization structure |
| Generalized linear models        | `PoissonRegressor`, `GammaRegressor`, `TweedieRegressor`                     | Distribution-aware losses and link functions                                 |
| Classification                   | `LogisticRegression`, `LogisticRegressionCV`, `RidgeClassifier`              | Regularized classification with multiple solver choices                      |
| Robust regression                | `HuberRegressor`, `RANSACRegressor`, `TheilSenRegressor`                     | Reduced sensitivity to outliers and contaminated observations                |
| Quantile modeling                | `QuantileRegressor`                                                          | Conditional quantile estimation using pinball loss                           |
| Bayesian linear estimation       | `BayesianRidge`, `ARDRegression`                                             | Probabilistic coefficients, regularization, predictive uncertainty           |
| Stochastic optimization          | `SGDClassifier`, `SGDRegressor`                                              | Mini-batches, online learning, configurable loss and penalties               |
| Multitask learning               | `MultiTaskLasso`, `MultiTaskElasticNet`                                      | Joint regularization across related prediction targets                       |
| Linear latent relationships      | `PLSRegression`, `PLSCanonical`, `CCA`, `PLSSVD`                             | Cross-covariance modeling and latent projections between data matrices       |

Important computational distinctions:

- L1 regularization can produce sparse coefficient vectors, providing implicit feature selection.
- Ridge and related estimators offer specialized numerical solvers whose suitability depends on matrix shape, conditioning, sparsity, and dtype.
- Coordinate-descent methods can efficiently compute regularization paths and reuse numerical structure.
- SGD-based estimators provide an alternative when full-batch optimization is too expensive or incremental updates are required.
- Robust losses and quantile objectives change the statistical quantity being estimated, not merely solver efficiency.
- MultiTaskLasso and MultiTaskElasticNet jointly constrain multiple outputs, whereas `MultiOutputRegressor` fits separate regressors.

The generalized linear models are particularly useful when squared-error regression is statistically inappropriate. Poisson, Gamma, and Tweedie models represent different mean–variance relationships and outcome distributions.

`QuantileRegressor` and quantile-based gradient boosting provide routes to conditional quantile modeling. Quantile estimates can support prediction-interval construction, but valid interval coverage is not automatically guaranteed by fitting two quantile models.

Reference:

[https://scikit-learn.org/stable/modules/linear_model.html](https://scikit-learn.org/stable/modules/linear_model.html?utm_source=chatgpt.com)

### 5.2 Decision trees and ensembles

The tree-based ecosystem has multiple computational and statistical families.

Individual trees: `DecisionTreeClassifier`, `DecisionTreeRegressor`, and extremely randomized trees support nonlinear partitioning, different splitting criteria, pruning, and selected monotonic constraints.

Bagged and randomized ensembles: `RandomForestClassifier`, `RandomForestRegressor`, `ExtraTreesClassifier`, `ExtraTreesRegressor`, and `BaggingClassifier`/`BaggingRegressor` reduce variance through averaging or voting across fitted learners. Random forests also provide out-of-bag evaluation when appropriately configured.

Boosted models: `GradientBoostingClassifier`, `GradientBoostingRegressor`, `HistGradientBoostingClassifier`, and `HistGradientBoostingRegressor` fit successive learners against loss-derived corrections.

General-purpose ensembles: `VotingClassifier`, `VotingRegressor`, `StackingClassifier`, and `StackingRegressor` combine potentially heterogeneous estimators. Stacking uses learned meta-models, with cross-validated predictions supporting meta-learner training.

#### Histogram-based gradient boosting

`HistGradientBoostingClassifier` and `HistGradientBoostingRegressor` merit particular attention.

Their execution model uses quantized feature bins and histogram-based split search rather than repeatedly sorting continuous feature values at every node. The algorithm also uses second-order loss information and OpenMP parallelism.

Important capabilities include:

- Native missing-value handling by learning how missing observations are assigned at splits.
- Native categorical partitioning through `categorical_features`, including dataframe categorical dtypes.
- Monotonic constraints through `monotonic_cst`.
- Restrictions on feature interactions through `interaction_cst`.
- Early stopping and regularization controls.
- Sample weighting.
- Regression losses including squared error, absolute error, Poisson, Gamma, and quantile.

These mechanisms can remove preprocessing and constraint-handling code that would otherwise sit outside the estimator.

Tradeoffs: Categorical cardinality is limited by `max_bins`; some constraints and losses are estimator- or task-specific. Histogram binning is approximate, and the older non-histogram boosting estimators retain differences in supported options. The official guide explicitly distinguishes the two implementations rather than treating the histogram implementation as a universal replacement.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+1



Version 1.9 also expands missing-value support for dense decision-tree and forest inputs and permits certain monotonic constraints to coexist with missing values. These are material improvements in models that previously required more preprocessing or different configuration.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Reference:

[https://scikit-learn.org/stable/modules/ensemble.html](https://scikit-learn.org/stable/modules/ensemble.html?utm_source=chatgpt.com)

### 5.3 Kernel, neighbor-based, and Gaussian-process models

These model families provide nonlinear learning without requiring explicitly parameterized deep neural networks.

Support vector methods

- `SVC`, `NuSVC`, `LinearSVC` for classification.
- `SVR`, `NuSVR`, `LinearSVR` for regression.
- `OneClassSVM` for novelty detection.
- Linear, polynomial, radial-basis, sigmoid, callable, and precomputed kernels where supported.

Kernel methods can represent highly nonlinear decision surfaces through pairwise similarities. Their principal limitation is that training and prediction costs can become expensive as the number of observations grows.

Linear SVM implementations and explicit kernel approximations provide alternative computational paths.

Nearest-neighbor methods

- `NearestNeighbors`, `KNeighborsClassifier`, `KNeighborsRegressor`.
- Radius-based classifiers and regressors.
- `KDTree` and `BallTree`.
- Neighbor graph generation through `kneighbors_graph` and `radius_neighbors_graph`.

The neighbor infrastructure supports more than predictive models: its generated adjacency structures are useful in manifold methods, clustering, graph-based preprocessing, and anomaly detection.

Tree-based neighbor indexing can be effective for suitable dimensions and metrics, but may lose its advantage in high-dimensional spaces. Brute-force pairwise computation may then be competitive.

Gaussian processes

`GaussianProcessRegressor` and `GaussianProcessClassifier` provide kernel-based probabilistic modeling.

Distinctive capabilities include kernel composition, hyperparameter optimization through marginal likelihood, multiple optimizer restarts, observation-noise specification, and predictive uncertainty. The regressor exposes `sample_y()` and `log_marginal_likelihood()` in addition to standard estimator methods.

These features are useful where uncertainty estimation, surrogate modeling, or flexible covariance structures matter.

However, scikit-learn's standard Gaussian-process implementation is not a sparse or inducing-point approximation framework. Kernel-matrix factorization limits scalability, especially as the number of training observations grows.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+1



References:

[https://scikit-learn.org/stable/modules/svm.html](https://scikit-learn.org/stable/modules/svm.html?utm_source=chatgpt.com)

[https://scikit-learn.org/stable/modules/neighbors.html](https://scikit-learn.org/stable/modules/neighbors.html?utm_source=chatgpt.com)

[https://scikit-learn.org/stable/modules/gaussian_process.html](https://scikit-learn.org/stable/modules/gaussian_process.html?utm_source=chatgpt.com)

### 5.4 Other supervised capabilities

Several additional model families and meta-estimators extend the supervised-learning scope.

| Capability                         | Mechanisms                                                          | Distinction                                                                    |
| ---------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Discriminant analysis              | `LinearDiscriminantAnalysis`, `QuadraticDiscriminantAnalysis`       | Probabilistic class modeling using covariance assumptions                      |
| Naive Bayes                        | Gaussian, multinomial, complement, Bernoulli, categorical variants  | Efficient probabilistic classifiers under conditional-independence assumptions |
| Neural networks                    | `MLPClassifier`, `MLPRegressor`                                     | Configurable feedforward nonlinear models, some incremental training support   |
| Multiclass adaptation              | `OneVsRestClassifier`, `OneVsOneClassifier`, `OutputCodeClassifier` | Reduction of multiclass tasks to sets of simpler classifiers                   |
| Multioutput learning               | `MultiOutputClassifier`, `MultiOutputRegressor`                     | Independent model fitting across outputs                                       |
| Chained predictions                | `ClassifierChain`, `RegressorChain`                                 | Sequential modeling of dependencies among prediction outputs                   |
| Semi-supervised classification     | `SelfTrainingClassifier`, `LabelPropagation`, `LabelSpreading`      | Learning from mixtures of labeled and unlabeled samples                        |
| Monotonic nonparametric regression | `IsotonicRegression`                                                | Order-constrained fitting without assuming a linear response                   |

Scikit-learn's MLP implementations are general-purpose estimators, not substitutes for dedicated deep-learning frameworks. The official documentation explicitly states that these implementations do not provide GPU acceleration and are not intended for large-scale neural-network applications.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



The multiclass and multioutput meta-estimators are important because they can extend compatible base learners without changing those learners' implementations.

References:

[https://scikit-learn.org/stable/modules/multiclass.html](https://scikit-learn.org/stable/modules/multiclass.html?utm_source=chatgpt.com)

[https://scikit-learn.org/stable/modules/semi_supervised.html](https://scikit-learn.org/stable/modules/semi_supervised.html?utm_source=chatgpt.com)

[https://scikit-learn.org/stable/modules/neural_networks_supervised.html](https://scikit-learn.org/stable/modules/neural_networks_supervised.html?utm_source=chatgpt.com)

## 6. Unsupervised learning and statistical structure discovery

Scikit-learn provides several complementary ways to extract structure from observations without an explicit supervised prediction target.

### 6.1 Clustering

| Family           | Representative estimators                         | Statistical/computational behavior                                 |
| ---------------- | ------------------------------------------------- | ------------------------------------------------------------------ |
| Centroid-based   | `KMeans`, `MiniBatchKMeans`, `BisectingKMeans`    | Compact clusters represented by learned centroids                  |
| Density-based    | `DBSCAN`, `HDBSCAN`, `OPTICS`                     | Density-connected clusters, noise labeling, irregular geometries   |
| Hierarchical     | `AgglomerativeClustering`, `FeatureAgglomeration` | Dendrogram or hierarchical feature grouping                        |
| Graph/spectral   | `SpectralClustering`                              | Partitioning based on affinities and graph eigenstructure          |
| Other clustering | `MeanShift`, `AffinityPropagation`, `Birch`       | Mode seeking, exemplar selection, incremental clustering summaries |
| Biclustering     | `SpectralCoclustering`, `SpectralBiclustering`    | Joint grouping of rows and columns                                 |

Important distinctions:

- KMeans versus MiniBatchKMeans: Full-data centroid optimization versus approximate updates using mini-batches.
- DBSCAN versus HDBSCAN: A single density threshold versus hierarchical density-based cluster discovery.
- OPTICS: Builds an ordering and reachability representation from which cluster structures can be extracted at different density levels.
- Birch: Maintains compact clustering-feature summaries and supports incremental fitting.
- AgglomerativeClustering: Can use a predefined connectivity graph, making neighborhood structure relevant to hierarchical merges.

Density-based clustering can identify arbitrarily shaped clusters and distinguish noise from assigned samples, but its memory costs vary substantially. Scikit-learn's DBSCAN can require quadratic memory in unfavorable conditions. Sparse radius-neighbor graphs and OPTICS are documented alternatives for certain workloads.

Scikit-learn's native `HDBSCAN` should also be distinguished from the separate `hdbscan` package; even similarly named parameters can have different definitions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+2



Reference:

[https://scikit-learn.org/stable/modules/clustering.html](https://scikit-learn.org/stable/modules/clustering.html?utm_source=chatgpt.com)

### 6.2 Dimensionality reduction and matrix factorization

The decomposition subsystem supports several objectives that are often incorrectly grouped together as generic dimensionality reduction.

| Technique                      | Representative estimators                                          | Primary purpose                                                                    |
| ------------------------------ | ------------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| Principal-component methods    | `PCA`, `IncrementalPCA`, `SparsePCA`, `MiniBatchSparsePCA`         | Variance-preserving linear representations                                         |
| Singular-value decomposition   | `TruncatedSVD`                                                     | Low-rank decomposition without explicit centering; useful for sparse text matrices |
| Kernel PCA                     | `KernelPCA`                                                        | Nonlinear reduction through kernel methods                                         |
| Nonnegative factorization      | `NMF`, `MiniBatchNMF`                                              | Additive, nonnegative latent components                                            |
| Independent component analysis | `FastICA`                                                          | Statistically independent latent signal components                                 |
| Factor analysis                | `FactorAnalysis`                                                   | Latent-factor modeling with noise structure                                        |
| Sparse dictionary learning     | `DictionaryLearning`, `MiniBatchDictionaryLearning`, `SparseCoder` | Sparse representation of samples using learned basis elements                      |
| Topic modeling                 | `LatentDirichletAllocation`                                        | Probabilistic document-topic representation                                        |

The PCA family offers multiple solvers, including full and randomized SVD approaches. `IncrementalPCA` trades computational and memory behavior for batch-oriented fitting.

`TruncatedSVD` does not center features as PCA does, allowing efficient use with sparse representations. `NMF` instead imposes nonnegativity and yields additive components, which can be more interpretable in appropriate domains.

Sparse dictionary learning is another distinct facility: it aims to encode observations using relatively few active dictionary atoms rather than simply retain directions of maximum variance.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Reference:

[https://scikit-learn.org/stable/modules/decomposition.html](https://scikit-learn.org/stable/modules/decomposition.html?utm_source=chatgpt.com)

### 6.3 Manifold learning and nonlinear embedding

The manifold subsystem includes:

- `Isomap`: Neighborhood graphs and geodesic-distance preservation.
- `LocallyLinearEmbedding`: Local reconstruction weights.
- `SpectralEmbedding`: Eigenvectors of graph-based operators.
- `MDS` and `ClassicalMDS`: Low-dimensional reconstruction of pairwise dissimilarities.
- `TSNE`: Neighborhood-preserving nonlinear embedding primarily used for exploration and visualization.

These methods can reveal structure not well captured by global linear projections.

The important distinction is between learning a reusable transformation and embedding a fixed collection of observations. Some methods, notably t-SNE, do not provide a standard reusable `transform()` interface for arbitrary new observations.

This limits their interchangeability with PCA or other fitted transformers inside prediction pipelines.

Reference:

[https://scikit-learn.org/stable/modules/manifold.html](https://scikit-learn.org/stable/modules/manifold.html?utm_source=chatgpt.com)

### 6.4 Probabilistic mixtures, covariance, and density estimation

Additional statistical capabilities include:

Mixture modeling: `GaussianMixture` and `BayesianGaussianMixture` provide probabilistic cluster assignments, likelihood evaluation, covariance-structure choices, and component modeling. Gaussian mixtures support information-criterion-based selection through AIC and BIC; Bayesian mixtures use variational inference and component-weight priors.

Covariance estimation: `EmpiricalCovariance`, `LedoitWolf`, `OAS`, `ShrunkCovariance`, `GraphicalLasso`, `GraphicalLassoCV`, and `MinCovDet` provide covariance shrinkage, sparse inverse covariance estimation, and robust alternatives.

Density estimation: `KernelDensity` implements nonparametric density estimation with configurable kernels, bandwidths, and suitable spatial search structures.

Anomaly and novelty detection: `IsolationForest`, `LocalOutlierFactor`, `OneClassSVM`, `SGDOneClassSVM`, and `EllipticEnvelope` capture substantially different definitions of abnormality.

A subtle distinction concerns `LocalOutlierFactor`: ordinary outlier-detection mode evaluates the observed training collection, while `novelty=True` permits scoring new observations. Their available prediction interfaces differ, and scores for training observations need not match between the two modes.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+1



References:

[https://scikit-learn.org/stable/modules/mixture.html](https://scikit-learn.org/stable/modules/mixture.html?utm_source=chatgpt.com)

[https://scikit-learn.org/stable/modules/covariance.html](https://scikit-learn.org/stable/modules/covariance.html?utm_source=chatgpt.com)

[https://scikit-learn.org/stable/modules/density.html](https://scikit-learn.org/stable/modules/density.html?utm_source=chatgpt.com)

[https://scikit-learn.org/stable/modules/outlier_detection.html](https://scikit-learn.org/stable/modules/outlier_detection.html?utm_source=chatgpt.com)

## 7. Model selection, statistical validation, and evaluation

Scikit-learn's model-selection facilities are not limited to hyperparameter search. They provide a unified framework for data partitioning, repeated estimator fitting, statistical comparison, model selection, and post-fit decision optimization.

### 7.1 Cross-validation as a reusable execution mechanism

The `sklearn.model_selection` module supports multiple assumptions about how observations may be partitioned.

| Validation strategy        | Principal splitters                                                    | Appropriate data structure                                                  |
| -------------------------- | ---------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Ordinary K-fold            | `KFold`, `RepeatedKFold`, `ShuffleSplit`                               | Approximately independent and identically distributed observations          |
| Stratified                 | `StratifiedKFold`, `RepeatedStratifiedKFold`, `StratifiedShuffleSplit` | Classification with preservation of class proportions                       |
| Group-aware                | `GroupKFold`, `GroupShuffleSplit`, `LeaveOneGroupOut`                  | Observations sharing an entity, subject, experiment, or other group         |
| Stratified and group-aware | `StratifiedGroupKFold`                                                 | Classification requiring both group isolation and approximate class balance |
| Temporal                   | `TimeSeriesSplit`                                                      | Ordered observations where later data must not enter earlier training folds |
| Leave-one/few-out          | `LeaveOneOut`, `LeavePOut`                                             | Specialized validation on small datasets                                    |
| Precomputed                | `PredefinedSplit`                                                      | Fixed external train/validation assignments                                 |

`TimeSeriesSplit` provides `gap`, `test_size`, and `max_train_size` controls. These support expanding or bounded training windows and a configurable separation between training and evaluation observations. They do not automatically solve all temporal leakage problems, such as overlapping forecast horizons or labels whose information spans the split boundary.

The principal evaluation functions have distinct roles:

- `cross_val_score`: Single-metric cross-validation.
- `cross_validate`: Multi-metric scoring, training and scoring durations, optional fitted estimators, and optional train/test index returns.
- `cross_val_predict`: Out-of-fold predictions for observations under appropriate partitioning conditions.
- `permutation_test_score`: Permutation-based statistical significance testing.
- `learning_curve`: Performance across training-set sizes, including optional exploitation of incremental learning.
- `validation_curve`: Performance across values of one hyperparameter.

A crucial distinction: `cross_val_predict()` is not interchangeable with `cross_val_score()`. Aggregating out-of-fold predictions into a single metric need not equal averaging fold metrics, particularly for nonlinear or non-decomposable scoring functions.

Nested cross-validation separates hyperparameter selection from outer performance estimation and can avoid the optimistic bias of reporting the same validation scores used to choose the model.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+1



Reference:

[https://scikit-learn.org/stable/modules/cross_validation.html](https://scikit-learn.org/stable/modules/cross_validation.html?utm_source=chatgpt.com)

### 7.2 Hyperparameter optimization

Scikit-learn exposes multiple strategies behind compatible estimator interfaces.

| Search method             | Mechanism                                          | Principal tradeoff                                                   |
| ------------------------- | -------------------------------------------------- | -------------------------------------------------------------------- |
| `GridSearchCV`            | Exhaustive Cartesian parameter grid                | Systematic coverage; combinatorial cost                              |
| `RandomizedSearchCV`      | Fixed-budget sampling from parameter distributions | Better control of candidate count and continuous spaces              |
| `HalvingGridSearchCV`     | Successive halving of a parameter grid             | Early elimination of candidates using smaller resource budgets       |
| `HalvingRandomSearchCV`   | Randomized candidates with successive halving      | Combines randomized exploration with progressive resource allocation |
| Specialized CV estimators | `RidgeCV`, `LassoCV`, `ElasticNetCV`, etc.         | Algorithm-specific reuse and optimized internal selection            |

Successive-halving estimators can allocate resources in stages, commonly through numbers of samples or a configurable integer estimator parameter. They assume early, lower-resource performance is useful for deciding which candidates deserve further evaluation. That assumption is not universally valid.

As of 1.9.1, successive-halving search remains experimental and requires explicit enabling through `sklearn.experimental.enable_halving_search_cv`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



#### Advanced selection mechanisms

Search objects support more than choosing the candidate with the highest mean validation score.

- Multiple scorers: Evaluate competing objectives for each parameter combination.
- Custom `refit`: Select a candidate using a callable that examines the complete `cv_results_` structure.
- Conditional parameter spaces: Lists of parameter dictionaries allow different configurations or even different estimator choices.
- Fit-failure handling: `error_score` controls whether failed candidates raise exceptions or receive fallback scores.
- Parallel fitting: `n_jobs` and `pre_dispatch` control joblib-based execution and task dispatch.
- Nested component tuning: Parameter paths can reach through pipelines and meta-estimators.

A custom `refit` callable can encode a selection policy that considers score, variance, training duration, or complexity. It does not turn search into a native multi-objective optimization engine, but it can eliminate substantial custom result-ranking code.

When `refit` is callable, `best_estimator_` and `best_params_` are available, while `best_score_` is not defined.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+1



Reference:

[https://scikit-learn.org/stable/modules/grid_search.html](https://scikit-learn.org/stable/modules/grid_search.html?utm_source=chatgpt.com)

### 7.3 Metrics, scorers, and decision objectives

Scikit-learn separates metric calculations from estimator-aware scoring objects.

A metric ordinarily receives observed and predicted quantities. A scorer receives an estimator and data, invokes an appropriate prediction method, and computes a scalar where larger values are preferable.

`make_scorer()` bridges these interfaces. Its `response_method` parameter specifies whether the scorer should use `predict`, `predict_proba`, or `decision_function`. `greater_is_better=False` converts a loss into the maximization convention used by model-selection tools.

Consequently, a scorer named `neg_mean_squared_error` returns a negative loss, not an unusual form of mean squared error.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



The principal metric families include:

| Problem                   | Representative measures                                                                        | What the distinction captures                                             |
| ------------------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Classification labels     | Accuracy, balanced accuracy, precision, recall, F1/F-beta, Matthews correlation, Cohen's kappa | Error distribution, class imbalance, and asymmetric consequences          |
| Classification scores     | ROC AUC, average precision, log loss, Brier score                                              | Ranking quality versus probabilistic accuracy                             |
| Regression                | MAE, MSE, RMSE, \\(R^2\\), explained variance, median absolute error                           | Sensitivity to large errors, baseline-relative fit, robust central errors |
| Specialized regression    | Pinball loss, Tweedie deviance, Poisson/Gamma deviance, D² scores                              | Distribution-aware and quantile-oriented evaluation                       |
| Clustering with labels    | Adjusted Rand, adjusted mutual information, homogeneity, completeness, V-measure               | Agreement with externally supplied cluster labels                         |
| Clustering without labels | Silhouette, Calinski–Harabasz, Davies–Bouldin                                                  | Intrinsic separation and cohesion                                         |
| Ranking/multilabel        | Label-ranking average precision, coverage error, hamming loss, subset accuracy                 | Different notions of relevance and multilabel correctness                 |

Metrics often expose averaging, sample-weighting, and multioutput options, but these are not universal across every function.

Architectural implication: Model training, model selection, and downstream decision objectives can use different but explicitly defined metrics, avoiding the assumption that the estimator's native objective is automatically the correct application objective.

Reference:

[https://scikit-learn.org/stable/modules/model_evaluation.html](https://scikit-learn.org/stable/modules/model_evaluation.html?utm_source=chatgpt.com)

### 7.4 Probability calibration versus decision-threshold optimization

These are separate operations.

Probability calibration attempts to make predicted probabilities better aligned with observed event frequencies. `CalibratedClassifierCV` supports:

- Sigmoid calibration.
- Isotonic calibration.
- Temperature scaling, introduced in version 1.8.

Its `ensemble=True` and `ensemble=False` modes differ in whether prediction uses an ensemble of calibrated fold models or a model refitted on the full training data with a calibrator learned from out-of-fold predictions.

`FrozenEstimator` allows calibration of a pre-fitted classifier without fitting it again; the caller must ensure that the calibration data is separate from the data used to train that classifier.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Decision-threshold optimization changes how scores or probabilities become discrete class predictions.

- `TunedThresholdClassifierCV` selects a threshold by cross-validation against a scorer.
- `FixedThresholdClassifier` applies an explicitly supplied threshold.
- `metric_at_thresholds`, introduced in 1.9, evaluates metrics across candidate score thresholds.

These mechanisms allow an application to retain the same probabilistic model while changing its decision policy according to error costs or operating constraints.

Threshold tuning should not reuse the model's training observations as an unconstrained tuning set. Calibration and threshold optimization can also overfit their respective validation data.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



References:

[https://scikit-learn.org/stable/modules/calibration.html](https://scikit-learn.org/stable/modules/calibration.html?utm_source=chatgpt.com)

[https://scikit-learn.org/stable/modules/classification_threshold.html](https://scikit-learn.org/stable/modules/classification_threshold.html?utm_source=chatgpt.com)

## 8. Feature selection, model inspection, and diagnostics

### 8.1 Feature selection as estimator-compatible transformation

`sklearn.feature_selection` provides three conceptually different approaches.

| Approach              | Components                                                                                    | Meaning                                                                      |
| --------------------- | --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Statistical filters   | `VarianceThreshold`, `SelectKBest`, `SelectPercentile`, `SelectFdr`, `SelectFpr`, `SelectFwe` | Select features using individual statistics or significance criteria         |
| Model-based selection | `SelectFromModel`, `RFE`, `RFECV`                                                             | Use estimator-derived feature importance and repeated model fitting          |
| Wrapper selection     | `SequentialFeatureSelector`                                                                   | Greedy forward/backward selection based on cross-validated model performance |

These can participate as transformers inside pipelines, including during hyperparameter search.

`SelectFdr` and related statistical selectors provide native multiple-testing controls that are easy to overlook. `RFECV` selects the number of retained features through cross-validation, while `SequentialFeatureSelector` can work with estimators that do not expose coefficient-based feature importance.

Their computational costs differ considerably: repeated estimator fitting can dominate the cost of wrapper and recursive selection. Correlated features can also make importance rankings unstable.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+2



Reference:

[https://scikit-learn.org/stable/modules/feature_selection.html](https://scikit-learn.org/stable/modules/feature_selection.html?utm_source=chatgpt.com)

### 8.2 Model-independent inspection

Scikit-learn provides estimator-agnostic inspection through:

- `permutation_importance()`: Measures score degradation after perturbing one feature.
- `partial_dependence()`: Computes average modeled responses over selected feature values.
- `PartialDependenceDisplay`: Partial-dependence, individual conditional expectation, and related visualizations.
- `DecisionBoundaryDisplay`: Two-dimensional decision surfaces.

Permutation importance measures a model's reliance on features for a specified dataset and scorer. It is not an intrinsic causal effect or universal feature-ranking statistic.

Strongly correlated features can receive deceptively small individual permutation importances because the model can recover predictive information from correlated alternatives.

Partial-dependence methods similarly describe a fitted model rather than establishing causal relationships. Marginalizing features can construct combinations that are implausible or absent from the original joint distribution.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+1



Additional estimator-specific diagnostics include learning curves, validation curves, calibration curves, confusion matrices, precision–recall curves, ROC curves, fitted coefficients, split feature importances, support vectors, tree structure, and out-of-bag scores where supported.

References:

[https://scikit-learn.org/stable/inspection.html](https://scikit-learn.org/stable/inspection.html?utm_source=chatgpt.com)

[https://scikit-learn.org/stable/modules/permutation_importance.html](https://scikit-learn.org/stable/modules/permutation_importance.html?utm_source=chatgpt.com)

## 9. Experimental callback infrastructure: fitting-time observability and control

Scikit-learn 1.9 introduces an experimental callback framework for observing and extending supported fitting operations without rewriting the underlying optimization or orchestration code.

Its model is a hierarchy of fitting tasks: a complete fit may contain pipeline steps, cross-validation folds, candidate fits, solver iterations, or other estimator-defined units of work.

### 9.1 Built-in capabilities

| Mechanism              | Role                                                                |
| ---------------------- | ------------------------------------------------------------------- |
| `set_callbacks()`      | Registers callback objects on compatible estimators                 |
| `ProgressBar`          | Presents progress across fitting tasks                              |
| `ScoringMonitor`       | Computes and records scoring metrics during supported fitting tasks |
| `CallbackContext`      | Represents a fitting task and its metadata                          |
| `CallbackSupportMixin` | Adds callback registration and integration to custom estimators     |
| `with_callbacks`       | Supports callback lifecycle and cleanup in third-party estimators   |

`ScoringMonitor` can capture per-iteration metrics and expose logs for later analysis. This is distinct from computing only a final training or validation score.

### 9.2 Regular versus auto-propagated callbacks

- Regular callbacks attach to a given estimator and can execute when its clones are fitted inside a meta-estimator.
- Auto-propagated callbacks, including `ProgressBar`, can be registered on the top-level compatible meta-estimator and propagate through compatible nested components.

Task contexts retain parent-child relationships, creating an observable structure for composite fitting operations.

For third-party estimators, the callback developer API permits reporting task boundaries, supplying temporarily reconstructed fitted state to callbacks, lazily computing expensive callback inputs, and interpreting callback requests to interrupt iterative fitting. These are integration capabilities, not a blanket guarantee that all native scikit-learn solvers can be stopped or controlled through callbacks.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+1



### 9.3 Availability boundaries in 1.9.1

Native callback support is limited to:

- `LogisticRegression`, specifically `solver="lbfgs"`.
- `GridSearchCV`, `RandomizedSearchCV`, and the two successive-halving search estimators.
- `Pipeline`.
- `StandardScaler`.

The API remains experimental and may change without the ordinary deprecation cycle. It does not yet constitute a universal training-event system across all scikit-learn algorithms.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+1



The general architectural opportunity is nevertheless significant: when compatible, callbacks allow progress reporting, metric monitoring, and task-aware control to be expressed independently of estimator implementation.

References:

[https://scikit-learn.org/stable/callbacks.html](https://scikit-learn.org/stable/callbacks.html?utm_source=chatgpt.com)

[https://scikit-learn.org/stable/developers/callback_support.html](https://scikit-learn.org/stable/developers/callback_support.html?utm_source=chatgpt.com)

[https://scikit-learn.org/stable/api/sklearn.callback.html](https://scikit-learn.org/stable/api/sklearn.callback.html?utm_source=chatgpt.com)

## 10. Data interoperability and feature-schema semantics

Scikit-learn is closely integrated with the Python numerical ecosystem, but its supported data interfaces have different semantics. The distinction between accepting an input format, preserving that format, and executing natively on its underlying engine is especially important.

### 10.1 NumPy, SciPy sparse, pandas, and Polars

| Representation               | Native capability                                                          | Important boundary                                                                            |
| ---------------------------- | -------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| NumPy arrays                 | Primary numerical representation for most estimators                       | Typically homogeneous numeric dtype                                                           |
| SciPy sparse matrices/arrays | Supported by selected estimators and transformers                          | Sparse support varies; centering and some transformations cause densification                 |
| pandas DataFrames            | Named-column input, dtype-based selection, configurable transformer output | Fitting commonly converts to numerical arrays; pandas operations are not an execution backend |
| Polars DataFrames            | Named-column input and configurable transformer output                     | Does not make estimator internals lazy or execute them through Polars expressions             |
| Array API tensors            | Experimental dispatch for a documented subset of algorithms                | Requires compatible device, namespace, estimator, and dependency versions                     |

This means a dataframe can provide input schema and column-selection semantics without the learning algorithm itself executing as dataframe expressions.

### 10.2 Feature names and dataframe output

`feature_names_in_`, `n_features_in_`, and `get_feature_names_out()` support propagation of feature identity through compatible estimators.

`set_output(transform="pandas")` and `set_output(transform="polars")` configure individual transformer outputs. The corresponding global setting is:

`sklearn.set_config(transform_output="pandas")`

or `"polars"`.

This is valuable when an intermediate transformed feature matrix must remain inspectable by name rather than requiring a separate mapping from numerical column positions to original features.

Version 1.9 additionally improves estimator HTML representations by exposing fitted attributes and displaying output feature names from `ColumnTransformer` and `FeatureUnion`. That is an inspection enhancement, not a guarantee of full dataframe schema preservation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+1



Important limitations:

- Output configuration applies to compatible transformers, not every estimator or method.
- Sparse transformer output can be incompatible with dataframe output settings; for example, dense one-hot output may be necessary before configuring a pandas result.
- Column names are not a substitute for a complete schema contract that validates data semantics, units, permitted categories, or relationships.
- A transformation may change dimensions, feature order, or representation, so feature-name support must be examined for each component.

Reference:

[https://scikit-learn.org/stable/modules/df_output_transform.html](https://scikit-learn.org/stable/modules/df_output_transform.html?utm_source=chatgpt.com)

### 10.3 SciPy sparse-array migration

A material change in scikit-learn 1.9 is the addition of:

`sklearn.set_config(sparse_interface="sparray")`

The configuration supports two values:

- `"spmatrix"`: Return SciPy sparse matrix objects, the 1.9 default.
- `"sparray"`: Return SciPy sparse array objects.

SciPy sparse matrices and sparse arrays do not have identical operator semantics. In particular, array-style elementwise multiplication differs from the historical sparse-matrix interpretation of `*`.

Scikit-learn provides this setting so applications and integrated libraries can transition deliberately rather than relying on an implicit future representation change.

The upstream roadmap says the default is expected to become `"sparray"` in a later release, but this change has not occurred in 1.9.1.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+1



This mechanism is particularly relevant at interfaces where sparse output is consumed by other numerical libraries that distinguish sparse arrays from sparse matrices.

### 10.4 Experimental Array API dispatch and accelerators

Scikit-learn implements selective support for the Python Array API standard, allowing compatible numerical operations to use namespaces other than NumPy.

The 1.9.1 documentation identifies tested support for:

| Array library | Device classes      |
| ------------- | ------------------- |
| PyTorch       | CPU, CUDA, MPS, XPU |
| CuPy          | CUDA                |
| dpnp          | CPU, Intel GPU/SYCL |

Enabling the capability requires `SCIPY_ARRAY_API=1` before importing SciPy and scikit-learn, together with `array_api_dispatch=True` in scikit-learn's configuration. The feature remains experimental.

Supported estimators include selected configurations of:

- `PCA`.
- `Ridge`, `RidgeCV`, `RidgeClassifier`, and `RidgeClassifierCV`.
- `LogisticRegression` and `PoissonRegressor`, with the L-BFGS solver.
- `LinearDiscriminantAnalysis`.
- `GaussianNB` and `GaussianMixture`.
- `Nystroem`.
- Several preprocessing transformers and compatible metrics.

Version 1.9 specifically adds or extends Array API support for L-BFGS logistic and Poisson regression, Nyström kernel approximation, feature unions, and additional metrics.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+1



#### Namespace and device propagation

The interoperability model has more precise semantics than merely accepting GPU tensors:

1. Supported estimators follow the array namespace and device of the feature input `X`.
2. Other input arrays, including `y` and `sample_weight`, may be converted to match `X`.
3. Fitted array attributes generally remain in the training namespace and device.
4. Subsequent prediction or transformation expects compatible input namespaces/devices.
5. Array API-compatible scoring functions follow the namespace/device of `y_pred`.

These rules allow some composed operations to cross CPU and GPU boundaries while preserving the semantics needed by the participating estimators.

However, scikit-learn does not automatically migrate an already fitted model between devices through its ordinary `predict()` protocol. The documentation illustrates `sklearn.utils._array_api.move_estimator_to`, but its underscore-prefixed module path means it should not be treated as a stable public device-transfer API.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Most important limitation: Array API support is selective, not general GPU acceleration for scikit-learn. Algorithms implemented primarily through specialized Cython code, including many tree-based estimators, do not automatically acquire GPU support.

Performance depends on transfer costs, workload dimensions, data type, supported operations, and device-specific numerical capabilities. Some devices lack `float64` support for operations that would ordinarily use it, with potential numerical consequences.

Reference:

[https://scikit-learn.org/stable/modules/array_api.html](https://scikit-learn.org/stable/modules/array_api.html?utm_source=chatgpt.com)

## 11. Incremental learning, approximate computation, and numerical utilities

Scikit-learn has several mechanisms for reducing the memory or computational burden of learning. They work at different levels and should not be treated as interchangeable.

### 11.1 `partial_fit` versus `warm_start`

`partial_fit` defines an incremental update interface for estimators capable of incorporating successive batches without reconstructing the model from the complete historical dataset.

Examples include:

| Problem type   | Incremental estimators                                                                       |
| -------------- | -------------------------------------------------------------------------------------------- |
| Classification | `SGDClassifier`, `Perceptron`, selected Naive Bayes estimators, `MLPClassifier`              |
| Regression     | `SGDRegressor`, `MLPRegressor`                                                               |
| Clustering     | `MiniBatchKMeans`, `Birch`                                                                   |
| Decomposition  | `IncrementalPCA`, `MiniBatchNMF`, `MiniBatchDictionaryLearning`, `LatentDirichletAllocation` |
| Preprocessing  | `StandardScaler`, `MinMaxScaler`, `MaxAbsScaler`                                             |

For some classifiers, the first call to `partial_fit` must establish the full possible class set using `classes=`.

`warm_start`, by contrast, permits selected estimators to reuse fitted state when `fit()` is called again. It is generally intended for repeated fitting under compatible conditions—for example, adding more trees or continuing iterations—not as a universal replacement for incremental learning on distinct data batches.

A third concept, cached transformation, avoids recomputing fitted preprocessing but does not imply that a learner can update its model incrementally.

These three mechanisms target different costs: updating learned state, reusing initialized state, and avoiding repeated preprocessing.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



### 11.2 Out-of-core learning

Scikit-learn's documented out-of-core architecture combines:

- An external source of mini-batches.
- A feature extraction mechanism that does not require keeping the complete input in memory.
- An estimator supporting incremental updates.

`HashingVectorizer` or `FeatureHasher` can be particularly effective where the complete feature vocabulary is unknown or evolving.

The library does not itself provide a general streaming data-ingestion framework. File readers, database cursors, distributed storage access, and streaming orchestration remain the caller's responsibilities.

Reference:

[https://scikit-learn.org/stable/computing/scaling_strategies.html](https://scikit-learn.org/stable/computing/scaling_strategies.html?utm_source=chatgpt.com)

### 11.3 Randomized projections and approximate linear algebra

Scikit-learn offers native numerical approximations that can be useful independently of its predictive estimators.

Random projection

`GaussianRandomProjection` and `SparseRandomProjection` create lower-dimensional representations using random matrices. These rely on probabilistic distance-preservation properties and trade representation accuracy for reduced dimensionality and computational cost.

Randomized SVD

`sklearn.utils.extmath.randomized_svd()` and corresponding decomposition estimators use randomized subspace methods to approximate leading singular components. Power iterations and oversampling allow accuracy/cost tradeoffs.

Kernel approximation

`RBFSampler`, `Nystroem`, and related transformers approximate nonlinear kernel mappings with finite-dimensional features.

Pairwise calculations

`pairwise_distances`, `pairwise_kernels`, `pairwise_distances_argmin`, and `pairwise_distances_chunked` provide reusable numerical primitives for similarity and distance-based operations.

The key distinctions are:

- Random projection approximates geometric representation.
- Randomized SVD approximates low-rank linear structure.
- Kernel approximation replaces implicit nonlinear relationships with explicit features.
- Chunking controls intermediate-memory growth without necessarily changing the mathematical result.

These are complementary techniques, not equivalent ways of making any estimator scalable.

References:

[https://scikit-learn.org/stable/modules/random_projection.html](https://scikit-learn.org/stable/modules/random_projection.html?utm_source=chatgpt.com)

[https://scikit-learn.org/stable/modules/kernel_approximation.html](https://scikit-learn.org/stable/modules/kernel_approximation.html?utm_source=chatgpt.com)

[https://scikit-learn.org/stable/modules/metrics.html](https://scikit-learn.org/stable/modules/metrics.html?utm_source=chatgpt.com)

### 11.4 Pairwise kernels and distances as reusable infrastructure

The pairwise subsystem contains algorithms that can be reused beyond a single predictor:

- Euclidean, Manhattan, cosine, haversine, and other supported distances.
- Linear, polynomial, RBF, sigmoid, Laplacian, and other kernel functions.
- Nearest-centroid and nearest-neighbor distance reductions.
- Precomputed affinity and distance matrix interfaces.
- Blockwise pairwise calculations to limit memory pressure.

These utilities can replace bespoke pairwise numerical kernels and also supply compatible inputs to clustering, embedding, kernel learning, and anomaly-detection algorithms.

Some downstream methods consume a full pairwise matrix whose space requirement grows quadratically with observations. A chunked distance calculation alone does not eliminate that cost if the consumer still requires full materialization.

## 12. Computational execution and resource management

Scikit-learn's performance architecture combines several native execution systems. Understanding their interaction is more useful than treating `n_jobs` as a universal parallelism switch.

### 12.1 Three layers of parallel execution

| Layer                          | Underlying mechanism            | Typical use                                                  |
| ------------------------------ | ------------------------------- | ------------------------------------------------------------ |
| High-level task parallelism    | joblib                          | Independent folds, parameter candidates, ensemble components |
| Compiled algorithm parallelism | OpenMP                          | Parallel loops in C/Cython implementations                   |
| Numerical kernel parallelism   | BLAS/LAPACK through NumPy/SciPy | Matrix multiplication, factorizations, linear algebra        |

`n_jobs` controls joblib-managed parallelism where supported. It does not directly set the number of OpenMP threads or BLAS threads.

For compiled numerical execution, relevant controls include `OMP_NUM_THREADS`, library-specific BLAS environment variables, and `threadpoolctl`.

Scikit-learn also uses specialized Cython pairwise-distance reductions for supported operations. Global configuration includes related controls, but the documentation describes some of these as internal benchmarking parameters rather than generally beneficial optimization knobs.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+1



### 12.2 Nested parallelism and oversubscription

Suppose a model-selection routine executes several fits concurrently, each of which uses OpenMP or multithreaded BLAS internally.

Without coordination, the total number of runnable threads can substantially exceed available CPU resources. The result may be slower execution because of oversubscription, scheduling overhead, and memory contention.

Joblib's default `loky` process backend applies heuristics to limit native thread pools inside workers. This protection is not universal: explicitly configured environment variables can override it, and the joblib threading backend has different behavior.

Joblib can also use memory mapping to share sufficiently large arrays across worker processes, avoiding some copying costs.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



### 12.3 Memory, validation, and performance configuration

Several global settings affect computation:

| Setting                         | Purpose                                            | Caution                                            |
| ------------------------------- | -------------------------------------------------- | -------------------------------------------------- |
| `working_memory`                | Memory budget for certain chunk-capable algorithms | Applies only where the implementation honors it    |
| `pairwise_dist_chunk_size`      | Chunk size for accelerated pairwise reductions     | Mainly intended for internal benchmarking/testing  |
| `enable_cython_pairwise_dist`   | Enable accelerated pairwise-distance backend       | Not a universal speed toggle                       |
| `assume_finite`                 | Skip finiteness checks                             | May allow invalid numerical input and crashes      |
| `skip_parameter_validation`     | Skip selected public parameter checks              | Can produce less intelligible failures             |
| `display`, `print_changed_only` | Estimator representation                           | Affects inspection rather than numerical execution |

Validation can be a material part of small repeated computations, but disabling it globally changes the reliability boundary. The normal estimator API does not become an unchecked computational kernel merely because validation is disabled.

Reference:

[https://scikit-learn.org/stable/modules/generated/sklearn.set_config.html](https://scikit-learn.org/stable/modules/generated/sklearn.set_config.html?utm_source=chatgpt.com)

### 12.4 Computational design implications

Scikit-learn already contains multiple mechanisms that can reduce custom performance engineering:

- Reuse of optimized NumPy/SciPy and compiled algorithm implementations.
- Fold- and candidate-level parallel execution.
- Memory-mapped sharing for suitable multiprocessing workloads.
- Caching of intermediate transformers.
- Incremental algorithms and mini-batching.
- Sparse representations and sparse-compatible solvers.
- Approximate transformations and randomized decomposition.
- Selective Array API dispatch to accelerator-backed numerical arrays.

The optimal combination remains workload-dependent. Higher parallelism, approximate methods, GPU execution, and caching can each introduce additional overhead or change numerical behavior. No one mechanism makes the whole estimator framework uniformly faster.

References:

[https://scikit-learn.org/stable/computing/parallelism.html](https://scikit-learn.org/stable/computing/parallelism.html?utm_source=chatgpt.com)

[https://scikit-learn.org/stable/computing/computational_performance.html](https://scikit-learn.org/stable/computing/computational_performance.html?utm_source=chatgpt.com)

## 13. Model persistence, serialization, and deployment boundaries

Scikit-learn does not prescribe a single model artifact format. Instead, model persistence depends on whether an application needs to recover a Python estimator, execute predictions outside Python, or safely inspect an artifact before loading it.

### 13.1 Persistence mechanisms

| Mechanism     | Provided by                               | Principal value                                                              | Main limitation                                                            |
| ------------- | ----------------------------------------- | ---------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `pickle`      | Python standard library                   | General Python object serialization                                          | Untrusted files can execute arbitrary code                                 |
| `joblib`      | Separate dependency, used by scikit-learn | Compression, efficient handling and memory mapping of large numerical arrays | Pickle-based security risks                                                |
| `cloudpickle` | Separate package                          | Serialization of certain dynamically defined Python objects                  | Pickle-based; weak portability and compatibility guarantees                |
| `skops.io`    | Separate `skops` package                  | Restricted loading with explicit inspection of unknown types                 | More limited type support; still requires trust decisions                  |
| ONNX          | Separate `skl2onnx` converter and runtime | Portable inference graph executable outside scikit-learn                     | Conversion coverage is incomplete; original estimator is not reconstructed |

The difference between persistence and interoperability is fundamental.

A pickle-based artifact preserves the Python object graph, but depends on compatible Python packages and trusted loading conditions.

An ONNX artifact represents a separate computational graph whose operators can be executed by ONNX-compatible runtimes. Conversion of a pipeline requires converters for its constituent operations and may introduce numerical differences, such as floating-point precision changes or differences in preprocessing behavior.

`skl2onnx` supports many common scikit-learn estimators, including complex pipelines, but neither scikit-learn nor the converter guarantees coverage for every custom transformer or estimator.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+2



### 13.2 Cross-version compatibility

Scikit-learn explicitly does not support loading estimator artifacts trained with a different scikit-learn version.

An artifact may happen to deserialize across versions, but that is not an API guarantee. Internal fitted attributes, numerical behavior, and dependency assumptions may change.

The persistence guide therefore recommends preserving relevant environment, package-version, and training information alongside an artifact. A durable model record also benefits from retaining feature schema, preprocessing semantics, and validation evidence, because serialization alone does not establish those contracts.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



References:

[https://scikit-learn.org/stable/model_persistence.html](https://scikit-learn.org/stable/model_persistence.html?utm_source=chatgpt.com)

[https://onnx.ai/sklearn-onnx/](https://onnx.ai/sklearn-onnx/?utm_source=chatgpt.com)

[https://onnx.ai/sklearn-onnx/supported.html](https://onnx.ai/sklearn-onnx/supported.html?utm_source=chatgpt.com)

## 14. Dataset generation, testing, and developer instrumentation

### 14.1 Dataset utilities

`sklearn.datasets` contains several capabilities beyond the familiar bundled examples.

| Capability                  | Representative APIs                                                          | Purpose                                                           |
| --------------------------- | ---------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Small reference datasets    | `load_iris`, `load_digits`, `load_diabetes`, `load_wine`                     | Reproducible algorithm exercises and regression tests             |
| External reference datasets | `fetch_openml`, `fetch_20newsgroups`, other fetchers                         | Retrieval of published benchmark datasets                         |
| Synthetic classification    | `make_classification`, `make_blobs`, `make_circles`, `make_moons`            | Controlled class structures and difficulty                        |
| Synthetic regression        | `make_regression`, `make_friedman1/2/3`                                      | Known generating relationships and noise                          |
| Structural numerical data   | `make_low_rank_matrix`, `make_sparse_spd_matrix`, `make_sparse_coded_signal` | Testing decomposition, sparse recovery, and covariance algorithms |
| Manifold datasets           | `make_s_curve`, `make_swiss_roll`                                            | Testing nonlinear embedding and geometric methods                 |
| Sparse interchange          | `load_svmlight_file`, `dump_svmlight_file`                                   | Exchange of sparse labeled feature data                           |

Synthetic generators are particularly useful for isolated testing of numerical and statistical properties. They allow controlled changes in feature dimensionality, informative-feature fraction, covariance structure, label noise, and class imbalance.

These are test and dataset utilities rather than a general synthetic-data framework with complete domain semantics or database integration.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Reference:

[https://scikit-learn.org/stable/datasets.html](https://scikit-learn.org/stable/datasets.html?utm_source=chatgpt.com)

### 14.2 Estimator validation and introspection

The developer tooling supports automated checks of the estimator protocol.

Important utilities include:

- `check_estimator()` for checking expected estimator behaviors.
- `parametrize_with_checks()` and `estimator_checks_generator()` for incorporating framework compatibility checks into external test suites.
- `get_tags()` for structured inspection of estimator capabilities.
- `validate_data()`, `check_array()`, and `check_is_fitted()` for consistent validation and lifecycle checks.
- `all_estimators()` for discovering estimator classes.
- `estimator_html_repr()` and notebook displays for structural inspection.

The estimator checks cover different expectations depending on declared capabilities. They can expose inconsistencies in cloning, fitted-state handling, input validation, sparse support, and estimator behavior.

For Array API-capable custom estimators, the `array_api_support` tag enables additional tests. The documentation uses `array-api-strict` to test namespace and device assumptions even without an actual accelerator; testing on real hardware remains necessary for full device-specific coverage.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



These checks provide a substantial alternative to implementing every estimator-interface test from scratch. They are not, however, substitutes for algorithm-specific numerical accuracy, statistical correctness, or performance tests.

Reference:

[https://scikit-learn.org/stable/developers/develop.html](https://scikit-learn.org/stable/developers/develop.html?utm_source=chatgpt.com)

## 15. Ecosystem integrations and responsibilities

The usefulness of scikit-learn's estimator abstraction extends into related packages. Those packages should be understood as compatible components rather than capabilities necessarily implemented by scikit-learn itself.

| Integration                      | Responsibility and relationship                                                                                            |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| NumPy/SciPy                      | Numerical arrays, sparse structures, optimization, and low-level mathematics underlying scikit-learn                       |
| pandas/Polars                    | Dataframe input/output, column naming, and feature-data preparation                                                        |
| joblib/threadpoolctl             | Task parallelism, shared memory, caching, and native thread-pool management                                                |
| PyTorch/CuPy/dpnp                | Experimental Array API-backed numerical execution for supported operations                                                 |
| `imbalanced-learn`               | Resampling algorithms and an estimator-compatible pipeline that incorporates sampling steps                                |
| `skl2onnx`/ONNX Runtime          | Conversion and inference execution outside scikit-learn                                                                    |
| `skops`                          | Model persistence with inspection-oriented loading controls                                                                |
| XGBoost/LightGBM/CatBoost        | External optimized boosting engines that provide scikit-learn-compatible APIs                                              |
| External optimization frameworks | Additional hyperparameter search algorithms that can use scikit-learn estimators and scoring                               |
| Distributed-computing frameworks | External execution, dataset partitioning, scheduling, or parallel search; not intrinsic to the ordinary estimator protocol |

### 15.1 Important integration distinctions

Resampling is not ordinary transformation. `imbalanced-learn` supplies samplers and a specialized pipeline for operations such as oversampling or undersampling within training workflows. Resampling can change the number of observations and therefore has different semantics from scikit-learn transformers that preserve sample correspondence.

Using resampling outside the appropriate training folds can cause leakage. The sampling-aware pipeline helps incorporate these operations into validation correctly.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://imbalanced-learn.org\&sz=32)

Version 0.14.2



Estimator compatibility is not algorithm identity. External boosting packages can expose `fit`, `predict`, and parameter APIs compatible with scikit-learn, while retaining their own execution engines, serialization formats, hardware capabilities, and optimization behavior.

Array interoperability is not deep-learning integration. Passing supported PyTorch tensors to scikit-learn does not make arbitrary scikit-learn estimators differentiable through PyTorch autograd, nor does it convert scikit-learn into a neural-network training framework.

Native pipelines are not arbitrary computational DAGs. `Pipeline`, `ColumnTransformer`, and `FeatureUnion` model specific sequential and parallel feature operations. They do not natively provide SQL optimization, relational joins, distributed scheduling, or arbitrary control-flow graphs.

Model persistence is not model operations. Artifact registries, deployment orchestration, serving APIs, drift monitoring, and production experiment tracking are separate responsibilities.

These distinctions define where scikit-learn can meaningfully replace custom code and where external systems remain appropriate.

## 16. Version 1.9-specific developments and compatibility considerations

The following consolidates the most consequential changes for the target version, separating released enhancements from experimental and deprecated behavior.

### 16.1 Notable released changes

\| Area | Change in 1.9 | Significance |\
\|---|---|---|\
\| Sparse interoperability | `sparse_interface="spmatrix"|"sparray"` | Explicit transition path to SciPy sparse arrays |\
\| Dataframe support | Adoption of Narwhals as a dependency | Common interoperability mechanisms for supported dataframe inputs/outputs |\
\| Estimator inspection | HTML display of fitted attributes and composite output features | Easier introspection of learned state and feature-schema changes |\
\| Numerical backends | Additional Array API-compatible estimators and metrics | Broader selective CPU/GPU interoperability |\
\| Linear models | Sparse inputs and sample weights for multitask Lasso/ElasticNet | More flexible high-dimensional multioutput learning |\
\| Tree models | Expanded missing-value and monotonic-constraint combinations | Less dependence on external imputation in supported cases |\
\| Threshold metrics | `metric_at_thresholds` | Native evaluation of metrics across operating thresholds |\
\| Metadata routing | Expanded coverage and bug fixes | More reliable composition of weighted and group-aware operations |

Version 1.9.1 in particular corrects metadata being silently dropped through certain feature-selection and imputation meta-estimators, as well as issues affecting `Pipeline.transform_input`, bagging metadata propagation, and callback serialization during multiprocessing. These are correctness changes that can affect composite workflows without requiring new public APIs.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+2



### 16.2 Experimental interfaces in 1.9.1

| Feature                      | Status                                   | Consequence                                              |
| ---------------------------- | ---------------------------------------- | -------------------------------------------------------- |
| Metadata routing             | Experimental; opt-in                     | API and coverage may change                              |
| Array API dispatch           | Experimental; opt-in                     | Backend/device support is selective                      |
| Callbacks                    | Experimental; limited estimator coverage | Interface may change without standard deprecation        |
| `IterativeImputer`           | Experimental; explicit enable import     | Availability and interface are not yet considered stable |
| Successive-halving CV search | Experimental; explicit enable import     | Search interface may change without standard deprecation |

An experimental capability can be useful and functional, but it should not be described as offering the same compatibility guarantees as established estimator APIs.

### 16.3 Material deprecations and transition points

The 1.9 release notes identify several API changes requiring attention:

- `SVC(probability=...)` and `NuSVC(probability=...)` are deprecated, with removal planned for 1.11. The documented alternative is `CalibratedClassifierCV` with `ensemble=False`. Associated `probA_` and `probB_` attributes are also deprecated.
- `TargetEncoder`'s `shuffle` and `random_state` parameters are deprecated in favor of specifying a cross-validation generator through `cv`, with removal planned for 1.11.
- The `friedman_mse` splitting criterion in several ordinary tree and forest estimators is deprecated because it behaved like `squared_error` in those implementations.
- The `n_alphas` transition for regularization-path APIs continues in favor of a unified `alphas` parameter.

These are deprecations, not claims that the interfaces have already been removed in 1.9.1.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Reference:

[https://scikit-learn.org/stable/whats_new/v1.9.html](https://scikit-learn.org/stable/whats_new/v1.9.html?utm_source=chatgpt.com)

## 17. Architectural synthesis: where scikit-learn provides the greatest leverage

The most consequential architectural feature of scikit-learn is the way its capabilities compose.

Consider a general workflow with heterogeneous input features, group-aware validation, a nonlinear model, probability calibration, and a decision-specific threshold.

A collection of compatible scikit-learn components can express the following structure:

Structured feature inputs

NumPy / sparse / supported DataFrame

Feature composition

`ColumnTransformer` + `Pipeline`

Imputation, encoding, scaling, selection

Model and statistical evaluation

Compatible estimator + group-aware CV + hyperparameter search

Estimator cloning, fitting, scoring, metadata routing

Post-fit prediction behavior

Calibration + decision-threshold selection

Separate probability estimation from decision policy

Prediction and inspection

Scoring, feature attribution, persistence

Parameter introspection

Estimator tags

Callback monitoring

Execution controls

Conceptual composition of compatible mechanisms; not a claim that every estimator supports every capability.

This illustrates several native combinations with unusually high leverage.

First, preprocessing becomes part of statistical estimation. Composed estimators and CV eliminate much of the need for custom, leakage-sensitive fit/transform orchestration.

Second, model evaluation becomes a reusable policy layer. The same estimator can be evaluated with different splitters, metrics, sampling weights, parameter budgets, and candidate-selection rules.

Third, estimator metadata and introspection create a common integration surface. External algorithms can participate in parameter search, validation, feature processing, and inspection without each application implementing its own machinery.

Fourth, numerical execution can be varied independently of much of the higher-level model interface. Dense versus sparse data, batch versus incremental estimators, exact versus approximate representations, and selected CPU/GPU array backends offer different computational pathways.

Fifth, statistical modeling and decision making remain distinct. Calibration, threshold tuning, and post-fit evaluation permit refinement of output behavior without assuming every downstream objective requires retraining the base model.

The main limits are equally important: scikit-learn is not a general relational engine, not a distributed-computing platform, not a universal accelerator framework, and not a complete model-serving or model-governance system. Its primary role is composable statistical and machine-learning computation within a consistent estimator ecosystem.

### Primary-source navigation

For subsequent deeper investigation, these are the most valuable general entry points:

| Topic                                       | Direct source URL                                                                                                                                             |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Stable user guide                           | [https://scikit-learn.org/stable/user_guide.html](https://scikit-learn.org/stable/user_guide.html?utm_source=chatgpt.com)                                     |
| Full API reference                          | [https://scikit-learn.org/stable/api/index.html](https://scikit-learn.org/stable/api/index.html?utm_source=chatgpt.com)                                       |
| Developer and custom-estimator API          | [https://scikit-learn.org/stable/developers/develop.html](https://scikit-learn.org/stable/developers/develop.html?utm_source=chatgpt.com)                     |
| Estimator composition                       | [https://scikit-learn.org/stable/modules/compose.html](https://scikit-learn.org/stable/modules/compose.html?utm_source=chatgpt.com)                           |
| Metadata routing                            | [https://scikit-learn.org/stable/metadata_routing.html](https://scikit-learn.org/stable/metadata_routing.html?utm_source=chatgpt.com)                         |
| Cross-validation                            | [https://scikit-learn.org/stable/modules/cross_validation.html](https://scikit-learn.org/stable/modules/cross_validation.html?utm_source=chatgpt.com)         |
| Hyperparameter search                       | [https://scikit-learn.org/stable/modules/grid_search.html](https://scikit-learn.org/stable/modules/grid_search.html?utm_source=chatgpt.com)                   |
| Metrics and evaluation                      | [https://scikit-learn.org/stable/modules/model_evaluation.html](https://scikit-learn.org/stable/modules/model_evaluation.html?utm_source=chatgpt.com)         |
| Model inspection                            | [https://scikit-learn.org/stable/inspection.html](https://scikit-learn.org/stable/inspection.html?utm_source=chatgpt.com)                                     |
| Callback framework                          | [https://scikit-learn.org/stable/callbacks.html](https://scikit-learn.org/stable/callbacks.html?utm_source=chatgpt.com)                                       |
| Array API interoperability                  | [https://scikit-learn.org/stable/modules/array_api.html](https://scikit-learn.org/stable/modules/array_api.html?utm_source=chatgpt.com)                       |
| DataFrame and feature-name interoperability | [https://scikit-learn.org/stable/modules/df_output_transform.html](https://scikit-learn.org/stable/modules/df_output_transform.html?utm_source=chatgpt.com)   |
| Out-of-core computation                     | [https://scikit-learn.org/stable/computing/scaling_strategies.html](https://scikit-learn.org/stable/computing/scaling_strategies.html?utm_source=chatgpt.com) |
| Parallel execution                          | [https://scikit-learn.org/stable/computing/parallelism.html](https://scikit-learn.org/stable/computing/parallelism.html?utm_source=chatgpt.com)               |
| Model persistence                           | [https://scikit-learn.org/stable/model_persistence.html](https://scikit-learn.org/stable/model_persistence.html?utm_source=chatgpt.com)                       |
| Common pitfalls and leakage                 | [https://scikit-learn.org/stable/common_pitfalls.html](https://scikit-learn.org/stable/common_pitfalls.html?utm_source=chatgpt.com)                           |
| Version 1.9 release history                 | [https://scikit-learn.org/stable/whats_new/v1.9.html](https://scikit-learn.org/stable/whats_new/v1.9.html?utm_source=chatgpt.com)                             |

Overall: Scikit-learn's greatest value is not any one model family. It is the shared architecture joining statistical models, trainable transformations, meta-estimators, selection procedures, metrics, numerical execution, and inspection. For advanced engineering systems, understanding these interactions is the key to using the library's full capabilities while minimizing unnecessary custom machine-learning infrastructure.

# Scikit-learn 1.9.1 — Advanced Capabilities Addendum

Research date: November 5, 2026\
Target version: scikit-learn 1.9.1\
Companion document: Scikit-learn 1.9.1 — Comprehensive Python Library Capability Overview

## Scope and orientation

This addendum supplements the existing capability overview with functionality that was absent or insufficiently developed. It focuses on additional mathematical modeling families, structural representations, reusable computational primitives, estimator extension mechanisms, and version-sensitive numerical behavior.

The principal additions are:

| Capability area                    | Additional functionality                                                                                                |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Supervised representation learning | Neighborhood Components Analysis, kernel ridge regression, supervised multiview decomposition                           |
| Sparse modeling                    | Orthogonal Matching Pursuit, Least Angle Regression, information-criterion selection                                    |
| Graph and dependency analysis      | Reusable nearest-neighbor graphs, sparse precision estimation, multiresolution density clustering                       |
| Nonlinear feature construction     | RandomTreesEmbedding, PolynomialCountSketch, additional kernel-composition mechanisms                                   |
| Statistical evaluation             | Analytical leave-one-out validation, mutual-information selection, embedding trustworthiness, baseline models           |
| Framework extension                | Custom cloning, frozen estimators, conditional estimator methods, custom metadata routers                               |
| Specialized estimators             | AdaBoost, nearest-centroid classification, restricted Boltzmann machines, passive-aggressive learning                   |
| Release-specific behavior          | Changes affecting sampling, weighting, numerical solutions, optimization, and compatibility in versions 1.9.0 and 1.9.1 |

Unless explicitly marked otherwise, the capabilities described below are available in scikit-learn 1.9.1. Their inclusion does not imply that they were introduced in the 1.9 series.

## 1. Supervised representation learning and reusable neighborhood infrastructure

### 1.1 Neighborhood Components Analysis: learning task-dependent similarity

`sklearn.neighbors.NeighborhoodComponentsAnalysis` (NCA) learns a linear transformation of feature space that directly optimizes a stochastic nearest-neighbor classification objective.

Ordinary nearest-neighbor classification depends on a distance metric chosen independently of the classification task. NCA instead uses class labels to learn a transformation under which points sharing a label are more likely to become neighbors.

Let \\(L\in\mathbb{R}^{d\times p}\\) be a learned transformation from \\(p\\) original features into \\(d\\) dimensions. The squared Euclidean distance after transformation is

\\[ d_L(x_i,x_j)^2 =\\|L(x_i-x_j)\\|\_2^2 =(x_i-x_j)^TL^TL(x_i-x_j). \\]

Consequently, NCA implicitly learns a positive semidefinite Mahalanobis metric \\(M=L^TL\\).

The algorithm assigns a stochastic neighbor-selection probability

\\[ p\_{ij}= \frac{\exp(-\\|Lx_i-Lx_j\\|\_2^2)} {\sum\_{k\ne i}\exp(-\\|Lx_i-Lx_k\\|\_2^2)}, \qquad p\_{ii}=0. \\]

If \\(C_i\\) is the set of other training observations sharing the class label of observation \\(i\\), the learning objective is

\\[ \max_L\sum_i\sum\_{j\in C_i}p\_{ij}. \\]

This maximizes a stochastic approximation to leave-one-out nearest-neighbor classification accuracy rather than explained variance, reconstruction accuracy, or preservation of the original geometry.

#### Distinctive capabilities

NCA offers supervised metric learning and supervised dimensionality reduction through the same estimator.

When `n_components` is smaller than the original feature count, the estimator learns a lower-dimensional representation while optimizing its usefulness for class discrimination. The fitted `transform()` method then applies the learned mapping to new observations.

The transformation can be composed with `KNeighborsClassifier` or another compatible estimator in a pipeline. Such a composition allows model selection to consider the representation dimensionality, NCA optimization settings, and downstream classifier configuration together.

Unlike `PCA`, NCA does not attempt to preserve maximum variance. Unlike `LinearDiscriminantAnalysis`, it does not derive its representation from the conventional within-class and between-class scatter criterion or require a Gaussian class-distribution model.

It also differs from unsupervised manifold embedding: the learned mapping is a reusable linear transformation, not merely an embedding of the original training observations.

#### Optimization and limitations

Scikit-learn uses L-BFGS-B with full gradients to optimize the NCA objective. The optimization is nonconvex, so initialization and local solutions matter.

The implementation stores pairwise distances with quadratic memory complexity in the number of training samples. Its documentation gives a per-iteration time complexity of

\\[ O\left(d\\,n\\,\min(n,p)\right), \\]

where \\(n\\) is the sample count, \\(p\\) the feature count, and \\(d\\) the output dimensionality. Overall fitting time also depends on the number of optimization iterations.

NCA is therefore a potentially valuable supervised metric learner for moderate-sized datasets, but not a general replacement for scalable approximate-neighbor infrastructure. Its learned distances should also not be interpreted as causal or universally meaningful measures of similarity.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Primary source: [https://scikit-learn.org/1.9/modules/neighbors.html#neighborhood-components-analysis](https://scikit-learn.org/1.9/modules/neighbors.html?utm_source=chatgpt.com#neighborhood-components-analysis)

### 1.2 Nearest-neighbor graphs as separately computed, reusable representations

Scikit-learn provides two estimator-compatible graph transformers that are distinct from its nearest-neighbor prediction models:

- `KNeighborsTransformer`
- `RadiusNeighborsTransformer`

These components produce sparse neighborhood graphs using either a fixed neighbor count or a distance radius.

The key capability is the separation of neighborhood construction from algorithms consuming neighborhood relationships.

Neighbor graphs can serve as inputs to compatible clustering, manifold-learning, and neighbor-based prediction algorithms. Their construction need not be repeated inside every downstream estimator.

For example, a pipeline can produce a sparse distance graph with `KNeighborsTransformer(mode="distance")` and pass that graph to `Isomap(metric="precomputed")`.

This enables several architectural options.

Reusable computation. An expensive neighborhood graph may be computed once and reused across compatible downstream configurations. Pipeline caching can avoid recomputing the graph when downstream hyperparameters change without changing the graph-construction step.

Interchangeable search strategies. Neighborhood construction can use exact nearest-neighbor algorithms or an appropriately wrapped external approximate-nearest-neighbor implementation. The downstream estimator can remain unchanged if the supplied graph satisfies its interface contract.

Independent resource control. Graph construction can expose neighbor-search parallelism, distance metrics, and indexing configuration that may not be directly available through the downstream consumer.

Sparse graph interchange. Instead of materializing an \\(n\times n\\) dense distance matrix, suitable algorithms can consume sparse connectivity or distance matrices containing only retained neighborhood edges.

#### Graph representation requirements

The sparse representation has nontrivial semantics.

A neighborhood graph may encode connectivity or distances. Those interpretations are not interchangeable. For example, a spectral algorithm expecting affinities cannot generally interpret a sparse distance graph as its affinity matrix without an appropriate transformation.

For precomputed nearest-neighbor distance graphs, the upstream documentation specifies:

| Requirement                         | Significance                                                                              |
| ----------------------------------- | ----------------------------------------------------------------------------------------- |
| CSR representation preferred        | Efficient sparse row access; other supported SciPy sparse formats may be accepted         |
| Explicit zero-distance neighbors    | Sparse absence must not be confused with a valid zero distance                            |
| Self-neighbor handling              | Training-to-training graphs may require an explicitly represented diagonal                |
| Nonnegative distance entries        | Negative values violate the neighbor-distance contract                                    |
| No duplicate column indices per row | Duplicate sparse entries can introduce incorrect neighbor semantics                       |
| Sufficient neighbors per row        | A downstream \\(k\\)-nearest-neighbor consumer needs at least the required neighbor count |
| Sorted distances within rows        | Optional for correctness where supported, but unsorted rows may require extra sorting     |

The last requirements are particularly important when connecting externally generated approximate-neighbor graphs to scikit-learn. Successful sparse-matrix conversion does not by itself establish semantic compatibility.

A precomputed graph also represents relationships to a particular reference set. When evaluating new observations or using cross-validation, the graph must preserve the correct query-to-training correspondence and prevent validation observations from influencing training-only graph construction where that would cause leakage.

#### Interaction with structural-learning algorithms

The same graph-construction abstraction can underpin multiple analytical stages:

\\[ X \xrightarrow{\text{neighbor search}} G\_{\mathrm{sparse}} \xrightarrow{\text{compatible estimator}} Z. \\]

Here \\(Z\\) might represent cluster assignments, manifold coordinates, or predicted labels.

The opportunity is not simply faster neighbor search. It is the possibility of treating an expensive spatial or semantic relationship structure as an explicit intermediate representation, with independent construction, reuse, inspection, and downstream processing.

Whether the graph can actually be shared depends on each consumer's required distance semantics, neighbor count, graph format, and fitted-state lifecycle.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Primary source: [https://scikit-learn.org/1.9/modules/neighbors.html#nearest-neighbors-transformer](https://scikit-learn.org/1.9/modules/neighbors.html?utm_source=chatgpt.com#nearest-neighbors-transformer)

## 2. Additional supervised modeling and latent-variable methods

### 2.1 Kernel ridge regression: regularized nonlinear regression without an explicit feature expansion

`sklearn.kernel_ridge.KernelRidge` combines ridge regression with kernel-based representations.

Instead of constructing a finite-dimensional nonlinear feature expansion, kernel ridge regression represents predictions using similarities between observations and the fitted training set.

For a positive semidefinite kernel matrix \\(K\\), a standard dual formulation is

\\[ \hat{\alpha}=(K+\lambda I)^{-1}y, \\]

with predictions

\\[ \hat{f}(x)=\sum\_{i=1}^{n}\hat{\alpha}\_i\\,k(x,x_i). \\]

The regularization parameter \\(\lambda\\) controls the tradeoff between data fit and model complexity.

The estimator accepts kernels available through scikit-learn's pairwise-kernel infrastructure, as well as callable and precomputed kernels. It supports multiple regression targets and sample weighting.

#### Distinction from related kernel estimators

| Estimator                  | Training principle                                     | Consequential distinction                                                |
| -------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------ |
| `KernelRidge`              | Regularized squared-error minimization in kernel space | Closed-form solution for fixed kernel and regularization                 |
| `SVR`                      | Epsilon-insensitive optimization                       | Can produce a sparse support-vector representation                       |
| `GaussianProcessRegressor` | Probabilistic inference with kernel-defined covariance | Predictive uncertainty and marginal-likelihood-based kernel optimization |

Kernel ridge regression's solution is generally dense: prediction depends on kernel evaluations against the retained training observations. Consequently, fitting can be efficient for moderate datasets while prediction can be more expensive than that of a sparse SVR.

Exact kernel ridge regression also requires storing and solving systems involving the kernel matrix, giving it the familiar quadratic storage and potentially cubic factorization costs of dense kernel methods.

The estimator's major architectural value is that it supports nonlinear regression without a separately implemented nonlinear model, provided an appropriate positive semidefinite kernel is available.

For larger datasets, a relevant alternative is to combine an explicit kernel approximation, such as `Nystroem` or `RBFSampler`, with ordinary ridge regression. This changes the computation from an exact sample-space kernel solution to a finite-dimensional approximate feature-space solution. The two approaches are not numerically equivalent, but they can represent related modeling objectives with different scaling properties.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+1



Primary source: [https://scikit-learn.org/1.9/modules/kernel_ridge.html](https://scikit-learn.org/1.9/modules/kernel_ridge.html?utm_source=chatgpt.com)

### 2.2 Orthogonal Matching Pursuit: direct sparse approximation

`OrthogonalMatchingPursuit`, `OrthogonalMatchingPursuitCV`, `orthogonal_mp`, and `orthogonal_mp_gram` provide greedy sparse approximation.

The central problem is to fit a linear model using only a limited number of nonzero coefficients:

\\[ \min_w\\|y-Xw\\|\_2^2 \quad\text{subject to}\quad \\|w\\|\_0\leq k. \\]

Alternatively, OMP can seek a sparse approximation satisfying a specified reconstruction-error tolerance.

Unlike Lasso, which relaxes sparsity through an L1 penalty, OMP greedily selects predictors or dictionary atoms according to their relationship with the current residual.

After selecting an atom, the algorithm recomputes coefficients over the active set using an orthogonal projection. This distinguishes OMP from ordinary matching pursuit, which does not perform the same full residual orthogonalization.

#### Consequential capabilities

The algorithm directly addresses fixed-sparsity representation problems. This may be preferable when the number of active variables is itself a meaningful constraint rather than a property emerging indirectly from an L1 penalty.

The low-level `orthogonal_mp_gram` function permits computation from a Gram matrix and the relevant inner products. Such a representation can be useful when multiple sparse recovery problems share the same dictionary, because some matrix products can be reused.

`OrthogonalMatchingPursuitCV` selects the number of nonzero coefficients through cross-validation.

OMP is a greedy approximation, not a general exact solution to the combinatorial L0 optimization problem. Highly correlated predictors, poorly conditioned active sets, and noise can affect the atoms selected. The resulting feature set is not necessarily stable across perturbations of the data.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Primary source: [https://scikit-learn.org/1.9/modules/linear_model.html#orthogonal-matching-pursuit-omp](https://scikit-learn.org/1.9/modules/linear_model.html?utm_source=chatgpt.com#orthogonal-matching-pursuit-omp)

### 2.3 Least Angle Regression and regularization-path computation

The Least Angle Regression family provides methods for constructing coefficient paths as model complexity changes.

Relevant interfaces include `Lars`, `LarsCV`, `LassoLars`, `LassoLarsCV`, `LassoLarsIC`, and the lower-level `lars_path` and `lars_path_gram` functions.

LARS constructs a piecewise-linear path by progressively incorporating predictors into an active set. The Lasso-LARS variant modifies this procedure to follow the Lasso solution path, including handling coefficients that leave the active set.

This differs from repeatedly solving independent regression problems at a grid of regularization strengths.

A particularly useful option is `LassoLarsIC`, which selects regularization using an information criterion:

\\[ \mathrm{AIC}=-2\log\hat{\mathcal L}+2\\,\mathrm{df}, \\]

\\[ \mathrm{BIC}=-2\log\hat{\mathcal L} +\log(n)\\,\mathrm{df}. \\]

Here \\(\mathrm{df}\\) denotes the effective model complexity under the estimator's assumptions.

AIC and BIC selection can avoid the computational expense of cross-validation, but rely on statistical assumptions about the likelihood, noise, and effective degrees of freedom. Information-criterion selection and predictive cross-validation should therefore not be treated as interchangeable.

The distinction between LARS-based and coordinate-descent-based Lasso implementations also matters computationally. LARS is potentially attractive when the solution is very sparse and the number of observations is comparatively small. Coordinate descent is often preferable in other regimes, especially when a specific subset of regularization strengths is sufficient.

Gram-matrix-based path APIs create a further opportunity to reuse cross-products when repeated sparse models share a common design matrix.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+1



Primary source: [https://scikit-learn.org/1.9/modules/linear_model.html#least-angle-regression](https://scikit-learn.org/1.9/modules/linear_model.html?utm_source=chatgpt.com#least-angle-regression)

### 2.4 Multiview decomposition: relationships between two feature spaces

The `sklearn.cross_decomposition` subsystem is more than another collection of linear regressors.

Its estimators extract relationships between paired matrices \\(X\\) and \\(Y\\), seeking low-dimensional representations that capture shared statistical structure.

This is distinct from PCA, whose principal components depend only on the variance structure of a single matrix.

| Estimator       | Primary mechanism                                                                            | Important distinction                                                    |
| --------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `PLSRegression` | Constructs latent components useful for predicting one or more target variables              | Directly combines dimension reduction with multivariate regression       |
| `PLSCanonical`  | Iteratively finds paired latent scores with high cross-covariance and deflates both matrices | Symmetric treatment of the two variable spaces                           |
| `CCA`           | Finds projections whose paired scores exhibit high correlation                               | Correlation-normalized objective rather than raw covariance maximization |
| `PLSSVD`        | Performs a truncated SVD of the cross-covariance matrix                                      | Computes coupled directions without sequential deflation                 |

For centered matrices, the cross-covariance structure is represented by

\\[ C=X^TY, \\]

up to normalization by sample count.

A singular-value decomposition

\\[ C=U\Sigma V^T \\]

reveals paired directions in the two feature spaces that explain their strongest linear cross-covariance relationships.

`PLSSVD` uses this decomposition directly. `PLSCanonical` extracts components iteratively, with deflation modifying the residual matrices after each component.

`CCA` instead uses variance-normalized cross-relationships, addressing a different objective.

These methods support supervised or paired-view representation learning, including problems involving two measurement systems, coupled feature families, or multivariate output spaces.

They are particularly worth distinguishing from PCA when directions with small variance in \\(X\\) may nevertheless have a strong relationship with \\(Y\\).

#### Interpretation and limitations

A high cross-covariance or canonical correlation does not establish causality, nor does it necessarily demonstrate that the shared latent representation will generalize.

Feature scaling can materially change the result, especially for covariance-oriented methods. Classical CCA can also become unstable when covariance matrices are poorly conditioned, such as in high-dimensional, low-sample regimes.

The estimators expose fitted weights, loadings, rotations, scores, and, where supported, regression coefficients. These provide access to more structural information than final predictions alone.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Primary source: [https://scikit-learn.org/1.9/modules/cross_decomposition.html](https://scikit-learn.org/1.9/modules/cross_decomposition.html?utm_source=chatgpt.com)

### 2.5 Gaussian-process kernel composition as a model-construction mechanism

The Gaussian-process discussion in the original guide notes kernel composition but does not fully describe how native kernel objects encode prior assumptions about function structure.

Scikit-learn provides a composable kernel algebra in which covariance functions are combined through addition, multiplication, and exponentiation.

For kernels \\(k_1\\) and \\(k_2\\), additions and products form kernels of the type

\\[ k\_{\mathrm{sum}}(x,x')=k_1(x,x')+k_2(x,x'), \\]

\\[ k\_{\mathrm{product}}(x,x')=k_1(x,x')\\,k_2(x,x'). \\]

These operations provide a native mechanism for specifying composite covariance structures.

| Kernel              | Structural assumption                                          |
| ------------------- | -------------------------------------------------------------- |
| `RBF`               | Very smooth functions with characteristic length scales        |
| `Matern`            | Functions with configurable smoothness controlled by \\(\nu\\) |
| `RationalQuadratic` | An effective mixture of RBF kernels at different length scales |
| `ExpSineSquared`    | Periodic relationships                                         |
| `DotProduct`        | Linear or affine covariance structure                          |
| `ConstantKernel`    | Constant covariance contributions or multiplicative scaling    |
| `WhiteKernel`       | An independently varying noise component                       |

For example, adding an RBF component to a periodic component can represent covariance arising from both nonperiodic and periodic variation. Multiplication allows covariance to depend jointly on different structural properties.

This is a model-specification capability, not merely an implementation detail of Gaussian-process fitting.

#### Kernel hyperparameters and data noise

The kernel API exposes hyperparameter bounds and gradients used during marginal-likelihood optimization. Kernel objects can therefore encapsulate both a covariance function and the parameters that may be optimized during fitting.

A useful distinction is between `GaussianProcessRegressor(alpha=...)` and including `WhiteKernel` in the kernel expression.

`alpha` supplies an explicitly specified diagonal contribution to the training covariance matrix, either globally or observation by observation. It can represent known measurement noise and improve numerical conditioning.

`WhiteKernel` instead includes an optimizable noise-level parameter within the kernel itself.

The two mechanisms are related but not identical. Their parameterization, fitted-state behavior, and interpretation differ.

Scikit-learn's Gaussian-process kernels also support anisotropic length scales in selected kernels, enabling separate sensitivity to different input dimensions.

These mechanisms provide relatively expressive structured probabilistic regression without implementing custom covariance operators. They remain subject to the computational limitations of exact Gaussian-process inference and to the suitability of the assumed kernel family.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+1



Primary source: [https://scikit-learn.org/1.9/modules/gaussian_process.html](https://scikit-learn.org/1.9/modules/gaussian_process.html?utm_source=chatgpt.com)

## 3. Graph structure, conditional dependence, and reusable clustering representations

### 3.1 Graphical Lasso: sparse conditional-dependency discovery

`GraphicalLasso`, `GraphicalLassoCV`, and `graphical_lasso()` estimate sparse inverse-covariance matrices.

The importance of this capability is that an inverse-covariance matrix can encode a conditional-dependency graph, rather than merely summarize pairwise correlations.

Let \\(\Sigma\\) denote a covariance matrix and

\\[ \Theta=\Sigma^{-1} \\]

its precision matrix.

For a multivariate Gaussian distribution, an off-diagonal entry \\(\Theta\_{ij}=0\\) corresponds to conditional independence between variables \\(i\\) and \\(j\\), given the other variables.

Graphical Lasso estimates \\(\Theta\\) using an L1-penalized Gaussian log-likelihood:

\\[ \hat{\Theta} = \arg\min\_{\Theta\succ0} \left[ \operatorname{tr}(S\Theta) -\log\det\Theta +\alpha\sum\_{i\ne j}|\Theta\_{ij}| \right], \\]

where \\(S\\) is the empirical covariance matrix.

The penalty encourages zero off-diagonal entries. Consequently, the resulting precision matrix can be interpreted as the weighted adjacency structure of an estimated Gaussian conditional-dependency graph.

#### Distinction from covariance shrinkage

Covariance shrinkage, as implemented by estimators such as `LedoitWolf` and `OAS`, primarily improves the conditioning and stability of covariance estimates.

Graphical Lasso instead combines covariance estimation with the inference of a sparse dependency structure.

The library also provides `GraphicalLassoCV`, which selects its regularization strength using cross-validation, and a lower-level `graphical_lasso()` function that accepts an empirical covariance matrix directly.

This exposes a useful separation between calculating covariance statistics and solving the penalized inverse-covariance problem.

The lower-level function supports coordinate descent and a LARS-based solver. The upstream documentation identifies coordinate descent as generally more numerically stable, with LARS potentially useful for very sparse graphs in high-dimensional settings.

#### Structural interpretation and limits

The inferred edges describe conditional statistical dependencies under a Gaussian model, not causal relationships.

An edge does not determine which variable influences the other, and omitted edges can result from estimation error or inappropriate regularization rather than genuine conditional independence.

The upstream documentation identifies several practical limits:

- Standardization can improve graph recovery when variables have substantially different scales.
- Highly connected nodes can be difficult to recover faithfully.
- The number of observations must be sufficiently large relative to the underlying dependency structure.
- Cross-validated regularization can select too many edges, even under otherwise favorable recovery conditions.
- Very strong correlations or unfavorable conditioning can create numerical instability.

These distinctions matter because predictive covariance estimation and accurate graph recovery are different statistical objectives. A regularization setting suitable for likelihood-based prediction may not produce a reliably sparse graph.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+1



Primary source: [https://scikit-learn.org/1.9/modules/covariance.html#sparse-inverse-covariance](https://scikit-learn.org/1.9/modules/covariance.html?utm_source=chatgpt.com#sparse-inverse-covariance)

### 3.2 OPTICS: separating density exploration from cluster extraction

`OPTICS` constructs a reachability ordering that represents density-connected structure across multiple neighborhood scales.

Its fitted representation includes `ordering_`, `reachability_`, `core_distances_`, and `predecessor_`. These describe the order in which points are explored, the distances at which they become reachable, and aspects of their density-connected relationships.

This intermediate representation can be reused to extract different cluster assignments without repeating the full OPTICS computation.

Two extraction mechanisms are especially important.

`cluster_optics_dbscan()` extracts DBSCAN-like clusters for a selected distance threshold. With an appropriate fitted reachability structure, this extraction is linear in the number of observations.

`cluster_optics_xi()` identifies clusters through changes in reachability, allowing density structure to be analyzed without selecting only one global DBSCAN radius.

The estimator can also expose `cluster_hierarchy_`, representing nested clusters identified through its extraction procedure.

#### Why the intermediate representation matters

A DBSCAN fit principally returns a partition for a specified density threshold. OPTICS instead produces a reusable density ordering from which several related partitions can be derived.

That distinction enables investigation of cluster structure across multiple density resolutions, including identifying nested groups and examining how cluster boundaries change with the extraction threshold.

The reachability plot is also an analytical representation in its own right. Valleys and changes in reachability can help expose density boundaries that are obscured by a single flat assignment.

The resulting hierarchy should not be confused with the hierarchical density representation generated by HDBSCAN. The algorithms use different structures and extraction rules.

#### Computational and semantic limitations

The documented scikit-learn implementation can have substantially greater runtime than a single DBSCAN fit. Reusing an OPTICS result may nevertheless be advantageous when several density thresholds must be examined.

OPTICS extraction is also not guaranteed to reproduce DBSCAN's labels exactly. Border-point and noise assignments can differ, and correspondence depends partly on the relationship between `eps` and the fitted `max_eps`.

The implementation has favorable memory characteristics relative to methods that retain full pairwise distance matrices, but time costs and search-radius configuration remain important.

This makes OPTICS particularly valuable as a reusable density-analysis mechanism, not merely as another clustering algorithm.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+1



Primary source: [https://scikit-learn.org/1.9/modules/clustering.html#optics](https://scikit-learn.org/1.9/modules/clustering.html?utm_source=chatgpt.com#optics)

### 3.3 BIRCH: incremental clustering-feature trees and compressed sufficient statistics

`Birch` incrementally summarizes observations in a Clustering Feature Tree (CFT).

Rather than storing every observation as an independent element in its internal clustering representation, it maintains compact subcluster summaries.

For a subcluster containing observations \\(x_1,\ldots,x_m\\), the essential statistics include

\\[ N=m,\qquad LS=\sum\_{i=1}^{m}x_i,\qquad SS=\sum\_{i=1}^{m}\\|x_i\\|\_2^2. \\]

These provide the subcluster count, linear sum, and squared sum. Together they support the computation of centroids and selected dispersion measures without retaining every original observation in the clustering-feature node.

This is a form of lossy data compression targeted at clustering.

#### Two-stage clustering architecture

The estimator distinguishes between incremental subcluster construction and optional global clustering.

During the first stage, incoming observations update the CF tree, whose structure is controlled principally by `threshold` and `branching_factor`.

During the second stage, a global clustering algorithm can operate on the resulting leaf subclusters, producing a final assignment.

The `n_clusters` parameter controls this global step. Setting it to `None` retains the leaf-level subclusters as the operative clustering representation.

This separation enables a particularly useful incremental fitting pattern: build the CF tree across successive batches with `partial_fit()`, defer global clustering, then perform the global step after the compressed representation has been constructed.

#### Architectural significance

BIRCH is simultaneously a clustering algorithm and a streaming summarization mechanism.

Its compressed leaf subclusters can serve as a reduced representation for downstream clustering, avoiding the need for a global clustering algorithm to operate directly on every original observation.

The compression is not information preserving. Fine-scale geometries, minority structures, and distinctions within a subcluster may be lost.

The official documentation also notes that BIRCH becomes less attractive in high-dimensional spaces and suggests considering `MiniBatchKMeans` when the feature dimension is comparatively large.

The clustering-feature summaries should therefore be understood as compact statistics for distance-based grouping, not as universal sufficient statistics for arbitrary subsequent statistical inference.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Primary source: [https://scikit-learn.org/1.9/modules/clustering.html#birch](https://scikit-learn.org/1.9/modules/clustering.html?utm_source=chatgpt.com#birch)

## 4. Nonlinear feature construction and additional ensemble mechanisms

### 4.1 RandomTreesEmbedding: sparse representations from random partitions

`sklearn.ensemble.RandomTreesEmbedding` is an unsupervised feature transformer based on randomly generated decision trees.

The estimator constructs a forest of random trees and encodes each observation according to the terminal leaves into which it falls.

Each tree induces a nonlinear partition of feature space. Leaf membership is then represented using one-hot encoding, and the representations from all trees are concatenated into a sparse binary feature matrix.

For example, if a forest contains \\(T\\) trees, each with its own set of leaves, an observation activates one leaf indicator per tree. The resulting representation has approximately \\(T\\) active entries per observation, independently of the total number of possible leaf features.

#### Why this differs from ordinary tree ensembles

Random forests and Extra Trees typically use labeled outcomes to construct predictive ensembles.

`RandomTreesEmbedding` instead constructs an unsupervised representation. The trees define nonlinear spatial partitions, and the resulting leaf-membership indicators can be supplied to a separate learning algorithm.

This creates a native route from nonlinear partitioning to sparse linear modeling.

A linear estimator operating on the transformed features can express different predictions in different regions of the original space without requiring explicit polynomial bases or hand-written interaction rules.

The representation can also be used for similarity analysis: observations occupying the same leaves share active features. The resulting inner products reflect agreement across tree partitions, although they are not automatically calibrated similarity probabilities.

#### Computational and representational tradeoffs

The output can be high-dimensional because each tree contributes multiple potential leaf features. Sparse storage mitigates this cost when relatively few indicators are active.

The representation is piecewise constant with respect to the underlying tree partitions. This makes it capable of expressing discontinuous nonlinear relationships but insensitive to distinctions between observations falling into the same leaves.

The partition geometry depends on the random tree construction and its configuration. Unlike NCA, it does not use class labels to optimize a distance metric.

The estimator also supports `warm_start=True`, allowing additional random trees to be incorporated into an existing forest under compatible fitting conditions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Primary source: [https://scikit-learn.org/1.9/modules/generated/sklearn.ensemble.RandomTreesEmbedding.html](https://scikit-learn.org/1.9/modules/generated/sklearn.ensemble.RandomTreesEmbedding.html?utm_source=chatgpt.com)

### 4.2 PolynomialCountSketch: compressed polynomial interaction spaces

`sklearn.kernel_approximation.PolynomialCountSketch` approximates a polynomial kernel using Tensor Sketch.

The target kernel has the form

\\[ k(x,y)=(\gamma x^Ty+c_0)^d, \\]

where \\(d\\) controls the polynomial degree.

An explicit polynomial feature map contains combinations of input features whose number can grow rapidly with both feature dimension and polynomial degree.

Tensor Sketch avoids constructing that entire expansion.

Instead, it uses hash functions and convolution computed through fast Fourier transforms to construct a compressed representation approximating the polynomial feature space.

The resulting feature map \\(\phi(x)\\) approximately satisfies

\\[ \phi(x)^T\phi(y)\approx k(x,y). \\]

#### Distinction between explicit and approximate interactions

`PolynomialFeatures` explicitly creates polynomial combinations. This provides interpretable individual basis features but can produce a large expansion.

`PolynomialCountSketch` instead constructs a fixed-dimensional randomized representation controlled by `n_components`.

The approximation trades exact recoverability of individual polynomial interactions for reduced representation size and potentially lower computational cost.

A further distinction is that Tensor Sketch is input-data-independent in its construction. The transformer's `fit()` operation initializes the randomized mapping without learning statistical landmarks from the training observations.

That contrasts with `Nystroem`, which derives its approximation from selected samples.

The compressed representation can be combined with compatible linear estimators, including incremental estimators, enabling approximate nonlinear learning without constructing a full kernel matrix.

However, the approximation introduces variance and information loss. Its accuracy depends on the chosen output dimension, polynomial degree, and input characteristics. Individual transformed coordinates should not be interpreted as particular original interaction terms.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+1



Primary source: [https://scikit-learn.org/1.9/modules/kernel_approximation.html#polynomial-kernel-approximation-via-tensor-sketch](https://scikit-learn.org/1.9/modules/kernel_approximation.html?utm_source=chatgpt.com#polynomial-kernel-approximation-via-tensor-sketch)

### 4.3 AdaBoost: adaptive reweighting rather than gradient fitting

Scikit-learn includes both `AdaBoostClassifier` and `AdaBoostRegressor`.

AdaBoost trains a sequence of weak learners, progressively adjusting the influence of observations according to the performance of earlier learners.

For classification, observations that are incorrectly predicted receive greater relative emphasis in subsequent fitting stages. The final prediction combines the individual learners using weights derived from their fitted performance.

This differs from gradient boosting, in which successive learners are fitted to loss-derived gradients or residual-like targets.

Although both are sequential ensemble techniques, their update mechanisms and supported objectives differ.

AdaBoost's dependence on repeated observation weighting makes it especially important that the underlying base estimator supports appropriate weighted fitting.

For regression, AdaBoost uses a related adaptive procedure based on regression errors and weighted aggregation rather than simply applying the classifier's voting rule to continuous targets.

#### Implications and limits

AdaBoost can provide an effective ensemble around relatively simple base estimators, such as shallow decision trees.

Its sample-reweighting mechanism can also make it sensitive to mislabeled observations and influential outliers, since difficult observations may receive increasing emphasis.

The existence of AdaBoost alongside gradient boosting is therefore more than historical compatibility. It provides an alternative sequential-learning objective and an estimator-compatible way of composing weak learners.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Primary source: [https://scikit-learn.org/1.9/modules/ensemble.html#adaboost](https://scikit-learn.org/1.9/modules/ensemble.html?utm_source=chatgpt.com#adaboost)

## 5. Statistical selection, representation validation, and analytical shortcuts

### 5.1 Efficient leave-one-out cross-validation with RidgeCV

`RidgeCV` has a significant computational capability beyond its general role as a cross-validated estimator.

When `cv=None`, it performs efficient leave-one-out cross-validation using linear-algebraic relationships rather than independently fitting a model for every excluded observation.

In ordinary leave-one-out cross-validation, \\(n\\) separate models might be fitted for \\(n\\) observations. For ridge regression, the algebraic structure allows the necessary validation quantities to be derived more efficiently.

`gcv_mode` controls the underlying linear-algebra strategy:

| Mode      | Computation                                                                          |
| --------- | ------------------------------------------------------------------------------------ |
| `"svd"`   | Singular-value decomposition for dense inputs, with an alternative for sparse inputs |
| `"eigen"` | Eigendecomposition of the relevant Gram matrix                                       |
| `"auto"`  | Selects a strategy based on input characteristics                                    |

The appropriate computational strategy depends on the number of observations, number of features, sparsity, and numerical conditioning.

Two other features are significant.

`store_cv_results=True` retains per-observation cross-validation results for the candidate regularization strengths. This enables inspection of model-selection behavior rather than retaining only the selected alpha.

`alpha_per_target=True` permits a separate regularization strength for each output of a multioutput regression problem.

Both of these capabilities apply to the efficient leave-one-out mode rather than arbitrary user-specified CV splitters.

#### Important scoring distinction

`RidgeCV` changes its default scoring semantics according to the cross-validation mode.

With `cv=None`, the default objective is negative mean squared error. With an explicit general CV strategy, the default scoring uses \\(R^2\\).

Consequently, switching CV modes can change both the computation and the selection criterion. That is an important distinction when interpreting differences in selected regularization strengths.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Primary source: [https://scikit-learn.org/1.9/modules/generated/sklearn.linear_model.RidgeCV.html](https://scikit-learn.org/1.9/modules/generated/sklearn.linear_model.RidgeCV.html?utm_source=chatgpt.com)

### 5.2 Mutual-information feature selection

Scikit-learn provides `mutual_info_classif()` and `mutual_info_regression()` as nonparametric measures of dependence between individual features and a target.

Mutual information is defined by

\\[ I(X;Y)= \int p(x,y) \log\frac{p(x,y)}{p(x)p(y)} \\,dx\\,dy \\]

for continuous random variables, with the corresponding summation for discrete variables.

It measures statistical dependence rather than only linear association.

A feature can have low Pearson correlation with a target but still exhibit substantial mutual information when the relationship is nonlinear.

Scikit-learn estimates mutual information using nearest-neighbor-based entropy estimation techniques.

Its interface supports explicit designation of discrete features and controls such as `n_neighbors`, which influence the statistical estimation procedure.

#### Integration with feature selection

The mutual-information functions can be supplied as scoring functions to compatible selectors such as `SelectKBest` and `SelectPercentile`.

`GenericUnivariateSelect` adds a separate capability: it exposes the selection strategy itself as a configurable estimator parameter.

This permits model selection to vary not only the score function and selection threshold but also whether features are selected by count, percentile, or a supported statistical-testing rule.

A critical distinction concerns significance-testing selectors.

Mutual-information functions provide estimated dependency scores; they do not generally provide the p-values required by false-discovery-rate or family-wise-error-control selectors.

Consequently, MI cannot simply be substituted into every statistical selector with identical semantics.

#### Interpretation and limitations

Mutual-information selection is univariate: each feature is evaluated independently against the target.

It does not directly measure whether several features together convey information unavailable from any feature individually.

For example, XOR-like relationships can have zero marginal mutual information for each feature despite being completely predictable from their joint configuration.

Nearest-neighbor entropy estimation also requires adequate sample sizes and is sensitive to the treatment of discrete and continuous variables.

MI is therefore useful for screening nonlinear marginal dependencies, but is not a complete multivariate dependency-discovery or feature-interaction framework.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+2



Primary source: [https://scikit-learn.org/1.9/modules/feature_selection.html#univariate-feature-selection](https://scikit-learn.org/1.9/modules/feature_selection.html?utm_source=chatgpt.com#univariate-feature-selection)

### 5.3 Embedding trustworthiness: validating neighborhood preservation

`sklearn.manifold.trustworthiness()` evaluates the degree to which a low-dimensional representation introduces neighbors that were not close in the original feature space.

The score lies between zero and one, with higher values indicating greater preservation of original local neighborhood relationships.

Its definition penalizes observations that appear among the nearest neighbors in the embedding but have comparatively distant ranks in the original space.

For \\(n\\) observations and neighborhood size \\(k\\), the documented measure is

\\[ T(k)=1- \frac{2}{nk(2n-3k-1)} \sum\_{i=1}^{n} \sum\_{j\in\mathcal{N}\_i^k} \max(0,r(i,j)-k), \\]

where \\(\mathcal{N}\_i^k\\) contains the \\(k\\) nearest neighbors of observation \\(i\\) in the embedded space, and \\(r(i,j)\\) is the original-space neighbor rank of observation \\(j\\) relative to \\(i\\).

This directly measures a geometric property of the representation rather than a predictive score or visualization quality.

#### What it does and does not establish

Trustworthiness is useful for comparing dimensionality-reduction outputs produced by PCA, t-SNE, Isomap, or other embeddings.

It can also help assess how changing representation dimensionality affects local structure.

The metric is directional: it principally penalizes false neighbors introduced by the embedding. It is not a complete measure of all topology preservation, global distance distortion, or neighborhood recall.

A representation can obtain high trustworthiness while omitting meaningful original neighbors from the embedded neighborhood.

The result is also dependent on the original-space distance metric and chosen neighborhood size.

The function supports a precomputed original-space distance matrix, permitting evaluation against a distance definition that may differ from ordinary Euclidean distance.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Primary source: [https://scikit-learn.org/1.9/modules/generated/sklearn.manifold.trustworthiness.html](https://scikit-learn.org/1.9/modules/generated/sklearn.manifold.trustworthiness.html?utm_source=chatgpt.com)

### 5.4 Class-weight and sample-weight generation

`compute_class_weight()` and `compute_sample_weight()` provide reusable weighting calculations for imbalanced classification problems.

For ordinary balanced class weights, the heuristic is

\\[ w_c=\frac{n}{C\\,n_c}, \\]

where \\(n_c\\) denotes the count of observations in class \\(c\\), \\(C\\) the number of classes, and \\(n\\) the total sample count.

`compute_class_weight()` produces weights indexed by class. In 1.9.1 it can also incorporate an existing sample-weight vector when calculating balanced weights.

`compute_sample_weight()` produces observation-level weights and supports multioutput targets, combining per-output class weights where appropriate.

It also supports computing balanced weights for a specified subsample through its `indices` parameter.

These utilities are distinct from resampling. They do not change the number of observations, create synthetic examples, or necessarily balance the learned model's predictions.

Their interaction with individual estimators depends on how those estimators use sample weights during fitting. In particular, some estimators use weights in multiple stages of fitting, not solely as multiplicative factors in a final loss function.

Weighting also does not replace probability calibration or appropriate evaluation under the target data distribution.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+1



Primary sources:

[https://scikit-learn.org/1.9/modules/generated/sklearn.utils.class_weight.compute_class_weight.html](https://scikit-learn.org/1.9/modules/generated/sklearn.utils.class_weight.compute_class_weight.html?utm_source=chatgpt.com)

[https://scikit-learn.org/1.9/modules/generated/sklearn.utils.class_weight.compute_sample_weight.html](https://scikit-learn.org/1.9/modules/generated/sklearn.utils.class_weight.compute_sample_weight.html?utm_source=chatgpt.com)

### 5.5 Dummy estimators and cross-validation-aware precision–recall analysis

Baseline estimators. `DummyClassifier` and `DummyRegressor` implement feature-independent prediction rules under the standard estimator interface.

Their significance is not predictive sophistication. They establish baseline behavior using the same fitting, scoring, and cross-validation machinery as substantive models.

Classifier strategies include class-prior-based and constant or randomized prediction rules. Regressor strategies include mean, median, quantile, and constant predictions.

This avoids implementing separate evaluation logic for baseline models.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Multifold precision–recall visualization. Version 1.9 introduces `PrecisionRecallDisplay.from_cv_results()`.

It constructs fold-specific precision–recall curves from results returned by `cross_validate()` with both `return_estimator=True` and `return_indices=True`.

This differs from calculating one precision–recall curve from a single collection of out-of-fold predictions. Each fitted fold estimator is evaluated against its corresponding held-out observations, preserving fold-specific behavior.

The resulting visualization can expose variability in operating characteristics across validation partitions.

It also eliminates custom code for associating fitted fold models with their held-out indices and generating individual displays.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Primary sources:

[https://scikit-learn.org/1.9/api/sklearn.dummy.html](https://scikit-learn.org/1.9/api/sklearn.dummy.html?utm_source=chatgpt.com)

[https://scikit-learn.org/1.9/modules/generated/sklearn.metrics.PrecisionRecallDisplay.html](https://scikit-learn.org/1.9/modules/generated/sklearn.metrics.PrecisionRecallDisplay.html?utm_source=chatgpt.com)

## 6. Custom estimator architecture and extension mechanisms

### 6.1 Custom cloning through `__sklearn_clone__`

Scikit-learn ordinarily clones estimators by reconstructing their configuration without retaining fitted attributes.

The developer protocol `__sklearn_clone__()` provides a controlled way to override that behavior.

When an estimator defines this method, `sklearn.base.clone()` can delegate cloning to the estimator's own implementation.

This matters because estimator cloning is deeply embedded in cross-validation, model selection, pipelines, and meta-estimators.

The ability to customize cloning makes it possible to preserve selected state across a clone operation when that state is an intentional property of the estimator's lifecycle.

The returned object must still satisfy the estimator contract. Retaining fitted state is not automatically appropriate: it can undermine the independence assumed by cross-validation or cause observations from one validation fold to influence another.

The protocol should therefore be distinguished from ordinary object copying and from serialization. It is an explicit extension point for the semantics of estimator reconstruction.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Primary source: [https://scikit-learn.org/1.9/developers/develop.html](https://scikit-learn.org/1.9/developers/develop.html?utm_source=chatgpt.com)

### 6.2 FrozenEstimator: incorporating fitted components into new compositions

`sklearn.frozen.FrozenEstimator` wraps a fitted estimator and prevents subsequent fitting operations from changing its learned state.

Calling `fit()` on the wrapper has no effect. The wrapper delegates supported prediction and transformation methods to the underlying estimator and exposes its attributes.

Its `fit_predict()` and `fit_transform()` methods are disabled, distinguishing it from an ordinary estimator whose combined fit-and-predict or fit-and-transform behavior is available.

This has two important applications.

First, a previously trained estimator can participate in a composite workflow without being fitted again.

Second, a pretrained transformer can be incorporated into a pipeline whose `fit()` operation must train other stages but should not modify that particular component.

The distinction from `warm_start` is important. Warm starting allows a supported estimator to reuse existing learned state while continuing or extending fitting. Freezing prevents fitting from modifying that state.

`FrozenEstimator` uses the custom cloning protocol to preserve the wrapped estimator's fitted state under cloning.

#### Correctness boundary

Freezing does not validate the suitability of the pretrained model for new data.

Feature compatibility, preprocessing consistency, data distribution changes, and the independence of evaluation data remain separate concerns.

Likewise, freezing a model before cross-validation does not make the model's original training history disappear. A frozen component trained using observations subsequently treated as validation data can introduce leakage.

The capability is best understood as fitted-state preservation within estimator composition, not as a general mechanism for making pretrained models statistically safe to reuse.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Primary source: [https://scikit-learn.org/1.9/modules/generated/sklearn.frozen.FrozenEstimator.html](https://scikit-learn.org/1.9/modules/generated/sklearn.frozen.FrozenEstimator.html?utm_source=chatgpt.com)

### 6.3 Metadata-routing implementation for third-party meta-estimators

The original guide covers metadata routing as a mechanism for passing auxiliary information through nested estimators. The corresponding developer interface deserves explicit treatment.

For external implementations, the core components are:

| Interface                           | Responsibility                                                                     |
| ----------------------------------- | ---------------------------------------------------------------------------------- |
| `MetadataRequest`                   | Describes metadata consumed by particular estimator methods                        |
| `MetadataRouter`                    | Describes metadata routing among an outer estimator and contained objects          |
| `MethodMapping`                     | Maps methods of an outer estimator to methods invoked on contained objects         |
| `process_routing()`                 | Validates and distributes supplied metadata according to the routing configuration |
| `get_routing_for_object()`          | Obtains a routing representation from an object or its metadata configuration      |
| `MetadataRouter.add_self_request()` | Declares metadata consumed by the router itself                                    |

The central design consideration is that an outer method and an inner method need not have the same name.

For example, an outer estimator's `fit()` operation may invoke a transformer's `fit()` and `transform()` methods, followed by a classifier's `fit()` method.

`MethodMapping` can explicitly represent those relationships.

`process_routing()` then determines which metadata should be passed to each specific call and validates whether the nested consumers requested it.

The developer API therefore supports a structured representation of method-specific dataflow, not merely a dictionary of keyword arguments to forward.

#### Consumers, routers, and combined roles

A simple estimator consuming `sample_weight` may obtain its request configuration automatically through the estimator API.

A meta-estimator that invokes contained estimators needs to define routing relationships explicitly.

An estimator can also consume metadata itself while forwarding metadata to children.

This combined role is represented by including a self-request in its `MetadataRouter`.

For example, an ensemble wrapper might use one set of sample weights for its own aggregation process while routing a distinct set of weights to a contained estimator through metadata aliases.

The routing contract can distinguish these values without requiring them to share the same externally visible name.

#### Architectural implications

These mechanisms substantially reduce the need for custom keyword filtering and manual propagation through deeply nested modeling structures.

They also make routing behavior inspectable, testable, and compatible with framework-level validation.

One important implementation detail is that `process_routing()` returns a nested structure organized by consuming object and method. The documentation recommends item-based access to the resulting structure, particularly because serialization across execution backends may not preserve every convenience attribute-access behavior.

Metadata routing remains experimental in version 1.9.1. Its availability should not be interpreted as a guarantee that every third-party meta-estimator implements the protocol or that all supported methods accept arbitrary metadata.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+1



Primary sources:

[https://scikit-learn.org/1.9/auto_examples/miscellaneous/plot_metadata_routing.html](https://scikit-learn.org/1.9/auto_examples/miscellaneous/plot_metadata_routing.html?utm_source=chatgpt.com)

[https://scikit-learn.org/1.9/api/sklearn.utils.metadata_routing.html](https://scikit-learn.org/1.9/api/sklearn.utils.metadata_routing.html?utm_source=chatgpt.com)

### 6.4 Conditional method availability through `available_if`

`sklearn.utils.metaestimators.available_if()` is a descriptor for conditionally exposing methods or attributes.

A common problem for wrapper estimators is that not every wrapped object implements the same prediction interfaces.

A classifier might expose `predict_proba()`, while another compatible classifier exposes only `decision_function()` and `predict()`.

A meta-estimator should not necessarily advertise `predict_proba()` merely because the wrapper class can define a method with that name.

`available_if()` permits the existence of the wrapper's method to depend on a predicate evaluated against the wrapper instance.

This allows conditional estimator interfaces to participate in ordinary capability discovery through operations such as `hasattr()`.

The mechanism improves compatibility with framework code that checks for a method before invoking it.

Its role is more precise than ordinary dynamic delegation: it controls whether the method is presented as available, helping align the wrapper's public capabilities with those of its contained estimator.

The predicate still needs to reflect the wrapper's true behavior. Conditional availability does not automatically validate every downstream method signature, data representation, or estimator state.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Primary source: [https://scikit-learn.org/1.9/modules/generated/sklearn.utils.metaestimators.available_if.html](https://scikit-learn.org/1.9/modules/generated/sklearn.utils.metaestimators.available_if.html?utm_source=chatgpt.com)

### 6.5 Additional inspection and low-level numerical primitives

Several existing utilities provide useful access to intermediate model structure or reusable computations.

Feature-importance extraction. `SelectFromModel` and `RFE` support `importance_getter` as either an attribute path or a callable receiving the fitted estimator.

This permits feature selection to operate on importance information stored inside nested estimators or calculated through a custom importance-extraction function.

Version 1.9 extends support for sparse feature-importance arrays in these selectors and makes `RFE` ranking deterministic when importances are tied by using stable sorting.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Tree traversal and pruning. Decision-tree estimators provide `apply()`, which identifies the terminal leaf reached by each observation, and `decision_path()`, which returns a sparse indicator matrix of visited nodes.

They also expose `cost_complexity_pruning_path()`, which computes effective pruning parameters and corresponding subtree impurities.

Together, these support inspection of individual decision paths, comparison of tree regions, and model-complexity analysis beyond aggregate feature importance.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Numerical utility functions. Scikit-learn exposes functions including `safe_sparse_dot`, sparse in-place normalization and scaling operations, incremental statistical updates, and randomized linear-algebra primitives.

These are potentially valuable building blocks when implementing compatible transformers or numerical algorithms.

For example, `safe_sparse_dot()` performs dot products while handling supported sparse inputs and controlling whether the result is retained as sparse or converted to dense.

Such utilities can reduce bespoke handling of sparse representations, although their behavior should be evaluated against the corresponding NumPy and SciPy operations rather than assuming a unique numerical capability exists only in scikit-learn.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Primary sources:

[https://scikit-learn.org/1.9/modules/feature_selection.html](https://scikit-learn.org/1.9/modules/feature_selection.html?utm_source=chatgpt.com)

[https://scikit-learn.org/1.9/modules/generated/sklearn.tree.DecisionTreeClassifier.html](https://scikit-learn.org/1.9/modules/generated/sklearn.tree.DecisionTreeClassifier.html?utm_source=chatgpt.com)

[https://scikit-learn.org/1.9/api/sklearn.utils.html](https://scikit-learn.org/1.9/api/sklearn.utils.html?utm_source=chatgpt.com)

## 7. Specialized estimators and additional learning semantics

### 7.1 NearestCentroid and shrunken-centroid classification

`NearestCentroid` represents each class using a central prototype and assigns observations to the closest prototype.

Its usefulness extends beyond being a simplified nearest-neighbor classifier.

With `shrink_threshold`, it can shrink class-centroid deviations toward an overall centroid, reducing the influence of features that contribute relatively little to class separation.

This provides an interpretable feature-discrimination mechanism and can be useful in high-dimensional classification settings.

The fitted estimator exposes class centroids, centroid deviations, within-class standard deviations, and class priors.

This makes it possible to inspect which features contribute to the separation of class prototypes.

The estimator supports Euclidean and Manhattan distance choices, with corresponding differences in the definition of the class center.

Centroid shrinking is not supported with sparse input matrices, however, even though ordinary nearest-centroid classification accepts supported sparse inputs.

Unlike a Gaussian discriminant model, the estimator does not construct a full covariance-based representation of each class.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Primary source: [https://scikit-learn.org/1.9/modules/generated/sklearn.neighbors.NearestCentroid.html](https://scikit-learn.org/1.9/modules/generated/sklearn.neighbors.NearestCentroid.html?utm_source=chatgpt.com)

### 7.2 BernoulliRBM: probabilistic unsupervised feature learning

`sklearn.neural_network.BernoulliRBM` implements a restricted Boltzmann machine with binary visible and hidden units.

The model is a probabilistic bipartite graphical model in which visible units have no direct connections to other visible units, and hidden units have no direct connections to other hidden units.

The conditional distributions factorize within each layer.

For a binary hidden unit, the conditional activation probability is expressed through a logistic function:

\\[ P(h_j=1\mid v) = \sigma\left(c_j+\sum_i W\_{ij}v_i\right). \\]

This structure supports block Gibbs sampling by alternating between visible and hidden states.

#### Learning algorithm

The implementation uses Stochastic Maximum Likelihood, commonly described as Persistent Contrastive Divergence.

The learning procedure maintains persistent Markov chains whose states are updated across training iterations. These chains approximate the model-dependent expectation needed in the likelihood gradient.

This differs from ordinary supervised neural-network training with backpropagation against observed labels.

The estimator learns a latent probabilistic representation of the input distribution and can transform observations into hidden-feature activations.

#### Boundaries

Scikit-learn's implementation specifically models Bernoulli visible units. Input data should therefore be binary or contain values between zero and one that can meaningfully represent activation probabilities.

The model is not a general-purpose density estimator, nor does it provide the flexibility or accelerator infrastructure associated with modern deep generative modeling frameworks.

The documentation also notes that the approximate sampling procedure can be inefficient and that small datasets may not support useful learning of the latent structure.

Nevertheless, it remains a distinct native capability for probabilistic feature learning and studying restricted energy-based models.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Primary source: [https://scikit-learn.org/1.9/modules/neural_networks_unsupervised.html](https://scikit-learn.org/1.9/modules/neural_networks_unsupervised.html?utm_source=chatgpt.com)

### 7.3 Passive-aggressive learning through SGD estimators

The passive-aggressive learning algorithms remain relevant in scikit-learn 1.9.1, but their API status requires an explicit qualification.

`PassiveAggressiveClassifier` and `PassiveAggressiveRegressor` were deprecated in version 1.8, with removal scheduled for 1.10.

Their algorithms are instead accessible through `SGDClassifier` and `SGDRegressor`, using the appropriate loss and `learning_rate="pa1"` or `"pa2"`.

Passive-aggressive learning performs online updates according to prediction losses.

When an observation is already classified with sufficient margin, the update can be zero. When the model incurs loss, it adjusts the coefficients with a step size determined by the loss, feature norm, and aggressiveness parameter.

For PA-I classification with hinge loss, the update step can be expressed as

\\[ \eta_t= \min\left( C,\frac{\ell_t}{\\|x_t\\|^2} \right). \\]

PA-II uses a modified denominator that regularizes the update.

These update rules are distinct from ordinary SGD learning-rate schedules.

The mechanism can be useful for sparse, incrementally processed observations where updates should respond to current prediction errors.

However, the old dedicated classes should not be presented as the preferred long-term interface. The replacement configuration within the SGD estimators is the relevant stable integration path for the target version.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+2



Primary sources:

[https://scikit-learn.org/1.9/modules/generated/sklearn.linear_model.PassiveAggressiveClassifier.html](https://scikit-learn.org/1.9/modules/generated/sklearn.linear_model.PassiveAggressiveClassifier.html?utm_source=chatgpt.com)

[https://scikit-learn.org/1.9/modules/generated/sklearn.linear_model.SGDClassifier.html](https://scikit-learn.org/1.9/modules/generated/sklearn.linear_model.SGDClassifier.html?utm_source=chatgpt.com)

### 7.4 Semi-supervised learning: graph inference versus self-training

The original overview lists the principal semi-supervised estimators, but their learning semantics warrant a clearer distinction.

`SelfTrainingClassifier` wraps a compatible supervised classifier and repeatedly adds pseudo-labeled observations to its training set.

The process relies on the base estimator's predicted probabilities. Observations can be selected according to a probability threshold or by choosing the highest-confidence candidates.

The estimator tracks the labels assigned during training and the iteration in which each previously unlabeled observation was selected.

Because pseudo-label selection depends on predicted confidence, probability calibration is consequential. Overconfident errors can be reinforced through successive self-training rounds.

`LabelPropagation` and `LabelSpreading` instead construct a similarity graph over the observed labeled and unlabeled data.

They infer unknown labels using relationships among observations rather than iteratively training a separate supervised predictor on increasingly large pseudo-labeled datasets.

The two graph-based methods also differ.

`LabelPropagation` uses hard clamping of the original labels.

`LabelSpreading` introduces regularization and soft-clamping behavior, using a normalized graph representation that can provide greater robustness to noisy labels.

Their kernel choice materially affects computation: an RBF similarity can produce a dense graph, whereas the nearest-neighbor kernel can produce a sparse representation.

These distinctions make the semi-supervised subsystem relevant to two different problem families: bootstrapping a supervised predictor using unlabeled data, and inferring labels through the geometry of an observed similarity graph.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Primary source: [https://scikit-learn.org/1.9/modules/semi_supervised.html](https://scikit-learn.org/1.9/modules/semi_supervised.html?utm_source=chatgpt.com)

### 7.5 Outlier-score semantics and threshold interpretation

Scikit-learn's anomaly-detection estimators do not share a universal raw anomaly-score definition.

For supported estimators, `score_samples()` returns the estimator's raw scoring convention, while `decision_function()` adjusts scores relative to an offset or decision threshold.

A common documented relationship is

\\[ \operatorname{decision\\\_function}(X) = \operatorname{score\\\_samples}(X)-\operatorname{offset\\\_}. \\]

The offset may be chosen according to the configured contamination fraction or another estimator-specific convention.

This means raw scores, decision scores, and binary inlier/outlier labels answer different questions.

Furthermore, the raw scores generated by Isolation Forest, One-Class SVM, Local Outlier Factor, and covariance-based methods do not represent the same statistical quantity.

Numerical agreement between their scores should not be assumed, even when all estimators use positive and negative decision values to distinguish inliers from outliers.

`LocalOutlierFactor` also retains its distinct interface behavior: ordinary outlier-detection mode exposes training-observation scores through `negative_outlier_factor_`, whereas novelty mode enables scoring previously unseen observations.

This boundary is particularly important when composing anomaly detectors with general evaluation infrastructure.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Primary source: [https://scikit-learn.org/1.9/modules/outlier_detection.html](https://scikit-learn.org/1.9/modules/outlier_detection.html?utm_source=chatgpt.com)

## 8. Version 1.9.0 and 1.9.1: additional numerical and behavioral changes

The original guide identifies the major new capabilities and several deprecations introduced in the 1.9 series.

The following changes deserve additional documentation because they affect numerical results, sampling semantics, reproducibility, or future compatibility.

### 8.1 Changes introduced in version 1.9.0

| Affected functionality                                       | Behavior in 1.9.0                                                                                                                                                  | Consequence                                                                                               |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| Random forests and Extra Trees                               | Bootstrap sampling uses supplied sample weights as sampling probabilities. With weights, float `max_samples` is interpreted relative to the sum of sample weights. | Weighted ensembles can fit different trees than earlier releases, even with otherwise unchanged settings. |
| Histogram gradient boosting                                  | Bin-edge construction now accounts for sample weights through weighted quantiles or weighted subsampling, depending on the fitting conditions.                     | Weighting influences feature discretization as well as the subsequent tree-fitting objective.             |
| `MiniBatchKMeans`                                            | Mini-batch observations are sampled with replacement according to normalized sample weights when weights are supplied.                                             | Weights influence which observations are processed during incremental optimization.                       |
| `GaussianProcessRegressor`                                   | Hyperparameters of the default `ConstantKernel() * RBF()` kernel are now optimized when an optimizer is enabled.                                                   | Default fitted Gaussian-process models can differ from earlier versions.                                  |
| `LogisticRegression` with L-BFGS                             | Supported `float32` inputs now use `float32` gradient calculations instead of automatically being promoted to `float64`.                                           | Memory use, computation, and floating-point results may change.                                           |
| `ElasticNet`, `ElasticNetCV`, and `enet_path`                | Support for `l1_ratio=0` is improved through an alternative dual-gap formulation.                                                                                  | The implementations can support the pure L2 endpoint with improved stopping behavior.                     |
| `PowerTransformer` with Yeo–Johnson                          | The transformation now uses SciPy's implementation for improved numerical stability.                                                                               | Numerical edge cases and floating-point results may differ.                                               |
| `BayesianRidge` and `ARDRegression`                          | Test features are now centered correctly when calculating predictive variance.                                                                                     | Predictive uncertainty estimates can change even when the underlying prediction problem is unchanged.     |
| `GradientBoostingClassifier` and `GradientBoostingRegressor` | Impurity calculations are corrected for the formerly default `friedman_mse` behavior.                                                                              | Previously fitted tree structures may differ in affected cases.                                           |

These are not interchangeable changes.

Some affect which observations are sampled. Others alter the numerical solver, statistical objective implementation, or interpretation of uncertainty.

In particular, weighting should not be understood as a generic multiplier applied only after feature discretization or bootstrap sampling. The exact stage at which weights enter fitting can substantially affect model behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+2



Primary source: [https://scikit-learn.org/1.9/whats_new/v1.9.html](https://scikit-learn.org/1.9/whats_new/v1.9.html?utm_source=chatgpt.com)

### 8.2 Additional corrections in version 1.9.1

Version 1.9.1 introduces several correctness improvements with implications for existing workflows.

LDA and QDA covariance normalization. Covariance normalization in the SVD-based computations is adjusted to align with maximum-likelihood covariance estimation and the corresponding eigen-based results. Predictions or fitted quantities may differ from earlier behavior in affected cases.

Sparse distance graphs in clustering. `DBSCAN` and `OPTICS` no longer emit certain spurious efficiency warnings for supported precomputed sparse distance matrices. This improves compatibility with explicitly constructed sparse graph representations.

Parallel neighbor searches. `NearestNeighbors.radius_neighbors()` correctly handles array-like radius arguments with multiple jobs using KD-tree and Ball-tree search.

QuantileTransformer sparse fitting. A correction addresses degenerate quantiles when fitting sparse inputs under the combination of `ignore_implicit_zeros=True` and subsampling.

Array API interoperability. Classification metrics handle pandas labels correctly when prediction arrays belong to another supported Array API namespace or device.

Scoring metadata overhead. Scorers created by `make_scorer()` no longer deep-copy metadata keyword arguments on every invocation, reducing unnecessary memory work during evaluation.

Routing through intermediate meta-estimators. Corrected `fit_transform()` routing prevents metadata from being silently dropped through selected feature-selection and imputation meta-estimators used as intermediate pipeline stages. Although the guide already identifies this general fix, it is worth emphasizing that the old behavior could affect fitted results without an obvious error.

The sparse-graph corrections are especially relevant to the reusable neighbor-graph capabilities described earlier in this addendum. They improve the compatibility of those representations with downstream clustering operations but do not alter the requirement that graph semantics be correct.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation



Primary source: [https://scikit-learn.org/1.9/whats_new/v1.9.html](https://scikit-learn.org/1.9/whats_new/v1.9.html?utm_source=chatgpt.com)

### 8.3 Additional deprecations and planned changes

The following transitions should be distinguished from already-removed functionality.

| Interface                                                                               | Status in 1.9.1                                                                    | Consequence                                                                                |
| --------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `PassiveAggressiveClassifier`, `PassiveAggressiveRegressor`                             | Deprecated since 1.8; scheduled removal in 1.10                                    | Use equivalent passive-aggressive configurations of the SGD estimators                     |
| `GradientBoostingClassifier(criterion=...)`, `GradientBoostingRegressor(criterion=...)` | Parameter deprecated in 1.9                                                        | The criterion choices no longer provide a meaningful modeling distinction after correction |
| `LogisticRegressionCV(scoring=None)`                                                    | Existing default remains accuracy-based; change to `neg_log_loss` planned for 1.11 | Explicit scoring avoids future changes in the optimization-selection criterion             |
| Positional `sample_weight` in `LogisticRegressionCV.score()`                            | Deprecated; removal planned for 1.11                                               | Supply sample weights by keyword                                                           |
| `n_alphas` in `lasso_path()` and `enet_path()`                                          | Deprecated in 1.9                                                                  | Use `alphas`, which accepts either an integer count or explicit parameter values           |

The most consequential distinction is between an API that is deprecated but available and one that has already been removed.

The relevant functionality should remain documented for the target release, but the current preferred interface and scheduled transition should be stated alongside it.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://scikit-learn.org\&sz=32)

scikit-learn 1.9.1 documentation+2



Primary source: [https://scikit-learn.org/1.9/whats_new/v1.9.html](https://scikit-learn.org/1.9/whats_new/v1.9.html?utm_source=chatgpt.com)

## 9. Cross-capability architectural implications

The additional mechanisms documented here support several broader forms of composition that are easy to overlook when examining individual estimator families.

### 9.1 Treating learned representations as independently useful outputs

NCA, RandomTreesEmbedding, PLS, and polynomial kernel approximation all produce representations that can be consumed independently of the mechanism that learned or constructed them.

However, they encode different forms of structure.

NCA encodes class-sensitive distances. RandomTreesEmbedding encodes membership in nonlinear spatial partitions. PLS encodes cross-covariance between paired variable spaces. PolynomialCountSketch approximates a particular nonlinear kernel feature space.

The shared transformer interface does not imply that their resulting representations are statistically interchangeable.

This distinction makes the estimator protocol valuable: it enables interchangeable composition while preserving differences in the mathematical meaning of each representation.

### 9.2 Reusing expensive structural computation

Several additional capabilities separate an expensive construction step from lower-cost downstream operations.

OPTICS separates reachability ordering from cluster extraction. BIRCH separates incremental data summarization from global clustering. Neighbor-graph transformers separate search from graph consumption. Regularization-path algorithms reuse structure across a family of coefficient solutions. Efficient RidgeCV exploits analytical structure rather than independently refitting every validation problem.

These capabilities create opportunities to avoid repeated computation when multiple analyses share a common mathematical intermediate.

The benefit depends on whether the intermediate representation remains valid as downstream parameters, samples, or statistical assumptions change.

### 9.3 Distinguishing predictive modeling from structural inference

Graphical Lasso, mutual-information estimators, NCA, and cross-decomposition methods illustrate different meanings of learning relationships.

Graphical Lasso estimates conditional dependencies under a Gaussian model. Mutual information estimates marginal statistical dependence. NCA learns distances for supervised classification. Cross-decomposition learns linear relationships between paired data spaces.

These operations can produce complementary evidence, but they do not jointly establish causality or automatically construct a coherent probabilistic graphical model.

The additional mathematical structure comes from their distinct objectives, not from the fact that they all return numerical arrays or estimator attributes.

### 9.4 Preserving estimator lifecycle semantics across compositions

Custom cloning, FrozenEstimator, metadata routing, and conditional method availability collectively expand what can be expressed through scikit-learn's estimator protocol.

An external component can preserve intentional fitted state, expose only supported methods, declare how nested operations consume metadata, and participate in higher-level validation or model-selection tools.

This reduces the need to reimplement broad portions of estimator orchestration.

At the same time, these mechanisms introduce lifecycle obligations: fitted-state reuse, validation independence, metadata propagation, and method availability must remain consistent with the statistical operation being performed.

They provide compositional infrastructure, not automatic guarantees of statistical correctness.

## Closing synthesis

The capabilities added in this document extend scikit-learn's architectural significance in several directions not fully captured by the original overview.

The library provides more than standard predictive estimators and preprocessing functions. It also includes supervised metric learning, sparse reconstruction, conditional-dependency estimation, compressed nonlinear representations, reusable graph structures, analytical model-selection shortcuts, and extensibility mechanisms that control estimator lifecycle and nested dataflow.

The most important distinction running through these additions is between learning a model, constructing a reusable representation, and extracting information from that representation.

Scikit-learn supports all three through partially shared interfaces, but each capability retains its own statistical assumptions, numerical behavior, and computational constraints.

Understanding those distinctions, along with the specific ways they compose, reveals additional opportunities to replace bespoke modeling, representation, graph-processing, and evaluation machinery with functionality already present in the library.