# Unified domain model and execution — recoverable work and operable changes

**Reviewed 2026-11-18** against clean `main` `3726a5cb6`, the proposed UDM-00–24 series. The
production baseline is `5139eaba3`. This review covers the [coordinator][udm] and all six
companions for [model authority][model], [validity and support][validity], [programs and identity][programs],
[cache ownership][cache], [analytical placement and retirement][analytical], and [qualification][qualification].
Current observations are **Interface-checked by source inspection, 2026-11-18**, unless attributed to
an earlier receipt. Recommendations are **Proposed**. The coordinator owns scheduled disposition.

## Combined judgment

The proposed compiled model, lowered operation facts, typed program registry, and separate program,
kernel, and validator identities give the series the right foundation for targeted reuse. The main
addition is to carry that distinction through **what can be recovered**. Local preparation caches,
query pages, completed derivations, and work which has reached computation but has yet to settle
have different owners and lifetimes. Implementing UDM-13–15 and an unchanged-repeat test alone
would leave some expensive failure and release-transition cases uncovered.

The CLI already has typed result inspection, bounded watch, native demands, and guarded model-change
actions. Extend these owners with the facts they need to answer operational questions. The highest
value is an exact way to resume, reuse, or explain a refusal from one managed ID, followed by live
progress and a model-change preview that exposes the impact on production work. Rich improves the
presentation after the evidence is available. Typer can make the existing routes discoverable.

### What the book evidence establishes

| Prior evidence | Consequence for the review |
|---|---|
| N18 stopped after 135 spool-acknowledged pages, then resumed and published the complete capture (`db23eb6a0b8d45c59faee72ea27a1e77`, `7a5bff563a8e461ca054d03d39efbcf8`). N21 later attached the exact capture to a successor demand (`9bef89796a334e33b61b32f1ce24cc47`). | Same-demand checkpoint replay and cross-release completed-result adoption already have working foundations. |
| N23 published the 518-page capture and the 29-region population. The 16 GiB attempt `1dd5d45ded4b4ea38399fb121a44d28c` retained 3,411 sentence occurrences in 20 completed regions. Nine sentence-region attempts timed out during settlement. The whole-view binding query later stalled. | Distinguish retained products, timed-out attempts, and fan-in. Establish the last durable boundary for each relevant attempt before attributing recomputation. The counts are occurrences over completed regions. |
| N27 removed duplicate canonical-payload hashing in retained-intent insertion. N28 added an equivalent unfinished generation successor and demonstrated native adoption of a retained intent. A separate two-region fixture (`3fed447a2a5649538c80ac05c1ed7c47`) reached the discovery closure mismatch. | Preserve the repairs and reproduce only the remaining distinct decisions. A shorter native transaction reduces exposure without making completed work durable before that transaction. |
| The N23/N29 archive comparison found changed capture, organization, discovery, and construction recipes, with sentence and formal identities equal. The N29 whole-book attempt never started. The one-page Integrated Nemotron check stopped before demand registration with zero completed inference requests. | Check the causes of each identity change against the material operation boundary. The receipts give no final-head book result or successful Integrated inference result. |

The receipt IDs and dated counts come from the [DDO checkpoint][ddo] and [STATUS][status]. The two
managed failure manifests were present during the review, with no active hold listed. Preserve them
at UDM-20 entry and retain their original outcome and scope. The outer book cleanup report and the
nested join uncertainty are separate evidence. DDO records the independent process exit and lease
expiry checks, which supply the stronger retirement evidence for that invocation.

## Make reuse follow the operation

<a id="I01"></a>

### I01 · Separate production determinants, current admission, and provenance

Extend UDM-09–12 and UDM-18 to state which dependency of a producer affects its output and which
governs acquisition, settlement, or current use. The present PDF lowering capture
(`semantic/pdf_lowering.py:31`) includes fixed references to native SQL authoring, schema, and
publication code. A derived import closure can reproduce excessive scope if it starts at an
orchestration or publication entry point. UDM-10's narrowing is useful only when the nominated
entry points, data/configuration reads, and opaque dependencies match the role being fingerprinted.
This refines DA-068/069/076/082 under [UDM][udm].

Use the existing operation and request identities as the reuse authority. Their determinants should
include effective input meaning and required logical context, parameters and selection semantics,
output-affecting implementation and policies, exact material assets, output contracts, and any
replicate identity. A batching, runtime, or library change belongs there when it changes the
observation allowed by the contract. A deployment ID, scheduler setting, formatting change, or
consumer-only program belongs in the captured record or its own responsibility unless a dependency
shows it contributes to the producer's result. Use the existing complete-dependency requirement
and conservative fallback for opaque code. Where absence of a dependency cannot be established,
withhold reuse with a reason. Keep actual archived bytes and execution custody for every producer.
Follow the semantics of the equal-content cutoff in [ADR-0092][op-adr], including required support.

Record the decisions at the owning native boundaries. A current contract may allow an authentic
prior result to attach, require read or validity checks again, require rebinding and only new
subordinate work, or require fresh computation. Ensure reconfirmation covers the **current**
applicable validator families, including a newly applicable family, even when every entry in the
old seal still matches. A provisional-to-ready or newly required family is an explicit test case
for UDM-05/06/10/12. Current authorization and support remain authoritative. The use of a revoked
derivation cannot be restored by a successful content match. [Set-wise validity][support-adr]

Remove broad producer salts where the complete narrower basis and consumers are established.
Keeping the coarse basis for a cheap or still opaque boundary is preferable to guessing at a
missing dependency. Check a same-behavior release, one changed region with unaffected siblings,
and explicit material changes to source, method/asset, output and replicate. A test comparing only
newly computed digests from the same compiler would miss an overbroad or omitted dependency. Use
independent expectations about which producer runs and which derivations are used. This serves
FP-04/06/07 and DP-04/08/09, with the code-intelligence rules on attributed facts and unknowns where
static dependency analysis contributes.

<a id="I02"></a>

### I02 · Make completed-but-unsettled computation recoverable

`orchestrate/data_operations.py:955–1056` validates and assembles the result in memory, then submits
it to native intent retention. The retention routine checks the original claim, runtime, inputs,
support, and completion correspondence before inserting a durable intent
(`semantic/data_completion_settlement_native.py:878–1070`). A rolled-back insert can leave no intent.
Once an intent is committed, `_reconcile` has an established adoption and publication path. Existing
provider and CPU evidence binds the actual attempt. Re-stamping that evidence with a new fence
would falsify provenance. The retained book error record includes SQLSTATE `57014` in the intent
insert's canonical JSON/seal path. The record gives a concrete pre-retention failure case. It does
not establish how many of the timed-out attempts lost work or whether the N27 repair is sufficient.

Move the retention question into UDM-20's smallest reproduction, before committing the identity
transition. First reuse the native intent by exact identity on committed or uncertain outcomes.
For expensive results which are lost before commitment, give the native completion owner a private
recoverable handoff before settlement. Evaluate adopting a bounded, typed completion draft from
existing private spool custody against a minimal native intake which commits the authenticated
draft in a separate short write. Prefer the intake if it can preserve evidence without depending
on the failing settlement path. Prefer existing private spool custody if that independence is
needed during PostgreSQL unavailability. Either needs a single native consume decision, exact
fenced original evidence, content and size verification, current support and validity, and clear
retirement on successful settlement, rejection, or expiry. Material bytes should be written once
at that boundary where feasible. Record the handoff independently of user-facing cache pruning and
held diagnostic results. Apply first to the demonstrated expensive PDF and sentence boundaries.

The minimal alternative is to retain and replay the answer while the original owner and valid claim
are alive. It handles a recoverable statement interruption but loses the handoff on process exit or
claim retirement. Avoid an unbounded store of arbitrary Python returns. Existing completed-result
retrieval and native intent reconciliation take precedence. Expose neither drafts nor failed attempts
as completed products. Check a pre-retention rollback, post-commit lost acknowledgment, physical
owner retirement, and a late stale writer. The original producer evidence stays exact, one result
can settle, and changed inputs, revocation, or incompatible evidence refuse recovery. This is a
UDM-12/20/23 contract and an ADR-0125/0126 impact if adopted. DP-03/19/20 and G5 apply.

<a id="I03"></a>

### I03 · Carry proven reuse through PDF checkpoints and population closure

**Checkpoints.** `PdfSpoolProducerBasis.determining_basis` includes request, generation and release
in addition to recipe, implementation, profile and PDF-domain identity. `PdfSpoolPremises` also
compares the source, asset, native/payload-schema, package, and page-range bases
(`ingest/pdf_build_spool.py:62–139`). Narrower producer identities alone leave acknowledged pages
stranded across a successor generation or release. Keep exact writer and recovery ownership.
Extend the current verified recovery and cloning path (`clone_recovery_entries`) to admit a prior
complete page under an explicitly compatible page production basis and authorized current request,
preserving its original contributor. Recheck content, artifact coordinates, page selection and
contract compatibility. Retain source or document-wide dependencies where later certification or
recognition actually requires them. The proposal does not promise page reuse across arbitrary PDF
edits. A changed page-local basis can invalidate an individual unit only where its dependencies
are known. Legacy spool records without adequate evidence remain eligible for existing exact-basis
recovery. `ReplayCandidatePageSource` already yields selected page batches, and the native staging
reader already has acknowledged replay keys. Use those boundaries to avoid restarting recognition
or rehydrating whole-book candidates. Keep full ordered coverage at certification and require it
before consumers that depend on a complete population. A regional operation should run when its
declared inputs are ready, even if an unrelated region is pending. No general artifact migration
is required. [Analytical placement and certification][analytical]

**Discovery.** `semantic/demand_registration_native.py:1338–1365` requires the producing request's
release to equal the current demand's, although equivalent completed discovery can already be
attached. Consume the exact fulfilled current-demand use and the declared current discovery
relation, with authenticated old producer/output role and exact membership/completeness, current
support and original-source/purpose checks. Establish this from existing native relation and use
authority. Preserve the original producing release. Merely dropping the release-equality predicate
could admit a different role, relation, scope or population. The other viable choice where the
equivalence proof is missing is fresh discovery, reported as such before attempting closure.

Assign checkpoint compatibility to UDM-10/20 and native closure to UDM-05/07 with UDM-20 regression
evidence. Resolve the native change before the relevant revision freezes. Test a retired spool with
the same production basis, an active writer, a material change to provider/page/contract, and
tampering. Test an equivalent old-release discovery that closes under the target declaration,
and reject a wrong relation, incomplete or differently scoped product, or revoked support. Show
that an added member schedules the necessary new work and preserves unchanged siblings. This
extends DP-04/07/09/19 and the scheduled DA-071/073 ownership. The observed mismatch was in a
fixture with equivalent discovery. The recorded N29 book recipe requires fresh discovery under
its current basis.

## Preserve the planned cache simplification

<a id="I04"></a>

### I04 · Use cachetools for bounded process reuse and keep cache maintenance local

Retain UDM-13's choice of cachetools 8.0.1 for the tiers where bounded retention or concurrent
construction pays. The installed pin at review is 7.2.7. The 8.0.0 overview gives orientation;
the [8.0.1 evidence][cache-evidence] and the tagged implementation govern. Byte sizes from
`getsizeof` are taken on insertion. Use immutable or owned entries with known retained weights and
count weights as declared estimates where live allocations are external. The condition wrapper
coordinates a pending key in one wrapper, then retries a miss after the owner raises or returns
an oversized uncached value. Use it where those semantics fit. Keep T4's planned shared future
for a scoped wave that must receive the same settled value or failure, and clear it at settlement.
Process-local coordination and expiry remain independent of claim retirement. Keep inexpensive
static holders simple. [Cachetools storage](https://github.com/tkem/cachetools/blob/v8.0.1/src/cachetools/__init__.py) · [Decorator behavior](https://github.com/tkem/cachetools/blob/v8.0.1/src/cachetools/_decorator.py)

Refine UDM-10/13's planned cursor invalidation. `serve/rich_queries.py:71–100` currently mixes
`cachetools` into every served implementation basis. The plan specifies a one-time refusal of all
outstanding cursors on the upgrade. Scope cache storage and codec versions to cache entries.
Derive whether query semantics, row ordering, cursor format, or authenticated code paths change
separately. If an old opaque cursor cannot be interpreted after the identity contract changes, allow
that explicit transition refusal. A later storage-only pin should not move the new continuation
basis. Keep per-read native authorization and drift refusal. Verify cached and uncached answers
and ordering independently, and distinguish an expected cache miss from a native read refusal.

`ci cache stats` and MCP should state the observed process/owner and the scope of each counter.
Fresh CLI processes can list D2/D4 presence and their budgets, and report their own in-process
activity. For long-lived worker statistics use the existing long-lived process diagnostic owner.
Show misses, admission skips and evictions only where the tier can attribute them. `ci cache prune`
should identify the prospective or actual tier and bytes under its custody. Include no retained
intents, acknowledged checkpoints, or held receipts in cache-pruning eligibility. Avoid TTL as a
substitute for content identity or authorization. This makes UDM-13/14 and DA-075 verifiable
without a new telemetry store. FP-07 and DP-09/13/14/20 apply.

<a id="I05"></a>

### I05 · Fix the disk publication premise and keep analytical identity close to the result

UDM-14 describes publishing a nonempty entry directory with `os.replace` and treating a second
same-key replacement as harmless. Python's contract raises on a nonempty destination directory.
Use single-winner installation. A competing writer discards its private temporary entry after
verifying the winner under the tier lock. A mismatching winner needs eviction or refusal of that
cache entry and a diagnostic, since it may indicate corruption or an incomplete key. Coordinate
pruning and readers so that neither an active write directory nor a partial read can be mistaken
for a valid entry. A missing entry falls back to the authoritative derivation. Room exists for an
atomic single-file encoding if it fits D2/D4; retain directories if separate files materially help.
Add two writers and a concurrent prune/read to the existing checksum and interrupted-write tests.
[Python `os.replace`](https://docs.python.org/3.14/library/os.html#os.replace)

Retain UDM-16/17's placement of authority-bound work in PostgreSQL, typed analytical expressions
over immutable identified inputs, and explicit bag versus set semantics. In UDM-16/18, make a
backend or settings change move the relevant producer/result basis where it can affect observable
ordering, precision, or grammar. Scratch path, spill policy, or passive observability need no
semantic identity unless a concrete operation depends on them. Use the declared snapshot,
output contract and independent controls for nulls, duplicates and floating order. Use the plan's
bounded observation to settle rich views and certification folds. Avoid a second query language
or a backend-based cache key that overrides native authority. Merge the narrow dependency rules
with I01. The substantive retention changes leave UDM-19's planned removal of legacy model,
migrations, and authoring machinery viable. Carry forward only meaningful archived provenance and
move live consumers with their replacements. DP-08/09/11/15/19 apply.

## Extend the operator's CLI

<a id="I06"></a>

### I06 · Capture the exact run plan and recover it by managed ID

In `cli/demands.py:211–266` the execution policy is resolved in the invocation. The registered
callback records the demand/source context, and `orchestrate/source_reporting.py` records target,
release and runtime, but the recovery action in `cli/result_inspection.py:190–207` reconstructs
`ci demands execute` with only demand ID and source-root. A resumable command can lose the 16 GiB
policy or use the wrong context. The inspection reader verifies the recorded target against the
configured reader. A stage receipt viewed from a canonical session can correctly make native
state unavailable, but its suggested action should carry the expected target identity and how to
select it explicitly.

Add a typed run plan and recovery binding to the existing managed run and demand entry points,
recorded before expensive preparation. Expose a read-only preview of project, selected native
target, release/runtime/provider mode, document and scope, demanded family closure, effective
policy and availability of prerequisites. Separate verified available work from estimates of what
will attach once native bindings exist. `ci demands plan` already registers a demand. Keep preview
read-only and explicit about its limits. Record the nonsecret effective policy and original input
selection in the managed result; on retry, re-resolve credentials and verify the acquired target
and selected basis. Reuse `ci run resume` and `ci results inspect` with an exact recovery action,
including pending attachment or retained intent when available. Explicit policy overrides are
visible. If a predecessor lacks sufficient capture, say what must be supplied. Keep inspect
passive on wrong-target and auth failure, and avoid writing against the configured database as a
side effect of preview or recovery discovery.

Prefer the existing invocation and native-demand contract to a new run controller. Remove
shell-only, partially reconstructed actions when their callers adopt the typed action. UDM-08/12
and UDM-20/21 are the natural owners, with UDM-23 exercising the actual journey. Use an identical
fresh-process retry, an explicit physical memory override, an unauthorized/wrong-target path, and
a pre-registration failed provider check. Verify the displayed effective settings and zero effects
before explicit execution. FP-02/04 and DP-05/18/21/24 apply.

<a id="I07"></a>

### I07 · Give inspection, watch and cancel one attributable operational view

Extend `ci results inspect/watch` and `ci demands read` with a shared typed projection over managed
observations and exact native bindings. The managed `watch` already bounds follow time and the
latest log window. `cli/result_inspection.py` already preserves typed availability and next
actions. Use native snapshot counts by fate and scope when a denominator is available. Frontier
pages stay explicitly partial. Use scoped owner observations for loading, readiness, submitted and
completed inference, wait state, settlement and publication. Distinguish physical provider activity
from registration and acknowledged progress. An observation should identify its attempt/device or
worker and time, and become unknown or stale when attribution or freshness is missing. A process
or GPU observation alone supplies no proof of completed inference. Present documents, pages,
regions, products, and sentence occurrences as separate units. Include the reuse reason from the
native decision, with the source derivation or retained intent when the reader may see it.

Cancellation should return the actual effect and next action. For `ci demands cancel`, show demand
detachment, surviving shared interest, and any owned work it can subsequently retire. Add a managed
stop action by invocation ID for the separate case of an operator interrupting one execution. Route
it through the established execution host cancellation and retirement protocol after verifying
invocation ownership and process-start identity. A stale identity, unsupported ownership or
unreachable host gives an explicit refusal. A repeated request should return the observed drain or
settlement standing. Expose stop requested, draining, unresolved custody or confirmed retirement
only as established by the corresponding owner. Provider cleanup, exact lease settlement and safe
resume belong to their own authorities. The thinner alternative is to report an external interrupt
and its outcome, which still leaves the operator to locate and authenticate the process manually.

Build the first projection with UDM-12/20 so it can serve diagnosis, then use UDM-21/23 for Standard
and Integrated projections. The managed stop route depends on the host's authenticated ownership and
can follow the first projection. Exercise two callers with shared interest, one cancellation, a
stale process identity, wrong-target observations and nested uncertainty. Verify JSON and terminal
report the same facts, and a watcher exit leaves the operation's execution contract intact.
[CLI custody][cli-adr] · [Execution host][host-adr]

<a id="I08"></a>

### I08 · Expose change impact and keep CLI presentation thin

Combine the UDM-04 compiled-model preview successor with UDM-09–12's typed program delta,
changed producer and validity identities, and the planned no-native-change decision. Before apply,
show which authoritative facts changed, installed bytes or privileges that would move, and whether
prior work can carry forward, require reconfirmation, or need new execution. Mark assumptions that
only a live binding or current support check can settle. Follow the existing `ci model change`
preview/inspect/apply and candidate/register/deploy with explicit target and expected revision,
then activation/adoption where required. Retain binding and partial-apply recovery. Include
focused read-only inspection for failed or unavailable effects. The successor retires the old
preview's rule digest and explanation with UDM-04/19. Reuse that comparison for impact reporting
and review the outstanding revision-log decision there. Avoid a parallel change graph, manual
command registry, or separate application mechanism. Compare a vocabulary change, a validation-only
change and an unrelated authoring edit with no change to installed bytes. Verify exact reviewed
changes apply through the installed command.

Typer 0.28.0 and Rich 15.0.0 are the repository pins. Context7 supplied the official Typer help
and group reference and exact Rich 15.0.0 render references. Installed Typer source confirms
`add_typer`, `rich_help_panel` and completion hooks. Group options by selection, effects and output
in the existing lazy registry, and link help/examples from the task's entry point. Complete static
names or bounded local identifiers when available. Shell completion should remain passive and cheap.
Rich `Table` or `Tree` can render nested reasons. A single optional `Live` view over a shared stderr
console can show bounded known/indeterminate progress, updating on observation rather than launching
extra polls for display. Disable redirection of machine output and keep `--json` to one stable
document. Provide a bounded plain view in noninteractive use. Use the existing output owner and
maintain outcome-specific exit and closed-pipe behavior. Verify completion/help, TTY and piped JSON,
missing authority, and mid-watch cancellation on the same typed model. Typer/Rich help and output
choices serve the operability changes without changing the meaning of commands. DP-01/14/17/21/24
apply. [Typer reference](https://typer.tiangolo.com/reference/typer/) · [Rich 15.0.0 Live](https://github.com/Textualize/rich/blob/v15.0.0/docs/source/live.rst)

## Integrate and qualify

1. At UDM-00/20, preserve historical evidence. Resolve the material dependency and private
   recovery premises and the cross-release discovery defect before fixing the relevant revisions.
   Keep the existing bounded timeout and withheld-region diagnosis. A failure that cannot be
   reproduced at that bound is an explicit limit, with the recorded production-scale check still due.
2. Land identity, support, and recovery together at their owners. Land the operation inspection
   and exact recovery projections along those seams so the stage journey exercises them. Cache
   preparation and the authoring preview can proceed independently where they share no contract.
   Complete retired-consumer migration with the replacing owner. The project needs neither a
   general remote cache nor a second orchestration plane to obtain these amendments' benefits.
3. Add the distinguishing cases to UDM-22's managed union. UDM-23 already requires a fresh demand
   on final source, an interruption and resume, full coverage and an unchanged repeat with zero
   provider requests, native attempts or new derivations. Keep those checks. State the actual
   retained-work census and independent expected reuse before execution, so a new demand can show
   adopted work and proper fresh computation simultaneously. Include a bounded unrelated-change
   and equal-content case to detect over-invalidation, a changed-validator/support case where use
   requires recheck, and a material operation or input change that requires a producer. Use independent
   native/provider counts and exact receipts to distinguish cache hits, revalidation, checkpoint
   reuse, settlement and real work. Repeat after an expendable cache eviction to ensure durable
   work remains reusable. Keep independent whole-view comparison and authentic provider
   coverage, with explicitly selected fresh evidence where needed. A no-work repeat can pass while
   a cross-release case still fails. [Qualification][qualification] · [Test-assessment companion][tests]

The review used source and retained evidence across the series, including model and vocabulary
authority, program and privilege declarations, analytical placement, and retirement consumers where
they intersect reuse and operation. Live deployment, provider execution, and whole-book reproduction
remain qualification work. The incidence of pre-retention losses, compatible checkpoint basis, and
cost remain open. The TDM plan owns its test architecture and Chandra OCR stays outside this series.
Adopt recommendations through plan revision, with proposed ADR impacts kept distinct from existing
accepted rules.

[udm]: ../plans/unified-domain-model-and-execution_2026-11-19.md
[model]: ../plans/unified-domain-model-and-execution/model-authorities-and-openness.md
[validity]: ../plans/unified-domain-model-and-execution/lowered-operation-facts-and-validity.md
[programs]: ../plans/unified-domain-model-and-execution/programs-identity-and-revisions.md
[cache]: ../plans/unified-domain-model-and-execution/cache-system.md
[analytical]: ../plans/unified-domain-model-and-execution/analytical-placement-sql-and-retirement.md
[qualification]: ../plans/unified-domain-model-and-execution/qualification.md
[ddo]: ../plans/declared-data-operations_2026-11-12.md#scoped-acquisition-and-native-authoring-integration--2026-11-18
[status]: ../../STATUS.md
[op-adr]: ../adr/0092-ddo-operation-authority.md
[support-adr]: ../adr/0122-set-wise-support-validity.md
[host-adr]: ../adr/0125-process-owned-execution-host.md
[cli-adr]: ../adr/0069-cli-operations-custody.md
[cache-evidence]: ../design_review/evidence/2026-11-18_production-review-inputs/library-cachetools.md
[tests]: ../design_review/design_principles/core/test-assessment.md
