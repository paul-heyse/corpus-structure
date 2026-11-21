# Owner-resolved reads

**Status:** Proposed. Companion of [Set-based execution](../set-based-execution_2026-11-21.md).
**Created:** 2026-11-21.

This companion owns the read side: what a reader may ask PostgreSQL, what the replaying readers
carry, and how answers are paged and cached. It owns SBX-11 to SBX-13 and is carried by native
revision B. Source facts are **Inspected** at `7a415d18d`.

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

**Online readers ask; replaying readers carry.** A reader with no offline entry point asks for
the shape it needs and decodes bodies. The structural family and export verification keep one
implementation over the raw relations, run from PostgreSQL rows online and from the export
offline. The end the replay serves is that someone without the database can confirm a served
response follows from the exported closure; one implementation over two sources is what carries
it.

**Replay relations are typed.** The export already writes Parquet per relation from a captured
Arrow schema. The replaying readers read typed relations through one interface with the five
access shapes they use (keyed get, children by foreign key, filtered scan, embedded reference,
whole-relation iteration), backed online by rows from the support program and offline by the
export's files. Tagged bodies stay JSON text inside those relations, since Arrow cannot hold
their value forms exactly, and the cut and frontier bytes stay retained bytes. The custody end of
"same bytes as acquired" is served by a digest per relation in the manifest. The SQLite index of
JSON blobs and the second copy of the closure as JSON lines are retired.

**Carrier today.** Typed relations in process as Arrow tables; set work over them where a
replaying reader needs a join, through the analytical owner; keyed access through an index built
once per relation. The need is "typed relations with five access shapes from two sources"; if
point lookups remain dominant after online readers leave, a dictionary index is sufficient and
DuckDB is not introduced here.

**One cursor.** Version, implementation identity, selection digest, cut, and a position that is a
keyset where the data is row-addressable and an ordinal where rows are derived. Clients do not
see native keysets.

**A substantive cache key.** Implementation, selection digest and the digests of what the answer
read: product body digests, partition digests, rule fingerprints. The key survives a fresh cut
and a revocation that did not touch what was read. Authority is never cached: each call performs
the context-only authority check and body access for the products it returns, which replaces the
whole-frontier recheck. An answer that depends on the validity of its support includes that in
its per-call check.

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

**Owns.** The outputs, partitions, derivation-facts and proofs programs; their disclosure checks,
which restate body access, kind disclosure and leaf masking per row returned; their wire records;
the membership of each in the read closure; migration of every online-only reader to them.

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

**Owns.** The typed relation interface and its two backings; the export's relation list,
including partitions and proof rows; the manifest's per-relation digests; the detached verifier's
treatment of partitions (recompute each partition digest and the root) and of proofs (custody of
claims, with fingerprints recomputed from the captured release); the unified cursor; the cache
key; the transaction scope of readers.

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
