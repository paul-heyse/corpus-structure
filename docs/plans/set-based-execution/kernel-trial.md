# The kernel trial

**Status:** Proposed. Companion of [Set-based execution](../set-based-execution_2026-11-21.md).
**Created:** 2026-11-21.

This companion owns one kernel family rebuilt as set operations over tables, as a trial that
ends in a recorded decision on whether other families follow. It owns SBX-18 and SBX-19. Source
facts are **Inspected** at `7a415d18d`; the library behaviour cited is reproduced by the retained
checks in `docs/design_review/evidence/2026-11-21_columnar-execution-review/` and by the checks
the trial investigation ran, which are re-run and retained by SBX-18.

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

**Tables, built in process.** From the inputs' carriers: source pieces and items with table cells
unnested; navigation records, roles and extents; formal inputs, symbols and occurrences;
predicate frames, readings and qualifiers; passages. Each carries an ordinal, because every
current index returns rows in original order and relational results have none.

**The relational steps.** Pieces within selected ranges; table geometry and header paths as
range joins; mention to caption by a grouped count; the earlier row with the same parent as a
window; formal symbols per equation as one join in place of a re-scan per declaration;
participants to passages and to source intervals by containment and overlap.

**The seam.** Regular expressions, `casefold`, pydantic row validation, and all identity
computation stay Python functions over rows. Participants are staged before anchors, anchors
before ids, ids before relations, because each id depends on the stage before it. Emission order
across the kernel's phases is reproduced by an explicit sequence column.

**Carriers today, per step.**

| Step | Carrier | Why | Change if |
|---|---|---|---|
| Range and containment joins, header paths, windows | DuckDB relations through the analytical owner, as typed expressions | PyArrow has no inequality join; these are the steps that are quadratic or re-scanned today | Per-call size stays so small that a sorted list with bisection is as clear |
| Equality joins, grouped counts, membership | DuckDB in the same connection, or PyArrow `join` and `group_by` | Either expresses them; one engine per kernel is simpler | — |
| Regular expressions, case folding, edit distance | Python | The engine functions differ silently on non-ASCII input | Never for identity-bearing text |
| Ids and canonical bytes | Python, the existing encoder | DuckDB's JSON differs for floats, decimals and control-character escapes | Never |

<a id="sbx-18"></a>
## SBX-18 — The analytical owner states the fidelity rules

**Owns.** In `cs/analytics.py`: binary collation fixed beside the time zone; a grouped aggregate
that takes typed group keys, which the wrapper lacks today; a window helper; sort helpers that
require NULL placement; an ASOF join that requires a tie-break; an ordered-list aggregate that
requires an order; a scan of Arrow tables with an ordinal; a connection that lives as long as a
worker, beside the per-invocation one. Regular expressions, edit distance and JSON text for
identity are not offered, with the reason stated where a kernel author will look. The evidence
script is extended with the new findings (upper-case hex in control-character escapes; a
connection costs about ten milliseconds to open and a reused one one to three per join, observed
on synthetic data and stated as such).

**Conditions.** DuckDB's and Arrow's thread pools are outside the worker's thread limit and the
pool inventory that receipts record. The owner configures
[DuckDB 2.0.0](../../../python/corpus-structure/pyproject.toml#L9) `threads`, `memory_limit`
and `temp_directory` from the existing worker policy.
[Arrow 26.0.0](../../../python/corpus-structure/pyproject.toml#L23) `set_cpu_count` and
`set_io_thread_count` configure process pools once through that owner, avoiding competing settings
per relation.

**Each job owns resources.** A worker connection is shared, while each computation owns its
temporary relations, registered inputs, readers and spill. Success, failure and stop release
those resources before another job uses the connection. Retire the connection if cleanup cannot
establish a usable state. The existing invocation connection's private spill-directory lifecycle
is the starting integration, preserved for callers that still use it.

DuckDB 2.0.0 `DuckDBPyRelation.to_arrow_reader` provides an Arrow `RecordBatchReader`. Compare
batch consumption with `to_arrow_table` for the actual operator and consume incrementally where
the consumer permits it. This does not establish bounded memory inside a join or sort. The
binding exposes `DuckDBPyConnection.interrupt`, but its cancellation outcome and connection reuse
must be established through the actual worker route before relying on it. Cooperative activity
checks still surround engine work. See [result conversion](../../libraries/analytical_infrastructure/duckdb_2.md#35-materialization-result-conversion-and-streaming),
[streaming limits](../../libraries/analytical_infrastructure/duckdb_2.md#115-python-relation-iteration-does-not-imply-bounded-memory-streaming)
and [Arrow thread control](../../libraries/analytical_infrastructure/pyarrow.md#83-execution-parallelism-and-thread-control).
These APIs are exposed by the pinned bindings. Their worker lifecycle behaviour remains the
package's verification responsibility, integrating
[I08](../../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I08).

**Evidence.** Each helper refuses its unsafe form: a sort without NULL placement, an ASOF join
without a tie-break, an ordered aggregate without an order, a string where an expression is
required. In the actual worker, two jobs share one connection while the second cannot reach the
first job's temporary relations, registered inputs or spill. Failure and interruption checks
establish the current result's outcome and cleanup, including whether the connection is reusable
or must be retired.

<a id="sbx-19"></a>
## SBX-19 — Scoped relations as set operations

**Depends.** SBX-18; validated carriers (SBX-08) so inputs are acquired once; the reference
carrier (SBX-05), since participants and relations are references.

**Vision.** `discover_relations` becomes: build tables from carriers; a sequence of named
relational steps; the Python seam for text rules, anchors and ids; assembly of the report. The
repeated re-acquisition and re-validation at the kernel's entry is already gone by SBX-08.

**Success criteria.**
1. The published report is byte-identical on every fixture and on recorded real sections, apart
   from identities this series deliberately changes, which are listed.
2. Every per-item question in the current kernel is part of one batched step, and no step
   re-scans an input per item.
3. The relational steps are stated as a short named list that a reader can check against the
   kernel's description.
4. Each fidelity trap is handled by the seam or reproduced and tested.
5. A functional run on a real source view establishes worker-connection and per-job resource
   lifetimes and scoped access. The adoption decision explains the material reduction in repeated
   work or implementation complexity, including conversion, ordering, cleanup and the Python seam.
6. Judge adoption qualitatively from the complete implementation and semantic evidence. Use a
   timed comparison only when it would decide between plausible implementations. Line counts and
   setup ratios are optional observations, with their conditions stated.

**Findings that stop the trial.** Most steps remain per-item or procedural after the rewrite. A
step needs SQL text where typed expressions are required. Ids can be reproduced only by calling
Python per row from inside the engine. The complete route adds complexity or repeated work once
emission ordering, conversion, cleanup and the Python seam are included. A material uncertainty
between plausible routes can justify a focused comparison before the decision.

**Decision.** The package ends with a recorded decision, with the criteria above as its
evidence: continue to a second family (predicate evidence, then constructions' region handling,
source preparation, math layout), or stop and keep the Python span vocabulary of SBX-10 as the
kernels' basis. Either is an acceptable outcome of the series.
