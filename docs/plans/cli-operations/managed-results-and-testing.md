# Managed invocation results, tests and repository maintenance

**Accepted target.** Companion to the [CLI operations coordinator](../cli-operations_2026-11-07.md).
Owns CLI-02 and CLI-03. The receipt supervisor owns process evidence and classification.
Domain data and published evidence have separate custody. CLI-02 also owns the bounded
diagnostic retrieval and retention used by other packages.

<a id="CLI-02"></a>
## CLI-02 · Create, retrieve and expire managed results

Allocate an opaque invocation ID and private workspace at dispatch. Use ignored `build/ci/`
under the resolved development checkout and a deployment-owned persistent state directory on
an installed host. Announce the ID early, including on the diagnostic stream in JSON mode.
Publish a small manifest with action and scope, effective redacted target, applicable source and
runtime bindings, stage and outcome, relevant authoritative IDs, related invocations and named
artifact roles. Domain selection IDs remain the IDs used for semantic reads. A copy or external
delivery of the same result preserves its ID. Retry and recomputation create a new invocation
with its own context and a reference to the original.

Use `ci results list` with bounded page and scope, `show RESULT` for artifacts and retention,
`watch RESULT` over available status or receipt events, and `export RESULT` for named deliverables
with optional destination. No read exposes producer-private staging. Bounded pages control emitted
work. Directory enumeration can still grow with the retained population, so start with scoped
workspace discovery and short retention. Add an index if observed repeated lookup or sorting
becomes costly enough to justify its coordination and recovery obligations. Distinguish expired
from unknown when an existing lifecycle record can do so. A compact expiry marker becomes useful
if an actual consumer needs that distinction beyond cleanup.

**Publication and concurrency.** Use same-filesystem staging and Python 3.14 `os.replace()`
for one complete manifest update. Reuse the existing Linux `renameat2(RENAME_NOREPLACE)` bundle
publisher for a complete directory, factoring shared mechanics at its publication boundary if
needed. Stage on the destination filesystem for external copies and refuse an occupied destination.
A manifest can expose settled artifacts only after publication. For the supported local Linux
state root, use Python 3.14 `fcntl.flock()` with stable per-result lock identity to coordinate
producer, export, hold updates and cleanup, or reuse an existing equivalent coordination
primitive at that boundary. Use the same stable lock identity when a reader acquires an export lease or a consumer adds
a hold. Check eligibility again while holding that lock. Acquire a dependency hold before
starting dependent work. If the required result has expired, refuse the late hold. Keep the
lock identity stable across competing discovery and deletion, including abandoned producer
recovery. A manifest becoming visible is a publication event. Expiry eligibility follows
settlement and the hold policy.
Only managed paths proven inside the owned root may be removed. Treat path substitution and
untrusted manifest paths as refusal conditions. Stage and identify incomplete publication
so a later inspection or retry can recover. Atomic rename gives visibility atomicity. A
power-loss durability promise would require its own storage assumptions and verification.
[Python `os.replace`](https://docs.python.org/3.14/library/os.html#os.replace) ·
[Python `fcntl.flock`](https://docs.python.org/3.14/library/fcntl.html#fcntl.flock) ·
[Linux `renameat2`](https://man7.org/linux/man-pages/man2/rename.2.html) ·
[Existing publication owner](../../../python/corpus-structure/src/corpus_structure/serve/companion_export.py)

| Class | Minimum retained result and protection under CLI-RC02 |
|---|---|
| Active or unsettled work | Keep producer scratch, staging and transport until process settlement and cleanup are established. A dead owner alone does not settle surviving children. Keep a bounded diagnostic excerpt where needed. |
| Ordinary success | Receipt, named deliverables and authoritative references. Expire after **one day** from settlement if unreferenced. |
| Failure or interruption | Identity, exact stage, exit and cleanup outcome plus the evidence needed for diagnosis or reconciliation. Expire after **one week** from settlement if unreferenced. |
| Model or migration candidate | Keep exact candidate and predecessor bindings while a pending approved change or dependent result uses them. An unreferenced success uses the one-day window. A stale preview can be inspected while retained and needs a fresh preview before application. |
| Active review, qualification and delivery | Hold dependencies until the consumer settles and its required evidence is published or released. Protect any live export. Publish the necessary durable evidence through the existing evidence owner. |
| Committed evidence, source and functional data | The existing owners govern custody. GC cannot select these classes. |

`ci results gc` previews by default. `--apply` reuses the same eligibility rule and performs
the effect. A host can schedule the same operation if recurring cleanup warrants it. `show`
explains holds and expiry. Explicit evidence retention promotes only the necessary closure and
keeps its references. Compact raw test data only after demonstrating the retained representation
still supports classification, replacement and audit. Rich's terminal capture is presentation.
[Durable evidence custody](../../design_review/evidence/README.md)

### Action-driven diagnostics

Use the producer's status, receipt or typed refusal first. Each retained or emitted diagnostic
must help answer an operator question. Introduce new capture only when that answer would otherwise
be lost, and identify the consumer, next action, expected volume and storage and processing burden.

| Operator decision | Source and presentation |
|---|---|
| Can I retry a failed check? | `ci results show RESULT` projects lane, stage, failure code, retryability and receipt ID. `watch RESULT` follows complete new records from the live owner. Use a bounded child excerpt if the receipt alone cannot explain the failure. |
| Can I resume a change or export? | Project the owned outcome and settled effects with the exact preview, target, predecessor or cut needed to resume. CLI-05 and CLI-06 supply those bindings. |
| Which service, target or role needs attention? | `ci doctor` and named health/status actions use the owner's existing check and its remedy. CLI-07 owns any further authorized host read. |

Use invocation/result identity, meaningful stage or code, source and an optional attempt reference.
Select actionable warnings, errors and phase transitions needed for operator control. Omit per-item
success chatter, routine SQL or provider payloads and duplicated receipt events. Bound bytes, count
and excerpts before formatting or persistence. If a named consumer needs live or foreign diagnostics
that the owner cannot retain, use a bounded invocation-local JSONL sidecar under the same expiry and
holds. Limit reads by cursor, bytes and complete records. A partial final line while active can be
retried at the same cursor. Report invalid settled output as corrupt and report truncation or
unavailability explicitly. `scripts/test_receipts.py:read_stream()` materializes the settled input
for classification. Use incremental byte offsets for live watch. Diagnostic availability is separate
from settlement, authority and verified coverage. CLI-01 owns terminal projection and the diagnostic
sidecar follows CLI-02 custody.
[Receipt owner](../../../scripts/test_receipts.py) ·
[Safe output](command-context-output.md#safe-output-and-progress)

**Logging selection.** Start with typed owner events and an invocation-scoped stdlib
`logging.StreamHandler` for useful foreign records, with filtering and redaction before delivery.
Qualify structlog **26.1.0** only if a real mixed application/stdlib journey needs shared structured
fields that the small stdlib route cannot preserve without duplicative code. Compare that journey
with the receipt-only path. Use `structlog.contextvars.bound_contextvars()` and
`merge_contextvars()` in the producing context, `structlog.stdlib.LoggerFactory`,
`ProcessorFormatter.wrap_for_formatter` for structured events, and `foreign_pre_chain` and
`ProcessorFormatter.remove_processors_meta` at the stdlib formatter boundary. Capture and redact
approved fields before any buffering. Keep the first useful path synchronous and local, and pass
explicit approved IDs across thread and process boundaries. A listener cannot reconstruct producer
context, and `logging.handlers.QueueHandler.prepare()` can flatten record information.
Compare final stderr and any sidecar in a fresh process. `structlog.testing.capture_logs()`
does not establish behavior of the configured processors.
[Python 3.14 StreamHandler](https://docs.python.org/3.14/library/logging.handlers.html#logging.StreamHandler) ·
[Structlog 26.1.0 context](https://www.structlog.org/en/26.1.0/contextvars.html) ·
[Stdlib integration](https://www.structlog.org/en/26.1.0/standard-library.html) ·
[Structlog testing](https://www.structlog.org/en/26.1.0/testing.html) ·
[QueueHandler.prepare](https://docs.python.org/3.14/library/logging.handlers.html#logging.handlers.QueueHandler.prepare)

External JSON/ECS formatting needs a concrete collector. Additional routing or failure-context
buffering needs an evidenced gap beyond bounded excerpts and a resource and drain contract.
Distributed tracing or hosted query needs a decision spanning services that current status and
IDs cannot resolve. Metrics, incident storage, support exports and a faster logging backend
require their own consumer and cost case. I10 records the tool-specific comparisons and prior
evidence. [I10 review](../../plan_improvement_reviews/cli-operations_2026-11-07.md#I10)

**Acceptance.** Retrieve settled and running invocations from a second process. Deliver to an
optional destination and verify identity and content. Race GC with an active export, producer,
or dependency hold, and with interrupted publication. Use controlled time to prove both expiry
boundaries and exact collection eligibility. Exercise an expired identity with a late hold,
an interrupted publication and an unsettled child. Protected candidates and durable evidence
remain accessible. Show the correct next action from a known failed or interrupted invocation
by ID. Include a partial live tail, corrupt settled input, a noisy source, and disabled or failed
diagnostics with the primary outcome intact. A missing local delivery never triggers an implicit provider or extraction rerun.

<a id="CLI-03"></a>
## CLI-03 · Route tests and maintenance through owned recipes

`ci test` selects the complete applicable suite for the resolved checkout with zero operands.
The installed adapter invokes the established `just test-all` and, where applicable, the separate
`just test-native-faults` owner. Extend the recipes and existing `scripts/test_receipts.py`
interface to accept an internally allocated result workspace and preserve direct recipe defaults.
Use one managed invocation containing separate native lane receipts. Keep the existing
supervisor's responsibility for child process groups, exit records and cleanup. Treat a missing
required lane prerequisite as blocked and a valid empty selection as its own outcome. A lane
selector or declared pytest selector is a deliberate narrower run. After the explicit command-specific
`--`, validate the literal suffix with the test owner before forwarding. Support selectors and
options whose impact on scope the receipt can represent. Reject attempts to override receipt
paths, required plugins, lane policy or safety controls. Keep the argv intact through `just`
and the supervisor. The command surface owns recognizing the separator.
[CLI-01 recipe boundary](command-context-output.md#routes-and-invocation-intent)

**Native tooling.** Reuse pytest-xdist **3.8.0** `-n auto` and `--dist=loadgroup` for the ordinary
parallel lane, strict markers and config, and the existing exclusion of shared-cluster faults.
Keep the owner-defined exclusive fault invocation at `-n 0` after ordinary work has settled and
the native harness can acquire its existing exclusive lease. Diagnose parallel failures in the substrate owner and preserve the
actual resolved lanes and selectors in receipts. Reuse `cargo nextest list --release --workspace --message-format json` and
`cargo nextest run --release --workspace --profile qualification --no-tests=warn` through
the supervisor. Preserve `INSTA_UPDATE=no`. The profile currently writes to a shared JUnit
path per target directory. In the receipt supervisor, serialize nextest report production
through report capture for invocations sharing that target/report. Hold the lock across both
operations, including direct recipe callers of the same supervisor, and release after the
receipt settles. Preserve shared compilation caches and keep ordinary pytest outside that lock.
Revisit the lock only if a supported invocation-specific report path can preserve the profile
and caches. The supervisor's existing process-group use of Python 3.14 `subprocess.Popen(start_new_session=True)`
and its settlement record are the child boundary. Forward cancellation through the additional recipe process layer to the
receipt supervisor before any forced teardown. The inner supervisor owns its separate
worker process groups. Wait for actual settlement and record escalation or unreachable ownership
separately from a normal cancellation. An empty native selection or startup warning cannot establish passing
functionality. Record actual toolchain versions with applicable results.
[xdist 3.8.0 distribution source](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/docs/distribution.rst) ·
[nextest run options](https://nexte.st/docs/running/) · [nextest profile JUnit path](https://nexte.st/docs/machine-readable/junit/#configuration) ·
[Python process supervision API](https://docs.python.org/3.14/library/subprocess.html#subprocess.Popen) ·
[Existing recipes](../../../justfile) · [Receipt supervisor](../../../scripts/test_receipts.py)

`ci test retry RESULT` uses the prior receipt, existing `write_unresolved()` and a check against
current collection, source and context. A broader affected selection is explicit and explained.
`ci test coverage RESULT…` uses the existing `classify()` and declared required manifests.
Report the original attempt outcome separately from exact replacement coverage and unresolved
identities. Preserve native context, failures and interruption records. A retained classifier
input needs a hold while it is required for qualification. Use truthful stage and count events
for parent progress and a direct remedy in final output.
[Test policy owner](../test-audit-resolution_2026-11-05.md) ·
[Test assessment companion](../../design_review/design_principles/core/test-assessment.md)

`ci check` and named check routes map to established readiness, type, lint, hygiene, documentation,
model, evidence and verification recipes. Split read-only variants where needed. Existing
`ruff` applies fixes and `turn-end` formats and regenerates metadata. Give formatting, generation,
ADR creation and deliberate evidence promotion explicit effects. Keep ownership and defaults in
the recipe and tool layers. Results are managed where retrieval or reconciliation matters.
Return a small typed outcome for short actions. Do not copy all tool streams.

**Acceptance.** Demonstrate native argv through the installed CLI and the actual recipe owner,
including a zero-argument campaign, an explicit narrower selection, and an unavailable exclusive
prerequisite. Exercise a failed ordinary attempt, applicable replacement and exclusive lane.
Verify the declared union against independently known gaps without rewriting the failed receipt. Cancel an installed invocation
and confirm child-group settlement or explicit cleanup failure. Retry by ID from a second process. Exercise concurrent campaigns to
verify receipt isolation and exclusive native prerequisites. Check with a deliberately fixable source issue and demonstrate that only the explicit fix path
writes it.

### Completion audit follow-up

**F01 · Managed custody and settlement.** The normal lease, no-replace delivery, expiry and
hold paths have bounded controls. Reads accept a manifest artifact path of `.` and can copy the
entire invocation, including private staging. GC deletes a `.gc-<id>` directory based on its
name, without proving it was retired by the store or including it in preview/removal output.
Both were reproduced in temporary storage. Validate stored artifact roles and path identity at
read and delivery, and authenticate retired directories under the existing namespace boundary
before cleanup. An abandoned running invocation has no installed settlement or recovery path.
Add recovery that preserves unknown child ownership and permits inspection or retry when the
owner proves settlement. Exercise substituted paths, unrelated directories, authenticated
interrupted cleanup and active exporter/producer interleavings. Keep existing retention windows.
[Artifact reads and delivery](../../../python/corpus-structure/src/corpus_structure/cli/managed.py#L260) ·
[Collection](../../../python/corpus-structure/src/corpus_structure/cli/managed.py#L321)

**CLI-CA02 · Actionable diagnostics and durable promotion.** `show` returns the raw manifest
without effective expiry or diagnostic availability. `watch` exits at settlement before reading
remaining records and treats a missing stream as silence. Test progress has stage/failure output
but lacks the planned owner counts. The supervisor writes and then prints the full classification,
which the recipe adapter buffers before the CLI rereads the retained copy. Project compact bounded
status from the existing owners, including explicit unavailable, corrupt or truncated diagnostics
and the next action by ID. `ci evidence retain` copies the artifact and indexes a folder without
creating a finalized record, so provenance, consumer references and file hashes are missing from
the evidence owner. Compose the existing record/finalize path for the selected necessary closure.
Exercise settled and partial tails, blocked diagnostics, and a promoted result that can be verified
after its managed copy expires. Keep optional logging and extra capture conditional.
[Show and watch](../../../python/corpus-structure/src/corpus_structure/cli/managed.py#L409) ·
[Supervisor publication](../../../scripts/test_receipts.py#L1204) ·
[Promotion adapter](../../../python/corpus-structure/src/corpus_structure/cli/operations.py#L151) ·
[Evidence records](../../design_review/evidence/README.md)

**F03 · Test dispatch, retry and qualification context.** The selector validator returns false
for `-k EXPRESSION` alone, just as for display-only `-q`. The installed adapter then treats a
filtered request as the full campaign and can send the filter to the exclusive fault lane.
Classify keyword selections as narrowing intent and refuse them for that lane. The current
failure summary recommends a node retry whenever any artifact exists, even for failures that
cannot be retried by node. Use the supervisor's failure scope to distinguish node retry, a fresh
lane or a custody diagnosis. The retry preflight compares source, Python and library versions,
and installed coverage drops the per-attempt native and invocation context already retained by
the supervisor. Expose enough context to judge applicability and separate original outcomes,
replacement evidence and unresolved identities. Coverage also derives the required set solely from
published artifacts. In a temporary full-campaign control with a passed ordinary receipt and a
failed fault lane without an artifact, installed coverage returned `passed` and `covered` for the
ordinary nodes. Preserve the requested applicable lanes and their original outcomes even when a
lane cannot publish a receipt. Exercise keyword-only and display-only inputs, reserved options,
unavailable prerequisites and retry actions without changing the recorded failed attempt.
[Selector validation](../../../scripts/test_receipts.py#L1054) ·
[Dispatch and next action](../../../python/corpus-structure/src/corpus_structure/cli/testing.py#L127)
