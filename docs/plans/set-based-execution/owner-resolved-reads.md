# Owner-resolved reads

**Status:** Proposed. Companion of [Set-based execution](../set-based-execution_2026-11-21.md).
**Created:** 2026-11-21.

This companion owns the read side: what a reader may ask PostgreSQL, what the replaying readers
carry, and how answers are paged and cached. It owns SBX-11 to SBX-13 and is carried by native
revision B. Source facts are **Inspected** at `7a415d18d`. The common analytics amendment
schedules review I04 below against source `d884fa8a2` and review commit `8fab53dd5`.

## Baseline

**The program.** One security-definer program answers a selected read
(`cs/semantic/demand_result_native.py`; page body `read_page` in
`cs/semantic/data_operation_projections.py`). Its views are frontier, products and support.
`limit` counts obligations. The support view exports 25 relations as keyed records and recomputes
the walk on every page.

**Authority per call.** Universe authorization, read currency with trust epochs re-locked, and
visibility by the read receipt depend only on the cut and survive any change of answer shape.
Body access (`ddo_body_access`), kind disclosure and authority-leaf masking depend on the rows
returned and must be restated for any new shape.

**Cost of changing it.** The program is in the read closure whose digest is stamped into every
receipt. Any change invalidates outstanding receipts, cursors and resource handles, regenerates
the wire contract, and moves the digests of the record-grade and operation-event programs that
embed `read_page`.

**Post-SBX-01 baseline · Inspected 2026-11-21.** Exact consumed-use retrieval is keyed. The
adjacent graph-input path still enumerates authority leaves to build a map. The private
partition acquisition checks parent project and kind and leaves selected-parent and current-cut
authority to its caller. These are the preparation and disclosure boundaries this work addresses.
[Graph-input path](../../../python/corpus-structure/src/corpus_structure/semantic/selected_contribution_input.py#L169) ·
[Private partition acquisition](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_partition_native.py#L438)

**Push propagation baseline · Inspected 2026-11-21 at `3ceeadfbc`.** The live result read
requires an explicit demand and project. Its cursor continues the acquired cut. The
freshness-aware read below adds a governed selection scope alongside these exact reads.
[Live demand read](../../../python/corpus-structure/src/corpus_structure/semantic/demand_results.py#L171) ·
[Exact CLI selection](../../../python/corpus-structure/src/corpus_structure/cli/selected_results.py#L22)

**Precedent for a family of programs.** `read_selected_pdf_source`, the observation and visual
reads, the feature-fit frame and `data_binding_rows` are already separate programs that
authenticate a pinned cut through shared projections. `acquire_data_read_context` performs the
per-call authority checks alone.

**Readers.** 41 call sites. Only the structural family (structures, dossier, gaps, source
journey) and export verification ever run offline. Every other reader, including all evaluation
readers, is online only.

**What PostgreSQL computes and Python discards or rebuilds.**
- The use-to-output-to-product join is in every frontier page; `SelectedRecordIndex.append_page`
  strips it and at least five readers rebuild it by keyed lookups.
- A derivation's inputs with their support: `ddo_input_support_refs` computes it natively;
  Python re-derives it from outputs and admissions.
- Producer of a product, with release, recipe, outcome and inputs by role: readers scan the
  output relation by product, which the index does not key.

**Paging and caches.** Six cursor schemes and several offset tokens. Every derived-row cache key
includes the cut identity, so a first page never hits, a revocation anywhere in scope evicts
every answer, and each process starts cold. `recheck_selected_frontier` walks the whole frontier
on every page to recheck body access and to produce a cache stamp.

**Transaction.** Most readers hold one transaction, with trust locks, through all Python work;
graph inspection alone commits the receipt and releases first.

**Evaluation.** The grade and event plans open a second index before running and re-derive use,
episode, request, output and recipe facts that the binding established and that the completion
guards recompute. One check has no database equivalent: authored reference coordinates against
retained source text.

**Common analytics baseline · Inspected 2026-11-22.** The selected structural review exports,
replays immediately, and later reopens the frozen archive for verification. The Parquet option
also emits JSONL, while replay reconstructs a SQLite index from JSONL. This repeated conversion
makes that archive the first persisted Parquet boundary in this series. The retained pinned-build
probe establishes fixture-level Arrow and Parquet behavior, including refusal of a truncated
footer. Integrated archive publication and recovery still require the SBX-12 evidence below.
[Review I04](../../plan_improvement_reviews/set-based-execution-common-analytics_2026-11-22.md#I04) ·
[Pinned-build evidence](../../design_review/evidence/2026-11-22_sbx-common-analytics/README.md)

## Target

**A small family of programs behind one boundary.** Each calls the shared read-currency and
authorization steps and shares the scope, walk and output projections.

| Program | Answers | Replaces |
|---|---|---|
| Frontier (existing) | The cut, obligations, uses with their output references | Unchanged in role |
| Outputs | For uses in scope: derivation, request operation, output role and position, product or member with kind and context, body on request; filtered by kind, member or address, record type; keyset-paged over output position and member or partition | Stripping and rebuilding the join; member filters after the fact; one-obligation paging |
| Partitions | For a product and collection: partitions by key or in ordinal order, with digests and item counts, bodies and chosen field groups on request | Whole-body reads for populations |
| Derivation facts | For a derivation: its recorded inputs with resolved support; for a product: its producing derivations with release, recipe and outcome | Scans of input and output relations; the Python mirror of support matching |
| Proofs | For products or partitions and a rule set: which are established | New |
| Support subgraph (existing export) | The raw relations of the closure, now including partitions and proof rows | Unchanged in role; for replay only |

Whether each program joins the receipt-checked read closure is decided per program, so that a
change to one does not invalidate receipts used by another.

**Sufficient facts per access shape.** Start from the exact use and selected parent in the
acquired cut. Establish current visibility and purpose before acquiring the body. Keyed item
reads add the membership check from the [reference contract](references-and-projection-keys.md#the-reference-model).
Filtered pages acquire authority for the selected parents and support edges they traverse. A
legitimate empty answer follows from the authorized selection and filter, with undisclosed
partitions kept outside absence claims. Genuine export and replay still acquire the required
transitive closure. Proof reads follow the rule's [premise and establishment contract](populations-rules-and-proofs.md#proofs).

The response page budget covers delivered rows. For a structural point read, use the exact
selected use and producing role to fetch the named member or partition and the support needed
for its authority. The online backing should follow additional keys only when the reader asks
for them. An algorithm that needs a graph can build it from that acquired subset. Apply the
existing textbook condition and protected-admission control with unrelated support present to
verify that this point read avoids building an index of the whole selected closure.

Change-only reads use product headers, projection digests and declared dependency edges. The
projection-keyed binding in [SBX-06](references-and-projection-keys.md#sbx-06) determines change
before any body hydration. Expose digest-only answers through the same keyed programs and scope
their authority to the selected metadata.

<a id="freshness-aware-reads"></a>
### Freshness for an explicitly governed selection

**Proposed.** A caller opts in by naming a governed selection and its project. The authorized
owner advances that selection through an explicit transition or an explicitly selected successor
demand. Execution starts through the existing demand path. In the same native acquisition,
resolve the governed scope, authorize the result and its freshness metadata, and acquire the
result or its cut with the [settlement coverage supplied by SBX-06](references-and-projection-keys.md#settlement-coverage).
Expose these outcomes for the requested scope.

| Outcome | What the native acquisition establishes |
|---|---|
| Fresh | A result or cut is available and settlement covers the relevant committed changes. |
| Pending | A relevant committed change still needs a downstream decision or a demanded result. |
| Unavailable | The scope is resolved and the owner establishes that no eligible result can be supplied for it. |
| Unknown | The owner lacks sufficient coverage evidence to determine freshness or availability. |

A queued item at the immediate consumer is only one sign of pending work. Coverage must include
committed upstream changes whose propagation has yet to reach that consumer. A branch that
settles unchanged can advance coverage without a new provider attempt. Independently covered
scopes stay readable. A caller can explicitly request the last settled cut, identified as such,
if the current native checks authorize it. Scope, selection and leaf disclosure rules also
apply to freshness metadata. Responses preserve existing refusal and masking rules for
protected state, including where disclosing pending work would expose a protected dependency.
[Push-propagation review I04](../../plan_improvement_reviews/set-based-execution-push-propagation_2026-11-21.md#I04) ·
[Disclosure owner](../../adr/0147-sbx-owner-resolved-reads.md)

**Online readers ask; replaying readers carry.** A reader with no offline entry point asks for
the shape it needs and decodes bodies. The structural family and export verification keep one
implementation over the raw relations, run from PostgreSQL rows online and from the export
offline. The end the replay serves is that someone without the database can confirm a served
response follows from the exported closure; one implementation over two sources is what carries
it.

**Replay relations are typed.** Derive relation schemas under the
[common projection contract](common-analytical-basis.md#projection-contract). Replaying readers
use one interface with keyed get, children by foreign key, filtered scan, embedded reference,
and whole-relation iteration. Its live backing acquires rows through the scoped native read
owner, while its detached backing reads the sealed Parquet archive directly. Preserve canonical
encoded body fields wherever their exact value forms need that representation, and retain cut
and frontier bytes. Both backings feed the same structural projection and reference interpretation.

**Acquire the shape the consumer uses.** Compare direct Parquet keyed and filtered scans with
an Arrow relation and a once-built lookup index for the actual structural projection. Use the
analytical owner for set work that combines relations. Select the simplest complete route across
first replay and subsequent rereads, including verification, file reads, derivation, buffering and
cleanup. Immediate reuse uses in-memory batches, and transient pressure uses the existing spill
owner. A whole-relation consumer can acquire the whole relation, while keyed consumers follow
only the governing keys and required support. Remove duplicate closure and index construction as
their consumers move. Persist a derived dossier relation only when a named rereading consumer
avoids repeated derivation after accounting for its full write and read cost. Such a relation
carries its implementation and determining input identities under the same projection contract.

**Seal the archive at its manifest.** The manifest binds relation schemas, selected scope,
completeness, row order, lineage and file digests. Record an authorized empty relation explicitly.
Compression and row-group layout are physical choices outside semantic identity. Verify the
relation file digests and the declared logical content and ordering, including partition and root
commitments. Publish the sealed manifest only when its complete file set is ready. An interruption
before sealing leaves an incomplete archive that readers refuse. Restart through the existing
publication owner and either finish that exact archive or report its unusable state. Detached
replay interprets the captured cut and custody. Each live acquisition and continuation establishes
current authority at its requested cut, including when local payload or a derived answer is reused.

**One cursor.** Version, implementation identity, selection digest, cut, and a position that is a
keyset where the data is row-addressable and an ordinal where rows are derived. Clients do not
see native keysets. A freshness-aware first page binds its authorized cut. Continuation follows
that exact cut even if the governed selection advances. Each live page reacquires authority
and checks current revocation. Detached replay establishes captured custody under the exported
cut and evidence.

**A substantive cache key.** Implementation, selection digest and the digests of what the answer
read: product body digests, partition digests, rule fingerprints. The key survives a fresh cut
and a revocation that did not touch what was read. Authority is never cached: each call performs
the context-only authority check and body access for the products it returns, which replaces the
whole-frontier recheck. An answer that depends on the validity of its support includes that in
its per-call check. For an answer about proof absence or completeness, a cache hit must also
establish current membership in the relevant proof and establishment relations. Bypass answer
reuse for that shape if current membership cannot be established from scoped reads. A new
matching proof can change that answer with the same content digest and rule fingerprint.
Coverage and authority are established by the native read even on a semantic answer cache hit.
[Shared change scenarios](cutover-and-qualification.md#change-scenarios) ·
[Continuation authority](../../adr/0141-serving-continuation-and-reuse.md)

**Transaction scope.** A reader acquires in a short transaction, commits the receipt and releases
trust locks before deriving, the pattern graph inspection already uses. An online reader that
asks for an answer shape derives nothing afterwards.

*Alternatives rejected.* Extending the one program with every view and filter: one closure
digest, so every addition invalidates every receipt, and the meaning of `limit` splits further.
Keeping the index for online readers with cheaper lookups: leaves the rebuilt joins in place.
Answer-shaped programs for the replaying family as well: two implementations of the same
projection, which is what makes replay meaningless.

<a id="sbx-11"></a>
## SBX-11 — The read programs

**Additional scope and evidence.** Demonstrate a keyed read, a legitimate empty
answer, and a filtered continuation with unrelated partitions, frontier uses and protected
leaves present. Use independent expected rows and authority outcomes. Apply the read contract's
missing-address outcome for a missing item inside an authorized partition and preserve
non-disclosure for a protected parent. Reacquire authority on continuation and exercise relevant
revocation between pages. Use a narrow decoded-body or examined-row check where it distinguishes
bounded acquisition from a broader scan. Retain the genuine selected-use and native export
controls under the [shared development evidence policy](cutover-and-qualification.md#cutover-policy).
[Post-SBX-01 review I04](../../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I04) ·
[Post-SBX-01 review I09](../../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I09)

**Owns.** The outputs, partitions, derivation-facts and proofs programs; their disclosure checks,
which restate body access, kind disclosure and leaf masking per row returned; their wire records;
the membership of each in the read closure; migration of every online-only reader to them.

**Freshness slice.** Integrate the opt-in selection and coverage observation above into the native
read boundary and its wire contract. This slice consumes SBX-06's working settlement coverage.
Other keyed read shapes can advance against their partition, proof and reference prerequisites.
Use the shared propagation scenarios to verify pending coverage between edges, an unchanged
branch advancing coverage, a separately resolved scope, and disclosure of freshness metadata.
Compare scoped metadata acquisition with a body request under the same authority.
[Propagation scenarios](cutover-and-qualification.md#propagation-scenarios)

**Consumer scope (complete).** The demand query path; contribution scope and its readers
(facets, neighbourhood, interpretations, identity-exclusion comparison); selected math; demand
context; contextual selection; change impact acquisition; visual routing; rich reference;
interpretation authoring; the planner, execution and status frontier reads. Each is listed with
its call sites in the read investigation's census, kept in the SBX-00 baseline.

**Removes.** `append_page`'s stripping; the five copies of the use-to-product loop; the Python
mirror of input support matching; member expansion and filtering over whole bodies in
`demand_query_projection`; the source catalog's acquisition per row, replaced by publication
headers in the outputs answer.

**Failure behaviour.** A request for a body the principal may not see refuses as today. A page
that cannot fit one row within its byte bound refuses, naming the row; with partitions the unit
is a block, not a product.

**Evidence.** For each migrated reader, its existing tests pass with expectations unchanged. The
outputs program, asked for members of one kind in one product, returns exactly those rows, in
keyset order, across a page boundary inside one obligation, the expected rows written by hand. A
principal without the evaluator universe is refused a protected body through each new program.
An input-support answer equals the native function's result for a fixture with both derivation
and original support.

<a id="sbx-12"></a>
## SBX-12 — Replay, export, cursor and cache

**Common analytics amendment · Scheduled · 2026-11-22.** Implement the frozen selected-review
archive as the first Parquet boundary using the typed relation and sealing contract above. This
package consumes the projection decision from the early pilot and the scoped authority interface
from SBX-11. The archive comparison itself follows its runnable proof, reference and export
prerequisites and remains scheduled after the SBX-09 cold root.
[Review I04](../../plan_improvement_reviews/set-based-execution-common-analytics_2026-11-22.md#I04)

**Owns.** The typed relation interface and its two backings; the export's relation list,
including partitions and proof rows; the manifest's per-relation digests; the detached verifier's
treatment of partitions (recompute each partition digest and the root) and of proofs (custody of
claims, with fingerprints recomputed from the captured release); the unified cursor; the cache
key; the transaction scope of readers.

Keep the freshness-aware first page and its exact pinned continuation distinct. Exercise a
selection advance between pages, authority loss during continuation, and detached replay of
the earlier authorized cut. The earlier cut and its captured interpretation stay exact. Only
the live acquisition establishes current authority and freshness.

**Decided here.** Whether an export may carry digests only for products no replaying reader
reads; the proposal is that the manifest names any relation carried without bodies, and the
verifier's identity guarantee for those products is stated as header-level.

**Removes.** `SelectedRecordIndex` and its SQLite store; the export's JSON-lines closure and its
SQLite spool; the six cursor schemes; the frontier stamp and the per-page frontier walk; member
rows of partitioned kinds from the export.

**Evidence.** The structural review's export, verification and replay reproduce a byte-identical
response from typed relations, online and offline, on the existing fixtures. A verifier given an
export with one altered partition body refuses, naming the partition. A cached answer is served
after an unrelated revocation and after a fresh cut, and is not served after a revocation that
affects a product it read; in every case the per-call authority check ran, asserted by counting.
A reader's trust locks are released before its Python derivation begins.

Extend that evidence through selected structural export, immediate replay and a later reopened
verification. Include a dossier larger than the present derived-row cache can retain. Compare
independently expected selected answers through all five relation access shapes online and
offline. Include an authorized empty relation, private and withheld leaves, schema or ordering
mismatch, altered digests and truncated files. Interrupt before manifest sealing and after sealing,
then restart through the real archive publication route and verify its completeness outcome.
Check that compression or row-group changes preserve logical answers and identities. Reuse at a
live cut still acquires authority, while detached replay of an earlier authorized cut keeps its
captured interpretation after live selection or support changes. Move the independent malformed
input and semantic expectations with the replacement as JSONL, SQLite and duplicate closure
machinery retire. Timing is needed only if scans, memory or reread work can decide between
conforming routes.

Use authenticated artifacts for reader-only checks when their producer, wire, release and
captured authority premises still apply. Move malformed relation, digest mutation, independent
semantic and continued authority controls to typed replay with the retirement of SQLite and
JSONL. Exercise two current selections sharing one derivation and a transitive input from a
different demand. Interpret a published role-relative reference through its producing inputs.
Check current selected support through the live read boundary and verify captured conclusions
and establishment custody through the detached boundary. Include the protected issuer and
first matching proof cases.

Retain the native textbook condition as separate structural-read and export acceptance for
SBX-11/12. Confirm selected structural body acquisition and direct, CLI and MCP delivery within
the declared scope, and exercise genuine closure export and detached replay. A metadata-only
freshness result establishes its own access bounds. The recorded MCP timeout remains open
evidence for the structural closure path.
[Textbook condition and retained failure](references-and-projection-keys.md#sbx-05)

<a id="sbx-13"></a>
## SBX-13 — Evaluation preflight

**Owns.** The grade, fit and event plans' preflight. Each keeps the checks with no database
equivalent, which are the coordinate check against retained source text and the restricted-role
re-read that enforces the fitter's separation, and relies on the binding and the completion
guards for the rest.

**Consequence stated.** A fact the preflight used to refuse on is now refused at completion, by
the guard, after the kernel has run. That is a change in when a failure appears, not in whether
it does.

**Evidence.** For each removed preflight check, a fixture that violates the fact is refused by
the named completion guard. The coordinate check still refuses an authored coordinate whose text
differs from the source. No evaluation plan opens a second index.
Retain an independent coordinate expectation and a restricted-role refusal when the protected
reference cannot be followed. Move those checks with the evaluation readers as duplicate
preflight and the old index are retired.
