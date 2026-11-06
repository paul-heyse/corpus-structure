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

# pgmpy 1.1.2 — Advanced Capabilities Addendum

Research date: November 5, 2026\
Target version: pgmpy 1.1.2 (stable; released April 30, 2026)\
Scope: Additional functionality, advanced mechanisms, and behavioral qualifications supplementing the existing comprehensive library reference.

This addendum extends the original reference without repeating its existing treatment of model families, structure learning, causal estimation, and probabilistic inference. It focuses on capabilities whose significance becomes clearer when their underlying mechanisms, interactions, and limitations are examined. All version-specific descriptions target the released 1.1.2 implementation rather than unreleased development functionality.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



## 1. Symbolic independence reasoning and distribution-to-graph validation

Extends original sections 2.1, 2.3, and 8.1.

### 1.1 Independence assertions as first-class mathematical objects

The `pgmpy.independencies` package provides a symbolic reasoning layer distinct from both graphical separation algorithms and statistical conditional-independence tests.

`IndependenceAssertion` represents relationships such as

\\[ X\perp Y\mid Z \\]

where the independent variable groups and conditioning variables can each contain multiple variables. `Independencies` stores collections of these assertions and supports logical operations over the relationships they encode.

The distinction is important: graphical separation derives independencies from a specified graph, whereas symbolic reasoning determines which independence statements follow from other independence statements without requiring a graph or numerical probability distribution.

The supported operations include:

| Operation              | API                                  | Mathematical or analytical purpose                                       |
| ---------------------- | ------------------------------------ | ------------------------------------------------------------------------ |
| Assertion construction | `IndependenceAssertion`              | Represents unconditional or conditional independence                     |
| Assertion collection   | `Independencies`, `add_assertions()` | Maintains sets of independence constraints                               |
| Logical closure        | `closure()`                          | Derives additional independencies using semigraphoid axioms              |
| Logical implication    | `entails()`                          | Determines whether one collection implies another                        |
| Equivalence            | `is_equivalent()`                    | Tests whether two collections have the same implied independence content |
| Redundancy elimination | `reduce()`                           | Removes redundant or less informative assertions                         |
| Assertion membership   | `contains()`, `get_assertions()`     | Inspects explicitly represented assertions                               |

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy

### 1.2 Semigraphoid closure and entailment

The implementation's logical foundation is the set of semigraphoid properties satisfied by probabilistic conditional independence.

For disjoint variable sets \\(X,Y,Z,W\\), these include:

Symmetry

\\[ X\perp Y\mid Z\implies Y\perp X\mid Z \\]

Decomposition

\\[ X\perp(Y,W)\mid Z\implies X\perp Y\mid Z \\]

Weak union

\\[ X\perp(Y,W)\mid Z\implies X\perp Y\mid(Z,W) \\]

Contraction

\\[ \begin{aligned} X&\perp Y\mid Z\\\ X&\perp W\mid(Y,Z) \end{aligned} \implies X\perp(Y,W)\mid Z \\]

These rules allow a collection of independence assertions to function as a constraint system. Rather than manually constructing every logically related independence statement, an application can use `closure()` or `entails()` to establish consequences of the statements it already possesses.

For example, a collection asserting \\(X\perp(Y,W)\mid Z\\) entails both \\(X\perp Y\mid Z\\) and \\(X\perp W\mid Z\\). Conversely, two separately asserted pairwise independencies do not necessarily establish joint independence of \\(X\\) from \\((Y,W)\\).

`is_equivalent()` performs a stronger comparison than textual or set equality: collections with different explicitly stored assertions may nevertheless represent the same independence theory.

Computational and logical boundaries. The official documentation warns that closure and entailment may become very slow with more than approximately six variables. The expansion of possible conditioning sets makes exhaustive symbolic reasoning combinatorially expensive.

Furthermore, semigraphoid closure is not a universally complete characterization of every conditional-independence implication across arbitrary probability distributions. Failure to derive an assertion through these rules should not automatically be interpreted as a demonstration that the assertion is probabilistically impossible.

Primary sources:

`https://pgmpy.org/api/generated/independencies/pgmpy.independencies.Independencies.html`

`https://pgmpy.org/api/generated/independencies/pgmpy.independencies.IndependenceAssertion.html`

### 1.3 Deriving graphical structure from a known joint distribution

`JointProbabilityDistribution` provides an additional direction of reasoning: rather than starting with a graph and determining its implied independencies, it can start with an explicit joint probability distribution and derive or validate graphical representations.

The relevant methods are `check_independence()`, `get_independencies()`, `is_imap()`, and `minimal_imap(order)`.

`check_independence()` evaluates whether a specified independence relationship holds under the represented probability distribution. It distinguishes conditioning on particular variable states from testing conditional independence given a random variable itself through `condition_random_variable`.

`get_independencies()` extracts independence relationships from the distribution, with optional conditioning variables.

An independence map, or I-map, is a graph whose implied conditional independencies hold in the represented distribution. Formally, for graph \\(G\\) and distribution \\(P\\),

\\[ \mathcal I(G)\subseteq\mathcal I(P). \\]

`is_imap(model)` checks whether a supplied discrete Bayesian network is an independence map for the distribution.

This is not the same as requiring the graph to encode every independence in the distribution. An I-map may contain additional edges and consequently make fewer independence assertions than a more compact representation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy



### 1.4 Minimal I-map construction

`minimal_imap(order)` constructs a minimal independence-map Bayesian network relative to a supplied variable ordering.

For an ordering \\(X_1,\ldots,X_n\\), the construction seeks parent sets from the variables preceding each node such that the required local Markov independencies are satisfied. Conceptually, for each \\(X_i\\), the remaining predecessors should be independent of \\(X_i\\) once its selected parents are conditioned upon.

This provides a programmatic route from an explicit probability distribution to a factorized graphical representation.

The ordering is consequential. Different orders can produce different minimal I-maps, including graphs with different numbers of edges. Minimal means that unnecessary edges cannot be removed while retaining the relevant independence-map property; it does not imply the globally sparsest possible graph.

These operations enable several distinct forms of validation:

- Comparing a proposed graph's independence claims against a known distribution.
- Deriving alternative minimal factorizations from different variable orderings.
- Testing whether structure-learning algorithms recover a graph compatible with a synthetic ground-truth distribution.
- Distinguishing graphical model representation errors from statistical estimation errors.

These are general analytical possibilities enabled by the native operations, not guarantees that recovered edges describe causality.

Explicit joint distributions are practical primarily for small or otherwise tractable discrete systems. Their storage requirements grow with the product of variable cardinalities, and independence checks can require expensive marginalization or conditioning.

`conditional_distribution()` and `marginal_distribution()` also default to in-place modification. Callers preserving an original distribution for later comparisons should use their non-mutating options or an explicit copy.

Primary source:

`https://pgmpy.org/api/generated/factors/pgmpy.factors.discrete.JointProbabilityDistribution.html`

### 1.5 Combining the three independence layers

These capabilities establish three distinct levels of independence analysis within pgmpy:

| Level          | Starting representation                          | Question answered                                                |
| -------------- | ------------------------------------------------ | ---------------------------------------------------------------- |
| Graphical      | DAG, Bayesian network, or compatible mixed graph | What independencies does the graph imply?                        |
| Symbolic       | `Independencies` assertions                      | What additional independencies follow logically?                 |
| Distributional | `JointProbabilityDistribution`                   | Which independencies hold under these actual probability values? |

Statistical CI testing adds a fourth, empirically estimated level: whether a finite observational dataset provides evidence for or against a particular independence relationship.

The distinction is architecturally useful because discrepancies have different interpretations. A failure of graphical and distributional agreement can expose an incorrect factorization. A failure of a statistical test to support a graph-implied independence may arise from misspecification, sampling variability, inadequate statistical power, or inappropriate test assumptions.

No single one of these checks establishes that a directed relationship is causal.

## 2. Analytical inference in linear Gaussian Bayesian networks

Extends original sections 2.2, 4.2, and 5.

The original reference explains linear Gaussian models primarily through their conditional distributions and parameter-estimation capabilities. A further important capability is native multivariate Gaussian inference, which allows uncertainty to be propagated and conditioned analytically.

### 2.1 Converting a directed model to a joint Gaussian

A parameterized `LinearGaussianBayesianNetwork` represents linear structural relationships with Gaussian disturbances.

Its `to_joint_gaussian()` method derives the implied joint mean vector and covariance matrix:

\\[ X\sim\mathcal N(\mu,\Sigma). \\]

For a linear structural model written as

\\[ X=BX+a+\varepsilon, \qquad \varepsilon\sim\mathcal N(0,\Omega), \\]

the implied distribution, under a nonsingular \\(I-B\\), is

\\[ \mu=(I-B)^{-1}a \\]

and

\\[ \Sigma=(I-B)^{-1}\Omega(I-B)^{-T}. \\]

These equations describe the mathematical relationship underlying the conversion; they do not assert that pgmpy computes the quantities using this exact matrix algorithm.

The native API returns a tuple of NumPy arrays containing the joint mean vector and covariance matrix. This makes the compact graphical parameterization available to conventional numerical linear algebra without manually expanding all paths through the directed graph.

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy

### 2.2 Conditional posterior means and covariance

The more consequential functionality is `predict_probability(data)`.

Suppose the model's joint Gaussian is partitioned into missing variables \\(X_M\\) and observed variables \\(X_O\\):

\\[ \begin{bmatrix} X_M\\\X_O \end{bmatrix} \sim \mathcal N\left( \begin{bmatrix} \mu_M\\\\\mu_O \end{bmatrix}, \begin{bmatrix} \Sigma\_{MM}&\Sigma\_{MO}\\\ \Sigma\_{OM}&\Sigma\_{OO} \end{bmatrix} \right). \\]

When \\(\Sigma\_{OO}\\) is invertible, conditioning on \\(X_O=x_O\\) gives

\\[ \mu\_{M\mid O} = \mu_M+ \Sigma\_{MO}\Sigma\_{OO}^{-1}(x_O-\mu_O) \\]

and

\\[ \Sigma\_{M\mid O} = \Sigma\_{MM}- \Sigma\_{MO}\Sigma\_{OO}^{-1}\Sigma\_{OM}. \\]

The posterior mean depends on the observed values, but the conditional covariance does not. For a fixed model and partition of observed versus missing variables, the covariance can therefore be reused across many observations.

`predict_probability(data)` exposes this structure directly by returning:

`(missing_variables, posterior_means, posterior_covariance)`

The posterior means are computed for the supplied data rows, while the covariance describes their conditional uncertainty. The covariance depends on the fitted parameters and observed-variable set, not merely the graph topology.

`predict(data)` provides the corresponding point estimates. In a Gaussian model, the conditional mean is also a posterior mode, so this method supplies the MAP estimates without separately implementing Gaussian optimization.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy



### 2.3 Architectural significance and limitations

The combination of graphical factorization, joint Gaussian construction, and analytic conditioning creates a distinct alternative to discretization or general probabilistic programming.

It supports multivariate uncertainty propagation, prediction under partial observation, conditional covariance analysis, and calculation of correlations implied by a fitted directed model.

The analytical result is exact relative to the assumed linear-Gaussian probability model, apart from floating-point numerical error. It is not an approximation produced by sampling or stochastic variational inference.

This distinction has important limits.

Nonlinear or non-Gaussian mechanisms generally cannot be represented faithfully by these equations. The covariance structure also inherits assumptions about the disturbances used in the graphical parameterization. Dense covariance calculations and factorizations can be costly for large models, even when their directed representations are sparse.

The API also does not imply arbitrary inference interoperability. In particular, `LinearGaussianBayesianNetwork.to_markov_model()` is explicitly unimplemented in the documented version. A joint covariance representation is therefore not equivalent to native support for every Markov-network transformation or discrete variable-elimination mechanism.

Primary source:

`https://pgmpy.org/api/generated/models/pgmpy.models.LinearGaussianBayesianNetwork.html`

## 3. Graph-based instrumental-variable identification

Extends original sections 7.1–7.4.

### 3.1 Discovering candidate instruments from causal structure

The original reference covers instrumental-variable regression through `NaiveIVRegressor` and `IVEstimator`. A separate, important capability is pgmpy's ability to identify candidate instruments from the structure of a causal graph.

`CausalInference` exposes `get_ivs(X, Y)` and `get_conditional_ivs(X, Y)`, together with the more specialized `get_total_conditional_ivs(X, Y)`.

For a treatment \\(X\\), outcome \\(Y\\), and candidate instrument \\(Z\\), instrumental-variable identification relies on assumptions such as instrument relevance, exclusion of direct effects on the outcome, and independence from the disturbances that confound the treatment–outcome relationship.

In an elementary linear setting,

\\[ X=\pi Z+U_X \\]

\\[ Y=\beta X+U_Y, \\]

a valid instrument can identify \\(\beta\\) despite correlation between \\(U_X\\) and \\(U_Y\\), provided the required restrictions hold and \\(\pi\neq0\\).

Graph-based instrument discovery provides a means of investigating whether those restrictions are compatible with a specified causal structure.

`get_ivs()` identifies candidate instruments using graph transformations and graphical connectivity. Rather than testing arbitrary combinations of variables through regression, it reasons about the paths connecting instrument candidates, treatments, outcomes, and confounding structures.

The official documentation illustrates this with an `SEMGraph` containing an instrument affecting treatment, treatment affecting outcome, and correlated treatment–outcome disturbances.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy



### 3.2 Conditional instrumental variables

Ordinary IV validity can be too restrictive when a candidate instrument becomes valid only after conditioning on additional variables.

`get_conditional_ivs()` extends the search to pairs \\((Z,W)\\), where \\(Z\\) is an instrument conditional on a set \\(W\\).

For example, the documented `SEMGraph` example identifies instrument `I` conditional on `W`:

```
from pgmpy.models import SEMGraphfrom pgmpy.inference import CausalInferencemodel = SEMGraph(    ebunch=[("I", "X"), ("X", "Y"), ("W", "I")],    latents=[],    err_corr=[("W", "Y")],)c_infer = CausalInference(model)conditional_ivs = c_infer.get_conditional_ivs("X", "Y")# [('I', {'W'})]
```

The underlying algorithm searches for conditioning sets capable of blocking problematic paths while preserving the relationship needed for the candidate instrument to inform the treatment.

`get_total_conditional_ivs()` is another released method, implemented separately in `CausalInference.py`. Its handling of nodes on causal paths distinguishes it from the ordinary conditional-IV search. Its public documentation is sparse, so the tagged implementation should be treated as the authoritative source for its exact behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 3.3 Latent-variable measurement models and scaling indicators

Instrument identification also interacts with pgmpy's structural equation modeling capabilities.

When an SEM contains latent constructs measured by observed indicators, `get_scaling_indicators()` selects an observed measurement variable for each latent variable. The instrumental-variable identification methods accept an explicit `scaling_indicators` mapping.

This supplies an implementation mechanism for reasoning about identifiable structural relationships involving latent measurement models.

An important qualification is that pgmpy's default indicator selection can be random. Explicitly supplying measurement indicators avoids introducing uncontrolled selection into otherwise reproducible identification workflows.

An indicator's suitability for scaling is a substantive measurement-model assumption, not something established merely by the function returning a variable.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy



### 3.4 Identification-method discovery and estimator composition

`CausalInference.identification_method(X, Y)` provides another useful coordination mechanism. It attempts several identification routes and returns a dictionary describing methods for which candidate identification results were found.

The source includes backdoor adjustment, frontdoor adjustment, ordinary IVs, conditional IVs, and total conditional IVs.

This means pgmpy can provide a structural exploration layer before selecting a numerical estimation method.

The distinction between structural identification and numerical estimation remains essential. A graphically admissible instrument can be statistically weak. Instrument validity depends on the assumed graph, exclusion restrictions, and other causal assumptions. Finite-sample properties and estimator consistency additionally depend on the statistical model.

The identification-method helper is therefore a means of discovering candidate identification strategies, not an automatic proof that an effect has been reliably identified and estimated. Its implementation also catches exceptions from individual search routines, so an absent candidate in its result should not be treated as a universal impossibility theorem.

Primary sources:

`https://pgmpy.org/api/generated/causal_inference/pgmpy.inference.CausalInference.CausalInference.html`

`https://github.com/pgmpy/pgmpy/blob/v1.1.2/pgmpy/inference/CausalInference.py`

## 4. Advanced discrete parameter estimation and EM behavior

Extends original section 4.1 and qualifies its missing-data discussion.

### 4.1 Configurable M-step estimation

The newer `pgmpy.parameter_estimator.DiscreteEM` implementation exposes substantially more control than a conventional fixed maximum-likelihood EM routine.

Its `m_step_estimator` argument accepts a discrete parameter estimator implementing weighted-data support.

The default is `DiscreteMLE()`, but `DiscreteBayesianEstimator` can also be supplied.

The E-step estimates posterior weights for possible latent-state assignments. In the M-step, those weights are used to fit the complete-data conditional distributions.

For a latent variable \\(H\\) and observation \\(x_i\\), the E-step constructs weights proportional to

\\[ w\_{ih}=P(H=h\mid x_i,\theta^{(t)}). \\]

An ordinary M-step updates parameters using the resulting expected sufficient statistics. A prior-regularized M-step can instead combine the weighted observations with pseudo-counts supplied by a Bayesian estimator.

The architecture separates latent-state responsibility computation from parameter estimation, allowing the same EM machinery to reuse alternative local parameter-fitting methods.

The supplied estimator must advertise weighted-data support; otherwise, `DiscreteEM` raises an error. This is a concrete extension boundary rather than unrestricted interchangeability with arbitrary estimators.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 4.2 Bayesian priors and regularization

`DiscreteBayesianEstimator` supports three prior specifications:

| Prior       | Mechanism                                                              | Consequence                                                     |
| ----------- | ---------------------------------------------------------------------- | --------------------------------------------------------------- |
| `BDeu`      | Uniform Dirichlet pseudo-counts derived from an equivalent sample size | Distributes prior strength over state and parent configurations |
| `K2`        | Unit pseudo-count for each CPD cell                                    | Provides a fixed additive prior contribution                    |
| `dirichlet` | Explicit pseudo-counts, including node-specific arrays                 | Permits asymmetric and domain-informed prior information        |

For node \\(X_i\\) with \\(r_i\\) states and \\(q_i\\) parent configurations, BDeu assigns a pseudo-count of

\\[ \alpha\_{ijk}=\frac{\alpha_i}{r_iq_i} \\]

to each cell, where \\(\alpha_i\\) is the node's equivalent sample size.

With empirical counts \\(N\_{ijk}\\), the resulting local probability estimate is

\\[ \hat P(X_i=k\mid\mathrm{Pa}\_i=j) = \frac{N\_{ijk}+\alpha\_{ijk}} {\sum\_{\ell}(N\_{ij\ell}+\alpha\_{ij\ell})}. \\]

The estimator supports per-node equivalent sample sizes, explicit Dirichlet pseudo-count arrays, sample weights, and parallel estimation of local CPDs.

These options are significant where some parent-state combinations are rare, because the estimator can regularize locally without requiring a separate custom CPD-fitting implementation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 4.3 Latent-state configuration, initialization, and convergence

`DiscreteEM` exposes the following consequential controls:

| Parameter          | Function                                                                             |
| ------------------ | ------------------------------------------------------------------------------------ |
| `latent_card`      | Cardinality of each latent variable; unspecified latent cardinalities default to two |
| `init_cpds`        | Initial CPDs supplied explicitly or generated using `random` or `uniform`            |
| `m_step_estimator` | Weighted parameter estimator used during each M-step                                 |
| `max_iter`         | Maximum number of EM iterations                                                      |
| `atol`             | Parameter-change convergence tolerance                                               |
| `n_jobs`           | Parallel processing of E-step weight computations                                    |
| `batch_size`       | Batch size for computing latent-assignment weights                                   |
| `seed`             | Random initialization control                                                        |

The implementation also distinguishes CPDs requiring iterative updates from those that can be estimated once without latent-variable involvement. In particular, CPDs for observed variables that are neither latent nor children of latent variables can be initialized and held fixed when no explicit initialization requires updating them.

This avoids repeatedly estimating parameters that do not depend on the posterior distribution of the latent variables.

The implementation deduplicates observed data patterns before E-step processing and accounts for their occurrence counts when generating weighted completed observations. These optimizations can reduce repeated work when datasets contain many identical rows.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 4.4 Computational implications of explicit latent-state enumeration

The 1.1.2 E-step constructs assignments over the Cartesian product of latent-variable states.

For latent variables \\(H_1,\ldots,H_m\\), the number of latent combinations per distinct observed pattern is

\\[ K=\prod\_{j=1}^{m}|\mathcal S(H_j)|. \\]

Consequently, a rough lower-level driver of E-step work is the number of distinct observed records multiplied by \\(K\\), together with the cost of evaluating model probabilities for each completed assignment.

This explains why parallel processing and batching can improve execution in some cases without eliminating the exponential dependence on the number and cardinality of latent variables.

EM is also sensitive to initialization. Different starting CPDs may converge to different local optima, particularly in latent-variable models with weak identifiability or symmetry between latent states.

The `atol` convergence condition concerns numerical changes in estimated parameters. Convergence is not evidence of a unique optimum, and an arbitrary alternative M-step does not automatically preserve every theoretical monotonic-likelihood property associated with classical maximum-likelihood EM.

### 4.5 Critical missing-data limitation in pgmpy 1.1.2

The newer `DiscreteEM` implementation has a narrower missing-data capability than a generic description of EM might suggest.

The tagged source explicitly:

1. Removes columns containing only missing values and promotes the corresponding variables to latent status.
2. Drops rows containing missing values in otherwise partially observed columns.
3. Performs EM over the remaining observed data and modeled latent variables.

This means partially missing observed cells are not generally imputed through the E-step of this implementation. Their rows are excluded before parameter estimation.

The distinction is substantial. Suppose observations contain variables \\(A,B,C\\), and some rows have observed \\(A,C\\) but missing \\(B\\). The newer estimator does not automatically preserve those rows and integrate over the unknown value of \\(B\\); it drops them.

By contrast, if a column representing \\(B\\) is entirely missing, the estimator can treat \\(B\\) as latent, subject to the specified graphical structure and latent cardinality.

Dropping partially observed records can reduce statistical efficiency and introduce selection effects when missingness is not completely random.

This behavior is verified from the v1.1.2 implementation and must be distinguished from the older `pgmpy.estimators.ExpectationMaximization` interface, whose algorithms and options require separate treatment.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Primary tagged sources:

`https://github.com/pgmpy/pgmpy/blob/v1.1.2/pgmpy/parameter_estimator/discrete_em.py`

`https://github.com/pgmpy/pgmpy/blob/v1.1.2/pgmpy/parameter_estimator/discrete_bayesian.py`

## 5. Batch probabilistic prediction

Extends original sections 5.1–5.3.

### 5.1 Prediction as repeated graphical inference

`DiscreteBayesianNetwork.predict()` provides a higher-level interface for applying probabilistic inference across multiple records.

The input is a pandas DataFrame containing observed model variables. Variables omitted from the input are predicted from the fitted network.

The method defaults to `VariableElimination`, but the `algo` argument can select compatible alternatives, including `BeliefPropagation` and `ApproxInference`.

This functionality is distinct from parameter fitting and from directly invoking an inference engine for one evidence assignment. It coordinates inference over the supplied observations and converts the results into a tabular representation.

The API exposes `n_jobs` for parallel processing and forwards algorithm-specific options, including elimination-order controls for variable elimination and sample-count controls for approximate inference.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy



### 5.2 MAP predictions versus stochastic predictions

`predict()` supports two different predictive operations through `stochastic`.

With `stochastic=False`, it produces highest-probability assignments for the missing variables. This corresponds to the relevant MAP assignment under the model and selected inference algorithm.

With `stochastic=True`, the predictions are sampled from the inferred conditional distributions.

The distinction is consequential. A MAP prediction selects a representative high-probability outcome, whereas stochastic prediction preserves variability across possible outcomes.

For example, if a target variable has posterior probabilities \\(0.45\\), \\(0.35\\), and \\(0.20\\), deterministic prediction repeatedly selects the first state. Stochastic prediction instead generates outcomes according to the three-state distribution.

The latter can be useful for uncertainty-aware synthetic completions, although it inherits any approximation or sampling error of the selected inference method.

### 5.3 Per-state probability output

`predict_probability(data)` returns probabilities for the states of the missing variables, rather than committing to a single predicted state.

This enables subsequent calculations involving expected values, uncertainty measures, threshold decisions, or comparisons between predictive distributions.

For a discrete variable \\(X\\), the entropy

\\[ H(X\mid e) = -\sum_x P(x\mid e)\log P(x\mid e) \\]

can be calculated directly from its returned posterior state probabilities.

However, per-variable marginal probabilities are not necessarily sufficient to reconstruct a joint posterior over multiple missing variables. Correlations between the predicted variables can matter, particularly for decisions involving their combined states.

Batch prediction is also not a new inference algorithm. Its runtime and exactness remain dependent on the underlying inference engine and the network's structure.

The documented examples primarily express missing variables as omitted DataFrame columns; this should not be confused with general support for arbitrary patterns of missing cells inside otherwise present columns.

Primary source:

`https://pgmpy.org/api/generated/models/pgmpy.models.DiscreteBayesianNetwork.html`

## 6. Advanced maximal ancestral graph operations

Extends original sections 2.1 and 7.1.

### 6.1 Inducing paths and maximality

The `MAG` representation includes operations that are not available merely by treating the graph as a conventional DAG.

`has_inducing_path(u, v, W)` checks whether an inducing path exists between two nodes relative to a specified set \\(W\\).

The implementation characterizes such a path through collider intermediates that satisfy specified ancestry or membership conditions.

Inducing paths matter because maximal ancestral graphs encode conditional-independence relationships after accounting for latent or selection-related structure.

A central property of a maximal ancestral graph is that nonadjacent vertices can be separated by an appropriate conditioning set. The existence of certain inducing paths explains why an adjacency may need to appear in a marginalized or conditioned representation even when there is no direct causal relationship between the corresponding observed variables.

This provides a structural operation for reasoning about the effects of hidden variables on the graphical relationships among observed variables.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy



### 6.2 Visible versus invisible directed edges

`is_visible_edge(u, v)` distinguishes two different interpretations of a directed edge in a MAG.

A visible edge \\(X\rightarrow Y\\) has graphical evidence ruling out certain forms of latent confounding between the endpoints under the MAG semantics.

An invisible directed edge lacks that graphical guarantee. Its arrow direction alone does not establish that the relationship can be treated as unconfounded.

The implementation checks specific graphical configurations involving vertices not adjacent to the destination and appropriate directed or collider paths into the source.

This distinction is easily overlooked because the same arrow notation is used in ordinary DAGs and MAGs, even though the representational assumptions differ.

Edge visibility is therefore relevant to causal identification and graphical manipulation. It should not be interpreted as an empirical causal-effect strength or an independently verified statement that no hidden confounder exists.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy



### 6.3 Upper and lower graph manipulations

`MAG` exposes `upper_manipulation(X)` and `lower_manipulation(X)`.

`upper_manipulation()` removes edges with arrowheads pointing into the manipulated variables.

`lower_manipulation()` removes visible edges originating from the manipulated variables and performs additional transformations involving invisible edges to preserve relevant independence relationships.

Both operations accept `inplace=False`, allowing transformed graphs to be produced without changing the original object.

These mechanisms support the graphical transformations required by certain causal-identification arguments in mixed ancestral graphs.

However, the transformations should not be confused with automatically identifying and evaluating arbitrary causal interventions. Their validity and interpretation depend on the graph semantics and the causal assumptions of the surrounding analysis.

Likewise, the availability of these operations does not establish that pgmpy implements complete general-purpose identification for every effect represented by an arbitrary mixed graph.

Primary source:

`https://pgmpy.org/api/generated/base/pgmpy.base.MAG.html`

## 7. Marginal-constrained graphical-model estimation through mirror descent

Extends original sections 4.2 and 5.4.

### 7.1 Fitting an undirected distribution to empirical marginals

`MirrorDescentEstimator` provides a specialized optimization approach for discrete undirected graphical models.

It accepts a `DiscreteMarkovNetwork`, `FactorGraph`, or `JunctionTree` together with a tabular dataset, and estimates graphical-model potentials to reproduce selected empirical marginal distributions.

This is different from ordinary directed Bayesian-network MLE. Rather than fitting one normalized conditional distribution per node, the estimator adjusts the potentials of an undirected factorization so that the model's implied marginals agree with observed marginal statistics.

The optimization operates on a probability representation using entropic mirror descent and computes updates in log space.

The estimator returns an optimized `JunctionTree`, allowing its fitted factors to participate in the library's existing inference machinery.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy



### 7.2 Optimization objective and controls

Conceptually, for selected variable subsets \\(\mathcal S\\), the objective is to reduce discrepancies between empirical marginals \\(\hat P_S\\) and model-implied marginals \\(P\_{\theta,S}\\):

\\[ \min\_\theta \sum\_{S\in\mathcal S} D\left(\hat P_S,P\_{\theta,S}\right). \\]

Here \\(D\\) represents the configured marginal-discrepancy measure. This is a conceptual expression of the fitting problem, not a transcription of the implementation's exact objective.

The public method

`estimate(marginals, metric="L2", iterations=100, stepsize=None, show_progress=True)`

allows callers to specify variable subsets and choose `L1` or `L2` discrepancy metrics.

The `stepsize` option controls optimization updates. When it is omitted, the estimator uses a default step-size rule together with line search.

The optimization also uses the model's graphical inference structure to evaluate the marginals implied by its current potentials.

These components enable iterative fitting without requiring a bespoke marginal-to-factor optimization algorithm.

### 7.3 Relationship to maximum-entropy modeling

There is a useful conceptual connection between matching marginal constraints and maximum-entropy probabilistic modeling.

For a set of compatible marginal constraints, a maximum-entropy distribution selects the least additionally committed joint distribution satisfying those constraints.

Undirected exponential-family models provide a natural parameterization for such problems because their factor potentials represent interactions over subsets of variables.

Mirror descent can exploit this structure when estimating potentials that reproduce empirical marginal information.

The connection is particularly valuable when the desired representation is a factorized joint distribution, rather than a collection of unrelated marginal probability tables.

The pgmpy implementation is based on work involving graphical-model estimation for differential privacy, but using `MirrorDescentEstimator` does not by itself provide differential privacy. Privacy guarantees would require an appropriate upstream mechanism and analysis of the complete workflow.

### 7.4 Limitations and integration boundaries

The estimator is specialized for discrete graphical models and empirical marginals obtained from a supplied dataset.

It should not be described as a general API for arbitrary externally supplied marginal arrays without considering how those values are introduced into the implementation.

Its usefulness also depends on the selected graph's expressiveness. A factorization that cannot represent the relevant interactions may fail to match all observed marginals adequately.

The junction-tree representation and associated belief-propagation computations retain the usual clique-size and treewidth limitations. Mirror descent changes the parameter-estimation approach; it does not remove the computational cost of the model's underlying inference operations.

Primary source:

`https://pgmpy.org/api/generated/parameter_estimation/pgmpy.estimators.MirrorDescentEstimator.html`

## 8. MPLP relaxation, tightening, and MAP solution diagnostics

Extends original section 5.2.

### 8.1 MAP inference as an optimization problem

`Mplp` implements max-product linear programming for approximate MAP inference in discrete Markov networks.

For factor potentials \\(\psi\_\alpha\\), the MAP problem can be written as

\\[ x^\* = \arg\max_x \sum\_\alpha \log\psi\_\alpha(x\_\alpha). \\]

This is a global optimization problem over variable assignments.

MPLP approximates it through a linear-programming relaxation expressed in terms of locally consistent marginal quantities. Message-passing updates optimize the dual formulation of that relaxation.

This is different from Gibbs sampling or approximate posterior marginal inference. Its purpose is to find a high-scoring global assignment, not to estimate a normalized distribution over states.

### 8.2 Integrality gap as a solution-quality diagnostic

`Mplp.get_integrality_gap()` exposes a particularly useful diagnostic.

The LP relaxation can provide an upper bound on the best achievable MAP objective, while an integral assignment supplies a feasible objective value.

For a maximization formulation, the corresponding gap is conceptually

\\[ \Delta\_{\mathrm{int}} = U\_{\mathrm{LP}}-L\_{\mathrm{feasible}} \geq0. \\]

A small gap indicates that the relaxation's bound and the feasible assignment are close under the objective being optimized.

A zero gap, when the computed bounds are valid and numerical tolerances are satisfied, can establish that the assignment attains the relaxed bound and therefore solves the original MAP problem.

A nonzero gap does not, by itself, quantify the probability that the assignment is correct or show that the returned solution is globally optimal.

This gives MPLP a form of optimization diagnostics that ordinary sampling-based approximate inference does not provide.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy



### 8.3 Tightening the relaxation with triplet clusters

`Mplp.map_query()` exposes controls for progressively tightening the optimization relaxation.

These include `tighten_triplet`, `max_triplets`, `max_iterations`, and `prolong`, alongside the initial and later iteration limits.

Triplet tightening introduces additional cluster constraints intended to strengthen the relaxation where pairwise or existing local constraints are insufficient.

The method also exposes `dual_threshold` and `integrality_gap_threshold` as stopping controls.

The implementation's message updates are designed to decrease the dual objective, and the relaxation-tightening process can improve the relationship between the relaxed solution and an integral assignment.

This creates a tradeoff between computational effort and solution quality: additional clusters and message updates may yield tighter bounds, but they increase the work and state maintained during optimization.

### 8.4 Practical boundaries

MPLP is particularly relevant when the desired result is a high-scoring joint assignment under discrete undirected factor potentials.

It is not an automatic substitute for posterior inference. Even an exactly solved MAP problem does not provide normalized marginal probabilities, posterior uncertainty, or evidence likelihoods.

The documented `Mplp` implementation is specialized for `DiscreteMarkovNetwork`, so compatibility with arbitrary Bayesian networks or functional distributions should not be assumed.

Primary source:

`https://pgmpy.org/api/generated/inference/pgmpy.inference.Mplp.html`

## 9. Graph-native statistical diagnostics and structural characterization

Extends original sections 2.1, 8.1, and 9.4.

### 9.1 Empirical edge-strength estimation

`DAG.edge_strength(data, edges=None)` computes a data-dependent measure of association for specified graph edges.

It uses a conditional-independence testing approach, with conditioning based on the graph's parent relationships.

The documented effect-size calculation uses a residualization-based method associated with Pillai's trace. It accommodates categorical and continuous variables under the supported testing method and produces strength values between zero and one.

For an edge \\(X\rightarrow Y\\), the quantity is intended to summarize the association between the variables after adjusting for the relevant parent variables.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy



This has a different interpretation from either the existence of an edge or its numerical causal effect.

An edge represents an assumed or learned graphical dependency. An edge-strength statistic measures an empirical relationship under a particular conditioning and modeling procedure.

The statistic does not automatically identify an intervention effect. Residual confounding, incorrect graphical structure, nonlinear dependence, and misspecified conditional models can all affect the interpretation.

It is also not equivalent to a standardized regression coefficient or a universal unit of causal influence.

### 9.2 Structural graph statistics

`DAG.get_stats()` returns a dictionary containing structural characteristics such as node and edge counts, edge density, numbers of roots and leaves, weakly connected components, v-structures, average and maximum parent counts, and latent-node counts.

This provides a native structural characterization mechanism that can be used without separately traversing the graph for every elementary statistic.

Several outputs are directly relevant to probabilistic modeling.

A high maximum parent count may indicate expensive local conditional distributions in a discrete Bayesian network. V-structures influence conditional-independence relationships and help distinguish Markov-equivalence classes. Weak connectivity can identify graph components that may admit separate analysis, depending on model semantics.

However, simple graph statistics are not substitutes for inference-complexity measures. Maximum indegree and edge density do not uniquely determine treewidth or the size of the intermediate factors created during elimination.

### 9.3 Annotated graphical representations

The graph visualization interfaces also support edge-strength annotations.

`to_graphviz(plot_edge_strength=True)` and `to_daft(plot_edge_strength=True)` can include previously computed strength values in rendered graph representations.

This enables graphical structure and empirical dependency information to be presented together without implementing a separate annotation layer.

The resulting diagrams must still preserve the distinction between edge orientation and edge strength: an annotated causal hypothesis is not an empirically proven causal mechanism.

Primary source:

`https://pgmpy.org/api/generated/base/pgmpy.base.DAG.html`

## 10. Factored Markov-chain transitions and sample-based diagnostics

Extends original section 6.2.

### 10.1 Multiple transition kernels

`MarkovChain` supports a state represented by multiple discrete variables, with separate transition kernels attached through `add_transition_model()`.

Each variable's transition matrix can be provided as a nested dictionary or a two-dimensional array.

The model therefore need not be expressed manually as a single transition table over every combination of component states.

For state components \\(X_1,\ldots,X_m\\), a factorized transition representation can avoid explicitly storing a full transition matrix over the composite state space.

However, the implemented per-variable transition kernels do not imply general support for cross-variable conditional dependencies. A dynamic Bayesian network is the more expressive representation when the next state of one variable depends on the previous or current state of other variables.

### 10.2 Streaming samples and empirical state probabilities

`generate_sample()` exposes trajectory generation through an iterator, rather than requiring every simulated observation to be materialized immediately as a DataFrame.

`sample()` provides the corresponding tabular simulation interface.

`prob_from_sample()` estimates probabilities of specified partial or complete states over generated or supplied samples, with an optional window-size parameter.

`is_stationarity()` provides a stationarity-related check based on the model's state probabilities and supplied or generated sample information.

These utilities can support empirical characterization of finite-state transition behavior without requiring a separate generic simulation framework.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy



The stationarity method should not be interpreted as a general-purpose numerical solver for stationary distributions of arbitrary structured transition systems. Its documented behavior is a consistency check with specified tolerance, and sample-derived probabilities remain subject to finite-sample variability and mixing effects.

Primary source:

`https://pgmpy.org/api/generated/models/pgmpy.models.MarkovChain.html`

## 11. Simulation API compatibility across model families

Clarifies original section 6.3.

The original guide correctly distinguishes evidence, hard interventions, virtual evidence, and soft interventions. However, those concepts should not be presented as uniformly implemented options of every model family's `simulate()` method.

The following table reflects the documented 1.1.2 interfaces.

| Simulation capability                | Discrete BN           | Linear Gaussian BN              | Functional BN   | Dynamic BN   |
| ------------------------------------ | --------------------- | ------------------------------- | --------------- | ------------ |
| Ordinary forward simulation          | Yes                   | Yes                             | Yes             | Yes          |
| Hard intervention (`do`)             | Yes                   | Yes                             | Yes             | Yes          |
| Conditioning on observed evidence    | Yes                   | Yes                             | Not exposed     | Yes          |
| Virtual evidence                     | Yes                   | Not exposed                     | Not exposed     | Yes          |
| Virtual/stochastic intervention      | `TabularCPD`          | `LinearGaussianCPD`             | `FunctionalCPD` | `TabularCPD` |
| Simulated missingness                | CPD-defined mechanism | Per-variable MCAR probabilities | Not exposed     | Not exposed  |
| Partial sample constraints           | Yes                   | Not exposed                     | Not exposed     | Not exposed  |
| Latent-value inclusion flag          | Yes                   | Yes                             | Not exposed     | Yes          |
| Time-indexed intervention/evidence   | Not applicable        | Not applicable                  | Not applicable  | Yes          |
| Configurable temporal return layouts | Not applicable        | Not applicable                  | Not applicable  | Yes          |

[image](https://www.google.com/s2/favicons?domain=https://pgmpy.org\&sz=32)

pgmpy+3

### 11.1 Discrete missingness generation

For `DiscreteBayesianNetwork.simulate()`, the `missing_prob` argument accepts one or more `TabularCPD` objects defining probabilities of missingness.

The missingness mechanism can depend on specified model variables, providing considerably more expressiveness than simply deleting a fixed proportion of values at random.

This makes it possible to generate datasets with different missingness patterns under explicitly specified assumptions.

The implementation also exposes `return_full`, allowing both the generated complete data and its missingness-affected representation to be retained when applicable.

This can be valuable for evaluating missing-data methods because the complete simulated values are known relative to the generating model.

### 11.2 Linear Gaussian missingness is narrower

For `LinearGaussianBayesianNetwork.simulate()`, `missing_prob` is a mapping from variable names to probabilities.

Each generated value is independently replaced with `NaN` according to the supplied probability. This implements a missing-completely-at-random mechanism.

It is not equivalent to the conditional missingness distributions available through discrete CPDs.

The linear-Gaussian simulator additionally supports interventions, evidence conditioning, and soft interventions specified using `LinearGaussianCPD`.

### 11.3 Functional interventions replace generating mechanisms

`FunctionalBayesianNetwork.simulate()` exposes hard interventions and stochastic interventions specified through replacement `FunctionalCPD` objects.

The documented soft-intervention mechanism requires unconditional replacement CPDs. This means a replacement mechanism supplies a distribution without retaining dependencies on the intervened node's original parents.

The API should not be confused with unrestricted modification of arbitrary conditional generating functions while preserving their existing dependence structure.

The method does not expose the same conditional-evidence or missingness-generation options as the discrete simulator.

### 11.4 Temporal simulation adds a different dimension

`DynamicBayesianNetwork.simulate()` supports time-indexed evidence and interventions, using variable/time pairs to identify the affected states.

It also exposes multiple output layouts, including wide DataFrames, three-dimensional NumPy arrays, multi-indexed DataFrames, and lists of per-trace DataFrames.

These are temporal data-representation capabilities rather than generic simulation options available to every Bayesian-network class.

Architectural implication: A system using multiple pgmpy model families can share high-level concepts such as interventions and probabilistic evidence, but it must preserve the model-specific CPD types, semantics, accepted parameters, and output representations.

Primary sources:

`https://pgmpy.org/api/generated/models/pgmpy.models.DiscreteBayesianNetwork.html`

`https://pgmpy.org/api/generated/models/pgmpy.models.LinearGaussianBayesianNetwork.html`

`https://pgmpy.org/api/generated/models/pgmpy.models.FunctionalBayesianNetwork.html`

`https://pgmpy.org/api/generated/models/pgmpy.models.DynamicBayesianNetwork.html`

## 12. Additional capability interactions and boundaries

The newly detailed functionality reveals several connections that are important when treating pgmpy as a composable probabilistic modeling framework.

### 12.1 From mathematical independence specifications to fitted models

Symbolic independence assertions, graphical separation, joint-distribution validation, and empirical CI testing form complementary validation mechanisms.

A model's graph can encode independence constraints; those constraints can be investigated through symbolic entailment; a known joint distribution can validate their probabilistic consistency; and observed data can test whether the implications are statistically plausible.

This supports richer model validation than relying solely on a structure score or on successful CPD normalization.

These checks do not become equivalent when composed. Symbolic consistency does not establish empirical truth, and distributional consistency does not establish causal direction.

### 12.2 From graphical causal assumptions to identifiable estimation problems

Instrument discovery, conditional adjustment, and regression-based estimation occupy different stages of causal reasoning.

Graphical algorithms can identify candidate variables and conditioning sets. Estimators then use observed data to compute effect estimates under those assumptions.

This makes it possible to keep causal-identification logic separate from numerical prediction machinery, while still connecting them through explicit graph structure and variable roles.

The resulting numerical estimates require their own statistical diagnostics, including checks of instrument relevance, model adequacy, and estimator uncertainty.

### 12.3 From local distributions to analytical uncertainty propagation

Linear-Gaussian CPDs provide an example of a model-specific capability combination that can be substantially simpler than a generic probabilistic program.

Local structural equations determine a joint Gaussian distribution, whose conditional posterior parameters can be calculated analytically.

This yields conditional estimates and covariance information with no Monte Carlo error under the assumed model.

The advantage is conditional on the model remaining within the linear-Gaussian family. Moving to arbitrary nonlinear functional CPDs generally changes both the computational machinery and the available guarantees.

### 12.4 From empirical marginals to graphical models

Mirror-descent estimation provides an alternative to constructing all CPDs or factor potentials independently.

A selected set of empirical marginal relationships can inform the parameters of an undirected model, whose fitted junction-tree representation can then participate in graphical inference.

This interaction is useful when the relevant statistical information is naturally represented through overlapping marginal relationships rather than directed local regressions.

Its limitations are determined jointly by the sufficiency of the selected marginals, the model's factorization, the optimization method, and the inference cost of the junction tree.

### 12.5 From approximate optimization to solution-quality evidence

MPLP illustrates a different form of approximation from Monte Carlo inference.

Sampling approximates expectations or distributions through random draws. MPLP approximates a MAP optimization problem through a relaxation, with an integrality-gap diagnostic that can reveal how tightly the computed solution is bounded.

These approaches therefore provide different kinds of evidence about result quality.

A well-mixed sampler does not necessarily provide an optimal assignment certificate, and a tightly bounded MAP solution does not characterize the full posterior distribution.

The capability distinction matters whenever a system must represent not only a probabilistic answer but also what can and cannot be established about its reliability.

End of pgmpy 1.1.2 advanced capabilities addendum.