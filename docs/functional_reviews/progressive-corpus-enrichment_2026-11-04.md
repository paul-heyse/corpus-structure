# Progressive corpus enrichment: operation contracts, assessment and linkage

**Proposed recommendations; source-inspected functional-extension review, 2026-11-04
(America/New_York).** Library research continued on 2026-11-05 UTC. This review applies
`functional-extension-review` to the operator-selected revised target, rather than conducting
a diagnostic audit or restarting M1 execution.

Source baseline: `8695e869a8f38bbd521dd88470fff86009f94f05`, plus the operator-supplied
[revised milestone](../target-pipeline-design/production-miletone-one-revised.md) (untracked
at inspection and preserved byte-for-byte with this publication),
SHA-256 `3ed1168d594e6a69e63dca3fdc2345bfea9a3847e7715f35163c53286142177e`.
The supplied document was read unchanged. Current plans and accepted ADRs describe the
implementation and its obligations; this review identifies the changes needed for the revised
functional intent. It changes no production contract, accepted ADR, active-plan disposition,
database, dependency, runtime default or assessment result.

The assessment uses core principles 3.3, efficient-architecture heuristics 1.0, the repository
binding and applicable code-intelligence 1.4 fidelity/graph/unknown-state guidance through
[standard.toml](../design_review/design_principles/standard.toml). Domain modeling, composition,
library leverage and execution fit shape the recommendations. No broad audit prerequisite,
automatic benchmark campaign or new alignment checker follows.

## Recommendation

Make an independently attributable **structural contribution** the useful unit of enrichment.
An operation can establish a source occurrence, propose a contextual type, attach a qualifier,
nominate concept targets or assemble a stronger structure. Each addition has its own meaning,
evidence, alternatives and assessment. A later failure does not erase earlier contributions.

Retain whole-record qualification as a stronger, separately named claim. Replace its role as
the universal product gate with a manifest of assessed structural capabilities and their actual
source populations. A located value, a correct header attachment and a complete table reading
are three assessable achievements; none should silently stand for another.

The coherent immediate direction is:

1. Expose typed intermediate contributions through the existing observation, custody and read
   owners; assess retained outputs before changing or retraining their producers.
2. Add operation-specific source-first and output-first assessment, granular structural diffs
   and a portable review package. Preserve uncertainty about missing or hidden stages.
3. Use explicit local decisions, compatibility factors and constraints for relationships that
   need joint interpretation, while retaining useful independent outputs directly.
4. Add contextual occurrence-to-concept retrieval, an explicit link selector and source-grounded
   dossiers. Embeddings nominate candidates; source-grounded relationship decisions govern use.

This is a functional redesign of the accumulation and assessment boundary, not a proposal to
relax source fidelity or relabel old unsuccessful complete-record assessments as successes.

## Current capability and concrete evidence

**Implemented, source-inspected 2026-11-04:** there is useful infrastructure to extend.

| Current owner | Actual capability | Boundary relevant to this review |
|---|---|---|
| [core/method.py](../../python/corpus-structure/src/corpus_structure/core/method.py), `ObservationDraft`, `SourceObservationReference`; [observations.yaml](../../python/corpus-structure/src/corpus_structure/model/semantic/observations.yaml) | Versioned, attributable observations with source locations, payloads, input references and outcomes, separate from records and coverage | A losslessly retained report is not automatically a typed, independently assessed mention or relationship product |
| [m1_source.py](../../python/corpus-structure/src/corpus_structure/methods/m1_source.py), `_retained_report`; [record_readings.py](../../python/corpus-structure/src/corpus_structure/methods/record_readings.py), `native_model_observations` | Raw native responses, preparation/profile identity, actual returned field/group/fragment scores and dependence attribution survive before assembly | The score projection is diagnostic and skips unsupported confidence shapes; the complete raw response remains. Hidden proposal pools and suppression reasons are not exposed by this adapter |
| [record_assembly.py](../../python/corpus-structure/src/corpus_structure/methods/record_assembly.py), `AssemblyResult` | Located field readings, alternatives, coordinate texts and assembly diagnostics | Failure to identify a canonical record occurrence can prevent a group from becoming a record; it need not mean every returned span was wrong |
| [record_projection.py](../../python/corpus-structure/src/corpus_structure/semantic/record_projection.py), [record_queries.py](../../python/corpus-structure/src/corpus_structure/semantic/record_queries.py) | Typed field, piece, alternative and evidence relations; producer coverage is readable independently of record membership | Public structural roots remain assembled record occurrences; optional producer diagnostics do not supply a standalone operation catalogue |
| [record_alignment.py](../../python/corpus-structure/src/corpus_structure/evaluate/record_alignment.py), [record_gaps.py](../../python/corpus-structure/src/corpus_structure/evaluate/record_gaps.py) | Core/full/evidence comparison, role failures, no-output accounting and paired comparison on the same frozen cohort | Field explanations follow record occurrence alignment. They are not independent span, type, attachment or concept-link denominators |
| [record_interpretation.py](../../python/corpus-structure/src/corpus_structure/semantic/record_interpretation.py) | Bounded log-space factors/constraints, decision marginals, coherent alternatives and composite-event probabilities | Current templates and required events are complete-record oriented; production M1 does not manufacture missing coupling factors |
| [record_fitting.py](../../python/corpus-structure/src/corpus_structure/evaluate/record_fitting.py), [record_policy.py](../../python/corpus-structure/src/corpus_structure/semantic/record_policy.py) | Protected whole-reading labels, fitted parameters, held-out final-event calibration and native admission proposals | These labels and probabilities cannot be renamed as field, relation or mention correctness |
| [identity_resolution.py](../../python/corpus-structure/src/corpus_structure/semantic/identity_resolution.py), [ADR-0029](../adr/0029-identity-exclusions-scoped-reference.md) | Explicit exclusions, distinct known anchors and constrained identity groups | Similarity retrieval must not create a second identity authority or indirectly merge excluded endpoints |
| [record_results.py](../../python/corpus-structure/src/corpus_structure/serve/record_results.py), [record_support.py](../../python/corpus-structure/src/corpus_structure/serve/record_support.py), [record_export.py](../../python/corpus-structure/src/corpus_structure/serve/record_export.py) | Pinned query/CLI/registered MCP journeys and JSONL/Parquet exports with source-reading support | Support is not scientific truth assessment; ordinary record export does not establish original-source coverage |

### What the retained failures actually establish

The [run14 summary](../design_review/evidence/2026-11-04_m1-cpu-readings/attempt-summary-011.json)
retains 294 native calls, 232 raw assembled readings (50 definition, 182 table), and another
232 resolver interpretations. Its raw native groups include 62 definition, 58 formula-context,
13 measurement and 73 table groups. These counts have different grains: native groups,
assembled readings, interpretations and independent source occurrences must not be added or
substituted for each other. Native structural table assembly also means that record count need
not be bounded by the number of native decoder groups.

The [protected development assessment](../design_review/evidence/2026-11-04_m1-independent-assessment/README.md)
reports 190 missing reference occurrences, 80 unaccepted matching table occurrences and zero
accepted readings. The failed policy fits report no complete-reading positives. Those are real
results under that contract. They establish neither that all returned spans are wrong nor that
the book contains no accumulated structure. In that saved assessment, the 80 matches are
occurrence matches; field agreement needs its own comparison.

**New bounded comparison, 2026-11-04:** normal-reader task37/run14/source-view23 candidate bytes
were compared with the independently authored, already frozen feature-fit C24 reference bytes
under the same BC69 release. Of 182 table candidate interpretations, exactly 80 have the 80
reference occurrence IDs. Within that matched subset, existing reading/evidence comparison
semantics agree for every table location, cell location, header path, cell value and caption.
All 80 instead differ in `row_label`, `unit` and `note`. These are field-agreement counts against
this finite reference subset, not a new protected grade or accuracy claim over all 182 candidates.

One actual candidate at `#/tables/0/data/table_cells/8` has header `Poisson`, value `.9048`
and the correct table caption. The reference row label is present `0`; the candidate leaves
it unresolved. Reference unit/note are inspected unstated with evidence; the candidate leaves
them unresolved with unavailable evidence. A detached, authenticated pure whole-reading replay
refuses this candidate because a meaning-changing role is unresolved. Its original standing
remains candidate and its stored policy event is `not_run` because no fitted instance exists.
This is one replay explaining a real whole-reading failure, not a recalibration or promotion.

The correct header/value contribution comes through the **native structural branch**. Same-context
GLiNER proposals include header fragments offered as cell values; credit for the correct native
value must not be assigned to GLiNER. The field-level trace is preserved in the
[bounded comparison evidence](../design_review/evidence/2026-11-04_progressive-enrichment-review/README.md).
Its [finalized record](../design_review/evidence/2026-11-04_progressive-enrichment-review/records/m1.retained-table-contributions.json)
and [catalog-rendered role matrix](../design_review/evidence/2026-11-04_progressive-enrichment-review/contribution-summary.md)
retain the exact count sources and denominators.
It supplies a concrete reason to preserve and expose local success while repairing role inspection
and attachment, rather than treating an unaccepted whole reading as empty knowledge.

The [memoryless probe](../design_review/evidence/2026-11-04_m1-state-inspection/README.md)
is an inspectable local contrast. Its saved core-only result locates `memoryless` at context
offsets 213–223, supplies no defining text and proposes `qs` at 405–407 as an alias. Frozen
piece mapping locates the term at selected source-view21 offsets 6882–6892 and `qs` in formula
text at 6665–6667. The source location of `qs` can be correct while its proposed alias
relationship is unsupported. This offline probe produced no assembled/admitted record; its
saved native outputs are not evidence of an already public reusable mention product.

The [stopped adaptation](../design_review/evidence/2026-11-04_m1-contextual-adaptation/attempt-002/operator-stop.json)
ended after 101 optimizer updates, without a final checkpoint. This review resumes no model
execution and draws no efficacy conclusion from finite losses or target representability.

<a id="O01"></a>
## O01 — Independently retained, typed structural contributions

**Proposed; foundational.** A person inspecting the corpus should be able to retrieve what was
located, typed, associated or inferred without first obtaining a complete definition, assertion,
measurement, table reading or workflow. A parser developer should be able to change a role
assignment without losing the underlying occurrence.

Extend the existing released observation/product model with the smallest useful operation
outputs. The following are semantic responsibilities, not a requirement for a new class, table,
process or database transaction per row:

| Contribution | Meaning and boundaries |
|---|---|
| Located occurrence | An exact source extent or ordered real pieces, with its coordinate space and source revision. It does not itself establish a term, entity, alias or fact |
| Type or role proposal | An attributable classification about that occurrence in a stated context; several types/roles may remain alternatives |
| Relationship proposal | A named, directed or explicitly undirected relationship between identified endpoints, with its own supporting evidence, scope and alternatives |
| Qualification attachment | A condition, exception, negation, modality, attribution, threshold or scope attached to a particular target; the cue and attachment are distinct contributions |
| Normalization or derived value | Original content plus declared transformation and premises; source spelling remains available and is not replaced by the transformed value |
| Composite interpretation | Membership, association, order or dependence among contributions. A workflow branch and a mandatory sequence have different meanings |
| Identity/consolidation decision | An explicit equivalence or distinction under the identity owner, preserving original occurrences, applicable versions and exclusions |

An operation contract declares the question it answers, input scope, output types, preconditions,
versions, alternatives, effects and non-positive outcomes. It also declares how its contribution
can be independently assessed. Domain packs own changing distinctions; common source/operation
identity and observation infrastructure remain shared.

Use source identity independently of interpreted meaning where appropriate. Changing the proposed
type or alias target need not create a new physical occurrence; changing the source, coordinate
recipe or selected pieces can. Equal strings at different locations remain distinct. Repeated
windows over the same occurrence remain separate producer observations of that occurrence.
Several providers can support or dispute one proposition without becoming independent votes.

Separate execution outcome, source-field state, interpretation disposition and assessment. A
successful call can return an unsupported relation. An unresolved interpretation can contain
supported spans. A partial source inspection cannot establish that a field was unstated.
Existing `present`/`unstated`/`inapplicable`/`unresolved` states retain their source meanings;
they do not become a generic progress scale.

**Realization.** Reuse `ObservationDraft`, source observation identity, released payload
validation, input references and ordinary task custody. Add typed projections and selectors for
the selected operation outputs through existing owned reads. Public relation roots must include
independent contributions, not require a `SourceRecord` parent. Existing record fields and
assertions can reference those contributions when stronger structures are formed. Raw provider
reports remain preserved; promoting their contents creates a new attributed interpretation,
never a rewritten historical report.

Build the raw-to-contribution adapter from the retained returned objects, not from the
confidence-only diagnostic projection. A returned source span without a supported native score
shape must not disappear merely because `native_model_observations` has no row for it. Preserve
its score availability separately from its occurrence and proposed role.

**Alternative assessed:** adding a completeness percentage to each current record is smaller,
but cannot expose groups skipped before occurrence assembly and conflates field availability,
relationship correctness and acceptance. Keeping only arbitrary diagnostic JSON preserves bytes
but makes consumers reconstruct domain semantics. Both are insufficient for this target.

**Delivery evidence:** retrieve a term span after definition assembly fails; retrieve `qs` as
source text while showing its alias proposal as unsupported/unreviewed; expose a value with an
unresolved unit; preserve existing record/publication behavior for stronger claims.

<a id="O02"></a>
## O02 — Assessment contracts at the operation's grain

**Proposed; foundational.** Assessment should answer a declared structural question rather than
ask whether an entire book or final record is simply complete.

| Operation | Assessable distinctions |
|---|---|
| Reconstruction/segmentation | Source fidelity, ordering, item/section membership, cell geometry, missing regions and unresolved recognition |
| Discovery/boundaries | Missed occurrence, extra occurrence, exact versus incomplete/overextended boundary, wrong source address |
| Typing/role | Located occurrence versus correct contextual type/role; wrong sense, swapped role and legitimate ambiguity |
| Candidate generation | Target inventory coverage, correct target present/absent from the eligible set, retrieved/missed/displaced candidates |
| Link selection | Correct target or permissible alternatives; wrong type, parent, version, direction, scope, or inappropriate forced choice |
| Qualification/attachment | Correct cue versus correct governing target and extent; lost or overextended condition/exception/negation |
| Assembly/workflow | Correct membership and association, ordering, optional/alternative branches, prerequisite links and unresolved constituents |
| Consolidation | Correct merge/distinction, false merge, missed equivalence, version boundaries and retained source occurrences |

For every selected operation use both **source → structure** and **structure → source**.
An independently selected passage/table/list/document pair supplies a bounded opportunity to
find omissions, including when nothing was emitted. An emitted contribution supplies a bounded
question about source support, spurious structure, duplication or incorrect association. These
sampling frames and denominators remain separate.

Retain a compact assessment unit: source anchors, operation and rubric versions, target output
identity, expected structure or permissible alternatives, actual contribution, judgment, error
category, explanation and assessor provenance. A source-first miss needs no invented output ID.
Reference scope specifies what was exhaustively inspected within that unit; it does not claim
that all knowledge in the document was enumerated.

Reuse independently authored field values, locations and permissible interpretations from
existing reference records when they answer the new operation's exact question. Record that
projection and its scope explicitly. A whole-reading Boolean cannot supply local correctness,
and a record-selected subset cannot supply a source-first denominator for all discoverable
mentions. New independent judgments are needed for the genuinely new questions, not simply to
recreate every existing reference under another format.

Judgments must distinguish supported, unsupported, ambiguous and unassessed questions. For
example, boundary correctness can be supported while role correctness remains unassessed. The
raw native score, an independent judgment and a population performance estimate are different
values with different provenance. Do not derive field correctness from a complete-reading label.

Reuse the protected reference lifecycle and immutable source/frame/pass conventions, extending
its protocol/grain instead of changing the meaning of old record references. Where operations
need new reference shapes or correspondence policies, version them explicitly. Existing A/B/C
work remains evidence at its original whole-reading scope; focused source-grounded judgments
can supplement it without asking authors to reconstruct the entire corpus.

**Before/after comparison.** Compare the same frozen cases and permissible structures. Show
newly captured, corrected, regressed, newly spurious and still unresolved contributions. For a
changed selector hold mentions/candidate lists fixed first; then replay affected downstream
operations to inspect integration effects. Reference changes require a new comparison basis.
Record observed failure separately from hypothesized cause: an omitted qualifier is observed;
an alleged positional bias requires evidence that distinguishes it from other mechanisms.

Use installed Scikit-learn for suitable metrics/error analysis and SciPy through the existing
statistics owner for justified intervals or paired procedures. Count/sample contributions at
their declared grain, account for repeated windows and shared origins, and retain undefined
denominators. Structured qualitative findings are useful when population claims are premature.
No universal completeness index, confidence threshold or minimum reference-book replica is
needed to deliver this capability.

**Delivery evidence:** a review can show a correct term, a missed defining passage and an
unsupported alias as three findings; isolate a correct cell value from a wrong header link;
distinguish missing inventory targets from retrieval misses and selector errors; retain zero-output
source cases and distinguish unassessed material from inspected absence.

<a id="O03"></a>
## O03 — Mathematical construction of local and composite interpretations

**Proposed; central enabling capability.** Mathematics should express the distinctions and
dependencies being interpreted, as well as support assessment. It must not make complete-record
assembly or calibrated probabilities a prerequisite for retaining useful local structure.

### Decision and factor model

Build on `Decision`, `CandidateSelection`, `LogPotential`, `HardConstraint`, `Dependency`,
`DependenceScope` and the existing result model in `record_interpretation.py`:

- Local decisions name boundary, type, role, target concept, predicate/direction, qualifier
  attachment, scope or composite membership. Candidate sets retain unresolved/local/new choices
  where semantically warranted, and preserve exclusions and retrieval limits.
- Local evidence features express source boundary agreement, explicit alias wording, lexical or
  embedding rank, type compatibility or header geometry.
- Compatibility factors express relationships among decisions: role/predicate, concept/type,
  header/cell, condition/statement and version/scope compatibility.
- Hard constraints represent source-backed impossibilities, released invariants or identity
  exclusions, with their provenance. Uncertain typing must not become an arbitrary hard filter;
  overlapping spans, multiple roles and alternative workflow branches are not universally invalid.
- Composite events express stronger interpretations of local products. Their probabilities do
  not replace independent local judgments or establish that the candidate universe is exhaustive.

For example, Finance and Procurement can remain located occurrences while their approver/requester
roles compete. A supported approval relation can remain available while the threshold attachment
is unresolved. The assembled procedure receives a separate membership/scope/dependency assessment.

Current interpretation requests require complete-record events and validate them against selected
record templates. Generalize the domain-owned request/result meanings to allow local questions
and selected composite events, without constructing a universal solver language. A limited or
infeasible larger interpretation leaves prior local products intact. Its own outcome remains
limited/infeasible, rather than pretending the full interpretation succeeded partially.

### Select inference by the actual coupled problem

| Situation | Recommended realization | Material boundary |
|---|---|---|
| Independent local contribution | Retain/assess directly | A probability model is unnecessary merely to save a source span |
| Small genuinely coupled candidate component | Extend the current bounded log-space executor's local query contract | It already handles hard zeros, normalization over retained support, overlapping event unions, coherent alternatives and explicit cancellation/limits |
| Useful sparse coupled problem exceeding the full-joint guard | Native exact factor inference; Pyro is the numerical-fit lead, pgmpy the declarative finite-factor alternative | Establish normalization, numerical behavior, dependency dimensions, alternatives/events and operational limits before replacing the executor |
| Dense global coupling | Narrow the question or report the limit | A different library does not remove large intermediate factors or justify independence |
| Hierarchical uncertainty about evidence reliability | Pyro when a substantive model and independently judged data justify it | Adds fitting and model-validation obligations; not a general requirement for enrichment |

The current executor enumerates retained Cartesian support; its connected components are
diagnostic rather than an elimination strategy. Keep it as an immediate bounded executor and
small-case reference. Do not extend it into bespoke general variable elimination. Trigger the
native successor comparison when an actual useful operation exceeds that guard while having
exploitable factor structure; no such operational need is demonstrated by this read-only review.

**pgmpy.** `DiscreteFactor`, `DiscreteMarkovNetwork`, `VariableElimination.query` and junction-tree
`BeliefPropagation` fit finite compatibility relationships without inventing causal CPDs. However,
v1.1.2 non-Bayesian classic query paths return unnormalized factors; automatic named classic
ordering heuristics differ from Bayesian-network paths. Ordinary factor arithmetic also differs
from the current log-potential contract. Explicitly establish normalization/ordering and preserve
small supported weights; do not promise equivalent cancellation, event unions or alternative
enumeration without an adapter design. Sources: [overview §5](../libraries/scientific_compute/pgmpy.md),
[v1.1.2 exact inference](https://raw.githubusercontent.com/pgmpy/pgmpy/v1.1.2/pgmpy/inference/ExactInference.py),
[factor arithmetic](https://raw.githubusercontent.com/pgmpy/pgmpy/v1.1.2/pgmpy/factors/discrete/DiscreteFactor.py).

**Pyro.** `pyro.factor` accepts log factors; native parallel discrete enumeration and contraction
are a credible route to exact local marginals without training. `TraceEnum_ELBO.compute_marginals`
and `infer_discrete` serve different marginal/MAP/sampling questions. Enumeration dimensions and
dependency restrictions remain substantive model choices; `plate` asserts independence, not just
batching. SVI or hierarchical latent models introduce different approximation/fitting obligations.
Never silently fall back from exact inference to approximation. Sources: [overview §§2–5](../libraries/scientific_compute/pyro-ppl.md),
[1.9.2 primitives](https://docs.pyro.ai/en/1.9.2/primitives.html),
[enumerated inference](https://raw.githubusercontent.com/pyro-ppl/pyro/1.9.2/pyro/infer/traceenum_elbo.py),
[discrete inference](https://raw.githubusercontent.com/pyro-ppl/pyro/1.9.2/pyro/infer/discrete.py).

### Dependence, constraints and graph structure

`DependenceScope` currently joins diagnostic component structure; it does not change factors or
correct double-counted evidence. Declaring GLiNER typing, lexical agreement and embeddings
dependent does not make three independently added scores valid. Combine them through jointly
fitted features, a compound factor or a justified shared latent model.

Use installed **rule-engine** through the existing [typed rule-language owner](../../python/corpus-structure/src/corpus_structure/schema/rulelang.py)
for predicates and derived classifications. Preserve missing, null, false, unknown and evaluation
failure explicitly. The engine does not supply the domain's epistemology; permissive default-null
lookup or Boolean coercion must not erase it. Rules constrain interpretation but do not independently
verify that a source supports the relationship. See [overview §§3, 5, 8–9](../libraries/scientific_compute/rule-engine.md)
and the [primary documentation](https://zerosteiner.github.io/rule-engine/).

Use installed **SciPy** `linear_sum_assignment` when correspondence really is one-to-one and
unmatched choices are modeled. Use `milp` where meaningful linear cardinality/coupling constraints
justify it. Optimal assignment is not a correctness probability. Use **NetworkX** for declared
workflow/scope projections, cycles, reachability and topological order where appropriate. A general
knowledge graph is not a DAG merely because a procedure has prerequisites. Preserve parallel
relationships, direction, isolated occurrences and provenance in the owning data. See
[SciPy §3.5](../libraries/scientific_compute/scipy.md) and [NetworkX](../libraries/scientific_compute/networkx.md).

### Fitting and statistical methods: selected roles and limits

| Library | Proposed role | Adoption condition or limit |
|---|---|---|
| Scikit-learn, installed 1.9.1 | Joint operation-specific feature models, grouped validation, calibration where warranted and separately chosen decision thresholds | New independently judged event labels/populations; whole-reading labels are not local labels. `GroupKFold`/`StratifiedGroupKFold` preserve supplied groups but do not determine the correct grouping |
| SciPy, installed 1.18.1 | Assignment/optimization, descriptive and paired assessment procedures, existing finite-population statistics owner | Match the procedure to the actual frame and sampling design; bootstrap availability does not establish independence or adequacy |
| statsmodels | GEE for population-averaged error relationships with credible source clusters; mixed effects for a different group-variation question | Conditional on the statistical question and adequate independent groups; not needed to count local errors |
| Splink | Structured identity deduplication/linkage with useful comparison attributes, compound comparisons, null handling and match judgments | Conditional specialized identity operation; not the default engine for contextual semantic relationships. Blocking, scoring, frequency lifecycle and clustering require separate assessment |
| Z3 | Explain conflicting symbolic constraints using tracked assertions/unsatisfiable cores | Conditional on a real explanation requirement. An inconsistent encoded subset is not necessarily minimal and does not identify a parser's causal failure |
| CVXPY | No immediate addition recommended | Revisit when a concrete optimization formulation benefits from its modeling/solver composition |
| PPI | Prediction-assisted population error estimation | Conditional on a valid independent judgment sample and inferential question; does not qualify individual outputs or eliminate sampling obligations |

pgmpy, Pyro, statsmodels, Splink, Z3, CVXPY and PPI were absent from the inspected root lockfile
and environment metadata. Their capabilities are research-backed design options, not installed
compatibility or efficacy claims. Relevant guides: [Scikit-learn §7](../libraries/scientific_compute/Scikit-learn.md),
[statsmodels §3](../libraries/scientific_compute/statsmodels.md), [Splink §§2, 5, 7–9](../libraries/scientific_compute/Splink.md),
[Z3](../libraries/scientific_compute/z3-solver.md), [CVXPY](../libraries/scientific_compute/cvxpy.md),
[PPI](../libraries/scientific_compute/ppi_py.md). Exact selected versions need normal compatibility
checks during implementation planning; the newer Splink v5 overview is not an installed API promise.

Do not make discovery of causal graphs from corpus observations an immediate capability. Source
co-occurrence, repeated parser outputs and qualitative failure patterns do not supply the causal
assumptions needed to explain why extraction failed.

<a id="O04"></a>
## O04 — Compose parsing capabilities around distinct structural questions

**Proposed.** Preserve the native grouped-record route and add independently assessable outputs
where the operation needs a span, attribute or relationship before complete assembly.

### GLiNER2.5

Use native source spans from entity extraction for occurrence discovery; `AttributeGroup` for
span-conditioned classification; relation extraction for proposed predicates/endpoints; and
native record mode where within-context grouping is the actual question. Combined schemas can
share work while each returned contribution keeps its semantic operation, source coordinates and
common computation dependence. List-field fragments retain their actual order/locations and
the checked source-order bridge; no confidence sorting or concatenation across real intervening
text changes the source literal.

Use `Classifier`/`JointIE` only for declared constraints that fit the question. `JointIE.score`
and `return_lattice=True` offer an explicit diagnostic surface for a selected future operation;
the current combined adapter does not expose those internal lattices. Typed endpoints and a
feasible decoded graph do not establish source correctness. False/infeasible, limited search,
empty output and hidden/unavailable diagnostics remain distinct. A downstream field's absence
cannot reveal whether the native proposal pool missed it or a hidden stage filtered it.

Span attributes occur after mention selection, so a missed mention is not an attribute error.
Relations emitted independently of entities need exact endpoint reconciliation, rather than
string-based or positional attachment. Combined schema competition, thresholds, overlap policy,
tokenization and truncation are part of the effective operation identity.

This builds on the installed `gliner2==2.1.0` and existing boundary checkpoint/worker; it does
not select training or another inference service. Sources: [GLiNER overview §§3–6](../libraries/parsing/gliner2.md),
[native entities](https://github.com/fastino-ai/gliner2/blob/v2.1.0/tutorial/2-ner.md),
[attributes](https://github.com/fastino-ai/gliner2/blob/v2.1.0/tutorial/13-span_attributes.md),
[joint extraction](https://github.com/fastino-ai/gliner2/blob/v2.1.0/tutorial/15-joint_ie.md).

### spaCy

Reuse the source-bound token/lemma/POS/dependency/sentence columns already produced by
[ingest/annotations.py](../../python/corpus-structure/src/corpus_structure/ingest/annotations.py)
and sealed by `extract.m1_annotations`. Do not rerun a linguistic model for every field or rule.
The current restored product is detached columns, not a ready serialized `Doc`; an adapter can
reconstruct the needed native view or consume columns, preserving token heads, whitespace,
math/reference atoms and native coordinates. Its exact behavior needs focused implementation
checks; successful annotation availability is not linguistic correctness.

Select `PhraseMatcher` for glossary/alias candidates, `Matcher` for declared token/morphology
patterns, and `SpanRuler`/`Doc.spans` for overlapping typed candidates. Use `DependencyMatcher`
where syntactic attachment distinguishes actors, objects, clauses or qualification scope, with
explicit dependency-annotation availability and independently assessed parser error. Existing
[math/scope.py](../../python/corpus-structure/src/corpus_structure/methods/math/scope.py) already
uses token and phrase patterns; it explicitly does not use `DependencyMatcher`.

Do not force overlaps into `Doc.ents`, erase competing annotations with an overwrite default or
allow retokenization to change evidence coordinates. A phrase match establishes a lexical hit;
its contextual role or concept identity still needs assessment. Sources: [spaCy §§2, 4–5](../libraries/parsing/spacy.md),
[span rules](https://spacy.io/usage/rule-based-matching#span-ruler),
[dependency patterns](https://spacy.io/usage/rule-based-matching#dependencymatcher).
The guide targets 3.8.16; the actual pin is 3.8.18. Check exact-version integration rather than
describing the overview's release as the installed one.

### Lark

Extend the existing grammar/syntax/interpretation separation where the source has a sufficiently
declared language: mathematical notation, explicit identifiers, bounds, comparator expressions or
selected structured condition syntax. A successful grammar parse is a syntax contribution;
interpreting symbols, assigning roles and validating a mathematical claim are separate operations.
Lark is not selected as a universal grammar for unrestricted prose or enterprise procedures.

The current [math grammar](../../python/corpus-structure/src/corpus_structure/methods/math/grammar.py)
already uses Earley, explicit ambiguity and propagated positions, with source/profile interpretation
and bounded lifetime. Preserve those meanings and native `PreparedMathInput` ownership. Keep
explicit alternatives for modest ambiguity; consider an SPPF only when actual ambiguity warrants
shared representation. Enumerating every parse can explode even when the forest is compact.
No parse recovery may silently repair or drop source tokens and then claim an exact reading.

Sources: [Lark §§3–5](../libraries/parsing/lark.md), [1.3.1 API](https://github.com/lark-parser/lark/blob/1.3.1/docs/classes.rst),
[forest representation](https://github.com/lark-parser/lark/blob/1.3.1/docs/forest.rst).

**Delivery evidence for this composition:** contrast a lexical occurrence with a role/alias
judgment; preserve overlapping candidates; detect a subject/object swap and condition overreach;
retain syntactically valid but semantically ambiguous notation; compare parser changes at those
layers before interpreting their whole-record effect. No parser is adopted merely because its
capability exists.

<a id="O05"></a>
## O05 — Contextual embeddings and hybrid concept candidates

**Proposed; first embedding job.** Given an independently located occurrence, retrieve plausible
concept targets from a frozen eligible inventory. A complete record is unnecessary.

Encode two versioned representations:

- **Occurrence:** literal mention plus bounded sentence/list-item context, informative heading
  and discriminating context. Table headers can include parent header/caption; workflow steps
  can include procedure heading. Retain the source anchor independently of rendered encoder text.
- **Target:** stable target ID, canonical label, aliases, type, source-backed definition or
  registry description, applicable scope/version and parent entity when meaningful.

A curated glossary or source-backed definition inventory suffices initially. A definition
passage or local/provisional sense can be a target before global identity is established.
Unknown type keeps plausible types eligible rather than becoming an unsupported hard filter.

Generate lexical/alias/fuzzy candidates and dense candidates separately; preserve channel rank,
score and evidence. Fuse and deduplicate by target ID under an explicit bounded policy. Compare
lexical-only, dense-only and hybrid using the same final budget of unique target IDs and frozen
inventory. Do not let hybrid win merely by returning more candidates. The existing
[source search](../../python/corpus-structure/src/corpus_structure/serve/source_search.py) uses
PostgreSQL English `to_tsvector`, `websearch_to_tsquery` and `ts_rank_cd`; it is a useful source
retrieval owner, not an implemented BM25 or concept-candidate operation.

### Encoder and runtime recommendation

Recommend `intfloat/e5-small-v2` as the compact English baseline and exactly
`Qwen/Qwen3-Embedding-0.6B` as the larger challenger. E5's documented query/passage prefixes,
normalization and 512-token input limit require a context recipe that retains the mention and
discriminating evidence. Qwen's task-instructed query representation, different pooling/input
conventions and larger capacity provide a meaningful challenger. Published dimensions/context
limits are capabilities, not evidence of better source linkage or CPU fit.

Prefer direct local `SentenceTransformer` CPU encoding first, with pinned model revision and
recorded prompt, pooling, normalization, input-limit and precision policies. This is a proposed
new encoder integration; its Python/package compatibility and actual workload fit remain open.
Batch within a bounded owned model lifetime and avoid holding database transactions during
encoding. Reconcile the older Jina v5 recommendation explicitly: leave it as an alternative if
technical/operational evidence changes this choice, rather than automatically running three
models or treating licensing as a rejection without an actual operator constraint.

Sources: [E5 model card](https://huggingface.co/intfloat/e5-small-v2),
[Qwen model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B),
[vLLM pooling guide](../libraries/analytical_infrastructure/vllm.md).

vLLM remains a substantive runtime alternative, not the default merely because Nemotron uses it.
The overview targets 0.32.0; the isolated [Nemotron service](../../services/nemotron-parse/pyproject.toml)
pins 0.26.0 and loads a different model. Tagged 0.26 pooling documentation describes
`runner="pooling"`, embedding methods and `/v1/embeddings`, but provides no performance guarantee
over direct Transformers/SentenceTransformers. Its CPU installation documents Python 3.10–3.13,
while root Python is 3.14.10. That leaves this CPU pooling deployment unverified; omission from a
CPU validation matrix does not prove incompatibility. A managed embedding profile becomes useful
when repeated consumers justify residency and service lifecycle ownership. It needs its own
compatible profile and admission/cancellation behavior, without modifying Nemotron's loaded model
or recognition service. Sources: [0.26 pooling](https://raw.githubusercontent.com/vllm-project/vllm/v0.26.0/docs/models/pooling_models/README.md),
[embedding models](https://raw.githubusercontent.com/vllm-project/vllm/v0.26.0/docs/models/pooling_models/embed.md),
[CPU installation](https://raw.githubusercontent.com/vllm-project/vllm/v0.26.0/docs/getting_started/installation/cpu.md),
[CPU model matrix](https://raw.githubusercontent.com/vllm-project/vllm/v0.26.0/docs/models/hardware_supported_models/cpu.md).

### Derived vectors and retrieval identity

Start with PostgreSQL/pgvector exact cosine over the eligible inventory, with deterministic
target-ID tie handling. `vector 0.8.7` in the provisioning specification establishes a selected
extension version, not activation or an existing embedding table. Extend the active semantic
physical model through its existing migration/admission owners after checking actual capability.
Legacy `system.yaml` declarations and D4 M04/M14 cards are design leads, not verified delivery.

Keep distinct identities for:

1. **Vector:** object identity, rendered-input digest, context recipe, model/tokenizer revision,
   encoding profile, dimension, pooling/normalization and storage precision.
2. **Inventory:** frozen eligible target membership, target representation versions, corpus,
   scope/effective-version rules and reliable type constraints.
3. **Candidate list:** occurrence/vector identity, inventory snapshot, channel/fusion/deduplication
   policy and budget. The selector additionally binds exclusions and interpretation policy.

Adding a concept invalidates affected retrieval results while unchanged occurrence vectors remain
reusable. Changed exclusions can invalidate selection without re-encoding. Prompt, context or
pooling changes invalidate the relevant vectors. A claim embedding used for semantic comparison
requires its qualifications first; an anchored mention embedding need not wait for claim acceptance.

HNSW/IVFFlat follow demonstrated scale need. Measure approximate-index recall against exact
neighbors separately from correct-target recall. Filtered approximate scans can underfill the
eligible result set; reduced precision is another approximation to assess separately. Source:
[pgvector 0.8.7](https://raw.githubusercontent.com/pgvector/pgvector/v0.8.7/README.md).

<a id="O06"></a>
## O06 — Explicit relationship selection before identity consolidation

**Proposed.** The candidate generator nominates; a separate selector decides what relationship
the source supports. Preserve a selected target, permissible ambiguous alternatives, a local sense,
a new-concept proposal or insufficient evidence. Low similarity alone establishes none of the
last three: the inventory may be incomplete or retrieval may have failed.

Represent relationship questions explicitly: denotes, alias-of within scope, defined/explained-by,
specializes, compared-with, participates-in, or a domain-owned workflow relationship. Do not
create a universal `semantically_related_to` edge whose meaning cannot be assessed. A comparison
pair need not be an identity pair; process, subprocess, form and system action remain distinct.

Selection consumes lexical evidence, explicit alias/definition language, contextual type, parent,
source scope/version and known exclusions. Start with declared evidence/compatibility policies;
introduce jointly fitted feature scoring where operation-specific labels support it. Add a
pairwise reranker when fixed-list assessment demonstrates a ranking/selection problem rather
than missing mentions or inventory coverage. Cosine, fuzzy scores and rank fusion remain ranking
features. A model-normalized shortlist is not calibrated identity probability.

Preserve [ADR-0029](../adr/0029-identity-exclusions-scoped-reference.md) and the existing identity
owner: no transitive neighbor clustering or selected comparison edge can merge canonical entities
or bypass a known exclusion. Splink becomes relevant for a defined structured identity task,
not as a substitute for this typed semantic-relationship model.

**Delivery evidence:** distinguish onboarding process, activation step and checklist; normal versus
standard normal; the central limit theorem versus the normal distribution; the same parameter
symbol under different parent families; a correct-looking alias in the wrong effective version;
and A–B–C similarity with an A/C identity exclusion. Give the generator reference mentions and
the selector fixed lists to isolate their responsibilities.

<a id="O07"></a>
## O07 — Definition retrieval, clause comparison and source-grounded dossiers

**Proposed; staged cross-document products.** These capabilities make progressive enrichment
useful while preserving the distinction between relevant material and established relationships.

First expose retrieval of definitions or explanations for an anchored usage. Assess whether
the passage defines that usage rather than merely mentioning or exemplifying it, and distinguish
an absent inventory entry from an unretrieved one.

Next nominate clauses/workflow steps worth comparing. Compare actor, action, object, obligation,
condition, threshold, exception, order/dependency and applicable version. `must approve above
$25,000` and `may review above $50,000` are useful neighbors for comparison; an equivalence
or duplicate judgment would erase material distinctions. The examples supplied in the target
are illustrative transfer cases, not measured enterprise-corpus results. No representative
enterprise dataset or enterprise performance claim was established in this review.

Build concept or provisional-sense dossiers as cited structural assemblies: definitions/scope,
accepted and proposed terminology, representative usages, typed relationships, variants,
exceptions, conflicting interpretations and open questions. Preserve original occurrences and
qualifications. A dossier does not adjudicate scientific truth or silently choose a policy version.

Use diversity-aware example selection only after sense, scope, role and version grouping.
Always retain meaningful exceptions and revisions even when near-duplicate wording dominates.
MMR-style selection is a useful mechanism for representative excerpts, not a correctness
criterion or an excuse to omit inconvenient evidence. Assess dossier membership, missing senses,
exceptions, duplication and traceability directly. Sources: the supplied target, [BLINK](https://aclanthology.org/2020.emnlp-main.519/)
for retrieve-then-assess architecture and [MMR](https://aclanthology.org/X98-1025/) for diversity
selection; their benchmark results do not establish effectiveness on this corpus.

<a id="O08"></a>
## O08 — Granular inventory, structural diff and complete review export

**Proposed; immediate operator/research value.** The external reviewer needs enough evidence to
recommend the next refinement without database access or interpreting a single accepted count.

Offer linked views rather than one completion percentage:

| View | What it exposes |
|---|---|
| Source inventory | Original/edition/excerpt identity, known physical-page maps, retained source regions, selected run/cut/release, processing/recognition health and explicitly unprocessed or unavailable regions |
| Operation inventory | Input/eligible/inspected scopes, actual executions, successful/empty/failed/skipped/limited outcomes and available versus hidden diagnostics |
| Contribution inventory | Spans, types, roles, relations, qualifications, alternatives and composite memberships, each independently addressable |
| Assessment matrix | Separate judgments for boundary, type, role, target, direction, attachment, scope, evidence and integration; unassessed dimensions remain visible |
| Gap account | Source-first missed structures and output-first unsupported structures, actual stage observations and hypothesized causes kept separate |
| Change account | Newly captured/corrected/regressed/spurious/unresolved contributions on comparable cases, plus effects of changed upstream inputs |

Distinguish unique physical occurrences, producer observations, interpretations and accepted
assertions. Count them separately by book, source region, operation and version. A full retained
PDF or five selected sections does not establish that every original page was processed or that
all knowledge was assessed. Existing Siegrist material and the three M1 excerpt origins have
different source/release histories; compatible correspondence must be explicit.

Extend existing snapshot capture, read, source inspection and JSONL/Parquet export owners.
The portable package contains a readable overview, versioned machine-readable tables, exact
contracts/rubrics, manifests with counts/hashes, source excerpts/native addresses, per-case raw
outputs and diagnostic references, assessments and paired diffs. Include the actual consumed
context or a reconstructible self-contained source slice for each review case. The `_retained_report`
hash alone is not sufficient for an external reviewer without its source text and piece map.

Common query/CLI/MCP selectors should name source/snapshot, operation/version and contribution
kind, with assessment and interpretation facets separately selectable. Bind continuations and
exports to that selection. Structural comparisons bind the baseline/revised products and the
same source cases; changed semantic grains or sources need explicit correspondence or an
incomparable result, rather than a superficially matched pair of strings.

Shared source material, profiles and raw reports are stored once and referenced by stable IDs.
Stream or spool bounded partitions and publish the manifest after completion. If a required
payload is unavailable, permission-excluded or over limit, identify the omission and its affected
coverage. A selected page's successful export must not be labelled a complete corpus export.
Do not copy model weights, environments, database directories or redundant full books into every
entry's packet. Detail completeness concerns the declared review scope, not a wholesale disk dump.

Protected fitting/calibration/final judgments remain separately authorized. Default development
refinement packages include development judgments and an explicit inventory of sealed populations.
If held-out material or feedback is deliberately used for development, mark the affected cohort
as exposed for future assessment purposes and obtain a fresh valid assessment population; do not
rewrite historical passes or silently keep claiming it is unseen. This preserves the review
workflow without turning the reference store into ordinary producer input.

**Delivery evidence:** an external reviewer can follow a correct span through a rejected alias
link, explain a whole-record failure without losing correct values, inspect no-output regions,
reconcile counts across stages and identify what to change next. Humans and AI receive the same
underlying evidence and explicit population limits. No downstream task-performance score is needed.

<a id="O09"></a>
## O09 — Capability-scoped qualification and stronger composite claims

**Proposed; required milestone revision.** Replace the all-five-families release gate with an
explicit manifest of independently assessed structural capabilities. Keep complete-record grades
and their historical numerical targets at their existing scope; they remain informative stronger
claims, rather than the sole definition of progress.

A capability manifest names its operation/version, domain distinctions, source populations,
input/context policies, assessment rubric/frame, actual findings and unresolved limitations.
An assessed term inventory does not imply correct alias attachment. Assessed cell values do not
imply correct header/notes. A source-supported relationship is not scientific truth. Quantified
performance claims require their actual samples and assumptions; an unreviewed capability can
still expose useful attributable proposals with that standing.

Separate preservation, assessment and publication policy. Retention does not grant semantic
authority. Conversely, failure of a whole record must not prevent consumption of an independently
qualified lower-level contribution. Extend common publication with typed operation-specific
eligibility/witnesses where public assertions are appropriate, retaining the existing whole-record
path for its stronger claim. Do not bypass current record admission by changing a private record's
standing, or simply remove every admission check.

Calibration is selected for a declared probabilistic event when data supports it. A deterministic
source-location check, an independent role judgment, a candidate-relative marginal and a calibrated
whole-reading probability are different qualifications. No universal 0.99 threshold or fitted
logistic model is required for every contribution. A graph consistency constraint does not
establish semantic correctness, and semantic correctness in a case does not certify a population.

The revised success account is the structural enrichment produced, its independently supported
distinctions/relationships, its scoped error/omission account and the demonstrated changes on
reviewed cases. Consumer needs prioritize which structures matter; source and operation contracts
determine whether they were represented correctly. Agent-task benchmarks are not release criteria.

<a id="O10"></a>
## O10 — Composition, reuse and preservation through the existing lifecycle

**Proposed; cross-cutting integration.** Keep the existing operation graph, owned readers,
versioned releases, task claims, immutable reports and publication owner. A new enrichment
workflow should compose primitives through their declared products rather than add a parallel
workflow engine, observation database, lease loop or generic solver registry.

Semantic granularity does not prescribe physical granularity. One native call may produce many
typed contributions under one shared computation identity; one task transaction may seal a batch.
One span with several proposals need not copy the raw report or canonical source into each row.
Retain compact shared representations and project/filter before hydration. Actual model, parser,
context, schema and inventory changes invalidate only products whose declared determinants change.
Failed retrieval and consumed counterevidence belong to computation dependencies where they can
change the result, even when they are not positive derivation premises.

The investigation also exposed a practical assessment-access concern: a protected bulk prediction
frame SELECT spent several minutes in source-custody validation before being interrupted. The
bounded comparison instead used an already frozen authorized reference artifact and a narrow
ordinary-reader capture. That is a diagnostic workflow, not permission for production to bypass
protected reference access. For the new evaluator products, prepare/capture the validated source
closure at the owning scope and use set-oriented, selected-column reads for local questions;
preserve authorization and immutable bindings while avoiding repeated full reconstruction per
field or metric. No performance improvement is measured here.

Historical raw responses are immutable evidence. A corrected adapter can interpret the same
returned bytes under a new attributed adapter/operation version when inputs suffice. It must
not invent suppressed candidates, hidden native stages, absent cues or unexecuted contexts.
New producer work is selected only for the unobserved or inadequate question. Structural inspection
and local assessment precede another broad extraction or training attempt.

Original source selections, archived releases, old A/B/C bytes, failed runs and old complete-record
grades remain intact. Changing operation grains or event meanings creates new products and
assessment protocols; it does not migrate an old full-reading label into new truth. Reuse and
paired comparisons require the relevant semantic and physical correspondence, not equal strings
or a renamed record family.

## Proposed rule impacts and change routes

The operator has selected the progressive-enrichment intent. These impacts identify how to
realize it in existing authorities; they do not ask the operator to reapprove that intent.
Accepted ADRs remain immutable. Implementation planning should select coherent successor
decisions and update owning design sections in the same changes, preserving surviving obligations.

| Impact | Required change | Owners and preserved boundary |
|---|---|---|
| RC01 — Milestone qualification | Replace universal five-family accepted-record completion with capability/population qualification; retain stronger record metrics | [ADR-0053](../adr/0053-m1-sol-reference-assessment.md), DESIGN §B5, M1 coordinator/evaluation companion; preserve author profile and historical numerical meanings |
| RC02 — Intermediate semantic products | Declare independently addressable occurrence/type/role/link/qualification/composite outputs and operation contracts | D1/D2/D4; source observation/model compiler plus new typed projections; preserve exact source attribution and raw reports |
| RC03 — Assessment grain | Add operation-specific references/judgments, frames and paired structural diffs | [ADR-0052](../adr/0052-m1-independent-record-references.md), D7, protected evaluator and statistics owner; no reinterpretation of existing record labels |
| RC04 — Public qualification | Admit/expose qualified local contributions independently of complete records | [ADR-0060](../adr/0060-m1-reference-applicability.md), D5/D8; preserve current whole-record admission and sealed custody |
| RC05 — Embeddings before records | Contextual anchored occurrences and target descriptions can be encoded before complete-record acceptance | D4 M04/M14, D3 active physical model, D6 runtime; qualification of claim embeddings remains a different decision |
| RC06 — Link semantics and identity | Represent candidates, scoped link decisions, local senses and comparison relations separately from canonical equivalence | D1/D5, M14 and [ADR-0029](../adr/0029-identity-exclusions-scoped-reference.md); exclusion/anchor invariants survive |
| RC07 — Mathematical queries | Local decision queries and selected composites need not require complete-record events | `record_interpretation` and operation declarations; retain numerical/exactness/dependence limits and explicit non-positive outcomes |
| RC08 — Review/export contracts | Expose typed intermediate products, source-first gaps and complete declared-scope portable evidence | D8, existing captured exports/reader budgets; separately authorize protected judgments, preserve source and stage population distinctions |

The [current M1 plan](../plans/first-production-milestone_2026-11-03.md) remains the owner of
scheduled findings until deliberately revised. This review neither closes its findings nor creates
a competing mutable progress register. Existing design-spike references are mechanism/evidence
leads, not automatic scope or permission to restart them.

## Priorities and integration sequence for subsequent planning

1. **Recover the value already present:** O01/O02/O08 on retained development outputs, including
   no-record groups and exact failure layers. Establish useful inspection/export and the first
   independent local judgments before changing the producer.
2. **Set the capability boundary:** O09 plus the necessary RC01–04/08 decisions, integrated with
   the new typed products. Keep current whole-record consumers functional and old evidence readable.
3. **Add contextual linking:** O05/O06 on one frozen statistics slice and an explicitly bounded
   enterprise glossary/procedure slice when available. Evaluate supplied-reference mentions,
   inventory coverage, equal-budget retrieval and fixed-list selection separately.
4. **Refine interpretation and parsing:** O03/O04 from recurring structural cases, composing rules,
   linguistic annotations, syntax alternatives and bounded coupled decisions. Native inference
   growth, hierarchical models, specialized identity linkage or reranking follow their stated triggers.
5. **Deliver cross-document structural products:** O07 plus the same O02/O08 assessments for
   definition retrieval, clause/workflow comparison and dossiers. Preserve distinctions and exceptions.

These are dependencies and recommended priorities, not a new implementation-plan series or an
instruction to finish one library at a time. Detailed migration packages, dependency pins and
native transitions belong in subsequent plan creation. Retire only superseded active code whose
consumers have migrated; never delete historical plans/evidence or old immutable migrations to
make the new target appear simpler.

## Evidence limits and review completion

This review combines current source/contract inspection, retained development artifacts and
Context7 followed by primary/version-specific library research. It proposes capability and
mechanism choices; it does not claim measured parser improvements, encoder quality, CPU fit,
enterprise performance, statistical adequacy, pgvector activation or implemented new products.
Library examples are not corpus results. The raw-provider/assembly boundaries and existing source
protocols remain observable limits rather than invented causal diagnoses.

An independent focused design assessment checked the draft against the supplied target and
current operation, identity, interpretation and serving owners and reported no material findings.
It did not independently replay the newly captured field comparison or qualify external APIs;
those source/library investigations retain their separate scopes. This was advice within the
functional review, not a new diagnostic or recommendation-audit publication.

Product tests, provider execution, model loading/training, database mutation and full functional
qualification are **not_run** for this documentation engagement. The retained-data capture is a
read-only query; the field comparison is detached. An earlier bulk validation SELECT was interrupted
and rolled back; the evidence account preserves that limit and the corrected strict-JSON decoding
attempt. Focused publication checks for the completed review are reported in the handoff. M1 execution remains stopped. The next authorized
phase can create/revise implementation plans from these opportunities and proposed rule impacts.
