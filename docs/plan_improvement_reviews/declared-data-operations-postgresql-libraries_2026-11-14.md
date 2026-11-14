# PostgreSQL client-library leverage in the declared-data-operations redesign

**Proposed recommendations · 2026-11-14.** Reviews the remaining DDO-00–12 change footprint at
`0463cb997`: the [coordinator](../plans/declared-data-operations_2026-11-12.md) and its ten
supporting plans, plus the legacy paths that series migrates or retires. The lens is seven
libraries: pglast 8.7, sqlglot 30.27.0, psycopg 3.3.6, psycopg-pool 3.3.3, pgpq 0.12.0,
adbc-driver-postgresql 1.13.0 and pgvector 0.5.1 (server extension `vector` 0.8.7), with pyarrow
only where it meets PostgreSQL. DDO-00–05 are complete at their foundation boundary with the
[SQLAlchemy/Alembic amendment](../plans/declared-data-operations_2026-11-12.md#sqlalchemyalembic-alignment-amendment--accepted-2026-11-14)
implemented; DDO-06–12 are open. `main` did not advance during the review and every citation is
exact at that commit. Root synthesis with five bounded independent contributions: three library-contract
confirmations at the installed versions, one family-by-mechanism map, and one adversarial review
of the draft. That review withdrew the draft's largest proposal, made two others conditional and
corrected its central judgment; see [what the challenge changed](#what-the-independent-challenge-changed).
No plan amendment or production change is made by this review.

**Revised 2026-11-14 at `ee683f3e9`.** `main` advanced by about 190 commits after publication
(`c703d4c31`) as DDO-06–08 execution resumed, so every recommendation, defect and cited passage
was re-checked against the current tree. The outcome:

| Item | State at `ee683f3e9` |
|---|---|
| I01 | Executor half implemented in `7c26b596e`. A native half remains, which the published version did not see |
| I02 | Open, and stronger: five port modules now borrow connections from the write engine |
| I03 | Open, unchanged |
| I04 | Overtaken. Contextual retrieval migrated (`a1411ce47`, `704ba229e`) in a form that meets the proposal's aims without a stored vector column. What remains is to record that contract |
| I05 | Open, unchanged |
| I06, I07 | Conditional; neither trigger has been met |
| Defects 1–5 | All still present |

The sections below are updated in place and the `I0n` anchors are unchanged. Citations into files
that changed since `0463cb997` are restated at `ee683f3e9`; the rest point at files that have not
changed. The coordinator's
[current implementation account](../plans/declared-data-operations_2026-11-12.md#current-integrated-implementation-and-scoped-evidence--2026-11-14)
owns current package state, and its resumed-execution section records that this review's
recommendations are not adopted wholesale. That part of the coordinator is being edited as work
proceeds, so this revision cites it by section and receipt, not by line. `main` moved twice more
during the re-check, to `9506ee45e`, without touching a cited code file.

**Draft exposure · 2026-11-14.** While this review was an untracked draft, the DDO root noted it
in the coordinator. That draft proposed a typed staged route for product members, which the
published version withdraws; nothing in the withdrawn proposal should be taken forward from the
draft.

The review asks two questions. **Added use:** which documented capabilities should take over a
responsibility that bespoke code carries, within the work DDO-06–12 still have to do.
**Lagging pivot:** where one responsibility is done several ways, and where target code does not
use a mechanism the repository already owns, or legacy code keeps one the target design replaced.

Recommendations are cited as `declared-data-operations-postgresql-libraries_2026-11-14.md#I0n`
and written "PG-libraries I0n" where other reviews' I-numbers are nearby. Existing identities
stay with their owners: F01–F14, RC01–09, DDO-CA-01…09, SQLA/Alembic I01–I05, CBO-001–025.

**Standard applied:** core principles 3.3 (FP-01–07, A1–A4, DP-01–24, G1–G8),
efficient-architecture heuristics, code-intelligence profile 1.4, test-assessment 1.2 and the
repository binding, selected through `standard.toml`. Evidence labels follow principles §D.
Every benefit below is **Proposed**; nothing here is Tested or Measured.

**Sources.** Each overview was read end to end (lines · SHA-256 prefix):
[pglast](../libraries/postgresql/pglast.md) 1,846 · `3a376dc3`;
[sqlglot](../libraries/postgresql/sqlglot.md) 2,723 · `d477cc16`;
[psycopg](../libraries/postgresql/psycopg.md) 2,306 · `8fdefbbe`;
[psycopg-pool](../libraries/postgresql/psycopg-pool.md) 1,941 · `f9e3ac33`;
[pgpq](../libraries/postgresql/pgpq.md) 1,319 · `ff6aa0b8`;
[pgvector](../libraries/postgresql/pgvector.md) 954 · `731f85f7`;
[adbc-driver-postgresql](../libraries/postgresql/adbc-driver-postgresql.md) 1,505 · `9df58164`.
Installed versions match the pins. The bundled libpq is 18.0.6.

**Path convention.** `P/` is `python/corpus-structure/src/corpus_structure/`. Plan citations
name the file: "coordinator:1188", "demand-planning:296".

**Not in scope.** This is not a completion audit, a design review under the binding, or a
refresh of the library-leverage accounts. No test, provider, build, health check or database
operation was run; the standing cancellations remain in force.

## Combined judgment

The seven libraries are deployed consistently with the accepted decisions, in the target code as
well as the legacy code. The premise that they can be leveraged much more extensively for the
declared-data-operations target holds only narrowly, more narrowly than it did for SQLAlchemy
and Alembic.

The target does not lag the legacy design in how it moves data. Generic DDO products travel as
one JSON document by design, with an explicit size refusal. Where bulk typed transfer is
warranted, DDO already uses it: PDF records under a DDO claim go through Arrow binary COPY into
authenticated staging ([ADR-0099](../adr/0099-runless-pdf-source-ownership.md)), and release
archives do the same ([ADR-0098](../adr/0098-typed-release-archive.md)). ADR-0098 also records
why a second transport path is unwelcome. The draft of this review proposed a typed staged route
for product members; it is [withdrawn](#considered-and-withdrawn-a-typed-staged-route-for-product-members).

The review published five recommendations and two conditional ones. After the re-check at
`ee683f3e9`, three are open as written, one is half done and one is overtaken:

- **I01** replaced per-member hydration with set reads. The executor now does this. Native
  binding validation still gathers the whole binding population into one JSON value and scans it
  per selected item, which is the same access pattern on the other side of the boundary.
- **I02** bounds the executor's database concurrency. Claim renewal shares a four-connection pool
  with port workers, which the plan says it must not wait behind. More ports borrow now than at
  publication. Open.
- **I03** gives raised database errors one contract and removes a dependency on message text.
  Open.
- **I04** asked DDO-08 to state the vector contract before contextual retrieval migrated. The
  migration has happened and its design is sound; the plan and D3 still do not describe it.
- **I05** is a low-priority cleanup of native declaration edits and duplicated derivations. Open.
- **I06** and **I07** are conditional: an Arrow read transport for DDO-10, and a cross-check of
  declared read inputs against compiled SQL. Neither trigger has been met.

Five observed defects are listed separately and all remain. Most of what the overviews offer has
no current fit, and the coverage tables say why.

## Current footprint

| Owner | Observed contract (Interface-checked 2026-11-14, at `ee683f3e9`) | Significance for the lens |
|---|---|---|
| DDO generic write path, `P/semantic/data_operation_storage.py:390–411` | Every native operation is `ops.<name>(jsonb) → jsonb`; the payload is sent as text and cast. A completion is refused in Python above 64 MiB (`P/orchestrate/data_operations.py:715–716`). | One deliberate transport for product bodies, with an explicit limit. |
| DDO recovery protocol, `data_operations.py:718–784` | Retaining the completion intent and publishing it are separate transactions; a later attempt can adopt the retained intent (coordinator:90). | Anything a completion needs must survive between those transactions. |
| DDO product identity, `P/semantic/sql/data_operations.sql:1069–1101` | Product identity digests the canonical body, which embeds every member packet; each member body must equal its packet. | Member bodies are part of the product's identity, not only its storage. |
| DDO PDF capture, `P/semantic/pdf_capture.py:182–291`; `P/semantic/pdf_staging_native.py:52–91` | Under a DDO claim the port stages PDF records through `copy_arrow_stream`; staging accepts a DDO task by decision (ADR-0099). The DDO product binds the sealed publication's receipt. | DDO already uses typed staging where a decision places it. |
| Arrow writer, `P/semantic/arrow_transfer.py:60–171` | Refuses nanosecond timestamps and inexact numerics; checks pgpq's emitted schema against declared wire types; full schema equality per batch; explicit column list; fresh encoder per COPY; no footer after an error. | Guards every pgpq hazard the overview lists. |
| DDO reads, `P/semantic/data_operation_consumers.py:103–250`; `data_operation_storage.py:891–953`; `data_operations.sql:1727–1742`; `P/semantic/sql/data_operation_bindings.sql:626–704` | Hydration joins a typed `VALUES` relation of up to 1,024 retained pins to `ops.data_binding_rows`, once per page, and reads the bodies one row at a time through a server-side cursor. The function is still PL/pgSQL `RETURN QUERY` with no limit. Native binding validation aggregates the function's whole result, bodies included, into one JSON value. | See I01. |
| DDO read acquisition, `data_operations.sql:1395–1442` | `read_demand_result` inserts trust scopes, takes `FOR SHARE` locks and records the read, also when a `read_id` is supplied. Its product view now refuses a page whose bodies exceed a byte bound (8 MiB by default, 64 MiB at most) before aggregating them. | It is an effect, not a pure read, and its JSON pages are now bounded; see I06. |
| DDO Core read bodies, `P/semantic/data_operation_projections.py:312–317, 1079–1121` | Core selects compiled with `literal_binds`, captured with the whole physical model as input identity, substituted into PL/pgSQL at placeholders. | The route the adopted SQLA/Alembic I02 describes. |
| Pool and engine, `P/core/db/store.py:45–54, 132–156` | One `ConnectionPool` per opened purpose, `close_returns=True`, `check_connection` per checkout, JSON adapters in `configure`; SQLAlchemy borrows through `creator=pool.getconn` with `NullPool`. No `reset`. | The documented integration. |
| Executor, `P/cli/demands.py:222–225`; `data_operations.py:462, 1027–1028, 1083`; `P/semantic/claim_lifetime.py:296, 397` | Holds a write pool and an admission pool. Capacity is `min(max_claims, max_owned_bytes // reservation)`, two at defaults. A renewal thread and up to four worker threads borrow from the write engine. Five port modules open connections on it: PDF capture, effect, transforms and views, and contextual retrieval. | See I02. |
| Failure classifier, `store.py:231–304` | One translation of SQLSTATE, pool exceptions and ADBC status. About twenty other sites compare SQLSTATE strings. | See I03. |
| Legacy vectors, `P/model/semantic/physical.yaml:49–52, 4345–4390`; `P/semantic/sql/source_contributions.sql:2453–2454, 3209, 3220` | Dimensionless `vector` columns keyed by task; values arrive as JSON in the task envelope and are cast through text, repeatedly. Search is exact. | Legacy stored route; its remaining callers are in the run-based store (`P/semantic/operations.py:1531–1595`). |
| DDO vectors, `P/semantic/contextual_operations.py:143–199, 329–339`; `P/semantic/contextual_storage.py:567–624`; `P/model/semantic/data-operation-contextual.yaml` | Vectors are a member value of a `DdoContextualVectors` product. Retrieval binds them as typed `VECTOR(d)` parameters in a transient `VALUES` relation and PostgreSQL computes exact cosine and lexical rank over the complete selected inventory. No vector column is written. | The migration I04 asked the plan to describe; see I04. |
| ADBC reads, `P/core/db/adbc_lifetime.py`; `P/semantic/analytics.py:857–935`; `P/serve/companion_export.py:121–189` | Separate session importing the SQLAlchemy snapshot (ADR-0026), COPY-backed Arrow batches. | See I06. |
| Native authoring, 18 modules importing pglast | One parse entry, declaration identity, inventories, SQL-standard body insertion. Wrappers are f-string templates here and in the companion module (`P/semantic/companion_projection_native.py:24–88`). | Already the backbone (ADR-0047). |
| Projection analysis, `P/semantic/projection_analysis.py` | sqlglot qualification, typing and lineage over the checked recipe (ADR-0074). | Recipe-carried metadata is the authority. |

An offline pglast scan of the 54 native SQL files, repeated at `ee683f3e9`, found 356 functions in
the 50 that parse before templating; all 188 that are `SECURITY DEFINER` also fix `search_path`.
That convention holds without a rule, so the review proposes none.

## One responsibility, several mechanisms

"Go-forward" names the mechanism an accepted owner selects. Where no owner does, the row says so.

| Responsibility | Mechanisms in use | Go-forward and its owner | Lagging | Disposition |
|---|---|---|---|---|
| Write of product data | One JSON document to a native function (DDO generic products); Arrow binary COPY to typed staging (PDF under legacy and DDO tasks, Arrow publication, archive); text COPY rows (publication); `complete_task` envelope (legacy tasks) | JSON document for product bodies (wire protocol); typed staging for PDF (ADR-0099) and archives (ADR-0098); one transport per responsibility (ADR-0098) | None. The legacy branch of PDF staging retires with runs | Consistent with decisions. A typed member route was considered and withdrawn |
| Hydration and validation of bound inputs | Executor: one typed `VALUES` join per page of 1,024 pins, read through a server-side cursor. Native binding validation: the whole binding population aggregated into one JSON value, then scanned per selected item | Keyed, demand-scoped set reads (adopted SQLA/Alembic I02; demand-planning:235–236) | Native binding validation | **I01**: executor half implemented, native half open |
| Public reads | Paged JSON functions, byte-bounded for DDO product pages; ADBC Arrow over an imported snapshot; `yield_per` cursors; materialized rows | One pinned projection through guarded functions with scope, cursor and limit as parameters (interfaces-and-evaluation:10–20, 42–43) | No DDO read owner in `serve` or `intervene` yet (coordinator:1188) | DDO-10 owns it; Arrow transport **I06**, conditional |
| Executor database concurrency | Pool bounds in settings; claim, byte and worker bounds in the execution policy | None stated. D3:805 says one pool per process | The two sets of bounds are independent; renewal shares the pool | **I02** |
| Meaning of a raised database error | Central classifier; about twenty direct SQLSTATE comparisons; one comparison with English message text; declared `NativeDiagnosticBinding`; DDO refusals in the result envelope | The classifier plus declared bindings | Retained modules that compare directly; claim renewal | **I03** |
| Vector storage and search | DDO: vectors as a product member, bound as typed `VECTOR(d)` parameters into a transient relation. Legacy: JSON cast to `vector` in native SQL, stored columns keyed by task, JSONB path reads of cached vectors. Residual `halfvec` mapping | Exact cosine with pgvector's SQLAlchemy types (D3 "current bounded route"). The DDO form is implemented but stated in neither the plan nor D3 | The legacy stored route, which retires with the run-based store | **I04**: overtaken; record the contract |
| Edits to native declarations | Parse-tree edits for SQL-standard bodies; f-string wrappers; string replace for renames; placeholders for compiled Core | pglast for declarations (ADR-0047); placeholders and PL/pgSQL wrappers for guarded reads (adopted I02) | String renames in the DDO kernel and `native_candidate.py` | **I05**, low priority |
| Derivation of one native fact | Two production copies of the descriptor-literal extraction; bare integers for trigger flags | One helper per fact | `source_view_native.py:21–42, 232–233`; `execution_admission.py:508–536` | **I05** |
| Dependencies of a read | sqlglot analysis of checked recipes (ADR-0074); whole-model closure for DDO Core bodies; declared relations for change determination (change-reuse:44–50) | Declared contracts and relations | None | Consistent; cross-check **I07**, conditional |
| JSON across the boundary | Pool codec (`json`, floats); DDO exact-decimal codec through text casts; 40 legacy `CAST(:x AS jsonb)` sites | For DDO: `json_bytes` and `ContextJSONB` (`P/semantic/data_operation_json.py`) | Legacy string casts | Deliberately different. psycopg can scope a codec per connection, cursor or value, but SQLAlchemy owns the cursor and wraps values itself, so a per-column exact codec goes through text. Legacy sites retire with `complete_task` |
| Identifier quoting | SQLAlchemy preparer; psycopg `sql.Identifier` at COPY sites; hand-rolled in five modules | SQLAlchemy preparer for SQL text, psycopg `sql` at the driver | `cli/db.py:63–68` and four other modules | Align when touched |
| Run supervision | Dedicated session with a session advisory lock (`P/orchestrate/liveness.py`) | Native demand and fulfillment (RC05, coordinator:52) | Three importers remain (`orchestrate/commands.py`, `orchestrate/source_progress.py`, `semantic/visual_requests.py`), all on run-based paths | Ordinary drivers have moved to native demands (coordinator:1184); the rest retires with its run-based callers |
| Transactions, cancellation, waiting | SQLAlchemy `begin` everywhere, one SERIALIZABLE owner; `cancel_safe` and `adbc_cancel` under one handle; polling | As implemented (D8; demand-planning:209) | None | Consistent; no action |

<a id="I01"></a>
## I01 — Hydrate bound inputs in sets

**Executor half implemented (`7c26b596e`, 2026-11-14). Native half open: Recommend.**

**What the review found at `0463cb997`.** The executor looped over every member of every role and
ran one statement per member. Each statement selected from `ops.data_binding_rows(...)`, a
PL/pgSQL function that returns its whole result with `RETURN QUERY` and takes no limit.
PostgreSQL materializes such a function's full result before the caller filters it, so the
binding population was recomputed once per member. The adopted SQLA/Alembic I02 text already
asked for "keyed, demand-scoped joins and bounded pages", and demand-planning:235–236 for "a
bounded page of compact identities" before hydration.

**What is implemented (Interface-checked at `ee683f3e9`).** `hydrate_consumer_selection`
(`data_operation_consumers.py:103–250`) now does what steps 1 and 2 proposed:

- Retained pins travel as one typed `VALUES` relation per page of up to 1,024 members and join
  the binding function, with every former predicate as a join condition. The function is
  evaluated once per page instead of once per member.
- Each page must return exactly its members, once each; a missing or duplicated member refuses.
- The byte charge is unchanged: canonical decoded size times multiplicity, checked across pages.
- Bodies are read through a server-side cursor one row at a time (`yield_per=1`), so no driver
  batch can exceed the owned packet before the capacity check runs.

The coordinator records 18 pure and 4 native hydration controls as passed (receipts
`8db09d42786b4b66ac290c2343f03396` and `9b5175234c124c8dabec18fce8e2b714`). This review ran none
of them.

One consequence of the last point is worth knowing, not changing: a server-side cursor with a
fetch size of one costs one round trip per member. The statement and the function evaluation are
still single. That is a deliberate trade of round trips for a client memory bound of one body.

**What remains.** Two things, both on the native side, where the client libraries cannot help.

1. **Native binding validation uses the same pattern in JSON.** `ops.attach_data_request` calls
   `ops.ddo_require_binding` (`data_operations.sql:755`). That function aggregates the complete
   result of `ops.data_binding_rows`, with both body columns of every row, into one `jsonb` array
   (`data_operation_bindings.sql:658`). It then scans the array once per selected input
   (`:662–668`) and places it in a `context` value handed to the population checks (`:704`).
   Those checks scan it again per population member and copy the whole context once per
   candidate row (`:357–359`). The work grows with selected items times population, and the
   population's bodies are carried through every copy. This was present at `0463cb997`; the
   published review looked only at the Python side and missed it.

   The proposal is the one already made for the executor: join the selected inputs to the
   binding function as a relation, and give the population checks the member columns without
   bodies, fetching a body only for a row that was chosen. The Core projections already name
   that body-free column set (`member_columns`, `data_operation_projections.py:304–309`).
   Whether any population predicate reads body fields from unselected rows was not established
   and decides how much of the body can be dropped.

2. **The binding function is still unbounded.** `ops.data_binding_rows`
   (`data_operations.sql:1727–1742`) takes subject, source and scope but no limit or
   continuation. It is evaluated once per hydration page and once per attach. Either it gains
   those parameters or its callers establish that the demand-scoped population is bounded. This
   is step 3 of the published proposal and is unchanged.

**Why it matters (Proposed).** PostgreSQL limits the elements of one `jsonb` array to 256 MiB in
total and any value to 1 GiB. The aggregate in step 1 carries two body columns per row, so a
binding population reaches that limit well before its bodies alone would. The coordinator
records the `jsonb` array limit being hit on 2026-11-14 while the effective model archive was
interpreted (receipt `2950f7ac49574c4a970e491119d89972`), and
[ADR-0105](../adr/0105-compact-effective-identity-archives.md) resolved it by removing repeated
content at its owner instead of changing the transport. The same reasoning applies here.

**Preserved guarantees.** The exactly-one-admitted-body check, the trust and support predicates,
the byte capacity rule, the `SECURITY DEFINER` boundary, and the rule that binding validation
checks the complete pinned demand and not only the request's lock subset
(`data_operations.sql:754`).

**Uncertainty.** No binding population was measured, so whether the native half matters at
current scale is not known. The argument is structural.

**Alternative.** Leave native validation as it is and rely on the 256 MiB limit as the refusal.
That keeps a hard failure whose cause is not visible in the error, as the archive episode showed.

**Challenge case.** A negative population check needs to see candidates that were not selected.
Dropping bodies must not drop rows; the proposal keeps every row and removes only the body
columns from the set that is scanned.

**Affected packages.** DDO-05 and DDO-06. Unlike the executor half, this changes native function
bodies and so needs a native successor.

**Closure evidence.** For the executor half, the coordinator's hydration controls. For the native
half: an attach whose binding population has many members validates with the same result and
refusals as today, with expectations written independently of the function.

<a id="I02"></a>
## I02 — Bound the executor's database concurrency

**Recommend. Rule impact for the ADR route. Open at `ee683f3e9`, and stronger than at
publication.**

**Current approach.** D3:805 and D9:175 say one pool per process. Each opened purpose has its
own pool, and the DDO executor holds a write pool and an admission pool for its run
(`cli/demands.py:222–225`). Pools default to four connections and four waiters.

Three kinds of thread borrow from the write engine: the driving thread, the claim-renewal thread
(`claim_lifetime.py:296, 397`), and up to four worker threads (`data_operations.py:1083`), in
which ports open their own connections. That is six possible borrowers for four connections.
Nothing refuses at defaults, because four may wait, but renewal can queue behind port work.
Demand-planning:296–297 says "Renewal has its own finite database operation and does not wait
behind provider work".

At publication one port did this, PDF capture. Five modules do now: PDF capture
(`pdf_capture.py:206, 237, 266`), the PDF effect, transforms and views
(`data_operation_pdf_effect.py:76`, `pdf_transforms.py:300–683`, `pdf_views.py:125`) and
contextual retrieval (`contextual_operations.py:333`). They release the connection before
computing, as the plan requires, so each borrow is short. The number of threads that can ask at
once is what grew.

The pool bounds live in settings and the worker and claim bounds in the execution policy. Neither
is derived from, or checked against, the other.

**Proposed change.**

1. Decide and record pool ownership: one pool per login per process, each with a stated role and
   a total connection budget. Update D3 and D9. The 2026-10-29 leverage review left concurrent
   pools without a consumer; the executor is that consumer.
2. Renewal does not share admission with port work. The simplest form is a pool size checked at
   executor start against the policy's worker count plus the driving and renewal threads. A
   reserved connection for renewal is the stronger form.
3. Keep the pool without a `reset` callback. What makes that safe is `SET LOCAL` only and staging
   tables dropped at commit; both hold in the code read. A `reset` would move every return onto a
   worker thread.
4. Fix the notice-handler accumulation (observed defect 1) in the store.
5. Pass `application_name` in the ADBC connection URI so those sessions are attributable.

**Benefit (Proposed).** The plan's renewal rule becomes true by construction, and the documented
pool rule matches the code.

**No current fit, with reasons.** `NullConnectionPool` ignores `close_returns`, which confirms
the 2026-10-29 rejection. Zero-minimum pools, `drain`, `resize` and callable connection
parameters have no consumer while credentials are static. Pipeline mode is still experimental and
SQLAlchemy does not use it. Row factories would change SQLAlchemy's rows.

**Alternative.** Leave the defaults. Capacity is two claims at default byte settings, so
contention needs several port workers borrowing at once; it may be rare today.

**Challenge case.** Sizing the pool to the worker count over-provisions a process whose workers
mostly wait on providers. Connections are released before waits (demand-planning:295–296), so a
start-time check is cheaper than a larger pool and is the form proposed.

**Affected packages.** DDO-06; D3 and D9 owners.

**Closure evidence.** A recorded decision; an executor start that refuses an inconsistent policy;
a renewal that proceeds while every port worker holds a connection.

<a id="I03"></a>
## I03 — One failure contract for raised database errors

**Recommend. Small. Open and unchanged at `ee683f3e9`.**

**Current approach.** `classify_error` is the central translation. About twenty other sites read
`exc.orig.sqlstate` and compare strings such as `P0004`, `55000`, `54000` and `23514`. Claim
renewal, which the DDO executor uses, decides whether a timeout is retryable by matching SQLSTATE
together with the English primary message (`claim_lifetime.py:214–227`). The classifier maps
`57014` to "cancelled" and does not classify `55P03`. PostgreSQL 18 raises `55P03` for lock
timeout and `57014` for both statement timeout and cancellation; the code uses no `NOWAIT`.

Server messages follow `lc_messages`. The provisioned cluster is created with
`--locale C.UTF-8` (`scripts/pg_provision.sh:93`), so the match holds there. It is an implicit
dependency: nothing states it, and a server named through `CORPUS_DATABASE__URL` need not share
it.

**Proposed change.**

1. The classifier reports a lock timeout for `55P03` and an operation deadline (its existing
   cause) for `57014` when no client cancellation was requested. Renewal reads the cause, not the
   message. Retrying after an administrative cancel is safe here: the work rolled back and retries
   are bounded by the lease.
2. One small table in `core/db` names the application's own conditions once. Retained modules
   read it. psycopg's exception classes add nothing, because custom codes fall back to generic
   classes.
3. Sites in modules the plan retires go with their owners. Sites in retained infrastructure
   (`execution_admission.py`, `releases.py`, `characterization_store.py`) move to the classifier.

**Benefit (Proposed).** One place states what a database failure means, and the executor's retry
decision no longer depends on message wording.

**Preserved guarantees.** DDO refusals stay in the result envelope. Phase and effect knowledge
stay with the caller.

**Alternative.** State the locale dependency where the match is made and leave the rest. That
closes the defect and keeps twenty private readings of the same codes.

**Challenge case.** A guard raises one code that two callers must treat differently. The table
names the condition; each caller still chooses its recovery.

**Affected packages.** DDO-06; retained native infrastructure.

**Closure evidence.** Renewal retry decided without message text, shown by a lock-timeout and a
statement-timeout case with expectations written independently of the classifier.

<a id="I04"></a>
## I04 — State the vector contract for contextual retrieval

**Overtaken by implementation (`a1411ce47`, `704ba229e`, 2026-11-14). Remaining: record the
contract. Recommend, small.**

**What the review found at `0463cb997`.** Operations-and-adapter-cutover listed contextual
retrieval for DDO-08, and the plan said nothing about vectors. The only vector route was the
legacy one: JSON arrays in the task envelope, cast through text to `vector` for each check and
insert, stored in columns keyed by task, and read back with `jsonb_path_query_array`. The review
asked the DDO-08 package to state, before migrating, where a vector is authoritative, how a
searchable form is derived, what stays fixed, how reuse reads vectors, and what is not adopted.

**What is implemented (Interface-checked at `ee683f3e9`).** Contextual retrieval is now a
declared operation (`P/methods/contextual_declared.py`, `P/semantic/contextual_operations.py`,
`P/model/semantic/data-operation-contextual.yaml`). Its design answers each point, and more
simply than the review proposed:

| Point | Review proposed | Implemented |
|---|---|---|
| Authority | Vector as a member value; `vector` column a derived projection | Vector as a member value of a `DdoContextualVectors` product. No projection and no stored vector column |
| Searchable form | A named native step from the tagged value to a pgvector input | Python binds each vector as a typed `VECTOR(d)` parameter in a transient `VALUES` relation (`contextual_storage.py:567–624`) |
| What stays fixed | FP32, exact cosine, dimension and finiteness checks, no approximate index | The same. `validate_vector` checks dimension and finiteness, and the declaration states `exact-pgvector-cosine-and-lexical-ranking`. A transient relation cannot carry an index, so exactness holds by construction |
| Reuse | Read from the projection, not from task results | Product identity; the vectors product is an ordinary bound input |
| Not adopted | `register_vector` on the shared pool; pgpq to a `vector` column | Neither is used |

The implemented form is better than the proposal in one respect: with no stored column there is
no derivation step to keep in agreement with the member value. The database borrow is also
released before relationship selection (`contextual_operations.py:329–339`).

**What remains.**

1. **The contract is not written down.** The coordinator's resumed-execution section says only
   "exact pgvector kernels where their contracts fit". D3's "current bounded route" still says the route
   stores FP32 vectors (D3:161–166 at `HEAD`), which describes the legacy tables; the target
   keeps vectors as product members. The DDO-08 text and D3 should state the implemented
   contract in the table above.
2. **The bound that keeps it cheap is implicit.** Each retrieval sends the whole selected
   inventory as parameters: six per target, one of them the full vector. The encoder profile's
   `max_items` caps the population (256 by default,
   `P/methods/contextual_embeddings.py:54`), and `prepare_contextual_retrieval` refuses above
   it. PostgreSQL's extended protocol allows 65,535 parameters per statement, so this form
   stops working near 10,900 targets. Nothing relates `max_items` to that ceiling. One sentence
   in the contract, or a check where the profile is admitted, would do.
3. **The legacy stored route retires with its callers.** `kb.contextual_vector`,
   `kb.contextual_target_vector`, `ops.contextual_mutual_neighbors` and the cached-vector reader
   are reached only from the run-based store (`P/semantic/operations.py:1531–1595`). They
   belong to the retirement the coordinator already assigns to DDO-10 and DDO-11.

**Benefit (Proposed).** The exact-search guarantee and the inventory bound are stated where a
later change to either would be noticed.

**Uncertainty.** The cost of resending the inventory for each query occurrence was not measured.
At the default bound it is at most 256 vectors per statement.

**Alternative.** Leave it unwritten. The code is correct today; the cost is that D3 describes a
different route from the one the target uses.

**Challenge case.** If the scale trigger in D3 fires and an inventory outgrows parameter
binding, the natural next step is a stored column, and with it the derivation and index questions
the published I04 raised. That is the point at which those questions become live again.

**Affected packages.** DDO-08; the D3 owner.

**Closure evidence.** The plan and D3 text. Items 1 and 3 need no code change; item 2 needs one
only if the ceiling is checked instead of stated.

<a id="I05"></a>
## I05 — Edit declaration headers through the parse tree; one helper per native fact

**Recommend. Low priority; do it when the code is next changed. Open and unchanged at
`ee683f3e9`.**

**Current approach.** The DDO kernel renames each protocol function by replacing the literal text
`CREATE OR REPLACE FUNCTION ops.<name>(` (`data_operation_storage.py:219–224`).
`native_candidate.py:352, 697, 846` turn `CREATE FUNCTION` into `CREATE OR REPLACE FUNCTION` by
string replace although the parsed `replace` flag is already inspected. The descriptor-literal
extraction exists twice in production and once in tests. A trigger's shape is checked with
`timing != 2` and `events != 56`.

Wrappers built from f-string templates and compiled Core substituted at placeholders are the
adopted route for guarded reads, used by the companion module too. They are not in question.

**Proposed change.**

1. Header edits use the parse tree: rename and `OR REPLACE`. pglast keeps a PL/pgSQL body byte
   for byte through such edits, and body identity is the digest of the stored source
   (`execution_admission.py:210, 309`), so digests do not change. Each edited statement is
   reparsed and compared with pglast's position-insensitive equality.
2. One helper for the descriptor literal, shared by both production sites and the test.
3. Named trigger constants from `pglast.enums` in place of the integers.

**Limits (Interface-checked; offline checks unretained).** The deparser regenerates the
dollar-quote tag and the header, and drops comments between statements. A body ending in `$`
deparses to text that does not reparse, so the reparse check in step 1 is required. Deparse
output is not stable across pglast releases; frozen artifacts already account for that.

**Benefit (Proposed).** A kernel whose spacing changes cannot silently skip a rename.

**Alternative.** Leave it. The rendered kernel is reparsed and split into definitions, and
`plpgsql_check` runs on DDO functions, so a missed rename is caught at authoring.

**Challenge case.** The PDF native modules slice SQL with regular expressions and markers
throughout. Converting them is a larger change with frozen-artifact consequences and is excluded.

**Affected packages.** DDO-04; native authoring.

**Closure evidence.** Body digests unchanged across the conversion; the reparse check refuses a
deliberately malformed edit.

<a id="I06"></a>
## I06 — An Arrow read transport for DDO-10

**Conditional.** Trigger: the first DDO-10 consumer that needs columnar output, such as an export
or the analytical capture, over DDO-owned products.

**Why not now.** No DDO read owner exists in `serve` or `intervene` (coordinator:1188), and JSON
pages are the preserved contract (interfaces-and-evaluation:43). Converting a JSON page to Arrow
in Python is correct and simple until a columnar consumer exists. Since publication the JSON
route has been strengthened instead: product pages are refused above an explicit byte bound
before their bodies are aggregated (`4dcc41dc1`). The trigger has not been met at `ee683f3e9`.

**Constraints when triggered (Interface-checked).**

- `read_demand_result` has effects on every call, so it cannot run in ADBC's read-only session.
  The transport needs a `STABLE` projection function evaluated under pins acquired separately,
  which is the separation the adopted SQLA/Alembic I02 already describes.
- ADR-0026 has ADBC import the SQLAlchemy snapshot before data reads. Either that stays, with the
  acquiring transaction exporting its snapshot as today, or a successor states that native pins
  are the consistency boundary. This is a rule impact.
- ADBC uses COPY only for queries without bound parameters; pins and cursors are inlined as
  literals, as `companion_export.py` does. Bound queries buffer whole results.
- A PL/pgSQL `RETURN QUERY` function materializes its result. Paging must be a function
  parameter, one COPY per page. Companion export today issues one COPY per family, unpaged.
- `jsonb` arrives as text marked `arrow.json`, `numeric` as text, and `vector` as opaque bytes
  unless projected to `real[]`. ADBC's default type resolver reads all of `pg_attribute` at
  connect; existing callers choose `builtin` deliberately.
- `PublishedPdfReader` and its `yield_per` cursors are retained with PDF publication (ADR-0099);
  the other cursor readers retire with their tables.

**Not established.** That COPY over a `SECURITY DEFINER` function behaves as ordinary execution
was reasoned from PostgreSQL source, not run.

<a id="I07"></a>
## I07 — Cross-check declared read inputs against the compiled SQL

**Conditional.** Trigger: a DDO-09 or DDO-10 projection whose declared inputs are narrower than
the whole physical model. Not met at `ee683f3e9`: compiled Core bodies still take the whole
physical model as their input identity (`data_operation_projections.py:1079–1121`).

**Scope.** Declared contracts and relations are the authority for change determination
(change-reuse:44–50), and checked recipes are the authority for projection explanations
(ADR-0074). Parsing emitted SQL cannot replace either. It can supply an independent check: the
relations a compiled read references are a subset of its declared inputs. The adopted I02 text
allows exactly that role: "Text derivation checks supplement, not replace".

**Mechanism when triggered.** pglast's `referenced_relations` over the compiled select, with one
fresh visitor per statement.

**Hazards (Interface-checked; offline checks unretained).**

- pglast's helper drops a real table that shares a name with a CTE elsewhere in the same input.
  Authored SQL uses it for its allow-list (`P/semantic/authored_sql.py:172–179`); the catalog
  `EXPLAIN` that follows is the check that holds in that case.
- sqlglot reads a bare `<=>` as null-safe equality (`sqlglot/tokens.py:247`) and prints
  `IS NOT DISTINCT FROM`. That is pgvector's cosine operator; vector queries must not pass
  through sqlglot unless written as `OPERATOR(public.<=>)`.
- sqlglot treats bare function arguments as unresolved columns and renders `CREATE FUNCTION`
  with `SECURITY DEFINER` invalidly. It stays out of native declarations.
- Neither library promises stable output across releases. Parsed facts may explain or check;
  they are never identity.

## Considered and withdrawn: a typed staged route for product members

The draft proposed that a kind could declare its members as staged columns, written through
`copy_arrow_stream` and finalized natively, with the JSON document reduced to a manifest. It is
withdrawn for these reasons, each verified after the challenge:

- **Recovery.** Retain and publish are separate transactions and a later attempt can adopt the
  retained intent. Staging tables are dropped at commit. Staged rows would not survive to
  publication or adoption without a durable custody design of their own.
- **Identity.** Product identity digests a canonical body that embeds every member packet. Moving
  member bodies out of the document changes the identity rule, not only storage.
- **Decision.** ADR-0098 selected one typed route for archives and rejected a second transport
  path and any size-dependent fallback for their recovery and testing burden. A second route for
  product members needs an argument against that reasoning, and the draft had none.
- **Concept.** The refusing `artifact_digest` branch is for exact encoded original bytes
  authenticated by digest (contracts-and-compilation:246–247). The coordinator assigns "DDO-07
  staged artifacts" to an owner (coordinator:909–910). Stream items already have a declared
  mapping to one completion under DDO-06 (contracts-and-compilation:309–314).
- **Need.** No DDO family is known to approach the 64 MiB refusal. The review measured no sizes.
  The one size failure recorded since publication was in the model archive, not in product
  members, and [ADR-0105](../adr/0105-compact-effective-identity-archives.md) answered it by
  storing repeated identity witnesses once. It states that this complements typed binary staging
  and adds no transport, which is the same preference this section rests on.

If a family does reach the limit, the decision belongs with those owners and with ADR-0098's
single-route reasoning. One observation is left for the physical owner, outside this lens: a
member body is stored in the retained intent, in the product's canonical body and in its member
row, and is schema-checked at each.

## Observed defects

These were found while reading and need no plan change to fix. All five were re-checked at
`ee683f3e9` and remain; the files cited in defects 1 to 3 have not changed since `0463cb997`.

1. **Notice handlers accumulate on pooled connections.** With `NullPool`, SQLAlchemy attaches the
   dialect's `on_connect` to every checkout (`sqlalchemy/engine/create.py:718–729`), and the
   psycopg dialect appends a notice handler each time (`dialects/postgresql/psycopg.py:576–578`).
   psycopg's list does not deduplicate, and with `close_returns` the same physical connection
   comes back. It gains one handler per borrow until `max_lifetime` replaces it.
   Interface-checked in installed source; not observed on a live connection. Owner: `store.py`.
2. **Claim renewal depends on the server's message locale** (`claim_lifetime.py:214–227`). The
   provisioned cluster satisfies it implicitly. See I03.
3. **`halfvec` mappings outlive their model element.** `sys:HalfVec` was removed
   (`P/model/revisions.yaml:766`). `P/schema/relational.py:68, 145, 788–789, 917` and
   `P/schema/interchange.py:75, 188–189` still map it, and `interchange` has no Arrow mapping for
   `vector`. Whether the legacy compiler still needs the mapping for historical revisions was not
   checked. Owner: the interchange reduction at coordinator:1193.
4. **Design text describes superseded choices.** D3:805 and D9:175 on pools (I02). D9:116–123
   lists SQLAlchemy 2.1.5 and Alembic 1.20.0, a `halfvec` column type, pglast as a development
   dependency, and ADBC and pgpq as conditional on a probe.
5. **Library defects at the installed versions**: the pglast and sqlglot hazards in I05 and I07,
   and pglast's deparse of a unique index with both `NULLS NOT DISTINCT` and `WHERE`, which does
   not reparse.

## What the independent challenge changed

A design-reviewer agent was given the draft and the sources, not the reasoning. Every objection
below was re-verified by the root before the rewrite.

- **Central judgment corrected.** The draft said DDO writes everything as one JSON document and
  that the target lagged the legacy design. DDO PDF capture and release admission already stage
  typed rows under ADR-0099 and ADR-0098.
- **Withdrawn:** the typed staged member route, for the reasons above.
- **Made conditional:** the Arrow read transport (the read function has effects, and ADR-0026
  requires the snapshot import) and the analysis of deployed SQL (ADR-0074 keeps recipe analysis
  as the authority, and change determination uses declared relations).
- **Corrected facts.** The message locale is fixed by cluster provisioning. Executor capacity is
  two claims at defaults, not eight. The companion module builds its wrappers from templates, so
  the DDO placeholders follow the adopted route. Hydration cost is members times population.
- **Strengthened:** I02, by the renewal thread sharing the pool with port workers.

## Adoption order, interactions and authority

Priority by consequence at `ee683f3e9`: I02, the native half of I01, I03, I04, I05; I06 and I07
wait for their triggers. I02 moves to the front because the number of ports borrowing
connections grew while its bound did not.

The five are independent of one another. I02 and I03 touch the executor and the store and can
share one change. The native half of I01 changes native function bodies and needs a registered
successor, so it fits best with the next successor DDO-05 or DDO-06 already has to author. I04 is
now mostly documentation: two passages and, optionally, one bound check. I05 waits for the next
change to the kernel
assembly.

I02 revises a statement in D3 and goes through the ADR route. I06, if triggered, interacts with
ADR-0026. Only the native half of I01 needs a native successor.

Taken together the set is small and has become smaller. It adds no mechanism, changes no
accepted decision other than the pool statement, and leaves the transfer design where ADR-0098
and ADR-0099 put it.

## Capability coverage

Every section of each overview has a disposition. "In use" means production code relies on it.

### pglast

| Overview sections | Disposition |
|---|---|
| §1–2 architecture; raw parse tree only | In use as the stated boundary (ADR-0047) |
| §3 parsing; node serialization and cloning | In use (`prepared_sql.py`). JSON and Protobuf forms: no fit |
| §4 typed nodes, validation, equality | In use for edits; equality as an edit check: **I05** |
| §5 visitors, relation discovery | In use (authored SQL, model explanation). Visitor actions: conditional on a rewrite that needs them. Scoping defect: **I07** |
| §6 scanner, keywords, splitting, coordinates | Splitting and displacements in use; scanner and keywords: no fit |
| §7 and addendum §1 fingerprints | No fit. They ignore function bodies, options, schemas and constants; raw-text digests are the right identity |
| §8 streams, formatting, Protobuf deparse | `RawStream` in use; formatting and the second deparser: no fit |
| §9 custom printers | No fit. The registry is process-global |
| §10.1 comments | Constraint on **I05** (comments are lost) |
| §10.2 and addendum §5 PL/pgSQL parsing | Tests only. It checks syntax and variables offline and exposes embedded statements as text; conditional on an authoring failure that the rollback candidate catches late |
| §11–14 applications, adjacent libraries, limits | Covered by I05 and I07; licence is not a criterion |
| Addendum §2–4 traversal internals, printer internals, source spans | No fit, except named trigger constants: **I05** |
| Addendum §6 corrections | Noted; `parser.normalize` is not in 8.7 |

### sqlglot

| Overview sections | Disposition |
|---|---|
| §2 parsing and expression model | Builders in use; text parsing at one site |
| §3 and addendum §11–13 dialects, transpilation, generator transforms, pipe syntax, time formats | No fit. One target dialect; ADR-0047 rejects sqlglot as an execution representation |
| §4 schema, qualification, scopes, typing | In use. UDF typing: no fit while recipes carry their own types |
| §5 optimizer | No fit. Output is not stable across minor releases and cannot be identity |
| §6 lineage | In use over checked recipes (ADR-0074) |
| §7 diff | In use for model explanation of single selects |
| §8 serialization, anonymization; §9 JSONPath | No fit |
| §10 planner and executor | No fit. A second engine cannot supply independent expectations for PostgreSQL |
| §11–13 extension, diagnostics, versioning | The runtime tuple is already captured as a determinant |
| Addendum §1–4 traits, expansion, placeholders, structural accessors | Expansion in use with its own cycle checks; the rest no fit |
| Addendum §5 DDL, grants, opaque commands | No fit; hazard in **I07**. pglast and ADR-0103 own these |
| Addendum §6–10 types, pivot, DSL, comment directives, diagnostics | Type building in use; the rest no fit |
| Addendum §14–15 SQLFrame, boundaries | No fit; boundaries noted in **I07** |

### psycopg

| Overview sections | Disposition |
|---|---|
| §2 implementations, libpq capabilities | Binary wheel with libpq 18; `cancel_safe` timeouts are effective |
| §3 binding, `sql` composition, template strings, cursor classes | Through SQLAlchemy. `sql` at COPY sites. Template strings: no fit beyond driver sites |
| §4 prepared statements | Defaults. Rolling back to a savepoint clears the cache; noted, no action |
| §5 and addendum §7 pipeline mode | No fit. Experimental; no COPY; unused by SQLAlchemy |
| §6 and addendum §5 COPY | In use, both writers. COPY TO, offline COPY files, `executemany(returning)`: no fit |
| §7 and addendum §3 adaptation | JSON adapters in use; exact codec through text (JSON row above). Array and typed-row binding: in use for hydration pins since `7c26b596e` (**I01**). Enums, composites, ranges, NumPy, Shapely: no fit |
| §8 row factories and typing | No fit; they would change SQLAlchemy rows |
| §9 and addendum §6 results, server cursors, streaming | Named cursors through `yield_per` in retained and legacy readers, and in DDO hydration with a fetch size of one (**I01**). A cursor over a PL/pgSQL set function bounds only the transfer: **I06**. `stream()` and adopted cursors: no fit |
| §10 and addendum §2 transactions | SQLAlchemy owns them. Two-phase commit: no fit |
| §11 and addendum §8 concurrency, cancellation | `cancel_safe` in use. Async: no fit |
| §12 pooling | See psycopg-pool |
| §13.1 and addendum §8.2 LISTEN/NOTIFY | Conditional on a wakeup consumer; demand-planning:209 says none is needed |
| §13.2–13.5 notices, SQLSTATE classes, connection info, libpq | Notices and connection info in use. Failure meaning: **I03** |
| §14–19 ecosystem, trade-offs, limits | Baseline; session state addressed in **I02** |
| Addendum §1, §4 pool operations, binary control, capabilities | See psycopg-pool; binary parameter control: no fit |

### psycopg-pool

| Overview sections | Disposition |
|---|---|
| §1–3 pool types, ownership, borrowing | One synchronous pool lent through `getconn` with `close_returns`; in use |
| §4 sizing and admission | In use; relation to executor bounds: **I02** |
| §5 `configure`, `check`, `reset` | `configure` and `check` in use; `reset` deliberately absent: **I02** |
| §6 and addendum A5–A6 null pools | No fit; `close_returns` is ignored there |
| §7 recovery, timeouts, health | Defaults; `reconnect_failed`: conditional on a long-lived server needing escalation |
| §8 and addendum A1–A3 open, resize, drain, dynamic parameters, zero-minimum pools | Explicit open and wait in use; the rest no fit with static credentials |
| §9 and addendum A7 statistics | `get_stats` in use; the store already records that `usage_ms` excludes its route |
| §10 SQLAlchemy integration | In use as documented; side effect in observed defect 1 |
| §11 typing, prepared statements, composition | No fit beyond defaults |
| §12–14 and addendum A4, A8 versions, limits, ownership semantics | Noted; no 3.3.4-only behavior is relied on |

### pgpq

| Overview sections | Disposition |
|---|---|
| §1–2 and addendum §2 encoder lifecycle, stream integrity | In use and guarded (`arrow_transfer.py`), including under DDO PDF claims and archive admission |
| §3 type mapping, unsupported types | In use; the profile refuses the unsupported cases |
| §4 and addendum §1 lists, structs, generated DDL | No fit. A float list encodes as `real[]`, not `vector`; the model is the schema authority |
| §5 and addendum §3 JSONB encoders | In use. `arrow-json`: no fit |
| §6 staging then SQL transformation | In use; the accepted shape (ADR-0098, ADR-0099) |
| §7 performance | Qualitative only |
| §8 limits, PostgreSQL constraints | Baseline; binary COPY applies no casts, hence typed staging |
| §9–10 Rust crate, packaging | No fit. Alpha classifier noted |
| Addendum §4–5 extension boundaries, progress view | No fit; `pg_stat_progress_copy` conditional on an operator diagnostic |

### pgvector

| Overview sections | Disposition |
|---|---|
| §2 types and representations | `vector` in use; `halfvec`, `sparsevec`, `bit`: no fit; residue in observed defect 3 |
| §3 driver registration | No fit on the shared pool; the DDO route does not use it (**I04**) |
| §4 SQLAlchemy types and comparators | In use (cosine), including typed `VECTOR(d)` binds for the DDO transient relation. Other frameworks: no fit |
| §5–6 approximate indexes, iterative scans, quantization, subvectors | No fit; behind D3's scale trigger. A transient relation cannot be indexed, so the DDO route is exact by construction (**I04**) |
| §6.4 server-side vector functions | In use for validation |
| §7 hybrid, sparse and multivector retrieval | Hybrid ranking exists by design; the rest no fit |
| §8 bulk loading, index maintenance, planning | No fit; the DDO route stores no vector column (**I04**) |
| §9–11 dimensions, invalid values, storage, versions | Dimension and finiteness are checked in Python before binding; the dimensionless column is legacy only (**I04**) |

### adbc-driver-postgresql

| Overview sections | Disposition |
|---|---|
| §2 interfaces, connection model | One factory in use; cloning: no fit |
| §3 and addendum §1 COPY results, batching, parameters | In use; literal arguments required for COPY: **I06** |
| §4 and addendum §2 ingest | No fit. Separate session; ADR-0026 |
| §5 and addendum §3 type mapping | In use; projection rules in **I06** |
| §6 type resolver modes | In use deliberately (`builtin` for data, `server` for description) |
| §7 and addendum §6 metadata and statistics | In use in `database_description.py` only |
| §8 and addendum §7–8 transactions, errors, cancellation | In use; errors already classified |
| §9 and addendum §5, §9 ecosystem, C stream, DuckDB extension | pyarrow only. The DuckDB extension is autocommit-only and cannot import a snapshot: no fit |
| §10–11 limits, versions | Baseline |
| Addendum §4 manifests and profiles | No fit; rejected 2026-10-29, premise unchanged |
| Addendum §10 libpq parameters | `application_name`: **I02** |

## Rule impacts and package integration

| Recommendation | Packages | Rule impact |
|---|---|---|
| I01 | DDO-05, 06 | None; realizes the adopted read route. Executor half implemented; native half needs a native successor |
| I02 | DDO-06 | Revises D3:805 and D9:175 on pool ownership |
| I03 | DDO-06, retained infrastructure | None |
| I04 | DDO-08; D3 owner | Plan and D3 text for the implemented contract. Code changes only if the parameter ceiling is checked where the profile is admitted |
| I05 | DDO-04 | None |
| I06 | DDO-10 | When triggered: ADR-0026 snapshot import kept or succeeded |
| I07 | DDO-09, 10 | None |

Earlier verdicts carried forward unchanged: no null pool behind SQLAlchemy; no ADBC ingest
without a change of session owner; pgpq DDL is not a schema authority; sqlglot is not an execution
representation; approximate search waits for its trigger; LISTEN/NOTIFY waits for a wakeup
consumer. One earlier condition has been met: concurrent pools now have a consumer (I02).

## Evidence account and limits

- **Interface-checked, 2026-11-14.** Code and plan citations were read by the root at
  `0463cb997`. Library contracts were confirmed in installed source and upstream source at
  matching tags. No recommendation rests on a database run.
- **Re-check, 2026-11-14 at `ee683f3e9`.** The root compared every cited file with the baseline.
  Most of the code files cited are unchanged; the changed ones were re-read where cited and
  their citations restated. Plan and design line citations are to committed text; the working
  tree holds uncommitted insertions by the DDO root that shift D3 and contracts-and-compilation
  by a few lines. New reading: the hydration, binding-validation, contextual-retrieval
  and product-page code named in I01, I04 and I06; the coordinator's resumed-execution and
  current-implementation accounts and its retirement table; ADR-0105. Installed versions of the
  seven libraries, pyarrow and SQLAlchemy are unchanged. That `yield_per` selects a server-side
  cursor with the stated fetch size was confirmed in installed SQLAlchemy source. The parser scan
  of native SQL files was repeated. No subagent took part in the re-check, and no test, provider
  or database operation was run. The uncommitted work of the concurrent DDO root (a bound-row
  native successor and edits to D3, the coordinator and three companions) was read where it
  touches a citation and is not otherwise assessed.
- **Offline checks, unretained.** In-process checks without a database supported four statements:
  body preservation and the dollar-tag case in I05, the two parser hazards in I07, the float
  round trip in I04, and a stub of the notice-handler path in defect 1. Each statement is also
  supported by cited source. The scripts are in the session scratchpad and are not evidence
  records; any that becomes decisive for an adopted change should be re-run inside the consuming
  package.
- **From the maps, spot-checked only.** The list of about twenty direct SQLSTATE sites, the
  count of JSON cast sites, the quoting sites and the reader inventory come from the usage
  maps. The root verified the sites cited by line. A text search at `ee683f3e9` finds nineteen
  direct SQLSTATE comparisons outside the classifier and forty JSON cast sites.
- **Not established.** Binding sizes, so whether the native half of I01 matters at current
  scale; whether a population predicate reads body fields from unselected rows (I01). How often
  port workers hold connections concurrently (I02). The cost of resending a vector inventory per
  query (I04). Member and body sizes for any DDO family. That
  COPY over a `SECURITY DEFINER` function behaves as reasoned (I06). Whether the legacy compiler
  needs the `halfvec` mapping (defect 3). The "two canonical forms of argument types" lead from
  the usage map was not verified and is not used.
- **Coverage limits.** The coordinator was read in its amendment, receipt, audit, retirement and
  remaining-scope sections. Demand-planning, products-and-support, interfaces-and-evaluation,
  operations-and-adapter-cutover, contracts-and-compilation and change-reuse were read in the
  passages cited; the other four companions were covered through the document map. The draft
  missed scheduled work in passages it had not read, which the challenge found. The re-check did
  not re-read the companions beyond the passages cited. The 54 native SQL files were scanned by
  parser, not read; four templated files do not parse before rendering and are outside the
  `SECURITY DEFINER` count.
- **Tests and qualification.** Product tests, native controls, providers and health checks:
  not_run, by standing cancellation. Closure evidence named above is future focused evidence,
  not a command this review authorizes.
