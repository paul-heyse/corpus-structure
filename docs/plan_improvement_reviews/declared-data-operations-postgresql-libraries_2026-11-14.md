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

**Concurrent work at publication · 2026-11-14.** The tree was clean when the review began. Before
it was published, the DDO root made uncommitted edits to the coordinator, one companion and
`STATUS.md`, which this review does not touch. They add a "DDO-06–08 resumed execution" section
that already schedules hydration as joins of exact selection pins to one binding-row base per
bounded page, with every comparison and the byte limits preserved. That is the substance of I01
below; I01 remains as the source reasoning and closure evidence for it. The same section notes
this review while it was an untracked draft. That draft proposed a typed staged route for product
members, which this published version withdraws; nothing in the withdrawn proposal should be
taken forward from the draft.

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

What remains is five recommendations and two conditional ones:

- **I01** replaces per-member hydration, which re-evaluates an unpaged table function for every
  member, with one set read per binding. This is the clearest inefficiency found.
- **I02** bounds the executor's database concurrency. Claim renewal shares a four-connection pool
  with port workers, which the plan says it must not wait behind.
- **I03** gives raised database errors one contract and removes a dependency on message text.
- **I04** asks DDO-08 to state the vector contract before contextual retrieval migrates. The plan
  is silent on vectors.
- **I05** is a low-priority cleanup of native declaration edits and duplicated derivations.
- **I06** and **I07** are conditional: an Arrow read transport for DDO-10, and a cross-check of
  declared read inputs against compiled SQL.

Five observed defects are listed separately. Most of what the overviews offer has no current fit,
and the coverage tables say why.

## Current footprint

| Owner | Observed contract (Interface-checked 2026-11-14) | Significance for the lens |
|---|---|---|
| DDO generic write path, `P/semantic/data_operation_storage.py:376–397` | Every native operation is `ops.<name>(jsonb) → jsonb`; the payload is sent as text and cast. A completion is refused in Python above 64 MiB (`P/orchestrate/data_operations.py:715–716`). | One deliberate transport for product bodies, with an explicit limit. |
| DDO recovery protocol, `data_operations.py:718–784` | Retaining the completion intent and publishing it are separate transactions; a later attempt can adopt the retained intent (coordinator:90). | Anything a completion needs must survive between those transactions. |
| DDO product identity, `P/semantic/sql/data_operations.sql:1062–1084` | Product identity digests the canonical body, which embeds every member packet; each member body must equal its packet. | Member bodies are part of the product's identity, not only its storage. |
| DDO PDF capture, `P/semantic/pdf_capture.py:187–273`; `P/semantic/pdf_staging_native.py:52–91` | Under a DDO claim the port stages PDF records through `copy_arrow_stream`; staging accepts a DDO task by decision (ADR-0099). The DDO product binds the sealed publication's receipt. | DDO already uses typed staging where a decision places it. |
| Arrow writer, `P/semantic/arrow_transfer.py:60–171` | Refuses nanosecond timestamps and inexact numerics; checks pgpq's emitted schema against declared wire types; full schema equality per batch; explicit column list; fresh encoder per COPY; no footer after an error. | Guards every pgpq hazard the overview lists. |
| DDO reads, `P/semantic/data_operation_consumers.py:228–262`; `data_operation_storage.py:893–901`; `data_operations.sql:1673–1688` | `ops.data_binding_rows` is a PL/pgSQL `RETURN QUERY` function with no limit. Hydration issues one query per member against that function, with eleven predicates and an exactly-one-row check. | See I01. |
| DDO read acquisition, `data_operations.sql:1364–1380` | `read_demand_result` inserts trust scopes, takes `FOR SHARE` locks and records the read, also when a `read_id` is supplied. | It is an effect, not a pure read; see I06. |
| DDO Core read bodies, `P/semantic/data_operation_projections.py:311–316, 1009–1051` | Core selects compiled with `literal_binds`, captured with the whole physical model as input identity, substituted into PL/pgSQL at placeholders. | The route the adopted SQLA/Alembic I02 describes. |
| Pool and engine, `P/core/db/store.py:45–54, 132–156` | One `ConnectionPool` per opened purpose, `close_returns=True`, `check_connection` per checkout, JSON adapters in `configure`; SQLAlchemy borrows through `creator=pool.getconn` with `NullPool`. No `reset`. | The documented integration. |
| Executor, `P/cli/demands.py:180–182`; `data_operations.py:462, 1010–1011, 1066`; `P/semantic/claim_lifetime.py:296, 397` | Holds a write pool and an admission pool. Capacity is `min(max_claims, max_owned_bytes // reservation)`, two at defaults. A renewal thread and up to four port workers borrow from the write engine. | See I02. |
| Failure classifier, `store.py:231–304` | One translation of SQLSTATE, pool exceptions and ADBC status. About twenty other sites compare SQLSTATE strings. | See I03. |
| Vectors, `P/model/semantic/physical.yaml:49–52, 4345–4390`; `P/semantic/sql/source_contributions.sql:2453–2454, 3209, 3220` | Dimensionless `vector` columns keyed by task; values arrive as JSON in the task envelope and are cast through text, repeatedly. Search is exact. | Legacy route; no DDO vector kind exists. See I04. |
| ADBC reads, `P/core/db/adbc_lifetime.py`; `P/semantic/analytics.py:857–935`; `P/serve/companion_export.py:121–189` | Separate session importing the SQLAlchemy snapshot (ADR-0026), COPY-backed Arrow batches. | See I06. |
| Native authoring, 17 modules importing pglast | One parse entry, declaration identity, inventories, SQL-standard body insertion. Wrappers are f-string templates here and in the companion module (`P/semantic/companion_projection_native.py:24–88`). | Already the backbone (ADR-0047). |
| Projection analysis, `P/semantic/projection_analysis.py` | sqlglot qualification, typing and lineage over the checked recipe (ADR-0074). | Recipe-carried metadata is the authority. |

An offline pglast scan of the 53 native SQL files found 345 functions in the 49 that parse before
templating; all 179 that are `SECURITY DEFINER` also fix `search_path`. That convention holds
without a rule, so the review proposes none.

## One responsibility, several mechanisms

"Go-forward" names the mechanism an accepted owner selects. Where no owner does, the row says so.

| Responsibility | Mechanisms in use | Go-forward and its owner | Lagging | Disposition |
|---|---|---|---|---|
| Write of product data | One JSON document to a native function (DDO generic products); Arrow binary COPY to typed staging (PDF under legacy and DDO tasks, Arrow publication, archive); text COPY rows (publication); `complete_task` envelope (legacy tasks) | JSON document for product bodies (wire protocol); typed staging for PDF (ADR-0099) and archives (ADR-0098); one transport per responsibility (ADR-0098) | None. The legacy branch of PDF staging retires with runs | Consistent with decisions. A typed member route was considered and withdrawn |
| Hydration of bound inputs | One query per member over an unpaged table function | Keyed, demand-scoped set reads (adopted SQLA/Alembic I02; demand-planning:235–236) | DDO executor | **I01** |
| Public reads | Paged JSON functions; ADBC Arrow over an imported snapshot; `yield_per` cursors; materialized rows | One pinned projection through guarded functions with scope, cursor and limit as parameters (interfaces-and-evaluation:10–20, 42–43) | No DDO read owner in `serve` or `intervene` yet (coordinator:1188) | DDO-10 owns it; Arrow transport **I06**, conditional |
| Executor database concurrency | Pool bounds in settings; claim, byte and worker bounds in the execution policy | None stated. D3:805 says one pool per process | The two sets of bounds are independent; renewal shares the pool | **I02** |
| Meaning of a raised database error | Central classifier; about twenty direct SQLSTATE comparisons; one comparison with English message text; declared `NativeDiagnosticBinding`; DDO refusals in the result envelope | The classifier plus declared bindings | Retained modules that compare directly; claim renewal | **I03** |
| Vector storage and search | JSON cast to `vector` in native SQL; typed `VECTOR(d)` binds; JSONB path reads of cached vectors; residual `halfvec` mapping | Exact cosine over a materialized inventory with pgvector's SQLAlchemy types (D3 "current bounded route") | No DDO vector kind; plan silent | **I04** |
| Edits to native declarations | Parse-tree edits for SQL-standard bodies; f-string wrappers; string replace for renames; placeholders for compiled Core | pglast for declarations (ADR-0047); placeholders and PL/pgSQL wrappers for guarded reads (adopted I02) | String renames in the DDO kernel and `native_candidate.py` | **I05**, low priority |
| Derivation of one native fact | Two production copies of the descriptor-literal extraction; bare integers for trigger flags | One helper per fact | `source_view_native.py:21–42`, `execution_admission.py:508–536`, `:232–233` | **I05** |
| Dependencies of a read | sqlglot analysis of checked recipes (ADR-0074); whole-model closure for DDO Core bodies; declared relations for change determination (change-reuse:44–50) | Declared contracts and relations | None | Consistent; cross-check **I07**, conditional |
| JSON across the boundary | Pool codec (`json`, floats); DDO exact-decimal codec through text casts; 44 legacy `CAST(:x AS jsonb)` sites | For DDO: `json_bytes` and `ContextJSONB` (`P/semantic/data_operation_json.py`) | Legacy string casts | Deliberately different. psycopg can scope a codec per connection, cursor or value, but SQLAlchemy owns the cursor and wraps values itself, so a per-column exact codec goes through text. Legacy sites retire with `complete_task` |
| Identifier quoting | SQLAlchemy preparer; psycopg `sql.Identifier` at COPY sites; hand-rolled in five modules | SQLAlchemy preparer for SQL text, psycopg `sql` at the driver | `cli/db.py:63–68` and four other modules | Align when touched |
| Run supervision | Dedicated session with a session advisory lock (`P/orchestrate/liveness.py`) | Native demand and fulfillment (RC05, coordinator:52) | All consumers are legacy run and stage commands | Retires with coordinator:1184 |
| Transactions, cancellation, waiting | SQLAlchemy `begin` everywhere, one SERIALIZABLE owner; `cancel_safe` and `adbc_cancel` under one handle; polling | As implemented (D8; demand-planning:209) | None | Consistent; no action |

<a id="I01"></a>
## I01 — Hydrate bound inputs in sets

**Recommend.**

**Current approach.** To hydrate a consumer's inputs the executor loops over every member of
every role and runs one statement per member (`data_operation_consumers.py:234–252`). Each
statement selects from `ops.data_binding_rows(...)`, a PL/pgSQL function that returns its whole
result with `RETURN QUERY` and takes no limit. PostgreSQL materializes such a function's full
result before the caller filters it, so the binding population is recomputed once per member.
The cost grows with members times population, not with members.

The adopted SQLA/Alembic I02 text already asks for "keyed, demand-scoped joins and bounded
pages", and demand-planning:235–236 for "a bounded page of compact identities" before hydration.
The row shape moved to Core in the foundation work; the access pattern did not.

**Proposed change.**

1. Hydration evaluates the binding function once per binding and joins it to the retained member
   identities, passed as one array parameter or a `VALUES` relation. Every predicate of the
   current per-member query stays, as join conditions. The result is checked for exactly one row
   per retained member, which keeps the present refusal.
2. The byte charge is unchanged: canonical decoded size times multiplicity. The set read may add
   a coarse pre-check on stored size to refuse early, but it does not replace the charge.
3. `data_binding_rows` gains limit and continuation parameters, or its callers establish that the
   demand-scoped population is bounded. Which one is DDO-05's decision.

**What it retires.** The per-member statement loop.

**Benefit (Proposed).** Hydration work follows the size of the binding, once. No new mechanism
is involved: psycopg and SQLAlchemy bind arrays natively.

**Preserved guarantees.** The exactly-one-admitted-body check, the trust and support predicates,
the byte capacity rule and the function's `SECURITY DEFINER` boundary.

**Uncertainty.** Whether any binding is large enough for this to matter today was not measured.
The argument is structural.

**Alternative.** Keep the loop and add a cache of the function result in Python. That moves the
set into the client and keeps N round trips.

**Challenge case.** A member retained by an earlier attempt that no longer has an admitted body
must still refuse. A join silently drops it unless the row-count check is kept; step 1 keeps it.

**Affected packages.** DDO-05 (hydration), DDO-06 (planner reads).

**Closure evidence.** A multi-member role hydrates with one statement and the same values; a
revoked member still refuses, with the expectation written independently of the query.

<a id="I02"></a>
## I02 — Bound the executor's database concurrency

**Recommend. Rule impact for the ADR route.**

**Current approach.** D3:805 and D9:175 say one pool per process. Each opened purpose has its
own pool, and the DDO executor holds a write pool and an admission pool for its run
(`cli/demands.py:180–182`). Pools default to four connections and four waiters.

Three kinds of thread borrow from the write engine: the driving thread, the claim-renewal thread
(`claim_lifetime.py:296, 397`), and up to four port workers (`data_operations.py:1066`), which
can open their own transactions, as PDF capture does (`pdf_capture.py:189–249`). That is six
possible borrowers for four connections. Nothing refuses at defaults, because four may wait, but
renewal can queue behind port work. Demand-planning:296–297 says "Renewal has its own finite
database operation and does not wait behind provider work".

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

**Recommend. Small.**

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
## I04 — State the vector contract before contextual retrieval migrates

**Recommend, as plan content for DDO-08 and DDO-04.**

**Current approach.** Operations-and-adapter-cutover:49–51 lists contextual retrieval for DDO-08.
The plan does not mention vectors, embeddings or pgvector, and no DDO kind carries one. The
legacy producer writes vectors as JSON arrays in the task envelope; native SQL casts each through
text to `vector` for a dimension check, a norm check and each insert, and
`ops.contextual_mutual_neighbors` casts again per read. Cached vectors are read back with
`jsonb_path_query_array` over stored task results. Search binds typed parameters and is
deliberately exact.

DDO members are tagged JSON values, with floats as hex (contracts-and-compilation:231–232), and
their bodies are part of product identity. Similarity search needs a `vector` column. The plan
already allows "kind-specific projections" beside the common member table
(products-and-support:24–25). Nothing yet says how a vector member becomes a searchable column.

**Proposed change.** DDO-08's contextual-retrieval package states, before implementation:

1. **Where the vector is authoritative.** As a member value under the existing identity rules,
   with the `vector` column a derived, rebuildable projection written by the publishing function.
2. **How the projection is derived.** pgvector provides casts to `vector` from `real[]`,
   `double precision[]`, `numeric[]` and from text; it rejects NaN and infinity on each. It has
   no conversion from the tagged hex form, so the package names the native step that produces one
   of those inputs, once per vector.
3. **What stays fixed.** FP32 storage, exact cosine over the materialized inventory, native
   dimension and unit-norm checks. The projection carries no approximate index: pgvector answers
   the same query approximately as soon as an applicable index exists, and D3's scale trigger
   governs that decision.
4. **How reuse reads vectors.** From the projection, not from stored task results, since product
   identity replaces task provenance (coordinator:1189).
5. **What is not adopted.** `register_vector` on the shared pool, which would change what
   existing SQLAlchemy consumers receive. Binary COPY of vectors through pgpq, which cannot target
   a `vector` column and would need the typed route this review withdrew.

**Benefit (Proposed).** The migration starts from a decision instead of inheriting the envelope
casts, and the exact-search guarantee is written where an index could later break it.

**Uncertainty.** The value route through JSON text is exact today: an unretained offline check
found no float32 value changed by it. The case for restating the contract is typing and
authority, not a correctness defect.

**Alternative.** Migrate the operation and keep `kb.contextual_vector` on the legacy envelope.
That leaves vector reuse keyed by task while everything around it is keyed by product.

**Challenge case.** A dimensionless column cannot be indexed, and the search casts only its
parameter (`P/semantic/contextual_retrieval.py:422–423`). If the scale trigger fires, column
expression and query change together. That is a reason to record the invariant now.

**Affected packages.** DDO-08, DDO-04.

**Closure evidence.** The plan section exists; then stored vectors equal independently computed
float32 values, a non-finite value and a wrong dimension refuse, and retrieval matches the legacy
route on a fixed inventory.

<a id="I05"></a>
## I05 — Edit declaration headers through the parse tree; one helper per native fact

**Recommend. Low priority; do it when the code is next changed.**

**Current approach.** The DDO kernel renames each protocol function by replacing the literal text
`CREATE OR REPLACE FUNCTION ops.<name>(` (`data_operation_storage.py:203–219`).
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
in Python is correct and simple until a columnar consumer exists.

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
the whole physical model.

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

If a family does reach the limit, the decision belongs with those owners and with ADR-0098's
single-route reasoning. One observation is left for the physical owner, outside this lens: a
member body is stored in the retained intent, in the product's canonical body and in its member
row, and is schema-checked at each.

## Observed defects

These were found while reading and need no plan change to fix.

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

Priority by consequence: I01, I02, I03, I04, I05; I06 and I07 wait for their triggers.

The five are independent of one another. I01 can land with the next DDO-05 or DDO-06 change. I02
and I03 touch the executor and the store and can share one change. I04 is plan content that
should precede the DDO-08 contextual-retrieval package. I05 waits for the next change to the
kernel assembly.

I02 revises a statement in D3 and goes through the ADR route. I06, if triggered, interacts with
ADR-0026. None of the five needs a native successor.

Taken together the set is small. It adds no mechanism, changes no accepted decision other than
the pool statement, and leaves the transfer design where ADR-0098 and ADR-0099 put it.

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
| §7 and addendum §3 adaptation | JSON adapters in use; exact codec through text (JSON row above). Array binding: **I01**. Enums, composites, ranges, NumPy, Shapely: no fit |
| §8 row factories and typing | No fit; they would change SQLAlchemy rows |
| §9 and addendum §6 results, server cursors, streaming | Named cursors through `yield_per` in retained and legacy readers; a cursor over a PL/pgSQL set function bounds only the transfer: **I06**. `stream()` and adopted cursors: no fit |
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
| §4 and addendum §1 lists, structs, generated DDL | No fit. A float list encodes as `real[]`, not `vector` (**I04**); the model is the schema authority |
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
| §3 driver registration | No fit on the shared pool: **I04** |
| §4 SQLAlchemy types and comparators | In use (cosine). Other frameworks: no fit |
| §5–6 approximate indexes, iterative scans, quantization, subvectors | No fit; behind D3's scale trigger. Invariant in **I04** |
| §6.4 server-side vector functions | In use for validation |
| §7 hybrid, sparse and multivector retrieval | Hybrid ranking exists by design; the rest no fit |
| §8 bulk loading, index maintenance, planning | No fit; casts for derivation in **I04** |
| §9–11 dimensions, invalid values, storage, versions | Dimensionless column noted in **I04** |

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
| I01 | DDO-05, 06 | None; realizes the adopted read route |
| I02 | DDO-06 | Revises D3:805 and D9:175 on pool ownership |
| I03 | DDO-06, retained infrastructure | None |
| I04 | DDO-04, 08 | New plan content; records the no-approximate-index invariant with the physical owner |
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
- **Offline checks, unretained.** In-process checks without a database supported four statements:
  body preservation and the dollar-tag case in I05, the two parser hazards in I07, the float
  round trip in I04, and a stub of the notice-handler path in defect 1. Each statement is also
  supported by cited source. The scripts are in the session scratchpad and are not evidence
  records; any that becomes decisive for an adopted change should be re-run inside the consuming
  package.
- **From the maps, spot-checked only.** The list of about twenty direct SQLSTATE sites, the
  count of 44 JSON cast sites, the quoting sites and the reader inventory come from the usage
  maps. The root verified the sites cited by line.
- **Not established.** Binding sizes, so whether I01 matters at current scale. How often port
  workers hold connections concurrently (I02). Member and body sizes for any DDO family. That
  COPY over a `SECURITY DEFINER` function behaves as reasoned (I06). Whether the legacy compiler
  needs the `halfvec` mapping (defect 3). The "two canonical forms of argument types" lead from
  the usage map was not verified and is not used.
- **Coverage limits.** The coordinator was read in its amendment, receipt, audit, retirement and
  remaining-scope sections. Demand-planning, products-and-support, interfaces-and-evaluation,
  operations-and-adapter-cutover, contracts-and-compilation and change-reuse were read in the
  passages cited; the other four companions were covered through the document map. The draft
  missed scheduled work in passages it had not read, which the challenge found. The 53 native SQL
  files were scanned by parser, not read; four templated files do not parse before rendering and
  are outside the `SECURITY DEFINER` count.
- **Tests and qualification.** Product tests, native controls, providers and health checks:
  not_run, by standing cancellation. Closure evidence named above is future focused evidence,
  not a command this review authorizes.
