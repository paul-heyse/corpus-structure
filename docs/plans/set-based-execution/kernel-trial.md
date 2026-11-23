# The kernel trial

**Status:** Proposed. Companion of [Set-based execution](../set-based-execution_2026-11-21.md).
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
The pilot carrier is the implemented baseline for comparison with the proposed typed path. This package evaluates the named
scoped-relations workload, using the shared [transfer](common-analytical-basis.md#postgresql-placement-and-transfer)
and [numeric fidelity](common-analytical-basis.md#numeric-fidelity) contracts.

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

**Canonical production and authoring.** The reconciled target proposes model-derived canonical
item text and ordered digest aggregation while keeping the existing identity definition and
independent Python reference. The recorded identity-rule change must be resolved before use.
Keep typed authoring under ADR-0135. Captured raw SQL remains a candidate requiring its existing
decision route, rather than a prerequisite of the columnar pivot. Independent fidelity cases
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

**Prepared relations.** Derive shapes from the [model projection contract](common-analytical-basis.md#projection-contract)
and acquire each input once. Compare in-process Arrow and DuckDB work with PostgreSQL-native
preparation and set checks over the same admitted scope, accounting for transfer, JSON unpacking,
typed storage and any return to Python. Prepare source pieces and items with table cells
unnested, navigation records with roles and extents, formal inputs with symbols and occurrences,
predicate frames with readings and qualifiers, and passages from the acquired carriers. Each carries an ordinal, because every
current index returns rows in original order and relational results have none. Prepare one
formal inventory keyed by selected product, projection, pointer, source start, representation
and formal input. Retain explicit input occurrence wherever required to disambiguate a reference.
The inventory serves all formula questions in the invocation.

**The relational steps.** Pieces within selected ranges; table geometry and header paths as
range joins; mention to caption by a grouped count; the earlier row with the same parent as a
window; formal symbols per equation as one join in place of a re-scan per declaration;
participants to passages and to source intervals by containment and overlap.

**The seam.** Regular expressions, `casefold`, edit distance and canonical scalar production
use the existing Python semantics wherever the pinned engine differs. Reconsider an individual
field only after independent positive and negative parity cases. Acquire typed rows and their
established invariants under SBX-08/04 before reuse. External input and conversions that can
change meaning receive their own validation at acquisition. Participants are staged before
anchors, anchors before ids, and ids before relations, because each id depends on the stage before it. Emission order
across the kernel's phases is reproduced by an explicit sequence column.

**Compared implementations.** Use the same named relational steps and independent expected
answers for the existing typed-expression route, captured DuckDB SQL, and PostgreSQL-native set
work. Direct Arrow compute remains useful for simple column transforms. Choose one coherent
implementation for the selected family after accounting for its conversion, preparation and
cleanup. Capture explicit ordering, NULL placement, join multiplicity and same-position tie
semantics, including any ASOF match and ordered aggregate. Reuse the shared canonical-text
contract within its approved scope. Scoped-relations identity keeps its existing Python
publication contract unless the family decision explicitly extends that scope.

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
the rule needs per-group counts. Compare the same steps with named captured
`con.sql(query, params=[...])` definitions using `SEMI JOIN`, `ANTI JOIN`, `EXCEPT ALL`,
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

Compare captured named DuckDB SQL with typed expressions. Each maintained query has one owner,
exact captured definition, versioned dependencies, model-checked input/output shape and bound
values. Validate its declared relations before executing and preserve release correspondence
and production observability. PostgreSQL comparisons may use reviewed static SQL where installed
catalog, descriptor, privilege and candidate checks can establish the same guarantees as the
generated route. Keep caller values separate from query definitions. The actual selected SQL
policy follows the [decision routes](common-analytical-basis.md#decision-routes).

Retain the earlier synthetic timing observations with their original evidence and scope.
Compare production work qualitatively and time it only when setup, transfer, memory or spill
uncertainty can decide between conforming routes.

**Conditions.** DuckDB's and Arrow's thread pools are outside the worker's thread limit and the
pool inventory that receipts record. The owner configures
[DuckDB 2.0.0](../../../python/corpus-structure/pyproject.toml#L9) `threads`, `memory_limit`
and `temp_directory` from the existing worker policy.
[Arrow 26.0.0](../../../python/corpus-structure/pyproject.toml#L23) `set_cpu_count` and
`set_io_thread_count` configure process pools once through that owner, avoiding competing settings
per relation.

**Each job owns resources.** Invocation-owned connections and private spill directories are
the baseline. Consider worker-wide reuse only when it removes material setup work. Each
computation owns its temporary relations, registered inputs, readers and spill. Success,
failure and stop must finish or close the relation reader, or end the DB-API result as appropriate,
and release those resources before another job uses a retained connection. Retire the connection if cleanup cannot establish a
usable state. Establish job isolation through the real worker route before selecting reuse.

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

The
binding exposes `DuckDBPyConnection.interrupt`, but its cancellation outcome and connection reuse
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
In the actual worker, establish the chosen connection lifetime, cancellation outcome and spill
cleanup. If reuse is selected, a second job must be unable to reach the first job's temporary
relations, registered inputs or spill after success, failure and interruption. Exercise a
partially consumed reader before the next job and verify either safe reuse or connection
retirement. Preserve the prior I08 resource and interruption obligations.

<a id="sbx-19"></a>
## SBX-19 — Scoped relations as set operations

**Depends.** SBX-18; validated carriers (SBX-08) so inputs are acquired once; the reference
carrier (SBX-05), since participants and relations are references.

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

**API-to-step comparison.** Acquire the shared inventories as model-derived Arrow tables, with
explicit ordinal and occurrence columns. Use range joins for pieces and extents, grouped counts
for caption candidates, windows for earlier rows under the same parent, and one formal-symbol
join per prepared inventory. Direct `pyarrow.compute` kernels suit simple existing column
transforms. Consider `ASOF` or `NEAREST` only where the named question has the same direction,
range and tie semantics, then verify exact provenance separately. Compare PostgreSQL-native
preparation using the admitted snapshot and transfer route in the shared owner. Account for
server tagged-packet extraction, movement back to Python, ordering and cleanup when choosing.
No timing requirement follows unless memory, spill, transfer or setup uncertainty could change
the choice. [Shared placement](common-analytical-basis.md#postgresql-placement-and-transfer)

The complete-path comparison starts at authenticated acquired inputs and ends after native
publication, selected readback and exact artifact nomination. Include conversion, relation
preparation, materialization, ordering, resource release and any current proof or authority
checks. A connector candidate consumes an already visible exact pin through its granted
projection and retains the owning snapshot through scan completion. Name the complete pass or
repeated question it removes. Reuse the existing analytical and transfer owners before adding
a new abstraction. Record an inconclusive result with the missing observation and revisit
condition, while retaining the current implementation for that scope. Archive-specific
Parquet adoption and cold reopen remain in [SBX-12](owner-resolved-reads.md#sbx-12).

**Success criteria.**

1. The published report is byte-identical on every fixture and on recorded real sections, apart
   from identities this series deliberately changes, which are listed.
2. Every per-item question in the current kernel is part of one batched step, and no step
   re-scans an input per item.
3. The relational steps are stated as a short named list that a reader can check against the
   kernel's description.
4. Each fidelity trap is handled by the seam or reproduced and tested. Independent cases cover
   Unicode cues, repeated formulas at distinct pointers, decimals, null and absence, phase order,
   tie order and scope-specific missing members.
5. A functional run on a real source view establishes the chosen connection and per-job resource
   lifetimes and scoped access through publication, selected readback and artifact nomination. The
   adoption decision explains the material reduction in repeated work or implementation complexity,
   including conversion, ordering, cleanup and the Python seam.
6. Judge adoption qualitatively from the complete implementation and semantic evidence. Use a
   timed comparison only when it would decide between plausible implementations. Line counts and
   setup ratios are optional observations, with their conditions stated.

**Findings that stop adoption.** Most steps remain per-item after the rewrite, or the complete
route adds complexity or repeated work after accounting for emission ordering, conversion,
preparation, cleanup and the Python seam. A failure to preserve exact canonical bytes, reference
meaning, current selected authority or publication custody disqualifies the candidate. Needing
captured SQL feeds the authoring comparison and its decision route. A material uncertainty
between plausible implementations can justify a focused comparison before the decision.

**Decision.** Record adopt, adjust or stop with the criteria above and the typed-expression,
captured SQL and native comparison. Integrate the chosen family route with its consumers and
remove its displaced implementation and mechanism-specific tests while preserving independent
expectations. Record whether a second family should follow, considering predicate evidence, then
constructions' region handling, source preparation and math layout. If the trial stops, retain
the Python span vocabulary of SBX-10 as the kernels' basis. A second-family recommendation
enters the existing scope and decision route before execution.
