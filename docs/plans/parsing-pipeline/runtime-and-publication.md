# Runtime preparation and protected parsing-product publication

**State:** Implemented mechanisms; assembled acceptance remains with PP-10, 2026-10-30.
**Scope:** PP-08 and PP-09. Current package state, opportunity dispositions and execution order
belong to the [coordinator](../parsing-pipeline_2026-10-30.md).

## Result and ownership

Extend the current operation/preparation/publication path so useful parsing work is prepared at
its actual validity lifetime, demanded capabilities determine execution, and immutable outputs
become visible only under their declared coverage and protected effect contract. This realizes
functional-review [O04](../../functional_reviews/parsing-pipeline_2026-10-30.md#O04) and
[O07](../../functional_reviews/parsing-pipeline_2026-10-30.md#O07), with O01/O02/O03/O06 custody,
identity and validation obligations at their runtime boundaries.

PP-01 owns the source, representation, dependency, demand, outcome and operation meanings;
PP-04 owns persisted product structure and the explicit selected-reader contract. PP-03/PP-05/
PP-06/PP-07 own actual native producers. PP-08 realizes preparation and resource ownership without
becoming another semantic registry or task manager. PP-09 integrates those concrete products into
protected completion, publication and historical reads. Neither package makes a lexical token
into a durable task or requires a SQL lookup per parsing decision.

The [connected target](../../functional_reviews/parsing-pipeline_2026-10-30_target-model.md)
distinguishes immutable identity from a live resource handle, and computational lifecycle from
semantic outcome and coverage. These distinctions govern both packages. Contract-significant
changes flow through PP-00's authority route before dependent implementation relies on them.
Existing D3/D4/D6 and publication/reader decisions remain current until deliberately revised.

## Examined baseline and focused foundation assessment

Static source inspection for planning used main `b3a8313` on 2026-10-30. The functional review's
2026-10-30 library research supplies installed/tagged-source capability findings, not runtime
qualification of the proposed composition.

| Current owner | Existing mechanism and what this plan changes |
|---|---|
| `semantic/prepare.py` | `prepare_release` separates immutable pure inputs and a bounded cached compilation; database state is not that cache's input. Reuse its admitted prepared contracts rather than opening or compiling policy inside a token loop. |
| `semantic/analysis_contracts.py` | Prepared interpretation context and stage keys already bind interpretation dependencies. Extend their finite supported recipes and missing-declaration semantics; do not create a parallel preparation framework. |
| `methods/math/prepared.py` | `PreparedMathInput.reading()` shares a reading and does not retain timeout failure; `symbolic_value()` lazily constructs and retains the value or unrepresentability. Ambiguity resolution in the underlying grammar can still construct SymPy, so decomposition-only execution requires actual adapter separation. |
| `methods/math/grammar.py` | The deadline uses `signal.SIGALRM`/`setitimer` and requires a process main thread. The finally path disarms its timer and restores its handler. A generic thread executor cannot satisfy this mathematical contract. |
| `methods/math/methods.py`, `orchestrate/semantic.py` | Current mathematical work executes through source methods and protected semantic task operations; M09/M11/M13 consume real interpreted observations. Reuse the operation graph and native attempt/source fences. |
| `semantic/operations.py` | `complete_unit_result`/`store_rendition` and the current `BoundReader` bind run-selected products. `text_layouts` joins the chosen run and `coalesce(reused_task_id, id)`; multiple builds refuse. Extend that actual selection pattern to new products. |
| `semantic/publication.py` | `stage_batch` uses typed psycopg COPY on the SQLAlchemy-owned connection. `publish_on_connection` stages inside the caller's SERIALIZABLE transaction without committing. `_publish` owns immutable-batch retry and receipt lookup after ambiguous connection loss. Preserve these protections where the new products use this route. |
| `semantic/runtime.py`, `semantic/archive_reader.py`, `semantic/source_frames.py` | Purpose-specific resource opening, supported immutable archive reads and effective-origin frame custody already have owners. Extend their actual callers rather than inventing a generic source lifetime or compatibility service. |

The relevant design assessment uses core 3.3, efficient-architecture guidance and code-intelligence
1.4: prepare stable dependencies once, reduce unused work before multiplying workers, retain useful
intent across native calls, keep expensive computation outside effect exclusion, and preserve
actual coverage/evidence on read. No broad audit, proof machinery, throughput estimator or new
alignment gate follows. Performance benefits remain hypotheses until measured; known unnecessary
reconstruction is still a reason to choose the simpler physical route.

<a id="PP-08"></a>
## PP-08 — Demand-driven preparation and owned native execution

### Prerequisites and useful first delivery

PP-01's admitted demands, stage dependencies, capability/result dimensions and supported operation
bindings are enough to begin. Existing algorithms can consume prepared inputs before the complete
new decomposition/storage pipeline exists. Connect new adapters as their individual PP-03/05/06/07
products become executable; do not wait for their whole documents or PP-09. A producer supplies its
actual capability, dependency recipe, ownership/lifetime and outcome contract before integration.

For one operation, consume pinned source/product references, the admitted release, exact frontend/
profile/native support and the requested capabilities. Prepare only prerequisites required by that
demand, execute native kernels over owned immutable inputs, and return products plus typed semantic
outcome, coverage, diagnostics and dependencies. Local intermediate work need not become durable
attempt rows. New operation support remains independently implemented and admitted; release data
cannot enable an absent algorithm by declaring it available.

### A. Preparation granularity and native handles

Separate stable release/context preparation from source syntax and from question-specific
assessment. Reuse compiled source profiles/selectors, supported grammar/context, macro selection,
validator/TypeAdapter objects and configured linguistic models at their actual dependency scope.
Keep source-bound layouts with their producing representation/build; reuse relative pure
computational products across different anchors only when the complete interpretation inputs
match, then attach each occurrence's own coordinates and evidence. Shared symbolic object identity
must never collapse two source occurrences.

Use current operation/comparison/rendition owners and ordinary immutable products/maps. Extend
bounded owner-local preparation where it removes demonstrated reconstruction; introduce neither a
global cache service nor durable caching of every parse alternative. A new cache needs a real
reuse scope and bounded retention. Coalesce equivalent in-flight requests only when cancellation
and remaining consumer ownership are explicit. One caller cancelling shared work cannot destroy
another caller's required result.

Keep lxml trees, spaCy objects, Lark parser/forest state and SymPy values in a compatible native
owner. If several demands can be served while that tree is live, compose their products there
instead of serializing an all-purpose dictionary and rebuilding another tree. Retain durable
decomposition only where subsequent independent operations need it. A printed formula, `srepr`
or pickle alone is not a supported executable interchange ABI. Worker handoff transmits compact
source/product references or immutable input values; never queue live connections, trees, Docs or
release resource handles as if immutable IDs made their lifetime safe.

### B. Dependency keys and honest reuse

PP-01's recipes own which dependencies affect meaning. Implement those recipes in current
preparation/task identity boundaries and distinguish reusable computation from the provenance
needed to cite a particular output. The following are required distinctions, not independent
hand-maintained key lists:

| Prepared result | Result-affecting inputs to bind under its recipe |
|---|---|
| Source decomposition/structure | Source/representation identity, decoding and frontend/grammar revision, repair/ambiguity recipe, native implementation/support and relevant profile. |
| Canonical projection/layout | Selected structure/product, source conventions, exclusion/separator/normalization recipe, token/sentence configuration and implementation. |
| Mathematical interpretation | Syntax identity and kind, effective macros including defaults/fallback definitions and their custody, declaration/binding scope, absent declarations, assumptions and interpretation support. |
| Assessment | Selected interpretations, named question, conditions/domain/definedness, evidence policy, algorithm version, precision/sampling where relevant and any reference-side inputs owned by that assessment. |
| Quote/graph/derived view | Actual selected population and projection/placement recipe, selector scope, candidate policy, mappings and relevant native implementation. |

Adding a previously absent function declaration for `f` must invalidate a reading of `f(x)` even
though the source bytes and previously found declarations match. A macro fallback edit must
invalidate expansions using it; shadowed/unconsumed definitions need not invalidate a result when
the admitted recipe can establish that independence. Unknown dependencies conservatively miss or
refuse; they are not assumed irrelevant. Incidental task IDs need not invalidate substitutable
pure computation, but build-specific mapping claims cannot be reused as rendition-only facts.

Timeout and cancellation are attempt/resource outcomes. `PreparedMathInput`'s present non-caching
of timeout failures is a useful baseline: a later admitted budget may succeed. Do not make a
timeout into permanent unsupported semantics. A persisted attempt may retain its failure without
becoming a reusable complete result. Scope retries to the actual failed computation/effect owner;
do not multiply a worker retry by a publication retry and an orchestrator retry without reason.

Independent reference preparation remains isolated. Gold/reference data cannot seed source
recognition, declaration inference, macro selection or quote placement. Source and reference keys
may share a computational mechanism, but retain distinct inputs, evidence policies and custody.

### C. Capability demands and observable states

Implement separate useful requests for decomposition, structure, occurrences, interpretation,
symbolic values and particular assessments, preserving the actual prerequisite graph. A lexical
inspection must not perform hidden Earley recognition, construct SymPy objects or run numerical
assessment. Fix that at the producer boundary rather than exposing a `lazy` flag over work that
still happens in ambiguity resolution. PP-06 owns mathematical native separation; PP-08 ensures
dispatch and preparation do not eagerly defeat it.

Keep work state (not requested, pending/running where needed, available, failed, cancelled) apart
from semantic status and coverage. An available interpretation can be ambiguous/unsupported/
invalid/unknown, and a product can have partial coverage. An unevaluated integral is an available
symbolic object, not a completed integration assessment. State names and legal transitions come
from PP-01 and existing execution projections, not another executor-specific lifecycle table.

M09 `extract.math` and M11 `normalize.formula` retain their required interpreted results until an
explicitly versioned method/output redesign migrates M13 and every affected observation, scope,
packet/query and evaluation consumer together. A faster decomposition-only path cannot satisfy
the old contract by changing a label. Demand composition preserves lexical evidence even when
interpretation fails; partial support does not silently satisfy a complete-result request.

### D. Workers, deadlines and cancellation

Use the repository's Python **3.14.10** runtime. The review's 3.15.2 guide is orientation only.
Start with inline/native batching for current useful work; choose worker processes or native
threads only from the actual kernel and its isolation/deadline requirements. Mathematical
SIGALRM work runs in a process main thread, either the existing inline caller or the main thread
of an owned worker process. Off-main-thread invocation retains a typed refusal/failure rather
than silently dropping its deadline. Nested deadlines must have an explicit owner/composition;
do not let one stage accidentally disarm another stage's timer.

For useful process batching, evaluate `ProcessPoolExecutor` initializer/initargs to prepare
worker-local immutable context/models once, and Python 3.14 `Executor.map(..., buffersize=...)`
with a meaningful `chunksize`. `buffersize` bounds submitted not-yet-yielded work for map;
`chunksize` affects process-map grouping, not a universal bound for all executors. Ordered map
results can retain later results behind a slow earlier item; use an owned bounded submit/collect
route if unordered completion is semantically allowed and materially avoids that retention.
Transport source-shaped batches and compact outputs rather than many per-token futures.

Choose native thread execution only for a kernel whose GIL/ownership behavior and cancellation
contract actually permit it. Account for spaCy/other native thread pools before multiplying process
workers. `Language.pipe(as_tuples=True)` supplies native batching and context association for
selected linguistic components; it is not permission to retain Docs outside their owner. Select
spaCy `memory_zone` only for actual long-lived worker retention needs and keep returned Docs,
Tokens, Spans and Lexemes inside the zone. No 3.15-only executor feature, free-threading,
subinterpreter, shared-memory or distributed-worker machinery is selected by API availability.

`Future.result(timeout=...)` stops waiting; it does not stop the computation. `shutdown` with
`cancel_futures=True` cancels pending work, while running work still requires completion or owned
termination. Python 3.14 `terminate_workers()`/`kill_workers()` affect a whole process pool; do not
use them as an individual-job timeout while the pool serves other consumers. Where a hard
independently owned deadline is required beyond the mathematical timer, evaluate a separately
owned process and `multiprocessing.connection.wait`/process sentinels rather than pretending
a shared-pool Future can be killed independently. Select this extra isolation only for the
concrete requirement; an inline bounded kernel may remain simpler.

Cancellation stops admission, cancels pending owned work, settles/drains or terminates owned
running work according to its contract, closes worker/native resources and reports all relevant
failures before re-propagating cancellation. Preserve completed immutable products still needed
by another consumer; retain attempt diagnostics and explicitly incomplete coverage. Worker death
must not publish partial outputs, leak resource handles or bypass the current protected lease/
attempt completion fence. Build/publication readiness is separate from worker exit status.

### Completion and scoped acceptance

Deliver preparation and migrated call sites together: ingest/profile/layout preparation,
mathematical methods and assessments, quote/scope preparation, selected graph/extraction kernels
and their current orchestrator readers, according to each implemented contract. PP-10 owns final
adoption and required-union qualification, not leftover inner consumers of a changed PP-08 API.

Targeted verification must expose: decomposition with recognition/symbolic work not invoked;
repeated requests sharing compatible preparation; changed/absent declarations, effective macro,
profile and algorithm versions invalidating the right product; two anchors sharing computation
without sharing occurrences; timeout retried with a changed budget; off-main-thread mathematics
refusing; worker initialization and meaningful batch ordering; cancellation with pending and
running work; and reference inputs unable to enter source preparation. Use independent expected
states and instrument only enough to answer whether forbidden work or repeated construction ran.
No standalone scheduler/cache framework or recurring performance campaign is needed.

Native worker tests and existing mathematical/preparation tests under
`python/corpus-structure/tests/math/`, `tests/llm/` and `tests/semantic/` are likely test homes;
choose commands from the actual implementation. Process cancellation acceptance requires real
owned processes, not a mocked executor labelled passed. Preparation/throughput measurements are
separate from functional correctness and remain unclaimed until representative execution.

<a id="PP-09"></a>
## PP-09 — Seal, publish and read build-bound parsing products

### Prerequisites and publication input

Start from PP-04's implemented product storage, identities and reader selection, PP-01's admitted
effects/outcomes, and concrete produced products from the relevant PP-03/05/06/07 slice. Require
the corresponding PP-08 lifetime/dependency/cancellation support where that producer uses it.
Do not wait for every optional adapter or runtime mechanism. PP-09 can integrate HTML custody
first and later mathematical/view products against the same protected boundary, while their
remaining obligations stay visible in the coordinator.

The publication input is a coherent immutable build/product set: source and representation
references; partition/structure/mapping products where required; actual recipe/native-support
and release/dependency bindings; coverage, typed outcome and diagnostics; and the current
operation/attempt authority. Preparation can produce this outside the write transaction.
Unavailable required support refuses before pretending the set is publishable. An explicitly
partial product may be published only under an admitted partial-product contract whose readers
cannot consume it as complete; required full partition/fidelity obligations remain open.

### A. Pure preparation followed by protected effects

Extend `complete_unit_result`, `store_rendition` and the applicable protected SQL routines/model
effects together. PP-04 supplies typed storage and product integrity; PP-09 supplies atomic
visibility and effect/attempt/source fencing. Keep parsing, tokenization, model construction,
large graph work and symbolic evaluation outside SERIALIZABLE effect exclusion. Before commit,
the native operation verifies the actual selected source snapshot, admitted release/support,
attempt/holder, dependency binding and required product coherence. A short transaction is safe
because it checks those premises, not because the earlier pure computation was trusted forever.

Use set-based SQLAlchemy Core DML and typed staging for logical sets. Where products enter the
existing `PublicationBatch` path, retain psycopg COPY on the same SQLAlchemy-owned connection,
bound values and `publish_on_connection`'s no-commit contract. Do not create a database round trip
per lexical item or stage. Apply native identity/range/ordering/endpoint/representation/build
constraints where PP-04 admits them; generated shape validators alone cannot enforce cross-record
custody. Carry already established immutable properties through unchanged products, rechecking
only new uncertainty and live effect premises at their owning boundary.

Seal the product set and expose its completion atomically with the required task/result effects.
No successful process exit, partial staging, diagnostic payload or sequence of Python writes is
equivalent to protected completion. A failed mapping build may preserve complete lexical custody
under a distinct supported product outcome, but cannot publish a complete exact-provenance claim.
Source bytes remain retrievable even if interpretation or decoding fails.

### B. Retry, crash and historical custody

Retain one publication retry owner. Reuse the exact immutable identity/content when retrying a
serialization/deadlock failure or resolving ambiguous connection loss; `lookup_receipt` must
distinguish the same committed batch from an identity reused for different contents. The current
receipt-first replay behavior must not become a back door to new writes under unsupported
historical contracts. Parsing retries and publication retries have separate scopes; recovering a
commit receipt does not require repeating successful expensive preparation.

Respect the existing deployment's asynchronous-commit policy: transactional acknowledgement is
not a new crash-durability promise. An interrupted pre-commit build exposes no complete result;
an ambiguous post-commit client outcome resolves through its receipt. Lease expiry/reclaimed
attempts use existing native fences so a late worker cannot attach products to a new attempt.
Retain failure/interruption diagnostics without treating them as reusable successful products.
No new durable staging/task service is required for disposable preparation.

Forward schema/routine migrations preserve frozen migration bytes and archived identities.
Changed implementation or schema support has its own compatibility/admission meaning; never
reinterpret an old product through the newest recipe because its payload shape is readable.
Retain archived release/native-support/configuration custody needed by historical inspection.
Reading a supported historical ABI does not authorize new writes, activation or admission.
Do not migrate unrelated historical databases merely to qualify this parsing series.

### C. Explicit reader selection and consumer migration

Extend the current `BoundReader.text_layouts` effective-origin pattern from PP-04. A run/build
selection identifies the producing decomposition, mapping, structure and interpretation products
as well as any shared rendition. Resolve explicit `reused_task_id` origins; refuse incompatible
or ambiguous candidates rather than selecting the newest build. Missing product support has a
typed availability/remediation result. Canonical reconstruction is permissible only for a
consumer whose contract needs that compatible canonical projection; it cannot fabricate original
source decomposition or exact mapping evidence.

Two parser configurations may produce identical canonical text and the complete segment/macro
content used by rendition identity while producing different diagnostics/source mappings. Share
the rendition under existing identity rules and retain separate builds/products. A changed
canonical text/segmentation creates new rendition/anchor identities. Never overwrite historical
anchors or one build's provenance to simplify reading. Historical demand binds the archived
source/release/configuration, not current defaults or a newly discovered macro environment.

Migrate actual source-product consumers with the boundary: ingest/run completion, text layouts
and sentences, mathematical observation preparation, scope/binding, quote placement, source frames
and packets, query/export and reference/evaluation opening where their input bindings change.
`semantic/source_frames.py`'s immutable effective-origin custody and packet hash validation remain
applicable. A frame containing canonical sentences must pin the associated product selection when
it also serves original-source explanations. Do not add another payload copy per quote to evade
selection. Reference evaluation keeps its separate prepared inputs and evidence/grading policy.

### Completion and scoped acceptance

Use real PostgreSQL native tests for the protected boundary and the actual runtime principal;
mocked publication cannot establish passed. Suitable acceptance scenarios include:

| Trigger | Required result |
|---|---|
| Complete coherent product set | One protected completion exposes source/build/products with the same admitted binding and queryable custody. |
| Undeclared/out-of-scope cross-build endpoint, wrong representation/range or missing required partition | Native/shared admission rejects the set before complete visibility; independent invalid inputs remain deliberate tests. |
| Pinned macro definition/default/fallback from a named dependency build | Admission preserves the dependency and endpoint custody; different producing-build identity alone does not invalidate legitimate multi-artifact provenance. |
| Source changes, stale holder or reclaimed attempt during preparation | Native final fence refuses completion, preserving the new owner and historical source. |
| Cancellation/worker death during preparation or staging | No complete product set is visible; cancellation drains owned resources and retains failure/partial state under its declared contract. |
| Commit acknowledgement lost | Exact receipt replay resolves the same committed product set; changed contents under the same identity conflict. |
| Two builds share a rendition and one task reuses an origin | Explicit read selection returns the correct mapping/diagnostics; ambiguous unselected builds refuse. |
| Archive/runtime changes after publication | A supported historical read keeps its recorded meaning; unsupported execution fails explicitly and old read support grants no current-write authority. |
| Partial or unavailable mapping product | Exact-origin consumer refuses or reports its declared unavailable result; source inspection still exposes retained original bytes/components. |

Expected source identities, ranges and graph memberships must come from independent fixture
annotations; asking the same producer to validate its own reconstructed output does not establish
semantic correctness. Reuse production invariant validators when testing their consumers, retaining
independent expectations when assessing the validators themselves.

Existing scoped test homes include semantic publication/release tests, source reader/frame tests
and native operation tests under `python/corpus-structure/tests/semantic/`. Plan authoring runs no
product tests, migration, database qualification or benchmark: those outcomes are **not_run**.
During implementation use focused checks for the slice, then PP-10's assembled `just test-all`
and applicable `just hygiene` route once functional scope is complete. Do not turn a passing
reader or component check into full parsing-pipeline qualification.

## Native sources and remaining execution choices

- [Python 3.14 concurrent futures](https://docs.python.org/3.14/library/concurrent.futures.html)
  specifies map buffering, process initialization, cancellation and whole-pool termination;
  [multiprocessing](https://docs.python.org/3.14/library/multiprocessing.html) supplies process
  ownership/sentinels and connection waiting. Use the actual 3.14.10 support, not the guide's 3.15 APIs.
- [spaCy pipeline batching](https://spacy.io/usage/processing-pipelines) and
  [memory management](https://spacy.io/usage/memory-management) inform worker-local linguistic
  execution; selected components and object lifetime are part of the product recipe.
- [SQLAlchemy 2.1 transactions](https://docs.sqlalchemy.org/en/21/core/connections.html) and
  [Core DML](https://docs.sqlalchemy.org/en/21/core/dml.html), plus
  [psycopg COPY](https://www.psycopg.org/psycopg3/docs/basic/copy.html), support existing set-shaped
  staging/publication. Installed SQLAlchemy 2.1.5 is the planning baseline; live 2.1 documentation
  may describe later patches and does not authorize a silent dependency move.

The review's source-verified mechanisms remain implementation leads, not claims of composed
runtime behavior. At execution use Context7 first for consequential API questions and verify
the pinned implementation for deadline, cancellation, ownership and admission details. Choose
inline/native batching, shared process batching or individually owned processes from the actual
demand and failure contract. Record a bounded choice before dependent worker integration; the
decision can defer unneeded concurrency mechanisms, but cannot defer required cancellation,
coverage, historical custody or protected publication behavior.
