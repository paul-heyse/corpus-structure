# Unified domain model: typed operations and generated realization

**Status:** Active — completion audit confirms substantive implementation; UM-CA13 cancellation integration and UM-CA10 assembled acceptance remain open (2026-11-02).
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
| UM-00 | Implemented; qualification open | Confirmed decisions and current owner/source snapshot | Architecture/rule amendments, explicit supported versions and source-to-consumer baseline for this series; no new audit |
| UM-01 | Implemented; qualification open | Effective property definitions and current comparison policy | Checked comparison context/meaning/evidence projection, used by scientific decisions without changing fact identity |
| UM-02 | Implemented; qualification open | Current invariant/enforcer/operation definitions | Observable versus descriptive invariant contract and qualified diagnostic mapping consumed by real enforcers |
| UM-03 | Implemented; qualification open | Settled request/result concepts; UM-02 only for promised failure mapping | Generated typed domain calls, binds, Core/result projections and materializers, including published-document consumers with private placement bindings |
| UM-04 | Implemented; qualification open | Existing serving protocol; settled implementation compatibility binding | Archived-run query/continuation/explanation/evidence meaning is compatible or explicitly refused |
| UM-05 | Implemented; qualification open | UM-03 signature/projection contract slice, not full caller migration; working PDF foundation for its consumer case | Model-bound Core companion/inference recipes plus published-address read/effect bindings and selected-section projection |
| UM-06 | Implemented; qualification open | UM-02 enforcement contract and UM-05 selected native expression recipes | Structured native declarations and eligible SQL-language bodies with versioned identity/dependency/admission |
| UM-07 | Implemented; qualification open | UM-06 first qualified desired product plus existing Alembic lifecycle | Frozen forward native transitions including changed consumer constraints/inserts/replay, before/after drift/ACL/recreation controls; old revisions unchanged |
| UM-08 | Implemented; qualification open | One settled UM-05 companion recipe and model/native signature metadata | Qualified projection type/dependency analysis with SQLGlot, unknowns explicit, used by UM-12 |
| UM-09 | Partial — UM-CA13; qualification open | Existing Settings and AnalysisScope owners | Non-default resources reach operations; supported lazy results enforce owner lifetime |
| UM-10 | Partial — UM-CA13; qualification open | UM-03/05 directional operation contracts and relevant UM-09 owners | Model-derived exact transfer/decoding used in actual publication and analytical read/export |
| UM-11 | Implemented; qualification open | Operation/state/binding contracts plus actual owner checks | CLI/MCP operation/prerequisite explanations; effects recheck atomically |
| UM-12 | Implemented; qualification open | UM-01/02 semantics, UM-05 projection dependencies, relevant UM-08 analysis | CLI/MCP semantic impact and declared consumer changes, with conservative unknowns |
| UM-13 | Implemented; qualification open | Existing validator outputs and an early shared diagnostic contract | Model/path/operation/scope-located diagnostic consumers preserving failure categories |
| UM-14 | Partial — UM-CA13; adoption/qualification open | Working producer and affected consumer products from each package | Remaining maintained callers migrated; replacement paths retired and supported archives/adoption reconciled |
| UM-15 | In progress | All selected functional scope and UM-14 final-source integration | Required functional/native/provider/nonfunctional union has applicable evidence; honest unresolved/benefit limits |

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
| UM-CA04 — UM-09/14 | Configured driver now reaches `companion_export.py:129–134`; snapshot import and batch hints are actual consumers. | Driver omission corrected; cancellation continuity is separately open as UM-CA13. |
| UM-CA05 — UM-08/12/13 | `projection_analysis.py:267–349` executes strict qualification/type/scope/lineage and relational clause dependencies; actual impact consumes the archive product. | Unknown helper/body semantics remain explicit; not universal semantic equivalence. |
| UM-CA06 — UM-13/14 | `ontology.py:985–1018` returns the shared located graph report and raw validation; shape/execution/nonconformance distinctions remain. | Broader actual-provider/consumer qualification at UM-CA10. |
| UM-CA07 — UM-13/14 | Invocation-local FailureContext carries known release/model/operation through CLI/MCP translation; structured native invariant bindings preserve cause. | No claim that every library error is normalized or every invariant has a qualified observer. |
| UM-CA08 — UM-06 | `native_catalog.py:96–244` supplies typed observed catalogs, consumed by native_objects; existing Inspector/Alembic owners retained. | Selected catalog mechanism delivered; no second desired catalog. |
| UM-CA09 — UM-03/14 | Generated columns match authoritative current stored metadata; separate read shapes do not own DDL. | Retain generation/static/runtime evidence scope. |
| UM-CA11 — UM-12/14 | `cli/regenerate.py:230–249` actually consumes shared impact/advice; class/helper gaps report unknown. | Richer known dependency closure is optional improvement I05, not a false-success defect. |
| UM-CA12 — UM-03/14 | Generated semantic NewTypes and nested completion IDs reach strict scalar/JSON materialization. | Static and runtime controls remain complementary. |
| UM-CA10 — UM-14/15 | Open qualification/adoption, not an implementation-complete series exit. Live observer coverage and stale-preflight controls retain their stated boundaries. | Complete exact applicable functional/provider/nonfunctional union and actual PDF/knowledge/query/report/export acceptance. Reuse independent reference obligations through their existing owners. |
| UM-CA13 — UM-09/10/14 | **Open implementation gap:** caller cancellation is registered only in ADBC; SQLAlchemy snapshot/source inspection and snapshot export are unregistered. | Coordinate backend-specific cancellation under one operation owner; qualify in-flight metadata, handoff and bulk cancellation with full settlement and no destination publication. |

### UM-CA13 evidence and closure

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

**Next:** resolve UM-CA13 through existing resource/transport owners; complete UM-CA10 without
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

**Implemented / bounded Tested, with UM-CA13 open.** Current semantic
compiler14/boundary12/execution23/archive3 is integrated; the audit above identifies the remaining
cancellation integration gap. ADR-0047's retirement removes historical readers/base runtime, installed registries,
old compiler/executor paths, aggregate/rendition/HTML persistence and the legacy test engine.
Generic database test fixtures now clone the current sealed semantic head; independent resource,
rollback, COPY/ADBC, extension, owner and cancellation expectations remain. Current locators,
scientific interpretation, rule/cascade, alignment and exact-value capabilities remain.
Schema-only compilation/boundary generation and exact artifact archiving remain non-executable;
execution and analytical operations require their bound model. No installed analytical-policy
fallback remains. Current query compatibility across retained current-format results remains.

Native91 retires36 relations and replaces their dependents before dropping tables. Native92 binds
the regenerated report-schema artifact. Native93 corrects retained empty OCR inventories and six
source-derived kernel bodies; native94 binds the final analytical source. All predecessors are
immutable. [Forward evidence](../design_review/evidence/2026-11-02_um-current-only-forward/README.md)
retains failed attempts and passing82→94 replay, no-op, empty candidate, exact catalog, source/ACL
refusal, restoration and caller-owned rollback. Rehearsal roles remain distinct from actual LOGIN.

Fresh owned corpus_pdf_20261102/OID16934542 is deployed through94. Actual admitter LOGIN archived
and admitted the statistics release; actual writer initialized siegrist-pdf; actual reader opened
its operation explanation. Defaults select this database/project; no completed result is selected.
Receipts: build/um-current-fresh-bootstrap. Full-PDF attempt1 exposed the incorrect nonempty OCR
inventory constraint; its cancelled state and settled processes are retained. The model correction
preserves [] versus absent/null in Arrow and preserves unknown/partial health;27 focused controls
passed. Attempt2 refused before conversion because the owned Nemotron endpoint was unavailable.
The restarted service has been shut down and its process group is absent. Fresh recognition and
five-section knowledge/query/report/export acceptance are not established by API readiness.

Four obsolete historical success cases were retired: populated0032 compiler10 reconstruction,
two native-closure old-head backfills, and aggregate-PDF historical backfill through an exported
old runtime. Frozen migrations, source fixtures and evidence remain; current archive/replay,
unsupported-ABI, native guard and independent semantic expectations remain. Other affected tests
were ported to current composed profiles, exact published pins and record readers. Invalid native
inputs retain independent expectations rather than weakening production guards.

**Verification:** warning-inclusive just types and whole-repository just ruff passed at
build/um-current-closeout-{types,ruff}-final.log, supplemented by scoped passing checks for the
last fixture repairs. Targeted analytical/resource, ABI/invariant/scope
and source CLI/reader checks passed; their receipts retain exact selections. The baseline final94
collection selected3191 nodes; the existing classifier recorded2806 passed and385 unresolved before
closeout repairs. Concurrent native cold bootstraps exhausted shared locks; their214 setup failures
were followed by serialized targeted checks with repaired native cases. The interrupted math shard leaves79 nodes
without a passing call. Original failed/interrupted receipts are preserved; package counts overlap
and are not summed. The last whole collection selected3187 nodes before two retired child checks were replaced by
four pure preparation cases; full required-union qualification remains open. The targeted closeout result is recorded below.

**Next executable work:** start the owned Nemotron service, verify its actual API/control readiness,
then run one fresh corrected full-PDF intake; resume the existing five-section knowledge workflow,
exercise actual query/report/export/evaluation consumers and complete the outstanding required
union. Reuse applicable final-source receipts; do not repeat passing checks merely after lint or
formatting. Additional PDF provider/evaluator/default acceptance retains its existing coordinator.

### Settled closeout evidence

The serialized targeted batch selected234 nodes:203 passed and31 failed. The two obsolete JSON
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
