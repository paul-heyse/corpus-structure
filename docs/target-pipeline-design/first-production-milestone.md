# First production milestone

**Proposed · 2026-11-03.** M1 adds a shared CPU semantic assembly path downstream of the existing Docling and Nemotron 3.5 intake. Release five bounded families of qualified source records through existing custody and publication owners. Acceptance means a faithful reading under a released annotation guideline. Scientific truth, causal validity and proof verification are separate tasks. [Milestone proposal](https://app.notion.com/p/40d141b58369818ca7cff992a52c7d6e)

## Products and scope

| Family | Initial supported shape | Attachment and evidence obligations |
| --- | --- | --- |
| Definitions and concepts | Explicit definitions, aliases/abbreviations and stated hierarchy or instance relations | Keep term and defining passage separately anchored. Resolve local sense and scope. Treat proposed global identity or ontology changes as reviewable. |
| Qualified local assertions | Explicit typed relations or predicate/argument frames with recoverable local arguments | Preserve condition, exception, modality, polarity, attribution, quantification and applicable time/scope. A meaning-changing unresolved qualifier prevents unqualified acceptance. |
| Measurements and comparisons | Entity/property/value/unit with a stated value role, comparator, bounds and uncertainty when applicable | Preserve the numeric string, normalized value, role and all conditions. Record unit conversions as deterministic derivations with premises. |
| Table assertions | Tables with recoverable rows, columns, full header paths and note inheritance | Anchor each field to native cells and applicable caption, notes and units. Preserve blank/missing semantics and report ambiguous layouts. |
| Formula and symbol context | Existing formula occurrence linked to explicit local symbol declarations, meanings, assumptions or definition/result text | Keep formula coordinates distinct from nearby prose and respect symbol scope. |

Also emit a source coverage and routing ledger, multi-label content roles, typed mentions and attributes with alternatives, and a source-grounded gap ledger. Preserve unknown, unstated and inapplicable states independently. Simple ordered procedures are shadow evaluation using grouped action/input/output/condition fields. Promotion is conditional on the same family gates and delivery of the five core families. [Milestone products](https://app.notion.com/p/40d141b58369818ca7cff992a52c7d6e) · [GLiNER2.5 deployment](gliner-deployment.md)


## Reviewed target and release population

**Proposed target revision · 2026-11-03.** The [functional review](../functional_reviews/m1-target-design_2026-11-03.md)
owns the reasoning, alternatives and enhancement recommendations. This page owns the complete M1
proposal, with the linked deployment, foundation, mathematics and evaluation pages supplying detail.
The review inspected `b8e1a020`; it does not change accepted architectural authority or active plan
scope. Statistics is the first release population. Engineering examples challenge reusable contracts
but do not establish another released domain. English is the initial language; unsupported languages
and source shapes have explicit coverage dispositions. Published PDF input and selected native
source views remain the boundary; M1 introduces no alternative intake path.

The five families above are required even if their supported subsets differ. A definition may be
accepted without a global ontology merge, and a formula-context record without proving a theorem.
Ordered procedures remain shadow output. Corpus truth estimation, causal discovery, learned
escalation, broad multilingual deployment and general generative extraction are follow-ons.

## Source preparation and routing

1. Consume a **pinned selected view** with source ancestry, projection/recipe digests, recognition health, selection lineage and native item, table and formula addresses. Keep original PDF material, admitted intake and schema-eligible material as separate populations.
2. Extend the existing sentence preparation into one reusable linguistic product containing tokens, sentences, lemmas, POS, morphology and needed dependencies. Retain exact reconstruction, formula/reference atoms, block boundaries and pinned model versions. Use spaCy initially. Stanza is a measured comparison.
3. Construct bounded typed contexts. Local prose uses a sentence or paragraph, neighbors and section ancestry. Definitions preserve term and defining passage. Formula context pairs native formula occurrences with declarations and prose. Table context combines native cells, row keys, header paths, units, captions and notes. Targeted references record the retrieval reason, candidates and all consumed inputs. Every context keeps reversible coordinate maps, including when model input is normalized or a table is serialized.
4. Run a coverage pass on all selected views and record applicability and outcomes, including an empty result. Use a modest high-recall role, anchor and mention schema with structural checks. The focused pass routes compact packs from structure, rules and classification. Table, formula and list cues can independently trigger a pack. Mixed and unknown units receive bounded fallback or explicit pending status. Audit units omitted by routing.
5. Resolve missing roles through bounded context widening, explicit declaration or note retrieval, larger candidate budgets or a measured specialist. Capture each action, its inputs, resource cost and terminal reason.

Use existing sentence and [native frame](../../python/corpus-structure/src/corpus_structure/semantic/proposals.py) preparation as the starting seam. Native frames currently support primary evidence and bounded direct ancestors. Neighbor, table-note and general reference contexts require an explicit extension. [Architecture and contracts](https://app.notion.com/p/40d141b58369819eb958e952d47b0301) · [Sentence preparation](../../python/corpus-structure/src/corpus_structure/ingest/sentences.py)

## Observation and publication contracts

Extend `SourceObservationBatch` and the existing result binding path. Preserve producer and operation versions, checkpoint and tokenizer revision, schema and configuration digests, normalization and context inputs, and consumed ontology/calibration versions. Store raw alternatives with stable IDs, source anchors, score meaning and available suppression reasons. Carry invocation/window and shared upstream dependency groups, feasibility and constraint violations, search limits, truncation/exactness and unresolved reason. Record scope actually inspected and coverage in the observation contract. Keep scheduling, skips and `not_run` in the routing ledger. Measure CPU and wall time, peak memory, batch/window/schema size, candidate counts and cache outcome.

Multi-anchor evidence is a proposed extension. Use named, role-labelled anchor sets with explicit coordinate spaces, including noncontiguous text, native item pointers, cells and formula occurrences. A source occurrence has a different identity from a normalized fact. Mark each field as extracted, normalized or derived and preserve coherent alternatives, calibration status, policy version, derivation lineage and all computation dependencies. Rejected candidates remain inspectable alongside immutable observations. [Observation model](../../python/corpus-structure/src/corpus_structure/model/semantic/observations.yaml) · [Architecture and contracts](https://app.notion.com/p/40d141b58369819eb958e952d47b0301)

The phase-0 policy at the source baseline uses `agent.opus` for claim extraction. Add a CPU policy runnable with general LLM extraction disabled. Reuse the domain-policy and `consolidate_cut` publication boundary. Keep local meanings and qualified source disagreements intact when consolidating occurrences. Apply finite inference over admitted premises with proof witnesses. Review ontology proposals before publishing a new version and replaying affected interpretations. [Phase-0 orchestration](../../python/corpus-structure/src/corpus_structure/orchestrate/phase0.py) · [Statistics policy](../../domains/statistics/policies.yaml)

## Bounded interpretation

Start with value–property–referent–condition, then reuse the contracts for mention identity–type–relation and table header–row identity–cell value–unit–note. Definition and formula records reuse these decisions plus their native source context. Use deterministic joins when keys and premises are established, a fitted independent/stacked baseline for uncertain decisions, and coupled inference where measured gains justify it. GLiNER's local decoder supplies observations and candidates. The outer interpreter owns cross-context source identity, units, qualifiers, scope and whole-record acceptance. [Inference contract](https://app.notion.com/p/40d141b5836981e2bdcac2a511da386c)

Every uncertain decision includes an unresolved alternative and a separate reason such as missing retrieval, conflicting candidates, insufficient context or resource limit. Identity can also resolve to a genuine new/local entity. Record candidate search scope, exclusions and truncation. Apply hard constraints to complete interpretations under established premises. Structural invariants can be hard. Unit/type compatibility is hard only under the meanings selected in the assignment. Typical values and uncertain ontology expectations remain soft or diagnostic.

For a bounded connected component with assignment (z), observations (e) and ontology (O), the proposed conditional model is

```math
P_\theta(z\mid e,O)
= \frac{\exp[\sum_g f_{\theta,g}(z_g,e_g)+\sum_j w_j\psi_j(z_j,O)]\,\mathbf{1}[z\ \text{is feasible}]}{Z_\theta(e,O)}.
```

Evidence potentials group correlated observations. Compatibility potentials connect related decisions. Fit grouped features where supported, or document a conservative feature/representative policy and keep the result provisional. A binary calibrated posterior can supply an LLR by subtracting the matching prior log-odds from the posterior log-odds under matching conditioning assumptions. Candidate-versus-rest scores do not automatically define a coherent multiclass distribution. Shared GLiNER heads, duplicate windows, reused constraints and common OCR errors belong in dependency accounting. The reference prototype's effective-count discount is a heuristic.

Start exact enumeration with a configurable 65,536-state guard plus time and memory limits. Independent components can be solved independently. Over-budget and infeasible results carry explicit dispositions. Approximate splitting and variable elimination require their own justification. Exactness is relative to the declared model and retained candidates. For a whole-record event \(\Phi_r\), sum assignment probabilities over the event rather than multiplying field marginals. Model marginals require held-out evidence to be called calibrated. Keep a small number of coherent alternatives and unresolved mass where the model defines it.

Use proof-bearing deterministic acceptance where applicable and evaluated policy for model-resolved candidates. Under the stated utility assumptions, accepting a record with value \(v_r\) when correct, cost \(c_r\) when wrong and zero utility for abstaining gives threshold \(c_r/(c_r+v_r)\). The illustrative 0.75 is a decision-model example. Select actual thresholds by family with held-out precision/coverage evidence.

### Ambiguous pressure reference

> At a suction pressure of 2 bar, P-101 delivered 120 m³/h; its rated flow was 100 m³/h. Below this pressure, cavitation may occur.

If OCR retains both `2 bar` and `2 h`, resolve the unit, antecedent, value roles and condition scope together. A duration or flow-rate interpretation cannot fill a pressure reference under the specified dimensions. The `bar` reading can satisfy it, and unresolved remains available. Preserve the distinction between delivered and rated flow, and retain **may** and **below this pressure** on the cavitation assertion. The prototype's early hard choice of dimension must be replaced so that a slightly higher raw OCR score for hours cannot eliminate the correct reading before joint interpretation. [Worked inference example](https://app.notion.com/p/40d141b5836981e2bdcac2a511da386c)

### Lineage and corpus support

Derivation lineage tracks premises and rules that establish a result. Computational dependencies include every relevant input to candidate construction and acceptance, including counterevidence and the context consumed by rejected alternatives. Evidence withdrawal recomputes affected components and descendants. Semiring lineage can represent conjunctive and alternative derivations. Probability needs the corresponding event under a probability model.

Keep qualified support/opposition in a ledger with citation groups, source types and known shared origins. Separate author modality, interpretation confidence, source reliability and corpus support. A general mixture likelihood ratio is the ratio of the two mixtures of observation likelihoods, weighted by their respective hypothesis-conditional reading priors. A parser posterior already conditioned on the observation cannot serve as the prior in that mixture. The earlier weighted ratio, uniform correlation discount and latent-truth proposals require separate assumptions and evaluation. Conformal sets, corpus-wide inference, full attribution analysis and learned escalation are later options. [Mathematical assessment](https://app.notion.com/p/40d141b5836981e2bdcac2a511da386c)


## Owned model and operation contracts

**Proposed.** Extend effective domain declarations and their generated boundary/projection products.
The names below describe domain responsibilities, not a new parallel schema registry, service per
concept, or a promise that these types already exist. D1/D2 own meaning, D3 persistence, D4 methods,
D5 interpretation/publication, D6 execution, D7 evaluation and D8 consumers. Use existing release,
operation, invariant, comparison and diagnostic bindings. Schema changes require a new release;
no migration of frozen predecessor observations is implicit.

| Contract | Required meaning and boundary |
| --- | --- |
| Linguistic product | Selected source pin, text/layout recipe, token and sentence positions, available lemma/POS/morphology/dependency annotations, component/model versions and annotation availability. No token's model label overrides its native formula/reference role. |
| Context product | Ordered source pieces, each with its own source view, native address and projection coordinates; explicit synthetic separators; retrieval reason, candidate scope, selection and terminal reason. It may reference neighbors, declarations, captions and notes, not only direct ancestors. |
| Evidence anchor set | Named field/role and one or more located pieces: text span, native item, table cell or formula occurrence, plus coordinate space, source pin and mapping precision. A field can use discontinuous evidence; coarse item grounding must not be relabelled as an exact character span. |
| Candidate observation | Existing producer-bound observation plus typed family payload: candidate/anchor identities, raw field alternatives, score kind, grouping, window, dependency groups, feasible/violation state, examined scope, suppression diagnostics when exposed and search limits. Missing diagnostics are unavailable, not an invented complete lattice. |
| Interpretation component | Explicit decisions and candidate domains including unresolved, evidence and compatibility factors, constraints, source/ontology/policy inputs, search settings, computation dependencies and result status. It is distinct from finite inference over accepted facts. |
| Qualified record occurrence | Family, occurrence identity, role values and their states, evidence per field, original/normalized/derived distinction, coherent interpretation and acceptance policy. One occurrence can yield several linked domain assertions without losing record grouping. |
| Routing and gap records | Operational dispositions and source-grounded omissions, kept separate from what a completed observation actually inspected. A route skipped before invocation cannot claim an empty inspection. |

Use explicit field states: present, unstated, inapplicable and unresolved. Unresolved includes a
reason and available alternatives. Failure and not-run are operation/routing outcomes rather than
substitutes for a field state. A required meaning-changing unresolved role prevents full-record
acceptance. Optional unstated content remains unstated; a decoder's required cardinality cannot
manufacture evidence. Structural mappings and field-state validation reuse production validators;
independent references still determine whether the reading is faithful.

Occurrence identity binds family, selected source, native occurrence/anchor and the versioned
occurrence recipe. Candidate identity additionally distinguishes operation, input, window and
alternative. Fact grouping uses the existing semantic equivalence policy, including qualifications;
it must not erase separate mentions, source occurrences, conditions or provenance origins. Replayed
attempts attach to the same logical observations; attempt IDs and solver-local array indices are
not semantic identities.

### Shared preparation and context selection

Extend the atom-preserving sentence path rather than creating another tokenizer. Its current
`SentenceConfig` excludes the lemmatizer; the richer profile must explicitly enable and version
needed components. Keep the sentence-only profile available to consumers that do not need syntax.
Prepare batches with `Language.pipe`; store the needed annotation columns and shared source
references rather than copying full text into every candidate. A spaCy `Doc` is a local working
representation, not another canonical document.

Use `Matcher`, `PhraseMatcher` and `DependencyMatcher` as candidate/cue mechanisms where useful;
syntax is evidence for attachment, not an unconditional semantic gate. Keep overlapping spans in
span groups when needed rather than forcing them into non-overlapping `Doc.ents`. Lemmas and
normalized matches are indexed aids; evidence continues to cite original source pieces.
See [spaCy §§2–4, 9](../libraries/parsing/spacy.md).

Context construction begins with the smallest coherent source region for the family. Definitions
pair the term with the defining passage; assertions retain their clause and local qualifications;
measurements retain value/property/referent/role and conditions; table contexts retain complete
header paths, row keys and inherited notes; formula contexts retain the native formula occurrence
and separately addressed declaration prose. Textual serialization carries an interval map from
model characters to source pieces. Characters synthesized for headers or separators are marked
synthetic. A match crossing synthetic/source pieces becomes multiple anchors or is refused; a
lossy normalization never receives a fictitious one-to-one reverse map.

Widen in a fixed policy order: local neighbor, enclosing declaration/section, explicitly referenced
note/table/formula, then bounded targeted retrieval. Record unsuccessful retrieval and exclusions
as dependencies where they influence acceptance. Repeated text at different positions remains
distinct. Structural table/formula cues can activate a pack despite uncertain role classification.
Unknown/mixed roles get a bounded broad pass or pending disposition; no silent routing loss.

### Five family assemblers

| Family | Assembly and acceptance rule |
| --- | --- |
| Definition | Join the term occurrence to explicit definition text and scope. Alias/hierarchy candidates remain typed relations; a lexical similarity alone cannot assert identity or a hierarchy edge. Distinguish a new local sense from failed global retrieval. |
| Qualified assertion | Anchor the predicate and each participant, and attach polarity, modality, attribution, conditions, exceptions, quantification and time where applicable. Cue presence without attachment is insufficient. Preserve alternatives when two scopes change meaning. |
| Measurement/comparison | Parse the original number/range and comparator deterministically; retain unit, dimension, reference quantity, role, uncertainty and conditions. Select unit meaning jointly when ambiguous. Conversions/comparisons cite exact operands, numeric policy and conversion rule; no binary float is substituted for an exact source decimal. |
| Table assertion | Assemble by native table/cell identity and header path, not flattened text proximity. Unit/caption/note inheritance is explicit and may be conditional. Blank, dash, unreadable and absent are different source states until a guideline assigns meaning. Spanning/ambiguous layouts remain candidate-only outside the supported subset. |
| Formula/symbol context | Bind the existing formula occurrence to explicitly declared symbols, meanings, domains and assumptions under local scope. Preserve symbol shadowing and multiple occurrences. Recognized LaTeX, parsed expression and source claim of a result remain distinct; no algebraic rewrite proves the source theorem. |

A compact native grouped record can propose these associations; deterministic assembly and outer
interpretation validate them against the same domain contracts. Do not adopt one custom neural
extractor per family when schema packs and shared preparation suffice.

### Interpretation execution and numerics

The baseline is deterministic joins/validation plus an independently evaluated fitted scoring
policy where data support it. Add coupling only for decisions with a real interaction: the three
initial templates are quantity/property/referent/condition, identity/type/relation, and
header/row/cell/unit/note. Definitions and symbol bindings reuse these operations with their
own role and scope definitions. Merely sharing an ontology release does not connect otherwise
independent components; actual decision dependencies determine connectivity.

For bounded enumeration, stream assignment blocks through NumPy operations; reject infeasible
assignments before normalizing. Use SciPy `special.logsumexp` for the log partition and the
log numerator of each whole-record event. If all assignments have zero mass, return infeasible;
never evaluate an undefined normalization as an ordinary empty result. Keep explicit treatment
of nonfinite inputs and numerical failures. The event probability is the sum over all assignments
that realize the complete record; top-k alternatives are a presentation view, not a renormalized
replacement distribution. Omitted mass within the enumerated model can be reported; probability
mass for candidates never generated is unknown. Numerical normalization supplies model
probabilities, not empirical calibration. See [SciPy §12.1](../libraries/scientific_compute/scipy.md).

The 65,536-state guard is an initial enumeration control, not a workload qualification. Keep state,
time, memory and candidate limits distinct. Over-budget components stay unresolved and may request
bounded new evidence; do not silently split dependent variables or replace marginal inference with
MAP. pgmpy discrete factors and exact inference are an alternative when a repeated factorized
workload justifies their preparation and induced intermediate sizes. Promotion requires matching
factor/variable state order, hard-zero semantics, joint record events and numerical behavior against
small independent expectations. No universal probabilistic runtime or approximate inference enters
M1 by default. [Numerical realization and alternatives](mathematics.md#m1-numerical-realization).

Scores from shared GLiNER heads, repeated windows, re-decoding and common recognition inputs are
features of related evidence, not independent votes. Fit grouped features on isolated development
and fitting populations; without sufficient fitting data, use a declared conservative policy and
expose provisional decision status. Typical values and uncertain type expectations remain soft.
Only constraints whose premises hold for the selected assignment may exclude it.

### Execution, publication and consumer journeys

Add an explicit CPU extraction policy to the existing run lifecycle. It schedules typed methods
and observations without fabricating `agent.opus` tasks or relying on a complete agent-mode path.
Method allowlists and terminal routing dispositions enforce the no-general-LLM boundary; reference
and evaluator assistance remain separate, recorded activities. Source preparation can complete
without a released knowledge result. Empty complete family results, failures, unsupported scope
and unrun work retain different dispositions.

Use one resident boundary checkpoint per worker profile and a bounded queue. Start with one CPU
model worker, batching compatible schema/length inputs, and increase workers only after profiling
aggregate memory and threads. Coordinate spaCy, Torch/BLAS and analytical engine capacity together;
a thread bound per library is not an aggregate bound. Reuse existing task fencing, cancellation and scoped resource ownership; implement coordinated
CPU admission and worker supervision. Model execution and uncertain solving run outside publication transactions. Persist
completed immutable observations through existing binding; private record preparation then enters
`consolidate_cut`, where source/release/policy premises are rechecked before atomic publication.
Finite rule closure remains inside its existing governed publication route. No partial component
becomes a default selected result.

A changed schema/checkpoint invalidates dependent extraction; changed grouping policy may reuse
raw observations but recomputes interpretations. A changed context or rejected countercandidate
invalidates dependent acceptance too. Retain the earlier accepted cut for rollback. Cancellation
drains owned work and preserves completed reports; restart repeats the smallest incomplete unit.
Do not add a second cache, lease system or durable service solely for M1.

For joins and audits, use existing owned analytical scopes and typed Arrow batches. Preserve native
addresses, exact numeric representations, qualification/state tags and one-to-many evidence links.
DuckDB handles set joins/aggregation where it avoids repeated Python loops; NumPy/SciPy handle
bounded dense numerical factors. Arrow is interchange, not a second semantic store. Explicitly
complete or abort DuckDB results before another operation, retain input buffers through lazy
consumption and release readers with their scope. Project required columns and stream/spill where
supported; a bounded response alone does not bound candidate preparation or intermediate joins.

The operator journey is: select a pinned source and released CPU policy; inspect family routing
and progress; inspect a candidate or accepted record with each field's evidence, alternatives and
reason; follow its native table/formula/text anchors; inspect gaps; then select a fully published
result through existing policy. CLI and MCP expose the same domain operations and pinned IDs.
Export carries records, evidence links, decision status, source/recipe/release manifest and coverage,
not only accepted triples. Existing exports and `agent_claims` grading require explicit extensions;
current consumer success does not prove this new journey. D8 remains the consumer contract owner.

### Worked contract challenges

| Case | Required target behavior |
| --- | --- |
| Statistics definition: “A random variable is ...”; later reuse of the same term | Keep defined term and passage separately located, create a scoped sense, and avoid an unreviewed global merge. A later occurrence resolves under scope or remains alternative. |
| Pressure example above | Keep bar/hour readings until attachment and dimensions are evaluated together; preserve rated versus delivered values, the antecedent and the modal conditional claim. Never use the initially preferred unit to prune all other meanings. |
| Table with a parent header, blank cell and note “at 20 °C” | Cite full header path and note, retain blank semantics, inherit the condition only over its declared cells. A changed note invalidates affected records. |
| “Let X ...”, formula, followed by a new section reusing X | Cite formula and declaration in distinct spaces; do not merge symbols across a scope boundary by spelling. No proof-verification claim follows. |
| No output or infeasible/limited search | Distinguish inspected-empty, missed route, candidate suppression, infeasible, numerical failure and resource limit. Preserve denominator and candidate diagnostics. |
| Withdraw a rejected alternative; interrupt before publication | Recompute the affected component even if the winning evidence is unchanged; retain prior accepted cut and idempotently resume unfinished work. |

## Delivery and exit evidence

| Package | Deliverable and exit evidence |
| --- | --- |
| WP0 | Freeze the source cut, family guidelines, supported subsets, sample denominators and isolated references and splits. |
| WP1 | Shared linguistic and context products with exact alignment on prose, formulas and tables, stable occurrence identities and replay. |
| WP2 | Qualified GLiNER CPU operations and schema registry with actual CPU runs, reproducible caching and explicit empty/infeasible/truncated/failure cases. |
| WP3 | Five record assemblers with a deterministic baseline and complete located candidates on retained sources. |
| WP4 | Three reusable inference templates with dependency, calibration and acceptance evidence, paired comparisons and invalidation/replay. |
| WP5 | Frozen per-family gates, CPU/memory fit, restart/resume, traceable publication, no general LLM extraction and coverage/gap report. |
| WP6 | Ranked source-grounded gaps and bounded CPU experiments with incremental complete-record results, regression and route/adopt/defer decisions. |

The release manifest states supported languages and source types, per-family subsets, all deployment/schema versions, resource bounds, acceptance policy, calibration standing and unsupported cases. Operational cases include Unicode/repeated strings, nested/long spans, formula atoms, table notes, truncation, qualifier retention, changed inputs, retry/idempotence, interruption/resume and atomic publication. Full M1 requires a released supported subset in each core family. [Delivery plan](https://app.notion.com/p/40d141b58369819eb958e952d47b0301) · [Rollout and evaluation](rollout-and-evaluation.md)
