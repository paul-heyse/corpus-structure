# Consumer and evaluation target contracts

**Proposed, 2026-11-03.** Supporting analysis for the
[principal review](../design_review_audit-closure-target_2026-11-03.md).
Source inspection at 90ed25c4 plus the principal's identified dirty M1 tree; no runtime validation.
Paths below omit `python/corpus-structure/src/corpus_structure/` unless specified.

## Select coverage before hydration — DA-035

Current `serve/journey.py:235–261` obtains all coverage before selecting its family/universe;
`semantic/query.py:1150` has family/scope predicates but returns hydrated tuples. The target is
one public coverage operation accepting the released producer/universe requirement and query
scope, lowering that selection to Core predicates before fetching. Absence still requires the
complete required source population; a returned row subset never defines coverage completeness.

For a query without a property family, return a bounded coverage summary with an explicit
not-established diagnostic rather than attaching every coverage detail. Full coverage becomes an
explicit paged query over the same binding. The answer distinguishes evidence coverage, population
paging and operational exhaustion. Generic, named, explanation and record adapters consume that
contract; none reconstructs required units or source-outcome interpretation independently.

Keep keyset continuation and current query source/runtime compatibility. Extend the archived query
contract when summary/detail shape changes, reject incompatible tokens, and retain explicit detail
access. This changes the default envelope: it needs a versioned consumer migration, not an invisible
optimization. Do not truncate a coverage tuple and infer completeness from its last returned row.

**Alternatives:** fetching then filtering retains unnecessary work; duplicating a coverage cache
adds invalidation machinery. Selection at the existing relational owner plus separately requested
detail is the simpler complete correction. Use existing SQLAlchemy Core select/where/exists and
batched result hydration. No new engine or dependency is selected.

## Return standing with every fact — DA-036

Extend the release-owned fact-answer product consumed by QueryRow/ClaimAnswer, rather than add a
CLI-only marker. Carry selection disposition and referenced assessment/establishment evidence for
each fact/occurrence, with unknown/unassessed distinct from rejected. The authoritative assessment
and selection relations determine these fields under one declared interpretation. One batched
hydrator serves primitive and named queries, entity properties, path premises, explanation and
exports. Candidate-only M1 admission remains its distinct contract; do not relabel candidate
records as accepted claims.

A projection label describes the requested universe, not the standing of every member. An
accepted claim may have premises of another standing; preserve their own markers and evidence.
Do not fabricate a single status by arbitrary last-row ordering when assessments disagree.
Use release definitions/Pydantic discriminated products for the supported standing meanings;
there is no second independently writable status store.

**Migration:** version result contracts, generated schemas and export descriptors together;
update all actual CLI/MCP/presentation adapters and independent fixtures. Preserve exact lexical
values, source attribution, parallel occurrences and query bindings. The metadata is derived at
read time from pinned relations, so historical immutable rows need not be rewritten merely to
add presentation fields.

## Separate evidence inventory from source payload — DA-039

Replace implicit full explain hydration (`semantic/query.py:1576–1801`, `serve/explain.py:60–142`)
with public bounded selections for supports, evidence, assessments, derivations and source-report
references. Each has a deterministic identity cursor under the same result/query binding.
The summary reports whether each collection is complete and links to its next page. Source report
content is retrieved explicitly by immutable identity with a payload budget, rather than repeated
inside every fact explanation or evidence page. A single oversized object refuses explicitly or
uses the existing source-range contract; it is never silently cut into apparently exact evidence.

`serve/read.py:236` should query the evidence relation directly, not build an explanation then
filter it. Apply identity/scope/cursor/limit before value/source hydration. Reuse read_snapshot,
public batched hydration, shared continuation checking and existing output error classification.
Count canonical encoded bytes consistently; avoid serializing the entire growing response for
every candidate row. Preserve a final envelope-size check and honest oversized-row refusal.

SQLAlchemy `yield_per`/Result.partitions can bound client buffering for detached inventories;
use the result as a context manager so early termination closes its cursor. It does not bound
server joins, recursive expansion, sorts or total source payload. Existing keyset batches remain
preferable where hydration needs another query on the connection. Do not replace them wholesale
with a long-lived cursor.

## Declare relation question semantics before selecting its algorithm — DA-039

Current `domains/statistics/queries.py:312–380` enumerates depth-four walks with UNION ALL and
sorts their path strings. Preserve that question under an explicit versioned bounded-walk contract:
relation kinds, direction, edge multiplicity, cycle/revisit policy, maximum depth and universe are
part of the query meaning and token identity. A complete answer means all matching walks under
those semantic bounds, not arbitrary-depth reachability. Default depth four becomes visible.

For interactive execution, evaluate a frontier at a time over indexed selected edges, retaining
compact fact-ID witnesses. Enforce examined-frontier/edge and retained-state limits before issuing
the next expansion; no query step may fetch an unbounded adjacency batch. Account for edge/path
payload and visited state, not only emitted rows. Sort only bounded frontiers or use a stable
frontier/edge key order. The new query version declares depth/frontier/fact-ID ordering
in place of the old lexical path-string order; old cursor formats are refused through existing
query-compatibility handling. Edge identity and walk multiplicity remain unchanged. A bounded page may still require more search to find a matching target;
that work consumes the operation budget. On exhaustion return explicit partial/refused semantics,
never absent or complete. Do not promise resumability from the last returned path: a partial
frontier needs its own sufficient continuation state, or require a fresh explicitly selected run
with a larger admitted budget. No durable traversal job framework is justified by this review.

A separate reachability/shortest-witness question can avoid enumerating walks and use a native
frontier or suitable graph algorithm, but must have another declared contract/version. NetworkX
is a candidate for bounded detached projections already required by another consumer; moving the
whole realization into Python merely to bound a small request is rejected. PostgreSQL CYCLE can
implement a deliberately selected cycle policy; automatically applying it changes walk meaning.
An outer LIMIT is not a work bound when an outer sort/join consumes recursion.

**Preserved scope:** do not remove intermediate nodes merely because the requested target set is
small. Semantically necessary global analysis keeps its required universe. Bounded refusal is not
alone A4 evidence; indexed adjacency and bounded frontiers supply the physical route. Measured
capacity remains unestablished.

## Persist split decisions, not just labels — DA-037

Keep the existing evaluator-owned document split relation and its immutable source assignments.
For new assignments, record the producing release/effective split policy, actual seed, source
population/grouping inputs and algorithm version, assignment reason and resulting split through
one protected operation. Shared invocation metadata can be stored once and referenced per
assignment; a table/object per document is unnecessary. The operation receives the frozen policy,
not a live project-default lookup hidden in a replay.

Persist idempotent intent: exact repeated assignment replays; a different decision for an already
assigned source refuses or follows an explicit migration that preserves provenance. Retain the
existing dev/test meanings and M1's distinct origin partitions and sample metadata. Existing rows
whose provenance cannot be reconstructed remain explicitly legacy/provenance-unavailable; do not
invent historical seeds, reasons or source populations. A forward native migration adds this
contract; frozen migration bodies and historical grades remain untouched. CLI/API status and M1
reference prerequisites expose that older provenance limit.

**Alternative:** folding dev/test and M1 training/origin partitions into one enum is rejected:
they answer different leakage and sampling questions. Replacing the split algorithm is unnecessary;
the defect is loss of its actual inputs/results at the effect boundary (`evaluate/semantic.py:528–599`).

## Library evidence and limits

Orientation: [SQLAlchemy §8 and §11.4](../../../libraries/postgresql/sqlalchemy.md),
[Arrow §5.2](../../../libraries/analytical_infrastructure/pyarrow.md),
[DuckDB §6.5](../../../libraries/analytical_infrastructure/duckdb_2.md), and
[NetworkX traversal](../../../libraries/scientific_compute/networkx.md).
Context7 resolved SQLAlchemy to /sqlalchemy/sqlalchemy/rel_2_1_6 and PostgreSQL to
/websites/postgresql/18, then queried read transactions, streaming, and recursive cycle/limit semantics.
[SQLAlchemy 2.1.6 connection source](https://github.com/sqlalchemy/sqlalchemy/blob/rel_2_1_6/doc/build/core/connections.rst)
supports fixed buffering/partition lifetime and pre-transaction isolation options.
[PostgreSQL18 recursive-query documentation](https://www.postgresql.org/docs/18/queries-with.html)
explains CYCLE and why outer sorting defeats LIMIT-based early termination. Installed SQLAlchemy
postgresql/base.py:245–272 and psycopg.py:570 were inspected for read-only dialect support.
These interfaces are **Interface-checked**; the proposed composed operations remain **Proposed**.
Arrow/DuckDB/NetworkX alternatives are not newly selected execution routes by this section.

## Closure evidence required after implementation

Independent cases must distinguish no evidence from complete absence; subset paging from source
completeness; rejected/ambiguous/unassessed facts; premises with differing standing; missing producer
reports; large source payloads; early cursor close; cyclic/parallel-edge/reconvergent/high-degree
walks; search-budget exhaustion before any matching output; token reuse after contract/selection
changes; and immutable split replay with a seed override. Verify actual CLI/MCP/export consumers
against native populated data at their proper integrated endpoint. No checks here were executed.
