# pgmpy 1.1.2 — Comprehensive Python Library Capability Reference

Research date: October 22, 2026 | Target: pgmpy 1.1.2 (stable, released April 30, 2026) | Python 3.10–3.14 | MIT license

## 1. Executive orientation

pgmpy is a Python framework for probabilistic graphical modeling, causal discovery, causal reasoning, and statistical inference. It combines graph-theoretic representations of dependencies and causal relationships with probability distributions, statistical estimators, inference algorithms, simulation mechanisms, and model evaluation.

Its distinguishing architectural value is the ability to represent a probabilistic or causal system explicitly and reuse that representation across multiple operations, rather than building unrelated implementations for statistical estimation, dependency reasoning, prediction, simulation, and intervention analysis.

Version 1.1 substantially expanded pgmpy's causal-model infrastructure and introduced more consistent, scikit-learn-compatible interfaces. Version 1.1.2 added conditional-independence tests, test caching, graph diagnostics, and several algorithmic correctness and performance improvements.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

+2



Primary sources:

- Documentation: [https://pgmpy.org/](https://pgmpy.org/?utm_source=chatgpt.com)
- Repository: [https://github.com/pgmpy/pgmpy](https://github.com/pgmpy/pgmpy?utm_source=chatgpt.com)
- Version history: [https://github.com/pgmpy/pgmpy/blob/v1.1.2/CHANGELOG.md](https://github.com/pgmpy/pgmpy/blob/v1.1.2/CHANGELOG.md?utm_source=chatgpt.com)
- Tagged source: [https://github.com/pgmpy/pgmpy/tree/v1.1.2](https://github.com/pgmpy/pgmpy/tree/v1.1.2?utm_source=chatgpt.com)
- Package metadata: [https://pypi.org/project/pgmpy/1.1.2/](https://pypi.org/project/pgmpy/1.1.2/?utm_source=chatgpt.com)

### 1.1 Core conceptual model

pgmpy separates several concerns that are frequently conflated in probabilistic modeling:

1. Graph structure: Which variables are connected, how their dependencies are directed, and which independence or causal relationships the structure implies.
2. Probability distributions: How uncertainty is represented numerically through conditional probability distributions, factors, potentials, or structural equations.
3. Learning: How graph structure and distribution parameters are inferred from observations, potentially subject to prior knowledge.
4. Inference: How probability distributions and predictions are computed from a fitted model and observed evidence.
5. Causal identification and estimation: Whether and how intervention effects can be identified and computed under causal assumptions.
6. Simulation and validation: How fitted models generate observational or interventional data, and how their structures and behavior are evaluated.

These layers can be combined, but they are not interchangeable. A learned Bayesian network may be an excellent model of conditional dependencies without providing a justified causal interpretation.

### 1.2 Capability map

| Functional area         | Principal capabilities                                                                                                    |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Graph representations   | DAGs, PDAGs, ancestral and mixed graphs, Bayesian networks, Markov networks, factor graphs, dynamic Bayesian networks     |
| Probability modeling    | Discrete conditional distributions, linear Gaussian models, factors, functional distributions, structural equation models |
| Structure learning      | Constraint-based discovery, greedy score optimization, equivalence search, expert-constrained discovery                   |
| Parameter learning      | Maximum likelihood, Bayesian estimation, expectation-maximization, Gaussian parameter estimation                          |
| Probabilistic inference | Variable elimination, junction-tree methods, belief propagation, sampling-based inference, MAP estimation                 |
| Causal reasoning        | Graphical separation, causal identification, backdoor/frontdoor analysis, intervention queries                            |
| Simulation              | Forward sampling, evidence-conditioned simulation, interventions, synthetic data                                          |
| Statistical testing     | Conditional independence testing, scoring, graph evaluation, model diagnostics                                            |
| Ecosystem integration   | pandas, NumPy, NetworkX, SciPy, scikit-learn, PyTorch/Pyro, model serialization, graph visualization                      |

The most useful way to understand pgmpy is as a graph-centered probabilistic reasoning toolkit, not simply a Bayesian-network package or a causal-discovery algorithm collection.

## 2. Graph representations and probabilistic models

### 2.1 Graph semantics

pgmpy distinguishes graphs that encode conditional dependencies from graphs representing causal hypotheses or equivalence classes.

| Representation      | Meaning and capabilities                                                                                                                           |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DAG`               | Directed acyclic graph supporting ancestral relationships, graphical separation, independencies, causal roles, and graph transformations           |
| `PDAG`              | Partially directed acyclic graph, representing edges whose orientations may remain unresolved; useful for observational Markov-equivalence classes |
| `ADMG`              | Acyclic directed mixed graph, supporting directed and bidirected edges to encode relationships involving latent confounding                        |
| `MAG`               | Maximal ancestral graph, supporting causal reasoning with latent variables and potentially selection effects                                       |
| `SimpleCausalModel` | Specialized causal DAG constructed from role information                                                                                           |
| `UndirectedGraph`   | Base representation for undirected graphical models and their associated separation properties                                                     |

These classes are not merely drawing structures. They implement graph operations that can encode or interrogate meaningful statistical constraints.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy

+3



DAG capabilities include:

- Ancestors, descendants, parents, children, roots, leaves, and active trails.
- D-separation tests and discovery of minimal separating sets.
- Markov blankets and implied conditional independencies.
- Moralization, graph conversion, and structural transformations.
- Latent-variable annotations.
- Causal role annotations such as exposures, outcomes, confounders, mediators, and adjustment variables.
- Random graph generation and graph statistics.
- Import/export connections to DAGitty and lavaan representations.

D-separation deserves particular attention. It determines when a graph implies conditional independence, independent of the numerical probability parameters.

For example, in \\(X \rightarrow M \rightarrow Y\\), conditioning on \\(M\\) blocks the path between \\(X\\) and \\(Y\\). In \\(X \rightarrow M \leftarrow Y\\), conditioning on the collider \\(M\\) can instead open a statistical association between \\(X\\) and \\(Y\\).

This permits structural checks without requiring a full distribution to be fitted.

ADMGs add important functionality: `get_district`, `get_ancestral_graph`, `get_markov_blanket`, `is_mconnected`, `is_mseparated`, and `to_dag`. Bidirected edges represent dependencies associated with latent common causes, and `to_dag` can introduce explicit latent variables to represent them.

These operations make mixed graphs useful analytical structures in their own right. They should not, however, be assumed to support every Bayesian-network inference or causal-identification algorithm merely because the representation exists.

Source: [https://pgmpy.org/api/base.html](https://pgmpy.org/api/base.html?utm_source=chatgpt.com)

### 2.2 Probabilistic model families

| Model                           | Core semantics                                                                  | Especially useful for                                                           |
| ------------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `DiscreteBayesianNetwork`       | Directed factorization into finite-state conditional probability tables         | Diagnostics, discrete uncertain states, classification, decision-support models |
| `LinearGaussianBayesianNetwork` | Directed linear conditional relationships with Gaussian noise                   | Continuous dependency systems, covariance propagation, linear structural models |
| `FunctionalBayesianNetwork`     | Arbitrary distribution-valued conditional functions backed by Pyro              | Nonlinear, non-Gaussian, mixed discrete/continuous generative models            |
| `DynamicBayesianNetwork`        | A repeating temporal Bayesian-network structure                                 | State transitions, time-dependent stochastic processes                          |
| `NaiveBayes`                    | Restricted Bayesian-network structure with conditionally independent predictors | Classification with learned discrete distributions                              |
| `DiscreteMarkovNetwork`         | Undirected graph with clique/factor potentials                                  | Symmetric dependencies, constrained probabilistic systems                       |
| `FactorGraph`                   | Bipartite graph connecting variables and factors                                | Explicit factorization and message-passing formulations                         |
| `JunctionTree` / `ClusterGraph` | Clusters of variables connected through separator structures                    | Exact inference and decomposition                                               |
| `MarkovChain`                   | Finite-state transition kernels                                                 | Sequential stochastic simulation and stationary behavior                        |
| `SEM`, `SEMGraph`, `SEMAlg`     | Structural equation models in graphical and algebraic forms                     | Latent-variable modeling, covariance structures, structural relationships       |

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy

+2

#### Discrete Bayesian networks

A discrete Bayesian network represents the joint distribution as:

\\[ P(X_1,\ldots,X_n)=\prod\_{i=1}^{n}P(X_i\mid\operatorname{Pa}(X_i)) \\]

The graph establishes the factorization; individual `TabularCPD` objects provide each conditional distribution.

This separation offers several architectural benefits:

- Each local distribution can be inspected or re-estimated independently.
- Conditional independence is represented structurally instead of being replicated across probability calculations.
- Inference algorithms can exploit sparsity in graph connectivity.
- The same parameterized graph can support posterior inference, conditional prediction, interventions, and simulation.

The relevant complexity is driven not just by the number of variables, but by variable cardinalities, parent configurations, and graph connectivity.

#### Linear Gaussian Bayesian networks

`LinearGaussianBayesianNetwork` models continuous variables through conditional Gaussian distributions:

\\[ X_i=\beta\_{i0}+\sum\_{j\in\operatorname{Pa}(i)} \beta\_{ij}X_j+\epsilon_i \\]

with Gaussian residuals.

It supports CPD validation, fitting, prediction, simulation, log-likelihood calculation, and persistence. Version 1.1 expanded these capabilities, including interventions, evidence, virtual interventions, and missing-data simulation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy

+1



Because it belongs to a parametric continuous family, it can be more compact than a discretized model. That benefit comes with assumptions of linearity and Gaussian residual structure.

#### Functional Bayesian networks

This is one of pgmpy's most consequential advanced capabilities.

`FunctionalBayesianNetwork` uses `FunctionalCPD` objects whose functions return Pyro distributions. The family can therefore represent mixtures of discrete and continuous variables, nonlinear relationships, and non-Gaussian uncertainty without constructing enormous tabular CPDs.

Capabilities include:

- Generative functions using Pyro distributions.
- Vectorized CPD evaluation.
- Simulation from mixed and nonlinear models.
- Hard and stochastic interventions.
- Parameter fitting through stochastic variational inference (SVI).
- Bayesian parameter inference through MCMC, using Pyro's NUTS machinery.

The crucial distinction is that pgmpy supplies the graph/model abstraction, while PyTorch and Pyro supply the differentiable probabilistic computation and associated inference machinery.

The normal discrete variable-elimination algorithms should not be assumed to apply directly to arbitrary functional distributions.

Sources:

[https://pgmpy.org/api/generated/models/pgmpy.models.FunctionalBayesianNetwork.html](https://pgmpy.org/api/generated/models/pgmpy.models.FunctionalBayesianNetwork.html?utm_source=chatgpt.com)

[https://pgmpy.org/api/generated/factors/pgmpy.factors.hybrid.FunctionalCPD.html](https://pgmpy.org/api/generated/factors/pgmpy.factors.hybrid.FunctionalCPD.html?utm_source=chatgpt.com)

### 2.3 Factors and conditional probability distributions

pgmpy exposes probability representations as first-class objects, including:

| Primitive                      | Function                                               |
| ------------------------------ | ------------------------------------------------------ |
| `DiscreteFactor`               | Multidimensional potential over finite-state variables |
| `TabularCPD`                   | Normalized conditional probability table               |
| `JointProbabilityDistribution` | Explicit finite joint distribution                     |
| `NoisyORCPD`                   | Compact binary causal-influence model                  |
| `LinearGaussianCPD`            | Linear Gaussian conditional distribution               |
| `FunctionalCPD`                | Executable conditional distribution                    |
| `FactorSet`                    | Collection of discrete factors                         |
| `FactorDict`                   | Dictionary-oriented factor container                   |

The factor layer supports operations such as factor multiplication, division, reduction by evidence, marginalization, normalization, and reordering of variables.

These operations are the foundation for inference algorithms.

`NoisyORCPD` is especially useful when multiple approximately independent binary causes can activate an outcome. It can replace a full conditional table with one influence parameter per cause, subject to the noisy-OR modeling assumptions.

`FactorSet` and `factor_sum_product` expose algebraic operations directly, making it possible to express factor-product and elimination calculations without manually constructing multidimensional probability arrays.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy



Source: [https://pgmpy.org/api/factors.html](https://pgmpy.org/api/factors.html?utm_source=chatgpt.com)

### 2.4 Model consistency versus statistical validity

`check_model()` verifies model-level consistency, including applicable CPD-parent agreement, state cardinalities, and probability normalization.

That validation is important but narrowly scoped. It does not establish that:

- The graph correctly represents a real-world causal process.
- Estimated parameters are statistically reliable.
- Unobserved confounding has been addressed.
- The intended causal effect is identifiable.
- The model will generalize to new data.

The distinction matters because pgmpy supports both structural validation and empirical evaluation, and those are different operations.

Source: [https://pgmpy.org/guides/custom_model.html](https://pgmpy.org/guides/custom_model.html?utm_source=chatgpt.com)

## 3. Structure learning and causal discovery

Structure learning is the process of inferring a graph from observations. In pgmpy, it spans several fundamentally different algorithm families rather than a single approach to searching over directed graphs.

### 3.1 Discovery algorithms

| Algorithm          | Mechanism                                                                                    | Strengths and important limitations                                                                                          |
| ------------------ | -------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `PC`               | Constraint-based discovery through conditional-independence tests and edge-orientation rules | Makes statistical independence assumptions explicit; sensitive to CI-test reliability, sample size, and faithfulness         |
| `HillClimbSearch`  | Greedy add/delete/reverse edge search guided by a structure score                            | Flexible, easy to constrain, but can converge to local optima                                                                |
| `GES`              | Greedy equivalence search using score improvements over graph equivalence classes            | Avoids treating every observationally equivalent DAG as a distinct hypothesis; depends on score assumptions                  |
| `MmhcEstimator`    | Max-min hill climbing: constraint-based candidate selection followed by score-based search   | Restricts the search space before optimization; principally documented for discrete data                                     |
| `TreeSearch`       | Chow–Liu trees and tree-augmented naïve Bayes structures                                     | Efficient restricted-family learning; cannot represent arbitrary network topology                                            |
| `ExhaustiveSearch` | Enumerates DAG structures and evaluates their scores                                         | Useful for small problems and reference comparisons; combinatorial cost makes it impractical at scale                        |
| `ExpertInLoop`     | Combines statistical discovery with human- or LLM-supplied edge orientation                  | Allows knowledge that is unavailable in observational statistics to influence structure; expert decisions remain assumptions |

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy

+1

The current discovery interface exposes `fit(X)`, `causal_graph_`, `adjacency_matrix_`, and `score(...)`. This offers a common way to fit and inspect algorithms despite their different statistical foundations.

PC is particularly important when interpretability of the discovered dependence structure matters. It first identifies an undirected skeleton using CI tests, records separating sets, and then applies orientation rules. It supports original, stable, and parallel variants, significance thresholds, conditioning-set limits, and different return types.

Returning a DAG when the data only identify a partially directed equivalence class does not mean the remaining causal orientations have become statistically identifiable. The distinction between DAG and CPDAG/PDAG output must survive downstream processing.

GES searches over equivalence-class representations using forward, backward, and turning operations. Its score-based character is different from PC's sequence of CI decisions, making the two useful for comparing how sensitive structural conclusions are to modeling assumptions.

HillClimbSearch provides controls such as initial graph, tabu search, maximum indegree, score choice, and expert constraints. These reduce the need for a bespoke graph-edit search loop.

TreeSearch is a useful alternative when a restricted dependency topology is acceptable. A Chow–Liu model represents a tree-structured approximation of a joint distribution, while a tree-augmented naïve Bayes model adds dependencies among predictive features under a class variable.

Sources:

[https://pgmpy.org/api/structure_learning.html](https://pgmpy.org/api/structure_learning.html?utm_source=chatgpt.com)

[https://pgmpy.org/api/generated/structure_learning/pgmpy.causal_discovery.PC.html](https://pgmpy.org/api/generated/structure_learning/pgmpy.causal_discovery.PC.html?utm_source=chatgpt.com)

[https://pgmpy.org/api/generated/structure_learning/pgmpy.causal_discovery.GES.html](https://pgmpy.org/api/generated/structure_learning/pgmpy.causal_discovery.GES.html?utm_source=chatgpt.com)

[https://pgmpy.org/api/generated/structure_learning/pgmpy.causal_discovery.HillClimbSearch.html](https://pgmpy.org/api/generated/structure_learning/pgmpy.causal_discovery.HillClimbSearch.html?utm_source=chatgpt.com)

### 3.2 Conditional-independence testing

pgmpy treats CI tests as reusable statistical primitives. The available families include:

| Data/assumption family                    | Tests                                                                           |
| ----------------------------------------- | ------------------------------------------------------------------------------- |
| Discrete                                  | `ChiSquare`, `GSq`, `LogLikelihood`, `ModifiedLogLikelihood`, `PowerDivergence` |
| Continuous, correlation-based             | `FisherZ`, `Pearsonr`, `PearsonrEquivalence`                                    |
| Mixed discrete/continuous                 | `PillaiTrace`                                                                   |
| Generalized conditional independence      | `GCM`                                                                           |
| Known symbolic independence relationships | `IndependenceMatch`                                                             |

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy

Two less obvious distinctions are consequential.

First, a failure to reject dependence is not generally evidence of independence. Equivalence-testing approaches such as `PearsonrEquivalence` address a different statistical hypothesis than ordinary correlation significance tests.

Second, the choice of CI test affects the graph that discovery can recover. Correlation-based testing is not a general test for nonlinear dependence, while discrete contingency-based tests may perform poorly when conditioning sets create sparse cells.

The `GCM` implementation broadens the available methodology by testing generalized covariance after regression-based residualization. It is useful to investigate when linear correlation assumptions would be restrictive, although the regression models and their adequacy become part of the inference assumptions.

The 1.1.2 release also introduced CI-test effect-size capabilities and caching-related improvements. Caching repeated tests can matter during discovery because searches revisit related variable and conditioning-set combinations.

Source: [https://pgmpy.org/api/ci_test.html](https://pgmpy.org/api/ci_test.html?utm_source=chatgpt.com)

### 3.3 Structure scoring

pgmpy implements local decomposable structure scores, including:

| Data type                  | Score families                                |
| -------------------------- | --------------------------------------------- |
| Discrete                   | K2, BDeu, BDs, log-likelihood, AIC, BIC       |
| Continuous Gaussian        | Gaussian log-likelihood, AIC, BIC             |
| Mixed conditional Gaussian | Conditional-Gaussian log-likelihood, AIC, BIC |

The score family affects which graph structures are statistically preferred.

- Log-likelihood rewards data fit and can favor excessive complexity without a compensating penalty.
- AIC/BIC balance fit against parameter complexity using different penalty principles.
- BDeu/BDs/K2 bring Bayesian score assumptions and priors into structure selection.
- Conditional Gaussian scores allow mixed-type structure evaluation under a restricted distribution family; this is not equivalent to arbitrary mixed probabilistic modeling.

`BaseStructureScore` and the score-selection utilities provide extension points for domain-specific scoring. Local score decompositions also make it possible for search algorithms to recalculate only affected families following a graph edit, rather than rescoring the entire model.

Source: [https://pgmpy.org/api/structure_score.html](https://pgmpy.org/api/structure_score.html?utm_source=chatgpt.com)

### 3.4 Expert knowledge as a structural constraint

`ExpertKnowledge` supports four major constraint types:

- Required edges.
- Forbidden edges.
- Temporal tiers or partial temporal ordering.
- A restricted set of candidate edges (`search_space`).

These constraints can encode physical impossibilities, known precedence relationships, or externally established dependencies. They can also reduce computational expense by shrinking the candidate structure space.

The distinction between knowledge as a hard constraint and knowledge as an initial hypothesis is important: required and forbidden edges affect what the algorithm is permitted to return, rather than merely influencing a score.

`ExpertInLoop` adds a separate mechanism for resolving potential orientations through human or LLM input. This is not a statistical guarantee of causal correctness; the resulting model incorporates the reliability and provenance of those supplied judgments.

Sources:

[https://pgmpy.org/guides/causal_discovery.html](https://pgmpy.org/guides/causal_discovery.html?utm_source=chatgpt.com)

[https://pgmpy.org/api/generated/structure_learning/pgmpy.causal_discovery.ExpertKnowledge.html](https://pgmpy.org/api/generated/structure_learning/pgmpy.causal_discovery.ExpertKnowledge.html?utm_source=chatgpt.com)

[https://pgmpy.org/api/generated/structure_learning/pgmpy.estimators.ExpertInLoop.html](https://pgmpy.org/api/generated/structure_learning/pgmpy.estimators.ExpertInLoop.html?utm_source=chatgpt.com)

### 3.5 What discovery does and does not establish

Observational data generally identify causal structure only under additional assumptions about such matters as confounding, acyclicity, Markov properties, faithfulness, functional relationships, and sample adequacy.

In particular, several DAGs can encode the same set of observational conditional independencies. A score-optimal graph or a graph returned by PC is therefore not automatically the uniquely established causal mechanism.

pgmpy's separation between graph discovery, expert constraints, causal identification, and effect estimation is valuable precisely because those questions are not equivalent.

## 4. Parameter estimation and model fitting

Once a structure is specified, pgmpy can estimate its distributional parameters. Parameter fitting is distinct from structure discovery: the former estimates probabilities or numerical coefficients conditional on the chosen graph.

### 4.1 Discrete estimation

| Estimator                   | Mechanism                           | Primary distinction                                                    |
| --------------------------- | ----------------------------------- | ---------------------------------------------------------------------- |
| `DiscreteMLE`               | Frequency-based maximum likelihood  | Straightforward estimates; can produce zero-probability configurations |
| `DiscreteBayesianEstimator` | Dirichlet-prior posterior estimates | Smoothing and control over prior beliefs                               |
| `DiscreteEM`                | Iterative expectation-maximization  | Latent-variable or incomplete-data estimation                          |

The current release exposes these classes through `pgmpy.parameter_estimator`. They have a model/data fitting interface and learned `parameters_` results.

There is a version-sensitive API distinction worth preserving: much of the public parameter-estimation guide still illustrates `model.fit(..., estimator=MaximumLikelihoodEstimator)` and the earlier `pgmpy.estimators` classes. Both interfaces appear in the 1.1.2 codebase and documentation; the newer `DiscreteMLE`, `DiscreteBayesianEstimator`, and `DiscreteEM` interfaces should not be confused with those legacy names.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



The main numerical and statistical issues are:

- Sparse configurations: An observed dataset may contain only a subset of combinations of parent states. Explicit `state_names` prevent the apparent domain from being silently reduced to observed states.
- Prior smoothing: Dirichlet pseudo-counts can avoid brittle zero-frequency estimates, but change the fitted distribution according to the prior.
- Incomplete observations: Expectation-maximization alternates estimating latent or missing-state distributions and updating parameters; convergence need not imply a global optimum.
- Computational granularity: CPDs are locally parameterized. Independent family estimation creates opportunities for parallel work, including the documented `n_jobs` support in model fitting.
- Large parent sets: A tabular CPD requires parameters for the combinations of parent states, so fitting and storage can grow exponentially with parent count.

### 4.2 Non-discrete estimation

`LinearGaussianMLE` estimates linear Gaussian CPDs from observations. This is naturally different from fitting a finite-state conditional probability table: it estimates regression coefficients and residual uncertainty.

For functional Bayesian networks, Pyro-backed fitting enables parameterized nonlinear distributions with variational or MCMC inference. In that case, optimization, priors, differentiability, and convergence behavior are determined partly by the supplied probabilistic functions and Pyro configuration.

pgmpy also provides `SEMEstimator`, `IVEstimator`, and `MirrorDescentEstimator` for additional model families:

- Structural equation models: fitting covariance and structural relations.
- Instrumental-variable models: estimators designed around identified instruments.
- Undirected models: mirror-descent-based parameter estimation from marginal information.

These are specialized mechanisms, not drop-in replacements for discrete Bayesian-network estimators.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy



Sources:

[https://pgmpy.org/guides/parameter_estimation.html](https://pgmpy.org/guides/parameter_estimation.html?utm_source=chatgpt.com)

[https://github.com/pgmpy/pgmpy/tree/v1.1.2/pgmpy/parameter_estimator](https://github.com/pgmpy/pgmpy/tree/v1.1.2/pgmpy/parameter_estimator?utm_source=chatgpt.com)

[https://pgmpy.org/api/parameter_estimation.html](https://pgmpy.org/api/parameter_estimation.html?utm_source=chatgpt.com)

### 4.3 Modeling representations influence what can be learned

A significant architectural choice precedes selection of an estimator:

| Representation                  | Consequence                                                                                                                                     |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Discretized continuous variable | Compatible with discrete CPDs and inference, but loses within-bin information and may inflate state spaces                                      |
| Linear Gaussian CPD             | Compact numerical representation and continuous inference, but imposes linear/Gaussian assumptions                                              |
| Functional CPD                  | Flexible nonlinear/non-Gaussian distribution, but introduces probabilistic-programming dependencies and approximate inference requirements      |
| Noisy-OR CPD                    | Compact representation of binary influences, but imposes noisy-OR causal mechanism assumptions                                                  |
| Structural equation model       | Expresses structural coefficients, latent variables, and correlated disturbances, but has identification and estimation requirements of its own |

The choice is not merely about storage or syntax. It determines which assumptions the model makes, which algorithms can fit it, and what subsequent inference operations are available.

## 5. Probabilistic inference and computational mechanisms

pgmpy's inference functionality computes distributions, likelihoods, and likely assignments from a parameterized graphical model.

The central design distinction is between exact inference, which evaluates the model's probability distribution without sampling error, and approximate inference, which trades precision or guarantees for potentially more manageable computation.

### 5.1 Exact inference

| Algorithm                             | Supported mechanism                                                                   | When it is particularly relevant                      |
| ------------------------------------- | ------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| `VariableElimination`                 | Eliminates unqueried variables by multiplying and marginalizing factors               | General discrete posterior and MAP queries            |
| `BeliefPropagation`                   | Calibrates a junction-tree representation and propagates clique/separator information | Exact inference with reusable junction-tree structure |
| `BeliefPropagationWithMessagePassing` | Explicit factor-to-variable and variable-to-factor messages                           | Loop-free factor graphs                               |
| `DBNInference`                        | Specialized dynamic Bayesian-network inference                                        | Temporal posterior reasoning                          |

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy

#### Variable elimination

Given a query \\(Q\\), evidence \\(E=e\\), and hidden variables \\(H\\), the algorithm computes:

\\[ P(Q\mid E=e)\propto\sum_H\prod_i\phi_i \\]

where the \\(\phi_i\\) are local factors after incorporating evidence.

`VariableElimination` supports joint queries, separate marginals, MAP assignments, maximum marginals, and virtual evidence.

The particularly valuable advanced controls are:

- `elimination_order`: Explicit ordering or heuristic selection.
- `induced_graph(order)`: Inspection of graph fill-in caused by elimination.
- `induced_width(order)`: Measurement of the largest intermediate clique, minus one.
- `joint=True/False`: Choice between a joint returned factor and separate marginal distributions.

Elimination order is a major performance variable. The largest intermediate factor typically grows exponentially with the number and cardinalities of variables it contains. An inefficient order can make a relatively sparse model expensive even when the requested marginal is small.

pgmpy exposes `MinFill`, `WeightedMinFill`, `MinWeight`, and `MinNeighbors` heuristics. These can avoid writing custom ordering algorithms while allowing the factorization cost to be investigated directly.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy

+1



#### Junction-tree inference

A junction tree groups variables into cliques connected by separators satisfying the running-intersection property.

`BeliefPropagation` uses this transformed representation to perform exact probabilistic reasoning. It can be attractive when many related queries reuse a model, although building and calibrating a junction tree requires preprocessing and may be expensive for graphs with large cliques.

An exact junction-tree representation does not remove treewidth complexity. It reorganizes the computations; if the underlying graph induces large cliques, factor sizes remain the principal limitation.

#### Loop-free factor-graph message passing

`BeliefPropagationWithMessagePassing` is a separate implementation specialized for factor graphs without loops.

It exposes message calculations and can optionally return the computed messages alongside marginals. This can be useful for understanding which parts of a factorized model contribute to a posterior or for inspecting message-passing behavior.

It is not a general-purpose loopy belief-propagation engine: the documentation explicitly states that it does not work on loopy factor graphs.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy



Sources:

[https://pgmpy.org/guides/probabilistic_inference.html](https://pgmpy.org/guides/probabilistic_inference.html?utm_source=chatgpt.com)

[https://pgmpy.org/api/generated/inference/pgmpy.inference.VariableElimination.html](https://pgmpy.org/api/generated/inference/pgmpy.inference.VariableElimination.html?utm_source=chatgpt.com)

[https://pgmpy.org/api/generated/inference/pgmpy.inference.BeliefPropagationWithMessagePassing.html](https://pgmpy.org/api/generated/inference/pgmpy.inference.BeliefPropagationWithMessagePassing.html?utm_source=chatgpt.com)

### 5.2 Approximate inference and sampling

| Mechanism               | Role                                                                 | Principal considerations                                                      |
| ----------------------- | -------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `BayesianModelSampling` | Forward, rejection, and likelihood-weighted sampling                 | Evidence rarity and sampling variance                                         |
| `GibbsSampling`         | Iterative Markov-chain sampling from local conditional distributions | Mixing, autocorrelation, burn-in, convergence assessment                      |
| `ApproxInference`       | Sample-based approximate marginal inference                          | Accuracy depends on sample quality and count                                  |
| `Mplp`                  | Max-product linear-programming-style approximation                   | Discrete MAP optimization, rather than general posterior marginalization      |
| Pyro SVI/MCMC           | Inference for functional probabilistic models                        | Approximation families, differentiability, optimization and chain diagnostics |

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy

These methods solve different problems. For example, `Mplp` is relevant to a maximum-probability assignment problem, not a request for accurately normalized posterior probabilities for every state.

Likelihood weighting can be substantially more useful than naïve rejection sampling when conditioning on relatively unlikely evidence, but weight concentration may leave a low effective sample size.

Gibbs sampling can be appropriate where the required local conditionals are tractable. It introduces convergence and mixing considerations absent from exact enumeration.

The existence of an approximate inference method therefore does not remove the need to consider the structure and distribution family of the model.

### 5.3 MAP versus marginal inference

A frequently important distinction is:

\\[ \arg\max_q P(Q=q\mid E=e) \\]

versus

\\[ \arg\max\_{q,h}P(Q=q,H=h\mid E=e) \\]

The first selects the most probable assignment of the queried variables after marginalizing hidden variables. The second optimizes the joint assignment of both queried and hidden variables. These can produce different answers.

`map_query` is documented in terms of the marginal posterior over the requested variables. A full-network most probable explanation is a different query shape.

### 5.4 Factor graphs and undirected models

An undirected Markov network represents a joint distribution as:

\\[ P(X)=\frac{1}{Z}\prod\_{C}\psi_C(X_C) \\]

where \\(Z\\) is the partition function.

Unlike Bayesian networks, local clique potentials are not necessarily normalized conditional distributions.

`DiscreteMarkovNetwork` provides factor attachment, model validation, partition-function calculation, triangulation, and transformations into factor graphs and junction trees.

These capabilities are especially useful when the model naturally consists of symmetric local compatibility constraints rather than directed conditional mechanisms.

The normalization constant can itself be expensive to compute. Conversion to a factor graph exposes the factorization but does not magically reduce its intrinsic computational difficulty.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy



Source: [https://pgmpy.org/api/generated/undirected/pgmpy.models.DiscreteMarkovNetwork.html](https://pgmpy.org/api/generated/undirected/pgmpy.models.DiscreteMarkovNetwork.html?utm_source=chatgpt.com)

## 6. Temporal modeling, simulation, and synthetic data

### 6.1 Dynamic Bayesian networks

A `DynamicBayesianNetwork` describes repeated time-indexed dependence relationships using a two-time-slice template (2-TBN).

Its structure differentiates:

- Intra-slice edges: Dependencies among variables at the same time step.
- Inter-slice edges: Dependencies between consecutive time steps.
- Initial CPDs: Distributions defining the starting state.
- Transition CPDs: Conditional dynamics that repeat over the modeled time horizon.

Rather than manually constructing a fresh Bayesian network for every step, a DBN encodes the repeated structure directly.

pgmpy includes utilities for retrieving intra/inter-slice edges, obtaining a two-slice constant Bayesian network, initializing state CPDs, learning parameters, and performing inference using `DBNInference`.

A material limitation is that `DynamicBayesianNetwork.fit` is documented as supporting maximum-likelihood estimation, with observations pooled across consecutive two-slice windows under the stationary-template assumption. This is not a general-purpose temporal structure-discovery or nonlinear state-space estimation system.

The simulation interface supports `n_time_slices`, time-indexed evidence and interventions, and several useful output layouts:

| Return format   | Representation                                                       |
| --------------- | -------------------------------------------------------------------- |
| `wide`          | One row per simulated trace, columns identified by variable and time |
| `numpy3d`       | Three-dimensional NumPy array organized by trace, variable, and time |
| `pd-multiindex` | DataFrame with instance/time indexing                                |
| `pd-list`       | Per-trace DataFrames                                                 |
| `sorted`        | Sorted wide-style representation                                     |

This avoids bespoke reshaping for several common downstream analytical interfaces.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy

+1



Source: [https://pgmpy.org/api/generated/models/pgmpy.models.DynamicBayesianNetwork.html](https://pgmpy.org/api/generated/models/pgmpy.models.DynamicBayesianNetwork.html?utm_source=chatgpt.com)

### 6.2 Markov chains versus dynamic Bayesian networks

`MarkovChain` is a more restricted model centered on finite-state transition kernels. It is useful for transition simulation, trajectories, and stationary-distribution questions.

A DBN can represent multiple interacting variables per time slice and both contemporaneous and cross-time dependencies.

Thus, Markov chains offer a compact abstraction for simple state-transition systems; DBNs become valuable when a state decomposes into multiple interacting random variables.

### 6.3 Interventional and conditional simulation

The `simulate(...)` API supports much more than unconditional forward sampling.

| Operation              | Semantics                                                 |
| ---------------------- | --------------------------------------------------------- |
| Unconditional sampling | Draw from the represented joint distribution              |
| `evidence`             | Condition the sample distribution on observed values      |
| `do`                   | Force variable values through a hard intervention         |
| `virtual_evidence`     | Introduce probabilistic evidence about a variable         |
| `virtual_intervention` | Replace or alter the targeted mechanism probabilistically |
| `missing_prob`         | Introduce missingness into generated observations         |
| `include_latents`      | Control whether latent values appear in results           |
| `partial_samples`      | Supply partially specified sample values                  |

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy

These distinctions are causally significant. Conditioning on \\(X=x\\) and forcing \\(X=x\\) generally produce different distributions:

\\[ P(Y\mid X=x)\ne P(Y\mid do(X=x)) \\]

A hard intervention removes the variable's original generating mechanism and replaces it with the supplied value. Evidence leaves the original mechanism intact and conditions on observing its outcome.

Virtual evidence and virtual intervention are also different: the former changes what is known about a variable, while the latter changes how it is generated.

The ability to generate observational and interventional datasets from the same model enables controlled comparisons, including model-estimator evaluation under known synthetic ground truth.

Such generated data provide ground truth relative to the assumed model, not independent evidence that the model represents the real system.

Source: [https://pgmpy.org/guides/simulations.html](https://pgmpy.org/guides/simulations.html?utm_source=chatgpt.com)

## 7. Causal identification, inference, and effect estimation

This is one of pgmpy's most important areas of development in the 1.1.x releases.

It provides a progression from causal graph → identification → effect estimation or interventional inference, with separate APIs for each stage.

### 7.1 Causal identification

Causal identification determines whether an intervention effect can be expressed using the available observational distribution, given an assumed causal structure.

For example, consider:

\\[ Z\rightarrow X,\quad Z\rightarrow Y,\quad X\rightarrow Y \\]

Here \\(Z\\) is a common cause of treatment \\(X\\) and outcome \\(Y\\).

Under the appropriate causal assumptions, the adjustment formula is:

\\[ P(Y\mid do(X=x)) = \sum_z P(Y\mid X=x,Z=z)P(Z=z) \\]

pgmpy's `pgmpy.identification` package implements identification and validation workflows for this kind of reasoning.

| Mechanism                   | Function                                                                    |
| --------------------------- | --------------------------------------------------------------------------- |
| `Adjustment`                | Identify variables satisfying the graphical adjustment criterion            |
| Minimal adjustment          | Find a sufficient set without unnecessary adjustment variables              |
| All adjustment sets         | Enumerate qualifying alternatives                                           |
| Variance-optimal adjustment | Select a set using an efficiency-oriented criterion                         |
| `Frontdoor`                 | Identify a suitable mediated route when adjustment is unavailable           |
| `validate(...)`             | Check whether designated variables satisfy the relevant graphical criterion |

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy

The interface uses graph-embedded roles, including `exposures`, `outcomes`, and `adjustment`. This makes the output more useful than a detached list of node names: downstream logic can consume a graph that carries the interpretation of its variables.

Important boundary: These are concrete identification mechanisms, not evidence that pgmpy implements a complete general identification algorithm for every identifiable effect in every mixed causal graph.

Moreover, the existence of a frontdoor or adjustment set depends on the assumed graph being appropriate. Identification is a mathematical consequence of assumptions about that graph, not empirical proof of those assumptions.

Source: [https://pgmpy.org/guides/causal_identification.html](https://pgmpy.org/guides/causal_identification.html?utm_source=chatgpt.com)

### 7.2 Causal inference over fitted probabilistic models

`CausalInference` can compute interventional distributions over fitted discrete Bayesian networks.

For example:

```
from pgmpy.inference import CausalInferencecausal = CausalInference(model)result = causal.query(    variables=["Y"],    do={"X": 1},    evidence={"Z": 0},)
```

This combines intervention semantics with conditioning on additional observations.

It is different from:

```
from pgmpy.inference import VariableEliminationobservational = VariableElimination(model).query(    variables=["Y"],    evidence={"X": 1, "Z": 0},)
```

The second query conditions on observing \\(X=1\\); the first actively intervenes on \\(X\\).

For a model with confounding or selection relationships, they need not agree.

`CausalInference.estimate_ate(...)` additionally supports estimating average treatment effects from data, using graph-based adjustment.

Source: [https://pgmpy.org/guides/causal_estimation.html](https://pgmpy.org/guides/causal_estimation.html?utm_source=chatgpt.com)

### 7.3 Regression-based causal estimation

The `pgmpy.prediction` package is a substantial complement to its graphical inference engines.

| Estimator                  | Mechanism                                                                                                       | Important boundaries                                                                            |
| -------------------------- | --------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `NaiveAdjustmentRegressor` | Fits a supervised estimator using exposure, adjustment, and pretreatment variables selected through graph roles | Prediction quality alone does not validate a causal effect                                      |
| `NaiveIVRegressor`         | Two-stage instrumental-variable-style estimation                                                                | Requires instrument relevance and exclusion/exogeneity assumptions                              |
| `DoubleMLRegressor`        | Cross-fitting, nuisance estimation, residualization, and final effect estimation                                | Statistical guarantees depend on causal assumptions, nuisance quality, and final estimator form |

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy

+3

#### Double machine learning

`DoubleMLRegressor` implements the DML2 approach.

For an outcome \\(Y\\), treatment \\(T\\), and observed adjustment variables \\(X\\), the broad procedure is:

1. Estimate \\(E[Y\mid X]\\) using an outcome nuisance model.
2. Estimate \\(E[T\mid X]\\) using a treatment nuisance model.
3. Obtain out-of-fold residuals through cross-fitting.
4. Regress outcome residuals against treatment residuals to estimate the treatment relationship.

Cross-fitting reduces the effects of overfitting nuisance models by separating the data used for prediction from the data used to fit those models.

The implementation exposes:

- `nuisance_estimators`: Custom scikit-learn-compatible models for the treatment and outcome nuisance regressions.
- `effect_estimator`: The final model fitted to residualized variables.
- `n_folds`: Cross-fitting partition count.
- `seed`: Reproducible cross-fitting splits.
- Learned nuisance estimators and variable-role information.

An important documented qualification is that allowing an arbitrary nonlinear final effect estimator does not imply that the theoretical DoubleML guarantees still hold. The upstream documentation associates those guarantees with a linear final effect model.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy



The integration opportunity is significant: graph role annotations determine which variables have causal roles, while mature scikit-learn estimators supply the statistical learning machinery. This can eliminate separate, manually maintained feature-selection logic for each estimation workflow.

#### Instrumental-variable estimation

`NaiveIVRegressor` provides a two-stage estimation mechanism for a single exposure, a single outcome, and one or more instruments.

It accepts interchangeable first- and second-stage regressors and can incorporate pretreatment covariates.

Its usefulness depends on substantive instrumental-variable assumptions. A graph annotation that labels a variable as an instrument does not establish that the instrument is valid or strong.

Sources:

[https://pgmpy.org/api/generated/causal_inference/pgmpy.prediction.DoubleMLRegressor.DoubleMLRegressor.html](https://pgmpy.org/api/generated/causal_inference/pgmpy.prediction.DoubleMLRegressor.DoubleMLRegressor.html?utm_source=chatgpt.com)

[https://pgmpy.org/api/generated/causal_inference/pgmpy.prediction.NaiveIVRegressor.NaiveIVRegressor.html](https://pgmpy.org/api/generated/causal_inference/pgmpy.prediction.NaiveIVRegressor.NaiveIVRegressor.html?utm_source=chatgpt.com)

[https://pgmpy.org/api/generated/causal_inference/pgmpy.prediction.NaiveAdjustmentRegressor.NaiveAdjustmentRegressor.html](https://pgmpy.org/api/generated/causal_inference/pgmpy.prediction.NaiveAdjustmentRegressor.NaiveAdjustmentRegressor.html?utm_source=chatgpt.com)

### 7.4 Structural equation modeling

The structural equation modeling functionality deserves treatment as its own model family rather than as a synonym for Bayesian networks.

`SEMGraph`, `SEMAlg`, and `SEM` support graphical and algebraic descriptions of structural relationships involving observed and latent variables.

`SEMGraph` distinguishes:

- Structural directed edges and associated coefficients.
- Observed versus latent variables.
- Correlated error terms through `err_corr`.
- Error variances through `err_var`.
- The main structural graph from the separate error-dependence graph.

This is important when latent constructs, measurement relationships, or correlated disturbances are part of the model.

The `SEMEstimator` implementation constructs an implied covariance matrix from structural coefficients and disturbance covariance, and implements fitting objectives including maximum likelihood and least-squares forms.

The source establishes a consequential dependency requirement: `SEMEstimator` requires the PyTorch backend and raises an error when the NumPy backend is selected.

Structural equation modeling is not interchangeable with functional Bayesian-network modeling. SEM focuses on structured algebraic and covariance relationships; functional Bayesian networks allow arbitrary Pyro-backed conditional distribution functions.

Sources:

[https://pgmpy.org/api/generated/models/pgmpy.models.SEMGraph.html](https://pgmpy.org/api/generated/models/pgmpy.models.SEMGraph.html?utm_source=chatgpt.com)

[https://pgmpy.org/api/parameter_estimation.html](https://pgmpy.org/api/parameter_estimation.html?utm_source=chatgpt.com)

[https://pgmpy.org/\_modules/pgmpy/estimators/SEMEstimator.html](https://pgmpy.org/_modules/pgmpy/estimators/SEMEstimator.html?utm_source=chatgpt.com)

## 8. Evaluation, diagnostics, and reference datasets

### 8.1 Graph evaluation versus statistical evaluation

pgmpy offers several distinct ways of evaluating a learned model.

| Evaluation                       | API                          | Question answered                                                                      |
| -------------------------------- | ---------------------------- | -------------------------------------------------------------------------------------- |
| Structural Hamming distance      | `SHD`                        | How many structural edits separate an estimated graph from a reference?                |
| Skeleton accuracy                | `AdjacencyConfusionMatrix`   | Which adjacencies were detected or missed?                                             |
| Orientation accuracy             | `OrientationConfusionMatrix` | Were directed relationships oriented correctly?                                        |
| Conditional-dependence agreement | `CorrelationScore`           | How well does the graph's dependence structure agree with observations?                |
| Implied independence tests       | `ImpliedCIs`                 | Do the conditional independencies encoded by the graph hold empirically?               |
| Global independence diagnostics  | `FisherC`                    | Is the graph's implied independence structure statistically compatible with data?      |
| Structure scores                 | `StructureScore`             | How does the graph score under a specified statistical model and complexity criterion? |

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy

The distinction between supervised and unsupervised metrics is fundamental.

Supervised structural evaluation requires a reference graph. It can measure adjacency and orientation recovery but says little by itself about predictive calibration.

Unsupervised statistical evaluation uses observed data to assess the graph's implications. It cannot establish that an observationally equivalent causal orientation is correct.

The metric registry is discoverable through `get_metrics(...)`, with metadata filters such as `requires_true_graph` and `requires_data`.

This enables dynamically assembled evaluation workflows without a bespoke registry of every metric class.

Additional diagnostic opportunities include examining separating sets from PC, investigating evidence probabilities, inspecting learned CPDs, testing model consistency, and comparing simulation outputs under known synthetic interventions.

Source: [https://pgmpy.org/guides/metrics.html](https://pgmpy.org/guides/metrics.html?utm_source=chatgpt.com)

### 8.2 Example datasets

The `pgmpy.datasets` package exposes a structured dataset registry:

```
from pgmpy.datasets import list_datasets, load_datasetnames = list_datasets(    is_discrete=True,    has_ground_truth=True,)dataset = load_dataset(names[0])
```

A loaded dataset provides more than observations:

- `data`: pandas DataFrame.
- `ground_truth`: Reference graph, when available.
- `expert_knowledge`: Associated structural constraints, when available.
- `tags`: Dataset metadata.

Registry filters include data type, sample count, variable count, simulated/interventional status, and available reference information.

Version 1.1 moved example dataset and model loading toward externally hosted registries, including Hugging Face-backed sources. Therefore, data acquisition, caching, and reproducibility should be distinguished from the local algorithm implementation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy

+1



Source: [https://pgmpy.org/guides/datasets.html](https://pgmpy.org/guides/datasets.html?utm_source=chatgpt.com)

### 8.3 Example models

`pgmpy.example_models` provides `list_models(...)` and `load_model(...)`.

The registry includes discrete Bayesian networks, continuous models, and structure-only graphs sourced from collections such as bnlearn, bnrep, and DAGitty.

This is useful for constructing reproducible comparisons between:

- Learned and reference structures.
- Exact and approximate inference.
- Different discovery algorithms.
- Different structure scores.
- Observational and interventional queries.

Not every returned example model is fully parameterized. A structure-only graph must acquire the relevant distributional model and parameters before ordinary probabilistic inference or simulation.

Source: [https://pgmpy.org/guides/example_models.html](https://pgmpy.org/guides/example_models.html?utm_source=chatgpt.com)

## 9. Integration, extensibility, and engineering boundaries

### 9.1 Ecosystem integration

| Ecosystem component   | Relationship to pgmpy                                                                      |
| --------------------- | ------------------------------------------------------------------------------------------ |
| NetworkX              | Underlying graph operations, structural manipulation, and graph-algorithm interoperability |
| NumPy                 | Array operations, probability tables, and numerical computation                            |
| pandas                | Primary representation of observational and generated datasets                             |
| SciPy                 | Numerical and statistical routines underlying multiple algorithms                          |
| scikit-learn          | Estimator compatibility and interchangeable causal-prediction/nuisance regressors          |
| PyTorch               | Optional tensor backend and differentiable numerical computation                           |
| Pyro                  | Functional CPDs, stochastic variational inference, and MCMC                                |
| Graphviz / PyGraphviz | Layout and rendered graph diagrams                                                         |
| daft                  | Publication-style graphical model diagrams                                                 |
| LiteLLM               | Optional integration for LLM-assisted expert-in-the-loop discovery                         |
| Hugging Face Hub      | Registry-backed example dataset/model retrieval                                            |

These relationships are not all equivalent.

NetworkX supports graph structure but does not implement pgmpy's probabilistic semantics. PyTorch supplies numerical computation, while Pyro supplies probabilistic-programming and approximate-inference capabilities. A scikit-learn estimator supplies a predictive function, not its own causal identification logic.

Keeping those boundaries explicit avoids attributing an ecosystem library's capabilities to every pgmpy model.

### 9.2 Numerical backends and optional dependencies

pgmpy supports NumPy and PyTorch-oriented numerical configurations.

The PyTorch backend is especially relevant for functionality that requires differentiable parameters or tensor operations, including SEM fitting and Pyro-backed functional models.

Backend settings are exposed through `pgmpy.config`, including `set_backend("torch")`. The release also includes device- and dtype-related configuration. Backend choice is not merely a performance hint: for some functionality it is a prerequisite.

The PyTorch/Pyro relationship should not be interpreted as a promise that all pgmpy algorithms are GPU-accelerated, or that switching to CUDA will accelerate graph search, pandas-oriented preprocessing, or arbitrary inference routines.

Official installation extras are:

| Extra      | Scope                                                                           |
| ---------- | ------------------------------------------------------------------------------- |
| Base       | Core pgmpy functionality                                                        |
| `torch`    | PyTorch and Pyro                                                                |
| `optional` | Torch plus optional integrations such as daft, XGBoost, LiteLLM, and PyGraphviz |
| `tests`    | Test and development dependencies                                               |
| `docs`     | Documentation toolchain                                                         |
| `all`      | Combined extras                                                                 |

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy

+2

Source: [https://pgmpy.org/started/install.html](https://pgmpy.org/started/install.html?utm_source=chatgpt.com)

### 9.3 Model import, export, and representation conversion

pgmpy includes model-level `save(...)` and `load(...)` methods, alongside format-specific readers and writers.

Available interchange families include:

- BIF.
- Hugin NET.
- XMLBIF.
- GeNIe XDSL.
- XBN.
- UAI.
- PomdpX.

These allow reuse of existing Bayesian-network models, exchanging models with graphical editing tools, and persisting model structures and conditional probability tables.

The dedicated classes in `pgmpy.readwrite` offer more granular parsing and serialization controls.

However, format support should not be confused with universal round-trip preservation.

A format designed for discrete Bayesian networks may not encode the semantics of functional Pyro CPDs, structural equation models, causal role annotations, or every form of mixed graph.

State names, cardinalities, parameter ordering, and metadata preservation deserve explicit verification when converting between formats. Version 1.1 introduced warnings for comma-containing state names in several writers, which illustrates that even relatively ordinary serialization details can be semantically important.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy

+2



Sources:

[https://pgmpy.org/guides/io.html](https://pgmpy.org/guides/io.html?utm_source=chatgpt.com)

[https://pgmpy.org/api/readwrite.html](https://pgmpy.org/api/readwrite.html?utm_source=chatgpt.com)

### 9.4 Visualization

The graphical model objects expose several visualization routes.

`to_graphviz()` produces a PyGraphviz representation suited to automatic layout and PNG, SVG, or PDF output.

`to_daft()` supports publication-style diagrams.

Direct NetworkX compatibility supports plotting and structural inspection through existing graph tools.

The 1.1.x releases also expanded edge-strength annotations and conversion helpers such as `to_dagitty()` and `to_lavaan()`, connecting pgmpy graphs to other causal and structural modeling ecosystems.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy

+1



Source: [https://pgmpy.org/guides/plotting.html](https://pgmpy.org/guides/plotting.html?utm_source=chatgpt.com)

### 9.5 Extensibility and internal interfaces

pgmpy provides several practical extension seams:

| Extension surface          | Mechanism                                                         |
| -------------------------- | ----------------------------------------------------------------- |
| New discovery algorithm    | Implement the estimator pattern, exposing fit results and scoring |
| Custom structure objective | Subclass the structure-score abstraction                          |
| Custom CI test             | Supply a test compatible with the relevant discovery API          |
| New parameter estimator    | Reuse model and estimator abstractions                            |
| New factor/CPD             | Represent a different local probability mechanism                 |
| Custom metric              | Integrate through the metric interface and registry               |
| Dataset or example model   | Implement compatible metadata and loading interfaces              |
| Pyro distributions         | Define new functional conditional distributions using Pyro        |

The repository contains extension templates under `devtools/extension_templates/`.

The documented extension process is largely source/package-oriented: implement the class in the appropriate namespace, expose it in the package exports, and add tests and documentation.

This is a conventional Python extension pattern, not evidence of a fully automatic external plugin system that discovers arbitrary installed third-party packages.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy



Source: [https://pgmpy.org/guides/extensibility.html](https://pgmpy.org/guides/extensibility.html?utm_source=chatgpt.com)

## 10. Consequential distinctions and limitations

Several cross-cutting distinctions have more architectural importance than any individual algorithm name.

| Distinction                                           | Consequence                                                                                                             |
| ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Observational dependency vs causation                 | A statistically learned edge direction does not by itself establish an intervention mechanism                           |
| DAG vs PDAG/CPDAG                                     | Some directions may be observationally indistinguishable; forcing a DAG can discard that uncertainty                    |
| Explicit latent variables vs latent confounding edges | Different graphical representations support different separation and identification operations                          |
| Identification vs estimation                          | An effect can be identifiable but difficult to estimate reliably; a numerical estimate can exist without identification |
| Conditioning vs intervening                           | `evidence` and `do` express different distributions                                                                     |
| Exact vs approximate inference                        | Exact methods avoid sampling error but can have prohibitive structural complexity                                       |
| Discrete vs Gaussian vs functional CPDs               | Different distribution families entail different assumptions, algorithms, and dependencies                              |
| Parameter consistency vs model correctness            | `check_model()` validates representation-level invariants, not real-world causal validity                               |
| Structural metrics vs statistical fit                 | A good graph score is not the same as correct causal orientation or predictive calibration                              |
| Global backend vs algorithm support                   | A PyTorch setting does not make every model or inference method differentiable or GPU-native                            |
| Graph/model conversion vs semantic preservation       | Different representational formats need not preserve every modeling assumption or annotation                            |

### 10.1 Performance characteristics

The important cost drivers vary by subsystem.

Discovery: Number of variables, candidate edges, conditioning-set enumeration, score recalculation, and independence-test cost. Expert constraints and restricted search spaces can materially reduce work.

Discrete parameter estimation: State cardinalities and combinations of parent states. Parallel local CPD estimation may help when many sufficiently costly families are independent.

Exact inference: Induced width, clique cardinalities, and number of factor operations. Sparse-looking graphs can still contain expensive inference subproblems.

EM and approximate inference: Number of iterations or samples, convergence behavior, posterior approximation quality, and the cost of each E-step or sampling transition.

Functional probabilistic programming: PyTorch/Pyro execution, vectorization, differentiability, optimizer behavior, device placement, and data movement.

These describe mechanisms rather than guaranteed performance rankings. A larger graph is not necessarily harder to query than a smaller graph with denser dependencies or higher-cardinality variables.

### 10.2 Model families are not universally interchangeable

A particularly important limitation is that pgmpy's broad family coverage does not imply one universal inference/learning engine.

For example:

- Variable elimination is appropriate for supported discrete factorized models, not arbitrary executable Pyro distributions.
- A linear Gaussian Bayesian network has analytically useful structure that is lost when represented as arbitrary black-box conditional functions.
- A mixed-data structure score does not imply full support for exact hybrid inference.
- `DBNInference` is specialized for dynamic Bayesian networks, not arbitrary time-series probabilistic programs.
- A mixed causal graph may support separation and causal-role analysis without supporting every discrete Bayesian-network operation.

The correct boundary is defined by the combination of model class, distribution family, estimator, and inference algorithm.

### 10.3 API transition considerations in 1.1.x

Several important names and interfaces changed or were reorganized in version 1.1:

| Area                     | Current direction                                                                                         |
| ------------------------ | --------------------------------------------------------------------------------------------------------- |
| Bayesian-network classes | `DiscreteBayesianNetwork` is the explicit discrete model class                                            |
| Undirected models        | `DiscreteMarkovNetwork` supersedes the deprecated `MarkovNetwork` name                                    |
| Causal discovery         | Unified classes under `pgmpy.causal_discovery`                                                            |
| Structure scores         | Organized under `pgmpy.structure_score`                                                                   |
| Parameter estimation     | Newer estimators under `pgmpy.parameter_estimator`; older `pgmpy.estimators` interfaces remain documented |
| Causal roles             | Standardized role annotations such as `exposures`, `outcomes`, and `confounders`                          |
| Benchmarks               | Dataset/model registries with metadata, filters, and remote-backed loading                                |

Version 1.1.2 also addressed algorithmic correctness in PC and GES, including edge orientation, determinism, and CI-test behavior.

For reproducible causal discovery, these fixes can matter more than performance changes because they affect the structure being inferred.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Source: [https://github.com/pgmpy/pgmpy/blob/dev/CHANGELOG.md](https://github.com/pgmpy/pgmpy/blob/dev/CHANGELOG.md?utm_source=chatgpt.com)

## 11. How the capabilities compose

A small example illustrates the relationship between pgmpy's layers without assuming that graph discovery automatically establishes causality.

Suppose an assumed causal model contains a confounder \\(Z\\), treatment \\(X\\), and outcome \\(Y\\).

The following is an illustrative v1.1.x sketch, not an executed example:

```
from pgmpy.base import DAGfrom pgmpy.identification import Adjustmentfrom pgmpy.models import DiscreteBayesianNetworkfrom pgmpy.inference import VariableElimination, CausalInference# Hypothesized causal graph.graph = DAG(    [("Z", "X"), ("Z", "Y"), ("X", "Y")],    roles={"exposures": "X", "outcomes": "Y"},)# Determine whether adjustment identifies the effect.identified, success = Adjustment(    variant="minimal").identify(graph)if success:    print(identified.get_role("adjustment"))# df contains observed discrete columns Z, X, Y.model = DiscreteBayesianNetwork(graph.edges())model.fit(df)# Observational prediction.posterior = VariableElimination(model).query(    variables=["Y"],    evidence={"X": 1},)# Interventional prediction, given causal interpretation.intervention = CausalInference(model).query(    variables=["Y"],    do={"X": 1},)# Synthetic samples under intervention.synthetic = model.simulate(    n_samples=1000,    do={"X": 1},    seed=42,)
```

The important architectural point is the reuse of a shared graph and fitted distribution across multiple operations:

Graph structure and causal assumptions

Nodes, edges, roles, graphical separation

Identification

Adjustment, frontdoor, validity

Parameter fitting

CPDs, likelihoods, priors

Posterior inference

Evidence

Causal inference

Interventions

Simulation

Synthetic observations

For a different problem shape, discovery can supply a candidate graph and statistical validation can evaluate its implied dependencies before causal assumptions are added. Functional CPDs or regression-based causal estimators can replace some of the components, provided their model and interface requirements are respected.

This composability is pgmpy's strongest architectural characteristic: the same explicit probabilistic/causal representation can participate in estimation, reasoning, simulation, and evaluation, with fewer independent implementations of the system's statistical structure.

## 12. Primary-source reference map

The following resources are the most useful entry points for further library-specific investigation.

| Topic                          | Primary URL                                                                                                                         |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| Full API reference             | [https://pgmpy.org/api/index.html](https://pgmpy.org/api/index.html?utm_source=chatgpt.com)                                         |
| Release history                | [https://github.com/pgmpy/pgmpy/releases](https://github.com/pgmpy/pgmpy/releases?utm_source=chatgpt.com)                           |
| Changelog                      | [https://github.com/pgmpy/pgmpy/blob/dev/CHANGELOG.md](https://github.com/pgmpy/pgmpy/blob/dev/CHANGELOG.md?utm_source=chatgpt.com) |
| Official examples              | [https://pgmpy.org/examples.html](https://pgmpy.org/examples.html?utm_source=chatgpt.com)                                           |
| Tutorial repository            | [https://github.com/pgmpy/pgmpy_tutorials](https://github.com/pgmpy/pgmpy_tutorials?utm_source=chatgpt.com)                         |
| Graph representations          | [https://pgmpy.org/api/base.html](https://pgmpy.org/api/base.html?utm_source=chatgpt.com)                                           |
| Model families                 | [https://pgmpy.org/api/models.html](https://pgmpy.org/api/models.html?utm_source=chatgpt.com)                                       |
| Factors and CPDs               | [https://pgmpy.org/api/factors.html](https://pgmpy.org/api/factors.html?utm_source=chatgpt.com)                                     |
| Structure learning             | [https://pgmpy.org/api/structure_learning.html](https://pgmpy.org/api/structure_learning.html?utm_source=chatgpt.com)               |
| Conditional independence tests | [https://pgmpy.org/api/ci_test.html](https://pgmpy.org/api/ci_test.html?utm_source=chatgpt.com)                                     |
| Structure scoring              | [https://pgmpy.org/api/structure_score.html](https://pgmpy.org/api/structure_score.html?utm_source=chatgpt.com)                     |
| Parameter estimation           | [https://pgmpy.org/api/parameter_estimation.html](https://pgmpy.org/api/parameter_estimation.html?utm_source=chatgpt.com)           |
| Inference and sampling         | [https://pgmpy.org/api/inference.html](https://pgmpy.org/api/inference.html?utm_source=chatgpt.com)                                 |
| Causal identification          | [https://pgmpy.org/guides/causal_identification.html](https://pgmpy.org/guides/causal_identification.html?utm_source=chatgpt.com)   |
| Causal estimation              | [https://pgmpy.org/guides/causal_estimation.html](https://pgmpy.org/guides/causal_estimation.html?utm_source=chatgpt.com)           |
| Simulations                    | [https://pgmpy.org/guides/simulations.html](https://pgmpy.org/guides/simulations.html?utm_source=chatgpt.com)                       |
| Evaluation metrics             | [https://pgmpy.org/api/metrics.html](https://pgmpy.org/api/metrics.html?utm_source=chatgpt.com)                                     |
| Datasets                       | [https://pgmpy.org/guides/datasets.html](https://pgmpy.org/guides/datasets.html?utm_source=chatgpt.com)                             |
| Example models                 | [https://pgmpy.org/guides/example_models.html](https://pgmpy.org/guides/example_models.html?utm_source=chatgpt.com)                 |
| Import/export                  | [https://pgmpy.org/api/readwrite.html](https://pgmpy.org/api/readwrite.html?utm_source=chatgpt.com)                                 |
| Plotting                       | [https://pgmpy.org/guides/plotting.html](https://pgmpy.org/guides/plotting.html?utm_source=chatgpt.com)                             |
| Extending pgmpy                | [https://pgmpy.org/guides/extensibility.html](https://pgmpy.org/guides/extensibility.html?utm_source=chatgpt.com)                   |

### Overall assessment

pgmpy occupies a valuable position between graph-analysis libraries, conventional statistical modeling, probabilistic programming, and causal-inference tooling.

Its greatest strengths are not restricted to any single Bayesian-network algorithm. They are the breadth and composability of its model representations, the explicit separation of structural and distributional reasoning, and its support for moving between observational modeling, causal identification, effect estimation, and simulation.

The areas especially worth understanding beyond introductory usage are mixed causal graph representations, conditional-independence testing, equivalence-class discovery, expert-constrained search, inference treewidth, functional Pyro CPDs, dynamic Bayesian networks, DoubleML estimation, structural equation models, and the model-agnostic evaluation infrastructure.

The essential constraint is that these capabilities inhabit different statistical and computational regimes. The library provides substantial common infrastructure, but there is no single distribution family or universal inference algorithm that covers them all.