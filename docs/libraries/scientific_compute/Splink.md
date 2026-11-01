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