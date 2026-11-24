# The PDF path

**Status:** Complete for development. Companion of [Set-based execution](../set-based-execution_2026-11-21.md).
**Created:** 2026-11-21.

This companion owns the PDF path from an original to published records. It owns SBX-14 to SBX-17
and is carried by native revision C. It consumes the shared typed carrier and analytical
execution contracts. Directly used custody and column checks may land through SBX-08/09. Source facts are
**Inspected** at `7a415d18d`; counts of repeated work are counts of call sites.

**Preserved contracts.** The per-row identity fold mirrored in PostgreSQL links Python's
validation to the stored rows. Page payloads preserve absent versus null and integer versus
float. Recognition observations remain products. Spool custody spans attempts. Docling
validates the derived document before lowering. SBX-16 owns the conditional comparison of
physical IPC layouts.

## Baseline

**Two rebuild routines.** `reconstruct_native_document` (`cs/semantic/pdf_records.py`) is what
the round-trip validation proves; it checks schema paths, ordinals, counts, duplicate keys,
extension overlap and containment cycles. Every transform builds its whole-document input from
the event stream instead (`hydrate_document` in `cs/semantic/pdf_record_reader.py`), which makes
none of those checks and whose recursive query has no cycle guard. Against the database,
`reconstruct` costs a round trip per record, which is why it is not used for whole documents;
the validation child already feeds it from rows held in memory.

**Access rows.** Three Python derivations and one SQL checker. `write_pdf_access_projection`
builds items and regions from the document; certification's Python validators read them; they
are staged from a file as JSON lines; `pdf_check_access_correspondence`
(`cs/semantic/pdf_record_access_native.py`) reconciles every column and the JSON copy with the
rows. The checker already derives section owner and ordinal recursively and compares label,
layer, parent, text and regions. The region table is read only by pointer and index. The JSON
copy has many readers and cannot be derived without a row-to-JSON serializer and a number
spelling contract.

**The draft path.** One enrich operation performs six full Docling validations, two across a
process boundary, and at least eight whole-document serialize and parse passes. The in-process
hand-offs go through bytes with a digest (`NativeSnapshot`, `PreparedPdfProduct.payload`), which
is what forces most of them.

**Payloads and files.** A candidate page payload is decoded and validated about eight times in
an enrich operation; a record replay file is hashed six times on the stream path, twice back to
back at adoption.

**The build identifier.** `product_id`, `revision_id` and `release_id` are columns of every
replay row although identity excludes them. Recovery therefore rewrites every file
(`rebind_pdf_recovery_reply`) and re-folds every row. The scratch-table authorization refuses
column defaults.

**Certification store.** `native_entry` is a pass-through of every row as JSON; `identity_frame`
is a disk sort of frames; part bodies make a hex round trip; validators read companions, fields
and parts by key and use a primary key as the duplicate-page refusal.

**Validation capture.** Rows read from PostgreSQL as JSON are re-encoded into an Arrow file of a
family name and a JSON string, then parsed again in the child. The capture contract omits the
captured lowering, so the child validates with the repository's current schema and callback
policy where the producer used the captured ones.

**Identity coupling.** The lowering identity hashes named modules and callables
(`cs/semantic/pdf_lowering.py`), and the standard producer contract hashes a module list
(`cs/ingest/pdf_producer_contract.py`). Renaming or retiring any of them changes those
identities.

<a id="pdf-producer-custody"></a>
### Producer custody through SBX-09

**Accepted · 2026-11-23.** Bring Standard capture custody and independently acquired
recognition forward for the Integrated route. The release archives the capture-specific
lowering beside the generic transformed-publication lowering and shares their schemas
and codecs. Capture and recognition use the determining inputs and acquired execution
of their own operation. PostgreSQL selects a publication certificate's lowering from
the producing operation and retains its exact historical basis.

**Tested · 2026-11-23.** The refreshed root passed the policy remap with the existing
capture and observation episodes. It also passed the later generation with retained page
results, exact historical custody, and refusal of the withdrawn public use.
[ADR-0155](../../adr/0155-pdf-producer-custody.md) ·
[SBX-09 readiness](cutover-and-qualification.md#sbx-columnar-implementation)

## Target

**One rebuild.** `reconstruct_native_document` is the only assembler of a document from rows.
Transforms, whole-document reads and the validation child use it under the producing schema
and callback policy. The reader supplies records, memberships and stream descriptors in
ordered keyset pages. The same ordered rows can feed a streaming export writer. Per-item and
subtree reads use the [sparse access relations](#sbx-pdf-sparse-access) to limit acquisition to
the selected scope and retain the selected-source subtree event representation.

**Access columns derived where the rows are.** At prepare, PostgreSQL derives the relational
columns (pointer, parent, ordinal, label, layer, section owner, text, regions) from the staged
JSON copy, whose numbers are already in the store's numeric form. The JSON copy stays staged and
reconciled with the rows, since it has readers and no second serializer should be written. The
checker keeps its JSON-against-rows section and loses its column comparisons and its ordinal,
section and region sections, because those columns are no longer supplied. Certification's
Python validators keep a pure function from document to items for their own use; its output is
no longer staged. The region table becomes a view over the access rows.

*Stated cost.* Two derivations of the item list remain, one in SQL that is stored and served and
one in Python that validators consume before staging. Removing the second means moving
certification after staging, which this series does not do.

**Acquired input, private draft and sealed result.** A transform receives an acquired source,
hydrates once and mutates a private draft. It exports and validates once under the captured
schema and callback policy, then seals the result before lowering, certification, digesting or
access projection can reuse it. The sealed interface prevents a mutable alias from changing those
inputs. Derived byte views belong to that sealed revision and follow its owner's lifetime, using
the [carrier retention contract](validated-values-and-handoff.md#target). Bytes and a digest cross
the worker pipe and validation child. Captured policy and independent digest checks remain at
those boundaries and adoption retains file-custody checks.

**Verified carriers.** Full page admission yields a carrier binding exact encoded bytes,
schema, page number, receipt and verified logical digest. Status, geometry, draft, companion
encoding and certification consume that admission within its owned lifetime. Sparse consumers
can decode only their columns from authenticated admitted bytes. Consumers needing the same
complete batch share one bounded decoded value. A replay file verified at acknowledgement yields
a handle, which is verified again at copy into PostgreSQL and after a custody gap.

**Common analytics amendment · Scheduled · 2026-11-22.** SBX-12's frozen selected-review
archive is the first persisted Parquet boundary. PDF page IPC retains its acknowledgement,
verified replay handle and recovery locator responsibilities under SBX-14–17. Reconsider Parquet
for PDF transport only when a named retained consumer can remove repeated work across the full
write, recovery and read route. Any selected replacement must preserve acknowledgement custody,
restart and digest behavior, with a genuinely recovered spool in acceptance. Immediate reuse uses
in-memory batches and the existing spill owner handles transient pressure. SBX-17 settles its
external sort below through the shared DuckDB owner.
[Review I04](../../plan_improvement_reviews/set-based-execution-common-analytics_2026-11-22.md#I04) ·
[Selected structural replay owner](owner-resolved-reads.md#sbx-12) ·
[PDF streaming custody](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_streaming.py#L71)

**The build identifier is supplied at load.** Replay rows carry no build columns. The adopt
program fills them from its argument. Files become independent of the build, recovery stops
rewriting them, and recertification checks the original files' digests.

**Certification reads the files.** Two passes over the memory-mapped IPC batches. The first
collects compact descriptors and part coordinates, checks stream identity and part order, and
folds the original part bodies per stream from their acquired IPC buffers. The second builds
each record's frame from the row and descriptors, sorts frames externally and folds them in
order. Companions and their fields are keyed for validators. Explicit set and ordinal checks
preserve the duplicate refusals previously supplied by the certification store.

The [pinned PyArrow 26.0.0](../../../python/corpus-structure/pyproject.toml#L23) route uses
`memory_map`, `ipc.open_file` and
`RecordBatchFileReader.get_batch` to read typed batches without first building a whole-file Python
table. The map and batch buffers remain owned until their readers finish. The frame sort still
needs an external-memory route. See [Arrow IPC](../../libraries/analytical_infrastructure/pyarrow.md#71-arrow-ipc-native-columnar-interchange).

**Typed capture under the captured policy.** The validation capture is one typed table per
family using the stage and companion schemas, and its contract includes the captured lowering.
The child rebuilds and validates with the producer's mapping and callback policy. Membership
closure (ordinals dense per parent and field; count equals declared length; map keys unique) is
checked over the typed rows before the rebuild.

<a id="columnar-pdf-certification"></a>
## Typed certification and document adoption

**Proposed · 2026-11-22.** Combine
[columnar I07](../../plan_improvement_reviews/set-based-execution-columnar-basis_2026-11-22.md#I07)
and [redesign I05](../../plan_improvement_reviews/set-based-execution-efficiency-and-analytical-redesign_2026-11-22.md#I05)
under SBX-14–17. The [shared analytical target](common-analytical-basis.md#columnar-population-target)
provides Arrow schemas and ownership and one configured DuckDB owner. Certification consumes
existing authenticated IPC through `pa.memory_map`, `pa.ipc.open_file` and owned batches. Use
DuckDB over compact typed stream coordinates for descriptor/part joins, grouped duplicate and
ordinal checks, binary-collated frame ordering and typed validation capture. Pass opaque part
bodies from the live IPC buffers to the ordered fold. Preserve the canonical per-record
frame and exact value conversion at that boundary.
Replace the certifier's SQLite JSON row store, per-row JSON round trips and artifact bytes-to-hex
bridge together with their consumers. Share keyed typed companion relations and the
[publication access shapes](#sbx-pdf-sparse-access) with the validators. Project recognition
outcomes, coverage scope, cell/table/page relationships and runtime bindings, retaining parent
and element ordinals through nested expansion. Use grouped counts for duplicates and anti-joins
for missing outcomes and dangling pointers. Captured policy decides eligibility and empty
scope meaning. Checks that require a rebuilt nominal object remain at the rebuild boundary.
[Review I04](../../plan_improvement_reviews/set-based-execution-after-sbx09_2026-11-23.md#I04)

Choose model-derived expressions for logical row values and canonical frames under the captured
lowering policy. Establish parity for the full normalization contract, including absent fields,
explicit null, numeric spelling and non-ASCII keys. The generic canonical reference supplies
independent expected values. Fold rows by column where compatible, and retain the final ordered
fold where the protocol requires it. This changes the implementation of the calculation while
preserving its defined result. Keep full independent encode/decode expectations and deliberate
invalid fixtures.

Stage a document's batches and access rows by the existing transaction-owned Arrow COPY route.
Reassess commit scope over the whole document, acknowledgement and restart obligations together.
Use one document adoption transaction when the complete input is available. Any retained partial
recognition acknowledgements remain explicit recovery boundaries. Derived access rows follow
SBX-15's PostgreSQL owner. Acquired input handles keep their maps and buffer owners alive through
consumption, success, refusal or cancellation. A verified immutable handle may replace repeated
whole-file checks only within its established custody lifetime. Recovery or an external transfer
reacquires the exact bytes and their admission premises.

The complete certification/store replacement stays with SBX-16/17. SBX-08/09 may consume a
columnar build-id comparison and distinct stream-id selection before the fresh native probe, or
an owned verified handle, when that retires work in an actual current path. Its completion then
covers that consumer and relevant tamper and cleanup controls. Population qualification consumes the directly affected early PDF slices, while SBX-16/17
retain the complete certification replacement.

**Completion evidence.** Independently assert the exact logical and stream roots, ordered frames,
shared and unreferenced streams, empty inputs, duplicate page/record/part refusal, captured-policy
changes, post-encoding tamper detection and genuine interrupted/recovered adoption. Verify file,
reader, connection and spill cleanup on early exit. Replace the mechanism-specific SQLite and
hex controls with the equivalent behavioral assertions on the typed route.

**Early omission slice · Tested by selected identity · 2026-11-22.** The current shared-stream
adoption path checks build columns and selects distinct part stream IDs in Arrow. It still
submits the selected descriptors to a fresh native probe. The six transport-omission controls
passed with `uv run ci test --workers 1 -- python/corpus-structure/tests/semantic/test_pdf_shared_streams.py -k transport_omission`
(`01094d17f290448a82a25907a18510a2`). The certifier and adopted-root replay retain their scope above.

<a id="sbx-14"></a>
## SBX-14 — One rebuild, under the captured policy

**Owns.** The paged row reader for `reconstruct`; migration of transforms and whole-document
reads to it; the capture contract's lowering; the child's use of it.

**Removes.** `hydrate_document` and whole-document use of the event stream. SBX-15 owns the
replacement of the repeated size and payload evaluations for protected reads.

**Failure behaviour.** A published row set with a containment cycle, a wrong ordinal or a count
mismatch refuses a transform's input, where today it would be accepted or would not terminate.

**Evidence.** On the existing fixtures, the document a transform receives equals the document the
validation child reconstructs, compared as canonical bytes. A row set with a membership cycle is
refused by a transform. A forced re-validation of a publication made under an earlier schema and
callback policy passes under its captured policy and would fail under the current defaults; the
fixture is built with a policy that differs.

<a id="sbx-15"></a>
## SBX-15 — Access columns derived at publication

**Owns.** The derivation program, sparse read projections, the reduced checker, compact region
addresses and their geometry view, staging of the JSON copy alone, and the pure
document-to-items function for validators.

**Removes.** Column staging and its row equality, the checker's column, ordinal, section and
region sections, and the separately stored region geometry.

**Evidence.** For the fixtures, derived columns equal the columns published today, row for row.
A staged JSON copy that disagrees with the rows is refused as now. Region reads by pointer and
index return today's values through the view.

<a id="sbx-pdf-sparse-access"></a>
### Sparse access and certification relations

**Scheduled · 2026-11-23.** Derive pointer, ancestry, page, original diagnostic order and
report membership at publication under the existing access owner. Key the relation by exact
publication and report occurrence. Batch authorized pointer and ancestry lookups and hydrate
opaque bodies only for the selected diagnostics. Share the relationship shapes with SBX-17
certification. Before staging, the pure document-to-items function supplies the same meaning
to the validators. Retire family-wide report scans and redundant reader caches as their consumers
move.

Use one invocation-owned selected source and bounded acquired projections for item, region,
formula and contextual diagnostics. Supply selected math through the
[shared acquired reader](owner-resolved-reads.md#sbx-acquired-reader) with the exact proof,
formula and original source use. Batch catalog headers at the selected cut, preserving each
native publication receipt check, continuation and disclosure semantics. Visual evidence uses
the same sparse address contract and retains submitted-page, coordinate and mapping-availability
checks.

**Catalog slice implemented with SBX-11 · 2026-11-23.** The selected publication catalog
uses bounded ordered receipt and header batches. Each publication retains its exact selected
use, product, release and physical revision checks. The scoped source-catalog cases passed
within `86fb6e86e1224ec6b2d635904b511199`, including multiple publications, ambiguous
headers and a foreign cut. Sparse item, region and certification access remain in SBX-15.
The private cross-work artifact fixture (`a4b3fe95e36b4ef9b05540443a625b5e`) also verified
header, health and release parity with the installed guarded scalar path.
[SBX-11 checkpoint](owner-resolved-reads.md#sbx-qualified-reads-checkpoint)

Use one bounded native evaluation for row delivery and exact size refusal before transfer.
Consider an admitted address window with stored lengths only when those lengths refer to the
same authorized snapshot and returned representation and would avoid material work. Qualify a
selected formula and ancestors amid unrelated diagnostics, multiple reports sharing a local
position, protected refusal, an oversized selected value and a fully ordered document rebuild.
Verify that the selected statement runs once, that an oversized response refuses before body
transfer and that sparse reads skip unrelated report bodies. Compare catalog and visual
results against independent expectations.
[Review I11](../../plan_improvement_reviews/set-based-execution-after-sbx09-deep-review_2026-11-23.md#I11)

<a id="sbx-16"></a>
## SBX-16 — One document, verified carriers, build identifier at load

**Projected candidate replay · Scheduled · 2026-11-22.** Status and geometry use distinct
projections. Carry the exact byte-to-logical admission in the page carrier, then reuse
`PreparedPayloadFamily.read_batch(payload, schema_digest=..., columns=...)` for sparse reads.
Its PyArrow 26.0.0 implementation uses `pa.BufferReader`, `pa.ipc.open_stream` and
`pa.ipc.IpcReadOptions(included_fields=top_level_indices, use_threads=False)`, compares the full
schema header and calls `RecordBatch.validate(full=True)`. Include `page_no` in the physical
projection to verify the released binding, then return requested fields in caller order. Empty
`included_fields` means all fields at the Arrow API, so retain the codec's explicit projection
validation. Page payloads use the IPC stream format. Certification files below use IPC file readers.
[Production codec](../../../python/corpus-structure/src/corpus_structure/semantic/pdf_payloads.py#L317) ·
[Candidate replay](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_candidate_source.py#L45) ·
[IPC read options](https://arrow.apache.org/docs/python/generated/pyarrow.ipc.IpcReadOptions.html)

Authenticate the exact received bytes after custody gaps. If prior logical admission cannot be
established, fully admit the recovered payload before sparse use. The codec refuses `columns`
together with whole-page `logical_digest` recomputation. A projected result cannot establish
omitted-column identity, as the retained payload probe demonstrates. When status and geometry
can share one bounded admitted batch, use `RecordBatch.select()` on that owned value instead.
Keep owner lifetime through all buffer consumers and release derived state with its carrier.
Keyed region rendering and one-observation visual mapping consume the
[sparse access contract](#sbx-pdf-sparse-access).
[Post-pilot I05](../../plan_improvement_reviews/set-based-execution-through-sbx09_2026-11-22.md#I05) ·
[Projected custody probe](../../design_review/evidence/2026-11-22_sbx09-review/README.md)

**Projected replay acceptance.** Compare status, geometry and complete-page expectations on
null and absent fields, nested values, page numbers, ordinals and requested field order. Change
an omitted field while retaining the projected values, alter bytes after admission, and recover
a real spool. Verify refusal or fresh full admission at the relevant custody boundary. Assert
that sparse reads request only the intended columns and that shared complete-batch consumers
reuse one decode. Preserve schema, page, logical and receipt bindings through adoption and
certification, including cancellation and owner close.

**Owns.** The in-process document interface across `pdf_transforms`, `pdf_methods`,
`pdf_hierarchy`, enrichment and the publication draft; the page and file carriers and the
signatures that accept them; replay schemas without build columns; the adopt program and scratch
authorization; recovery without rebind. The document interface seals the validated result and
owns cached byte views through lowering, certification and access projection, integrating
[I07](../../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I07).

**Identity.** Attribute each lowering and module change to the producer that consumes it.
Standard capture, recognition and transformed publication retain their own determining
inputs and executable custody. Shared record schemas and codecs affect every producer that
consumes them. Historical replay uses the exact archived lowering committed by the publication
receipt. In the revision C comparison, separate a transformed-publication change from a
genuinely shared schema or codec change. Qualify a policy-only remap that reuses eligible
capture and recognition, and a recovered-page journey verifying the original admitted bytes
and the producing lowering.
[ADR-0155](../../adr/0155-pdf-producer-custody.md) ·
[Native revisions](cutover-and-qualification.md#native-revisions)

**Failure behaviour.** A file whose bytes changed between acknowledgement and adoption is refused
at adoption. Mutation through a former draft alias cannot change the sealed lowering input. The
validation child independently checks its digest and captured policy, as now.

**Evidence.** An enrich operation on a fixture performs two Docling validations in the parent
path and one in each child, asserted by counting, and publishes records whose logical digest
equals today's. Whole-page logical admission is reused for its bound bytes and schema. Sparse
consumers project columns or share a bounded decoded batch under the carrier owner. A recovered
spool is adopted under a new build without any file being rewritten, and its recertification compares recorded file
digests. A mutation attempt through a retained draft alias leaves the sealed lowering input
unchanged. Releasing the sealed owner releases its derived views. Parent and child use the same
captured policy, including after recovery.

<a id="sbx-pdf-payload-layout"></a>
### Page payload layout and projected execution

**Conditional investigations · 2026-11-23.** The selected pinned codec can skip decoding
columns, while the published reader still concatenates the entire stream before decoding and
the recovery reader acquires whole-file bytes. Use a real recovered page with a small candidate
inventory and large OCR parts. Compare the bounded stream baseline against an IPC file backed
by a verified native owner or a page manifest binding independently sealed candidate and OCR
streams. The file candidate uses `pa.memory_map`, `pa.ipc.open_file`,
`RecordBatchFileReader.get_batch()` and `IpcReadOptions(included_fields=...)` under the same
verified custody. Select another layout only if a named consumer avoids material transfer or
live bytes through the full capture, publication and recovery path. Preserve one page receipt
and acknowledgement, whole-page logical admission, exact schema and page correspondence,
validity evidence and ordered replay. Verify the full result and seal independently of the
sparse projection, including a change to omitted bytes and a genuine restart. Keep the
existing bounded page stream if the requirement or savings cannot be established.
[Published payload reader](../../../python/corpus-structure/src/corpus_structure/semantic/pdf_record_reader.py#L980) ·
[Recovered payload reader](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_candidate_source.py#L45) ·
[Arrow IPC](../../libraries/analytical_infrastructure/pyarrow.md#71-arrow-ipc-native-columnar-interchange)

Keep the simple projected reader and current Arrow nested kernels as the execution baseline.
Independently of layout, consider a PyArrow 26.0.0 Acero plan using
`RecordBatchReaderSourceNodeOptions`, filter and project nodes, and
`Declaration.to_reader()` if it removes a pass over admitted batches. Ensure the source
projection carries all fields used by the plan. The retained threaded probe read ahead beyond
immediate demand. Adopt fusion only with equivalent projected and full results, bounded retained
buffers and reader release on early close and cancellation. Keep joins, grouping and order
checks over compact coordinates under the shared analytical owner.
[Acero reader and operators](../../libraries/analytical_infrastructure/pyarrow.md#42-acero-the-native-streaming-execution-engine) ·
[Retained streaming evidence](../../design_review/evidence/2026-11-22_sbx-columnar-basis/README.md) ·
[Review I12](../../plan_improvement_reviews/set-based-execution-after-sbx09-deep-review_2026-11-23.md#I12)

<a id="sbx-through-16-checkpoint"></a>
### SBX-14–16 implementation checkpoint

**Implemented · 2026-11-23.** Transforms, full exports and the validation child use
ordered native record, membership and stream relations. The child checks the lowering
captured by the producer. A transformation acquires bounded immutable rows and artifact
streams, releases its database connection, then assembles the owned document. The selected
transform hands off acquired values directly, and Integration validates those values under
the producer's captured policy. PostgreSQL derives sparse access and report-occurrence
relationships from admitted rows and their staged JSON. Admitted compact report pointers
keep opaque diagnostic bytes out of JSONB indexing. Region reads use the derived
view. Budget evaluation and delivery share a bounded native selection, with exact scalar
payload limits checked before transfer. The legacy whole-document event entry point is
retired. Explicit fragment traversal keeps its own semantic purpose.

**Implemented · 2026-11-23.** Retained replay files carry logical rows. Scoped loaders
supply physical build, revision and release bindings. Adoption authenticates the
original retained bytes, then stages the recovered document in one transaction with
claim renewal coordinated by the claim owner. Old replay shapes can supply a verified
projection at load. Adoption preserves the original files byte for byte. Candidate status and geometry read
from an admitted page batch or its projected stream. The document draft seals an
owned result. Lowering and certification reuse the parent's validation when the exact
emitted value and captured callback policy match. A changed representation receives fresh
validation. The validation child independently reconstructs and validates its own input.

**Tested by selected identity · 2026-11-23.** The repaired private cohort
`f0e6aace46384292927754feea14c920` passed native transformation with a controlled
provider and a same-spool different-build case. The latter refused a late tamper, left
no partial receipt and adopted unchanged retained files after retry.

**Tested and measured on the recovered fixture · 2026-11-23.** The genuine Docling GPU
recovery passed (`4a13e399a673476da3237a5bef75e27f`) on physical pages 120–122.
It recomputed only the missing pages and compared native record output from the same
completed spool. The recovered candidate page produced identical projected status and
geometry for the two IPC layouts. Complete authenticated acquisition was 27,488 bytes
for the existing stream and 33,522 bytes for an IPC file. Retain the stream on this
evidence. A larger OCR-heavy case or an Acero operator chain remains conditional on
removing material transfer or a full pass while preserving custody and release.

**Tested by selected identity · 2026-11-23.** The installed policy-remap and historical
basis journeys passed (`42a62898af344299b27d3faa75dcf7fd`). They exercised genuine
Standard capture, the installed recognition worker with a finite service, policy-only
reuse of the observations, and historical authorization across generation advance and
withdrawal. The provider-only selection of these two identities selected no cases
(`e3e1174896b54b6cad2902f8b0a5bc99`). The passing run used the ordinary native lane.

**Tested by selected identity · 2026-11-23.** The subsequent private native cohort
`248e71d8bba04aedb3f42f5c9fde4dab` passed forced revalidation from a real sealed
publication. The spawned child reconstructed the sealed digest under the captured contract.
Its deliberately incompatible ambient schema and callback defaults rejected the same
document independently. The installed sparse diagnostic case preserved exact NUL and
Unicode, selected two report kinds sharing a local ordinal, skipped unrelated bodies, and
refused malformed or forged compact pointer arrays.

The serial retry `753f19be5cb14ad1b2f7606badacc4ae` passed the installed derived access and
region parity check, native organization, enrichment, integration and exact resume, and
real native worker reuse. The managed cohort retains four enrichment-control failures
from instrumentation that outlived its native fixture. The affected isolated controls
passed `3b0ce36ecba246b7bc10f982af246931` after narrowing the instrumentation to the
seal methods.

The final native control cohort `1f6e6523ba374dc7bb9b41a39cc1778e` passed the
organization and enrichment publication-seal checks and the four enrichment controls
on the same worker. It also passed exact materialization bounds for a small source and
refusal of an oversized selected source before reading body rows.

**Implemented · 2026-11-24.** The publication draft owns the sealed typed document through
Organization, enrichment and lowering. The enrichment worker normalizes only new formula
provenance after computing with the original crop and returns only the candidate page changes.
The parent retains its original admission for unchanged candidate pages. Recovered or received
candidate IPC bytes must establish complete page admission before projected kernel reads. Both
projected and full readers verify the embedded physical page against the requested address.

The installed compact region table binds item pointer, physical page and original provenance
ordinal. Its view takes geometry from the admitted native record at that exact ordinal. Visual
inspection uses the same page-addressed rows for its bounded incumbent summary and joins.
The [registered successor](cutover-and-qualification.md#native-revisions) owns the physical
schema. The first focused run `0324d5091d7f4a5695489f262325905e` retained three
malformed-input fixture setup failures. The updated fixtures enter the finite reader before
asserting refusal of a cycle, missing ordinal or incompatible membership inventory.

**Tested by selected identity · 2026-11-24.** The recovered private serial cohort
`5bcb1a72804b4b289795d7ae519f8e19` passed the three malformed-input controls, native
Organization, enrichment and Integration, the captured-policy validation child, atomic
different-build adoption and byte-retaining recertification, and the native PDF policy-only
reuse and historical withdrawal controls. Two visual cases needed the controlled Standard
input to stay within fixture custody through the new visual demand. The genuine visual
canary uses retained incumbent page-151 records under that custody, the exact original PDF,
a real render, pinned Chandra inference, native mapping, and a selected read.

**Tested by selected identity · 2026-11-24.** Both genuine Docling recovery cases passed in
`1d39812b1acb4c4aaf67dcea6908edd1`, including the selected-file producer contract.
They restored page 121, computed pages 120 and 122, and reproduced the same spool records.
Projected status and geometry agreed. The recovered candidate measured 27,488 bytes for the
authenticated IPC stream and 33,522 bytes for the file layout. The first genuine Chandra run
produced two located four-by-four tables on page 151. Its installed readback fixture used an
operation-only cut and omitted selected visual evidence. The revised fixture selects the
capture by kind within the original-source cut and retains both operations in that cut.

**Tested by selected identity · 2026-11-24.** Provider retry
`3faacfd6a4a84e4ca52548d756a82858` passed the Grinstead–Snell page 151 render,
pinned Chandra inference, mapping, and exact installed readback. The controlled incumbent
contributed one table, two captions and four formulas. The selected Chandra artifact
contributed two located four-by-four tables with recognition-candidate standing and
exact raw producer attribution.

The ordinary native visual failure case passed in `eb886689fe7c4f2abe2f16f50f31526a`,
including exact retained attempt attribution and CLI delivery. The combined formula
and visual case passed in `6d8f467315b04b86b4432914b1005367`, through the same source
cut, physical page, pointer, provenance ordinal, and canonical coordinate representation.

<a id="sbx-17"></a>
## SBX-17 — Certification and validation without round trips

**Owns.** The two-pass certifier; the keyed companion store for validators; typed capture and the
child's reads; closure checks before the rebuild; conversion of logical rows by column in the
companion export with the existing encoder.

Consume SBX-15's access relation shapes and SBX-16's admitted page and replay carriers in the
certifier and child. Retain complete logical validation where the whole payload first enters
the domain or its premises change.
Use `pa.memory_map`, `pa.ipc.open_file` and `RecordBatchFileReader.get_batch()` for typed
certification files, holding maps and batches until the readers finish. The existing page
stream decoder is the default pending the [layout decision](#sbx-pdf-payload-layout). Preserve
ordinal and duplicate expectations independently of the typed reader. [Arrow file reader](https://arrow.apache.org/docs/python/generated/pyarrow.ipc.open_file.html)

**Selected plan target · Proposed · 2026-11-22.** Use the shared DuckDB analytical owner for
external frame ordering and grouped/join checks over typed IPC. Its invocation owns spill,
registered inputs and output readers. Implement the [complete certification replacement](#columnar-pdf-certification)
and retire the SQLite certifier store with its consumers. Preserve binary order, duplicate
refusal and the canonical fold, and validate failure cleanup through the real worker path.

**Fidelity conditions.** The inputs to the folds pass through normalizations that are part of
each digest's effective definition: nulls dropped after a JSON round trip, key-presence tests,
and companion bodies parsed to float before decimal. The acceptance corpus includes
exponent-spelled floats, null against absent columns and non-ASCII keys.

**Evidence.** Retained certifications and a real recovery reproduce their recorded logical and
stream-inventory digests on that corpus. Independent fixtures cover duplicate record, part
ordinal and page refusal, missing formula outcomes, dangling report pointers, policy-defined
empty scope, and distinct report occurrences sharing a local position. Verify the ordered
part fold with shared and unreferenced streams and exercise cleanup on early exit. The
validation child reads typed rows directly. The companion export's logical-row digest is
unchanged on a mixed-type batch.

**Implementation checkpoint · 2026-11-24.** Capture, transformed publication, spool
recertification and the independent validation child consume keyed Arrow batches. The certifier
uses DuckDB for compact coordinate checks and binary frame ordering. Ordered folds consume the
existing canonical record frames and binary part buffers. The keyed store and per-family oracle
capture replace the PDF SQLite and JSON row stores. The protected PostgreSQL pages and both
companion export routes carry part bodies in a binary column on the
[development successor](cutover-and-qualification.md#native-revisions). Formula outcome,
coverage, cell-to-page and runtime relationships use typed groups and anti-joins. Report and
page validation share the acquired source index. Nominal and geometry checks use their
captured validators.

**Installed controls · 2026-11-24.** The private serial cohort
`65cbe14ee2724ed5ae5b162499599421` passed forced validation under the captured policy,
byte-retaining new-build adoption, exact selected metadata and overflow companion streaming
with cursor cleanup. Two Standard capture journeys reached a closed source-custody refusal.
The PDF worker now captures its analytical settings before spawn and retires standalone
scratch with the process. It sends a primitive allocation so Docling's generated dependencies
are acquired inside the existing Standard capture guard. The final-source policy and historical
authorization controls have their own installed selection.

**Passed · 2026-11-24.** `uv run ci test --workers 1` covered 125 selected PDF identities
after the report relationship and worker startup changes (`ee7cb6eb7f11408cae83d3ed31fb9734`).
This includes independent corruption checks and installed OCR writer cases.

**Genuine recovery and adoption · Passed · 2026-11-24.** `uv run ci test retry
13d1c48d7610472782bb4cd87efb22c8 --lane ordinary --json` passed
`7468deed9ce84945b12b9ec4a8c52ca5` on the private successor. Standard capture interrupted and
recovered Grinstead–Snell pages 120–122, recomputed the missing pages and reproduced the emitted
records on a warm spool. The adopter selected the Standard capture contract, reproduced the
logical and stream commitments, sealed a different native build and reopened all three pages.
The original provider attempt failed at the fixture's generic lowering basis. The retry changed
that fixture, and the provider coverage view accounts for all three originally selected identities.

**Development acceptance · Passed · 2026-11-24.** `uv run ci test --native-host private
--workers 1` on the final source passed forced validation with the captured schema and policy,
genuine Standard and recognition reuse after policy remap, and historical authorization after
generation advance and withdrawal (`8dd7a7bfd13241d9bba9a3fa92589a42`, selected PDF identities).
Together with genuine recovered adoption and the installed binary export controls, this closes
SBX-17 for development.
