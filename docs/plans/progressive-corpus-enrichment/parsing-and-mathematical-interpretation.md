# Parsing and mathematical interpretation

**Implementation target and bounded execution evidence, updated 2026-11-05.** This companion develops PCE-07 and PCE-08
from [review O04](../../functional_reviews/progressive-corpus-enrichment_2026-11-04.md#O04)
and [O03](../../functional_reviews/progressive-corpus-enrichment_2026-11-04.md#O03).
The [coordinator](../progressive-corpus-enrichment_2026-11-04.md) owns package state,
execution order, rule-change disposition and combined completion. This document owns the
parsing and interpretation target and its acceptance obligations, without a second progress
ledger. Baseline examined: `a3b0f21d`; documentation inspection: 2026-11-04 local date.
The selected execution boundary below supersedes blanket `not_run` statements for its route.
Native sparse inference, learned-model alternatives and unselected parser mechanisms remain
Proposed, with their original applicability triggers.

## Selected implementation and evidence — 2026-11-05

**Implemented and bounded Tested; selected paired source/output assessment completed2026-11-05.**
Annotationv2 reconstructs retained spaCy columns in a consumer-local native view, preserving
token/whitespace coordinates, heads and explicit sentence ownership. Rules share the resident
vocabulary and prepared matchers. The selected primary-region filter applies before context
widening/model calls; unrequested regions retain unknown coverage. No PDF/OCR reread is needed.

GLiNER2.5-base-v1 at revision `54785d51df8d86a0d8f2eb212fec15871aad2c4d` uses the existing
`gliner2[local]==2.1.0` worker and native entity/AttributeGroup/directed-relation interfaces.
Returned extents, repeated endpoints, common computation dependencies and raw reports survive.
Local adapterv2 makes attribute meaning the returned label; native confidence is retained
separately as a raw score. Oldv1 report bytes and comparisons keep their original semantics.
Request-specific schema refusal yields a limited operation and leaves the healthy resident
worker available; actual model/IPC faults remain terminal. Actual same-PID refusal→valid-request
execution qualifies that distinction, alongside controlled fault cases.

Matched exact-input/checkpoint/schema probes show that the previous codepoint recipe returns
zero distribution spans/roles/relations on two named passages, while explicit whitespace returns
eight distribution spans/roles and six relations. These are returned proposals, not correctness
labels. The go-forward contextual source recipe therefore selects existing whitespace policy6.
The original codepoint corpus run34, its raw data and the corrected89-gap diagnosis remain;
the sealed whitespace corpus run40 is recovered without rerunning extraction. Fifteen selected
primary regions plus bounded related/window contexts define this experiment, not full-book coverage.

Lark exposes captured-native-text syntax with exact grammar/hash/prefix/tail/tree coordinates,
explicit source-health unknown and separate failure diagnostics. This mode claims no recognized
LaTeX, original glyph fidelity, numerical correctness or interpreted scientific truth. The
recognized-only mode retains its stricter source prerequisites. Conditional JointIE/lattice/SPPF
and training branches below remain untriggered.

The shared bounded log-space executor now accepts local marginal/composite questions alongside
the strict record adapter, preserving full-normalizer/event-union/coherent-alternative and
invalid/infeasible/numerical/limit/cancellation behavior. Actual retained run31 seals the local
question as `not_run`: no genuine domain factor policy applies. Its5099 useful contributions
remain inspectable. No extraction score is converted into a probability. There is no actual
useful sparse request beyond the full-joint guard, so Pyro/pgmpy activation is untriggered and
not passed. The concrete mechanisms and acceptance obligations below remain the selected route
if that trigger occurs. [Local evidence](../../design_review/evidence/2026-11-05_pce-local-capabilities/README.md)
owns commands, native/provider results and the final paired assessment boundary.

RC01–RC08 were accepted for planning on 2026-11-04. RC02 supplies the contribution model;
RC07 permits local mathematical questions with optional selected composite events. Their
successor ADRs and owning architecture edits precede the production changes that depend on
them. Planning acceptance does not supersede an accepted ADR by itself. Preserve the surviving
whole-record contract, source custody, independent evaluation and numerical obligations.

## Purpose and boundary

Make a located term, syntactic expression, role, relation or qualification independently
useful before a complete record exists. Then support explicit local and coupled decisions
where alternatives actually interact. A parser supplies evidence and proposals; inference
constructs an interpretation relative to declared candidates, factors and constraints;
assessment supplies separately justified correctness claims. Neither grammar success nor
normalized model weight establishes source truth.

PCE-01/02 own released contribution contracts and initial retained-output adapters. PCE-03
owns independent judgments, frames and statistical assessment; PCE-04 owns public qualification;
PCE-05/06 own contextual retrieval, relationship selection and identity integration. PCE-09
owns export and lifecycle adoption, PCE-10 cross-document products, and PCE-11 assembled
qualification. These packages consume this companion's outputs without taking ownership of
parser or inference meaning. Exact shared definitions belong in
[contributions and semantic contracts](contributions-and-semantic-contracts.md#shared-contracts),
especially its [operation contract](contributions-and-semantic-contracts.md#operation-contract),
[source-coordinate identity](contributions-and-semantic-contracts.md#identity-and-source-coordinates),
[independent axes](contributions-and-semantic-contracts.md#independent-axes) and
[dependency/reuse contract](contributions-and-semantic-contracts.md#dependency-and-reuse-contract),
then their executable semantic declarations. Adjacent consumer plans are
[assessment](operation-assessment-and-qualification.md),
[embeddings and linking](contextual-embeddings-and-concept-linking.md),
[publication and lifecycle](publication-review-and-lifecycle.md) and
[cross-document products](cross-document-structural-products.md).

Immediate work uses existing pinned parsers and the bounded log-space executor. Native exact
factor inference, learned reliability models and specialized statistical/constraint engines
are conditional branches with different triggers. No obligation to install every reviewed
library, adopt both Pyro and pgmpy, retrain a model, construct a universal solver language or
introduce causal discovery follows from O03/O04.

## Existing foundations and the changes they need

**Implemented baseline, source-inspected 2026-11-04; no tests rerun for plan authoring:**

| Owner | Reusable behavior | Required change or preserved limit |
|---|---|---|
| [record_interpretation.py](../../../python/corpus-structure/src/corpus_structure/semantic/record_interpretation.py), `InterpretationRequest`, `interpret_records` | Named candidates, explicit log potentials and assignment-relative hard masks; exact retained-joint enumeration; event unions, marginals and coherent alternatives | Requests are currently limited to three record templates and at least one complete-record event. Generalize question selection while keeping record-specific completeness validation at its adapter |
| Same owner, `SearchLimits`, `SearchDiagnostics` | Defaults: 65,536 states, 1,024-state blocks, 64 MiB numerical workspace, ten seconds and five displayed alternatives; explicit invalid/infeasible/numerical/resource/cancelled outcomes | Connected components are diagnostic. The guard covers the full Cartesian support and does not authorize independent component solves or approximation |
| [record_readings.py](../../../python/corpus-structure/src/corpus_structure/methods/record_readings.py), `interpret_candidate_readings` | Retains complete-reading alternatives and seals actual interpretation requests/results; absent applicable real factor policy yields `not_run` | Preserve that independent baseline. Extraction confidence must not be manufactured into calibrated potentials; add local consumers beside the record adapter |
| [ingest/annotations.py](../../../python/corpus-structure/src/corpus_structure/ingest/annotations.py), `AnnotationProduct`, `restore_annotations` | Persisted source-bound token, space, lemma, POS, morphology, dependency-head, sentence and piece columns with profile identity and availability | Detached columns are not a serialized native `Doc`. Supply a checked consumer-local native view without rerunning the linguistic pipeline for each rule |
| [math/scope.py](../../../python/corpus-structure/src/corpus_structure/methods/math/scope.py) | Existing `Matcher` and `PhraseMatcher` binder patterns | Reuse preparation where compatible; dependency matching is an added operation with explicit annotation prerequisites |
| [math/grammar.py](../../../python/corpus-structure/src/corpus_structure/methods/math/grammar.py), [math/prepared.py](../../../python/corpus-structure/src/corpus_structure/methods/math/prepared.py), [math/native.py](../../../python/corpus-structure/src/corpus_structure/methods/math/native.py) | Earley, explicit ambiguity, propagated positions, source/profile interpretation, `PreparedMathInput`, separate syntax and interpretation operations | Retain coordinate bridges, macro authority, ambiguity and bounded lifetime. Expose useful syntax alternatives through contributions without making mathematical validation a syntax precondition |
| [schema/rulelang.py](../../../python/corpus-structure/src/corpus_structure/schema/rulelang.py) | Existing typed rule-language owner | Extend declared operation contexts there; do not create a parallel predicate evaluator |

The architectural owners are [D4 parsing operations and method cards](../../design/D4-method-catalog.md),
[D5 interpretation and consolidation](../../design/D5-consolidation-identity-confidence.md),
[D1 representation](../../design/D1-knowledge-representation.md) and
[D2 declarations](../../design/D2-schema-and-guidelines.md). D5's current stronger record
admission remains a separate claim. Existing record consumers and their labels continue to
mean what they meant; local products are not a relabeling of historical failed record judgments.

The focused foundation assessment favors composition under those owners. Typed contributions
must govern producer mapping and downstream decisions, rather than becoming display-only rows.
Retained annotations remove repeated model work; local query selection removes a false record
precondition. Neither change needs a new service, process pool or generic provider framework.
This follows FP-04/A2, FP-07/A4 and the relevant source-fidelity and unknown-state rules of the
[declared standard](../../design_review/design_principles/standard.toml).

## PCE-07 — Compose parsers around structural questions

### Prerequisites and delivered capability

Consume the implemented PCE-01 contribution/relation identity and operation-result contract,
including exact source coordinates, ordered real pieces, input/output populations, dependency
identity and non-positive outcomes. Consume PCE-02's working retained-report mapping before
changing a producer. PCE-03 supplies frozen local questions and judgments needed to compare
changed behavior. Agreement on a schema alone does not establish those working prerequisites.

Deliver declared parser operations whose useful outputs survive independently of complete
assembly. First select recurring cases from retained-output assessment: a term whose alias is
wrong; an accurate table value whose row or unit attachment is unresolved; an actor/object swap;
or a condition attached beyond its clause. These motivate the parser composition and fix the
local acceptance questions. They do not mandate every parser on every input.

### GLiNER2.5: discover spans, classify spans, propose links, group records

Retain `gliner2[local]==2.1.0`, the existing resident boundary checkpoint/worker and native
record frontend. Implement operation-specific schema composition at the existing source
method/worker boundary, not a second inference service:

1. Use `AutoExtractor` entity extraction with returned spans to propose located occurrences.
   Check each returned extent against the exact prepared text and map it through the existing
   piece bridge. Equal strings at different offsets remain different occurrences.
2. Compose `.entities(...).entity_attributes({...})` with `AttributeGroup` for attributes
   conditioned on decoded mentions. Preserve `applies_to`, single-label versus multilabel
   semantics, thresholds and `qualify_labels`. A missed mention belongs to occurrence discovery;
   it cannot become an attribute-classification error. Attribute absence is not a negative label.
3. Use relation extraction for a declared predicate and endpoints, retaining endpoint spans,
   direction, qualifiers and proposal identity. Independently emitted entities and relations
   require exact coordinate reconciliation. Repeated endpoint text or output list position is
   insufficient. Unresolved endpoints remain explicit rather than being attached to the first
   equal string.
4. Preserve native structured-record mode where within-context grouping is the question.
   Combined schemas may share a native call, but retain the identity and assessment grain of
   each returned contribution and their common computation dependence. Field fragments retain
   native order, individual extents and the checked source-order bridge. Confidence order and
   concatenation across intervening source content cannot define a new source literal.

Use native returned field/group/fragment scores only under their declared raw-score meaning.
Retain complete raw reports through the existing custody owner. The adapter exposes actual
returned proposals and known stages; it must not infer hidden proposals or suppression reasons
from an absent downstream field. Schema competition, overlap behavior, tokenizer, truncation,
thresholds, candidate caps, checkpoint and requested/effective configuration enter operation
identity where they can change results.

Preserve existing natural/latent/anchorless native grouping identities rather than selecting
one universal record frontend. A recurring observed grouping error can trigger a comparison
within the existing worker: natural formation where a source anchor actually exists, latent
formation for meaningful within-context grouping without that anchor, or anchorless formation
where the released checkpoint supports the requested question. Keep actual returned count and
count-guidance/abstention diagnostics when available; never infer a hidden candidate count from
the assembled record count. Count correctness, field-to-instance attachment and field-span
correctness are distinct assessment questions.

A supplied-span or forced-candidate bridge is conditional on an operation that actually needs
attribute/role scoring at an independently supplied occurrence. Establish exact checkpoint/API
support, source mapping and semantics first. Native post-selection `AttributeGroup` scoring does
not itself promise a public supplied-span API. Supplied-span diagnostic assessment names its
different input population and isolates attribute/attachment behavior from mention recall;
reference spans cannot enter ordinary discovery assessment.

**Conditional constrained decoding.** Select `Classifier` for a real cross-label constraint,
or `JointIE` for a selected operation requiring typed entity/relation endpoints and graph
constraints. A combined `extract` schema alone is not joint decoding. For `JointIE`, construct
the `JointSchema`, bind head/tail types through `.relation(...)`, and select only domain-valid
uniqueness/self-loop/cardinality rules. A relation head enabled in the selected checkpoint is
a prerequisite. Preserve `JointIEConfig` thresholds, beam/greedy selection and candidate caps;
beam search does not establish globally exact inference.

Where diagnosing native candidate loss is a concrete need, use `JointIE.score` or
`extract(..., return_lattice=True)` and retain the actual lattice under declared coverage.
Check feasibility before interpreting an empty graph. False/infeasible decoding, a completed
empty output, limited candidate search and unavailable diagnostics remain distinct. A feasible
typed graph still requires source-grounded assessment. This branch can remain unused when
independent proposals plus domain selection answer the selected question adequately.

Sources: [GLiNER overview §§3–6](../../libraries/parsing/gliner2.md), and release v2.1.0
[entity tutorial](https://github.com/fastino-ai/gliner2/blob/v2.1.0/tutorial/2-ner.md),
[span attributes](https://github.com/fastino-ai/gliner2/blob/v2.1.0/tutorial/13-span_attributes.md),
[joint extraction](https://github.com/fastino-ai/gliner2/blob/v2.1.0/tutorial/15-joint_ie.md).
Context7 resolved `/fastino-ai/gliner2`; its main-branch examples were reconciled with the
versioned attributes and joint-extraction tutorials. API fit does not establish checkpoint
compatibility or extraction benefit. Actual selected-operation evidence is bounded above; JointIE remains untriggered.

Training, LoRA/DoRA, candidate-count guidance changes, numerical precision changes and specialist
checkpoints each require an observed operation-specific failure and a credible mechanism that
addresses it. First distinguish representation/grouping capacity, proposal recall, span/attachment
errors and downstream selection. Training needs faithful target encoding, independent development
and protected assessment populations, held-out uninjected predictions and retained count/proposal
diagnostics where exposed. LoRA additionally needs native head/adapter save-load compatibility;
precision changes need coordinate/output/numerical comparison; specialists need exact task and
checkpoint compatibility. These are conditional investigations with explicit decisions, not
automatic experiments or permission to resume stopped adaptation. Preserve historical attempts
and their incomplete outcomes.

### spaCy: reuse annotation columns and preserve overlapping proposals

Use the pinned `spacy==3.8.18` with its existing source-bound annotation recipe. Construct a
consumer-local `Doc(vocab, words=..., spaces=..., lemmas=..., pos=..., tags=..., morphs=...,
heads=..., deps=...)` from authenticated `AnnotationProduct` columns. Source slices supply
token text; block-local indices supply heads. Retain a token-to-native-piece mapping outside
any mutable library handle. Model or rule consumers cannot retokenize this view.

Reconstruction must establish `Doc.text`, token extents, whitespace, annotation values and
source-piece mapping against the retained source/layout. The constructor's `spaces` values
express a following space; they do not represent arbitrary whitespace by themselves. Reuse
the existing prepared-layout treatment of whitespace and atoms, and refuse a native view
that cannot faithfully reproduce it; a direct-column matcher may serve a question whose
semantics permit that route. Do not silently normalize newlines or synthesize token offsets.
In release 3.8.18, supplying heads can override sentence starts: compare derived native
sentences with the retained sentence ownership, and preserve that source-bound ownership
explicitly for scope consumers. Do not assume two independently supplied columns survive
unchanged merely because the constructor accepts both arguments.

Prepare a view once for the block/profile and the consumers that need it, then release it
after use. Reuse the existing resident vocabulary and annotation lifecycle where appropriate;
do not add an unbounded cross-run `Doc` cache. Require the requested annotations explicitly.
A sentence-only or unavailable-dependency product cannot silently satisfy dependency matching.

Select matching capability by question:

| Native mechanism | Product and use | Boundary |
|---|---|---|
| `PhraseMatcher(attr="LOWER")` | Source-located glossary/alias lexical candidates; shared compiled patterns | A lexical hit does not establish contextual role or canonical identity |
| `Matcher(validate=True)` | Declared lemma/POS/morphology/token patterns for roles and cues | Pattern matches retain rule and annotation dependencies; a cue is distinct from its attachment |
| `Doc.spans` or explicitly configured `SpanRuler` | Overlapping and nested typed candidate spans, separated by operation | Preserve competing candidates; avoid `Doc.ents` exclusivity and overwrite defaults |
| `DependencyMatcher` | Actor/object, clause and qualifier-attachment proposals using head/dependency structure | Require complete compatible syntax; retain independent parser-error assessment and scope evidence |

Compile shared glossary and rule preparation once per relevant recipe. A new glossary entry
changes its pattern dependency, not the source annotation run. A changed linguistic model
invalidates affected annotation-dependent proposals, not the physical source occurrence.
Future relationship rules should compose these outputs through domain declarations rather
than teach the public reader how to interpret raw dependency labels.

Sources: [spaCy overview §§2–5](../../libraries/parsing/spacy.md),
[3.8.18 `Doc` implementation](https://github.com/explosion/spaCy/blob/release-v3.8.18/spacy/tokens/doc.pyx),
[native matchers](https://spacy.io/usage/rule-based-matching),
[dependency matcher](https://spacy.io/api/dependencymatcher).
The overview targets 3.8.16; the manifest pin and inspected constructor are 3.8.18.
Context7 `/explosion/spacy` supplies API orientation; selected reconstruction is now exercised by the retained-column controls and actual source consumer above.

### Lark: retain syntax separately from interpretation

Reuse `lark==1.3.1`, the existing Earley grammar and `PreparedMathInput`. Apply declared
grammars to mathematical notation and selected bounded identifier/comparator/condition
languages, rather than unrestricted enterprise prose. Preserve `parser="earley"`,
`ambiguity="explicit"` and `propagate_positions=True` where the existing contract uses them.
The parser's positions index its prepared input; the existing preparation/source bridge
establishes native coordinates. Tree metadata alone does not do that translation.

Expose syntactic occurrences and explicit alternative readings before symbol interpretation
or mathematical validation. Keep source macro definitions, profile rules and mathematical
context with interpretation. Syntactically valid but semantically ambiguous notation remains
ambiguous. Preserve any existing declared trimmed-reading distinction and its original
failure/tail; a recovered or trimmed parse cannot be labeled an exact whole-input reading.

Use explicit alternatives for modest ambiguity. Investigate `ambiguity="forest"` and native
SPPF visitors only when observed ambiguity makes expanded trees the material problem. A compact
forest does not make enumerating all derivations cheap. Limits apply to parsing, interpretation
and forest expansion together; preserve deadlines and main-thread/native worker constraints.
Do not introduce a second parser lifetime or recovery path that drops tokens silently.

Sources: [Lark overview §§3–5](../../libraries/parsing/lark.md),
[1.3.1 API](https://github.com/lark-parser/lark/blob/1.3.1/docs/classes.rst),
[options implementation](https://github.com/lark-parser/lark/blob/1.3.1/lark/lark.py),
[SPPF documentation](https://github.com/lark-parser/lark/blob/1.3.1/docs/forest.rst).
Context7 `/lark-parser/lark/1.3.1` supplied the versioned option semantics.

### Delivery, migration and acceptance

Implement in coherent producer/consumer slices: reconstruct and consume retained annotations;
add the selected GLiNER span/attribute/relation operations; expose grammar syntax/interpretation
products. Each slice includes released mappings, custody, method/configuration identity, coverage
and the PCE-03 assessment consumer needed for its question. PCE-02's retained-output recovery
must remain available before fresh producer runs, so a parser change can be compared with a
frozen baseline. PCE-04 public adoption can follow at each qualified contribution grain.

Migrate affected `m1_source`, native worker/report mapping, grammar/scope consumers and released
operation declarations together. Reuse existing method registration and runtime cancellation.
Remove superseded private mapping or repeated annotation preparation after its actual consumers
move; preserve historical profiles, immutable migrations, raw reports, plans and evidence.
Do not re-identify old observations using a newly introduced schema. Derived new products record
their old input and new transformation identities; fresh producer runs record new operation
identity. A failed later parser or assembly run leaves prior local products readable.

PCE-07 completion requires independently specified controls for:

- Identical text at different source locations, overlapping/nested candidates, discontinuous
  real pieces, Unicode, explicit whitespace and math/reference atoms; no retokenization drift.
- Attribute classification conditional on an actually selected mention; missed mention,
  missing attribute and negative attribute remain separate.
- Repeated relation endpoint strings, swapped actor/object, parallel links with different
  evidence and a condition attached to the wrong clause; source/cue correctness cannot mask
  attachment failure.
- Restoration of token heads, dependency labels and sentence ownership from retained columns;
  missing required annotations produce an explicit unavailable outcome without model rerun.
- Whole-input syntax, declared trimmed syntax, ambiguous interpretation and parse failure;
  grammar success cannot silently become a semantic assertion.
- Unavailable hidden diagnostics versus actual lattice diagnostics; native decoder infeasible,
  limited and completed-empty results; earlier useful contributions survive later failure.

Run focused native integration only for selected parser capabilities; mocks cover transport
faults without establishing provider success. PCE-03 compares unchanged frozen cases at
occurrence/type/role/relation/attachment grains before whole-record effects. New parser calls
and any training remain separately scoped execution work, not plan-authoring evidence.

## PCE-08 — Local and coupled mathematical questions

### Generalize the question, preserve the stronger record adapter

Consume PCE-01's working contribution identities and operation outcomes, plus PCE-03's frozen
question meanings. PCE-07 is a prerequisite only where a selected query needs a newly produced
parser product; already retained contributions can support the first local query. PCE-06 supplies
candidate-selection context and identity exclusions for link questions. These are input contracts,
not a demand to wait for every parser or all linking work.

The semantic owner declares a finite decision set and selected output questions. Keep current
`Decision`, `CandidateSelection`, `Dependency`, `LogPotential`, `HardConstraint` and
`DependenceScope` meanings. Candidate axes retain stable named candidates and declared ordering;
local/new and unresolved alternatives occur where the domain question requires them. Do not
force every decision to have identity-specific alternatives. Keep model, policy, ontology,
context, retrieval and selection dependencies explicit when they affect the question.

A local request may ask for a role marginal, relation direction or qualifier target without
supplying a record template or an event. Selected composite events are optional and name their
actual meaning. Validate event bindings against that declaration: local conjunctions may bind
only the relevant decisions; whole-record events still bind every required role and meaning-
changing qualifier and retain their stricter one-reading derivation rule. The existing three
record templates adapt to the same numerical execution while preserving current validation.
Keep strict `RecordEvent` validation in existing record adapters; the separate local-query contract permits partial bindings only for its explicitly declared question.

An event is a union of assignment predicates; overlapping derivations count each assignment
once. A decision marginal, a MAP assignment, a displayed coherent alternative and a composite
event probability answer different questions. Displayed alternatives keep probabilities under
the complete retained normalizer rather than renormalizing the displayed list. Every probability
remains provisional and candidate-relative, with omitted candidate mass unknown. A normalized
small candidate list is not a claim that the source universe is exhaustive or empirically calibrated.

Independent products need no probability calculation to be retained or assessed. When no real
factor policy applies, retain the independent contribution and report inference `not_run`.
When a larger model is invalid, infeasible, cancelled or limited, its own operation has that
outcome and no completed probability result; prior smaller products remain available. This is
preservation across operations, not partial success of the failed solve.

### Evidence, dependence and constraints

Source boundary agreement, explicit alias wording, header geometry, contextual type compatibility
and retrieval rank can supply declared features. Their owner specifies whether they are raw
features, fitted log weights or source-backed constraints. Adding GLiNER, lexical and embedding
scores independently is not justified merely by naming their common `DependenceScope`.
That object currently joins diagnostic component structure; it does not correct double counting.
Use a compound factor, jointly fitted feature model or justified shared latent model for actual
dependence. Preserve common-call and repeated-window attribution in the shared contribution model.

Hard constraints encode released invariants, explicit identity exclusions or source-supported
impossibility with provenance. Uncertain predicted typing, overlapping spans, multiple roles,
workflow branches and missing data are not universal hard filters. A contradictory hard mask
produces infeasibility, not a uniform posterior or a relaxed constraint. Rules may derive
features or classifications under the existing typed rule-language owner; they do not
independently establish that a relationship is supported by the source.

### Immediate executor and physical route

Extend the bounded executor's request validation and query accumulation; retain its log-space
arithmetic, hard zeros, block polling, preallocation guards and explicit failure classes.
Keep full-support enumeration for the small actual coupled questions admitted by this route.
Do not turn connected-component diagnostics into independence or create bespoke general variable
elimination. Reuse prepared factor shape/index mappings only under complete dependencies; changing
numeric values need not reconstruct stable domain identity. There is no requirement to persist
an execution plan or add a cost estimator.

The workload is selected passage/table/clause candidate sets, with rules and linguistic columns
already prepared per source block. One block can feed several local questions without repeated
model execution. Coupled queries need the full factor-connected universe required by their
meaning; an output selector cannot truncate relevant candidates or intermediate decisions.
The current Cartesian guard is credible for deliberately small queries. A useful sparse query
that predictably exceeds it is evidence for the native route below; repeatedly refusing that
ordinary use is not a satisfactory execution-fit answer. Dense global coupling still requires
question narrowing or an honest limit because another library cannot remove its intrinsic
large intermediates.

### Conditional native exact-factor successor

**Trigger:** an actual selected, useful operation exceeds the bounded full-joint guard and its
factor structure offers exploitable sparsity. Preserve that request and its intended semantics.
Compare Pyro's exact enumerated contraction with pgmpy's finite Markov-factor execution only to
the depth needed to choose. Pyro is the numerical-fit lead because it accepts log factors;
pgmpy is the declarative finite-factor alternative. Neither is an installed dependency promise,
and adopting both is not an acceptance condition.

**Pyro candidate, research baseline 1.9.2.** Compose one model-enumerated finite
`pyro.sample(..., dist.Categorical(...), infer={"enumerate": "parallel"})` site per decision,
`Vindex` to select each potential along named enumerated axes, and `pyro.factor` for its log
contribution and hard-mask `-inf`. Use float64 and declared enumeration dimensions. Do not use
`plate` simply to batch coupled decisions: it asserts conditional independence. An empty guide
and `TraceEnum_ELBO(num_particles=1).compute_marginals` provide a candidate exact-marginal route
without SVI, training, guide enumeration or continuous unintegrated latent variables.

Categorical sites contribute their own normalized base density. With uniform base sites of
sizes `K_i`, adding only the desired potentials leaves a constant `-sum(log K_i)` in joint log
weight. Marginals are unchanged, but the partition is not: add `sum(log K_i)` to the native
log normalizer, or compensate through explicitly modeled factors. A nonuniform base requires
assignment-dependent subtraction of its log density to preserve the original factor model,
and must be positive everywhere the intended model has support.
Choose and document one route; never count unary evidence in both the base and a factor.
Establish the public normalization operation for the selected model rather than exposing
private contraction internals as the domain contract.

`infer_discrete(temperature=0)` supplies one MAP assignment; `temperature=1` supplies posterior
samples. Neither yields the deterministic probability-ranked top-k alternatives promised by
the current executor. `compute_marginals` supplies site marginals, not arbitrary overlapping
event unions. For a requested union, compose one Boolean union indicator/mask under native
contraction and compare its constrained partition with the base partition; summing the separate
derivation probabilities would double count overlap. The indicator itself can induce a large
factor, so include event structure in feasibility. Decide an exact bounded alternative-enumeration
route using supported library operations, or restrict this backend to operations that do not
request top-k and retain the bounded route for those that do. No silent sampling substitute,
heuristic top-k claim or exactness downgrade is permitted.

Sources: [Pyro overview §§2–5](../../libraries/scientific_compute/pyro-ppl.md),
[1.9.2 primitives](https://docs.pyro.ai/en/1.9.2/primitives.html),
[enumerated inference](https://github.com/pyro-ppl/pyro/blob/1.9.2/pyro/infer/traceenum_elbo.py),
[discrete MAP/sample inference](https://github.com/pyro-ppl/pyro/blob/1.9.2/pyro/infer/discrete.py),
[Vindex](https://github.com/pyro-ppl/pyro/blob/1.9.2/pyro/ops/indexing.py).
Context7 `/pyro-ppl/pyro` was followed by versioned primary source. The base-density offset
above is a mathematical consequence of the proposed composition, not a measured library result.

**pgmpy candidate, research baseline 1.1.2.** Construct `DiscreteFactor` tables with explicit
variable order, cardinalities and state names, attach them to a `DiscreteMarkovNetwork`, and
use `VariableElimination.query` for retained finite-factor questions. Build undirected factor
connectivity from scopes while preserving domain relation direction separately. Do not invent
causal Bayesian CPDs for compatibility weights. Explicitly add isolated variables and their
unary factors so an isolate is not dropped from the normalizer.

In v1.1.2 the classic non-Bayesian query path returns unnormalized Markov factors. Establish
the scalar normalizer from the raw query factor, detect zero/nonfinite total mass, and normalize
explicitly. Preserve any factor-rescaling constants when reconstructing `log_partition`.
Named classic ordering heuristics are not interchangeable with Bayesian-network behavior;
qualify the selected contraction path or explicit complete elimination order and named-axis
results. Probability-space multiplication/exponentiation can erase small supported weights
that the existing log-space executor retains. Factor rescaling is not by itself a general
underflow solution; reject this candidate for the required numerical envelope if the supported
route cannot preserve it. `BeliefPropagation`/junction-tree reuse is an alternative only where
repeated actual questions justify its preparation and lifetime.

As with Pyro, event unions, coherent alternatives and cancellation are adapter obligations,
not benefits inferred from the library name. Do not request the full joint merely to recover
an answer whose original motivation was sparse inference. If a specific query's union or top-k
needs a large intermediate, narrow supported semantics explicitly or retain the existing route.

Sources: [pgmpy overview §5](../../libraries/scientific_compute/pgmpy.md),
[v1.1.2 exact inference](https://github.com/pgmpy/pgmpy/blob/v1.1.2/pgmpy/inference/ExactInference.py),
[factor arithmetic](https://github.com/pgmpy/pgmpy/blob/v1.1.2/pgmpy/factors/discrete/DiscreteFactor.py),
[Markov model](https://github.com/pgmpy/pgmpy/blob/v1.1.2/pgmpy/models/DiscreteMarkovNetwork.py).
Context7 `/pgmpy/pgmpy` was followed by versioned source for normalization and ordering caveats.

The investigation decides supported query class, exactness, numerical envelope, normalization,
alternative/event support and cancellation/limits before activation. Native tensor calls may
not poll a Python cancellation event inside a contraction. Bound admitted intermediates before
allocation and qualify cancellation/deadline behavior using the existing worker lifecycle;
if isolated termination is necessary, justify and integrate it there instead of inventing a
second pool. If neither candidate meets the actual contract, leave the larger query unsupported
and record the concrete blocker. Do not implement a custom general elimination engine.

### Other mathematical capabilities and their distinct triggers

These are operation choices, not a sequence of mandatory engine adoptions. Context7 was used
for each named API family; linked overviews provide broader orientation. New optional packages
need exact selected pins and ordinary compatibility checks only when their trigger is met.

| Capability and current route | Trigger and selected composition | Decision and acceptance boundary |
|---|---|---|
| `rule-engine==5.1.0`; [overview](../../libraries/scientific_compute/rule-engine.md) | A declared predicate/derived classification; extend `schema.rulelang` typed `Context`/resolver and prepared `Rule` | Immediate reuse when selected rules need it. Preserve missing, explicit null, false, unknown and evaluation failure. `default_value=None` or Boolean coercion must not collapse them |
| `scipy==1.18.1`; [assignment/optimization](../../libraries/scientific_compute/scipy.md) | Genuine one-to-one correspondence: `linear_sum_assignment` with declared unmatched options; linear cardinality/coupling: `milp` with `Bounds`, integrality and `LinearConstraint` | Conditional on those domain semantics. Rectangular assignment alone does not encode voluntary unmatched choices for every endpoint. Preserve solver status/limits; optimal objective is not correctness probability |
| `networkx==3.7`; [overview](../../libraries/scientific_compute/networkx.md) | Declared workflow/scope topology: `MultiDiGraph`, explicit nodes, cycle/reachability analysis and `topological_sort` only for the DAG question | Use native graph algorithms for actual topology. Preserve isolated occurrences, parallel links, direction and provenance; do not impose a DAG on the general knowledge graph or treat reachability as semantic entailment |
| `scikit-learn==1.9.1`; [overview §7](../../libraries/scientific_compute/Scikit-learn.md) | New independently judged operation labels justify joint features; use `Pipeline`, `GroupKFold`/`StratifiedGroupKFold`, and separately justified calibration/threshold selection | Conditional learned feature policy, shared with PCE-03. Group by source/occurrence/common generation dependence as applicable, fit transformations inside folds, separate model-fit/calibration/threshold/protected assessment populations. A splitter preserves supplied groups; it cannot discover valid independence |
| statsmodels; [overview §3](../../libraries/scientific_compute/statsmodels.md), research baseline 0.15.0 | Population-averaged error relationships with credible source clusters: `GEE`; a distinct group-variation question: mixed effects such as `MixedLM` | No immediate addition. Require sufficient independent groups, suitable outcome/link/model and diagnostics. Parser reruns or windows are not new independent groups; do not use mixed effects and GEE as interchangeable answers |
| Splink; [overview §§2,5,7–9](../../libraries/scientific_compute/Splink.md), overview baseline 5.0.0 | Structured identity deduplication with useful comparison attributes and match judgments; null comparison levels, compound comparisons, blocking, `u` estimation/EM and pairwise scoring | No default semantic-link engine. Coordinate with PCE-06 in the [embedding/linking companion](contextual-embeddings-and-concept-linking.md). Qualify exact selected version APIs, blocked-pair recall, dependence, frequency population/lifecycle and exclusion-safe consolidation before clustering; pair scores cannot override identity invariants |
| Z3; [overview](../../libraries/scientific_compute/z3-solver.md) | A concrete need to explain conflicting symbolic constraints: tracked assertions through `assert_and_track`, `check`, `unsat_core` | No immediate addition. Preserve constraint/evidence identities and `unknown`/timeout. A returned core need not be minimal and cannot identify the causal parser failure |
| PPI; [overview](../../libraries/scientific_compute/ppi_py.md) | A prediction-assisted population-error estimand with valid independent judgments and sampling design: an appropriate estimator such as `ppi_mean_ci` | No immediate addition. Assessment/statistics owner selects assumptions, population weights and interval method; predictions do not qualify individual outputs or eliminate labeled sampling obligations |
| CVXPY; [overview](../../libraries/scientific_compute/cvxpy.md) | A concrete convex/conic or mixed-integer formulation benefits from modeling/solver composition beyond the selected SciPy route | No immediate addition. Establish formulation, `is_dcp`/other applicable discipline, available solver capability, selected solver/status and precision before selection; package presence does not imply mixed-integer support |

### Learned and hierarchical uncertainty is separate work

An exact finite-factor query with fixed weights does not require training. A joint feature model
requires newly judged labels at its operation grain and independently assessed generalization.
A hierarchical Pyro reliability model requires an explicit scientific/statistical question,
identifiable data structure, priors, fitted parameters and validation of reliability across
sources. SVI, continuous latent uncertainty and sampling introduce approximation/convergence
obligations distinct from exact discrete contraction. State those assumptions, posterior or
variational diagnostics and the meaning of intervals under the selected model; do not silently
fallback to them when the exact route reaches a limit. Existing whole-reading labels and
calibration artifacts cannot be renamed as role, mention or link correctness.

### Delivery and migration

1. Publish the RC07 semantic/architecture changes through the coordinator's decision route.
   Implement local question validation and optional composite queries alongside the strict
   record adapter. Move existing record calls onto shared numerical execution with unchanged
   whole-record meaning and preserve old serialized requests/results as their original version.
2. Integrate one useful retained-data local query end to end: domain request, real supplied
   factor policy or explicit `not_run`, numerical result, sealed observation, PCE-03 comparison
   and PCE-04/PCE-09 reader/export consumption. A role marginal can be present while a stronger
   record is unresolved. A no-factor operation remains useful without invented probabilities.
3. Add selected parser/link consumers as their working prerequisites become available. Keep
   factor meaning in its domain owner; methods and serving compose results without independently
   recalculating confidence or inference semantics. Remove replaced complete-record-only
   assumptions from migrated local paths, not from surviving record admission.
4. Execute a native-successor or optional-method investigation only when its stated trigger is
   demonstrated. Record the decision and exact dependency move, then implement, migrate and
   qualify the selected query class. Keep the bounded executor as the deliberately supported
   small-question route/reference while it has that real consumer; remove displaced adapters
   after migration rather than retaining unused compatibility layers.

New persisted operation/result versions use normal released-schema migrations and custody.
No destructive database conversion is needed merely to reinterpret old records: historical
whole-record results keep their identity and standing. New derivations from retained inputs
are separate attributable products. New factor/policy/ontology/selection versions invalidate
affected derived interpretations without deleting the physical occurrences. PCE-09 owns the
shared lifecycle and rebuild route; model computation stays outside publication transactions.

### Numerical and semantic acceptance

Extend the existing independent tiny-distribution controls in
[test_record_interpretation.py](../../../python/corpus-structure/tests/semantic/test_record_interpretation.py),
preserving their independent expectations. Do not compute both expected and actual values
through the same adapter, axis mapping or event compiler. Add local questions to those controls
and assess any selected native backend against both hand-calculated distributions and the
bounded reference where its supported domain overlaps.

| Revealing case | Required result |
|---|---|
| A role-only query with no record template and no event | Completed requested marginals/normalizer under explicit support; no fabricated complete-record event. Equivalent strict record query still rejects omitted required roles/qualifiers |
| Joint weights `1,2,3,4` for two binary decisions | Marginals `3/10`, `4/10`, joint first-state event `1/10`; product of marginals is not substituted. `log_partition=log(10)` before any declared offset |
| Duplicate and overlapping event derivations | Boolean union sums each assignment once; an event's total mass may beat the MAP assignment; changing derivation order/duplication does not change probability |
| Requested coherent top alternatives, ties and permutation | Jointly feasible full named assignments, deterministic declared tie behavior and full-normalizer probabilities; displayed mass need not sum to one. Samples and separately maximized marginals are rejected as substitutes |
| Uniform categorical base of sizes two and three | Native marginal equivalence and explicit `log(6)` partition correction; adding a real unary factor counts it exactly once. A nonuniform-base case exposes forgotten base-density compensation |
| Hard zero and all-infeasible support | Zero feasibility is preserved; infeasible produces no success probabilities. Malformed/nonfinite factors retain their proper invalid/numerical failure class even on otherwise impossible states |
| Tiny positive weights and extreme common log offsets | Preserve supported tiny mass within the declared floating-point envelope; normalize without uniform fallback. Finite arithmetic overflow is numerical failure, not invented hard zero. No probability-space adapter may silently lose support |
| Named-axis, candidate, factor and block-order changes | Named distributions agree within stated tolerance; identity and factor scope never depend on library-local node order |
| Omitted candidates, dependence scopes and uncertain typing | Omitted mass remains unknown; a dependence declaration does not change weights; uncertain evidence is not transformed into an unexplained hard filter |
| Cancellation before allocation and during work; elapsed/workspace/state limits | Existing explicit outcomes and diagnostics survive; no partial probabilities or empty completed solve. Parent cancellation drains/terminates selected native work under the actual lifecycle |
| Sparse native trigger and dense counterexample | Actual useful sparse request has a credible admitted contraction route; unsupported dense or event-induced growth refuses explicitly. No full-joint materialization hidden inside a claimed sparse route |

The native investigation may conclude that only a narrower query class is suitable; it cannot
claim replacement parity while leaving required events, alternatives, tiny-weight behavior
or cancellation unresolved. A selected operation can omit top-k by contract before execution;
an operation that promised it cannot discard it after choosing a backend.

## Verification and execution handoff

The following is the verification route; actual commands/outcomes live in the linked evidence. During PCE-07/08 run focused
`uv run pytest` selections for the changed parser/annotation/interpretation owners and relevant
consumer integration; preserve strict markers/configuration. Use actual selected native model
calls only where necessary to establish the new provider path and retain exact source/profile
identity, requested/effective configuration and outcomes. After a dependency or environment
change run `just ready`; pin deliberately without wholesale lockfile upgrades. A Rust boundary
change, if one becomes necessary, uses focused compile/nextest checks with `rustc --version`.

PCE-03 owns independent operation-quality evidence and comparison frames. PCE-11 owns the final
assembled required union, applicable native/provider/nonfunctional results and `just test-all`
then applicable `just hygiene`. Focused package checks do not establish that union. The root's
`just turn-end` remains the final maintenance step of changed turns; workers do not run it.
Save investigations that are actually executed under dated evidence folders and retain failed,
interrupted and infeasible receipts as well as passing ones.

PCE-07 can finish with the selected parser composition and its migrated consumers while a
conditional JointIE/SPPF investigation remains untriggered. PCE-08 can finish its immediate local
query scope without installing a native successor or hierarchical model when their triggers
have not occurred. Record that explicit scope at the coordinator; do not mark the conditional
branch passed. If a trigger occurs within an accepted capability, its unresolved feasibility
constrains that capability's completion until the coordinator disposes the actual result.

Before accepting this companion's implementation, move enduring operation semantics into D1,
D2, D4/D5 and executable declarations through the accepted decision routes. Keep the coordinator's
state and evidence links current. This plan does not resume stopped adaptation, change runtime
defaults, authorize protected-label access or turn a source-inspected proposal into a tested
capability.
