# Operation reuse and recoverable completion

**Status:** The bounded implementation and qualification are complete. Recovery ordering, draft retirement, changed-request uptake and fresh PDF attribution passed. N35 is active on the bounded stage. UDM-20 owns regional confirmation.
**Created:** 2026-11-18.

This companion owns **UDM-25**, the recoverable completion and compatible PDF checkpoint
amendment from [review I02 and I03][review]. The [coordinator][coordinator] owns package state,
the execution queue, scheduled finding disposition and the shared contracts. Production and
admission identities belong to [UDM-09–12][programs]. Current support, validity and discovery
closure belong to [UDM-05–07][validity]. This document consumes those contracts and specifies the
private handoff and adoption work which makes them effective after interruption.

**Baseline and evidence.** The source review examined `3726a5cb6`, with production baseline
`5139eaba3`. The decisive completion, claim-lifetime and PDF spool sources were re-read at
`929124ae5`; those files have no changes from that production baseline. Their observations below
are **Interface-checked by source inspection, 2026-11-18**. Historical receipts and outcomes are
attributed to the review and [qualification companion][qualification], rather than re-executed.
Every target and expected benefit below is **Proposed**. Module paths are relative to
`python/corpus-structure/src/corpus_structure/`; test paths are relative to
`python/corpus-structure/tests/`.

## Purpose and boundaries

An operation whose material inputs and result-affecting implementation have not changed should
be able to use its authentic work after an orchestration change or downstream failure. Three
states need different treatment. A completed derivation uses existing native attachment and
current validity. A committed completion intent uses exact reconciliation. An expensive completed
computation which has not committed an intent needs a recoverable private handoff. PDF pages
acknowledged by an earlier producer need an explicit compatibility decision before they can
contribute to a successor build.

UDM-25 delivers the last two capabilities for the demonstrated PDF and sentence boundaries.
It adds no general workflow scheduler, arbitrary Python return archive or remote cache. The
native completion owner continues to decide publication, support and claim effects. A private
draft and a page checkpoint are neither completed products nor reusable execution failures.
The process host continues to own resource lifetime and physical retirement. [UDM-13/14][cache]
owns expendable caches, whose pruning cannot remove acknowledged recovery material.

This boundary addresses the failure amplification identified in I02/I03. Saving a bounded
completion once can avoid repeating recognition or sentence computation when only settlement
failed. Narrow compatible page uptake can avoid restarting acknowledged page work after a
successor release or request generation. Those benefits depend on proven compatibility and
available evidence. They establish no timing or capacity claim and promise no reuse across
arbitrary PDF edits.

## Entry baseline before UDM-25

| Existing owner | Source fact and consequence |
|---|---|
| `orchestrate/data_operations.py`, `_retain_answer` | Checks output witnesses, builds typed completion meaning, binds actual execution evidence and enforces reply/draft bounds before calling native intent retention. Until that call commits, the completion can exist only in memory. |
| `semantic/data_completion_settlement_native.py`, `_intent_settlement` | Checks the original claim, runtime, inputs, support and completion correspondence before the durable intent insert. A known rollback can leave no intent. `adopt_data_completion_intent` accepts an unresolved exact-generation retained intent, rather than an arbitrary answer. |
| `semantic/claim_lifetime.py`, `_transact` | Serializes renewal and settlement. It can replay certain connection/IO failures during commit, while a known statement interruption is a different outcome. The unresolved completion callback is retained in process. It is not a process-exit recovery store. |
| `ingest/pdf_build_spool.py`, `PdfSpoolProducerBasis` and `PdfSpoolPremises` | The determining basis includes request, generation and release as well as recipe, implementation, profile and PDF domain. The premises also compare source, native/payload schema, assets, packages and page selection. Narrowing UDM-10 identities alone therefore leaves cross-generation or cross-release pages ineligible. |
| `verify_spool_recovery`, `clone_recovery_entries` | Recovery acquires the original writer lock, checks files and manifests, and clones selected verified material while retaining original contributor association. A live writer refuses uptake. Lease expiry or a PID check cannot replace physical retirement. |
| `ingest/pdf_candidate_source.py`, `ReplayCandidatePageSource`; `semantic/pdf_staging.py` and `pdf_staging_native.py` | Selected page batches and acknowledged replay keys already provide uptake units. They are the integration route for retained pages, rather than whole-book candidate rehydration. |

The review records SQLSTATE `57014` during the book's retained-intent insert. It establishes a
concrete pre-retention exposure, without establishing that every timed-out attempt lost its
answer. N27's reduced hashing and N28's committed-intent adoption remain useful. The early
UDM-20 diagnosis distinguishes their coverage from the remaining failure. It preserves the
original failed/interrupted receipts and establishes the last durable boundary for each selected
case before drawing conclusions.

## Shared contracts consumed by UDM-25

UDM-10 supplies the complete material production basis and original implementation/archive
custody. It separates result determinants from current admission and original provenance.
UDM-25 never treats release equality, a content digest alone or a caller's compatibility flag as
that proof. A target request may admit prior work only through native authenticated
correspondence to its operation, exact input/support binding, logical context, parameters,
selection, output contract and replicate. An unknown determinant withholds recovery with a
reason. It does not license guessing that the computation was equivalent.

The [UDM-10 code-closure follow-up](programs-identity-and-revisions.md#udm-10-code-closure)
owns any change to the producing identity consumed here. Where its authenticated source basis
changes, verify original attempt and contributor attribution, exact compatible checkpoint reuse,
and withholding on an unresolved determinant. The selected-read closure alone establishes no
producer compatibility. Keep the existing attempt-scoped path available under incomplete identity.

UDM-12 supplies current validation and reconfirmation. The applicable family set is computed
under the current declaration, including a newly applicable or newly ready family. Matching all
entries in an old seal is insufficient when the current required set is larger. Original
producer facts remain exact through any checks or reconfirmation. Authorization, trust, source,
purpose and support are live conditions of use. Revoked support cannot become usable because
the bytes still match. [ADR-0092][operation-adr] and [ADR-0122][support-adr] retain those meanings.

I03's discovery correction is implemented at **UDM-05/07**, not in a spool adapter. Its owner
uses the fulfilled current-demand use and current declared discovery relation, verifying output
role, exact member scope/completeness, original source/purpose and current support while retaining
the producing release. UDM-25 can depend on a population that owner has closed; it cannot close a
population itself. An unavailable equivalence proof requires explicit fresh discovery. The
recorded N29 book basis already requires fresh discovery, so it cannot alone qualify this
cross-release case.

## UDM-25 — recoverable completion and compatible checkpoints

<a id="udm-25"></a>

The package has a bounded early decision and two implementation slices. Their shared
contract is authentic prior production under current native use authority. Each slice has its
own acceptance below, and neither can be marked complete solely because the other works.

### Early decision with UDM-20

At UDM-20's early bounded reproduction, inspect exact committed-intent and completion outcomes
before adding storage. Reconcile an already committed or uncertain intent first. Reproduce a
known rollback before intent commitment with a bounded PDF or sentence completion. Identify the
bytes which can be retained once, the original evidence needed to authenticate them, and the
current transaction's work which the handoff must survive. Preserve the existing bounded
timeout/withheld-region diagnosis. A bounded reproduction which cannot expose the historical
failure states that limit; it does not close the recorded production-scale obligation.

Choose one durable custody route at this point, and record the selection and its failure
envelope in this companion before implementing its consumers.

| Candidate | What it provides | Selection condition and burden |
|---|---|---|
| Minimal native intake, committed in a separate short transaction | Stores an authenticated, bounded typed draft independently of the expensive validation/settlement transaction. The native owner retains intake and single consumption. | Prefer when the intake can acknowledge without repeating the failing canonicalization/seal/settlement path and database availability is an acceptable handoff premise. Inspect its actual write path and commit uncertainty. An inner savepoint in settlement is not independently durable. |
| Existing private spool custody extended with a typed completion draft | Can acknowledge durable local material without depending on PostgreSQL availability, preserving the existing file/manifest and physical-owner discipline. Native consumption establishes target use authority later. | Prefer when the demonstrated recovery requirement includes database unavailability or intake would share the failing path. Reuse existing custody and cleanup primitives. Add only the bounded envelope and authenticated consume correspondence that are missing. |

Keeping an answer in memory while its original claim is alive may reduce an immediate retry's
work. It does not meet UDM-25's process-exit requirement and cannot become the only recovery
route. Do not implement both durable stores by default. If the selected route fails the required
failure envelope, reopen this one decision and its callers rather than retaining parallel
fallback implementations. Routine type names and physical file layout remain implementation
judgment.

### Slice A — private completed-result handoff

**Envelope and acknowledgement.** Extend the existing model-owned completion/wire and execution
evidence declarations with the minimum private handoff correspondence. Reuse canonical completion
meaning and existing CPU/provider/PDF evidence codecs. Admit only the selected PDF and sentence
boundaries initially; registering arbitrary objects is outside scope. The envelope identifies
the exact original request/generation/task/attempt/holder/runtime, original output/evidence
digests and byte lengths, complete production basis, output contract, selected input/support
binding and private content custody. Retain actual archived producer bytes and existing evidence
references. It must be possible to verify the expected artifact extent and digest before reading
or interpreting the body. Transport/reply limits remain enforced without semantic truncation.

A handoff is acknowledged only after its selected custody owner has made the complete envelope
and body durable. A partially written file, uncommitted row or successful worker return supplies
no acknowledgement. Material bytes should be written once at this boundary where feasible;
reference already-owned immutable PDF evidence instead of copying the entire build. Keep owned
memory charged through its last consumer and physical work charged until proven retirement.
Durable bytes surviving process exit do not imply that an uncertain worker has stopped.

**Consumption.** Integrate recovery into the existing executor's completion reconciliation,
before acquiring fresh compute resources. The order is completed-result attachment, exact
committed/uncertain intent reconciliation, admissible acknowledged draft, then genuinely missing
computation. Use one native idempotent consume decision and its current claim to bind an accepted
draft to intent/publication. Its original evidence is verified under the authentic original
execution basis. Current applicability, input/support, contract and authority checks decide
whether the target can use it. Any successor request/generation correspondence is checked by
this native owner using the UDM-10 identity contract. It is not implemented by editing an old
intent's generation or substituting the adopter's runtime into old evidence.

Concurrent consumers and lost acknowledgements must converge on the same exact outcome. A
consumed draft records the existing intent/receipt correspondence so a retry can inspect it.
Uniqueness and the existing request/task fences prevent publishing competing answers. A fresh
claim never restores an expired original claim. A late writer which has lost its authority
cannot create a newly acknowledged result or overwrite acknowledged content. Adoptable evidence
produced while authorized and retained under the selected custody contract remains distinct
from a late stale result. Native rejection remains a rejection and does not silently turn the
draft into a published terminal outcome.

**Lifecycle.** A draft moves from private preparation to acknowledged recoverable material, then
to consumed correspondence or explicit rejection/retirement. Native commit uncertainty is
resolved by exact identity before retrying or retiring it. Successful settlement allows the
private copy to retire only when its publication/evidence consumers no longer need it. A
permanent incompatibility or an expressly defined expiry may make a draft ineligible, but neither
lease expiry nor process exit alone authorizes deleting its evidence or proves physical death.
Define expiry eligibility and explicit authenticated cleanup in the existing custody owner.
Preserve the reason and existing attempt/receipt evidence required to explain the outcome.
User-facing cache prune/clear, managed-result expiry and diagnostic holds remain separate.

Cancellation stops new admission and follows existing collection, quarantine and retirement.
It never publishes a private draft or classifies execution failure as a terminal input result.
An already acknowledged authentic handoff can remain available for a later authorized demand;
an unacknowledged late answer follows the existing discard rule. Shared useful work retains the
native demand-interest rules. The bounded early decision must reconcile these transitions with
[ADR-0125][host-adr] and [ADR-0126][failure-adr] before dependent implementation.

### Slice B — compatible PDF checkpoint uptake

Split `PdfSpoolProducerBasis`'s original producer attribution from the compatibility facts used
for page production. Keep request, generation, release, task/attempt and actual runtime as exact
original facts. Derive the comparable production basis from UDM-10's admitted operation/recipe,
result-affecting implementation/profile, material assets, source and logical page selection,
PDF contracts and native/payload meaning. Do not remove source/schema/package determinants
merely because they appear broad. Establish which affect production, which affect decoding or
current admission, and which are provenance. Retain coarse conservative determinants wherever
their narrower correspondence is unknown.

Extend `verify_spool_recovery` and `clone_recovery_entries` with explicit target-compatible
uptake. Acquire the original writer custody and prove its physical retirement before reading
acknowledged entries for reuse. Verify the manifest, files, extents, digests, page/artifact
coordinates and selected output contract. Select complete reusable page units; restore their
original contributors separately from the new sealing publisher. Complete missing page-local
stages and the required global assembly/certification through the existing producer route.
Existing exact-basis records remain eligible through the same verifier. Records lacking enough
evidence cannot receive an inferred cross-basis compatibility claim, and need no general legacy
reader or spool migration.

Use `ReplayCandidatePageSource` batches and native acknowledged replay keys for uptake. Preserve
stable logical page identity and exact contributor attribution when relocating private raster
paths. Do not rehydrate every page into a whole-book candidate collection or call recognition
again for an adopted acknowledged page. Keep full ordered page coverage and required
document-wide checks at certification. A requested region can proceed when its actual inputs
are ready; unrelated unfinished regions introduce no stage-wide barrier. Page-local invalidation
is permitted only where dependencies establish locality. A changed original document may still
invalidate all pages when extraction/certification depends on its whole content.

Native staging, contributor and publication correspondence changes use the same typed program
registry and model-owned generation as other UDM programs. Existing publication proof still
binds the real PDF receipt, original contributors and the current sealing/admission fence.
There is one converter, one checkpoint verifier and one publication route.

### Prerequisites and revision placement

| Required slice or decision | What it supplies and when it is needed |
|---|---|
| UDM-20 early diagnosis and this package's custody selection | Establishes the pre-retention failure boundary and chosen durable handoff before installing intake/consume programs. UDM-20's later confirmation exercises the selected repair. |
| UDM-00 decision route | Records the selected handoff and rule impacts with their design owners before dependent implementation. See the next section. |
| UDM-10 code/material identity slice | Supplies complete producer and checkpoint compatibility determinants before cross-release/request-generation uptake. Original exact-basis recovery remains independently useful. |
| UDM-05/06 current validity declarations and UDM-09 program registry | Supplies applicable-family and integrity/purpose facts, typed generated intake/consume and staging programs. Their native identity/validation integration joins UDM-10/12. |
| UDM-12 native current-validation and reconciliation contract | Establishes current family reconfirmation and retained evidence handling for consumption, including newly applicable families. |
| UDM-05/07 discovery correction | Enables the independent compatible old-release population journey. It does not become a prerequisite for private file acknowledgement or unrelated exact-request recovery. |
| UDM-22/23 final-source qualification | Establishes assembled fault, provider, cross-release and whole-book behavior after local delivery. A bounded package pass closes only its stated scope. |

**Native revision.** Installed UDM-25 intake/consume programs and any PDF staging/contributor
changes join the **identity transition revision**, with their UDM-09 declarations, grants,
guards and UDM-10 identities. They are resolved and included before that revision freezes.
Python-only identity/spool changes install no native revision. There is no additional default
UDM-25 revision. If the bounded decision discovers an incompatible late requirement, update the
coordinator's sequencing before freezing; do not silently postpone native integration until
after UDM-23. UDM-20's diagnostic reproduction remains early even though its package confirmation
uses this delivered contract. Discovery's UDM-05/07 native change follows its own assigned
revision, rather than being hidden in the recovery package.

Shared edits include `orchestrate/data_operations.py`, `semantic/claim_lifetime.py`,
`semantic/data_completion_settlement_native.py`, the completion/evidence declarations and wire
generation, `ingest/pdf_build_spool.py`, `ingest/pdf_candidate_source.py`, `semantic/pdf_staging.py`
and its native generator, plus PDF publication contributor validation. Sequence or single-own
those surfaces with UDM-05/09/10/12. The operator inspection/recovery work consumes typed
identifiers, retained fates and refusal reasons from these owners. It adds no draft publication
or alternate effect route.

### Rule impacts and architectural updates

This document records proposals, not an inferred acceptance of new rule changes. UDM-00 records
the operator's disposition and the selected mechanism through the existing ADR route before
dependent implementation, and amends D3's product/PDF custody sections and D6's execution/recovery
sections in the same architectural change.

- **ADR-0125/0126.** A durable pre-intent handoff adds a recovery boundary to process/run custody
  and retained-intent reconciliation. Preserve physical retirement, quarantine, current fences,
  failed-attempt classification and nonpublication. A new decision can extend those contracts.
  If the selected transition changes their binding discard or retirement clauses, supersede the
  affected immutable ADR explicitly and carry forward its surviving guarantees.
- **[ADR-0127][pdf-adr].** Its current recovery rule requires exact premises and says differing premises
  refuse. Explicit compatible page production across different request/generation/release
  carriers needs a scoped successor decision separating that compatibility from exact producer
  provenance. Preserve writer retirement, actual contributors, source/asset custody, sealed
  receipt correspondence and no asserted fresh-GPU equivalence. Do not silently weaken the
  current exact-premise rule in a Python comparator.
- **ADR-0092/0122.** Complete semantic determinants, equal-value/support cutoff and current
  support authority are preserved. UDM-25 requires no new relaxation of those rules, no broad
  runtime recipe fallback and no independent cache authority.

### Concrete library mechanisms

The selected route uses the repository's pinned Python 3.14.10, Psycopg 3.3.6 and SQLAlchemy
2.1.6. No new cache or persistence dependency is required by this package.

For a native intake, an independent transaction is pivotal. Psycopg's
[`Connection.transaction()`](https://www.psycopg.org/psycopg3/docs/basic/transactions.html#transaction-contexts)
commits or rolls back its transaction scope; nested scopes on an existing transaction are
savepoints and cannot survive outer rollback. Use the existing engine/claim lifetime owner to
open the genuinely separate short write rather than adding an adapter retry loop or a
savepoint labelled durable. The version-matched [Psycopg overview, section 10][psycopg] and
[SQLAlchemy transaction boundaries](https://docs.sqlalchemy.org/en/21/core/connections.html#using-transactions)
orient the implementation. Confirm cancellation/commit uncertainty against the selected driver
and existing failure classification where it affects acknowledgement. For single consumption,
use the existing native unique identity and an exact locked lookup or PostgreSQL 18
[`INSERT ... ON CONFLICT`](https://www.postgresql.org/docs/18/sql-insert.html#SQL-ON-CONFLICT)
against the relevant unique constraint. Re-read and authenticate the winner if the insert
reports a conflict; success requires a committed authoritative intent or publication. SQL remains
in UDM-09's typed registry. Use the current [SQLAlchemy expression](../../libraries/postgresql/sqlalchemy.md)
and [pglast AST](../../libraries/postgresql/pglast.md) program authoring paths for changed predicates
and native statements, and generate the corresponding purpose grants with the programs.

For private files, extend the existing spool's exclusive creation, `flush`/`os.fsync`, manifest
acknowledgement and writer `fcntl.flock` custody. Python's
[`os.fsync`](https://docs.python.org/3.14/library/os.html#os.fsync),
[`os.open`](https://docs.python.org/3.14/library/os.html#os.open) and
[`fcntl.flock`](https://docs.python.org/3.14/library/fcntl.html#fcntl.flock)
are the relevant APIs. Follow the existing descriptor ownership and no-follow checks. Do not
explicitly unlock a shared inherited writer descriptor while another physical writer may own
it. Directory-entry durability and write ordering must be established before acknowledgement;
an atomic rename alone establishes neither a complete manifest nor a settled native effect.
Python [`os.replace`](https://docs.python.org/3.14/library/os.html#os.replace) also cannot
overwrite a nonempty entry directory. If a new immutable entry publication is needed, use
single-winner installation with verified winner content, coordinated readers and cleanup,
sharing the publication reasoning corrected in [UDM-14][cache]. Recovery custody itself remains
outside that expendable store.

Cachetools is deliberately not the durable handoff. Its `condition=` coordination is local to
one wrapper/process, has no durable consumption authority and does not survive process exit.
The [8.0.1 capability evidence][cache-evidence] and [library overview][cachetools] support
UDM-13's process tiers; no cachetools pin or TTL is a draft eligibility rule. Reuse existing
typed completion/evidence codecs rather than pickle. A digest checks retained content identity;
native correspondence and current validation establish its permitted use.

### Acceptance evidence

Plan local correctness checks at a coherent package endpoint, then include the cases in
UDM-22's managed union and UDM-23's final-source journey. Extend existing spool, executor,
completion, contributor and native demand tests rather than creating a parallel harness.
Independent expectations name the producer calls and original contributors which should appear.
Expected identities computed by the same new comparator cannot prove correct invalidation.

| Distinguishing case | Required observation |
|---|---|
| Known rollback before intent retention | An acknowledged typed handoff survives; recovery performs settlement/validation without repeating that expensive computation. An unacknowledged partial body is ineligible. |
| Process exit after handoff acknowledgement | A fresh process discovers exact private custody and can request authorized consumption without the old Python callback or hydrated input objects. |
| Retention committed but acknowledgement lost | Existing exact intent reconciliation takes precedence. No duplicate draft consumption, producer call or competing result is created. |
| Producer retirement and stale writer | A live/uncertain writer refuses uptake and retains charges. Proven retirement permits verified recovery. Expired leases and reused PIDs do not substitute for retirement. Late unauthorized writes cannot alter an acknowledged answer. |
| Two recovery consumers or an interrupted consume acknowledgement | Native uniqueness and exact replay converge on one intent/publication outcome while retaining original producer attribution. |
| Tampered, truncated, oversized or wrong-contract draft/checkpoint | It is refused before use with an attributable reason. No compatibility flag bypasses content, extent or native evidence checks. |
| Changed input, material method/asset/profile, output contract or replicate | Incompatible material is not used. Fresh work is explicit and independently counted. A harmless orchestration/deployment-only change permits reuse when the complete basis proves compatibility. |
| Revoked support or changed/newly applicable validator family | Revocation refuses use. Current checks/reconfirmation run as required without rewriting old evidence or claiming the old seal covered a new family. |
| Compatible old-release/request-generation PDF pages | Original retired contributors remain inspectable, acknowledged adopted pages cause no recognition, and only missing/incompatible page-local work executes. A material document-wide dependency still invalidates the necessary complete scope. |
| Selected page batches and certification | Uptake uses the selected batches; no whole-book hydration is required for regional consumption. Full ordered coverage and required global checks remain mandatory at certification. |
| Cross-release discovery and changed membership | UDM-05/07's owner closes an equivalent current population from authenticated prior output, rejects wrong relation/role/scope/incompleteness/support, and schedules an added member while preserving unaffected siblings. |
| Cache eviction and explicit recovery cleanup | Clearing/pruning expendable caches leaves acknowledged drafts/checkpoints recoverable. Cleanup cannot remove active or uncertain ownership or needed publication evidence; completed eligible cleanup retires only its declared private material. |

UDM-20's later confirmation reports the chosen route, the last durable boundary and the bounded
reproduction's actual outcome. UDM-23 records the retained-work census and expected mixture of
adoption, revalidation and fresh work before execution. Use existing independent native/provider
counts and exact receipts to distinguish actual computation, checkpoint uptake, retained intent
reconciliation and cache hits. Preserve failed/interrupted records and scoped limitations. The
whole-book unchanged repeat and production-scale settlement/binding checks remain required at
their owning qualification packages. Chandra OCR is excluded.

### Consumer migration and retirement

Migrate the selected PDF and sentence execution/reconciliation callers together with their
handoff. Remove any superseded in-memory-only recovery assumption, duplicate rehydration or
recompute fallback which would bypass an eligible acknowledged result. Preserve bounded
same-owner retry only where it composes with the one durable owner. Refused recovery may require
fresh computation, but the reason remains visible and no historical interpreter is revived.

Replace the spool's combined carrier/production compatibility comparison and its callers with
the one qualified verifier. Keep exact producer fields and useful existing file/retirement
verification. Retire mechanism-specific tests that enforce release/generation equality as the
sole reuse criterion, and replace them with positive and negative material-basis controls.
Do not keep both the old comparator and a new compatibility adapter. No broad spool/data
migration or deletion is required. Inert historical material without sufficient proof may
remain or be explicitly cleaned through its custody owner.

Package completion requires delivered consumer integration, the selected lifecycle and
architectural decision, installed programs at the planned transition where needed, local
acceptance and links to outstanding assembled qualification. It establishes no completed
UDM-22/23 result by itself. Execution updates the coordinator's single package state and records
closure evidence there.

### Native transition evidence

**Tested, 2026-11-18.** Exact execution origin is registered before computation. A private draft
retains its origin, runtime and typed output through a failed retain step. Native consumption
authenticates the original retirement, producing basis and new claim. A committed consumption
maps the new claim to its retained intent after the local acknowledgement is lost. Publication
preserves original producer attribution and records current adoption separately. Compatible
PDF batches authenticate material determinants and original contributor proofs before reapplying
the carrier fields.

Private PostgreSQL passed retain rollback, later-generation consumption, repeat publication,
retirement refusal and actual cross-build PDF contributor adoption. A second case passed
lost-acknowledgement reconciliation after the persistent mapping committed and the private data
was removed. The owning receipts are `bd79f9aa68bf4915a7df0d1aa9e7b360` and
`fdd3cb361f0f406690339d723151e630`. The [qualification account](qualification.md#retained-book-diagnosis)
owns the original book diagnosis, its evidence limits and the remaining regional and provider
observations.

**N33 stage observation, 2026-11-19.** The current statistical PDF producing closure has
unresolved dependencies. Its checkpoint recovery requires the original attempt, and its
current producing requests carry demand scope. The retained-result comparison found zero
exact-recipe matches among the 14 preserved episodes. The
[identity successor record][programs] owns the current stage evidence.

<a id="remaining-recovery-implementation"></a>

### Recovery audit corrections

**Interface-checked, 2026-11-19, at `618fff894`.** The production managed demand route
passes the draft root into the native execution service. `CompletionDraftStore` durably writes
the bounded body and ACK under one file owner. `execution_origin_native.py` binds the original
claim and material inputs, requires retirement for transfer, and records the consumed draft's
intent correspondence. The two private receipts establish those paths for their selected cases.
The cross-build PDF case reused a later attempt of the same task.

| Obligation | Current implementation boundary | Closure |
|---|---|---|
| UDM-25-R1. Select an admissible draft before work specific to fresh computation | Claim acquisition commits before renewal, intent reconciliation and draft inspection. Scalar and batch execution acquire preparation and hydrate fresh inputs after recovery resolves. A deferred member retains its exact renewed claim and only compact metadata. | Controlled recovery, refusal, mixed and deferred batches passed in `87c9503076d44152b19f3545af1b4ae4`. The submitted-held-claim cancellation control passed in `e6bd6d6ea94c40328462a6fcb07f1091`. |
| UDM-25-R2. Authenticate retirement and cleanup of private draft material | The protected native inspection binds the original producer, completion, intent and publication. The private namespace owner only unlinks an exact acknowledged body after positive physical retirement. A synced marker makes an interrupted deletion retryable. | Final private PostgreSQL controls verified retention before publication, refusal under a different project, retirement after publication and recovery of the original answer after a lost local acknowledgement (`a073a72d45ff46dbac05763954436d8a`). File and cache custody controls passed in `87c9503076d44152b19f3545af1b4ae4`. |
| UDM-25-R3. Support compatible PDF checkpoints across a changed request | Native recovery keys select candidates for full comparison. Both discovery and contribution compare authenticated original-source facts across the two demand-scoped admissions, exact other supports, current scope, complete material premises and original retirement. File uptake verifies the exact native writer and manifest. | The final private selection passed changed-request uptake, attribution, missing and forged source refusals, exact other support and request slots, both original and current revocation controls, five archived material variants, and current complete and incomplete attribution (`a073a72d45ff46dbac05763954436d8a`). |

To request explicit cleanup, run `ci demands retire-draft DRAFT_ID --project PROJECT --target
development` against the acquired project and configured target. The same command selects
`deployment` for a configured deployment profile. Automatic cleanup can record retirement
while the original live process can establish it. If that proof is unavailable and native
custody has no exact failed attempt, the acknowledged private file stays retained. Files without
a complete acknowledgment stay inert. Cache pruning never enters the completion-draft namespace.

Discovery computes the current key once in a typed local before querying retired producers.
The indexed column compares to that local. The query then verifies the candidate's complete
material and authorization. This avoids placing a volatile SQL call inside the indexed equality.
Regional qualification owns planner behavior on a populated workload. [PostgreSQL function volatility](https://www.postgresql.org/docs/18/xfunc-volatility.html)

### Fresh PDF contribution on N34

**Failed, 2026-11-19.** The selected-source native control reached the first fresh PDF contributor
registration and PostgreSQL refused it with SQLSTATE 23514, “PDF spool contributor has no matching
original producer” (`6c22c15dd71141a390ce8733dcee242c`). The same selection passed all four
JSONL and Parquet demand exports. The selected-source test failed upstream of package export.

The current lowering capture reports `code_identity.complete=false`. The installed contributor
guard requires material-domain compatibility for both the original attempt's own contribution and
cross-attempt adoption. Its material-domain projection requires complete code identity, so that
predicate cannot establish compatibility for this fresh attempt. UDM-25 owns the distinction
between same-attempt attribution with exact current custody and recovery across attempts. Preserve
the complete-identity and original-retirement requirements for cross-attempt adoption. Address
the fresh path through the native revision lifecycle and rerun the selected-source journey.
The first private N35 qualification reached fresh certification and exposed its remaining v1
lowering rule (`a826fdddf8f64bbbb207e6f8a04cfe5b`). Current certification authenticates the exact
v2 release archive, input digests and current producer. Reuse of another producer's oracle still
requires complete lowering custody. A second candidate detected the v2 incomplete-code digest
shape (`4fac60f3f0d743448375f409bda91fc6`). Current verification accepts the generator's exact null
digest when the code identity is incomplete and requires a valid digest for a complete identity.

### Fresh PDF qualification on N35

**Tested, 2026-11-19.** The registered N35 private runs passed fresh producer certification,
exact writer-fence and prior-oracle controls, fresh selected-source export and offline formula
preparation, and native companion Parquet export and cancellation. The retry acquires a fresh
cut for the exact capture and original source. Broader continuation under complete determining
read identity remains with UDM-10. [Qualification receipts](../../design_review/evidence/2026-11-19_udm-audit-closure/README.md)

**Tested, 2026-11-19.** N35 is active at generation 32 on `ddo-current-pdf-bounded`. Native
catalog and archive checks passed. The retained project identities and selected demand payload
matched preflight. The stage check preserves the bounded record set. UDM-20 owns the regional
workload exercise. [Cutover evidence](../../design_review/evidence/2026-11-19_udm-audit-closure/README.md#bounded-stage-activation)

[UDM-10 code identity boundary][programs]

[coordinator]: ../unified-domain-model-and-execution_2026-11-19.md
[review]: ../../plan_improvement_reviews/unified-domain-model-and-execution_2026-11-18.md#I02
[programs]: programs-identity-and-revisions.md
[validity]: lowered-operation-facts-and-validity.md
[qualification]: qualification.md
[cache]: cache-system.md
[operation-adr]: ../../adr/0092-ddo-operation-authority.md
[support-adr]: ../../adr/0122-set-wise-support-validity.md
[host-adr]: ../../adr/0125-process-owned-execution-host.md
[failure-adr]: ../../adr/0126-terminal-outcomes-and-attempt-failures.md
[pdf-adr]: ../../adr/0139-compatible-pdf-checkpoint-custody.md
[psycopg]: ../../libraries/postgresql/psycopg.md#10-transactions-savepoints-and-distributed-transaction-support
[cachetools]: ../../libraries/analytical_infrastructure/cachetools.md
[cache-evidence]: ../../design_review/evidence/2026-11-18_production-review-inputs/library-cachetools.md
