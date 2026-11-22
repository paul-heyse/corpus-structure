# The PDF path

**Status:** Proposed. Companion of [Set-based execution](../set-based-execution_2026-11-21.md).
**Created:** 2026-11-21.

This companion owns the PDF path from an original to published records. It owns SBX-14 to SBX-17
and is carried by native revision C. It is independent of the other companions. Source facts are
**Inspected** at `7a415d18d`; counts of repeated work are counts of call sites.

**Kept as it is.** The per-row identity fold mirrored in PostgreSQL, which is the only link
between Python's validation and the stored rows; the page payload encoding, which preserves
absent against null and integer against float and which PostgreSQL cannot read; publication of
recognition observations as products; spool custody across attempts; Docling validation of a
derived document before lowering.

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

## Target

**One rebuild.** `reconstruct_native_document` is the only assembler of a document from rows. It
is fed by a reader over rows fetched in keyset pages (records, memberships, streams in bulk), the
shape the validation child already uses. Transforms, whole-document reads, per-item reads and the
validation child use it. Exports that stream to a file keep a streaming writer, fed by the same
ordered rows, and selected-source keeps its subtree events; both are writers of bytes, not
builders of the document a transform works on. Transforms thereby gain the checks they lack, and
the proven routine is the used one.

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
external-sort choice below from the complete operation.
[Review I04](../../plan_improvement_reviews/set-based-execution-common-analytics_2026-11-22.md#I04) ·
[Selected structural replay owner](owner-resolved-reads.md#sbx-12) ·
[PDF streaming custody](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_streaming.py#L71)

**The build identifier is supplied at load.** Replay rows carry no build columns. The adopt
program fills them from its argument. Files become independent of the build, recovery stops
rewriting them, and recertification checks the original files' digests.

**Certification reads the files.** Two passes over the memory-mapped IPC batches. The first
collects stream descriptors by stream id and folds part bodies per stream with an expected-next
ordinal check. The second builds each row's frame from the row and the descriptors and emits
frames to an external sort, then folds in order. Companions and their fields are held keyed for
the validators. Duplicate refusals that primary keys gave become explicit checks in the sort and
the fold.

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

<a id="sbx-14"></a>
## SBX-14 — One rebuild, under the captured policy

**Owns.** The paged row reader for `reconstruct`; migration of transforms and whole-document
reads to it; the capture contract's lowering; the child's use of it.

**Removes.** `hydrate_document` and whole-document use of the event stream; the materialization
bound's second evaluation of the event query, if nothing else needs it.

**Failure behaviour.** A published row set with a containment cycle, a wrong ordinal or a count
mismatch refuses a transform's input, where today it would be accepted or would not terminate.

**Evidence.** On the existing fixtures, the document a transform receives equals the document the
validation child reconstructs, compared as canonical bytes. A row set with a membership cycle is
refused by a transform. A forced re-validation of a publication made under an earlier schema and
callback policy passes under its captured policy and would fail under the current defaults; the
fixture is built with a policy that differs.

<a id="sbx-15"></a>
## SBX-15 — Access columns derived at publication

**Owns.** The derivation program; the reduced checker; the region view; staging of the JSON copy
alone; the pure document-to-items function for validators.

**Removes.** Column staging and its row equality; the checker's column, ordinal, section and
region sections; the stored region table.

**Evidence.** For the fixtures, derived columns equal the columns published today, row for row.
A staged JSON copy that disagrees with the rows is refused as now. Region reads by pointer and
index return today's values through the view.

<a id="sbx-16"></a>
## SBX-16 — One document, verified carriers, build identifier at load

**Projected candidate replay · Scheduled · 2026-11-22.** Candidate `_read_replay` currently
hashes bytes, decodes every column and recomputes the whole-page logical digest before
`iter_batches` selects the caller's columns. Status and geometry use different projections.
Carry the exact byte-to-logical admission in the page carrier, then reuse
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
Keyed region rendering and one-observation visual mapping stay on their current selected routes.
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

**Identity.** Changing the listed lowering modules and callables changes the lowering identity,
and retiring a module changes the standard producer contract. Both happen once, in revision C,
with the lists updated in the same change.

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

<a id="sbx-17"></a>
## SBX-17 — Certification and validation without round trips

**Owns.** The two-pass certifier; the keyed companion store for validators; typed capture and the
child's reads; closure checks before the rebuild; conversion of logical rows by column in the
companion export with the existing encoder.

Consume SBX-16's admitted page and replay carriers in the certifier and child. Retain complete
logical validation where the whole payload first enters the domain or its premises change.
Use `pa.memory_map`, `pa.ipc.open_file` and `RecordBatchFileReader.get_batch()` for typed
certification files, holding maps and batches until the readers finish. The existing page
stream decoder remains the route for page payloads. Preserve ordinal and duplicate expectations
independently of the typed reader. [Arrow file reader](https://arrow.apache.org/docs/python/generated/pyarrow.ipc.open_file.html)

**Open choice, settled in the package.** The engine for the external sort of frames: the
analytical owner over a temporary Arrow file, or the existing SQLite table. Either keeps byte
order, duplicate refusal and bounded spill, which the fold requires. Choose the simpler complete
route, including cleanup and canonical encoding. Keep SQLite if it needs less total integration,
and reuse the existing encoder in either route.

**Fidelity conditions.** The inputs to the folds pass through normalizations that are part of
each digest's effective definition: nulls dropped after a JSON round trip, key-presence tests,
and companion bodies parsed to float before decimal. The acceptance corpus includes
exponent-spelled floats, null against absent columns and non-ASCII keys.

**Evidence.** Retained certifications and a real recovery reproduce their recorded logical and
stream-inventory digests on that corpus. A duplicate record id, a duplicate part ordinal and a
duplicate page are each refused, with the expectation written by hand. The validation child
reads no JSON string per row. The companion export's logical-row digest is unchanged on a
mixed-type batch.
