# Serving and evidence journeys

**Proposed implementation target · 2026-11-03.** This companion defines the AC10 and
AC11 contracts of the [audit-closure coordinator](../audit-closure_2026-11-03.md).
The coordinator alone owns new-series package state, review-obligation conclusions, sequencing
and completion. Existing plans retain their scheduled DA dispositions; this companion does not
transfer or copy them. It contains no separate progress ledger and authorizes no production changes.

The input is the [principal review](../../design_review/reviews/design_review_audit-closure-target_2026-11-03.md)
at `fd4ea601`, especially DA-035/036/039 and its
[consumer contracts](../../design_review/reviews/audit-closure-target/consumer-contracts.md),
read with the [semantic](../../design_review/reviews/audit-closure-target/semantic-contracts.md)
and [runtime](../../design_review/reviews/audit-closure-target/runtime-boundaries.md) contributions.
Source grounding is that revision plus the identified concurrent dirty M1 tree inspected on
2026-11-03; those edits are preserved, not qualification evidence. Core 3.3, its efficient
architecture companion, code-intelligence 1.4 and the test-assessment companion guide the target.
All future checks below are planned, not run for plan authoring.

## Purpose and existing foundations

An answer must let a caller distinguish what was selected, what was assessed, what established
a fact, what source work covered the question, and whether an inventory has more pages. Those
are separate meanings. The same release/result/query binding must govern the entire answer,
evidence, source retrieval and export journey.

The architectural owners are [D8](../../design/D8-agent-and-query-interfaces.md),
[D1](../../design/D1-knowledge-representation.md),
[D3](../../design/D3-database.md) and
[D5](../../design/D5-consolidation-identity-confidence.md). AC00 schedules the ADR/owner route for
accepted RC08 and RC09 before dependent implementation. Their explicit operator acceptance on
2026-11-03 is planning authority; this companion neither edits those authorities nor claims the
new result contracts already exist.

Source paths in this document are relative to `python/corpus-structure/src/corpus_structure/`
unless qualified. Current `semantic/query.py` provides `SnapshotBinding`, strict `QueryRow`,
`ReadSession.coverage(family, scope)`, scoped Core predicates, exact value nodes and read snapshots.
`serve/read.py:claims` already uses keyset batches to avoid keeping a cursor open during hydration.
`serve/journey.py:serve_query` resolves a completed run, enforces producing/installed query
compatibility and uses query-owned positions. These are foundations to extend.

The missing composition is visible in `serve/journey.py:235–261`: all coverage is hydrated before
family/universe selection. `semantic/query.py:explain` and `serve/explain.py:explain` collect full
supports, derivations, assessments, task results and observation payloads. `serve/read.py:evidence`
builds an explanation before extracting evidence. `QueryRow` currently lacks fact standing.
Top-level `domains/statistics/queries.py:Relations.rows` uses `UNION ALL`, depth four and an outer
lexical path-string sort; client partitions do not bound its recursive expansion or sort.

M1's dirty `semantic/record_queries.py` already has `RecordReadSelection`, finite row/record/byte
budgets, source/report distinctions and whole-result refusal. Preserve that separate candidate
record contract. A candidate-admission label must never be translated to accepted claim standing.

## Shared answer contract

The following shapes specify required meaning, not mandatory new classes for each noun. Extend
released definitions and the existing strict Pydantic products and batched hydrators. AC01–05
supply their authoritative semantics; AC10 owns their presentation and migration.

```text
AnswerBinding = SnapshotBinding + run/completed-cut identity
              + producing query contract/implementation + installed compatibility
              + projection/universe + canonical parameters

FactStanding = {
  selection: {disposition: selected | not_selected | undetermined,
              policy/release, selection references},
  assessment: {availability: available | unassessed | unavailable,
               assessment references and each released outcome/context},
  establishment: {availability: available | unavailable,
                  establishment references and released kind/context}
}

CoverageRequest = {binding, released requirement/universe, Scope, detail cursor?, page limits}
CoverageSummary = {binding, requirement?, state: established | not_established,
                   diagnostic?, source completeness, detail-page reference}
Page[T] = {binding, selection, items: T[], population_complete,
           next_page_token?, operational outcome}
```

The wire version will use release-owned outcome vocabularies; the illustrative availability tags
above must not become a second writable status model. `not_selected` means selection nonmembership,
never scientific rejection. A positive assessment does not imply selection. Several assessments
remain individually attributable; no last-row, maximum, or arbitrary aggregate becomes a fabricated
verdict. If the released contract does not establish a conclusion, expose that limitation. Facts
and occurrences retain their own references, including premises whose standing differs from the
selected conclusion. Establishment distinguishes source assertions, inference and other released
origins; missing historical information remains unavailable.

Standing travels with every returned fact in primitive and named answers, entity properties,
statement/proof/path premises, explanations and logical exports. The projection label describes
the requested universe only. Exact lexical values, typed value-role graphs, qualifiers, source
attribution and parallel occurrences survive the additional metadata unchanged.

The standing envelope itself stays bounded: inline references are a bounded selection with an
explicit continuation to AC11's assessment/establishment detail, not every assessment attached to
every returned fact. Any released contextual summary must state its interpretation and detail
completeness; it cannot hide contradictory evidence outside the first page. A summary may require
set-shaped inspection of the complete scoped assessment relation, but not full value/source
hydration. Establishment detail receives the same bounded reference treatment.

Coverage selection occurs at the relational owner before fetching detail. A scoped property
request uses its archived producer/universe requirement and the complete required source/task
population, including missing producer reports. A query without a property family returns a
bounded summary with `not_established` and a diagnostic; it does not attach every coverage row.
Explicit detail is paged over the same binding. Detail paging, source completeness and operational
exhaustion are separately reported: an empty first page establishes absence only when the actual
required coverage and completed question do so. A last returned detail row never establishes that
population's completeness. Summary calculations use owned set-shaped predicates/aggregates rather
than materializing every detail just to count or classify it.

## AC10 — select coverage and expose fact standing

AC10 consumes the AC01–05 released semantic contracts and AC06's owned read/lifetime boundary.
A signed-off shape alone is insufficient: the reader must be able to resolve the actual selected,
assessment and establishment relations for the pinned result. AC10 can design schemas against
those early interfaces, but native journeys depend on their implemented operation.

Add one public coverage selection/summary operation and one batched standing hydration path at
`semantic/query.py`. Push family, requirement/universe, run/document/unit scope and keyset position
into Core selection; use the archived coverage recipe, not independently reconstructed units.
Return detached owned values under `read_snapshot` and release the checkout before presentation.
Selection must precede value/source hydration; do not add a coverage cache with another lifecycle.

The package includes migrations of `QueryRow`, `semantic.query.QueryResult`,
`serve.results.ClaimAnswer` and `EntityAnswer`, `serve.protocol.QueryResult`,
`serve.journey`, generic `serve/queries.py` and actual statistics query products. It also includes
`serve/explain.py`, `serve/record_results.py` where shared coverage/result envelopes meet M1,
and CLI `query.py`, `explain.py`, `records.py` JSON/Rich presentations. Primitive direct callers
must move with those products, not wait for AC13 to discover them.

Update `serve/export.py`, `companion_export.py`, `record_export.py` and their actual CLI/native
consumers wherever the changed logical answer/descriptor participates. Keep physical captured
relations authoritative: an export may derive the new answer fields from the pinned selection,
assessment and establishment relations or declare a separately versioned derived relation; do
not write an independent standing store. Export descriptors and generated schemas change in the
same package as their fields. Preserve existing exact lexical/decimal/rounding declarations,
relation digests, provenance, atomic directory publication and cancellation behavior.

Actual MCP consumers in `intervene/semantic_server.py` include `find`, `inspect_source` and source
resources/refusals, rather than a currently observed named-query/claim-explanation transport.
Migrate any affected shared binding, response schema and source reference there in this package;
do not claim or add an unrelated named-query tool merely to complete a checklist. AC13 checks the
assembled actual transport union; it does not take over unfinished AC10 consumer migration.

Archive a new ordinary answer/coverage contract under existing query compatibility, version
generated output descriptors and migrate independent fixtures. Reject incompatible old tokens
through existing compatibility handling. Keep old immutable rows and releases honest; adding
derived presentation fields does not itself require rewriting history or supporting arbitrary
old runtimes. AC00 routes changed D8/RC08 authority before activation; AC13 integrates the resulting
release/reader/export descriptors, preserving current-only execution and frozen predecessors.

## AC11 — bounded evidence, explicit payloads and relation walks

AC11 consumes AC10's answer/binding shapes and AC06's owned readers. Its walk implementation also
depends on I02 below and the released edge/universe/standing definitions from AC01–05. Evidence
inventory work may proceed while the walk budget decision is being settled; the complete AC11
package includes both paths and their actual consumers.

### Evidence and source retrieval

Provide public selection operations for supports, evidence, assessments, derivations and source
report references. Each request names its root fact or unit, collection, binding, deterministic
identity cursor and limits. Filter scope/identity/cursor/limit before source/value hydration.
`serve/read.py:evidence` queries the evidence relation directly. A summary returns a bounded first
selection or links plus per-collection completeness and continuation; it does not hide a full
explanation underneath a small presentation limit. Unit task/results and observations follow the
same inventory-versus-payload separation, including missing reports and explicit empty reports.

Source report content is an explicit immutable-identity read under the original binding and an
encoded payload budget. Report references carry their custody/provenance without embedding the
report body repeatedly in every support. A single oversized object refuses as oversized, or uses
an existing explicitly selected source-range contract whose boundaries/coverage are visible. It
is never silently truncated into apparently exact evidence. Missing, wrong-binding and unsupported
range requests remain distinguishable; no fallback to the newly promoted run is allowed.

Use canonical encoded UTF-8 bytes consistently for admission/accounting, bounded row hydration
and a final complete-envelope size check. Compute each row's encoding once rather than serializing
the entire growing response for each candidate. Version any replacement of the current
`max_chars` meaning; do not silently reinterpret existing tokens/options. AC11 migrates both
primitive and named evidence queries, `serve/explain`, CLI explanation/source reads, exports'
explicit payload decisions, MCP source/resource response schemas and their actual consumers.
Detached exports may intentionally request full inventories through bounded batches; interactive
limits do not silently truncate their declared full-relation contract.

### I02 — settle admission and page mechanics before walk implementation

This is a bounded decision dependency, not an invitation to choose arbitrary limits during AC11.
Inspect current `max_rows`/`max_chars`, `QueryContext.row_batch` (64), native source/range controls,
record read limits and the intended depth-four workload, including high degree and many nonmatching
walks. Choose supported defaults and upper admission limits for examined adjacency rows/edges,
frontier states, retained witness/state bytes, serialized result/payload bytes and page/cursor
bytes. Specify what each counter includes, when it is checked and the maximum next database batch.
Timeout may supplement those bounds; it is not the sole work bound. Existing output and record
limits are grounding inputs, not automatic traversal budgets or measured capacity claims.

The decision must specify a versioned `(depth, frontier/walk fact-ID sequence)` order, adjacency
keyset, complete cursor schema, cursor-size refusal, supported depth/defaults and structured
`work_limit`, `oversized_item`, `invalid_continuation` distinctions. The selected page strategy is
bounded deterministic replay to reconstruct the search frontier under the same immutable binding;
all replay work counts against the request's budgets. The new version's cursor identifies an exact
successful page position and all answer-affecting parameters; it does not serialize an unfinished
frontier or grant permission to skip reconstruction. I02 settles safe page boundaries, any bounded
lookahead and repeated-work consequences against the actual workload before fixing defaults. A last
emitted path alone is insufficient to resume an unfinished frontier. No partial-frontier resumption
machinery or server-side durable traversal scheduler/state store is selected.

This deliberately buys small, binding-checkable tokens and no retained server traversal lifecycle
at the cost of repeating bounded prefix search on later pages. A replay that no longer fits the
admitted work/state budget refuses; it never skips necessary search. I02 must demonstrate a credible
supported page workload from source reasoning or its bounded investigation, rather than declaring
arbitrary defaults adequate because refusal is available. A materially unsuitable repeated-work
route reopens this decision with the coordinator before implementation, not through an implicit
partial-frontier cache.

Record the exact values, units and strategy in this section via the coordinator's decision route
before AC11 dependent implementation begins. Source reasoning can settle them; if a consequential
uncertainty remains, schedule one bounded evidence investigation under AC00/I02 with a question,
selected workload, bounded resources and decision outcome. Keep dependent implementation blocked
until that outcome is integrated. Plan authoring runs no probe and makes no capacity claim.

**I02 settled for implementation, 2026-11-03 (coordinator decision):** the supported
walk version is `bounded-walks-2`, breadth first by `(depth, origin entity ID,
ordered fact-ID witness sequence)`, with C-collated fact-ID adjacency keysets. Default
and maximum depth are four. The following request bounds include deterministic replay
and the one matching-witness lookahead needed to establish a successful next page.

| Resource | Default | Maximum | Unit and admission point |
|---|---:|---:|---|
| Examined adjacency | 100,000 | 1,000,000 | Fetched edge rows per expanded frontier state; repeated edges and replay count again; check before admitting each row |
| Live frontier | 20,000 | 100,000 | Pending frontier states, including the currently expanded state; check before retaining a new state |
| Retained state | 8 MiB | 32 MiB | Sum of canonical UTF-8 encodings of live `(origin, target, fact-ID sequence)` states; check before enqueue |
| Result envelope | 1 MiB | 8 MiB | Canonical UTF-8 bytes including binding, standing, rows and continuation; complete-envelope check before success |
| Encoded cursor | 8 KiB | 8 KiB | Complete encoded continuation bytes; refuse before decoding or returning an oversized token |
| Next adjacency batch | 64 | 64 | At most `min(row_batch, remaining examined-edge budget + 1)` rows; the extra detection row is examined and causes refusal |

A page defaults to 100 output rows, with an upper admission limit of 1,000. The cursor
position is exactly `{walk_version: 2, depth, origin, path: [fact IDs]}` inside the
existing release/run/realization/revision/query/implementation/projection/canonical-parameter
binding. Depth equals witness length. A continuation must name a matching witness actually
encountered during reconstruction; an invented position refuses `invalid_continuation`.
All answer-affecting admitted bounds are parameters and therefore bound by the token.
A successful page ends after its admitted output rows plus one matching witness establishing
`has_more`, or after complete search exhaustion. It never claims exhaustion from the last
output row. Later pages reconstruct from roots, counting the whole replay; work/state
exhaustion returns `work_limit` with no partial page or continuation. A complete individual
row/envelope/cursor that cannot fit returns `oversized_item`. Malformed, old-order and
wrong-request cursors refuse through continuation compatibility.

Source reasoning establishes a bounded useful workload rather than a measured capacity claim:
one origin with branching at most ten through depth four examines at most 11,110 edges,
with at most 10,000 depth-four witnesses. This fits default edge/frontier admission; actual
encoded identifiers must also fit the retained-byte budget. A high-degree first vertex is
fetched in batches of at most 64, so degree cannot bypass admission. Sparse matching output
may require the complete expansion; later-page replay can exceed the same budget and must
refuse. Larger branching/many roots/long identifiers are explicitly conditional on all bounds,
not promised by the example. No latency or universal capacity benefit has been measured.
The coordinator accepted these values before dependent traversal implementation; no probe
was needed to resolve a remaining factual uncertainty.

The ordinary-answer v2 hydrator also admits an individual typed graph before transferring
value bodies: discovery fetches at most 64 node/role metadata rows per batch, at most
100,000 distinct value nodes and 100,000 examined role edges, and at most 8 MiB of physical
scalar UTF-8 data across those nodes and roles. Mapping-role cursor keys are limited to
8 KiB. These are operational read limits (`work_limit`), distinct from canonical result
bytes and independent of claim acceptance. No incomplete graph is returned as exact.
Only after complete bounded discovery are value bodies fetched in batches of at most64;
entity memberships/source-reference metadata receive the same8 MiB physical preflight.

### Walk meaning and selected physical route

The new `relations_between` contract explicitly asks for **walks**, not reachability or shortest
paths. Preserve the selected `special_case_of`, `transformation_of`, `limit_of` relation kinds,
directed source-to-target edges, actual query universe and fact-ID edge identity. Parallel edges
produce different witnesses. Cycles, repeated vertices and repeated edges remain legal through
the declared depth bound, default four; do not introduce visited-node deduplication or PostgreSQL
`CYCLE` suppression. Returned witnesses retain ordered fact IDs and their individual standing.
Target filtering selects results after expansion; it must not remove intermediate nodes or shrink
semantically required global scope. Any supported depth override is explicit and admitted by I02.

Select a versioned breadth-first frontier traversal over indexed scoped adjacency, with compact
fact-ID witnesses and deterministic depth/frontier/fact-ID order. Replace the old lexical
concatenated-path order and cursor version deliberately; do not describe it as equivalent.
Bound each adjacency fetch with keyset predicates before hydration, including a single high-degree
node. Admit next expansions against examined-edge/frontier and retained-state/payload bounds;
do not build an unbounded next frontier or sort the full recursive result then apply an outer
`LIMIT`. Query plans/indexes must support the selected release/realization/subject/edge route.
If an index is needed, schedule it with this package through a forward migration, preserving
frozen bodies/native descriptors. Scope identity does not require a new table per semantic kind.

Exhaustion policy is **EXACT-OR-REFUSE**. Ordinary successful paging returns an exact ordered page
and truthful remaining-population information under its cursor strategy. If admitted search or
state bounds are exhausted before that exact page/continuation can be established, refuse the
operation explicitly; return neither partial rows represented as a successful page nor an absence
claim. No continuation from the last output cursor is issued after an unfinished frontier. A
caller may start a fresh explicitly admitted request with a larger supported budget. Earlier
successful pages retain their original scope; they do not establish that a later refused search
completed. This contract removes ambiguity without requiring durable jobs.

AC11 includes `domains/statistics/queries.py`, query protocol/compatibility and cursor codecs,
`serve/read`/result products, real CLI output and token follow-up, affected source MCP/resource
consumers and independent fixtures. AC00 routes RC09/D8 authority and RC08 payload/result changes;
AC13 assembles release/native/query artifacts after those migrations, rather than postponing them.

## Library realization and alternatives

Carry forward the review's **Interface-checked** mechanisms, with the composed target still
**Proposed**. No dependency change or new documentation research is selected by these contracts.
SQLAlchemy **2.1.6** Core `select`/`where`/`exists`, joins/aggregates and keyset predicates select
before batched hydration. `read_snapshot` retains `REPEATABLE READ` plus
`postgresql_readonly=True` before begin; detached values do not extend database lifetime through
transport. For a genuinely detached inventory, `yield_per`/`Result.partitions` can bound client
buffering; context-managed result closure must survive early stop. Keep existing keyset batches
where subsequent hydration queries use that connection. Streaming does not bound server recursion,
sorting or total source payload.

Precise retained sources are [SQLAlchemy 2.1.6 connections](https://github.com/sqlalchemy/sqlalchemy/blob/rel_2_1_6/doc/build/core/connections.rst),
[PostgreSQL 18 recursion](https://www.postgresql.org/docs/18/queries-with.html),
[SQLAlchemy guide §§8/11.4](../../libraries/postgresql/sqlalchemy.md), and the review's installed
PostgreSQL dialect/psycopg inspection (`base.py:245–272`, `psycopg.py:570`). Pydantic **2.14.1**
strict/discriminated products consume released definitions rather than recreating their semantics;
see [strict mode](https://github.com/pydantic/pydantic/blob/v2.14.1/docs/concepts/strict_mode.md).
FastMCP **4.1.3** remains the actual MCP transport, not another semantic owner. These are retained
pins/evidence, not fresh runtime verification.

Shortest-witness/reachability, a bounded detached NetworkX projection, PostgreSQL `CYCLE`, and
DuckDB **2.0.0** recursive state are deferred alternatives with concrete triggers: a real consumer
asks a different graph question, or I02/implementation evidence shows the chosen indexed frontier
route cannot serve an admitted workload. They require their own semantic contract/comparison;
none is unconditional implementation. Whole-realization Python graphs, another coverage cache,
long-lived cursors for every query and durable traversal jobs add movement/lifecycle costs without
solving the current question. Quantitative capacity/latency benefits remain unmeasured.

## Completion evidence and later evolution

AC10 and AC11 own focused functional/native checks for their implemented behavior; AC14 owns
final-source assembled qualification and evidence union. AC13 owns coherent release activation.
Use independent, manually specified expected standing, population and walk witnesses rather than
the production projector/traversal to calculate both expected and actual results.

Required future cases distinguish selected from assessed/rejected/ambiguous/unassessed facts,
mixed-standing premises, unestablished coverage from complete absence, missing reports, partial
source work and ordinary detail paging. Exercise generic, primitive and named results, entity
properties, claim/unit explanations, M1 candidate separation, exact lexical values and both
JSONL/Parquet descriptor routes against populated native data. Native constraints and protected
reads remain real obligations; a pure adapter fake does not establish them.

Evidence cases include independently known support/evidence/derivation identities over several
pages, source payload fetched only explicitly, oversized single reports, early cursor closure,
wrong-root/changed-selection/changed-release tokens and promotion between requests. Walk cases
include cycles/self-loops, parallel edges, reconvergence, a necessary intermediate outside the
target set, depth-four boundary, sparse matching outputs, a high-degree first vertex and work
exhaustion before any output. Verify new order/old-token refusal and no fabricated continuation
after an unfinished frontier. Check real CLI transport and actual MCP source/reference journeys
at their integrated endpoint; retain refusals and failures alongside successes.

A new property family should extend its released requirement and reuse the same selected coverage
operation; a new assessment context should extend released standing without every adapter inventing
an aggregation. A separately requested shortest-witness query can reuse pinned adjacency and
hydration but must not change this walk meaning. Those scenarios explain the seams; they do not
add new packages. AC14 reports implementation, tested scope and any deferred benefit measurement
separately. No test command or probe was run for this documentation-only contribution.
