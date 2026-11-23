# Set-based execution through SBX-22 after the columnar cutover

**Inspected · 2026-11-23.** The review starts at `c1d834921` on a clean tree, with
product source `4a9c2889e`. It follows the installed SBX-11 development checkpoint
`semantic_sbx_answer_guards`, the open SBX-10 installed producer seam, and the remaining
work through SBX-22. It traces the native and public reads, detached review and evaluation,
PDF production and source inspection, analytical workers, and native installation and
qualification. The findings build on the seven earlier recommendations and the retained
pilot and managed results. One synthetic probe was run on PyArrow 26.0.0 and DuckDB 2.0.0.
The ADBC assessment uses the selected PostgreSQL driver 1.13.0 and existing evidence.
The probe establishes file-opening behavior on this machine. The performance effects
below are qualitative, and the review adds no installed, provider, stage or whole-book
qualification. [Plan coordinator](../plans/set-based-execution_2026-11-21.md#execution-queue) ·
[Development checkpoint](../../STATUS.md) ·
[First review](set-based-execution-after-sbx09_2026-11-23.md)

## Combined judgment

The largest gains come from requesting fewer facts, resolving them once under the right
authority, and keeping their custody through the last consumer. The native reader can avoid
rebuilding readiness on historical reads. A change-impact cache hit can avoid acquiring
payload entirely. A sparse PDF diagnostic can seek by pointer without decoding a family.
Each of those changes removes work before an analytical engine receives data.

Use PostgreSQL for exact cut selection, grants, mutable coverage and committed publication.
Use Arrow as the typed acquired carrier and for bounded single-relation projections. Use
DuckDB for compact relational work on that carrier, with ordering and multiplicity explicit.
Parquet makes repeated selected replay cheaper once verified file custody extends through
actual scan execution. Keep the gains composable through the existing read, archive,
execution and deployment owners. A universal reader, a persistent analytical service and
general-purpose materialized indexes would add a second lifecycle without a demonstrated
consumer. [Accepted population basis](../adr/0154-sbx-columnar-populations.md) ·
[Owner-resolved reads decision](../adr/0147-sbx-owner-resolved-reads.md)

<a id="I08"></a>
## I08 — Bind governed coverage to qualified dependencies

**Inspected limitation and proposed amendment · SBX-11, with SBX-06 as coverage owner.**
The settlement helper's recursive frontier uses operation, subject and original source.
It carries the upstream operation forward with the downstream subject and source and
matches obligations on that same tuple. The selection can contain a narrower analyzed
scope. Sibling scopes and dependency roles that change subject, source set or qualified
context challenge this mapping. Source inspection establishes the incomplete
correspondence. It has yet to demonstrate an incorrect freshness answer on an installed
case. [Dependency and obligation selection](../../python/corpus-structure/src/corpus_structure/semantic/obligation_readiness_native.py#L1108) ·
[Coverage owner](../plans/set-based-execution/references-and-projection-keys.md#settlement-coverage)

Follow declared binding roles and actual enrolled dependency facts, with exact qualified
context in scope matching. Use existing dependency delivery and readiness facts where
their determinants cover the request, and report insufficient coverage when the mapping
is unestablished. Keep the current trust and disclosure checks over the resolved scope.
Retaining the current recursive helper as the semantic source for all reads would keep
both the correspondence limitation and its repeated work.

The historical `last-settled` path calls the complete helper and discards its settlement
result after it checks disclosure. Share qualified dependency scope preparation, and give
historical authorization an operation that checks disclosure without deriving new
readiness. A historical answer retains its captured settled cut and remains subject to
current trust and disclosure. A change to current settlement eligibility does not by itself
disqualify that historical answer. Evaluate current coverage for current reads. Reuse an
established settlement basis across equivalent reads only where the native owner can keep
the exact generation, coverage and authority correspondence and still account for the
individual read receipt. Current answer reuse must account for qualified coverage and
current membership, including proof appearance after a negative result. Qualify two analyzed
scopes under one subject, an upstream role with a different source, an independently settled sibling, revocation,
an upstream commit between reads, and an old-generation continuation. This extends the
earlier page-work recommendation to the work performed before address selection.
FP-07, DP-04, DP-07, DP-09, DP-10.
[Historical authorization and fresh observation write](../../python/corpus-structure/src/corpus_structure/semantic/governed_read_native.py#L167) ·
[Native read and freshness target](../plans/set-based-execution/owner-resolved-reads.md#sbx-11)

<a id="I09"></a>
## I09 — Make acquired facts finite and reusable across structural consumers

**Proposed amendment · SBX-10–13 and the readers they replace.** Put an explicit finite
acquisition boundary behind the planned typed selected reader. Acquire purpose-scoped
addresses, headers, provenance and required bodies within the exact native cut. Give each
pure derivation phase finite acquired facts so Python can interpret them outside the read
transaction. Where one phase discovers additional addresses, reacquire only those facts
under the same pinned cut through an explicit acquisition. A stream that still needs the
source transaction owns it until close, refusal or cancellation. A lazy wrapper over the
current reference resolver would leave additional SQL in derivation and obscure which operation can read
more facts. Preserve exact producer and current uses, reference occurrence and order, and
the difference between missing, undisclosed and incomplete evidence. Continue with public
direct, CLI and MCP consumers on the same semantic contract, including textbook structural
readback. [Reference acquisition](../../python/corpus-structure/src/corpus_structure/semantic/live_reference_resolution.py#L189) ·
[CLI transaction owner](../../python/corpus-structure/src/corpus_structure/cli/selected_results.py#L178) ·
[Typed selected access](../plans/set-based-execution/owner-resolved-reads.md#sbx-12)

Two migrations show where the boundary pays:

- **Change impact.** The current route constructs a full SQLite support index for each cut,
  derives smaller evidence and edge collections, and does both acquisitions before checking
  the comparison cache. Acquire typed selection and coverage headers, exact producing and
  current-use edges, closure/membership facts and scoped revocation facts. Compare them with
  DuckDB joins, grouped counts and anti-joins where these replace reconstruction, and hydrate
  detail only for an explanation that needs it. An eligible repeat can check the actual
  determining facts without importing bodies. Compare equal-content membership changes,
  duplicate occurrences, incomplete discovery, upstream revocation and an unchanged warm
  comparison. [Support acquisition](../../python/corpus-structure/src/corpus_structure/semantic/change_impact.py#L434) ·
  [Acquisition before cache](../../python/corpus-structure/src/corpus_structure/semantic/change_impact.py#L621)
- **Evaluation and operation-event frames.** The reference, original-source and prediction
  reads also build separate indexes, and event frames reopen already bound inputs for
  comparison. Acquire an immutable bundle of selected facts per exact cut and purpose,
  batch roles and provenance, and reuse that bundle within grading, fitting and event
  construction where they share an invocation. Keep the reference demand separate from the
  prediction demand and preserve source-role authorization. Use Arrow for the fact bundle
  and DuckDB for correspondence and missing references within acquired scope. Retain
  independently authored coordinate expectations, semantic scoring and effect-time
  checks. Compare equal payloads with different producing uses, protected reference
  refusal, two releases and a mismatched coordinate. [Selected reference evaluation](../../python/corpus-structure/src/corpus_structure/evaluate/selected_references.py#L560) ·
  [Event reconstruction](../../python/corpus-structure/src/corpus_structure/evaluate/declared_operation_events.py#L321) ·
  [Evaluation preflight target](../plans/set-based-execution/owner-resolved-reads.md#sbx-13)

For the shared reader, exercise a denied subsequent page, an early-stopped reader and a
consumer exception, as well as explicit empty and incomplete cuts. Alongside the output and
derivation-fact controls, exercise field projection and exact item-address absence for
partitions, and rule fingerprints, premises and establishment provenance for proofs.
Distinguish absent and withheld evidence when a proof appears with unchanged payload.
Use address-first candidate windows, native authority and independent output expectations
already identified by the first review. Bring the structural contract forward as each consumer
moves so the interim reader and SQLite paths can retire with their last callers.
DP-06, DP-07, DP-10, DP-18, DP-19, DP-20, DP-23.

<a id="I10"></a>
## I10 — Keep verified archive bytes under custody through lazy scans

**Tested library behavior and proposed correction · SBX-12.** The archive authenticates files
by path and the selected population reader passes paths to a lazy DuckDB relation.
The new synthetic probe hashes an open Parquet file, creates a path-based DuckDB relation
and replaces the pathname before execution. DuckDB returns the replacement row. A
`pyarrow.parquet.ParquetFile` using the original held `NativeFile` returns the original
row and the original value in the omitted column. A check at relation creation therefore
cannot bind a later pathname open. A held descriptor resolves replacement of the pathname
in this test. In-place mutation and production archive admission are outside its scope.
[Archive verification](../../python/corpus-structure/src/corpus_structure/serve/demand_export.py#L486) ·
[Lazy population open](../../python/corpus-structure/src/corpus_structure/semantic/selected_population_archive.py#L113) ·
[Probe and result](../design_review/evidence/2026-11-23_sbx-parquet-scan-custody/README.md) ·
[Arrow ParquetFile API](https://arrow.apache.org/docs/python/generated/pyarrow.parquet.ParquetFile.html)

Extend the existing file-custody owner so cold archive verification and later scans acquire
the same stable bytes. For mutable detached inputs, compare acquiring an owned immutable
copy before verification and scan with hashing and scanning the same held file under an
actual immutable storage guarantee. An identity check after consuming a stream cannot
recall disclosed rows. For a held-file implementation, `ParquetFile` provides projected row-group or batch
reads and DuckDB can consume the admitted Arrow result when a join is needed. For paths
under exclusive immutable custody, `read_parquet` or a projected dataset scan can seek
directly. Reuse cross-file closure verification only within that verified boundary.
Require complete cold verification, preserve omitted columns in sealed identity, and
test replacement, in-place writes, first and subsequent batches, early close, incomplete
publication and full ordered replay. [File-custody owner](../../python/corpus-structure/src/corpus_structure/semantic/file_custody.py#L84) ·
[Replay owner](../plans/set-based-execution/owner-resolved-reads.md#sbx-12)

Choose sorted row groups and actual scan predicates before considering a page index,
Bloom filters or a separate side index. A DuckDB CLI `EXPLAIN` can confirm projection and
filter placement on the physical candidate. It does not measure I/O or certify identity.
Detached standing remains the archived standing. Current native authorization is still
acquired for live requests. DP-04, DP-09, DP-15, DP-19.
[Retained pushdown probe](../design_review/evidence/2026-11-22_sbx-common-analytics/README.md) ·
[DuckDB Parquet reader](https://duckdb.org/docs/data/parquet)

<a id="I11"></a>
## I11 — Publish PDF access relations that the sparse readers can use

**Inspected repeated work and proposed amendment · SBX-14–17 and SBX-10 readback.** A
sparse report lookup can scan and decode an entire metadata family and query ancestors per
pointer. The protected budget first executes a count and length query over the read
statement and then executes the statement again to return rows. Formula inspection can
also acquire several published readers, repeat the item read during region lookup, and
reopen the complete selected support index for formula interpretations.
[Report family and pointer lookup](../../python/corpus-structure/src/corpus_structure/semantic/pdf_record_reader.py#L593) ·
[Budget preflight](../../python/corpus-structure/src/corpus_structure/semantic/pdf_record_reader.py#L51) ·
[Region lookup](../../python/corpus-structure/src/corpus_structure/semantic/pdf_storage.py#L106) ·
[Selected math](../../python/corpus-structure/src/corpus_structure/serve/selected_math.py#L58)

Derive pointer, page, ancestry, original diagnostic order and report addresses at the
publication boundary that already owns access columns. Reuse that typed relationship
projection for relational certification. A sparse native reader can batch authorized
pointer keys, fetch the matching diagnostics and leave opaque bodies in their existing
carrier until selected. Compare one bounded native evaluation envelope with an address
window carrying exact admitted lengths for the returned representation where such lengths
are cheaply available. The budget must refuse oversized output before transfer, and the
size check must refer to the same authorized snapshot and representation as the payload.
Avoid retaining family-wide report caches alongside an equivalent publication relation.

Pass one invocation-owned exact selected PDF source and reuse its bounded acquired
projections for item, region, formula and contextual diagnostics under the same pin.
Connect selected math to I09 so proof, formula and original source use remain explicit.
The publication catalog currently runs a one-header inspection per selected publication.
Batch those headers at the selected cut, preserving each native publication receipt
check and the catalog's continuation and disclosure semantics. Use the same sparse
address contract for visual evidence while keeping submitted-page, coordinate and
mapping-availability checks. [Catalog header acquisition](../../python/corpus-structure/src/corpus_structure/serve/source_catalog.py#L211) ·
[Visual evidence reader](../../python/corpus-structure/src/corpus_structure/serve/pdf_visual_evidence.py#L286)

Keep the planned one rebuild under captured policy and use grouped counts or anti-joins
for independent certification of coverage, formula outcomes, ordinal and reference
checks. Keep whole-document consumers on full ordered reads. Exercise a selected formula
and its ancestors with many unrelated diagnostic rows, multiple reports with the same
local position, an oversized selected value, protected denial, and complete rebuild and
recovery with independent expected output. FP-07, DP-07, DP-10, DP-20, DP-23.
[PDF publication and certification target](../plans/set-based-execution/pdf-path.md#columnar-pdf-certification) ·
[Formula context handoff](../plans/set-based-execution/validated-values-and-handoff.md#sbx-10)

<a id="I12"></a>
## I12 — Distinguish PDF projection from physical payload acquisition

**Conditional investigation · SBX-16/17.** Published IPC reads concatenate the complete
stored stream before selecting fields. Recovery also reads a whole file into bytes.
The existing candidate inventory already uses Arrow nested kernels. More field projection
and Acero can reduce decode or per-batch work and can leave the largest acquisition
untouched. Compare the existing bounded page stream with an IPC file over verified native
file ownership or a page manifest that binds independently sealed candidate and OCR
streams. Select a split only if a real sparse consumer avoids large transferred or live
parts and full capture, admission and recovery stay simple. Preserve one page receipt and
acknowledgement, full logical admission, exact page/schema correspondence and ordered replay.
Metadata for a projection cannot serve as proof of the bytes that were omitted.
[Published payload and candidate inventory](../../python/corpus-structure/src/corpus_structure/semantic/pdf_record_reader.py#L980) ·
[Recovered payload](../../python/corpus-structure/src/corpus_structure/ingest/pdf_candidate_source.py#L45)

For compact coordinates use DuckDB for relationships and ordered certification metadata.
Feed large opaque parts directly into the existing byte fold. For IPC file reads consider
`pa.memory_map`, `ipc.open_file`, `get_batch` and `IpcReadOptions(included_fields=…)`
within verified custody. Keep Arrow kernels on the existing reader unless an Acero
`RecordBatchReaderSourceNodeOptions` pipeline with filter/project composition removes a
material pass. The retained threaded Acero fixture read ahead beyond immediate demand.
Use a real recovered page with large OCR and a small candidate inventory to decide the
layout and check cancellation, the full validity witness and correspondence. DP-11,
DP-15, DP-19, DP-20.
[Retained streaming evidence](../design_review/evidence/2026-11-22_sbx-columnar-basis/README.md) ·
[Acero capabilities and limits](../libraries/analytical_infrastructure/pyarrow.md#42-acero-the-native-streaming-execution-engine)

<a id="I13"></a>
## I13 — Batch physical work without merging semantic partitions

**Proposed trial refinement · SBX-18/19 and SBX-10's producer seam.** Sentence and canonical
sentence paths invoke canonical population processing per partition. Each call selects
projections, adds ordinals, orders rows, creates an output reader and folds the groups.
For many small partitions, prepare the shared typed projections once on an Arrow relation
with explicit semantic partition and local ordinal. Use one DuckDB plan per bounded
physical cohort, then feed independent ordered partition and field-group folds. Preserve
explicit empty headers, partition commitments, placement, proof premises and reuse keys.
A large partition can remain its own cohort. The better operating point depends on
avoided setup and kept-live state, including sort and spill.
[Sentence population invocation](../../python/corpus-structure/src/corpus_structure/semantic/sentence_partitions.py#L85) ·
[Canonical output loop](../../python/corpus-structure/src/corpus_structure/semantic/canonical_sentences.py#L408) ·
[Population projection and fold](../../python/corpus-structure/src/corpus_structure/semantic/population_canonical.py#L188)

Carry the same ordered stream into sealed output if the durable draft can own it through
close, publication and failed acknowledgement. Keep the incremental result at DuckDB's
relation `to_arrow_reader(batch_size=…)` boundary. The connection-result binding can
materialize the result before exposing batches. The current commitment fold also joins
a whole batch's canonical strings into a transient value. Include it in the byte-lifetime
design. A row-count bound leaves a wide batch potentially expensive. Use wide and narrow
canonical rows, multiple groups, zero rows, repeated placements and changed batch boundaries
to check identical commitments. Retain explicit handling of a single oversized item and
test partial writer, failed seal and cancellation. Keep file-backed output conditional
on eliminating overlapping complete results through real transactional COPY and custody.
[Current IPC buffer path](../../python/corpus-structure/src/corpus_structure/semantic/population_transfer.py#L81) ·
[Shared analytical owner](../plans/set-based-execution/kernel-trial.md#sbx-18) ·
[Relation and connection Arrow delivery](https://duckdb.org/docs/2.0/guides/python/export_arrow)

Rebase the scoped-relations trial on retained span indexes and exact math handoff, with
installed SBX-10 producer integration as a distinct acceptance responsibility. Compare
one typed occurrence/ordinal inventory and one relational candidate through exact artifact
nomination and readback. Run captured DuckDB SQL or typed expressions under the existing
owner. Use partitioned windows with explicit tie breakers, range joins for overlapping
matches and `ASOF JOIN` only for a true directional nearest match. Include multiple
independent formal reports, each with its own local position, and absence and incomplete
cases. Use PostgreSQL for selection or effect-time work that depends on it, and the owning
transaction's Psycopg COPY for session-local keys and uncommitted admission. Consider
ADBC `fetch_record_batch()` on an imported exact snapshot only for committed projected
facts accessible to that purpose. Binding parameters can use a different transport from
COPY result delivery. Preserve the existing exact lexical transfer for values whose
mapping loses meaning. Trial adoption depends on removed preparation and crossings across
the complete chain. FP-07, DP-07, DP-10, DP-11, DP-15, DP-20.
[Current scoped inputs](../../python/corpus-structure/src/corpus_structure/semantic/scoped_products.py#L135) ·
[Trial and adoption decision](../plans/set-based-execution/kernel-trial.md#sbx-19) ·
[Transfer owner](../plans/set-based-execution/common-analytical-basis.md#postgresql-placement-and-transfer) ·
[ADBC PostgreSQL release 25](https://arrow.apache.org/adbc/25/driver/postgresql.html)

<a id="I14"></a>
## I14 — Give the full analytical job one resource allocation

**Inspected realization gap · SBX-18 and worker/publication consumers.** Worker initialization
sets Arrow pools from the CPU worker policy. DuckDB opens each invocation with separate
`threads`, `async_threads` and `memory_limit` settings. The executor reservation covers
input, packet, reply and draft, while native analytical workspace is configured separately.
Extend the existing admission owner so concurrent work receives compatible Arrow, DuckDB,
output and spill allowances from the same job allocation. A private `temp_directory` and an
appropriate `max_temp_directory_size` bound that scratch path. DuckDB's `memory_limit`
covers its buffer manager, while other native allocations, Arrow and mapped files still
need headroom. Treat platform thread pools as process settings and respect that lifetime
when admitting multiple jobs. Keep connections scoped to one invocation unless a reused
worker can establish equivalent drain and cleanup across jobs.
[Worker Arrow pools](../../python/corpus-structure/src/corpus_structure/semantic/cpu_execution.py#L305) ·
[DuckDB connection](../../python/corpus-structure/src/corpus_structure/analytics.py#L131) ·
[Executor reservation](../../python/corpus-structure/src/corpus_structure/orchestrate/data_operations.py#L363) ·
[DuckDB resource limits](https://duckdb.org/docs/2.0/operations_manual/limits)

Use the planned lifecycle evidence on two admitted jobs with a partially consumed result,
a cancellation and substantial sealed output or spill. Account for process and reader
release alongside native scratch and reservations. Keep a serial baseline. Measure the
combined working set only if it changes the carrier, spill policy or safe concurrency
choice. CLI plan inspection and a fast isolated query cannot establish that envelope.
DP-19, DP-20. [Job and worker contract](../plans/set-based-execution/kernel-trial.md#sbx-18) ·
[DuckDB CLI inspection and limits](../libraries/analytical_infrastructure/duckdb_2_cli.md#7-security-resource-control-and-correctness-boundaries)

<a id="I15"></a>
## I15 — Compare executable custody, installed admission and evidence separately

**Proposed sequencing and contract refinement · SBX-10, SBX-16, SBX-19–22.** Runtime
source inspection enumerates module classes before filtering expected nodes. Its class
locator can refuse a generic helper before reaching an unrelated selected callable.
The CPU preparation path has the same enumeration shape. Narrow discovery to the
consumed source nodes with class-code correspondence for Python 3.14. Keep checks on
actually used transitive imports, global/class members and late imports, and verify
cold and warmed execution under the same captured premises. Test adding an unrelated
generic class, consuming a supported generic class and changing a consumed member.
Resolve any material rule change at the runtime-custody owner. This extends the previous
deployment finding to the actual Python capture seam.
[Runtime member traversal](../../python/corpus-structure/src/corpus_structure/semantic/data_operation_ports.py#L1506) ·
[Expected-node filter](../../python/corpus-structure/src/corpus_structure/semantic/data_operation_ports.py#L1581) ·
[CPU helper capture](../../python/corpus-structure/src/corpus_structure/semantic/data_operation_cpu.py#L560) ·
[PDF producer custody](../adr/0155-pdf-producer-custody.md)

For stage, establish the exact registered predecessor and compare read implementation,
wire-only and material lowering changes. Include the split between transformed PDF
publication and shared schema/codec changes, plus producer identity and request
attachment for the installed math seam. Use existing candidate comparison, descriptor
and grant checks. The current application admission checks the installed kernel against
the prepared release. Propose a narrower admission or receipt determinant only if the
comparison demonstrates collateral invalidation and the complete executable and purpose
correspondence can still be checked. Keep the full installation descriptor. Planned
revisions A, B and C describe change strands. The actual stage candidate chain and
applicable receipts govern adoption and restart.
[Installed kernel check](../../python/corpus-structure/src/corpus_structure/semantic/data_operation_storage.py#L156) ·
[Native revisions](../plans/set-based-execution/cutover-and-qualification.md#native-revisions) ·
[Stage registration](../plans/set-based-execution/cutover-and-qualification.md#sbx-20)

Move each independent expectation when its consumer moves. Retire the corresponding
SQLite/JSONL paths, recursive discovery fallback where coverage is established, obsolete
PDF access paths and redundant adapters at the last migrated caller. Keep SBX-21 as
the residual search, including the independent PDF reconciliation oracle while it has a
consumer. Under SBX-22, keep applicability tied to actual source, harness, installed
descriptor, purpose and provider inputs. Reuse authentic unchanged input custody for
reader-only checks. Fresh provider and installed acceptance remain owned by their real
runs. Retained SBX-11 named passes inside a failed aggregate establish those identities.
Run bounded cohorts under the existing managed owner and preserve interrupted results.
Retain the final assembled whole-book interruption and unchanged repeat, direct/CLI/MCP
textbook structural read, revocation/continuation, and controlled native recovery.
DP-04, DP-22, DP-23. [Read results and retained failures](../plans/set-based-execution/owner-resolved-reads.md#sbx-11) ·
[Retirement](../plans/set-based-execution/cutover-and-qualification.md#sbx-21) ·
[Assembled qualification](../plans/set-based-execution/cutover-and-qualification.md#sbx-22)

## Integration order and remaining decisions

First fix qualified coverage and bring forward the finite selected reader while the
SBX-11/12 consumers are changing. Apply the archive custody correction before granting
warm verification reuse. Resolve the PDF access and certification relation together at
publication. In parallel, settle the common resource allocation and executable capture
seam before choosing physical layout or drawing conclusions from the scoped-relations
trial. Start exact-predecessor comparisons early enough to inform stage sequencing.

The highest-priority changes preserve authority, current versus historical meaning and
verified-byte custody. The largest additional cost reductions are smaller native and
typed acquisitions for change impact, evaluation and PDF inspection. Physical partition
batching, split IPC and file-backed output depend on the shape and lifetime of the named
route. Page indexes, alternate ADBC paths and Acero fusion remain targeted choices.
Remote DuckDB, a separate analytical store, portable plan translation and a universal
cache would introduce additional ownership with no workflow in this footprint requiring
it. [Analytical capability dispositions](../plans/set-based-execution/common-analytical-basis.md#decision-routes)

| Earlier finding | Follow-up disposition |
| --- | --- |
| [I01](set-based-execution-after-sbx09_2026-11-23.md#I01) · Native page work | Carry forward address-led windows and safe continuation. Apply [I08](#I08) to coverage before paging and [I11](#I11) to exact PDF budget evaluation. |
| [I02](set-based-execution-after-sbx09_2026-11-23.md#I02) · Shared typed reader | Carry forward shared live and detached interpretation. [I09](#I09) defines finite acquisition, lease lifetime and two previously expensive consumers. |
| [I03](set-based-execution-after-sbx09_2026-11-23.md#I03) · Parquet reread | Keep cold semantic verification and scoped pruning. [I10](#I10) requires custody through scan execution before warm reuse. |
| [I04](set-based-execution-after-sbx09_2026-11-23.md#I04) · PDF certification | Combine certification with the native access relation in [I11](#I11). Compare physical layout conditionally in [I12](#I12) and include split producer custody in [I15](#I15). |
| [I05](set-based-execution-after-sbx09_2026-11-23.md#I05) · Durable streaming | Check partition batching and the byte-wide commitment fold in [I13](#I13), with common admitted resources in [I14](#I14). |
| [I06](set-based-execution-after-sbx09_2026-11-23.md#I06) · Scoped-relations trial | Keep the whole-route adoption decision. [I13](#I13) sharpens its physical work, installed handoff and transfer comparison. |
| [I07](set-based-execution-after-sbx09_2026-11-23.md#I07) · Deployment effects | Use [I15](#I15) to compare captured source, registered effects and evidence applicability while closing the existing package obligations. |

Use the existing package acceptance and refusal cases to decide the selected amendments.
The reviewed plan series continues to own disposition and completion. Static traces reveal
work and ownership opportunities, while the retained product evidence and single new
library probe have the scopes stated above.
