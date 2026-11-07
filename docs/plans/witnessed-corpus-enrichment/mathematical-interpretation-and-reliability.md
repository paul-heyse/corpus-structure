# Mathematical interpretation and operation reliability

> Current authority,2026-11-06: ADR-0068 selects shared-development qualification; ADR-0067 selects current-only execution.
> Use the SAME120 Grinstead–Snell physical pages191–310 for development, regression, fitting and
> assessment. No new sources, separate calibration population or independent-origin readiness gate
> is required. In-sample fitting is diagnostic; preserve numerical validity, exact source evidence
> and source-only reference judgments. Current test-resolution is complete. Remove replaced
> production contracts and historical decoder paths across ALL remaining WCE, retaining controls
> only on current contracts. The coordinator owns execution status and final-source qualification.


**Implemented selected contracts; current execution reconciliation,2026-11-06.** This document develops WCE08 and WCE09 of the [witnessed corpus enrichment coordinator](../witnessed-corpus-enrichment_2026-11-05.md). The coordinator alone owns execution status, accepted rule dispositions, conditional-investigation decisions and finding closure. This companion specifies the required capability and its evidence; it does not report implementation completion.

The principal input is the integrated [production enrichment target review](../../design_review/reviews/design_review_production-enrichment-improvements_2026-11-05.md), especially F06–F07, §4.4, §8 and §10, at `6487c486075a832e50b59fcec96c88485f30c11a`. The operator accepted RC01–RC06 for planning on 2026-11-05; WCE00 routes the owning rule/ADR changes before dependent implementation. The separate test-audit resolution plan is treated as an available target foundation, with its final checks separately owned. This plan neither reopens its scope nor counts that assumption as a new passing receipt.

The focused foundation assessment uses core principles 3.3, the efficient-architecture companion, code-intelligence profile 1.4 and the repository binding. The current dirty additions to the Lark, spaCy, scikit-learn, pgmpy and Splink guides were read as research inputs and remain outside this companion's edit scope. Their API examples are evidence to reconcile with tagged sources, not new installed dependencies. The original functional review is historical input to the integrated principal, not the execution target.

## 1. Purpose and boundaries

The required improvement is to give a real, bounded source ambiguity an explicit policy over retained choices, then expose exactly what that policy established. A local solve must explain which interpretations are feasible, which remain alternatives and how shared source evidence affects their relative weights. An operation-specific reliability evaluator subsequently asks whether a particular emitted relation, role or attachment agrees with independently authored source judgments. These are different questions and must remain different products.

WCE08 owns the genuine table policy, its deterministic/independent/coupled comparison and its integration through the existing private local-question path. WCE09 owns the new operation-event fitting/evaluation lifecycle and compatible candidate-neighborhood reuse. Neither package supplies scientific truth, entity identity, independent source support or publication permission. A local posterior is `provisional_candidate_relative`; an operation reliability estimate is conditional on a named event, population and evaluation protocol. Complete-record fitting and its existing policy retain their original meaning.

The required implementation includes the usable policy and evaluator contracts, native custody, ordinary read/export surfaces and truthful insufficient-data outcomes. Parameter fitting, a larger inference backend and hierarchical/population inference have separate entry conditions below. Lack of a suitable learning cohort must not prevent building the witnessed-component path or be concealed by fitting the existing twenty pairs from two usages.

## 2. Current foundations and the necessary corrections

The2026-11-05 planning baseline supplied these boundaries and gaps; the current selected realization below supersedes its then-missing coupling/evaluator descriptions:

| Foundation | Current source and retained guarantee | Planned use or correction |
|---|---|---|
| Finite local inference | `semantic/record_interpretation.py:101–270,306–315`: `CandidateSelection`, ordered `Decision` states, `LogPotential`, `HardConstraint`, `CompositeEvent`, `LocalInterpretationRequest`, `InterpretationResult`. | Reuse the existing exact retained-support executor. Add an actual policy producer rather than a generic second inference service. |
| Numerical/failure semantics | The same file, `_interpret`: validates dependency identities and factor shapes, guards total joint support/workspace, accumulates in log space, normalizes over the retained joint, unions overlapping event derivations and returns explicit refusal outcomes. | Keep invalid input, infeasible, numerical failure, limited and cancelled distinct; no partial probabilities after unsuccessful execution. Preserve conservative total-joint admission until a separately selected backend supplies equivalent semantics. |
| Private request/result custody | `methods/local_interpretation.py:19–143` seals retained contributions, dependencies and exact request/result bytes; `semantic/local_interpretation_reports.py:16–91` validates their correspondence. | Both currently encode coupling as disabled: the producer writes `coupling_enabled=False` and the validator rejects a true flag. Version the operation/report binding and migrate these consumers before describing a genuine coupled report as coupled. Merely changing the producer flag would fail current validation. |
| Actual invocation | `methods/m1_readings.py:211–231` calls `local_question_operation` for retained questions. | Extend the applicable policy dispatch at this real route. Keep a truthful `not_run` when a question lacks a supported policy; do not substitute generic equal weights and claim evidence-informed inference. |
| Protected evaluation | `evaluate/operation_assessment.py:32–174` owns operation question, direction, source anchors, source states and independently authored alternatives; `evaluate/structural_assessment.py:18–34` currently limits structural frames to development. | Consume WCE02's versioned operation/group frames and RC06 partitions. Preserve source-first capture and output-first correctness separately. |
| Historical fitter | `evaluate/record_fitting.py:1–187` distinguishes `WholeReadingLabel`, complete scored-event membership, finite/converged fitting and quality; `evaluate/record_policy.py` reads protected partitions. | Reuse protected custody and the established fitted-parameter boundary. Introduce a distinct operation-event algorithm/schema; do not relabel whole-reading correctness as attachment or relation correctness or silently change its released scaling algorithm. |

Paths above are relative to `python/corpus-structure/src/corpus_structure/`. Existing checks such as `tests/semantic/test_local_interpretation.py` and `tests/methods/test_local_interpretation.py` are useful local controls, not evidence that a real policy already improves interpretation. No source, provider, database or product tests were run during this plan authoring.

The foundation assessment favors composition: the solver's mathematical contract is already sufficient for the first small question. The missing responsibility is source-bound policy construction and its honest consumer representation. Evaluation uses its own event meaning and protected shared-development frame at the existing reference store. These changes localize policy, numerical execution and assessment authority while keeping their complete dependencies explicit (FP-02/04/06; CI-02/06/12).

## 3. WCE08: one real table interpretation policy

### 3.1 Supported question, variables and retained support

Choose a recurring retained table ambiguity from WCE02's frozen source opportunities, consumed through the located table/header/unit/note products of WCE06. The policy answers: **which retained header/property, unit, note attachment and value-role interpretation is coherent for these selected cells under this source scope?** Freeze the question and its source judgments before comparing scoring methods. The initial ordinary workload is a bounded local table region with repeated headers or note applicability, not a whole-book joint over every cell.

Use existing decisions with explicit state identities and unresolved options:

| Decision family | Candidate meaning | Multiplicity and failure meaning |
|---|---|---|
| Header/property for a selected cell or coherent column band | Exact retained header occurrence/property reading, including alternative nested bands. | Mutually exclusive readings for one question remain alternatives. A multi-cell policy can share one header decision where its meaning is actually shared. |
| Applicable unit for that cell/band | Exact located unit declaration with declared scope, or an unresolved state. | A truly unstated unit, uninspected region and competing unit readings stay distinct in source products. The policy cannot turn any of these into an observed unit by agreement alone. |
| Note-to-target attachment | A separate Boolean/finite decision for each eligible note-target relation, retaining the exact note and target occurrences. | One note may govern several rows. Do not encode a global exactly-one-target constraint or use one-to-one assignment for this question. |
| Value role | Declared role alternatives such as estimate, uncertainty or sample count, tied to the same exact cell value occurrence. | The same numeric lexeme can have several plausible roles; a selected role does not change the original value or imply scientific validity. |

Candidate selection records inventory/retrieval revisions, selected source/region, exclusions and truncations. Unknown omitted mass remains unknown. A finite support describes the retained model only; exhaustiveness is a separate source premise with evidence. Freeze common support for all three comparison arms so a change in candidate recall cannot masquerade as an improvement from coupling.

### 3.2 Hard masks, soft factors and shared evidence

Prepare `HardConstraint` tables only for impossibilities established by authenticated source and released semantics: a note marker excludes an explicit disjoint region; a located unit declaration is outside the band it demonstrably governs; an assignment references a different selected table; a candidate's declared role/type is incompatible under the bound ontology. Every mask cites the exact premises and policy revision. Geometry that is suggestive, an inferred header reading, a lexical similarity or missing retrieval result cannot become a hard source fact.

Prepare `LogPotential` tables for uncertain compatibility: alignment under an ambiguous spanning header; agreement of value role with a selected property; a unit reading's compatibility with that same property; uncertain marker/geometry support for a note target. Authored initial weights must be finite, named, versioned assumptions with sensitivity comparisons, not described as fitted likelihoods or calibrated truth. A zero-weight feasibility control is useful and explicitly has no ranking evidence.

Each factor lists its observation, candidate-selection, ontology and policy dependencies. Assign each source observation to one evidence contribution, or represent its joint contribution in a single factor over the affected variables. For example, if a header's wording is the only reason both a property and a unit look plausible, do not award its full likelihood independently to the header, unit and role and multiply those votes. A shared header decision plus one joint factor can preserve that dependence. If the dependence cannot yet be specified honestly, omit the duplicated soft evidence and retain uncertainty.

`DependenceScope` names genuine evidence/selection connectivity for diagnostics and invalidation; it does not divide out duplicate likelihoods. Registering a scope cannot repair already double-counted numerical evidence. Retain rejection/counterevidence dependencies as well as positive observations. Inventory membership and relevant negative lookups participate in recomputation; a changed source region or added candidate can change normalization even when the previous winning candidate is unchanged.

### 3.3 Execution, output and actual consumers

Construct a `LocalInterpretationRequest` with ordered decisions, C-order factor axes, complete dependency identities and a `CandidateSelection`. Declare `CompositeEvent` unions for consumed questions, including alternatives with shared assignments; the same assignment contributes once to an event. Use `interpret_local` and retain marginals, event probabilities, coherent alternatives, log partition and diagnostics as one result. A request for fewer displayed marginals or alternatives must not shrink the normalization universe or renormalize the displayed subset.

Compare three named arms on identical retained candidates and masks: feasibility only; independent evidence choices with their declared independence premise; and the genuine coupled policy. Compare against independently authored header/unit/note/role judgments, not against the policy's own best assignment. Report supported distinctions corrected, supported answers preserved, losses, spurious selections and unresolved cases. Increased concentration without a corrected independently supported distinction is not benefit. If coupling does not improve the question, retain the simpler production choice and preserve the coupled investigation and its conclusion; do not keep complexity solely because the solver can express it.

Prepare/solve outside the publication transaction. Scope factor construction to the selected table region and reuse retained annotations and normalized premises instead of rerunning parsing or hydrating unrelated source banks. The current defaults (`max_states=65_536`, `block_states=1_024`, numerical workspace 64 MiB, ten seconds, five displayed alternatives) are implementation defaults to assess against the selected ordinary question, not capacity promises. Record actual chosen settings. Current time/cancellation polling is cooperative and its workspace guard covers the numerical operation rather than the whole process; use the existing execution admission/lifetime owner for broader supervision, not a new solver-specific process framework.

The new versioned operation must distinguish absent policy/`not_run`, executed independent policy and executed coupled policy without rewriting old `local-interpretation-1` reports. WCE01 supplies released shape/native binding support; WCE08 migrates producer, report validator, contribution report lowering, actual M1 invocation, ordinary Reader/query, CLI/MCP rendering and detached export for this capability together. Consumers show model/support limits beside probabilities and preserve all exact source pins and producing-runtime provenance. No score crosses into a component or whole-record eligibility assertion without that assertion's separate policy and independent evidence. Authentic raw reports remain evidence. Replaced unconditional coupling-disabled semantics and obsolete production decoders are retired; current consumers use the versioned current contract.

### 3.4 WCE08 prerequisites and completion

WCE00 supplies routed RC01/RC06 authority as applicable; WCE01 supplies the new operation/binding/native/read contract slice; WCE02 supplies frozen operation questions, source opportunities, rubrics and protected judgments; WCE06 supplies real located header/unit/note/value alternatives with scope. WCE08 can define small policy tables before all WCE06 producers finish, but actual policy acceptance requires those real products and consumers. WCE09 is not a prerequisite: the initial policy has declared weights and sensitivity, with no claim of fitted reliability.

The early WCE02 source/question/rubric slice permits producer construction before new outputs exist. Output-first frames and event labels follow their actual producer runs. Dependencies here never require all WCE02 references to be complete before producing outputs, and never assume those later labels already exist.

Completion requires the authentic recurring question, all three arms, report/native/read migration and independent semantic/numerical controls below. A missing real ambiguity or missing independent judgment is a named missing prerequisite, not an invitation to invent a toy as production efficacy evidence. Small analytic cases remain appropriate to verify the executor/policy interface.

## 4. WCE09: operation-event evaluation and candidate reuse

### 4.1 Freeze what is being predicted

Define a versioned event for each selected learned operation: for example, whether this emitted note-to-row attachment, with these endpoints, direction and applicability scope, is supported under its frozen rubric. Do not collapse span correctness, role correctness, endpoint identity and scope into an undocumented binary. A deliberately conjunctive event may be fitted only when its rubric names every conjunct; retain facet judgments to diagnose errors. Distinguish candidate-present interpretation correctness from source-first capture. Missing output remains a capture failure/unknown at source-opportunity grain and does not disappear from the denominator or become an invented low-score emitted event.

Reuse WCE02's exact shared-development source/frame contract and protected evaluator custody.
The selected event is `defined_by_correctness`, version `defined-by-exact-endpoints-scope-1`:
an emitted `relation.defined_by` with independently judged exact head/tail anchor scopes.
Location, role, attachment and scope judgments remain inspectable facets. Freeze source membership,
event IDs, operation/schema/rubric and feature order. A contextual proposal with an own-component
`defined-by` edge is a different contract; it cannot be relabelled as this event to manufacture a fit.

The SAME120 pages serve fitting and assessment. There is no separate-origin, held-out-group or
calibration-population readiness gate. Preserve exposure and report `in_sample_development`.
Production receives finite parameter values with exact algorithm/event/frame provenance through
its parameter-only read boundary; protected judgments remain evaluator-owned. A semantic event
or rubric change creates a new version. A runtime-only budget or deployment repair preserves the
semantic identity when outputs and parsing are unchanged.

### 4.2 Selected first learned baseline

For the new operation-event algorithm, select scikit-learn **1.9.1**, already pinned in `python/corpus-structure/pyproject.toml`, and compose `Pipeline([("scale", StandardScaler()), ("event", LogisticRegression(...))])` with `predict_proba`. Configure the regularization, solver, tolerance, seed where applicable and iteration limit explicitly in the immutable algorithm instance. Fit the scaler on the declared shared development observations. A `DummyClassifier(strategy="prior")` uses the same labeled frame and scoring as the class-prior control. The existing whole-reading implementation remains its historical baseline; do not silently replace its released scaling or labels with this new pipeline.

The implemented unit-weight pipeline explicitly fixes regularization, solver, tolerance and
iteration budget. Retain convergence warnings, iterations, finite-input checks, all exact event
predictions, prior/fitted Brier and log loss, and failures. No class duplication, ambiguous-to-negative
conversion or group-count gate is permitted. Both independently judged binary classes are needed
for this logistic operation; an unavailable result names that specific prerequisite.
`cross_validate`, group splitters, `FrozenEstimator`, metadata routing and calibration remain library
capabilities for a later concrete question, not obligations for this development execution.

The evaluator reconstructs its frame from the exact protected operation grade and final cut,
checks independently authored C endpoint alternatives, and records the result natively. The fitter
can read its protected frame; ordinary consumers read only finite typed parameters and provenance.
Controlled positive/negative fitting verifies that mechanism. Actual corpus fitting additionally
requires emitted compatible events and exact protected operation labels. It is not established by
component grades, software controls, improved loss or successful provider execution.

Sources for the selected pipeline/prior/scoring mechanisms and later optional capabilities remain
[the sklearn guide](../../libraries/scientific_compute/Scikit-learn.md) and its tagged primary
references: [Pipeline](https://github.com/scikit-learn/scikit-learn/blob/1.9.1/sklearn/pipeline.py), [logistic regression](https://github.com/scikit-learn/scikit-learn/blob/1.9.1/sklearn/linear_model/_logistic.py), [class-prior control](https://github.com/scikit-learn/scikit-learn/blob/1.9.1/sklearn/dummy.py), and [tagged validation API](https://github.com/scikit-learn/scikit-learn/blob/1.9.1/sklearn/model_selection/_validation.py). No held-out or calibrated-truth claim follows from in-sample scores.

### 4.3 Shared candidate neighborhoods

Where at least two actual consumers need the same candidate neighborhood—such as a fixed-candidate operation challenger and reference-selection diagnostics—construct it once using `KNeighborsTransformer` or `RadiusNeighborsTransformer`. Retain a sparse distance or connectivity graph with a complete validity contract: exact inventory membership/order, source split, encoder/checkpoint and normalization, feature/metric revision and fitted-state provenance, neighbor/radius policy, construction revision, direction, self-edge/duplicate policy, query-to-training index mapping and limits. Local graph indices never become occurrence identities. Changed inventory, fit or metric invalidates affected reuse. A held-out query can search a frozen training inventory under the declared protocol; an all-source/transductive graph requires its own explicit assessment question and cannot quietly enter an inductive held-out result.

Preserve explicit zero-distance neighbors in CSR storage, including distinct occurrences with identical vectors. Distinguish absent sparse entries from observed zero distance; preserve a training diagonal only where the consumer contract requires it, avoid duplicate column indices and satisfy each consumer's retained-neighbor requirement. Distance graphs cannot be relabeled as affinities or connectivity without the declared transformation. Keep source-valid scope/type exclusions separate from heuristic neighbor truncation; retrieving no neighbor does not establish absence of a relation.

The graph is candidate structure, not admitted relationships, independence evidence or identity truth. A repeated consumer with different scope, metric, required neighborhood width or split cannot share it merely because the encoder is the same. Prepare no persistent graph/cache when one cheap consumer needs it once; the required implementation then retains the graph contract and a reasoned direct route. When sharing is selected, demonstrate actual producer and consuming paths together rather than persisting an unused artifact. Keep CPU/model work and intermediate graph lifetime outside database publication, with existing owned-result lifetime and export custody. This removes repeated neighborhood construction where reuse is valid without imposing one lifecycle per relation kind (FP-07; heuristic H5/H12/H14).

Mechanism evidence: [scikit-learn addendum §1.2](../../libraries/scientific_compute/Scikit-learn.md#12-nearest-neighbor-graphs-as-separately-computed-reusable-representations), [tagged graph contract](https://github.com/scikit-learn/scikit-learn/blob/1.9.1/doc/modules/neighbors.rst), [tagged transformers](https://github.com/scikit-learn/scikit-learn/blob/1.9.1/sklearn/neighbors/_graph.py). Approximate-neighbor machinery is not selected by this plan merely because the contract could accommodate it.

### 4.4 WCE09 prerequisites and completion

WCE00/RC06 and WCE02 supply the operation-specific frame, protected partition/read and independent source/reference contracts; WCE01 supplies typed/native result custody and read/export support. WCE03/WCE04/WCE05/WCE06 supply the actual candidate/operation features needed by the particular event. WCE09 should start with one well-defined event whose products are ready rather than wait for every operation family. A source-only frame and an agreed interface alone do not establish a fitting-ready cohort.

Deliver the versioned event evaluator, class-prior and in-sample pipeline comparison, exact protected frame/parameter bindings, truthful insufficient-support products and ordinary evaluator CLI/read/export consumption within WCE09. When suitable protected data exists, run the declared comparison and report its actual outcome; otherwise leave efficacy and the fitting prerequisite explicit at the coordinator. Graph reuse requires compatible real consumers as described above; retaining a direct route with that assessed outcome does not warrant a cache completion claim. WCE11 integrates cross-capability journeys; it does not postpone the consumers needed to use this evaluator correctly.

## 5. Conditional investigations and their settling evidence

These are bounded decision questions under the coordinator's conditional IDs. They do not authorize dependency installation or imply that the current observations support fitting. Exact optional versions are research baselines; select/pin the actual dependency only when its entry condition is met, reconcile the lock diff and run affected checks then.

| Investigation | Entry question and selected candidate mechanism | Evidence and possible outcomes |
|---|---|---|
| I02: policy/parameter learning | After WCE08 defines real variables and observation ownership, does independently observed discrete data support learning better parameters than the declared policy? pgmpy **1.1.2** `DiscreteBayesianEstimator` with explicit priors; `DiscreteEM(m_step_estimator=...)` only for a justified latent model; `MirrorDescentEstimator(model=..., data=...).estimate(marginals=...)` for selected empirical marginals. | Predeclare states, priors, missingness/selection and the actual shared-development event question. A held-out/group protocol is required only for a separately selected generalization claim. `DiscreteEM` 1.1.2 drops partially missing rows and promotes all-missing columns to latent status; retain who was excluded and why. Its weighted M-step requirement, latent cardinalities, initialization, seed, tolerance and iteration budget are part of the instance. Mirror descent estimates empirical marginals selected from its data; do not pass arbitrary external marginal arrays and claim support. Keep declared factors if the data cannot settle the question or the challenger adds no supported value. |
| I02: independence challenge | A particular few-variable factorization risks double counting. Use `Independencies.closure/entails` or a tiny explicit `JointProbabilityDistribution.check_independence/is_imap`. | Independent analytical source/model expectations can falsify a declared premise. Logical closure or agreement with an authored joint is not empirical truth, causal identification or a general policy validator. Bound the question; closure can become impractical beyond a few variables. A failed premise changes the affected factorization, not every solver. |
| I02: backend substitution | A useful real policy exceeds the existing conservative enumeration guard while a tractable elimination order/intermediate representation exists. Candidate: `DiscreteMarkovNetwork` + `DiscreteFactor` + `VariableElimination.query`; `BeliefPropagation` may amortize repeated queries. | Compare full interface semantics on identical supports: normalizers, marginals, event unions, coherent alternatives, dependency provenance, infeasible/numerical/cancelled/limited outcomes and actual ordinary question fit. Converting log factors to ordinary products risks underflow; demonstrate a stable route. Keep current solver if equivalence or useful fit fails. No backend activation based solely on a larger synthetic joint. |
| I02: assignment-only relaxation | A separate named consumer needs one best assignment rather than posterior/event probabilities. Candidate: `Mplp` and its integrality-gap diagnostics. | Declare its narrower output, relaxation/termination meaning and independent small exact assignment control. An assignment or reported gap cannot substitute for normalized marginals, event unions or the full WCE08 backend interface. Without that consumer, no MPLP work. |
| I03: reliability hierarchy | Independent operation labels span meaningful source/layout groups and a new-group reliability question remains after the pooled WCE09 baseline. Candidate: Pyro **1.9.2** hierarchical logits, `sample`, `plate`, `NUTS`, `MCMC`, `Predictive`. | Freeze operation event, shared-evidence groups and observation model. Compare pooled, held-out group and genuinely new-group posterior predictions, prior sensitivity, chain/convergence diagnostics and failures. Capture/discovery remains a separate process; emitted-output correctness labels cannot answer it. Twenty pairs from two usages do not establish hierarchy efficacy. Keep pooled/insufficient-data outcome if grouping/model identification or fit fails. |
| I03: clustered associations or population inference | A declared question needs population-averaged error associations or a population mean with prediction assistance. Candidates: statsmodels **0.15.0** `GEE` with Binomial and specified groups/covariance; ppi-python **0.2.3** (`ppi_py`) `ppi_mean_ci`. | GEE needs enough independent clusters and justified dependence/model assumptions; it does not estimate the same group-specific hierarchy as Pyro. PPI needs a frozen estimand, target population, labeled probability sample and compatible predictions on the declared unlabeled population; weights alone cannot supply arbitrary survey/cluster covariance. Retain the existing finite-population SRS route for its actual question. Invalid sampling or weak cluster support leaves the question unestablished. |
| I05: learned span/metric/semisupervised challengers | A named error/reference-selection question remains after fixed-candidate controls, with suitable independently judged labels or a useful unlabeled selection population. Candidates include spaCy preset-span classification, NCA, declared feature interactions/mutual information, density summaries, `LabelPropagation`/`LabelSpreading` or `SelfTrainingClassifier`. | WCE03 owns span discovery/classification and exact checkpoint qualification; WCE09 owns affected grouped evaluation and graph reuse. NCA fits only on training groups and can incur quadratic pairwise state; semi-supervised predictions never become gold. Declare shared-development/transductive semantics; require unseen-group assessment only for a separately selected new-source claim. Graphical Lasso requires a specific Gaussian conditional-dependence question; a sparse precision graph is neither source truth nor causality. Reject, retain simpler method or schedule a justified challenger from the result. |

I04's interacting dossier constraints/MILP question belongs to the dossier companion; this document does not add that machinery. Splink's selected identity pilot is developed in the [identity companion](identity-pilot-and-candidate-reuse.md), not hidden inside operation reliability.

Research evidence: [pgmpy addendum §§1,4,7,8](../../libraries/scientific_compute/pgmpy.md#pgmpy-112--advanced-capabilities-addendum), [tagged DiscreteEM](https://github.com/pgmpy/pgmpy/blob/v1.1.2/pgmpy/parameter_estimator/discrete_em.py), [tagged discrete Bayesian estimation](https://github.com/pgmpy/pgmpy/blob/v1.1.2/pgmpy/parameter_estimator/discrete_bayesian.py), [tagged mirror descent](https://github.com/pgmpy/pgmpy/blob/v1.1.2/pgmpy/estimators/MirrorDescentEstimator.py), [tagged exact inference](https://github.com/pgmpy/pgmpy/blob/v1.1.2/pgmpy/inference/ExactInference.py), [Pyro guide](../../libraries/scientific_compute/pyro-ppl.md), [tagged partial-pooling example](https://github.com/pyro-ppl/pyro/blob/1.9.2/examples/baseball.py), [GEE API](https://www.statsmodels.org/stable/generated/statsmodels.genmod.generalized_estimating_equations.GEE.html), [PPI tagged API](https://github.com/aangelopoulos/ppi_py/blob/v0.2.3/ppi_py/ppi.py), [sklearn addendum §§1,3,5,7](../../libraries/scientific_compute/Scikit-learn.md#scikit-learn-191--advanced-capabilities-addendum). Context7's pgmpy result referenced development documentation; the 1.1.2 tagged missing-data behavior takes precedence.

## 6. Verification, migration and handoff obligations

Plan-authoring validation is separate from future implementation evidence. The authoring outcome is static reconciliation of review obligations, current contracts, source/read consumers, package dependencies and conditional triggers. Product, provider and database checks are **not_run** for authoring. The coordinator owns documentation publication checks and final maintenance; a link check cannot establish policy or statistical correctness.

During implementation, run focused tests at coherent capability endpoints. Relevant existing routes include `uv run pytest python/corpus-structure/tests/semantic/test_local_interpretation.py python/corpus-structure/tests/methods/test_local_interpretation.py` from the root; extend the selected cases for the actual changed semantics rather than execute a broad qualification campaign after each slice. Add/run the new operation-event/protected-read and native consumer controls when that capability is integrated. Exact file selection follows the final implementation; commands in this paragraph are planned, not execution receipts.

Required discriminating evidence includes:

1. A small analytically enumerated policy with literal independent weights/masks and expected marginals/events; overlapping event derivations count once, and displaying fewer alternatives leaves their original full-joint probabilities unchanged. Include infeasible support, unknown omitted mass, large common log offsets, malformed factor axes/dependencies and limits/cancellation. Expected values must not be generated by `interpret_local` or the policy builder being tested.
2. A shared-header case where naive repeated likelihood changes the answer; an independent reference distinguishes valid joint evidence from duplicate votes. Include uncertain unit agreement that must remain soft and a single note correctly governing multiple rows.
3. A real recurring table ambiguity under fixed source/support with all three arms and the source-author judgment ledger. A deterministic known answer can validate arithmetic but cannot establish empirical benefit on that real question.
4. Exact report/native custody and ordinary Reader/CLI/MCP/detached-export controls for coupled, independent, unrun, limited and failed cases. Altered dependencies/source selection, stale factor policy and forged probability standing must refuse. No local result can bypass separately evaluated component/whole-record eligibility.
5. Operation-event fold independence and protected split access, including an adversarial shared-source/revision grouping case, training-only preprocessing, fit versus score weights, failed folds, inadequate classes/groups and separately held calibration. Use independent literal partition membership and malformed native requests where relevant; production split code cannot produce its own expected partition.
6. If graph reuse is selected, identical-vector distinct occurrences with explicit zero edges, absent entries, query/training remapping, self/duplicate policies, metric/inventory/split invalidation and incompatible consumer refusal. Confirm actual consumers use the prepared graph while preserving the independent reference population.

Retain original raw results and failed/interrupted attempts. Optional investigations record their question, entry evidence, selected instance and decision outcome in the existing evidence system when executed; do not create proof artifacts merely to demonstrate planning diligence. WCE12 owns the required combined functional/provider/nonfunctional union and final-source qualification, after all required functional scope. WCE08/WCE09 supply their scoped receipts and unresolved prerequisites. They cannot close broader F06/F07 or claim learning benefit solely from unit checks, software availability or finite fitted coefficients.

## Current selected realization — 2026-11-06

The [completion audit](../witnessed-corpus-enrichment_2026-11-05.md#completion-audit) retains the matched band experiment below. Feasibility
and independent requests use uniform unary potentials, while the coupled arm adds a symmetric
same-state preference. Closing WCE08 requires the accepted comparison over source-conditioned
alternatives and its evidence and sensitivity controls. The WCE09 fit mechanism retains scoped
completion, with actual fitting conditional on genuine exact events and protected grades.

**Implemented; final qualification owned by the coordinator.** `shared-table-band-2` uses one
binary applicability decision per retained relation edge, permitting multiple or no applicable
targets. One shared band factor expresses declared coherence; it does not create source support.
Exact three-arm GS120 runs162/170/180 preserve the same8210 contributions and84 candidate cohorts.
Each executes41 requests, retains3 oversized and40 inapplicable `not_run` cohorts; coupled uses
40 joint policies and one independent request. Symmetric declared weights leave marginals near
0.5, so no semantic improvement or calibration is claimed. Python/native invariants reject invalid
normalization, marginal populations, algorithm parameters and failed-result probabilities.

The event fitter is `evaluate/operation_fitting.py` with native `operation_event_fitting.sql`.
Current corpus availability and the exact missing prerequisite are retained under
[operation-fit availability](../../design_review/evidence/2026-11-06_wce-gs120/assessment/operation-fit-availability/).
The existing exact E5 route reuses vectors under its current identity contract. A second compatible
consumer of a sklearn sparse neighborhood was not established, so no additional shared graph/cache
is introduced. Conditional pgmpy learning/backend, Pyro/GEE/PPI and learned-span/metric challengers
remain inactive with the concrete triggers below, rather than imposing a new qualification gate.

**Tested, 2026-11-07.** The Table 5.2 marginal-role comparison preserves the same 358
contributions across feasibility, independent weighting, coupling and four sensitivity
runs. All nine source-supported roles are available, with five contrary layout readings.
Both weighted modes selected the supported roles at all tested scales. Coupling changes
the candidate-relative probabilities, with the same top selections. The
[table receipts](../../design_review/evidence/2026-11-06_wce-completion-repair/table/README.md)
preserve the executed factor scopes and bounded native replay claim.
