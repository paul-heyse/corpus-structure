# Python validation and PostgreSQL execution through SBX-09

**Reviewed 2026-11-22.** Main `d1a917c68`, with the plan series at that revision. The
production checkout was clean. The isolated comparison uses registered bounded-codec
assembly `663254b05`, the draft live-page handoff, and an existing test-only fixture edit
outside the selected comparison. PostgreSQL 18.7, CPython 3.14.10, Pydantic 2.14.1,
PyArrow 26.0.0 and DuckDB 2.0.0. The [coordinator](../plans/set-based-execution_2026-11-21.md)
owns acceptance and cutover. This review covers materially affected live reads, worker
handoff, request lifecycle, completion and replay, and the qualification paths that exercise
them. It extends the [post-pilot review](set-based-execution-through-sbx09_2026-11-22.md)
where current execution supplied new evidence.

## Combined judgment

Advance [I01](#I01) before resuming broad qualification. The read watchdog and a fixed-leaf
nesting probe establish amplification in generated validation of already admitted live
pages. The same admission principle applies to the summary projection. Keep the current
native disclosure and independent read-budget check.

There is also material work inside PostgreSQL. Start with focused attribution and corrections
on the event journey [I02](#I02), [I03](#I03) and [I04](#I04). The read requires different
changes at the native and Python boundaries. A faster Python projection cannot reduce
request attachment or completion-retention time. A faster SQL plan cannot remove the
generated Python revalidation. Move the smallest keyed read needed for an ordinary supported
caller forward only if the Python handoff and native measurements establish that need. SBX-11
owns the full keyed query contract.

Use [I05](#I05) for the remaining handoff and proof-consumer migrations and [I07](#I07) for
qualification. Keep the selected annotation carrier. The strongest columnar opportunities
are already-typed populations and finite, authenticated replay, with specific applicability
conditions in [I06](#I06). The review applies the repository's execution-fit and test
assessment guidance, particularly FP-04, FP-06, FP-07 and H5–H14, H18–H23 and H28. The
recommendations below are **Proposed**. Scoped checks and projections carry their own
evidence labels.

## What the long clocks establish

| Scope | Observed evidence and limit |
|---|---|
| Live read | The current independent-read control hit its 30-minute watchdog in the captured Pydantic validator during the final query. The final query had a different product filter and default budget, which legitimately required a fresh, guarded read. The worker also spent 232 seconds in fixture setup. Receipt `9a40ecca090e424ba4bb0f52a238975f`. |
| Shared event fixture | **Measured.** In one 1,432.8-second setup, 106 statements of at least 250 ms accumulated 1,046.9 seconds of server elapsed time. This includes 22 result reads totaling 302.0 seconds, eight requests to attach totaling 204.9, and seven to retain completion intent totaling 191.6. The outer attach took up to 107.3 seconds. Durations can overlap. The outer plans establish endpoint costs and leave attribution within the routines open. Receipt `f02c6b33e0d14cd4b77b97c5a3394854`, event fixture only. |
| Native proof publication | The older M1 publication statement timed out at 120 seconds in native JSON meaning conversion. A separate 300-second diagnostic reached a subsequent normalization traversal before cancellation. The ordered array codec and direct canonical observation identity passed the real M1 case under the normal 120-second statement limit. Overall managed time was 951.9 seconds. These records establish a resolved class of premature statement cancellation and no passing per-statement timing. Receipts `ecb00e443c4d4e68a867d9f5dafb0352`, `5ec6ed6dccae4b9e9be19e9178dd306b` and `7c1659f02d00483a83953d1b9b5b24bd`. |
| Detached and provider work | The exact finite/rich replay took 378.5 seconds, including 263.8 seconds of setup and 96.1 seconds for the full body. The D1 figure was 23.2 seconds of export and 163.0 seconds of offline verification and replay. A later authenticated-header and binding reuse change brought offline verification of that same archive to 35.0 seconds and replay to 0.13 seconds. Six actual annotation and canonical provider cases passed in 2,738.7 seconds on one worker. Receipts `93e9997f5d61466e9201c87390e15671`, `4578a734f8e04db69e4918c5687025d9` and `267e776231a74518b001f5d387fbb0dd`. |

The [probe folder](../design_review/evidence/2026-11-22_python-postgresql-efficiency/README.md)
retains the bounded measurements. The [cutover history](../plans/set-based-execution/cutover-and-qualification.md#development-reset-through-sbx-09)
and [archive timings](../plans/set-based-execution/owner-resolved-reads.md#sbx-12) give the
registered source and broader ownership. No total in the table measures a standalone SQL
operator or establishes a general latency target.

<a id="I01"></a>
## I01 — Transfer the admitted live page into Python projection

**Observed defect.** The native transport checks the current installed wire digest, validates
the result and interprets its field roles. `DemandResult` serializes the admitted value and
lazily parses and interprets it again. On a cache miss, projection receives the bytes and
repeats interpretation, validates the entire generated type, compares material equality and
freezes the result. The generated recursive list alternatives overlap. This work is unrelated
to the subsequent changes in requested scope and budget.

**Measured 2026-11-22.** The bounded comparison used the same admitted synthetic page in
both branches. With one leaf and 10, 14, 18 and 20 nesting levels, the old projection step
took about 10 ms, 153 ms, 2.43 s and 9.80 s, respectively. The output grew from 2,310 to
2,460 bytes and the initial output check stayed below 3 ms. At eight nested levels and widths
8, 32 and 128, the old projection took 39, 154 and 612 ms. The candidate's serialization,
snapshot, cut and projection together took under 1.1 ms in each of these synthetic cases.
Both routes yielded equal selected rows and exact cut bytes. The measurements exclude a
database and do not predict the end-to-end gain for the actual read.

**Tested 2026-11-22.** The same isolated draft passed all 78 selected native and wire/cut
controls, including the exact independent-read test that hit the watchdog on main
(`a091707e98c443ae954a80a58ad2b01e`). The live case spent 197.7 seconds in setup and 38.3
seconds in its full test body on this private host. This establishes feasibility through
the normal scoped read and refusal entry points. The previous attempt differed in host,
source and workload contention, so these times supply no speedup ratio.

Use the draft private live constructor in the `DemandResult` owner, with one immutable
snapshot shared by the current-query projection. Keep the strict generated path for raw
bytes, including a caller-created `DemandResult` without native acquisition. Preserve
material field and value fidelity, native descriptor and current trust checks, storage
bounds, exact retained lexical cut bytes on replay, and mutation isolation. An arbitrary
constructed object cannot vouch for native admission. Before merging, demonstrate that
initial admission entails the downstream generated shape and material guarantees used
by projection. Compare negative inputs with missing fields, excess support keys,
boolean versus integer, invalid tags and malformed numerics, as well as valid pages and
historical cut/cursor bytes. Close any genuine gap at admission or retain a narrow
consumer check. Both paths refused a missing release, boolean generation and unexpected
product field in the probe. First admission also refused unknown tags and missing tag payloads.
Both shape checks admitted the noncanonical integer spelling `"01"`, which the canonical
tag decoder refuses. Preserve that semantic check at its owning boundary.
Keep the current eager canonical
bytes during this repair because the selected-query cache and pinned consumers use them.
Investigate changing that retention only with a named consumer and [I02](#I02)'s exact
byte/cursor controls.

The selected characterization summary has a related defect. It revalidates a whole
native JSON body as strict Python tuples and can refuse an admitted result. Its response
also drops the plain body while still exposing `meaning_body`. Project bounded metadata
from the already authorized nominal body, remove both payload fields from the summary,
and keep the archived nominal filter, provider attribution and response schema. The
separate serving control passed by unit identity `4b62418035d8469f929a1cfde9ccb8d2`. The
native attempt `3adb62f740974af0b243b45161c9e265` reached the summary then failed an old
partial-result assertion against an actual complete fixture. Retain the controlled partial
and unknown cases and verify the genuine fixture's complete coverage and metadata.

**Measured 2026-11-22.** At the tagged-field boundary alone, the existing canonical codec
took 0.046 ms on a 16-level sequence. The generated annotation adapter took 622 ms on the
same value. The canonical codec also refused an unknown tag, missing string payload,
and noncanonical integer that this generated field adapter accepted in isolation. Native
Draft7 already dispatches by first tag. These are constituent controls independent of public
wrapper and detached verifier behavior. Where a full raw reader still suffers this growth,
use the existing tag owner and strict arity to replace the recursive union there. Keep
envelope and nominal checks, including missing versus null, decimal precision, members,
partitions and references. Changing the validator alone would leave the redundant live check
and copies.
SBX-08 owns the live handoff, and SBX-11 owns changes to result shape. [Native transport](../../python/corpus-structure/src/corpus_structure/semantic/data_operation_storage.py#L98) ·
[Projection](../../python/corpus-structure/src/corpus_structure/semantic/demand_query_projection.py#L21) ·
[Selected summary](../../python/corpus-structure/src/corpus_structure/serve/characterization.py#L92)

<a id="I02"></a>
## I02 — Bound native examination before building result bodies

A first read assembles scoped trust and locks in order. A continuation checks current
standing. For body-bearing queries the frontier can independently examine canonical
body lengths before the products read constructs its reply. Selected cache reuse still
depends on that current authorization and caller budget. The native result builder also
serializes the assembled envelope to enforce exact bytes. These facts explain why there
can be multiple traversals. The event log alone does not identify which traversal dominates.

**Measured and tested 2026-11-22.** On the empty installed bounded-codec qualification
target, the PostgreSQL JSON-schema check for the synthetic read-output page stayed near
3 ms through depth 32. The 172 KB, 10,000-leaf case took 5.73 ms for that check, 25.56 ms
for canonicalization and 49.33 ms for meaning conversion in separate client-timed probes.
These observations concern distinct operations on synthetic shapes. The actual attach and
retain input schema costs remain open. A private, authorized three-product control passed
in 1.195 seconds of test body after 79.1 seconds of setup. It selected one product and read
its authentic support. The late nested-plan capture found no statement above 100 ms in
the remaining interval. The managed environment stripped the proposed Python observer.
The smaller fixture leaves the expensive event internals open.
[PostgreSQL evidence](../design_review/evidence/2026-11-22_python-postgresql-efficiency/postgresql/README.md)

Use one bounded case with a stable resolved cut and the exact role. Compare a fresh cut,
continuation, first whole-body page, repeat at the same budget, repeat with a lower budget,
and a keyed request with one wanted member in many unrelated members. Attribute examined
rows and bytes to scope acquisition, body selection, JSON assembly and serialization.
Measure native wrapper and nested statements separately from the client. Start with
database-scoped `pg_stat_statements` deltas and wait observations. Use nested
`auto_explain` selectively when a specific body, scope or ordering branch is still
unexplained. Compare ordinary and instrumented runs and keep payload parameters redacted.
The current shared outer plans have no nested timing. [Read owner](../../python/corpus-structure/src/corpus_structure/semantic/demand_result_native.py#L81) ·
[Body and budget projection](../../python/corpus-structure/src/corpus_structure/semantic/data_operation_projections.py#L1888) ·
[PostgreSQL 18 nested plans](https://www.postgresql.org/docs/18/auto-explain.html) ·
[Serialization measurement](https://www.postgresql.org/docs/18/sql-explain.html)

Prefer to reach the authorized key before opening or serializing the product. The
selected-contribution reader prepares a full authenticated SQLite closure even for exact
roots, and live reference authorization fetches the parent meaning per lookup. Compare
existing addressed reads and context-only acquisition with one prepared, exact same-cut
binding batch, native header or member projection, and reuse of the examined result within
one acquired transaction and budget. Context-only acquisition can replace a pass where
it supplies the required authority and the exact budget is still enforced. A retained length
can accelerate a bound only when it proves the same encoded measure including the applicable
selection, framing and kind. A cheaper approximation must preserve refusal semantics.
Challenge denial after revocation, lower budget after a warm cache, empty versus withheld
results, continuation ordering, and equal-content members from different producers.
Use the existing read protocol and SBX-11 where cross-consumer projection is needed.
This sharpens [post-pilot I03](set-based-execution-through-sbx09_2026-11-22.md#I03).

<a id="I03"></a>
## I03 — Share invariant native attachment work across a batch

**Inspected.** Batch attachment already acquires the ordered union scope locks and read or
source-set evidence once. Inside the item loop it derives support scopes, canonicalizes
the item for an exact binding digest, accumulates JSONB and enters a scalar attachment
with per-item failure isolation. A batch with many distinct overlapping bindings gets
less benefit from an exact-item memo than a batch of duplicates. The 107-second outer
call establishes that this path deserves attention. Individual loop, hash and indexing
costs remain **Proposed** investigation targets.

Profile a representative batch with common versus disjoint scope and duplicate versus
distinct bindings. Preserve actual refusal, adopted result, and new attempt cases.
Extract the support-scope relation once where its inputs and lifetime are genuinely
invariant. Reuse exact scoped facts through the existing attachment call, keep per-item
proof/claim decisions and rollback behavior, and consider a set-shaped output construction
if accumulator work is material. Compare with the current shared-lock batch and with a
full relational rewrite. Favor the focused change when whole-statement fusion would
change isolation or increase lock holding and failure cost. Check both commit orders,
first eligible delivery versus unrelated publication, repeated idempotent attachment,
and one invalid item adjacent to a valid item. Keep two independent formal producer
occurrences, even when both outputs occupy position zero. SBX-05/06 own exact evidence
binding and readiness. [Attachment owner](../../python/corpus-structure/src/corpus_structure/semantic/request_attachment_native.py#L2133) ·
[Computation and current custody](../adr/0149-contextual-requests-and-projected-computation.md)

<a id="I04"></a>
## I04 — Carry completion validation under its established seal

**Inspected.** The public native wrapper runs an input schema check before its internal
routine. Retention acquires support and checks live claim and correspondence, then uses
the full payload in its intent identity and in a payload digest. Publication keeps live
authority checks and chooses between the retained seal and correspondence. Recovery
re-establishes current facts as needed. These are separate owners and need separate
timings. The M1 evidence establishes the value of removing a second traversal of
already canonical native observations. It does not establish the cause of the event
fixture's 63-second retention calls.

Measure wrapper schema work, canonical bytes and digests, correspondence and proof
queries, lock acquisition and native writes as separate operations. Compare fresh
retention, sealed publication, retry/recovery and a changed-premise case on the same
bounded packet. Carry canonical bytes or digests between these operations only where
the exact value and validation version stay fixed. A digest cannot substitute for a
live claim, current proof establishment, or exact selected use. Preserve the distinct
framed intent identity and payload digest. Share the canonical component while keeping
the complete claim/runtime framing and seal verification. If a public packet
still incurs a large schema cost, compare keeping the public full check with a smaller
protected native handle produced by in-transaction validation. Price the extra
lifecycle or storage before selecting a handle. Reject any design that simply accepts
an untrusted assertion. Preserve exact digests, reply and input budgets, two-output
positions, lost acknowledgement, cross-purpose refusal, and atomic publication.
SBX-04/06/08/09 share this boundary. [Wire wrapper](../../python/corpus-structure/src/corpus_structure/semantic/native_protocol_authoring.py#L830) ·
[Retention](../../python/corpus-structure/src/corpus_structure/semantic/data_completion_settlement_native.py#L1071) ·
[Publication](../../python/corpus-structure/src/corpus_structure/semantic/data_derivation_native.py#L430)

<a id="I05"></a>
## I05 — Materialize worker and witness inputs at their consumer

**Inspected.** Hydration eagerly builds witness rows and normalizes analyzed scopes
even for callers that never use those rows. The admitted input carrier already returns
its cached decoded value. Python witness matching then compares each output against
candidate members, re-encoding both sides of comparisons, and native settlement also
establishes witness correspondence on applicable paths.
Completion decodes output meaning for witnesses and separately parses those same bytes
to construct a native packet. CPU ports already have an acquired descriptor and a
special sealed source path. Generic arguments and replies still cross a typed boundary.

Prepare witness inputs only for operations with witnesses and only for roles and
fields authorized by the witness contract. Compare relying on the authoritative native
check where it covers the same cases and diagnostic obligations, with preparing an
exact normalized match relation keyed by declared group and occurrence once. Preserve
same-member matching, numeric and context equality, and refusal of cross-product matches.
An independent Python oracle can still test native correspondence. Share the owned decoded or canonical
snapshot with completion assembly where the two forms agree. Preserve independently
established occurrence and product references. Retain admission and post-encoding
checks for mutable code/assets and the attempt and reply fences. Compare per-role
materialization and bytes over one actual two-report construction or event path.
Use an invalid witness and a late source change as independent controls. Avoid an
additional generic worker representation if existing carriers can remove the repeated
work. This extends the established SBX-08/09 ownership and the post-pilot I02/I05
scoped conclusions. [Hydration and assembly](../../python/corpus-structure/src/corpus_structure/orchestrate/data_operations.py#L1055) ·
[Witness matching](../../python/corpus-structure/src/corpus_structure/semantic/data_operation_output_witnesses.py#L416) ·
[CPU argument and reply boundary](../../python/corpus-structure/src/corpus_structure/semantic/data_operation_cpu.py#L421)

<a id="I06"></a>
## I06 — Use typed relations where they replace a complete pass

Keep the acquired immutable carrier on the annotation fork, with PostgreSQL owning
governed transactional selection and publication. The prior worker trial established
transport parity and required extra conversion for that consumer. For the keyed native
route, test projection before packet construction first. A committed exact pin and
granted companion projection can support an ADBC/Arrow path. An imported snapshot
cannot make the other session see the acquiring transaction's uncommitted pin.

For wide, already-typed populations or finite selected archives, reuse the companion
export's selected-pin, exported-snapshot and ADBC batch-transfer pattern. Compare a
`RecordBatchReader` and Arrow projected scans against the current extract and replay
path. Use DuckDB relations for semijoins, anti-joins, explicit ordered windows and
independent parity where they replace repeated row scans. Use a relation's
`to_arrow_reader()` for streaming and verify advancing and closing the reader.
A callable that builds all rows before returning the reader merely moves the copy.
Benchmark a complete named path from authorized extraction through conversion, scoped
query, and file authentication or PostgreSQL publication. Keep independent multiplicity,
null and ordering expectations. For detached work start with the existing D1
header/binding reuse result and compare Parquet `Dataset.scanner(columns=..., filter=...)`
or DuckDB `read_parquet` on an authenticated finite archive. Preserve exact schema,
manifest, scope and original support and charge index setup and cold reopen.

**Tested 2026-11-22.** The current-version common-analytics probe repeated the existing
window and Arrow/Parquet parity, truncation refusals, and nanosecond UTC egress. Arrow
structural admission still accepts a duplicate ordinal and out-of-bounds span. A
separate installed decimal control found that a 103-digit decimal exceeds both Arrow
decimal256's 76-digit precision and DuckDB's 38-digit `DECIMAL` width. The current
generic codec allows up to 16,384 fixed-point digits. Use modeled bounded numeric
columns where representable. Carry wider exact values as tagged canonical text where
they merely need transport, and reserve arithmetic for an exact compatible engine.
Exercise mixed precision and scale along with that wider representation.

Use SBX-11/12 for selective read and archive trials and SBX-18/19 for broader compute
placement. A change to where authority is established needs the existing decision
route. [Pilot](../plans/set-based-execution/common-analytical-basis.md#pilot-implementation-and-evidence) ·
[Typed relation evidence](../design_review/evidence/2026-11-22_sbx-common-analytics/README.md) ·
[Companion transfer](../../python/corpus-structure/src/corpus_structure/serve/companion_export.py#L125) ·
[DuckDB 2.0 Arrow export](https://duckdb.org/docs/2.0/guides/python/export_arrow) ·
[Snapshot obstacle and options](declared-data-operations-postgresql-domain-alignment_2026-11-14.md#i07--preserve-transport-distinctions-and-record-the-target-vector-contract)

<a id="I07"></a>
## I07 — Qualify on a stable source and reuse valid preparation

Separate candidate authoring and model compilation, installation or clone, release
preparation, actual provider/worker execution, and the assertion path. A pytest phase
is only the fixture boundary. The real event fixture publishes and fits during setup.
The finite/rich test setup took nearly three quarters of the total wall time. Current
private hosts can share a verified deployment template across per-test commit clones.
Reuse immutable release preparation and finished authenticated fixtures where their
premises hold. Keep a genuine cross-boundary publication and replay case and preserve
independent expectations for identity, authority and failure. Cache preparation by
the actual release, runtime and source premises. Never give stale generated companion
metadata standing to authorize an active consumer.

Retain failed and interrupted receipts. The seven-worker alphabetical retry admitted
mostly heavyweight native cases up front. Its lighter disjoint cohort completed 944
passing cases before the pause, with different test work. Group slow native case
identities and release-independent controls so each can progress with a bounded
worker count. Keep exact affinity groups and reconcile them against the original
required selection with `ci test coverage`. The earlier aggressive concurrency
triggered host OOM. A later hot change to generated reporting metadata invalidated
active snapshots. Stable source, bounded concurrency, and test-identity reconciliation
address both problems. They supply no generalized product performance claim.
[Qualification owner](../plans/set-based-execution/cutover-and-qualification.md#development-reset-through-sbx-09)

## Integration and limits

I01 and the affected summary disclosure should land as a coherent read correction before
broad retry. In parallel, attribute the slow native event endpoints with I02–I04 and use
the scoped results to decide whether a native correction is an SBX-09 prerequisite or
belongs with the broader SBX-11 change. Keep I05 focused on concrete already-owned
values. I06 and I07 give independent ways to reduce materialization and fixture burden.
Each proposal has a different invalidation boundary. Compare gains and integration
costs at the whole affected path.

Independent source review challenged the draft at the admission and verification
boundaries. It identified the repeated same-member witness comparisons and made
native-shaped negative parity, exact budget checks, per-item attachment isolation,
distinct intent/digest framing, and mixed-precision cases explicit above.

The review does not confer final-source qualification. Development reset follows the
existing accepted cutover route after qualification. This review does not change the
coordinator or selected authority. Treat any nested SQL hotspot that was not observed
in representative admitted work as a hypothesis, and any synthetic timing as local to
the stated input and check.
