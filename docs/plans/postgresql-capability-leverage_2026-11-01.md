# PostgreSQL capability leverage

**Status:** Complete — PG-00–PG-12 implemented and targeted Tested on 2026-11-01; merged into main at `7b39e1b0`. Original and supporting plan documents are retained.
**Created/revised:** 2026-11-01. **Target claims:** Implemented and targeted Tested as recorded below; quantitative performance benefits remain unmeasured.
**Basis:** [integrated review O01–O15](../functional_reviews/postgresql-capability-leverage_2026-11-01.md) at `09d3125e1570df7c94ca357962107155cfdb939b`. Its audit explains rationale, not a second execution queue. This coordinator is the sole package/investigation/source-disposition owner for this series. The expanded implementation design below refines the initial investigation questions without changing their IDs.

## Outcome and scope

Produce a more coherent PostgreSQL realization of the semantic model: native-aware execution outcomes and resource ownership; reusable typed relational preparation; directional transfer profiles; native Alembic-backed object evolution; and useful analytical, operator and selected-source consumers.

The operator selected delivery, not discovery-only treatment, for typed published-data access, database description and selected-subtree exports. The concrete first consumers are companion-family Parquet export/DuckDB comparison, `ci db describe` for query/import preparation, and intact-section source export for scientific/extraction use. They are required capabilities of this series. Investigations settle technical realization, not whether to quietly omit them.

Latest-stable library upgrades are settled direction. Breaking interfaces or physical realizations of any scale may be proposed when they improve the target; preserving the current implementation or compatibility is not a ceiling. Domain meaning, truthful outcomes and evidence obligations must remain explicit when representations change.

This is a new undertaking. It neither updates another plan series nor adopts its unfinished work. PDF producer completion, whole-book validation, operational defaults, provider/reference grading and prior qualification remain outside. Existing published-record/claim/source interfaces are consumed as baseline capabilities. If a prerequisite is unavailable at execution, name that external prerequisite and continue ready work; do not add its repair to this series by implication. New consumers and regressions introduced here are this series' responsibility.

## Baseline and focused foundation assessment

**Implemented and targeted Tested, 2026-11-01.** The authoring assessment used
`0be6e535`/`2e24f8c0` and concurrent reference material; execution started at `0878ba1b`.
The delivered source and selected acceptance are recorded below, rather than inferred from the
source review's original package-state prose.

- One Psycopg pool still lends through SQLAlchemy `NullPool`; separate ADBC analytical sessions
  have explicit ownership. Borrower-scoped cancellation, queue/deadline settings and settlement
  were integrated with existing publication, PDF read/COPY/validation and claim-renewal owners.
- The duplicated missing-SQLSTATE transport-loss heuristics were removed. Native cause,
  operation phase and effect knowledge now govern refusal, retry and receipt-resolution behavior.
- Generated static Core surfaces, release-scoped query preparation and shared directional
  `ArrowWriteProfile` facts replace repeated stable work. Both Arrow writers create fresh pgpq
  encoders; ordinary Python-row COPY keeps its existing consumer.
- Existing bounded PDF reads and complete native export remain available for their current
  uses. Four typed companion projections and the selected-source stream add the requested
  analytical and offline scientific consumers.
- Native Alembic Plugin comparison, frozen operations/rendering and caller-Connection execution
  now provide lifecycle mechanics, with explicit managed scope and independent catalog admission.
  The separate alembic-utils package was not added.
- Existing PDF freeze/prepare/validate/seal contracts supplied the publication foundation.
  Their deployed-book cutover, subsequent PDF-27/28 changes and RC12 rebuilding remain owned
  by the PDF series; this completion does not claim those workflows finished.

## Reading route and shared target

| Supporting owner | Responsibility |
|---|---|
| [Outcomes and lifetimes](postgresql-capability-leverage/outcomes-and-lifetimes.md) | Cause/phase/effect/recovery, physical inventory, cancellation and useful native diagnostics |
| [Typed realization and transfer](postgresql-capability-leverage/typed-realization-and-transfer.md) | Model-derived preparation, full relational intent, directional COPY/ADBC and typed published families |
| [Native object evolution](postgresql-capability-leverage/native-object-evolution.md) | Native Alembic extensions, residual model policy, syntax facts and own migrations |
| [Consumer capabilities](postgresql-capability-leverage/consumer-capabilities.md) | Parquet/DuckDB, bounded database description and selected-source export contracts |
| [Adoption and validation](postgresql-capability-leverage/adoption-and-validation.md) | This series' transitions, retirement, integration and acceptance |

The model owns semantic fields, scope, invariants and domain operations. A prepared relational realization carries stable typed structure; request bindings carry changing pins/filter values. Each execution owner controls its actual connection, transaction and reader. A projection can have row and batch executions without two independent definitions of its fields/visibility. Native object lifecycle registration is scoped to migration authoring; runtime admission independently checks actual instance protection. None of these conceptual boundaries requires a service, new DSL, persistent registry or hop per operation.

**Operator correction (2026-11-01):** do not add the separate alembic-utils package. Recreating particular valuable lifecycle features is permitted when a compelling case exists. Native Alembic extension APIs are the selected basis; the source review's companion-library choice does not override this direction.

**Library-informed design refinements beyond the review:** make failure effect-phase explicit rather than expanding a flat retry enum; derive a shared published-family projection for row/batch consumers rather than a second independent reader; retain model-owned dependency ordering rather than recreate a best-effort lifecycle solver; exclude helper behavior that commits implicitly from caller-owned migration transactions; and distinguish physical description, query output schema and domain schema in the public operator report.

## Packages and dependencies

Execution baseline `0878ba1b` (2026-11-01), private PostgreSQL18 socket/port55434; final source at `c5394eaa` is qualified by the targeted 319-case union. Supporting owners explain behavior and closure; this table owns current package state. The completion section identifies the final selected qualification and preserves the limits of earlier checks.

| Package | Inputs | Delivered capability / verification boundary | State |
|---|---|---|---|
| <a id="PG-00"></a>PG-00 | Current baseline and standing upgrade direction | Refresh affected baseline, update exact dependency family deliberately, retire reproduced obsolete adapters; affected regression union and `just ready` | Complete; SQLAlchemy 2.1.6/Alembic 1.20.1, exact default-defect adapter decision and readiness tested |
| <a id="PG-01"></a>PG-01 | PG-00 library realization | Verify native Alembic extension PG-I01 on one protected object family; selected mechanism and exact residual gap, not blanket product qualification | Complete; implemented and tested in the final 319-case targeted union |
| <a id="PG-02"></a>PG-02 | Cause/effect contract can be designed immediately; runtime checks after PG-00 | One phase-aware outcome route used by store/publication/refusals, with correct retry/receipt/refusal behavior | Complete; implemented and tested in the final 319-case targeted union |
| <a id="PG-03"></a>PG-03 | Current model and existing projection consumers | Prepared typed relational shapes and directional profiles used by analytics and one published-family operation | Complete; implemented and tested in the final 319-case targeted union |
| <a id="PG-04"></a>PG-04 | Working PG-02/03 for integration; PG-I02 current route resolved | Shared transfer preparation, preserved row COPY and integrated Arrow transfer with exact profile checks | Complete; implemented and tested in the final 319-case targeted union |
| <a id="PG-05"></a>PG-05 | PG-02 outcome semantics; existing resource owners | Owned cancellation/settlement, bounded admission settings and structured native diagnostics used by actual operations | Complete; implemented and tested in the final 319-case targeted union |
| <a id="PG-06"></a>PG-06 | Working PG-03/04 plus published-pin baseline | Typed input/relation/coverage/mapping-report batches, Parquet sink and pinned DuckDB comparison consumed end to end | Complete; implemented and tested in the final 319-case targeted union |
| <a id="PG-07"></a>PG-07 | Description contract; PG-03 only for model/query linkage | `ci db describe` structured physical/query description, optional estimates with clear provenance | Complete; implemented and tested in the final 319-case targeted union |
| <a id="PG-08"></a>PG-08 | PG-01 decision and current generated native products | Selected lifecycle delegation for new forward products, independent admission, own schema transitions | Complete; implemented and tested in the final 319-case targeted union |
| <a id="PG-09"></a>PG-09 | PG-01 object-boundary decision; active SQL consumers | Reusable source-qualified syntax facts and diagnostics; no historical-generator cleanup for its own sake | Complete; implemented and tested in the final 319-case targeted union |
| <a id="PG-10"></a>PG-10 | PG-I03 selection contract; working PG-05 and published source baseline | Streamed selected-source package for an intact section with required context and explicit omissions | Complete; implemented and tested in the final 319-case targeted union |
| <a id="PG-11"></a>PG-11 | Each changed producer plus its actual consumer | This series' migration/activation/retirement, no parallel paths left without a concrete reader | Complete; implemented and tested in the final 319-case targeted union |
| <a id="PG-12"></a>PG-12 | All selected functional scope including PG-11 | Final-source functional/provider/nonfunctional union for this series and honest benefit accounting | Complete; 319 targeted cases passed with 0 failures/errors/skips; relevant hygiene passed |

These dependencies describe the implemented composition, not a remaining execution queue. Shared outcome/preparation contracts were integrated before their dependent consumers; PG-07 remained independent of native lifecycle authoring. The final selected union covers the assembled responsibilities, not separate agent assignments.

## Investigations that decide implementation

| ID | Question and settling evidence | Consequence |
|---|---|---|
| <a id="PG-I01"></a>PG-I01 | Native lifecycle fit: overloads, properties, privileges, dependencies, discovery limits and transaction ownership | Settled: native Alembic extensions, frozen operations and independent catalog admission preserve the selected contract; native rollback/property/replay controls are in the final union. |
| <a id="PG-I02"></a>PG-I02 | Ownership of selected Arrow-input/publication operations | Settled: both writers use same-session Core/Psycopg/pgpq; resident movement stays server-native. A speculative standalone ADBC ingest was not selected. Reconsider only for a concrete new input operation. |
| <a id="PG-I03"></a>PG-I03 | Selected-section context closure for offline scientific preparation | Settled and tested: current hierarchy membership, all incident endpoints, original nested/ancestor recognition coverage, repeated outside references and explicit missing-input outcomes feed actual formula preparation. |

All three investigations have a recorded disposition. PG-I02 selected an ownership route rather than an additional feature; PG-I01 and PG-I03 have runtime acceptance in the final union. No investigation remains an open execution prerequisite.

## Source disposition

Source links below refer to the one [principal review](../functional_reviews/postgresql-capability-leverage_2026-11-01.md). Every item is accounted for without copying another plan's progress.

| Source item | New series route | Closure meaning |
|---|---|---|
| [O01](../functional_reviews/postgresql-capability-leverage_2026-11-01.md#O01) | PG-00 | Latest stable exact family; affected checks and deliberate workaround decisions |
| [O02](../functional_reviews/postgresql-capability-leverage_2026-11-01.md#O02) | PG-02/05 | Correct effects/recovery from acquisition through acknowledgement |
| [O03](../functional_reviews/postgresql-capability-leverage_2026-11-01.md#O03) | Baseline retained; PG-02/05 owner contracts | One inventory owner; transaction and borrower cleanup independently correct |
| [O04](../functional_reviews/postgresql-capability-leverage_2026-11-01.md#O04) | PG-03/04, PG-I02 | Directional preparation shared, exact transfer and native adoption preserved |
| [O05](../functional_reviews/postgresql-capability-leverage_2026-11-01.md#O05) | Baseline rows/native export retained; PG-06/10 | No gratuitous second small-row engine; new consumers delivered |
| [O06](../functional_reviews/postgresql-capability-leverage_2026-11-01.md#O06) | PG-03/06/08 | Whole query intent/validation realizations use native set capabilities where beneficial |
| [O07](../functional_reviews/postgresql-capability-leverage_2026-11-01.md#O07) | PG-01/08 | Lifecycle selection precedes custom operation machinery |
| [O08](../functional_reviews/postgresql-capability-leverage_2026-11-01.md#O08) | PG-09 | Shared syntax facts serve current consumers with original-source diagnostics |
| [O09](../functional_reviews/postgresql-capability-leverage_2026-11-01.md#O09) | PG-05; optional items below | Correct cancellation/settlement and useful native diagnostics |
| [O10](../functional_reviews/postgresql-capability-leverage_2026-11-01.md#O10) | PG-08/11 only for this series' transitions | Source-shaped migration and own cutover; no inherited PDF adoption task |
| [O11](../functional_reviews/postgresql-capability-leverage_2026-11-01.md#O11) | PG-03 | Stable structure reused; binding/catalog changes invalidate correct scope |
| [O12](../functional_reviews/postgresql-capability-leverage_2026-11-01.md#O12) | PG-01/08 | Native Alembic extension fit settled; valuable residual features bounded and tested |
| [O13](../functional_reviews/postgresql-capability-leverage_2026-11-01.md#O13) | PG-06 | Real Parquet and DuckDB analytical consumer, not API presence alone |
| [O14](../functional_reviews/postgresql-capability-leverage_2026-11-01.md#O14) | PG-07 | Operator prepares a query/import using bounded, honestly qualified metadata |
| [O15](../functional_reviews/postgresql-capability-leverage_2026-11-01.md#O15) | PG-10 | Selected-source export serves intact-section scientific/extraction consumption |
| RC01 | Correct physical/transaction owner description in this target | No edit to the former PDF staging plan is scheduled |
| RC02 | PG-02/03/06/10 contract versions and PG-08 enduring-owner decision route | Concrete interface/model changes documented before dependent behavior |

**Deferred with triggers:** zero-minimum regular pools on demonstrated intermittent-session burden; drain/callable-credential refresh when credentials/endpoints actually rotate; LISTEN/NOTIFY when a consumer needs wakeups beyond current reads; COPY backend progress when native metrics cannot answer actual ingestion diagnosis; direct C Stream/alternate dataframe integration on a selected consumer that avoids materialization; native composite/DOMAIN/range storage when an operation needs the semantics; middleware, sharding, two-phase, remote discovery and Rust transport only on a concrete participant/workload requirement. These are not completion requirements. Small bound ADBC reads remain conditional on an Arrow consumer outperforming the adequate Core route in total machinery/semantics, not a mandatory second interface.

## Decisions, authority and completion

Operator directions (2026-11-01): create this independent series; plan O13–15 for delivery; use latest stable; permit breaking target changes and improvements beyond the review. RC01 is a new-plan description correction, not an architectural pivot. RC02 is a contract-change envelope, not blanket acceptance of unspecified changes to semantic authority. No §B change is selected here. If execution reveals a concrete change to a governing rule, present that precise consequence for decision before its dependent behavior; routine dependency moves and breaking interfaces within the selected target need no repeated permission.

Apply FP-01–07 and applicable profile semantics qualitatively, especially authority, non-circular validation, exact versus approximate values, evidence reachability and workload fit. Compare necessary work, preparation, copies, transaction duration and recovery, not source-line counts. No quantitative benefit is claimed. The series is complete only with all required capabilities, affected consumers, own migrations/retirement and final-source qualification; a decision or probe is not implementation. [Adoption/validation](postgresql-capability-leverage/adoption-and-validation.md) defines the union and reporting.

## Current execution checkpoint

**Design-phase execution constraint (operator, 2026-11-01):** all data is regenerable. This is permission to prioritize the target during the current design phase, not a permanent product compatibility policy or an architectural decision. Compiler18 is the current execution contract. Fresh current creation and regenerated-data journeys replace historical-reader and retained-data upgrade obligations. Reject obsolete execution products with a regeneration requirement. Frozen migrations, plans and receipts remain as history without ongoing compatibility support. This boundary does not authorize changing the main database.

**Merged and qualified, 2026-11-01.** Execution ran in the separate
`work/postgresql-capability-leverage` worktree from `0878ba1b`. Main's documentation changes
through `72970e40` were integrated before fast-forward merge at `7b39e1b0`; the completion
handoff is `b853a345`. All 11 pre-existing dirty library documents were preserved. The merged PG production/test snapshot matched qualified source `c5394eaa`. Subsequent or
concurrent PDF-27/28 production changes are outside this completion record and require their
own qualification.

The private PostgreSQL18 instance used port55434, a private socket, extension-only
`cs_pg_template`, bootstrap-only `pgpl_bootstrap`, ordinary CREATEDB maintenance `paul` and
restricted semantic principals. It was stopped and the merged worktree/branch removed.
These are retained receipt coordinates, not a live endpoint. Research inputs, candidate artifacts
and original `build/pg*` logs are archived under `build/postgresql-capability-leverage/` in main.

Dependency commit `3a0365a4` moved SQLAlchemy to 2.1.6 and Alembic to 1.20.1; the other selected
libraries were already current. The exact upstream callable-default comparison defect remained
reproducible, so the narrow adapter was retained. New head `semantic_pg_20261101` extends the
frozen semantic_0065 chain with ten managed objects and compiler18 admission; old migration
bytes were not edited. Fresh current realization/regenerated data, not retained-data upgrading,
formed the adoption boundary.

The final 319-case targeted run passed after directly affected borrower, native-authoring,
error-taxonomy and ABI expectations were reconciled. Ruff, Pyrefly, dependency checks and
readiness passed; main readiness also passed after integration. The interrupted broad run and
unrelated baseline failures remain preserved without acceptance credit. No main database
migration or PDF RC12 cutover is claimed.

## Expanded implementation design and shared contracts

**Implemented realization, 2026-11-01.** The original expanded design drew on review `09d3125e1570df7c94ca357962107155cfdb939b`, all seven PostgreSQL references, Context7/primary sources and authoring baseline `cfa009b2`. The supporting documents now identify the delivered APIs, selected departures from sketches and applicable acceptance. The package table is the single completion owner; illustrative examples do not supersede executable declarations.

### Shared contract ownership

| Contract/product | Definition owner | Producer and consumers |
|---|---|---|
| Physical cause, phase, effect knowledge and settlement | [Outcomes: concrete execution contract](postgresql-capability-leverage/outcomes-and-lifetimes.md#concrete-execution-contract--pg-02) | Storage/native adapters observe cause; publication/read/renewal owners add phase/effects; refusal and CLI/MCP reporting consume the result |
| Generated static surfaces, prepared expressions and directional profiles | [Typed realization](postgresql-capability-leverage/typed-realization-and-transfer.md) | Model/compiler prepares stable source facts; current Arrow writers and published-family operations consume operation-specific forms |
| Desired native object, frozen operation input and syntax facts | [Native evolution](postgresql-capability-leverage/native-object-evolution.md) | Current forward generators feed native Alembic comparison/rendering; migrations execute frozen payloads; deployed catalog admission remains independent |
| Published pin, companion request/manifest and comparison meaning | [Consumer capabilities](postgresql-capability-leverage/consumer-capabilities.md) | Shared source-export service and CLI consume protected typed functions, write detached files and feed DuckDB |
| Scoped database description and selected-source package | [Consumer capabilities](postgresql-capability-leverage/consumer-capabilities.md) | Current read authority and native source operations feed structured CLI reports and incremental scientific input preparation |
| Adoption state and required final evidence | [Adoption and validation](postgresql-capability-leverage/adoption-and-validation.md#executable-adoption-route--pg-0011) | Every changed producer migrates its consumers; coordinator retains combined disposition |

These are information ownership boundaries, not a requirement for a new class/module/service for every row. Runtime representations may remain ordinary immutable values and functions. Concrete schemas, examples and meaningful limits are explained at their single owner. Generated declarations derive from the executable model, while independent expected fixtures challenge the model/compiler's realization.

### Selected design choices and alternatives

**Outcome translation is separate from recovery policy.** Native adapters can recognize `PoolClosed`, queue pressure, cancellation and invalidation; they cannot infer whether a domain operation committed. PG-02 supplies explicit phase transitions and retains publication's immutable identity/receipt protocol. This removes the duplicated missing-SQLSTATE inference without adding a universal retry engine. Supporting acceptance distinguishes translation tests from durable-effect observations.

**Stable preparation is operation-shaped.** Generate static Core column surfaces and retain reusable expression/profile structure at the model/compiler lifetime. Changing request values remain binds. Keep Engine statement caching for normal execution; reuse expression construction for direct ADBC literal compilation without pretending that path uses Engine caching. Fresh encoders and physical-session state never become model-lifetime caches. Ordinary fixed family queries do not need an additional lambda cache.

**Native extensions supply lifecycle mechanics; application policy stays explicit.** Alembic comparator dispatch, operation containers, rendering, history and execution replace current repeated mechanical orchestration. The application supplies exact managed scope, overload/security/dependency meaning and independent native admission. There is no assumption that parsing or an empty autogenerate diff proves native equivalence. Alembic Utils stays excluded even where its former review lead supplied a useful feature idea.

**New consumers have distinct physical routes.** Four protected typed family functions feed one coherent snapshot capture, closed Parquet files and a detached manifest; DuckDB runs after database resources are released. Operator metadata uses supported discovery/schema/statistics interfaces and reports visible scope honestly. Selected-source JSONL uses ordered native events and declared context closure; it is an application-owned source projection, not an ADBC serialization feature. Existing bounded Core rows, row COPY and complete native JSON remain where they retain actual consumers.

### Investigation disposition after design expansion

PG-I01 is **settled, implemented and targeted Tested** in the final 319-case union. The selected chain is native Alembic Plugin comparison → custom operation payload → renderer/frozen history → implementation on the caller Connection → independent native admission. PG-01 exercised representative security/dependency/rollback behavior, and PG-08 migrated current authoring to that same mechanism. A mismatch must identify the exact residual API/catalog/property defect; it does not reopen Alembic Utils adoption.

PG-I02 is **design-resolved for current scope**: resident SQL moves inside PostgreSQL; both integrated Arrow writers retain same-session Core/Psycopg/pgpq ownership; Python domain rows retain typed row COPY. No new standalone Arrow import is selected. A complete ADBC-owned ingest is reconsidered only if a concrete newly required input operation warrants it. It is not a required parallel implementation or an unconditional feasibility spike.

PG-I03’s selection and context contract is implemented with a revealing native formula/table consumer. Independent implementation review identified missing scoped recognition coverage and nested-section coverage; their repairs passed the rich native/CLI case and independent focused reassessment. The final 319-case union includes the actual selected-source service/CLI and offline scientific input-preparation consumer with outside references, repeated occurrences and unknown geometry. The corrected closure is implemented and tested; full-book inference, provider grading and database cutover remain outside this series.

### Practical execution route

Execution completed the dependency/workaround decision, shared cause/phase/effect and
preparation contracts, both current Arrow writers, existing lifetime owners and all three new
consumers. Native authoring/syntax integration and the frozen current head were then validated
with actual catalog admission and caller rollback. Consumer migration accompanied the relevant
producer changes; PG-11 was not deferred as a separate unimplemented phase.

Final-source maintenance preceded the selected 319-case qualification. The originally attempted
broad suite was interrupted after the operator clarified that the non-green PDF/repository
baseline was not a completion gate. Only directly affected contract expectations were adapted;
existing unrelated failures were not absorbed into the plan. There is no remaining execution
queue in PG-00–PG-12.

### Expected extension experience and execution fit

A new modeled companion field updates generated static/native/Arrow forms and the consumers that use its semantics. It should not require a handwritten second column registry. A new transfer layout changes a directional profile and its exactness checks, not publication replay policy. A new supported native property extends desired/observed comparison and admission with independent controls, not a new migration runner. These are the credible variations behind the boundaries; they do not schedule additional feature families.

Batch movement avoids JSON/dict/hex reconstruction for analytical consumers, while server-native set operations avoid exporting rows only to reinsert them. Preparation removes repeated stable work but introduces bounded retention/invalidation responsibilities. Snapshot capture holds read resources only through export, not local analysis. Cancellation and rollback preserve honest effect knowledge even when network loss prevents a hard cleanup deadline. These qualitative tradeoffs apply FP-04/05/07 and the efficient-architecture heuristics without a new cost model, telemetry framework or benchmark requirement.

The final selected union establishes this series’ targeted functional/native qualification. Earlier isolated checks retain their original scope, and none of these results establishes a measured performance benefit or completion of another plan.

## Completion and retained evidence

**Implemented and targeted Tested, 2026-11-01.** All PG-00–PG-12/O01–O15 delivery scope is complete.
PG-I01 is settled by the native extension/admission/caller-rollback controls; PG-I02 is resolved
for same-session Psycopg/pgpq writers without a speculative standalone ingest; PG-I03 is settled
by selected-source production, original scoped coverage and offline scientific input preparation.
Independent consumer reassessment confirmed the three identified comparison/coverage defects
were corrected. Existing PDF-27/28 and RC12 scope remains with its coordinator.

| Evidence | Outcome and applicability |
|---|---|
| `build/test-receipts/qualification/pg-series-final-c5394eaa` | **passed:** 319 tests across 32 explicitly selected affected test files;0failures/errors/skips,89.560s; actual private PostgreSQL/ADBC/pgpq/Parquet/DuckDB and CLI consumers included. `invocation.json` and collection events preserve the exact command, source and selection. |
| `build/postgresql-capability-leverage/pg-targeted-{ruff,types}.log` | **passed:** whole-tree Ruff/Pyrefly after the directly affected test adaptations; no unrelated repairs. |
| `build/postgresql-capability-leverage/pg-scope-deps.log`, `pg-final-ready.log` | **passed:** exact dependency-family checks and environment readiness. |
| `build/postgresql-capability-leverage/pg11-final-{freeze,adoption-tests}.log` | **passed:** ten frozen native objects, independent admission, rollback, fresh current18/regenerated-data publication and recurring authoring; seven adoption cases. |
| `build/test-receipts/qualification/20261101T131200Z-2640716` | **interrupted:** broad exploratory run retained 36 failed/2615 passed/9 skipped before normal SIGINT/fixture teardown. No broad acceptance credit; only direct PG contract fallout was repaired. Existing PDF, old-reader, corpus and host-authentication failures were not imported into this series. |
| `build/postgresql-capability-leverage/pg-plan-doc-closeout-links.json` | **passed:** 89 local references and 20 Markdown anchors resolved across the coordinator and five supporting documents with zero errors. Separately, source inspection reconciled actual APIs/ownership and removed obsolete pending-state prose. Documentation-only correction; the existing319-case result remains applicable. |
| `build/postgresql-capability-leverage/pg-scope-docs-check.log` | **failed:** pre-existing/out-of-scope publication targets;0errors in this series’ changed plan/architecture documents. No blanket documentation pass claimed. |

Receipts originally produced under isolated `build/pg*` are retained under
`build/postgresql-capability-leverage/`; the final and interrupted qualification directories keep
their standard paths. Frozen migration artifacts and all plans remain committed. The private
validation server was stopped and the merged worktree/branch removed; no shared application
cluster or deployed PDF database is migrated. Main database cutover remains with PDF RC12.
No Rust product scope changed, and no Rust functional coverage is claimed. Structural improvements
are implemented/tested; no speedup, bounded-memory or hard-cleanup-deadline measurement is claimed.
