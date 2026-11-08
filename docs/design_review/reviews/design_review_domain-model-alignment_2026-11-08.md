# Domain-model alignment design review

**2026-11-08 · Design/target · Principle focused · FP-04 and A2**

## 1. Decision and scope

**Revise.** The current architecture has an executable domain model. Effective
LinkML declarations, scoped domain functions, immutable products and native
enforcement already govern substantial behavior. The target should extend
those authorities to the decisions that currently escape them. The most
consequential gaps concern source and derivation fidelity, release and target
identity, and the states communicated through operational evidence. Fixing
schemas alone would leave those decisions split across runtime boundaries.

This review consumes audit publication `0cab8033595e004e19387736b0c5ec829652eaf4`
and product source `67cbe680e7ab2b9860576f2ed650d4ff22e0f990`. The intervening
commit changes the audit and handoff only. Uncommitted Chandra and Docling
experiments and unrelated drafts are excluded. The standard is core and
template 3.3, heuristics 1.0, code-intelligence 1.4, and the repository binding.
Test-assessment 1.2 applies to evidence used for production claims.

The functional target is progressive, attributed knowledge from documents
under a declared domain, with useful partial output and typed answers for
operators and agents. The physical premise is the 518-page Grinstead–Snell PDF,
overlapping page and crop scopes, a shared local GPU, a transactional
PostgreSQL installation with purpose roles, and a serialized documentation
release. WCE receipts retain their smaller population. The enterprise examples
in DESIGN §1.3 challenge extension locality and semantic sufficiency. They
supply neither a new delivery requirement nor transfer qualification.
[Audit baseline](../audit/README.md#baseline) · [Functional target](../../design/DESIGN.md#section-1) · [Full-book decision](../../adr/0070-full-book-method-development.md)

## 2. Responsibilities and semantic authority

Treat a context as an owner of a specific meaning with explicit translations
to its consumers. The same occurrence can have a storage key, a representation
address, a producing identity and several semantic readings. Each answers a
different question. An operation contract states applicability, input and
result meanings, dependencies, valid outcomes and effects. It may be realized
by an ordinary domain function or a native operation. The repository already
uses both.

| Context and owner | Owned distinctions and intended dependency direction |
|---|---|
| Domain pack and release compilation (D1/D2) | Effective terms, fields, role and vocabulary subsets, scoped relation identity, operation bindings and allowable representations. LinkML inputs and domain functions supply the meaning. Generated types, boundary adapters and native shapes consume it. |
| Source acquisition and publication (D3/D4) | Original artifact, physical page, crop, positioned item, organized document, canonical view and exact projection binding. Provider results cite their recipe and source. Selected structure and candidate visual evidence have distinct publication authority. |
| Contribution, interpretation and consolidation (D4/D5) | Methods establish observations, candidates and attributed derivations. A released or scoped operation owns selection, numeric semantics or rule interpretation. Consolidation and protected eligibility govern committed assertions and scientific standing. |
| Execution, policies and intervention (D6/D8) | Runs, task and attempt identity, preparation and claim custody, outcome, readiness, effects and budgets. The runtime binds released operations to capabilities. Orchestration composes them, and agents act through scoped packets and queue authority. |
| Evaluation and public eligibility (D5/D7) | Source-first opportunities, output-first products, applicability and independent witnesses have separate populations and lineage. Consumer views can report an assessment without granting the producer its own public eligibility. |
| Reader, CLI, MCP and detached delivery (D8) | Requests bind a snapshot, scope, capability and work bounds. Views preserve identity, standing, evidence and coverage. Transport formats compose these contracts, and detached verification declares which guarantees it actually reproduces. |
| Model change and operational evidence (D2/D3/D8) | Reviewed release, physical descriptor, approved candidate, acquired database, invocation and artifact custody are separate identities. Phase, effect outcome and knowledge of cleanup remain independently observable. |
| Documentation publication | Authored meaning stays with source and evidence owners. The checked Pages projection binds a source revision and publishable selections. Deployment uses separate permissions and the serialized operator route. |

### Fact and fidelity map

| Fact or claim | Required provenance and limit |
|---|---|
| PDF geometry and recognized text | Exact source, page or crop, provider and retained response. A parser's candidate remains attributed. The selected incumbent has a distinct authorized derivation. |
| Typed link or definition component | Exact participating spans and roles, scoped relationship identity, named derivation basis and decision context. Located spans alone establish quotation. A supported relation needs the basis it claims. |
| Finite interpretation or fitted output | Frozen request, policy, actual computation and support, numeric standing and evaluation population. Candidate-relative mass and fitted estimates have separate meanings. |
| Dossier facet or public assertion | Root, member interpretation, applicability, qualified identity and exact independent evidence required by the admission policy. A summary or match does not increase source coverage. |
| Served and operational evidence | Exact release, product and evidence pins where relevant. Deployment receipts identify the acquired target and settled effects. Report outcome and custody support different statements. |

The model-to-behavior pass starts at `model/semantic/contracts.yaml`,
`semantic/contracts.py` and `semantic/prepare.py`. The inverse pass starts
at the executing routes and follows effects and answers back to these and
other owners. The independent principal reviewer (`review`) assessed the assembled target.
The read-only `definitions` and `routes` contributors supplied the two
evidence routes. The coordinator checked the decisive sources and integrated
the report.
The responsibility and scenario sections reconcile their material
intersections. Inspection sampled materially distinct contract routes
within each family, including both the ordinary completed-result reader
and the agent queue. It did not trace every operation, field, migration
body, installed ACL, external consumer or legacy artifact. Rust is a
starter crate and the supported native PDF boundary has its own custody.
The audit's serialized Pages scope stays applicable. No product code
acquired meaning from an ordinary docs build in the inspected path.

## 3. Contracts, constraints and testing boundaries

Designated constructors or admission points must establish invariants before
publishing products that rely on them. Structural schemas establish shape.
For example, object-field positions, membership of a witnessed event and
whether two located spans have the claimed relationship require contextual
checks. A byte hash establishes custody. The invariants it protects still
need a semantic owner. Verify this distinction with independently specified
counterexamples, including cases whose digests are valid.

For each operation, bind an applicability and dependency scope before
execution. Require explicit distinctions between refused, failed, partial,
unavailable, complete and empty wherever a caller can act differently.
Compare a local domain predicate, native enforcement using the same scoped
meaning and independent verification of a recorded product. Require an
explicit boundary where a verifier intentionally establishes stronger
assurance than ordinary admission.

## 4. Composition and execution

| Operation or projection | Input universe, resulting claim and physical route |
|---|---|
| PDF view and visual capture | One authenticated document and a declared scope. View membership and physical transforms belong to their released recipes. Share acquisition and verification where source and artifact custody permits. Keep recognition, mapping, publishing and their recovery independently attributable. |
| Candidate selection and inference | Bind the actual inspected source population and compatible endpoint kinds before applying policy. Source-side omissions and output-side mistakes use separate populations. Store direct evidence and selected decisions. Derive bounded traversals or views under their declared direction, multiplicity and completeness. |
| Local table inference and fitting | Prepare the source-conditioned request once per relevant scope. Keep solver work outside the transaction. Admission checks enough structure, provenance and result consistency to support the result's advertised standing. Detached numerical replay can be stronger. |
| Exact Reader and exports | Bind to the actual product and immutable evidence closure. Apply selector and continuation within declared snapshot and query semantics. Budget examined rows and bytes, including locator and custody work, separately from the response size. |
| Release and deployment | Prepare deterministic artifacts from frozen determinants. Verify the exact acquired target against a trusted descriptor for its revision. Keep local authoring, registration, database effects and selection separate. |
| Result custody and recovery | Lease managed artifacts, publish immutable roles and preserve actual effect progress. Retention records outcome and custody separately and carries the context needed after GC. |

## 5. Change and failure scenarios

For the existing contextual-link journey, the qualified projection keeps the
exact source scope and selected endpoint. The selector checks candidate
provenance, endpoints and exclusion context. The completed-result Reader
binds its query and continuation to the producing release and snapshot.
The CLI and detached export consume that binding. Inverse inspection also
traced MCP project/run selection and leased-task completion. The project
queue's implicit newest-run selection has a stable order and an explicit
run override. The inspected evidence raises a discoverability question,
with no established authority split in that route
(`semantic/contextual_links.py:219–303`; `serve/journey.py:69–95,149–235`;
`cli/export.py:34–74`; `intervene/semantic.py:423–450`;
`semantic/sql/native_task_completion.sql:8–39,53–90`).

- **New domain meaning.** Trace a qualified ownership relation between distinct
  same-name organizations, and a duty with a scoped exception and a compound
  condition, through declaration, construction, validity, identity, admission,
  query and assessment. Inspect an attributed quantity with basis, unit and
  note. A new predicate or qualifier should change its pack and any genuinely
  new domain behavior. Shared consumers should use released roles and
  applicability instead of special-casing names. The toy pack can exercise
  scoped conditions and quantities. A complete non-statistics journey remains
  an evidence question. Pack proposal ingress derives its enums from the
  selected release and validates endpoint ranges. Identity resolution preserves
  ambiguous anchors and refuses mandatory-key merges that violate a scoped
  exclusion. This supports extending existing categories. It does not show that
  a new accepted unit or interpretation profile has a scientific implementation
  (`semantic/proposals.py:36–121,589–669`;
  `semantic/domain_operations.py:1217–1314`;
  `semantic/analysis_contracts.py:111–163`).
- **New composition.** Add a second source-local readable formula witness and
  combine it with a view that already serves the first. Exact occurrence
  lookup must preserve both witnesses, original spelling and versioned meaning.
  Rebuilding a current product from authenticated sources and reading a
  supported retained product have different compatibility needs.
- **Mechanism substitution.** Swap a compatible mapper or provider under
  explicit realization bindings. If only mapping changes, the producing raw
  response remains meaningful and reusable when its actual determinants match.
  New observation semantics require a new binding. The existing candidate
  route and protected incumbent illustrate the distinction.
- **Failure and growth.** Resume a group after inference settles and mapping
  fails, then exercise two scopes on the same page. Read a small typed result
  from a near-limit mapped artifact, and distinguish negative routing from
  incomplete assessment. On the operations side, register a successor while
  an older target remains bound and recover a receipt after its candidate is
  collected. Work and effects stay proportional to the requested operation
  and durable state.

## 6. Correctness and fidelity gates

These verdicts concern the inspected architecture. The recommended changes
are **Proposed**. They require their own closure evidence before acceptance.

| Gate | Verdict and decisive scope |
|---|---|
| G1 Authority | **Fail.** Acquired deployment and checkout head can disagree on descriptor authority. Preparation reads installed physical context outside release identity. DA-063/067. |
| G2 Semantic fidelity | **Fail.** Report structure, derivation basis, operational refusal and cleanup state can be lost or overclaimed. DA-059/060/062/065. |
| G3 Validity | **Fail.** A completed result can violate cross-field numeric consistency, malformed reports can cross native admission, and a source view can omit text it promises to project. DA-056/062 and F02. |
| G4 Hidden behavior | **Fail.** The installed physical profile changes prepared output under the same declared determinants. DA-067. |
| G5 Consistency and recovery | **Fail.** A retained record can describe completion while cleanup custody is unresolved. A migration can commit before a wrong-head archive refusal, and dispatch can lose its original routing decision during recovery. DA-060/063 and F01. Native claim and snapshot fences remain effective in the inspected paths. |
| G6 Transformation and reuse | **Fail.** The archived read can lose a formula witness after installation changes, and native and detached report acceptance disagree. DA-061/062/067. |
| G7 Truthful capability claims | **Fail.** Routing can describe unexamined cues as a skip. Routine dispatch cannot reconstruct that decision later. Typed access can refuse a mapped artifact permitted by its own producer. DA-064/066 and F01. |
| G8 Library leverage | **Pass for the compared core mechanisms.** Released structural schemas, domain functions and native custody already compose. Broader generic machinery has no demonstrated advantage for these corrections. Gaps in implementation and whole-operation fit remain under their own judgments. |
| CI-G1 Typed and attributed facts | **Fail.** A private derived claim can cite an unauthenticated basis, and incomplete cue inspection can look negative. DA-064/065. |
| CI-G2 Evidence closure | **Fail.** A located component can claim a derivation whose evidence it never bound, and visual dispatch cannot explain its nomination from retained evidence. A frame can repeat incomplete source-view text as exact. DA-065 and F01/F02. |
| CI-G3 Evaluation independence | **Unresolved for the enclosing scope.** Inspected WCE and progressive admission paths separate production inputs, independently authored cases and public eligibility. Source inspection did not settle reference reachability across every evaluation family. |

## 7. Corrections and applicability

All numbered audit references below refer to publication `0cab80335`.
Corrections name a target owner and a closure condition. The execution
state remains with the linked plan where one already owns the obligation.

### Govern semantic values, numerical results and derivation at their admission boundaries

**DA-062.** Give the source-value codec one contract for the encoded
sequence, including contiguous positions, unique names and recursive
validity. The native decoder must reject before it discards the position
field or aggregates by name. Python and PostgreSQL may implement that
predicate differently as long as both consume or realize the same contract.
Keep generic JSON conversion separate from this encoded value. A
mechanically produced native predicate is preferable if the chosen schema
representation can express the recursive invariant faithfully. A local
native function is sufficient otherwise. Remove paths that normalize
malformed input before authenticating it. Closure is rejection of a
resealed position gap or repeated field name in native, ordinary and
detached routes, plus lossless valid nested decoding.
[DA-062](../audit/semantic-model-and-authority.md#da-062)

**DA-056.** The interpretation owner defines event membership, exact-support
claims, numeric tolerance and the relationship between reported event
probabilities and displayed assignments. At admission, check that the
reported event mass lies between the displayed member mass and that mass
plus the undisplayed mass, within the declared tolerance. On fully
displayed support those bounds coincide. Apply the same rule to requested
marginals. Distinguish independent
request reconstruction, local result consistency and full numerical
verification in the product's assurance. Re-running the solver in the
publication transaction would increase the transaction's work while
duplicating detached verification. A result with a valid digest and
contradictory support must refuse. Legitimately bounded top-k, unavailable
and resource-limited outputs must retain their semantics. Test against
independently chosen probabilities and exercise the detached replay.
[DA-056](../audit/witnessed-enrichment.md#DA-056) ·
[Finite interpretation owner](../../plans/next-corpus-enrichment/finite-interpretation.md)

**DA-065.** Resolve and authenticate a witness for each claimed derivation
basis. The definition component owner specifies the required input
relation or geometry, source scope and resulting attachment. Admission
resolves the exact scoped witness and checks applicability before accepting
the basis. Detached verification checks the same meaning from the portable
dependencies. An ordinary producer lacking the required witness may retain
a weaker attributed candidate with its actual standing. It cannot issue
the stronger basis. Hashes and verified text are necessary custody
conditions. Independent public eligibility is a separate decision. Close
with genuine spans and a resealed false basis, and positive controls for
each qualified basis plus the existing independently witnessed public
case. Prefer binding an existing exact cue decision over recreating the
full extraction pipeline in native or detached code.
[DA-065](../audit/semantic-model-and-authority.md#da-065)

**DA-055 and DA-057.** Retain the corrected meanings and their evidence
limits. Table interpretation supports co-applicable note and unit edges
and separate header levels. Dossier identity and output retain predecessor
interpretation and applicability. Preserve those cases as regression
controls across the correction above. The earlier WCE band-3 reconstruction
obligation remains with WCE-R18. Apply the same request-versus-result
assurance distinction there, or retire the earlier route through an
explicit current-contract decision if its active use ends.
[WCE reconciliation](../audit/witnessed-enrichment.md#reconciliation-at-the-november-8-baseline) ·
[WCE owner](../../plans/witnessed-corpus-enrichment_2026-11-05.md#repair-disposition--2026-11-07)

### Separate a visual observation from the work and views built from it

**DA-061.** Make the released section-text policy consume a collection of
qualified readable-original witnesses. A witness binds an exact authenticated
occurrence, original spelling and admitted scope. The integrated product
digest remains delivery and provenance context. A change elsewhere in the
product should leave the witness usable only when equivalence of its actual
premises is established. Use the archived policy bytes for supported reads,
or an explicitly versioned projection that carries the readable decision.
Remove comparison with the ambient installed recipe from the ordinary
historical Reader decision. Keep raw recognized text and verified readable
text separate. Closure adds two independent witnesses, changes unrelated
selected content, and reads the first v9 product after installing a new
recipe. A changed spelling or occurrence must not inherit the witness.
This preserves explicitly supported archived PDF products within the
current-only WCE policy.
[DA-061](../audit/served-claims.md#da-061) ·
[Current-only boundary](../../adr/0067-witnessed-current-only-cutover.md)

**DA-064.** Model cue availability separately from positive, negative and
inconclusive cue results. The routing owner declares required cue coverage
for a negative disposition. Acquisition and parsing supply assessed,
unsupported or missing inputs with provenance. A strong positive cue can
still nominate a page while other cues are unresolved. The CLI and study
can see why. Preserve independently verified blanks as their own
disposition. Close by varying one missing or oversized crop artifact under
otherwise identical A/B/C inputs. Retain the known held-out misses at their
actual evidence strength.
[DA-064](../audit/served-claims.md#da-064)

**DA-058.** Resolve durable group and member settlement before preparing
unsettled work. Reuse the singleton's exact raw-response recovery for an
already settled inference. Share authentication and page preparation within
one useful operation lifetime, keyed on actual source, scope and recipe
determinants. Keep recognition, mapping and publication recovery distinct.
At native settlement, bind the existing authenticated original and exact
structural dependency under attempt custody. Remove the full original
re-upload for each derivative once the native reference route preserves
that custody. The group remains the GPU and cancellation boundary.
Closure shows inference-only resume without render or checkpoint
reverification, safe reuse for a page and crop, exact source binding at
native settlement and a bounded GPU lifetime across interruption and cancellation.
[DA-058](../audit/execution-fit.md#da-058)

**DA-066.** Select indexed, scoped access to the mapped candidate locator and
bounded bodies. Reuse the native PDF access patterns where they preserve the
mapped candidate's own identity and multiplicity. A compact sidecar index
that supports bounded decoding is a viable alternative if it can bind the
same immutable artifact and avoid full materialization. Keep raw bytes
available through their own route. A lower artifact cap alone would make
the producer and Reader limits consistent at the cost of discarding valid
evidence. Close with exact item, cell and continuation reads near the
admitted cap, including budget refusal when a requested result genuinely
exceeds its allowance.
[DA-066](../audit/served-claims.md#da-066) ·
[Visual execution owner](../../plans/chandra-2-post-nemotron_2026-11-08.md#repaired-comparator-shadow-execution)

<a id="F01"></a>

### F01 — Visual dispatch loses the nomination that selected its work

**Implemented source inspected.** FP-04/05/06, DP-05/08/18/21,
CI-01/04/09/11. The ordinary dispatch command computes routes with the
installed router and emits its report after dispatch. A grouped run
retains the selected scopes, execution context and recovery key. It
does not retain the routing policy, considered cue population, coverage
or reasons. An interruption can leave native work without the report.
After a policy change, recomputing against the same source can answer a
different question from the original nomination. Exact result custody
and the separately frozen research study retain useful evidence at
their own boundaries
(`cli/visual_route.py:71–96`; `semantic/visual_dispatch.py:116–157`;
`semantic/visual_requests.py:920–926`).
[Research freeze](../evidence/2026-11-08_chandra-execution/freeze_book_shadow.py)

**Proposed.** Have the routing owner persist the exact policy and source/cut
pins, considered scope, per-cue coverage and resulting decisions before
dispatch. Retain the minimum authoritative decision in the native run’s versioned
inputs, linked from its group members. Native work outlives the managed
invocation. A managed report can project the same decision and effect
progress for by-ID inspection. The inference key contains
its actual inference determinants. An unchanged request can reuse its
result when routing reasons or policy change. An interrupted dispatch can
resume from its original decisions. Close with a policy-only change,
interrupted dispatch and stable raw reuse. Confirm that historical and
new reasons remain distinguishable. Coordinate with DA-064 and the
existing Chandra campaign owner.
[Chandra campaign owner](../../plans/chandra-2-post-nemotron_2026-11-08.md#repaired-comparator-shadow-execution)

<a id="F02"></a>

### F02 — Source-view admission can certify exact pieces with incomplete text

**Implemented source inspected.** FP-04/05, DP-03/08/21, CI-02/04/11.
The released Python projector visits ordinary text nodes and includes
their nonempty text. Native publication verifies exact selected item
membership and order, then authenticates the spelling and extent of each
submitted piece. Captions have an additional correspondence check. The
ordinary-text guard does not compare the expected ordered field inventory
with the submitted pieces. A first publication for a section without a
caption can omit a nonempty prose item from the text, retain the same item
inventory, and recompute the projection digest and offsets. Downstream
frame validation then treats the retained text as its source. Immutable
replay protects against later mutation. These observations establish a
source-level admission counterexample. No malformed production row or
executed native submission was observed
(`ingest/pdf_hierarchy.py:479–506`; `semantic/sql/source_views.sql:124–156,163–197,231–246,301–335`).

**Proposed.** Give the section projection owner an exact ordered inventory
of field addresses derived from selected source and released policy.
Compare it before accepting text pieces and authenticate the supplied
bytes against those addresses. Account for authorized exclusions, rich
cells, formulas, caption placement and separators. Derive or share the
selector semantics so that a new policy does not create an independently
maintained native interpretation. Compare a compact authoritative
address sequence to full native text reconstruction. Prefer the address
check because it protects coverage and multiplicity without a second
text product. Close with omitted and repeated ordinary prose, authorized
exclusion and the current caption and formula controls. Source search,
packets and downstream interpretations should bind the same projection.
[PDF projection ownership](../../design/DESIGN.md#section-b5) ·
[NCE source-view controls](../../plans/next-corpus-enrichment_2026-11-07.md#selected-execution--2026-11-07)

### Make operation receipts durable statements about outcomes and custody

**DA-059 and DA-060.** Put a typed operational outcome in the managed
result at the operation boundary. Preserve the safe refusal reason, known
effect progress and exact acquired target and predecessor when relevant.
Immediate rendering and later read-by-ID consume that same record.
Separately model whether artifact custody and cleanup are established.
An artifact can be useful to diagnose a failure while cleanup remains
unresolved. Retention must either refuse promotion as settled evidence or
preserve the explicitly unresolved state in an allowed diagnostic artifact.
A lease and artifact hash continue to prove ownership and bytes. A
deployment receipt stays interpretable after a candidate expires.

Reuse the managed result owner and its atomic records. Storing stderr or
indefinitely holding all candidate artifacts would couple interpretation to
transport or retention. Close with pre-write refusal, known partial effects,
a completed deployment after candidate expiry and an unsettled review
selection. Verify that immediate, by-ID and retained forms make consistent
claims and never misstate cleanup.
[DA-059](../audit/boundaries-and-composition.md#da-059) ·
[DA-060](../audit/boundaries-and-composition.md#da-060) ·
[CLI custody owner](../../plans/cli-operations_2026-11-07.md#execution-disposition--2026-11-07)

### Bind release products and native admission to their actual determinants

**DA-067.** Derive projection analysis from explicitly retained physical
inputs and a pinned compiler context. Compile the metadata for those
inputs using the existing closed-source `SchemaView` and
`compile_metadata` route. Distinguish pure projection preparation from
the executable-installation compatibility check currently inside
`prepare_projection` (`schema/model_change.py:224–251`;
`semantic/companion_projection.py:525–535`). Otherwise record a deterministic unsupported result
under an explicitly bound capability determinant. The same release
identity must imply the same required prepared products. Validate candidate
versus preview at that boundary, including the reviewed product digest if
the contract includes it. Ordinary archived reads may use stored bytes.
Full rederivation must select the recorded context or refuse its unsupported
compiler explicitly. Remove the ambient-profile branch. Close by preparing
the same proposed inputs in processes on opposite sides of apply and
rederiving an archived release under its declared context.
[DA-067](../audit/native-integrity.md#da-067)

**DA-063.** Verify the acquired target against the trusted descriptor for
its actual bound revision, resolved from the approved migration or admitted
descriptor provenance. Bind both native body and ACL expectations and
the selected-fact view expectation to that revision. The latter also
currently defaults to installed metadata
(`semantic/execution_admission.py:121–136`;
`semantic/native_products.py:25–43`). Perform the appropriate compatibility check before
the first durable effect. After migration, check the reached revision,
descriptor and purpose roles before archive, admission or activation.
The effect report identifies the verified target, rather than substituting
a value from local model sources. Retain checkout-head checks for authoring
a successor. They answer a different question. A global latest-only
deployment requirement would remove valid existing target distinctions.
Close by registering a successor and checking an older bound database,
then applying an approved non-head candidate where the supported route
allows it. An incompatible target must refuse before durable migration.
[DA-063](../audit/native-integrity.md#da-063) ·
[Deployment authority](../../adr/0069-cli-operations-custody.md)

### Inherited questions and historical corrections

| Audit scope | Review disposition |
|---|---|
| DA-004 and DA-012 | Preserve the typed batch and released operation/vocabulary routes in their inspected scope. DA-062 supplies a concrete representation mismatch. Apply the codec correction there. Reopen the earlier batch conversion only for a concrete lost distinction or repeated independent decision. |
| DA-027 | Use DA-056/062/065 to correct actual enforcement mismatches. Establish which invariants each operation assumes and where the released implementation establishes them. Wider body correspondence remains unresolved where there is no source or discriminating evidence. |
| DA-032 | Existing release/runtime/deployment history has distinct owners. The missing operational receipt facts need DA-059/063. Require an additional per-semantic-result deployment pin only for a consumer that cannot recover material provenance from existing exact lineage. |
| DA-033 | Preserve cumulative assurance where it protects actual trust and cross-row invariants. Examine repeated work by invariant and lifecycle boundary. DA-058 identifies a concrete redundant crossing, while a general incremental substitute for native admission still needs a preservation argument and a failure case. |
| DA-046 and DA-048 | Keep statistical rules in scoped packs or dedicated domain functions and shared numeric mechanics in reusable code. A second pack is a transfer case. Concurrent multi-pack execution or new production-domain qualification needs its own supported product scenario. |
| Other DA-001–054 identities | Consume the prior item-by-item correspondence at its original scope, retaining the audit's later corrections and qualifications. No new evidence in this review reopens those historical manifestations as a group. Existing plan owners retain their obligations, including any whose closure has wider criteria than the historical example. |

The prior correspondence supplies all 54 earlier identities in conjunction
with the consumed audit's DA-054 entry. The live and qualified entries above
plus DA-055–067 account for the newer audit. Retained historical dispositions
are not fresh verification.
[Prior correspondence](../../plans/audit-closure_2026-11-03.md#7-audit-correspondence-without-disposition-transfer) ·
[DA-054](../audit/execution-fit.md#da-054) ·
[Phase 0 finding owner](../../plans/phase-0_2026-10-28.md#11-findings-disposition)

## 8. Library fit and total complexity

Effective LinkML slots and the existing compiled boundary are suitable for
structural contracts, role sets and generated representations. Keep
contextual invariants as owned executable predicates when generation would
obscure or weaken them. Existing Pydantic adapters and model validators
support typed ingress. They do not establish invariants at the independent
native write boundary. PostgreSQL constraints, scoped indexes, joins and
transaction fences fit source custody, exact target verification and
bounded candidate access. Retain Alembic's registered migration chain and
the exact deployed descriptor instead of adding another migration
authority. Docling and Arrow can provide retained provider and physical
representations with explicit fidelity translation. Neither establishes the
meaning of a public claim.

Compare complete operations. A candidate index pays publication and storage
cost once and permits selective reads, while a whole-artifact scan repeats
per continuation. Whole solver replay gives stronger assurance but belongs
in detached verification unless a particular published standing requires it.
Derived mechanical forms can share one authority without forcing a
transaction, service, table or task per semantic kind. No dependency
addition is recommended on the inspected evidence.
[LinkML capability overview](../../libraries/data_model/linkml.md) ·
[Pydantic capability overview](../../libraries/data_model/pydantic.md) ·
[Efficiency heuristics](../design_principles/core/efficient-architecture-heuristics.md)

## 9. Architecture alternatives

| Alternative | Judgment |
|---|---|
| Preserve current seams and add local guards | A small guard can close a local validity gap. It cannot fix unchanged release identities, ambient archive behavior or copies of outcome meaning. Use this option only where the current owner already has the necessary determinants and consumers. |
| Make existing owners govern each material boundary | **Recommended.** Add explicit witness, outcome or compatibility facts where consumers need them. Derive representations and bind exact authority at native admission, serving and recovery. Existing operators and algorithms keep their roles. A narrow change in meaning propagates through the relevant contract and generated forms. |
| Centralize all domain behavior in a new interpreter or ontology | The scoped meanings and current mechanisms differ. Moving them into one runtime would introduce a second model migration and reduce native optimizer and constraint visibility without resolving the need for independent evidence. Keep this alternative unselected. |

## 10. Verification and uncertainty

Use the closure cases in section 7 as future controls. Keep expected identity,
source truth, eligibility, mass and recovery state independent of the
production derivation. Reuse retained WCE repair receipts, p416 exact
source and candidate journeys, and bound deployment controls at their
original source and scope. Existing one-process preview or head-only
deployment fixtures do not discriminate DA-063/067.

This review uses source inspection and retained evidence. New product tests,
provider or GPU runs, live fault injection, database qualification and
measurements were **not_run**. Source evidence establishes the named
mechanisms and counterexamples. It does not establish runtime incidence,
full reference independence across all evaluation families, or end-to-end
generalization to an unseen domain. Resolve the enclosing CI-G3 verdict by
tracing the role, allowed inputs and dependency custody of the source-first,
output-first, fitting and research-overlay entry points. In particular, show
that a production run and its preparation cannot acquire a protected reference
through configuration or replay, while an explicitly labeled research run
preserves its actual exposure. Use a protected reference access refusal and
a held-out control if source inspection leaves those claims open. For a
production transfer claim, independently expected ownership, exception,
quantity and identity cases must survive compile, admission and delivery under
a second pack. The current statistics workload retains its own criteria.

## 11. Authority changes and disposition

No binding rule changes are required by the selected corrections. §B1–§B6
already distinguish occurrence, semantic fact, operational effects and
versioned interpretation. Keep PostgreSQL transactional authority, the
released semantic contract, current-only semantic execution and protected
candidate standing. Update the owning design sections alongside any accepted
implementation. The following are distinct subsequent decisions.

| Decision boundary | Route |
|---|---|
| Current-only migration and retained PDF reads | Preserve the explicitly supported archived PDF products and their provenance. Faithfully migrate sufficient derived data. Regenerate from retained sources when the required witness or meaning was never recorded. Keep unsupported historical behavior explicit. Any expansion into old semantic executors needs a separate authority decision. |
| Native and operational changes | Extend or supersede a physical revision forward with reviewed, revision-specific checks. Version any externally visible receipt or result change. Prior receipts with missing custody or target facts retain an explicit unknown. |
| Chandra promotion or automatic default dispatch | Keep the recommended routing, access and retry corrections within candidate-only authority. Promoting a new provider into selected structure or changing the default would require a separately authorized change under §B4–§B6 and independent qualification. |
| Scheduled findings | WCE-R18 and the original repair obligations stay with WCE. Use the NCE, Chandra and CLI owners where they already own the behavior. Route new unscheduled findings through plan creation and keep stable review and audit anchors. |

[Current-only decision](../../adr/0067-witnessed-current-only-cutover.md) ·
[Operations decision](../../adr/0069-cli-operations-custody.md) ·
[Disposition binding](../design_principles/binding/corpus-structure.md#4-where-findings-land)

## 12. Architectural judgment and priorities

| Judgment | Verdict | Scenario evidence |
|---|---|---|
| A1 Localize change | **Violated.** | A successor registration changes admission of a separately bound database. Adding a readable witness can require global policy and consumer changes. |
| A2 Encode domain meaning explicitly | **Violated.** | Codec validity, joint consistency, derivation basis, assessed routing scope and cleanup state are meaningful distinctions that do not govern every relevant accepting or serving boundary. |
| A3 Extend through composition | **Violated.** | Preview and archive cannot compose the same explicit inputs into the same artifact across installed profiles. Reader and admission also disagree on encoded validity. Existing released operation dispatch and exact Reader binding show where composition already works. |
| A4 Fit execution to workload | **Violated.** | Group recovery repeats full-input work at a settled boundary. A near-limit mapped artifact can defeat a narrow request even with the largest supported work budget. Wider admission and high-degree traversal costs remain separate evidence questions. |

FP-01 and FP-02 fail at the release and deployment authority seams. FP-03
fails where recovery and serving bypass reusable outcomes or reconstruct
the wrong context. FP-04 and FP-05 fail on the evidenced meaning and validity
gaps. FP-06 fails where a caller needs the installed profile or initial
stdout to interpret a pinned result. FP-07 fails on the visual workloads
above. The corresponding DP and CI judgments follow the scoped evidence
and gate rows. Positive mechanisms in sections 2–5 are preservation
requirements rather than an aggregate pass.

**Overall decision · Revise.** The enclosing architecture needs revision.
The proposed direction is to make existing scoped authorities govern these
boundaries and to add only the missing distinctions that their consumers
need. Acceptance requires demonstrated closure of the in-scope MUST gaps
and independently supported architectural and gate verdicts. The review
does not establish runtime incidence, qualification, or full alignment
across unexamined variants.

Correct source-view coverage, source-value validity, numerical consistency,
derivation and target identity first by consequence. Release determinism enables exact preview
and compatible native admission. Trusted source identity and routing
decisions enable safe preparation reuse and indexed visual delivery.
Outcome and custody corrections can proceed independently and supply
the managed boundary for retained routing decisions. These dependencies
describe the target design. Execution order and acceptance ownership are
for the subsequent implementation plan.
