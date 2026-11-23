# Owner-resolved reads

**Status:** Proposed. Companion of [Set-based execution](../set-based-execution_2026-11-21.md).
**Created:** 2026-11-21.

This companion owns the read side: what a reader may ask PostgreSQL, what the replaying readers
carry, and how answers are paged and cached. It owns SBX-11 to SBX-13. The early typed item/read
slice is carried by the replacement SBX-09 root. The general read program and archive work retain
native revision B ownership. Source facts are **Inspected** at `7a415d18d`. The common analytics amendment
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

<a id="columnar-selected-read"></a>
## Typed selected access and replay

**Selected planning target · Proposed · 2026-11-22.** The
[columnar redesign amendment](../set-based-execution_2026-11-21.md#columnar-redesign-amendment)
selects a guarded keyed and bulk read slice before SBX-09 qualification. It consumes the
[stored item relation](populations-rules-and-proofs.md#typed-item-admission) and the
[typed reference/binding contract](references-and-projection-keys.md#columnar-reference-and-binding).
The general answer programs, freshness/cursor work and complete archive retirement remain with
SBX-11/12. The operator accepted the revised population-bearing wire boundary on 2026-11-23.

**One source for two access shapes.** A point access authenticates the actual producing role,
selected use and parent, then reaches the declared item key through the native index. Fetch only
its required content and authority premises. A finite bulk request selects the authorized item
relation before tagged envelope construction. Its row schema is the model-derived projection,
with canonical item text where logical identity requires it. Member envelopes carry common context
once and expose typed reference rows. Derive binding rows once per read scope. Cached content and
stored digests may avoid reconstruction, while each actual use rechecks current authority and
required support. Reacquire completeness for absence answers and distinguish an undisclosed
parent from an absent item.

**Columnar extraction.** Choose the transfer route by pin visibility and session ownership.
For a committed pin with a purpose-granted projection, the companion export's pattern keeps
the authorizing PostgreSQL transaction alive, imports its snapshot into an owned ADBC PostgreSQL
1.13.0 session and consumes eligible unparameterized COPY-compatible projection SQL with
`fetch_record_batch()`. Keep same-session Psycopg extraction for uncommitted or
session-local state, including staged archive keys. ADBC bound results use a different native
buffering path, so the reader interface alone establishes no memory bound. Deliver typed
batches to their actual consumer or `ParquetWriter`. Preserve purpose-role, schema, cut and
cancellation ownership through reader close and transaction settlement.
[Transfer contracts](common-analytical-basis.md#postgresql-placement-and-transfer)

**One relational replay.** SBX-12 scans Parquet under [verified file custody](#sbx-verified-archive).
DuckDB 2.0.0 supplies anti-joins, `EXCEPT ALL`, grouped counts and explicitly ordered digest
aggregation for closure, membership and identity. Carry original producing bindings and
captured cut evidence. Both live and detached inputs feed the same structural projection
contract. Remove the selected SQLite index, JSONL-to-index reconstruction and per-product
lookup loops when their replaying consumers have moved. Keep the canonical fold where it is
required for content commitments.
The early SBX-09 slice migrates its authentic finite/rich export and replay consumers; completing
that slice establishes its declared scope, while the remaining archive consumers stay open.

**Publication and verification.** The manifest seals the full relation file set, schema,
logical commitments, selected scope, lineage and authorized empty relations. Choose Parquet
sorting and row-group layout for the requested keys, then verify actual pruning only where it
could affect the layout decision. Existing probes establish filter/projection plan evidence.
Exercise a missing item in a valid partition, two producer-local positions, duplicate references,
revocation after cache warming or between pages, concurrent commits after snapshot export,
malformed canonical/projection pairs and an interrupted archive publication. Preserve authentic
finite and rich replay under the [replacement qualification sequence](cutover-and-qualification.md#columnar-cutover-sequence).

## Target

**A small family of programs behind one boundary.** Each calls the shared read-currency and
authorization steps and shares the scope, walk and output projections.

| Program | Answers | Replaces |
|---|---|---|
| Frontier (existing) | The cut, obligations, uses with their output references | Unchanged in role |
| Outputs | For uses in scope: derivation, request operation, output role and position, product or member with kind and context, body on request; filtered by kind, member or address, record type; keyset-paged over output position and member or partition | Stripping and rebuilding the join; member filters after the fact; one-obligation paging |
| Partitions/items | For an authorized product and collection: partition metadata, indexed item addresses, or selected typed rows and field groups in declared order | Whole-partition hydration for point references and JSON expansion before bulk transfer |
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

The response page budget covers delivered rows and bytes. The separate
[examination bound](#sbx-address-led-reads) covers the work needed to find those rows.
For a structural point read, use the exact
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

A queued item at the immediate consumer is one sign of pending work. Coverage includes committed
upstream changes whose propagation has yet to reach that consumer. A branch that settles unchanged
can advance coverage without a new provider attempt. Independently covered scopes stay readable.
Use the exact qualified dependency scope prepared by SBX-06 for both paths. The current path
evaluates settlement on that scope and the selected generation. The explicit `last-settled`
path checks current trust and disclosure for the captured settled cut without deriving new
readiness. Later changes to current settlement eligibility leave that historical cut readable
while current authority permits. An unchanged coverage determination can be reused only when
its exact scope, generation and authority correspondence survive and the read receipt still
accounts for the individual acquisition. Scope, selection and leaf disclosure rules also apply
to freshness metadata, including pending work that could reveal a protected dependency.
[Push-propagation review I04](../../plan_improvement_reviews/set-based-execution-push-propagation_2026-11-21.md#I04) ·
[Post-SBX-09 review I08](../../plan_improvement_reviews/set-based-execution-after-sbx09-deep-review_2026-11-23.md#I08) ·
[Disclosure owner](../../adr/0147-sbx-owner-resolved-reads.md)

**Online readers ask; replaying readers carry.** A reader with no offline entry point asks for
the shape it needs and decodes bodies. The structural family and export verification keep one
implementation over the raw relations, run from PostgreSQL rows online and from the export
offline. The end the replay serves is that someone without the database can confirm a served
response follows from the exported closure; one implementation over two sources is what carries
it.

<a id="sbx-acquired-reader"></a>
### Shared acquired reader

Derive relation schemas under the
[common projection contract](common-analytical-basis.md#projection-contract). Replaying readers
use one interface with keyed get, children by foreign key, filtered scan, embedded reference,
and whole-relation iteration. Its live backing acquires rows through the scoped native read
owner, while its detached backing reads from verified archive custody. Preserve canonical
encoded body fields wherever their exact value forms need that representation. Both backings
feed the same structural projection and reference interpretation with the captured producing
bindings, exact selected use, cut, frontier, protected issuer standing and authorized evidence.
Keep missing, withheld and incomplete relations distinct. A detached read interprets captured
standing. Each live acquisition applies native purpose and authority checks.

Bring forward the SBX-12 interface and its first two-backing slice for a protected issuer with
selectable ordinary report support. The slice establishes the acquired relation contract for
SBX-11's remaining consumers and SBX-13 before the general archive migration finishes. Migrate
protected structural admission, source journeys, selected math and contextual witnesses as they
can consume the scoped facts. Online-only consumers continue to use native answers. Compare
independent live and detached results for the two uses of one historical producer and move
refusal and malformed-input expectations with each migration.

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

**Finite acquisition phases.** Acquire only the authorized addresses, headers, provenance and
bodies needed by the next phase. Commit the read receipt and release the transaction and trust
locks before pure derivation. When derivation discovers another key, acquire a new finite batch
under the same pinned cut with current authority. A live stream that needs its transaction owns
it through close, refusal or cancellation. Verify early stop and consumer exception, including
receipt and lock release. Exercise explicit empty and incomplete cuts, partition field projection
and missing item keys, and proof fingerprints, premises and establishment provenance.

**Change impact.** Replace the full support exports and SQLite reconstruction before the cache
lookup with typed selection and coverage headers, exact producing and current-use edges,
closure/membership and scoped revocation facts for each cut. Compare the acquired relations
with DuckDB joins, grouped counts and anti-joins where these replace repeated reconstruction.
Hydrate bodies only for explanations that need them. An unchanged comparison can check its
determining facts and authority without payload acquisition. Exercise equal-content membership
changes, repeated occurrences, incomplete discovery, upstream revocation and an unchanged repeat.
[Post-SBX-09 review I02](../../plan_improvement_reviews/set-based-execution-after-sbx09_2026-11-23.md#I02) ·
[Post-SBX-09 review I09](../../plan_improvement_reviews/set-based-execution-after-sbx09-deep-review_2026-11-23.md#I09)

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
and a revocation that did not touch what was read. Each call establishes current authority on
the exact context and facts it uses, including body access for payloads it returns. This
replaces the whole-frontier recheck. An answer that depends on the validity of its support
includes that in its per-call check. For an answer about proof absence or completeness, a cache
hit must also establish current membership in the relevant proof and establishment relations.
Bypass answer reuse for that shape if current membership cannot be established from scoped reads. A new
matching proof can change that answer with the same content digest and rule fingerprint.
Coverage and authority are established by the native read even on a semantic answer cache hit.
[Shared change scenarios](cutover-and-qualification.md#change-scenarios) ·
[Continuation authority](../../adr/0141-serving-continuation-and-reuse.md)

*Alternatives rejected.* Extending the one program with every view and filter: one closure
digest, so every addition invalidates every receipt, and the meaning of `limit` splits further.
Keeping the index for online readers with cheaper lookups: leaves the rebuilt joins in place.
Answer-shaped programs for the replaying family as well: two implementations of the same
projection, which is what makes replay meaningless.

<a id="sbx-11"></a>
## SBX-11 — The read programs

**Early scalar slice · Proposed replacement · 2026-11-22.** SBX-11 owns the scalar construction
caller and its transition from guarded parent/partition reads to
[indexed item access](#columnar-selected-read). The earlier registered-root plan made an
interim correction conditional on a reproduced bound failure and native attribution. The
typed replacement supplies its keyed path as a direct consumer of the physical redesign.
Its final contract must remove full-closure preparation, work within
the normal 8 MiB examined bound, and preserve producing input, exact current use, occurrence,
multiplicity and withheld-versus-absent behavior. SBX-05 supplies that caller's reference and
occurrence contract. Reuse the acquired cut and authorize each lookup. The fork's 64 MiB
scoped result and the textbook's separate 32 MiB experiment retain their original evidence scopes.
[Post-pilot I03](../../plan_improvement_reviews/set-based-execution-through-sbx09_2026-11-22.md#I03) ·
[SBX-05](references-and-projection-keys.md#sbx-05)

<a id="sbx-live-summary-correction"></a>
### Early summary correction

**Scheduled · 2026-11-22.** Deliver the existing characterization metadata response with the
SBX-08 admitted-page handoff before broad qualification resumes. This correction has its own
acceptance and proceeds independently of the conditional scalar slice. Read bounded summary
metadata from the authorized admitted nominal body, omit both `body` and `meaning_body`,
and retain the archived kind filter, provider attribution, exact selection and summary response
schema. Retire the repeated whole-body Python validation on this admitted route after the
handoff's admission-parity checks establish its guarantees. Raw and detached ingress retain
their owning validation. [Efficiency review I01](../../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md#I01)

The isolated summary units passed at their original scope (`4b62418035d8469f929a1cfde9ccb8d2`).
The native attempt returned the summary and then failed an old partial-result assertion
against the recognized complete fixture (`3adb62f740974af0b243b45161c9e265`).
Verify the actual fixture's complete outcome, nonempty coverage with its available families
complete or empty, exact product and derivation, and summary counts independently. Keep authored partial and
unknown fixtures and assert omission of both payload fields without mutating the acquired input.
The isolated live-page 78-case result establishes feasibility and remains subject to final-source
qualification. [Shared qualification](cutover-and-qualification.md#sbx-efficiency-qualification)

<a id="sbx-native-read-attribution"></a>
### Native read attribution and selection

**Scheduled investigation · 2026-11-22.** On one stable installed source, compare fresh cut
acquisition, the first whole-body page, continuation, same-budget repeat, lower-budget repeat,
and an exact member among unrelated members. Compare the cold bounds with reuse on the
warm route. Attribute scope acquisition, body examination, JSON assembly and serialization
separately from client processing. Use database-scoped `pg_stat_statements` deltas and waits,
then targeted nested `auto_explain` for unresolved branches, with redacted parameters and a
separate ordinary baseline. PostgreSQL 18 `EXPLAIN (ANALYZE, BUFFERS, SERIALIZE TEXT, FORMAT JSON)`
can isolate output conversion for a suitable bounded query. Its serialization measure excludes
network transfer. The outer event plans and small scalar read leave the expensive nested cause
open. [Efficiency review I02](../../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md#I02) ·
[PostgreSQL 18 EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)

Compare existing `acquire_data_read_context`, addressed reads and one prepared same-cut binding
batch before adding a new read shape. Reach the authorized key before opening or serializing
the parent where the contract permits. Reuse examined facts only within their exact scope,
representation, budget and authority lifetime. A stored length must measure the same immutable
encoded representation and framing that the refusal uses. Preserve fresh native authorization
on cache hits, lower-budget refusals, exact cursors, ordered placement, denial after revocation,
and absent-versus-withheld standing. Include equal-content members with different exact producing
uses. A digest or context-only acquisition supplies only the
facts its contract establishes.

Record the selected correction or partial attribution with the missing observation and revisit
condition. Keep residual timing-driven work conditional on material cost in the route that will
survive the replacement. The early keyed path remains a required consumer of the proposed
replacement; the full keyed reader migration remains in this package. An inconclusive
optimization inquiry leaves failing required identities open under the cutover owner.
[Coordinator amendment](../set-based-execution_2026-11-21.md#validation-postgresql-efficiency-amendment)

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
that cannot fit one row within its byte bound refuses, naming the row. Typed item reads enforce
row and byte limits before hydration; partition metadata retains its own access shape.

**Evidence.** For each migrated reader, its existing tests pass with expectations unchanged. The
outputs program, asked for members of one kind in one product, returns exactly those rows, in
keyset order, across a page boundary inside one obligation, the expected rows written by hand. A
principal without the evaluator universe is refused a protected body through each new program.
An input-support answer equals the native function's result for a fixture with both derivation
and original support.

<a id="sbx-address-led-reads"></a>
### Address-led paging and references

**Scheduled · 2026-11-23.** Start each output, partition, derivation-fact or proof read from
an indexable address in the pinned cut. For outputs and members, use the exact selected use
and physical output/member coordinates. Apply safe scoped filters before fetching payloads.
For routine `record_type` or `family` filters, consider compact admission-derived classification
only when the declared kind supplies the field and the same kind and leaf disclosure rules
cover it. Otherwise retain exact classification within the bounded candidate work.

Resolve validity and disclosure over bounded candidate windows, then hydrate and serialize
deliverable rows. Continue past ineligible candidates within the examination bound. Account
separately for examined work, delivered rows and bytes, and retained buffers. Keep the examined
position internal and make the public continuation safe for hidden membership. Distinguish
authorized exhaustion, withholding and a work-limit refusal. An oversized selected row still
refuses before transfer. Current authority applies on continuation, cache reuse and reopening.

Batch exact references by original producing role and selected use in a typed ordered Arrow
request/result relation. Preserve request ordinal and multiplicity through every join. Share
authorized immutable payload for repeated addresses within the same acquisition and purpose.
Use the existing [attribution route](#sbx-native-read-attribution) to separate acquisition,
validity and serialization costs. Verify a deep page with unrelated support and members in
the same obligation, an oversized body outside selected keys, equal payloads with distinct
producing uses, a reduced budget and revocation between pages. Reuse the independent expected
rows and distinguish withheld proof from absent proof when matching membership first appears.
[Post-SBX-09 review I01](../../plan_improvement_reviews/set-based-execution-after-sbx09_2026-11-23.md#I01)

### Development checkpoint and remaining scope

**Implementation checkpoint · 2026-11-23.** The development source declares the four
answer programs and their shared read-closure membership. The member query uses a native seek
key and checks current authority on each page. Ordinary contribution and structural consumers
use native output, derivation and reference answers. Source-view catalogs acquire projected
source and selector metadata. The governed query supports a current named selection and an
explicit last-settled cut. Covered historical reads retain their exact generation and repeat
current trust and dependency disclosure checks on reopening.

**Development installation · Tested · 2026-11-23.** The preview
(`9d6c6eee992b434b9a94d84e747a97c5`), rollback-only candidate (`ff291f4e0cca42b19fa6879450d9edb8`) and registration
(`d4c7ffbd4a954b2f85a4c45e8979847d`) passed. `uv run ci model change deploy
ff291f4e0cca42b19fa6879450d9edb8` installed `semantic_sbx_selected_answers` on the dedicated
development database (`ae746537aaf145bbb84e75b1b230998b`). Maintenance readback confirmed
it is both the installed revision and registered head. The managed repository checks
(`b9e25a288a2a4359a2d82fbbcf8df006`) and all 37 focused cursor, governed ingress,
contribution-input and source-catalog checks (`82e902b9f05145d2925f1f6f903ad226`) passed.

The first private native run (`e75664f16c1e4b6592b0e25d63fd6d51`) passed two tests and
failed two. The governed reader rejected valid optional wire fields. The outputs fixture
stopped during producer preparation because the captured callable source exposed a generic
span class to the closed runtime inspector. The correction uses the generated wire contract
for request shape, checks only the program's required selectors, and keeps the span class in
producer execution custody. The immediate retry (`e68191f9f7454ce28ff1477372fcafd6`) stopped
because the changed source expected the new kernel. The guarded successor was then authored
(`f6ec27aa156e4be7869897126bd56257`), registered (`81f10d769bcd472fad3bcebc019b3a7b`),
and installed on development (`cab4a94b4bb64ba2931180aa39e3cb50`). Maintenance readback
confirmed `semantic_sbx_answer_guards` is the installed revision and registered head.

**Native and consumer checks · Tested by selected identity · 2026-11-23.** The guarded private
run (`1a8d1fa595024d93bbb4d7b3649c712f`) passed the scoped settlement cases, including pending
work, exact last-settled history and revocation, and the detached export regression. The
filtered outputs fixture still stopped in producer preparation. Using a plain runtime span
class resolved that failure. The next private run (`ed64bfb189254f52babc0ae9dfe08414`) passed
all nine selected filtered paging, contextual acquisition and span checks. Contextual product
acquisition uses the native output address and retains exact producing-use proof. Its later
witness acquisition still requests transitive support. The live `ci query members` CLI returned
`Unknown` for an absent governed selection under `--last-settled`. The final repository
check passed (`991db62ae0f54113adfef509b0353eee`). The populated native fixture then passed
filtered paging and derivation-fact parity against the recorded binding and exact formal
producer use (`64975a9001414921be232c776bd8dfc2`).

**Remaining at this checkpoint.** Protected structural admissions, complete source journeys
and full graph inspection needed their existing support custody. The PDF publication catalog
called the guarded header reader per result. The non-output programs narrowed support
acquisition to the anchoring obligation, with additional related support still traversed before
filtering in some point queries. The [successor below](#sbx-qualified-reads-checkpoint) records
the subsequent acquisition changes.

<a id="sbx-qualified-reads-checkpoint"></a>
### Qualified reads development checkpoint

**Installed · 2026-11-23.** The typed preview `abb9d01b18134ded87c7fab00f889e24` and
rollback-only candidate `904350b9213a44599bad41c2e4c82889` passed against
`semantic_sbx_answer_guards`. The candidate contains 75 native operations and one ordinary
operation, with no privilege changes. Registration passed (`f23202e30b0440a6b9ccb711203a30e6`).
`uv run ci model change deploy 904350b9213a44599bad41c2e4c82889` installed
`semantic_sbx_qualified_reads` (`d077b3180afc4384b0a73751b369becf`) and maintenance
readback confirmed the same registered head. This establishes development installation.

**Tested by selected identity · 2026-11-23.** Two serial focused cohorts (`uv run ci test
--workers 1`) passed 22 custody, archive-manifest and governed-read checks
(`dea2454c2bfe406c8bb140e3145e2baf`) and 37 selected archive, reader, cache and CLI checks
(`e8b001c5b8124624a28aad8551b8e134`) before the subsequent serving integration.
The initial source-capture failure (`9e27ddc288bf49f4be2656436e65dd5e`) and the later fixture
failure (`67d84e84e93c4dfa8b02aeaf0b5bd94c`) retain their failed scope. The first private serial
cohort (`8309fbf3a24648498f4dc84d7d8ac5e1`) passed analyzed-scope selection and authorized
historical freshness, and filtered output paging within one obligation. It failed on nested
Parquet field naming and an explicit frozen source set in the installed math fixture.
After the serving integrations, `uv run ci test --workers 1` passed all 135 selected archive,
cursor, source-catalog, structural reader and runtime custody checks
(`86fb6e86e1224ec6b2d635904b511199`). Its predecessor (`29ac37d6f47940f6bb85cf6282a2c012`)
passed 101 cases and retained one obsolete test expectation about analyzed-scope support.
The later compact cursor and replay cohort (`3e874af324a74887a904088e37417834`) passed 143 cases.
Two detached fixture cases omitted the required output position and passed on the follow-up
contribution-reference cohort (`d92ce4665794426cb6b55804ab07cca9`, 16 selected).
The private serial textbook condition (`63e50273bf3c489fa49e59a0e8c8a325`) passed direct,
installed CLI and stdio MCP reads of the same selected assertion. Its independent switched-role
and unprivileged publication controls refused as expected.

**Implemented · 2026-11-23.** Qualified coverage follows observed dependencies with exact
source and analyzed-context selection. Current reads and independently authorized historical
cuts retain separate criteria. Outputs choose bounded physical candidates before hydrating
deliverable bodies. Point partition and proof reads narrow their validity seeds. Structural,
contextual, math and graph consumers use shared acquired support, with graph derivation outside
the acquiring transaction. Change impact uses one compact support-fact acquisition. The PDF
publication catalog retrieves guarded receipt and metadata batches under the selected cut.
Structural artifact navigation submits ordered Arrow coordinates after resolving each original
producing occurrence. The existing guarded member program establishes each distinct exact
address under the cut, then the caller restores order and multiplicity within the acquisition.
The private cross-work artifact fixture (`a4b3fe95e36b4ef9b05540443a625b5e`) passed the live
navigation path and established PDF catalog header parity against the installed scalar reader.

**Open.** Other exact-reference consumers still need migration. Native physical examination and
lock cost remain partially attributed. Readers that borrow lazy population items retain the
acquiring transaction through their use. Independently pending analyzed siblings, cross-source
role correspondence, protected partition and proof coverage, and combined installed read
acceptance retain their individual evidence requirements.

<a id="sbx-12"></a>
## SBX-12 — Replay, export, cursor and cache

**Implementation checkpoint · 2026-11-23.** New v4 exports write model-derived typed Parquet
support, population and proof data. Existing v3 JSONL closures enter through a read-only
adapter. Detached replay authenticates an owned copy, checks complete native page order and
the terminal boundary, and uses scoped Arrow scans. Structural replay charges logical
records and bytes under its examined budget. Staged files and DuckDB sort scratch retain
their existing store bounds. Demand, dossier, gap, contribution, rich, comparison and
source-catalog continuations use compact pins and the shared codec. Native demand continuations
carry positions and governed generation while reconstructing scope from the explicit request.
Dossier presentation reuse establishes the current root and reference authority first.
Wider substantive reuse, custody and integrated replay remain open.

**Tested by selected identity · 2026-11-23.** The private serial native export retry
(`ba8f7c5fe16e4d5fa52d82ab6426f4e6`) passed typed episode closure, detached identity and altered
fragment refusal. The Parquet writer preserved the declared Arrow nested field names and nullability.
The extended private textbook case (`3d3b20e1fbc74494ac162c0f0f60cc9a`) passed direct, CLI and
MCP delivery, sealed its v4 structural review at the same cut, and reopened its exact published
admission from captured custody.
The candidate-conditioned D1 journey (`8120aa4120464a28a6dd3e1dc499533d`) reached genuine provider
execution and sealed the v4 archive in 4.7 seconds on the selected fixture. Detached traversal
then stopped because the verification budget wrapper lacked the exact item-read method. The
wrapper now forwards exact item references through the authenticated population reader. The
original failed result remains part of the acceptance history.
`uv run ci review verify` then passed on the retained v4 archive under its explicit manifest
digest. Direct replay with the same authenticated reader checked all 179 contextual member
addresses against the original input ledger. On that replay, cold verification took 36.2
seconds and reference expansion took 0.87 seconds.

**Candidate-conditioned D1 · Tested and measured · 2026-11-23.** `uv run ci test
--native-host private --providers-only --workers 1` passed the genuine provider, exact selected
export and detached contextual replay journey (`2e02f08907f24c36986694cc84b09cd1`) within the
existing 15-minute watchdog. The test call took 468.7 seconds. Native setup took 238.5 seconds,
provider execution took 185.4 seconds, and selected export took 4.8 seconds. One support stage
took 0.62 seconds and 28 support fetches took 0.43 seconds in total. Detached verification and
exact replay took 35.5 seconds. These measurements cover this fixture and execution context.

**Native archive acquisition pulled forward · 2026-11-22.** Stage the finite authorized support
keys once under the pinned export transaction. Use the shared support membership and disclosure
rules, omit live validity explanations and hydrate bounded key windows. Support row capacity is
independent of result pagination and the existing byte ceiling applies to each support reply.
Qualify exact v3 replay on the private installed target and rerun the candidate-conditioned D1
journey while preserving its watchdog and retaining phase timings. Carry native installation
through the existing revision sequence. [ADR-0152](../../adr/0152-selected-archive-support-keys.md)

**Native archive acquisition · Tested · 2026-11-22.** The exporter stages support once and
hydrates up to 64 ordered keys per call. Native controls cover exact support equality, both
archive encodings, byte-limited advancement, empty cuts, scratch custody, and failed publication.
The final scoped `uv run ci test --native-host private` coverage is 13 selected cases across
`a19ca8823e624cbb9d779def25b16fbd` and `d325c030f8f24381b20a2f1c8649559b`. Only the byte-limit
test changed between these runs to calculate its threshold from the PostgreSQL wire envelope.
The protected structural export, detached replay and live revocation journey also passed
(`9d00d2be3d644ff7a57ce2f432ca1e72`). `uv run ci model change candidate` passed rollback-only
authoring against registered N47 (`fd6adbce6be64948a704e3d3a94f4014`, preview
`1f4bbad70cf648199e9ffeec1aaa812b`).

The first provider retry (`0c37729f30714ab398a0fbf2799d75b8`) sealed the D1 archive and reached the
watchdog in detached member verification. Verification now decodes each parent once and checks
its indexed members together, preserving the captured schemas, context and exact packet equality.
Standalone `uv run ci review verify` passed on that sealed archive in 89 seconds. The 52 selected
`uv run ci test` detached result and manifest controls passed (`47bf7dbb2e314643b2c5fc75902ea74b`).
The final source passed all 14 selected installed archive and whole-read controls
(`1e92211b89504cd7b39096a3ad974158`).

**Candidate-conditioned D1 · Tested and measured · 2026-11-22.** The private
`uv run ci test --native-host private --providers-only` journey passed under the existing
15-minute watchdog (`4578a734f8e04db69e4918c5687025d9`). The test took 830.1 seconds. Setup
took 319.8 seconds and provider execution took 297.8 seconds. The export took 23.2 seconds,
including one 10.6-second support preparation and 26 fetches totaling 0.45 seconds. Detached
verification and exact contextual replay took 163.0 seconds. Timings cover this fixture.

**Residual replay work · Measured · 2026-11-22.** A timed pass on that same sealed archive
observed 78 seconds of detached verification. Of those, 40 seconds were spent in 360 full-record
product lookups over a closure containing 13 products. Contextual expansion then took 83
seconds, with 78 seconds in 358 product lookups for 179 exact references. File checksums took
0.12 seconds.

**Prepared replay · Tested and measured · 2026-11-22.** The verifier reuses authenticated product
headers for closure links, and contextual replay prepares the exact use and slot bindings once per
declared path. The same sealed D1 archive verified in 35.0 seconds with six full-record product
lookups. Contextual expansion took 0.13 seconds with one full-record lookup and recovered all 179
captured member addresses. The measurements cover offline replay of the retained archive.
The 86 selected `uv run ci test` detached, authority and reference controls passed
(`4bcf7cdb1b0a4a378b64760e0b9a1605`).

**Common analytics amendment · Scheduled · 2026-11-22.** Implement the frozen selected-review
archive as the first Parquet boundary using the typed relation and sealing contract above. This
package consumes the projection decision from the early pilot and the scoped authority interface
from SBX-11. The archive comparison itself follows its runnable proof, reference and export
prerequisites and remains scheduled after the SBX-09 cold root.
[Review I04](../../plan_improvement_reviews/set-based-execution-common-analytics_2026-11-22.md#I04)

<a id="sbx-verified-archive"></a>
### Verified archive scans

**Scheduled · 2026-11-23.** Reuse the existing export pattern
`pyarrow.parquet.ParquetWriter(path, schema).write_batch(batch)` on model-derived typed batches.
Close each writer, verify exact schemas, logical rows and file digests, then publish the complete
manifest. Cold replay authenticates the trusted manifest and exact files, verifies all required
bytes including omitted columns, and establishes logical closure, order and partition/root
commitments. Keep captured release preparation and cross-file verification for rereads only
while that exact acquired file set, schema, manifest and verification implementation still bind.

Extend the existing file-custody owner over all scan execution. Acquire an owned immutable
copy for mutable detached inputs before verifying and reading it. A held file may be hashed
and scanned through the same handle when the storage guarantees immutability. Reacquire and
verify if custody ends or the file identity is uncertain. A synthetic probe on PyArrow 26.0.0
and DuckDB 2.0.0 shows lazy DuckDB path reads can open a replacement after initial verification.
Arrow over the held original handle kept reading the original across that pathname replacement.
The held-handle result covers replacement only. In-place writes require an independent
immutability guarantee. Validate custody before delivering rows, and retain it through
early stop, refusal and release.
[Custody owner](../../../python/corpus-structure/src/corpus_structure/semantic/file_custody.py#L84) ·
[Parquet custody probe](../../design_review/evidence/2026-11-23_sbx-parquet-scan-custody/README.md)

**Pinned scan choices.** PyArrow 26.0.0 `ParquetFile(NativeFile).iter_batches(columns=...)`
or `read_row_group(..., columns=...)` projects held files. Where paths are under exclusive
immutable custody, use `dataset.Scanner` column projection and exact address filters for
single-relation reads, or the analytical owner's `from_parquet()` and DuckDB 2.0.0
`read_parquet()` for combined scans. Use admitted Arrow batches for local joins when the
path is unsuitable. Verify bag differences with `Relation.except_all()` or SQL `EXCEPT ALL`.
Open the manifest's exact file set with the declared schema. Sort by actual
product/collection/partition addresses and choose row groups for the mix of point and full scans.
The writer's `sorting_columns` records order that the writer input must already satisfy.
Use DuckDB `EXPLAIN` to check filter and projection placement. Investigate `write_page_index`,
Bloom filters or a side index only if sorted row groups leave a material selective-read cost,
and demonstrate benefit on the pinned reader before adopting. PyArrow 26 can write page
indexes, and its Parquet reader does not use them for filtering. Layout and compression can vary
while semantic keys, order and commitments remain fixed.
[Existing writer](../../../python/corpus-structure/src/corpus_structure/serve/companion_export.py#L196) ·
[Arrow Scanner API](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Scanner.html) ·
[Arrow ParquetFile API](https://arrow.apache.org/docs/python/generated/pyarrow.parquet.ParquetFile.html) ·
[Parquet writer API](https://arrow.apache.org/docs/python/generated/pyarrow.parquet.ParquetWriter.html) ·
[DuckDB 2.0 Parquet scans](https://duckdb.org/docs/2.0/data/parquet/overview) ·
[Post-SBX-09 review I03](../../plan_improvement_reviews/set-based-execution-after-sbx09_2026-11-23.md#I03) ·
[Post-SBX-09 review I10](../../plan_improvement_reviews/set-based-execution-after-sbx09-deep-review_2026-11-23.md#I10)

**Efficiency comparison.** Use the improved authenticated D1 replay with prepared headers and
use/slot bindings as the baseline. Keep staged `pg_temp` selected archive keys and their typed
batch extraction in the owning PostgreSQL session. Exported snapshots do not transfer that
session-local state. Reuse the companion export's ADBC PostgreSQL 1.13.0
`cursor.fetch_record_batch()` route only where a committed exact pin is visible in the imported
snapshot and the purpose-granted projection supplies the required rows. Compare the complete
authorized extraction, conversion, file authentication, cold reopen, index preparation and
repeated query. Use the existing analytical relation owner for semijoins, anti-joins, explicitly
ordered windows and `except_all` where they replace repeated scans. Consume a relation's `to_arrow_reader(batch_size=...)`
for streaming output. Verify that the selected route does not materialize every Python row before
returning the reader, and close readers on success, failure and cancellation.
[Efficiency review I06](../../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md#I06) ·
[Transfer and fidelity](common-analytical-basis.md#postgresql-placement-and-transfer)

Extend first replay and reopen acceptance to compare complete schema, selected cut, logical rows,
explicit ordering, null/presence and occurrence multiplicity independently of physical pushdown.
Verify the cold open and a reread under stable custody. Exercise pathname replacement and
in-place mutation before the first batch and during consumption, early close, changed omitted
columns, a partial or truncated file, empty relations and protected leaves. Assert that rows
come from the verified bytes or refuse, without accepting any changed bytes. Retain full
ordered replay with duplicates. The manifest owner retains publication and interruption recovery.
[Post-pilot I03/I06](../../plan_improvement_reviews/set-based-execution-through-sbx09_2026-11-22.md#I03)

Include mixed decimal precision and scale, a wider exact tagged lexical value, UTC nanoseconds,
and two independent equal-valued occurrences. Numeric columns use declared bounds supported by
the selected engine. Wider canonical decimal text retains transport meaning and requires an
exact compatible arithmetic route if arithmetic is requested. Compare with the shared
[numeric fidelity contract](common-analytical-basis.md#numeric-fidelity). An uncertain complete
path ends with an explicit adjust or retain decision and the evidence that would reopen it.

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

**Owns.** The grade, fit and event plans' preflight. Use the native binding facts and
[early acquired reader](#sbx-acquired-reader), independently of full archive completion.
Acquire finite immutable facts per exact reference, prediction and original-source cut and
purpose. Keep the reference demand separate from prediction and enforce the source role on
acquisition. Use Arrow bundles keyed by cut, use and provenance. Use ordered correspondence
joins or anti-joins in DuckDB where they remove repeated index reconstruction or event-frame
reopens within the invocation. Independent authored-coordinate checks and semantic scoring
retain their own expectations.

**Refusal timing.** Establish cheap deterministic input refusals once in native acquisition
before expensive evaluation where that boundary supplies the required facts. Keep independent
coordinate checking against retained source text and the restricted-role checks that enforce
the fitter's separation. Completion still checks mutable premises at effect time. Remove
duplicate checks only once their actual authority and failure timing are accounted for.

**Evidence.** For each moved check, show that a violating fixture refuses at the named
acquisition, evaluation or completion owner. Include equal payloads from different producing
uses, different releases, a protected reference unavailable to the permitted role and an
authored coordinate whose text differs from the retained source. Verify the native
deterministic refusal precedes expensive evaluation and the mutable refusal still applies
at completion. Migrate the independent controls with their consumers and retire the old
index and duplicate preflight when their last consumers move.
[Post-SBX-09 review I02](../../plan_improvement_reviews/set-based-execution-after-sbx09_2026-11-23.md#I02) ·
[Post-SBX-09 review I09](../../plan_improvement_reviews/set-based-execution-after-sbx09-deep-review_2026-11-23.md#I09)
