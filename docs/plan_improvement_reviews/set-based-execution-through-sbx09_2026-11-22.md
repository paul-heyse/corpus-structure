# Set-based execution through SBX-09 after the typed-population pilot

**Review date and baseline.** Inspected on 2026-11-22 at `6834339f6`, with a clean
implementation and plan baseline. The footprint covers the remaining [coordinator queue](
../plans/set-based-execution_2026-11-21.md#remaining-execution-through-sbx-09), including the
installed producers and consumers of SBX-01 through SBX-09, native readers and export, and the
SBX-20 work needed to author and qualify the sole root. Adjacent SBX-11/12, SBX-16 and SBX-18
responsibilities were inspected where they determine placement. This is a standalone review.
The following amendments are **Proposed**. Existing finding dispositions, including construction
validity and reference closure, remain with the [coordinator](../plans/set-based-execution_2026-11-21.md#disposition-of-the-review).
The architectural authorities are [binding decisions](../design/DESIGN.md#section-2),
[D3 database](../design/D3-database.md), [D6 orchestration](../design/D6-orchestration-metrics-policies.md)
and [D8 query interfaces](../design/D8-agent-and-query-interfaces.md).

## Combined recommendation

Use a common **typed basis for each operation**. Let its owner admit the facts once, carry that
admission with the representation where it remains applicable, and reuse prepared state within
the selected cut. Use native sets for checks whose subject and authority are already in PostgreSQL,
PyArrow for admitted batches and projected file reads, and DuckDB for relational analysis of an
already fixed population. A semijoin can replace repeated membership, and a partitioned window can
express a dense order check. Each still needs a declared domain, exact occurrence keys, and the
right authority for the rows. Checks of current eligibility, complete coverage, transaction
settlement and exact-byte custody belong at the boundaries where those facts arise.

The pilot decided the first placement question. Retain immutable annotation blocks and the
already-acquired contextual rows, then finish the consumers of those carriers. Serializing the
carrier to Arrow and rebuilding it at the other end would repeat preparation on this path.
The pilot’s strongest new signal is the cost of *read preparation*. The provider cohort
`90493eda42ba42ecb7ce700513ee4670` passed four identities. Both that run and the exact trial
`8456c96758dc4ef0bcfb4b4a29751bd4` reached the 8 MiB retained selected-closure limit on the
fork. The scoped 64 MiB rerun `52f96d62df8945858ebdbb3cddae97b2` passed including exact selected
readback. Keep 8 MiB as the normal limit while the ordinary keyed path still prepares that
closure. The separate textbook MCP deadline belongs to the later read/replay work.
[Tested 2026-11-22, including receipt scopes and the carrier decision](
../plans/set-based-execution/common-analytical-basis.md#pilot-implementation-and-evidence)

The design standard favors explicit semantic authority, execution fit and reuse of admitted
values. The highest-payoff interventions are [I02](#I02) and [I04](#I04), since the same
authorization and settlement obligations already drive the remaining migrations. [I03](#I03)
offers a direct way to remove preparation if the governed successor supplies a concrete caller.
[I01](#I01) and [I06](#I06) govern sequence and evidence. [I05](#I05) closes the smaller custody
mismatch and places the newly found PDF projection opportunity with its consumer.
[Principles FP-04, FP-07, DP-09, DP-10 and DP-23](../design_review/design_principles/core/design-principles.md) ·
[Execution heuristics](../design_review/design_principles/core/efficient-architecture-heuristics.md) ·
[Test assessment](../design_review/design_principles/core/test-assessment.md)

<a id="I01"></a>
## I01 — Make the installed successor the integration path

**Proposed execution improvement.** Replace pilot-first queue wording with its recorded decision.
SBX-01/02 are the installed collection and rule foundations. Reopen their contracts only where
the SBX-03/04 construction and contextual claims require them. In SBX-03/05/06/07 use one real
installed canonical successor to exercise occurrence correspondence, exact current producer/use
selection, publication-driven settlement and memo reuse. Feed it through ordinary admission,
execution, publication and selected readback. The pilot establishes the transport placement and
an unchanged fork. The revision-A journey still needs actual governed changes and downstream
adoption. [Queue](../plans/set-based-execution_2026-11-21.md#remaining-execution-through-sbx-09) ·
[Early integration](../plans/set-based-execution/cutover-and-qualification.md#early-revision-a-integration)

Use the same journey to distinguish these outcomes:

- Edit an unread field. Check that the unaffected projection and consumer execution claim remain
  valid. Then cause a real producer attempt whose downstream projection settles equal. Check
  proof applicability and downstream adoption independently of skipped computation.
- Move or rename a block, and reconvert with independently known provenance. When the local
  projected bytes and effective parameters agree, a worker-local hit is valid and the result
  must refer to the current occurrence and binding. Repeated equal content and an ambiguous
  split or merge must retain their occurrence semantics when a computation can be reused.
- Change a read field or eligibility premise. Check that a matching digest cannot authorize
  reuse of an invalid proof or attachment. Check that the selected output reports the exact
  current cause and use.

Keep the existing charged, worker-local canonical memo. Its key covers project, recipe,
projection and effective parameters, and the assembled output uses current references. The
spawned-worker controls on 2026-11-22, including the rename hit and exact canonical byte and digest
comparisons, passed with `0f867b8b822d4391be68bbdbeb6a854f`. Remove consideration of a persistent
table or cross-worker cache for this slice. A named later workload would need to establish its
own complete determinants and custody. HanLP and other hosts may observe a cohort or batch,
so a block-only key cannot be inferred from the canonical result. This keeps independent
expectations for local computation, proof applicability and current attachment (DP-04, DP-09).
[SBX-03](../plans/set-based-execution/populations-rules-and-proofs.md#sbx-03) ·
[SBX-07](../plans/set-based-execution/references-and-projection-keys.md#sbx-07)

<a id="I02"></a>
## I02 — Bind the construction premise once and check addresses in sets

**Proposed alignment and efficiency improvement.** Specify the exact construction and contextual
navigation facts before removing rereads. Construction already gets admitted primary block views.
The retained characterization carrier already parses its input collections and verifies their roots
on acquisition, yet construction reacquires those blocks and rebuilds item/layout sets. The
current intrinsic navigation declaration reads construction members. It does not establish the
selected annotation layout, address and token facts that the cross-input check needs.
[Current construction checks](../../python/corpus-structure/src/corpus_structure/semantic/construction_products.py#L777) ·
[Retained carrier](../../python/corpus-structure/src/corpus_structure/semantic/enriched_document_products.py#L139) ·
[SBX-04](../plans/set-based-execution/populations-rules-and-proofs.md#sbx-04)

Bind the exact selected producing role and member, occurrence, logical slot and the roots or
other facts that govern layout, token membership and order. First examine the existing
establishment reader over a declared role header and the observed output navigation/coverage
fields. The header carries separate body and placement commitments. Use each where the rule
observes it. A whole-collection commitment can conservatively invalidate on an unrelated edit.
Introduce a narrower group premise only when its producer and current consumer can derive the
same fact and a concrete reuse case warrants it. Thread the admitted block view where it is
already present. On genuinely sparse reads acquire only addressed authorized partitions. Preserve
full-domain checking where the claim requires closed coverage. Retain the contextual role if
interpretation independently observes it. A historical establishment by itself gives no access
to a replacement input with equal content. [Header commitments](
../../python/corpus-structure/src/corpus_structure/semantic/data_operation_partitions.py#L152) ·
[Rule establishment](../../python/corpus-structure/src/corpus_structure/semantic/rule_establishment_native.py#L74)

Publication and projected adoption already invoke the owner-native reference validator. It
selects a declared input and expands addresses once per contiguous visit to a partition.
Interleaved references in construction can revisit it. Reuse one admitted address lookup per
exact authorized input/partition or group native requested references by partition and do a
membership/cardinality comparison. Choose the least preparation for the actual shape. A second
Arrow or DuckDB validator would need the same rows moved out of the transaction and would
duplicate authority. For a dense batch already carried as typed values, a relational comparison
is a useful independent check. Capture distinct partition opens or expansions in the installed
fork only if the choice depends on how often the path repeats work. Preserve reference failure
order and identity, malformed typed addresses, duplicate occurrences, access denials and
publication/adoption atomicity. Cover token extent and order, equal body at different placement,
genuine absence, ineligible or revoked premise, and complete versus partial scope (FP-04, DP-03,
DP-07, DP-10). [Native reference validator](
../../python/corpus-structure/src/corpus_structure/semantic/data_operation_reference_native.py#L124) ·
[Native set rule owner](../../python/corpus-structure/src/corpus_structure/semantic/data_operation_rule_native.py#L563)

<a id="I03"></a>
## I03 — Use the guarded native route for a genuinely keyed selected read

**Proposed conditional sequencing improvement.** The selected contribution reader prepares the
SQLite-backed selected closure even when the caller has an exact product. Structural projection
then resolves several references and the live entry point rebuilds indexed access and resolver
state per call. Native exact-parent and addressed partition reads already exist. The existing
`LiveReferenceAccess` adapter requires a captured consumer selection and currently handles one
binding for a product/member/kind. Multiplicity, occurrence labeling, original producing
attachments and the disclosure path still matter. [Selected reader](
../../python/corpus-structure/src/corpus_structure/serve/selected_contributions.py#L44) ·
[Live reference access](
../../python/corpus-structure/src/corpus_structure/semantic/live_reference_resolution.py#L50) ·
[Native addressed partitions](
../../python/corpus-structure/src/corpus_structure/semantic/data_operation_read_native.py#L968)

Complete the existing family migration after construction and contextual premises. Actual
characterization and declaration nodes need declared addressed collections or admitted
members. Artifact and witness reports, contributions, facets and rich records need the same
original-role/current-authority protocol, including labelled multiple occurrences where
declared. Carry the contract through native publication, serving, evaluation and detached
verification, with the protected issuer and genuine report paths as acceptance cases. Remove
legacy reference types and checks at their last consumers. This work already belongs to
SBX-05 and does not require the keyed-read optimization. [Existing SBX-05 family order](
../plans/set-based-execution/references-and-projection-keys.md#sbx-05)

Start with the exact scalar construction slot used in the installed journey. If it can share
one selected-cut lifetime, an exact current eligibility guard and a role-relative selected
use/path, prepare those facts once and use the existing resolver and native addressed reads
for the batch. Reauthorize each lookup; scope the reuse to that cut. Move this slice into
SBX-05 only if it removes ordinary full-closure preparation for that actual caller and fits the
final consumer contract. Otherwise finish SBX-05 on its accepted contract and do the keyed
migration with SBX-11. Keep the closure path for detached replay and genuine transitive discovery
until their own owners replace it. A control with the production resolver and a stand-in access
port observed three authorized lookups sharing a single partition open. It also exercised
authorized absence and denial on a cached partition. This establishes the resolver's local
behavior, with native selection and database access still to verify. Use the installed fork
to check exact current and producing use, ambiguous multiplicity, wrong or stale selection,
absence versus withheld access, independent ordered answers and whether the request can run under
the ordinary budget (FP-04, DP-10, DP-20). [Tested 2026-11-22, scoped resolver control](
../design_review/evidence/2026-11-22_sbx09-review/README.md) ·
[SBX-05](../plans/set-based-execution/references-and-projection-keys.md#sbx-05)

<a id="I04"></a>
## I04 — Finish native event settlement before removing the recursive watermark

**Remaining accepted work with proposed refinements.** PostgreSQL already stores exact publication
fulfillment and release activation identities. Use those facts in the existing bounded native
executor and generation-checked readiness path. The native overlap test observes a gap after
both commits and explicitly calls selection advancement to repair it. Make normal resume or
drain reconcile event-before-enrollment and enrollment-before-event from the exact retained
facts. Retry or loss of acknowledgment should reuse the committed claim and advance only the
current generation. Release activation already retains its old and new release and generation in
the same transaction; use that fact for recovery with prospective maintenance opt-in and the
existing frozen-demand semantics. [Publication reconciliation](
../../python/corpus-structure/src/corpus_structure/semantic/publication_delivery_native.py#L115) ·
[Overlap test](
../../python/corpus-structure/tests/semantic/test_publication_delivery_native.py#L209) ·
[Activation](../../python/corpus-structure/src/corpus_structure/semantic/closure_native.py#L558)

Extend the attached scalar readiness cut to account for each affected, unchanged and unavailable
arm. Prove appropriate closure for the current scoped selection. Include fulfillment and join
arrival, first discovery, departure, scope closure, proof or trust changes and superseded
generations. Discovery's existing anti-join compares prior closure by semantic keys that omit
the exact admitted use tested by population validity. The resulting question is whether a
historical or revoked closure masks a newly admissible witness with the same semantic key.
Exercise that case, complete-empty, incomplete and first member against independent expected
uses and recipients. Batch common relational work only if the native closer retains support
locks, current demand and context, output authority, completeness, duplicate handling and atomic
settlement. [Discovery sweep](
../../python/corpus-structure/src/corpus_structure/semantic/publication_delivery_native.py#L220) ·
[Population closer](
../../python/corpus-structure/src/corpus_structure/semantic/demand_registration_native.py#L1544) ·
[Attached scalar cuts](
../../python/corpus-structure/src/corpus_structure/semantic/obligation_readiness_native.py#L280)

The recorded exact-pin wake, local eligibility, original admission and selected population
controls establish those individual origins. The scalar-join control
`4290f9f41f354ea0b5c0e8df35a188f2` also exercised one unchanged arm on 2026-11-21.
The real cross-release adoption passed on 2026-11-22 (`fc1c520ca269452496679c52b1f3310d`).
Use those scoped results to focus the successor on multi-origin ordering and coverage, with
one committed journey through normal recovery. [Retained SBX-06 evidence](
../plans/set-based-execution/references-and-projection-keys.md#sbx-06)

The recursive watermark is a fallback scheduling heuristic. The shared native page can still
compute it for public reads with absent native readiness. Grading uses the page's exact
obligations/uses and export serializes the page. Give scheduling state a scheduler-owned
projection before retiring the recursive watermark, repeated discovery sweep and their obsolete
fields. Verify actual resumption after overlapping commits, exact downstream reuse and
attachment, grade completion on the selected cut and genuine detached export/replay. Already
sealed pages retain their recorded reader schema. For a finite comparison, DuckDB can test
a typed selector or closure on a captured cut. The pinned probe lost an independent arm when
keyed by node alone and retained it when keyed by node and arm. Distinct keys or `EXCEPT ALL`
must preserve exactly the role, occurrence and generation relevant to the claim. Native
settlement still owns authorization and atomic effects. An independent small expected set is
sufficient where it exposes the same errors (DP-07, DP-12, DP-19, DP-23).
[Watermark call](
../../python/corpus-structure/src/corpus_structure/semantic/data_operation_projections.py#L2559) ·
[Grading](../../python/corpus-structure/src/corpus_structure/semantic/record_grade_native.py#L447) ·
[Export](../../python/corpus-structure/src/corpus_structure/serve/demand_export.py#L208) ·
[SBX-06](../plans/set-based-execution/references-and-projection-keys.md#sbx-06) ·
[Tested 2026-11-22, finite DuckDB control](../design_review/evidence/2026-11-22_sbx09-review/README.md)

<a id="I05"></a>
## I05 — Keep worker custody and put projected IPC where it avoids decode

**Proposed carrier disposition.** Finish SBX-08 on the selected nominal immutable carrier and
the native frame and sealed worker routes already implemented. Share decoded partition bodies
within their existing byte owner. Keep population and placement commitments on each acquired
assembly, with derived indexes owned by the invocation. The 20 scoped partition controls
already established relocation, altered-row refusal and reacquisition after cache clear on
2026-11-22 (`3db106fc6ad84c29889413846a39f95f`). Verify the remaining ordinary and spawned
provider routes on the registered head, including the five native stream cases that stopped
at legacy descriptor correspondence. Carry the request fence and independent retained reply
checks through the same journey. [SBX-08 scoped receipts](
../plans/set-based-execution/validated-values-and-handoff.md#sbx-08)

**Proposed contract clarification and later PDF opportunity.** Retain the two-check executable
bracket. The CPU worker still verifies live source and uses the Python loader/import path.
A source digest or sealed Arrow packet can identify captured input, but replacing the second
check would require a loader binding the code that actually executes, its late imports and
assets to that capture. Keep the attempt, cancellation and reply fences at their own boundaries.
The threaded region and visual migrations are already present. Their second verification
currently precedes result encoding and their parent checks attempt activity after collection.
Align the second verification with the last use of captured code or assets, including encoding
if it uses them. Keep the existing two checks and verify the actual executor journey on the
registered root. Reconcile the stale migration wording. Exercise changed late imports or assets,
expired attempt and no published reply on invalidated inputs (FP-06, DP-15, DP-19).
[CPU worker](../../python/corpus-structure/src/corpus_structure/semantic/data_operation_cpu.py#L164) ·
[PDF thread](../../python/corpus-structure/src/corpus_structure/semantic/native_requests.py#L391) ·
[Visual thread](../../python/corpus-structure/src/corpus_structure/semantic/visual_requests.py#L354) ·
[SBX-08/09](../plans/set-based-execution/validated-values-and-handoff.md#sbx-09)

Keyed PDF rendering already reads one selected region and its original bytes and releases the
database lease before render. Visual maps one observation and PNG. There is no whole Arrow
payload decode on either path to remove. The existing published PDF reader already verifies
physical bytes before Arrow IPC projection, with nested Arrow kernels for inventory. Preserve
full logical identity checks when admitting or replaying the complete payload. A probe using
the production payload writer found two valid payloads with equal projected page number and
different full bytes and logical digests. The projection cannot attest to omitted fields.

A different PDF consumer exposes actual savings. Candidate replay currently decodes every
column and recomputes the whole-page logical digest before selecting columns. Status and
geometry ask for different subsets. With the existing SBX-16 replay carrier, retain whole-page
logical admission at the boundary, authenticate the exact bytes after storage or a handoff,
then push top-level selection into IPC, or reuse one bounded admitted decoded batch when both
consumers need it. Retain schema, exact receipts and owned file/reader lifetime. Test nulls,
ordinals, changed unprojected columns and a recovered spool; compare with independent full-page
expectations. Keep the PDF rewrite in SBX-14–17 (DP-09, DP-10, DP-15).
[Published PDF reader](
../../python/corpus-structure/src/corpus_structure/semantic/pdf_record_reader.py#L981) ·
[Candidate replay](../../python/corpus-structure/src/corpus_structure/ingest/pdf_candidate_source.py#L45) ·
[Status and geometry](../../python/corpus-structure/src/corpus_structure/ingest/pdf_candidate_geometry.py#L38) ·
[SBX-16](../plans/set-based-execution/pdf-path.md#sbx-16) ·
[Tested 2026-11-22, Arrow projected payload control](../design_review/evidence/2026-11-22_sbx09-review/README.md)

<a id="I06"></a>
## I06 — Qualify the registered singleton through ordinary preparation

**Proposed execution improvement.** Bring up the integrated, null-predecessor root immediately
after the functional changes are in place. Reconcile tested carrier and verification work
before retiring the active predecessor chain and its data-step code. Inspect the captured source,
descriptor, rollback, exact head and grants. Install the registered root from empty state on a
fresh qualification target and check purpose-role access early. Keep the existing independent
cold authoring and rollback fixtures for those claims. Reuse the existing verified deployment
template and per-test commit clones for ordinary provider and sentence-chain cases that currently
capture, author and install their private root. This reduces repeated test preparation and
ensures those cases exercise the actual registered head. Preserve shared-host authentication,
fault and durability cases where isolation would change the claim (FP-06, FP-07, DP-10, DP-23).
[Cold root work](../plans/set-based-execution/cutover-and-qualification.md#development-reset-through-sbx-09) ·
[Verified test deployments](../adr/0101-verified-test-deployments.md) ·
[Current sentence fixture](
../../python/corpus-structure/tests/semantic/test_sentence_partition_chain_native.py#L114)

Run required ordinary, provider and repository checks on final source and account for the
required identity union. Preserve failures and interruptions and reuse recorded results only
where source, descriptor, scope and context still apply. Earlier pilot, bracket and cold-root
rehearsals establish their dated scopes. Final qualification still needs the integrated governed
successor and an authentic finite and rich publication-to-verified-export journey. After
acceptance, discard the authorized development database and install the same root empty on the
dedicated cluster. There is no development data retention, backup, backfill, dual-write or
compatibility work to schedule. Stage installation remains with SBX-20.

## Library capabilities examined and where they pay

**Inspected 2026-11-22.** Reviewed the capability overviews and CLI guide against installed
use and the named consumers above. The fresh probes exercised PyArrow 26.0.0 and DuckDB 2.0.0.
The prior pilot pins ADBC PostgreSQL 1.13.0 and records the matching DuckDB test build.
Source or documented capability is described below where it affects a choice. An independent
probe was reserved for a consequential uncertainty. [PyArrow](../libraries/analytical_infrastructure/pyarrow.md) ·
[DuckDB 2](../libraries/analytical_infrastructure/duckdb_2.md) ·
[DuckDB CLI](../libraries/analytical_infrastructure/duckdb_2_cli.md) ·
[Prior placement evidence](../plans/set-based-execution/common-analytical-basis.md#postgresql-placement-and-transfer)

| Capability | Relevance and evidence needed to change placement |
| --- | --- |
| Arrow schemas, nested lists and structs, presence bits, scalar and nested compute, dictionary/chunked arrays, batch validation and canonical projection | Use typed schemas at an existing batch boundary. Preserve absent versus null, empty versus absent collection, exact integer/address ranges, multiplicity and explicit ordinal. Structural validation checks shape. A sorted/grouped typed comparison can check business constraints against independent expectations. Existing annotation objects already carry these facts, so a packet adds work in SBX-03/08. Arrow expressions or Acero fit if a real dense existing Arrow input can share columns and kernels across consumers. Check current types and null/order behavior before preferring them to a simple index or native set operation. |
| DuckDB joins, anti-joins, `EXCEPT ALL`, partitioned windows, `QUALIFY`, ordered aggregates and nested SQL | Good candidates for cardinality, completeness, rank, duplicate and boundary checks on fixed typed populations. Include ties, explicit order, missing scope, equal content at different positions and null semantics. Native SQL already owns many publication rules and avoids extraction. Prefer a keyed access path for few addresses. Range/ASOF and nearest-candidate joins may help a later analytical sweep. Prove direction, tie-breaking and scope before using them for correspondence. They can suggest candidates; exact occurrence and provenance decide acceptance. |
| Recursive CTEs, `USING KEY`, temporary relations, triggers and `MERGE` | The bounded probe discriminates keys that collapse distinct arms and set difference that collapses duplicates. Use a finite model only if it independently exposes an error in a proposed selector. Scratch relations can share a prepared analytical population if needed. Scratch DML and local triggers cannot establish native commit identity, enrollment, trust and recovery. For SBX-06, extend the native owners above. [Recursive CTE reference](https://duckdb.org/docs/2.0/sql/query_syntax/with) |
| Arrow IPC projection and C Stream, batch readers and budgets, DuckDB Arrow reader and result lifecycle | Useful for existing typed PDF or later analytical transfers when projection avoids decode or batch movement. Test full-byte authentication first, empty/truncated or replaced data, stream drain or early close, connection/replacement behavior and ownership on failure. Keep whole logical admission where needed. For a DuckDB trial, distinguish another connection operation while a result is unfinished from issuing another `execute` that replaces the result. [Arrow IPC read options](https://arrow.apache.org/docs/python/generated/pyarrow.ipc.IpcReadOptions.html) · [DuckDB 2 Python lifecycle](https://duckdb.org/docs/2.0/clients/python/migration) |
| Parquet row groups, statistics, projection/filter pushdown, partitioning, manifests and spill | Opens a useful later replay option for stable selected populations reused by several scans (SBX-12/18). Check file authentication, schema and explicit order, publication/retry of a complete artifact and independent parity with the frozen cut. For a one-shot keyed live request, a new file to write, authenticate and keep adds preparation and lifetime work. Judge clustering, spill and row-group layout with a real workload if they could change a later decision. |
| Native PostgreSQL sets and COPY, ADBC, DuckDB PostgreSQL extension and database placement | Reviewed live native processing, selected native reads plus batched transfer, and direct attachment. COPY already has a typed PDF consumer. The pilot established an exact ADBC handoff on its admitted snapshot, which confirms feasibility for a downstream shared population. It did not remove tagged packet assembly or justify broader purpose grants. The extension can use pooled backend sessions for parallel scans. Any candidate must demonstrate equivalent visibility to pending writes, exact snapshot and pin, purpose auth, type fidelity and cleanup. Keep native authority in one transaction through SBX-09. Take up direct attachment or alternate durable placement only for a named shared workload that removes a real boundary. [PostgreSQL extension pool](https://duckdb.org/docs/2.0/core_extensions/postgres/connection_pool) |
| Native types, dynamic types and extensions | Prefer model-derived typed columns for occurrences, span and time/decimal precision. DuckDB `VARIANT` and Arrow extension arrays can represent more input shapes, but bring conversion semantics whose value depends on a named consumer. Avoid a second graph model through DuckPGQ when native projections already express scope and dependency. Spatial, vector and text index decisions belong with the actual retrieval consumers. |
| Flight and remote services, Substrait and extension execution, device/GPU interchange, DuckLake or remote DuckDB transport | No remaining SBX-09 consumer calls for a remote exchange, portable query plan, device-resident typed computation or analytical catalog. These add an execution or custody boundary. Reconsider where a later owner can name which work and handoff disappear. |

## Adoption and verification limits

If selected, first revise the coordinator using the completed pilot and existing scoped work.
Settle the authority and proof contract, then use the installed successor to decide whether
the keyed live slice should move forward. Native settlement and the worker endpoint can proceed
alongside those changes once their interfaces are agreed. Retire superseded rows, paths and
mechanism-specific tests as each consumer moves. Finish the registered root and qualification
after the integrated journey can run. Use the existing plan documents and disposition owners.

**Tested 2026-11-22.** The three focused boundary controls passed. Managed tests passed 27
selected cases (`cd3bf0ad96654638aa90f7113a6a315d`) with
`uv run ci test --workers 2 -- python/corpus-structure/tests/semantic/test_pdf_payloads.py python/corpus-structure/tests/semantic/test_pdf_payload_reader.py python/corpus-structure/tests/semantic/test_role_relative_references.py`.
No new provider, native successor, database attachment or final registered-root run was needed
to answer this review. The proposals carry qualitative benefits. No latency or capacity gain
has been measured. [Probe method, exact expectations and results](
../design_review/evidence/2026-11-22_sbx09-review/README.md)
