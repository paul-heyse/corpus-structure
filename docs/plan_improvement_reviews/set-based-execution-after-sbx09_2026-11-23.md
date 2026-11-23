# Set-based execution after the columnar cutover

**Inspected · 2026-11-23.** Baseline `4a9c2889e`, clean at inspection. SBX-09 established typed
populations and the new native development root. The tree also contains the SBX-10 implementation
and selected evidence, and development has the two SBX-11 read revisions through
`semantic_sbx_answer_guards`. This review covers the open SBX-11 work and SBX-12–22, with SBX-10
considered where its installed producer or derived views affect those packages. It uses the
current code and retained results. It does not extend the provider, stage, or whole-book evidence.
The installed bindings report PyArrow 26.0.0 and DuckDB 2.0.0. API presence was inspected.
Expected savings are stated in terms of work removed. No performance measurement was made.
[Coordinator](../plans/set-based-execution_2026-11-21.md#execution-queue) ·
[Development checkpoint](../../STATUS.md) ·
[Accepted columnar basis](../adr/0154-sbx-columnar-populations.md)

## Combined judgment

Use the typed basis to reduce the work each caller requests, the state it keeps live, and
the frequency with which it establishes the same fact. PostgreSQL should own selection,
disclosure, settlement and committed effects. Arrow should carry the finite result and run
straightforward column work. DuckDB should perform the joins, ordered processing and set
comparisons within an acquired analytical scope. Several proposed package changes are already
directionally right. The amendments below make those changes apply to the whole path from
acquisition through the final consumer.

<a id="I01"></a>
## I01 — Make the native page bound a bound on work

**Observed gap and proposed correction · SBX-11.** The outputs program materializes matching
records, reads body fields to classify some matches and collects validity seeds across the
matches before the page helper seeks and limits. The limit therefore bounds delivered rows
more directly than it bounds examination. Non-output answers also traverse the selected
obligation's support before reaching the target item. A smaller response or another public
cursor cannot remove that work. [Output matching and validity](../../python/corpus-structure/src/corpus_structure/semantic/selected_answer_native.py#L188) ·
[Page query](../../python/corpus-structure/src/corpus_structure/semantic/selected_answer_native.py#L54)

Seek first on a stable, narrow, indexable address assembled from the exact selected use and
physical output/member coordinates. Apply safe predicates before hydration. For routinely used
`record_type` and `family`, consider compact admission-derived classification when a declared
kind supplies the field. Derive it under existing admission and disclose it under the same
kind and leaf rules. Bounded candidate windows then resolve the validity and disclosure
premises they need, hydrate the chosen payloads and account for delivery. If a candidate is
ineligible, keep scanning within the work bound. Use an internal position for examined
candidates and an externally safe continuation that cannot disclose hidden membership.
Keep exhausted authorized scope, undisclosed scope and a work-bound refusal distinct.

Use the same address-led approach to batch exact references by producing role and use. Keep
one ordered Arrow request/result relation for the reference occurrences and share the
authorized immutable payload for repeated addresses within the acquisition. Carry request
ordinal, role and multiplicity through the joins. Distinguish transferred/examined bytes from
retained buffers. Current authority still applies when reopening or continuing. This replaces
repeat acquisition in the resolver and reduces the work protected dossiers currently drive.
Test a deep page with unrelated members and support **inside the same obligation**, an
oversized body outside the requested keys, duplicates with distinct producing uses, denial
between pages, and a reduced bound. Use the existing attribution route to distinguish
acquisition, validity and serialization. FP-07, DP-07, DP-10, DP-20.
[Reference acquisition](../../python/corpus-structure/src/corpus_structure/semantic/live_reference_resolution.py#L189) ·
[Read budgets](../../python/corpus-structure/src/corpus_structure/semantic/selected_contribution_input.py#L67) ·
[Native attribution owner](../plans/set-based-execution/owner-resolved-reads.md#sbx-native-read-attribution)

<a id="I02"></a>
## I02 — Finish the structural migrations against the shared typed reader

**Proposed sequencing change · SBX-11–13.** Bring forward SBX-12's five-operation typed relation
interface as the point of integration for protected structural admission, source journeys,
selected math and contextual witness acquisition. Today the contribution scope implements live and
detached paths separately, and custody-sensitive consumers can still require the complete
support index. Define the needed custody projections once, including exact historical producer
and current use, protected issuer standing and the evidence a scoped reader can disclose.
Put shared structural interpretation above two backings, bounded current PostgreSQL reads and
authenticated detached relations. Keep purpose-built native answers for online-only consumers.
[Live and detached branches](../../python/corpus-structure/src/corpus_structure/semantic/selected_contribution_input.py#L117) ·
[Protected structural reader](../../python/corpus-structure/src/corpus_structure/serve/selected_structural_admission.py#L18) ·
[Accepted replay interface](../plans/set-based-execution/owner-resolved-reads.md#sbx-12)

Build the first thin vertical slice around a protected issuer with selectable ordinary report
support. Then use the same typed facts for restricted evaluator inputs in SBX-13. Cash in
existing native binding evidence before removing the duplicate preflight and keep cheap
deterministic input refusals before expensive evaluation when the native acquisition can
establish them once. Completion still owns mutable effect-time checks, while independent
authored-coordinate and restricted-role controls retain their separate purpose. Use exact joins
and anti-joins over already disclosed relations where they simplify projection. Keep captured
detached standing distinct from live authority. Verify the same structural interpretation and
intentional disclosure outcomes in both backings, including the textbook body journey and two uses
of the same historical producer. DP-01, DP-06, DP-09, DP-18, H18.
[Read and replay decision](../adr/0147-sbx-owner-resolved-reads.md) ·
[Evaluation preflight owner](../plans/set-based-execution/owner-resolved-reads.md#sbx-13)

<a id="I03"></a>
## I03 — Let Parquet pruning pay on a verified reread

**Proposed refinement · SBX-12.** Typed population Parquet already supports direct item lookup.
However every archive open hashes all files and population open reruns global duplicate, orphan
and count checks. The planned answer cache sits after that work. Reuse the existing file-custody
owner in one bounded acquired archive session. Bind verification to the trusted manifest, exact
file set and stable acquired identities, relation schemas, and verification implementation.
Cold verification still checks all required bytes and semantics. Within verified custody, retain
the completed cross-file verification and release preparation, then run only the requested
projection. Reacquire under changed or uncertain file identity and check identity through the
actual consumption window. Filename, modification time alone and an earlier receipt are
insufficient. This reuse is separate from current native authority.
[Current archive open](../../python/corpus-structure/src/corpus_structure/serve/demand_export.py#L486) ·
[Global relation checks](../../python/corpus-structure/src/corpus_structure/semantic/selected_population_archive.py#L113) ·
[Existing verification custody](../../python/corpus-structure/src/corpus_structure/semantic/file_custody.py#L84)

Make exact product/collection/partition addresses usable as Parquet filter columns and choose
row-group layout from the mix of point and full reads. Use Arrow `dataset.Scanner` projections and
filters for single-relation reads, and DuckDB `from_parquet()` or `read_parquet()` for joins and
set checks. Use the repository analytical owner's `Relation.except_all()` or SQL `EXCEPT ALL`
for bag differences. Compare sorted row groups first. Test `write_page_index` with the pinned
DuckDB reader only if selective scans are still material. PyArrow's writer's `sorting_columns`
describes order and does not establish it, and its reader does not yet use page indexes for
filtering. Avoid building an extra side index unless the actual access shape warrants it.

Keep row order and commitments independent of compression and physical layout. Include cold
and warm reopen, mutated bytes in a column the query omits, incomplete publication, and full
replay with duplicate and protected rows. For export, the existing `pg_temp` selected-key
state cannot move to a second session through an exported snapshot. Use same-session typed
batch extraction for that route. Use the existing ADBC snapshot path only when the required
committed pin and granted projection are visible on the second session. This distinguishes
two implementation choices already grouped under typed transfer. DP-04, DP-09, DP-15, H19.
[Selected archive session state](../../python/corpus-structure/src/corpus_structure/semantic/selected_archive_native.py#L69) ·
[Arrow Scanner 26](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Scanner.html) ·
[Arrow Parquet writer and reader behavior](https://arrow.apache.org/docs/python/parquet/parquet.html) ·
[DuckDB Parquet pruning](https://duckdb.org/docs/data/parquet)

<a id="I04"></a>
## I04 — Make PDF certification relational where it checks relationships

**Proposed extension and identity correction · SBX-14–17.** The plan already chooses typed
certification, ordered frames and DuckDB stream/ordinal checks. Extend that replacement to the
remaining recognition report traversals that test relational facts. Project formula outcomes,
coverage scope, cell/table/page relationships and runtime bindings into typed relations.
Use grouped duplicate checks and anti-joins for missing outcomes and dangling pointers.
Retain parent and element ordinals through nested expansion, and have the captured policy
decide eligibility and empty-scope meaning. Keep checks that require a rebuilt nominal object
at that boundary. [Recognition validation](../../python/corpus-structure/src/corpus_structure/semantic/pdf_report_validation.py#L85) ·
[Existing typed certification target](../plans/set-based-execution/pdf-path.md#columnar-pdf-certification)

Keep large opaque stream bodies in acquired IPC buffers. Use DuckDB for compact stream
coordinates, descriptors, ordinal checks and canonical frame ordering, and feed ordered part
bytes into the existing fold. `pa.memory_map`, `ipc.open_file`, `get_batch` and
`IpcReadOptions(included_fields=...)` belong at the authenticated capture boundary. This
extends the planned SQLite and hex bridge retirement without sending every large binary part
through a join or sort. For projected page inventory, try an Acero
`RecordBatchReaderSourceNodeOptions` → filter → project → `Declaration.to_reader()` only where
composing the existing kernels removes a pass across admitted batches. A simple projected
reader remains the baseline. Validate source field availability at the IPC projection, bounded
buffer/reader cleanup on early exit, and exact correspondence and canonical roots on a recovered
shared stream. Acero's streaming surface is experimental, and joins, grouping and ordering
can retain substantial state. [Current certification conversion](../../python/corpus-structure/src/corpus_structure/semantic/pdf_certification.py#L142) ·
[PyArrow 26 Acero](../libraries/analytical_infrastructure/pyarrow.md#42-acero-the-native-streaming-execution-engine)

Before changing captured module lists, correct the revision C assumption that the generic PDF
lowering and Standard capture move together. SBX-09 split those determinants. Compare a
transformed-publication change with a genuinely shared schema/codec change, and keep the approved
policy-remap and recovered-page journeys in the affected scope. This makes the full typed PDF
path compatible with the capture reuse already earned. DP-04, DP-07, DP-10, DP-20.
[Existing revision C assumption](../plans/set-based-execution/pdf-path.md#sbx-16) ·
[Implemented PDF custody split](../adr/0155-pdf-producer-custody.md)

<a id="I05"></a>
## I05 — Carry the analytical stream through durable output

**Proposed investigation · SBX-18 and its producer/publication consumers.** A populated
canonicalization route consumes a DuckDB Arrow reader, retains the emitted batches in an Arrow
table, then accumulates a complete IPC buffer and explicitly copies it to Python bytes.
`Table.from_batches` can share buffers. The issue is overlapping whole-result lifetimes and
the explicit bytes copy. Compare the bounded current path with folding commitments while
sending the same ordered batch stream to the existing owned sealed IPC mechanism. Finalize the
manifest after writer close and transfer the verified carrier to the existing transactional
COPY consumer. A compact table remains appropriate where actual partitions are small or the
consumer genuinely repeats scans. [Canonical output](../../python/corpus-structure/src/corpus_structure/semantic/population_canonical.py#L225) ·
[IPC buffering](../../python/corpus-structure/src/corpus_structure/semantic/population_transfer.py#L81)

Use the actual durable-draft and worker custody as the feasibility check. If IPC-backed
custody cannot carry an incomplete write, refusal or recovery safely, keep the current bounded
contract for that route. Test byte-identical commitments and success, partial reader, failed seal,
lost acknowledgement, and cancellation cleanup. Coordinate resource allocation across DuckDB
threads and spill, Arrow read-ahead, mapped files, Python objects and concurrent worker jobs
under the existing owner. An incremental result alone does not bound the producer, engine and
outgoing payload together. A focused working-set comparison is warranted only if it changes
the carrier or concurrency choice. DP-19, DP-20, H17, H24.
[Analytical job contract](../plans/set-based-execution/kernel-trial.md#sbx-18) ·
[DuckDB spill and workload tuning](https://duckdb.org/docs/current/guides/performance/how_to_tune_workloads)

<a id="I06"></a>
## I06 — Rebase the scoped-relations trial and narrow its comparisons

**Proposed trial amendment · SBX-18/19.** Compare with the current typed inputs and SBX-10
retained indexes, including the remaining predicate and contribution construction in
`scoped_products.py`. The useful question is which Python per-item questions and reshaping
remain across the complete route after that preparation. Begin with one Arrow inventory keyed
by scope, original occurrence and ordinal. Compare a DuckDB plan for range membership,
partitioned ranking and the batched formal/participant joins against the current acquired
route through exact artifact nomination. Carry tie-breakers and original order in the
relation. Try `ASOF JOIN` only for true directional predecessor/successor semantics and
ordinary range joins plus a partitioned ordered window where overlapping candidates or
multiple valid matches matter. Leave language/model decisions in the existing Python seam.
Avoid a full second and third rewrite. Compare captured SQL, typed expressions or native
PostgreSQL placement on the specific subgraph where they could change the choice.
[Installed-input seam](../../python/corpus-structure/src/corpus_structure/semantic/scoped_products.py#L175) ·
[Trial criteria](../plans/set-based-execution/kernel-trial.md#sbx-19) ·
[Pinned DuckDB reference](../libraries/analytical_infrastructure/duckdb_2.md#6-advanced-sql-and-relational-expressiveness)

Rank adoption by the removed preparation and crossings across the actual chain, including
publication and selected readback. Exact output, two producers with the same local position,
zero-width and overlapping spans, Unicode, optional states and duplicate occurrences must
survive. Keep ordered canonical identity at its owner and use exact lexical fields for
unsupported native scalar widths. Adopt one route or retain the current implementation if the
whole candidate still rebuilds both inventories. FP-07, DP-07, DP-11, DP-15.

<a id="I07"></a>
## I07 — Resolve deployment invalidation from the real chain

**Proposed sequencing and decision · SBX-20–22.** Refresh the A/B/C effect account around the
installed development root and two read successors, and discover the actual stage predecessor
before authoring that install. The existing plan already calls for direct/shared attribution.
An SBX-11 retry was refused because its prepared release expected a different native kernel
while the reader fix was being installed. That is a reason to execute the comparison now,
and does not identify which dependency necessarily caused it. Compare a read implementation
change, a wire shape change, and a material producer change against their exact predecessor.
Distinguish release preparation, receipt currency, installed descriptor and material producer
identity. If a narrower checked identity can preserve the complete executable dependency and
privilege correspondence, propose it before stage. Keep the full installation descriptor.
[Recorded kernel refusal](../plans/set-based-execution/owner-resolved-reads.md#sbx-11) ·
[Revision and attribution owner](../plans/set-based-execution/cutover-and-qualification.md#native-revisions)

Let scoped-relations and PDF work proceed in parallel once their shared carrier contract is
settled. Tie retirement to the last migrated consumer in each package, with the SBX-21 sweep
checking residual references once. Reuse captured authentic artifacts for checks whose
determining inputs remain applicable. Prepare fresh producer evidence when those determinants
or admission change. Keep the final whole-book interruption and unchanged-repeat journey on
the assembled stage chain. These are scope and source-applicability decisions under existing
result custody. DP-04, DP-22, DP-23, H24.
[Stage, retirement and assembled qualification](../plans/set-based-execution/cutover-and-qualification.md#sbx-20)

## Integration priority

Bring [I01](#I01) and [I02](#I02) into the remaining structural work together. They define the
smallest native acquisitions and the shared consumer contract that should own them. Use
[I03](#I03) when shipping the first complete typed structural archive. Correct the PDF identity
account in [I04](#I04) before the next producer capture changes. Apply [I05](#I05) only at
the durable output seam and [I06](#I06) to the actual scoped route. Start the bounded comparison
in [I07](#I07) early enough to inform stage. There is no concrete workload in this footprint
requiring a broader DuckDB server, remote/federated authorization, an additional analytical
store, Flight, or a new persistent dossier. The current typed carriers and two existing
execution owners are sufficient for the proposed improvements.
