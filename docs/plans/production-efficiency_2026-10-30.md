# Model-governed production efficiency

**Status:** Planned; authoring complete; production implementation not started · **Created:**2026-10-30.
**Target maturity:** Proposed. This coordinator owns PE-00–PE-12 package state and current disposition
of findings scheduled from the [production-efficiency review](../design_review/reviews/production-efficiency_2026-10-30.md).
Approval to create these documents is not a claim of implementation or measured benefit.

## 1. Basis, purpose and boundaries

Consume review534e956, whose production baseline is7fadeff. Existing semantic-model-pivot source,
selected results and qualification remain at their original owners. No existing plan scope is
rewritten. The new series addresses all production efficiency facets, with greatest depth in
analysis. Audit accounts/premises and testing-code architecture are excluded. No audit refresh
or new diagnostic baseline is a prerequisite to this plan.

The target is one domain model governing analytical intent, available context, dependencies,
outcomes and effects, with efficient operation-shaped physical execution. It replaces repeated
consumer interpretation and preparation, rather than putting wrappers/caches around them. Large
breaking changes are acceptable where they improve that design. Current APIs or algorithms are
not preservation requirements; source fidelity, explicit meaning, evidence, exactness, authority,
consistency and truthful outcomes are.

Evidence: [bounded production observations](../design_review/evidence/2026-10-30_production-efficiency/README.md).
A195-span page took6.40s cold and0.00153s warm; its existing parser memo works. CLI import took1.51s
in one measured process. Instrumented parsing changed a timeout outcome. The historical172s/78-page
observation is an investigative lead, not a production throughput target. No speedup, SLA, memory
capacity or globally optimal design is claimed by these documents.

## 2. Combined target and foundation

Extend existing `MathematicalExpression`/binding definitions, `OperationContract`, result dimensions,
method/report composition, release dependencies and fixed native execution projections. LinkML and
trusted execution definitions own domain-relevant shapes and meaning; generated runtime adapters,
Core rows and native operations consume them. Model-backed requirements must reach actual consumers.
A schema-only declaration does not complete a package.

The shared products are context-authorized analytical inputs; relative syntax/occurrence and lazy
mathematical values; operation-local candidate/comparison indexes; owned publication transport;
and resident or spooled snapshot-qualified analytical inputs. Their names do not require a class,
service or durable artifact for every concept. Libraries own generic execution. Ordinary semantic
variation should become model-derived data/release rows where appropriate, without per-domain DDL.

Preserve separate source occurrence and reusable semantic value identities. Source-local declarations
can precede consolidated entities; inferred scope cannot silently authorize earlier pruning. Missing,
unknown, unsupported, ambiguous, partial and scientifically undecided results retain distinct meanings.
Conditions, interpretation and policy bind reuse. Effects still enforce current native authority,
snapshots and fencing; pure kernels do not pay a database lookup per span merely to consume a contract.

The focused foundation assessment is in [analysis-model-and-contracts](production-efficiency/analysis-model-and-contracts.md).
It identifies actual reuse and missing distinctions. Existing parser caches, spaCy batching, recursive
value closure, native analytical operations, protected publication and explicit ownership stay useful.
Do not add a global cache registry, generic workflow engine or mandatory persisted mega-IR.

## 3. Rule decisions accepted for planning

The operator explicitly approved the authoring plan and its four proposed change envelopes on
2026-10-30. These decisions permit planning the replacements; no accepted ADR is amended here.
PE-00 supplies the required durable decisions/owner changes before dependent implementation.

| Review impact | Accepted planning consequence | Route / boundary |
|---|---|---|
| RC01 | Multiple physical recognizers or structural frontends may serve one authoritative interpretation model; retain source/token fidelity and declare supported semantics. | PE-00/PE-02; identify ADR-0012 clauses requiring a successor. Internal representation changes alone may preserve it. |
| RC02 | Segmentation may change through an explicit method/configuration and release; rendition/anchor identity can intentionally change. | PE-00/PE-05; new declared profile and fresh source processing, never reinterpret old anchors. |
| RC03 | Logical skipped-task identity can depend on source/configuration without rendering a provider packet. | PE-00/PE-10; revise identity/dependency contract, retain skipped logical population/reasons/unknown coverage. |
| RC04 | Analytical capture can be resident or detached spooled under the same semantic contract. | PE-00/PE-01/PE-09; implement the scalable representation, preserving complete spine, exact values, atomic completeness and snapshot custody. |

No approval for a particular unqualified parser, segmenter, approximate proof policy or third-party
model is inferred. Genuine semantic changes must be explicit in the selected profile and decision.
Historical archive/source bytes and recorded meaning remain preserved. No database disposal scope follows.

## 4. Documents, packages and dependency readiness

| Package | Owner document / delivered capability | Required readiness | State |
|---|---|---|---|
| PE-00 | [Model contracts](production-efficiency/analysis-model-and-contracts.md#PE-00): durable authority decisions | Accepted planning envelope and affected current owners | Open |
| PE-01 | [Model contracts](production-efficiency/analysis-model-and-contracts.md#PE-01): compiled context/demand/outcome/dependency and ownership contracts | Relevant PE-00 decisions | Open |
| PE-02 | [Interpretation](production-efficiency/interpretation-and-scientific-analysis.md#PE-02): qualified recognizer/ambiguity decision | Agreed PE-01 semantics; bounded production evidence | Open |
| PE-03 | [Interpretation](production-efficiency/interpretation-and-scientific-analysis.md#PE-03): shared mathematical interpretation and consumer migration | Working PE-01 and selected PE-02 contract | Open |
| PE-04 | [Scientific analysis](production-efficiency/interpretation-and-scientific-analysis.md#PE-04): prepared comparison | PE-01 policy contracts/PE-03 operands; local repetition removal can start earlier | Open |
| PE-05 | [Text/candidates](production-efficiency/text-and-candidate-analysis.md#PE-05): token reuse and explicit segmentation decision | PE-01 context; RC02 before changed segmentation | Open |
| PE-06 | [Text/candidates](production-efficiency/text-and-candidate-analysis.md#PE-06): scope/eligibility indexes | PE-01 authority and required universe | Open |
| PE-07 | [Text/candidates](production-efficiency/text-and-candidate-analysis.md#PE-07): prepared assignment/citation consumers | PE-06; PE-04 for substantive mathematical comparisons | Open |
| PE-08 | [Data execution](production-efficiency/data-execution-and-publication.md#PE-08): one owned transport outside retries where valid | Existing ownership/receipt contract; reconcile with PE-01 | Open |
| PE-09 | [Data execution](production-efficiency/data-execution-and-publication.md#PE-09): resident/spooled capture, trusted builders, graph preparation | PE-01 capture contract, PE-08 ownership, RC04 | Open |
| PE-10 | [Runtime/adoption](production-efficiency/runtime-preparation-and-adoption.md#PE-10): cheap logical scheduling and bulk source context | PE-01 invocation/dependencies; RC03 before identity change | Open |
| PE-11 | [Runtime/adoption](production-efficiency/runtime-preparation-and-adoption.md#PE-11): cheap product opening/startup | Protected finalization/trust and existing explicit lifecycle | Open |
| PE-12 | [Runtime/adoption](production-efficiency/runtime-preparation-and-adoption.md#PE-12): integrated adoption/retirement and evidence | All implemented contracts and migrated required consumers | Open |

A contract agreed for design does not establish working runtime/native enforcement. PE-02/PE-05
investigations can use agreed contracts early. PE-08 and local PE-11 fixes can proceed without
waiting for the whole analysis redesign. Document order is not a global barrier. Settle shared
context/eligibility before independently optimizing consumers into incompatible caches or projections.
The main analysis route is PE-01→PE-02/PE-06→PE-03/PE-04/PE-07; integration joins with data/runtime work.

## 5. Finding disposition and complete review coverage

This table is the one current disposition owner for scheduled review findings. IDs retain their
source meaning; packages are delivery units rather than renamed findings. Closure needs all named
contributors, actual consumer adoption and suitable evidence, not merely a helper or model type.

| Item | Component / structural correction | Disposition · dependency | Closure evidence |
|---|---|---|---|
| F01 | Contextual recognition and ambiguity execution; PE-01–03 | Open · recognizer decision gates downstream migration | Supported interpretation/ambiguity preserved or explicitly versioned; real consumers and production cost route established |
| F02 | One authorized context and prepared mathematical products; PE-01/03 | Open · no circular scope feedback | All source/rule/scientific readers consume the model-derived context and complete dependency keys |
| F03 | Prepared operands and policy-bound scientific comparison; PE-04/07 | Open · no numeric-as-proof substitution | Repeated base/value work removed; evidence tiers/conditions remain correct; comparison measured separately |
| F04 | Shared token preparation and segmentation decision; PE-05 | Open · RC02 before changed anchors | Actual ingest/scope consumers migrated; exact offsets retained or new release declared |
| F05 | Hierarchy/per-symbol scope indexes; PE-06 | Open · authority/tie rules from model | Enclosure/reopen/mention results preserve meaning; repeated flat scans retire |
| F06 | Candidate/eligibility/comparison indexes and native citation processing; PE-04/06/07 | Open · dependent comparisons remain conditional | No hidden scorer wrapper or repeated invariant preparation; ties/cycles/global candidates preserved |
| F07 | Compose owned transport and move stable work outside retry; PE-08 | Open · first ownership copy retained | One freeze/canonicalization, same canonical receipts, correct mutation isolation/replay |
| F08 | Separate logical skips from provider preparation and bulk-load frames; PE-10 | Open · RC03 and source custody | Skips require no provider packet; required logical coverage and effective origin/frame identity remain |
| F09 | Finalized header-first opening and explicit verification; PE-11 | Open · trust-qualified cache only | Warm hit avoids full payload transfer; untrusted/historical/admission verification remains necessary and effective |
| F10 | Cheap command registration and owner-local runtime preparation; PE-11 | Open · no new plugin framework | Real CLI/MCP entry points preserve behavior without importing unused analytical kernels |
| F11 | One capture contract, resident/spooled lowerings; PE-09/12 | Open · RC04 and snapshot ownership | Required larger input can detach before long analytics; complete exact export and cleanup remain |

Additional review obligations are owned explicitly: constant RDF shape preparation/mutable Graph
isolation and trusted CandidateInput builder reuse belong to PE-09; native exact-value normalization
limits belong to PE-08/09; truthful measurement and complete consumer retirement belong to PE-12.
Tokenizers, pylatexenc and GLiNER2 receive explicit candidate/selection dispositions in the owning
plans. No library is mandated merely because it is available. Existing native query/filtering,
matcher, cache, pool and retry strengths are preservation constraints, not automatic rewrite targets.

## 6. Investigation decisions and concrete library realization

PE-02 settles recognition versus expansion cost and the viable parser contract. PE-04 qualifies
whether numerical code generation amortizes its cost. PE-05 settles segmentation semantics and
annotation reuse. PE-07 chooses suitable component assignment, including sparse edge semantics.
PE-09 settles batch normalization, manifests and detached lifetime; both resident/spooled modes are
target scope. Each investigation records alternatives, evidence, selected outcome and blocked
dependents. No unbounded TBD or unqualified permanent fallback completes a finding.

Recognizable APIs, versions, primary references, why they matter and their limits live beside the
packages: Lark typed starts/SPPF visitors and qualified LALR; SymPy targeted operators/prepared values
and conditional `lambdify`; spaCy Doc-aware `nlp.pipe`/component analysis; native RapidFuzz scorers
and eligible bulk operations; SciPy component assignment; Arrow ownership/batches/ParquetWriter;
DuckDB relational/file scans; immutable RDF preparation; Core snapshot/indexed acquisition and
existing native admission. Context7 is the first lookup for consequential integration details,
followed by primary/pinned installed sources. Do not replace these mechanisms with generic prose
such as "use a faster parser" or "batch the pipeline" when planning execution.

## 7. Adoption and completion

Prefer coordinated fresh regeneration where release, segmentation, identity or archived product
contracts change. Do not implement automatic upcasters, dual writers or hot upgrade machinery
without a real consumer requirement. Preserve historical bytes/data/grades and an explicitly
bound read route; never relabel old meanings under the new model. A single current production path
adopts the target; retire superseded context translations, candidate setup, transport rebuilding,
packet identity dependencies and eager import paths with their replacements.

Package acceptance concerns real producer/consumer/native behavior and discriminating independent
cases: same text/different bindings, changed macros and conditions, partial versus undecided results,
assignment ties and cyclic references, skipped scope population, mutable buffers and ambiguous
retries, exact decimal/missingness across capture modes, stale snapshots, and finalized versus
untrusted archives. A generated expected output from the same producer cannot establish its meaning.
This specifies production acceptance; testing-code efficiency/architecture remains separate.

Use focused checks during implementation and coherent type diagnostics before expensive overlapping
qualification. Complete applicable assembled functional/provider/nonfunctional obligations at
PE-12, preserving failed/interrupted receipts and source/context applicability. Lint-only changes
do not invalidate passing typing/tests or mandate repetition. Model declarations, functional
integration, qualification and measured benefit are distinct claims.

Measure production cold/warm/incremental paths where the change claims a benefit, with fixed inputs,
semantic context and relevant environment; account for profiler effects and required stronger work.
No arbitrary speed percentage or172s-derived SLA is imposed. Removing known amplification can be
source-established; a quantitative speed/capacity claim requires actual measurement. A failed
experiment refines the selected design rather than silently removing a finding from scope.

**Series completion:** all adopted obligations have working model-governed consumers, replacement
routes retired, required native/functional/nonfunctional evidence and justified benefit conclusions.
Move enduring knowledge into existing D1–D8 owners through decision work. The coordinator retains
current package/finding status; supporting documents and reviews link here rather than duplicate it.

## 8. Authoring verification and current state

Created from current source/review inspection. No production implementation, runtime benchmark,
product qualification or audit refresh was performed while authoring. Publication checks are
recorded in STATUS; they establish document integrity only. The next execution boundary is PE-00/
PE-01 contract decisions and independent ready local corrections, after authorization to implement
the production series. Prior semantic-pivot qualification is neither revoked nor enlarged here.
