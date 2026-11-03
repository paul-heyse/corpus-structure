# M1 target design and functional opportunities

**Proposed recommendations · 2026-11-03.** Functional, capability-led review under
`functional-extension-review`; no diagnostic audit prerequisite or diagnostic acceptance claim.
Original source baseline: `b8e1a020`, clean at initial inspection. Supplemental reassessment
(2026-11-03): `a99e15ab` plus the operator's uncommitted GLiNER reference, Git blob
`3daefdd5af8a3118f4767d9a558da4bc712cbacd`. Both its original reference and supplemental §§1–8
were considered together. The operator-owned reference is not edited or staged by this revision. The operator selected statistics first,
engineering/other transfer scenarios, five core families, downstream CPU-first execution without
general LLM extraction, and broader improvements staged separately. This review owns opportunity
reasoning and alternatives. The [M1 design](../target-pipeline-design/first-production-milestone.md)
and its supporting pages own the integrated proposed behavior. Neither changes accepted design,
active-plan scope, deployed databases, dependencies or runtime defaults.

## Conclusion and current capability

Recommend the five-family milestone with shared preparation, native GLiNER candidate production,
a small domain-owned interpretation boundary and existing custody/publication/consumer owners.
The strongest improvements are field-addressable evidence, loss-aware context retrieval, explicit
candidate-loss accounting, numerically stable whole-record decisions and an operator journey that
explains both accepted output and omissions. Elaborate inference and global linkage should earn
promotion from measured residual problems rather than become mandatory foundations.

The existing source is materially stronger than a greenfield extractor:

| Inspected source/owner | Existing capability and remaining M1 boundary |
| --- | --- |
| [sentences.py](../../python/corpus-structure/src/corpus_structure/ingest/sentences.py), `SentenceConfig`, `prepare_layout`, `split` | Exact reconstruction, formula/reference atoms, resident spaCy batching and pinned models. Current profile excludes lemmatizer and returns sentence boundaries rather than the proposed reusable annotations. |
| [proposals.py](../../python/corpus-structure/src/corpus_structure/semantic/proposals.py), `NativeFrameSource`, `NativeProposalFrame` | Qualified source/product/projection coordinates and direct-ancestor context. Neighbor, table-note and arbitrary referenced sources require an explicit extension. |
| [observations.yaml](../../python/corpus-structure/src/corpus_structure/model/semantic/observations.yaml), [bind_result](../../python/corpus-structure/src/corpus_structure/semantic/observations.py) | Producer-bound immutable reports, linked inputs, coverage and measurements; current single-location fields do not establish M1 field-to-multiple-anchor semantics. |
| [publication.py](../../python/corpus-structure/src/corpus_structure/semantic/publication.py), [consolidation.py](../../python/corpus-structure/src/corpus_structure/semantic/consolidation.py) | Multiple occurrence evidence/role rows and source-occurrence versus fact separation. Extend this spine rather than build family stores. |
| [domain_operations.py](../../python/corpus-structure/src/corpus_structure/semantic/domain_operations.py), `consolidate_cut`; [inference.py](../../python/corpus-structure/src/corpus_structure/semantic/inference.py), `derive` | Policy-controlled publication and finite qualified rule closure. Candidate-level probabilistic interpretation is a separate new operation. |
| [source runner](../../python/corpus-structure/src/corpus_structure/orchestrate/semantic.py), [statistics policy](../../domains/statistics/policies.yaml) | Existing task/cut lifecycle and agent extraction route. A CPU-only policy and coordinated admission need implementation; resource declarations do not establish a parallel CPU scheduler. |
| [analytics.py](../../python/corpus-structure/src/corpus_structure/semantic/analytics.py), `CapturedPacket`, `AnalysisScope` | Owned Arrow/DuckDB lifetime and execution scopes; useful foundations for candidate relations and component extraction. |
| [query.py](../../python/corpus-structure/src/corpus_structure/semantic/query.py), [evaluation](../../python/corpus-structure/src/corpus_structure/evaluate/semantic.py) | Existing semantic queries and protected reference evaluation; current `agent_claims` report family does not establish five-family evaluation or record evidence export. |

[STATUS](../../STATUS.md) and the [UM coordinator](../plans/unified-domain-model_2026-11-01.md)
retain implementation and qualification authority. The inspected checkpoint has native99 source
readiness with knowledge/reference/evaluator acceptance open. This review performed no live read
of that database and no provider inference; those checkpoint receipts retain their original dates.
D1–D8 and accepted ADRs, especially ADR-0024/0026/0027/0035/0040/0047, remain architectural authority.

## Recommended M1 improvements

<a id="O01"></a>
### O01 · Shared linguistic and loss-aware context products

**Recommend for M1.** The operator and all five assemblers gain one reusable, aligned view rather
than repeated tokenization and incompatible offset reconstruction. Extend the existing sentence
path into explicit sentence-only and richer linguistic profiles. Use spaCy `Language.pipe`,
`Matcher`/`PhraseMatcher`, `DependencyMatcher` and overlapping `Doc.spans`/`SpanRuler` candidates.
Persist only required annotation columns and source references; a `Doc` need not become a new
canonical artifact. Formula/reference atom roles survive linguistic labels.

Extend context to neighbors, declarations, captions, header paths and notes, with typed retrieval
reasons and source-piece interval maps. The alternatives are per-extractor contexts or whole-section
input: both increase repeated work or obscure which evidence actually affected a decision. Reuse
small coherent contexts and widen only for missing roles. A failed retrieval is visible and can be
an invalidation dependency. Demonstration: an interval recovers its estimand/population from a
preceding sentence while a formula and synthetic separator remain separately addressed.

Sources: [spaCy §§2–4, 9](../libraries/parsing/spacy.md),
[DependencyMatcher](https://spacy.io/api/dependencymatcher),
[SpanRuler](https://spacy.io/api/spanruler). Syntax supplies candidates, not guaranteed meaning.

<a id="O02"></a>
### O02 · Governed GLiNER packs and native structured candidates

**Recommend for M1.** Use one versioned adapter/schema family rather than one model pipeline per
record family. `AutoExtractor.from_pretrained` selects boundary architecture. Native
`structure(..., mode="natural", anchor=...)` proposes repeated grouped records, with supported
field cardinality and within-group same-field exclusivity; combined
`extract` shares compatible work, and `AttributeGroup` supplies mention-specific role observations.
Use the seven existing packs with domain-specific descriptions, boundary conventions and examples.
Changing descriptions, prompts or development-only examples changes effective model input and
therefore the reuse key. The native shared proposal pool makes schema competition material to
candidate recall. A cheap routing pass cannot promise reuse of its encoding under a different
focused schema.

Compare native grouped output with deterministic span assembly. A grouped record can associate
mean, standard deviation and sample size; it cannot establish that every required role is stated.
Attributes are scored after mentions survive selection, so missed mentions cannot be diagnosed as
attribute failures. Extract qualification cues and resolve their attachment separately.

`Classifier.score`/`decode` and `JointIE.score`/returned lattices support bounded local constraint
experiments. Set explicit infeasibility handling; default Classifier relaxation cannot authorize
acceptance. JointIE gives typed local edges, not cross-window identity or faithful whole records.
Use constraints only where relation scope warrants them; unique employment-style assumptions
cannot be imported into arbitrary scientific relations.

Sources: [GLiNER §§2–7](../libraries/parsing/gliner2.md), tagged v2.1.0
[combined](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/tutorial/4-combined.md),
[grouped records](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/tutorial/3-json_extraction.md),
[attributes](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/tutorial/13-span_attributes.md),
[classification](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/tutorial/14-constrained_classification.md),
[joint extraction](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/tutorial/15-joint_ie.md).
Supplemental tagged-source inspection resolves the earlier cardinality/ambiguity API uncertainty.
Use explicit record mode/anchor and native assignment before writing another within-group matcher.
Prefer `optional_one` for extracted scalars so model absence can survive even when the domain
requires that field for final acceptance. `required_one` can force a low-score candidate past the
field threshold; `one_or_more` can still return empty. Exclusive scalar assignment is joint within
one record group's same field; exclusive lists choose the strongest instance. Shared conditions,
headers and units must remain reusable where meaning requires it. Native `ABSENT` does not mean
source-unstated, and training `occurrence_policy` does not resolve runtime identities.

Latent and anchorless formation are useful pack-specific challengers for unstable/missed anchors,
not mandatory replacements. Their learned seeds/slots still depend on field candidates; fixed
instance-query capacity and slot order cannot define durable source identity. Evaluate complete
records against natural grouping and deterministic assembly. Native enum fields can return record
anchor offsets or `(0,0)` for schema-prefix choices: retain classified value and association, and
obtain literal cue evidence independently. Never relabel those offsets as extraction evidence.

Use strict `Schema.from_dict` admission for registry input, not permissive builder kwargs. Round-trip
the supported declarative subset; callable validators need a separate versioned binding under the
same owner. No local API, inference or model-quality qualification is claimed.
Sources: tagged [schema/serialization](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/inference/schema.py),
[record assignment](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/models/boundary/records.py),
[formatter](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/models/boundary/engine.py),
[supplemental integration](../target-pipeline-design/gliner-deployment.md#supplemental-capability-integration).

<a id="O03"></a>
### O03 · Field-addressable evidence and complete-record interpretation

**Recommend for M1; foundation for O02/O04/O07.** Consumers should inspect the term, assertion,
argument, unit, header and condition evidence independently. Define named role-labelled anchor
sets in the released model and lower them through existing occurrence evidence/role relations.
Retain source precision and original/normalized/derived status per field. Do not confuse all
context consulted with evidence establishing a field.

Use LinkML declarations, existing prepared Pydantic boundaries and domain operation invariants
instead of separate family schemas with divergent validators. Existing many-to-many evidence is
useful but does not already enforce the full field-to-anchor contract. Observation, publication,
query, export and evaluator changes must arrive coherently under a versioned release. The
alternative, opaque JSON records with one passage citation, cannot locate table-note inheritance
or expose which qualifier is unresolved.

Sources: [LinkML §§1–2](../libraries/data_model/linkml.md),
[Pydantic §§1–2](../libraries/data_model/pydantic.md), current source table above.
Delivery is demonstrated by the same table record resolving its cell, headers and note through
query and export, with no re-recognition and no flattening into fictitious continuous text.

<a id="O04"></a>
### O04 · Stable bounded inference with honest probability semantics

**Recommend NumPy/SciPy enumeration baseline for M1; pgmpy conditional.** Independent field
selection loses interactions such as pressure-unit/antecedent compatibility. Yet a universal
probabilistic runtime adds model conversion, lifecycle and numerical obligations before those
gains are established. Retain small deterministic joins and evaluated fitted baselines, adding
coupling to the three specified templates where held-out full-record comparisons justify it.

Use assignment-relative feasibility and SciPy `special.logsumexp` for partition and whole-event
sums. An all-infeasible component cannot be normalized. Do not multiply marginal field scores,
renormalize only displayed alternatives, or label missing-candidate probability as known unresolved
mass. Hard dimensional constraints depend on selected unit meanings, not the first OCR winner.
Shared model heads, windows and recognition origins require grouped evidence treatment.

pgmpy `DiscreteFactor` and a discrete Markov model are promising for repeated factorized workloads;
`VariableElimination`/junction-tree inference are alternatives requiring supported model shape,
state-order/normalization and intermediate-size qualification. Constraint optimization alone
(Z3, SciPy `milp`, CVXPY) does not provide posterior marginals. The M1 baseline must remain runnable
without any of those optional mechanisms. [Numerical design](../target-pipeline-design/mathematics.md#m1-numerical-realization)
retains the chosen calculations and promotion conditions.

Sources: [SciPy §§3, 8, 12.1](../libraries/scientific_compute/scipy.md),
[pgmpy §§5, 10](../libraries/scientific_compute/pgmpy.md),
[SciPy logsumexp](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.logsumexp.html).
No exactness, accuracy or speed claim extends beyond the specified retained-candidate model.

<a id="O05"></a>
### O05 · Candidate-loss diagnostics and targeted recovery

**Recommend for M1.** The operator needs to distinguish missing intake, missed route, absent
proposal, overlap suppression, wrong grouping, interpretation rejection and publication loss.
Combine routing, actual coverage, interpretation and gap reports through their existing owners;
these are distinct meanings, not separate new services. Independently sample source regions with
no output so agreement among extractors cannot hide shared omissions.

Use native long/batch APIs only under their actual window semantics. Preserve window observations
before highest-score duplicate merging; nested spans and sparse boundary budgets matter. JointIE
long extraction creates no cross-chunk edges. Repair schema descriptions, overlap, candidate
budgets and context before adding models. Lower-level explicit-span scoring is a conditional
bridge with source-confirmed API but still requiring executed token/query/mask and capacity
qualification. Shared-pool injection can overflow and raise; it does not bypass every budget.
Learned no-match suppression and Poisson count-guided retention apply to particular entity/
grouped candidate paths, not a record-completeness certificate. Keep adaptive retention off in the
initial checkpoint profile and compare it only on supported tasks with dense-span losses. Retain
raw signals where exposed without inventing a general public diagnostics API or treating related
heads as independent evidence.

Sources: [GLiNER §§2.3, 5, 6.3](../libraries/parsing/gliner2.md),
[tagged long-context tutorial](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/tutorial/12-long_context.md).
Benefit is additional correct complete records at controlled false positives, not a larger raw
candidate count. Diagnostic completeness is limited by what the library actually exposes.

<a id="O06"></a>
### O06 · Shared CPU admission and relational/columnar preparation

**Recommend for M1.** Extend existing task, capture and analytical scopes. Use one resident model
worker initially, compatible batching, bounded detached contexts and coordinated aggregate thread/
memory admission across spaCy, Torch/BLAS and DuckDB. `max_concurrency` declarations alone do not
establish such scheduling in the current runner. Existing task fencing, cancellation and scoped resource ownership can be reused; coordinated CPU
admission and worker supervision need implementation. Avoid a pool per semantic stage.

Use DuckDB for typed set joins and coverage aggregation; extract only bounded connected components
for NumPy/SciPy. Reuse `CapturedPacket`/`AnalysisScope`, Arrow batch streams and explicit lazy-result
ownership. A DuckDB memory limit is not a whole-process RSS limit; Arrow row batches/readahead do
not bound bytes. Source addresses, state tags and exact numeric representations survive transport.
Finish/abort result objects before reuse and keep buffers alive for consumers.

Alternatives are whole-corpus Python hydration or adding an analytics service. The selected route
keeps optimizer visibility and reuses current machinery; actual throughput and combined working
set remain unmeasured. Sources: [DuckDB §§3–5](../libraries/analytical_infrastructure/duckdb_2.md),
[Arrow §§2, 4–5, 8](../libraries/analytical_infrastructure/pyarrow.md),
[Arrow Scanner](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Scanner.html),
[DuckDB resource settings](https://duckdb.org/docs/current/configuration/pragmas.html).

<a id="O07"></a>
### O07 · Family-aware inspection and independent release evidence

**Recommend for M1.** Extend existing CLI/MCP/query/export and evaluator operations to inspect the
same pinned record, its field evidence, coherent alternatives and terminal reason. A table record
must support cell/header/note retrieval and faithful export. Coverage and gaps must remain visible
when there are no accepted records. No new dashboard is necessary to deliver this workflow.

Freeze guideline, supported subsets, source population and development/fitting/final partitions.
Related editions, overlapping windows and repeated tables stay together. Within-book chapter
splits support within-book claims only. Use independent references and source-region denominators;
score full records, qualifications and evidence separately from partial fields. Fit thresholds
before final assessment. SciPy resampling/statistical kernels support evaluation, but selecting
the independent sampling unit and valid clustered interval remains an evaluator responsibility.
Reuse the protected evaluator and extend its family model rather than duplicating it.

Sources: [evaluation design](../design/D7-evaluation-goldens-outer-loop.md),
[SciPy §8](../libraries/scientific_compute/scipy.md),
[release evidence design](../target-pipeline-design/rollout-and-evaluation.md).
Delivery requires actual CPU extraction and consumer journeys for all released families; static
contracts and this review do not establish any release gate.

## Broader opportunities and comparative disposition

The parsing, scientific-compute and data-model collections supplied discovery leads, including
advanced capabilities; this is not an ecosystem-wide applicability assessment. The following
options have concrete value but do not all belong in the first release.

<a id="O08"></a>
### O08 · Reviewable identity proposals and linkage diagnostics

**Stage beyond the local M1 baseline.** Splink comparisons/blocking, parameter estimation and
pair predictions could help an operator inspect entity matches across larger corpora. Start M1
with scoped identifiers, released aliases, lexical candidate retrieval and explicit local/new/
unresolved identity. RapidFuzz can broaden candidates without authorizing a merge.

Promote Splink only for a population with repeated multi-attribute records and independent match/
nonmatch evidence. Its pairwise probabilities and clustering are distinct decisions: connected
components can bridge incompatible entities and do not enforce cannot-links or scientific sense.
Keep linkage proposals under current identity policy with exclusions and full candidate context.
A symbol spelling or similar definition is not a multi-attribute identity record by itself.
Sources: [Splink §§2–8, 16](../libraries/scientific_compute/Splink.md),
[RapidFuzz §§2–3](../libraries/parsing/rapidfuzz.md). No Splink/DuckDB version compatibility is
qualified here; backend integration must be checked before adding it.

<a id="O09"></a>
### O09 · Fitted calibration, factorized inference and population estimation

**Conditional extensions.** Scikit-learn calibration/stacking and statsmodels fitted models can
improve uncertain decisions once isolated labels support fitting. pgmpy can reduce repeated
assignment work on suitable sparse factorized problems. Pyro is relevant only for a separately
justified learned probabilistic model; causal discovery does not follow from extracting causal
language. Prediction-powered inference (`ppi_py`) addresses population estimands with its own
sampling/reference requirements, not per-record factual certification.

Promotion requires an explicit target decision/estimand, valid training/reference separation and
additional correct whole records or useful population evidence compared with the simpler route.
The sources are [scikit-learn](../libraries/scientific_compute/Scikit-learn.md),
[statsmodels](../libraries/scientific_compute/statsmodels.md),
[pgmpy](../libraries/scientific_compute/pgmpy.md),
[Pyro](../libraries/scientific_compute/pyro-ppl.md), [PPI](../libraries/scientific_compute/ppi_py.md).
These remain capability leads, not selected APIs or dependencies.

<a id="O10"></a>
### O10 · Guided terminology, schema and representation evolution

**Stage behind reviewed gaps.** LinkML-map can serve a concrete schema-to-schema transformation;
LinkML-datalog/RDF/SHACL or ontology tooling can serve a specified rule, graph-interchange or
vocabulary workflow. Existing domain operations and prepared validators suffice for M1 shape and
publication ownership. Adding another rule engine, codec or RDF store without such a consumer
would multiply semantics and lifecycle work. Schema Automator can propose structures; examples
alone do not authorize domain meaning. Lark/regex/Pynini/SymPy remain focused parser/normalization
leads where current numeric or declaration readers leave a concrete gap.

Sources: [LinkML-map](../libraries/data_model/linkml-map.md),
[LinkML-datalog](../libraries/data_model/linkml-datalog.md),
[ontology toolkit](../libraries/data_model/oaklib.md),
[SHACL](../libraries/data_model/pyshacl.md),
[Schema Automator](../libraries/data_model/schema-automator.md),
[Lark](../libraries/parsing/lark.md), [SymPy](../libraries/parsing/Sympy.md).
Preserve the existing exact/scientific numeric policy; a generic solver must not silently replace it.

<a id="O11"></a>
### O11 · Routed specialists and richer record families

**Follow-on.** Explicit ordered procedures, multilingual packs, supervised/LoRA specialization
(with DoRA as an evaluated alternative), distant
coreference/discourse and corpus support models can extend useful coverage. First demonstrate
persistent source-grounded gaps after schema/context repair; use the same whole-record/evidence
gates and regression population. Procedures remain shadow output until the five core families
ship. Keep support/opposition and known citation origins in M1; latent truth estimation, exhaustive
stream attribution and learned value-of-information routing require separate assumptions and
outcome evidence. Generative assistance would require an explicit revision of release scope.

## Combined capabilities and supplemental dispositions

**Proposed reassessment · 2026-11-03.** The original reference's combined APIs, attributes,
constrained decoders, source spans and specialization facilities make the supplemental mechanisms
more useful in composition. The integrated design selects the following workflows, without
assuming that the native decoders already share one globally coherent interpretation.

| Combination and consumer benefit | Selected design and alternative/limit |
| --- | --- |
| Compact combined schema + shared candidate pool + multi-label role conditioning | Co-produce compatible mentions/roles/records on one coherent context, then route missing roles. Compare focused schemas when competition hides candidates. Version prompts/examples and never assume changed schemas reuse earlier encodings. |
| Mention attributes + anchored records + native assignment | Candidate value-role observations join grouped quantities by exact source occurrence. Native exclusivity prevents duplicate same-field use; outer interpretation checks role/qualifier attachment and shared conditions. Independently extracted flat lists remain the comparator, not the default reconciliation framework. |
| Rule/grammar spans + original text maps + explicit-span scoring | A numeric parser or overlapping spaCy rule identifies a span missed by proposals; the qualified low-level bridge scores aligned model-word spans and the same outer assembler consumes them. Pool overflow and missing alignment have explicit dispositions; this does not force the span into a record or certify it. |
| Score/decode separation + alternative constraints + complete-record evaluation | Re-decode Classifier scores only under a matching compiled-schema fingerprint and supported decode settings; changed schema constraints require re-scoring too. Qualify JointIE lattice reuse separately. This fixed-evidence comparison supplies no additional independent observation. |
| Shared preparation + native batching + source-aware windows | Prepare and map once, batch compatible schemas/lengths, retain per-window alternatives before native merging. Reuse compatible encoder state only when the actual encoded batch, queries/masks and model profile match. Prefer combined APIs over a new general tensor cache. Classifier(model)/JointIE(model) can share resident weights, but shape-valid hidden states do not prove schema/token compatibility. |
| Native dataset alignment + injection-free diagnostics + targeted adaptation | Attribute proposal, scoring and grouping loss separately before selecting a repair. Explicit occurrence labels and capacity/error accounting prevent injected gold or skipped dense examples from creating spurious improvement claims. |

A worked statistics case is “Group A: mean 12, SD 3; Group B: mean 10, SD 2.” Rule spans and GLiNER
candidates are anchored by original occurrence, role attributes distinguish mean/dispersion, and
native grouped assignment associates values with groups. A shared population or confidence note
remains nonexclusive. Outer interpretation preserves the complete cohort/condition and missing
sample-size state. If natural anchor detection fails, latent grouping is a controlled challenger;
if a number is never proposed, explicit-span recovery is a different controlled action. No change
in model grouping turns a source statement into scientific truth or a calibrated decision.

The remaining supplemental mechanisms have these dispositions:

- **Integrate now into contracts:** explicit splitter restoration, preprocessing synthetic punctuation,
  strict schema admission and validator binding, checkpoint-active head/pool provenance, classified
  enum evidence, task-specific null/count semantics and local dependency-profile qualification.
- **Conditional M1 routes:** latent/anchorless grouping, count-guided retention and bounded supplied-span
  scoring. Require a source-grounded gap, selected operation signature, complete-record comparison
  and actual CPU/coordinate qualification before enabling a route.
- **Conditional specialization:** native dataset statistics/validation and literal-entity alignment diagnostics; explicit negative/nested supervision; injection-off recall diagnostics;
  gold-capacity failure and strict data/numerical handling; supervised/LoRA/DoRA comparison. Native
  dry-run diagnostics do not update parameters or replace held-out family assessment. Default
  capacity failure retains the population; explicit skips/truncation must retain their denominators.
- **Defer runtime alternatives:** BF16/FP16, compile/attention/packing strategies and alternate internal
  streaming/vectorized execution until an actual CPU problem warrants comparison with FP32. Do not
  import GPU-derived packing cutoffs as CPU performance facts or change trained representation
  modules as casual tuning. `export_mode` is not an ONNX export capability.
- **Scoped follow-ons:** Decide-340M/Decide-1B/multilingual Decide have distinct architecture/heads;
  safety/PII/combined checkpoints require a sensitive-source or agent workflow with explicit demand.
  They add no default statistics-release requirement. Detection is not redaction or a security proof.
- **Alternative interface only:** hosted batching/partial results/retries and native Transformers
  integration are not local-feature parity or an automatic fallback. Hosted record builders omit
  local features. Saved weights/tokenizer do not replace the runtime deployment manifest; the local
  extra includes PEFT even though adapter imports can be lazy. NCCL/DDP does not imply CPU training.

The exact detailed source contracts and qualification scenarios live in the
[deployment](../target-pipeline-design/gliner-deployment.md#supplemental-capability-integration) and
[evaluation](../target-pipeline-design/rollout-and-evaluation.md#supplemental-gliner-capability-comparisons)
pages. Original opportunity IDs remain stable; these mechanisms deepen O01/O02/O05/O06/O11 rather
than create another opportunity register or a recommendation-audit publication.

## Interactions, decisions and architectural assessment

O01/O03 provide the context/evidence foundation for O02/O04/O05. O06 supplies execution ownership;
O07 is part of delivery rather than optional presentation. Settling contracts first does not
require a universal solver or completion of every specialist. The existing WP0–WP6 decomposition
remains a delivery proposal, not an adopted implementation plan or another progress ledger.

| Judgment | Proposed assessment and remaining obligation |
| --- | --- |
| A1 local change | Shared context/observation/record contracts localize pack changes. A new family still needs semantic roles and consumer/evaluator support. |
| A2 explicit meaning | Field states, occurrence/fact identity, evidence precision, interpretation and admitted-rule closure have separate owners. Enforcers and generated projections must be delivered together. |
| A3 composition | Prefer native GLiNER operations, existing model/publication scopes and SciPy numerical kernels; optional engines have explicit promotion conditions. |
| A4 execution fit | Coherent contexts, set joins, bounded components, resident models and private preparation provide a credible route. Dense connected components and actual CPU/RSS fit remain unresolved release premises; protective limits alone do not establish support. |

Core 3.3 and the efficient-architecture companion guide this comparison; code-intelligence 1.4
fidelity, explicit coverage, pinned claims and non-circular evaluation apply by the repository
binding. Program-analysis-specific obligations do not create new M1 functionality. G1–G8 and
CI evidence/coverage constraints shape the proposed contracts; no runtime gate is reported passed.
No new checker, audit, numerical architecture score or benchmark campaign is introduced.

Adoption needs versioned record/evidence and interpretation contracts, CPU policy/operation changes,
consumer/evaluator extensions and the corresponding D1–D8/ADR decisions through existing routes.
In particular, preserving current `agent.opus` extraction as the only path would contradict M1's
selected independence requirement. No accepted ADR is amended here; no automatic rule or scope
adoption follows from these recommendations. Unscheduled opportunity reasoning stays in this
review; selected work transfers to one owning implementation plan without copying mutable status.

## Evidence limits and completion

Three bounded specialist contributions covered extraction/context, numerics/linkage and model/
analytics integration. Independent inspection of the integrated design identified an overstated
resource-supervisor reuse claim; the design now distinguishes existing task/cancellation ownership
from proposed CPU admission and worker supervision. No further material issue was identified in
that scoped inspection; this is not whole-system acceptance. The coordinator inspected source and
integrated the judgments. Context7
lookups led to upstream/tagged documentation for consequential GLiNER, numerical and analytical
contracts. Local overviews supplied broader discovery leads; their research versions are not
assumed equal to current dependency pins. No library overviews were rewritten. The supplemental reassessment additionally inspected tagged
record/schema/engine/processor/trainer implementations and immutable base/multi configurations.
It corrects the former source-uncertain cardinality/explicit-span statements while leaving local
runtime and quality evidence unestablished. The initially dirty source document was committed independently as `4720b9a7` with unchanged
blob during subsequent plan authoring. Optional native formation, structured
assignment, original attribute/combined APIs and supplied-span recovery were assessed in composition;
shared model residency and exact schema fingerprints constrain reuse. The original base-install
claim is qualified by the supplemental reported import issue, not repeated as an import guarantee.

**Completed:** detailed proposed target, grounded opportunities O01–O11, comparative dispositions,
worked contract challenges, consumer/compatibility impacts and staged uncertainty routes.
**not_run:** model inference, runtime probes, corpus evaluation, calibration, performance profiling,
product tests and provider journeys; the review made no quantitative benefit claim needing a probe.
Documentation maintenance/publication checks are reported in the session handoff separately.
The proposed gates in the rollout page remain unestablished. The next decision is selection into
implementation planning, including the named qualification prerequisites, rather than claiming
that M1 has been implemented or released.


## Implementation planning owner

**Proposed plan scope, 2026-11-03.** The [M1 coordinator](../plans/first-production-milestone_2026-11-03.md)
now owns the planned O01–O07 packages, WP0–WP6 mapping and conditional investigation/disposition
routes. O08–O11 remain trigger-based opportunities with their value argument here; no unconditional
implementation adoption follows. Execution and runtime qualification have not started. The operator
clarified that prior UM code functionality and validation are complete; its remaining agent
assessment/follow-up work is distinct from the new M1 scope.
