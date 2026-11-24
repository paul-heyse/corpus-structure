# The kernel trial

**Status:** SBX-18 and SBX-19 have open completion obligations. The typed scoped-relations route is adopted. Companion of [Set-based execution](../set-based-execution_2026-11-21.md).
**Created:** 2026-11-21.

This companion owns one kernel family rebuilt as set operations over tables, as a trial that
ends in a recorded decision on whether other families follow. It owns SBX-18 and SBX-19. Source
facts are **Inspected** at `7a415d18d`; the library behaviour cited is reproduced by the retained
checks in `docs/design_review/evidence/2026-11-21_columnar-execution-review/` and by the checks
the trial investigation ran, which are re-run and retained by SBX-18.

**Scheduled amendment · 2026-11-22.** The [common analytics review I02](../../plan_improvement_reviews/set-based-execution-common-analytics_2026-11-22.md#I02)
and [I03](../../plan_improvement_reviews/set-based-execution-common-analytics_2026-11-22.md#I03)
expand the comparison to captured DuckDB SQL and PostgreSQL-native set work. The
[common analytical basis](common-analytical-basis.md#typed-population-pilot) owns the earlier
annotation-fork pilot and its dated immutable-carrier decision. The
[reconciled columnar target](common-analytical-basis.md#columnar-population-target) proposes a
replacement producer-to-consumer path. SBX-18/19 consume applicable evidence and keep their
complete scoped-relations family trial downstream. The
[pinned-build probe](../../design_review/evidence/2026-11-22_sbx-common-analytics/README.md)
establishes fixture-level DuckDB 2.0.0 and PyArrow 26.0.0 behavior, including a typed window
through the existing owner and blocked connection use until an active result is drained.
Production adoption and integrated qualification remain open.

**Efficiency amendment · Scheduled · 2026-11-22.** The
[validation and PostgreSQL review I06](../../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md#I06)
adds complete-path comparison and exact wide-value conditions to the existing trial.
The post-cutover baseline is the current acquired typed route and retained SBX-10 indexes.
SBX-18 owns the remaining resource and durable-output work. SBX-19 compares one complete
scoped-relations candidate using the shared
[transfer](common-analytical-basis.md#postgresql-placement-and-transfer) and
[numeric fidelity](common-analytical-basis.md#numeric-fidelity) contracts. The
[post-cutover review I06](../../plan_improvement_reviews/set-based-execution-after-sbx09_2026-11-23.md#I06)
and [deeper review I13](../../plan_improvement_reviews/set-based-execution-after-sbx09-deep-review_2026-11-23.md#I13)
refine the comparison.

<a id="columnar-analytical-prerequisites"></a>
## Shared analytical prerequisites brought forward

**Proposed · 2026-11-22.** The [reconciled amendment](../set-based-execution_2026-11-21.md#columnar-redesign-amendment)
brings the shared fidelity, resource and query-custody parts of SBX-18 before the first typed
population slice. Those prerequisites serve SBX-01–09 and are owned in the
[common analytical target](common-analytical-basis.md#columnar-population-target). SBX-19 still
owns the scoped-relations implementation, independent expected results and adopt, adjust or
stop decision for that family. The bulk validation design does not establish that another
kernel's semantics can move into the engine.

Use DuckDB 2.0.0 through the existing analytical owner for relational plans, `from_arrow(pa.Table)`
for reusable known populations, and `to_arrow_reader(batch_size=...)` for incremental output.
Windows, range and semi/anti joins, ordered aggregates and `EXCEPT ALL` express the population
work. Prepare declared shapes once per model and implementation identity. Explicitly own
materialization for multiple consumers. Keep a reader single-use unless the input is deliberately
materialized. Set binary collation, UTC, observable order, NULL placement and tie rules. Retain
exact canonical values where the engine's types or functions differ from the domain.

Arrow 26.0.0 owns schema, batches, IPC and suitable direct column kernels. Acero remains a
candidate for a specific filter/project stream whose input, output, buffer and cancellation
lifetimes remove work. The small paused-consumer probe shows read-ahead on that fixture. It
cannot establish the general absence of backpressure. Python's exposed options, retained
operator state and spill support must match the selected responsibility. A second relational
planner requires its own concrete integration benefit.

Configure `pa.set_cpu_count`, `pa.set_io_thread_count`, scanner readahead and DuckDB `threads`,
async I/O settings, `memory_limit` and private spill under the existing execution-policy owner.
A buffer-manager limit does not cover complete process memory. Preserve captured code and
model correspondence, cancellation drain and final resource release. These obligations are
prerequisites for the actual worker path, without a separate broad qualification campaign.

**Resource slice · Tested by selected identity · 2026-11-22.** The configured analytical
owner sets binary collation and bounds DuckDB asynchronous I/O by the captured thread count.
Spawned CPU workers initialize Arrow CPU and I/O pools from the existing native thread
policy. `uv run ci test --workers 1 -- python/corpus-structure/tests/test_analytics.py`
passed 11 identities, including the real spawned-consumer control
(`e789cc5d3eca4d239c3991964c28e43c`). The CPU worker and in-flight cancellation selection
also passed (`66a858e58d634dc18d3f97a5361195d2`). Typed IPC cleanup remains part of the
replacement worker acceptance.

**Canonical production and authoring.** [ADR-0154](../../adr/0154-sbx-columnar-populations.md)
permits model-derived canonical item text and ordered digest aggregation in the affected
population families, subject to exact parity with the existing identity definition and
independent Python reference. Keep typed authoring under ADR-0135. Captured raw SQL remains a
candidate under the existing decision route. Independent fidelity cases
cover optional states, wide numbers, escaping, sets, bags and nested mappings before the
selected generator is used on supported collections.
[Rule routes](common-analytical-basis.md#decision-routes) ·
[Library controls](../../design_review/evidence/2026-11-22_sbx-columnar-basis/README.md)

## Why a trial and not a commitment

The review sampled kernels and found the procedural cores dominant. A first proposal for a
relational span layer was withdrawn because kernels ask span questions one at a time inside
procedural code. Two facts make a trial worthwhile all the same. In both families examined,
every question a kernel asks is known before the first answer, so the questions can be batched.
And the building blocks reproduce production functions exactly: selected source ranges
(1500 of 1500 cases), table header paths (800 of 800), and the three positioned-row queries.

## Choice of family: scoped relations

| | Formal evidence | Scoped relations |
|---|---|---|
| Set-shaped share of the kernel | About a tenth of the producer; the mass is the Lark and Earley cores | About half, in joins, lookups, grouping and windows; no parser |
| Per-item questions | Few in the producer; many in its readers | Many, all batchable; several re-scan every formal annotation per declaration |
| Consumers of its output | About thirty modules | Three or four |
| Fidelity risk | High: node ordinals in ids, a wall-clock parse deadline in product bytes, Unicode regular expressions | Medium: emission order across phases, key order inside hashed rows |
| What it teaches | How a parser-centred kernel behaves | The shape of most consumers in `cs/methods/` |

Scoped relations (`cs/methods/scoped_relations.py`, `discover_relations`;
`cs/semantic/scoped_products.py`) is the trial. It reads the source frame, construction
navigation records, formal annotations and predicate contributions, and writes participants and
relations.

*What it does not test.* It reads no token partitions, so it does not exercise typed rows derived
from partitions. If the decision is to continue, predicate evidence, the one kernel that joins
token tables, is the natural second family.

## Target for the trial

**Prepared relations.** Derive shapes from the
[model projection contract](common-analytical-basis.md#projection-contract) and acquire each
input once. Bring the retained SBX-10 span, source-view and navigation indexes to the baseline.
Trace remaining re-acquisition and reshaping in construction, formal and predicate contribution
preparation. Build the candidate's inventory once from acquired Arrow columns keyed by scope,
original occurrence and ordinal. Prepare source pieces and items with table cells unnested,
navigation records with roles and extents, formal inputs with symbols and occurrences,
predicate frames with readings and qualifiers, and passages. The formal inventory carries
selected product, projection, pointer, source start, representation and formal input. Its
occurrence tags keep independently produced reports distinct when they share local positions.
[Current preparation](../../../python/corpus-structure/src/corpus_structure/semantic/scoped_products.py#L127) ·
[Retained views and formula contexts](validated-values-and-handoff.md#sbx-10)

**The relational steps.** Find pieces, table geometry and header paths with range joins.
Use grouped counts for mentions and captions and a partitioned window for earlier rows under
the same parent. Join formal symbols per equation in one batched step. Match participants to
passages and source intervals by containment and overlap.

**The seam.** Regular expressions, `casefold`, edit distance and canonical scalar production
use the existing Python semantics wherever the pinned engine differs. Reconsider an individual
field only after independent positive and negative parity cases. Acquire typed rows and their
established invariants under SBX-08/04 before reuse. External input and conversions that can
change meaning receive their own validation at acquisition. Participants are staged before
anchors, anchors before ids, and ids before relations, because each id depends on the stage before it. Emission order
across the kernel's phases is reproduced by an explicit sequence column.

**Compared implementations.** Compare one complete DuckDB candidate with the current acquired
route using independent expected answers. Use the existing typed-expression owner as the
candidate default. Compare captured DuckDB SQL or a PostgreSQL-native placement for named
steps where authoring or crossing costs could change the decision. Direct Arrow compute remains
useful for simple column transforms. Compare preparation, conversion and cleanup with the
publication and read outcome. Capture explicit ordering, NULL placement, join multiplicity and
same-position tie semantics. Apply the shared canonical-text rules within their approved
scope. Scoped-relations identity keeps its Python publication contract unless a family decision
authorizes extending that scope.

The [PostgreSQL placement and transfer comparison](common-analytical-basis.md#postgresql-placement-and-transfer)
owns the shared cut, authorization, ADBC baseline and conditional extension investigation. Feed
its findings into this family's complete comparison. SQL authoring changes follow the
[decision routes](common-analytical-basis.md#decision-routes) before production adoption.

<a id="sbx-18"></a>
## SBX-18 — The analytical owner states the fidelity rules

**Pinned execution APIs · Scheduled · 2026-11-22.** On DuckDB 2.0.0, use the existing
`AnalyticalConnection.from_arrow(pa.Table)` and `Relation.select`, `join`, `aggregate`, `sort`
and `except_all` for the typed comparison. Build columns and constants with `duckdb.col` and
`duckdb.lit`. A typed ordinal window can use `duckdb.fn("row_number").over(partition_by=[...],
order_by=[duckdb.col(...).asc().nulls_last()])`. Use the existing `count_all().over(...)` where
the rule needs per-group counts. For a selected authoring comparison, express the named step as
a captured `con.sql(query, params=[...])` definition using `SEMI JOIN`, `ANTI JOIN`, `EXCEPT ALL`,
`row_number() OVER (PARTITION BY ... ORDER BY ... NULLS ...)`, `QUALIFY` and ordered aggregates.
Pair dense-order checks with duplicate cardinality and expected-scope anti-joins so a rank-only
comparison cannot hide a duplicate or absent group. Bind explicit role, occurrence and generation
keys where the fact needs them. Set `default_collation` to `binary` beside UTC. Apply the
shared canonical-text contract only within its approved identity and fidelity scope.
[Existing analytical owner](../../../python/corpus-structure/src/corpus_structure/analytics.py#L34) ·
[DuckDB 2.0 expression API](https://duckdb.org/docs/2.0/clients/python/expression) ·
[Window functions](https://duckdb.org/docs/2.0/sql/functions/window_functions)

The captured SQL route is a comparison candidate under the existing decision routes. A selected
change to authoring, connection lifetime or authority receives its operator decision and owning
ADR update before dependent production adoption. [Post-pilot library dispositions](common-analytical-basis.md#capability-dispositions)

**Owns.** In `cs/analytics.py`, the configured analytical execution boundary, fidelity
contract, captured query custody, input and output checks and connection/resource policy.
Set binary collation beside UTC, require explicit order and NULL placement where observable,
and declare multiplicity and tie behavior. Use the existing typed window capability before
adding helpers. Add a grouped aggregate or other helper only when the complete implementation
needs it and the helper simplifies the owned operation.

Compare captured named DuckDB SQL with typed expressions where it could change the trial
decision. Each maintained query has one owner,
exact captured definition, versioned dependencies, model-checked input/output shape and bound
values. Validate its declared relations before executing and preserve release correspondence
and production observability. PostgreSQL comparisons may use reviewed static SQL where installed
catalog, descriptor, privilege and candidate checks can establish the same guarantees as the
generated route. Keep caller values separate from query definitions. The actual selected SQL
policy follows the [decision routes](common-analytical-basis.md#decision-routes).

Retain the earlier synthetic timing observations with their original evidence and scope.
Compare production work qualitatively and time it only when setup, transfer, memory or spill
uncertainty can decide between conforming routes.

<a id="sbx-analytical-job-allocation"></a>
### One resource allocation per analytical job

**Baseline · Inspected · 2026-11-23.** Arrow CPU and I/O pools are initialized from the native
worker policy. The analytical connection takes DuckDB settings separately. The request
reservation covers hydrated input, packets, replies and drafts, while analytical workspace has
its own allowance. Concurrent jobs can multiply analytical state outside the existing
reservation. [Arrow worker initialization](../../../python/corpus-structure/src/corpus_structure/semantic/cpu_execution.py#L305) ·
[DuckDB connection settings](../../../python/corpus-structure/src/corpus_structure/analytics.py#L131) ·
[Request reservation](../../../python/corpus-structure/src/corpus_structure/orchestrate/data_operations.py#L363)

**Target · Proposed.** Extend the existing worker admission owner to supply one allocation for
engine workspace and spill, Arrow read-ahead and mapped buffers, and the already reserved
inputs, replies and drafts. Set PyArrow 26.0.0 process pools with `pa.set_cpu_count()` and
`pa.set_io_thread_count()` at worker initialization. Admit jobs within the pools the worker
has, and derive DuckDB 2.0.0 `threads`, `async_threads`, `memory_limit`, private
`temp_directory` and `max_temp_directory_size` from the allocation. The memory setting
governs DuckDB's buffer manager. Allow separately for other native allocations, Python, Arrow
and mapped files. The spill ceiling applies to the job's scratch directory. Keep reservations
until readers, spills, mapped inputs and outgoing drafts are released or handed to their next
owner. [DuckDB resource limits](https://duckdb.org/docs/2.0/operations_manual/limits) ·
[Arrow thread control](../../libraries/analytical_infrastructure/pyarrow.md#83-execution-parallelism-and-thread-control) ·
[Deeper review I14](../../plan_improvement_reviews/set-based-execution-after-sbx09-deep-review_2026-11-23.md#I14)

**Connection lifetime.** Invocation-owned connections and private spill directories are the
default. Each computation owns its temporary relations, registered inputs and readers.
Success, failure and stop finish or close each reader or end its DB-API result and release
all attached resources. Consider worker-wide reuse only if it removes material setup work
and the real worker route establishes equivalent isolation, drain and cleanup. Retire a
connection whose cleanup cannot establish it is usable.

DuckDB 2.0.0 `DuckDBPyRelation.to_arrow_reader(batch_size=...)` provides an Arrow
`RecordBatchReader`. Use it for incremental consumption and `to_arrow_table()` for deliberately
bounded complete materialization. Keep Arrow table owners alive for repeat evaluation. An input
`RecordBatchReader` is single-use unless explicitly materialized once. Drain or close each output
reader before another query on its connection. For an unfinished DB-API `execute()` result,
`DuckDBPyConnection.complete()` or `abort()` ends that result, while another `execute()` replaces
it. Use relation Arrow output to avoid the extra copied result path. Verify these distinct
lifetimes on the worker route. Incremental consumption does not establish bounded memory inside
a join or sort. [DuckDB 2.0 Python migration](https://duckdb.org/docs/2.0/clients/python/migration)

Verify the producer as well as the reader. Count or inspect the selected path's materialization
where that resolves uncertainty about whether all Python rows are constructed before the reader
is returned. Compare the relation's `to_arrow_reader(batch_size=...)` with a deliberately
bounded `to_arrow_table()` only where repeated access benefits from materialization.
Retain underlying Arrow owners until consumption ends and close on cancellation. Generic
decimal values wider than the engine supports use canonical tagged text for exact transport.
Arithmetic requires a compatible exact engine. Include declared bounded columns, mixed precision
and scale, a wider lexical decimal, UTC nanoseconds, null/absence and duplicate occurrences
in independent fidelity controls. [Shared numeric contract](common-analytical-basis.md#numeric-fidelity) ·
[DuckDB 2.0 Arrow export](https://duckdb.org/docs/2.0/guides/python/export_arrow)

The binding exposes `DuckDBPyConnection.interrupt`, but its cancellation outcome and connection reuse
must be established through the actual worker route before relying on it. Cooperative activity
checks still surround engine work. See [result conversion](../../libraries/analytical_infrastructure/duckdb_2.md#35-materialization-result-conversion-and-streaming),
[streaming limits](../../libraries/analytical_infrastructure/duckdb_2.md#115-python-relation-iteration-does-not-imply-bounded-memory-streaming)
and [Arrow thread control](../../libraries/analytical_infrastructure/pyarrow.md#83-execution-parallelism-and-thread-control).
These APIs are exposed by the pinned bindings. Their worker lifecycle behaviour remains the
package's verification responsibility, integrating
[I08](../../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I08).

**Evidence.** Use independent expected answers for ordering, NULL placement, same-position
candidates, ordered aggregates and join multiplicities under each candidate. Verify bound
parameter handling, captured query/dependency correspondence and declared input/output shapes.
For a selected static PostgreSQL route, exercise the candidate and installed privilege checks.
Use a serial baseline and two concurrently admitted jobs on the real worker route with
substantial sealed output or spill, a partially consumed reader and a cancelled submission.
Verify release of the reader, buffers, reservation and spill and establish worker cleanup
after stop. If reuse is
selected, the next job cannot reach the previous temporary relations, registered inputs or spill
after success, failure or interruption. Measure combined working set only if it changes the
carrier, spill policy or safe concurrency choice. Preserve the prior I08 resource and interruption
obligations.

<a id="sbx-durable-analytical-output"></a>
### Bounded canonical processing and durable output

**Baseline · Inspected · 2026-11-23.** Sentence and canonical-sentence producers invoke
canonical processing per partition. Each call projects, orders, opens a result reader and
folds the partition and field groups. The fold joins the canonical strings for a whole batch.
The result can retain an Arrow table, the encoded IPC buffer and a Python bytes copy at the
same time. A compact table remains suitable for small results or genuinely repeated scans.
[Population canonicalization](../../../python/corpus-structure/src/corpus_structure/semantic/population_canonical.py#L188) ·
[Current draft writer](../../../python/corpus-structure/src/corpus_structure/semantic/population_transfer.py#L80)

**Physical cohort comparison · Proposed.** For many small partitions, compare the current
per-partition route with one bounded Arrow relation and DuckDB plan per cohort of compatible
shapes. Carry semantic partition and local ordinal explicitly. Order output and feed independent
partition and field-group folds. Preserve zero-item headers, exact bytes, placements, proof
premises and reuse keys. Keep a large partition as its own cohort where useful. Select physical
batching only when setup removed across the real producer and publication path justifies its
sort, spill and kept-live state. Retain per-partition execution if the cohort adds work or
cannot preserve independent partition semantics.

**Sealed carrier comparison · Proposed.** Carry one ordered relation
`to_arrow_reader(batch_size=...)` into the existing private durable draft and transactional
COPY path. Bound the fold's joined canonical text by bytes, including within DuckDB output
batches whose size is expressed in rows. Keep the supported oversized-row path or refuse the
row explicitly. Write incremental batches to owned IPC with `pa.ipc.new_stream()` and
`RecordBatchStreamWriter.write_batch()`, then seal the manifest after writer close. Reopen and
verify through the existing custody owner as needed and pass admitted batches from the same
verified carrier to the owning transaction's Psycopg COPY path. Use file-backed output only when
it removes overlapping complete results and fits the existing draft ownership, publication and
recovery contract. Keep the current bounded carrier when those conditions are unmet.
[Worker and draft custody](validated-values-and-handoff.md#typed-worker-custody) ·
[IPC reference](../../libraries/analytical_infrastructure/pyarrow.md#71-arrow-ipc-native-columnar-interchange) ·
[Post-cutover review I05](../../plan_improvement_reviews/set-based-execution-after-sbx09_2026-11-23.md#I05) ·
[Deeper review I13](../../plan_improvement_reviews/set-based-execution-after-sbx09-deep-review_2026-11-23.md#I13)

**Acceptance.** Compare exact canonical bytes and independent partition and field-group
commitments with wide and narrow rows, multiple groups, empty partitions, reordered partitions,
repeated placements, and varied physical batch boundaries. Exercise short or partial readers,
incomplete writes and failed seals, oversized refusal, lost acknowledgement and cancellation
through the real draft and COPY consumer. Verify cleanup at each ownership transfer. Qualify
streaming as part of the route that selects it and preserve the current bounded contract
where the comparison retains it.

<a id="sbx-19"></a>
## SBX-19 — Scoped relations as set operations

**Depends.** Use SBX-18's [job allocation](#sbx-analytical-job-allocation), SBX-08's validated
carriers and SBX-05's references for participants and relations. Prepare the trial against
SBX-10's retained indexes and exact formula contexts. The complete installed comparison
consumes [SBX-10's installed producer acceptance](validated-values-and-handoff.md#sbx-consumed-runtime-custody).
Trial preparation and its fixture comparisons can proceed before that separate acceptance.

When adopting [SBX-06 projections](references-and-projection-keys.md#read-projections) for the
trial, declare the source frame, navigation, formal and predicate inputs it actually reads and
their observed ordering and membership. The whole-source premises govern this trial unless
the analytical owner establishes a narrower determining scope. Trial preparation can proceed
on its stated dependencies. Any qualification of projection-keyed reuse consumes SBX-06's
runnable binding contract.

**Vision.** `discover_relations` acquires its admitted projections, prepares the shared
inventories, performs named relational steps, applies the Python seam, and assembles the report.
Qualify the selected implementation through native publication and exact artifact nomination.
The artifact consumer must follow the independently selected report occurrence and its actual
source. SBX-08's acquired inputs and SBX-04's established premises remove repeated entry
re-acquisition, validation and inventory reconstruction for the covered scope.

**API-to-step comparison.** Register one model-derived Arrow inventory through the existing
analytical owner. Use range joins for pieces, extents and overlapping candidates, grouped counts
for captions, partitioned windows with explicit tie order for preceding rows, and batched
formal-symbol and participant joins. Use `ASOF JOIN` only for a true directional nearest match
whose extent and tie semantics are explicit. Verify exact provenance separately. Keep Python's
language decisions and lexical values where the pinned engine differs. Trial the full acquired
route using the current typed-expression machinery, with focused captured SQL or native
comparisons where a step can change the whole-path choice.
[DuckDB comparison surface](../../libraries/analytical_infrastructure/duckdb_2.md#6-advanced-sql-and-relational-expressiveness)

The complete-path comparison starts at authenticated acquired inputs and ends after native
publication, selected readback and exact artifact nomination. Include conversion, relation
preparation, materialization, ordering, resource release and any current proof or authority
checks. PostgreSQL owns selection and effect-time work. Use same-session Psycopg COPY for
session-local keys and uncommitted admission. Consider ADBC `fetch_record_batch()` only when
the imported snapshot sees the committed exact pin and the called projection is granted.
Preserve the existing lexical transfer for unsupported widths and account for any difference
between parameter-bound execution and COPY result delivery. Name the complete pass or repeated
question any alternative removes. Record an inconclusive result with the missing observation
and revisit condition, while retaining the current implementation for that scope.
[Shared placement](common-analytical-basis.md#postgresql-placement-and-transfer) ·
[SBX-12 archive owner](owner-resolved-reads.md#sbx-12)

**Success criteria.**

1. The published report is byte-identical on every fixture and on recorded real sections, apart
   from identities this series deliberately changes, which are listed.
2. Every per-item question in the current kernel is part of one batched step, and no step
   re-scans an input per item.
3. The relational steps are stated as a short named list that a reader can check against the
   kernel's description.
4. Each fidelity trap is handled by the seam or reproduced and tested. Independent cases cover
   Unicode cues, repeated formulas at distinct pointers, independent formal reports at the same
   local position, zero-width and overlapping spans, exact decimals, null and absence,
   duplicate occurrences, phase and tie order, and absent versus incomplete scope.
5. A functional run on a real source view establishes the chosen connection and per-job resource
   lifetimes and scoped access through publication, selected readback and artifact nomination. The
   adoption decision explains the material reduction in repeated work or implementation complexity,
   including conversion, ordering, cleanup and the Python seam.
6. Judge adoption qualitatively from the complete implementation and semantic evidence. Use a
   timed comparison only when it would decide between plausible implementations. Line counts and
   setup ratios are optional observations, with their conditions stated.

**Findings that stop adoption.** Most steps remain per item, the candidate still rebuilds both
inventories, or the complete route adds complexity or repeated work after accounting for
ordering, conversion, preparation, cleanup and the Python seam. A failure to preserve exact
canonical bytes, reference meaning, current authority or publication custody disqualifies the
candidate. A material uncertainty can justify a focused comparison before the decision.

**Decision.** Record adopt, adjust or stop with the criteria above, the complete current and
candidate routes, and the results of any step-specific comparisons. Integrate the chosen
family route with its consumers. Remove its displaced implementation and mechanism-specific
tests while preserving independent
expectations. Record whether a second family should follow, considering predicate evidence, then
constructions' region handling, source preparation and math layout. If the trial stops, retain
the Python span vocabulary of SBX-10 as the kernels' basis. A second-family recommendation
enters the existing scope and decision route before execution.

## SBX-18 and SBX-19 implementation checkpoint

**Implemented · 2026-11-24.** The demand request reservation includes analytical workspace. The
allocation and captured settings follow its parent callbacks, relay steps and CPU dispatch.
Admitted worker resources bound DuckDB threads, buffer memory and private spill. The
connection owns incremental readers and observes cancellation before releasing scratch.

The selected physical cohort path shares projection, ordering and result setup across compatible
sentence partitions while retaining independent commitments and zero-item headers. The draft
writer streams validated IPC to its owned file, seals it after close and fsync, and reopens an
authenticated private copy for transactional COPY. This removes the complete encoded IPC buffer
and Python bytes copy. The per-partition canonical Arrow tables remain available to publication.
Typed expressions remain the production route. The named window comparison covers bound SQL
and explicit ties without a new authoring policy.

**Local evidence · 2026-11-24.** `uv run ci test --workers 1` selected 188 analytical,
population, draft, PDF and scoped identities (`fb7c53f257654b9295c875da1f4f9a66`). The
capture, resource and fixture corrections were verified in the 29-identity serial cohort
`8dd9a9efdc674f69bff14130b9d17550`, including the five earlier failed identities. It also
exercised captured per-job settings in the parent and worker paths and checked that the relay
releases the binding between scheduler steps.

**Provider evidence · 2026-11-24.** `uv run ci test --native-host private --providers-only
--workers 1` passed the native sentence and canonical chain with an acknowledged file-backed
population draft and PostgreSQL COPY/readback. The same receipt
(`13d1c48d7610472782bb4cd87efb22c8`) passed full scoped report byte equality on four retained
Siegrist excerpts with authored HTML coordinates. The independent PDF identity in that receipt
failed at its fixture's lowering contract and retains its own retry in SBX-17.

The installed serial cohort `8dd7a7bfd13241d9bba9a3fa92589a42` passed the two-subprocess
control. One worker held a partially consumed Arrow reader over actual DuckDB spill. A
cancellation flag interrupted its sibling while the first reader remained open and then closed
normally. The test directly submits workers and returns their admissions. The same cohort
passed the fresh Standard child check and the typed and bound-SQL window comparison.

**SBX-19 trial · Tested · 2026-11-24.** The candidate uses one invocation-owned analytical
inventory for range membership, table geometry, caption counts, prior declarations and witness
matching. Formal inventories retain independently produced occurrences. Python retains lexical
decisions and report identity. The ordinary managed cohort `8ea062e8ef40464db87095e64b135d28`
passed 71 analytical and scoped identities on 2026-11-24. The final private native cohort
`8dd7a7bfd13241d9bba9a3fa92589a42` passed all 19 selected identities. The scoped case used
controlled PDF decoding and exercised actual native acquisition, scoped and artifact publication,
exact nomination of a report occurrence and contribution from the selected source member,
selected structural readback, and verified detached reopen of the report dependency.

Earlier cohorts `65cbe14ee2724ed5ae5b162499599421` and `af2e10d3910c4ad89225b350212527fe`
reached scoped publication and contribution selection. The fixture corrections supplied the
required artifact policy and bound the actual source member with its product. The final case
checks both bindings against the published result.

**Decision · Adopt · 2026-11-24.** Keep one typed DuckDB route for scoped relations. The
implemented range joins, grouped matches and explicit ordinal windows batch the questions
they serve. The fixture comparisons and installed artifact path support that choice. Keep
Python's lexical and identity semantics, PostgreSQL selection and transactional
publication and use whole-source premises for the trial. The current acquired transfer already
supplies the required columns, so this path keeps its existing transfer and typed authoring.
Predicate evidence is the next family to consider where a distinct trial of retained token
partitions is scheduled through the existing decision route. SBX-20 retains stage installation.

### Remaining SBX-18 completion obligations

<a id="sbx-18-a1"></a>
**SBX-18-A1 · Open implementation · Inspected · 2026-11-24.** Selected PDF source verification
runs its oracle after closing the checkout with no analytical allocation. The child maps the
captured IPC and uses the unallocated DuckDB connection, which lacks the job spill ceiling.
Give this supported entry point an owned allocation for captured inputs, mapped buffers,
engine workspace and spill through child exit. Its private mapped replay copy is created in
child-owned temporary storage outside the job scratch. Keep that storage in parent-owned
custody so forced child exit can release it. Verify release after success and cancellation.
[Selected source verification](../../../python/corpus-structure/src/corpus_structure/serve/source_verification.py#L27) ·
[Oracle spawn](../../../python/corpus-structure/src/corpus_structure/semantic/pdf_publication.py#L404) ·
[Private replay copy](../../../python/corpus-structure/src/corpus_structure/semantic/pdf_replay_transport.py#L42) ·
[Connection resource policy](../../../python/corpus-structure/src/corpus_structure/analytics.py#L274)

<a id="sbx-18-a2"></a>
**SBX-18-A2 · Open implementation and qualification · Inspected · 2026-11-24.** A stop or
failure after the draft owner installs `.body`, `.arrow` and `.candidate` but before `.ack`
can strand the files. The writer's cleanup removes the temporary path and candidate recovery
requires an acknowledgment. Settle ownership and cleanup across the pre-ack seal, preserving
the original bytes after a durable seal or uncertain native settlement. Carry borrower stop
through the private upload copy and native COPY. These operations currently have no propagated
active check. The native sentence case covers successful file-backed COPY and exact readback.
Close I05 and I13 with the adopted
carrier through the native consumer, including short or partially consumed readers, incomplete
writes or seals, oversized refusal, cancellation and lost acknowledgment followed by recovery.
Keep the existing independent byte and commitment checks.
[Draft seal](../../../python/corpus-structure/src/corpus_structure/semantic/completion_drafts.py#L293) ·
[Candidate lookup](../../../python/corpus-structure/src/corpus_structure/semantic/completion_drafts.py#L384) ·
[Transactional COPY consumer](../../../python/corpus-structure/src/corpus_structure/orchestrate/data_operations.py#L1457)

**I14 · Open qualification · Inspected · 2026-11-24.** The two-worker control calls the pool
directly, sets the cancellation flag and releases the admissions itself. Exercise serial and
concurrent analytical jobs through normal dispatch, cancellation and handle retirement with
actual spill or substantial sealed output and a partial reader. Verify that open readers,
mapped inputs, scratch and reservations remain owned until physical release or handoff.
[Two-worker control](../../../python/corpus-structure/tests/test_analytics.py#L154) ·
[Production submission](../../../python/corpus-structure/src/corpus_structure/semantic/cpu_execution.py#L1104)

<a id="sbx-18-o10"></a>
**O10 · Open qualification · Inspected · 2026-11-24.** The selected cohorts cover typed
ordering, wide integer and canonical partition parity. Separate Arrow capture and transfer
controls cover nanoseconds and decimal values. Account for admitted mixed precision and scale,
wider lexical decimals, UTC nanoseconds and null versus absence on the adopted worker and
carrier boundaries, including exact refusal where values fall outside the declared shape.
[Canonical parity control](../../../python/corpus-structure/tests/semantic/test_data_operation_population.py#L190) ·
[Capture digest control](../../../python/corpus-structure/tests/semantic/test_capture_storage.py#L12)

### Remaining SBX-19 completion obligations

<a id="sbx-19-a1"></a>
**SBX-19-A1 · Open implementation · Inspected · 2026-11-24.** The installed operation still
acquires its source mapping twice. The source cache computes its canonical key before lookup,
and the frame serializes and decodes owned native columns before rebuilding a separate
inventory. Reuse one authenticated acquisition for the frame and model-derived inventory.
Batch the remaining per-item containment, table geometry and schematic matching, and
same-parent formal-symbol questions. The supported method-level ordered witness also
re-scans sibling and cue inputs per use. Retain lexical judgments and canonical identity in
the Python seam. State the final named steps and preserve occurrence, extent, null and ordering
semantics.
[Acquisition](../../../python/corpus-structure/src/corpus_structure/semantic/scoped_products.py#L126) ·
[Frame projection](../../../python/corpus-structure/src/corpus_structure/semantic/declared_record_sources.py#L192) ·
[Structural matches](../../../python/corpus-structure/src/corpus_structure/methods/scoped_relations.py#L672) ·
[Ordered witness](../../../python/corpus-structure/src/corpus_structure/methods/witnessed_source_links.py#L466)

**I06 · Open qualification · Inspected · 2026-11-24.** The four retained excerpts compare full
report bytes with independent answers for the replaced question layer, using the same surrounding
kernel. The installed fixture verifies the acquisition-to-artifact custody with controlled
decoding and a table nomination. Complete the accepted acquired-route comparison on the final
batched kernel. Include real-source inputs and the installed SBX-10 formula contexts with
independent incumbent expectations for report bytes and exact reference provenance. Cover the
remaining named steps and apply the production job lifetime and selected artifact controls to the
completed route.
[Reference comparison](../../../python/corpus-structure/tests/methods/test_scoped_inventory.py#L281) ·
[Installed artifact control](../../../python/corpus-structure/tests/semantic/test_scoped_relational_trial_native.py#L93)
