# PostgreSQL capability leverage

**Status:** Planned; owns PG-00–PG-12 and investigations PG-I01–PG-I03. No product implementation is established by these documents.
**Created/revised:** 2026-11-01. **Target claims:** Proposed unless explicitly source-inspected below.
**Basis:** [integrated review O01–O15](../functional_reviews/postgresql-capability-leverage_2026-11-01.md) at `09d3125e1570df7c94ca357962107155cfdb939b`. Its audit explains rationale, not a second execution queue. This coordinator is the sole package/investigation/source-disposition owner for this series. The expanded implementation design below refines the initial investigation questions without changing their IDs.

## Outcome and scope

Produce a more coherent PostgreSQL realization of the semantic model: native-aware execution outcomes and resource ownership; reusable typed relational preparation; directional transfer profiles; native Alembic-backed object evolution; and useful analytical, operator and selected-source consumers.

The operator selected delivery, not discovery-only treatment, for typed published-data access, database description and selected-subtree exports. The concrete first consumers are companion-family Parquet export/DuckDB comparison, `ci db describe` for query/import preparation, and intact-section source export for scientific/extraction use. They are required capabilities of this series. Investigations settle technical realization, not whether to quietly omit them.

Latest-stable library upgrades are settled direction. Breaking interfaces or physical realizations of any scale may be proposed when they improve the target; preserving the current implementation or compatibility is not a ceiling. Domain meaning, truthful outcomes and evidence obligations must remain explicit when representations change.

This is a new undertaking. It neither updates another plan series nor adopts its unfinished work. PDF producer completion, whole-book validation, operational defaults, provider/reference grading and prior qualification remain outside. Existing published-record/claim/source interfaces are consumed as baseline capabilities. If a prerequisite is unavailable at execution, name that external prerequisite and continue ready work; do not add its repair to this series by implication. New consumers and regressions introduced here are this series' responsibility.

## Baseline and focused foundation assessment

**Source-inspected, 2026-11-01:** initial checkout `0be6e535`, refreshed through `2e24f8c0`, plus concurrent dirty library references and PDF source/plan/tests; refresh affected paths before execution. The integrated review's old package-state prose is not a current completion oracle. No product tests, deployment or performance measurements were run for plan authoring.

- `core/db/store.py` has one regular Psycopg pool with `close_returns`, lending through SQLAlchemy `NullPool`. Retain it for current row and publication consumers: there is no technical reason to duplicate physical inventory. Scope ADBC sessions explicitly when columnar work earns them.
- `semantic/publication.py::_publish` and store classification independently infer transport loss from missing SQLSTATE. Replace this premise with native cause plus operation phase, not a new universal retry framework.
- Fixed model metadata, `pdf_record_model`, Arrow publication and analytics already derive related typed forms. Unify stable source facts and directional preparation without inventing a universal schema/driver abstraction. Raw driver paths bypass SQLAlchemy Python processors.
- `PublishedPdfReader`, native event export and scoped source readers exist. Preserve their useful small-row and whole-native-output behavior; the new work is typed analytical families and an explicitly selected-context export, not initial PDF reader delivery.
- Native product authors combine domain SQL, mechanical inventories, replacement and admission. Existing Alembic history is reusable; use native Alembic extension interfaces for valuable missing lifecycle mechanics; the separate alembic-utils package is excluded.
- During authoring, `2e24f8c0` added modeled `semantic/pdf_publication.py` freeze/prepare/validate/seal and native products. These are source-inspected available contracts, not a claim of live deployment or full validation. Their prior missing-module observation is superseded for this baseline. Foundation/consumer checks use actual current contracts, retaining explicit external prerequisite failures without importing repairs or granting fixtures provider acceptance.

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

All rows start **planned**, not implemented. Supporting owners explain behavior and closure; this table alone owns execution state.

| Package | Inputs | Delivered capability / verification boundary |
|---|---|---|
| <a id="PG-00"></a>PG-00 | Current baseline and standing upgrade direction | Refresh affected baseline, update exact dependency family deliberately, retire reproduced obsolete adapters; affected regression union and `just ready` |
| <a id="PG-01"></a>PG-01 | PG-00 library realization | Verify native Alembic extension PG-I01 on one protected object family; selected mechanism and exact residual gap, not blanket product qualification |
| <a id="PG-02"></a>PG-02 | Cause/effect contract can be designed immediately; runtime checks after PG-00 | One phase-aware outcome route used by store/publication/refusals, with correct retry/receipt/refusal behavior |
| <a id="PG-03"></a>PG-03 | Current model and existing projection consumers | Prepared typed relational shapes and directional profiles used by analytics and one published-family operation |
| <a id="PG-04"></a>PG-04 | Working PG-02/03 for integration; PG-I02 current route resolved | Shared transfer preparation, preserved row COPY and integrated Arrow transfer with exact profile checks |
| <a id="PG-05"></a>PG-05 | PG-02 outcome semantics; existing resource owners | Owned cancellation/settlement, bounded admission settings and structured native diagnostics used by actual operations |
| <a id="PG-06"></a>PG-06 | Working PG-03/04 plus published-pin baseline | Typed input/relation/coverage/mapping-report batches, Parquet sink and pinned DuckDB comparison consumed end to end |
| <a id="PG-07"></a>PG-07 | Description contract; PG-03 only for model/query linkage | `ci db describe` structured physical/query description, optional estimates with clear provenance |
| <a id="PG-08"></a>PG-08 | PG-01 decision and current generated native products | Selected lifecycle delegation for new forward products, independent admission, own schema transitions |
| <a id="PG-09"></a>PG-09 | PG-01 object-boundary decision; active SQL consumers | Reusable source-qualified syntax facts and diagnostics; no historical-generator cleanup for its own sake |
| <a id="PG-10"></a>PG-10 | PG-I03 selection contract; working PG-05 and published source baseline | Streamed selected-source package for an intact section with required context and explicit omissions |
| <a id="PG-11"></a>PG-11 | Each changed producer plus its actual consumer | This series' migration/activation/retirement, no parallel paths left without a concrete reader |
| <a id="PG-12"></a>PG-12 | All selected functional scope including PG-11 | Final-source functional/provider/nonfunctional union for this series and honest benefit accounting |

PG-00 and PG-01 do not serialize all design work. PG-02/03 shared contracts, PG-07 report design and PG-10 selection design can progress independently. PG-06 does not wait for object-lifecycle replacement if the existing native authoring route already supplies its independently enforced projection. Shared editing surfaces still need a single integration owner. No package is a fixed agent roster.

## Investigations that decide implementation

| ID | Question and settling evidence | Consequence |
|---|---|---|
| <a id="PG-I01"></a>PG-I01 | Can the selected native Alembic extension preserve overload identity, function properties/search_path/role/grants, dependent view/trigger and exact admission? Inspect source, then one disposable authoring DB case if needed; explicitly check transaction ownership and discovery limits. | Use native Alembic Plugin/comparator/operation/render interfaces with SQLAlchemy and pglast. Alembic Utils is explicitly excluded by the operator; recreate a narrow missing lifecycle feature only for demonstrated value, with independent contract checks. PG-08 waits, other packages do not. |
| <a id="PG-I02"></a>PG-I02 | Does any new Arrow-input operation benefit from full ADBC-owned ingest/adopt versus Core/Psycopg/pgpq or server-native movement? Compare one actual input/profile including casts, effects, cancellation and recovery. | Current publication remains same-session Psycopg; no standalone import is added without a selected consumer. ADBC ownership is selected only for a complete operation with a concrete benefit, never by swapping a connection under another owner's temp tables. |
| <a id="PG-I03"></a>PG-I03 | Verify the selected section-source-context-v1 closure against incremental formula/source input preparation, including outside references, repeated occurrences and coarse/unknown geometry; the consumer owner now specifies membership and context rules. | Implement and independently test the selected-source-v1 membership/context/omission contract; revise its owned rule if the revealing consumer case fails. Never relabel a fragment as a complete Docling document. |

The expanded investigation disposition below records settled routes and remaining runtime evidence. Investigations must yield a choice, counterevidence or a named blocking contract gap with a bounded next decision. They are not unrestricted ecosystem reviews. Probes use existing evidence conventions only when needed; no additional audit campaign or benchmark framework.

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

## Current authoring checkpoint

Documents only. All PG packages remain planned; implementation and required runtime checks are **not_run**. Library capability evidence and current-code inspection informed the design; they are not qualification. Authoring validation receipts are recorded in the adoption/validation owner. Next execution work is PG-00, with PG-02/03 contract design and PG-01 preparation able to proceed on their actual prerequisites.

## Expanded implementation design and shared contracts

**Proposed revision, 2026-11-01.** This expansion consumes the same integrated review `09d3125e1570df7c94ca357962107155cfdb939b`, the original and added content of all seven PostgreSQL references, focused Context7/primary-source research and current source at `cfa009b2` plus relevant dirty PDF changes. No code state or qualification from those concurrent changes is claimed here. The support documents now contain the implementation visions; package-table rows are navigation and completion boundaries rather than sufficient specifications by themselves.

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

PG-I01 remains a bounded **runtime integration obligation**, not an open choice of lifecycle dependency. The selected chain is native Alembic Plugin comparison → custom operation payload → renderer/frozen history → implementation on the caller Connection → independent native admission. PG-01 exercises the representative family, its security properties and rollback before PG-08 migrates current forward families. A mismatch must identify the exact residual API/catalog/property defect; it does not reopen Alembic Utils adoption.

PG-I02 is **design-resolved for current scope**: resident SQL moves inside PostgreSQL; both integrated Arrow writers retain same-session Core/Psycopg/pgpq ownership; Python domain rows retain typed row COPY. No new standalone Arrow import is selected. A complete ADBC-owned ingest is reconsidered only if a concrete newly required input operation warrants it. It is not a required parallel implementation or an unconditional feasibility spike.

PG-I03's selection and context contract is developed in the consumer owner as **Proposed design**. PG-10 must exercise that contract against the current scientific/source input-preparation consumer, including outside references, repeated occurrences and unknown geometry. Failure of that revealing case requires revising the owned context rule before completing PG-10; it is not grounds to omit selected-source delivery or hide the case as unknown future scope. Design selection, implemented query and verified consumer remain different states.

### Practical execution route

Start with the deliberate dependency/workaround move and native extension representative preparation. In parallel design terms, PG-02's result transitions, PG-03's generated shapes and PG-07/10's request/result contracts can be developed from inspected source; this does not require product implementation to have finished.

Integrate the shared outcome and preparation contracts with their existing consumers before claiming those packages usable. PG-04 migrates both actual Arrow writers using their separate protected admission owners. PG-05 addresses current long operations, renewal and cancellation races. Deliver PG-06 and PG-10 against working published/read contracts, and PG-07 against the real read principal. PG-08/09 replace current forward authoring/syntax mechanics after the representative extension contract is proven. PG-11 participates with each changed producer; it is not permission to defer consumer migration to the end. PG-12 closes only after all selected capabilities, own transitions and affected consumers are covered by the required final-source evidence.

A materially missing external prerequisite is named at its existing owner. Continue independently ready packages without inventing a substitute semantic authority or importing the prerequisite's repair into this series. Shared editing surfaces need coordination even when capability dependencies permit parallel progress.

### Expected extension experience and execution fit

A new modeled companion field updates generated static/native/Arrow forms and the consumers that use its semantics. It should not require a handwritten second column registry. A new transfer layout changes a directional profile and its exactness checks, not publication replay policy. A new supported native property extends desired/observed comparison and admission with independent controls, not a new migration runner. These are the credible variations behind the boundaries; they do not schedule additional feature families.

Batch movement avoids JSON/dict/hex reconstruction for analytical consumers, while server-native set operations avoid exporting rows only to reinsert them. Preparation removes repeated stable work but introduces bounded retention/invalidation responsibilities. Snapshot capture holds read resources only through export, not local analysis. Cancellation and rollback preserve honest effect knowledge even when network loss prevents a hard cleanup deadline. These qualitative tradeoffs apply FP-04/05/07 and the efficient-architecture heuristics without a new cost model, telemetry framework or benchmark requirement.

All packages remain **planned**. The expansion changes design detail and resolves authoring choices; it establishes no library integration, database deployment, product acceptance or measured benefit. The next product execution is PG-00, with the nondependent contract work described above ready to proceed alongside it.
