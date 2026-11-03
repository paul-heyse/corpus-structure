# Unified domain model: typed operations and generated realization

**Status:** Active — code functionality implemented and validated; remaining scope is agent assessment and follow-up work only (operator clarification, 2026-11-03).
**Created:** 2026-11-01. **Target claims:** Substantial implementation with the bounded gaps below; Tested only within
recorded receipt scopes. Historical evidence retains its original source and scope. This coordinator alone owns package state,
execution queue and source-review disposition for the new series.

## Outcome, authority and selected scope

Deliver R01–R09 and O01–O03 from the [integrated review](../design_review/reviews/design_review_unified-domain-model_2026-11-01.md)
at `370f0643`. One coherent release governs concepts, relationships, operations, state,
comparison/invariant policy and qualified consumers. Ordinary callers use domain APIs;
model-derived typed implementations generate relational/native products and minimize maintained
SQL. Preserve database enforcement and exact/pinned evidence across Python, SQL, Arrow and RDF.

This is a new implementation series. Existing plans, their historical qualification and their
scheduled finding ownership remain unchanged. The review is design evidence; DESIGN/D-documents
and accepted ADRs remain architectural authority. UM-00 schedules selected authority amendments
before dependent new behavior. No production code, database, dependency or default was changed
while authoring this series. Creating these plans does not itself start implementation.

Operator decisions, 2026-11-01: all nine recommendations and three functional opportunities enter
this series, including bounded investigations. RC01–RC03 accepted; RC04 rejected. A conditional
mechanism must receive an explicit result and realization decision; it cannot silently erase
its selected capability. Complete procedural SQL elimination remains unestablished.

## Baseline and focused foundation assessment

Inspected source `370f0643`, with the current dirty PDF model/contracts, generated columns,
native-candidate, readers/producers, payload/metadata validation, native functions/SQL and tests
read where relevant. The principal review used `1cb8e620`/`f999ffcb`, diagnostic revisions
UM-20261101-r2/r3, publications `cc2998d9`/`54cd74cb`. Current source remains substantially founded
on effective LinkML definitions, prepared Pydantic boundaries, native execution bindings,
Core metadata/typed columns, qualified graphs, owned Arrow/DuckDB analysis, protected publication
and Alembic native operations. They are reused, not presumed absent.

The additional user direction is explicit: the PDF series is still changing; use the inspected
current snapshot and reconcile later in a **discrete update**, rather than continuously tracking
or integrating its work. The PDF coordinator retains current-book completion, provider/evaluator
journeys, deployment/default adoption and its evidence. A later change affecting a consumed
contract requires focused reinspection before executing that affected package. It does not
invalidate unrelated settled design or require another full review.

The SQLGlot guide's Advanced Capabilities Addendum (supplied lines 1121–2724) was assessed in full
on 2026-11-01 after the principal review. [UM-08](unified-domain-model/relational-implementations-and-projections.md#added-sqlglot-capabilities-disposition-and-limits)
records all added capability-family dispositions. Selected improvements include non-output
dependencies, pinned source composition, rich type descriptions, origin diagnostics and explicit
AST completeness admission, consumed by O02/O03. Exact v30.27.0 source confirms the remaining
PostgreSQL procedural-generation gap. Core-primary execution and native enforcement are retained;
no architectural rule change beyond the confirmed RC decisions is introduced.

Foundation conclusions:

- Comparison grouping needs its own checked projection; different fact/comparison identities can
  be legitimate. Preserve current policy behavior until an explicit semantic change is selected.
- Invariant failure codes become domain-facing promises only through an admitted enforcer and
  stable native diagnostic identity; SQLSTATE or message text alone cannot identify an invariant.
- Existing domain APIs and typed columns do not type every bind or row materialization. Generate
  actual signatures, expressions and materializers together; retain independent runtime admission.
- Relational execution stays set-based. Structured SQL-language body generation is feasible at
  the interface level; current AS-body custody and prosqlbody refusal require versioned changes.
- Resources and lazy-result ownership are runtime inputs/contracts, separate from semantic policy.
- O01–O03 must consume the same contracts and validators as real operations, without a second
  interpreter, schema authority or universal workflow framework.

## PDF consumer reconciliation

**Scoped plan amendment, 2026-11-01; target Proposed, all UM packages remain Planned.**
The operator selected updating this series only. This is the discrete reconciliation for the
published-document consumer case; other changed PDF contracts still require focused reinspection
before dependent execution. It changes no PDF package state or execution scope, architecture,
database, dependency or operational default. Existing RC01–RC04 decisions remain in force.

Inspected source `5dec0c2f` and identified dirty PDF/status/evidence context. Read-only inspection
of owned `corpus_pdf_20261101` found published task10/product `integrated`, logical digest
`d3482c7126a5db75d8bb1962bb34cabd1b8f772bc136cd3f5987744dfec7bce0`.
The subsequent source-preparation attempt failed constraint
`fk_source_view_native_task_id_native_product_key_sectio_e425`. Source-view publication reads
the new published record projection, while the physical model/FK still targets
`kb.native_document_item`; rendered-artifact FK likewise targets `kb.native_document_region`,
and rendering still directly selects that old relation. Integrated reuse also reconstructs,
serializes and reloads the book merely to prepare selected sections. These are inspected
foundations/gaps, not UM implementation results. The [PDF coordinator](pdf-docling-pipeline_2026-10-31.md)
retains current deployment, repair and actual consumer/provider/evaluator/default acceptance.
This amendment does not promote that publication to completed knowledge or full qualification.

The shared target connects an enforced published-address invariant, typed domain operations,
model-bound selected-section projection and native effect relationships. The
[relational companion](unified-domain-model/relational-implementations-and-projections.md#published-document-consumers)
is the single technical owner of binding keys and projection design; UM-02 owns invariant meaning.
Build/revision placement stays internal, preserving semantic product pins and original/frozen
evidence. Existing publication can feed newly prepared consumers; consumer-only changes do not
require recognition or whole-book republication. Necessary global validation and explicit complete
exports retain their own guarantees. No new identity registry, parallel schema or benchmark follows.

| Existing package | Required contribution to this case |
|---|---|
| UM-00/02 | Reconcile actual PDF prerequisite; resolve enforced relationship and operation/state/failure meaning. |
| UM-03/05 | Typed request/result/bind/materializer continuity, selected projection and shared read/effect endpoint binding. |
| UM-06/07 | Model-derived composite constraints, native insert/replay correspondence and frozen forward admission. |
| UM-09/10 | Appropriate selected/batch reads, resource propagation, snapshot/cancellation and retained immutable assurance. |
| UM-11/12/13 | Shared prerequisite explanation, declared relationship impact and model/address-located native diagnostics. |
| UM-14/15 | Actual affected-consumer closure and independent small native success/refusal/recovery journeys. |

The case extends R03/R05/R06/R07/R09 and O01–O03 through their existing owners, without inventing
new review findings or duplicating scheduled PDF obligations. SQLGlot analysis remains qualified
projection evidence, not proof of native relational enforcement. UM-04's query-compatibility
contract and UM-01's scientific comparison obligations remain unchanged.

Define shared contracts early; integrate each producer with the consumers it changes once its
required PDF foundation is usable. Do not defer a broken effect-side relationship to final UM-14
cleanup or make unrelated UM work wait for the whole PDF series. If PDF repairs land first,
inspect and reuse their actual binding/reader contracts rather than implement a second route.
The [UM-14/15 acceptance case](unified-domain-model/integration-adoption-and-qualification.md#published-document-consumer-acceptance)
owns the additional planned controls. No production test or provider result is established by
this plan amendment; historical receipts retain their dates, source and scope.

Amendment authoring checks (2026-11-01): `git diff --check` passed; bounded document review
found no material ownership/status/link issues. `just docs-check` failed on existing deferred
library-reorganization links, with no reported UM-series error. Product tests and provider
execution were not_run for these documentation changes. Read-only catalog inspection establishes
only the publication/constraint baseline above, not assembled UM or PDF acceptance.

## Rule decisions and architectural routes

| Item | Operator decision, 2026-11-01 | Consequence / route before dependent implementation |
|---|---|---|
| RC01 | Accept | Domain APIs and model-derived Core authoring; UM-00 amends D2/D3/D8 ownership detail through the governing ADR route where binding meaning changes. Completed PG-plan history is not rewritten. |
| RC02 | Accept | Structured SQL-language bodies with versioned inventory/custody/catalog/admission; UM-00/06/07 update D3 and the relevant accepted decision through its existing ADR route before new admission. No automatic general procedure/PLpgSQL support. |
| RC03 | Accept | Qualify and deliver a useful model-bound projection analysis consumer. UM-08 selects an exact SQLGlot release after verification; normal dependency selection alone needs no ADR. Changed authority would. |
| RC04 | Reject | Retain §B4 server-side enforcement and restricted writers. No client-side replacement of protected publication or added publisher privileges. |

## Reading route and ownership

| Companion | Owns |
|---|---|
| [Semantic contracts and policies](unified-domain-model/semantic-contracts-and-policies.md) | UM-01/02, comparison and invariant semantics; shared contract authority |
| [Typed domain operations](unified-domain-model/typed-domain-operations.md) | UM-03, generated requests/results/callables and materializers |
| [Relational implementations and projections](unified-domain-model/relational-implementations-and-projections.md) | UM-05/08, Core recipes and SQLGlot analysis |
| [Native authoring and evolution](unified-domain-model/native-authoring-and-evolution.md) | UM-06/07, native generation, custody/admission and frozen evolution |
| [Query compatibility and serving](unified-domain-model/query-compatibility-and-serving.md) | UM-04, old-run query meaning and complete serving journey |
| [Execution resources and transport](unified-domain-model/execution-resources-and-transport.md) | UM-09/10, configured execution, lazy results and directional transport |
| [Operation explanations, semantic impact and validation](unified-domain-model/operation-explanations-semantic-impact-and-validation.md) | UM-11/12/13, real CLI/MCP operator/agent capabilities |
| [Integration, adoption and qualification](unified-domain-model/integration-adoption-and-qualification.md) | UM-14/15, combined consumer coverage, adoption and acceptance |

Companions explain local designs, mechanisms, alternatives and package acceptance. They link here
for mutable package state. Shared model declarations, generator inputs, manifests and generated
outputs require one writer per integrated slice. Logical independence does not confer concurrent
edit ownership. Document boundaries are not execution barriers or permanent worker assignments.

## Package queue and working prerequisites

The table is the sole current package-state owner. Early implementation is not assembled qualification. A prerequisite means
usable contract/behavior, not that an entire companion must finish. Early contracts and later
admission/consumer closure are deliberately separate.

| Package | State | Required working input | Delivered behavior / completion boundary |
|---|---|---|---|
| UM-00 | Implemented; functional/native qualification passed | Confirmed decisions and current owner/source snapshot | Architecture/rule amendments, explicit supported versions and source-to-consumer baseline for this series; no new audit |
| UM-01 | Implemented; functional/native qualification passed | Effective property definitions and current comparison policy | Checked comparison context/meaning/evidence projection, used by scientific decisions without changing fact identity |
| UM-02 | Implemented; functional/native qualification passed | Current invariant/enforcer/operation definitions | Observable versus descriptive invariant contract and qualified diagnostic mapping consumed by real enforcers |
| UM-03 | Implemented; UM-TA04 typed-support extension implemented; functional/native qualification passed | Settled request/result concepts; UM-02 only for promised failure mapping | Generated typed domain calls, binds, Core/result projections and materializers, including published-document consumers with private placement bindings |
| UM-04 | Implemented; functional/native qualification passed | Existing serving protocol; settled implementation compatibility binding | Archived-run query/continuation/explanation/evidence meaning is compatible or explicitly refused |
| UM-05 | Implemented; functional/native qualification passed | UM-03 signature/projection contract slice, not full caller migration; working PDF foundation for its consumer case | Model-bound Core companion/inference recipes plus published-address read/effect bindings and selected-section projection |
| UM-06 | Implemented; functional/native qualification passed | UM-02 enforcement contract and UM-05 selected native expression recipes | Structured native declarations and eligible SQL-language bodies with versioned identity/dependency/admission |
| UM-07 | Implemented; functional/native qualification passed | UM-06 first qualified desired product plus existing Alembic lifecycle | Frozen forward native transitions including changed consumer constraints/inserts/replay, before/after drift/ACL/recreation controls; old revisions unchanged |
| UM-08 | Implemented; functional/native qualification passed | One settled UM-05 companion recipe and model/native signature metadata | Qualified projection type/dependency analysis with SQLGlot, unknowns explicit, used by UM-12 |
| UM-09 | Implemented through native99; functional/native and source publication Tested | Existing Settings and AnalysisScope owners | Non-default resources reach operations; supported lazy results enforce owner lifetime |
| UM-10 | Implemented; functional/native qualification passed | UM-03/05 directional operation contracts and relevant UM-09 owners | Model-derived exact transfer/decoding used in actual publication and analytical read/export |
| UM-11 | Implemented; functional/native qualification passed | Operation/state/binding contracts plus actual owner checks | CLI/MCP operation/prerequisite explanations; effects recheck atomically |
| UM-12 | Implemented; UM-TA02 alias-impact extension implemented; functional/native qualification passed | UM-01/02 semantics, UM-05 projection dependencies, relevant UM-08 analysis | CLI/MCP semantic impact and declared consumer changes, with conservative unknowns |
| UM-13 | Implemented; functional/native qualification passed | Existing validator outputs and an early shared diagnostic contract | Model/path/operation/scope-located diagnostic consumers preserving failure categories |
| UM-14 | Implemented through native99; source consumers Tested; knowledge adoption open | Working producer and affected consumer products from each package | Remaining maintained callers migrated; replacement paths retired and supported archives/adoption reconciled |
| UM-15 | Partial — functional/native and source consumers Tested; Claude-dependent acceptance open | All selected functional scope and UM-14 final-source integration | Required functional/native/provider/nonfunctional union has applicable evidence; honest unresolved/benefit limits |

Useful order: begin UM-00 and shared contract definition; UM-04 and UM-09 can progress independently.
Develop UM-01/02 and UM-03 contracts early, then UM-05/06/07 and UM-10 as working products become
available. UM-13's diagnostic contract can precede its full consumer delivery; UM-08 can begin from
one projection. Deliver O01/O03 incrementally with actual operations; O02 follows semantic
contracts. Producers migrate their directly affected consumers within their package. UM-14
completes the remaining inventory; it is not permission to postpone required integration.

## Source-review disposition and retained alternatives

This table schedules new review obligations, not a second copy of an older plan's DA progress.
Original audit IDs and older scheduled homes remain linked; this series owns its R/O delivery.

| Source item | Package owner | Closure obligation |
|---|---|---|
| R01 / DA-001 | UM-01 | Explicit checked grouping, independent coarser-grouping and invalid-reference controls |
| R02 / DA-028 | UM-04 | Old-run plugin edit through real CLI, continuation, explanation and evidence |
| R03 / DA-027 | UM-02 | Qualified invariant/diagnostic contract realized by enforcers, not metadata parity alone |
| R04 / DA-020 | UM-09 | Resource propagation and lazy-consumption supported boundary |
| R05 | UM-03 | Static call/parameter/result continuity plus runtime output admission |
| R06 | UM-05 | Single model recipe, Core consumers, exact scope/null/multiplicity semantics |
| R07 | UM-06/07 | Structured native authoring/custody and explicit procedural-family disposition |
| R08 | UM-08 | Useful qualified projection analysis and actual impact consumer |
| R09 | UM-10 | Exact directional codecs and existing transaction/snapshot ownership |
| O01 | UM-11 | Actual CLI/MCP applicability explanation and stale-preflight refusal |
| O02 | UM-12 | Changed qualifier/result/projection consumer impact plus explicit unknown |
| O03 | UM-13 | Invalid value/cross-record/validator-failure diagnostics through actual consumers |
| Review §§3/6/8–12 | UM-14/15, plus local owners | All maintained consumers, qualified relationship/lifecycle/substitution/growth/failure cases and truthful acceptance |

LinkML-Map 0.5.4 remains a candidate for a named pure translation, not publication replacement;
join multiplicity, exact types and provenance must fit. LinkML-Datalog 0.2.0 remains a candidate
for a required inference family beyond the selected qualified SQL kernel; numeric/provenance and
modern compatibility gaps remain. Selective ORM requires a named editable aggregate. Universal
SQL/procedural DSL, central SQLGlot IR, arbitrary archived-code execution and client enforcement
replacement are not selected. These choices and revisit triggers remain in the relevant companion;
no library adoption quota follows from coverage of eighteen guides.

## Mechanism and evidence preservation

Each implementing package owns its local explanation of authoritative definition → exact library
APIs/composition → real consumer → preserved guarantees and failure case, including versions,
primary/installed source pointers and residual obligations. Selected/candidate/unresolved are
choice labels, distinct from Proposed/Interface-checked/Implemented/Tested/Measured.

Reuse the focused [semantic](../library_leverage/libraries/unified-model-semantics_2026-11-01.md),
[boundary](../library_leverage/libraries/unified-model-boundaries_2026-11-01.md) and
[PostgreSQL](../library_leverage/libraries/unified-model-postgresql_2026-11-01.md) assessments.
Exact versions are not silently promoted from newer addenda: current review pins include
LinkML/runtime1.12.1, RDFLib7.6.0, pySHACL0.40.1, Valuesets0.4.2, Pydantic2.14.1,
settings2.16.1, jsonschema4.26.0, Arrow26.0.0, DuckDB2.0.0; SQLAlchemy2.1.6,
Alembic1.20.1, pglast8.7, Psycopg3.3.6/pool3.3.3, pgpq0.12.0, ADBC1.13.0.
SQLGlot30.27.0 is now installed exactly (2026-11-02). UM-00 reconciled actual pins;
needed version moves are deliberate, exact and affected-test scoped, not a wholesale upgrade.

## Investigations, acceptance and current boundary

Companions own bounded investigations with settling evidence and dependent packages: generated
static signatures, structured-body server/custody equivalence, delayed iterator behavior,
serializer equivalence, SQLGlot projection fidelity, and any selected transport/type substitution.
Each outcome must change a choice, allow dependent work or leave a named obligation open.
No investigation is a pretext for a broad benchmark campaign or another library survey.

[UM-14/15](unified-domain-model/integration-adoption-and-qualification.md) defines the combined
acceptance and later discrete PDF drift reconciliation. Independent semantic expectations,
native authorization/concurrency, actual CLI/MCP use and maintained consumer migration matter;
annotation existence or self-round-tripping does not establish correctness. Run targeted checks
during implementation; final maintenance precedes integrated qualification at complete scope.
No speed, memory, capacity or quality improvement is established by these plan documents.

**Next:** resolve the completion-audit obligations below through their existing package owners, then reassess affected functional evidence and the required acceptance union. Historical PDF/PG receipts retain their scope and do not qualify UM replacements.

## Execution checkpoint — 2026-11-02

The operator authorized the complete UM-00–15 execution approach. ADR-0046 records accepted RC01–RC03 realization boundaries while preserving RC04; D2/D3/D8 and DESIGN §B4/§B5 carry the target. SQLGlot30.27.0 was added exactly, with only its intended lock/dependency changes; `just ready` passed. These steps do not establish UM-08 analysis or native body support.

One writer owns shared model/preparation/archive/generation changes; separate owners implement query compatibility and resource/lifetime consumers. Current source/body profiles, frozen migrations, book task10 pin and dirty concurrent PDF/library files remain preserved. Independent focused checks precede complete-scope qualification. Available disk was about6GB at kickoff; small owned tests and retained products avoid full database/book copies. No cache/database/evidence cleanup was performed.

Product qualification has a failed completed attempt; required-union and applicable provider obligations remain open, as assessed below.

### Integrated implementation checkpoint — 2026-11-02

The working tree implements checked comparison/PRESENT contracts, qualified invariant diagnostics,
87 fixed correspondences (76 native and11 Core), query implementation custody, execution resources
and lazy ownership, finite relational/projection analysis, and model-bound reports. Core registration
and document/rendition/original custody retain their named algorithms while generated requests,
TypedColumns/closed column protocols, value projections and strict materializers own correspondence.
Dynamic configuration, domain records, fixed-point working relations and Arrow families retain their
existing checked boundaries. Static continuity is not a claim to infer every algorithm from schema.

Compiler23 distinguishes native versus Core binding products. Exact20–22 archive decoding remains
separate from current source/effect admission; immutable products are not re-normalized through
current capabilities. Actual old20 static CLI/MCP inspection and explicit unsupported subject refusal
passed with the current23 reader. Full query continuation/plugin-edit/compatibility journeys passed
under their scoped custody owner. Report changes retain exact member facts, absence/null and ordered
membership; native diagnostics retain available producing model/release and original failure scope.

Forward83–90 are frozen. The current desired native state has61 objects and12 SQL-standard bodies.
The original published-address constraints/backfill remain unchanged; observation-only retention
replaces current aggregate document writes. Current native support checks resolve every declared
edge against exact input pin, coverage ID, scope and family; integrated complete coverage needs a
complete witness. Native intrinsic coverage and weaker/mixed cases retain their declared meanings.
Validation epochv5 rejects stale unfinished receipts. Published reads instead use their original
immutable receipt, keeping projection and schema-source contracts distinct. The final descriptor-only
successors bind the actual callback/operation source; they do not change native policy or epoch.
See the [native evidence](../design_review/evidence/2026-11-02_um-native-evolution/README.md).

Scoped tests include76 shared Core/archive/resource controls,28 added receipt-call controls,
19 optional-support callback controls and25 current report/product controls. Native authoring,
actual admission, frozen82→90 replay, drift/stale-state refusals, exact empty candidates and outer
rollback passed. Counts overlap and are not added. Failed/interrupted receipts remain unchanged;
formatting does not itself invalidate typing or functional results.

Assembled acceptance is still open. Earlier native88 failures and their affected repairs retain
individual receipts. Repository-root qualification initially passed281 cases with2 fixture failures
(`build/test-receipts/qualification/20261102T131710Z-2800697`); those same2 corrected fixtures passed
in `build/um-root-retained-fixtures-00001.log`, without repeating unaffected cases. The product run
completed with3107 passed/30 failed/0 skipped. Its exact failures and applicability are assessed in
the completion audit below. Rust exited0 with zero tests, establishing no Rust functional coverage.
Package/local passes do not close UM-14/15 or import PDF provider/book/default acceptance.

No target deployment occurred. Actual task10 retained-v4 receipt inspection was read-only; the book
remains at82 and was neither recognized again nor republished. The PDF coordinator retains its
operational/provider/evaluator/default-adoption obligations.

## Completion audit — 2026-11-02

**Baseline:** `fb84eb8f`, initially clean tree, product source unchanged from closeout `d457bdf0`.
Assessed all Complete/Implemented/Tested subclaims in UM-00–15 and all eight companions, including
partial packages. Reconstructed R01–R09/O01–O03 from the principal review, accepted amendments,
concrete mechanism tables and plan history (`d5ce3ff2`, `0eaead10`, `009ee977`, `d457bdf0`).
ADR-0047 authorizes retirement of old formats, not removal of guarantees for current consumers.
The prior audit is reassessed here, not presumed closure evidence. Diagnostic audit premises and
concurrent test-architecture planning remain unchanged.

**Implementation judgment:** substantial delivery of the accepted model, library mechanisms and
ordinary consumers is confirmed by independent source inspection. One incomplete integration is
confirmed, UM-CA13: operation cancellation does not cover the SQLAlchemy metadata/snapshot phase
of companion export. UM-09/10/14 therefore remain partially implemented at that seam. Other scoped
implementation claims are supported; this does not certify a universal complete domain model.

**Qualification judgment:** retained232 distinct targeted native passes and four pure child-graph
cases have their recorded scope. They do not establish UM-15. The79-node math remainder, corrected
fresh PDF intake, actual-provider five-section knowledge/query/report/export/evaluation journey
and complete applicable qualification remain open. Historical failed receipts are preserved.
No tests, live probes, inference or database mutations were needed for this audit: the cancellation
call path and existing coverage limits establish the gap statically. No new performance or
semantic-fidelity benefit was measured.

### Current obligations and disposition

The coordinator is the sole disposition owner; previous source evidence remains recoverable in Git.

| ID / owner | Current disposition and decisive evidence | Remaining obligation |
|---|---|---|
| UM-CA01 — UM-03/04/14 | Authorized retirement implemented: current archive3 custody and producing/installed query compatibility remain; old compiler readers explicitly refuse. | Required-union qualification at UM-CA10; no restoration of obsolete formats. |
| UM-CA02 — UM-03/14 | Current composed run/project/cancellation/hold paths replace base execution; source guards and native91 retire obsolete storage. | Current consumer acceptance at UM-CA10. |
| UM-CA03 — UM-06/07/14 | Pure derive and sole server-bound native-candidate route are implemented; frozen91–94 replay/empty-candidate/refusal/rollback receipts exist. | No unbound deployment authority; retain actual native qualification limits. |
| UM-CA04 — UM-09/14 | Configured driver now reaches `companion_export.py:129–134`; snapshot import and batch hints are actual consumers. | Driver omission corrected; UM-CA13 now has bounded metadata/handoff/bulk closure. |
| UM-CA05 — UM-08/12/13 | `projection_analysis.py:267–349` executes strict qualification/type/scope/lineage and relational clause dependencies; actual impact consumes the archive product. | Unknown helper/body semantics remain explicit; not universal semantic equivalence. |
| UM-CA06 — UM-13/14 | `ontology.py:985–1018` returns the shared located graph report and raw validation; shape/execution/nonconformance distinctions remain. | Broader actual-provider/consumer qualification at UM-CA10. |
| UM-CA07 — UM-13/14 | Invocation-local FailureContext carries known release/model/operation through CLI/MCP translation; structured native invariant bindings preserve cause. | No claim that every library error is normalized or every invariant has a qualified observer. |
| UM-CA08 — UM-06 | `native_catalog.py:96–244` supplies typed observed catalogs, consumed by native_objects; existing Inspector/Alembic owners retained. | Selected catalog mechanism delivered; no second desired catalog. |
| UM-CA09 — UM-03/14 | Generated columns match authoritative current stored metadata; separate read shapes do not own DDL. | Retain generation/static/runtime evidence scope. |
| UM-CA11 — UM-12/14 | `cli/regenerate.py:230–249` actually consumes shared impact/advice; class/helper gaps report unknown. | Richer known dependency closure is optional improvement I05, not a false-success defect. |
| UM-CA12 — UM-03/14 | Generated semantic NewTypes and nested completion IDs reach strict scalar/JSON materialization. | Static and runtime controls remain complementary. |
| UM-CA10 — UM-14/15 | Functional/native required union3318/563 has zero unresolved; actual SourceReady, CLI/MCP/render/full-export consumers passed. Full series acceptance remains open. | Complete actual knowledge extraction, source-only A/B/C references, evaluator and result/default adoption from the prepared run6; preserve current source and applicable receipts rather than repeating PDF processing. |
| UM-CA13 — UM-09/10/14 | Implemented and focused Tested: one sticky operation owner registers PostgreSQL metadata/snapshot and ADBC work, including capture. | Metadata/handoff pass in `um-native96-cancellation-observation-001`, bulk in `-002`; capture-binding pass in `um-native96-closure-001`. Retain broader UM-CA10 acceptance and separate publication-fidelity evidence. |
| UM-CA14 — UM-09/13/14 | Implemented and focused Tested under native97: Standard-child FD1 diagnostics route to stderr, preserving pre-bound TableFormer loggers, native writes and typed Pipe replies. Baseline failure and corrected success/error controls are retained. | Actual stock source preparation and CLI passed; broader knowledge acceptance stays UM-CA10; `build/um-native-stdio-{baseline,fixed}` and `um.native-stdio-renewal97` bound this correction. |
| UM-CA15 — UM-09/14 | Implemented and scoped Tested under native97: bounded companion transactions and inventory hashing outside the task fence remove the observed renewal lock contention. Existing model-owned isolation and protected append-only/count checks preserve freeze semantics. | Actual native publication and post-termination read passed. Required36-node selection is closed by `build/um-native97-renewal-union.json`; earlier failed receipts remain failed. No timeout increase or weakened validation. |
| UM-CA16 — UM-14 | Implemented through native98: supplied raw pins use the canonical organizer; same-task exact published output custody permits organization before source-view selection. All40 affected controls pass, including13 native; author/replay has exactly two source changes and no schema/policy change. | Actual run6 five-view preparation and source clients passed. Preserve selected/declared-input and cross-task/document/source/project refusals; knowledge acceptance stays UM-CA10. |
| UM-CA17 — UM-03/05/14 | Implemented and scoped Tested under native99: exact-pin batch qualification of the excluded furniture frontier preserves body membership/text/items and strict missing/body/identity refusals. All33 affected controls pass, including12 native; actual run6 passes the former failure and reuses task5’s organized pin. | Integrated publication, five views and external source clients passed. Diagnostic receipt and failed run5 artifacts remain; knowledge/reference/evaluator acceptance stays UM-CA10. No organization or conversion was repeated for this repair. |

### UM-CA13 evidence and closure

**Implemented / scoped Tested, 2026-11-03.** The original gap below motivated the composed
operation owner in `core/db/cancellation.py`. Metadata, snapshot/capture and ADBC borrowers now
register with the same sticky request; final atomic publication is linearized against cancellation.
Actual metadata/handoff/bulk controls and capture binding passed in the receipts named above.
Backend-specific settlement and original-versus-cleanup errors remain distinct. This closes the
cancellation seam, not PDF publication fidelity or UM-15's enclosing qualification.

**Original audit evidence at `fb84eb8f`:**

`serve/companion_export.py:87,92–93` accepts/polls ADBCBorrowerCancellation, but
`:109–110` calls read_snapshot without its SQLAlchemy cancellation argument; `:112–122` omits
inspect_native_source's token; `:127` exports the snapshot before ADBC registration at129–134.
`serve/native_source.py:164–175` consequently creates another BorrowerCancellation. A caller's
request cannot interrupt an in-flight pin/header/archive/snapshot SQLAlchemy query. This violates
the transport/resource consumer-continuity obligation, not the configured-driver requirement.

`tests/semantic/test_companion_export.py:229–344` mocks snapshot/source inspection and cancels in
fetch_record_batch; the actual ADBC slow-query control in `tests/db/test_adbc_lifetime.py:15–61`
does not assess this two-backend handoff. ADBC's `.adbc_cancel()` token cannot simply be passed to
SQLAlchemy. Extend the existing owners with operation-level phase/fanout registration, preserving
snapshot lifetime, atomic output and cancellation-versus-cleanup failures. Independent closure
controls must interrupt the actual metadata phase, handoff and ADBC read and verify settlement.

### Library realization and substitution judgment

Concrete API/consumer evidence and proposed opportunities are preserved in the
[linked improvement review](../plan_improvement_reviews/unified-domain-model_2026-11-02.md#accepted-library-mechanism-account).
The companion method tables remain required reading. LinkML effective resolution, strict prepared
Pydantic adapters, normalized cattrs products, qualified RDFLib/pySHACL reports, typed Core recipes,
pglast SQL-standard bodies, Alembic operation/comparator/renderer integration, typed catalogs,
SQLGlot strict analysis and directional Arrow/DuckDB/Psycopg/pgpq/ADBC ownership are substantively
used. API names alone were not accepted as proof.

Retained procedural families have named trigger/assertion/order/custody/privilege construct reasons;
a general procedural compiler, universal ORM, Map/Datalog replacement, RDF store or Flight service
was not selected. Small semantic serialization visitors preserve supplied/reference semantics.
These are justified scope decisions, not missing library adoption. Model-owned external boundary
checks remain necessary even when Arrow physical validation or generated annotations succeed.

**Next:** finish current UM-CA10 qualification and operational acceptance without
promoting targeted receipts to assembled acceptance. The separate improvement review's I01–I05
are proposals requiring adoption, not automatic changes to this plan. Provider improvements also
name the existing PDF owner; they do not transfer every PDF obligation into UM.

**Audit publication checks (2026-11-02):** `git diff --check` and root `just turn-end`
passed; all720 Python files were unchanged. `just docs-check` failed on the existing deferred
library-reorganization links, with no UM-plan or new-review error reported. Product tests/types
were **not_run** for this documentation-only assessment; prior receipts keep their original scope.

## Current-only execution amendment — 2026-11-02

The operator approved all remaining scope plus repository legacy retirement, and selected resetting
all seven identified project-result databases on5434. ADR-0047 changes the supported runtime target:
current composed execution and record PDF publications only, with immutable current release custody.
UM-CA01/02 are now authorized retirement/transition work, not promises to repair historical results.
All other UM-CA obligations remain open until implementation and actual controls close them.

The audited203-file working implementation was committed as63cc99e5 before isolated concurrent work.
Three sparse worktrees exclude large evidence payloads. A mistaken full checkout was removed before
work began; no original evidence was deleted. After exact OID/owner/zero-client verification, all
seven selected result databases were dropped. Receipt build/um-current-result-reset.json records
24,341,479,424 bytes reclaimed (about22.67GiB); filesystem free space increased from about11GiB to33GiB.
Templates and the separately owned authoring database were preserved. The fresh-intake state is below.

Execution owners: current-model/generators/runtime and historical document removal; report/analysis/
graph/advice integration; native observation/authoring/export; root integration, legacy executor
retirement, forward freezing, fresh bootstrap/intake and final qualification. All reported passing
predecessor checks retain their limits. Final source must be qualified after broad retirement.

## Current execution checkpoint — 2026-11-02

**Operator clarification, 2026-11-03:** no code functionality remains to implement or validate in
this series. Remaining work is agent assessment and follow-up only. New M1 code and qualification
are owned by the [M1 series](first-production-milestone_2026-11-03.md), not unfinished UM work.

**Implemented / bounded Tested (updated2026-11-03); Claude-dependent acceptance open.**
Current compiler14/boundary12/execution23/archive3 and ADR-0047 remain current-only.
`7188cafb` integrates UM-CA13 and UM-TA01–04; `f536fede`/native97 repairs freeze/renewal and
child diagnostics; `b349bf59`/native98 unifies source selection/current-task output custody;
`38cdb8ba`/native99 qualifies excluded furniture children without changing body membership.
Frozen predecessors remain immutable. Application `corpus_pdf_20261102`/OID16934542 is on
native99 in dedicated18/corpus; other clusters are unchanged.

Run6 published integrated pin `6/integrated/1882a372985949584bc3c15a3df8b2c6a9f21a1b610dd2b583cea70dc44975ac`
and prepared five intact descendant analysis views. Source tasks are done/empty; tasks27–31
await agent work. No Claude session, completed knowledge result, reference authoring, grade or
result/default selection is claimed. The public status is `awaiting_agent`; the run remains
unsealed for continuation. Owned parsing/consumer processes and Nemotron8035 are stopped;
the database stays online and an actual post-stop status read passed with no orphaned tasks.

The functional union covers3318 distinct nodes,563 native, zero unresolved with complete
provenance and explicit96/97/98/99 applicability. Warning-inclusive types and scoped final99
Ruff passed; historical failed aggregates stay failed. Actual CLI7 calls, external stdio MCP13
operations, formula rendering/raw-response custody and7 export/roundtrip stages passed. Exports
cover1819 equal JSONL/Parquet rows and the complete1589-page native/integrated graph. These are
functional/source observations, not extraction fidelity or speed measurements.

Qualified retained native/perception inputs keep their exact bindings and original partial/unknown
health; missing candidate/OCR inventory stays unknown. The failed run3/run5 artifacts remain.
Run6 reused task5 organization and unchanged recognition receipts; no replacement perception
inference or historical knowledge import is claimed.

**Next executable work:** use the [exact run6 handoff](../design_review/evidence/2026-11-01_pdf-current-consumers/RUN6.md)
for queued knowledge work, source-only references, evaluation and eventual selection. Canonical
reference inputs and a separate complete prompt view are prepared; actual provider/model/context
capacity and semantic grades remain unqualified. The
[source consumer record](../design_review/evidence/2026-11-01_pdf-current-consumers/run6-source-ready.md)
and [functional record](../design_review/evidence/2026-11-03_um-section-closure-qualification/README.md)
own their respective evidence limits. Unselected improvements and diagnostic audit premises
are unchanged.

### Settled closeout evidence

**Historical bounded checkpoint at native94; current state is above.** The serialized targeted batch selected234 nodes:203 passed and31 failed. The two obsolete JSON
publisher/plan nodes were replaced with four independently specified current preparation cases,
which passed. Repairs preserved method/configuration/packet binding, exact published custody,
owned batch preparation, binary-profile refusal, evaluator privileges and query semantics.
The failure-only tail passed23 of29, then the final six passed4 and the last two passed2. These
are overlapping targeted receipts, not additive suite counts. The existing classifier's exact
surviving required-node union has232 distinct nodes with passing evidence and zero unresolved:
build/test-receipts/qualification/20261102-closeout-target-union.json. Its overall failed history
is intentionally retained alongside later passing evidence. A transient host DiskFull failure
also passed its exact retry after storage became available; no unrelated data was deleted.

All owned test groups and fixture databases are absent, recorded in
build/test-receipts/qualification/20261102-closeout-owned-settlement-final.json. All worktrees are
integrated/deleted; owned model services are stopped. Actual alternate-principal authentication
files and role sets restored exactly. No provider or broad math work is queued.

The child-graph controls assert refusal at current Docling preparation, without claiming native
publication proof. A dangling reference currently exposes Docling's raw IndexError; backpointer
and multiple-parent faults produce specific Pydantic validation errors. No malformed graph was
accepted. Current native record constraints and publication controls retain their own evidence.

just evidence finalize / just evidence passed:126 records,0errors,39 historical warnings.
just docs-check failed on the existing deferred library-reorganization links, with no UM-plan
error reported. Types and Ruff passed before the last assertion-only repair; affected fixture
files also passed scoped typing/lint. No result is invalidated solely by safe formatting.
The79-node math remainder, fresh PDF/provider journeys and final complete qualification remain
open. No implementation completion claim is promoted to full pipeline or benefit qualification.

## Test-architecture reconciliation — 2026-11-02

**Selected amendments, Proposed; source-inspected foundations only.** The operator authorized
combined design/assurance review and revision of this series, against a recorded snapshot with
one affected-change refresh. The [review](../plan_improvement_reviews/unified-domain-model-test-architecture_2026-11-02.md)
consumes `af567228` plus ongoing TA production/tests/support/owner changes. TA's coordinator
retains DTA disposition and TA-12 qualification; Phase0 X2-01 and PDF/provider owners are unchanged.
No production implementation, native/provider run, dependency change or new architectural rule
is authorized by publishing these amendments. RC01–RC04 remain unchanged.

The review confirms useful deeper model penetration: compiled full-class-IRI alias policy shared
by consolidation/evaluation, current independent semantic counterparts, fresh committed scenario
clones and observed native acquisition. Reuse these foundations rather than implement a second
fixture/validator/catalog/receipt framework. Known unsupported Notice classification and T3-D1
inference remain explicit; current authored counterparts do not prove original ingress recognition.

This table alone owns the new UM amendment state; source-review IDs remain qualified by review path.

| ID / package | Current disposition | Required outcome and closure |
|---|---|---|
| UM-TA01 — UM-04/03/14; review I05 | Implemented; qualification in progress | Include exact-object lowering's `consolidation.plain` and required delegates in existing finite query source custody. Cover pre-imported helpers, changed files after load and refusal before incompatible named-query/continuation execution. Frozen products remain immutable. |
| UM-TA02 — UM-12/13/14; review I01 | Implemented; actual CLI/MCP/advice control passed | Compare released alias profiles by class/member, separate origin from normalization changes, retain known consumer kinds and unknown dynamic closure through actual CLI/MCP/advice. Use existing report products and versioned model/implementation bindings, not another registry. |
| UM-TA03 — UM-08/03/12/14; review I06 | Implemented; focused cold/persist/cache checks passed | SQLGlot is already captured; qualify required captured/runtime analysis determinants before preparation/cache reuse. Refuse mismatch with reacquisition advice; supported immutable archives remain readable. Independent cold semantic-2 contents/dependency/type expectations complement warm/refusal controls. |
| UM-TA04 — UM-03/05/14; review I07 | Implemented; static controls passed | Type shared scenario resource/identity/result ports with existing domain types, migrate actual callers, and retain raw malformed construction and independent expected data. No universal scenario model. |
| Review I02/I03/I04 — UM-01–15 at affected owners | Acceptance amendments selected; qualification open | Reuse independent key/reference, cold/warm, native cause, explicit principal, stdio and formatter evidence only within their real scope; do not duplicate TA work or promote its partial evidence. UM-CA13 focused capture/metadata/handoff/bulk controls passed; assembled acceptance remains UM-CA10. |

UM-00/01/02 retain implemented authority/comparison/invariant foundations; consume the new released
policy and independent key/meaning controls. UM-03/04 carry typed ports and query custody; UM-05
retains set-based recipe ownership; UM-06/07 retain actual cold/frozen/native independent checks.
UM-08 qualifies analysis production; UM-09/10 preserve two-backend operation ownership; UM-11/13
require their own served explanation/diagnostic controls; UM-12 delivers the alias extension.
UM-14 migrates actual affected consumers and UM-15 owns evidence applicability and final union.
No package becomes qualified merely because TA improves its fixture infrastructure.

**Execution order:** repair UM-TA01 and UM-TA03 with their affected consumers; UM-TA04 is independent
once its scenario contracts are stable. UM-TA02 reuses working released policy and report contracts.
UM-CA13 proceeds independently through existing backend lifetime owners; include capture_packet's
actual SQLAlchemy/ADBC continuity, preserving snapshot lifetime and atomic output. Add only missing
UM-specific cold/admission/consumer checks; no all-TA-complete barrier or blanket full rerun follows.

**Evidence:** prior TA212-node/native and UM232-node receipts retain their original source/context;
new stdio/formatter/counterpart cases cannot inherit those passes. Use existing source_identity,
record_native_context and required-node classifier, with explicit restricted-operation/session
observations and human applicability judgment. Original failures remain. UM-CA10, the math
remainder and actual-provider/assembled acceptance are not closed by this source review.
The earlier improvement review's I01–I05 remain proposals except this explicitly selected,
bounded alias-impact extension overlaps its general I05 direction; no provider scope is adopted.

**Publication verification (2026-11-02):** scoped `git diff --check` passed; root `just turn-end`
passed with735 Python files unchanged. A read-only local-target check covered this coordinator,
eight companions and the new review with no missing source targets. Independent challenge found
one omitted UM-TA04 integration reference, corrected before publication. `just docs-check` failed
at the concurrent ADR-0048/§B4 decision-link lint before the publisher could run; that unrelated
in-progress TA authority edit was not repaired here. Product tests/types, native/provider checks
and broad qualification were not_run for this documentation-only engagement. These results do
not close any implementation or acceptance obligation.


## Remaining execution — 2026-11-02

**Implemented; qualification in progress.** The execution baseline was clean `7d1ade1a` after
TA completion. UM-TA01 extends finite query custody to exact-object lowering. UM-TA03 qualifies
SQLGlot/SQLAlchemy/LinkML-runtime inputs before preparation and analyzer cache reuse, preserving
retained-artifact reads. UM-TA02 compares released alias normalization and origins, preserves
actual implementation/profile consumer kinds and unknown dynamic closure, and reaches existing
report/advice consumers. UM-TA04 types shared scenario resource/identity/result ports and their
callers without replacing malformed inputs. UM-CA13 composes one sticky operation cancellation
request across existing Psycopg/ADBC owners and atomic publication. No new semantic authority,
provider lifecycle framework or historical compatibility layer is introduced.

Native96 freezes one descriptor transition, with no ordinary schema/catalog-policy change;
292 predecessor files remain unchanged. Authoring, outer rollback/prior admission, fresh replay,
repeated upgrade and empty candidate passed. The existing app database `corpus_pdf_20261102`,
OID16934542, was migrated through96; this does not itself admit a new result. The bounded owner is
[um.native-closure96](../design_review/evidence/2026-11-02_um-completion-forward/README.md).

**Passed, bounded:** warning-inclusive `just types`, corrected `just ruff`, `just ready`, focused
query/analysis/cache and cold semantic-2 checks, typed scenario static controls, pure cancellation
and alias controls. Six actual Store checkout controls passed with complete item-bound provenance
(`build/test-receipts/um-store-observation-001`). The latest TA broad receipt contains passing
calls for all79 formerly interrupted math nodes; their source/context applicability remains
separate from full current qualification. No separate historical math rerun is required.

**Failed, retained:** the first native96 selection (62 nodes,10passed/52failed) and fresh intake
exposed a scoped-analysis manifest mismatch at exact release persistence. Producer, persistence
and full verification now share the determinant owner; actual native96 persistence/full verification
and changed-runtime/archive-read controls passed in `um-scoped-persist-00001`. Exact validation
is not weakened. New cancellation controls also exposed cross-role monitoring visibility, repaired
using the actual reader principal without new grants or relaxed deadlines. Original receipts remain
under `build/test-receipts/um-native96-closure-001` and
`build/um-final-intake-20261103-attempt-00001`.

UM-CA10 and UM-15 remain open until the repaired real consumers, complete required union and configured
PDF/provider/reference/evaluator journeys have applicable evidence. Earlier improvement proposals
remain unadopted except the already selected alias extension. No diagnostic audit premises changed.


### Actual qualification and worker stdio follow-up

The full functional attempt `20261103T021214Z-2310775` finished with3295passed/1failed,
complete native provenance and no missing acquired-context nodes. Rust selected no tests
(not_run). The one failure was the new alias integration test assuming its minimal report fixture
contained domain-rule inputs. Its corrected actual-statistics setup passed real CLI/MCP/advice
in `um-alias-served-corrected-002`; the intermediate invalid minimal-rule fixture remains failed
in `-001`. This is scoped correction, not a relabelled fresh full-suite pass.

Actual Standard conversion exposed UM-CA14: TableFormer diagnostics reached CLI stdout. Its
spawned regression reproduces the defect and checks typed Pipe success/error replies plus native
FD writes. The fixed child routes diagnostics to stderr without suppression. Native97 freezes its
source provenance alongside UM-CA15: bounded companion transactions and inventory hashing outside
the task fence. The actual renewal failure was55P03, not an arbitrary processing deadline; guards,
leases and timeouts remain enforced. Native97 author/replay and the affected36-node union passed.
Independent review of `7188cafb` found no material issue; it ran no tests or provider calls.

The failed full-book run3 remains cancelled with its private spool/OCR metadata and real formula
work retained. Native task4 instead re-lowered the verified actual native observation from the
prior rebuild. It published pin `4/native/5ea04802e046368a609dea84430ba6a672dd87f826057e737d9eb263efe721b7`.
The original helper's post-check compared formula metadata against the health wrapper incorrectly;
publication itself completed. That failed receipt is retained. Corrected read-only recheck passed
in `build/um-native-recovery-postread-00001`: exact schema/archive/receipt, unchanged native health,
6342 formula outcomes, terminal producer task and cancelled auxiliary container with no unfinished
tasks. No second import, new inference, synthetic knowledge or OCR inventory was introduced.

UM-CA16 also includes current-task output custody: after ordinary organization, the exact newly
published child must be readable within its own still-running claimed document task, before source
views exist. Existing selected/exact-input custody remains; this requires an explicit same-task,
same-document/project/source check, not an arbitrary same-source bypass. Both fixes proceed through
the existing reader/selector and a source-only forward descriptor. Current five-section knowledge,
external consumers, independent references and grading remain open until their actual receipts.

### Final functional union at native98 — 2026-11-03

**Passed required-node coverage, bounded to Python functional/native scope.**
`build/um-final-required-functional.json` declares3311 distinct nodes, including562 native.
`build/um-final-functional-union.json` has zero required unresolved nodes and complete native
provenance. Applicability is explicit in `build/um-final-functional-applicability.json`:
3235 unchanged96 nodes,36 renewal97 nodes and40 affected98 nodes form disjoint groups. The97
freeze product is byte-equal at98; new98 guard assertions have their own98 passing evidence.
Do not substitute an older node-ID pass for a changed assertion.

The40-node98 selection first passed39 and failed one new native fixture setup after its actual
positive custody checks had passed. Writing its required second original PDF corrected that setup;
the exact native case then passed in `um-native98-final-affected-00002`. Both receipts remain.
The aggregate classifier intentionally remains failed because it retains original failed campaigns;
zero unresolved required nodes is not a relabelled all-green broad run. Whole warning-inclusive
`just types` and `just ruff` passed (`build/um-final-types-003.log`, `build/um-final-ruff-004.log`).
Ruff reordered two test imports only; no result is invalidated solely by that formatting.

This union does not establish actual full-book integration, external consumers, provider authoring,
extraction, independent references or evaluator acceptance. Run5/task5 is executing the ordinary
source preparation path on native98; those remaining obligations retain UM-CA10/UM-15 ownership.

### Retained organized-product recovery — 2026-11-03

Run5/task5 failed after successful protected organized publication and before recognition or source
views. `build/um-final-intake-20261103-attempt-00003` preserves exit1, exact stdout/stderr,
`organized.publication.json`, `organized.pin.json` and settled task/run state. The published pin is
`5/organized/28d8e22275dc6b069ed42e4e3fa82ed98dddf37801e5e122b069520a7e42b42f`.
The next preparation must consume that pin after UM-CA17's reader correction; repeating book
conversion or organization is unnecessary. The3311-node functional union above retains its scope;
this actual consumer defect adds a required obligation and prevents assembled acceptance.
Static independent review of `b349bf59` found no material selector/custody issue; it performed no
runtime operations and does not override this actual failure.

### Final functional union at native99 — 2026-11-03

**Passed required-node coverage, bounded to Python functional/native scope.** The updated required
set is3318 distinct nodes, including563 actual-native requirements, with zero unresolved required
nodes and complete native provenance. `build/um-final99-functional-applicability.json` partitions
3214 unchanged96,36 renewal97,35 unaffected98 and33 requalified99 nodes; seven new frontier
obligations are included. All non-descriptor native products are exact98↔99. The prior3311-node
account and its archived receipts remain immutable. Original failed aggregates remain failed.

The33-node actual99 endpoint passed in `um-native99-final-affected-00001`, covering independent
mixed-layer publication, frontier refusals, membership/text offsets/items/health, selected and
offline consumers, evidence/regions/reports and current native custody. Warning-inclusive
`just types` passed in `build/um-frontier-final-types-00001.log`; scoped Ruff passed. Source bytes
have not changed since99 freezing. No whole-suite rerun is justified solely by safe formatting.

The actual diagnosis confirmed every missing target in all five sections exists in the same
published placement with `content_layer=furniture`. Body-only SQL membership and original native
child references therefore need explicit frontier qualification, not relaxed missing-reference
checks. Run6/task6 now consumes the exact task5 organized pin and has advanced into cached
recognition admission without a new native/organized build. Its final integrated publication,
five-view source-ready state and actual provider/reference/evaluator acceptance remain open.

## SourceReady and non-Claude acceptance — 2026-11-03

**Tested, bounded; UM-CA10 remains open for knowledge/reference/evaluator adoption.** Stock
prepare-only attempt00004 passed on run6 with views1–5 and tasks27–31 awaiting agent work.
The [source-ready record](../design_review/evidence/2026-11-01_pdf-current-consumers/run6-source-ready.md)
retains exact publication/CLI/pin/source/task identities, actual source consumers, previous failures
and owned-service settlement. Native schema/tree validation and detached roundtrip passed on
1589 pages,183085 text items and107 tables. The integrated V2 export is511116985 bytes; its
serialization digest is verified independently of the distinct logical record-fold identity.

The current table-cell challenge is in analysis view4 and has valid retained text without a
cell bbox. Source inspection supports that modeled state; formula rendering uses its own actual
provenance. The helper's stale bbox requirement failed once, was corrected without inventing
coordinates, and all current source journeys passed. The current export helper admits only V2;
no legacy aggregate fallback was retained. No production source changed after native99 freezing.

Reference preparation preserves complete canonical frames and uses a distinct frame-derived
provider view with exact body text, rich structure and evidence quotes. Raw reconciliation graphs
and repeated packet/schema serialization are omitted from transmission, while local admission
still consumes the complete canonical frames. Controlled protocol/preparation checks are not
Claude execution. Current inputs and exact continuation commands are in the
[run6 handoff](../design_review/evidence/2026-11-01_pdf-current-consumers/RUN6.md).

Knowledge extraction, A/B/C authoring, semantic reference agreement, evaluator grades, completed
result selection and persistent default-result adoption remain `not_run` or pending their
required authored outputs. SourceReady and3318 passing required-node obligations do not close
those remaining UM-14/15 acceptance obligations. No new audit premises, performance claim or
accuracy threshold is introduced.

Final maintenance: `just turn-end` passed. Cosmetic test formatting leaves the qualified behavior
unchanged; product source bytes match the admitted native99 input set. Types/tests are not rerun
solely after formatting. `just docs-check` still fails on deferred library-reorganization links,
with no current UM/source-consumer target reported. Evidence finalize/catalog/render/check passed:
136 current records, zero errors,39 historical warnings. The
[reference-input record](../design_review/evidence/2026-11-01_pdf-current-consumers/run6-reference-inputs.md)
qualifies preparation and controlled protocol only; all actual Claude-dependent outcomes remain open.
