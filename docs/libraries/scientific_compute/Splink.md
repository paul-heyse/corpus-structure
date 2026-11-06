# Splink 5.0.0 — Comprehensive Python Library Capability Reference

Research date: October 21, 2026 | Current stable release: 5.0.0 (September 28, 2026) | Python: 3.10+ | License: MIT

Splink is an open-source Python library for probabilistic record linkage, entity resolution, and deduplication. Its principal capability is identifying records that refer to the same underlying entity—even when they lack common identifiers, contain errors, use inconsistent representations, or disagree on individual attributes.

Splink combines a statistical matching model, configurable candidate generation, SQL-based execution, parameter estimation, interactive diagnostics, and graph-based clustering into one coherent framework.

Version 5.0 is particularly significant. It improves the execution architecture for very large datasets, introduces explicit chunked processing and incremental linkage APIs, reduces dependencies, and provides more direct control over SQL execution, intermediate data, and profiling. The statistical model remains compatible with version 4, but several Python interfaces have changed.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

+1



Official sources

- Documentation: [https://moj-analytical-services.github.io/splink/](https://moj-analytical-services.github.io/splink/?utm_source=chatgpt.com)
- Source repository: [https://github.com/moj-analytical-services/splink](https://github.com/moj-analytical-services/splink?utm_source=chatgpt.com)
- Python package: [https://pypi.org/project/splink/](https://pypi.org/project/splink/?utm_source=chatgpt.com)
- Splink 5 release announcement: [https://moj-analytical-services.github.io/splink/blog/2026/09/28/splink-500-released.html](https://moj-analytical-services.github.io/splink/blog/2026/09/28/splink-500-released.html?utm_source=chatgpt.com)
- API reference: [https://moj-analytical-services.github.io/splink/api_docs/api_docs_index.html](https://moj-analytical-services.github.io/splink/api_docs/api_docs_index.html?utm_source=chatgpt.com)

## 1. Architectural orientation

Splink is best understood as a probabilistic entity-resolution engine with a relational execution architecture, rather than merely a fuzzy-string matching library.

Its core workflow is:

Source records

One or multiple datasets containing candidate entities

Blocking / candidate generation

Identify plausible record pairs without generating the full Cartesian product

Feature comparisons and probabilistic scoring

Compute comparison levels, evidence weights, and posterior match probabilities

Pairwise linkage results

Scored candidate pairs, match evidence, and thresholded links

Graph clustering and evaluation

Group linked records into estimated entities; inspect accuracy and cluster quality

Model training, blocking analysis, exploratory diagnostics, and visualization interact with several of these stages.

### 1.1 Major capability families

| Capability             | What Splink provides                                                                                 |
| ---------------------- | ---------------------------------------------------------------------------------------------------- |
| Entity matching        | Probabilistic deduplication, cross-dataset linkage, combined linkage and deduplication               |
| Statistical modeling   | Fellegi–Sunter model, comparison-level likelihoods, match weights, term-frequency adjustments        |
| Candidate generation   | Multiple blocking rules, SQL predicates, candidate-count analysis, blocking optimization             |
| Feature engineering    | Built-in and custom comparison logic, string similarity, dates, geographic and structured attributes |
| Model training         | Unsupervised EM estimation, random-sampling estimation, labeled-data estimation, model diagnostics   |
| Execution              | SQL generation, DuckDB, Spark, PostgreSQL, SQLite                                                    |
| Large-scale processing | Chunked predictions, backend execution controls, direct Parquet materialization, profiling           |
| Incremental matching   | Scoring new records against existing records, within-set linkage, explicit pairwise scoring          |
| Entity consolidation   | Thresholded graph clustering and cluster diagnostics                                                 |
| Explainability         | Match-weight decomposition, waterfall charts, comparison viewers, interactive cluster exploration    |
| Model evaluation       | Precision/recall analysis, labeled-pair evaluation, threshold selection, error analysis              |
| Integration            | Arrow, DuckDB, SQLGlot, PySpark, model serialization, SQL and tabular result interfaces              |

### 1.2 What Splink does not attempt to be

Splink is not a general-purpose database, a master-data-management platform, or a complete entity-identity lifecycle service.

Its native responsibilities center on generating, scoring, evaluating, and clustering record links. Applications can combine these capabilities with external persistence, business rules, golden-record generation, human-review workflows, and identity governance.

It also is not principally a semantic-search engine. Its strongest use cases involve multiple informative attributes that can collectively distinguish entities. The project explicitly cautions that it is poorly suited to records containing only a single bag-of-words field, such as an isolated company name, without additional distinguishing attributes.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

moj-analytical-services.github.io

+1



This boundary matters: Splink's distinctive value is the combination of imperfect evidence across multiple fields, not simply calculating sophisticated string distances.

## 2. The probabilistic matching model

Splink implements a modified Fellegi–Sunter record-linkage model, which combines evidence from individual field comparisons into an overall estimate of whether two records represent the same entity.

This is a meaningful distinction from conventional fuzzy matching: Splink does not treat every similarity score as having equivalent evidential significance.

### 2.1 The three fundamental parameters

For a pair of records, Splink models:

| Parameter      | Meaning                                                                                                   |
| -------------- | --------------------------------------------------------------------------------------------------------- |
| \\(\lambda\\)  | Prior probability that two randomly selected records refer to the same entity                             |
| \\(m\_{i,k}\\) | Probability of observing comparison level \\(k\\) in feature \\(i\\), conditional on the records matching |
| \\(u\_{i,k}\\) | Probability of observing that comparison level, conditional on the records not matching                   |

The evidence contribution from a comparison level is the likelihood ratio \\(m\_{i,k}/u\_{i,k}\\).

For example, an exact match on an uncommon date of birth is generally stronger evidence of identity than an exact match on a frequently occurring city.

Splink expresses these contributions as additive, base-2 logarithmic match weights:

\\[ W=\log_2\frac{\lambda}{1-\lambda} +\sum_i\log_2\frac{m\_{i,k_i}}{u\_{i,k_i}} +\Delta\_{\mathrm{TF}} \\]

Here, \\(\Delta\_{\mathrm{TF}}\\) represents any enabled term-frequency adjustments.

The match probability is obtained from the resulting posterior odds:

\\[ P(\text{match}\mid\text{evidence})=\frac{2^W}{1+2^W} \\]

This provides an interpretable scoring mechanism: each feature either increases or decreases the evidence supporting a match.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink

+1



### 2.2 Why this formulation is useful

Evidence has learned significance. An exact agreement is not intrinsically worth a fixed number of points. Its contribution depends on how frequently that agreement occurs in matching and nonmatching records.

Disagreements can provide negative evidence. A sharply conflicting attribute may reduce the overall match probability, even when several other fields agree.

Different attributes receive different probabilistic treatment. Name similarity, date differences, geographic proximity, and exact identifiers can contribute distinct evidence.

Scores are explainable. The final match weight can be decomposed into the prior and contributions from individual comparison levels, which Splink exposes through diagnostic charts.

Training does not require hand-labeled pairs. Splink can estimate parameters through statistical sampling and expectation-maximization, although labeled data can improve estimation and evaluation.

### 2.3 The conditional-independence assumption

A consequential limitation is the model's assumption that comparison observations are conditionally independent, given whether the records match.

For instance, postcode, city, and geographic coordinates may encode almost the same information. Treating all three as independent evidence can exaggerate confidence.

Splink does not automatically learn an arbitrary joint probability distribution across all attributes.

Its comparison framework does, however, allow related attributes to be combined within a single comparison, avoiding some forms of double counting. The built-in `ForenameSurnameComparison` illustrates this approach by jointly evaluating first name and surname, including their possible reversal.

The general architectural distinction is:

- Independent comparisons are appropriate for sufficiently distinct evidence.
- Compound comparisons can model relationships between correlated fields.
- More complex dependencies may require custom comparisons, derived features, or a different statistical model.

Source: [https://moj-analytical-services.github.io/splink/topic_guides/theory/fellegi_sunter.html](https://moj-analytical-services.github.io/splink/topic_guides/theory/fellegi_sunter.html?utm_source=chatgpt.com)

## 3. Linkage modes, input representation, and identity semantics

### 3.1 Three linkage modes

Splink supports three principal modes through the `link_type` setting.

| Mode              | Semantics                                                                      | Typical application                                                                        |
| ----------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| `dedupe_only`     | Compare records within a single dataset                                        | Identify duplicate customer, person, business, or transaction records                      |
| `link_only`       | Compare records across datasets, excluding comparisons within the same dataset | Match two registers or reconcile separate data sources                                     |
| `link_and_dedupe` | Compare records both within and across datasets                                | Resolve entities across several overlapping sources that may themselves contain duplicates |

The choice changes which record pairs are eligible for comparison, not just the way output is labeled.

An important distinction is that `link_only` does not itself enforce one-to-one matches between datasets. Multiple records can receive plausible matches. Restrictions such as no more than one record from a particular source per entity belong to a separate constrained-clustering step.

### 3.2 Input identity and registration

Splink needs a reliable way to identify source records.

In version 5, records are registered through a backend's `db_api.register()` method, producing a `SplinkDataFrame` object that can be supplied to `Linker`.

Important elements include:

- A unique record identifier, defaulting to `unique_id`.
- An explicit dataset identity, particularly for multi-dataset linkage.
- Consistent field types and appropriately normalized source data.
- A shared database backend for datasets participating in a linkage operation.

The distinction between a record identifier and an inferred entity identifier is fundamental. Splink does not presume that source-record identity equals real-world entity identity.

After clustering, several different source records may receive the same estimated entity identifier.

### 3.3 Data preparation and derived attributes

Splink supports comparisons over raw columns, normalized fields, and SQL expressions.

For example, an entity might have an original legal name, standardized name, postal address, phonetic name representation, industry classification, and external identifiers.

Derived attributes can serve different purposes:

- Blocking keys reduce candidate generation.
- Comparison features contribute probabilistic evidence.
- Frequency-adjustment columns characterize the prevalence of values.
- Source identifiers support lineage and linkage constraints.

These roles need not use identical representations. A coarse normalized name may be useful for blocking, whereas a more discriminating representation may be preferable for comparison.

Official documentation:

[https://moj-analytical-services.github.io/splink/topic_guides/splink_fundamentals/settings.html](https://moj-analytical-services.github.io/splink/topic_guides/splink_fundamentals/settings.html?utm_source=chatgpt.com)

[https://moj-analytical-services.github.io/splink/topic_guides/splink_fundamentals/link_type.html](https://moj-analytical-services.github.io/splink/topic_guides/splink_fundamentals/link_type.html?utm_source=chatgpt.com)

## 4. Blocking: the principal scalability mechanism

Blocking is one of Splink's most architecturally important capabilities.

Without blocking, deduplication over \\(n\\) records potentially requires:

\\[ \frac{n(n-1)}{2} \\]

pairwise comparisons.

For one million records, this is approximately 500 billion potential comparisons.

Splink instead generates candidate pairs through configurable rules, implemented primarily as SQL joins.

### 4.1 Multiple independent blocking rules

A model can generate candidates using multiple criteria, such as:

```
from splink import block_onblocking_rules = [    block_on("first_name", "surname"),    block_on("date_of_birth", "postcode"),    block_on("email"),]
```

A pair only needs to satisfy one of the rules to become a candidate.

This means one matching signal can compensate for errors in another. For example, a typo in someone's name need not eliminate the pair if date of birth and postcode agree.

Splink handles overlapping blocking rules so that candidates satisfying more than one rule are not redundantly scored as separate candidate pairs.

### 4.2 Blocking rules versus comparison rules

These mechanisms have different responsibilities.

Blocking rules decide which pairs are examined. A pair excluded from every blocking rule will not be found by that prediction operation, regardless of how closely the records resemble one another.

Comparison rules decide what evidence is assigned to pairs that have already been generated.

This distinction separates candidate-generation recall from the quality of the probabilistic scoring model.

It also means improving the statistical model cannot recover records omitted by candidate generation.

### 4.3 Sophisticated blocking predicates

Splink supports `block_on()` and more general SQL predicates. Consequently, blocking can use expressions involving:

- Multiple equality conditions.
- Normalized or transformed fields.
- Substrings and derived tokens.
- Date components.
- Composite identifiers.
- Backend-supported SQL functions.

For example, blocking on surname and birth year can retain candidate pairs whose dates differ in day or month.

Non-equality predicates are also possible, but they may prevent the database from using efficient equijoins. Expensive fuzzy functions inside blocking joins can produce dramatically worse execution plans.

The most valuable design pattern is often a union of several selective, relatively inexpensive blocking rules instead of one broad, computationally expensive rule.

### 4.4 Blocking analysis and diagnostics

Splink provides native tools for examining the computational implications of blocking specifications:

| API                                       | Capability                                                         |
| ----------------------------------------- | ------------------------------------------------------------------ |
| `count_comparisons_from_blocking_rules()` | Estimate or count the candidate pairs generated                    |
| `chart_comparisons_from_blocking_rules()` | Visualize cumulative comparisons across rules                      |
| `n_largest_blocks()`                      | Identify values responsible for the largest, most expensive blocks |

These are available through `splink.blocking_analysis`, with corresponding conveniences under `linker.blocking_analysis`.

In Splink 5, blocking analysis defaults to sampling records for approximate counts, reducing the cost of exploring candidate rules on large datasets. Setting `record_sample_proportion=1.0` requests exact counts.

This is particularly helpful because excessively broad blocking rules can be identified before running a full prediction job.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink

+1



### 4.5 Blocking for training is different

Splink uses blocking during both prediction and expectation-maximization training, but with different objectives.

Prediction blocking aims to capture as many genuine matches as possible while limiting computational cost.

Training blocking aims to produce a useful statistical sample containing both matching and nonmatching pairs. It does not have to cover every genuine match.

A training rule can also prevent the model from learning about the attribute on which it blocks: if every training pair shares the same surname, there is no useful variation in surname agreement.

Splink addresses this partly through multiple training sessions using different blocking rules, allowing different model parameters to be estimated.

Source documentation:

[https://moj-analytical-services.github.io/splink/topic_guides/blocking/blocking_rules.html](https://moj-analytical-services.github.io/splink/topic_guides/blocking/blocking_rules.html?utm_source=chatgpt.com)

[https://moj-analytical-services.github.io/splink/topic_guides/blocking/model_training.html](https://moj-analytical-services.github.io/splink/topic_guides/blocking/model_training.html?utm_source=chatgpt.com)

[https://moj-analytical-services.github.io/splink/api_docs/blocking_analysis.html](https://moj-analytical-services.github.io/splink/api_docs/blocking_analysis.html?utm_source=chatgpt.com)

## 5. Comparison models and feature engineering

Splink's comparison system provides far more expressive capability than a conventional collection of fixed fuzzy-match functions.

The central abstraction is a `Comparison`, containing ordered `ComparisonLevel` objects.

### 5.1 Discrete comparison levels

Consider a name comparison with these levels:

1. Null or invalid values.
2. Exact equality.
3. Jaro–Winkler similarity at least 0.95.
4. Jaro–Winkler similarity at least 0.85.
5. All other comparisons.

Each record pair falls into one level, using SQL `CASE WHEN`-style precedence.

Although a string comparator may produce a continuous similarity score, Splink maps that score into discrete categories for parameter estimation and scoring.

The choice of thresholds therefore affects both model expressiveness and statistical reliability: finer levels offer more distinctions but require enough observations to estimate meaningful probabilities.

### 5.2 Built-in comparison families

Splink provides reusable comparisons covering several kinds of data.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink

+1



| Family                  | Principal available functionality                                     |
| ----------------------- | --------------------------------------------------------------------- |
| Exact matching          | `ExactMatch`, exact-match levels, literal matching                    |
| String edit distances   | Levenshtein, Damerau–Levenshtein                                      |
| String similarity       | Jaro, Jaro–Winkler, Jaccard                                           |
| Vector/array similarity | Cosine similarity, array intersection, array subsets                  |
| Names                   | `NameComparison`, `ForenameSurnameComparison`, swapped-name detection |
| Email addresses         | Whole-email, username, and fuzzy-email comparison                     |
| Dates and times         | Date-of-birth comparisons, absolute time/date differences             |
| Locations               | Postcode comparisons and kilometer-distance comparisons               |
| Numeric attributes      | Absolute differences and percentage differences                       |
| Custom comparators      | Backend-defined distance functions and arbitrary SQL predicates       |

Some specialized comparisons capture distinctions that would otherwise require substantial custom code.

For example, `ForenameSurnameComparison` recognizes swapped first and last names, and `EmailComparison` distinguishes full-email agreement from username agreement or fuzzy similarity.

`PairwiseStringDistanceFunctionAtThresholds` and its comparison-level counterpart can compare arrays of strings using the best-matching element pair. This is useful when a record contains multiple names, aliases, or alternative representations.

Backend support for individual functions varies, especially outside DuckDB and Spark.

### 5.3 Custom comparisons

`CustomComparison` and `CustomLevel` allow a model to represent domain-specific evidence.

A custom comparison might distinguish between complete identifier agreement, agreement on a normalized prefix, a small edit distance, and complete disagreement.

The comparison system also supports composition through constructs such as `And`, `Or`, and `Not`, along with explicit null and fallback levels.

Advanced configuration permits manually specifying or overriding individual `m_probability` and `u_probability` values. This enables expert-defined models, partially trained models, or carefully controlled statistical assumptions where appropriate.

Custom SQL remains subject to the functions and semantics of the selected execution backend.

### 5.4 ColumnExpression: lazy relational feature transformations

The `ColumnExpression` abstraction represents a SQL expression that can be used in comparisons and blocking rules.

For example:

```
from splink import ColumnExpressionnormalized_email = ColumnExpression("email").lower()surname_prefix = ColumnExpression("surname").substr(1, 3).lower()parsed_date = ColumnExpression("date_text").try_parse_date()
```

Available transformations include lowercasing, substrings, casts, regular-expression extraction, null replacement, date/time parsing, and array-element selection.

A `ColumnExpression` can defer the final SQL dialect until the model is associated with a backend, increasing portability.

It also provides a choice between materializing prepared features ahead of time and computing them during comparisons.

The latter can reduce preparation requirements, but repeated transformations may be expensive when an attribute participates in millions of candidate comparisons.

Important restriction: term-frequency adjustments cannot be applied directly to transformed `ColumnExpression` values. When both normalization and term frequencies are needed, the normalized value must be prepared as an actual input column.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink



### 5.5 Term-frequency adjustments

Term-frequency adjustment is a major differentiator of Splink.

Ordinary exact matching treats agreement on all values of a given field as having the same evidential significance. But matching the surname Smith is much less informative than matching an extremely rare surname.

Splink's TF adjustments modify the evidence contribution according to how common a matching value is.

This is useful for attributes with strongly skewed frequency distributions, including names, company names, geographical features, classifications, and categorical identifiers.

TF adjustments can be enabled on prebuilt comparisons:

```
import splink.comparison_library as clsurname = cl.ExactMatch("surname").configure(    term_frequency_adjustments=True)
```

The mechanism also supports more advanced cases:

- Different adjustment columns for different levels.
- Frequency adjustments over compound or derived fields.
- Tunable adjustment weights.
- Minimum frequency-related probability controls.
- TF adjustments associated with fuzzy matches.

The frequency-adjustment approach can be incorporated into EM estimation rather than being restricted to a final postprocessing correction. For fuzzy matches involving different values, Splink's documented adjustment method uses the greater of the two frequencies.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink



Combining the comparison system with frequency adjustments, compound attributes, and precomputed normalized columns can substantially reduce the need for custom probabilistic feature-engineering code.

Detailed sources

Comparison library: [https://moj-analytical-services.github.io/splink/api_docs/comparison_library.html](https://moj-analytical-services.github.io/splink/api_docs/comparison_library.html?utm_source=chatgpt.com)

Comparison-level library: [https://moj-analytical-services.github.io/splink/api_docs/comparison_level_library.html](https://moj-analytical-services.github.io/splink/api_docs/comparison_level_library.html?utm_source=chatgpt.com)

Custom comparison guide: [https://moj-analytical-services.github.io/splink/topic_guides/comparisons/comparison_templates.html](https://moj-analytical-services.github.io/splink/topic_guides/comparisons/comparison_templates.html?utm_source=chatgpt.com)

Column expressions: [https://moj-analytical-services.github.io/splink/api_docs/column_expression.html](https://moj-analytical-services.github.io/splink/api_docs/column_expression.html?utm_source=chatgpt.com)

Term frequencies: [https://moj-analytical-services.github.io/splink/topic_guides/comparisons/term-frequency.html](https://moj-analytical-services.github.io/splink/topic_guides/comparisons/term-frequency.html?utm_source=chatgpt.com)

## 6. Model training and parameter estimation

Splink supports several complementary estimation methods. This is important because estimating the match prior, nonmatch frequencies, and match frequencies poses three different statistical problems.

### 6.1 Estimating the prior match probability

`linker.training.estimate_probability_two_random_records_match()` estimates the prior probability that two randomly selected eligible records describe the same entity.

It uses a set of conservative deterministic matching rules, counts the resulting unique pairs, and adjusts the observed count using a supplied estimate of the rules' recall.

Consequently, it is not fully automatic: the recall estimate is an external modeling assumption that can materially affect posterior match probabilities.

Version 5 adds `record_sample_proportion`, allowing this estimate to be computed from sampled input records when full counts would be expensive.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink



### 6.2 Estimating nonmatch frequencies

`estimate_u_using_random_sampling()` estimates the probability of each comparison level among nonmatching pairs.

Its statistical premise is that two records randomly selected from sufficiently large datasets are very unlikely to represent the same entity.

The resulting comparison-level frequencies provide a baseline for determining how surprising agreement would be under the nonmatch hypothesis.

In version 5, random-sampling estimation can:

- Process candidate samples in chunks.
- Stop collecting observations for a comparison when its levels have sufficient evidence.
- Use `min_count_per_level` to control the observation target.
- Use `max_pairs` to bound the sampling workload.
- Use a seed for reproducible sampling on supported backends.

These optimizations primarily change the cost of estimating the model, not its underlying statistical formulation.

### 6.3 Expectation-maximization training

`estimate_parameters_using_expectation_maximisation()` performs unsupervised parameter estimation.

The EM algorithm alternates between inferring likely match status from the current model and updating the model's statistical parameters.

Splink ordinarily holds previously estimated \\(u\\) probabilities fixed while estimating \\(m\\) probabilities, although the API permits different combinations of fixed and trainable parameters.

Training returns an `EMTrainingSession`, which exposes information about the estimation process.

Version 5 offers several significant controls:

| Parameter                                                           | Purpose                                                                                                              |
| ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `max_pairs`                                                         | Approximately cap the number of pairs used for a training session                                                    |
| `record_sample_proportion`                                          | Control the preliminary sampling used to estimate the blocked-pair workload when `max_pairs` is active               |
| `estimate_without_term_frequencies`                                 | Skip TF corrections during iterative EM estimation, trading some statistical difference for lower computational cost |
| `fix_m_probabilities`                                               | Keep existing match probabilities fixed                                                                              |
| `fix_u_probabilities`                                               | Keep existing nonmatch probabilities fixed; the default                                                              |
| `fix_probability_two_random_records_match`                          | Prevent EM from updating its internal estimate of the prior                                                          |
| `populate_probability_two_random_records_match_from_trained_values` | Explicitly propagate the EM-derived prior into the model                                                             |

A subtle but important behavior: EM may update its internal match prior during training without saving that value back into the overall model. The corresponding propagation parameter is disabled by default.

Also, `max_pairs` is an approximate bound achieved through sampling, rather than a guaranteed exact count.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink



### 6.4 Multiple training passes and parameter identifiability

Training on different blocking rules makes it possible to estimate parameters that are not identifiable from any one training subset.

Consider a model comparing name, birth date, email, and address. A training pass blocked on name may help estimate birth-date and address probabilities; another pass blocked on birth date may provide useful evidence for name comparisons.

Splink can combine parameter estimates across training sessions, with visual diagnostics to inspect their consistency.

This makes repeated EM estimation part of the native modeling workflow rather than requiring a bespoke algorithm for reconciling training runs.

The primary risks remain statistical: unrepresentative training subsets, insufficient examples of rare comparison levels, correlated attributes, and local EM optima.

### 6.5 Supervised and hybrid estimation

Where trusted identity labels exist, Splink provides:

- `estimate_m_from_pairwise_labels()` for explicitly identified matching record pairs.
- `estimate_m_from_label_column()` for source records containing a ground-truth entity identifier.

The label column need not be fully populated.

An important API distinction: `estimate_m_from_pairwise_labels()` treats every supplied pair as a positive match. It does not use a `clerical_match_score` field as a fractional or probabilistic label during this estimation.

This is different from the evaluation APIs, which can use scored clerical labels.

The model therefore supports hybrid training: unsupervised estimation for some parameters and labeled-positive estimation for others, without requiring a wholly different matching engine.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink



### 6.6 Training diagnostics

The `EMTrainingSession` API exposes iteration-history charts for match weights, parameter values, and the estimated match prior. The broader visualization API can compare parameter estimates from different training rounds.

These diagnostics help distinguish genuine convergence from unstable estimates or training passes that provide inadequate information about particular attributes.

Primary sources

Training API: [https://moj-analytical-services.github.io/splink/api_docs/training.html](https://moj-analytical-services.github.io/splink/api_docs/training.html?utm_source=chatgpt.com)

Training rationale: [https://moj-analytical-services.github.io/splink/topic_guides/training/training_rationale.html](https://moj-analytical-services.github.io/splink/topic_guides/training/training_rationale.html?utm_source=chatgpt.com)

EM training session API: [https://moj-analytical-services.github.io/splink/api_docs/em_training_session.html](https://moj-analytical-services.github.io/splink/api_docs/em_training_session.html?utm_source=chatgpt.com)

Training blocking rules: [https://moj-analytical-services.github.io/splink/topic_guides/blocking/model_training.html](https://moj-analytical-services.github.io/splink/topic_guides/blocking/model_training.html?utm_source=chatgpt.com)

## 7. Prediction, incremental record linkage, and explicit scoring

Splink 5 substantially expands the distinction between training a model, generating candidate pairs, and applying an existing model to different data.

### 7.1 Main inference interfaces

| API                    | Behavior                                                                              |
| ---------------------- | ------------------------------------------------------------------------------------- |
| `predict()`            | Generate blocked candidate pairs from the Linker's registered inputs and score them   |
| `predict_chunk()`      | Score one specified partition of the candidate-generation workload                    |
| `predict_within()`     | Generate and score eligible pairs within an explicitly supplied collection of records |
| `predict_between()`    | Generate and score pairs across two explicitly supplied collections                   |
| `score_pair()`         | Score one specified pair without requiring it to pass blocking rules                  |
| `score_pairs()`        | Score the Cartesian product of two supplied collections, without blocking             |
| `deterministic_link()` | Produce links based on the configured blocking rules without probabilistic scoring    |

The distinction between `score_pairs()` and `predict_between()` is especially consequential.

`score_pairs()` compares every left record with every right record. It is useful when the Cartesian product is intentionally small or when the supplied collections are already narrowed to candidates.

`predict_between()` instead uses blocking to generate candidates between the two collections, preserving the scalability characteristics of the trained linkage model.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink

+2



### 7.2 Incremental entity resolution

A common problem is matching a new batch of records against an existing resolved dataset without recomputing all historical record pairs.

Splink 5 makes that workflow more explicit.

Assume:

- \\(E\\): existing records
- \\(N\\): new records

The required comparisons can be separated into:

\\[ E\times N \\]

for existing-to-new linkage, and:

\\[ N\times N \\]

for detecting duplicates among new records.

The native interfaces correspond directly:

```
between = linker.inference.predict_between(existing, new)within_new = linker.inference.predict_within(new)
```

Here, `existing` and `new` are previously registered `SplinkDataFrame` objects, and the example presumes a compatible trained deduplication model and prepared term-frequency lookups.

`predict_between()` does not redundantly regenerate all existing-to-existing pairs. Both interfaces permit overriding prediction blocking rules and linkage type.

The left/right distinction represents processing roles, not necessarily the source-dataset labels used by `link_only` or `link_and_dedupe`. Source-dataset restrictions from the effective linkage type still apply.

### 7.3 Term-frequency consistency across batches

Incremental inference introduces an important statistical lifecycle obligation.

`predict_within()` and `predict_between()` do not automatically estimate term-frequency tables from the newly supplied records. They require previously registered frequency lookups or explicit `tf_*` columns where the trained model needs them.

The available table-management operations include:

- `compute_tf_table()`
- `register_term_frequency_lookup()`

This separation makes it possible to score new records against a stable reference distribution rather than silently redefining evidence weights from each new batch.

However, it also places responsibility on the surrounding system to maintain appropriate frequency statistics. A distribution that has changed significantly over time can alter the calibration and meaning of the scores.

### 7.4 Explicit pair scoring

`score_pair()` supports scoring known record pairs, including records supplied as Python dictionaries.

This makes it useful for interactive inspection, candidate verification, targeted pair scoring, and applying a trained model where another system has already selected a pair.

It can also report whether the scored pair would have been found by the model's configured blocking rules.

That diagnostic is valuable because a pair may receive a high match probability when explicitly scored yet remain completely invisible to ordinary blocked prediction.

`score_pairs()` extends the idea to two collections, but deliberately does not impose candidate-generation restrictions. It should therefore not be interpreted as a scalable substitute for blocked inference.

### 7.5 Separate candidate generation from scoring

Splink 5 also exposes:

- `compute_blocked_pairs_for_predict()`
- `compute_blocked_pairs_for_predict_chunk()`
- `register_blocked_pairs_for_predict()`

The first two materialize candidate pairs independently of statistical scoring. The third allows a previously generated candidate table to be registered for a later prediction operation.

This enables a more modular execution architecture:

1. Generate candidate pairs.
2. Store or exchange the resulting pair table.
3. Score those pairs in another processing session.
4. Preserve the scored output for clustering or analysis.

For supported workloads, this separation can avoid repeating expensive blocking joins, permit independent performance analysis of candidate generation and scoring, and facilitate distribution of work across machines.

It does not by itself provide a managed distributed scheduler or exactly-once workflow. Those remain external concerns.

Primary sources

Inference API: [https://moj-analytical-services.github.io/splink/api_docs/inference.html](https://moj-analytical-services.github.io/splink/api_docs/inference.html?utm_source=chatgpt.com)

Table management API: [https://moj-analytical-services.github.io/splink/api_docs/table_management.html](https://moj-analytical-services.github.io/splink/api_docs/table_management.html?utm_source=chatgpt.com)

Splink 5 release details: [https://moj-analytical-services.github.io/splink/blog/2026/09/28/splink-500-released.html](https://moj-analytical-services.github.io/splink/blog/2026/09/28/splink-500-released.html?utm_source=chatgpt.com)

## 8. Entity clustering and graph analysis

Pairwise linkage and entity clustering are distinct operations.

Splink scores individual pairs, but a practical entity-resolution system often needs to assign all corresponding source records to a common entity.

### 8.1 Connected-components clustering

`linker.clustering.cluster_pairwise_predictions_at_threshold()` interprets thresholded pairwise predictions as graph edges and finds connected components.

For example:

Illustrative graph: A–B and B–C exceed the edge threshold, so A, B, and C belong to one connected component even without a qualifying A–C edge.

This is an important semantic distinction: connected-components clustering applies transitivity to a graph of accepted links. It does not assert that every pair of records within a cluster independently exceeds the match threshold.

A single erroneous bridging edge can therefore merge two otherwise well-separated entities.

This is not a defect of the probabilistic model itself; it is a consequence of the chosen clustering rule.

### 8.2 Single-best-links constrained clustering

Splink also exposes `cluster_using_single_best_links()`.

This supports the constraint that selected source datasets should contribute at most one record per cluster.

For example, two administrative registers might each guarantee that a real-world entity appears at most once. Ordinary connected-components clustering can violate that assumption, whereas single-best-links clustering can enforce it for the specified datasets.

The algorithm considers mutual best matches and supports tie handling through `ties_method="drop"` or `"lowest_id"`.

The latter resolves certain ambiguous equal-weight links using identifiers, while the former discards those conflicting links.

This is a valuable native alternative to implementing custom source-uniqueness checks after clustering.

It should not, however, be confused with a globally optimal bipartite or multipartite assignment solver. The documented algorithm is a particular constrained greedy-style graph procedure, with its own tie semantics.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink



### 8.3 Standalone graph clustering

The separate module-level function:

`splink.clustering.cluster_pairwise_predictions_at_threshold()`

can operate on supplied node and edge tables together with a database API.

This permits use of Splink's connected-components machinery even when the graph edges were produced by another process rather than a trained Splink model.

It is a useful capability boundary: Splink's graph utility can be used independently of its probabilistic feature model.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink



### 8.4 Graph-quality metrics

`linker.clustering.compute_graph_metrics()` generates three relational outputs:

- `nodes`: node-level graph metrics.
- `edges`: edge-level graph metrics.
- `clusters`: cluster-level graph metrics.

The documented metrics include node degree and centrality, identification of bridge edges, cluster size, density, and centralization.

These are particularly useful for identifying suspicious clustering structures.

A large component connected by one weak bridge can deserve different scrutiny from a similarly sized, densely interconnected component.

Similarly, a record with few high-confidence connections might warrant closer inspection than a record supported by multiple independent links.

Graph metrics are diagnostics, not proof that an entity cluster is correct. Their interpretation depends on the availability of candidate edges, the chosen threshold, and the data's expected entity distribution.

Primary sources

Clustering API: [https://moj-analytical-services.github.io/splink/api_docs/linker_clustering.html](https://moj-analytical-services.github.io/splink/api_docs/linker_clustering.html?utm_source=chatgpt.com)

Standalone clustering: [https://moj-analytical-services.github.io/splink/api_docs/clustering.html](https://moj-analytical-services.github.io/splink/api_docs/clustering.html?utm_source=chatgpt.com)

Graph metrics: [https://moj-analytical-services.github.io/splink/topic_guides/evaluation/clusters/graph_metrics.html](https://moj-analytical-services.github.io/splink/topic_guides/evaluation/clusters/graph_metrics.html?utm_source=chatgpt.com)

## 9. Model diagnostics, explainability, and evaluation

Splink has unusually extensive native diagnostic functionality for an entity-resolution library.

Rather than treating predicted matches as an opaque result table, it provides inspection mechanisms for source-data quality, learned probabilities, individual predictions, and final clusters.

### 9.1 Exploratory data analysis

The `splink.exploratory` module includes:

| API                    | Purpose                                                                                                     |
| ---------------------- | ----------------------------------------------------------------------------------------------------------- |
| `completeness_chart()` | Measure how frequently relevant columns contain non-null information, including comparisons across datasets |
| `profile_columns()`    | Inspect value distributions, frequent and rare values, and cardinality characteristics                      |

These operations help expose data-quality issues that may affect either statistical estimation or candidate generation.

For example, a blocking attribute with extreme skew may generate one enormous block, while an attribute missing from most rows may provide much less candidate coverage than anticipated.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink



### 9.2 Model and prediction visualizations

The principal interfaces under `linker.visualisations` include:

| Visualization                            | What it reveals                                                           |
| ---------------------------------------- | ------------------------------------------------------------------------- |
| `match_weights_chart()`                  | Evidence contribution of comparison levels                                |
| `m_u_parameters_chart()`                 | Learned matching and nonmatching probabilities                            |
| `match_weights_histogram()`              | Distribution of scored pairs across match weights                         |
| `parameter_estimate_comparisons_chart()` | Consistency between different training passes                             |
| `tf_adjustment_chart()`                  | Impact of term frequency on evidence weights                              |
| `waterfall_chart()`                      | How an individual pair's probability is assembled from its evidence       |
| `comparison_viewer_dashboard()`          | Interactive exploration of prediction patterns and example record pairs   |
| `cluster_studio_dashboard()`             | Interactive inspection of resolved clusters and their graph relationships |

The waterfall chart is especially valuable for understanding a single prediction. It decomposes the final score into the prior and feature-specific contributions.

The comparison viewer provides a complementary aggregate perspective, organizing predictions by their comparison patterns so that systematic false positives, underweighted attributes, or unexpectedly common evidence combinations can be investigated.

Cluster Studio instead operates at the entity-graph level, where errors can arise from transitivity even when individual high-confidence links appear reasonable.

These tools are complementary: no single chart establishes model quality.

Splink 5's `SplinkChart` objects can display and save HTML without Altair. Altair is optional for conversion to Altair objects and more advanced export formats. HTML can also be generated with an inlined JavaScript runtime for offline viewing.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink



### 9.3 Supervised accuracy evaluation

When ground truth is available, Splink can evaluate pairwise linkage quality using either:

- A column containing known entity identifiers.
- A separate labeled table of record pairs.

Relevant APIs include:

`accuracy_analysis_from_labels_column()`, `accuracy_analysis_from_labels_table()`, `prediction_errors_from_labels_column()`, and `prediction_errors_from_labels_table()`.

The native analysis supports precision, recall, threshold selection, and additional statistics including F-scores, specificity, negative predictive value, accuracy, and Matthews correlation coefficient.

It also supports ROC and precision–recall visualizations.

A significant detail is the `positives_not_captured_by_blocking_rules_scored_as_zero` option in label-column evaluation.

This explicitly accounts for genuine matches that blocking failed to generate, rather than measuring only the quality of predictions that survived candidate generation.

That distinction is essential for evaluating the end-to-end linkage process, because a strong classifier operating on an incomplete candidate set can still miss large numbers of genuine matches.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink

+1



### 9.4 Clerical labeling and active error investigation

Splink includes `labelling_tool_for_specific_record()` and related evaluation tools for inspecting and manually judging linkage results.

`unlinkables_chart()` helps examine records that the model finds difficult to link.

These are useful for discovering systematic gaps in comparison design, blocking coverage, and attribute quality.

They are not a complete human-review queue or annotation-management platform. Splink provides diagnostic and labeling interfaces; the surrounding processes for reviewer assignment, audit history, and approval remain separate.

### 9.5 Interpreting probabilities appropriately

Match probabilities are model estimates, not externally guaranteed statements of correctness.

Their calibration depends on the match prior, representativeness of estimated \\(m/u\\) probabilities, conditional-independence assumptions, and the relationship between the evaluated population and the population used to construct the model.

In particular:

- A high posterior probability does not mean a false match is impossible.
- A match threshold is an application decision, not a universal correctness criterion.
- An aggregate precision estimate may not represent performance equally across different populations.
- Pairwise precision and recall do not completely describe cluster quality.

Splink's evaluation and explainability tools make these distinctions observable, but they do not remove the need for representative ground truth where consequential decisions depend on accuracy.

Primary sources

Evaluation API: [https://moj-analytical-services.github.io/splink/api_docs/evaluation.html](https://moj-analytical-services.github.io/splink/api_docs/evaluation.html?utm_source=chatgpt.com)

Visualizations API: [https://moj-analytical-services.github.io/splink/api_docs/visualisations.html](https://moj-analytical-services.github.io/splink/api_docs/visualisations.html?utm_source=chatgpt.com)

Exploratory analysis API: [https://moj-analytical-services.github.io/splink/api_docs/exploratory.html](https://moj-analytical-services.github.io/splink/api_docs/exploratory.html?utm_source=chatgpt.com)

## 10. SQL execution architecture and supported backends

Splink's execution model is a central reason it can scale beyond typical Python-based record-matching implementations.

The library constructs SQL queries representing candidate generation, comparisons, parameter estimation, match-weight calculations, and other relational operations. An underlying SQL engine executes those queries.

Python orchestrates the operations, but most of the computational work occurs inside the database engine.

### 10.1 Backend comparison

| Backend      | Principal strengths                                                                                      | Important constraints                                                                                |
| ------------ | -------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| DuckDB       | Fast in-process analytics, vectorized execution, Parquet/Arrow integration, relatively simple deployment | Single-node resource limits, although version 5 supports chunking and external work distribution     |
| Apache Spark | Distributed execution across clusters, large datasets, established data-platform integration             | More configuration, distributed scheduling and shuffle overhead, additional UDF/JAR integration      |
| PostgreSQL   | Processing records already held in PostgreSQL, SQLAlchemy-based integration                              | Less-complete comparison support, required database permissions, relatively limited upstream testing |
| SQLite       | Lightweight embedded processing, basic linkage on smaller datasets                                       | Missing native similarity functions, Python UDF overhead, limited array/date comparison support      |

The maintainers identify DuckDB as the general-purpose default, with Spark useful when a workload exceeds practical single-node execution resources or already operates within Spark infrastructure.

DuckDB and Spark have the most complete coverage of the supplied comparison library.

The PostgreSQL and SQLite implementations have narrower functionality and receive less active upstream support.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink



### 10.2 SQLGlot and backend portability

Splink uses SQLGlot to help translate SQL expressions across backend dialects.

This allows substantial portions of the linkage logic to be shared across engines.

The boundary is not complete abstraction from SQL semantics, however.

Custom comparison predicates may depend on:

- Engine-specific string similarity functions.
- Different date and timestamp operations.
- Array and structural data semantics.
- Availability of user-defined functions.
- Differences in SQL type coercion and null handling.

A model built entirely from comparisons supported by multiple backends is more portable than one using extensive custom SQL.

SQLGlot translates expressions; it does not automatically provide missing database functions or guarantee equivalent query plans.

Source: [https://moj-analytical-services.github.io/splink/dev_guides/transpilation.html](https://moj-analytical-services.github.io/splink/dev_guides/transpilation.html?utm_source=chatgpt.com)

### 10.3 PostgreSQL-specific integration

Splink's PostgreSQL backend uses SQLAlchemy for database connectivity, with `PostgresAPI` wrapping the underlying engine.

It supports registering existing database tables or bringing in additional data.

The backend creates a working schema, conventionally named `splink`, and uses SQL functions and PostgreSQL extensions for required operations.

Its documented permissions include sufficient privileges to create the working schema, install `fuzzystrmatch`, and create the necessary SQL functions.

Backend-specific UDFs support functions such as `log2`, date differences, and array intersection.

The architectural advantage is executing linkage closer to relational data already stored in PostgreSQL. The tradeoff is that this does not necessarily provide the full comparator coverage or performance characteristics of DuckDB.

Source: [https://moj-analytical-services.github.io/splink/topic_guides/splink_fundamentals/backends/postgres.html](https://moj-analytical-services.github.io/splink/topic_guides/splink_fundamentals/backends/postgres.html?utm_source=chatgpt.com)

### 10.4 Spark and the Scala UDF ecosystem

Spark provides distributed execution of SQL-based comparisons.

Some operations absent from native Spark SQL are implemented using compiled Scala UDFs, packaged as JAR files.

The related source project is `splink_scalaudfs`, which contains the Scala implementations used to support matching functions.

There is an important current documentation issue: the original organizational repository is no longer available at its published URL. A maintainer identified a development copy in a separate repository. This does not establish that the released Spark backend is unusable, but it matters for developers wishing to inspect or extend its Scala functions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



Current accessible development source:

[https://github.com/ADBond/splink_scalaudfs](https://github.com/ADBond/splink_scalaudfs?utm_source=chatgpt.com)

Upstream issue:

[https://github.com/moj-analytical-services/splink/issues/3283](https://github.com/moj-analytical-services/splink/issues/3283?utm_source=chatgpt.com)

UDF documentation:

[https://moj-analytical-services.github.io/splink/dev_guides/udfs.html](https://moj-analytical-services.github.io/splink/dev_guides/udfs.html?utm_source=chatgpt.com)

### 10.5 User-defined functions as extension points

Custom database functions can extend the comparison model beyond built-in similarity operators.

For example, an application might implement a specialized matching function over proprietary classification codes or scientific identifiers.

Splink can invoke such a function inside a custom comparison or blocking expression, provided the selected backend supports it.

The performance distinction is important. Native vectorized database operations are generally preferable when they can express the required logic. Python UDFs may introduce row-level execution overhead; compiled or vectorized extensions may be more appropriate for high-volume comparisons.

The exact benefits depend on the engine and implementation.

## 11. Large-scale processing, memory management, and profiling

Splink's scalability depends on several interacting mechanisms: candidate reduction, efficient SQL execution, bounded working sets, and minimizing unnecessary data movement.

### 11.1 Prediction chunking in version 5

`predict()` accepts `num_chunks_left` and `num_chunks_right`.

This partitions the left and right sides of the candidate-generation workload into smaller pieces, enabling incremental computation rather than one large materialization.

The corresponding `predict_chunk()` interface permits execution of a particular chunk.

This is useful for large workloads because it can reduce peak resource demand and create independently executable units of work.

It also permits distributing different chunks to distinct machines and assembling the resulting pairwise predictions externally.

The interface should not be mistaken for an automatic distributed task-management system, and chunks need not have identical computational costs. Blocking-key skew can produce substantial differences between chunk workloads.

### 11.2 Direct Parquet materialization

Splink 5 introduces direct Parquet materialization for DuckDB intermediate and final results.

The significant architectural benefit is avoiding a requirement to retain every intermediate relational result in database-managed memory or reconstruct a large result through Python.

For example, a large candidate-pair table or prediction table can become a disk-backed relation participating in subsequent SQL operations.

This combines effectively with:

- Chunked predictions.
- Reusable blocked-pair tables.
- Precomputed term-frequency tables.
- Downstream DuckDB or Arrow processing.
- External orchestration of individual processing stages.

The result is a more composable execution system without requiring a separate custom engine for every intermediate step.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink



### 11.3 SQL profiling

Version 5 adds `DuckDBAPIWithProfiling` and `SparkAPIWithProfiling`.

These record detailed query profiles, allowing engineers to isolate expensive relational operations rather than treating linkage execution as one opaque Python function.

Typical performance bottlenecks include candidate-generation joins, excessive block sizes, repeated record hydration, expensive string similarity functions, intermediate materializations, and graph processing.

Splink also supports logging of generated SQL through the `SQL` log level.

An upstream open issue concerning candidate-pair hydration illustrates why such diagnostics matter: SQL that is semantically correct can still produce asymmetric or expensive database join plans.

That issue is an optimization proposal, not an established feature of 5.0.0.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink

+1



### 11.4 Performance evidence

The Splink 5 release announcement reports a benchmark processing:

# 1B

Input records

# 10B

Candidate comparisons

# 8.5 min

Reported runtime

The reported test used a 192-vCPU EC2 instance and a then-forthcoming DuckDB 2.0 engine.

This is evidence of the architecture's potential on heavily provisioned hardware under the published benchmark conditions—not a general expectation for arbitrary data, comparison logic, or server resources.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink



A reproducible benchmark and its associated setup are documented here:

[https://moj-analytical-services.github.io/splink/topic_guides/performance/duckdb_performance_reprex.html](https://moj-analytical-services.github.io/splink/topic_guides/performance/duckdb_performance_reprex.html?utm_source=chatgpt.com)

### 11.5 Where performance improvements arise

The largest gains often come from reducing the number and expense of comparisons rather than changing the statistical model.

| Mechanism                     | Work avoided or reduced                          | Principal tradeoff                                |
| ----------------------------- | ------------------------------------------------ | ------------------------------------------------- |
| Selective blocking            | Unnecessary record pairs                         | Potentially missed matches                        |
| Multiple blocking rules       | Dependence on one potentially fragile identifier | Additional joins and candidate overlap            |
| Precomputed normalized fields | Repeated expression evaluation                   | Storage and preparation work                      |
| Materialized TF lookups       | Repeated frequency aggregation                   | Maintaining an appropriate reference distribution |
| Native string functions       | Python or UDF execution overhead                 | Engine-specific implementation                    |
| Chunking                      | Large peak working sets                          | Scheduling and output coordination                |
| Parquet intermediate results  | Excessive memory-resident intermediates          | Disk I/O and intermediate lifecycle management    |
| Incremental prediction        | Recomputing historical record pairs              | Managing existing matches and new cluster changes |

These mechanisms compose naturally, but their combined performance should be measured under representative workloads.

## 12. Data integration, persistence, and lifecycle management

### 12.1 The `SplinkDataFrame` abstraction

A `SplinkDataFrame` represents a table or relation managed through the selected SQL backend.

It provides several methods for accessing results:

| Method                  | Result                                |
| ----------------------- | ------------------------------------- |
| `as_duckdbpyrelation()` | Native DuckDB relation                |
| `as_spark_dataframe()`  | Native Spark DataFrame                |
| `as_pyarrow_table()`    | PyArrow table                         |
| `as_pandas_dataframe()` | pandas DataFrame                      |
| `as_record_list()`      | List of Python record dictionaries    |
| `as_dict()`             | Dictionary of columns                 |
| `query_sql()`           | Relational queries against the result |
| `to_parquet()`          | Parquet export                        |
| `to_csv()`              | CSV export                            |

The native relational interfaces are generally more suitable for large results than bringing the complete output into Python dictionaries or pandas.

`as_pyarrow_table()` is useful for interoperability, but it still materializes a table in the Python process. For especially large results, disk-backed Parquet or native database relations may avoid unnecessary transfers.

Source: [https://moj-analytical-services.github.io/splink/api_docs/splink_dataframe.html](https://moj-analytical-services.github.io/splink/api_docs/splink_dataframe.html?utm_source=chatgpt.com)

### 12.2 Reusing computed data

The version 5 table-management API includes explicit registration of:

- Precomputed candidate pairs.
- Existing prediction tables.
- Term-frequency lookup tables.
- Additional user tables.

`register_table_predict()` can make previously computed predictions available for subsequent clustering or analysis.

`invalidate_cache()` provides explicit invalidation when input state changes.

Version 5's release history also records removal of the earlier implicit caching mechanism in favor of explicit cache/table-management interfaces. For developers familiar with version 4, this is a consequential lifecycle change.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink

+1



### 12.3 Model serialization and reuse

Splink supports saving a trained model as JSON using:

`linker.misc.save_model_to_json()`

The serialized representation includes the model configuration and learned parameters.

A new linker can then load that representation:

```
linker.misc.save_model_to_json("linkage_model.json", overwrite=True)# In a separate session, with registered input data:new_linker = Linker(new_data, settings="linkage_model.json")
```

The important distinction is that model serialization does not serialize the input database, term-frequency lifecycle, generated candidate pairs, or operational state of an entire entity-resolution service.

Those are separate relational artifacts and infrastructure responsibilities.

Splink 4 model JSON files remain loadable in Splink 5, according to the release notes.

Sources:

[https://moj-analytical-services.github.io/splink/api_docs/misc.html](https://moj-analytical-services.github.io/splink/api_docs/misc.html?utm_source=chatgpt.com)

[https://moj-analytical-services.github.io/splink/topic_guides/splink_fundamentals/settings.html](https://moj-analytical-services.github.io/splink/topic_guides/splink_fundamentals/settings.html?utm_source=chatgpt.com)

### 12.4 Privacy and sensitive-data handling

Record linkage often involves sensitive identifying attributes.

Some visualization and debugging outputs contain source-record values. For instance, `waterfall_chart()` has a `remove_sensitive_data` option, while interactive comparison viewers can include illustrative source-record pairs.

This distinction matters when exporting HTML diagnostics, sharing evaluation artifacts, or logging SQL.

Splink supplies statistical and relational functionality; access controls, safe storage, retention policies, and decisions about exposing underlying identifiers remain responsibilities of the hosting system.

## 13. Associated libraries and tooling

Splink's ecosystem is relatively compact, with its most important integrations occurring at the SQL-engine and data-exchange layers.

| Component              | Role and relationship to Splink                                                                 |
| ---------------------- | ----------------------------------------------------------------------------------------------- |
| DuckDB                 | Default SQL execution engine; provides vectorized relational processing and Parquet integration |
| PyArrow                | Core dependency supporting columnar data exchange and result materialization                    |
| SQLGlot                | Core dependency supporting SQL expressions and cross-dialect transformation                     |
| PySpark / Apache Spark | Optional distributed SQL backend                                                                |
| SQLAlchemy             | Connection and database-engine abstraction for PostgreSQL integration                           |
| Scala UDF libraries    | Backend-specific comparison functions used by the Spark implementation                          |
| pandas                 | Optional tabular input/output integration                                                       |
| Altair                 | Optional advanced chart conversion and export functionality                                     |
| igraph                 | Optional graph-related dependency, rather than a mandatory core runtime dependency              |
| Splink datasets        | Bundled dataset-access API backed by a separately maintained example-dataset repository         |

Splink's example datasets include synthetic people, historical persons, FEBRL linkage benchmarks, and paired financial transaction records. Some datasets include known entity IDs or clerical labels.

They are accessed through `splink_datasets` and downloaded on demand rather than embedded in the main package.

This makes them useful for checking comparison behavior, studying label-based evaluation, and reproducing examples.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink



Source repository:

[https://github.com/moj-analytical-services/splink_datasets](https://github.com/moj-analytical-services/splink_datasets?utm_source=chatgpt.com)

Dataset API:

[https://moj-analytical-services.github.io/splink/api_docs/datasets.html](https://moj-analytical-services.github.io/splink/api_docs/datasets.html?utm_source=chatgpt.com)

### 13.1 Dependency changes in version 5

Splink 5 reduces its mandatory runtime dependencies to three packages:

`duckdb`, `pyarrow`, and `sqlglot`.

It no longer requires pandas, NumPy, Altair, or Jinja2 for core operation.

Available PyPI extras are:

`altair`, `igraph`, `postgres`, `pyspark`, `spark`, and `sqlite`.

The published Python requirement is `>=3.10,<4.0`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

+1



A minimal installation is:

```
pip install "splink==5.0.0"
```

For a specific optional backend, use the corresponding published extra, for example:

```
pip install "splink[postgres]==5.0.0"
```

### 13.2 Relationship to fuzzy matching and semantic matching

Splink can replace substantial bespoke code when the problem requires combining multiple imperfect identifiers, estimating agreement reliability, and producing explainable matching probabilities.

However, it serves a different purpose from libraries primarily designed for nearest-neighbor search, dense embeddings, or a single high-performance fuzzy-string operation.

Those mechanisms can complement Splink:

- A fuzzy-string library can supply a custom similarity measure.
- A phonetic algorithm can generate additional matching features.
- A semantic model can produce a domain-specific similarity signal.
- A database or search index can generate specialized candidate sets.
- Splink can combine suitably represented evidence using a trained probabilistic model.

This is an architectural possibility, not an assertion that Splink provides native vector-index retrieval or a complete semantic-entity-resolution stack.

## 14. Significant changes from Splink 4 to Splink 5

The current release is a major version upgrade, so examples from earlier releases require care.

| Area                    | Version 4 → version 5                                                                      |
| ----------------------- | ------------------------------------------------------------------------------------------ |
| Core statistical model  | Unchanged; model JSON remains compatible                                                   |
| Input registration      | Inputs are now registered with `db_api.register()` before constructing `Linker`            |
| Backend ownership       | Derived from the registered `SplinkDataFrame`, rather than supplied separately to `Linker` |
| Incremental inference   | New `predict_within()` and `predict_between()` replace the older new-record workflow       |
| Explicit pair scoring   | New `score_pair()` and `score_pairs()` replace `compare_two_records()`                     |
| Match-weight output     | `mw_*` replaces former `bf_*`-style output                                                 |
| Prediction chunking     | New APIs for partitioned prediction and separately materialized candidate pairs            |
| Training scale          | Improved random-sampling estimation, EM `max_pairs`, prior-estimation sampling             |
| Intermediate data       | Direct DuckDB Parquet materialization                                                      |
| Profiling               | Dedicated DuckDB/Spark profiling APIs                                                      |
| Caching                 | Implicit caching removed; explicit registration and table management emphasized            |
| Dependencies            | Significantly reduced core dependency set                                                  |
| Athena backend          | Removed from version 5                                                                     |
| Legacy blocking salting | Removed in version 5                                                                       |

These distinctions are supported by the version 5 release announcement and tagged release history.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink

+1



A documentation-version caution: the current comparison-template reference is:

[https://moj-analytical-services.github.io/splink/topic_guides/comparisons/out_of_the_box_comparisons.html](https://moj-analytical-services.github.io/splink/topic_guides/comparisons/out_of_the_box_comparisons.html?utm_source=chatgpt.com)

The earlier `comparison_templates.html` page linked in section 5 contains legacy material and should not be treated as the authoritative Splink 5 comparison guide.

## 15. Compact version 5 example

The following illustrates the major interfaces without attempting a complete training methodology. It is an illustrative example, not an executed benchmark or validated statistical model.

```
from splink import (    DuckDBAPI,    Linker,    SettingsCreator,    block_on,    splink_datasets,)import splink.comparison_library as cldb_api = DuckDBAPI()records = db_api.register(    splink_datasets.fake_1000,    dataset_display_name="example_records",)settings = SettingsCreator(    link_type="dedupe_only",    blocking_rules_to_generate_predictions=[        block_on("first_name", "surname"),        block_on("surname", "dob"),    ],    comparisons=[        cl.ExactMatch("first_name"),        cl.ExactMatch("surname").configure(            term_frequency_adjustments=True        ),        cl.ExactMatch("dob"),    ],)linker = Linker(records, settings)# Estimate statistical parameters.linker.training.estimate_u_using_random_sampling()
```

The example illustrates how the distinct abstractions compose: registered backend relations, declarative comparison configuration, unsupervised parameter estimation, SQL-based prediction, and graph clustering.

It intentionally does not assign an arbitrary numerical match prior, since a realistic prior depends on the eligible pair population and properties of the data.

## 16. Important limitations and architectural boundaries

The main qualifications to Splink's capabilities can be summarized as follows.

| Concern                 | Consequential limitation                                                                                                           |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Candidate completeness  | Blocking can exclude genuine matches permanently from a prediction run                                                             |
| Statistical assumptions | Standard Fellegi–Sunter evidence aggregation does not model arbitrary conditional dependencies                                     |
| Parameter quality       | Unsupervised estimates depend on representative sampling, useful training blocks, and sufficient data                              |
| Match probabilities     | Calibration is model-dependent and should not be treated as guaranteed accuracy                                                    |
| Cluster semantics       | Connected-components transitivity can merge records that have little direct pairwise evidence                                      |
| Identity constraints    | Single-best-links supports particular source-uniqueness constraints, not arbitrary global optimization                             |
| Incremental operations  | New pairwise predictions do not automatically provide a complete persistent entity-ID governance system                            |
| Portability             | Custom SQL and backend-specific UDFs can reduce interoperability                                                                   |
| Scale                   | Very large workloads still require selective blocking, disk/memory planning, and suitable execution resources                      |
| Source quality          | Missing identifiers, corrupted attributes, correlated errors, and changing attribute distributions affect results                  |
| Golden records          | Record matching and clustering do not automatically choose authoritative values or resolve attribute conflicts                     |
| Operational lifecycle   | Model versioning, persistent identity stability, manual review, audits, and approval workflows remain surrounding responsibilities |

An especially important distinction is that an estimated cluster identifier is not necessarily a permanent business identifier. If the underlying evidence or clustering threshold changes, clusters can split or merge. Maintaining stable entity identity across successive model runs requires additional lifecycle semantics.

## 17. Final architectural perspective

Splink's most valuable capability is not any individual fuzzy comparator, clustering routine, or EM implementation.

It is the ability to combine those components into a coherent, configurable, statistically interpretable, SQL-executed entity-resolution system.

Three aspects stand out.

First, it provides a native alternative to hand-built matching heuristics. Learned likelihood ratios, term-frequency adjustments, compound comparisons, configurable matching levels, and labeled or unlabeled training offer a more systematic framework than independently assigning similarity thresholds and adding weighted scores.

Second, it makes entity resolution a relational workload. Blocking, feature comparisons, scoring, intermediate storage, and much of the analysis can execute through database engines rather than Python record-by-record loops. The version 5 improvements make that architecture more modular and observable.

Third, it supports investigation of the entire identity-resolution process. Blocking analysis, model-parameter diagnostics, pairwise explainability, threshold evaluation, cluster graph metrics, and interactive inspection are integrated capabilities.

The most consequential design choices concern the correctness of candidate generation, statistical calibration, and clustering semantics. Once those are appropriately characterized, Splink can supply a large fraction of the machinery needed for capable, explainable, and scalable probabilistic entity resolution.

### Additional primary resources

For deeper investigation beyond the specific API pages cited throughout:

- Official project examples: [https://moj-analytical-services.github.io/splink/demos/examples/examples_index.html](https://moj-analytical-services.github.io/splink/demos/examples/examples_index.html?utm_source=chatgpt.com)
- Tagged v5.0.0 release: [https://github.com/moj-analytical-services/splink/releases/tag/v5.0.0](https://github.com/moj-analytical-services/splink/releases/tag/v5.0.0?utm_source=chatgpt.com)
- Performance benchmark and reproduction: [https://moj-analytical-services.github.io/splink/topic_guides/performance/duckdb_performance_reprex.html](https://moj-analytical-services.github.io/splink/topic_guides/performance/duckdb_performance_reprex.html?utm_source=chatgpt.com)
- Source and test suite: [https://github.com/moj-analytical-services/splink](https://github.com/moj-analytical-services/splink?utm_source=chatgpt.com)
- Package metadata and optional dependencies: [https://pypi.org/project/splink/5.0.0/](https://pypi.org/project/splink/5.0.0/?utm_source=chatgpt.com)
- Original Splink research publication: [https://ijpds.org/article/view/1794](https://ijpds.org/article/view/1794?utm_source=chatgpt.com)

# Splink 5.0.0 — Advanced Capabilities Addendum

Research date: November 5, 2026\
Target version: Splink 5.0.0, released September 28, 2026\
Companion reference: Splink 5.0.0 — Comprehensive Python Library Capability Reference

## Scope

This addendum documents capabilities, configuration mechanisms, and behavioral distinctions that are absent from or insufficiently developed in the companion reference. It is intended to be read alongside that document rather than replace its explanations of Splink's statistical model, principal APIs, execution architecture, and clustering functionality.

The additions concentrate on multivalued candidate generation, missing-data semantics, compound and phonetic comparisons, probabilistic parameter control, evaluation outputs, and less obvious SQL execution mechanisms.

All described Splink functionality is verified against the version 5 documentation and associated upstream sources. Functionality provided by companion extensions or underlying database engines is distinguished from Splink's own interfaces.

## 1. Multivalued blocking through array explosion

Splink supports blocking directly on individual elements of array-valued attributes. This extends candidate generation beyond scalar equality and makes it possible to discover record pairs sharing any value in a multivalued field without permanently normalizing each source record into multiple records.

### 1.1 The `arrays_to_explode` mechanism

The interfaces are:

```
block_on(*col_names_or_exprs, arrays_to_explode=None)CustomRule(    blocking_rule,    sql_dialect=None,    arrays_to_explode=None,)
```

Both accept a list of array-valued input columns whose elements should participate individually in blocking.

For example:

```
from splink import block_onalias_rule = block_on(    "aliases",    arrays_to_explode=["aliases"],)
```

If record A contains `["Robert", "Bob"]` and record B contains `["Bob", "Bobby"]`, the rule can generate the pair because the arrays share `"Bob"`.

The underlying candidate-generation operation conceptually expands array elements into join keys, applies equality joins, and maps resulting matches back to original record pairs.

This differs from a conventional scalar blocking rule, which compares complete column values, and from an array-intersection comparison, which evaluates similarity only after the candidate pair has been generated.

Splink's current cookbook explicitly demonstrates array-exploding blocking in conjunction with `ArrayIntersectAtSizes`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink+1



### 1.2 Combining array blocking with compound conditions

Array expansion can participate in compound blocking expressions.

For instance, records might contain multiple historical postal codes and a scalar country field:

```
blocking_rule = block_on(    "historical_postcodes",    "country",    arrays_to_explode=["historical_postcodes"],)
```

The intended semantics are that a pair must share an individual historical postcode and agree on country.

This permits selective matching over multivalued attributes without requiring a general array-overlap predicate across every potential pair.

`CustomRule` supplies a complementary route when the blocking condition requires more elaborate SQL.

### 1.3 Interactions with comparison modeling

Array explosion creates candidates; it does not determine the probabilistic evidence associated with the shared array elements.

After candidate generation, Splink can apply an array-aware comparison such as:

```
import splink.comparison_library as clcomparison = cl.ArrayIntersectAtSizes(    "historical_postcodes",    [2, 1],)
```

A candidate found because of one shared value can therefore receive different comparison evidence from a candidate whose arrays share multiple values.

This separation is valuable because blocking does not need to encode the complete strength or structure of a match. A relatively permissive array-based candidate rule can be combined with a more discriminating probabilistic comparison.

### 1.4 Performance and semantic limitations

Array-exploding blocking introduces several considerations.

Intermediate cardinality. A record with many array elements contributes multiple candidate join keys. The computational benefit depends on whether the resulting equality joins are sufficiently selective.

Skewed elements. Common aliases, generic identifiers, or frequently occurring classifications can generate disproportionately large candidate groups. Frequency-based evidence weighting does not itself reduce the candidate-generation cost.

Overlapping candidates. Two records might share several array values or satisfy multiple blocking rules. Splink handles candidate deduplication, so duplicated candidate-generation paths do not need to become separate probabilistic predictions.

Element semantics. Exact equality of individual array elements is still subject to normalization. Array explosion does not introduce fuzzy matching between different elements unless the blocking predicate explicitly supplies that behavior.

The mechanism is particularly consequential when source records contain multiple aliases, addresses, associated identifiers, classifications, or other alternative representations.

Primary sources

Blocking API:\
[https://moj-analytical-services.github.io/splink/api_docs/blocking.html](https://moj-analytical-services.github.io/splink/api_docs/blocking.html?utm_source=chatgpt.com)

Official array-blocking example:\
[https://moj-analytical-services.github.io/splink/demos/examples/duckdb_no_test/cookbook.html](https://moj-analytical-services.github.io/splink/demos/examples/duckdb_no_test/cookbook.html?utm_source=chatgpt.com)

## 2. Missing-value semantics, invalid data, and neutral evidence

Splink's treatment of missing comparison values is a substantive statistical modeling choice, not simply an implementation detail of SQL `NULL` handling.

### 2.1 Null comparison levels contribute zero evidence

A comparison level marked with:

```
is_null_level=True
```

has two special behaviors:

- Its \\(m\\) and \\(u\\) probabilities are not estimated.
- Its contribution to the pairwise match weight is zero.

If a comparison observes missing data and enters its null level, it neither increases nor decreases the evidence for a match.

In the base-2 log-likelihood formulation, this is equivalent to assigning a neutral likelihood ratio of one:

\\[ W\_{\mathrm{null}}=0,\qquad 2^{W\_{\mathrm{null}}}=1 \\]

For example, suppose a pair has evidence weights of \\(+5\\) from one comparison and \\(-2\\) from another. If a third comparison is null, its contribution is zero; the evidence sum remains \\(+3\\), before incorporating the model prior and other adjustments.

The absence of a value is therefore distinguished from disagreement between two observed values.

Splink's settings documentation explicitly associates this treatment with an assumption that missing information can be ignored for linkage evidence under a missing-at-random model.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink



### 2.2 When neutral missingness can be misleading

The distinction becomes important when missingness is statistically informative.

For example:

- One source systematically omits secondary identifiers.
- Certain records contain missing addresses because of a particular collection process.
- Some identifiers are absent specifically when they could not be validated.
- Missing information is correlated with the identity of the entity or its source.

Under these conditions, treating every missing observation as neutral may discard relevant information. It can also interact with Splink's conditional-independence assumptions and the representativeness of its parameter estimates.

Splink does not automatically estimate a separate probabilistic missingness model.

If missingness itself should contribute evidence, it can instead be represented using suitable derived attributes or custom comparison conditions, with their probabilities estimated or otherwise justified explicitly.

That is a modeling extension, rather than the default meaning of `NullLevel`.

### 2.3 Invalid-value detection using `NullLevel`

The comparison-level library exposes:

```
NullLevel(    col_name,    valid_string_pattern=None,)
```

The `valid_string_pattern` argument allows validation to be incorporated into null handling.

Splink applies regular-expression extraction and then evaluates whether the resulting value is null. Consequently, strings that do not contain a valid extractable representation can be directed into the null comparison level.

This provides a way to treat malformed input as unavailable evidence rather than allowing two identically malformed values to count as an exact match.

The mechanism does not perform general schema validation or repair malformed values. It determines how such values participate in the comparison model.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink



### 2.4 Specialized invalid-value behavior

Several built-in comparisons incorporate related controls:

| Comparison                           | Configuration               | Behavior                                                                                          |
| ------------------------------------ | --------------------------- | ------------------------------------------------------------------------------------------------- |
| `PostcodeComparison`                 | `invalid_postcodes_as_null` | Treats invalid UK postcode representations as missing evidence                                    |
| `DateOfBirthComparison`              | `invalid_dates_as_null`     | When using string inputs, prevents malformed dates from being treated as ordinary matching values |
| `AbsoluteTimeDifferenceAtThresholds` | `invalid_dates_as_null`     | Supports null treatment for invalid date/time strings                                             |

These are comparison-specific facilities rather than one universal data-validation mechanism.

For instance, `PostcodeComparison` defaults `invalid_postcodes_as_null` to `False`, while the documented date-comparison defaults differ.

The interaction between validation and evidence is consequential: identifying a value as invalid can change a potentially positive or negative comparison result into a neutral contribution.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink



### 2.5 Architectural significance

Splink can distinguish three states that a simplistic matching implementation may collapse:

1. Agreement between valid observed values.
2. Disagreement between valid observed values.
3. Unavailable or invalid evidence that should not contribute to the score.

These states have different statistical implications.

Native null-level handling avoids the need for every caller to construct separate missing-value scoring rules, while custom levels permit other assumptions when the missingness process itself requires modeling.

Primary sources

Settings and null-weight semantics:\
[https://moj-analytical-services.github.io/splink/api_docs/settings_dict_guide.html](https://moj-analytical-services.github.io/splink/api_docs/settings_dict_guide.html?utm_source=chatgpt.com)

Comparison-level API:\
[https://moj-analytical-services.github.io/splink/api_docs/comparison_level_library.html](https://moj-analytical-services.github.io/splink/api_docs/comparison_level_library.html?utm_source=chatgpt.com)

Comparison templates:\
[https://moj-analytical-services.github.io/splink/api_docs/comparison_library.html](https://moj-analytical-services.github.io/splink/api_docs/comparison_library.html?utm_source=chatgpt.com)

## 3. Phonetic feature engineering and native comparison integration

Splink can incorporate phonetic similarity into its ordinary probabilistic comparison model. Its `NameComparison` template specifically supports Double Metaphone representations, while the companion DuckDB `splink_udfs` extension supplies SQL functions for generating those representations.

This combination allows phonetic matching to participate in both candidate generation and evidence scoring without requiring a separate Python matching subsystem.

### 3.1 Double Metaphone in `NameComparison`

The template exposes:

```
NameComparison(    col_name,    *,    jaro_winkler_thresholds=[0.92, 0.88, 0.7],    dmeta_col_name=None,)
```

When `dmeta_col_name` is supplied, Splink introduces a phonetic comparison level based on the intersection of two arrays of Double Metaphone codes.

The input column must already exist and contain arrays of one or two phonetic codes. Splink does not automatically compute those codes when the comparison is instantiated.

For example:

```
import splink.comparison_library as clcomparison = cl.NameComparison(    "person_name",    dmeta_col_name="person_name_phonetic",)
```

The documented default ordering places the phonetic-intersection condition between stronger and weaker Jaro–Winkler similarity thresholds.

This produces an important distinction: phonetic agreement is not simply appended to an existing string-similarity score. It becomes its own mutually exclusive comparison level, with an estimable likelihood ratio.

A pair might therefore fail stronger character-similarity thresholds but receive evidence from phonetic agreement.

As with other comparison levels, its statistical contribution depends on the estimated matching and nonmatching distributions. Phonetic agreement is not inherently proof of identity.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink+1



### 3.2 The `splink_udfs` DuckDB extension

The DuckDB community extension `splink_udfs` provides functions that complement Splink's SQL comparison architecture.

Its published functionality includes:

| Function                                  | Capability                                                    |
| ----------------------------------------- | ------------------------------------------------------------- |
| `double_metaphone(str)`                   | Generate primary and alternative phonetic codes               |
| `soundex(str)`                            | Generate a Soundex phonetic representation                    |
| `strip_diacritics(str)` / `unaccent(str)` | Normalize accented text                                       |
| `ngrams(list, n)`                         | Generate n-grams from lists                                   |
| `levenshtein`                             | Alternative implementation of edit distance                   |
| `damerau_levenshtein`                     | Alternative implementation supporting adjacent transpositions |

The extension also exposes additional functions, including address-related functionality, whose behavior is maintained separately from Splink's core comparison API.

The documented installation and loading interface is:

```
INSTALL splink_udfs FROM community;
LOAD splink_udfs;
```

These statements are executed against a DuckDB connection. That same connection can subsequently be supplied to `DuckDBAPI` so derived features and Splink's relational operations share an execution environment.

The extension is optional. Its function availability and binary compatibility depend on the DuckDB version and supported platform, rather than solely on the installed Splink version.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB Community Extensions



### 3.3 Combining phonetic generation, blocking, and scoring

A SQL-centered workflow can compose these capabilities as follows:

1. Normalize source strings using DuckDB expressions or compatible extension functions.
2. Generate Double Metaphone arrays as derived columns.
3. Use the arrays in `NameComparison`.
4. Optionally generate candidate pairs through phonetic-code equality, including array-exploding blocking.
5. Estimate the corresponding probabilistic evidence from training data.

The fourth and fifth operations should be distinguished.

Phonetic blocking increases candidate coverage for differently spelled values with matching phonetic codes. Phonetic comparison levels determine how much evidence those matches contribute.

A phonetic blocking rule can also be highly permissive. Different names may collapse to the same phonetic representation, creating large candidate groups. Such rules are often more effective when combined with additional selective attributes.

The `splink_udfs` implementation is specific to DuckDB. Other Splink backends require compatible functions or separately generated phonetic columns.

Primary sources

Phonetic algorithms and name comparison:\
[https://moj-analytical-services.github.io/splink/topic_guides/comparisons/phonetic.html](https://moj-analytical-services.github.io/splink/topic_guides/comparisons/phonetic.html?utm_source=chatgpt.com)

Feature-engineering guide:\
[https://moj-analytical-services.github.io/splink/topic_guides/data_preparation/feature_engineering.html](https://moj-analytical-services.github.io/splink/topic_guides/data_preparation/feature_engineering.html?utm_source=chatgpt.com)

DuckDB extension documentation:\
[https://duckdb.org/community_extensions/extensions/splink_udfs](https://duckdb.org/community_extensions/extensions/splink_udfs?utm_source=chatgpt.com)

## 4. Advanced compound comparisons and evidence interactions

Splink's specialized comparison templates encode more than collections of independent similarity thresholds. Some model relationships among multiple attributes, alternative matching patterns, and the frequency of compound identifiers.

These structures can reduce the need for custom comparison logic and, more importantly, avoid some of the statistical problems associated with treating highly related observations as separate evidence.

### 4.1 `ForenameSurnameComparison`: joint identity evidence

The template accepts:

```
ForenameSurnameComparison(    forename_col_name,    surname_col_name,    *,    jaro_winkler_thresholds=[0.92, 0.88],    forename_surname_concat_col_name=None,)
```

Its comparison hierarchy distinguishes:

- Both names agreeing exactly.
- Forename and surname appearing in reversed positions.
- Both names meeting stronger approximate-similarity thresholds.
- Both names meeting weaker approximate-similarity thresholds.
- Surname-only exact agreement.
- Forename-only exact agreement.
- Remaining disagreements.

The template also has a special null condition for the compound comparison. Its documented generated form treats the joint evidence as null when both name components are unavailable, rather than automatically discarding every pair in which either individual name is absent.

This permits partial name evidence to remain usable where appropriate.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink



#### Compound-name term-frequency adjustments

The `forename_surname_concat_col_name` parameter is particularly consequential.

Consider two common names, John and Smith. The frequencies of the individual components do not necessarily describe the empirical frequency of the full name John Smith.

Likewise, some individually common names form comparatively uncommon combinations.

If a precomputed column contains the canonical full-name representation, the template can use that column for term-frequency adjustment when the full name agrees.

```
import splink.comparison_library as clcomparison = cl.ForenameSurnameComparison(    "first_name",    "surname",    forename_surname_concat_col_name="full_name",)
```

This allows the evidence for complete-name agreement to reflect the observed frequency of the complete name, rather than relying exclusively on separate component frequencies.

It also avoids automatically counting forename and surname as two independent probabilistic comparisons in the manner of a naïve field-by-field model.

The compound comparison still has modeling assumptions: it does not learn an unrestricted joint probability distribution over every possible name transformation or error pattern.

Source: [https://moj-analytical-services.github.io/splink/topic_guides/data_preparation/feature_engineering.html](https://moj-analytical-services.github.io/splink/topic_guides/data_preparation/feature_engineering.html?utm_source=chatgpt.com)

### 4.2 `EmailComparison`: full identifiers versus partial identifiers

`EmailComparison` distinguishes several forms of agreement:

| Level                        | Evidence represented                                     |
| ---------------------------- | -------------------------------------------------------- |
| Exact full-email match       | Identical complete address                               |
| Exact username match         | Same local part, potentially different domains           |
| Approximate full-email match | String similarity across complete addresses              |
| Approximate username match   | Similar local parts across potentially different domains |
| Other                        | Remaining combinations                                   |

The distinction is useful because a complete email address and its username component have different identity semantics.

Agreement on an entire address is generally more discriminating than agreement on a short or commonly used username.

Conversely, users can retain a username while moving between organizations or email providers.

By representing these cases as separate levels, Splink can learn different \\(m/u\\) ratios rather than assigning the same weight to every apparent email agreement.

The template is not a comprehensive email-identity normalization engine. Provider-specific aliasing, plus-address handling, domain equivalence, and mailbox ownership semantics require separate treatment where relevant.

Source: [https://moj-analytical-services.github.io/splink/api_docs/comparison_library.html](https://moj-analytical-services.github.io/splink/api_docs/comparison_library.html?utm_source=chatgpt.com)

### 4.3 `PostcodeComparison`: hierarchical and geographic agreement

`PostcodeComparison` is specialized for UK postcode structure. It does not provide a universal model for all national postal-code systems.

Its hierarchy includes agreement at the full-postcode, sector, district, and area levels.

This provides graduated evidence rather than treating every nonidentical postcode as complete disagreement.

The template can additionally incorporate geographic distance using precomputed latitude and longitude columns:

```
comparison = cl.PostcodeComparison(    "postcode",    lat_col="latitude",    long_col="longitude",    km_thresholds=[1, 10],)
```

When coordinates are provided, the comparison can distinguish postal-code disagreement from geographic proximity.

The coordinates must be supplied beforehand. Splink does not automatically geocode arbitrary postal addresses as part of this comparison.

#### Evidence dependence

Postcode hierarchy and geographic distance are strongly related signals.

Modeling them inside one compound comparison reduces the risk of separately counting full-postcode agreement, postcode-sector agreement, and geographic proximity as independent evidence.

This is useful, but does not eliminate every dependence. A separate city comparison, for example, may still be highly correlated with postcode evidence.

Source: [https://moj-analytical-services.github.io/splink/api_docs/comparison_library.html](https://moj-analytical-services.github.io/splink/api_docs/comparison_library.html?utm_source=chatgpt.com)

### 4.4 Term-frequency configuration at comparison and level scope

The existing reference describes term-frequency adjustments in detail. An additional distinction concerns where they are enabled.

At the comparison level, the convenience configuration:

```
cl.ExactMatch("surname").configure(    term_frequency_adjustments=True)
```

applies to exact-match comparison levels.

More specialized behavior is available through comparison-level configuration, including:

`tf_adjustment_column`, `tf_adjustment_weight`, `tf_minimum_u_value`, and `disable_tf_exact_match_detection`.

The last setting changes an important detail: it allows the adjustment to use the current level's \\(u\\) value rather than automatically using the \\(u\\) value associated with the exact-match level.

This matters for custom fuzzy or compound levels where the appropriate nonmatch frequency is not the ordinary exact-agreement frequency.

The distinction is between enabling a convenient default frequency adjustment and explicitly defining the statistical baseline for a specialized comparison outcome.

Primary sources

Comparison library and configuration:\
[https://moj-analytical-services.github.io/splink/api_docs/comparison_library.html](https://moj-analytical-services.github.io/splink/api_docs/comparison_library.html?utm_source=chatgpt.com)

Comparison-level configuration:\
[https://moj-analytical-services.github.io/splink/api_docs/comparison_level_library.html](https://moj-analytical-services.github.io/splink/api_docs/comparison_level_library.html?utm_source=chatgpt.com)

## 5. Marginal blocking-rule analysis and candidate provenance

Splink's blocking analysis provides more information than the total number of candidates generated by a rule set.

It can distinguish the independent computational contribution of each rule, account for overlap between rules, and identify unusually expensive blocking values.

### 5.1 Marginal versus cumulative comparisons

`count_comparisons_from_blocking_rules()` returns one record per supplied blocking rule.

Two output fields are particularly important:

- `marginal_comparison_count`: additional candidate pairs introduced by the rule, excluding pairs generated by earlier rules.
- `cumulative_comparison_count`: total distinct candidate pairs generated through the current rule.

Suppose three blocking rules produce the following illustrative counts:

| Rule                      | Marginal pairs | Cumulative pairs |
| ------------------------- | -------------- | ---------------- |
| Exact name and birth year | 12,000         | 12,000           |
| Email username            | 4,000          | 16,000           |
| Postcode and surname      | 2,500          | 18,500           |

The third rule may generate many raw pair occurrences, but contributes only 2,500 previously unseen candidates.

This distinguishes the computational cost of executing a rule from its contribution to candidate coverage.

It also illustrates why overlapping blocking rules cannot be assessed solely from their independent candidate counts.

### 5.2 Sampling behavior and estimation uncertainty

In version 5, blocking analysis defaults to `record_sample_proportion=0.05`.

The implementation samples records on both sides of the blocking join, calculates the resulting candidate counts, and scales the results to estimate full-dataset counts.

For a sampling proportion \\(p\\), the approximate reduction in candidate comparisons is proportional to \\(p^2\\), assuming the sampled pairs are representative.

This makes blocking analysis substantially less expensive on large datasets, but introduces uncertainty, particularly for rare matching patterns.

The documented API supports:

```
linker.blocking_analysis.count_comparisons_from_blocking_rules(    record_sample_proportion=1.0)
```

to request exact counts.

Small sampled pair counts can produce unstable estimates even when the sampled record population appears reasonably large. Splink's scaling tutorial demonstrates this issue and the associated warnings.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink+1



### 5.3 The `match_key` output

Prediction results can include a `match_key` column identifying the blocking-rule path associated with candidate generation.

Its meaning is operational rather than statistical.

A candidate may satisfy several blocking rules, but Splink avoids generating separate scored copies of the same pair. Consequently, its recorded blocking-rule attribution should not be interpreted as an exhaustive list of all rules the pair satisfies.

It is also not a measure of confidence, similarity, or relative rule quality.

Changing rule order can affect marginal candidate counts and attribution, even when the union of generated candidates remains unchanged.

This distinction matters when inspecting which blocking rules appear to contribute useful matches. Observed match-key frequencies are not equivalent to a controlled measurement of the independent recall provided by each rule.

### 5.4 Pre-filter block sizes versus actual candidate counts

`n_largest_blocks()` identifies large groups associated with blocking values.

Its documented analysis occurs before non-equality filtering conditions are applied. By contrast, `count_comparisons_from_blocking_rules()` calculates candidate counts after the relevant filters.

A large block identified by the first method may therefore generate fewer actual scored pairs if the blocking rule contains additional filtering predicates.

The methods answer different questions:

- Where are potentially expensive groups concentrated?
- How many candidates survive the complete blocking rule?
- How much additional candidate coverage does a rule provide?

Together, they provide a more useful basis for analyzing blocking workloads than raw block cardinality alone.

Primary sources

Blocking analysis API:\
[https://moj-analytical-services.github.io/splink/api_docs/blocking_analysis.html](https://moj-analytical-services.github.io/splink/api_docs/blocking_analysis.html?utm_source=chatgpt.com)

Large-scale blocking analysis:\
[https://moj-analytical-services.github.io/splink/demos/tutorials/09_scaling_up_techniques.html](https://moj-analytical-services.github.io/splink/demos/tutorials/09_scaling_up_techniques.html?utm_source=chatgpt.com)

## 6. Prediction output structure and retention controls

Splink's prediction tables are not limited to record identifiers and final match probabilities. They can retain comparison outcomes, individual evidence contributions, term-frequency information, and source attributes.

The model settings determine which information remains available for downstream relational analysis.

### 6.1 Output fields and evidence representation

A prediction may expose several distinct classes of columns.

| Field or prefix                        | Interpretation                                   |
| -------------------------------------- | ------------------------------------------------ |
| `unique_id_l`, `unique_id_r`           | Source-record identifiers                        |
| `source_dataset_l`, `source_dataset_r` | Source identities for linkage workflows          |
| `match_weight`                         | Aggregated log-base-2 match weight               |
| `match_probability`                    | Model-derived match probability                  |
| `match_key`                            | Blocking-rule attribution                        |
| `gamma_*`                              | Discrete comparison-level outcome identifiers    |
| `mw_*`                                 | Individual comparison match-weight contributions |
| `tf_*`                                 | Term-frequency information used in scoring       |
| `*_l`, `*_r`                           | Retained source attributes from the two records  |

The generated prefixes are configurable.

The distinction between `gamma_*` and `mw_*` is particularly useful.

A gamma value identifies the categorical outcome of a comparison. It says which comparison level was selected.

An individual match-weight value represents the statistical evidence associated with that outcome, potentially including its configured term-frequency adjustment.

Two pairs can therefore occupy the same nominal comparison category but receive different final evidence when their frequency adjustments differ.

This makes structured prediction outputs useful for analyzing why apparently similar pairs receive different scores.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink+1



### 6.2 Retaining source attributes and intermediate calculations

The relevant settings include:

```
retain_matching_columns=Trueretain_intermediate_calculation_columns=Falseadditional_columns_to_retain=[]
```

These are the documented defaults.

`retain_matching_columns` preserves original attributes used in the comparison expressions. Disabling it can reduce the amount of data carried through prediction operations.

`retain_intermediate_calculation_columns` controls retention of detailed scoring calculations, including individual evidence contributions. Enabling it increases observability at the cost of larger intermediate or output relations.

`additional_columns_to_retain` preserves fields that would otherwise be excluded because they are not required by the comparison model.

The settings operate independently of whether Splink can compute the relevant comparisons. A source field may be necessary during scoring without needing to remain in the final prediction table.

Retaining extra fields can increase I/O, materialized table size, and the volume of identifying information present in downstream artifacts.

A related interaction is that some interactive diagnostics require more information than minimal prediction outputs provide. The comparison-viewer dashboard, for example, requires matching columns and intermediate calculations to be retained.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink+2



### 6.3 Filtering predictions at materialization time

The principal prediction interfaces accept:

```
threshold_match_probability=...threshold_match_weight=...
```

These thresholds filter the scored pairs returned by inference.

Their performance benefit comes primarily from retaining and writing fewer low-scoring results, especially when the prediction output would otherwise be very large.

They should not be understood as reducing the candidate-generation workload. Candidates must still be generated and evaluated sufficiently to determine whether they satisfy the threshold.

Retaining only high-confidence links can also discard evidence useful for subsequent calibration, review, or threshold sensitivity analysis.

The relevant distinction is between reducing the output relation and reducing the number of candidate comparisons performed.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink+1



Primary sources

Settings reference:\
[https://moj-analytical-services.github.io/splink/api_docs/settings_dict_guide.html](https://moj-analytical-services.github.io/splink/api_docs/settings_dict_guide.html?utm_source=chatgpt.com)

Inference API:\
[https://moj-analytical-services.github.io/splink/api_docs/inference.html](https://moj-analytical-services.github.io/splink/api_docs/inference.html?utm_source=chatgpt.com)

Performance drivers:\
[https://moj-analytical-services.github.io/splink/topic_guides/performance/drivers_of_performance.html](https://moj-analytical-services.github.io/splink/topic_guides/performance/drivers_of_performance.html?utm_source=chatgpt.com)

## 7. Fine-grained training controls and statistical parameter lifecycle

Splink provides additional parameter-control functionality beyond selecting EM training rules, fixing whole parameter families, or estimating \\(m\\) and \\(u\\) probabilities.

These controls determine when estimation stops, which individual probabilities can change, and how custom statistical assumptions interact with learned parameters.

### 7.1 EM convergence and iteration limits

The model settings include:

| Setting          | Default  | Meaning                                            |
| ---------------- | -------- | -------------------------------------------------- |
| `em_convergence` | `0.0001` | Maximum permitted parameter change for convergence |
| `max_iterations` | `25`     | Upper bound on EM iterations                       |

`em_convergence` applies to the maximum parameter change between iterations.

`max_iterations` terminates training after the configured number of iterations, even if the convergence criterion has not been met.

These controls address a different dimension from `max_pairs`, which approximately constrains the size of the training workload.

For example, reducing the number of training pairs does not guarantee convergence in fewer iterations. Likewise, increasing the iteration limit cannot correct inadequate training coverage or unidentifiable parameters.

The interaction is important when interpreting EM training histories: training can terminate because it converged, or because it reached an iteration limit.

Source: [https://moj-analytical-services.github.io/splink/api_docs/settings_dict_guide.html](https://moj-analytical-services.github.io/splink/api_docs/settings_dict_guide.html?utm_source=chatgpt.com)

### 7.2 Fixing individual comparison-level probabilities

Comparison-level creators support:

`m_probability`, `u_probability`, `fix_m_probability`, and `fix_u_probability`.

This allows fixed statistical assumptions to be applied at a finer granularity than an entire comparison or complete EM session.

For example, an individual level can be configured to preserve a supplied \\(m\\) estimate:

```
import splink.comparison_level_library as clllevel = cll.ExactMatchLevel("external_identifier").configure(    m_probability=0.99,    fix_m_probability=True,)
```

This is an illustrative comparison-level configuration, not an assertion that `0.99` is appropriate for a particular identifier.

The key distinction is between supplying a numerical value and freezing that value during training.

An explicitly initialized probability may otherwise be eligible for estimation. Setting the corresponding `fix_*` option expresses the stronger requirement that training should preserve it.

The mechanism supports mixed models in which some comparison outcomes are learned and others remain constrained by expert knowledge, labeled evidence, or externally estimated parameters.

It does not establish that the manually specified probabilities are statistically consistent with the remaining estimated parameters.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink



### 7.3 Comparison-level versus training-session controls

There are two different scopes of parameter control.

At the comparison-level scope, `fix_m_probability` and `fix_u_probability` constrain individual outcomes.

At the EM-session scope, `fix_m_probabilities` and `fix_u_probabilities` determine whether whole parameter families are updated during that training operation.

The latter controls are broader and can override the practical ability to estimate a family even when individual levels are otherwise trainable.

A related distinction concerns the match prior. An EM session can estimate an internal prior while not automatically propagating that estimate back into the overall linkage model.

Consequently, convergence of an EM session does not necessarily imply that every estimated quantity becomes part of the subsequently applied prediction model.

These behaviors are important when interpreting multiple EM training passes as a coherent final parameter set.

### 7.4 Training assumptions and term-frequency adjustments

EM training can use the `estimate_without_term_frequencies` option to skip term-frequency adjustments during its iterations.

That can reduce computational cost, but changes the statistical calculation used during training. It should not be described as a numerically identical optimization.

There are therefore distinct choices concerning:

- Which observations enter an EM session.
- Which probability parameters are fixed.
- Whether term-frequency adjustments participate in estimation.
- When iterative estimation stops.
- Which estimated prior is propagated into the final model.

Splink exposes these controls without requiring callers to implement a separate EM algorithm, but their composition determines the statistical model actually fitted.

Primary sources

Training API:\
[https://moj-analytical-services.github.io/splink/api_docs/training.html](https://moj-analytical-services.github.io/splink/api_docs/training.html?utm_source=chatgpt.com)

Comparison-level configuration:\
[https://moj-analytical-services.github.io/splink/api_docs/comparison_level_library.html](https://moj-analytical-services.github.io/splink/api_docs/comparison_level_library.html?utm_source=chatgpt.com)

Model settings:\
[https://moj-analytical-services.github.io/splink/api_docs/settings_dict_guide.html](https://moj-analytical-services.github.io/splink/api_docs/settings_dict_guide.html?utm_source=chatgpt.com)

## 8. Structured evaluation outputs and clerical-label semantics

Splink's evaluation functions are capable of producing relational accuracy tables, not only charts. They also distinguish thresholding probabilistic ground-truth labels from thresholding predicted match probabilities.

These distinctions are particularly relevant when evaluation outputs need to be analyzed programmatically rather than only inspected visually.

### 8.1 Accessing the underlying evaluation tables

The accuracy-analysis methods support an `output_type` parameter.

Documented values include:

| `output_type`           | Result                                                              |
| ----------------------- | ------------------------------------------------------------------- |
| `"threshold_selection"` | Interactive threshold-selection visualization                       |
| `"accuracy"`            | Accuracy metrics visualization                                      |
| `"roc"`                 | Receiver operating characteristic chart                             |
| `"precision_recall"`    | Precision–recall chart                                              |
| `"table"`               | `SplinkDataFrame` containing threshold-dependent evaluation results |

The table output is especially useful because it exposes the data underlying the visualizations.

For example:

```
accuracy_table = linker.evaluation.accuracy_analysis_from_labels_table(    labels_table,    output_type="table",    add_metrics=["f1", "phi"],)
```

The resulting relation includes threshold values, confusion-matrix counts, and derived evaluation metrics.

This enables threshold analysis, comparisons across model variants, and more specialized statistical calculations using the same relational interfaces as other Splink outputs.

The returned `SplinkDataFrame` can also be queried directly with SQL, avoiding conversion of the entire accuracy table into pandas.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink+1



### 8.2 Threshold rounding and evaluation-table cardinality

Accuracy analysis accepts:

```
match_weight_round_to_nearest=0.1
```

The parameter controls rounding of match-weight thresholds when constructing evaluation results.

Without rounding, a large labeled dataset containing many distinct match weights can produce a very large set of threshold points.

Rounding consolidates nearby thresholds, reducing the number of distinct evaluation rows or chart points.

This improves tractability at the cost of threshold resolution.

It should therefore be understood as an evaluation-output granularity control, not a change to the model's underlying pairwise scoring function.

### 8.3 Probabilistic clerical scores versus prediction thresholds

Splink's labeled-pair evaluation supports a `clerical_match_score` column.

This can represent a probability-like assessment supplied by a reviewer or another labeling process, rather than only a binary match indicator.

In `accuracy_analysis_from_labels_table()`, `threshold_match_probability` controls how such scores are converted into binary ground-truth labels.

For example, a clerical score of `0.8` may be considered a positive label when the truth-label threshold is `0.5`, but not when the threshold is `0.9`.

This ground-truth threshold is distinct from the model-decision threshold used to accept predicted record pairs.

The distinction is especially important because the parameter name `threshold_match_probability` also appears in other interfaces.

In `prediction_errors_from_labels_table()`, the parameter determines the match-probability threshold used to classify predictions for false-positive and false-negative analysis.

Consequently, the meaning of the threshold must be interpreted in the context of the particular evaluation API.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink



### 8.4 Training labels and evaluation labels are not interchangeable

There is an additional asymmetry between supervised parameter estimation and evaluation.

`estimate_m_from_pairwise_labels()` treats supplied record pairs as positive matches for estimating the match distribution.

It does not interpret every supplied clerical score as a fractional positive contribution to the \\(m\\)-probability estimates.

Evaluation can instead use clerical-score thresholds to distinguish positive and negative labels.

This means that probabilistic or uncertain annotations cannot automatically be reused with identical semantics across the two operations.

A probabilistic labeling workflow and supervised model estimation may therefore require different transformations of the same source annotations.

Primary sources

Evaluation API:\
[https://moj-analytical-services.github.io/splink/api_docs/evaluation.html](https://moj-analytical-services.github.io/splink/api_docs/evaluation.html?utm_source=chatgpt.com)

Evaluation tutorial:\
[https://moj-analytical-services.github.io/splink/demos/tutorials/07_Evaluation.html](https://moj-analytical-services.github.io/splink/demos/tutorials/07_Evaluation.html?utm_source=chatgpt.com)

Accuracy-table examples:\
[https://moj-analytical-services.github.io/splink/charts/accuracy_analysis_from_labels_table.html](https://moj-analytical-services.github.io/splink/charts/accuracy_analysis_from_labels_table.html?utm_source=chatgpt.com)

## 9. Advanced DuckDB execution and optimization

Splink's DuckDB backend provides additional optimization opportunities associated with SQL expression evaluation, materialization strategy, and prediction partitioning.

These mechanisms are largely orthogonal to the statistical model: they concern how comparisons are executed and how relational intermediate results are retained.

### 9.1 Eliminating repeated fuzzy-function evaluation

A comparison containing several thresholds can generate SQL resembling:

```
CASE
    WHEN value_l IS NULL OR value_r IS NULL THEN -1
    WHEN value_l = value_r THEN 3
    WHEN jaro_winkler_similarity(value_l, value_r) >= 0.9 THEN 2
    WHEN jaro_winkler_similarity(value_l, value_r) >= 0.8 THEN 1
    ELSE 0
END
```

The similarity function appears twice in this example.

Although DuckDB can perform common-subexpression elimination, the presence of a preceding null-handling branch can prevent the optimizer from moving the similarity calculation outside the `CASE` expression.

This restriction preserves SQL evaluation semantics.

For example, a similarity function might raise an exception on certain invalid inputs. An early branch could intentionally prevent that function from being evaluated for those rows.

Moving the function outside the conditional structure could invalidate that protection.

### 9.2 Conditional function-hoisting optimization

Splink's official DuckDB performance guide documents a workaround for functions known to be safe to evaluate on every row.

The technique adds a logically impossible function comparison to the first comparison level.

Because the function then appears in the first branch, DuckDB can recognize that evaluating it once and reusing the result does not violate the protection provided by earlier branches.

An illustrative comparison is:

```
import splink.comparison_library as climport splink.comparison_level_library as cllcomparison = cl.CustomComparison(    output_column_name="label",    comparison_levels=[        cll.CustomLevel(            "jaro_winkler_similarity(label_l, label_r) = -1 "            "OR label_l IS NULL OR label_r IS NULL"        ).configure(is_null_level=True),        cll.ExactMatchLevel("label"),        cll.JaroWinklerLevel("label", 0.93),        cll.JaroWinklerLevel("label", 0.82),        cll.ElseLevel(),    ],)
```

Jaro–Winkler similarity is bounded between zero and one, so comparison with `-1` cannot be true for a valid similarity result.

The sentinel condition introduces the function into the first branch without changing which rows the null branch selects.

The `is_null_level=True` configuration is essential. It preserves Splink's special statistical treatment of that level, including its zero match-weight contribution.

For safe functions and eligible query plans, the optimization can reduce repeated similarity calculations across thresholds.

It is not appropriate for arbitrary user-defined functions or functions that might raise errors on data normally excluded by earlier conditions.

This technique is documented by Splink rather than inferred solely from general SQL optimization principles.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink



### 9.3 Direct Parquet materialization configuration

The DuckDB backend accepts:

```
DuckDBAPI(    connection=...,    materialisation="parquet",    materialisation_dir="...",)
```

For example:

```
import duckdbfrom splink import DuckDBAPIconnection = duckdb.connect(":memory:")db_api = DuckDBAPI(    connection=connection,    materialisation="parquet",    materialisation_dir="splink_work",)
```

Splink can materialize intermediate relational results directly to local Parquet files and access them through DuckDB views.

The important distinction is that this is not simply exporting finished predictions to Parquet.

It changes how Splink stores materialized intermediate relations during execution.

The approach can reduce memory requirements for retained intermediate tables and avoid some durability-related database writes associated with persistent DuckDB tables.

However, it does not eliminate the working memory required by joins, sorting, and Parquet writing.

The materialization directory must be local, and it must remain available while dependent relations are in use.

It is not a transparent durable-object-store abstraction. In particular, the documented `materialisation_dir` is not an S3 URL.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink



### 9.4 Chunking is a resource-management mechanism, not an inherent speedup

Splink 5 supports partitioned prediction, but chunking introduces additional work.

The official performance documentation explicitly cautions that chunking may be slower than unchunked execution when the workload already fits comfortably in memory.

This is because some calculations are repeated across chunks and their outputs subsequently need to be assembled.

Chunking is therefore best understood as providing:

- Smaller peak candidate-generation working sets.
- Incrementally executable prediction partitions.
- More granular progress information.
- Opportunities to distribute independently identified chunks across machines.

The native `predict()` chunking workflow processes partitions and unions their outputs.

Earlier scored chunks must still be retained until the combined result is available. For very large prediction outputs, chunking and Parquet materialization can consequently address different parts of the memory problem.

The first controls the size of the work performed at one time; the second controls how retained results occupy memory and storage.

### 9.5 Precomputed candidate pairs and chunked inference

The model's externally supplied candidate-pair workflow has an important compatibility restriction.

After calling:

```
linker.table_management.register_blocked_pairs_for_predict(    blocked_pairs)
```

the registered candidates can be scored using:

```
predictions = linker.inference.predict()
```

However, this registration is not compatible with `predict_chunk()` or with `predict()` arguments requesting automatic chunking.

The intended alternative is to generate individual candidate chunks through `compute_blocked_pairs_for_predict_chunk()`, register each resulting candidate table, and score it through the ordinary prediction interface.

This permits external orchestration of chunks, but it is not equivalent to activating Splink's automatic chunking over one previously registered candidate table.

The distinction is important for evaluating how far Splink's modular candidate-generation and scoring interfaces can be composed without additional coordination logic.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink+1



### 9.6 Additional DuckDB configuration considerations

The performance documentation also discusses several backend-level considerations:

In-memory connections. These avoid persistent database durability overhead for intermediate workloads, although DuckDB may still spill working data to disk.

Explicit memory limits. In environments where DuckDB cannot accurately determine available memory, a configured `memory_limit` can help avoid exhaustion of system memory. Headroom must remain for Python and allocations outside DuckDB's buffer manager.

Local storage. Storage performance can materially affect Parquet-backed execution and spill behavior.

CPU utilization. Sustained underutilization during major blocking and scoring operations may indicate execution bottlenecks that are not visible from Python-level timing alone.

These are DuckDB execution characteristics. Splink exposes the opportunity to benefit from them but does not guarantee particular speedups for arbitrary configurations.

Primary source

DuckDB performance and function-hoisting guide:\
[https://moj-analytical-services.github.io/splink/topic_guides/performance/optimising_duckdb.html](https://moj-analytical-services.github.io/splink/topic_guides/performance/optimising_duckdb.html?utm_source=chatgpt.com)

## 10. Additional SQL extension, inspection, and lifecycle interfaces

Several smaller interfaces complete the picture of how Splink can be extended or integrated into relational processing workflows.

### 10.1 Backend-defined similarity functions

`DistanceFunctionAtThresholds` allows a custom SQL similarity or distance function to participate in Splink's standard comparison hierarchy.

Its signature is:

```
DistanceFunctionAtThresholds(    col_name,    distance_function_name,    distance_threshold_or_thresholds,    higher_is_more_similar=True,)
```

The `higher_is_more_similar` argument determines threshold direction.

This matters because different comparison functions have opposite interpretations:

- Jaro–Winkler: larger values indicate greater similarity.
- Levenshtein: smaller values indicate greater similarity.

A custom SQL function can therefore be incorporated into ordinary comparison levels without manually constructing every `CASE` branch.

Splink does not automatically create the underlying SQL function. It must already be available through the selected database backend.

The same backend-dependent constraints apply to data types, null handling, and execution cost.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink



### 10.2 SQL-dialect translation in custom blocking rules

`CustomRule` supports an optional `sql_dialect` argument.

When provided, Splink attempts to translate the supplied blocking predicate into the dialect associated with the execution backend.

For example:

```
from splink.blocking_rule_library import CustomRulerule = CustomRule(    "SUBSTR(l.surname, 1, 3) = SUBSTR(r.surname, 1, 3)",    sql_dialect="sqlite",)
```

This can improve portability of custom blocking specifications.

However, successful SQL syntax translation does not imply semantic equivalence of every function, nor does it supply functions unavailable in the destination database.

Consequently, custom SQL can be syntactically portable while still depending on backend-specific behavior.

Source: [https://moj-analytical-services.github.io/splink/api_docs/blocking.html](https://moj-analytical-services.github.io/splink/api_docs/blocking.html?utm_source=chatgpt.com)

### 10.3 Direct relational querying

Two related interfaces support database-side analysis:

```
linker.misc.query_sql(sql)
```

and:

```
splink_dataframe.query_sql(sql)
```

The `SplinkDataFrame` method supports a `{this}` placeholder referencing its underlying relation.

For example:

```
filtered = predictions.query_sql(    """    SELECT unique_id_l, unique_id_r, match_weight    FROM {this}    WHERE match_weight > 8    """)
```

This preserves a relational workflow and avoids converting large prediction tables into Python objects simply to filter or aggregate them.

`linker.misc.query_sql()` provides the more general interface for querying the backend database. Its documented default output type is `splink_df`.

Both methods are useful extension points for SQL operations not explicitly exposed by Splink's higher-level APIs.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink+1



### 10.4 Explicit table cleanup

`SplinkDataFrame` provides:

```
drop_table_from_database_and_remove_from_cache(    force_non_splink_table=False)
```

The method drops the underlying database table and removes its corresponding cache entry.

By default, it refuses to delete tables that were not created by Splink. The `force_non_splink_table` argument can override this protection.

This distinguishes explicit resource deletion from cache invalidation.

Invalidating cached computations affects how results are reused or recomputed; dropping a physical relation affects the underlying database resource itself.

The distinction is particularly important when intermediate results are large, are retained across analytical stages, or share a database environment with user-managed tables.

Source: [https://moj-analytical-services.github.io/splink/api_docs/splink_dataframe.html](https://moj-analytical-services.github.io/splink/api_docs/splink_dataframe.html?utm_source=chatgpt.com)

### 10.5 Internal debug execution mode

In addition to logging, Splink documents an internal debugging mechanism:

```
linker._debug_mode = True
```

The documented effects include executing SQL pipeline stages individually, showing generated SQL, and displaying intermediate tabular results.

This can expose the relational transformations that are ordinarily hidden by Splink's pipelining optimizations.

However, this is a private interface, indicated by its leading underscore. It should not be treated as a stable, supported public API.

The documentation also warns that the mode can dramatically reduce performance.

For routine observability, the documented logging and profiling interfaces are preferable. The private debug mode is more appropriately understood as an implementation-inspection aid whose behavior may change between releases.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://moj-analytical-services.github.io\&sz=32)

Splink



Primary source:\
[https://moj-analytical-services.github.io/splink/dev_guides/debug_modes.html](https://moj-analytical-services.github.io/splink/dev_guides/debug_modes.html?utm_source=chatgpt.com)

## 11. Additional semantic qualifications for the companion reference

### 11.1 Record identifiers and source identity

For multi-dataset linkage, Splink requires record identifiers to be unique within their source datasets, not necessarily globally unique across every participating dataset.

The documented model distinguishes:

`unique_id_column_name` — identifies a record within its source.

`source_dataset_column_name` — identifies the source dataset.

The combination provides the relevant cross-source record identity.

This matters for linkage systems in which several datasets independently use integer primary keys beginning at one. Duplicate numeric IDs across different source datasets do not inherently violate Splink's input identity model.

Source: [https://moj-analytical-services.github.io/splink/api_docs/settings_dict_guide.html](https://moj-analytical-services.github.io/splink/api_docs/settings_dict_guide.html?utm_source=chatgpt.com)

### 11.2 Comparison retention versus visualization requirements

A minimal prediction output is not automatically sufficient for every Splink visualization.

Certain explainability interfaces depend on retained matching columns or intermediate calculations.

Consequently, choosing to omit these columns is not exclusively a storage optimization. It also changes which analyses can be performed directly from the retained result without recomputing or restoring additional evidence.

This is a cross-cutting interaction between execution efficiency, observability, and the availability of source-record information.

### 11.3 Version-specific API stability

The addendum targets the released Splink 5.0.0 public interfaces.

Version-specific examples should use the v5 model in which input data is registered through the backend and then supplied to `Linker` as `SplinkDataFrame` objects.

Some upstream topic and developer guides retain older examples or internal implementation references. Those should not be interpreted as evidence that older constructor signatures remain supported in version 5.

Similarly, private interfaces and implementation optimizations should not be treated as part of Splink's stable public API merely because they are described in developer documentation.

The companion reference's illustrative Python snippets should also retain proper line breaks and executable statement separation. In particular, its compact example should be formatted consistently with the version 5 registration and linker-construction model.

Primary sources

Version 5 release and migration information:\
[https://moj-analytical-services.github.io/splink/blog/2026/09/28/splink-500-released.html](https://moj-analytical-services.github.io/splink/blog/2026/09/28/splink-500-released.html?utm_source=chatgpt.com)

Version 5 API index:\
[https://moj-analytical-services.github.io/splink/api_docs/api_docs_index.html](https://moj-analytical-services.github.io/splink/api_docs/api_docs_index.html?utm_source=chatgpt.com)

Tagged source:\
[https://github.com/moj-analytical-services/splink/releases/tag/v5.0.0](https://github.com/moj-analytical-services/splink/releases/tag/v5.0.0?utm_source=chatgpt.com)

## 12. Architectural implications of the additional functionality

Taken together, these mechanisms extend the architectural options exposed by Splink beyond those apparent from the major APIs alone.

Multivalued entity representations can participate directly in SQL-based resolution. Array-exploding blocking, array comparisons, phonetic-code arrays, and database-side feature generation allow systems to represent alternative identifiers and names without requiring a separate custom candidate-generation engine for every multivalued attribute.

Compound comparison templates provide more expressive evidence models. Joint name comparisons, full-name term-frequency adjustments, hierarchical postcode agreement, and partial email matching can capture relationships between attributes that a collection of independent fuzzy-string comparisons would represent less accurately.

Missingness and invalidity are explicit statistical decisions. The distinction between neutral null evidence, negative disagreement, and invalid source values affects what the model is estimating. Splink exposes mechanisms to manage that distinction rather than treating all nonagreement as equivalent.

Training and evaluation can be controlled at finer granularity. Individual probability constraints, EM convergence settings, structured accuracy tables, and clerical-label threshold semantics allow more precise control over the estimation and evaluation of probabilistic linkage models.

The relational execution architecture exposes substantial optimization opportunities. Precomputed candidates, output-retention settings, Parquet materialization, chunking, and carefully controlled SQL expression reuse can reduce different kinds of computational work. Their advantages depend on how the mechanisms are composed, and some combinations carry explicit API restrictions.

The common theme is that Splink's higher-level abstractions do not entirely conceal its SQL execution and statistical foundations. They expose enough of both to support specialized entity-resolution behavior without requiring developers to reimplement the entire record-linkage pipeline.

These additions complete the consequential gaps identified in the companion reference while preserving its existing coverage of the main functionality.